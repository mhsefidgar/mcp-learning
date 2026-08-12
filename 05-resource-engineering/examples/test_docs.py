"""Tests for docs_server.py: templates, validation, versioning, traversal."""
import pytest
from fastmcp.exceptions import ResourceError

from docs_server import mcp, _safe, DOCS_ROOT


@pytest.mark.asyncio
async def test_template_listed_and_resolves():
    templates = await mcp.list_resource_templates()
    assert "docs://{project}/{file}" in {t.uri_template for t in templates}

    (DOCS_ROOT / "getting-started").mkdir(exist_ok=True)
    (DOCS_ROOT / "getting-started" / "start.md").write_text("hello docs", encoding="utf-8")
    result = await mcp.read_resource("docs://getting-started/start.md")
    assert "hello docs" in result.contents[0].content


@pytest.mark.asyncio
async def test_unknown_file_fails_cleanly():
    with pytest.raises(ResourceError, match="not found"):
        await mcp.read_resource("docs://api/nope.md")


@pytest.mark.asyncio
async def test_traversal_rejected():
    # Whether the URI fails at match time (NotFoundError) or at the handler
    # (ResourceError), traversal must never resolve to a file outside the root.
    with pytest.raises(Exception):
        await mcp.read_resource("docs://api/../../etc/passwd")


@pytest.mark.asyncio
async def test_versioned_config():
    v1 = await mcp.read_resource("config://app/v1/settings")
    assert "light" in v1.contents[0].content
    latest = await mcp.read_resource("config://app/settings")
    assert '"version": "v2"' in latest.contents[0].content


@pytest.mark.asyncio
async def test_unknown_version_fails():
    with pytest.raises(ResourceError, match="Unknown config version"):
        await mcp.read_resource("config://app/v99/settings")


def test_safe_helper_rejects_traversal():
    with pytest.raises(ResourceError):
        _safe("getting-started", "../../etc/passwd")
