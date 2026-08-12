# 08 — Authorization Routing

## What is it?

**Authorization routing** is the rule that *which* components a client may see and
call depends on **who** the client is. Instead of exposing every tool to every
caller, the server:

1. **Authenticates** the request (who are you? — see
   [14-security/authentication.md](../14-security/authentication.md)).
2. **Determines identity** (principal, roles, scopes).
3. **Checks permissions** (may this principal call `delete_order`? read
   `config://secrets`?).
4. **Routes accordingly**: the catalog (`tools/list`) shows *only permitted*
   components, and dispatch (`tools/call`, `resources/read`) *enforces* the same
   permissions on every request.

## Why does MCP need it?

MCP servers are increasingly multi-tenant: many users, many agents, one deployment. A
tool that deletes production data must not be reachable by every caller. And because
the model chooses tools from `tools/list`, **filtering the catalog is itself a
security control**: a tool the model never sees, it never calls. Authorization must
happen at the *routing layer* so no handler can be reached without a permission check.

## How does it work?

```
request ──► authenticate ──► identity ──► permission check ──► dispatch ──► handler
              (token,            │             │
               session,          ▼             ▼
               mTLS)         principal    allowed tools/resources/prompts?
                                             │ yes        │ no
                                             ▼            ▼
                                       dispatch      deny (routed error)
```

- **Discovery-time filtering**: `tools/list`, `resources/list`, `prompts/list` return
  only what the principal may use. (The *names* of hidden tools are also hidden.)
- **Dispatch-time enforcement**: `tools/call` re-checks — never trust that the client
  only calls listed tools.
- **Both checks must agree**, or a hidden-but-callable tool leaks.

## Mental model

Authorization routing is **RBAC at the router**: like a web app's middleware that
attaches a user to the request and controllers that check roles before acting. The
MCP twist: the *menu* (the catalog) is filtered too, not just the *service*.

## MCP-specific behavior

- **The protocol has no authorization fields** in the session-based spec: identity
  arrives via the transport (HTTP bearer tokens, mTLS) or the session's authenticated
  origin. The 2026-07-28 spec and the auth extensions add OAuth-based auth
  ([14-security/authentication.md](../14-security/authentication.md)).
- **Per-component visibility is a FastMCP feature** (per-session visibility, enabled
  transforms); the *authorization decision* is yours. FastMCP's `auth` field on
  components plus providers give you the hook — but the policy is application code.
- **The catalog is a disclosure channel**: exposing a tool's *name* or *description*
  can leak internal knowledge. Filtering the catalog is part of authorization.

## Example

A minimal FastMCP authorization middleware (educational simplification — use a real
auth library in production):

```python
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext

class AuthMiddleware(Middleware):
    """Gate tools/call by a bearer token embedded in request state.

    Educational simplification — not production-ready.
    """

    def __init__(self, allowed: dict[str, set[str]]):
        self.allowed = allowed  # token -> set of tool names

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        token = context.message.meta.get("auth_token") if context.message.meta else None
        permitted = self.allowed.get(token, set())
        name = context.message.name
        if name not in permitted:
            from fastmcp.exceptions import ToolError
            raise ToolError(f"Not authorized to call {name}")
        return await call_next(context)

mcp = FastMCP("secured")
mcp.add_middleware(AuthMiddleware({"tok-read": {"list_orders"}, "tok-admin": {"list_orders", "delete_order"}}))
```

> Real deployments authenticate at the transport (HTTP bearer tokens validated before
> the MCP layer) — see [14-security/authentication.md](../14-security/authentication.md).

## Industry-standard pattern

Authenticate once at the edge, authorize at every operation, and filter discoverable
surface by identity — this is the standard posture of **RBAC/ABAC systems, Kubernetes
RBAC, cloud IAM, and enterprise gateways**. The "filter the catalog" part is
**capability exposure control**: like cloud consoles showing only the services a role
can use.

## Common mistakes

- **Filtering the catalog but not enforcing dispatch** (or vice versa) — the two must
  be built from the same policy.
- **Authorizing by tool *name* alone** — name-based allowlists rot; authorize by
  operation type, resource scope, and role together.
- **Trusting the client's self-asserted identity** (e.g. a `clientInfo` field) — that
  is identification, not authentication.
- **Applying authorization only in the handler** — by then, listing already leaked
  existence.
- **Deny-by-default forgotten** — an unlisted tool that falls through to "allowed" is
  a hole.

## Testing

- **Catalog tests**: different principals see different `tools/list` results
  ([15-testing/security-testing.md](../15-testing/security-testing.md)).
- **Dispatch tests**: each principal's *permitted* tools work; *forbidden* ones
  return the deny error.
- **Hidden-but-callable tests**: a tool absent from one principal's catalog is also
  rejected on direct call.
- **Negative-path tests**: missing/expired tokens, revoked permissions mid-session.

## Debugging

- Log the principal + decision for every denied request (auditability —
  [14-security/auditability.md](../14-security/auditability.md)).
- A "works in Inspector, fails in my app" authorization bug is almost always an
  identity problem: Inspector sends no token. Check what identity your transport
  actually attaches.

## Security considerations

- **Deny by default**, allow explicitly.
- **Least privilege**: a read-only principal shouldn't even *see* write tools
  ([14-security/tool-permissions.md](../14-security/tool-permissions.md)).
- **Authorization must not depend on the model's choices** — enforce server-side,
  always.
- Audit every deny and every sensitive allow
  ([14-security/auditability.md](../14-security/auditability.md)).

## Related concepts

- [01-request-dispatch.md](01-request-dispatch.md)
- [11-middleware-routing.md](11-middleware-routing.md)
- [14-security/authentication.md](../14-security/authentication.md)
- [14-security/authorization.md](../14-security/authorization.md)
- [14-security/tool-permissions.md](../14-security/tool-permissions.md)