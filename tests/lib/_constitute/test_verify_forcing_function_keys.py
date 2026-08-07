"""Tests for cmd_verify_forcing_function_keys in _constitute._cmds_quality.

Fixtures are built via the REAL producer (set_forcing_function from _setters)
so the constitute.json shape is exactly what the CLI setter writes, not a
hand-authored approximation.

Coverage
--------
test_all_rules_present_exit_0      -- all FORCING_FUNCTION_RULES keys present → exit 0
test_one_rule_missing_exit_2       -- drop design_token_provenance → exit 2, rule in report
test_forcing_functions_none_exit_2 -- forcing_functions field is null → exit 2, all missing
test_forcing_functions_absent_exit_2 -- forcing_functions key absent → exit 2, all missing
test_no_constitute_json_exit_3     -- .devforge/constitute.json absent → exit 3
test_corrupt_json_exit_1           -- constitute.json present but bad JSON → exit 1
test_stdout_json_structure_exit_0  -- stdout is valid JSON with correct keys on exit 0
test_stdout_json_structure_exit_2  -- stdout is valid JSON with missing_rules on exit 2
test_stderr_missing_lines_exit_2   -- stderr carries one line per missing rule
test_stderr_note_exit_3            -- stderr carries note on exit 3
test_no_extra_rules_reported       -- extra consumer keys never appear in missing_rules
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_LIB_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "src", "devforge", "lib"
)
if _LIB_ROOT not in sys.path:
    sys.path.insert(0, _LIB_ROOT)

from _constitute._cli import main  # noqa: E402
from _constitute._schema import FORCING_FUNCTION_RULES  # noqa: E402
from _constitute._forcing_functions._setters import set_forcing_function  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_cli(argv):
    """Return (exit_code, stdout_str, stderr_str) from main()."""
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        code = main(argv)
        out = sys.stdout.getvalue()
        err = sys.stderr.getvalue()
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
    return code, out, err


def _run_verb(consumer_path):
    """Run forge-internal:verify-forcing-function-keys --consumer-path <path>."""
    return _run_cli([
        "forge-internal:verify-forcing-function-keys",
        "--consumer-path", str(consumer_path),
    ])


def _write_all_rules(devforge_dir):
    """Write every rule in FORCING_FUNCTION_RULES to constitute.json via the
    real setter so the fixture is producer-canonical.

    Uses enabled=False for every rule; this avoids required-field constraints
    (dirs, layer_graph, etc.) while still writing the key, which is all the
    verb cares about.
    """
    config_path = Path(devforge_dir) / "constitute.json"
    for rule in sorted(FORCING_FUNCTION_RULES):
        set_forcing_function(config_path, rule, enabled=False)
    return config_path


def _drop_rule_from_config(config_path, rule_to_drop):
    """Read the config, remove rule_to_drop from forcing_functions, write back."""
    data = json.loads(config_path.read_text(encoding="utf-8"))
    if isinstance(data.get("forcing_functions"), dict):
        data["forcing_functions"].pop(rule_to_drop, None)
    config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestAllRulesPresent(unittest.TestCase):
    """Exit 0 when constitute.json exists and has all schema rule keys."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.devforge_dir = Path(self._td) / ".devforge"
        self.devforge_dir.mkdir()
        _write_all_rules(self.devforge_dir)
        self.consumer_root = Path(self._td)

    def tearDown(self):
        shutil.rmtree(self._td, ignore_errors=True)

    def test_all_rules_present_exit_0(self):
        code, out, _err = _run_verb(self.consumer_root)
        self.assertEqual(code, 0)

    def test_stdout_json_structure_exit_0(self):
        code, out, _err = _run_verb(self.consumer_root)
        self.assertEqual(code, 0)
        report = json.loads(out)
        self.assertIn("consumer", report)
        self.assertIn("missing_rules", report)
        self.assertIn("schema_rules", report)
        self.assertEqual(report["missing_rules"], [])
        self.assertEqual(sorted(report["schema_rules"]), sorted(FORCING_FUNCTION_RULES))


