"""Tests for probe_command_executability and collect_executability_warnings.

Covers:
- probe_command_executability: single resolvable token → no missing
- probe_command_executability: single unresolvable token → missing token returned
- probe_command_executability: "N/A" literal → skipped (None returned)
- probe_command_executability: empty / blank string → skipped (None returned)
- probe_command_executability: &&-chain with missing second token → warning names
  the missing token; cd prefix ignored
- probe_command_executability: &&-chain with all tokens resolvable → no missing
- probe_command_executability: semicolon-chain → same logic as &&-chain
- probe_command_executability: "cd packages/x && tsc" where tsc missing → tsc named
- probe_command_executability: "cd packages/x && tsc" where tsc present → no missing
- collect_executability_warnings: primary commands all probed (type_check, lint, build)
- collect_executability_warnings: package_stacks commands probed per-package
- collect_executability_warnings: N/A commands skipped, no false warning
- collect_executability_warnings: empty state → no warnings
- collect_executability_warnings: mixed resolvable / unresolvable
- _render_configure_summary: warning block present when warnings exist
- _render_configure_summary: warning block absent when no warnings

shutil.which is monkeypatched throughout — tests do NOT depend on host PATH.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import List, Optional
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _configure._validators import (  # noqa: E402
    collect_executability_warnings,
    probe_command_executability,
)
from _configure._summary import _render_configure_summary  # noqa: E402


# ---------------------------------------------------------------------------
# Helper: build a which-mock that resolves specific tokens and nothing else.
# ---------------------------------------------------------------------------


def _make_which(present: List[str]):
    """Return a mock for shutil.which that resolves only tokens in `present`."""
    present_set = set(present)

    def _which(token):
        return "/usr/bin/{0}".format(token) if token in present_set else None

    return _which


# ---------------------------------------------------------------------------
# probe_command_executability — single token cases.
# ---------------------------------------------------------------------------


class TestProbeCommandExecutabilitySingleToken(unittest.TestCase):

    def test_resolvable_token_returns_empty(self):
        """A command whose binary resolves → no unresolved tokens."""
        with patch("shutil.which", _make_which(["vue-tsc"])):
            result = probe_command_executability("vue-tsc --noEmit")
        self.assertEqual(result, [])

    def test_unresolvable_token_returns_token_name(self):
        """A command whose binary does NOT resolve → the token name is returned."""
        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("vue-tsc --noEmit")
        self.assertEqual(result, ["vue-tsc"])

    def test_npm_command_resolvable_via_npm_prefix(self):
        """'npm run check' — npm is on PATH → empty (no warning)."""
        with patch("shutil.which", _make_which(["npm"])):
            result = probe_command_executability("npm run check")
        self.assertEqual(result, [])

    def test_npm_command_npm_missing(self):
        """'npm run check' — npm NOT on PATH → 'npm' flagged."""
        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("npm run check")
        self.assertEqual(result, ["npm"])

    def test_npx_command_resolvable(self):
        """'npx tsc' where npx resolves — no warning (accepted limitation: npx indirection)."""
        with patch("shutil.which", _make_which(["npx"])):
            result = probe_command_executability("npx tsc")
        self.assertEqual(result, [])

    def test_pnpm_resolvable(self):
        """'pnpm run build' where pnpm resolves → no warning."""
        with patch("shutil.which", _make_which(["pnpm"])):
            result = probe_command_executability("pnpm run build")
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# probe_command_executability — skip cases (N/A, empty, blank).
# ---------------------------------------------------------------------------


class TestProbeCommandExecutabilitySkip(unittest.TestCase):

    def test_na_literal_returns_none(self):
        """Literal 'N/A' → skipped; None returned."""
        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("N/A")
        self.assertIsNone(result)

    def test_empty_string_returns_none(self):
        """Empty string → skipped; None returned."""
        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("")
        self.assertIsNone(result)

    def test_blank_string_returns_none(self):
        """Whitespace-only string → skipped; None returned."""
        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("   ")
        self.assertIsNone(result)

    def test_na_with_surrounding_spaces_returns_none(self):
        """'  N/A  ' → treated as N/A after strip; skipped."""
        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("  N/A  ")
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# probe_command_executability — chain cases (&&, ;).
# ---------------------------------------------------------------------------


class TestProbeCommandExecutabilityChain(unittest.TestCase):

    def test_cd_then_tsc_missing(self):
        """'cd packages/x && tsc' where tsc is missing → ['tsc'] (cd ignored)."""
        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("cd packages/x && tsc --noEmit")
        self.assertEqual(result, ["tsc"])

    def test_cd_then_tsc_present(self):
        """'cd packages/x && tsc' where tsc resolves → empty."""
        with patch("shutil.which", _make_which(["tsc"])):
            result = probe_command_executability("cd packages/x && tsc --noEmit")
        self.assertEqual(result, [])

    def test_cd_only_segment_skipped(self):
        """'cd packages/x' alone — cd segment skipped; no warning."""
        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("cd packages/x")
        self.assertEqual(result, [])

    def test_chain_both_missing(self):
        """'foo --x && bar --y' — both foo and bar missing → both flagged."""
        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("foo --x && bar --y")
        self.assertIn("foo", result)
        self.assertIn("bar", result)

    def test_chain_first_missing_second_present(self):
        """'foo && npm run check' — foo missing, npm present → only foo flagged."""
        with patch("shutil.which", _make_which(["npm"])):
            result = probe_command_executability("foo && npm run check")
        self.assertEqual(result, ["foo"])

    def test_semicolon_chain_missing(self):
        """'vue-tsc; eslint .' — vue-tsc missing, eslint present → ['vue-tsc']."""
        with patch("shutil.which", _make_which(["eslint"])):
            result = probe_command_executability("vue-tsc; eslint .")
        self.assertEqual(result, ["vue-tsc"])

    def test_semicolon_chain_all_present(self):
        """'tsc; eslint .' — both present → empty."""
        with patch("shutil.which", _make_which(["tsc", "eslint"])):
            result = probe_command_executability("tsc; eslint .")
        self.assertEqual(result, [])

    def test_dedup_same_missing_token(self):
        """If same missing token appears in two segments, reported once."""
        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("tsc && tsc --strict")
        self.assertEqual(result.count("tsc"), 1)


# ---------------------------------------------------------------------------
# probe_command_executability — false-positive regression tests.
# ---------------------------------------------------------------------------


class TestProbeCommandExecutabilityFalsePositiveRegressions(unittest.TestCase):
    """Regression tests for the three false-positive classes fixed in the
    unified tokenizer rewrite:
      - Finding 1: env-var assignment prefix skipped; real executable probed.
      - Finding 2: no-space '&&' treated as separator (tsc&&eslint).
      - Finding 3: ';' / '&&' inside quoted args NOT treated as separators.
    """

    # --- Finding 1: env-var assignment prefix ---

    def test_env_var_prefix_is_skipped_executable_present(self):
        """NODE_ENV=test tsc — tsc present → no warning (no false-positive on NODE_ENV=test)."""
        with patch("shutil.which", _make_which(["tsc"])):
            result = probe_command_executability("NODE_ENV=test tsc --noEmit")
        self.assertEqual(result, [])

    def test_env_var_prefix_is_skipped_executable_missing(self):
        """NODE_ENV=test tsc — tsc absent → warns 'tsc', NOT 'NODE_ENV=test'."""
        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("NODE_ENV=test tsc --noEmit")
        self.assertEqual(result, ["tsc"])

    def test_multiple_env_var_prefixes(self):
        """A=1 B=2 tsc — probes 'tsc' (skips both A=1 and B=2)."""
        with patch("shutil.which", _make_which(["tsc"])):
            result = probe_command_executability("A=1 B=2 tsc --noEmit")
        self.assertEqual(result, [])

    def test_multiple_env_var_prefixes_missing(self):
        """A=1 B=2 tsc — tsc absent → warns 'tsc'."""
        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("A=1 B=2 tsc --noEmit")
        self.assertEqual(result, ["tsc"])

    def test_env_var_prefix_real_world_node_env_next_build(self):
        """NODE_ENV=production next build — 'next' probed (present → no warning)."""
        with patch("shutil.which", _make_which(["next"])):
            result = probe_command_executability("NODE_ENV=production next build")
        self.assertEqual(result, [])

    def test_env_var_prefix_real_world_ci_vite(self):
        """CI=true vite build — 'vite' probed (missing → warns 'vite')."""
        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("CI=true vite build")
        self.assertEqual(result, ["vite"])

    def test_segment_only_assignments_probes_nothing(self):
        """A segment consisting only of assignments → nothing probed (no crash)."""
        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("NODE_ENV=test")
        # Segment is entirely assignments — no executable to probe → empty (not missing).
        self.assertEqual(result, [])

    # --- Finding 2: no-space '&&' ---

    def test_no_space_ampersand_chain_both_present(self):
        """tsc&&eslint — both present → no warning."""
        with patch("shutil.which", _make_which(["tsc", "eslint"])):
            result = probe_command_executability("tsc&&eslint")
        self.assertEqual(result, [])

    def test_no_space_ampersand_chain_first_missing(self):
        """tsc&&eslint — tsc absent → warns 'tsc'."""
        with patch("shutil.which", _make_which(["eslint"])):
            result = probe_command_executability("tsc&&eslint")
        self.assertEqual(result, ["tsc"])

    def test_no_space_ampersand_chain_second_missing(self):
        """tsc&&eslint — eslint absent → warns 'eslint'."""
        with patch("shutil.which", _make_which(["tsc"])):
            result = probe_command_executability("tsc&&eslint")
        self.assertEqual(result, ["eslint"])

    def test_no_space_ampersand_with_args(self):
        """tsc --noEmit&&eslint . — two segments; tsc absent → warns 'tsc' only."""
        with patch("shutil.which", _make_which(["eslint"])):
            result = probe_command_executability("tsc --noEmit&&eslint .")
        self.assertEqual(result, ["tsc"])

    # --- Finding 3: separator inside quoted args ---

    def test_semicolon_in_single_quoted_arg_not_split(self):
        """eslint --rule 'no-use;before-define' — eslint present → no warning (one segment)."""
        with patch("shutil.which", _make_which(["eslint"])):
            result = probe_command_executability("eslint --rule 'no-use;before-define'")
        self.assertEqual(result, [])

    def test_semicolon_in_double_quoted_arg_not_split(self):
        """eslint --rule "no-use;before-define" — eslint present → no warning."""
        with patch("shutil.which", _make_which(["eslint"])):
            result = probe_command_executability('eslint --rule "no-use;before-define"')
        self.assertEqual(result, [])

    def test_ampersand_in_quoted_arg_not_split(self):
        """eslint --rule 'x && y' — eslint present → no warning (one segment)."""
        with patch("shutil.which", _make_which(["eslint"])):
            result = probe_command_executability("eslint --rule 'x && y'")
        self.assertEqual(result, [])

    def test_ampersand_in_quoted_arg_missing_executable(self):
        """eslint --rule 'x && y' — eslint absent → warns 'eslint' (not split on && inside quotes)."""
        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("eslint --rule 'x && y'")
        self.assertEqual(result, ["eslint"])


# ---------------------------------------------------------------------------
# collect_executability_warnings — integration over state.
# ---------------------------------------------------------------------------


class TestCollectExecutabilityWarnings(unittest.TestCase):

    def _make_state(
        self,
        type_check_commands=None,
        lint_commands=None,
        build_commands=None,
        package_stacks=None,
    ):
        """Minimal state dict with only the command-bearing fields."""
        return {
            "type_check_commands": type_check_commands or [],
            "lint_commands": lint_commands or [],
            "build_commands": build_commands or [],
            "package_stacks": package_stacks or [],
        }

    def test_empty_state_no_warnings(self):
        """All empty arrays → no warnings."""
        with patch("shutil.which", _make_which([])):
            warnings = collect_executability_warnings(self._make_state())
        self.assertEqual(warnings, [])

    def test_primary_type_check_unresolvable(self):
        """Primary type_check_commands[0] unresolvable → warning with correct scope."""
        state = self._make_state(type_check_commands=["vue-tsc --noEmit"])
        with patch("shutil.which", _make_which([])):
            warnings = collect_executability_warnings(state)
        self.assertEqual(len(warnings), 1)
        w = warnings[0]
        self.assertIn("type_check", w["scope"])
        self.assertEqual(w["command"], "vue-tsc --noEmit")
        self.assertEqual(w["missing_token"], "vue-tsc")

    def test_primary_lint_unresolvable(self):
        """Primary lint_commands[0] unresolvable → warning."""
        state = self._make_state(lint_commands=["eslint ."])
        with patch("shutil.which", _make_which([])):
            warnings = collect_executability_warnings(state)
        self.assertEqual(len(warnings), 1)
        self.assertIn("lint", warnings[0]["scope"])

    def test_primary_build_unresolvable(self):
        """Primary build_commands[0] unresolvable → warning."""
        state = self._make_state(build_commands=["vite build"])
        with patch("shutil.which", _make_which([])):
            warnings = collect_executability_warnings(state)
        self.assertEqual(len(warnings), 1)
        self.assertIn("build", warnings[0]["scope"])

    def test_primary_na_skipped(self):
        """Primary command 'N/A' → no warning."""
        state = self._make_state(type_check_commands=["N/A"])
        with patch("shutil.which", _make_which([])):
            warnings = collect_executability_warnings(state)
        self.assertEqual(warnings, [])

    def test_primary_all_resolvable_no_warnings(self):
        """All primary commands resolve → no warnings."""
        state = self._make_state(
            type_check_commands=["tsc --noEmit"],
            lint_commands=["eslint ."],
            build_commands=["npm run build"],
        )
        with patch("shutil.which", _make_which(["tsc", "eslint", "npm"])):
            warnings = collect_executability_warnings(state)
        self.assertEqual(warnings, [])

    def test_package_stacks_type_check_unresolvable(self):
        """Per-package type_check_command unresolvable → warning with package path in scope."""
        stack = {
            "path": "packages/frontend",
            "language": "TypeScript",
            "type_check_command": "vue-tsc --noEmit",
            "lint_command": None,
            "build_command": None,
        }
        state = self._make_state(package_stacks=[stack])
        with patch("shutil.which", _make_which([])):
            warnings = collect_executability_warnings(state)
        self.assertEqual(len(warnings), 1)
        w = warnings[0]
        self.assertIn("packages/frontend", w["scope"])
        self.assertEqual(w["missing_token"], "vue-tsc")

    def test_package_stacks_lint_unresolvable(self):
        """Per-package lint_command unresolvable → warning."""
        stack = {
            "path": "packages/api",
            "language": "Python",
            "lint_command": "ruff check .",
            "type_check_command": None,
            "build_command": None,
        }
        state = self._make_state(package_stacks=[stack])
        with patch("shutil.which", _make_which([])):
            warnings = collect_executability_warnings(state)
        self.assertEqual(len(warnings), 1)
        self.assertIn("packages/api", warnings[0]["scope"])
        self.assertEqual(warnings[0]["missing_token"], "ruff")

    def test_package_stacks_build_unresolvable(self):
        """Per-package build_command unresolvable → warning."""
        stack = {
            "path": "packages/ui",
            "language": "TypeScript",
            "build_command": "vite build",
            "type_check_command": None,
            "lint_command": None,
        }
        state = self._make_state(package_stacks=[stack])
        with patch("shutil.which", _make_which([])):
            warnings = collect_executability_warnings(state)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["missing_token"], "vite")

    def test_package_stacks_na_skipped(self):
        """Per-package command 'N/A' → no warning."""
        stack = {
            "path": "packages/docs",
            "language": "Markdown",
            "type_check_command": "N/A",
            "lint_command": "N/A",
            "build_command": "N/A",
        }
        state = self._make_state(package_stacks=[stack])
        with patch("shutil.which", _make_which([])):
            warnings = collect_executability_warnings(state)
        self.assertEqual(warnings, [])

    def test_package_stacks_none_fields_skipped(self):
        """Per-package command fields that are None → no warning."""
        stack = {
            "path": "packages/empty",
            "language": "Go",
            "type_check_command": None,
            "lint_command": None,
            "build_command": None,
        }
        state = self._make_state(package_stacks=[stack])
        with patch("shutil.which", _make_which([])):
            warnings = collect_executability_warnings(state)
        self.assertEqual(warnings, [])

    def test_multiple_packages_mixed(self):
        """Two packages, one with a missing tool → exactly one warning."""
        stacks = [
            {
                "path": "packages/frontend",
                "language": "TypeScript",
                "type_check_command": "vue-tsc --noEmit",
                "lint_command": None,
                "build_command": None,
            },
            {
                "path": "packages/api",
                "language": "Python",
                "type_check_command": "mypy .",
                "lint_command": None,
                "build_command": None,
            },
        ]
        state = self._make_state(package_stacks=stacks)
        # mypy is present, vue-tsc is not
        with patch("shutil.which", _make_which(["mypy"])):
            warnings = collect_executability_warnings(state)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["missing_token"], "vue-tsc")

    def test_warning_dict_has_required_keys(self):
        """Each warning has 'scope', 'command', 'missing_token' keys."""
        state = self._make_state(type_check_commands=["missing-tool --flag"])
        with patch("shutil.which", _make_which([])):
            warnings = collect_executability_warnings(state)
        self.assertEqual(len(warnings), 1)
        w = warnings[0]
        self.assertIn("scope", w)
        self.assertIn("command", w)
        self.assertIn("missing_token", w)


# ---------------------------------------------------------------------------
# _render_configure_summary — warning block integration.
# ---------------------------------------------------------------------------


class TestSummaryWarningBlock(unittest.TestCase):
    """Verify that _render_configure_summary emits/omits the WARNING block."""

    def _minimal_state(self):
        """State with all command fields empty (no warnings expected)."""
        return {
            "project_name": "my-project",
            "project_description": "A test project",
            "project_type": "web",
            "primary_language": "TypeScript",
            "languages": ["TypeScript"],
            "frameworks": ["Vue"],
            "architectures": ["spa"],
            "project_natures": ["web"],
            "error_handlings": ["result"],
            "api_layers": ["REST"],
            "testings": ["vitest"],
            "build_tools": ["vite"],
            "build_commands": [],
            "type_check_commands": [],
            "lint_commands": [],
            "package_stacks": [],
            "project_structure": "src/",
            "dev_commands": "npm run dev",
            "architecture_details": "SPA",
            "workflow_enforcement": "Strict",
            "ai_attribution": "Yes",
            "claude_tier_think": "Opus",
            "claude_tier_do": "Sonnet",
            "claude_tier_verify": "Haiku",
            "ac_verification_mode": "off",
            "ac_runtime_url": None,
            "ac_runtime_api_base": None,
            "ac_runtime_cli_command": None,
        }

    def test_warning_block_present_when_unresolvable(self):
        """Summary contains WARNING block when a primary command is unresolvable."""
        state = self._minimal_state()
        state["type_check_commands"] = ["vue-tsc --noEmit"]
        with patch("shutil.which", _make_which([])):
            output = _render_configure_summary(state)
        self.assertIn("WARNING", output)
        self.assertIn("vue-tsc", output)

    def test_warning_block_absent_when_all_resolvable(self):
        """Summary has no WARNING block when all commands resolve."""
        state = self._minimal_state()
        state["type_check_commands"] = ["tsc --noEmit"]
        state["lint_commands"] = ["eslint ."]
        with patch("shutil.which", _make_which(["tsc", "eslint"])):
            output = _render_configure_summary(state)
        self.assertNotIn("WARNING", output)

    def test_warning_block_absent_when_no_commands(self):
        """Summary has no WARNING block when all command fields are empty."""
        state = self._minimal_state()
        with patch("shutil.which", _make_which([])):
            output = _render_configure_summary(state)
        self.assertNotIn("WARNING", output)

    def test_warning_message_names_missing_token(self):
        """WARNING line cites the specific missing binary name."""
        state = self._minimal_state()
        state["type_check_commands"] = ["vue-tsc --noEmit"]
        with patch("shutil.which", _make_which([])):
            output = _render_configure_summary(state)
        # Must name the token explicitly so the user knows what to install.
        self.assertIn("vue-tsc", output)
        # Must mention PATH so the user understands the resolution context.
        self.assertIn("PATH", output)

    def test_warning_message_names_package_path(self):
        """WARNING for per-package command cites the package path."""
        state = self._minimal_state()
        state["package_stacks"] = [
            {
                "path": "packages/frontend",
                "language": "TypeScript",
                "type_check_command": "vue-tsc --noEmit",
                "lint_command": None,
                "build_command": None,
            }
        ]
        with patch("shutil.which", _make_which([])):
            output = _render_configure_summary(state)
        self.assertIn("packages/frontend", output)

    def test_summary_stability_no_commands(self):
        """Summary output is stable (deterministic) when no commands configured."""
        state = self._minimal_state()
        with patch("shutil.which", _make_which([])):
            out1 = _render_configure_summary(state)
            out2 = _render_configure_summary(state)
        self.assertEqual(out1, out2)

    def test_multiple_warnings_all_appear(self):
        """Multiple unresolvable commands → multiple WARNING lines."""
        state = self._minimal_state()
        state["type_check_commands"] = ["vue-tsc --noEmit"]
        state["lint_commands"] = ["eslint ."]
        with patch("shutil.which", _make_which([])):
            output = _render_configure_summary(state)
        self.assertIn("vue-tsc", output)
        self.assertIn("eslint", output)

    def test_na_command_no_warning_in_summary(self):
        """'N/A' in commands → no WARNING in summary."""
        state = self._minimal_state()
        state["type_check_commands"] = ["N/A"]
        with patch("shutil.which", _make_which([])):
            output = _render_configure_summary(state)
        self.assertNotIn("WARNING", output)


# ---------------------------------------------------------------------------
# node_bin_dirs unit tests (new shared utility).
# ---------------------------------------------------------------------------


import os as _os
import stat as _stat
import tempfile as _tempfile
import shutil as _shutil

from _shared.node_bin import node_bin_dirs, resolves  # noqa: E402


class TestNodeBinDirs(unittest.TestCase):
    """Unit tests for _shared.node_bin.node_bin_dirs upward-walk logic.

    Creates real temp directory trees so the 'is_dir' check in node_bin_dirs
    reflects actual filesystem state.
    """

    def setUp(self):
        self._root = _tempfile.mkdtemp()

    def tearDown(self):
        _shutil.rmtree(self._root, ignore_errors=True)

    def _mkdir(self, *parts):
        """Create <root>/<part1>/<part2>/... and return its path."""
        path = _os.path.join(self._root, *parts)
        _os.makedirs(path, exist_ok=True)
        return path

    def test_only_root_node_modules_bin_exists(self):
        """Only <source_root>/node_modules/.bin → returns that single dir."""
        self._mkdir("node_modules", ".bin")
        result = node_bin_dirs(self._root, "")
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].endswith(_os.path.join("node_modules", ".bin")))

    def test_no_node_modules_anywhere_empty_list(self):
        """No node_modules/.bin on any level → empty list."""
        result = node_bin_dirs(self._root, "packages/frontend")
        self.assertEqual(result, [])

    def test_package_local_first_root_last(self):
        """Package-local bin appears before root bin (most-specific first)."""
        self._mkdir("packages", "frontend", "node_modules", ".bin")
        self._mkdir("node_modules", ".bin")
        result = node_bin_dirs(self._root, "packages/frontend")
        # At minimum, frontend and root bins must be in the list.
        self.assertGreaterEqual(len(result), 2)
        # First entry should be the package-local bin.
        self.assertIn(_os.path.join("packages", "frontend", "node_modules", ".bin"),
                      result[0])
        # Last entry should be the root-level bin.
        self.assertIn(_os.path.join("node_modules", ".bin"), result[-1])
        # Root-level must NOT come before package-local.
        frontend_idx = next(i for i, d in enumerate(result)
                             if "frontend" in d)
        root_idx = next(i for i, d in enumerate(result)
                        if "packages" not in d and d.endswith(
                            _os.path.join("node_modules", ".bin")))
        self.assertLess(frontend_idx, root_idx,
                        "package-local bin must precede root bin in result list")

    def test_intermediate_dir_bin_included(self):
        """<root>/packages/node_modules/.bin (intermediate) included in upward walk."""
        self._mkdir("packages", "frontend", "node_modules", ".bin")
        self._mkdir("packages", "node_modules", ".bin")
        self._mkdir("node_modules", ".bin")
        result = node_bin_dirs(self._root, "packages/frontend")
        # All three dirs must appear.
        self.assertEqual(len(result), 3)

    def test_empty_package_path_returns_only_root_bin(self):
        """Empty package_path → only root node_modules/.bin checked."""
        self._mkdir("node_modules", ".bin")
        result = node_bin_dirs(self._root, "")
        self.assertEqual(len(result), 1)

    def test_dot_package_path_same_as_empty(self):
        """'.' package_path → equivalent to empty (start from source_root)."""
        self._mkdir("node_modules", ".bin")
        result = node_bin_dirs(self._root, ".")
        self.assertEqual(len(result), 1)

    def test_non_existent_node_modules_not_included(self):
        """Dirs that don't exist on disk are NOT returned."""
        # No node_modules anywhere.
        result = node_bin_dirs(self._root, "packages/frontend")
        self.assertEqual(result, [],
                         "non-existent node_modules/.bin must not appear in results")

    def test_result_paths_are_absolute(self):
        """All returned paths are absolute (not relative)."""
        self._mkdir("node_modules", ".bin")
        result = node_bin_dirs(self._root, "")
        for d in result:
            self.assertTrue(_os.path.isabs(d),
                            "path must be absolute: {0!r}".format(d))

    def test_deeply_nested_package_walks_up(self):
        """Deep package path 'a/b/c' — only existing bins at c, b, a, root returned."""
        self._mkdir("a", "b", "c", "node_modules", ".bin")
        self._mkdir("a", "node_modules", ".bin")
        # No bin at a/b or root.
        result = node_bin_dirs(self._root, "a/b/c")
        # Should find a/b/c and a, not root or a/b.
        self.assertEqual(len(result), 2)
        self.assertTrue(any("a" + _os.sep + "b" + _os.sep + "c" in d for d in result))
        self.assertTrue(any(d.endswith(_os.path.join("a", "node_modules", ".bin")) for d in result))

    def test_sibling_sharing_string_prefix_not_included(self):
        """A sibling dir whose name shares source_root's string prefix must NOT appear.

        Before the fix, a walk guard using str.startswith() would pass for
        a sibling like /tmp/proj_sibling when source_root is /tmp/proj,
        because '/tmp/proj_sibling'.startswith('/tmp/proj') is True.
        The separator-safe relative_to() check breaks out of the walk
        correctly so the sibling's node_modules/.bin is never returned.

        Concretely: source_root = <tmpdir>/proj,
                    sibling    = <tmpdir>/proj_sibling
        We start walking inside proj (package_path = "pkg") and ensure
        proj_sibling/node_modules/.bin is absent from the result even
        though its string representation starts with proj's path.
        """
        import tempfile as _tf
        import shutil as _sh

        # Create a fresh parent so we control the exact names.
        parent_dir = _tf.mkdtemp()
        try:
            root = _os.path.join(parent_dir, "proj")
            sibling = _os.path.join(parent_dir, "proj_sibling")

            # Create a package inside root and its bin dir.
            pkg_bin = _os.path.join(root, "pkg", "node_modules", ".bin")
            _os.makedirs(pkg_bin, exist_ok=True)

            # Create a node_modules/.bin inside the sibling (should never appear).
            sibling_bin = _os.path.join(sibling, "node_modules", ".bin")
            _os.makedirs(sibling_bin, exist_ok=True)

            result = node_bin_dirs(root, "pkg")

            # The sibling's bin MUST NOT appear in the walk result.
            for d in result:
                self.assertFalse(
                    d.startswith(sibling),
                    "sibling dir {0!r} must not appear in node_bin_dirs result; "
                    "got: {1!r}".format(sibling, result),
                )
        finally:
            _sh.rmtree(parent_dir, ignore_errors=True)


