# Observability & Distributed Tracing at Scale

## What is it?

Observability when the server is a **fleet**: aggregated logs, fleet-wide metrics,
and traces that span many instances — plus the two scale-specific problems: **how
much to trace** (sampling) and **how to find the needle** (correlation).

## Why does MCP need it?

At scale, the questions change from "what is this instance doing?" to "what is the
system doing?":

- **Aggregation**: 50 instances' logs must be searchable as one corpus
  ([09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md)).
- **Fleet metrics**: error rate across all instances; which instance is the
  outlier ([09-observability-telemetry/metrics.md](../09-observability-telemetry/metrics.md)).
- **Tracing across hops**: an agent call that passes through gateway → backend → 
  downstream on different machines needs one joined trace
  ([09-observability-telemetry/distributed-tracing.md](../09-observability-telemetry/distributed-tracing.md)).

## How does it work?

1. **Ship everything centrally**: structured logs → log aggregator; metrics →
   Prometheus/OTLP; traces → collector ([09-observability-telemetry/opentelemetry.md](../09-observability-telemetry/opentelemetry.md)).
2. **Sample traces at scale**: 100% tracing is expensive at high throughput —
   head sampling (decide at the root) or tail sampling (keep the interesting ones:
   errors, slow calls).
3. **Correlate everything**: trace id in every log line, every span, every metric
   label — the one key that joins the fleet
   ([09-observability-telemetry/distributed-tracing.md](../09-observability-telemetry/distributed-tracing.md)).
4. **Fleet dashboards**: per-service error rates, p95 latency, queue depth,
   instance spread — alert on the fleet, not per instance.
5. **Per-instance drill-down**: when a fleet metric alerts, the trace id leads you
   to the exact logs/spans of the failing request.

## Mental model

Fleet observability is the **air-traffic control room**: you don't watch one plane
(logs per instance) — you watch the whole airspace (aggregated telemetry), with
every flight tagged by flight number (trace id) so you can zoom from the overview to
one plane's exact path.

## MCP-specific behavior

- **The natural fleet views**: per-server error rates, per-tool latency heatmaps,
  per-gateway backend health, session counts (session-based spec), and
  connection counts ([connection-management-at-scale.md](connection-management-at-scale.md)).
- **Nothing protocol-level** — this is your telemetry stack
  ([09-observability-telemetry/README.md](../09-observability-telemetry/README.md)).

## Example

Sampling decision (conceptual OTel config): keep all traces for errors and slow
calls; sample the rest at 10%.

```yaml
# otel collector tail-sampling policy (conceptual)
tail_sampling:
  policies:
    - name: keep-errors
      type: status_code
      status_code: { status_codes: [ERROR] }
    - name: keep-slow
      type: latency
      latency: { threshold_ms: 1000 }
    - name: sample-rest
      type: probabilistic
      probabilistic: { sampling_percentage: 10 }
```

## Industry-standard pattern

Centralized telemetry + sampling + trace-id correlation is the standard stack
(Jaeger/Tempo, Prometheus, Loki/ELK). Rules: **ship first, aggregate, then sample**;
**sample at the right layer**; **make every artifact joinable by trace id**; and
**alert on symptoms** (error rate, latency), not causes.

## Common mistakes

- **Tracing at 100% with no sampling** — cost explodes at scale.
- **Sampling before errors are captured** — you sample away the interesting traces
  (tail sampling keeps errors).
- **No aggregation** — 50 instances of logs nobody can search.
- **Trace ids not in logs** — the fleet is unjoinable.
- **Per-instance alerting** — noise; alert on fleet aggregates.

## Testing

- **Pipeline tests**: a request's trace + logs + metrics all land centrally
  (local collector in CI, [09-observability-telemetry/opentelemetry.md](../09-observability-telemetry/opentelemetry.md)).
- **Sampling tests**: error traces are never sampled away.
- **Join tests**: trace id links log lines, spans, and metric labels.

## Security considerations

- **Centralized telemetry is a honeypot** — protect it like the sensitive store it
  is; restrict access, redact attributes
  ([14-security/auditability.md](../14-security/auditability.md)).
- **Sampling must not drop audit-relevant traces** — keep errors and security
  events at 100%.

## Related

- [09-observability-telemetry/README.md](../09-observability-telemetry/README.md)
- [load-and-performance-testing.md](load-and-performance-testing.md)
- [multi-server-and-gateway.md](multi-server-and-gateway.md)
- [08-reliability-resilience/observability.md](../08-reliability-resilience/observability.md)