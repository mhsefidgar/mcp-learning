"""Discover and call the composed gateway from composed_server.py.

    python client_routing.py
"""
import asyncio

from fastmcp import Client


async def main() -> None:
    async with Client("composed_server.py") as client:
        tools = await client.list_tools()
        print("catalog:", [t.name for t in tools])
        # Expect: ['ping', 'events', 'wx_forecast']  (order may vary)

        print("ping ->", (await client.call_tool("ping")).content[0].text)
        print("events(monday) ->", (await client.call_tool("events", {"day": "monday"})).content[0].text)
        print("wx_forecast(paris) ->", (await client.call_tool("wx_forecast", {"city": "paris"})).content[0].text)

        # Error routing: unknown tool -> error; semantic failure -> isError result
        try:
            await client.call_tool("no_such_tool")
        except Exception as exc:
            print("unknown tool ->", type(exc).__name__, str(exc)[:80])

        # raise_on_error=False returns the isError result instead of raising.
        bad = await client.call_tool("events", {"day": "sunday"}, raise_on_error=False)
        print("events(sunday) is_error =", bad.is_error, "| text =", bad.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
