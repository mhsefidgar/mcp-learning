# Retry Budgets

> **General engineering pattern.** Retry budgets are not an MCP feature — they're
> the global cap that keeps per-request retries from becoming system-wide storms.

## What is it?

A **retry budget** is a global limit on retry activity: "no more than X retries per
window across all clients/calls" — or, per client, "no more than N total retry time
per operation." Per-request retry policies ([exponential-backoff.md](exponential-backoff.md))
control one call; the budget controls the *fleet*. Without it, 100 clients × 6
retries = 600 attempts at a down server.

## Why does MCP need it?

Retries are a **load multiplier**: every retry is a new request hitting the server,
its downstreams, and its rate limits. A retry budget is the accounting that keeps
the multiplier bounded:

- **Per operation**: total time/attempts allowed before giving up (the request
  budget).
- **Per client**: retry rate limit (don't let one agent's retries dominate).
- **Global**: fleet-wide retry cap (circuit breakers at the server help here too —
  [circuit-breakers.md](circuit-breakers.md)).

## How does it work?

1. **Budget per operation**: `max_attempts` and/or `max_total_time` (a deadline, not
   just a count — [04-tool-engineering/timeouts.md](../04-tool-engineering/timeouts.md)).
2. **Budget per client**: a token-bucket on *retry attempts* (retries are metered
   like normal traffic).
3. **Budget globally (optional)**: an adaptive cap — if the server is failing,
   *reduce* the retry rate fleet-wide (dynamic, e.g. based on error rate).

## Mental model

A retry budget is a **household budget for "try again"**: each attempt costs a
coin, the jar has a finite number of coins per day, and when the jar is empty you
stop trying (and fix the real problem instead). Per-request rules say *how* to
retry; the budget says *whether you're allowed to at all*.

## MCP-specific behavior

- **Nothing protocol-level** — budgets are client/proxy policy.
- **Interacts with rate limiting**: a server's `429` is the budget's enforcement
  from the other side ([rate-limiting.md](rate-limiting.md)).
- **Server-side protection**: a server should also bound *its* work (per-call
  execution timeouts) so retries can't pile up inside it.

## Example

Per-operation budget as a deadline (conceptual):

```python
deadline = time.monotonic() + 30.0   # 30s total budget, not 30s per attempt
attempt = 0
while time.monotonic() < deadline:
    try:
        return await client.call_tool(name, args)
    except RetryableError:
        attempt += 1
        await asyncio.sleep(min(backoff_delay(attempt), deadline - time.monotonic()))
raise TimeoutError(f"gave up after {attempt} attempts")
```

## Industry-standard pattern

Budgets are standard in production retry stacks (gRPC's retry budget, AWS SDKs'
max-attempts, Netflix's adaptive concurrency limits). The rules: budget counts *time
and attempts*, budgets are shared (not per-request), and when the budget is spent,
**fail fast** — don't let one operation eat the fleet's retries.

## Common mistakes

- **Only counting attempts, not time** — a "3 attempts" policy with huge backoffs
  can still wait 10 minutes.
- **Per-request budgets only** — 1,000 requests × 3 attempts still hammers the
  server.
- **No global view** — no one knows the fleet is collectively retrying.
- **Budget spent but still retrying** — the budget must be *enforced*, not
  advisory.

## Testing

- **Budget exhaustion tests**: the operation gives up at the boundary
  ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **Fleet-simulation tests**: N clients retrying share the global budget.
- **Fail-fast tests**: when the budget is gone, new operations fail immediately
  rather than queuing retries.

## Security considerations

- **Budgets are a DoS control**: bounded retries mean a coordinated attack can't
  amplify itself through retries.
- **Budget exhaustion should alert** — a fleet spending its retry budget is a
  signal (observability, [observability.md](observability.md)).

## Related

- [04-tool-engineering/retries.md](../04-tool-engineering/retries.md)
- [exponential-backoff.md](exponential-backoff.md)
- [circuit-breakers.md](circuit-breakers.md)
- [rate-limiting.md](rate-limiting.md)