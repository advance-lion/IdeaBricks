from __future__ import annotations

import argparse
from pathlib import Path

from cli_catalog.curate import apply_curated_overrides, save_curated_entries
from cli_catalog.quality import quality_report
from cli_catalog.query import SearchOptions, entry_detail_json, find_entry, format_search_results, search_entries
from cli_catalog.render import render_catalog_markdown
from cli_catalog.sync import load_existing_entries, load_state, project_root, sync
from cli_catalog.summary import load_summary_category_aliases, render_cli_summary
from cli_catalog.validate import validate_catalog


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI Catalog — sync and maintain open-source CLI registry")
    sub = parser.add_subparsers(dest="command", required=True)

    sync_parser = sub.add_parser("sync", help="Fetch upstream repos and update catalog JSON + Markdown")
    sync_parser.add_argument("--force", action="store_true", help="Sync even if upstream commit unchanged")
    sync_parser.add_argument(
        "--sources",
        nargs="+",
        help="Only sync specific source ids (e.g. toolleeo-csv modern-unix)",
    )

    sync_parser.add_argument(
        "--skip-stars",
        action="store_true",
        help="Skip refreshing GitHub star counts",
    )

    render_parser = sub.add_parser("render", help="Regenerate Markdown from existing JSON catalog")
    render_parser.add_argument(
        "--output",
        default=None,
        help="Output markdown path (default: catalog/cli-catalog.md)",
    )

    summary_parser = sub.add_parser("summary", help="Generate compact JSON summary for agent use")
    summary_parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path (default: catalog/cli-summary.json)",
    )

    sub.add_parser("stats", help="Show catalog statistics")
    sub.add_parser("validate", help="Validate catalog JSON files and agent summary")
    sub.add_parser("quality", help="Show catalog quality report")

    curate_parser = sub.add_parser("curate", help="Apply local curated overrides to catalog JSON")
    curate_parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing files")

    search_parser = sub.add_parser("search", help="Search local CLI catalog")
    search_parser.add_argument("query", nargs="?", default="", help="Search text")
    search_parser.add_argument("--category", default="", help="Filter by category text")
    search_parser.add_argument("--agent-only", action="store_true", help="Only show agent-friendly CLIs")
    search_parser.add_argument("--limit", type=int, default=20, help="Maximum results to show")

    show_parser = sub.add_parser("show", help="Show full JSON for one CLI")
    show_parser.add_argument("key", help="CLI id, name, alias, or partial match")

    args = parser.parse_args()
    root = project_root()

    if args.command == "sync":
        result = sync(force=args.force, sources_filter=args.sources, skip_stars=args.skip_stars)
        if result["skipped"]:
            print("No upstream changes detected. Use --force to re-sync anyway.")
        print(
            f"Sync complete: +{result['added']} added, {result['updated']} updated, "
            f"{result['total']} total, {result['agent_friendly']} agent-friendly"
        )
        if result["sources_updated"]:
            print("Updated sources:", ", ".join(result["sources_updated"]))
        stars = result.get("stars") or {}
        if stars:
            print(
                f"Stars refreshed: {stars.get('entries_updated', 0)} entries "
                f"({stars.get('repos_fetched', 0)}/{stars.get('repos_total', 0)} repos)"
            )
            if stars.get("rate_limited"):
                print("Stars refresh stopped early due to GitHub API rate limit. Set GITHUB_TOKEN to refresh all.")

    elif args.command == "render":
        data_dir = root / "catalog" / "data"
        output = Path(args.output) if args.output else root / "catalog" / "cli-catalog.md"
        summary_output = root / "catalog" / "cli-summary.json"
        entries = load_existing_entries(data_dir)
        state = load_state(root / "state" / "sources.json")
        render_catalog_markdown(entries, output, state)
        render_cli_summary(entries, summary_output, state)
        print(f"Rendered {len(entries)} entries to {output} and {summary_output}")

    elif args.command == "summary":
        data_dir = root / "catalog" / "data"
        output = Path(args.output) if args.output else root / "catalog" / "cli-summary.json"
        entries = load_existing_entries(data_dir)
        state = load_state(root / "state" / "sources.json")
        render_cli_summary(entries, output, state)
        print(f"Rendered {len(entries)} entries to {output}")

    elif args.command == "stats":
        data_dir = root / "catalog" / "data"
        entries = load_existing_entries(data_dir)
        state = load_state(root / "state" / "sources.json")
        agent_friendly = sum(1 for e in entries.values() if e.agent_friendly)
        print(f"Total CLIs: {len(entries)}")
        print(f"Agent-friendly: {agent_friendly}")
        print(f"Categories: {len({e.category for e in entries.values()})}")
        print(f"Last sync: {state.get('last_run_at', 'never')}")

    elif args.command == "validate":
        result = validate_catalog(root)
        for warning in result.warnings:
            print(f"Warning: {warning}")
        for error in result.errors:
            print(f"Error: {error}")
        if result.ok:
            print(f"Validation passed ({len(result.warnings)} warnings)")
        else:
            raise SystemExit(1)

    elif args.command == "quality":
        data_dir = root / "catalog" / "data"
        entries = load_existing_entries(data_dir)
        print("\n".join(quality_report(entries)))

    elif args.command == "curate":
        data_dir = root / "catalog" / "data"
        entries = load_existing_entries(data_dir)
        result = apply_curated_overrides(entries)
        print(f"Curated overrides: {len(result.changed)} changed, {len(result.unchanged)} unchanged, {len(result.missing)} missing")
        if result.changed:
            print("Changed:", ", ".join(result.changed))
        if result.missing:
            print("Missing:", ", ".join(result.missing))
        if not args.dry_run:
            save_curated_entries(data_dir, entries, result.changed)
            render_cli_summary(entries, root / "catalog" / "cli-summary.json", load_state(root / "state" / "sources.json"))
        else:
            print("Dry run: no files written")

    elif args.command == "search":
        data_dir = root / "catalog" / "data"
        entries = load_existing_entries(data_dir)
        options = SearchOptions(
            query=args.query,
            category=args.category,
            agent_only=args.agent_only,
            limit=args.limit,
        )
        category_aliases = load_summary_category_aliases()
        print(format_search_results(search_entries(entries, options, category_aliases), category_aliases))

    elif args.command == "show":
        data_dir = root / "catalog" / "data"
        entries = load_existing_entries(data_dir)
        entry = find_entry(entries, args.key)
        if entry is None:
            print(f"No CLI found for {args.key!r}")
            raise SystemExit(1)
        print(entry_detail_json(data_dir, entry), end="")


if __name__ == "__main__":
    main()
