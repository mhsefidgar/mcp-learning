# 15 — MCP Testing

**What this section teaches.** How to test MCP systems at every level: server
unit tests, client/server integration over real transports, capability
discovery, tool/resource/prompt behavior, failure and error paths, schema
contracts, security, and resilience. The goal is a test suite that gives you
confidence the *protocol behavior* is right, not just that your Python functions
work.

**Prerequisites.** All of sections 01–14; this section reuses their examples as
test subjects. In particular [02-primitives/examples](../02-primitives/examples)
and [04-tool-engineering/examples](../04-tool-engineering/examples) contain
servers that these docs test.

**The core idea.** MCP testing has three layers:

```text
 unit tests      →  server logic in isolation (no transport)
 integration     →  client ↔ server over stdio / Streamable HTTP
 conformance     →  does the wire behavior match the protocol spec?
```

The highest-value tests are the **integration** ones: spawn the server, connect
with the real client, and assert on what the client sees — because that is what
an MCP *consumer* sees.

**Reading order:**

1. [server-testing.md](server-testing.md) · [integration-testing.md](integration-testing.md) — the two core levels
2. [capability-testing.md](capability-testing.md) · [tool-testing.md](tool-testing.md) · [resource-testing.md](resource-testing.md) · [prompt-testing.md](prompt-testing.md) — per-primitive
3. [schema-testing.md](schema-testing.md) — the contract
4. [failure-testing.md](failure-testing.md) · [resilience-testing.md](resilience-testing.md) — the dark side
5. [security-testing.md](security-testing.md) — the adversarial side
6. [compatibility-testing.md](compatibility-testing.md) — the ecosystem side

**How to run the tests in this repository.** Each section's `examples/` folder
has its own test files; run them from that folder:

```bash
cd 02-primitives/examples && python -m pytest -q      # or the repo venv:
cd ../../ && .venv/Scripts/python.exe -m pytest 02-primitives/examples -q
```

The examples were written against FastMCP 3.4.7 (see [docs/VERSIONS.md](../docs/VERSIONS.md)).

**Exercises.**

1. **Port a test**: take any test from [02-primitives/examples](../02-primitives/examples)
   and re-implement it against a *different* server you built.
2. **Schema contract test**: write a test that asserts the exact JSON schema a
   tool advertises (type, required fields, description) — then break the schema
   and watch the test fail.
3. **Failure injection**: add a fault toggle to a tool (see
   [08-reliability-resilience/failure-injection.md](../08-reliability-resilience/failure-injection.md))
   and test every outcome it can produce.
4. **Adversarial pass**: apply the checks in
   [security-testing.md](security-testing.md) to your own server.
5. **Compat matrix**: run your server against two different MCP clients (e.g.,
   the FastMCP client and the MCP Inspector).

**Runnable example.** [examples/README.md](examples/README.md) — a conformance
harness that drives a real server with raw JSON-RPC over stdio, plus client
contract tests (6 tests).

**Common mistakes in this section**

- Testing the framework instead of the protocol (asserting on internal
  functions, never on what a client observes).
- No integration tests — "it works when I click it" is not a test.
- Tests that depend on wall-clock time (flaky under load).
- Only testing the happy path (see [failure-testing.md](failure-testing.md)).
- Asserting on exact JSON serialization order instead of semantics.
