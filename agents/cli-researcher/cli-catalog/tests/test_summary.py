from __future__ import annotations

import unittest

from cli_catalog.models import CliEntry, SourceRef
from cli_catalog.summary import build_cli_summary, normalize_summary_category, summary_record


def entry(
    *,
    entry_id: str,
    name: str,
    description: str = "",
    category: str = "Utilities",
    tags: list[str] | None = None,
    agent_score: int = 1,
    agent_friendly: bool = False,
    github_stars: int | None = None,
) -> CliEntry:
    return CliEntry(
        id=entry_id,
        name=name,
        description=description,
        repo_url=f"https://github.com/{entry_id}",
        category=category,
        tags=tags or [],
        agent_score=agent_score,
        agent_friendly=agent_friendly,
        github_stars=github_stars,
        sources=[SourceRef(id="test-source", repo="example/source", commit="abc123")],
    )


class SummaryTest(unittest.TestCase):
    def test_summary_record_uses_description_as_function(self) -> None:
        record = summary_record(
            entry(
                entry_id="owner/tool",
                name="tool",
                description="Does one useful thing.",
                tags=["useful"],
                agent_score=3,
                agent_friendly=True,
            )
        )

        self.assertEqual(record, ["owner/tool", "tool", "Does one useful thing.", 3])

    def test_summary_record_falls_back_when_description_missing(self) -> None:
        record = summary_record(
            entry(
                entry_id="owner/no-description",
                name="no-description",
                category="Files & Search",
                tags=["search", "files"],
            )
        )

        self.assertEqual(record, ["owner/no-description", "no-description", "Files & Search CLI tool.", 1])

    def test_build_summary_groups_by_category_and_sorts_rows(self) -> None:
        summary = build_cli_summary(
            [
                entry(entry_id="owner/general", name="general", category="Utilities", github_stars=100),
                entry(
                    entry_id="owner/agent-small",
                    name="agent-small",
                    category="AI & Agents",
                    agent_score=3,
                    agent_friendly=True,
                    github_stars=10,
                ),
                entry(
                    entry_id="owner/agent-large",
                    name="agent-large",
                    category="AI & Agents",
                    agent_score=3,
                    agent_friendly=True,
                    github_stars=1000,
                ),
            ],
            {"last_run_at": "2026-07-21T13:03:12+08:00"},
        )

        self.assertEqual(summary["counts"]["total"], 3)
        self.assertEqual(summary["counts"]["agent_friendly"], 2)
        self.assertEqual(summary["counts"]["categories"], 2)
        self.assertEqual(summary["detail_template"], "catalog/data/{id with '/' replaced by '__'}.json")

        ai_category = summary["categories"][0]
        self.assertEqual(ai_category["name"], "AI & Agents")
        self.assertEqual(ai_category["columns"], ["id", "cli", "function", "score"])
        self.assertEqual(ai_category["rows"][0][0], "owner/agent-large")
        self.assertEqual(ai_category["rows"][1][0], "owner/agent-small")

        utilities_category = summary["categories"][1]
        self.assertEqual(utilities_category["name"], "Utilities")
        self.assertEqual(utilities_category["rows"][0][0], "owner/general")

    def test_build_summary_applies_category_aliases(self) -> None:
        summary = build_cli_summary(
            [
                entry(entry_id="owner/video", name="video", category="Video"),
                entry(entry_id="owner/media", name="media", category="Media & Graphics"),
            ],
            {},
            {"Video": "Media & Graphics"},
        )

        self.assertEqual(summary["counts"]["categories"], 1)
        self.assertEqual(summary["categories"][0]["name"], "Media & Graphics")
        self.assertEqual(summary["categories"][0]["count"], 2)
        self.assertEqual(normalize_summary_category("Video", {"Video": "Media & Graphics"}), "Media & Graphics")

    def test_summary_record_limits_long_descriptions(self) -> None:
        record = summary_record(
            entry(
                entry_id="owner/large",
                name="large",
                description="x" * 300,
            )
        )

        self.assertLessEqual(len(record[2]), 140)


if __name__ == "__main__":
    unittest.main()
