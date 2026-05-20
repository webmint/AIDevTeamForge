"""Tests for src/devforge/lib/_pr_review/_smells/atomic_dump.py.

Coverage:
  _count_added_lines — parser helper, isolated
  _count_new_files   — parser helper, isolated
  run()              — positive (additions threshold), positive (new-files threshold),
                       negative (below both), edge (empty diff)
  Finding schema     — correct keys + evidence format
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._smells.atomic_dump import (  # noqa: E402
    _DEFAULT_ADDITIONS_THRESHOLD,
    _DEFAULT_NEW_FILES_THRESHOLD,
    _count_added_lines,
    _count_new_files,
    run,
)
from _pr_review._state import PRReviewState  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers for building synthetic diffs.
# ---------------------------------------------------------------------------


def _make_diff_with_additions(n: int, with_new_file: bool = False) -> str:
    """Build a minimal unified diff with n added lines and optionally one new file."""
    lines = []
    lines.append("diff --git a/foo.py b/foo.py")
    if with_new_file:
        lines.append("new file mode 100644")
    lines.append("index 0000000..1111111 100644")
    lines.append("--- a/foo.py")
    lines.append("+++ b/foo.py")
    lines.append("@@ -1,0 +1,{n} @@".format(n=n))
    for i in range(n):
        lines.append("+added line {i}".format(i=i))
    return "\n".join(lines) + "\n"


def _make_diff_with_new_files(count: int) -> str:
    """Build a minimal unified diff with `count` new-file blocks (1 added line each)."""
    blocks = []
    for i in range(count):
        blocks.append(
            "diff --git a/file{i}.py b/file{i}.py\n"
            "new file mode 100644\n"
            "index 0000000..1111111 100644\n"
            "--- /dev/null\n"
            "+++ b/file{i}.py\n"
            "@@ -0,0 +1,1 @@\n"
            "+content\n".format(i=i)
        )
    return "\n".join(blocks)


def _make_state(diff: str) -> PRReviewState:
    return PRReviewState(diff=diff)


# ---------------------------------------------------------------------------
# _count_added_lines
# ---------------------------------------------------------------------------


class TestCountAddedLines(unittest.TestCase):
    def test_empty_diff_returns_zero(self):
        self.assertEqual(_count_added_lines(""), 0)

    def test_single_added_line(self):
        diff = "+added content\n"
        self.assertEqual(_count_added_lines(diff), 1)

    def test_file_header_line_excluded(self):
        """'+++ b/file.py' must NOT count as an added line."""
        diff = "+++ b/file.py\n+actual added line\n"
        self.assertEqual(_count_added_lines(diff), 1)

    def test_removed_lines_not_counted(self):
        diff = "-removed line\n+added line\n"
        self.assertEqual(_count_added_lines(diff), 1)

    def test_context_lines_not_counted(self):
        diff = " context line\n+added line\n-removed line\n"
        self.assertEqual(_count_added_lines(diff), 1)

    def test_multiple_added_lines(self):
        diff = "+line1\n+line2\n+line3\n"
        self.assertEqual(_count_added_lines(diff), 3)

    def test_300_added_lines(self):
        diff = "\n".join("+line{i}".format(i=i) for i in range(300)) + "\n"
        self.assertEqual(_count_added_lines(diff), 300)

    def test_diff_with_only_headers(self):
        diff = (
            "diff --git a/foo.py b/foo.py\n"
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
        )
        self.assertEqual(_count_added_lines(diff), 0)


# ---------------------------------------------------------------------------
# _count_new_files
# ---------------------------------------------------------------------------


class TestCountNewFiles(unittest.TestCase):
    def test_empty_diff_returns_zero(self):
        self.assertEqual(_count_new_files(""), 0)

    def test_one_new_file(self):
        diff = (
            "diff --git a/new.py b/new.py\n"
            "new file mode 100644\n"
            "+content\n"
        )
        self.assertEqual(_count_new_files(diff), 1)

    def test_zero_new_files_in_modification_diff(self):
        diff = (
            "diff --git a/existing.py b/existing.py\n"
            "index abc..def 100644\n"
            "--- a/existing.py\n"
            "+++ b/existing.py\n"
            "+added\n"
        )
        self.assertEqual(_count_new_files(diff), 0)

    def test_multiple_new_files(self):
        diff = _make_diff_with_new_files(5)
        self.assertEqual(_count_new_files(diff), 5)

    def test_mix_of_new_and_modified_files(self):
        diff = (
            "diff --git a/new.py b/new.py\n"
            "new file mode 100644\n"
            "+content\n"
            "diff --git a/existing.py b/existing.py\n"
            "index abc..def 100644\n"
            "+modification\n"
        )
        self.assertEqual(_count_new_files(diff), 1)


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------


class TestAtomicDumpRunPositive(unittest.TestCase):
    def test_additions_above_threshold_fires(self):
        """301 added lines (> 300) with 1 new file fires."""
        diff = _make_diff_with_additions(_DEFAULT_ADDITIONS_THRESHOLD + 1, with_new_file=True)
        state = _make_state(diff)
        findings = run(state)
        self.assertEqual(len(findings), 1)

    def test_new_files_above_threshold_fires(self):
        """5 new files (> 4) with 1 added line each fires."""
        diff = _make_diff_with_new_files(_DEFAULT_NEW_FILES_THRESHOLD + 1)
        state = _make_state(diff)
        findings = run(state)
        self.assertEqual(len(findings), 1)

    def test_500_added_lines_fires(self):
        diff = _make_diff_with_additions(500)
        findings = run(_make_state(diff))
        self.assertEqual(len(findings), 1)

    def test_both_thresholds_exceeded_one_finding(self):
        """Only ONE finding emitted even when both thresholds are exceeded."""
        diff = _make_diff_with_new_files(10)
        # Add 500 more addition lines by appending to the diff.
        extra = "\n".join("+extra{i}".format(i=i) for i in range(500))
        diff += extra
        findings = run(_make_state(diff))
        self.assertEqual(len(findings), 1)


class TestAtomicDumpRunNegative(unittest.TestCase):
    def test_100_additions_2_new_files_no_finding(self):
        """100 lines + 2 new files — both below thresholds."""
        diff = _make_diff_with_additions(100)
        diff += _make_diff_with_new_files(2)
        findings = run(_make_state(diff))
        self.assertEqual(findings, [])

    def test_exactly_at_additions_threshold_no_finding(self):
        """Exactly 300 additions — threshold is >300, so no finding."""
        diff = _make_diff_with_additions(_DEFAULT_ADDITIONS_THRESHOLD)
        findings = run(_make_state(diff))
        self.assertEqual(findings, [])

    def test_exactly_at_new_files_threshold_no_finding(self):
        """Exactly 4 new files — threshold is >4, so no finding."""
        diff = _make_diff_with_new_files(_DEFAULT_NEW_FILES_THRESHOLD)
        findings = run(_make_state(diff))
        self.assertEqual(findings, [])


class TestAtomicDumpEdgeCases(unittest.TestCase):
    def test_empty_diff_no_finding(self):
        findings = run(_make_state(""))
        self.assertEqual(findings, [])

    def test_none_diff_treated_as_empty(self):
        state = PRReviewState(diff=None)  # type: ignore[arg-type]
        findings = run(state)
        self.assertEqual(findings, [])


class TestAtomicDumpFindingSchema(unittest.TestCase):
    def setUp(self):
        diff = _make_diff_with_additions(500)
        self.findings = run(_make_state(diff))

    def test_finding_name(self):
        self.assertEqual(self.findings[0]["name"], "atomic_dump")

    def test_finding_severity_medium(self):
        self.assertEqual(self.findings[0]["severity"], "medium")

    def test_finding_location_star(self):
        self.assertEqual(self.findings[0]["location"], "*")

    def test_finding_evidence_contains_additions_count(self):
        evidence = self.findings[0]["evidence"]
        self.assertIn("500", evidence)

    def test_finding_evidence_contains_thresholds(self):
        evidence = self.findings[0]["evidence"]
        self.assertIn(str(_DEFAULT_ADDITIONS_THRESHOLD), evidence)
        self.assertIn(str(_DEFAULT_NEW_FILES_THRESHOLD), evidence)

    def test_exactly_one_finding(self):
        self.assertEqual(len(self.findings), 1)


if __name__ == "__main__":
    unittest.main()
