# Testing

## What is it?

**End-to-end testing** for the agent system proves the *whole loop*: server +
agent + workflow + approvals + failures, running together the way they will in
production. It complements [15-testing](../15-testing/README.md), which tests
the server in isolation; here the *agent's behavior* is the subject.

## Why does MCP need it?

The end-to-end system is where integration bugs live: a workflow step that
misuses a validated output, an approval that never fires, a retry that loops
forever, a shutdown that hangs. Each of those is invisible to server-only tests
— they only appear when the agent actually drives the server.

## How it works — what to test

1. **Happy-path workflow**: the agent completes the full multi-step workflow and
   the final state is correct (create → ship → confirmed).
2. **Output validation**: a step that receives malformed output fails safely
   (no downstream call with garbage).
3. **Approval paths**: the approved path proceeds; the rejected path cancels
   cleanly — and both are audited
   ([14-security/auditability.md](../14-security/auditability.md)).
4. **Failure + recovery**: a flaky tool is retried and the workflow completes;
   a hard failure aborts the workflow with a useful error.
5. **Progress/long operations**: progress notifications arrive and (where
   supported) cancellation works.
6. **Metrics**: the agent reports latency and success rate; tests assert the
   expected counts (e.g., 3 retries → success rate reflects it).
7. **Graceful shutdown**: ending the session terminates the server subprocess
   cleanly.

## Example shape

```python
import pytest
from fastmcp import Client
from agent import run_order_workflow       # the agent under test

@pytest.mark.asyncio
async def test_full_workflow_with_approval():
    decisions = {"ship_order": True}       # inject the human's decisions
    async with Client("agent_server.py", elicitation_handler=make_user(decisions)) as client:
        report = await run_order_workflow(client, "widget", 2)
    assert report["status"] == "shipped"
    assert report["steps"] == ["create_order", "ship_order"]
    assert report["success_rate"] == 1.0

@pytest.mark.asyncio
async def test_rejected_approval_cancels():
    decisions = {"ship_order": False}
    async with Client("agent_server.py", elicitation_handler=make_user(decisions)) as client:
        report = await run_order_workflow(client, "widget", 2)
    assert report["status"] == "cancelled"
    assert report["reason"] == "user declined"
```

## MCP-specific behavior

- **Inject decisions, don't simulate the user in tests**: the elicitation
  handler is the seam — tests control it
  ([06-agent-interaction/elicitation.md](../06-agent-interaction/elicitation.md)).
- The same client API the production agent uses *is* the test API — no test
  double for the protocol.
- Assert on the **agent's report** (steps, latency, success rate, final state),
  not internal variables — the report is the observable contract.

## Industry-standard pattern

**Workflow-level tests with injected dependencies**: the agent takes its
"external" inputs (approvals, failures) as injectable seams, so every path —
happy, rejected, failed, retried — is a deterministic test case. Run them in CI
against the real server binary.

## Common mistakes

- Testing the workflow with the LLM in the loop — nondeterministic and slow;
  script the decisions.
- Testing the happy path only — the approval-rejection and retry paths are the
  ones that break in production.
- Asserting on log text instead of structured report fields.

## Related

- [architecture.md](architecture.md)
- [implementation.md](implementation.md)
- [15-testing/README.md](../15-testing/README.md)
- [examples/test_agent.py](examples/test_agent.py)
