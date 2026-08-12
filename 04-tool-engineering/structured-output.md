# Structured Output

## What is it?

**Structured output** is returning tool results in a shape the model can parse and
reuse — JSON with a documented schema — instead of free-form prose. MCP results are
`content` blocks; the structured-output pattern puts machine-readable data in the
text block (usually as JSON) so the model can extract it reliably and chain it into
the next call.

## Why does MCP need it?

Models are far more reliable at *parsing* structured data than at *parsing prose*.
Compare:

- Prose: `"Found 3 orders: order 123 from Acme for 42.50 USD on 2026-08-01, ..."`
- JSON: `[{"id": 123, "customer": "Acme", "amount": 42.5, "currency": "USD"}]`

The JSON version lets the model extract fields exactly, pass them to the next tool,
and present them to the user. Structured output is how tool results become *usable
data* instead of *walls of text*.

## How does it work?

1. **Design the output shape** — a JSON object with stable field names and types,
   matching what the caller needs downstream.
2. **Return it as JSON in a text content block** (SDKs: `json.dumps(...)` /
   `JSON.stringify(...)`).
3. **Document the shape** — in the tool description ("returns a JSON array of
   `{id, customer, amount, currency}`"), and in the newer spec, via `outputSchema`
   on the tool definition.
4. **Keep it flat and simple** — deeply nested or ambiguous shapes defeat the purpose.

## Mental model

Structured output is **returning an API response, not an essay**: field names,
types, and a documented shape. The model is the API consumer — give it the same
quality of contract you'd give a human developer (see [schemas.md](schemas.md) for
the input side).

## MCP-specific behavior

- **The result envelope is MCP's** (`content` blocks + `isError`); *what's inside* a
  text block is your choice. Structured output is a convention, not a protocol
  feature.
- **`outputSchema`** (2025-06-18+ spec): tools may declare a JSON Schema for their
  result — clients can validate and models can plan against it. (Not yet declared by
  every SDK in the same way; check yours.)
- **Non-text content**: images (`image` blocks) and resource references
  (`resource` blocks) are for binary/large data — structured JSON goes in text
  blocks.

## Example

FastMCP — return a list of dicts; FastMCP serializes to JSON in the text block:

```python
@mcp.tool
def get_order(order_id: int) -> dict:
    """Get an order as JSON: {id, customer, amount, currency, status}."""
    order = db.get(order_id)
    if order is None:
        raise ToolError(f"Order {order_id} does not exist")
    return {
        "id": order.id,
        "customer": order.customer,
        "amount": order.amount,
        "currency": order.currency,
        "status": order.status,
    }
```

TypeScript:

```typescript
server.registerTool("get_order", {
  description: "Get an order as JSON: {id, customer, amount, currency, status}.",
  inputSchema: { order_id: z.number().int() },
}, async ({ order_id }) => {
  const order = await db.get(order_id);
  if (!order) return { content: [{ type: "text", text: `Order ${order_id} not found` }], isError: true };
  return { content: [{ type: "text", text: JSON.stringify(order) }] };
});
```

## Industry-standard pattern

Machine-readable responses with documented schemas are the norm in APIs (JSON APIs,
protobufs). The MCP twist: the consumer is a model, so **stability of field names
matters more** — the model may have cached knowledge of your output shape. Change
shapes only with versioning ([09-version-aware-routing.md](../03-routing-dispatch/09-version-aware-routing.md)).

## Common mistakes

- **Prose-wrapped JSON** ("Here are the results: {…}") — the model has to unwrap it.
- **Unstable field names** (`customerName` sometimes, `name` other times).
- **Nested blob objects** — flatten what the caller needs.
- **Omitting units/currency/type info** — `amount: 42.5` without `currency: "USD"`
  invites unit errors.
- **Returning error details as successful structured data** — semantic failures
  should still set `isError` ([errors.md](errors.md)).

## Testing

- **Shape tests**: call the tool and validate the JSON against the documented shape
  (JSON Schema assertions, [15-testing/schema-testing.md](../15-testing/schema-testing.md)).
- **Parsability tests**: the text block always `json.loads`/`JSON.parse`s cleanly.
- **Field-stability tests**: golden snapshots of the output shape catch drift.

## Debugging

- In Inspector, call the tool and look at the raw text block — is it parseable JSON?
  Is the shape what you documented?
- If the model "misunderstands" a result, the shape is ambiguous or the description
  is missing — fix both.

## Security considerations

- **Structured output can carry injection content** (a database field with
  instructions). The model must treat tool output as untrusted data
  ([14-security/untrusted-output.md](../14-security/untrusted-output.md)).
- **Don't emit secrets** into results — check that returned records exclude
  sensitive fields.

## Related concepts

- [schemas.md](schemas.md)
- [errors.md](errors.md)
- [02-primitives/tools.md](../02-primitives/tools.md)
- [14-security/untrusted-output.md](../14-security/untrusted-output.md)