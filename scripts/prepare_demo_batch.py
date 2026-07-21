from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def build_contract(
    run_id: str,
    screenshot: Path,
    name: str,
    kind: str,
    visual_requirements: list[str],
    interactions: list[str],
) -> dict[str, Any]:
    return {
        "contract_version": "1.0",
        "run_id": run_id,
        "handoff": {"from": "demo-foreman-simulator", "to": "mvp-worker"},
        "source_screenshot": {"path": str(screenshot), "authorized_for_demo": True, "reference_only": True},
        "app": {
            "name": name,
            "kind": kind,
            "goal": "Create a runnable frontend that closely reconstructs the screenshot's layout, hierarchy, dominant visual rhythm and visible interaction state without reproducing source branding or protected assets.",
            "reference_fidelity": {
                "priority": "high",
                "preserve": ["viewport rhythm", "section order", "component geometry", "dominant colour blocks", "navigation placement", "visible modal or drawer state", "interaction entry points"],
                "replace": ["brand", "logo", "product photography", "product names", "prices", "source wording", "user data"],
            },
            "visual_requirements": visual_requirements,
            "required_interactions": interactions,
            "out_of_scope": ["accounts", "payments", "orders", "backend", "remote API", "external image loading"],
        },
        "acceptance": {
            "viewport": {"width": 390, "height": 844},
            "required_testids": ["app-shell", "search-input", "recommendation-list", "cart-count", "add-to-cart", "qa-result"],
            "required_checks": ["page-load", "required-sections", "search-or-filter", "primary-action"],
            "maximum_repair_attempts": 1,
        },
        "delivery": {
            "github_enabled": False,
            "required_files": ["ui-spec.json", "app/index.html", "app/styles.css", "app/app.js", "artifacts/preview.png", "artifacts/acceptance-report.json", "worker-delivery.json"],
        },
    }


def prepare_run(contract_path: Path) -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / "prepare_run.py"), "--contract", str(contract_path)], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare two authorized screenshots for an mvp-worker recording batch.")
    parser.add_argument("--kfc", required=True, help="Food ordering screenshot")
    parser.add_argument("--taobao", required=True, help="Shopping home screenshot")
    parser.add_argument("--batch-id", default="screenshot-to-app-recording-001")
    args = parser.parse_args()
    batch_id = args.batch_id
    sources = {"fastbite": Path(args.kfc).resolve(), "malllite": Path(args.taobao).resolve()}
    for source in sources.values():
        if not source.is_file():
            raise FileNotFoundError(source)
    input_dir = ROOT / "inputs" / batch_id
    input_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, Path] = {}
    for name, source in sources.items():
        target = input_dir / f"{name}-reference{source.suffix.lower()}"
        shutil.copy2(source, target)
        copied[name] = target

    contracts = [
        build_contract(
            f"{batch_id}-fastbite", copied["fastbite"], "FastBite", "mobile food-ordering frontend",
            ["warm promotion hero", "store summary", "menu categories", "food cards", "pickup mode"],
            ["category or search filter changes cards", "add-to-cart updates visible count", "pickup mode can be selected"],
        ),
        build_contract(
            f"{batch_id}-malllite", copied["malllite"], "MallLite", "mobile product-discovery frontend",
            ["recommendation tabs", "search bar", "shortcut grid", "promotion strip", "two-column product discovery cards", "bottom navigation"],
            ["search or category filter changes cards", "add-to-cart updates visible count"],
        ),
    ]
    contract_dir = ROOT / "contracts" / batch_id
    contract_dir.mkdir(parents=True, exist_ok=True)
    contract_paths = []
    for contract in contracts:
        contract_path = contract_dir / f"{contract['run_id']}.json"
        contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
        prepare_run(contract_path)
        contract_paths.append(contract_path)
    batch = {
        "batch_id": batch_id,
        "prepared_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "worker": "mvp-worker",
        "runs": [
            {"run_id": contract["run_id"], "contract": str(path), "app_name": contract["app"]["name"]}
            for contract, path in zip(contracts, contract_paths)
        ],
        "github": {"enabled": False, "rule": "Create a local Git commit after PASS. A remote GitHub push needs explicit repository and approval."},
    }
    batch_path = contract_dir / "demo-batch.json"
    batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(batch, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
