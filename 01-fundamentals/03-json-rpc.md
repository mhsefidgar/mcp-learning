# 03 — JSON-RPC

## What is it?

[JSON-RPC 2.0](https://www.jsonrpc.org/specification) is a lightweight remote procedure
call protocol: a JSON object that says "call method X with these parameters" and a JSON
object that says "here is the result" (or "here is the error"). MCP uses JSON-RPC 2.0
as its message format. **MCP does not define its own wire format** — it defines a
vocabulary of *methods* on top of JSON-RPC.

## Why does MCP need it?

MCP needs a message format that is:

- **Simple** — implementable in any language without code generation.
- **Standard** — JSON-RPC 2.0 is a published spec, so protocol-level interop is not
  "MCP's problem".
- **Bidirectional** — both the client and the server can send requests; JSON-RPC's
  request/response/notification trio supports that.
- **Extensible** — new methods can be added without breaking old ones.

## How does it work?

JSON-RPC has exactly **three message shapes** (a fourth, the error, is a special kind
of response):

### 1. Request — has an `id`, expects a response

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
 "params": {"name": "add", "arguments": {"a": 2, "b": 3}}}
```

### 2. Success response — echoes the `id`, carries `result`

```json
{"jsonrpc": "2.0", "id": 1,
 "result": {"content": [{"type": "text", "text": "5"}], "isError": false}}
```

### 3. Error response — echoes the `id`, carries `error`

```json
{"jsonrpc": "2.0", "id": 1,
 "error": {"code": -32602, "message": "Invalid params", "data": {"path": ["a"], "msg": "Input should be a valid integer"}}}
```

### 4. Notification — **no `id`**, no response expected

```json
{"jsonrpc": "2.0", "method": "notifications/progress",
 "params": {"progressToken": "abc", "progress": 50, "total": 100}}
```

The `id` is what lets a client match a response to its request when many requests are
in flight (JSON-RPC is asynchronous: responses may arrive out of order). The
`jsonrpc: "2.0"` field is mandatory.

## Request IDs and error structure

- **IDs** can be numbers or strings; they must be unique per in-flight request on a
  connection. MCP does not prescribe a format — SDKs generate them for you
  (monotonic integers, UUIDs, etc.).
- **Error codes** are integers. JSON-RPC reserves a few:

| Code | Meaning |
|------|---------|
| `-32700` | Parse error (invalid JSON) |
| `-32600` | Invalid Request (not a valid request object) |
| `-32601` | Method not found |
| `-32602` | Invalid params |
| `-32603` | Internal error |
| `-32000` to `-32099` | Reserved for implementation-defined server errors (MCP uses these) |

MCP maps its own error conditions onto these codes (e.g. `-32602` for invalid tool
arguments, `-32601` for unknown tool names, and `-32603` with structured `data` for
tool execution errors). See [04-tool-engineering/errors.md](../04-tool-engineering/errors.md).

## Mental model

JSON-RPC is a **telephone call with a message ID**: you dial (send a request with an
`id`), the operator routes it, and the reply comes back with the same `id` written on
it. Notifications are postcards — sent, never answered. The `id` on the reply is how
you know which call it answers, even if replies arrive out of order.

## MCP-specific behavior

- **MCP adds no new JSON-RPC primitives.** Everything MCP does is a method name under
  a namespace (`tools/*`, `resources/*`, `prompts/*`, `initialize`,
  `notifications/*`, `sampling/*`, `elicitation/*`, `logging/*`).
- **MCP uses `params._meta`** as a place for protocol metadata (progress tokens, client
  info in the stateless 2026-07-28 spec).
- **MCP constrains notification names** to the `notifications/` namespace and requests
  to their capability namespaces.
- **Content types**: MCP results use its own content structures (`text`, `image`,
  `resource` blocks) inside `result.content` — that is MCP's addition, not JSON-RPC's.

## Example

A complete initialize exchange (session-based spec). Client → server:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize",
 "params":{"protocolVersion":"2025-11-25",
           "capabilities":{"tools":{"listChanged":true}},
           "clientInfo":{"name":"demo-agent","version":"1.0.0"}}}
```

Server → client:

```json
{"jsonrpc":"2.0","id":1,
 "result":{"protocolVersion":"2025-11-25",
           "capabilities":{"tools":{}},
           "serverInfo":{"name":"demo-server","version":"1.0.0"},
           "instructions":"A demo server."}}
```

Then the client sends the `notifications/initialized` notification (no `id`).

**Low-level implementation.** The language lab has from-scratch JSON-RPC cores you can
read to see every detail of framing, IDs, and error codes:

- `repository/go/jsonrpc` — Go implementation with tests
- `repository/rust/jsonrpc` — Rust implementation with tests
- `repository/python/jsonrpc` — Python implementation with tests

## Industry-standard pattern

JSON-RPC sits in a family of RPC formats (gRPC, Thrift, XML-RPC, REST-with-verbs).
Its unusual property is that it is **self-describing and bidirectional** while staying
human-readable, which is exactly what a model-facing protocol needs: an LLM can be
shown a JSON-RPC exchange and reason about it.

## Common mistakes

- **Forgetting `jsonrpc: "2.0"`** — the message is invalid.
- **Sending a response to a notification.** Notifications have no `id`; you can never
  respond to them, and an `id` of `null` is *not* a valid response target.
- **Reusing an in-flight `id`** — a second request with the same `id` before the first
  is answered is ambiguous.
- **Ignoring the `isError` flag** — in MCP, a tool call can return a `result` that
  contains `isError: true` (the tool ran, but failed semantically). That is *not* a
  JSON-RPC error.

## Testing

- Unit-test your protocol code against the JSON-RPC spec's own test vectors (the lab
  projects do this).
- Test that your SDK-level client and server produce/consume *well-formed* JSON-RPC by
  capturing raw messages (see [07-inspector-debugging/protocol-messages.md](../07-inspector-debugging/protocol-messages.md)).
- Test error paths: unknown method (`-32601`), invalid params (`-32602`), malformed
  JSON (`-32700`).

## Debugging

- Pretty-print and validate the JSON of a captured message before debugging anything
  else — many "protocol" bugs are just invalid JSON.
- Check `id` matching: a response that doesn't match any outstanding request means
  something on the client side is mismanaging IDs.
- Error code first, then `message`, then `data`: MCP servers put detailed structured
  info in `error.data`.

## Security considerations

- JSON-RPC is a **remote-code-execution-by-design** surface: a method name maps to a
  handler. Validate that only *declared* methods are reachable (no wildcard dispatch to
  arbitrary functions) — see [14-security/authorization.md](../14-security/authorization.md).
- Be strict about `params` shapes (schema validation) to avoid type-confusion bugs.
- Log redact-sensitive fields; JSON-RPC errors can leak argument values
  ([09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md)).

## Related concepts

- [04-requests-responses-notifications.md](04-requests-responses-notifications.md)
- [02-mcp-architecture.md](02-mcp-architecture.md)
- [04-tool-engineering/errors.md](../04-tool-engineering/errors.md)
- [11-communication-transport/json-rpc.md](../11-communication-transport/json-rpc.md)
- `repository/go/jsonrpc`, `repository/rust/jsonrpc`, `repository/python/jsonrpc`
