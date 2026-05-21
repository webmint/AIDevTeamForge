"""Tests for _constitute._forcing_functions._setters.

Tests round-trip via the real config writer + reader (no hand-authored
fixtures), confirming that what is written can be read back by the
existing detector command patterns.

Coverage
--------
test_set_magic_enum_creates_config
    New file created with magic_enum_duplication block.
test_set_magic_enum_merges_existing_keys
    Existing unrelated keys preserved on update.
test_set_magic_enum_preserves_other_rules
    Other rules in forcing_functions are not overwritten.
test_set_magic_enum_enabled_false_does_not_require_dirs
    Disabling does not require generated_types_dirs.
test_set_magic_enum_enabled_true_requires_dirs
    enabling without dirs raises ValueError.
test_set_cross_layer_creates_config
    New cross_layer_imports block written correctly.
test_set_cross_layer_enabled_true_requires_both_maps
    enabling without layer_graph raises ValueError.
test_set_cross_layer_mismatched_keys_raises
    layer_graph and layer_dirs key mismatch raises ValueError.
test_set_any_leak_creates_config
    any_with_generated_available block written correctly.
test_set_any_leak_enabled_true_requires_dirs
    enabling without dirs raises ValueError.
test_unknown_rule_raises
    Unknown rule name raises ValueError (never writes).
test_atomic_write_leaves_no_temp_on_success
    No *.tmp files left after successful write.
test_existing_malformed_json_raises
    JSONDecodeError propagated when existing config is malformed.
test_round_trip_via_magic_enum_cmd
    Written config is correctly consumed by cmd_verify_magic_enum
    (real producer round-trip per feedback_test_first_python_helpers.md).
test_round_trip_via_cross_layer_cmd
    Written config is correctly consumed by cmd_verify_cross_layer_imports.
test_round_trip_via_any_leak_cmd
    Written config is correctly consumed by cmd_verify_any_leak.
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

from _constitute._forcing_functions._setters import (  # noqa: E402
    KNOWN_RULES,
    set_forcing_function,
)
from _constitute._cli import main as cli_main  # noqa: E402


def _run_cli(argv: list) -> tuple:
    """Return (exit_code, stdout_str, stderr_str)."""
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        code = cli_main(argv)
        out = sys.stdout.getvalue()
        err = sys.stderr.getvalue()
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
    return code, out, err


class TestSetMagicEnum(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.config_path = Path(self._td) / "constitute.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_set_magic_enum_creates_config(self):
        set_forcing_function(
            self.config_path,
            "magic_enum_duplication",
            True,
            generated_types_dirs=["packages/types/src"],
        )
        self.assertTrue(self.config_path.exists())
        data = json.loads(self.config_path.read_text())
        ff = data["forcing_functions"]["magic_enum_duplication"]
        self.assertTrue(ff["enabled"])
        self.assertEqual(ff["generated_types_dirs"], ["packages/types/src"])

    def test_set_magic_enum_merges_existing_keys(self):
        # Pre-populate with a known allowlist_paths
        initial = {
            "project_name": "test-project",
            "forcing_functions": {
                "magic_enum_duplication": {
                    "enabled": True,
                    "generated_types_dirs": ["old/path"],
                    "allowlist_paths": ["scripts/**"],
                }
            },
        }
        self.config_path.write_text(json.dumps(initial))
        # Update only generated_types_dirs; allowlist_paths should be preserved
        set_forcing_function(
            self.config_path,
            "magic_enum_duplication",
            True,
            generated_types_dirs=["new/path"],
        )
        data = json.loads(self.config_path.read_text())
        # project_name preserved
        self.assertEqual(data["project_name"], "test-project")
        ff = data["forcing_functions"]["magic_enum_duplication"]
        self.assertEqual(ff["generated_types_dirs"], ["new/path"])
        # allowlist_paths preserved from previous config (caller did not supply it)
        self.assertEqual(ff["allowlist_paths"], ["scripts/**"])

    def test_set_magic_enum_preserves_other_rules(self):
        initial = {
            "forcing_functions": {
                "any_with_generated_available": {
                    "enabled": False,
                    "generated_types_dirs": ["types/src"],
                }
            }
        }
        self.config_path.write_text(json.dumps(initial))
        set_forcing_function(
            self.config_path,
            "magic_enum_duplication",
            True,
            generated_types_dirs=["packages/types/src"],
        )
        data = json.loads(self.config_path.read_text())
        # Other rule still present
        self.assertIn("any_with_generated_available", data["forcing_functions"])
        self.assertIn("magic_enum_duplication", data["forcing_functions"])

    def test_set_magic_enum_enabled_false_does_not_require_dirs(self):
        # Should not raise even without generated_types_dirs
        set_forcing_function(
            self.config_path,
            "magic_enum_duplication",
            False,
        )
        data = json.loads(self.config_path.read_text())
        ff = data["forcing_functions"]["magic_enum_duplication"]
        self.assertFalse(ff["enabled"])

    def test_set_magic_enum_enabled_true_requires_dirs(self):
        with self.assertRaises(ValueError) as ctx:
            set_forcing_function(
                self.config_path,
                "magic_enum_duplication",
                True,
                # no generated_types_dirs
            )
        self.assertIn("generated_types_dirs", str(ctx.exception))
        # File must NOT be created when validation fails
        self.assertFalse(self.config_path.exists())

    def test_set_magic_enum_enabled_true_requires_nonempty_dirs(self):
        with self.assertRaises(ValueError):
            set_forcing_function(
                self.config_path,
                "magic_enum_duplication",
                True,
                generated_types_dirs=[],
            )
        self.assertFalse(self.config_path.exists())

    def test_set_allowlist_paths_written(self):
        set_forcing_function(
            self.config_path,
            "magic_enum_duplication",
            True,
            generated_types_dirs=["types/src"],
            allowlist_paths=["scripts/**", "*.fixture.ts"],
        )
        data = json.loads(self.config_path.read_text())
        ff = data["forcing_functions"]["magic_enum_duplication"]
        self.assertEqual(ff["allowlist_paths"], ["scripts/**", "*.fixture.ts"])


class TestSetCrossLayer(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.config_path = Path(self._td) / "constitute.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def _layer_graph(self):
        return {"domain": [], "infra": ["domain"], "ui": ["domain", "infra"]}

    def _layer_dirs(self):
        return {
            "domain": "packages/*/domain/**",
            "infra": "packages/*/infra/**",
            "ui": "packages/*/ui/**",
        }

    def test_set_cross_layer_creates_config(self):
        set_forcing_function(
            self.config_path,
            "cross_layer_imports",
            True,
            layer_graph=self._layer_graph(),
            layer_dirs=self._layer_dirs(),
        )
        data = json.loads(self.config_path.read_text())
        ff = data["forcing_functions"]["cross_layer_imports"]
        self.assertTrue(ff["enabled"])
        self.assertEqual(ff["layer_graph"]["infra"], ["domain"])
        self.assertEqual(ff["layer_dirs"]["domain"], "packages/*/domain/**")

    def test_set_cross_layer_enabled_true_requires_layer_graph(self):
        with self.assertRaises(ValueError) as ctx:
            set_forcing_function(
                self.config_path,
                "cross_layer_imports",
                True,
                layer_dirs=self._layer_dirs(),
                # no layer_graph
            )
        self.assertIn("layer_graph", str(ctx.exception))
        self.assertFalse(self.config_path.exists())

    def test_set_cross_layer_enabled_true_requires_layer_dirs(self):
        with self.assertRaises(ValueError) as ctx:
            set_forcing_function(
                self.config_path,
                "cross_layer_imports",
                True,
                layer_graph=self._layer_graph(),
                # no layer_dirs
            )
        self.assertIn("layer_dirs", str(ctx.exception))
        self.assertFalse(self.config_path.exists())

    def test_set_cross_layer_mismatched_keys_raises(self):
        bad_dirs = {"domain": "packages/*/domain/**"}  # missing infra + ui
        with self.assertRaises(ValueError) as ctx:
            set_forcing_function(
                self.config_path,
                "cross_layer_imports",
                True,
                layer_graph=self._layer_graph(),
                layer_dirs=bad_dirs,
            )
        self.assertIn("keys must match", str(ctx.exception))
        self.assertFalse(self.config_path.exists())

    def test_set_cross_layer_enabled_false_no_required_fields(self):
        # Should not raise even without layer_graph / layer_dirs
        set_forcing_function(
            self.config_path,
            "cross_layer_imports",
            False,
        )
        data = json.loads(self.config_path.read_text())
        ff = data["forcing_functions"]["cross_layer_imports"]
        self.assertFalse(ff["enabled"])


class TestSetAnyLeak(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.config_path = Path(self._td) / "constitute.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_set_any_leak_creates_config(self):
        set_forcing_function(
            self.config_path,
            "any_with_generated_available",
            True,
            generated_types_dirs=["packages/types/src"],
        )
        data = json.loads(self.config_path.read_text())
        ff = data["forcing_functions"]["any_with_generated_available"]
        self.assertTrue(ff["enabled"])
        self.assertEqual(ff["generated_types_dirs"], ["packages/types/src"])

    def test_set_any_leak_enabled_true_requires_dirs(self):
        with self.assertRaises(ValueError) as ctx:
            set_forcing_function(
                self.config_path,
                "any_with_generated_available",
                True,
            )
        self.assertIn("generated_types_dirs", str(ctx.exception))
        self.assertFalse(self.config_path.exists())

    def test_set_any_leak_disabled_does_not_require_dirs(self):
        set_forcing_function(
            self.config_path,
            "any_with_generated_available",
            False,
        )
        data = json.loads(self.config_path.read_text())
        ff = data["forcing_functions"]["any_with_generated_available"]
        self.assertFalse(ff["enabled"])


class TestUnknownRule(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.config_path = Path(self._td) / "constitute.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_unknown_rule_raises(self):
        with self.assertRaises(ValueError) as ctx:
            set_forcing_function(
                self.config_path,
                "non_existent_rule",
                True,
            )
        self.assertIn("unknown rule", str(ctx.exception))
        self.assertFalse(self.config_path.exists())


class TestAtomicWrite(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.config_path = Path(self._td) / "constitute.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_no_temp_files_left_after_success(self):
        set_forcing_function(
            self.config_path,
            "magic_enum_duplication",
            True,
            generated_types_dirs=["types/src"],
        )
        tmp_files = list(Path(self._td).glob("*.tmp"))
        self.assertEqual(tmp_files, [], "Temp files should be cleaned up")


class TestExistingMalformedJson(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.config_path = Path(self._td) / "constitute.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_malformed_json_raises(self):
        self.config_path.write_text("{not: valid json")
        import json as _json
        with self.assertRaises(_json.JSONDecodeError):
            set_forcing_function(
                self.config_path,
                "magic_enum_duplication",
                True,
                generated_types_dirs=["types/src"],
            )


class TestReEnableRequiresDirsAgain(unittest.TestCase):
    """F6: disabling a rule then re-enabling without dirs must raise ValueError."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.config_path = Path(self._td) / "constitute.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_reenable_requires_dirs_again(self):
        # Step 1: configure rule enabled with dirs
        set_forcing_function(
            self.config_path,
            "magic_enum_duplication",
            True,
            generated_types_dirs=["types/src"],
        )
        # Step 2: disable without supplying dirs (allowed)
        set_forcing_function(
            self.config_path,
            "magic_enum_duplication",
            False,
        )
        # Step 3: re-enable without dirs — must raise; stored dirs are NOT used
        # because the merge happens AFTER validation, and validation runs on the
        # caller-supplied value (None), not the stored value.
        with self.assertRaises(ValueError) as ctx:
            set_forcing_function(
                self.config_path,
                "magic_enum_duplication",
                True,
                # no generated_types_dirs supplied
            )
        self.assertIn("generated_types_dirs", str(ctx.exception))


