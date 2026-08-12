# Secret Management

## What is it?

**Secret management** is how you store, distribute, rotate, and revoke credentials
(API keys, database passwords, tokens, certificates) so they never live in code,
config files, logs, or memory longer than necessary.

## Why does MCP need it?

MCP servers are credential *holders*: they need to call databases, cloud APIs,
payment systems, and other tools — often with powerful credentials. Those same
servers receive untrusted input and run model-triggered code
([untrusted-output.md](untrusted-output.md)). Secrets are the crown jewels; every
MCP system is one leaked key away from full compromise.

## How it works

1. **Centralize**: secrets live in a secret manager (vault, cloud secret store,
   env-injected at deploy) — never in source control, schemas, or docs.
2. **Inject**: the runtime receives secrets via environment variables or mounted
   files at startup, not via the MCP protocol.
3. **Use with least privilege**: each server gets only the credentials it needs
   ([least-privilege.md](least-privilege.md)).
4. **Rotate**: automated, short-lived credentials (tokens expire; keys rotate on
   schedule or on suspicion).
5. **Revoke fast**: the ability to kill a credential in seconds limits blast
   radius.

## MCP-specific behavior

- **Never send secrets as tool arguments or resource content** — they would be
  logged, audited, and exposed to the model
  ([sensitive-data-redaction.md](sensitive-data-redaction.md)). The server holds
  its own credentials; the client does not pass them in.
- **Client-side secrets**: the agent's own API keys (LLM provider) are client
  concerns; MCP does not carry them.
- **Elicitation** should never be used to harvest secrets ("please provide your
  API key") — that is a prompt-injection pattern to reject.

## Industry-standard pattern

- Secret manager + inject-at-deploy (env vars / files), **never in the repo**.
- Short-lived, automatically rotated credentials where the platform allows.
- Scoped credentials per service (a DB password for the MCP server is not the
  admin password).
- Secrets scanned for in CI (secret scanners on every commit).
- Incident playbook: suspected leak → rotate immediately → audit who used the key
  ([auditability.md](auditability.md)).

## Common mistakes

- Hard-coding keys in examples, `.env` files committed, or tool *schemas* (a
  default value containing a key!).
- Passing secrets through tool arguments (logged + exposed to the model).
- One all-powerful key for everything.
- Long-lived keys with no rotation.

## Testing

- **Scan tests**: CI scans the repo for known secret patterns; example files must
  pass.
- **No-leak tests**: run the server, exercise tools, assert logs/audit contain no
  credential values ([sensitive-data-redaction.md](sensitive-data-redaction.md)).
- **Rotation tests**: rotating a key invalidates old ones and the server keeps
  working with the new one.
- **Revocation tests**: revoking a token stops access promptly.

## Security considerations

Secrets are the highest-value target in the system. Combine centralized storage,
least privilege, rotation, and redaction so that a single leak is *contained*:
the leaked key is scoped, short-lived, and quickly revoked.

## Related

- [sensitive-data-redaction.md](sensitive-data-redaction.md)
- [least-privilege.md](least-privilege.md)
- [auditability.md](auditability.md)
- [11-communication-transport/tls.md](../11-communication-transport/tls.md)
