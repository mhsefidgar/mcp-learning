# Glossary

Short, plain-language definitions of the terms used throughout this repository.
Terms are grouped by the layer they belong to (protocol / SDK / general engineering),
mirroring the distinction we keep everywhere.

## Protocol terms (defined by the MCP specification)

- **MCP (Model Context Protocol)** — An open protocol that lets an LLM application
  (the *client*) discover and call *tools*, read *resources*, and use *prompts*
  exposed by an external program (the *server*). Think of it as a USB-C port for AI:
  any compliant client can plug into any compliant server.

- **Client** — The application that initiates the connection and drives the
  conversation (e.g., an agent, an IDE, a chat app). It calls tools, reads resources,
  and retrieves prompts.

- **Server** — The program that *exposes* capabilities. It owns the tools/resources/
  prompts and executes them. A server can be local (stdio) or remote (HTTP).

- **Tool** — An executable operation the model can invoke with structured arguments,
  e.g. `search_orders`. Defined by a name, a description, and a JSON Schema for its
  input. Tools *do* things.

- **Resource** — A piece of *data* exposed to the client, addressed by a URI, e.g.
  `file:///etc/config.json` or `db://users/42`. Resources *provide* context.

- **Resource template** — A URI pattern with parameters, e.g.
  `db://users/{id}`, that resolves to many resources.

- **Prompt** — A reusable *instruction template* the server offers the client, with
  optional arguments, e.g. a "summarize this bug report" prompt. Prompts *guide* the
  model.

- **JSON-RPC** — The wire protocol MCP messages are encoded in. A lightweight
  Remote Procedure Call format: `request`, `response`, `error`, `notification`.

- **Request** — A JSON-RPC message with an `id` that expects a response. e.g.
  `tools/call`.

- **Notification** — A JSON-RPC message *without* an `id`; fire-and-forget, no
  response. e.g. `notifications/cancelled`, `notifications/progress`.

- **Initialization** — The handshake (`initialize` / `initialized`) at the start of a
  session where client and server agree on protocol version and capabilities.
  *(Removed in the 2026-07-28 stateless spec.)*

- **Capabilities** — The set of features a client or server declares it supports
  during initialization (tools, resources, prompts, sampling, etc.).

- **Transport** — The mechanism that carries JSON-RPC messages between client and
  server: **stdio** (local, over standard input/output) or **Streamable HTTP**
  (remote, over HTTP).

- **Session** — A logical connection between a client and a server that persists
  across multiple messages (identified by `Mcp-Session-Id` in the session-based spec).

- **Sampling** — *(deprecated in 2026-07-28)* A server asking the client to generate
  an LLM completion on its behalf.

- **Elicitation** — A server asking the client (and through it, the user) for input
  *during* a tool call, e.g. a confirmation or a missing parameter.

- **Roots** — *(deprecated in 2026-07-28)* Filesystem or URI roots the client offers
  the server as context.

- **MRTR (Multi Round-Trip Requests)** — The 2026-07-28 mechanism that lets a server
  ask for more input mid-call over a stateless connection: it returns
  `resultType: "input_required"` with its questions, and the client retries with
  `inputResponses`.

## SDK / framework terms

- **FastMCP** — The Python framework (Prefect) for building MCP servers, clients, and
  interactive apps. `@mcp.tool`, `@mcp.resource`, `@mcp.prompt` decorators turn Python
  functions into MCP capabilities.

- **Provider** — In FastMCP, a *source* of components (tools/resources/prompts).
  `LocalProvider` (your decorators), `FastMCPProvider` (a mounted server),
  `ProxyProvider` (a remote server).

- **Transform** — In FastMCP, a filter that modifies components as they flow from
  providers to clients (e.g. `Namespace` prefixes names).

- **Middleware** — In FastMCP, a pipeline that intercepts requests/responses for
  cross-cutting concerns (auth, logging, rate limiting). *FastMCP-specific, not part of
  the MCP spec.*

- **`McpServer` / `McpClient`** — Core classes in the TypeScript and Java SDKs for
  building servers and clients.

- **`Context`** — In FastMCP, an injected object giving your tool/resource/prompt
  access to logging, progress, resources, prompts, and request state.

## General engineering terms (NOT MCP features)

- **Retry** — Re-attempting a failed operation, usually with backoff. General pattern.
- **Exponential backoff** — Doubling the wait between retries. Often combined with
  **jitter** (randomness) to avoid thundering herds.
- **Circuit breaker** — Stops calling a failing dependency for a cooldown period to
  let it recover. General resilience pattern.
- **Bulkhead** — Isolating failures by partitioning resources (e.g. per-tool worker
  pools) so one failure can't exhaust everything.
- **Rate limiting** — Capping how many requests a client/consumer may make in a
  window. General pattern.
- **Backpressure** — Signaling a producer to slow down when a consumer can't keep up.
- **Idempotency** — Ensuring repeating an operation produces the same result (via
  idempotency keys).
- **Connection pooling** — Reusing a fixed set of connections instead of opening a new
  one per request.
- **Observability** — Structured logging, metrics, and distributed tracing, usually
  via OpenTelemetry.
- **Distributed tracing** — Tracking one logical request across many service
  boundaries (spans, trace IDs).
- **Deadline** — A time limit for an operation; when exceeded, the operation is
  cancelled.
