"""Tests for the composed gateway: provider routing, namespacing, error routing."""
import pytest
from fastmcp.exceptions import ToolError

from composed_server import gateway, weather, calendar


@pytest.mark.asyncio
async def test_merged_catalog():
    tools = await gateway.list_tools()
    names = {t.name for t in tools}
    # Local + namespaced mount + unmounted mount
    assert {"ping", "wx_forecast", "events"} <= names


@pytest.mark.asyncio
async def test_namespaced_tool_routes_to_mounted_server():
    result = await gateway.call_tool("wx_forecast", {"city": "paris"})
    assert "paris" in result.content[0].text
    assert not result.is_error


@pytest.mark.asyncio
async def test_unprefixed_tool_still_resolves():
    result = await gateway.call_tool("events", {"day": "monday"})
    assert "standup" in result.content[0].text


@pytest.mark.asyncio
async def test_unknown_tool_raises():
    with pytest.raises(Exception):
        await gateway.call_tool("no_such_tool")


@pytest.mark.asyncio
async def test_semantic_failure_raises_tool_error_server_side():
    # Server-side API: a ToolError is raised for a semantic failure...
    with pytest.raises(ToolError):
        await gateway.call_tool("events", {"day": "sunday"})


@pytest.mark.asyncio
async def test_semantic_failure_is_error_on_the_wire():
    # ...but on the wire it is an isError result, not a JSON-RPC error.
    from fastmcp import Client

    async with Client("composed_server.py") as client:
        result = await client.call_tool("events", {"day": "sunday"}, raise_on_error=False)
        assert result.is_error
        assert "No events found" in result.content[0].text


@pytest.mark.asyncio
async def test_sub_servers_still_work_independently():
    # The mounted servers remain usable as servers in their own right.
    tools = await weather.list_tools()
    assert "forecast" in {t.name for t in tools}
    tools = await calendar.list_tools()
    assert "events" in {t.name for t in tools}
