# 09 — Version-Aware Routing

## What is it?

**Version-aware routing** is routing that changes *which implementation* a name
resolves to based on a version — either an explicit version in the name
(`orders_search_v1` / `orders_search_v2`) or a version carried in the request
(FastMCP's versioned components, selected via `version=` at call time). It answers:
"`v1` must keep behaving like v1, even after v2 ships."

## Why does MCP need it?

Tools, resources, and prompts are long-lived contracts. When you change a tool's
behavior, schema, or prompt text, *existing clients keep calling the old contract*.
Version-aware routing lets you ship v2 without breaking v1 — the standard
backward-compatibility strategy for any public API
([13-versioning/compatibility.md](../13-versioning/compatibility.md)).

## How does it work?

1. **Versioned registration**: the same logical capability is registered under
   multiple versions — either as distinct names (`orders_search_v1`,
   `orders_search_v2`) or as one name with versions (FastMCP component versioning).
2. **Resolution**: at dispatch time, the version is selected from the name, from an
   explicit call parameter (`version="v2"`), or from a default.
3. **Isolation**: each version has its own handler and schema; v1 code is *frozen* —
   bug fixes may be backported, but behavior stays compatible.
4. **Deprecation**: old versions are deprecated with a timeline
   ([13-versioning/deprecation.md](../13-versioning/deprecation.md)) and removed only
   when the policy allows.

```
tools/call "orders_search_v1" ──► v1 handler (frozen)
tools/call "orders_search_v2" ──► v2 handler (current)
```

## Mental model

Version-aware routing is a **compatibility adapter layer**: like REST APIs serving
`/v1/orders` and `/v2/orders`, or a library that keeps `v1` exports while adding `v2`.
The routing layer is the "translator" that keeps both alive.

## MCP-specific behavior

- **The protocol itself doesn't version tools** — a tool name is a name
  ([13-versioning/tool-resource-prompt-versions.md](../13-versioning/tool-resource-prompt-versions.md)).
  Versioning conventions are application/SDK-level.
- **FastMCP 3.x supports component versioning**: a component can carry a `version`,
  providers merge versions, and callers can request a specific version
  (`await mcp.call_tool("search", {...}, version="2.0")` or a version spec range).
- **Name-embedded versions** (`v1_`, `v2_`) are the portable, SDK-agnostic convention
  — they work with any client and any SDK, at the cost of longer names.
- **Protocol version ≠ component version** — the 2025-11-25 protocol negotiation
  ([01-fundamentals/07-version-negotiation.md](../01-fundamentals/07-version-negotiation.md))
  is orthogonal to tool-level versioning.

## Example

Name-embedded versioning (works everywhere):

```python
from fastmcp import FastMCP

mcp = FastMCP("orders")

@mcp.tool
def orders_search_v1(query: str) -> list[dict]:
    """v1: search by customer name only."""
    return db.search_by_name(query)

@mcp.tool
def orders_search_v2(query: str, include_cancelled: bool = False) -> list[dict]:
    """v2: search by name or id, optional cancelled orders."""
    return db.search(query, include_cancelled=include_cancelled)
```

FastMCP component versions (`version=` selection):

```python
@mcp.tool(version="1.0")
def analyze(data: str) -> str:
    """Original analysis."""
    return f"v1: {data}"

@mcp.tool(version="2.0")
def analyze(data: str) -> str:
    """Improved analysis with more context."""
    return f"v2 (enhanced): {data}"

# callers pick: await mcp.call_tool("analyze", {"data": "x"}, version="2.0")
# or leave unversioned for the default/highest version.
```

Compatibility adapter (explicit, in any SDK): a v1-named tool that translates to the
v2 implementation:

```python
@mcp.tool
def orders_search(query: str) -> list[dict]:
    """Deprecated alias: routes to the v2 implementation."""
    return orders_search_v2(query, include_cancelled=False)
```

## Industry-standard pattern

This is **API versioning done right**: frozen old versions, explicit version
selection, deprecation windows, and adapters for the transition. See how cloud APIs
(`/v1`, `/v2`), SDKs (semver majors), and databases (schema migrations) handle it —
the principles carry over directly
([13-versioning/compatibility.md](../13-versioning/compatibility.md)).

## Common mistakes

- **Mutating a v1 handler "just a little"** — that's a breaking change without a
  version bump.
- **Versioning only the name, not the schema/behavior** — v2 with v1's bugs.
- **No deprecation timeline** — old versions accumulate forever, or get removed
  overnight (see [13-versioning/deprecation.md](../13-versioning/deprecation.md)).
- **Forgetting that clients cache `tools/list`** — new versions must appear in the
  catalog before clients can discover them (send `list_changed`).

## Testing

- **Per-version tests**: each version's behavior and schema pinned by tests
  ([15-testing/compatibility-testing.md](../15-testing/compatibility-testing.md)).
- **Adapter tests**: the deprecated alias routes to the right implementation.
- **Catalog tests**: both versions are listed and discoverable.
- **Selection tests**: explicit `version=` requests resolve to the exact version, and
  invalid versions fail cleanly.

## Debugging

- A client calling `orders_search` and getting v2 behavior when it expected v1 →
  check the version-selection default (unversioned calls usually get the highest
  version).
- Catalog shows only one version → a transform (`Namespace`) or visibility filter is
  hiding the other; check [07-transform-routing.md](07-transform-routing.md).

## Security considerations

- **Old versions are old attack surface.** Track which versions are still exposed;
  deprecated versions should lose access to new permissions
  ([14-security/README.md](../14-security/README.md)).
- **Never backport security fixes to v1 silently** if the fix changes observable
  behavior — version it.
- Adapters must preserve the *authorization* of the version they adapt (don't widen
  permissions).

## Related concepts

- [02-tool-routing.md](02-tool-routing.md)
- [13-versioning/README.md](../13-versioning/README.md)
- [13-versioning/deprecation.md](../13-versioning/deprecation.md)
- [13-versioning/compatibility.md](../13-versioning/compatibility.md)
- [15-testing/compatibility-testing.md](../15-testing/compatibility-testing.md)