# Sorting

## What is it?

**Sorting** is letting the caller order results server-side — by `created`, `amount`,
`name` — with a direction (`asc`/`desc`). Like filtering, it's a tool-design
concern: the server orders, the model receives a ready-to-use sequence.

## Why does MCP need it?

Models reason best over *ordered* data: "top 5 orders", "newest first", "most
expensive". If the server doesn't sort, the model either gets arbitrary order (and
"top 5" becomes a guess) or has to sort in its head over a huge list (unreliable).
Sorting also interacts with pagination: stable ordering is what makes pages
meaningful at all ([pagination.md](pagination.md)).

## How does it work?

1. **Design sort parameters**: `sort_by` (allowed field names) + `sort_dir`
   (`asc`/`desc`).
2. **Validate against an allowlist** of sortable fields — never accept arbitrary
   field names (they map to SQL ORDER BY, an injection surface).
3. **Push the sort into the data layer** (`ORDER BY created DESC, id DESC`).
4. **Use a stable tiebreaker** (`id`) so pagination doesn't shuffle rows between
   pages.

## Mental model

Sorting is **ORDER BY exposed as arguments**, with a bouncer: only fields on the
allowlist get in. The tiebreaker is the "ID column" that keeps pages stable — without
it, equal keys reorder between fetches.

## MCP-specific behavior

- **Nothing protocol-level** — sorting is your tool's design.
- Default sort should be **documented and stable** ("returns orders by created desc")
  — models rely on the default when they don't pass sort args.

## Example

```python
from typing import Literal

SORTABLE = {"created", "amount", "customer"}

@mcp.tool
def list_orders(
    sort_by: Literal["created", "amount", "customer"] = "created",
    sort_dir: Literal["asc", "desc"] = "desc",
    limit: int = 100,
) -> list[dict]:
    """List orders sorted by a field. Default: created desc. Tiebreak by id."""
    return db.query(order_by=sort_by, direction=sort_dir, limit=limit)
```

## Industry-standard pattern

Allowlisted sort fields with explicit direction and a stable tiebreaker is standard
API design (GitHub, Stripe, most query APIs). General rules: **allowlist fields,
validate direction, always add a unique tiebreaker, push sort to the DB.**

## Common mistakes

- **Accepting arbitrary `sort_by`** — SQL injection / expensive sorts on unindexed
  columns.
- **No tiebreaker** — equal keys shuffle between pages (duplicates/skips).
- **Sorting after pagination** — pages are ordered within, but the set is wrong.
- **Undocumented default order** — the model assumes one and gets another.

## Testing

- **Ordering tests**: each sortable field orders correctly in both directions.
- **Tiebreaker tests**: equal-key rows keep stable order across page fetches.
- **Validation tests**: unknown fields / bad direction → clean errors.
- **Default tests**: no sort args → documented default.

## Debugging

- Duplicates between pages with sorted results → missing tiebreaker.
- "Model always asks for the same sort" → make that the default and say so.

## Security considerations

- **Sort fields are query surface**: allowlist only; never echo arbitrary input into
  ORDER BY.
- Sorting on sensitive fields can leak ordering information — restrict per principal
  where it matters.

## Related concepts

- [filtering.md](filtering.md) · [pagination.md](pagination.md)
- [validation.md](validation.md)
- [10-scaling-performance/pagination-at-scale.md](../10-scaling-performance/pagination-at-scale.md)