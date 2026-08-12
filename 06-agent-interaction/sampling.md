# Sampling

> **Deprecation note.** Sampling is **deprecated** in the 2026-07-28 spec (works for
> at least 12 months; new implementations shouldn't adopt it). The modern guidance:
> call an LLM directly from your server, or use elicitation for interactive input.
> This doc explains the concept because you will meet sampling in existing
> 2024–2026 servers and need to understand it.

## What is it?

**Sampling** is the server asking the *client* to generate an LLM completion on its
behalf, via the `sampling/createMessage` request (server→client). The server sends
prompt messages, `maxTokens`, and other parameters; the client runs its own model
(possibly with the *user's* permission) and returns the completion.

## Why does MCP need it?

Two historical motivations:

1. **No API keys server-side.** A server that needs a one-off completion ("summarize
   this") could ask the client, which already has model access — the server never
   touches a model API.
2. **User control.** The client can gate generation behind user consent, keeping
   model usage on the user's account and under the user's eye.

It never became a recommended pattern: model calls from servers are better done
directly (with the server's own credentials), and interactive flows are better done
with elicitation ([elicitation.md](elicitation.md)).

## How does it work?

1. The **client declares the `sampling` capability** at initialization — if it
   doesn't, the server must not ask.
2. The server sends `sampling/createMessage` with `messages`, `maxTokens`,
   `systemPrompt`, `includeContext` (how much conversation context to include), and
   `_meta.progressToken` (optional).
3. The client runs its model (with user consent where configured) and replies with
   `CreateMessageResult` — the model output plus `stopReason`, `model`, and
   `role`.
4. The server uses the text and continues.

## Mental model

Sampling is **asking your host to think for you**: "you have a brain (model access);
please think this thought." The host (client) controls the brain and can refuse. It's
the mirror of the normal flow, where the *client* asks the *server* to act.

## MCP-specific behavior

- **Protocol-defined, server→client, client-gated**: `sampling/createMessage`, only
  after the client declares `sampling`.
- **`includeContext`** controls how much of the ongoing conversation the server wants
  the model to see — a privacy knob.
- **Deprecated in 2026-07-28**; the modern protocol has no channel for server-initiated
  generation over stateless connections (the FastMCP docs note: "for generation, call
  an LLM directly from your server").

## Example

On a 2025-era client, the *server* code would call:

```python
# Educational: shows the historical mechanism. Prefer calling an LLM directly.
result = await ctx.session.create_message(
    messages=[{"role": "user", "content": {"type": "text", "text": "Summarize this bug report."}}],
    max_tokens=300,
)
summary = result.content.text
```

In **FastMCP 3.x on session-based connections**, sampling support is limited (the
framework moved toward elicitation and direct LLM calls); check your client's
declared capabilities before relying on it.

## Industry-standard pattern

"Delegate generation to the caller" is an unusual pattern; the industry norm is the
server owning its model calls (its own keys, budgets, and observability). The
successor ideas — *ask for a decision from the host* and *let the user approve* — are
alive in elicitation and human-approval flows ([human-approval.md](human-approval.md)).

## Common mistakes

- **Calling `sampling/createMessage` on a client that never declared `sampling`.**
- **Building new features on sampling** — it's deprecated; call an LLM directly.
- **Sending private conversation context via `includeContext`** without thinking
  about what the model (and its vendor) will see.

## Testing

- **Capability tests**: sampling is only attempted when the client declares it.
- **Request-shape tests**: messages/maxTokens are correct
  ([15-testing/capability-testing.md](../15-testing/capability-testing.md)).
- **Refusal tests**: a client that refuses sampling doesn't break the server.

## Debugging

- "Sampling didn't work" → check the client's declared capabilities first; most
  clients don't declare it.
- Log the model + stopReason returned — sampling failures are usually client-side.

## Security considerations

- **Sampling sends your prompt text to the client's model provider** — treat it as a
  data-exfiltration channel. Never sample with sensitive data unless you trust the
  client's model pipeline.
- **The result is untrusted model output** — validate before use
  ([14-security/untrusted-output.md](../14-security/untrusted-output.md)).

## Related concepts

- [elicitation.md](elicitation.md) — the modern interactive mechanism
- [roots.md](roots.md) — another deprecated client capability
- [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)
- [14-security/untrusted-output.md](../14-security/untrusted-output.md)