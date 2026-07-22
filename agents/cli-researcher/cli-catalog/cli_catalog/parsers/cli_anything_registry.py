from __future__ import annotations

import json
from datetime import date

from cli_catalog.categorize import categorize
from cli_catalog.models import CliEntry, SourceRef, normalize_repo_url, parse_github_id

CLI_ANYTHING_REPO = "https://github.com/HKUDS/CLI-Anything"
CLI_ANYTHING_HUB = "https://clianything.cc/"

CATEGORY_MAP = {
    "ai": "AI & Agents",
    "automation": "AI & Agents",
    "graphics": "Media & Graphics",
    "image": "Media & Graphics",
    "video": "Media & Graphics",
    "music": "Media & Graphics",
    "devops": "DevOps & Cloud",
    "web": "Network & API",
    "office": "Productivity",
    "database": "Data & JSON",
    "gamedev": "Development",
    "security": "Security",
    "science": "Data & JSON",
    "utility": "Utilities",
}


def _skill_url(skill_md: str | None) -> str | None:
    if not skill_md:
        return None
    skill_md = skill_md.strip()
    if skill_md.startswith("http"):
        return skill_md
    return f"{CLI_ANYTHING_REPO}/blob/main/{skill_md.lstrip('/')}"


def _entry_id(name: str, source_url: str | None) -> tuple[str, str]:
    if source_url:
        repo_id = parse_github_id(source_url)
        if repo_id:
            return repo_id, normalize_repo_url(source_url)
    slug = name.strip().lower().replace(" ", "-")
    return f"HKUDS/CLI-Anything/{slug}", CLI_ANYTHING_REPO


def _map_category(upstream: str, slug_to_group: dict[str, str], default_group: str) -> str:
    if upstream in CATEGORY_MAP:
        return CATEGORY_MAP[upstream]
    return categorize(upstream, slug_to_group, default_group)


def _install_from_cmd(install_cmd: str | None) -> dict[str, str]:
    if not install_cmd or not install_cmd.strip():
        return {}
    cmd = install_cmd.strip()
    if cmd.startswith("pip "):
        return {"pip": cmd}
    if cmd.startswith("npm ") or cmd.startswith("npx "):
        return {"npm": cmd}
    if cmd.startswith("brew "):
        return {"brew": cmd}
    return {"shell": cmd}


def parse_registry_payload(
    payload: dict,
    *,
    source_id: str,
    source_repo: str,
    commit: str,
    registry_file: str,
    slug_to_group: dict[str, str],
    default_group: str,
) -> list[CliEntry]:
    entries: list[CliEntry] = []
    today = date.today().isoformat()

    for item in payload.get("clis", []):
        name = (item.get("entry_point") or item.get("name") or item.get("display_name") or "").strip()
        if not name:
            continue

        raw_name = item.get("name", name).strip()
        display = item.get("display_name", raw_name).strip()
        description = (item.get("description") or "").strip()
        source_url = item.get("source_url")
        entry_id, repo_url = _entry_id(raw_name, source_url)
        upstream_category = (item.get("category") or "ai").strip()
        skill = _skill_url(item.get("skill_md"))
        install = _install_from_cmd(item.get("install_cmd"))

        entry = CliEntry(
            id=entry_id,
            name=display or name,
            description=description,
            repo_url=repo_url,
            homepage=(item.get("homepage") or "").strip() or CLI_ANYTHING_HUB,
            install=install,
            category=_map_category(upstream_category, slug_to_group, default_group),
            tags=["cli-anything", upstream_category, registry_file.removesuffix(".json")],
            agent_score=3,
            agent_friendly=True,
            agent_signals=["cli-anything", "agent-native-harness"],
            skill_url=skill,
            sources=[
                SourceRef(
                    id=source_id,
                    repo=source_repo,
                    commit=commit,
                    upstream_category=upstream_category,
                )
            ],
            first_seen_at=today,
            updated_at=today,
        )
        if item.get("requires"):
            entry.tags.append("requires-deps")
        entries.append(entry)

    return entries


def parse_cli_anything_registry(
    registry_json: str,
    public_registry_json: str,
    *,
    source_id: str,
    source_repo: str,
    commit: str,
    slug_to_group: dict[str, str],
    default_group: str,
) -> list[CliEntry]:
    entries: list[CliEntry] = []
    for text, registry_file in (
        (registry_json, "registry.json"),
        (public_registry_json, "public_registry.json"),
    ):
        if not text.strip():
            continue
        payload = json.loads(text)
        entries.extend(
            parse_registry_payload(
                payload,
                source_id=source_id,
                source_repo=source_repo,
                commit=commit,
                registry_file=registry_file,
                slug_to_group=slug_to_group,
                default_group=default_group,
            )
        )

    by_id: dict[str, CliEntry] = {}
    for entry in entries:
        if entry.id in by_id:
            existing = by_id[entry.id]
            existing.tags = sorted(set(existing.tags + entry.tags))
            existing.sources.extend(entry.sources)
            if entry.skill_url and not existing.skill_url:
                existing.skill_url = entry.skill_url
        else:
            by_id[entry.id] = entry
    return list(by_id.values())
