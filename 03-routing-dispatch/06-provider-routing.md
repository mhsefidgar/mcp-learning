# 06 — Provider Routing

> **Framework concept.** Providers are a **FastMCP** abstraction (3.0+) for *sourcing*
> components. They are not part of the MCP protocol. The TypeScript and Java SDKs
> don't have a provider object, but they solve the same problem (composing servers)
> via client-side aggregation or proxying — see
> [12-remote-proxy-routing.md](12-remote-proxy-routing.md).

## What is it?

A **provider** is a source of tools, resources, and prompts. In a simple FastMCP
server, your `@mcp.tool` decorators all feed one implicit provider
(`LocalProvider`). As servers grow, components come from several places:

| Provider | Source | Typical use |
|----------|--------|-------------|
| `LocalProvider` | your decorators / `add_tool()` | the default |
| `FastMCPProvider` | another FastMCP server | `mcp.mount(sub_server)` — composition |
| `ProxyProvider` | a remote MCP server | `create_proxy(client)` — proxying |
| custom providers | a database, an OpenAPI spec, ... | dynamic tools |

**Provider routing** is the question: *which provider supplies this component?* When a
client asks for tool `search`, FastMCP asks each provider and merges the results.

## Why does MCP need it? (Why FastMCP needs it)

Composition. A production server is rarely one file of decorators — it's several
domain servers (weather, calendar, files) mounted together, or a gateway that proxies
remote backends, or a server whose tool catalog comes from a database. Providers give
every source a uniform interface so routing, transforms, and authorization treat all
sources the same.

## How does it work?

1. **Registration order defines precedence.** `LocalProvider` is always first; mounted
   and proxied providers follow in the order you add them.
2. **Listing**: the server queries every provider and merges catalogs. For
   unversioned components, earlier providers win name conflicts.
3. **Lookup**: a request for a component by name/URI queries providers in order and
   returns the first (or highest-version) match.
4. **Execution**: the owning provider runs the handler — local code, a mounted
   server's code, or a forwarded remote call.

```
                ┌─────────────────────────────┐
                │         FastMCP server      │
                │   ┌──────────┐ ┌──────────┐ │
  tools/call ──►│   │ Local    │ │ Mounted  │ │
                │   │ Provider │ │ Provider │ │
                │   └──────────┘ └──────────┘ │
                │   ┌──────────────────────┐  │
                │   │  ProxyProvider (http)│──┼──► remote MCP server
                │   └──────────────────────┘  │
                └─────────────────────────────┘
```

## Mental model

Providers are **plug-in sources behind one namespace**: like a package manager that
installs tools from many repositories, or a compiler that links object files from
many libraries. The server is the aggregate; providers are the inputs.

## MCP-specific behavior

- **Nothing here is protocol-level.** The client sees one server; it has no idea
  components come from multiple providers. Provider routing is purely server-side
  organization.
- **Version-aware merging**: FastMCP queries providers and returns the *highest
  matching version* across providers that have the component; equal/unversioned →
  registration order decides.
- **Transforms attach per provider** (namespace a mounted server without touching
  your local tools) — see [07-transform-routing.md](07-transform-routing.md).
- **State does not flow across mount boundaries** by default: middleware state set on
  the parent isn't visible in a mounted child unless you share a session state store
  ([12-fastmcp/composition.md](../12-fastmcp/composition.md)).

## Example

```python
from fastmcp import FastMCP
from fastmcp.server.providers import FastMCPProvider

weather = FastMCP("weather")
calendar = FastMCP("calendar")

@weather.tool
def forecast(city: str) -> str:
    """Weather forecast for a city."""
    return f"Sunny in {city}."

@calendar.tool
def events(day: str) -> list[str]:
    """Calendar events for a day."""
    return ["standup", "review"]

main = FastMCP("workspace", providers=[FastMCPProvider(weather), FastMCPProvider(calendar)])
# or, equivalently:
# main.mount(weather)
# main.mount(calendar)
```

The client sees `forecast` and `events` as if `main` defined them. Mount with a
namespace to avoid collisions:

```python
main.mount(weather, namespace="wx")
# client now sees wx_forecast
```

See [12-fastmcp/composition.md](../12-fastmcp/composition.md) for the full story.

## Industry-standard pattern

Provider abstraction = **dependency injection of capability sources**: plugin systems
(loaders), data-source abstraction (databases behind one interface), and service
composition (facades over many services). The invariants: sources are swappable,
ordering is explicit, and the consumer can't tell which source served the result.

## Common mistakes

- **Name collisions between providers** — always namespace mounted servers, or one
  silently shadows the other (registration order decides).
- **Assuming provider order doesn't matter** — it does, for equal-version conflicts.
- **Sharing state across providers by accident** — mounted servers have isolated
  state unless you opt in.
- **Treating providers as a protocol feature** — they're FastMCP's organization; the
  wire sees one server.

## Testing

- **Merged catalog tests**: components from all providers appear in `tools/list`/
  `resources/list`/`prompts/list`.
- **Precedence tests**: duplicate names resolve to the expected provider.
- **Namespace tests**: namespaced mounts appear/route under prefixes.
- **Isolation tests**: mounted server's middleware/state doesn't leak into the parent.

## Debugging

- A tool "missing" from the catalog: check which providers are registered and their
  order; a namespaced mount hides names under prefixes.
- A wrong-handler call: check precedence — an earlier provider with an equal-version
  duplicate wins.

## Security considerations

- **Providers widen the attack surface**: a proxied remote provider executes remote
  code — authorize and rate-limit it like any remote dependency
  ([12-remote-proxy-routing.md](12-remote-proxy-routing.md)).
- **Custom providers (database-backed) need input validation** exactly like any other
  handler.
- Apply authorization *after* provider resolution (per resolved component), not per
  provider.

## Related concepts

- [07-transform-routing.md](07-transform-routing.md)
- [12-remote-proxy-routing.md](12-remote-proxy-routing.md)
- [12-fastmcp/providers.md](../12-fastmcp/providers.md)
- [12-fastmcp/composition.md](../12-fastmcp/composition.md)