# Resource Testing

## What is it?

**Resource testing** verifies a server's resource surface: static resources,
dynamic (computed-on-read) resources, URI templates, and the content they return
([05-resource-engineering/README.md](../05-resource-engineering/README.md)).

## Why does MCP need it?

Resources are how an agent *sees* data — but unlike tools, a resource's URI is a
contract the client matches against templates. A template that advertises
`docs://{path}` but fails on a valid substitution, or a resource whose read
returns the wrong shape, silently poisons the agent's context. Testing pins the
URI contract and the content.

## How to test — what to cover

1. **Listing**: `resources/list` returns the static resources with their URIs
   and (where present) descriptions.
2. **Templates**: `resources/templates/list` returns the templates; each
   template's URI pattern is correct
   ([05-resource-engineering/resource-templates.md](../05-resource-engineering/resource-templates.md)).
3. **Reading a static resource**: `read_resource(uri)` returns expected content.
4. **Template expansion**: read a URI matching a template (e.g., `docs://guide`)
   and verify the content is computed correctly
   ([05-resource-engineering/dynamic-resources.md](../05-resource-engineering/dynamic-resources.md)).
5. **Unknown URIs**: a URI matching no resource or template → a clean error, not
   a crash.
6. **Content shape**: text vs. blob content, and correct `mimeType`.

## Example

```python
import pytest
from fastmcp import Client

@pytest.mark.asyncio
async def test_resources():
    async with Client("docs_server.py") as client:
        uris = [r.uri for r in await client.list_resources()]
        assert "info://config" in uris

        templates = [t.uriTemplate for t in await client.list_resource_templates()]
        assert "docs://{path}" in templates

        contents = await client.read_resource("docs://guide")
        assert contents[0].text.startswith("# Guide")

        with pytest.raises(Exception):
            await client.read_resource("docs://does-not-exist")
```

## MCP-specific behavior

- `read_resource` returns a list of content items (a resource can have multiple
  parts) — assert on the whole list when it matters.
- Resource subscriptions are part of the spec but rarely implemented
  ([05-resource-engineering/subscriptions.md](../05-resource-engineering/subscriptions.md));
  test them only if your server or its SDK supports them — don't assume.

## Industry-standard pattern

**URI-contract tests**: treat the URI scheme + template as a public API. Any
change to URI patterns is a breaking change for clients — a test that pins them
catches accidental renames.

## Common mistakes

- Testing that reading *works* but not that the *URI set* is stable.
- Forgetting unknown-URI errors — clients will type mistakes.
- Testing template expansion only with the exact example from the docs.

## Related

- [05-resource-engineering/resource-templates.md](../05-resource-engineering/resource-templates.md)
- [05-resource-engineering/dynamic-resources.md](../05-resource-engineering/dynamic-resources.md)
- Example: [05-resource-engineering/examples/test_docs.py](../05-resource-engineering/examples/test_docs.py)
