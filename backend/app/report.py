"""Prepare a ready-to-paste report. The app never submits it for the user."""
from __future__ import annotations

# Federal channel only (docs/spec.md section 5).
# Source checked 21 Nov 2026. The exact in-app eCrime form and any deep link still need verification.
OFFICIAL_CHANNEL = {
    "name": {"ar": "منصة eCrime في تطبيق وزارة الداخلية (MOI UAE)", "en": "eCrime platform in the Ministry of Interior app (MOI UAE)"},
    "info_url": "https://u.ae/en/information-and-services/justice-safety-and-the-law/cyber-safety-and-digital-security/report-cybercrimes-online",
    "verified_on": "2026-11-21",
}

WHAT_HAPPENED = {
    "not_clicked": {"ar": "لم أضغط الرابط", "en": "I did not tap the link"},
    "clicked": {"ar": "ضغطت الرابط", "en": "I tapped the link"},
    "entered_card": {"ar": "أدخلت بيانات بطاقتي", "en": "I entered my card details"},
    "paid": {"ar": "دفعت مبلغاً", "en": "I paid money"},
}
CHANNELS = {"whatsapp": {"ar": "واتساب", "en": "WhatsApp"}, "sms": {"ar": "رسالة نصية SMS", "en": "SMS"}}

BANK_FIRST = {
    "ar": "تواصل مع بنكك فوراً لإيقاف البطاقة أو العملية، ثم قدّم البلاغ.",
    "en": "Contact your bank right now to block the card or the payment, then file the report.",
}


def build_report(
    masked_text: str,
    urls: list[str],
    channel: str | None,
    received_at: str | None,
    what_happened: str | None,
    lang: str = "ar",
) -> dict:
    lang = "ar" if lang == "ar" else "en"
    L = {
        "ar": ("بلاغ عن رسالة مشبوهة", "القناة", "وقت الاستلام", "الرابط/الروابط", "ماذا حصل", "نص الرسالة (بعد حجب البيانات الحساسة)", "غير محدد", "لا يوجد"),
        "en": ("Report: suspicious message", "Channel", "Received at", "Link(s)", "What happened", "Message text (sensitive data masked)", "Not specified", "None"),
    }[lang]
    title, ch_l, time_l, url_l, what_l, text_l, unknown, none = L
    lines = [
        title,
        f"{ch_l}: {CHANNELS.get(channel or '', {}).get(lang, unknown)}",
        f"{time_l}: {received_at or unknown}",
        f"{url_l}: {', '.join(urls) if urls else none}",
        f"{what_l}: {WHAT_HAPPENED.get(what_happened or '', {}).get(lang, unknown)}",
        "",
        f"{text_l}:",
        masked_text.strip(),
    ]
    bank_first = what_happened in ("entered_card", "paid")
    return {
        "report_text": "\n".join(lines),
        "bank_first": BANK_FIRST[lang] if bank_first else None,
        "channel": {"name": OFFICIAL_CHANNEL["name"][lang], "info_url": OFFICIAL_CHANNEL["info_url"], "verified_on": OFFICIAL_CHANNEL["verified_on"]},
    }
