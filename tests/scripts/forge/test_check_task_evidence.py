#!/usr/bin/env python3
"""Tests for scripts/forge/check-task-evidence.py (stdlib unittest; Python 3.9+): a newly Complete task needs filled
Completion Notes, a task file Status that agrees with the task index and, mid-branch, a commit that names it.

A throwaway git repository holds a base commit with one open task and a work branch. All names are invented.

Run: python3 -m unittest discover -s tests/scripts/forge -v
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPTS = os.path.join(REPO, "scripts", "forge")
_spec = importlib.util.spec_from_file_location("check_task_evidence", os.path.join(SCRIPTS, "check-task-evidence.py"))
checker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(checker)

ROWS = "# Tasks: X\n\n## Task Index\n\n| # | Title | Agent | Depends on | Status |\n|---|---|---|---|---|\n"
OPEN = ROWS + "| 001 | One | a | None | Pending |\n| 002 | Two | a | 001 | Pending |\n"
DONE_1 = ROWS + "| 001 | One | a | None | Complete |\n| 002 | Two | a | 001 | Pending |\n"
NOTES = "# Task 001: One\n\n## Completion Notes\n\n**Completed**: 2026-01-02 10:00\n**Notes**: gates green.\n"
NO_NOTES = "# Task 001: One\n\n## Completion Notes\n\n## Other\nx\n"
# The section as /breakdown writes it: placeholders only.
TEMPLATE_NOTES = (
    "# Task 001: One\n\n## Completion Notes\n\n[Filled in by /execute-task after completion]\n"
    "**Completed**: [date/time]\n**Files changed**: [actual files]\n"
    "**Contract**: Expects [X/Y verified] | Produces [X/Y verified]\n**Notes**: [deviations or observations]\n"
)


class EvidenceRepo(unittest.TestCase):
    """The throwaway repository and its helpers; it holds no tests of its own."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = self.tmp.name
        self.git("init", "-q", "-b", "main")
        self.write("specs/900-x/tasks/README.md", OPEN)
        self.write("specs/900-x/tasks/001-one.md", "# Task\n")
        self.commit("base")
        self.git("branch", "base")
        self.git("checkout", "-q", "-b", "work")

    def git(self, *args):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                        "-C", self.repo, *args], check=True, capture_output=True)

    def write(self, rel, text):
        path = os.path.join(self.repo, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def commit(self, subject):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", subject)

    def run_check(self):
        return checker.check(self.repo, "base")


class EvidenceCase(EvidenceRepo):
    def test_an_unresolvable_integration_ref_names_the_fix(self):
        with self.assertRaises(ValueError) as caught:
            checker.check(self.repo, "origin/main")
        self.assertEqual(str(caught.exception), "integrationRef origin/main does not resolve (no remote or no commits "
                                                "yet); fetch it or set integrationRef")

    def test_untouched_readme_is_not_read(self):
        self.write("docs/a.md", "x")
        self.commit("docs")
        self.assertEqual(self.run_check(), ([], 0))

    def test_complete_with_notes_and_named_commit_passes(self):
        self.write("specs/900-x/tasks/README.md", DONE_1)
        self.write("specs/900-x/tasks/001-one.md", NOTES)
        self.commit("[WIP] Task 1: One — complete")
        self.commit_extra()
        self.assertEqual(self.run_check(), ([], 1))

    def commit_extra(self):
        self.write("docs/b.md", "y")
        self.commit("[WIP] Task 2: Two — agent execution complete")

    def test_missing_notes_fails(self):
        self.write("specs/900-x/tasks/README.md", DONE_1)
        self.write("specs/900-x/tasks/001-one.md", NO_NOTES)
        self.commit("[WIP] Task 1: One - complete")
        problems, _ = self.run_check()
        self.assertEqual(len(problems), 1)
        self.assertIn("Completion Notes", problems[0])

    def test_no_commit_names_the_task_fails_when_several_commits(self):
        self.write("specs/900-x/tasks/README.md", DONE_1)
        self.write("specs/900-x/tasks/001-one.md", NOTES)
        self.commit("[WIP] Task 2: Two - complete")
        self.commit_extra()
        problems, _ = self.run_check()
        self.assertEqual(len(problems), 1)
        self.assertIn("no commit", problems[0])

    def test_squashed_single_commit_needs_notes_only(self):
        self.write("specs/900-x/tasks/README.md", DONE_1)
        self.write("specs/900-x/tasks/001-one.md", NOTES)
        self.commit("feat(x): the squashed feature")
        self.assertEqual(self.run_check(), ([], 1))

    def test_squashed_commit_under_a_merge_commit_needs_notes_only(self):
        # CI checks out the pull request merge ref: a merge commit sits on top of the single squashed commit.
        self.write("specs/900-x/tasks/README.md", DONE_1)
        self.write("specs/900-x/tasks/001-one.md", NOTES)
        self.commit("feat(x): the squashed feature")
        self.git("checkout", "-q", "-b", "side", "base")
        self.write("docs/c.md", "z")
        self.commit("main moved")
        self.git("branch", "-f", "base", "side")
        self.git("checkout", "-q", "work")
        self.git("merge", "-q", "--no-ff", "-m", "Merge side into work", "side")
        self.assertEqual(self.run_check(), ([], 1))

    def test_already_complete_at_base_is_ignored(self):
        self.git("checkout", "-q", "main")
        self.write("specs/900-x/tasks/README.md", DONE_1)
        self.commit("old complete")
        self.git("branch", "-f", "base", "main")
        self.git("checkout", "-q", "work")
        self.git("rebase", "-q", "main")
        self.write("docs/a.md", "x")
        self.commit("docs")
        self.assertEqual(self.run_check(), ([], 0))

    def test_template_placeholders_are_not_notes(self):
        self.write("specs/900-x/tasks/README.md", DONE_1)
        self.write("specs/900-x/tasks/001-one.md", TEMPLATE_NOTES)
        self.commit("feat(x): the squashed feature")
        problems, _ = self.run_check()
        self.assertEqual(problems, ["900-x task 001: marked Complete without filled Completion Notes"])
        self.assertEqual(checker.completion_notes(TEMPLATE_NOTES), "")
        filled = TEMPLATE_NOTES.replace("[actual files]", "`src/a.py` (see [the plan](../plan.md))")
        self.assertEqual(checker.completion_notes(filled), "**Files changed**: `src/a.py` (see [the plan](../plan.md))")
        self.assertEqual(checker.completion_notes("## Completion Notes\n\n- [x] checked by hand\n"), "- [x] checked by hand")

    def test_a_task_index_row_without_a_task_file_fails(self):
        self.write("specs/900-x/tasks/README.md", ROWS + "| 001 | One | a | None | Pending |\n| 002 | Two | a | 001 | Complete |\n")
        self.commit("feat(x): the squashed feature")
        self.assertEqual(self.run_check(), (["900-x task 002: marked Complete but has no task file"], 1))

    def run_main(self, *args, profile=None):
        path = os.path.join(self.repo, ".claude", "quality-profile.json")
        if profile is not None:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(profile, fh)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = checker.main(["--profile", path, *args])
        return code, out.getvalue() + err.getvalue()

    def test_an_unset_integration_ref_prints_one_line_and_passes(self):
        for profile in ({"integrationRef": ""}, {}):
            code, out = self.run_main(profile=profile)
            self.assertEqual(code, 0, out)
            self.assertEqual(out.splitlines(),
                             ["task-evidence: integrationRef is unset in the binding and no --base given; no range to check"])

    def test_the_integration_ref_or_base_selects_the_range(self):
        self.write("specs/900-x/tasks/README.md", DONE_1)
        self.write("specs/900-x/tasks/001-one.md", NO_NOTES)
        self.commit("feat(x): the squashed feature")
        code, out = self.run_main(profile={"integrationRef": "base"})
        self.assertEqual(code, 1, out)
        self.assertIn("task-evidence: 900-x task 001: marked Complete without filled Completion Notes", out)
        self.assertEqual(self.run_main("--base", "HEAD", profile={"integrationRef": ""})[0], 0)
        self.assertEqual(self.run_main("--base", "no-such-ref")[0], 2)
        os.remove(os.path.join(self.repo, ".claude", "quality-profile.json"))
        self.assertEqual(self.run_main("--base", "base"), (0, "task-evidence: no .claude/quality-profile.json; run python3 scripts/forge/quality_profile.py init\n"))

    def test_names_task_matches_number_not_prefix(self):
        self.assertTrue(checker.names_task("[WIP] Task 3: x", "003"))
        self.assertTrue(checker.names_task("fix (T3)", "003"))
        self.assertFalse(checker.names_task("[WIP] Task 13: x", "003"))
        self.assertFalse(checker.names_task("[WIP] Task 30: x", "003"))



STATUS_DONE = "# Task\n\n**Status**: Complete\n\n## Completion Notes\n\nDone, gates green.\n"
STATUS_OPEN = "# Task\n\n**Status**: In Progress\n\n## Completion Notes\n\nDone, gates green.\n"
RATIONALE = ("\n## Rationale\n\n| # | Decision | Why |\n|---|---|---|\n| 001 | Split | Pending |\n"
             "| 002 | Merge | Complete |\n| 003 | Extra | Complete |\n")


class StatusAgreement(EvidenceRepo):
    """The task file's Status line and the tasks/README.md row must agree for a newly Complete task."""

    def test_task_file_complete_while_the_readme_row_is_pending_is_flagged(self):
        self.write("specs/900-x/tasks/001-one.md", STATUS_DONE)
        self.commit("feat(x): one")
        problems, examined = self.run_check()
        self.assertEqual(examined, 1)
        self.assertEqual(problems, ["900-x task 001: task file Status is Complete while tasks/README.md row is 'Pending'"])

    def test_readme_complete_while_the_task_file_is_in_progress_is_flagged(self):
        self.write("specs/900-x/tasks/README.md", DONE_1)
        self.write("specs/900-x/tasks/001-one.md", STATUS_OPEN)
        self.commit("feat(x): one")
        problems, examined = self.run_check()
        self.assertEqual(examined, 1)
        self.assertEqual(problems, ["900-x task 001: task file Status is 'In Progress' while tasks/README.md marks it "
                                    "Complete"])

    def test_both_complete_is_ok(self):
        self.write("specs/900-x/tasks/README.md", DONE_1)
        self.write("specs/900-x/tasks/001-one.md", STATUS_DONE)
        self.commit("feat(x): one")
        self.assertEqual(self.run_check(), ([], 1))

    def test_complete_with_a_remark_is_accepted(self):
        self.write("specs/900-x/tasks/README.md", DONE_1)
        self.write("specs/900-x/tasks/001-one.md", STATUS_DONE.replace("Complete\n\n##", "Complete (header set by x)\n\n##", 1))
        self.commit("feat(x): one")
        self.assertEqual(self.run_check(), ([], 1))

    def test_a_later_numbered_non_status_table_does_not_hide_or_add_rows(self):
        # A rationale table after the task index (last cell free text, even "Complete") is not a status table.
        self.write("specs/900-x/tasks/README.md", DONE_1 + RATIONALE)
        self.write("specs/900-x/tasks/001-one.md", STATUS_DONE)
        self.commit("feat(x): one")
        self.assertEqual(self.run_check(), ([], 1))

    def test_first_row_per_task_number_wins(self):
        again = "\n## Review\n\n" + ROWS + "| 001 | One again | a | None | Pending |\n"
        self.write("specs/900-x/tasks/README.md", DONE_1 + again)
        self.write("specs/900-x/tasks/001-one.md", STATUS_DONE)
        self.commit("feat(x): one")
        self.assertEqual(self.run_check(), ([], 1))

    def test_task_file_without_a_status_line_is_not_flagged(self):
        self.write("specs/900-x/tasks/README.md", DONE_1)
        self.write("specs/900-x/tasks/001-one.md", NOTES)
        self.commit("feat(x): one")
        self.assertEqual(self.run_check(), ([], 1))

    def test_one_task_gets_one_set_of_lines_when_both_sources_mark_it_complete(self):
        self.write("specs/900-x/tasks/README.md", DONE_1)
        self.write("specs/900-x/tasks/001-one.md", "# Task\n\n**Status**: Complete\n")
        self.commit("feat(x): one")
        problems, examined = self.run_check()
        self.assertEqual(examined, 1)
        self.assertEqual(len(problems), 1)
        self.assertIn("Completion Notes", problems[0])

    def test_task_file_complete_at_the_base_is_not_new(self):
        self.git("checkout", "-q", "main")
        self.write("specs/900-x/tasks/001-one.md", STATUS_DONE)
        self.commit("old")
        self.git("branch", "-f", "base", "main")
        self.git("checkout", "-q", "work")
        self.git("rebase", "-q", "main")
        self.write("specs/900-x/tasks/001-one.md", STATUS_DONE + "\nextra line\n")
        self.commit("tweak")
        self.assertEqual(self.run_check(), ([], 0))

    def test_unit_helpers(self):
        self.assertEqual(checker.row_statuses(DONE_1 + RATIONALE), {"001": "Complete", "002": "Pending"})
        self.assertEqual(checker.complete_ids(DONE_1 + RATIONALE), {"001"})
        self.assertEqual(checker.task_status("# T\n\n**Status**: Complete (x)  \n"), "Complete (x)")
        self.assertIsNone(checker.task_status("# T\n"))
        self.assertTrue(checker.is_complete("Complete"))
        self.assertTrue(checker.is_complete("Complete (remark)"))
        self.assertFalse(checker.is_complete("Completed"))
        self.assertFalse(checker.is_complete("Incomplete"))
        self.assertFalse(checker.is_complete(None))


if __name__ == "__main__":
    unittest.main()
