"""A scripted agent driving the order-processing server end to end.

Demonstrates the full loop from 16-end-to-end/implementation.md:
- connect + discover capabilities, tools, schemas
- execute a multi-step workflow, validating each output before chaining it
- ask for human approval (elicitation) before the sensitive step
- retry flaky failures with backoff
- report progress from long-running work
- log every step, measure latency + success rate
- graceful shutdown (the async with block)

    python agent.py
"""
import asyncio
import json
import time
from dataclasses import dataclass, field

from fastmcp import Client


@dataclass
class WorkflowReport:
    """The observable contract of one workflow run."""
    steps: list = field(default_factory=list)
    latencies_ms: dict = field(default_factory=dict)
    retries: int = 0
    status: str = "unknown"
    reason: str | None = None
    success_rate: float = 1.0

    def to_dict(self) -> dict:
        return {
            "steps": self.steps,
            "latencies_ms": self.latencies_ms,
            "retries": self.retries,
            "status": self.status,
            "reason": self.reason,
            "success_rate": round(self.success_rate, 3),
        }


def _validate_order_output(payload: dict) -> dict:
    """Output validation: never chain garbage into the next step.
    (14-security/untrusted-output.md — tool output is data, check it.)
    The one thing every step's output must carry is the order id — that is
    what the next step chains on. Per-step fields (status, total, ...) are
    checked by the steps that use them."""
    if not isinstance(payload, dict) or "order_id" not in payload:
        raise ValueError(f"unexpected tool output shape: {payload!r}")
    return payload


async def _call(client, name, arguments, report, step, attempts=3):
    """Call a tool with retry/backoff, recording latency + retries."""
    base = 0.05
    for attempt in range(1, attempts + 1):
        start = time.perf_counter()
        try:
            result = await client.call_tool(name, arguments)
            report.latencies_ms[step] = round((time.perf_counter() - start) * 1000, 1)
            report.steps.append(step)
            return result
        except Exception as exc:                     # TimeoutError, ToolError, ...
            if attempt == attempts:
                raise
            report.retries += 1
            print(f"  [agent] {step} failed ({exc}); retry {attempt}/{attempts - 1}")
            await asyncio.sleep(base * 2 ** (attempt - 1))   # exponential backoff
    raise RuntimeError("unreachable")


async def run_order_workflow(client, item: str, quantity: int,
                             user_decision: bool = True) -> WorkflowReport:
    """The multi-step workflow: create -> verify -> ship (with approval)."""
    report = WorkflowReport()
    log = []

    def log_step(msg):
        log.append(msg)
        print(f"  [agent] {msg}")

    # 1. Discover capabilities and inspect the schema before calling.
    tools = {t.name: t for t in await client.list_tools()}
    required_tools = {"create_order", "get_order", "ship_order", "flaky_lookup"}
    if not required_tools <= set(tools):
        raise RuntimeError(f"server missing tools: {required_tools - set(tools)}")
    log_step(f"discovered {len(tools)} tools; schemas present for all")

    # 2. Create the order (validate the output before proceeding).
    create = await _call(client, "create_order",
                         {"item": item, "quantity": quantity}, report, "create_order")
    order = _validate_order_output(json.loads(create.content[0].text))
    log_step(f"created {order['order_id']} total={order['total']}")

    # 3. Verify via a flaky lookup (retries with backoff).
    lookup = await _call(client, "flaky_lookup", {"order_id": order["order_id"]},
                         report, "flaky_lookup")
    state = _validate_order_output(json.loads(lookup.content[0].text))
    log_step(f"verified {state['order_id']} status={state['status']}")

    # 4. The sensitive step: ship (server elicits the human; our handler answers).
    ship = await _call(client, "ship_order",
                       {"order_id": order["order_id"], "confirm": True},
                       report, "ship_order")
    final = _validate_order_output(json.loads(ship.content[0].text))
    report.status = final["status"]
    if final.get("reason"):
        report.reason = final["reason"]
        log_step(f"ship {final['order_id']} -> {final['status']} ({final['reason']})")
    else:
        log_step(f"ship {final['order_id']} -> {final['status']}")

    # 5. Read the resource template for the final state (an extra capability).
    contents = await client.read_resource(f"orders://{order['order_id']}")
    log_step(f"resource read: {contents[0].text}")

    succeeded = report.status == "shipped"
    report.success_rate = 1.0 if succeeded else 0.0
    return report


def make_user(decision: bool):
    """The human at the approval step. (In a real agent this renders a UI.)"""
    async def on_elicit(message, response_type, params, context):
        print(f"  [USER PROMPT] {message}")
        if decision:
            print("  [USER] approving")
            return True
        from fastmcp.client.elicitation import ElicitResult
        print("  [USER] declining")
        return ElicitResult(action="decline", content="I changed my mind")
    return on_elicit


async def main() -> None:
    print("=== Workflow: approved ===")
    async with Client("agent_server.py", elicitation_handler=make_user(True)) as client:
        report = await run_order_workflow(client, "widget", 2, user_decision=True)
        print("report:", json.dumps(report.to_dict(), indent=2))

    print("\n=== Workflow: declined ===")
    async with Client("agent_server.py", elicitation_handler=make_user(False)) as client:
        report = await run_order_workflow(client, "gadget", 1, user_decision=False)
        print("report:", json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
