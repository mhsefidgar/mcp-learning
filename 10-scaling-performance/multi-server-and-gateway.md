# Multi-Server Architectures, Gateways & Service Discovery

## What is it?

Production MCP deployments are rarely one server:

- **Multi-server agent architectures**: one agent connected to many MCP servers
  (tools, resources, and prompts from multiple sources)
  ([03-routing-dispatch/06-provider-routing.md](../03-routing-dispatch/06-provider-routing.md),
  [06-agent-interaction/README.md](../06-agent-interaction/README.md)).
- **Proxy/gateway scaling**: a gateway in front of many backend servers — one
  endpoint, centralized policy ([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)).
- **Provider scaling / horizontal composition**: the same logical server running as
  many instances, discovered and load-balanced.
- **Service discovery**: how clients/gateways find instances (DNS, registries).

## Why does MCP need it?

Three forces push toward multi-server:

1. **Modularity**: different teams own different servers (weather, calendar,
   finance); the agent needs all of them.
2. **Scale**: one server instance can't serve everyone; a fleet needs discovery and
   balancing.
3. **Governance**: a gateway centralizes auth, rate limits, and routing across
   backends that can't or shouldn't implement them individually.

## How does it work?

**Agent-side multi-server**: the agent connects to N servers (each with its own
session in the session-based spec) and routes each request to the right one —
usually by tool naming (`weather_forecast`, `calendar_events`) or by an internal
router ([16-end-to-end/architecture.md](../16-end-to-end/architecture.md)).

**Gateway-side aggregation**: the gateway is a client of the backends and a server
to the agents; it merges catalogs (with namespaces to avoid collisions) and
forwards calls ([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)).

**Discovery**: instances register with a registry (DNS SRV, Consul, K8s Service);
clients/gateways resolve and load-balance
([session-affinity.md](session-affinity.md) for the stateful case).

```
                   ┌──────────┐  ┌──────────┐  ┌──────────┐
Agent ──► Gateway ─► backend-A│  │ backend-B│  │ backend-C│
                   └──────────┘  └──────────┘  └──────────┘
                        └────── service discovery / registry ──────┘
```

## Mental model

Multi-server MCP is a **franchise with a central phone line**: customers (agents)
call one number (the gateway); the operator routes to the right branch (backend),
and branches are added/removed from the directory (discovery) without customers
noticing. Each branch may itself be a chain (instance fleet).

## MCP-specific behavior

- **Each session-based connection carries its own session** — a multi-server agent
  holds one session per server; a gateway holds one session per backend. Session
  state does not flow between them
  ([01-fundamentals/09-sessions-and-lifecycle.md](../01-fundamentals/09-sessions-and-lifecycle.md)).
- **Name collisions across servers** are the #1 integration bug — namespace
  aggressively ([03-routing-dispatch/07-transform-routing.md](../03-routing-dispatch/07-transform-routing.md)).
- **The stateless 2026-07-28 spec simplifies the fleet half**: round-robin, no
  affinity, any instance serves any request
  ([scaling-fundamentals.md](scaling-fundamentals.md)).

## Example

Multi-server client (FastMCP supports config-driven multi-server clients via
`MCPConfig` — a dict of `mcpServers` — where each server's components are prefixed
with the server name):

```python
from fastmcp import Client

config = {
    "mcpServers": {
        "weather": {"url": "http://weather-svc/mcp"},
        "calendar": {"url": "http://calendar-svc/mcp"},
    }
}

async with Client(config) as client:
    tools = await client.list_tools()
    # names arrive prefixed: weather_forecast, calendar_events
```

## Industry-standard pattern

Gateway + service mesh + registry is the standard architecture for any microservice
system (K8s Services, Consul, API gateways). The MCP-specific notes: gateways must
relay server→client requests
([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)),
and **health checks** keep discovery honest
([degradation-and-isolation.md](degradation-and-isolation.md)).

## Common mistakes

- **Unprefixed name collisions** across composed servers.
- **A gateway that can't relay elicitation/sampling** — interactive features break
  silently ([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)).
- **Static backend lists** — no discovery, no autoscaling
  ([performance-engineering.md](performance-engineering.md)).
- **The gateway as a hidden single point of failure** — run it as a fleet with its
  own health checks.

## Testing

- **Multi-server tests**: an agent calls tools on N servers correctly
  ([15-testing/integration-testing.md](../15-testing/integration-testing.md)).
- **Gateway merge tests**: catalogs merge without collisions (namespace tests).
- **Discovery tests**: adding/removing instances updates routing.
- **Failover tests**: a dead backend is removed from rotation
  ([08-reliability-resilience/fallback.md](../08-reliability-resilience/fallback.md)).

## Security considerations

- **The gateway concentrates risk** — it deserves the strongest auth/audit
  ([14-security/auditability.md](../14-security/auditability.md)).
- **Backend identity**: the gateway's credentials to each backend must be scoped;
  never blindly forward client tokens
  ([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)).
- **Discovery is an attack surface** — a poisoned registry reroutes traffic; secure
  the registry ([14-security/README.md](../14-security/README.md)).

## Related

- [03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)
- [session-affinity.md](session-affinity.md)
- [degradation-and-isolation.md](degradation-and-isolation.md)
- [16-end-to-end/architecture.md](../16-end-to-end/architecture.md)