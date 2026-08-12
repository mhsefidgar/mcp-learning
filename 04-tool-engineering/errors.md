# Tool Errors

## What is it?

**Tool errors** are how a tool communicates failure to the client — and there are
*two distinct channels*, which is the core of this topic:

1. **JSON-RPC errors** — the request itself failed (unknown tool, invalid params,
   unauthorized, internal crash). Response carries `error` with a code.
2. **Semantic tool failures** — the tool *ran* but the operation failed ("file not
   found", "insufficient stock"). Response carries `result` with `isError: true` and
   a message.

Getting this distinction right is the single most important error-handling decision
in MCP server engineering.

## Why does MCP need it?

Because the two channels are read differently by clients:

- A **JSON-RPC error** means "something is wrong with the request/protocol" — the
  client may retry differently, but the model usually can't fix it.
- An **`isError` result** means "the tool understood you, but the operation failed"
  — the model *can* react: "file not found → let me list the directory".

If you raise exceptions for expected business failures, the model loses the ability
to recover. If you return `isError: false` for real failures, the model trusts bad
data. Error design *is* UX for models.

## How does it work?

| Situation | Channel | What you do |
|-----------|---------|-------------|
| Unknown tool name | JSON-RPC error | SDK raises/returns tool-not-found |
| Invalid arguments (schema) | JSON-RPC error `-32602` | SDK validates before your code |
| Unauthorized | JSON-RPC error | auth middleware ([03-routing-dispatch/08-authorization-routing.md](../03-routing-dispatch/08-authorization-routing.md)) |
| Expected business failure | `isError: true` result | raise `ToolError` / return `isError: true` |
| Unexpected exception | JSON-RPC error `-32603` | let it propagate, log it, don't leak details |
| Timeout / cancellation | JSON-RPC error | SDK handles ([timeouts.md](timeouts.md), [cancellation.md](cancellation.md)) |

## Mental model

Two doors: the **protocol door** (did the request make sense?) and the **business
door** (did the operation succeed?). A rejected protocol door → JSON-RPC error. A
rejected business door → `isError` result. The model stands in front of both doors;
each rejection must tell it what to do next.

## MCP-specific behavior

- **`isError` is an MCP protocol field** on tool results — a real, spec-defined
  mechanism, not a convention.
- **FastMCP**: raise `ToolError("message")` in a handler → the SDK converts it to an
  `isError: true` result. Server-side API calls re-raise; wire-level clients see the
  flag. The TS SDK: return `{content: [...], isError: true}` explicitly.
- **Never leak internals** in errors — log the detail, return a safe summary
  ([03-routing-dispatch/10-error-routing.md](../03-routing-dispatch/10-error-routing.md)).

## Example

FastMCP:

```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("orders")

@mcp.tool
def cancel_order(order_id: int) -> dict:
    """Cancel an order. Fails if already shipped."""
    order = db.get(order_id)
    if order is None:
        # Semantic failure -> isError: true result the model can react to.
        raise ToolError(f"Order {order_id} does not exist")
    if order.status == "shipped":
        raise ToolError(f"Order {order_id} already shipped; cannot cancel")
    db.cancel(order_id)
    return {"order_id": order_id, "status": "cancelled"}
```

TypeScript:

```typescript
server.registerTool("cancel_order", { description: "Cancel an order.", inputSchema: { order_id: z.number().int() } },
  async ({ order_id }) => {
    const order = await db.get(order_id);
    if (!order) return { content: [{ type: "text", text: `Order ${order_id} does not exist` }], isError: true };
    if (order.status === "shipped") return { content: [{ type: "text", text: "Already shipped" }], isError: true };
    await db.cancel(order_id);
    return { content: [{ type: "text", text: JSON.stringify({ order_id, status: "cancelled" }) }] };
  });
```

## Industry-standard pattern

Separating transport-level errors from application-level failures is universal:
**HTTP 4xx/5xx vs. 200-with-error-body**, **gRPC status vs. response envelope**,
**exceptions vs. result objects**. The MCP `isError` flag is its version of
"200 with an error payload" — and the model-friendly rule is: *if the caller can act
on the failure, make it a result, not an error.*

## Common mistakes

- **Raising for expected failures** (the #1 mistake) — the model can't distinguish
  "order not found" from a protocol bug.
- **Returning `isError: false` with an error string** — the model trusts it.
- **Ambiguous messages** — "operation failed" without *what* failed or *what to do*.
- **Leaking stack traces / SQL / internal paths** in errors.
- **Inconsistent shapes** — sometimes the error is in `text`, sometimes in `data`;
  pick one and document it.

## Testing

- **Channel tests**: expected business failures → `isError` result; protocol
  failures → JSON-RPC error ([15-testing/failure-testing.md](../15-testing/failure-testing.md)).
- **Message tests**: error text contains actionable info, never secrets/tracebacks.
- **Recovery tests**: after a semantic failure, subsequent calls work (errors don't
  poison the session).

## Debugging

- In Inspector, check *which channel* the failure used: red error response vs.
  `isError` result content. That alone tells you which layer to fix.
- Centralize error conversion in middleware so every path is visible
  ([03-routing-dispatch/11-middleware-routing.md](../03-routing-dispatch/11-middleware-routing.md)).

## Security considerations

- **Errors leak information**: unknown-tool errors disclose the catalog; validation
  errors disclose schema internals. Filter by principal
  ([03-routing-dispatch/08-authorization-routing.md](../03-routing-dispatch/08-authorization-routing.md)).
- **Never include secrets/PII** in error text or `data`.
- Log redacted full errors server-side for forensics
  ([14-security/auditability.md](../14-security/auditability.md)).

## Related concepts

- [validation.md](validation.md)
- [failure-handling.md](failure-handling.md)
- [03-routing-dispatch/10-error-routing.md](../03-routing-dispatch/10-error-routing.md)
- [15-testing/failure-testing.md](../15-testing/failure-testing.md)