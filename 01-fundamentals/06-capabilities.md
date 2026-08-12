# 06 — Capabilities

## What is it?

A **capability** is a feature category that a client or server declares during
initialization. Client capabilities describe what the *client* can do *for* the server
(sampling, roots, elicitation); server capabilities describe what the *server* offers
(tools, resources, prompts, logging).

```
Client declares:                     Server declares:
{ "sampling": {},                    { "tools":     {"listChanged": true},
  "roots":    {"listChanged": true},   "resources": {"subscribe": true,
  "elicitation": {}                    "listChanged": true},
                                     "prompts":    {},
                                     "logging":    {} }
```

## Why does MCP need it?

Capabilities are how MCP stays **extensible without breaking**: a client from 2025 and
a server from 2026 can still talk, because each side only *uses* what the other side
declared. Without capabilities, every feature would have to be assumed present, and any
new feature would break every old peer. Capabilities are the protocol's "feature flags
on the wire".

## How does it work?

1. During `initialize` ([05-initialization.md](05-initialization.md)), each side sends
   its capability map in `params.capabilities` / `result.capabilities`.
2. Each side **reads the other's map** and records what is available.
3. During operation, each side **only invokes methods inside declared capability
   namespaces**: if the server didn't declare `prompts`, the client won't call
   `prompts/list`.
4. Some capabilities carry **sub-flags**: e.g. `tools.listChanged: true` means the
   server will send `notifications/tools/list_changed` when its tool list changes.

The rule is simple: **if it's not declared, don't call it; if it's declared, you must
honor it.**

## Mental model

Capabilities are a **résumé exchange**. Before collaborating, each side shows its
résumé: "I can do tools, resources, and logging." You then plan your work together
using only the skills on both résumés. If your partner never mentioned "sampling", you
don't ask them to sample — and if they *did* list it, they'd better actually be able to
do it.

## MCP-specific behavior

**Server capabilities** (what the server offers):

| Capability | What it enables |
|------------|-----------------|
| `tools` | `tools/list`, `tools/call`, `tools/list_changed` notification (if `listChanged`) |
| `resources` | `resources/list`, `resources/read`, `resources/templates/list`, `resources/subscribe` (if `subscribe`), `resources/updated` notification (if `listChanged`) |
| `prompts` | `prompts/list`, `prompts/get`, `prompts/list_changed` notification (if `listChanged`) |
| `logging` | `logging/setLevel` (client→server) and `notifications/message` (server→client) |
| `completions` | `completions/complete` (argument autocomplete for prompts/tools) |

**Client capabilities** (what the client offers):

| Capability | What it enables |
|------------|-----------------|
| `sampling` | server may call `sampling/createMessage` *(deprecated in 2026-07-28)* |
| `roots` | server may call `roots/list` *(deprecated in 2026-07-28)* |
| `elicitation` | server may use elicitation to request input mid-tool-call |
| `experimental.*` | extension namespaces (e.g. tasks) |

**What is *not* a capability:** retries, timeouts, caching, rate limiting, circuit
breakers — those are general engineering concerns, invisible to the protocol (see
[08-reliability-resilience/README.md](../08-reliability-resilience/README.md)).

## Example

A server that declares **read-only** tools and resources with change notifications:

```python
# FastMCP — capability declaration is handled by the framework based on
# what you register; you rarely touch the map yourself.
from fastmcp import FastMCP

mcp = FastMCP("readonly-data")
# Registering tools/resources/prompts automatically adds the matching
# capabilities to the initialize response.
```

You can inspect what your server actually declares by capturing the handshake in
Inspector, or by using the client-side view:

```python
import asyncio
from fastmcp import Client

async def main() -> None:
    async with Client("python server.py") as client:
        # FastMCP's Client exposes the server's capabilities from the handshake
        caps = client.server_capabilities
        print(caps)  # e.g. Capabilities(tools=..., resources=..., prompts=...)

asyncio.run(main())
```

In the **TypeScript SDK**, capabilities are part of the server config:

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

const server = new McpServer(
  { name: "demo", version: "1.0.0" },
  {
    capabilities: {
      tools: { listChanged: true },
      resources: { subscribe: true, listChanged: true },
      prompts: {},
    },
  }
);
```

In the **Java SDK**:

```java
var server = McpServer.sync(serverInfo)
    .capabilities(ServerCapabilities.builder()
        .tools(true)
        .resources(true, true)   // subscribe, listChanged
        .prompts(true)
        .build())
    .build();
```

## Industry-standard pattern

Capability/feature negotiation appears in **HTTP (Accept headers, feature detection)**,
**TLS (cipher suites)**, **WebRTC (codecs)**, and **CSS feature queries**. MCP's
version is unusually *coarse* (categories, not individual features) and *declarative*
(no probing) — the model then discovers the concrete inventory at runtime via
`*/list`.

## Common mistakes

- **Declaring more than you implement.** This is the #1 interop bug — a client will
  trust the declaration.
- **Forgetting that sub-flags matter.** Declaring `tools` but not `listChanged` means
  clients should *not* expect change notifications — and you must not send them.
- **Treating capabilities as static forever.** If your tool list can change, declare
  `listChanged` and send the notification when it does
  ([03-routing-dispatch/06-capability-routing.md](../03-routing-dispatch/06-capability-routing.md)).
- **Assuming the client's capabilities are available to the server in the stateless
  spec** — in 2026-07-28, client capabilities travel per-request in `_meta`, not once
  per session ([13-versioning/capability-negotiation.md](../13-versioning/capability-negotiation.md)).

## Testing

- **Capability discovery tests**: assert the client's view of server capabilities
  matches what the server declared ([15-testing/capability-testing.md](../15-testing/capability-testing.md)).
- **Negative tests**: a client must *not* call methods for undeclared capabilities —
  assert the server rejects them cleanly.
- **Sub-flag tests**: with `listChanged: false`, no change notifications arrive; flip
  it on and verify they do.
- The conformance suites in the SDK repos (e.g. the Java SDK's conformance-tests) do
  exactly this — borrow their scenarios.

## Debugging

- In Inspector, open the **initialization panel** and read the two capability maps
  before touching anything else. Most "method not found" or "not supported" errors are
  capability mismatches.
- If a client "doesn't see" a tool you registered, the server likely failed to declare
  the `tools` capability (or the tool was registered *after* the handshake without
  `listChanged`).

## Security considerations

- **Capabilities are an attack-surface statement.** Declaring fewer capabilities is a
  real security posture improvement: a server that declares no `resources` refuses
  `resources/*` by default.
- **Capabilities are not authorization.** Declaring `tools` does not mean every client
  may call every tool — that's [14-security/authorization.md](../14-security/authorization.md)'s
  job.
- **Experimental capabilities** (`experimental.*`) are by definition unstable: pin
  versions and treat them as untrusted interfaces.

## Related concepts

- [05-initialization.md](05-initialization.md)
- [07-version-negotiation.md](07-version-negotiation.md)
- [03-routing-dispatch/06-capability-routing.md](../03-routing-dispatch/06-capability-routing.md)
- [13-versioning/capability-negotiation.md](../13-versioning/capability-negotiation.md)
- [15-testing/capability-testing.md](../15-testing/capability-testing.md)
