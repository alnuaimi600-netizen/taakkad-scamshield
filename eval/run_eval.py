"""Technical evaluation on the synthetic message set (docs/spec.md section 8).

Usage (from the repo root):
    backend/.venv/Scripts/python eval/run_eval.py            # rules only (default)
    TAAKKAD_LLM=1 backend/.venv/Scripts/python eval/run_eval.py --llm

Writes eval/results.md and eval/results.json exactly as measured.
Nothing is fetched: links in the data use reserved .test domains and are only read as text.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
# Reproducible: ignore domains confirmed on a live dashboard; use an empty throwaway DB.
import os, tempfile  # noqa: E401,E402
os.environ["TAAKKAD_DB"] = os.path.join(tempfile.mkdtemp(prefix="taakkad-eval-"), "eval.db")

from app.analyzer import analyse_message  # noqa: E402

HIGH, UNCLEAR, NONE = "high_suspicion", "unclear", "no_visible_indicators"


def pct(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "n/a"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true", help="use the LLM layer (needs TAAKKAD_LLM=1 and credentials)")
    ap.add_argument("--data", default=str(ROOT / "data" / "synthetic_messages.jsonl"))
    args = ap.parse_args()

    rows = [json.loads(line) for line in Path(args.data).read_text(encoding="utf-8").splitlines() if line.strip()]
    results = []
    for r in rows:
        out = analyse_message(r["text"], r["lang"], use_llm=args.llm)
        results.append({**{k: r[k] for k in ("id", "lang", "channel", "category", "asks_card_or_otp")},
                        "status": out["status"], "reasons": [x["code"] for x in out["reasons"]], "llm_used": out["llm_used"]})

    by = lambda cat: [x for x in results if x["category"] == cat]  # noqa: E731
    scam, legit, otp, amb = by("scam"), by("legit"), by("otp_delivery"), by("ambiguous")
    benign = legit + otp
    card_otp = [x for x in results if x["asks_card_or_otp"]]

    metrics = {
        "false_alarms_benign_high": pct(sum(x["status"] == HIGH for x in benign), len(benign)),
        "benign_unclear": pct(sum(x["status"] == UNCLEAR for x in benign), len(benign)),
        "misses_scam_no_indicators": pct(sum(x["status"] == NONE for x in scam), len(scam)),
        "scam_high": pct(sum(x["status"] == HIGH for x in scam), len(scam)),
        "scam_unclear": pct(sum(x["status"] == UNCLEAR for x in scam), len(scam)),
        "card_or_otp_request_detected_high": pct(sum(x["status"] == HIGH for x in card_otp), len(card_otp)),
        "otp_delivery_false_alarms_high": pct(sum(x["status"] == HIGH for x in otp), len(otp)),
        "unclear_overall": pct(sum(x["status"] == UNCLEAR for x in results), len(results)),
        "ambiguous_distribution": dict(Counter(x["status"] for x in amb)),
    }
    mode = "rules + LLM" if args.llm else "rules only"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    llm_calls = sum(x["llm_used"] for x in results)

    (ROOT / "eval" / "results.json").write_text(
        json.dumps({"run_at": stamp, "mode": mode, "llm_calls_succeeded": llm_calls, "n": len(results),
                    "metrics": metrics, "per_message": results}, ensure_ascii=False, indent=2), encoding="utf-8")

    labels = {
        "false_alarms_benign_high": "False alarms: benign (legit + code-delivery) rated high_suspicion",
        "benign_unclear": "Benign rated unclear",
        "misses_scam_no_indicators": "Misses: scam rated no_visible_indicators",
        "scam_high": "Scam rated high_suspicion",
        "scam_unclear": "Scam rated unclear",
        "card_or_otp_request_detected_high": "Card/OTP requests rated high_suspicion",
        "otp_delivery_false_alarms_high": "Code-delivery messages rated high_suspicion",
        "unclear_overall": "Unclear rate (all messages)",
    }
    md = [
        "# Evaluation results",
        "",
        f"- Run: {stamp}",
        f"- Mode: **{mode}**" + (f" (LLM answered {llm_calls}/{len(results)})" if args.llm else ""),
        f"- Data: `{Path(args.data).relative_to(ROOT).as_posix()}` — {len(results)} synthetic messages "
        f"({len(scam)} scam, {len(legit)} legit, {len(otp)} code-delivery, {len(amb)} ambiguous; "
        f"{len(card_otp)} ask for card/OTP)",
        "",
        "> Caveat: the messages were written by the same team that wrote the rules, so these numbers are",
        "> in-sample and likely optimistic. They are not a measure of real-world accuracy.",
        "",
        "| Metric | Result |",
        "|---|---|",
        *[f"| {labels[k]} | {v} |" for k, v in metrics.items() if k in labels],
        f"| Ambiguous messages (no single right answer) | {metrics['ambiguous_distribution']} |",
        "",
        "## Per message",
        "",
        "| id | lang | category | card/OTP | status | reasons |",
        "|---|---|---|---|---|---|",
        *[f"| {x['id']} | {x['lang']} | {x['category']} | {'yes' if x['asks_card_or_otp'] else ''} | {x['status']} | {', '.join(x['reasons'])} |"
          for x in results],
        "",
    ]
    (ROOT / "eval" / "results.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md[:18 + len(labels)]))


if __name__ == "__main__":
    main()
