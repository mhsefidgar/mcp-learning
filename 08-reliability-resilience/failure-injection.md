# Failure Injection

> **General engineering pattern.** Failure injection (chaos engineering) is not an
> MCP feature — it's how you *prove* your resilience patterns work.

## What is it?

**Failure injection** is deliberately making components fail — in tests or in
production (chaos engineering) — to verify the system's resilience behavior. For MCP
that means: a mock server that returns errors, a tool that times out on command, a
downstream API that fails 50% of the time, a proxy that drops connections.

## Why does MCP need it?

Resilience code is only trustworthy if *proven*: a retry policy that has never seen
a failure, a circuit breaker that has never tripped, a session-recovery path that
has never reconnected — these are untested claims. Failure injection is how you test
the failure table ([04-tool-engineering/failure-handling.md](../04-tool-engineering/failure-handling.md))
and the resilience stack
([08-reliability-resilience/README.md](README.md)) *on purpose*, before production
does it by accident.

## How does it work?

1. **Identify failure modes** to inject: error responses, timeouts, hangs, crashes,
   slow responses, connection drops, rate limits
   ([remote-proxy-failures.md](remote-proxy-failures.md)).
2. **Build injectable seams**: a mock/faulty backend, a flag-controlled tool, a
   proxy that can drop/duplicate/delay.
3. **In tests**: run scenarios — flaky mode, dead mode, slow mode — and assert the
   client's behavior (retries, fail-fast, fallback, recovery).
4. **In production (advanced)**: chaos experiments with small blast radius and
   automatic rollback.

## Mental model

Failure injection is the **fire drill**: you don't wait for a real fire to learn
whether the alarms work — you set one off on purpose, watch the response, and fix
what fails. The drills get more realistic over time (small fires first).

## MCP-specific behavior

- **Nothing protocol-level.** The seams are yours: a tool that reads an injected
  failure flag, a mock MCP server with fault modes, a test-only tool that sleeps/
  errors/raises on demand.
- **The cleanest MCP seams**: 
  - a **faulty backend** (mock downstream with modes: `flaky`, `dead`, `slow`)
  - a **test tool** on the server (`fail_next(n)`, `sleep(seconds)`)
  - a **transport-level injector** (drop responses, corrupt JSON)

## Example

A failure-injection tool (test-only — never ship it to production):

```python
import asyncio
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("faulty")

_fail_next_n = 0

@mcp.tool
def fail_next(n: int) -> str:
    """TEST-ONLY: make the next n calls to flaky_tool fail with an error."""
    global _fail_next_n
    _fail_next_n = n
    return f"armed for {n} failures"

@mcp.tool
async def flaky_tool(payload: str) -> str:
    """A tool that fails when armed. Use with fail_next to test retries."""
    global _fail_next_n
    if _fail_next_n > 0:
        _fail_next_n -= 1
        raise ToolError("injected failure: upstream returned 503")
    return f"ok: {payload}"

@mcp.tool
async def slow_tool(seconds: float) -> str:
    """TEST-ONLY: sleeps, for timeout/cancellation tests."""
    await asyncio.sleep(seconds)
    return "done"
```

Full harnesses live in `implementations/python-fastmcp` (a `FaultyBackend`) and
`repository/go/resilience`.

## Industry-standard pattern

Chaos engineering (Netflix Chaos Monkey, Gremlin) is the production-grade version;
**fault-injected test suites** are the everyday version every team should have. The
rules: inject at seams (not by editing production code), start with the most
likely failures, assert *behavior* (retries happened, fail-fast happened), and keep
blast radius small in production experiments.

## Common mistakes

- **Injection without assertions** — the fault happened but you didn't verify the
  response.
- **Testing only happy paths** — the resilience code rots untested.
- **Injection tools shipped to production** — `fail_next` in prod is a self-DoS;
  gate them behind flags/environment.
- **Testing the mock, not the code** — the injection must exercise the *real* retry/
  breaker/recovery paths.

## Testing

- **Scenario tests**: each injected fault produces the designed behavior
  ([15-testing/resilience-testing.md](../15-testing/resilience-testing.md)).
- **Flaky-mode tests**: N failures then success → retry stack recovers.
- **Dead-mode tests**: persistent failure → circuit breaker trips → fail-fast.
- **Restart tests**: kill the server → client reconnects
  ([session-recovery.md](session-recovery.md)).

## Security considerations

- **Production failure injection is risky**: it can trigger real alerts, rate
  limits, and customer impact — scope it, schedule it, and have rollback.
- **Test-only tools are attack surface**: an attacker who finds `fail_next` can DoS
  your server — never expose them in production builds.

## Related

- [04-tool-engineering/failure-handling.md](../04-tool-engineering/failure-handling.md)
- [circuit-breakers.md](circuit-breakers.md) · [session-recovery.md](session-recovery.md)
- [15-testing/resilience-testing.md](../15-testing/resilience-testing.md)
- `examples/faulty_server.py` (this section)