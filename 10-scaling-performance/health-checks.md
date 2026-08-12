# Health Checks

## What is it?

**Health checks** are lightweight endpoints (or probes) that report whether an
instance can serve traffic. Two kinds:

- **Liveness** (`/healthz`): "is the process alive?" — if not, kill/restart it.
- **Readiness** (`/readyz`): "is this instance *ready to serve*?" — if not, take it
  out of the load balancer ([load-balancing.md](load-balancing.md)) but don't kill
  it (it may be warming up, draining, or degraded).

## Why does MCP need it?

Every piece of MCP infrastructure consumes health checks:

- **Load balancers** route only to ready instances
  ([load-balancing.md](load-balancing.md)).
- **Orchestrators** (K8s) restart unresponsive instances.
- **Service discovery** de-registers dead instances
  ([multi-server-and-gateway.md](multi-server-and-gateway.md)).
- **Agents/clients** can probe a gateway before connecting.

An MCP server without health checks gets traffic it can't serve — and the resulting
timeouts/retries ([08-reliability-resilience/README.md](../08-reliability-resilience/README.md))
are far worse than a clean "not ready."

## How does it work?

1. **Expose `/healthz` and `/readyz`** on the HTTP server *outside* the MCP
   endpoint (plain HTTP GET — the MCP protocol doesn't define them).
2. **Liveness**: cheap — process up? (Return 200 or don't respond.)
3. **Readiness**: meaningful — can I serve an MCP request right now? Check the
   critical dependencies: database reachable, downstream healthy, not draining,
   not over capacity ([degradation-and-isolation.md](degradation-and-isolation.md)).
4. **Integrate**: point the LB/orchestrator at them.

## Mental model

Health checks are the **"open/closed" sign on the shop door**: liveness is "is the
shop standing?", readiness is "can you actually buy something right now?" A shop
that's standing but out of stock (readiness fails) shouldn't take your order — and
a shop being remodeled (draining) tells the sign to say "closed" before it
demolishes the counter.

## MCP-specific behavior

- **MCP has no health-check method** in the stable spec — `/healthz`/`/readyz` are
  plain HTTP endpoints alongside `/mcp`. (Don't confuse them with the MCP
  handshake.)
- **Readiness must reflect the MCP-relevant dependencies**: the database the tools
  use, the backends the gateway proxies
  ([03-routing-dispatch/12-remote-proxy-routing.md](../03-routing-dispatch/12-remote-proxy-routing.md)).
- **stdio servers need no health checks** — the process spawn *is* the check.

## Example

FastMCP custom route (FastMCP 3.x exposes `custom_route` for non-MCP endpoints):

```python
from fastmcp import FastMCP

mcp = FastMCP("app", lifespan=...)

@mcp.custom_route("/healthz")
async def healthz(request):
    return "ok"                          # liveness: process is up

@mcp.custom_route("/readyz")
async def readyz(request):
    if not db.ping():
        return "db unavailable", 503     # readiness: can't serve tools
    return "ready"
```

## Industry-standard pattern

Liveness/readiness separation is the K8s standard; probes with fast timeouts and
low frequency are the norm. Rules: **liveness stays cheap**, **readiness reflects
real dependencies**, **don't let readiness flaps flap the fleet** (hysteresis),
and **health checks are not the same as metrics** — they're binary doors.

## Common mistakes

- **One combined endpoint** — a dead DB kills liveness, and the orchestrator
  restarts a perfectly alive (but unready) process.
- **Lying readiness** — returning ready while the DB is down (the LB sends traffic
  into the wall).
- **Expensive readiness** — checking every dependency per probe at high frequency.
- **No drain signaling** — an instance can't say "stop sending, I'm leaving"
  ([load-balancing.md](load-balancing.md)).

## Testing

- **Liveness tests**: process up → 200; hung process → probe timeout.
- **Readiness tests**: DB down → 503; restored → 200.
- **LB integration tests**: unready instances receive no traffic.
- **Drain tests**: during drain, readiness flips before the instance stops.

## Security considerations

- **Health endpoints reveal internals** (dependency status, topology) — keep them
  minimal and protect them if exposed publicly.
- **Health endpoints are a free request path** — rate-limit like any surface.

## Related

- [load-balancing.md](load-balancing.md)
- [degradation-and-isolation.md](degradation-and-isolation.md)
- [multi-server-and-gateway.md](multi-server-and-gateway.md)
- [08-reliability-resilience/observability.md](../08-reliability-resilience/observability.md)