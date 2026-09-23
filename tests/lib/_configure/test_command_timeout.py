"""Tests for the COMMAND_TIMEOUT config key (101-NON-WEB-STACK-READINESS-
PLAN.md Phase 1, D1/OQ-1/OQ-2).

Covers the _configure/ side of the surface:
  - FIELD_SCHEMA / FIELD_DEFAULTS entries (scalar, appended LAST; NOT in
    ENUM_FIELDS -- a string scalar holding a decimal integer, not an enum).
  - set-command-timeout: accepts a positive integer, stored as its
    canonical decimal string; rejects a non-integer, zero, and a negative
    value (exit 2, naming the field).
  - default_state() / _load() back-fill "120" on a legacy configure.yaml
    written before this field existed.
  - COMMAND_TIMEOUT's position in _PROJECT_CONFIG_KEY_ORDER (LAST, after
    CLAUDE_EFFORT_SECURITY).
  - configure_helper verify exits 0 with command_timeout unset (the
    FIELD_DEFAULTS "120" baseline means the null-scalar check never fires
    for it, exactly as for e2e_command/require_ticket/claude_effort_*).
  - Legacy split by which file predates the change: (a) a configure.yaml
    written before this change back-fills "120" and passes verify after
    render-config; (b) a project-config.json rendered before this change
    is missing exactly one key (COMMAND_TIMEOUT) at verify time.
  - The REAL-PRODUCER round-trip this repo's testing rule requires for
    anything another tool parses: configure_helper set-command-timeout +
    render-config write the real project-config.json; this test reads it
    back via raw JSON.
  - The consumer's resolution (present/absent/unparseable/zero/negative)
    and its timed-out message are covered in
    tests/lib/_implement/test_cmds_verify.py (the actual consumer module),
    per this repo's real-producer-round-trip rule and to keep this file
    scoped to the _configure/ side of the surface.

Follows the _EnvIsolationMixin + module-level subprocess-helper pattern
from tests/lib/test_configure_helper.py (mirrored, not imported, per the
existing tests/lib/_configure/ precedent in test_require_ticket.py).

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
import init_helper  # noqa: E402


# ---------------------------------------------------------------------------
# Subprocess helpers -- mirrors test_configure_helper.py / test_require_
# ticket.py conventions exactly.
# ---------------------------------------------------------------------------


def _run_configure(devforge_dir, *args):
    """Invoke configure_helper.py <args> as a subprocess."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY), "--devforge-dir", str(devforge_dir)] + list(args),
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


