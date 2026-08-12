# 01 — MCP Fundamentals

**What this section teaches.** The complete mental model of MCP: what a client and a
server are, how the protocol is structured (JSON-RPC over a transport), how a session
starts (initialization), what capabilities are, and how the two transports (stdio and
Streamable HTTP) work. After this section you can read a raw MCP message and know
exactly what is happening.

**Prerequisites.** Basic programming, JSON, and a little HTTP. No MCP knowledge needed.

**Recommended reading order:**

1. [01-client-server.md](01-client-server.md) — the big picture
2. [02-mcp-architecture.md](02-mcp-architecture.md) — where everything lives
3. [03-json-rpc.md](03-json-rpc.md) — the wire format
4. [04-requests-responses-notifications.md](04-requests-responses-notifications.md) — the three message kinds (incl. request IDs & error structure)
5. [05-initialization.md](05-initialization.md) — how sessions start
6. [06-capabilities.md](06-capabilities.md) — what each side can do
7. [07-version-negotiation.md](07-version-negotiation.md) — agreeing on a protocol version
8. [08-transports.md](08-transports.md) — stdio and Streamable HTTP (incl. TLS)
9. [09-sessions-and-lifecycle.md](09-sessions-and-lifecycle.md) — session state, graceful shutdown, health checks

> **Note on protocol eras.** These documents describe the session-based protocol
> (**2025-11-25**) that current stable SDKs implement. The new stateless revision
> (**2026-07-28**) is introduced in [08-transports.md](08-transports.md) and covered
> fully in [13-versioning/](../13-versioning/README.md). See
> [docs/VERSIONS.md](../docs/VERSIONS.md).

**Relevant examples:** `examples/` (raw JSON-RPC messages, a hand-rolled stdio exchange).

**Relevant implementations:**
- `implementations/python-fastmcp` — full FastMCP server + client
- `implementations/typescript-sdk` — full TS SDK server + client
- `repository/go/jsonrpc`, `repository/rust/jsonrpc` — from-scratch protocol cores

**Exercises.**

1. **Read a message.** Given the JSON-RPC example in
   [03-json-rpc.md](03-json-rpc.md), identify: the `id`, the `method`, the `params`,
   and whether it is a request or a notification. *Acceptance:* you can do this for all
   six example messages without looking at the answers.
2. **Hand-roll a stdio exchange.** Using the messages in
   [examples/stdio-exchange.md](examples/stdio-exchange.md), play client and server
   with a friend (or `nc`) over a pipe. *Acceptance:* you can complete an
   initialize → initialized → tools/list → tools/call sequence by hand.
3. **Trace initialization in FastMCP.** Run `implementations/python-fastmcp`'s server
   with `MCP_LOG_LEVEL=debug` and explain each line of the initialization handshake in
   your own words. *Acceptance:* you can name which message declares client info and
   which declares server info.

**Common mistakes to avoid in this section**

- Confusing **requests** (have an `id`, get a response) with **notifications** (no
  `id`, no response).
- Thinking MCP *defines* retries, timeouts, or circuit breakers — it does not; those
  are general engineering patterns you add (see [08-reliability-resilience](../08-reliability-resilience/README.md)).
- Assuming "the server" is always remote. The most common MCP server runs locally over
  **stdio** and is spawned by the client.
- Mixing up the two transports: stdio is *process-level* (pipes), Streamable HTTP is
  *network-level* (HTTP).
