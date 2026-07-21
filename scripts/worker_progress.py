from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Keep the CCCC terminal and PowerShell recording readable on Windows.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
MESSAGE_KEYS = {
    "fastbite-visual-start": "开始理解餐饮点餐截图中的促销、菜单与取餐意图",
    "fastbite-visual-pass": "已完成布局与交互意图提取，未使用原品牌内容",
    "fastbite-scaffold-start": "开始生成虚构品牌 FastBite 的前端脚手架",
    "fastbite-scaffold-pass": "已完成菜单筛选、加入餐袋和取餐方式交互",
    "fastbite-browser-start": "正在启动 Edge 执行浏览器验收",
    "fastbite-browser-pass": "浏览器验收通过：加载、筛选、加餐和取餐均正常",
    "fastbite-delivery-start": "正在封装源码、预览图与验收报告",
    "fastbite-delivery-pass": "FastBite 交付回执已生成",
    "malllite-visual-start": "开始理解电商首页的频道、搜索与发现流结构",
    "malllite-visual-pass": "已完成频道、快捷入口、促销和双列发现流的意图提取",
    "malllite-scaffold-start": "开始生成虚构品牌拾光集和本地 CSS 插画",
    "malllite-scaffold-pass": "已完成搜索筛选与购物袋计数交互",
    "malllite-browser-start": "正在启动 Edge 执行浏览器验收",
    "malllite-browser-pass": "浏览器验收通过：加载、筛选和加入购物袋均正常",
    "malllite-delivery-start": "正在封装源码、预览图与验收报告",
    "malllite-delivery-pass": "MallLite 交付回执已生成，GitHub 按契约跳过",
    "generic-visual-start": "开始分析授权截图中的布局和交互意图",
    "generic-visual-pass": "视觉理解完成，已写入界面规格",
    "generic-scaffold-start": "开始生成虚构品牌的前端页面",
    "generic-scaffold-pass": "前端源码和必要交互已生成",
    "generic-browser-start": "正在启动 Edge 执行浏览器验收",
    "generic-browser-pass": "浏览器验收通过",
    "generic-delivery-start": "正在封装源码、预览图与验收报告",
    "generic-delivery-pass": "交付回执已生成",
    "generic-delivery-fail": "流水线失败，已保留日志供排查",
}
PHASE_CN = {"visual": "视觉理解", "scaffold": "前端脚手架", "browser": "浏览器验收", "delivery": "交付封装"}
STATUS_CN = {"STARTED": "开始", "PASS": "通过", "FAIL": "失败"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Append a visible Screenshot-to-App Worker progress event.")
    parser.add_argument("--batch", required=True)
    parser.add_argument("--run", required=True)
    parser.add_argument("--phase", required=True, choices=("visual", "scaffold", "browser", "delivery"))
    parser.add_argument("--status", required=True, choices=("STARTED", "PASS", "FAIL"))
    message_group = parser.add_mutually_exclusive_group(required=True)
    message_group.add_argument("--message")
    message_group.add_argument("--message-key", choices=sorted(MESSAGE_KEYS))
    args = parser.parse_args()
    batch_dir = ROOT / "runs" / args.batch
    batch_dir.mkdir(parents=True, exist_ok=True)
    message = MESSAGE_KEYS.get(args.message_key, args.message)
    event = {
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "batch_id": args.batch,
        "run_id": args.run,
        "phase": args.phase,
        "status": args.status,
        "message": message,
    }
    with (batch_dir / "worker-progress.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    (batch_dir / "worker-status.json").write_text(json.dumps(event, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{event['timestamp']}] [{args.run}] {PHASE_CN[args.phase]} {STATUS_CN[args.status]}: {message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