class TestOneRuleMissing(unittest.TestCase):
    """Exit 2 when exactly one schema rule is absent — the real-consumer reproduction."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.devforge_dir = Path(self._td) / ".devforge"
        self.devforge_dir.mkdir()
        config_path = _write_all_rules(self.devforge_dir)
        # Drop design_token_provenance — the exact rule the consumer scenario lacked.
        _drop_rule_from_config(config_path, "design_token_provenance")
        self.consumer_root = Path(self._td)

    def tearDown(self):
        shutil.rmtree(self._td, ignore_errors=True)

    def test_one_rule_missing_exit_2(self):
        code, _out, _err = _run_verb(self.consumer_root)
        self.assertEqual(code, 2)

    def test_stdout_json_structure_exit_2(self):
        _code, out, _err = _run_verb(self.consumer_root)
        report = json.loads(out)
        self.assertEqual(report["missing_rules"], ["design_token_provenance"])

    def test_stderr_missing_lines_exit_2(self):
        _code, _out, err = _run_verb(self.consumer_root)
        self.assertIn("MISSING forcing-function rule: design_token_provenance", err)
        # Only the one missing rule is reported on stderr.
        self.assertEqual(
            err.count("MISSING forcing-function rule:"), 1,
            "Expected exactly 1 MISSING line; got: " + repr(err),
        )


class TestForcingFunctionsNullValue(unittest.TestCase):
    """forcing_functions present but null → all rules missing → exit 2."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.devforge_dir = Path(self._td) / ".devforge"
        self.devforge_dir.mkdir()
        config_path = self.devforge_dir / "constitute.json"
        data = {"project_name": "test-project", "forcing_functions": None}
        config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        self.consumer_root = Path(self._td)

    def tearDown(self):
        shutil.rmtree(self._td, ignore_errors=True)

    def test_forcing_functions_none_exit_2(self):
        code, out, err = _run_verb(self.consumer_root)
        self.assertEqual(code, 2)
        report = json.loads(out)
        # All schema rules should be listed as missing.
        self.assertEqual(
            sorted(report["missing_rules"]),
            sorted(FORCING_FUNCTION_RULES),
        )
        # One stderr line per missing rule.
        self.assertEqual(
            err.count("MISSING forcing-function rule:"),
            len(FORCING_FUNCTION_RULES),
        )


class TestForcingFunctionsKeyAbsent(unittest.TestCase):
    """forcing_functions key absent entirely → all rules missing → exit 2."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.devforge_dir = Path(self._td) / ".devforge"
        self.devforge_dir.mkdir()
        config_path = self.devforge_dir / "constitute.json"
        # Write a constitute.json with NO forcing_functions key at all.
        data = {"project_name": "test-project", "mode": "existing-codebase"}
        config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        self.consumer_root = Path(self._td)

    def tearDown(self):
        shutil.rmtree(self._td, ignore_errors=True)

    def test_forcing_functions_absent_exit_2(self):
        code, out, err = _run_verb(self.consumer_root)
        self.assertEqual(code, 2)
        report = json.loads(out)
        self.assertEqual(
            sorted(report["missing_rules"]),
            sorted(FORCING_FUNCTION_RULES),
        )


class TestConstitueJsonAbsent(unittest.TestCase):
    """No .devforge/constitute.json → exit 3."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.consumer_root = Path(self._td)
        # Deliberately do NOT create .devforge/ or constitute.json.

    def tearDown(self):
        shutil.rmtree(self._td, ignore_errors=True)

    def test_no_constitute_json_exit_3(self):
        code, _out, err = _run_verb(self.consumer_root)
        self.assertEqual(code, 3)
        self.assertIn("not found", err)

    def test_stderr_note_exit_3(self):
        _code, _out, err = _run_verb(self.consumer_root)
        self.assertIn("verify-forcing-function-keys", err)
        self.assertIn("constitute.json", err)


