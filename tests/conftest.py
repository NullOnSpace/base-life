"""Shared test fixtures and helpers."""

from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


LIST_HTML = read_fixture("list_page.html")
DETAIL_1_HTML = read_fixture("detail_1.html")
DETAIL_2_HTML = read_fixture("detail_2.html")
DETAIL_CONTAINS_HTML = read_fixture("detail_contains.html")

BASE_URL = "https://example.com"

SOURCE_CONFIG = {
    "name": "test-source",
    "url": BASE_URL,
    "selectors": {
        "list_selector": "div.list-content ul li a",
        "title": "h1.arti-title",
        "pub": "span.arti-update",
        "pub-format": "YYYY-mm-dd",
        "content": "div.arti-articlecontent",
    },
}

SOURCE_CONFIG_WITH_SEARCH = {
    "name": "test-source-search",
    "url": BASE_URL,
    "selectors": {
        "list_selector": "div.list-content ul li a",
        "title": "h1.arti-title",
        "pub": "span.arti-update",
        "pub-format": "YYYY-mm-dd HH:MM:SS",
        "content": "div.arti-articlecontent",
        "search": ["water", "supply"],
    },
}

SOURCE_CONFIG_CONTAINS = {
    "name": "test-source-contains",
    "url": BASE_URL + "/contains",
    "selectors": {
        "list_selector": "table.topds table td.content table td > a",
        "title": "h1 > strong",
        "pub": 'div[align="center"]:contains("发布日期")',
        "pub-format": "YYYY-mm-dd HH:MM",
        "content": "#zoom",
    },
}
