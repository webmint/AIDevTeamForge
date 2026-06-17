"""Tests for src/devforge/lib/_verify/_preflight.py.

Coverage:
  preflight_context — all-files-absent defaults, each setup-chain artefact
                      missing individually, sentinel constitution, real
                      populated constitution, Source-Root extraction,
                      wrapper-mode detection, memory.md excerpt, and the
                      CLI gate (exit 2 on unpopulated/missing constitution
                      or incomplete setup chain) via cmd_preflight.

Fixture shapes mirror tests/lib/_review/test_preflight.py (TestPreflightContext)
so the two helpers stay structurally aligned.

Real-producer round-trip: fixtures are written to temp dirs via _write()
helpers that reproduce the actual filesystem layout the real /init-forge,
/configure, /generate-docs, and /constitute commands produce. No hand-faked
strings for the sentinel check — we use the exact sentinel strings exported
from _verify._preflight._UNPOPULATED_SENTINELS.

CRITICAL: the preflight reads .devforge/memory.md (the live path per
src/CLAUDE.md References block), NOT .claude/memory/MEMORY.md.
Tests explicitly verify this invariant.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _verify._preflight import (  # noqa: E402
    _SETUP_CHAIN_ARTEFACTS,
    _UNPOPULATED_SENTINELS,
    preflight_context,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_full_install(td: str) -> None:
    """Write a minimal but complete 4-command setup-chain install into td.

    Files created:
      constitution.md               — populated (no sentinels)
      CLAUDE.md                     — minimal CLAUDE.md with Source Root
      .devforge/project-config.json — /configure output stub
      .devforge/index.json          — /generate-docs output stub
      .devforge/memory.md           — memory file (live path, NOT .claude/memory/)

    All paths are exactly what the real commands produce (no invented names).
    """
    _write(td, "constitution.md",
           "# Architecture Rules\n\n1. Use dependency injection.\n2. No globals.\n")
    _write(td, "CLAUDE.md",
           "# CLAUDE.md\n\n"
           "- **Name**: TestProject\n"
           "- **Type**: web-app\n"
           "- **Frameworks**: Django\n"
           "- **Languages**: Python\n"
           "- **Project Root**: src/backend\n")
    _write(td, ".devforge/project-config.json",
           json.dumps({"configure_version": 1}))
    _write(td, ".devforge/index.json",
           json.dumps({"version": 1, "packages": []}))
    _write(td, ".devforge/memory.md",
           "- [Lesson 1](lesson_1.md)\n- [Lesson 2](lesson_2.md)\n")


def _write(td: str, rel_path: str, content: str) -> str:
    """Write content to td/rel_path, creating parent dirs."""
    full = os.path.join(td, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return full


# ---------------------------------------------------------------------------
# TestSentinelSet — verify the exported sentinel set matches _audit's
# ---------------------------------------------------------------------------

class TestSentinelSet(unittest.TestCase):
    """Ensure _verify uses the same sentinel set as _audit and _review (parity requirement)."""

    def test_sentinel_set_is_nonempty(self):
        self.assertGreater(len(_UNPOPULATED_SENTINELS), 0)

    def test_constitution_body_sentinel_present(self):
        self.assertIn("{{CONSTITUTION_BODY}}", _UNPOPULATED_SENTINELS)

    def test_run_constitute_backtick_sentinel_present(self):
        # The sentinel as it appears in the unpopulated template.
        self.assertIn("Run `/constitute`", _UNPOPULATED_SENTINELS)

    def test_run_constitute_to_populate_sentinel_present(self):
        self.assertIn("Run /constitute to populate", _UNPOPULATED_SENTINELS)

    def test_sentinel_parity_with_audit(self):
        """The sentinel tuple must match _audit._preflight._UNPOPULATED_SENTINELS."""
        from _audit._preflight import _UNPOPULATED_SENTINELS as audit_sentinels
        self.assertEqual(
            set(_UNPOPULATED_SENTINELS),
            set(audit_sentinels),
            msg=(
                "_verify sentinels diverge from _audit sentinels. "
                "Keep them in sync so all helpers enforce the same gate."
            ),
        )

    def test_sentinel_parity_with_review(self):
        """The sentinel tuple must also match _review._preflight._UNPOPULATED_SENTINELS."""
        from _review._preflight import _UNPOPULATED_SENTINELS as review_sentinels
        self.assertEqual(
            set(_UNPOPULATED_SENTINELS),
            set(review_sentinels),
            msg=(
                "_verify sentinels diverge from _review sentinels. "
                "Keep all three helpers in sync."
            ),
        )


# ---------------------------------------------------------------------------
# TestSetupChainArtefacts — verify the artefact list
# ---------------------------------------------------------------------------

class TestSetupChainArtefacts(unittest.TestCase):
    def test_four_artefacts_defined(self):
        self.assertEqual(len(_SETUP_CHAIN_ARTEFACTS), 4)

    def test_constitution_in_artefacts(self):
        paths = [p for p, _ in _SETUP_CHAIN_ARTEFACTS]
        self.assertIn("constitution.md", paths)

    def test_claude_md_in_artefacts(self):
        paths = [p for p, _ in _SETUP_CHAIN_ARTEFACTS]
        self.assertIn("CLAUDE.md", paths)

    def test_project_config_in_artefacts(self):
        paths = [p for p, _ in _SETUP_CHAIN_ARTEFACTS]
        self.assertIn(".devforge/project-config.json", paths)

    def test_index_json_in_artefacts(self):
        paths = [p for p, _ in _SETUP_CHAIN_ARTEFACTS]
        self.assertIn(".devforge/index.json", paths)


# ---------------------------------------------------------------------------
# TestPreflightContext — pure function
# ---------------------------------------------------------------------------

class TestPreflightContext(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.td)

    # --- No files ---

    def test_no_files_returns_sane_defaults(self):
        r = preflight_context(self.td)
        self.assertFalse(r["constitution_present"])
        self.assertFalse(r["constitution_populated"])
        self.assertFalse(r["setup_chain_ok"])
        self.assertFalse(r["claude_md_present"])
        self.assertFalse(r["memory_present"])
        self.assertEqual(r["memory_excerpt"], "")
        self.assertEqual(r["source_root"], ".")
        self.assertFalse(r["wrapper_mode"])
        self.assertEqual(r["project_type"], "")
        self.assertEqual(r["framework"], "")
        self.assertEqual(r["language"], "")

    def test_no_files_missing_artefacts_contains_all_four(self):
        r = preflight_context(self.td)
        labels = r["missing_artefacts"]
        self.assertEqual(len(labels), 4)

    def test_nonexistent_workspace_no_raise(self):
        r = preflight_context(os.path.join(self.td, "does_not_exist"))
        self.assertFalse(r["constitution_present"])
        self.assertFalse(r["setup_chain_ok"])

    # --- Full install (all artefacts present) ---

    def test_full_install_passes_all_checks(self):
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertTrue(r["constitution_present"])
        self.assertTrue(r["constitution_populated"])
        self.assertTrue(r["setup_chain_ok"])
        self.assertEqual(r["missing_artefacts"], [])
        self.assertTrue(r["claude_md_present"])

    def test_full_install_source_root_extracted(self):
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertEqual(r["source_root"], "src/backend")

    def test_full_install_project_type_extracted(self):
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertEqual(r["project_type"], "web-app")

    def test_full_install_framework_extracted(self):
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertEqual(r["framework"], "Django")

    def test_full_install_language_extracted(self):
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertEqual(r["language"], "Python")

    # --- Memory: .devforge/memory.md (live path) ---

    def test_full_install_memory_present(self):
        """Reads .devforge/memory.md — the live path."""
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertTrue(r["memory_present"])
        self.assertIn("Lesson 1", r["memory_excerpt"])

    def test_devforge_memory_md_is_read(self):
        """Explicit test: .devforge/memory.md present → memory_present=True."""
        _write(self.td, ".devforge/memory.md", "- Session note.\n")
        r = preflight_context(self.td)
        self.assertTrue(r["memory_present"])
        self.assertIn("Session note", r["memory_excerpt"])

    def test_stale_claude_memory_path_is_NOT_consulted(self):
        """Explicit test: only .claude/memory/MEMORY.md present → memory_present=False.

        The stale path (.claude/memory/MEMORY.md) must NOT be read.
        Only .devforge/memory.md is the live path.
        """
        # Write the stale path ONLY — do NOT write .devforge/memory.md.
        _write(self.td, ".claude/memory/MEMORY.md",
               "- Stale memory entry.\n")
        r = preflight_context(self.td)
        # The preflight must NOT detect the stale path.
        self.assertFalse(r["memory_present"])
        self.assertEqual(r["memory_excerpt"], "")

    def test_memory_present_and_excerpt_capped_at_40_lines(self):
        mem_content = "\n".join(
            ["Line {0}".format(i) for i in range(60)]
        ) + "\n"
        _write(self.td, ".devforge/memory.md", mem_content)
        r = preflight_context(self.td)
        self.assertTrue(r["memory_present"])
        lines = r["memory_excerpt"].splitlines()
        self.assertLessEqual(len(lines), 40)

    def test_memory_absent(self):
        r = preflight_context(self.td)
        self.assertFalse(r["memory_present"])
        self.assertEqual(r["memory_excerpt"], "")

    # --- Constitution sentinel checks (real sentinel strings from the module) ---

    def test_constitution_with_body_sentinel_unpopulated(self):
        # Use the exact sentinel string exported from the module.
        _write(self.td, "constitution.md",
               "This file contains {0} placeholder.".format(_UNPOPULATED_SENTINELS[0]))
        r = preflight_context(self.td)
        self.assertTrue(r["constitution_present"])
        self.assertFalse(r["constitution_populated"])

    def test_constitution_with_run_constitute_sentinel_unpopulated(self):
        _write(self.td, "constitution.md",
               "{0} to populate this file.".format(_UNPOPULATED_SENTINELS[1]))
        r = preflight_context(self.td)
        self.assertTrue(r["constitution_present"])
        self.assertFalse(r["constitution_populated"])

    def test_constitution_with_populate_sentinel_unpopulated(self):
        _write(self.td, "constitution.md",
               "{0} — see instructions.".format(_UNPOPULATED_SENTINELS[2]))
        r = preflight_context(self.td)
        self.assertTrue(r["constitution_present"])
        self.assertFalse(r["constitution_populated"])

    def test_constitution_with_real_content_populated(self):
        _write(self.td, "constitution.md",
               "# Architecture Rules\n\n1. Use dependency injection.\n")
        r = preflight_context(self.td)
        self.assertTrue(r["constitution_present"])
        self.assertTrue(r["constitution_populated"])

    def test_constitution_absent(self):
        r = preflight_context(self.td)
        self.assertFalse(r["constitution_present"])
        self.assertFalse(r["constitution_populated"])

    # --- Each setup-chain artefact missing individually ---

    def test_missing_constitution_flagged(self):
        _make_full_install(self.td)
        os.unlink(os.path.join(self.td, "constitution.md"))
        r = preflight_context(self.td)
        self.assertFalse(r["setup_chain_ok"])
        labels = r["missing_artefacts"]
        self.assertIn("/constitute", labels)

    def test_missing_claude_md_flagged(self):
        _make_full_install(self.td)
        os.unlink(os.path.join(self.td, "CLAUDE.md"))
        r = preflight_context(self.td)
        self.assertFalse(r["setup_chain_ok"])
        self.assertIn("/init-forge", r["missing_artefacts"])

    def test_missing_project_config_flagged(self):
        _make_full_install(self.td)
        os.unlink(os.path.join(self.td, ".devforge", "project-config.json"))
        r = preflight_context(self.td)
        self.assertFalse(r["setup_chain_ok"])
        self.assertIn("/configure", r["missing_artefacts"])

    def test_missing_index_json_flagged(self):
        _make_full_install(self.td)
        os.unlink(os.path.join(self.td, ".devforge", "index.json"))
        r = preflight_context(self.td)
        self.assertFalse(r["setup_chain_ok"])
        self.assertIn("/generate-docs", r["missing_artefacts"])

    def test_three_missing_artefacts_lists_three(self):
        # Only write constitution.md.
        _write(self.td, "constitution.md",
               "# Rules\n\n1. Use DI.\n")
        r = preflight_context(self.td)
        self.assertFalse(r["setup_chain_ok"])
        self.assertEqual(len(r["missing_artefacts"]), 3)

    # --- CLAUDE.md extraction ---

    def test_claude_md_present(self):
        _write(self.td, "CLAUDE.md", "# Project\n\nSome content.\n")
        r = preflight_context(self.td)
        self.assertTrue(r["claude_md_present"])

    def test_source_root_extraction_project_root(self):
        _write(self.td, "CLAUDE.md",
               "- **Project Root**: src/backend\n")
        r = preflight_context(self.td)
        self.assertEqual(r["source_root"], "src/backend")

    def test_source_root_extraction_source_root_label(self):
        _write(self.td, "CLAUDE.md",
               "- **Source Root**: frontend/src\n")
        r = preflight_context(self.td)
        self.assertEqual(r["source_root"], "frontend/src")

    def test_source_root_default_when_absent(self):
        _write(self.td, "CLAUDE.md", "# Minimal CLAUDE.md\n")
        r = preflight_context(self.td)
        self.assertEqual(r["source_root"], ".")

    # --- Wrapper-mode detection ---

    def test_wrapper_mode_false_by_default(self):
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertFalse(r["wrapper_mode"])

    def test_wrapper_mode_detected_from_claude_md(self):
        _write(self.td, "CLAUDE.md",
               "# CLAUDE.md\n\n"
               "**Wrapper mode**: the source root is a subdirectory.\n"
               "- **Source Root**: myapp/\n")
        r = preflight_context(self.td)
        self.assertTrue(r["wrapper_mode"])

    def test_wrapper_root_label_triggers_wrapper_mode(self):
        _write(self.td, "CLAUDE.md",
               "- Wrapper root: /Users/me/myapp\n")
        r = preflight_context(self.td)
        self.assertTrue(r["wrapper_mode"])

    # --- Result keyset ---

    def test_result_has_all_expected_keys(self):
        r = preflight_context(self.td)
        expected_keys = {
            "constitution_present", "constitution_populated",
            "setup_chain_ok", "missing_artefacts",
            "source_root", "wrapper_mode",
            "project_type", "framework", "language",
            "claude_md_present", "memory_present", "memory_excerpt",
        }
        self.assertEqual(set(r.keys()), expected_keys)


# ---------------------------------------------------------------------------
# TestMemoryPathInvariant — explicit source-level verification
# ---------------------------------------------------------------------------

class TestMemoryPathInvariant(unittest.TestCase):
    """Verify the preflight module reads .devforge/memory.md, not .claude/memory."""

    def test_preflight_module_contains_devforge_memory_path(self):
        """The source of _preflight.py must reference .devforge/memory.md."""
        preflight_path = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "_verify" / "_preflight.py"
        )
        with open(str(preflight_path), "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn(".devforge/memory.md", source,
                      "preflight must read .devforge/memory.md")

    def test_preflight_module_does_not_contain_stale_claude_memory_path(self):
        """The source of _preflight.py must NOT reference .claude/memory/MEMORY.md."""
        preflight_path = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "_verify" / "_preflight.py"
        )
        with open(str(preflight_path), "r", encoding="utf-8") as fh:
            source = fh.read()
        # The stale path must not appear anywhere (including comments or strings).
        self.assertNotIn(
            ".claude/memory",
            source,
            "preflight must NOT reference the stale .claude/memory path (finding F)",
        )


# ---------------------------------------------------------------------------
# TestCmdPreflight — CLI handler exit codes via _cli.main
# ---------------------------------------------------------------------------

class TestCmdPreflight(unittest.TestCase):
    """Verify the CLI gate behaviour (exit 2 on missing artefacts / sentinels)."""

    def setUp(self):
        self.td = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.td)

    def _run_preflight(self, workspace_root):
        """Run verify_helper preflight and return (exit_code, stdout_text)."""
        import io
        from contextlib import redirect_stdout, redirect_stderr
        from _verify._cli import main

        buf = io.StringIO()
        err = io.StringIO()
        try:
            with redirect_stdout(buf), redirect_stderr(err):
                code = main(["preflight", "--workspace-root", workspace_root])
        except SystemExit as exc:
            code = exc.code
        return code, buf.getvalue()

    def test_full_install_exits_0(self):
        _make_full_install(self.td)
        code, out = self._run_preflight(self.td)
        self.assertEqual(code, 0, msg="Expected exit 0 for full install, got {0}".format(code))
        data = json.loads(out)
        self.assertTrue(data["setup_chain_ok"])
        self.assertTrue(data["constitution_populated"])

    def test_missing_setup_chain_exits_2(self):
        # Only write constitution.md — setup chain incomplete.
        _write(self.td, "constitution.md",
               "# Rules\n\n1. Use DI.\n")
        code, _ = self._run_preflight(self.td)
        self.assertEqual(code, 2)

    def test_sentinel_constitution_exits_2(self):
        # Full setup chain present but constitution has sentinel.
        _make_full_install(self.td)
        # Overwrite constitution with a sentinel.
        _write(self.td, "constitution.md",
               "{0}".format(_UNPOPULATED_SENTINELS[0]))
        code, _ = self._run_preflight(self.td)
        self.assertEqual(code, 2)

    def test_absent_constitution_triggers_setup_chain_gate_exits_2(self):
        # constitution.md is in _SETUP_CHAIN_ARTEFACTS, so its absence fires
        # the setup-chain gate, not a dedicated constitution-present gate.
        _make_full_install(self.td)
        os.unlink(os.path.join(self.td, "constitution.md"))
        code, _ = self._run_preflight(self.td)
        self.assertEqual(code, 2)

    def test_output_is_always_json(self):
        """Even when exit 2, stdout must contain JSON (orchestrator reads it)."""
        code, out = self._run_preflight(self.td)
        self.assertEqual(code, 2)  # empty workspace → setup chain incomplete
        data = json.loads(out)
        self.assertIn("setup_chain_ok", data)
        self.assertIn("missing_artefacts", data)

    def test_stderr_names_verify_helper(self):
        """Error messages must name verify_helper (not review_helper)."""
        import io
        from contextlib import redirect_stdout, redirect_stderr
        from _verify._cli import main

        buf = io.StringIO()
        err = io.StringIO()
        try:
            with redirect_stdout(buf), redirect_stderr(err):
                main(["preflight", "--workspace-root", self.td])
        except SystemExit:
            pass
        self.assertIn("verify_helper", err.getvalue())


# ---------------------------------------------------------------------------
# TestCmdCheckStatusAndFlip — CLI handler for check-status-and-flip
# ---------------------------------------------------------------------------

class TestCmdCheckStatusAndFlip(unittest.TestCase):
    """Smoke-test the check-status-and-flip verb through the CLI."""

    def setUp(self):
        self.td = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.td)

    def _run(self, argv):
        import io
        from contextlib import redirect_stdout, redirect_stderr
        from _verify._cli import main

        buf = io.StringIO()
        err = io.StringIO()
        try:
            with redirect_stdout(buf), redirect_stderr(err):
                code = main(argv)
        except SystemExit as exc:
            code = exc.code
        return code, buf.getvalue(), err.getvalue()

    def test_read_only_absent_state_returns_defaults(self):
        code, out, _ = self._run(
            ["check-status-and-flip", "--feature-dir", self.td]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["phase"], "")
        self.assertEqual(data["status"], "in_progress")

    def test_flip_phase_writes_and_returns_new_state(self):
        code, out, _ = self._run([
            "check-status-and-flip",
            "--feature-dir", self.td,
            "--to", "preflight",
        ])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["phase"], "preflight")

    def test_flip_phase_with_status_complete(self):
        code, out, _ = self._run([
            "check-status-and-flip",
            "--feature-dir", self.td,
            "--to", "9",
            "--status", "complete",
        ])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["phase"], "9")
        self.assertEqual(data["status"], "complete")

    def test_empty_to_phase_exits_2(self):
        code, _, err = self._run([
            "check-status-and-flip",
            "--feature-dir", self.td,
            "--to", "",
        ])
        self.assertEqual(code, 2)
        self.assertIn("verify_helper check-status-and-flip", err)

    def test_state_file_is_verify_state_json(self):
        """The state file must be named verify-state.json in the feature dir."""
        code, _, _ = self._run([
            "check-status-and-flip",
            "--feature-dir", self.td,
            "--to", "1",
        ])
        self.assertEqual(code, 0)
        expected_file = os.path.join(self.td, "verify-state.json")
        self.assertTrue(os.path.exists(expected_file),
                        "verify-state.json must exist after flip")
        # review-state.json must NOT be created
        stale_file = os.path.join(self.td, "review-state.json")
        self.assertFalse(os.path.exists(stale_file),
                         "review-state.json must NOT be created by verify_helper")


# ---------------------------------------------------------------------------
# TestLauncherSmoke — import + help
# ---------------------------------------------------------------------------

class TestLauncherSmoke(unittest.TestCase):
    """Verify the CLI entry point parses --help without errors."""

    def test_help_exits_cleanly(self):
        from _verify._cli import main
        with self.assertRaises(SystemExit) as ctx:
            main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_no_subcommand_exits_2(self):
        from _verify._cli import main
        code = main([])
        self.assertEqual(code, 2)

    def test_check_status_and_flip_help_exits_0(self):
        from _verify._cli import main
        with self.assertRaises(SystemExit) as ctx:
            main(["check-status-and-flip", "--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_preflight_help_exits_0(self):
        from _verify._cli import main
        with self.assertRaises(SystemExit) as ctx:
            main(["preflight", "--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_registry_has_expected_verbs(self):
        """Phase 1: 2; Phase 2: +4 = 6; Phase 4: +2 = 8; Phase 5: +5 = 13 total."""
        from _verify._cli import _SUBCOMMAND_REGISTRY
        self.assertEqual(len(_SUBCOMMAND_REGISTRY), 13)

    def test_registry_verb_names(self):
        """F5: all 13 verb names must be present — a count-only assertion misses swaps."""
        from _verify._cli import _SUBCOMMAND_REGISTRY
        verbs = {v for v, _, _ in _SUBCOMMAND_REGISTRY}
        expected = {
            "check-status-and-flip",
            "preflight",
            "resolve-feature-scope",
            "read-ac-config",
            "parse-acs",
            "read-review-findings",
            "merge-ac-results",
            "check-hygiene",
            # Phase 5 verbs:
            "compute-verdict",
            "render-report",
            "render-inline-summary",
            "flip-spec-status",
            "file-bugs",
        }
        self.assertEqual(verbs, expected,
                         msg="Registry verb set mismatch — a verb was added, removed, or renamed")


if __name__ == "__main__":
    unittest.main()
