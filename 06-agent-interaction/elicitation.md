# Elicitation

## What is it?

**Elicitation** is the server asking the client — and through it, the **user** — for
structured input *during* a tool call: a confirmation, a missing parameter, a
choice. It's the mechanism that turns a one-shot tool call into a conversation when
the tool needs something only the user can provide.

```
client ──► server  tools/call {name: "delete_project", arguments: {id: "p-9"}}
server  ──► client  elicitation: "Delete project p-9? (confirm/cancel)"   ← mid-call
client  ──► server  answer: "confirm"
server  ──► client  tools/call result {status: "deleted"}
```

## Why does MCP need it?

Tools hit moments where the *right* thing depends on a human: confirm a destructive
action, pick an option, provide a value the model guessed. Without elicitation the
server must either guess (dangerous), fail ("cannot proceed"), or implement a
multi-tool dance. Elicitation keeps the decision *with the user* at the exact moment
it matters — the foundation of safe interactive agents
([human-approval.md](human-approval.md)).

## How does it work?

In the **session-based protocol (2025-11-25)**: elicitation is a server→client
request during the tool call; the client renders the question, gets user input, and
returns it; the tool continues with the answer.

In the **2026-07-28 stateless protocol (MRTR)**: the server returns
`resultType: "input_required"` with its questions; the client answers and *retries*
the original call with `inputResponses`. The server's next invocation receives the
answers. (See [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md).)

FastMCP abstracts this: `await ctx.elicit(question, response_type=...)` returns a
result whose `.action` is `"accept"` (with `.data`) or a decline/cancel result.

> **Verified against FastMCP 3.4.7.** Server-side results are `AcceptedElicitation`
> (`{action, data}`) and `DeclinedElicitation` (`{action}` only). Client-side, pass
> `Client(..., elicitation_handler=cb)` to advertise the capability; the callback
> receives `(message, response_type, params, context)` and may return the data
> directly (accept) or `ElicitResult(action="decline", content=...)`. See
> `06-agent-interaction/examples/` for a working approve/reject round trip.

## Mental model

Elicitation is **the server raising its hand mid-task**: "I need the user's input to
continue." The client is the *concierge* who relays the question and brings back the
answer — the server never talks to the user directly. The whole thing stays inside
one logical tool call.

## MCP-specific behavior

- **Protocol-defined** (2025-06-18+ spec; extended in 2026-07-28 via MRTR).
- **Client-gated**: only if the client supports elicitation (declared capability in
  the modern spec).
- **Typed responses**: FastMCP supports `str`, `bool`, numbers, and structured types
  (`response_type=bool` renders yes/no).
- **The tool decides the flow**: a tool may elicit several times in one call, or
  return an `InputRequiredResult` to pause and resume later.

## Example

FastMCP — confirm before deleting:

```python
from fastmcp import FastMCP, Context
from fastmcp.dependencies import CurrentContext

mcp = FastMCP("projects")

@mcp.tool
async def delete_project(project_id: str, ctx: Context = CurrentContext()) -> dict:
    """Delete a project. Asks the user to confirm first."""
    result = await ctx.elicit(
        f"Delete project {project_id}? This cannot be undone.",
        response_type=bool,
    )
    if result.action != "accept" or not result.data:
        return {"project_id": project_id, "status": "cancelled", "reason": result.reason or "user declined"}
    db.delete(project_id)
    return {"project_id": project_id, "status": "deleted"}
```

A "guard" style: the first call returns an ask, the resumed call does the work:

```python
from fastmcp import FastMCP, Context

@mcp.tool
async def approve_expense(amount: float, ctx: Context) -> dict:
    """Approve an expense; asks the manager for confirmation."""
    answer = await ctx.elicit(f"Approve ${amount:.2f} expense?", response_type=bool)
    if answer.action == "reject":
        return {"approved": False, "reason": answer.reason}
    return {"approved": True}
```

## Industry-standard pattern

Human-in-the-loop confirmation is standard for destructive operations everywhere
(sudo, cloud console confirmations, payment authorizations). MCP's contribution is
making it *protocol-native*: the confirmation happens inside the tool call, so the
agent's workflow doesn't break into disconnected steps.

## Common mistakes

- **Eliciting on clients that don't support it** — check capability first, and have
  a fallback (refuse safely).
- **Trusting the answer blindly** — "confirm" doesn't mean "authorized"; still
  enforce permissions server-side ([14-security/authorization.md](../14-security/authorization.md)).
- **Eliciting for things the tool already knows** — the model's arguments exist;
  elicit only for genuinely human decisions.
- **No rejection path** — every elicit must handle `action == "reject"`.

## Testing

- **Accept/reject tests**: both paths of an elicitation
  ([15-testing/failure-testing.md](../15-testing/failure-testing.md)).
- **Capability tests**: elicitation only on supporting clients.
- **Fallback tests**: unsupported client → safe refusal, no crash.
- **Round-trip tests** (2026-07-28): `input_required` → retry with `inputResponses`
  completes the call.

## Debugging

- "The tool paused and never resumed" → the client didn't answer the elicitation;
  check client support and the inputResponses round trip in logs.
- In Inspector you can answer elicitations manually — a great way to test the
  interaction without a full agent.

## Security considerations

- **Elicitation is a UX mechanism, not authorization** — the answer is one user's
  click; enforce real permissions
  ([14-security/destructive-operations.md](../14-security/destructive-operations.md)).
- **Phishing surface**: a malicious server can elicit convincing prompts — the client
  must render *who* is asking and what exactly will happen.
- Never include secrets in the question text (it's rendered to the user).

## Related concepts

- [human-approval.md](human-approval.md)
- [sampling.md](sampling.md)
- [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md) (MRTR)
- [14-security/destructive-operations.md](../14-security/destructive-operations.md)