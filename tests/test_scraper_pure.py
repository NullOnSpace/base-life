"""Tests for scraper pure functions (no network requests)."""

from bs4 import BeautifulSoup

from base_life.scraper import (
    NewsItem,
    _extract_links,
    _item_search_text,
    _matches_search,
    _merge_headers,
    _pub_format_to_regex,
    _select_with_contains,
    default_headers,
    extract_pub_time,
    filter_by_search,
    unfiltered_items,
)
from tests.conftest import (
    LIST_HTML,
    SOURCE_CONFIG,
)


class TestSelectWithContains:
    def test_plain_selector(self):
        html = "<div><p class='target'>hello</p><p>world</p></div>"
        soup = BeautifulSoup(html, "lxml")
        result = _select_with_contains(soup, "p.target")
        assert len(result) == 1
        assert result[0].get_text() == "hello"

    def test_contains_selector(self):
        html = "<div><p>发布日期：2025</p><p>其他信息</p></div>"
        soup = BeautifulSoup(html, "lxml")
        result = _select_with_contains(soup, "p:contains('发布日期')")
        assert len(result) == 1
        assert "发布日期" in result[0].get_text()

    def test_contains_with_double_quotes(self):
        html = "<div><span>发布日期</span><span>更新时间</span></div>"
        soup = BeautifulSoup(html, "lxml")
        result = _select_with_contains(soup, 'span:contains("发布日期")')
        assert len(result) == 1

    def test_contains_with_prefix_selector(self):
        html = (
            "<div align='center'>发布日期：2025</div>"
            "<div align='left'>发布日期：2024</div>"
            "<p>发布日期：2023</p>"
        )
        soup = BeautifulSoup(html, "lxml")
        result = _select_with_contains(soup, 'div[align="center"]:contains("发布日期")')
        assert len(result) == 1
        assert "2025" in result[0].get_text()

    def test_contains_no_prefix(self):
        html = "<div>apple</div><span>banana</span><p>cherry</p>"
        soup = BeautifulSoup(html, "lxml")
        result = _select_with_contains(soup, ":contains('banana')")
        banana_elements = [el for el in result if "banana" in el.get_text()]
        assert len(banana_elements) >= 1
        assert any(el.name == "span" for el in banana_elements)

    def test_contains_no_match(self):
        html = "<div><p>hello</p></div>"
        soup = BeautifulSoup(html, "lxml")
        result = _select_with_contains(soup, "p:contains('missing')")
        assert len(result) == 0

    def test_no_contains_delegates_to_select(self):
        html = "<div><p class='a'>x</p><p class='b'>y</p></div>"
        soup = BeautifulSoup(html, "lxml")
        result = _select_with_contains(soup, "p.a")
        assert len(result) == 1
        assert result[0].get_text() == "x"


class TestPubFormatToRegex:
    def test_simple_date_format(self):
        regex, strptime = _pub_format_to_regex("yyyy-mo-dd")
        assert "?P<Y>" in regex
        assert "?P<m>" in regex
        assert "?P<d>" in regex
        assert "%Y" in strptime
        assert "%m" in strptime
        assert "%d" in strptime

    def test_full_datetime_format(self):
        regex, strptime = _pub_format_to_regex("yyyy-mo-dd hh:mi:ss")
        assert "?P<Y>" in regex
        assert "?P<m>" in regex
        assert "?P<d>" in regex
        assert "?P<H>" in regex
        assert "?P<M>" in regex
        assert "?P<S>" in regex
        assert "%Y" in strptime
        assert "%m" in strptime
        assert "%d" in strptime
        assert "%H" in strptime
        assert "%M" in strptime
        assert "%S" in strptime

    def test_token_names_are_intuitive(self):
        regex, strptime = _pub_format_to_regex("yyyy-mo-dd hh:mi")
        assert "?P<m>" in regex and "%m" in strptime
        assert "?P<M>" in regex and "%M" in strptime

    def test_literal_chars_preserved(self):
        regex, strptime = _pub_format_to_regex("yyyy-mo-dd")
        assert "?P<Y>" in regex
        assert "%Y" in strptime


