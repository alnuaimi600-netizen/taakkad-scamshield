"""Anonymous, aggregate statistics for the authority dashboard.

What is stored per check (and nothing else):
  date + hour bucket, state, channel, UI language, signal codes, the categories /
  entity ids the message claimed to be, and the registered domain of links that were
  NOT on the official list.
What is NEVER stored: message text, masked text, IP address, user agent, any id
that links two checks to the same person.

Also holds the two-way link with the authority:
  * confirmed_domains - domains staff confirmed as fraudulent (raise the verdict)
  * alerts            - public warnings staff publish to the app

Storage: SQLite file (stdlib, no server). Set TAAKKAD_STATS=0 to turn recording off.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("TAAKKAD_DB", Path(__file__).resolve().parents[1] / "storage" / "taakkad.db"))
_lock = threading.Lock()
_cache_confirmed: set[str] | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS checks (
  id INTEGER PRIMARY KEY,
  day TEXT NOT NULL, hour INTEGER NOT NULL,
  status TEXT NOT NULL, channel TEXT, lang TEXT,
  synthetic INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS check_signals (check_id INTEGER NOT NULL, code TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS check_claims (check_id INTEGER NOT NULL, category TEXT, entity_id TEXT);
CREATE TABLE IF NOT EXISTS check_domains (check_id INTEGER NOT NULL, domain TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS confirmed_domains (domain TEXT PRIMARY KEY, added_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY, created_at TEXT NOT NULL,
  title_ar TEXT NOT NULL, title_en TEXT NOT NULL,
  body_ar TEXT NOT NULL, body_en TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS ix_checks_day ON checks(day);
"""


def enabled() -> bool:
    return os.environ.get("TAAKKAD_STATS", "1") != "0"


@contextmanager
def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        con = sqlite3.connect(DB_PATH)
        try:
            con.executescript(SCHEMA)
            yield con
            con.commit()
        finally:
            con.close()


def reset_cache() -> None:
    global _cache_confirmed
    _cache_confirmed = None


# --- recording -------------------------------------------------------------

def record_check(result: dict, channel: str | None, lang: str, when: datetime | None = None, synthetic: bool = False) -> None:
    """Record one check from the analyzer result. Only aggregate fields are read."""
    if not enabled():
        return
    when = when or datetime.now(timezone.utc)
    signals = {r["code"] for r in result.get("reasons", [])} | set(result.get("_all_codes", []))
    claims = result.get("_claims", [])  # [(category, entity_id|None)]
    domains = {l["domain"] for l in result.get("links", []) if not l.get("official") and l.get("domain")}
    with _db() as con:
        cur = con.execute(
            "INSERT INTO checks(day, hour, status, channel, lang, synthetic) VALUES (?,?,?,?,?,?)",
            (when.date().isoformat(), when.hour, result["status"], channel, lang, int(synthetic)),
        )
        cid = cur.lastrowid
        con.executemany("INSERT INTO check_signals VALUES (?,?)", [(cid, s) for s in signals])
        con.executemany("INSERT INTO check_claims VALUES (?,?,?)", [(cid, c, e) for c, e in claims])
        con.executemany("INSERT INTO check_domains VALUES (?,?)", [(cid, d) for d in domains])


# --- authority -> public ----------------------------------------------------

def confirmed_domains() -> set[str]:
    global _cache_confirmed
    if _cache_confirmed is None:
        try:
            with _db() as con:
                _cache_confirmed = {r[0] for r in con.execute("SELECT domain FROM confirmed_domains")}
        except sqlite3.Error:
            _cache_confirmed = set()
    return _cache_confirmed


def confirm_domain(domain: str) -> None:
    with _db() as con:
        con.execute("INSERT OR IGNORE INTO confirmed_domains VALUES (?,?)", (domain.lower(), datetime.now(timezone.utc).isoformat()))
    reset_cache()


def unconfirm_domain(domain: str) -> None:
    with _db() as con:
        con.execute("DELETE FROM confirmed_domains WHERE domain = ?", (domain.lower(),))
    reset_cache()


