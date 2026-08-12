# 02 — Tool Routing

## What is it?

**Tool routing** is the mapping from a tool *name* (received in `tools/call`) to the
*implementation* that runs it, and from a registered implementation to the catalog
entry returned by `tools/list`. In a simple server this is a one-to-one map:
`"add" → add()`. In a real server it grows: namespaced tools, dynamic tool selection,
versioned tools, and tools supplied by multiple providers.

## Why does MCP need it?

The client only ever sends a string (`"name": "search_orders"`). The server must
resolve that string to *exactly one* handler, quickly and safely, and the resolution
rules must be discoverable — what the client sees in `tools/list` must be exactly what
`tools/call` can invoke. Routing is where naming decisions (prefixes, namespaces,
versions) live.

## How does it work?

1. **Registration**: each tool is registered with a name (explicit or derived) and a
   handler.
2. **Listing**: `tools/list` renders the registry into the catalog, applying any
   transforms (renames, namespacing, visibility filters) along the way
   ([07-transform-routing.md](07-transform-routing.md)).
3. **Lookup**: `tools/call` looks up the name in the registry (through the same
   transforms, reversed).
4. **Validation + execution**: the handler runs; a schema-mismatch or unknown-name
   failure maps to the error route ([10-error-routing.md](10-error-routing.md)).

### Advanced patterns

- **Dynamic tool selection** — a single handler dispatches to sub-operations based on
  arguments (e.g. one `database` tool with a `query` argument) to keep catalog size
  down. Trade-off: a smaller catalog means less model guidance.
- **Namespaces / grouping** — `git_status`, `git_commit`, `db_query` prefix names by
  domain. FastMCP's `Namespace` transform does this automatically when you mount
  servers ([07-transform-routing.md](07-transform-routing.md)).
- **Versioned tools** — `orders_search_v1` / `orders_search_v2` when behavior changes
  (see [09-version-aware-routing.md](09-version-aware-routing.md) and
  [13-versioning](../13-versioning/README.md)).

## Mental model

Tool routing is **function-pointer tables with a naming convention**: the client holds
a name, the server holds a table, and the name is the index. Everything else —
prefixes, versions, filters — is just how you organize the table so names stay unique
and meaningful.

## MCP-specific behavior

- **Names are the wire contract.** Once a client has seen `tools/list`, the names
  there must resolve in `tools/call`. Changing a name breaks running clients — that's
  why versioning and deprecation policies exist
  ([13-versioning/deprecation.md](../13-versioning/deprecation.md)).
- **`tools/list` and `tools/call` must agree.** SDKs guarantee this by deriving both
  from one registry — a strong reason not to hand-roll.
- **Duplicates are a bug**: two handlers with the same name is undefined behavior;
  SDKs either error at registration or resolve by provider precedence
  ([06-provider-routing.md](06-provider-routing.md)).
- **Pagination** of `tools/list` (`cursor`) doesn't change routing — names must still
  resolve identically across pages.

## Example

FastMCP namespacing via a transform on registration:

```python
from fastmcp import FastMCP
from fastmcp.server.transforms import Namespace

mcp = FastMCP("app", transforms=[Namespace("v1")])

@mcp.tool
def search(query: str) -> list[str]:
    """Search the catalog."""
    return ["a", "b"]
# Client sees: v1_search   (see 07-transform-routing.md)
```

Dynamic selection in one handler (educational simplification — prefer distinct tools
when the operations differ):

```python
@mcp.tool
def math(operation: str, a: float, b: float) -> float:
    """Perform a math operation: add, subtract, multiply, divide."""
    if operation == "add":      return a + b
    if operation == "subtract": return a - b
    if operation == "multiply": return a * b
    if operation == "divide":
        if b == 0:
            raise ValueError("division by zero")
        return a / b
    raise ValueError(f"unknown operation: {operation}")
```

TypeScript: names are explicit in `registerTool`; namespacing is manual:

```typescript
server.registerTool("git_status", { description: "Show working tree status" }, async () => ({ content: [] }));
server.registerTool("git_commit", { description: "Create a commit" }, async () => ({ content: [] }));
```

## Industry-standard pattern

Name → implementation routing with discoverability is the pattern behind **command
registries, plugin systems, and RPC method tables**. The engineering rules are the
same: names are stable identifiers, uniqueness is enforced, and the catalog is the
source of truth for clients.

## Common mistakes

- **Unstable names** (generated from object ids or timestamps) — every client cache
  breaks.
- **Case/style inconsistency** (`search_orders` vs `searchOrders`) across tools — the
  model will guess wrong names.
- **Relying on string prefix parsing** instead of the SDK's namespace transform.
- **Hiding routing complexity in the handler** (gigantic if/else on the tool name
  inside one "router" tool) — hard to test, weak schemas.

## Testing

- **Catalog ↔ invocation consistency**: every name in `tools/list` resolves in
  `tools/call`, and nothing else does ([15-testing/tool-testing.md](../15-testing/tool-testing.md)).
- **Collision tests**: registering duplicate names fails loudly or has defined
  precedence.
- **Namespace tests**: mounted/namespaced tools appear and resolve under their
  prefixed names.
- **Versioned-tool tests**: `v1_*` and `v2_*` both resolve to their own handlers.

## Debugging

- "Client says tool not found" → check the *exact* name the client saw in `tools/list`
  (Inspector shows both sides of the exchange).
- Check transforms: a `Namespace` transform changes names *after* registration — the
  name you registered may not be the name on the wire.

## Security considerations

- **Names are user input** — never build file paths, shell commands, or attribute
  lookups from them (path traversal / RCE).
- **Authorization is per-tool** — routing must check permissions *before* execution
  ([08-authorization-routing.md](08-authorization-routing.md),
  [14-security/tool-permissions.md](../14-security/tool-permissions.md)).

## Related concepts

- [01-request-dispatch.md](01-request-dispatch.md)
- [07-transform-routing.md](07-transform-routing.md)
- [09-version-aware-routing.md](09-version-aware-routing.md)
- [10-error-routing.md](10-error-routing.md)
- [04-tool-engineering/README.md](../04-tool-engineering/README.md)