class _EnvIsolationMixin:
    """Save/restore DEVFORGE_DIR around each test + provide a tmpdir.

    Layout:
      self._tmp.name/          <- install_root
        .devforge/             <- devforge_dir
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

    def _write_full_init_yaml(self):
        """Minimal init.yaml sufficient for render-config to succeed."""
        _run_init(self.devforge_dir, "reset")
        _run_init(self.devforge_dir, "set-workspace-mode", "standalone")
        _run_init(self.devforge_dir, "set-project-root", ".")
        _run_init(self.devforge_dir, "set-project-state", "brownfield")
        _run_init(self.devforge_dir, "set-default-branch", "main")

    def _populate_all_configure_fields(self):
        """Set every configure.yaml field with no FIELD_DEFAULTS baseline
        to a valid value -- command_timeout deliberately left unset since
        its FIELD_DEFAULTS "120" baseline means it needs no setter call
        for verify to pass, mirroring e2e_command/require_ticket/
        claude_effort_*."""
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "test-project")
        _run_configure(self.devforge_dir, "set-project-description", "A test project")
        _run_configure(self.devforge_dir, "set-project-type", "Web App")
        _run_configure(self.devforge_dir, "set-primary-language", "TypeScript")
        _run_configure(self.devforge_dir, "set-languages", "TypeScript")
        _run_configure(self.devforge_dir, "set-frameworks", "React")
        _run_configure(self.devforge_dir, "set-architectures", "MVC")
        _run_configure(self.devforge_dir, "set-project-natures", "web")
        _run_configure(self.devforge_dir, "set-error-handlings", "try-catch")
        _run_configure(self.devforge_dir, "set-api-layers", "REST")
        _run_configure(self.devforge_dir, "set-testings", "Jest")
        _run_configure(self.devforge_dir, "set-build-tools", "vite")
        _run_configure(self.devforge_dir, "set-build-commands", "npm run build")
        _run_configure(self.devforge_dir, "set-type-check-commands", "npx tsc")
        _run_configure(self.devforge_dir, "set-lint-commands", "npm run lint")
        _run_configure(self.devforge_dir, "set-test-commands", "npm test")
        _run_configure(
            self.devforge_dir, "add-package-stack",
            "--path", "src", "--language", "TypeScript",
        )
        _run_configure(self.devforge_dir, "set-project-structure", "--text", "src/")
        _run_configure(self.devforge_dir, "set-dev-commands", "--text", "npm start")
        _run_configure(self.devforge_dir, "set-architecture-details", "--text", "MVC pattern")
        _run_configure(self.devforge_dir, "set-workflow-enforcement", "Strict")
        _run_configure(self.devforge_dir, "set-ai-attribution", "No")
        _run_configure(self.devforge_dir, "set-claude-tier-think", "Opus")
        _run_configure(self.devforge_dir, "set-claude-tier-do", "Sonnet")
        _run_configure(self.devforge_dir, "set-claude-tier-verify", "Haiku")
        _run_configure(self.devforge_dir, "set-claude-tier-security", "Opus")
        _run_configure(self.devforge_dir, "set-ac-verification-mode", "code-only")


# ---------------------------------------------------------------------------
# Schema-level facts.
# ---------------------------------------------------------------------------


class SchemaTests(unittest.TestCase):
    def test_field_schema_contains_command_timeout_scalar(self):
        field_kinds = dict(configure_helper.FIELD_SCHEMA)
        self.assertEqual(field_kinds.get("command_timeout"), "scalar")

    def test_command_timeout_not_in_enum_fields(self):
        self.assertNotIn("command_timeout", configure_helper.ENUM_FIELDS)

    def test_field_defaults_is_120(self):
        self.assertEqual(configure_helper.FIELD_DEFAULTS["command_timeout"], "120")

    def test_default_state_command_timeout_is_120(self):
        state = configure_helper.default_state()
        self.assertEqual(state["command_timeout"], "120")

    def test_command_timeout_is_last_field_in_schema(self):
        names = [name for name, _kind in configure_helper.FIELD_SCHEMA]
        self.assertEqual(names[-1], "command_timeout")

    def test_command_timeout_is_last_key_in_project_config_order(self):
        keys = list(configure_helper._PROJECT_CONFIG_KEY_ORDER)
        self.assertEqual(keys[-1], "COMMAND_TIMEOUT")
        self.assertEqual(keys[-2], "CLAUDE_EFFORT_SECURITY")


# ---------------------------------------------------------------------------
# set-command-timeout setter.
# ---------------------------------------------------------------------------


class SetCommandTimeoutTests(_EnvIsolationMixin, unittest.TestCase):
    def test_positive_integer_accepted(self):
        proc = _run_configure(self.devforge_dir, "set-command-timeout", "1200")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["command_timeout"], "1200")

    def test_canonical_decimal_string_stored(self):
        """A value with leading zeros normalizes to its canonical decimal
        form -- the persisted value is stable regardless of how the
        caller wrote it."""
        proc = _run_configure(self.devforge_dir, "set-command-timeout", "0300")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["command_timeout"], "300")

    def test_non_integer_rejected(self):
        proc = _run_configure(self.devforge_dir, "set-command-timeout", "abc")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"command_timeout", proc.stderr)

    def test_zero_rejected(self):
        proc = _run_configure(self.devforge_dir, "set-command-timeout", "0")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"command_timeout", proc.stderr)

    def test_negative_rejected(self):
        proc = _run_configure(self.devforge_dir, "set-command-timeout", "-5")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"command_timeout", proc.stderr)

    def test_float_string_rejected(self):
        proc = _run_configure(self.devforge_dir, "set-command-timeout", "1.5")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"command_timeout", proc.stderr)

    def test_empty_rejected(self):
        proc = _run_configure(self.devforge_dir, "set-command-timeout", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"command_timeout", proc.stderr)

    def test_huge_digit_string_rejected_as_out_of_range(self):
        """A digit string too large to convert to float (roughly 309+
        digits) is rejected at set-time -- the same ceiling
        _implement/_cmds_verify.py's consumer falls back on, refused here
        before it ever reaches the consumer."""
        huge = "9" * 400
        proc = _run_configure(self.devforge_dir, "set-command-timeout", huge)
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"command_timeout", proc.stderr)

    def test_large_but_convertible_value_accepted(self):
        """A large value that IS representable as a float (well under the
        float-overflow boundary) is accepted and stored verbatim."""
        proc = _run_configure(self.devforge_dir, "set-command-timeout", str(10 ** 18))
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["command_timeout"], str(10 ** 18))

    def test_overwrite_prior_value(self):
        _run_configure(self.devforge_dir, "set-command-timeout", "600")
        _run_configure(self.devforge_dir, "set-command-timeout", "900")
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["command_timeout"], "900")

    def test_default_applied_to_existing_yaml_with_null_field(self):
        """_load() back-fills '120' when configure.yaml exists but
        command_timeout is null (a legacy install predating this field)."""
        from _configure._state import _load
        minimal_yaml = "project_name: old-install\ncommand_timeout: null\n"
        yaml_path = self.devforge_dir / configure_helper.OUTPUT_FILE_NAME
        yaml_path.write_text(minimal_yaml, encoding="utf-8")
        state = _load(self.devforge_dir)
        self.assertEqual(state["command_timeout"], "120")

    def test_default_applied_when_field_entirely_absent_from_yaml(self):
        """A configure.yaml written before this field existed at all
        (the key is simply not a line in the file) still back-fills
        '120' -- OQ-1's ratified legacy-install case."""
        from _configure._state import _load
        legacy_yaml = "project_name: old-install\n"
        yaml_path = self.devforge_dir / configure_helper.OUTPUT_FILE_NAME
        yaml_path.write_text(legacy_yaml, encoding="utf-8")
        state = _load(self.devforge_dir)
        self.assertEqual(state["command_timeout"], "120")


