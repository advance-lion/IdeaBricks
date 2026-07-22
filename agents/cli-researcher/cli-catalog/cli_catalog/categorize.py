from __future__ import annotations

import json
from pathlib import Path

from cli_catalog.models import CliEntry


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_category_groups(config_dir: Path) -> tuple[dict[str, str], str]:
    data = load_json(config_dir / "category_groups.json")
    slug_to_group: dict[str, str] = {}
    for group, slugs in data.get("groups", {}).items():
        for slug in slugs:
            slug_to_group[slug] = group
    default_group = data.get("default_group", "Other")
    return slug_to_group, default_group


def categorize(upstream_slug: str, slug_to_group: dict[str, str], default_group: str) -> str:
    return slug_to_group.get(upstream_slug, default_group)


def derive_tags(entry: CliEntry, upstream_slug: str = "") -> list[str]:
    tags = set(entry.tags)
    if upstream_slug:
        tags.add(upstream_slug)
    desc = entry.description.lower()
    if any(k in desc for k in ("json", "yaml", "structured output")):
        tags.add("json")
    if any(k in desc for k in ("mcp", "model context protocol")):
        tags.add("mcp")
    if "non-interactive" in entry.agent_signals or "non-interactive" in desc:
        tags.add("non-interactive")
    return sorted(tags)[:5]
