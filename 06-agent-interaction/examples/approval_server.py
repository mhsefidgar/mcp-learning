"""Approval flow via elicitation: a tool that pauses for human confirmation.

    python approval_server.py          # run over stdio
    python client_approval.py          # drive it (answers the elicitation)
    pytest test_approval.py
"""
from fastmcp import FastMCP, Context
from fastmcp.dependencies import CurrentContext
from fastmcp.exceptions import ToolError

mcp = FastMCP("approval-demo")

_audit: list[dict] = []
# Toy store of existing projects: {id: {name, files, age_days}}
_projects = {
    "p-9": {"name": "Payments API", "files": 12, "age_days": 3},
    "p-2": {"name": "Old Monolith", "files": 340, "age_days": 800},
}


@mcp.tool
async def delete_project(project_id: str, ctx: Context = CurrentContext()) -> dict:
    """Delete a project. Requires explicit user approval."""
    project = _projects.get(project_id)
    if project is None:
        raise ToolError(f"Project {project_id} does not exist")  # fail BEFORE asking

    answer = await ctx.elicit(
        f"Delete '{project['name']}' ({project['files']} files, "
        f"{project['age_days']} days old)? This is irreversible.",
        response_type=bool,
    )

    # Accept -> {action: "accept", data: True}. Anything else -> declined/cancelled.
    if answer.action != "accept" or not getattr(answer, "data", None):
        _audit.append({"action": "delete_project", "project_id": project_id,
                       "decision": "rejected", "reason": "user declined"})
        return {"project_id": project_id, "status": "cancelled", "reason": "user declined"}

    # ... the destructive work would happen here ...
    _audit.append({"action": "delete_project", "project_id": project_id, "decision": "approved"})
    return {"project_id": project_id, "status": "deleted"}


@mcp.tool
def audit_log(limit: int = 20) -> list[dict]:
    """Recent approval decisions: {action, project_id, decision, reason?}."""
    return _audit[-limit:]


@mcp.tool
def safe_probe() -> str:
    """A harmless read-only tool that never requires approval."""
    return "all good"


if __name__ == "__main__":
    mcp.run()
