# Inspecting Resources

## What is it?

The Inspector's **resources view** shows `resources/list` (static resources),
`resources/templates/list` (URI patterns), and lets you call `resources/read` with a
hand-typed URI.

## Why it matters

Resource bugs are almost always **URI matching** bugs
([03-routing-dispatch/03-resource-routing.md](../03-routing-dispatch/03-resource-routing.md)):
a template that never matches, a typo in the scheme, a static resource shadowed by a
template. The Inspector makes matching visible: list the templates, then read URIs by
hand and watch which template (if any) matches.

## How to use it

1. Read the Resources panel: note every URI and every `uriTemplate`.
2. Try reading:
   - each listed static URI → should succeed
   - each template with concrete parameters → should succeed
   - a URI that should *not* exist → should fail cleanly
   - a traversal URI (`file:///../..`) → should be rejected
3. Compare the response `contents` — the returned `uri` should be the concrete URI,
   not the template.

## Typical findings

| Observation | Meaning |
|-------------|---------|
| Static URI fails | handler missing/raises; or a template shadows it |
| Template never matches | encoding/slash/case mismatch — compare char by char |
| Traversal read succeeds | **security bug** — validate parameters ([05-resource-engineering/resource-templates.md](../05-resource-engineering/resource-templates.md)) |
| Content's `uri` is the template string | the handler returned the pattern, not the concrete URI |

## Related

- [05-resource-engineering/README.md](../05-resource-engineering/README.md)
- [03-routing-dispatch/03-resource-routing.md](../03-routing-dispatch/03-resource-routing.md)
- [15-testing/resource-testing.md](../15-testing/resource-testing.md)