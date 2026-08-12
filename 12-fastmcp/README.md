# 12 — FastMCP Architecture

**What this section teaches.** The architecture of **FastMCP** (the Python
framework, version 3.x) from the inside: the `FastMCP` object, **providers**
(where components come from), **transforms** (how they're modified), **middleware**
(the request pipeline), **context** (what handlers can do), **composition**
(mounting servers), and **proxying** (bridging remote servers).

**Prerequisites.** [01-fundamentals](../01-fundamentals/README.md),
[02-primitives](../02-primitives/README.md), [03-routing-dispatch](../03-routing-dispatch/README.md).

**Framing.** FastMCP is a *framework*, not the protocol. Everything here is
**SDK/framework behavior** — the wire protocol is unchanged. The docs distinguish
"FastMCP-specific" from "MCP protocol" throughout.

**Versions.** Written against **FastMCP 3.4.x** (verified). FastMCP 4.0 (beta)
implements the 2026-07-28 stateless protocol; the concepts (providers, transforms,
middleware) carry over. See [docs/VERSIONS.md](../docs/VERSIONS.md).

**Reading order:**

1. [fastmcp.md](fastmcp.md) — the core object and mental model
2. [providers.md](providers.md) — sources of components
3. [transforms.md](transforms.md) — modifying components
4. [middleware.md](middleware.md) — the request pipeline
5. [context.md](context.md) — what handlers can access
6. [composition.md](composition.md) — mounting servers
7. [proxying.md](proxying.md) — bridging remote servers

**Relevant examples:** `examples/` — a composed server with providers, transforms,
middleware, and context. **Relevant implementations:**
`implementations/python-fastmcp` (the full project), `capstone/python-server`.

**Exercises.**

1. **Trace the pipeline**: add logging + timing middleware to a server; explain the
   order in which they run for a `tools/call`
   ([middleware.md](middleware.md)).
2. **Namespace a mount**: mount a sub-server with `namespace=`; verify the
   client-facing names and that calls route correctly
   ([composition.md](composition.md)).
3. **Add a custom transform**: filter tools by tag; verify both `tools/list` and
   `tools/call` honor it ([transforms.md](transforms.md)).
4. **Use context**: a tool that logs, reports progress, and reads a resource via
   `CurrentContext()` ([context.md](context.md)).

**Common mistakes in this section**

- Treating FastMCP features (middleware, providers) as MCP protocol features.
- Forgetting that `Client("server.py")` infers stdio from a script path, and
  prompt arguments are strings.
- Expecting state to cross mount boundaries — it doesn't by default
  ([composition.md](composition.md)).