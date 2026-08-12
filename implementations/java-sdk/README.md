# Java / MCP Java SDK reference implementation

An order-processing MCP server and client built with the official MCP Java SDK
**2.0.0**, in plain Java (no Spring): a Maven project, an MCP-free domain
(`OrderBook`), a stdio server, a stdio client demo, and JUnit tests.

> **Verification status.** This project was written against the published
> 2.0.0 API and cross-checked against the SDK source (record shapes, builders,
> `McpServer.sync`, `McpClient.sync`, `StdioServerTransportProvider`,
> `McpServerFeatures.Sync*Specification`). It was **not** compiled or run here
> because this environment has no Java toolchain. If an API detail has drifted,
> the [MCP Java SDK docs](https://modelcontextprotocol.info/docs/sdk/java/mcp-server/)
> and the [2.0 migration guide](https://github.com/modelcontextprotocol/java-sdk/blob/main/MIGRATION-2.0.md)
> are the source of truth.

## Layout

```text
java-sdk/
├── pom.xml
└── src
    ├── main/java/dev/mcplearn/orders/
    │   ├── OrderBook.java      # MCP-free domain (unit-testable)
    │   ├── OrdersServer.java   # McpSyncServer over stdio (tools/resource/prompt)
    │   └── OrdersClient.java   # McpSyncClient demo
    └── test/java/dev/mcplearn/orders/
        ├── OrderBookTest.java      # unit tests
        └── OrdersServerTest.java   # handler-level + capability tests
```

## Build, run, test

```bash
mvn -q package                      # compiles, runs tests, builds the jar

# Server over stdio (for MCP Inspector or any stdio client):
java -jar target/orders-java-1.0.0.jar

# Client demo (spawns the jar as a subprocess):
java -cp target/orders-java-1.0.0.jar dev.mcplearn.orders.OrdersClient
```

`mvn test` runs JUnit: domain unit tests, tool-handler tests (call the
`SyncToolSpecification.callHandler` directly, no transport — the pattern the
SDK docs use), and a capability advertisement check.

## API notes (2.0.0, verified against source)

- Server: `McpServer.sync(transportProvider).serverInfo(name, version)
  .capabilities(ServerCapabilities.builder()...).build()`; register via
  `server.addTool/addResource/addPrompt` with `McpServerFeatures.Sync*Specification.builder()`.
- Tool schemas are plain JSON Schema maps: `Tool.builder(name, Map.of(...))`.
- Transports: `StdioServerTransportProvider` (server) and
  `StdioClientTransport(ServerParameters, McpJsonMapper)` (client); the default
  Jackson mapper comes from `McpJsonDefaults.getMapper()`.
- The sync client (`McpSyncClient`) blocks per call: `initialize()`, `listTools()`,
  `callTool(new CallToolRequest(name, args))`, `readResource(...)`,
  `getPrompt(...)`, and `closeGracefully()`.

See [docs/VERSIONS.md](../../docs/VERSIONS.md) for the pinned versions.
