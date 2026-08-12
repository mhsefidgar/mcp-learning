# Inspecting Prompts

## What is it?

The Inspector's **prompts view** shows `prompts/list` (name, description, arguments)
and lets you call `prompts/get` with sample argument values to see the rendered
messages.

## Why it matters

Prompt bugs are **rendering and selection** bugs: arguments not interpolated, the
wrong template for a name, or a description so vague the model never chooses the
prompt. The Inspector shows you the exact messages a client would receive
([02-primitives/prompts.md](../02-primitives/prompts.md)).

## How to use it

1. Read the Prompts panel — for each prompt, note the description and argument list.
2. Call `prompts/get` with sample arguments.
3. Check: are the arguments interpolated correctly? Is the message set what you
   designed (roles, system instructions)? Do missing required arguments fail cleanly?
4. Judge the *description* as a model would: does it say when to use this prompt?

## Typical findings

| Observation | Meaning |
|-------------|---------|
| Placeholders not replaced | interpolation bug in the template |
| Argument `"42"` used as a number | MCP prompt arguments are strings — convert explicitly |
| Missing-argument call silently renders garbage | missing validation — fail cleanly instead |
| Model "never uses" the prompt | description is vague — rewrite it with *when* to use |

## Related

- [02-primitives/prompts.md](../02-primitives/prompts.md)
- [03-routing-dispatch/04-prompt-routing.md](../03-routing-dispatch/04-prompt-routing.md)
- [15-testing/prompt-testing.md](../15-testing/prompt-testing.md)