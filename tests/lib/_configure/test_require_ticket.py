"""Tests for the REQUIRE_TICKET config key (91-FEATURE-DIR-IDENTITY-AND-
PROVENANCE-PLAN.md Phase 2, D4/OQ-1/OQ-2).

Covers the _configure/ side of the surface:
  - FIELD_SCHEMA / ENUM_FIELDS / FIELD_DEFAULTS entries.
  - set-require-ticket: accepts "true"/"false" (case-insensitive, folded
    to the canonical lowercase member via _validate_enum), rejects any
    other value, rejects empty.
  - default_state() / _load() back-fill "false" on a legacy configure.yaml
    written before this field existed.
  - REQUIRE_TICKET's position in _PROJECT_CONFIG_KEY_ORDER (immediately
    after E2E_COMMAND).
  - configure_helper verify exits 0 with require_ticket unset (the
    FIELD_DEFAULTS "false" baseline means the null-scalar check never
    fires for it, exactly as for e2e_command/regression_gate).
  - The REAL-PRODUCER round-trip this repo's testing rule requires for
    anything another tool parses: configure_helper set-require-ticket +
    render-config write the real project-config.json; this test reads
    it back BOTH via raw JSON (to pin the emitted shape) AND via
    _shared.feature_alloc.read_require_ticket (the actual consumer this
    plan wires the key for) -- so the boundary between "configure_helper
    emits it" and "the reader function understands it" is exercised
    end-to-end, not just unit-tested in isolation on each side.

Follows the _EnvIsolationMixin + module-level subprocess-helper pattern
from tests/lib/test_configure_helper.py (mirrored, not imported, per the
existing tests/lib/_configure/ precedent in test_substitute_file.py).

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
from _shared.feature_alloc import read_require_ticket  # noqa: E402


# ---------------------------------------------------------------------------
# Subprocess helpers -- mirrors test_configure_helper.py conventions exactly.
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


# ---------------------------------------------------------------------------
# Schema-level facts.
# ---------------------------------------------------------------------------


class SchemaTests(unittest.TestCase):
    def test_field_schema_contains_require_ticket_scalar(self):
        field_kinds = dict(configure_helper.FIELD_SCHEMA)
        self.assertEqual(field_kinds.get("require_ticket"), "scalar")

    def test_enum_fields_contains_require_ticket(self):
        self.assertEqual(
            configure_helper.ENUM_FIELDS["require_ticket"], {"true", "false"},
        )

    def test_field_defaults_is_false(self):
        self.assertEqual(configure_helper.FIELD_DEFAULTS["require_ticket"], "false")

    def test_default_state_require_ticket_is_false(self):
        state = configure_helper.default_state()
        self.assertEqual(state["require_ticket"], "false")

    def test_require_ticket_key_position_after_e2e_command(self):
        """REQUIRE_TICKET appears immediately after E2E_COMMAND in key order."""
        keys = list(configure_helper._PROJECT_CONFIG_KEY_ORDER)
        idx_e2e = keys.index("E2E_COMMAND")
        idx_rt = keys.index("REQUIRE_TICKET")
        self.assertEqual(idx_rt, idx_e2e + 1)


# ---------------------------------------------------------------------------
# set-require-ticket setter.
# ---------------------------------------------------------------------------


class SetRequireTicketTests(_EnvIsolationMixin, unittest.TestCase):
    def test_true_accepted(self):
        proc = _run_configure(self.devforge_dir, "set-require-ticket", "true")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["require_ticket"], "true")

    def test_false_accepted(self):
        proc = _run_configure(self.devforge_dir, "set-require-ticket", "false")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["require_ticket"], "false")

    def test_case_insensitive_folded_to_canonical(self):
        """'TRUE' is accepted and stored as the canonical lowercase 'true'
        (matching _validate_enum's documented case-insensitive-fold
        behaviour for every other enum field in this schema)."""
        proc = _run_configure(self.devforge_dir, "set-require-ticket", "TRUE")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["require_ticket"], "true")

    def test_invalid_value_rejected(self):
        proc = _run_configure(self.devforge_dir, "set-require-ticket", "maybe")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"require_ticket", proc.stderr)

    def test_empty_rejected(self):
        proc = _run_configure(self.devforge_dir, "set-require-ticket", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"require_ticket", proc.stderr)

    def test_overwrite_prior_value(self):
        _run_configure(self.devforge_dir, "set-require-ticket", "true")
        _run_configure(self.devforge_dir, "set-require-ticket", "false")
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["require_ticket"], "false")

    def test_default_applied_to_existing_yaml_missing_field(self):
        """_load() back-fills 'false' when configure.yaml exists but
        require_ticket is null (a legacy install predating this field)."""
        from _configure._state import _load
        minimal_yaml = "project_name: old-install\nrequire_ticket: null\n"
        yaml_path = self.devforge_dir / configure_helper.OUTPUT_FILE_NAME
        yaml_path.write_text(minimal_yaml, encoding="utf-8")
        state = _load(self.devforge_dir)
        self.assertEqual(state["require_ticket"], "false")

    def test_default_applied_when_field_entirely_absent_from_yaml(self):
        """A configure.yaml written before this field existed at all
        (the key is simply not a line in the file) still back-fills
        'false' -- the legacy-install case OQ-1 is framed around."""
        from _configure._state import _load
        legacy_yaml = "project_name: old-install\n"
        yaml_path = self.devforge_dir / configure_helper.OUTPUT_FILE_NAME
        yaml_path.write_text(legacy_yaml, encoding="utf-8")
        state = _load(self.devforge_dir)
        self.assertEqual(state["require_ticket"], "false")


# ---------------------------------------------------------------------------
# Real-producer round-trip (this repo's rule for anything another tool
# parses): configure_helper writes the REAL project-config.json; both a
# raw-JSON assertion and the actual consumer function (read_require_ticket)
# read it back.
# ---------------------------------------------------------------------------


class RealProducerRoundTripTests(_EnvIsolationMixin, unittest.TestCase):
    def test_true_round_trips_through_render_config_and_reader(self):
        self._write_full_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-require-ticket", "true")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertIn("REQUIRE_TICKET", data)
        self.assertEqual(data["REQUIRE_TICKET"], "true")

        # The actual consumer this plan wires the key for.
        self.assertTrue(read_require_ticket(self.devforge_dir))

    def test_false_round_trips_through_render_config_and_reader(self):
        self._write_full_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-require-ticket", "false")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(data["REQUIRE_TICKET"], "false")
        self.assertFalse(read_require_ticket(self.devforge_dir))

    def test_default_false_when_never_set_round_trips_through_reader(self):
        """Key absent (never called set-require-ticket): OQ-1's ratified
        legacy-install / never-configured default, read all the way
        through to the actual consumer function."""
        self._write_full_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        # No set-require-ticket call -- reset writes default_state(),
        # which has require_ticket="false" (FIELD_DEFAULTS).
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(data["REQUIRE_TICKET"], "false")
        self.assertFalse(read_require_ticket(self.devforge_dir))

    def test_verify_exits_0_with_require_ticket_unset(self):
        """configure_helper verify exits 0 with require_ticket unset --
        same upgrade-path guard as plan 90's e2e_command test: an install
        that upgrades and then fails its own config check has shipped a
        regression to every consumer at once."""
        self._write_full_init_yaml()
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
        _run_configure(self.devforge_dir, "set-ac-verification-mode", "code-only")
        # require_ticket deliberately left unset -- FIELD_DEFAULTS "false"
        # baseline must keep it out of the null-scalar check.

        _run_configure(self.devforge_dir, "render-config")
        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn(b"verify: ok", proc.stderr)
        self.assertNotIn(b"require_ticket", proc.stderr.lower())
        self.assertNotIn(b"REQUIRE_TICKET", proc.stderr)


if __name__ == "__main__":
    unittest.main()
