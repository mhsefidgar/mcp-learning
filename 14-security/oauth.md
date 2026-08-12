# OAuth Concepts

## What is it?

**OAuth 2.0** is the industry-standard authorization framework for delegated
access: a *resource owner* (a person) grants a *client application* permission to
call a *resource server* on their behalf, without handing the client their
password. The client ends up with a short-lived **access token** it presents with
each call.

MCP does not define a general-purpose auth mechanism in its core protocol, but the
**MCP authorization extensions** standardize OAuth 2.0 flows for remote servers
(Streamable HTTP): dynamic client registration, the authorization-code flow with
PKCE, token refresh, and resource-server-style token validation.

## Why does MCP need it?

A remote MCP server is a set of tools a client can trigger. When that server is
multi-tenant (many users, each with their own data and permissions), the client
needs to act **on behalf of a specific user**. That is exactly OAuth's job. Without
it you get either "everyone shares one API key" or "build-your-own auth".

## How it works (authorization-code flow with PKCE)

1. **Discovery**: the client fetches the server's OAuth metadata (issuer,
   authorization endpoint, token endpoint) — a well-known configuration document.
2. **Registration**: the client registers (dynamic client registration, or static
   in production) and obtains a `client_id`.
3. **Authorization**: the client redirects the user to the authorization server,
   which authenticates the user and returns an authorization code to a callback.
   **PKCE** proves the client that started the flow is the one finishing it — the
   code verifier travels only in hashed form during step 3.
4. **Token exchange**: the client swaps the code for an **access token** (and
   optionally a **refresh token**).
5. **Access**: the client sends the access token with every MCP request
   (`Authorization: Bearer <token>`). The server validates signature/expiry/issuer
   and derives the principal ([authentication.md](authentication.md)).
6. **Refresh**: when the access token expires, the client uses the refresh token to
   get a new one without bothering the user again.

## MCP-specific behavior

- **Core protocol**: no auth fields — tokens ride transport headers.
- **Authorization extensions**: standardize the flows above for Streamable HTTP
  servers, including a metadata endpoint and scopes.
- **2026-07-28 hardening**: RFC 9207 `iss` parameter validation (the token is
  bound to its issuer), client credentials bound to the issuer, and **CIMD**
  (client metadata documents) replacing dynamic client registration. See
  [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md).
- **stdio servers**: no OAuth — the process boundary is the trust boundary
  ([01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)).

## Industry-standard pattern

- Use a real identity provider and a maintained OAuth library — do not implement
  token signing or the code exchange yourself.
- PKCE on every public client; confidential clients additionally use client
  authentication.
- Short-lived access tokens (minutes), longer-lived refresh tokens (hours/days),
  refresh-token rotation, and revocation on logout.
- `scope` = least privilege: request only the scopes the tools need
  ([least-privilege.md](least-privilege.md)).

## Common mistakes

- Skipping PKCE (open redirect / code interception).
- Long-lived access tokens instead of refresh tokens.
- Accepting tokens without validating issuer, audience, and expiry.
- One shared token for all users (no principal, so authorization is impossible).
- Storing refresh tokens insecurely (logs, plaintext config).

## Testing

- Full flow against the auth server: login → code → token → authorized call.
- Expired token → clean 401 → refresh → retry works.
- Wrong-audience token → rejected even if signature is valid.
- PKCE mismatch → authorization fails.
See [15-testing/security-testing.md](../15-testing/security-testing.md).

## Security considerations

- **TLS everywhere** — tokens are bearer credentials
  ([11-communication-transport/tls.md](../11-communication-transport/tls.md)).
- Validate **issuer** (RFC 9207) so a stolen token from another provider can't be
  replayed against yours.
- Rotate and revoke; never log tokens
  ([sensitive-data-redaction.md](sensitive-data-redaction.md)).

## Related

- [authentication.md](authentication.md)
- [authorization.md](authorization.md)
- [least-privilege.md](least-privilege.md)
- [secret-management.md](secret-management.md)
- [11-communication-transport/tls.md](../11-communication-transport/tls.md)
