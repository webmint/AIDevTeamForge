"""Tests for src/devforge/lib/cbm_sync_helper.py.

Covers the two subcommands (`write`, `check`), all four `check` state
tokens (`current` / `missing` / `drift` / `not-a-git-repo`), corrupt-stamp
handling, atomic-write semantics, DEVFORGE_DIR env override, and the
POSIX launcher shim.

Each test runs in its own `tempfile.TemporaryDirectory`. Tests that
need a real HEAD invoke `git init` + a real commit via subprocess so
the helper sees an actual sha (no mocked git). The test process's cwd
is restored in `tearDown` so tests can't leak state.

CLI-level tests invoke the .py file as a subprocess with cwd inside
the test repo and `DEVFORGE_DIR` pointing at a sibling temp directory,
exercising the real argparse + dispatch path.

Stdlib only.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER_PY = REPO_ROOT / "src" / "devforge" / "lib" / "cbm_sync_helper.py"
HELPER_SHIM = REPO_ROOT / "src" / "devforge" / "lib" / "cbm_sync_helper"

sys.path.insert(0, str(HELPER_PY.parent))
import cbm_sync_helper  # noqa: E402


def _init_repo(repo_dir):
    """Init a git repo at `repo_dir` and create one commit. Returns HEAD sha."""
    env = os.environ.copy()
    # Minimal env so commits don't depend on user-global git config.
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    subprocess.run(
        ["git", "init", "-q", "-b", "main", str(repo_dir)],
        check=True,
        env=env,
    )
    # Some old git versions don't support -b on init; if -b failed
    # silently the next commands still work because we don't rely on
    # branch name. Create one commit to give HEAD a target sha.
    (Path(repo_dir) / "README").write_text("hi\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo_dir), "add", "README"],
        check=True,
        env=env,
    )
    subprocess.run(
        ["git", "-C", str(repo_dir), "commit", "-q", "-m", "init"],
        check=True,
        env=env,
    )
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def _add_commit(repo_dir, filename, content):
    """Add a second commit on top of the existing repo. Returns new HEAD."""
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    (Path(repo_dir) / filename).write_text(content, encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(repo_dir), "add", filename],
        check=True,
        env=env,
    )
    subprocess.run(
        ["git", "-C", str(repo_dir), "commit", "-q", "-m", "second"],
        check=True,
        env=env,
    )
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def _run_cli(cwd, devforge_dir, *args):
    """Invoke cbm_sync_helper.py as a subprocess."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    # Inherit any pre-set GIT_* envs to keep commits reproducible if the
    # subprocess itself ever has to commit (it doesn't today).
    return subprocess.run(
        [sys.executable, str(HELPER_PY)] + list(args),
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )


