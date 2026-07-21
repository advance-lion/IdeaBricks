# 确定性 Worker Pipeline

`scripts/worker_pipeline.py` 负责推进每一次 Screenshot-to-App run：

```text
视觉规格 → 前端脚手架 → Edge 浏览器验收 → 交付回执 → 本地 Git 提交
```

每个阶段都会写入 `runs/<batch>/worker-progress.jsonl` 和 `runs/<run-id>/worker-pipeline.log`。任一阶段失败会以 `FAIL` 结束，不会无限停留在“处理中”。CCCC 保留为任务和运行日志的可视化层，不负责阶段推进。

当前默认后端是 `template`：这是上传、契约、页面、浏览器验收和交付的稳定性基线。它不宣称已经理解任意截图。接入本地 VLM 后，将视觉规格生成器替换为 `截图 → ui-spec.json`；DGX Spark 的文本代码模型再使用 `ui-spec.json` 生成页面，之后的验收与交付逻辑保持不变。

本地模型配置模板见 `config/local-model.example.json`。真实配置写入被 Git 忽略的 `config/local-model.local.json`。
