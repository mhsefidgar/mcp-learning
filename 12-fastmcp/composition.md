# FastMCP Composition (Mounting Servers)

## What is it?

**Composition** is combining servers: a "workspace" server that *mounts* a weather
server, a calendar server, and its own tools — the client sees one server, FastMCP
routes to the right source. The mounted server becomes a `FastMCPProvider`
([providers.md](providers.md)).

## Why it exists

Large servers should be **built from focused modules**: teams own domain servers
independently (each runnable and testable on its own), and a parent composes them.
Composition without collision is the whole game — names must be namespaced or they
collide.

## How it works (verified API)

```python
from fastmcp import FastMCP

weather = FastMCP("weather")

@weather.tool
def forecast(city: str) -> str:
    """Weather forecast for a city."""
    return f"Sunny in {city}."

calendar = FastMCP("calendar")

@calendar.tool
def events(day: str) -> list[str]:
    """Calendar events for a weekday."""
    return ["standup", "review"]

main = FastMCP("workspace")
main.mount(weather, namespace="wx")     # weather tools become wx_*
main.mount(calendar)                     # no namespace -> names stay as-is
```

The client sees `wx_forecast` and `events`; calls route to the right sub-server.
(The `namespace=` argument creates a `Namespace` transform automatically —
[transforms.md](transforms.md).)

**State rules** (verified): middleware state does **not** cross mount boundaries —
a value set on the parent isn't visible in a mounted child's handlers (unless you
share a session state store or use request-scoped state). Each `FastMCP` instance
owns its own state.

## MCP-specific behavior

- **Nothing protocol-level** — the wire sees one server with merged components.
- **Parent middleware runs for all requests; child middleware only for the child's
  handlers** ([middleware.md](middleware.md)).
- Mounted servers remain independently runnable (they're ordinary `FastMCP`
  objects).

## Common mistakes

- **Un-namespaced collisions** — two mounts both defining `search`; one silently
  shadows the other (registration order decides).
- **Expecting state to flow across the mount** — it doesn't by default.
- **Mounting with different lifecycle needs in mind** — each server may have its
  own lifespan; compose deliberately.

## Testing

- **Merged-catalog tests**: tools from all mounts appear under their namespaced
  names ([15-testing/capability-testing.md](../15-testing/capability-testing.md)).
- **Routing tests**: namespaced calls reach the right sub-server.
- **Isolation tests**: sub-server state/middleware stays scoped.

## Related

- [providers.md](providers.md) · [transforms.md](transforms.md)
- [03-routing-dispatch/06-provider-routing.md](../03-routing-dispatch/06-provider-routing.md)
- [03-routing-dispatch/examples/composed_server.py](../03-routing-dispatch/examples/composed_server.py)