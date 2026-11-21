# Port map: `<subsystem>`

Fill this in at step 4 and show it to the owner **before** any code moves.

## Ports

| Port (role) | Question it answers | Methods | Current code (file:line) | Adapters (production / test) | Why it earns a port |
|---|---|---|---|---|---|
| `HealthProbe` | Is this backend up right now? | `check(backend) -> Health` | `router.py:321 check_health` | `HttpHealthProbe`, `AssumeHealthy` / `FakeHealth` | tests patch it today; `--no-health` needs a second implementation |
| | | | | | |

Valid reasons in the last column:

- **2nd impl:** a second production implementation exists or is planned.
- **fake:** a test needs a fake (it patches or mocks this today).
- **placement:** a repo rule says this code lives in another module.

"Might change someday" is not a reason.

## Seams left inline

| Seam | Where | Why it stays |
|---|---|---|
| | | |

## Domain model (`model`)

| Type | Fields kept | Fields moved to an adapter's `settings` |
|---|---|---|
| | | |

## Code that must not move (from the repo's rules)

| Code | Rule | Adapter that delegates to it |
|---|---|---|
| | | |

## Layout after the refactor

```
<subsystem>/
  __init__      public API, architecture note
  model         domain values
  core          policy (ports only)
  service       composition root
  ports/        one interface per file
  adapters/     one implementation per file, registries in the index
```

## Baseline

- Test command:
- Interpreter / toolchain:
- Counts (pass / skip / fail):
- Characterization tests added:
