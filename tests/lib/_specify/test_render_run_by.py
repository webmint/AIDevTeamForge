"""Tests for the "Run by:" provenance line on rendered spec.md
(91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 4, D7-D9, OQ-7,
OQ-8).

Coverage:
  render / cmd_render        — name set + AI_ATTRIBUTION="Yes" -> the
                                line renders, with the bound note right
                                below it; name unset (no git identity
                                reachable) -> ABSENT, never "unknown" or
                                an empty value; AI_ATTRIBUTION="No" (or
                                absent) -> ABSENT regardless of the
                                configured name.
  verify-rendered             — re-render after a grill-re-entry-style
                                revision (a pre-existing spec.md with
                                its own Run-by line already on disk)
                                PRESERVES the original value even when
                                the configured git name has changed
                                since -- OQ-7's "keep the original".
                                verify-rendered itself must still pass
                                (0, no drift) against that preserved
                                value.

Subprocess pattern mirrors tests/lib/test_specify_helper.py: real
specify_helper subcommands build state, no hand-fabricated
specify-state.json. project-config.json (a SIBLING input this render
logic reads, not itself under test here -- see
tests/lib/_configure/test_ai_attribution_gate.py for the
configure_helper round-trip) and the git identity are both written
directly against the real consumers (a real project-config.json file,
a real `git` repo), per this repo's real-fixture-testing rule for
anything that parses another tool's output.
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

HELPER = LIB / "specify_helper.py"


def _run(devforge_dir, *args, env=None):
    return subprocess.run(
        [sys.executable, str(HELPER), "--devforge-dir", str(devforge_dir)] + list(args),
        capture_output=True, text=True, env=env,
    )


def _git(repo_root, *args):
    return subprocess.run(
        ["git", "-C", str(repo_root)] + list(args),
        capture_output=True, text=True, check=True,
    )


class _RunByFixture(unittest.TestCase):
    """Layout every test in this file shares:

        td/                          <- repo_root (a real git repo)
          .devforge/                 <- devforge_dir
            project-config.json      <- AI_ATTRIBUTION gate
          specs/007-run-by-fixture/  <- resolved feature dir (legacy shape,
                                        matching assign-feature-name's own
                                        _feature_dir_display fallback
                                        composition when spec_number is
                                        unset -- "NNN" -- so the target
                                        spec.md path this test writes to
                                        MUST equal what render's own
                                        internal resolution computes, or
                                        the read-back would look in the
                                        wrong place)
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.td = Path(self._tmp.name)
        self.dev = self.td / ".devforge"
        _git(self.td, "init", "--quiet")
        r = _run(self.dev, "reset-state")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = _run(self.dev, "set-date", "--date", "2026-08-31")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = _run(self.dev, "assign-feature-name", "--feature-name", "run-by-fixture")
        self.assertEqual(r.returncode, 0, r.stderr)
        # _feature_dir_display's fallback composition when spec_number is
        # unset: "specs/NNN-{feature_name}".
        self.spec_dir = self.td / "specs" / "NNN-run-by-fixture"

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
        """An env with NO git identity reachable via global/system config.

        `_set_git_name` always wins regardless of this (it writes the
        LOCAL repo config, which git prefers over global/system), so
        this is only needed by tests asserting ABSENCE of any name --
        without it, this suite would pass or fail depending on whether
        the machine running it happens to have a global
        `git config user.name` set, which is exactly the flakiness a
        real-fixture test must not have.
        """
        fake_home = self.td / "fake-home"
        fake_home.mkdir(exist_ok=True)
        env = os.environ.copy()
        env["HOME"] = str(fake_home)
        env["XDG_CONFIG_HOME"] = str(fake_home)
        env.pop("GIT_AUTHOR_NAME", None)
        env.pop("GIT_COMMITTER_NAME", None)
        return env


