"""Tests for the resolve-feature-scope verb in verify_helper._cli.

The verb is a thin wrapper around _shared.feature_scope.resolve_feature_scope
with heading_label="Verification Scope".  The underlying git logic is tested
exhaustively in tests/lib/_shared/test_feature_scope.py.  This file focuses on:

  1. The heading_label difference ("Verification Scope" vs "Review Scope").
  2. The CLI verb registration and argument shape.
  3. A real git fixture round-trip — same fixture pattern as test_feature_scope.py.
  4. Error handling (not a git repo → exit 2).

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List, Optional

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _verify._cli import main  # noqa: E402


# ---------------------------------------------------------------------------
# Git fixture helpers (mirrors tests/lib/_shared/test_feature_scope.py)
# ---------------------------------------------------------------------------


def _git(args, cwd, check=True):
    # type: (List[str], str, bool) -> subprocess.CompletedProcess
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def _init_repo(path, initial_branch="main"):
    # type: (str, str) -> None
    _git(["init", "-b", initial_branch, "."], cwd=path)
    _git(["config", "user.email", "test@example.com"], cwd=path)
    _git(["config", "user.name", "Test User"], cwd=path)
    _git(["config", "commit.gpgsign", "false"], cwd=path)


def _write_file(root, relpath, content="x\n"):
    # type: (str, str, str) -> str
    full = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return full


def _commit(path, message, files=None):
    # type: (str, str, Optional[List[str]]) -> str
    if files:
        _git(["add"] + files, cwd=path)
    else:
        _git(["add", "."], cwd=path)
    _git(["commit", "-m", message], cwd=path)
    return _git(["rev-parse", "HEAD"], cwd=path).stdout.strip()


def _make_simple_repo():
    # type: () -> str
    """Create a temp git repo with one base commit + one feature commit.

    Returns (td_path) — the caller is responsible for cleanup.
    """
    td = tempfile.mkdtemp()
    _init_repo(td)
    _write_file(td, "README.md", "# project\n")
    _commit(td, "initial commit")
    # Feature commit — one new file.
    _write_file(td, "src/feature.py", "def feat(): pass\n")
    _commit(td, "add feature")
    return td


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture(argv):
    # type: (List[str]) -> tuple
    """Run main(argv) capturing stdout/stderr. Returns (stdout, stderr, rc)."""
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = buf_out, buf_err
    try:
        rc = main(argv)
    except SystemExit as exc:
        rc = exc.code if isinstance(exc.code, int) else 2
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return buf_out.getvalue(), buf_err.getvalue(), rc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestResolveFeatureScopeVerb(unittest.TestCase):
    """resolve-feature-scope verb in verify_helper emits Verification Scope label."""

    def setUp(self):
        self.td = _make_simple_repo()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.td, ignore_errors=True)

    def test_exit_0_on_success(self):
        out, _, rc = _capture([
            "resolve-feature-scope",
            "--source-root", self.td,
            "--base", "HEAD~1",
        ])
        self.assertEqual(rc, 0, "stderr: {0}".format(_))

    def test_stdout_is_valid_json(self):
        out, _, rc = _capture([
            "resolve-feature-scope",
            "--source-root", self.td,
            "--base", "HEAD~1",
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertIsInstance(data, dict)

    def test_has_required_keys(self):
        out, _, rc = _capture([
            "resolve-feature-scope",
            "--source-root", self.td,
            "--base", "HEAD~1",
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        for key in ("files", "files_for_finders", "file_count", "scope_block"):
            self.assertIn(key, data, "Missing key: {0}".format(key))

    def test_scope_block_contains_verification_scope(self):
        """The scope_block uses 'Verification Scope' (not 'Review Scope')."""
        out, _, rc = _capture([
            "resolve-feature-scope",
            "--source-root", self.td,
            "--base", "HEAD~1",
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        scope_block = data.get("scope_block", "")
        self.assertIn(
            "Verification Scope", scope_block,
            "scope_block should contain 'Verification Scope'; got: {0!r}".format(
                scope_block[:200]
            ),
        )

    def test_scope_block_does_not_contain_review_scope(self):
        """The scope_block must NOT say 'Review Scope' (that's the /review label)."""
        out, _, rc = _capture([
            "resolve-feature-scope",
            "--source-root", self.td,
            "--base", "HEAD~1",
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        scope_block = data.get("scope_block", "")
        self.assertNotIn(
            "Review Scope", scope_block,
            "scope_block must not say 'Review Scope'; got: {0!r}".format(
                scope_block[:200]
            ),
        )

    def test_files_list_not_empty(self):
        """The feature commit added src/feature.py — files list should be non-empty."""
        out, _, rc = _capture([
            "resolve-feature-scope",
            "--source-root", self.td,
            "--base", "HEAD~1",
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertGreater(data["file_count"], 0)
        self.assertGreater(len(data["files"]), 0)

    def test_feature_py_in_files(self):
        """src/feature.py appears in the diff files."""
        out, _, rc = _capture([
            "resolve-feature-scope",
            "--source-root", self.td,
            "--base", "HEAD~1",
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        files = data["files"]
        self.assertTrue(
            any("feature.py" in f for f in files),
            "Expected feature.py in files; got: {0}".format(files),
        )

    def test_not_a_git_repo_exit_2(self):
        """Non-git directory → exit 2."""
        with tempfile.TemporaryDirectory() as td:
            _, err, rc = _capture([
                "resolve-feature-scope",
                "--source-root", td,
                "--base", "main",
            ])
            self.assertEqual(rc, 2, "Expected exit 2 for non-git repo")

    def test_bad_base_ref_exit_2(self):
        """Invalid base ref → exit 2."""
        _, _, rc = _capture([
            "resolve-feature-scope",
            "--source-root", self.td,
            "--base", "nonexistent-branch-xyz",
        ])
        self.assertEqual(rc, 2)

    def test_feature_flag_included_in_output(self):
        """The --feature directory appears in the output JSON."""
        out, _, rc = _capture([
            "resolve-feature-scope",
            "--feature", "specs/001-test",
            "--source-root", self.td,
            "--base", "HEAD~1",
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data.get("feature_dir"), "specs/001-test")


if __name__ == "__main__":
    unittest.main()
