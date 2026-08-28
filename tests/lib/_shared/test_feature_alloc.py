"""Tests for src/devforge/lib/_shared/feature_alloc.py.

Coverage:
  next_spec_number      — fresh repo -> 1; existing specs/003-* -> 4;
                           non-NNN dirs ignored; wrapper-root resolution.
  allocate_feature_dir  — fresh repo -> 001-<slug>; existing specs/003-* ->
                           004-<slug>; slug collision allowed (OQ-4);
                           invalid slug rejected; existing-target-dir
                           failure is loud (no silent reuse); result dict
                           shape.
  decide_branch_action  — all three arms (create / keep-spec / keep-other);
                           missing spec_number/slug on the default branch;
                           keep-spec and keep-other render IDENTICAL text
                           (the original /specify wording, preserved).
  specs_root_for        — repo-root and wrapper-root resolution; pure path
                           arithmetic (no stat, safe on nonexistent paths);
                           composes with iter_feature_dirs.
  iter_feature_dirs      — legacy-only / new-shape-only / mixed trees;
                           specs/ absent or empty; a 9999-too-many-digits
                           dir claimed by neither arm; stray non-directory
                           entries at every level ignored; documented sort
                           order (legacy family first, then new-shape);
                           an unreadable specs/ (or an unreadable ancestor)
                           returns [] rather than raising; symlinked
                           feature dirs are followed, dangling ones
                           excluded; near-miss name shapes (0001-x, 12345,
                           202-6, 2026-08) classified by exactly one arm
                           or none, never both.
  find_feature_dirs_with — sentinel-file filter on top of
                           iter_feature_dirs; a dir lacking the sentinel is
                           excluded, and so is a dir holding a DIRECTORY of
                           that name rather than a file; a symlinked
                           sentinel file matches, a dangling one does not.

All tests use real tempfile-backed filesystem trees — no hand-fabricated
JSON, no mocked Path objects (except the one deliberate race-simulation
test, which patches next_spec_number specifically to force a collision
that cannot occur through normal sequential allocation).

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# ---------------------------------------------------------------------------
# Permission-guarded test gate.
#
# chmod(..., 0o000) only enforces anything under POSIX, and only for a
# non-root user (root bypasses all permission checks, so the assertion
# would pass for the wrong reason -- it would prove nothing about the
# OSError-handling code path under test). No prior test in this file
# exercises permission errors; this constant is the first such gate.
# ---------------------------------------------------------------------------

_SKIP_PERMISSION_TESTS = os.name != "posix" or (
    hasattr(os, "geteuid") and os.geteuid() == 0
)
_PERMISSION_SKIP_REASON = (
    "permission enforcement requires a non-root POSIX user"
)

# ---------------------------------------------------------------------------
# Path setup (mirrors tests/lib/_shared/test_feature_scope.py).
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _shared.feature_alloc import (  # noqa: E402
    FEATURE_NAME_RE,
    MONTH_DIR_RE,
    SPEC_NUMBER_DIR_RE,
    SPEC_NUMBER_WIDTH,
    SPECS_ROOT_DEFAULT,
    YEAR_DIR_RE,
    allocate_feature_dir,
    decide_branch_action,
    find_feature_dirs_with,
    iter_feature_dirs,
    next_spec_number,
    specs_root_for,
)


# ---------------------------------------------------------------------------
# next_spec_number
# ---------------------------------------------------------------------------


class TestNextSpecNumber(unittest.TestCase):
    def test_fresh_repo_returns_1(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            self.assertEqual(next_spec_number(devforge_dir), 1)

    def test_no_specs_dir_at_all_returns_1(self):
        with tempfile.TemporaryDirectory() as td:
            # Not even the repo root's specs/ exists.
            devforge_dir = Path(td) / "sub" / ".devforge"
            devforge_dir.mkdir(parents=True)
            self.assertEqual(next_spec_number(devforge_dir), 1)

    def test_existing_specs_003_returns_4(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            (specs_root / "001-foo").mkdir(parents=True)
            (specs_root / "003-bar").mkdir(parents=True)
            self.assertEqual(next_spec_number(devforge_dir), 4)

    def test_non_nnn_dirs_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            (specs_root / "002-real").mkdir(parents=True)
            (specs_root / "not-a-spec-dir").mkdir(parents=True)
            (specs_root / "9999-too-many-digits").mkdir(parents=True)
            self.assertEqual(next_spec_number(devforge_dir), 3)

    def test_files_in_specs_root_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            specs_root.mkdir()
            (specs_root / "005-a-file-not-a-dir").write_text("x")
            self.assertEqual(next_spec_number(devforge_dir), 1)

    def test_wrapper_root_resolution(self):
        """devforge_dir's PARENT is the repo/install root, matching wrapper mode."""
        with tempfile.TemporaryDirectory() as td:
            wrapper_root = Path(td) / "wrapper-install-root"
            devforge_dir = wrapper_root / ".devforge"
            devforge_dir.mkdir(parents=True)
            specs_root = wrapper_root / SPECS_ROOT_DEFAULT
            (specs_root / "007-x").mkdir(parents=True)
            self.assertEqual(next_spec_number(devforge_dir), 8)
            # Confirm it did NOT look one level further up (outside wrapper root).
            outer_specs = Path(td) / SPECS_ROOT_DEFAULT
            self.assertFalse(outer_specs.exists())


