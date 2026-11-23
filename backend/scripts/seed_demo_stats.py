"""Fill the dashboard with DEMO data for presenting the prototype.

Replays the 60 synthetic messages in data/synthetic_messages.jsonl through the real
analyzer, spread over the last 14 days. Every row is stored with synthetic=1 and the
dashboard says so on screen. These are not real reports or real volumes.

Usage (from the repo root):
    backend/.venv/Scripts/python backend/scripts/seed_demo_stats.py          # add demo rows
    backend/.venv/Scripts/python backend/scripts/seed_demo_stats.py --clear  # remove demo rows only
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app import stats  # noqa: E402
from app.analyzer import analyse_message  # noqa: E402

# How many times each kind of message is replayed (fixed seed -> same demo every time).
REPEATS = {"scam": (2, 7), "legit": (1, 3), "otp_delivery": (1, 3), "ambiguous": (1, 2)}


def clear() -> int:
    with stats._db() as con:
        ids = [r[0] for r in con.execute("SELECT id FROM checks WHERE synthetic = 1")]
        for table in ("check_signals", "check_claims", "check_domains"):
            con.executemany(f"DELETE FROM {table} WHERE check_id = ?", [(i,) for i in ids])
        con.execute("DELETE FROM checks WHERE synthetic = 1")
    return len(ids)


def seed(days: int = 14) -> int:
    rng = random.Random(2026)
    rows = [json.loads(l) for l in (ROOT / "data" / "synthetic_messages.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    n = 0
    for r in rows:
        result = analyse_message(r["text"], r["lang"], use_llm=False)
        lo, hi = REPEATS[r["category"]]
        for _ in range(rng.randint(lo, hi)):
            when = now - timedelta(days=rng.randint(0, days - 1), hours=rng.randint(0, 12))
            stats.record_check(result, r["channel"], r["lang"], when=when, synthetic=True)
            n += 1
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--clear", action="store_true", help="remove demo rows only")
    args = ap.parse_args()
    if args.clear:
        print(f"removed {clear()} demo rows from {stats.DB_PATH}")
    else:
        print(f"removed {clear()} old demo rows, added {seed()} demo rows to {stats.DB_PATH}")
