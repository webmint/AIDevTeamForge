"""End-to-end tests for the ``verify-cross-layer-imports`` subcommand (Phase 3).

Tests exercise the full CLI path via the ``main()`` function in
``_constitute._cli``, mirroring how the ``constitute_helper`` shim works.
Stdout and stderr are captured via io.StringIO redirection.

Coverage
--------
test_cmd_exits_0_when_config_missing         -- no constitute.json -> exit 0
test_cmd_exits_0_when_ff_block_absent        -- no forcing_functions key -> exit 0
test_cmd_exits_0_when_rule_block_absent      -- no cross_layer_imports key -> exit 0
test_cmd_exits_0_when_disabled               -- enabled: false -> exit 0 silently
test_cmd_exits_2_with_violations             -- full setup, violation exists -> exit 2
test_cmd_stdout_is_valid_json_on_violations  -- stdout JSON shape on exit 2
test_cmd_stderr_format_contract              -- stderr line matches path:line: VIOLATION [rule] summary
test_cmd_stdout_path_is_relative             -- finding paths in JSON are project-relative
test_cmd_malformed_layer_graph_exits_findings -- unknown layer in graph -> exit 2
test_cmd_malformed_layer_dirs_only_exits_findings -- layer in layer_dirs not in layer_graph -> exit 2
test_cmd_exits_0_on_clean_source             -- valid config + no violations -> exit 0
test_cmd_help_works                          -- --help returns exit 0
test_cmd_custom_config_path                  -- --config flag uses non-default path
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
    layer_graph: dict = None,
    layer_dirs: dict = None,
    allowlist_paths: list = None,
) -> None:
    """Write a constitute.json with the cross_layer_imports block."""
    devforge_dir.mkdir(parents=True, exist_ok=True)
    rule_cfg = {
        "enabled": enabled,
        "layer_graph": layer_graph or {},
        "layer_dirs": layer_dirs or {},
        "allowlist_paths": allowlist_paths or [],
    }
    cfg = {"forcing_functions": {"cross_layer_imports": rule_cfg}}
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


_VALID_LAYER_GRAPH = {
    "domain": [],
    "infra": ["domain"],
    "ui": ["domain", "infra"],
}
_VALID_LAYER_DIRS = {
    "domain": ["pkg/domain/**", "**/pkg/domain/**"],
    "infra": ["pkg/infra/**", "**/pkg/infra/**"],
    "ui": ["pkg/ui/**", "**/pkg/ui/**"],
}


def _setup_violation_project(root: Path) -> None:
    """Minimal consumer project with one domain->infra violation."""
    _write(root / "pkg/infra/bar.ts", "export const bar = 1;\n")
    _write(
        root / "pkg/domain/foo.ts",
        "import { bar } from '../infra/bar';\n",
    )
    _write_config(
        root / ".devforge",
        enabled=True,
        layer_graph=_VALID_LAYER_GRAPH,
        layer_dirs=_VALID_LAYER_DIRS,
    )


# ---------------------------------------------------------------------------
# Tests: early-exit conditions (exit 0)
# ---------------------------------------------------------------------------

class TestCmdEarlyExit(unittest.TestCase):

    def test_cmd_exits_0_when_config_missing(self):
        """No constitute.json -> exit 0, brief stderr note."""
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = _run_cli(["verify-cross-layer-imports", "--root", tmp])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("skipping", err)

    def test_cmd_exits_0_when_ff_block_absent(self):
        """constitute.json without forcing_functions -> exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            (devforge / "constitute.json").write_text(
                json.dumps({"project_name": "test"}), encoding="utf-8"
            )
            code, out, err = _run_cli(["verify-cross-layer-imports", "--root", tmp])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_cmd_exits_0_when_rule_block_absent(self):
        """forcing_functions present but no cross_layer_imports key -> exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            (devforge / "constitute.json").write_text(
                json.dumps({"forcing_functions": {"other_rule": {"enabled": True}}}),
                encoding="utf-8",
            )
            code, out, err = _run_cli(["verify-cross-layer-imports", "--root", tmp])
        self.assertEqual(code, 0)

    def test_cmd_exits_0_when_disabled(self):
        """cross_layer_imports.enabled = false -> exit 0 silently (no stderr note)."""
        with tempfile.TemporaryDirectory() as tmp:
            _write_config(
                Path(tmp) / ".devforge",
                enabled=False,
                layer_graph=_VALID_LAYER_GRAPH,
                layer_dirs=_VALID_LAYER_DIRS,
            )
            code, out, err = _run_cli(["verify-cross-layer-imports", "--root", tmp])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        # Silently exit (no stderr note required when disabled — matches magic-enum pattern).


# ---------------------------------------------------------------------------
# Tests: violations
# ---------------------------------------------------------------------------

class TestCmdViolations(unittest.TestCase):

    def test_cmd_exits_2_with_violations(self):
        """Full setup with a domain->infra import -> exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_violation_project(Path(tmp))
            code, out, err = _run_cli(["verify-cross-layer-imports", "--root", tmp])
        self.assertEqual(code, 2)

    def test_cmd_stdout_is_valid_json_on_violations(self):
        """Stdout is valid JSON with rule and findings fields when exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_violation_project(Path(tmp))
            code, out, err = _run_cli(["verify-cross-layer-imports", "--root", tmp])
        self.assertEqual(code, 2)
        parsed = json.loads(out)
        self.assertEqual(parsed["rule"], "cross_layer_imports")
        self.assertIsInstance(parsed["findings"], list)
        self.assertGreater(len(parsed["findings"]), 0)
        first = parsed["findings"][0]
        self.assertIn("path", first)
        self.assertIn("line", first)
        self.assertIn("kind", first)
        self.assertIn("summary", first)
        self.assertEqual(first["kind"], "VIOLATION")

    def test_cmd_stderr_format_contract(self):
        """Stderr line matches ``path:line: VIOLATION [cross_layer_imports] summary``."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_violation_project(Path(tmp))
            code, out, err = _run_cli(["verify-cross-layer-imports", "--root", tmp])
        self.assertEqual(code, 2)
        pattern = re.compile(
            r"^[^\n]+:\d+: VIOLATION \[cross_layer_imports\] .+$",
            re.MULTILINE,
        )
        self.assertTrue(
            pattern.search(err),
            "Stderr does not match 'path:line: VIOLATION [cross_layer_imports] summary'. "
            "Got: {!r}".format(err),
        )

    def test_cmd_stdout_path_is_relative(self):
        """Finding paths in stdout JSON are project-relative, not absolute."""
        with tempfile.TemporaryDirectory() as tmp:
            _setup_violation_project(Path(tmp))
            code, out, err = _run_cli(["verify-cross-layer-imports", "--root", tmp])
        parsed = json.loads(out)
        for finding in parsed["findings"]:
            self.assertFalse(
                os.path.isabs(finding["path"]),
                "Finding path should be relative, got: {}".format(finding["path"]),
            )


