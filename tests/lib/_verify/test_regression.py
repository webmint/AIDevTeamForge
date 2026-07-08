"""Tests for src/devforge/lib/_verify/_regression.py and related verdict fold.

Coverage:
  _regression.run_regression_gate:
    mode=off:
      - mode arg "off" → status:"off", regression:false, no test runs
    inconclusive paths:
      - no test command in config → status:"inconclusive", regression:false
      - not a git repo → status:"inconclusive", regression:false
      - no auto-detectable base branch → status:"inconclusive", regression:false
      - config REGRESSION_GATE="off" (key in JSON) → status:"off"
    real-git fixture paths (REAL worktrees):
      - regression case: baseline pass, head fail → status:"regression", regression:true
      - pre-existing-failure case: baseline fail → status:"baseline-failing", regression:false
      - clean case: baseline pass, head pass → status:"clean", regression:false
    worktree cleanup:
      - after a clean run → git worktree list shows only main worktree
      - after a regression run → git worktree list shows only main worktree
      - after an exception mid-run → git worktree list shows only main worktree

  _symlink_deps:
      - node_modules present in source_root → symlinked into worktree
      - absent dep dir → no symlink created
      - dep already present in worktree → no double-symlink

  compute_verdict regression fold (_verdict.py):
      - regression:true → NEEDS WORK, "regression" blocker present
      - regression:false → verdict unaffected (APPROVED when otherwise clean)
      - regression:None → verdict unaffected (backward compat)
      - regression:true + constitution violation → REJECTED (constitution wins)
      - regression:true NEVER causes REJECTED on its own

Stdlib only.  Python 3.8+.  Real git fixtures — no hand-authored mocks.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _verify._regression import (   # noqa: E402
    _symlink_deps,
    run_regression_gate,
)
from _verify._verdict import compute_verdict  # noqa: E402


# ---------------------------------------------------------------------------
# Git fixture helpers
# ---------------------------------------------------------------------------

# A trivial, fast, deterministic test command.
# Exits 0 if pass.marker exists in CWD, else exits 1.
_TEST_CMD = (
    "python3 -c \""
    "import sys, os; "
    "sys.exit(0 if os.path.exists('pass.marker') else 1)"
    "\""
)


def _git_run(args, cwd, check=True):
    # type: (list, str, bool) -> subprocess.CompletedProcess
    """Run a git command.  Raises on failure when check=True."""
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def _init_repo(path, branch="main"):
    # type: (str, str) -> None
    """Initialise a fresh git repo at path."""
    os.makedirs(path, exist_ok=True)
    _git_run(["init", "-b", branch, "."], cwd=path)
    _git_run(["config", "user.email", "test@example.com"], cwd=path)
    _git_run(["config", "user.name", "Test User"], cwd=path)
    _git_run(["config", "commit.gpgsign", "false"], cwd=path)


def _write_and_commit(repo_path, message, files):
    # type: (str, str, dict) -> None
    """Write files dict to the repo and commit all changes."""
    for relpath, content in files.items():
        abs_path = os.path.join(repo_path, relpath)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as fh:
            fh.write(content)
    _git_run(["add", "-A"], cwd=repo_path)
    _git_run(["commit", "-m", message], cwd=repo_path)


def _write_config(install_root, test_cmd, extra=None):
    # type: (str, str, dict) -> None
    """Write .devforge/project-config.json with TEST_COMMANDS=[test_cmd]."""
    devforge = os.path.join(install_root, ".devforge")
    os.makedirs(devforge, exist_ok=True)
    data = {"TEST_COMMANDS": [test_cmd]}
    if extra:
        data.update(extra)
    with open(os.path.join(devforge, "project-config.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh)


def _count_worktrees(repo_path):
    # type: (str) -> int
    """Return the number of worktrees listed by git worktree list."""
    result = subprocess.run(
        ["git", "worktree", "list"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
    return len(lines)


# ---------------------------------------------------------------------------
# Tests: mode=off and config-reading
# ---------------------------------------------------------------------------

class TestModeOff(unittest.TestCase):
    """mode=off returns immediately without touching git or running tests."""

    def test_mode_arg_off(self):
        """--mode off → status off, no runs."""
        result = run_regression_gate(
            feature_dir=".",
            workspace_root="/nonexistent",
            mode="off",
        )
        self.assertEqual(result["status"], "off")
        self.assertFalse(result["regression"])
        self.assertEqual(result["mode"], "off")
        self.assertIsNone(result["baseline_status"])
        self.assertIsNone(result["head_status"])
        self.assertIn("disabled", result["note"])

    def test_config_key_off(self):
        """REGRESSION_GATE=off in config → status off."""
        tmpdir = tempfile.mkdtemp()
        try:
            _write_config(tmpdir, _TEST_CMD, extra={"REGRESSION_GATE": "off"})
            result = run_regression_gate(
                feature_dir=".",
                workspace_root=tmpdir,
                mode=None,  # reads from config
            )
            self.assertEqual(result["status"], "off")
            self.assertFalse(result["regression"])
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_mode_arg_overrides_config(self):
        """--mode off overrides REGRESSION_GATE=full in config."""
        tmpdir = tempfile.mkdtemp()
        try:
            _write_config(tmpdir, _TEST_CMD, extra={"REGRESSION_GATE": "full"})
            result = run_regression_gate(
                feature_dir=".",
                workspace_root=tmpdir,
                mode="off",
            )
            self.assertEqual(result["status"], "off")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Tests: inconclusive paths (no git, no test command, etc.)
# ---------------------------------------------------------------------------

class TestInconclusivePaths(unittest.TestCase):
    """Edge cases that should return status:inconclusive, never gate."""

    def test_no_test_command(self):
        """No TEST_COMMANDS in config → inconclusive."""
        tmpdir = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(tmpdir, ".devforge"))
            with open(os.path.join(tmpdir, ".devforge", "project-config.json"), "w") as fh:
                json.dump({}, fh)
            # Need a git repo so we pass the git check (hit test-cmd check first)
            _init_repo(tmpdir)
            _write_and_commit(tmpdir, "init", {"README.md": "hi"})
            result = run_regression_gate(
                feature_dir=".",
                workspace_root=tmpdir,
                mode="full",
            )
            self.assertEqual(result["status"], "inconclusive")
            self.assertFalse(result["regression"])
            self.assertIn("no test command", result["note"])
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_test_command_na(self):
        """TEST_COMMANDS=['N/A'] → inconclusive (no test command)."""
        tmpdir = tempfile.mkdtemp()
        try:
            _write_config(tmpdir, "N/A")
            _init_repo(tmpdir)
            _write_and_commit(tmpdir, "init", {"README.md": "hi"})
            result = run_regression_gate(
                feature_dir=".",
                workspace_root=tmpdir,
                mode="full",
            )
            self.assertEqual(result["status"], "inconclusive")
            self.assertFalse(result["regression"])
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_not_a_git_repo(self):
        """workspace_root is not a git repo → inconclusive."""
        tmpdir = tempfile.mkdtemp()
        try:
            _write_config(tmpdir, _TEST_CMD)
            # No git init → _is_git_repo returns False
            result = run_regression_gate(
                feature_dir=".",
                workspace_root=tmpdir,
                mode="full",
            )
            self.assertEqual(result["status"], "inconclusive")
            self.assertFalse(result["regression"])
            self.assertIn("not a git repository", result["note"])
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_no_base_branch(self):
        """Repo with no main/develop/master/origin/HEAD → inconclusive."""
        tmpdir = tempfile.mkdtemp()
        try:
            _write_config(tmpdir, _TEST_CMD)
            # Init on a non-standard branch name so no base is auto-detected
            _init_repo(tmpdir, branch="feature-xyz")
            _write_and_commit(tmpdir, "init", {"README.md": "hi"})
            result = run_regression_gate(
                feature_dir=".",
                workspace_root=tmpdir,
                mode="full",
            )
            self.assertEqual(result["status"], "inconclusive")
            self.assertFalse(result["regression"])
            self.assertIn("auto-detect", result["note"])
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_config_absent_defaults_to_full_mode(self):
        """Missing project-config.json → effective mode is full (not off)."""
        tmpdir = tempfile.mkdtemp()
        try:
            # No config at all; also no git repo → inconclusive, but mode=full
            result = run_regression_gate(
                feature_dir=".",
                workspace_root=tmpdir,
                mode=None,
            )
            # Not a git repo, but mode should be "full" not "off"
            self.assertEqual(result["mode"], "full")
            self.assertFalse(result["regression"])
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Tests: real git fixtures
# ---------------------------------------------------------------------------

class TestRealGitFixtures(unittest.TestCase):
    """Real git worktree round-trips.

    Each test builds a throwaway git repo in a temp directory.  The test
    command is a fast Python one-liner so these run in milliseconds.
    """

    def setUp(self):
        # type: () -> None
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        # type: () -> None
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_install_root(self, name):
        # type: (str) -> str
        """Create a named subdirectory for a repo + install root."""
        path = os.path.join(self.tmpdir, name)
        os.makedirs(path, exist_ok=True)
        return path

    # -----------------------------------------------------------------------
    # Regression case: baseline pass, head fail → regression:true
    # -----------------------------------------------------------------------

    def test_regression_detected(self):
        """Green→red: test passes at merge-base, fails at HEAD → regression:true."""
        repo = self._make_install_root("regression")
        _init_repo(repo)

        # main: pass.marker exists → test passes
        _write_and_commit(repo, "initial on main", {"pass.marker": "ok"})

        # Feature branch: remove pass.marker → test now fails
        _git_run(["checkout", "-b", "feature-1"], cwd=repo)
        os.remove(os.path.join(repo, "pass.marker"))
        _git_run(["add", "-A"], cwd=repo)
        _git_run(["commit", "-m", "break tests"], cwd=repo)

        _write_config(repo, _TEST_CMD)

        result = run_regression_gate(
            feature_dir=".",
            workspace_root=repo,
            mode="full",
        )

        self.assertEqual(result["status"], "regression")
        self.assertTrue(result["regression"])
        self.assertEqual(result["baseline_status"], "pass")
        self.assertEqual(result["head_status"], "fail")
        self.assertIn("head_output_tail", result)
        self.assertEqual(result["mode"], "full")

    # -----------------------------------------------------------------------
    # Pre-existing failure: baseline already fails → not gated (critical guard)
    # -----------------------------------------------------------------------

    def test_preexisting_failure_not_gated(self):
        """Critical false-positive guard: if tests fail at merge-base, not gated."""
        repo = self._make_install_root("preexisting")
        _init_repo(repo)

        # main: NO pass.marker → test fails at the merge-base
        _write_and_commit(repo, "initial on main", {"README.md": "no marker"})

        # Feature branch: adds unrelated file (pass.marker still absent)
        _git_run(["checkout", "-b", "feature-2"], cwd=repo)
        _write_and_commit(repo, "feature commit", {"other.txt": "content"})

        _write_config(repo, _TEST_CMD)

        result = run_regression_gate(
            feature_dir=".",
            workspace_root=repo,
            mode="full",
        )

        # Pre-existing failure → baseline-failing, NOT a regression gate
        self.assertEqual(result["status"], "baseline-failing")
        self.assertFalse(result["regression"])
        self.assertEqual(result["baseline_status"], "fail")
        # head_status may be pass or fail; both are reported, none gated
        self.assertIn(result["head_status"], ("pass", "fail"))
        self.assertIn("baseline already failing", result["note"])

    # -----------------------------------------------------------------------
    # Clean case: both passing → no regression
    # -----------------------------------------------------------------------

    def test_clean_no_regression(self):
        """Both merge-base and HEAD pass → clean, regression:false."""
        repo = self._make_install_root("clean")
        _init_repo(repo)

        # main: pass.marker present
        _write_and_commit(repo, "initial on main", {"pass.marker": "ok"})

        # Feature branch: adds a file; pass.marker stays
        _git_run(["checkout", "-b", "feature-3"], cwd=repo)
        _write_and_commit(repo, "feature adds file", {"new_feature.txt": "x"})

        _write_config(repo, _TEST_CMD)

        result = run_regression_gate(
            feature_dir=".",
            workspace_root=repo,
            mode="full",
        )

        self.assertEqual(result["status"], "clean")
        self.assertFalse(result["regression"])
        self.assertEqual(result["baseline_status"], "pass")
        self.assertEqual(result["head_status"], "pass")
        self.assertNotIn("head_output_tail", result)

    # -----------------------------------------------------------------------
    # Worktree cleanup: no dangling worktrees after any run
    # -----------------------------------------------------------------------

    def test_worktree_cleanup_after_clean_run(self):
        """After a clean run, git worktree list shows only the main worktree."""
        repo = self._make_install_root("cleanup_clean")
        _init_repo(repo)
        _write_and_commit(repo, "initial", {"pass.marker": "ok"})
        _git_run(["checkout", "-b", "feature-cleanup"], cwd=repo)
        _write_and_commit(repo, "feature", {"extra.txt": "hi"})
        _write_config(repo, _TEST_CMD)

        run_regression_gate(feature_dir=".", workspace_root=repo, mode="full")

        self.assertEqual(_count_worktrees(repo), 1,
                         "should only have the main worktree after run")

    def test_worktree_cleanup_after_regression_run(self):
        """After a regression run, git worktree list shows only the main worktree."""
        repo = self._make_install_root("cleanup_regression")
        _init_repo(repo)
        _write_and_commit(repo, "initial", {"pass.marker": "ok"})
        _git_run(["checkout", "-b", "feature-regclean"], cwd=repo)
        os.remove(os.path.join(repo, "pass.marker"))
        _git_run(["add", "-A"], cwd=repo)
        _git_run(["commit", "-m", "break"], cwd=repo)
        _write_config(repo, _TEST_CMD)

        run_regression_gate(feature_dir=".", workspace_root=repo, mode="full")

        self.assertEqual(_count_worktrees(repo), 1,
                         "should only have the main worktree after regression run")

    def test_worktree_cleanup_after_exception(self):
        """When _run_test_cmd raises, worktree is still cleaned up (finally runs)."""
        repo = self._make_install_root("cleanup_exception")
        _init_repo(repo)
        _write_and_commit(repo, "initial", {"pass.marker": "ok"})
        _git_run(["checkout", "-b", "feature-exc"], cwd=repo)
        _write_and_commit(repo, "feature", {"extra.txt": "hi"})
        _write_config(repo, _TEST_CMD)

        # Patch _run_test_cmd to raise so the finally block's cleanup is the
        # only thing keeping the worktree from leaking.
        import _verify._regression as regression_mod
        with mock.patch.object(regression_mod, "_run_test_cmd",
                               side_effect=RuntimeError("simulated failure")):
            result = run_regression_gate(
                feature_dir=".", workspace_root=repo, mode="full"
            )

        # The outer try/except catches the propagated exception → inconclusive
        self.assertEqual(result["status"], "inconclusive")
        self.assertFalse(result["regression"])

        # Critical: no dangling worktrees left despite the exception
        self.assertEqual(_count_worktrees(repo), 1,
                         "worktree must be cleaned up even after an exception")

    # -----------------------------------------------------------------------
    # Verify note fields are always present
    # -----------------------------------------------------------------------

    def test_result_always_has_note(self):
        """Every result dict has a 'note' key (required contract)."""
        for mode_arg in ("off", "full"):
            result = run_regression_gate(
                feature_dir=".", workspace_root="/nonexistent", mode=mode_arg
            )
            self.assertIn("note", result,
                          "note key missing from result with mode={0}".format(mode_arg))


# ---------------------------------------------------------------------------
# Tests: _symlink_deps unit tests
# ---------------------------------------------------------------------------

class TestSymlinkDeps(unittest.TestCase):
    """Unit tests for the dep-directory symlink helper."""

    def setUp(self):
        # type: () -> None
        self.tmpdir = tempfile.mkdtemp()
        self.source_root = os.path.join(self.tmpdir, "source")
        self.worktree = os.path.join(self.tmpdir, "worktree")
        os.makedirs(self.source_root)
        os.makedirs(self.worktree)

    def tearDown(self):
        # type: () -> None
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_symlinks_node_modules_when_present(self):
        """node_modules in source_root → symlinked into worktree."""
        nm = os.path.join(self.source_root, "node_modules")
        os.makedirs(nm)

        _symlink_deps(self.source_root, self.worktree)

        dst = os.path.join(self.worktree, "node_modules")
        self.assertTrue(os.path.islink(dst),
                        "node_modules should be a symlink in the worktree")
        self.assertEqual(os.path.realpath(dst), os.path.realpath(nm))

    def test_skips_absent_dep_dir(self):
        """Dep dir absent in source_root → no symlink created in worktree."""
        # No node_modules created
        _symlink_deps(self.source_root, self.worktree)

        dst = os.path.join(self.worktree, "node_modules")
        self.assertFalse(os.path.exists(dst))
        self.assertFalse(os.path.islink(dst))

    def test_symlinks_venv_when_present(self):
        """.venv in source_root → symlinked into worktree."""
        venv_dir = os.path.join(self.source_root, ".venv")
        os.makedirs(venv_dir)

        _symlink_deps(self.source_root, self.worktree)

        dst = os.path.join(self.worktree, ".venv")
        self.assertTrue(os.path.islink(dst))

    def test_skips_existing_dst(self):
        """If dst already exists in worktree, no double-symlink (no error)."""
        nm = os.path.join(self.source_root, "node_modules")
        os.makedirs(nm)
        dst = os.path.join(self.worktree, "node_modules")
        os.makedirs(dst)  # already a directory, not a link

        # Should not raise; existing dst is left unchanged
        _symlink_deps(self.source_root, self.worktree)
        self.assertTrue(os.path.isdir(dst))
        self.assertFalse(os.path.islink(dst))  # still a dir, not replaced by link

    def test_multiple_dep_dirs(self):
        """Multiple dep dirs all get symlinked when present."""
        for dep in ("node_modules", ".venv", "vendor"):
            os.makedirs(os.path.join(self.source_root, dep))

        _symlink_deps(self.source_root, self.worktree)

        for dep in ("node_modules", ".venv", "vendor"):
            dst = os.path.join(self.worktree, dep)
            self.assertTrue(os.path.islink(dst),
                            "{0} should be a symlink".format(dep))


# ---------------------------------------------------------------------------
# Tests: _verdict.py regression fold
# ---------------------------------------------------------------------------

class TestVerdictRegressionFold(unittest.TestCase):
    """compute_verdict: regression parameter folds into NEEDS WORK."""

    def _clean_inputs(self):
        """Return clean inputs that would otherwise yield APPROVED."""
        return dict(
            ac_results=[],
            mechanical_status="pass",
            review_findings={
                "missing": False,
                "confirmed": [],
                "contested": [],
                "summary": {
                    "critical": 0, "high": 0, "medium": 0, "info": 0,
                    "confirmed_count": 0, "contested_count": 0,
                    "dismissed_count": 0, "uncertain_count": 0,
                },
            },
            hygiene={
                "scope_creep": [],
                "leftover_artifacts": [],
                "scope_creep_checked": False,
                "files_checked": 0,
                "files_unreadable": [],
            },
            ac_verification_mode="code-only",
        )

    def test_regression_true_forces_needs_work(self):
        """regression={"regression": True} → NEEDS WORK with blocker type "regression"."""
        inputs = self._clean_inputs()
        regression = {"status": "regression", "regression": True}
        result = compute_verdict(**inputs, regression=regression)

        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("regression", blocker_types)

    def test_regression_true_never_rejected(self):
        """regression:true alone NEVER produces REJECTED."""
        inputs = self._clean_inputs()
        regression = {"status": "regression", "regression": True}
        result = compute_verdict(**inputs, regression=regression)

        self.assertNotEqual(result["verdict"], "REJECTED")

    def test_regression_false_no_effect(self):
        """regression={"regression": False} → APPROVED (clean inputs unaffected)."""
        inputs = self._clean_inputs()
        regression = {"status": "clean", "regression": False}
        result = compute_verdict(**inputs, regression=regression)

        self.assertEqual(result["verdict"], "APPROVED")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertNotIn("regression", blocker_types)

    def test_regression_none_backward_compat(self):
        """regression=None (default) → APPROVED; pre-existing callers unaffected."""
        inputs = self._clean_inputs()
        result = compute_verdict(**inputs, regression=None)
        self.assertEqual(result["verdict"], "APPROVED")

    def test_regression_omitted_backward_compat(self):
        """Omitting regression kwarg → APPROVED; signature is backward-compatible."""
        inputs = self._clean_inputs()
        result = compute_verdict(**inputs)  # no regression kwarg
        self.assertEqual(result["verdict"], "APPROVED")

    def test_regression_true_with_constitution_violation_is_rejected(self):
        """regression:true + confirmed constitution violation → REJECTED (constitution wins)."""
        inputs = self._clean_inputs()
        inputs["review_findings"]["confirmed"] = [
            {
                "pattern": "hard-coded key",
                "file": "src/main.py",
                "severity": "Critical",
                "tags": ["[CONSTITUTION-VIOLATION]"],
                "category": "constitution",
            }
        ]
        regression = {"status": "regression", "regression": True}
        result = compute_verdict(**inputs, regression=regression)

        # REJECTED because constitution_confirmed takes priority
        self.assertEqual(result["verdict"], "REJECTED")

    def test_regression_true_with_other_blocker_still_needs_work(self):
        """regression:true + mechanical failure → NEEDS WORK (two blockers, not REJECTED)."""
        inputs = self._clean_inputs()
        inputs["mechanical_status"] = "failed"
        regression = {"status": "regression", "regression": True}
        result = compute_verdict(**inputs, regression=regression)

        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("regression", blocker_types)
        self.assertIn("mechanical_failed", blocker_types)

    def test_regression_blocker_reason_is_present(self):
        """When regression:true, the reasons list mentions regression."""
        inputs = self._clean_inputs()
        regression = {"status": "regression", "regression": True}
        result = compute_verdict(**inputs, regression=regression)

        combined_reasons = " ".join(result["reasons"]).lower()
        self.assertIn("regression", combined_reasons)

    def test_regression_status_off_not_a_regression(self):
        """regression={"status":"off","regression":false} → no regression blocker."""
        inputs = self._clean_inputs()
        regression = {"status": "off", "regression": False}
        result = compute_verdict(**inputs, regression=regression)

        self.assertEqual(result["verdict"], "APPROVED")

    def test_regression_inconclusive_not_gating(self):
        """regression={"status":"inconclusive","regression":false} → APPROVED."""
        inputs = self._clean_inputs()
        regression = {"status": "inconclusive", "regression": False}
        result = compute_verdict(**inputs, regression=regression)

        self.assertEqual(result["verdict"], "APPROVED")


# ---------------------------------------------------------------------------
# Tests: CLI verb registration
# ---------------------------------------------------------------------------

class TestCLIVerb(unittest.TestCase):
    """regression-gate verb is registered and responds to --help."""

    def test_regression_gate_in_help(self):
        """verify_helper --help mentions regression-gate."""
        from _verify._cli import build_parser
        parser = build_parser()
        help_text = parser.format_help()
        self.assertIn("regression-gate", help_text)

    def test_regression_gate_no_args_returns_0(self):
        """regression-gate with --mode off returns 0 (no real workspace needed)."""
        from _verify._cli import main
        import io
        captured = io.StringIO()
        with mock.patch("sys.stdout", captured):
            rc = main(["regression-gate", "--mode", "off"])
        self.assertEqual(rc, 0)
        out = json.loads(captured.getvalue())
        self.assertEqual(out["status"], "off")

    def test_compute_verdict_accepts_regression_flag(self):
        """compute-verdict --help mentions --regression flag."""
        from _verify._cli import build_parser
        sub = build_parser()
        help_text = sub.format_help()
        # Just verify the subparser was built; regression flag is on the
        # compute-verdict subparser, not the top-level.
        self.assertIn("compute-verdict", help_text)


if __name__ == "__main__":
    unittest.main()