class TestResolvesFunction(unittest.TestCase):
    """Unit tests for _shared.node_bin.resolves()."""

    def setUp(self):
        self._root = _tempfile.mkdtemp()

    def tearDown(self):
        _shutil.rmtree(self._root, ignore_errors=True)

    def _make_fake_binary(self, bin_dir, name):
        """Create a fake executable at <bin_dir>/<name>."""
        _os.makedirs(bin_dir, exist_ok=True)
        path = _os.path.join(bin_dir, name)
        with open(path, "w") as fh:
            fh.write("#!/bin/sh\necho ok\n")
        _os.chmod(path, _stat.S_IRWXU)
        return path

    def test_token_on_global_path_returns_true(self):
        """Token found via shutil.which → True, regardless of node_modules."""
        with patch("shutil.which", _make_which(["tsc"])):
            result = resolves("tsc", self._root, "")
        self.assertTrue(result)

    def test_token_not_on_path_not_in_node_bin_returns_false(self):
        """Token absent from PATH and no node_modules → False."""
        with patch("shutil.which", _make_which([])):
            result = resolves("totally-absent-xyz", self._root, "")
        self.assertFalse(result)

    def test_token_in_root_node_modules_bin_returns_true(self):
        """Token in <source_root>/node_modules/.bin (not on PATH) → True."""
        bin_dir = _os.path.join(self._root, "node_modules", ".bin")
        self._make_fake_binary(bin_dir, "vue-tsc-fake")
        with patch("shutil.which", _make_which([])):
            result = resolves("vue-tsc-fake", self._root, "")
        self.assertTrue(result,
                        "binary in source_root/node_modules/.bin must resolve")

    def test_token_in_package_node_modules_bin_returns_true(self):
        """Token in <source_root>/<pkg>/node_modules/.bin → True."""
        bin_dir = _os.path.join(self._root, "packages", "ui", "node_modules", ".bin")
        self._make_fake_binary(bin_dir, "eslint-fake")
        with patch("shutil.which", _make_which([])):
            result = resolves("eslint-fake", self._root, "packages/ui")
        self.assertTrue(result,
                        "binary in package node_modules/.bin must resolve")

    def test_token_in_wrong_package_returns_false(self):
        """Token in packages/ui/node_modules/.bin but probing packages/api → False."""
        bin_dir = _os.path.join(self._root, "packages", "ui", "node_modules", ".bin")
        self._make_fake_binary(bin_dir, "ui-only-tool")
        with patch("shutil.which", _make_which([])):
            result = resolves("ui-only-tool", self._root, "packages/api")
        self.assertFalse(result,
                         "binary in wrong package must not resolve for different package")

    def test_non_executable_file_not_resolved(self):
        """A file in node_modules/.bin that is NOT executable → False."""
        bin_dir = _os.path.join(self._root, "node_modules", ".bin")
        _os.makedirs(bin_dir, exist_ok=True)
        path = _os.path.join(bin_dir, "non-exec-tool")
        with open(path, "w") as fh:
            fh.write("#!/bin/sh\n")
        # Make it NOT executable (read-only).
        _os.chmod(path, _stat.S_IRUSR)
        with patch("shutil.which", _make_which([])):
            result = resolves("non-exec-tool", self._root, "")
        self.assertFalse(result,
                         "non-executable file in node_modules/.bin must not resolve")

    def test_divergence_invariant_per_package_cannot_see_sibling_bin(self):
        """Divergence invariant (probe direction): resolves() is PER-PACKAGE.

        Design invariant: cmd_verify_touched UNIONS all touched packages'
        bin dirs, so it may resolve a binary that the per-package probe
        (resolves()) still returns False for.  The reverse must NEVER hold:
        if resolves() returns True, the runner must also find it.

        This test pins the invariant direction for the per-package probe:
        package B's resolves() call CANNOT see package A's
        node_modules/.bin, even though verify's union would include it.

        Setup:
          packages/a/node_modules/.bin/shared-tool  (executable)
          packages/b  (NO node_modules/.bin at all)

        Probing for "shared-tool" with package_path="packages/b" → False,
        because per-package walk from packages/b does not descend into
        packages/a.
        """
        # Create shared-tool in package A's bin dir.
        bin_dir_a = _os.path.join(self._root, "packages", "a", "node_modules", ".bin")
        self._make_fake_binary(bin_dir_a, "shared-tool")

        # Package B has no node_modules/.bin of its own.
        with patch("shutil.which", _make_which([])):
            result = resolves("shared-tool", self._root, "packages/b")

        self.assertFalse(
            result,
            "resolves() with package_path='packages/b' must NOT see "
            "packages/a/node_modules/.bin — per-package probe is isolated",
        )


