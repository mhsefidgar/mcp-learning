# Tool Testing

## What is it?

**Tool testing** verifies each tool's behavior end to end: what it advertises
(schema), how it validates arguments, what it returns on success, and how it
fails on bad input or errors.

## Why does MCP need it?

Tools are the primary way an agent *acts*. A tool that silently returns wrong
data, crashes the session on a bad argument, or advertises a schema that doesn't
match its real inputs breaks the whole system — and the failure is usually
"the agent called it wrong" rather than an obvious bug. Testing pins the
contract: schema, arguments, result, errors.

## How it works — what to test per tool

1. **Discovery**: the tool is listed with the expected name and description.
2. **Schema**: the advertised JSON schema matches your intent — parameter names,
   types, required fields, defaults, descriptions
   ([schema-testing.md](schema-testing.md),
   [04-tool-engineering/schemas.md](../04-tool-engineering/schemas.md)).
3. **Happy path**: valid arguments → expected result (content *and* structured
   content if declared).
4. **Validation**: missing required args, wrong types, out-of-range values →
   clean errors, not crashes ([04-tool-engineering/validation.md](../04-tool-engineering/validation.md)).
5. **Failure path**: the tool's own error branches raise `ToolError` with a
   useful message ([04-tool-engineering/errors.md](../04-tool-engineering/errors.md)).
6. **Side effects**: state mutations are correct (seed state, call, assert).

## Example

```python
import pytest
from fastmcp import Client

@pytest.mark.asyncio
async def test_add_tool_contract():
    async with Client("server.py") as client:
        tools = await client.list_tools()
        add = next(t for t in tools if t.name == "add")
        assert add.inputSchema["properties"]["a"]["type"] == "integer"
        assert set(add.inputSchema["required"]) == {"a", "b"}

        assert (await client.call_tool("add", {"a": 2, "b": 3})).content[0].text == "5"

        with pytest.raises(Exception):          # validation failure
            await client.call_tool("add", {"a": "not-a-number"})
```

## MCP-specific behavior

- Tool *results* are content lists — test both `content` (what the agent sees)
  and `structured_content` (the machine-readable form)
  ([04-tool-engineering/structured-output.md](../04-tool-engineering/structured-output.md)).
- The client's `raise_on_error` behavior matters: `call_tool` raises on
  `isError` results by default; pass `raise_on_error=False` to assert on the
  error result object instead ([04-tool-engineering/failure-handling.md](../04-tool-engineering/failure-handling.md)).

## Industry-standard pattern

**Table-driven tests**: one table of (arguments, expected result-or-error) per
tool. For MCP, write it as a parametrized pytest with a `call_tool` helper that
returns `(ok, text)` — see [14-security/examples/test_security.py](../14-security/examples/test_security.py).

## Common mistakes

- Testing only the happy path — validation and error branches go stale.
- Asserting on `isError` results as if they were successes (a tool that returns
  an error *result* is different from raising).
- Testing the schema only in-process (the wire schema can differ).

## Related

- [schema-testing.md](schema-testing.md)
- [server-testing.md](server-testing.md)
- [04-tool-engineering/validation.md](../04-tool-engineering/validation.md)
- Example: [04-tool-engineering/examples/test_hardened.py](../04-tool-engineering/examples/test_hardened.py)
