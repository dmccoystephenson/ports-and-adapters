---
name: ports-and-adapters
description: Refactor a project in any language, or one subsystem of it, into a pure core plus ports and adapters, with one file per port and one file per adapter, without changing behaviour. Use when the user asks to decouple code from its I/O, make a backend swappable, introduce hexagonal / clean architecture, add seams for testing, or invokes /ports-and-adapters <path-or-subsystem>.
---

# /ports-and-adapters

Turn tangled code (policy mixed with files, network, processes, clocks, logging and locks) into:

- a **core**: plain domain values (`model`) and pure policy (`core`), with no I/O;
- **ports**: small interfaces the core owns, **one file per port**;
- **adapters**: implementations of those ports, **one file per adapter**;
- a **composition root** (`service`) that wires the production adapters as defaults.

The refactor is **behaviour-preserving**. A layered safety net proves it, and the owner
approves the port map before any code moves.

The skill is **language-agnostic**. The layers, rules and gates are the same in every language;
only the idioms change. In this file, *interface* means the language's abstraction mechanism (a
Python `Protocol`, a TypeScript or Java or C# or Go `interface`, a Rust `trait`, a C++ abstract
class), and *index file* means its package entry point (`__init__.py`, `index.ts`,
`package-info`, `mod.rs`, a header). See `references/layouts.md` for each language's layout,
idioms and architecture-test recipe.

Argument: a path or subsystem name (`/ports-and-adapters src/billing`). With none, ask which
subsystem; never refactor a whole repository in one pass.

## Rules that apply throughout

1. **No behaviour change.** If you find a bug or want to tighten something, list it under
   "Flagged changes" in the report and do it in a separate step the owner approves. Never fold it
   silently into the move.
2. **The repo's own rules win.** Read the repo's agent and contributor docs (`CLAUDE.md`,
   `AGENTS.md`, `CONTRIBUTING.md`, architecture docs) before touching anything. Code they pin to a
   module (safety checks, auth, permission logic) stays there. Its adapter only *delegates* to it.
3. **No speculative ports.** A seam becomes a port only for a real reason: a second implementation
   exists or is planned, a test needs a fake, or a rule requires the code to live elsewhere.
   Anything else stays inline.
4. **Dependencies point inward.** `model`, `core` and `ports` never import `adapters` or
   `service`. Adapters may import `model`, `ports` and `core`. An automated test enforces this.
5. **One concept per file.** Each port file holds exactly one interface. Each adapter file holds
   exactly one implementation. Registries (e.g. a map of kind name to adapter) live in the
   adapters' index file. Where the language forces a different unit (e.g. Go, where a package is a
   directory), keep the same rule: one port or adapter per file.
6. **No new dependencies.** Use the language's own interface mechanism. Don't add a DI framework
   unless the repo already uses one.
7. **Respect the repo's workflow.** Work on a branch or in a worktree, use the repo's own test
   runner and interpreter, and don't commit, push or open PRs unless the user asked.

## Process

Follow these steps in order. A **Gate** means stop and do not continue until it passes or the
owner answers.

### 1. Scope and read the rules
- Confirm the subsystem and its entry points (who calls it).
- Read the repo's rules (rule 2) and note anything that must not move.
- Make or confirm a branch or worktree.

### 2. Baseline and characterize
- Find the repo's real test command and toolchain version (CI config, `Makefile`, the build
  file: `package.json`, `pyproject.toml`, `pom.xml`, `build.gradle`, `go.mod`, `Cargo.toml`,
  `*.csproj`, `CMakeLists.txt`). Run the **full** suite and record the pass, skip and fail
  counts. A suite that fails to build or import because of the wrong toolchain is not a
  baseline.
- Where the subsystem's behaviour is weakly tested, write **characterization tests** first. They
  pin today's outputs (return values, explain or log text, error messages, written files), and
  they must pass on the *old* code.
- **Gate:** the suite is green and the counts are recorded.

See `references/safety-net.md`.

### 3. Find the seams
List every place the subsystem touches the outside world:

- files and directories
- network and HTTP
- subprocesses
- environment variables and config files
- clocks and sleeps
- randomness
- threads, locks and semaphores
- logging and printing
- other modules' internals
- anything the tests currently `patch` or `mock`

Each one is a candidate port.

### 4. Draw the port map
Fill in `references/port-map-template.md`: for each candidate, record its port name, the
question it answers, its methods, the current code, its adapters, and the **reason** it earns a
port (rule 3). Also list the seams you chose to leave inline, with why.

- Ports are named for their **role** (`HealthProbe`, `Clock`, `OrderStore`). Adapters are named
  **technology plus role** (`HttpHealthProbe`, `SystemClock`, `PostgresOrderStore`). Fakes are
  `Fake` plus role.
