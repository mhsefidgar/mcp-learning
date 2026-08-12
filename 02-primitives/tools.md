# Tools

## What is it?

A **tool** is an executable operation the model can invoke with structured arguments.
Examples: `search_orders(query, limit)`, `send_email(to, subject, body)`,
`calculate_shipping(items, country)`. A tool is defined by:

- **name** — a unique identifier (snake_case / camelCase, no spaces)
- **description** — what it does, *and when to use it* (the model reads this)
- **inputSchema** — a JSON Schema describing the arguments
- **implementation** — the code that runs when called

## Why does MCP need it?

Tools are the **action** primitive: they are how an LLM stops *talking* and starts
*doing*. Without a standard tool interface, every client would need a bespoke adapter
for every capability. With it, one `tools/call` works for "search the web" and "deploy
the service" alike — the model discovers the contract at runtime via `tools/list`.

## How does it work?

1. **Discovery**: the client calls `tools/list`; the server returns the catalog
   (name, description, inputSchema).
2. **Selection**: the model (or the client) picks a tool and builds arguments from the
   schema.
3. **Invocation**: the client sends `tools/call` with `{name, arguments}`.
4. **Execution**: the server validates the arguments (against the schema), runs the
   implementation, and returns a result.
5. **Result**: the server returns `content` blocks (`text`, `image`, `resource`) and an
   `isError` flag. `isError: true` means the tool *ran* but failed semantically (e.g.
   "file not found") — that is not a JSON-RPC error, and the client should show the
   message to the model.

```
Client                        Server
  │ tools/list                  │
  ├────────────────────────────►│  return catalog (name, desc, schema)
  │ ◄───────────────────────────┤
  │ tools/call {name, arguments}│
  ├────────────────────────────►│  validate → execute handler
  │ ◄───────────────────────────┤  result {content, isError}
```

## Mental model

A tool is a **function with a published contract and a docstring the model can read**.
The schema is the function signature; the description is the docstring; the call is
the invocation. The model is a programmer who reads the docs at runtime and calls the
function — so the *quality of the description and schema* directly determines how well
the model uses the tool.

## MCP-specific behavior

- **Tools are server-side and stateless by default.** The server owns execution; the
  client is just a messenger. State must be threaded explicitly (arguments, resources).
- **The schema is JSON Schema** (draft 2020-12 in current specs). FastMCP generates it
  from Python type hints; the TS SDK from Zod schemas; the Java SDK from records/POJOs.
- **`tools/list` may be paginated** with `cursor` (see
  [04-tool-engineering/pagination.md](../04-tool-engineering/pagination.md)).
- **`listChanged`** capability: if declared, the server sends
  `notifications/tools/list_changed` when the catalog changes, so clients can
  re-fetch.
- **Annotations** (`title`, `readOnlyHint`, `destructiveHint`, `idempotentHint`,
  `openWorldHint`) are *hints* for the client/model — not enforcement
  ([04-tool-engineering/annotations.md](../04-tool-engineering/annotations.md)).
- **Tool results can be huge** — pagination, truncation, and structured output are
  engineering concerns covered in [04-tool-engineering](../04-tool-engineering/README.md).
- **Progress and cancellation** are supported via `_meta.progressToken` and
  `notifications/cancelled` ([04-tool-engineering/progress.md](../04-tool-engineering/progress.md),
  [04-tool-engineering/cancellation.md](../04-tool-engineering/cancellation.md)).

## Example

FastMCP derives the schema from type hints and docstring:

```python
from fastmcp import FastMCP

mcp = FastMCP("orders")

@mcp.tool
def search_orders(query: str, limit: int = 10) -> list[dict]:
    """Search orders by customer name or order ID.

    Use when the user asks about specific orders or order history.
    """
    return db.search_orders(query, limit=limit)  # list[dict] of order rows
```

TypeScript SDK with Zod:

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";

const server = new McpServer({ name: "orders", version: "1.0.0" });

