"""Tests for the --limit flag on find-feature-artifacts
(src/devforge/lib/_artifact/_cmds_find_artifacts.py), added after the
mtime + recency-ordering follow-up (see test_find_feature_artifacts_recency.py).

91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 1b: the prose
migration hit a real Class-B consumer with no single sentinel to filter
on -- it calls --filenames '["*"]', one record per file per feature
directory, and at fifty features that is thousands of records across two
full-size keys for a caller that wants exactly one string (the newest
feature_dir) or a handful (a windowed top-5). --limit N caps the emitted
population instead of pushing a shell-redirect-plus-python3-extraction
workaround onto command prose that has no python3 dependency today.

Kept in its OWN file, mirroring the same reasoning
test_find_feature_artifacts_recency.py's own docstring gives for its
split from test_find_feature_artifacts.py: each follow-up gets its own
concern-scoped file (with its own small harness, matching the precedent
tests/lib/_specify/test_find_handoffs_require.py already sets) so no
single file crosses this repository's 600-line test-file threshold.

Coverage:
  - --limit caps AFTER recency ordering, not layout order: a tree where
    the two orders DISAGREE, capped to 1, returns the RECENCY-newest
    record -- a limit applied to the wrong order would return a
    different one and this test would catch it.
  - the coherence rule under a limit > 1: "matches" keeps its own layout
    order over the SAME capped set "matches_by_recency" presents in
    recency order; "feature_dirs" is a view of the capped "matches".
  - --limit N >= the total match count returns everything, identical to
    omitting the flag entirely.
  - --limit 0 is a valid empty result, not an error.
  - a negative or non-integer --limit is a clean EXIT_ERR (this verb's
    own convention, not argparse's separate type=int exit code).
  - omitting --limit is byte-identical to the pre-flag contract.
  - a real CLI subprocess round-trip at --limit 1, parsing actual stdout
    JSON -- the actual Class-B call shape: no shell pipeline, no python3.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import json
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap — make _artifact importable (mirrors the sibling
# find-feature-artifacts test files)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LIB_DIR = str(_REPO_ROOT / "src" / "devforge" / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _artifact._cli import main  # noqa: E402
from _artifact._cmds_find_artifacts import EXIT_ERR, EXIT_OK  # noqa: E402

_ARTIFACT_HELPER_PY = _REPO_ROOT / "src" / "devforge" / "lib" / "artifact_helper.py"


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def _run_main(argv):
    """Call main() with sys.argv patched to argv. Returns (exit_code, stdout, stderr)."""
    old_argv = sys.argv
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.argv = ["artifact_helper"] + argv
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        code = main()
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    finally:
        stdout_val = sys.stdout.getvalue()
        stderr_val = sys.stderr.getvalue()
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        sys.argv = old_argv
    return code, stdout_val, stderr_val


def _find(root, filenames, limit=None):
    """Run find-feature-artifacts against root; return (code, parsed_json, stderr).

    limit=None omits --limit entirely (the no-flag / default path); any
    other value (including 0, including a negative int for the
    error-path tests) is passed through as --limit's raw string,
    unvalidated here -- validation is exactly what these tests exercise.
    """
    argv = [
        "find-feature-artifacts",
        "--filenames", json.dumps(filenames),
        "--root", str(root),
    ]
    if limit is not None:
        argv += ["--limit", str(limit)]
    code, stdout, stderr = _run_main(argv)
    parsed = json.loads(stdout.strip()) if stdout.strip() else None
    return code, parsed, stderr


def _set_mtime(path, epoch_seconds):
    """Set path's mtime (and atime) to an exact epoch-seconds value."""
    import os
    os.utime(str(path), (epoch_seconds, epoch_seconds))


def _build_disagreeing_order_tree(root):
    """A tree where layout order and recency order pick a DIFFERENT
    first record -- the fixture every --limit-caps-the-right-thing test
    needs, so a limit applied to the wrong order would be caught."""
    # Layout order (iter_feature_dirs): 001, then 002, then the new-shape
    # dir -- legacy family first, ascending by NNN.
    dir_001 = root / "specs" / "001-legacy-a"
    dir_001.mkdir(parents=True)
    (dir_001 / "plan.md").write_text("# Plan\n")
    _set_mtime(dir_001 / "plan.md", 2_000_000_000)  # middle

    dir_002 = root / "specs" / "002-legacy-b"
    dir_002.mkdir(parents=True)
    (dir_002 / "plan.md").write_text("# Plan\n")
    _set_mtime(dir_002 / "plan.md", 3_000_000_000)  # newest

    dir_new = root / "specs" / "2026" / "08" / "PROJ-100"
    dir_new.mkdir(parents=True)
    (dir_new / "plan.md").write_text("# Plan\n")
    _set_mtime(dir_new / "plan.md", 1_000_000_000)  # oldest


# ---------------------------------------------------------------------------
# --limit: caps after recency ordering, coherently across all three keys
# ---------------------------------------------------------------------------


