/**
 * Order-processing MCP server using the official TypeScript SDK.
 *
 *   npm run build && npm start        # run over stdio
 */
import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { pathToFileURL } from "node:url";
import { z } from "zod";
import { OrderBook, DomainError } from "./orders.js";
const book = new OrderBook();
export const server = new McpServer({ name: "orders-ts", version: "1.0.0" }, { capabilities: { tools: {}, resources: {}, prompts: {} } });
// --- tools -------------------------------------------------------------------
server.registerTool("create_order", {
    title: "Create order",
    description: "Create an order. Returns the order record.",
    inputSchema: {
        item: z.string().min(1).describe("item to order"),
        quantity: z.number().int().min(1).max(100).describe("how many"),
    },
}, async ({ item, quantity }) => {
    try {
        const order = book.create(item, quantity);
        return { content: [{ type: "text", text: JSON.stringify(order) }] };
    }
    catch (err) {
        // SDK tools may throw; the SDK converts to a tool error result.
        throw new Error(err instanceof DomainError ? err.message : String(err));
    }
});
server.registerTool("get_order", {
    title: "Get order",
    description: "Get an order's current state.",
    inputSchema: { orderId: z.string().min(1) },
}, async ({ orderId }) => {
    try {
        return { content: [{ type: "text", text: JSON.stringify(book.get(orderId)) }] };
    }
    catch (err) {
        throw new Error(err instanceof DomainError ? err.message : String(err));
    }
});
// --- resources ---------------------------------------------------------------
server.registerResource("order", new ResourceTemplate("orders://{orderId}", { list: undefined }), { mimeType: "application/json" }, async (uri, variables) => {
    const orderId = String(variables.orderId);
    try {
        return { contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify(book.get(orderId)) }] };
    }
    catch {
        return { contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify({ error: "not found" }) }] };
    }
});
// --- prompts -----------------------------------------------------------------
server.registerPrompt("order_summary", {
    description: "Template summarizing an order for the user.",
    argsSchema: { orderId: z.string().min(1) },
}, async ({ orderId }) => ({
    messages: [{ role: "user", content: { type: "text", text: `Summarize order ${orderId} for the user.` } }],
}));
// --- entry point --------------------------------------------------------------
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
    const transport = new StdioServerTransport();
    await server.connect(transport);
}
//# sourceMappingURL=server.js.map