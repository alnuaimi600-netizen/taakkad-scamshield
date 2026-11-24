"""The full check: mask -> link checks -> text signals -> (optional LLM) -> verdict."""
from __future__ import annotations

from dataclasses import asdict

from . import llm
from .entities import claimed_categories
from .masking import mask
from .scoring import decide
from .text_signals import detect
from .url_checks import URL_RE, check_message_links, extract_urls


def analyse_message(text: str, lang: str = "ar", use_llm: bool = True) -> dict:
    masked = mask(text)  # 1. privacy first: nothing below sees the raw text
    urls = extract_urls(masked.text)
    text_only = URL_RE.sub(" ", masked.text)

    link_reports, link_findings, claimed = check_message_links(text_only, urls)
    signals = detect(text_only, has_link=bool(urls))

    llm_result = None
    if use_llm:
        rule_codes = [s.code for s in signals if s.weight] + [f.code for r in link_reports for f in r.findings]
        llm_result = llm.analyse(masked.text, rule_codes, lang)

    verdict = decide(
        signals, link_reports, link_findings, claimed, lang=lang,
        extra_codes=set(llm_result["signals"]) if llm_result else None,
    )
    claim_pairs = [(e.category, e.id) for e in claimed]
    claim_pairs += [(c, None) for c in sorted(claimed_categories(text_only) - {e.category for e in claimed})]
    return {
        # internal fields for anonymous stats; main.py strips every "_" key from responses
        "_all_codes": sorted({s.code for s in signals if s.weight}
                             | {f.code for r in link_reports for f in r.findings}
                             | {f.code for f in link_findings}),
        "_claims": claim_pairs,
        "status": verdict.status,
        "risk_score": verdict.risk,  # 0-100, always inside the status band (see scoring.RISK_BANDS)
        "reasons": [{"code": r.code, "text": r.text} for r in verdict.reasons],
        "highlights": verdict.highlights,
        "safe_action": verdict.safe_action,
        "checked": verdict.checked,
        "not_guaranteed": verdict.not_guaranteed,
        "summary": (llm_result or {}).get("summary") or None,
        "claimed_entities": [e.name(lang) for e in claimed],
        "links": [
            {"url": r.url, "domain": r.registered_domain, "official": bool(r.official_for), "flags": [f.code for f in r.findings]}
            for r in link_reports
        ],
        "masked_text": masked.text,
        "masked_counts": masked.counts,
        "llm_used": llm_result is not None,
        "_debug_score": verdict.score,
    }


__all__ = ["analyse_message", "asdict"]
