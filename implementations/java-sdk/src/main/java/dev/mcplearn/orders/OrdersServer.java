package dev.mcplearn.orders;

import java.util.List;
import java.util.Map;

import io.modelcontextprotocol.json.McpJsonDefaults;
import io.modelcontextprotocol.server.McpServer;
import io.modelcontextprotocol.server.McpServerFeatures;
import io.modelcontextprotocol.server.McpSyncServer;
import io.modelcontextprotocol.server.transport.StdioServerTransportProvider;
import io.modelcontextprotocol.spec.McpSchema;
import io.modelcontextprotocol.spec.McpSchema.CallToolResult;
import io.modelcontextprotocol.spec.McpSchema.Prompt;
import io.modelcontextprotocol.spec.McpSchema.PromptArgument;
import io.modelcontextprotocol.spec.McpSchema.PromptMessage;
import io.modelcontextprotocol.spec.McpSchema.ReadResourceResult;
import io.modelcontextprotocol.spec.McpSchema.Resource;
import io.modelcontextprotocol.spec.McpSchema.Role;
import io.modelcontextprotocol.spec.McpSchema.ServerCapabilities;
import io.modelcontextprotocol.spec.McpSchema.TextContent;
import io.modelcontextprotocol.spec.McpSchema.TextResourceContents;
import io.modelcontextprotocol.spec.McpSchema.Tool;

import com.fasterxml.jackson.databind.ObjectMapper;

/**
 * Order-processing MCP server using the official Java SDK (2.x).
 *
 * <pre>
 *   mvn -q package
 *   java -jar target/orders-java-1.0.0.jar        # run over stdio
 * </pre>
 *
 * NOTE: written against the published 2.0.0 API (verified against the SDK
 * source); NOT compiled or run in this repository's environment (no Java
 * toolchain available there).
 */
public final class OrdersServer {

    private static final ObjectMapper JSON = new ObjectMapper();

    /** Serialize a domain object to a JSON string (simple, demo-grade). */
    private static String toJson(Object value) {
        try {
            return JSON.writeValueAsString(value);
        } catch (Exception e) {
            throw new IllegalStateException("serialization failed", e);
        }
    }

    private static final OrderBook BOOK = new OrderBook();

    private static Tool createTool(String name, String title, String description,
                                   Map<String, Object> inputSchema) {
        return Tool.builder(name, inputSchema)
                .title(title)
                .description(description)
                .build();
    }

    private static McpServerFeatures.SyncToolSpecification createOrderTool() {
        return McpServerFeatures.SyncToolSpecification.builder()
                .tool(createTool("create_order", "Create order",
                        "Create an order. Returns the order record.",
                        Map.of(
                                "type", "object",
                                "properties", Map.of(
                                        "item", Map.of("type", "string"),
                                        "quantity", Map.of("type", "integer", "minimum", 1)),
                                "required", List.of("item", "quantity"))))
                .callHandler((exchange, request) -> {
                    Map<String, Object> args = request.arguments();
                    OrderBook.Order order = BOOK.create(
                            (String) args.get("item"), ((Number) args.get("quantity")).intValue());
                    return new CallToolResult(List.of(new TextContent(toJson(order.toMap()))), false);
                })
                .build();
    }

    private static McpServerFeatures.SyncToolSpecification getOrderTool() {
        return McpServerFeatures.SyncToolSpecification.builder()
                .tool(createTool("get_order", "Get order",
                        "Get an order's current state.",
                        Map.of(
                                "type", "object",
                                "properties", Map.of("orderId", Map.of("type", "string")),
                                "required", List.of("orderId"))))
                .callHandler((exchange, request) -> {
                    OrderBook.Order order = BOOK.get((String) request.arguments().get("orderId"));
                    return new CallToolResult(List.of(new TextContent(toJson(order.toMap()))), false);
                })
                .build();
    }

    private static McpServerFeatures.SyncResourceSpecification orderResource() {
        Resource resource = Resource.builder("orders://{orderId}", "order")
                .title("Order")
                .description("An order's state, addressable by URI template")
                .mimeType("application/json")
                .build();
        return McpServerFeatures.SyncResourceSpecification.builder()
                .resource(resource)
                .readHandler((exchange, request) -> {
                    // The URI template variable is exposed on the request path.
                    String orderId = request.getPath();
                    try {
                        OrderBook.Order order = BOOK.get(orderId);
                        return new ReadResourceResult(List.of(
                                TextResourceContents.builder("orders://" + orderId, toJson(order.toMap()))
                                        .mimeType("application/json").build()));
                    } catch (OrderBook.DomainError e) {
                        return new ReadResourceResult(List.of(
                                TextResourceContents.builder("orders://" + orderId, "{\"error\":\"not found\"}")
                                        .mimeType("application/json").build()));
                    }
                })
                .build();
    }

    private static McpServerFeatures.SyncPromptSpecification orderSummaryPrompt() {
        Prompt prompt = Prompt.builder("order_summary")
                .title("Order summary")
                .description("Template summarizing an order for the user")
                .arguments(List.of(PromptArgument.builder("orderId")
                        .description("the order id")
                        .required(true).build()))
                .build();
        return McpServerFeatures.SyncPromptSpecification.builder()
                .prompt(prompt)
                .getPromptHandler((exchange, request) -> {
                    String orderId = (String) request.arguments().get("orderId");
                    PromptMessage message = new PromptMessage(Role.USER,
                            new TextContent("Summarize order " + orderId + " for the user."));
                    return McpSchema.GetPromptResult.builder(List.of(message))
                            .description("Order summary")
                            .build();
                })
                .build();
    }

    public static McpSyncServer createServer() {
        McpSyncServer server = McpServer.sync(
                        new StdioServerTransportProvider(McpJsonDefaults.getMapper()))
                .serverInfo("orders-java", "1.0.0")
                .capabilities(testCapabilities())
                .build();

        for (McpServerFeatures.SyncToolSpecification tool : toolsForTesting()) {
            server.addTool(tool);
        }
        server.addResource(orderResource());
        server.addPrompt(orderSummaryPrompt());
        return server;
    }

    /** The tool specs the server registers — exposed for handler-level tests. */
    static List<McpServerFeatures.SyncToolSpecification> toolsForTesting() {
        return List.of(createOrderTool(), getOrderTool());
    }

    /** The capabilities the server advertises — exposed for tests. */
    static ServerCapabilities testCapabilities() {
        return ServerCapabilities.builder()
                .resources(true)
                .tools(true)
                .prompts(true)
                .build();
    }

    public static void main(String[] args) {
        // The stdio transport runs its own (non-daemon) thread, which keeps the
        // JVM alive until the client closes the stream. Shutting down cleanly is
        // demonstrated by the client's closeGracefully() in OrdersClient.
        createServer();
    }
}
