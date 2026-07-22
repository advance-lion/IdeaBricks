from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from typing import Any


DEFAULT_HEADERS = {"User-Agent": "cli-catalog-sync/0.1"}


def github_headers() -> dict[str, str]:
    headers = dict(DEFAULT_HEADERS)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_text(url: str, timeout: int = 60, headers: dict[str, str] | None = None) -> str:
    request = urllib.request.Request(url, headers=headers or github_headers())
    context = ssl.create_default_context()
    with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_json(url: str, timeout: int = 60, headers: dict[str, str] | None = None) -> Any:
    return json.loads(fetch_text(url, timeout=timeout, headers=headers))


def github_api(path: str) -> Any:
    return fetch_json(f"https://api.github.com{path}")


def github_raw(repo: str, branch: str, file_path: str) -> str:
    return fetch_text(
        f"https://raw.githubusercontent.com/{repo}/{branch}/{file_path.lstrip('/')}"
    )


def latest_commit(repo: str, branch: str) -> str:
    try:
        data = github_api(f"/repos/{repo}/commits/{branch}")
        return data["sha"]
    except urllib.error.HTTPError:
        data = github_api(f"/repos/{repo}")
        default_branch = data["default_branch"]
        data = github_api(f"/repos/{repo}/commits/{default_branch}")
        return data["sha"]


def fetch_repo_stars(repo_id: str) -> int | None:
    try:
        data = github_api(f"/repos/{repo_id}")
        return int(data.get("stargazers_count", 0))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