class TestRoundTripViaMagicEnumCmd(unittest.TestCase):
    """Real producer round-trip: set_forcing_function → cmd_verify_magic_enum."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.root = Path(self._td)
        self.devforge = self.root / ".devforge"
        self.config_path = self.devforge / "constitute.json"
        # Create a generated-types dir with an enum
        gen_dir = self.root / "types" / "src"
        gen_dir.mkdir(parents=True)
        (gen_dir / "index.d.ts").write_text(
            "export enum ShipStatus { Pending = 'PENDING', Shipped = 'SHIPPED' }\n"
        )
        # Source with a violation
        src_dir = self.root / "src"
        src_dir.mkdir()
        (src_dir / "main.ts").write_text(
            "const status = 'PENDING'; // magic string\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_written_config_consumed_by_verify_cmd(self):
        set_forcing_function(
            self.config_path,
            "magic_enum_duplication",
            True,
            generated_types_dirs=["types/src"],
        )
        # Round-trip: the detector should find the violation
        code, out, _err = _run_cli([
            "--devforge-dir", str(self.devforge),
            "verify-magic-enum",
            "--root", str(self.root),
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 2, "Should find violation with written config")
        # stdout should be valid JSON
        parsed = json.loads(out)
        self.assertEqual(parsed["rule"], "magic_enum_duplication")
        self.assertGreater(len(parsed["findings"]), 0)

    def test_disabled_config_exits_clean(self):
        set_forcing_function(
            self.config_path,
            "magic_enum_duplication",
            False,
        )
        code, _out, _err = _run_cli([
            "--devforge-dir", str(self.devforge),
            "verify-magic-enum",
            "--root", str(self.root),
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)


class TestRoundTripViaCrossLayerCmd(unittest.TestCase):
    """Real producer round-trip: set_forcing_function → cmd_verify_cross_layer_imports."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.root = Path(self._td)
        self.devforge = self.root / ".devforge"
        self.config_path = self.devforge / "constitute.json"

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_written_config_exits_clean_on_empty_source(self):
        set_forcing_function(
            self.config_path,
            "cross_layer_imports",
            True,
            layer_graph={"domain": [], "infra": ["domain"]},
            layer_dirs={
                "domain": "packages/domain/**",
                "infra": "packages/infra/**",
            },
        )
        code, _out, _err = _run_cli([
            "--devforge-dir", str(self.devforge),
            "verify-cross-layer-imports",
            "--root", str(self.root),
            "--config", str(self.config_path),
        ])
        # No source files = no violations
        self.assertEqual(code, 0)

    def test_disabled_cross_layer_config_exits_clean(self):
        set_forcing_function(
            self.config_path,
            "cross_layer_imports",
            False,
        )
        code, _out, _err = _run_cli([
            "--devforge-dir", str(self.devforge),
            "verify-cross-layer-imports",
            "--root", str(self.root),
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)


class TestRoundTripViaAnyLeakCmd(unittest.TestCase):
    """Real producer round-trip: set_forcing_function → cmd_verify_any_leak."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self.root = Path(self._td)
        self.devforge = self.root / ".devforge"
        self.config_path = self.devforge / "constitute.json"
        # Gen dir and importing source
        gen_dir = self.root / "types" / "src"
        gen_dir.mkdir(parents=True)
        (gen_dir / "index.ts").write_text("export type Foo = { x: string }\n")
        src_dir = self.root / "src"
        src_dir.mkdir()
        (src_dir / "service.ts").write_text(
            "import { Foo } from '../types/src';\n"
            "function process(item: any): void {}\n"
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_written_config_consumed_by_verify_cmd(self):
        set_forcing_function(
            self.config_path,
            "any_with_generated_available",
            True,
            generated_types_dirs=["types/src"],
        )
        code, out, _err = _run_cli([
            "--devforge-dir", str(self.devforge),
            "verify-any-leak",
            "--root", str(self.root),
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 2, "Should find any leak with written config")
        parsed = json.loads(out)
        self.assertEqual(parsed["rule"], "any_with_generated_available")

    def test_disabled_any_leak_exits_clean(self):
        set_forcing_function(
            self.config_path,
            "any_with_generated_available",
            False,
        )
        code, _out, _err = _run_cli([
            "--devforge-dir", str(self.devforge),
            "verify-any-leak",
            "--root", str(self.root),
            "--config", str(self.config_path),
        ])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