# ---------------------------------------------------------------------------
# probe_command_executability with project_node_bin_dirs.
# ---------------------------------------------------------------------------


class TestProbeCommandWithNodeBinDirs(unittest.TestCase):
    """Tests for probe_command_executability(cmd, project_node_bin_dirs=[...])."""

    def setUp(self):
        self._root = _tempfile.mkdtemp()

    def tearDown(self):
        _shutil.rmtree(self._root, ignore_errors=True)

    def _make_fake_binary(self, bin_dir, name):
        _os.makedirs(bin_dir, exist_ok=True)
        path = _os.path.join(bin_dir, name)
        with open(path, "w") as fh:
            fh.write("#!/bin/sh\necho ok\n")
        _os.chmod(path, _stat.S_IRWXU)
        return path

    def test_binary_in_provided_node_bin_dirs_no_warning(self):
        """Binary in project_node_bin_dirs (not on PATH) → empty (no warning)."""
        from _configure._validators import probe_command_executability

        bin_dir = _os.path.join(self._root, "node_modules", ".bin")
        self._make_fake_binary(bin_dir, "vue-tsc-probe-fake")

        with patch("shutil.which", _make_which([])):
            result = probe_command_executability(
                "vue-tsc-probe-fake --noEmit",
                project_node_bin_dirs=[bin_dir],
            )
        self.assertEqual(result, [],
                         "binary in project_node_bin_dirs must suppress the warning")

    def test_binary_absent_from_path_and_node_bins_warns(self):
        """Binary absent from PATH and not in any provided node_bin_dirs → flagged."""
        from _configure._validators import probe_command_executability

        # Provide a real bin_dir but DON'T create the binary there.
        bin_dir = _os.path.join(self._root, "node_modules", ".bin")
        _os.makedirs(bin_dir, exist_ok=True)

        with patch("shutil.which", _make_which([])):
            result = probe_command_executability(
                "totally-absent-xyz --noEmit",
                project_node_bin_dirs=[bin_dir],
            )
        self.assertEqual(result, ["totally-absent-xyz"],
                         "truly absent binary must still be flagged")

    def test_no_node_bin_dirs_backward_compatible(self):
        """project_node_bin_dirs=None → original PATH-only behaviour (backwards compatible)."""
        from _configure._validators import probe_command_executability

        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("missing-tool --flag", project_node_bin_dirs=None)
        self.assertEqual(result, ["missing-tool"])

    def test_empty_node_bin_dirs_backward_compatible(self):
        """project_node_bin_dirs=[] → empty list is treated as no local bins."""
        from _configure._validators import probe_command_executability

        with patch("shutil.which", _make_which([])):
            result = probe_command_executability("missing-tool --flag", project_node_bin_dirs=[])
        self.assertEqual(result, ["missing-tool"])


