# Integration Testing

## What is it?

**Integration testing** for MCP means running a real client against a real server
over a real transport — spawning the server as a subprocess (stdio) or connecting
to it over Streamable HTTP — and asserting on what the *client* observes.

## Why does MCP need it?

Server tests prove your logic works in-process. But MCP is a *wire protocol*:
the client and server exchange JSON-RPC messages, negotiate capabilities
([01-fundamentals/05-initialization.md](../01-fundamentals/05-initialization.md)),
and serialize/deserialize through pydantic models. Bugs hide in that machinery —
a field that fails to serialize, a capability not advertised, an error that
arrives as a confusing exception. Only a real client/server exchange catches
them.

## How it works

With FastMCP's client, an integration test is a few lines:

```python
import pytest
from fastmcp import Client

@pytest.mark.asyncio
async def test_end_to_end():
    async with Client("server.py") as client:      # stdio subprocess
        tools = await client.list_tools()
        assert {"add", "multiply"} <= {t.name for t in tools}

        result = await client.call_tool("add", {"a": 2, "b": 3})
        assert result.content[0].text == "5"
```

Key mechanics:

- `Client("server.py")` spawns the server process over stdio
  ([01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)) —
  so the *entire* stack runs: JSON-RPC framing, initialization, sessions.
- Each `async with` block is a fresh session: the client performs
  `initialize`, exchanges capabilities, then your calls run.
- For Streamable HTTP, `Client("http://localhost:8000/mcp")` connects over the
  network instead ([11-communication-transport/http.md](../11-communication-transport/http.md)).

## MCP-specific behavior

- The client runs the *real* handshake, so a broken `initialize` or a
  mismatched protocol version fails your test instantly — exactly what you want
  ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).
- The client validates tool results against output schemas, so structured-output
  bugs surface here, not in production
  ([04-tool-engineering/structured-output.md](../04-tool-engineering/structured-output.md)).

## Industry-standard pattern

- **Test against the real artifact**: the same `server.py` you ship, not a
  test double.
- **Isolated state**: the server subprocess starts fresh per session — seed and
  assert state via *tools*, since you cannot reach into the subprocess.
  (This is why several examples in this repo expose an `audit_log`/`state`
  tool: it is how tests observe server-side state.)
- **Timeouts**: integration tests can hang; give every call a timeout.

## Common mistakes

- Writing integration tests that are really server tests (never spawning the
  client — nothing proves the wire works).
- Forgetting the server's stdout is a real stream: your `print()` debugging can
  corrupt JSON-RPC framing in stdio mode. Log to stderr or files
  ([07-inspector-debugging/transport-debugging.md](../07-inspector-debugging/transport-debugging.md)).
- No timeout → a wedged server hangs CI forever.

## Testing (how to test the testing)

- Mutate the server (add a tool, change a schema) and confirm the integration
  test fails — i.e., the test is actually sensitive to the wire behavior.

## Related

- [server-testing.md](server-testing.md)
- [capability-testing.md](capability-testing.md)
- [failure-testing.md](failure-testing.md)
- Examples: [03-routing-dispatch/examples/test_routing.py](../03-routing-dispatch/examples/test_routing.py),
  [05-resource-engineering/examples/test_docs.py](../05-resource-engineering/examples/test_docs.py)
