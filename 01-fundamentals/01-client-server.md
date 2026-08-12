# 01 — Client ↔ Server

## What is it?

MCP splits the world into two roles:

- **Client** — an application that wants to give an LLM access to external tools and
  data. Examples: an agent runtime, an IDE, a chat application.
- **Server** — a program that *exposes* capabilities: tools (things you can do),
  resources (data you can read), and prompts (reusable instructions).

The client connects to the server and, on the model's behalf, discovers and uses those
capabilities. One client can talk to many servers; one server serves one client at a
time in the common local (stdio) case.

```
┌─────────────┐   JSON-RPC messages    ┌─────────────┐
│   Client    │ ◄────────────────────► │   Server    │
│  (agent,    │      over a transport  │ (tools,     │
│   IDE, ...) │                        │  resources, │
└─────────────┘                        │  prompts)   │
                                       └─────────────┘
```

## Why does MCP need it?

Before MCP, every AI application had to build its own integration for every tool: "a
Slack plugin for ChatGPT, a Slack plugin for Claude, a Slack plugin for Copilot…".
The client/server split is the standardization: **one server implementation works with
every compliant client**, and **one client works with every compliant server**. This is
exactly the deal USB made for hardware: a standard socket, and any device plugs in.

## How does it work?

1. The **client** starts the connection (spawns the server process for stdio, or opens
   an HTTP connection for Streamable HTTP).
2. Client and server **introduce themselves** and negotiate protocol version and
   capabilities (see [05-initialization.md](05-initialization.md)).
3. The client **discovers** capabilities: `tools/list`, `resources/list`, `prompts/list`.
4. The model (through the client) **uses** them: `tools/call`, `resources/read`,
   `prompts/get`.
5. Either side can send **notifications** (progress, cancellation, logging) without
   expecting a reply.
6. Either side can **close** the connection when done.

The client is always the *initiator*: it connects, it initializes, it calls. The server
can, however, make *requests back* to the client (sampling, elicitation, roots) once
the session exists.

## Mental model

Think of the client as the **concierge** and the server as the **kitchen**. The model
(the guest) never talks to the kitchen directly. The concierge holds the menu (the
list of tools), takes the order (structured arguments), relays it to the kitchen, and
brings back the dish (the result). If the kitchen needs a clarification mid-order, it
asks the concierge (server → client requests), not the guest directly.

## MCP-specific behavior

- **Who is the client vs. server is fixed by the spec.** The LLM application is always
  the client side; the tool/data provider is always the server side. (A "server" that
  itself calls other MCP servers is a *client* of those — see
  [03-routing-dispatch/11-remote-proxy-routing.md](../03-routing-dispatch/11-remote-proxy-routing.md).)
- **Roles are asymmetric.** The client initiates; the server listens. But *after*
  initialization the channel is bidirectional: the server can send requests to the
  client.
- **Lifecycle is explicit** in the session-based protocol: initialize → initialized →
  operation → shutdown (see [09-sessions-and-lifecycle.md](09-sessions-and-lifecycle.md)).

## Example

The absolute minimum FastMCP server:

```python
# Educational simplification — not production-ready.
from fastmcp import FastMCP

mcp = FastMCP("greeter")

@mcp.tool
def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()  # stdio by default
```

And the minimal client (using FastMCP's client):

```python
import asyncio
from fastmcp import Client

async def main() -> None:
    # FastMCP 3.x infers a stdio transport from a script path
    async with Client("server.py") as client:
        result = await client.call_tool("greet", {"name": "Ada"})
        print(result)

asyncio.run(main())
```

The equivalent TypeScript server:

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

const server = new McpServer({ name: "greeter", version: "1.0.0" });

server.registerTool("greet", { description: "Greet someone by name" },
  async ({ name }: { name: string }) => ({ content: [{ type: "text", text: `Hello, ${name}!` }] }));

await server.connect(new StdioServerTransport());
```

Full runnable versions: `implementations/python-fastmcp`, `implementations/typescript-sdk`.

## Industry-standard pattern

Client/server with a discovery mechanism and a capability handshake is the standard
shape of remote procedure protocols everywhere: think gRPC (service definitions +
stubs), OpenAPI/HTTP (documented endpoints), or Jupyter (kernels exposed to clients).
MCP's specific contribution is that the *discovery* (`tools/list`) and the *contract*
(JSON Schema for arguments) are part of the protocol, so a model can adapt at runtime
to a server it has never seen.

## Common mistakes

- **Making the server call the client's tools.** A server that needs another server's
  capability should connect to it as a *client* (compose servers client-side, or use a
  proxy — see [03-routing-dispatch/11-remote-proxy-routing.md](../03-routing-dispatch/11-remote-proxy-routing.md)).
- **Assuming one server = one process per client is wasteful.** For stdio that's
  exactly how it works: each client spawns its own server process, which is why servers
  should be cheap to start and stateless (see [10-scaling-performance](../10-scaling-performance/README.md)).
- **Hard-coding client identity** instead of sending it during initialization — the
  client's `clientInfo` matters for server-side analytics and debugging.

## Testing

- Unit-test server handlers directly (call the Python function / the registered
  handler) without a transport.
- Integration-test the client↔server pair over a real transport (stdio or HTTP) — see
  [15-testing/integration-testing.md](../15-testing/integration-testing.md) and the
  test suites in `implementations/`.

## Debugging

- First question: **which side is failing?** Reproduce the call with the raw protocol
  using MCP Inspector (see [07-inspector-debugging](../07-inspector-debugging/README.md)).
- Enable protocol-level logging on both sides; the initialization exchange alone
  explains most "server not found" failures.
- For stdio, capture the server's stderr — it's the only place a crashed server speaks.

## Security considerations

- A server is arbitrary code running with the permissions of the user who launched it.
  The client must treat the server as *untrusted for its outputs* and *privileged for
  its inputs* (see [14-security/untrusted-output.md](../14-security/untrusted-output.md)).
- Remote (HTTP) servers must be authenticated before use
  ([14-security/authentication.md](../14-security/authentication.md)).
- stdio servers run with the client's environment: never pass secrets via environment
  variables you don't control, and beware of the server reading the client's files.

## Related concepts

- [02-mcp-architecture.md](02-mcp-architecture.md) — where the pieces live
- [03-json-rpc.md](03-json-rpc.md) — what the messages look like
- [05-initialization.md](05-initialization.md) — how the connection starts
- [02-primitives/tools.md](../02-primitives/tools.md) — what a server exposes
- [14-security/authentication.md](../14-security/authentication.md)
