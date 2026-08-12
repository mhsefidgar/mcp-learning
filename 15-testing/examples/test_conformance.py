"""Conformance tests for tiny_server.py — two layers:

1. RAW WIRE tests: speak JSON-RPC 2.0 directly over stdio, asserting the exact
   framing and message shapes the protocol defines. No SDK on the client side,
   so SDK bugs on either end can't hide each other.
2. CLIENT contract tests: the same server through the FastMCP client, asserting
   capability advertisement, schema contract, and tool behavior.

    pytest test_conformance.py -q
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastmcp import Client

SERVER = str(Path(__file__).parent / "tiny_server.py")
PYTHON = sys.executable

# ---------------------------------------------------------------------------
# A raw JSON-RPC client over stdio. One line of JSON in, one line out.
# ---------------------------------------------------------------------------

class RawStdioClient:
    """Educational simplification: a single-request client that spawns a fresh
    server per exchange. Fine for conformance tests; not a real client."""

    def __init__(self):
        self.proc = None
        self._id = 0

    def __enter__(self):
        self.proc = subprocess.Popen(
            [PYTHON, SERVER],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", bufsize=1,
        )
        return self

    def __exit__(self, *exc):
        if self.proc:
            self.proc.terminate()
            self.proc.wait(timeout=5)

    def send(self, method: str, params: dict | None = None) -> dict:
        self._id += 1
        request = {"jsonrpc": "2.0", "id": self._id, "method": method}
        if params is not None:
            request["params"] = params
        self.proc.stdin.write(json.dumps(request) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        return json.loads(line)


# ---------------------------------------------------------------------------
# 1. RAW WIRE conformance
# ---------------------------------------------------------------------------

def test_raw_initialize_handshake():
    with RawStdioClient() as c:
        response = c.send("initialize", {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "conformance", "version": "0.1"},
        })
        assert response["jsonrpc"] == "2.0"
        assert response["id"] == 1                       # echo of request id
        result = response["result"]
        assert result["protocolVersion"] == "2025-11-25"
        assert result["serverInfo"]["name"] == "tiny"
        assert "tools" in result["capabilities"]         # advertises tools


def test_raw_tools_list_schema_shape():
    with RawStdioClient() as c:
        c.send("initialize", {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "conformance", "version": "0.1"},
        })
        response = c.send("tools/list")
        tools = {t["name"]: t for t in response["result"]["tools"]}
        assert set(tools) == {"add", "divide"}
        schema = tools["add"]["inputSchema"]
        assert schema["type"] == "object"
        assert set(schema["required"]) == {"a", "b"}
        assert schema["properties"]["a"]["type"] == "integer"


def test_raw_tool_call_framing():
    with RawStdioClient() as c:
        c.send("initialize", {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "conformance", "version": "0.1"},
        })
        response = c.send("tools/call", {"name": "add", "arguments": {"a": 2, "b": 3}})
        result = response["result"]
        assert result["isError"] is False
        # FastMCP wraps the tool's return value under a `result` key.
        assert result["structuredContent"] == {"result": 5}


def test_raw_unknown_tool_is_clean_error():
    with RawStdioClient() as c:
        c.send("initialize", {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "conformance", "version": "0.1"},
        })
        response = c.send("tools/call", {"name": "nope", "arguments": {}})
        # FastMCP models an unknown tool as a tool-ERROR RESULT (isError: true),
        # not a JSON-RPC error object. Pin the actual behavior.
        assert response["result"]["isError"] is True
        assert "Unknown tool" in response["result"]["content"][0]["text"]


# ---------------------------------------------------------------------------
# 2. CLIENT-level contract tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_client_capabilities_and_tools():
    async with Client(SERVER) as client:
        caps = client.initialize_result.capabilities
        assert {"tools", "resources", "prompts"} <= set(caps.model_fields_set)

        tools = {t.name for t in await client.list_tools()}
        assert tools == {"add", "divide"}

        result = await client.call_tool("add", {"a": 2, "b": 3})
        assert result.content[0].text == "5"


@pytest.mark.asyncio
async def test_client_resource_and_prompt():
    async with Client(SERVER) as client:
        contents = await client.read_resource("info://version")
        assert contents[0].text == "tiny 1.0"

        prompt = await client.get_prompt("greet", {"name": "Ada"})
        assert prompt.messages[0].content.text == "Hello, Ada!"
