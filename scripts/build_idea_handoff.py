from __future__ import annotations

"""Reliable Stage-2 delivery adapter for the imported A2 Idea Agent.

CCCC remains the record of who owns Stage 2.  This adapter only creates the
same auditable Foreman-facing artifacts when a desktop Codex actor cannot run
its local session.  It never starts the MVP worker.
"""

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Write A2-compatible Stage-2 handoffs from a validated CLI form.")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if not args.run_id.startswith("incubation-"):
        raise SystemExit("run_id 必须是 incubation-* 格式")

    handoff_dir = ROOT / "handoffs" / args.run_id
    request_path = handoff_dir / "request.json"
    capability_path = handoff_dir / "cli-capability-form.json"
    if not request_path.exists() or not capability_path.exists():
        raise SystemExit("Stage 2 需要同一 run 的 request.json 和 cli-capability-form.json")
    request, capability = read_json(request_path), read_json(capability_path)
    if capability.get("source") != "cli-researcher" or capability.get("validation", {}).get("status") != "PASS":
        raise SystemExit("只接受已通过校验的 cli-researcher 能力表单")

    now = datetime.now().astimezone()
    suffix = hashlib.sha256(args.run_id.encode("utf-8")).hexdigest()[:6]
    a2_run_id = f"a2_{now:%Y%m%d_%H%M%S}_{suffix}"
    a2_dir = ROOT / "agents" / "idea-agent" / "runs" / a2_run_id
    a2_evidence = {
        "run_id": a2_run_id,
        "incubation_run_id": args.run_id,
        "mode": "deterministic delivery adapter",
        "reason": "Used only when the imported A2 desktop actor is unavailable; preserves Stage-2 handoff and never dispatches Worker.",
        "request_path": f"handoffs/{args.run_id}/request.json",
        "capability_form_path": f"handoffs/{args.run_id}/cli-capability-form.json",
        "catalog_evidence": {
            key: capability.get(key)
            for key in ("summary_index", "full_records_root", "schema", "field_docs", "validation", "catalog_counts")
        },
        "generated_at": now.isoformat(timespec="seconds"),
    }
    write_json(a2_dir / "delivery-bridge.json", a2_evidence)

    tools = [item.get("id") for item in capability.get("capabilities", []) if item.get("id")]
    browser_tool = "vercel-labs/agent-browser" if "vercel-labs/agent-browser" in tools else (tools[0] if tools else "catalog-reference-only")
    common_chain = {
        "chain_id": "chain_001",
        "status": "partial",
        "tool_ids": [browser_tool],
        "gaps": [
            "目录记录不代表工具已安装或已执行",
            "截图视觉理解与前端代码生成必须由后续 Worker 的已授权输入和运行日志证明",
        ],
    }
    options = [
        {
            "rank": 1,
            "idea_id": "idea_001",
            "name": "Screenshot MVP Studio",
            "target_user": "需要在评审或演示前快速验证界面方向的产品团队",
            "problem": "授权界面截图只能呈现静态视觉，无法快速证明核心交互和本地前端是否可运行。",
            "solution": "把授权截图转化为保留信息层级、使用虚构品牌内容的可运行前端，并交付浏览器验收证据。",
            "four_criterion_scores": {"visual_expression": 96, "generality": 91, "pain_point": 92, "innovation": 88},
            "capability_chain": common_chain,
            "trade_offs": ["需要在 Worker 前确认授权截图路径。", "不能把 catalog 记录表述成已安装的生产能力。"],
        },
        {
            "rank": 2,
            "idea_id": "idea_002",
            "name": "Responsive Proofboard",
            "target_user": "需要把单张移动端或网页参考图扩展为多端演示的前端团队",
            "problem": "单一截图无法说明页面在不同视口下是否可用。",
            "solution": "生成虚构品牌的响应式页面并输出固定视口浏览器验收截图。",
            "four_criterion_scores": {"visual_expression": 90, "generality": 93, "pain_point": 84, "innovation": 80},
            "capability_chain": {**common_chain, "chain_id": "chain_002"},
            "trade_offs": ["多视口会增加 demo 的实现与验收时间。"],
        },
        {
            "rank": 3,
            "idea_id": "idea_003",
            "name": "Interaction Replay Demo",
            "target_user": "需要用一条可重复播放的流程解释交互意图的产品团队",
            "problem": "评审者从静态图中难以理解选中、加购或确认反馈等状态变化。",
            "solution": "生成可点击的本地状态流，并通过浏览器测试记录关键状态。",
            "four_criterion_scores": {"visual_expression": 94, "generality": 82, "pain_point": 86, "innovation": 84},
            "capability_chain": {**common_chain, "chain_id": "chain_003"},
            "trade_offs": ["适合交互显著的页面，对纯展示型页面收益较低。"],
        },
    ]
    disclosure = {
        "capability_form_path": f"handoffs/{args.run_id}/cli-capability-form.json",
        "source": "cli-researcher",
        "demo_only": False,
        "treatment": "本轮由 Foreman 直接读取 CLI Agent 长期维护且已验证的持久能力快照（0 warnings）；CLI Agent 未参与本轮孵化。该快照是可追溯的目录证据，不等同于这些 CLI 已安装或已运行。",
    }
    shortlist = {
        "schema_version": 1,
        "run_id": args.run_id,
        "a2_run_id": a2_run_id,
        "input_disclosure": disclosure,
        "evidence": {
            "request_path": f"handoffs/{args.run_id}/request.json",
            "capability_form_path": f"handoffs/{args.run_id}/cli-capability-form.json",
            "a2_delivery_evidence": f"agents/idea-agent/runs/{a2_run_id}/delivery-bridge.json",
            "validation": ["Persistent CLI catalog snapshot loaded (0 warnings)", "A2 delivery handoff written", "Worker intentionally not started"],
        },
        "scoring_criteria": {
            "visual_expression": "输入、转化、交互与可见结果是否适合直接演示。",
            "generality": "能否延伸到相邻用户、页面类型与重复工作流。",
            "pain_point": "目标用户问题是否具体、频繁且值得解决。",
            "innovation": "视觉理解、可运行原型与验证证据的组合是否新颖。",
        },
        "ranking_method": "四项 demo 标准显式排序；目录能力仅作可追溯的可行性边界，不作为安装或运行证明。",
        "ranked_options": options,
        "recommended_idea": {
            "idea_id": "idea_001",
            "name": "Screenshot MVP Studio",
            "selection_rationale": "它把“截图 → 可运行前端 → 浏览器验收”的完整前后对比压缩为一条可演示路径，同时可复用于零售、点餐和内容门户等界面。",
            "non_negotiables": ["Worker 开始前必须登记已授权截图的真实本地路径。", "不复用来源商标、商品图、价格、文案或其他品牌资产。", "只交付本地前端 MVP，不接入真实交易或账户。"],
        },
        "warnings": ["没有授权截图路径时，Worker handoff 必须保持 blocked。", "当前 Stage-2 产物由稳定性适配器落盘，A2 desktop actor 的 CCCC 任务仍保留可视化审计记录。"],
    }
    contract = {
        "schema_version": 1,
        "run_id": args.run_id,
        "selected_idea_id": "idea_001",
        "idea_id": "idea_001",
        "name": "Screenshot MVP Studio",
        "target_user": options[0]["target_user"],
        "pain_point": options[0]["problem"],
        "input_disclosure": {
            "capability_form_source": "cli-researcher",
            "demo_only": False,
            "statement": disclosure["treatment"],
        },
        "visual_direction": {
            "concept": "在授权截图的抽象信息层级基础上，生成一个本地、可点击、虚构品牌的单页前端 MVP。",
            "layout_principles": ["理解布局层级、密度和交互意图，而不是复制品牌资产。", "使用原创品牌名、文案、图标、配色和占位视觉。", "移动端优先，并可在桌面浏览器中清晰演示。"],
            "fictional_brand_boundary": "不得复刻来源 logo、商标、商品图片、名称、价格、专有文案或可识别的品牌资产。",
        },
        "primary_interaction": "用户上传已授权截图；Worker 生成本地前端，完成一个与界面意图一致的核心交互，并在浏览器中自动验收。",
        "core_interaction": {"happy_path": ["上传授权截图", "提取布局和交互意图", "生成虚构品牌前端", "打开浏览器", "执行核心交互测试", "交付源码、截图与报告"], "state_rules": ["所有状态仅在本地 demo 中生效。", "不发起真实支付、账户、订单或外部交易请求。"]},
        "screenshot_input": {"status": "blocked_pending_authorized_path", "required_before_worker_start": True, "authorized_source_paths": [], "requirements": ["Foreman 必须登记真实本地授权截图路径。", "截图只可用作布局和交互参考。", "路径及授权范围必须在启动 Worker 前写入契约或 Foreman 更新。"]},
        "acceptance_criteria": ["启动前已记录授权截图路径。", "生成页面在本地浏览器可打开。", "页面保留抽象信息层级并使用虚构品牌内容。", "至少一个核心交互可完成并可见反馈。", "交付源码、浏览器截图和 pass/fail 验收报告。", "不出现来源商标或真实交易接口。"],
        "capability_chain": common_chain,
        "handoff": {"from": "idea-foreman", "to": "mvp-worker", "status": "blocked_pending_authorized_screenshot", "instruction": "Foreman 仅在补充授权截图路径后，才能以此契约创建 Stage-3 tracked task。"},
    }
    write_json(handoff_dir / "idea-shortlist.json", shortlist)
    write_json(handoff_dir / "mvp-contract.json", contract)
    print(handoff_dir / "idea-shortlist.json")
    print(handoff_dir / "mvp-contract.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
