"""Tests for configure_helper substitute-file subcommand.

Covers:
1. Happy path: file with {{PROJECT_NAME}}, {{LANGUAGE}} (singular alias),
   {{PACKAGE_STACKS_SECTION}} (composed), and {{UPPERCASE}} (identity passthrough)
   → all substitute; {{UPPERCASE}} stays as literal '{{UPPERCASE}}'; exit 0; file
   rewritten in place.
2. Unknown placeholder: file with {{NOT_A_REAL_KEY}} → exit 2, file content
   UNCHANGED, stderr names the key.
3. Missing project-config.json → exit 1.
4. Missing/nonexistent --file → exit 1.

Uses real-producer fixtures: init_helper writes init.yaml; configure_helper
render-config produces project-config.json. Follows the _EnvIsolationMixin
pattern from test_configure_helper.py.

Stdlib only.
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
_HELPER_PY = _LIB_DIR / "configure_helper.py"
_INIT_HELPER_PY = _LIB_DIR / "init_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import configure_helper  # noqa: E402
import init_helper       # noqa: E402
from _configure._render import _PROJECT_CONFIG_KEY_ORDER  # noqa: E402


# ---------------------------------------------------------------------------
# Subprocess helpers — mirrors test_configure_helper.py conventions exactly.
# ---------------------------------------------------------------------------


def _run_configure(devforge_dir, *args):
    """Invoke configure_helper.py <args> as a subprocess."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY), "--devforge-dir", str(devforge_dir)] + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _run_configure_extra(devforge_dir, extra_args, *args):
    """Invoke configure_helper.py with extra flags inserted before subcommand."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY), "--devforge-dir", str(devforge_dir)]
        + list(extra_args) + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _run_init(devforge_dir, *args):
    """Invoke init_helper.py <args> as a subprocess."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_INIT_HELPER_PY)] + list(args),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


# ---------------------------------------------------------------------------
# _EnvIsolationMixin — identical to test_configure_helper.py.
# ---------------------------------------------------------------------------


class _EnvIsolationMixin:
    """Save/restore DEVFORGE_DIR around each test + provide a tmpdir.

    Layout:
      self._tmp.name/          ← install_root
        .devforge/             ← devforge_dir
    """

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.install_root = Path(self._tmp.name)
        self.devforge_dir = self.install_root / ".devforge"
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.devforge_dir / configure_helper.OUTPUT_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env


# ---------------------------------------------------------------------------
# Shared fixture builder.
# ---------------------------------------------------------------------------


class _SubstituteFileFixture(_EnvIsolationMixin):
    """Helpers to build the minimal fixture required by substitute-file tests."""

    def _write_init_yaml(self, workspace_mode="standalone", project_root="."):
        """Produce init.yaml via the real init_helper producer."""
        _run_init(self.devforge_dir, "reset")
        _run_init(self.devforge_dir, "set-project-name", "test-project")
        _run_init(self.devforge_dir, "set-workspace-mode", workspace_mode)

    def _write_project_config_json(self):
        """Produce project-config.json via render-config (the real producer)."""
        proc = _run_configure_extra(
            self.devforge_dir,
            ["--install-root", str(self.install_root)],
            "render-config",
        )
        assert proc.returncode == 0, (
            "render-config failed: {0}".format(proc.stderr.decode())
        )

    def _write_target_file(self, name, content):
        """Write a file to the install root; return its absolute path."""
        p = self.install_root / name
        p.write_text(content, encoding="utf-8")
        return p

    def _run_substitute_file(self, file_path):
        """Run substitute-file --file <path>."""
        return _run_configure_extra(
            self.devforge_dir,
            ["--install-root", str(self.install_root)],
            "substitute-file",
            "--file", str(file_path),
        )


# ---------------------------------------------------------------------------
# Test 1: Happy path — all known placeholders substitute; {{UPPERCASE}} stays.
# ---------------------------------------------------------------------------


