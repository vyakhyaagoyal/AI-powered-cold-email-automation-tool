"""
Website research module.

Fetches the homepage plus a handful of internal pages that look like
About / Services / Solutions / Contact pages, strips nav/header/footer/
cookie-banner noise, and returns clean visible text for the LLM to reason
about. Uses `requests` + BeautifulSoup as required, wrapped in
`asyncio.to_thread` so it can run concurrently with other async work.
"""
import asyncio
import re
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from core.models import ScrapedSite

USER_AGENT = "Mozilla/5.0 (compatible; ReachOpsResearchBot/1.0; +https://reachops.example)"
KEYWORDS = ["about", "service", "solution", "product", "contact", "who-we-are", "what-we-do"]
MAX_PAGES = 5          # homepage + up to 4 internal pages
MAX_CHARS = 6000       # cap combined text so LLM prompts stay reasonable
REQUEST_TIMEOUT = 10


def _clean_soup(soup: BeautifulSoup) -> str:
    """Remove nav/header/footer/scripts/cookie banners, return clean visible text."""
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript", "iframe", "svg", "form"]):
        tag.decompose()

    # Remove likely cookie-consent / popup banners by common class/id naming patterns
    banner_pattern = re.compile(r"(cookie|consent|gdpr|popup|modal-overlay)", re.I)
    for el in soup.find_all(attrs={"class": banner_pattern}):
        el.decompose()
    for el in soup.find_all(attrs={"id": banner_pattern}):
        el.decompose()

    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text)


def _fetch(url: str) -> str | None:
    """Fetch raw HTML for a URL, returning None on any failure."""
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        if resp.status_code >= 400:
            return None
        return resp.text
    except requests.RequestException:
        return None


def _discover_links(base_url: str, html: str) -> list[str]:
    """Find same-domain links whose href/text suggest About/Services/Solutions/Contact pages."""
    soup = BeautifulSoup(html, "html.parser")
    found: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = (a.get_text() or "").lower()
        haystack = f"{href} {text}".lower()
        if any(keyword in haystack for keyword in KEYWORDS):
            full = urljoin(base_url, href)
            if urlparse(full).netloc == urlparse(base_url).netloc:
                found.add(full.split("#")[0])
    return list(found)[: MAX_PAGES - 1]


def scrape_website_sync(url: str) -> ScrapedSite:
    """Blocking scrape implementation — call via asyncio.to_thread for async use."""
    if not url.startswith("http"):
        url = "https://" + url

    home_html = _fetch(url)
    if home_html is None:
        return ScrapedSite(
            url=url, success=False,
            error="Could not reach website (connection failed or non-200 response)",
        )

    pages_scraped = [url]
    all_text = [_clean_soup(BeautifulSoup(home_html, "html.parser"))]

    for link in _discover_links(url, home_html):
        html = _fetch(link)
        if html:
            all_text.append(_clean_soup(BeautifulSoup(html, "html.parser")))
            pages_scraped.append(link)

    combined = " ".join(all_text).strip()[:MAX_CHARS]

    if not combined:
        return ScrapedSite(
            url=url, pages_scraped=pages_scraped, success=False,
            error="No meaningful text content found on website",
        )

    return ScrapedSite(url=url, pages_scraped=pages_scraped, content=combined, success=True)


async def scrape_website(url: str) -> ScrapedSite:
    """Async wrapper around the blocking scraper."""
    return await asyncio.to_thread(scrape_website_sync, url)
