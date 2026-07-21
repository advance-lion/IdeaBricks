from __future__ import annotations

import argparse
import contextlib
import html
import http.server
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import threading
from pathlib import Path
from typing import Any, Iterator


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return


def browser_path() -> str | None:
    configured = os.environ.get("MVP_WORKER_BROWSER")
    candidates = [
        configured,
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        shutil.which("msedge"),
        shutil.which("chrome"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return str(Path(candidate))
    return None


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


@contextlib.contextmanager
def server(directory: Path) -> Iterator[str]:
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", free_port()), lambda *args, **kwargs: QuietHandler(*args, directory=str(directory), **kwargs))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}/index.html"
    finally:
        httpd.shutdown()
        thread.join(timeout=3)
        httpd.server_close()


def qa_result(dom: str) -> dict[str, Any] | None:
    match = re.search(r'<[^>]*data-testid=["\']qa-result["\'][^>]*>(.*?)</[^>]+>', dom, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(html.unescape(match.group(1)).strip())
    except json.JSONDecodeError:
        return None


def emit(path: Path, report: dict[str, Any]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run browser acceptance for a Screenshot-to-App Worker run.")
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    report_path = run_dir / "artifacts" / "acceptance-report.json"
    app_dir = run_dir / "app"
    contract_path = run_dir / "mvp-contract.json"
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return emit(report_path, {"status": "FAIL", "reason": f"Invalid contract: {exc}", "checks": []})

    required_files = [app_dir / name for name in ("index.html", "styles.css", "app.js")]
    missing = [str(path) for path in required_files if not path.is_file()]
    if missing:
        return emit(report_path, {"status": "FAIL", "reason": "Missing generated app files", "missing": missing, "checks": []})
    browser = browser_path()
    if not browser:
        return emit(report_path, {"status": "FAIL", "reason": "Edge or Chrome was not found", "checks": []})

    viewport = contract.get("acceptance", {}).get("viewport", {})
    width, height = int(viewport.get("width", 390)), int(viewport.get("height", 844))
    preview = run_dir / "artifacts" / "preview.png"
    required_testids = contract.get("acceptance", {}).get("required_testids", [])
    required_checks = set(contract.get("acceptance", {}).get("required_checks", []))

    with server(app_dir) as url, tempfile.TemporaryDirectory(prefix="mvp-worker-browser-") as profile:
        qa_url = f"{url}?qa=1"
        base = [browser, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={profile}", f"--window-size={width},{height}", "--virtual-time-budget=3000"]
        screenshot = subprocess.run([*base, f"--screenshot={preview}", qa_url], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
        dump = subprocess.run([*base, "--dump-dom", qa_url], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)

    rendered_testids = {value for value in re.findall(r'data-testid=["\']([^"\']+)["\']', dump.stdout)}
    result = qa_result(dump.stdout)
    qa_checks = result.get("checks", []) if isinstance(result, dict) else []
    passed_ids = {check.get("id") for check in qa_checks if isinstance(check, dict) and check.get("status") == "PASS"}
    checks = [
        {"id": "page-load", "status": "PASS" if dump.returncode == 0 else "FAIL", "evidence": f"dump-dom exit={dump.returncode}"},
        {"id": "required-testids", "status": "PASS" if set(required_testids).issubset(rendered_testids) else "FAIL", "missing": sorted(set(required_testids) - rendered_testids)},
        {"id": "qa-result", "status": "PASS" if isinstance(result, dict) and result.get("status") == "PASS" else "FAIL", "result": result},
        {"id": "required-interactions", "status": "PASS" if required_checks.issubset(passed_ids) else "FAIL", "missing": sorted(required_checks - passed_ids)},
        {"id": "preview", "status": "PASS" if preview.is_file() and preview.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") and screenshot.returncode == 0 else "FAIL", "path": str(preview)},
    ]
    passed = all(check["status"] == "PASS" for check in checks)
    report = {
        "status": "PASS" if passed else "FAIL",
        "url": url,
        "qa_url": qa_url,
        "browser": browser,
        "viewport": {"width": width, "height": height},
        "checks": checks,
        "browser_stderr": {"screenshot": screenshot.stderr[-1000:], "dump_dom": dump.stderr[-1000:]},
    }
    return emit(report_path, report)


if __name__ == "__main__":
    raise SystemExit(main())
