# Partial Failures in Composed MCP Systems

## What is it?

**Partial failure** is when *some* parts of a composed operation fail while others
succeed. In MCP this shows up everywhere:

- a **batched tool** where 3 of 20 items fail
  ([04-tool-engineering/batching.md](../04-tool-engineering/batching.md))
- a **multi-server agent** where one of three MCP servers is down
  ([10-scaling-performance/multi-server-architectures.md](../10-scaling-performance/multi-server-architectures.md))
- a **proxy/gateway** where one of several backends fails
  ([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md))
- a **workflow** where tool A succeeded and tool B failed
  ([16-end-to-end/architecture.md](../16-end-to-end/architecture.md))

## Why does MCP need it?

Composed systems make partial failure the *normal* case, not the exception. If the
design assumes all-or-nothing, one failing backend takes down the whole workflow —
and the model gets an opaque failure instead of "these three worked, these two
didn't." Handling partial failures explicitly is what makes multi-server agents
usable at all.

## How does it work?

1. **Design for partial results from the start**: batches return per-item status
   (not a single error); multi-server fan-out returns per-server results.
2. **Decide the policy per use case**:
   - **Fail-fast**: if any part fails, fail everything (transactional workflows).
   - **Continue-on-partial**: return the successes plus the failures (searching
     multiple backends).
   - **Degrade**: drop failed parts, mark the result degraded
     ([fallback.md](fallback.md)).
3. **Report precisely**: the result must say *which* parts succeeded/failed and why,
   so the model can decide next steps.
4. **Isolate the damage**: a failing backend must not hang or exhaust the others
   ([bulkheads.md](bulkheads.md), timeouts).

## Mental model

Partial failure handling is **the report card**: each subject (backend, batch item)
gets its own grade, and the summary says "math: A, history: F". The model (the
parent) reads the card and decides — retake history, or accept the overall result.
Never hand back a single "failed" with no per-item detail.

## MCP-specific behavior

- **Nothing protocol-level** — per-item/per-server results are your result-shape
  design ([04-tool-engineering/structured-output.md](../04-tool-engineering/structured-output.md)).
- **The `isError` flag is per-result, not per-batch**: a batch tool returns one
  result whose *content* encodes per-item status.
- **In a proxy**, per-backend failure must surface as per-component errors, not a
  proxy-wide failure ([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)).

## Example

Per-item status in a batch (see [04-tool-engineering/batching.md](../04-tool-engineering/batching.md)):

```python
@mcp.tool
def get_orders(ids: list[int]) -> dict:
    """Fetch orders. Returns {results: {id: order}, errors: {id: reason}}."""
    results, errors = {}, {}
    for oid in ids:
        order = db.get(oid)
        if order is None:
            errors[oid] = "not found"
        else:
            results[oid] = order
    return {"results": results, "errors": errors}
```

Multi-server fan-out (client side, conceptual):

```python
async def query_all(servers, question):
    outcomes = {}
    for name, client in servers.items():
        try:
            outcomes[name] = {"status": "ok", "data": await client.call_tool("search", {"q": question})}
        except Exception as exc:
            outcomes[name] = {"status": "error", "reason": str(exc)}
    return outcomes  # the model sees exactly which servers answered
```

## Industry-standard pattern

Per-component status is standard in distributed systems: **map-reduce partial
results, multi-region failover reports, Stripe's per-charge errors, HTTP 207
Multi-Status**. The rules: results are per-item, errors carry reasons, and the
aggregation policy (fail-fast vs. continue) is explicit and documented.

## Common mistakes

- **All-or-nothing assumptions** — one backend failure kills the whole workflow.
- **Losing per-item detail** — "batch failed" with no indication of which items.
- **Unbounded fan-out** — waiting forever on a hung backend (timeouts per part).
- **The model can't tell what's fresh** — mark which parts are degraded/stale.

## Testing

- **Partial-success tests**: mixed success/failure inputs produce the expected
  per-item report ([15-testing/failure-testing.md](../15-testing/failure-testing.md)).
- **Policy tests**: fail-fast vs. continue-on-partial behave as configured.
- **Isolation tests**: a failing part doesn't hang the rest (timeouts).
- **E2E multi-server tests**: one server down, others still answer
  ([capstone](../capstone/README.md)).

## Security considerations

- **Partial results leak what each backend knows** — a model that can see "backend
  X failed" learns about your topology; consider what per-server detail to expose.
- **Error reasons can leak internals** — redact before returning.

## Related

- [04-tool-engineering/batching.md](../04-tool-engineering/batching.md)
- [bulkheads.md](bulkheads.md)
- [fallback.md](fallback.md)
- [10-scaling-performance/multi-server-architectures.md](../10-scaling-performance/multi-server-architectures.md)