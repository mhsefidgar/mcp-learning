# TLS (Transport Layer Security)

## What is it?

**TLS** encrypts and authenticates traffic in transit: the client verifies the
server's **certificate** (authenticity), and all bytes are **encrypted**
(confidentiality) and **integrity-protected** (tamper-evident). Every production
Streamable HTTP MCP endpoint must be served over TLS.

## Why does MCP need it?

MCP remote traffic is *actions*, not just reads: tool calls can trigger payments,
deploys, deletions, and data exfiltration. Without TLS:

- a network observer reads every tool call, argument, and response (including
  `Mcp-Session-Id` and tokens);
- a man-in-the-middle can modify requests ("transfer 10" becomes "transfer
  100000");
- a fake server can impersonate the real one.

TLS is the floor, not the ceiling: it protects *in transit*; the server still needs
authentication and authorization at the application layer
([14-security/authentication.md](../14-security/authentication.md)).

## How does it work (the parts that matter)

1. **Handshake**: the client connects; the server presents its certificate
   (public key + identity + signature by a trusted **CA**).
2. **Verification**: the client checks the certificate chain (trusted root),
   **hostname** (cert matches the URL), and **expiry/revocation**.
3. **Key exchange**: both sides derive session keys (forward secrecy with
   ECDHE/RSA-OAEP depending on config).
4. **Application data**: everything after the handshake is encrypted.

## Mental model

TLS is a **sealed, signed envelope delivered by a courier with ID**: the courier
(certificate) proves who they are (identity), you check their badge against the
issuer (CA), and the envelope is sealed (encrypted) so no one en route can read or
alter it. If the courier can't prove who they are, you don't hand them the
envelope.

## MCP-specific behavior

- **TLS sits under the MCP transport**: it's the HTTP layer's job
  ([http.md](http.md)). MCP itself has no TLS concepts.
- **Where TLS terminates matters**:
  - at the app server (simplest),
  - at a reverse proxy/LB (standard — [load-balancing.md](../10-scaling-performance/load-balancing.md)),
  - at the edge/CDN (common — but then the app-to-LB hop needs its own protection
    inside the network).
- **Mutual TLS (mTLS)**: both sides present certificates — a strong option for
  server-to-server MCP ([14-security/authentication.md](../14-security/authentication.md)).

## Example

Running the FastMCP HTTP server behind TLS (conceptual — in practice a reverse
proxy handles TLS):

```bash
# Typical: TLS terminated by a reverse proxy / LB in front of the app
# app:  mcp.run(transport="streamable-http", host="127.0.0.1", port=8000)
# proxy: listens on 443 with the certificate, forwards to 8000

# Verify from the client side:
openssl s_client -connect mcp.example.com:443 -servername mcp.example.com
```

## Industry-standard pattern

TLS 1.3 (or 1.2+) with modern ciphers, certificates from a public CA (or a
private CA with proper distribution), automatic renewal (Let's Encrypt), and
**strict verification** client-side (never disable certificate checks) — these are
non-negotiable production standards.

## Common mistakes

- **Self-signed certs everywhere** (or `verify=False`) — no real protection and a
  habit that leaks into production.
- **Hostname mismatches** — a valid cert for the wrong name verifies as invalid.
- **TLS termination without internal protection** — the app-to-proxy hop in
  plaintext leaks everything inside the network.
- **Expired certs** — the silent outage; automate renewal and monitor expiry.
- **Old TLS versions / weak ciphers** — enable TLS 1.2+, disable known-broken
  suites.

## Testing

- **Handshake tests**: `openssl s_client` succeeds with the expected cert/hostname.
- **Verification tests**: connecting with `verify=False` *fails* (your client must
  verify).
- **Expiry tests**: certificate expiry is monitored and alerted.
- **Proxy tests**: TLS end-to-end through the LB works with streaming intact.

## Security considerations

- **TLS ≠ authentication**: the *user* isn't identified by the certificate (unless
  mTLS) — application auth still needed.
- **TLS ≠ authorization**: encrypted transit doesn't mean the caller may call
  `delete_order` ([14-security/authorization.md](../14-security/authorization.md)).
- **Session ids and tokens are still secrets inside TLS**: don't log them.

## Related

- [http.md](http.md)
- [14-security/authentication.md](../14-security/authentication.md)
- [01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)
- [07-inspector-debugging/transport-debugging.md](../07-inspector-debugging/transport-debugging.md)