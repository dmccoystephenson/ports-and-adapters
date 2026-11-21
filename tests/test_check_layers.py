"""Tests for scripts/check_layers.py across languages. Run: python3 -m unittest discover -s tests"""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_layers  # noqa: E402

# For each language: a clean "billing" subsystem, plus edits that must each produce a violation.
CASES = {
    "python": {
        "good": {
            "__init__.py": "from app.billing.service import Service\n",
            "model.py": "class Invoice:\n    pass\n",
            "core.py": "from app.billing.model import Invoice\nfrom .ports.clock import Clock\n",
            "service.py": "from app.billing.adapters.system_clock import SystemClock\n",
            "ports/__init__.py": "from .clock import Clock\n",
            "ports/clock.py": "from typing import Protocol\n\nclass Clock(Protocol):\n    def now(self): ...\n",
            "adapters/__init__.py": "",
            "adapters/system_clock.py": "import time\n\nclass SystemClock:\n    def now(self):\n        return time.time()\n",
        },
        "bad_imports": [
            ("core.py", "from app.billing.adapters.system_clock import SystemClock\n"),
            ("core.py", "from .adapters import system_clock\n"),
            ("ports/clock.py", "from ..service import Service\n\nclass Clock:\n    pass\n"),
            ("model.py", "import app.billing.service\n\nclass Invoice:\n    pass\n"),
        ],
        "bad_types": ("adapters/system_clock.py", "class A:\n    pass\n\nclass B:\n    pass\n"),
        "comment_only": ("core.py", "# from app.billing.adapters import x\ns = 'from app.billing.adapters import y'\n"),
    },
    "ts": {
        "good": {
            "index.ts": "export { Service } from './service';\n",
            "model.ts": "export interface Invoice { id: string }\n",
            "core.ts": "import { Invoice } from './model';\nimport type { Clock } from './ports/clock';\n",
            "service.ts": "import { SystemClock } from './adapters/system-clock';\n",
            "ports/clock.ts": "// a port\nexport interface Clock {\n  now(): number;\n}\n",
            "adapters/system-clock.ts": "import { Clock } from '../ports/clock';\n"
                                        "export class SystemClock implements Clock {\n  now() { return Date.now(); }\n}\n"
                                        "type Ms = number;\n",
        },
        "bad_imports": [
            ("core.ts", "import { SystemClock } from './adapters/system-clock';\n"),
            ("ports/clock.ts", "import { Service } from '../service';\nexport interface Clock { now(): number }\n"),
            ("core.ts", "const s = require('./service');\n"),
            ("model.ts", "export { X } from './adapters';\nexport interface Invoice {}\n"),
        ],
        "bad_types": ("adapters/system-clock.ts", "export class A {}\nexport class B {}\n"),
        "comment_only": ("core.ts", "// import x from './adapters/x';\nconst s = \"import y from './service'\";\n"),
    },
    "java": {
        "good": {
            "model/Invoice.java": "package com.acme.billing.model;\npublic record Invoice(String id) {}\n",
            "core/Biller.java": "package com.acme.billing.core;\nimport com.acme.billing.ports.Clock;\n"
                                "public class Biller {}\n",
            "ports/Clock.java": "package com.acme.billing.ports;\n/** port */\npublic interface Clock {\n  long now();\n}\n",
            "adapters/SystemClock.java": "package com.acme.billing.adapters;\nimport com.acme.billing.ports.Clock;\n"
                                         "public final class SystemClock implements Clock {\n"
                                         "  public long now() { return System.currentTimeMillis(); }\n"
                                         "  private static class Helper {}\n}\n",
        },
        "bad_imports": [
            ("core/Biller.java", "package com.acme.billing.core;\nimport com.acme.billing.adapters.SystemClock;\n"
                                 "public class Biller {}\n"),
            ("ports/Clock.java", "package com.acme.billing.ports;\nimport static com.acme.billing.service.Wiring.build;\n"
                                 "public interface Clock {}\n"),
        ],
        "bad_types": ("adapters/SystemClock.java", "package x;\nclass A {}\nclass B {}\n"),
        "comment_only": ("core/Biller.java", "package x;\n/* import com.acme.billing.adapters.X; */\npublic class Biller {}\n"),
    },
    "kotlin": {
        "good": {
            "core/Biller.kt": "package com.acme.billing.core\nimport com.acme.billing.ports.Clock\nclass Biller\n",
            "ports/Clock.kt": "package com.acme.billing.ports\ninterface Clock {\n  fun now(): Long\n}\n",
            "adapters/SystemClock.kt": "package com.acme.billing.adapters\n"
                                       "class SystemClock : Clock {\n  override fun now() = 1L\n"
                                       "  companion object { val X = 1 }\n}\n",
        },
        "bad_imports": [("core/Biller.kt", "package x\nimport com.acme.billing.adapters.SystemClock\nclass Biller\n")],
        "bad_types": ("adapters/SystemClock.kt", "package x\nclass A\nobject B {}\n"),
    },
    "csharp": {
        "good": {
            "Core/Biller.cs": "using Acme.Billing.Ports;\nnamespace Acme.Billing.Core { public class Biller {} }\n",
            "Ports/IClock.cs": "namespace Acme.Billing.Ports;\npublic interface IClock { long Now(); }\n",
            "Adapters/SystemClock.cs": "using System;\nnamespace Acme.Billing.Adapters {\n"
                                       "  public sealed class SystemClock : Ports.IClock {\n"
                                       "    public long Now() => DateTime.UtcNow.Ticks;\n"
                                       "    private record Inner(int X);\n  }\n}\n",
        },
        "options": {"inner": ("Model", "Core", "Ports"), "outer": ("Adapters", "Service"),
                    "single_type_dirs": ("Ports", "Adapters")},
        "bad_imports": [("Core/Biller.cs", "using Acme.Billing.Adapters;\nnamespace X { class Biller {} }\n")],
        "bad_types": ("Adapters/SystemClock.cs", "namespace X {\n  class A {}\n  struct B {}\n}\n"),
    },
    "go": {
        "good": {
            "core.go": "package billing\n\nimport (\n\t\"fmt\"\n\t\"example.com/app/internal/billing/ports\"\n)\n",
            "ports/clock.go": "package ports\n\n// Clock is a port.\ntype Clock interface {\n\tNow() int64\n}\n",
            "adapters/system_clock.go": "package adapters\n\nimport \"time\"\n\n"
                                        "type SystemClock struct{}\n\nfunc (SystemClock) Now() int64 { return time.Now().Unix() }\n",
            "adapters/system_clock_test.go": "package adapters\n\ntype a struct{}\ntype b struct{}\n",
        },
        "bad_imports": [
            ("core.go", "package billing\n\nimport \"example.com/app/internal/billing/adapters\"\n"),
            ("ports/clock.go", "package ports\n\nimport (\n\tsvc \"example.com/app/internal/billing/service\"\n)\n\n"
                               "type Clock interface{}\n"),
        ],
        "bad_types": ("adapters/system_clock.go", "package adapters\n\ntype (\n\tA struct{}\n\tB struct{}\n)\n"),
    },
    "rust": {
        "good": {
            "mod.rs": "pub mod core;\npub mod ports;\npub mod adapters;\n",
            "core.rs": "use crate::billing::ports::clock::Clock;\nuse super::model::Invoice;\n",
            "ports/mod.rs": "pub mod clock;\n",
            "ports/clock.rs": "/// A port.\npub trait Clock {\n    fn now(&self) -> u64;\n}\n",
            "adapters/system_clock.rs": "use crate::billing::ports::clock::Clock;\npub struct SystemClock;\n"
                                        "impl Clock for SystemClock { fn now(&self) -> u64 { 0 } }\n",
        },
        "bad_imports": [
            ("core.rs", "use crate::billing::adapters::system_clock::SystemClock;\n"),
            ("ports/clock.rs", "use super::super::service::Service;\npub trait Clock {}\n"),
        ],
        "bad_types": ("adapters/system_clock.rs", "pub struct A;\npub(crate) struct B;\n"),
    },
    "cpp": {
        "good": {
            "core.h": "#pragma once\n#include \"ports/clock.h\"\n#include \"src/billing/ports/clock.h\"\n"
                      "#include \"vendor/adapters/x.h\"\n#include <vector>\nnamespace billing { class Biller {}; }\n",
            "ports/clock.h": "#pragma once\nnamespace billing::ports {\nclass Clock {\npublic:\n"
                             "  virtual ~Clock() = default;\n  virtual long now() = 0;\n};\n}\n",
            "adapters/system_clock.h": "#pragma once\n#include \"../ports/clock.h\"\nclass Helper;\n"
                                       "namespace billing { enum class Unit { Ms };\n"
                                       "class SystemClock : public ports::Clock { struct Cache {}; "
                                       "public: long now() override; }; }\n",
            "adapters/system_clock.cpp": "#include \"system_clock.h\"\nclass Anything {};\nclass More {};\n",
        },
        "bad_imports": [
            ("core.h", "#include \"adapters/system_clock.h\"\n"),
            ("ports/clock.h", "#include \"../service.h\"\nclass Clock {};\n"),
            # Project-rooted includes (an -I at the source root) name the subsystem first.
            ("core.h", "#include \"src/billing/adapters/system_clock.h\"\n"),
            ("core.h", "#include \"billing/service.h\"\n"),
        ],
        "bad_types": ("adapters/system_clock.h", "namespace b {\nclass A {};\nstruct B {};\n}\n"),
        "comment_only": ("core.h", "// #include \"adapters/x.h\"\nconst char* s = \"#include \\\"service.h\\\"\";\n"),
    },
}


