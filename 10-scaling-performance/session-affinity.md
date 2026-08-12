# Session Affinity / Sticky Sessions

## What is it?

**Session affinity** (sticky sessions) is a load-balancing rule that routes all
requests for one session to the same instance — required when instances hold
session state in memory (session-based protocol). The load balancer keys on the
session identifier (or client) and sticks.

## Why does MCP need it?

In the session-based protocol, the instance that answered `initialize` holds the
session state: subscriptions, progress tokens, in-flight server→client requests
([01-fundamentals/09-sessions-and-lifecycle.md](../01-fundamentals/09-sessions-and-lifecycle.md)).
If a load balancer round-robins the next request to a different instance, that
instance says "unknown session." Affinity keeps each session on its home instance.

## How does it work?

1. The client initializes → the load balancer assigns an instance.
2. The LB remembers the mapping (by `Mcp-Session-Id` cookie/header hash, or client
   IP) and routes subsequent requests for that session to the same instance.
3. On instance death, the session dies with it — the client must recover
   ([08-reliability-resilience/session-recovery.md](../08-reliability-resilience/session-recovery.md)).

## The costs (why stateless wins)

- **Uneven load**: some sessions hot, some cold — the LB can't balance finely.
- **Draining pain**: taking an instance down means killing its sessions (drain
  first, or accept the reconnect storm).
- **No graceful scale-down**: instances become un-drainable.

## Mental model

Sticky sessions are **assigned seats**: the customer always sits in the same seat
(instance), so the waiter (state) knows where they are. Fine in a small restaurant;
in a stadium, unassigned seating with shared locker rooms (external state) scales
better.

## MCP-specific behavior

- **The 2026-07-28 stateless spec removes the need**: no session state → plain
  round-robin load balancing
  ([scaling-fundamentals.md](scaling-fundamentals.md),
  [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).
- **Mitigation if you must stay session-based**: push session state to a shared
  store (Redis) and keep the LB round-robin — instances stay interchangeable.
- **stdio needs no affinity**: one process per client by construction.

## Example

Nginx-style affinity (conceptual config): hash on the session header so one session
always lands on one upstream:

```nginx
upstream mcp_servers {
    hash $http_mcp_session_id consistent;
    server 10.0.0.1:8000;
    server 10.0.0.2:8000;
}
```

## Industry-standard pattern

Sticky sessions are a standard (if disliked) LB feature (cookies, `hash` policies).
The modern guidance is the same everywhere: **prefer stateless services and
round-robin; use affinity only for genuinely local state, and externalize state when
you outgrow it.**

## Common mistakes

- **Affinity as a permanent architecture** — it stops working at fleet scale.
- **No drain handling** — killing an instance mid-session breaks live clients.
- **Hashing on the wrong key** — client IP behind NATs/NAT rotation breaks stickiness.
- **Forgetting session recovery** — even with affinity, instances die
  ([session-recovery.md](../08-reliability-resilience/session-recovery.md)).

## Testing

- **Stickiness tests**: a session's requests hit one instance (verify via per-instance logs).
- **Failover tests**: instance death → client recovers via a fresh session
  ([08-reliability-resilience/session-recovery.md](../08-reliability-resilience/session-recovery.md)).
- **Balance tests**: sessions spread across instances reasonably.

## Related

- [scaling-fundamentals.md](scaling-fundamentals.md)
- [load-balancing.md](load-balancing.md) (see [multi-server-and-gateway.md](multi-server-and-gateway.md))
- [01-fundamentals/09-sessions-and-lifecycle.md](../01-fundamentals/09-sessions-and-lifecycle.md)