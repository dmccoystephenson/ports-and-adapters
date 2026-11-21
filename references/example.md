# Worked example: provider routing in gardener

This example is in Python. Every step, rule and gate applies unchanged in other languages;
only the idioms in `layouts.md` differ.

[gardener](https://github.com/dmccoystephenson/gardener) is an MIT-licensed Python CLI that runs
coding agents against repositories. Its optional **provider routing** chooses, for each run, which
agent provider to use (a subscription model, a self-hosted model, an external command) by repo
size and mode, and escalates to the next provider when one fails.

## Before: one 521-line module

`gardener/router.py` mixed policy with:

- `urllib` health checks;
- `os.walk` repo profiling;
- JSON file reads;
- a `threading` semaphore per provider;
- `print` to stderr.

`Provider` carried harness-specific fields (`claude_bin`, `command`) and built its own harness
config. Tests patched `router.check_health` and `router._announce_wait`.

## Port map (as approved)

| Port | Question | Adapters | Reason |
|---|---|---|---|
| `ProviderKind` | How is this kind of provider configured and run? | `ClaudeCodeKind`, `CommandKind` | 2nd impl (two kinds today, more planned) |
| `HealthProbe` | Is it up right now? | `HttpHealthProbe`, `AssumeHealthy` | 2nd impl (`--no-health`, planning) + fake |
| `Readiness` | Can it run this mode on this machine at all? | `DispatchReadiness` | placement: safety checks must stay in `dispatch.py` |
| `RepoProfiler` | How big is this repo? | `FilesystemProfiler` | fake |
| `RoutingSource` | Where does the routing config come from? | `JsonFileSource` | fake |
| `ConcurrencyLimiter` | Is this provider free? | `SemaphoreLimiter` | fake (was patched) |
| `AgentRunner` | Do one run on one config. | `DispatchRunner` | placement (`dispatch.run_agent`) + fake |
| `RoutingObserver` | Tell someone what happened. | `StderrObserver`, `NullObserver` | 2nd impl + fake (was patched) |

## After

```
gardener/routing/
  __init__.py  __main__.py  model.py  core.py  service.py
  ports/     agent_runner.py  concurrency_limiter.py  health_probe.py  provider_kind.py
             readiness.py  repo_profiler.py  routing_observer.py  routing_source.py
  adapters/  assume_healthy.py  claude_code_kind.py  command_kind.py  dispatch_readiness.py
             dispatch_runner.py  filesystem_profiler.py  http_health_probe.py
             json_file_source.py  null_observer.py  semaphore_limiter.py  stderr_observer.py
```

- **A new provider type** is one adapter file plus one entry in `adapters.DEFAULT_KINDS`. A test
  defines a throwaway kind and routes a run through it with no core changes.
- **Core tests** use one fake per port, with no patching.
- **Architecture tests** fail if `model`, `core` or `ports` import `adapters` or `service`, or if
  a port or adapter file holds more than one class.

## Proof

| Check | Result |
|---|---|
| Full suite | 1,457 → 1,467 tests, all passing |
| Parity, old vs new (in-process; `scripts/parity.py` does the same through drivers) | 600 cases (mode × repo × size × health × readiness): 0 differences in candidates, skip reasons, harness configs and escalation results |
| Architecture tests | pass |

## Flagged changes (kept, with the owner's approval)

- **Config validation:** a provider key its kind doesn't own (e.g. the typo `comand`) and an
  unknown `cost` are now rejected. Before, they were ignored.
- **Health checks:** a health reply that isn't a JSON object now counts as unreachable. Before, it
  raised.

## Lessons the skill encodes

- **Write the safety net first.** In this example the new tests and the parity harness came
  *after* the move. Steps 2 and 6 now come before step 7.
- **Use the repo's interpreter.** The first suite run used system Python 3.8 and failed at
  import. Step 2 now says to use the repo's own runner and interpreter.
- **Moving code invites fixes.** Both tightenings were found mid-move. Rule 1 and the safety
  net's "flagged changes" layer keep them visible.
- **Existing types can be the contract.** The ports still use three gardener types (`Mode`,
  `HarnessConfig`, `DispatchResult`), because they are the real contract of its dispatch module.
  Port doc comments say so instead of duplicating them.
