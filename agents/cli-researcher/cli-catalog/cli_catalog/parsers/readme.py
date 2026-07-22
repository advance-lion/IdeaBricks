from __future__ import annotations

import re
from datetime import date

from cli_catalog.models import CliEntry, SourceRef, normalize_repo_url, parse_github_id

LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
CODE_LINK_RE = re.compile(
    r'<a href="(https?://github\.com/[^"]+)"><code>([^<]+)</code></a>',
    re.IGNORECASE,
)
HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)


def parse_awesome_readme(
    text: str,
    *,
    source_id: str,
    source_repo: str,
    commit: str,
    default_category: str = "Other",
) -> list[CliEntry]:
    entries: list[CliEntry] = []
    today = date.today().isoformat()
    current_category = default_category

    for line in text.splitlines():
        heading = HEADING_RE.match(line.strip())
        if heading:
            title = heading.group(1).strip()
            if title.lower() not in {"contents", "related", "license", "contributing"}:
                current_category = title

        for match in LINK_RE.finditer(line):
            name = match.group(1).strip()
            url = match.group(2).strip()
            repo_id = parse_github_id(url)
            if not repo_id:
                continue
            entries.append(
                CliEntry(
                    id=repo_id,
                    name=_clean_name(name),
                    description=_description_after_link(line, match.end()),
                    repo_url=normalize_repo_url(url),
                    category=current_category,
                    tags=["awesome-list"],
                    sources=[SourceRef(id=source_id, repo=source_repo, commit=commit)],
                    first_seen_at=today,
                    updated_at=today,
                )
            )

        for match in CODE_LINK_RE.finditer(line):
            url = match.group(1).strip()
            name = match.group(2).strip()
            repo_id = parse_github_id(url)
            if not repo_id:
                continue
            entries.append(
                CliEntry(
                    id=repo_id,
                    name=name,
                    description=_description_after_link(line, match.end()),
                    repo_url=normalize_repo_url(url),
                    category=current_category,
                    tags=["modern-unix"],
                    agent_score=2,
                    sources=[SourceRef(id=source_id, repo=source_repo, commit=commit)],
                    first_seen_at=today,
                    updated_at=today,
                )
            )

    return _dedupe_entries(entries)


def parse_ai_cli_readme(
    text: str,
    *,
    source_id: str,
    source_repo: str,
    commit: str,
) -> tuple[list[CliEntry], set[str]]:
    entries = parse_awesome_readme(
        text,
        source_id=source_id,
        source_repo=source_repo,
        commit=commit,
        default_category="AI & Agents",
    )
    agent_ids: set[str] = set()
    for entry in entries:
        entry.category = "AI & Agents"
        entry.agent_score = 3
        entry.agent_friendly = True
        entry.agent_signals.append("awesome-ai-cli")
        entry.tags.append("agent-friendly")
        agent_ids.add(entry.id)
        agent_ids.add(entry.name.lower())
    return entries, agent_ids


def parse_composio_readme(
    text: str,
    *,
    source_id: str,
    source_repo: str,
    commit: str,
) -> tuple[list[CliEntry], set[str]]:
    entries: list[CliEntry] = []
    agent_ids: set[str] = set()
    today = date.today().isoformat()

    for line in text.splitlines():
        if "github.com" not in line:
            continue
        for match in LINK_RE.finditer(line):
            name = match.group(1).strip()
            url = match.group(2).strip()
            repo_id = parse_github_id(url)
            if not repo_id:
                continue
            skill_match = re.search(r"\[`skill`\]\(([^)]+)\)", line)
            skill_url = skill_match.group(1) if skill_match else None
            agent_designed = "🤖" in line or "agent" in line.lower()
            entry = CliEntry(
                id=repo_id,
                name=_clean_name(name),
                description="",
                repo_url=normalize_repo_url(url),
                category="AI & Agents",
                tags=["composio-list"],
                agent_score=3 if agent_designed else 2,
                agent_friendly=True,
                agent_signals=["composio-agent-clis"],
                skill_url=skill_url,
                sources=[SourceRef(id=source_id, repo=source_repo, commit=commit)],
                first_seen_at=today,
                updated_at=today,
            )
            entries.append(entry)
            agent_ids.add(repo_id)
            agent_ids.add(entry.name.lower())

    return _dedupe_entries(entries), agent_ids


def _clean_name(name: str) -> str:
    name = re.sub(r"[`⭐\u2b50\ud83e\udd16]", "", name).strip()
    return name.split()[0] if name else name


def _description_after_link(line: str, end_index: int) -> str:
    description = line[end_index:].strip()
    description = re.sub(r"^(?:[-:–—|•]|\s)+", "", description).strip()
    description = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", description)
    description = re.sub(r"<[^>]+>", "", description)
    description = description.strip(" .")
    return description


def _dedupe_entries(entries: list[CliEntry]) -> list[CliEntry]:
    by_id: dict[str, CliEntry] = {}
    for entry in entries:
        if entry.id in by_id:
            existing = by_id[entry.id]
            existing.tags = sorted(set(existing.tags + entry.tags))
            existing.agent_score = max(existing.agent_score, entry.agent_score)
            if not existing.description and entry.description:
                existing.description = entry.description
        else:
            by_id[entry.id] = entry
    return list(by_id.values())
