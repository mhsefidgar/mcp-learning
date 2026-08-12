# Long-Running Operations

## What is it?

A **long-running operation** is a tool call that takes far longer than a normal
request — minutes or hours instead of milliseconds: a training job, a data pipeline,
a bulk migration, a deployment. Long operations raise a fundamental problem: **the
request/response model assumes the answer comes back on the same connection, in
bounded time.**

## Why does MCP need it?

Agents legitimately trigger long work (deploy, migrate, render, crawl), and a naive
implementation has three failure modes:

1. **Timeout death**: the client times out and the server keeps working — orphaned.
2. **Connection coupling**: the operation dies with the connection.
3. **Opacity**: nobody knows the job's status once the call ended.

Long-running operations need a design that *decouples* the work from the request
lifetime: **start a job, poll its status, and report progress along the way**.

## How does it work?

The standard pattern (job/task pattern):

1. **Start**: `start_migration(kind, options)` returns immediately with a
   `job_id` + `status: "queued"`.
2. **Track**: the server runs the job in the background (its own task queue —
   see [10-scaling-performance/queue-based-execution.md](../10-scaling-performance/queue-based-execution.md)).
3. **Poll**: `get_job(job_id)` returns `{status, progress, result?, error?}` — the
   model calls this as needed.
4. **Notify (optional)**: progress notifications while the caller is still
   connected ([progress.md](progress.md)).
5. **Finish**: the job lands in a terminal state (`completed`/`failed`) with a
   result the model can fetch.

```
start_migration → {job_id: "j-42", status: "queued"}
get_job("j-42")  → {status: "running", progress: 0.4}
get_job("j-42")  → {status: "completed", result: {...}}
```

## Mental model

Long operations are **restaurant takeout vs. dining in**: instead of waiting at the
table (holding the connection), you order (start), get a receipt number (job_id),
check back (poll), and pick up when ready. The receipt decouples you from the
kitchen — you can leave and come back.

## MCP-specific behavior

- **The stable MCP protocol has no built-in long-running-operation method** — no
  `jobs/start`. You design it with tools. (The **Tasks extension** in the 2026-07-28
  spec formalizes this: `tasks/get`, `tasks/update`, `tasks/cancel` — see
  [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md).)
- **Progress tokens still work during the initial call**, but once the call
  returns, progress is via polling.
- **Cancellation** of a background job is *your* tool (`cancel_job(job_id)`) — the
  protocol's `notifications/cancelled` only covers the in-flight call
  ([cancellation.md](cancellation.md)).
- **FastMCP** (and the modern SDKs) support background tasks on the server; check
  your SDK's task support ([12-fastmcp/README.md](../12-fastmcp/README.md)).

## Example

A minimal job-tracking design:

```python
import asyncio, uuid
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("jobs")
jobs: dict[str, dict] = {}

@mcp.tool
async def start_migration(kind: str) -> dict:
    """Start a background migration. Returns {job_id, status}."""
    job_id = uuid.uuid4().hex
    jobs[job_id] = {"status": "queued", "progress": 0.0, "result": None}
    asyncio.create_task(_run_migration(job_id, kind))   # background worker
    return {"job_id": job_id, "status": "queued"}

@mcp.tool
def get_job(job_id: str) -> dict:
    """Poll a job: {status, progress, result?, error?}."""
    job = jobs.get(job_id)
    if job is None:
        raise ToolError(f"Unknown job {job_id}")
    return job

@mcp.tool
def cancel_job(job_id: str) -> dict:
    """Cancel a queued or running job."""
    job = jobs.get(job_id)
    if job is None:
        raise ToolError(f"Unknown job {job_id}")
    job["status"] = "cancelled"
    return job

async def _run_migration(job_id: str, kind: str) -> None:
    job = jobs[job_id]
    job["status"] = "running"
    for i in range(1, 11):
        await asyncio.sleep(0.1)
        if job["status"] == "cancelled":
            return
        job["progress"] = i / 10
    job["status"] = "completed"
    job["result"] = {"migrated": kind, "rows": 1000}
```

## Industry-standard pattern

This is the **asynchronous job pattern** used by every serious platform: cloud
operations (AWS `createStack` → `describeStacks`), CI pipelines, payment intents,
map-reduce. The rules: return a job id fast, persist job state durably, make
`get_job` cheap, define terminal states, and clean up old jobs (TTL).

## Common mistakes

- **Holding the connection for the whole operation** — timeouts kill the work or
  the client hangs.
- **In-memory job state only** — jobs vanish on restart; persist them
  ([08-reliability-resilience/session-recovery.md](../08-reliability-resilience/session-recovery.md)).
- **No terminal-state discipline** — jobs stuck in "running" forever; add
  timeouts/deadlines.
- **Job ids that leak internals** — opaque ids, not sequential counters.
- **Polling abuse** — clients hammering `get_job`; add rate limits or push
  notifications where supported.

## Testing

- **Lifecycle tests**: queued → running → completed with correct state transitions
  ([15-testing/failure-testing.md](../15-testing/failure-testing.md)).
- **Failure tests**: a job that errors lands in `failed` with an error field.
- **Cancel tests**: cancelling stops the work and the job reports `cancelled`.
- **Restart tests**: jobs survive a server restart (with a durable store).
- **Poll tests**: `get_job` is stable and cheap.

## Debugging

- "Job disappeared" → in-memory state lost on restart.
- "Job never finishes" → check for swallowed exceptions in the background worker
  (log everything).
- Trace job lifecycle across logs with the job_id as the correlation key
  ([09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md)).

## Security considerations

- **Background jobs run with the server's permissions** — authorize *who* can start
  a job, and never let job parameters reach privileged operations unvalidated.
- **Job results may hold sensitive data** — protect `get_job` with the same
  authorization as the operation itself.
- **Job floods are a DoS vector** — per-client job quotas
  ([10-scaling-performance/per-client-quotas.md](../10-scaling-performance/per-client-quotas.md)).

## Related concepts

- [progress.md](progress.md) · [cancellation.md](cancellation.md)
- [timeouts.md](timeouts.md)
- [10-scaling-performance/queue-based-execution.md](../10-scaling-performance/queue-based-execution.md)
- [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md) (Tasks extension)