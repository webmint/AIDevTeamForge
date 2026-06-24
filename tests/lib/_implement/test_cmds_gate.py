"""Tests for src/devforge/lib/_implement/_cmds_gate.py.

Real-producer discipline: tests invoke the REAL constitute_helper verbs
(via subprocess) against seeded source directories.  No mocking of the
subprocess layer — past bugs in this codebase came from fixture gaps when
the real producer was bypassed.

Coverage:

  _load_constitute_json:
    - Missing file → returns ({}, None) -- treated as zero rules
    - Valid JSON → returns (data, None)
    - Malformed JSON → returns (None, error_msg)
    - Non-object JSON → returns (None, error_msg)

  _enabled_rules:
    - No forcing_functions block → empty list
    - Rule with enabled: true → included
    - Rule with enabled: false → excluded
    - Unknown rule key with enabled: true → error (non-zero) + stderr names it
    - Mixed enabled/disabled → only enabled ones returned
    - _get_rule_to_verb() covers exactly the 3 real rules

  cmd_run_forcing_functions_gate (integration, real constitute_helper):
    - Both rules disabled → exit 0, empty rules_run
    - No forcing_functions block → exit 0, empty rules_run
    - One rule enabled, clean source → exit 0, rules_run=[verb], rules_failed=[]
    - One rule enabled, violation source → exit 2, rules_failed=[verb], reports has JSON
    - Two rules enabled: one clean, one violation → exit 2, rules_failed=[failer]
    - Two rules enabled, both clean → exit 0, empty rules_failed
    - Missing constitute.json (no .devforge dir) → exit 0, empty report
    - --config explicit path overrides default location
    - Enabled unknown rule key → exit EXIT_FINDINGS + stderr names the rule

  _run_verify_verb crash coverage:
    - Verb exits EXIT_ERR (non-0, non-2) → aggregate_exit = EXIT_FINDINGS,
      rule appears in rules_failed

  CLI wiring:
    - 'run-forcing-functions-gate --help' exits 0

Setup:
  - Uses real constitute.json written by hand (shape confirmed from _setters.py).
  - Source files seeded to produce clean/violation states for
    verify-magic-enum and verify-any-leak.
  - verify-magic-enum setup: generated_types_dirs + source file; violation =
    magic string matching a generated union value.
  - verify-any-leak setup: generated_types_dirs + qualifying import + ': any'
    in source; violation = any-typed binding in a qualifying file.

Stdlib only.  Python 3.8+.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Path bootstrap: make _implement importable.
# ---------------------------------------------------------------------------
_LIB_DIR = str(Path(__file__).resolve().parents[3] / "src" / "devforge" / "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _implement._cmds_gate import (  # noqa: E402
    _load_constitute_json,
    _enabled_rules,
    _locate_constitute_helper,
    _get_rule_to_verb,
    _run_verify_verb,
    cmd_run_forcing_functions_gate,
    EXIT_OK,
    EXIT_FINDINGS,
    EXIT_ERR,
)

# ---------------------------------------------------------------------------
# Helper: locate constitute_helper.py for real subprocess invocations
# ---------------------------------------------------------------------------

_CONSTITUTE_HELPER_PY = str(
    Path(__file__).resolve().parents[3] / "src" / "devforge" / "lib" / "constitute_helper.py"
)


def _run_gate(root, config_path=None):
    # type: (str, object) -> tuple
    """Call cmd_run_forcing_functions_gate and return (exit_code, stdout_payload).

    stdout_payload is None when stdout is not valid JSON.
    """
    args = SimpleNamespace(root=root, config=config_path)
    stdout_buf = io.StringIO()
    with patch("sys.stdout", stdout_buf):
        rc = cmd_run_forcing_functions_gate(args)
    raw = stdout_buf.getvalue().strip()
    try:
        payload = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        payload = None
    return rc, payload


def _write_constitute_json(devforge_dir, forcing_functions_block):
    # type: (Path, dict) -> None
    """Write constitute.json with the given forcing_functions block."""
    devforge_dir.mkdir(parents=True, exist_ok=True)
    data = {"forcing_functions": forcing_functions_block}
    (devforge_dir / "constitute.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Source-seeding helpers (produce real violations / clean states)
# ---------------------------------------------------------------------------


def _seed_magic_enum_violation(root):
    # type: (Path) -> None
    """Seed a project with a magic-enum violation.

    Generated types dir has 'Color' type with 'RED' value.
    Source file uses the magic string 'RED' → violation.
    """
    gen_dir = root / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    (gen_dir / "index.ts").write_text(
        "export type Color = 'RED' | 'BLUE';\n", encoding="utf-8"
    )
    src_dir = root / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "widget.ts").write_text(
        "const x = 'RED';\n", encoding="utf-8"
    )


def _seed_magic_enum_clean(root):
    # type: (Path) -> None
    """Seed a project with no magic-enum violation.

    Generated types dir has 'Color' type. Source file does NOT use
    any matching magic string.
    """
    gen_dir = root / "generated"
    gen_dir.mkdir(parents=True, exist_ok=True)
    (gen_dir / "index.ts").write_text(
        "export type Color = 'RED' | 'BLUE';\n", encoding="utf-8"
    )
    src_dir = root / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "widget.ts").write_text(
        "const x = color;\n", encoding="utf-8"
    )


def _seed_any_leak_violation(root):
    # type: (Path) -> None
    """Seed a project with a verify-any-leak violation.

    Qualifying file (imports from generated_types_dirs) has ': any'.
    """
    gen_dir = root / "packages" / "types" / "src"
    gen_dir.mkdir(parents=True, exist_ok=True)
    # The generated types dir just needs to exist for the scanner.
    src_dir = root / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    qualifying_import = "import { Foo } from '../../packages/types/src/types';\n"
    (src_dir / "service.ts").write_text(
        qualifying_import + "const x: any = getValue();\n", encoding="utf-8"
    )


def _seed_any_leak_clean(root):
    # type: (Path) -> None
    """Seed a project with no verify-any-leak violation.

    No qualifying file has ': any'.
    """
    gen_dir = root / "packages" / "types" / "src"
    gen_dir.mkdir(parents=True, exist_ok=True)
    src_dir = root / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    qualifying_import = "import { Foo } from '../../packages/types/src/types';\n"
    (src_dir / "service.ts").write_text(
        qualifying_import + "const x: string = getValue();\n", encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Verify that our seeding actually produces the expected constitute_helper
# exit codes before we rely on them in the gate tests.
# ---------------------------------------------------------------------------


def _constitute_helper_exit(verb, root, config=None):
    # type: (str, str, object) -> int
    """Run constitute_helper <verb> --root <root> and return exit code."""
    cmd = [sys.executable, _CONSTITUTE_HELPER_PY, verb, "--root", root]
    if config:
        cmd += ["--config", config]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode


# ---------------------------------------------------------------------------
# Tests: _load_constitute_json (unit)
# ---------------------------------------------------------------------------


class TestLoadConstituteJson(unittest.TestCase):

    def test_missing_file_returns_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".devforge" / "constitute.json"
            data, err = _load_constitute_json(path)
            self.assertEqual(data, {})
            self.assertIsNone(err)

    def test_valid_json_returns_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "constitute.json"
            p.write_text(json.dumps({"forcing_functions": {}}), encoding="utf-8")
            data, err = _load_constitute_json(p)
            self.assertEqual(data, {"forcing_functions": {}})
            self.assertIsNone(err)

    def test_malformed_json_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "constitute.json"
            p.write_text("{invalid json", encoding="utf-8")
            data, err = _load_constitute_json(p)
            self.assertIsNone(data)
            self.assertIsNotNone(err)
            self.assertIn("malformed", err.lower())

    def test_non_object_json_returns_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "constitute.json"
            p.write_text("[1, 2, 3]", encoding="utf-8")
            data, err = _load_constitute_json(p)
            self.assertIsNone(data)
            self.assertIsNotNone(err)


# ---------------------------------------------------------------------------
# Tests: _enabled_rules (unit)
# ---------------------------------------------------------------------------


class TestEnabledRules(unittest.TestCase):

    def test_empty_dict_returns_empty(self):
        rule_keys, err = _enabled_rules({})
        self.assertEqual(rule_keys, [])
        self.assertIsNone(err)

    def test_enabled_true_rule_included(self):
        ff = {
            "magic_enum_duplication": {"enabled": True, "generated_types_dirs": ["x"]}
        }
        rule_keys, err = _enabled_rules(ff)
        self.assertIn("magic_enum_duplication", rule_keys)
        self.assertIsNone(err)

    def test_enabled_false_rule_excluded(self):
        ff = {
            "magic_enum_duplication": {"enabled": False, "generated_types_dirs": ["x"]}
        }
        rule_keys, err = _enabled_rules(ff)
        self.assertNotIn("magic_enum_duplication", rule_keys)
        self.assertIsNone(err)

    def test_unknown_rule_enabled_returns_error(self):
        """An enabled rule with no verb mapping → error (fail-closed, not silent skip)."""
        ff = {"future_rule_xyz": {"enabled": True}}
        rule_keys, err = _enabled_rules(ff)
        self.assertEqual(rule_keys, [])
        self.assertIsNotNone(err)
        self.assertIn("future_rule_xyz", err)

    def test_unknown_rule_disabled_is_ignored(self):
        """A disabled rule with no verb mapping → silently OK (disabled = no intent)."""
        ff = {"future_rule_xyz": {"enabled": False}}
        rule_keys, err = _enabled_rules(ff)
        self.assertEqual(rule_keys, [])
        self.assertIsNone(err)

    def test_mixed_enabled_disabled(self):
        ff = {
            "magic_enum_duplication": {"enabled": True, "generated_types_dirs": ["x"]},
            "any_with_generated_available": {"enabled": False},
        }
        rule_keys, err = _enabled_rules(ff)
        self.assertIn("magic_enum_duplication", rule_keys)
        self.assertNotIn("any_with_generated_available", rule_keys)
        self.assertIsNone(err)

    def test_non_dict_block_skipped(self):
        """A rule entry that is not a dict → skipped (defensive)."""
        ff = {"magic_enum_duplication": "not-a-dict"}
        rule_keys, err = _enabled_rules(ff)
        self.assertEqual(rule_keys, [])
        self.assertIsNone(err)


# ---------------------------------------------------------------------------
# Tests: _locate_constitute_helper (unit)
# ---------------------------------------------------------------------------


class TestLocateConstituteHelper(unittest.TestCase):

    def test_sibling_of_lib(self):
        """constitute_helper is a sibling of _implement's parent (lib dir)."""
        helper = _locate_constitute_helper()
        # Should be <lib_dir>/constitute_helper
        lib_dir = Path(_CONSTITUTE_HELPER_PY).parent
        self.assertEqual(helper, lib_dir / "constitute_helper")


