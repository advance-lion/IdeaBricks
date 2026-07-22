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
import time
import urllib.error
import urllib.request
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


def model_settings() -> dict[str, Any]:
    """Read the shared OpenAI-compatible Local LLM configuration.

    This intentionally matches the Worker configuration, so one untracked
    ``config/local-model.local.json`` enables both Idea Agent and Worker on a
    host without a coding CLI.
    """
    config_path = ROOT / "config" / "local-model.local.json"
    from_file = read_json(config_path) if config_path.is_file() else {}
    return {
        "base_url": os.environ.get("LOCAL_MODEL_BASE_URL") or os.environ.get("LOCAL_LLM_BASE_URL") or from_file.get("base_url", ""),
        "api_key": os.environ.get("LOCAL_MODEL_API_KEY") or os.environ.get("LOCAL_LLM_API_KEY") or from_file.get("api_key", ""),
        "model": os.environ.get("LOCAL_MODEL_NAME") or os.environ.get("LOCAL_LLM_MODEL") or from_file.get("model", ""),
        "timeout": int(os.environ.get("LOCAL_MODEL_TIMEOUT") or from_file.get("timeout_seconds", 60)),
        "idea_timeout": int(os.environ.get("LOCAL_MODEL_IDEA_TIMEOUT") or from_file.get("idea_timeout_seconds", 90)),
    }


def local_chat(settings: dict[str, Any], prompt: str, *, max_tokens: int, timeout: int) -> str:
    """Call an OpenAI-compatible chat-completions endpoint without an SDK."""
    base_url = str(settings.get("base_url", "")).rstrip("/")
    model = str(settings.get("model", ""))
    api_key = str(settings.get("api_key", ""))
    if not base_url or not model:
        raise RuntimeError("Local LLM is not configured (set LOCAL_MODEL_BASE_URL and LOCAL_MODEL_NAME)")
    payload = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        f"{base_url}/chat/completions", data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=max(30, timeout)) as response:
            response_json = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[-800:]
        raise RuntimeError(f"Local LLM rejected the Stage 2 request: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Local LLM is unavailable: {exc}") from exc
    content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Local LLM returned no Stage 2 content")
    return content


def parse_local_json(content: str) -> dict[str, Any]:
    """Accept a JSON-only reply while tolerating an accidental code fence."""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    candidate = cleaned if start < 0 or end <= start else cleaned[start:end + 1]
    value = json.loads(candidate)
    if not isinstance(value, dict):
        raise RuntimeError("Local LLM Stage 2 response was not a JSON object")
    return value


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


def local_idea_prompt(run_id: str, request: Path, cli_form: Path) -> str:
    """Constrain a small local model to the portable Stage-2 response schema."""
    return f"""You are the Idea Agent in a screenshot-to-app CCCC team. Produce the idea-ranking input for run {run_id}.

User request JSON:
{request.read_text(encoding="utf-8-sig")}

CLI capability snapshot reference JSON (catalog evidence only; do not claim its tools are installed or invoke its researcher):
{cli_form.read_text(encoding="utf-8-sig")}

Return ONLY one valid compact JSON object, no markdown. Use exactly this shape:
{{
  "recommended_index": 0,
  "selection_rationale": "short reason",
  "ideas": [
    {{
      "name": "short product name",
      "target_user": "specific user",
      "problem": "specific problem",
      "solution": "solution",
      "four_criterion_scores": {{"visual_expression": 0, "generality": 0, "pain_point": 0, "innovation": 0}},
      "trade_offs": ["one honest limitation"]
    }}
  ]
}}

Provide 1 to 3 ranked ideas. Scores must be integers from 0 to 100. The selected idea must use this exact demo chain: authorized screenshot -> visual/layout understanding -> runnable fictional-brand local frontend -> browser QA -> evidence delivery. Do not use real brands, real transactions, accounts, or external network requests. The Worker must remain blocked until Foreman records the authorized screenshot path."""


def local_idea_run(run_id: str, request: Path, cli_form: Path, output: Path, timeout: int, run_log: Path) -> tuple[bool, str]:
    """Ask Local LLM for candidates, then save validated JSON for the adapter."""
    started = time.monotonic()
    try:
        settings = model_settings()
        effective_timeout = min(timeout, max(30, int(settings["idea_timeout"])))
        content = local_chat(settings, local_idea_prompt(run_id, request, cli_form), max_tokens=1400, timeout=effective_timeout)
        value = parse_local_json(content)
        output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        elapsed = time.monotonic() - started
        log(run_log, f"LOCAL IDEA completed: model={settings.get('model', '')}, elapsed_seconds={elapsed:.2f}")
        return True, f"completed with {settings.get('model', '')} in {elapsed:.2f}s"
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        elapsed = time.monotonic() - started
        log(run_log, f"LOCAL IDEA failed after {elapsed:.2f}s: {exc}")
        return False, str(exc)[-900:]


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


def run_adapter(script: str, run_id: str, run_log: Path, idea_source: Path | None = None) -> bool:
    command = [str(PYTHON), script, "--run-id", run_id]
    if idea_source:
        command.extend(["--idea-source", str(idea_source)])
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
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
    local_stage2 = handoff / "local-stage2-response.json"
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
            ("local-openai", local_idea_run, local_stage2),
            ("codex-cli", codex_run, codex_stage2),
            ("claude-code", claude_run, claude_stage2),
        )
        for engine, runner, output in attempts:
            log(run_log, f"Stage 2: requesting {engine} as idea-agent")
            if engine == "local-openai":
                completed, detail = local_idea_run(args.run_id, request, cli_form, output, args.stage2_timeout, run_log)
                if completed:
                    completed = run_adapter("scripts/build_idea_handoff.py", args.run_id, run_log, output)
                    detail = "completed and normalized" if completed else "local response could not be normalized"
            else:
                completed, detail = runner(stage2_prompt, output, args.stage2_timeout, run_log)
            if completed and stage2_valid(shortlist, contract, args.run_id):
                stage2_mode = engine
                break
            log(run_log, f"Stage 2: {engine} result invalid ({detail})")
        if stage2_mode == "adapter":
            log(run_log, "Stage 2: no configured model agent produced valid handoffs; using deterministic adapter")
            if not run_adapter("scripts/build_idea_handoff.py", args.run_id, run_log) or not stage2_valid(shortlist, contract, args.run_id):
                raise SystemExit("Stage 2 failed: no valid idea handoffs")
    cccc_send("idea-agent", "idea-foreman", f"Stage 2 完成：{args.run_id} 的 idea-shortlist.json 与 mvp-contract.json 已交付（执行模式：{stage2_mode}）。推荐截图生成可运行 App；等待 Foreman 补充授权截图后再派发 Worker。", run_log, "attention")
    cccc_send("idea-foreman", "user", f"平台链路已跑到 MVP 契约：{args.run_id}。Foreman 已复用持久能力库并完成 Idea 阶段；Worker 当前等待授权截图输入。", run_log)
    log(run_log, f"Stage 2 PASS via {stage2_mode}; Worker intentionally blocked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
