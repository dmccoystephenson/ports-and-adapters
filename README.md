# ports-and-adapters

A Claude Code skill that refactors a project in **any language**, or one subsystem of it, into a
pure core plus **ports and adapters**: one file per port and one file per adapter. It works
without changing behaviour, and a layered test safety net proves that.

It follows Clean Architecture (dependencies point inward, ports are owned by the core, a single
composition root) and Clean Code (names reveal role and technology, one concept per file,
expected failures as values). It stops for your approval of the **port map** before any code
moves.

## What it produces

```
<subsystem>/
  model        domain values, no I/O
  core         policy, written against ports only
  service      composition root: production adapters as defaults
  ports/       one interface per file
  adapters/    one implementation per file, registries in the index file
```

A new backend then becomes one new adapter file plus a registry entry, and tests use fakes
instead of patching.

## Installation

Copy this directory into a Claude Code skills directory, either `.claude/skills/ports-and-adapters/`
in a project or `~/.claude/skills/ports-and-adapters/` for all projects.

```sh
git clone https://github.com/dmccoystephenson/ports-and-adapters ~/.claude/skills/ports-and-adapters
```

## Usage

```
/ports-and-adapters src/billing
```

The skill:

1. scopes the subsystem and reads the repo's own rules;
2. runs the baseline suite and adds characterization tests where coverage is thin;
3. finds the seams and drafts a **port map**, then waits for your approval;
4. extracts the model, writes the ports test-first, moves code into adapters, points the core at
   the ports, adds the composition root and rewires the callers;
5. proves the result: parity between old and new, architecture tests, frozen assertions, and the
   full suite at or above the baseline count;
6. updates the docs and reports, without committing anything on its own.

The full process is in [`SKILL.md`](SKILL.md).

## What's inside

| Path | Purpose |
|---|---|
| [`SKILL.md`](SKILL.md) | the process, gates and rules |
| [`references/port-map-template.md`](references/port-map-template.md) | the table you approve |
| [`references/safety-net.md`](references/safety-net.md) | characterization tests, parity, frozen assertions, mutation testing |
| [`references/layouts.md`](references/layouts.md) | Python, TypeScript/JavaScript, Java/Kotlin, C#, Go, Rust and C++: layout, port, adapter and fake snippets, and CI enforcement |
| [`references/clean-code-architecture.md`](references/clean-code-architecture.md) | how Clean Architecture, SOLID and Clean Code apply |
| [`references/example.md`](references/example.md) | a worked example on an open-source CLI |
| [`scripts/check_layers.py`](scripts/check_layers.py) | checks inward-only dependencies and one type per port/adapter file, for all of the languages above |
| [`scripts/parity.py`](scripts/parity.py) | runs the old and new code over a generated case grid through small drivers in any language, and diffs the results |

Both scripts need only Python 3.8+ and its standard library; the code they check can be in any
of the languages above.

```sh
python3 scripts/check_layers.py src/billing                 # OK / FAIL with the reasons
python3 scripts/parity.py grid axes.json > cases.jsonl
python3 scripts/parity.py run --cases cases.jsonl --old "node old.js" --new "node new.js"
```

## Development

```sh
python3 -m unittest discover -s tests
```

The tests cover `check_layers.py` on clean and violating fixtures in seven languages, and
`parity.py` end to end.

## License

[MIT](LICENSE)
