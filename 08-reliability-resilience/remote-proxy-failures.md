# Remote/Proxy Failures

## What is it?

The **failure landscape** for remote and proxied MCP setups: every way a call can
fail when the server is another service, and the layers where failures appear.
Remote failures are *not like local failures*: they're slower, noisier, and
composed of many independent failure domains.

## The failure layers

```
Client ──► [network] ──► Proxy/Gateway ──► [network] ──► Backend MCP server
             │                │                    │
          DNS/TCP/TLS      auth/limits/         sessions/process/
          timeouts         config errors        crashes
```

| Layer | Failure examples |
|-------|------------------|
| Network | DNS failure, TCP reset, TLS handshake failure, dropped packets, latency spikes |
| HTTP | 429 (rate-limited), 502/503/504 (upstream down), 401/403 (auth), timeouts |
| Session | `Mcp-Session-Id` invalid/expired, server restarted, session lost ([01-fundamentals/09-sessions-and-lifecycle.md](../01-fundamentals/09-sessions-and-lifecycle.md)) |
| Proxy | forwarding timeouts, config errors, backend discovery failure |
| Backend | crash, OOM, deadlock, hung handler, partial startup |

## Why it matters

Each layer needs a **different response**: a DNS failure is retryable-after-backoff;
a 401 is not retryable at all; a hung backend needs a circuit breaker, not more
retries. The first skill of remote reliability is **classifying which layer failed**
before choosing the response.

## How to handle it

1. **Classify** the failure (see the table above; error codes + trace ids make this
   fast — [09-observability-telemetry/distributed-tracing.md](../09-observability-telemetry/distributed-tracing.md)).
2. **Choose the response per class**:
   - transient network/5xx → retry with backoff + jitter ([exponential-backoff.md](exponential-backoff.md))
   - rate-limited (429) → respect `Retry-After`, retry once, then back off
   - auth (401/403) → don't retry; refresh credentials ([14-security/authentication.md](../14-security/authentication.md))
   - hung backend → circuit breaker, not retries ([circuit-breakers.md](circuit-breakers.md))
   - session lost → re-initialize a fresh session ([session-recovery.md](session-recovery.md))
3. **Bound the damage**: timeouts everywhere
   ([04-tool-engineering/timeouts.md](../04-tool-engineering/timeouts.md)), retry
   budgets, and per-backend bulkheads ([bulkheads.md](bulkheads.md)).
4. **Degrade gracefully**: if the backend is down, return a clear error (or a
   cached/fallback answer) instead of hanging — [fallback.md](fallback.md).

## Common mistakes

- Treating every failure as the same (all-retry or all-fail).
- Retrying 401s (lockout risk) or non-idempotent calls without keys
  ([04-tool-engineering/retries.md](../04-tool-engineering/retries.md)).
- No timeout on forwarded calls — one slow backend hangs every client.
- Proxy errors that leak backend internals
  ([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)).

## Testing

- Build a **mock backend** that can fail in each layer (DNS, 429, 500, hang, crash)
  and assert the client's response to each — see
  [failure-injection.md](failure-injection.md) and `examples/`.

## Related

- [03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)
- [session-recovery.md](session-recovery.md)
- [circuit-breakers.md](circuit-breakers.md)
- [10-scaling-performance/proxy-gateway-scaling.md](../10-scaling-performance/proxy-gateway-scaling.md)