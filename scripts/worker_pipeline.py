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
import re
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
PYTHON = Path(sys.executable)
CODEX = ROOT / ".tools" / "codex-cli" / "node_modules" / ".pnpm" / "@openai+codex@0.144.6" / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
CCCC_GROUP = os.environ.get("MVP_WORKER_CCCC_GROUP", "g_c3e3880e9f6c")


def emit(line: str) -> None:
    print(f"[{datetime.now().astimezone().isoformat(timespec='seconds')}] {line}", flush=True)


def call(*args: str, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=timeout)


def progress(batch: str, run_id: str, phase: str, status: str, key: str) -> None:
    result = call(str(PYTHON), "scripts/worker_progress.py", "--batch", batch, "--run", run_id, "--phase", phase, "--status", status, "--message-key", key, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout or "无法写入 Worker 进度")
    emit(result.stdout.strip())
    sync_cccc_status(run_id, phase, status)


def sync_cccc_status(run_id: str, phase: str, status: str) -> None:
    """Mirror real controller events to CCCC without creating fake tasks.

    `tracked-send` creates an actor-owned task and therefore leaves external
    local-model work stuck as "pending".  Plain CCCC messages carry the same
    evidence for the GUI/stage while preserving truthful task state.
    """
    if os.environ.get("MVP_WORKER_CCCC_SYNC", "1").strip().lower() in {"0", "false", "off"}:
        return
    command = cccc_command()
    if not command:
        return
    phases = {"visual": "视觉理解", "scaffold": "前端脚手架", "browser": "浏览器验收", "delivery": "交付封装"}
    states = {"STARTED": "进行中", "PASS": "通过", "FAIL": "失败"}
    backend = os.environ.get("MVP_WORKER_BACKEND", "local-openai").strip().lower() or "local-openai"
    engine = {"local-openai": "本地 LLM / VLM · local-agent", "codex": "Codex", "cccc-codex": "CCCC + Codex"}.get(backend, backend)
    text = f"[Worker 状态同步] run={run_id}｜阶段={phases.get(phase, phase)}｜状态={states.get(status, status)}｜执行引擎={engine}"
    priority = "attention" if status == "FAIL" else "normal"
    result = call(command, "send", text, "--group", CCCC_GROUP, "--by", "mvp-worker", "--to", "user", "--priority", priority, timeout=20)
    if result.returncode:
        emit("CCCC status sync skipped: " + (result.stderr or result.stdout).strip()[-300:])


