# Exponential Backoff + Jitter

> **General engineering pattern.** Backoff is not an MCP feature; it's the standard
> retry timing strategy.

## What is it?

**Exponential backoff** is waiting *exponentially longer* between retries: 1s, 2s,
4s, 8s… after each failure. **Jitter** is adding randomness to those waits so that
many retrying clients don't all wake up at the same instant. The two together are
the default retry policy of every serious distributed system.

## Why does MCP need it?

Without backoff, retries are a **thundering herd**: a server that hiccups gets hit
by every client's retry at the same moment, fails again, and the retries *cause* the
outage they're trying to survive. MCP systems are exactly this scenario — many
agents, many clients, retrying a shared server. Exponential backoff spreads the
retries; jitter prevents synchronization.

## How does it work?

```
attempt 1 fails → wait base * 2^0 (+ jitter) → retry
attempt 2 fails → wait base * 2^1 (+ jitter) → retry
attempt 3 fails → wait base * 2^2 (+ jitter) → retry
... capped at a max wait, and bounded by max attempts / total time
```

**Jitter options** (from the classic AWS article):

- **Full jitter**: `wait = random(0, min(cap, base * 2^attempt))` — most common,
  best for herd avoidance.
- **Equal jitter**: `wait = min(cap, base * 2^attempt)/2 + random(0, that/2)`.
- **No jitter**: `wait = min(cap, base * 2^attempt)` — fine for one client, fatal
  for a fleet.

## Mental model

Exponential backoff is a **crowded elevator after a fire alarm**: everyone waits,
but the schedule staggers who tries the door first (jitter), and the wait doubles so
the building has time to recover. Without jitter, everyone pushes the button at
once; without backoff, everyone keeps pushing every second.

## MCP-specific behavior

- **Nothing protocol-level** — backoff lives in your client/proxy retry logic.
- **Respect the server's hints**: a `429` with `Retry-After` should override your
  backoff schedule ([rate-limiting.md](rate-limiting.md)).
- **Backoff is only for retryable failures** — never back off-and-retry a
  non-retryable error ([04-tool-engineering/retries.md](../04-tool-engineering/retries.md)).

## Example

```python
import random, time

def backoff_delay(attempt: int, base: float = 0.5, cap: float = 8.0) -> float:
    """Full jitter: uniform random in [0, min(cap, base * 2^attempt)]."""
    exp = min(cap, base * (2 ** attempt))
    return random.uniform(0, exp)

# usage inside a retry loop
for attempt in range(max_attempts):
    try:
        return await client.call_tool(name, args)
    except RetryableError:
        if attempt == max_attempts - 1:
            raise
        await asyncio.sleep(backoff_delay(attempt))
```

Production-grade implementations (with budgets, circuit breakers, and tests) live
in `implementations/python-fastmcp` and `repository/go/resilience`.

## Industry-standard pattern

Backoff + jitter is standard in every SDK (AWS, Google, Stripe, gRPC). The
production rules: **cap the wait** (never 5-minute sleeps), **bound total time**
(retry budget, [retry-budgets.md](retry-budgets.md)), **add full jitter** for
fleet-wide safety, and **stop on non-retryable errors** immediately.

## Common mistakes

- **No jitter** — the herd forms anyway.
- **Uncapped backoff** — a 10-minute wait for a 2-second outage.
- **Retrying forever** — backoff without a max-attempt/total-time bound.
- **Backoff on non-retryable errors** — 4 pointless attempts at invalid params.
- **Ignoring `Retry-After`** — the server told you when to come back.

## Testing

- **Schedule tests**: delays follow the formula (fake clocks or assertions on the
  range) ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **Herd tests**: many simulated clients retrying together stay desynchronized.
- **Cap tests**: waits never exceed the cap; attempts never exceed the budget.
- **Interop tests**: `Retry-After` overrides the schedule.

## Security considerations

- **Backoff is a DoS mitigation**: a bounded, jittered schedule prevents retry
  storms from amplifying an outage.
- **Randomness must not be predictable enough to game** rate limits in
  security-sensitive paths (use proper jitter, not fixed offsets).

## Related

- [04-tool-engineering/retries.md](../04-tool-engineering/retries.md)
- [retry-budgets.md](retry-budgets.md)
- [circuit-breakers.md](circuit-breakers.md)
- [rate-limiting.md](rate-limiting.md)