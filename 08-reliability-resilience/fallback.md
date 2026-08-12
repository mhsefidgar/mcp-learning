# Capability-Aware Fallback

> **General engineering pattern.** Fallback is not an MCP feature; "capability-aware"
> means your fallback logic consults the negotiated capabilities.

## What is it?

**Fallback** is serving a degraded-but-useful answer when the primary path fails:
a second backend, a cached value, a simpler tool, or a clear "here's what you can
do instead." **Capability-aware** fallback means choosing the fallback based on what
the peer actually supports — never assuming a capability that wasn't declared.

## Why does MCP need it?

MCP clients and servers differ wildly in what they support. A client without
`sampling` can't be asked to generate; a server without `resources` can't serve a
resource-based answer. Capability-aware fallback is how systems degrade *smartly*:
the tool call fails on the primary path, and the fallback picks a path the peer can
actually handle — instead of failing again.

## How does it work?

1. **Know the capabilities**: the client's view of the server (and vice versa) from
   the handshake ([01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)).
2. **Define fallback tiers**: primary → cached → alternate tool → guidance error.
3. **On failure, pick the highest tier the peer supports**:
   - primary backend down → same tool on a mirror backend
   - expensive tool unavailable → cheaper equivalent tool
   - resource read fails → cached copy, with a "stale as of…" note
   - nothing works → an error that *tells the model what to do instead*
4. **Say what happened**: fallback results must be honest ("served from cache, may be
   stale") so the model doesn't mistake degraded data for fresh truth.

## Mental model

Fallback is an **emergency ladder**: the primary rung broke, so climb down to the
next rung that still holds — but check the ladder's manual (capabilities) first so
you don't reach for a rung that was never installed. And always tell someone which
rung you're standing on.

## MCP-specific behavior

- **Capabilities gate fallback options**: never fall back to `sampling/*` on a
  client that didn't declare it; never fall back to a resource read the server
  didn't declare.
- **`isError` results are the trigger**: a semantic failure ("backend unavailable")
  is the usual signal to fall back
  ([04-tool-engineering/errors.md](../04-tool-engineering/errors.md)).
- **Fallback output needs provenance**: "from cache", "from mirror", "degraded" —
  the model must be able to reason about data quality.

## Example

```python
@mcp.tool
async def current_price(symbol: str, ctx: Context) -> dict:
    """Current price for a symbol. Falls back to cached data on live failure."""
    try:
        return await live_price(symbol)
    except PriceFeedDown:
        cached = price_cache.get(symbol)
        if cached is not None:
            return {**cached, "source": "cache", "stale_at": cached["ts"]}
        # Capability-aware last resort: tell the model what to do.
        raise ToolError(
            f"Live price feed is down and no cache exists for {symbol}. "
            "Try quote_history instead, or retry shortly."
        )
```

## Industry-standard pattern

Failover, cache-as-fallback, and graceful degradation are standard in every HA
system (CDN fallbacks, database read replicas, feature flags). The MCP-specific
twist: the *error consumer is a model*, so the last-resort fallback should be a
**guidance message** ("try X instead") that lets the model reroute autonomously.

## Common mistakes

- **Falling back to something the peer can't do** — capability checks missing.
- **Silent fallback** — the model acts on degraded data as if it were fresh.
- **Fallback loops** — primary → fallback → primary → … (bound the attempts).
- **Fallback that hides the outage** — ops needs to know the primary is down;
  log it, alert on it.

## Testing

- **Tier tests**: each fallback tier triggers in its failure condition
  ([15-testing/failure-testing.md](../15-testing/failure-testing.md)).
- **Honesty tests**: fallback results carry provenance markers.
- **Capability tests**: fallbacks never use undeclared capabilities.
- **Loop tests**: fallback chains terminate.

## Security considerations

- **Cached fallbacks can serve stale (and wrong) data** — especially dangerous for
  authz-adjacent data; mark freshness clearly.
- **Fallback paths must enforce the same authorization** — a mirror backend with
  weaker checks is a hole.

## Related

- [caching.md](caching.md)
- [partial-failures.md](partial-failures.md)
- [remote-proxy-failures.md](remote-proxy-failures.md)
- [03-routing-dispatch/05-capability-routing.md](../03-routing-dispatch/05-capability-routing.md)