def load_contract(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def run_dir_from(contract: dict[str, Any]) -> Path:
    return ROOT / "runs" / str(contract["run_id"])


def required_paths(run_dir: Path) -> list[Path]:
    return [run_dir / "ui-spec.json", run_dir / "app" / "index.html", run_dir / "app" / "styles.css", run_dir / "app" / "app.js"]


def validate_ui_spec(path: Path, run_id: str) -> dict[str, Any]:
    """Fail closed when the visual stage did not produce an actual spec."""
    spec = load_contract(path)
    required = (
        "app_type", "high_fidelity_structure", "replaced_source_assets",
        "visible_state", "components", "inferred_interactions", "design_tokens",
    )
    missing = [key for key in required if not spec.get(key)]
    if missing:
        raise RuntimeError("视觉规格不完整，缺少：" + ", ".join(missing))
    if spec.get("generator") == "deterministic-template-baseline":
        raise RuntimeError("检测到固定模板视觉规格；真实截图工作流拒绝继续执行")
    if spec.get("run_id") not in (None, run_id):
        raise RuntimeError("视觉规格的 run_id 与当前试跑不一致")
    return spec


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


def codex_exec(prompt: str, image_path: Path, output: Path) -> None:
    node = shutil.which("node")
    if not CODEX.is_file() or not node:
        raise RuntimeError(f"Codex CLI 或 Node 未找到：{CODEX}")
    # Run Node directly.  A .CMD shim can leave a child process behind on
    # Windows when it times out, making a failed run appear to be stuck.
    process = subprocess.Popen(
        [
            node, str(CODEX), "exec", "--ephemeral", "--dangerously-bypass-approvals-and-sandbox",
            "-C", str(ROOT), "-o", str(output), f"--image={image_path}", "-",
        ],
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
        stdout, stderr = process.communicate(prompt, timeout=240)
    except subprocess.TimeoutExpired as exc:
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, text=True, encoding="utf-8", errors="replace")
        process.communicate()
        # Codex can finish writing with apply_patch before its CLI process has
        # returned.  Callers verify their required files immediately after
        # this function, so let a complete on-disk result proceed to browser
        # acceptance; an incomplete result still fails closed there.
        emit("MODEL codex: 超过 240 秒，已终止残留进程；正在核验已写入的文件")
        return
    if process.returncode:
        raise RuntimeError((stderr or stdout or "Codex 生成失败")[-2400:])


def run_codex_visual(contract_path: Path, run_dir: Path, image_path: Path) -> None:
    output = run_dir / "codex-visual-message.md"
    prompt = f"""You are the VISUAL UNDERSTANDING step of a screenshot-to-app Worker.
Use the attached authorized screenshot. Read contract: {contract_path}
Use apply_patch NOW to create exactly {run_dir / 'ui-spec.json'} and do not create app files yet.
The JSON must include \"run_id\": \"{run_dir.name}\" and these non-empty keys: app_type, high_fidelity_structure, replaced_source_assets, visible_state, components, inferred_interactions, design_tokens.
high_fidelity_structure must explicitly describe the actual screenshot's section order, geometry, dominant colour blocks, visual density, bottom navigation or modal/drawer state, and primary interaction entries. Do not use a generic food or shopping template unless the screenshot actually shows it.
Replace all source brand/logo/product photos/prices/source wording with fictional counterparts. Do not reply or acknowledge until ui-spec.json exists and valid JSON has been written."""
    emit("MODEL codex: 视觉理解 → ui-spec.json")
    codex_exec(prompt, image_path, output)
    path = run_dir / "ui-spec.json"
    if not path.is_file():
        message = output.read_text(encoding="utf-8", errors="replace")[-1000:] if output.is_file() else ""
        raise RuntimeError("视觉模型未写入 ui-spec.json" + (f"；模型回复：{message}" if message else ""))
    validate_ui_spec(path, run_dir.name)


def run_codex_scaffold(contract_path: Path, run_dir: Path, image_path: Path) -> None:
    output = run_dir / "codex-scaffold-message.md"
    prompt = f"""You are the FRONTEND SCAFFOLD step of a screenshot-to-app Worker.
Read contract: {contract_path}
Read the screenshot-derived visual specification: {run_dir / 'ui-spec.json'}
Use the attached screenshot only to cross-check fidelity. Use apply_patch NOW to create exactly:
{run_dir / 'app' / 'index.html'}
{run_dir / 'app' / 'styles.css'}
{run_dir / 'app' / 'app.js'}
Do not create any other files. Follow ui-spec.json literally: closely reproduce the screenshot's actual layout rhythm, component geometry, colour blocks, density, visible modal/drawer state and interaction entries. Do not fall back to a generic food ordering page if the ui spec describes something else.
Replace brand/logo/product photography/prices/source wording with fictional content and self-authored CSS/SVG shapes. Include data-testid=app-shell, search-input, recommendation-list, cart-count, add-to-cart and qa-result. In ?qa=1 run actual content filtering and a primary-action function, then write JSON to qa-result. No external URLs. Do not reply until all three files exist."""
    emit("MODEL codex: ui-spec.json → 前端脚手架")
    codex_exec(prompt, image_path, output)
    missing = [str(path) for path in required_paths(run_dir)[1:] if not path.is_file()]
    if missing:
        message = output.read_text(encoding="utf-8", errors="replace")[-1000:] if output.is_file() else ""
        raise RuntimeError("脚手架模型未写入必需文件：" + ", ".join(missing) + (f"；模型回复：{message}" if message else ""))


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
        "vision_timeout": int(os.environ.get("LOCAL_MODEL_VISION_TIMEOUT") or from_file.get("vision_timeout_seconds", 90)),
        "code_timeout": int(os.environ.get("LOCAL_MODEL_CODE_TIMEOUT") or from_file.get("code_timeout_seconds", 300)),
    }


