# Circuit Breakers

> **General engineering pattern.** Circuit breakers are **not** an MCP primitive.
> They are a general resilience pattern you apply around MCP clients, servers,
> providers, or remote dependencies.

## What is it?

A **circuit breaker** stops calls to a failing dependency for a cooldown period, so
the dependency can recover and the system doesn't waste resources on calls that will
fail. Three states:

```
          failures > threshold            cooldown expires
  CLOSED ───────────────────────► OPEN ───────────────────────► HALF-OPEN
   (calls flow)                  (calls fail fast)              (trial calls)
      ▲                                                              │
      └────────────────── success on trial ─────────────────────────┘
                              (back to CLOSED)
```

- **CLOSED** — normal operation; failures are counted.
- **OPEN** — a threshold of recent failures tripped it; calls *fail fast* (no
  attempt) for a cooldown.
- **HALF-OPEN** — after cooldown, allow a few trial calls; success → CLOSED,
  failure → OPEN again.

## Why does MCP need it?

Retries alone make things *worse* on a dead dependency: every client retries into a
server that can't answer, wasting connections, CPU, and time — and the retry storm
can *keep* the server down. The circuit breaker answers "stop trying for a while" —
the dependency gets breathing room, and callers get an immediate, clean failure
instead of a slow, repeated one. For a gateway/proxy in front of MCP backends
([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)),
the breaker is often the difference between "one backend down" and "gateway down."

## How does it work?

1. **Track recent outcomes** (sliding window of success/failure).
2. **Trip**: failure rate (or count) exceeds threshold → OPEN.
3. **Fail fast**: while OPEN, calls return a defined "circuit open" error
   immediately — the model sees "backend temporarily unavailable" instantly.
4. **Cool down**, then **HALF-OPEN** with trial calls.
5. **Reset** on trial success (CLOSED) or re-trip (OPEN).

## Mental model

A circuit breaker is a **fuse in your house**: a fault blows the fuse, power to that
circuit is cut instantly (fail fast), and you reset the fuse after checking the
problem. It's also a **hotel that stops taking reservations when it's on fire** —
better to say "no rooms" immediately than to make guests wait for a no.

## MCP-specific behavior

- **Where it applies**: around *client → server* calls (a flaky remote server), and
  around *server → downstream* calls (a flaky database/API inside a tool).
- **The failure-fasting error must be model-actionable**: "service
  temporarily unavailable, try again in 60s" — the model will respect the hint or
  fall back ([fallback.md](fallback.md)).
- **Breakers pair with retries**: retries before the breaker trips; fail-fast after
  it trips; the retry budget caps the whole thing
  ([retry-budgets.md](retry-budgets.md)).

## Example

A minimal breaker (full implementations in `repository/go/resilience` and
`repository/rust/resilience`):

```python
import time

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, cooldown_s: float = 30.0):
        self.threshold = failure_threshold
        self.cooldown = cooldown_s
        self.failures = 0
        self.state = "closed"
        self.opened_at = 0.0

    def allow(self) -> bool:
        if self.state == "open" and time.monotonic() - self.opened_at >= self.cooldown:
            self.state = "half-open"          # trial mode
        return self.state != "open"

    def record_success(self) -> None:
        self.failures = 0
        self.state = "closed"

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.state = "open"
            self.opened_at = time.monotonic()
```

Usage:

```python
if not breaker.allow():
    raise ToolError("service temporarily unavailable — retry in ~60s")  # fail fast
try:
    result = await backend.call(...)
    breaker.record_success()
    return result
except BackendError:
    breaker.record_failure()
    raise
```

## Industry-standard pattern

Circuit breakers are standard (Netflix Hystrix/Resilience4j, gRPC, Polly). The
production rules: **trip on rate, not single failures**; **fail fast, don't queue**;
**half-open with limited trials**; **expose breaker state as a metric**; and **use
them around every remote dependency**, not just MCP peers.

## Common mistakes

- **Tripping on one failure** — flaky networks trip it constantly; use a window/rate.
- **Queuing while open** — that's a queue, not a breaker; fail fast.
- **No half-open state** — a breaker that stays open forever never recovers.
- **Retrying into an open breaker** — the breaker bypasses retries; don't re-add
  them.
- **No observability** — a tripped breaker is invisible until users complain.

## Testing

- **State-machine tests**: closed → open → half-open → closed transitions
  ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **Threshold tests**: exactly N failures trip it; N-1 don't.
- **Fail-fast tests**: open breaker returns instantly without calling the backend.
- **Recovery tests**: half-open trials succeed → closed.
- **Integration tests**: a dead mock backend → breaker trips → client gets clean
  errors → backend restored → recovers.

## Security considerations

- **Breakers are a DoS defense**: they stop retry storms from amplifying outages.
- **The "circuit open" error must not leak** why (which backend, what failure) —
  keep it generic.

## Related

- [04-tool-engineering/retries.md](../04-tool-engineering/retries.md)
- [retry-budgets.md](retry-budgets.md)
- [bulkheads.md](bulkheads.md)
- [observability.md](observability.md)