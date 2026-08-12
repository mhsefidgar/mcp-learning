# Inspecting Protocol Messages

## What is it?

The Inspector's **protocol log** shows every raw JSON-RPC message in both directions —
the complete wire conversation, from `initialize` to every `tools/call`. This is the
most powerful debugging view in the tool, and the one that teaches you the protocol.

## Why it matters

Every abstraction (SDKs, middleware, transforms) is a lie detector: when behavior
doesn't match intent, the raw messages show you *exactly* what crossed the wire.
Protocol-level inspection answers the debugging questions no higher-level view can:
"did the client send the params I think?", "is the server responding to the right
id?", "is that a notification or a request?".

## How to read a captured exchange

1. **Connect fresh** so you capture the full handshake.
2. Read the initialize request/response: versions, capabilities, clientInfo/
   serverInfo ([01-fundamentals/05-initialization.md](../01-fundamentals/05-initialization.md)).
3. Find the message of interest and classify it:
   - request: has `id`, expects a response
   - response: echoes the `id`, has `result` or `error`
   - notification: no `id`
4. Check the error paths: JSON-RPC error codes (`-32601`, `-32602`, `-32603`) vs.
   `isError` results ([03-routing-dispatch/10-error-routing.md](../03-routing-dispatch/10-error-routing.md)).

## Typical findings

| Observation | Diagnosis |
|-------------|-----------|
| Request sent, no response | handler hung / no timeout; or the request was a notification |
| Response with wrong `id` | client-side id mismanagement |
| `-32601` for a method you implemented | capability gate or wrong namespace ([03-routing-dispatch/05-capability-routing.md](../03-routing-dispatch/05-capability-routing.md)) |
| `notifications/progress` with no token in the request | server reports progress for a request that never asked |
| `isError: true` where you expected success | handler logic, not protocol |

## Related

- [01-fundamentals/03-json-rpc.md](../01-fundamentals/03-json-rpc.md)
- [01-fundamentals/04-requests-responses-notifications.md](../01-fundamentals/04-requests-responses-notifications.md)
- [01-fundamentals/examples/stdio-exchange.md](../01-fundamentals/examples/stdio-exchange.md) — a hand-annotated exchange