# FastMCP Transforms

## What is it?

A **transform** modifies components as they flow from providers to clients — the
pipeline between "what the server owns" and "what the client sees"
([03-routing-dispatch/07-transform-routing.md](../03-routing-dispatch/07-transform-routing.md)).

```
Provider → [Transform A] → [Transform B] → Client
```

Built-in transforms include `Namespace` (prefix names), `ToolTransform` (rename/
re-describe), `Enabled` (visibility), `ToolSearch`, `ResourcesAsTools`,
`PromptsAsTools`.

## Why it exists

Three needs: **composition without collision** (namespace mounts), **versioning**
(expose everything as `v1_*`), and **surface control** (show different tool sets to
different clients). Transforms solve them in one layer instead of scattering renames
across handlers.

## How it works

- **Listing** (pure-function pattern): `list_tools(tools) -> tools` — transform the
  sequence.
- **Lookup** (middleware pattern): `get_tool(name, call_next)` — map the client's
  name back to the provider's name, call `call_next(original)`, transform the
  result. This bidirectional mapping is what makes `v1_search` resolve to `search`.
- **Order**: the first transform added is innermost (closest to the provider);
  later transforms see already-transformed names. Lookup reverses the chain.
- **Scope**: provider-level (one source) or server-level (all components).

## Example

Server-level namespacing (verified pattern):

```python
from fastmcp import FastMCP
from fastmcp.server.transforms import Namespace

mcp = FastMCP("app", transforms=[Namespace("v1")])

@mcp.tool
def search(query: str) -> list[str]:
    """Search the catalog."""
    return ["a", "b"]

# Client sees: v1_search; tools/call v1_search resolves to search()
```

Custom transform — filter by tag (from the FastMCP docs):

```python
from collections.abc import Sequence
from fastmcp.server.transforms import Transform, GetToolNext
from fastmcp.tools import Tool

class TagFilter(Transform):
    """Show only tools carrying the required tags."""

    def __init__(self, required_tags: set[str]):
        self.required_tags = required_tags

    async def list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]:
        return [t for t in tools if t.tags & self.required_tags]

    async def get_tool(self, name: str, call_next: GetToolNext) -> Tool | None:
        tool = await call_next(name)
        if tool and tool.tags & self.required_tags:
            return tool
        return None
```

## MCP-specific behavior

- **Nothing protocol-level** — transforms are invisible on the wire.
- **Bidirectional consistency is the hard part**: whatever `tools/list` shows, the
  same transform must reverse for `tools/call`. FastMCP derives both paths from one
  config.

## Common mistakes

- **One-way transforms** — renamed on list but not reversible on lookup (broken
  calls).
- **Order confusion** — later transforms see transformed names.
- **Filtering list but not get** — hidden-but-callable tools
  ([03-routing-dispatch/07-transform-routing.md](../03-routing-dispatch/07-transform-routing.md)).

## Testing

- **Round-trip tests**: list shows transformed names; call/get resolves them.
- **Order tests**: stacked transforms produce the expected final names.
- **Filter tests**: hidden components are invisible on both paths.

## Related

- [03-routing-dispatch/07-transform-routing.md](../03-routing-dispatch/07-transform-routing.md)
- [composition.md](composition.md)
- [03-routing-dispatch/06-provider-routing.md](../03-routing-dispatch/06-provider-routing.md)