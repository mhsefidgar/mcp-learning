"""Tests for the approval flow: accept/reject paths and validation-before-ask."""
import json

import pytest
from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult
from fastmcp.exceptions import ToolError

from approval_server import mcp, _audit


@pytest.mark.asyncio
async def test_unknown_project_errors_before_eliciting():
    # Validation happens BEFORE asking: unknown ids fail without a prompt.
    with pytest.raises(ToolError, match="does not exist"):
        await mcp.call_tool("delete_project", {"project_id": "nope"})


@pytest.mark.asyncio
async def test_approve_path_deletes_and_audits():
    _audit.clear()

    async def approve(message, response_type, params, context):
        return True  # returning the data directly == accept

    async with Client("approval_server.py", elicitation_handler=approve) as client:
        result = await client.call_tool("delete_project", {"project_id": "p-2"})
        audit = await client.call_tool("audit_log")
    assert json.loads(result.content[0].text) == {"project_id": "p-2", "status": "deleted"}
    assert json.loads(audit.content[0].text)[-1] == {
        "action": "delete_project", "project_id": "p-2", "decision": "approved"}


@pytest.mark.asyncio
async def test_reject_path_cancels_and_records_reason():
    _audit.clear()

    async def reject(message, response_type, params, context):
        # The client-side decline action; content carries the user's message.
        return ElicitResult(action="decline", content="I changed my mind")

    async with Client("approval_server.py", elicitation_handler=reject) as client:
        result = await client.call_tool("delete_project", {"project_id": "p-9"})
        audit = await client.call_tool("audit_log")
    assert json.loads(result.content[0].text) == {
        "project_id": "p-9", "status": "cancelled", "reason": "user declined"}
    assert json.loads(audit.content[0].text)[-1]["decision"] == "rejected"
