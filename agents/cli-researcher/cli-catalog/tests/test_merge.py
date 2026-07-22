from __future__ import annotations

import unittest

from cli_catalog.merge import merge_entries
from cli_catalog.models import CliEntry, SourceRef


SOURCE_PRIORITIES = {
    "primary": 1,
    "agent": 2,
    "breadth": 3,
}


def entry(
    *,
    source_id: str,
    description: str = "description",
    homepage: str = "",
    install: dict[str, str] | None = None,
    category: str = "Development",
    tags: list[str] | None = None,
    agent_score: int = 1,
    manual_edit: bool = False,
    locked_category: bool = False,
) -> CliEntry:
    return CliEntry(
        id="owner/tool",
        name="tool",
        description=description,
        repo_url="https://github.com/owner/tool",
        homepage=homepage,
        install=install or {},
        category=category,
        tags=tags or [],
        agent_score=agent_score,
        sources=[SourceRef(id=source_id, repo=f"example/{source_id}", commit="abc123")],
        first_seen_at="2026-07-21",
        updated_at="2026-07-21",
        manual_edit=manual_edit,
        locked_category=locked_category,
    )


class MergeEntriesTest(unittest.TestCase):
    def test_lower_priority_source_only_fills_missing_fields(self) -> None:
        existing = entry(
            source_id="primary",
            description="Primary description",
            homepage="https://primary.example",
            install={"brew": "brew install tool"},
            category="Files & Search",
            tags=["primary-tag"],
            agent_score=1,
        )
        incoming = entry(
            source_id="breadth",
            description="Breadth description",
            homepage="https://breadth.example",
            install={"brew": "brew install breadth-tool", "cargo": "cargo install tool"},
            category="Random README Heading",
            tags=["breadth-tag"],
            agent_score=2,
        )

        merged = merge_entries(existing, incoming, SOURCE_PRIORITIES)

        self.assertEqual(merged.description, "Primary description")
        self.assertEqual(merged.homepage, "https://primary.example")
        self.assertEqual(merged.install["brew"], "brew install tool")
        self.assertEqual(merged.install["cargo"], "cargo install tool")
        self.assertEqual(merged.category, "Files & Search")
        self.assertEqual(merged.agent_score, 2)
        self.assertEqual(merged.tags, ["breadth-tag", "primary-tag"])
        self.assertEqual([source.id for source in merged.sources], ["primary", "breadth"])

    def test_higher_priority_source_replaces_unprotected_fields(self) -> None:
        existing = entry(
            source_id="breadth",
            description="Breadth description",
            homepage="https://breadth.example",
            install={"brew": "brew install breadth-tool"},
            category="Random README Heading",
        )
        incoming = entry(
            source_id="primary",
            description="Primary description",
            homepage="https://primary.example",
            install={"brew": "brew install tool"},
            category="Files & Search",
        )

        merged = merge_entries(existing, incoming, SOURCE_PRIORITIES)

        self.assertEqual(merged.description, "Primary description")
        self.assertEqual(merged.homepage, "https://primary.example")
        self.assertEqual(merged.install["brew"], "brew install tool")
        self.assertEqual(merged.category, "Files & Search")

    def test_manual_edit_and_locked_category_still_win(self) -> None:
        existing = entry(
            source_id="breadth",
            description="Manual description",
            homepage="https://manual.example",
            install={"brew": "brew install manual-tool"},
            category="Manual Category",
            manual_edit=True,
            locked_category=True,
        )
        incoming = entry(
            source_id="primary",
            description="Primary description",
            homepage="https://primary.example",
            install={"brew": "brew install tool"},
            category="Files & Search",
        )

        merged = merge_entries(existing, incoming, SOURCE_PRIORITIES)

        self.assertEqual(merged.description, "Manual description")
        self.assertEqual(merged.homepage, "https://manual.example")
        self.assertEqual(merged.install["brew"], "brew install manual-tool")
        self.assertEqual(merged.category, "Manual Category")


if __name__ == "__main__":
    unittest.main()