class TestGetRuleToVerb(unittest.TestCase):
    """_get_rule_to_verb() imports the authoritative mapping from _setters."""

    def test_returns_dict(self):
        mapping = _get_rule_to_verb()
        self.assertIsInstance(mapping, dict)

    def test_covers_exactly_four_rules(self):
        """Exactly the 4 currently-defined rules are present — no more, no fewer.
        Updated from 3 when design_token_provenance was added in plan 40 Phase 4.
        """
        mapping = _get_rule_to_verb()
        expected_keys = {
            "magic_enum_duplication",
            "cross_layer_imports",
            "any_with_generated_available",
            "design_token_provenance",
        }
        self.assertEqual(set(mapping.keys()), expected_keys)

    def test_verbs_are_correct(self):
        mapping = _get_rule_to_verb()
        self.assertEqual(mapping["magic_enum_duplication"], "verify-magic-enum")
        self.assertEqual(mapping["cross_layer_imports"], "verify-cross-layer-imports")
        self.assertEqual(mapping["any_with_generated_available"], "verify-any-leak")

    def test_same_source_as_setters(self):
        """The returned dict is physically the same object as _setters.RULE_TO_VERB."""
        from _constitute._forcing_functions._setters import RULE_TO_VERB
        mapping = _get_rule_to_verb()
        self.assertIs(mapping, RULE_TO_VERB)


