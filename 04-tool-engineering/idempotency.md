# Idempotency

> **General engineering pattern.** Idempotency is not an MCP protocol feature. It is
> a property you design into tools (especially write tools) so they can be retried
> safely.

## What is it?

An operation is **idempotent** if repeating it produces the same effect as doing it
once. `GET` is idempotent; `DELETE /order/5` is idempotent (deleting a missing order
is a no-op); `POST /orders` (create) is **not** — twice means two orders. The
standard technique is an **idempotency key**: the caller sends a unique key, and the
server remembers "I already processed key X" and returns the original result instead
of doing the work again.

## Why does MCP need it?

Because **retries are unavoidable** ([retries.md](retries.md)) and retries of write
tools are dangerous. The worst MCP failure mode is invisible duplication: the network
dropped the response, the client retried, and now there are two orders / two emails /
two deployments. Idempotency is what makes retry *safe*. It also protects models,
which sometimes call the same tool twice for the same logical step.

## How does it work?

1. **The tool accepts an `idempotency_key`** argument (a caller-generated UUID).
2. **On first call**: run the operation, store `{key → result}` (in a durable store
   with a TTL).
3. **On repeat call with the same key**: return the stored result *without* running
   the operation.
4. **Key scope**: the key must be unique per *logical operation* — same key for the
   same request, new key for a new request. (Keys are often scoped per client/user
   to avoid collisions.)

```
call 1: create_order(idempotency_key="k-1", ...)  → creates order, stores k-1 → result
call 2: create_order(idempotency_key="k-1", ...)  → returns stored result, no new order
call 3: create_order(idempotency_key="k-2", ...)  → creates a NEW order
```

## Mental model

An idempotency key is a **receipt stub**: the server files one copy under the stub
number and never issues a duplicate. Call the same number again, and you get the same
receipt. This is exactly how payment providers (Stripe's `Idempotency-Key`) prevent
double charges.

## MCP-specific behavior

- **Nothing protocol-level.** Idempotency keys are ordinary tool arguments (or
  metadata in `_meta`).
- **Conventions help**: name it consistently (`idempotency_key`), document it
  ("pass the same key to retry safely"), and mark the tool
  `idempotentHint: true` only when it *is* safe without keys
  ([annotations.md](annotations.md)).
- **Read tools are naturally idempotent** — the problem is write tools.

## Example

```python
import uuid
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

mcp = FastMCP("orders")

# Durable store: a real implementation uses the database (same tx as the order).
_idempotency_store: dict[str, dict] = {}

@mcp.tool
def create_order(
    customer: str,
    amount: float,
    idempotency_key: str | None = None,
) -> dict:
    """Create an order. Pass the same idempotency_key to retry safely.

    Returns {order_id, status, created} — or the original result on retry.
    """
    key = idempotency_key or uuid.uuid4().hex
    if key in _idempotency_store:
        return _idempotency_store[key]  # already processed — return stored result

    order = db.create(customer=customer, amount=amount)
    result = {"order_id": order.id, "status": "created"}
    # Store the result in the SAME transaction as the insert, in production.
    _idempotency_store[key] = result
    return result
```

Production notes: the idempotency check-and-insert must be **atomic**
(unique constraint on the key, or a transaction), the store needs a **TTL** (keys
expire after, say, 24h), and duplicate-key races must resolve to one winner.

## Industry-standard pattern

Idempotency keys are the standard for payment/order APIs (Stripe, PayPal, AWS).
Their rules: keys are client-generated and opaque, lookups are atomic, results are
cached with a TTL, and the key is scoped to the caller. Also common: `PUT` semantics
("set state to X" — naturally idempotent) as an alternative to keys.

## Common mistakes

- **Idempotency without atomicity** — two concurrent calls with the same key both
  pass the check and both insert. Use a unique constraint / transaction.
- **Keys stored without results** — retry can't return the original answer.
- **No TTL** — the store grows forever.
- **Global key namespace** — keys from different clients collide; scope per client.
- **Assuming the whole tool is idempotent because it accepts a key** — the key only
  helps if you actually store and check it.

## Testing

- **Replay tests**: same key twice → one side effect, same result
  ([15-testing/tool-testing.md](../15-testing/tool-testing.md)).
- **Concurrency tests**: two parallel calls, same key → one order.
- **TTL tests**: after expiry, a new call with the old key creates a new order.
- **Different-key tests**: distinct keys → distinct operations.
- **Failure tests**: the operation fails mid-way → a retry with the same key
  completes it without duplicates.

## Debugging

- Duplicate orders in production → check the idempotency store's atomicity and TTL,
  then whether the client actually passed the same key on retry.
- Retry returning a stale result → TTL too long or result cache not invalidated.

## Security considerations

- **Idempotency keys are not authentication** — they don't identify the caller; scope
  them per authenticated principal.
- **Keys can be guessed/abused** — random, unguessable keys (UUIDs), and don't leak
  other users' results via key lookup.
- **The idempotency store holds results** — protect it like any data store.

## Related concepts

- [retries.md](retries.md)
- [annotations.md](annotations.md)
- [08-reliability-resilience/README.md](../08-reliability-resilience/README.md)
- [14-security/authorization.md](../14-security/authorization.md)