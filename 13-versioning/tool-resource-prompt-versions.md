# Tool / Resource / Prompt Versions

## What is it?

Versioning the *components you expose* — the application-layer contract — as
distinct from protocol or SDK versions. Three mechanisms:

1. **Name-embedded versions** (portable): `orders_search_v1`, `orders_search_v2`.
2. **Framework versions** (FastMCP 3.x): components carry a `version`; callers
   request a version at call time; providers merge by version.
3. **URI versions** (resources): `config://app/v1/settings`.

## Why it matters

Components are long-lived contracts: clients cache `tools/list`, models learn tool
behavior, and workflows depend on schemas. Changing a tool's schema/behavior
*without* versioning silently breaks everyone; versioning makes change explicit and
safe ([03-routing-dispatch/09-version-aware-routing.md](../03-routing-dispatch/09-version-aware-routing.md)).

## How it works

**Name-embedded (works with any client/SDK):**

```python
@mcp.tool
def orders_search_v1(query: str) -> list[dict]:
    """v1: search by customer name only."""
    ...

@mcp.tool
def orders_search_v2(query: str, include_cancelled: bool = False) -> list[dict]:
    """v2: search by name or id, with cancelled toggle."""
    ...
```

**FastMCP component versions (call-time selection):**

```python
@mcp.tool(version="1.0")
def analyze(data: str) -> str:
    """Original analysis."""
    ...

@mcp.tool(version="2.0")
def analyze(data: str) -> str:
    """Enhanced analysis."""
    ...

# callers: await client.call_tool("analyze", {...}, version="2.0")
# unversioned calls resolve to the highest/default version
```

**Resources by URI:** `config://app/v1/settings` vs `config://app/v2/settings`
([05-resource-engineering/resource-versioning.md](../05-resource-engineering/resource-versioning.md)).

## The rules

1. **v1 is frozen** — behavior, schema, and errors never change after release
   (bug fixes may be backported *without observable change*).
2. **v2 is additive-first** — new fields optional, old fields unchanged where
   possible.
3. **Deprecate, don't delete** — a version leaves via
   [deprecation.md](deprecation.md)'s window, not overnight.
4. **Document the version** in the description ("v2 adds include_cancelled") — the
   model needs to know.
5. **Catalog carries both** — clients discover all versions via `tools/list`.

## Mental model

Component versioning is **menu editions**: the menu (catalog) lists `v1` and `v2`
dishes; old dishes stay available (frozen recipes) until they're retired with
notice; the description tells diners what changed. Versioned tools are the same —
explicit choices, not silent substitutions.

## Common mistakes

- **Mutating v1** — the classic silent break.
- **Versioning names but not behavior** — v2 with v1's bugs.
- **No deprecation window** — versions removed overnight
  ([deprecation.md](deprecation.md)).
- **Forgetting `listChanged`** — new versions must appear in the catalog with a
  change notification ([06-agent-interaction/notifications.md](../06-agent-interaction/notifications.md)).

## Testing

- **Per-version tests**: each version's schema and behavior pinned
  ([15-testing/compatibility-testing.md](../15-testing/compatibility-testing.md)).
- **Selection tests**: explicit version requests resolve exactly; invalid versions
  fail cleanly.
- **Frozen-v1 tests**: re-running v1 tests after v2 ships still passes.

## Security considerations

- **Old versions are old attack surface** — track exposure, and deprecated versions
  should lose new permissions
  ([03-routing-dispatch/09-version-aware-routing.md](../03-routing-dispatch/09-version-aware-routing.md)).

## Related

- [03-routing-dispatch/09-version-aware-routing.md](../03-routing-dispatch/09-version-aware-routing.md)
- [deprecation.md](deprecation.md)
- [05-resource-engineering/resource-versioning.md](../05-resource-engineering/resource-versioning.md)
- [15-testing/compatibility-testing.md](../15-testing/compatibility-testing.md)