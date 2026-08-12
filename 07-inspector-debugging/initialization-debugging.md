# Diagnosing Initialization Failures

## What is it?

A systematic checklist for **"my client can't connect to the server"** — failures in
the handshake phase ([01-fundamentals/05-initialization.md](../01-fundamentals/05-initialization.md)),
before any tool can be called.

## The failure classes

| Failure | Typical cause | How to find it |
|---------|---------------|----------------|
| Server process won't start (stdio) | missing dependency, syntax error, wrong command | run the server manually; read **stderr** |
| Connection refused / timeout (HTTP) | wrong URL/port, server not listening, firewall | `curl -v http://host:port/mcp`; check the port is bound |
| Handshake times out | server starts but never answers `initialize` | protocol log: is `initialize` even received? |
| Version negotiation failure | disjoint protocol version sets | read the `protocolVersion` in both messages ([01-fundamentals/07-version-negotiation.md](../01-fundamentals/07-version-negotiation.md)) |
| `notifications/initialized` missing | client-side bug (or modern stateless client) | protocol log |
| Capability mismatch | server declares something it doesn't implement | [capabilities.md](capabilities.md) |
| TLS/certificate error (HTTP) | self-signed cert, wrong hostname, expired cert | inspect the cert; fix trust or URL |
| Auth failure (HTTP) | missing/invalid token | check the transport headers; Inspector sends **no token** |

## The checklist (in order)

1. **Can the server start at all?** Run it manually. For stdio: does it print to
   stderr and wait? For HTTP: is the port listening?
2. **Can a raw client reach it?** For HTTP, `curl` the endpoint; for stdio, feed it
   a hand-written `initialize` request
   ([01-fundamentals/examples/raw_handshake.py](../01-fundamentals/examples/raw_handshake.py)).
3. **Does the handshake complete?** Watch the protocol log: initialize →
   response → initialized.
4. **What does each side declare?** Compare the capability maps against what you
   registered.
5. **What version was negotiated?** Older-than-expected behavior is often just an
   old negotiated version.

## Common traps

- **Inspector vs. your app differ**: Inspector's client has its own capabilities and
  no auth — differences there point at *your client*, not the server.
- **A "handshake timeout" is often a server that crashed after starting** — the
  protocol log shows silence; stderr shows the traceback.
- **Two servers in play**: a wrong path/command silently running a *different*
  server; log `serverInfo` from the handshake and verify the name/version.

## Related

- [01-fundamentals/05-initialization.md](../01-fundamentals/05-initialization.md)
- [transport-debugging.md](transport-debugging.md)
- [protocol-messages.md](protocol-messages.md)
- [15-testing/failure-testing.md](../15-testing/failure-testing.md)