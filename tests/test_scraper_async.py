"""Tests for scraper async functions (with mocked HTTP via aioresponses)."""

import asyncio

import aiohttp
from aioresponses import aioresponses

from base_life.scraper import (
    _async_fetch_url,
    _fetch_detail,
    _SourceContext,
    fetch_source,
    parse_source,
)
from tests.conftest import (
    BASE_URL,
    DETAIL_1_HTML,
    DETAIL_2_HTML,
    DETAIL_CONTAINS_HTML,
    LIST_HTML,
    SOURCE_CONFIG,
    SOURCE_CONFIG_CONTAINS,
    SOURCE_CONFIG_WITH_SEARCH,
)


class TestAsyncFetchUrl:
    async def test_success(self):
        with aioresponses() as m:
            m.get(BASE_URL, body=LIST_HTML)
            async with aiohttp.ClientSession() as session:
                result = await _async_fetch_url(BASE_URL, session)
            assert result == LIST_HTML

    async def test_non_200_returns_none(self):
        with aioresponses() as m:
            m.get(BASE_URL, status=404)
            async with aiohttp.ClientSession() as session:
                result = await _async_fetch_url(BASE_URL, session)
            assert result is None

    async def test_connection_error_returns_none(self):
        with aioresponses() as m:
            m.get(BASE_URL, exception=aiohttp.ClientError("connection failed"))
            async with aiohttp.ClientSession() as session:
                result = await _async_fetch_url(BASE_URL, session)
            assert result is None

    async def test_timeout_returns_none(self):
        with aioresponses() as m:
            m.get(BASE_URL, exception=asyncio.TimeoutError())
            async with aiohttp.ClientSession() as session:
                result = await _async_fetch_url(BASE_URL, session)
            assert result is None


class TestFetchDetail:
    async def test_parse_detail_page(self):
        detail_url = BASE_URL + "/news/detail-1.html"
        ctx = _SourceContext(
            name="test-source",
            base_url=BASE_URL,
            selectors=SOURCE_CONFIG["selectors"],
        )
        with aioresponses() as m:
            m.get(detail_url, body=DETAIL_1_HTML)
            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(8)
                result = await _fetch_detail(session, sem, detail_url, ctx)
        assert result is not None
        assert result.title == "First Article About Water Supply"
        assert result.pub == "2025-04-26T00:00:00"
        assert "water supply" in result.content.lower()
        assert result.source == "test-source"
        assert result.url == detail_url

    async def test_detail_with_contains_selector(self):
        contains_url = BASE_URL + "/contains/notice/water-notice.html"
        ctx = _SourceContext(
            name="test-source-contains",
            base_url=BASE_URL + "/contains",
            selectors=SOURCE_CONFIG_CONTAINS["selectors"],
        )
        with aioresponses() as m:
            m.get(BASE_URL + "/contains", body=DETAIL_CONTAINS_HTML)
            m.get(contains_url, body=DETAIL_CONTAINS_HTML)
            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(8)
                result = await _fetch_detail(session, sem, contains_url, ctx)
        assert result is not None
        assert result.title == "Water Notice With Contains"
        assert result.pub == "2025-04-26T08:30:00"
        assert "water supply notice" in result.content.lower()

    async def test_fetch_failure_returns_none(self):
        detail_url = BASE_URL + "/news/nonexistent.html"
        ctx = _SourceContext(
            name="test-source",
            base_url=BASE_URL,
            selectors=SOURCE_CONFIG["selectors"],
        )
        with aioresponses() as m:
            m.get(detail_url, exception=aiohttp.ClientError("fail"))
            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(8)
                result = await _fetch_detail(session, sem, detail_url, ctx)
        assert result is None

    async def test_detail_with_seconds_in_pub(self):
        detail_url = BASE_URL + "/news/detail-2.html"
        ctx = _SourceContext(
            name="test-source-search",
            base_url=BASE_URL,
            selectors=SOURCE_CONFIG_WITH_SEARCH["selectors"],
        )
        with aioresponses() as m:
            m.get(detail_url, body=DETAIL_2_HTML)
            async with aiohttp.ClientSession() as session:
                sem = asyncio.Semaphore(8)
                result = await _fetch_detail(session, sem, detail_url, ctx)
        assert result is not None
        assert result.title == "Second Article About Road Repair"
        assert result.pub == "2025-03-15T10:30:00"


class TestParseSource:
    async def test_full_parse_source(self):
        detail_1_url = BASE_URL + "/news/detail-1.html"
        detail_2_url = BASE_URL + "/news/detail-2.html"
        with aioresponses() as m:
            m.get(BASE_URL, body=LIST_HTML)
            m.get(detail_1_url, body=DETAIL_1_HTML)
            m.get(detail_2_url, body=DETAIL_2_HTML)
            items = await parse_source(SOURCE_CONFIG)

        assert len(items) == 2
        assert items[0].title == "First Article About Water Supply"
        assert items[1].title == "Second Article About Road Repair"

    async def test_list_page_failure_returns_empty(self):
        with aioresponses() as m:
            m.get(BASE_URL, exception=aiohttp.ClientError("fail"))
            items = await parse_source(SOURCE_CONFIG)
        assert items == []

    async def test_detail_page_partial_failure(self):
        detail_1_url = BASE_URL + "/news/detail-1.html"
        detail_2_url = BASE_URL + "/news/detail-2.html"
        with aioresponses() as m:
            m.get(BASE_URL, body=LIST_HTML)
            m.get(detail_1_url, body=DETAIL_1_HTML)
            m.get(detail_2_url, exception=aiohttp.ClientError("fail"))
            items = await parse_source(SOURCE_CONFIG)

        assert len(items) == 1
        assert items[0].title == "First Article About Water Supply"


class TestFetchSource:
    def test_fetch_source_with_search_terms(self):
        detail_1_url = BASE_URL + "/news/detail-1.html"
        detail_2_url = BASE_URL + "/news/detail-2.html"
        with aioresponses() as m:
            m.get(BASE_URL, body=LIST_HTML)
            m.get(detail_1_url, body=DETAIL_1_HTML)
            m.get(detail_2_url, body=DETAIL_2_HTML)
            items = fetch_source(
                SOURCE_CONFIG_WITH_SEARCH,
                search_terms=["water", "supply"],
            )

        assert len(items) == 2
        matched = [it for it in items if not it.filtered]
        filtered = [it for it in items if it.filtered]
        assert len(matched) == 1
        assert matched[0].title == "First Article About Water Supply"
        assert len(filtered) == 1
        assert filtered[0].filter_reason == "no match"

    def test_fetch_source_no_search_terms(self):
        detail_1_url = BASE_URL + "/news/detail-1.html"
        detail_2_url = BASE_URL + "/news/detail-2.html"
        with aioresponses() as m:
            m.get(BASE_URL, body=LIST_HTML)
            m.get(detail_1_url, body=DETAIL_1_HTML)
            m.get(detail_2_url, body=DETAIL_2_HTML)
            items = fetch_source(SOURCE_CONFIG)

        assert len(items) == 2
        assert all(it.filtered is False for it in items)
