# Protocol Versions

## What is it?

The MCP protocol is versioned by **release date strings** (`2024-11-05`,
`2025-03-26`, `2025-06-18`, `2025-11-25`, `2026-07-28`), negotiated at connection
time ([01-fundamentals/07-version-negotiation.md](../01-fundamentals/07-version-negotiation.md)).
This document is the timeline and, in depth, the **2026-07-28 revision** — the
largest change since launch.

## The timeline

| Version | Highlights |
|---------|------------|
| 2024-11-05 | initial release: tools, resources, prompts; stdio |
| 2025-03-26 | tool annotations; Streamable HTTP; version negotiation rules clarified |
| 2025-06-18 | elicitation; pagination (experimental); completions; output schemas |
| **2025-11-25** | the stable session-based spec — what current stable SDKs implement |
| **2026-07-28** | **stateless core**: no handshake, no sessions, MRTR, header routing, cacheable lists, Tasks, deprecations |

## The 2026-07-28 revision (what changed)

**1. Stateless protocol core** (the headline):

- **No `initialize`/`initialized` handshake, no `Mcp-Session-Id`.**
- Every request is **self-describing**: it carries its protocol version, client
  identity, and client capabilities in `_meta`.
- Optional `server/discover` RPC for clients that want capabilities up front.
- Any request can hit any instance behind a plain round-robin load balancer —
  the scaling change ([10-scaling-performance/scaling-fundamentals.md](../10-scaling-performance/scaling-fundamentals.md)).

**2. Multi Round-Trip Requests (MRTR)** — interactive flows over a stateless
connection: a server that needs input mid-call returns
`resultType: "input_required"` with its questions; the client retries the call with
`inputResponses` ([06-agent-interaction/elicitation.md](../06-agent-interaction/elicitation.md)).

**3. Header-based routing** — Streamable HTTP requests must include `Mcp-Method`
and `Mcp-Name` headers, so gateways/WAFs route and meter without parsing bodies
([03-routing-dispatch/01-request-dispatch.md](../03-routing-dispatch/01-request-dispatch.md)).

**4. Cacheable list results** — `tools/list`, `prompts/list`, `resources/list`, and
`resources/read` responses carry `ttlMs` and `cacheScope` hints
([08-reliability-resilience/caching.md](../08-reliability-resilience/caching.md)).

**5. Authorization hardening** — RFC 9207 `iss` validation, client metadata
documents (CIMD) replacing dynamic client registration, issuer-bound credentials
([14-security/authentication.md](../14-security/authentication.md)).

**6. Tasks extension** — long-running work formalized (`tasks/get`, `tasks/update`,
poll-based) ([04-tool-engineering/long-running-operations.md](../04-tool-engineering/long-running-operations.md)).

**7. Deprecations** — roots, sampling, and logging are deprecated (≥12-month
window); the legacy HTTP+SSE transport is deprecated
([deprecation.md](deprecation.md)).

## How it affects you today

- **Stable SDKs (FastMCP 3.x, TS SDK 1.x, Java SDK 2.0.x) speak 2025-11-25** — the
  code in this repository runs on the session-based spec.
- **New SDKs (TS `@modelcontextprotocol/server` + `@modelcontextprotocol/client`,
  updated Python/Go/C#, Rust beta) speak 2026-07-28** — the spec the ecosystem is
  moving to.
- **Both eras must interoperate during the transition**: negotiation decides which
  behavior applies ([compatibility.md](compatibility.md)).

## Mental model

Protocol versions are **eras of the same language**: 2025-11-25 is the "phone call"
era (sessions, held-open connections); 2026-07-28 is the "mail" era (every letter
self-contained, questions answered by follow-up letters). Both eras coexist, and
negotiation is how two speakers agree which era they're in.

## Related

- [01-fundamentals/07-version-negotiation.md](../01-fundamentals/07-version-negotiation.md)
- [capability-negotiation.md](capability-negotiation.md)
- [compatibility.md](compatibility.md)
- [docs/VERSIONS.md](../docs/VERSIONS.md)