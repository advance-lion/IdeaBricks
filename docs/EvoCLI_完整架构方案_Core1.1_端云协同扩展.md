# EvoCLI 完整架构方案

**Core 1.1 + Edge-Cloud Collaboration Extension**

> CLI-First · Capability-Native · Self-Evolving · Edge-Cloud Collaborative Agent Runtime

- **核心运行平台：** NVIDIA DGX Spark
- **Agent 编排：** CCCC
- **Evolution Backend：** GenericAgent / 可扩展 Optimizer
- **文档定位：** 完整目标架构；黑客松按 Core First、Evolution Second、Distribution Last 逐步实现

---

> **核心结论**
>
> EvoCLI 的核心能力不依赖云端。Core 1.1 先在 DGX Spark 上完成 CLI-First Capability Runtime、结构化 Observation、Trace 与双轨 Self-Evolution；端云协同作为 Deployment Extension，通过 PlacementResolver、ExecutionBackend、TraceStore、EvolutionBackend 等标准接口自然叠加。

## 目录

- [1. 文档目标与版本关系](#section-1)
- [2. 总体技术定位](#section-2)
- [3. 架构设计原则](#section-3)
- [4. 完整分层架构](#section-4)
- [5. Agent Orchestration 与 CCCC](#section-5)
- [6. EvoCLI Core Runtime](#section-6)
- [7. Capability Runtime 与 Registry](#section-7)
- [8. Execution Runtime 与 Placement](#section-8)
- [9. Observation、Trace 与 Metrics](#section-9)
- [10. 双轨 Self-Evolution](#section-10)
- [11. GenericAgent / Codex / Claude Code 分工](#section-11)
- [12. 完整端云协同架构](#section-12)
- [13. Cloud Control Plane](#section-13)
- [14. DGX Spark Edge Plane](#section-14)
- [15. 典型任务执行链路](#section-15)
- [16. Cloud-Assisted Edge Evolution](#section-16)
- [17. 数据、安全与权限边界](#section-17)
- [18. 可靠性、版本与回滚](#section-18)
- [19. Core 1.1 预留接口](#section-19)
- [20. Hackathon 架构与完整 Agent 对照](#section-20)
- [21. Demo Story 与架构映射](#section-21)
- [22. 演进路线与最终定义](#section-22)

---

<a id="section-1"></a>

## 1. 文档目标与版本关系

本方案将此前的 Core 1.1 与完整端云协同设计统一为一套分层架构。目标是同时满足两个需求：第一，黑客松阶段可在 DGX Spark 单机环境中独立完成核心闭环；第二，未来可以在不重构 EvoCLI Core 的前提下，增加 Cloud Gateway、远程执行、集中 Trace、云侧 Sandbox、动态 Placement 和多 Edge Node。

| 层级 | 当前定位 | 是否依赖云端 | 主要内容 |
| --- | --- | --- | --- |
| EvoCLI Core 1.1 | 核心运行时 | 否 | Capability Runtime、CLI Executor、Observation、Trace、Evolution Controller |
| Evolution Extension | 自进化能力 | 否 | Capability Evolution 0→1；Performance Evolution 1→Better；GenericAgent Backend |
| Edge-Cloud Extension | 部署与调度扩展 | 否（可选） | Cloud Gateway、Remote Executor、Placement、Cloud Trace、Cloud Sandbox |
| Full Agent Platform | 长期完整形态 | 部分 | Cloud Control Plane、多 Agent、多 Edge Node、队列、策略、版本治理 |

<a id="section-1-1"></a>

### 1.1 设计原则：Core 与 Deployment 解耦

```text
EvoCLI Core
    ↓
Capability Runtime
    ↓
ExecutionBackend Interface
    ├── LocalExecutionBackend      [Core 1.1]
    ├── RemoteExecutionBackend     [Edge-Cloud]
    └── CloudExecutionBackend      [Edge-Cloud]

Self-Evolution
    ↓
EvolutionBackend Interface
    ├── GenericAgentEvolutionBackend
    ├── Hermes / GEPA Adapter      [Future]
    └── Custom Optimizer           [Future]
```

<a id="section-2"></a>

## 2. 总体技术定位

EvoCLI 是一个以 CLI 为原生行动接口、以 Capability 为统一能力抽象、由 CCCC 组织专业 Agent Team，并通过执行 Trace 持续扩展和优化自身能力的通用 Agent Runtime。

> **一句话定位**
>
> EvoCLI 通过 CLI-First 让 Agent 第一次执行就更快，通过 Capability Evolution 让不会做的事情自己学会，通过 Performance Evolution 让已经会做的事情越做越快，并通过端云协同把同一套 Capability Runtime 扩展到 Local / Edge / Cloud。

```text
CLI-First
    ↓
Capability-Native Runtime
    ↓
Structured Action & Observation
    ↓
Trace & Metrics
    ↓
Self-Evolution
    ├── Learn to Do        (0 → 1)
    └── Learn to Do Faster (1 → Better)
    ↓
Placement Abstraction
    ↓
Local / Edge / Cloud
```

<a id="section-3"></a>

## 3. 架构设计原则

| 原则 | 说明 |
| --- | --- |
| CLI-First | 优先通过 CLI、API、Script 和结构化接口操作真实软件，减少截图识别、坐标点击和 GUI 状态判断。 |
| Capability-Native | Agent 面向 repo.create、cad.model.create 等语义能力，而不是绑定 gh、FreeCAD 等具体工具。 |
| Structured Observation | 优先通过 exit_code、stdout、stderr、Schema、Read-Back、Artifact Exists 验证结果。 |
| Evolution-Native | Capability Registry 与 Workflow Registry 都是可增长、可版本化的运行时资产。 |
| Agent Backend Pluggable | Claude Code、Codex、GenericAgent、Local LLM 是可编排 Worker，不把核心架构绑定到某个单一 Agent。 |
| Placement Decoupled | Agent Harness 在哪里运行、模型在哪里推理、Capability 在哪里执行是三个独立问题。 |
| Core First, Distribution Last | 先完成 Core，再完成 Evolution，最后叠加端云协同与分布式部署。 |

<a id="section-4"></a>

## 4. 完整分层架构

```text
                                      USER
                                       │
                           Feishu / Web / API / CLI
                                       │
                                       ▼
┌────────────────────────────────────────────────────────────────────┐
│                        CLOUD ACCESS / CONTROL                      │
│ Gateway / Auth / Session / Task Queue / Trace / History           │
│ Agent Registry / Capability Registry Master / Dashboard           │
│ Optional: CCCC Control Plane / Evolution Sandbox / Eval Farm      │
└───────────────────────────────┬────────────────────────────────────┘
                                │ Secure Channel / RPC / HTTP
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                            AGENT PLANE                             │
│                               CCCC                                │
│ Claude Code | Codex | GenericAgent | Local Agent                  │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                         EvoCLI CORE RUNTIME                        │
│ Task Runtime / Agent Router / Capability Registry / Router         │
│ PlacementResolver / Execution / Observation / Trace / Metrics      │
│ Evolution Controller / Evaluation Harness / Version Registry      │
└───────────────────────────────┬────────────────────────────────────┘
                                │
                         ExecutionBackend
                   ┌────────────┼────────────┐
                   ▼            ▼            ▼
                Local         Edge         Cloud
                   │            │            │
         Native CLI /       DGX Node /    SaaS / Sandbox /
         CLI-Anything       Local Apps     Remote Services
                   │
          GitHub / Lark / Draw.io / LibreOffice / FreeCAD
```

完整架构中，Cloud 是“接入、控制、持久化、安全与分布式扩展层”；DGX Spark 是“本地智能、私有数据与真实软件执行节点”；EvoCLI Core 位于两者之间，保持逻辑独立。

<a id="section-5"></a>

## 5. Agent Orchestration 与 CCCC

CCCC 负责 Agent Team 的组织、任务委派、Agent 间协作和状态协调。EvoCLI 不要求所有 Agent 固定运行在云侧或端侧，而是通过 Agent Registry 描述其角色、能力与可用位置。

| Agent / Worker | 建议角色 | 典型职责 | 部署位置 |
| --- | --- | --- | --- |
| Claude Code | Planner / Reviewer | 复杂规划、任务分解、架构理解、Code Review、Evolution Review | DGX / Cloud 可配置 |
| Codex | Builder | 代码生成、CLI 生成、测试生成、Bug Fix | DGX / Cloud 可配置 |
| GenericAgent | Evolution Worker | 经验分析、SOP 提取、Skill/Workflow Candidate、性能优化建议 | DGX / Cloud 可配置 |
| Local LLM | Local Agent | 本地推理、日志分析、Artifact Review、私有数据处理 | DGX Spark |

<a id="section-5-1"></a>

### 5.1 三种 Placement 必须解耦

| 维度 | 问题 | 示例 |
| --- | --- | --- |
| Agent Placement | Agent Harness 在哪里运行？ | Claude Code/Codex/GenericAgent 可位于 DGX 或 Cloud |
| Model Placement | 模型在哪里推理？ | 外部模型服务、企业 Gateway、DGX Local Model |
| Capability Placement | 实际 Tool/CLI 在哪里执行？ | FreeCAD 在 Edge；Cloud Sandbox 在 Cloud；SaaS 可 Cloud |

<a id="section-6"></a>

## 6. EvoCLI Core Runtime

```text
EvoCLI Runtime
│
├── Task Runtime
├── Agent Router
├── Capability Registry
├── Capability Router
├── PlacementResolver
├── Execution Runtime
│   ├── CLI Executor
│   ├── LocalExecutionBackend
│   ├── RemoteExecutionBackend      [Extension]
│   └── CloudExecutionBackend       [Extension]
├── Observation Engine
├── Trace Recorder
├── Metrics Collector
├── Evolution Controller
├── Evaluation Harness
└── Version Registry
```

| 组件 | 职责 | Core 1.1 | 完整端云 |
| --- | --- | --- | --- |
| Task Runtime | 任务生命周期、上下文与 Trace ID | 实现 | 复用 |
| Agent Router | 选择 Planner/Builder/Evolution Agent | 基础实现 | 支持远程 Agent |
| Capability Router | 选择 Capability Provider | 实现 | 复用 |
| PlacementResolver | 决定 Local/Edge/Cloud | 固定 Local | 动态/策略化 |
| Execution Runtime | 统一执行请求与结果 | Local | Local + Remote + Cloud |
| Observation | 结构化验证任务结果 | 实现 | 复用 |
| Trace/Metrics | 记录性能、调用、产物与失败 | 本地 | 集中持久化 |
| Evolution Controller | Detect/Trigger/Delegate/Evaluate/Promote | 实现 | 复用 |
| Version Registry | Capability/Workflow 版本管理 | 简化 | 完整治理 |

<a id="section-7"></a>

## 7. Capability Runtime 与 Registry

EvoCLI 的核心抽象是 Task → Capability → Provider → Executor → Software。上层 Agent 只依赖语义 Capability，不直接绑定具体 CLI。

```text
Task
  ↓
Capability
  ↓
Provider
  ↓
Executor
  ↓
Software / Service

Example:
cad.model.create
  ↓
FreeCAD CLI-Anything
  ↓
CLIAnythingExecutor
  ↓
FreeCAD
```

<a id="section-7-1"></a>

### 7.1 Capability Registry 建议字段

```yaml
name: cad.model.create
domain: cad
description: Create a 3D CAD model from structured parameters

provider:
  name: freecad-cli-anything
  type: cli_anything

executor:
  backend: local

placement:
  preferred: edge
  allowed: [local, edge, cloud]

validation:
  strategy: artifact_and_rule

risk:
  level: medium

version:
  current: v1
  status: active

metrics:
  success_rate: 0.98
  avg_latency_ms: 8200
```

<a id="section-7-2"></a>

### 7.2 Provider 类型

| Provider Type | 当前/未来 | 用途 |
| --- | --- | --- |
| native_cli | 当前 | gh、lark-cli 等成熟 CLI |
| cli_anything | 当前 | Draw.io、LibreOffice、FreeCAD 等软件 CLI 化 |
| workflow | 当前 | 组合多个 Capability 的稳定 Workflow |
| evolved_skill | 当前 | Self-Evolution 生成并注册的能力 |
| http_api | 扩展 | 云服务/API Provider |
| mcp | Future | 生态兼容层，不作为 EvoCLI 核心 |

<a id="section-8"></a>

## 8. Execution Runtime 与 Placement

Core 1.1 只需要 LocalExecutionBackend，但所有执行通过统一 ExecutionBackend 接口。端云协同只增加新的 Backend 和 Placement 策略，不改动 Capability Router、Observation 或 Evolution。

```text
ExecutionBackend
├── LocalExecutionBackend
├── RemoteExecutionBackend
└── CloudExecutionBackend

PlacementResolver
├── LocalPlacementResolver          [Core 1.1]
├── StaticPlacementResolver         [Minimal Edge-Cloud]
└── PolicyPlacementResolver         [Full Agent]
```

<a id="section-8-1"></a>

### 8.1 Unified ExecutionResult

```json
{
  "success": true,
  "exit_code": 0,
  "stdout": "...",
  "stderr": "",
  "duration_ms": 1200,
  "artifacts": ["architecture.png", "report.pdf"],
  "metadata": {
    "backend": "local",
    "provider": "drawio-cli"
  }
}
```

<a id="section-9"></a>

## 9. Observation、Trace 与 Metrics

<a id="section-9-1"></a>

### 9.1 Observation 优先级

```text
Rule-Based
    ↓
Structured Validation
    ↓
Artifact / State Read-Back
    ↓
LLM Reviewer (only when needed)
```

目标是让 Task Success 可验证，而不是由 Agent 自己声明成功。Performance Evolution 也必须以 Verified Correctness 为硬约束。

<a id="section-9-2"></a>

### 9.2 Trace Schema

```json
{
  "trace_id": "trace_001",
  "task": "project.bootstrap",
  "workflow_version": "v1",
  "success": true,
  "metrics": {
    "total_duration_ms": 38200,
    "llm_duration_ms": 18000,
    "cli_duration_ms": 18000,
    "observation_duration_ms": 2200,
    "llm_calls": 6,
    "cli_calls": 9,
    "retry_count": 1,
    "token_usage": 11800
  },
  "artifacts": [
    "repo",
    "architecture.png",
    "report.pdf"
  ]
}
```

<a id="section-9-3"></a>

### 9.3 核心指标

| 指标 | 意义 | 用途 |
| --- | --- | --- |
| Verified Task Success | 任务真实完成且通过 Read-Back / Artifact 验证 | 所有优化的硬约束 |
| End-to-End Latency | 用户请求到验证完成的总耗时 | CLI-First 与性能进化主指标 |
| LLM Calls | 模型调用次数 | 衡量决策链长度 |
| CLI Calls | Tool/CLI 调用次数 | 衡量 Action Efficiency |
| Retry Count | 失败后的重试次数 | 稳定性 |
| Token Usage | 模型 Token 消耗 | 成本与效率 |
| Capability Growth | 新增并验证的 Capability 数量 | 0→1 进化指标 |
| Repeat Task Speedup | V1 与 V2 的重复任务加速比 | 1→Better 进化指标 |

<a id="section-10"></a>

## 10. 双轨 Self-Evolution

完整 Self-Evolution 由 EvoCLI Evolution Controller 控制，具体“如何学习/如何生成候选”可以委派给 GenericAgent 等 Evolution Backend。

```text
                  EvoCLI Evolution System

                  Evolution Controller
                         │
             ┌───────────┴───────────┐
             ▼                       ▼
   Capability Evolution      Performance Evolution
        0 → 1                   1 → Better
             │                       │
             └───────────┬───────────┘
                         ▼
                       CCCC
                         │
                         ▼
                  GenericAgent
                Evolution Backend
                         │
                 Candidate Output
                         │
                         ▼
                 EvoCLI Evaluation
                         │
                 PASS / FAIL / Promote
```

<a id="section-10-1"></a>

### 10.1 Capability Evolution：0 → 1

```text
Task
  ↓
Capability Router
  ↓
No Suitable Provider
  ↓
Capability Gap
  ↓
Evolution Controller
  ↓
CCCC → GenericAgent
  ↓
SOP / Skill Candidate
  ↓
Codex Builder (when code is needed)
  ↓
Sandbox Test
  ↓
Artifact / Functional Verification
  ↓
Capability Registry
  ↓
Reuse
```

<a id="section-10-2"></a>

### 10.2 Performance Evolution：1 → Better

```text
Workflow V1
  ↓
Execution Trace
  ↓
Repeated / Inefficient Pattern
  ↓
Evolution Controller
  ↓
GenericAgent Analyze / Optimize
  ↓
Workflow Candidate V2
  ↓
Benchmark V1 × N vs V2 × N
  ↓
Correctness >= Baseline ?
  ↓
Latency / Calls / Retry / Token Improved ?
  ↓
Promote V2
```

<a id="section-11"></a>

## 11. GenericAgent / Codex / Claude Code 分工

| 阶段 | EvoCLI | GenericAgent | Codex | Claude Code |
| --- | --- | --- | --- | --- |
| 检测 | 发现 Capability Gap / Optimization Opportunity | — | — | 可辅助分析 |
| 学习/归纳 | 提供 Trace、约束与目标 | 提取 SOP、模式、候选优化方案 | — | 可 Review |
| 构建 | 定义 Capability Contract | 生成 Skill/SOP Candidate | 生成 CLI/代码/测试 | 复杂方案审阅 |
| 评估 | Sandbox、Benchmark、Correctness Gate | 提供建议 | 修复失败候选 | Review |
| 发布 | Registry / Version / Promote / Rollback | — | — | — |

> **边界原则**
>
> GenericAgent 负责“学习和进化”，EvoCLI 负责“什么时候进化、进化什么、是否真的更好、是否正式生效”。这样可以复用成熟 Agent 的自进化能力，同时保留 EvoCLI 自己的 Runtime 与治理创新。

<a id="section-12"></a>

## 12. 完整端云协同架构

端云协同是完整平台的部署扩展。它的目标不是重构 EvoCLI Core，而是解决公网接入、资源调度、并发缓冲、集中状态、安全 Sandbox、多 Edge Node 和跨位置 Capability 执行。

```text
                        CLOUD CONTROL PLANE
┌──────────────────────────────────────────────────────────────┐
│ API / Feishu Gateway                                         │
│ Auth / Session / User Context / Task Queue                   │
│ Optional CCCC Control Plane                                  │
│ Agent Registry / Capability Registry Master                  │
│ Placement Scheduler                                          │
│ Workflow History / Trace / Metrics / Dashboard               │
│ Evolution Sandbox / Evaluation Farm                          │
└──────────────────────────────┬───────────────────────────────┘
                               │ Secure Channel
                               ▼
                        DGX SPARK EDGE PLANE
┌──────────────────────────────────────────────────────────────┐
│ Edge Agent Runtime                                           │
│ Local LLM / Local Reviewer                                   │
│ Local Registry Cache                                         │
│ CLI Executor                                                 │
│ LibreOffice / Draw.io / FreeCAD                              │
│ Local Files / Private Data / Local Artifacts                 │
└──────────────────────────────────────────────────────────────┘
```

<a id="section-13"></a>

## 13. Cloud Control Plane

| 模块 | 职责 |
| --- | --- |
| Agent Gateway | 统一接收 Feishu/Web/API/CLI 请求，处理 Auth、Session、Trace ID、Streaming、Callback |
| Task Queue | 缓冲请求，控制 DGX 瞬时并发，支持 Backpressure |
| Agent Control | 可选将 CCCC 主控制节点云化，统一管理 Cloud/Edge Agent Workers |
| Agent Registry | 记录 Agent 类型、角色、能力、位置与健康状态 |
| Capability Registry Master | 集中保存 Capability Metadata 与版本；Edge 可持有 Cache |
| Placement Scheduler | 根据数据隐私、资源、延迟、成本、可用性决定 Cloud / Edge |
| Trace / History | 集中存储 Workflow History、Evolution History 与 Metrics |
| Evolution Sandbox | 对生成的 Skill/CLI 进行隔离测试、依赖检查和 E2E 验证 |
| Dashboard | 展示任务状态、执行指标、进化版本和系统健康 |

<a id="section-14"></a>

## 14. DGX Spark Edge Plane

| 模块 | 职责 |
| --- | --- |
| Local LLM | 本地推理、私有数据处理、日志分析和轻量 Reviewer |
| Edge Agent Runtime | 运行 EvoCLI Core 或作为云侧 Control Plane 的 Edge Worker |
| CLI Executor | 执行本地 CLI、CLI-Anything 与 Evolved Skill |
| Local Software | LibreOffice、Draw.io、FreeCAD 等专业应用 |
| Local Files / Private Data | 敏感数据尽量不离开本地 |
| Registry Cache | 缓存允许在端侧执行的 Capability Metadata |
| Local Artifact Store | 保存 CAD、PDF、图片、文档等产物 |

<a id="section-15"></a>

## 15. 典型任务执行链路

<a id="section-15-1"></a>

### 15.1 本地任务

```text
User
  ↓
CCCC / Planner
  ↓
Capability Router
  ↓
PlacementResolver = EDGE
  ↓
LocalExecutionBackend
  ↓
FreeCAD / LibreOffice
  ↓
Observation
  ↓
Trace
```

<a id="section-15-2"></a>

### 15.2 云侧任务

```text
User
  ↓
Cloud Gateway
  ↓
CCCC / Planner
  ↓
Capability Router
  ↓
PlacementResolver = CLOUD
  ↓
CloudExecutionBackend
  ↓
SaaS / Cloud CLI / Sandbox
  ↓
Observation
  ↓
Central Trace
```

<a id="section-15-3"></a>

### 15.3 混合任务

```text
Project Bootstrap
    │
    ├── repo.create          → Cloud / SaaS
    ├── document.create      → Cloud / SaaS
    ├── diagram.create       → Edge
    ├── cad.model.create     → Edge
    └── skill.test           → Cloud Sandbox

Independent tasks may run in parallel
    ↓
Join
    ↓
report.generate / final package
```

<a id="section-16"></a>

## 16. Cloud-Assisted Edge Evolution

完整架构下，自进化可以采用“端侧发现、云侧生成与验证、端侧部署”的闭环，既保留本地执行和数据隐私，又提高新能力测试的安全性。

```text
DGX Edge
  ↓
Detect Capability Gap / Performance Issue
  ↓
Cloud CCCC / Evolution Controller
  ↓
GenericAgent / Codex / Claude Code
  ↓
Generate Candidate
  ↓
Cloud Sandbox / Eval Farm
  ↓
Correctness / Security / Dependency Check
  ↓
Human Approval (optional)
  ↓
Versioned Capability Registry
  ↓
DGX Pull / Activate / Rollback
```

<a id="section-17"></a>

## 17. 数据、安全与权限边界

| 安全域 | 设计 |
| --- | --- |
| 数据本地性 | 敏感文件、私有 CAD、内部文档优先在 DGX Edge 处理，不默认上传云端 |
| Capability Policy | Registry 标注 data_scope、risk、allowed_placement 和 auth_required |
| 最小权限 | gh/lark 等凭证按 Provider 隔离，Agent 不直接持有不必要权限 |
| Sandbox | 自生成代码先在 Docker/Cloud Sandbox 中测试，不直接进入生产执行环境 |
| 审计 | 所有关键执行生成 Trace ID，记录 Provider、Backend、输入摘要、结果与版本 |
| 人审 | 高风险 Capability 或自进化候选可要求 Human Approval |
| 版本回滚 | 新 Workflow/Skill 失败时快速切回上一 Active 版本 |

<a id="section-18"></a>

## 18. 可靠性、版本与回滚

```text
Capability / Workflow Lifecycle

PROPOSED
  ↓
GENERATED
  ↓
TESTING
  ↓
VERIFIED
  ↓
CANARY      [Full Agent]
  ↓
ACTIVE
  ↓
DEPRECATED
  ↓
ROLLBACK (when needed)
```

黑客松阶段可以简化为 PROPOSED → TESTING → VERIFIED → ACTIVE / DEPRECATED；完整平台再增加 Canary、自动回滚、多版本 Benchmark 与策略化发布。

<a id="section-19"></a>

## 19. Core 1.1 预留接口

| 接口 | Core 1.1 默认实现 | 完整端云扩展 |
| --- | --- | --- |
| PlacementResolver | LocalPlacementResolver | Static / Policy / Resource-Aware Resolver |
| ExecutionBackend | LocalExecutionBackend | RemoteExecutionBackend / CloudExecutionBackend |
| TraceStore | LocalTraceStore | CloudTraceStore / DistributedTraceStore |
| EvolutionBackend | GenericAgentEvolutionBackend | Hermes / GEPA / Remote Evolution Service |
| CapabilityProvider | CLI / CLI-Anything / Workflow / Evolved Skill | HTTP / MCP / Remote Provider |
| ArtifactStore | LocalArtifactStore | Cloud/Object Storage + Edge Cache |

<a id="section-20"></a>

## 20. Hackathon 架构与完整 Agent 对照

| 模块 | Hackathon 推荐 | 完整 Agent |
| --- | --- | --- |
| 运行位置 | Core 共址 DGX Spark | Cloud Control + Multi Edge |
| CCCC | DGX 运行 | 可云化主控或混合部署 |
| Claude Code / Codex | Harness 与 DGX 共址或远程调用模型 | Cloud/Edge Agent Worker |
| GenericAgent | Evolution Worker | 可扩展多 Evolution Backend |
| Capability Runtime | Local | 统一跨 Local/Edge/Cloud |
| Placement | 固定 Local | 策略化/资源感知 |
| Trace | 本地 JSON/DB | 集中式 Trace/History |
| Sandbox | 本地 Docker | Cloud Sandbox / Eval Farm |
| MCP | 不实现 | 兼容 Adapter |
| 端云协同 | 不作为提交前置 | 完整实现 |

> **推荐工程顺序**
>
> Core First → Evolution Second → Distribution Last。先让 Agent 会做事，再让 Agent 学会进化，最后再决定这些能力运行在哪里。

<a id="section-21"></a>

## 21. Demo Story 与架构映射

| Demo Story | 展示链路 | 对应架构能力 |
| --- | --- | --- |
| From Idea to Prototype | 一句话 → GitHub/Lark/Draw.io/LibreOffice/FreeCAD | Capability Runtime + CLI-First + 通用性 |
| Learn to Do | Capability Gap → GenericAgent/Codex → Test → Register | Capability Evolution 0→1 |
| Learn to Do Faster | Trace → GenericAgent Optimize → Benchmark → Promote V2 | Performance Evolution 1→Better |
| Professional Software Reach | Prompt → cad.model.create → FreeCAD → 3D Artifact | CLI-Anything + Edge Execution |
| Future Edge-Cloud | Cloud Gateway → Placement → DGX/Cloud Execute | Deployment Extension |

<a id="section-22"></a>

## 22. 演进路线与最终定义

<a id="section-22-1"></a>

### 22.1 Phase 1：Core 1.1

- CCCC + Agent Team 基础编排。
- Capability Registry / Router / CLI Executor。
- gh、lark-cli、Draw.io、LibreOffice、FreeCAD。
- Observation、Trace、Metrics。
- DGX Spark 真机部署。

<a id="section-22-2"></a>

### 22.2 Phase 2：Evolution

- Evolution Controller。
- GenericAgent Evolution Backend。
- Capability Evolution 0→1。
- Performance Evolution 1→Better。
- Evaluation Harness 与 Version Registry。

<a id="section-22-3"></a>

### 22.3 Phase 3：Minimal Edge-Cloud

- Cloud Gateway。
- RemoteExecutionBackend。
- Static Placement。
- Cloud Trace 或 Cloud Sandbox 二选一优先落地。

<a id="section-22-4"></a>

### 22.4 Phase 4：Full Agent Platform

- Cloud Control Plane、Task Queue、Agent Registry。
- Capability Registry Master + Edge Cache。
- 动态 Placement Scheduler。
- Cloud Evolution Sandbox / Eval Farm。
- 多 Edge Node、多 Agent Backend、Canary 与 Rollback。
- MCP 生态兼容层。

<a id="section-22-5"></a>

### 22.5 最终技术定义

> **EvoCLI 完整架构**
>
> EvoCLI 是一个 CLI-First、Capability-Native、Self-Evolving 的通用 Agent Runtime。它通过 CCCC 编排 Claude Code、Codex、GenericAgent 和 Local LLM 等专业 Agent，以统一 Capability Runtime 操作真实软件；通过结构化 Observation 和 Trace 将执行结果变成可验证、可学习的经验；通过双轨 Self-Evolution 同时实现能力从 0→1 与性能从 1→Better；并通过标准 PlacementResolver、ExecutionBackend、TraceStore 和 EvolutionBackend 接口自然扩展到 Cloud / Edge / Local，形成完整的端云协同自进化 Agent 平台。

**One Agent. More Capabilities. Less Time.**

**一个 Agent，越用越会，越用越快。**
