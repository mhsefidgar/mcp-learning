"""A client with the full retry stack — exponential backoff + jitter, a retry
budget, and a circuit breaker — exercised against faulty_server.py.

    python retry_client.py
"""
import asyncio
import random
import time

from fastmcp import Client
from fastmcp.exceptions import ToolError

RETRYABLE = (ToolError, TimeoutError, ConnectionError)


# --- Exponential backoff with full jitter --------------------------------------

def backoff_delay(attempt: int, base: float = 0.1, cap: float = 2.0) -> float:
    """Full jitter: uniform random in [0, min(cap, base * 2^attempt)]."""
    return random.uniform(0, min(cap, base * (2 ** attempt)))


# --- Circuit breaker --------------------------------------------------------------

class CircuitBreaker:
    def __init__(self, threshold: int = 3, cooldown_s: float = 2.0):
        self.threshold = threshold
        self.cooldown = cooldown_s
        self.failures = 0
        self.state = "closed"   # closed | open | half-open
        self.opened_at = 0.0

    def allow(self) -> bool:
        if self.state == "open" and time.monotonic() - self.opened_at >= self.cooldown:
            self.state = "half-open"
        return self.state != "open"

    def record_success(self) -> None:
        self.failures = 0
        self.state = "closed"

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.state = "open"
            self.opened_at = time.monotonic()


# --- The retrying call (backoff + budget + breaker) --------------------------------

async def call_with_resilience(client, name: str, arguments: dict, breaker: CircuitBreaker,
                               max_attempts: int = 5, budget_s: float = 10.0) -> str:
    """Call a tool with backoff, a time budget, and a circuit breaker."""
    deadline = time.monotonic() + budget_s
    attempts = 0
    while True:
        if not breaker.allow():
            raise ToolError("circuit open: service temporarily unavailable, retry later")

        try:
            result = await client.call_tool(name, arguments)
            breaker.record_success()
            return result.content[0].text

        except RETRYABLE as exc:
            breaker.record_failure()
            attempts += 1
            if attempts >= max_attempts or time.monotonic() >= deadline:
                raise ToolError(f"gave up after {attempts} attempts: {exc}")
            delay = min(backoff_delay(attempts), max(0.0, deadline - time.monotonic()))
            print(f"  attempt {attempts} failed ({exc}); retrying in {delay:.2f}s")
            await asyncio.sleep(delay)


async def main() -> None:
    breaker = CircuitBreaker()
    async with Client("faulty_server.py") as client:
        await client.call_tool("set_mode", {"mode": "flaky"})

        print("1) flaky server, 50% failures -> retries should succeed:")
        print("  ", await call_with_resilience(client, "flaky_tool", {"payload": "x"}, breaker))

        await client.call_tool("set_mode", {"mode": "dead"})
        print("\n2) dead server -> circuit breaker trips after 3 failures:")
        try:
            await call_with_resilience(client, "flaky_tool", {"payload": "x"}, breaker)
        except ToolError as exc:
            print("  ", exc)

        await client.call_tool("set_mode", {"mode": "ok"})
        await asyncio.sleep(2.5)  # cooldown
        print("\n3) server back, breaker half-open -> recovers:")
        print("  ", await call_with_resilience(client, "flaky_tool", {"payload": "y"}, breaker))


if __name__ == "__main__":
    asyncio.run(main())
