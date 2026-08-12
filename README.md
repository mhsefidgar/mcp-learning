# MCP Learning Repository

A complete, self-contained course + reference + implementation laboratory for the
**Model Context Protocol (MCP)**. It teaches you not just *what* MCP is, but how to
**understand, implement, debug, secure, test, and operate production-quality MCP
systems** in Python (FastMCP), TypeScript (official SDK), Java (official SDK), Go,
and Rust.

This is not a specification dump. Every concept is explained the way a competent
programmer who is *new to MCP* needs it explained: simple language first, then the
protocol details, then idiomatic code, then production patterns, testing, debugging,
and security.

---

## What this repository teaches

- The **MCP protocol**: how clients and servers talk over JSON-RPC, what a tool,
  resource, and prompt are, and how initialization, capabilities, and transports work.
- **Engineering the three primitives**: designing tool schemas, validation, errors,
  pagination, retries, idempotency, cancellation, and progress.
- **Routing and dispatch**: how an incoming request maps to the right implementation,
  including namespacing, versioning, authorization-aware routing, and proxying.
- **Reliability and resilience**: rate limiting, backpressure, caching, circuit
  breakers, retry budgets, connection pooling, and failure injection.
- **Observability, scaling, and security**: structured logging, OpenTelemetry,
  authentication/authorization, prompt injection, and least privilege.
- **Testing**: unit, integration, capability, schema, security, and resilience tests.
- **A full end-to-end capstone**: a realistic multi-server agent system you can run.

Every section distinguishes **three layers** that people routinely confuse:

| Layer | What it is | Examples |
|-------|-----------|----------|
| **MCP protocol** | Defined by the MCP specification itself | `tools/call`, `initialize`, `resources/read`, `notifications/cancelled` |
| **SDK / framework** | Provided by FastMCP, the TypeScript SDK, the Java SDK | `@mcp.tool`, `McpServer`, `McpClient`, `mcp.mount()` |
| **General engineering** | Standard distributed-systems patterns, not MCP features | retries, circuit breakers, caching, rate limiting, backpressure |

A circuit breaker is **not** an MCP primitive — it is a general resilience pattern you
*wrap around* MCP clients, servers, or remote dependencies. This repository is strict
about that distinction.

---

## Who is it for

- **Backend / platform engineers** building MCP servers and clients at scale.
- **Agent / LLM application developers** wiring models to tools and data.
- **Anyone learning MCP** who already knows how to program and wants depth, not a
  marketing overview.
- **Vibe-coding agents**: the whole repository is written as clean, self-contained
  Markdown + runnable code so it can be dropped into an agent's context as a reliable
  source of truth.

## MCP prerequisites

You do **not** need prior MCP experience. You should be comfortable with:

- A programming language basics (Python, TypeScript, or Java at minimum).
- JSON (MCP messages are JSON).
- Basic HTTP concepts (for the remote transport sections).
- Basic async programming (asyncio / async-await / threads).

No machine-learning background is required — MCP is a protocol, not a model.

---

## Repository structure

```
mcp-learning/
├── README.md                  ← you are here
├── CONTRIBUTING.md
├── LICENSE
├── docs/
│   ├── VERSIONS.md            ← every SDK version the repo targets (read this first)
│   └── GLOSSARY.md
│
├── 01-fundamentals/           ← the protocol: client/server, JSON-RPC, init, transports
├── 02-primitives/             ← tools, resources, prompts
├── 03-routing-dispatch/       ← how requests map to implementations
├── 04-tool-engineering/       ← schemas, validation, retries, cancellation, ...
├── 05-resource-engineering/   ← static/dynamic resources, templates, subscriptions
├── 06-agent-interaction/      ← sampling, elicitation, roots, progress, approvals
├── 07-inspector-debugging/    ← MCP Inspector and debugging workflows
├── 08-reliability-resilience/ ← rate limiting, backpressure, circuit breakers, ...
├── 09-observability-telemetry/← structured logging, OpenTelemetry, tracing, metrics
├── 10-scaling-performance/    ← statelessness, load balancing, concurrency, pooling
├── 11-communication-transport/← JSON-RPC, HTTP, TLS deep dives
├── 12-fastmcp/                ← FastMCP architecture: providers, transforms, middleware
├── 13-versioning/             ← protocol versions, capability negotiation, deprecation
├── 14-security/               ← authn/authz, prompt injection, secrets, audibility
├── 15-testing/                ← server, integration, schema, security, resilience tests
├── 16-end-to-end/             ← tying everything into one agent system
│
├── implementations/           ← MAIN runnable projects (the primary examples)
│   ├── python-fastmcp/        ← Python + FastMCP server & client (pytest)
│   ├── typescript-sdk/        ← TS official SDK server & client (vitest)
│   └── java-sdk/              ← Java SDK server & client (JUnit, Maven)
│
├── repository/                ← LANGUAGE LAB: lower-level & alternative implementations
│   ├── go/                    ← JSON-RPC, transports, client/server, routing, resilience
│   ├── rust/                  ← JSON-RPC, client/server
│   ├── python/                ← a from-scratch protocol implementation
│   ├── typescript/            ← protocol experiments
│   ├── java/                  ← lower-level Java pieces
│   └── other/                 ← other languages when genuinely useful
│
├── shared/                    ← diagrams (Mermaid), JSON schemas, test data, common code
│
└── capstone/                  ← END-TO-END realistic system (server + clients + docker)
```

