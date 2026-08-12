# 04 — Requests, Responses, and Notifications

## What is it?

Three kinds of messages flow on an MCP connection:

| Kind | Has `id`? | Expects a reply? | Used for |
|------|-----------|------------------|----------|
| **Request** | yes | yes | Anything that needs an answer: `initialize`, `tools/call`, `resources/read`, `prompts/get` |
| **Response** | yes (echoes request id) | no | The answer to a request: a `result` or an `error` |
| **Notification** | no | no | Fire-and-forget signals: `notifications/initialized`, `notifications/cancelled`, `notifications/progress`, `notifications/resources/updated` |

That's the whole taxonomy. Every byte on the wire is one of these.

## Why does MCP need it?

Distinguishing requests from notifications is what makes the protocol **asynchronous
and bidirectional** without requiring a full request/response turn for everything:

- **Requests** let either side *ask* and wait (needed for tool calls and for
  server→client features like sampling and elicitation).
- **Notifications** let either side *signal* without blocking (progress updates,
  cancellations, change events). If everything were a request, progress reporting would
  force the client to answer every tick.

## How does it work?

1. A side sends a **request** with a unique `id` and a `method`.
2. The other side processes it and sends back a **response** with the *same* `id`,
   containing either `result` or `error`.
3. While waiting, the requester may keep sending other requests (multiple in flight)
   and may receive notifications from the other side at any time.
4. A **notification** is sent and forgotten — no `id`, no reply, and the sender must
   not wait for one.

The request/response pairing is purely **id-based**: the responder never "connects" the
reply to the request by order, only by `id`. That's what allows out-of-order responses
and concurrent in-flight requests.

## Mental model

A request is **calling someone and staying on the line**; a notification is **sending a
text and moving on**. The `id` is the caller ID that lets you match replies to calls.
You can have many calls on hold at once — each reply announces which call it answers.
A notification is a broadcast: no one answers, ever.

## MCP-specific behavior

- **Notifications belong to the `notifications/` namespace.** Examples:
  - `notifications/initialized` — client tells server the handshake is done
  - `notifications/cancelled` — either side abandons an in-flight request (with a
    `requestId` and optional `reason`)
  - `notifications/progress` — server reports progress on a long operation (must carry
    the `progressToken` from the request's `_meta`)
  - `notifications/resources/updated` — a resource changed
  - `notifications/tools/list_changed` — the tool catalog changed
  - `notifications/message` — server→client log messages (via the `logging/*` capability)
- **Progress tokens**: a request may carry `params._meta.progressToken`; if so, the
  server may emit `notifications/progress` referencing it. Without a token, progress
  notifications are not expected.
- **Cancellation is a notification, not a request**: cancel `tools/call` #5 by sending
  `notifications/cancelled` with `requestId: 5`. There is no "cancel response" — the
  original request's response (success or error) still arrives eventually.
- In the **2026-07-28 stateless spec**, the notification set changes (no
  `notifications/initialized`; `notifications/cancelled` still exists) — see
  [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md).

## Example

A tool call with progress and cancellation, in order:

```
Client ──► Server   {"jsonrpc":"2.0","id":7,"method":"tools/call",
                     "params":{"name":"render","arguments":{"scene":"city"},
                               "_meta":{"progressToken":"p-42"}}}
Server ──► Client   {"jsonrpc":"2.0","method":"notifications/progress",
                     "params":{"progressToken":"p-42","progress":25,"total":100}}
Server ──► Client   {"jsonrpc":"2.0","method":"notifications/progress",
                     "params":{"progressToken":"p-42","progress":50,"total":100}}
Client ──► Server   {"jsonrpc":"2.0","method":"notifications/cancelled",
                     "params":{"requestId":7,"reason":"user lost patience"}}
Server ──► Client   {"jsonrpc":"2.0","id":7,
                     "error":{"code":-32800,"message":"Request cancelled"}}
```

Note the final message: it's a **response** (has `id: 7`) with an **error** — even
though the operation was cancelled, the client still gets a reply to its request.

**In FastMCP**, you rarely see these messages: progress is `await ctx.report_progress(50, 100)`
and cancellation is handled by `asyncio` task cancellation underneath. But knowing the
wire shape is what makes debugging possible.

```python
from fastmcp import FastMCP, Context

mcp = FastMCP("renderer")

@mcp.tool
async def render(scene: str, ctx: Context) -> str:
    """Render a scene, reporting progress along the way."""
    total = 100
    for i in range(0, total + 1, 25):
        await ctx.report_progress(i, total)
        await asyncio.sleep(0.05)  # simulated work; honours cancellation
    return f"Rendered {scene}"
```

## Industry-standard pattern

Request/response with correlation IDs plus fire-and-forget events is the pattern behind
**HTTP/2 streams**, **WebSocket subprotocols**, **AMQP RPC**, and **gRPC server
streaming**. The novel MCP twist: **cancellation and progress are first-class messages**
rather than transport hacks, which is what lets an LLM orchestrate long operations.

## Common mistakes

- **Treating notifications as if they had responses** — e.g., waiting for a reply to
  `notifications/progress`. There is none.
- **Sending progress without a progress token.** If the request didn't include one, the
  client is not obliged to understand the notification.
- **Cancelling by "forgetting" the request** — a request you never answer leaves the
  other side hanging forever. Always send `notifications/cancelled` *and* still respond
  (with an error) when you actually can.
- **Assuming responses arrive in order.** They don't have to; match on `id`.

## Testing

- Test the **id correlation**: fire several requests concurrently and assert each
  response matches its request (the lab clients in `repository/go`, `repository/rust`
  do exactly this).
- Test that **notifications produce no response** and don't break in-flight requests.
- Test the **cancellation dance**: start a long tool call, cancel it, and assert (a) a
  `notifications/cancelled` was sent, (b) the request eventually resolves with a
  cancellation error, (c) no work continues after cancellation (see
  [04-tool-engineering/cancellation.md](../04-tool-engineering/cancellation.md)).
- Test **progress**: a tool emitting progress notifications produces one per reported
  step, with the right token.

## Debugging

- In MCP Inspector, filter by message kind: seeing a flood of `notifications/progress`
  is normal; seeing *responses to notifications* means a bug.
- When a client "hangs", the first thing to check is an **unanswered request**: list
  outstanding IDs and find the one with no response.
- `id: null` in a response is a classic sign that code responded to a notification.

## Security considerations

- **Cancellation is advisory**: a server receiving `notifications/cancelled` should
  stop work, but a malicious server can ignore it. Never rely on cancellation for
  safety-critical guarantees — use idempotency and authorization instead
  ([04-tool-engineering/idempotency.md](../04-tool-engineering/idempotency.md)).
- **Notifications are the cheapest way to spam a peer** — rate-limit inbound
  notification floods (see [08-reliability-resilience/rate-limiting.md](../08-reliability-resilience/rate-limiting.md)).

## Related concepts

- [03-json-rpc.md](03-json-rpc.md) — the wire format for all three kinds
- [04-tool-engineering/progress.md](../04-tool-engineering/progress.md)
- [04-tool-engineering/cancellation.md](../04-tool-engineering/cancellation.md)
- [06-agent-interaction/progress.md](../06-agent-interaction/progress.md)
- [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)
