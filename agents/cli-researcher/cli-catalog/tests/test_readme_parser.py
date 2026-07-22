from __future__ import annotations

import unittest

from cli_catalog.parsers.readme import parse_awesome_readme


class ReadmeParserTest(unittest.TestCase):
    def test_parse_awesome_readme_extracts_description_after_link(self) -> None:
        entries = parse_awesome_readme(
            """
## Search

- [ripgrep](https://github.com/BurntSushi/ripgrep) - Recursively searches directories for regex patterns.
""",
            source_id="test",
            source_repo="owner/source",
            commit="abc123",
        )

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].id, "BurntSushi/ripgrep")
        self.assertEqual(entries[0].category, "Search")
        self.assertEqual(entries[0].description, "Recursively searches directories for regex patterns")

    def test_parse_awesome_readme_dedupes_and_keeps_description(self) -> None:
        entries = parse_awesome_readme(
            """
## Tools

- [tool](https://github.com/owner/tool)
- [tool](https://github.com/owner/tool) - Useful CLI tool.
""",
            source_id="test",
            source_repo="owner/source",
            commit="abc123",
        )

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].description, "Useful CLI tool")


if __name__ == "__main__":
    unittest.main()
