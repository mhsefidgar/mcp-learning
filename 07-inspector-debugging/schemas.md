# Inspecting Schemas

## What is it?

The **schemas** the Inspector shows are the `inputSchema` values from `tools/list` —
the exact JSON Schema the model and client see. Inspecting them is how you verify the
SDK generated what you intended
([04-tool-engineering/schemas.md](../04-tool-engineering/schemas.md)).

## Why it matters

SDK generation can surprise you: FastMCP derives schemas from Python type hints,
the TS SDK from Zod, Java from records/POJOs — and each has quirks (e.g. `dict`
becoming free-form `object`, `Optional` fields becoming nullable, `Literal` becoming
enums). What you *think* the schema is may differ from what's on the wire.

## How to use it

1. In the Tools panel, click a tool to expand its schema.
2. Check the five things that matter:
   - **types** match intent (`integer` not `string`)
   - **required** marks the right fields
   - **constraints** exist (`minimum`, `maximum`, `maxLength`)
   - **descriptions** are present on fields
   - **no surprise fields** (SDK-injected metadata)
3. Cross-check with `tools/list` output if you need the raw JSON.

## Typical findings

| Observation | Fix |
|-------------|-----|
| `required` missing | the parameter had a default or was typed `Optional` |
| `type: "object"` with no properties | the parameter was typed `dict` — give it a concrete model |
| No descriptions | add them to the type hints / Zod schemas / records |
| Constraints missing | add `ge`/`le`/`max_length` (pydantic), `.min()`/`.max()` (Zod), annotations (Java) |

## Related

- [tools.md](tools.md)
- [04-tool-engineering/schemas.md](../04-tool-engineering/schemas.md)
- [15-testing/schema-testing.md](../15-testing/schema-testing.md)