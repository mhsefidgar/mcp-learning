# Backpressure

> **General engineering pattern.** Backpressure is not an MCP protocol feature. It's
> how you keep a server alive when producers (agents) outpace consumers (your tool
> implementations).

## What is it?

**Backpressure** is signaling a producer to slow down when a consumer can't keep up —
instead of letting work pile up until something breaks. In MCP terms: when too many
tool calls arrive for the server's capacity, the server signals "slow down" rather
than queueing unboundedly (memory blowup) or dropping silently (data loss).

## Why does MCP need it?

Agents fire bursts. A model that decides to call 50 tools in parallel against a
server with 10 worker slots will, without backpressure, either:
- queue 40 requests (memory grows until OOM), or
- spawn unlimited workers (threads/connections exhausted, downstream pounded).

Backpressure keeps the system in the **stable region**: requests flow at the rate
the server can actually handle.

## How does it work?

1. **Bound the queue**: a fixed-size queue of pending tool calls.
2. **When full, signal**: return a *slow-down* error ("server busy, retry later")
   instead of accepting more work.
3. **The client honors it**: sees the signal, backs off (its retry stack does the
   rest — [04-tool-engineering/retries.md](../04-tool-engineering/retries.md)).
4. **Alternative: limit concurrency**: a semaphore caps in-flight operations; extra
   requests wait (bounded wait) or fail fast
   ([10-scaling-performance/concurrency-limits.md](../10-scaling-performance/concurrency-limits.md)).

## Mental model

Backpressure is **the queue at a checkout counter**: when the line is full, new
customers are told "come back in 10 minutes" instead of being allowed to stand in an
endless queue. The store never runs out of floor space, and nobody's order is lost
to a stampede — they just try again later.

## MCP-specific behavior

- **Nothing protocol-level.** The signal is an ordinary error result the model can
  read and act on.
- **In-flight concurrency is transport-level**: HTTP servers manage connection
  limits; stdio is one client per process. Both still need worker/semaphore bounds.
- **The 2026-07-28 spec's stateless model helps**: requests can be shed at any
  instance with no session state to worry about
  ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).

## Example

Bounded concurrency with a semaphore (FastMCP server):

```python
import asyncio
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("workers")

_slots = asyncio.Semaphore(4)  # at most 4 tool calls running at once

@mcp.tool
async def heavy_work(payload: str) -> str:
    """A CPU/IO-heavy operation. Server-limited to 4 concurrent calls."""
    if _slots.locked():
        raise ToolError("server busy — retry shortly")   # backpressure signal
    async with _slots:
        await asyncio.sleep(0.1)
        return f"processed {payload}"
```

## Industry-standard pattern

Backpressure is a first-class concept in **TCP flow control, message queues
(RabbitMQ prefetch, Kafka quotas), and reactive streams (Reactive Streams
specification — Java MCP SDK's reactor core is built on it)**. The design rules:
bound the queue, signal explicitly, honor the signal upstream, and never let the
queue grow unbounded.

## Common mistakes

- **Unbounded queues** — memory growth until OOM.
- **Dropping silently** — the client thinks work happened.
- **No signal the model understands** — a cryptic error leads to instant retry
  loops.
- **Blocking the whole server** — backpressure that stalls unrelated requests;
  scope it per-tool/per-client.
- **Ignoring it client-side** — the client must treat "busy" as retry-with-backoff,
  not as "try again right now".

## Testing

- **Overload tests**: fire more concurrent calls than capacity; assert defined
  slow-down behavior and no crash ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **Memory tests**: queue size stays bounded under sustained overload.
- **Recovery tests**: after the burst, normal throughput resumes.

## Security considerations

- **Backpressure is a DoS defense**: bounded queues prevent memory-exhaustion
  attacks.
- **The busy signal shouldn't leak internals** (capacity, queue depth) if that
  information is sensitive.

## Related

- [rate-limiting.md](rate-limiting.md) — admission control from the other side
- [bulkheads.md](bulkheads.md) — scoping limits so one tool can't starve others
- [10-scaling-performance/concurrency-limits.md](../10-scaling-performance/concurrency-limits.md)
- [04-tool-engineering/timeouts.md](../04-tool-engineering/timeouts.md)