"""Tests for the primitives-demo server, exercising discovery and invocation."""
import pytest

from server import mcp


@pytest.mark.asyncio
async def test_tool_discovery_and_call():
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    assert "add" in names

    result = await mcp.call_tool("add", {"a": 2, "b": 3})
    assert not result.is_error
    assert result.structured_content == {"result": 5}


@pytest.mark.asyncio
async def test_resource_discovery_and_read():
    resources = await mcp.list_resources()
    assert "info://about" in {str(r.uri) for r in resources}

    about = await mcp.read_resource("info://about")
    assert "demo server" in about.contents[0].content


@pytest.mark.asyncio
async def test_resource_template_resolution():
    templates = await mcp.list_resource_templates()
    assert "math://square/{number}" in {t.uri_template for t in templates}

    sq = await mcp.read_resource("math://square/9")
    assert sq.contents[0].content == "81"


@pytest.mark.asyncio
async def test_prompt_retrieval():
    prompts = await mcp.list_prompts()
    assert "explain_addition" in {p.name for p in prompts}

    # Note: MCP prompt arguments are strings; numbers travel as "5", not 5.
    prompt = await mcp.render_prompt("explain_addition", {"a": "5", "b": "7"})
    text = prompt.messages[0].content.text
    assert "5 and 7" in text
