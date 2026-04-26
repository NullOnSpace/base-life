"""CLI entrypoint for the base-life scraper.

Reads `config.toml` and prints a JSON array of `NewsItem` objects.
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import tomllib

from base_life import scraper


def load_config_toml(path: Path) -> Dict[str, Any]:
    """Load TOML configuration from ``path``.

    Raises :class:`tomllib.TOMLDecodeError` if the file cannot be parsed,
    or :class:`FileNotFoundError`/:class:`OSError` if the file cannot be read.
    """
    with path.open("rb") as f:
        return tomllib.load(f)


def run(config_path: str = "config.toml") -> None:
    """Run the scraper using the TOML configuration at ``config_path``.

    Results are printed to stdout as pretty JSON. The TOML file should
    contain a top-level `[[sources]]` array of tables and an optional
    `[logging]` table with `level`.
    """
    cfg = load_config_toml(Path(config_path))

    log_cfg = cfg.get("logging", {}) or {}
    scraper.setup_logging(log_cfg.get("level"))

    sources: List[Dict[str, Any]] = cfg.get("sources", []) or []
    all_items: List[Dict[str, Any]] = []

    for src in sources:
        search_terms = src.get("selectors", {}).get("search", [])
        items = scraper.fetch_source(src, search_terms=search_terms)
        all_items.extend([it.to_dict() for it in items])

    print(json.dumps(all_items, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="base-life news scraper – reads config.toml and outputs JSON"
    )
    parser.add_argument(
        "config",
        nargs="?",
        default="config.toml",
        help="Path to TOML configuration file (default: config.toml)",
    )
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
