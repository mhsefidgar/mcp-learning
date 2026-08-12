# 02 — The Three Core Primitives

**What this section teaches.** The three things an MCP server can expose — **tools**
(things the model can *do*), **resources** (data the model can *read*), and **prompts**
(reusable instructions the model can *follow*). After this section you can design a
server's surface: which capabilities belong in tools, which in resources, and which in
prompts.

**Prerequisites.** [01-fundamentals](../01-fundamentals/README.md).

**Recommended reading order:**

1. [tools.md](tools.md) — the most important primitive
2. [resources.md](resources.md) — data, URIs, templates
3. [prompts.md](prompts.md) — instruction templates

**Relevant examples:** `examples/` — a single FastMCP server exposing all three, plus a
client that discovers and uses them.

**Relevant implementations:** `implementations/python-fastmcp`, `implementations/typescript-sdk`.

**Exercises.**

1. **Build a tool** that takes a city name and returns the current weather (mock the
   data). *Acceptance:* `tools/list` shows it with a correct JSON Schema; `tools/call`
   returns structured content.
2. **Add a resource** `weather://current/{city}` and a resource template. *Acceptance:*
   `resources/list` shows the static one, `resources/templates/list` shows the pattern,
   and `resources/read` resolves both.
3. **Add a prompt** "plan_trip" that takes `destination` and `days`. *Acceptance:*
   `prompts/get` returns messages with the arguments interpolated.
4. **The classification challenge**: for each of these, decide tool vs resource vs
   prompt and justify: (a) "list files in a directory", (b) "the current git branch",
   (c) "a template for writing a bug report". *Acceptance:* you can defend each choice
   using the decision rules in [tools.md](tools.md) and [resources.md](resources.md).

**Common mistakes in this section**

- Making a **resource** that has side effects (deleting files). Resources are *reads*;
  side effects belong in tools.
- Making a **tool** that only returns data the model could read as a resource. If it
  never mutates anything and is addressed by a URI, it's probably a resource.
- Treating **prompts** as server-side LLM prompts. MCP prompts are *templates* the
  client renders; the server does not call an LLM.