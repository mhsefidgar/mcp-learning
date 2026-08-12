# Pagination

## What is it?

**Pagination** is returning results in **pages** instead of all at once. For MCP
list methods (`tools/list`, `resources/list`, `prompts/list`) the protocol defines a
**cursor** mechanism; for tool results (e.g. a `search_orders` tool) pagination is
your own design choice using the same ideas.

## Why does MCP need it?

Two reasons:

1. **Protocol listings can be huge**: a gateway exposing 5,000 tools shouldn't dump
   them all in one response. The protocol supports `cursor`-based pagination on
   `*/list` so clients can page through.
2. **Tool results can be huge**: a search returning 100,000 rows would blow context
   windows and slow everything down. Paginating tool results keeps responses bounded
   — and a model *can* page by calling the tool again with a cursor.

## How does it work?

**Protocol pagination (`*/list`)**: the client sends `cursor` in params; the server
returns `nextCursor` when more results exist.

```
client: tools/list {}
server: {tools: [...], nextCursor: "abc"}
client: tools/list {cursor: "abc"}
server: {tools: [...]}            ← no nextCursor → done
```

**Tool-result pagination** (your design): the tool takes `cursor` (and usually
`limit`) arguments, returns a page plus a `next_cursor` field:

```json
{"items": [...], "next_cursor": "page-2", "total": 100000}
```

Cursors should be **opaque tokens**, not page numbers: they encode position in the
dataset (e.g. "last seen id") so inserts/deletes between pages don't shift results.

## Mental model

Pagination is **bookmarking in a book whose pages can change**: a cursor is a
bookmark that says "I was here", robust to the book being edited. Page numbers are
"turn to page 5" — fragile when pages shift.

## MCP-specific behavior

- **`cursor`/`nextCursor` on list methods is protocol-defined** (2025-06-18+ spec;
  earlier spec versions had experimental pagination).
- **Clients should handle both paginated and non-paginated servers** — a server may
  return everything without a `nextCursor`.
- **Pagination must not affect routing**: names/URIs resolve identically across pages
  ([03-routing-dispatch/02-tool-routing.md](../03-routing-dispatch/02-tool-routing.md)).
- **Tool-result pagination is entirely your design** — the protocol defines no
  result-pagination fields.

## Example

FastMCP tool with cursor pagination:

```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("search")

@mcp.tool
def search_orders(cursor: str | None = None, limit: int = 100) -> dict:
    """Search orders. Returns {items, next_cursor, total}.

    Pass next_cursor from a previous call to get the next page.
    """
    if not 1 <= limit <= 500:
        raise ToolError("limit must be between 1 and 500")
    items, next_cursor = db.search_page(cursor=cursor, limit=limit)
    return {"items": items, "next_cursor": next_cursor, "total": db.count()}
```

Keys to a correct implementation:
- `next_cursor` is `None`/absent on the last page.
- The cursor encodes position (`last_seen_id`), not an offset.
- The same `limit`/`cursor` combination is deterministic.

## Industry-standard pattern

Cursor (keyset) pagination is the standard for large, changing datasets — **Stripe**,
**GitHub API**, **Slack** all use opaque cursors; offset/limit is discouraged for
production at scale (see [10-scaling-performance/pagination-at-scale.md](../10-scaling-performance/pagination-at-scale.md)).
Opaque cursors also hide implementation details (a nice security bonus).

## Common mistakes

- **Offset-based pages** (`page=2&size=100`) — duplicates/skips when data changes.
- **Non-opaque cursors** — base64-encoded internal ids leak structure; clients
  shouldn't be able to forge them (sign or use server-side state).
- **Forgetting the terminal page** — no `next_cursor` means "done"; clients loop
  forever if you never signal it.
- **Huge default page sizes** — cap `limit` (see [large-resources.md](../05-resource-engineering/large-resources.md)).
- **Pagination that changes result order** — always order by a stable key.

## Testing

- **Page walk tests**: iterate every page via `next_cursor`; assert union == full
  dataset, no duplicates, no gaps.
- **Mutation-between-pages tests**: insert/delete between page fetches; cursor
  pagination stays consistent.
- **Termination tests**: last page has no `next_cursor`; empty dataset → one empty
  page.
- **Limit validation tests**: `limit` bounds enforced.

## Debugging

- Duplicates across pages → unstable ordering or offset pagination.
- Infinite client loops → the server keeps returning `next_cursor` on the last page.
- In Inspector, list a large catalog and watch for `nextCursor` in responses.

## Security considerations

- **Cursors can be attack surface**: if they're opaque tokens, validate them (don't
  trust client-supplied positions blindly); if they encode data, sign them.
- **Pagination is a DoS control**: bounded pages keep responses small
  ([08-reliability-resilience/backpressure.md](../08-reliability-resilience/backpressure.md)).
- Don't leak data via cursor contents (e.g. raw database ids).

## Related concepts

- [filtering.md](filtering.md) · [sorting.md](sorting.md) — the query trio
- [05-resource-engineering/large-resources.md](../05-resource-engineering/large-resources.md)
- [10-scaling-performance/pagination-at-scale.md](../10-scaling-performance/pagination-at-scale.md)
- [02-primitives/tools.md](../02-primitives/tools.md)