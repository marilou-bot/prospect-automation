"""Analyse du site d'un restaurant : moteur de réservation + emails."""
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RestoProspector/0.1)"}

# Signatures cherchées dans les href / src / scripts (signal fort)
ENGINES = {
    "Zenchef": ["zenchef.com"],
    "TheFork": ["thefork.com", "thefork.fr", "lafourchette.com"],
    "SevenRooms": ["sevenrooms.com"],
    "CoverManager": ["covermanager.com", "covermanager.es"],
    "OpenTable": ["opentable.com", "opentable.fr", "opentable.co"],
}
# Mots-clés dans le texte visible (signal faible)
TEXT_HINTS = {
    "Zenchef": "zenchef",
    "TheFork": "thefork",
    "SevenRooms": "sevenrooms",
    "CoverManager": "covermanager",
    "OpenTable": "opentable",
}
EXTRA_PAGES = ("contact", "reserv", "book", "mention", "legal", "a-propos", "about", "infos")
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
JUNK = ("sentry", "wixpress", "example.", "domain.", ".png", ".jpg", ".webp", ".svg", "u003e")


def _get(url: str, timeout: int = 10):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        if r.ok and "text/html" in r.headers.get("content-type", ""):
            return r.url, r.text
    except requests.RequestException:
        pass
    return None, None


def _detect_engine(html: str, soup: BeautifulSoup):
    """Retourne (moteur, preuve) ou (None, None)."""
    urls = []
    for tag in soup.find_all(["a", "iframe", "script", "link"]):
        for attr in ("href", "src", "data-src"):
            if tag.get(attr):
                urls.append(tag[attr])
    blob = " ".join(urls) + " " + html[:400_000]
    low = blob.lower()
    for engine, sigs in ENGINES.items():
        for s in sigs:
            if s in low:
                return engine, f"signature '{s}'"
    text = soup.get_text(" ", strip=True).lower()
    for engine, kw in TEXT_HINTS.items():
        if kw in text:
            return engine, f"mention texte '{kw}'"
    return None, None


def _emails(html: str, soup: BeautifulSoup, site_domain: str) -> set[str]:
    found = set()
    for a in soup.select('a[href^="mailto:"]'):
        found.add(a["href"][7:].split("?")[0].strip().lower())
    found.update(m.lower() for m in EMAIL_RE.findall(soup.get_text(" ")))
    clean = {e for e in found if not any(j in e for j in JUNK)}
    return clean


def scan_site(website: str) -> dict:
    """Analyse la page d'accueil + quelques pages utiles (contact, réservation, mentions légales)."""
    out = {"booking_engine": None, "engine_evidence": None, "emails": [], "contact_page": None, "error": None}
    if not website:
        out["error"] = "pas de site web"
        return out
    if not website.startswith("http"):
        website = "https://" + website

    final_url, html = _get(website)
    if not html:
        out["error"] = "site inaccessible"
        return out

    domain = urlparse(final_url).netloc.replace("www.", "")
    soup = BeautifulSoup(html, "html.parser")
    pages = [(final_url, html, soup)]

    # Pages secondaires (même domaine uniquement)
    extra, seen = [], {final_url}
    for a in soup.find_all("a", href=True):
        full = urljoin(final_url, a["href"])
        if urlparse(full).netloc.replace("www.", "") != domain or full in seen:
            continue
        if any(k in full.lower() for k in EXTRA_PAGES):
            seen.add(full)
            extra.append(full)
    for u in extra[:3]:
        fu, h = _get(u)
        if h:
            pages.append((fu, h, BeautifulSoup(h, "html.parser")))

    emails = set()
    for u, h, s in pages:
        if not out["booking_engine"]:
            eng, ev = _detect_engine(h, s)
            if eng:
                out["booking_engine"], out["engine_evidence"] = eng, f"{ev} sur {u}"
        page_emails = _emails(h, s, domain)
        if page_emails and not out["contact_page"] and u != final_url:
            out["contact_page"] = u
        emails |= page_emails

    # Emails du domaine du restaurant en premier
    out["emails"] = sorted(emails, key=lambda e: (domain not in e, e))[:5]
    return out