# ---------------------------------------------------------------------------
# Tests: malformed config
# ---------------------------------------------------------------------------

class TestCmdMalformedConfig(unittest.TestCase):

    def test_cmd_malformed_layer_graph_exits_findings(self):
        """Unknown layer in layer_graph values -> exit 2; stderr cites the error."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            bad_cfg = {
                "forcing_functions": {
                    "cross_layer_imports": {
                        "enabled": True,
                        "layer_graph": {
                            "domain": [],
                            "infra": ["nonexistent_layer"],  # unknown layer
                        },
                        "layer_dirs": {
                            "domain": "pkg/domain/**",
                            "infra": "pkg/infra/**",
                        },
                        "allowlist_paths": [],
                    }
                }
            }
            (devforge / "constitute.json").write_text(
                json.dumps(bad_cfg, indent=2), encoding="utf-8"
            )
            code, out, err = _run_cli(["verify-cross-layer-imports", "--root", tmp])
        self.assertEqual(code, 2)
        # Stderr must reference the unknown layer name.
        self.assertIn("nonexistent_layer", err)

    def test_cmd_malformed_layer_dirs_only_exits_findings(self):
        """Layer in layer_dirs but not in layer_graph -> ValueError -> exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            bad_cfg = {
                "forcing_functions": {
                    "cross_layer_imports": {
                        "enabled": True,
                        "layer_graph": {"domain": []},
                        "layer_dirs": {
                            "domain": "pkg/domain/**",
                            "orphan": "pkg/orphan/**",  # not in layer_graph
                        },
                        "allowlist_paths": [],
                    }
                }
            }
            (devforge / "constitute.json").write_text(
                json.dumps(bad_cfg, indent=2), encoding="utf-8"
            )
            code, out, err = _run_cli(["verify-cross-layer-imports", "--root", tmp])
        self.assertEqual(code, 2)
        self.assertIn("orphan", err)


# ---------------------------------------------------------------------------
# Tests: clean + misc
# ---------------------------------------------------------------------------

class TestCmdClean(unittest.TestCase):

    def test_cmd_exits_0_on_clean_source(self):
        """Valid config + consumer source with no violations -> exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "pkg/domain/a.ts", "export const a = 1;\n")
            _write(
                root / "pkg/ui/page.ts",
                "import { a } from '../domain/a';\n",  # ui->domain is allowed
            )
            _write_config(
                root / ".devforge",
                enabled=True,
                layer_graph=_VALID_LAYER_GRAPH,
                layer_dirs=_VALID_LAYER_DIRS,
            )
            code, out, err = _run_cli(["verify-cross-layer-imports", "--root", tmp])
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_cmd_help_works(self):
        """--help exits 0 (argparse)."""
        with self.assertRaises(SystemExit) as ctx:
            _run_cli(["verify-cross-layer-imports", "--help"])
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
                        "cross_layer_imports": {
                            "enabled": False,
                            "layer_graph": {},
                            "layer_dirs": {},
                            "allowlist_paths": [],
                        }
                    }
                }),
                encoding="utf-8",
            )
            code, out, err = _run_cli([
                "verify-cross-layer-imports",
                "--root", tmp,
                "--config", str(config_path),
            ])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
