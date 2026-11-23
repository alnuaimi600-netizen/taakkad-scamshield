import json
import logging

from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["ok"] is True


def test_check_returns_masked_only(caplog):
    caplog.set_level(logging.DEBUG)
    secret = "4111 1111 1111 1111"
    res = client.post("/api/check", json={"text": f"Enter card {secret} at http://pay.test", "lang": "en"})
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "high_suspicion"
    assert secret not in json.dumps(body)
    assert secret not in caplog.text  # nothing logs the message
    assert body["saved"] is False
    assert res.headers["cache-control"] == "no-store"


def test_empty_and_too_long_rejected():
    assert client.post("/api/check", json={"text": ""}).status_code == 422
    assert client.post("/api/check", json={"text": "a" * 5001}).status_code == 422


def test_opt_in_saves_masked_text_only(tmp_path, monkeypatch):
    f = tmp_path / "opt.jsonl"
    monkeypatch.setattr(main, "OPT_IN_FILE", f)
    client.post("/api/check", json={"text": "call 050 123 4567", "save_consent": False})
    assert not f.exists()
    client.post("/api/check", json={"text": "call 050 123 4567", "save_consent": True})
    saved = f.read_text(encoding="utf-8")
    assert "[PHONE]" in saved and "123 4567" not in saved


def test_report_bank_first_and_remask():
    res = client.post("/api/report", json={
        "masked_text": "pay here, my number 050 123 4567",
        "urls": ["http://pay.test"], "channel": "sms", "what_happened": "paid", "lang": "en",
    }).json()
    assert res["bank_first"]
    assert "123 4567" not in res["report_text"]
    assert res["channel"]["info_url"].startswith("https://u.ae/")


def test_report_no_bank_message_when_not_clicked():
    res = client.post("/api/report", json={"masked_text": "x", "what_happened": "not_clicked"}).json()
    assert res["bank_first"] is None
