from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from cli_catalog.validate import validate_catalog


class ValidateCatalogTest(unittest.TestCase):
    def test_validate_minimal_catalog_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "catalog" / "data"
            data_dir.mkdir(parents=True)
            (data_dir / "owner__tool.json").write_text(
                json.dumps(
                    {
                        "id": "owner/tool",
                        "name": "tool",
                        "aliases": [],
                        "description": "Does useful work.",
                        "repo_url": "https://github.com/owner/tool",
                        "homepage": "",
                        "install": {},
                        "category": "Utilities",
                        "tags": [],
                        "github_stars": None,
                        "agent": {
                            "score": 1,
                            "friendly": False,
                            "signals": [],
                            "skill_url": None,
                        },
                        "sources": [{"id": "test", "repo": "owner/source", "commit": "abc123"}],
                        "meta": {
                            "first_seen_at": "2026-07-21",
                            "updated_at": "2026-07-21",
                            "status": "active",
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / "catalog" / "cli-summary.json").write_text(
                json.dumps(
                    {
                        "schema_version": 4,
                        "description": "Readable CLI routing index grouped by category. Read detail JSON for full metadata.",
                        "detail_template": "catalog/data/{id with '/' replaced by '__'}.json",
                        "counts": {
                            "total": 1,
                            "agent_friendly": 0,
                            "categories": 1,
                        },
                        "categories": [
                            {
                                "name": "Utilities",
                                "count": 1,
                                "columns": ["id", "cli", "function", "score"],
                                "rows": [["owner/tool", "tool", "Does useful work.", 1]],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = validate_catalog(root)

            self.assertEqual(result.errors, [])

    def test_validate_reports_bad_file_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_dir = root / "catalog" / "data"
            data_dir.mkdir(parents=True)
            (data_dir / "wrong.json").write_text(
                json.dumps(
                    {
                        "id": "owner/tool",
                        "name": "tool",
                        "description": "",
                        "repo_url": "https://github.com/owner/tool",
                        "category": "Utilities",
                        "tags": [],
                        "agent": {"score": 1, "friendly": False, "signals": [], "skill_url": None},
                        "sources": [],
                        "meta": {"status": "active"},
                    }
                ),
                encoding="utf-8",
            )

            result = validate_catalog(root)

            self.assertTrue(any("file name should be" in error for error in result.errors))


if __name__ == "__main__":
    unittest.main()
