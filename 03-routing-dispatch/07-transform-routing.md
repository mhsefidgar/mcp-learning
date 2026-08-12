# 07 — Transform Routing

> **Framework concept.** Transforms are a **FastMCP** (3.0+) feature. They are not part
> of the MCP protocol. They modify components as they flow from providers to clients.

## What is it?

A **transform** is a filter in the pipeline between providers and clients. When a
client asks "what tools do you have?", the components pass through each transform
before being returned. Transforms can:

- **Namespace** — prefix names (`search` → `v1_search`)
- **Rename / re-describe** — change a tool's name, description, or arguments
- **Filter** — hide components (per-session visibility, tag filtering)
- **Search** — replace a huge catalog with on-demand lookup
- **Bridge** — expose resources or prompts *as tools* for tool-only clients

```
Provider → [Transform A] → [Transform B] → Client
```

## Why does MCP need it? (Why FastMCP needs it)

Because the *provider's* view of a component and the *client's* view must be able to
differ. Three concrete needs:

1. **Composition without collision**: mount two servers that both define `search` —
   namespace each mount.
2. **API versioning**: expose everything as `v1_*` today, `v2_*` tomorrow, from one
   registry.
3. **Surface control**: show different tool sets to different clients/sessions
   without duplicating registration.

Transforms solve all three at one layer instead of sprinkling renames across handlers.

## How does it work?

- **Listing** (pure-function pattern): `list_tools(tools) -> tools` — the transform
  receives the sequence and returns a transformed sequence.
- **Lookup** (middleware pattern): `get_tool(name, call_next)` — the transform maps
  the *client's* name back to the provider's name, calls `call_next(original)`, then
  transforms the result. This is what makes `v1_search` resolve to the real `search`.
- **Order**: transforms stack — the first added is innermost (closest to the
  provider); the last added sees already-transformed names. On lookup, the chain
  reverses.
- **Scope**: provider-level transforms (one source) or server-level transforms (all
  components).

## Mental model

Transforms are **onion layers around the catalog**: names get wrapped as they go out
and unwrapped as they come back in. Think of URL rewriting in a reverse proxy — the
public URL differs from the internal URL, and the mapping is bidirectional.

## MCP-specific behavior

- **Nothing protocol-level here.** The client sees final names only; transforms are
  invisible on the wire.
- **Bidirectional consistency is the hard part**: whatever `tools/list` shows, the
  *same* transform must reverse for `tools/call`. FastMCP guarantees this by applying
  transforms on both paths from one configuration.
- Built-in transforms: `Namespace`, `ToolTransform`, `Enabled` (visibility),
  `ToolSearch`, `ResourcesAsTools`, `PromptsAsTools`.

## Example

Server-level namespacing (all tools become `v1_<name>`):

```python
from fastmcp import FastMCP
from fastmcp.server.transforms import Namespace

mcp = FastMCP("app", transforms=[Namespace("v1")])

@mcp.tool
def search(query: str) -> list[str]:
    """Search the catalog."""
    return ["a", "b"]

# Client sees: v1_search
```

Rename via `ToolTransform` (from the FastMCP docs):

```python
from fastmcp.server.providers import FastMCPProvider
from fastmcp.server.transforms import Namespace, ToolTransform
from fastmcp.tools.tool_transform import ToolTransformConfig

sub_server = FastMCP("Sub")

@sub_server.tool
def process(data: str) -> str:
    return f"Processed: {data}"

provider = FastMCPProvider(sub_server)
provider.add_transform(Namespace("api"))                       # process -> api_process
provider.add_transform(ToolTransform({
    "api_process": ToolTransformConfig(description="Process data through the API"),
}))

main = FastMCP("Main", providers=[provider])
```

Custom transform (filter by tag) — from the FastMCP docs:

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

## Industry-standard pattern

Bidirectional name mapping at a boundary is a **proxy/adaptor pattern**: reverse
proxies rewrite URLs, service meshes rewrite route names, and API gateways map public
contracts to internal services. The lesson: the mapping must be *deterministic and
reversible*, and it must live in exactly one place so list and call can't diverge.

## Common mistakes

- **One-way transforms** — renaming on list but not reversing on lookup (broken
  calls).
- **Transform order confusion** — expecting the last-added transform to see original
  names (it sees transformed ones).
- **Filtering on list but not on get** — a hidden tool still callable by name
  (both paths must filter).
- **Using transforms where a plain rename in registration would do** — transforms are
  for *systematic* changes; a single rename belongs in the tool definition.

## Testing

- **Round-trip tests**: for every transformed component, list shows the transformed
  name *and* get/call resolves it to the right handler.
- **Order tests**: stacking two transforms produces the expected final names.
- **Filter tests**: hidden components are invisible on both list and lookup.
- **Scope tests**: provider-level transforms don't affect other providers.

## Debugging

- A client that "sees" a tool but can't call it → a broken reverse mapping in a
  transform. Test the round trip directly.
- Names unexpectedly prefixed → a server-level `Namespace` is active; check
  `FastMCP(transforms=[...])`.

## Security considerations

- **Transforms are not authorization.** Hiding a tool via a visibility transform
  doesn't prevent a crafted direct call — pair with real authorization
  ([08-authorization-routing.md](08-authorization-routing.md)).
- **Resources-as-tools / prompts-as-tools** widen the surface: they create new
  callable names from read-only/static content — make sure the transformed tools carry
  the same security posture as their source.

## Related concepts

- [06-provider-routing.md](06-provider-routing.md)
- [09-version-aware-routing.md](09-version-aware-routing.md)
- [12-fastmcp/transforms.md](../12-fastmcp/transforms.md)
- [14-security/authorization.md](../14-security/authorization.md)