# Inspecting Server Capabilities

## What is it?

The Inspector's **capabilities view** shows what your server declared during
initialization: the two capability maps exchanged in the handshake
([01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)) — what
the *client* offered and what the *server* declared.

## Why is it the first thing to check?

Most "my client can't do X" bugs are **capability mismatches**, not code bugs: the
server never declared `resources`, or declared `tools` without `listChanged`, and the
client is behaving correctly per the handshake. Reading the capability view first
saves you from debugging a non-bug.

## How to read it

- **Server capabilities**: `tools`, `resources` (with `subscribe`/`listChanged`
  flags), `prompts`, `logging`, `completions`, `experimental.*`.
- **Client capabilities**: `sampling`, `roots`, `elicitation` — what the Inspector's
  client offers (usually minimal; it has no sampling).
- Compare against what you *intended*: every registered component must have a
  matching capability declaration.

## Common findings

| Symptom | Likely cause |
|---------|--------------|
| Client "doesn't see" my tools | server declared no `tools` capability, or tools registered after the handshake without `listChanged` |
| `resources/subscribe` never works | `resources.subscribe` not declared |
| Server never sends `tools/list_changed` | `tools.listChanged` not declared (or change detection not wired) |
| Server calls `sampling/*` but client never answers | client didn't declare `sampling` (deprecated anyway — see [06-agent-interaction/sampling.md](../06-agent-interaction/sampling.md)) |

## Related

- [01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)
- [03-routing-dispatch/05-capability-routing.md](../03-routing-dispatch/05-capability-routing.md)
- [initialization-debugging.md](initialization-debugging.md)