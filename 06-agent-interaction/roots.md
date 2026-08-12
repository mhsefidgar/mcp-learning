# Roots

> **Deprecation note.** Roots are **deprecated** in the 2026-07-28 spec (≥12-month
> window). You'll meet them in existing servers; new designs should prefer explicit
> context (tools/resources) or elicitation.

## What is it?

**Roots** are the client telling the server about its **context**: filesystem
directories or URI prefixes the client considers relevant. The client declares a
`roots` capability; the server can call `roots/list` to see them.

```
client declares: capabilities.roots = {listChanged: true}
server ──► client  roots/list
client ──► server  {roots: [{uri: "file:///Users/me/projects/app", name: "app"}]}
```

## Why does MCP need it?

It's the mirror image of resources: resources are *server* data made visible to the
client; roots are *client* data made visible to the server. A filesystem server
could use roots to know *which* directories matter to the current user, instead of
scanning everything. In practice, adoption was low (most servers take explicit paths
in tool arguments), which is partly why it was deprecated.

## How does it work?

1. The **client declares `roots`** (and optionally `listChanged`).
2. The server calls `roots/list` (server→client request).
3. The client returns its roots — each a `uri` plus optional `name`.
4. If `listChanged`, the client sends `notifications/roots/list_changed` when roots
   change; the server re-lists.

## Mental model

Roots are the client saying **"these are my files/places — work within them."** Like
giving a contractor the keys to the *rooms* they may work in, rather than the whole
building. The server should treat roots as a *suggestion of scope*, not a security
boundary.

## MCP-specific behavior

- **Protocol-defined, client-gated, server-initiated** — only if the client declares
  `roots`.
- **Deprecated in 2026-07-28** (SEP-2577): the modern spec has no channel for this
  server-initiated client-data request; the FastMCP guidance is to ask for roots via
  the same guard/elicitation pattern, or take paths as tool arguments.
- **Roots are not permissions** — they express relevance, not authorization.

## Example

A server that uses roots (session-based protocol, educational — 2025-era behavior):

```python
# FastMCP does not expose roots/list as a first-class server API in 3.x on all
# transports; the conceptual flow (historical) is:
#
#   if client declared roots:
#       result = await ctx.session.list_roots()   # server → client request
#       roots = result.roots                       # [Root(uri=..., name=...)]
#       # use roots to scope file operations
```

Where this still matters: **clients** declaring roots for legacy servers:

```typescript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
const client = new Client(
  { name: "app", version: "1.0" },
  { capabilities: { roots: { listChanged: true } } }
);
// client.setRoots([{ uri: "file:///Users/me/app", name: "app" }]);
```

## Industry-standard pattern

"Scope hints from the caller" is common (working directories, `git rev-parse
--show-toplevel`, IDE workspace folders). The lesson: scope hints are *hints* —
validate them server-side and never treat them as a security boundary.

## Common mistakes

- **Treating roots as authorization** — a server that limits itself to roots but
  doesn't enforce real permissions is vulnerable to a malicious client.
- **Requiring roots** — most clients never declare them; servers must work without.
- **Building new features on roots** — it's deprecated; prefer explicit arguments.

## Testing

- **Capability tests**: roots are only fetched when the client declares the
  capability.
- **Fallback tests**: no roots declared → the server works with explicit paths.
- **listChanged tests**: root changes trigger a re-list (legacy clients).

## Debugging

- "The server doesn't know my workspace" → the client didn't declare/attach roots;
  check the handshake capabilities.

## Security considerations

- **Roots reveal the client's file layout** to the server — a privacy disclosure;
  clients should share the minimum.
- **Never trust roots as a sandbox** — a malicious server ignores them entirely.

## Related concepts

- [sampling.md](sampling.md) — the other deprecated client capability
- [elicitation.md](elicitation.md) — the modern interactive mechanism
- [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)
- [14-security/README.md](../14-security/README.md)