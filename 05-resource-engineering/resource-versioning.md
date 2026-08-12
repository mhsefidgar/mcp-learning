# Resource Versioning

## What is it?

**Resource versioning** is giving a resource's *content* a version identity, so
clients can read a *specific* version and detect change. Two common approaches:

1. **Version in the URI** — `config://app/v1/settings`, `config://app/v2/settings`
   (immutable addresses).
2. **Version in metadata/content** — the resource returns
   `{"version": 12, ...}` and the client compares versions to detect staleness.

## Why does MCP need it?

Resource content changes, and clients act on what they read:

- **Reproducibility**: "the config that was deployed on Monday" must still be
  readable — URI versions keep history addressable.
- **Staleness detection**: a client that read version 7 shouldn't act on stale data
  when the resource is at version 12.
- **Compatibility**: v1 and v2 content may have different shapes; a client (or model)
  can ask for the shape it understands.

## How does it work?

**URI versioning**: register distinct URIs per version; the catalog shows them all.

```
config://app/v1/settings  →  '{"region": "us-east-1", "theme": "light"}'
config://app/v2/settings  →  '{"region": "us-east-1", "theme": "dark", "locale": "en"}'
```

**Content versioning**: one URI, but the content carries a version and possibly a
history:

```json
{"version": 12, "updated": "2026-08-01T10:00:00Z", "data": {...}}
```

The two combine: the "latest" alias (`config://app/settings`) returns current
content with its version; the versioned URI returns that exact version forever.

## Mental model

URI versioning is **book editions on a shelf** (`v1` and `v2` side by side); content
versioning is a **serial number stamped on each copy**. Editions let you fetch a
specific copy; serial numbers let you tell copies apart. Mature systems use both.

## MCP-specific behavior

- **Nothing protocol-level** — versioning is your URI/content design. The protocol
  has no resource-version fields.
- **Templates version nicely**: `config://app/{version}/settings` is a template that
  serves any version.
- **Version + subscriptions interact**: subscribe to the "latest" URI; when a new
  version ships, the notification fires and the client re-reads the latest
  ([subscriptions.md](subscriptions.md)).

## Example

```python
from fastmcp import FastMCP

mcp = FastMCP("config")

_VERSIONS = {
    "v1": '{"theme": "light", "region": "us-east-1"}',
    "v2": '{"theme": "dark", "region": "us-east-1", "locale": "en"}',
}
LATEST = "v2"

@mcp.resource("config://app/{version}/settings")
def settings_version(version: str) -> str:
    """Settings for a specific version (v1 or v2). Latest alias: config://app/settings."""
    if version not in _VERSIONS:
        raise ResourceError(f"Unknown config version {version!r}")
    return _VERSIONS[version]

@mcp.resource("config://app/settings")
def settings_latest() -> str:
    """Latest settings, with its version embedded."""
    return f'{{"version": "{LATEST}", "data": {_VERSIONS[LATEST]}}}'
```

## Industry-standard pattern

Versioned data is the norm in every serious system: **S3 versioning, config
management (consul/etcd revisions), database row versions, semver'd APIs**. The rules
that matter: old versions are immutable, latest is a first-class alias, and version
metadata travels with the content.

## Common mistakes

- **Mutating old versions** — v1 must never change after release.
- **Version only in the name, not in the content** — clients can't detect stale
  reads.
- **No "latest" story** — clients hard-code versions and drift.
- **Infinite version retention** — clean up old versions (retention policy).

## Testing

- **Immutable-version tests**: reading v1 after v2 ships returns the original v1.
- **Latest tests**: the alias returns the current version with correct metadata.
- **Staleness tests**: content version increments on change; clients detect it.
- **Unknown-version tests**: clean error for `v99`.

## Debugging

- A client acting on stale data → check whether the resource returns its version and
  whether the client compares it.
- "v1 changed!" → someone mutated an old version; make versions immutable in storage.

## Security considerations

- **Old versions are old attack surface** — a v1 with a known flaw should be
  deprecated, not deleted silently (clients break); follow a policy
  ([13-versioning/deprecation.md](../13-versioning/deprecation.md)).
- **Version metadata can leak history** — access control per version where it
  matters.

## Related concepts

- [static-resources.md](static-resources.md) · [dynamic-resources.md](dynamic-resources.md)
- [subscriptions.md](subscriptions.md)
- [13-versioning/deprecation.md](../13-versioning/deprecation.md)
- [03-routing-dispatch/09-version-aware-routing.md](../03-routing-dispatch/09-version-aware-routing.md)