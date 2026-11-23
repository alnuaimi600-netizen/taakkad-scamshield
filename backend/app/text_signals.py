"""Rule-based text signals (Arabic + English), run on the masked text.

Each signal has a stable code, a weight (3 strong, 2 medium, 1 weak) and the
original words that triggered it, so the UI can highlight them.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .normalize import normalize_ar


@dataclass
class TextSignal:
    code: str
    weight: int
    evidence: list[str]


def _rx(*parts: str) -> re.Pattern:
    return re.compile("|".join(parts), re.IGNORECASE)


# All Arabic patterns are written in normalised form (see normalize_ar):
# ا instead of أ/إ/آ, ه instead of ة, ي instead of ى.
CODE_WORDS = _rx(
    r"\botp\b", r"\bcode\b", r"\bpasscode\b", r"\bverification\b", r"\bpin\b", r"\[code\]",
    r"رمز", r"الرمز", r"كود", r"الكود", r"رقم سري", r"الرقم السري", r"كلمه السر",
)
# Verbs that ask the reader to hand the code over.
GIVE_VERBS = _rx(
    r"\bsend\b", r"\bshare\b", r"\bgive\b", r"\bprovide\b", r"\breply\b", r"\bforward\b", r"\btell\b",
    r"\bread (?:it|the code)\b",
    r"ارسل", r"ابعث", r"ابعت", r"شارك", r"زودنا", r"زودني", r"اعطني", r"اعطنا", r"عطني", r"رد ب",
    r"قول لي", r"قل لي", r"اكد لي", r"اكد لنا", r"وصلك",
)
ENTER_VERBS = _rx(r"\benter\b", r"\btype\b", r"\bsubmit\b", r"ادخل", r"اكتب", r"سجل")
# Negated phrases ("do not share") are removed before looking for give-verbs.
NEGATED = _rx(
    r"\b(?:do not|don't|dont|never|not to)\s+(?:share|send|give|forward|tell|disclose|reply)\b[^.\n]*",
    r"\bno one\b[^.\n]*", r"\bnobody\b[^.\n]*",
    r"(?:لا|ولا|عدم|يمنع)\s+(?:تشارك|تشاركه|تشاركها|مشاركه|ترسل|ترسله|ارسال|تعطي|تعطيه|تفصح|تبلغ|تخبر)[^.\n]*",
    r"لن\s+(?:نطلب|يطلب)[^.\n]*", r"\bwill never ask\b[^.\n]*", r"\bnever ask\b[^.\n]*",
)

CARD = _rx(
    r"card (?:number|details|info|information|data)", r"\bcvv\b", r"\bcvc\b", r"security code",
    r"expiry", r"expiration date", r"\[card\]", r"debit card", r"credit card", r"your card",
    r"رقم البطاقه", r"بيانات البطاقه", r"معلومات البطاقه", r"تفاصيل البطاقه", r"بيانات بطاقتك",
    r"رقم بطاقتك", r"بطاقتك البنكيه", r"البطاقه البنكيه", r"بطاقه الصراف", r"بطاقه الدفع",
    r"تاريخ الانتهاء", r"تاريخ انتهاء", r"الرمز السري", r"الرقم السري للبطاقه",
)
CARD_ACTION = _rx(
    r"\benter\b", r"\bprovide\b", r"\bsend\b", r"\bupdate\b", r"\bconfirm\b", r"\bverify\b", r"\bfill\b",
    r"\bshare\b", r"\bgive\b", r"\bsubmit\b", r"\btype\b", r"\badd\b",
    r"ادخل", r"ارسل", r"حدث", r"تحديث", r"اكد", r"تاكيد", r"عبي", r"زودنا", r"شارك", r"اكتب", r"ابعث",
    r"اعطني", r"سجل", r"تحقق",
)
PERSONAL = _rx(
    r"emirates id", r"\bid number\b", r"passport", r"\bpassword\b", r"online banking",
    r"\[emirates_id\]", r"\biban\b",
    r"رقم الهويه", r"الهويه الاماراتيه", r"صوره الهويه", r"جواز", r"كلمه المرور", r"كلمه السر",
    r"اسم المستخدم", r"الايبان",
)
PERSONAL_ACTION = CARD_ACTION

PAYMENT = _rx(
    r"\bpay\b", r"\bpayment\b", r"\bfee\b", r"\bfees\b", r"\bcharge\b", r"\bduty\b", r"customs",
    r"\baed\s?\d", r"\d+(?:\.\d+)?\s?aed\b", r"\bdhs?\b", r"\btransfer\b", r"settle",
    r"ادفع", r"دفع", r"رسوم", r"سداد", r"سدد", r"درهم", r"دراهم", r"مبلغ", r"تحويل", r"جمارك",
)
URGENCY = _rx(
    r"\burgent", r"immediately", r"right now", r"(?:pay|click|act|update|verify|confirm) now",
    r"within \d+ (?:hours?|minutes?|days?)", r"last chance", r"final notice", r"before it(?:'s| is) too late",
    r"\basap\b", r"limited time",
    r"فورا", r"فوري", r"(?:ادفع|اضغط|حدث|سدد|ادخل) الان", r"الان قبل", r"حالا", r"خلال \d+ ?(?:ساعه|ساعات|دقيقه|دقائق|يوم|ايام)",
    r"خلال ساعه", r"قبل نهايه اليوم", r"اخر فرصه", r"اخر تنبيه", r"انذار نهائي", r"عاجل", r"بسرعه", r"قبل فوات",
)
THREAT = _rx(
    r"will be (?:cancel+ed|suspended|blocked|returned|closed|deleted|frozen)", r"\bsuspend", r"\bblocked\b",
    r"legal action", r"\barrest", r"penalt", r"traffic fine", r"a fine of", r"pay (?:the |your )?fine", r"account (?:is |has been )?(?:locked|limited)",
    r"سيتم (?:الغاء|ايقاف|تعليق|حظر|اغلاق|حذف|تجميد|ارجاع)", r"ايقاف حسابك", r"تعليق حسابك",
    r"حظر", r"لتجنب", r"تجنب الغاء", r"\bto avoid\b", r"غرامه", r"مخالفه", r"اجراء قانوني", r"الاجراءات القانونيه", r"اعاده الشحنه",
)
PRIZE = _rx(
    r"you(?:'ve| have)? won", r"\bwinner\b", r"\bprize\b", r"\breward\b", r"congratulations", r"\bgift\b",
    r"cash ?back", r"\brefund\b", r"\bbonus\b", r"lucky",
    r"ربحت", r"فزت", r"الفائز", r"جائزه", r"مبروك", r"هديه", r"مكافاه", r"استرداد", r"استرجاع مبلغ",
)
# Time words that only count as pressure next to a payment request.
SOFT_URGENCY = _rx(r"\bnow\b", r"\btoday\b", r"\btonight\b", r"الان", r"اليوم", r"حالا", r"الحين")
# Buy/sell scam: "to RECEIVE the money, enter your card / pay a fee".
RECEIVE_MONEY = _rx(
    r"(?:to |in order to )?receive (?:the |your )?(?:money|payment|amount|funds)", r"release (?:the )?(?:payment|funds)",
    r"لاستلام المبلغ", r"لاستلام الفلوس", r"لاستلام المال", r"لاستلام الدفعه", r"استلام المبلغ", r"لتحويل المبلغ لك",
)


def _hits(pattern: re.Pattern, text: str) -> list[str]:
    return list(dict.fromkeys(m.group(0) for m in pattern.finditer(text)))


def _evidence_in_original(original: str, normalized_hits: list[str]) -> list[str]:
    """Map normalised hits back to the words the user actually sees (best effort)."""
    out: list[str] = []
    norm_orig = normalize_ar(original)
    for h in normalized_hits:
        # Arabic folding can change length (diacritics). Find the hit in a
        # per-character normalised copy and slice the original by those offsets.
        idx = norm_orig.find(h)
        if idx == -1:
            continue
        mapping = _norm_index_map(original)
        start = mapping[idx] if idx < len(mapping) else None
        end_i = idx + len(h) - 1
        end = mapping[end_i] + 1 if end_i < len(mapping) else None
        if start is not None and end is not None:
            out.append(original[start:end])
    return list(dict.fromkeys(out))


def _norm_index_map(original: str) -> list[int]:
    """For each char of normalize_ar(original), the index of its source char."""
    mapping: list[int] = []
    for i, ch in enumerate(original):
        mapping.extend([i] * len(normalize_ar(ch)))
    return mapping


def detect(masked_text: str, has_link: bool) -> list[TextSignal]:
    norm = normalize_ar(masked_text)
    signals: list[TextSignal] = []

    def add(code: str, weight: int, hits: list[str]) -> None:
        signals.append(TextSignal(code, weight, _evidence_in_original(masked_text, hits)))

    # --- OTP / code request -------------------------------------------------
    delivered_code = "[code]" in norm
    stripped = NEGATED.sub(" ", norm)
    code_hits = _hits(CODE_WORDS, stripped)
    if code_hits:
        give = _hits(GIVE_VERBS, stripped)
        enter = _hits(ENTER_VERBS, stripped)
        if give:
            add("asks_otp", 3, code_hits[:2] + give[:1])
        elif enter and has_link and not delivered_code:
            add("asks_otp", 3, code_hits[:2] + enter[:1])
    if delivered_code and not any(s.code == "asks_otp" for s in signals):
        # A message that hands you a code and tells you not to share it is normal.
        signals.append(TextSignal("delivers_code", 0, []))

    # --- card details ---------------------------------------------------------
    card_hits = _hits(CARD, stripped)
    if card_hits and (_hits(CARD_ACTION, stripped) or has_link):
        add("asks_card", 3, card_hits[:2])

    # --- other personal secrets ----------------------------------------------
    pers = _hits(PERSONAL, stripped)
    if pers and (_hits(PERSONAL_ACTION, stripped) or has_link):
        add("asks_personal", 3, pers[:2])

    # --- money ----------------------------------------------------------------
    pay = _hits(PAYMENT, norm)
    if pay:
        add("payment_request", 2 if has_link else 1, pay[:2])
    recv = _hits(RECEIVE_MONEY, norm)
    if recv and has_link:
        add("receive_money_link", 3, recv[:1])

    # --- pressure ---------------------------------------------------------------
    urg = _hits(URGENCY, norm)
    if not urg and pay:
        urg = _hits(SOFT_URGENCY, norm)
    if urg:
        add("urgency", 2, urg[:2])
    thr = _hits(THREAT, norm)
    if thr:
        add("threat", 2, thr[:2])
    prize = _hits(PRIZE, norm)
    if prize:
        add("prize", 2, prize[:2])

    return signals
