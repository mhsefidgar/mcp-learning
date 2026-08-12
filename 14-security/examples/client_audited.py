"""Drive audited_server.py as two principals and observe the boundary.

    python client_audited.py
"""
import asyncio

from fastmcp import Client

ALICE = {"auth": "alice-token"}
ADMIN = {"auth": "admin-token"}


async def call(client, name, arguments=None, meta=None, label=""):
    try:
        result = await client.call_tool(name, arguments, meta=meta)
        print(f"{label or name}: OK   -> {result.content[0].text}")
        return result
    except Exception as exc:                      # denied / rejected
        print(f"{label or name}: DENIED -> {type(exc).__name__}: {exc}")
        return None


async def main():
    async with Client("audited_server.py") as client:
        print("== alice (read-only role) ==")
        await call(client, "read_customer", {"customer_id": 1}, ALICE, "alice read")
        await call(client, "delete_customer", {"customer_id": 2, "confirm": True},
                   ALICE, "alice delete")
        await call(client, "audit_log", {}, ALICE, "alice audit")

        print("\n== admin ==")
        await call(client, "delete_customer", {"customer_id": 2, "confirm": False},
                   ADMIN, "admin delete (no confirm)")
        await call(client, "delete_customer", {"customer_id": 2, "confirm": True},
                   ADMIN, "admin delete (confirmed)")        trail = await call(client, "audit_log", {"limit": 20}, ADMIN, "admin audit")
        if trail is not None:
            print("\nAudit trail (sensitive arguments are redacted as ***):")
            print(trail.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
