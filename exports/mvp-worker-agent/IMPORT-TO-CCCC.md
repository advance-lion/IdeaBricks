# MVP Worker 导入说明

这个包只包含 Worker 身份和接入约定；不包含密钥、历史任务或运行产物。

## 导入到已有 CCCC Team

请由 Team 所有人在同一台运行 Worker 的机器上执行。`<GROUP_ID>` 是对方 Team 的 CCCC group id：

```powershell
cccc attach --group <GROUP_ID> "C:\Users\wanganxin\Documents\黑客松demo演示"

cccc actor update mvp-worker `
  --title "MVP Worker - Local VLM Screenshot to App" `
  --runtime codex `
  --command "codex -c shell_environment_policy.inherit=all --dangerously-bypass-approvals-and-sandbox --search" `
  --scope "C:\Users\wanganxin\Documents\黑客松demo演示" `
  --enabled 1 `
  --group <GROUP_ID>
```

若目标 Team 还没有 `mvp-worker`，把第二条替换为：

```powershell
cccc actor add mvp-worker `
  --title "MVP Worker - Local VLM Screenshot to App" `
  --runtime codex `
  --command "codex -c shell_environment_policy.inherit=all --dangerously-bypass-approvals-and-sandbox --search" `
  --scope "C:\Users\wanganxin\Documents\黑客松demo演示" `
  --group <GROUP_ID>
```

最后在当前项目创建 `config/cccc-team.local.json`：

```json
{ "group_id": "<GROUP_ID>" }
```

重启 `scripts/worker_intake_server.py`。之后本地 VLM/LLM 的真实阶段会同步进该 Team，供 Foreman 和运行舞台读取。
