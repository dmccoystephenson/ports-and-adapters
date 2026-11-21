# The safety net

A refactor is done only when every layer holds. Each layer catches something the one before it
can miss.

## 1. Baseline

- Run the **full** suite with the repo's own command and toolchain. Find them in CI config, a
  `Makefile` or the build file (`package.json`, `pyproject.toml`, `tox.ini`, `pom.xml`,
  `build.gradle`, `go.mod`, `Cargo.toml`, `*.csproj`, `CMakeLists.txt`).
- Record the pass, skip and fail counts.
- If the suite fails to build, import or collect, you probably have the wrong toolchain version
  (e.g. an old system Python, Node, JDK or Go). Fix that first: it is not a baseline.

## 2. Characterization tests (test-first, for a refactor)

TDD's cycle is red, green, refactor. For a refactor, the tests have to exist **before** the code
moves, then each move keeps them green.

Where the subsystem is weakly tested, pin what it does **today**:

- return values for representative inputs, including edge cases (empty input, the largest
  input, invalid input);
- human-facing text: explain output, log lines, error messages;
- side effects: files written, commands built (argv), requests made (URL, body).

Write them against the **old** code and confirm they pass there. They describe behaviour, not
structure, so they should survive the move with only import changes.

## 3. Parity harness

Unit tests sample behaviour; parity compares it across a grid. `scripts/parity.py` works the same
in any language:

1. **Keep the old code buildable.** Check out the base commit in a second worktree
   (`git worktree add ../old <base>`), or keep a backup copy of the old module.
2. **Write one tiny driver per side** in the project's language. Each one reads JSON Lines cases
   on stdin, calls the code, and prints one JSON result per line. If the code throws, print
   `{"raised": "<ErrorType>"}`: an exception is an output too. Normalize anything that legitimately
   differs, such as a field that moved into a settings map.
3. **Describe the grid** in `axes.json`: every input that matters, with values at and around each
   threshold, every override, each health or availability state, and invalid input. Then run
   `python3 scripts/parity.py grid axes.json > cases.jsonl`.
4. **Run both sides:** `python3 scripts/parity.py run --cases cases.jsonl --old "<old driver>"
   --new "<new driver>" [--old-cwd ../old]`.
5. **Get to zero differences.** Each difference is either a bug in the move (fix it) or a
   deliberate change (flag it).

A driver is a few lines. In TypeScript:

```ts
import * as readline from "node:readline";
import { decide } from "./src/billing";            // old: from the base worktree
for await (const line of readline.createInterface({ input: process.stdin })) {
  const c = JSON.parse(line);
  try { console.log(JSON.stringify(decide(c))); }
  catch (e) { console.log(JSON.stringify({ raised: (e as Error).name })); }
}
```

In Go, it's a `main` that runs `bufio.Scanner` over stdin with `json.Unmarshal` / `json.Marshal`.
In Java, it's a `main` using any JSON library the project already has.

A worked example compared 600 cases and found 0 differences.

## 4. Small green steps

Extract one seam at a time, and run the fast tests after each step. If a step goes red, undo it
and take a smaller one rather than debugging forward through several half-moves.

## 5. Test-first for each port

For each port:

1. Write the interface and its contract doc comment.
2. Write a fake and a contract test, and watch the test fail before the fake exists (red).
3. Make the fake pass (green).
4. Move the production adapter in, and run the **same** contract test against it.

One contract run against both stops a fake from drifting away from reality. That is the Liskov
substitution principle, enforced. A structural type check (e.g. Python's
`isinstance(x, SomeProtocol)` on a `runtime_checkable` Protocol) only checks that the method
names exist (the same goes for a TypeScript structural type or a Go interface), so behaviour
needs real assertions.

## 6. Architecture tests

These are automated checks that live in the repo's suite:

- inner layers (`model`, `core`, `ports`) never import `adapters` or `service`;
- each port or adapter file defines exactly one class or interface.

`scripts/check_layers.py` checks both rules in any supported language during the refactor. Then
encode the dependency rule in the repo's own suite with its native tool (ArchUnit,
dependency-cruiser, NetArchTest, a `go list` test, an `ast` test; see `layouts.md`), so CI keeps
enforcing it after the skill is gone.

## 7. Frozen assertions

During the move, tests may change how they import and wire things, but not what they assert.

- Diff the assertions: `git diff -U0 -- <test dirs> | grep -E '^[-+].*(assert|expect|should)'`,
  adjusted to the test framework's vocabulary.
- The test count may only go up.
- An edited assertion is a behaviour decision. It needs a reason in the report.

## 8. Flagged changes

Moving code often exposes things worth tightening, such as rejecting an unknown config key or
handling a malformed response. Don't fold them in silently. List each one with:

- the old behaviour;
- the new behaviour;
- why it's worth changing;
- a recommendation: keep it in this change, or split it out.

## 9. Mutation testing (optional)

Mutation testing makes small changes to the core and checks the suite fails on each. It shows
the tests would catch a real regression, not just that they pass. Tools: `mutmut` (Python),
Stryker (JS/TS, C#), PIT (Java/Kotlin), `go-mutesting` (Go), `cargo-mutants` (Rust), Mull
(C/C++). Run it on `core` only; adapters are thin
by design.
