# Scaling Streamable HTTP: Connections, Pooling, Downstreams, Databases

## What is it?

Connection management at scale — the *other* resource dimension next to CPU/memory:
how many connections a server can hold, how clients reuse them
([08-reliability-resilience/connection-pooling.md](../08-reliability-resilience/connection-pooling.md)),
and how the server manages its own connections to **downstream services and
databases**.

## Why does MCP need it?

Connections are finite and expensive:

- **Inbound**: each Streamable HTTP client may hold a connection (and in the
  session-based spec, a session with server-side state) — a busy fleet of agents
  can exhaust sockets, file descriptors, and memory ([01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)).
- **Outbound**: every tool that calls an API or database *per call* pays a
  connection cost — pooling is a huge latency/throughput win
  ([08-reliability-resilience/connection-pooling.md](../08-reliability-resilience/connection-pooling.md)).
- **Databases**: connection-per-request is a classic production killer; pooled
  DB connections are the standard fix.

## How does it work?

**Inbound (server side):**

1. Bound concurrent connections (server limit, LB limits).
2. Idle-timeout connections; enforce keep-alive policy.
3. Session-based spec: bound *sessions* (each holds state); expire stale ones
   ([01-fundamentals/09-sessions-and-lifecycle.md](../01-fundamentals/09-sessions-and-lifecycle.md)).
4. The stateless 2026-07-28 spec: connections carry no state — connection churn is
   harmless, and HTTP/2 multiplexing reduces connection count
   ([scaling-fundamentals.md](scaling-fundamentals.md)).

**Outbound (tool side):**

1. Reuse HTTP clients across calls (one pool per backend)
   ([08-reliability-resilience/connection-pooling.md](../08-reliability-resilience/connection-pooling.md)).
2. Bound pool sizes; health-check and evict dead connections.
3. **Database connection pooling**: a bounded pool (e.g. `psycopg_pool`,
   HikariCP, `pgbouncer`), sized by the concurrency limit
   ([concurrency-and-workers.md](concurrency-and-workers.md)).

## Mental model

Connections are **phone lines**: the server has a finite switchboard (inbound
lines), and your tools shouldn't dial a new number for every single request
(outbound) — they keep a few lines permanently open (pools). At scale, counting
"lines in use" is as important as counting CPU.

## MCP-specific behavior

- **Session-based HTTP**: an idle session holds memory; expire sessions
  aggressively and treat connection limits as session limits.
- **stdio**: no connection management needed (process = connection)
  ([01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)).
- **The stateless spec**: the *inbound* problem mostly disappears (no per-session
  state) — the *outbound* problem (tool → downstream) remains yours forever.

## Example

Database pool sized to the server's concurrency:

```python
from psycopg_pool import AsyncConnectionPool

# One pool for the whole server, sized to the concurrency limit.
pool = AsyncConnectionPool("postgresql://user:pass@db/app", min_size=4, max_size=16)

@mcp.tool
async def search_orders(query: str, limit: int = 10) -> list[dict]:
    """Search orders. Uses the shared pooled connection."""
    async with pool.connection() as conn:
        rows = await conn.execute("SELECT * FROM orders WHERE ...", (query, limit))
        return rows.fetchall()
```

## Industry-standard pattern

Connection limits + keep-alive + pooling + idle expiry is the standard pattern
(HTTP keep-alive, HikariCP/psycopg pools, pgbouncer, K8s connection limits). Rules:
**pool by destination**, **size pools to concurrency**, **evict dead connections**,
**expire idle inbound sessions**, and **expose connection counts as metrics**
([09-observability-telemetry/metrics.md](../09-observability-telemetry/metrics.md)).

## Common mistakes

- **Per-call connections** (client or DB) — the classic bottleneck
  ([08-reliability-resilience/connection-pooling.md](../08-reliability-resilience/connection-pooling.md)).
- **Unbounded pools** — socket/file-descriptor exhaustion.
- **Pool bigger than the concurrency limit** — threads waiting on connections that
  wait on threads.
- **No idle expiry** — leaked/stale connections accumulate.
- **Pool exhaustion = hang** — bound waits, fail fast
  ([08-reliability-resilience/backpressure.md](../08-reliability-resilience/backpressure.md)).

## Testing

- **Pool tests**: N calls reuse a bounded set of connections
  ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **Eviction tests**: dead connections are detected and replaced.
- **Exhaustion tests**: pool-full behavior is wait-then-fail-fast.
- **Connection-count metrics tests**: counts are visible and bounded.

## Security considerations

- **Pooled connections carry credentials/state** — scope pools per principal where
  tenants differ; never let pooled connections leak one tenant's session to
  another.
- **Inbound connection floods are a DoS vector** — limits + timeouts are security
  controls.

## Related

- [08-reliability-resilience/connection-pooling.md](../08-reliability-resilience/connection-pooling.md)
- [concurrency-and-workers.md](concurrency-and-workers.md)
- [performance-engineering.md](performance-engineering.md)
- [01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)