# Failure Testing

## What is it?

**Failure testing** verifies what happens when things *go wrong*: invalid input,
tool errors, unexpected exceptions, malformed requests, timeouts, disconnects,
and crashes. It is the counterpart to happy-path testing — and where most MCP
bugs actually live.

## Why does MCP need it?

An agent that meets a failure it wasn't tested against does the worst possible
thing: it guesses. It retries a non-retryable call, reports a confusing error,
or silently proceeds with bad data
([04-tool-engineering/failure-handling.md](../04-tool-engineering/failure-handling.md)).
Failure tests turn "what happens if…" from a mystery into a verified behavior.

## How to test — the failure menu

| Failure | How to trigger | Assert |
|---------|---------------|--------|
| Validation error | call with wrong/missing args | clean error, session survives |
| Tool error | raise `ToolError` (or a fault toggle) | `isError` result with message |
| Unexpected exception | raise `RuntimeError` in a tool | converted to an MCP error, server alive |
| Unknown tool | call a name not listed | clean "unknown tool" error |
| Unknown resource/URI | read a bad URI | clean error ([05-resource-engineering/resource-templates.md](../05-resource-engineering/resource-templates.md)) |
| Timeout | slow tool + short client timeout | client times out, server still responds next call |
| Disconnect | kill the server mid-session | client reports connection loss, not a hang |
| Auth denial | no/invalid credentials | clean permission error ([14-security/examples](../14-security/examples)) |

## Example

```python
import pytest
from fastmcp import Client

@pytest.mark.asyncio
async def test_failures_do_not_kill_the_session():
    async with Client("hardened_server.py") as client:
        # 1. A tool failure is a clean error result.
        result = await client.call_tool("divide", {"a": 1, "b": 0},
                                        raise_on_error=False)
        assert result.isError

        # 2. The session is still alive afterwards.
        ok = await client.call_tool("ping")
        assert not ok.isError
```

## MCP-specific behavior

- Error *results* (`isError: true`) vs *raised exceptions* are different
  things; test both the wire shape and the client-visible behavior
  ([04-tool-engineering/errors.md](../04-tool-engineering/errors.md)).
- After any failure, the session must remain usable — a broken session is a
  critical bug. Always follow a failure call with a healthy call.

## Industry-standard pattern

**Chaos/fault-injection discipline**: give the server a fault toggle (a tool or
env var that makes a specific failure happen on demand) so every failure is
testable, repeatable, and inspectable
([08-reliability-resilience/failure-injection.md](../08-reliability-resilience/failure-injection.md)).

## Common mistakes

- Only testing the failure *result*, never that the *session survives*.
- Forgetting timeout/disconnect tests because they need async machinery.
- Asserting error messages are non-empty instead of checking they're useful.

## Related

- [resilience-testing.md](resilience-testing.md)
- [04-tool-engineering/failure-handling.md](../04-tool-engineering/failure-handling.md)
- [04-tool-engineering/timeouts.md](../04-tool-engineering/timeouts.md)
- Example: [04-tool-engineering/examples/test_hardened.py](../04-tool-engineering/examples/test_hardened.py)
