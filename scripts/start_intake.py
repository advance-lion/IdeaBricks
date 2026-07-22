from __future__ import annotations

"""Start the local intake desk and open it once the listener answers.

This wrapper keeps the double-click launcher dependency-free: it shares the
same Python process as the HTTP server and uses only the standard library.
"""

import argparse
import runpy
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def open_when_ready(url: str) -> None:
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1):
                webbrowser.open(url, new=2)
                return
        except OSError:
            time.sleep(0.25)


def main() -> int:
    parser = argparse.ArgumentParser(description="Start the local Forge intake desk and open a browser.")
    parser.add_argument("--port", type=int, default=4181)
    args = parser.parse_args()
    url = f"http://127.0.0.1:{args.port}/"
    print(f"[Forge] Waiting for {url}", flush=True)
    threading.Thread(target=open_when_ready, args=(url,), daemon=True).start()
    sys.argv = [str(ROOT / "scripts" / "worker_intake_server.py"), "--port", str(args.port)]
    runpy.run_path(str(ROOT / "scripts" / "worker_intake_server.py"), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
