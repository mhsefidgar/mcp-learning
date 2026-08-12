# 14 — MCP Security

**What this section teaches.** How to secure MCP systems end to end:
**authentication** (who are you?), **authorization** (what may you do?), **tool
permissions** and **least privilege** (the principle), **OAuth concepts** (the
standard), handling **untrusted tool output** and **prompt injection**,
**destructive operations**, **auditability**, **secret management**, and
**sensitive-data redaction**.

**Prerequisites.** [01-fundamentals](../01-fundamentals/README.md),
[03-routing-dispatch/08-authorization-routing.md](../03-routing-dispatch/08-authorization-routing.md).

**The core threat model.** MCP servers are *code the client can trigger*; MCP
clients are *untrusted input channels* to the model. Two directions of trust to
manage:

```
  client ──(auth)──► server: prove who you are, prove what you may call
  server ──(output)──► model: tool results are UNTRUSTED data, may contain injection
```

**Reading order:**

1. [authentication.md](authentication.md) · [oauth.md](oauth.md) — identity
2. [authorization.md](authorization.md) · [tool-permissions.md](tool-permissions.md) · [least-privilege.md](least-privilege.md) — permissions
3. [untrusted-output.md](untrusted-output.md) · [prompt-injection.md](prompt-injection.md) — the model side
4. [destructive-operations.md](destructive-operations.md) — the dangerous tools
5. [auditability.md](auditability.md) · [secret-management.md](secret-management.md) · [sensitive-data-redaction.md](sensitive-data-redaction.md) — operations

**Protocol vs. engineering:** MCP contributes auth *extensions* and some hardening
(issuer validation, CIMD in 2026-07-28) — but authentication, authorization, and
secrets management are **general security engineering** applied at the MCP boundary.

**Exercises.**

1. **Protect a tool**: add token auth + per-tool permissions to a server
   ([authentication.md](authentication.md), [tool-permissions.md](tool-permissions.md)).
   *Acceptance:* an unauthenticated caller gets a clean auth error; an
   authenticated caller can only call its permitted tools.
2. **Injection drill**: make a tool return a payload containing instructions
   ("ignore previous instructions…"); observe how the client handles it
   ([untrusted-output.md](untrusted-output.md)).
3. **Redaction**: log a tool call whose arguments contain a secret; verify the log
   is clean ([sensitive-data-redaction.md](sensitive-data-redaction.md)).
4. **Audit review**: run the capstone and produce the audit trail for a session
   ([auditability.md](auditability.md)).

**Runnable example.** [examples/README.md](examples/README.md) — a server with
real auth, per-tool permissions, redacting audit, and a destructive tool,
plus a 6-test suite.

**Common mistakes in this section**

- Authentication with no authorization (any logged-in user can call anything).
- Trusting tool output as if it were instructions ([untrusted-output.md](untrusted-output.md)).
- Secrets in tool arguments/logs/schemas ([secret-management.md](secret-management.md)).
- Destructive tools with no confirmation or audit
  ([destructive-operations.md](destructive-operations.md)).