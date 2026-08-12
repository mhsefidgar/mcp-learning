# OpenTelemetry

## What is it?

**OpenTelemetry (OTel)** is the vendor-neutral standard for generating and exporting
telemetry — traces, metrics, and logs through one API. You instrument once with OTel
and export anywhere (Jaeger, Tempo, Datadog, Honeycomb, Prometheus, your own
collector). It's the plumbing that makes the other three docs practical.

## Why does MCP need it?

Without OTel, every MCP server would hand-roll telemetry with a vendor's SDK — and
every vendor would do it differently, making cross-service tracing impossible.
OTel gives you:

- **One API** for traces + metrics + logs across Python, TypeScript, Java, Go, Rust.
- **Standard propagation** (W3C `traceparent`) so your MCP server's spans join the
  agent client's trace automatically.
- **Auto-instrumentation** for HTTP/DB libraries — downstream calls get spanned for
  free.

## How does it work?

1. **Add the SDK** (language-specific: `opentelemetry-python`, `@opentelemetry/sdk-node`,
   `opentelemetry-java`, `go.opentelemetry.io/otel`, `opentelemetry-rust`).
2. **Get a tracer/meter**: `trace.get_tracer("mcp.server")`.
3. **Instrument**: span tool calls, count metrics, log with the trace context
   attached.
4. **Configure an exporter**: OTLP to a collector (or directly to a backend).
5. **Propagate**: HTTP instrumentation handles `traceparent` for you.

```
Agent client ──(traceparent)──► MCP server ──► tool ──► downstream API
     └───────────── one trace, spans at every hop ────────────► collector
```

## Mental model

OTel is the **phone system for observability**: your instruments (tracer, meter)
are the handsets, the wire format (OTLP) is the dial tone, and the collector is the
switchboard — you plug into it once and can reach any backend (any vendor) without
rewiring.

## MCP-specific behavior

- **Nothing protocol-level** — OTel sits entirely outside the MCP wire protocol.
- **The MCP-server integration point**: middleware wraps every request with a span
  and attaches context
  ([12-fastmcp/middleware.md](../12-fastmcp/middleware.md),
  [08-reliability-resilience/observability.md](../08-reliability-resilience/observability.md)).
- **SDK status**: all five languages in this repo have mature OTel support; the Go
  lab project (`repository/go/resilience`) shows a Go example.

## Example

FastMCP + OTel middleware (minimal — see the docs' middleware pattern):

```python
from opentelemetry import trace
from fastmcp.server.middleware import Middleware, MiddlewareContext

tracer = trace.get_tracer("mcp.server")

class TracingMiddleware(Middleware):
    async def on_message(self, context: MiddlewareContext, call_next):
        with tracer.start_as_current_span(f"mcp.{context.method}") as span:
            span.set_attribute("method", context.method)
            return await call_next(context)
```

## Industry-standard pattern

OTel is *the* industry standard (CNCF). Production rules: **instrument once, export
anywhere**, use **auto-instrumentation** where available, configure **sampling** at
scale, and treat the **collector** as the control point (redaction, sampling,
routing) between your services and backends.

## Common mistakes

- **Vendor SDKs everywhere** — lock-in and double instrumentation.
- **No sampling at scale** — 100% traces of high-throughput MCP servers is
  expensive; configure head/tail sampling.
- **Instrumentation without export config** — spans built and dropped.
- **Forgetting propagation** — the whole point (a joined trace) silently lost.
- **Collector as an afterthought** — redaction and sampling belong there, not in
  every service.

## Testing

- **Export tests**: a request produces spans/metrics visible to the collector (run
  a local OTel collector in CI).
- **Propagation tests**: `traceparent` flows client → server → downstream.
- **Redaction tests**: attributes are scrubbed before export.

## Security considerations

- **OTel data is sensitive** — protect the collector, restrict access, redact
  attributes ([14-security/auditability.md](../14-security/auditability.md)).
- **Don't export spans with secrets** — configure attribute redaction in the
  collector as defense in depth.

## Related

- [structured-logging.md](structured-logging.md) · [metrics.md](metrics.md) · [distributed-tracing.md](distributed-tracing.md)
- [08-reliability-resilience/observability.md](../08-reliability-resilience/observability.md)
- [10-scaling-performance/observability-at-scale.md](../10-scaling-performance/observability-at-scale.md)