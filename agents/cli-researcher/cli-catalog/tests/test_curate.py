from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cli_catalog.curate import apply_curated_overrides, save_curated_entries
from cli_catalog.models import CliEntry
from cli_catalog.sync import save_entry


class CurateTest(unittest.TestCase):
    def test_apply_curated_overrides_updates_description_tags_and_manual_flag(self) -> None:
        entry = CliEntry(
            id="owner/tool",
            name="tool",
            description="",
            repo_url="https://github.com/owner/tool",
            category="Utilities",
            tags=["old"],
        )
        entries = {"owner/tool": entry}

        result = apply_curated_overrides(
            entries,
            {
                "owner/tool": {
                    "description": "Does useful work.",
                    "tags": ["curated", "old"],
                }
            },
        )

        self.assertEqual(result.changed, ["owner/tool"])
        self.assertEqual(entry.description, "Does useful work.")
        self.assertTrue(entry.manual_edit)
        self.assertEqual(entry.tags, ["curated", "old"])

    def test_apply_curated_overrides_reports_missing_and_unchanged(self) -> None:
        entry = CliEntry(
            id="owner/tool",
            name="tool",
            description="Already good.",
            repo_url="https://github.com/owner/tool",
            category="Utilities",
        )

        result = apply_curated_overrides(
            {"owner/tool": entry},
            {
                "owner/tool": {"description": "Already good."},
                "owner/missing": {"description": "Missing."},
            },
        )

        self.assertEqual(result.unchanged, ["owner/tool"])
        self.assertEqual(result.missing, ["owner/missing"])

    def test_apply_curated_overrides_updates_agent_fields(self) -> None:
        entry = CliEntry(
            id="owner/awesome-list",
            name="awesome-list",
            description="A list.",
            repo_url="https://github.com/owner/awesome-list",
            category="Other",
            agent_score=3,
            agent_friendly=True,
            agent_signals=["curated-agent-list"],
        )

        result = apply_curated_overrides(
            {"owner/awesome-list": entry},
            {
                "owner/awesome-list": {
                    "agent_score": 1,
                    "agent_friendly": False,
                    "agent_signals": ["resource-list"],
                }
            },
        )

        self.assertEqual(result.changed, ["owner/awesome-list"])
        self.assertEqual(entry.agent_score, 1)
        self.assertFalse(entry.agent_friendly)
        self.assertEqual(entry.agent_signals, ["resource-list"])

    def test_apply_curated_overrides_removes_tags(self) -> None:
        entry = CliEntry(
            id="owner/list",
            name="list",
            description="A list.",
            repo_url="https://github.com/owner/list",
            category="Other",
            tags=["agent-friendly", "awesome-list", "resource-list"],
        )

        result = apply_curated_overrides(
            {"owner/list": entry},
            {"owner/list": {"remove_tags": ["agent-friendly"]}},
        )

        self.assertEqual(result.changed, ["owner/list"])
        self.assertEqual(entry.tags, ["awesome-list", "resource-list"])

    def test_save_curated_entries_writes_changed_json(self) -> None:
        entry = CliEntry(
            id="owner/tool",
            name="tool",
            description="",
            repo_url="https://github.com/owner/tool",
            category="Utilities",
        )
        entries = {"owner/tool": entry}
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            save_entry(data_dir, entry)
            apply_curated_overrides(entries, {"owner/tool": {"description": "Updated."}})

            save_curated_entries(data_dir, entries, ["owner/tool"])

            data = json.loads((data_dir / "owner__tool.json").read_text(encoding="utf-8"))
            self.assertEqual(data["description"], "Updated.")
            self.assertTrue(data["meta"]["manual_edit"])


if __name__ == "__main__":
    unittest.main()