server.registerTool(
  "search_orders",
  {
    description: "Search orders by customer name or order ID.",
    inputSchema: { query: z.string(), limit: z.number().int().default(10) },
  },
  async ({ query, limit }) => ({
    content: [{ type: "text", text: JSON.stringify(await db.search(query, limit)) }],
  })
);
```

Java SDK:

```java
var server = McpServer.sync(serverInfo)
    .registerTool(
        new McpSchema.Tool("search_orders", "Search orders by customer name or order ID.",
            new ObjectMapper().createObjectNode()
                .put("type", "object")
                .set("properties", new ObjectMapper().createObjectNode()
                    .put("query", "string"))),
        (request) -> new McpSchema.CallToolResult(
            List.of(new McpSchema.TextContent("orders...")), false))
    .build();
```

## Industry-standard pattern

Tools are **RPC endpoints with machine-readable contracts**: like OpenAPI operations,
gRPC methods, or GraphQL fields. The difference is the *consumer*: a model that reads
the contract and decides at runtime. That makes **description quality** and **schema
precision** first-class engineering concerns, not documentation afterthoughts (see
[04-tool-engineering/schemas.md](../04-tool-engineering/schemas.md)).

## Common mistakes

- **Vague descriptions** ("do stuff with orders") — the model can't decide when to
  call the tool. Write *when to use it* + *what it returns*.
- **Weak schemas** (`type: object` with no properties) — the model will guess
  arguments and fail. See [04-tool-engineering/schemas.md](../04-tool-engineering/schemas.md).
- **Side effects in a "read" tool** — surprising behavior models can't reason about.
- **Returning unstructured strings** instead of structured content — the model has to
  parse your prose. Prefer JSON-shaped text blocks with a clear shape
  ([04-tool-engineering/structured-output.md](../04-tool-engineering/structured-output.md)).
- **No error handling** — a raised exception becomes a confusing JSON-RPC error.
  Return `isError: true` with a helpful message for expected failures
  ([04-tool-engineering/errors.md](../04-tool-engineering/errors.md)).

## Testing

- **Schema tests**: the generated `inputSchema` matches your intent (types, required,
  defaults) — [15-testing/schema-testing.md](../15-testing/schema-testing.md).
- **Invocation tests**: call the tool with valid and invalid arguments; assert result
  shape and `isError` behavior — [15-testing/tool-testing.md](../15-testing/tool-testing.md).
- **Discovery tests**: `tools/list` returns the expected catalog — [15-testing/capability-testing.md](../15-testing/capability-testing.md).
- **Failure tests**: what happens on timeout, cancellation, and internal exceptions —
  [15-testing/failure-testing.md](../15-testing/failure-testing.md).

## Debugging

- Use MCP Inspector to call the tool manually with arbitrary JSON arguments — the
  fastest way to see whether a bug is in the schema, the validation, or the handler
  ([07-inspector-debugging/tools.md](../07-inspector-debugging/tools.md)).
- Check whether the failure is **validation** (before the handler — schema bug) or
  **execution** (inside the handler — logic bug). The error `data` usually tells you.

## Security considerations

- **Tools are the attack surface.** Every tool is code the client can trigger. Apply
  least privilege, validate inputs, and authorize per-tool
  ([14-security/tool-permissions.md](../14-security/tool-permissions.md)).
- **Destructive tools** (delete, send, deploy) should be marked with
  `destructiveHint`, require confirmation, and be audited
  ([14-security/destructive-operations.md](../14-security/destructive-operations.md)).
- **Untrusted output**: tool results may contain prompt-injection content — the client
  must treat them as untrusted data ([14-security/untrusted-output.md](../14-security/untrusted-output.md)).

## Related concepts

- [04-tool-engineering/README.md](../04-tool-engineering/README.md) — everything about
  engineering tools well
- [resources.md](resources.md) — data vs. actions
- [03-routing-dispatch/02-tool-routing.md](../03-routing-dispatch/02-tool-routing.md)
- [15-testing/tool-testing.md](../15-testing/tool-testing.md)