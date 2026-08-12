# Inspecting Tools

## What is it?

The Inspector's **tools view** lists what `tools/list` returns — the catalog the model
actually sees: names, descriptions, and schemas. From here you can also **invoke
tools manually** with hand-typed JSON arguments.

## Why it matters

Two debugging powers:

1. **See what the model sees.** If the catalog looks different from what you
   registered, a transform is renaming/filtering tools
   ([03-routing-dispatch/07-transform-routing.md](../03-routing-dispatch/07-transform-routing.md)),
   or a capability gate is hiding them.
2. **Isolate the failure layer.** Calling the tool directly from Inspector tells you:
   is the bug in the schema (validation fails), the handler (execution fails), or the
   client (the call never arrived)?

## How to use it

1. Connect Inspector to the server.
2. Open the Tools panel — read every name, description, and schema as a *model*
   would.
3. Pick a tool, type arguments as JSON, click **Call Tool**.
4. Read the response: a JSON-RPC error (protocol/validation layer) or a result with
   `isError` (application layer).

## Typical findings

| Observation | Meaning |
|-------------|---------|
| Tool missing from the list | transform/visibility filter, or registered after handshake without `listChanged` |
| Schema too vague | the model will mis-call it — tighten the schema ([04-tool-engineering/schemas.md](../04-tool-engineering/schemas.md)) |
| `-32602` invalid params on a "correct" call | schema and handler disagree — fix one |
| `isError: true` with a message | handler ran and failed semantically — look at the handler, not the protocol |
| Tool callable in Inspector but not in your app | your client sends different arguments, or auth differs |

## Related

- [schemas.md](schemas.md)
- [04-tool-engineering/schemas.md](../04-tool-engineering/schemas.md)
- [04-tool-engineering/errors.md](../04-tool-engineering/errors.md)
- [15-testing/tool-testing.md](../15-testing/tool-testing.md)