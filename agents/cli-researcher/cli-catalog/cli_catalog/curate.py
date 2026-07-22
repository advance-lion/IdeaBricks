from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from cli_catalog.models import CliEntry, entry_filename


@dataclass
class CurateResult:
    changed: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)


def load_curated_overrides(config_dir: Path | None = None) -> dict[str, dict[str, Any]]:
    if config_dir is None:
        config_dir = Path(__file__).resolve().parent.parent / "config"
    path = config_dir / "curated_overrides.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", {})
    return {str(entry_id): dict(override) for entry_id, override in entries.items()}


def _apply_override(entry: CliEntry, override: dict[str, Any]) -> bool:
    changed = False

    description = override.get("description")
    if isinstance(description, str) and description.strip() and entry.description != description.strip():
        entry.description = description.strip()
        entry.manual_edit = True
        changed = True

    homepage = override.get("homepage")
    if isinstance(homepage, str) and homepage.strip() and entry.homepage != homepage.strip():
        entry.homepage = homepage.strip()
        entry.manual_edit = True
        changed = True

    category = override.get("category")
    if isinstance(category, str) and category.strip() and entry.category != category.strip():
        entry.category = category.strip()
        entry.locked_category = True
        changed = True

    tags = override.get("tags")
    if isinstance(tags, list):
        old_tags = set(entry.tags)
        entry.tags = sorted(old_tags | {str(tag) for tag in tags if str(tag).strip()})
        changed = changed or set(entry.tags) != old_tags

    remove_tags = override.get("remove_tags")
    if isinstance(remove_tags, list):
        old_tags = set(entry.tags)
        tags_to_remove = {str(tag) for tag in remove_tags if str(tag).strip()}
        entry.tags = sorted(old_tags - tags_to_remove)
        changed = changed or set(entry.tags) != old_tags

    install = override.get("install")
    if isinstance(install, dict):
        for manager, command in install.items():
            manager_text = str(manager).strip()
            command_text = str(command).strip()
            if manager_text and command_text and entry.install.get(manager_text) != command_text:
                entry.install[manager_text] = command_text
                entry.manual_edit = True
                changed = True

    agent_score = override.get("agent_score")
    if isinstance(agent_score, int) and 1 <= agent_score <= 3 and entry.agent_score != agent_score:
        entry.agent_score = agent_score
        changed = True

    agent_friendly = override.get("agent_friendly")
    if isinstance(agent_friendly, bool) and entry.agent_friendly != agent_friendly:
        entry.agent_friendly = agent_friendly
        changed = True

    agent_signals = override.get("agent_signals")
    if isinstance(agent_signals, list):
        new_signals = sorted({str(signal) for signal in agent_signals if str(signal).strip()})
        if entry.agent_signals != new_signals:
            entry.agent_signals = new_signals
            changed = True

    if changed:
        entry.updated_at = date.today().isoformat()
    return changed


def apply_curated_overrides(
    entries: dict[str, CliEntry],
    overrides: dict[str, dict[str, Any]] | None = None,
) -> CurateResult:
    overrides = overrides or load_curated_overrides()
    result = CurateResult()

    for entry_id, override in overrides.items():
        entry = entries.get(entry_id)
        if entry is None:
            result.missing.append(entry_id)
            continue
        if _apply_override(entry, override):
            result.changed.append(entry_id)
        else:
            result.unchanged.append(entry_id)

    return result


def save_curated_entries(data_dir: Path, entries: dict[str, CliEntry], changed_ids: list[str]) -> None:
    for entry_id in changed_ids:
        entry = entries[entry_id]
        path = data_dir / entry_filename(entry.id)
        path.write_text(json.dumps(entry.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
