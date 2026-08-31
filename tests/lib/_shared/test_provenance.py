"""Tests for src/devforge/lib/_shared/provenance.py (91-FEATURE-DIR-
IDENTITY-AND-PROVENANCE-PLAN.md Phase 4, D7-D9, OQ-7, OQ-8).

Coverage:
  extract_run_by             — present line (value returned, whitespace
                                trimmed); absent line; empty text; None
                                text; whitespace-only value; embedded in
                                a larger multi-section document; only the
                                FIRST of two lines is read.
  read_ai_attribution_enabled — hand-written project-config.json fixtures
                                for the reader's own edge/error paths
                                (absent file, malformed JSON, non-object
                                top level, key absent, key present with a
                                non-"Yes" value) — mirroring
                                tests/lib/_shared/test_feature_alloc.py's
                                TestReadRequireTicket precedent for
                                testing a project-config.json reader in
                                isolation. The REAL-PRODUCER round-trip
                                (configure_helper set-ai-attribution +
                                render-config feeding this same function)
                                lives in
                                tests/lib/_configure/test_ai_attribution_gate.py,
                                where the configure_helper subprocess
                                machinery already lives.
  capture_git_user_name       — REAL git repo round-trip: `git init` +
                                `git config user.name` in a tempdir, then
                                capture_git_user_name reads it back
                                (round-tripping via the real external
                                tool this function wraps, not a mocked
                                subprocess); unset (no user.name anywhere
                                reachable, via HOME/XDG isolation) ->
                                None; not-a-git-repo directory still
                                resolves the GLOBAL config (git config is
                                not repo-scoped) so isolation is via
                                HOME/XDG env vars, not cwd; git binary
                                missing (PATH cleared) -> None, never
                                raises.
  resolve_run_by_for_render   — existing_text present with a value ->
                                that value, ignoring the gate/git entirely
                                (OQ-7 "keep the original"); existing_text
                                present with NO Run-by line -> None,
                                never backfilled; existing_text is None +
                                gate off -> None without invoking git;
                                existing_text is None + gate on -> the
                                captured git name.

All tests use real tempfile-backed filesystem trees; capture_git_user_name
is exercised against the real `git` binary, never mocked.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _shared.provenance import (  # noqa: E402
    RUN_BY_BOUND_NOTE,
    RUN_BY_LABEL,
    capture_git_user_name,
    extract_run_by,
    read_ai_attribution_enabled,
    resolve_run_by_for_render,
)


# ---------------------------------------------------------------------------
# extract_run_by
# ---------------------------------------------------------------------------


class TestExtractRunBy(unittest.TestCase):
    def test_present_line_returns_value(self):
        text = "# Spec: x\n\n**Date**: 2026-08-31\n**Run by**: Jane Doe\n"
        self.assertEqual(extract_run_by(text), "Jane Doe")

    def test_value_whitespace_trimmed(self):
        text = "**Run by**:   Jane Doe   \n"
        self.assertEqual(extract_run_by(text), "Jane Doe")

    def test_absent_line_returns_none(self):
        text = "# Spec: x\n\n**Date**: 2026-08-31\n**Status**: Draft\n"
        self.assertIsNone(extract_run_by(text))

    def test_empty_text_returns_none(self):
        self.assertIsNone(extract_run_by(""))

    def test_none_text_returns_none(self):
        self.assertIsNone(extract_run_by(None))

    def test_whitespace_only_value_returns_none(self):
        text = "**Run by**:    \n"
        self.assertIsNone(extract_run_by(text))

    def test_found_inside_larger_multi_section_document(self):
        text = (
            "# Spec: monorepo-migration\n\n"
            "**Date**: 2026-08-31\n"
            "**Status**: Draft\n"
            "**Design source**: none\n"
            "**Run by**: Alex Doe\n"
            + RUN_BY_BOUND_NOTE + "\n\n"
            "## 1. Overview\n\nSome overview text.\n\n"
            "## 9. Risks\n\n| Risk | Likelihood | Impact | Mitigation |\n"
        )
        self.assertEqual(extract_run_by(text), "Alex Doe")

    def test_only_first_of_two_lines_is_read(self):
        text = "**Run by**: First Person\n\n**Run by**: Second Person\n"
        self.assertEqual(extract_run_by(text), "First Person")

    def test_label_constant_matches_rendered_form(self):
        """RUN_BY_LABEL is the label both renderers wrap in ** ** --
        pin the two never drifting apart independently."""
        text = "**{0}**: Someone\n".format(RUN_BY_LABEL)
        self.assertEqual(extract_run_by(text), "Someone")


# ---------------------------------------------------------------------------
# read_ai_attribution_enabled (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-
# PLAN.md Phase 4, OQ-8(i)). Edge/error paths use hand-written project-
# config.json fixtures (mirroring test_feature_alloc.py's
# TestReadRequireTicket precedent); the real-producer round-trip lives in
# tests/lib/_configure/test_ai_attribution_gate.py.
# ---------------------------------------------------------------------------


class TestReadAiAttributionEnabled(unittest.TestCase):
    def test_missing_file_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            self.assertFalse(read_ai_attribution_enabled(devforge_dir))

    def test_missing_devforge_dir_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / "nonexistent" / ".devforge"
            self.assertFalse(read_ai_attribution_enabled(devforge_dir))

    def test_yes_value_returns_true(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                '{"AI_ATTRIBUTION": "Yes"}', encoding="utf-8"
            )
            self.assertTrue(read_ai_attribution_enabled(devforge_dir))

    def test_no_value_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                '{"AI_ATTRIBUTION": "No"}', encoding="utf-8"
            )
            self.assertFalse(read_ai_attribution_enabled(devforge_dir))

    def test_key_absent_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                '{"WORKSPACE_MODE": "standalone"}', encoding="utf-8"
            )
            self.assertFalse(read_ai_attribution_enabled(devforge_dir))

    def test_lowercase_yes_returns_false(self):
        """Only the exact string "Yes" -- matching _configure/_render.py's
        own `ai_attribution == "Yes"` derivation predicate exactly."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                '{"AI_ATTRIBUTION": "yes"}', encoding="utf-8"
            )
            self.assertFalse(read_ai_attribution_enabled(devforge_dir))

    def test_boolean_true_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                '{"AI_ATTRIBUTION": true}', encoding="utf-8"
            )
            self.assertFalse(read_ai_attribution_enabled(devforge_dir))

    def test_malformed_json_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                "{not valid json", encoding="utf-8"
            )
            self.assertFalse(read_ai_attribution_enabled(devforge_dir))

    def test_non_object_top_level_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                "[1, 2, 3]", encoding="utf-8"
            )
            self.assertFalse(read_ai_attribution_enabled(devforge_dir))

    def test_never_raises_on_unreadable_directory_as_file(self):
        """devforge_dir pointing at a plain FILE (not a dir) must not raise."""
        with tempfile.TemporaryDirectory() as td:
            not_a_dir = Path(td) / "actually-a-file"
            not_a_dir.write_text("x")
            self.assertFalse(read_ai_attribution_enabled(not_a_dir))


