# Compatibility Testing

## What is it?

**Compatibility testing** verifies that a server (or client) works across the
MCP ecosystem: different SDK versions, different protocol versions, and
different client implementations. It answers "does my server work for *other*
clients, not just the one I wrote tests with?"

## Why does MCP need it?

MCP is an open protocol with many implementations — the TypeScript SDK, the Java
SDK, MCP Inspector, IDE integrations, agent frameworks. Each has its own quirks
and its own protocol-version support
([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)). A
server that only works with FastMCP's own client has failed its purpose. The
protocol is the contract; compatibility tests prove you honor it.

## How to test — the compatibility matrix

1. **Protocol versions**: initialize with an older `protocolVersion` and confirm
   graceful negotiation (or a clean failure), per
   [01-fundamentals/07-version-negotiation.md](../01-fundamentals/07-version-negotiation.md).
2. **Client implementations**: connect with at least one *other* client — the
   MCP Inspector ([07-inspector-debugging/README.md](../07-inspector-debugging/README.md))
   or the TypeScript SDK client — and run the same capability checks.
3. **Transport matrix**: stdio and Streamable HTTP both work, with the same
   tools ([01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)).
4. **SDK-version bumps**: after upgrading FastMCP, the protocol-visible surface
   (schemas, listings, messages) is unchanged — this is where schema snapshot
   tests shine ([schema-testing.md](schema-testing.md)).
5. **Strictness**: the server tolerates clients that omit optional fields,
   send extra fields, or use unusual but valid encodings.

## Example

The strongest tool is a **conformance harness**: a script that speaks raw
JSON-RPC over stdio and asserts on the exact wire messages — no SDK at all.
This repo's [01-fundamentals/examples/raw_handshake.py](../01-fundamentals/examples/raw_handshake.py)
is exactly that: it proves a server answers `initialize`, `tools/list`, and
`tools/call` with correctly-framed JSON-RPC. Extend it with your own assertions:

```python
# drive the server with raw JSON-RPC, assert framing + shapes
# (see 01-fundamentals/examples/stdio-exchange.md for the message format)
```

## MCP-specific behavior

- The stable spec (2025-11-25) requires the `initialize` handshake and
  session/`Mcp-Session-Id` for Streamable HTTP; the 2026-07-28 revision removes
  both ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).
  Compatibility tests should pin *which* spec your server implements and how it
  fails (or adapts) when faced with the other.
- Version-negotiation behavior (fallback vs. reject) is itself a compatibility
  contract worth testing.

## Industry-standard pattern

**Contract/conformance testing**: a separate suite (or CI job) that tests
*only* the wire contract, independent of SDKs. Combined with a matrix of real
clients in CI, it catches ecosystem breakage early.

## Common mistakes

- Testing only with the same SDK on both ends (client and server share bugs).
- Assuming the SDK hides all protocol details — test the wire when it matters.
- Ignoring protocol-version negotiation until a client with a newer version
  shows up.

## Related

- [13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)
- [07-inspector-debugging/README.md](../07-inspector-debugging/README.md)
- [01-fundamentals/examples/raw_handshake.py](../01-fundamentals/examples/raw_handshake.py)
- [schema-testing.md](schema-testing.md)