# ---------------------------------------------------------------------------
# allocate_feature_dir
# ---------------------------------------------------------------------------


class TestAllocateFeatureDir(unittest.TestCase):
    def test_fresh_repo_allocates_001(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "add-dark-mode")
            self.assertIsNone(error)
            self.assertEqual(result["number"], 1)
            self.assertEqual(result["formatted_number"], "001")
            self.assertEqual(result["slug"], "add-dark-mode")
            self.assertEqual(result["dirname"], "001-add-dark-mode")
            self.assertTrue(result["created"])
            expected_path = Path(td).resolve() / SPECS_ROOT_DEFAULT / "001-add-dark-mode"
            self.assertEqual(Path(result["path"]), expected_path)
            self.assertTrue(expected_path.is_dir())

    def test_existing_specs_003_allocates_004(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            (specs_root / "003-prior-feature").mkdir(parents=True)
            result, error = allocate_feature_dir(devforge_dir, "next-feature-here")
            self.assertIsNone(error)
            self.assertEqual(result["number"], 4)
            self.assertEqual(result["dirname"], "004-next-feature-here")
            self.assertTrue((specs_root / "004-next-feature-here").is_dir())

    def test_slug_collision_across_nnn_is_allowed(self):
        """OQ-4: same slug, different NNN — no error, two distinct dirs."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result1, error1 = allocate_feature_dir(devforge_dir, "same-slug-twice")
            self.assertIsNone(error1)
            result2, error2 = allocate_feature_dir(devforge_dir, "same-slug-twice")
            self.assertIsNone(error2)
            self.assertNotEqual(result1["number"], result2["number"])
            self.assertEqual(result1["slug"], result2["slug"])
            self.assertEqual(result1["dirname"], "001-same-slug-twice")
            self.assertEqual(result2["dirname"], "002-same-slug-twice")
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            self.assertTrue((specs_root / "001-same-slug-twice").is_dir())
            self.assertTrue((specs_root / "002-same-slug-twice").is_dir())

    def test_invalid_slug_single_word_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "onlyoneword")
            self.assertEqual(result, {})
            self.assertIsNotNone(error)
            self.assertIn("invalid slug", error)
            # No directory was created.
            self.assertFalse((Path(td) / SPECS_ROOT_DEFAULT).exists())

    def test_invalid_slug_uppercase_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "Add-DarkMode")
            self.assertEqual(result, {})
            self.assertIsNotNone(error)

    def test_invalid_slug_too_many_words_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(
                devforge_dir, "way-too-many-words-here-now",
            )
            self.assertEqual(result, {})
            self.assertIsNotNone(error)

    def test_invalid_slug_empty_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "")
            self.assertEqual(result, {})
            self.assertIsNotNone(error)

    def test_existing_target_dir_failure_is_loud(self):
        """Race/retry: the computed target already exists -> no silent reuse."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            # Pre-create the exact dir a fresh allocation would compute by
            # patching next_spec_number to force the collision — this
            # cannot happen through normal sequential allocation (the
            # scanner would have counted a real NNN-prefixed dir and moved
            # the number forward), so simulating the TOCTOU race requires
            # forcing the return value directly.
            (specs_root / "001-clashing-slug").mkdir(parents=True)
            with mock.patch(
                "_shared.feature_alloc.next_spec_number", return_value=1,
            ):
                result, error = allocate_feature_dir(devforge_dir, "clashing-slug")
            self.assertEqual(result, {})
            self.assertIsNotNone(error)
            self.assertIn("already exists", error)
            self.assertIn("refusing to reuse", error)

    def test_valid_slug_boundaries_2_and_4_words(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "two-words")
            self.assertIsNone(error)
            self.assertEqual(result["dirname"], "001-two-words")

        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "one-two-three-four")
            self.assertIsNone(error)
            self.assertEqual(result["dirname"], "001-one-two-three-four")

    def test_wrapper_root_resolution(self):
        with tempfile.TemporaryDirectory() as td:
            wrapper_root = Path(td) / "wrapper-install-root"
            devforge_dir = wrapper_root / ".devforge"
            devforge_dir.mkdir(parents=True)
            result, error = allocate_feature_dir(devforge_dir, "wrapper-mode-feature")
            self.assertIsNone(error)
            expected_path = (
                wrapper_root.resolve() / SPECS_ROOT_DEFAULT / "001-wrapper-mode-feature"
            )
            self.assertEqual(Path(result["path"]), expected_path)
            self.assertTrue(expected_path.is_dir())
            # Confirm no dir was created one level further up.
            outer_specs = Path(td) / SPECS_ROOT_DEFAULT
            self.assertFalse(outer_specs.exists())

    def test_relative_path_present_and_correct(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "add-dark-mode")
            self.assertIsNone(error)
            self.assertEqual(result["relative_path"], "specs/001-add-dark-mode")

    def test_relative_path_is_genuinely_relative(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "genuinely-relative")
            self.assertIsNone(error)
            relative_path = result["relative_path"]
            self.assertFalse(relative_path.startswith("/"))
            self.assertNotIn(str(Path(td).resolve()), relative_path)
            self.assertNotIn(td, relative_path)

    def test_relative_path_uses_forward_slashes(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "forward-slash-check")
            self.assertIsNone(error)
            self.assertNotIn("\\", result["relative_path"])
            self.assertIn("/", result["relative_path"])

    def test_relative_path_recombines_to_absolute_path(self):
        """os.path.join(repo_root, relative_path) must reconstruct exactly
        the absolute `path` the SAME call returned -- the two keys must
        never disagree."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            result, error = allocate_feature_dir(devforge_dir, "recombine-check")
            self.assertIsNone(error)
            repo_root = Path(td).resolve()
            reconstructed = repo_root.joinpath(*result["relative_path"].split("/"))
            self.assertEqual(reconstructed, Path(result["path"]))
            # And the os.path.join form the spec text describes, resolved
            # through Path for cross-platform separator equivalence.
            joined = os.path.join(str(repo_root), result["relative_path"])
            self.assertEqual(Path(joined).resolve(), Path(result["path"]).resolve())

    def test_relative_path_wrapper_root_resolution(self):
        """Wrapper mode: relative_path is relative to the install root
        (devforge_dir's parent), not to any outer directory."""
        with tempfile.TemporaryDirectory() as td:
            wrapper_root = Path(td) / "wrapper-install-root"
            devforge_dir = wrapper_root / ".devforge"
            devforge_dir.mkdir(parents=True)
            result, error = allocate_feature_dir(devforge_dir, "wrapper-relative")
            self.assertIsNone(error)
            self.assertEqual(result["relative_path"], "specs/001-wrapper-relative")
            reconstructed = wrapper_root.resolve() / result["relative_path"]
            self.assertEqual(reconstructed, Path(result["path"]))

    def test_number_100_plus_widens_gracefully(self):
        """SPEC_NUMBER_WIDTH (3) is a MINIMUM width, not a cap -- format()
        widens past 999 instead of truncating or erroring."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            (specs_root / "999-nine-nine-nine").mkdir(parents=True)
            result, error = allocate_feature_dir(devforge_dir, "the-thousandth-feature")
            self.assertIsNone(error)
            self.assertEqual(result["number"], 1000)
            self.assertEqual(result["formatted_number"], "1000")
            self.assertTrue(result["dirname"].startswith("1000-"))
            self.assertEqual(result["dirname"], "1000-the-thousandth-feature")
            self.assertTrue((specs_root / "1000-the-thousandth-feature").is_dir())


# ---------------------------------------------------------------------------
# decide_branch_action
# ---------------------------------------------------------------------------


class TestDecideBranchAction(unittest.TestCase):
    def test_arm_create_on_default_branch(self):
        decision, line, error = decide_branch_action(
            "main", "main", "001", "add-dark-mode",
        )
        self.assertEqual(decision, "create")
        self.assertIsNone(error)
        self.assertEqual(line, "git checkout -b spec/001-add-dark-mode")

    def test_arm_create_missing_spec_number(self):
        decision, line, error = decide_branch_action(
            "main", "main", None, "add-dark-mode",
        )
        self.assertEqual(decision, "create")
        self.assertEqual(line, "")
        self.assertIsNotNone(error)
        self.assertIn("spec_number", error)

    def test_arm_create_missing_slug(self):
        decision, line, error = decide_branch_action(
            "main", "main", "001", None,
        )
        self.assertEqual(decision, "create")
        self.assertEqual(line, "")
        self.assertIsNotNone(error)

    def test_arm_create_missing_both(self):
        decision, line, error = decide_branch_action("main", "main", "", "")
        self.assertEqual(decision, "create")
        self.assertIsNotNone(error)

    def test_arm_keep_spec_on_existing_feature_branch(self):
        decision, line, error = decide_branch_action(
            "spec/000-other-feature", "main", "001", "add-dark-mode",
        )
        self.assertEqual(decision, "keep-spec")
        self.assertIsNone(error)
        self.assertEqual(
            line,
            "# already on non-default branch 'spec/000-other-feature'; "
            "no checkout emitted",
        )

    def test_arm_keep_other_on_unrelated_branch(self):
        decision, line, error = decide_branch_action(
            "feature/scratch", "main", "001", "add-dark-mode",
        )
        self.assertEqual(decision, "keep-other")
        self.assertIsNone(error)
        self.assertEqual(
            line,
            "# already on non-default branch 'feature/scratch'; "
            "no checkout emitted",
        )

    def test_keep_spec_and_keep_other_render_identical_text_shape(self):
        """The two 'keep' arms must differ only in the branch name embedded,
        never in the surrounding template — /specify's stdout depends on
        this being the single original message shape."""
        _, line_spec, _ = decide_branch_action(
            "spec/999-x", "main", "001", "add-dark-mode",
        )
        _, line_other, _ = decide_branch_action(
            "some-other-branch", "main", "001", "add-dark-mode",
        )
        template = "# already on non-default branch {0!r}; no checkout emitted"
        self.assertEqual(line_spec, template.format("spec/999-x"))
        self.assertEqual(line_other, template.format("some-other-branch"))

    def test_current_equals_default_takes_priority_over_spec_prefix(self):
        """If the default branch itself were named spec/..., current==default
        still wins (matches the original code's branch order)."""
        decision, line, error = decide_branch_action(
            "spec/main", "spec/main", "002", "weird-default-branch",
        )
        self.assertEqual(decision, "create")
        self.assertIsNone(error)
        self.assertEqual(line, "git checkout -b spec/002-weird-default-branch")

    def test_strips_whitespace_on_branch_names(self):
        decision, line, error = decide_branch_action(
            "  main  ", "  main  ", "003", "trim-test-feature",
        )
        self.assertEqual(decision, "create")
        self.assertIsNone(error)
        self.assertEqual(line, "git checkout -b spec/003-trim-test-feature")


# ---------------------------------------------------------------------------
# Constants sanity (used elsewhere via re-export — pin their values here).
# ---------------------------------------------------------------------------


class TestConstants(unittest.TestCase):
    def test_feature_name_re_shape(self):
        self.assertTrue(FEATURE_NAME_RE.match("two-words"))
        self.assertTrue(FEATURE_NAME_RE.match("one-two-three-four"))
        self.assertFalse(FEATURE_NAME_RE.match("oneword"))
        self.assertFalse(FEATURE_NAME_RE.match("Two-Words"))
        self.assertFalse(FEATURE_NAME_RE.match("one-two-three-four-five"))

    def test_spec_number_dir_re_shape(self):
        self.assertTrue(SPEC_NUMBER_DIR_RE.match("001-foo"))
        self.assertFalse(SPEC_NUMBER_DIR_RE.match("1-foo"))
        self.assertFalse(SPEC_NUMBER_DIR_RE.match("abc-foo"))

    def test_spec_number_width_and_root(self):
        self.assertEqual(SPEC_NUMBER_WIDTH, 3)
        self.assertEqual(SPECS_ROOT_DEFAULT, "specs")

    def test_year_dir_re_shape(self):
        self.assertTrue(YEAR_DIR_RE.match("2026"))
        self.assertFalse(YEAR_DIR_RE.match("26"))
        self.assertFalse(YEAR_DIR_RE.match("20266"))
        self.assertFalse(YEAR_DIR_RE.match("2026-08"))

    def test_month_dir_re_shape(self):
        self.assertTrue(MONTH_DIR_RE.match("08"))
        self.assertFalse(MONTH_DIR_RE.match("8"))
        self.assertFalse(MONTH_DIR_RE.match("123"))


# ---------------------------------------------------------------------------
# specs_root_for
# ---------------------------------------------------------------------------


class TestSpecsRootFor(unittest.TestCase):
    def test_returns_repo_root_specs(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            expected = Path(td).resolve() / SPECS_ROOT_DEFAULT
            self.assertEqual(specs_root_for(devforge_dir), expected)

    def test_wrapper_root_resolution(self):
        """devforge_dir's PARENT is the wrapper/install root -- the same
        convention next_spec_number / allocate_feature_dir already rely
        on."""
        with tempfile.TemporaryDirectory() as td:
            wrapper_root = Path(td) / "wrapper-install-root"
            devforge_dir = wrapper_root / ".devforge"
            devforge_dir.mkdir(parents=True)
            expected = wrapper_root.resolve() / SPECS_ROOT_DEFAULT
            self.assertEqual(specs_root_for(devforge_dir), expected)

    def test_pure_path_arithmetic_does_not_require_existing_paths(self):
        """Docstring claim: does not stat devforge_dir, the returned
        specs_root, or any ancestor -- safe to call even when none of
        them exist on disk."""
        with tempfile.TemporaryDirectory() as td:
            nonexistent_devforge_dir = Path(td) / "never-created" / ".devforge"
            # Must not raise even though nothing on this path exists.
            result = specs_root_for(nonexistent_devforge_dir)
            self.assertEqual(
                result,
                Path(td).resolve() / "never-created" / SPECS_ROOT_DEFAULT,
            )
            self.assertFalse(result.exists())

    def test_composes_with_iter_feature_dirs(self):
        """specs_root_for's whole reason to exist: a devforge_dir-holding
        caller reaches the specs_root iter_feature_dirs actually takes, in
        one explicit call."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            (specs_root / "001-x").mkdir(parents=True)
            result = iter_feature_dirs(specs_root_for(devforge_dir))
            self.assertEqual(result, [specs_root / "001-x"])


# ---------------------------------------------------------------------------
# iter_feature_dirs / find_feature_dirs_with
# ---------------------------------------------------------------------------


class TestIterFeatureDirs(unittest.TestCase):
    def test_specs_dir_absent_returns_empty_list(self):
        """specs_root itself was never created -- distinct from
        test_specs_dir_present_but_empty_returns_empty_list (exists but
        empty) and the two test_unreadable_specs_root_* cases (exists but
        (ancestor-)unreadable)."""
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            self.assertEqual(iter_feature_dirs(specs_root), [])

    def test_specs_dir_present_but_empty_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            specs_root.mkdir()
            self.assertEqual(iter_feature_dirs(specs_root), [])

    def test_legacy_only_tree(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            (specs_root / "003-legacy-three").mkdir(parents=True)
            (specs_root / "001-legacy-one").mkdir(parents=True)
            result = iter_feature_dirs(specs_root)
            self.assertEqual(
                result,
                [specs_root / "001-legacy-one", specs_root / "003-legacy-three"],
            )

    def test_new_shape_only_tree(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            (specs_root / "2026" / "08" / "PROJ-200").mkdir(parents=True)
            (specs_root / "2026" / "08" / "PROJ-100").mkdir(parents=True)
            (specs_root / "2025" / "01" / "PROJ-050").mkdir(parents=True)
            result = iter_feature_dirs(specs_root)
            self.assertEqual(
                result,
                [
                    specs_root / "2025" / "01" / "PROJ-050",
                    specs_root / "2026" / "08" / "PROJ-100",
                    specs_root / "2026" / "08" / "PROJ-200",
                ],
            )

    def test_mixed_tree_legacy_family_sorts_before_new_shape(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT

            # Legacy family.
            (specs_root / "003-legacy-three").mkdir(parents=True)
            (specs_root / "001-legacy-one").mkdir(parents=True)

            # New-shape family.
            (specs_root / "2026" / "09" / "PROJ-300").mkdir(parents=True)
            (specs_root / "2026" / "08" / "PROJ-200").mkdir(parents=True)
            (specs_root / "2026" / "08" / "PROJ-100").mkdir(parents=True)
            (specs_root / "2025" / "01" / "PROJ-050").mkdir(parents=True)

            # Directories claimed by neither arm.
            (specs_root / "9999-too-many-digits").mkdir(parents=True)
            (specs_root / "not-a-spec-dir").mkdir(parents=True)

            # Stray non-directory entries at every level.
            (specs_root / "README.txt").write_text("x")
            (specs_root / "2026" / "README.txt").write_text("x")
            (specs_root / "2026" / "08" / "README.txt").write_text("x")

            result = iter_feature_dirs(specs_root)
            self.assertEqual(
                result,
                [
                    specs_root / "001-legacy-one",
                    specs_root / "003-legacy-three",
                    specs_root / "2025" / "01" / "PROJ-050",
                    specs_root / "2026" / "08" / "PROJ-100",
                    specs_root / "2026" / "08" / "PROJ-200",
                    specs_root / "2026" / "09" / "PROJ-300",
                ],
            )

    def test_9999_dir_claimed_by_neither_arm(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            (specs_root / "9999-too-many-digits").mkdir(parents=True)
            self.assertEqual(iter_feature_dirs(specs_root), [])
            # And next_spec_number (the existing pin) still ignores it too.
            self.assertEqual(next_spec_number(devforge_dir), 1)

    def test_stray_file_directly_under_specs_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            specs_root.mkdir()
            (specs_root / "2026-stray-file").write_text("x")
            self.assertEqual(iter_feature_dirs(specs_root), [])

    def test_year_entry_that_is_a_file_not_a_dir_ignored(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            specs_root.mkdir()
            # A file literally named like a year -- must not be walked
            # into as though it were a year directory.
            (specs_root / "2026").write_text("x")
            self.assertEqual(iter_feature_dirs(specs_root), [])

    def test_wrapper_root_resolution(self):
        """specs_root_for resolves wrapper_root/specs from wrapper_root/.devforge,
        and composing it with iter_feature_dirs reproduces the old
        single-call (devforge_dir-in) behaviour this test used to pin
        before iter_feature_dirs took a specs_root directly."""
        with tempfile.TemporaryDirectory() as td:
            wrapper_root = (Path(td).resolve()) / "wrapper-install-root"
            devforge_dir = wrapper_root / ".devforge"
            devforge_dir.mkdir(parents=True)
            specs_root = wrapper_root / SPECS_ROOT_DEFAULT
            (specs_root / "007-x").mkdir(parents=True)

            resolved_specs_root = specs_root_for(devforge_dir)
            self.assertEqual(resolved_specs_root, specs_root)

            result = iter_feature_dirs(resolved_specs_root)
            self.assertEqual(result, [specs_root / "007-x"])

            outer_specs = Path(td).resolve() / SPECS_ROOT_DEFAULT
            self.assertFalse(outer_specs.exists())

    @unittest.skipIf(_SKIP_PERMISSION_TESTS, _PERMISSION_SKIP_REASON)
    def test_unreadable_specs_root_returns_empty_list_not_raise(self):
        """specs/ itself locked down (0o000): iterdir() on it raises --
        confirm the function swallows that OSError and returns [] rather
        than propagating (the "never raises" contract)."""
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            (specs_root / "001-locked-out").mkdir(parents=True)
            os.chmod(specs_root, 0o000)
            try:
                self.assertEqual(iter_feature_dirs(specs_root), [])
            finally:
                # Always restore, even on assertion failure, so the
                # TemporaryDirectory cleanup below can remove the tree.
                os.chmod(specs_root, 0o755)

    @unittest.skipIf(_SKIP_PERMISSION_TESTS, _PERMISSION_SKIP_REASON)
    def test_unreadable_specs_root_ancestor_returns_empty_list_not_raise(self):
        """The PARENT of specs/ locked down (0o000): stat()/exists() on
        specs_root itself raises before the emptiness guard is even
        evaluated -- confirm that path is guarded too, not just the
        iterdir() path covered above."""
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td).resolve()
            specs_root = repo_root / SPECS_ROOT_DEFAULT
            (specs_root / "001-x").mkdir(parents=True)
            os.chmod(repo_root, 0o000)
            try:
                self.assertEqual(iter_feature_dirs(specs_root), [])
            finally:
                os.chmod(repo_root, 0o755)

    def test_valid_symlink_to_dir_included(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            real_target = Path(td).resolve() / "elsewhere" / "real-feature-dir"
            real_target.mkdir(parents=True)
            specs_root.mkdir(parents=True, exist_ok=True)
            symlinked = specs_root / "005-symlinked-feature"
            symlinked.symlink_to(real_target, target_is_directory=True)
            result = iter_feature_dirs(specs_root)
            self.assertEqual(result, [symlinked])

    def test_dangling_symlink_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            specs_root.mkdir(parents=True)
            dangling = specs_root / "006-dangling-feature"
            dangling.symlink_to(
                specs_root / "does-not-exist", target_is_directory=True,
            )
            self.assertEqual(iter_feature_dirs(specs_root), [])

    def test_near_miss_name_shapes_classified_correctly(self):
        """Pins the disjointness claim the single-pass if/elif dispatch
        rests on: each of these near-miss name shapes is claimed by
        exactly one arm or by neither -- never both, and never
        misclassified into the wrong arm."""
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            (specs_root / "0001-x").mkdir(parents=True)    # neither arm
            (specs_root / "12345").mkdir(parents=True)     # neither arm
            (specs_root / "202-6").mkdir(parents=True)     # legacy arm (NNN=202)
            (specs_root / "2026-08").mkdir(parents=True)   # neither arm
            result = iter_feature_dirs(specs_root)
            self.assertEqual(result, [specs_root / "202-6"])


class TestFindFeatureDirsWith(unittest.TestCase):
    def test_specs_dir_absent_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            self.assertEqual(find_feature_dirs_with(specs_root, "spec.md"), [])

    def test_legacy_only_tree_filters_on_sentinel(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            has_spec = specs_root / "001-has-spec"
            has_spec.mkdir(parents=True)
            (has_spec / "spec.md").write_text("x")
            no_spec = specs_root / "002-no-spec"
            no_spec.mkdir(parents=True)
            result = find_feature_dirs_with(specs_root, "spec.md")
            self.assertEqual(result, [has_spec])

    def test_new_shape_tree_filters_on_sentinel(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            has_it = specs_root / "2026" / "08" / "PROJ-100"
            has_it.mkdir(parents=True)
            (has_it / "breakdown-handoff.json").write_text("{}")
            lacks_it = specs_root / "2026" / "08" / "PROJ-200"
            lacks_it.mkdir(parents=True)
            result = find_feature_dirs_with(specs_root, "breakdown-handoff.json")
            self.assertEqual(result, [has_it])

    def test_mixed_tree_filters_across_both_shapes(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            legacy_hit = specs_root / "001-legacy-hit"
            legacy_hit.mkdir(parents=True)
            (legacy_hit / "plan.md").write_text("x")
            (specs_root / "002-legacy-miss").mkdir(parents=True)
            new_hit = specs_root / "2026" / "08" / "PROJ-100"
            new_hit.mkdir(parents=True)
            (new_hit / "plan.md").write_text("x")
            (specs_root / "2026" / "08" / "PROJ-200").mkdir(parents=True)
            result = find_feature_dirs_with(specs_root, "plan.md")
            self.assertEqual(result, [legacy_hit, new_hit])

    def test_dir_lacking_sentinel_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            (specs_root / "001-no-sentinel").mkdir(parents=True)
            result = find_feature_dirs_with(specs_root, "research-handoff.json")
            self.assertEqual(result, [])

    def test_directory_named_like_sentinel_is_not_a_match(self):
        """A DIRECTORY named filename must not satisfy the filter -- only a
        FILE does (Path.is_file(), not mere existence)."""
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td) / SPECS_ROOT_DEFAULT
            feature_dir = specs_root / "001-sentinel-is-a-dir"
            (feature_dir / "spec.md").mkdir(parents=True)
            result = find_feature_dirs_with(specs_root, "spec.md")
            self.assertEqual(result, [])

    def test_symlink_to_file_matches(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            feature_dir = specs_root / "001-symlinked-sentinel"
            feature_dir.mkdir(parents=True)
            real_file = Path(td).resolve() / "elsewhere-spec.md"
            real_file.write_text("x")
            (feature_dir / "spec.md").symlink_to(real_file)
            result = find_feature_dirs_with(specs_root, "spec.md")
            self.assertEqual(result, [feature_dir])

    def test_dangling_symlink_to_file_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            feature_dir = specs_root / "001-dangling-sentinel"
            feature_dir.mkdir(parents=True)
            (feature_dir / "spec.md").symlink_to(
                specs_root / "nonexistent-target.md",
            )
            result = find_feature_dirs_with(specs_root, "spec.md")
            self.assertEqual(result, [])

    @unittest.skipIf(_SKIP_PERMISSION_TESTS, _PERMISSION_SKIP_REASON)
    def test_unreadable_feature_dir_excludes_rather_than_raises(self):
        """A feature dir that iter_feature_dirs already listed, but whose
        contents become unreadable (0o000) before this function's own
        is_file() probe, must be treated as "no match", not raise."""
        with tempfile.TemporaryDirectory() as td:
            specs_root = Path(td).resolve() / SPECS_ROOT_DEFAULT
            feature_dir = specs_root / "001-locked-contents"
            feature_dir.mkdir(parents=True)
            (feature_dir / "spec.md").write_text("x")
            os.chmod(feature_dir, 0o000)
            try:
                result = find_feature_dirs_with(specs_root, "spec.md")
                self.assertEqual(result, [])
            finally:
                os.chmod(feature_dir, 0o755)


if __name__ == "__main__":
    unittest.main()
