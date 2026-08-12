# 05 — Capability Routing

## What is it?

**Capability routing** is the rule that a method is only *routable* if the receiving
side declared the matching capability during initialization
([01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)). It's a
gate *in front of* the dispatch table: `resources/*` requests are not just "not
handled" — they are *not supposed to arrive* if the server never declared resources.

## Why does MCP need it?

Capabilities are how peers avoid stepping on each other. Capability routing turns the
declaration into enforcement:

- The **client** must not call methods in undeclared namespaces.
- The **server** should reject them anyway (defense in depth): a request for an
  undeclared capability is a protocol violation, likely a buggy client — or an
  attacker probing.

## How does it work?

1. During initialization both sides record the other's capability map.
2. At dispatch time, the method's namespace is checked against the *declared*
   capabilities *of the side that would handle it*:
   - Client side: don't send `resources/read` to a server that declared no
     `resources`.
   - Server side: if a `resources/*` request arrives but the server declared no
     `resources` capability, answer with a "method not found / not supported" error.
3. Sub-features are gated the same way: only send `resources/subscribe` if the server
   declared `resources.subscribe`; only expect change notifications if `listChanged`
   was declared.

## Mental model

Capability routing is a **feature-flag gate at the router**: "this route exists only
if the feature flag is on." The flags come from the handshake, not from config — they
are *negotiated per connection*.

## MCP-specific behavior

- **This is protocol behavior.** The spec defines the capability namespaces and says
  peers must not use undeclared ones. SDKs enforce the client side for you (FastMCP's
  `Client` won't call `resources/*` on a tool-only server) and give you hooks for the
  server side.
- **Optional features**: every capability *except* the core three (tools, resources,
  prompts) is optional. A client must work with any subset.
- **Server→client capabilities** (sampling, roots, elicitation) are gated on the
  *client's* declarations — a server must not call `sampling/createMessage` on a
  client that never declared `sampling`.
- In the **2026-07-28 stateless spec**, capability information moves per-request
  (`_meta`), so capability routing becomes per-request too
  ([13-versioning/capability-negotiation.md](../13-versioning/capability-negotiation.md)).

## Example

Server-side rejection of an undeclared namespace (conceptual — SDKs do this in their
protocol layer):

```python
# FastMCP: registering nothing under resources means the server declares no
# resources capability, and resources/* requests fail cleanly. You can verify
# with Inspector: the initialize response will contain no "resources" key.
from fastmcp import FastMCP

mcp = FastMCP("tools-only")

@mcp.tool
def ping() -> str:
    """A single tool; no resources, no prompts."""
    return "pong"
```

Client-side gating in the TypeScript SDK:

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
// ...
const serverCaps = client.getServerCapabilities();
if (serverCaps?.resources) {
  const resources = await client.listResources();
} else {
  console.log("server declares no resources — skipping resources/* calls");
}
```

## Industry-standard pattern

Negotiated feature gates appear in **HTTP (Accept/OPTIONS, feature detection)** and
**TLS (extension negotiation)**. The specific lesson: *enforce at both ends*. The
declaring side must honor its declaration; the consuming side must not rely on
undeclared features.

## Common mistakes

- **Calling undeclared methods and treating the error as a bug in the server.**
- **Declaring a capability but not implementing all its methods** — e.g. declaring
  `resources` but having no `resources/read` handler.
- **Hard-coding the peer's capabilities** instead of reading the handshake — breaks
  the moment the peer changes.
- **Forgetting sub-flags** (`subscribe`, `listChanged`) in both declaration and use.

## Testing

- **Discovery tests**: assert the client's view of server capabilities
  ([15-testing/capability-testing.md](../15-testing/capability-testing.md)).
- **Gate tests**: for each undeclared namespace, assert the server rejects the method
  with the defined error.
- **Sub-flag tests**: subscribe/listChanged behavior flips with the declaration.
- **Client discipline tests**: a client that respects capabilities never sends
  undeclared methods (test by recording outbound messages).

## Debugging

- An unexplained "method not found" for a method you *know* you implemented is almost
  always a capability gate: check the initialize response's capability map in
  Inspector before looking at the handler.
- If the client never calls your `resources/subscribe`, the server probably didn't
  declare `resources.subscribe`.

## Security considerations

- **Capability gating is a free authorization layer**: an undeclared namespace is
  unreachable by design. Keep declarations minimal.
- **It is not sufficient authorization** — see
  [08-authorization-routing.md](08-authorization-routing.md).

## Related concepts

- [01-request-dispatch.md](01-request-dispatch.md)
- [01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)
- [13-versioning/capability-negotiation.md](../13-versioning/capability-negotiation.md)
- [15-testing/capability-testing.md](../15-testing/capability-testing.md)