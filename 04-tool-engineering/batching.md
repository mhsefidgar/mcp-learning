# Batching

## What is it?

**Batching** is processing multiple operations in **one** tool call instead of many.
A `get_order(id)` tool becomes `get_orders(ids=[...])`; a `send_email(to, ...)` tool
becomes `send_emails(items=[...])`. The model sends one request, the server does N
units of work, and returns one structured result.

## Why does MCP need it?

Three wins:

1. **Fewer round trips** — models calling 20 tools sequentially is slow and token
   heavy; one batched call replaces 20.
2. **Atomicity / consistency** — batch operations can be transactional ("update all
   of these or none").
3. **Efficiency** — one DB round trip with `WHERE id IN (...)` beats 20 single
   lookups ([10-scaling-performance/tool-fan-out.md](../10-scaling-performance/tool-fan-out.md)).

## How does it work?

1. Design the batch tool: a list argument (`ids: [1,2,3]`), and a **result shape that
   maps back to inputs** — one result per input, keyed by input id.
2. Validate the batch (size caps — a batch of 10,000 is a memory bomb).
3. Process, collecting **per-item results and per-item errors**.
4. Return a structured envelope: successes + failures *for the same call*.

Partial failures are the key design decision: a batch that fails entirely on one bad
item is usually wrong — return per-item status instead
([08-reliability-resilience/partial-failures.md](../08-reliability-resilience/partial-failures.md)).

## Mental model

Batching is **array-based APIs**: instead of a scalar function, an array function.
Like `map()` vs. a for-loop over network calls. The contract must say how outputs
correspond to inputs — hence keyed results.

## MCP-specific behavior

- **MCP has no batch protocol method** — no `tools/batch`. Batching is a *tool
  design pattern*: you design a tool whose arguments are lists.
- **The protocol does support concurrency**: many `tools/call` requests can be
  in-flight simultaneously on one connection — a client can parallelize instead of
  batching ([10-scaling-performance/concurrent-tool-calls.md](../10-scaling-performance/concurrent-tool-calls.md)).
- **Progress reporting** works per batch (`ctx.report_progress(i, n)`) so long batches
  stay observable.

## Example

```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("orders")

@mcp.tool
def get_orders(ids: list[int]) -> dict:
    """Fetch several orders at once. Returns {results: {id: order}, errors: {id: reason}}.

    Use instead of get_order when you need multiple orders.
    """
    if len(ids) > 100:
        raise ToolError("ids: at most 100 per call")
    results, errors = {}, {}
    for oid in dict.fromkeys(ids):  # dedupe; keep first-seen order
        order = db.get(oid)
        if order is None:
            errors[oid] = "not found"
        else:
            results[oid] = {"id": oid, "amount": order.amount, "currency": order.currency}
    return {"results": results, "errors": errors}
```

## Industry-standard pattern

Batch endpoints are standard in APIs (Stripe `bulk`, AWS batch ops, GraphQL
`aliases`). The design rules: **cap batch size, key results by input, report
per-item errors, make batches idempotent** ([idempotency.md](idempotency.md)), and
size limits that protect the server.

## Common mistakes

- **Unbounded batch sizes** — memory/CPU bombs; cap them.
- **All-or-nothing semantics without saying so** — surprising failures.
- **Unkeyed results** — the model can't tell which result belongs to which input.
- **Batching operations that shouldn't be batched** — e.g. destructive ops in one
  call remove the per-item confirmation UI.

## Testing

- **Mapping tests**: every input id appears in results or errors exactly once.
- **Partial-failure tests**: mixed valid/invalid ids → per-item status.
- **Size-cap tests**: oversized batches rejected.
- **Idempotency tests**: repeat the batch → same outcome, no duplicate effects.

## Debugging

- Mismatched results ↔ inputs → the keying contract is broken; make results keyed by
  the exact input id.
- A slow batch → check per-item work (are you doing N sequential network calls
  server-side? parallelize with bounded concurrency).

## Security considerations

- **Batches amplify attacks**: one call = N operations. Cap sizes, rate-limit
  batches, and authorize per *item* where items differ in sensitivity.
- **Per-item errors can leak existence** ("id 5 not found") — acceptable usually,
  but consider for sensitive datasets.

## Related concepts

- [idempotency.md](idempotency.md)
- [08-reliability-resilience/partial-failures.md](../08-reliability-resilience/partial-failures.md)
- [10-scaling-performance/tool-fan-out.md](../10-scaling-performance/tool-fan-out.md)
- [progress.md](progress.md)