The four things the structure deliberately keeps separate:

1. **Learning documentation** — the `NN-*` numbered sections.
2. **Main implementation examples** — `implementations/`.
3. **Additional language implementations / experiments** — `repository/`.
4. **End-to-end capstone** — `capstone/`.

> **Note on numbering.** The curriculum in `Sections.text` (15 topics) is mapped onto
> the 13-section layout you requested, with three additions for the topics that had no
> home in the original layout: **09-observability-telemetry**, **10-scaling-performance**,
> and **11-communication-transport**. Everything else keeps its original number where
> possible. See `docs/VERSIONS.md` for the exact mapping.

---

## Learning order

Read the numbered sections **in order**. Each builds on the last:

1. **01-fundamentals** — the mental model and the wire protocol. Read all of it before
   touching code.
2. **02-primitives** — the three things you can expose.
3. **03-routing-dispatch** — how requests find their handler.
4. **04–05** — engineering tools and resources properly.
5. **06** — the interactive capabilities (sampling, elicitation, approvals).
6. **07** — how to inspect and debug a server (do this with your first real server).
7. **08–11** — making it reliable, observable, scalable, and well-transported.
8. **12** — FastMCP's architecture in depth (the framework you'll use most).
9. **13–15** — versioning, security, and testing.
10. **16 + capstone** — put it all together.

If you want the fastest path to *writing your first server*, do `01`, `02`, then the
`implementations/python-fastmcp` project. Come back for `04+` before you ship.

## Supported languages and SDKs

| Language | Primary SDK / framework | Where |
|----------|-------------------------|-------|
| Python | **FastMCP** 3.4.x | `implementations/python-fastmcp`, `capstone/python-server` |
| TypeScript | **`@modelcontextprotocol/sdk`** 1.30.x | `implementations/typescript-sdk`, `capstone/typescript-client` |
| Java | **`io.modelcontextprotocol.sdk:mcp`** 2.0.x | `implementations/java-sdk`, `capstone/java-client` |
| Go | standard library (custom JSON-RPC/transport) | `repository/go`, `capstone/go-components` |
| Rust | standard library + `tokio`/`serde_json` (custom) | `repository/rust`, `capstone/rust-components` |

Versions, the protocol spec targeted, and what is / isn't locally verified are all in
**[docs/VERSIONS.md](docs/VERSIONS.md)** — read it before running anything.

---

## How to run examples

Each section's `examples/` folder contains small runnable programs. The heavy, fully
tested projects live in `implementations/`.

### Python (FastMCP)

```bash
cd implementations/python-fastmcp
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m server_stdio                             # run the stdio server
python -m client                                   # talk to it
```

### TypeScript

```bash
cd implementations/typescript-sdk
npm install
npm run build
npm run server:stdio
npm test
```

### Java

```bash
cd implementations/java-sdk
mvn test
mvn exec:java -Dexec.mainClass=com.example.mcp.Server
```

### Go / Rust (language lab)

```bash
cd repository/go && go test ./...
cd repository/rust && cargo test
```

## How to run tests

| Project | Command |
|---------|---------|
| Python/FastMCP | `cd implementations/python-fastmcp && pytest -q` |
| TypeScript | `cd implementations/typescript-sdk && npm test` |
| Java | `cd implementations/java-sdk && mvn test` |
| Go lab | `cd repository/go && go test ./...` |
| Rust lab | `cd repository/rust && cargo test` |
| Capstone Python server | `cd capstone/python-server && pytest -q` |

## How to run the capstone

The capstone is a realistic **incident-response agent** with an MCP server (Python),
a TypeScript agent client, a Java read-only client, and Go/Rust support components.

```bash
cd capstone
# 1. Start the MCP server (streamable HTTP)
cd python-server && pip install -e ".[dev]" && python -m incident_server --transport streamable-http --port 8000

# 2. In another terminal, run the TypeScript agent
cd typescript-client && npm install && npm run agent

# 3. Run the full test suite (server unit + integration + resilience)
cd capstone && ./run_tests.sh
```

See **[capstone/README.md](capstone/README.md)** for the full walkthrough and the
Docker Compose setup in `capstone/docker`.

## How to use this repository with a coding agent

This repository is written to be a reliable context source for vibe-coding agents:

1. Point the agent at `README.md` and `docs/VERSIONS.md` first.
2. Ask it to read a specific section before implementing, e.g.
   *"Read 04-tool-engineering/retries.md and 08-reliability-resilience/circuit-breakers.md,
   then add a retrying tool client."*
3. Every doc follows the same structure (What is it → How it works → Example →
   Production pattern → Testing → Debugging → Security), so an agent can extract the
   "how" without wading through prose.
4. Runnable code lives under `implementations/` and `capstone/`; the agent can run the
   tests to verify changes.

---

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for how to add sections, examples, or
implementations, and the accuracy rules we enforce (never invent SDK APIs, always
verify versions, keep the MCP-vs-general distinction).

## License

MIT — see **[LICENSE](LICENSE)**.