class TestSubstituteFileHappyPath(_SubstituteFileFixture, unittest.TestCase):
    """Happy-path tests where the file is rewritten and the command exits 0."""

    def test_project_name_substituted(self):
        """{{PROJECT_NAME}} is replaced with the configured value; exit 0."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "my-great-app")
        self._write_project_config_json()

        target = self._write_target_file("custom.md", "Name: {{PROJECT_NAME}}\n")
        proc = self._run_substitute_file(target)

        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        result = target.read_text(encoding="utf-8")
        self.assertIn("my-great-app", result)
        self.assertNotIn("{{PROJECT_NAME}}", result)

    def test_language_singular_alias_substituted(self):
        """{{LANGUAGE}} (singular alias of LANGUAGES array) is substituted; exit 0."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-languages", "TypeScript")
        self._write_project_config_json()

        target = self._write_target_file("custom.md", "Lang: {{LANGUAGE}}\n")
        proc = self._run_substitute_file(target)

        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        result = target.read_text(encoding="utf-8")
        self.assertIn("TypeScript", result)
        self.assertNotIn("{{LANGUAGE}}", result)

    def test_package_stacks_section_substituted(self):
        """{{PACKAGE_STACKS_SECTION}} (composed) substitutes as a markdown table."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(
            self.devforge_dir, "add-package-stack",
            "--path", "apps/web",
            "--language", "TypeScript",
            "--framework", "Vue",
            "--build-tool", "Vite",
        )
        self._write_project_config_json()

        target = self._write_target_file(
            "custom.md", "## Packages\n\n{{PACKAGE_STACKS_SECTION}}\n"
        )
        proc = self._run_substitute_file(target)

        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        result = target.read_text(encoding="utf-8")
        self.assertIn("| Package | Language | Framework | Build Tool | Test Command |", result)
        self.assertIn("| apps/web | TypeScript | Vue | Vite |", result)
        self.assertNotIn("{{PACKAGE_STACKS_SECTION}}", result)

    def test_uppercase_identity_passthrough_stays_literal(self):
        """{{UPPERCASE}} is the identity placeholder — stays as '{{UPPERCASE}}'; exit 0.

        UPPERCASE is in sub_map with value '{{UPPERCASE}}', so it is NOT
        "missing" — the command must exit 0 and the literal must remain.
        """
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        self._write_project_config_json()

        original = "Marker: {{UPPERCASE}}\n"
        target = self._write_target_file("custom.md", original)
        proc = self._run_substitute_file(target)

        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        result = target.read_text(encoding="utf-8")
        # The identity substitution replaces {{UPPERCASE}} with {{UPPERCASE}},
        # so the literal must still be present.
        self.assertIn("{{UPPERCASE}}", result)

    def test_mixed_placeholders_all_in_one_file(self):
        """{{PROJECT_NAME}}, {{LANGUAGE}}, {{PACKAGE_STACKS_SECTION}}, {{UPPERCASE}}
        all in one file: the first three are replaced, UPPERCASE stays; exit 0."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "multi-test")
        _run_configure(self.devforge_dir, "set-languages", "Python")
        self._write_project_config_json()

        content = (
            "Project: {{PROJECT_NAME}}\n"
            "Language: {{LANGUAGE}}\n"
            "Packages:\n{{PACKAGE_STACKS_SECTION}}\n"
            "Marker: {{UPPERCASE}}\n"
        )
        target = self._write_target_file("multi.md", content)
        proc = self._run_substitute_file(target)

        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        result = target.read_text(encoding="utf-8")
        self.assertIn("multi-test", result)
        self.assertIn("Python", result)
        self.assertNotIn("{{PROJECT_NAME}}", result)
        self.assertNotIn("{{LANGUAGE}}", result)
        # UPPERCASE identity passthrough remains.
        self.assertIn("{{UPPERCASE}}", result)

    def test_file_with_no_placeholders_exits_0_unchanged(self):
        """A file with no {{...}} markers exits 0 and content is unchanged."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        self._write_project_config_json()

        original = "No placeholders here.\n"
        target = self._write_target_file("plain.md", original)
        proc = self._run_substitute_file(target)

        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_idempotent_second_run_exits_0(self):
        """Running substitute-file twice on an already-substituted file exits 0."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "idempotent-app")
        self._write_project_config_json()

        target = self._write_target_file("custom.md", "Name: {{PROJECT_NAME}}\n")
        proc1 = self._run_substitute_file(target)
        self.assertEqual(proc1.returncode, 0, proc1.stderr.decode())
        after_first = target.read_text(encoding="utf-8")

        proc2 = self._run_substitute_file(target)
        self.assertEqual(proc2.returncode, 0, proc2.stderr.decode())
        self.assertEqual(target.read_text(encoding="utf-8"), after_first)

    def test_file_outside_install_root_is_substituted(self):
        """substitute-file accepts an arbitrary path, not just files under install_root."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "arbitrary-path")
        self._write_project_config_json()

        # Write the file to the devforge dir itself (arbitrary location).
        target = self.devforge_dir / "extra-template.md"
        target.write_text("Proj: {{PROJECT_NAME}}\n", encoding="utf-8")

        proc = self._run_substitute_file(target)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn("arbitrary-path", target.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Test 2: Unknown placeholder → exit 2, file unchanged, stderr names the key.
# ---------------------------------------------------------------------------


class TestSubstituteFileUnknownPlaceholder(_SubstituteFileFixture, unittest.TestCase):

    def test_unknown_key_exits_2(self):
        """{{NOT_A_REAL_KEY}} → exit 2."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        self._write_project_config_json()

        target = self._write_target_file("unknown.md", "Hello {{NOT_A_REAL_KEY}} world\n")
        proc = self._run_substitute_file(target)

        self.assertEqual(proc.returncode, 2)

    def test_unknown_key_named_in_stderr(self):
        """stderr must name the unknown key."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        self._write_project_config_json()

        target = self._write_target_file("unknown.md", "Hello {{NOT_A_REAL_KEY}} world\n")
        proc = self._run_substitute_file(target)

        self.assertIn(b"NOT_A_REAL_KEY", proc.stderr)

    def test_unknown_key_file_content_unchanged(self):
        """When exit 2, the file content must be UNCHANGED (atomic write skipped)."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        self._write_project_config_json()

        original = "Hello {{NOT_A_REAL_KEY}} world\n"
        target = self._write_target_file("unknown.md", original)
        self._run_substitute_file(target)

        self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_multiple_unknown_keys_all_named_in_stderr(self):
        """Multiple unknown placeholders → all named in stderr."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        self._write_project_config_json()

        target = self._write_target_file(
            "multi_unknown.md", "{{KEY_ONE}} and {{KEY_TWO}}\n"
        )
        proc = self._run_substitute_file(target)

        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"KEY_ONE", proc.stderr)
        self.assertIn(b"KEY_TWO", proc.stderr)

    def test_mixed_known_and_unknown_exits_2_file_unchanged(self):
        """File with both known ({{PROJECT_NAME}}) and unknown ({{BAD_KEY}}) →
        exit 2, file unchanged (not partially substituted)."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "partial-test")
        self._write_project_config_json()

        original = "Name: {{PROJECT_NAME}} bad: {{BAD_KEY}}\n"
        target = self._write_target_file("mixed.md", original)
        proc = self._run_substitute_file(target)

        self.assertEqual(proc.returncode, 2)
        # Must NOT have partially substituted PROJECT_NAME.
        self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_state_management_placeholder_is_unknown(self):
        """{{STATE_MANAGEMENT}} is not in sub_map → exit 2.

        STATE_MANAGEMENT lives in constitution.md; the substitution layer
        intentionally does not define a value for it (same behaviour as
        substitute-templates which exits 2 for this key).
        """
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        self._write_project_config_json()

        target = self._write_target_file("sm.md", "State: {{STATE_MANAGEMENT}}\n")
        proc = self._run_substitute_file(target)

        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"STATE_MANAGEMENT", proc.stderr)


