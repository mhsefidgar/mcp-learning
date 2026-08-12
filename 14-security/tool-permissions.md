# Tool Permissions

## What is it?

**Tool permissions** decide *which tools a given caller may invoke*, and with what
arguments. Authentication answers "who are you?"; authorization answers "what may
you do?" — tool permissions are authorization applied at the granularity of a
single tool call ([authorization.md](authorization.md)).

## Why does MCP need it?

Tools are the dangerous surface: one tool reads a database, another deletes rows,
another sends email. A client that is authenticated should not automatically be
able to call all of them. Per-tool permissions turn a "logged in" caller into a
"caller who may run `read_customer` but not `delete_customer`" caller — the
difference between a useful API and a foot-gun API.

## How it works

1. **Authenticate** the caller to get a principal
   ([authentication.md](authentication.md)).
2. **Resolve permissions** for that principal — usually from an allowlist per
   principal or per role: `{principal -> {tool: {allowed, constraints}}}`.
3. **Check before dispatch**: the authorization layer inspects
   `tools/call` params (`name`, `arguments`) against the allowlist — this is
   authorization-aware routing
   ([03-routing-dispatch/08-authorization-routing.md](../03-routing-dispatch/08-authorization-routing.md)).
4. **Enforce**: deny → `-32602`-style tool error ("unauthorized"), with the reason
   audited; allow → execute.

For *visibility* (hiding unpermitted tools from `tools/list`) vs *enforcement*
(rejecting calls) — production systems usually do both: hide what you can't call,
and *still enforce at call time*, because hiding is not security.

## MCP-specific behavior

- **The protocol has no permission model** — it is entirely server-side policy.
  MCP only carries the method (`tools/call`), the tool name, and arguments.
- The server's capability declaration (`tools/list`) is *advertisement*, not
  entitlement — a client may call any listed tool; the server must enforce.
- A common pattern is a **transform** that filters `tools/list` by permission while
  middleware enforces at `tools/call`
  ([12-fastmcp/transforms.md](../12-fastmcp/transforms.md),
  [12-fastmcp/middleware.md](../12-fastmcp/middleware.md)).

## Example (FastMCP middleware enforcing an allowlist)

```python
from fastmcp.server.middleware import Middleware, MiddlewareContext

class ToolPermissionMiddleware(Middleware):
    def __init__(self, allowed):          # {tool_name: set(principals)}
        self.allowed = allowed

    async def on_message(self, context: MiddlewareContext, call_next):
        if context.method == "tools/call":
            name = context.message.name
            meta = context.fastmcp_context.request_context.meta if context.fastmcp_context else None
            principal = (meta or {}).get("principal")
            if principal not in self.allowed.get(name, set()):
                raise PermissionError(f"caller may not invoke tool '{name}'")
        return await call_next(context)
```

## Industry-standard pattern

- **Policy, not code**: express permissions as data (allowlist/roles), not
  scattered `if` statements in handlers.
- **Default deny**: no rule = no access. Never default-allow.
- **Least privilege** ([least-privilege.md](least-privilege.md)): grants only what
  a role needs.
- **Argument-level constraints** where meaningful (e.g., "may read customers, but
  not export them") — enforced at the boundary, not inside the tool.
- **Enforce at call time regardless of what you advertise.**

## Common mistakes

- Hiding tools from `tools/list` but not enforcing at `tools/call` — a crafted
  client calls them anyway.
- Authorization inside the tool body (skipped for any tool without the check).
- Checking the *client name* instead of the authenticated principal.
- Allow-everything defaults.

## Testing

- Each tool: allowed principal succeeds, denied principal gets a clean error
  ([15-testing/security-testing.md](../15-testing/security-testing.md)).
- Hidden-but-callable test: a client calls a tool it was not shown — must be denied.
- Every method, not just tools: `resources/read` and `prompts/get` need checks too.
- Audit: denied attempts are recorded ([auditability.md](auditability.md)).

## Security considerations

- **Tool permissions are the last line of defense** for destructive operations —
  layer them with confirmation ([destructive-operations.md](destructive-operations.md)).
- Argument constraints protect against *abuse of a legitimate tool* (e.g., a
  "send_email" tool used to spam).

## Related

- [authorization.md](authorization.md)
- [least-privilege.md](least-privilege.md)
- [authentication.md](authentication.md)
- [03-routing-dispatch/08-authorization-routing.md](../03-routing-dispatch/08-authorization-routing.md)
- [15-testing/security-testing.md](../15-testing/security-testing.md)
