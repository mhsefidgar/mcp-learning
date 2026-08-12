# Load Balancing MCP Servers

## What is it?

**Load balancing** distributes incoming connections/requests across a fleet of MCP
server instances. The two flavors that matter for MCP:

- **Stateless servers** → plain **round-robin/least-connections**: any instance
  serves any request ([scaling-fundamentals.md](scaling-fundamentals.md)).
- **Session-based servers** → **sticky/affinity** routing: one session stays on one
  instance ([session-affinity.md](session-affinity.md)).

## Why does MCP need it?

A single MCP server instance is a single point of failure *and* a capacity wall.
Balancing gives you: capacity (more instances), availability (instance death is
routed around), and rolling deploys (drain one instance at a time). Without it,
horizontal scaling is just multiple uncoordinated servers.

## How does it work?

1. **Place the balancer** in front of the server fleet (nginx, HAProxy, a cloud LB,
   or a service mesh).
2. **Health-check instances**: only healthy instances receive traffic
   ([health-checks.md](health-checks.md)).
3. **Choose the policy**:
   - stateless: round-robin / least-connections / random — all equal
   - session-based: consistent-hash or cookie-pinned on the session id
     ([session-affinity.md](session-affinity.md))
4. **Drain on deploy**: stop sending new sessions, let existing ones finish, then
   remove the instance.

## Mental model

The load balancer is the **airline check-in counter manager**: it sends each
passenger (request/session) to the counter (instance) with the shortest line
(least-connections), skips counters that are closed (unhealthy), and, for
stateful services, remembers which counter holds which passenger's bags (affinity).

## MCP-specific behavior

- **Session-based protocol**: load balancing *without* affinity causes "unknown
  session" errors — the LB must pin sessions ([session-affinity.md](session-affinity.md)).
- **The 2026-07-28 stateless spec removes the constraint**: any instance, any
  request, plain round-robin — the spec's headline scaling win
  ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).
- **stdio needs no balancing** — each client already gets its own process.

## Example

HAProxy-style balancing (conceptual):

```haproxy
frontend mcp
    bind :8000
    default_backend mcp_servers

backend mcp_servers
    # stateless (2026-07-28): plain balancing
    balance roundrobin
    server s1 10.0.0.1:8000 check
    server s2 10.0.0.2:8000 check

    # session-based: pin by session id instead
    # balance hdr(Mcp-Session-Id)
```

## Industry-standard pattern

LB + health checks + draining is universal. Rules: **health checks must reflect
real readiness** ([health-checks.md](health-checks.md)), **prefer statelessness to
avoid affinity** ([scaling-fundamentals.md](scaling-fundamentals.md)), and **test
draining** so deploys don't drop sessions.

## Common mistakes

- **Round-robin over session-based servers** — the "unknown session" outage.
- **LBs with no health checks** — traffic to dead instances, retry storms.
- **LBs that terminate SSE/streaming poorly** — buffering or timing out long
  responses; configure for streaming
  ([01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)).
- **No drain on deploy** — mid-session requests killed mid-flight.

## Testing

- **Distribution tests**: load spreads across instances per the policy.
- **Failover tests**: killing one instance redirects traffic cleanly
  ([08-reliability-resilience/session-recovery.md](../08-reliability-resilience/session-recovery.md)).
- **Drain tests**: deploys complete without dropping sessions (session-based) or
  requests (stateless).

## Security considerations

- **The LB is a chokepoint** — it should terminate TLS, apply rate limits, and log
  ([11-communication-transport/tls.md](../11-communication-transport/tls.md),
  [08-reliability-resilience/rate-limiting.md](../08-reliability-resilience/rate-limiting.md)).
- **Don't balance on attacker-controlled headers** for security decisions.

## Related

- [session-affinity.md](session-affinity.md)
- [health-checks.md](health-checks.md)
- [scaling-fundamentals.md](scaling-fundamentals.md)
- [multi-server-and-gateway.md](multi-server-and-gateway.md)