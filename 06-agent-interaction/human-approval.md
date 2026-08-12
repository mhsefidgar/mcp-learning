# Human Approval

## What is it?

**Human approval** is the pattern of *requiring a person's explicit consent* before a
tool performs a sensitive action — deleting data, spending money, sending messages,
deploying. In MCP it is built on **elicitation** ([elicitation.md](elicitation.md)):
the tool pauses mid-call, asks the user to confirm, and proceeds only on approval.

## Why does MCP need it?

Agents act with real-world consequences. A model that deletes a project, sends an
email, or spends money on a *guess* is a liability. Human approval is the control
that keeps consequential actions under human authority:

- **Correctness**: the user verifies intent before irreversible effects.
- **Trust**: users let agents do *more* when destructive actions require a nod.
- **Auditability**: the approval is a recorded event
  ([14-security/auditability.md](../14-security/auditability.md)).

## How does it work?

1. **Classify the action**: which tools are sensitive? (delete*, send*, pay*,
   deploy* — see [04-tool-engineering/annotations.md](../04-tool-engineering/annotations.md)
   `destructiveHint`).
2. **Elicit before executing**: the tool asks a precise question — *what* will
   happen, *what* is affected, *how* to undo it.
3. **Act on the answer**: approve → proceed; reject → return a cancelled result with
   the reason.
4. **Record**: log the approval decision (who, what, when, outcome).

```
tools/call delete_project(id: "p-9")
   │  elicitation: "Delete project p-9 (12 files, 3 days old)? This is irreversible."
   ▼
user approves ──► delete + audit log "user X approved delete of p-9"
user rejects  ──► return {status: "cancelled", reason: "user declined"}
```

## Mental model

Human approval is a **two-key system** for sensitive operations: the model holds one
key (the tool call), the user holds the other (the confirmation). Both are required —
like a launch switch that needs two people, or a bank transfer needing a second
authorizer.

## MCP-specific behavior

- **The protocol mechanism is elicitation** (session-based: server→client request;
  stateless: MRTR `input_required`).
- **Approval policies are application-side**: which tools require approval, whether
  approval expires, whether a session can pre-approve ("don't ask again for this
  session") — all yours.
- **Client rendering matters**: the client decides how to present the question
  (dialog, inline button). A well-phrased question is a safety feature.
- **Approval is not authorization**: the click confirms intent; permissions are still
  enforced server-side ([14-security/authorization.md](../14-security/authorization.md)).

## Example

FastMCP — approval via elicitation (see [elicitation.md](elicitation.md) for the
`CurrentContext` pattern):

```python
from fastmcp import FastMCP, Context
from fastmcp.dependencies import CurrentContext

mcp = FastMCP("projects")

SENSITIVE = {"delete_project", "transfer_funds", "send_broadcast"}

@mcp.tool
async def delete_project(project_id: str, ctx: Context = CurrentContext()) -> dict:
    """Delete a project. Requires explicit user approval."""
    project = db.get(project_id)
    if project is None:
        raise ToolError(f"Project {project_id} does not exist")

    answer = await ctx.elicit(
        f"Delete project '{project['name']}' ({project['file_count']} files)? "
        "This is irreversible.",
        response_type=bool,
    )
    if answer.action != "accept" or not getattr(answer, "data", None):
        return {"project_id": project_id, "status": "cancelled", "reason": "user declined"}

    db.delete(project_id)
    audit.log("delete_project", project_id, decision="approved")
    return {"project_id": project_id, "status": "deleted"}
```

## Industry-standard pattern

Approval workflows are standard: **sudo, cloud IAM confirmations, code-review
gates, dual control in banking**. The engineering rules: ask the *right* question
(concrete, specific), never pre-approve destructive actions silently, expire
approvals, and audit every decision. The MCP version just makes it a first-class
interaction inside a tool call.

## Common mistakes

- **Asking vague questions** ("Proceed?") — the user can't consent to what they
  can't see; state the concrete effect.
- **Approval without authorization** — the click is not the permission check
  ([14-security/destructive-operations.md](../14-security/destructive-operations.md)).
- **No rejection path** — every approval must handle decline.
- **Skipping approval for "small" destructive actions** — irreversibility, not size,
  is the criterion.
- **No audit record** — unrecorded approvals are unaccountable.

## Testing

- **Approve/reject tests**: both paths, including reason capture
  ([15-testing/failure-testing.md](../15-testing/failure-testing.md)).
- **Irreversibility tests**: the action happens exactly once, only on approval.
- **Audit tests**: every approval/rejection is recorded with enough detail.
- **Policy tests**: the sensitive-tool list is enforced (a tool marked sensitive
  can't be called without the flow).

## Debugging

- "The tool deleted without asking" → the approval path wasn't wired into that
  handler (or a client bypassed elicitation); check the sensitive-tool registry.
- Approval prompts that users ignore → the question is too vague or the client
  renders it poorly.

## Security considerations

- **Approval fatigue is a real attack**: users click "OK" out of habit — keep
  approvals *rare and specific* so each one means something.
- **A compromised client can auto-approve** — approvals are a UX control, not a
  security boundary; server-side authorization + audit are the real controls.
- **Log approvals with full context** (what, when, by whom, outcome) for forensics
  ([14-security/auditability.md](../14-security/auditability.md)).

## Related concepts

- [elicitation.md](elicitation.md)
- [04-tool-engineering/annotations.md](../04-tool-engineering/annotations.md)
- [14-security/destructive-operations.md](../14-security/destructive-operations.md)
- [14-security/auditability.md](../14-security/auditability.md)