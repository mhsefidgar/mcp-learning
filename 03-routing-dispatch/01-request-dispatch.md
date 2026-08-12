# 01 — Request Dispatch

## What is it?

**Request dispatch** is the mapping from an incoming JSON-RPC `method` string to the
operation that handles it. It's the protocol layer's switchboard:

```
tools/list        → list tool catalog
tools/call        → validate + run a tool
resources/list    → list resources
resources/read    → resolve a URI and return content
resources/templates/list → list URI templates
prompts/list      → list prompt catalog
prompts/get       → render a prompt
initialize        → handshake
notifications/*   → no response, just side effects
```

## Why does MCP need it?

Every request arrives as a string (`"tools/call"`), and strings are dangerous: a
server that blindly evaluates them would let a client reach arbitrary code. Dispatch is
the **bounded mapping** that turns a network-controlled string into a *fixed set* of
operations. It is also the natural place to hang cross-cutting concerns — capability
gates, auth, metrics — because *every* request passes through it.

## How does it work?

1. The transport delivers a JSON-RPC message.
2. The protocol layer classifies it: request (has `id`) vs. notification (no `id`).
3. The `method` string is looked up in the **dispatch table** (a static map from
   method name → handler). No dynamic evaluation, no reflection on the method string.
4. The handler validates `params` (schema check), runs the application logic, and
   returns a result.
5. The result is wrapped in a JSON-RPC response with the request's `id`; any error is
   wrapped per [10-error-routing.md](10-error-routing.md).
6. Unknown methods fall through to the **default handler** → `-32601 Method not found`.

You saw a hand-rolled dispatch table in
[01-fundamentals/examples/raw_handshake.py](../01-fundamentals/examples/raw_handshake.py)
— that `dispatch()` function *is* request dispatch.

## Mental model

Dispatch is the **router in a web framework**: URL pattern → controller. Here the
"URL" is the `method` field and the "controller" is your tool/resource/prompt handler.
Everything you already know about routing security (no eval, fixed routes, 404 for
unknown paths) applies verbatim.

## MCP-specific behavior

- **Method namespaces are fixed by the spec**: `tools/*`, `resources/*`, `prompts/*`,
  `completions/*`, `logging/*`, `initialize`, `notifications/*`, plus server→client
  namespaces (`sampling/*`, `roots/*`, `elicitation/*`).
- **The dispatch table is per-side**: servers dispatch client→server methods; clients
  dispatch server→client methods. A client receiving `tools/call` has no handler and
  must answer with `-32601`.
- **Notifications are dispatched too, but produce no response.**
- SDKs (FastMCP, TS SDK, Java SDK) build the table for you from your registered
  components. You write the *application* routing (which tool → which function) via
  registration; the *protocol* routing (method → registry lookup) is the SDK's job.
- The **2026-07-28 stateless spec** adds header-based routing: `Mcp-Method` and
  `Mcp-Name` HTTP headers let gateways route *before* parsing the body
  ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).

## Example

The table in the hand-rolled server ([01-fundamentals/examples/raw_handshake.py](../01-fundamentals/examples/raw_handshake.py)):

```python
def dispatch(method: str, params: dict, request_id) -> dict:
    if method == "initialize":       return handle_initialize(params, request_id)
    if method == "tools/list":       return handle_tools_list(request_id)
    if method == "tools/call":       return handle_tools_call(params, request_id)
    # unknown method -> -32601
    return make_response(request_id, error={"code": -32601, "message": f"Method not found: {method}"})
```

In **FastMCP**, the table is built from registrations — you never write `if method ==`:

```python
from fastmcp import FastMCP
mcp = FastMCP("shop")
# each registration adds a row to the tools/* dispatch table
@mcp.tool
def list_products(category: str | None = None) -> list[dict]:
    """List products, optionally filtered by category."""
    ...
```

The **TypeScript SDK** does the same via `registerTool`/`registerResource`/
`registerPrompt`; the **Java SDK** via `registerTool`/`resources()`/`prompts()`.

## Industry-standard pattern

A static, explicit dispatch map is table stakes for any network protocol
implementation: HTTP routers, gRPC method tables, and RPC registries all work this
way. The general rules: **no eval on untrusted strings, fixed set of routes, explicit
default for unknown routes, and dispatch *before* any side effects**.

## Common mistakes

- **Dynamic dispatch on the method string** (`getattr(handler, method)` or `eval`) —
  the classic RCE hole in hand-rolled RPC servers.
- **Doing auth/validation *inside* handlers** instead of at dispatch time — duplicated
  and easy to forget (see [11-middleware-routing.md](11-middleware-routing.md)).
- **Not handling unknown methods** — a bare exception becomes a confusing
  `-32603` instead of a clean `-32601`.
- **Mixing request and notification dispatch** — e.g., trying to respond to a
  notification because the dispatch code assumed every message has an `id`.

## Testing

- **Method coverage**: every method in the spec's namespace you claim to support is
  dispatched ([15-testing/capability-testing.md](../15-testing/capability-testing.md)).
- **Unknown-method tests**: `"foo/bar"` → `-32601`; wrong namespace
  (`"resources/call"`) → `-32601`.
- **Notification tests**: dispatching a notification has no response and no error.
- **Concurrency tests**: many in-flight requests through the table don't corrupt state.

## Debugging

- Inspector's protocol panel shows the method of every message — the first question is
  always "did this request even reach the right dispatch path?"
- If a request reaches the wrong handler, check for **name shadowing**: two components
  with the same name registered in different providers (see
  [06-provider-routing.md](06-provider-routing.md)).

## Security considerations

- **The dispatch table is the attack surface boundary.** Keep it static and minimal;
  add capability and authorization gates *at* the table, not inside handlers
  ([08-authorization-routing.md](08-authorization-routing.md)).
- Log the method + name of every dispatched operation (auditability,
  [14-security/auditability.md](../14-security/auditability.md)).

## Related concepts

- [02-tool-routing.md](02-tool-routing.md) · [03-resource-routing.md](03-resource-routing.md) · [04-prompt-routing.md](04-prompt-routing.md)
- [05-capability-routing.md](05-capability-routing.md)
- [10-error-routing.md](10-error-routing.md)
- [11-middleware-routing.md](11-middleware-routing.md)
- [01-fundamentals/03-json-rpc.md](../01-fundamentals/03-json-rpc.md)