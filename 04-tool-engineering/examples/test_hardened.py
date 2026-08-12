"""Failure-table tests for hardened_server.py — one test per failure mode."""
import asyncio
import pytest
from fastmcp.exceptions import ToolError

from hardened_server import mcp, _orders, _idempotency


# --- Schema + validation -------------------------------------------------------

@pytest.mark.asyncio
async def test_schema_validation_rejects_bad_types():
    with pytest.raises(Exception):                      # -32602 Invalid params
        await mcp.call_tool("get_order", {"order_id": "not-an-int"})


@pytest.mark.asyncio
async def test_unknown_order_is_semantic_failure():
    with pytest.raises(ToolError, match="does not exist"):
        await mcp.call_tool("get_order", {"order_id": 9999})


# --- Structured output ----------------------------------------------------------

@pytest.mark.asyncio
async def test_structured_output_shape():
    # For dict returns, structured_content IS the returned dict.
    result = await mcp.call_tool("get_order", {"order_id": 1})
    assert set(result.structured_content.keys()) >= {"id", "customer", "amount", "status"}


# --- Idempotency ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_idempotency_key_prevents_duplicates():
    before = len(_orders)
    args = {"customer": "Umbrella", "amount": 10.0, "idempotency_key": "k-replay-1"}
    first = await mcp.call_tool("create_order", args)
    second = await mcp.call_tool("create_order", args)   # same key -> replay
    assert first.structured_content["id"] == second.structured_content["id"]
    assert len(_orders) == before + 1                     # only one new order


@pytest.mark.asyncio
async def test_distinct_keys_create_distinct_orders():
    before = len(_orders)
    await mcp.call_tool("create_order", {"customer": "A", "amount": 1.0, "idempotency_key": "k1"})
    await mcp.call_tool("create_order", {"customer": "A", "amount": 1.0, "idempotency_key": "k2"})
    assert len(_orders) == before + 2


# --- Progress -----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_progress_reported():
    # progress_handler is a client-side feature; drive the server over stdio.
    from fastmcp import Client

    seen = []

    # The progress callback receives (progress, total, progress_token).
    async def on_progress(progress, total, _token):
        seen.append((progress, total))

    async with Client("hardened_server.py") as client:
        await client.call_tool("render_report", {"rows": 3}, progress_handler=on_progress)
    assert seen == [(1.0, 3.0), (2.0, 3.0), (3.0, 3.0)]


# --- Timeout ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_timeout_fails_cleanly():
    with pytest.raises(ToolError, match="timed out"):
        await mcp.call_tool("slow_op", {"delay": 5.0})


@pytest.mark.asyncio
async def test_fast_operation_succeeds():
    result = await mcp.call_tool("slow_op", {"delay": 0.01})
    assert result.content[0].text == "done"
