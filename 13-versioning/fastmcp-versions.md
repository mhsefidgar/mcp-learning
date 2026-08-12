# FastMCP Versions

## What is it?

FastMCP's own release history and what changed between majors — separate from the
*protocol* version (FastMCP negotiates protocol versions independently). Knowing
the framework's history helps you read old code and upgrade cleanly.

## The majors (as of this writing)

| Version | Era | What changed |
|---------|-----|--------------|
| 1.x (2024–2025) | early | the classic `@mcp.tool` API; sessions-era protocol |
| 2.x (2025) | growth | `Client` (2.0); middleware (2.9); elicitation (2.10); resources/prompts APIs; context injection |
| **3.x** (Jan 2026–) | **current stable** | **providers, transforms, component versioning**; server/client API split; the API this repo uses |
| 4.0 (beta) | stateless | first-class support for the 2026-07-28 protocol (background tasks, stateless interactivity, MRTR) |

## What changed in 3.x (the API this repo targets)

Verified against 3.4.x — notable differences from 2.x:

- **Providers and transforms** are core concepts
  ([providers.md](../12-fastmcp/providers.md), [transforms.md](../12-fastmcp/transforms.md)).
- **Server-side prompt rendering**: `mcp.get_prompt(name)` returns the component;
  **`mcp.render_prompt(name, arguments)`** renders it with arguments.
- **Result types changed**: `ToolResult` has `structured_content` (dict-shaped for
  structured returns) rather than the 2.x `data`; client-side `read_resource`
  returns content blocks directly.
- **Client transport inference**: `Client("server.py")` (script path → stdio),
  `Client(url)` (→ HTTP), `Client({mcpServers: ...})` (→ multi-server config).
- **MCP prompt arguments are strings** (`"5"`, not `5`).

## How to upgrade

1. Read the upgrade guide in the FastMCP docs (`gofastmcp.com/updates`).
2. Grep for the changed APIs (above) and update imports/calls.
3. Re-run your test suite — the repo's tests are the migration safety net
   ([15-testing/README.md](../15-testing/README.md)).
4. Update [docs/VERSIONS.md](../docs/VERSIONS.md).

## Mental model

FastMCP versions are **framework majors**, like any library: 2.x → 3.x introduced
the provider/transform architecture (how components are sourced and shaped), and
4.x tracks the protocol's stateless era. Protocol version and framework version are
two different clocks — a 3.4 server negotiates the protocol version
independently ([compatibility.md](compatibility.md)).

## Common mistakes

- **Following 2.x tutorials with 3.x installed** — the API changed; check the
  version badge on every docs page.
- **Assuming the framework version implies the protocol version** — FastMCP 3.x
  speaks the session-based protocol; FastMCP 4.0 (beta) speaks the stateless one.
- **Silent upgrades** — pin your dependency and test before bumping.

## Related

- [docs/VERSIONS.md](../docs/VERSIONS.md)
- [12-fastmcp/README.md](../12-fastmcp/README.md)
- [protocol-versions.md](protocol-versions.md)
- [compatibility.md](compatibility.md)