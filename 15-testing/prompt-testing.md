# Prompt Testing

## What is it?

**Prompt testing** verifies a server's prompts: that `prompts/list` advertises
them, that `prompts/get` returns the expected message structure with the given
arguments, and that prompt *content* is correct and safe.

## Why does MCP need it?

Prompts are reusable instruction templates the client fills in and sends to the
model ([02-primitives/prompts.md](../02-primitives/prompts.md)). A prompt with a
broken argument substitution, a wrong system prompt, or — worse — content that
injects instructions from untrusted data produces an agent that misbehaves
([14-security/prompt-injection.md](../14-security/prompt-injection.md)). Testing
prompts is cheap and catches all of it.

## How to test — what to cover

1. **Listing**: every prompt appears in `prompts/list` with its name and
   argument schema.
2. **Retrieval with arguments**: `prompts/get(name, arguments)` returns the
   expected `messages` — role, content, and the substituted arguments
   ([02-primitives/prompts.md](../02-primitives/prompts.md)).
3. **Missing arguments**: prompting without a required argument → clean error.
4. **Substitution**: arguments actually appear where the template says
   (no placeholder left behind, no unescaped user data injected as instructions).
5. **Safety**: if a prompt embeds resource content or user text, the *result*
   is still data-shaped, not instruction-shaped
   ([14-security/untrusted-output.md](../14-security/untrusted-output.md)).

## Example

```python
import pytest
from fastmcp import Client

@pytest.mark.asyncio
async def test_prompts():
    async with Client("server.py") as client:
        names = [p.name for p in await client.list_prompts()]
        assert "review" in names

        result = await client.get_prompt("review", {"subject": "payments"})
        assert result.messages[0].role == "user"
        assert "payments" in result.messages[0].content.text
```

## MCP-specific behavior

- Prompts are *server-provided templates*, not chat — the client renders them
  into its own conversation. Test the rendered `messages`, not your template
  source.
- FastMCP prompt arguments are strings by default (3.x); typed argument
  coercion is a FastMCP feature, not the protocol
  ([12-fastmcp/fastmcp.md](../12-fastmcp/fastmcp.md)).

## Industry-standard pattern

**Golden-file tests** for prompts: render each prompt with representative
arguments and assert the exact output. This catches accidental wording changes
that alter model behavior.

## Common mistakes

- Testing the template function, not the rendered messages.
- Never testing prompts at all (they're "just text" — until the agent follows
  them).
- Embedding untrusted content in a prompt without a data boundary.

## Related

- [02-primitives/prompts.md](../02-primitives/prompts.md)
- [14-security/prompt-injection.md](../14-security/prompt-injection.md)
- Example: [02-primitives/examples/test_primitives.py](../02-primitives/examples/test_primitives.py)
