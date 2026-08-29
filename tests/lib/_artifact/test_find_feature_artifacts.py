"""Tests for src/devforge/lib/_artifact/_cmds_find_artifacts.py
(find-feature-artifacts verb for artifact_helper).

91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 1b: this verb is the
ONE shared discovery primitive that will replace the depth-1
`specs/*/...` globs several command specs run themselves. It delegates
ALL specs/-layout scanning to _shared/feature_alloc.py's
iter_feature_dirs / find_feature_dirs_with -- these tests exist to prove
that delegation actually reaches BOTH directory shapes (legacy
specs/NNN-slug/ and the Phase-3 forward specs/YYYY/MM/TICKET/), which is
the entire point of building this verb before Phase 3 ships.

This file pins the ORIGINAL committed contract (commit 617a867): the
match/feature_dirs shape, layout order, dedup, glob matching, and error
handling. The mtime + recency-ordering follow-up (added after 617a867,
per plan 91 Phase 1b's Class-B gap) lives in its own sibling file,
test_find_feature_artifacts_recency.py -- kept separate so neither file
grows past this repository's 600-line test-file split threshold, and
each file's own docstring stays a description of ONE coherent concern
rather than needing "and" to summarize it.

Coverage:
  - legacy-shape tree: single hit found.
  - new-shape tree: single hit found (the load-bearing case -- without
    this, the verb is no better than the depth-1 globs it replaces).
  - mixed tree: both found, in iter_feature_dirs's documented order
    (legacy family first, ascending by NNN; then new-shape, ascending by
    (YYYY, MM, leaf)).
  - multi-filename lookup: hits from each requested filename; a directory
    holding files matching two DIFFERENT requested names contributes two
    distinct match entries but ONE deduplicated feature_dirs entry.
  - glob-suffix pattern (e.g. "*-seed.json"): matches every file in a
    feature dir ending that way, in the dir's own listing order.
  - overlapping patterns matching the SAME file (an exact name repeated,
    or a literal name that also satisfies a supplied glob) collapse to
    exactly one match -- the (feature_dir, file) dedup contract.
  - no match: empty result, exit 0, no exception (a real "no seed yet"
    outcome, never an error).
  - specs/ absent entirely: same empty-result, exit-0 contract.
  - wrapper mode: specs/ is resolved under the INSTALL root, never the
    nested source root (matches commit-artifacts's own D2 convention in
    this same package).
  - malformed input: bad --filenames JSON, --filenames not a JSON array,
    and blank array entries (benign skip, not an error).
  - a REAL CLI round-trip via subprocess against artifact_helper.py,
    parsing actual stdout JSON -- not a hand-authored fixture.
  - the two pure internal predicates (_is_glob_pattern, _relative_posix)
    directly.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap — make _artifact importable (mirrors test_commit_artifacts.py)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LIB_DIR = str(_REPO_ROOT / "src" / "devforge" / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _artifact._cli import main  # noqa: E402
from _artifact._cmds_find_artifacts import (  # noqa: E402
    EXIT_ERR,
    EXIT_OK,
    _is_glob_pattern,
    _relative_posix,
)

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


def _find(root, filenames):
    """Run find-feature-artifacts against root; return (code, parsed_json, stderr)."""
    code, stdout, stderr = _run_main([
        "find-feature-artifacts",
        "--filenames", json.dumps(filenames),
        "--root", str(root),
    ])
    parsed = json.loads(stdout.strip()) if stdout.strip() else None
    return code, parsed, stderr


# ---------------------------------------------------------------------------
# Legacy shape
# ---------------------------------------------------------------------------


class TestFindFeatureArtifactsLegacyShape(unittest.TestCase):
    def test_legacy_tree_hit_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            feature_dir = root / "specs" / "003-foo-bar"
            feature_dir.mkdir(parents=True)
            (feature_dir / "research-handoff.json").write_text("{}")

            code, out, stderr = _find(root, ["research-handoff.json"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 1)
            self.assertEqual(out["matches"][0]["feature_dir"], "specs/003-foo-bar")
            self.assertEqual(
                out["matches"][0]["file"],
                "specs/003-foo-bar/research-handoff.json",
            )
            self.assertEqual(out["matches"][0]["filename"], "research-handoff.json")
            self.assertEqual(out["feature_dirs"], ["specs/003-foo-bar"])


# ---------------------------------------------------------------------------
# New shape — the load-bearing case
# ---------------------------------------------------------------------------


class TestFindFeatureArtifactsNewShape(unittest.TestCase):
    def test_new_shape_tree_hit_found(self):
        """A specs/YYYY/MM/TICKET/ hit is found -- the whole point of the verb.

        A flat depth-1 scan (what this verb replaces) enumerates YEAR
        directories under specs/ and can never see this file at all.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            feature_dir = root / "specs" / "2026" / "08" / "PROJ-123"
            feature_dir.mkdir(parents=True)
            (feature_dir / "grill.md").write_text("# Grill\n")

            code, out, stderr = _find(root, ["grill.md"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 1)
            self.assertEqual(
                out["matches"][0]["feature_dir"], "specs/2026/08/PROJ-123"
            )
            self.assertEqual(
                out["matches"][0]["file"], "specs/2026/08/PROJ-123/grill.md"
            )
            self.assertEqual(out["feature_dirs"], ["specs/2026/08/PROJ-123"])


# ---------------------------------------------------------------------------
# Mixed tree — documented order
# ---------------------------------------------------------------------------


class TestFindFeatureArtifactsMixedShapeOrder(unittest.TestCase):
    def test_mixed_tree_both_found_in_accessor_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()

            legacy_dir = root / "specs" / "001-legacy-hit"
            legacy_dir.mkdir(parents=True)
            (legacy_dir / "plan.md").write_text("# Plan\n")

            new_dir = root / "specs" / "2026" / "08" / "PROJ-100"
            new_dir.mkdir(parents=True)
            (new_dir / "plan.md").write_text("# Plan\n")

            # Distractor: legacy dir with no plan.md, must not appear.
            (root / "specs" / "002-legacy-miss").mkdir(parents=True)

            code, out, stderr = _find(root, ["plan.md"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            # iter_feature_dirs's documented order: legacy family first.
            self.assertEqual(
                [m["feature_dir"] for m in out["matches"]],
                ["specs/001-legacy-hit", "specs/2026/08/PROJ-100"],
            )
            self.assertEqual(
                out["feature_dirs"],
                ["specs/001-legacy-hit", "specs/2026/08/PROJ-100"],
            )


# ---------------------------------------------------------------------------
# Multi-filename lookup
# ---------------------------------------------------------------------------


class TestFindFeatureArtifactsMultiFilename(unittest.TestCase):
    def test_two_filenames_both_matched_dir_deduplicated(self):
        """A dir holding BOTH requested filenames contributes two distinct
        match entries (different files) but ONE feature_dirs entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            feature_dir = root / "specs" / "005-both"
            feature_dir.mkdir(parents=True)
            (feature_dir / "research-handoff.json").write_text("{}")
            (feature_dir / "discover-handoff.json").write_text("{}")

            code, out, stderr = _find(
                root, ["research-handoff.json", "discover-handoff.json"]
            )

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 2)
            filenames = {m["filename"] for m in out["matches"]}
            self.assertEqual(
                filenames, {"research-handoff.json", "discover-handoff.json"}
            )
            self.assertTrue(
                all(m["feature_dir"] == "specs/005-both" for m in out["matches"])
            )
            # Deduplicated: ONE directory entry, not two.
            self.assertEqual(out["feature_dirs"], ["specs/005-both"])

    def test_only_one_of_two_filenames_present(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            feature_dir = root / "specs" / "006-research-only"
            feature_dir.mkdir(parents=True)
            (feature_dir / "research-handoff.json").write_text("{}")

            code, out, stderr = _find(
                root, ["research-handoff.json", "discover-handoff.json"]
            )

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 1)
            self.assertEqual(out["matches"][0]["filename"], "research-handoff.json")

    def test_repeated_literal_name_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            feature_dir = root / "specs" / "007-repeat"
            feature_dir.mkdir(parents=True)
            (feature_dir / "spec.md").write_text("# Spec\n")

            code, out, stderr = _find(root, ["spec.md", "spec.md"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 1)


# ---------------------------------------------------------------------------
# Glob-suffix pattern
# ---------------------------------------------------------------------------


class TestFindFeatureArtifactsGlobPattern(unittest.TestCase):
    def test_seed_suffix_glob_matches_every_producer(self):
        """/devforge:plan's real need: '*-seed.json' matches ANY producer,
        without this verb needing to enumerate them by name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            feature_dir = root / "specs" / "008-seeds"
            feature_dir.mkdir(parents=True)
            (feature_dir / "grill-seed.json").write_text('{"target_stage": "plan"}')
            (feature_dir / "spec-check-seed.json").write_text(
                '{"target_stage": "spec"}'
            )
            (feature_dir / "spec.md").write_text("# Spec\n")  # must NOT match

            code, out, stderr = _find(root, ["*-seed.json"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 2)
            # Directory-listing order: alphabetical ("grill-..." < "spec-check-...").
            self.assertEqual(
                [m["filename"] for m in out["matches"]],
                ["grill-seed.json", "spec-check-seed.json"],
            )

    def test_overlapping_literal_and_glob_pattern_deduplicated(self):
        """The SAME file matching both a literal name and a glob pattern
        supplied together contributes exactly one match."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            feature_dir = root / "specs" / "009-overlap"
            feature_dir.mkdir(parents=True)
            (feature_dir / "grill-seed.json").write_text("{}")

            code, out, stderr = _find(
                root, ["grill-seed.json", "*-seed.json"]
            )

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 1)

    def test_new_shape_tree_glob_pattern_matches(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            feature_dir = root / "specs" / "2026" / "08" / "PROJ-500"
            feature_dir.mkdir(parents=True)
            (feature_dir / "fix-seed.json").write_text("{}")

            code, out, stderr = _find(root, ["*-seed.json"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 1)
            self.assertEqual(
                out["matches"][0]["feature_dir"], "specs/2026/08/PROJ-500"
            )


# ---------------------------------------------------------------------------
# No match / specs/ absent
# ---------------------------------------------------------------------------


class TestFindFeatureArtifactsNoMatch(unittest.TestCase):
    def test_no_match_in_existing_tree_is_empty_not_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "specs" / "001-nothing-here").mkdir(parents=True)

            code, out, stderr = _find(root, ["research-handoff.json"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(out["matches"], [])
            self.assertEqual(out["feature_dirs"], [])
            self.assertEqual(stderr, "")


class TestFindFeatureArtifactsSpecsAbsent(unittest.TestCase):
    def test_specs_dir_absent_entirely_is_empty_not_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            # No specs/ directory created at all.

            code, out, stderr = _find(root, ["research-handoff.json"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(out["matches"], [])
            self.assertEqual(out["feature_dirs"], [])
            self.assertEqual(stderr, "")


# ---------------------------------------------------------------------------
# Wrapper mode
# ---------------------------------------------------------------------------


class TestFindFeatureArtifactsWrapperMode(unittest.TestCase):
    def test_wrapper_mode_resolves_specs_under_install_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            install_root = Path(tmpdir).resolve()
            source_root = install_root / "acme-product-app"
            source_root.mkdir(parents=True)

            devforge_dir = install_root / ".devforge"
            devforge_dir.mkdir(parents=True)
            (devforge_dir / "project-config.json").write_text(
                json.dumps({"PROJECT_ROOT": "acme-product-app"})
            )

            # Artifact lives under the INSTALL root's specs/, never inside
            # the nested source repo.
            feature_dir = install_root / "specs" / "010-wrapper"
            feature_dir.mkdir(parents=True)
            (feature_dir / "review.md").write_text("# Review\n")

            # A decoy specs/ inside the source root must NOT be scanned.
            decoy = source_root / "specs" / "999-decoy"
            decoy.mkdir(parents=True)
            (decoy / "review.md").write_text("# Decoy\n")

            code, out, stderr = _find(install_root, ["review.md"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 1)
            self.assertEqual(out["matches"][0]["feature_dir"], "specs/010-wrapper")


# ---------------------------------------------------------------------------
# Malformed input
# ---------------------------------------------------------------------------


class TestFindFeatureArtifactsMalformedInput(unittest.TestCase):
    def test_bad_json_is_exit_err(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            code, stdout, stderr = _run_main([
                "find-feature-artifacts",
                "--filenames", "not valid json",
                "--root", tmpdir,
            ])
            self.assertEqual(code, EXIT_ERR)
            self.assertIn("not valid JSON", stderr)
            self.assertEqual(stdout, "")

    def test_non_array_json_is_exit_err(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            code, stdout, stderr = _run_main([
                "find-feature-artifacts",
                "--filenames", json.dumps({"a": 1}),
                "--root", tmpdir,
            ])
            self.assertEqual(code, EXIT_ERR)
            self.assertIn("must be a JSON array", stderr)
            self.assertEqual(stdout, "")

    def test_blank_entries_are_benign_skip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            feature_dir = root / "specs" / "011-blank"
            feature_dir.mkdir(parents=True)
            (feature_dir / "spec.md").write_text("# Spec\n")

            code, out, stderr = _find(root, ["", "   ", "spec.md"])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(len(out["matches"]), 1)
            self.assertEqual(out["matches"][0]["filename"], "spec.md")

    def test_empty_filenames_array_is_valid_empty_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()
            (root / "specs" / "012-x").mkdir(parents=True)

            code, out, stderr = _find(root, [])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            self.assertEqual(out["matches"], [])
            self.assertEqual(out["feature_dirs"], [])


# ---------------------------------------------------------------------------
# Real CLI round-trip (subprocess) — this repo's rule for anything another
# tool parses: drive the real producer, don't hand-author the fixture.
# ---------------------------------------------------------------------------


class TestFindFeatureArtifactsRealCliRoundTrip(unittest.TestCase):
    def test_subprocess_round_trip_legacy_and_new_shape(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir).resolve()

            legacy_dir = root / "specs" / "001-legacy"
            legacy_dir.mkdir(parents=True)
            (legacy_dir / "research-handoff.json").write_text("{}")

            new_dir = root / "specs" / "2026" / "08" / "PROJ-777"
            new_dir.mkdir(parents=True)
            (new_dir / "research-handoff.json").write_text("{}")

            result = subprocess.run(
                [
                    sys.executable,
                    str(_ARTIFACT_HELPER_PY),
                    "find-feature-artifacts",
                    "--filenames", json.dumps(["research-handoff.json"]),
                    "--root", str(root),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, EXIT_OK, msg="stderr: " + result.stderr)
            out = json.loads(result.stdout.strip())
            self.assertEqual(
                [m["feature_dir"] for m in out["matches"]],
                ["specs/001-legacy", "specs/2026/08/PROJ-777"],
            )

    def test_subprocess_round_trip_no_match_exit_ok(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = subprocess.run(
                [
                    sys.executable,
                    str(_ARTIFACT_HELPER_PY),
                    "find-feature-artifacts",
                    "--filenames", json.dumps(["research-handoff.json"]),
                    "--root", tmpdir,
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, EXIT_OK, msg="stderr: " + result.stderr)
            out = json.loads(result.stdout.strip())
            self.assertEqual(out["matches"], [])
            self.assertEqual(out["feature_dirs"], [])


# ---------------------------------------------------------------------------
# Pure internal predicates
# ---------------------------------------------------------------------------


class TestIsGlobPattern(unittest.TestCase):
    def test_literal_names_are_not_glob(self):
        for name in ["spec.md", "research-handoff.json", "grill-seed.json"]:
            self.assertFalse(_is_glob_pattern(name))

    def test_star_question_bracket_are_glob(self):
        self.assertTrue(_is_glob_pattern("*-seed.json"))
        self.assertTrue(_is_glob_pattern("spec?.md"))
        self.assertTrue(_is_glob_pattern("spec[0-9].md"))

    def test_empty_string_is_not_glob(self):
        self.assertFalse(_is_glob_pattern(""))


class TestRelativePosix(unittest.TestCase):
    def test_relative_posix_forward_slash(self):
        root = Path("/tmp/install-root")
        path = root / "specs" / "2026" / "08" / "PROJ-1"
        self.assertEqual(
            _relative_posix(path, root), "specs/2026/08/PROJ-1"
        )


if __name__ == "__main__":
    unittest.main()
