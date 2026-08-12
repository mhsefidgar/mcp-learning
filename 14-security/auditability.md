# Auditability

## What is it?

**Auditability** is the property that every security-relevant action in an MCP
system can be *proven* afterwards: who called which tool with what arguments, when,
from which session, and what happened. It turns "we think we're safe" into "we can
show what happened."

## Why does MCP need it?

An agent that can act can also act wrongly — or be hijacked
([prompt-injection.md](prompt-injection.md)). Without an audit trail, a bad tool
call is undiscoverable and unrecoverable: you cannot tell what was affected, who
to notify, or whether a fix worked. Audit is the *evidence* layer under every other
security control, and it is what makes least-privilege reviews possible
([least-privilege.md](least-privilege.md)).

## What to audit (minimum set)

- **Identity**: principal, and how authenticated.
- **Action**: method (`tools/call`, `resources/read`, `prompts/get`), tool/resource
  name.
- **Parameters**: arguments — with secrets redacted
  ([sensitive-data-redaction.md](sensitive-data-redaction.md)).
- **Outcome**: success/failure, error code, duration, result size.
- **Context**: session ID, transport, client info, request ID (links to tracing,
  [09-observability-telemetry/distributed-tracing.md](../09-observability-telemetry/distributed-tracing.md)).
- **Timestamp**: monotonic + wall clock.

## How it works

1. An **audit point** fires at the boundary — middleware around dispatch captures
   the request, then the outcome
   ([03-routing-dispatch/11-middleware-routing.md](../03-routing-dispatch/11-middleware-routing.md)).
2. The event is **normalized** into a structured record (JSON) with an event type,
   IDs, and redaction applied.
3. It is **persisted** to an append-only store (the audit log must be
   tamper-evident: append-only, access-controlled, ideally WORM/immutable).
4. **Reviewed and alerted**: dashboards, anomaly alerts (mass deletion, denied
   attempts, new tools used).

## MCP-specific behavior

- **The protocol has no audit concept** — audit is server engineering (and client
  engineering on the agent side). MCP only gives you the *shape* of requests to
  record.
- The session/request lifecycle gives you stable IDs to correlate
  ([01-fundamentals/04-requests-responses-notifications.md](../01-fundamentals/04-requests-responses-notifications.md)).
- In composed systems, audit at **each boundary**: provider, proxy, and consumer
  ([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)).

## Industry-standard pattern

- **Structured, centralized logs** ([09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md)).
- **Append-only storage** with restricted access; operators who can read cannot
  silently edit.
- **Redaction at the source**, not at query time
  ([sensitive-data-redaction.md](sensitive-data-redaction.md)).
- **Retention policy**: keep what you can defend; delete what you must.
- **Alerting on anomalies**: unexpected denied calls, destructive operations,
  privilege changes.

## Common mistakes

- Auditing only failures (successful damage is invisible).
- Logging raw arguments including secrets.
- An in-memory "audit log" that vanishes on restart.
- No correlation ID, so a single request can't be traced across systems.
- Audit that is readable but not *trustworthy* (anyone can edit it).

## Testing

- A tool call produces an audit event with principal, tool, args (redacted),
  outcome, and timestamp.
- Denied attempts are audited too.
- Secrets never appear in audit records
  ([15-testing/security-testing.md](../15-testing/security-testing.md)).
- Crash simulation: events persisted before the operation's side effects are
  acknowledged.

## Security considerations

Audit is the difference between "we have security controls" and "we can verify
them." It also supports **compliance** (who accessed what) and **forensics**
(what happened during an incident). Protect the audit log itself — it is the
attacker's first target.

## Related

- [sensitive-data-redaction.md](sensitive-data-redaction.md)
- [secret-management.md](secret-management.md)
- [09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md)
- [09-observability-telemetry/distributed-tracing.md](../09-observability-telemetry/distributed-tracing.md)
- [14-security/examples/audited_server.py](examples/audited_server.py)
