# 16 — End-to-end examples

**`agent_server.py`** — an order-processing MCP server: tools
(`create_order`, `get_order`, `ship_order`, `flaky_lookup`), a resource
template (`orders://{order_id}`), a prompt, validation + `ToolError`s,
progress reporting, and an approval elicitation on the destructive step.

**`agent.py`** — a scripted agent (no LLM, fully deterministic) that drives
the whole loop: discovers capabilities and schemas, chains validated outputs,
retries flaky failures with backoff, asks the human before shipping, reads a
resource template, logs every step, and produces a `WorkflowReport` with
latency, retries, status, and success rate. `python agent.py` runs two
workflows — one approved, one declined.

**`test_agent.py`** — 7 end-to-end tests: happy-path workflow, rejected
approval, output validation, deterministic retries, progress notifications,
graceful shutdown, and server-side argument validation.

```bash
python agent.py                  # run the agent demo
pytest test_agent.py -q          # or: ../../.venv/Scripts/python.exe -m pytest ...
```

**Design notes worth stealing**

- The agent validates **every tool output before chaining it** (the
  `_validate_order_output` gate) — tool output is data, not truth.
- The human's decisions are injected via the elicitation handler, so the
  workflow is deterministic and testable
  ([16-end-to-end/testing.md](../testing.md)).
- The flaky tool fails *deterministically* twice per order, so the retry path
  is always exercised and never flakes.
- The agent's report is its observable contract — tests assert on the report,
  not internal variables.
