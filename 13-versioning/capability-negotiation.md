# Capability Negotiation

## What is it?

**Capability negotiation** is how two peers agree *which features* they'll use —
declared at the handshake in the session-based spec
([01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)), and
per-request in the 2026-07-28 stateless spec. Capabilities are the feature flags of
the protocol: undeclared = unusable.

## How it changes across versions

**Session-based (2025-11-25):** capabilities are exchanged *once* in the
`initialize` handshake — a static map for the session's lifetime. Both sides record
it and behave accordingly.

**Stateless (2026-07-28):** there's no handshake, so client capabilities travel
**per request** in `_meta` — each request is a fresh "introduction." Servers can't
assume anything from a previous request
([protocol-versions.md](protocol-versions.md)).

## The rules

1. **Declared ⇒ honor it.** If you declared `resources.subscribe`, implement it.
2. **Undeclared ⇒ don't use it.** Never call methods in an undeclared namespace
   ([03-routing-dispatch/05-capability-routing.md](../03-routing-dispatch/05-capability-routing.md)).
3. **Optional features are optional** — clients must work with any subset
   (tools/resources/prompts are the core; everything else — sampling, elicitation,
   completions — may be absent).
4. **Sub-flags gate specifics** — `listChanged`, `subscribe` are finer-grained
   contracts within a capability.
5. **Version-aware defaults**: the negotiated protocol version defines which
   capabilities *exist*. A 2026-07-28 client talking to a 2025-11-25 server must
   not send 2026-only capabilities, and vice versa
   ([compatibility.md](compatibility.md)).

## Mental model

Capability negotiation is the **résumé exchange** from
[01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md): in the
session era you exchange résumés once per job; in the stateless era you hand your
business card with every interaction. Either way, you only offer skills you actually
have, and you only request skills the other side listed.

## MCP-specific behavior

- **The capability set is version-dependent**: elicitation arrived in 2025-06-18;
  tasks/extensions in 2026-07-28; sampling/roots deprecated in 2026-07-28
  ([deprecation.md](deprecation.md)).
- **SDKs handle the mechanics** — but *you* decide what to declare, and the
  declaration must match what you registered
  ([01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)).

## Example

A version-aware capability check (client side):

```python
init = client.initialize_result
caps = init.capabilities if init else None

if caps and caps.resources and caps.resources.subscribe:
    await client.send_request("resources/subscribe", {"uri": uri})
else:
    # capability absent or version doesn't support it — poll or read once
    pass
```

## Common mistakes

- **Declaring more than you implement** (the #1 interop bug).
- **Assuming capabilities persist across requests in the stateless era** — they
  ride in `_meta` per request.
- **Using 2026-only capabilities against a 2025 server** and vice versa.

## Testing

- **Capability-discovery tests**: the peer's capability map is read correctly
  ([15-testing/capability-testing.md](../15-testing/capability-testing.md)).
- **Version-matrix tests**: capabilities behave correctly across negotiated
  versions ([15-testing/compatibility-testing.md](../15-testing/compatibility-testing.md)).

## Related

- [01-fundamentals/06-capabilities.md](../01-fundamentals/06-capabilities.md)
- [compatibility.md](compatibility.md)
- [protocol-versions.md](protocol-versions.md)
- [03-routing-dispatch/05-capability-routing.md](../03-routing-dispatch/05-capability-routing.md)