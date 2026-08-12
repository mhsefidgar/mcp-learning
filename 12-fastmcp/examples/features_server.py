"""FastMCP architecture in action: middleware (logging + timing) and Context
(progress + resource access). Demonstrates 12-fastmcp/middleware.md and
12-fastmcp/context.md.

    python features_server.py
    python client_features.py
    pytest test_features.py
"""
import asyncio
import time

from fastmcp import FastMCP
from fastmcp.dependencies import CurrentContext
from fastmcp.server.context import Context
from fastmcp.server.middleware import Middleware, MiddlewareContext

mcp = FastMCP("features")

_events: list[tuple[str, str]] = []   # (hook, method) audit trail


# --- Middleware: logging + timing ---------------------------------------------

class TimingMiddleware(Middleware):
    async def on_message(self, context: MiddlewareContext, call_next):
        start = time.perf_counter()
        try:
            result = await call_next(context)
            outcome = "ok"
        except Exception:
            outcome = "error"
            raise
        finally:
            _events.append(("timing", f"{context.method}:{outcome}:{time.perf_counter()-start:.3f}s"))
        return result


class AuditMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        _events.append(("audit", f"call_tool:{context.message.name}"))
        return await call_next(context)


mcp.add_middleware(TimingMiddleware())   # 1st in, last out
mcp.add_middleware(AuditMiddleware())    # 2nd


# --- Context: progress + resource access ----------------------------------------

@mcp.resource("info://config")
def config() -> str:
    """A config resource the tools read via context."""
    return "region=us-east-1"


@mcp.tool
async def analyze(rows: int, ctx: Context = CurrentContext()) -> str:
    """Analyze rows, reporting progress and reading the config resource."""
    await ctx.info(f"analyzing {rows} rows")
    cfg = await ctx.read_resource("info://config")
    for i in range(rows):
        await ctx.report_progress(i + 1, rows)
        await asyncio.sleep(0.01)
    return f"analyzed {rows} rows; config={cfg.contents[0].content}"


@mcp.tool
def audit_trail() -> list[tuple[str, str]]:
    """The middleware audit trail (test-only)."""
    return list(_events)


if __name__ == "__main__":
    mcp.run()
