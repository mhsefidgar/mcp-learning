# Compatibility

## What is it?

**Compatibility** is the set of rules that let clients and servers of *different
versions* work together — and the explicit list of what *breaks* when versions
differ. It's the contract between "old client, new server" and "new client, old
server."

## Why it matters

Deployments are never synchronized: a fleet will run mixed SDK versions for months
while the ecosystem migrates from 2025-11-25 to 2026-07-28. Compatibility rules
decide which pairs work:

| Pair | Verdict | Why |
|------|---------|-----|
| Same version | ✅ | trivially compatible |
| New client, old server | ✅ | negotiation steps down ([01-fundamentals/07-version-negotiation.md](../01-fundamentals/07-version-negotiation.md)) |
| Old client, new server | ✅ | new server supports the old version (spec guarantee: support prior stable) |
| Client/server with no shared version | ❌ | negotiate fails cleanly |

## The rules

1. **Newer servers must keep supporting older protocol versions** — that's what
   makes rolling deployments possible.
2. **Newer clients must be willing to step down** to the server's version — and
   then behave *per that version* (no 2026-only features on a 2025 connection).
3. **Behavior follows the negotiated version** — the version decides message
   shapes, deprecations, and defaults. An old connection gets old behavior.
4. **SDK-level compatibility is separate from protocol-level**: FastMCP 3.4.x
   negotiates protocol versions independently of its own framework version.

## Mental model

Compatibility is the **power-plug adapter**: the wall socket (server) has
international sockets (multiple versions); your device (client) brings the right
adapter (negotiation) and then runs at the socket's voltage (negotiated version).
No shared socket → the device politely refuses to plug in (clean error).

## MCP-specific behavior

- **The spec requires servers to support at least one previous stable version**
  during transitions — the 2026-07-28 release must serve 2025-11-25 clients.
- **Deprecated features keep working** for the deprecation window
  ([deprecation.md](deprecation.md)) — that's compatibility in action.
- **Component-level compatibility is your job**: tools, resources, and prompts are
  *your* contracts, versioned by your conventions
  ([tool-resource-prompt-versions.md](tool-resource-prompt-versions.md)).

## Example

A compatibility matrix test (conceptual):

| Server version | Client version | Expected |
|----------------|----------------|----------|
| 2025-11-25 | 2025-11-25 | ✅ session-based |
| 2025-11-25 | 2026-07-28 | ✅ steps down, session-based behavior |
| 2026-07-28 | 2026-07-28 | ✅ stateless |
| 2026-07-28 | 2025-11-25 | ✅ server serves the old version (per spec) |
| 2025-06-18 only | 2026-07-28 only | ❌ clean failure |

Test these with a real matrix ([15-testing/compatibility-testing.md](../15-testing/compatibility-testing.md)).

## Common mistakes

- **Assuming "newer is always better"** — the negotiated version, not the SDK
  version, decides behavior.
- **Dropping old-version support too fast** — breaking old clients is a breaking
  change; follow deprecation policy.
- **Testing only same-version pairs** — the interesting bugs live in mixed-version
  matrices.

## Testing

- **Version-matrix tests**: every supported client × server pair
  ([15-testing/compatibility-testing.md](../15-testing/compatibility-testing.md)).
- **Downgrade-behavior tests**: a new client on an old server uses old behavior.
- **Conformance suites**: the SDK repos ship conformance tests against the spec
  (the Java SDK's conformance-tests, for example) — run them per version.

## Security considerations

- **Older versions may lack newer security features** — a negotiated old version
  means old defaults; combine with real authentication
  ([14-security/README.md](../14-security/README.md)).
- **Downgrade attacks**: a MITM forcing a lower version disables newer protections
  — authenticate before trusting the negotiation
  ([01-fundamentals/07-version-negotiation.md](../01-fundamentals/07-version-negotiation.md)).

## Related

- [protocol-versions.md](protocol-versions.md)
- [deprecation.md](deprecation.md)
- [01-fundamentals/07-version-negotiation.md](../01-fundamentals/07-version-negotiation.md)
- [15-testing/compatibility-testing.md](../15-testing/compatibility-testing.md)