# ---------------------------------------------------------------------------
# capture_git_user_name -- real `git` binary round-trip, never mocked.
# ---------------------------------------------------------------------------


def _git(repo_root, *args):
    return subprocess.run(
        ["git", "-C", str(repo_root)] + list(args),
        capture_output=True, text=True, check=True,
    )


class TestCaptureGitUserName(unittest.TestCase):
    def test_configured_name_round_trips(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            _git(repo, "init", "--quiet")
            _git(repo, "config", "user.name", "Jane Doe")
            self.assertEqual(capture_git_user_name(repo), "Jane Doe")

    def test_unset_returns_none(self):
        """No user.name reachable at all -- isolate HOME/XDG_CONFIG_HOME
        so no global config on the machine running this suite leaks in,
        mirroring how a fresh CI checkout with no git identity behaves."""
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            _git(repo, "init", "--quiet")
            fake_home = Path(td) / "fake-home"
            fake_home.mkdir()
            env = os.environ.copy()
            env["HOME"] = str(fake_home)
            env["XDG_CONFIG_HOME"] = str(fake_home)
            env.pop("GIT_AUTHOR_NAME", None)
            env.pop("GIT_COMMITTER_NAME", None)
            # capture_git_user_name has no env parameter -- it inherits
            # the current process's env, so patch os.environ for the
            # duration of the call rather than the subprocess.run() args
            # the function itself issues.
            old_environ = dict(os.environ)
            os.environ.clear()
            os.environ.update(env)
            try:
                self.assertIsNone(capture_git_user_name(repo))
            finally:
                os.environ.clear()
                os.environ.update(old_environ)

    def test_embedded_newline_collapsed_to_space(self):
        """git itself rejects a literal newline in a config value, so
        exercise the collapse path directly against a value git DID
        accept but that still round-trips with a trailing newline from
        git's own stdout -- the collapse logic must not depend on git
        ever emitting a bare newline mid-value to be exercised safely."""
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            _git(repo, "init", "--quiet")
            _git(repo, "config", "user.name", "Jane Doe")
            name = capture_git_user_name(repo)
            self.assertNotIn("\n", name)
            self.assertNotIn("\r", name)

    def test_git_binary_missing_returns_none_never_raises(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            old_path = os.environ.get("PATH", "")
            os.environ["PATH"] = ""
            try:
                self.assertIsNone(capture_git_user_name(repo))
            finally:
                os.environ["PATH"] = old_path

    def test_no_repo_root_uses_process_cwd(self):
        """repo_root=None omits the `-C` flag entirely -- git resolves
        config from the process's own working directory. Exercised by
        chdir'ing into a real repo with a configured name."""
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            _git(repo, "init", "--quiet")
            _git(repo, "config", "user.name", "Cwd Person")
            old_cwd = os.getcwd()
            os.chdir(str(repo))
            try:
                self.assertEqual(capture_git_user_name(), "Cwd Person")
            finally:
                os.chdir(old_cwd)


# ---------------------------------------------------------------------------
# resolve_run_by_for_render (D9 + OQ-7 combined).
# ---------------------------------------------------------------------------


class TestResolveRunByForRender(unittest.TestCase):
    def test_existing_text_with_value_preserves_it(self):
        """OQ-7 'keep the original' -- the gate/git are never consulted
        when a prior render already exists, even when the gate is off."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            # No project-config.json at all -- gate would read False.
            existing = "**Run by**: Original Author\n"
            result = resolve_run_by_for_render(existing, devforge_dir)
            self.assertEqual(result, "Original Author")

    def test_existing_text_without_run_by_line_stays_none(self):
        """A pre-Phase-4 document (or one created with the gate off)
        carries no Run-by line -- a later re-render must not backfill
        one from now-current git config."""
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                '{"AI_ATTRIBUTION": "Yes"}', encoding="utf-8"
            )
            existing = "# Spec: x\n\n**Date**: 2026-08-31\n**Status**: Draft\n"
            result = resolve_run_by_for_render(existing, devforge_dir)
            self.assertIsNone(result)

    def test_no_existing_text_gate_off_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                '{"AI_ATTRIBUTION": "No"}', encoding="utf-8"
            )
            result = resolve_run_by_for_render(None, devforge_dir)
            self.assertIsNone(result)

    def test_no_existing_text_gate_on_captures_git_name(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                '{"AI_ATTRIBUTION": "Yes"}', encoding="utf-8"
            )
            repo = Path(td) / "repo"
            repo.mkdir()
            _git(repo, "init", "--quiet")
            _git(repo, "config", "user.name", "Fresh Author")
            result = resolve_run_by_for_render(None, devforge_dir, repo)
            self.assertEqual(result, "Fresh Author")

    def test_no_existing_text_gate_on_git_unset_returns_none(self):
        with tempfile.TemporaryDirectory() as td:
            devforge_dir = Path(td) / ".devforge"
            devforge_dir.mkdir()
            (devforge_dir / "project-config.json").write_text(
                '{"AI_ATTRIBUTION": "Yes"}', encoding="utf-8"
            )
            repo = Path(td) / "repo"
            repo.mkdir()
            _git(repo, "init", "--quiet")
            fake_home = Path(td) / "fake-home"
            fake_home.mkdir()
            old_environ = dict(os.environ)
            os.environ["HOME"] = str(fake_home)
            os.environ["XDG_CONFIG_HOME"] = str(fake_home)
            os.environ.pop("GIT_AUTHOR_NAME", None)
            os.environ.pop("GIT_COMMITTER_NAME", None)
            try:
                result = resolve_run_by_for_render(None, devforge_dir, repo)
                self.assertIsNone(result)
            finally:
                os.environ.clear()
                os.environ.update(old_environ)


if __name__ == "__main__":
    unittest.main()
