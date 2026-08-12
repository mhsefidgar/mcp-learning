# 08 — Transports

## What is it?

A **transport** is the mechanism that carries JSON-RPC messages between client and
server. MCP defines two transports in the current stable spec:

| Transport | Where | Direction | Typical use |
|-----------|-------|-----------|-------------|
| **stdio** | local machine | client **spawns** the server as a child process and talks over its stdin/stdout | IDE plugins, local CLI agents, dev-time servers |
| **Streamable HTTP** | network | client sends HTTP requests to a server URL | remote/production servers, multi-client services |

(A third, the legacy **HTTP + SSE** transport, is deprecated with a year-long offramp
in the 2026-07-28 spec.)

```
stdio:
┌──────────┐  spawn + pipes   ┌──────────────┐
│  Client  │ ◄──────────────► │ Server proc  │
└──────────┘  stdin / stdout  └──────────────┘

Streamable HTTP:
┌──────────┐   POST /mcp (JSON-RPC)   ┌──────────────┐
│  Client  │ ───────────────────────► │ HTTP server  │
│          │ ◄─────────────────────── │  (MCP)       │
└──────────┘   response / SSE stream  └──────────────┘
```

## Why does MCP need it?

Because the *same protocol* must work in two very different worlds:

- **Local**: the client and server are on one machine; the cheapest, most private
  transport is a child process with pipes. No network, no auth, no ports.
- **Remote**: the server is a service many clients reach over a network; it must ride
  on HTTP (with TLS, auth, load balancing).

By keeping transports pluggable, MCP lets you develop locally over stdio and deploy the
*identical* server remotely over HTTP.

## How does it work?

### stdio

1. The client spawns the server process: `python server.py` or `node server.js`.
2. JSON-RPC messages are framed over stdin/stdout using **newline-delimited JSON**
   (one JSON object per line; the SDKs implement this framing).
3. The server writes its responses and notifications to stdout; the client reads them.
4. **stderr is reserved for human/observability output** — logs, tracebacks. It is
   *not* part of the protocol.
5. When either side exits or closes the pipes, the session ends.

Key property: **one client per server process, always**. Spawning is cheap, so clients
do it per-connection and never share server processes.

### Streamable HTTP

1. The client `POST`s a JSON-RPC message to the server's endpoint (typically `/mcp`).
2. The server answers with an HTTP response whose body is JSON-RPC; for
   server-initiated messages (notifications, and in the session-based spec,
   server→client requests) the server may hold the response open as an **SSE stream**
   (content-type `text/event-stream`).
3. In the session-based spec, the server returns an **`Mcp-Session-Id`** header on the
   first response; the client must echo it on subsequent requests.
4. Clients **must** send `Accept: application/json, text/event-stream`; requests that
   don't get a `406`.

### TLS

TLS encrypts the HTTP transport: the server presents a certificate, the client verifies
it, and all bytes (including `Mcp-Session-Id` and message bodies) are confidential and
tamper-evident. In production, every Streamable HTTP endpoint is served **behind TLS**
(terminated by the app, a reverse proxy, or a load balancer). See
[11-communication-transport/tls.md](../11-communication-transport/tls.md) for the deep
dive.

## Mental model

**stdio** is a **phone line between two processes on one desk** — private, free, and
gone the moment either hangs up. **Streamable HTTP** is a **public mail service** —
addressed envelopes over a shared network, needing locks (TLS), IDs (session), and
rules of the road (headers, status codes). The protocol (the *message*) is identical;
only the *delivery* differs.

## MCP-specific behavior

- **Framing**: stdio uses newline-delimited JSON in the current spec-era SDKs
  (historically LSP-style `Content-Length` headers; SDKs handle whichever they speak).
  Don't hand-roll this — use the SDK.
- **`Mcp-Session-Id`** ties an HTTP connection's requests into a session
  ([09-sessions-and-lifecycle.md](09-sessions-and-lifecycle.md)). Servers may require
  it after the first request; clients must retry once without it if they get a
  session-not-found error.
- **SSE on POST**: the response to a POST may be a *stream* the server keeps open to
  deliver server-initiated messages. The client must be able to read both a plain JSON
  response and an SSE stream.
- **Dependency isolation (stdio)**: because each client spawns its own server process,
  server code is naturally isolated per client — a crash or a hang takes down only that
  client's session. This is a *transport property*, not something you implement.
- **Health checks** are not part of the MCP protocol; on HTTP deployments you add a
  separate `/healthz` endpoint ([10-scaling-performance/health-checks.md](../10-scaling-performance/health-checks.md)).
