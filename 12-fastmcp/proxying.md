# FastMCP Proxying

## What is it?

**Proxying** is exposing a *remote* MCP server through your local server — the
remote's tools/resources/prompts become part of your catalog, and calls are
forwarded. Your server is simultaneously a **server** (to its clients) and a
**client** (to the remote). The remote connection becomes a `ProxyProvider`
([providers.md](providers.md)).

## Why it exists

Three use cases:

1. **Transport bridging**: expose a remote HTTP-only server to a stdio-only client.
2. **Aggregation**: one endpoint in front of many remote backends.
3. **Control**: apply your middleware (auth, rate limits, logging) to remote
   capabilities you don't own.

## How it works (verified API)

```python
from fastmcp import FastMCP, Client
from fastmcp.server.providers import ProxyProvider

async def build_gateway() -> FastMCP:
    mcp = FastMCP("gateway")

    client = Client("https://backend.example.com/mcp")   # a client to the remote
    mcp.add_provider(ProxyProvider(client))               # exposed through us

    return mcp
```

The remote's tools appear in `tools/list`; calls route to the remote; responses
relay back. Namespace the proxy if collisions are possible
(`mcp.mount(remote_server, namespace="backend")` style transforms apply).

## The hard part: relaying server→client requests

If the remote uses **elicitation** (or, in the old world, sampling/roots), the
proxy must relay: forward the remote's question to *your* client, collect the
answer, and return it to the remote. Naive forwards get this wrong. In the
session-based protocol this requires the proxy to hold its own session with the
remote and its own connection to the client
([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)).

## MCP-specific behavior

- **Sessions don't propagate**: your client's session is with you; your sessions
  are with each backend — independent state at each hop
  ([01-fundamentals/09-sessions-and-lifecycle.md](../01-fundamentals/09-sessions-and-lifecycle.md)).
- **The stateless 2026-07-28 spec makes proxying easier**: self-describing requests
  and header-based routing (`Mcp-Method`/`Mcp-Name`) let gateways route without
  parsing bodies ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).

## Common mistakes

- **No timeouts on forwarded calls** — one slow backend hangs every client
  ([04-tool-engineering/timeouts.md](../04-tool-engineering/timeouts.md)).
- **Not relaying elicitation** — interactive features silently break.
- **Leaking backend error internals** through the relay
  ([03-routing-dispatch/10-error-routing.md](../03-routing-dispatch/10-error-routing.md)).
- **SSRF-style forwarding** — validate destinations
  ([14-security/README.md](../14-security/README.md)).

## Testing

- **Forwarding tests**: a remote tool call arrives at the backend verbatim and its
  response returns ([15-testing/integration-testing.md](../15-testing/integration-testing.md)).
- **Failure tests**: backend down → defined proxy error, not a hang.
- **Relay tests**: backend elicitation reaches the client and the answer returns.

## Related

- [providers.md](providers.md)
- [03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)
- [10-scaling-performance/multi-server-and-gateway.md](../10-scaling-performance/multi-server-and-gateway.md)
- `capstone/` — a gateway in practice