"""Tests for src/devforge/lib/_artifact/_cli.py (commit-artifacts verb).

Coverage (all 6 required arms + edge cases):

  1. STANDALONE happy path
     - Stages named untracked files in install repo, makes [WIP] <label> commit
       containing EXACTLY those files (asserted via git show --stat).
     - Emits {"committed": true, "head_sha": ..., "message": "[WIP] <label>"}.
     - Exit 0.

  2. NEVER git add -A
     - An UNRELATED dirty/untracked file in the working tree is NOT in the commit.
     - Only the explicitly named --paths are staged.

  3. FAIL-SOFT on git error
     - A non-repo --root (no .git) → exit 1, stderr message, NO traceback.
     - Exception must not escape main() (caller is never crashed).

  4. WRAPPER arm
     - A tmp install repo with a nested source repo + .devforge/project-config.json
       carrying PROJECT_ROOT pointing at the nested dir.
     - The commit lands in install_root.
     - The SOURCE repo HEAD is UNCHANGED before/after (D2 invariant).

  5. D4 DIRECTORY-PATH arm
     - Called with a directory path (["specs/003-foo/"]) stages ALL untracked
       files under it (equivalent to `git add specs/003-foo/`).
     - An UNRELATED file OUTSIDE that directory is NOT committed.
     - An absent/empty path in --paths is a benign no-op (no exception, no crash).

  6. BENIGN no-op (idempotency)
     - Running the verb twice (second run has nothing new to stage) → exit 0,
       {"committed": false, "skipped": "nothing to commit"}, no error on stderr.

  Additional edge cases:
  - --paths not valid JSON → exit 1, stderr, no traceback.
  - --paths valid JSON but not a list → exit 1, stderr.
  - --label missing / empty → exit 1, stderr.
  - Empty string in --paths list → benign skip, no crash.
  - Verb called with no subcommand → exit 1.

  Language guard (advisory Cyrillic detector):
  - Cyrillic in a staged file → commit succeeds, exit 0, stdout JSON
    byte-identical in shape to the ASCII case, stderr names that file.
  - Pure-ASCII run → no language warning on stderr at all.
  - Cyrillic in --label → warning fires, commit proceeds, committed message
    unchanged.
  - Detector exception → exactly ONE "language check skipped" warning,
    commit still succeeds, exit 0.
  - Enumeration returncode != 0 (git fails without raising) → same single
    "language check skipped" warning, never a silent no-op, commit succeeds.
  - Direct unit test of the pure _contains_cyrillic predicate.

Design notes:
- Each test creates its own git tempdir (real git init) to avoid cross-test
  contamination.
- Git tempdir is initialised with `git init -b main`, `git config user.*`,
  an initial commit.
- The "only named paths committed" safety assertion inspects
  `git show --stat HEAD` for the commit's changed file list.
- Wrapper tests write .devforge/project-config.json with PROJECT_ROOT pointing
  at a nested subdirectory that is itself a git repo.

Stdlib only. Python 3.8+.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Path bootstrap — make _artifact + _implement importable
# ---------------------------------------------------------------------------

_LIB_DIR = str(Path(__file__).resolve().parents[3] / "src" / "devforge" / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _artifact._cli import (  # noqa: E402
    EXIT_OK,
    EXIT_ERR,
    _cmd_commit_artifacts,
    _contains_cyrillic,
    main,
)


# ---------------------------------------------------------------------------
# Git tempdir helpers
# ---------------------------------------------------------------------------


def _git_env():
    """Minimal git env to avoid leaking real-user identity into test commits."""
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Test User"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test User"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    # Prevent GPG signing in test repos.
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    return env


def _init_git_repo(tmpdir):
    """Initialise a minimal git repo in tmpdir. Returns (root_path, initial_sha)."""
    root = Path(tmpdir)
    env = _git_env()

    def run(*cmd):
        result = subprocess.run(
            list(cmd), cwd=str(root), capture_output=True, text=True,
            env=env, check=True,
        )
        return result.stdout.strip()

    run("git", "init", "-b", "main")
    run("git", "config", "user.email", "test@example.com")
    run("git", "config", "user.name", "Test User")
    run("git", "config", "commit.gpgsign", "false")
    # Initial commit so HEAD exists.
    init_file = root / "README.md"
    init_file.write_text("# Test repo\n")
    run("git", "add", "--", str(init_file))
    run("git", "commit", "-m", "init")
    sha = run("git", "rev-parse", "HEAD")
    return root, sha


def _head_sha(repo_root):
    """Return current HEAD SHA for repo_root (absolute path)."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True, env=_git_env(),
    )
    return result.stdout.strip()


