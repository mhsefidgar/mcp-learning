# 04 — Prompt Routing

## What is it?

**Prompt routing** is the mapping from a prompt *name* (received in `prompts/get`) to
the template that renders it — including how arguments are validated and how the
template interpolates them. It's simpler than tool/resource routing (names, not URIs;
string arguments, not schemas), but it has its own pitfalls around argument handling
and versions.

```
prompts/get {name: "summarize_bug", arguments: {bug_id: "42"}}
        │
        ▼
  registry lookup → handler(bug_id="42") → interpolated messages
```

## Why does MCP need it?

Prompts are *named, reusable assets*; the name is the contract. Routing decides which
template a name refers to, whether the provided arguments are acceptable, and what the
client receives. With routing in place, a client can list the catalog (`prompts/list`)
and use any prompt by name without knowing its internals.

## How does it work?

1. **List**: `prompts/list` returns name + description + argument metadata.
2. **Lookup**: `prompts/get` resolves the name in the registry.
3. **Argument check**: required arguments present? (MCP prompt arguments are simple
   strings — see [02-primitives/prompts.md](../02-primitives/prompts.md).)
4. **Render**: the template interpolates the arguments and returns the message list.

### Advanced patterns

- **Parameterized prompts** — a prompt's *value* depends on its arguments
  (`summarize_bug(bug_id)`). FastMCP renders Python functions; the TS/Java SDKs render
  templates with argument substitution.
- **Prompt versions** — `onboard_v1` / `onboard_v2` for incompatible template changes
  ([13-versioning/deprecation.md](../13-versioning/deprecation.md),
  [09-version-aware-routing.md](09-version-aware-routing.md)).
- **Grouping** — name prefixes act as namespaces (`security_*`, `onboarding_*`), the
  same convention as tools ([02-tool-routing.md](02-tool-routing.md)).

## Mental model

Prompt routing is a **template registry**: name → (argument spec, render function).
Like a mail-merge library: you pick the form by name, fill the fields, and get the
document.

## MCP-specific behavior

- **Arguments are strings** — numbers arrive as `"42"`; the template must handle
  conversion. (FastMCP generates string-typed prompt arguments from function
  parameters and documents their expected shape in the description.)
- **`prompts/get` failures**: unknown name → prompt-not-found error; missing required
  argument → invalid-params error ([10-error-routing.md](10-error-routing.md)).
- **`listChanged`** capability: send `notifications/prompts/list_changed` when the
  catalog changes so clients re-list.
- **Prompts are not executed** — routing stops at rendering; no side effects.

## Example

FastMCP — the decorated function *is* the route:

```python
from fastmcp import FastMCP

mcp = FastMCP("support")

@mcp.prompt
def summarize_bug_report(bug_id: str) -> str:
    """Create a structured bug summary for an engineer."""
    return (
        f"You are a support engineer. Summarize bug #{bug_id} into: "
        "(1) symptom, (2) cause, (3) fix. Be concise."
    )
```

A versioned pair:

```python
@mcp.prompt
def onboarding_v1(role: str) -> str:
    return f"Explain the codebase to a new {role}, focusing on architecture."

@mcp.prompt
def onboarding_v2(role: str) -> str:
    return (f"Explain the codebase to a new {role}. First the architecture, "
            "then the deployment pipeline, then the testing conventions.")
```

TypeScript SDK:

```typescript
server.registerPrompt(
  "summarize_bug_report",
  { description: "Create a structured bug summary.",
    arguments: [{ name: "bug_id", description: "Bug tracker ID", required: true }] },
  async ({ bug_id }) => ({
    messages: [{ role: "user", content: { type: "text", text: `Summarize bug #${bug_id}.` } }],
  })
);
```

## Industry-standard pattern

A named-template registry with parameter validation is the pattern behind **email
templates, prompt libraries, and localization catalogs**. The operational concerns are
the same: names are stable identifiers, parameters are validated up front, and the
catalog is versioned.

## Common mistakes

- **Assuming prompts run code or call an LLM** — they render text
  ([02-primitives/prompts.md](../02-primitives/prompts.md)).
- **Silently accepting missing arguments** — the template renders garbage instead of a
  clean error.
- **Type confusion in templates** — `"42"` used where a number was expected; convert
  explicitly.
- **No versioning story** — editing a prompt's text changes behavior for every client
  silently (see [13-versioning/deprecation.md](../13-versioning/deprecation.md)).

## Testing

- **Registry tests**: every listed prompt resolves; unknown names fail cleanly
  ([15-testing/prompt-testing.md](../15-testing/prompt-testing.md)).
- **Argument tests**: required-missing → error; provided → rendered.
- **Golden-file tests**: assert exact rendered text for known inputs — this catches
  accidental template edits.
- **Version tests**: `v1` and `v2` render their own text.

## Debugging

- Inspector's prompt panel lists prompts and renders them with sample arguments — a
  two-second way to see interpolation bugs
  ([07-inspector-debugging/prompts.md](../07-inspector-debugging/prompts.md)).
- If the client "didn't use" your prompt, check the description: the model chooses
  prompts by description.

## Security considerations

- **Prompt templates are instructions to the model** — sanitize/validate arguments so
  a user can't inject conflicting instructions via a prompt argument
  ([14-security/prompt-injection.md](../14-security/prompt-injection.md)).
- **Never embed secrets in templates** — they're fetched by name by any client.
- **Template rendering must not execute code** (no eval of argument strings).

## Related concepts

- [01-request-dispatch.md](01-request-dispatch.md)
- [09-version-aware-routing.md](09-version-aware-routing.md)
- [10-error-routing.md](10-error-routing.md)
- [02-primitives/prompts.md](../02-primitives/prompts.md)
- [15-testing/prompt-testing.md](../15-testing/prompt-testing.md)