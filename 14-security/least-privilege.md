# Least Privilege

## What is it?

**Least privilege** is the principle that every component — a user, a client, a
tool, a server — gets exactly the permissions it needs to do its job, and nothing
more. It is a *principle* (a design rule), not a protocol feature or a library.

## Why does MCP need it?

An MCP server aggregates many capabilities behind one boundary. If every caller
gets full access to every tool, then a compromise anywhere (a stolen token, a
prompt-injected client, a buggy tool) escalates into a compromise everywhere.
Least privilege contains the blast radius: the database tool cannot delete, the
email tool cannot read files, and the client that only needs `read` never holds
`delete` credentials.

## How to apply it

1. **Per capability**: grant tools/resources/prompts individually, not "all".
2. **Per role**: map real job functions to tool sets
   ([tool-permissions.md](tool-permissions.md)).
3. **Per argument**: where meaningful, constrain arguments (read customer #42, not
   the whole table).
4. **Per transport**: stdio servers run with the *OS user's* privileges — run them
   under a dedicated, unprivileged account with no write access outside their data
   dir ([01-fundamentals/08-transports.md](../01-fundamentals/08-transports.md)).
5. **Per secret**: give the server only the credentials its tools need, never a
   super-user key ([secret-management.md](secret-management.md)).
6. **At the data layer**: the server's database account should lack
   `DROP TABLE` even if a tool *intends* to delete rows — defense in depth.

## MCP-specific behavior

- The protocol does not define permissions, roles, or scopes — you implement least
  privilege with your authorization layer (auth extensions give you OAuth scopes
  as one mechanism; see [oauth.md](oauth.md)).
- Capability advertisement works *with* least privilege: expose in `tools/list`
  only what the caller may actually use (transform-based filtering in FastMCP,
  [12-fastmcp/transforms.md](../12-fastmcp/transforms.md)).

## Industry-standard pattern

- **Role-based access control (RBAC)** with roles defined as tool sets.
- **Default deny**; grants are explicit and reviewed.
- **Periodic reviews**: permissions accumulate; audit and prune
  ([auditability.md](auditability.md)).
- **Scoped credentials** at every layer (OAuth scopes, cloud IAM roles, DB roles).

## Common mistakes

- Granting "all tools" to every caller for convenience.
- Using one powerful credential everywhere instead of scoped ones.
- Leaving permissions in place after a role changes.
- Running stdio servers as the admin/root user.

## Testing

- Verify each role can call exactly its tools — no more
  ([15-testing/security-testing.md](../15-testing/security-testing.md)).
- Verify the server's *own* credentials cannot exceed its job (try the DB delete
  with the server's account).
- Rotate a role's permissions and confirm behavior changes immediately.

## Security considerations

Least privilege is the single highest-leverage hardening move in an MCP system:
it turns every other defense's failure into a contained incident instead of total
compromise. Pair it with audit so you can *prove* what each principal could do.

## Related

- [tool-permissions.md](tool-permissions.md)
- [authorization.md](authorization.md)
- [secret-management.md](secret-management.md)
- [destructive-operations.md](destructive-operations.md)
- [auditability.md](auditability.md)
