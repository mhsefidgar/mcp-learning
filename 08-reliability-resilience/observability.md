# Observability

> **General engineering pattern.** Observability is not an MCP feature (the `logging`
> capability is MCP's *log channel*, but the discipline is general). Full detail in
> [09-observability-telemetry](../09-observability-telemetry/README.md).

## What is it?

**Observability** is the ability to answer "what is happening, and why?" from
telemetry — structured logs, metrics, and traces
([09-observability-telemetry/README.md](../09-observability-telemetry/README.md)). For
MCP systems it means being able to see: which tools are called, by whom, how long
they took, whether they failed, and *why*.

## Why does MCP need it?

MCP servers sit between models and the world — the exact place where invisible
failures happen (a hallucinated argument, a slow tool, a retried call). Debugging an
agent's behavior *without* observing the tool calls is guesswork. Observability
answers the three questions that come up in every MCP incident:

1. **What did the model call?** (audit + debugging — see
   [14-security/auditability.md](../14-security/auditability.md))
2. **How did it go?** (latency, errors, retries)
3. **Where did it go wrong?** (which layer, which dependency)

## How does it work?

1. **Structured logging**: every request/response logged as JSON with context
   (method, tool, caller, trace id, duration, outcome). Redact secrets
   ([09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md)).
2. **Metrics**: counters/gauges for tool calls (by tool, by outcome), latency
   histograms, error rates, in-flight requests
   ([09-observability-telemetry/metrics.md](../09-observability-telemetry/metrics.md)).
3. **Tracing**: one trace id per logical operation across client → proxy → backend
   ([distributed-tracing.md](distributed-tracing.md)).
4. **Health checks**: expose liveness/readiness for load balancers
   ([10-scaling-performance/health-checks.md](../10-scaling-performance/health-checks.md)).

## Mental model

Observability is the **instrument panel of the plane**: without gauges for fuel,
altitude, and engine health, you're flying blind. Each instrument (log, metric,
trace) answers a different question: logs tell the story, metrics show the trend,
traces follow one journey.

## MCP-specific behavior

- **The `logging` capability** lets a client set the server's log level
  (`logging/setLevel`) and receive `notifications/message` — the protocol's own log
  channel. Use it, but also log locally (the client may never subscribe).
- **Log the MCP envelope**: method, tool name, arguments (redacted), result/error,
  duration, caller identity.
- **Middleware is the perfect place to instrument** — one logging middleware covers
  every request ([12-fastmcp/middleware.md](../12-fastmcp/middleware.md)).
- **The 2026-07-28 spec deprecates the `logging` capability** — local observability
  remains the baseline ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).

## Example

A logging middleware (FastMCP) that emits structured JSON:

```python
import json, logging, time
from fastmcp.server.middleware import Middleware, MiddlewareContext

log = logging.getLogger("mcp.server")

class StructuredLoggingMiddleware(Middleware):
    async def on_message(self, context: MiddlewareContext, call_next):
        start = time.perf_counter()
        try:
            result = await call_next(context)
            outcome = "ok"
        except Exception as exc:
            outcome = f"error:{type(exc).__name__}"
            raise
        finally:
            log.info(json.dumps({
                "event": "mcp.request",
                "method": context.method,
                "outcome": outcome,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            }))
        return result
```

## Industry-standard pattern

The three pillars (logs, metrics, traces) with OpenTelemetry as the vendor-neutral
standard — see [09-observability-telemetry/README.md](../09-observability-telemetry/README.md)
for the full treatment. The rules: **log structured** (JSON, machine-parseable),
**correlate** (trace ids everywhere), **redact** (secrets/PII never in logs), and
**measure what matters** (call volume, latency, errors).

## Common mistakes

- **Prose logs** — unparseable, uncorrelatable.
- **No trace ids** — can't follow a call across the client, proxy, and backend.
- **Logging raw arguments** — secrets and PII in logs
  ([09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md)).
- **Only logging errors** — success paths are needed to spot regressions.
- **No metrics** — logs are fine for debugging one request, useless for trends.

## Testing

- **Log-shape tests**: emitted logs parse as JSON with required fields
  ([15-testing/security-testing.md](../15-testing/security-testing.md)).
- **Redaction tests**: secrets never appear in logs.
- **Correlation tests**: a request's trace id appears in every log line for it.
- **Metric tests**: counters increment on calls and errors.

## Security considerations

- **Logs are a data store**: they hold sensitive data by definition — protect them,
  control access, and redact aggressively
  ([14-security/auditability.md](../14-security/auditability.md)).
- **Log injection**: attackers can inject fake log lines via tool arguments —
  sanitize newlines and control characters in logged fields.

## Related

- [09-observability-telemetry/README.md](../09-observability-telemetry/README.md)
- [distributed-tracing.md](distributed-tracing.md)
- [14-security/auditability.md](../14-security/auditability.md)
- [12-fastmcp/middleware.md](../12-fastmcp/middleware.md)