"""CLI entrypoint for the base-life scraper.

Reads `config.json` and prints a JSON array of matched news items.
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

from base_life import scraper


def load_config(path: Path) -> Dict[str, Any]:
    """Load JSON configuration from ``path``.

    Raises a :class:`ValueError` if the file cannot be read or parsed.
    """
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run(config_path: str = "config.json") -> None:
    """Run the scraper using the configuration at ``config_path``.

    Results are printed to stdout as pretty JSON.
    """
    cfg = load_config(Path(config_path))
    sources = cfg.get("sources", [])
    all_items: list[Dict[str, Any]] = []

    for src in sources:
        items = scraper.parse_source(src)
        search_terms = src.get("selectors", {}).get("search", [])
        filtered = scraper.filter_by_search(items, search_terms)
        all_items.extend(filtered)

    print(json.dumps(all_items, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    cfg_arg = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    run(cfg_arg)
