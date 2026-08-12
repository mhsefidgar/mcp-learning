# Resources

## What is it?

A **resource** is a piece of **data** the server exposes to the client, addressed by a
**URI**. Examples: `file:///etc/config.json`, `db://users/42`,
`weather://current/tokyo`, `git://repo/main/README.md`. Resources come in two flavors:

- **Static resources** — a fixed URI with a fixed value (`config://app/settings`).
- **Resource templates** — a URI *pattern* with parameters that resolves to many
  resources (`db://users/{id}`, `weather://current/{city}`).

## Why does MCP need it?

Resources are the **context** primitive: they let the model *read* data without a tool
call — no arguments to invent, no side effects to worry about. Tools answer "what can I
do?"; resources answer "what can I see?". For an agent, resources are the difference
between hallucinating a config value and actually reading it.

## How does it work?

1. **Discovery**: the client calls `resources/list` (static resources) and
   `resources/templates/list` (patterns).
2. **Selection**: the model/client picks a URI; for templates it substitutes the
   parameters (`db://users/42`).
3. **Reading**: the client calls `resources/read` with the URI.
4. **Resolution**: the server matches the URI (against static resources first, then
   templates), reads/generates the content, and returns it as content blocks
   (`text`, `image`, `resource` — a reference to another resource, e.g. a binary file).

```
Client                        Server
  │ resources/list              │  → [ {uri, name, mimeType, description} ]
  │ resources/templates/list    │  → [ {uriTemplate: "db://users/{id}", ...} ]
  │ resources/read {uri}        │
  ├────────────────────────────►│  match uri → static? template? → generate content
  │ ◄───────────────────────────┤  {contents: [ {uri, mimeType, text|blob} ]}
```

## Mental model

Resources are **files in a virtual filesystem**. The URI is the path; the template is a
glob pattern; `resources/read` is `cat`. The server is the filesystem — it decides what
exists and what each path contains, and it can generate content *on demand* (dynamic
resources) rather than storing it.

## MCP-specific behavior

- **URIs are the contract.** They must be valid URIs; templates use RFC 6570 URI
  template syntax (`{param}`). See [05-resource-engineering/resource-templates.md](../05-resource-engineering/resource-templates.md).
- **`resources/read` returns content blocks**, like tool results. The `resource`
  block type can reference a URI for binary/large content.
- **Subscriptions**: if the server declares `resources.subscribe`, clients may call
  `resources/subscribe` to get `notifications/resources/updated` on change
  ([05-resource-engineering/subscriptions.md](../05-resource-engineering/subscriptions.md)).
- **`listChanged`**: if declared, the server sends `notifications/resources/list_changed`
  when the catalog changes.
- **Resources are read-only by protocol design.** There is no `resources/write`. If you
  need to mutate data, that's a tool.
- **Templates are resolved server-side**: the client sends the concrete URI; the server
  matches it to a template and fills parameters.
- **Large resources** need explicit handling — pagination or chunked reads
  ([05-resource-engineering/large-resources.md](../05-resource-engineering/large-resources.md)).

## Example

FastMCP: static resource + template + dynamic generation:

```python
from fastmcp import FastMCP

mcp = FastMCP("weather")

@mcp.resource("weather://current/summary")
def weather_summary() -> str:
    """A static-ish resource: the overall weather summary."""
    return "Sunny in most regions, rain expected in the north."

@mcp.resource("weather://current/{city}")
def weather_for_city(city: str) -> str:
    """Dynamic resource: generated on demand from the URI parameter."""
    return f"Weather in {city}: 22°C, partly cloudy."
```

TypeScript SDK:

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

const server = new McpServer({ name: "weather", version: "1.0.0" });

server.registerResource(
  "weather://current/summary",
  "Weather summary",
  async (uri) => ({ contents: [{ uri, text: "Sunny in most regions." }] })
);

server.registerResourceTemplate(
  "weather://current/{city}",
  "Current weather for a city",
  async (uri, { city }) => ({ contents: [{ uri, text: `Weather in ${city}: 22°C.` }] })
);
```

Java SDK:

```java
var server = McpServer.sync(serverInfo)
    .resources(
        new McpSchema.Resource("weather://current/summary", "Weather summary", "text/plain", null),
        new McpSchema.ResourceTemplate("weather://current/{city}", "Current weather for a city", "text/plain", null))
    .resourceReader((request) -> new McpSchema.ReadResourceResult(
        List.of(new McpSchema.TextResourceContents(request.uri(), "text/plain",
            "Weather in " + request.uri().substring(request.uri().lastIndexOf('/') + 1) + ": 22°C."))))
    .build();
```

## Industry-standard pattern

Resources are the MCP version of **content-addressed / URI-addressed data** seen in
REST (`GET /users/{id}`), filesystems, and object stores. The template mechanism is
like **route parameters in a web framework**. The novel part: the *client is an LLM*
that reads the URI catalog and decides what to fetch — so descriptions and mime types
matter more than they do for human-facing APIs.

## Common mistakes

- **Putting side effects in a resource reader.** Reading a resource must be safe to
  repeat and must not mutate state.
- **Non-URI "URIs"** — `"users/42"` is not a valid URI; use a scheme (`db://users/42`).
- **Templates that don't match their URIs** — `weather://current/{city}` must actually
  match `weather://current/tokyo`; test the matching
  ([05-resource-engineering/resource-templates.md](../05-resource-engineering/resource-templates.md)).
- **Returning data in the wrong shape** — `resources/read` returns `contents`, a list
  of content blocks, not a bare string.
- **Ignoring mimeType** — clients use it to decide how to render/parse the content.

## Testing

- **Discovery tests**: `resources/list` and `resources/templates/list` return the
  expected catalog ([15-testing/resource-testing.md](../15-testing/resource-testing.md)).
- **Resolution tests**: every template, when substituted, resolves via `resources/read`;
  unknown URIs fail cleanly.
- **Idempotency tests**: reading the same resource twice yields the same result (for
  static ones).
- **Subscription tests**: subscribe, mutate the underlying data, assert the
  `resources/updated` notification fires ([05-resource-engineering/subscriptions.md](../05-resource-engineering/subscriptions.md)).

## Debugging

- In Inspector, list resources and read them with hand-typed URIs — this isolates
  matching bugs from client bugs ([07-inspector-debugging/resources.md](../07-inspector-debugging/resources.md)).
- A `resources/read` failure is usually one of: URI doesn't match any template,
  template handler raised, or the URI isn't in `resources/list`.
- Check mimeType/encoding mismatches when text comes back garbled.

## Security considerations

- **Resources can expose sensitive data.** A `file://` resource that reads arbitrary
  paths is a path-traversal vulnerability waiting to happen — validate and sandbox
  ([14-security/authorization.md](../14-security/authorization.md)).
- **Resources are a read channel for exfiltration.** Authorize *which* resources a
  given client may read, not just "resources: yes".
- **Dynamic resources run code on read** — a template handler is code execution
  triggered by a URI; treat it like a tool for security purposes.

## Related concepts

- [05-resource-engineering/README.md](../05-resource-engineering/README.md) — everything
  about engineering resources
- [tools.md](tools.md) — actions vs. data
- [03-routing-dispatch/03-resource-routing.md](../03-routing-dispatch/03-resource-routing.md)
- [15-testing/resource-testing.md](../15-testing/resource-testing.md)