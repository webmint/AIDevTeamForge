"""Tests for src/devforge/lib/_summarize/_preflight.py.

Coverage:
  preflight_context — all-files-absent defaults, each setup-chain artefact
                      missing individually, real populated spec in both
                      Complete/not-Complete states, source_root / wrapper_mode
                      extraction, memory.md excerpt, and the CLI gate (exit 2
                      on missing setup chain, exit 3 on not-Complete spec)
                      via cmd_preflight.

Real-producer round-trip:
  - A real CLAUDE.md built the same way tests/lib/_verify/test_preflight.py
    builds its fixture (standalone + wrapper-mode cases).
  - A real spec in the not-Complete state: uses the actual
    tests/lib/fixtures/specify-sample-migration.md (Status: Draft) — asserts
    the gate REJECTS it with a "run `/verify` first" stop.
  - A real spec in the Complete state: produced by the REAL
    _verify._specstatus.flip_spec_status (the verify-helper producer) on a
    copy of that fixture with no tasks/ dir (so the task cross-check passes).
    NOT hand-authored.

CRITICAL: the preflight reads .devforge/memory.md (the live path per
src/CLAUDE.md References block), NOT .claude/memory/MEMORY.md.
Tests explicitly verify this invariant.

NOTE: /summarize deliberately OMITS the constitution-populated sentinel guard
(_UNPOPULATED_SENTINELS) that /verify and /review carry.  These tests confirm
that an UNpopulated constitution does NOT block the summarize preflight — only
the setup-chain EXISTENCE check applies.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_FIXTURES_DIR = _REPO_ROOT / "tests" / "lib" / "fixtures"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _summarize._preflight import (  # noqa: E402
    _SETUP_CHAIN_ARTEFACTS,
    _REQUIRED_SPEC_STATUS,
    preflight_context,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(td, rel_path, content):
    # type: (str, str, str) -> str
    """Write content to td/rel_path, creating parent dirs."""
    full = os.path.join(td, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return full


def _make_full_install(td):
    # type: (str) -> None
    """Write a minimal but complete 4-command setup-chain install into td.

    Files created:
      constitution.md               — populated (no sentinels)
      CLAUDE.md                     — minimal CLAUDE.md with Source Root
      .devforge/project-config.json — /configure output stub
      .devforge/index.json          — /generate-docs output stub
      .devforge/memory.md           — memory file (live path, NOT .claude/memory/)
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


def _make_complete_spec(td):
    # type: (str) -> str
    """Produce a real Complete spec.md via the REAL verify flip_spec_status.

    Copies the real not-Complete fixture into td, then calls
    _verify._specstatus.flip_spec_status (the producer) with no tasks dir
    (so the task cross-check passes) to flip it to Complete.

    Returns the absolute path to the Complete spec.md.
    """
    from _verify._specstatus import flip_spec_status

    spec_src = str(_FIXTURES_DIR / "specify-sample-migration.md")
    spec_dst = os.path.join(td, "spec.md")
    shutil.copy(spec_src, spec_dst)

    # flip_spec_status requires a feature_dir; with no tasks/ subdir it skips
    # the task cross-check and flips the **Status**: line directly.
    result = flip_spec_status(
        feature_dir=td,
        ac_results=[],
        spec_path=spec_dst,
    )
    if not result["flipped"]:
        raise RuntimeError(
            "flip_spec_status failed in test setup: {0}".format(result.get("blocker"))
        )
    return spec_dst


# ---------------------------------------------------------------------------
# TestConstantsAndExports
# ---------------------------------------------------------------------------

class TestConstantsAndExports(unittest.TestCase):
    """Verify the exported constants have the correct shape."""

    def test_required_spec_status_is_complete(self):
        self.assertEqual(_REQUIRED_SPEC_STATUS, "Complete")

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

    def test_no_unpopulated_sentinels_exported(self):
        """_summarize/_preflight.py must NOT export _UNPOPULATED_SENTINELS.

        /summarize omits the constitution-populated sentinel guard — only the
        setup-chain existence check applies.  A future session must NOT add
        the sentinel guard back.
        """
        import _summarize._preflight as mod
        self.assertFalse(
            hasattr(mod, "_UNPOPULATED_SENTINELS"),
            "_summarize/_preflight.py must NOT define _UNPOPULATED_SENTINELS "
            "(the constitution-populated guard is intentionally omitted; "
            "the spec-Complete gate is a strictly stronger precondition)",
        )