# ---------------------------------------------------------------------------
# Tests: cmd_run_forcing_functions_gate integration with REAL constitute_helper
# ---------------------------------------------------------------------------


class TestGateBothDisabled(unittest.TestCase):
    """Both rules disabled → exit 0, empty rules_run."""

    def test_both_disabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_constitute_json(
                root / ".devforge",
                {
                    "magic_enum_duplication": {
                        "enabled": False,
                        "generated_types_dirs": ["generated"],
                    },
                    "any_with_generated_available": {
                        "enabled": False,
                        "generated_types_dirs": ["packages/types/src"],
                    },
                },
            )
            rc, payload = _run_gate(tmp)
        self.assertEqual(rc, EXIT_OK)
        self.assertIsNotNone(payload)
        self.assertEqual(payload["gate"], "forcing_functions")
        self.assertEqual(payload["rules_run"], [])
        self.assertEqual(payload["rules_failed"], [])
        self.assertEqual(payload["aggregate_exit"], EXIT_OK)


class TestGateNoBlock(unittest.TestCase):
    """No forcing_functions block → exit 0, empty report."""

    def test_empty_constitute_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".devforge").mkdir()
            (root / ".devforge" / "constitute.json").write_text(
                json.dumps({"project_name": "test"}), encoding="utf-8"
            )
            rc, payload = _run_gate(tmp)
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["rules_run"], [])
        self.assertEqual(payload["rules_failed"], [])

    def test_missing_constitute_json(self):
        """No .devforge dir at all → treated as zero rules."""
        with tempfile.TemporaryDirectory() as tmp:
            rc, payload = _run_gate(tmp)
        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["rules_run"], [])
        self.assertEqual(payload["rules_failed"], [])


