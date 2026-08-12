# Large Resources, Pagination at Scale & Tool Fan-Out

## What is it?

Three scale problems for *data movement* in MCP:

- **Large resource handling**: multi-MB content must not be materialized per read
  ([05-resource-engineering/large-resources.md](../05-resource-engineering/large-resources.md)).
- **Pagination at scale**: cursor pagination that stays correct and cheap as data
  grows ([04-tool-engineering/pagination.md](../04-tool-engineering/pagination.md)).
- **Tool fan-out**: one logical request that fans out to many tool calls or many
  backends — and how to bound and orchestrate it.

## Why does MCP need it?

At scale, the naive versions stop working: a `resources/read` that loads a 50 MB
file per call exhausts memory; offset pagination on a 10M-row table times out;
fan-out without limits spawns unbounded work. Each has a *bounded* design.

## How does it work?

**Large resources at scale:**

- Slice at the source: range reads, streaming, or summary-first designs
  ([05-resource-engineering/large-resources.md](../05-resource-engineering/large-resources.md)).
- Never build the full content in memory just to truncate it.
- Consider object-store references for truly big content (signed URLs out-of-band).

**Pagination at scale:**

- **Cursor/keyset pagination**, not offsets: `WHERE id > last_seen ORDER BY id`
  with an index — O(page) instead of O(offset) ([04-tool-engineering/pagination.md](../04-tool-engineering/pagination.md)).
- Stable ordering + tiebreaker for correctness across pages.
- The 2026-07-28 spec makes list results cacheable (TTL hints), so paged catalogs
  are cheap to re-fetch ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).

**Tool fan-out:**

- A single agent turn can issue many parallel tool calls
  ([06-agent-interaction/README.md](../06-agent-interaction/README.md)) — bound
  client-side concurrency and server-side pools
  ([concurrency-and-workers.md](concurrency-and-workers.md)).
- A proxy fanning one request to many backends
  ([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)) —
  bound fan-out width, add per-backend timeouts and partial-failure handling
  ([08-reliability-resilience/partial-failures.md](../08-reliability-resilience/partial-failures.md)).

## Mental model

Scale-safe data movement is **never move the whole lake, only the needed slices**:
range requests for files, keyset pagination for lists, and bounded fan-out with
per-branch timeouts for parallel work. The lake stays in the lake; the model gets
buckets.

## MCP-specific behavior

- **Cursor pagination on `*/list` is protocol-defined** — servers should implement
  it before catalogs grow ([01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)).
- **Large content has no protocol answer** — it's your design
  ([05-resource-engineering/large-resources.md](../05-resource-engineering/large-resources.md)).
- **Fan-out is client/proxy logic** — the protocol happily carries many concurrent
  requests; you decide how many.

## Example

Keyset (cursor) pagination against a large table:

```python
async def search_page(cursor: str | None, limit: int = 100):
    # cursor encodes the last seen id: "42" → WHERE id > 42
    last_id = int(cursor) if cursor else 0
    rows = await db.fetch(
        "SELECT * FROM orders WHERE id > $1 ORDER BY id LIMIT $2",
        last_id, limit + 1,
    )
    next_cursor = str(rows[-2].id) if len(rows) > limit else None
    return rows[:limit], next_cursor
```

## Industry-standard pattern

Keyset pagination + range reads + bounded fan-out with per-branch deadlines are
standard (database pagination, S3 ranges, async fan-out frameworks). Rules: **index
the cursor column**, **cap page and fan-out sizes**, **timeout every branch**, and
**aggregate partial results explicitly**
([08-reliability-resilience/partial-failures.md](../08-reliability-resilience/partial-failures.md)).

## Common mistakes

- **Offset pagination at scale** — O(n) scans, drift on inserts.
- **Unbounded page sizes** — a `limit=10_000_000` argument is a memory bomb;
  cap it server-side ([04-tool-engineering/validation.md](../04-tool-engineering/validation.md)).
- **Unbounded fan-out** — 500 parallel backends with no cap or timeout.
- **Full-content reads** — materializing huge resources
  ([05-resource-engineering/large-resources.md](../05-resource-engineering/large-resources.md)).

## Testing

- **Pagination tests at scale**: page walks over large tables stay fast (indexed)
  and correct ([15-testing/resource-testing.md](../15-testing/resource-testing.md)).
- **Fan-out tests**: caps and timeouts hold under wide fan-out.
- **Memory tests**: large reads don't balloon RSS.

## Security considerations

- **Cursors and range params are input** — validate bounds (negative, huge) and
  keep cursors opaque/unforgeable.
- **Fan-out amplifies both cost and failure** — per-backend auth and quotas.

## Related

- [05-resource-engineering/large-resources.md](../05-resource-engineering/large-resources.md)
- [04-tool-engineering/pagination.md](../04-tool-engineering/pagination.md)
- [concurrency-and-workers.md](concurrency-and-workers.md)
- [08-reliability-resilience/partial-failures.md](../08-reliability-resilience/partial-failures.md)