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


if __name__ == "__main__":
    unittest.main()
