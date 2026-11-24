"""Link-only evaluation: precision / recall on synthetic URLs (data/synthetic_urls.jsonl).

Each URL is checked on its own, as if a user pasted only the link. Nothing is fetched:
every address is a reserved .test/.example domain, an RFC 5737 documentation IP, or a
shortener string that is only read as text.

Usage (from the repo root):
    backend/.venv/bin/python eval/run_url_eval.py

Writes eval/url_results.md and eval/url_results.json exactly as measured.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["TAAKKAD_DB"] = os.path.join(tempfile.mkdtemp(prefix="taakkad-url-eval-"), "eval.db")

from app.analyzer import analyse_message  # noqa: E402

HIGH, UNCLEAR, NONE = "high_suspicion", "unclear", "no_visible_indicators"


def prf(rows: list[dict], flagged) -> dict:
    tp = sum(1 for r in rows if r["label"] == "phishing" and flagged(r))
    fp = sum(1 for r in rows if r["label"] == "legitimate" and flagged(r))
    fn = sum(1 for r in rows if r["label"] == "phishing" and not flagged(r))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}


def main() -> None:
    data = ROOT / "data" / "synthetic_urls.jsonl"
    rows = [json.loads(line) for line in data.read_text(encoding="utf-8").splitlines() if line.strip()]
    for r in rows:
        out = analyse_message(r["url"], "en", use_llm=False)
        r["status"] = out["status"]
        r["risk_score"] = out["risk_score"]
        r["flags"] = out["links"][0]["flags"] if out["links"] else []

    strict = prf(rows, lambda r: r["status"] == HIGH)
    broad = prf(rows, lambda r: r["status"] != NONE)
    by_trick = {}
    for r in rows:
        by_trick.setdefault(f'{r["label"]}/{r["trick"]}', Counter())[r["status"]] += 1

    run = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    n_ph = sum(r["label"] == "phishing" for r in rows)
    (ROOT / "eval" / "url_results.json").write_text(json.dumps(
        {"run": run, "mode": "rules only, link only", "strict_high_only": strict, "broad_high_or_unclear": broad,
         "by_trick": {k: dict(v) for k, v in by_trick.items()}, "results": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Link-only evaluation", "",
        f"- Run: {run}", "- Mode: **rules only**, each URL checked alone (no message text)",
        f"- Data: `data/synthetic_urls.jsonl`: {len(rows)} synthetic URLs ({n_ph} phishing, {len(rows) - n_ph} legitimate)", "",
        "> Caveat: the URLs were written by the same team that wrote the rules, so these numbers are",
        "> in-sample and likely optimistic. They are not a measure of real-world accuracy.", "",
        "| Counting as \"flagged\" | Precision | Recall | F1 | TP | FP | FN |", "|---|---|---|---|---|---|---|",
        f'| `high_suspicion` only | {strict["precision"]:.2f} | {strict["recall"]:.2f} | {strict["f1"]:.2f} | {strict["tp"]} | {strict["fp"]} | {strict["fn"]} |',
        f'| `high_suspicion` or `unclear` | {broad["precision"]:.2f} | {broad["recall"]:.2f} | {broad["f1"]:.2f} | {broad["tp"]} | {broad["fp"]} | {broad["fn"]} |',
        "", "## By trick", "", "| label / trick | results |", "|---|---|",
        *[f"| {k} | {', '.join(f'{s}: {n}' for s, n in sorted(v.items()))} |" for k, v in sorted(by_trick.items())],
        "", "## Per URL", "", "| id | label | trick | url | status | risk | flags |", "|---|---|---|---|---|---|---|",
        *[f'| {r["id"]} | {r["label"]} | {r["trick"]} | `{r["url"]}` | {r["status"]} | {r["risk_score"]} | {", ".join(r["flags"])} |' for r in rows],
    ]
    (ROOT / "eval" / "url_results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"strict (high only): {strict}\nbroad (high or unclear): {broad}")


if __name__ == "__main__":
    main()
