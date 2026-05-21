"""End-to-end tests for the ``verify-magic-enum`` subcommand (Phase 1).

Tests exercise the full CLI path via the ``main()`` function in
``_constitute._cli``, which mirrors what the ``constitute_helper`` shim does.
Stdout and stderr are captured via io.StringIO redirection.

Coverage
--------
test_cmd_exits_0_when_config_missing         -- no constitute.json -> exit 0
test_cmd_exits_0_when_disabled               -- enabled: false -> exit 0
test_cmd_exits_0_when_ff_block_absent        -- no forcing_functions key -> exit 0
test_cmd_exits_0_when_rule_block_absent      -- forcing_functions but no magic_enum key -> exit 0
test_cmd_exits_2_with_violations             -- full setup, violation exists -> exit 2
test_cmd_stdout_is_valid_json_on_violations  -- stdout JSON shape when exit 2
test_cmd_stderr_cites_violation              -- stderr line mentions the violation
test_cmd_exits_0_on_clean_source            -- valid config, no violations in source
test_cmd_help_works                          -- --help returns exit 0
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_LIB_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "src", "devforge", "lib")
if _LIB_ROOT not in sys.path:
    sys.path.insert(0, _LIB_ROOT)

from _constitute._cli import main  # noqa: E402


# ---------------------------------------------------------------------------
# Helper: build a minimal constitute.json with forcing_functions block
# ---------------------------------------------------------------------------

def _write_config(
    devforge_dir: Path,
    enabled: bool,
    generated_dirs: list,
    allowlist_paths: list = None,
) -> None:
    """Write a constitute.json with the magic_enum_duplication block."""
    devforge_dir.mkdir(parents=True, exist_ok=True)
    cfg = {
        "forcing_functions": {
            "magic_enum_duplication": {
                "enabled": enabled,
                "generated_types_dirs": generated_dirs,
                "allowlist_paths": allowlist_paths or [],
            }
        }
    }
    (devforge_dir / "constitute.json").write_text(
        json.dumps(cfg, indent=2), encoding="utf-8"
    )


def _run_cli(argv: list) -> tuple:
    """Run the CLI and return (exit_code, stdout_str, stderr_str)."""
    old_stdout, old_stderr = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        code = main(argv)
        out = sys.stdout.getvalue()
        err = sys.stderr.getvalue()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return code, out, err


class TestCmdConfigMissing(unittest.TestCase):

    def test_cmd_exits_0_when_config_missing(self):
        """No constitute.json in .devforge/ -> exit 0, brief stderr note."""
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = _run_cli(["verify-magic-enum", "--root", tmp])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("skipping", err)

    def test_cmd_exits_0_when_ff_block_absent(self):
        """constitute.json without forcing_functions key -> exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            (devforge / "constitute.json").write_text(
                json.dumps({"project_name": "test"}), encoding="utf-8"
            )
            code, out, err = _run_cli(["verify-magic-enum", "--root", tmp])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_cmd_exits_0_when_rule_block_absent(self):
        """forcing_functions key present but no magic_enum_duplication entry -> exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            (devforge / "constitute.json").write_text(
                json.dumps({"forcing_functions": {"other_rule": {"enabled": True}}}),
                encoding="utf-8",
            )
            code, out, err = _run_cli(["verify-magic-enum", "--root", tmp])
        self.assertEqual(code, 0)


class TestCmdDisabled(unittest.TestCase):

    def test_cmd_exits_0_when_disabled(self):
        """forcing_functions.magic_enum_duplication.enabled = false -> exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _write_config(devforge, enabled=False, generated_dirs=["generated"])
            code, out, err = _run_cli(["verify-magic-enum", "--root", tmp])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")


