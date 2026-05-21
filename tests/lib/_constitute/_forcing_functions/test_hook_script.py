"""Tests for the pre-commit-forcing-functions.sh hook script.

Tests invoke the hook as a subprocess with a controlled fixture project.
The hook requires:
  - a git repo at ROOT
  - .devforge/constitute.json present
  - .devforge/lib/constitute_helper executable

Since the real constitute_helper binary lives at
src/devforge/lib/constitute_helper in the template repo (not a git-managed
binary in the fixture), tests create a minimal stub shell script that acts
as the constitute_helper.

Coverage
--------
test_hook_exits_0_when_no_config
    Missing constitute.json → exit 0 (no block).

test_hook_exits_0_when_no_enabled_rules
    Config present but no enabled rules → exit 0.

test_hook_exits_0_when_helper_not_executable
    Helper absent/not-executable → exit 0 silently.

test_hook_exits_0_on_all_clean_rules
    Enabled rules all return exit 0 → hook exits 0.

test_hook_exits_1_on_violation
    One enabled rule returns exit 2 → hook exits 1 + stderr message.

test_hook_stderr_message_contains_rule_name
    Error message includes the failing verb name.
"""

from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[4]
_HOOK_SCRIPT = _REPO_ROOT / "src" / "git-hooks" / "pre-commit-forcing-functions.sh"


def _git_init(path: Path) -> None:
    """Initialize a git repo at path."""
    subprocess.check_call(
        ["git", "init", str(path)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Configure identity so git doesn't complain
    subprocess.check_call(
        ["git", "-C", str(path), "config", "user.email", "test@test.com"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.check_call(
        ["git", "-C", str(path), "config", "user.name", "Test"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _write_config(devforge_dir: Path, ff_block: dict) -> None:
    import json
    devforge_dir.mkdir(parents=True, exist_ok=True)
    cfg = {"forcing_functions": ff_block}
    (devforge_dir / "constitute.json").write_text(
        json.dumps(cfg, indent=2), encoding="utf-8"
    )


def _write_stub_helper(
    helper_path: Path,
    list_output: str = "",
    verify_exit: int = 0,
) -> None:
    """Write a minimal stub constitute_helper that:
    - responds to list-forcing-functions (prints list_output)
    - responds to verify-* (exits verify_exit)
    """
    helper_path.parent.mkdir(parents=True, exist_ok=True)
    script = (
        "#!/bin/sh\n"
        "CMD=$1\n"
        "shift\n"
        'if [ "$CMD" = "list-forcing-functions" ]; then\n'
        "  printf '{list_output}'\n"
        "  exit 0\n"
        "fi\n"
        'case "$CMD" in\n'
        "  verify-*)\n"
        "    exit {verify_exit}\n"
        "    ;;\n"
        "  *)\n"
        "    exit 0\n"
        "    ;;\n"
        "esac\n"
    ).format(
        list_output=list_output,
        verify_exit=verify_exit,
    )
    helper_path.write_text(script, encoding="utf-8")
    helper_path.chmod(helper_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _run_hook(project_root: Path, env=None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["sh", str(_HOOK_SCRIPT)],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        env=env,
    )


class TestHookMissingConfig(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.root = Path(self._td)
        _git_init(self.root)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_hook_exits_0_when_no_config(self):
        # No .devforge/constitute.json
        result = _run_hook(self.root)
        self.assertEqual(result.returncode, 0)

    def test_hook_exits_0_when_helper_not_executable(self):
        # Config present but helper absent
        devforge = self.root / ".devforge"
        _write_config(devforge, {"magic_enum_duplication": {"enabled": True}})
        result = _run_hook(self.root)
        self.assertEqual(result.returncode, 0)


class TestHookNoEnabledRules(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.root = Path(self._td)
        _git_init(self.root)
        devforge = self.root / ".devforge"
        _write_config(devforge, {
            "magic_enum_duplication": {"enabled": False},
        })
        helper = devforge / "lib" / "constitute_helper"
        _write_stub_helper(helper, list_output="", verify_exit=0)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_hook_exits_0_when_no_enabled_rules(self):
        result = _run_hook(self.root)
        self.assertEqual(result.returncode, 0)


class TestHookAllClean(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.root = Path(self._td)
        _git_init(self.root)
        devforge = self.root / ".devforge"
        _write_config(devforge, {
            "magic_enum_duplication": {"enabled": True},
        })
        helper = devforge / "lib" / "constitute_helper"
        # list-forcing-functions --format verb returns the CLI verb; verify exits 0 (clean)
        _write_stub_helper(
            helper,
            list_output="verify-magic-enum\n",
            verify_exit=0,
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_hook_exits_0_on_all_clean_rules(self):
        result = _run_hook(self.root)
        self.assertEqual(result.returncode, 0)


class TestHookViolation(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.root = Path(self._td)
        _git_init(self.root)
        devforge = self.root / ".devforge"
        _write_config(devforge, {
            "magic_enum_duplication": {"enabled": True},
        })
        helper = devforge / "lib" / "constitute_helper"
        # list-forcing-functions --format verb returns the CLI verb; verify exits 2 (violations)
        _write_stub_helper(
            helper,
            list_output="verify-magic-enum\n",
            verify_exit=2,
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_hook_exits_1_on_violation(self):
        result = _run_hook(self.root)
        self.assertEqual(result.returncode, 1)

    def test_hook_stderr_message_contains_verb(self):
        # After F1 fix, the error message contains the CLI verb name, not the rule key.
        result = _run_hook(self.root)
        self.assertIn("verify-magic-enum", result.stderr)

    def test_hook_stderr_mentions_forcing_fn_ok(self):
        result = _run_hook(self.root)
        self.assertIn("forcing-fn-ok", result.stderr)


class TestHookMultipleRules(unittest.TestCase):
    """Two rules: first clean, second violating → hook exits 1.

    The stub helper is invoked with --format verb, so it outputs the real
    CLI verb names (verify-magic-enum, verify-any-leak) — not raw config keys.
    """

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.root = Path(self._td)
        _git_init(self.root)
        devforge = self.root / ".devforge"
        _write_config(devforge, {
            "magic_enum_duplication": {"enabled": True},
            "any_with_generated_available": {"enabled": True},
        })
        helper = devforge / "lib" / "constitute_helper"
        # Stub: list-forcing-functions --format verb outputs real verb names.
        # verify-magic-enum exits 0 (clean); verify-any-leak exits 2 (violation).
        script = (
            "#!/bin/sh\n"
            "CMD=$1\n"
            "shift\n"
            'if [ "$CMD" = "list-forcing-functions" ]; then\n'
            "  printf 'verify-magic-enum\\nverify-any-leak\\n'\n"
            "  exit 0\n"
            "fi\n"
            'if [ "$CMD" = "verify-magic-enum" ]; then\n'
            "  exit 0\n"
            "fi\n"
            'if [ "$CMD" = "verify-any-leak" ]; then\n'
            "  exit 2\n"
            "fi\n"
            "exit 0\n"
        )
        helper.parent.mkdir(parents=True, exist_ok=True)
        helper.write_text(script, encoding="utf-8")
        helper.chmod(helper.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_hook_exits_1_when_any_rule_violates(self):
        result = _run_hook(self.root)
        self.assertEqual(result.returncode, 1)


if __name__ == "__main__":
    unittest.main()
