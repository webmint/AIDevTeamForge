"""Tests for src/devforge/lib/_verify/_specstatus.py

Real fixture discipline:
  spec.md fixtures are created from real content matching the specify-sample-migration.md
  structure (the real spec format), NOT hand-authored JSON or arbitrary markdown.
  Task files use the real **Status**: line pattern from _implement/_cmds_resolve.py.

Coverage:
  flip_spec_status:
    Blocking paths (task cross-check):
      - Single task with Pending status → flipped=False, blocker names the task
      - Single task with "In Progress" status → flipped=False
      - Mixed: one Complete, one Pending → flipped=False (all must pass)
      - Task with no Status line → flipped=False (treated as incomplete)
      - Unreadable task file → flipped=False (no crash, treated as incomplete)

    Success paths:
      - All tasks Complete → flipped=True, spec **Status** → Complete
      - All tasks Skipped → flipped=True (Skipped counts as satisfied)
      - Mixed Complete + Skipped → flipped=True
      - No tasks dir → treated as "no tasks to check" → flipped=True

    AC ticking:
      - PASS ACs: checkbox ticked (- [ ] → - [x])
      - PASS (code) ACs: ticked
      - FAIL ACs: NOT ticked
      - PARTIAL ACs: NOT ticked
      - UNVERIFIED ACs: NOT ticked
      - MANUAL ACs: NOT ticked (only PASS and PASS (code) tick)
      - Already-ticked ACs: left as-is (no double-tick)

    Idempotency:
      - Re-running on an already-Complete spec returns flipped=True, ticked=[]
        (nothing changed, no error)

    Atomic write:
      - No .tmp- files left after success
      - Spec content on-disk matches expected after flip

    Error paths:
      - Missing spec.md → flipped=False with blocker explaining
      - Spec without **Status**: line → flipped=False with blocker
      - README.md in tasks/ is excluded from cross-check

    Return shape:
      - Always returns dict with {flipped, blocker, ticked, spec_path}
"""

from __future__ import annotations

import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _verify._specstatus import flip_spec_status  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


_SPEC_TEMPLATE = """\
# Spec: {title}

**Date**: 2026-06-16
**Status**: {status}
**Author**: Test

## 5. Acceptance Criteria

### 5.1 First criteria

{box_1} **AC-1**: The system shall do X.

### 5.2 Second criteria

{box_2} **AC-2**: The system shall do Y.

### 5.3 Third criteria

{box_3} **AC-3**: The system shall do Z.
"""

_TASK_TEMPLATE = """\
# Task 001: Do something

**Status**: {status}
**Agent**: backend-engineer

## Context

Some context here.
"""


