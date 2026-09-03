"""Tests for 92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md Phase 1, Deliverables 1+2.

Deliverable 1 (D4) — the three effort fields `claude_effort_think` /
`claude_effort_do` / `claude_effort_verify`:
  - FIELD_SCHEMA / ENUM_FIELDS / FIELD_DEFAULTS entries (appended last,
    after require_ticket).
  - set-claude-effort-{think,do,verify}: accept every one of the six
    enum members (default | low | medium | high | xhigh | max,
    case-insensitively folded to the canonical lowercase member via
    _validate_enum), reject any other value, reject empty.
  - default_state() / _load() back-fill "default" on a legacy
    configure.yaml written before these fields existed — "default" is a
    real ENUM_FIELDS member, not a null sentinel, so this needs no
    _cmds_verify.py exemption (same mechanism as e2e_command /
    require_ticket).
  - CLAUDE_EFFORT_THINK / _DO / _VERIFY's position in
    _PROJECT_CONFIG_KEY_ORDER (the last three keys, after REQUIRE_TICKET).
  - configure_helper verify exits 0 with the trio unset, AND against a
    legacy configure.yaml written before they existed.
  - The three fields render under the configure summary's "Preferences"
    group, directly after claude_tier_verify.
  - The REAL-PRODUCER round-trip this repo's testing rule requires for
    anything another tool parses: configure_helper set-claude-effort-*
    + render-config write the real project-config.json; this test reads
    it back via raw JSON.

Deliverable 2 (D3) — alias normalization in the claude_tier_* setters:
  - A value that case-insensitively matches one of the four Claude Code
    subagent `model:` aliases (opus/sonnet/haiku/fable) is stored in its
    lowercase canonical form, regardless of the case (or surrounding
    whitespace) submitted.
  - Any other non-empty scalar (a Bedrock route, a pinned full model ID,
    etc.) is stored verbatim, unchanged — today's `Other`-branch pin
    behavior, preserved exactly.
  - Empty values are still rejected (exit 2), unaffected by the
    normalization change.

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


_EFFORT_ENUM_MEMBERS = ("default", "low", "medium", "high", "xhigh", "max")
_EFFORT_TIERS = ("think", "do", "verify")


# ---------------------------------------------------------------------------
# Schema-level facts (Deliverable 1 / D4).
# ---------------------------------------------------------------------------


class SchemaTests(unittest.TestCase):
    def test_field_schema_ends_with_effort_trio_in_order(self):
        names = [name for name, _kind in configure_helper.FIELD_SCHEMA]
        self.assertEqual(
            names[-3:],
            ["claude_effort_think", "claude_effort_do", "claude_effort_verify"],
        )

    def test_field_schema_effort_trio_are_scalars(self):
        field_kinds = dict(configure_helper.FIELD_SCHEMA)
        for tier in _EFFORT_TIERS:
            self.assertEqual(field_kinds.get("claude_effort_{0}".format(tier)), "scalar")

    def test_enum_fields_effort_trio_has_six_members(self):
        for tier in _EFFORT_TIERS:
            self.assertEqual(
                configure_helper.ENUM_FIELDS["claude_effort_{0}".format(tier)],
                {"default", "low", "medium", "high", "xhigh", "max"},
            )

    def test_field_defaults_effort_trio_is_default(self):
        for tier in _EFFORT_TIERS:
            self.assertEqual(
                configure_helper.FIELD_DEFAULTS["claude_effort_{0}".format(tier)],
                "default",
            )

    def test_default_state_effort_trio_is_default(self):
        state = configure_helper.default_state()
        for tier in _EFFORT_TIERS:
            self.assertEqual(state["claude_effort_{0}".format(tier)], "default")

    def test_effort_keys_are_last_three_in_project_config_key_order(self):
        """CLAUDE_EFFORT_THINK/_DO/_VERIFY appear last, immediately after
        REQUIRE_TICKET, in that order."""
        keys = list(configure_helper._PROJECT_CONFIG_KEY_ORDER)
        idx_rt = keys.index("REQUIRE_TICKET")
        self.assertEqual(
            keys[idx_rt + 1:],
            ["CLAUDE_EFFORT_THINK", "CLAUDE_EFFORT_DO", "CLAUDE_EFFORT_VERIFY"],
        )
        self.assertEqual(keys[-3:], ["CLAUDE_EFFORT_THINK", "CLAUDE_EFFORT_DO", "CLAUDE_EFFORT_VERIFY"])


# ---------------------------------------------------------------------------
# set-claude-effort-{think,do,verify} setters.
# ---------------------------------------------------------------------------


class SetClaudeEffortTests(_EnvIsolationMixin, unittest.TestCase):
    def test_every_member_accepted_for_every_tier(self):
        for tier in _EFFORT_TIERS:
            for member in _EFFORT_ENUM_MEMBERS:
                with self.subTest(tier=tier, member=member):
                    devforge_dir = self.devforge_dir / tier / member
                    devforge_dir.mkdir(parents=True, exist_ok=True)
                    proc = _run_configure(
                        devforge_dir, "set-claude-effort-{0}".format(tier), member
                    )
                    self.assertEqual(proc.returncode, 0, proc.stderr.decode())
                    state = configure_helper.parse_yaml(
                        (devforge_dir / configure_helper.OUTPUT_FILE_NAME).read_text(
                            encoding="utf-8"
                        )
                    )
                    self.assertEqual(state["claude_effort_{0}".format(tier)], member)

    def test_case_insensitive_folded_to_canonical(self):
        proc = _run_configure(self.devforge_dir, "set-claude-effort-think", "HIGH")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["claude_effort_think"], "high")

    def test_invalid_value_rejected(self):
        for tier in _EFFORT_TIERS:
            with self.subTest(tier=tier):
                proc = _run_configure(
                    self.devforge_dir, "set-claude-effort-{0}".format(tier), "extreme"
                )
                self.assertEqual(proc.returncode, 2)
                self.assertIn("claude_effort_{0}".format(tier).encode(), proc.stderr)

    def test_empty_rejected(self):
        for tier in _EFFORT_TIERS:
            with self.subTest(tier=tier):
                proc = _run_configure(
                    self.devforge_dir, "set-claude-effort-{0}".format(tier), ""
                )
                self.assertEqual(proc.returncode, 2)

    def test_overwrite_prior_value(self):
        _run_configure(self.devforge_dir, "set-claude-effort-do", "low")
        _run_configure(self.devforge_dir, "set-claude-effort-do", "xhigh")
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["claude_effort_do"], "xhigh")

    def test_default_applied_to_existing_yaml_missing_field(self):
        """_load() back-fills 'default' when configure.yaml exists but a
        claude_effort_* field is null (a legacy install predating this field)."""
        from _configure._state import _load
        minimal_yaml = (
            "project_name: old-install\n"
            "claude_effort_think: null\n"
            "claude_effort_do: null\n"
            "claude_effort_verify: null\n"
        )
        yaml_path = self.devforge_dir / configure_helper.OUTPUT_FILE_NAME
        yaml_path.write_text(minimal_yaml, encoding="utf-8")
        state = _load(self.devforge_dir)
        for tier in _EFFORT_TIERS:
            self.assertEqual(state["claude_effort_{0}".format(tier)], "default")

    def test_default_applied_when_field_entirely_absent_from_yaml(self):
        """A configure.yaml written before these fields existed at all
        (the keys are simply not lines in the file) still back-fills
        'default' for each -- the legacy-install case this plan targets."""
        from _configure._state import _load
        legacy_yaml = "project_name: old-install\n"
        yaml_path = self.devforge_dir / configure_helper.OUTPUT_FILE_NAME
        yaml_path.write_text(legacy_yaml, encoding="utf-8")
        state = _load(self.devforge_dir)
        for tier in _EFFORT_TIERS:
            self.assertEqual(state["claude_effort_{0}".format(tier)], "default")


# ---------------------------------------------------------------------------
# Real-producer round-trip (this repo's rule for anything another tool
# parses): configure_helper writes the REAL project-config.json; the raw
# JSON is read back and pinned.
# ---------------------------------------------------------------------------


class RealProducerRoundTripTests(_EnvIsolationMixin, unittest.TestCase):
    def test_effort_trio_round_trips_through_render_config(self):
        self._write_full_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-claude-effort-think", "high")
        _run_configure(self.devforge_dir, "set-claude-effort-do", "low")
        _run_configure(self.devforge_dir, "set-claude-effort-verify", "xhigh")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(data["CLAUDE_EFFORT_THINK"], "high")
        self.assertEqual(data["CLAUDE_EFFORT_DO"], "low")
        self.assertEqual(data["CLAUDE_EFFORT_VERIFY"], "xhigh")

        # The three effort keys are the LAST three keys emitted, in order.
        keys = list(data.keys())
        self.assertEqual(
            keys[-3:], ["CLAUDE_EFFORT_THINK", "CLAUDE_EFFORT_DO", "CLAUDE_EFFORT_VERIFY"]
        )

    def test_effort_trio_defaults_to_default_when_never_set(self):
        self._write_full_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        # No set-claude-effort-* calls -- reset writes default_state(),
        # which has "default" for all three (FIELD_DEFAULTS).
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(data["CLAUDE_EFFORT_THINK"], "default")
        self.assertEqual(data["CLAUDE_EFFORT_DO"], "default")
        self.assertEqual(data["CLAUDE_EFFORT_VERIFY"], "default")

    def test_verify_exits_0_with_effort_trio_unset(self):
        """configure_helper verify exits 0 with the effort trio unset --
        same upgrade-path guard as plan 90's e2e_command / plan 91's
        require_ticket tests: an install that upgrades and then fails
        its own config check has shipped a regression to every consumer
        at once."""
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
        _run_configure(self.devforge_dir, "set-claude-tier-think", "opus")
        _run_configure(self.devforge_dir, "set-claude-tier-do", "sonnet")
        _run_configure(self.devforge_dir, "set-claude-tier-verify", "haiku")
        _run_configure(self.devforge_dir, "set-ac-verification-mode", "code-only")
        # claude_effort_* deliberately left unset -- FIELD_DEFAULTS "default"
        # baseline must keep them out of the null-scalar check.

        _run_configure(self.devforge_dir, "render-config")
        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn(b"verify: ok", proc.stderr)
        self.assertNotIn(b"claude_effort", proc.stderr.lower())
        self.assertNotIn(b"CLAUDE_EFFORT", proc.stderr)

    def test_verify_exits_0_on_legacy_yaml_missing_effort_fields(self):
        """configure_helper verify exits 0 against a configure.yaml written
        before these fields existed -- the pre-build shape lacks the
        'claude_effort_*:' lines entirely. Built from the real emit_yaml()
        producer with those lines stripped out afterward, to simulate the
        pre-migration artifact shape without inventing a hand-authored
        fixture from scratch (mirrors plan 90's e2e_command equivalent)."""
        self._write_full_init_yaml()

        state = configure_helper.default_state()
        state.update({
            "project_name": "legacy-install",
            "project_description": "A pre-migration project",
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
            "package_stacks": [
                {
                    "path": "src",
                    "language": "TypeScript",
                    "framework": None,
                    "build_tool": None,
                    "build_command": None,
                    "type_check_command": None,
                    "lint_command": None,
                    "test_command": None,
                }
            ],
            "project_structure": "src/",
            "dev_commands": "npm start",
            "architecture_details": "MVC pattern",
            "workflow_enforcement": "Strict",
            "ai_attribution": "No",
            "claude_tier_think": "opus",
            "claude_tier_do": "sonnet",
            "claude_tier_verify": "haiku",
            "ac_verification_mode": "code-only",
        })
        text = configure_helper.emit_yaml(state)
        legacy_text = "\n".join(
            line for line in text.splitlines()
            if not line.startswith("claude_effort_")
        ) + "\n"
        self.assertNotIn("claude_effort_", legacy_text)  # sanity: lines really stripped

        yaml_path = self.devforge_dir / configure_helper.OUTPUT_FILE_NAME
        yaml_path.write_text(legacy_text, encoding="utf-8")

        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn(b"verify: ok", proc.stderr)

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(data["CLAUDE_EFFORT_THINK"], "default")
        self.assertEqual(data["CLAUDE_EFFORT_DO"], "default")
        self.assertEqual(data["CLAUDE_EFFORT_VERIFY"], "default")


# ---------------------------------------------------------------------------
# Summary rendering (Preferences group).
# ---------------------------------------------------------------------------


class SummaryTests(_EnvIsolationMixin, unittest.TestCase):
    def test_effort_trio_rendered_under_preferences_group(self):
        """claude_effort_* (plan 92 D4) render in the 'Preferences' group,
        directly after claude_tier_verify."""
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-claude-effort-think", "high")
        proc = _run_configure(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        out = proc.stdout.decode()
        prefs_section = out.split("### Preferences", 1)[1].split("### ", 1)[0]
        self.assertIn("claude_effort_think", prefs_section)
        self.assertIn("high", prefs_section)
        self.assertIn("claude_effort_do", prefs_section)
        self.assertIn("claude_effort_verify", prefs_section)


# ---------------------------------------------------------------------------
# Alias normalization (Deliverable 2 / D3) -- _cmd_set_claude_tier.
# ---------------------------------------------------------------------------


class AliasNormalizationTests(_EnvIsolationMixin, unittest.TestCase):
    def test_opus_normalized_to_lowercase(self):
        proc = _run_configure(self.devforge_dir, "set-claude-tier-think", "Opus")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["claude_tier_think"], "opus")

    def test_fable_uppercase_normalized_to_lowercase(self):
        proc = _run_configure(self.devforge_dir, "set-claude-tier-do", "FABLE")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["claude_tier_do"], "fable")

    def test_padded_sonnet_normalized(self):
        proc = _run_configure(self.devforge_dir, "set-claude-tier-verify", " sonnet ")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["claude_tier_verify"], "sonnet")

    def test_lowercase_haiku_stays_lowercase(self):
        proc = _run_configure(self.devforge_dir, "set-claude-tier-think", "haiku")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["claude_tier_think"], "haiku")

    def test_bedrock_route_pin_stored_unchanged(self):
        proc = _run_configure(
            self.devforge_dir, "set-claude-tier-do", "my-bedrock-route"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["claude_tier_do"], "my-bedrock-route")

    def test_versioned_model_id_pin_stored_unchanged(self):
        proc = _run_configure(
            self.devforge_dir, "set-claude-tier-verify", "claude-opus-5"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["claude_tier_verify"], "claude-opus-5")

    def test_empty_value_still_rejected(self):
        proc = _run_configure(self.devforge_dir, "set-claude-tier-think", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"claude_tier_think", proc.stderr)


if __name__ == "__main__":
    unittest.main()
