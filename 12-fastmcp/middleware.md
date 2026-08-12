# FastMCP Middleware

## What is it?

**Middleware** is a pipeline around the server's operations: every request flows
through each middleware before dispatch, and the response flows back through in
reverse ([03-routing-dispatch/11-middleware-routing.md](../03-routing-dispatch/11-middleware-routing.md)).

```
Request → Middleware A → Middleware B → Handler → Middleware B → Middleware A → Response
```

## Why it exists

Cross-cutting concerns — authentication, logging, rate limiting, timing, error
normalization — would otherwise be copy-pasted into every handler. Middleware gives
one place for: **before** dispatch (auth, rate limits, logging), **after** (timing,
response shaping), and **on error** (conversion to the right response).

## How it works (verified API)

```python
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext

class LoggingMiddleware(Middleware):
    async def on_message(self, context: MiddlewareContext, call_next):
        print(f"→ {context.method}")
        result = await call_next(context)
        print(f"← {context.method}")
        return result

mcp = FastMCP("MyServer")
mcp.add_middleware(LoggingMiddleware())
```

**Hooks**, general → specific: `on_message` (all traffic) → `on_request`/
`on_notification` → operation hooks (`on_call_tool`, `on_read_resource`,
`on_get_prompt`, `on_list_*`). The `call_next(context)` call continues the chain;
not calling it stops processing.

**Ordering**: first added runs first in, last out. Place error handling early so it
catches everything; logging late so it records real execution:

```python
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware

mcp.add_middleware(ErrorHandlingMiddleware())  # 1st in, last out
mcp.add_middleware(RateLimitingMiddleware())
mcp.add_middleware(LoggingMiddleware())        # sees the real execution
```

**State**: `ctx.set_state(key, value)` passes values from middleware to handlers
within a request ([context.md](context.md)); it does **not** cross mount
boundaries by default ([composition.md](composition.md)).

## MCP-specific behavior

- **FastMCP-specific, not protocol** — MCP defines methods, not pipelines.
- **Composition**: parent middleware runs for all requests (including mounted
  servers' handlers); a mounted server's own middleware runs only for its handlers.

## Common mistakes

- **Ordering mistakes** — auth after logging leaks details; error handling last
  misses earlier failures.
- **Blocking sync I/O in async middleware.**
- **Forgetting `call_next` can raise** — wrap it when converting errors.

## Testing

- **Pipeline-order tests**: middleware runs in the expected order (side-effect
  log).
- **Rejection tests**: a middleware that doesn't call `call_next` stops the chain.
- **State tests**: `set_state` in middleware is visible to the handler, scoped to
  the request.

## Related

- [03-routing-dispatch/11-middleware-routing.md](../03-routing-dispatch/11-middleware-routing.md)
- [context.md](context.md)
- [09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md)
- [08-reliability-resilience/rate-limiting.md](../08-reliability-resilience/rate-limiting.md)