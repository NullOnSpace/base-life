"""Simple news scraper utilities.

Provides functions to fetch pages, parse news items according to a
`config.toml` source definition, and filter results by search terms.
"""

import asyncio
import logging
import os
import re
from asyncio import Semaphore
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def setup_logging(level: Optional[str] = None) -> None:
    """Configure basic logging for the scraper.

    If ``level`` is not provided, read from the environment variable
    ``BASE_LIFE_LOG_LEVEL``. Accepts logging level names or integers.
    """
    if level is None:
        level = os.environ.get("BASE_LIFE_LOG_LEVEL", "INFO")

    try:
        lvl = int(level)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        lvl = getattr(logging, str(level).upper(), logging.INFO)

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=lvl,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    else:
        logging.getLogger().setLevel(lvl)


def default_headers() -> Dict[str, str]:
    """Return a set of default headers that resemble a real browser.

    Callers may update/override these per-source via `source["headers"]`.
    """
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Connection": "keep-alive",
    }


def _merge_headers(source: Dict[str, Any]) -> Dict[str, str]:
    """Merge default headers with any source-specific overrides."""
    src_headers = source.get("headers", {}) or {}
    merged = default_headers()
    merged.update({k: str(v) for k, v in src_headers.items()})
    return merged


def _select_with_contains(soup: BeautifulSoup, selector: str) -> List[BeautifulSoup]:
    """Select elements supporting a ``:contains(text)`` pseudo-selector.

    When ``:contains("text")`` is present we emulate it by filtering
    candidate elements by text content. Otherwise delegate to
    ``soup.select``.
    """
    if ":contains(" in selector:
        prefix, rest = selector.split(":contains(", 1)
        contain_text = rest.rsplit(")", 1)[0].strip('"').strip("'")
        candidates = soup.select(prefix) if prefix.strip() else soup.find_all(True)
        return [el for el in candidates if contain_text in el.get_text()]

    return soup.select(selector)


def _pub_format_to_regex(fmt: str) -> Tuple[str, str]:
    """Convert a simple ``pub-format`` string into a regex and strptime
    format string.

    Supported tokens (order matters: longer tokens first to avoid partial
    replacement): ``YYYY``, ``MM``, ``mm``, ``dd``, ``HH``, ``SS``.
    """
    token_map: List[Tuple[str, str, str]] = [
        (r"YYYY", r"(?P<Y>\d{4})", "%Y"),
        (r"MM", r"(?P<M>\d{1,2})", "%M"),
        (r"mm", r"(?P<m>\d{1,2})", "%m"),
        (r"dd", r"(?P<d>\d{1,2})", "%d"),
        (r"HH", r"(?P<H>\d{1,2})", "%H"),
        (r"SS", r"(?P<S>\d{1,2})", "%S"),
    ]
    regex = re.escape(fmt)
    strptime = fmt

    for token, token_regex, token_strp in token_map:
        regex = regex.replace(re.escape(token), token_regex)
        strptime = strptime.replace(token, token_strp)

    return regex, strptime


def extract_pub_time(text: str, pub_format: str) -> Optional[str]:
    """Extract a publication time from ``text`` using ``pub_format``.

    Returns an ISO 8601 formatted string on success, or ``None`` on failure.
    """
    if not text:
        return None

    regex, strptime_fmt = _pub_format_to_regex(pub_format)
    m = re.search(regex, text)
    if not m:
        pattern = r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2} \d{1,2}:\d{2}(?::\d{2})?)"
        m2 = re.search(pattern, text)
        if m2:
            try:
                dt = datetime.fromisoformat(m2.group(1))
                return dt.isoformat()
            except ValueError:
                return None

        return None

    date_str = m.group(0)
    try:
        dt = datetime.strptime(date_str, strptime_fmt)
        return dt.isoformat()
    except ValueError:
        return None


async def _async_fetch_url(
    url: str,
    session: aiohttp.ClientSession,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 15,
) -> Optional[str]:
    """Fetch URL content asynchronously and return text or ``None`` on error."""
    try:
        hdrs = headers or default_headers()
        logger.debug("HTTP GET %s (timeout=%s)", url, timeout)
        client_timeout = aiohttp.ClientTimeout(total=timeout)
        async with session.get(url, timeout=client_timeout, headers=hdrs) as resp:
            if resp.status != 200:
                logger.warning("Non-200 response %s for %s", resp.status, url)
                return None
            text = await resp.text()
            logger.debug("Received %s bytes from %s", len(text or ""), url)
            return text
    except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None


def _extract_links(
    soup: BeautifulSoup, list_sel: Optional[str], base_url: str
) -> List[str]:
    """Extract and resolve detail-page links from a list page."""
    page_base = base_url
    base_tag = soup.find("base", href=True)
    if base_tag and base_tag.get("href"):
        try:
            page_base = urljoin(base_url, base_tag.get("href"))
            logger.debug("Using <base> href for link resolution: %s", page_base)
        except Exception:
            logger.debug(
                "Invalid <base> href %s; falling back to %s",
                base_tag.get("href"),
                base_url,
            )

    link_elems = _select_with_contains(soup, list_sel) if list_sel else []
    links: List[str] = []

    for el in link_elems:
        href = el.get("href") if hasattr(el, "get") else None
        if href:
            links.append(urljoin(page_base, href))

    return links


@dataclass
class NewsItem:
    source: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    pub: Optional[str] = None
    content: Optional[str] = None
    filtered: bool = False
    filter_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "url": self.url,
            "title": self.title,
            "pub": self.pub,
            "content": self.content,
            "filtered": self.filtered,
            "filter_reason": self.filter_reason,
        }


