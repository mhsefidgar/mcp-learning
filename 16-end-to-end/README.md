# 16 — End-to-End MCP Agent

**What this section teaches.** How all the pieces fit together into a real
agent-server system: a server exposing tools, resources, and prompts; a client
that discovers capabilities, executes multi-step workflows, chains tool outputs,
handles failures, approvals, and long-running work; and the tests that prove the
whole loop. This is the *integration* of everything in sections 01–15.

**Prerequisites.** Everything before this. In particular:
[01-fundamentals](../01-fundamentals/README.md) (the protocol),
[02-primitives](../02-primitives/README.md) (the three primitives),
[04-tool-engineering](../04-tool-engineering/README.md) (tool quality),
[06-agent-interaction](../06-agent-interaction/README.md) (approval, progress,
elicitation), [08-reliability-resilience](../08-reliability-resilience/README.md)
(retries and recovery), [14-security](../14-security/README.md) (the boundary),
[15-testing](../15-testing/README.md) (proving it works).

**The shape of an end-to-end system**

```text
  agent (client)
    │  discover capabilities & tools
    │  call tools / read resources / use prompts
    │  chain outputs, track state, retry failures
    ▼
  MCP server
    │  tools (business logic + validation + errors)
    │  resources (data the agent reads)
    │  prompts (reusable templates)
    │  middleware (logging, audit, auth)
    ▼
  domain systems (database, APIs, human approval)
```

**Reading order:**

1. [architecture.md](architecture.md) — the components and the flow
2. [implementation.md](implementation.md) — how to build each piece
3. [testing.md](testing.md) — how to prove the whole loop works

**Runnable example.** [examples/README.md](examples/README.md) — an
order-processing server and a scripted agent that discovers, chains, approves,
retries, measures, and shuts down. The [capstone](../capstone/README.md) is the
larger, multi-language version of the same idea.

**The checklist this section maps to** (from the curriculum): building a server,
exposing tools/resources/prompts, connecting a client, sessions, capability
discovery, schema inspection, structured tool calls, resource reads, prompt
usage, resource templates, pagination, failure handling, malformed inputs,
disconnects and timeouts, retries, approval steps, context across calls,
multi-step workflows, chaining outputs, workflow state, long-running operations,
progress, cancellation, auth/permissions, multiple servers and routing,
concurrent calls, caching, logging and tracing, output validation, unsafe-call
prevention, testing, metrics, and graceful shutdown.

**Exercises.**

1. **Extend the workflow**: add a third step to the agent example (e.g., a
   discount step between create and ship) and the tests for it.
2. **Add a second server**: route part of the workflow to a second MCP server
   ([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)).
3. **Make it concurrent**: run two independent workflows in parallel and verify
   isolation.
4. **Measure**: add latency/success-rate reporting to the agent and assert on it.

**Common mistakes in this section**

- Building the server and client separately and never running them together.
- No output validation between chained steps (step 2 trusts step 1 blindly).
- One big script with no failure handling — the moment the server hiccups,
  the workflow dies.
- No metrics, so "is it working?" is unanswerable.
