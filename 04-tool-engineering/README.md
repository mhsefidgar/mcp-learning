# 04 — Tool Engineering

**What this section teaches.** How to engineer tools that models can use reliably:
schemas and validation, structured output, annotations, errors, pagination/filtering/
sorting, retries, idempotency, cancellation, progress, long-running operations,
timeouts, and failure handling. This is the difference between "a tool that works in a
demo" and "a tool that works in production."

**Prerequisites.** [01-fundamentals](../01-fundamentals/README.md),
[02-primitives/tools.md](../02-primitives/tools.md),
[03-routing-dispatch](../03-routing-dispatch/README.md).

**Recommended reading order:**

1. [schemas.md](schemas.md) — the contract (start here; everything builds on it)
2. [validation.md](validation.md) · [structured-output.md](structured-output.md)
3. [annotations.md](annotations.md) · [errors.md](errors.md)
4. [pagination.md](pagination.md) · [filtering.md](filtering.md) · [sorting.md](sorting.md) — data-heavy tools
5. [batching.md](batching.md) — efficiency
6. [retries.md](retries.md) · [idempotency.md](idempotency.md) — correctness under failure
7. [cancellation.md](cancellation.md) · [progress.md](progress.md) · [long-running-operations.md](long-running-operations.md) — long work
8. [timeouts.md](timeouts.md) · [failure-handling.md](failure-handling.md) — bounding failure

**A crucial distinction for this section:** most of these topics are **general
engineering patterns** applied to tools, not MCP protocol features.

| Topic | MCP protocol feature? | Reality |
|-------|----------------------|---------|
| progress | ✅ protocol (`_meta.progressToken`, `notifications/progress`) | see [progress.md](progress.md) |
| cancellation | ✅ protocol (`notifications/cancelled`) | see [cancellation.md](cancellation.md) |
| pagination | ✅ protocol (`cursor` on list methods) | see [pagination.md](pagination.md) |
| retries | ❌ general pattern | see [retries.md](retries.md) |
| timeouts | ❌ general pattern | see [timeouts.md](timeouts.md) |
| idempotency | ❌ general pattern | see [idempotency.md](idempotency.md) |
| batching | ❌ general pattern (MCP has no batch method) | see [batching.md](batching.md) |
| schemas/validation | ✅ schema in protocol; validation is yours | see [schemas.md](schemas.md) |

**Relevant examples:** `examples/` — a progressively hardened "orders" server.
**Relevant implementations:** `implementations/python-fastmcp`, `repository/go/resilience`,
`repository/rust/resilience`.

**Exercises.**

1. **Harden a tool**: take a simple tool and add (a) a precise JSON Schema,
   (b) validation with useful errors, (c) structured output, (d) `readOnlyHint`/
   `destructiveHint` annotations. *Acceptance:* Inspector shows the schema; bad input
   yields `-32602` with a specific message; the result is structured.
2. **Add pagination** to a `list_*` tool. *Acceptance:* `cursor` round-trips, pages
   don't overlap or skip, and the last page terminates.
3. **Make a tool idempotent** (e.g. `create_order` with an `idempotency_key`).
   *Acceptance:* calling twice with the same key returns the same result and creates
   one order.
4. **Simulate a timeout** (a tool that sleeps) and fix it with a timeout + a clean
   error. *Acceptance:* the client sees a timeout error in bounded time, and the
   server's in-flight work is cancelled.
5. **Failure injection**: make a tool fail 50% of the time and add retries with
   exponential backoff + jitter. *Acceptance:* the client eventually succeeds, and the
   number of attempts is visible in logs (see
   [08-reliability-resilience/failure-injection.md](../08-reliability-resilience/failure-injection.md)).

**Common mistakes in this section**

- Schema sloppiness (see [schemas.md](schemas.md)) — the #1 cause of model-side tool
  misuse.
- Confusing protocol-level errors with semantic failures ([errors.md](errors.md)).
- Retrying non-idempotent operations ([retries.md](retries.md), [idempotency.md](idempotency.md)).
- Ignoring cancellation and then leaking work ([cancellation.md](cancellation.md)).
- No timeouts — a hung tool hangs the whole agent ([timeouts.md](timeouts.md)).