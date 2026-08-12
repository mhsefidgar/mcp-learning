# 07 — Version Negotiation

## What is it?

Version negotiation is the part of initialization where client and server agree on
**which protocol version** to speak for the rest of the connection. The client proposes
the newest version it understands; the server replies with the version it wants to use
— and per the session-based spec, **the server's reply wins**.

```
Client sends:  protocolVersion: "2025-11-25"   (newest the client supports)
Server replies: protocolVersion: "2025-11-25"  (server's choice; may be older)
```

## Why does MCP need it?

Protocols evolve, and not every client and server upgrade at the same time. A
production fleet will contain servers speaking 2024, 2025, and 2026 dialects
simultaneously. Version negotiation lets a new client talk to an old server (and vice
versa) instead of failing hard. It is the difference between "upgrade everything in
lockstep" and "deploy at your own pace".

## How does it work?

1. The client sends `initialize` with the **newest** `protocolVersion` it supports.
2. The server looks at the client's version and picks the version it will speak:
   - If the server supports that version → echoes it.
   - If not → picks the newest version *it* supports that is **older than or equal to**
     the client's (the intersection of the two version sets).
3. The client checks the server's choice: if it's a version the client also supports,
   the session proceeds; if not, the client **must fail** (it cannot downgrade below
   its own minimum).
4. Both sides then behave per the agreed version — message shapes, deprecations, and
   defaults all follow that version.

Version strings look like dates: `2024-11-05`, `2025-03-26`, `2025-06-18`,
`2025-11-25`, `2026-07-28`. There is no semver — the "version" *is* the release date.

## Mental model

Two people who speak different dialects of the same language agree to speak **the older
dialect** — the one both actually know. The younger speaker offers their newest
dialect; the older speaker says "I can only do X"; if X is something the younger
speaker also knows, they proceed in X. If the younger speaker *doesn't* know X (the
gap is too big), they politely part ways.

## MCP-specific behavior

- **The server chooses; the client must accept or abort.** This asymmetry avoids a
  race where both sides pick different versions. (The 2026-07-28 stateless spec
  changes this: every request carries its own `MCP-Protocol-Version` header — see
  [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md).)
- **Version numbers are dates, and ordering is chronological.**
- **Negotiated version ≠ SDK version.** FastMCP 3.4.x can negotiate to an older
  protocol version when talking to an older server.
- SDKs handle negotiation for you, but they expose the *result*: FastMCP's `Client`
  records `server_protocol_version`; the TS SDK's `Client.getServerVersion()` returns
  the server's `protocolVersion`.

## Example

A 2026-era client talking to an older server:

```json
// client → server
{"jsonrpc":"2.0","id":1,"method":"initialize",
 "params":{"protocolVersion":"2025-11-25",
           "capabilities":{},
           "clientInfo":{"name":"modern-client","version":"2.0"}}}

// server → client — server only knows 2025-06-18, steps down
{"jsonrpc":"2.0","id":1,
 "result":{"protocolVersion":"2025-06-18",
           "capabilities":{"tools":{}},
           "serverInfo":{"name":"legacy-server","version":"1.0"}}}
```

The client accepts `2025-06-18` (it supports it) and the session proceeds under the
older rules.

**In FastMCP**, you mostly see this indirectly, but you can pin behavior:

```python
from fastmcp import Client

async def main() -> None:
    async with Client("python server.py") as client:
        # Which protocol version did we actually agree on?
        print(client.server_protocol_version)  # e.g. "2025-11-25"

import asyncio; asyncio.run(main())
```

**In the TypeScript SDK:**

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";

const client = new Client({ name: "x", version: "1.0" });
// after connect():
const serverVersion = client.getServerVersion();
console.log(serverVersion?.protocolVersion); // e.g. "2025-11-25"
```

## Industry-standard pattern

Version negotiation is universal: **HTTP** (`Accept`/`Content-Type` + `Upgrade`),
**TLS** (version + cipher negotiation), **SSH** (version strings), **gRPC** (content
types), **Kubernetes** (API versioning). The general principles — offer the newest,
accept the oldest common, fail cleanly on no intersection — are the same everywhere;
MCP just makes the whole thing two JSON fields.

## Common mistakes

- **Hard-coding the version instead of negotiating** — you lose the ability to talk to
  older peers and get confusing failures when you deploy an upgrade.
- **Client blindly accepting the server's version** even when it's newer than the
  client supports. The server can only choose from versions *the client offered*; if a
  broken server responds with something else, the client must abort, not proceed.
- **Confusing protocol version with SDK/library version** when filing bugs.
- **Forgetting that deprecations follow the negotiated version** — a 2026 client on a
  2025 server must still honor 2025 behavior (e.g. the deprecated roots/sampling
  messages may still arrive).

## Testing

- **Version matrix tests**: connect every client version against every server version
  you support and assert the negotiated result (see
  [15-testing/compatibility-testing.md](../15-testing/compatibility-testing.md)).
- **Downgrade tests**: assert that a newer client correctly steps down and that
  behavior matches the older version (e.g. no `2026-07-28`-only features).
- **Rejection tests**: client supports only `2025-11-25`, server only `2026-07-28` →
  assert a clean failure, not a hang or garbage.

## Debugging

- The negotiated version is visible in Inspector's initialization panel and in the
  raw `initialize` exchange. When weird behavior appears after an SDK upgrade, check
  the negotiated version *first* — you may be running old-protocol behavior.
- On HTTP transports, version mismatches sometimes surface as transport errors (wrong
  header handling) — see [07-inspector-debugging/transport-debugging.md](../07-inspector-debugging/transport-debugging.md).

## Security considerations

- **Negotiation is not a security boundary.** An attacker who can spoof the handshake
  can claim an old version and disable your newer security features. Combine
  negotiation with real authentication on remote transports
  ([14-security/authentication.md](../14-security/authentication.md)).
- Beware of **downgrade attacks** where a MITM forces both sides to an old version:
  on remote transports, authenticate before trusting the negotiated result.

## Related concepts

- [05-initialization.md](05-initialization.md)
- [06-capabilities.md](06-capabilities.md)
- [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)
- [13-versioning/compatibility.md](../13-versioning/compatibility.md)
- [15-testing/compatibility-testing.md](../15-testing/compatibility-testing.md)
