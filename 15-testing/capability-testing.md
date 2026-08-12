# Capability Testing

## What is it?

**Capability testing** verifies what a server *advertises*: the capabilities it
declares during `initialize` and the tools, resources, templates, and prompts it
lists. It answers "does this server say what it can do, and is that accurate?"

## Why does MCP need it?

Clients decide *how* to use a server based on its advertised capabilities
([01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)). A
server that fails to advertise its `prompts` capability won't get prompt
requests; one that advertises more than it implements causes client errors. The
capability contract is the first thing every client checks — it must be correct.

## How it works

1. Connect a real client (initialization performs capability exchange).
2. Assert on the **initialization result**: `serverInfo`, `protocolVersion`,
   and the capabilities map.
3. Assert on the **listings**: `tools/list`, `resources/list`,
   `resources/templates/list`, `prompts/list` — every name you expect, nothing
   you don't.
4. Assert the listings **match implementation**: every listed tool actually
   exists; nothing implemented is missing.

## MCP-specific behavior

- Capabilities are *declarations of intent*, negotiated during initialization
  ([01-fundamentals/05-initialization.md](../01-fundamentals/05-initialization.md)).
  Testing must cover both directions: the server advertises X *and* the client
  can use X.
- FastMCP auto-advertises based on what you registered — but transforms and
  composition can change the advertised surface
  ([12-fastmcp/transforms.md](../12-fastmcp/transforms.md),
  [03-routing-dispatch/05-capability-routing.md](../03-routing-dispatch/05-capability-routing.md)),
  so test the *resulting* surface, not the registration.

## Example

```python
from fastmcp import Client

async def test_capabilities():
    async with Client("server.py") as client:
        init = client.initialize_result            # after handshake
        caps = init.capabilities
        assert "tools" in caps and "resources" in caps and "prompts" in caps

        tools = {t.name for t in await client.list_tools()}
        assert tools == {"add", "multiply"}        # exact surface
```

## Industry-standard pattern

- **Contract tests** pin the advertised surface so a change in either direction
  is noticed (adding a tool is a change; accidentally hiding one is too).
- Combine with **capability-based routing tests**
  ([03-routing-dispatch/05-capability-routing.md](../03-routing-dispatch/05-capability-routing.md)):
  a client that *lacks* a capability must not use it.

## Common mistakes

- Testing capabilities through the server API instead of the client — the
  advertisement only matters if a client sees it.
- Asserting listings are *non-empty* instead of *exact* (an accidentally hidden
  tool passes an empty check).

## Related

- [integration-testing.md](integration-testing.md)
- [01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)
- [compatibility-testing.md](compatibility-testing.md)
