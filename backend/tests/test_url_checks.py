"""Only reserved/fake domains (.test, .example) and shortener *names* are used.
Nothing is fetched: url_checks has no network code."""
from app.url_checks import check_message_links, check_url, extract_urls, registered_domain


def codes(url):
    return {f.code for f in check_url(url).findings}


def test_extract_urls_with_and_without_scheme():
    text = "go to https://a.test/x, or www.b.test. also c-d.example/pay! not e.g. or Dr.Ahmed"
    assert extract_urls(text) == ["https://a.test/x", "www.b.test", "c-d.example/pay"]


def test_registered_domain():
    assert registered_domain("pay.track.aramex-x.test") == "aramex-x.test"
    assert registered_domain("www.something.gov.ae") == "something.gov.ae"


def test_ip_host():
    assert "ip_host" in codes("http://192.0.2.10/pay")


def test_shortener():
    assert "shortener" in codes("https://bit.ly/3xYz")


def test_punycode():
    assert "punycode" in codes("https://xn--frlcon-express-abc.test/")


def test_no_https():
    assert "no_https" in codes("http://falcon-express.test/")


def test_official_demo_domain_is_clean():
    r = check_url("https://track.falcon-express.test/88812")
    assert r.official_for == ["falcon_express"]
    assert r.findings == []


def test_lookalike_digit_swap():
    assert "lookalike" in codes("https://falc0n-express.test/upd")


def test_lookalike_typo():
    assert "lookalike" in codes("https://oasisbankk.test/login")


def test_brand_inside_other_domain():
    assert "brand_in_host" in codes("https://oasisbank.secure-login.test/")
    assert "brand_in_host" in codes("https://oasis-bank-verify.test/")


def test_unusual_tld():
    assert "unusual_tld" in codes("https://parcel-fee.xyz/")


def test_claimed_entity_mismatch():
    _, findings, claimed = check_message_links("Falcon Express: pay the fee", ["https://parcel-fees.test/pay"])
    assert [e.id for e in claimed] == ["falcon_express"]
    assert [f.code for f in findings] == ["link_mismatch_claimed"]


def test_claimed_entity_match():
    _, findings, _ = check_message_links("فالكون إكسبريس: تتبع شحنتك", ["https://falcon-express.test/t/1"])
    assert findings == []


def test_alias_inside_longer_name_is_not_a_claim():
    from app.entities import claimed_entities
    assert [e.id for e in claimed_entities("نجم للاتصالات: تم تجديد باقتك")] == ["najm_telecom"]
    assert [e.id for e in claimed_entities("اتصالات: فاتورتك متأخرة")] == ["etisalat"]


def test_generic_claim_unknown_link():
    _, findings, _ = check_message_links("شحنتك معلقة", ["http://example-track.test/pay"])
    assert [f.code for f in findings] == ["link_unknown_for_claim"]


def test_at_sign_trick_survives_masking_and_is_high():
    from app.analyzer import analyse_message
    r = analyse_message("https://oasisbank.test@login-check.test/session", "en", use_llm=False)
    assert r["status"] == "high_suspicion"
    assert "at_sign" in r["links"][0]["flags"]


def test_plain_email_is_still_masked():
    from app.masking import mask
    assert "ali@mail.test" not in mask("راسلني على ali@mail.test").text


def test_malformed_bracket_host_does_not_crash():
    from app.analyzer import analyse_message
    assert analyse_message("https://[nothing]/x", "en", use_llm=False)["status"] in {
        "high_suspicion", "unclear", "no_visible_indicators"}
