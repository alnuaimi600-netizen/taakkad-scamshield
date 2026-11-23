"""All numbers here are synthetic (test card numbers / made-up IDs)."""
from app.masking import luhn_valid, mask


def test_luhn():
    assert luhn_valid("4111111111111111")
    assert not luhn_valid("4111111111111112")


def test_card_masked_with_spaces_and_dashes():
    r = mask("card 4111 1111 1111 1111 and 5555-5555-5555-4444")
    assert "4111" not in r.text and "5555" not in r.text
    assert r.counts["card"] == 2


def test_non_luhn_long_number_kept():
    # e.g. a tracking number that is not a card
    assert "1234567890123" in mask("tracking 1234567890123").text


def test_emirates_id_before_card():
    r = mask("ID 784-1990-1234567-1 and 784199012345671")
    assert r.counts == {"emirates_id": 2}


def test_iban():
    r = mask("IBAN AE07 0331 2345 6789 0123 456")
    assert r.counts.get("iban") == 1 and "0331" not in r.text


def test_phones_uae_and_international():
    r = mask("call 050 123 4567 or +971 50 765 4321 or 00971501112233 or 04 123 4567")
    assert r.counts.get("phone") == 4
    assert "[PHONE]" in r.text


def test_arabic_indic_digits_are_masked():
    r = mask("بطاقتي ٤١١١ ١١١١ ١١١١ ١١١١ وجوالي ٠٥٠١٢٣٤٥٦٧")
    assert r.counts.get("card") == 1 and r.counts.get("phone") == 1


def test_email_masked():
    assert mask("write to someone@example.test").counts == {"email": 1}


def test_delivered_code_masked():
    r = mask("رمز التحقق الخاص بك هو 482913. لا تشاركه")
    assert "482913" not in r.text and "[CODE]" in r.text
    r = mask("Your OTP is 7712")
    assert "7712" not in r.text


def test_urls_survive_masking():
    url = "https://falcon-express.test/track/05012345678"
    r = mask(f"track here {url}")
    assert url in r.text


def test_invisible_direction_marks_removed():
    # OCR output often wraps words and links in LRM/RLM marks.
    r = mask("‎http://example-track.test/pay‏ ‮card‬")
    assert r.text == "http://example-track.test/pay card"


def test_short_sender_numbers_untouched():
    assert mask("Pay AED 25 by 5pm").text == "Pay AED 25 by 5pm"
