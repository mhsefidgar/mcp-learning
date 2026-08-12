# Input Validation

## What is it?

**Input validation** is checking that the arguments a client sends in `tools/call`
are correct *before* the handler runs: types, required fields, ranges, formats,
business invariants. Two layers:

1. **Schema validation** — structural (types, required, constraints). Usually done by
   the SDK against the tool's `inputSchema`.
2. **Semantic validation** — business-level ("this order id exists", "this date is
   not in the past"). Done by your code.

## Why does MCP need it?

Every argument arrives from a network — and, worse, from a **model that may
hallucinate values**. A model might send `limit: -5`, `status: "pending-ish"`, or
`order_id: "ORD-123"` when ids look like `123`. Without validation, these flow into
your database, your shell, your API calls. Validation is the first line of defense and
the source of the *most useful errors* the model can recover from.

## How does it work?

1. **Schema validation** happens automatically at dispatch: the SDK checks `arguments`
   against `inputSchema`. Failure → `-32602 Invalid params` with details.
2. **Semantic validation** happens at the top of your handler: check business rules,
   raise a tool error with a precise message (see [errors.md](errors.md)).
3. **Fail fast**: the earlier a bad value is caught, the cheaper the failure — and the
   clearer the error the model can act on.

```
tools/call ──► schema validation (SDK) ──► handler: semantic validation ──► work
                    │ fails                       │ fails
                    ▼                             ▼
              -32602 Invalid params        isError result with message
```

## Mental model

Validation is a **bouncer with two checkpoints**: the first checks your ticket format
(schema), the second checks you're on the list (semantics). Each checkpoint turns
away bad entrants with a specific reason — and the *reason* is what lets the model
fix its behavior and try again.

## MCP-specific behavior

- **Schema validation on `tools/call` is protocol-driven** (the SDK validates against
  the published `inputSchema`) — but *how strict* is SDK-dependent: FastMCP validates
  with pydantic; the TS SDK validates with Zod; Java with Jackson + your schema.
- **Semantic validation is always yours** — the protocol has no notion of business
  rules.
- **Validation errors** should be structured: `-32602` with `data` naming the failing
  field (see [errors.md](errors.md)).

## Example

```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("orders")

@mcp.tool
def ship_order(order_id: int, tracking_note: str = "") -> dict:
    """Ship an order by numeric id, optionally adding a tracking note."""
    # Semantic validation: schema already guaranteed order_id is an int.
    order = db.get(order_id)
    if order is None:
        raise ToolError(f"Order {order_id} does not exist")
    if order.status != "paid":
        raise ToolError(f"Order {order_id} is {order.status}, not 'paid' — cannot ship")
    if len(tracking_note) > 200:
        raise ToolError("tracking_note must be at most 200 characters")
    db.ship(order_id, tracking_note)
    return {"order_id": order_id, "status": "shipped"}
```

TypeScript SDK — Zod validates at the boundary; business checks in the handler:

```typescript
server.registerTool("ship_order", {
  description: "Ship an order by numeric id.",
  inputSchema: { order_id: z.number().int(), tracking_note: z.string().max(200).optional() },
}, async ({ order_id, tracking_note }) => {
  const order = await db.get(order_id);
  if (!order) return { content: [{ type: "text", text: `Order ${order_id} does not exist` }], isError: true };
  if (order.status !== "paid") return { content: [{ type: "text", text: `Order is ${order.status}` }], isError: true };
  await db.ship(order_id, tracking_note);
  return { content: [{ type: "text", text: "shipped" }] };
});
```

## Industry-standard pattern

Validate at the boundary, fail fast, and return **actionable error messages** — the
same rules as web APIs (422 with field errors), form validation, and gRPC
`InvalidArgument`. For MCP the "actionable" part is amplified: the error text is read
by a model that will retry with corrected input.

## Common mistakes

- **Trusting the schema alone** — schemas can't express "order must be paid".
- **Silently coercing bad input** (`int("abc")` → 0) — hide bugs, surprise the model.
- **Vague validation errors** ("invalid input") — the model can't fix anything.
- **Validating only in the handler** — shared helpers called from multiple tools skip
  checks; validate centrally where possible.
- **Forgetting size limits** — unbounded strings/lists are memory bombs
  (see [08-reliability-resilience/backpressure.md](../08-reliability-resilience/backpressure.md)).

## Testing

- **Schema-level tests**: bad types/required-missing → `-32602`
  ([15-testing/tool-testing.md](../15-testing/tool-testing.md)).
- **Semantic tests**: business violations → `isError` with the right message.
- **Boundary tests**: min/max, empty strings, huge payloads, unicode.
- **Fuzz-ish tests**: random garbage arguments never crash the handler.

## Debugging

- A `-32602` with a precise `data` message pinpoints the failing field — read it
  before guessing.
- If validation errors are confusing, the schema is the problem: make it tighter
  ([schemas.md](schemas.md)).

## Security considerations

- **Validation is a security control**: size limits, type strictness, and
  allowlists reject injection payloads (SQL, shell, path traversal) early.
- **Never pass raw arguments into queries/shell** — validation reduces but doesn't
  eliminate injection risk; use parameterized queries ([14-security/README.md](../14-security/README.md)).
- **Be strict about types**: a `str` where an `int` belongs is a classic type-confusion
  bug vector.

## Related concepts

- [schemas.md](schemas.md)
- [errors.md](errors.md)
- [timeouts.md](timeouts.md)
- [15-testing/tool-testing.md](../15-testing/tool-testing.md)