# 10 — Error Routing

## What is it?

**Error routing** is the mapping from *failure conditions* to *responses*. Every
request can fail in a bounded set of ways, and each way must produce a defined,
predictable JSON-RPC response (or a defined notification/result for semantic
failures). A server without error routing produces arbitrary errors — and an LLM
client cannot recover from arbitrary errors.

## Why does MCP need it?

MCP clients are **LLM-driven**: the model reads error messages and decides what to do
next. A clear, structured error ("tool `fly` does not exist; available tools: add,
search") lets the model recover *autonomously*. An opaque one ("internal error 500")
dead-ends the conversation. Error routing is how you make failures *actionable*.

## How does it work?

The failure classes, their routes, and the responses:

| Failure | Route | Response |
|---------|-------|----------|
| Malformed JSON | parse stage | `-32700` Parse error |
| Not a valid request object | parse stage | `-32600` Invalid Request |
| Unknown method | dispatch | `-32601` Method not found |
| Invalid params (schema) | validation | `-32602` Invalid params (with `data` detail) |
| Unknown tool name | tool lookup | tool-not-found error (SDK-defined, `-32602`-family) |
| Unknown resource URI | resource lookup | resource-not-found error |
| Unknown prompt | prompt lookup | prompt-not-found error |
| Unauthorized operation | authz gate | authorization error |
| Unsupported capability | capability gate | method-not-found error |
| Handler raised (unexpected) | execution | `-32603` Internal error (don't leak details) |
| Tool ran but failed semantically | execution | `result` with `isError: true` + message content |

Two *very different* failure kinds to keep apart:

1. **JSON-RPC errors** — the request never produced a result (wrong method, bad
   params, unauthorized). Response has `error`.
2. **Semantic tool failures** — the tool *ran* but the operation failed ("file not
   found", "insufficient stock"). Response has `result` with `isError: true`. The
   model *sees* this message and can react.

## Mental model

Error routing is a **triage desk**: every incoming failure gets classified and routed
to the right response format, with the right level of detail. JSON-RPC errors are
"the phone call failed"; `isError` results are "the phone call succeeded, but the
answer is 'no'." Conflating them confuses clients.

## MCP-specific behavior

- **The SDKs define the standard error shapes**: FastMCP raises
  `ToolError`/`ResourceError`/`PromptError` (and friends) which become
  `isError: true` results; `mcp.types.ErrorData` for JSON-RPC errors. The TS SDK has
  `McpError` with `ErrorCode`. Use the SDK's error types — don't hand-roll.
- **`error.data` is the structured detail channel** — put machine-readable info there
  (which param failed, which tools exist).
- **Never leak internals**: handler tracebacks belong in server logs, not in the
  response (see security below).
- In the **2026-07-28 stateless spec**, errors additionally carry
  `Mcp-Method`/`Mcp-Name` routing context, but the JSON-RPC error structure is
  unchanged.

## Example

FastMCP — semantic failure as a result, not an exception:

```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("orders")

@mcp.tool
def cancel_order(order_id: str) -> dict:
    """Cancel an order by id."""
    order = db.get(order_id)
    if order is None:
        raise ToolError(f"Order {order_id} does not exist")   # → isError: true result
    if order.status == "shipped":
        raise ToolError(f"Order {order_id} is already shipped and cannot be cancelled")
    db.cancel(order_id)
    return {"order_id": order_id, "status": "cancelled"}
```

TypeScript SDK — same idea:

```typescript
import { McpError, ErrorCode } from "@modelcontextprotocol/sdk/types.js";

server.registerTool("cancel_order", { description: "Cancel an order by id" },
  async ({ order_id }: { order_id: string }) => {
    const order = await db.get(order_id);
    if (!order) {
      return { content: [{ type: "text", text: `Order ${order_id} does not exist` }], isError: true };
    }
    await db.cancel(order_id);
    return { content: [{ type: "text", text: "cancelled" }] };
  });
```

## Industry-standard pattern

Structured, classified errors are the norm in production APIs: **HTTP status codes +
problem+json**, **gRPC status codes**, **GraphQL error paths**, **structured error
envelopes** in every SDK. The MCP-specific lesson is *why* it matters: the error
consumer is a model, so error text should be written for a model that will try again
— include what went wrong and what the caller can do about it.

## Common mistakes

- **Raising for expected business failures** — "order not found" as an exception
  becomes a JSON-RPC error the model can't distinguish from a protocol bug. Use
  `isError: true`.
- **Leaking stack traces / SQL in errors** — a debugging gift to attackers.
- **Ambiguous "internal error" for everything** — the model has nothing to recover
  with. Log the detail, return a safe summary.
- **Inconsistent error shapes** — the client must parse one shape; add structure via
  `data`.
- **Erroring where a notification was expected** (or vice versa).

## Testing

- **Error matrix tests**: each failure class → the exact expected response
  ([15-testing/failure-testing.md](../15-testing/failure-testing.md)).
- **Semantic-failure tests**: `isError: true` results for expected business failures.
- **No-leak tests**: errors never contain tracebacks, secrets, or internal paths.
- **Recovery tests**: after an error, the connection still works (errors must not
  poison the session).

## Debugging

- In Inspector, capture the exact error object and check: code, message, `data`.
  The *code* tells you which routing stage failed.
- Semantic failures (`isError`) won't appear as protocol errors — look at the result
  content. Check both places when "it failed."
- Centralize error handling (middleware) so every error path is visible in one place
  ([11-middleware-routing.md](11-middleware-routing.md)).

## Security considerations

- **Errors leak information**: validation errors disclose schema internals; unknown-tool
  errors disclose the catalog. Decide what to expose *per principal*
  ([08-authorization-routing.md](08-authorization-routing.md)).
- **Never include secrets, tokens, or PII in error messages or `data`.**
- **Log the full error server-side** (redacted) for forensics
  ([14-security/auditability.md](../14-security/auditability.md)).

## Related concepts

- [01-request-dispatch.md](01-request-dispatch.md)
- [04-tool-engineering/errors.md](../04-tool-engineering/errors.md)
- [11-middleware-routing.md](11-middleware-routing.md)
- [15-testing/failure-testing.md](../15-testing/failure-testing.md)
- [01-fundamentals/03-json-rpc.md](../01-fundamentals/03-json-rpc.md)