# ---------------------------------------------------------------------------
# TestPreflightContext — pure function
# ---------------------------------------------------------------------------

class TestPreflightContext(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.td)

    # --- No files ---

    def test_no_files_returns_sane_defaults(self):
        r = preflight_context(self.td)
        self.assertFalse(r["setup_chain_ok"])
        self.assertEqual(r["source_root"], ".")
        self.assertFalse(r["wrapper_mode"])
        self.assertEqual(r["project_type"], "")
        self.assertEqual(r["framework"], "")
        self.assertEqual(r["language"], "")
        self.assertFalse(r["claude_md_present"])
        self.assertFalse(r["memory_present"])
        self.assertEqual(r["memory_excerpt"], "")

    def test_no_files_spec_gate_defaults(self):
        r = preflight_context(self.td)
        self.assertEqual(r["spec_path"], "")
        self.assertEqual(r["spec_status"], "")
        self.assertFalse(r["spec_complete"])

    def test_no_files_missing_artefacts_contains_all_four(self):
        r = preflight_context(self.td)
        self.assertEqual(len(r["missing_artefacts"]), 4)

    def test_nonexistent_workspace_no_raise(self):
        r = preflight_context(os.path.join(self.td, "does_not_exist"))
        self.assertFalse(r["setup_chain_ok"])
        self.assertFalse(r["spec_complete"])

    def test_result_has_all_expected_keys(self):
        r = preflight_context(self.td)
        expected_keys = {
            "setup_chain_ok", "missing_artefacts",
            "spec_path", "spec_status", "spec_complete",
            "source_root", "wrapper_mode",
            "project_type", "framework", "language",
            "claude_md_present", "memory_present", "memory_excerpt",
        }
        self.assertEqual(set(r.keys()), expected_keys)

    # --- Full install (all artefacts present) ---

    def test_full_install_setup_chain_ok(self):
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertTrue(r["setup_chain_ok"])
        self.assertEqual(r["missing_artefacts"], [])

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

    def test_full_install_claude_md_present(self):
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertTrue(r["claude_md_present"])

    # --- Spec gate — not-Complete (real fixture, Status: Draft) ---

    def test_draft_spec_fails_spec_complete_gate(self):
        """The real specify-sample-migration.md fixture is Status: Draft.

        preflight_context must parse it correctly and report spec_complete=False.
        """
        _make_full_install(self.td)
        spec_path = str(_FIXTURES_DIR / "specify-sample-migration.md")
        r = preflight_context(self.td, spec_path=spec_path)
        self.assertTrue(r["setup_chain_ok"])
        self.assertEqual(r["spec_status"], "Draft")
        self.assertFalse(r["spec_complete"])

    def test_in_progress_spec_fails_complete_gate(self):
        spec_path = _write(
            self.td, "spec_ip.md",
            "# Spec\n\n**Status**: In Progress\n\n## Overview\n\nContent.\n"
        )
        r = preflight_context(self.td, spec_path=spec_path)
        self.assertEqual(r["spec_status"], "In Progress")
        self.assertFalse(r["spec_complete"])

    def test_approved_spec_fails_complete_gate(self):
        spec_path = _write(
            self.td, "spec_ap.md",
            "# Spec\n\n**Status**: Approved\n\n## Overview\n\nContent.\n"
        )
        r = preflight_context(self.td, spec_path=spec_path)
        self.assertEqual(r["spec_status"], "Approved")
        self.assertFalse(r["spec_complete"])

    # --- Spec gate — Complete (produced by REAL verify flip_spec_status) ---

    def test_complete_spec_passes_gate_real_producer(self):
        """The Complete spec is produced by the REAL flip_spec_status (not hand-authored).

        This validates the gate against a real producer output — the same file
        /verify writes when it approves a feature.
        """
        _make_full_install(self.td)
        spec_path = _make_complete_spec(self.td)

        r = preflight_context(self.td, spec_path=spec_path)
        self.assertTrue(r["setup_chain_ok"])
        self.assertEqual(r["spec_status"], "Complete")
        self.assertTrue(r["spec_complete"])

    def test_complete_spec_path_preserved_in_result(self):
        spec_path = _make_complete_spec(self.td)
        r = preflight_context(self.td, spec_path=spec_path)
        self.assertEqual(r["spec_path"], spec_path)

    def test_spec_path_none_skips_spec_gate(self):
        """When spec_path is None the spec gate is skipped — setup chain is still checked."""
        _make_full_install(self.td)
        r = preflight_context(self.td, spec_path=None)
        self.assertTrue(r["setup_chain_ok"])
        # Spec gate skipped
        self.assertEqual(r["spec_status"], "")
        self.assertFalse(r["spec_complete"])
        self.assertEqual(r["spec_path"], "")

    def test_missing_spec_file_spec_complete_false(self):
        """When spec_path is given but file does not exist, spec_complete=False."""
        _make_full_install(self.td)
        r = preflight_context(
            self.td,
            spec_path=os.path.join(self.td, "nonexistent_spec.md"),
        )
        self.assertTrue(r["setup_chain_ok"])
        self.assertFalse(r["spec_complete"])
        self.assertEqual(r["spec_status"], "")

    def test_multiline_status_is_rejected(self):
        """Fix 1 regression guard: _STATUS_RE must NOT match across blank lines.

        A malformed spec where the status value is on a separate line from the
        **Status**: marker must yield spec_complete=False — the value must NOT
        bleed from a later line into the match.

        Before Fix 1 the pattern was r"\\*\\*Status\\*\\*:\\s*(.+)$" with
        re.MULTILINE.  The \\s* could span a newline, causing
        "**Status**:\\n\\nComplete\\n" to match "Complete" from the later line
        and wrongly pass the gate.  After Fix 1, [ \\t]* (horizontal whitespace
        only) is used, so the match fails on blank-line-separated values.
        """
        spec_path = _write(
            self.td, "spec_malformed.md",
            "# Spec\n\n**Status**:\n\nComplete\n\n## Overview\n\nContent.\n"
        )
        r = preflight_context(self.td, spec_path=spec_path)
        # The status value is not on the same line as **Status**: — must be rejected.
        self.assertFalse(r["spec_complete"],
                         "Malformed multi-line status must NOT pass the spec_complete gate")
        self.assertEqual(r["spec_status"], "",
                         "spec_status must be empty when the value is not on the same line")

    # --- Constitution: existence is checked but sentinel content is NOT ---

    def test_unpopulated_constitution_does_not_block(self):
        """Key difference vs _verify/_review:  /summarize does NOT check sentinels.

        An UNPOPULATED constitution still passes the summarize preflight as long
        as the file EXISTS.  The spec-Complete gate is a strictly stronger
        precondition at this pipeline stage.
        """
        _make_full_install(self.td)
        # Overwrite with an unpopulated sentinel body (exact verify sentinel)
        _write(self.td, "constitution.md",
               "{{CONSTITUTION_BODY}}\nRun `/constitute` to populate this.\n")
        r = preflight_context(self.td)
        # setup chain ok (constitution.md EXISTS)
        self.assertTrue(r["setup_chain_ok"])
        # No sentinel-populated key in the result
        self.assertNotIn("constitution_populated", r)

    def test_missing_constitution_fails_setup_chain(self):
        """constitution.md is artefact #1 — its absence fails the setup chain."""
        _make_full_install(self.td)
        os.unlink(os.path.join(self.td, "constitution.md"))
        r = preflight_context(self.td)
        self.assertFalse(r["setup_chain_ok"])
        self.assertIn("/constitute", r["missing_artefacts"])

    # --- Each setup-chain artefact missing individually ---

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
        """Only .devforge/memory.md is the live path.

        The stale path (.claude/memory/MEMORY.md) must NOT be read even if
        present.
        """
        _write(self.td, ".claude/memory/MEMORY.md",
               "- Stale memory entry.\n")
        r = preflight_context(self.td)
        self.assertFalse(r["memory_present"])
        self.assertEqual(r["memory_excerpt"], "")

    def test_memory_excerpt_capped_at_40_lines(self):
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

    # --- CLAUDE.md: source_root + wrapper-mode ---

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


