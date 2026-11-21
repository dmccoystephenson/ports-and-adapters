"""Tests for scripts/parity.py. Run: python3 -m unittest discover -s tests"""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import parity  # noqa: E402

# A driver in "the project's language" (Python here, to keep the test self-contained). OLD ranks
# sizes one way; NEW has a deliberate off-by-one at the threshold.
DRIVER = """
import json, sys
BUG = {bug}
for line in sys.stdin:
    c = json.loads(line)
    if c["size"] < 0:
        print(json.dumps({{"raised": "ValueError"}})); continue
    limit = 60000 if not BUG else 59999
    print(json.dumps({{"tier": "S" if c["size"] <= limit else "M", "mode": c["mode"]}}))
"""


class ParityTests(unittest.TestCase):
    def setUp(self):
        self._d = tempfile.TemporaryDirectory()
        self.d = Path(self._d.name)
        for name, bug in (("old.py", False), ("same.py", False), ("new_bug.py", True)):
            (self.d / name).write_text(DRIVER.format(bug=bug))
        axes = {"mode": ["report", "tend"], "size": [-1, 0, 60000, 60001]}
        (self.d / "axes.json").write_text(json.dumps(axes))
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(parity.main(["grid", str(self.d / "axes.json")]), 0)
        (self.d / "cases.jsonl").write_text(out.getvalue())

    def tearDown(self):
        self._d.cleanup()

    def run_parity(self, new):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = parity.main(["run", "--cases", str(self.d / "cases.jsonl"),
                                "--old", f"{sys.executable} {self.d / 'old.py'}",
                                "--new", f"{sys.executable} {self.d / new}"])
        return code, out.getvalue()

    def test_grid_is_the_cross_product(self):
        self.assertEqual(len((self.d / "cases.jsonl").read_text().splitlines()), 8)

    def test_identical_drivers_have_no_differences(self):
        code, out = self.run_parity("same.py")
        self.assertEqual(code, 0)
        self.assertIn("8 cases compared, 0 difference(s)", out)

    def test_a_behaviour_change_is_reported(self):
        code, out = self.run_parity("new_bug.py")
        self.assertEqual(code, 1)
        self.assertIn("8 cases compared, 2 difference(s)", out)   # size 60000, both modes
        self.assertIn('"size": 60000', out)

    def test_driver_that_prints_too_few_lines_is_an_error(self):
        (self.d / "short.py").write_text("print('{}')\n")
        code, _ = self.run_parity("short.py")
        self.assertEqual(code, 2)

    def test_empty_axis_is_rejected(self):
        with self.assertRaises(ValueError):
            parity.grid({"mode": []})


if __name__ == "__main__":
    unittest.main()
