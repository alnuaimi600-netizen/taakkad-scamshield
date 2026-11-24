"""End-to-end rules (no LLM). Messages are synthetic; links use .test domains."""
import pytest

from app.analyzer import analyse_message


def status(text, lang="ar"):
    return analyse_message(text, lang, use_llm=False)["status"]


def test_mockup_message_is_high():
    assert status("شحنتك معلّقة. ادفع 5 دراهم الآن عبر الرابط لتجنب الإلغاء: http://example-track.test/pay") == "high_suspicion"


# Rule 3: a request for card or OTP => high, even with an official link.
def test_official_link_plus_otp_request_is_high():
    msg = "Oasis Bank: to keep your account active, enter the OTP we sent you at https://oasisbank.test/verify"
    assert status(msg, "en") == "high_suspicion"


def test_official_link_plus_card_request_is_high():
    msg = "فالكون إكسبريس: لإكمال التوصيل أدخل رقم البطاقة هنا https://falcon-express.test/pay"
    assert status(msg) == "high_suspicion"


def test_send_me_the_code_no_link_is_high():
    assert status("هلا، وصلك كود على جوالك بالغلط، ارسله لي لو سمحت") == "high_suspicion"


# ...but a message that DELIVERS a code with "don't share" is not suspicious.
@pytest.mark.parametrize("msg", [
    "رمز التحقق الخاص بك هو 482913. لا تشارك هذا الرمز مع أي أحد.",
    "Your Oasis Bank verification code is 553201. Do not share it with anyone. Valid for 5 minutes.",
    "Use code 9921 to sign in to Najm Telecom. Never share this code; we will never ask for it.",
])
def test_code_delivery_is_not_suspicious(msg):
    r = analyse_message(msg, "en", use_llm=False)
    assert r["status"] == "no_visible_indicators"
    assert r["reasons"] == []


def test_official_link_clean_text_lists_what_was_checked():
    r = analyse_message("فالكون إكسبريس: طلبك في الطريق. تتبع الشحنة: https://falcon-express.test/track/88812", "ar", use_llm=False)
    assert r["status"] == "no_visible_indicators"
    assert any("فالكون" in c for c in r["checked"])
    assert r["not_guaranteed"]


def test_buy_sell_receive_money_scam():
    msg = "مرحبا، شفت إعلانك. حولت لك المبلغ، ادخل بيانات بطاقتك في الرابط لاستلام المبلغ: http://souq-waha-pay.test/receive"
    r = analyse_message(msg, "ar", use_llm=False)
    assert r["status"] == "high_suspicion"
    assert len(r["reasons"]) <= 3


def test_plain_personal_message():
    assert status("Hey are we still meeting at 7? I'm fine with the cafe near the mall.", "en") == "no_visible_indicators"


def test_shortener_alone_is_unclear():
    assert status("check this out https://bit.ly/3abcd", "en") == "unclear"


def test_never_says_safe():
    for msg in ["hello", "رمز التحقق 1234 لا تشاركه", "https://falcon-express.test/"]:
        for lang in ("ar", "en"):
            r = analyse_message(msg, lang, use_llm=False)
            assert r["status"] in {"high_suspicion", "unclear", "no_visible_indicators"}
            blob = " ".join([r["safe_action"], *r["checked"], *[x["text"] for x in r["reasons"]]]).lower()
            assert "is safe" not in blob
            # "آمنة" may only appear in the disclaimer "this does not mean it is safe".
            assert blob.replace("لا يعني أن الرسالة آمنة", "").count("آمن") == 0


def test_reasons_follow_ui_language():
    msg = "Falcon Express: pay AED 9 now https://falcon-pay.test/x"
    en = analyse_message(msg, "en", use_llm=False)["reasons"][0]["text"]
    ar = analyse_message(msg, "ar", use_llm=False)["reasons"][0]["text"]
    assert en.isascii() and not ar.isascii()


@pytest.mark.parametrize("payload", ["a." * 2500, "1-" * 2500, "www." + "a." * 2400, "a-" * 2500])
def test_crafted_long_input_is_fast(payload):
    # Regression: unbounded domain-label repetition made "a.a.a…" take ~3 s (ReDoS).
    import time
    start = time.perf_counter()
    analyse_message(payload[:5000], "en", use_llm=False)
    assert time.perf_counter() - start < 1.0


def test_analysis_sees_only_masked_text():
    r = analyse_message("Send your card 4111 1111 1111 1111 to http://x.test", "en", use_llm=False)
    assert "4111" not in r["masked_text"]
    assert "4111" not in str(r)


# The 0-100 risk score always sits inside its status band and never reaches 0.
@pytest.mark.parametrize("msg,expected", [
    ("شحنتك معلّقة. ادفع 5 دراهم الآن عبر الرابط لتجنب الإلغاء: http://example-track.test/pay", "high_suspicion"),
    ("https://bit.ly/3xYz", "unclear"),
    ("رمز التحقق الخاص بك هو 482913. لا تشارك هذا الرمز مع أي أحد.", "no_visible_indicators"),
])
def test_risk_score_stays_in_status_band(msg, expected):
    from app.scoring import RISK_BANDS
    r = analyse_message(msg, "ar", use_llm=False)
    lo, hi = RISK_BANDS[r["status"]]
    assert r["status"] == expected
    assert lo <= r["risk_score"] <= hi and r["risk_score"] > 0


@pytest.mark.parametrize("url", ["https://tamm-fines.test/pay", "https://uaepass.ae.login-verify.test"])
def test_link_alone_impersonating_uae_services_is_high(url):
    assert status(url, "en") == "high_suspicion"
