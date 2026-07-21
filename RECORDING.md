# 截图生成应用：录制脚本

## 录制时展示的证据

1. CCCC 的 `mvp-worker` 终端，以及两张已授权的参考截图。
2. Foreman 交给 Worker 的批次契约：`contracts/screenshot-to-app-recording-001/demo-batch.json`。
3. 中文阶段日志：视觉理解 → 前端脚手架 → 浏览器验收 → 交付封装。
4. FastBite 与 MallLite 的源码、浏览器预览图、验收报告和 `worker-delivery.json`。
5. 本地 Git 提交；没有明确仓库与授权时不创建或推送 GitHub。

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

## 重新派发真实 Worker

```powershell
.\scripts\send_recording_task.ps1 -Batch .\contracts\screenshot-to-app-recording-001\demo-batch.json -GroupId g_c3e3880e9f6c
```

Worker 的角色提示词在 `worker/ROLE.md`。真实 Foreman 准备好后，将这个 Worker 加入其 CCCC 工作组，并只交付相同结构的 `mvp-contract.json` 或 `demo-batch.json`。
