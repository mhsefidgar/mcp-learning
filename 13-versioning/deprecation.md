# Deprecation

## What is it?

**Deprecation** is the controlled retirement of a feature: it's announced and still
works for a defined window, then removed. The MCP spec now has a **formal
deprecation policy** (a twelve-month minimum window), and the ecosystem follows the
same discipline for protocol features, SDK APIs, and your own components.

## Why does it matter?

Abrupt removal breaks every user; indefinite retention rots the surface. Deprecation
is the middle path: **announce → keep working (window) → remove**, giving users time
to migrate and the surface time to clean up. It's a trust contract: "deprecated"
means "still works, but plan to move" — not "broken."

## Current deprecations in MCP (2026-07-28)

| Feature | Status | What to do |
|---------|--------|------------|
| `sampling` (server→client LLM calls) | deprecated, ≥12-month window | call an LLM directly from your server; use elicitation for interactive input ([06-agent-interaction/sampling.md](../06-agent-interaction/sampling.md)) |
| `roots` (client→server context) | deprecated, ≥12-month window | explicit paths/URIs in tool arguments; elicitation for interactive context ([06-agent-interaction/roots.md](../06-agent-interaction/roots.md)) |
| `logging` capability | deprecated, ≥12-month window | log locally/OTel; the channel still works for compatible clients ([09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md)) |
| legacy HTTP+SSE transport | deprecated, year-long offramp | migrate to Streamable HTTP ([01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)) |
| Dynamic Client Registration (OAuth) | deprecated → CIMD | use client metadata documents ([14-security/authentication.md](../14-security/authentication.md)) |

## The discipline (for your own components)

1. **Announce** — document the deprecation (changelog, tool description, schema).
2. **Mark** — make it visible: a deprecated tool keeps working but its description
   says "deprecated, use X instead"; consider a `deprecated` annotation where the
   spec/SDK supports it.
3. **Window** — keep it working for a defined period (mirror the spec's
   twelve-month minimum as a default).
4. **Remove** — after the window, remove it and note the removal in the changelog.
5. **Instrument** — log usage of deprecated features so you know when the window
   can close ([09-observability-telemetry/metrics.md](../09-observability-telemetry/metrics.md)).

## Mental model

Deprecation is the **renovation notice on the building**: "This wing stays open for
12 months, then it becomes a garden — here's the map to the new entrance." Tenants
(deprecated users) keep living there, but they're told, given a deadline, and
tracked — and when the deadline comes, the demolition is no surprise.

## Common mistakes

- **Deprecating without a window** — an instant break for someone.
- **Deprecating without a replacement** — "deprecated" with nothing to migrate to.
- **Keeping deprecated code forever** — surface rot and security debt.
- **Removing without instrumenting** — you can't prove nobody used it.
- **Treating "deprecated" as "broken"** — it must keep working for the window.

## Testing

- **Window tests**: deprecated features work until the removal date
  ([15-testing/compatibility-testing.md](../15-testing/compatibility-testing.md)).
- **Migration tests**: the replacement behaves equivalently.
- **Usage tests**: metrics show deprecated-feature usage trends.

## Security considerations

- **Deprecated features are attack surface** — old auth flows, old transports, old
  protocol behavior; track and secure them during the window.
- **Deprecated capabilities may lack modern hardening** — don't build new systems
  on them.

## Related

- [protocol-versions.md](protocol-versions.md)
- [compatibility.md](compatibility.md)
- [tool-resource-prompt-versions.md](tool-resource-prompt-versions.md)
- [03-routing-dispatch/09-version-aware-routing.md](../03-routing-dispatch/09-version-aware-routing.md)