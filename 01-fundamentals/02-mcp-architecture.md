# 02 — MCP Architecture

## What is it?

MCP's architecture is a **layered stack**. At the top are the application-facing
concepts (tools, resources, prompts). In the middle is the protocol layer (JSON-RPC
messages, methods, notifications). At the bottom is the transport (stdio or HTTP).

```
┌──────────────────────────────────────────────────────────────┐
│  APPLICATION LAYER                                            │
│  Tools · Resources · Prompts · (Sampling, Elicitation, ...)  │
├──────────────────────────────────────────────────────────────┤
│  PROTOCOL LAYER                                               │
│  JSON-RPC 2.0 messages  ·  methods (tools/call, ...)         │
│  requests / responses / errors / notifications               │
├──────────────────────────────────────────────────────────────┤
│  TRANSPORT LAYER                                              │
│  stdio (local)  ·  Streamable HTTP (remote)  ·  (SSE legacy) │
└──────────────────────────────────────────────────────────────┘
```

The layers are strict: the application layer knows nothing about whether the server is
local or remote, and the transport layer knows nothing about tools.

## Why does MCP need it?

Three reasons:

1. **One protocol, many transports.** The same `tools/call` message travels over a
   pipe to a local process or over HTTPS to a remote service. Splitting transport from
   protocol means you can develop locally (stdio) and deploy remotely (HTTP) with zero
   application changes.
2. **One message format, many capabilities.** JSON-RPC is generic; MCP adds a small
   vocabulary of methods (`tools/list`, `resources/read`, `prompts/get`, …) on top.
   The architecture keeps those two things separate so the protocol can grow.
3. **Strictly separated concerns let each layer be tested and secured independently.**
   You can unit-test a tool handler with no transport, and test a transport with no
   tools.

## How does it work?

1. A **client** chooses a transport (spawn a stdio process, or connect over HTTP) and
   creates a connection.
2. Over that connection, the client sends **JSON-RPC messages** (requests and
   notifications) whose `method` fields are MCP methods.
3. The server's **protocol layer** routes each message to the matching operation
   (see [03-routing-dispatch/01-request-dispatch.md](../03-routing-dispatch/01-request-dispatch.md)).
4. The **application layer** executes the tool/resource/prompt and returns a result,
   which the protocol layer wraps in a JSON-RPC response and the transport carries
   back.

## Mental model

Think of the **postal system**: the transport is the postal trucks (they only move
envelopes), the protocol layer is the envelope format and addressing rules, and the
application layer is the person inside the building who actually does the work. The
truck driver never reads the letter; the letter writer never drives the truck.

## MCP-specific behavior

- The **method namespace** is part of the protocol: `tools/*`, `resources/*`,
  `prompts/*`, `initialize`, `notifications/*`, etc. New capabilities add new methods
  under their own namespace.
- **Capabilities** (declared at initialization) tell each side which method groups the
  other side supports — so a server may legally ignore `resources/*` methods if it
  declared no resource capability.
- The **server can initiate requests to the client** (sampling, elicitation, roots) —
  that is unusual for HTTP-style architectures and is what makes MCP genuinely
  bidirectional at the application layer.
- SDKs (FastMCP, TS SDK, Java SDK) implement the protocol layer for you; you only write
  the application layer. Understanding the protocol layer is still essential for
  debugging (see [07-inspector-debugging](../07-inspector-debugging/README.md)).

## Example

The same server logic expressed at three different layers:

**Application layer (FastMCP):**

```python
@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b
```

**Protocol layer (what the client actually sends):**

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
 "params": {"name": "add", "arguments": {"a": 2, "b": 3}}}
```

**Transport layer (stdio, over the pipe):**

```
Content-Length: 123\r\n\r\n{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"add","arguments":{"a":2,"b":3}}}
```

## Industry-standard pattern

This three-layer split (application / protocol / transport) is the architecture of
every serious RPC system: **gRPC** (service definitions over HTTP/2), **WebSocket**
(subprotocols over TCP), **Jupyter** (kernels over ZMQ), **XMPP** (stanzas over TCP).
If you already understand one of those, MCP's architecture will feel familiar — the
novel part is the capability negotiation and the model-facing vocabulary.

## Common mistakes

- **Baking transport into application code** (e.g., reading from stdin inside a tool).
  Tools must be transport-agnostic; that is what makes the same server runnable over
  stdio and HTTP.
- **Implementing your own protocol layer** when an SDK exists, and getting the details
  (framing, IDs, error codes) subtly wrong. Use the SDK; go lower-level only in the
  language lab (`repository/`) to *learn*.
- **Treating the transport as the protocol** — e.g., building "an MCP server" that is
  really just an HTTP endpoint that happens to accept JSON.

## Testing

- Test the **application layer** in isolation (pure function tests).
- Test the **protocol layer** with the SDK's own client against your server (capability
  discovery, tool calls — see [15-testing](../15-testing/README.md)).
- Test the **transport layer** by running the server over both stdio and HTTP in CI
  (see [12-testing/compatibility-testing.md](../15-testing/compatibility-testing.md)).

## Debugging

- MCP Inspector (see [07-inspector-debugging](../07-inspector-debugging/README.md))
  shows you the protocol layer live: every request/response as it happens.
- When a call fails, classify the failure by layer *first*: did the message arrive
  (transport)? was it well-formed (protocol)? did the handler raise (application)?

## Security considerations

- Each layer has its own threat surface: transport (network sniffing → use TLS, see
  [11-communication-transport/tls.md](../11-communication-transport/tls.md)), protocol
  (malformed messages → schema validation, see
  [04-tool-engineering/validation.md](../04-tool-engineering/validation.md)), and
  application (malicious inputs → authorization, see
  [14-security/authorization.md](../14-security/authorization.md)).
- Keep layers separated *in your code* too: a transport bug should never be able to
  reach tool code without passing the protocol checks.

## Related concepts

- [01-client-server.md](01-client-server.md)
- [03-json-rpc.md](03-json-rpc.md)
- [08-transports.md](08-transports.md)
- [03-routing-dispatch/01-request-dispatch.md](../03-routing-dispatch/01-request-dispatch.md)
- [11-communication-transport/README.md](../11-communication-transport/README.md)
