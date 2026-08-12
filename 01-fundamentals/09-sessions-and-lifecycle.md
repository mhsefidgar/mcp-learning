# 09 — Sessions and Lifecycle

> **Protocol era note.** Sessions exist in the session-based protocol (**2025-11-25**).
> The **2026-07-28** stateless spec removes the protocol-level session. This document
> is essential for understanding the current SDKs *and* for understanding what changed.

## What is it?

A **session** is a logical, stateful connection between one client and one server that
persists across many messages. In the session-based protocol it is identified by the
**`Mcp-Session-Id`** header (HTTP) or implicitly by the process (stdio). The
**lifecycle** is the session's arc: connect → initialize → operate → close.

```
┌──────────┐   ┌──────────┐   ┌───────────────────────┐   ┌─────────┐
│ CONNECT  │ → │INITIALIZE│ → │       OPERATE         │ → │  CLOSE  │
│ transport│   │ handshake│   │ tools/resources/prompts│   │ shutdown│
└──────────┘   └──────────┘   │ + server→client reqs  │   └─────────┘
                              └───────────────────────┘
```

## Why does MCP need it?

The session is the *container* that makes MCP's bidirectional features possible in the
session-based protocol:

- The server can hold a request open while it asks the client for input (sampling,
  elicitation, roots).
- The server can push notifications (progress, log messages, resource updates) at any
  time.
- Both sides can correlate state: "this client called tool X, then tool Y" belongs to
  one logical conversation.

Without a session, all of those would need re-invention over stateless HTTP. (The
2026-07-28 spec *did* re-invent them via MRTR — see
[13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md).)

## How does it work?

1. **Connect**: the client establishes the transport (spawns the process / opens HTTP).
2. **Initialize**: the handshake ([05-initialization.md](05-initialization.md)) creates
   the session. On HTTP, the server issues `Mcp-Session-Id`; the client echoes it on
   every subsequent request.
3. **Operate**: requests, responses, notifications flow; either side may hold a channel
   open (HTTP: the SSE stream) to push messages.
4. **Close**: either side may terminate:
   - The client stops sending / closes the connection.
   - The server closes the connection.
   - Either side's process/connection dies (crash, timeout, network drop).
5. **Cleanup**: both sides release resources (cancelled tasks, closed connections,
   flushed logs). Graceful shutdown is a *best effort* — see below.

**Graceful shutdown** (general engineering, not an MCP method): on SIGTERM or an
explicit close, the server should (a) stop accepting new work, (b) let in-flight
operations finish or cancel within a deadline, (c) flush logs/metrics, (d) exit
cleanly. The MCP protocol has no `shutdown` method in the stable spec — shutdown is a
transport/process concern (the 2026-07-28 spec's Tasks extension adds `tasks/update`
for long-running work, and graceful shutdown remains an application concern).

## Mental model

A session is a **phone call**; the lifecycle is "dial → greeting → conversation →
hang up". In the stateless future it becomes a **mail correspondence**: each letter
carries enough context to stand alone, and the "call" features (asking a question
mid-call) are done by sending a letter that says "I need more info" and getting a
follow-up letter (MRTR).

## MCP-specific behavior

- **`Mcp-Session-Id`** (HTTP transport): opaque server-issued token; required on
  subsequent requests in the session-based spec; must be kept secret.
- **Session state lives on the server.** The client holds the ID; the server holds the
  state (subscriptions, progress tokens, in-flight server→client requests).
- **One session per stdio process.** stdio sessions are implicit — the process *is*
  the session.
- **Session timeout / recovery**: if a server drops a session, the client should
  re-initialize a new one (that's *application* logic; see
  [08-reliability-resilience/session-recovery.md](../08-reliability-resilience/session-recovery.md)).
- **No `shutdown` method** in the stable spec; close is transport-level. FastMCP
  exposes lifecycle hooks (`lifespan`) so you can clean up on start/stop — that's a
  framework feature, not a protocol one.

## Example

FastMCP lifespan hooks for graceful startup/shutdown:

```python
from contextlib import asynccontextmanager
from fastmcp import FastMCP

@asynccontextmanager
async def lifespan(server: FastMCP):
    # startup: open the shared database connection
    db = await connect_to_db()
    server.state.db = db
    try:
        yield
    finally:
        # shutdown: close it, flush logs, cancel workers
        await db.close()

mcp = FastMCP("orders", lifespan=lifespan)
```

TypeScript SDK close:

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
// ...
await client.close();  // sends close, releases transport resources
```

## Industry-standard pattern

Session lifecycle is the oldest pattern in networking: **TCP** (handshake → data →
FIN), **HTTP cookies/sessions**, **SSH**, **database connections**. The engineering
lessons carry over directly: sessions need timeouts, must be recoverable, and must be
scoped to an authenticated identity (see
[10-scaling-performance/session-affinity.md](../10-scaling-performance/session-affinity.md)
for why sessions complicate scaling).

## Common mistakes

- **Leaking sessions**: never closing the client/transport on shutdown (tests and CI
  hang).
- **Assuming sessions survive restarts.** A server restart invalidates all sessions;
  clients must re-initialize (see [08-reliability-resilience/session-recovery.md](../08-reliability-resilience/session-recovery.md)).
- **Storing secrets in session state** — session state is server memory, often
  serialized or logged; keep it minimal.
- **Graceful-shutdown misses**: not cancelling in-flight tool calls on shutdown, so the
  process hangs for minutes. Give shutdown a deadline.
- **Treating the session as an identity boundary** — `Mcp-Session-Id` identifies a
  *connection*, not a *user*. Authentication is separate
  ([14-security/authentication.md](../14-security/authentication.md)).

## Testing

- **Lifecycle tests**: connect → assert initialized; close → assert both sides
  released resources (no dangling sockets/processes).
- **Graceful shutdown tests**: start a long tool call, send shutdown, assert the call
  is cancelled *or* completes within the deadline and the process exits 0
  ([15-testing/failure-testing.md](../15-testing/failure-testing.md)).
- **Session-loss tests**: kill the server process; assert the client detects it and
  can re-initialize ([08-reliability-resilience/session-recovery.md](../08-reliability-resilience/session-recovery.md)).

## Debugging

- "Works the first time, fails the second" is almost always a **session problem**:
  check whether the second connection reused a dead session ID.
- On HTTP, a `404`/`400` for "unknown session" means the server lost the session — look
  at server restarts, timeouts, and load-balancer routing
  ([07-inspector-debugging/transport-debugging.md](../07-inspector-debugging/transport-debugging.md)).
- Check for **zombie processes**: every abandoned stdio client should have killed its
  server.

## Security considerations

- **Session IDs are bearer tokens**: they grant access to the session's capabilities.
  Use TLS (so they're not sniffed), rotate on privilege change, and tie them to the
  authenticated user ([14-security/authentication.md](../14-security/authentication.md)).
- **Session fixation / hijacking** are the classic attacks — never accept a
  client-chosen session ID; always issue your own.
- On shutdown, **purge session state** (don't leave sensitive data in memory longer
  than needed).

## Related concepts

- [05-initialization.md](05-initialization.md)
- [08-transports.md](08-transports.md)
- [08-reliability-resilience/session-recovery.md](../08-reliability-resilience/session-recovery.md)
- [10-scaling-performance/session-affinity.md](../10-scaling-performance/session-affinity.md)
- [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)
