# Clean Architecture and Clean Code, applied

## The rings, mapped to files

| Clean Architecture ring | Here |
|---|---|
| Entities | `model`: plain values, no I/O |
| Use cases | `core` (the policy) plus `service` (the application service) |
| Interface adapters | `ports/` (owned by the core) and `adapters/` (which implement them) |
| Frameworks and drivers | the CLI, HTTP, the filesystem, subprocesses, databases: reached only through adapters |

**The dependency rule:** source-code dependencies point inward only. An architecture test
enforces it, so it doesn't rest on review.

## SOLID

- **SRP:** a file has one reason to change, which is why there is one port or adapter per file.
- **OCP:** a new backend is a new adapter file plus a registry entry. The core is not edited.
- **LSP:** every adapter and every fake passes the same contract test.
- **ISP:** ports stay small, usually one to three methods. Split a port whose callers use
  disjoint subsets of it.
- **DIP:** the core declares the interface it needs, and adapters conform to it. The core never
  conforms to a library's shape.

## Composition root

Production wiring lives in one place (`service`), as defaults. Callers override an adapter only
where the choice is genuinely theirs (a `--no-health` flag, a per-call base config). Tests pass
fakes for any port.

## Humble adapters

Adapters translate and do I/O; they hold no policy. When an adapter starts making decisions,
those decisions move into the core where fakes can test them. The exception is code the repo's
rules pin to a module: there, the adapter delegates and the code stays put.

## Clean Code rules

| Rule | In practice |
|---|---|
| Names reveal role and technology | port `HealthProbe`; adapter `HttpHealthProbe`; fake `FakeHealth`; each file named after its type, in the language's casing convention |
| The contract lives in one place | the port's doc comment: inputs, outputs, failure meanings, blocking, threading |
| Expected failures are values | `Health.down("paused")`, not an exception; exceptions are for misconfiguration and bugs |
| No flag arguments | `health=None` / `dry_run=True` becomes a choice of adapter (`AssumeHealthy`, `DryRunStore`) |
| Small functions | the core reads as policy; parsing, I/O and formatting live elsewhere |
| Readable moves | move code verbatim first, rename in a separate step |
| Boy Scout, separately | a found bug or cleanup is flagged or committed on its own, never hidden in the move |
| Comments say why | doc comments state contracts and reasons, not what the next line does |
