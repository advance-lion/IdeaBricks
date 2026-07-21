# 截图生成应用：录制脚本

## 录制时展示的证据

1. CCCC 的 `mvp-worker` 终端，以及两张已授权的参考截图。
2. Foreman 交给 Worker 的批次契约：`contracts/screenshot-to-app-recording-001/demo-batch.json`。
3. 中文阶段日志：视觉理解 → 前端脚手架 → 浏览器验收 → 交付封装。
4. FastBite 与 MallLite 的源码、浏览器预览图、验收报告和 `worker-delivery.json`。
5. 本地 Git 提交；没有明确仓库与授权时不创建或推送 GitHub。

## 高保真界面复刻原则

Worker 优先复刻截图的空间结构，而非做抽象风格改版：保留首屏节奏、区块顺序、组件尺寸、主色块、信息密度、导航位置、弹层打开态和交互入口；替换品牌、Logo、商品摄影、商品名称、价格、原文案与用户数据。这样演示能直观证明“截图变可运行应用”，同时不把来源品牌内容带入交付物。

## 现场演示 MallLite

MallLite 已作为淘宝端参考截图的虚构重设计完成，当前本地预览地址：

```text
http://127.0.0.1:4174/index.html
```

现场可点击频道、在搜索框输入“键盘”或“夜灯”，再点击商品卡右下角 `＋`，购物袋数字会实时更新。

## 中文日志

在另一个终端中执行：

```powershell
Get-Content -Encoding UTF8 .\runs\screenshot-to-app-recording-001\worker-progress.jsonl -Wait
```

日志由 Worker 的每一个真实阶段写入。`worker-progress.py` 的 `--message-key` 采用内置中文消息，规避 Windows 命令行传入中文参数时的编码问题。

## 再跑一次浏览器验收

```powershell
.\scripts\python.cmd scripts\browser_acceptance.py --run-dir .\runs\screenshot-to-app-recording-001-malllite
.\scripts\python.cmd scripts\finalize_delivery.py --run-dir .\runs\screenshot-to-app-recording-001-malllite
```

## 用一张新截图做真实试跑

优先使用浏览器投递台，不需要终端拖入路径：

```powershell
.\scripts\python.cmd scripts\worker_intake_server.py
```

打开 `http://127.0.0.1:4181`，直接拖入图片或点击选择图片；勾选“立即发送到 CCCC Worker”后创建试跑。页面会显示每次 run 的预览图、验收报告和交付回执。

每个完成的 run 还会直接显示四个交付入口：`运行网页`（真实生成前端）、`预览图`、`验收`、`回执`；页面顶部固定提供 `CCCC GUI` 和 `仓库状态`。GitHub 只有在团队显式配置远程仓库并授权推送后才显示真实链接。

如需没有浏览器时的备用方式，再将图片拖到 PowerShell 窗口获取其绝对路径，并运行：

```powershell
.\scripts\intake_screenshot.ps1 `
  -Screenshot "C:\path\to\your-reference.jpg" `
  -AppName "SparkMVP" `
  -Dispatch
```

它会创建独立的 `runs/trial-<时间戳>/`，启动 CCCC 的 `mvp-worker` 并下发契约。观察 CCCC 终端，或在第二个 PowerShell 窗口运行：

```powershell
[Console]::OutputEncoding = [Text.UTF8Encoding]::new()
Get-Content -Encoding UTF8 .\runs\live-trials\worker-progress.jsonl -Wait
```

## 重新派发真实 Worker

```powershell
.\scripts\send_recording_task.ps1 -Batch .\contracts\screenshot-to-app-recording-001\demo-batch.json -GroupId g_c3e3880e9f6c
```

Worker 的角色提示词在 `worker/ROLE.md`。真实 Foreman 准备好后，将这个 Worker 加入其 CCCC 工作组，并只交付相同结构的 `mvp-contract.json` 或 `demo-batch.json`。
