# Timeouts

> **General engineering pattern.** Timeouts are not an MCP protocol feature. The
> protocol has no timeout field; you set timeouts in your client calls, your server
> handlers, and your downstream calls.

## What is it?

A **timeout** is a bound on how long an operation may take before it is abandoned:
the client stops waiting, or the server stops working. A **deadline** is the
absolute time by which an operation must finish (often with a timeout chain:
each hop gets a slice of the remaining budget).

## Why does MCP need it?

Without timeouts, one slow tool call **hangs the whole agent**: the model waits, the
user waits, the connection accumulates in-flight requests, and threads/tasks pile up
([08-reliability-resilience/backpressure.md](../08-reliability-resilience/backpressure.md)).
Timeouts are how failures become *bounded*: the worst case is "it took 30 seconds
and returned a timeout error", not "it hung forever". They are the first line of
defense against slow downstream APIs, deadlocks, and buggy code.

## How does it work?

1. **Pick a timeout budget per operation** (e.g. client `call_tool` timeout = 30s).
2. **Set the timeout** where the operation is bounded:
   - *Client side*: `client.call_tool(..., timeout=30)` / TS `client.callTool(..., {timeout})`.
   - *Server side*: a per-tool timeout (FastMCP `timeout=` on tool registration or a
     handler-level `asyncio.wait_for`); a deadline propagated into downstream calls.
3. **On expiry, fail cleanly**: raise/cancel, return a timeout error the model
   understands ("timed out after 30s — try again with fewer items").
4. **Clean up**: cancel the underlying work so it doesn't keep running in the
   background ([cancellation.md](cancellation.md)).

## Mental model

A timeout is a **deadline you set before starting**: "I'll wait until 12:00:30, then
I leave." Deadlines are the *same idea composable across hops*: the whole trip has a
deadline, and each leg gets a slice. Timeout thinking is "worst-case budgeting" —
decide the worst acceptable wait up front.

## MCP-specific behavior

- **The client's `call_tool` timeout** bounds waiting for a *response* — but
  remember: with progress notifications flowing, some clients treat the connection
  as alive. Decide whether your timeout is "no response at all" or "no progress at
  all".
- **The server's per-tool timeout** bounds *execution*. FastMCP supports a
  `timeout` on tool registration; TS/Java SDKs support per-call timeouts client-side
  and cancellation server-side.
- **Timeouts interact with long operations**: a long-running design
  ([long-running-operations.md](long-running-operations.md)) deliberately returns
  fast and tracks work by job id — never fight long work with a huge timeout.

## Example

Client-side (FastMCP `Client` supports `timeout` on `call_tool`):

```python
from fastmcp import Client

async def main() -> None:
    async with Client("server.py") as client:
        try:
            result = await client.call_tool("render", {"frames": 500}, timeout=30)
        except TimeoutError:
            # The model can recover: suggest a smaller job or the job-based API.
            print("timed out — offer start_render_job instead")
```

Server-side (bounded handler with `asyncio.wait_for`):

```python
import asyncio
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("renderer")

@mcp.tool
async def render(scene: str, frames: int) -> str:
    """Render frames. Fails cleanly if it exceeds 60s."""
    try:
        return await asyncio.wait_for(_do_render(scene, frames), timeout=60)
    except asyncio.TimeoutError:
        raise ToolError("render timed out after 60s — reduce frames or use the job API")
```

## Industry-standard pattern

Timeouts, deadlines, and timeout chains are standard in every distributed system
(gRPC deadlines, HTTP client timeouts, database statement timeouts, cloud SDKs).
The production rules: **always have one, chain them (each hop gets a slice), fail
cleanly with an actionable message, and cancel the underlying work on expiry.**

## Common mistakes

- **No timeout at all** — the classic hang.
- **Timeouts that are too long** — a 10-minute timeout is a hang with extra steps.
- **Setting a timeout but not cancelling the work** — the caller moves on, the
  server keeps burning compute.
- **Nested waits with no chain** — each hop resets the clock instead of sharing a
  deadline; the total far exceeds the intent.
- **Catching TimeoutError and swallowing it** — the caller thinks it succeeded.

## Testing

- **Timeout tests**: a handler that sleeps longer than the timeout → clean timeout
  error within the bound ([15-testing/failure-testing.md](../15-testing/failure-testing.md)).
- **Deadline-chain tests**: a slow downstream call fails the whole chain at the
  shared deadline.
- **Cleanup tests**: after a timeout, no background work continues.
- **Boundary tests**: work finishing just under the timeout succeeds.

## Debugging

- A client that hangs → check whether *any* timeout is set, then whether the
  timeout is measured on "no response" or "no progress".
- A server with leaked background work after timeouts → handlers aren't cancelling
  the underlying task.

## Security considerations

- **Timeouts are a DoS control**: unbounded work lets one caller tie up server
  resources; per-call timeouts bound the damage.
- **Timeout errors should not reveal internals** ("operation took too long" is
  enough; the reason belongs in logs).

## Related concepts

- [cancellation.md](cancellation.md)
- [long-running-operations.md](long-running-operations.md)
- [retries.md](retries.md)
- [08-reliability-resilience/README.md](../08-reliability-resilience/README.md)