# FastMCP: The Core Object

## What is it?

`FastMCP` is the central class: one object that is simultaneously a **server**
(exposes tools/resources/prompts), can **mount** other servers, and can be driven
as a **client** to remote servers. It manages schema generation, validation,
transports, auth, and protocol compatibility around your application code.

```python
from fastmcp import FastMCP

mcp = FastMCP("my-server")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b

if __name__ == "__main__":
    mcp.run()          # stdio by default
```

## Why does it exist?

FastMCP exists to make the protocol *obvious*: you write plain Python functions and
FastMCP turns them into correct MCP capabilities — generating schemas from type
hints, validating inputs/outputs, handling the handshake, and speaking the
transport. It's the "one coherent API" for servers, clients, and interactive apps
(see [01-client-server.md](../01-fundamentals/01-client-server.md)).

## How it's structured (the parts this section covers)

```
┌────────────────────────────── FastMCP ──────────────────────────────┐
│  providers ──► components (tools/resources/prompts) ──► transforms │
│        │                                                          │
│  middleware ──► request pipeline (before/during/after dispatch)   │
│        │                                                          │
│  context ──► what handlers can access (logging, progress, ...)    │
│        │                                                          │
│  composition / proxying ──► other servers (mount / proxy)         │
└────────────────────────────────────────────────────────────────────┘
```

## MCP-specific vs. FastMCP-specific

| Concern | Layer |
|---------|-------|
| `tools/call`, `initialize`, transports | **MCP protocol** ([01-fundamentals](../01-fundamentals/README.md)) |
| `@mcp.tool`, providers, transforms, middleware, `Context` | **FastMCP framework** |
| retries, caching, circuit breakers | **general engineering** ([08-reliability-resilience](../08-reliability-resilience/README.md)) |

## Key facts (verified against FastMCP 3.4.x)

- `@mcp.tool`, `@mcp.resource`, `@mcp.prompt` register components (bare or
  parenthesized decorators work).
- `mcp.run()` runs stdio by default; `mcp.run(transport="streamable-http", host=..., port=...)`
  runs HTTP.
- Server-side introspection: `await mcp.list_tools()`, `await mcp.call_tool(name, args)`
  (returns `ToolResult` with `.structured_content`), `await mcp.read_resource(uri)`,
  `await mcp.render_prompt(name, args)`.
- `mcp.mount(sub_server, namespace=...)` composes; `mcp.add_middleware(...)` adds
  middleware; `mcp.add_provider(...)` / `providers=[...]` add sources.
- Client: `Client("server.py")` infers stdio; `Client(url)` infers HTTP;
  `Client({...mcpServers...})` infers a multi-server config.

## Mental model

`FastMCP` is the **conductor**: your functions are the musicians (application
layer), providers/transforms are the sheet-music distribution (where/who plays),
middleware is the sound engineer (cross-cutting), and the protocol/transport is the
concert hall. You write the music; FastMCP runs the show.

## Common mistakes

- Confusing FastMCP features with MCP protocol features.
- Using 2.x-era APIs that changed in 3.x (e.g. `get_prompt` no longer takes
  arguments server-side — use `render_prompt`; result fields changed).
- Forgetting the version you're on — check `fastmcp.__version__` and
  [docs/VERSIONS.md](../docs/VERSIONS.md).

## Related

- [providers.md](providers.md) · [transforms.md](transforms.md)
- [middleware.md](middleware.md) · [context.md](context.md)
- [composition.md](composition.md) · [proxying.md](proxying.md)
- `implementations/python-fastmcp`