"""A hand-rolled MCP server over stdio, in pure Python (no SDK).

Educational simplification — not production-ready.
This exists so you can SEE the protocol: every message it sends and receives is
raw JSON-RPC, newline-delimited over stdin/stdout. Real servers use the SDKs
(implementations/python-fastmcp) which handle all of this for you.

Supports the session-based protocol (2025-11-25):
  initialize -> notifications/initialized -> tools/list -> tools/call

Run it, then talk to it like a client would:

    $ python raw_handshake.py

In another terminal, feed it a scripted client session:

    $ printf '%s\n' \
      '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"probe","version":"0.1"}}}' \
      '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
      '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
      '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"add","arguments":{"a":2,"b":3}}}' \
      | python raw_handshake.py

You will see the raw JSON-RPC responses printed to stderr as they are sent.
"""

from __future__ import annotations

import json
import sys

# --- JSON-RPC helpers -------------------------------------------------------

def make_response(request_id, result=None, error=None) -> dict:
    """A JSON-RPC response echoes the request id and carries result XOR error."""
    msg = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        msg["error"] = error
    else:
        msg["result"] = result
    return msg


def send(message: dict) -> None:
    """Write one JSON-RPC message to stdout, newline-delimited (the stdio framing)."""
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()
    # Stderr is the server's voice for humans; stdout is reserved for the protocol.
    print(f"→ {json.dumps(message)}", file=sys.stderr)


# --- The one tool -----------------------------------------------------------

def tool_add(arguments: dict) -> dict:
    a, b = arguments.get("a", 0), arguments.get("b", 0)
    if not isinstance(a, int) or not isinstance(b, int):
        raise ValueError("a and b must be integers")
    # An MCP tool result wraps content blocks; isError flags semantic failure.
    return {"content": [{"type": "text", "text": str(a + b)}], "isError": False}


# --- Dispatch: the heart of request routing ---------------------------------

def dispatch(method: str, params: dict, request_id) -> dict:
    """Route a request method to the matching operation.

    This is the entire protocol layer of the server. SDKs generate exactly this
    dispatch table from your registered tools/resources/prompts. See
    ../03-routing-dispatch/01-request-dispatch.md for the full picture.
    """
    if method == "initialize":
        # Version negotiation: echo the client's version when we support it.
        client_version = params.get("protocolVersion", "unknown")
        if client_version != "2025-11-25":
            # A real server would negotiate; this toy only knows one version.
            print(f"⚠  client offered {client_version}; we only speak 2025-11-25",
                  file=sys.stderr)
        return make_response(request_id, result={
            "protocolVersion": "2025-11-25",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "raw-handshake-demo", "version": "0.1.0"},
            "instructions": "A hand-rolled server. Try tools/call add.",
        })

    if method == "tools/list":
        # Discovery: the catalog of tools, with JSON Schema for arguments.
        return make_response(request_id, result={
            "tools": [
                {
                    "name": "add",
                    "description": "Add two integers.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "integer", "description": "First addend"},
                            "b": {"type": "integer", "description": "Second addend"},
                        },
                        "required": ["a", "b"],
                    },
                }
            ]
        })

    if method == "tools/call":
        name = params.get("name")
        if name != "add":
            # Unknown tool -> JSON-RPC method-not-found style error.
            return make_response(
                request_id,
                error={"code": -32602, "message": f"Unknown tool: {name}"},
            )
        try:
            result = tool_add(params.get("arguments", {}))
        except ValueError as exc:
            # Validation failure -> invalid-params error with a structured message.
            return make_response(
                request_id,
                error={"code": -32602, "message": "Invalid arguments", "data": str(exc)},
            )
        return make_response(request_id, result=result)

    # Anything else: unknown method.
    return make_response(
        request_id,
        error={"code": -32601, "message": f"Method not found: {method}"},
    )


# --- Main loop --------------------------------------------------------------

def main() -> None:
    print("raw_handshake server listening on stdin (newline-delimited JSON).",
          file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            # JSON-RPC parse error (-32700). No id -> no valid response id.
            send(make_response(None, error={"code": -32700, "message": f"Parse error: {exc}"}))
            continue

        if "id" not in message:
            # A notification: no id, no response ever.
            print(f"← notification {message.get('method')}", file=sys.stderr)
            continue

        response = dispatch(message["method"], message.get("params", {}), message["id"])
        send(response)


if __name__ == "__main__":
    main()