class TestGateOneRuleClean(unittest.TestCase):
    """One rule enabled, source is clean → exit 0."""

    def test_magic_enum_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_magic_enum_clean(root)
            _write_constitute_json(
                root / ".devforge",
                {
                    "magic_enum_duplication": {
                        "enabled": True,
                        "generated_types_dirs": ["generated"],
                    }
                },
            )
            # Verify the real constitute_helper agrees this is clean.
            real_rc = _constitute_helper_exit("verify-magic-enum", tmp)
            if real_rc != 0:
                self.fail(
                    "Seeded clean project produced a violation — seeding assumption "
                    "is wrong (real exit {0}). Fix the seed or the detector.".format(real_rc)
                )

            rc, payload = _run_gate(tmp)

        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["rules_run"], ["verify-magic-enum"])
        self.assertEqual(payload["rules_failed"], [])
        self.assertEqual(payload["aggregate_exit"], EXIT_OK)


class TestGateOneRuleViolation(unittest.TestCase):
    """One rule enabled, violation source → exit 2."""

    def test_magic_enum_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed_magic_enum_violation(root)
            _write_constitute_json(
                root / ".devforge",
                {
                    "magic_enum_duplication": {
                        "enabled": True,
                        "generated_types_dirs": ["generated"],
                    }
                },
            )
            # Verify the real constitute_helper exits 2 for this fixture.
            real_rc = _constitute_helper_exit("verify-magic-enum", tmp)
            if real_rc != 2:
                self.fail(
                    "Seeded violation project did NOT produce a violation — "
                    "seeding assumption is wrong (real exit {0}). "
                    "Fix the seed or the detector.".format(real_rc)
                )

            rc, payload = _run_gate(tmp)

        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertIn("verify-magic-enum", payload["rules_run"])
        self.assertIn("verify-magic-enum", payload["rules_failed"])
        # Report contains the stdout JSON from the verb.
        report_text = payload["reports"].get("verify-magic-enum", "")
        self.assertTrue(len(report_text) > 0, "report for failing rule should be non-empty")
        # Report stdout should be valid JSON from emit_findings.
        report_json = json.loads(report_text)
        self.assertEqual(report_json["rule"], "magic_enum_duplication")
        self.assertEqual(payload["aggregate_exit"], EXIT_FINDINGS)


