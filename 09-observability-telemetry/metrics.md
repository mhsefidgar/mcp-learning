# Metrics

## What is it?

**Metrics** are numeric, time-series measurements of system behavior: counters
(total tool calls, total errors), gauges (in-flight requests, queue depth), and
histograms (latency distribution). They answer *trend* questions: "is the error rate
rising?", "is p95 latency creeping up?", "how many calls per second are we
handling?"

## Why does MCP need it?

Logs explain one request; metrics explain the *system over time*. For an MCP server,
the questions that matter are all metric-shaped:

- call volume per tool (which tools are hot?)
- error rate per tool (which tool is failing?)
- latency percentiles (is the server getting slower?)
- in-flight concurrency and queue depth (are we near capacity?)
- retry counts and circuit-breaker state (is resilience working?)

Without metrics, you only find out when users complain; with them, you see trends
before they become incidents.

## How does it work?

1. **Instrument**: counters (`mcp.tools.calls` with labels `tool`, `outcome`),
   histograms (`mcp.tools.duration` with the same labels), gauges (`mcp.inflight`).
2. **Export**: either push to a metrics backend (Prometheus `/metrics` scrape, or
   OpenTelemetry OTLP — see [opentelemetry.md](opentelemetry.md)).
3. **Alert**: thresholds on the interesting metrics (error rate, p95 latency, queue
   depth).
4. **Dashboards**: latency/error/throughput per tool over time.

## Mental model

Metrics are the **gauges on the instrument panel**: fuel level (queue depth), speed
(throughput), engine temperature (latency), warning lights (error rate). You fly the
plane by watching the gauges, not by reading the mechanic's diary (logs).

## MCP-specific behavior

- **The natural metric set** for an MCP server:
  - `mcp.requests` counter by `method`, `outcome`
  - `mcp.tool_calls` counter by `tool`, `outcome`, `caller`
  - `mcp.tool_duration` histogram by `tool`
  - `mcp.inflight_requests` gauge
  - `mcp.session_count` gauge (session-based spec)
- **Middleware instruments everything** in one place
  ([12-fastmcp/middleware.md](../12-fastmcp/middleware.md)).
- **Rate-limit and breaker state** belong here too (`mcp.rate_limited`,
  `mcp.circuit_open`) — see [08-reliability-resilience/README.md](../08-reliability-resilience/README.md).

## Example

Prometheus-style counters in a middleware (conceptual — exact client depends on your
metrics library; OpenTelemetry instruments are standard):

```python
from fastmcp.server.middleware import Middleware, MiddlewareContext

class MetricsMiddleware(Middleware):
    def __init__(self, meter):
        self.calls = meter.create_counter("mcp.tool_calls", "count")
        self.duration = meter.create_histogram("mcp.tool_duration", "s")

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        start = time.perf_counter()
        try:
            result = await call_next(context)
            outcome = "error" if getattr(result, "is_error", False) else "ok"
        except Exception:
            outcome = "error"
            raise
        finally:
            self.calls.add(1, {"tool": context.message.name, "outcome": outcome})
            self.duration.record(time.perf_counter() - start, {"tool": context.message.name})
```

## Industry-standard pattern

Counters/histograms/gauges with **labels** (dimensions) + Prometheus/OTLP + alerting
is the standard stack. Rules: **labels are cardinality-limited** (don't put
request-scoped values like user ids in labels — use logs for that), **histograms
over averages** (p50/p95/p99 tell the real story), and **alert on symptoms** (error
rate, latency), not causes.

## Common mistakes

- **No labels** — "how many calls" without "which tool" is nearly useless.
- **High-cardinality labels** — a `user_id` label explodes the metric set.
- **Averages only** — one slow call hides in the mean; use percentiles.
- **Metrics that don't match code** — instrument at one layer (middleware), not
  scattered in handlers.
- **No alerting** — metrics without thresholds are archaeology, not observability.

## Testing

- **Instrumentation tests**: a tool call increments the right counter with the
  right labels ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **Error tests**: failing calls increment the error path.
- **Scrape tests**: the `/metrics` endpoint returns valid, parseable output.

## Security considerations

- **Metrics can leak**: caller names, tool names, and volumes reveal business
  activity — protect the metrics endpoint and consider what dimensions you expose.
- **Rate-limit your metrics endpoint** like any other surface.

## Related

- [structured-logging.md](structured-logging.md)
- [opentelemetry.md](opentelemetry.md)
- [08-reliability-resilience/observability.md](../08-reliability-resilience/observability.md)
- [10-scaling-performance/load-testing.md](../10-scaling-performance/load-testing.md)