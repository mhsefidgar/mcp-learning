# 13 — MCP Versioning

**What this section teaches.** Every versioning axis in MCP: **protocol versions**
(2025-11-25 vs. the 2026-07-28 stateless revision), **SDK/framework versions**
(FastMCP, TS SDK, Java SDK), **capability negotiation** across versions, the
**compatibility** rules, **deprecation** policy, and **tool/resource/prompt
versioning** as an application practice.

**Prerequisites.** [01-fundamentals/07-version-negotiation.md](../01-fundamentals/07-version-negotiation.md),
[01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md).

**Reading order:**

1. [protocol-versions.md](protocol-versions.md) — the version timeline and the big 2026-07-28 change
2. [capability-negotiation.md](capability-negotiation.md) — how features are gated across versions
3. [compatibility.md](compatibility.md) — what stays compatible, what breaks
4. [deprecation.md](deprecation.md) — the official deprecation policy
5. [fastmcp-versions.md](fastmcp-versions.md) — framework versioning in practice
6. [tool-resource-prompt-versions.md](tool-resource-prompt-versions.md) — versioning the components you expose

**The landscape (as of this writing):**

| Version | Status | Character |
|---------|--------|-----------|
| 2024-11-05 → 2025-06-18 | legacy | handshake-era, growing feature set |
| **2025-11-25** | **current stable** — what this repo's code targets | sessions, stdio + Streamable HTTP, elicitation |
| **2026-07-28** | new major revision (just released) | **stateless core**, MRTR, header routing, Tasks |

**Exercises.**

1. **Migration review**: take a 2025-11-25 server and enumerate what the
   2026-07-28 spec changes for it (sessions, initialization, notifications,
   elicitation) ([protocol-versions.md](protocol-versions.md)).
2. **Negotiation drill**: a client that supports only 2025-11-25 meets a server
   that supports 2025-06-18 and 2025-11-25 — what version is negotiated?
   ([01-fundamentals/07-version-negotiation.md](../01-fundamentals/07-version-negotiation.md)).
3. **Deprecation plan**: pick a tool you'd remove; write its deprecation plan
   (announce, mark, warn, remove) ([deprecation.md](deprecation.md)).

**Common mistakes in this section**

- Confusing **protocol version** with **SDK version** (and with **component
  version**).
- Assuming every client/server supports the newest spec.
- Deprecating without a window (see [deprecation.md](deprecation.md)).