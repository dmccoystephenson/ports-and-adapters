#!/usr/bin/env python3
"""Parity runner: feed the same cases to the OLD and NEW code and diff what comes back.

Language-agnostic. For each side you write a tiny *driver* in the project's own language. It
reads cases as JSON Lines on stdin (one JSON object per line) and writes one JSON result per
line to stdout, in the same order. A driver that raises for a case should print an object such
as {"raised": "<ErrorType>"} for it, because an exception is an output too.

    # 1. build the case grid (cross product of the axes)
    python3 parity.py grid axes.json > cases.jsonl
    # 2. run both sides and compare
    python3 parity.py run --cases cases.jsonl --old "node old_driver.js" --new "node new_driver.js"

axes.json maps each input name to the values to try, e.g.
{"mode": ["report", "tend"], "size": [0, 59999, 60000, 60001], "healthy": [true, false]}.

The old side is usually the base commit checked out in a separate worktree (`git worktree add
../old <base>`), or a backup copy of the old module, so both builds exist at once. Results are
compared as parsed JSON (object key order doesn't matter). Exit code: 0 when there are no
differences, 1 when there are, 2 on usage or driver errors. Needs Python 3.8+ and the standard
library only.
"""
from __future__ import annotations

import argparse
import itertools
import json
import shlex
import subprocess
import sys
from pathlib import Path


def grid(axes: dict) -> list:
    keys = list(axes)
    for k in keys:
        if not isinstance(axes[k], list) or not axes[k]:
            raise ValueError(f"axis {k!r} must be a non-empty list")
    return [dict(zip(keys, values)) for values in itertools.product(*(axes[k] for k in keys))]


def run_driver(command: str, cases: list, timeout: float, cwd=None) -> list:
    payload = "".join(json.dumps(c, sort_keys=True) + "\n" for c in cases)
    proc = subprocess.run(shlex.split(command), input=payload, capture_output=True, text=True,
                          timeout=timeout, cwd=cwd)
    if proc.returncode != 0:
        raise RuntimeError(f"`{command}` exited {proc.returncode}: {proc.stderr.strip()[-2000:]}")
    lines = [line for line in proc.stdout.splitlines() if line.strip()]
    if len(lines) != len(cases):
        raise RuntimeError(f"`{command}` printed {len(lines)} result line(s) for {len(cases)} case(s)")
    results = []
    for i, line in enumerate(lines):
        try:
            results.append(json.loads(line))
        except ValueError:
            raise RuntimeError(f"`{command}` result {i + 1} is not JSON: {line[:200]}") from None
    return results


def compare(cases: list, old: list, new: list) -> list:
    return [(c, a, b) for c, a, b in zip(cases, old, new) if a != b]


def load_cases(path: Path) -> list:
    cases = []
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                cases.append(json.loads(line))
            except ValueError:
                raise ValueError(f"{path}:{n}: not JSON") from None
    return cases


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("grid", help="print the cross product of an axes file as JSON Lines")
    g.add_argument("axes", type=Path)
    r = sub.add_parser("run", help="run both drivers over the cases and report differences")
    r.add_argument("--cases", type=Path, required=True, help="JSON Lines, one case per line")
    r.add_argument("--old", required=True, help="command for the old-code driver")
    r.add_argument("--new", required=True, help="command for the new-code driver")
    r.add_argument("--old-cwd", help="directory to run the old driver in (e.g. a base-commit worktree)")
    r.add_argument("--new-cwd", help="directory to run the new driver in")
    r.add_argument("--timeout", type=float, default=600, help="seconds per driver run")
    r.add_argument("--show", type=int, default=20, help="differences to print")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "grid":
            for case in grid(json.loads(a.axes.read_text(encoding="utf-8"))):
                print(json.dumps(case, sort_keys=True))
            return 0
        cases = load_cases(a.cases)
        old = run_driver(a.old, cases, a.timeout, a.old_cwd)
        new = run_driver(a.new, cases, a.timeout, a.new_cwd)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    diffs = compare(cases, old, new)
    print(f"{len(cases)} cases compared, {len(diffs)} difference(s)")
    for case, x, y in diffs[: a.show]:
        print(f"- case {json.dumps(case, sort_keys=True)}\n    old: {json.dumps(x, sort_keys=True)}"
              f"\n    new: {json.dumps(y, sort_keys=True)}")
    return 1 if diffs else 0


if __name__ == "__main__":
    sys.exit(main())
