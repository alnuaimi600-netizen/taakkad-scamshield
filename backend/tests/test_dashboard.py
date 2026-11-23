"""Authority dashboard: anonymity of stats, staff-only access, two-way link."""
import sqlite3

from fastapi.testclient import TestClient

from app import stats
from app.main import app

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-only-token"}


def _all_db_text() -> str:
    con = sqlite3.connect(stats.DB_PATH)
    out = []
    for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        out += [repr(r) for r in con.execute(f"SELECT * FROM {table}")]
    con.close()
    return "\n".join(out)


def test_stats_never_store_message_text_or_numbers():
    secret_words = "ZEBRA-PASSPHRASE"
    client.post("/api/check", json={
        "text": f"Falcon Express {secret_words}: enter card 4111 1111 1111 1111 at https://falcon-pay-now.test/x call 050 123 4567",
        "lang": "en", "channel": "sms"})
    dump = _all_db_text()
    assert "ZEBRA" not in dump and "4111" not in dump and "123 4567" not in dump
    assert "falcon-pay-now.test" in dump  # only the unofficial link domain is kept
    assert "asks_card" in dump


def test_response_has_no_internal_fields():
    body = client.post("/api/check", json={"text": "hello"}).json()
    assert not any(k.startswith("_") for k in body)


def test_admin_requires_token():
    assert client.get("/api/admin/stats").status_code == 401
    assert client.get("/api/admin/stats", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.post("/api/admin/confirmed-domains", json={"domain": "x.test"}).status_code == 401
    assert client.get("/api/admin/stats", headers=AUTH).status_code == 200


def test_summary_counts():
    client.post("/api/check", json={"text": "شحنتك معلقة ادفع 5 دراهم الآن http://parcel-x.test/pay", "channel": "whatsapp"})
    s = client.get("/api/admin/stats", headers=AUTH).json()
    assert s["total"] >= 1
    assert s["by_status"]["high_suspicion"] >= 1
    assert any(d["domain"] == "parcel-x.test" for d in s["top_domains"])
    assert len(s["daily"]) == 14


def test_confirmed_domain_raises_verdict_and_can_be_removed():
    msg = "check this https://plain-site.test/page"
    assert client.post("/api/check", json={"text": msg, "lang": "en"}).json()["status"] == "no_visible_indicators"
    client.post("/api/admin/confirmed-domains", json={"domain": "plain-site.test"}, headers=AUTH)
    r = client.post("/api/check", json={"text": msg, "lang": "en"}).json()
    assert r["status"] == "high_suspicion"
    assert r["reasons"][0]["code"] == "confirmed_by_authority"
    client.delete("/api/admin/confirmed-domains/plain-site.test", headers=AUTH)
    assert client.post("/api/check", json={"text": msg, "lang": "en"}).json()["status"] == "no_visible_indicators"


def test_confirmed_domain_validation():
    bad = client.post("/api/admin/confirmed-domains", json={"domain": "<script>"}, headers=AUTH)
    assert bad.status_code == 422
    # A shortener or an official domain must never be marked as fraud.
    assert client.post("/api/admin/confirmed-domains", json={"domain": "bit.ly"}, headers=AUTH).status_code == 400
    assert client.post("/api/admin/confirmed-domains", json={"domain": "falcon-express.test"}, headers=AUTH).status_code == 400


def test_ip_link_kept_whole():
    from app.url_checks import registered_domain
    assert registered_domain("192.0.2.44") == "192.0.2.44"


def test_alerts_flow():
    created = client.post("/api/admin/alerts", headers=AUTH, json={
        "title_ar": "تحذير", "title_en": "Warning",
        "body_ar": "رسائل تنتحل شركات الشحن", "body_en": "Messages impersonating couriers"}).json()
    public = client.get("/api/alerts?lang=en").json()
    assert any(a["id"] == created["id"] and a["title"] == "Warning" for a in public)
    client.post(f"/api/admin/alerts/{created['id']}/active?active=false", headers=AUTH)
    assert all(a["id"] != created["id"] for a in client.get("/api/alerts").json())


def test_stats_can_be_disabled(monkeypatch):
    monkeypatch.setenv("TAAKKAD_STATS", "0")
    before = client.get("/api/admin/stats", headers=AUTH).json()["total"]
    client.post("/api/check", json={"text": "hello again"})
    assert client.get("/api/admin/stats", headers=AUTH).json()["total"] == before
