"""Tests for scripts/devforge-state-migrate.sh (`forge_migrate_devforge_state`).

Extends the plan-56 install-reproducible CODE-dir untrack loop for the
plan-63 relocated command-reference home `.devforge/command-refs/` (see
63-SKILL-COLLISION-SUPPRESSION-PLAN.md Phase 1b).

No persisted test previously existed for this script (plan 56's coverage was
a scratch-only fixture run during that plan's build, per repo memory) — this
file is the first committed test, built real-git-fixture (no hand-authored
mocks): a real `git init` tempdir, real tracked files, the real shell
function sourced and invoked via `bash -c`.

Coverage:
  1. `.devforge/command-refs/<name>/<file>.md` previously tracked → untracked
     (git rm --cached), leaving the working-tree file on disk.
  2. VERSIONED root files (`.devforge/memory.md`) stay tracked (untouched).
  3. The other plan-56 CODE dirs (`lib`, `bin`, `templates`) still untrack
     alongside the new `command-refs` dir (no regression).
  4. `.devforge/template/` (singular) stays tracked (explicit plan-56
     exclusion, unaffected by this change).
  5. Non-git target dir → benign no-op (function returns success, no crash).
  6. Absent target dir → benign no-op.
  7. Idempotency — running the migration twice does not error the second
     time (nothing left to untrack).

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MIGRATE_SCRIPT = _REPO_ROOT / "scripts" / "devforge-state-migrate.sh"


def _run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        check=True,
    )


def _tracked_files(cwd: Path) -> set:
    result = subprocess.run(
        ["git", "-C", str(cwd), "ls-files"],
        capture_output=True,
        text=True,
        check=True,
    )
    return set(result.stdout.splitlines())


def _run_migrate(target_dir: Path) -> subprocess.CompletedProcess:
    """Source the script and invoke forge_migrate_devforge_state "$target_dir"."""
    cmd = f'source "{_MIGRATE_SCRIPT}"; forge_migrate_devforge_state "{target_dir}"'
    return subprocess.run(
        ["bash", "-c", cmd],
        capture_output=True,
        text=True,
    )


class DevforgeStateMigrateTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.target = Path(self._tmp.name)
        _run_git(self.target, "init", "-b", "main")
        _run_git(self.target, "config", "user.email", "test@example.com")
        _run_git(self.target, "config", "user.name", "Test")

    def tearDown(self):
        self._tmp.cleanup()

    def _seed_tracked_devforge_tree(self):
        """Populate + commit a realistic tracked .devforge/ tree (CODE + VERSIONED)."""
        paths = {
            ".devforge/command-refs/audit/adversarial-preamble.md": "preamble content\n",
            ".devforge/command-refs/review/report-format.md": "report format\n",
            ".devforge/lib/audit_helper.py": "# helper\n",
            ".devforge/bin/audit_helper": "#!/bin/sh\n",
            ".devforge/templates/some-template.md": "template\n",
            ".devforge/template/agent.md": "agent baseline\n",
            ".devforge/memory.md": "# memory\n",
        }
        for rel, content in paths.items():
            p = self.target / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
        _run_git(self.target, "add", "-A")
        _run_git(self.target, "commit", "-m", "seed tracked devforge tree")
        return set(paths)

    # 1 + 2 + 3 + 4 ── the full untrack matrix in one fixture
    def test_command_refs_untracked_while_versioned_and_template_stay_tracked(self):
        seeded = self._seed_tracked_devforge_tree()
        before = _tracked_files(self.target)
        for rel in seeded:
            self.assertIn(rel, before, f"fixture setup sanity: {rel} must start tracked")

        result = _run_migrate(self.target)
        self.assertEqual(
            result.returncode, 0,
            f"migration must exit 0; stderr: {result.stderr}",
        )

        after = _tracked_files(self.target)

        # CODE class (all four subdirs, incl. the new command-refs) untracked.
        for rel in (
            ".devforge/command-refs/audit/adversarial-preamble.md",
            ".devforge/command-refs/review/report-format.md",
            ".devforge/lib/audit_helper.py",
            ".devforge/bin/audit_helper",
            ".devforge/templates/some-template.md",
        ):
            self.assertNotIn(rel, after, f"{rel} should be untracked (CODE class)")
            # The migration only untracks (git rm --cached) — the working-tree
            # file must survive on disk.
            self.assertTrue((self.target / rel).is_file(), f"{rel} must remain on disk")

        # VERSIONED root file stays tracked, untouched.
        self.assertIn(".devforge/memory.md", after, "memory.md (VERSIONED) must stay tracked")

        # .devforge/template/ (singular) — plan-56 deliberate exclusion — stays tracked.
        self.assertIn(
            ".devforge/template/agent.md", after,
            ".devforge/template/ (singular) must stay tracked (plan-56 exclusion)",
        )

    # 5 ── non-git target dir is a benign no-op
    def test_non_git_target_dir_is_benign_noop(self):
        non_git = Path(tempfile.mkdtemp())
        try:
            (non_git / ".devforge" / "command-refs" / "audit").mkdir(parents=True)
            (non_git / ".devforge" / "command-refs" / "audit" / "x.md").write_text("x\n")
            result = _run_migrate(non_git)
            self.assertEqual(
                result.returncode, 0,
                f"non-git target must be a benign no-op; stderr: {result.stderr}",
            )
        finally:
            shutil.rmtree(non_git, ignore_errors=True)

    # 6 ── absent target dir is a benign no-op
    def test_absent_target_dir_is_benign_noop(self):
        absent = self.target / "does-not-exist"
        result = _run_migrate(absent)
        self.assertEqual(
            result.returncode, 0,
            f"absent target must be a benign no-op; stderr: {result.stderr}",
        )

    # 7 ── idempotency: second run is a no-op, no error
    def test_idempotent_second_run_does_not_error(self):
        self._seed_tracked_devforge_tree()
        first = _run_migrate(self.target)
        self.assertEqual(first.returncode, 0)

        second = _run_migrate(self.target)
        self.assertEqual(
            second.returncode, 0,
            f"second migration run must not error; stderr: {second.stderr}",
        )
        # Nothing further to untrack on the second pass.
        after = _tracked_files(self.target)
        self.assertNotIn(".devforge/command-refs/audit/adversarial-preamble.md", after)
        self.assertIn(".devforge/memory.md", after)


if __name__ == "__main__":
    unittest.main()
