# Static Resources

## What is it?

A **static resource** is a resource whose content is fixed at registration time (or
changes rarely): a config file, a schema, a version banner. It has one concrete URI
(`config://app/settings`) listed in `resources/list`, and reading it returns the same
content until the server updates it.

## Why does MCP need it?

Static resources are the *simplest* contract for handing context to a model: "here is
the config, read it whenever you need it." They're cheap to list, cache, and reason
about — and they form the base case that dynamic resources and templates build on.

## How does it work?

1. **Register** the resource with a URI, name, description, and mime type.
2. **List**: it appears in `resources/list` with its metadata.
3. **Read**: `resources/read` returns its content (typically loaded from a file or
   string at registration).
4. **Change**: when the underlying value changes, re-register/update it and (if
   supported) notify subscribers ([subscriptions.md](subscriptions.md)).

## Mental model

A static resource is a **checked-in file**: content that ships with the server and is
read many times. Like `README.md` or `config.json` in a repo — stable, addressable,
rarely changing.

## MCP-specific behavior

- **Static vs. dynamic is a spectrum, not a protocol distinction.** The protocol
  treats all resources the same; "static" just means content doesn't change per read.
- **Metadata matters**: `name`, `description`, and `mimeType` help the client/model
  decide *whether* to read and *how* to parse.
- **`resources/list` may be paginated** (cursor) for large catalogs
  ([pagination.md](pagination.md)).

## Example

```python
from fastmcp import FastMCP

mcp = FastMCP("app")

@mcp.resource("config://app/settings")
def settings() -> str:
    """Application settings (JSON)."""
    return '{"env": "production", "region": "us-east-1", "feature_flags": ["search-v2"]}'
```

TypeScript SDK:

```typescript
server.registerResource(
  "config://app/settings",
  "Application settings",
  async (uri) => ({ contents: [{ uri, text: JSON.stringify(settings) }] })
);
```

## Industry-standard pattern

Stable, addressable, cacheable content is the model of **static files served by a CDN
or object store**: immutable-ish, cached aggressively, refreshed by a defined
mechanism. If a resource truly never changes, tell clients — cache it
([08-reliability-resilience/caching.md](../08-reliability-resilience/caching.md)).

## Common mistakes

- **Pretending something dynamic is static** — content that changes per read (time,
  user) belongs in dynamic resources.
- **No mimeType** — clients can't tell JSON from plain text.
- **Missing descriptions** — the model can't decide when to read it.

## Testing

- **List/read tests**: appears in `resources/list`; reads return expected content
  ([15-testing/resource-testing.md](../15-testing/resource-testing.md)).
- **Stability tests**: two reads return identical content.
- **Metadata tests**: name/description/mimeType correct.

## Debugging

- In Inspector: list resources, read by hand, compare against expectations. Static
  resources are the easiest thing to debug — if a read fails, the URI or the handler
  is wrong.

## Security considerations

- Static content can still be **sensitive** — authorize reads per client
  ([14-security/authorization.md](../14-security/authorization.md)).
- Never put secrets in resources that any client can list (e.g. don't register
  `config://secrets` without auth).

## Related concepts

- [dynamic-resources.md](dynamic-resources.md)
- [resource-templates.md](resource-templates.md)
- [02-primitives/resources.md](../02-primitives/resources.md)
- [08-reliability-resilience/caching.md](../08-reliability-resilience/caching.md)