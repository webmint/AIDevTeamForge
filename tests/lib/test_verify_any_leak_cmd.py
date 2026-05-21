"""End-to-end tests for the ``verify-any-leak`` subcommand (Phase 4).

Tests exercise the full CLI path via the ``main()`` function in
``_constitute._cli``, mirroring how the ``constitute_helper`` shim works.
Stdout and stderr are captured via io.StringIO redirection.

Coverage
--------
test_cmd_exits_0_when_config_missing         -- no constitute.json -> exit 0
test_cmd_exits_0_when_disabled               -- enabled: false -> exit 0 silently
test_cmd_exits_0_when_ff_block_absent        -- no forcing_functions key -> exit 0
test_cmd_exits_0_when_rule_block_absent      -- no any_with_generated_available key -> exit 0
test_cmd_exits_0_when_generated_dirs_missing -- rule enabled but dirs key absent -> exit 0 + note
test_cmd_exits_2_with_violations             -- full setup, qualifying file with : any -> exit 2
test_cmd_stdout_is_valid_json_on_violations  -- stdout JSON shape on exit 2
test_cmd_stderr_format_contract              -- stderr matches path:line: VIOLATION [rule] summary
test_cmd_stdout_path_is_relative             -- finding paths in JSON are project-relative
test_cmd_exits_0_on_clean_source             -- valid config, no any -> exit 0
test_cmd_help_works                          -- --help returns exit 0
test_cmd_custom_config_path                  -- --config flag uses non-default path
test_cmd_malformed_json_exits_0              -- corrupt constitute.json -> exit 0 (family-wide)
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

_LIB_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "..", "src", "devforge", "lib"
)
if _LIB_ROOT not in sys.path:
    sys.path.insert(0, _LIB_ROOT)

from _constitute._cli import main  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_config(
    devforge_dir: Path,
    enabled: bool,
    generated_types_dirs=None,
    allowlist_paths=None,
) -> None:
    """Write a constitute.json with the any_with_generated_available block."""
    devforge_dir.mkdir(parents=True, exist_ok=True)
    rule_cfg = {"enabled": enabled}
    if generated_types_dirs is not None:
        rule_cfg["generated_types_dirs"] = generated_types_dirs
    if allowlist_paths is not None:
        rule_cfg["allowlist_paths"] = allowlist_paths
    cfg = {"forcing_functions": {"any_with_generated_available": rule_cfg}}
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


_DEFAULT_GEN_DIRS = ["packages/cse-types/src"]
_DEFAULT_ALLOWLIST = [
    "node_modules/**", "**/node_modules/**",
    ".git/**", "**/.git/**",
    "**/*.test.ts", "**/*.spec.ts",
]

QUALIFYING_IMPORT = "import { Foo } from '../../packages/cse-types/src/types';\n"


def _setup_violation_project(root: Path) -> None:
    """Minimal consumer project with one qualifying file that has : any."""
    # Create the generated types dir.
    (root / "packages/cse-types/src").mkdir(parents=True, exist_ok=True)
    # Write a qualifying source file.
    _write(
        root / "src/service.ts",
        QUALIFYING_IMPORT + "const x: any = getValue();\n",
    )
    _write_config(
        root / ".devforge",
        enabled=True,
        generated_types_dirs=_DEFAULT_GEN_DIRS,
        allowlist_paths=_DEFAULT_ALLOWLIST,
    )


# ---------------------------------------------------------------------------
# Tests: early-exit conditions (exit 0)
# ---------------------------------------------------------------------------

class TestCmdEarlyExit(unittest.TestCase):

    def test_cmd_exits_0_when_config_missing(self):
        """No constitute.json -> exit 0, brief stderr note."""
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = _run_cli(["verify-any-leak", "--root", tmp])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("skipping", err)

    def test_cmd_exits_0_when_disabled(self):
        """enabled: false -> exit 0 silently (no stderr note required)."""
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(
                Path(tmp) / ".devforge",
                enabled=False,
                generated_types_dirs=_DEFAULT_GEN_DIRS,
            )
            code, out, err = _run_cli(["verify-any-leak", "--root", tmp])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_cmd_exits_0_when_ff_block_absent(self):
        """constitute.json without forcing_functions -> exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            (devforge / "constitute.json").write_text(
                json.dumps({"project_name": "test"}), encoding="utf-8"
            )
            code, out, err = _run_cli(["verify-any-leak", "--root", tmp])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_cmd_exits_0_when_rule_block_absent(self):
        """forcing_functions present but no any_with_generated_available key -> exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            (devforge / "constitute.json").write_text(
                json.dumps({"forcing_functions": {"other_rule": {"enabled": True}}}),
                encoding="utf-8",
            )
            code, out, err = _run_cli(["verify-any-leak", "--root", tmp])
        self.assertEqual(code, 0)

    def test_cmd_exits_0_when_generated_dirs_missing(self):
        """Rule enabled but generated_types_dirs key absent -> exit 0 + stderr note."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            (devforge / "constitute.json").write_text(
                json.dumps({
                    "forcing_functions": {
                        "any_with_generated_available": {
                            "enabled": True,
                            # No generated_types_dirs key
                        }
                    }
                }),
                encoding="utf-8",
            )
            code, out, err = _run_cli(["verify-any-leak", "--root", tmp])
        self.assertEqual(code, 0)
        self.assertIn("generated_types_dirs", err)