def add_alert(title_ar: str, title_en: str, body_ar: str, body_en: str) -> int:
    with _db() as con:
        cur = con.execute(
            "INSERT INTO alerts(created_at, title_ar, title_en, body_ar, body_en) VALUES (?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(timespec="minutes"), title_ar, title_en, body_ar, body_en),
        )
        return cur.lastrowid


def set_alert_active(alert_id: int, active: bool) -> None:
    with _db() as con:
        con.execute("UPDATE alerts SET active = ? WHERE id = ?", (int(active), alert_id))


def list_alerts(active_only: bool) -> list[dict]:
    with _db() as con:
        q = "SELECT id, created_at, title_ar, title_en, body_ar, body_en, active FROM alerts"
        q += " WHERE active = 1" if active_only else ""
        rows = con.execute(q + " ORDER BY id DESC").fetchall()
    keys = ("id", "created_at", "title_ar", "title_en", "body_ar", "body_en", "active")
    return [dict(zip(keys, r)) | {"active": bool(r[6])} for r in rows]


# --- dashboard aggregates ---------------------------------------------------

def summary(days: int = 14) -> dict:
    days = max(1, min(days, 90))
    start = (date.today() - timedelta(days=days - 1)).isoformat()
    with _db() as con:
        rows = con.execute("SELECT id, day, status, channel, synthetic FROM checks WHERE day >= ?", (start,)).fetchall()
        ids = [r[0] for r in rows]
        sig = con.execute(
            "SELECT s.code, COUNT(*) FROM check_signals s JOIN checks c ON c.id = s.check_id WHERE c.day >= ? GROUP BY s.code",
            (start,)).fetchall()
        claims = con.execute(
            "SELECT cl.category, cl.entity_id, COUNT(*) FROM check_claims cl JOIN checks c ON c.id = cl.check_id "
            "WHERE c.day >= ? AND c.status != 'no_visible_indicators' GROUP BY cl.category, cl.entity_id", (start,)).fetchall()
        doms = con.execute(
            "SELECT d.domain, COUNT(*), MAX(c.day), SUM(c.status = 'high_suspicion') FROM check_domains d "
            "JOIN checks c ON c.id = d.check_id WHERE c.day >= ? GROUP BY d.domain ORDER BY COUNT(*) DESC LIMIT 15",
            (start,)).fetchall()
    confirmed = confirmed_domains()

    by_status = Counter(r[2] for r in rows)
    by_channel = Counter(r[3] or "unknown" for r in rows)
    daily: dict[str, Counter] = defaultdict(Counter)
    for _, day, status, _, _ in rows:
        daily[day][status] += 1
    series = []
    for i in range(days):
        d = (date.today() - timedelta(days=days - 1 - i)).isoformat()
        c = daily.get(d, Counter())
        series.append({"day": d, "high_suspicion": c["high_suspicion"], "unclear": c["unclear"],
                       "no_visible_indicators": c["no_visible_indicators"]})

    cat_counts = Counter()
    ent_counts = Counter()
    for cat, ent, n in claims:
        if ent:
            ent_counts[ent] += n
        elif cat:
            cat_counts[cat] += n

    from .entities import load_catalog
    from .url_checks import SHORTENERS
    names = {e.id: (e.name_ar, e.name_en) for e in load_catalog().entities}
    return {
        "days": days,
        "total": len(ids),
        "synthetic": sum(r[4] for r in rows),
        "by_status": {k: by_status.get(k, 0) for k in ("high_suspicion", "unclear", "no_visible_indicators")},
        "by_channel": dict(by_channel),
        "daily": series,
        "top_signals": [{"code": c, "count": n} for c, n in sorted(sig, key=lambda x: -x[1])[:8]],
        "top_entities": [{"entity_id": e, "count": n, "name_ar": names.get(e, (e, e))[0], "name_en": names.get(e, (e, e))[1]}
                         for e, n in ent_counts.most_common(8)],
        "top_categories": [{"category": c, "count": n} for c, n in cat_counts.most_common(6)],
        "top_domains": [{"domain": d, "count": n, "last_seen": last, "high": int(h or 0), "confirmed": d in confirmed,
                         "shortener": d in SHORTENERS}
                        for d, n, last, h in doms],
    }
