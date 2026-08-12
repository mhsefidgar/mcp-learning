# Notifications (Server → Client)

## What is it?

**Notifications** are fire-and-forget messages from the server to the client: no
`id`, no response expected. The server-side set includes:

| Notification | Meaning |
|--------------|---------|
| `notifications/progress` | a long operation advanced ([progress.md](progress.md)) |
| `notifications/resources/updated` | a subscribed resource changed ([05-resource-engineering/subscriptions.md](../05-resource-engineering/subscriptions.md)) |
| `notifications/resources/list_changed` | the resource catalog changed |
| `notifications/tools/list_changed` | the tool catalog changed |
| `notifications/prompts/list_changed` | the prompt catalog changed |
| `notifications/message` | a log message (via the `logging` capability) |

(Client→server notifications — `initialized`, `cancelled` — are covered in
[01-fundamentals/04-requests-responses-notifications.md](../01-fundamentals/04-requests-responses-notifications.md).)

## Why does MCP need it?

The client's view of the server must stay **fresh without polling**. If the server
adds a tool, renames a resource, or changes a value, the client's cached view goes
stale — and a model acting on a stale catalog is a model calling dead tools.
Notifications are the "invalidate your cache" signals that keep the client's model of
the server accurate.

## How does it work?

1. The server detects a change (tool registered, resource mutated, log line
   produced).
2. The server sends the matching notification.
3. The client **invalidates its cached catalog/state** and re-fetches on demand
   (`tools/list` again, `resources/read` again).
4. Notifications are best-effort: they can be lost; the client must always be able
   to recover by re-listing/reading.

## Mental model

Notifications are **postcards saying "something changed"** — never the content, just
the fact. The client's cache is a **whiteboard of the server's surface**; each
postcard erases the relevant part so it gets redrawn fresh when needed.

## MCP-specific behavior

- **`listChanged` capability flags** gate catalog-change notifications: a server that
  declares `tools.listChanged: true` must send `tools/list_changed` when its catalog
  changes — and clients may *depend* on that ([01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)).
- **`notifications/message`** carries structured log levels (`debug`…`error`) and is
  gated by `logging/setLevel` from the client
  ([09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md)).
- **In the 2026-07-28 spec**, notification delivery changes shape: change
  notifications move to a single `subscriptions/listen` stream clients opt into per
  type ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).

## Example

FastMCP — registering a tool *after* startup and signaling the catalog change:

```python
from fastmcp import FastMCP

mcp = FastMCP("dynamic", capabilities={"tools": {"listChanged": True}})

# Later, at runtime (e.g. a plugin loaded a tool):
mcp.add_tool(my_new_tool_fn, name="plugin_tool")
# FastMCP emits notifications/tools/list_changed automatically when a declared
# listChanged capability is active (verify your version's exact behavior).
```

Client side (TypeScript SDK), re-listing on change:

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
client.onnotification = async (notification) => {
  if (notification.method === "notifications/tools/list_changed") {
    const tools = await client.listTools();   // refresh the catalog
  }
};
```

## Industry-standard pattern

Cache-invalidation events are standard: **HTTP cache-control, WebSocket push,
database NOTIFY/LISTEN, CDN purges**. The rules: the event is a *hint to refetch*,
not the data; events can be lost, so refetches must always work; and the client
controls how aggressively it re-syncs.

## Common mistakes

- **Sending `list_changed` without the capability declared** — clients shouldn't
  depend on it, and some will ignore it.
- **Putting content in notifications** — they're signals; content belongs in
  responses.
- **Notification storms** — batching multiple changes into one notification.
- **Clients that ignore notifications** — stale catalogs, dead tool calls.

## Testing

- **Change-detection tests**: mutate the catalog/data → exactly the right
  notification fires ([15-testing/capability-testing.md](../15-testing/capability-testing.md)).
- **Client-refresh tests**: after the notification, the client's next list/read
  returns fresh data.
- **Loss-tolerance tests**: dropping the notification still leads to correct
  behavior on the next explicit call.

## Debugging

- "Client keeps calling a tool I removed" → it never processed the `list_changed`
  notification; check the client's notification handler.
- Notifications firing constantly → change detection too sensitive; debounce.

## Security considerations

- **Notifications leak change information** — "a new tool appeared" or "config
  changed" can reveal activity; scope notification delivery per authenticated
  session where sensitive.
- **Notification floods are a DoS vector** — rate-limit server-side emission and
  client-side processing ([08-reliability-resilience/backpressure.md](../08-reliability-resilience/backpressure.md)).

## Related concepts

- [01-fundamentals/04-requests-responses-notifications.md](../01-fundamentals/04-requests-responses-notifications.md)
- [05-resource-engineering/subscriptions.md](../05-resource-engineering/subscriptions.md)
- [progress.md](progress.md)
- [09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md)