def _commit_files_in_stat(repo_root):
    """Return the set of filenames (not full paths) in HEAD's diff --stat."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), "show", "--stat", "--format=", "HEAD"],
        capture_output=True, text=True, check=True, env=_git_env(),
    )
    files = set()
    for line in result.stdout.splitlines():
        # stat lines look like:  " some/path/file.md | 1 +"
        if "|" in line:
            path_part = line.split("|")[0].strip()
            if path_part:
                files.add(path_part)
    return files


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


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestCommitArtifactsStandaloneHappyPath(unittest.TestCase):
    """Arm 1: standalone happy path — stages named files, makes [WIP] commit."""

    def test_stages_named_files_and_commits(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)

            # Write two artifact files.
            spec_file = root / "spec.md"
            handoff_file = root / "handoff.json"
            spec_file.write_text("# Spec\n")
            handoff_file.write_text('{"kind": "specify"}\n')

            paths_json = json.dumps([str(spec_file), str(handoff_file)])
            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", paths_json,
                "--label", "spec: 001-foo",
                "--root", str(root),
            ])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            # Parse emitted JSON.
            out = json.loads(stdout.strip())
            self.assertTrue(out["committed"])
            self.assertEqual(out["message"], "[WIP] spec: 001-foo")
            self.assertIn("head_sha", out)
            self.assertRegex(out["head_sha"], r"^[0-9a-f]{40}$")

            # Verify git log shows the WIP commit message.
            result = subprocess.run(
                ["git", "-C", str(root), "log", "--oneline", "-1"],
                capture_output=True, text=True, check=True, env=_git_env(),
            )
            self.assertIn("[WIP] spec: 001-foo", result.stdout)

            # Verify EXACTLY those files are in the commit.
            stat_files = _commit_files_in_stat(root)
            self.assertIn("spec.md", stat_files)
            self.assertIn("handoff.json", stat_files)


class TestCommitArtifactsNeverGitAddA(unittest.TestCase):
    """Arm 2: NEVER git add -A — unrelated dirty file must NOT be committed."""

    def test_unrelated_file_not_in_commit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)

            # Named artifact.
            spec_file = root / "spec.md"
            spec_file.write_text("# Spec\n")

            # UNRELATED dirty file — must not be committed.
            unrelated = root / "unrelated.py"
            unrelated.write_text("# should not appear\n")

            paths_json = json.dumps([str(spec_file)])
            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", paths_json,
                "--label", "spec: 002-bar",
                "--root", str(root),
            ])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)

            # The commit must contain spec.md but NOT unrelated.py.
            stat_files = _commit_files_in_stat(root)
            self.assertIn("spec.md", stat_files)
            self.assertNotIn("unrelated.py", stat_files)

            # unrelated.py must still be untracked.
            result = subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain"],
                capture_output=True, text=True, check=True, env=_git_env(),
            )
            self.assertIn("?? unrelated.py", result.stdout)


class TestCommitArtifactsFailSoft(unittest.TestCase):
    """Arm 3: fail-soft — a non-repo root → exit 1, stderr, no traceback."""

    def test_non_repo_root_returns_exit1_no_traceback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # No .git in this directory — not a git repo.
            non_repo = Path(tmpdir)
            artifact = non_repo / "spec.md"
            artifact.write_text("# Spec\n")

            paths_json = json.dumps([str(artifact)])
            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", paths_json,
                "--label", "spec: 003-baz",
                "--root", str(non_repo),
            ])

            # Must return exit 1, not crash.
            self.assertEqual(code, EXIT_ERR, msg="stdout: " + stdout)
            # stderr must carry a message.
            self.assertTrue(len(stderr) > 0, msg="Expected error on stderr, got none")
            # Must NOT contain a Python traceback.
            self.assertNotIn("Traceback", stderr)
            self.assertNotIn("raise ", stderr)

    def test_bad_json_paths_returns_exit1(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)
            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", "not-json!",
                "--label", "spec: 004",
                "--root", str(root),
            ])
            self.assertEqual(code, EXIT_ERR)
            self.assertIn("not valid JSON", stderr)
            self.assertNotIn("Traceback", stderr)

    def test_paths_non_array_json_returns_exit1(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)
            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", '"just a string"',
                "--label", "spec: 005",
                "--root", str(root),
            ])
            self.assertEqual(code, EXIT_ERR)
            self.assertIn("JSON array", stderr)
            self.assertNotIn("Traceback", stderr)

    def test_empty_label_returns_exit1(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)
            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", "[]",
                "--label", "",
                "--root", str(root),
            ])
            self.assertEqual(code, EXIT_ERR)
            self.assertIn("--label", stderr)
            self.assertNotIn("Traceback", stderr)


class TestCommitArtifactsWrapperArm(unittest.TestCase):
    """Arm 4: wrapper mode — commit lands in install root, source HEAD unchanged."""

    def _make_wrapper_install(self, tmpdir):
        """Create an install repo + nested source repo + project-config.json.

        Returns (install_root, source_root).
        """
        install_root = Path(tmpdir)
        _init_git_repo(str(install_root))

        # Nested source repo.
        source_root = install_root / "source-project"
        source_root.mkdir()
        _init_git_repo(str(source_root))

        # Write .devforge/project-config.json pointing at source-project.
        devforge_dir = install_root / ".devforge"
        devforge_dir.mkdir(exist_ok=True)
        config = {"PROJECT_ROOT": "source-project"}
        (devforge_dir / "project-config.json").write_text(json.dumps(config))

        return install_root, source_root

    def test_commit_lands_in_install_root_source_head_unchanged(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            install_root, source_root = self._make_wrapper_install(tmpdir)

            # Capture source HEAD before.
            source_sha_before = _head_sha(source_root)

            # Write an artifact in the install root.
            spec_file = install_root / "spec.md"
            spec_file.write_text("# Wrapper Spec\n")

            paths_json = json.dumps([str(spec_file)])
            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", paths_json,
                "--label", "spec: 006-wrapper",
                "--root", str(install_root),
            ])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            out = json.loads(stdout.strip())
            self.assertTrue(out["committed"])

            # The commit must land in the INSTALL repo.
            stat_files = _commit_files_in_stat(install_root)
            self.assertIn("spec.md", stat_files)

            # The SOURCE repo HEAD must be UNCHANGED.
            source_sha_after = _head_sha(source_root)
            self.assertEqual(
                source_sha_before, source_sha_after,
                msg="Source repo HEAD changed — D2 invariant violated"
            )

    def test_wrapper_commit_message_uses_wip_label(self):
        """In wrapper mode the commit message is still [WIP] <label> (no TICKET-ID)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            install_root, source_root = self._make_wrapper_install(tmpdir)

            artifact = install_root / "plan.md"
            artifact.write_text("# Plan\n")

            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", json.dumps([str(artifact)]),
                "--label", "plan: 007-wrapper",
                "--root", str(install_root),
            ])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            out = json.loads(stdout.strip())
            self.assertEqual(out["message"], "[WIP] plan: 007-wrapper")

            # Verify in git log.
            result = subprocess.run(
                ["git", "-C", str(install_root), "log", "--oneline", "-1"],
                capture_output=True, text=True, check=True, env=_git_env(),
            )
            self.assertIn("[WIP] plan: 007-wrapper", result.stdout)


