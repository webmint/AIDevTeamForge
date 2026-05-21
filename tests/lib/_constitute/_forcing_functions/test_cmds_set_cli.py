"""End-to-end CLI tests for set-forcing-functions and list-forcing-functions.

Tests invoke via main() exactly as the constitute_helper shim would.

Coverage
--------
set-forcing-functions
  test_set_magic_enum_cli_creates_config        -- basic success path
  test_set_magic_enum_cli_disabled              -- --enabled false works
  test_set_magic_enum_cli_unknown_rule          -- exits 2 on bad rule
  test_set_magic_enum_cli_missing_dirs          -- exits 2 when dirs absent
  test_set_cross_layer_cli_creates_config       -- layer JSON args work
  test_set_cross_layer_cli_bad_json             -- exits 2 on bad JSON arg
  test_set_any_leak_cli_creates_config          -- any_leak success path
  test_help_works                               -- --help exits 0

list-forcing-functions
  test_list_no_config                           -- missing config → 0 lines
  test_list_all_rules                           -- all rules printed
  test_list_enabled_filter                      -- --enabled filters correctly
  test_list_exits_1_on_malformed_config         -- exits 1 on parse error
  test_list_empty_ff_block                      -- no forcing_functions → 0 lines
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_LIB_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "src", "devforge", "lib"
)
if _LIB_ROOT not in sys.path:
    sys.path.insert(0, _LIB_ROOT)

from _constitute._cli import main  # noqa: E402


def _run_cli(argv: list) -> tuple:
    """Return (exit_code, stdout_str, stderr_str)."""
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


class TestSetForcingFunctionsCLI(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.config_path = Path(self._td) / "constitute.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_set_magic_enum_cli_creates_config(self):
        code, _out, _err = _run_cli([
            "set-forcing-functions",
            "--rule", "magic_enum_duplication",
            "--enabled", "true",
            "--generated-types-dirs", "packages/types/src",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)
        self.assertTrue(self.config_path.exists())
        data = json.loads(self.config_path.read_text())
        ff = data["forcing_functions"]["magic_enum_duplication"]
        self.assertTrue(ff["enabled"])
        self.assertEqual(ff["generated_types_dirs"], ["packages/types/src"])

    def test_set_magic_enum_cli_with_allowlist(self):
        code, _out, _err = _run_cli([
            "set-forcing-functions",
            "--rule", "magic_enum_duplication",
            "--enabled", "true",
            "--generated-types-dirs", "types/src",
            "--allowlist-paths", "scripts/**,*.fixture.ts",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)
        data = json.loads(self.config_path.read_text())
        ff = data["forcing_functions"]["magic_enum_duplication"]
        self.assertEqual(ff["allowlist_paths"], ["scripts/**", "*.fixture.ts"])

    def test_set_magic_enum_cli_disabled(self):
        code, _out, _err = _run_cli([
            "set-forcing-functions",
            "--rule", "magic_enum_duplication",
            "--enabled", "false",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)
        data = json.loads(self.config_path.read_text())
        ff = data["forcing_functions"]["magic_enum_duplication"]
        self.assertFalse(ff["enabled"])

    def test_set_magic_enum_cli_missing_dirs_exits_2(self):
        code, _out, err = _run_cli([
            "set-forcing-functions",
            "--rule", "magic_enum_duplication",
            "--enabled", "true",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 2)
        self.assertIn("generated_types_dirs", err)
        # Config must NOT have been created
        self.assertFalse(self.config_path.exists())

    def test_set_unknown_rule_exits_2(self):
        # argparse choices= should reject unknown rules at the CLI level
        import argparse as _ap
        with self.assertRaises(SystemExit) as ctx:
            _run_cli([
                "set-forcing-functions",
                "--rule", "bad_rule",
                "--enabled", "true",
                "--config", str(self.config_path),
            ])
        self.assertEqual(ctx.exception.code, 2)

    def test_set_cross_layer_cli_creates_config(self):
        graph_json = json.dumps({"domain": [], "infra": ["domain"]})
        dirs_json = json.dumps({
            "domain": "packages/domain/**",
            "infra": "packages/infra/**",
        })
        code, _out, err = _run_cli([
            "set-forcing-functions",
            "--rule", "cross_layer_imports",
            "--enabled", "true",
            "--layer-graph-json", graph_json,
            "--layer-dirs-json", dirs_json,
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0, "stderr: " + err)
        data = json.loads(self.config_path.read_text())
        ff = data["forcing_functions"]["cross_layer_imports"]
        self.assertTrue(ff["enabled"])
        self.assertEqual(ff["layer_graph"]["infra"], ["domain"])

    def test_set_cross_layer_bad_json_exits_2(self):
        code, _out, err = _run_cli([
            "set-forcing-functions",
            "--rule", "cross_layer_imports",
            "--enabled", "true",
            "--layer-graph-json", "{not valid}",
            "--layer-dirs-json", "{}",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 2)
        self.assertIn("layer-graph-json", err.lower())

    def test_set_any_leak_cli_creates_config(self):
        code, _out, _err = _run_cli([
            "set-forcing-functions",
            "--rule", "any_with_generated_available",
            "--enabled", "true",
            "--generated-types-dirs", "types/src",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)
        data = json.loads(self.config_path.read_text())
        ff = data["forcing_functions"]["any_with_generated_available"]
        self.assertTrue(ff["enabled"])

    def test_set_forcing_functions_help(self):
        import argparse as _ap
        with self.assertRaises(SystemExit) as ctx:
            _run_cli(["set-forcing-functions", "--help"])
        self.assertEqual(ctx.exception.code, 0)


class TestListForcingFunctionsCLI(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.config_path = Path(self._td) / "constitute.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def _write_config(self, data: dict) -> None:
        self.config_path.write_text(json.dumps(data, indent=2))

    def test_list_no_config(self):
        code, out, _err = _run_cli([
            "list-forcing-functions",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_list_all_rules(self):
        self._write_config({
            "forcing_functions": {
                "magic_enum_duplication": {"enabled": True, "generated_types_dirs": ["t"]},
                "any_with_generated_available": {"enabled": False},
            }
        })
        code, out, _err = _run_cli([
            "list-forcing-functions",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)
        lines = out.strip().splitlines()
        self.assertIn("magic_enum_duplication", lines)
        self.assertIn("any_with_generated_available", lines)

    def test_list_enabled_filter(self):
        self._write_config({
            "forcing_functions": {
                "magic_enum_duplication": {"enabled": True, "generated_types_dirs": ["t"]},
                "any_with_generated_available": {"enabled": False},
                "cross_layer_imports": {"enabled": True,
                                        "layer_graph": {"domain": []},
                                        "layer_dirs": {"domain": "pkg/domain/**"}},
            }
        })
        code, out, _err = _run_cli([
            "list-forcing-functions",
            "--enabled",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)
        lines = out.strip().splitlines()
        self.assertIn("magic_enum_duplication", lines)
        self.assertIn("cross_layer_imports", lines)
        self.assertNotIn("any_with_generated_available", lines)

    def test_list_exits_1_on_malformed_config(self):
        self.config_path.write_text("{bad json")
        code, _out, err = _run_cli([
            "list-forcing-functions",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 1)
        self.assertIn("cannot parse", err)

    def test_list_empty_ff_block(self):
        self._write_config({"project_name": "test", "forcing_functions": {}})
        code, out, _err = _run_cli([
            "list-forcing-functions",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_list_no_ff_key(self):
        self._write_config({"project_name": "test"})
        code, out, _err = _run_cli([
            "list-forcing-functions",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_list_help(self):
        import argparse as _ap
        with self.assertRaises(SystemExit) as ctx:
            _run_cli(["list-forcing-functions", "--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_list_enabled_with_no_enabled_rules(self):
        self._write_config({
            "forcing_functions": {
                "magic_enum_duplication": {"enabled": False},
            }
        })
        code, out, _err = _run_cli([
            "list-forcing-functions",
            "--enabled",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_list_format_key_is_default(self):
        """--format key (the default) outputs rule config keys."""
        self._write_config({
            "forcing_functions": {
                "magic_enum_duplication": {"enabled": True, "generated_types_dirs": ["t"]},
            }
        })
        code, out, _err = _run_cli([
            "list-forcing-functions",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)
        self.assertIn("magic_enum_duplication", out)
        # Must NOT contain the verb form
        self.assertNotIn("verify-magic-enum", out)

    def test_list_format_verb_outputs_verb_names(self):
        """--format verb outputs CLI verb names, not config keys."""
        self._write_config({
            "forcing_functions": {
                "magic_enum_duplication": {"enabled": True, "generated_types_dirs": ["t"]},
                "any_with_generated_available": {"enabled": True, "generated_types_dirs": ["t"]},
                "cross_layer_imports": {
                    "enabled": True,
                    "layer_graph": {"domain": []},
                    "layer_dirs": {"domain": "pkg/**"},
                },
            }
        })
        code, out, _err = _run_cli([
            "list-forcing-functions",
            "--format", "verb",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)
        lines = out.strip().splitlines()
        self.assertIn("verify-magic-enum", lines)
        self.assertIn("verify-any-leak", lines)
        self.assertIn("verify-cross-layer-imports", lines)
        # Must NOT contain raw key names
        self.assertNotIn("magic_enum_duplication", out)

    def test_list_format_verb_enabled_filter(self):
        """--format verb combined with --enabled filters correctly."""
        self._write_config({
            "forcing_functions": {
                "magic_enum_duplication": {"enabled": True, "generated_types_dirs": ["t"]},
                "any_with_generated_available": {"enabled": False},
            }
        })
        code, out, _err = _run_cli([
            "list-forcing-functions",
            "--enabled",
            "--format", "verb",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)
        lines = out.strip().splitlines()
        self.assertIn("verify-magic-enum", lines)
        self.assertNotIn("verify-any-leak", lines)

    def test_list_format_key_explicit(self):
        """--format key explicit is the same as default."""
        self._write_config({
            "forcing_functions": {
                "cross_layer_imports": {
                    "enabled": True,
                    "layer_graph": {"domain": []},
                    "layer_dirs": {"domain": "pkg/**"},
                },
            }
        })
        code, out, _err = _run_cli([
            "list-forcing-functions",
            "--format", "key",
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)
        self.assertIn("cross_layer_imports", out)
        self.assertNotIn("verify-cross-layer-imports", out)


if __name__ == "__main__":
    unittest.main()
