from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from cli_catalog.models import CliEntry
from cli_catalog.quality import effective_agent_score

SUMMARY_SCHEMA_VERSION = 4
SUMMARY_DESCRIPTION = "Readable CLI routing index grouped by category. Read detail JSON for full metadata."
SUMMARY_COLUMNS = ["id", "cli", "function", "score"]
DETAIL_TEMPLATE = "catalog/data/{id with '/' replaced by '__'}.json"
MAX_FUNCTION_CHARS = 140


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _clip_text(text: str, max_chars: int = MAX_FUNCTION_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def _function_text(entry: CliEntry) -> str:
    description = _clean_text(entry.description)
    if description:
        return _clip_text(description)

    return _clip_text(f"{entry.category} CLI tool.")


def load_summary_category_aliases(config_dir: Path | None = None) -> dict[str, str]:
    if config_dir is None:
        config_dir = Path(__file__).resolve().parent.parent / "config"
    path = config_dir / "summary_categories.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    aliases = data.get("aliases", {})
    return {str(source): str(target) for source, target in aliases.items()}


def normalize_summary_category(category: str, aliases: dict[str, str] | None = None) -> str:
    if not aliases:
        return category
    return aliases.get(category, category)


def summary_record(entry: CliEntry, category: str | None = None) -> list[Any]:
    display_category = category or entry.category
    function = _function_text(entry)
    if not _clean_text(entry.description) and display_category != entry.category:
        function = _clip_text(f"{display_category} CLI tool.")
    return [
        entry.id,
        entry.name,
        function,
        effective_agent_score(entry),
    ]


def build_cli_summary(
    entries: list[CliEntry] | dict[str, CliEntry],
    state: dict,
    category_aliases: dict[str, str] | None = None,
) -> dict[str, Any]:
    if isinstance(entries, dict):
        entry_list = list(entries.values())
    else:
        entry_list = list(entries)

    entry_list.sort(key=lambda e: (-effective_agent_score(e), -(e.github_stars or 0), e.name.lower()))
    grouped: dict[str, list[CliEntry]] = defaultdict(list)
    for entry in entry_list:
        grouped[normalize_summary_category(entry.category, category_aliases)].append(entry)

    categories = [
        {
            "name": category,
            "count": len(category_entries),
            "columns": SUMMARY_COLUMNS,
            "rows": [summary_record(entry, category) for entry in category_entries],
        }
        for category, category_entries in sorted(grouped.items())
    ]

    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "description": SUMMARY_DESCRIPTION,
        "detail_template": DETAIL_TEMPLATE,
        "counts": {
            "total": len(entry_list),
            "agent_friendly": sum(1 for entry in entry_list if entry.agent_friendly),
            "categories": len(categories),
        },
        "categories": categories,
    }


def render_cli_summary(entries: list[CliEntry] | dict[str, CliEntry], output: Path, state: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    summary = build_cli_summary(entries, state, load_summary_category_aliases())
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
