# 03 — MCP Routing & Dispatch

**What this section teaches.** How an incoming MCP request becomes an executed
operation: the dispatch table, tool/resource/prompt routing, capability-aware routing,
provider routing (which source supplies a component), transforms, authorization-aware
routing, version-aware routing, error routing, middleware, and remote/proxy routing.
After this section you can design a server that stays correct as it grows from one tool
to a composed multi-provider system.

**Prerequisites.** [01-fundamentals](../01-fundamentals/README.md),
[02-primitives](../02-primitives/README.md).

**Recommended reading order:**

1. [01-request-dispatch.md](01-request-dispatch.md) — the central dispatch table
2. [02-tool-routing.md](02-tool-routing.md) · [03-resource-routing.md](03-resource-routing.md) · [04-prompt-routing.md](04-prompt-routing.md) — routing per primitive
3. [05-capability-routing.md](05-capability-routing.md) — gate by declared capabilities
4. [06-provider-routing.md](06-provider-routing.md) — *which source* supplies a component
5. [07-transform-routing.md](07-transform-routing.md) — rename/filter/namespace on the way out
6. [08-authorization-routing.md](08-authorization-routing.md) — who may call what
7. [09-version-aware-routing.md](09-version-aware-routing.md) — v1 vs v2 implementations
8. [10-error-routing.md](10-error-routing.md) — every failure mode mapped to a response
9. [11-middleware-routing.md](11-middleware-routing.md) — before/during/after dispatch
10. [12-remote-proxy-routing.md](12-remote-proxy-routing.md) — forward to a remote server

**Relevant examples:** `examples/` — a dispatch-table walkthrough and a composed
multi-provider FastMCP server.

**Relevant implementations:** `implementations/python-fastmcp`, `repository/go/routing`,
`repository/rust/routing`.

**Exercises.**

1. **Trace the dispatch** of these requests through your own mental table: `tools/call`
   for an unknown tool, `resources/read` for an unknown URI, `prompts/get` for a prompt
   whose argument is missing. *Acceptance:* you predict each error code before running
   it against `examples/` (see [10-error-routing.md](10-error-routing.md)).
2. **Namespace collision**: mount two FastMCP servers that both define a tool called
   `search`. *Acceptance:* with `namespace="api"`, the client sees `api_search` and
   `api2_search`, and calls route to the right handler.
3. **Authorization gate**: protect a `delete_*` tool so only a client presenting a
   valid token may call it. *Acceptance:* an unauthenticated `tools/call` for
   `delete_order` returns the unauthorized error, while `list_orders` still works
   ([08-authorization-routing.md](08-authorization-routing.md)).

**Common mistakes in this section**

- **Dispatch on strings you don't control** (e.g. `getattr(server, method)`) — a
  malicious `method` could reach unintended code. Always dispatch through a fixed map.
- **Ignoring capability gates** — routing `resources/*` on a server that never declared
  the resource capability.
- **Name collisions** when composing servers, fixed by namespacing
  ([06-provider-routing.md](06-provider-routing.md), [07-transform-routing.md](07-transform-routing.md)).
- **Performing authorization *after* dispatch** — the handler already ran.
- **Forgetting error routing** — every unknown method/name/URI needs a defined response
  ([10-error-routing.md](10-error-routing.md)).