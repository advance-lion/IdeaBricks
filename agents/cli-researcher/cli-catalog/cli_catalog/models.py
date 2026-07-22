from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


GITHUB_RE = re.compile(
    r"https?://(?:www\.)?github\.com/([^/\s?#]+)/([^/\s?#]+)",
    re.IGNORECASE,
)


@dataclass
class SourceRef:
    id: str
    repo: str
    commit: str
    upstream_category: str = ""


@dataclass
class CliEntry:
    id: str
    name: str
    description: str
    repo_url: str
    homepage: str = ""
    aliases: list[str] = field(default_factory=list)
    install: dict[str, str] = field(default_factory=dict)
    category: str = "Other"
    tags: list[str] = field(default_factory=list)
    agent_score: int = 1
    agent_friendly: bool = False
    agent_signals: list[str] = field(default_factory=list)
    skill_url: str | None = None
    github_stars: int | None = None
    github_stars_updated_at: str = ""
    sources: list[SourceRef] = field(default_factory=list)
    first_seen_at: str = ""
    updated_at: str = ""
    status: str = "active"
    manual_edit: bool = False
    locked_category: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "aliases": sorted(set(self.aliases)),
            "description": self.description,
            "repo_url": self.repo_url,
            "homepage": self.homepage,
            "install": self.install,
            "category": self.category,
            "tags": sorted(set(self.tags)),
            "github_stars": self.github_stars,
            "agent": {
                "score": self.agent_score,
                "friendly": self.agent_friendly,
                "signals": sorted(set(self.agent_signals)),
                "skill_url": self.skill_url,
            },
            "sources": [
                {
                    "id": s.id,
                    "repo": s.repo,
                    "commit": s.commit,
                    **({"upstream_category": s.upstream_category} if s.upstream_category else {}),
                }
                for s in self.sources
            ],
            "meta": {
                "first_seen_at": self.first_seen_at,
                "updated_at": self.updated_at,
                "status": self.status,
                **({"github_stars_updated_at": self.github_stars_updated_at} if self.github_stars_updated_at else {}),
                **({"manual_edit": True} if self.manual_edit else {}),
                **({"locked_category": True} if self.locked_category else {}),
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CliEntry:
        agent = data.get("agent", {})
        meta = data.get("meta", {})
        sources = [
            SourceRef(
                id=s.get("id", ""),
                repo=s.get("repo", ""),
                commit=s.get("commit", ""),
                upstream_category=s.get("upstream_category", ""),
            )
            for s in data.get("sources", [])
        ]
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            repo_url=data.get("repo_url", ""),
            homepage=data.get("homepage", ""),
            aliases=list(data.get("aliases", [])),
            install=dict(data.get("install", {})),
            category=data.get("category", "Other"),
            tags=list(data.get("tags", [])),
            agent_score=int(agent.get("score", 1)),
            agent_friendly=bool(agent.get("friendly", False)),
            agent_signals=list(agent.get("signals", [])),
            skill_url=agent.get("skill_url"),
            github_stars=data.get("github_stars"),
            github_stars_updated_at=meta.get("github_stars_updated_at", ""),
            sources=sources,
            first_seen_at=meta.get("first_seen_at", ""),
            updated_at=meta.get("updated_at", ""),
            status=meta.get("status", "active"),
            manual_edit=bool(meta.get("manual_edit", False)),
            locked_category=bool(meta.get("locked_category", False)),
        )


def parse_github_id(url: str) -> str | None:
    if not url:
        return None
    match = GITHUB_RE.search(url.strip())
    if not match:
        return None
    owner, repo = match.group(1), match.group(2)
    repo = repo.removesuffix(".git")
    return f"{owner}/{repo}"


def normalize_repo_url(url: str) -> str:
    repo_id = parse_github_id(url)
    if repo_id:
        return f"https://github.com/{repo_id}"
    return url.strip()


def entry_filename(entry_id: str) -> str:
    return entry_id.replace("/", "__") + ".json"
