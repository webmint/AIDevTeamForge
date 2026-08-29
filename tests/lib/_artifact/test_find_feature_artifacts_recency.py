"""Tests for the mtime + recency-ordering follow-up on find-feature-artifacts
(src/devforge/lib/_artifact/_cmds_find_artifacts.py), added after commit
617a867.

91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 1b's 26-site inventory
splits into two classes. Class A finds a named or patterned file
(/devforge:research, /devforge:discover, /devforge:plan, /devforge:specify's
seed globs) -- test_find_feature_artifacts.py already covers this, pinning
617a867's committed contract. Class B resolves the MOST-RECENTLY-MODIFIED
feature directory carrying a sentinel (/devforge:review, /devforge:fix,
/devforge:verify, /devforge:finalize, /devforge:summarize,
/devforge:spec-check; /devforge:audit additionally windows to the last 90
days before taking the 5 most recent) -- this file covers the mtime_ts /
mtime_iso fields and the matches_by_recency output key that make Class B
answerable from this verb's own output, with no second tool call.

Kept in its OWN file (with its own small path-bootstrap + harness,
matching the precedent tests/lib/_specify/test_find_handoffs_require.py
already sets for a concern-scoped test file over a function covered
elsewhere too) rather than appended to test_find_feature_artifacts.py, so
neither file crosses this repository's 600-line test-file split threshold.

Coverage:
  - mtime_ts / mtime_iso are present and correct for a legacy-shape AND a
    new-shape hit (controlled via os.utime, not creation-order timing).
  - matches_by_recency actually reorders: built from mtimes that
    DELIBERATELY invert iter_feature_dirs's layout order, so a test that
    happened to pass on a no-op sort would fail here.
  - the 617a867 contract is unbroken: "matches" / "feature_dirs" keep
    their exact committed order and meaning with the new fields present.
  - a 90-day window is computable straight from matches_by_recency (a
    plain mtime_ts >= cutoff filter), demonstrated end to end.
  - a file that vanishes between discovery and this verb's own mtime stat
    (a simulated TOCTOU race, _file_mtime patched for one path only)
    drops silently from every output view; exit stays 0, no exception.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

# ---------------------------------------------------------------------------
# Path bootstrap — make _artifact importable (mirrors test_commit_artifacts.py
# and test_find_feature_artifacts.py)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LIB_DIR = str(_REPO_ROOT / "src" / "devforge" / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

import _artifact._cmds_find_artifacts as _find_artifacts_mod  # noqa: E402
from _artifact._cli import main  # noqa: E402
from _artifact._cmds_find_artifacts import EXIT_OK  # noqa: E402


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


def _find(root, filenames):
    """Run find-feature-artifacts against root; return (code, parsed_json, stderr)."""
    code, stdout, stderr = _run_main([
        "find-feature-artifacts",
        "--filenames", json.dumps(filenames),
        "--root", str(root),
    ])
    parsed = json.loads(stdout.strip()) if stdout.strip() else None
    return code, parsed, stderr


def _set_mtime(path, epoch_seconds):
    """Set path's mtime (and atime) to an exact epoch-seconds value."""
    os.utime(str(path), (epoch_seconds, epoch_seconds))


def _expected_iso(epoch_seconds):
    """Independently compute the expected mtime_iso string for epoch_seconds."""
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


# ---------------------------------------------------------------------------
# mtime presence + correctness (both layout shapes)
# ---------------------------------------------------------------------------


