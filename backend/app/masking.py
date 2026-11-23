"""Mask sensitive data BEFORE any analysis or LLM call.

Masked: payment card numbers (Luhn-valid), Emirates ID (784-YYYY-NNNNNNN-C),
UAE IBANs (AE..), phone numbers, e-mail addresses, and one-time codes that a
message delivers. URLs are left intact because link analysis needs them.

The function never returns the original values, only the masked text and a
count per type.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Arabic-Indic (U+0660..) and Extended/Persian (U+06F0..) digits -> ASCII.
# One char maps to one char, so offsets stay stable.
_DIGIT_MAP = {ord(c): str(i) for i, c in enumerate("٠١٢٣٤٥٦٧٨٩")}
_DIGIT_MAP.update({ord(c): str(i) for i, c in enumerate("۰۱۲۳۴۵۶۷۸۹")})

# Bare domains (no scheme) are only recognised with a known TLD, so that
# "Dr.Ahmed" or "e.g." are not treated as links.
BARE_TLDS = (
    "com|net|org|ae|info|biz|xyz|top|site|online|shop|store|click|link|live|app|io|co|me|"
    "test|example|ly|gd|at|cc|ru|cn|tk|ml|ga|cf|gq|icu|buzz|sbs|cfd|rest|vip|club|page|"
    "support|help|services|pay|win|loan|work|monster|cam|ws|su|in|uk|sa|qa|om|kw|bh"
)
URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s<>\"'،]+"
    # {1,8} labels (not +): unbounded repetition made "a.a.a.…" inputs quadratic (ReDoS).
    r"|\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.){1,8}(?:" + BARE_TLDS + r"|xn--[a-z0-9-]+)\b"
    r"(?:[/?#][^\s<>\"'،]*)?",
    re.IGNORECASE,
)
TRAILING_PUNCT = ".,;:!?)]}»\"'؟،"

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
EMIRATES_ID_RE = re.compile(r"\b784[\s-]?\d{4}[\s-]?\d{7}[\s-]?\d\b")
IBAN_RE = re.compile(r"\bAE\d{2}(?:[\s-]?\d){19}\b", re.IGNORECASE)
CARD_CANDIDATE_RE = re.compile(r"\b\d(?:[\s-]?\d){12,18}\b")
PHONE_RE = re.compile(
    r"(?<![\w+])(?:\+|00)\d{1,3}[\s-]?\(?\d{1,4}\)?(?:[\s-]?\d){5,10}\b"  # international
    r"|\b0(?:5\d|[2-4679])[\s-]?\d{3}[\s-]?\d{4}\b"                     # UAE local
    r"|\b800[\s-]?\d{3,7}\b"                                              # UAE toll-free
)
# A code that the message delivers, e.g. "Your code is 482913" / "رمز التحقق: 4829".
CODE_RE = re.compile(
    r"(?P<kw>\b(?:otp|code|passcode|pin|verification)\b|رمز|كود|الرمز|الكود)"
    r"(?P<gap>[^\d\n]{0,25}?)(?P<code>\b\d{4,8}\b)",
    re.IGNORECASE,
)

TOKENS = {
    "card": "[CARD]",
    "emirates_id": "[EMIRATES_ID]",
    "iban": "[IBAN]",
    "phone": "[PHONE]",
    "email": "[EMAIL]",
    "code": "[CODE]",
}


@dataclass
class MaskResult:
    text: str
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return sum(self.counts.values())


# Invisible direction / zero-width characters. OCR output is full of LRM/RLM, and
# they can also be used to disguise a link. Removed before anything else.
_INVISIBLE = re.compile(r"[​-‏‪-‮⁦-⁩؜﻿]")


def normalize_digits(text: str) -> str:
    return _INVISIBLE.sub("", text).translate(_DIGIT_MAP)


def luhn_valid(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _protect_urls(text: str) -> tuple[str, list[str]]:
    urls: list[str] = []

    def keep(m: re.Match) -> str:
        urls.append(m.group(0))
        return f"\x00{len(urls) - 1}\x00"

    return URL_RE.sub(keep, text), urls


def _restore_urls(text: str, urls: list[str]) -> str:
    return re.sub(r"\x00(\d+)\x00", lambda m: urls[int(m.group(1))], text)


def mask(text: str) -> MaskResult:
    counts: dict[str, int] = {}

    def bump(kind: str) -> str:
        counts[kind] = counts.get(kind, 0) + 1
        return TOKENS[kind]

    work = normalize_digits(text).replace("\x00", "")
    # E-mails first: they look like URLs to the URL pattern.
    work = EMAIL_RE.sub(lambda m: bump("email"), work)
    work, urls = _protect_urls(work)

    # Order matters: Emirates ID (15 digits, Luhn check digit) before cards.
    work = EMIRATES_ID_RE.sub(lambda m: bump("emirates_id"), work)
    work = IBAN_RE.sub(lambda m: bump("iban"), work)

    def card_or_keep(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and luhn_valid(digits):
            return bump("card")
        return m.group(0)

    work = CARD_CANDIDATE_RE.sub(card_or_keep, work)
    work = PHONE_RE.sub(lambda m: bump("phone"), work)
    work = CODE_RE.sub(lambda m: m.group("kw") + m.group("gap") + bump("code"), work)

    return MaskResult(text=_restore_urls(work, urls), counts=counts)
