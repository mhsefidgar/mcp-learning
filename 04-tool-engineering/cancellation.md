# Cancellation

## What is it?

**Cancellation** is stopping an in-flight operation before it completes — because the
user changed their mind, the model moved on, or a deadline passed. In MCP, the
protocol-level mechanism is the **`notifications/cancelled`** notification, which
carries the `requestId` of the request being abandoned:

```
client ──► server   tools/call {id: 7, ...}          (long operation starts)
client ──► server   notifications/cancelled {requestId: 7, reason: "user aborted"}
server  ──► client  tools/call response {id: 7, error: cancelled}   (still answered!)
```

## Why does MCP need it?

Models start long operations (renders, searches, code runs, batch jobs) and then
decide they don't need the result. Without cancellation, the server burns compute on
work nobody wants, and its resources fill up with abandoned tasks
([08-reliability-resilience/backpressure.md](../08-reliability-resilience/backpressure.md)).
Cancellation is also a **cost control**: long-running operations cost money, and
cancelling them is the protocol's "stop the meter."

## How does it work?

1. A request with a long operation starts; the client tracks its `id`.
2. The client sends `notifications/cancelled` with `requestId` (and optional
   `reason`).
3. The server cooperatively checks cancellation in its work loop (see below) and
   stops.
4. **The original request still gets a response** — a cancellation error — so the
   client's pending future resolves. Cancellation is a *notification*: it has no
   response of its own.

Crucially, cancellation in any real system is **cooperative**: the server must check
for cancellation between steps. You cannot forcibly kill a running tool call from
outside (that would corrupt state); you ask it to stop, and it stops at a safe point.

## Mental model

Cancellation is **raising your hand to the waiter mid-meal**: the kitchen doesn't
magically stop the dish — the waiter carries the message, and the kitchen stops at a
safe point (between courses, not mid-plate). The meal (the request) still gets
"closed out" with a final answer (the cancellation error).

## MCP-specific behavior

- **`notifications/cancelled` is protocol-defined** (with `requestId` and optional
  `reason`) — this is one of the few *true* MCP protocol features in this section.
- **Both sides can cancel**: a client can cancel a `tools/call`; a server can cancel
  a `sampling/createMessage` it asked the client for.
- **Cancellation is advisory at the wire level**: the protocol asks; the
  implementation honors it. A malicious/buggy server may ignore it — don't rely on
  cancellation for safety.
- **Progress tokens + cancellation**: cancelled requests may still have emitted
  progress notifications; the client should tolerate that.

## Example

FastMCP — async tools honour cancellation via asyncio; a sleep or await is a
cancellation point:

```python
import asyncio
from fastmcp import FastMCP, Context

mcp = FastMCP("renderer")

@mcp.tool
async def render(scene: str, frames: int, ctx: Context) -> str:
    """Render a scene frame by frame. Cancellable between frames."""
    for i in range(frames):
        # asyncio.sleep is a cooperative cancellation point: a cancelled task
        # raises CancelledError here and stops cleanly.
        await asyncio.sleep(0.1)
        await ctx.report_progress(i + 1, frames)
    return f"Rendered {frames} frames of {scene}"
```

Long CPU-bound work needs explicit checks (a `CancelledError` is raised at the
next `await` — if your loop never awaits, it can't be cancelled):

```python
@mcp.tool
async def crunch(n: int, ctx: Context) -> int:
    """CPU-bound work with cooperative cancellation checks."""
    total = 0
    for i in range(n):
        if ctx.is_cancelled():          # framework-provided check
            raise asyncio.CancelledError("cancelled by client")
        total += i * i
    return total
```

## Industry-standard pattern

Cooperative cancellation is the model behind **asyncio cancellation, goroutine
contexts, HTTP request cancellation, and gRPC cancellation**: a signal propagates,
and work stops at safe points. The engineering rules: check often, stop fast, clean
up resources (finally blocks), and never swallow the cancellation signal.

## Common mistakes

- **Ignoring cancellation** — work continues after the client gave up (wasted
  compute, locks held).
- **Swallowing `CancelledError`** — catching it and continuing ruins the client's
  expectation that the request is dead.
- **Not responding to the original request** — the client's pending future hangs
  forever. Always answer the cancelled request with a cancellation error.
- **Cancellation without cleanup** — releasing locks/connections in a `finally`, not
  only on success.
- **Retrying cancelled work** — cancellation is final ([retries.md](retries.md)).

## Testing

- **Cancellation tests**: start a long call, cancel it, assert (a) the client got a
  cancellation error, (b) the server stopped work promptly, (c) resources were
  cleaned up ([15-testing/failure-testing.md](../15-testing/failure-testing.md)).
- **Cooperative-check tests**: a loop with cancellation checks stops between
  iterations.
- **No-leak tests**: cancelled tasks don't keep running in the background.

## Debugging

- A server whose CPU stays pegged after cancellations → cancellation is being
  ignored or `CancelledError` is swallowed; check handlers for bare `except:`.
- A client that hangs forever after a cancel → the server never answered the
  original request.

## Security considerations

- **Cancellation is not a safety mechanism** — a server may ignore it; use
  authorization and idempotency for guarantees
  ([14-security/destructive-operations.md](../14-security/destructive-operations.md)).
- **Cancellation can be weaponized** — a client that cancels constantly can cause
  churn; rate-limit cancellations like other messages.

## Related concepts

- [long-running-operations.md](long-running-operations.md)
- [progress.md](progress.md)
- [timeouts.md](timeouts.md)
- [01-fundamentals/04-requests-responses-notifications.md](../01-fundamentals/04-requests-responses-notifications.md)