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

All tests use real tempfile-backed filesystem trees — no hand-fabricated
JSON, no mocked Path objects (except the one deliberate race-simulation
test, which patches next_spec_number specifically to force a collision
that cannot occur through normal sequential allocation).

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

# ---------------------------------------------------------------------------
# Path setup (mirrors tests/lib/_shared/test_feature_scope.py).
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _shared.feature_alloc import (  # noqa: E402
    FEATURE_NAME_RE,
    SPEC_NUMBER_DIR_RE,
    SPEC_NUMBER_WIDTH,
    SPECS_ROOT_DEFAULT,
    allocate_feature_dir,
    decide_branch_action,
    next_spec_number,
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


if __name__ == "__main__":
    unittest.main()
