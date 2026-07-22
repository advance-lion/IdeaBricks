from __future__ import annotations

import os
import time
import urllib.error
from collections import defaultdict

from cli_catalog.github_client import fetch_repo_stars
from cli_catalog.models import CliEntry, parse_github_id


def _repo_key(entry: CliEntry) -> str | None:
    return parse_github_id(entry.repo_url) or (entry.id if "/" in entry.id and not entry.id.startswith("HKUDS/CLI-Anything/") else None)


def update_github_stars(
    entries: dict[str, CliEntry],
    *,
    updated_at: str,
    sleep_seconds: float = 0.0,
) -> dict[str, int | bool]:
    repo_to_entries: dict[str, list[CliEntry]] = defaultdict(list)
    for entry in entries.values():
        repo_id = _repo_key(entry)
        if repo_id:
            repo_to_entries[repo_id].append(entry)

    cache: dict[str, int | None] = {}
    stats = {
        "repos_total": len(repo_to_entries),
        "repos_fetched": 0,
        "repos_failed": 0,
        "entries_updated": 0,
        "rate_limited": False,
    }

    has_token = bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))
    if not has_token and len(repo_to_entries) > 60:
        print(
            "Warning: fetching GitHub stars for "
            f"{len(repo_to_entries)} unique repos without GITHUB_TOKEN "
            "(GitHub API limit ~60/hour). Set GITHUB_TOKEN or GH_TOKEN for full updates."
        )

    for index, repo_id in enumerate(sorted(repo_to_entries.keys()), start=1):
        if repo_id not in cache:
            try:
                cache[repo_id] = fetch_repo_stars(repo_id)
                stats["repos_fetched"] += 1
            except urllib.error.HTTPError as exc:
                if exc.code in {403, 429}:
                    stats["rate_limited"] = True
                    print(f"Warning: GitHub API rate limit hit at repo {repo_id}. Keeping previous star counts.")
                    break
                cache[repo_id] = None
                stats["repos_failed"] += 1
            except Exception:
                cache[repo_id] = None
                stats["repos_failed"] += 1

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

        stars = cache.get(repo_id)
        if repo_id not in cache:
            continue

        for entry in repo_to_entries[repo_id]:
            if stars is not None:
                entry.github_stars = stars
                entry.github_stars_updated_at = updated_at
                stats["entries_updated"] += 1
            elif entry.github_stars is None:
                entry.github_stars_updated_at = updated_at

        if index % 200 == 0:
            print(f"Stars progress: {index}/{len(repo_to_entries)} repos")

    return stats
