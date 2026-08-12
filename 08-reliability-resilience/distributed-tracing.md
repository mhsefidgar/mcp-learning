# Distributed Tracing

> **General engineering pattern.** Tracing is not an MCP feature — it's the
> OpenTelemetry-style practice of following one logical operation across many
> services (see [09-observability-telemetry/distributed-tracing.md](../09-observability-telemetry/distributed-tracing.md)).

## What is it?

**Distributed tracing** tracks one logical request across every service boundary it
crosses: client → MCP server → tool → downstream API → database. Each hop creates a
**span**; spans chain into a **trace** identified by a **trace id** propagated via
headers (W3C `traceparent`).

## Why does MCP need it?

MCP calls are naturally multi-hop: an agent calls a tool, the tool calls an API,
which calls a database. When something is slow or wrong, the questions are "which
hop?" and "where's the time going?" — unanswerable without tracing. Tracing is what
makes a 3-second tool call explainable: 0.1s in dispatch, 2.7s in the downstream
API, 0.2s in serialization.

## How does it work?

1. **Generate**: the entry point (agent client, or gateway) creates a trace id and
   the root span.
2. **Propagate**: the trace id travels with the request — in HTTP headers
   (`traceparent`) at the transport, in `_meta` where the protocol allows, or in
   your own envelope fields.
3. **Span**: each service creates a child span (client → server → tool → downstream),
   recording start/end, status, and attributes.
4. **Export**: spans go to a collector (Jaeger, Tempo, Honeycomb) via OpenTelemetry.

```
trace 4bf92f…
 ├─ span: agent.call_tool("render")         client
 │   └─ span: server.tools/call             mcp server
 │       └─ span: tool.render               handler
 │           └─ span: POST /render-api      downstream HTTP
```

## Mental model

Tracing is a **receipt trail through a maze**: each room you enter stamps your
receipt with entry/exit times; at the end you can reconstruct exactly where the
time went. Logs are the diary of one room; the trace is the full itinerary.

## MCP-specific behavior

- **Nothing protocol-level** (the session-based spec has no trace fields; carry the
  id in `_meta` or transport headers, or use the newer spec's metadata).
- **The natural correlation points**: per `tools/call` (one span), per tool handler
  (child span), per downstream call (grandchild spans), per proxy hop
  ([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)).
- **Middleware is the place to add spans** — one middleware can span every request
  ([12-fastmcp/middleware.md](../12-fastmcp/middleware.md)).

## Example

Spanning a tool call with OpenTelemetry (conceptual — see
`repository/go/resilience` for a Go example and
[09-observability-telemetry/distributed-tracing.md](../09-observability-telemetry/distributed-tracing.md)):

```python
from opentelemetry import trace

tracer = trace.get_tracer("mcp.tools")

@mcp.tool
async def render(scene: str) -> str:
    """Render a scene, traced end-to-end."""
    with tracer.start_as_current_span("tool.render") as span:
        span.set_attribute("tool", "render")
        span.set_attribute("scene", scene)
        result = await render_api.call(scene)   # downstream span via instrumentation
        span.set_attribute("frames", result.frames)
        return result.text
```

## Industry-standard pattern

W3C `tracecontext` propagation + OpenTelemetry SDKs + a collector is the standard
stack. Rules: **propagate everywhere** (a dropped trace id kills the trace),
**span at service boundaries**, **record meaningful attributes** (tool name, outcome,
error), and **sample wisely** (head or tail sampling at scale —
[10-scaling-performance/distributed-tracing-at-scale.md](../10-scaling-performance/distributed-tracing-at-scale.md)).

## Common mistakes

- **Not propagating the id** — orphan spans that can't be linked.
- **One giant span** for the whole call — no insight into which hop was slow.
- **No error attributes** — the trace shows failure but not why.
- **Tracing only the server** — the client and downstream must participate too.
- **Logging the trace id inconsistently** — logs and traces must correlate.

## Testing

- **Span tests**: a tool call produces the expected span tree with attributes
  ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **Propagation tests**: the trace id survives client → proxy → backend hops.
- **Error tests**: failures mark spans as errored with the right status.
- **Sampling tests**: sampling config respects budgets at scale.

## Security considerations

- **Trace data is sensitive**: spans capture arguments and downstream URLs — redact
  and protect traces like logs
  ([14-security/auditability.md](../14-security/auditability.md)).
- **Trace ids can be forged/spoofed** (trace poisoning) — treat inbound trace
  headers as untrusted metadata, and enforce sampling at trusted edges.

## Related

- [observability.md](observability.md)
- [09-observability-telemetry/distributed-tracing.md](../09-observability-telemetry/distributed-tracing.md)
- [remote-proxy-failures.md](remote-proxy-failures.md)
- [12-fastmcp/middleware.md](../12-fastmcp/middleware.md)