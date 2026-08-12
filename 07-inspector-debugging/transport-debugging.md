# Diagnosing Transport Problems

## What is it?

A systematic approach to **"the protocol is fine but the bytes don't flow"** —
failures at the transport layer
([01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)).

## stdio diagnostics

The single most important fact: **stderr is the server's voice; stdout is the
protocol.** Almost every stdio mystery is solved by watching stderr.

```bash
# Run the server manually and watch both streams
python server.py 2>&1 | tee server.log
```

Checklist:

1. **Does it print anything on stderr?** No → it's hanging before the loop (import
   error, waiting on something). Yes → read it; FastMCP/SDKs log the handshake.
2. **Is stdout clean?** Anything not newline-delimited JSON on stdout corrupts the
   protocol (a stray `print()` is a protocol bug).
3. **Did the process exit immediately?** Exit code 0 → clean shutdown (client closed
   early?); nonzero → crash; check the traceback on stderr.
4. **Spawn test**: run the server exactly as the client does — same command, same
   cwd, same env. Path/env differences are the classic "works by hand, fails from the
   client" cause.

## HTTP diagnostics

Start with headers, then the body:

```bash
# Is the endpoint up at all?
curl -v http://localhost:8000/mcp

# Does it speak MCP? (session-based spec)
curl -N -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"curl","version":"0"}}}'
```

Checklist:

1. **Status codes**: `404` → wrong path; `405` → wrong method (MCP uses POST);
   `406` → missing `Accept: application/json, text/event-stream`; `401/403` → auth.
2. **`Mcp-Session-Id`**: first response should issue it; subsequent requests must
   echo it — dropping it causes "unknown session" errors
   ([01-fundamentals/09-sessions-and-lifecycle.md](../01-fundamentals/09-sessions-and-lifecycle.md)).
3. **SSE stream**: for long requests, the response may be `text/event-stream` — use
   `curl -N` and read event-by-event.
4. **TLS**: `curl -v` shows the certificate chain; verify hostname, expiry, and
   trust ([11-communication-transport/tls.md](../11-communication-transport/tls.md)).
5. **Behind a proxy?** Check reverse-proxy config: timeout settings, buffering of
   SSE, session-id header forwarding.

## The layer test

When a call fails over a transport, isolate the layer:

1. **Transport**: does the raw exchange (above) work?
2. **Protocol**: does the handshake complete and the method get dispatched?
3. **Application**: does the handler fail?

Each "yes" narrows the bug to the next layer.

## Related

- [01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)
- [initialization-debugging.md](initialization-debugging.md)
- [11-communication-transport/http.md](../11-communication-transport/http.md)
- [11-communication-transport/tls.md](../11-communication-transport/tls.md)