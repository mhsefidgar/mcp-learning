# 15 — Testing examples

**`tiny_server.py`** — a deliberately small server (two tools, one resource,
one prompt) used as the test subject. **`test_conformance.py`** tests it at two
layers (6 tests):

1. **Raw wire conformance** — a hand-rolled JSON-RPC client speaks directly to
   the server over stdio, asserting the exact framing and message shapes the
   protocol defines: `initialize` handshake, `tools/list` schema shape,
   `tools/call` result framing, and the unknown-tool error behavior. No SDK on
   the client side, so a client bug can't hide a server bug.
2. **Client contract tests** — the same server through the FastMCP client:
   capability advertisement, tool behavior, resource reads, prompt rendering.

```bash
pytest test_conformance.py -q        # or: ../../.venv/Scripts/python.exe -m pytest ...
```

**Two behavior notes the raw tests pin down** (both verified against FastMCP
3.4.7 — this is the point of conformance testing):

- FastMCP wraps a tool's return value in `structuredContent` under a `result`
  key: `{"result": 5}`, not the bare value.
- An unknown tool comes back as a **tool-error result** (`isError: true` with a
  message), not a JSON-RPC error object. Clients must handle both shapes.

See [compatibility-testing.md](../compatibility-testing.md) and
[server-testing.md](../server-testing.md) for the surrounding discussion.
