# Screenshot-to-App MVP Worker

这是黑客松 Demo 中唯一需要交付的 Agent：`mvp-worker`。

它不负责选创意、不维护市场能力表，也不替 Foreman 做决策。它只接收一份 `mvp-contract.json` 和一张已获授权的截图，交付一个可本地运行并经浏览器验收的前端 MVP。

## Worker 的输入与输出

```text
Foreman（当前由 scripts/simulate_foreman.ps1 模拟）
  -> contracts/mvp-contract.json
  -> mvp-worker
  -> runs/<run-id>/
       input/reference.*
       ui-spec.json
       app/index.html
       app/styles.css
       app/app.js
       artifacts/preview.png
       artifacts/acceptance-report.json
       worker-delivery.json
```

截图中的品牌、Logo、商品图、价格和用户数据只能用于理解布局与交互意图。Worker 必须创建新的虚构产品及自制视觉资产，不能直接复制来源品牌。

## 现在如何模拟 Foreman

把一张截图保存到本机后运行：

```powershell
.\scripts\simulate_foreman.ps1 -Screenshot "C:\path\to\kfc-reference.png" -RunId "fastbite-001" -AppName "FastBite"
```

脚本会产生 `contracts/mvp-contract.json` 并创建本次 run 的目录。后续真正的 Foreman 只需写出同结构的契约文件，不需要改 Worker。
如果需要指定 Python，先设置 `$env:MVP_WORKER_PYTHON = "C:\path\to\python.exe"`；本机 Codex 的 bundled Python 会被自动识别。

## 在 CCCC 中接入 Worker

由团队的 Foreman 在自己的工作组中添加一个 actor：

```powershell
cccc actor add mvp-worker --runtime codex --scope "C:\Users\wanganxin\Documents\黑客松demo演示"
```

随后向 Worker 发送带回执任务，任务正文必须包含契约绝对路径：

```text
请执行 Screenshot-to-App Worker。
契约：C:\Users\wanganxin\Documents\黑客松demo演示\contracts\mvp-contract.json
完成条件：worker-delivery.json.status=PASS，并回传 preview.png、acceptance-report.json 的绝对路径。
```

Worker 的完整角色提示词在 [worker/ROLE.md](worker/ROLE.md)。

## Worker 的执行命令

Worker 先准备 run：

```powershell
python .\scripts\prepare_run.py --contract .\contracts\mvp-contract.json
```

然后根据截图和契约生成 `runs/<run-id>/app/index.html`、`styles.css`、`app.js`，并必须实现 `?qa=1` 的自检接口。

生成后运行真实浏览器验收与交付封装：

```powershell
python .\scripts\browser_acceptance.py --run-dir .\runs\fastbite-001
python .\scripts\finalize_delivery.py --run-dir .\runs\fastbite-001
```

`browser_acceptance.py` 使用本机 Edge/Chrome headless 打开真实本地页面、执行页面内的受控交互检查并生成 PNG。任何验收失败都必须以 `FAIL` 交付；Worker 最多修复一次后重跑全部检查。

## 今天的 P0

- 主案例：肯德基小程序截图 -> 虚构的 `FastBite` 点餐前端；
- 只做前端视觉、搜索/分类和“加入购物车”两个真实交互；
- 淘宝首页可作为同一 Worker 的第二次输入，输出虚构的 `MallLite`；
- 不做账号、支付、订单、真实商品、API、数据库或 GitHub 推送。