class TestCommitArtifactsDirectoryPath(unittest.TestCase):
    """Arm 5: directory path stages all files under it; absent path is benign no-op."""

    def test_directory_path_stages_all_files_under_it(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)

            # Create a directory with multiple files.
            specs_dir = root / "specs" / "003-foo"
            specs_dir.mkdir(parents=True)
            (specs_dir / "spec.md").write_text("# Spec 003\n")
            (specs_dir / "handoff.json").write_text('{"kind":"specify"}\n')

            # UNRELATED file outside the directory — must NOT be committed.
            unrelated = root / "unrelated.txt"
            unrelated.write_text("unrelated\n")

            # Call with directory path (trailing slash, as typical for D4 safety-net).
            dir_path = str(specs_dir) + "/"
            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", json.dumps([dir_path]),
                "--label", "spec: 003-foo",
                "--root", str(root),
            ])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            out = json.loads(stdout.strip())
            self.assertTrue(out["committed"])

            # Both files under the dir must be in the commit.
            stat_files = _commit_files_in_stat(root)
            # stat paths are relative: "specs/003-foo/spec.md"
            stat_basenames = {p.split("/")[-1] for p in stat_files}
            self.assertIn("spec.md", stat_basenames)
            self.assertIn("handoff.json", stat_basenames)

            # Unrelated file must NOT be in the commit.
            self.assertNotIn("unrelated.txt", stat_basenames)

    def test_absent_path_is_benign_no_op(self):
        """An absent path in --paths produces no crash and no commit error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)

            # ONE real file, one absent path (optional artifact not written).
            real_file = root / "review.md"
            real_file.write_text("# Review\n")
            absent_path = str(root / "grill-seed.json")  # does not exist

            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", json.dumps([str(real_file), absent_path]),
                "--label", "review: 008-absent-ok",
                "--root", str(root),
            ])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            out = json.loads(stdout.strip())
            self.assertTrue(out["committed"])

            stat_files = _commit_files_in_stat(root)
            self.assertIn("review.md", stat_files)

    def test_empty_string_in_paths_list_is_benign(self):
        """Empty string entry in --paths list is silently skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)

            real_file = root / "plan.md"
            real_file.write_text("# Plan\n")

            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", json.dumps(["", str(real_file), ""]),
                "--label", "plan: 009-empty-skip",
                "--root", str(root),
            ])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            out = json.loads(stdout.strip())
            self.assertTrue(out["committed"])

    def test_empty_paths_list_is_benign_nop(self):
        """Empty --paths list → benign no-op, exit 0, committed: false."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)

            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", "[]",
                "--label", "spec: 010-nop",
                "--root", str(root),
            ])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            out = json.loads(stdout.strip())
            self.assertFalse(out["committed"])
            self.assertIn("skipped", out)


class TestCommitArtifactsBenignNoOp(unittest.TestCase):
    """Arm 6: running the verb twice — second run is a benign no-op."""

    def test_second_invocation_is_benign_nop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root, initial_sha = _init_git_repo(tmpdir)

            spec_file = root / "spec.md"
            spec_file.write_text("# Spec\n")

            paths_json = json.dumps([str(spec_file)])

            # First run — should commit.
            code1, stdout1, stderr1 = _run_main([
                "commit-artifacts",
                "--paths", paths_json,
                "--label", "spec: 011-idempotent",
                "--root", str(root),
            ])
            self.assertEqual(code1, EXIT_OK, msg="First run stderr: " + stderr1)
            out1 = json.loads(stdout1.strip())
            self.assertTrue(out1["committed"])

            sha_after_first = _head_sha(root)

            # Second run — nothing new to stage.
            code2, stdout2, stderr2 = _run_main([
                "commit-artifacts",
                "--paths", paths_json,
                "--label", "spec: 011-idempotent",
                "--root", str(root),
            ])

            self.assertEqual(code2, EXIT_OK, msg="Second run stderr: " + stderr2)
            out2 = json.loads(stdout2.strip())
            self.assertFalse(out2["committed"])
            self.assertIn("skipped", out2)
            self.assertEqual(out2["skipped"], "nothing to commit")

            # HEAD must not have advanced.
            self.assertEqual(_head_sha(root), sha_after_first)

            # stderr must be clean (no error).
            self.assertEqual(stderr2.strip(), "")


class TestCommitArtifactsNoSubcommand(unittest.TestCase):
    """Calling main() with no subcommand → exit 1."""

    def test_no_subcommand_returns_exit1(self):
        code, stdout, stderr = _run_main([])
        self.assertEqual(code, EXIT_ERR)


class TestCommitArtifactsRelativePaths(unittest.TestCase):
    """Relative --paths items are resolved against --root (install_root)."""

    def test_relative_path_staged_correctly(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)

            spec_file = root / "spec.md"
            spec_file.write_text("# Spec relative\n")

            # Pass a relative path — should be resolved against --root.
            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", '["spec.md"]',
                "--label", "spec: 012-relative",
                "--root", str(root),
            ])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            out = json.loads(stdout.strip())
            self.assertTrue(out["committed"])

            stat_files = _commit_files_in_stat(root)
            self.assertIn("spec.md", stat_files)


# ---------------------------------------------------------------------------
# FINDING 1 regression: _git_has_staged_changes must treat rc>1 (git error)
# as "nothing staged", NOT as "staged changes exist".
# ---------------------------------------------------------------------------


class TestGitHasStagedChangesReturncode(unittest.TestCase):
    """FINDING 1: non-repo path must not trigger a spurious commit attempt.

    git diff --cached --quiet in a non-repo exits 128 (not 0 or 1).
    The old code used `returncode != 0`, which treated 128 as "staged changes
    present" and then called git commit — which also failed, producing a
    misleading double-error.  The fix is `returncode == 1` (only rc=1 means
    staged changes).

    This test confirms the non-repo case:
    - fails with exit 1 (clean error from the staging step), AND
    - does NOT produce a "git commit failed" message on stderr (i.e. no second
      git-commit attempt is made after the first error).
    """

    def test_non_repo_no_spurious_commit_attempt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            non_repo = Path(tmpdir)
            artifact = non_repo / "spec.md"
            artifact.write_text("# Spec\n")

            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", json.dumps([str(artifact)]),
                "--label", "spec: finding1",
                "--root", str(non_repo),
            ])

            # Must exit 1 (not 0).
            self.assertEqual(code, EXIT_ERR, msg="stdout: " + stdout)
            # Must carry a message on stderr.
            self.assertTrue(len(stderr) > 0, msg="Expected error on stderr")
            # Must NOT contain a "git commit failed" message — proves no second
            # commit attempt was made after the staging error.
            self.assertNotIn("git commit failed", stderr,
                             msg="Spurious git commit attempt after staging error")
            # Must not contain a Python traceback.
            self.assertNotIn("Traceback", stderr)


# ---------------------------------------------------------------------------
# FINDING 2 regression: successful commit always exits 0 + committed:true,
# even when HEAD SHA read returns None.
# ---------------------------------------------------------------------------


class TestCommitSucceedsEvenIfShaReadFails(unittest.TestCase):
    """FINDING 2: a successful commit must exit 0 + committed:true regardless
    of whether _git_head_sha can read the resulting SHA.

    We test the contract by monkey-patching _git_head_sha to return None
    after the commit, then verifying that committed:true and exit 0 are
    emitted (the git log confirms the commit DID land), and a WARNING appears
    on stderr but no exit-1 error code is returned.
    """

    def test_commit_exits_0_when_sha_read_fails(self):
        import _artifact._cli as cli_mod  # noqa: E402 (import inside test ok)

        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)

            spec_file = root / "spec.md"
            spec_file.write_text("# Spec\n")

            original_git_head_sha = cli_mod._git_head_sha

            def _sha_always_none(repo_root):
                return None

            try:
                cli_mod._git_head_sha = _sha_always_none

                code, stdout, stderr = _run_main([
                    "commit-artifacts",
                    "--paths", json.dumps([str(spec_file)]),
                    "--label", "spec: finding2",
                    "--root", str(root),
                ])
            finally:
                cli_mod._git_head_sha = original_git_head_sha

            # Must exit 0 (commit DID land).
            self.assertEqual(code, EXIT_OK,
                             msg="Expected exit 0 even when SHA read fails; stderr: " + stderr)

            # JSON output must have committed:true.
            out = json.loads(stdout.strip())
            self.assertTrue(out["committed"],
                            msg="committed must be true when commit succeeded")

            # head_sha must be None (not absent — null in JSON).
            self.assertIn("head_sha", out)
            self.assertIsNone(out["head_sha"])

            # Must carry a WARNING on stderr (not an error message that implies failure).
            self.assertIn("WARNING", stderr,
                          msg="Expected WARNING on stderr when SHA read fails")

            # The commit MUST actually exist in git history.
            result = subprocess.run(
                ["git", "-C", str(root), "log", "--oneline", "-1"],
                capture_output=True, text=True, check=True, env=_git_env(),
            )
            self.assertIn("[WIP] spec: finding2", result.stdout,
                          msg="Commit must exist in git history even when SHA read fails")


# ---------------------------------------------------------------------------
# Language guard: advisory Cyrillic detector (plan 87 Phase 2)
# ---------------------------------------------------------------------------


class TestCommitArtifactsLanguageGuard(unittest.TestCase):
    """The advisory Cyrillic scan inside commit-artifacts.

    D1: advisory-only -- never touches the exit code or either stdout JSON
    shape. Cases (1) and (2) below are scored as a PAIR: a detector that
    catches Cyrillic by warning on everything fails the pure-ASCII case.
    """

    def test_cyrillic_in_staged_file_warns_and_commit_succeeds(self):
        """(1) Cyrillic in a staged file: commit succeeds, stdout JSON shape
        unchanged, stderr names the offending file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)

            spec_file = root / "spec.md"
            spec_file.write_text(u"# Spec\n\nПривіт, це не англійська.\n", encoding="utf-8")

            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", json.dumps([str(spec_file)]),
                "--label", "spec: 013-cyrillic-file",
                "--root", str(root),
            ])

            # Exit code and stdout JSON shape are BYTE-IDENTICAL to the ASCII
            # happy path (D3): committed:true, message, a 40-hex head_sha.
            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            out = json.loads(stdout.strip())
            self.assertTrue(out["committed"])
            self.assertEqual(out["message"], "[WIP] spec: 013-cyrillic-file")
            self.assertIn("head_sha", out)
            self.assertRegex(out["head_sha"], r"^[0-9a-f]{40}$")
            self.assertEqual(sorted(out.keys()), ["committed", "head_sha", "message"])

            # The commit itself still landed with exactly the named file.
            stat_files = _commit_files_in_stat(root)
            self.assertIn("spec.md", stat_files)

            # The warning names the offending file, in the exact D3 shape.
            self.assertIn(
                "commit-artifacts: warning: non-English (Cyrillic) text in "
                "spec.md",
                stderr,
            )
            self.assertIn("advisory, commit proceeds", stderr)

    def test_pure_ascii_run_has_no_language_warning(self):
        """(2) A pure-ASCII run prints no language warning at all -- the
        false-positive floor, scored as a pair with (1)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)

            spec_file = root / "spec.md"
            spec_file.write_text("# Spec\n\nPlain English only.\n")

            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", json.dumps([str(spec_file)]),
                "--label", "spec: 014-ascii-only",
                "--root", str(root),
            ])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            out = json.loads(stdout.strip())
            self.assertTrue(out["committed"])

            self.assertNotIn("Cyrillic", stderr)
            self.assertNotIn("language check skipped", stderr)
            self.assertEqual(stderr.strip(), "")

    def test_cyrillic_in_label_warns_and_commit_proceeds(self):
        """(3) Cyrillic in --label: warning fires, commit proceeds, the
        committed message is unchanged (label text is never altered)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)

            spec_file = root / "spec.md"
            spec_file.write_text("# Spec\n")

            label = u"spec: 015-Привіт"  # "Привіт"
            code, stdout, stderr = _run_main([
                "commit-artifacts",
                "--paths", json.dumps([str(spec_file)]),
                "--label", label,
                "--root", str(root),
            ])

            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            out = json.loads(stdout.strip())
            self.assertTrue(out["committed"])
            # The committed message carries the label VERBATIM -- unchanged.
            self.assertEqual(out["message"], u"[WIP] {0}".format(label))

            self.assertIn(
                "commit-artifacts: warning: non-English (Cyrillic) text in "
                "commit label",
                stderr,
            )

            # git log confirms the same unaltered message actually landed.
            result = subprocess.run(
                ["git", "-C", str(root), "log", "-1", "--format=%s"],
                capture_output=True, text=True, check=True, env=_git_env(),
            )
            self.assertEqual(result.stdout.strip(), u"[WIP] {0}".format(label))

    def test_detector_exception_is_fail_soft_and_commit_succeeds(self):
        """(4) A detector exception is swallowed: exactly ONE 'language check
        skipped' warning, and the commit still succeeds with exit 0."""
        import _artifact._cli as cli_mod  # noqa: E402 (import inside test ok)

        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)

            spec_file = root / "spec.md"
            spec_file.write_text("# Spec\n")

            original_contains_cyrillic = cli_mod._contains_cyrillic

            def _boom(text):
                raise RuntimeError("simulated detector failure")

            try:
                cli_mod._contains_cyrillic = _boom

                code, stdout, stderr = _run_main([
                    "commit-artifacts",
                    "--paths", json.dumps([str(spec_file)]),
                    "--label", "spec: 016-detector-exception",
                    "--root", str(root),
                ])
            finally:
                cli_mod._contains_cyrillic = original_contains_cyrillic

            # The commit must still succeed -- the detector can never fail it.
            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            out = json.loads(stdout.strip())
            self.assertTrue(out["committed"])

            # Exactly ONE skip warning, never a traceback.
            self.assertEqual(
                stderr.count("commit-artifacts: warning: language check skipped:"),
                1,
                msg="stderr: " + stderr,
            )
            self.assertIn("simulated detector failure", stderr)
            self.assertNotIn("Traceback", stderr)

            # The commit itself actually landed.
            result = subprocess.run(
                ["git", "-C", str(root), "log", "--oneline", "-1"],
                capture_output=True, text=True, check=True, env=_git_env(),
            )
            self.assertIn("[WIP] spec: 016-detector-exception", result.stdout)

    def test_enumeration_nonzero_returncode_is_fail_soft(self):
        """Finding 1 regression: a nonzero returncode from the staged-set
        enumeration (git failing WITHOUT raising) must still surface through
        the single fail-soft 'language check skipped' line rather than
        going dark, and must never fail the commit."""
        import _artifact._cli as cli_mod  # noqa: E402 (import inside test ok)

        with tempfile.TemporaryDirectory() as tmpdir:
            root, _ = _init_git_repo(tmpdir)

            spec_file = root / "spec.md"
            spec_file.write_text("# Spec\n")

            original_run = cli_mod.subprocess.run

            def _rc1_on_enumeration(cmd, *args, **kwargs):
                if "--name-only" in cmd and "-z" in cmd:
                    return subprocess.CompletedProcess(
                        cmd, 1, stdout="", stderr="simulated git failure"
                    )
                return original_run(cmd, *args, **kwargs)

            try:
                cli_mod.subprocess.run = _rc1_on_enumeration

                code, stdout, stderr = _run_main([
                    "commit-artifacts",
                    "--paths", json.dumps([str(spec_file)]),
                    "--label", "spec: 017-enum-rc-nonzero",
                    "--root", str(root),
                ])
            finally:
                cli_mod.subprocess.run = original_run

            # The commit must still succeed -- a failed enumeration is
            # advisory-only, never a commit failure.
            self.assertEqual(code, EXIT_OK, msg="stderr: " + stderr)
            out = json.loads(stdout.strip())
            self.assertTrue(out["committed"])

            # Exactly ONE skip warning naming the underlying git failure,
            # never a traceback -- this is the tripwire the finding closes:
            # a silent, trace-free empty staged list is no longer possible.
            self.assertEqual(
                stderr.count("commit-artifacts: warning: language check skipped:"),
                1,
                msg="stderr: " + stderr,
            )
            self.assertIn("git diff --cached --name-only failed", stderr)
            self.assertIn("simulated git failure", stderr)
            self.assertNotIn("Traceback", stderr)

            # The commit itself actually landed.
            result = subprocess.run(
                ["git", "-C", str(root), "log", "--oneline", "-1"],
                capture_output=True, text=True, check=True, env=_git_env(),
            )
            self.assertIn("[WIP] spec: 017-enum-rc-nonzero", result.stdout)


