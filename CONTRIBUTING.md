# Contributing

Thanks for helping make this the best MCP learning resource possible.

## What belongs where

| Change | Where |
|--------|-------|
| A concept explanation | `NN-<section>/<concept>.md` |
| A small runnable example for a concept | `NN-<section>/examples/` |
| A full, tested server/client project | `implementations/<lang>/` |
| A lower-level / experimental implementation | `repository/<lang>/` |
| Diagrams, JSON schemas, shared test data | `shared/` |
| The end-to-end system | `capstone/` |

## Doc conventions

Every concept doc follows the standard structure (see any existing doc):

What is it? → Why does MCP need it? → How does it work? → Mental model →
MCP-specific behavior → Example (FastMCP / TypeScript / Java where supported) →
Industry-standard pattern → Common mistakes → Testing → Debugging →
Security considerations → Related concepts.

**Hard rules:**

1. **Never invent MCP methods, capabilities, SDK classes, decorators, imports,
   transports, or configuration options.** If you are not sure, check the official
   spec or SDK docs first and record the version in `docs/VERSIONS.md`.
2. **Keep the three-layer distinction.** MCP protocol behavior ≠ SDK behavior ≠
   general engineering patterns. Never claim a general pattern (circuit breakers,
   caching, rate limiting) is an MCP feature.
3. **Mark educational simplifications** explicitly:
   `Educational simplification — not production-ready.`
4. **Label code blocks with a language.** No unlabeled fences.
5. **No fake APIs, no `# implementation omitted`.** If you can't show real code, say
   why, or don't include the section.
6. **Cross-link** to related docs using relative links.

## Code conventions

- Python: FastMCP 3.x, type hints everywhere, pytest tests, `asyncio` where async.
- TypeScript: official SDK 1.x, `async/await`, vitest tests.
- Java: MCP Java SDK 2.0.x, modern Java, JUnit 5, Maven.
- Go: standard library first, `context.Context`, idiomatic testing.
- Rust: `tokio`/`serde` where needed, `cargo test`.

## Before you submit

1. Run the relevant test suite (see root `README.md` "How to run tests").
2. Update `docs/VERSIONS.md` if you changed or added a dependency.
3. Update the section `README.md` if you added a doc or example.
4. Verify cross-links with a quick grep for `](` targets that exist.

## Reviewing

Be kind and specific. The two most common review findings:

- API invented or wrong for the recorded version → fix the code or the version note.
- MCP feature / general pattern confusion → fix the attribution.

## License

By contributing you agree your contributions are licensed under the same MIT license
as the repository (see `LICENSE`).
