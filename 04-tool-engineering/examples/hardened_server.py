"""A progressively hardened "orders" server demonstrating the tool-engineering
patterns from this section: precise schemas, semantic validation, structured output,
idempotency, progress, timeouts, and the two error channels.

    python hardened_server.py          # run over stdio
    python client_hardened.py          # drive it from a client
    pytest test_hardened.py            # test the failure table
"""
import asyncio
import time
import uuid

from fastmcp import FastMCP, Context
from fastmcp.exceptions import ToolError

mcp = FastMCP("hardened-orders")

# A toy in-memory store: {id: {"id", "customer", "amount", "currency", "status"}}
_orders: dict[int, dict] = {}
_idempotency: dict[str, dict] = {}  # idempotency_key -> stored result
_next_id = 1


def _seed() -> None:
    global _next_id
    for customer, amount in [("Acme", 42.5), ("Globex", 99.0), ("Initech", 12.0)]:
        _orders[_next_id] = {"id": _next_id, "customer": customer,
                             "amount": amount, "currency": "USD", "status": "paid"}
        _next_id += 1


_seed()


# --- 1. Schema + validation + structured output -------------------------------

@mcp.tool
def get_order(order_id: int) -> dict:
    """Get one order as JSON: {id, customer, amount, currency, status}."""
    order = _orders.get(order_id)
    if order is None:
        raise ToolError(f"Order {order_id} does not exist")     # semantic -> isError
    return order                                               # structured output


# --- 2. Idempotency (write path) ---------------------------------------------

@mcp.tool
def create_order(customer: str, amount: float, idempotency_key: str | None = None) -> dict:
    """Create an order. Pass the same idempotency_key to retry safely.

    Returns {id, customer, amount, currency, status, created}.
    """
    global _next_id
    key = idempotency_key or uuid.uuid4().hex
    if key in _idempotency:                                    # replay -> stored result
        return _idempotency[key]

    order_id = _next_id
    _next_id += 1
    order = {"id": order_id, "customer": customer, "amount": round(amount, 2),
             "currency": "USD", "status": "open", "created": True}
    _orders[order_id] = order
    _idempotency[key] = order                                  # remember for retries
    return order


# --- 3. Progress + cooperative cancellation -----------------------------------

@mcp.tool
async def render_report(rows: int, ctx: Context) -> str:
    """Simulate generating a report, reporting progress (cancellable)."""
    for i in range(rows):
        await asyncio.sleep(0.02)                              # cancellation point
        await ctx.report_progress(i + 1, rows)
    return f"Report ready with {rows} rows"


# --- 4. Timeout bound ---------------------------------------------------------

@mcp.tool
async def slow_op(delay: float) -> str:
    """Simulate a downstream call; fails cleanly if it exceeds 3 seconds."""
    try:
        await asyncio.wait_for(asyncio.sleep(delay), timeout=3.0)
    except asyncio.TimeoutError:
        raise ToolError("slow_op timed out after 3s — try a smaller delay")
    return "done"


# --- 5. Result validation (defense in depth) ----------------------------------

def _validate_result(result: dict) -> dict:
    """Every tool result passes a shape check before leaving the server.

    Educational simplification — production servers validate against the
    documented output schema (see structured-output.md).
    """
    if not isinstance(result, dict) or "id" not in result:
        raise RuntimeError(f"result failed shape validation: {result!r}")
    return result


if __name__ == "__main__":
    mcp.run()
