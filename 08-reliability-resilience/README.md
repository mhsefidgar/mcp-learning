# 08 — Reliability & Resilience

**What this section teaches.** How to make MCP systems survive failure: remote/proxy
failures, rate limiting, backpressure, caching, session recovery, fallback, partial
failures, exponential backoff with jitter, retry budgets, circuit breakers,
bulkheads, connection pooling, observability, distributed tracing, and failure
injection.

**Critical framing — read this first.** Almost everything in this section is a
**general distributed-systems pattern**, not an MCP feature. MCP gives you the
*request/response model*; resilience is what you build *around* it. The protocol
defines no retries, no circuit breakers, no rate limits. The distinction matters
because it tells you *where* to implement each pattern (in your client, server, proxy,
or infrastructure — not in the protocol).

**Prerequisites.** [01-fundamentals](../01-fundamentals/README.md),
[04-tool-engineering/retries.md](../04-tool-engineering/retries.md).

**Recommended reading order:**

1. [remote-proxy-failures.md](remote-proxy-failures.md) — the failure landscape
2. [rate-limiting.md](rate-limiting.md) · [backpressure.md](backpressure.md) — protect the server
3. [caching.md](caching.md) · [session-recovery.md](session-recovery.md) — recover cheaply
4. [fallback.md](fallback.md) · [partial-failures.md](partial-failures.md) — degrade gracefully
5. [exponential-backoff.md](exponential-backoff.md) · [retry-budgets.md](retry-budgets.md) · [circuit-breakers.md](circuit-breakers.md) — the retry stack
6. [bulkheads.md](bulkheads.md) · [connection-pooling.md](connection-pooling.md) — isolate and reuse
7. [observability.md](observability.md) · [distributed-tracing.md](distributed-tracing.md) — see it fail
8. [failure-injection.md](failure-injection.md) — make it fail on purpose

**Protocol vs. general engineering:**

| Pattern | MCP protocol feature? |
|---------|----------------------|
| Retries, backoff, jitter, retry budgets | ❌ general |
| Circuit breakers, bulkheads | ❌ general |
| Rate limiting, backpressure | ❌ general |
| Caching | ❌ general |
| Connection pooling | ❌ general |
| Session recovery | ⚠️ MCP sessions exist ([01-fundamentals/09-sessions-and-lifecycle.md](../01-fundamentals/09-sessions-and-lifecycle.md)); recovery logic is general |
| Observability, tracing | ❌ general (the `logging` capability is MCP's log channel) |

**Relevant examples:** `examples/` — a client with the full retry stack and a
fault-injecting mock server. **Relevant implementations:**
`repository/go/resilience`, `repository/rust/resilience`, `implementations/python-fastmcp`.

**Exercises.**

1. **Build the retry stack**: a client that retries with exponential backoff + jitter,
   a retry budget, and a circuit breaker. *Acceptance:* a flaky server succeeds; a
   dead server fails fast with a clean error ([circuit-breakers.md](circuit-breakers.md)).
2. **Add rate limiting** to a server. *Acceptance:* exceeding the limit returns a
   defined rate-limit error, not a crash ([rate-limiting.md](rate-limiting.md)).
3. **Inject failures**: make a downstream API fail 50% of the time; verify your
   retries/fallback behave ([failure-injection.md](failure-injection.md)).
4. **Simulate a session loss**: kill the server, restart it, and verify the client
   reconnects and recovers ([session-recovery.md](session-recovery.md)).

**Common mistakes in this section**

- Implementing resilience patterns *inside* tool handlers instead of at the
  client/proxy boundary (duplicated, untestable).
- Retry storms: no jitter, no budget ([exponential-backoff.md](exponential-backoff.md)).
- Rate limits that reject legitimate bursts; backpressure that drops instead of
  signaling ([backpressure.md](backpressure.md)).
- Caching mutable data without invalidation ([caching.md](caching.md)).