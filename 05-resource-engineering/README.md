# 05 — Resource Engineering

**What this section teaches.** How to engineer resources that serve data safely and
scalably: static vs. dynamic resources, URI templates, subscriptions, pagination,
large resources, and resource versioning. After this section you can design a
resource layer that behaves like a small, well-governed filesystem.

**Prerequisites.** [01-fundamentals](../01-fundamentals/README.md),
[02-primitives/resources.md](../02-primitives/resources.md),
[03-routing-dispatch/03-resource-routing.md](../03-routing-dispatch/03-resource-routing.md).

**Recommended reading order:**

1. [static-resources.md](static-resources.md) — the simple case
2. [dynamic-resources.md](dynamic-resources.md) — content generated on read
3. [resource-templates.md](resource-templates.md) — URI patterns (the workhorse)
4. [subscriptions.md](subscriptions.md) — change notifications
5. [pagination.md](pagination.md) · [large-resources.md](large-resources.md) — scale
6. [resource-versioning.md](resource-versioning.md) — data that changes over time

**Protocol vs. engineering in this section:**

| Topic | Protocol feature? | Reality |
|-------|-------------------|---------|
| URI templates | ✅ protocol (`resources/templates/list`) | see [resource-templates.md](resource-templates.md) |
| Subscriptions | ✅ protocol (`resources/subscribe`, `notifications/resources/updated`) | see [subscriptions.md](subscriptions.md) |
| Static/dynamic resources | ✅ protocol (both are just resources) | see [static-resources.md](static-resources.md) |
| Pagination of lists | ✅ protocol (cursor) | see [pagination.md](pagination.md) |
| Large-resource chunking | ❌ your design (protocol has `resource` content refs) | see [large-resources.md](large-resources.md) |
| Resource versioning | ❌ your convention (URIs or metadata) | see [resource-versioning.md](resource-versioning.md) |

**Relevant examples:** `examples/` — a filesystem-ish resource server with
templates, subscriptions, and versioning.

**Exercises.**

1. **Build a template** `docs://{project}/{file}` that resolves from a directory.
   *Acceptance:* `resources/templates/list` shows it; reads resolve; unknown files
   fail cleanly; `../` traversal is rejected.
2. **Add a subscription** to a mutable resource. *Acceptance:* after the underlying
   data changes, `notifications/resources/updated` fires with the URI
   ([subscriptions.md](subscriptions.md)).
3. **Version a resource**: serve `config://app/v1/settings` and
   `config://app/v2/settings` with different content. *Acceptance:* reads return the
   right version and the catalog documents both.
4. **Large resource**: expose a multi-megabyte log as a resource with
   paginated/chunked reads. *Acceptance:* the client can page through without the
   server materializing the whole file in memory.

**Common mistakes in this section**

- Side effects in resource reads (resources must be safe to read repeatedly).
- Templates that don't match their own URIs, or `..` path traversal in `file://`
  templates ([resource-templates.md](resource-templates.md)).
- Subscriptions without change detection (see [subscriptions.md](subscriptions.md)).
- Unbounded reads of huge content ([large-resources.md](large-resources.md)).