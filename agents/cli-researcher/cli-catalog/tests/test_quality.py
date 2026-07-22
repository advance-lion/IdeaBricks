from __future__ import annotations

import unittest

from cli_catalog.models import CliEntry
from cli_catalog.quality import effective_agent_score, is_likely_resource_list, quality_report


def entry(
    *,
    entry_id: str,
    name: str,
    description: str = "",
    tags: list[str] | None = None,
    agent_score: int = 3,
) -> CliEntry:
    return CliEntry(
        id=entry_id,
        name=name,
        description=description,
        repo_url=f"https://github.com/{entry_id}",
        category="AI & Agents",
        tags=tags or [],
        agent_score=agent_score,
        agent_friendly=agent_score >= 3,
    )


class QualityTest(unittest.TestCase):
    def test_detects_obvious_awesome_resource_list(self) -> None:
        tool = entry(entry_id="owner/awesome-tools", name="awesome-tools", tags=["awesome-list"])

        self.assertTrue(is_likely_resource_list(tool))
        self.assertEqual(effective_agent_score(tool), 1)

    def test_does_not_downgrade_real_cli_with_awesome_list_source_tag(self) -> None:
        tool = entry(
            entry_id="BurntSushi/ripgrep",
            name="ripgrep",
            description="Recursively searches directories for a regex pattern.",
            tags=["awesome-list", "modern-unix"],
        )

        self.assertFalse(is_likely_resource_list(tool))
        self.assertEqual(effective_agent_score(tool), 3)

    def test_quality_report_includes_high_score_resource_lists(self) -> None:
        entries = {
            "owner/awesome-tools": entry(entry_id="owner/awesome-tools", name="awesome-tools"),
            "owner/tool": entry(entry_id="owner/tool", name="tool", description="Does work.", agent_score=1),
        }

        report = "\n".join(quality_report(entries))

        self.assertIn("High-score likely resource-list entries: 1", report)
        self.assertIn("owner/awesome-tools", report)


if __name__ == "__main__":
    unittest.main()