# ---------------------------------------------------------------------------
# Test 3: Missing project-config.json → exit 1.
# ---------------------------------------------------------------------------


class TestSubstituteFileMissingConfig(_SubstituteFileFixture, unittest.TestCase):

    def test_missing_project_config_exits_1(self):
        """project-config.json absent → exit 1."""
        # Do NOT run render-config; project-config.json will not exist.
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        # Intentionally skip _write_project_config_json().

        target = self._write_target_file("custom.md", "{{PROJECT_NAME}}\n")
        proc = self._run_substitute_file(target)

        self.assertEqual(proc.returncode, 1)

    def test_missing_project_config_stderr_message(self):
        """stderr must mention 'project-config.json not found' on exit 1."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")

        target = self._write_target_file("custom.md", "{{PROJECT_NAME}}\n")
        proc = self._run_substitute_file(target)

        self.assertIn(b"project-config.json not found", proc.stderr)

    def test_malformed_project_config_exits_1(self):
        """Malformed project-config.json (invalid JSON) → exit 1."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        # Write a broken project-config.json.
        bad_json = b"{ not valid json }"
        (self.devforge_dir / "project-config.json").write_bytes(bad_json)

        target = self._write_target_file("custom.md", "{{PROJECT_NAME}}\n")
        proc = self._run_substitute_file(target)

        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"malformed project-config.json", proc.stderr)


# ---------------------------------------------------------------------------
# Test 4: Missing/nonexistent --file → exit 1.
# ---------------------------------------------------------------------------


