# Backpressure, Rate Limits & Per-Client Quotas Under Load

## What is it?

The admission-control layer of a busy MCP server, from three angles:

- **Backpressure**: signal producers to slow down when work exceeds capacity
  ([08-reliability-resilience/backpressure.md](../08-reliability-resilience/backpressure.md)).
- **Rate limiting**: cap requests per window
  ([08-reliability-resilience/rate-limiting.md](../08-reliability-resilience/rate-limiting.md)).
- **Per-client / per-tool quotas**: differentiated limits — cheap tools get high
  limits, expensive/destructive ones get low limits; heavy tenants get less than
  light ones.

## Why does MCP need it?

Under load, the difference between a graceful server and a collapsing one is
admission control. Unbounded admission means: memory exhaustion, downstream pounded,
all tenants degraded. Quotas add *fairness*: one agent's runaway loop shouldn't
starve everyone else — and one `delete_all` call shouldn't carry the cost of 10,000
`ping`s.

## How does it work?

1. **Backpressure**: bounded queue + busy signal when full (see
   [08-reliability-resilience/backpressure.md](../08-reliability-resilience/backpressure.md)).
2. **Rate limiting**: token bucket per scope (client, IP, session) —
   [08-reliability-resilience/rate-limiting.md](../08-reliability-resilience/rate-limiting.md).
3. **Quotas**: cost-weighted budgets — each tool declares a cost (`ping=1`,
   `render=100`), each client has a budget per window; a call is denied when the
   budget is exhausted.
4. **Load shedding**: when the server itself is saturated, shed *cheap, safe* work
   (or the least important) first — reject new requests before the queue explodes
   ([degradation-and-isolation.md](degradation-and-isolation.md)).

## Mental model

Admission control is the **airport's gate system**: capacity is the runway count;
rate limits are the boarding rules per airline; quotas are each airline's slot
allocation; load shedding is ground-stop — when the airport is saturated, everyone
waits on the ground instead of stacking in the sky (queues exploding).

## MCP-specific behavior

- **Nothing protocol-level** — limits live at the HTTP layer, in middleware, or in a
  gateway ([12-fastmcp/middleware.md](../12-fastmcp/middleware.md)).
- **The signal must be model-actionable**: "quota exhausted, resets in 60s" — the
  model will wait or reroute ([08-reliability-resilience/fallback.md](../08-reliability-resilience/fallback.md)).
- **Per-tool quotas pair with annotations**: `destructiveHint`/expensive tools get
  the tightest quotas ([04-tool-engineering/annotations.md](../04-tool-engineering/annotations.md)).

## Example

A cost-weighted quota (conceptual):

```python
TOOL_COST = {"ping": 1, "search": 5, "render": 100, "delete_all": 1000}
BUDGET_PER_WINDOW = 1000   # per client, per window

async def check_quota(client_id: str, tool: str) -> None:
    cost = TOOL_COST[tool]
    used = await redis.get(f"quota:{client_id}")
    if used + cost > BUDGET_PER_WINDOW:
        raise ToolError(f"quota exhausted (budget {BUDGET_PER_WINDOW}) — retry later")
    await redis.incrby(f"quota:{client_id}", cost)
```

## Industry-standard pattern

Cost-weighted quotas and load shedding are standard in cloud APIs (per-tier rate
limits, cost-based billing, cloud "shed low-priority work first"). Rules: **weight
by cost, not just count**; **share limits across instances** (distributed counters);
**deny with a clear retry hint**; and **shed gracefully** — never drop silently.

## Common mistakes

- **Count-only limits** — a `render` call counted the same as `ping`.
- **Per-instance limits** — a fleet of N instances multiplies the effective limit
  N×; use a shared counter (Redis).
- **Silent shedding** — dropped requests with no signal the model can act on.
- **Quota denial that looks like a bug** — make "quota" explicit in the error.

## Testing

- **Quota tests**: exhausting the budget denies with the defined error
  ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **Fairness tests**: one client's burst doesn't starve another's budget.
- **Cost-weight tests**: one `render` costs more than 10 `ping`s.
- **Shedding tests**: under saturation, the server stays alive and sheds safely.

## Security considerations

- **Quotas are a DoS control and a cost control** — they bound what one (possibly
  compromised) agent can spend.
- **Quota state is per-principal** — key by authenticated identity, not IP
  ([08-reliability-resilience/rate-limiting.md](../08-reliability-resilience/rate-limiting.md)).

## Related

- [08-reliability-resilience/rate-limiting.md](../08-reliability-resilience/rate-limiting.md)
- [08-reliability-resilience/backpressure.md](../08-reliability-resilience/backpressure.md)
- [degradation-and-isolation.md](degradation-and-isolation.md)
- [04-tool-engineering/annotations.md](../04-tool-engineering/annotations.md)