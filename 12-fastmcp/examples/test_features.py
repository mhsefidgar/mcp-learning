"""Tests for features_server.py: middleware ordering + context progress."""
import asyncio
import json

import pytest
from fastmcp import Client

from features_server import mcp, _events


@pytest.mark.asyncio
async def test_middleware_runs_in_order():
    _events.clear()
    await mcp.call_tool("audit_trail")
    # TimingMiddleware wraps everything; AuditMiddleware wraps the tool call.
    kinds = [e[0] for e in _events]
    assert "timing" in kinds and "audit" in kinds


@pytest.mark.asyncio
async def test_context_progress_and_resource_access():
    seen = []

    async def on_progress(progress, total, _token):
        seen.append((progress, total))

    async with Client("features_server.py") as client:
        result = await client.call_tool(
            "analyze", {"rows": 3}, progress_handler=on_progress)
    assert seen == [(1.0, 3.0), (2.0, 3.0), (3.0, 3.0)]
    assert "config=region=us-east-1" in result.content[0].text


@pytest.mark.asyncio
async def test_audit_middleware_records_tool_calls():
    # The audit trail lives in the server process; read it through the tool.
    async with Client("features_server.py") as client:
        await client.call_tool("audit_trail")
        trail = await client.call_tool("audit_trail")
    events = json.loads(trail.content[0].text)
    assert any(e[0] == "audit" and "audit_trail" in e[1] for e in events)
