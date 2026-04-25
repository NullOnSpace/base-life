"""Simple news scraper utilities.

Provides functions to fetch pages, parse news items according to a
`config.json` source definition, and filter results by search terms.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TypedDict
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def _select_with_contains(
    soup: BeautifulSoup, selector: str
) -> List[BeautifulSoup]:
    """Select elements supporting a ``:contains(text)`` pseudo-selector.

    When ``:contains("text")`` is present we emulate it by filtering
    candidate elements by text content. Otherwise delegate to
    ``soup.select``.
    """
    if ":contains(" in selector:
        prefix, rest = selector.split(":contains(", 1)
        contain_text = rest.rsplit(")", 1)[0].strip('"').strip("'")
        candidates = (
            soup.select(prefix) if prefix.strip() else soup.find_all(True)
        )
        return [el for el in candidates if contain_text in el.get_text()]

    return soup.select(selector)


def _pub_format_to_regex(fmt: str) -> Tuple[str, str]:
    """Convert a simple ``pub-format`` string into a regex and strptime
    format string.

    Supported tokens: ``YYYY``, ``mm``, ``dd``, ``HH``, ``MM``, ``SS``.
    """
    token_map: List[Tuple[str, str, str]] = [
        (r"YYYY", r"(?P<Y>\d{4})", "%Y"),
        (r"dd", r"(?P<d>\d{1,2})", "%d"),
        (r"HH", r"(?P<H>\d{1,2})", "%H"),
        (r"MM", r"(?P<M>\d{1,2})", "%M"),
        (r"mm", r"(?P<m>\d{1,2})", "%m"),
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
        # loose fallback: look for an ISO-like date/time
        m2 = re.search(
            r"(\d{4}[-/.]\d{1,2}[-/.]\d{1,2} \d{1,2}:\d{2}(?::\d{2})?)", text
        )
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


def fetch_url(url: str, timeout: int = 15) -> Optional[str]:
    """Fetch URL content and return text or ``None`` on error.

    Uses ``requests`` and sets response encoding to the apparent encoding.
    """
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        return r.text
    except requests.RequestException:
        return None


class Item(TypedDict, total=False):
    source: Optional[str]
    url: Optional[str]
    title: Optional[str]
    pub: Optional[str]
    content: Optional[str]


def parse_source(source: Dict[str, Any]) -> List[Item]:
    """Parse a source definition from config and return list of items.

    The ``source`` dict is expected to have keys like ``url``, ``name`` and
    ``selectors`` following the project README and `docs/START.md`.
    """
    base_url = source.get("url")
    selectors = source.get("selectors", {})
    list_sel = selectors.get("list_selector")
    results: List[Item] = []

    html = fetch_url(base_url) if base_url else None
    if not html:
        return results

    soup = BeautifulSoup(html, "lxml")
    link_elems = _select_with_contains(soup, list_sel) if list_sel else []
    links: List[str] = []

    for el in link_elems:
        href = el.get("href") if hasattr(el, "get") else None
        if href:
            links.append(urljoin(base_url, href))

    for link in links:
        detail_html = fetch_url(link)
        if not detail_html:
            continue

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

        pub_text: Optional[str] = None
        if pub_sel:
            els = _select_with_contains(dsoup, pub_sel)
            if els:
                pub_text = els[0].get_text(separator=" ", strip=True)
            else:
                node = dsoup.select_one(pub_sel)
                pub_text = node.get_text(strip=True) if node else None

        pub = extract_pub_time(pub_text or "", pub_fmt) if pub_fmt else None

        content: str
        if content_sel:
            cels = _select_with_contains(dsoup, content_sel)
            if cels:
                content = cels[0].get_text(separator=" ", strip=True)
            else:
                content = dsoup.get_text(separator=" ", strip=True)
        else:
            content = dsoup.get_text(separator=" ", strip=True)

        results.append(
            {
                "source": source.get("name"),
                "url": link,
                "title": title,
                "pub": pub,
                "content": content,
            }
        )

    return results


def filter_by_search(
    items: List[Dict[str, Any]], search_terms: List[str]
) -> List[Dict[str, Any]]:
    """Return only items that contain any of the ``search_terms`` in title or content.

    Matching is case-insensitive and performs simple substring matching.
    """
    if not search_terms:
        return items

    lowered = [t.lower() for t in search_terms]
    out: List[Dict[str, Any]] = []

    for it in items:
        text = (
            " ".join(
                filter(None, [it.get("title", ""), it.get("content", "")])
            )
        ).lower()
        if any(term in text for term in lowered):
            out.append(it)

    return out
