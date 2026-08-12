# Architecture

## What is it?

The **architecture** of an end-to-end MCP system is the arrangement of
components and the flow of control between them: the agent (client), the MCP
server, and the domain systems behind it. This document describes the
architecture used by the runnable example in this section and the capstone.

## Why does MCP need it?

MCP doesn't dictate an architecture — it defines the *boundary* between client
and server. Everything else (how the agent makes decisions, how the server gets
its data, how approvals happen) is engineering you choose. A clear architecture
makes those choices explicit: what lives on which side, what crosses the wire,
and where each concern (validation, auth, resilience, observability) is handled.

## The components

```text
┌──────────────────────────────┐
│ AGENT (client)               │
│  workflow orchestrator       │
│  - discovers capabilities    │
│  - chains tool calls         │
│  - tracks workflow state     │
│  - validates outputs         │
│  - retries / fails over      │
│  - logs + metrics            │
└──────────────┬───────────────┘
               │ JSON-RPC over stdio / Streamable HTTP
┌──────────────▼───────────────┐
│ MCP SERVER                   │
│  tools   resources   prompts │
│  middleware: auth, audit,    │
│    logging, rate limiting    │
│  providers / domain adapters │
└──────────────┬───────────────┘
               │ calls
┌──────────────▼───────────────┐
│ DOMAIN SYSTEMS               │
│  database, APIs, human       │
│  approval (elicitation)      │
└──────────────────────────────┘
```

### The agent (client side)

- **Orchestrates**: decides *what* to do next (for a scripted agent: a step
  list; for an LLM agent: model reasoning over tool results).
- **Discovers**: capabilities, tools, resources, prompts
  ([01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)).
- **Chains**: passes one tool's validated output as the next tool's input.
- **Protects itself**: output validation
  ([14-security/untrusted-output.md](../14-security/untrusted-output.md)),
  retries ([08-reliability-resilience/exponential-backoff.md](../08-reliability-resilience/exponential-backoff.md)),
  approvals ([06-agent-interaction/human-approval.md](../06-agent-interaction/human-approval.md)).
- **Observes**: structured logging, metrics, tracing
  ([09-observability-telemetry/README.md](../09-observability-telemetry/README.md)).

### The server (server side)

- **Exposes**: tools (actions), resources (data), prompts (templates)
  ([02-primitives/README.md](../02-primitives/README.md)).
- **Enforces**: validation ([04-tool-engineering/validation.md](../04-tool-engineering/validation.md)),
  auth + permissions ([14-security/README.md](../14-security/README.md)).
- **Adapts**: providers hide the domain systems behind capability interfaces
  ([12-fastmcp/providers.md](../12-fastmcp/providers.md)).
- **Reports**: progress and elicitation back to the client
  ([06-agent-interaction/progress.md](../06-agent-interaction/progress.md)).

## The flow of a request

1. **Session setup**: client initializes, negotiates capabilities
   ([01-fundamentals/05-initialization.md](../01-fundamentals/05-initialization.md)).
2. **Discovery**: client lists tools/resources/prompts and inspects schemas.
3. **Execution**: client calls a tool; the server authenticates, authorizes,
   validates, runs the provider, and returns a result (or error, or progress
   notifications, or an elicitation for approval).
4. **Chaining**: the client validates the result and decides the next call.
5. **Teardown**: graceful shutdown closes the session cleanly
   ([01-fundamentals/09-sessions-and-lifecycle.md](../01-fundamentals/09-sessions-and-lifecycle.md)).

## Where each concern lives (the architecture contract)

| Concern | Agent | Server | Notes |
|---------|-------|--------|-------|
| What to do next | ✓ | | the *decision* is client-side |
| Capability truth | | ✓ | server advertises, client trusts but verifies |
| Validation | ✓ (outputs) | ✓ (inputs) | both sides validate |
| Auth/permissions | ✓ (presents creds) | ✓ (enforces) | server is the gate |
| Retries/breakers | ✓ | ✓ (optional) | client is the primary retrier |
| Approval | ✓ (shows UI) | ✓ (asks via elicitation) | server asks, human decides |
| Logging/metrics | ✓ | ✓ | correlated via request/session IDs |
| Data access | | ✓ | via providers |

## MCP vs general engineering

- **MCP defines**: the message model, capability negotiation, sessions,
  transports, the three primitives, progress/elicitation
  ([01-fundamentals/README.md](../01-fundamentals/README.md)).
- **You define**: the workflow, the domain logic, retry policy, auth stack,
  observability, and how approvals are presented. MCP doesn't have opinions
  about your architecture — it just carries the messages.

## Related

- [implementation.md](implementation.md)
- [testing.md](testing.md)
- [03-routing-dispatch/README.md](../03-routing-dispatch/README.md)
- [10-scaling-performance/multi-server-and-gateway.md](../10-scaling-performance/multi-server-and-gateway.md)
- [capstone/architecture](../capstone/architecture/)
