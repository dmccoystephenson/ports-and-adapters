# Layouts by language

The shape is the same everywhere:

- `model`: domain values;
- `core`: policy, written against ports only;
- `service`: the composition root;
- `ports/`: one interface per file;
- `adapters/`: one implementation per file, with registries in the index file.

Follow the repo's existing naming and casing conventions over these defaults. Each section shows
the layout, one port, one adapter, one fake, and how to enforce the dependency rule in the repo's
own CI.

`scripts/check_layers.py` checks the dependency rule and the one-type-per-file rule in every
language below. Pass `--inner` and `--outer` when the names differ, e.g. `--inner Model Core
Ports --outer Adapters Service` for C#.

The running example is a `Clock` port (`now()`), its `SystemClock` adapter and a `FakeClock`.

---

## Python

```
pkg/billing/
  __init__.py   model.py   core.py   service.py
  ports/__init__.py   ports/clock.py
  adapters/__init__.py   adapters/system_clock.py
tests/test_billing.py
```

```python
# ports/clock.py
from typing import Protocol, runtime_checkable

@runtime_checkable
class Clock(Protocol):
    """Current time in seconds since the epoch. Never blocks; thread-safe."""
    def now(self) -> float: ...

# adapters/system_clock.py
import time

class SystemClock:
    def now(self) -> float:
        return time.time()

# tests: a fake
class FakeClock:
    def __init__(self, t: float = 0.0): self.t = t
    def now(self) -> float: return self.t
```

**Enforce in CI:** a unit test that walks `ast` over `model.py`, `core.py` and `ports/` and fails
on imports of `adapters` or `service`. `scripts/check_layers.py` can be called from the test.

**Import cycles:** if an adapter must reach a module that imports the subsystem back, import it
inside the function, with a comment saying why.

## TypeScript / JavaScript

```
src/billing/
  index.ts   model.ts   core.ts   service.ts
  ports/clock.ts
  adapters/index.ts   adapters/system-clock.ts
```

```ts
// ports/clock.ts
/** Current time in ms since the epoch. Never throws. */
export interface Clock { now(): number }

// adapters/system-clock.ts
import type { Clock } from "../ports/clock";
export class SystemClock implements Clock { now() { return Date.now(); } }

// test fake
export class FakeClock implements Clock { constructor(public t = 0) {} now() { return this.t; } }
```

**Enforce in CI:** add an ESLint override for `src/billing/{model,core}.ts` and
`src/billing/ports/**`:

```json
{ "rules": { "no-restricted-imports": ["error", { "patterns": ["**/adapters/**", "**/service"] }] } }
```

Alternatively, a dependency-cruiser rule: `from: { path: "billing/(model|core|ports)" }, to:
{ path: "billing/(adapters|service)" }`.

## Java / Kotlin

```
com/acme/billing/model/Invoice.java
com/acme/billing/core/Biller.java
com/acme/billing/ports/Clock.java
com/acme/billing/adapters/SystemClock.java
com/acme/billing/BillingService.java
```

```java
// ports/Clock.java
/** Current time in ms since the epoch. Thread-safe. */
public interface Clock { long now(); }

// adapters/SystemClock.java
public final class SystemClock implements Clock {
  @Override public long now() { return System.currentTimeMillis(); }
}

// test fake
final class FakeClock implements Clock { long t; @Override public long now() { return t; } }
```

**Enforce in CI:** an ArchUnit test.

```java
@ArchTest static final ArchRule inward = noClasses()
    .that().resideInAnyPackage("..billing.model..", "..billing.core..", "..billing.ports..")
    .should().dependOnClassesThat().resideInAnyPackage("..billing.adapters..");
```

In Kotlin, the same rule works with ArchUnit, or Konsist.

## C#

```
Billing/Model/Invoice.cs
Billing/Core/Biller.cs
Billing/Ports/IClock.cs
Billing/Adapters/SystemClock.cs
Billing/BillingService.cs
```

```csharp
// Ports/IClock.cs
/// <summary>Current UTC time. Thread-safe.</summary>
public interface IClock { DateTimeOffset Now(); }

// Adapters/SystemClock.cs
public sealed class SystemClock : IClock { public DateTimeOffset Now() => DateTimeOffset.UtcNow; }

// test fake
sealed class FakeClock : IClock { public DateTimeOffset T; public DateTimeOffset Now() => T; }
```

**Enforce in CI:** a NetArchTest assertion, `Types.InAssembly(asm).That()
.ResideInNamespace("Acme.Billing.Core").ShouldNot().HaveDependencyOn("Acme.Billing.Adapters")`.
Alternatively, split the layers into projects whose references only point inward.

`check_layers.py` flags: `--inner Model Core Ports --outer Adapters Service`.

## Go

Interfaces belong to the consumer: keep `ports` next to the core.

```
internal/billing/model.go   core.go   service.go
internal/billing/ports/clock.go
internal/billing/adapters/system_clock.go
```

```go
// ports/clock.go
// Clock reports the current time. Safe for concurrent use.
type Clock interface{ Now() time.Time }

// adapters/system_clock.go
type SystemClock struct{}
func (SystemClock) Now() time.Time { return time.Now() }

// fake, in a _test.go file or an internal testutil package
type FakeClock struct{ T time.Time }
func (f FakeClock) Now() time.Time { return f.T }
```

**Enforce in CI:** a test that runs `go list -deps ./internal/billing/ports` and `go list -f
'{{join .Imports "\n"}}' ./internal/billing` and fails on any path containing
`internal/billing/adapters` or `internal/billing/service`.

If one adapter needs several files, give it its own package (`adapters/systemclock/`). The rule
is still one adapter per package, and one exported type per file.

## Rust

```
src/billing/mod.rs   model.rs   core.rs   service.rs
src/billing/ports/mod.rs   src/billing/ports/clock.rs
src/billing/adapters/mod.rs   src/billing/adapters/system_clock.rs
```

```rust
// ports/clock.rs
/// Current time in ms since the epoch. Must be cheap and non-blocking.
pub trait Clock { fn now(&self) -> u64; }

// adapters/system_clock.rs
pub struct SystemClock;
impl Clock for SystemClock {
    fn now(&self) -> u64 { std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_millis() as u64 }
}

// test fake
struct FakeClock(u64);
impl Clock for FakeClock { fn now(&self) -> u64 { self.0 } }
```

**Enforce in CI:** move the core and ports into their own crate in the workspace, without
`adapters` as a dependency, so the compiler enforces the rule. Alternatively, run
`check_layers.py` as a CI step.

## C++

```
billing/model.h
billing/core.{h,cpp}
billing/service.{h,cpp}
billing/ports/clock.h
billing/adapters/system_clock.{h,cpp}
```

```cpp
// ports/clock.h
/// Current time in ms since the epoch. Thread-safe.
class Clock { public: virtual ~Clock() = default; virtual long long now() const = 0; };

// adapters/system_clock.h
class SystemClock final : public Clock { public: long long now() const override; };

// test fake
class FakeClock final : public Clock { public: long long t = 0; long long now() const override { return t; } };
```

**Enforce in CI:** separate CMake targets (`billing_core` links nothing from `billing_adapters`),
so a stray include fails to link. Alternatively, a CTest step running `check_layers.py`.

The one-type rule applies to headers. `.cpp` files may hold private helpers.
