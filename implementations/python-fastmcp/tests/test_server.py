"""Integration tests: a real client session against the orders server
(15-testing/integration-testing.md)."""
import json

from fastmcp import Client

from orders import create_app


async def test_capabilities_and_tools():
    app = create_app()
    async with Client(app) as client:       # in-memory transport, real protocol
        caps = client.initialize_result.capabilities
        assert {"tools", "resources", "prompts"} <= set(caps.model_fields_set)
        tools = {t.name for t in await client.list_tools()}
        assert {"create_order", "get_order", "ship_order"} <= tools


async def test_end_to_end_via_client():
    app = create_app()

    async with Client(app) as client:
        tools = {t.name for t in await client.list_tools()}
        assert {"create_order", "get_order", "ship_order"} <= tools

        created = await client.call_tool("create_order",
                                         {"item": "widget", "quantity": 3})
        order = json.loads(created.content[0].text)
        assert order["total"] == 30

        state = await client.call_tool("get_order", {"order_id": order["order_id"]})
        assert json.loads(state.content[0].text)["status"] == "created"

        shipped = await client.call_tool("ship_order", {"order_id": order["order_id"]})
        assert json.loads(shipped.content[0].text)["status"] == "shipped"


async def test_validation_errors_are_clean():
    app = create_app()
    async with Client(app) as client:
        result = await client.call_tool("create_order", {"item": "x", "quantity": 0},
                                        raise_on_error=False)
        assert result.is_error
        assert "quantity" in result.content[0].text


async def test_resource_and_prompt():
    app = create_app()
    async with Client(app) as client:
        await client.call_tool("create_order", {"item": "w", "quantity": 1})
        contents = await client.read_resource("orders://ord-1")
        assert "ord-1" in contents[0].text

        prompt = await client.get_prompt("order_summary", {"order_id": "ord-1"})
        assert "ord-1" in prompt.messages[0].content.text