class TestExtractPubTime:
    def test_simple_date(self):
        result = extract_pub_time("2025-04-26", "yyyy-mo-dd")
        assert result == "2025-04-26T00:00:00"

    def test_datetime_with_time(self):
        result = extract_pub_time("2025-04-26 08:30", "yyyy-mo-dd hh:mi")
        assert result == "2025-04-26T08:30:00"

    def test_datetime_with_seconds(self):
        result = extract_pub_time("2025-03-15 10:30:00", "yyyy-mo-dd hh:mi:ss")
        assert result == "2025-03-15T10:30:00"

    def test_text_with_embedded_date(self):
        text = "发布日期：2025-04-26 08:30"
        result = extract_pub_time(text, "yyyy-mo-dd hh:mi")
        assert result == "2025-04-26T08:30:00"

    def test_fallback_iso_format(self):
        text = "some text 2025-04-26 10:30 embedded"
        result = extract_pub_time(text, "yyyy-mo-dd")
        assert result is not None
        assert "2025" in result

    def test_fallback_date_only(self):
        text = "published on 2025-04-26"
        result = extract_pub_time(text, "yyyy-mo-dd hh:mi")
        assert result is not None
        assert "2025" in result

    def test_empty_text_returns_none(self):
        assert extract_pub_time("", "yyyy-mo-dd") is None

    def test_no_match_returns_none(self):
        assert extract_pub_time("no date here", "yyyy-mo-dd") is None

    def test_invalid_date_value_returns_none(self):
        result = extract_pub_time("9999-99-99", "yyyy-mo-dd")
        assert result is None


class TestExtractLinks:
    def test_basic_link_extraction(self):
        soup = BeautifulSoup(LIST_HTML, "lxml")
        links = _extract_links(soup, "div.list-content ul li a", SOURCE_CONFIG["url"])
        assert len(links) == 2
        assert "/news/detail-1.html" in links[0]
        assert "/news/detail-2.html" in links[1]

    def test_links_resolved_with_base_url(self):
        soup = BeautifulSoup(LIST_HTML, "lxml")
        links = _extract_links(soup, "div.list-content ul li a", "https://example.com")
        assert links[0] == "https://example.com/news/detail-1.html"
        assert links[1] == "https://example.com/news/detail-2.html"

    def test_base_tag_href(self):
        html = (
            '<head><base href="https://cdn.example.com/"></head>'
            '<body><a href="/page.html">link</a></body>'
        )
        soup = BeautifulSoup(html, "lxml")
        links = _extract_links(soup, "a", "https://example.com")
        assert links[0] == "https://cdn.example.com/page.html"

    def test_no_list_selector_returns_empty(self):
        soup = BeautifulSoup("<div><a href='/x'>x</a></div>", "lxml")
        links = _extract_links(soup, None, "https://example.com")
        assert links == []

    def test_no_matching_elements_returns_empty(self):
        soup = BeautifulSoup("<div>no links here</div>", "lxml")
        links = _extract_links(soup, "a.nonexistent", "https://example.com")
        assert links == []

    def test_contains_selector_in_list(self):
        html = '<div><a href="/a">Water Notice</a><a href="/b">Other</a></div>'
        soup = BeautifulSoup(html, "lxml")
        links = _extract_links(soup, "a:contains('Water')", "https://example.com")
        assert len(links) == 1
        assert links[0] == "https://example.com/a"


class TestMergeHeaders:
    def test_default_headers_only(self):
        source = {"name": "test"}
        result = _merge_headers(source)
        assert "User-Agent" in result
        assert result["User-Agent"].startswith("Mozilla")

    def test_source_headers_override(self):
        source = {"name": "test", "headers": {"User-Agent": "CustomBot"}}
        result = _merge_headers(source)
        assert result["User-Agent"] == "CustomBot"

    def test_source_headers_add_new(self):
        source = {"name": "test", "headers": {"X-Custom": "value"}}
        result = _merge_headers(source)
        assert "X-Custom" in result
        assert "User-Agent" in result

    def test_empty_headers_dict(self):
        source = {"name": "test", "headers": {}}
        result = _merge_headers(source)
        assert result == default_headers()


