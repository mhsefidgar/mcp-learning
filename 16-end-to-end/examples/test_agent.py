"""End-to-end tests for the agent-server loop (16-end-to-end/testing.md).

Covers: happy-path workflow, approval rejection, output validation failure,
retry/recovery, progress notifications, metrics, and graceful shutdown.

    pytest test_agent.py
"""
import json

import pytest
from fastmcp import Client

from agent import make_user, run_order_workflow, _validate_order_output


@pytest.mark.asyncio
async def test_happy_path_workflow():
    async with Client("agent_server.py", elicitation_handler=make_user(True)) as client:
        report = await run_order_workflow(client, "widget", 2)
    assert report.status == "shipped"
    assert report.steps == ["create_order", "flaky_lookup", "ship_order"]
    assert report.success_rate == 1.0
    assert report.latencies_ms["create_order"] >= 0


@pytest.mark.asyncio
async def test_rejected_approval_cancels_cleanly():
    async with Client("agent_server.py", elicitation_handler=make_user(False)) as client:
        report = await run_order_workflow(client, "gadget", 1)
    assert report.status == "cancelled"
    assert report.reason == "user declined"


@pytest.mark.asyncio
async def test_output_validation_rejects_garbage():
    with pytest.raises(ValueError):
        _validate_order_output({"not": "an order"})
    # the valid shape passes
    _validate_order_output({"order_id": "ord-1", "status": "created"})


@pytest.mark.asyncio
async def test_retries_are_bounded_and_reported():
    # flaky_lookup fails the first two attempts per order, then succeeds:
    # the retry path is exercised deterministically and stays bounded.
    async with Client("agent_server.py", elicitation_handler=make_user(True)) as client:
        report = await run_order_workflow(client, "widget", 1)
    assert report.status == "shipped"
    assert report.retries == 2            # exactly the injected failures
    assert report.steps.count("flaky_lookup") == 1   # counted once on success


@pytest.mark.asyncio
async def test_progress_notifications_arrive():
    seen = []

    async def on_progress(progress, total, _token):
        seen.append((progress, total))

    async with Client("agent_server.py",
                      elicitation_handler=make_user(True)) as client:
        created = await client.call_tool("create_order",
                                         {"item": "w", "quantity": 1})
        order_id = json.loads(created.content[0].text)["order_id"]
        await client.call_tool("ship_order",
                               {"order_id": order_id, "confirm": True},
                               progress_handler=on_progress)
    assert seen == [(1.0, 5.0), (2.0, 5.0), (3.0, 5.0), (4.0, 5.0), (5.0, 5.0)]


@pytest.mark.asyncio
async def test_graceful_shutdown_terminates_server():
    # Entering and exiting the async-with block must not hang; the subprocess
    # is cleaned up by the context manager (transport teardown).
    async with Client("agent_server.py") as client:
        await client.list_tools()
    # If we got here, teardown completed cleanly.


@pytest.mark.asyncio
async def test_server_rejects_bad_arguments():
    async with Client("agent_server.py") as client:
        result = await client.call_tool("create_order", {"item": "x", "quantity": 0},
                                        raise_on_error=False)
        assert result.is_error
        assert "quantity" in result.content[0].text
