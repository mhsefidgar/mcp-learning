# Caching

> **General engineering pattern.** Caching is not an MCP protocol feature. (The
> 2026-07-28 spec adds *cache hints* — `ttlMs`/`cacheScope` — on list results, but
> caching strategy remains yours.)

## What is it?

**Caching** is storing the result of an expensive operation so repeat calls are
cheap: the tool catalog, a slow query's answer, a rendered report. In MCP systems
the highest-value caches are usually:

- **The catalog**: `tools/list` / `resources/list` results — stable, repeatedly
  fetched, expensive to regenerate.
- **Read-only tool results**: `get_order(123)` when orders don't change often.
- **Static/dynamic resources** ([05-resource-engineering/README.md](../05-resource-engineering/README.md)).

## Why does MCP need it?

Models re-fetch constantly: the same tool list, the same config resource, the same
"current status" — often every turn of a conversation. Each uncached call costs
server CPU, downstream API calls, and latency. Caching turns repeated identical
requests into in-memory hits — the single biggest latency win for most MCP servers.

## How does it work?

1. **Decide what's cacheable**: stable keys (tool names, URIs), stable values
   (catalogs), bounded size.
2. **Choose the cache**: in-process dict (single instance), distributed cache
   (Redis — multi-instance, [10-scaling-performance/distributed-caching.md](../10-scaling-performance/distributed-caching.md)),
   or HTTP-level caching (reverse proxy).
3. **Set a TTL**: how long a value may be served stale. Trade-off: freshness vs.
   hit rate.
4. **Invalidate on change**: for mutable data, bust the cache when the source
   changes ([05-resource-engineering/subscriptions.md](../05-resource-engineering/subscriptions.md)).
5. **Protect against stampedes**: when a cached value expires and 50 requests hit
   the source at once — use single-flight (one fetch, many waiters).

## Mental model

Caching is a **notebook by the phone**: before making an expensive call, check the
notebook; if the answer is there and fresh enough, read it instead. The notebook has
a "written at" time (TTL) and gets torn out pages when facts change (invalidation).

## MCP-specific behavior

- **The catalog is the safest cache**: tool/resource/prompt lists change rarely and
  the `listChanged` notifications ([06-agent-interaction/notifications.md](../06-agent-interaction/notifications.md))
  give you invalidation for free.
- **The 2026-07-28 spec makes catalogs cacheable by design**: list responses carry
  `ttlMs` and `cacheScope` hints so clients can cache with confidence
  ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).
- **Don't cache per-user data in a shared cache** without keying by user — the
  classic leak.

## Example

A simple TTL cache for catalog listing (see `repository/go/resilience` for a fuller
implementation):

```python
import time

class TTLCache:
    def __init__(self, ttl_seconds: float):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, object]] = {}

    def get(self, key: str):
        entry = self._store.get(key)
        if entry and time.monotonic() - entry[0] < self._ttl:
            return entry[1]
        self._store.pop(key, None)
        return None

    def set(self, key: str, value: object) -> None:
        self._store[key] = (time.monotonic(), value)

_catalog_cache = TTLCache(ttl_seconds=30)

async def list_tools_cached():
    cached = _catalog_cache.get("tools")
    if cached is not None:
        return cached
    tools = await expensive_catalog_fetch()
    _catalog_cache.set("tools", tools)
    return tools
```

## Industry-standard pattern

TTL caches with explicit invalidation are standard (HTTP caching, CDNs, Redis).
Production rules: bounded size (LRU eviction), short-enough TTLs, single-flight
against stampedes, and **cache keys that include identity** when data is per-user.

## Common mistakes

- **Caching mutable data without invalidation** — stale results served forever.
- **No TTL** — entries live forever (or fill memory).
- **Unbounded cache size** — memory growth; bound + evict.
- **Caching per-user data without user in the key** — cross-user data leaks.
- **Stampede on expiry** — add single-flight or jittered TTLs.

## Testing

- **Hit/miss tests**: repeat calls hit the cache; the source is called once.
- **TTL tests**: after expiry, the source is called again.
- **Invalidation tests**: source change → cache busted → fresh result.
- **Per-user isolation tests**: user A's cached data never serves user B.

## Security considerations

- **Cache keys and values can leak**: never cache secrets; scope per-user data by
  authenticated identity; beware caching authorization decisions
  ([14-security/authorization.md](../14-security/authorization.md)).
- **Cache poisoning**: if a value is user-influenced and cached, one bad write
  serves everyone — validate before caching.

## Related

- [06-agent-interaction/notifications.md](../06-agent-interaction/notifications.md)
- [10-scaling-performance/distributed-caching.md](../10-scaling-performance/distributed-caching.md)
- [05-resource-engineering/subscriptions.md](../05-resource-engineering/subscriptions.md)
- [fallback.md](fallback.md) — a cache can serve as a degraded-mode fallback