class TestRunByFirstRender(_RunByFixture):
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
        """No git identity reachable anywhere (a bare `git init` with no
        user.name ever configured, local or global, and HOME/XDG
        isolated so a real global config on the machine running this
        suite cannot leak in) -- the line must not appear at all."""
        self._write_gate(enabled=True)
        # Deliberately no _set_git_name call.
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
        """No project-config.json at all (e.g. a manual /specify run
        with no /devforge:configure yet) -- fail-closed, no name leaks.
        The gate check happens before git is ever consulted, so this
        passes even without an isolated env or a configured name."""
        self._set_git_name("Jane Doe")
        r = _run(self.dev, "render")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("**Run by**", r.stdout)


class TestRunByRerender(_RunByFixture):
    """OQ-7: /devforge:specify rewrites spec.md on a grill re-entry.
    The Run-by value already on disk must survive that re-render even
    when the configured git name has since changed."""

    def _first_render_and_write(self):
        r = _run(self.dev, "render")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.spec_dir.mkdir(parents=True, exist_ok=True)
        spec_path = self.spec_dir / "spec.md"
        spec_path.write_text(r.stdout, encoding="utf-8")
        return spec_path

    def test_rerender_preserves_original_value_after_name_change(self):
        self._write_gate(enabled=True)
        self._set_git_name("Original Author")
        spec_path = self._first_render_and_write()
        self.assertIn("**Run by**: Original Author", spec_path.read_text(encoding="utf-8"))

        # The configured name changes between the first render and the
        # re-render -- simulating a different machine/session running
        # the grill re-entry.
        self._set_git_name("Someone Else")
        r2 = _run(self.dev, "render")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("**Run by**: Original Author", r2.stdout)
        self.assertNotIn("Someone Else", r2.stdout)

    def test_rerender_after_gate_turned_off_still_preserves(self):
        """The value was captured while the gate was on; the gate is
        turned off before the re-entry revision. OQ-7's "keep the
        original" wins over re-checking the gate on every render --
        the gate only governs FRESH capture, never a preserved value."""
        self._write_gate(enabled=True)
        self._set_git_name("Original Author")
        self._first_render_and_write()

        self._write_gate(enabled=False)
        r2 = _run(self.dev, "render")
        self.assertEqual(r2.returncode, 0, r2.stderr)
        self.assertIn("**Run by**: Original Author", r2.stdout)

    def test_rerender_of_a_pre_phase4_spec_stays_absent(self):
        """A spec.md written before this field existed (or with the
        gate off / no identity at creation) carries no Run-by line --
        a later re-render must not backfill one from now-current git
        config, even when the gate is on and a name is now available."""
        self.spec_dir.mkdir(parents=True, exist_ok=True)
        (self.spec_dir / "spec.md").write_text(
            "# Spec: run-by-fixture\n\n**Date**: 2026-08-31\n"
            "**Status**: Draft\n**Design source**: none\n\n"
            "## 1. Overview\n",
            encoding="utf-8",
        )
        self._write_gate(enabled=True)
        self._set_git_name("Newly Configured")
        r = _run(self.dev, "render")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("**Run by**", r.stdout)

    def test_verify_rendered_passes_against_the_preserved_value(self):
        self._write_gate(enabled=True)
        self._set_git_name("Original Author")
        spec_path = self._first_render_and_write()

        self._set_git_name("Someone Else")
        r = _run(
            self.dev, "verify-rendered", "--path", str(spec_path),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stderr.strip(), "")

    def test_verify_rendered_still_catches_unrelated_tamper(self):
        """The Run-by exemption must not blind verify-rendered to a
        tampered NON-Run-by line."""
        self._write_gate(enabled=True)
        self._set_git_name("Original Author")
        spec_path = self._first_render_and_write()
        disk = spec_path.read_text(encoding="utf-8")
        tampered = disk.replace("## 1. Overview", "## 1. OverviewTAMPERED", 1)
        spec_path.write_text(tampered, encoding="utf-8")

        r = _run(
            self.dev, "verify-rendered", "--path", str(spec_path),
        )
        self.assertEqual(r.returncode, 2)
        self.assertIn("drift at line", r.stderr)


if __name__ == "__main__":
    unittest.main()
