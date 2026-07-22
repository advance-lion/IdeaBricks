from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cli_catalog.models import CliEntry
from cli_catalog.query import SearchOptions, display_category, entry_detail_json, find_entry, format_search_results, search_entries
from cli_catalog.sync import save_entry


def entry(
    *,
    entry_id: str,
    name: str,
    description: str,
    category: str,
    agent_score: int = 1,
    agent_friendly: bool = False,
) -> CliEntry:
    return CliEntry(
        id=entry_id,
        name=name,
        description=description,
        repo_url=f"https://github.com/{entry_id}",
        category=category,
        tags=[category.lower()],
        agent_score=agent_score,
        agent_friendly=agent_friendly,
    )


class QueryTest(unittest.TestCase):
    def test_search_entries_ranks_exact_name_first(self) -> None:
        entries = {
            "owner/ripgrep": entry(
                entry_id="owner/ripgrep",
                name="ripgrep",
                description="Search files quickly.",
                category="Files & Search",
                agent_score=3,
                agent_friendly=True,
            ),
            "owner/other": entry(
                entry_id="owner/other",
                name="other",
                description="Mentions ripgrep in docs.",
                category="Development",
            ),
        }

        matches = search_entries(entries, SearchOptions(query="ripgrep"))

        self.assertEqual([match.id for match in matches], ["owner/ripgrep", "owner/other"])

    def test_search_entries_filters_category_and_agent(self) -> None:
        entries = {
            "owner/video": entry(
                entry_id="owner/video",
                name="video",
                description="Download video.",
                category="Media & Graphics",
                agent_score=3,
                agent_friendly=True,
            ),
            "owner/general": entry(
                entry_id="owner/general",
                name="general",
                description="Download files.",
                category="Files & Search",
            ),
        }

        matches = search_entries(entries, SearchOptions(query="download", category="Media", agent_only=True))

        self.assertEqual([match.id for match in matches], ["owner/video"])

    def test_search_entries_filters_normalized_category(self) -> None:
        entries = {
            "owner/video": entry(
                entry_id="owner/video",
                name="video",
                description="Download video.",
                category="Video",
            )
        }

        matches = search_entries(
            entries,
            SearchOptions(query="download", category="Media"),
            {"Video": "Media & Graphics"},
        )

        self.assertEqual([match.id for match in matches], ["owner/video"])

    def test_find_entry_and_detail_json(self) -> None:
        tool = entry(
            entry_id="owner/tool",
            name="tool",
            description="Does useful work.",
            category="Utilities",
        )
        entries = {tool.id: tool}
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            save_entry(data_dir, tool)

            found = find_entry(entries, "tool")

            self.assertIsNotNone(found)
            self.assertEqual(found.id, "owner/tool")
            self.assertEqual(json.loads(entry_detail_json(data_dir, found))["id"], "owner/tool")

    def test_format_search_results_handles_empty_matches(self) -> None:
        self.assertEqual(format_search_results([]), "No matching CLIs found.")

    def test_format_search_results_displays_normalized_category(self) -> None:
        tool = entry(
            entry_id="owner/video",
            name="video",
            description="Download video.",
            category="Video",
        )

        self.assertEqual(display_category(tool, {"Video": "Media & Graphics"}), "Media & Graphics (from Video)")
        self.assertIn("Media & Graphics (from Video)", format_search_results([tool], {"Video": "Media & Graphics"}))


if __name__ == "__main__":
    unittest.main()
