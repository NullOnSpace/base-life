"""Simple news scraper utilities.

Provides functions to fetch pages, parse news items according to a
config.toml source definition, and filter results by search terms.
"""

import asyncio
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def setup_logging(level: str | None = None) -> None:
    """Configure basic logging for the scraper.

    If ``level`` is not provided, read from the environment variable
    ``BASE_LIFE_LOG_LEVEL``. Accepts logging level names or integers.
    Only affects the root logger when no handlers exist yet; otherwise
    just sets the level on the existing root logger.
    """
    if level is None:
        level = os.environ.get("BASE_LIFE_LOG_LEVEL", "INFO")

    try:
        lvl = int(level)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        lvl = getattr(logging, str(level).upper(), logging.INFO)

    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=lvl,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
    else:
        root.setLevel(lvl)


def default_headers() -> dict[str, str]:
    """Return a set of default headers that resemble a real browser.

    Callers may update/override these per-source via ``source["headers"]``.
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


def _merge_headers(source: dict[str, Any]) -> dict[str, str]:
    """Merge default headers with any source-specific overrides."""
    src_headers = source.get("headers", {}) or {}
    merged = default_headers()
    merged.update({k: str(v) for k, v in src_headers.items()})
    return merged


def _select_with_contains(soup: BeautifulSoup, selector: str) -> list[BeautifulSoup]:
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


def _pub_format_to_regex(fmt: str) -> tuple[str, str]:
    """Convert a ``pub-format`` string into a regex and strptime format.

    Supported tokens (order matters — longer/more-specific first):

    ======  ========  ===========
    Token   Regex     strptime
    ======  ========  ===========
    yyyy    \\d{4}    %Y   (year)
    mo      \\d{1,2}  %m   (month)
    dd      \\d{1,2}  %d   (day)
    hh      \\d{1,2}  %H   (hour)
    mi      \\d{1,2}  %M   (minute)
    ss      \\d{1,2}  %S   (second)
    ======  ========  ===========
    """
    token_map: list[tuple[str, str, str]] = [
        ("yyyy", r"(?P<Y>\d{4})", "%Y"),
        ("mo", r"(?P<m>\d{1,2})", "%m"),
        ("dd", r"(?P<d>\d{1,2})", "%d"),
        ("hh", r"(?P<H>\d{1,2})", "%H"),
        ("mi", r"(?P<M>\d{1,2})", "%M"),
        ("ss", r"(?P<S>\d{1,2})", "%S"),
    ]
    regex = re.escape(fmt)
    strptime = fmt

    for token, token_regex, token_strp in token_map:
        regex = regex.replace(re.escape(token), token_regex)
        strptime = strptime.replace(token, token_strp)

    return regex, strptime


def extract_pub_time(text: str, pub_format: str) -> str | None:
    """Extract a publication time from ``text`` using ``pub_format``.

    Returns an ISO 8601 formatted string on success, or ``None`` on failure.
    """
    if not text:
        return None

    regex, strptime_fmt = _pub_format_to_regex(pub_format)
    m = re.search(regex, text)
    if not m:
        for pattern in [
            r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2} \d{1,2}:\d{2}(?:\d{2})?)",
            r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2})",
        ]:
            m2 = re.search(pattern, text)
            if m2:
                try:
                    dt = datetime.fromisoformat(m2.group(1))
                    return dt.isoformat()
                except ValueError:
                    continue
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
    headers: dict[str, str] | None = None,
    per_request_timeout: int | None = None,
) -> str | None:
    """Fetch URL content asynchronously and return text or ``None`` on error.

    Uses the session-level timeout by default. When
    ``per_request_timeout`` is given, it overrides the session timeout
    for this specific request only.
    """
    try:
        hdrs = headers or default_headers()
        logger.debug("HTTP GET %s", url)
        kwargs: dict[str, Any] = {"headers": hdrs}
        if per_request_timeout is not None:
            kwargs["timeout"] = aiohttp.ClientTimeout(total=per_request_timeout)
        async with session.get(url, **kwargs) as resp:
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
    soup: BeautifulSoup, list_sel: str | None, base_url: str
) -> list[str]:
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
    links: list[str] = []

    for el in link_elems:
        href = el.get("href") if hasattr(el, "get") else None
        if href:
            links.append(urljoin(page_base, href))

    return links


@dataclass
class NewsItem:
    source: str | None = None
    url: str | None = None
    title: str | None = None
    pub: str | None = None
    content: str | None = None
    filtered: bool = False
    filter_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "url": self.url,
            "title": self.title,
            "pub": self.pub,
            "content": self.content,
            "filtered": self.filtered,
            "filter_reason": self.filter_reason,
        }


@dataclass
class _SourceContext:
    """Bundled source-related parameters passed to ``_fetch_detail``."""

    name: str | None = None
    base_url: str | None = None
    merged_headers: dict[str, str] = field(default_factory=dict)
    selectors: dict[str, Any] = field(default_factory=dict)


async def _fetch_detail(
    session: aiohttp.ClientSession,
    sem: asyncio.Semaphore,
    link: str,
    ctx: _SourceContext,
) -> NewsItem | None:
    """Fetch and parse a single detail page."""
    async with sem:
        logger.debug("Fetching detail page: %s", link)
        per_headers = dict(ctx.merged_headers)
        if ctx.base_url:
            per_headers.setdefault("Referer", ctx.base_url)

        detail_html = await _async_fetch_url(link, session, headers=per_headers)
        if not detail_html:
            return None

        logger.debug("Fetched %s bytes for %s", len(detail_html), link)

    dsoup = BeautifulSoup(detail_html, "lxml")
    title_sel = ctx.selectors.get("title")
    pub_sel = ctx.selectors.get("pub")
    pub_fmt = ctx.selectors.get("pub-format")
    content_sel = ctx.selectors.get("content")

    title: str | None = None
    if title_sel:
        els = _select_with_contains(dsoup, title_sel)
        if els:
            title = els[0].get_text(strip=True)
    logger.debug("Parsed title for %s: %s", link, title)

    pub_text: str | None = None
    if pub_sel:
        els = _select_with_contains(dsoup, pub_sel)
        if els:
            pub_text = els[0].get_text(separator=" ", strip=True)

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
        source=ctx.name,
        url=link,
        title=title,
        pub=pub,
        content=content,
    )


def _matches_search(text: str, terms: list[str]) -> bool:
    """Check whether ``text`` (already lowered) contains any of the
    lowered ``terms`` as a substring.
    """
    return any(term in text for term in terms)


def _item_search_text(title: str | None, content: str | None) -> str:
    """Combine title and content into a single lowered string for search."""
    parts = [v for v in [title, content] if v]
    return " ".join(parts).lower()


def _apply_search_filter(
    items: list[NewsItem], search_terms: list[str]
) -> list[NewsItem]:
    """Mark items that don't match ``search_terms`` as filtered.

    Matching is case-insensitive substring. Items that match keep
    ``filtered=False``; non-matching items get ``filtered=True`` with
    ``filter_reason="no match"``.
    """
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
    return items


async def parse_source(
    source: dict[str, Any],
    session: aiohttp.ClientSession | None = None,
) -> list[NewsItem]:
    """Parse a source definition from config and return list of items.

    When ``session`` is provided, it is reused for all requests (enabling
    connection pooling across sources). When ``None``, a new session is
    created and closed within this call.
    """
    base_url = source.get("url")
    selectors = source.get("selectors", {})
    list_sel = selectors.get("list_selector")

    logger.info("Parsing source %s: %s", source.get("name"), base_url)
    merged_headers = _merge_headers(source)

    ctx = _SourceContext(
        name=source.get("name"),
        base_url=base_url,
        merged_headers=merged_headers,
        selectors=selectors,
    )

    owned_session = session is None
    if owned_session:
        conn = aiohttp.TCPConnector(limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=60)
        session = aiohttp.ClientSession(connector=conn, timeout=timeout)

    try:
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
            "Found %d candidate links for source %s",
            len(links),
            source.get("name"),
        )

        sem = asyncio.Semaphore(8)
        tasks = [_fetch_detail(session, sem, link, ctx) for link in links]
        results_async = await asyncio.gather(*tasks)
        details = [r for r in results_async if r]
        logger.info(
            "Fetched %d detail pages for source %s",
            len(details),
            source.get("name"),
        )
        return details
    finally:
        if owned_session:
            await session.close()


def fetch_source(
    source: dict[str, Any],
    search_terms: list[str] | None = None,
    session: aiohttp.ClientSession | None = None,
) -> list[NewsItem]:
    """Fetch items for a source and return a list of ``NewsItem`` objects.

    If ``search_terms`` is provided, each returned ``NewsItem`` will have
    ``filtered=True`` when it does NOT match any of the search terms.

    When ``session`` is provided, it is reused across requests (enabling
    connection pooling). When ``None``, a new session is created per call.
    """
    if session is not None:
        items = asyncio.run(parse_source(source, session=session), debug=False)
    else:
        items = asyncio.run(parse_source(source))

    if search_terms:
        _apply_search_filter(items, search_terms)

    logger.info(
        "Fetched %d items for source %s (search_terms=%s)",
        len(items),
        source.get("name"),
        search_terms,
    )
    return items


async def fetch_all_sources(
    sources: list[dict[str, Any]],
) -> list[NewsItem]:
    """Fetch items from all sources using a shared ``ClientSession``.

    This enables connection pooling across sources that share the same
    host, and avoids repeated event-loop creation overhead.
    """
    conn = aiohttp.TCPConnector(limit_per_host=5)
    timeout = aiohttp.ClientTimeout(total=60)
    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        all_items: list[NewsItem] = []
        for src in sources:
            items = await parse_source(src, session=session)
            search_terms = src.get("selectors", {}).get("search", [])
            if search_terms:
                _apply_search_filter(items, search_terms)
            all_items.extend(items)
        return all_items


def unfiltered_items(items: list[NewsItem]) -> list[NewsItem]:
    """Return only items that are not marked as filtered."""
    return [it for it in items if not it.filtered]


def filter_by_search(
    items: list[dict[str, Any]], search_terms: list[str]
) -> list[dict[str, Any]]:
    """Return only items that contain any of the ``search_terms``.

    Matching is case-insensitive and performs simple substring matching
    on title and content fields.
    """
    if not search_terms:
        return items

    lowered_terms = [t.lower() for t in search_terms]
    return [
        it
        for it in items
        if _matches_search(
            _item_search_text(it.get("title"), it.get("content")),
            lowered_terms,
        )
    ]
