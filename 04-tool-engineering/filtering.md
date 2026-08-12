# Filtering

## What is it?

**Filtering** is letting the caller narrow results **server-side** — "orders for
customer Acme", "files modified today" — instead of returning everything and making
the model/client filter locally. Filtering happens through tool arguments
(`customer`, `status`, `since`), and its quality determines whether a model gets a
precise answer or a wall of data it has to reason over.

## Why does MCP need it?

Models have small working contexts. A tool that returns 10,000 orders because it
can't filter is a tool that forces the model to (a) ignore most of the data, (b)
hallucinate summaries, or (c) burn context. Filtering is how the *server* does the
work the model can't afford. It's also a **data-minimization** control: the model
only sees what it asked for.

## How does it work?

1. **Design filter parameters**: fields the caller can narrow by (`customer`,
   `status`, `date_from`, `tags`).
2. **Validate them** (types, ranges, allowed values — [validation.md](validation.md)).
3. **Push the filter into the data layer**: `WHERE customer = ? AND status = ?` —
   never filter in application memory after loading everything (that's a
   scalability bug).
4. **Document the filter fields** in the schema so the model knows what's available.

## Mental model

Filtering is **SQL WHERE clauses exposed as arguments**: the tool is a query
builder, and the model writes the query by filling arguments. Good filter design =
good query design: indexed fields, exact names, documented values.

## MCP-specific behavior

- **Nothing protocol-level**: filtering is a tool-design concern. MCP defines no
  filter grammar; you design the arguments.
- **Consistency with pagination/sorting matters**: filters apply *before*
  pagination, so page sizes stay meaningful.
- **Filterable fields should be discoverable**: the schema's descriptions should say
  "filter by customer (exact name)".

## Example

```python
from typing import Literal
from datetime import date

@mcp.tool
def list_orders(
    customer: str | None = None,
    status: Literal["open", "paid", "shipped", "cancelled"] | None = None,
    created_after: date | None = None,
    limit: int = 100,
) -> list[dict]:
    """List orders. Filter by customer name (exact), status, or created date.

    Returns {id, customer, amount, currency, status, created} ordered by created desc.
    """
    return db.query(
        customer=customer, status=status, created_after=created_after, limit=limit,
    )
```

## Industry-standard pattern

Server-side filtering with typed, documented parameters is standard API design
(REST query params, GraphQL arguments, gRPC filter messages). The rules that matter:
**filter in the database, validate strictly, use indexes, and expose only fields the
caller may filter on.**

## Common mistakes

- **Filtering in application memory** after loading everything — O(n) waste that
  becomes a latency/DB problem ([10-scaling-performance/README.md](../10-scaling-performance/README.md)).
- **Free-text filter fields** with no validation — SQL injection surface
  ([14-security/README.md](../14-security/README.md)).
- **Filter fields that don't match the result fields** — the model filters by
  `customerName`, but the argument is `customer`.
- **Too many filter options** — a dozen rarely-used filters clutter the schema.
- **Filters that ignore pagination** — filtering after paging gives wrong totals.

## Testing

- **Filter correctness tests**: each filter narrows results as documented; combined
  filters behave like AND.
- **Filter validation tests**: invalid values → clean errors.
- **Filter + pagination tests**: filtered page walks stay consistent.
- **Index/performance tests**: filtered queries stay fast at data scale.

## Debugging

- A model "ignoring" your filters usually means the schema didn't document them or
  the field names are unintuitive.
- Wrong filtered results → test the query directly (the tool is a thin wrapper).

## Security considerations

- **Filters are exfiltration surface**: a filter like `customer` lets the caller
  probe the dataset. Authorize *which fields and values* a principal may filter on
  ([14-security/authorization.md](../14-security/authorization.md)).
- **Parameterize everything** — never interpolate filter values into SQL/shell.

## Related concepts

- [pagination.md](pagination.md) · [sorting.md](sorting.md)
- [validation.md](validation.md)
- [structured-output.md](structured-output.md)