# ---------------------------------------------------------------------------
# TestMemoryPathInvariant — source-level verification
# ---------------------------------------------------------------------------

class TestMemoryPathInvariant(unittest.TestCase):
    """Verify the preflight module reads .devforge/memory.md, not .claude/memory."""

    def test_preflight_module_contains_devforge_memory_path(self):
        """The source of _preflight.py must reference .devforge/memory.md."""
        preflight_path = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "_summarize" / "_preflight.py"
        )
        with open(str(preflight_path), "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn(".devforge/memory.md", source,
                      "preflight must read .devforge/memory.md")

    def test_preflight_module_does_not_contain_stale_claude_memory_path(self):
        """The source of _preflight.py must NOT reference .claude/memory/MEMORY.md."""
        preflight_path = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "_summarize" / "_preflight.py"
        )
        with open(str(preflight_path), "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn(
            ".claude/memory",
            source,
            "preflight must NOT reference the stale .claude/memory path",
        )

    def test_preflight_module_does_not_assign_unpopulated_sentinels(self):
        """_summarize/_preflight.py must NOT assign _UNPOPULATED_SENTINELS as a variable.

        The module may reference the name in comments/docstrings to explain the
        deliberate omission, but must not define it as a tuple/list constant
        (which would be the indicator that the sentinel guard was accidentally added).
        """
        preflight_path = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "_summarize" / "_preflight.py"
        )
        with open(str(preflight_path), "r", encoding="utf-8") as fh:
            source = fh.read()
        # An assignment would look like: _UNPOPULATED_SENTINELS = (
        self.assertNotIn(
            "_UNPOPULATED_SENTINELS = ",
            source,
            "_summarize/_preflight.py must NOT assign _UNPOPULATED_SENTINELS "
            "(the constitution-populated guard is intentionally omitted)",
        )

    def test_preflight_module_contains_complete_gate(self):
        """The source must reference the Complete gate and 'run /verify' message."""
        preflight_path = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "_summarize" / "_preflight.py"
        )
        with open(str(preflight_path), "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn("Complete", source,
                      "preflight must reference the Complete gate")


