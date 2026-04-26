"""Tests for main.py CLI and runner functions."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import tomllib

from main import load_config_toml, main, run

MOCK_TOML_CONTENT = """
[logging]
level = "DEBUG"

[[sources]]
name = "mock-source"
url = "https://example.com"

[sources.selectors]
list_selector = "div.list-content ul li a"
title = "h1.arti-title"
pub = "span.arti-update"
pub-format = "YYYY-mm-dd"
content = "div.arti-articlecontent"
"""

MOCK_NEWS_ITEMS = [
    {
        "source": "mock-source",
        "url": "https://example.com/news/1.html",
        "title": "Mock Article One",
        "pub": "2025-04-26T00:00:00",
        "content": "Mock content one",
        "filtered": False,
        "filter_reason": None,
    },
    {
        "source": "mock-source",
        "url": "https://example.com/news/2.html",
        "title": "Mock Article Two",
        "pub": "2025-03-15T10:30:00",
        "content": "Mock content two",
        "filtered": True,
        "filter_reason": "no match",
    },
]


class TestLoadConfigToml:
    def test_load_valid_toml(self, tmp_path: Path):
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text(MOCK_TOML_CONTENT, encoding="utf-8")
        result = load_config_toml(cfg_file)
        assert "sources" in result
        assert result["sources"][0]["name"] == "mock-source"
        assert result["logging"]["level"] == "DEBUG"

    def test_load_nonexistent_file_raises(self):
        with patch("main.Path.open", side_effect=FileNotFoundError):
            try:
                load_config_toml(Path("/nonexistent/config.toml"))
                assert False, "Should have raised FileNotFoundError"
            except FileNotFoundError:
                pass

    def test_load_invalid_toml_raises(self, tmp_path: Path):
        cfg_file = tmp_path / "bad.toml"
        cfg_file.write_text("[[[invalid", encoding="utf-8")
        try:
            load_config_toml(cfg_file)
            assert False, "Should have raised tomllib.TOMLDecodeError"
        except tomllib.TOMLDecodeError:
            pass


class TestRun:
    def test_run_with_mocked_scraper(self, tmp_path: Path, capsys):
        cfg_file = tmp_path / "config.toml"
        cfg_file.write_text(MOCK_TOML_CONTENT, encoding="utf-8")

        mock_items = [
            MagicMock(
                to_dict=MagicMock(return_value=MOCK_NEWS_ITEMS[0]),
            ),
            MagicMock(
                to_dict=MagicMock(return_value=MOCK_NEWS_ITEMS[1]),
            ),
        ]

        with patch("main.scraper.fetch_source", return_value=mock_items) as mock_fetch:
            with patch("main.scraper.setup_logging"):
                run(str(cfg_file))

        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        assert call_args[0][0]["name"] == "mock-source"
        assert call_args[1]["search_terms"] == []

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert len(output) == 2
        assert output[0]["title"] == "Mock Article One"
        assert output[1]["filtered"] is True

    def test_run_empty_sources(self, tmp_path: Path, capsys):
        cfg_file = tmp_path / "empty.toml"
        cfg_file.write_text("[logging]\nlevel = 'INFO'\n", encoding="utf-8")

        with patch("main.scraper.setup_logging"):
            run(str(cfg_file))

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == []


class TestMain:
    def test_main_with_default_config(self):
        with patch("main.run") as mock_run:
            mock_run.return_value = None
            sys.argv = ["main.py"]
            main()
        mock_run.assert_called_once_with("config.toml")

    def test_main_with_custom_config(self):
        with patch("main.run") as mock_run:
            mock_run.return_value = None
            sys.argv = ["main.py", "/path/to/custom.toml"]
            main()
        mock_run.assert_called_once_with("/path/to/custom.toml")
