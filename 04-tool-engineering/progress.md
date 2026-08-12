# Progress

## What is it?

**Progress** is reporting how far a long operation has gotten, while it runs. In MCP,
the mechanism is the **`notifications/progress`** notification, carrying a
`progressToken` (from the request's `_meta`), the current `progress` value, and
optionally `total`:

```
client ──► server   tools/call {id: 7, _meta: {progressToken: "p-1"}}
server  ──► client  notifications/progress {progressToken: "p-1", progress: 1, total: 10}
server  ──► client  notifications/progress {progressToken: "p-1", progress: 2, total: 10}
...
```

## Why does MCP need it?

Long operations are opaque black boxes without it: the user sees "working…" for
minutes with no idea if it's 2% or 95% done. Progress gives the client (and through
it, the user) something to render — a bar, a percentage, a "step 3 of 7" — and lets
the client *decide*: show a spinner, offer cancellation, or warn about the wait. For
agents, progress is how the *user* stays in control of long-running tool calls.

## How does it work?

1. **The client opts in**: it includes `_meta.progressToken` in the request. **No
   token = no progress expected** (don't send progress for requests that didn't ask).
2. **The server reports**: during the operation it sends `notifications/progress`
   with the same token, `progress` (current count), and `total` (optional — for
   indeterminate progress, omit `total` or use a fraction).
3. **The client renders**: maps token → request, updates its UI.
4. **The operation completes** normally with its result.

## Mental model

Progress is **a second channel running alongside the request**: the request is the
"call", the progress notifications are the "status updates" on the same ticket
number (the token). The client shows a progress bar only if it put a ticket number on
the original call.

## MCP-specific behavior

- **`notifications/progress` + `_meta.progressToken` are protocol-defined** — a true
  MCP feature.
- **Tokens are client-chosen and opaque** — the server just echoes them.
- **Progress is optional and best-effort** — a server may report at any granularity
  or not at all; a client must tolerate no progress.
- **`total` semantics**: progress/total is a fraction (e.g. 3/10). No `total` =
  indeterminate.

## Example

FastMCP — `ctx.report_progress`:

```python
import asyncio
from fastmcp import FastMCP, Context

mcp = FastMCP("renderer")

@mcp.tool
async def render(scene: str, frames: int, ctx: Context) -> str:
    """Render a scene frame by frame, reporting progress."""
    for i in range(frames):
        await asyncio.sleep(0.1)                      # simulated work
        await ctx.report_progress(i + 1, frames)      # -> notifications/progress
    return f"Rendered {frames} frames of {scene}"
```

TypeScript server side (the TS SDK's `Server` doesn't auto-wire progress; you send
notifications via the server's notification helper when your handler has a
progress token):

```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
// In a handler, after reading the progress token from request._meta:
//   await server.notification({ method: "notifications/progress", params: { progressToken, progress, total } });
```

## Industry-standard pattern

Progress reporting is standard for long operations everywhere: HTTP upload progress,
job queues, `rsync`/`wget`, cloud job status. MCP's version is just the protocol
encoding of the same idea — the engineering is yours (how often to report, what unit
to count, how to keep it cheap).

## Common mistakes

- **Sending progress without a token** — the client can't associate it.
- **Spamming progress** (per-row on a million-row job) — flood the connection; batch
  updates (e.g. every 1% or every N rows).
- **Never sending `total`** for determinate work — clients can't show a meaningful
  bar.
- **Lying about progress** — fake percentages erode user trust; indeterminate
  (no `total`) is honest.
- **Forgetting that progress is optional** — don't build the client to *require* it.

## Testing

- **Token tests**: progress notifications carry the request's token.
- **Sequence tests**: progress values are monotonic and end at/under `total`.
- **Indeterminate tests**: no `total` → no division-by-zero issues client-side.
- **Opt-in tests**: requests *without* a token get no progress notifications.

## Debugging

- In Inspector, you can see progress notifications streaming for a long call — if
  they don't appear, either the client didn't send a token or the server never calls
  `report_progress`.
- Spammy progress → check reporting granularity.

## Security considerations

- **Progress can leak information** (job sizes, data volumes) — consider what counts
  you expose to unauthenticated callers.
- Progress notifications are cheap to flood — rate-limit if needed
  ([08-reliability-resilience/rate-limiting.md](../08-reliability-resilience/rate-limiting.md)).

## Related concepts

- [long-running-operations.md](long-running-operations.md)
- [cancellation.md](cancellation.md)
- [06-agent-interaction/progress.md](../06-agent-interaction/progress.md)
- [01-fundamentals/04-requests-responses-notifications.md](../01-fundamentals/04-requests-responses-notifications.md)