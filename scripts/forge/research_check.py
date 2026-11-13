#!/usr/bin/env python3
"""Run the research checks as one command: closure_check.py, then research_lint.py, on one definition index.

Usage:
  python3 scripts/forge/research_check.py <research/<report>.md> [--ledger <path>] [--depth N] [--budget-share F]
                                         [--index auto|ctags|regex|none] [--root <dir>]
Options as in closure_check.py. Writes `<report>-closure.txt` and, when the report exists, `<report>-research-lint.txt`
(both also printed, closure first), then `research-check: closure <b> blocking, lint <b> blocking`.
Exit codes: 0 neither check has a blocking finding; 1 at least one has; 2 bad arguments, an unreadable ledger, an
unwritable output, or a forced ctags index that is missing or fails. The lint is skipped (and said so) while the report
does not exist yet.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import closure_check  # noqa: E402  (sibling module; path set above)
import research_closure as rc  # noqa: E402
import research_lint  # noqa: E402
import spec_refs  # noqa: E402


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run closure_check.py and research_lint.py as one command.")
    parser.add_argument("report", help="research/<report>.md")
    parser.add_argument("--ledger")
    parser.add_argument("--depth", type=int, default=rc.DEFAULT_DEPTH)
    parser.add_argument("--budget-share", type=float, default=rc.DEFAULT_BUDGET_SHARE)
    parser.add_argument("--index", choices=("auto", "ctags", "regex", "none"), default="auto")
    parser.add_argument("--root", default=os.getcwd())
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if args.depth < 0 or not 0 <= args.budget_share <= 100:
        print("error: --depth must be >= 0 and --budget-share between 0 and 100", file=sys.stderr)
        return 2
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("error: --root is not a directory: %s" % root, file=sys.stderr)
        return 2
    report, ledger, closure_out = closure_check.report_paths(args.report, args.ledger)
    stem = report[:-3] if report.endswith(".md") else report
    lint_out = stem + "-research-lint.txt"
    try:
        index = rc.build_index(root, args.index)
        c_text, c_blocking = closure_check.run(report, ledger, root, args.depth, args.budget_share, args.index, index)
        spec_refs.atomic_write(closure_out, c_text)
        sys.stdout.write(c_text)
        if os.path.isfile(report):
            l_text, l_blocking = research_lint.run(report, ledger, root, args.depth, args.budget_share, args.index,
                                                   index)
            spec_refs.atomic_write(lint_out, l_text)
            sys.stdout.write(l_text)
            lint_note = "lint %d blocking" % l_blocking
        else:
            l_blocking = 0
            lint_note = "lint skipped (no report yet)"
    except Exception as exc:  # noqa: BLE001  any failure is exit 2, never a false "findings" exit 1
        print("error: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        return 2
    print("research-check: closure %d blocking, %s" % (c_blocking, lint_note))
    return 1 if c_blocking or l_blocking else 0


if __name__ == "__main__":
    sys.exit(main())
