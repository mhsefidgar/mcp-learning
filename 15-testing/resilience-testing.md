# Resilience Testing

## What is it?

**Resilience testing** verifies that an MCP system keeps working (or fails
gracefully) under real-world pressure: flaky servers, slow responses, crashes,
and load. Where [failure-testing.md](failure-testing.md) checks *single*
failures, resilience testing checks *patterns*: retries, backoff, circuit
breakers, recovery, and degradation
([08-reliability-resilience/README.md](../08-reliability-resilience/README.md)).

## Why does MCP need it?

MCP clients and servers sit on networks — and networks fail, servers get
overloaded, and dependencies go down. A client that cannot survive a flaky
server is a client that bricks the agent mid-task. Resilience testing proves the
resilience machinery (retry loops, circuit breakers, fallbacks) actually engages
when it should — and, just as importantly, *disengages* when the system
recovers.

## How to test — the resilience menu

1. **Retry**: a tool fails N times then succeeds → the client retries and
   returns the success ([08-reliability-resilience/exponential-backoff.md](../08-reliability-resilience/exponential-backoff.md)).
2. **No retry on non-retryable errors**: a validation error is *not* retried —
   the retry policy must classify errors
   ([04-tool-engineering/retries.md](../04-tool-engineering/retries.md)).
3. **Circuit breaker**: repeated failures trip the breaker → subsequent calls
   fail fast without hitting the server; after cooldown, half-open probes and
   recovery works ([08-reliability-resilience/circuit-breakers.md](../08-reliability-resilience/circuit-breakers.md)).
4. **Timeout + recovery**: a slow call times out client-side, but the *next*
   call works (the session survived).
5. **Disconnect/reconnect**: the server dies mid-session → the client detects
   it and can establish a fresh session
   ([08-reliability-resilience/session-recovery.md](../08-reliability-resilience/session-recovery.md)).
6. **Backpressure**: a flood of calls → the client/server applies limits
   without crashing ([08-reliability-resilience/backpressure.md](../08-reliability-resilience/backpressure.md)).

## Example

```python
import asyncio
from fastmcp import Client
from resilient_client import resilient_call   # retries + breaker (see section 08)

async def test_retry_then_success():
    async with Client("faulty_server.py") as client:
        # faulty_server fails the first 2 calls, succeeds on the 3rd
        result = await resilient_call(client, "flaky")
        assert result == "ok after 2 failures"

async def test_breaker_fails_fast():
    async with Client("faulty_server.py") as client:
        with pytest.raises(Exception):          # breaker is open
            await resilient_call(client, "dead")
        # and it recovers once the server is healthy again
```

See [08-reliability-resilience/examples/test_resilience.py](../08-reliability-resilience/examples/test_resilience.py)
for a complete, running version.

## MCP-specific behavior

- Resilience patterns (retries, breakers, backpressure) are **general
  engineering**, not MCP protocol features
  ([08-reliability-resilience/README.md](../08-reliability-resilience/README.md)).
  Testing them is the same regardless of transport.
- Session semantics matter: after a disconnect, the client must re-run
  `initialize` for a new session — resilience tests should exercise that path
  ([01-fundamentals/09-sessions-and-lifecycle.md](../01-fundamentals/09-sessions-and-lifecycle.md)).

## Industry-standard pattern

**Failure injection + golden scenarios**: control the failure (a fault toggle),
run the scenario, assert on observable behavior — including timing bounds
(backoff grows, breaker trips after N failures) without depending on exact
sleep durations. Make the delays configurable in tests (milliseconds) so the
suite is fast and deterministic
([08-reliability-resilience/failure-injection.md](../08-reliability-resilience/failure-injection.md)).

## Common mistakes

- Testing retries with real sleeps — slow and flaky; inject a clock or shorten
  delays.
- Testing that retries *happen* but not that non-retryable errors *don't*
  retry (the retry storm bug).
- Testing the breaker trips but not that it recovers.

## Related

- [failure-testing.md](failure-testing.md)
- [08-reliability-resilience/README.md](../08-reliability-resilience/README.md)
- [08-reliability-resilience/examples/test_resilience.py](../08-reliability-resilience/examples/test_resilience.py)
- [10-scaling-performance/load-and-performance-testing.md](../10-scaling-performance/load-and-performance-testing.md)
