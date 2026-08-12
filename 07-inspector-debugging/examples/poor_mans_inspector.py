"""A programmatic "poor man's MCP Inspector": dump what a server declares and call
things by hand — useful when you can't open the browser-based Inspector.

    python poor_mans_inspector.py ../../04-tool-engineering/examples/hardened_server.py
"""
import asyncio
import sys

from fastmcp import Client


async def inspect(server_path: str) -> None:
    async with Client(server_path) as client:
        init = client.initialize_result  # the server's initialize response
        print("=" * 60)
        print(f"SERVER: {server_path}")
        print(f"  negotiated protocol: {init.protocolVersion if init else 'n/a'}")
        print(f"  serverInfo: {init.serverInfo if init else 'n/a'}")
        print(f"  server capabilities: {init.capabilities if init else 'n/a'}")

        print("\n-- TOOLS (name / description) --")
        tools = await client.list_tools()
        for t in tools:
            print(f"  {t.name}: {t.description}")

        print("\n-- TOOL SCHEMA (first tool) --")
        if tools:
            first = tools[0]
            print(f"  {first.name}: {first.inputSchema}")

        print("\n-- RESOURCES --")
        try:
            resources = await client.list_resources()
            for r in resources:
                print(f"  {r.uri}")
        except Exception as exc:
            print(f"  (no resources: {exc})")

        print("\n-- RESOURCE TEMPLATES --")
        try:
            templates = await client.list_resource_templates()
            for t in templates:
                print(f"  {t.uriTemplate}")
        except Exception as exc:
            print(f"  (no templates: {exc})")

        print("\n-- PROMPTS --")
        try:
            prompts = await client.list_prompts()
            for p in prompts:
                print(f"  {p.name}: {p.description}")
        except Exception as exc:
            print(f"  (no prompts: {exc})")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "../../03-routing-dispatch/examples/composed_server.py"
    asyncio.run(inspect(target))
