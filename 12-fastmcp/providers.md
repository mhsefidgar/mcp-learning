# FastMCP Providers

## What is it?

A **provider** is a source of tools, resources, and prompts. Every FastMCP server
has one or more providers; when a client asks "what tools do you have?", FastMCP
queries each provider and merges the results
([03-routing-dispatch/06-provider-routing.md](../03-routing-dispatch/06-provider-routing.md)).

| Provider | Source | How you use it |
|----------|--------|----------------|
| `LocalProvider` | components you define in code | `@mcp.tool`, `mcp.add_tool()` — the default |
| `FastMCPProvider` | another FastMCP server | `mcp.mount(server)` / `providers=[FastMCPProvider(s)]` |
| `ProxyProvider` | a remote MCP server | `mcp.add_provider(ProxyProvider(client))` |
| custom providers | a database, an OpenAPI spec, ... | subclass `Provider` |

## Why it exists

Composition. As servers grow, components come from multiple sources — a mounted
domain server, a proxied remote server, a database-backed catalog. Providers give
every source a uniform interface so routing, transforms, and auth treat all sources
the same. You can ignore providers entirely for a simple decorator server.

## How it works

1. `LocalProvider` is always registered **first** — your decorator components win
   name conflicts (for equal/unversioned components).
2. Additional providers register in the order you add them.
3. **Listing**: FastMCP queries every provider and merges catalogs.
4. **Lookup**: a request for a component queries providers in order and returns the
   first (or highest-version) match.
5. **Execution**: the owning provider runs the handler — local code, a mounted
   server's code, or a forwarded remote call.

## MCP-specific behavior

- **Nothing protocol-level** — the client sees one server; providers are
  server-side organization.
- **Version-aware merging**: FastMCP returns the highest matching version across
  providers that have the component; equal/unversioned → registration order.
- **Transforms attach per provider** (namespace a mount without touching local
  tools) — [transforms.md](transforms.md).

## Example

```python
from fastmcp import FastMCP
from fastmcp.server.providers import FastMCPProvider

weather = FastMCP("weather")
@weather.tool
def forecast(city: str) -> str:
    """Weather forecast for a city."""
    return f"Sunny in {city}."

main = FastMCP("workspace", providers=[FastMCPProvider(weather)])
# or: main.mount(weather, namespace="wx")
```

## Common mistakes

- **Name collisions between providers** — namespace mounts
  ([composition.md](composition.md)).
- **Assuming provider order doesn't matter** — it does, for equal-version
  conflicts.
- **Treating providers as a protocol feature** — they're FastMCP's organization.

## Testing

- **Merged-catalog tests**: components from all providers appear in `*/list`
  ([15-testing/capability-testing.md](../15-testing/capability-testing.md)).
- **Precedence tests**: duplicate names resolve to the expected provider.
- **Isolation tests**: mounted provider state doesn't leak into the parent.

## Related

- [03-routing-dispatch/06-provider-routing.md](../03-routing-dispatch/06-provider-routing.md)
- [composition.md](composition.md) · [proxying.md](proxying.md)
- [transforms.md](transforms.md)