class TestMatchesSearch:
    def test_match_found(self):
        assert _matches_search("hello water world", ["water"]) is True

    def test_match_not_found(self):
        assert _matches_search("hello world", ["water"]) is False

    def test_case_insensitive(self):
        assert _matches_search("water supply", ["water"]) is True

    def test_uppercase_text_not_matched(self):
        assert _matches_search("WATER supply", ["water"]) is False

    def test_multiple_terms_any_match(self):
        assert _matches_search("road repair", ["water", "road"]) is True

    def test_multiple_terms_no_match(self):
        assert _matches_search("happy day", ["water", "road"]) is False

    def test_empty_terms(self):
        assert _matches_search("anything", []) is False


class TestItemSearchText:
    def test_both_title_and_content(self):
        result = _item_search_text("Water Supply", "Residents affected")
        assert result == "water supply residents affected"

    def test_only_title(self):
        result = _item_search_text("Water Supply", None)
        assert result == "water supply"

    def test_only_content(self):
        result = _item_search_text(None, "Residents affected")
        assert result == "residents affected"

    def test_both_none(self):
        result = _item_search_text(None, None)
        assert result == ""


class TestNewsItem:
    def test_to_dict(self):
        item = NewsItem(
            source="test",
            url="https://example.com",
            title="Title",
            pub="2025-04-26T00:00:00",
            content="Content",
            filtered=False,
            filter_reason=None,
        )
        d = item.to_dict()
        assert d["source"] == "test"
        assert d["url"] == "https://example.com"
        assert d["title"] == "Title"
        assert d["pub"] == "2025-04-26T00:00:00"
        assert d["content"] == "Content"
        assert d["filtered"] is False
        assert d["filter_reason"] is None

    def test_defaults(self):
        item = NewsItem()
        assert item.source is None
        assert item.filtered is False
        assert item.filter_reason is None

    def test_dataclass_equality(self):
        a = NewsItem(source="x", title="t")
        b = NewsItem(source="x", title="t")
        assert a == b


class TestFilterBySearch:
    def test_match_terms(self):
        items = [
            {"title": "Water Supply Notice", "content": "Maintenance scheduled"},
            {"title": "Road Repair Update", "content": "Traffic detour posted"},
        ]
        result = filter_by_search(items, ["water"])
        assert len(result) == 1
        assert result[0]["title"] == "Water Supply Notice"

    def test_no_terms_returns_all(self):
        items = [{"title": "A"}, {"title": "B"}]
        result = filter_by_search(items, [])
        assert len(result) == 2

    def test_case_insensitive(self):
        items = [{"title": "WATER NOTICE", "content": None}]
        result = filter_by_search(items, ["water"])
        assert len(result) == 1

    def test_content_search(self):
        items = [{"title": "Notice", "content": "water supply info"}]
        result = filter_by_search(items, ["supply"])
        assert len(result) == 1


class TestUnfilteredItems:
    def test_returns_only_unfiltered(self):
        items = [
            NewsItem(title="A", filtered=False),
            NewsItem(title="B", filtered=True, filter_reason="no match"),
            NewsItem(title="C", filtered=False),
        ]
        result = unfiltered_items(items)
        assert len(result) == 2
        assert all(it.filtered is False for it in result)

    def test_all_unfiltered(self):
        items = [NewsItem(title="A"), NewsItem(title="B")]
        result = unfiltered_items(items)
        assert len(result) == 2

    def test_all_filtered(self):
        items = [
            NewsItem(title="A", filtered=True, filter_reason="no match"),
        ]
        result = unfiltered_items(items)
        assert len(result) == 0
