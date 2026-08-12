/**
 * MCP-free business logic — no imports from the MCP SDK, so it is unit
 * testable in isolation (the same separation as the Python implementation).
 */

export interface Order {
  orderId: string;
  item: string;
  quantity: number;
  total: number;
  status: "created" | "shipped";
}

export class DomainError extends Error {}

export class OrderBook {
  private orders = new Map<string, Order>();
  private next = 1;

  create(item: string, quantity: number): Order {
    if (!item || !item.trim()) {
      throw new DomainError("item must be a non-empty string");
    }
    if (!Number.isInteger(quantity) || quantity < 1 || quantity > 100) {
      throw new DomainError("quantity must be between 1 and 100");
    }
    const order: Order = {
      orderId: `ord-${this.next++}`,
      item,
      quantity,
      total: 10 * quantity,
      status: "created",
    };
    this.orders.set(order.orderId, order);
    return order;
  }

  get(orderId: string): Order {
    const order = this.orders.get(orderId);
    if (!order) {
      throw new DomainError(`unknown order: ${orderId}`);
    }
    return order;
  }

  ship(orderId: string): Order {
    const order = this.get(orderId);
    if (order.status !== "created") {
      throw new DomainError(`order ${orderId} is already ${order.status}`);
    }
    order.status = "shipped";
    return order;
  }
}
