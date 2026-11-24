"""Text-only link checks.

Nothing in this module opens, resolves or fetches a URL. Every check looks at the
characters of the link and compares them with the entities the message claims to
come from. (Server-side fetching is excluded by the hackathon rules and is an
SSRF risk.)
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from .entities import Entity, claimed_categories, claimed_entities, load_catalog
from .masking import TRAILING_PUNCT, URL_RE

SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.ly", "cutt.ly", "is.gd", "rb.gy", "shorturl.at", "ow.ly",
    "goo.gl", "s.id", "t.co", "tiny.cc", "rebrand.ly", "bitly.com", "v.gd", "shorturl.com",
}
UNUSUAL_TLDS = {
    "xyz", "top", "icu", "click", "link", "buzz", "shop", "live", "online", "site", "cfd",
    "sbs", "rest", "monster", "gq", "tk", "ml", "cf", "ga", "win", "loan", "work", "cam", "su",
}
# Two-level public suffixes we care about (no external Public Suffix List dependency).
TWO_LEVEL_SUFFIXES = {
    "co.ae", "gov.ae", "ac.ae", "net.ae", "org.ae", "sch.ae", "mil.ae",
    "com.sa", "gov.sa", "co.uk", "org.uk", "com.qa", "com.om", "com.kw", "com.bh",
}
# Characters scammers swap in to imitate a brand name.
HOMOGLYPHS = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "$": "s"})


@dataclass
class LinkFinding:
    code: str           # stable id, translated in scoring.REASONS
    weight: int         # 3 strong, 2 medium, 1 weak
    evidence: str       # the substring to highlight in the message


@dataclass
class LinkReport:
    url: str
    host: str
    registered_domain: str
    official_for: list[str] = field(default_factory=list)  # entity ids the domain officially belongs to
    findings: list[LinkFinding] = field(default_factory=list)


def extract_urls(text: str) -> list[str]:
    seen: list[str] = []
    for m in URL_RE.finditer(text):
        url = m.group(0).rstrip(TRAILING_PUNCT)
        if url and url not in seen:
            seen.append(url)
    return seen


def _parse(url: str) -> tuple[str, str]:
    """Return (scheme, host) without network access."""
    candidate = url if re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I) else "http-less://" + url
    try:
        parts = urlsplit(candidate)
        host = (parts.hostname or "").lower().rstrip(".")
    except ValueError:  # e.g. a malformed "[...]" host: treat as no host, never crash
        return "", ""
    scheme = parts.scheme.lower()
    return ("" if scheme == "http-less" else scheme), host


def registered_domain(host: str) -> str:
    if _is_ip(host):
        return host
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in TWO_LEVEL_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return False


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _brand_label(domain: str) -> str:
    """'emiratesnbd.com' -> 'emiratesnbd'; 'falcon-express.test' -> 'falconexpress'."""
    return domain.split(".")[0].replace("-", "")


def _lookalike_of(reg_domain: str, official: dict[str, Entity]) -> Entity | None:
    label = reg_domain.split(".")[0].replace("-", "")
    folded = label.translate(HOMOGLYPHS).replace("rn", "m").replace("vv", "w")
    for dom, ent in official.items():
        brand = _brand_label(dom)
        if len(brand) < 4 or reg_domain == dom:
            continue
        if folded == brand and label != brand:
            return ent  # digit/letter swap, e.g. arame0x -> aramex
        if label != brand and _levenshtein(label, brand) <= (1 if len(brand) <= 6 else 2):
            return ent
    return None


def _brand_mentioned_in_host(host: str, reg_domain: str, official: dict[str, Entity]) -> Entity | None:
    """Brand name used in a subdomain or glued into another domain, e.g.
    aramex.track-parcel.test or aramex-pay.test."""
    host_flat = host.replace("-", "").replace(".", " ")
    for dom, ent in official.items():
        brand = _brand_label(dom)
        if len(brand) < 3 or reg_domain == dom:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(brand)}", host_flat) or brand in host.replace("-", ""):
            return ent
    return None


def check_url(url: str) -> LinkReport:
    catalog = load_catalog()
    official = catalog.official_domains()
    scheme, host = _parse(url)
    reg = registered_domain(host)
    report = LinkReport(url=url, host=host, registered_domain=reg)

    if reg in official:
        report.official_for.append(official[reg].id)
    elif host in official:
        report.official_for.append(official[host].id)

    add = report.findings.append
    # Domains that staff confirmed as fraudulent on the authority dashboard (text match only).
    from .stats import confirmed_domains
    confirmed = confirmed_domains()
    if not report.official_for and (reg in confirmed or host in confirmed):
        add(LinkFinding("confirmed_by_authority", 3, url))
    if _is_ip(host):
        add(LinkFinding("ip_host", 2, url))
    if host.startswith("xn--") or ".xn--" in host or any(ord(c) > 127 for c in host):
        add(LinkFinding("punycode", 3, url))
    if reg in SHORTENERS or host in SHORTENERS:
        add(LinkFinding("shortener", 2, url))
    tld = host.rsplit(".", 1)[-1] if "." in host else ""
    if tld in UNUSUAL_TLDS and not report.official_for:
        add(LinkFinding("unusual_tld", 2, url))
    if scheme == "http":
        add(LinkFinding("no_https", 1, url))
    if "@" in url.split("//", 1)[-1].split("/", 1)[0]:
        add(LinkFinding("at_sign", 3, url))
    if not report.official_for and not _is_ip(host):
        look = _lookalike_of(reg, official)
        if look is not None:
            add(LinkFinding("lookalike", 3, url))
        else:
            brand = _brand_mentioned_in_host(host, reg, official)
            if brand is not None:
                add(LinkFinding("brand_in_host", 3, url))
    if len(url) > 90 or host.count(".") >= 4 or host.count("-") >= 3:
        add(LinkFinding("odd_structure", 1, url))
    return report


def check_message_links(text_without_urls: str, urls: list[str]) -> tuple[list[LinkReport], list[LinkFinding], list[Entity]]:
    """Check each link and compare it with the entity the message claims to be.

    Returns per-link reports, message-level findings (claim/link mismatch) and the
    claimed entities.
    """
    reports = [check_url(u) for u in urls]
    claimed = claimed_entities(text_without_urls)
    findings: list[LinkFinding] = []
    if claimed and reports:
        claimed_ids = {e.id for e in claimed}
        for r in reports:
            if not (set(r.official_for) & claimed_ids):
                findings.append(LinkFinding("link_mismatch_claimed", 3, r.url))
    elif reports and claimed_categories(text_without_urls):
        # "Your shipment / your bank..." with a link that is not on any official list we know.
        for r in reports:
            if not r.official_for:
                findings.append(LinkFinding("link_unknown_for_claim", 2, r.url))
    return reports, findings, claimed
