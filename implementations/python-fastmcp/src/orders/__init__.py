"""The FastMCP adapter: exposes the OrderBook domain as MCP tools/resources.

    from orders import create_app
    app = create_app()
"""
from fastmcp import FastMCP, Context
from fastmcp.dependencies import CurrentContext
from fastmcp.exceptions import ToolError

from .domain import OrderBook

__all__ = ["create_app"]


def create_app() -> FastMCP:
    """Build the FastMCP server around a fresh OrderBook."""
    mcp = FastMCP("orders")
    book = OrderBook()

    # Domain errors are converted to clean tool errors by FastMCP's built-in
    # error-handling middleware (04-tool-engineering/errors.md) — no per-tool
    # try/except needed. For custom error semantics, raise ToolError explicitly.

    @mcp.tool
    def create_order(item: str, quantity: int) -> dict:
        """Create an order. Returns the order record."""
        return book.create(item, quantity).to_dict()

    @mcp.tool
    def get_order(order_id: str) -> dict:
        """Get an order's current state."""
        return book.get(order_id).to_dict()

    @mcp.tool
    async def ship_order(order_id: str, ctx: Context = CurrentContext()) -> dict:
        """Ship an order. Reports progress while the work runs."""
        order = book.get(order_id)
        for step in range(1, 6):
            await ctx.report_progress(step, 5)
        return book.ship(order_id).to_dict()

    @mcp.resource("orders://{order_id}")
    def order_resource(order_id: str) -> str:
        """An order's state, addressable by URI template."""
        try:
            return str(book.get(order_id).to_dict())
        except DomainError:
            return str({"error": "not found"})

    @mcp.prompt()
    def order_summary(order_id: str) -> str:
        """Template: summarize an order for the user."""
        return f"Summarize order {order_id} for the user."

    return mcp
