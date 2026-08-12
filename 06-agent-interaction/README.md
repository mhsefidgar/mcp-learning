# 06 — Agent Interaction

**What this section teaches.** The *interactive* capabilities that let a server and a
client collaborate beyond plain request/response: sampling (the server asks the
client's model to generate), elicitation (the server asks the client's *user* for
input mid-call), roots (the client tells the server about its filesystem/URIs),
notifications (server→client events), progress (client-side handling), and
human-approval flows.

**Prerequisites.** [01-fundamentals](../01-fundamentals/README.md),
[02-primitives](../02-primitives/README.md).

**Recommended reading order:**

1. [sampling.md](sampling.md) — server asks the client for model generation
2. [elicitation.md](elicitation.md) — server asks the *user* for input mid-call
3. [roots.md](roots.md) — client shares its context with the server
4. [notifications.md](notifications.md) — server→client events
5. [progress.md](progress.md) — client-side progress handling
6. [human-approval.md](human-approval.md) — confirmation before sensitive actions

**Version reality check (read this first):** roots and sampling are **deprecated** in
the 2026-07-28 spec (still working for ≥12 months) and were always gated on the
*client* declaring them. Elicitation is the *current* mechanism for interactive
input, and the 2026-07-28 spec reworks it via MRTR (Multi Round-Trip Requests). See
[13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md).

**MCP vs. general engineering:**

| Topic | Protocol? | Notes |
|-------|-----------|-------|
| Sampling | ✅ protocol (deprecated 2026-07-28) | server→client `sampling/createMessage` |
| Elicitation | ✅ protocol | server→client input request |
| Roots | ✅ protocol (deprecated 2026-07-28) | client→server `roots/list` |
| Notifications | ✅ protocol | `notifications/*` |
| Progress | ✅ protocol | client-side handling |
| Human approval | ⚠️ pattern | built *on* elicitation/notifications; policy is yours |

**Exercises.**

1. **Elicit a confirmation**: make a `delete_*` tool request confirmation from the
   user before acting. *Acceptance:* the tool call pauses, the client shows the
   question, and the operation proceeds only on approval
   ([human-approval.md](human-approval.md), [elicitation.md](elicitation.md)).
2. **Report + react to progress**: a long tool reports progress; the client renders
   it and offers cancellation. *Acceptance:* progress values arrive with the right
   token and the client can cancel ([progress.md](progress.md)).
3. **Roots round-trip** (on a 2025-era client): the client declares a root; the
   server reads it via `roots/list`. *Acceptance:* the server sees exactly the roots
   the client declared ([roots.md](roots.md)).

**Common mistakes in this section**

- Assuming sampling/roots exist on every client — they are *client capabilities*;
  check the handshake ([01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)).
- Building new systems on deprecated capabilities (sampling/roots) — prefer
  elicitation and direct LLM calls ([sampling.md](sampling.md)).
- Confusing elicitation (protocol) with "the server calls an LLM" (application).