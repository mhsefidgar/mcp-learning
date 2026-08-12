"""MCP-free business logic for the orders server.

Keeping the domain separate from FastMCP is the point: this module has no
import of `fastmcp`, so it is unit-testable in isolation and reusable outside
an MCP context (12-fastmcp/providers.md).
"""
from dataclasses import dataclass, field
from typing import Any

# --- domain types -------------------------------------------------------------


class DomainError(Exception):
    """A domain-level error, mapped to a tool error by the MCP adapter."""


@dataclass
class Order:
    order_id: str
    item: str
    quantity: int
    total: int
    status: str = "created"

    def to_dict(self) -> dict[str, Any]:
        return {"order_id": self.order_id, "item": self.item,
                "quantity": self.quantity, "total": self.total,
                "status": self.status}


# --- domain service -----------------------------------------------------------

class OrderBook:
    """In-memory order store. (In production this is a repository over a real
    database — the adapter pattern keeps the MCP layer unchanged.)"""

    def __init__(self) -> None:
        self._orders: dict[str, Order] = {}
        self._next = 1

    def create(self, item: str, quantity: int) -> Order:
        if not item or not item.strip():
            raise DomainError("item must be a non-empty string")
        if not 1 <= quantity <= 100:
            raise DomainError("quantity must be between 1 and 100")
        order = Order(order_id=f"ord-{self._next}", item=item,
                      quantity=quantity, total=10 * quantity)
        self._orders[order.order_id] = order
        self._next += 1
        return order

    def get(self, order_id: str) -> Order:
        if order_id not in self._orders:
            raise DomainError(f"unknown order: {order_id}")
        return self._orders[order_id]

    def ship(self, order_id: str) -> Order:
        order = self.get(order_id)
        if order.status != "created":
            raise DomainError(f"order {order_id} is already {order.status}")
        order.status = "shipped"
        return order