class TestCmdViolations(unittest.TestCase):

    def _setup_violation_project(self, tmp: str) -> None:
        """Create a minimal consumer project with one violation."""
        root = Path(tmp)
        gen_dir = root / "generated"
        gen_dir.mkdir()

        # Write a generated type file with OrgV2AddressType
        (gen_dir / "index.ts").write_text(
            "export type OrgV2AddressType = 'SHIPPING' | 'BILLING';\n",
            encoding="utf-8",
        )

        # Write a consumer source file with a magic-string violation
        src_dir = root / "src"
        src_dir.mkdir()
        (src_dir / "order.ts").write_text(
            "const addressType = 'SHIPPING';\n",
            encoding="utf-8",
        )

        # Write config
        devforge = root / ".devforge"
        _write_config(devforge, enabled=True, generated_dirs=["generated"])

    def test_cmd_exits_2_with_violations(self):
        """Full setup with violation -> exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_violation_project(tmp)
            code, out, err = _run_cli(["verify-magic-enum", "--root", tmp])
        self.assertEqual(code, 2)

    def test_cmd_stderr_cites_violation(self):
        """Stderr contains the violation path and VIOLATION kind marker."""
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_violation_project(tmp)
            code, out, err = _run_cli(["verify-magic-enum", "--root", tmp])
        self.assertIn("VIOLATION", err)
        self.assertIn("SHIPPING", err)

    def test_cmd_stderr_format_contract(self):
        """Stderr line matches the full ``path:line: VIOLATION [rule] summary``
        contract defined by ``_shared.emit_findings``.  Regression guard for
        Phase 5 wire-in: humans triage findings from stderr, so the format
        cannot silently drift.
        """
        import re as _re

        with tempfile.TemporaryDirectory() as tmp:
            self._setup_violation_project(tmp)
            code, out, err = _run_cli(["verify-magic-enum", "--root", tmp])
        self.assertEqual(code, 2)
        # Match: <path>:<line>: VIOLATION [magic_enum_duplication] <summary>
        pattern = _re.compile(
            r"^[^\n]+:\d+: VIOLATION \[magic_enum_duplication\] .+$",
            _re.MULTILINE,
        )
        self.assertTrue(
            pattern.search(err),
            "Stderr does not match the expected "
            "'path:line: VIOLATION [magic_enum_duplication] summary' format. "
            "Got: {!r}".format(err),
        )

    def test_cmd_stdout_is_valid_json_on_violations(self):
        """Stdout is valid JSON with rule and findings fields when exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_violation_project(tmp)
            code, out, err = _run_cli(["verify-magic-enum", "--root", tmp])
        self.assertEqual(code, 2)
        parsed = json.loads(out)
        self.assertEqual(parsed["rule"], "magic_enum_duplication")
        self.assertIsInstance(parsed["findings"], list)
        self.assertGreater(len(parsed["findings"]), 0)
        first = parsed["findings"][0]
        self.assertIn("path", first)
        self.assertIn("line", first)
        self.assertIn("kind", first)
        self.assertIn("summary", first)
        self.assertEqual(first["kind"], "VIOLATION")

    def test_cmd_stdout_path_is_relative(self):
        """Finding paths in stdout JSON are project-relative, not absolute."""
        with tempfile.TemporaryDirectory() as tmp:
            self._setup_violation_project(tmp)
            code, out, err = _run_cli(["verify-magic-enum", "--root", tmp])
        parsed = json.loads(out)
        for finding in parsed["findings"]:
            self.assertFalse(
                os.path.isabs(finding["path"]),
                msg="Finding path should be relative, got: {0}".format(finding["path"]),
            )


class TestCmdCleanSource(unittest.TestCase):

    def test_cmd_exits_0_on_clean_source(self):
        """Valid config + generated dir + consumer source with no violations -> exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gen_dir = root / "generated"
            gen_dir.mkdir()
            (gen_dir / "index.ts").write_text(
                "export type Status = 'ACTIVE' | 'INACTIVE';\n",
                encoding="utf-8",
            )
            src_dir = root / "src"
            src_dir.mkdir()
            (src_dir / "service.ts").write_text(
                "import { Status } from '../generated/index';\n"
                "const s = Status.Active;\n",
                encoding="utf-8",
            )
            devforge = root / ".devforge"
            _write_config(devforge, enabled=True, generated_dirs=["generated"])
            code, out, err = _run_cli(["verify-magic-enum", "--root", tmp])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_cmd_help_works(self):
        """--help exits 0 (argparse handles this naturally)."""
        with self.assertRaises(SystemExit) as ctx:
            _run_cli(["verify-magic-enum", "--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_cmd_custom_config_path(self):
        """--config flag allows specifying a non-default config path."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # Config at a non-default location.
            config_dir = root / "custom"
            config_dir.mkdir()
            config_path = config_dir / "my-constitute.json"
            config_path.write_text(
                json.dumps({
                    "forcing_functions": {
                        "magic_enum_duplication": {
                            "enabled": False,
                            "generated_types_dirs": [],
                        }
                    }
                }),
                encoding="utf-8",
            )
            code, out, err = _run_cli([
                "verify-magic-enum",
                "--root", tmp,
                "--config", str(config_path),
            ])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
