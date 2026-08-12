# 07 — MCP Inspector & Debugging

**What this section teaches.** How to use the **MCP Inspector** — the official
browser-based debugging tool — and how to diagnose the most common failure classes
(initialization, transport, protocol). After this section you can debug any MCP
server: inspect what it declares, call its operations by hand, and read the raw
protocol exchange.

**Prerequisites.** [01-fundamentals](../01-fundamentals/README.md) — you need to know
what initialize, capabilities, and transports are before you can debug them.

**What is the MCP Inspector?** A web UI (started with `npx @modelcontextprotocol/inspector`)
that connects to your server (stdio or HTTP), performs the handshake, and lets you:
inspect capabilities and tools/resources/prompts, call tools with hand-typed
arguments, read resources, get prompts, and watch **every raw protocol message**.

**Recommended reading order:**

1. [capabilities.md](capabilities.md) — what the server declares
2. [tools.md](tools.md) · [schemas.md](schemas.md) — the tool catalog and schemas
3. [resources.md](resources.md) · [prompts.md](prompts.md)
4. [protocol-messages.md](protocol-messages.md) — the raw exchange (the power tool)
5. [initialization-debugging.md](initialization-debugging.md) · [transport-debugging.md](transport-debugging.md) — failure classes

**Starting the Inspector:**

```bash
npx @modelcontextprotocol/inspector   # then follow the UI: pick a transport,
                                      # point it at your server, click Connect
```

For a stdio server: `python implementations/python-fastmcp/server.py`. For an HTTP
server: the URL, e.g. `http://localhost:8000/mcp`.

**Relevant examples:** `examples/` — scripts that dump the same information
programmatically (when you can't run a browser).

**Exercises.**

1. **Inspect a server**: connect Inspector to any example server; write down (a) the
   capabilities, (b) the tool list with schemas, (c) the resources/prompts.
   *Acceptance:* you can answer all three without reading the server code.
2. **Call a tool by hand**: invoke a tool with deliberately wrong arguments; then with
   right ones. *Acceptance:* you can describe the difference between the two failure
   channels (JSON-RPC error vs. `isError`).
3. **Read the handshake**: open the raw protocol panel, connect fresh, and explain
   every message from `initialize` to `notifications/initialized`.
4. **Break it on purpose**: start a server with a broken transport (wrong port,
   missing script) and diagnose the failure class
   ([transport-debugging.md](transport-debugging.md)).

**Common mistakes in this section**

- Debugging the *application* when the failure is in the *protocol* (Inspector shows
  which layer is failing).
- Forgetting that Inspector's client sends **no auth token** — "works in Inspector,
  fails in my app" is usually identity, not code
  ([03-routing-dispatch/08-authorization-routing.md](../03-routing-dispatch/08-authorization-routing.md)).
- Ignoring stderr for stdio servers — it's the server's only voice.