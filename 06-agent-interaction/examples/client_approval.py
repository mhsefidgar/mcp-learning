"""Drive the approval server, answering elicitations like a user would.

    python client_approval.py
"""
import asyncio

from fastmcp import Client


def make_user(decision: bool):
    """Simulate a user clicking 'approve' or 'decline' on the prompt."""

    async def on_elicit(message, response_type, params, context):
        print(f"[USER PROMPT] {message}")
        if decision:
            print("[USER] approving")
            return True
        print("[USER] declining")
        from fastmcp.client.elicitation import ElicitResult
        return ElicitResult(action="decline", content="I changed my mind")

    return on_elicit


async def run(decision: bool) -> None:
    # The elicitation_handler makes the client advertise the capability.
    async with Client("approval_server.py", elicitation_handler=make_user(decision)) as client:
        result = await client.call_tool("delete_project", {"project_id": "p-9"})
        print("delete_project ->", result.content[0].text)
        audit = await client.call_tool("audit_log", {"limit": 5})
        print("audit ->", audit.content[0].text)


async def main() -> None:
    print("=== Approve path ===")
    await run(decision=True)
    print("\n=== Reject path ===")
    await run(decision=False)


if __name__ == "__main__":
    asyncio.run(main())
