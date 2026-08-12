# 11 — Communication & Transport Deep Dives

**What this section teaches.** The three foundations MCP runs on, in depth: the
**JSON-RPC** wire protocol, **HTTP** as the remote transport, and **TLS** for
confidentiality and integrity. These are *general standards* MCP builds on — this
section is where you go when a transport-level bug or a security requirement needs
more than the fundamentals section provides.

**Prerequisites.** [01-fundamentals/03-json-rpc.md](../01-fundamentals/03-json-rpc.md),
[01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md).

**Reading order:**

1. [json-rpc.md](json-rpc.md) — the wire format, spec-level details
2. [http.md](http.md) — how MCP rides on HTTP
3. [tls.md](tls.md) — encrypting the transport

**Protocol vs. engineering:** JSON-RPC, HTTP, and TLS are **external standards** MCP
uses — none of them are "MCP features." Understanding them is understanding the
environment MCP lives in.

**Exercises.**

1. **Frame a message**: take a JSON-RPC request and write it as raw bytes over
   stdio (newline-delimited) and as an HTTP POST (headers + body).
   *Acceptance:* both forms carry the same message.
2. **TLS inspection**: `openssl s_client -connect host:port` on a TLS-protected
   MCP endpoint. *Acceptance:* you can read the certificate chain and verify the
   hostname.
3. **HTTP status mapping**: list the HTTP status codes an MCP endpoint can return
   and what each means for the client ([http.md](http.md)).

**Common mistakes in this section**

- Treating transport behavior as MCP behavior (e.g. expecting MCP to define
  retries/timeouts — it doesn't; HTTP does).
- TLS "configured" but not verified (self-signed everywhere, no hostname checks).