# Subscriptions

## What is it?

**Subscriptions** let a client say "tell me when this resource changes." The flow:

1. Client calls `resources/subscribe {uri}` (only allowed if the server declared the
   `resources.subscribe` capability).
2. The server watches the resource.
3. On change, the server sends `notifications/resources/updated {uri}`.
4. The client re-reads the resource (`resources/read`) to get fresh content.

```
client ──► server   resources/subscribe {uri: "config://app/settings"}
server  ──► client  notifications/resources/updated {uri: "config://app/settings"}
client  ──► server   resources/read {uri: "config://app/settings"}   ← fresh content
```

## Why does MCP need it?

Polling is wasteful and slow: without subscriptions, a client that wants current
config either re-reads constantly (waste) or reads once and goes stale (risk).
Subscriptions flip the model: **the server pushes the fact of change, the client
pulls the content**. For long-lived agent sessions, this is how a server's mutable
state stays visible to the model.

## How does it work?

1. **Declare the capability**: the server's `resources` capability includes
   `subscribe: true`.
2. **Subscribe**: the client sends `resources/subscribe` per URI (optionally with
   `_meta` for the session).
3. **Watch**: the server detects changes — via file watchers, DB triggers, cache
   invalidation, or application code that bumps a version.
4. **Notify**: on change, send `notifications/resources/updated` with the URI.
5. **Re-read**: the client fetches fresh content. **The notification carries no
   content** — only "it changed."

## Mental model

A subscription is a **change-of-address card for a file**: "mail me when this path
changes." The notification is just the postcard saying "it changed" — you still go
pick up the new version yourself. It's the difference between a push of *news* and a
push of *content*: MCP pushes news only.

## MCP-specific behavior

- **`resources/subscribe` + `notifications/resources/updated` are protocol-defined**
  — a real MCP feature (gated on the `resources.subscribe` capability).
- **The notification is URI-scoped** and content-free.
- **Unsubscribe**: the spec's subscribe mechanism is per-session; when the session
  ends, subscriptions end with it. (Explicit unsubscribe is SDK/extension territory —
  check your SDK.)
- **`listChanged` is a different thing**: `notifications/resources/list_changed`
  tells clients the *catalog* changed, not a resource's content. Don't confuse the
  two ([01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)).

## Example

FastMCP — declare the capability and hook change detection:

```python
from fastmcp import FastMCP

mcp = FastMCP("config-service", capabilities={"resources": {"subscribe": True}})

@mcp.resource("config://app/settings")
def settings() -> str:
    """Application settings (JSON)."""
    return open("settings.json").read()
```

The change *detection* is yours: when `settings.json` is rewritten, tell FastMCP the
resource changed. FastMCP exposes resource update notifications through its server
API (check your version's mechanism; conceptually it emits
`notifications/resources/updated` for the URI).

TypeScript SDK — declare the capability at construction:

```typescript
const server = new McpServer(
  { name: "config-service", version: "1.0.0" },
  { capabilities: { resources: { subscribe: true } } }
);
```

## Industry-standard pattern

Change-notification + client-pull is the classic **cache-invalidation / pub-sub**
pattern: HTTP ETags, WebSub, Redis pub/sub, filesystem watches. The rules carry
over: notify on *actual* change (avoid notification storms), batch notifications
where possible, and keep the notification channel cheap.

## Common mistakes

- **Declaring `subscribe` but never notifying** — clients wait forever.
- **Notification storms** — notifying on every intermediate write; debounce/batch.
- **Notifying without a corresponding capability declaration** — clients shouldn't
  expect it.
- **Content in the notification** — the spec says news only; putting content in
  `notifications/resources/updated` breaks clients.
- **Forgetting sessions**: subscriptions die with the session — a reconnect needs a
  fresh subscribe.

## Testing

- **Capability tests**: the handshake declares `resources.subscribe`.
- **Notify tests**: mutate the source → exactly one `resources/updated` with the
  right URI ([15-testing/resource-testing.md](../15-testing/resource-testing.md)).
- **Storm tests**: N mutations in a burst → debounced notifications.
- **Session tests**: after reconnect, the client must re-subscribe.

## Debugging

- "Client is stale" → did the notification fire? Check the server's change-detection
  path (file watcher, DB trigger) in logs.
- Notifications firing but the client not re-reading → the client ignored the
  notification; check its subscription handling.

## Security considerations

- **Subscriptions leak change information** ("this config changed") — fine for most
  resources, sensitive for others; authorize who may subscribe.
- **Notification floods are a DoS vector** — rate-limit/queue change events
  ([08-reliability-resilience/backpressure.md](../08-reliability-resilience/backpressure.md)).

## Related concepts

- [dynamic-resources.md](dynamic-resources.md)
- [01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)
- [04-tool-engineering/progress.md](../04-tool-engineering/progress.md) (notification patterns)
- [08-reliability-resilience/caching.md](../08-reliability-resilience/caching.md)