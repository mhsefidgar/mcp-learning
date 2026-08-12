# Pagination (for Resources)

## What is it?

**Pagination** for resources happens at two levels:

1. **Catalog pagination** — `resources/list` (and `resources/templates/list`) can
   return pages via the protocol's `cursor` mechanism, exactly like `tools/list`.
2. **Content pagination** — the *content* of a huge resource can be too big for one
   read; you design chunked reads (e.g. `resources://logs?offset=...` or a
   `read_log_page` tool).

## Why does MCP need it?

Two different scale problems:

- **Many resources**: a gateway exposing 10,000 URIs shouldn't dump them all in one
  response — `resources/list` needs cursor pagination.
- **Huge resources**: a 50 MB log file as one `resources/read` blows context and
  memory — content needs chunking
  ([large-resources.md](large-resources.md)).

## How does it work?

**Catalog pagination** (protocol-defined):

```
client: resources/list {}
server: {resources: [...], nextCursor: "c1"}
client: resources/list {cursor: "c1"}
server: {resources: [...]}              ← no nextCursor → done
```

**Content chunking** (your design): either the resource exposes chunk parameters in
its URI (`logs://svc?from=0&count=1000`) or you provide tools
(`read_log_range(start, end)`). Both are conventions, not protocol.

## Mental model

The same bookmark idea as tool pagination
([04-tool-engineering/pagination.md](../04-tool-engineering/pagination.md)): cursor
for the catalog (bookmark in a changing list), chunk parameters for content (page
numbers into a fixed file). Keep the two mechanisms separate in your head — they
solve different problems.

## MCP-specific behavior

- **Cursor pagination on list methods is protocol-defined.**
- **Templates paginate too**: a server with thousands of templates pages
  `resources/templates/list`.
- **Content chunking is not protocol-defined** — design it and document it in the
  resource description so the model knows chunking exists.

## Example

Catalog pagination is SDK-handled on the client (FastMCP `Client.list_resources()`
pages automatically up to `max_pages`). Server-side, the SDK handles cursor state for
you in most implementations; the important design work is content chunking:

```python
from fastmcp import FastMCP

mcp = FastMCP("logs")

@mcp.resource("logs://svc")
def logs_index() -> str:
    """Log index: total size + how to page. Content chunking is URI-driven."""
    size = get_log_size("svc")
    return f'{{"service": "svc", "size_bytes": {size}, "page_size": 4096, "uri": "logs://svc?start=0&count=4096"}}'

@mcp.resource("logs://svc?start={start}&count={count}")
def log_page(start: int, count: int) -> str:
    """A page of the service log: bytes [start, start+count)."""
    return read_log_range("svc", start, count)
```

## Industry-standard pattern

Cursor pagination for catalogs, range-based chunking for content — the same split as
**ListObjects vs. GET-range in object stores**, **SQL LIMIT/OFFSET vs. streaming
reads**. Rules: bounded page sizes, documented chunk semantics, deterministic pages
([04-tool-engineering/pagination.md](../04-tool-engineering/pagination.md)).

## Common mistakes

- **Returning unbounded content** from `resources/read` (see
  [large-resources.md](large-resources.md)).
- **Catalog pagination bugs** — non-opaque cursors, missing terminal page.
- **Chunk APIs the model can't discover** — document chunking in the resource
  description.
- **Chunking by line number without an index** — O(n) scans per page; use offsets or
  an index.

## Testing

- **Catalog page-walk tests**: union of pages == full catalog, no dupes/gaps
  ([15-testing/resource-testing.md](../15-testing/resource-testing.md)).
- **Content-chunk tests**: ranges are correct, non-overlapping, and cover the whole
  content.
- **Boundary tests**: empty content, content smaller than one page, exact-multiple
  content.

## Debugging

- Duplicates across catalog pages → unstable ordering (add a stable sort key).
- A huge read hanging the server → check whether the handler materializes the whole
  file ([large-resources.md](large-resources.md)).

## Security considerations

- **Chunk parameters are input** — validate `start`/`count` bounds (negative or
  enormous values are memory bombs).
- **Cursor contents** should be opaque and unforgeable.

## Related concepts

- [large-resources.md](large-resources.md)
- [04-tool-engineering/pagination.md](../04-tool-engineering/pagination.md)
- [10-scaling-performance/pagination-at-scale.md](../10-scaling-performance/pagination-at-scale.md)