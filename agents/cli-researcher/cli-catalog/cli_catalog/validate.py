from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cli_catalog.models import entry_filename
from cli_catalog.summary import DETAIL_TEMPLATE, SUMMARY_COLUMNS, SUMMARY_SCHEMA_VERSION


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)


def _load_json(path: Path, result: ValidationResult) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - validation should report path + reason
        result.error(f"{path}: invalid JSON: {exc}")
        return None


def validate_entry(path: Path, result: ValidationResult) -> None:
    data = _load_json(path, result)
    if not isinstance(data, dict):
        result.error(f"{path}: expected object")
        return

    required = ("id", "name", "description", "repo_url", "category", "tags", "agent", "sources", "meta")
    for field_name in required:
        if field_name not in data:
            result.error(f"{path}: missing required field {field_name!r}")

    entry_id = data.get("id")
    if isinstance(entry_id, str):
        expected_name = entry_filename(entry_id)
        if path.name != expected_name:
            message = f"{path}: file name should be {expected_name!r} for id {entry_id!r}"
            if path.name.lower() == expected_name.lower():
                result.warning(message)
            else:
                result.error(message)
    else:
        result.error(f"{path}: id must be a string")

    for field_name in ("name", "description", "repo_url", "category"):
        if field_name in data and not isinstance(data[field_name], str):
            result.error(f"{path}: {field_name} must be a string")

    if "tags" in data and not isinstance(data["tags"], list):
        result.error(f"{path}: tags must be a list")
    if "sources" in data and not isinstance(data["sources"], list):
        result.error(f"{path}: sources must be a list")
    elif "sources" in data and not data["sources"]:
        result.warning(f"{path}: sources is empty")

    agent = data.get("agent")
    if not isinstance(agent, dict):
        result.error(f"{path}: agent must be an object")
    else:
        score = agent.get("score")
        if not isinstance(score, int) or not 1 <= score <= 3:
            result.error(f"{path}: agent.score must be an integer from 1 to 3")
        if "friendly" in agent and not isinstance(agent["friendly"], bool):
            result.error(f"{path}: agent.friendly must be a boolean")
        if score == 3 and agent.get("friendly") is not True:
            result.warning(f"{path}: agent.score is 3 but agent.friendly is not true")
        if "signals" in agent and not isinstance(agent["signals"], list):
            result.error(f"{path}: agent.signals must be a list")

    meta = data.get("meta")
    if not isinstance(meta, dict):
        result.error(f"{path}: meta must be an object")
    elif meta.get("status", "active") not in {"active", "deprecated"}:
        result.error(f"{path}: meta.status must be active or deprecated")


def validate_summary(summary_path: Path, data_dir: Path, result: ValidationResult) -> None:
    summary = _load_json(summary_path, result)
    if not isinstance(summary, dict):
        result.error(f"{summary_path}: expected object")
        return

    if summary.get("schema_version") != SUMMARY_SCHEMA_VERSION:
        result.error(
            f"{summary_path}: schema_version should be {SUMMARY_SCHEMA_VERSION}, got {summary.get('schema_version')!r}"
        )
    if summary.get("detail_template") != DETAIL_TEMPLATE:
        result.error(f"{summary_path}: unexpected detail_template")

    categories = summary.get("categories")
    if not isinstance(categories, list):
        result.error(f"{summary_path}: categories must be a list")
        return

    total_rows = 0
    seen_ids: set[str] = set()
    for index, category in enumerate(categories):
        if not isinstance(category, dict):
            result.error(f"{summary_path}: categories[{index}] must be an object")
            continue
        name = category.get("name")
        if not isinstance(name, str) or not name:
            result.error(f"{summary_path}: categories[{index}].name must be a non-empty string")
        if category.get("columns") != SUMMARY_COLUMNS:
            result.error(f"{summary_path}: category {name!r} has unexpected columns")
        rows = category.get("rows")
        if not isinstance(rows, list):
            result.error(f"{summary_path}: category {name!r} rows must be a list")
            continue
        if category.get("count") != len(rows):
            result.error(f"{summary_path}: category {name!r} count does not match rows length")
        total_rows += len(rows)

        for row_index, row in enumerate(rows):
            if not isinstance(row, list) or len(row) != len(SUMMARY_COLUMNS):
                result.error(f"{summary_path}: category {name!r} row {row_index} has invalid shape")
                continue
            row_id, cli, function, score = row
            if not all(isinstance(value, str) and value for value in (row_id, cli, function)):
                result.error(f"{summary_path}: category {name!r} row {row_index} has invalid text fields")
            if not isinstance(score, int) or not 1 <= score <= 3:
                result.error(f"{summary_path}: category {name!r} row {row_index} has invalid score")
            if row_id in seen_ids:
                result.error(f"{summary_path}: duplicate id in summary: {row_id}")
            seen_ids.add(row_id)
            detail_path = data_dir / entry_filename(row_id)
            if not detail_path.exists():
                result.error(f"{summary_path}: missing detail JSON for {row_id}: {detail_path}")

    counts = summary.get("counts")
    if not isinstance(counts, dict):
        result.error(f"{summary_path}: counts must be an object")
    else:
        if counts.get("total") != total_rows:
            result.error(f"{summary_path}: counts.total does not match row total")
        if counts.get("categories") != len(categories):
            result.error(f"{summary_path}: counts.categories does not match categories length")


def validate_catalog(root: Path) -> ValidationResult:
    result = ValidationResult()
    data_dir = root / "catalog" / "data"
    summary_path = root / "catalog" / "cli-summary.json"

    if not data_dir.exists():
        result.error(f"{data_dir}: directory does not exist")
        return result

    entry_paths = sorted(data_dir.glob("*.json"))
    if not entry_paths:
        result.error(f"{data_dir}: no JSON entries found")
    for path in entry_paths:
        validate_entry(path, result)

    if summary_path.exists():
        validate_summary(summary_path, data_dir, result)
    else:
        result.warning(f"{summary_path}: summary file does not exist")

    return result
