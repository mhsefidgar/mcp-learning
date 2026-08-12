# Dynamic Resources

## What is it?

A **dynamic resource** is a resource whose content is **generated at read time**:
the handler runs when `resources/read` arrives and produces fresh content — a
database query result, a computed metric, a live status. The URI is stable; the
content is not.

## Why does MCP need it?

Most useful data is *live*: the model should read "current server status", "latest
deployments", "today's metrics" — not a snapshot from registration time. Dynamic
resources give the model **fresh context on demand** with the same simple interface
(URI → content) as static ones. They're also the natural partner of resource
templates ([resource-templates.md](resource-templates.md)), which is how dynamic
resources scale to "one per entity."

## How does it work?

1. **Register** the resource (fixed URI, dynamic handler).
2. **Read**: `resources/read` invokes the handler *now* — query the DB, call the
   API, compute — and returns fresh content.
3. **Cost**: every read is real work. Cache aggressively for expensive/stable
   computations ([08-reliability-resilience/caching.md](../08-reliability-resilience/caching.md)),
   and consider subscriptions so clients know when to re-read
   ([subscriptions.md](subscriptions.md)).

## Mental model

A dynamic resource is a **live endpoint disguised as a file**: the "path" is fixed,
but reading it runs a function. Like `/proc/cpuinfo` in Linux — a file-like view over
live kernel state.

## MCP-specific behavior

- **No protocol distinction** — the wire sees an ordinary resource. "Dynamic" is an
  implementation property.
- **Read handlers may be expensive** — the protocol gives clients no hint about
  cost; your description should say ("this runs a live query").
- **Dynamic + templates** = the standard pattern for entity data
  (`orders://{id}` reads the current order).

## Example

```python
import time
from fastmcp import FastMCP

mcp = FastMCP("ops")

@mcp.resource("ops://server/status")
def server_status() -> str:
    """Live server status. Generated on every read."""
    return f'{{"uptime_s": {int(time.time() - boot_time)}, "load": {load_avg()}, "healthy": true}}'
```

TypeScript:

```typescript
server.registerResource("ops://server/status", "Live server status",
  async (uri) => ({ contents: [{ uri, text: JSON.stringify(await getStatus()) }] }));
```

## Industry-standard pattern

Read-triggered computation behind a stable address is standard: **REST GET endpoints**,
**SQL views**, **cached queries**. The engineering rules carry over: bound the cost of
each read, cache where appropriate, and make the read **idempotent and
side-effect-free** (a read must never mutate).

## Common mistakes

- **Side effects in read handlers** — a "read" that increments a counter or writes is
  a bug waiting for a client that reads twice.
- **Slow reads** — a 30-second read blocks the model; keep reads fast or use
  pagination/chunking ([large-resources.md](large-resources.md)).
- **Unbounded queries** — a read that loads a million rows; cap it.
- **No caching** — the same expensive query runs on every read.

## Testing

- **Freshness tests**: two reads return different content when the source changed.
- **Idempotency tests**: a read doesn't mutate anything.
- **Cost tests**: reads complete within a budget; caps enforced.

## Debugging

- A slow `resources/read` → the handler does too much; check query size and caching.
- Stale-looking content → caching too aggressive or change notifications missing
  ([subscriptions.md](subscriptions.md)).

## Security considerations

- **Dynamic reads run code with server permissions** — validate parameters (from
  templates) and authorize *which* resources a principal may read
  ([03-routing-dispatch/03-resource-routing.md](../03-routing-dispatch/03-resource-routing.md)).
- **Reads can leak live data** — a status resource may expose internal topology;
  filter per principal.

## Related concepts

- [static-resources.md](static-resources.md)
- [resource-templates.md](resource-templates.md)
- [subscriptions.md](subscriptions.md)
- [08-reliability-resilience/caching.md](../08-reliability-resilience/caching.md)