class TestContainsCyrillicPredicate(unittest.TestCase):
    """Direct unit test of the pure _contains_cyrillic predicate."""

    def test_ascii_string_is_false(self):
        self.assertFalse(_contains_cyrillic("Hello, world! 123 -- plain ASCII."))

    def test_empty_string_is_false(self):
        self.assertFalse(_contains_cyrillic(""))

    def test_ukrainian_letters_are_true(self):
        # i (U+0456), yi (U+0457), ye (U+0454), g (U+0491) -- every letter
        # modern Ukrainian needs beyond the shared Cyrillic set (D2).
        for ch in (u"і", u"ї", u"є", u"ґ"):
            self.assertTrue(
                _contains_cyrillic(u"prefix-{0}-suffix".format(ch)), msg=repr(ch)
            )

    def test_cyrillic_supplement_block_char_is_true(self):
        # U+0501 CYRILLIC SMALL LETTER KOMI DE -- inside the Supplement block
        # (U+0500-U+052F), which rides along with the Basic block (D2).
        self.assertTrue(_contains_cyrillic(u"prefix-ԁ-suffix"))

    def test_out_of_range_boundary_chars_are_false(self):
        # U+03FF (Greek, below the range) and U+0531 (Armenian AYB, just
        # past U+052F, outside the range) -- confirms the range is
        # bounded, not "any non-ASCII".
        self.assertFalse(_contains_cyrillic(u"\u03ff"))
        self.assertFalse(_contains_cyrillic(u"\u0531"))


if __name__ == "__main__":
    unittest.main()
