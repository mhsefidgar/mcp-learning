/**
 * Drive the orders-ts server with the official SDK client.
 *
 *   npm run client
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { fileURLToPath } from "node:url";
/** Extract the text from a tool result's first text content block. */
function textOf(result) {
    const block = result.content[0];
    if (!block || block.type !== "text") {
        throw new Error("expected a text result");
    }
    return block.text;
}
/** Extract text from a resource read result. */
function resourceTextOf(contents) {
    const block = contents[0];
    if (!("text" in block)) {
        throw new Error("expected a text resource");
    }
    return block.text;
}
const transport = new StdioClientTransport({
    command: process.execPath,
    args: [fileURLToPath(new URL("./server.js", import.meta.url))],
});
const client = new Client({ name: "orders-client", version: "1.0.0" });
await client.connect(transport);
console.log("server:", client.getServerVersion());
console.log("capabilities:", Object.keys(client.getServerCapabilities() ?? {}));
const tools = await client.listTools();
console.log("tools:", tools.tools.map((t) => t.name).join(", "));
const created = (await client.callTool({ name: "create_order", arguments: { item: "widget", quantity: 2 } }));
const order = JSON.parse(textOf(created));
console.log("created:", order);
const read = await client.readResource({ uri: `orders://${order.orderId}` });
console.log("resource:", resourceTextOf(read.contents));
const prompt = await client.getPrompt({ name: "order_summary", arguments: { orderId: order.orderId } });
const promptText = prompt.messages[0].content;
console.log("prompt:", "text" in promptText ? promptText.text : JSON.stringify(promptText));
await client.close();
//# sourceMappingURL=client.js.map