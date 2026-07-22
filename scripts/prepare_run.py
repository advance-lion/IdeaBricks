from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(value: Any, label: str) -> Any:
    if value in (None, "", [], {}):
        raise ValueError(f"Missing required contract field: {label}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare an isolated Screenshot-to-App Worker run.")
    parser.add_argument("--contract", required=True, help="Path to mvp-contract.json")
    args = parser.parse_args()

    contract_path = Path(args.contract).resolve()
    # Windows PowerShell 5's `Set-Content -Encoding utf8` includes a BOM.
    # Accept both UTF-8 and UTF-8-with-BOM so a simulated or real Foreman can
    # produce the contract using native PowerShell without breaking the Worker.
    contract = json.loads(contract_path.read_text(encoding="utf-8-sig"))
    run_id = str(require(contract.get("run_id"), "run_id"))
    screenshot = contract.get("source_screenshot", {})
    source = Path(str(require(screenshot.get("path"), "source_screenshot.path"))).expanduser().resolve()
    if not screenshot.get("authorized_for_demo"):
        raise ValueError("source_screenshot.authorized_for_demo must be true")
    if not source.is_file():
        raise FileNotFoundError(f"Screenshot does not exist: {source}")

    app = contract.get("app", {})
    require(app.get("name"), "app.name")
    acceptance = contract.get("acceptance", {})
    require(acceptance.get("required_testids"), "acceptance.required_testids")
    require(acceptance.get("required_checks"), "acceptance.required_checks")

    run_dir = ROOT / "runs" / run_id
    if run_dir.exists() and any(run_dir.iterdir()):
        raise FileExistsError(f"Run directory already exists and is not empty: {run_dir}")
    for relative in ("input", "app", "artifacts"):
        (run_dir / relative).mkdir(parents=True, exist_ok=True)

    copied = run_dir / "input" / f"reference{source.suffix.lower()}"
    shutil.copy2(source, copied)
    copied_contract = run_dir / "mvp-contract.json"
    copied_contract.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    context = {
        "run_id": run_id,
        "prepared_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "contract": str(copied_contract),
        "source_screenshot": {
            "original_path": str(source),
            "copied_path": str(copied),
            "sha256": sha256_file(copied),
        },
        "app_dir": str(run_dir / "app"),
        "artifacts_dir": str(run_dir / "artifacts"),
    }
    context_path = run_dir / "run-context.json"
    context_path.write_text(json.dumps(context, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(context, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
