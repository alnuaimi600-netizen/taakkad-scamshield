"""Loads the list of entities and their official domains from data/."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from .normalize import normalize_ar

DATA_DIR = Path(os.environ.get("TAAKKAD_DATA_DIR", Path(__file__).resolve().parents[2] / "data"))


@dataclass(frozen=True)
class Entity:
    id: str
    category: str
    name_en: str
    name_ar: str
    aliases: tuple[str, ...]
    domains: tuple[str, ...]
    verified: bool
    demo: bool

    def name(self, lang: str) -> str:
        return self.name_ar if lang == "ar" else self.name_en


@dataclass(frozen=True)
class Catalog:
    entities: tuple[Entity, ...]
    generic_claims: dict[str, tuple[str, ...]]

    def official_domains(self) -> dict[str, Entity]:
        return {d: e for e in self.entities for d in e.domains}


@lru_cache(maxsize=1)
def load_catalog() -> Catalog:
    raw = json.loads((DATA_DIR / "official_domains.json").read_text(encoding="utf-8"))
    entities = tuple(
        Entity(
            id=e["id"],
            category=e["category"],
            name_en=e["names"]["en"],
            name_ar=e["names"]["ar"],
            aliases=tuple(normalize_ar(a) for a in {*e.get("aliases", []), e["names"]["en"], e["names"]["ar"]}),
            domains=tuple(d.lower() for d in e["domains"]),
            verified=bool(e.get("verified")),
            demo=bool(e.get("demo")),
        )
        for e in raw["entities"]
    )
    generic = {k: tuple(normalize_ar(w) for w in v) for k, v in raw.get("generic_claims", {}).items()}
    return Catalog(entities=entities, generic_claims=generic)


def _contains_word(haystack: str, needle: str) -> bool:
    # Word boundaries that also work for Arabic (prefixes like ال/ب/ل are allowed before Arabic words).
    if re.search(r"[a-z]", needle):
        return re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])", haystack) is not None
    return needle in haystack


def _spans(haystack: str, needle: str) -> list[tuple[int, int]]:
    if re.search(r"[a-z]", needle):
        pat = r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])"
    else:
        pat = re.escape(needle)
    return [m.span() for m in re.finditer(pat, haystack)]


def claimed_entities(text: str) -> list[Entity]:
    """Entities whose name or alias appears in the message text (URLs excluded by caller).

    A match that only occurs inside a longer match of another entity does not count:
    "اتصالات" inside "نجم للاتصالات" is Najm Telecom, not Etisalat.
    """
    norm = normalize_ar(text)
    found: list[tuple[Entity, tuple[int, int]]] = []
    for e in load_catalog().entities:
        for a in e.aliases:
            if a:
                found += [(e, sp) for sp in _spans(norm, a)]

    def covered(e: Entity, sp: tuple[int, int]) -> bool:
        return any(o is not e and os_[0] <= sp[0] and sp[1] <= os_[1] and (os_[1] - os_[0]) > (sp[1] - sp[0])
                   for o, os_ in found)

    out: list[Entity] = []
    for e, sp in found:
        if e not in out and not covered(e, sp):
            out.append(e)
    return out


def claimed_categories(text: str) -> set[str]:
    norm = normalize_ar(text)
    cats = {e.category for e in claimed_entities(text)}
    for cat, words in load_catalog().generic_claims.items():
        if any(_contains_word(norm, w) for w in words):
            cats.add(cat)
    return cats