class TestFindFeatureArtifactsMtimePresence(unittest.TestCase):
    def test_mtime_correct_on_legacy_shape_hit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            feature_dir = root / "specs" / "001-legacy"
            feature_dir.mkdir(parents=True)
            target = feature_dir / "spec.md"
            target.write_text("# Spec\n")
            fixed_ts = 1735689600.0  # 2025-01-01T00:00:00Z
            _set_mtime(target, fixed_ts)

            code, out, stderr = _find(root, ["spec.md"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 1)
            self.assertEqual(out["matches"][0]["mtime_ts"], fixed_ts)
            self.assertEqual(
                out["matches"][0]["mtime_iso"], _expected_iso(fixed_ts)
            )
            self.assertEqual(out["matches"][0]["mtime_iso"], "2025-01-01T00:00:00Z")

    def test_mtime_correct_on_new_shape_hit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            feature_dir = root / "specs" / "2026" / "08" / "PROJ-900"
            feature_dir.mkdir(parents=True)
            target = feature_dir / "spec.md"
            target.write_text("# Spec\n")
            fixed_ts = 1767225600.0  # 2026-01-01T00:00:00Z
            _set_mtime(target, fixed_ts)

            code, out, stderr = _find(root, ["spec.md"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 1)
            self.assertEqual(out["matches"][0]["mtime_ts"], fixed_ts)
            self.assertEqual(
                out["matches"][0]["mtime_iso"], _expected_iso(fixed_ts)
            )


# ---------------------------------------------------------------------------
# matches_by_recency: proves an actual sort, not a passthrough
# ---------------------------------------------------------------------------


class TestFindFeatureArtifactsRecencyOrdering(unittest.TestCase):
    def test_recency_order_inverts_layout_order(self):
        """Construct mtimes that DELIBERATELY disagree with layout order,
        so a no-op "sort" (matches copied unchanged) would fail this test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()

            # Layout order (iter_feature_dirs): 001, then 002, then the
            # new-shape dir -- legacy family first, ascending by NNN.
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

            code, out, stderr = _find(root, ["plan.md"])
            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)

            # Layout order unaffected by mtime (the 617a867 contract).
            self.assertEqual(
                [m["feature_dir"] for m in out["matches"]],
                [
                    "specs/001-legacy-a",
                    "specs/002-legacy-b",
                    "specs/2026/08/PROJ-100",
                ],
            )

            # Recency order: newest first -- 002 (3e9), then 001 (2e9),
            # then the new-shape dir (1e9). This DIFFERS from layout
            # order in its first two entries, proving the sort is real.
            self.assertEqual(
                [m["feature_dir"] for m in out["matches_by_recency"]],
                [
                    "specs/002-legacy-b",
                    "specs/001-legacy-a",
                    "specs/2026/08/PROJ-100",
                ],
            )
            self.assertNotEqual(
                [m["feature_dir"] for m in out["matches"]],
                [m["feature_dir"] for m in out["matches_by_recency"]],
            )

    def test_recency_tie_broken_by_file_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            same_ts = 1_500_000_000

            dir_a = root / "specs" / "003-tie-a"
            dir_a.mkdir(parents=True)
            (dir_a / "plan.md").write_text("# Plan\n")
            _set_mtime(dir_a / "plan.md", same_ts)

            dir_b = root / "specs" / "004-tie-b"
            dir_b.mkdir(parents=True)
            (dir_b / "plan.md").write_text("# Plan\n")
            _set_mtime(dir_b / "plan.md", same_ts)

            code, out, stderr = _find(root, ["plan.md"])
            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            # Tie broken by "file" string, ascending -- deterministic.
            self.assertEqual(
                [m["file"] for m in out["matches_by_recency"]],
                sorted(m["file"] for m in out["matches"]),
            )


# ---------------------------------------------------------------------------
# 90-day window: demonstrably computable from the output alone
# ---------------------------------------------------------------------------


class TestFindFeatureArtifactsNinetyDayWindow(unittest.TestCase):
    def test_ninety_day_window_and_top_n_from_matches_by_recency(self):
        """/devforge:audit's real need: glob within the last 90 days, take
        the 5 most recent. Demonstrate both steps from the verb's own
        output -- no second tool call, no re-stat."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            now = time.time()
            day = 86400

            # Two recent hits (within 90 days), one stale hit (well past).
            recent_a = root / "specs" / "010-recent-a"
            recent_a.mkdir(parents=True)
            (recent_a / "review.md").write_text("# Review\n")
            _set_mtime(recent_a / "review.md", now - (10 * day))

            recent_b = root / "specs" / "011-recent-b"
            recent_b.mkdir(parents=True)
            (recent_b / "review.md").write_text("# Review\n")
            _set_mtime(recent_b / "review.md", now - (40 * day))

            stale = root / "specs" / "012-stale"
            stale.mkdir(parents=True)
            (stale / "review.md").write_text("# Review\n")
            _set_mtime(stale / "review.md", now - (200 * day))

            code, out, stderr = _find(root, ["review.md"])
            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)

            cutoff = now - (90 * day)
            within_window = [
                m for m in out["matches_by_recency"] if m["mtime_ts"] >= cutoff
            ]
            top_5_within_window = within_window[:5]

            self.assertEqual(
                [m["feature_dir"] for m in top_5_within_window],
                ["specs/010-recent-a", "specs/011-recent-b"],
            )
            self.assertNotIn(
                "specs/012-stale",
                [m["feature_dir"] for m in top_5_within_window],
            )


# ---------------------------------------------------------------------------
# Vanishing-file race: degrade, never raise
# ---------------------------------------------------------------------------


class TestFindFeatureArtifactsVanishingFileRace(unittest.TestCase):
    def test_file_vanishing_between_discovery_and_stat_drops_silently(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()

            vanishing_dir = root / "specs" / "001-vanishing"
            vanishing_dir.mkdir(parents=True)
            vanishing_file = vanishing_dir / "spec.md"
            vanishing_file.write_text("# Spec\n")

            surviving_dir = root / "specs" / "002-surviving"
            surviving_dir.mkdir(parents=True)
            surviving_file = surviving_dir / "spec.md"
            surviving_file.write_text("# Spec\n")

            real_file_mtime = _find_artifacts_mod._file_mtime

            def _flaky_mtime(path):
                # Simulate the file having vanished by the time this verb
                # stats it -- the file still passed the earlier is_file()
                # discovery check (find_feature_dirs_with already ran).
                if path == vanishing_file:
                    return None
                return real_file_mtime(path)

            with mock.patch.object(
                _find_artifacts_mod, "_file_mtime", side_effect=_flaky_mtime
            ):
                code, out, stderr = _find(root, ["spec.md"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 1)
            self.assertEqual(out["matches"][0]["feature_dir"], "specs/002-surviving")
            self.assertEqual(out["feature_dirs"], ["specs/002-surviving"])
            self.assertEqual(len(out["matches_by_recency"]), 1)
            self.assertEqual(
                out["matches_by_recency"][0]["feature_dir"], "specs/002-surviving"
            )

    def test_glob_matched_file_vanishing_drops_silently(self):
        """Same race, but through the glob-matching loop rather than the
        literal-name / find_feature_dirs_with path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()

            feature_dir = root / "specs" / "005-glob-race"
            feature_dir.mkdir(parents=True)
            vanishing_file = feature_dir / "grill-seed.json"
            vanishing_file.write_text("{}")
            surviving_file = feature_dir / "spec-check-seed.json"
            surviving_file.write_text("{}")

            real_file_mtime = _find_artifacts_mod._file_mtime

            def _flaky_mtime(path):
                if path == vanishing_file:
                    return None
                return real_file_mtime(path)

            with mock.patch.object(
                _find_artifacts_mod, "_file_mtime", side_effect=_flaky_mtime
            ):
                code, out, stderr = _find(root, ["*-seed.json"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 1)
            self.assertEqual(out["matches"][0]["filename"], "spec-check-seed.json")


# ---------------------------------------------------------------------------
# 617a867 contract regression: existing keys, meaning, and order unbroken
# ---------------------------------------------------------------------------


class TestFindFeatureArtifactsExistingContractUnbroken(unittest.TestCase):
    def test_original_three_keys_still_present_and_unchanged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            feature_dir = root / "specs" / "001-legacy"
            feature_dir.mkdir(parents=True)
            (feature_dir / "research-handoff.json").write_text("{}")

            code, out, stderr = _find(root, ["research-handoff.json"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            match = out["matches"][0]
            self.assertEqual(match["feature_dir"], "specs/001-legacy")
            self.assertEqual(
                match["file"], "specs/001-legacy/research-handoff.json"
            )
            self.assertEqual(match["filename"], "research-handoff.json")
            self.assertEqual(out["feature_dirs"], ["specs/001-legacy"])
            # New keys are additive: present alongside the original three,
            # never replacing them.
            self.assertIn("mtime_ts", match)
            self.assertIn("mtime_iso", match)
            self.assertIn("matches_by_recency", out)

    def test_mixed_tree_layout_order_unchanged_by_mtime_addition(self):
        """Re-run of the ORIGINAL mixed-tree order test: layout order must
        be exactly what 617a867 committed, mtimes notwithstanding."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()

            legacy_dir = root / "specs" / "001-legacy-hit"
            legacy_dir.mkdir(parents=True)
            (legacy_dir / "plan.md").write_text("# Plan\n")
            _set_mtime(legacy_dir / "plan.md", 1_000_000_000)  # oldest

            new_dir = root / "specs" / "2026" / "08" / "PROJ-100"
            new_dir.mkdir(parents=True)
            (new_dir / "plan.md").write_text("# Plan\n")
            _set_mtime(new_dir / "plan.md", 3_000_000_000)  # newest

            code, out, stderr = _find(root, ["plan.md"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(
                [m["feature_dir"] for m in out["matches"]],
                ["specs/001-legacy-hit", "specs/2026/08/PROJ-100"],
            )
            self.assertEqual(
                out["feature_dirs"],
                ["specs/001-legacy-hit", "specs/2026/08/PROJ-100"],
            )


if __name__ == "__main__":
    unittest.main()
