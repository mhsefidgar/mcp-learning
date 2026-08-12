/**
 * Integration tests: spawn the compiled server over stdio and drive it with
 * the official SDK client (15-testing/integration-testing.md).
 *
 *   npm test
 */
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";
import { fileURLToPath } from "node:url";

import { OrderBook, DomainError } from "../src/orders.js";

const serverPath = fileURLToPath(new URL("../dist/server.js", import.meta.url));

describe("domain (unit, no MCP)", () => {
  it("creates and ships an order", () => {
    const book = new OrderBook();
    const order = book.create("widget", 2);
    expect(order.total).toBe(20);
    book.ship(order.orderId);
    expect(book.get(order.orderId).status).toBe("shipped");
  });

  it("rejects bad input and double-shipping", () => {
    const book = new OrderBook();
    expect(() => book.create("", 1)).toThrow(DomainError);
    expect(() => book.create("widget", 0)).toThrow(DomainError);
    const order = book.create("widget", 1);
    book.ship(order.orderId);
    expect(() => book.ship(order.orderId)).toThrow(DomainError);
  });
});

describe("server over stdio (integration)", () => {
  let client: Client;
  let transport: StdioClientTransport;

  beforeAll(async () => {
    transport = new StdioClientTransport({ command: process.execPath, args: [serverPath] });
    client = new Client({ name: "test-client", version: "0.0.1" });
    await client.connect(transport);
  });

  afterAll(async () => {
    await client.close();
  });

  it("negotiates capabilities and lists tools", async () => {
    const caps = client.getServerCapabilities();
    expect(caps?.tools).toBeDefined();
    const tools = await client.listTools();
    expect(tools.tools.map((t) => t.name)).toContain("create_order");
  });

  it("creates an order end to end", async () => {
    const result = await client.callTool({ name: "create_order", arguments: { item: "widget", quantity: 3 } });
    const order = JSON.parse(result.content[0].text);
    expect(order.total).toBe(30);
    expect(order.status).toBe("created");
  });

  it("reads a resource by URI template", async () => {
    await client.callTool({ name: "create_order", arguments: { item: "w", quantity: 1 } });
    const read = await client.readResource({ uri: "orders://ord-1" });
    expect(read.contents[0].text).toContain("ord-1");
  });

  it("gets a prompt", async () => {
    const prompt = await client.getPrompt({ name: "order_summary", arguments: { orderId: "ord-1" } });
    expect(prompt.messages[0].content.text).toContain("ord-1");
  });

  it("returns a tool error result for bad arguments", async () => {
    const result = await client.callTool({ name: "create_order", arguments: { item: "x", quantity: 0 } });
    expect(result.isError).toBe(true);
  });
});
