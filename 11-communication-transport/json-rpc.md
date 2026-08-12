# JSON-RPC Deep Dive

## What is it?

[JSON-RPC 2.0](https://www.jsonrpc.org/specification) is the RPC wire format MCP
uses. The fundamentals are in
[01-fundamentals/03-json-rpc.md](../01-fundamentals/03-json-rpc.md); this document
covers the spec-level details that matter when you implement or debug the protocol
layer yourself — framing, IDs, error codes, and edge cases.

## The message shapes (recap, with the details)

**Request** — `jsonrpc`, `id`, `method`, optional `params`:

```json
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "add", "arguments": {"a": 1, "b": 2}}}
```

**Success response** — `id` echoes the request's:

```json
{"jsonrpc": "2.0", "id": 3, "result": {"content": [{"type": "text", "text": "3"}]}}
```

**Error response** — `error: {code, message, data?}`:

```json
{"jsonrpc": "2.0", "id": 3, "error": {"code": -32602, "message": "Invalid params", "data": {"path": ["a"], "msg": "Input should be a valid integer"}}}
```

**Notification** — no `id`:

```json
{"jsonrpc": "2.0", "method": "notifications/progress", "params": {"progressToken": "t1", "progress": 1, "total": 10}}
```

## The rules that bite

1. **`jsonrpc: "2.0"` is mandatory.** Missing it → `-32600` Invalid Request.
2. **IDs**: number or string, no `null` (except in the *response* to an
   unidentifiable request). Client-generated uniqueness is required per in-flight
   request; responses match by id, not by order.
3. **`params`**: object or array; MCP always uses objects.
4. **Notifications must not produce responses.** An `id` of `null` in a request is
   *not* a valid notification — it's an invalid request.
5. **Error codes**: `-32700` parse, `-32600` invalid request, `-32601` method not
   found, `-32602` invalid params, `-32603` internal; `-32000…-32099`
   implementation-defined. **MCP uses the `-32xxx` space for its own conditions**
   (tool-not-found, resource-not-found, authorization errors — see
   [03-routing-dispatch/10-error-routing.md](../03-routing-dispatch/10-error-routing.md)).
6. **Batch requests**: JSON-RPC supports arrays of requests — **MCP does not use
   batching**; each message is a single object.

## Framing (how messages travel)

- **stdio**: one JSON object per line (newline-delimited). (Older implementations
  used LSP-style `Content-Length` headers; current SDKs speak newline-delimited.
  Don't hand-roll — use the SDK.)
- **Streamable HTTP**: the JSON body of a POST; responses are JSON or SSE streams
  ([http.md](http.md)).

## Error structure (what to put where)

- `code` — the machine-readable class (retryable? validation? not found?).
- `message` — human-readable, model-actionable ("tool `fly` does not exist;
  available tools: add, search").
- `data` — structured detail (failing field path, available names). Never put
  secrets or stack traces here
  ([04-tool-engineering/errors.md](../04-tool-engineering/errors.md)).

## Mental model

JSON-RPC is **envelopes with tracking numbers**: every outbound envelope (request)
has a number (id); every reply has the same number written on it; envelopes without
numbers (notifications) are never answered. The spec is the postal regulations —
small, precise, and worth reading once.

## MCP-specific behavior

- MCP adds **method namespaces** (`tools/*`, `resources/*`, `prompts/*`,
  `notifications/*`, `initialize`, server→client namespaces) but no new JSON-RPC
  primitives.
- MCP results use **content blocks** inside `result` — MCP's addition to the
  result shape.
- The **2026-07-28 stateless spec** keeps JSON-RPC 2.0 unchanged; what changes is
  transport headers and per-request `_meta`
  ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).

## Testing & debugging

- Validate captured messages against the spec (id rules, `jsonrpc` field,
  notification semantics) before debugging anything else
  ([07-inspector-debugging/protocol-messages.md](../07-inspector-debugging/protocol-messages.md)).
- Hand-rolled protocol cores with tests: `repository/go/jsonrpc`,
  `repository/rust/jsonrpc`, `repository/python/jsonrpc` — read them for the
  edge cases in practice.

## Security considerations

- **JSON-RPC is RCE-by-design**: a method name maps to a handler. Keep dispatch
  static and gated ([03-routing-dispatch/01-request-dispatch.md](../03-routing-dispatch/01-request-dispatch.md)).
- **Strict parsing**: reject unknown fields and oversized payloads; beware of
  duplicate keys and deeply nested JSON (parser attacks).

## Related

- [01-fundamentals/03-json-rpc.md](../01-fundamentals/03-json-rpc.md)
- [http.md](http.md)
- [01-fundamentals/examples/raw_handshake.py](../01-fundamentals/examples/raw_handshake.py)
- `repository/{go,rust,python}/jsonrpc`