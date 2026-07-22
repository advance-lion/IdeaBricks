from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from cli_catalog.models import CliEntry


def agent_stars(score: int) -> str:
    return "★" * score + "☆" * (3 - score)


def render_catalog_markdown(entries: list[CliEntry] | dict[str, CliEntry], output: Path, state: dict) -> None:
    if isinstance(entries, dict):
        entry_list = list(entries.values())
    else:
        entry_list = list(entries)

    entry_list.sort(key=lambda e: (-e.agent_score, e.name.lower()))
    grouped: dict[str, list[CliEntry]] = defaultdict(list)
    for entry in entry_list:
        grouped[entry.category].append(entry)

    stats = state.get("stats", {})
    last_run = state.get("last_run_at", "unknown")
    source_count = len(state.get("sources", {}))

    lines = [
        "# CLI Catalog",
        "",
        "> Open-source CLI tools curated for AI agent use.",
        f"> Last sync: {last_run} · Sources: {source_count} · Total: {stats.get('total_unique_clis', len(entry_list))} tools",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|--------|------:|",
        f"| Total unique CLIs | {stats.get('total_unique_clis', len(entry_list))} |",
        f"| Agent-friendly | {stats.get('agent_friendly_count', 0)} |",
        f"| Categories | {stats.get('category_count', len(grouped))} |",
        "",
        "---",
        "",
    ]

    for category in sorted(grouped.keys()):
        lines.append(f"## {category}")
        lines.append("")
        lines.append("| Name | Description | Stars | Agent | Repository | Tags |")
        lines.append("|------|-------------|------:|:-----:|------------|------|")
        for entry in sorted(grouped[category], key=lambda e: (-(e.github_stars or 0), -e.agent_score, e.name.lower())):
            desc = entry.description.replace("|", "\\|").replace("\n", " ")
            if len(desc) > 120:
                desc = desc[:117] + "..."
            repo = entry.repo_url or entry.homepage or ""
            tags = ", ".join(entry.tags[:3])
            stars = f"{entry.github_stars:,}" if entry.github_stars is not None else "-"
            lines.append(
                f"| `{entry.name}` | {desc or '-'} | {stars} | {agent_stars(entry.agent_score)} | [{entry.id}]({repo}) | {tags or '-'} |"
            )
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## Agent score legend",
            "",
            "| Score | Meaning |",
            "|-------|---------|",
            "| ★★★ | Listed in agent-focused upstream sources |",
            "| ★★☆ | Modern/scriptable CLI anchor tools |",
            "| ★☆☆ | General CLI from primary catalog |",
            "",
            "## Upstream sources",
            "",
            "| Source ID | Repository | Last commit |",
            "|-----------|----------|-------------|",
        ]
    )

    for source_id, info in sorted(state.get("sources", {}).items()):
        commit = info.get("commit", "")[:7]
        lines.append(f"| {source_id} | `{info.get('repo', '')}` | `{commit}` |")

    lines.append("")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
