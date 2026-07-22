# Sync CLI Catalog

When the user asks to sync/update the CLI catalog:

1. Run from `cli-catalog/` directory:
   ```bash
   python3 -m cli_catalog sync
   ```
2. If no changes detected but user wants refresh:
   ```bash
   python3 -m cli_catalog sync --force
   ```
3. Review `meta/changelog.md` and summarize added/updated counts.
4. Canonical data lives in `catalog/data/*.json` — one `{}` per CLI.
5. Markdown view is generated at `catalog/cli-catalog.md`.

Do not hand-edit `cli-catalog.md`; edit JSON entries or upstream config instead, then run `render` or `sync`.
