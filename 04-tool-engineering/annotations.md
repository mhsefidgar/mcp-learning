# Annotations

## What is it?

**Annotations** are structured metadata attached to a tool's definition that tells
clients/models about the tool's *nature* without reading its implementation:

| Annotation | Meaning |
|------------|---------|
| `title` | Human-readable display name |
| `readOnlyHint` | true = the tool never mutates state |
| `destructiveHint` | true = the tool can destroy data (delete, overwrite) |
| `idempotentHint` | true = calling it twice has the same effect as once |
| `openWorldHint` | true = the tool may interact with the outside world (network, files beyond its sandbox) |

## Why does MCP need it?

Models and clients must make **risk decisions** about tools they've never seen:
"should I confirm before calling this?" "can I retry this safely?" "is this just a
read?" Annotations are the machine-readable answer. A `destructiveHint: true` tool can
trigger a confirmation UI in the client; an `idempotentHint: true` tool is safe to
retry. Annotations turn tool *judgment* from guesswork into a contract.

## How does it work?

1. You declare annotations when registering the tool.
2. They travel in the tool definition returned by `tools/list`.
3. Clients/models read them at decision time — to gate retries, prompt for
   confirmation, or filter the catalog.

**Hints are advisory, not enforced.** The protocol does not make a `readOnlyHint`
tool read-only — that's your implementation's responsibility. Annotations describe
reality; they don't create it.

## Mental model

Annotations are **nutrition labels** on tool packaging: "this product has side
effects (destructive), is safe to re-take (idempotent), doesn't leave the house
(read-only)". Consumers decide how to use the product based on the label — but the
label must be *true*, or consumers get hurt.

## MCP-specific behavior

- **Annotations are part of the MCP spec** (added 2025-03-26): `ToolAnnotations` in
  the tool definition.
- **They are hints** — no client or server enforces them; enforcement is yours
  (see security below).
- **SDK support varies**: FastMCP exposes annotations on tools (via the `Tool` model
  and `@mcp.tool` metadata); the TS/Java SDKs expose them on their tool
  specifications where supported. Check your SDK version before relying on them.
- **Resources also have annotations** (in the newer spec, e.g. `openWorldHint` for
  resources that reference external data).

## Example

FastMCP — set annotations on the tool:

```python
from fastmcp import FastMCP

mcp = FastMCP("fs")

@mcp.tool(annotations={
    "readOnlyHint": True,
    "openWorldHint": False,
})
def list_directory(path: str) -> list[str]:
    """List entries in a directory. Read-only, sandboxed to /data."""
    return os.listdir(os.path.join("/data", path))
```

TypeScript SDK:

```typescript
server.registerTool(
  "delete_file",
  {
    description: "Permanently delete a file.",
    annotations: { destructiveHint: true, idempotentHint: true },
    inputSchema: { path: z.string() },
  },
  async ({ path }) => { /* ... */ }
);
```

## Industry-standard pattern

Declarative risk metadata is standard in platform APIs: **cloud IAM policies,
OpenAPI `deprecated`/security markers, gRPC options, HTML `rel` attributes**. The
principle: make *judgment* data machine-readable so consumers can automate safe
behavior instead of guessing.

## Common mistakes

- **Wrong hints** — marking a deleting tool `readOnlyHint: true` is a safety lie;
  marking a non-idempotent tool `idempotentHint: true` leads clients to retry
  duplicates.
- **Relying on hints for safety** — a client that skips confirmation because of
  `readOnlyHint` on a buggy tool will be surprised. Enforcement, not hints, protects
  data ([14-security/destructive-operations.md](../14-security/destructive-operations.md)).
- **Omitting hints entirely** — clients default to caution (or retry-anything);
  either way, behavior degrades.
- **Treating annotations as protocol-enforced** — they're metadata, not behavior.

## Testing

- **Metadata tests**: the published tool definition carries the annotations you set.
- **Honesty tests**: a tool marked `readOnlyHint: true` doesn't mutate state (test
  the side effect).
- **Client-behavior tests**: a client that honors hints prompts before
  `destructiveHint` tools.

## Debugging

- In Inspector, inspect the tool definition — annotations are visible in the raw
  `tools/list` response. Missing annotations = you didn't set them (or your SDK
  version doesn't carry them).

## Security considerations

- **Destructive tools** should be annotated `destructiveHint: true` *and* protected
  by authorization + confirmation ([14-security/destructive-operations.md](../14-security/destructive-operations.md)).
- **Do not trust client-side enforcement of hints** — a malicious client ignores
  them. Hints inform, enforcement protects.
- `openWorldHint: false` is a *claim*, not a sandbox — implement actual sandboxing
  if the claim matters ([14-security/README.md](../14-security/README.md)).

## Related concepts

- [schemas.md](schemas.md)
- [idempotency.md](idempotency.md)
- [14-security/destructive-operations.md](../14-security/destructive-operations.md)
- [02-primitives/tools.md](../02-primitives/tools.md)