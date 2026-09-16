"""Tests for scripts/post-update-checks.sh.

Two sourced functions, both WARN-only and fail-soft:
  - forge_check_config_completeness — surfaces `configure_helper verify`
    violations for a project-config.json that predates the current schema.
  - forge_check_precommit_hook — warns when an installed copy of the
    forcing-functions pre-commit hook differs from the shipped template.

Built on real fixtures, per tests/scripts/test_devforge_state_migrate.py:
the real shell function is sourced and invoked via `bash -c` under
`set -euo pipefail` (update.sh's own mode), against real `git init` repos
and a project-config.json produced by the real configure_helper
(`emit_yaml` → `render-config`). The only stubs are the two fault-injection
helpers that stand in for a crashing / noisy configure_helper — paths the
real helper cannot be driven into on demand.

Every test asserts a sentinel printed AFTER the call: under `set -e` a
non-zero return would abort before it, so its presence proves rc 0.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPT = _REPO_ROOT / "scripts" / "post-update-checks.sh"
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_TEMPLATE_HOOK = _REPO_ROOT / "src" / "git-hooks" / "pre-commit-forcing-functions.sh"
_SENTINEL = "AFTER-CALL-RC0"
_HEADER = "Project configuration does not match this framework version"
_TIER_LINE = "A model tier reported above runs on the session's model (inherit)"
_FIX_LINE = "Fix: re-run /devforge:configure"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import configure_helper  # noqa: E402


# The keys a 2.0.9-era project-config.json lacks (observed on a real 2.0.9
# consumer run through `configure_helper verify`).
_LEGACY_MISSING_KEYS = (
    "E2E_COMMAND",
    "REQUIRE_TICKET",
    "CLAUDE_EFFORT_THINK",
    "CLAUDE_EFFORT_DO",
    "CLAUDE_EFFORT_VERIFY",
    "CLAUDE_TIER_SECURITY",
    "CLAUDE_EFFORT_SECURITY",
)


def _call(function: str, target: Path, template: Path) -> subprocess.CompletedProcess:
    """Source the script and call one function under set -euo pipefail."""
    return subprocess.run(
        [
            "bash",
            "-c",
            'set -euo pipefail; . "$1"; {0} "$2" "$3"; echo {1}'.format(function, _SENTINEL),
            "_",
            str(_SCRIPT),
            str(target),
            str(template),
        ],
        capture_output=True,
        text=True,
    )


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True)


def _bullet_paths(stdout: str) -> list:
    return [line.split("• ", 1)[1] for line in stdout.splitlines() if "• " in line]


def _write_stub_template(root: Path, body: str) -> Path:
    """A template dir whose configure_helper is a fault-injection stub."""
    lib = root / "src" / "devforge" / "lib"
    lib.mkdir(parents=True)
    helper = lib / "configure_helper"
    helper.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    helper.chmod(0o755)
    return root


class _TmpMixin:
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


# ---------------------------------------------------------------------------
# forge_check_config_completeness
# ---------------------------------------------------------------------------


class ConfigCompletenessTests(_TmpMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.target = self.tmp / "consumer"
        self.devforge = self.target / ".devforge"
        self.devforge.mkdir(parents=True)

    def _run_helper(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(_LIB_DIR / "configure_helper.py"),
             "--devforge-dir", str(self.devforge)] + list(args),
            capture_output=True,
            text=True,
        )

    def _write_init_yaml(self) -> None:
        env = os.environ.copy()
        env["DEVFORGE_DIR"] = str(self.devforge)
        for args in (
            ("reset",),
            ("set-workspace-mode", "standalone"),
            ("set-project-root", "."),
            ("set-project-state", "brownfield"),
            ("set-default-branch", "main"),
        ):
            subprocess.run(
                [sys.executable, str(_LIB_DIR / "init_helper.py")] + list(args),
                env=env, capture_output=True, check=True,
            )

    def _write_config(self, claude_tier_security) -> None:
        """Real producer chain: emit_yaml → configure.yaml → render-config."""
        self._write_init_yaml()
        state = configure_helper.default_state()
        state.update({
            "project_name": "consumer",
            "project_description": "A test project",
            "project_type": "Web App",
            "primary_language": "TypeScript",
            "languages": ["TypeScript"],
            "frameworks": ["React"],
            "architectures": ["MVC"],
            "project_natures": ["web"],
            "error_handlings": ["try-catch"],
            "api_layers": ["REST"],
            "testings": ["Jest"],
            "build_tools": ["vite"],
            "build_commands": ["npm run build"],
            "type_check_commands": ["npx tsc"],
            "lint_commands": ["npm run lint"],
            "test_commands": ["npm test"],
            "package_stacks": [{
                "path": "src", "language": "TypeScript", "framework": None,
                "build_tool": None, "build_command": None,
                "type_check_command": None, "lint_command": None,
                "test_command": None,
            }],
            "project_structure": "src/",
            "dev_commands": "npm start",
            "architecture_details": "MVC pattern",
            "workflow_enforcement": "Strict",
            "ai_attribution": "No",
            "claude_tier_think": "opus",
            "claude_tier_do": "sonnet",
            "claude_tier_verify": "sonnet",
            "claude_tier_security": claude_tier_security,
            "ac_verification_mode": "code-only",
        })
        (self.devforge / configure_helper.OUTPUT_FILE_NAME).write_text(
            configure_helper.emit_yaml(state), encoding="utf-8"
        )
        proc = self._run_helper("render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_complete_config_is_silent(self):
        self._write_config(claude_tier_security="opus")
        # Precondition: the real helper agrees the config is complete.
        self.assertEqual(self._run_helper("verify").returncode, 0)

        proc = _call("forge_check_config_completeness", self.target, _REPO_ROOT)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, _SENTINEL + "\n")

    def _edit_project_config(self, edit) -> None:
        config_path = self.devforge / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        edit(data)
        config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def test_legacy_config_warns_with_each_violation_tier_line_and_fix(self):
        self._write_config(claude_tier_security=None)
        self._edit_project_config(
            lambda data: [data.pop(key) for key in _LEGACY_MISSING_KEYS]
        )

        proc = _call("forge_check_config_completeness", self.target, _REPO_ROOT)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(proc.stdout.endswith(_SENTINEL + "\n"))
        self.assertIn(_HEADER, proc.stdout)
        self.assertIn("  • required field CLAUDE_TIER_SECURITY is null", proc.stdout)
        for key in _LEGACY_MISSING_KEYS:
            self.assertIn("  • project-config.json missing key {0}".format(key), proc.stdout)
        self.assertIn(_TIER_LINE, proc.stdout)
        self.assertIn(_FIX_LINE, proc.stdout)
        # The "verify: " prefix is replaced by the bullet, never echoed raw.
        self.assertNotRegex(proc.stdout, re.compile(r"^verify: ", re.M))

    def test_missing_non_tier_key_warns_without_tier_line(self):
        self._write_config(claude_tier_security="opus")
        self._edit_project_config(lambda data: data.pop("E2E_COMMAND"))

        proc = _call("forge_check_config_completeness", self.target, _REPO_ROOT)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("  • project-config.json missing key E2E_COMMAND", proc.stdout)
        self.assertNotIn(_TIER_LINE, proc.stdout)
        self.assertIn(_FIX_LINE, proc.stdout)
        self.assertTrue(proc.stdout.endswith(_SENTINEL + "\n"))

    def test_tier_round_trip_mismatch_warns_without_tier_line(self):
        """A mismatched tier key still carries a model, so it is NOT inherit."""
        self._write_config(claude_tier_security="opus")
        self._edit_project_config(lambda data: data.update({"CLAUDE_TIER_THINK": "haiku"}))

        proc = _call("forge_check_config_completeness", self.target, _REPO_ROOT)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("  • round-trip mismatch:", proc.stdout)
        self.assertIn("CLAUDE_TIER_THINK", proc.stdout)
        self.assertNotIn(_TIER_LINE, proc.stdout)
        self.assertTrue(proc.stdout.endswith(_SENTINEL + "\n"))

    def test_no_project_config_is_silent(self):
        proc = _call("forge_check_config_completeness", self.target, _REPO_ROOT)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, _SENTINEL + "\n")

    def test_missing_helper_prints_skip_note(self):
        (self.devforge / "project-config.json").write_text("{}", encoding="utf-8")
        empty_template = self.tmp / "empty-template"
        empty_template.mkdir()

        proc = _call("forge_check_config_completeness", self.target, empty_template)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("config completeness check skipped: helper not found", proc.stdout)
        self.assertTrue(proc.stdout.endswith(_SENTINEL + "\n"))

    def test_unexpected_helper_exit_prints_skip_note(self):
        (self.devforge / "project-config.json").write_text("{}", encoding="utf-8")
        template = _write_stub_template(self.tmp / "crash-template", "echo boom >&2\nexit 1\n")

        proc = _call("forge_check_config_completeness", self.target, template)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("config completeness check skipped: helper exit 1", proc.stdout)
        self.assertNotIn("boom", proc.stdout)
        self.assertNotIn(_HEADER, proc.stdout)
        self.assertTrue(proc.stdout.endswith(_SENTINEL + "\n"))

    def test_interpreter_noise_on_stderr_is_filtered_out(self):
        (self.devforge / "project-config.json").write_text("{}", encoding="utf-8")
        template = _write_stub_template(
            self.tmp / "noisy-template",
            "echo '/x/_lint_ignore.py:632: SyntaxWarning: invalid escape sequence' >&2\n"
            "echo 'configure_helper verify: cannot load configure.yaml: gone' >&2\n"
            "exit 2\n",
        )

        proc = _call("forge_check_config_completeness", self.target, template)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("  • cannot load configure.yaml: gone", proc.stdout)
        self.assertNotIn("SyntaxWarning", proc.stdout)
        self.assertNotIn(_TIER_LINE, proc.stdout)
        self.assertTrue(proc.stdout.endswith(_SENTINEL + "\n"))


# ---------------------------------------------------------------------------
# forge_check_precommit_hook
# ---------------------------------------------------------------------------


class PrecommitHookTests(_TmpMixin, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        _git(self.repo, "init", "-q", ".")

    def _write_hook(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _stale_template_text(self) -> str:
        current = _TEMPLATE_HOOK.read_text(encoding="utf-8")
        stale = current.replace("-maxdepth 4", "-maxdepth 2")
        self.assertNotEqual(stale, current)  # sanity: the fixture really differs
        return stale

    def _assert_warns_for(self, proc: subprocess.CompletedProcess, expected: Path) -> None:
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("Installed pre-commit hook differs", proc.stdout)
        paths = _bullet_paths(proc.stdout)
        self.assertEqual(len(paths), 1, proc.stdout)
        self.assertEqual(os.path.realpath(paths[0]), os.path.realpath(str(expected)))
        self.assertIn("cp .devforge/templates/git-hooks/pre-commit-forcing-functions.sh", proc.stdout)
        self.assertTrue(proc.stdout.endswith(_SENTINEL + "\n"))

    def _assert_silent(self, proc: subprocess.CompletedProcess) -> None:
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, _SENTINEL + "\n")

    def test_no_hook_is_silent(self):
        self._assert_silent(_call("forge_check_precommit_hook", self.repo, _REPO_ROOT))

    def test_identical_hook_is_silent(self):
        hook = self.repo / ".git" / "hooks" / "pre-commit"
        hook.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(_TEMPLATE_HOOK, hook)

        self._assert_silent(_call("forge_check_precommit_hook", self.repo, _REPO_ROOT))

    def test_foreign_hook_is_silent(self):
        self._write_hook(self.repo / ".git" / "hooks" / "pre-commit", "#!/bin/sh\nnpx lint-staged\n")

        self._assert_silent(_call("forge_check_precommit_hook", self.repo, _REPO_ROOT))

    def test_stale_framework_hook_warns(self):
        hook = self.repo / ".git" / "hooks" / "pre-commit"
        self._write_hook(hook, self._stale_template_text())

        self._assert_warns_for(_call("forge_check_precommit_hook", self.repo, _REPO_ROOT), hook)

    def test_relative_core_hooks_path_is_resolved(self):
        _git(self.repo, "config", "core.hooksPath", ".githooks")
        hook = self.repo / ".githooks" / "pre-commit"
        self._write_hook(hook, self._stale_template_text())
        # A stale copy at the default location is inactive and must not be reported.
        self._write_hook(self.repo / ".git" / "hooks" / "pre-commit", self._stale_template_text())

        self._assert_warns_for(_call("forge_check_precommit_hook", self.repo, _REPO_ROOT), hook)

    def test_absolute_core_hooks_path_is_used_as_is(self):
        """git returns an ABSOLUTE path here — it must not be re-prefixed."""
        hooks_dir = self.tmp / "shared-hooks"
        _git(self.repo, "config", "core.hooksPath", str(hooks_dir))
        hook = hooks_dir / "pre-commit"
        self._write_hook(hook, self._stale_template_text())

        self._assert_warns_for(_call("forge_check_precommit_hook", self.repo, _REPO_ROOT), hook)

    def test_linked_worktree_resolves_main_repo_hook(self):
        """A linked worktree's --git-path is absolute, into the main repo's hooks."""
        _git(self.repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
             "--allow-empty", "-m", "init")
        worktree = self.tmp / "wt"
        _git(self.repo, "worktree", "add", "-q", str(worktree))
        hook = self.repo / ".git" / "hooks" / "pre-commit"
        self._write_hook(hook, self._stale_template_text())

        self._assert_warns_for(_call("forge_check_precommit_hook", worktree, _REPO_ROOT), hook)

    def test_target_nested_inside_repo_resolves_parent_hook(self):
        hook = self.repo / ".git" / "hooks" / "pre-commit"
        self._write_hook(hook, self._stale_template_text())
        nested = self.repo / "packages" / "app"
        nested.mkdir(parents=True)

        self._assert_warns_for(_call("forge_check_precommit_hook", nested, _REPO_ROOT), hook)

    def test_non_git_target_is_silent(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        env_ceiling = subprocess.run(
            ["git", "-C", str(plain), "rev-parse", "--git-dir"], capture_output=True
        )
        self.assertNotEqual(env_ceiling.returncode, 0)  # sanity: really outside any repo

        self._assert_silent(_call("forge_check_precommit_hook", plain, _REPO_ROOT))

    def test_missing_template_prints_skip_note(self):
        empty_template = self.tmp / "empty-template"
        empty_template.mkdir()

        proc = _call("forge_check_precommit_hook", self.repo, empty_template)

        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("pre-commit hook check skipped: template not found", proc.stdout)
        self.assertTrue(proc.stdout.endswith(_SENTINEL + "\n"))


if __name__ == "__main__":
    unittest.main()
