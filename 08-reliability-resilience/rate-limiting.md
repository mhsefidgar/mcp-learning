# Rate Limiting

> **General engineering pattern.** Rate limiting is not an MCP protocol feature. MCP
> defines no rate-limit fields; you implement limits at your server, proxy, or
> gateway (on HTTP, standard `429` + `Retry-After` apply).

## What is it?

**Rate limiting** caps how many requests a caller may make in a window — per client,
per tool, per IP, per token. It's the server's first line of defense against
runaway agents, buggy loops, and abuse.

## Why does MCP need it?

Agents are *amplifiers*: one model loop can fire dozens of tool calls per second,
and a multi-agent fleet multiplies that. An unthrottled server gets pounded by
legitimate traffic, let alone attacks. Rate limits protect:
- **Downstream systems** (a database, an external API) from burst load.
- **Cost** (each tool call may hit a paid API).
- **Fairness** (one tenant can't starve others).

## How does it work?

1. **Pick the scope**: per-client (token/principal), per-tool, per-session, or
   global.
2. **Pick the algorithm**: token bucket (allows bursts), fixed window, sliding
   window, or leaky bucket.
3. **Enforce at the boundary**: an HTTP server → `429 Too Many Requests` with
   `Retry-After`; an MCP server → a defined error result/JSON-RPC error that the
   model understands ("rate limited, try again in 30s").
4. **Count what matters**: requests per window (cheap) or *cost-weighted* units
   (a `render` call counts 100× a `ping`).

## Mental model

Rate limiting is a **bouncer at a venue**: X people per hour, door stays open for
steady flow, bursts get a short queue, and repeat offenders are turned away with a
"come back later" card (the `Retry-After`).

## MCP-specific behavior

- **MCP has no rate-limit fields** — implement at the transport (HTTP middleware,
  gateway) or in server middleware ([12-fastmcp/middleware.md](../12-fastmcp/middleware.md)).
- **Rate-limit errors must be model-actionable**: "rate limited — retry in 30s"
  beats a bare 429 the model can't parse. Respect `Retry-After` on the client side
  when retrying.
- **Per-tool quotas** are common: cheap tools get high limits, expensive/destructive
  ones get low limits ([10-scaling-performance/per-client-quotas.md](../10-scaling-performance/per-client-quotas.md)).

## Example

A token-bucket limiter in Python (see `repository/go/resilience` and
`repository/rust/resilience` for full implementations):

```python
import time
from dataclasses import dataclass

@dataclass
class TokenBucket:
    capacity: int      # max burst
    refill_per_sec: float
    tokens: float
    last: float

    def allow(self, now: float) -> bool:
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.refill_per_sec)
        self.last = now
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False
```

## Industry-standard pattern

Rate limiting is universal (nginx `limit_req`, cloud API quotas, Stripe/OpenAI
rate limits). Production additions: distributed counters (Redis) for multi-instance
servers, cost-weighted units, and per-tenant isolation
([10-scaling-performance/rate-limiting.md](../10-scaling-performance/rate-limiting.md)).

## Common mistakes

- **No limits at all** — the classic agent-loop incident.
- **Rejecting legitimate bursts** — token buckets tolerate bursts; fixed windows
  don't.
- **Non-actionable errors** — a bare 429 that makes the model retry instantly,
  forever.
- **Limiting per connection instead of per principal** — one user rotating sessions
  bypasses the limit.
- **Not telling the client when to retry** (`Retry-After`).

## Testing

- **Limit tests**: requests at/over the limit behave as defined
  ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **Burst tests**: bursts within capacity succeed.
- **Scope tests**: per-client limits don't leak across principals.
- **Cost-weight tests**: expensive tools exhaust the budget faster.

## Security considerations

- **Rate limiting is a DoS control** — without it, one caller can exhaust CPU,
  memory, connections, or downstream quotas.
- **Rate limiters are also attack surface**: a wrong key lookup (e.g. by IP behind
  a shared NAT) can block innocent users; use tokens/principal where possible.
- **429s leak policy** — don't reveal internal quotas in the error body.

## Related

- [backpressure.md](backpressure.md)
- [10-scaling-performance/rate-limiting.md](../10-scaling-performance/rate-limiting.md)
- [04-tool-engineering/retries.md](../04-tool-engineering/retries.md)
- [12-fastmcp/middleware.md](../12-fastmcp/middleware.md)