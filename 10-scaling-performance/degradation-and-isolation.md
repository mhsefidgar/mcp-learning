# Graceful Degradation, Failure Isolation & Memory Management

## What is it?

How a loaded or partially-failing MCP system stays **alive and useful**:

- **Graceful degradation**: when capacity drops, serve *less* well rather than not
  at all (read-only mode, cached answers, longer queues, shedding non-essential
  work) ([08-reliability-resilience/fallback.md](../08-reliability-resilience/fallback.md)).
- **Failure isolation**: one broken component must not take down the rest —
  bulkheads, per-backend breakers, per-tenant pools
  ([08-reliability-resilience/bulkheads.md](../08-reliability-resilience/bulkheads.md),
  [08-reliability-resilience/circuit-breakers.md](../08-reliability-resilience/circuit-breakers.md)).
- **Load shedding**: reject *selected* work under saturation — shed cheap/safe work
  first, or the lowest-priority caller
  ([backpressure-and-quotas.md](backpressure-and-quotas.md)).
- **Memory management**: bounded queues, bounded results, no accidental retention —
  the silent killer of long-running servers.

## Why does MCP need it?

At scale, partial failure is the *default state*: some backend down, one instance
OOMing, a tenant bursting. The question is whether the system degrades gracefully
or collapses. A system with good degradation returns "degraded but correct" answers
and survives; a system without it returns "connection refused" to everyone.

## How does it work?

1. **Know your modes**: define degraded states (read-only, cache-only,
   limited-tools) and what triggers them (backends down, queue depth, memory).
2. **Isolate**: per-tool/per-backend pools and breakers
   ([08-reliability-resilience/bulkheads.md](../08-reliability-resilience/bulkheads.md)).
3. **Shed deliberately**: under load, reject by priority, never randomly
   ([backpressure-and-quotas.md](backpressure-and-quotas.md)).
4. **Bound memory**: bounded queues, capped results, streaming large data
   ([large-data-at-scale.md](large-data-at-scale.md)), and result TTLs (don't hold
   every response forever).
5. **Signal degradation**: return results marked "degraded"/"cached"/"read-only" so
   the model can adjust ([08-reliability-resilience/fallback.md](../08-reliability-resilience/fallback.md)).

## Mental model

Degradation is the **power-company rolling blackout**: instead of the whole grid
dying, carefully chosen blocks are shed in rotation, hospitals (critical tools)
stay powered, and everyone knows the schedule (signals). The alternative — no
shedding — is a full-grid collapse.

## MCP-specific behavior

- **Nothing protocol-level** — degradation is your server's policy. The `isError`
  result and honest messages are how you signal it to the model.
- **Health checks** (`/healthz` liveness vs. readiness) tell load balancers and
  discovery which instances can serve what
  ([multi-server-and-gateway.md](multi-server-and-gateway.md)).
- **In the 2026-07-28 stateless world**, degradation is simpler: shed any request
  on any instance; no session state to protect.

## Example

A read-only degraded mode:

```python
READ_ONLY = False   # flipped by ops when the write backend is down

@mcp.tool
def create_order(customer: str, amount: float) -> dict:
    """Create an order."""
    if READ_ONLY:
        raise ToolError("write operations paused (degraded mode) — orders are read-only right now")
    return db.create(customer=customer, amount=amount)
```

## Industry-standard pattern

Graceful degradation, circuit breaking, load shedding, and memory bounds are
standard (cloud multi-AZ degradation, streaming backpressure, JVM/GC tuning,
Kubernetes resource limits). Rules: **degrade visibly** (never silently), **shed by
priority**, **isolate by failure domain**, and **measure memory as a first-class
operational metric**.

## Common mistakes

- **Silent degradation** — the model acts on degraded data as if it were fresh.
- **All-or-nothing** — one backend down takes the whole server down.
- **Memory leaks from caches/queues** — unbounded growth, no TTL, no eviction
  ([08-reliability-resilience/caching.md](../08-reliability-resilience/caching.md)).
- **Random shedding** — dropping the *most important* work under load.
- **Readiness lying** — health checks that report ready when the server can't
  serve.

## Testing

- **Degradation tests**: trigger degraded mode; assert defined behavior and honest
  signals ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **Isolation tests**: one pool/breaker tripping doesn't affect others.
- **Memory tests**: sustained load keeps RSS bounded (assert in CI).
- **Health-check tests**: liveness/readiness reflect real state.

## Security considerations

- **Degraded modes must not weaken authz** — "read-only" is not "open"
  ([14-security/authorization.md](../14-security/authorization.md)).
- **Shedding decisions can be gamed** — shed by authenticated priority, not by
  request characteristics an attacker controls.

## Related

- [08-reliability-resilience/fallback.md](../08-reliability-resilience/fallback.md)
- [08-reliability-resilience/bulkheads.md](../08-reliability-resilience/bulkheads.md)
- [backpressure-and-quotas.md](backpressure-and-quotas.md)
- [performance-engineering.md](performance-engineering.md)