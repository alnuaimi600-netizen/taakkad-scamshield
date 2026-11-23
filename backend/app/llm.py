"""Optional LLM layer: intent analysis + a plain-language summary (AR/EN).

* Off by default. Enabled only when TAAKKAD_LLM=1 and Anthropic credentials exist
  (we still need to confirm with the organisers that external APIs are allowed).
* Receives ONLY the masked text plus the rule signals - never the raw message.
* Can ADD signals and write a summary; it can never lower the rule-based verdict.
* Any failure (no key, network, refusal, bad JSON) falls back to rules only.
"""
from __future__ import annotations

import json
import logging
import os

log = logging.getLogger("taakkad.llm")

MODEL = os.environ.get("TAAKKAD_LLM_MODEL", "claude-opus-5-5")
ALLOWED_CODES = ["asks_card", "asks_otp", "asks_personal", "receive_money_link", "payment_request", "urgency", "threat", "prize"]

SYSTEM = (
    "You help people in the UAE judge WhatsApp/SMS messages that might be fraud. "
    "You get a message in which personal data was already replaced by tokens like [CARD] or [PHONE], "
    "and the signals a rules engine found. Do not open links. "
    "Return which of the allowed signal codes are clearly present in the message (only add codes you are confident about), "
    "and a summary of at most two short sentences in the requested language that explains, in plain words for any age, "
    "what the message asks the reader to do and why that is risky. "
    "Never call a message safe and never name a type of fraud. "
    "A message that only delivers a code and says not to share it is normal and does not contain asks_otp."
)

SCHEMA = {
    "type": "object",
    "properties": {
        "signals": {"type": "array", "items": {"type": "string", "enum": ALLOWED_CODES}},
        "summary": {"type": "string"},
    },
    "required": ["signals", "summary"],
    "additionalProperties": False,
}


def enabled() -> bool:
    return os.environ.get("TAAKKAD_LLM") == "1"


def analyse(masked_text: str, rule_codes: list[str], lang: str) -> dict | None:
    """Return {"signals": [...], "summary": str} or None if the LLM is off or failed."""
    if not enabled():
        return None
    try:
        import anthropic
    except ImportError:
        return None

    language = "Arabic (simple, Gulf-friendly Modern Standard Arabic)" if lang == "ar" else "English"
    user = (
        f"Message (masked):\n<<<\n{masked_text[:4000]}\n>>>\n\n"
        f"Rule signals already found: {', '.join(rule_codes) or 'none'}\n"
        f"Write the summary in {language}."
    )
    try:
        client = anthropic.Anthropic(timeout=20.0, max_retries=1)
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=SYSTEM,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}},
            messages=[{"role": "user", "content": user}],
        )
    except Exception as exc:  # network, auth, rate limit... -> rules only
        log.warning("LLM call failed (%s); using rules only", type(exc).__name__)
        return None

    if response.stop_reason == "refusal":
        return None
    text = next((b.text for b in response.content if getattr(b, "type", "") == "text"), "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    signals = [s for s in data.get("signals", []) if s in ALLOWED_CODES]
    summary = str(data.get("summary", "")).strip()[:500]
    # Guard: the model must not reassure the user.
    if any(w in summary.lower() for w in ("safe", "legit", "آمن", "امن", "سليمة")):
        summary = ""
    return {"signals": signals, "summary": summary}
