# Performance Engineering: Bottlenecks, Latency, Throughput, Capacity

## What is it?

The discipline of making an MCP server **fast and predictable**: knowing whether
your tools are **CPU-bound or I/O-bound**, finding **bottlenecks**, optimizing
**latency** (time per call) and **throughput** (calls per second), and planning
**capacity** (how much hardware for how much load) — including **autoscaling**.

## Why does MCP need it?

Agent UX is latency: a model turn that needs 5 tool calls takes 5× the slowest
call. Throughput decides how many agents one server can serve. And capacity
planning is how you avoid both over-provisioning (waste) and surprise outages
(under-provisioning). None of this is MCP-specific — but MCP servers have a
specific profile worth understanding.

## The MCP performance profile

- **Tools are the hot path**: the protocol layer is cheap; the tool's work decides
  everything.
- **CPU-bound tools** (parsing, transforms, ML): parallelize across cores; watch
  GIL (Python) / worker threads; consider offloading to native code.
- **I/O-bound tools** (APIs, databases, files): the bottleneck is waiting — use
  async I/O, connection pooling ([connection-management-at-scale.md](connection-management-at-scale.md)),
  and caching ([caching-at-scale.md](caching-at-scale.md)).
- **Serialization is a real cost**: large JSON payloads dominate latency; keep
  results small ([04-tool-engineering/structured-output.md](../04-tool-engineering/structured-output.md)).

## How does it work?

1. **Measure** (load testing, [load-and-performance-testing.md](load-and-performance-testing.md)):
   latency percentiles, throughput, resource usage.
2. **Find the bottleneck**: profile — is it CPU, I/O, locks, memory, GC, or the
   downstream?
3. **Fix the dominant term first**: a tool that waits on a slow API is fixed by
   caching/parallelism, not by a faster server.
4. **Optimize latency**: reduce serialization, parallelize independent work within a
   tool, cache hot data, avoid sync-in-async.
5. **Optimize throughput**: bounded concurrency
   ([concurrency-and-workers.md](concurrency-and-workers.md)), connection reuse,
   horizontal scaling once a single box is tuned
   ([scaling-fundamentals.md](scaling-fundamentals.md)).
6. **Plan capacity**: model load (agents × calls/turn × turns), size instances,
   set autoscaling on the measured metric (queue depth, CPU, latency).
7. **Autoscale**: add instances when the queue grows, remove when idle — with
   graceful drain for session-based servers
   ([session-affinity.md](session-affinity.md)).

## Mental model

Performance engineering is **finding the widest bottleneck in a water pipe**:
latency is the time a drop takes, throughput is the flow rate, and capacity is the
size of the reservoir. Widening the wrong section of pipe changes nothing — measure
first, widen the real bottleneck.

## MCP-specific behavior

- **Nothing protocol-level**; but two MCP-specific opportunities:
  - **Catalog caching** is nearly free throughput
    ([caching-at-scale.md](caching-at-scale.md)).
  - **The stateless 2026-07-28 spec** removes session overhead from the fleet
    ([scaling-fundamentals.md](scaling-fundamentals.md)).

## Example

Latency diagnosis flow for a slow tool:

```
tool "render" takes 3.0s
 ├─ 0.05s dispatch/validation      (cheap — ignore)
 ├─ 0.10s serialization            (cheap — ignore)
 └─ 2.85s POST /render-api         (I/O bound → the bottleneck)
     → fix: parallelize? cache results? reduce payload? timeout/retry config?
```

## Industry-standard pattern

Profile → fix the dominant term → load test → capacity plan → autoscale is the
standard loop (APM profiling, load testing, SRE capacity reviews). Rules: **percentiles
not averages**, **one bottleneck at a time**, **load-test before tuning in
production**, and **autoscale on queue depth/latency, not just CPU**.

## Common mistakes

- **Optimizing the wrong layer** — protocol micro-optimizations while tools wait on
  slow downstreams.
- **Averages** — p99 tells the real story.
- **Sync I/O in async handlers** — blocks the whole loop
  ([concurrency-and-workers.md](concurrency-and-workers.md)).
- **No load tests** — capacity planned from guesses
  ([load-and-performance-testing.md](load-and-performance-testing.md)).
- **Autoscaling on CPU only** — an I/O-bound server idles on CPU while latency
  explodes.

## Testing

- **Load tests** for latency/throughput curves
  ([load-and-performance-testing.md](load-and-performance-testing.md)).
- **Bottleneck tests**: profiling asserts the dominant cost is where you think.
- **Autoscaling tests**: load increases → instances scale; drains gracefully.

## Security considerations

- **Performance data is sensitive** (traffic volumes, capacity) — protect load-test
  results and metrics endpoints.
- **Optimization must not skip validation** — a "fast path" that bypasses checks is
  a security bug.

## Related

- [load-and-performance-testing.md](load-and-performance-testing.md)
- [concurrency-and-workers.md](concurrency-and-workers.md)
- [connection-management-at-scale.md](connection-management-at-scale.md)
- [scaling-fundamentals.md](scaling-fundamentals.md)