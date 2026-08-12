# Load Testing, Stress Testing & Performance Testing

> **General engineering practice.** Testing is not an MCP feature — but every
> scaling claim in this section should be backed by one of these.

## What is it?

Three related practices:

- **Performance testing**: measuring latency/throughput/resource usage of *defined*
  workloads (baseline: "100 calls/s at p95 50ms on 2 cores").
- **Load testing**: driving increasing load to find the *sustainability curve*
  (latency vs. concurrency) and the healthy operating range.
- **Stress testing**: pushing past the breaking point to find *how* the system
  fails — does it degrade, shed, or crash? Does it recover?

## Why does MCP need it?

Scaling claims without measurements are guesses. Load tests answer the questions
that matter for MCP servers:

- What concurrency can this server sustain? ([concurrency-and-workers.md](concurrency-and-workers.md))
- Where does latency start climbing? (the knee of the curve)
- What happens at 2× capacity — graceful degradation or OOM?
  ([degradation-and-isolation.md](degradation-and-isolation.md))
- What's the right autoscaling threshold?
  ([performance-engineering.md](performance-engineering.md))

## How does it work?

1. **Define the workload profile**: realistic agent traffic — bursts of parallel
   tool calls, mix of cheap/expensive tools, mixed read/write
   ([16-end-to-end/README.md](../16-end-to-end/README.md) for a realistic agent
   pattern).
2. **Choose the tool**: `locust`, `k6`, `hey`, `wrk` for HTTP; scripted MCP clients
   for protocol-level realism.
3. **Measure the pillars**: throughput (req/s), latency percentiles (p50/p95/p99),
   error rate, and server resources (CPU, memory, connections, queue depth).
4. **Find the knee**: ramp concurrency until latency/errors climb — that's your
   sustainable limit.
5. **Stress past it**: find the failure mode (shedding? OOM? hang?) and verify
   recovery after the load stops.
6. **Document and alert**: capacity numbers become autoscaling thresholds and
   alert baselines ([observability-at-scale.md](observability-at-scale.md)).

## Mental model

Load testing is the **treadmill test for the server**: walk (baseline), jog
(load), sprint (stress) — and record heart rate (latency), breathing (throughput),
and what happens at the wall (failure mode). You wouldn't prescribe exercise
without the test; don't set capacity without it.

## MCP-specific behavior

- **Test at the protocol level**: drive real MCP clients (many of them) rather
  than raw HTTP — tool-call semantics, sessions, and argument sizes change the
  profile.
- **Include session churn** (session-based spec): connect/disconnect load is as
  real as call load.
- **The 2026-07-28 stateless spec changes the profile**: no session state — load
  tests focus on request throughput and downstream capacity.

## Example

A k6-style HTTP smoke test (conceptual — adapt to your server):

```javascript
// k6 script (conceptual)
import http from "k6/http";

export const options = {
  scenarios: {
    ramp: { executor: "ramping-vus", startVUs: 0, stages: [
      { duration: "30s", target: 20 },
      { duration: "30s", target: 100 },
      { duration: "30s", target: 300 },
    ]},
  },
};

export default function () {
  const body = JSON.stringify({
    jsonrpc: "2.0", id: 1, method: "tools/call",
    params: { name: "search", arguments: { q: "test" } },
  });
  http.post("http://localhost:8000/mcp", body, {
    headers: { "Content-Type": "application/json",
               "Accept": "application/json, text/event-stream" },
  });
}
```

## Industry-standard pattern

Ramp testing, percentile analysis, and failure-mode discovery are standard (load
testing in CI, SRE capacity reviews). Rules: **test realistic workloads**, **ramp
gradually**, **record percentiles not averages**, **find the failure mode under
stress**, and **re-run after every significant change** (perf regression
detection).

## Common mistakes

- **Testing on localhost with one client** — measures nothing about the fleet.
- **Averages only** — p99 tells the real story.
- **No failure-mode investigation** — "it got slow" without knowing why (OOM?
  queue? downstream?).
- **Unrealistic workloads** — sequential single calls instead of agent bursts.
- **Not testing recovery** — what happens *after* the load stops matters
  (does the queue drain? do sessions recover?).

## Testing

- **Baseline tests in CI**: assert latency/throughput stay within budget on
  reference hardware.
- **Ramp tests**: the knee of the latency curve is documented.
- **Stress tests**: the failure mode is identified and recovery verified.
- **Regression tests**: perf tests run on every release
  ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).

## Security considerations

- **Load tests can look like attacks** (and vice versa) — run them against staging,
  not production, or use dedicated load-testing infrastructure.
- **Load-test artifacts reveal capacity** — protect them like other sensitive
  operational data.

## Related

- [performance-engineering.md](performance-engineering.md)
- [degradation-and-isolation.md](degradation-and-isolation.md)
- [concurrency-and-workers.md](concurrency-and-workers.md)
- [capstone/tests](../capstone/README.md)