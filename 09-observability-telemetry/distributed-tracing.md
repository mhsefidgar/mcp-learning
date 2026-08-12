# Distributed Tracing

## What is it?

**Distributed tracing** follows one logical operation across every service boundary
it crosses. Each hop creates a **span** (named, timed work); spans nest into a
**trace** identified by a **trace id** that propagates across services (standard:
W3C `traceparent` header).

For MCP the boundaries are natural: **agent client → MCP server → tool handler →
downstream API → database**.

## Why does MCP need it?

A slow tool call raises the question "which hop is slow?" — the *reason* MCP exists
is that the call spans systems. Tracing answers it: 3.0s total breaks down into
0.1s dispatch + 2.6s downstream + 0.3s serialization. It's also the only way to
reconstruct a *multi-tool workflow* (agent turns) across the whole path
([16-end-to-end/README.md](../16-end-to-end/README.md)).

## How does it work?

1. **Create**: the entry point (agent, gateway) starts a trace and root span.
2. **Propagate**: the trace id travels with the request — HTTP `traceparent`
   header, or `_meta` for protocol-level metadata.
3. **Span**: each hop creates a child span, recording attributes (tool name,
   outcome) and status (ok/error).
4. **Export**: spans → collector (Jaeger/Tempo/OTLP) → UI.

```
trace 4bf92f…
 ├─ span: agent.call_tool("render")          [client]
 │   └─ span: mcp.tools/call                 [server]
 │       └─ span: tool.render                [handler]
 │           └─ span: POST /render-api       [downstream]
```

## Mental model

Tracing is the **receipt trail through a multi-floor building**: each floor stamps
your ticket with entry/exit times. Logs tell you what happened *on one floor*; the
trace reconstructs the whole journey, showing exactly where you spent your time.

## MCP-specific behavior

- **Nothing protocol-level** in the stable spec — carry the trace id via transport
  headers (HTTP) or `_meta`. (The modern spec's per-request `_meta` makes this
  cleaner.)
- **The span points**: one span per `tools/call`; a child span per tool handler;
  grandchild spans for downstream calls; a span per hop through a proxy
  ([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)).
- **Middleware instruments everything** at once
  ([12-fastmcp/middleware.md](../12-fastmcp/middleware.md)).

## Example

Spanning a tool (OpenTelemetry Python):

```python
from opentelemetry import trace

tracer = trace.get_tracer("mcp.tools")

@mcp.tool
async def render(scene: str) -> str:
    """Render a scene, traced end-to-end."""
    with tracer.start_as_current_span("tool.render") as span:
        span.set_attribute("tool", "render")
        try:
            result = await render_api.call(scene)      # instrumented downstream
            span.set_attribute("frames", result.frames)
            return result.text
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(exc)))
            raise
```

## Industry-standard pattern

W3C `tracecontext` + OpenTelemetry SDK + collector is the standard. Rules:
**propagate unconditionally** (dropping the id kills the trace), **span at every
boundary**, **record error status on failure**, and **sample at scale** (head/tail
sampling — [10-scaling-performance/tracing-at-scale.md](../10-scaling-performance/tracing-at-scale.md)).

## Common mistakes

- **Not propagating** — orphan spans with no parent.
- **One giant span** — no per-hop insight.
- **Missing error status** — the trace shows slowness, not failure.
- **Only server-side tracing** — the client and downstream must participate.
- **Trace ids not in logs** — logs and traces can't be joined.

## Testing

- **Span tests**: a tool call emits the expected span tree with attributes.
- **Propagation tests**: the trace id survives client → proxy → backend.
- **Error tests**: failures produce errored spans.

## Security considerations

- **Spans carry sensitive data** (arguments, URLs) — redact attributes and protect
  traces like logs ([14-security/auditability.md](../14-security/auditability.md)).
- **Trace injection**: forged `traceparent` headers can poison traces — treat them
  as untrusted metadata; enforce sampling at trusted edges.

## Related

- [structured-logging.md](structured-logging.md) · [metrics.md](metrics.md)
- [opentelemetry.md](opentelemetry.md)
- [08-reliability-resilience/distributed-tracing.md](../08-reliability-resilience/distributed-tracing.md)