from __future__ import annotations

import cgi
import html
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import uuid
from datetime import datetime
from http import HTTPStatus
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "scripts" / "python.cmd"
MAX_UPLOAD_BYTES = 16 * 1024 * 1024
ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
DEFAULT_GROUP = "g_c3e3880e9f6c"


PAGE = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Worker 投递台 · 截图生成 MVP</title>
  <style>
    :root{--ink:#182721;--paper:#f6f2eb;--cream:#fffdfa;--lime:#c9f64a;--orange:#ff633a;--line:#d7d0c7;--muted:#69736e;--mono:ui-monospace,SFMono-Regular,Consolas,monospace;--sans:"Microsoft YaHei","PingFang SC",sans-serif}
    *{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans)}button,input{font:inherit}button{cursor:pointer}.grain{position:fixed;inset:0;z-index:-1;opacity:.12;background-image:radial-gradient(#182721 0.65px,transparent .7px);background-size:7px 7px;pointer-events:none}.wrap{max-width:1120px;margin:auto;padding:28px 28px 60px}.top{display:flex;align-items:center;justify-content:space-between;padding-bottom:25px;border-bottom:1px solid var(--line)}.brand{display:flex;align-items:center;gap:10px;font-weight:900;font-size:18px;letter-spacing:-.6px}.brand i{display:grid;place-items:center;width:30px;height:30px;color:var(--ink);background:var(--lime);font-style:normal;font:700 15px var(--mono);transform:rotate(-8deg);box-shadow:3px 3px 0 var(--ink)}.state{display:flex;align-items:center;gap:7px;color:var(--muted);font:11px var(--mono)}.state b{width:8px;height:8px;border-radius:50%;background:#a0a7a4}.state.ready b{background:#78af21;box-shadow:0 0 0 4px #dbe9c8}.access{display:flex;gap:7px;margin-left:auto;margin-right:18px}.access a,.show-link{border-bottom:1px solid var(--orange);color:var(--ink);text-decoration:none;font:11px var(--mono);padding-bottom:3px}.eyebrow{margin:52px 0 11px;color:#547242;font:11px var(--mono);letter-spacing:.7px}.intro{display:grid;grid-template-columns:minmax(0,1fr) 300px;gap:40px;align-items:end}.intro h1{max-width:700px;margin:0;font-size:clamp(38px,6vw,67px);line-height:1.03;letter-spacing:-3px}.intro h1 em{font-style:normal;color:var(--orange)}.intro p{margin:0;color:var(--muted);font-size:14px;line-height:1.8}.desk{display:grid;grid-template-columns:1.25fr .75fr;gap:18px;margin-top:42px}.card{background:var(--cream);border:1px solid var(--line);box-shadow:7px 7px 0 #dcd5cd}.intake{padding:22px}.card-title{display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}.card-title h2{margin:0;font-size:16px}.card-title span{color:var(--muted);font:10px var(--mono)}.drop{position:relative;display:grid;place-items:center;min-height:255px;border:2px dashed #a9b2a9;background:#eff3ea;transition:.2s;overflow:hidden}.drop.drag{border-color:var(--orange);background:#fff0e8}.drop.has-file{border-style:solid;border-color:var(--ink);background:#111f19}.drop input{position:absolute;inset:0;opacity:0;cursor:pointer}.drop-main{text-align:center;pointer-events:none}.drop-mark{position:relative;width:68px;height:68px;margin:0 auto 15px;border:1px solid var(--ink);background:var(--lime);box-shadow:5px 5px 0 var(--ink)}.drop-mark:before,.drop-mark:after{content:"";position:absolute;background:var(--ink)}.drop-mark:before{width:28px;height:2px;left:19px;top:33px}.drop-mark:after{width:2px;height:28px;top:20px;left:32px}.drop h3{margin:0;font-size:18px}.drop p{margin:8px 0 0;color:var(--muted);font-size:12px}.file-preview{display:none;align-items:center;gap:15px;width:100%;height:100%;padding:18px;color:#f8f7f0}.has-file .drop-main{display:none}.has-file .file-preview{display:flex}.file-preview img{width:118px;height:190px;object-fit:cover;border:2px solid var(--lime)}.file-preview b{display:block;font-size:15px;word-break:break-all}.file-preview small{display:block;margin-top:7px;color:#b7c3b9;font:10px var(--mono)}.form-row{display:grid;grid-template-columns:1fr 150px;gap:12px;margin-top:18px}.field label{display:block;margin-bottom:7px;font-size:12px;font-weight:800}.field input{width:100%;border:1px solid var(--line);border-radius:0;padding:11px;background:#fff;color:var(--ink);outline-color:var(--orange)}.dispatch{display:flex;align-items:center;gap:9px;margin:19px 0;color:#45534b;font-size:12px}.dispatch input{accent-color:var(--orange);width:15px;height:15px}.submit{width:100%;display:flex;align-items:center;justify-content:space-between;border:0;background:var(--ink);color:#fff;padding:14px 16px;font-size:13px;font-weight:800}.submit span{color:var(--lime);font:18px var(--mono)}.submit:disabled{opacity:.55;cursor:wait}.rail{padding:21px 20px}.flow{margin:17px 0 24px;padding:0;list-style:none}.flow li{display:grid;grid-template-columns:26px 1fr;gap:10px;position:relative;padding-bottom:17px;font-size:12px}.flow li:not(:last-child):before{content:"";position:absolute;left:10px;top:24px;height:22px;border-left:1px dashed #aeb7b0}.flow b{display:grid;place-items:center;width:21px;height:21px;border-radius:50%;background:#e5e8e2;font:10px var(--mono)}.flow strong{display:block;margin-bottom:3px}.flow small{color:var(--muted);line-height:1.45}.note{border-top:1px solid var(--line);padding-top:16px;color:var(--muted);font-size:11px;line-height:1.65}.note b{color:var(--ink)}.evidence{margin-top:18px;padding:21px}.evidence-head{display:flex;align-items:center;justify-content:space-between}.evidence h2{margin:0;font-size:16px}.evidence button{border:1px solid var(--line);background:#fff;padding:6px 8px;color:var(--ink);font-size:11px}.empty{padding:30px 0 9px;color:var(--muted);font-size:13px;text-align:center}.run{display:grid;grid-template-columns:1.5fr .7fr .7fr auto;gap:10px;align-items:center;border-top:1px solid var(--line);padding:13px 0;font-size:12px}.run b{font:700 11px var(--mono)}.run small{color:var(--muted);font:10px var(--mono)}.pill{width:max-content;padding:4px 6px;background:#eceeea;color:#56615b;font:10px var(--mono)}.pill.pass{background:#e5f7b8;color:#365900}.pill.working{background:#ffe6d2;color:#a53d14}.links{display:flex;gap:5px;flex-wrap:wrap}.links a{padding:5px 7px;background:var(--ink);color:#fff;text-decoration:none;font:10px var(--mono)}.links a.live{background:#39704f}.toast{position:fixed;right:22px;bottom:22px;max-width:360px;padding:12px 14px;background:var(--ink);color:#fff;box-shadow:5px 5px 0 var(--orange);font-size:12px;transform:translateY(130%);transition:.25s}.toast.show{transform:translateY(0)}.statusline{display:none;margin-top:15px;padding:9px 10px;background:#e9f7c8;color:#365900;font:11px var(--mono)}.statusline.error{background:#ffe5dc;color:#9a351a}@media(max-width:760px){.wrap{padding:20px 16px}.intro,.desk{grid-template-columns:1fr}.intro{gap:18px}.intro h1{letter-spacing:-2px}.eyebrow{margin-top:35px}.form-row{grid-template-columns:1fr}.run{grid-template-columns:1fr 1fr}.links{grid-column:1/-1}.top{align-items:flex-start}.state{margin-top:6px}.access{margin-left:0;margin-right:0;flex-wrap:wrap}}
  </style>
</head>
<body><div class="grain"></div><main class="wrap">
  <header class="top"><div class="brand"><i>⇣</i>截图生成 MVP · Worker 投递台</div><nav class="access"><a href="/apps/screenshot-to-app-recording-001-malllite/index.html" target="_blank">运行网页 ↗</a><a href="http://127.0.0.1:8848/ui/" target="_blank">CCCC GUI ↗</a><a href="/repo" target="_blank">仓库状态 ↗</a><a href="/show">运行舞台 →</a></nav><div class="state" id="actor-state"><b></b><span>正在检查 CCCC Worker</span></div></header>
  <p class="eyebrow">UPLOAD → CONTRACT → WORKER → BROWSER QA</p>
  <section class="intro"><h1>不用终端路径。<br><em>把截图放在这里。</em></h1><p>这是 Worker 的输入台：选择或直接拖入一张授权截图，系统会创建独立契约并把任务交给 CCCC。输出始终保留在本地 run 目录中。</p></section>
  <section class="desk"><form class="card intake" id="intake-form"><div class="card-title"><h2>投递一张参考截图</h2><span>JPG · PNG · WEBP / 最大 16 MB</span></div><label class="drop" id="drop-zone"><input id="screenshot" name="screenshot" type="file" accept="image/jpeg,image/png,image/webp" required><div class="drop-main"><div class="drop-mark"></div><h3>拖放截图，或点击选择</h3><p>图片只用于理解布局与交互意图</p></div><div class="file-preview"><img id="preview" alt="待投递截图预览"><div><b id="file-name"></b><small id="file-meta"></small><small>已就绪，可创建 Worker 契约</small></div></div></label><div class="form-row"><div class="field"><label for="app-name">虚构应用名称</label><input id="app-name" name="app_name" maxlength="32" value="SparkMVP" required></div><div class="field"><label for="kind">页面类型</label><input id="kind" name="kind" maxlength="32" value="mobile app" required></div></div><label class="dispatch"><input id="dispatch" name="dispatch" type="checkbox" checked>创建契约后立即发送到 CCCC 的 <b>mvp-worker</b></label><button class="submit" id="submit" type="submit">创建本次试跑 <span>→</span></button><div class="statusline" id="statusline"></div></form>
  <aside class="card rail"><div class="card-title"><h2>这次试跑会发生什么</h2><span>本地执行</span></div><ol class="flow"><li><b>1</b><div><strong>保存截图</strong><small>复制到独立 run；不覆盖任何已完成样例。</small></div></li><li><b>2</b><div><strong>生成 MVP 契约</strong><small>包含应用名、验收规则和交付清单。</small></div></li><li><b>3</b><div><strong>派发给 CCCC Worker</strong><small>Worker 在终端输出中文阶段日志。</small></div></li><li><b>4</b><div><strong>浏览器自动验收</strong><small>交付源码、PNG 预览、JSON 报告与回执。</small></div></li></ol><p class="note"><b>安全边界：</b>参考图只用于布局与交互理解。Worker 必须产生虚构品牌与自制素材，不能复用 Logo、商品图或品牌文案。</p></aside></section>
  <section class="card evidence"><div class="evidence-head"><h2>最近试跑与可视化证据</h2><button type="button" id="refresh">刷新</button></div><div id="runs"><p class="empty">正在读取本地 run…</p></div></section>
</main><div class="toast" id="toast"></div>
<script>
const $=s=>document.querySelector(s);const zone=$('#drop-zone'),input=$('#screenshot'),preview=$('#preview'),toast=$('#toast');
function say(message,error=false){const el=$('#statusline');el.textContent=message;el.className='statusline'+(error?' error':'');el.style.display='block';toast.textContent=message;toast.classList.add('show');setTimeout(()=>toast.classList.remove('show'),3600)}
function renderFile(file){if(!file)return;$('#file-name').textContent=file.name;$('#file-meta').textContent=`${Math.ceil(file.size/1024)} KB · ${file.type||'image'}`;preview.src=URL.createObjectURL(file);zone.classList.add('has-file')}
input.addEventListener('change',()=>renderFile(input.files[0]));['dragenter','dragover'].forEach(type=>zone.addEventListener(type,e=>{e.preventDefault();zone.classList.add('drag')}));['dragleave','drop'].forEach(type=>zone.addEventListener(type,e=>{e.preventDefault();zone.classList.remove('drag')}));zone.addEventListener('drop',e=>{const file=e.dataTransfer.files[0];if(!file)return;const dt=new DataTransfer();dt.items.add(file);input.files=dt.files;renderFile(file)});
async function refresh(){try{const data=await fetch('/api/runs').then(r=>r.json());const actor=$('#actor-state');actor.className='state '+(data.actor.running?'ready':'');actor.innerHTML=`<b></b><span>${data.actor.running?'CCCC Worker 已运行':'CCCC Worker 当前停止；投递时会自动启动'}</span>`;const host=$('#runs');if(!data.runs.length){host.innerHTML='<p class="empty">还没有新的试跑。投递一张截图后，证据会出现在这里。</p>';return}host.innerHTML=data.runs.map(run=>`<article class="run"><div><b>${run.run_id}</b><small>${run.created_at||'已创建，等待 Worker'}</small></div><span class="pill ${run.status==='PASS'?'pass':run.status==='处理中'?'working':''}">${run.status}</span><span class="pill ${run.dispatched?'working':''}">${run.dispatched?'已派发':'仅已准备'}</span><div class="links">${run.app_url?`<a class="live" target="_blank" href="${run.app_url}">运行网页</a>`:''}${run.pipeline_log?`<a target="_blank" href="${run.pipeline_log}">流水线日志</a>`:''}${run.preview?`<a target="_blank" href="${run.preview}">预览图</a>`:''}${run.report?`<a target="_blank" href="${run.report}">验收</a>`:''}${run.delivery?`<a target="_blank" href="${run.delivery}">回执</a>`:''}<a target="_blank" href="http://127.0.0.1:8848/ui/">CCCC</a><a target="_blank" href="/repo">仓库</a></div></article>`).join('')}catch(e){$('#runs').innerHTML='<p class="empty">无法读取本地状态，请确认投递台仍在运行。</p>'}}
$('#refresh').addEventListener('click',refresh);setInterval(refresh,5000);refresh();
$('#intake-form').addEventListener('submit',async e=>{e.preventDefault();if(!input.files[0])return say('请先选择一张截图。',true);const btn=$('#submit');btn.disabled=true;btn.innerHTML='正在创建… <span>⋯</span>';try{const fd=new FormData(e.currentTarget);fd.set('dispatch',$('#dispatch').checked?'true':'false');const result=await fetch('/api/intake',{method:'POST',body:fd}).then(async r=>{const json=await r.json();if(!r.ok)throw new Error(json.error||'创建失败');return json});say(result.message);await refresh();if(result.show_url)window.location.assign(result.show_url)}catch(err){say(err.message,true)}finally{btn.disabled=false;btn.innerHTML='创建本次试跑 <span>→</span>'}});
</script></body></html>"""


def json_response(handler: SimpleHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def send_static_file(handler: SimpleHTTPRequestHandler, path: Path) -> None:
    """Send one explicitly approved static file without exposing the workspace."""
    if not path.is_file():
        handler.send_error(HTTPStatus.NOT_FOUND)
        return
    content_type, _ = mimetypes.guess_type(str(path))
    body = path.read_bytes()
    handler.send_response(HTTPStatus.OK)
    handler.send_header("Content-Type", content_type or "application/octet-stream")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def safe_name(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^\w\-\u4e00-\u9fff ]", "", value, flags=re.UNICODE).strip()
    return cleaned[:32] or fallback


def cccc_command() -> str | None:
    return shutil.which("cccc") or shutil.which("cccc.exe")


def git_output(*args: str) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def repository_info() -> dict[str, str | None]:
    remote = git_output("remote", "get-url", "origin")
    return {
        "commit": git_output("rev-parse", "--short", "HEAD") or None,
        "subject": git_output("log", "-1", "--pretty=%s") or None,
        "remote": remote or None,
        "github_url": remote if remote.startswith(("https://github.com/", "http://github.com/")) else None,
    }


def repository_page() -> bytes:
    info = repository_info()
    commit = html.escape(info["commit"] or "无提交")
    subject = html.escape(info["subject"] or "本地仓库尚未初始化")
    remote = info["remote"]
    remote_view = f'<a href="{html.escape(remote, quote=True)}" target="_blank">{html.escape(remote)}</a>' if remote and remote.startswith("http") else "未配置远程 GitHub 仓库"
    body = f"""<!doctype html><html lang=\"zh-CN\"><meta charset=\"utf-8\"><title>Worker 仓库状态</title>
    <style>body{{margin:0;background:#f6f2eb;color:#182721;font-family:\"Microsoft YaHei\",sans-serif}}main{{max-width:760px;margin:70px auto;padding:28px;background:#fffdfa;border:1px solid #d7d0c7;box-shadow:8px 8px #dcd5cd}}small{{font-family:Consolas,monospace;color:#69736e}}h1{{margin:8px 0 30px}}dl{{display:grid;grid-template-columns:140px 1fr;gap:14px;border-top:1px solid #d7d0c7;padding-top:20px}}dt{{font-size:12px;color:#69736e}}dd{{margin:0;word-break:break-all}}a{{color:#182721;text-decoration-color:#ff633a}}.note{{margin-top:28px;padding:14px;background:#eff3ea;font-size:13px;line-height:1.7}}</style>
    <main><small>LOCAL GIT REPOSITORY / DELIVERY EVIDENCE</small><h1>Worker 仓库状态</h1><dl><dt>最新提交</dt><dd><code>{commit}</code> · {subject}</dd><dt>远程仓库</dt><dd>{remote_view}</dd><dt>GitHub 交付</dt><dd>{'已连接，可在 Worker 契约允许时推送。' if info['github_url'] else '未配置。为了不创建意外的公开仓库，当前 Worker 只创建本地 Git 提交。'}</dd></dl><p class=\"note\">录制可展示这个页面作为“源码已提交”的证据。若要真正显示 GitHub 链接，请先配置团队的 GitHub remote；Worker 不会自行创建或公开推送仓库。</p></main></html>"""
    return body.encode("utf-8")


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def worker_events(run_id: str) -> list[dict[str, Any]]:
    """Read the append-only Worker feed and retain only one trial's events."""
    events: list[dict[str, Any]] = []
    for path in (ROOT / "runs").glob("*/worker-progress.jsonl"):
        try:
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                event = json.loads(line)
                if event.get("run_id") == run_id:
                    events.append(event)
        except (OSError, json.JSONDecodeError):
            continue
    return sorted(events, key=lambda event: str(event.get("timestamp", "")))[-32:]


def runtime_info() -> dict[str, Any]:
    """State only what the operator has configured this machine to prove."""
    configured = os.environ.get("FORGE_RUNTIME_LABEL", "").strip()
    label = configured or "本机演示环境"
    platform = "dgx-spark" if configured.lower() == "dgx spark" else "local"
    return {
        "label": label,
        "platform": platform,
        "verified": platform == "dgx-spark",
        "hint": "在 DGX Spark 上启动时设置 FORGE_RUNTIME_LABEL=DGX Spark；未设置时绝不冒充平台运行。",
    }


def run_data(run_dir: Path) -> dict[str, Any]:
    run_id = run_dir.name
    delivery = read_json(run_dir / "worker-delivery.json") or {}
    context = read_json(run_dir / "run-context.json") or {}
    contract = read_json(run_dir / "mvp-contract.json") or {}
    events = worker_events(run_id)
    input_file = next((item for item in (run_dir / "input").glob("reference.*") if item.is_file()), None)
    artifacts = delivery.get("artifacts", {}) if isinstance(delivery, dict) else {}
    dispatched = (ROOT / "contracts" / "live-trials" / f"{run_id}.dispatch.json").is_file()
    return {
        "run_id": run_id,
        "created_at": delivery.get("created_at") or context.get("prepared_at"),
        "status": delivery.get("status") or ("处理中" if dispatched else "已准备"),
        "dispatched": dispatched,
        "app": contract.get("app", {}),
        "events": events,
        "source": f"/files/{run_id}/input/{input_file.name}" if input_file else None,
        "preview": f"/files/{run_id}/artifacts/preview.png" if (run_dir / "artifacts" / "preview.png").is_file() else None,
        "report": f"/files/{run_id}/artifacts/acceptance-report.json" if (run_dir / "artifacts" / "acceptance-report.json").is_file() else None,
        "delivery": f"/files/{run_id}/worker-delivery.json" if (run_dir / "worker-delivery.json").is_file() else None,
        "app_url": f"/apps/{run_id}/index.html" if (run_dir / "app" / "index.html").is_file() else None,
        "pipeline_log": f"/files/{run_id}/worker-pipeline.log" if (run_dir / "worker-pipeline.log").is_file() else None,
        "artifact_summary": artifacts,
        "show_url": f"/show?run={run_id}",
    }


def actor_status() -> dict[str, bool]:
    command = cccc_command()
    if not command:
        return {"running": False}
    try:
        process = subprocess.run([command, "actor", "list"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
        payload = json.loads(process.stdout)
        actors = payload.get("result", {}).get("actors", [])
        actor = next((item for item in actors if item.get("id") == "mvp-worker"), {})
        return {"running": bool(actor.get("running"))}
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return {"running": False}


def launch_pipeline(contract: Path, run_dir: Path, run_id: str) -> Path:
    """Start a single controller process; phase progression is not delegated to chat."""
    log_path = run_dir / "worker-pipeline.log"
    command = [str(PYTHON), "scripts/worker_pipeline.py", "--contract", str(contract), "--batch", "live-trials"]
    creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    with log_path.open("w", encoding="utf-8") as log:
        subprocess.Popen(
            command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, text=True,
            encoding="utf-8", errors="replace", creationflags=creationflags,
        )
    return log_path


class IntakeHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            body = PAGE.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path in {"/show", "/show/"}:
            send_static_file(self, ROOT / "index.html")
            return
        if parsed.path == "/repo":
            body = repository_page()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        show_assets = {
            "/show/styles.css": ROOT / "styles.css",
            "/show/app.js": ROOT / "app.js",
            # /show?run=... treats relative URLs as root-relative in browsers.
            "/styles.css": ROOT / "styles.css",
            "/app.js": ROOT / "app.js",
        }
        if parsed.path in show_assets:
            send_static_file(self, show_assets[parsed.path])
            return
        if parsed.path.startswith("/apps/"):
            parts = [unquote(part) for part in parsed.path.split("/") if part]
            if len(parts) < 2:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            run_id = parts[1]
            relative = Path(*parts[2:]) if len(parts) > 2 else Path("index.html")
            app_root = (ROOT / "runs" / run_id / "app").resolve()
            candidate = (app_root / relative).resolve()
            if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id) or ".." in relative.parts or not candidate.is_file() or app_root not in candidate.parents:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            send_static_file(self, candidate)
            return
        if parsed.path.startswith("/assets/"):
            relative = Path(*[unquote(part) for part in parsed.path.removeprefix("/assets/").split("/")])
            candidate = (ROOT / relative).resolve()
            allowed_suffixes = {".jpg", ".jpeg", ".png", ".webp"}
            if ROOT.resolve() not in candidate.parents or candidate.suffix.lower() not in allowed_suffixes:
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            send_static_file(self, candidate)
            return
        if parsed.path == "/api/runs":
            runs_root = ROOT / "runs"
            runs = [run_data(path) for path in runs_root.glob("trial-*") if path.is_dir()]
            runs.sort(key=lambda item: item.get("created_at") or "", reverse=True)
            json_response(self, HTTPStatus.OK, {"actor": actor_status(), "runtime": runtime_info(), "runs": runs[:12]})
            return
        if parsed.path == "/api/project":
            json_response(self, HTTPStatus.OK, {"repository": repository_info(), "cccc_gui": "http://127.0.0.1:8848/ui/"})
            return
        if parsed.path.startswith("/api/runs/"):
            run_id = unquote(parsed.path.removeprefix("/api/runs/"))
            if not re.fullmatch(r"trial-[\w-]+", run_id):
                json_response(self, HTTPStatus.BAD_REQUEST, {"error": "无效的 run ID"})
                return
            run_dir = ROOT / "runs" / run_id
            if not run_dir.is_dir():
                json_response(self, HTTPStatus.NOT_FOUND, {"error": "找不到这个试跑"})
                return
            json_response(self, HTTPStatus.OK, {"runtime": runtime_info(), "actor": actor_status(), "run": run_data(run_dir)})
            return
        if parsed.path.startswith("/files/"):
            parts = [unquote(part) for part in parsed.path.split("/") if part]
            if len(parts) < 3:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            run_id, relative = parts[1], Path(*parts[2:])
            if not re.fullmatch(r"trial-[\w-]+", run_id) or ".." in relative.parts:
                self.send_error(HTTPStatus.FORBIDDEN)
                return
            candidate = (ROOT / "runs" / run_id / relative).resolve()
            root = (ROOT / "runs" / run_id).resolve()
            if not candidate.is_file() or root not in candidate.parents:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            return super().do_GET()
        self.send_error(HTTPStatus.NOT_FOUND)

    def translate_path(self, path: str) -> str:
        parsed = urlparse(path)
        if parsed.path.startswith("/files/"):
            parts = [unquote(part) for part in parsed.path.split("/") if part]
            return str(ROOT / "runs" / parts[1] / Path(*parts[2:]))
        return str(ROOT)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/intake":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_length = int(self.headers.get("Content-Length", "0"))
        if not 0 < content_length <= MAX_UPLOAD_BYTES:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "图片不能为空，且必须小于 16 MB。"})
            return
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": "请通过投递台上传图片。"})
            return
        try:
            form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type})
            field = form["screenshot"]
            if isinstance(field, list) or not getattr(field, "filename", ""):
                raise ValueError("请选择一张图片。")
            suffix = Path(field.filename).suffix.lower()
            if suffix not in ALLOWED_SUFFIXES:
                raise ValueError("只支持 JPG、PNG 或 WEBP 图片。")
            raw = field.file.read(MAX_UPLOAD_BYTES + 1)
            if len(raw) > MAX_UPLOAD_BYTES:
                raise ValueError("图片超过 16 MB。")
            if not raw:
                raise ValueError("图片内容为空。")
            app_name = safe_name(form.getfirst("app_name", "SparkMVP"), "SparkMVP")
            kind = safe_name(form.getfirst("kind", "mobile app"), "mobile app")
            dispatch = form.getfirst("dispatch", "false") == "true"
            created = datetime.now().astimezone()
            run_id = f"trial-{created.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4]}"
            upload_dir = ROOT / "inputs" / "live-uploads"
            contract_dir = ROOT / "contracts" / "live-trials"
            upload_dir.mkdir(parents=True, exist_ok=True)
            contract_dir.mkdir(parents=True, exist_ok=True)
            screenshot = upload_dir / f"{run_id}{suffix}"
            screenshot.write_bytes(raw)
            sample = read_json(ROOT / "contracts" / "mvp-contract.sample.json")
            if not sample:
                raise ValueError("找不到 Worker 契约模板。")
            sample["run_id"] = run_id
            sample["handoff"] = {"from": "worker-intake-desk", "to": "mvp-worker"}
            sample["source_screenshot"]["path"] = str(screenshot.resolve())
            sample["source_screenshot"]["authorized_for_demo"] = True
            sample["app"]["name"] = app_name
            sample["app"]["kind"] = kind
            contract = contract_dir / f"{run_id}.json"
            contract.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
            launcher = ROOT / "scripts" / "python.cmd"
            prepared = subprocess.run([str(launcher), str(ROOT / "scripts" / "prepare_run.py"), "--contract", str(contract)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
            if prepared.returncode:
                raise ValueError(f"创建独立 run 失败：{prepared.stderr or prepared.stdout}")
            message = "截图已创建独立契约，等待 Worker。"
            if dispatch:
                command = cccc_command()
                if not command:
                    raise ValueError("CCCC 命令不可用；截图已准备，但未派发。")
                start = subprocess.run([command, "actor", "start", "mvp-worker", "--group", DEFAULT_GROUP], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
                if start.returncode:
                    raise ValueError(f"无法启动 mvp-worker：{start.stderr or start.stdout}")
                pipeline_log = launch_pipeline(contract, ROOT / "runs" / run_id, run_id)
                (contract_dir / f"{run_id}.dispatch.json").write_text(json.dumps({"run_id": run_id, "sent_at": datetime.now().astimezone().isoformat(timespec="seconds"), "controller": "deterministic-pipeline", "pipeline_log": str(pipeline_log)}, ensure_ascii=False, indent=2), encoding="utf-8")
                message = "确定性 Pipeline 已启动；它会连续完成视觉理解、脚手架、验收和交付，CCCC GUI 可用于查看 Worker 与任务状态。"
            json_response(self, HTTPStatus.CREATED, {"run_id": run_id, "message": message, "contract": str(contract.resolve()), "run_dir": str((ROOT / "runs" / run_id).resolve()), "dispatched": dispatch, "show_url": f"/show?run={run_id}"})
        except (ValueError, KeyError, subprocess.TimeoutExpired) as exc:
            json_response(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:  # Keep browser feedback usable in a demo.
            json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"投递失败：{exc}"})


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run the local Screenshot-to-App Worker upload desk.")
    parser.add_argument("--port", type=int, default=4181)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), IntakeHandler)
    print(f"Worker upload desk: http://127.0.0.1:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
