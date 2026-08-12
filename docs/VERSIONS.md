# Versions

> **Read this first.** Everything in this repository is written against a specific
> protocol version and specific SDK versions. MCP and its SDKs evolve quickly, and
> APIs change between releases. This file records exactly what the repository targets,
> so you know what will run and what to update when you upgrade.

_Last verified: August 12, 2026._

---

## The two protocol eras (important context)

MCP has two protocol generations that matter right now. The repository teaches the
**stable, widely-deployed** version as its primary target and documents the newer
revision as a migration topic.

| Spec version | Status | What it looks like | Implemented by |
|--------------|--------|--------------------|----------------|
| **2025-11-25** | Current stable, what all current stable SDKs ship | Session-based: `initialize`/`initialized` handshake, `Mcp-Session-Id`, stdio + Streamable HTTP transports, server-to-client requests (sampling, elicitation, roots) over a held-open connection | FastMCP 3.x, `@modelcontextprotocol/sdk` 1.x, Java SDK 2.0.x, Go/Rust current releases |
| **2026-07-28** | New major revision (released late July 2026) | **Stateless** core: no `initialize` handshake, no sessions, every request self-describing; Multi Round-Trip Requests (MRTR); `Mcp-Method`/`Mcp-Name` HTTP headers for routing; cacheable list results (`ttlMs`, `cacheScope`); Tasks extension; deprecations (roots, sampling, logging, legacy SSE) | Brand-new SDK v2s: `@modelcontextprotocol/server` + `@modelcontextprotocol/client` (TS), updated Python/Go/C# SDKs, Rust SDK (beta). FastMCP 4.0 (beta) |

**Why the repository teaches 2025-11-25 as primary:** the curriculum — initialization,
capabilities, version negotiation, sessions, lifecycle, graceful shutdown, stdio,
Streamable HTTP — describes the session-based protocol, and that is what every *stable*
release of the three primary SDKs (FastMCP 3.x, TS SDK 1.x, Java SDK 2.0.x) implements
today. The **2026-07-28** stateless revision is covered in depth in
[13-versioning/](../13-versioning/README.md) and
[01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md), with migration
notes, so you can move to it when your SDK supports it.

---

## Version matrix

| Component | Version | Notes |
|-----------|---------|-------|
| MCP protocol (primary teaching target) | **2025-11-25** | Session-based spec |
| MCP protocol (secondary / future) | **2026-07-28** | Stateless spec, covered in `13-versioning` |
| Python | **3.13** | 3.10+ required for FastMCP 3.x |
| FastMCP | **3.4.x** | `pip install fastmcp`; FastMCP 4.0.0b1 (beta) implements 2026-07-28 |
| TypeScript SDK | **`@modelcontextprotocol/sdk` 1.30.x** | v2 (new spec) ships as `@modelcontextprotocol/server` + `@modelcontextprotocol/client` |
| Node.js | **24.x** | 18+ works for the TS examples |
| Java | **21** (17+ required) | |
| MCP Java SDK | **`io.modelcontextprotocol.sdk:mcp` 2.0.x** | Jackson + Reactor core; spec 2025-11-25 |
| Go | **1.24** | custom implementations in `repository/go`, stdlib only |
| Rust | **1.95 (edition 2021)** | `tokio`, `serde`, `serde_json`; custom implementations |

---

## What is locally verified

The repository was built in an environment with the following toolchains available.
Code that could be executed and tested locally is marked accordingly.

| Language | Toolchain | Locally verified? |
|----------|-----------|-------------------|
| Python | 3.13.14 | ✅ Yes — FastMCP examples and tests run |
| TypeScript | Node 24.13.0 | ✅ Yes — SDK examples and tests run |
| Rust | 1.95.0 | ✅ Yes — `cargo test` runs |
| Go | — (not installed) | ⚠️ Written carefully, **not** executed locally |
| Java | — (not installed) | ⚠️ Written carefully, **not** executed locally |

Where a file is not locally verified, its header comment says so. Treat Go and Java
code as a close-to-correct reference and run `go test` / `mvn test` on your machine
before relying on it.

---

## Curriculum → folder mapping

The `Sections.text` curriculum (15 topics) is mapped onto the repository's numbered
folders. Three topics had no home in the original 13-section layout and were added as
new sections (marked ⭐).

| `Sections.text` topic | Repository section |
|-----------------------|--------------------|
| 1. MCP fundamentals | `01-fundamentals/` |
| 2. Three core primitives | `02-primitives/` |
| 3. Routing & dispatch | `03-routing-dispatch/` |
| 4. Tool engineering | `04-tool-engineering/` |
| 5. Resource engineering | `05-resource-engineering/` |
| 6. Agent interaction | `06-agent-interaction/` |
| 7. Inspector / debugging | `07-inspector-debugging/` |
| 8. Reliability & resilience | `08-reliability-resilience/` |
| 9. Observability & telemetry | `09-observability-telemetry/` ⭐ |
| 9. Scaling & performance | `10-scaling-performance/` ⭐ |
| 10. Communication & transport | `11-communication-transport/` ⭐ |
| 11. FastMCP architecture | `12-fastmcp/` |
| 12. MCP versioning | `13-versioning/` |
| 13. MCP security | `14-security/` |
| 14. MCP testing | `15-testing/` |
| 15. End-to-end MCP agent | `16-end-to-end/` + `capstone/` |

---

## Updating examples when APIs change

When you upgrade a dependency:

1. Update this file's version matrix.
2. Grep the affected language's docs and examples for the old API and update imports
   and calls.
3. Re-run that language's test suite (see the root `README.md`).
4. If the change is a **deprecation** (not a removal), keep a short "migration" note in
   the relevant doc under `13-versioning/deprecation.md`.

## Version-accuracy rules

- **Never invent an SDK API.** If an implementation detail depends on the current SDK
  version, verify it against the official docs before writing the example.
- **Mark what is MCP spec vs. SDK vs. general engineering.** A wrong attribution is a
  bug.
- **Record the version** in the file header of any runnable project.
