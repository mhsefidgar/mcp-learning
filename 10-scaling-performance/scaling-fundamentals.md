# MCP Scaling Fundamentals

## What is it?

**Scaling** is serving more clients/calls by adding resources — either **vertically**
(a bigger machine) or **horizontally** (more machines). The fundamental question for
MCP servers: **can any instance serve any request?** The answer depends on one
design property — whether the server keeps **session state in memory**.

## Stateless vs. stateful MCP servers

| | Stateless | Stateful (session-based) |
|---|---|---|
| What it stores | nothing between requests (or only external stores) | session state in process memory: subscriptions, progress tokens, in-flight server→client requests |
| Scaling | any instance serves any request → round-robin load balancing, trivial horizontal scaling | the instance that initialized a session must keep serving it → sticky sessions, coordination |
| Restart/redeploy | zero impact | kills all sessions ([08-reliability-resilience/session-recovery.md](../08-reliability-resilience/session-recovery.md)) |
| The 2026-07-28 spec | the *default* — the protocol core is stateless | legacy era |

## How to decide

1. **If you can be stateless, be stateless.** It is strictly simpler to operate.
2. **If you need state** (subscriptions, long-lived context), push it to an
   **external store** (Redis, a database) keyed by session/client, so instances stay
   interchangeable — or accept sticky sessions and their operational cost
   ([session-affinity.md](session-affinity.md)).
3. **The stateless 2026-07-28 spec makes this the default**: no sessions, requests
   self-describing, any instance handles any request
   ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).

## Vertical vs. horizontal

- **Vertical**: bigger CPU/RAM. Simple, but bounded, and it concentrates risk (one
  box, one failure domain).
- **Horizontal**: more instances behind a load balancer. The scaling answer for
  production; requires statelessness (or affinity) and service discovery
  ([multi-server-and-gateway.md](multi-server-and-gateway.md)).

## Mental model

Stateless servers are **teller windows at a bank**: any teller (instance) can serve
any customer; add windows to reduce lines. Stateful servers are **medical records
filed in one doctor's office**: the patient must return to the office that holds
their file — adding offices doesn't help unless records are shared (external store)
or patients are assigned (sticky sessions).

## MCP-specific behavior

- **The session-based protocol's session state is the scaling blocker**
  ([01-fundamentals/09-sessions-and-lifecycle.md](../01-fundamentals/09-sessions-and-lifecycle.md)):
  `Mcp-Session-Id` + server-held state.
- **stdio is inherently one-client-per-process** — horizontal scaling of stdio
  servers means *more processes*, which is automatic and cheap
  ([01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)).
- **Streamable HTTP is where scaling design matters** — see
  [connection-management-at-scale.md](connection-management-at-scale.md).

## Example

Making a server stateless: move per-session state out of memory.

```python
# BAD (stateful, in-memory): subscriptions vanish on restart and can't be shared
_subscriptions: dict[str, set[str]] = {}

# GOOD (stateless handler): state lives in an external store keyed by session id
async def get_subscriptions(session_id: str) -> set[str]:
    return await redis.smembers(f"subs:{session_id}")
```

## Common mistakes

- **Sticky sessions by default** — they work in demos and bite in production
  (draining, uneven load, restart pain).
- **In-memory state "for now"** — it becomes the production architecture.
- **Scaling reads but not writes** — shared mutable state behind N instances is a
  consistency problem, not a scaling win.
- **Forgetting that stdio scales by process count** — no HTTP tuning needed, but
  each process is one client: resource-heavy servers are expensive per client.

## Testing

- **Interchangeability tests**: two instances serve the same client (stateless) or
  the same session (stateful, shared store) correctly
  ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **Restart tests**: killing one instance doesn't lose state (external store).
- **Load tests**: N instances achieve near-linear throughput until the shared store
  saturates ([load-and-performance-testing.md](load-and-performance-testing.md)).

## Related

- [session-affinity.md](session-affinity.md)
- [multi-server-and-gateway.md](multi-server-and-gateway.md)
- [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)
- [01-fundamentals/09-sessions-and-lifecycle.md](../01-fundamentals/09-sessions-and-lifecycle.md)