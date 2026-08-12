# 05 — Initialization

> **Protocol era note.** This document describes initialization in the session-based
> protocol (**2025-11-25**), which is what current stable SDKs implement. The
> **2026-07-28** stateless spec removes this handshake entirely — see
> [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md).

## What is it?

Initialization is the **opening handshake** of an MCP connection: before any
`tools/call` or `resources/read` happens, client and server introduce themselves,
agree on a protocol version, and declare their capabilities. It consists of exactly two
messages (a request/response pair) followed by one notification:

```
Client                           Server
  │  initialize (request)          │
  │ ─────────────────────────────► │
  │                                │
  │  initialize (result)           │
  │ ◄───────────────────────────── │
  │                                │
  │  notifications/initialized     │
  │ ─────────────────────────────► │
  │                                │
  │  ... normal operation ...      │
```

## Why does MCP need it?

Two reasons:

1. **Version compatibility.** A client built in 2025 must not silently assume a server
   built in 2026 speaks the same dialect. Initialization is where both sides find a
   protocol version they share (see [07-version-negotiation.md](07-version-negotiation.md)).
2. **Capability awareness.** The client needs to know *before it tries* whether the
   server supports tools, resources, prompts, or sampling — otherwise it would call
   `resources/read` on a tool-only server and get errors. Initialization declares this
   up front.

## How does it work?

1. **Client sends `initialize`** with:
   - `protocolVersion` — the newest spec version the client supports
   - `capabilities` — what the *client* can do (e.g. `{"sampling": {}, "roots": {...}}`)
   - `clientInfo` — `{name, version}` for identification
2. **Server responds** with:
   - `protocolVersion` — the version both sides will use (the *older* of the two
     preferred versions; see [07-version-negotiation.md](07-version-negotiation.md))
   - `capabilities` — what the *server* can do (e.g. `{"tools": {"listChanged": true},
     "resources": {...}, "prompts": {...}}`)
   - `serverInfo` — `{name, version}`
   - optionally `instructions` — free-text guidance for the client/model
3. **Client sends `notifications/initialized`** — "I've seen your capabilities; we're
   live."
4. Only *after* `notifications/initialized` may either side send operational requests.
   (Some implementations are lenient; the spec requires the handshake.)

## Mental model

Initialization is a **first date**: you state your name, you ask what the other person
can do, you agree on a language you both speak (version), and only then do you start
doing things together. Skipping it is like assuming a stranger speaks your dialect —
sometimes it works, sometimes you get nonsense.

## MCP-specific behavior

- **It's protocol-level, not SDK-level.** FastMCP's `mcp.run()`, the TS SDK's
  `server.connect(transport)`, and the Java SDK's `McpClient.sync(transport)` all
  perform the handshake for you — but the messages are real and visible in Inspector.
- **Order matters.** `initialize` must be the first message a client sends. A server
  receiving `tools/list` before `initialize` should respond with an error.
- **`clientInfo`/`serverInfo` are structured**: `{name, version}` — useful for
  server-side metrics ("which client versions are calling us?").
- **`instructions`** (server→client) is a great place for server-specific guidance
  ("this server only exposes read-only tools").
- **Capabilities are declarative, not imperative**: declaring `tools` means "you may
  call tools/*", not "I have these specific tools". The specific list comes from
  `tools/list`.

## Example

The raw exchange (see [03-json-rpc.md](03-json-rpc.md) for field details):

```json
// client → server
{"jsonrpc":"2.0","id":1,"method":"initialize",
 "params":{"protocolVersion":"2025-11-25",
           "capabilities":{"sampling":{}},
           "clientInfo":{"name":"my-agent","version":"0.4.1"}}}

// server → client
{"jsonrpc":"2.0","id":1,
 "result":{"protocolVersion":"2025-11-25",
           "capabilities":{"tools":{},"resources":{},"prompts":{}},
           "serverInfo":{"name":"filesystem","version":"2.0.0"},
           "instructions":"Read-only access to /data."}}

// client → server (notification, no id)
{"jsonrpc":"2.0","method":"notifications/initialized"}
```

In **FastMCP** you never write this — but you can *see* it:

```python
from fastmcp import FastMCP
mcp = FastMCP("demo")
# mcp.run() performs initialize/initialized automatically over stdio or HTTP
```

In the **TypeScript SDK**, the same is true:

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const client = new Client({ name: "my-agent", version: "0.4.1" });
await client.connect(new StdioClientTransport({ command: "python", args: ["server.py"] }));
// connect() performs initialize + notifications/initialized
```

In the **Java SDK**:

```java
var transport = new StdioServerTransport(new ProcessBuilder("python", "server.py").start());
McpSyncClient client = McpClient.sync(transport);
// client.initialize() runs the handshake
```

## Industry-standard pattern

Handshakes with version + capability negotiation are the norm in protocols that
outlive their first release: **HTTP/2's SETTINGS + ALPN**, **WebSocket's opening
handshake**, **SSH's version exchange**, **TLS's ClientHello/ServerHello**. MCP's
handshake is deliberately tiny compared to TLS — its job is just *agreement*, not
security (security comes from the transport, see [14-security/authentication.md](../14-security/authentication.md)).

## Common mistakes

- **Sending operational requests before `notifications/initialized`.** The server may
  reject them.
- **Forgetting to negotiate version** and just sending `2025-11-25` — if the server
  supports an older version, the client must be willing to step down
  ([07-version-negotiation.md](07-version-negotiation.md)).
- **Declaring capabilities you don't implement.** If you declare `resources` but have
  no `resources/list` handler, clients will fail confusingly.
- **Putting per-tool info in the handshake** — capabilities are feature *categories*,
  not inventories.

## Testing

- **Capability discovery tests**: after connecting, assert the client learned the
  server's capabilities correctly ([15-testing/capability-testing.md](../15-testing/capability-testing.md)).
- **Version matrix tests**: connect with a client that supports only an older version
  and assert the negotiated version ([15-testing/compatibility-testing.md](../15-testing/compatibility-testing.md)).
- **Malformed-handshake tests**: send `initialize` with a bad `protocolVersion` and
  assert a clean error, not a hang.
- The SDK test suites in `implementations/` include these.

## Debugging

- **MCP Inspector shows the whole handshake** — the most common "can't connect"
  failures (wrong version, unexpected capability shape) are visible in the first two
  messages (see [07-inspector-debugging/initialization-debugging.md](../07-inspector-debugging/initialization-debugging.md)).
- If a handshake fails on HTTP, check the transport-level headers and status codes
  before the JSON (see [07-inspector-debugging/transport-debugging.md](../07-inspector-debugging/transport-debugging.md)).
- Log `clientInfo`/`serverInfo` on both sides; a mismatch in names is often the clue
  that two different servers are in play.

## Security considerations

- **The handshake is not authentication.** Anyone can say `clientInfo: {"name": "admin"}`.
  Real identity comes from transport security (TLS + OAuth for HTTP)
  ([14-security/authentication.md](../14-security/authentication.md)).
- **Declared capabilities constrain attack surface**: a server that declares no
  `resources` capability should refuse `resources/*` requests — that's a free
  authorization layer.
- Never put secrets in `clientInfo` or `instructions`.

## Related concepts

- [06-capabilities.md](06-capabilities.md)
- [07-version-negotiation.md](07-version-negotiation.md)
- [09-sessions-and-lifecycle.md](09-sessions-and-lifecycle.md)
- [07-inspector-debugging/initialization-debugging.md](../07-inspector-debugging/initialization-debugging.md)
- [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)