class TestConstitueJsonCorrupt(unittest.TestCase):
    """constitute.json present but unparseable JSON → exit 1."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.devforge_dir = Path(self._td) / ".devforge"
        self.devforge_dir.mkdir()
        config_path = self.devforge_dir / "constitute.json"
        config_path.write_text("{ this is NOT valid json }", encoding="utf-8")
        self.consumer_root = Path(self._td)

    def tearDown(self):
        shutil.rmtree(self._td, ignore_errors=True)

    def test_corrupt_json_exit_1(self):
        code, _out, err = _run_verb(self.consumer_root)
        self.assertEqual(code, 1)
        self.assertIn("verify-forcing-function-keys", err)


class TestTopLevelNotDict(unittest.TestCase):
    """constitute.json parses as valid JSON but top-level value is not a dict → exit 1."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.devforge_dir = Path(self._td) / ".devforge"
        self.devforge_dir.mkdir()
        config_path = self.devforge_dir / "constitute.json"
        # Valid JSON, but a list not a dict — wrong shape.
        config_path.write_text("[1, 2, 3]\n", encoding="utf-8")
        self.consumer_root = Path(self._td)

    def tearDown(self):
        shutil.rmtree(self._td, ignore_errors=True)

    def test_top_level_not_dict_exit_1(self):
        code, _out, err = _run_verb(self.consumer_root)
        self.assertEqual(code, 1)
        self.assertIn("verify-forcing-function-keys", err)
        self.assertIn("expected dict", err)


class TestNoExtraRulesReported(unittest.TestCase):
    """Extra/unknown consumer keys do NOT appear in missing_rules."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.devforge_dir = Path(self._td) / ".devforge"
        self.devforge_dir.mkdir()
        config_path = _write_all_rules(self.devforge_dir)
        # Inject a future/unknown rule key alongside all known rules.
        data = json.loads(config_path.read_text(encoding="utf-8"))
        data["forcing_functions"]["future_detector_v99"] = {"enabled": False}
        config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        self.consumer_root = Path(self._td)

    def tearDown(self):
        shutil.rmtree(self._td, ignore_errors=True)

    def test_no_extra_rules_reported(self):
        code, out, _err = _run_verb(self.consumer_root)
        # All schema rules ARE present, so exit 0.
        self.assertEqual(code, 0)
        report = json.loads(out)
        # future_detector_v99 must NOT be in missing_rules (it's not in the schema).
        self.assertNotIn("future_detector_v99", report["missing_rules"])
        # missing_rules is empty.
        self.assertEqual(report["missing_rules"], [])


class TestSchemaRulesInReport(unittest.TestCase):
    """schema_rules in the JSON report always reflects FORCING_FUNCTION_RULES."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.devforge_dir = Path(self._td) / ".devforge"
        self.devforge_dir.mkdir()
        _write_all_rules(self.devforge_dir)
        self.consumer_root = Path(self._td)

    def tearDown(self):
        shutil.rmtree(self._td, ignore_errors=True)

    def test_schema_rules_matches_frozenset(self):
        _code, out, _err = _run_verb(self.consumer_root)
        report = json.loads(out)
        self.assertEqual(
            set(report["schema_rules"]),
            set(FORCING_FUNCTION_RULES),
        )

    def test_schema_rules_is_sorted(self):
        _code, out, _err = _run_verb(self.consumer_root)
        report = json.loads(out)
        self.assertEqual(report["schema_rules"], sorted(report["schema_rules"]))

    def test_missing_rules_is_sorted(self):
        # Drop two rules to have a non-trivial missing set.
        config_path = self.devforge_dir / "constitute.json"
        for rule in ["design_token_provenance", "magic_enum_duplication"]:
            _drop_rule_from_config(config_path, rule)
        _code, out, _err = _run_verb(self.consumer_root)
        report = json.loads(out)
        self.assertEqual(report["missing_rules"], sorted(report["missing_rules"]))


if __name__ == "__main__":
    unittest.main()