class TestSubstituteFileMissingTarget(_SubstituteFileFixture, unittest.TestCase):

    def test_nonexistent_file_exits_1(self):
        """--file pointing at a nonexistent path → exit 1."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        self._write_project_config_json()

        nonexistent = self.install_root / "does-not-exist.md"
        proc = self._run_substitute_file(nonexistent)

        self.assertEqual(proc.returncode, 1)

    def test_nonexistent_file_stderr_message(self):
        """stderr must mention 'not found' when --file does not exist."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        self._write_project_config_json()

        nonexistent = self.install_root / "does-not-exist.md"
        proc = self._run_substitute_file(nonexistent)

        self.assertIn(b"not found", proc.stderr)

    def test_nonexistent_file_no_project_config_exits_1_on_config(self):
        """When both project-config.json AND --file are absent, exit 1 is for
        the config (it is checked first)."""
        # Do NOT write project-config.json OR the target file.
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")

        nonexistent = self.install_root / "no-such-file.md"
        proc = self._run_substitute_file(nonexistent)

        # Exit 1 because project-config.json is checked before --file.
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"project-config.json not found", proc.stderr)

    def test_directory_passed_as_file_exits_1(self):
        """--file pointing at a directory (not a file) → exit 1 with 'not a file' message.

        update.sh constructs --file from shell vars and could pass a directory
        path if the variable is set incorrectly.
        """
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        self._write_project_config_json()

        # Pass the install_root directory itself as --file.
        proc = self._run_substitute_file(self.install_root)

        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"not a file", proc.stderr)


# ---------------------------------------------------------------------------
# Edge cases: init.yaml absent (packages_detected falls back to []).
# ---------------------------------------------------------------------------


class TestSubstituteFileInitYamlAbsent(_SubstituteFileFixture, unittest.TestCase):

    def test_init_yaml_absent_project_paths_empty_exit_0(self):
        """When init.yaml is absent, PROJECT_PATHS is empty string; {{PROJECT_PATHS}}
        substitutes to '' and exit is 0."""
        # render-config requires init.yaml, so we hand-author project-config.json
        # directly. The schema-drift assertion below ensures this dict stays aligned
        # with _PROJECT_CONFIG_KEY_ORDER as the schema evolves.
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "no-init")
        # Write a minimal project-config.json without running render-config
        # (which requires init.yaml). We use a hand-crafted config with the
        # expected keys so the substitution map can be built.
        minimal_config = {
            "PROJECT_NAME": "no-init",
            "PROJECT_DESCRIPTION": None,
            "PROJECT_TYPE": None,
            "PROJECT_ROOT": None,
            "WORKSPACE_MODE": None,
            "PROJECT_STATE": None,
            "DEFAULT_BRANCH": None,
            "LANGUAGES": [],
            "FRAMEWORKS": [],
            "PRIMARY_LANGUAGE": None,
            "ARCHITECTURES": [],
            "PROJECT_NATURES": [],
            "ERROR_HANDLINGS": [],
            "API_LAYERS": [],
            "TESTINGS": [],
            "BUILD_TOOLS": [],
            "BUILD_COMMANDS": [],
            "TYPE_CHECK_COMMANDS": [],
            "LINT_COMMANDS": [],
            "TEST_COMMANDS": [],
            "PACKAGES_DETECTED": [],
            "PACKAGE_STACKS": [],
            "PROJECT_STRUCTURE": None,
            "DEV_COMMANDS": None,
            "ARCHITECTURE_DETAILS": None,
            "WRAPPER_MODE_SECTION": "",
            "COMMIT_ATTRIBUTION": "",
            "AGENT_LIST": "",
            "WORKFLOW_ENFORCEMENT": None,
            "AI_ATTRIBUTION": None,
            "CLAUDE_TIER_THINK": None,
            "CLAUDE_TIER_DO": None,
            "CLAUDE_TIER_VERIFY": None,
            "AC_VERIFICATION_MODE": None,
            "AC_RUNTIME_URL": None,
            "AC_RUNTIME_API_BASE": None,
            "AC_RUNTIME_CLI_COMMAND": None,
            "REGRESSION_GATE": "full",
            "E2E_COMMAND": "",
        }
        # Schema-drift guard: fails loudly if _PROJECT_CONFIG_KEY_ORDER grows
        # or shrinks so a maintainer knows to update this hand-authored dict.
        self.assertEqual(
            set(minimal_config.keys()),
            set(_PROJECT_CONFIG_KEY_ORDER),
            "minimal_config is out of sync with _PROJECT_CONFIG_KEY_ORDER — "
            "update the dict above to match the current schema",
        )
        (self.devforge_dir / "project-config.json").write_text(
            json.dumps(minimal_config, indent=2),
            encoding="utf-8",
        )
        # init.yaml does NOT exist.

        target = self._write_target_file(
            "custom.md", "Paths: {{PROJECT_PATHS}}\nName: {{PROJECT_NAME}}\n"
        )
        proc = self._run_substitute_file(target)

        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        result = target.read_text(encoding="utf-8")
        self.assertIn("no-init", result)
        self.assertNotIn("{{PROJECT_NAME}}", result)
        # PROJECT_PATHS → empty string when packages_detected is absent.
        self.assertNotIn("{{PROJECT_PATHS}}", result)


if __name__ == "__main__":
    unittest.main()
