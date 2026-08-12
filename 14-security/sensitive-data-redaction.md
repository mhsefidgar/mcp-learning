# Sensitive-Data Redaction

## What is it?

**Redaction** is removing or masking sensitive values (passwords, tokens, API
keys, PII) from anything that leaves the secure boundary: logs, audit records,
error messages, traces, metrics, and tool output that flows to the model.

## Why does MCP need it?

An MCP server's logs and audit trail record every call — arguments included
([auditability.md](auditability.md)). If a client (or an attacker who got a
token) passed a secret in an argument, or a tool returned PII, the *log* becomes
the leak. Redaction is what lets you keep the diagnostic value of logs without
keeping the sensitive data.

## How it works

1. **Know the sensitive shapes**: key names (`password`, `token`, `api_key`,
   `authorization`), value patterns (JWT, UUIDs, credit-card, email, phone).
2. **Redact at the source**: scrub *before* writing — never redact at query time
   (the raw data has already been written somewhere).
3. **Mask or drop**: replace with `***` (keep length/shape for debugging) or drop
   the field entirely.
4. **Apply everywhere**: logs, audit, error messages, OpenTelemetry attributes,
   metrics labels, tool output sent to the model (if the model does not need it).

## MCP-specific behavior

- MCP has no redaction feature — it is server (and client) engineering. But MCP's
  design makes it essential: tool *arguments* arrive as JSON and get logged by
  middleware, and tool *results* flow into the model's context.
- **Defaults in schemas**: a tool schema with a secret in a `default` is leaked to
  every client that calls `tools/list`
  ([04-tool-engineering/schemas.md](../04-tool-engineering/schemas.md)) — redact
  and never put secrets in defaults.

## Example (FastMCP middleware that redacts before logging)

```python
import re
from fastmcp.server.middleware import Middleware, MiddlewareContext

SENSITIVE_KEYS = {"password", "token", "api_key", "secret", "authorization"}
TOKEN_RE = re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+")  # JWT

def redact(obj):
    if isinstance(obj, dict):
        return {k: ("***" if k.lower() in SENSITIVE_KEYS else redact(v))
                for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    if isinstance(obj, str):
        return TOKEN_RE.sub("***", obj)
    return obj

class RedactingLogMiddleware(Middleware):
    async def on_request(self, context: MiddlewareContext, call_next):
        result = await call_next(context)
        self.log(context.message.method, redact(context.message.params))
        return result
```

## Industry-standard pattern

- **Structured logging with a redaction filter** in the pipeline
  ([09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md)).
- **Allowlist of logged keys** vs denylist: default to *not* logging unknown
  fields, allowlist what is safe.
- **Pattern-based scrubbers** for tokens/cards/PII, applied centrally.
- **OpenTelemetry attribute filtering** so traces don't carry secrets
  ([09-observability-telemetry/distributed-tracing.md](../09-observability-telemetry/distributed-tracing.md)).
- Test redaction with real-shaped data (unit + integration
  ([15-testing/security-testing.md](../15-testing/security-testing.md))).

## Common mistakes

- Redacting only log *text* but not structured fields (audit JSON, trace
  attributes).
- Redacting at display time only — the raw value already reached disk.
- Forgetting error messages: a stack trace can embed arguments.
- Key-based redaction only: a token in a field named `data` slips through — use
  pattern matching too.

## Testing

- Feed calls with secret-shaped values; assert logs, audit, and traces contain
  only redacted forms.
- Assert schemas contain no secrets (scan defaults).
- Assert error messages from failing tools contain no arguments.

## Security considerations

Redaction protects *secondary* exposure (logs, traces, model context) after a
secret or PII entered the system. It is not a substitute for not collecting
sensitive data in the first place — but combined with secret management
([secret-management.md](secret-management.md)) and audit
([auditability.md](auditability.md)), it closes the most common leak paths.

## Related

- [secret-management.md](secret-management.md)
- [auditability.md](auditability.md)
- [09-observability-telemetry/structured-logging.md](../09-observability-telemetry/structured-logging.md)
- [14-security/examples/audited_server.py](examples/audited_server.py)
