# DGX Spark test run

The DGX Spark host is the runtime of record for the Worker: its local VLM/LLM receives the screenshot and produces the frontend. Codex CLI is optional. Claude Code is only an explicit fallback, recorded in each run's evidence.

The supplied test ZIP omits previous runs and tool caches, but retains the persistent CLI snapshot, raw catalog provenance, and the two authorized reference screenshots used by the demo controls. It is therefore self-contained for a normal demo run; use the full repository only when you need to refresh catalog maintenance data.

## 1. Check the host

```bash
python3 --version
node --version
claude --version                 # optional fallback; Codex is not required
curl http://127.0.0.1:8000/v1/models
nvidia-smi
```

If the model server is on another host or port, use that URL in the next step. The configured model must support both OpenAI-compatible chat completions and image input for the visual stage.

## 2. Configure the local model

```bash
cp config/local-model.example.json config/local-model.local.json
```

Set `base_url`, `api_key` when needed, and `model` in `config/local-model.local.json`. Do not put secrets in Git or the demo video.

If a local-only `config/worker-test-mode.local.json` exists, remove it or leave `force_backend` empty. That file is intentionally excluded from the test ZIP because a forced `codex` setting would hide the DGX local-model path.

The tracked runtime policy is:

```json
{
  "backend": "local-openai",
  "fallback_order": ["codex", "claude"]
}
```

On a Spark with no Codex but with Claude Code, the effective fallback is automatically `claude`. With a healthy local service, neither CLI is called.

## 3. Validate before recording

```bash
export FORGE_RUNTIME_LABEL='DGX Spark'
export MVP_WORKER_BACKEND='local-openai'
python3 -m py_compile scripts/worker_pipeline.py scripts/worker_intake_server.py scripts/run_incubation_pipeline.py
python3 scripts/worker_intake_server.py --port 4181
```

The intake server binds to loopback. From your laptop, create an SSH tunnel and open `http://127.0.0.1:4181/` locally:

```bash
ssh -L 4181:127.0.0.1:4181 <user>@<dgx-spark-host>
```

The full interactive intake path also expects the project's CCCC runtime. For an isolated Worker test, prepare a valid contract with `scripts/prepare_run.py`, then run `scripts/worker_pipeline.py --contract <contract> --backend local-openai` directly.

## 4. Evidence to capture

For the same `run_id`, preserve these files from the Spark host:

- `runs/<run_id>/run-execution.json` — requested and active engine; fallback chain if any.
- `runs/<run_id>/worker-pipeline.log` — model-stage timings and phase progress.
- `runs/<run_id>/local-vlm-response.txt` and `local-code-response.txt` — local-model output evidence.
- `runs/<run_id>/artifacts/acceptance-report.json` and `worker-delivery.json` — browser QA and delivery.

At the end of the video, show the matching `run_id`, model-service terminal output, and `nvidia-smi`. If `run-execution.json` says `Claude Code 兜底`, say so plainly; do not describe that run as local DGX inference.
