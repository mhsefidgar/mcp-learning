# Authentication

## What is it?

**Authentication** is proving *who* is calling: the client presents credentials
(bearer token, client certificate, OAuth access token) and the server verifies them
**before** any MCP request is processed. It answers "who are you?" — not "what may
you do?" (that's [authorization.md](authorization.md)).

## Why does MCP need it?

A remote MCP server is code execution on demand: anyone who can reach it can trigger
its tools. Without authentication, that "anyone" includes attackers. Authentication
is the gate at the boundary — for local stdio servers, the OS process boundary *is*
the auth (you only spawn servers you chose); for remote servers, identity must be
proven per request (or per session).

## How it works

1. **The client obtains credentials** (an API key, an OAuth access token via
   [oauth.md](oauth.md), or a client certificate).
2. **The transport presents them**: HTTP `Authorization: Bearer <token>` is the
   standard for Streamable HTTP; mTLS presents a certificate.
3. **The server verifies** at the transport/middleware layer *before* MCP dispatch:
   signature, expiry, issuer ([03-routing-dispatch/11-middleware-routing.md](../03-routing-dispatch/11-middleware-routing.md)).
4. **The verified identity flows into authorization**: the request carries a
   principal for permission checks ([authorization.md](authorization.md)).

## MCP-specific behavior

- **The stable session-based spec has no auth fields in the protocol** — auth rides
  the transport (HTTP headers). The **auth extensions** add OAuth 2.0 for
  authorization-code flows and resource-server style access
  ([oauth.md](oauth.md)).
- **2026-07-28 hardening**: RFC 9207 `iss` validation (bind tokens to their
  issuer), client credentials bound to issuer, and CIMD (client metadata documents)
  replacing dynamic client registration — see
  [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md).
- **`clientInfo` is not authentication** — a client *saying* "I am admin" is
  identification, not proof. Never authorize on `clientInfo`.
- **stdio**: the process boundary is the auth — spawn only trusted servers
  ([01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)).

## Example

Middleware that authenticates before dispatch (educational simplification — use a
real auth library in production):

```python
from fastmcp.server.middleware import Middleware, MiddlewareContext

class AuthMiddleware(Middleware):
    def __init__(self, verify):
        self.verify = verify            # token -> principal

    async def on_message(self, context: MiddlewareContext, call_next):
        # Client-supplied metadata rides the request's _meta field.
        meta = context.fastmcp_context.request_context.meta if context.fastmcp_context else None
        token = (meta or {}).get("auth")
        principal = self.verify(token)
        if principal is None:
            raise PermissionError("unauthenticated")
        # store principal for authorization + audit
        return await call_next(context)
```

In production, authenticate at the HTTP layer (a real auth server/middleware), not
in MCP-land.

## Industry-standard pattern

Bearer tokens + OAuth 2.0 + (for server-to-server) mTLS is the standard stack.
Rules: **verify before dispatch**, **tokens expire and rotate**, **bind tokens to
issuer** (RFC 9207), and **never build your own crypto** — use a proven identity
provider and library.

## Common mistakes

- **Auth only in the handler** — a forgotten handler skips the gate; do it at the
  boundary.
- **Trusting `clientInfo`** — identification ≠ authentication.
- **No expiry/rotation** — leaked tokens work forever.
- **Self-rolled tokens** — use standard signed tokens (JWT/OAuth), not "base64 of
  the username".
- **Auth errors that look like bugs** — clean 401/403 with a clear message
  ([03-routing-dispatch/10-error-routing.md](../03-routing-dispatch/10-error-routing.md)).

## Testing

- **Positive tests**: valid credentials → request proceeds with the right principal
  ([15-testing/security-testing.md](../15-testing/security-testing.md)).
- **Negative tests**: missing/expired/forged tokens → clean denial.
- **Boundary tests**: auth applies to *every* method, not just tools.
- **Leak tests**: credentials never appear in logs/errors
  ([sensitive-data-redaction.md](sensitive-data-redaction.md)).

## Security considerations

- **Auth without TLS is theater** — credentials in plaintext
  ([11-communication-transport/tls.md](../11-communication-transport/tls.md)).
- **Auth without authorization is a locked door with every room open** —
  [authorization.md](authorization.md).
- **Rate-limit the auth path** — it's the brute-force surface
  ([08-reliability-resilience/rate-limiting.md](../08-reliability-resilience/rate-limiting.md)).

## Related

- [oauth.md](oauth.md)
- [authorization.md](authorization.md)
- [tool-permissions.md](tool-permissions.md)
- [11-communication-transport/tls.md](../11-communication-transport/tls.md)
- [15-testing/security-testing.md](../15-testing/security-testing.md)