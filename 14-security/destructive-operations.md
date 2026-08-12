# Destructive Operations

## What is it?

**Destructive operations** are tool calls that delete, overwrite, send, spend, or
otherwise irreversibly change state: `delete_customer`, `drop_table`,
`send_email`, `charge_card`, `deploy`. They are the tools that must be wrapped in
extra layers: confirmation, permissions, and audit.

## Why does MCP need it?

An MCP server exposes an agent's ability to *act*. The whole danger profile of
agentic systems is that a single tool call — mis-argued by the model, injected via
untrusted output ([prompt-injection.md](prompt-injection.md)), or invoked by a
stolen token — causes irreversible damage. Destructive tools concentrate that
risk; they need a different risk posture than read-only tools.

## How to engineer them

1. **Identify them explicitly**: name them clearly (`delete_`, `drop_`,
   `send_`, `charge_`); the name is also documentation for the model.
2. **Restrict them**: destructive tools are the first place to apply least
   privilege and tool permissions ([tool-permissions.md](tool-permissions.md),
   [least-privilege.md](least-privilege.md)).
3. **Confirm them**: require a confirmation step for irreversible actions
   ([06-agent-interaction/human-approval.md](../06-agent-interaction/human-approval.md)).
   MCP has no protocol-level confirmation; implement it with **elicitation**
   (server asks the client/human) or client-side policy before calling.
4. **Make them recoverable**: soft-delete, backups, transactionality — the
   engineering answer to "irreversible".
5. **Require explicit, validated parameters**: a `confirm: true` flag plus full
   target identity ("delete customer id 42"), never ambiguous partial specs.
6. **Audit them unconditionally**: who, what, when, from which session
   ([auditability.md](auditability.md)).

## MCP-specific behavior

- **No protocol feature marks a tool destructive** — it is convention plus your
  policy layer. `annotations` are descriptive only
  ([04-tool-engineering/annotations.md](../04-tool-engineering/annotations.md)).
- The **elicitation** capability is the mechanism a server uses to ask for human
  confirmation ([06-agent-interaction/elicitation.md](../06-agent-interaction/elicitation.md)).
- The client may additionally enforce its own policy: refuse to call
  `delete_*` without explicit user confirmation.

## Example (FastMCP — confirmation via elicitation, enforced server-side)

```python
from fastmcp import FastMCP, Context
from fastmcp.dependencies import CurrentContext

mcp = FastMCP("safe-server")

@mcp.tool
async def delete_customer(customer_id: int, ctx: Context = CurrentContext()) -> str:
    # Ask the human before doing anything irreversible.
    answer = await ctx.elicit(
        f"Delete customer {customer_id}? This is irreversible.",
        response_type=bool,
    )
    # Accept -> {action: "accept", data: True}; anything else -> declined.
    if answer.action != "accept" or not getattr(answer, "data", None):
        return f"customer {customer_id}: cancelled (not approved)"
    # ... perform the deletion ...
    return f"customer {customer_id} deleted"
```

Verified against FastMCP 3.4.7 (`Context.elicit(response_type=...)`); see the
working example in
[06-agent-interaction/examples/approval_server.py](../06-agent-interaction/examples/approval_server.py).

## Industry-standard pattern

- **Separation of duties**: the agent proposes, the human disposes — destructive
  actions route through a human approval step.
- **Two-phase operations** where possible: "stage" then "commit".
- **Undo capability**: backups, soft deletes, transaction logs.
- **Audit + alerting**: destructive operations are the highest-priority audit
  events and trigger alerts on anomalies (e.g., mass deletion).

## Common mistakes

- Naming a destructive tool neutrally (`update_customer` that deletes) so the
  model and reviewers underestimate it.
- No confirmation step because "the model wouldn't do that".
- Deleting without backups, or deleting in a way that bypasses the audit log.
- Granting destructive tools broadly so least privilege is meaningless.

## Testing

- **Confirmation path**: a destructive call without approval is refused; with
  approval it proceeds ([06-agent-interaction/examples](../06-agent-interaction/examples)).
- **Rejection path**: denial is clean and audited.
- **Permission path**: a principal without permission is refused before the
  confirmation step.
- **Recovery drill**: delete something, restore from backup, verify.

## Security considerations

Destructive tools should be *rare, narrow, confirmed, and audited*. If a system
has many destructive tools, that is a design smell — most agents only need a
handful of write operations.

## Related

- [06-agent-interaction/human-approval.md](../06-agent-interaction/human-approval.md)
- [06-agent-interaction/elicitation.md](../06-agent-interaction/elicitation.md)
- [tool-permissions.md](tool-permissions.md)
- [least-privilege.md](least-privilege.md)
- [auditability.md](auditability.md)
