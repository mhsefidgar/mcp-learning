# Structured Logging

## What is it?

**Structured logging** is writing logs as **machine-readable records** (JSON) with a
**fixed, documented field set**, instead of free-form prose. Example:

```json
{"ts": "2026-08-12T13:00:00Z", "level": "info", "event": "tool_call",
 "tool": "search_orders", "caller": "alice", "outcome": "ok",
 "duration_ms": 12.4, "trace_id": "4bf92f…"}
```

vs. prose: `INFO: order search for alice worked and took 12.4 ms`.

## Why does MCP need it?

MCP servers are where models touch the real world — exactly the place you need to
*search, aggregate, and correlate* logs. Structured logs make that possible:

- **Search**: "all `delete_*` calls by caller in the last hour" is a query, not a
  grep.
- **Aggregate**: error rates per tool are a simple group-by.
- **Correlate**: every log line for one request carries the same trace id.

Prose logs fail at all three, and at scale they're effectively noise.

## How does it work?

1. **Define the field set** (the log schema): timestamp, level, event, plus
   context fields (tool, method, caller, outcome, duration, trace id).
2. **Log via the logger**, passing fields as structured data — never string
   interpolation (`log.info(json.dumps({...}))` or a JSON formatter).
3. **Redact by default**: secrets, tokens, PII, and raw argument values are
   scrubbed (see below).
4. **Correlate**: attach the request's trace id to every line
   ([distributed-tracing.md](distributed-tracing.md)).

## Mental model

Structured logging is **filling in a form for every event** instead of writing a
paragraph: the form's fields are fixed, machine-readable, and queryable. Prose logs
are diary entries; structured logs are a database table.

## MCP-specific behavior

- **The `logging` capability** lets a client set the server's level
  (`logging/setLevel`) and receive `notifications/message` — emit the *same*
  structured events through that channel if the client subscribed, but always log
  locally too.
- **The natural log events**: `initialize`, `tools/list`, `tools/call` (with tool
  name, arguments *redacted*, outcome, duration), `resources/read`, errors.
- **Middleware is the place to log** — one structured-logging middleware covers all
  operations ([12-fastmcp/middleware.md](../12-fastmcp/middleware.md)).

## Example

FastMCP structured logging middleware (verified pattern — adapt levels to your
version):

```python
import json, logging, time
from fastmcp.server.middleware import Middleware, MiddlewareContext

log = logging.getLogger("mcp")

class StructuredLoggingMiddleware(Middleware):
    async def on_message(self, context: MiddlewareContext, call_next):
        start = time.perf_counter()
        outcome = "ok"
        try:
            return await call_next(context)
        except Exception:
            outcome = "error"
            raise
        finally:
            log.info(json.dumps({
                "event": "mcp.message",
                "method": context.method,
                "outcome": outcome,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                # trace_id: attached by the tracing middleware, not hard-coded
            }))
```

## Industry-standard pattern

JSON logs + a log-shipping pipeline (ELK, Loki, CloudWatch) + query-time
aggregation is the standard. Production rules: **one schema per service**, **redact
at the source** (never log the secret in the first place), **correlate with trace
ids**, and **log success paths too** (you can't see regressions in error-only logs).

## Common mistakes

- **Prose logs** — unparseable, uncorrelatable.
- **Logging raw arguments** — tool arguments routinely contain emails, tokens,
  paths ([14-security/sensitive-data-redaction.md](../14-security/sensitive-data-redaction.md)).
- **No field schema** — "sometimes it has duration, sometimes not" breaks queries.
- **Log injection**: a tool argument containing `\n{"event":"fake"}` injects a
  forged log line — sanitize newlines/control characters in logged fields.

## Testing

- **Shape tests**: every log line parses as JSON with the documented fields
  ([15-testing/security-testing.md](../15-testing/security-testing.md)).
- **Redaction tests**: feeding a tool a secret argument never puts the secret in
  logs.
- **Correlation tests**: all lines for one request share the trace id.
- **Injection tests**: malicious argument values can't forge log lines.

## Security considerations

- **Logs are sensitive data stores** — protect access, retain per policy, redact
  aggressively ([14-security/auditability.md](../14-security/auditability.md)).
- **Redact at the source**, not in the pipeline — the pipeline is too late.
- Never log authorization tokens, session ids, or full argument payloads.

## Related

- [metrics.md](metrics.md) · [distributed-tracing.md](distributed-tracing.md)
- [08-reliability-resilience/observability.md](../08-reliability-resilience/observability.md)
- [14-security/sensitive-data-redaction.md](../14-security/sensitive-data-redaction.md)
- [12-fastmcp/middleware.md](../12-fastmcp/middleware.md)