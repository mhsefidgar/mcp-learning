"""A fault-injecting server: tools that fail, sleep, or hang on command — the
seam for testing retries, timeouts, and circuit breakers.

    python faulty_server.py
    python retry_client.py            # exercises the retry stack against it
    pytest test_resilience.py
"""
import asyncio
import random

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("faulty")

_fail_next_n = 0
_mode = "flaky"  # "flaky" | "dead" | "ok"


@mcp.tool
def set_mode(mode: str) -> str:
    """TEST-ONLY. Modes: ok (always succeeds), flaky (fails 50%),
    dead (fails every call)."""
    global _mode
    if mode not in {"ok", "flaky", "dead"}:
        raise ToolError(f"unknown mode {mode!r}")
    _mode = mode
    return f"mode set to {mode}"


@mcp.tool
def fail_next(n: int) -> str:
    """TEST-ONLY. Make the next n calls to flaky_tool fail."""
    global _fail_next_n
    _fail_next_n = n
    return f"armed for {n} failures"


@mcp.tool
async def flaky_tool(payload: str) -> str:
    """Fails according to the current mode. Use with set_mode/fail_next."""
    global _fail_next_n
    if _fail_next_n > 0:
        _fail_next_n -= 1
        raise ToolError("injected failure: upstream returned 503")
    if _mode == "dead":
        raise ToolError("injected failure: server is down")
    if _mode == "flaky" and random.random() < 0.5:
        raise ToolError("injected failure: flaky upstream error")
    return f"ok: {payload}"


@mcp.tool
async def slow_tool(seconds: float) -> str:
    """TEST-ONLY. Sleeps, for timeout/cancellation tests."""
    await asyncio.sleep(seconds)
    return f"slept {seconds}s"


if __name__ == "__main__":
    mcp.run()
