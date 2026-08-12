# Implementation

## What is it?

**Implementation** is the practical, step-by-step construction of the end-to-end
system described in [architecture.md](architecture.md) — what each piece looks
like in code, in what order to build it, and how the pieces connect.

## Step 1 — Build the server

Start with the domain: the things your system *does* (tools), *knows* (resources),
and *says* (prompts).

```python
from fastmcp import FastMCP, Context
from fastmcp.dependencies import CurrentContext
from fastmcp.exceptions import ToolError

mcp = FastMCP("orders")
_orders: dict[str, dict] = {}

@mcp.tool
async def create_order(item: str, quantity: int, ctx: Context = CurrentContext()) -> dict:
    """Create an order. Returns the order id and total."""
    if quantity <= 0:
        raise ToolError("quantity must be positive")
    order_id = f"ord-{len(_orders) + 1}"
    _orders[order_id] = {"item": item, "quantity": quantity, "status": "created"}
    await ctx.info(f"created order {order_id}")
    return {"order_id": order_id, "total": 10 * quantity}

@mcp.resource("orders://{order_id}")
def order_resource(order_id: str) -> str:
    """An order's current state, addressable by URI template."""
    return str(_orders.get(order_id, {}))

@mcp.prompt()
def order_summary(order_id: str) -> str:
    """Template summarizing an order for the agent."""
    return f"Summarize order {order_id} for the user."
```

Rules that matter ([04-tool-engineering/README.md](../04-tool-engineering/README.md)):
every tool validates its inputs, returns structured results, raises `ToolError`
with a useful message, and never blocks forever (long work reports progress and
supports cancellation — [04-tool-engineering/long-running-operations.md](../04-tool-engineering/long-running-operations.md)).

## Step 2 — Harden the server

Add the middleware boundary from [14-security/README.md](../14-security/README.md):
logging + audit, auth + permissions where the server is remote. Add the
resilience and observability from [08-reliability-resilience/README.md](../08-reliability-resilience/README.md)
and [09-observability-telemetry/README.md](../09-observability-telemetry/README.md).
The [capstone](../capstone/python-server/) shows a fully hardened server; the
[14-security example](../14-security/examples/README.md) shows the boundary.

## Step 3 — Build the agent

The agent is the client plus its decision loop. For a scripted agent it's a
workflow; for an LLM agent it's a loop of "call a tool, read the result, decide
again." Either way it must:

1. **Connect and discover** ([01-fundamentals/05-initialization.md](../01-fundamentals/05-initialization.md)):

```python
from fastmcp import Client

async with Client("agent_server.py") as client:
    tools = {t.name: t for t in await client.list_tools()}
    assert "create_order" in tools
```

2. **Inspect schemas** before calling — never guess arguments
   ([04-tool-engineering/schemas.md](../04-tool-engineering/schemas.md)).
3. **Call with structured arguments** and *validate the result* before using it
   downstream ([14-security/untrusted-output.md](../14-security/untrusted-output.md)):

```python
result = await client.call_tool("create_order", {"item": "widget", "quantity": 2})
payload = parse(result)                    # your validation: type, required keys
order_id = payload["order_id"]             # only now may the next step use it
```

4. **Chain steps**: the next tool call's arguments come from the *validated*
   output of the previous one. Track intermediate state in the workflow, not in
   global variables ([04-tool-engineering/failure-handling.md](../04-tool-engineering/failure-handling.md)).
5. **Handle failures** ([04-tool-engineering/retries.md](../04-tool-engineering/retries.md)):

```python
for attempt in range(3):
    try:
        return await client.call_tool("ship_order", {"order_id": order_id})
    except TimeoutError:
        await asyncio.sleep(0.5 * 2 ** attempt)     # backoff (general pattern)
```

6. **Handle approvals** — the server asks via elicitation, your client shows the
   question ([06-agent-interaction/elicitation.md](../06-agent-interaction/elicitation.md)):

```python
async def on_elicit(message, response_type, params, context):
    print(f"[CONFIRM] {message}")
    return True if user_says_yes() else ElicitResult(action="decline", content="no")
```

7. **Handle long operations** — subscribe to progress and support cancellation
   ([06-agent-interaction/progress.md](../06-agent-interaction/progress.md),
   [04-tool-engineering/cancellation.md](../04-tool-engineering/cancellation.md)).
8. **Observe everything** — log each step (redacted), track latency and
   success rate, and shut down gracefully when done.

## Step 4 — Wire them together

Run the server over stdio (or Streamable HTTP for remote), point the agent at it,
and watch the whole loop: discovery → workflow → approval → completion → shutdown.

## Industry-standard pattern

Build in this order: **domain first, boundary second, orchestration third,
observability throughout.** The server must be correct and safe before the agent
exists; the agent must be testable without a live LLM (scripted workflows and
injected decisions), so the *system* is testable
([15-testing/README.md](../15-testing/README.md)).

## Common mistakes

- The agent trusting raw tool output (skipping validation before chaining).
- The server doing decision-making it shouldn't (or the agent doing
  authorization it can't).
- No graceful shutdown — sessions and subprocesses left dangling.
- Building the agent before the server's error semantics are defined.

## Related

- [architecture.md](architecture.md)
- [testing.md](testing.md)
- [examples/agent.py](examples/agent.py)
- [capstone/README.md](../capstone/README.md)
