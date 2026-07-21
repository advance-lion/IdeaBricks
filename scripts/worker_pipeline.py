from __future__ import annotations

"""Deterministic controller for one Screenshot-to-App Worker run.

The controller owns phase progression and evidence. A model only generates
content; it cannot leave a run between VISUAL and SCAFFOLD by forgetting the
next instruction. `codex` is the reliable development backend, while
`local-openai` is the DGX Spark handoff point for any OpenAI-compatible local
VLM/LLM. CCCC remains the visible orchestration/control plane.
"""

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import time
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "scripts" / "python.cmd"
CODEX = ROOT / ".tools" / "codex-cli" / "node_modules" / ".bin" / "codex.CMD"


def emit(line: str) -> None:
    print(f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] {line}", flush=True)


def call(*args: str, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=timeout)


def progress(batch: str, run_id: str, phase: str, status: str, key: str) -> None:
    result = call(str(PYTHON), "scripts/worker_progress.py", "--batch", batch, "--run", run_id, "--phase", phase, "--status", status, "--message-key", key, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout or "无法写入 Worker 进度")
    emit(result.stdout.strip())


def load_contract(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def run_dir_from(contract: dict[str, Any]) -> Path:
    return ROOT / "runs" / str(contract["run_id"])


def required_paths(run_dir: Path) -> list[Path]:
    return [run_dir / "ui-spec.json", run_dir / "app" / "index.html", run_dir / "app" / "styles.css", run_dir / "app" / "app.js"]


def template_kind(contract: dict[str, Any]) -> str:
    kind = str(contract.get("app", {}).get("kind", "")).lower()
    return "malllite" if any(word in kind for word in ("shopping", "discovery", "market", "mall")) else "fastbite"


def write_template_ui_spec(contract: dict[str, Any], run_dir: Path) -> None:
    """Stable pre-VLM visual baseline; it is deliberately labelled as such."""
    kind = template_kind(contract)
    if kind == "malllite":
        structure = ["频道标签与搜索框", "快捷入口网格", "促销卡与活动条", "双列发现流", "固定底部导航"]
        palette = ["橙红行动色", "白色卡片", "浅暖灰背景"]
    else:
        structure = ["红色促销 Hero", "门店信息卡", "左侧分类栏", "菜品列表", "固定餐袋栏", "打开的取餐方式弹层"]
        palette = ["高饱和红色 Hero", "白色门店卡", "浅灰菜单区", "暗色遮罩", "红色确认按钮"]
    spec = {
        "run_id": contract["run_id"],
        "generator": "deterministic-template-baseline",
        "note": "Pre-local-VLM stability mode. This baseline validates the worker pipeline; replace this visual-spec step with a VLM for screenshot-specific layout extraction.",
        "high_fidelity_structure": {"priority": "baseline", "template": kind, "preserved": structure, "dominant_palette": palette},
        "replaced_source_assets": ["brand", "logo", "product photography", "product names", "prices", "source copy", "user data"],
        "interactions": ["filter changes visible cards", "primary action updates visible count", "QA mode executes real functions"],
    }
    (run_dir / "ui-spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")


def write_template_app(contract: dict[str, Any], run_dir: Path) -> None:
    kind = template_kind(contract)
    source = ROOT / "runs" / "screenshot-to-app-recording-001-fastbite" / "app"
    if kind == "malllite":
        source = ROOT / "runs" / "screenshot-to-app-recording-001-malllite" / "app"
    if not source.is_dir():
        raise RuntimeError(f"稳定模板缺失：{source}")
    destination = run_dir / "app"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("index.html", "styles.css", "app.js"):
        text = (source / name).read_text(encoding="utf-8")
        if name == "index.html":
            app_name = str(contract.get("app", {}).get("name", "SparkMVP"))
            text = text.replace("好食街", app_name).replace("拾光集", app_name)
        (destination / name).write_text(text, encoding="utf-8")


def codex_prompt(contract_path: Path, run_dir: Path, image_path: Path) -> str:
    return f"""You are the content-generation step of a deterministic Screenshot-to-App Worker pipeline.

Read this contract: {contract_path}
Reference screenshot (authorized, layout reference only): {image_path}

You have workspace write access. Use apply_patch NOW to create exactly these files, and no files outside this run directory:
{run_dir / 'ui-spec.json'}
{run_dir / 'app' / 'index.html'}
{run_dir / 'app' / 'styles.css'}
{run_dir / 'app' / 'app.js'}

The controller will run browser acceptance afterwards. This task must finish in one pass. Do not reply with a plan, an acknowledgement, or “understood”. Keep using tools until all four paths exist, then verify them with a file listing before replying.

Critical fidelity rule: closely reproduce the screenshot's viewport rhythm, section order, component geometry, dominant colour blocks, information density, visible modal/drawer state, navigation placement, and interaction entry points. Do NOT turn it into a loosely inspired redesign.

Safety/content rule: use a fictional app name and self-authored CSS/SVG illustrations. Do not copy logos, brands, product photos, prices, source wording, or user data.

Implement all contract test IDs, including data-testid=app-shell, search-input, recommendation-list, cart-count, add-to-cart, and qa-result. Under ?qa=1, invoke real filter/search and primary-action functions then write PASS/FAIL JSON to qa-result; do not hardcode success.

ui-spec.json must contain high_fidelity_structure and replaced_source_assets. Use no external network requests or external image URLs. Reply briefly only after the four files exist."""


def run_codex(contract_path: Path, run_dir: Path, image_path: Path) -> None:
    if not CODEX.is_file():
        raise RuntimeError(f"Codex CLI 未找到：{CODEX}")
    prompt = codex_prompt(contract_path, run_dir, image_path)
    final_message = run_dir / "codex-last-message.md"
    emit("MODEL codex: 单次生成视觉规格与前端源码")
    # `--image=<path> -` plus stdin is the reliable Codex CLI form on Windows.
    # Putting a positional prompt immediately after `-i` makes the variadic
    # image option consume it, leaving Codex with no task.
    result = subprocess.run(
        [
            str(CODEX), "exec", "--ephemeral", "--dangerously-bypass-approvals-and-sandbox",
            "-C", str(ROOT), "-o", str(final_message), f"--image={image_path}", "-",
        ],
        cwd=ROOT,
        input=prompt,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=420,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Codex 生成失败")[-2400:])
    missing = [str(path) for path in required_paths(run_dir) if not path.is_file()]
    if missing:
        message = final_message.read_text(encoding="utf-8", errors="replace")[-1200:] if final_message.is_file() else ""
        raise RuntimeError("模型没有完成所需文件：" + ", ".join(missing) + (f"；模型回复：{message}" if message else ""))


def cccc_command() -> str | None:
    from shutil import which

    return which("cccc") or which("cccc.exe")


def send_cccc_task(run_id: str, title: str, text: str, key: str) -> None:
    command = cccc_command()
    if not command:
        raise RuntimeError("CCCC 命令不可用")
    result = call(
        command, "tracked-send", text, "--group", "g_c3e3880e9f6c", "--to", "mvp-worker",
        "--title", title, "--outcome", "Create the requested files before replying.",
        "--idempotency-key", key, timeout=30,
    )
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout or "无法向 CCCC Worker 下发任务")
    emit(f"CCCC task sent: {title}")


def wait_for(paths: list[Path], label: str, timeout: int = 180) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if all(path.is_file() and path.stat().st_size > 0 for path in paths):
            return
        time.sleep(2)
    missing = [str(path) for path in paths if not path.is_file() or path.stat().st_size == 0]
    raise RuntimeError(f"{label} 超时，缺少：" + ", ".join(missing))


def cccc_visual(contract_path: Path, run_dir: Path, source: Path, run_id: str) -> None:
    task = f"""Execute only the VISUAL phase for Screenshot-to-App run {run_id}.
Contract: {contract_path}
Reference screenshot: {source}
Immediately inspect the screenshot and create {run_dir / 'ui-spec.json'}.
The ui spec must include high_fidelity_structure (viewport rhythm, section order, geometry, dominant colour blocks, visible modal/drawer state and navigation placement) and replaced_source_assets (brand/logo/product photos/prices/source text replaced).
Do NOT create HTML/CSS/JS yet. Do NOT only acknowledge. Reply only after ui-spec.json exists."""
    send_cccc_task(run_id, f"VISUAL: {run_id}", task, f"pipeline-{run_id}-visual")
    wait_for([run_dir / "ui-spec.json"], "视觉理解")


def cccc_scaffold(contract_path: Path, run_dir: Path, source: Path, run_id: str) -> None:
    task = f"""Execute only the SCAFFOLD phase for Screenshot-to-App run {run_id}.
Contract: {contract_path}
Reference screenshot: {source}
Read {run_dir / 'ui-spec.json'} and create exactly:
{run_dir / 'app' / 'index.html'}
{run_dir / 'app' / 'styles.css'}
{run_dir / 'app' / 'app.js'}
Use high-fidelity screenshot structure: preserve layout rhythm, component geometry, dominant colour blocks, visible modal/drawer state and interaction entry points. Replace brand/logo/product photos/prices/source wording with fictional content and self-authored CSS/SVG assets. Implement every contract test id and real ?qa=1 functions. Do NOT run browser acceptance; the pipeline does it. Do NOT only acknowledge. Reply only after all three files exist."""
    send_cccc_task(run_id, f"SCAFFOLD: {run_id}", task, f"pipeline-{run_id}-scaffold")
    wait_for(required_paths(run_dir)[1:], "前端脚手架")


def model_settings() -> dict[str, Any]:
    config_path = ROOT / "config" / "local-model.local.json"
    from_file = read_json(config_path) if config_path.is_file() else {}
    return {
        "base_url": os.environ.get("LOCAL_MODEL_BASE_URL") or os.environ.get("LOCAL_LLM_BASE_URL") or from_file.get("base_url", ""),
        "api_key": os.environ.get("LOCAL_MODEL_API_KEY") or os.environ.get("LOCAL_LLM_API_KEY") or from_file.get("api_key", ""),
        "model": os.environ.get("LOCAL_MODEL_NAME") or os.environ.get("LOCAL_LLM_MODEL") or from_file.get("model", ""),
        "timeout": int(os.environ.get("LOCAL_MODEL_TIMEOUT") or from_file.get("timeout_seconds", 60)),
    }


def local_prompt(contract: dict[str, Any], ui_spec: dict[str, Any]) -> str:
    return f"""You are a screenshot-to-app code generator. Return exactly these four sections, in this order:
===UI_SPEC===
valid JSON
===INDEX_HTML===
complete HTML
===STYLES_CSS===
complete CSS
===APP_JS===
complete JavaScript

Contract:
{json.dumps(contract, ensure_ascii=False, indent=2)}

Visual specification from the screenshot-analysis step:
{json.dumps(ui_spec, ensure_ascii=False, indent=2)}

Closely reproduce layout structure, colour blocks, geometry, visible modal/drawer state and interaction entry points. Replace brand/logo/product photos/prices/source copy with fictional content and CSS/SVG illustrations. Include all required test IDs. Under ?qa=1, app.js must execute real filter/search and action functions before writing qa-result JSON. No markdown fences and no external network requests."""


def split_sections(text: str) -> dict[str, str]:
    markers = ["UI_SPEC", "INDEX_HTML", "STYLES_CSS", "APP_JS"]
    result: dict[str, str] = {}
    for index, marker in enumerate(markers):
        start_marker = f"==={marker}==="
        start = text.find(start_marker)
        if start < 0:
            raise RuntimeError(f"本地模型输出缺少 {start_marker}")
        start += len(start_marker)
        end = len(text)
        if index + 1 < len(markers):
            end_marker = f"==={markers[index + 1]}==="
            end = text.find(end_marker, start)
            if end < 0:
                raise RuntimeError(f"本地模型输出缺少 {end_marker}")
        result[marker] = text[start:end].strip()
    json.loads(result["UI_SPEC"])
    return result


def run_local_openai(contract: dict[str, Any], run_dir: Path) -> None:
    settings = model_settings()
    base_url = str(settings["base_url"]).rstrip("/")
    model = str(settings["model"])
    api_key = str(settings["api_key"])
    if not base_url or not model:
        raise RuntimeError("local-openai 需要配置 LOCAL_MODEL_BASE_URL 和 LOCAL_MODEL_NAME")
    ui_spec = load_contract(run_dir / "ui-spec.json")
    payload = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": 7000,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": [
            {"role": "system", "content": "You are a strict frontend code generator. Return only the requested four sections. Do not acknowledge, explain, or use markdown fences."},
            {"role": "user", "content": local_prompt(contract, ui_spec)},
        ],
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"} if api_key else {"Content-Type": "application/json"}, method="POST",
    )
    emit(f"MODEL local-openai: {model}")
    try:
        with urllib.request.urlopen(request, timeout=max(30, int(settings["timeout"]))) as response:
            response_json = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"本地模型服务不可用：{exc}") from exc
    content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
    sections = split_sections(content)
    (run_dir / "ui-spec.json").write_text(json.dumps(json.loads(sections["UI_SPEC"]), ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "app" / "index.html").write_text(sections["INDEX_HTML"], encoding="utf-8")
    (run_dir / "app" / "styles.css").write_text(sections["STYLES_CSS"], encoding="utf-8")
    (run_dir / "app" / "app.js").write_text(sections["APP_JS"], encoding="utf-8")


def commit_delivery(run_dir: Path, run_id: str) -> str | None:
    paths = [
        run_dir / "ui-spec.json", run_dir / "app", run_dir / "artifacts" / "preview.png",
        run_dir / "artifacts" / "acceptance-report.json", run_dir / "worker-delivery.json",
    ]
    add = call("git", "add", "-f", *[str(path) for path in paths], timeout=30)
    if add.returncode:
        emit("GIT skipped: " + (add.stderr or add.stdout).strip())
        return None
    commit = call("git", "-c", "user.name=MVP Worker", "-c", "user.email=mvp-worker@local", "commit", "-m", f"feat: deliver {run_id}", timeout=30)
    if commit.returncode:
        # No staged content is harmless for a retried pipeline.
        emit("GIT no new delivery commit: " + (commit.stderr or commit.stdout).strip()[-300:])
        return None
    return call("git", "rev-parse", "--short", "HEAD", timeout=15).stdout.strip() or None


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic Screenshot-to-App Worker pipeline.")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--batch", default="live-trials")
    parser.add_argument("--backend", choices=("template", "cccc-codex", "codex", "local-openai"), default=os.environ.get("MVP_WORKER_BACKEND", "template"))
    args = parser.parse_args()
    contract_path = Path(args.contract).resolve()
    contract = load_contract(contract_path)
    run_id = str(contract["run_id"])
    run_dir = run_dir_from(contract)
    source = Path(str(contract["source_screenshot"]["path"])).resolve()
    if not source.is_file() or not run_dir.is_dir():
        raise SystemExit("契约或已准备的 run 不存在")

    try:
        progress(args.batch, run_id, "visual", "STARTED", "generic-visual-start")
        if args.backend == "template":
            write_template_ui_spec(contract, run_dir)
        elif args.backend in {"cccc-codex", "local-openai"}:
            cccc_visual(contract_path, run_dir, source, run_id)
        elif args.backend == "codex":
            run_codex(contract_path, run_dir, source)
        else:
            run_local_openai(contract, run_dir)
        progress(args.batch, run_id, "visual", "PASS", "generic-visual-pass")
        progress(args.batch, run_id, "scaffold", "STARTED", "generic-scaffold-start")
        if args.backend == "template":
            write_template_app(contract, run_dir)
        elif args.backend == "cccc-codex":
            cccc_scaffold(contract_path, run_dir, source, run_id)
        missing = [str(path) for path in required_paths(run_dir) if not path.is_file()]
        if missing:
            raise RuntimeError("脚手架文件缺失：" + ", ".join(missing))
        progress(args.batch, run_id, "scaffold", "PASS", "generic-scaffold-pass")
        progress(args.batch, run_id, "browser", "STARTED", "generic-browser-start")
        acceptance = call(str(PYTHON), "scripts/browser_acceptance.py", "--run-dir", str(run_dir), timeout=60)
        if acceptance.returncode:
            raise RuntimeError((acceptance.stderr or acceptance.stdout or "浏览器验收失败")[-2400:])
        progress(args.batch, run_id, "browser", "PASS", "generic-browser-pass")
        progress(args.batch, run_id, "delivery", "STARTED", "generic-delivery-start")
        final = call(str(PYTHON), "scripts/finalize_delivery.py", "--run-dir", str(run_dir), timeout=30)
        if final.returncode:
            raise RuntimeError((final.stderr or final.stdout or "交付封装失败")[-2400:])
        delivery = load_contract(run_dir / "worker-delivery.json")
        if delivery.get("status") != "PASS":
            raise RuntimeError("worker-delivery.json 不是 PASS")
        commit = commit_delivery(run_dir, run_id)
        progress(args.batch, run_id, "delivery", "PASS", "generic-delivery-pass")
        emit(f"PASS {run_id}; git={commit or 'unchanged'}")
        return 0
    except Exception as exc:
        emit(f"FAIL {run_id}: {exc}")
        try:
            progress(args.batch, run_id, "delivery", "FAIL", "generic-delivery-fail")
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
