"""Tests for the "Run by:" provenance line on rendered research-report.md
(91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 4, D7-D9, OQ-7,
OQ-8).

Coverage:
  render / cmd_render — name set + AI_ATTRIBUTION="Yes" -> the line
                         renders, with the bound note right below it;
                         name unset (no git identity reachable) ->
                         ABSENT, never "unknown" or an empty value;
                         AI_ATTRIBUTION="No" (or the gate never
                         configured at all) -> ABSENT regardless of the
                         configured name.
  --existing-path        (OQ-7's read-back, KNOWN GAP -- see cmd_render's
                         own docstring): omitted -> always a fresh
                         capture, matching today's only real call site
                         (a first-time render with nothing to preserve);
                         given and the target file already carries a
                         Run-by line -> that value is preserved even
                         when the configured git name has since changed;
                         given and the target file carries NO Run-by
                         line (a pre-Phase-4 report, or one created with
                         the gate off) -> stays absent, never backfilled;
                         given but the file does not exist -> treated
                         identically to omitted (fresh capture).

Subprocess pattern mirrors tests/lib/test_research_helper.py: real
research_helper subcommands build state. project-config.json (a SIBLING
input this render logic reads -- see
tests/lib/_configure/test_ai_attribution_gate.py for the configure_helper
round-trip) and the git identity are both written directly against the
real consumers (a real project-config.json file, a real `git` repo).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "src" / "devforge" / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

HELPER = LIB / "research_helper.py"


def _run(devforge_dir, *args, env=None, cwd=None):
    return subprocess.run(
        [sys.executable, str(HELPER), "--devforge-dir", str(devforge_dir)] + list(args),
        capture_output=True, text=True, env=env, cwd=str(cwd) if cwd else None,
    )


def _git(repo_root, *args):
    return subprocess.run(
        ["git", "-C", str(repo_root)] + list(args),
        capture_output=True, text=True, check=True,
    )


class _RunByFixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.td = Path(self._tmp.name)
        self.dev = self.td / ".devforge"
        _git(self.td, "init", "--quiet")
        r = _run(self.dev, "reset-memo")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = _run(self.dev, "reset-report")
        self.assertEqual(r.returncode, 0, r.stderr)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_gate(self, enabled: bool):
        self.dev.mkdir(parents=True, exist_ok=True)
        (self.dev / "project-config.json").write_text(
            json.dumps({"AI_ATTRIBUTION": "Yes" if enabled else "No"}),
            encoding="utf-8",
        )

    def _set_git_name(self, name):
        _git(self.td, "config", "user.name", name)

    def _isolated_env(self):
        fake_home = self.td / "fake-home"
        fake_home.mkdir(exist_ok=True)
        env = os.environ.copy()
        env["HOME"] = str(fake_home)
        env["XDG_CONFIG_HOME"] = str(fake_home)
        env.pop("GIT_AUTHOR_NAME", None)
        env.pop("GIT_COMMITTER_NAME", None)
        return env


class TestResearchRunByFirstRender(_RunByFixture):
    def test_name_set_and_gate_on_renders(self):
        self._write_gate(enabled=True)
        self._set_git_name("Jane Doe")
        r = _run(self.dev, "render")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("**Run by**: Jane Doe", r.stdout)

    def test_bound_note_renders_alongside_the_line(self):
        self._write_gate(enabled=True)
        self._set_git_name("Jane Doe")
        r = _run(self.dev, "render")
        self.assertIn("not updated on later edits", r.stdout)

    def test_name_unset_is_absent_not_empty_not_unknown(self):
        self._write_gate(enabled=True)
        r = _run(self.dev, "render", env=self._isolated_env())
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("**Run by**", r.stdout)
        self.assertNotIn("unknown", r.stdout.lower())

    def test_gate_off_is_absent_regardless_of_name(self):
        self._write_gate(enabled=False)
        self._set_git_name("Jane Doe")
        r = _run(self.dev, "render")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("**Run by**", r.stdout)

    def test_gate_never_configured_is_absent(self):
        self._set_git_name("Jane Doe")
        r = _run(self.dev, "render")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("**Run by**", r.stdout)

    def test_git_config_reads_repo_root_not_process_cwd(self):
        """Regression guard for the repo_root omission the build caught:
        cmd_render must resolve `git config user.name` against
        repo_root (Path(devforge_dir).resolve().parent) via an explicit
        `git -C <repo_root>`, never against whatever directory the
        research_helper PROCESS happens to be standing in.

        Launches the helper with its own cwd pointed at a SEPARATE git
        repo carrying a DIFFERENT identity than repo_root's. A bare
        `_run(self.dev, "render")` call (used by every other test in
        this file) inherits the pytest process's OWN cwd -- which, for
        this suite, is this framework's own checkout -- and a
        regression back to reading the ambient cwd could coincidentally
        still return the right-looking value there (or a machine
        default), masking the bug. Pinning an explicit, different `cwd`
        removes that coincidence: this test fails on the pre-fix code
        regardless of where the suite itself is invoked from.
        """
        self._write_gate(enabled=True)
        self._set_git_name("Correct Name")  # repo_root's (self.td's) local config

        decoy = tempfile.TemporaryDirectory()
        try:
            decoy_root = Path(decoy.name)
            _git(decoy_root, "init", "--quiet")
            _git(decoy_root, "config", "user.name", "Decoy Name")

            r = _run(self.dev, "render", cwd=decoy_root)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("**Run by**: Correct Name", r.stdout)
            self.assertNotIn("Decoy Name", r.stdout)
        finally:
            decoy.cleanup()


class TestResearchRunByExistingPath(_RunByFixture):
    """OQ-7's read-back, wired via the explicit --existing-path flag
    (see cmd_render's own docstring for why research needs this flag
    where /devforge:specify does not)."""

    def _first_render_and_write(self):
        r = _run(self.dev, "render")
        self.assertEqual(r.returncode, 0, r.stderr)
        report_path = self.td / "specs" / "007-fixture" / "research-report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(r.stdout, encoding="utf-8")
        return report_path

    def test_omitted_existing_path_always_captures_fresh(self):
        """No --existing-path -- matches today's only call site: even
        though a report already sits on disk, this run doesn't know
        about it and behaves exactly like a first-time render."""
        self._write_gate(enabled=True)
        self._set_git_name("Original Author")
        report_path = self._first_render_and_write()
        self.assertIn("**Run by**: Original Author", report_path.read_text(encoding="utf-8"))

        self._set_git_name("Someone Else")
        r2 = _run(self.dev, "render")  # no --existing-path
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("**Run by**: Someone Else", r2.stdout)

    def test_existing_path_preserves_original_after_name_change(self):
        self._write_gate(enabled=True)
        self._set_git_name("Original Author")
        report_path = self._first_render_and_write()

        self._set_git_name("Someone Else")
        r2 = _run(self.dev, "render", "--existing-path", str(report_path))
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("**Run by**: Original Author", r2.stdout)
        self.assertNotIn("Someone Else", r2.stdout)

    def test_existing_path_to_pre_phase4_report_stays_absent(self):
        """A research-report.md with no Run-by line (pre-Phase-4, or
        created with the gate off) -- a re-render via --existing-path
        must not backfill one from now-current git config."""
        report_path = self.td / "specs" / "007-fixture" / "research-report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "# Research: fixture\n\n**Date**: 2026-08-31\n"
            "**Topic**: fixture\n**Mode**: Bug\n**Verdict**: (unset)\n",
            encoding="utf-8",
        )
        self._write_gate(enabled=True)
        self._set_git_name("Newly Configured")
        r = _run(self.dev, "render", "--existing-path", str(report_path))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("**Run by**", r.stdout)

    def test_existing_path_to_nonexistent_file_captures_fresh(self):
        """--existing-path pointing at a file that isn't there yet is
        treated identically to a first-time render."""
        self._write_gate(enabled=True)
        self._set_git_name("Fresh Author")
        missing = self.td / "specs" / "007-fixture" / "research-report.md"
        r = _run(self.dev, "render", "--existing-path", str(missing))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("**Run by**: Fresh Author", r.stdout)


if __name__ == "__main__":
    unittest.main()
