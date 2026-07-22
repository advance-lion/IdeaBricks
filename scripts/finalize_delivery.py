from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the Worker-to-Foreman delivery receipt.")
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    run_dir = Path(args.run_dir).resolve()
    contract = json.loads((run_dir / "mvp-contract.json").read_text(encoding="utf-8-sig"))
    report_path = run_dir / "artifacts" / "acceptance-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {"status": "FAIL", "reason": "Acceptance report missing"}
    # The delivery receipt itself is listed in the public contract, but it is
    # created by this command. Validate every other promised artifact first.
    required = [
        run_dir / relative
        for relative in contract.get("delivery", {}).get("required_files", [])
        if relative != "worker-delivery.json"
    ]
    missing = [str(path) for path in required if not path.is_file()]
    status = "PASS" if report.get("status") == "PASS" and not missing else "FAIL"
    delivery = {
        "run_id": contract.get("run_id"),
        "worker": "mvp-worker",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": status,
        "artifacts": {
            "source_dir": str(run_dir / "app"),
            "ui_spec": str(run_dir / "ui-spec.json"),
            "preview": str(run_dir / "artifacts" / "preview.png"),
            "acceptance_report": str(report_path),
        },
        "acceptance_status": report.get("status"),
        "missing_required_files": missing,
        "github": "SKIPPED_BY_CONTRACT" if not contract.get("delivery", {}).get("github_enabled") else "NOT_IMPLEMENTED",
    }
    output = run_dir / "worker-delivery.json"
    output.write_text(json.dumps(delivery, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(delivery, ensure_ascii=False, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