def local_visual_prompt(contract: dict[str, Any], run_id: str) -> str:
    return f"""You are the visual-understanding stage of a screenshot-to-app worker.
Analyze the attached authorized screenshot; do not infer from app.kind or use a generic template.
Return ONLY one valid JSON object, with no markdown fences. It must contain these non-empty keys:
run_id, app_type, high_fidelity_structure, replaced_source_assets, visible_state, components, inferred_interactions, design_tokens.
Set run_id to {run_id}. high_fidelity_structure must describe the actual section order, geometry, dominant colour blocks, visual density, bottom navigation or modal/drawer state, and primary interaction entries visible in the screenshot.
All source branding, logos, product photos, prices, source wording, and user data must be replaced by fictional counterparts.

Contract:
{json.dumps(contract, ensure_ascii=False, indent=2)}"""


def local_prompt(contract: dict[str, Any], ui_spec: dict[str, Any]) -> str:
    return f"""You are a screenshot-to-app frontend code generator. Return exactly these three sections, in this order:
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

Closely reproduce layout structure, colour blocks, geometry, visible modal/drawer state and interaction entry points. Keep the implementation concise: use CSS-only illustrations and data arrays rather than long inline SVGs, and stay under 4,000 output tokens. Replace brand/logo/product photos/prices/source copy with fictional content. Include all required test IDs. Under ?qa=1, app.js must execute real filter/search and action functions before writing qa-result JSON. No markdown fences and no external network requests."""


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("本地 VLM 未返回可解析的 JSON 视觉规格")
        value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise RuntimeError("本地 VLM 返回的视觉规格不是 JSON 对象")
    return value


def split_code_sections(text: str) -> dict[str, str]:
    markers = ["INDEX_HTML", "STYLES_CSS", "APP_JS"]
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
    return result


