package dev.mcplearn.orders;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * MCP-free business logic — no imports from the MCP SDK, so this class is
 * unit-testable in isolation (the same separation as the Python and
 * TypeScript implementations; see 12-fastmcp/providers.md).
 */
public final class OrderBook {

    public static final class DomainError extends RuntimeException {
        public DomainError(String message) {
            super(message);
        }
    }

    public record Order(String orderId, String item, int quantity,
                        int total, String status) {
        public Map<String, Object> toMap() {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("orderId", orderId);
            m.put("item", item);
            m.put("quantity", quantity);
            m.put("total", total);
            m.put("status", status);
            return m;
        }
    }

    private final Map<String, Order> orders = new LinkedHashMap<>();
    private int next = 1;

    public Order create(String item, int quantity) {
        if (item == null || item.isBlank()) {
            throw new DomainError("item must be a non-empty string");
        }
        if (quantity < 1 || quantity > 100) {
            throw new DomainError("quantity must be between 1 and 100");
        }
        Order order = new Order("ord-" + next++, item, quantity, 10 * quantity, "created");
        orders.put(order.orderId(), order);
        return order;
    }

    public Order get(String orderId) {
        Order order = orders.get(orderId);
        if (order == null) {
            throw new DomainError("unknown order: " + orderId);
        }
        return order;
    }

    public Order ship(String orderId) {
        Order order = get(orderId);
        if (!order.status().equals("created")) {
            throw new DomainError("order " + orderId + " is already " + order.status());
        }
        Order shipped = new Order(order.orderId(), order.item(), order.quantity(),
                order.total(), "shipped");
        orders.put(orderId, shipped);
        return shipped;
    }
}
