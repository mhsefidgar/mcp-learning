# Retries

> **General engineering pattern.** Retries are *not* an MCP protocol feature. MCP
> defines no retry semantics; you implement retries around your client calls,
> around your server's calls to downstream services, or around tool execution.

## What is it?

**Retrying** is re-attempting a failed operation, in the hope that a transient
failure (network blip, timeout, busy downstream) succeeds on a second try. The
engineering question is *which* failures to retry, *how many* times, and *how fast*.

## Why does MCP need it?

MCP traffic crosses networks and processes: remote servers go down briefly, HTTP
connections reset, load balancers reroute, downstream APIs hiccup. Without retries, a
5-second blip becomes a failed agent run. With naive retries, a *persistent* failure
becomes a thundering herd of duplicate calls. Retry policy is how MCP systems stay
alive through transient chaos.

## How does it work?

1. **Classify the failure**: retryable (network error, timeout, 5xx, `-32603`
   internal errors) vs. non-retryable (invalid params `-32602`, auth errors,
   `isError` semantic failures like "not found"). **Never retry what won't succeed.**
2. **Choose the policy**: max attempts, delay between attempts
   ([08-reliability-resilience/exponential-backoff.md](../08-reliability-resilience/exponential-backoff.md)),
   and **jitter** to avoid synchronized retry storms.
3. **Check idempotency**: retrying a non-idempotent call can duplicate effects —
   retry only if safe or if you carry an idempotency key
   ([idempotency.md](idempotency.md)).
4. **Give up gracefully**: exhaust attempts → return a clean final error to the
   caller (the model can then try a different approach).

### Retryable vs non-retryable errors

| Error | Retry? | Why |
|-------|--------|-----|
| Network / connection reset | ✅ | transient by nature |
| Timeout | ✅ (bounded) | could be transient load |
| HTTP 429 / 503 | ✅ | "try later" is explicit |
| `-32603` internal error | ⚠️ | maybe — depends on cause |
| `-32602` invalid params | ❌ | same params will fail again |
| auth / 401 / 403 | ❌ | fix credentials, not timing |
| `isError: true` ("not found") | ❌ | semantic, won't change |
| `-32601` method not found | ❌ | permanent |

## Mental model

Retries are **asking twice before giving up — but only when the answer might
change**. The classification step is the intelligence: retry transient "maybe the
network hiccuped" failures; never retry deterministic "the answer is no" failures.
And always ask "what happens if both calls succeed?" (idempotency).

## MCP-specific behavior

- **Where retries live**:
  - **Client side**: wrap `client.call_tool(...)` / TS `client.callTool` in a retry
    helper (transient transport failures).
  - **Server side**: your tool calls downstream APIs — wrap those in retries.
  - **Proxy side**: forwarded calls to backends get retries
    ([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)).
- **The protocol has no retry headers/fields** — a client cannot tell a server
  "retry this". Retry is purely local policy.
- **Cancellation and retries interact**: if the client cancelled, don't retry
  ([cancellation.md](cancellation.md)).

## Example

Client-side retry with backoff (Python, using `tenacity` — the standard library for
this):

```python
from tenacity import (
    retry, stop_after_attempt, wait_exponential, retry_if_exception_type,
)

RETRYABLE = (ConnectionError, TimeoutError)  # transport-level failures

@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=0.5, max=8),  # 0.5s, 1s, 2s, 4s... + jitter
    retry=retry_if_exception_type(RETRYABLE),
)
async def call_tool_with_retry(client, name: str, arguments: dict):
    return await client.call_tool(name, arguments)
```

Full implementations with jitter and retry budgets live in
`implementations/python-fastmcp` and `repository/go/resilience`.

## Industry-standard pattern

Retries with exponential backoff + jitter are universal (AWS SDKs, Stripe, gRPC).
The production-grade additions: **retry budgets** (a global cap on retry attempts per
window so storms can't form), **circuit breakers** (stop retrying into a dead
service), and **idempotency keys** (make retries safe). See
[08-reliability-resilience/README.md](../08-reliability-resilience/README.md) for the
full resilience stack.

## Common mistakes

- **Retrying everything** — including non-retryable and semantic failures.
- **No jitter** — synchronized retries create thundering herds that take services
  down ([08-reliability-resilience/jitter.md](../08-reliability-resilience/jitter.md)).
- **Infinite retries** — cap attempts *and* total time.
- **Retrying non-idempotent operations** without keys — duplicate orders, duplicate
  emails.
- **Retrying after cancellation** — work that was cancelled must stay cancelled.

## Testing

- **Retry-count tests**: a flaky mock that fails twice then succeeds → exactly 3
  attempts ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **Non-retryable tests**: invalid params are attempted exactly once.
- **Backoff tests**: delays follow the policy (measure with fake clocks).
- **Budget tests**: the retry budget is exhausted → clean final error.

## Debugging

- Count attempts in logs: too many → policy too aggressive or failure not
  transient; exactly one → policy too timid or failure non-retryable.
- Distinguish *where* the retry happened (client transport vs. server downstream) —
  trace ids help ([09-observability-telemetry/distributed-tracing.md](../09-observability-telemetry/distributed-tracing.md)).

## Security considerations

- **Retries amplify load** — rate-limit and budget them
  ([08-reliability-resilience/rate-limiting.md](../08-reliability-resilience/rate-limiting.md)).
- **Retry storms are a DoS vector**: jitter + budgets + circuit breakers.
- **Never retry security failures** (auth failures) — lockout/brute-force risks.

## Related concepts

- [idempotency.md](idempotency.md)
- [timeouts.md](timeouts.md)
- [08-reliability-resilience/exponential-backoff.md](../08-reliability-resilience/exponential-backoff.md)
- [08-reliability-resilience/retry-budgets.md](../08-reliability-resilience/retry-budgets.md)
- [08-reliability-resilience/circuit-breakers.md](../08-reliability-resilience/circuit-breakers.md)