class CheckLayersTests(unittest.TestCase):
    def build(self, files):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        root = Path(d.name) / "billing"
        for rel, text in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text)
        return root

    def check(self, lang, files):
        return check_layers.violations(self.build(files), "billing", **CASES[lang].get("options", {}))

    def test_clean_subsystems_pass(self):
        for lang, case in CASES.items():
            with self.subTest(lang=lang):
                self.assertEqual(self.check(lang, case["good"]), [])

    def test_inner_layer_importing_an_outer_one_fails(self):
        for lang, case in CASES.items():
            for rel, text in case["bad_imports"]:
                with self.subTest(lang=lang, file=rel, text=text):
                    problems = self.check(lang, dict(case["good"], **{rel: text}))
                    self.assertTrue(any(p.startswith(rel) and "imports" in p for p in problems), problems)

    def test_two_types_in_one_port_or_adapter_file_fails(self):
        for lang, case in CASES.items():
            rel, text = case["bad_types"]
            with self.subTest(lang=lang):
                problems = self.check(lang, dict(case["good"], **{rel: text}))
                self.assertTrue(any(p.startswith(rel) and "2 top-level types" in p for p in problems), problems)

    def test_comments_and_strings_are_ignored(self):
        for lang, case in CASES.items():
            if "comment_only" not in case:
                continue
            rel, text = case["comment_only"]
            with self.subTest(lang=lang):
                self.assertEqual(self.check(lang, dict(case["good"], **{rel: text})), [])

    def test_absolute_import_needs_the_subsystem_name_before_the_layer(self):
        files = dict(CASES["python"]["good"], **{"core.py": "from otherlib.adapters import thing\n"})
        self.assertEqual(self.check("python", files), [])

    def test_a_dotted_name_still_sees_outer_imports(self):
        # --name may be written as it appears in imports (app.billing, crate::billing,
        # com/acme/billing); each form must catch the same violation as the bare name.
        root = self.build(dict(CASES["python"]["good"], **{"core.py": "from app.billing.adapters import x\n"}))
        for name in ("billing", "app.billing", "app/billing", "app::billing", "App.Billing"):
            with self.subTest(name=name):
                problems = check_layers.violations(root, name)
                self.assertTrue(any(p.startswith("core.py") and "imports" in p for p in problems), problems)

    def test_a_dotted_name_must_match_whole_segments(self):
        files = dict(CASES["python"]["good"], **{"core.py": "from other.billing.adapters import x\n"})
        self.assertEqual(check_layers.violations(self.build(files), "app.billing"), [])
        self.assertEqual(self.check("python", CASES["python"]["good"]), [])

    def test_cli(self):
        root = self.build(CASES["python"]["good"])
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(check_layers.main([str(root)]), 0)
        self.assertIn("OK: billing", out.getvalue())
        (root / "core.py").write_text("from app.billing import service\n")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(check_layers.main([str(root)]), 1)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(check_layers.main([str(root / "missing")]), 2)


if __name__ == "__main__":
    unittest.main()