# ---------------------------------------------------------------------------
# collect_executability_warnings with source_root.
# ---------------------------------------------------------------------------


class TestCollectWarningsWithSourceRoot(unittest.TestCase):
    """Tests for collect_executability_warnings(state, source_root=...)."""

    def setUp(self):
        self._root = _tempfile.mkdtemp()

    def tearDown(self):
        _shutil.rmtree(self._root, ignore_errors=True)

    def _make_fake_binary(self, bin_dir, name):
        _os.makedirs(bin_dir, exist_ok=True)
        path = _os.path.join(bin_dir, name)
        with open(path, "w") as fh:
            fh.write("#!/bin/sh\necho ok\n")
        _os.chmod(path, _stat.S_IRWXU)
        return path

    def _make_state(self, **kw):
        base = {
            "type_check_commands": [],
            "lint_commands": [],
            "build_commands": [],
            "package_stacks": [],
        }
        base.update(kw)
        return base

    def test_binary_in_source_root_node_modules_no_warning(self):
        """Binary in <source_root>/node_modules/.bin (not on PATH) → no warning."""
        bin_dir = _os.path.join(self._root, "node_modules", ".bin")
        self._make_fake_binary(bin_dir, "vue-tsc-warn-fake")
        state = self._make_state(type_check_commands=["vue-tsc-warn-fake --noEmit"])
        with patch("shutil.which", _make_which([])):
            warnings = collect_executability_warnings(state, source_root=self._root)
        self.assertEqual(warnings, [],
                         "binary in node_modules/.bin must suppress warning")

    def test_truly_missing_binary_still_warns(self):
        """Binary absent from PATH and node_modules/.bin → warning (unchanged)."""
        state = self._make_state(type_check_commands=["truly-absent-xyz --noEmit"])
        with patch("shutil.which", _make_which([])):
            warnings = collect_executability_warnings(state, source_root=self._root)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["missing_token"], "truly-absent-xyz")

    def test_no_source_root_falls_back_to_path_only(self):
        """source_root=None → PATH-only probe (backward compatible with existing tests)."""
        state = self._make_state(type_check_commands=["absent-tool --flag"])
        with patch("shutil.which", _make_which([])):
            warnings = collect_executability_warnings(state, source_root=None)
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["missing_token"], "absent-tool")

    def test_package_binary_in_pkg_node_modules_no_warning(self):
        """Per-package binary in <pkg>/node_modules/.bin → no warning."""
        pkg_bin_dir = _os.path.join(self._root, "packages", "frontend",
                                    "node_modules", ".bin")
        self._make_fake_binary(pkg_bin_dir, "pkg-tool-fake")
        stack = {
            "path": "packages/frontend",
            "language": "TypeScript",
            "type_check_command": "pkg-tool-fake --noEmit",
            "lint_command": None,
            "build_command": None,
        }
        state = self._make_state(package_stacks=[stack])
        with patch("shutil.which", _make_which([])):
            warnings = collect_executability_warnings(state, source_root=self._root)
        self.assertEqual(warnings, [],
                         "per-package binary in pkg node_modules/.bin must suppress warning")


if __name__ == "__main__":
    unittest.main()