def _write_spec(directory, title="test-feature", status="In Progress",
                ac1_checked=False, ac2_checked=False, ac3_checked=False):
    """Write a spec.md into directory and return its path."""
    def _box(checked):
        return "- [x]" if checked else "- [ ]"
    # Note: template already has the list item prefix as {box_N}, so the box IS
    # the full "- [x]" or "- [ ]" item.

    content = _SPEC_TEMPLATE.format(
        title=title,
        status=status,
        box_1=_box(ac1_checked),
        box_2=_box(ac2_checked),
        box_3=_box(ac3_checked),
    )
    spec_path = os.path.join(directory, "spec.md")
    with open(spec_path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return spec_path


def _write_task(tasks_dir, filename, status):
    """Write a task file with the given status."""
    os.makedirs(tasks_dir, exist_ok=True)
    content = _TASK_TEMPLATE.format(status=status)
    path = os.path.join(tasks_dir, filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def _ac_result(ac_id, status):
    return {
        "id": ac_id,
        "text": "test",
        "checked": False,
        "subsection": "",
        "status": status,
        "evidence": "",
    }


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestFlipSpecStatusBlocking(unittest.TestCase):
    """Task cross-check blocking paths."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tasks_dir = os.path.join(self.tmp, "tasks")
        _write_spec(self.tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_pending_task_blocks(self):
        _write_task(self.tasks_dir, "001-task.md", "Pending")
        result = flip_spec_status(self.tmp, [])
        self.assertFalse(result["flipped"])
        self.assertIsNotNone(result["blocker"])
        self.assertIn("001-task.md", result["blocker"])
        self.assertIn("Pending", result["blocker"])

    def test_in_progress_task_blocks(self):
        _write_task(self.tasks_dir, "001-task.md", "In Progress")
        result = flip_spec_status(self.tmp, [])
        self.assertFalse(result["flipped"])
        self.assertIn("In Progress", result["blocker"])

    def test_mixed_complete_pending_blocks(self):
        _write_task(self.tasks_dir, "001-task.md", "Complete")
        _write_task(self.tasks_dir, "002-task.md", "Pending")
        result = flip_spec_status(self.tmp, [])
        self.assertFalse(result["flipped"])
        self.assertIn("002-task.md", result["blocker"])

    def test_spec_unchanged_when_blocked(self):
        """Spec **Status** must NOT be changed when a task blocks."""
        _write_task(self.tasks_dir, "001-task.md", "Pending")
        with open(os.path.join(self.tmp, "spec.md"), encoding="utf-8") as fh:
            original = fh.read()
        flip_spec_status(self.tmp, [])
        with open(os.path.join(self.tmp, "spec.md"), encoding="utf-8") as fh:
            after = fh.read()
        self.assertEqual(original, after)

    def test_task_no_status_line_blocks(self):
        """Task file without **Status**: line is treated as incomplete."""
        tasks_dir = self.tasks_dir
        os.makedirs(tasks_dir, exist_ok=True)
        path = os.path.join(tasks_dir, "001-notask.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("# Task without status\n\nSome content.\n")
        result = flip_spec_status(self.tmp, [])
        self.assertFalse(result["flipped"])
        self.assertIn("no Status line", result["blocker"])

    def test_readme_md_excluded(self):
        """README.md in tasks/ is NOT subject to cross-check."""
        os.makedirs(self.tasks_dir, exist_ok=True)
        # Write only README.md with no Status — should be ignored
        with open(os.path.join(self.tasks_dir, "README.md"), "w", encoding="utf-8") as fh:
            fh.write("# Task Index\n\nThis is the README.\n")
        # No real task files — should flip successfully (no tasks to check)
        result = flip_spec_status(self.tmp, [])
        self.assertTrue(result["flipped"])


class TestFlipSpecStatusSuccess(unittest.TestCase):
    """Successful flip paths."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.tasks_dir = os.path.join(self.tmp, "tasks")
        _write_spec(self.tmp, status="In Progress")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _read_spec(self):
        with open(os.path.join(self.tmp, "spec.md"), encoding="utf-8") as fh:
            return fh.read()

    def test_all_complete_tasks_flips(self):
        _write_task(self.tasks_dir, "001-task.md", "Complete")
        result = flip_spec_status(self.tmp, [])
        self.assertTrue(result["flipped"])
        self.assertIsNone(result["blocker"])
        self.assertIn("**Status**: Complete", self._read_spec())

    def test_all_skipped_tasks_flips(self):
        _write_task(self.tasks_dir, "001-task.md", "Skipped")
        result = flip_spec_status(self.tmp, [])
        self.assertTrue(result["flipped"])
        self.assertIn("**Status**: Complete", self._read_spec())

    def test_mixed_complete_skipped_flips(self):
        _write_task(self.tasks_dir, "001-task.md", "Complete")
        _write_task(self.tasks_dir, "002-task.md", "Skipped")
        result = flip_spec_status(self.tmp, [])
        self.assertTrue(result["flipped"])

    def test_no_tasks_dir_flips(self):
        """No tasks/ directory = no tasks to check → flip succeeds."""
        result = flip_spec_status(self.tmp, [])
        self.assertTrue(result["flipped"])

    def test_spec_path_returned(self):
        result = flip_spec_status(self.tmp, [])
        self.assertTrue(result["spec_path"].endswith("spec.md"))

    def test_ticked_empty_when_no_pass_acs(self):
        result = flip_spec_status(self.tmp, [
            _ac_result("AC-1", "FAIL"),
            _ac_result("AC-2", "UNVERIFIED"),
        ])
        self.assertTrue(result["flipped"])
        self.assertEqual(result["ticked"], [])

    def test_pass_ac_ticked(self):
        result = flip_spec_status(self.tmp, [
            _ac_result("AC-1", "PASS"),
            _ac_result("AC-2", "FAIL"),
            _ac_result("AC-3", "UNVERIFIED"),
        ])
        self.assertTrue(result["flipped"])
        self.assertIn("AC-1", result["ticked"])
        self.assertNotIn("AC-2", result["ticked"])
        self.assertNotIn("AC-3", result["ticked"])

    def test_pass_code_ac_ticked(self):
        result = flip_spec_status(self.tmp, [
            _ac_result("AC-1", "PASS (code)"),
            _ac_result("AC-2", "PASS"),
        ])
        self.assertIn("AC-1", result["ticked"])
        self.assertIn("AC-2", result["ticked"])

    def test_fail_partial_unverified_manual_not_ticked(self):
        for status in ("FAIL", "PARTIAL", "UNVERIFIED", "MANUAL",
                       "FAIL (code)", "PARTIAL (code)"):
            with self.subTest(status=status):
                # Fresh spec each sub-test
                tmpd = tempfile.mkdtemp()
                try:
                    _write_spec(tmpd, status="In Progress")
                    result = flip_spec_status(tmpd, [_ac_result("AC-1", status)])
                    self.assertNotIn("AC-1", result["ticked"],
                                     msg="Status {0} should not tick AC-1".format(status))
                finally:
                    import shutil
                    shutil.rmtree(tmpd, ignore_errors=True)

    def test_spec_checkbox_ticked_on_disk(self):
        """The actual spec.md content has - [x] after a PASS tick."""
        result = flip_spec_status(self.tmp, [
            _ac_result("AC-1", "PASS"),
        ])
        spec_content = self._read_spec()
        self.assertIn("- [x] **AC-1**:", spec_content)

    def test_spec_checkbox_unticked_for_fail(self):
        """FAIL AC checkbox stays - [ ] after flip."""
        result = flip_spec_status(self.tmp, [
            _ac_result("AC-1", "FAIL"),
        ])
        spec_content = self._read_spec()
        self.assertIn("- [ ] **AC-1**:", spec_content)


class TestFlipSpecStatusIdempotent(unittest.TestCase):
    """Idempotency: re-running on already-Complete spec."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Write spec already Complete with AC-1 ticked
        _write_spec(self.tmp, status="Complete", ac1_checked=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_re_run_on_complete_spec(self):
        """Re-running on already-Complete spec → flipped=True, ticked=[] (no-op)."""
        result = flip_spec_status(self.tmp, [
            _ac_result("AC-1", "PASS"),
        ])
        self.assertTrue(result["flipped"])
        # AC-1 was already ticked — ticked list should be empty (nothing changed)
        self.assertEqual(result["ticked"], [])

    def test_re_run_spec_content_unchanged(self):
        """Spec content after re-run = same as before (idempotent)."""
        spec_path = os.path.join(self.tmp, "spec.md")
        with open(spec_path, encoding="utf-8") as fh:
            before = fh.read()

        flip_spec_status(self.tmp, [_ac_result("AC-1", "PASS")])

        with open(spec_path, encoding="utf-8") as fh:
            after = fh.read()
        self.assertEqual(before, after)

    def test_uppercase_x_already_ticked_is_idempotent(self):
        """A spec with - [X] (uppercase) is already ticked — no re-tick, no file write.

        The fix: check_char.lower() != 'x' prevents treating [X] as unchecked.
        """
        # Write a spec with uppercase [X] on AC-1
        spec_path = os.path.join(self.tmp, "spec.md")
        content = textwrap.dedent("""\
            # Spec: uppercase-tick

            **Date**: 2026-06-16
            **Status**: In Progress
            **Author**: Test

            ## 5. Acceptance Criteria

            ### 5.1 First criteria

            - [X] **AC-1**: Uppercase already ticked.
        """)
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(content)

        result = flip_spec_status(self.tmp, [
            _ac_result("AC-1", "PASS"),
        ], spec_path=spec_path)

        # flipped=True (operation succeeded)
        self.assertTrue(result["flipped"])
        # ticked=[] — no change, AC-1 was already ticked (via uppercase [X])
        self.assertEqual(result["ticked"], [],
                         "AC-1 was already [X]-ticked; ticked should be empty but got: {0}".format(
                             result["ticked"]))

        # Verify the on-disk content was not changed (idempotent)
        with open(spec_path, encoding="utf-8") as fh:
            after = fh.read()
        self.assertIn("- [X] **AC-1**:", after,
                      "Uppercase [X] should be preserved, not lowercased")


class TestFlipSpecStatusAtomicWrite(unittest.TestCase):
    """Atomic write properties."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        _write_spec(self.tmp, status="In Progress")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_no_tmp_files_after_success(self):
        flip_spec_status(self.tmp, [])
        entries = os.listdir(self.tmp)
        tmp_files = [e for e in entries if e.startswith(".tmp-spec-")]
        self.assertEqual(tmp_files, [])


class TestFlipSpecStatusErrors(unittest.TestCase):
    """Error paths."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_spec_md_returns_false(self):
        """No spec.md in feature dir → flipped=False with a blocker message."""
        result = flip_spec_status(self.tmp, [])
        self.assertFalse(result["flipped"])
        self.assertIsNotNone(result["blocker"])

    def test_spec_without_status_line(self):
        """spec.md without **Status**: line → flipped=False."""
        spec_path = os.path.join(self.tmp, "spec.md")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write("# Spec: no status\n\nSome content.\n")
        result = flip_spec_status(self.tmp, [])
        self.assertFalse(result["flipped"])
        self.assertIn("no **Status**", result["blocker"])

    def test_result_always_has_required_keys(self):
        """Return dict always has {flipped, blocker, ticked, spec_path}."""
        result = flip_spec_status(self.tmp, [])
        for key in ("flipped", "blocker", "ticked", "spec_path"):
            self.assertIn(key, result)


class TestFlipSpecStatusMalformedStatusLine(unittest.TestCase):
    """Regression: _STATUS_PATTERN must NOT bleed across blank lines.

    A malformed spec where **Status**: appears on a line by itself (no value)
    followed by blank lines and then a word on the next non-empty line must NOT
    have that word captured as the status value.  With the old \\s* pattern,
    "**Status**:\\n\\nComplete\\n" wrongly yielded status "Complete".
    With the fixed [ \\t]* pattern the match fails (no value on the same line),
    which means:
      - _read_task_status returns None  → task treated as incomplete (flip blocks)
      - flip_spec_status returns flipped=False with a blocker about no Status line
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_malformed_status_blank_line_does_not_bleed(self):
        """**Status**: on its own line, value on next non-empty line → not treated as Complete."""
        # Craft a spec where **Status**: has its value on the NEXT line (malformed).
        malformed_spec = (
            "# Spec: malformed\n"
            "\n"
            "**Status**:\n"
            "\n"
            "Complete\n"
            "\n"
            "## Overview\n"
            "\n"
            "Some content.\n"
        )
        spec_path = os.path.join(self.tmp, "spec.md")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(malformed_spec)

        result = flip_spec_status(self.tmp, [], spec_path=spec_path)

        # The malformed **Status**: line has no value on the same line.
        # The pattern must not match "Complete" from a later line.
        # flip_spec_status should return flipped=False with a blocker.
        self.assertFalse(
            result["flipped"],
            "Malformed spec with **Status**: on its own line must NOT be treated as Complete; "
            "got flipped=True with blocker={0!r}".format(result["blocker"]),
        )
        self.assertIsNotNone(result["blocker"])
        self.assertIn("no **Status**", result["blocker"],
                      "Expected blocker to report missing Status line, got: {0!r}".format(
                          result["blocker"]))

    def test_well_formed_status_still_matches(self):
        """Sanity: a well-formed **Status**: In Progress line still matches after the fix."""
        well_formed_spec = (
            "# Spec: well-formed\n"
            "\n"
            "**Status**: In Progress\n"
            "\n"
            "## Overview\n"
            "\n"
            "Some content.\n"
            "\n"
            "## 5. Acceptance Criteria\n"
            "\n"
            "- [ ] **AC-1**: Something.\n"
        )
        spec_path = os.path.join(self.tmp, "spec.md")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(well_formed_spec)

        result = flip_spec_status(self.tmp, [], spec_path=spec_path)

        self.assertTrue(result["flipped"],
                        "Well-formed spec must flip successfully; got blocker={0!r}".format(
                            result["blocker"]))
        with open(spec_path, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("**Status**: Complete", content)

    def test_malformed_task_status_blank_line_blocks_flip(self):
        """A task file with **Status**: on its own line is treated as incomplete (blocks flip).

        This exercises _read_task_status — when the pattern fails to match
        (value on next line), the function returns None, which causes
        flip_spec_status to return flipped=False with a 'no Status line' blocker.
        """
        # Write a valid spec
        well_formed_spec = (
            "# Spec: well-formed\n"
            "\n"
            "**Status**: In Progress\n"
            "\n"
            "## 5. Acceptance Criteria\n"
            "\n"
            "- [ ] **AC-1**: Something.\n"
        )
        spec_path = os.path.join(self.tmp, "spec.md")
        with open(spec_path, "w", encoding="utf-8") as fh:
            fh.write(well_formed_spec)

        # Write a task with malformed **Status**: (value on next line)
        tasks_dir = os.path.join(self.tmp, "tasks")
        os.makedirs(tasks_dir)
        malformed_task = (
            "# Task 001: Do something\n"
            "\n"
            "**Status**:\n"
            "\n"
            "Complete\n"
            "\n"
            "## Context\n"
        )
        with open(os.path.join(tasks_dir, "001-task.md"), "w", encoding="utf-8") as fh:
            fh.write(malformed_task)

        result = flip_spec_status(self.tmp, [], spec_path=spec_path)

        # _read_task_status returns None → treated as "no Status line" → blocked
        self.assertFalse(result["flipped"])
        self.assertIsNotNone(result["blocker"])
        self.assertIn("no Status line", result["blocker"])


class TestFlipSpecStatusExplicitSpecPath(unittest.TestCase):
    """spec_path parameter override."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_explicit_spec_path_used(self):
        """--spec-path flag uses the given path instead of <feature>/spec.md."""
        other_spec = os.path.join(self.tmp, "custom-spec.md")
        with open(other_spec, "w", encoding="utf-8") as fh:
            fh.write(
                "# Spec: custom\n\n"
                "**Status**: In Progress\n\n"
                "## 5. Acceptance Criteria\n\n"
                "- [ ] **AC-1**: Do something.\n"
            )
        result = flip_spec_status(self.tmp, [], spec_path=other_spec)
        self.assertTrue(result["flipped"])
        self.assertEqual(result["spec_path"], other_spec)
        with open(other_spec, encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("**Status**: Complete", content)


if __name__ == "__main__":
    unittest.main()
