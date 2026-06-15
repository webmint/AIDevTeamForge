"""Tests for src/devforge/lib/_shared/_validate.py.

Coverage:
  validate_findings — one finding per rejection class:
    - file doesn't exist → file_missing discard
    - line 0 (and line > total) → line_oob discard
    - evidence not a literal substring → quote_mismatch discard
    - evidence empty / just "..." → evidence_empty discard
    - pattern empty → pattern_missing discard
  - a fully-valid finding passes
  - whitespace-normalisation: evidence with collapsed spaces still matches
  - discard_counts tally correct
  All tests build real files on disk (round-trip via real producer).
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _shared._validate import (  # noqa: E402
    REASON_EVIDENCE_EMPTY,
    REASON_FILE_MISSING,
    REASON_LINE_OOB,
    REASON_PATTERN_MISSING,
    REASON_QUOTE_MISMATCH,
    validate_findings,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(**overrides):
    """Return a minimal valid ParsedFinding dict; overrides applied last."""
    base = {
        "agent": "code-reviewer",
        "severity": "High",
        "file": "src/foo.py",
        "line": 1,
        "pattern": "Some bad pattern",
        "confidence": "Certain",
        "evidence": "def foo():",
        "why": "This is wrong.",
        "remediation": "Fix it.",
        "tags": [],
    }
    base.update(overrides)
    return base


class TestValidateFindingsSetup(unittest.TestCase):
    """Base class providing a temp directory with real source files."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Create a real source file with known content
        self.src_dir = os.path.join(self.tmpdir, "src")
        os.makedirs(self.src_dir)
        self.src_file = os.path.join(self.src_dir, "foo.py")
        self.file_content = (
            "# Module foo\n"
            "def foo():\n"
            "    return True\n"
            "\n"
            "def bar(x, y):\n"
            "    if x > y:\n"
            "        return x\n"
            "    return y\n"
        )
        with open(self.src_file, "w", encoding="utf-8") as fh:
            fh.write(self.file_content)
        self.total_lines = len(self.file_content.splitlines())  # 8

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TestFileMissing(TestValidateFindingsSetup):
    def test_nonexistent_file_discarded(self):
        finding = _make_finding(
            file="src/does_not_exist.py",
            line=1,
            evidence="def foo():",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(len(result["passed"]), 0)
        self.assertEqual(len(result["discarded"]), 1)
        self.assertEqual(result["discarded"][0]["reason"], REASON_FILE_MISSING)

    def test_discard_counts_file_missing(self):
        finding = _make_finding(file="src/ghost.py", line=1, evidence="x = 1")
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(result["discard_counts"][REASON_FILE_MISSING], 1)
        self.assertEqual(result["discard_counts"][REASON_LINE_OOB], 0)


class TestLineOOB(TestValidateFindingsSetup):
    def test_line_zero_discarded(self):
        finding = _make_finding(
            file="src/foo.py",
            line=0,
            evidence="def foo():",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(len(result["discarded"]), 1)
        self.assertEqual(result["discarded"][0]["reason"], REASON_LINE_OOB)

    def test_line_exceeds_file_length_discarded(self):
        finding = _make_finding(
            file="src/foo.py",
            line=self.total_lines + 1,
            evidence="def foo():",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(result["discarded"][0]["reason"], REASON_LINE_OOB)

    def test_line_at_total_passes_line_check(self):
        # Line == total is valid (1-based); evidence must also match
        finding = _make_finding(
            file="src/foo.py",
            line=self.total_lines,
            evidence="return y",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        # Should pass line OOB check (may pass or fail quote check depending on evidence)
        reasons = [d["reason"] for d in result["discarded"]]
        self.assertNotIn(REASON_LINE_OOB, reasons)


class TestQuoteMismatch(TestValidateFindingsSetup):
    def test_fabricated_evidence_discarded(self):
        finding = _make_finding(
            file="src/foo.py",
            line=2,
            evidence="THIS IS NOT IN THE FILE AT ALL xyz123",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(len(result["discarded"]), 1)
        self.assertEqual(result["discarded"][0]["reason"], REASON_QUOTE_MISMATCH)

    def test_verbatim_evidence_passes(self):
        finding = _make_finding(
            file="src/foo.py",
            line=2,
            evidence="def foo():",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(len(result["passed"]), 1)
        self.assertEqual(len(result["discarded"]), 0)

    def test_whitespace_normalised_evidence_passes(self):
        # Evidence with extra/different spaces should still match after normalisation
        # "def foo():" and "def  foo():" should both match the normalised file content
        finding = _make_finding(
            file="src/foo.py",
            line=2,
            evidence="def  foo():",  # double space — normalised matches "def foo():"
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        # After whitespace normalisation, "def  foo():" → "def foo():" which IS in the file
        self.assertEqual(len(result["passed"]), 1,
                         "Whitespace-normalised evidence should pass quote check")


class TestEvidenceEmpty(TestValidateFindingsSetup):
    # Per §4.2 check order (file → line → quote → evidence → pattern),
    # check 3 (quote_mismatch) runs BEFORE check 4 (evidence_empty).
    # The quote check guard `if not normalised_evidence` catches empty/whitespace
    # evidence and reports it as quote_mismatch.  Check 4 (evidence_empty) is a
    # defensive follow-up that only fires when evidence_stripped == "..." somehow
    # passes the quote substring test (i.e. the file literally contains "...").
    # Tests below reflect the new spec-faithful order.

    def test_empty_evidence_discarded_as_quote_mismatch(self):
        # Empty evidence normalises to "" → fails `not normalised_evidence` in
        # check 3 → quote_mismatch (not evidence_empty per old order).
        finding = _make_finding(
            file="src/foo.py",
            line=2,
            evidence="",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(len(result["discarded"]), 1)
        self.assertEqual(result["discarded"][0]["reason"], REASON_QUOTE_MISMATCH)

    def test_just_dots_discarded_as_quote_mismatch(self):
        # "..." normalises to "..." which is not in the test file → quote_mismatch.
        finding = _make_finding(
            file="src/foo.py",
            line=2,
            evidence="...",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(len(result["discarded"]), 1)
        self.assertEqual(result["discarded"][0]["reason"], REASON_QUOTE_MISMATCH)

    def test_whitespace_only_evidence_discarded_as_quote_mismatch(self):
        # Whitespace-only normalises to "" → quote_mismatch from check 3.
        finding = _make_finding(
            file="src/foo.py",
            line=2,
            evidence="   \n  \t  ",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(len(result["discarded"]), 1)
        self.assertEqual(result["discarded"][0]["reason"], REASON_QUOTE_MISMATCH)

    def test_none_evidence_discarded(self):
        finding = _make_finding(
            file="src/foo.py",
            line=2,
            evidence=None,
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        # Should be discarded (check 3: empty normalised evidence → quote_mismatch)
        self.assertTrue(len(result["discarded"]) > 0)
        self.assertEqual(result["discarded"][0]["reason"], REASON_QUOTE_MISMATCH)

    def test_evidence_empty_reason_reachable_when_dots_in_file(self):
        # Construct a source file that literally contains "..." so that check 3
        # passes, allowing check 4 (evidence_empty) to fire for "..." evidence.
        dots_file = os.path.join(self.src_dir, "dots.py")
        with open(dots_file, "w", encoding="utf-8") as fh:
            fh.write("# file with ellipsis\nx = ...\nreturn ...\n")

        finding = _make_finding(
            file="src/dots.py",
            line=2,
            evidence="...",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(len(result["discarded"]), 1)
        # "..." IS in the file → check 3 passes → check 4 fires → evidence_empty
        self.assertEqual(result["discarded"][0]["reason"], REASON_EVIDENCE_EMPTY)


class TestPatternMissing(TestValidateFindingsSetup):
    def test_empty_pattern_discarded(self):
        finding = _make_finding(
            file="src/foo.py",
            line=2,
            evidence="def foo():",
            pattern="",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(result["discarded"][0]["reason"], REASON_PATTERN_MISSING)

    def test_whitespace_only_pattern_discarded(self):
        finding = _make_finding(
            file="src/foo.py",
            line=2,
            evidence="def foo():",
            pattern="   ",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(result["discarded"][0]["reason"], REASON_PATTERN_MISSING)


class TestFullyValidFinding(TestValidateFindingsSetup):
    def test_all_checks_pass(self):
        finding = _make_finding(
            file="src/foo.py",
            line=2,
            evidence="def foo():",
            pattern="Always returns True",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(len(result["passed"]), 1)
        self.assertEqual(len(result["discarded"]), 0)

    def test_multiline_evidence_passes(self):
        finding = _make_finding(
            file="src/foo.py",
            line=5,
            evidence="def bar(x, y):\n    if x > y:",
            pattern="Bar logic",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(len(result["passed"]), 1)


class TestDiscardCountsTally(TestValidateFindingsSetup):
    def test_all_reason_keys_present(self):
        result = validate_findings([], repo_root=self.tmpdir)
        counts = result["discard_counts"]
        for key in (
            REASON_FILE_MISSING,
            REASON_LINE_OOB,
            REASON_QUOTE_MISMATCH,
            REASON_EVIDENCE_EMPTY,
            REASON_PATTERN_MISSING,
        ):
            self.assertIn(key, counts)

    def test_multiple_discards_tallied_correctly(self):
        findings = [
            _make_finding(file="src/ghost1.py", line=1, evidence="x"),  # file_missing
            _make_finding(file="src/ghost2.py", line=1, evidence="x"),  # file_missing
            _make_finding(file="src/foo.py", line=0, evidence="def foo():"),  # line_oob
        ]
        result = validate_findings(findings, repo_root=self.tmpdir)
        self.assertEqual(result["discard_counts"][REASON_FILE_MISSING], 2)
        self.assertEqual(result["discard_counts"][REASON_LINE_OOB], 1)


class TestNearMissEvidence(TestValidateFindingsSetup):
    """Fix 5 — near-miss evidence must be rejected (exact substring, not fuzzy)."""

    def test_near_miss_evidence_discarded(self):
        # File contains "def validate_user(x):" but finding evidence says
        # "def validate_user(y):" — one identifier changed.  The substring
        # check is exact (not fuzzy), so this must be discarded as quote_mismatch.
        near_miss_file = os.path.join(self.src_dir, "users.py")
        with open(near_miss_file, "w", encoding="utf-8") as fh:
            fh.write("def validate_user(x):\n    return x is not None\n")

        finding = _make_finding(
            file="src/users.py",
            line=1,
            evidence="def validate_user(y):",
            pattern="Parameter naming inconsistency",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(len(result["discarded"]), 1)
        self.assertEqual(result["discarded"][0]["reason"], REASON_QUOTE_MISMATCH)

    def test_exact_evidence_passes(self):
        # Counterpart: exact match must still pass.
        near_miss_file = os.path.join(self.src_dir, "users.py")
        with open(near_miss_file, "w", encoding="utf-8") as fh:
            fh.write("def validate_user(x):\n    return x is not None\n")

        finding = _make_finding(
            file="src/users.py",
            line=1,
            evidence="def validate_user(x):",
            pattern="Parameter naming inconsistency",
        )
        result = validate_findings([finding], repo_root=self.tmpdir)
        self.assertEqual(len(result["passed"]), 1)
        self.assertEqual(len(result["discarded"]), 0)


class TestSourceRootResolution(TestValidateFindingsSetup):
    def test_source_root_resolves_shorter_path(self):
        # With source_root="src", agent can write "foo.py" instead of "src/foo.py"
        finding = _make_finding(
            file="foo.py",
            line=2,
            evidence="def foo():",
            pattern="Always True",
        )
        result = validate_findings(
            [finding],
            repo_root=self.tmpdir,
            source_root="src",
        )
        self.assertEqual(len(result["passed"]), 1)


if __name__ == "__main__":
    unittest.main()
