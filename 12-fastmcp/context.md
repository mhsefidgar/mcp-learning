# FastMCP Context

## What is it?

`Context` gives your tool/resource/prompt functions access to the MCP session's
capabilities: logging to the client, progress reporting, reading resources and
prompts, eliciting user input, and request-scoped state
([01-fundamentals/04-requests-responses-notifications.md](../01-fundamentals/04-requests-responses-notifications.md)).

## Why it exists

Handlers need more than their arguments: they need to *report progress*, *log to
the client*, *read a resource*, or *ask the user something*. Without `Context`,
you'd have to thread session handles through every signature. FastMCP injects it.

## How to access it (verified API — two ways)

**Preferred — `CurrentContext()` dependency (2.14+):**

```python
from fastmcp import FastMCP
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context

mcp = FastMCP("demo")

@mcp.tool
async def process_file(file_uri: str, ctx: Context = CurrentContext()) -> str:
    """Process a file, logging progress via context."""
    await ctx.info(f"Processing {file_uri}")
    await ctx.report_progress(1, 3)
    return "done"
```

**Legacy — type-hint injection:** a parameter typed `Context` is injected
automatically:

```python
from fastmcp import FastMCP, Context

@mcp.tool
async def process_file(file_uri: str, ctx: Context) -> str:
    ...
```

## What you can do with it

| Capability | Method |
|------------|--------|
| Logging to the client | `await ctx.debug/info/warning/error(...)` |
| Progress | `await ctx.report_progress(progress, total)` |
| Read resources | `await ctx.read_resource(uri)`; `await ctx.list_resources()` |
| Prompts | `await ctx.get_prompt(name, args)`; `await ctx.list_prompts()` |
| Elicitation | `await ctx.elicit(question, response_type=...)` ([06-agent-interaction/elicitation.md](../06-agent-interaction/elicitation.md)) |
| Request state (middleware ↔ handler) | `await ctx.set_state(k, v)` / `await ctx.get_state(k)` / `delete_state(k)` |

**Rules:** context methods are async; dependency parameters are excluded from the
schema (clients never see them); each request gets a fresh context (state does not
survive to the next call — use session state for persistence); context is only
available during a request.

## Mental model

`Context` is the **tool's desk phone**: the arguments are the work order, and the
phone connects you to the rest of the building — the intercom (logging), the
elevator display (progress), the library (resources), and the front desk (user
input). You don't carry the whole building with you; you just know where the phone
is.

## Common mistakes

- **Using context outside a request** — raises; it's request-scoped.
- **Expecting `set_state` to persist across calls** — it doesn't; that's session
  state.
- **Sync handlers with `await ctx...`** — context methods are async; make the
  handler async.
- **Schema pollution** — context params are excluded automatically, but keep other
  injected dependencies explicit.

## Testing

- **Logging tests**: `ctx.info(...)` produces a `notifications/message`
  (via a client with a log handler).
- **Progress tests**: `report_progress` emits the right notifications
  ([04-tool-engineering/progress.md](../04-tool-engineering/progress.md)).
- **State tests**: middleware-set state is visible to the handler.

## Related

- [middleware.md](middleware.md)
- [04-tool-engineering/progress.md](../04-tool-engineering/progress.md)
- [06-agent-interaction/elicitation.md](../06-agent-interaction/elicitation.md)
- [09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md)