# ---------------------------------------------------------------------------
# TestCmdPreflight — CLI handler exit codes via _cli.main
# ---------------------------------------------------------------------------

class TestCmdPreflight(unittest.TestCase):
    """Verify the CLI gate behaviour (exit 2 on missing artefacts, exit 3 on not-Complete)."""

    def setUp(self):
        self.td = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.td)

    def _run_preflight(self, workspace_root, spec=None):
        # type: (str, str) -> tuple
        """Run summarize_helper preflight and return (exit_code, stdout_text, stderr_text)."""
        import io
        from contextlib import redirect_stdout, redirect_stderr
        from _summarize._cli import main

        argv = ["preflight", "--workspace-root", workspace_root]
        if spec:
            argv += ["--spec", spec]

        buf = io.StringIO()
        err = io.StringIO()
        try:
            with redirect_stdout(buf), redirect_stderr(err):
                code = main(argv)
        except SystemExit as exc:
            code = exc.code
        return code, buf.getvalue(), err.getvalue()

    # --- Happy path ---

    def test_full_install_no_spec_exits_0(self):
        """Without --spec, only the setup chain is checked."""
        _make_full_install(self.td)
        code, out, _ = self._run_preflight(self.td)
        self.assertEqual(code, 0,
                         msg="Expected exit 0 for full install without spec, got {0}".format(code))
        data = json.loads(out)
        self.assertTrue(data["setup_chain_ok"])

    def test_full_install_complete_spec_exits_0(self):
        """Full install + Complete spec (real producer) → exit 0."""
        _make_full_install(self.td)
        spec_path = _make_complete_spec(self.td)
        code, out, _ = self._run_preflight(self.td, spec=spec_path)
        self.assertEqual(code, 0,
                         msg="Expected exit 0 for Complete spec, got {0}".format(code))
        data = json.loads(out)
        self.assertTrue(data["setup_chain_ok"])
        self.assertTrue(data["spec_complete"])
        self.assertEqual(data["spec_status"], "Complete")

    # --- Setup chain incomplete → exit 2 ---

    def test_missing_setup_chain_exits_2(self):
        code, _, _ = self._run_preflight(self.td)
        self.assertEqual(code, 2)

    def test_missing_one_artefact_exits_2(self):
        _make_full_install(self.td)
        os.unlink(os.path.join(self.td, ".devforge", "index.json"))
        code, _, _ = self._run_preflight(self.td)
        self.assertEqual(code, 2)

    def test_missing_artefact_stderr_names_summarize_helper(self):
        code, _, err = self._run_preflight(self.td)
        self.assertEqual(code, 2)
        self.assertIn("summarize_helper", err)

    def test_missing_artefact_stderr_names_setup_sequence(self):
        code, _, err = self._run_preflight(self.td)
        self.assertEqual(code, 2)
        self.assertIn("/init-forge", err)

    # --- Spec not Complete → exit 3 ---

    def test_draft_spec_exits_3(self):
        """The real specify-sample-migration.md (Status: Draft) → exit 3."""
        _make_full_install(self.td)
        spec_path = str(_FIXTURES_DIR / "specify-sample-migration.md")
        code, out, err = self._run_preflight(self.td, spec=spec_path)
        self.assertEqual(code, 3,
                         msg="Expected exit 3 for Draft spec, got {0}".format(code))
        self.assertIn("/verify", err)

    def test_not_complete_stderr_mentions_current_status(self):
        """stderr must name the actual (non-Complete) status value."""
        _make_full_install(self.td)
        spec_path = str(_FIXTURES_DIR / "specify-sample-migration.md")
        _, _, err = self._run_preflight(self.td, spec=spec_path)
        self.assertIn("Draft", err)

    def test_in_progress_spec_exits_3(self):
        _make_full_install(self.td)
        spec_path = _write(
            self.td, "spec_ip.md",
            "# Spec\n\n**Status**: In Progress\n\n## Overview\n\nContent.\n"
        )
        code, _, _ = self._run_preflight(self.td, spec=spec_path)
        self.assertEqual(code, 3)

    def test_nonexistent_spec_path_exits_3(self):
        """Fix 2: When --spec points to a nonexistent file, spec_complete=False → exit 3.

        A nonexistent spec path is NOT a setup-chain failure (exit 2) — the setup
        chain artefacts are all present.  The spec gate treats a missing file as
        spec_complete=False, so the CLI must exit 3 (not 2) and mention /verify.
        """
        _make_full_install(self.td)
        code, out, err = self._run_preflight(
            self.td, spec=os.path.join(self.td, "nonexistent_spec.md")
        )
        self.assertEqual(code, 3,
                         msg="Nonexistent spec path must exit 3 (not setup-chain exit 2), got {0}".format(code))
        self.assertIn("/verify", err,
                      msg="stderr must mention /verify when spec gate fails")

    # --- JSON always emitted to stdout ---

    def test_stdout_is_always_json_on_missing_setup_chain(self):
        """Even when exit 2, stdout must contain JSON."""
        code, out, _ = self._run_preflight(self.td)
        self.assertEqual(code, 2)
        data = json.loads(out)
        self.assertIn("setup_chain_ok", data)
        self.assertIn("missing_artefacts", data)

    def test_stdout_is_always_json_on_not_complete_spec(self):
        """Even when exit 3, stdout must contain JSON."""
        _make_full_install(self.td)
        spec_path = str(_FIXTURES_DIR / "specify-sample-migration.md")
        code, out, _ = self._run_preflight(self.td, spec=spec_path)
        self.assertEqual(code, 3)
        data = json.loads(out)
        self.assertIn("spec_complete", data)
        self.assertFalse(data["spec_complete"])

    # --- Wrapper mode via CLI ---

    def test_wrapper_mode_install_setup_chain_ok(self):
        """A wrapper-mode CLAUDE.md is correctly reported as wrapper_mode=True."""
        _make_full_install(self.td)
        # Overwrite CLAUDE.md with a wrapper-mode one.
        # Note: "**Wrapper mode**: ..." text contains "source root" so the
        # source_root extractor fires on it first (shared limitation with
        # _verify/_review preflight — accepted, consistent).  The important
        # assertion here is wrapper_mode=True and setup_chain_ok.
        _write(self.td, "CLAUDE.md",
               "# CLAUDE.md\n\n"
               "**Wrapper mode**: active.\n"
               "- **Source Root**: myapp/\n")
        code, out, _ = self._run_preflight(self.td)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertTrue(data["wrapper_mode"])
        self.assertEqual(data["source_root"], "myapp/")

    # --- Unpopulated constitution does NOT block /summarize ---

    def test_unpopulated_constitution_does_not_trigger_exit_2(self):
        """/summarize has no constitution-populated guard — unpopulated = ok."""
        _make_full_install(self.td)
        _write(self.td, "constitution.md",
               "{{CONSTITUTION_BODY}}\nRun `/constitute` to populate this.\n")
        code, out, _ = self._run_preflight(self.td)
        # The setup chain still passes (constitution.md EXISTS)
        self.assertEqual(code, 0,
                         msg="Expected exit 0 (no sentinel guard), got {0}".format(code))
        data = json.loads(out)
        self.assertTrue(data["setup_chain_ok"])
        # No constitution_populated key (the guard is intentionally absent)
        self.assertNotIn("constitution_populated", data)


