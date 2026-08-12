"""A "docs" resource server: templates with validation, versioned config, and a
static resource. Demonstrates resource templates, static/dynamic resources, and
resource versioning.

    python docs_server.py
    python client_docs.py
    pytest test_docs.py
"""
import os
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.exceptions import ResourceError

mcp = FastMCP("docs-server")

DOCS_ROOT = Path(__file__).parent / "docs_content"
DOCS_ROOT.mkdir(exist_ok=True)
(DOCS_ROOT / "welcome.md").write_text("# Welcome\n\nRead me first.", encoding="utf-8")
(DOCS_ROOT / "guide.md").write_text("# Guide\n\nHow to use the system.", encoding="utf-8")


def _safe(project: str, file: str) -> Path:
    """Resolve (project, file) under DOCS_ROOT, rejecting path traversal."""
    if not project or not file or "/" in file or "\\" in file or file in {".", ".."}:
        raise ResourceError(f"Invalid path: {project}/{file}")
    if project not in {"getting-started", "api"}:
        raise ResourceError(f"Unknown project: {project!r}")
    return DOCS_ROOT / project / file


@mcp.resource("docs://{project}/{file}")
def doc_file(project: str, file: str) -> str:
    """Read a doc file from a project (getting-started or api)."""
    path = _safe(project, file)
    if not path.exists():
        raise ResourceError(f"docs://{project}/{file} not found")
    return path.read_text(encoding="utf-8")


_CONFIG = {"v1": '{"theme": "light", "region": "us-east-1"}',
           "v2": '{"theme": "dark", "region": "us-east-1", "locale": "en"}'}
LATEST = "v2"


@mcp.resource("config://app/{version}/settings")
def settings_version(version: str) -> str:
    """Settings for a specific version (v1 or v2)."""
    if version not in _CONFIG:
        raise ResourceError(f"Unknown config version {version!r}")
    return _CONFIG[version]


@mcp.resource("config://app/settings")
def settings_latest() -> str:
    """Latest settings with its version embedded."""
    return f'{{"version": "{LATEST}", "data": {_CONFIG[LATEST]}}}'


@mcp.resource("info://about")
def about() -> str:
    """Static resource: what this server exposes."""
    return "Docs + versioned config demo server."


if __name__ == "__main__":
    mcp.run()
