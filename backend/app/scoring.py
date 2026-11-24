"""Combine link + text signals into one of three states and up to 3 reasons.

States (the app never says "safe"):
  high_suspicion        several strong signals, or ANY request for card / OTP
  unclear               few or conflicting signals
  no_visible_indicators nothing found - which does not mean safe
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .entities import Entity
from .text_signals import TextSignal
from .url_checks import LinkFinding, LinkReport

HIGH = "high_suspicion"
UNCLEAR = "unclear"
NONE = "no_visible_indicators"

# Plain-language reasons. {entity} is replaced by the claimed entity's name.
REASONS: dict[str, dict[str, str]] = {
    "confirmed_by_authority": {
        "ar": "هذا الرابط أكّدته الجهة الأمنية كرابط احتيالي.",
        "en": "The security authority has confirmed this link as fraudulent.",
    },
    "asks_card": {
        "ar": "تطلب منك بيانات بطاقتك البنكية. الجهات الرسمية لا تطلبها عبر رسالة أو رابط.",
        "en": "It asks for your card details. Real organisations don't ask for them by message or link.",
    },
    "asks_otp": {
        "ar": "تطلب منك رمز التحقق (OTP). هذا الرمز لك وحدك، ولا تشاركه مع أي أحد.",
        "en": "It asks for your verification code (OTP). That code is for you only. Never share it.",
    },
    "asks_personal": {
        "ar": "تطلب بيانات شخصية حساسة مثل الهوية أو كلمة المرور.",
        "en": "It asks for sensitive personal details like your ID or password.",
    },
    "receive_money_link": {
        "ar": "تطلب منك إدخال بياناتك عبر رابط حتى «تستلم» مبلغاً. استلام المال لا يحتاج بطاقتك.",
        "en": "It asks you to use a link to \"receive\" money. Receiving money never needs your card.",
    },
    "link_mismatch_claimed": {
        "ar": "الرابط لا يطابق الموقع الرسمي لـ{entity} المذكورة في الرسالة.",
        "en": "The link doesn't match the official website of {entity}, which the message claims to be.",
    },
    "link_unknown_for_claim": {
        "ar": "الرسالة تتكلم عن شحنة أو بنك أو جهة رسمية، لكن الرابط ليس من المواقع الرسمية التي نعرفها.",
        "en": "The message talks about a delivery, bank or official body, but the link isn't one of the official websites we know.",
    },
    "lookalike": {
        "ar": "الرابط يشبه اسم جهة معروفة مع تغيير بسيط في الحروف.",
        "en": "The link looks like a known organisation's name with small letter changes.",
    },
    "brand_in_host": {
        "ar": "الرابط يضع اسم جهة معروفة داخل موقع آخر لا يتبع لها.",
        "en": "The link puts a known organisation's name inside a different website.",
    },
    "punycode": {
        "ar": "الرابط يستخدم حروفاً خاصة قد تخدع العين.",
        "en": "The link uses special characters that can fool the eye.",
    },
    "at_sign": {
        "ar": "الرابط مكتوب بطريقة تخفي الموقع الحقيقي.",
        "en": "The link is written in a way that hides the real website.",
    },
    "ip_host": {
        "ar": "الرابط رقم (عنوان IP) وليس اسم موقع.",
        "en": "The link is a raw number (IP address) instead of a website name.",
    },
    "shortener": {
        "ar": "الرابط مختصر ويخفي الموقع الذي سيفتحه.",
        "en": "The link is shortened and hides where it really goes.",
    },
    "unusual_tld": {
        "ar": "نهاية الرابط غير معتادة للجهات الرسمية.",
        "en": "The link ends in an unusual way for official organisations.",
    },
    "payment_request": {
        "ar": "تطلب منك دفع مبلغ.",
        "en": "It asks you to pay money.",
    },
    "urgency": {
        "ar": "تستعجلك حتى لا تأخذ وقتك في التفكير.",
        "en": "It rushes you so you don't stop to think.",
    },
    "threat": {
        "ar": "تهددك بعواقب (إلغاء، إيقاف، غرامة) لتضغط عليك.",
        "en": "It threatens consequences (cancellation, blocking, fines) to pressure you.",
    },
    "prize": {
        "ar": "تعدك بجائزة أو مبلغ لم تتوقعه.",
        "en": "It promises a prize or money you weren't expecting.",
    },
    "no_https": {
        "ar": "الرابط غير مؤمَّن (لا يبدأ بـ https).",
        "en": "The link isn't secured (it doesn't start with https).",
    },
    "odd_structure": {
        "ar": "شكل الرابط طويل أو معقّد بشكل غير معتاد.",
        "en": "The link is unusually long or complicated.",
    },
}

SAFE_ACTION = {
    HIGH: {
        "ar": "لا تضغط الرابط ولا تدفع ولا ترسل أي رمز. بلّغ عن الرسالة.",
        "en": "Don't tap the link, don't pay, and don't send any code. Report the message.",
    },
    UNCLEAR: {
        "ar": "تحقق بنفسك: افتح تطبيق الجهة أو موقعها الرسمي، أو اتصل برقمها المعروف، ولا تستخدم الرابط الموجود في الرسالة.",
        "en": "Check it yourself: open the organisation's own app or official website, or call its known number. Don't use the link in the message.",
    },
    NONE: {
        "ar": "لم نجد مؤشرات ظاهرة، وهذا لا يعني أن الرسالة آمنة. الأفضل أن تفتح تطبيق الجهة بنفسك بدل الضغط على الرابط.",
        "en": "We found no visible warning signs. That doesn't mean it's safe. It's best to open the organisation's app yourself instead of tapping the link.",
    },
}

CHECKED = {
    "domain_matches": {
        "ar": "الرابط يطابق النطاق الرسمي لـ{entity} في قائمتنا.",
        "en": "The link matches the official domain of {entity} in our list.",
    },
    "list_unverified": {
        "ar": "تنبيه: قائمة النطاقات الرسمية في النموذج الأولي لم تُراجع بعد من مصادر رسمية.",
        "en": "Note: the official-domain list in this prototype has not yet been verified with official sources.",
    },
    "no_payment_or_code": {
        "ar": "لا تطلب الرسالة دفعاً أو بطاقة أو رمز تحقق.",
        "en": "The message doesn't ask for payment, card details or a verification code.",
    },
    "no_links": {
        "ar": "لا توجد روابط في الرسالة.",
        "en": "There are no links in the message.",
    },
    "delivers_code": {
        "ar": "الرسالة تعطيك رمزاً ولا تطلبه منك. لا تشارك هذا الرمز مع أحد.",
        "en": "The message gives you a code; it doesn't ask for one. Don't share that code with anyone.",
    },
}

NOT_GUARANTEED = {
    "ar": "لا نستطيع التأكد من مُرسل الرسالة نفسه، ولا نفتح الروابط. هذا تقدير وليس حكماً نهائياً.",
    "en": "We can't confirm who actually sent the message, and we don't open links. This is an estimate, not a final verdict.",
}

# Risk score bands. The 0-100 number always falls inside its status band, so it can
# never contradict the status, and it never reaches 0 (we never say "safe").
RISK_BANDS = {NONE: (5, 24), UNCLEAR: (30, 65), HIGH: (70, 100)}


def risk_score(status: str, raw: int) -> int:
    """Map the summed signal weights to 0-100 inside the status band."""
    lo, hi = RISK_BANDS[status]
    if status == NONE:
        value = lo + raw * 10
    elif status == UNCLEAR:
        value = lo + (raw - 2) * 9
    else:
        value = lo + raw * 3
    return max(lo, min(hi, value))


HARD_HIGH = {"asks_card", "asks_otp", "asks_personal", "receive_money_link", "confirmed_by_authority"}
# A link that dresses up as a known organisation it does not belong to is enough on
# its own (this is what a link pasted without any message looks like).
IMPERSONATING_LINK = {"lookalike", "brand_in_host", "at_sign"}


@dataclass
class Reason:
    code: str
    weight: int
    text: str
    evidence: list[str] = field(default_factory=list)


@dataclass
class Verdict:
    status: str
    score: int
    risk: int
    reasons: list[Reason]
    highlights: list[str]
    safe_action: str
    checked: list[str]
    not_guaranteed: str


def _fmt(template: str, claimed: list[Entity], lang: str) -> str:
    name = claimed[0].name(lang) if claimed else ("الجهة" if lang == "ar" else "the organisation")
    return template.replace("{entity}", name)


def decide(
    text_signals: list[TextSignal],
    link_reports: list[LinkReport],
    message_link_findings: list[LinkFinding],
    claimed: list[Entity],
    lang: str = "ar",
    extra_codes: set[str] | None = None,
) -> Verdict:
    lang = "ar" if lang == "ar" else "en"
    delivers_code = any(s.code == "delivers_code" for s in text_signals)
    has_links = bool(link_reports)

    # Collect (code -> weight, evidence) from every source, keeping the max weight per code.
    collected: dict[str, tuple[int, list[str]]] = {}

    def put(code: str, weight: int, evidence: list[str]) -> None:
        w, ev = collected.get(code, (0, []))
        collected[code] = (max(w, weight), list(dict.fromkeys(ev + evidence)))

    for s in text_signals:
        if s.weight > 0:
            put(s.code, s.weight, s.evidence)
    for r in link_reports:
        for f in r.findings:
            put(f.code, f.weight, [f.evidence])
    for f in message_link_findings:
        put(f.code, f.weight, [f.evidence])
    for code in extra_codes or set():  # signals added by the LLM (never removes rule signals)
        if code in REASONS and code not in collected:
            put(code, 3 if code in HARD_HIGH else 2, [])

    # A code-delivery SMS with no link: "valid for 5 minutes" is not pressure.
    if delivers_code and not has_links:
        collected.pop("urgency", None)

    all_official = has_links and all(r.official_for for r in link_reports)
    # Payment on an official link (e.g. a real bill) is only a weak hint.
    if all_official and "payment_request" in collected:
        w, ev = collected["payment_request"]
        collected["payment_request"] = (1, ev)

    score = sum(w for w, _ in collected.values())
    strong = [c for c, (w, _) in collected.items() if w >= 3]
    medium = [c for c, (w, _) in collected.items() if w == 2]

    if HARD_HIGH & collected.keys():
        status = HIGH  # rule 3: card / OTP request => high, even with an official link
    elif IMPERSONATING_LINK & collected.keys():
        status = HIGH
    elif len(strong) >= 2 or (strong and medium) or score >= 6:
        status = HIGH
    elif score >= 2:
        status = UNCLEAR
    else:
        status = NONE

    ordered = sorted(collected.items(), key=lambda kv: (-kv[1][0], list(REASONS).index(kv[0]) if kv[0] in REASONS else 99))
    reasons = [
        Reason(code=c, weight=w, text=_fmt(REASONS[c][lang], claimed, lang), evidence=ev)
        for c, (w, ev) in ordered
        if c in REASONS and (status != NONE)
    ][:3]
    highlights = list(dict.fromkeys(e for r in reasons for e in r.evidence if e))

    checked: list[str] = []
    if status != HIGH:
        official_entities = [r.official_for for r in link_reports if r.official_for]
        if has_links and all_official:
            from .entities import load_catalog
            ents = {e.id: e for e in load_catalog().entities}
            first = ents[official_entities[0][0]]
            checked.append(CHECKED["domain_matches"][lang].replace("{entity}", first.name(lang)))
            if not first.verified:
                checked.append(CHECKED["list_unverified"][lang])
        if not has_links:
            checked.append(CHECKED["no_links"][lang])
        if not ({"payment_request", "asks_card", "asks_otp"} & collected.keys()):
            checked.append(CHECKED["no_payment_or_code"][lang])
    if delivers_code:
        checked.append(CHECKED["delivers_code"][lang])

    return Verdict(
        status=status,
        score=score,
        risk=risk_score(status, score),
        reasons=reasons,
        highlights=highlights,
        safe_action=SAFE_ACTION[status][lang],
        checked=checked,
        not_guaranteed=NOT_GUARANTEED[lang],
    )
