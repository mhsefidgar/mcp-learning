"""Tests for audited_server.py: authentication, per-tool permissions,
destructive-operation confirmation, redaction, and auditability.

    pytest test_security.py
"""
import json

import pytest
from fastmcp import Client

ALICE = {"auth": "alice-token"}
ADMIN = {"auth": "admin-token"}


async def call(client, name, arguments=None, meta=None):
    """Return (ok, result_or_error_text)."""
    try:
        result = await client.call_tool(name, arguments, meta=meta)
        return True, result.content[0].text
    except Exception as exc:
        return False, str(exc)


@pytest.mark.asyncio
async def test_unauthenticated_rejected():
    async with Client("audited_server.py") as client:
        ok, text = await call(client, "read_customer", {"customer_id": 1})
        assert not ok
        assert "unauthenticated" in text


@pytest.mark.asyncio
async def test_invalid_token_rejected():
    async with Client("audited_server.py") as client:
        ok, text = await call(client, "read_customer", {"customer_id": 1},
                              meta={"auth": "forged-token"})
        assert not ok
        assert "unauthenticated" in text


@pytest.mark.asyncio
async def test_alice_can_read_but_not_delete():
    async with Client("audited_server.py") as client:
        ok, text = await call(client, "read_customer", {"customer_id": 1}, ALICE)
        assert ok and "Ada" in text

        ok, text = await call(client, "delete_customer",
                              {"customer_id": 2, "confirm": True}, ALICE)
        assert not ok
        assert "not permitted" in text

        ok, text = await call(client, "audit_log", {}, ALICE)
        assert not ok
        assert "not permitted" in text


@pytest.mark.asyncio
async def test_destructive_tool_requires_confirmation():
    async with Client("audited_server.py") as client:
        ok, text = await call(client, "delete_customer",
                              {"customer_id": 2, "confirm": False}, ADMIN)
        assert ok                      # allowed, but refused by the tool itself
        assert "confirm=True required" in text

        ok, text = await call(client, "delete_customer",
                              {"customer_id": 2, "confirm": True}, ADMIN)
        assert ok and "deleted" in text


@pytest.mark.asyncio
async def test_audit_redacts_sensitive_arguments():
    async with Client("audited_server.py") as client:
        await call(client, "read_customer",
                   {"customer_id": 1, "api_key": "super-secret-value"}, ALICE)
        trail = json.loads((await client.call_tool("audit_log", {}, meta=ADMIN)
                            ).content[0].text)
    last = trail[-1]
    assert last["outcome"] == "ok"
    assert last["params"]["api_key"] == "***"
    assert "super-secret-value" not in json.dumps(trail)


@pytest.mark.asyncio
async def test_audit_records_denied_attempts():
    async with Client("audited_server.py") as client:
        await call(client, "delete_customer", {"customer_id": 2, "confirm": True},
                   ALICE)
        trail = json.loads((await client.call_tool("audit_log", {}, meta=ADMIN)
                            ).content[0].text)
    last = trail[-1]
    assert last["outcome"] == "error"
    assert last["name"] == "delete_customer"
    assert last["principal"] == "alice"
