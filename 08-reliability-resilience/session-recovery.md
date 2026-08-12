# Session Recovery

## What is it?

**Session recovery** is the client-side logic that survives a broken session:
detecting that the connection/session died, re-initializing a new one, and resuming
work — possibly replaying safe in-flight operations. In the session-based protocol
this is essential, because sessions are fragile (server restarts, timeouts, network
drops invalidate `Mcp-Session-Id`s).

## Why does MCP need it?

Remote MCP servers restart, deploy, and get killed by OOM killers. Every restart
invalidates all sessions, and every client holding a dead session starts getting
"unknown session" errors. Without recovery logic, a routine deploy becomes a
client-wide outage. Recovery is what turns "the server went down" from an incident
into a blip.

## How does it work?

1. **Detect**: classify the failure as session-related — "unknown session",
   connection reset, transport timeout ([remote-proxy-failures.md](remote-proxy-failures.md)).
2. **Re-initialize**: open a fresh transport and run the handshake
   ([01-fundamentals/05-initialization.md](../01-fundamentals/05-initialization.md)) —
   in the session-based spec this mints a new `Mcp-Session-Id`.
3. **Re-establish state**: re-subscribe to resources, re-apply logging levels,
   re-fetch the catalog (subscriptions don't survive sessions —
   [05-resource-engineering/subscriptions.md](../05-resource-engineering/subscriptions.md)).
4. **Replay safely**: retry in-flight requests — only if idempotent or keyed
   ([04-tool-engineering/idempotency.md](../04-tool-engineering/idempotency.md)).
5. **Bounded retries**: cap reconnection attempts with backoff
   ([exponential-backoff.md](exponential-backoff.md)), then fail cleanly with a
   model-actionable error.

## Mental model

Session recovery is **redialing after a dropped call**: hear the disconnect, hang up,
dial again, and re-introduce yourself (handshake), then continue the conversation
from where it was safe to. You don't replay the whole call — just the part that was
cut off, and only if replaying it is safe.

## MCP-specific behavior

- **Sessions are server-side state**: recovery = new session + re-establish what the
  server forgot (subscriptions, tokens).
- **Replaying in-flight calls is dangerous**: the call may have *succeeded* before
  the response was lost — retry only idempotent operations.
- **The stateless 2026-07-28 spec removes this problem for reads**: any request can
  hit any instance, no session to lose
  ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)) —
  recovery becomes "retry the request", not "recreate the session".

## Example

A minimal reconnect loop (conceptual client pattern):

```python
import asyncio

async def connect_with_recovery(make_transport, max_attempts: int = 5) -> Client:
    for attempt in range(max_attempts):
        try:
            client = Client(make_transport())
            await client.initialize()               # handshake → new session
            return client
        except (ConnectionError, SessionLost) as exc:
            if attempt == max_attempts - 1:
                raise
            await asyncio.sleep(2 ** attempt)       # backoff, then retry
```

## Industry-standard pattern

Reconnect-with-backoff and safe-replay is the pattern behind database connection
pools, WebSocket reconnects, and gRPC reconnection logic. The rules: detect fast,
back off, restore state, replay only what's safe, and give up loudly.

## Common mistakes

- **Retrying in-flight *write* calls blindly** — duplicates (the classic double-order).
- **Forgetting subscriptions re-establishment** — the session is back but the
  client is blind to changes.
- **Infinite reconnect loops** — bounded attempts + backoff, then a clean error.
- **Reusing the dead session id** — the client "reconnects" but still sends the old
  `Mcp-Session-Id`.
- **No detection** — the client keeps sending into the void instead of noticing.

## Testing

- **Kill-restart tests**: restart the server mid-session; assert the client
  reconnects and resumes ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **State-restore tests**: subscriptions/log levels are re-applied after recovery.
- **Replay-safety tests**: a write that succeeded pre-crash is not double-executed
  (idempotency keys).
- **Give-up tests**: a server that never comes back produces a clean final error.

## Security considerations

- **Re-authenticate on recovery** — never reuse a dead session's auth blindly;
  tokens may have expired during the outage.
- **Recovery must not bypass authorization** — re-run the same checks on the new
  session.

## Related

- [01-fundamentals/09-sessions-and-lifecycle.md](../01-fundamentals/09-sessions-and-lifecycle.md)
- [remote-proxy-failures.md](remote-proxy-failures.md)
- [exponential-backoff.md](exponential-backoff.md)
- [04-tool-engineering/idempotency.md](../04-tool-engineering/idempotency.md)