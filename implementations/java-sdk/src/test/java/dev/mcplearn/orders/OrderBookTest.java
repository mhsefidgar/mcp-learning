package dev.mcplearn.orders;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

import org.junit.jupiter.api.Test;

import dev.mcplearn.orders.OrderBook.DomainError;
import dev.mcplearn.orders.OrderBook.Order;

/** Unit tests for the MCP-free domain layer (15-testing/server-testing.md). */
class OrderBookTest {

    @Test
    void createsOrderWithComputedTotal() {
        OrderBook book = new OrderBook();
        Order order = book.create("widget", 2);
        assertEquals("ord-1", order.orderId());
        assertEquals(20, order.total());
        assertEquals("created", order.status());
    }

    @Test
    void rejectsInvalidInput() {
        OrderBook book = new OrderBook();
        assertThrows(DomainError.class, () -> book.create("", 1));
        assertThrows(DomainError.class, () -> book.create("widget", 0));
        assertThrows(DomainError.class, () -> book.create("widget", 101));
    }

    @Test
    void shipsAndCannotShipTwice() {
        OrderBook book = new OrderBook();
        Order order = book.create("widget", 1);
        book.ship(order.orderId());
        assertEquals("shipped", book.get(order.orderId()).status());
        assertThrows(DomainError.class, () -> book.ship(order.orderId()));
    }

    @Test
    void unknownOrderThrows() {
        OrderBook book = new OrderBook();
        assertThrows(DomainError.class, () -> book.get("ord-999"));
    }
}
