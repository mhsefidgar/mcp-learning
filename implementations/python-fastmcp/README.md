# Python / FastMCP reference implementation

A canonical FastMCP project: proper `pyproject.toml`, an installable package
(`orders`), a stdio server, an HTTP server, and a pytest suite that exercises
the server over a real client session.

This is the reference Python project for the whole repository — the section
examples use the same patterns in a lighter form.

## Layout

```text
python-fastmcp/
├── pyproject.toml          # package metadata + dev dependencies
├── src/orders/
│   ├── __init__.py         # create_app() — the FastMCP server
│   └── domain.py           # pure business logic (unit-testable)
├── examples/
│   ├── run_stdio.py        # run the server over stdio
│   └── run_http.py         # run the server over Streamable HTTP
└── tests/
    ├── test_domain.py      # unit tests (no MCP involved)
    └── test_server.py      # integration tests (real client sessions)
```

## Setup and run

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# stdio server (for MCP Inspector or any stdio client):
python examples/run_stdio.py

# Streamable HTTP server (default port 8000):
python examples/run_http.py
#   curl http://localhost:8000/mcp      # protocol endpoint

pytest -q
```

## Why this layout

- **`domain.py` is MCP-free** — the business logic is testable without any
  protocol machinery; `create_app()` is a thin adapter. This is the
  industry-standard separation for MCP servers
  ([12-fastmcp/providers.md](../../12-fastmcp/providers.md)).
- **The server is importable** (`from orders import create_app`), so tests and
  other tools can reuse it in-process.
- **Editable install** means `pytest` and the examples see the same code.

See [docs/VERSIONS.md](../../docs/VERSIONS.md) for the pinned versions.
