# Progress (Client-Side)

## What is it?

This document is the **client-side companion** to
[04-tool-engineering/progress.md](../04-tool-engineering/progress.md): how the client
*receives* progress, maps it to the right request, renders it, and decides what to do
(show a bar, offer cancellation, or abandon). The server-side mechanics (tokens,
`notifications/progress`) are covered there.

## Why does MCP need it?

Progress is only useful if the client *acts* on it. A client that ignores progress
notifications renders every long operation as an opaque spinner — and loses the
ability to *decide* (cancel a stuck job, tell the user how long is left). Client-side
progress handling is the difference between "the user is informed and in control" and
"the user stares at a spinner."

## How does it work?

1. **Opt in**: the client attaches `_meta.progressToken` to the request it wants
   progress for (a client-chosen opaque token).
2. **Correlate**: incoming `notifications/progress` carry the same token → map token
   to the in-flight request.
3. **Render**: progress/total → percentage or step display; no `total` → indeterminate
   spinner.
4. **Decide**: with progress data, the client (or user) can offer cancellation,
   warn about long waits, or time out based on *no progress* rather than *no
   response*.

## Mental model

The client is a **dashboard**: each request is a row on the dashboard; the token is
the row id; progress notifications are the updates to that row. A good dashboard
shows rows that are moving, rows stuck, and gives the user a "cancel" button on rows
that shouldn't be there.

## MCP-specific behavior

- **Token correlation is protocol-defined**: the token travels in `_meta` on the
  request and is echoed in the notification.
- **Tolerate absence**: a server may ignore the token entirely — progress handling
  must never be *required*.
- **Tolerate extra**: progress notifications may keep arriving after the request
  completes or is cancelled; ignore unknown/stale tokens.
- **In the 2026-07-28 stateless spec**, progress still flows via
  `notifications/progress` per request context
  ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).

## Example

FastMCP client — `progress_handler`:

```python
from fastmcp import Client

async def main() -> None:
    async with Client("renderer.py") as client:
        async def on_progress(progress, total, token):
            if total:
                print(f"  render: {progress}/{total} ({100 * progress / total:.0f}%)")
            else:
                print(f"  render: working ({progress} units)")

        result = await client.call_tool(
            "render", {"frames": 100}, progress_handler=on_progress, timeout=120,
        )
        print(result.content[0].text)
```

TypeScript SDK:

```typescript
const result = await client.callTool(
  { name: "render", arguments: { frames: 100 } },
  {
    timeout: 120_000,
    progressCallback: (progress) => {
      if (progress.total) {
        console.log(`render: ${progress.progress}/${progress.total}`);
      }
    },
  }
);
```

## Industry-standard pattern

Correlated progress events are standard in job systems, uploads, and build tools.
The client-side rules: correlate by token, never require progress, debounce high-
frequency updates for rendering, and use "no progress for N seconds" as a signal for
timeout decisions ([04-tool-engineering/timeouts.md](../04-tool-engineering/timeouts.md)).

## Common mistakes

- **Not sending a token** — then complaining there's no progress.
- **Requiring progress** — a server that doesn't report breaks your client; degrade
  gracefully.
- **Rendering every notification** — a 1M-row job floods the UI; throttle.
- **Ignoring cancellation UI** — progress is *the* natural place to offer cancel
  ([04-tool-engineering/cancellation.md](../04-tool-engineering/cancellation.md)).

## Testing

- **Correlation tests**: progress notifications map to the correct in-flight request.
- **Render tests**: determinate vs. indeterminate handling; no division by zero.
- **Stale-token tests**: late notifications after completion are ignored.
- **No-progress tests**: a server that never reports → client still completes.

## Debugging

- Progress arrives but nothing renders → the token isn't being correlated or the UI
  layer is dropped; check the mapping.
- A call "hangs" but progress is flowing → your timeout is response-based, not
  progress-based; consider no-progress timeouts.

## Security considerations

- **Progress can leak data volumes** ("row 900,000 of 1M") — consider what progress
  data is shown to whom.
- **Progress floods** are cheap for a malicious server to emit — rate-limit
  processing.

## Related concepts

- [04-tool-engineering/progress.md](../04-tool-engineering/progress.md)
- [04-tool-engineering/cancellation.md](../04-tool-engineering/cancellation.md)
- [notifications.md](notifications.md)
- [04-tool-engineering/timeouts.md](../04-tool-engineering/timeouts.md)