"""A FastMCP client that discovers and uses all three primitives from server.py.

    python client.py
"""
import asyncio

from fastmcp import Client


async def main() -> None:
    # FastMCP 3.x infers a stdio transport from a script path.
    async with Client("server.py") as client:
        # 1. Discover what the server exposes
        tools = await client.list_tools()
        resources = await client.list_resources()
        templates = await client.list_resource_templates()
        prompts = await client.list_prompts()

        print("TOOLS:", [t.name for t in tools])
        print("RESOURCES:", [r.uri for r in resources])
        print("TEMPLATES:", [t.uriTemplate for t in templates])
        print("PROMPTS:", [p.name for p in prompts])

        # 2. Call the tool
        result = await client.call_tool("add", {"a": 2, "b": 3})
        print("add(2, 3) ->", result)

        # 3. Read the static resource (client returns a list of content blocks)
        about = await client.read_resource("info://about")
        print("info://about ->", about[0].text)

        # 4. Read a template-resolved resource
        sq = await client.read_resource("math://square/9")
        print("math://square/9 ->", sq[0].text)

        # 5. Get the prompt (MCP prompt arguments are strings)
        prompt = await client.get_prompt("explain_addition", {"a": "5", "b": "7"})
        print("prompt messages ->", [m.content.text for m in prompt.messages])


if __name__ == "__main__":
    asyncio.run(main())