# ---------------------------------------------------------------------------
# Tests: violations (exit 2)
# ---------------------------------------------------------------------------

class TestCmdViolations(unittest.TestCase):

    def test_cmd_exits_2_with_violations(self):
        """Full setup, qualifying file with : any -> exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_violation_project(Path(tmp))
            code, out, err = _run_cli(["verify-any-leak", "--root", tmp])
        self.assertEqual(code, 2)

    def test_cmd_stdout_is_valid_json_on_violations(self):
        """Stdout is valid JSON with rule and findings when exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_violation_project(Path(tmp))
            code, out, err = _run_cli(["verify-any-leak", "--root", tmp])
        self.assertEqual(code, 2)
        parsed = json.loads(out)
        self.assertEqual(parsed["rule"], "any_with_generated_available")
        self.assertIsInstance(parsed["findings"], list)
        self.assertGreater(len(parsed["findings"]), 0)
        first = parsed["findings"][0]
        self.assertIn("path", first)
        self.assertIn("line", first)
        self.assertIn("kind", first)
        self.assertIn("summary", first)
        self.assertEqual(first["kind"], "VIOLATION")

    def test_cmd_stderr_format_contract(self):
        """Stderr line matches ``path:line: VIOLATION [any_with_generated_available] summary``."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_violation_project(Path(tmp))
            code, out, err = _run_cli(["verify-any-leak", "--root", tmp])
        self.assertEqual(code, 2)
        pattern = re.compile(
            r"^[^\n]+:\d+: VIOLATION \[any_with_generated_available\] .+$",
            re.MULTILINE,
        )
        self.assertTrue(
            pattern.search(err),
            "Stderr does not match expected format. Got: {!r}".format(err),
        )

    def test_cmd_stdout_path_is_relative(self):
        """Finding paths in stdout JSON are project-relative, not absolute."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_violation_project(Path(tmp))
            code, out, err = _run_cli(["verify-any-leak", "--root", tmp])
        parsed = json.loads(out)
        for finding in parsed["findings"]:
            self.assertFalse(
                os.path.isabs(finding["path"]),
                "Finding path should be relative, got: {}".format(finding["path"]),
            )


# ---------------------------------------------------------------------------
# Tests: clean + misc
# ---------------------------------------------------------------------------

class TestCmdClean(unittest.TestCase):

    def test_cmd_exits_0_on_clean_source(self):
        """Valid config, qualifying file with no any -> exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "packages/cse-types/src").mkdir(parents=True, exist_ok=True)
            _write(
                root / "src/service.ts",
                QUALIFYING_IMPORT + "const x: string = getValue();\n",
            )
            _write_config(
                root / ".devforge",
                enabled=True,
                generated_types_dirs=_DEFAULT_GEN_DIRS,
            )
            code, out, err = _run_cli(["verify-any-leak", "--root", tmp])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_cmd_help_works(self):
        """--help exits 0 (argparse)."""
        with self.assertRaises(SystemExit) as ctx:
            _run_cli(["verify-any-leak", "--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_cmd_custom_config_path(self):
        """--config flag uses a non-default config path."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_dir = root / "custom"
            config_dir.mkdir()
            config_path = config_dir / "my-constitute.json"
            config_path.write_text(
                json.dumps({
                    "forcing_functions": {
                        "any_with_generated_available": {
                            "enabled": False,
                            "generated_types_dirs": ["packages/cse-types/src"],
                        }
                    }
                }),
                encoding="utf-8",
            )
            code, out, err = _run_cli([
                "verify-any-leak",
                "--root", tmp,
                "--config", str(config_path),
            ])
        self.assertEqual(code, 0)

    def test_cmd_malformed_json_exits_0(self):
        """Malformed JSON in constitute.json -> exit 0 with stderr note."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            (devforge / "constitute.json").write_text(
                "{ not valid json }", encoding="utf-8"
            )
            code, out, err = _run_cli(["verify-any-leak", "--root", tmp])
        self.assertEqual(code, 0)
        self.assertIn("cannot parse", err)


if __name__ == "__main__":
    unittest.main()