class TestGateTwoRulesOnePasses(unittest.TestCase):
    """Two rules enabled: one passes, one fails → exit 2, only failer in rules_failed."""

    def test_magic_enum_passes_any_leak_fails(self):
        """
        magic_enum_duplication: clean source → verify-magic-enum passes (exit 0)
        any_with_generated_available: violation source → verify-any-leak fails (exit 2)
        Aggregate: exit 2; rules_failed = ['verify-any-leak']
        """
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            # Seed clean magic-enum source.
            _seed_magic_enum_clean(root)

            # Seed any-leak violation on top (qualifying import + : any).
            _seed_any_leak_violation(root)

            # Write constitute.json enabling both rules.
            _write_constitute_json(
                root / ".devforge",
                {
                    "magic_enum_duplication": {
                        "enabled": True,
                        "generated_types_dirs": ["generated"],
                    },
                    "any_with_generated_available": {
                        "enabled": True,
                        "generated_types_dirs": ["packages/types/src"],
                        "allowlist_paths": [
                            "node_modules/**", "**/node_modules/**",
                        ],
                    },
                },
            )

            # Verify seeding with the REAL produce before running the gate.
            magic_rc = _constitute_helper_exit("verify-magic-enum", tmp)
            any_rc = _constitute_helper_exit("verify-any-leak", tmp)

            if magic_rc != 0:
                self.fail(
                    "magic-enum seeded project is NOT clean (exit {0}). "
                    "Fix the seed or the detector.".format(magic_rc)
                )
            if any_rc != 2:
                self.fail(
                    "any-leak seeded project did NOT produce a violation (exit {0}). "
                    "Fix the seed or the detector.".format(any_rc)
                )

            rc, payload = _run_gate(tmp)

        self.assertEqual(rc, EXIT_FINDINGS)
        self.assertEqual(payload["aggregate_exit"], EXIT_FINDINGS)
        # Both rules ran.
        self.assertIn("verify-magic-enum", payload["rules_run"])
        self.assertIn("verify-any-leak", payload["rules_run"])
        # Only the failer is in rules_failed.
        self.assertNotIn("verify-magic-enum", payload["rules_failed"])
        self.assertIn("verify-any-leak", payload["rules_failed"])
        # Passing rule report may be empty (exit 0 = no stdout from emit_findings).
        # Failing rule report should contain JSON.
        any_report = payload["reports"].get("verify-any-leak", "")
        self.assertTrue(len(any_report) > 0)
        report_json = json.loads(any_report)
        self.assertEqual(report_json["rule"], "any_with_generated_available")


class TestGateTwoRulesBothPass(unittest.TestCase):
    """Two rules enabled, both clean → exit 0."""

    def test_both_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Seed both clean.
            _seed_magic_enum_clean(root)
            _seed_any_leak_clean(root)

            _write_constitute_json(
                root / ".devforge",
                {
                    "magic_enum_duplication": {
                        "enabled": True,
                        "generated_types_dirs": ["generated"],
                    },
                    "any_with_generated_available": {
                        "enabled": True,
                        "generated_types_dirs": ["packages/types/src"],
                        "allowlist_paths": [
                            "node_modules/**", "**/node_modules/**",
                        ],
                    },
                },
            )

            # Verify seeding with real producer.
            magic_rc = _constitute_helper_exit("verify-magic-enum", tmp)
            any_rc = _constitute_helper_exit("verify-any-leak", tmp)

            if magic_rc != 0:
                self.fail(
                    "magic-enum seeded clean project is NOT clean (exit {0}). "
                    "Fix the seed or the detector.".format(magic_rc)
                )
            if any_rc != 0:
                self.fail(
                    "any-leak seeded clean project is NOT clean (exit {0}). "
                    "Fix the seed or the detector.".format(any_rc)
                )

            rc, payload = _run_gate(tmp)

        self.assertEqual(rc, EXIT_OK)
        self.assertEqual(payload["rules_run"], ["verify-magic-enum", "verify-any-leak"])
        self.assertEqual(payload["rules_failed"], [])
        self.assertEqual(payload["aggregate_exit"], EXIT_OK)


