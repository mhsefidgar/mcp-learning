package dev.mcplearn.orders;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Map;

import org.junit.jupiter.api.Test;

import io.modelcontextprotocol.server.McpServerFeatures;
import io.modelcontextprotocol.server.McpSyncServer;
import io.modelcontextprotocol.spec.McpSchema.CallToolRequest;
import io.modelcontextprotocol.spec.McpSchema.TextContent;

/**
 * Handler-level tests: invoke the tool/resource/prompt handlers directly
 * (no transport), the pattern shown in the SDK's own documentation. See
 * 15-testing/server-testing.md for why this complements integration tests.
 */
class OrdersServerTest {

    private static final String CREATED =
            "{\"orderId\":\"ord-1\",\"item\":\"widget\",\"quantity\":2,\"total\":20,\"status\":\"created\"}";

    @Test
    void createOrderHandlerReturnsOrderRecord() {
        McpServerFeatures.SyncToolSpecification tool = OrdersServer.toolsForTesting().get(0);
        var result = tool.callHandler().apply(null,
                new CallToolRequest("create_order", Map.of("item", "widget", "quantity", 2)));
        assertNotNull(result);
        assertFalse(Boolean.TRUE.equals(result.isError()));
        String text = ((TextContent) result.content().getFirst()).text();
        assertTrue(text.contains("\"orderId\":\"ord-1\""));
        assertTrue(text.contains("\"total\":20"));
    }

    @Test
    void serverBuildsWithExpectedCapabilities() {
        McpSyncServer server = OrdersServer.createServer();
        assertNotNull(server);
        // addTool/addResource/addPrompt all succeeded without throwing, and
        // the server advertises the three primitives.
        var caps = OrdersServer.testCapabilities();
        assertTrue(caps.tools() != null);
        assertTrue(caps.resources() != null);
        assertTrue(caps.prompts() != null);
    }

    @Test
    void ordersAreIsolatedBetweenBookInstances() {
        // The server owns a single OrderBook; the domain itself must not leak
        // state across instances (used by tests and by the client).
        OrderBook a = new OrderBook();
        OrderBook b = new OrderBook();
        a.create("widget", 1);
        assertEquals("ord-1", b.create("widget", 1).orderId());
    }
}