- Keep ports small, usually one to three methods. A port with many unrelated methods is two
  ports.
- Port signatures use domain types, not library types. Where an existing in-repo type really is
  the contract, use it and say so in the doc comment.
- **Gate:** show the map to the owner and wait for approval. Apply their edits before writing any
  code.

### 5. Extract the model
Move the plain value types into `model` (records, data classes, structs, value objects). Strip
infrastructure
detail out of them. Settings only one backend reads become an opaque `settings` mapping, which
only that backend's adapter validates and reads.

### 6. Write the ports, test-first
For each port, in its own file:
- the interface, with its **contract** in its doc comment: inputs, outputs, what each failure
  means, whether it may block, and its threading or async rules;
- a fake in the tests;
- a contract test that the fake passes. The production adapter will pass the same test.

Expected outcomes ("down", "not found", "paused") are **values** at the port
(`Health.down(reason)`). Exceptions are for misconfiguration and bugs.

### 7. Move code into adapters
One implementation per file. Move the existing code **nearly verbatim**, so the diff reads as a
move, and save renames for a separate step. Code that the repo's rules pin to a module stays
there, and its adapter only calls it. Put registries in the adapters' index file.

### 8. Point the core at the ports
Replace module-level callables, globals and patched functions with port parameters. Remove flag
arguments (`dry_run=True`, `health=None`) by choosing an adapter instead (e.g. `AssumeHealthy`).
The core must not import any adapter.

### 9. Add the composition root
Add `service` (a class, a factory function, or a constructor in the language's idiom) that
takes the config and builds the core with production
adapters as defaults. Callers construct it and override an adapter only where the choice is
genuinely theirs: a command-line flag, or a per-call value only the caller knows.

### 10. Rewire the callers
Move every caller (CLI, handlers, jobs, other modules) onto the service, then delete the old
module. Leave a re-export shim only if code outside the repository imports it, and say so in the
report.

### 11. Prove it
- **Parity:** run the old code (built from a backup or the base commit) and the new code side by
  side over a generated grid of inputs, comparing every output field. `scripts/parity.py` drives
  this for any language: you write a tiny driver for each side that reads a JSON case on stdin and
  prints a JSON result. The target is zero differences; anything else is a flagged change.
- **Architecture tests:** run `scripts/check_layers.py`, which works for any language. Then
  encode the same rule in the repo's own suite with the language's native tool (see
  `references/layouts.md`), so CI keeps enforcing it. It fails if an inner layer imports an outer
  one, or if a port or adapter file declares more than one top-level type.
- **Frozen assertions:** during the move, tests may change their imports and wiring, but not what
  they assert. Diff the old and new assertions. The test count may only go up.
- **Full suite:** run it with the same command as the baseline. The pass count must be at or above
  the baseline.
- Optionally, run mutation testing on the core (mutmut, Stryker, PIT) to show the tests would
  catch a change.
- **Gate:** every check above holds, or the failure is reported, not hidden.

### 12. Update the docs
- **Package overview:** the package's doc comment or README gets the diagram (callers → service →
  core → ports ← adapters), a port → adapters table, and a "how to add a new X" line, which should
  be one new file plus one registry entry.
- **Old names:** fix every doc that named the old module or symbols, including the repo's agent
  docs and any doc-sync checklists.

### 13. Report
- **Layout:** before and after, as file trees, plus the approved port map.
- **Numbers:** baseline vs final test counts, the parity result (cases compared, differences) and
  the architecture-test result.
- **Flagged changes:** every behaviour difference, with a recommendation to keep or split.
- **Not done:** anything left undone, and why.
- **Gate:** the owner decides about committing, and the skill doesn't commit on its own.

## When not to use it

- **Tiny tools with one backend and no tests:** in scripts like these, the indirection costs more
  than it buys.
- **When a framework is already the adapter layer** (e.g. a thin web controller): refactor the
  domain behind it instead.
- **When the real goal is a behaviour change:** do that before or after, never during.

## Files in this skill

- `references/port-map-template.md`: the table approved at step 4.
- `references/safety-net.md`: characterization tests, parity, frozen assertions, mutation
  testing.
- `references/layouts.md`: per-language layout, port, adapter and fake snippets, and the
  architecture-test recipe (Python, TypeScript/JavaScript, Java/Kotlin, C#, Go, Rust, C++).
- `references/clean-code-architecture.md`: how Clean Architecture, SOLID and Clean Code apply
  here.
- `references/example.md`: a worked example on an open-source CLI (written in Python; the steps
  are the same in any language).
- `scripts/check_layers.py`: a dependency-direction and one-type-per-file checker for any of the
  languages above. It needs Python 3.8+ to run, and only the standard library.
- `scripts/parity.py`: the old-vs-new parity runner, which drives drivers written in any
  language.
