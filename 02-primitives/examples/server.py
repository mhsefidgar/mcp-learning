"""A single FastMCP server exposing all three primitives: a tool, a resource
(+ template), and a prompt.

Run it over stdio:
    python server.py
Then discover and use it from client.py:
    python client.py
"""
from fastmcp import FastMCP

mcp = FastMCP("primitives-demo")

# --- Tool: an action ---------------------------------------------------------

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two integers. Use for any arithmetic addition."""
    return a + b


# --- Resource: data ----------------------------------------------------------

@mcp.resource("info://about")
def about() -> str:
    """Static resource describing this server."""
    return "A demo server exposing a tool, a resource, and a prompt."


@mcp.resource("math://square/{number}")
def square(number: int) -> str:
    """Dynamic resource: returns the square of a number from the URI."""
    return str(number * number)


# --- Prompt: reusable instruction ------------------------------------------------

@mcp.prompt
def explain_addition(a: int, b: int) -> str:
    """Explain how to add two numbers step by step."""
    return (
        f"Explain to a beginner how to add {a} and {b}: "
        "show the carry, then the result."
    )


if __name__ == "__main__":
    mcp.run()  # stdio
