# 14 — Security examples

**`audited_server.py`** — one server, the full boundary:
token authentication (via the request `_meta` field), per-tool permissions
(admin-only destructive + audit tools), a redacting audit trail, an
untrusted-output drill tool, and a destructive tool that requires a
`confirm` flag. `client_audited.py` drives it as `alice` (read-only) and
`admin`. Tests: `test_security.py` (6 tests).

```bash
python audited_server.py            # terminal 1
python client_audited.py            # terminal 2
pytest test_security.py -q          # or: ../../.venv/Scripts/python.exe -m pytest ...
```

**What each test covers**

| Test | Asserts |
|------|---------|
| `test_unauthenticated_rejected` | operations without a token are denied |
| `test_invalid_token_rejected` | a forged token is denied |
| `test_alice_can_read_but_not_delete` | per-tool permissions (read yes, delete no, audit no) |
| `test_destructive_tool_requires_confirmation` | `confirm=True` gate |
| `test_audit_redacts_sensitive_arguments` | secrets never reach the audit log |
| `test_audit_records_denied_attempts` | denials are audited too |

**Why discovery methods are public.** The client SDK itself issues `tools/list`
internally (e.g., to validate a tool result's schema) and cannot attach your
auth metadata to those calls. Like real MCP servers, this example keeps
**listing public and acting protected** — `tools/call`, `resources/read`, and
`prompts/get` require a valid token and permission. Hiding tool *names* is not a
security control anyway ([14-security/least-privilege.md](../least-privilege.md));
enforcement at call time is.

**Running against the section docs.** Pair with:
[authentication.md](../authentication.md), [tool-permissions.md](../tool-permissions.md),
[destructive-operations.md](../destructive-operations.md),
[sensitive-data-redaction.md](../sensitive-data-redaction.md),
[auditability.md](../auditability.md), [untrusted-output.md](../untrusted-output.md).
