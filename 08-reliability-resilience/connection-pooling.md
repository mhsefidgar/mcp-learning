# Connection Pooling

> **General engineering pattern.** Connection pooling is not an MCP feature — it's
> how HTTP/DB/backend clients reuse connections instead of opening one per request.

## What is it?

**Connection pooling** reuses a fixed set of connections rather than opening a new
one for every request. For HTTP transports, each MCP request would otherwise pay
TCP + TLS handshake costs; pooling amortizes that across many requests.

## Why does MCP need it?

Three costs per new connection:

1. **Latency**: TCP handshake (+ TLS round trips) before a single tool call —
   significant for chatty agent traffic.
2. **Server load**: each connection consumes sockets, memory, and (in the
   session-based spec) session state — thousands of short-lived connections are a
   classic server killer.
3. **Rate limits / port exhaustion**: clients (and NATs) run out of ephemeral
   ports under connection churn.

An agent making 50 tool calls should use **one pooled connection**, not 50.

## How does it work?

1. **Open a bounded set of connections** (pool size), typically per server.
2. **Check out** a connection per request; **return** it when done.
3. **Reuse**: the next request picks an idle connection from the pool.
4. **Manage lifecycle**: idle timeout (close unused), health checks (evict dead),
   and **waiting vs. failing** when the pool is exhausted (bounded wait, then
   fail-fast with backpressure — [backpressure.md](backpressure.md)).

HTTP/2 (and the stateless 2026-07-28 spec) reduce this further: multiplexed streams
over fewer connections, and no session state per connection
([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).

## Mental model

Connection pooling is **valet parking**: a small lot of cars (connections) is kept
ready; you hand over your key (request), a car is already there (no startup wait),
and the lot manages washing (keep-alive), checking (health), and towing (eviction)
— instead of everyone renting a brand-new car per trip.

## MCP-specific behavior

- **HTTP clients pool by default**: FastMCP's `Client` (httpx), the TS SDK, and the
  Java SDK (JDK HttpClient) all pool HTTP connections under the hood — but only if
  you *reuse the client object* across calls. Creating a new `Client` per call
  defeats the pool.
- **stdio has no pooling**: one process per client — the "pool" is the process
  lifetime ([01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)).
- **Session-based spec**: pooled connections still carry `Mcp-Session-Id` state —
  the pool must route requests for the same session to the same connection
  ([10-scaling-performance/session-affinity.md](../10-scaling-performance/session-affinity.md)).

## Example

Reuse the client — don't create one per call:

```python
# GOOD: one client, many calls → pooled connection reused
async with Client("http://backend/mcp") as client:
    for symbol in symbols:
        result = await client.call_tool("quote", {"symbol": symbol})
```

```python
# BAD: a new client per call → new connection, new handshake, new session each time
for symbol in symbols:
    async with Client("http://backend/mcp") as client:
        result = await client.call_tool("quote", {"symbol": symbol})
```

## Industry-standard pattern

Pooling is universal (DB connection pools, HTTP keep-alive, gRPC channels). The
rules: bound the pool size, reuse clients, health-check connections, close idle
ones, and decide the pool-full behavior explicitly (wait vs. fail fast).

## Common mistakes

- **Creating a client per request** — the #1 pooling mistake in MCP code.
- **Unbounded pool size** — socket exhaustion under load.
- **No idle timeout** — stale connections accumulate.
- **Pool-full = hang** — unbounded waiting; fail fast after a bounded wait.
- **Ignoring dead connections** — retrying on a stale pooled connection; evict and
  reconnect.

## Testing

- **Reuse tests**: N calls over one client use ≤ K connections (instrument the
  transport).
- **Eviction tests**: a dead connection is detected and replaced.
- **Pool-full tests**: exhausted pools wait briefly then fail fast.
- **Session tests** (session-based spec): pooled connections preserve session
  routing.

## Security considerations

- **Pooled connections carry auth/session state** — ensure credentials are scoped
  per principal and that pooled connections can't leak one tenant's session to
  another.
- **Connection reuse across principals** can leak state if the server keys session
  state by connection rather than by identity.

## Related

- [bulkheads.md](bulkheads.md)
- [10-scaling-performance/connection-pooling.md](../10-scaling-performance/connection-pooling.md)
- [10-scaling-performance/session-affinity.md](../10-scaling-performance/session-affinity.md)
- [01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)