- **2026-07-28 stateless spec**: Streamable HTTP drops `Mcp-Session-Id` and adds
  required `Mcp-Method`/`Mcp-Name` headers, and every request carries
  `MCP-Protocol-Version` + identity in `_meta`. See
  [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md).

## Example

**stdio** is the default in FastMCP:

```python
from fastmcp import FastMCP
mcp = FastMCP("demo")
# ...
if __name__ == "__main__":
    mcp.run()                      # transport="stdio" is the default
```

**Streamable HTTP**:

```python
from fastmcp import FastMCP
mcp = FastMCP("demo")
if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
```

**TypeScript — stdio server:**

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
const server = new McpServer({ name: "demo", version: "1.0.0" });
await server.connect(new StdioServerTransport());
```

**TypeScript — streamable HTTP server (Express):**

```typescript
import express from "express";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";

const app = express();
const transports: Record<string, StreamableHTTPServerTransport> = {};

app.post("/mcp", async (req, res) => {
  const sessionId = req.headers["mcp-session-id"] as string;
  if (!sessionId) {
    const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
    transports[transport.sessionId] = transport;
    await server.connect(transport);
    transport.onmessage = (message) => transport.send(message);
  }
  // ... route the request to the session's transport
});
```

(Full runnable version in `implementations/typescript-sdk`.)

## Industry-standard pattern

- **stdio ↔ HTTP duality** mirrors how developer tools ship: LSP (same duality),
  language servers, `git` over pipes vs. over HTTP. Local-first, remote-when-needed is
  a proven product pattern.
- **HTTP transport** follows standard web practice: TLS everywhere, keep-alive, load
  balancing, health checks, structured error responses — nothing MCP-specific about
  that layer (see [11-communication-transport/http.md](../11-communication-transport/http.md)).
- **Reverse-proxy termination** (TLS + compression + routing at the edge) is the
  industry norm for production MCP servers; see
  [10-scaling-performance/load-balancing.md](../10-scaling-performance/load-balancing.md).

## Common mistakes

- **Writing protocol frames to stderr** (or logs to stdout) on stdio — corrupts the
  protocol and mysteriously breaks the client.
- **Forgetting `Accept: application/json, text/event-stream`** on Streamable HTTP →
  `406` responses.
- **Dropping `Mcp-Session-Id`** on HTTP — the server can't correlate requests, and
  session state is lost (session-based spec).
- **Running Streamable HTTP without TLS in production** — credentials and tool data in
  plaintext.
- **Assuming stdio implies a shared server.** One client per process: if you need
  multiple clients against one stateful server, use HTTP.

## Testing

- **Transport matrix**: run the same server over stdio and Streamable HTTP and assert
  identical behavior (see [15-testing/compatibility-testing.md](../15-testing/compatibility-testing.md)).
- **stdio tests**: spawn the server process in a test, drive JSON-RPC over pipes,
  assert responses and that stderr stays clean (the lab projects do this:
  `repository/go`, `repository/rust`).
- **HTTP tests**: assert status codes, `Mcp-Session-Id` handling, SSE framing, and
  `406` on missing `Accept`.
- **TLS tests**: connect with a self-signed cert in CI and assert verification
  succeeds/fails as configured.

## Debugging

- For stdio: **watch stderr** — it's the server's only voice. Add logging there and run
  the server manually, feeding it a recorded request (see
  [07-inspector-debugging/transport-debugging.md](../07-inspector-debugging/transport-debugging.md)).
- For HTTP: inspect headers first (`Mcp-Session-Id`, `Accept`, status codes), then the
  body. Use `curl -N` to watch SSE streams.
- MCP Inspector speaks both transports and shows you the raw bytes — start there before
  writing your own harness.

## Security considerations

- **stdio = full trust.** The server runs as your user with your permissions and can
  read your files. Only spawn servers you trust, with a restricted environment
  ([14-security/authentication.md](../14-security/authentication.md)).
- **HTTP = full distrust.** Assume every request is from an attacker: TLS, auth,
  rate limiting, and input validation (see [14-security/README.md](../14-security/README.md)).
- **Session IDs are bearer tokens** in the session-based spec: keep them secret, rotate
  them, and tie them to the authenticated identity.
- TLS only protects *in transit*; the server still needs authorization at the
  application layer.

## Related concepts

- [01-client-server.md](01-client-server.md)
- [09-sessions-and-lifecycle.md](09-sessions-and-lifecycle.md)
- [11-communication-transport/http.md](../11-communication-transport/http.md)
- [11-communication-transport/tls.md](../11-communication-transport/tls.md)
- [10-scaling-performance/README.md](../10-scaling-performance/README.md)
- [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)