class TestFindFeatureArtifactsLimitCapsByRecency(unittest.TestCase):
    def test_limit_1_returns_recency_newest_not_layout_first(self):
        """The layout-first record (001-legacy-a) is NOT the newest
        (002-legacy-b is). --limit 1 must return 002-legacy-b -- a limit
        applied to layout order instead of recency would return the
        wrong one and this assertion would catch it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            _build_disagreeing_order_tree(root)

            code, out, stderr = _find(root, ["plan.md"], limit=1)

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 1)
            self.assertEqual(len(out["matches_by_recency"]), 1)
            self.assertEqual(out["feature_dirs"], ["specs/002-legacy-b"])
            self.assertEqual(out["matches"][0]["feature_dir"], "specs/002-legacy-b")
            self.assertEqual(
                out["matches_by_recency"][0]["feature_dir"], "specs/002-legacy-b"
            )

    def test_limit_2_keeps_matches_in_layout_order_recency_in_recency_order(self):
        """The SAME two-record set, presented two ways: "matches" keeps
        its own layout order (001 before 002) even though 002 is 3rd by
        layout but 1st by recency (the top-2-by-recency set is {002,
        001}, excluding the new-shape dir); "matches_by_recency" stays
        newest-first."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            _build_disagreeing_order_tree(root)

            code, out, stderr = _find(root, ["plan.md"], limit=2)

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            # Top-2 by recency: 002 (3e9), 001 (2e9) -- the new-shape dir
            # (1e9) is excluded.
            self.assertEqual(
                [m["feature_dir"] for m in out["matches_by_recency"]],
                ["specs/002-legacy-b", "specs/001-legacy-a"],
            )
            # Same two records, "matches" own layout order: 001 before 002.
            self.assertEqual(
                [m["feature_dir"] for m in out["matches"]],
                ["specs/001-legacy-a", "specs/002-legacy-b"],
            )
            # feature_dirs is a VIEW of the (capped) "matches", so it
            # follows "matches"'s layout order too.
            self.assertEqual(
                out["feature_dirs"],
                ["specs/001-legacy-a", "specs/002-legacy-b"],
            )

    def test_limit_larger_than_match_count_returns_everything(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            _build_disagreeing_order_tree(root)

            code_limited, out_limited, stderr_limited = _find(
                root, ["plan.md"], limit=1000
            )
            code_unlimited, out_unlimited, stderr_unlimited = _find(
                root, ["plan.md"]
            )

            self.assertEqual(code_limited, EXIT_OK, msg="stderr: " + stderr_limited)
            self.assertEqual(
                code_unlimited, EXIT_OK, msg="stderr: " + stderr_unlimited
            )
            self.assertEqual(out_limited, out_unlimited)
            self.assertEqual(len(out_limited["matches"]), 3)
            self.assertEqual(len(out_limited["matches_by_recency"]), 3)

    def test_limit_0_is_empty_not_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            _build_disagreeing_order_tree(root)

            code, out, stderr = _find(root, ["plan.md"], limit=0)

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(out["matches"], [])
            self.assertEqual(out["feature_dirs"], [])
            self.assertEqual(out["matches_by_recency"], [])
            self.assertEqual(stderr, "")

    def test_negative_limit_is_exit_err(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            _build_disagreeing_order_tree(root)

            code, stdout, stderr = _run_main([
                "find-feature-artifacts",
                "--filenames", json.dumps(["plan.md"]),
                "--root", str(root),
                "--limit", "-1",
            ])

            self.assertEqual(code, EXIT_ERR)
            self.assertIn("--limit must be >= 0", stderr)
            self.assertEqual(stdout, "")

    def test_non_integer_limit_is_exit_err(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            _build_disagreeing_order_tree(root)

            code, stdout, stderr = _run_main([
                "find-feature-artifacts",
                "--filenames", json.dumps(["plan.md"]),
                "--root", str(root),
                "--limit", "not-a-number",
            ])

            self.assertEqual(code, EXIT_ERR)
            self.assertIn("--limit must be an integer", stderr)
            self.assertEqual(stdout, "")

    def test_no_limit_flag_is_byte_identical_to_pre_flag_contract(self):
        """Omitting --limit entirely must not cap anything: every
        discovered record survives, in the SAME order the pre-flag
        contract already committed (617a867 / 049022e)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            _build_disagreeing_order_tree(root)

            code, out, stderr = _find(root, ["plan.md"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 3)
            self.assertEqual(len(out["matches_by_recency"]), 3)
            self.assertEqual(len(out["feature_dirs"]), 3)
            self.assertEqual(
                [m["feature_dir"] for m in out["matches"]],
                [
                    "specs/001-legacy-a",
                    "specs/002-legacy-b",
                    "specs/2026/08/PROJ-100",
                ],
            )
            self.assertEqual(
                [m["feature_dir"] for m in out["matches_by_recency"]],
                [
                    "specs/002-legacy-b",
                    "specs/001-legacy-a",
                    "specs/2026/08/PROJ-100",
                ],
            )

    def test_subprocess_round_trip_limit_1(self):
        """The real Class-B call shape: no shell pipeline, no python3 --
        the single newest record comes straight out of stdout."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            _build_disagreeing_order_tree(root)

            result = subprocess.run(
                [
                    sys.executable,
                    str(_ARTIFACT_HELPER_PY),
                    "find-feature-artifacts",
                    "--filenames", json.dumps(["plan.md"]),
                    "--root", str(root),
                    "--limit", "1",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, EXIT_OK, msg="stderr: " + result.stderr)
            out = json.loads(result.stdout.strip())
            self.assertEqual(len(out["matches"]), 1)
            self.assertEqual(len(out["matches_by_recency"]), 1)
            self.assertEqual(out["feature_dirs"], ["specs/002-legacy-b"])


if __name__ == "__main__":
    unittest.main()
