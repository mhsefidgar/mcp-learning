# Resource Caching, Distributed Caching & Invalidation

## What is it?

**Caching at scale** is the question of where cached data lives when the server is a
fleet: in-process caches (fast, per-instance, duplicated) vs. **distributed caches**
(shared, consistent, one extra hop). And how caches stay fresh:
**invalidation** — the hard part.

## Why does MCP need it?

At scale, the cache *strategy* changes the architecture:

- One instance: an in-process dict is fine.
- Ten instances: ten copies of the catalog — still fine for immutable data (each
  instance fetches once); *wrong* for mutable data (ten inconsistent copies, ten
  times the fetch).
- Distributed cache (Redis): one copy shared by all instances — consistent, but a
  new dependency and a new failure mode.

The catalog (`tools/list`, `resources/list`) is the highest-value cache at scale:
it's stable, hot, and identical across instances
([08-reliability-resilience/caching.md](../08-reliability-resilience/caching.md)).

## How does it work?

1. **Classify the data**: immutable (catalog, static resources) vs. mutable
   (order status, config that changes).
2. **Immutable → in-process cache** with TTL; no invalidation needed.
3. **Mutable → distributed cache (or no cache)** keyed by resource/URI, with
   **explicit invalidation** on write.
4. **Invalidation patterns**:
   - **Write-through invalidation**: the writer deletes/updates the cache entry in
     the same operation.
   - **TTL staleness**: accept staleness for a bounded window.
   - **Pub/sub invalidation**: a change event busts the cache on all instances
     ([05-resource-engineering/subscriptions.md](../05-resource-engineering/subscriptions.md),
     [06-agent-interaction/notifications.md](../06-agent-interaction/notifications.md)).
5. **Protect the origin**: single-flight per key so a cache miss doesn't stampede
   the source ([08-reliability-resilience/caching.md](../08-reliability-resilience/caching.md)).

## Mental model

Caching at scale is the **library system**: each branch (instance) keeps its own
fast shelf (in-process cache) for popular books that never change; books that
change go in the central catalog (distributed cache); and when a book changes, the
librarian sends a recall notice (invalidation) to every branch.

## MCP-specific behavior

- **The catalog is the crown jewel**: cache `tools/list`/`resources/list`
  results aggressively; the 2026-07-28 spec even ships cache hints (`ttlMs`,
  `cacheScope`) on list responses
  ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).
- **`listChanged` notifications are the invalidation channel** — subscribe to them
  server-side to bust catalog caches
  ([06-agent-interaction/notifications.md](../06-agent-interaction/notifications.md)).
- **Never cache per-user data in a shared cache without the user in the key**
  ([08-reliability-resilience/caching.md](../08-reliability-resilience/caching.md)).

## Example

Distributed catalog cache with pub/sub invalidation (conceptual):

```python
async def get_catalog(redis):
    cached = await redis.get("catalog:tools")
    if cached:
        return json.loads(cached)
    tools = await expensive_catalog_fetch()          # one instance fetches...
    await redis.set("catalog:tools", json.dumps(tools), ex=300)
    return tools

# on any registration change:
async def on_catalog_change(redis, pubsub):
    await redis.delete("catalog:tools")             # bust everywhere
    await pubsub.publish("catalog.changed", "tools")
```

## Industry-standard pattern

TTL + write-through invalidation + pub/sub busting is the standard cache stack
(Redis, Memcached, CDNs with purge APIs). Rules: **cache immutable data in-process**,
**share mutable data through a distributed cache**, **invalidate at the write**, and
**never let a cache miss stampede the origin**.

## Common mistakes

- **In-process caching of mutable data at fleet scale** — inconsistent copies.
- **No invalidation** — stale data served forever (the worst kind of wrong).
- **Cache-as-truth** — the cache must be reconstructible from the source at any
  time; it's a cache, not the database.
- **Stampedes on expiry** — single-flight or jittered TTLs
  ([08-reliability-resilience/exponential-backoff.md](../08-reliability-resilience/exponential-backoff.md)).
- **A distributed cache as a single point of failure** — treat Redis like the
  critical dependency it is (replicas, fallback to origin on cache outage —
  [fallback](../08-reliability-resilience/fallback.md)).

## Testing

- **Consistency tests**: after a write, all instances serve the new value within
  the invalidation window.
- **Stampede tests**: N concurrent misses → one origin fetch.
- **Outage tests**: cache down → server still serves from origin (degraded, not
  dead).
- **Per-user isolation tests**: cached per-user data never crosses users.

## Security considerations

- **Cached data is shared data**: never cache secrets or per-user rows without
  identity-scoped keys and authorization on read
  ([14-security/authorization.md](../14-security/authorization.md)).
- **Cache poisoning**: one bad write served to everyone — validate before caching.

## Related

- [08-reliability-resilience/caching.md](../08-reliability-resilience/caching.md)
- [06-agent-interaction/notifications.md](../06-agent-interaction/notifications.md)
- [large-data-at-scale.md](large-data-at-scale.md)
- [multi-server-and-gateway.md](multi-server-and-gateway.md)