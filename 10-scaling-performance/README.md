# 10 — MCP Scaling & Performance

**What this section teaches.** How to take an MCP server from single-process to
fleet: scaling fundamentals (vertical/horizontal, stateless vs. stateful),
session-aware scaling and affinity, load balancing, connection management at scale,
concurrency and worker pools, quotas and backpressure under load, caching at scale,
large data, multi-server architectures and gateways, degradation and isolation,
performance engineering, observability at scale, and load/stress testing.

**Prerequisites.** [01-fundamentals](../01-fundamentals/README.md),
[08-reliability-resilience](../08-reliability-resilience/README.md).

**The one idea that drives everything:** the session-based protocol's *session state*
is the obstacle to horizontal scaling; the **2026-07-28 stateless spec removes it**.
Read [scaling-fundamentals.md](scaling-fundamentals.md) first — it explains why.

**Reading order:**

1. [scaling-fundamentals.md](scaling-fundamentals.md) — stateless vs. stateful, vertical vs. horizontal
2. [session-affinity.md](session-affinity.md) — sticky sessions and load balancing
3. [connection-management-at-scale.md](connection-management-at-scale.md) — connections, pooling
4. [concurrency-and-workers.md](concurrency-and-workers.md) — concurrency limits, worker pools, queues
5. [backpressure-and-quotas.md](backpressure-and-quotas.md) — rate limits, quotas, load shedding
6. [caching-at-scale.md](caching-at-scale.md) — distributed caching, invalidation
7. [large-data-at-scale.md](large-data-at-scale.md) — large resources, pagination, fan-out
8. [multi-server-and-gateway.md](multi-server-and-gateway.md) — multi-server architectures, gateways, discovery
9. [degradation-and-isolation.md](degradation-and-isolation.md) — graceful degradation, isolation, memory
10. [performance-engineering.md](performance-engineering.md) — CPU/IO, bottlenecks, latency, capacity, autoscaling
11. [observability-at-scale.md](observability-at-scale.md) — telemetry for fleets
12. [load-and-performance-testing.md](load-and-performance-testing.md) — load, stress, performance testing

**Protocol vs. engineering:** everything in this section is **general engineering**.
MCP's only contribution is the *session* (which complicates scaling) and the
stateless 2026-07-28 revision (which removes the complication).

**Exercises.**

1. **Statelessness audit**: take a server; find every piece of in-memory state;
   design where it should live (stateless handler + external store).
   *Acceptance:* two instances of the server can serve the same client
   interchangeably.
2. **Load balance**: run two server instances behind a load balancer; verify calls
   spread across them (session-based: with affinity; stateless: round-robin).
3. **Load test**: drive the server with a load-testing tool; find the concurrency
   limit and the p95 latency curve ([load-and-performance-testing.md](load-and-performance-testing.md)).
4. **Add a worker pool**: bound tool execution concurrency; verify throughput and
   memory stay flat under overload
   ([concurrency-and-workers.md](concurrency-and-workers.md)).

**Common mistakes in this section**

- Scaling stateless servers while keeping session state in memory (shared nothing
  breaks).
- Unbounded concurrency (threads/tasks) under agent bursts
  ([concurrency-and-workers.md](concurrency-and-workers.md)).
- Load testing on localhost with one client (measures nothing real).
- Ignoring memory: every request's result held longer than needed.