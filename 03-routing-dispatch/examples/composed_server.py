"""A composed MCP server: two domain servers mounted under namespaces, plus local
tools and error routing. Demonstrates provider routing (06), transform routing
(namespacing, 07), and error routing (10).

Inspect the resulting catalog with the FastMCP client or MCP Inspector:

    python composed_server.py            # run over stdio
    python client_routing.py             # discover + call through the gateway
"""
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

# --- Two independent domain servers ------------------------------------------

weather = FastMCP("weather")

@weather.tool
def forecast(city: str) -> str:
    """Weather forecast for a city."""
    return f"Sunny, 22 C in {city}."


calendar = FastMCP("calendar")

@calendar.tool
def events(day: str) -> list[str]:
    """Calendar events for a weekday name (e.g. 'monday')."""
    schedule = {"monday": ["standup", "design review"], "friday": ["retro"]}
    if day.lower() not in schedule:
        raise ToolError(f"No events found for {day!r}")  # semantic failure -> isError
    return schedule[day.lower()]


# --- The gateway server ------------------------------------------------------

gateway = FastMCP("workspace-gateway")

# Provider routing: mounted servers become FastMCPProvider sources.
gateway.mount(weather, namespace="wx")        # tools become wx_forecast
gateway.mount(calendar)                        # no namespace -> events

# Local capability: handled right here, not forwarded.
@gateway.tool
def ping() -> str:
    """Health probe for the gateway."""
    return "pong"


if __name__ == "__main__":
    gateway.run()
