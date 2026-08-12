"""Run the orders server over Streamable HTTP.

    python examples/run_http.py
    # protocol endpoint: http://localhost:8000/mcp
"""
import uvicorn

from orders import create_app

if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app.streamable_http_app(), host="127.0.0.1", port=8000)
