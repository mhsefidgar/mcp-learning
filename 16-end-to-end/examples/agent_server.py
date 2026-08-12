"""Order-processing server: the domain side of the end-to-end agent.

Exposes tools (create/get/ship order, with validation, errors, progress, and an
approval elicitation for the destructive ship step), a resource template, and a
prompt. The agent in agent.py drives it.

    python agent_server.py              # run over stdio
    python agent.py                     # drive it from the agent
    pytest test_agent.py
"""
import asyncio

from fastmcp import FastMCP, Context
from fastmcp.dependencies import CurrentContext
from fastmcp.exceptions import ToolError

mcp = FastMCP("orders")

_orders: dict[str, dict] = {}
_counters = {"created": 0}


@mcp.tool
async def create_order(item: str, quantity: int,
                       ctx: Context = CurrentContext()) -> dict:
    """Create an order. Returns {order_id, item, quantity, total}."""
    if not item.strip():
        raise ToolError("item must be a non-empty string")
    if quantity <= 0 or quantity > 100:
        raise ToolError("quantity must be between 1 and 100")
    _counters["created"] += 1
    order_id = f"ord-{_counters['created']}"
    # the id is part of the record so lookups carry it (the agent chains on it)
    _orders[order_id] = {"order_id": order_id, "item": item,
                         "quantity": quantity, "total": 10 * quantity,
                         "status": "created"}
    await ctx.info(f"created {order_id}")
    return {"order_id": order_id, "item": item, "quantity": quantity,
            "total": 10 * quantity}


@mcp.tool
def get_order(order_id: str) -> dict:
    """Get an order's current state."""
    if order_id not in _orders:
        raise ToolError(f"unknown order: {order_id}")
    return _orders[order_id]


@mcp.tool
async def ship_order(order_id: str, confirm: bool,
                     ctx: Context = CurrentContext()) -> dict:
    """Ship an order. Asks the human for confirmation first, then reports
    progress while the (simulated) shipping work runs."""
    order = _orders.get(order_id)
    if order is None:
        raise ToolError(f"unknown order: {order_id}")

    answer = await ctx.elicit(
        f"Ship order {order_id} ({order['quantity']}x {order['item']}, "
        f"total {order['total']})? This charges the customer.",
        response_type=bool,
    )
    if answer.action != "accept" or not getattr(answer, "data", None):
        return {"order_id": order_id, "status": "cancelled",
                "reason": "user declined"}

    for step in range(1, 6):                      # simulated long-running work
        await ctx.report_progress(step, 5)
        await asyncio.sleep(0.02)
    order["status"] = "shipped"
    return {"order_id": order_id, "status": "shipped"}


_flaky_failures: dict[str, int] = {}   # order_id -> remaining failures


@mcp.tool
async def flaky_lookup(order_id: str) -> dict:
    """Read an order, but fails the first two attempts per order so the agent
    can demo retries deterministically (failures reset after a success)."""
    if order_id not in _orders:
        raise ToolError(f"unknown order: {order_id}")
    remaining = _flaky_failures.get(order_id, 2)
    if remaining > 0:
        _flaky_failures[order_id] = remaining - 1
        raise ToolError("temporary upstream failure; try again")
    return _orders[order_id]


@mcp.resource("orders://{order_id}")
def order_resource(order_id: str) -> str:
    """An order's state, addressable by URI template."""
    return str(_orders.get(order_id, {"error": "not found"}))


@mcp.prompt()
def order_summary(order_id: str) -> str:
    """Template: summarize an order for the user."""
    return f"Summarize order {order_id} for the user."


if __name__ == "__main__":
    mcp.run()
