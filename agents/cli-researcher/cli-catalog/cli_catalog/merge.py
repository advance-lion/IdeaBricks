from __future__ import annotations

from cli_catalog.models import CliEntry

DEFAULT_SOURCE_PRIORITY = 100


def _entry_priority(entry: CliEntry, source_priorities: dict[str, int] | None) -> int:
    if not source_priorities or not entry.sources:
        return DEFAULT_SOURCE_PRIORITY
    return min(source_priorities.get(source.id, DEFAULT_SOURCE_PRIORITY) for source in entry.sources)


def _merge_install(
    merged: CliEntry,
    incoming: CliEntry,
    *,
    incoming_can_replace: bool,
) -> None:
    for manager, command in incoming.install.items():
        if manager not in merged.install or incoming_can_replace:
            merged.install[manager] = command


def merge_entries(
    existing: CliEntry | None,
    incoming: CliEntry,
    source_priorities: dict[str, int] | None = None,
) -> CliEntry:
    if existing is None:
        return incoming

    merged = CliEntry.from_dict(existing.to_dict())
    existing_priority = _entry_priority(existing, source_priorities)
    incoming_priority = _entry_priority(incoming, source_priorities)
    incoming_can_replace = incoming_priority <= existing_priority

    if not merged.manual_edit:
        if incoming.description and (incoming_can_replace or not merged.description):
            merged.description = incoming.description
        if incoming.homepage and (incoming_can_replace or not merged.homepage):
            merged.homepage = incoming.homepage
        if incoming.install:
            _merge_install(merged, incoming, incoming_can_replace=incoming_can_replace)

    if not merged.locked_category and incoming.category:
        if incoming_can_replace or merged.category == "Other":
            merged.category = incoming.category

    merged.aliases = sorted(set(merged.aliases + incoming.aliases))
    merged.tags = sorted(set(merged.tags + incoming.tags))
    merged.agent_score = max(merged.agent_score, incoming.agent_score)
    merged.agent_friendly = merged.agent_friendly or incoming.agent_friendly
    merged.agent_signals = sorted(set(merged.agent_signals + incoming.agent_signals))
    if incoming.skill_url:
        merged.skill_url = incoming.skill_url

    seen = {(s.id, s.repo) for s in merged.sources}
    for source in incoming.sources:
        key = (source.id, source.repo)
        if key not in seen:
            merged.sources.append(source)
            seen.add(key)

    merged.updated_at = incoming.updated_at or merged.updated_at
    merged.status = incoming.status
    return merged


def apply_agent_boost(entry: CliEntry, agent_tool_ids: set[str], anchor_ids: set[str]) -> None:
    repo_id = entry.id
    name_key = entry.name.lower()

    if repo_id in agent_tool_ids or name_key in agent_tool_ids:
        entry.agent_score = max(entry.agent_score, 3)
        entry.agent_friendly = True
        if "curated-agent-list" not in entry.agent_signals:
            entry.agent_signals.append("curated-agent-list")

    if repo_id in anchor_ids:
        entry.agent_score = max(entry.agent_score, 2)
        if "modern-unix" not in entry.agent_signals:
            entry.agent_signals.append("modern-unix")

    if entry.agent_score >= 3:
        entry.agent_friendly = True


def collect_boost_ids(entries: dict[str, CliEntry]) -> tuple[set[str], set[str]]:
    """Preserve agent/anchor boosts across incremental syncs."""
    agent_tool_ids: set[str] = set()
    anchor_ids: set[str] = set()
    for entry in entries.values():
        if entry.agent_score >= 3 or "curated-agent-list" in entry.agent_signals or "cli-anything" in entry.agent_signals:
            agent_tool_ids.add(entry.id)
            agent_tool_ids.add(entry.name.lower())
        if "modern-unix" in entry.agent_signals or "modern-unix" in entry.tags:
            anchor_ids.add(entry.id)
    return agent_tool_ids, anchor_ids
