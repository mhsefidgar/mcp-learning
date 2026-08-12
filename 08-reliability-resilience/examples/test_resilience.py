"""Tests for the retry stack: backoff schedule, breaker states, recovery."""
import asyncio
import time

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from retry_client import CircuitBreaker, backoff_delay, call_with_resilience


def test_backoff_is_bounded_and_jittered():
    delays = [backoff_delay(i) for i in range(8)]
    assert all(0 <= d <= 2.0 for d in delays)          # capped at 2.0
    assert delays[0] < delays[3]                       # grows (in expectation)


def test_backoff_is_random():
    assert len({backoff_delay(2) for _ in range(50)}) > 1   # jitter, not fixed


def test_breaker_closed_to_open():
    b = CircuitBreaker(threshold=3, cooldown_s=60)
    assert b.allow() is True
    b.record_failure(); b.record_failure(); b.record_failure()
    assert b.state == "open"
    assert b.allow() is False                            # fail-fast


def test_breaker_recovers_after_cooldown():
    b = CircuitBreaker(threshold=2, cooldown_s=0.05)
    b.record_failure(); b.record_failure()
    assert b.allow() is False
    time.sleep(0.06)
    assert b.allow() is True                             # half-open trial
    b.record_success()
    assert b.state == "closed"


@pytest.mark.asyncio
async def test_flaky_server_survives_with_retries():
    breaker = CircuitBreaker(threshold=10)
    async with Client("faulty_server.py") as client:
        await client.call_tool("set_mode", {"mode": "flaky"})
        text = await call_with_resilience(client, "flaky_tool", {"payload": "ping"}, breaker)
    assert text.startswith("ok:")


@pytest.mark.asyncio
async def test_dead_server_trips_breaker_and_fails_fast():
    breaker = CircuitBreaker(threshold=3, cooldown_s=60)
    async with Client("faulty_server.py") as client:
        await client.call_tool("set_mode", {"mode": "dead"})
        with pytest.raises(ToolError):
            await call_with_resilience(client, "flaky_tool", {"payload": "x"}, breaker)
        # Next call fails immediately without even reaching the server.
        start = time.monotonic()
        with pytest.raises(ToolError, match="circuit open"):
            await call_with_resilience(client, "flaky_tool", {"payload": "x"}, breaker)
        assert time.monotonic() - start < 1.0            # fail-fast, no attempts


@pytest.mark.asyncio
async def test_recovery_after_server_restores():
    breaker = CircuitBreaker(threshold=3, cooldown_s=0.1)
    async with Client("faulty_server.py") as client:
        await client.call_tool("set_mode", {"mode": "dead"})
        with pytest.raises(ToolError):
            await call_with_resilience(client, "flaky_tool", {"payload": "x"}, breaker)

        await client.call_tool("set_mode", {"mode": "ok"})
        await asyncio.sleep(0.15)                        # let the breaker cool down
        text = await call_with_resilience(client, "flaky_tool", {"payload": "y"}, breaker)
    assert text.startswith("ok:")