class TestGateExplicitConfig(unittest.TestCase):
    """--config explicit path overrides default location."""

    def test_explicit_config_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Write constitute.json at a non-default location.
            custom_config = root / "custom_constitute.json"
            custom_data = {
                "forcing_functions": {
                    "magic_enum_duplication": {
                        "enabled": False,
                        "generated_types_dirs": ["generated"],
                    }
                }
            }
            custom_config.write_text(json.dumps(custom_data, indent=2), encoding="utf-8")
            # Do NOT create .devforge/constitute.json.

            rc, payload = _run_gate(tmp, config_path=str(custom_config))

        self.assertEqual(rc, EXIT_OK)
        # Rule is disabled → zero rules_run.
        self.assertEqual(payload["rules_run"], [])


# ---------------------------------------------------------------------------
# Tests: unknown-rule-enabled → gate errors (integration of F1b)
# ---------------------------------------------------------------------------


class TestGateUnknownRuleEnabled(unittest.TestCase):
    """An enabled rule key not in RULE_TO_VERB → gate returns EXIT_FINDINGS + stderr."""

    def test_unknown_rule_key_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_constitute_json(
                root / ".devforge",
                {
                    "future_unknown_rule": {
                        "enabled": True,
                    }
                },
            )
            args = SimpleNamespace(root=tmp, config=None)
            stderr_buf = io.StringIO()
            stdout_buf = io.StringIO()
            with patch("sys.stderr", stderr_buf), patch("sys.stdout", stdout_buf):
                rc = cmd_run_forcing_functions_gate(args)

        self.assertEqual(rc, EXIT_FINDINGS)
        # stdout should be empty — no JSON payload on error
        self.assertEqual(stdout_buf.getvalue().strip(), "")
        # stderr should name the unknown rule
        self.assertIn("future_unknown_rule", stderr_buf.getvalue())


# ---------------------------------------------------------------------------
# Tests: _run_verify_verb crash coverage (F4)
# ---------------------------------------------------------------------------


class TestRunVerifyVerbCrashExit(unittest.TestCase):
    """Verb exiting EXIT_ERR (non-0, non-2) propagates as a gate failure."""

    def test_verb_exit_err_treated_as_failure(self):
        """Patch _run_verify_verb to return EXIT_ERR → aggregate_exit = EXIT_FINDINGS."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_constitute_json(
                root / ".devforge",
                {
                    "magic_enum_duplication": {
                        "enabled": True,
                        "generated_types_dirs": ["generated"],
                    }
                },
            )
            args = SimpleNamespace(root=tmp, config=None)
            stdout_buf = io.StringIO()

            # Patch _run_verify_verb inside the gate module to simulate a verb crash.
            with patch(
                "_implement._cmds_gate._run_verify_verb",
                return_value=(EXIT_ERR, ""),
            ), patch("sys.stdout", stdout_buf):
                rc = cmd_run_forcing_functions_gate(args)

        self.assertEqual(rc, EXIT_FINDINGS)
        raw = stdout_buf.getvalue().strip()
        payload = json.loads(raw)
        self.assertEqual(payload["aggregate_exit"], EXIT_FINDINGS)
        self.assertIn("verify-magic-enum", payload["rules_failed"])


# ---------------------------------------------------------------------------
# Tests: CLI wiring (verb registered in _cli.py)
# ---------------------------------------------------------------------------


class TestCliWiring(unittest.TestCase):

    def test_help_exits_zero(self):
        """implement_helper.py run-forcing-functions-gate --help exits 0."""
        helper_py = str(
            Path(__file__).resolve().parents[3]
            / "src"
            / "devforge"
            / "lib"
            / "implement_helper.py"
        )
        result = subprocess.run(
            [sys.executable, helper_py, "run-forcing-functions-gate", "--help"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("forcing", result.stdout.lower())


if __name__ == "__main__":
    unittest.main()
