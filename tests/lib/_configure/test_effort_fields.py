"""Tests for 92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md Phase 1, Deliverables 1+2,
extended by 94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md Phase 1 Deliverable 6
(the fourth tier's configuration surface, `security`).

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

Plan 94 Phase 1 Deliverable 6 — the fourth tier's configuration surface
(`claude_tier_security` / `claude_effort_security`), added after this
file's original Deliverable 1+2 coverage was written (`_EFFORT_TIERS`
below now includes "security", so every existing parametrized/enumerated
effort-trio test above widens to the quad for free):
  - claude_tier_security mirrors claude_tier_think/do/verify EXACTLY:
    FIELD_SCHEMA scalar entry, NOT in ENUM_FIELDS, NO FIELD_DEFAULTS
    entry, set through the same shared _cmd_set_claude_tier (alias
    normalization: opus/sonnet/haiku/fable case-insensitively folded to
    lowercase, any other non-empty scalar stored verbatim as a pin) via
    a new set-claude-tier-security CLI verb.
  - claude_effort_security mirrors claude_effort_think/do/verify
    EXACTLY: FIELD_SCHEMA scalar entry, ENUM_FIELDS six-member set,
    FIELD_DEFAULTS "default", set through the same shared _cmd_set_enum
    via a new set-claude-effort-security CLI verb.
  - Both fields are APPENDED LAST in FIELD_SCHEMA (after
    claude_effort_verify, as claude_tier_security then
    claude_effort_security) and in _PROJECT_CONFIG_KEY_ORDER (as
    CLAUDE_TIER_SECURITY then CLAUDE_EFFORT_SECURITY) — this deliverable
    is scoped independently of the shared apply-verb machinery another
    Phase 1 run owns for the other three tiers, so it does not touch
    _agent_models.py / _cmds_agent_models.py.
  - The counted numbers this deliverable moves: FIELD_SCHEMA 35 -> 37,
    _PROJECT_CONFIG_KEY_ORDER 43 -> 45, ENUM_FIELDS 8 -> 9,
    FIELD_DEFAULTS 6 -> 7 (see test_configure_helper.py's four renamed
    count-pin tests for the schema-wide assertions; this file covers
    only the setter/render/verify/summary behavior the new pair
    exercises).
  - configure_helper verify's behavior on an unset claude_tier_security
    is NOT the same as an unset claude_effort_security: the tier field
    has no FIELD_DEFAULTS baseline (mirroring claude_tier_verify), so
    verify's null-scalar check fires and reports a violation exactly as
    it does today for a null claude_tier_verify (exit 2) -- proven
    empirically against the real subprocess before this file assumed it
    (see TierSecurityVerifyTests below). The effort field DOES have a
    "default" baseline, so it behaves like its three effort siblings
    (exit 0 when unset, and on a legacy configure.yaml written before
    it existed).

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
_EFFORT_TIERS = ("think", "do", "verify", "security")


# ---------------------------------------------------------------------------
# Schema-level facts (Deliverable 1 / D4).
# ---------------------------------------------------------------------------


class SchemaTests(unittest.TestCase):
    def test_field_schema_ends_with_effort_trio_then_security_pair(self):
        """The original effort trio (claude_effort_think/do/verify) is
        immediately followed by the security pair (94-MODEL-OVERRIDE-AND-
        NO-DEFAULTS-PLAN.md D3), appended last as claude_tier_security
        then claude_effort_security -- NOT clustered beside
        claude_tier_verify/claude_effort_verify."""
        names = [name for name, _kind in configure_helper.FIELD_SCHEMA]
        self.assertEqual(
            names[-5:],
            [
                "claude_effort_think",
                "claude_effort_do",
                "claude_effort_verify",
                "claude_tier_security",
                "claude_effort_security",
            ],
        )

    def test_field_schema_effort_trio_are_scalars(self):
        field_kinds = dict(configure_helper.FIELD_SCHEMA)
        for tier in _EFFORT_TIERS:
            self.assertEqual(field_kinds.get("claude_effort_{0}".format(tier)), "scalar")

    def test_field_schema_claude_tier_security_is_scalar_not_in_enum_fields(self):
        """claude_tier_security mirrors claude_tier_think/do/verify: a
        FIELD_SCHEMA scalar entry that is deliberately NOT enum-restricted
        (any non-empty scalar is a valid pin)."""
        field_kinds = dict(configure_helper.FIELD_SCHEMA)
        self.assertEqual(field_kinds.get("claude_tier_security"), "scalar")
        self.assertNotIn("claude_tier_security", configure_helper.ENUM_FIELDS)
        self.assertNotIn("claude_tier_security", configure_helper.FIELD_DEFAULTS)

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

    def test_effort_keys_and_security_pair_follow_require_ticket_in_order(self):
        """CLAUDE_EFFORT_THINK/_DO/_VERIFY immediately follow REQUIRE_TICKET,
        followed immediately by CLAUDE_TIER_SECURITY then
        CLAUDE_EFFORT_SECURITY -- the last two keys overall
        (94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md D3)."""
        keys = list(configure_helper._PROJECT_CONFIG_KEY_ORDER)
        idx_rt = keys.index("REQUIRE_TICKET")
        self.assertEqual(
            keys[idx_rt + 1:],
            [
                "CLAUDE_EFFORT_THINK",
                "CLAUDE_EFFORT_DO",
                "CLAUDE_EFFORT_VERIFY",
                "CLAUDE_TIER_SECURITY",
                "CLAUDE_EFFORT_SECURITY",
            ],
        )
        self.assertEqual(keys[-2:], ["CLAUDE_TIER_SECURITY", "CLAUDE_EFFORT_SECURITY"])


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

        # The three effort keys are immediately followed by the security
        # pair (unset in this test, so null/"default") -- five keys total
        # from this point to the end of the emitted JSON.
        keys = list(data.keys())
        self.assertEqual(
            keys[-5:],
            [
                "CLAUDE_EFFORT_THINK",
                "CLAUDE_EFFORT_DO",
                "CLAUDE_EFFORT_VERIFY",
                "CLAUDE_TIER_SECURITY",
                "CLAUDE_EFFORT_SECURITY",
            ],
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
        # claude_tier_security (plan 94 D3) has NO FIELD_DEFAULTS baseline,
        # mirroring claude_tier_think/do/verify exactly -- unlike the
        # claude_effort_* quad below, it MUST be set for verify to pass
        # (see TierSecurityVerifyTests for the exit-2 proof of the
        # opposite case).
        _run_configure(self.devforge_dir, "set-claude-tier-security", "opus")
        _run_configure(self.devforge_dir, "set-ac-verification-mode", "code-only")
        # claude_effort_* (all four, incl. claude_effort_security)
        # deliberately left unset -- FIELD_DEFAULTS "default" baseline
        # must keep them out of the null-scalar check.

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
            # claude_tier_security (plan 94 D3) has NO FIELD_DEFAULTS
            # baseline, mirroring claude_tier_think/do/verify exactly --
            # it must be set here so this legacy fixture exercises ONLY
            # the claude_effort_* back-fill this test is actually about
            # (a genuinely legacy yaml would predate BOTH new fields, but
            # that combined case is a real verify violation, not a
            # regression -- see TierSecurityVerifyTests).
            "claude_tier_security": "opus",
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
        self.assertEqual(data["CLAUDE_EFFORT_SECURITY"], "default")


# ---------------------------------------------------------------------------
# Security tier + effort (plan 94 Phase 1 Deliverable 6) -- dedicated
# coverage for the shape that differs from its siblings: claude_tier_
# security has NO FIELD_DEFAULTS baseline (mirrors claude_tier_verify),
# so an unset claude_tier_security is a verify VIOLATION (exit 2),
# unlike claude_effort_security which behaves exactly like its three
# effort siblings (exit 0 when unset).
# ---------------------------------------------------------------------------


class SecurityTierRoundTripTests(_EnvIsolationMixin, unittest.TestCase):
    def test_security_pair_round_trips_through_render_config_as_last_two_keys(self):
        self._write_full_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-claude-tier-security", "opus")
        _run_configure(self.devforge_dir, "set-claude-effort-security", "high")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(data["CLAUDE_TIER_SECURITY"], "opus")
        self.assertEqual(data["CLAUDE_EFFORT_SECURITY"], "high")

        keys = list(data.keys())
        self.assertEqual(keys[-2:], ["CLAUDE_TIER_SECURITY", "CLAUDE_EFFORT_SECURITY"])

    def test_security_pair_renders_null_tier_default_effort_when_unset(self):
        """render-config emits CLAUDE_TIER_SECURITY=null (never "inherit"
        or any other sentinel -- claude_tier_security has no FIELD_DEFAULTS
        entry) and CLAUDE_EFFORT_SECURITY="default" when neither setter was
        ever called, and both remain the LAST two keys in that order."""
        self._write_full_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        # No set-claude-tier-security / set-claude-effort-security calls.
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertIsNone(data["CLAUDE_TIER_SECURITY"])
        self.assertEqual(data["CLAUDE_EFFORT_SECURITY"], "default")

        keys = list(data.keys())
        self.assertEqual(keys[-2:], ["CLAUDE_TIER_SECURITY", "CLAUDE_EFFORT_SECURITY"])

    def test_load_backfills_default_for_effort_security_on_legacy_yaml(self):
        """_load() back-fills 'default' for claude_effort_security when a
        configure.yaml predates this field -- built from the real
        emit_yaml() producer with only the claude_effort_security line
        stripped out afterward (mirrors plan 90's e2e_command / plan 92's
        effort-trio legacy-yaml pattern), never a hand-authored fixture.
        claude_tier_security is kept set (has no default of its own, so
        stripping it too would test a different thing -- see
        TierSecurityVerifyTests for that case)."""
        from _configure._state import _load

        state = configure_helper.default_state()
        state["claude_tier_security"] = "opus"
        text = configure_helper.emit_yaml(state)
        legacy_text = "\n".join(
            line for line in text.splitlines()
            if not line.startswith("claude_effort_security:")
        ) + "\n"
        self.assertNotIn("claude_effort_security:", legacy_text)
        self.assertIn("claude_tier_security: opus", legacy_text)

        yaml_path = self.devforge_dir / configure_helper.OUTPUT_FILE_NAME
        yaml_path.write_text(legacy_text, encoding="utf-8")

        state2 = _load(self.devforge_dir)
        self.assertEqual(state2["claude_effort_security"], "default")
        self.assertEqual(state2["claude_tier_security"], "opus")


class TierSecurityVerifyTests(_EnvIsolationMixin, unittest.TestCase):
    """configure_helper verify's behavior for claude_tier_security --
    proven, not assumed, against the REAL subprocess: it mirrors
    claude_tier_verify's CONFIRMED current behavior exactly (no
    _cmds_verify.py exemption was added for either), so an unset
    claude_tier_security is a violation (exit 2), the same as an unset
    claude_tier_verify today."""

    def _populate_everything_except_claude_tier_security(self):
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
        # claude_tier_security deliberately left unset -- this class's
        # whole point.

    def test_verify_exits_2_when_claude_tier_security_unset(self):
        self._populate_everything_except_claude_tier_security()
        _run_configure(self.devforge_dir, "render-config")
        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"CLAUDE_TIER_SECURITY", proc.stderr)
        self.assertIn(b"is null", proc.stderr)

    def test_verify_exits_0_once_claude_tier_security_is_set(self):
        """Same fixture as the exit-2 case, plus the one missing setter
        call -- proves the exit 2 above is caused SPECIFICALLY by the
        unset tier, not by anything else in the fixture."""
        self._populate_everything_except_claude_tier_security()
        _run_configure(self.devforge_dir, "set-claude-tier-security", "opus")
        _run_configure(self.devforge_dir, "render-config")
        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn(b"verify: ok", proc.stderr)


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

    def test_security_pair_rendered_under_preferences_group(self):
        """claude_tier_security / claude_effort_security (plan 94 D3)
        render in the 'Preferences' group, directly after their
        respective claude_tier_verify / claude_effort_verify siblings."""
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-claude-tier-security", "opus")
        _run_configure(self.devforge_dir, "set-claude-effort-security", "high")
        proc = _run_configure(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        out = proc.stdout.decode()
        prefs_section = out.split("### Preferences", 1)[1].split("### ", 1)[0]
        self.assertIn("claude_tier_security", prefs_section)
        self.assertIn("opus", prefs_section)
        self.assertIn("claude_effort_security", prefs_section)
        self.assertIn("high", prefs_section)
        # Ordering: claude_tier_security directly after claude_tier_verify,
        # claude_effort_security directly after claude_effort_verify.
        tier_idx = prefs_section.index("claude_tier_verify")
        tier_security_idx = prefs_section.index("claude_tier_security")
        effort_idx = prefs_section.index("claude_effort_verify")
        effort_security_idx = prefs_section.index("claude_effort_security")
        self.assertLess(tier_idx, tier_security_idx)
        self.assertLess(effort_idx, effort_security_idx)


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

    # -- claude_tier_security (plan 94 D3) -- same _cmd_set_claude_tier
    # shared implementation as the four cases above, exercised through
    # the fourth tier's own CLI verb.

    def test_opus_normalized_to_lowercase_for_security_tier(self):
        proc = _run_configure(self.devforge_dir, "set-claude-tier-security", "Opus")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["claude_tier_security"], "opus")

    def test_fable_uppercase_normalized_to_lowercase_for_security_tier(self):
        proc = _run_configure(self.devforge_dir, "set-claude-tier-security", "FABLE")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["claude_tier_security"], "fable")

    def test_bedrock_route_pin_stored_unchanged_for_security_tier(self):
        proc = _run_configure(
            self.devforge_dir, "set-claude-tier-security", "my-bedrock-route"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["claude_tier_security"], "my-bedrock-route")

    def test_empty_value_still_rejected_for_security_tier(self):
        proc = _run_configure(self.devforge_dir, "set-claude-tier-security", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"claude_tier_security", proc.stderr)


if __name__ == "__main__":
    unittest.main()
