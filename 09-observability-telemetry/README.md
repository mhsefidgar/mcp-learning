# 09 — Observability & Telemetry

**What this section teaches.** The three pillars of production observability —
**structured logging**, **metrics**, and **distributed tracing** — and how to apply
them to MCP servers and clients, with OpenTelemetry as the vendor-neutral standard.

**Prerequisites.** [01-fundamentals](../01-fundamentals/README.md),
[08-reliability-resilience/observability.md](../08-reliability-resilience/observability.md).

**Framing.** Observability is **general engineering**, not an MCP feature. MCP
contributes two small protocol pieces — the `logging` capability
(`logging/setLevel` + `notifications/message`) and `_meta` for carrying metadata —
but the discipline (JSON logs, OTLP, trace propagation) is the same as for any
distributed system.

**Recommended reading order:**

1. [structured-logging.md](structured-logging.md) — the foundation
2. [metrics.md](metrics.md) — the trends
3. [distributed-tracing.md](distributed-tracing.md) — the journeys
4. [opentelemetry.md](opentelemetry.md) — the standard plumbing

**Exercises.**

1. **Structured logging**: add JSON logging to a server (every tool call: method,
   outcome, duration, trace id). *Acceptance:* logs parse as JSON and contain the
   documented fields; secrets are redacted
   ([structured-logging.md](structured-logging.md)).
2. **Metrics**: instrument tool calls (counters by tool/outcome, latency histogram).
   *Acceptance:* a metric endpoint shows call volume and error rate.
   ([metrics.md](metrics.md)).
3. **Tracing**: add OpenTelemetry spans to a tool call (server + downstream).
   *Acceptance:* a trace shows the full call path with per-span timings
   ([distributed-tracing.md](distributed-tracing.md)).

**Common mistakes in this section**

- Prose logs (unparseable) — always JSON with a fixed field set.
- Logging secrets/PII raw — redact by default
  ([structured-logging.md](structured-logging.md)).
- Logs without trace ids — uncorrelatable across hops
  ([distributed-tracing.md](distributed-tracing.md)).
- Metrics without labels (tool, outcome) — useless for diagnosing which tool is
  slow.