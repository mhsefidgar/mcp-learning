# Authorization

## What is it?

**Authorization** is deciding *what* an authenticated principal may do: which tools
they may call, which resources they may read, which prompts they may use. It answers
"may you?" — the question *after* [authentication.md](authentication.md)'s "who are
you?"

## Why does MCP need it?

Authentication proves identity; authorization prevents that identity from doing
anything. An MCP server with auth but no authorization is a building with a locked
front door and every office unlocked: any valid user can call `delete_order`, read
`config://secrets`, or drain the database. Authorization is where least privilege
([least-privilege.md](least-privilege.md)) actually happens.

## How it works

1. **Authenticate** → establish the principal
   ([authentication.md](authentication.md)).
2. **Determine identity details** → roles, groups, scopes.
3. **Check permission for the specific operation** → principal + tool/resource +
   arguments vs. policy (RBAC/ABAC).
4. **Route accordingly** → permitted operations dispatch; denied ones return a
   defined denial error; the *catalog* shows only permitted components
   ([03-routing-dispatch/08-authorization-routing.md](../03-routing-dispatch/08-authorization-routing.md)).

```
authenticate → principal → can principal call delete_order? → yes: dispatch | no: deny
```

## MCP-specific behavior

- **Authorization must gate two surfaces**: the *catalog* (what the model can even
  see) and *dispatch* (what actually executes) — both from the same policy
  ([03-routing-dispatch/08-authorization-routing.md](../03-routing-dispatch/08-authorization-routing.md)).
- **Per-resource authorization**: "may read resources" is too coarse; "may read
  `config://app/*` but not `config://secrets/*`" is right.
- **The 2026-07-28 spec's header-based routing** (`Mcp-Name`) lets a gateway
  authorize on the tool name before the body
  ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).
- **Authorization is not part of the core protocol** — it's your layer, built at
  the middleware/transport boundary.

## Example

Per-tool permission check (FastMCP middleware; educational simplification):

```python
from fastmcp.server.middleware import Middleware, MiddlewareContext

class AuthorizeMiddleware(Middleware):
    def __init__(self, policy):     # policy: principal -> set of (tool, resource_uri_pattern)
        self.policy = policy

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        principal = context.fastmcp_context.get_state("principal")
        allowed = self.policy.allowed_tools(principal)
        if context.message.name not in allowed:
            raise PermissionError(f"{principal} may not call {context.message.name}")
        return await call_next(context)
```

## Industry-standard pattern

RBAC/ABAC with deny-by-default is the standard (cloud IAM, Kubernetes RBAC).
Rules: **deny by default**, **allow explicitly**, **check at every operation**
(never just at connect), **policy from a central source**, and **audit denies**
([auditability.md](auditability.md)).

## Common mistakes

- **Authorization only at connect time** — permissions must be checked per call.
- **Tool-name-only allowlists** — authorize on operation type + resource scope +
  role together.
- **Filtering the catalog but not enforcing dispatch** (or vice versa) — a
  hidden-but-callable tool leaks ([03-routing-dispatch/08-authorization-routing.md](../03-routing-dispatch/08-authorization-routing.md)).
- **Trusting the model's choices** — the model may call anything in the catalog;
  the server must enforce.

## Testing

- **Per-principal tests**: each principal's permitted/denied matrix
  ([15-testing/security-testing.md](../15-testing/security-testing.md)).
- **Catalog tests**: principals see only their components.
- **Direct-call tests**: a denied tool is rejected even if called directly.
- **Deny-audit tests**: denials are logged.

## Security considerations

- **Deny by default** — anything not explicitly allowed is denied.
- **Least privilege** — start minimal, add as needed
  ([least-privilege.md](least-privilege.md)).
- **Authorization must not depend on client-supplied data** (roles in the token
  are fine if signed; roles in arguments are not).

## Related

- [authentication.md](authentication.md)
- [tool-permissions.md](tool-permissions.md)
- [least-privilege.md](least-privilege.md)
- [03-routing-dispatch/08-authorization-routing.md](../03-routing-dispatch/08-authorization-routing.md)
- [auditability.md](auditability.md)