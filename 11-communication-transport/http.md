# HTTP & MCP

## What is it?

The remote transport rides on **HTTP** ([01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)).
This document covers the HTTP-level details: endpoints, methods, headers, status
codes, and streaming — the layer *under* the JSON-RPC messages.

## The contract (session-based spec)

- **Endpoint**: the MCP endpoint is an HTTP URL (conventionally `/mcp`).
- **Method**: `POST` — the request body is a JSON-RPC message.
- **Required header**: `Accept: application/json, text/event-stream` — missing it
  yields `406 Not Acceptable`.
- **Content-Type**: `application/json`.
- **Session header**: the server issues **`Mcp-Session-Id`** on the first response;
  the client must echo it on subsequent requests
  ([01-fundamentals/09-sessions-and-lifecycle.md](../01-fundamentals/09-sessions-and-lifecycle.md)).
- **Response**: JSON for a normal reply; **`text/event-stream`** when the server
  needs to push (notifications, server→client requests) — the client must handle
  both.

## Status codes that matter

| Code | Meaning | Client action |
|------|---------|---------------|
| `200` | request handled | parse body (JSON or SSE) |
| `202` | accepted, response elsewhere | follow the response URL if provided |
| `400` | malformed request | fix the request, don't retry blindly |
| `401/403` | unauthenticated/unauthorized | refresh credentials, don't retry |
| `404` | wrong endpoint | fix the URL |
| `406` | missing `Accept` header | add `Accept: application/json, text/event-stream` |
| `429` | rate limited | honor `Retry-After`, back off ([08-reliability-resilience/rate-limiting.md](../08-reliability-resilience/rate-limiting.md)) |
| `5xx` | server error | retryable with backoff ([04-tool-engineering/retries.md](../04-tool-engineering/retries.md)) |

## Streaming: how the server pushes

For server-initiated messages (progress, log messages, and in the session-based
spec, server→client requests like elicitation), the server can't wait for the
client's next POST — it keeps a POST response open as an **SSE stream**
(`Content-Type: text/event-stream`), writing `event:`/`data:` frames as they
occur. Clients must be able to read a streamed response.

## The 2026-07-28 stateless revision (header-based)

The new spec changes the HTTP contract significantly:

- **No `Mcp-Session-Id`** — requests are stateless
  ([scaling-fundamentals](../10-scaling-performance/scaling-fundamentals.md)).
- **`Mcp-Method` and `Mcp-Name` headers are required** — gateways, rate limiters,
  and WAFs route on headers without parsing bodies
  ([03-routing-dispatch/01-request-dispatch.md](../03-routing-dispatch/01-request-dispatch.md)).
- **`MCP-Protocol-Version`** travels per request; client identity and capabilities
  ride in `_meta`
  ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).

## Mental model

HTTP is the **postal trucks**; JSON-RPC is the envelopes. The MCP-specific rules are
the *labeling* requirements: the truck must carry a specific return-address header
(`Mcp-Session-Id` or, in the new spec, `Mcp-Method`/`Mcp-Name`), and some trucks
drive slowly in circles (SSE streams) while the driver keeps feeding you updates.

## Common mistakes

- **Missing `Accept`** → confusing `406`s.
- **Dropping `Mcp-Session-Id`** → "unknown session" errors
  ([07-inspector-debugging/transport-debugging.md](../07-inspector-debugging/transport-debugging.md)).
- **Clients that can't parse SSE** — server pushes break them.
- **Reverse proxies buffering SSE** — long responses get stuck; disable buffering
  for the MCP path.
- **Retrying `401/403/400`** — permanent failures
  ([04-tool-engineering/retries.md](../04-tool-engineering/retries.md)).

## Testing

- **curl the endpoint** by hand with the right headers
  ([07-inspector-debugging/transport-debugging.md](../07-inspector-debugging/transport-debugging.md)).
- **Status-code tests**: each code maps to the documented client behavior.
- **Header tests**: `Accept`, `Content-Type`, `Mcp-Session-Id` round-trips.
- **Proxy tests**: behind a reverse proxy with streaming disabled → asserts fail
  loudly.

## Security considerations

- **TLS everywhere** ([tls.md](tls.md)) — MCP carries real actions, not just reads.
- **HTTP-level auth** (bearer tokens, mTLS) happens *at* this layer, before MCP
  logic ([14-security/authentication.md](../14-security/authentication.md)).
- **Header-based routing (new spec) exposes tool names to intermediaries** — the
  `Mcp-Name` header is metadata; make sure it doesn't leak sensitive tool names to
  parties you don't trust.

## Related

- [01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)
- [tls.md](tls.md)
- [07-inspector-debugging/transport-debugging.md](../07-inspector-debugging/transport-debugging.md)
- [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)