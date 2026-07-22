from __future__ import annotations

"""Run one online incubation from persistent catalog to Idea Agent.

CLI Researcher is deliberately outside this request path: it maintains the
saved catalog snapshot on its own schedule. Foreman reads that snapshot,
dispatches Idea Agent, validates the ranked result, freezes the contract, and
later authorizes Worker after a screenshot is attached.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(sys.executable)
CODEX = ROOT / ".tools" / "codex-cli" / "node_modules" / ".pnpm" / "@openai+codex@0.144.6" / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
GROUP = "g_f5118483aa7a"

for stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure:
        reconfigure(encoding="utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def log(path: Path, message: str) -> None:
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as output:
        output.write(line + "\n")


def kill_tree(process: subprocess.Popen[str]) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    else:
        process.kill()


def codex_command() -> list[str] | None:
    """Resolve either the packaged Codex CLI entry or a normal PATH install."""
    configured = os.environ.get("CODEX_BIN", "").strip()
    candidate = Path(configured).expanduser() if configured else None
    if candidate and candidate.is_file():
        if candidate.suffix.lower() == ".js":
            node = shutil.which("node")
            return [node, str(candidate)] if node else None
        return [str(candidate)]
    node = shutil.which("node")
    if CODEX.is_file() and node:
        return [node, str(CODEX)]
    executable = shutil.which("codex") or shutil.which("codex.exe") or shutil.which("codex.cmd")
    return [executable] if executable else None


def codex_run(prompt: str, output: Path, timeout: int, run_log: Path) -> tuple[bool, str]:
    command = codex_command()
    if not command:
        return False, "Codex CLI is unavailable; install codex or set CODEX_BIN"
    process = subprocess.Popen(
        [*command, "exec", "--ephemeral", "--dangerously-bypass-approvals-and-sandbox", "-C", str(ROOT), "-o", str(output), "-"],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    try:
        stdout, stderr = process.communicate(prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(process)
        stdout, stderr = process.communicate()
        log(run_log, f"CODEX timeout after {timeout}s")
        return False, f"timeout after {timeout}s"
    transcript = (stdout + "\n" + stderr).strip()
    if transcript:
        with run_log.open("a", encoding="utf-8") as destination:
            destination.write(transcript[-8000:] + "\n")
    if process.returncode:
        return False, (stderr or stdout or f"Codex exit {process.returncode}")[-900:]
    return True, "completed"


def claude_command() -> str | None:
    """Resolve Claude Code without assuming a particular install location."""
    configured = os.environ.get("CLAUDE_BIN", "").strip()
    if configured:
        return configured
    return shutil.which("claude") or shutil.which("claude.exe")


def claude_run(prompt: str, output: Path, timeout: int, run_log: Path) -> tuple[bool, str]:
    """Run the same Stage-2 contract through Claude Code's noninteractive mode."""
    command = claude_command()
    if not command:
        return False, "Claude Code is unavailable"
    process = subprocess.Popen(
        [
            command, "--print", "--output-format", "text", "--no-session-persistence",
            "--dangerously-skip-permissions", prompt,
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_tree(process)
        stdout, stderr = process.communicate()
        log(run_log, f"CLAUDE timeout after {timeout}s")
        return False, f"timeout after {timeout}s"
    output.write_text(stdout, encoding="utf-8")
    transcript = (stdout + "\n" + stderr).strip()
    if transcript:
        with run_log.open("a", encoding="utf-8") as destination:
            destination.write(transcript[-8000:] + "\n")
    if process.returncode:
        return False, (stderr or stdout or f"Claude exit {process.returncode}")[-900:]
    return True, "completed"


def cccc_send(sender: str, recipient: str, text: str, run_log: Path, priority: str = "normal") -> None:
    command = shutil.which("cccc")
    if not command:
        log(run_log, "CCCC message skipped: command unavailable")
        return
    env = os.environ.copy()
    env.update({"CCCC_EXE": command, "CCCC_TEXT": text, "CCCC_GROUP": GROUP, "CCCC_BY": sender, "CCCC_TO": recipient, "CCCC_PRIORITY": priority})
    powershell = shutil.which("powershell") or shutil.which("powershell.exe")
    if not powershell:
        log(run_log, "CCCC message skipped: PowerShell unavailable")
        return
    result = subprocess.run(
        [powershell, "-NoProfile", "-Command", "& $env:CCCC_EXE send $env:CCCC_TEXT --group $env:CCCC_GROUP --by $env:CCCC_BY --to $env:CCCC_TO --priority $env:CCCC_PRIORITY"],
        cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
    )
    if result.returncode:
        log(run_log, "CCCC message skipped: " + (result.stderr or result.stdout).strip()[-300:])


def stage1_valid(path: Path, run_id: str) -> bool:
    value = read_json(path)
    return value.get("run_id") == run_id and value.get("source") == "cli-researcher" and value.get("validation", {}).get("status") == "PASS" and bool(value.get("summary_index"))


def stage2_valid(shortlist_path: Path, contract_path: Path, run_id: str) -> bool:
    shortlist, contract = read_json(shortlist_path), read_json(contract_path)
    return (
        shortlist.get("run_id") == run_id
        and bool(shortlist.get("recommended_idea", {}).get("idea_id"))
        and contract.get("run_id") == run_id
        and contract.get("handoff", {}).get("from") == "idea-foreman"
        and contract.get("handoff", {}).get("to") == "mvp-worker"
    )


def run_adapter(script: str, run_id: str, run_log: Path) -> bool:
    result = subprocess.run([str(PYTHON), script, "--run-id", run_id], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    log(run_log, f"adapter {script}: {'PASS' if result.returncode == 0 else 'FAIL'}")
    if result.stdout:
        log(run_log, result.stdout.strip()[-1200:])
    if result.stderr:
        log(run_log, result.stderr.strip()[-1200:])
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Foreman orchestration from persistent CLI snapshot to Idea Agent.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--stage2-timeout", type=int, default=90)
    args = parser.parse_args()
    if not args.run_id.startswith("incubation-"):
        raise SystemExit("run_id 必须是 incubation-* 格式")

    handoff = ROOT / "handoffs" / args.run_id
    request = handoff / "request.json"
    cli_form = handoff / "cli-capability-form.json"
    shortlist = handoff / "idea-shortlist.json"
    contract = handoff / "mvp-contract.json"
    run_log = handoff / "orchestration.log"
    codex_stage2 = handoff / "codex-stage2-last-message.md"
    claude_stage2 = handoff / "claude-stage2-last-message.md"
    if not request.is_file():
        raise SystemExit(f"missing request: {request}")

    log(run_log, "pipeline START: Foreman consumes persistent CLI snapshot; CLI Agent is not invoked")
    if stage1_valid(cli_form, args.run_id):
        catalog_mode = "existing-run-reference"
        log(run_log, "Catalog: valid run reference already exists")
    else:
        log(run_log, "Catalog: Foreman is materializing the saved snapshot reference")
        if not run_adapter("scripts/build_cli_handoff.py", args.run_id, run_log) or not stage1_valid(cli_form, args.run_id):
            raise SystemExit("Catalog snapshot unavailable or invalid; request CLI maintenance before retrying")
        catalog_mode = "persistent-catalog-snapshot"
    cccc_send(
        "idea-foreman", "idea-agent",
        f"{args.run_id}：Foreman 已读取持久化 CLI 能力快照（CLI Agent 本轮未介入）。请结合 request.json 与 cli-capability-form.json 执行创意挖掘和排序。",
        run_log, "attention",
    )
    log(run_log, f"Catalog PASS via {catalog_mode}; dispatched directly to Idea Agent")

    stage2_prompt = f"""You are the A2 Idea Agent in a CCCC team. Work on run {args.run_id}.
Read agents/idea-agent/AGENTS.md, its A2 skill, TEAM-ARCHITECTURE.md, {request}, and {cli_form}.
The CLI form is a run-scoped reference to the already maintained persistent catalog snapshot; do not invoke CLI Researcher or refresh the catalog.
Perform Stage 2 now: generate and rank ideas by visual expression, generality, pain point, innovation.
The demo's central execution capability is screenshot-to-runnable-app. Therefore the recommended idea must directly guide mvp-worker through authorized screenshot -> visual/layout understanding -> runnable local frontend -> browser QA -> evidence delivery. The user request determines the scenario, not whether this capability is used.
Write valid {shortlist} and {contract}. The contract must hand off from idea-foreman to mvp-worker, but keep Worker blocked until the Foreman supplies an authorized screenshot input. Do not start Worker. Finish only after both files exist."""
    if stage2_valid(shortlist, contract, args.run_id):
        stage2_mode = "existing-valid-handoff"
        log(run_log, "Stage 2: valid handoffs already exist; resuming without rerun")
    else:
        stage2_mode = "adapter"
        attempts = (
            ("codex-cli", codex_run, codex_stage2),
            ("claude-code", claude_run, claude_stage2),
        )
        for engine, runner, output in attempts:
            log(run_log, f"Stage 2: requesting {engine} as idea-agent")
            completed, detail = runner(stage2_prompt, output, args.stage2_timeout, run_log)
            if completed and stage2_valid(shortlist, contract, args.run_id):
                stage2_mode = engine
                break
            log(run_log, f"Stage 2: {engine} result invalid ({detail})")
        if stage2_mode == "adapter":
            log(run_log, "Stage 2: no CLI agent produced valid handoffs; using deterministic adapter")
            if not run_adapter("scripts/build_idea_handoff.py", args.run_id, run_log) or not stage2_valid(shortlist, contract, args.run_id):
                raise SystemExit("Stage 2 failed: no valid idea handoffs")
    cccc_send("idea-agent", "idea-foreman", f"Stage 2 完成：{args.run_id} 的 idea-shortlist.json 与 mvp-contract.json 已交付（执行模式：{stage2_mode}）。推荐截图生成可运行 App；等待 Foreman 补充授权截图后再派发 Worker。", run_log, "attention")
    cccc_send("idea-foreman", "user", f"平台链路已跑到 MVP 契约：{args.run_id}。Foreman 已复用持久能力库并完成 Idea 阶段；Worker 当前等待授权截图输入。", run_log)
    log(run_log, f"Stage 2 PASS via {stage2_mode}; Worker intentionally blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