async def _fetch_detail(
    session: aiohttp.ClientSession,
    sem: Semaphore,
    link: str,
    base_url: Optional[str],
    merged_headers: Dict[str, str],
    selectors: Dict[str, Any],
    source_name: Optional[str],
) -> Optional[NewsItem]:
    """Fetch and parse a single detail page."""
    async with sem:
        logger.debug("Fetching detail page: %s", link)
        per_headers = dict(merged_headers)
        if base_url:
            per_headers.setdefault("Referer", base_url)

        detail_html = await _async_fetch_url(link, session, headers=per_headers)
        if not detail_html:
            return None

        logger.debug("Fetched %s bytes for %s", len(detail_html), link)

    dsoup = BeautifulSoup(detail_html, "lxml")
    title_sel = selectors.get("title")
    pub_sel = selectors.get("pub")
    pub_fmt = selectors.get("pub-format")
    content_sel = selectors.get("content")

    title: Optional[str] = None
    if title_sel:
        els = _select_with_contains(dsoup, title_sel)
        if els:
            title = els[0].get_text(strip=True)
    logger.debug("Parsed title for %s: %s", link, title)

    pub_text: Optional[str] = None
    if pub_sel:
        els = _select_with_contains(dsoup, pub_sel)
        if els:
            pub_text = els[0].get_text(separator=" ", strip=True)
        else:
            node = dsoup.select_one(pub_sel)
            pub_text = node.get_text(strip=True) if node else None

    pub = extract_pub_time(pub_text or "", pub_fmt) if pub_fmt else None
    logger.debug("Parsed pub for %s: %s", link, pub)

    if content_sel:
        cels = _select_with_contains(dsoup, content_sel)
        if cels:
            content = cels[0].get_text(separator=" ", strip=True)
        else:
            content = dsoup.get_text(separator=" ", strip=True)
    else:
        content = dsoup.get_text(separator=" ", strip=True)
    logger.debug("Content length for %s: %d", link, len(content or ""))

    return NewsItem(
        source=source_name,
        url=link,
        title=title,
        pub=pub,
        content=content,
    )


def _matches_search(text: str, terms: List[str]) -> bool:
    """Check whether ``text`` (already lowered) contains any of the
    lowered ``terms`` as a substring.
    """
    return any(term in text for term in terms)


def _item_search_text(title: Optional[str], content: Optional[str]) -> str:
    """Combine title and content into a single lowered string for search."""
    parts = list(filter(None, [title or "", content or ""]))
    return " ".join(parts).lower()


async def parse_source(source: Dict[str, Any]) -> List[NewsItem]:
    """Parse a source definition from config and return list of items.

    The ``source`` dict is expected to have keys like ``url``, ``name`` and
    ``selectors`` following the project README and `docs/START.md`.
    """
    base_url = source.get("url")
    selectors = source.get("selectors", {})
    list_sel = selectors.get("list_selector")

    logger.info("Parsing source %s: %s", source.get("name"), base_url)
    merged_headers = _merge_headers(source)

    conn = aiohttp.TCPConnector(limit_per_host=5)
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        html = (
            await _async_fetch_url(base_url, session, headers=merged_headers)
            if base_url
            else None
        )
        if not html:
            logger.warning("No HTML returned for source %s", source.get("name"))
            return []

        soup = BeautifulSoup(html, "lxml")
        links = _extract_links(soup, list_sel, base_url or "")
        logger.debug(
            "Found %d candidate links for source %s", len(links), source.get("name")
        )

        sem = Semaphore(8)
        tasks = [
            _fetch_detail(
                session,
                sem,
                link,
                base_url,
                merged_headers,
                selectors,
                source.get("name"),
            )
            for link in links
        ]
        results_async = await asyncio.gather(*tasks)
        details = [r for r in results_async if r]
        logger.info(
            "Fetched %d detail pages for source %s",
            len(details),
            source.get("name"),
        )
        return details


def fetch_source(
    source: Dict[str, Any], search_terms: Optional[List[str]] = None
) -> List[NewsItem]:
    """Fetch items for a source and return a list of `NewsItem` objects.

    If `search_terms` is provided, each returned `NewsItem` will have
    `filtered=True` when it does NOT match any of the search terms. The
    function returns all items (both matched and filtered) so callers can
    inspect the `filtered` flag.
    """
    items = asyncio.run(parse_source(source))
    if not search_terms:
        return items

    lowered_terms = [t.lower() for t in search_terms]
    matched = 0
    for it in items:
        text = _item_search_text(it.title, it.content)
        if _matches_search(text, lowered_terms):
            it.filtered = False
            it.filter_reason = None
            matched += 1
        else:
            it.filtered = True
            it.filter_reason = "no match"

    logger.info(
        "Marked %d/%d items as matched for source %s",
        matched,
        len(items),
        source.get("name"),
    )
    return items


def unfiltered_items(items: List[NewsItem]) -> List[NewsItem]:
    """Return only items that are not marked as filtered."""
    return [it for it in items if not it.filtered]


def filter_by_search(
    items: List[Dict[str, Any]], search_terms: List[str]
) -> List[Dict[str, Any]]:
    """Return only items that contain any of the ``search_terms`` in title or content.

    Matching is case-insensitive and performs simple substring matching.
    """
    logger.info("Filtering %d items with search terms: %s", len(items), search_terms)

    if not search_terms:
        logger.debug("No search terms provided, returning original items")
        return items

    lowered_terms = [t.lower() for t in search_terms]
    out: List[Dict[str, Any]] = []

    for it in items:
        text = _item_search_text(it.get("title"), it.get("content"))
        if _matches_search(text, lowered_terms):
            out.append(it)

    logger.info("Filtered down to %d items", len(out))
    return out
