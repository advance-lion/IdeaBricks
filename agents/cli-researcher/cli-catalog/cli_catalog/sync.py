from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from cli_catalog.categorize import load_category_groups, load_json
from cli_catalog.curate import apply_curated_overrides
from cli_catalog.github_client import github_raw, latest_commit
from cli_catalog.merge import apply_agent_boost, collect_boost_ids, merge_entries
from cli_catalog.models import CliEntry, entry_filename, parse_github_id
from cli_catalog.parsers.cli_anything_registry import parse_cli_anything_registry
from cli_catalog.parsers.readme import parse_ai_cli_readme, parse_awesome_readme, parse_composio_readme
from cli_catalog.parsers.toolleeo_csv import parse_toolleeo_csv
from cli_catalog.render import render_catalog_markdown
from cli_catalog.stars import update_github_stars
from cli_catalog.summary import render_cli_summary


def _fetch_readme(repo: str, branch: str, file_path: str) -> str:
    candidates = [file_path]
    if file_path.lower() == "readme.md":
        candidates = ["README.md", "readme.md", "Readme.md"]
    last_error: Exception | None = None
    for candidate in candidates:
        try:
            return github_raw(repo, branch, candidate)
        except Exception as exc:  # noqa: BLE001 - try fallbacks
            last_error = exc
    raise last_error or RuntimeError(f"Could not fetch readme for {repo}")


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def load_existing_entries(data_dir: Path) -> dict[str, CliEntry]:
    entries: dict[str, CliEntry] = {}
    if not data_dir.exists():
        return entries
    for path in data_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        entry = CliEntry.from_dict(data)
        entries[entry.id] = entry
    return entries


