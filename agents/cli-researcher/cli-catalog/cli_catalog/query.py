from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from cli_catalog.models import CliEntry, entry_filename
from cli_catalog.quality import effective_agent_score
from cli_catalog.summary import load_summary_category_aliases, normalize_summary_category


@dataclass
class SearchOptions:
    query: str = ""
    category: str = ""
    agent_only: bool = False
    limit: int = 20


def _haystack(entry: CliEntry) -> str:
    parts = [
        entry.id,
        entry.name,
        entry.description,
        entry.category,
        " ".join(entry.aliases),
        " ".join(entry.tags),
        " ".join(entry.agent_signals),
    ]
    return " ".join(parts).lower()


def _score_entry(entry: CliEntry, query: str) -> int:
    if not query:
        return 0
    needle = query.lower()
    score = 0
    if needle == entry.id.lower():
        score += 100
    if needle == entry.name.lower():
        score += 80
    if needle in (alias.lower() for alias in entry.aliases):
        score += 70
    if needle in entry.id.lower():
        score += 40
    if needle in entry.name.lower():
        score += 35
    if needle in entry.description.lower():
        score += 20
    if needle in entry.category.lower():
        score += 10
    if any(needle in tag.lower() for tag in entry.tags):
        score += 10
    return score


def search_entries(
    entries: dict[str, CliEntry],
    options: SearchOptions,
    category_aliases: dict[str, str] | None = None,
) -> list[CliEntry]:
    query = options.query.strip().lower()
    category = options.category.strip().lower()
    matches: list[CliEntry] = []

    for entry in entries.values():
        if options.agent_only and not entry.agent_friendly:
            continue
        normalized_category = normalize_summary_category(entry.category, category_aliases)
        if category and category not in entry.category.lower() and category not in normalized_category.lower():
            continue
        if query and query not in _haystack(entry):
            continue
        matches.append(entry)

    matches.sort(
        key=lambda entry: (
            -_score_entry(entry, query),
            -effective_agent_score(entry),
            -(entry.github_stars or 0),
            entry.name.lower(),
        )
    )
    return matches[: max(options.limit, 0)]


def search_catalog(entries: dict[str, CliEntry], options: SearchOptions) -> list[CliEntry]:
    return search_entries(entries, options, load_summary_category_aliases())


def display_category(entry: CliEntry, category_aliases: dict[str, str] | None = None) -> str:
    normalized = normalize_summary_category(entry.category, category_aliases)
    if normalized != entry.category:
        return f"{normalized} (from {entry.category})"
    return entry.category


def find_entry(entries: dict[str, CliEntry], key: str) -> CliEntry | None:
    needle = key.strip().lower()
    if not needle:
        return None

    for entry in entries.values():
        if entry.id.lower() == needle:
            return entry
    for entry in entries.values():
        if entry.name.lower() == needle or needle in (alias.lower() for alias in entry.aliases):
            return entry
    for entry in entries.values():
        if needle in entry.id.lower() or needle in entry.name.lower():
            return entry
    return None


def entry_detail_path(data_dir: Path, entry: CliEntry) -> Path:
    return data_dir / entry_filename(entry.id)


def entry_detail_json(data_dir: Path, entry: CliEntry) -> str:
    path = entry_detail_path(data_dir, entry)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return json.dumps(entry.to_dict(), indent=2, ensure_ascii=False) + "\n"


def format_search_results(entries: list[CliEntry], category_aliases: dict[str, str] | None = None) -> str:
    if not entries:
        return "No matching CLIs found."

    lines = ["Score | CLI | Category | Function | ID", "----- | --- | -------- | -------- | --"]
    for entry in entries:
        description = entry.description.replace("\n", " ").strip() or f"{entry.category} CLI tool."
        if len(description) > 100:
            description = description[:97].rstrip() + "..."
        lines.append(
            f"{effective_agent_score(entry)} | {entry.name} | "
            f"{display_category(entry, category_aliases)} | {description} | {entry.id}"
        )
    return "\n".join(lines)
