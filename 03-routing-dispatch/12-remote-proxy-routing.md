# 12 — Remote/Proxy Routing

## What is it?

**Remote/proxy routing** is the pattern where a request arriving at *your* server is
forwarded to *another* MCP server, and the response is relayed back — while the
client sees only your server. Your server acts as a **gateway or proxy**:

```
┌────────────┐   tools/call    ┌─────────────────┐   tools/call    ┌────────────────┐
│   Client   │ ──────────────► │  Proxy server   │ ──────────────► │  Remote MCP    │
│            │ ◄────────────── │  (your code)    │ ◄────────────── │  server        │
└────────────┘   response      └─────────────────┘   response      └────────────────┘
```

Routing here is per-component: some requests are handled locally, others are
forwarded — the proxy decides which is which (local capability vs. remote
capability).

## Why does MCP need it?

Real deployments need **bridging and aggregation**:

- **Transport bridging**: expose a remote HTTP-only MCP server to a local stdio-only
  client (or vice versa).
- **Aggregation**: one endpoint in front of many backend servers
  ([10-scaling-performance/multi-server-architectures.md](../10-scaling-performance/multi-server-architectures.md)).
- **Control**: the gateway can enforce auth, rate limits, and policy on top of
  backend servers that don't have them.
- **Namespace isolation**: expose subsets of remote capabilities under prefixed names.

## How does it work?

1. **Connect**: the proxy opens a *client* connection to each remote MCP server
   (the proxy is a client of the backends).
2. **Expose**: the proxy registers the remote capabilities as its own — via a
   `ProxyProvider` (FastMCP) or by forwarding at the protocol layer.
3. **Route**: for each inbound request, the proxy decides:
   - local handler → run it
   - remote capability → forward the request to the owning backend, await, relay
4. **Translate**: namespaces/transforms map public names to backend names and back
   ([07-transform-routing.md](07-transform-routing.md)).
5. **Fail over**: if the backend fails, the proxy applies its resilience policy
   (timeout, retry, circuit breaker — see
   [08-reliability-resilience/README.md](../08-reliability-resilience/README.md)).

## Mental model

The proxy is a **travel agent**: you hand it your request; it decides whether to
answer from its own desk (local) or call a partner agency (remote), then brings back
the result. You never talk to the partner agency directly.

## MCP-specific behavior

- **A proxy is simultaneously a server and a client.** It speaks server-side to its
  clients and client-side to its backends — the two roles are per-connection, not per
  process.
- **Sessions don't propagate**: the client's session is with the proxy; the proxy's
  sessions are with each backend. State at each hop is independent
  ([01-fundamentals/09-sessions-and-lifecycle.md](../01-fundamentals/09-sessions-and-lifecycle.md)).
- **Server→client features (sampling, elicitation) must be *relayed***: if a backend
  elicits, the proxy must forward the elicitation to *its* client and relay the
  answer. This is one of the hardest parts of proxying (FastMCP's `ProxyProvider`
  handles it; hand-rolled proxies frequently get it wrong).
- **In the 2026-07-28 stateless spec**, proxying gets *easier*: requests are
  self-describing, and `Mcp-Method`/`Mcp-Name` headers let gateways route without
  parsing bodies ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).

## Example

FastMCP proxying (from the FastMCP docs — `create_proxy`):

```python
from fastmcp import FastMCP, Client
from fastmcp.server.providers import ProxyProvider

async def build_proxy() -> FastMCP:
    mcp = FastMCP("gateway")

    # Connect to a remote server as a client...
    client = Client("https://backend.example.com/mcp")
    await client.connect()  # in FastMCP 3.x: async with Client(...)

    # ...and expose it through this server.
    mcp.add_provider(ProxyProvider(client))

    return mcp
```

Hand-rolled forwarding (educational simplification — shows the routing decision):

```python
async def route(self, request):
    if request.method == "tools/call":
        tool_name = request.params["name"]
        if tool_name in self.local_tools:
            return await self.run_local(request)          # local capability
        if tool_name in self.remote_tools:
            return await self.forward(request)            # remote capability
        return self.not_found(tool_name)                  # error route
```

## Industry-standard pattern

This is the **API gateway / reverse proxy / BFF (backend-for-frontend)** pattern from
web architecture, applied to MCP: aggregation, translation, policy enforcement, and
resilience at one edge. Everything you know about gateway design (timeouts, retries,
rate limiting, circuit breakers, observability) applies here
([10-scaling-performance/proxy-gateway-scaling.md](../10-scaling-performance/proxy-gateway-scaling.md)).

## Common mistakes

- **Forgetting that the proxy must relay server→client requests** — sampling and
  elicitation silently break in naive forwards.
- **No timeouts on forwarded calls** — one slow backend hangs every client.
- **Relaying errors without translation** — backend error text leaking internal
  names/URLs.
- **Session leaks** — proxy sessions to backends opened but never closed.
- **Circular proxying** — proxy A → proxy B → proxy A (add hop limits).

## Testing

- **Forwarding tests**: a remote tool call arrives at the backend verbatim (capture
  with a mock backend) and its response returns unchanged.
- **Local/remote split tests**: local names run locally, remote names forward, unknown
  names error ([15-testing/integration-testing.md](../15-testing/integration-testing.md)).
- **Failure tests**: backend down → defined proxy error (timeout/502-equivalent), not
  a hang ([15-testing/failure-testing.md](../15-testing/failure-testing.md)).
- **Relay tests**: backend elicitation reaches the client and the answer returns.

## Debugging

- **Tracing is essential**: add a per-request trace id at the gateway so you can
  follow client → proxy → backend across logs
  ([09-observability-telemetry/distributed-tracing.md](../09-observability-telemetry/distributed-tracing.md)).
- "Works directly, fails through the proxy" → check transport/session/header
  differences at each hop (Inspector on both sides).
- Test the backend directly first: the proxy is only as good as the boundary it
  crosses.

## Security considerations

- **The proxy must not become a SSRF gadget**: validate that forwarded destinations
  are allowed hosts ([14-security/README.md](../14-security/README.md)).
- **Identity propagation**: the proxy's auth to backends must be scoped — don't
  forward the client's token blindly unless the backend is trusted.
- **The gateway is a choke point**: it concentrates risk, so it deserves the
  strongest auth, rate limiting, and audit logging
  ([14-security/auditability.md](../14-security/auditability.md)).

## Related concepts

- [06-provider-routing.md](06-provider-routing.md)
- [08-reliability-resilience/remote-proxy-failures.md](../08-reliability-resilience/remote-proxy-failures.md)
- [10-scaling-performance/proxy-gateway-scaling.md](../10-scaling-performance/proxy-gateway-scaling.md)
- [12-fastmcp/proxying.md](../12-fastmcp/proxying.md)
- [16-end-to-end/architecture.md](../16-end-to-end/architecture.md)