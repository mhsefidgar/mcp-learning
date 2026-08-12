# Large Resources

## What is it?

A **large resource** is one whose content is too big to return in a single
`resources/read` — multi-megabyte logs, images, dataset dumps. The problem: MCP
results are JSON with content blocks, and both the wire and the model's context have
limits. Large resources need an explicit strategy.

## Why does MCP need it?

Three limits collide for large content:

1. **Context limits** — a model can't "read" 50 MB; it needs summaries, ranges, or
   structured slices.
2. **Response limits** — huge JSON responses are slow, memory-heavy, and often
   rejected by clients.
3. **Server limits** — materializing a 50 MB file per read kills server memory
   ([10-scaling-performance/memory-management.md](../10-scaling-performance/memory-management.md)).

## How does it work?

Choose a strategy per content type:

| Strategy | How | Best for |
|----------|-----|----------|
| **Chunked reads** | URI/parameters select a range (`logs://svc?start=0&count=4096`) | logs, files |
| **Summaries first** | the resource returns a summary/index; details via chunk URIs | big data, repos |
| **Binary references** | return a `resource` content block referencing a URI (client fetches out-of-band, e.g. an object-store URL) | images, binaries |
| **Pagination as content** | treat the resource as a paged collection | tables, datasets |

The common shape: **the canonical read returns a small, useful view** (index,
summary, first page) that *points* at the rest.

## Mental model

A large resource is a **library, not a book**: you don't hand the model all 5,000
pages — you hand it the catalog card, then lend out pages on request. The read
interface becomes "what do you want to see?" rather than "here is everything."

## MCP-specific behavior

- **The `resource` content block type** is protocol-defined: a content block that
  references another resource by URI — the mechanism for "content lives elsewhere."
- **Everything else (chunking, summaries, ranges) is your design.**
- **`resources/read` must still work** for large URIs — never blow up; return the
  summary/default page.

## Example

Summary-first pattern:

```python
from fastmcp import FastMCP

mcp = FastMCP("data")

@mcp.resource("data://sales/report")
def report_index() -> str:
    """Sales report: summary + page URIs. Read pages for details."""
    summary = summarize_sales()
    pages = [f"data://sales/report/page/{i}" for i in range(page_count())]
    return {"summary": summary, "pages": pages, "page_size": 1000}

@mcp.resource("data://sales/report/page/{n}")
def report_page(n: int) -> str:
    """One page of the sales report (1000 rows)."""
    return fetch_page(n)
```

## Industry-standard pattern

Index + ranged access is universal: **database indexes + paging, object-store range
requests, zip central directories, Git's packfiles**. The rule: **never send the
whole thing when a pointer + slices will do**, and make the first read cheap.

## Common mistakes

- **Returning whole files** — the naive implementation that breaks at scale.
- **Building the full content in memory just to truncate it** — stream or slice at
  the source.
- **Chunk URIs that aren't discoverable** — the index must document them.
- **No size caps anywhere** — a "summary" that is itself 5 MB.

## Testing

- **First-read tests**: the canonical read returns something small and useful.
- **Slice tests**: page/range reads return correct, bounded slices
  ([15-testing/resource-testing.md](../15-testing/resource-testing.md)).
- **Memory tests**: reading a large resource doesn't balloon server memory
  (assert via instrumentation in CI).
- **Failure tests**: range requests past the end fail cleanly.

## Debugging

- High server memory during reads → the handler materializes full content; add
  slicing at the source.
- Client "context overflow" → the resource returned too much; check the summary
  strategy and sizes.

## Security considerations

- **Range/chunk parameters must be bounded** — unbounded `count` is a memory bomb.
- **Out-of-band fetches (object-store URLs) must be authorized** — don't hand out
  unsigned URLs to private data.

## Related concepts

- [pagination.md](pagination.md)
- [10-scaling-performance/large-resource-handling.md](../10-scaling-performance/large-resource-handling.md)
- [02-primitives/resources.md](../02-primitives/resources.md)