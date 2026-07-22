from __future__ import annotations

import csv
import io
import re
from datetime import date

from cli_catalog.categorize import categorize, derive_tags
from cli_catalog.models import CliEntry, SourceRef, normalize_repo_url, parse_github_id


def parse_toolleeo_csv(
    apps_csv: str,
    categories_csv: str,
    *,
    source_id: str,
    source_repo: str,
    commit: str,
    slug_to_group: dict[str, str],
    default_group: str,
) -> list[CliEntry]:
    category_names: dict[str, str] = {}
    reader = csv.DictReader(io.StringIO(categories_csv))
    for row in reader:
        category_names[row["label"]] = row["name"]

    entries: list[CliEntry] = []
    today = date.today().isoformat()
    reader = csv.DictReader(io.StringIO(apps_csv))
    for row in reader:
        git_url = row.get("git", "").strip()
        homepage = row.get("homepage", "").strip()
        repo_url = normalize_repo_url(git_url or homepage)
        entry_id = parse_github_id(repo_url)
        if not entry_id:
            continue

        upstream = row.get("category", "").strip()
        name = row.get("name", entry_id.split("/")[-1]).strip()
        description = row.get("description", "").strip()
        category = categorize(upstream, slug_to_group, default_group)

        entry = CliEntry(
            id=entry_id,
            name=name,
            description=description,
            repo_url=repo_url,
            homepage=homepage if homepage and homepage != git_url else "",
            category=category,
            tags=derive_tags(CliEntry(id=entry_id, name=name, description=description, repo_url=repo_url), upstream),
            sources=[
                SourceRef(
                    id=source_id,
                    repo=source_repo,
                    commit=commit,
                    upstream_category=upstream,
                )
            ],
            first_seen_at=today,
            updated_at=today,
        )
        if upstream in category_names and category_names[upstream] not in entry.tags:
            entry.tags.append(category_names[upstream].lower().replace(" ", "-"))
        entries.append(entry)
    return entries