# ---------------------------------------------------------------------------
# Real-producer round-trip (this repo's rule for anything another tool
# parses): configure_helper writes the REAL project-config.json; raw JSON
# is read back and pinned.
# ---------------------------------------------------------------------------


class RealProducerRoundTripTests(_EnvIsolationMixin, unittest.TestCase):
    def test_value_round_trips_through_render_config_as_last_key(self):
        self._write_full_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-command-timeout", "1800")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertIn("COMMAND_TIMEOUT", data)
        self.assertEqual(data["COMMAND_TIMEOUT"], "1800")

        keys = list(data.keys())
        self.assertEqual(keys[-1], "COMMAND_TIMEOUT")

    def test_default_120_when_never_set_round_trips(self):
        """Key never set (never called set-command-timeout): OQ-1's
        ratified legacy-install / never-configured default, read all the
        way through render-config -- today's behaviour, unchanged."""
        self._write_full_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(data["COMMAND_TIMEOUT"], "120")

    def test_verify_exits_0_with_command_timeout_unset(self):
        """configure_helper verify exits 0 with command_timeout unset --
        same upgrade-path guard as plan 90's e2e_command test: an install
        that upgrades and then fails its own config check has shipped a
        regression to every consumer at once."""
        self._write_full_init_yaml()
        self._populate_all_configure_fields()
        # command_timeout deliberately left unset -- FIELD_DEFAULTS "120"
        # baseline must keep it out of the null-scalar check.

        _run_configure(self.devforge_dir, "render-config")
        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn(b"verify: ok", proc.stderr)
        self.assertNotIn(b"COMMAND_TIMEOUT", proc.stderr)

    def test_verify_exits_0_with_non_default_command_timeout_round_trip(self):
        """configure_helper verify exits 0 with a NON-default
        command_timeout ("1800") -- exercising verify's round-trip
        identity check (configure.yaml.command_timeout ==
        project-config.json.COMMAND_TIMEOUT) on an actual value, not just
        the null-scalar-unset case above (Phase 1's Verify)."""
        self._write_full_init_yaml()
        self._populate_all_configure_fields()
        _run_configure(self.devforge_dir, "set-command-timeout", "1800")

        _run_configure(self.devforge_dir, "render-config")
        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn(b"verify: ok", proc.stderr)

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(data["COMMAND_TIMEOUT"], "1800")


# ---------------------------------------------------------------------------
# Legacy split by which file predates the change (Phase 1 Verify).
# ---------------------------------------------------------------------------


class LegacyUpgradeTests(_EnvIsolationMixin, unittest.TestCase):
    def test_legacy_configure_yaml_backfills_and_passes_verify(self):
        """(a) A configure.yaml written BEFORE this change: loading it
        back-fills "120" with no setter call, and after render-config
        `configure_helper verify` passes."""
        self._write_full_init_yaml()
        self._populate_all_configure_fields()
        # Emulate a pre-change configure.yaml by stripping the
        # command_timeout line the real emitter would otherwise write --
        # built from the real emit_yaml() producer, never a hand-authored
        # fixture (mirrors plan 90's e2e_command / plan 91's require_
        # ticket legacy-yaml pattern).
        from _configure._state import _load
        from _configure._yaml import emit_yaml

        state = _load(self.devforge_dir)
        text = emit_yaml(state)
        legacy_text = "\n".join(
            line for line in text.splitlines() if not line.startswith("command_timeout:")
        ) + "\n"
        self.assertNotIn("command_timeout:", legacy_text)
        (self.devforge_dir / configure_helper.OUTPUT_FILE_NAME).write_text(
            legacy_text, encoding="utf-8"
        )

        reloaded = _load(self.devforge_dir)
        self.assertEqual(reloaded["command_timeout"], "120")

        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn(b"verify: ok", proc.stderr)

    def test_legacy_project_config_json_reports_exactly_one_violation(self):
        """(b) A project-config.json rendered BEFORE this change:
        `configure_helper verify` reports exactly one new violation,
        "project-config.json missing key COMMAND_TIMEOUT"."""
        self._write_full_init_yaml()
        self._populate_all_configure_fields()
        _run_configure(self.devforge_dir, "render-config")

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertIn("COMMAND_TIMEOUT", data)
        del data["COMMAND_TIMEOUT"]
        config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        stderr_lines = [
            line for line in proc.stderr.decode().splitlines() if "COMMAND_TIMEOUT" in line
        ]
        self.assertEqual(
            stderr_lines,
            ["verify: project-config.json missing key COMMAND_TIMEOUT"],
        )


if __name__ == "__main__":
    unittest.main()
