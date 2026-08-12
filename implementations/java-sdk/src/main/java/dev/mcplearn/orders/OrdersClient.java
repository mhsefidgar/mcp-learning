package dev.mcplearn.orders;

import java.util.Map;

import io.modelcontextprotocol.client.McpClient;
import io.modelcontextprotocol.client.McpSyncClient;
import io.modelcontextprotocol.client.transport.ServerParameters;
import io.modelcontextprotocol.client.transport.StdioClientTransport;
import io.modelcontextprotocol.json.McpJsonDefaults;
import io.modelcontextprotocol.spec.McpSchema.CallToolRequest;
import io.modelcontextprotocol.spec.McpSchema.CallToolResult;
import io.modelcontextprotocol.spec.McpSchema.ReadResourceRequest;
import io.modelcontextprotocol.spec.McpSchema.TextContent;

/**
 * Drive the orders-java server over stdio with the official SDK client.
 *
 * <pre>
 *   mvn -q package
 *   mvn -q exec:java -Dexec.mainClass=dev.mcplearn.orders.OrdersClient   # or run OrdersClient
 * </pre>
 *
 * NOTE: written against the published 2.0.0 API (verified against the SDK
 * source); NOT compiled or run in this repository's environment (no Java
 * toolchain available there).
 */
public final class OrdersClient {

    public static void main(String[] args) {
        // Spawn the packaged server jar as a subprocess over stdio.
        ServerParameters params = ServerParameters.builder("java")
                .args("-jar", "target/orders-java-1.0.0.jar")
                .build();
        StdioClientTransport transport = new StdioClientTransport(params,
                McpJsonDefaults.getMapper());

        McpSyncClient client = McpClient.sync(transport).build();
        try {
            client.initialize();

            client.listTools().tools().forEach(t ->
                    System.out.println("tool: " + t.name()));

            CallToolResult created = client.callTool(new CallToolRequest(
                    "create_order", Map.of("item", "widget", "quantity", 2)));
            String orderJson = ((TextContent) created.content().getFirst()).text();
            System.out.println("created: " + orderJson);

            String orderId = orderJson.replaceAll(".*\"orderId\"\\s*:\\s*\"([^\"]+)\".*", "$1");
            client.listResources().resources().forEach(r ->
                    System.out.println("resource: " + r.uri()));

            var read = client.readResource(ReadResourceRequest.builder("orders://" + orderId).build());
            System.out.println("read: " + ((TextContent) read.contents().getFirst()).text());

            var prompt = client.getPrompt(
                    io.modelcontextprotocol.spec.McpSchema.GetPromptRequest
                            .builder("order_summary").arguments(Map.of("orderId", orderId)).build());
            System.out.println("prompt: " + ((TextContent) prompt.messages().getFirst().content()).text());
        } finally {
            client.closeGracefully();
        }
    }
}
