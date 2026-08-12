# Prompts

## What is it?

A **prompt** is a reusable **instruction template** the server offers to the client.
Unlike tools (actions) and resources (data), prompts are *guidance*: a named, possibly
parameterized set of messages the client can render into its conversation with the
model. Example: a "summarize bug report" prompt that takes a `bug_id` and produces a
structured instruction for the model.

A prompt is defined by:

- **name** — unique identifier
- **description** — what the prompt is for
- **arguments** — optional parameters (each with a description and optional required flag)
- **messages** — the template body: system/user/assistant messages with
  `{{arguments}}`-style interpolation

## Why does MCP need it?

Prompts encode **expert workflows** as reusable assets: "onboard a new employee",
"triage a security incident", "write a release note". Instead of every client
reinventing these instructions, the server ships them once, and any client can fetch
and render them. Prompts turn the server into a source of *process*, not just data and
actions.

## How does it work?

1. **Discovery**: the client calls `prompts/list`; the server returns the catalog
   (name, description, arguments).
2. **Selection**: the client (or model, via the client) picks a prompt and provides
   argument values.
3. **Retrieval**: the client calls `prompts/get` with `{name, arguments}`.
4. **Rendering**: the server interpolates the arguments into the template and returns
   the message list.
5. **Use**: the client inserts the returned messages into its conversation with the
   model. **The server does not call an LLM** — it only returns text.

```
Client                        Server
  │ prompts/list                │  → [ {name, description, arguments} ]
  │ prompts/get {name, args}    │
  ├────────────────────────────►│  interpolate template
  │ ◄───────────────────────────┤  {messages: [ {role, content} ]}
```

## Mental model

Prompts are **macros / templates** — like a mail-merge document or a code snippet with
placeholders. The server provides the blank form; the client fills in the blanks and
uses the result. The server is the *library of forms*, not the printer.

## MCP-specific behavior

- **Prompts are server-side templates, rendered server-side.** The client receives
  ready-to-use messages.
- **Messages have roles** (`system`, `user`, `assistant`) and content. The
  `system` role is where you put the strongest instructions.
- **Arguments are simple strings** (name + description + required). There is no JSON
  Schema for prompt arguments in the stable spec — keep them simple.
- **`prompts/list` may be paginated** (`cursor`), and `listChanged` enables
  `notifications/prompts/list_changed`.
- **Prompts are not tools**: they don't execute anything. Some SDKs offer a
  "prompts as tools" transform (FastMCP) to expose prompts to tool-only clients — that
  is a framework feature, not a protocol one
  ([12-fastmcp/transforms.md](../12-fastmcp/transforms.md)).

## Example

FastMCP:

```python
from fastmcp import FastMCP

mcp = FastMCP("support")

@mcp.prompt
def summarize_bug_report(bug_id: str) -> str:
    """Create a structured bug summary for an engineer."""
    return (
        "You are a senior support engineer. Summarize the bug report "
        f"#{bug_id} into: (1) symptom, (2) affected component, "
        "(3) steps to reproduce, (4) suggested next action. "
        "Be concise and technical."
    )
```

A prompt with multiple messages (FastMCP returns a string → single user message; for
multi-message prompts, return a list or use the `Prompt` helpers):

```python
from fastmcp import FastMCP
from fastmcp.prompts.base import UserMessage, SystemMessage

mcp = FastMCP("support")

@mcp.prompt
def triage_incident(severity: str) -> list:
    """Triage a support incident by severity."""
    return [
        SystemMessage(content="You are an incident triage specialist."),
        UserMessage(content=f"Triage this {severity} incident: what is the impact, who is affected, what should we do first?"),
    ]
```

TypeScript SDK:

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

const server = new McpServer({ name: "support", version: "1.0.0" });

server.registerPrompt(
  "summarize_bug_report",
  {
    description: "Create a structured bug summary for an engineer.",
    arguments: [{ name: "bug_id", description: "Bug tracker ID", required: true }],
  },
  async ({ bug_id }) => ({
    messages: [{
      role: "user",
      content: { type: "text", text: `Summarize bug #${bug_id} into symptom, cause, fix.` },
    }],
  })
);
```

Java SDK:

```java
var server = McpServer.sync(serverInfo)
    .registerPrompt(
        new McpSchema.Prompt("summarize_bug_report", "Create a structured bug summary.",
            List.of(new McpSchema.PromptArgument("bug_id", "Bug tracker ID", true))),
        (request) -> new McpSchema.GetPromptResult(
            List.of(new McpSchema.PromptMessage(McpSchema.Role.USER,
                new McpSchema.TextContent("Summarize bug #" + request.arguments().get("bug_id") + ".")))))
    .build();
```

## Industry-standard pattern

Prompts are **content templates with parameters**, the same idea as email templates,
Jinja/Handlebars, and Terraform modules. The MCP-specific value is that the *catalog is
discoverable*: a client can list what workflows a server supports and use them without
hard-coding any of them.

## Common mistakes

- **Assuming the server calls an LLM.** It doesn't — prompts return text. If you need
  generation, that's sampling (deprecated) or a direct LLM call from your server
  ([06-agent-interaction/sampling.md](../06-agent-interaction/sampling.md)).
- **Prompts that are just tools in disguise.** If the "prompt" needs to run code, make
  it a tool that returns the result.
- **No descriptions on arguments** — the client can't ask the user for good values.
- **Interpolation bugs** — escaping/formatting arguments; use your SDK's template
  mechanism rather than hand-rolled `f-strings` when the arguments are user-controlled.
- **Overloading prompts with everything** — a prompt should be focused; split into
  several.

## Testing

- **Retrieval tests**: `prompts/get` returns messages with arguments interpolated
  correctly ([15-testing/prompt-testing.md](../15-testing/prompt-testing.md)).
- **Discovery tests**: `prompts/list` shows the catalog with correct argument
  metadata.
- **Validation tests**: missing required arguments produce a clean error.
- **Rendering tests**: assert exact message text for known inputs (golden files work
  well here).

## Debugging

- In Inspector, list prompts and call `prompts/get` with sample arguments — you'll see
  the rendered messages immediately
  ([07-inspector-debugging/prompts.md](../07-inspector-debugging/prompts.md)).
- If a client "ignores" your prompt, check the description — the model decides which
  prompt fits, and a vague description means it won't be chosen.

## Security considerations

- **Prompts may contain injection content** (e.g. a prompt fed from user data). Treat
  rendered prompt text as potentially untrusted
  ([14-security/prompt-injection.md](../14-security/prompt-injection.md)).
- **Prompts are instructions to the model** — a malicious or careless prompt can steer
  the model to unsafe actions. Validate prompt inputs and keep instructions
  authoritative: put the strongest constraints in `system` messages.
- Don't embed secrets in prompt templates — they're fetched by any client that knows
  the name.

## Related concepts

- [tools.md](tools.md) — actions
- [resources.md](resources.md) — data
- [03-routing-dispatch/04-prompt-routing.md](../03-routing-dispatch/04-prompt-routing.md)
- [15-testing/prompt-testing.md](../15-testing/prompt-testing.md)
- [14-security/prompt-injection.md](../14-security/prompt-injection.md)