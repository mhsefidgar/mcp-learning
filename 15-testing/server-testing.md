# Server Testing

## What is it?

**Server testing** is testing a server's logic in isolation — importing the server
module and calling its tools/resources/prompts directly, without any transport.
FastMCP makes this trivial: the `FastMCP` object exposes `call_tool`,
`read_resource`, and `get_prompt` coroutines you can await in-process.

## Why does MCP need it?

Integration tests are the ground truth, but they are slower and more
machinery-heavy (spawning processes, waiting on ports). Server tests give you a
fast feedback loop for *logic*: argument validation, error branches, state
transitions. You want both layers — server tests for speed, integration tests for
truth ([integration-testing.md](integration-testing.md)).

## How it works

```python
import pytest
from my_server import mcp           # the FastMCP instance

@pytest.mark.asyncio
async def test_add_tool():
    result = await mcp.call_tool("add", {"a": 2, "b": 3})
    assert result.content[0].text == "5"
```

Notes:

- **No transport**: no subprocess, no port — just the event loop.
- **In-process state**: the server's module state (dicts, caches) is directly
  visible, so you can seed and assert on it.
- **Deterministic**: no I/O races; time-based logic can be faked.

## MCP-specific behavior

- `call_tool` returns a `ToolResult` (content list) — same shape a client sees,
  minus the wire encoding. Assert on `result.content[0].text` or
  `result.structured_content`.
- `read_resource` returns the resource contents; `get_prompt` returns the prompt
  messages.
- Exceptions raised by tools (`ToolError`) propagate — test them with
  `pytest.raises`.

## Industry-standard pattern

**The test pyramid**: many fast server/unit tests, fewer integration tests, fewest
end-to-end tests. FastMCP's in-process API *is* the unit-test harness — no extra
framework needed.

## Common mistakes

- Testing only through integration (slow, and you can't reach error branches
  that require broken inputs).
- Asserting on the *framework's* return type instead of your logic (e.g., testing
  that FastMCP returns a `ToolResult` — that's the framework's job).
- Relying on server tests alone — they never prove the wire protocol works.

## Testing (how to test the testing)

- A server test should exercise every branch of every tool: happy path, each
  validation error, each `ToolError`.
- Seed module state before each test and assert on mutations after.

## Related

- [integration-testing.md](integration-testing.md)
- [tool-testing.md](tool-testing.md)
- [03-routing-dispatch/10-error-routing.md](../03-routing-dispatch/10-error-routing.md)
- Example: [02-primitives/examples/test_primitives.py](../02-primitives/examples/test_primitives.py)
