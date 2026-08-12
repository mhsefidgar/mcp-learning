"""Run the orders server over stdio (for MCP Inspector or any stdio client).

    python examples/run_stdio.py
"""
from orders import create_app

if __name__ == "__main__":
    create_app().run()