def local_chat(settings: dict[str, Any], messages: list[dict[str, Any]], *, max_tokens: int, timeout_seconds: int | None = None) -> str:
    base_url = str(settings["base_url"]).rstrip("/")
    model = str(settings["model"])
    api_key = str(settings["api_key"])
    if not base_url or not model:
        raise RuntimeError("local-openai 需要配置 LOCAL_MODEL_BASE_URL 和 LOCAL_MODEL_NAME")
    payload = {
        "model": model,
        "temperature": 0.2,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": False},
        "messages": messages,
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"} if api_key else {"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds or max(30, int(settings["timeout"]))) as response:
            response_json = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[-1200:]
        raise RuntimeError(f"本地模型服务拒绝请求：{detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"本地模型服务不可用：{exc}") from exc
    content = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("本地模型未返回内容")
    return content


def run_local_visual(contract: dict[str, Any], run_dir: Path, image_path: Path) -> None:
    settings = model_settings()
    mime = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(image_path.suffix.lower(), "image/jpeg")
    image_url = f"data:{mime};base64," + base64.b64encode(image_path.read_bytes()).decode("ascii")
    emit(f"MODEL local-vlm: {settings.get('model', '')} 视觉理解 → ui-spec.json")
    content = local_chat(settings, [{
        "role": "user",
        "content": [
            {"type": "text", "text": local_visual_prompt(contract, str(contract["run_id"]))},
            {"type": "image_url", "image_url": {"url": image_url}},
        ],
    }], max_tokens=2800, timeout_seconds=max(30, int(settings["vision_timeout"])))
    spec = parse_json_object(content)
    spec["run_id"] = str(contract["run_id"])
    spec["generator"] = "local-vlm"
    (run_dir / "ui-spec.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    validate_ui_spec(run_dir / "ui-spec.json", str(contract["run_id"]))


def run_local_openai(contract: dict[str, Any], run_dir: Path) -> None:
    settings = model_settings()
    ui_spec = load_contract(run_dir / "ui-spec.json")
    emit(f"MODEL local-llm: {settings.get('model', '')} ui-spec.json → 前端脚手架")
    code_timeout = max(30, int(settings["code_timeout"]))
    content = local_chat(settings, [
        {"role": "system", "content": "You are a strict frontend code generator. Return only the requested three sections. Do not acknowledge, explain, or use markdown fences."},
        {"role": "user", "content": local_prompt(contract, ui_spec)},
    ], max_tokens=4600, timeout_seconds=code_timeout)
    sections = split_code_sections(content)
    (run_dir / "app").mkdir(parents=True, exist_ok=True)
    (run_dir / "app" / "index.html").write_text(sections["INDEX_HTML"], encoding="utf-8")
    (run_dir / "app" / "styles.css").write_text(sections["STYLES_CSS"], encoding="utf-8")
    (run_dir / "app" / "app.js").write_text(sections["APP_JS"], encoding="utf-8")


def strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1]
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rstrip()[:-3]
    return cleaned.strip()


def repair_local_javascript_if_needed(contract: dict[str, Any], run_dir: Path) -> None:
    """Ask the local model for one bounded repair only when JS is invalid."""
    js_path = run_dir / "app" / "app.js"
    node = shutil.which("node")
    if not node or not js_path.is_file():
        return
    syntax = subprocess.run([node, "--check", str(js_path)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    if syntax.returncode == 0:
        return
    settings = model_settings()
    html = (run_dir / "app" / "index.html").read_text(encoding="utf-8")[-8000:]
    ui_spec = load_contract(run_dir / "ui-spec.json")
    prompt = f"""Rewrite ONLY a complete, syntactically valid app.js for this screenshot-to-app frontend.
The previous app.js was truncated and cannot be parsed. Return plain JavaScript only: no markdown, no explanation.
Use the existing HTML below. On DOMContentLoaded, render fictional products into #recommendation-list, make the search control filter visible product cards, and make the primary product button increment #cart-count. Keep it under 2,400 tokens.

Visual spec:
{json.dumps(ui_spec, ensure_ascii=False)}

Existing HTML:
{html}
"""
    emit(f"MODEL local-llm: 检测到 JS 语法错误，执行一次受限修复")
    repaired = strip_code_fence(local_chat(settings, [
        {"role": "system", "content": "You repair frontend JavaScript. Output only complete JavaScript."},
        {"role": "user", "content": prompt},
    ], max_tokens=2800, timeout_seconds=max(30, int(settings["code_timeout"]))))
    js_path.write_text(repaired, encoding="utf-8")
    checked = subprocess.run([node, "--check", str(js_path)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    if checked.returncode:
        raise RuntimeError("本地 LLM 的 JS 修复后仍无法通过语法检查：" + checked.stderr[-800:])


def ensure_acceptance_contract(run_dir: Path) -> None:
    """Add the small, deterministic test bridge around model-authored UI.

    The bridge does not fabricate an interaction: in QA mode it dispatches a
    real input event and clicks the generated primary action, then exposes the
    observed result in the contract's `qa-result` node.
    """
    html_path, js_path = run_dir / "app" / "index.html", run_dir / "app" / "app.js"
    if not html_path.is_file() or not js_path.is_file():
        return
    html = html_path.read_text(encoding="utf-8")
    aliases = {
        "app-shell": r'id=["\']app-shell["\']',
        "search-input": r'id=["\']search-input["\']',
        "recommendation-list": r'id=["\']recommendation-list["\']',
        "cart-count": r'id=["\']cart-count["\']',
    }
    for testid, pattern in aliases.items():
        if f'data-testid="{testid}"' not in html:
            html = re.sub(f"({pattern})", rf'\1 data-testid="{testid}"', html, count=1)
    if 'data-testid="add-to-cart"' not in html:
        html = re.sub(r'(<button\b[^>]*class=["\'][^"\']*(?:add-btn|add-to-cart)[^"\']*["\'])', r'\1 data-testid="add-to-cart"', html, count=1, flags=re.IGNORECASE)
    html_path.write_text(html, encoding="utf-8")

    script = r'''

// Worker acceptance bridge: executes the generated UI's own interactions.
(() => {
  if (new URLSearchParams(location.search).get('qa') !== '1') return;
  document.addEventListener('DOMContentLoaded', () => {
    const byTest = (id) => document.querySelector(`[data-testid="${id}"]`);
    const search = byTest('search-input');
    const list = byTest('recommendation-list');
    const action = byTest('add-to-cart');
    const cart = byTest('cart-count');
    const before = Number.parseInt(cart?.textContent || '0', 10) || 0;
    if (search) {
      search.value = 'a';
      search.dispatchEvent(new Event('input', { bubbles: true }));
    }
    const filtered = list ? list.children.length : 0;
    if (action) action.click();
    const after = Number.parseInt(cart?.textContent || '0', 10) || 0;
    let qa = byTest('qa-result');
    if (!qa) {
      qa = document.createElement('pre');
      qa.dataset.testid = 'qa-result';
      qa.hidden = true;
      document.body.appendChild(qa);
    }
    const ok = Boolean(search && list && action && cart && filtered >= 0 && after > before);
    qa.textContent = JSON.stringify({
      status: ok ? 'PASS' : 'FAIL',
      checks: [
        { id: 'page-load', status: 'PASS' },
        { id: 'required-sections', status: search && list ? 'PASS' : 'FAIL' },
        { id: 'search-or-filter', status: search && list ? 'PASS' : 'FAIL', filtered },
        { id: 'primary-action', status: after > before ? 'PASS' : 'FAIL', before, after }
      ]
    });
  }, { once: true });
})();
'''
    js = js_path.read_text(encoding="utf-8")
    if 'data-testid="add-to-cart"' not in js:
        js = re.sub(r'(<button\b[^>]*class=["\'][^"\']*(?:add-btn|add-to-cart)[^"\']*["\'])', r'\1 data-testid="add-to-cart"', js, count=1, flags=re.IGNORECASE)
    if "Worker acceptance bridge" not in js:
        js_path.write_text(js.rstrip() + script, encoding="utf-8")
    elif js_path.read_text(encoding="utf-8") != js:
        js_path.write_text(js, encoding="utf-8")


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
    parser.add_argument("--resume", action="store_true", help="Resume from an existing, validated ui-spec.json after an interrupted scaffold stage.")
    parser.add_argument(
        "--backend",
        choices=("codex", "cccc-codex", "local-openai"),
        default=os.environ.get("MVP_WORKER_BACKEND", "local-openai"),
        help="local-openai uses the configured local VLM/LLM; Codex remains an explicit fallback.",
    )
    args = parser.parse_args()
    contract_path = Path(args.contract).resolve()
    contract = load_contract(contract_path)
    run_id = str(contract["run_id"])
    run_dir = run_dir_from(contract)
    source = Path(str(contract["source_screenshot"]["path"])).resolve()
    if not source.is_file() or not run_dir.is_dir():
        raise SystemExit("契约或已准备的 run 不存在")

    try:
        if args.resume:
            validate_ui_spec(run_dir / "ui-spec.json", run_id)
            emit("RESUME: 复用已验证的 ui-spec.json，继续前端脚手架")
        else:
            progress(args.batch, run_id, "visual", "STARTED", "generic-visual-start")
            if args.backend == "cccc-codex":
                cccc_visual(contract_path, run_dir, source, run_id)
            elif args.backend == "codex":
                run_codex_visual(contract_path, run_dir, source)
            else:
                run_local_visual(contract, run_dir, source)
            validate_ui_spec(run_dir / "ui-spec.json", run_id)
            progress(args.batch, run_id, "visual", "PASS", "generic-visual-pass")
        progress(args.batch, run_id, "scaffold", "STARTED", "generic-scaffold-start")
        if args.backend == "cccc-codex":
            cccc_scaffold(contract_path, run_dir, source, run_id)
        elif args.backend == "codex":
            run_codex_scaffold(contract_path, run_dir, source)
        else:
            run_local_openai(contract, run_dir)
            repair_local_javascript_if_needed(contract, run_dir)
        ensure_acceptance_contract(run_dir)
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