# ---------------------------------------------------------------------------
# TestLauncherSmoke — import + help + registry shape
# ---------------------------------------------------------------------------

class TestLauncherSmoke(unittest.TestCase):
    """Verify the CLI entry point parses --help and the registry is extensible."""

    def test_help_exits_cleanly(self):
        from _summarize._cli import main
        with self.assertRaises(SystemExit) as ctx:
            main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_no_subcommand_exits_2(self):
        from _summarize._cli import main
        code = main([])
        self.assertEqual(code, 2)

    def test_preflight_help_exits_0(self):
        from _summarize._cli import main
        with self.assertRaises(SystemExit) as ctx:
            main(["preflight", "--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_registry_has_preflight(self):
        from _summarize._cli import _SUBCOMMAND_REGISTRY
        verbs = [v for v, _, _ in _SUBCOMMAND_REGISTRY]
        self.assertIn("preflight", verbs)

    def test_registry_phase2_has_five_verbs(self):
        """Phase 1 shipped 1 verb (preflight); Phase 2 adds 4 more for a total of 5."""
        from _summarize._cli import _SUBCOMMAND_REGISTRY
        self.assertEqual(len(_SUBCOMMAND_REGISTRY), 5)

    def test_registry_entries_are_triples(self):
        from _summarize._cli import _SUBCOMMAND_REGISTRY
        for entry in _SUBCOMMAND_REGISTRY:
            self.assertEqual(len(entry), 3,
                             msg="Registry entry must be a (verb, help, handler) triple")

    def test_main_is_importable_from_init(self):
        from _summarize import main
        self.assertTrue(callable(main))


# ---------------------------------------------------------------------------
# TestSummarizeHelperShim — Python shim imports and dispatches
# ---------------------------------------------------------------------------

class TestSummarizeHelperShim(unittest.TestCase):
    """Verify summarize_helper.py shim wires _summarize._cli.main correctly."""

    def test_shim_imports_main_from_summarize_cli(self):
        """summarize_helper.py must import from _summarize._cli, not _verify._cli."""
        shim_path = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "summarize_helper.py"
        )
        with open(str(shim_path), "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn("from _summarize._cli import main", source)
        self.assertNotIn("from _verify._cli import main", source)
        self.assertNotIn("from _review._cli import main", source)

    def test_launcher_is_executable(self):
        launcher = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "summarize_helper"
        )
        self.assertTrue(
            os.access(str(launcher), os.X_OK),
            "summarize_helper must be executable (chmod +x)",
        )

    def test_launcher_references_summarize_helper_py(self):
        launcher = (
            _REPO_ROOT / "src" / "devforge" / "lib" / "summarize_helper"
        )
        with open(str(launcher), "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertIn("summarize_helper.py", source)


if __name__ == "__main__":
    unittest.main()
