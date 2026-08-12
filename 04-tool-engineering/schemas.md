# Tool Schemas

## What is it?

A tool's **schema** is the machine-readable contract for its arguments — a JSON
Schema (draft 2020-12 in current specs) attached to the tool's catalog entry. It says:
what arguments exist, their types, which are required, what constraints apply, and
what each argument means.

```json
{
  "type": "object",
  "properties": {
    "query": {"type": "string", "description": "Search term"},
    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10}
  },
  "required": ["query"]
}
```

## Why does MCP need it?

The schema is the **only thing the model knows about a tool's inputs**. It doesn't read
your code or your docs — it reads the schema and the description. A precise schema is
the difference between the model calling `search_orders(query="Acme")` correctly and
inventing arguments. The schema is also what the *client* uses to build forms, and
what the *server* uses to validate. One contract, three consumers.

## How does it work?

1. **Declaration**: you define the arguments (FastMCP: Python type hints + docstring;
   TS SDK: Zod schemas; Java: records/POJOs or hand-built JSON Schema).
2. **Generation**: the SDK converts your declaration into JSON Schema for the
   `tools/list` entry. **FastMCP generates this from your function signature and type
   hints.**
3. **Distribution**: the schema travels in `tools/list` (and can be re-fetched).
4. **Enforcement**: `tools/call` validates the incoming `arguments` against the schema
   before the handler runs.

## Mental model

The schema is a **form definition**: fields, types, required marks, constraints, help
text. The model is the form-filler. If the form says "city: string (required)",
the model fills a string. If the form is blank ("type: object", no properties), the
model guesses — and guesses wrong.

## MCP-specific behavior

- **The `inputSchema` is part of the protocol** (`Tool.inputSchema` in `tools/list`).
- **JSON Schema draft 2020-12** is the current reference version.
- **`title`, `description`, `annotations`, `outputSchema`** (newer spec additions)
  sit alongside `inputSchema` in the tool definition.
- **What the SDK generates is SDK-specific**: FastMCP derives from Python types
  (pydantic); the TS SDK derives from Zod; Java from annotations/records. The *output*
  is standard JSON Schema either way.

## Example

FastMCP — the schema comes from types + docstring:

```python
from typing import Literal
from pydantic import Field

@mcp.tool
def search_orders(
    query: str = Field(description="Customer name or order ID to search for"),
    status: Literal["open", "shipped", "cancelled"] | None = Field(
        default=None, description="Filter by order status"),
    limit: int = Field(default=10, ge=1, le=100, description="Max results"),
) -> list[dict]:
    """Search orders. Use when the user asks about their orders."""
    ...
```

The generated schema will include types, `required`, `minimum`/`maximum` (from `ge`/
`le`), and descriptions. **Inspect it** — `await mcp.list_tools()` and print
`tool.parameters`.

TypeScript SDK (Zod):

```typescript
import { z } from "zod";

server.registerTool(
  "search_orders",
  {
    description: "Search orders. Use when the user asks about their orders.",
    inputSchema: {
      query: z.string().describe("Customer name or order ID"),
      status: z.enum(["open", "shipped", "cancelled"]).optional(),
      limit: z.number().int().min(1).max(100).default(10),
    },
  },
  async (args) => ({ content: [{ type: "text", text: JSON.stringify(await search(args)) }] })
);
```

Java SDK:

```java
var schema = new ObjectMapper().createObjectNode()
    .put("type", "object")
    .set("properties", new ObjectMapper().createObjectNode()
        .put("query", "string")
        .set("limit", new ObjectMapper().createObjectNode()
            .put("type", "integer").put("minimum", 1).put("maximum", 100)));
var tool = new McpSchema.Tool("search_orders", "Search orders.", schema);
```

## Industry-standard pattern

Machine-readable contracts are standard: **OpenAPI**, **JSON Schema**, **gRPC proto**,
**GraphQL SDL**. The MCP-specific difference is the consumer is a *model*, so
**descriptions matter as much as types** — write "when to use" guidance, units,
ranges, and examples into the schema's descriptions.

## Common mistakes

- **Empty schemas** (`type: object` with no properties) — the model guesses.
- **Types without constraints** — `integer` without min/max lets absurd values through.
- **Missing descriptions** — the model doesn't know what `q` means.
- **Unions/anyOf overused** — models handle simple types far better.
- **Schema drift** — the schema you declared differs from what the handler actually
  accepts (test it, [15-testing/schema-testing.md](../15-testing/schema-testing.md)).
- **Vague tool-level descriptions** — the model can't tell *when* to use the tool.

## Testing

- **Schema tests**: assert generated `inputSchema` matches intent — types, required,
  constraints, descriptions ([15-testing/schema-testing.md](../15-testing/schema-testing.md)).
- **Round-trip tests**: schema validates all the examples you intend; rejects obvious
  garbage.
- **Golden schema snapshots** — catch accidental changes when you edit code.

## Debugging

- In Inspector, look at the tool's schema *as the model sees it* — not as you wrote
  it. SDK generation can surprise you (e.g. FastMCP turning `dict` into free-form
  object).
- If the model calls a tool with wrong arguments, the schema (or description) is
  almost always the culprit.

## Security considerations

- **Schemas are also input filters**: tight schemas reject malicious payloads early.
- **Never include secrets or internal paths in schema descriptions.**
- Be careful with `additionalProperties` — keep it false (or absent-and-ignored) to
  prevent argument smuggling.

## Related concepts

- [validation.md](validation.md)
- [structured-output.md](structured-output.md)
- [annotations.md](annotations.md)
- [02-primitives/tools.md](../02-primitives/tools.md)
- [15-testing/schema-testing.md](../15-testing/schema-testing.md)