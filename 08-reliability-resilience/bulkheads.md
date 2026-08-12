# Bulkheads

> **General engineering pattern.** Bulkheads are not an MCP feature — they're
> resource isolation applied to MCP servers (per-tool pools) and clients (per-server
> pools).

## What is it?

A **bulkhead** partitions resources so a failure in one partition can't starve the
others. On a ship, bulkheads divide the hull into watertight compartments — one
flooded compartment doesn't sink the whole ship. In an MCP server: separate worker
pools per tool/tenant; in a client: separate connection pools per server.

## Why does MCP need it?

Without isolation, one bad tool can take down the server: a `render` tool that
spawns unbounded threads eats the pool, and `get_order` (innocent) starts timing
out too. Worse, a single misbehaving client can exhaust the shared pool and starve
every other client. Bulkheads make failures **contained**: the flooding compartment
degrades; the rest of the ship sails on.

## How does it work?

1. **Identify the partitions**: per-tool (expensive vs. cheap), per-client/tenant,
   per-backend.
2. **Give each partition its own resource pool**: its own worker threads/tasks, its
   own connection pool, its own queue, its own circuit breaker
   ([circuit-breakers.md](circuit-breakers.md)).
3. **Bound each pool** (size, queue depth, timeout).
4. **On overload, the partition rejects** (backpressure signal,
   [backpressure.md](backpressure.md)) without touching other partitions.

```
┌───────────────────────────────┐
│  MCP server                  │
│  ┌───────────┐ ┌───────────┐ │
│  │ render    │ │ get_order │ │   separate worker pools
│  │ pool (2)  │ │ pool (10) │ │
│  └───────────┘ └───────────┘ │
│  render saturates ──► only render degrades; get_order unaffected
└───────────────────────────────┘
```

## Mental model

Bulkheads are the **watertight doors of a ship** — or the **separate lanes of a
highway**: a crash in the left lane doesn't stop the right lane. The essence is
*shared nothing between partitions that must not fail together*: separate pools,
separate queues, separate breakers.

## MCP-specific behavior

- **Nothing protocol-level.** MCP has no notion of workers or pools; this is your
  server's execution model
  ([10-scaling-performance/worker-pools.md](../10-scaling-performance/worker-pools.md)).
- **The natural MCP partition is the tool**: one pool for heavy tools, one for
  light; one for destructive tools, one for reads.
- **Client-side**: a multi-server client gives each server its own connection pool
  so one dead server doesn't exhaust connections for the others
  ([connection-pooling.md](connection-pooling.md),
  [10-scaling-performance/multi-server-architectures.md](../10-scaling-performance/multi-server-architectures.md)).

## Example

Per-tool worker pools (conceptual — see `repository/go/resilience` for a Go
implementation with goroutines):

```python
import asyncio

# Each pool is a semaphore-bounded partition with its own queue.
render_pool = asyncio.Semaphore(2)    # heavy: only 2 concurrent
light_pool = asyncio.Semaphore(20)    # light: up to 20 concurrent

@mcp.tool
async def render(scene: str) -> str:
    """Heavy operation — its own pool. Saturating it does not block light tools."""
    async with render_pool:
        return await do_render(scene)

@mcp.tool
async def get_order(order_id: int) -> dict:
    """Light operation — separate pool, unaffected by render saturation."""
    async with light_pool:
        return db.get(order_id)
```

## Industry-standard pattern

Bulkheads are standard in production systems (Hystrix thread pools, connection
pool partitioning, per-tenant Kubernetes namespaces/quotas). The rules: **partition
by failure domain**, **size pools explicitly**, **bound queue lengths**, and **give
each partition its own breaker and metrics** so a partition's health is visible.

## Common mistakes

- **One shared pool for everything** — the exact anti-pattern.
- **Pools that are too small** — legitimate concurrency rejected (tune with
  load testing).
- **Partitioning by name only** — if the pools share a thread pool underneath,
  there's no isolation.
- **Forgetting the queue** — a pool with an unbounded queue is a memory bomb.
- **No per-partition observability** — you can't see which compartment is flooding.

## Testing

- **Isolation tests**: saturate one partition; assert others keep working
  ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **Bound tests**: partition queues stay bounded under overload.
- **Recovery tests**: after the flooding partition clears, it recovers without
  restarting the server.

## Security considerations

- **Bulkheads are a DoS control**: a malicious client hammering one tool can't
  starve other tenants' tools.
- **Per-tenant partitioning** prevents noisy-neighbor issues in multi-tenant MCP
  deployments ([10-scaling-performance/README.md](../10-scaling-performance/README.md)).

## Related

- [backpressure.md](backpressure.md)
- [circuit-breakers.md](circuit-breakers.md)
- [connection-pooling.md](connection-pooling.md)
- [10-scaling-performance/worker-pools.md](../10-scaling-performance/worker-pools.md)