# 11 — Middleware Routing

> **Framework concept.** Middleware is a **FastMCP** feature (2.9+). It is not part of
> the MCP protocol. The TypeScript and Java SDKs solve the same problems with
> interceptors/hooks or by wrapping at the transport layer — see the "alternatives"
> section below.

## What is it?

**Middleware** is a pipeline of interceptors around the server's operations. Every
inbound request flows through the middleware chain *before* dispatch, and every
response flows back through it *after* the handler:

```
Request → Middleware A → Middleware B → Handler → Middleware B → Middleware A → Response
```

Middleware is where cross-cutting concerns live — authentication, logging, rate
limiting, timing, error normalization — so individual tools don't each re-implement
them.

## Why does MCP need it? (Why FastMCP needs it)

Without a middleware layer, cross-cutting concerns get copy-pasted into every handler
(or, worse, forgotten in one). Middleware routing gives a single place where:

- **before dispatch**: validate auth, check rate limits, log the request
- **during dispatch**: nothing (handlers do the work) — but middleware can wrap it
- **after dispatch**: transform the response, record timing, normalize errors
- **on error**: catch and convert exceptions into the right response shape
  ([10-error-routing.md](10-error-routing.md))

## How does it work?

1. **Registration**: middleware is added to the server (`mcp.add_middleware(...)`).
2. **Ordering**: the first added middleware runs first on the way in and last on the
   way out (onion model).
3. **Hooks**: FastMCP provides hooks at increasing specificity:

| Hook | Scope | Typical use |
|------|-------|-------------|
| `on_message` | every message (requests + notifications) | logging, metrics |
| `on_request` / `on_notification` | requests vs. notifications | auth (requests), event recording |
| `on_call_tool`, `on_read_resource`, `on_get_prompt`, `on_list_*` | specific operations | tool-specific logic, response shaping |

4. **`call_next`** continues the chain; not calling it stops processing (a middleware
   can reject a request by raising).
5. **State**: `ctx.set_state(key, value)` passes values from middleware to handlers
   within a request ([12-fastmcp/context.md](../12-fastmcp/context.md)).

## Mental model

Middleware is an **onion**: each layer sees the request, may act, passes it inward,
and sees the response on the way out. It's the same model as Express/Koa/FastAPI
middleware — which is exactly where the pattern came from.

## MCP-specific behavior

- **MCP itself has no middleware concept.** The protocol defines methods, not
  pipelines. Middleware is FastMCP's way to build them.
- **Middleware sees protocol messages** (`context.method`, `context.message`), so it
  can gate by method, by tool name, by session — but the *typed* operation hooks
  (`on_call_tool`) get the parsed message and return typed results.
- **Composition**: parent middleware runs for all requests including mounted servers'
  handlers; a mounted server's own middleware runs only for its handlers
  ([12-fastmcp/composition.md](../12-fastmcp/composition.md)).
- In the **2026-07-28 stateless spec**, FastMCP's middleware still applies — it wraps
  the request/response cycle, which now happens per round-trip
  ([13-versioning/protocol-versions.md](../13-versioning/protocol-versions.md)).

## Example

Logging + timing middleware (from the FastMCP docs):

```python
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
import time

class LoggingMiddleware(Middleware):
    async def on_message(self, context: MiddlewareContext, call_next):
        print(f"→ {context.method}")
        start = time.perf_counter()
        result = await call_next(context)
        print(f"← {context.method} ({time.perf_counter() - start:.3f}s)")
        return result

mcp = FastMCP("MyServer")
mcp.add_middleware(LoggingMiddleware())
```

Ordering matters:

```python
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
from fastmcp.server.middleware.logging import LoggingMiddleware

mcp = FastMCP("MyServer")
mcp.add_middleware(ErrorHandlingMiddleware())  # 1st in, last out — catches everything
mcp.add_middleware(RateLimitingMiddleware())   # 2nd
mcp.add_middleware(LoggingMiddleware())        # 3rd — logs the real execution
```

**Alternatives in other SDKs:**

- **TypeScript SDK**: no middleware class; wrap handlers, or use
  `server.setRequestHandler` with a decorated function; transport-level interceptors
  for HTTP. Common pattern: a `withLogging(fn)` wrapper around registered handlers.
- **Java SDK**: wrap tool handlers, use Servlet filters / Spring interceptors at the
  transport, or Reactor operators (`doOnNext`, `timeout`) on the async API.

## Industry-standard pattern

Middleware/interceptor pipelines are the standard answer to cross-cutting concerns:
**Express/Koa**, **FastAPI**, **ASP.NET**, **gRPC interceptors**, **Spring
HandlerInterceptors**. The MCP-specific reminder: this is *framework* machinery —
don't document it as protocol behavior.

## Common mistakes

- **Ordering mistakes** — auth middleware placed after logging leaks request details;
  error handling placed last misses earlier failures.
- **Blocking in async middleware** (sync I/O in an async chain).
- **Forgetting that `call_next` may raise** — wrap it if you must convert errors.
- **Performing authorization in middleware but not catalog filtering** — see
  [08-authorization-routing.md](08-authorization-routing.md).

## Testing

- **Pipeline tests**: assert middleware runs in order (side-effect log), and that a
  rejecting middleware stops the chain.
- **Hook tests**: `on_call_tool` sees tool name + arguments; `on_read_resource` sees
  the URI.
- **Error-path tests**: handler raises → error middleware converts it → client gets
  the defined response.
- **State tests**: `set_state` in middleware is visible to the handler and scoped to
  the request.

## Debugging

- A middleware swallowing or reshaping responses is a classic "works without
  middleware, breaks with it" bug — bisect by removing middleware one at a time.
- Check hook coverage: `on_message` fires for *all* traffic; `on_call_tool` only for
  tool calls. If you expected the latter but wrote the former, filtering is off.

## Security considerations

- **Middleware is a security boundary**: auth, rate limiting, and input inspection
  belong here, *before* handlers ([08-authorization-routing.md](08-authorization-routing.md)).
- **Logging middleware must redact** secrets/PII from messages
  ([09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md)).
- Middleware runs for *every* request — a slow middleware is a DoS amplifier; keep it
  fast.

## Related concepts

- [01-request-dispatch.md](01-request-dispatch.md)
- [08-authorization-routing.md](08-authorization-routing.md)
- [10-error-routing.md](10-error-routing.md)
- [12-fastmcp/middleware.md](../12-fastmcp/middleware.md)
- [12-fastmcp/context.md](../12-fastmcp/context.md)