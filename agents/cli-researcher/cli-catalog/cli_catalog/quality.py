from __future__ import annotations

from collections import Counter

from cli_catalog.models import CliEntry


LIST_NAME_PREFIXES = ("awesome-", "awesome_", "awesome ")
LIST_DESCRIPTION_HINTS = ("curated list", "awesome list", "collection of", "list of")


def is_likely_resource_list(entry: CliEntry) -> bool:
    name = entry.name.lower().strip()
    repo_name = entry.id.split("/")[-1].lower()
    description = entry.description.lower()

    if name == "awesome" or repo_name == "awesome":
        return True
    if name.startswith(LIST_NAME_PREFIXES) or repo_name.startswith(LIST_NAME_PREFIXES):
        return True
    if "awesome-list" in entry.tags and any(hint in description for hint in LIST_DESCRIPTION_HINTS):
        return True
    return False


def effective_agent_score(entry: CliEntry) -> int:
    if is_likely_resource_list(entry):
        return min(entry.agent_score, 1)
    return entry.agent_score


def quality_report(entries: dict[str, CliEntry]) -> list[str]:
    entry_list = list(entries.values())
    empty_descriptions = [entry for entry in entry_list if not entry.description.strip()]
    likely_lists = [entry for entry in entry_list if is_likely_resource_list(entry)]
    high_score_lists = [entry for entry in likely_lists if entry.agent_score >= 3]
    categories = Counter(entry.category for entry in entry_list)

    lines = [
        "# Catalog Quality Report",
        "",
        f"Total entries: {len(entry_list)}",
        f"Empty descriptions: {len(empty_descriptions)}",
        f"Likely resource-list entries: {len(likely_lists)}",
        f"High-score likely resource-list entries: {len(high_score_lists)}",
        f"Categories: {len(categories)}",
        "",
        "## Largest Categories",
    ]
    for category, count in categories.most_common(15):
        lines.append(f"- {category}: {count}")

    lines.extend(["", "## High-Score Likely Resource Lists"])
    if high_score_lists:
        for entry in sorted(high_score_lists, key=lambda item: (-(item.github_stars or 0), item.id.lower()))[:25]:
            lines.append(f"- score={entry.agent_score} stars={entry.github_stars or 0} {entry.id} ({entry.name})")
    else:
        lines.append("- None")

    lines.extend(["", "## Empty Description Examples"])
    if empty_descriptions:
        for entry in sorted(empty_descriptions, key=lambda item: (-item.agent_score, item.name.lower()))[:25]:
            lines.append(f"- score={entry.agent_score} {entry.id} ({entry.name}) category={entry.category}")
    else:
        lines.append("- None")

    return lines
