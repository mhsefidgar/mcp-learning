# Concurrency Limits, Worker Pools & Async Execution

## What is it?

Bounding and organizing **how much work runs at once** on an MCP server:

- **Concurrent tool calls**: multiple `tools/call` requests in flight
  (MCP supports this on one connection; agents do it constantly).
- **Concurrency limits**: a cap on in-flight operations (semaphore) so a burst
  can't exhaust threads/tasks/memory.
- **Worker pools**: a fixed set of workers executing tasks from a queue — bounded
  concurrency with a bounded backlog.
- **Async task execution**: long work moved off the request path into background
  tasks ([04-tool-engineering/long-running-operations.md](../04-tool-engineering/long-running-operations.md)).

## Why does MCP need it?

Agents are bursty: one model turn can fire dozens of parallel tool calls
([tool-fan-out](large-data-at-scale.md)). An unbounded server spawns a thread/task
per call → memory blows up, downstreams get pounded, and latency degrades for
everyone. Bounded concurrency keeps the server in its stable region — the same
problem as [08-reliability-resilience/backpressure.md](../08-reliability-resilience/backpressure.md),
seen from the execution side.

## How does it work?

1. **Measure first** (load testing, [load-and-performance-testing.md](load-and-performance-testing.md)):
   what concurrency can this box actually sustain?
2. **Cap in-flight work** with a semaphore/worker pool sized to that number.
3. **Queue the rest** with a bounded queue; when full, signal backpressure
   (busy error, [08-reliability-resilience/backpressure.md](../08-reliability-resilience/backpressure.md)).
4. **Separate pools per workload class** (bulkheads — heavy render vs. light reads)
   ([08-reliability-resilience/bulkheads.md](../08-reliability-resilience/bulkheads.md)).
5. **Long work → background tasks** with job ids, not long-held requests
   ([04-tool-engineering/long-running-operations.md](../04-tool-engineering/long-running-operations.md)).

## Mental model

The server is a **restaurant kitchen**: the pass (concurrency limit) has a fixed
number of plates, the ticket rail (queue) holds the backlog, and different stations
(worker pools) handle different dishes. When the rail is full, the maître d'
(backpressure) tells new customers to wait — the kitchen never collapses into chaos.

## MCP-specific behavior

- **MCP allows many concurrent requests per connection** — the protocol doesn't
  serialize tool calls; your server's concurrency model decides.
- **stdio servers** are one-client — but one agent can still burst dozens of
  parallel calls; limits still apply.
- **Server→client requests** (elicitation/sampling) also consume workers — count
  them in the pool.

## Example

Bounded concurrency (asyncio semaphore) — verified pattern:

```python
import asyncio
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("bounded")
_slots = asyncio.Semaphore(8)          # at most 8 tool executions at once

@mcp.tool
async def work(payload: str) -> str:
    """Bounded-concurrency tool. 8 max in flight; others queue or get busy."""
    if _slots.locked():
        raise ToolError("server busy — retry shortly")    # backpressure signal
    async with _slots:
        await asyncio.sleep(0.05)
        return f"done: {payload}"
```

Worker-pool pattern (queue + workers) is shown in Go in `repository/go/resilience`.

## Industry-standard pattern

Bounded concurrency + worker pools + queues is universal (thread pools, executors,
Celery/Redis queues, Kubernetes pod limits). Rules: **size from measurements**, not
guesses; **bound the queue**; **isolate workloads** (bulkheads); **expose queue
depth and pool utilization as metrics**
([09-observability-telemetry/metrics.md](../09-observability-telemetry/metrics.md)).

## Common mistakes

- **No limits** — a 50-call burst spawns 50 threads, then 500.
- **Limits but unbounded queues** — memory grows instead of threads.
- **Blocking calls inside async handlers** — sync I/O in an async server stalls the
  loop; use `run_in_executor` or async libraries.
- **One pool for everything** — a heavy tool starves light ones
  ([bulkheads](../08-reliability-resilience/bulkheads.md)).
- **Sizing from intuition** — 8 workers is a guess until load tests say so.

## Testing

- **Concurrency-limit tests**: N parallel calls obey the cap
  ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **Queue tests**: backlog stays bounded under overload.
- **Throughput tests**: pooled vs. unpooled throughput at the same concurrency.
- **Worker-pool tests**: tasks complete in order, workers recycle cleanly.

## Security considerations

- **Unbounded concurrency is a DoS hole** — limits are a security control, not just
  performance.
- **Per-tenant pools** prevent one tenant's burst from starving others.

## Related

- [08-reliability-resilience/backpressure.md](../08-reliability-resilience/backpressure.md)
- [08-reliability-resilience/bulkheads.md](../08-reliability-resilience/bulkheads.md)
- [04-tool-engineering/long-running-operations.md](../04-tool-engineering/long-running-operations.md)
- [load-and-performance-testing.md](load-and-performance-testing.md)