def _run_launcher(cwd, devforge_dir, *args):
    """Invoke the POSIX launcher shim as a subprocess."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [str(HELPER_SHIM)] + list(args),
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
    )


class _CwdIsolation(unittest.TestCase):
    """Module-level tests that rely on Path.cwd() — restore cwd in tearDown."""

    def setUp(self):
        self._saved_cwd = os.getcwd()
        self._saved_env = os.environ.get("DEVFORGE_DIR")
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        os.chdir(self._saved_cwd)
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env
        self._tmp.cleanup()


# ---------------------------------------------------------------------------
# Path resolution.
# ---------------------------------------------------------------------------


class StampPathTests(_CwdIsolation):

    def test_env_override_honored(self):
        os.environ["DEVFORGE_DIR"] = str(self.tmp_path)
        path = cbm_sync_helper._stamp_path()
        self.assertEqual(path, self.tmp_path / "cbm-last-indexed-sha")

    def test_no_env_falls_back_to_helper_parent(self):
        os.environ.pop("DEVFORGE_DIR", None)
        path = cbm_sync_helper._stamp_path()
        # Helper lives at <repo>/src/devforge/lib/cbm_sync_helper.py.
        # Parent.parent of the .py file == <repo>/src/devforge → stamp
        # lands at <repo>/src/devforge/cbm-last-indexed-sha.
        expected = (
            Path(cbm_sync_helper.__file__).resolve().parent.parent
            / "cbm-last-indexed-sha"
        )
        self.assertEqual(path, expected)

    def test_resolution_is_per_call_not_cached(self):
        os.environ["DEVFORGE_DIR"] = str(self.tmp_path)
        first = cbm_sync_helper._stamp_path()
        other = self.tmp_path / "other"
        other.mkdir()
        os.environ["DEVFORGE_DIR"] = str(other)
        second = cbm_sync_helper._stamp_path()
        self.assertNotEqual(first, second)
        self.assertEqual(second, other / "cbm-last-indexed-sha")

    def test_stamp_file_name_constant(self):
        self.assertEqual(cbm_sync_helper.STAMP_FILE_NAME, "cbm-last-indexed-sha")


# ---------------------------------------------------------------------------
# write subcommand.
# ---------------------------------------------------------------------------


class WriteCmdTests(_CwdIsolation):

    def test_write_fresh_stamp(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()
        devforge = self.tmp_path / "df"
        head = _init_repo(repo)

        result = _run_cli(repo, devforge, "write")
        self.assertEqual(result.returncode, 0, result.stderr)

        stamp_path = devforge / "cbm-last-indexed-sha"
        self.assertTrue(stamp_path.exists())
        data = json.loads(stamp_path.read_text(encoding="utf-8"))
        self.assertEqual(data["git_sha"], head)
        # indexed_at: yyyy-mm-ddThh:mm:ssZ, length 20.
        self.assertEqual(len(data["indexed_at"]), 20)
        self.assertTrue(data["indexed_at"].endswith("Z"))

    def test_write_overwrite(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()
        devforge = self.tmp_path / "df"
        first = _init_repo(repo)

        _run_cli(repo, devforge, "write")
        stamp_path = devforge / "cbm-last-indexed-sha"
        first_data = json.loads(stamp_path.read_text(encoding="utf-8"))
        self.assertEqual(first_data["git_sha"], first)

        second = _add_commit(repo, "two.txt", "two\n")
        self.assertNotEqual(first, second)
        result = _run_cli(repo, devforge, "write")
        self.assertEqual(result.returncode, 0, result.stderr)
        second_data = json.loads(stamp_path.read_text(encoding="utf-8"))
        self.assertEqual(second_data["git_sha"], second)

    def test_write_not_a_git_repo_exits_2(self):
        # tmp_path itself is not a git repo.
        devforge = self.tmp_path / "df"
        result = _run_cli(self.tmp_path, devforge, "write")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not a git repository", result.stderr)
        self.assertFalse((devforge / "cbm-last-indexed-sha").exists())

    def test_atomic_write_no_tmp_file_survives(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()
        devforge = self.tmp_path / "df"
        _init_repo(repo)

        result = _run_cli(repo, devforge, "write")
        self.assertEqual(result.returncode, 0, result.stderr)
        survivors = [p.name for p in devforge.iterdir()]
        self.assertEqual(survivors, ["cbm-last-indexed-sha"])
        for name in survivors:
            self.assertFalse(name.endswith(".tmp"), name)

    def test_write_io_failure_exits_1(self):
        # Force the os.replace step to raise by making the stamp path a
        # directory. The helper catches OSError → exit 1 + diagnostic on
        # stderr. Also verifies the temp file is cleaned up after the
        # failure (no .tmp survivors).
        repo = self.tmp_path / "repo"
        repo.mkdir()
        devforge = self.tmp_path / "df"
        devforge.mkdir()
        (devforge / "cbm-last-indexed-sha").mkdir()
        _init_repo(repo)

        result = _run_cli(repo, devforge, "write")
        self.assertEqual(result.returncode, 1)
        self.assertIn("cannot write stamp", result.stderr)
        # Temp file from mkstemp must not survive the failed write.
        survivors = sorted(p.name for p in devforge.iterdir())
        self.assertEqual(survivors, ["cbm-last-indexed-sha"])


# ---------------------------------------------------------------------------
# check subcommand.
# ---------------------------------------------------------------------------


class CheckCmdTests(_CwdIsolation):

    def test_check_missing(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()
        devforge = self.tmp_path / "df"
        devforge.mkdir()
        _init_repo(repo)
        # No stamp written → "missing".
        result = _run_cli(repo, devforge, "check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "missing")

    def test_check_current(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()
        devforge = self.tmp_path / "df"
        _init_repo(repo)

        write_result = _run_cli(repo, devforge, "write")
        self.assertEqual(write_result.returncode, 0, write_result.stderr)
        check_result = _run_cli(repo, devforge, "check")
        self.assertEqual(check_result.returncode, 0, check_result.stderr)
        self.assertEqual(check_result.stdout.strip(), "current")

    def test_check_drift(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()
        devforge = self.tmp_path / "df"
        first = _init_repo(repo)
        _run_cli(repo, devforge, "write")
        second = _add_commit(repo, "two.txt", "two\n")
        self.assertNotEqual(first, second)

        result = _run_cli(repo, devforge, "check")
        self.assertEqual(result.returncode, 0, result.stderr)
        line = result.stdout.strip()
        self.assertTrue(line.startswith("drift "), line)
        body = line[len("drift "):]
        a, sep, b = body.partition("..")
        self.assertEqual(sep, "..")
        self.assertEqual(a, first)
        self.assertEqual(b, second)

    def test_check_corrupt_json_treated_as_missing(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()
        devforge = self.tmp_path / "df"
        devforge.mkdir()
        _init_repo(repo)
        stamp_path = devforge / "cbm-last-indexed-sha"
        stamp_path.write_text("not-json{{{", encoding="utf-8")

        result = _run_cli(repo, devforge, "check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "missing")

    def test_check_stamp_missing_git_sha_field_treated_as_missing(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()
        devforge = self.tmp_path / "df"
        devforge.mkdir()
        _init_repo(repo)
        stamp_path = devforge / "cbm-last-indexed-sha"
        stamp_path.write_text(json.dumps({"indexed_at": "x"}), encoding="utf-8")

        result = _run_cli(repo, devforge, "check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "missing")

    def test_check_stamp_non_dict_treated_as_missing(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()
        devforge = self.tmp_path / "df"
        devforge.mkdir()
        _init_repo(repo)
        stamp_path = devforge / "cbm-last-indexed-sha"
        # Valid JSON but not a dict → must be treated as missing.
        stamp_path.write_text(json.dumps(["a", "b"]), encoding="utf-8")

        result = _run_cli(repo, devforge, "check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "missing")

    def test_check_not_a_git_repo_exits_2(self):
        devforge = self.tmp_path / "df"
        devforge.mkdir()
        result = _run_cli(self.tmp_path, devforge, "check")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout.strip(), "not-a-git-repo")


# ---------------------------------------------------------------------------
# CLI shape (argparse, no subcommand).
# ---------------------------------------------------------------------------


class CliShapeTests(_CwdIsolation):

    def test_no_subcommand_exits_2(self):
        devforge = self.tmp_path / "df"
        devforge.mkdir()
        result = _run_cli(self.tmp_path, devforge)
        self.assertEqual(result.returncode, 2)

    def test_help_subcommand_works(self):
        devforge = self.tmp_path / "df"
        devforge.mkdir()
        result = _run_cli(self.tmp_path, devforge, "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("write", result.stdout)
        self.assertIn("check", result.stdout)


# ---------------------------------------------------------------------------
# POSIX launcher shim.
# ---------------------------------------------------------------------------


class LauncherShimTests(_CwdIsolation):

    def test_launcher_dispatches_to_check(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()
        devforge = self.tmp_path / "df"
        devforge.mkdir()
        _init_repo(repo)
        result = _run_launcher(repo, devforge, "check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "missing")

    def test_launcher_dispatches_to_write_and_round_trip(self):
        repo = self.tmp_path / "repo"
        repo.mkdir()
        devforge = self.tmp_path / "df"
        head = _init_repo(repo)
        wr = _run_launcher(repo, devforge, "write")
        self.assertEqual(wr.returncode, 0, wr.stderr)
        ck = _run_launcher(repo, devforge, "check")
        self.assertEqual(ck.returncode, 0, ck.stderr)
        self.assertEqual(ck.stdout.strip(), "current")
        data = json.loads((devforge / "cbm-last-indexed-sha").read_text(encoding="utf-8"))
        self.assertEqual(data["git_sha"], head)


if __name__ == "__main__":
    unittest.main()
