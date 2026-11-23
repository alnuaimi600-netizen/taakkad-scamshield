"""Text normalisation shared by the signal detectors."""
from __future__ import annotations

import re

_ARABIC_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")  # + tatweel
_ALEF = re.compile(r"[إأآٱ]")


def normalize_ar(text: str) -> str:
    """Lower-case and fold Arabic spelling variants so keyword lists stay short.

    أ/إ/آ -> ا, ى -> ي, ة -> ه, ؤ -> و, ئ -> ي, diacritics and tatweel removed.
    The result has a different length from the input; use it for matching only.
    """
    t = text.lower()
    t = _ARABIC_DIACRITICS.sub("", t)
    t = _ALEF.sub("ا", t)
    return t.replace("ى", "ي").replace("ة", "ه").replace("ؤ", "و").replace("ئ", "ي")
