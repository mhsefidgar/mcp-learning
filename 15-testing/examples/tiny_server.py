"""A tiny FastMCP server used as the test subject for the conformance and
contract tests in this folder.

    python tiny_server.py
    pytest test_conformance.py -q
"""
from fastmcp import FastMCP

mcp = FastMCP("tiny")


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


@mcp.tool
def divide(a: int, b: int) -> float:
    """Divide a by b. Raises a tool error when b is zero."""
    if b == 0:
        raise ValueError("division by zero")
    return a / b


@mcp.resource("info://version")
def version() -> str:
    """The server version string."""
    return "tiny 1.0"


@mcp.prompt()
def greet(name: str) -> str:
    """A greeting template."""
    return f"Hello, {name}!"


if __name__ == "__main__":
    mcp.run()
