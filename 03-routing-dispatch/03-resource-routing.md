# 03 — Resource Routing

## What is it?

**Resource routing** is the mapping from a **URI** (received in `resources/read`) to
the data behind it. Because resources are addressed by URIs — not flat names — routing
has two steps: *match* the URI against static resources or templates, then *resolve*
it to content.

```
resources/read {uri: "db://users/42"}
        │
        ▼
  static resources?  db://users/42  ✗ (not a static URI)
        │
        ▼
  templates?  db://users/{id}  ✓  → extract id=42 → handler → content
```

## Why does MCP need it?

URIs are open-ended: `file:///etc/hosts`, `db://users/42`, `weather://current/tokyo`.
The server must decide, for *any* URI a client sends, whether it exists and how to
produce its content. That requires a deterministic matching strategy (static first,
then templates), plus validation — an unvalidated `file://` template is a path
traversal waiting to happen.

## How does it work?

1. **List**: `resources/list` returns concrete URIs; `resources/templates/list` returns
   URI patterns with parameter names.
2. **Match**: `resources/read` tries the exact URI against static resources first;
   failing that, it tries each template and extracts parameters (`{id}` → `42`).
3. **Resolve**: the matched handler runs with the extracted parameters (or none for
   static) and returns content blocks.
4. **Miss**: no match → an error routed per [10-error-routing.md](10-error-routing.md).

### Advanced patterns

- **Dynamic resolution** — the handler doesn't store content; it *generates* it on
  read (database lookups, computed values). This is the common production case
  ([05-resource-engineering/dynamic-resources.md](../05-resource-engineering/dynamic-resources.md)).
- **Namespaces** — URI schemes are natural namespaces: `db://`, `file://`, `config://`.
  A mounted sub-server can keep its own scheme namespace
  ([06-provider-routing.md](06-provider-routing.md)).
- **Versioning** — `config://app/v1/settings` or a `version` segment inside the URI
  ([05-resource-engineering/resource-versioning.md](../05-resource-engineering/resource-versioning.md)).

## Mental model

Resource routing is **URL routing in a web framework with a filesystem flavor**: exact
routes first (`/about`), then parameterized routes (`/users/:id`). The URI is the
path; the template is the route pattern; the handler is the controller. `resources/read`
is `GET`.

## MCP-specific behavior

- **Matching order is significant**: exact static match before template match (spec
  behavior — SDKs implement it; a template that shadows a static URI is a bug).
- **Templates use RFC 6570 syntax** (`{param}`, `{?optional}`) —
  [05-resource-engineering/resource-templates.md](../05-resource-engineering/resource-templates.md).
- **The resolved URI should be returned in the content** — content blocks carry the
  concrete `uri` so clients can correlate.
- **Subscriptions** route through the URI too: `resources/subscribe {uri}` then
  `notifications/resources/updated {uri}` on change
  ([05-resource-engineering/subscriptions.md](../05-resource-engineering/subscriptions.md)).
- **Templates may overlap** — the most specific match wins where SDKs define it;
  check your SDK's precedence rules rather than assuming.

## Example

FastMCP routes by URI automatically; order = registration order:

```python
from fastmcp import FastMCP

mcp = FastMCP("shop")

@mcp.resource("products://featured")
def featured() -> str:
    """The featured product list (static-ish)."""
    return "['laptop', 'headphones']"

@mcp.resource("products://{product_id}")
def product(product_id: str) -> str:
    """A single product by id (dynamic, resolved on read)."""
    return f"Product {product_id}: loaded from the catalog on demand."
```

`resources/read products://featured` → static handler. `resources/read
products://42` → template handler with `product_id="42"`.

TypeScript SDK:

```typescript
server.registerResource("products://featured", "Featured products",
  async (uri) => ({ contents: [{ uri, text: "['laptop', 'headphones']" }] }));
server.registerResourceTemplate("products://{product_id}", "Product by id",
  async (uri, { product_id }) => ({ contents: [{ uri, text: `Product ${product_id}` }] }));
```

## Industry-standard pattern

Exact-then-parameterized matching is the routing model of Express, FastAPI, Rails,
and every HTTP framework. The same correctness concerns apply: route order matters,
parameter extraction must be validated, and unknown paths return a clean 404-equivalent
(resource-not-found error).

## Common mistakes

- **Template matching bugs** — `{id}` swallowing slashes, or templates that never
  match because of an encoding mismatch. Test each template with representative URIs.
- **Missing validation of extracted parameters** — `file://{path}` with `path =
  ../../etc/passwd` (see security below).
- **Shadowing** — a template registered *before* a static URI that would have matched.
- **Returning the template string instead of the concrete URI** in content blocks.

## Testing

- **Match matrix**: for each static URI and each template, assert
  match/parameters/miss behavior with a table of test URIs
  ([15-testing/resource-testing.md](../15-testing/resource-testing.md)).
- **Precedence**: a URI matching both a static resource and a template resolves to the
  static one.
- **Invalid URIs**: non-URI strings, malformed templates, encoding edge cases.
- **Security cases**: traversal payloads in template parameters.

## Debugging

- In Inspector, list resources and templates, then `read` URIs by hand — match
  failures are instantly visible ([07-inspector-debugging/resources.md](../07-inspector-debugging/resources.md)).
- A "resource not found" that *should* exist usually means the URI doesn't match any
  template — compare character by character (scheme, slashes, case).

## Security considerations

- **Validate every URI and parameter.** `file://`, `http://`, and similar schemes are
  the classic attack surface: sandbox the base path, reject `..`, reject scheme
  mismatches ([14-security/authorization.md](../14-security/authorization.md)).
- **Resources are read channels** — restrict which URIs an authenticated client may
  read; don't rely on "it's just a read" as a security argument.
- **Dynamic handlers run code on read** — the URI is user input to a function.

## Related concepts

- [01-request-dispatch.md](01-request-dispatch.md)
- [05-capability-routing.md](05-capability-routing.md)
- [10-error-routing.md](10-error-routing.md)
- [05-resource-engineering/README.md](../05-resource-engineering/README.md)
- [02-primitives/resources.md](../02-primitives/resources.md)