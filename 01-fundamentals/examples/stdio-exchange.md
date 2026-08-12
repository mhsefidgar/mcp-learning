# A raw stdio exchange, annotated

This is the entire client↔server conversation for a minimal session, exactly as it
appears on the wire (newline-delimited JSON over stdio). Run
[`raw_handshake.py`](raw_handshake.py) to reproduce it live.

## 1. Client spawns the server and sends `initialize`

```
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"probe","version":"0.1"}}}
```

- `id: 1` — first request.
- `protocolVersion: "2025-11-25"` — newest version the client supports.
- `capabilities: {}` — this client offers nothing to the server (no sampling, no roots).

## 2. Server responds

```
{"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2025-11-25","capabilities":{"tools":{}},"serverInfo":{"name":"raw-handshake-demo","version":"0.1.0"},"instructions":"A hand-rolled server. Try tools/call add."}}
```

- Same `id: 1` — this answers request 1.
- Server declares it can do **tools** and nothing else.
- `instructions` is optional guidance for the client/model.

## 3. Client sends the `initialized` notification

```
{"jsonrpc":"2.0","method":"notifications/initialized"}
```

- **No `id`** — fire-and-forget. The server must not respond to it.

## 4. Client asks for the tool catalog

```
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
```

## 5. Server returns the catalog (with JSON Schema)

```
{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"add","description":"Add two integers.","inputSchema":{"type":"object","properties":{"a":{"type":"integer","description":"First addend"},"b":{"type":"integer","description":"Second addend"}},"required":["a","b"]}}]}}
```

## 6. Client calls the tool

```
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"add","arguments":{"a":2,"b":3}}}
```

## 7. Server returns the result (as content blocks)

```
{"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"5"}],"isError":false}}
```

- `content` is a list of content blocks — MCP's structured way to return text, images,
  or resource references.
- `isError: false` means the tool *ran successfully* (semantically). A tool that runs
  but fails (e.g. "file not found") returns `isError: true` with a text block — *not*
  a JSON-RPC error.

## 8. Client calls an unknown tool

```
{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"fly","arguments":{}}}
```

```
{"jsonrpc":"2.0","id":4,"error":{"code":-32602,"message":"Unknown tool: fly"}}
```

- JSON-RPC **error response**: same `id`, `error` instead of `result`.

## 9. Client sends malformed JSON

```
{"jsonrpc":"2.0","id":5,"method":"initialize",,,
```

```
{"jsonrpc":"2.0","id":null,"error":{"code":-32700,"message":"Parse error: Expecting value: line 1 column 32 (char 31)"}}
```

- `-32700` is JSON-RPC's parse error. With no valid `id`, the server uses `null`.

---

## Try it yourself

```bash
cd 01-fundamentals/examples
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"probe","version":"0.1"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"add","arguments":{"a":2,"b":3}}}' \
  '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"fly","arguments":{}}}' \
  | python raw_handshake.py
```

The responses appear on **stderr** (annotated with `→`); the protocol bytes go to
stdout. Then read them against the annotations above — every field should be
explainable from [03-json-rpc.md](../03-json-rpc.md) and
[04-requests-responses-notifications.md](../04-requests-responses-notifications.md).
