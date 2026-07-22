from __future__ import annotations

"""Maintain and consume the persistent CLI capability snapshot.

CLI Researcher owns the long-lived catalog and refreshes the snapshot only as
an offline maintenance job. A Foreman run merely materializes a tiny,
run-scoped reference to that already saved snapshot; it never wakes the CLI
actor or performs a market/catalog refresh on the critical path.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CATALOG_ROOT = ROOT / "agents" / "cli-researcher" / "cli-catalog"
SNAPSHOT_PATH = CATALOG_ROOT / "catalog" / "idea-capability-snapshot.json"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def relevant_records(summary: dict[str, Any]) -> list[dict[str, Any]]:
    keywords = ("image", "screenshot", "browser", "web", "frontend", "ui", "test", "automation", "agent", "git", "code")
    selected: list[dict[str, Any]] = []
    for category in summary.get("categories", []):
        columns = category.get("columns", [])
        for row in category.get("rows", []):
            record = dict(zip(columns, row))
            text = " ".join(str(value) for value in record.values()).lower()
            if any(keyword in text for keyword in keywords):
                selected.append({"category": category.get("name", "Uncategorized"), **record})
            if len(selected) >= 12:
                return selected
    return selected


def refresh_snapshot() -> dict[str, Any]:
    """CLI Agent maintenance path: validate the catalog and persist its view."""
    validation = subprocess.run(
        [sys.executable, "-m", "cli_catalog", "validate"], cwd=CATALOG_ROOT,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    if validation.returncode:
        raise SystemExit((validation.stderr or validation.stdout or "CLI catalog validate failed").strip())
    summary_path = CATALOG_ROOT / "catalog" / "cli-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    categories = summary.get("categories", [])
    payload = {
        "source": "cli-researcher",
        "supply_mode": "persistent-catalog-snapshot",
        "maintenance_role": "CLI Agent periodically refreshes this file outside incubation runs",
        "summary_index": "agents/cli-researcher/cli-catalog/catalog/cli-summary.json",
        "full_records_root": "agents/cli-researcher/cli-catalog/catalog/data",
        "schema": "agents/cli-researcher/cli-catalog/schema/cli.schema.json",
        "field_docs": "agents/cli-researcher/cli-catalog/docs/FIELDS.md",
        "snapshot_path": "agents/cli-researcher/cli-catalog/catalog/idea-capability-snapshot.json",
        "validation": {
            "status": "PASS", "command": "python -m cli_catalog validate",
            "output": validation.stdout.strip(),
            "validated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
        "catalog_counts": {
            "categories": len(categories),
            "records": sum(int(category.get("count", 0)) for category in categories),
        },
        "capabilities": relevant_records(summary),
    }
    write_json(SNAPSHOT_PATH, payload)
    return payload


def load_snapshot() -> dict[str, Any]:
    if not SNAPSHOT_PATH.is_file():
        raise SystemExit(
            "Persistent CLI snapshot is missing. Run the maintenance command once: "
            "python scripts/build_cli_handoff.py --refresh-snapshot"
        )
    payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8-sig"))
    if payload.get("source") != "cli-researcher" or payload.get("validation", {}).get("status") != "PASS":
        raise SystemExit("Persistent CLI capability snapshot is invalid")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh or consume the persistent CLI capability snapshot.")
    parser.add_argument("--run-id")
    parser.add_argument("--refresh-snapshot", action="store_true")
    args = parser.parse_args()
    if args.refresh_snapshot:
        refresh_snapshot()
        print(SNAPSHOT_PATH, flush=True)
        if not args.run_id:
            return 0
    if not args.run_id or not args.run_id.startswith("incubation-"):
        raise SystemExit("run_id 必须是 incubation-* 格式")
    payload = dict(load_snapshot())
    payload.update({
        "run_id": args.run_id,
        "consumed_by": "idea-foreman",
        "consumed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "provenance": "Foreman consumed the saved CLI catalog snapshot; CLI Agent was not invoked for this run",
    })
    destination = ROOT / "handoffs" / args.run_id / "cli-capability-form.json"
    write_json(destination, payload)
    print(destination, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
