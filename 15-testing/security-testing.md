# Security Testing

## What is it?

**Security testing** verifies the trust boundaries of an MCP system: that
unauthenticated and unauthorized callers are denied, secrets never leak through
tools/logs/schemas, untrusted tool output cannot drive the agent, and
destructive operations are gated.

## Why does MCP need it?

An MCP server is code execution on demand; a compromised or hostile caller is one
bad `tools/call` away from damage
([14-security/README.md](../14-security/README.md)). Security bugs — unlike logic
bugs — are actively *exploited*, so they need deliberate adversarial tests, not
happy-path coverage that happens to include auth.

## How to test — the security checklist

1. **Auth**: no token → denied; forged/expired token → denied; valid token →
   proceeds ([14-security/authentication.md](../14-security/authentication.md)).
2. **Authorization**: a principal can call *exactly* its permitted tools — every
   other tool is denied
   ([14-security/tool-permissions.md](../14-security/tool-permissions.md)).
3. **Least privilege**: destructive/admin tools require the right role
   ([14-security/least-privilege.md](../14-security/least-privilege.md)).
4. **Redaction**: secrets passed in arguments never appear in logs, audit, or
   traces ([14-security/sensitive-data-redaction.md](../14-security/sensitive-data-redaction.md)).
5. **Schema hygiene**: no secrets in schema defaults/descriptions
   ([schema-testing.md](schema-testing.md)).
6. **Prompt injection**: tools that fetch external content return it as *data*;
   the client does not act on embedded instructions
   ([14-security/prompt-injection.md](../14-security/prompt-injection.md)).
7. **Destructive gating**: irreversible tools require confirmation
   ([14-security/destructive-operations.md](../14-security/destructive-operations.md)).
8. **Audit**: denials and successes are both recorded
   ([14-security/auditability.md](../14-security/auditability.md)).

## Example

```python
import pytest
from fastmcp import Client

ADMIN = {"auth": "admin-token"}
USER = {"auth": "alice-token"}

@pytest.mark.asyncio
async def test_permissions_and_redaction():
    async with Client("audited_server.py") as client:
        # unauthorized caller is denied
        with pytest.raises(Exception):
            await client.call_tool("delete_customer",
                                   {"customer_id": 2, "confirm": True}, meta=USER)
        # authorized caller succeeds
        await client.call_tool("delete_customer",
                               {"customer_id": 2, "confirm": True}, meta=ADMIN)
        # secrets are redacted from the audit trail
        await client.call_tool("read_customer", {"customer_id": 1,
                                                 "api_key": "top-secret"}, meta=USER)
        trail = (await client.call_tool("audit_log", {}, meta=ADMIN)).content[0].text
        assert "top-secret" not in trail
```

See [14-security/examples/test_security.py](../14-security/examples/test_security.py)
for a complete, running version of this pattern.

## MCP-specific behavior

- Client metadata (`meta=`) is how the FastMCP client carries credentials to the
  server's middleware (the `_meta` field). Test the *middleware-enforced*
  behavior over a real session — in-process calls can miss the boundary
  ([14-security/authentication.md](../14-security/authentication.md)).
- Auth must be tested per *method*, not per tool: `resources/read` and
  `prompts/get` need the same gates.

## Industry-standard pattern

**Negative-path-first testing**: write the denial tests before the happy-path
tests for any security control. Add secret-scanning in CI for the whole repo
([14-security/secret-management.md](../14-security/secret-management.md)).

## Common mistakes

- Testing auth in-process without a session (the boundary is bypassed).
- Testing only tools — resources and prompts are forgotten.
- No redaction tests, so a "minor" logging change leaks secrets silently.

## Related

- [14-security/README.md](../14-security/README.md)
- [14-security/examples/test_security.py](../14-security/examples/test_security.py)
- [failure-testing.md](failure-testing.md)
