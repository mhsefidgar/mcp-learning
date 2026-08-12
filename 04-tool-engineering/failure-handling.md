# Failure Handling

## What is it?

**Failure handling** is the *systematic* answer to "what happens when this tool
call goes wrong?" — every failure mode identified, classified, and given a defined
behavior. It's the umbrella over the previous topics: validation errors, semantic
failures, timeouts, cancellations, retries, and unexpected exceptions, all handled
consistently.

## Why does MCP need it?

Because MCP failures are read by **models that will try again**, inconsistent
failure handling trains models badly:

- Sometimes an error is raised, sometimes returned, sometimes swallowed → the model
  can't learn a recovery strategy.
- "Internal error" for everything → the model has nothing to act on.
- A swallowed failure returns wrong-looking success data → the model *trusts it* and
  makes decisions on garbage.

Consistent failure handling is a **reliability contract**: every call either
succeeds, fails *loudly and usefully*, or is bounded (timeout/cancel).

## How does it work?

1. **Enumerate the failure modes** for each tool:
   - input problems (validation) — [validation.md](validation.md)
   - expected business failures (not found, conflict) — [errors.md](errors.md)
   - downstream failures (DB/API down) — [retries.md](retries.md),
     [08-reliability-resilience/README.md](../08-reliability-resilience/README.md)
   - duration problems (timeout) — [timeouts.md](timeouts.md)
   - abandonment (cancellation) — [cancellation.md](cancellation.md)
   - unexpected exceptions (bugs)
2. **Classify each into the right channel**: JSON-RPC error vs. `isError` result
   ([errors.md](errors.md)).
3. **Define the response for each**: message text, `data` structure, and whether the
   model can retry/repair.
4. **Make it consistent**: centralize conversion (middleware), so every handler gets
   the same treatment ([03-routing-dispatch/11-middleware-routing.md](../03-routing-dispatch/11-middleware-routing.md)).
5. **Validate the result too**: even "success" output should be shape-checked before
   it reaches the client (tool result validation — see below).

### Tool result validation

Before returning, check the result against its documented shape
([structured-output.md](structured-output.md)): correct type, no secrets, sane
sizes. A tool that returns `None` when it promised a dict is itself a failure.

## Mental model

Failure handling is **writing the emergency procedures before the emergency**: a
checklist for every bad thing that can happen, each with a scripted response. The
model is the emergency responder reading the checklist — it can only act if the
script tells it what happened and what to do.

## MCP-specific behavior

- **The protocol defines the channels** (JSON-RPC error vs. `isError` result) —
  classification is your job.
- **SDK error types** (`ToolError` in FastMCP, `McpError` in TS) map to the right
  channels — use them.
- **Consistency across tools matters more than cleverness in one**: a
  `raise ToolError(...)` convention everywhere beats one beautifully handled tool.

## Example

A failure-handling checklist for `ship_order`:

| Failure | Channel | Response |
|---------|---------|----------|
| `order_id` not an int | JSON-RPC `-32602` | SDK validation |
| order not found | `isError` result | "Order 123 does not exist" |
| order not paid | `isError` result | "Order 123 is 'open'; pay it first" |
| DB down | JSON-RPC `-32603` (after retries) | "shipping service unavailable; try later" |
| takes > 30s | JSON-RPC timeout error | "shipping timed out; check get_job" |
| cancelled | JSON-RPC cancelled error | client-initiated |
| unexpected bug | JSON-RPC `-32603` (logged, redacted) | "internal error" |

```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("orders")

@mcp.tool
def ship_order(order_id: int) -> dict:
    """Ship an order by id. Returns {order_id, status, tracking}."""
    order = db.get(order_id)
    if order is None:
        raise ToolError(f"Order {order_id} does not exist")          # expected → isError
    if order.status != "paid":
        raise ToolError(f"Order {order_id} is '{order.status}', not 'paid'")
    try:
        tracking = shipping_api.ship(order)                          # downstream
    except shipping_api.Unavailable as exc:
        # retries happened inside shipping_api; give up cleanly
        raise ToolError("Shipping service is unavailable right now; try again shortly")
    result = {"order_id": order_id, "status": "shipped", "tracking": tracking}
    _validate_result(result)                                          # result validation
    return result
```

## Industry-standard pattern

Failure-mode enumeration + classification + defined responses is standard reliability
engineering: **failure-mode analysis (FMEA), structured error envelopes, and error
budgets** all start from "list every way this can fail." The MCP-specific habit worth
adopting: write the failure table *first*, then implement against it.

## Common mistakes

- **Ad-hoc handling per tool** — some raise, some return, some swallow.
- **Swallowing failures** (`except: pass`) — the model gets success-shaped garbage.
- **No result validation** — garbage-in, garbage-out past the server boundary.
- **Treating downstream failures as semantic failures** — "DB down" as `isError:
  true` looks retryable to the model when it isn't.
- **No testing of the failure table** — the paths you never test are the ones that
  fire in production.

## Testing

- **Failure-table tests**: one test per row of your failure table, asserting the
  exact response ([15-testing/failure-testing.md](../15-testing/failure-testing.md)).
- **Chaos/failure-injection tests**: randomly failing downstreams to verify retry
  and error behavior ([08-reliability-resilience/failure-injection.md](../08-reliability-resilience/failure-injection.md)).
- **Result-validation tests**: shape-checked results reject bad output.

## Debugging

- Log every failure with its classification — the log is your failure table in
  action; mismatches between log and table reveal unclassified failures.
- "Worked in demo, failed in prod" → usually an unenumerated failure mode (auth,
  quota, network); add it to the table.

## Security considerations

- **Failures leak information** — never expose stack traces, SQL, or internals in
  client-facing errors ([errors.md](errors.md)).
- **Failure responses are attack surface** — keep them consistent so probing
  responses don't reveal system internals.
- **Log redacted failures** for forensics
  ([09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md),
  [14-security/auditability.md](../14-security/auditability.md)).

## Related concepts

- [errors.md](errors.md) · [validation.md](validation.md)
- [timeouts.md](timeouts.md) · [retries.md](retries.md)
- [08-reliability-resilience/failure-injection.md](../08-reliability-resilience/failure-injection.md)
- [15-testing/failure-testing.md](../15-testing/failure-testing.md)