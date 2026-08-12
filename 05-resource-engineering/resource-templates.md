# Resource Templates

## What is it?

A **resource template** is a URI *pattern* that resolves to many resources. It uses
RFC 6570 URI template syntax: `db://users/{id}`, `docs://{project}/{file}`,
`weather://current/{city}`. The template is registered with parameter names; at read
time, a concrete URI is matched against it and the parameters are extracted.

## Why does MCP need it?

You cannot list every resource that will ever exist — a database has millions of
rows, a filesystem millions of files. Templates make the *space* of resources
discoverable without enumerating it: the client learns "there are users at
`db://users/{id}`" and reads `db://users/42` directly. Templates are how resource
catalogs stay finite while data stays infinite.

## How does it work?

1. **Register** a template: `uriTemplate` (RFC 6570) + description + parameter names.
2. **List**: it appears in `resources/templates/list`.
3. **Match**: `resources/read` with a concrete URI matches the template and extracts
   parameters (`db://users/42` → `{id: "42"}`).
4. **Resolve**: the handler runs with the parameters and returns content.

Matching rules to know:

- **Exact/static resources match first**, before templates
  ([03-routing-dispatch/03-resource-routing.md](../03-routing-dispatch/03-resource-routing.md)).
- **Parameters are strings** extracted from the URI — validate/convert them
  (`"42"` → 42).
- **Multiple templates** are tried in registration order; the first match wins (per
  your SDK's precedence rules).

## Mental model

A template is a **route pattern in a web framework** (`/users/:id`) exposed as a
filesystem glob. The client discovers the *shape* (`{id}`), then fills in values to
form concrete paths. The server is the router that turns paths into handlers.

## MCP-specific behavior

- **RFC 6570 syntax is protocol-defined**: `{var}`, `{?optional}`,
  `{+reserved}`. Most SDKs support the simple `{name}` case; check your SDK for
  advanced operators.
- **`resources/templates/list` is a protocol method** — templates are first-class,
  not a convention.
- **Concrete URIs are what the client sends** — the client never sends template
  syntax in `resources/read`.

## Example

```python
from fastmcp import FastMCP

mcp = FastMCP("docs")

@mcp.resource("docs://{project}/{file}")
def doc_file(project: str, file: str) -> str:
    """Read a doc file from a project's docs directory."""
    # Validate BEFORE touching the filesystem — see security below.
    safe_project = _validate(project)
    safe_file = _validate(file)
    return open(f"/docs/{safe_project}/{safe_file}").read()
```

TypeScript:

```typescript
server.registerResourceTemplate(
  "docs://{project}/{file}",
  "Read a doc file",
  async (uri, { project, file }) => ({
    contents: [{ uri, text: await readDoc(project, file) }],
  })
);
```

## Industry-standard pattern

Parameterized URL routing is the backbone of every web framework. The additional
lesson from MCP: **the template is a discoverable contract** — the description should
explain the parameter semantics ("file paths are relative to /docs"), because the
model will *invent* URIs from the template.

## Common mistakes

- **Path traversal**: a `{path}` parameter containing `../` escapes the sandbox.
  Validate and normalize *every* parameter
  ([14-security/authorization.md](../14-security/authorization.md)).
- **Templates that never match** — encoding mismatches, extra slashes, case
  sensitivity. Test each template with representative URIs.
- **Parameter type confusion** — extracting `"42"` and comparing it to the int `42`.
- **Overlapping templates** with unclear precedence.
- **Forgetting that static resources win** over templates.

## Testing

- **Match matrix tests**: for each template, a table of URIs asserting match/params/
  miss ([15-testing/resource-testing.md](../15-testing/resource-testing.md)).
- **Security tests**: traversal payloads (`../`, absolute paths, encoded slashes)
  are rejected.
- **Precedence tests**: static URI + template overlap → static wins.
- **Round-trip tests**: every listed template resolves at least one concrete URI.

## Debugging

- "Resource not found" for a URI that should match → compare char-by-char: scheme,
  slashes, case, encoded characters.
- In Inspector, list templates and read concrete URIs by hand — matching is visible
  instantly ([07-inspector-debugging/resources.md](../07-inspector-debugging/resources.md)).

## Security considerations

- **Templates are the classic injection surface**: `file://{path}`, `db://{id}`,
  `http://{url}` all execute with server privileges. Validate parameters, sandbox
  base paths, reject `..` and scheme smuggling
  ([14-security/README.md](../14-security/README.md)).
- **Don't leak the filesystem layout** through error messages ("no file at /docs/…").

## Related concepts

- [dynamic-resources.md](dynamic-resources.md)
- [static-resources.md](static-resources.md)
- [03-routing-dispatch/03-resource-routing.md](../03-routing-dispatch/03-resource-routing.md)
- [02-primitives/resources.md](../02-primitives/resources.md)