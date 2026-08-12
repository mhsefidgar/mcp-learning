/**
 * MCP-free business logic — no imports from the MCP SDK, so it is unit
 * testable in isolation (the same separation as the Python implementation).
 */
export class DomainError extends Error {
}
export class OrderBook {
    orders = new Map();
    next = 1;
    create(item, quantity) {
        if (!item || !item.trim()) {
            throw new DomainError("item must be a non-empty string");
        }
        if (!Number.isInteger(quantity) || quantity < 1 || quantity > 100) {
            throw new DomainError("quantity must be between 1 and 100");
        }
        const order = {
            orderId: `ord-${this.next++}`,
            item,
            quantity,
            total: 10 * quantity,
            status: "created",
        };
        this.orders.set(order.orderId, order);
        return order;
    }
    get(orderId) {
        const order = this.orders.get(orderId);
        if (!order) {
            throw new DomainError(`unknown order: ${orderId}`);
        }
        return order;
    }
    ship(orderId) {
        const order = this.get(orderId);
        if (order.status !== "created") {
            throw new DomainError(`order ${orderId} is already ${order.status}`);
        }
        order.status = "shipped";
        return order;
    }
}
//# sourceMappingURL=orders.js.map