def save_entry(data_dir: Path, entry: CliEntry) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / entry_filename(entry.id)
    path.write_text(json.dumps(entry.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_state(state_path: Path) -> dict:
    if state_path.exists():
        return json.loads(state_path.read_text(encoding="utf-8"))
    return {"version": 1, "sources": {}, "stats": {}}


def save_state(state_path: Path, state: dict) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def source_priority_map(config: dict) -> dict[str, int]:
    return {source["id"]: int(source.get("priority", 100)) for source in config.get("sources", [])}


def sync(*, force: bool = False, sources_filter: list[str] | None = None, skip_stars: bool = False) -> dict:
    root = project_root()
    config_dir = root / "config"
    data_dir = root / "catalog" / "data"
    state_path = root / "state" / "sources.json"
    catalog_md = root / "catalog" / "cli-catalog.md"
    summary_json = root / "catalog" / "cli-summary.json"
    changelog_path = root / "meta" / "changelog.md"

    config = load_json(config_dir / "sources.json")
    source_priorities = source_priority_map(config)
    slug_to_group, default_group = load_category_groups(config_dir)
    existing = load_existing_entries(data_dir)
    state = load_state(state_path)

    agent_tool_ids, anchor_ids = collect_boost_ids(existing)
    parsed_total = 0
    updated_sources: list[str] = []
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    added = 0
    updated = 0

    for source in config.get("sources", []):
        source_id = source["id"]
        if sources_filter and source_id not in sources_filter:
            continue

        repo = source["repo"]
        branch = source.get("branch", "master")
        parser = source["parser"]
        commit = latest_commit(repo, branch)
        prev_commit = state.get("sources", {}).get(source_id, {}).get("commit")

        if not force and prev_commit == commit:
            continue

        updated_sources.append(source_id)
        incoming_batch: list[CliEntry] = []

        try:
            if parser == "toolleeo_csv":
                apps_csv = github_raw(repo, branch, "data/apps.csv")
                categories_csv = github_raw(repo, branch, "data/categories.csv")
                incoming_batch = parse_toolleeo_csv(
                    apps_csv,
                    categories_csv,
                    source_id=source_id,
                    source_repo=repo,
                    commit=commit,
                    slug_to_group=slug_to_group,
                    default_group=default_group,
                )
            elif parser == "awesome_readme":
                readme = _fetch_readme(repo, branch, source["files"][0])
                incoming_batch = parse_awesome_readme(
                    readme,
                    source_id=source_id,
                    source_repo=repo,
                    commit=commit,
                )
                if source_id == "modern-unix":
                    anchor_ids.update(e.id for e in incoming_batch)
            elif parser == "ai_cli_readme":
                readme = github_raw(repo, branch, source["files"][0])
                batch, ids = parse_ai_cli_readme(
                    readme,
                    source_id=source_id,
                    source_repo=repo,
                    commit=commit,
                )
                incoming_batch = batch
                agent_tool_ids.update(ids)
            elif parser == "composio_readme":
                readme = github_raw(repo, branch, source["files"][0])
                batch, ids = parse_composio_readme(
                    readme,
                    source_id=source_id,
                    source_repo=repo,
                    commit=commit,
                )
                incoming_batch = batch
                agent_tool_ids.update(ids)
            elif parser == "cli_anything_registry":
                registry_json = github_raw(repo, branch, "registry.json")
                public_registry_json = github_raw(repo, branch, "public_registry.json")
                incoming_batch = parse_cli_anything_registry(
                    registry_json,
                    public_registry_json,
                    source_id=source_id,
                    source_repo=repo,
                    commit=commit,
                    slug_to_group=slug_to_group,
                    default_group=default_group,
                )
                for entry in incoming_batch:
                    agent_tool_ids.add(entry.id)
                    agent_tool_ids.add(entry.name.lower())
            else:
                raise ValueError(f"Unknown parser: {parser}")
        except Exception as exc:  # noqa: BLE001 - continue other sources
            print(f"Warning: failed to sync {source_id}: {exc}")
            updated_sources.pop()
            continue

        parsed_total += len(incoming_batch)

        for incoming in incoming_batch:
            if not incoming.id:
                incoming.id = parse_github_id(incoming.repo_url) or incoming.name
            apply_agent_boost(incoming, agent_tool_ids, anchor_ids)
            prev = existing.get(incoming.id)
            merged = merge_entries(prev, incoming, source_priorities)
            if prev is None:
                added += 1
            else:
                updated += 1
            existing[incoming.id] = merged

        state.setdefault("sources", {})[source_id] = {
            "repo": repo,
            "commit": commit,
            "synced_at": now,
            "entry_count": len(incoming_batch),
        }

    # Second pass: apply agent boosts to all entries after all sources loaded
    for entry in existing.values():
        apply_agent_boost(entry, agent_tool_ids, anchor_ids)

    apply_curated_overrides(existing)

    stars_stats: dict[str, int | bool] = {}
    if not skip_stars:
        stars_stats = update_github_stars(existing, updated_at=now)

    for entry in existing.values():
        save_entry(data_dir, entry)

    agent_friendly_count = sum(1 for e in existing.values() if e.agent_friendly)
    categories = sorted({e.category for e in existing.values()})

    state["last_run_at"] = now
    state["stats"] = {
        "total_unique_clis": len(existing),
        "agent_friendly_count": agent_friendly_count,
        "category_count": len(categories),
    }
    save_state(state_path, state)

    render_catalog_markdown(existing.values(), catalog_md, state)
    render_cli_summary(existing.values(), summary_json, state)

    changelog = _build_changelog(
        now=now,
        updated_sources=updated_sources,
        added=added,
        updated=updated,
        total=len(existing),
        force=force,
        stars_stats=stars_stats,
    )
    changelog_path.parent.mkdir(parents=True, exist_ok=True)
    changelog_path.write_text(changelog, encoding="utf-8")

    return {
        "sources_updated": updated_sources,
        "parsed_rows": parsed_total,
        "added": added,
        "updated": updated,
        "total": len(existing),
        "agent_friendly": agent_friendly_count,
        "skipped": not updated_sources and not force,
        "stars": stars_stats,
    }


def _build_changelog(
    *,
    now: str,
    updated_sources: list[str],
    added: int,
    updated: int,
    total: int,
    force: bool,
    stars_stats: dict[str, int | bool] | None = None,
) -> str:
    lines = [
        "# Sync Changelog",
        "",
        f"## {now.split('T')[0]}",
        "",
        f"**Trigger:** manual{' (force)' if force else ''}",
        "",
        "### Sources updated",
    ]
    if updated_sources:
        for source in updated_sources:
            lines.append(f"- {source}")
    else:
        lines.append("- (no upstream changes detected)")

    lines.extend(
        [
            "",
            "### Catalog changes",
            f"- Added: {added}",
            f"- Updated: {updated}",
            f"- Total unique CLIs: {total}",
        ]
    )

    if stars_stats:
        lines.extend(
            [
                "",
                "### GitHub stars refresh",
                f"- Unique repos: {stars_stats.get('repos_total', 0)}",
                f"- Repos fetched: {stars_stats.get('repos_fetched', 0)}",
                f"- Entries updated: {stars_stats.get('entries_updated', 0)}",
                f"- Rate limited: {stars_stats.get('rate_limited', False)}",
            ]
        )

    lines.append("")
    return "\n".join(lines)
