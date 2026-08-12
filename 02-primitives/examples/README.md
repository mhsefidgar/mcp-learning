# 02-primitives examples

A single FastMCP server exposing all three primitives, plus a client that discovers
and uses them, plus tests.

## Run

```bash
# from the repository root, with the shared venv (see implementations/python-fastmcp)
.venv/Scripts/python.exe 02-primitives/examples/client.py   # Windows
.venv/bin/python 02-primitives/examples/client.py           # macOS/Linux
```

`client.py` starts `server.py` over stdio automatically and prints:

- the discovered catalog (tools, resources, templates, prompts)
- a tool call result
- a static resource read
- a template-resolved resource read (`math://square/9` → `81`)
- a rendered prompt

## Test

```bash
.venv/Scripts/python.exe -m pytest 02-primitives/examples/test_primitives.py -q
```

4 tests: tool discovery+call, resource discovery+read, template resolution, prompt
retrieval.

## Notes on the FastMCP 3.x API (verified against 3.4.7)

- Server side: `await mcp.list_tools()`, `await mcp.call_tool(name, args)` (returns
  `ToolResult` with `.structured_content`), `await mcp.read_resource(uri)` (returns
  `ResourceResult` with `.contents`), `await mcp.render_prompt(name, args)`.
- Client side: `await client.list_tools()`, `await client.call_tool(...)` (returns
  `CallToolResult`), `await client.read_resource(uri)` (**returns a list of content
  blocks directly**), `await client.get_prompt(name, args)`.
- **MCP prompt arguments are strings** — pass `"5"`, not `5`.
- `Client("server.py")` infers a stdio transport from a script path.
