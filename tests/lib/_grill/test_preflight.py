"""Tests for src/devforge/lib/_grill/_preflight.py.

Coverage:
  preflight_context — all-files-absent defaults, each setup-chain artefact
                      missing individually, sentinel constitution, real
                      populated constitution, Source-Root extraction,
                      wrapper-mode detection, memory.md excerpt (at the
                      CORRECT .devforge/memory.md path), feature-gate checks
                      (spec.md + plan.md required for /grill), feature_dir=None
                      mode, and the all-green pass.

Structural mirror of tests/lib/_review/test_preflight.py (TestPreflightContext)
so the two helpers stay structurally aligned, with the additions specific to
/grill's feature-level gate.

Real-producer round-trip: fixtures are written to temp dirs via _write()
helpers that reproduce the actual filesystem layout the real /init-forge,
/configure, /generate-docs, and /constitute commands produce. No hand-faked
strings for the sentinel check — we use the exact sentinel strings exported
from _grill._preflight._UNPOPULATED_SENTINELS.
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

from _grill._preflight import (  # noqa: E402
    _SETUP_CHAIN_ARTEFACTS,
    _UNPOPULATED_SENTINELS,
    preflight_context,
)
from _shared.memory import DEFAULT_EXCERPT_LINES  # noqa: E402

# The real shipped installer stub -- used to build production-shaped
# memory.md fixtures (real "## " sections) rather than headingless ones
# (plan 79 Phase 1: a headingless file is 100% preamble and excerpts "").
_REAL_STUB_PATH = _REPO_ROOT / "src" / "devforge" / "memory.md"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_full_install(td):
    # type: (str) -> None
    """Write a minimal but complete 4-command setup-chain install into td.

    Files created:
      constitution.md               — populated (no sentinels)
      CLAUDE.md                     — minimal CLAUDE.md with Source Root
      .devforge/project-config.json — /configure output stub
      .devforge/index.json          — /generate-docs output stub
      .devforge/memory.md           — forge memory file (correct path)

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
    # plan 79 Phase 1: production-shaped memory.md -- the real shipped
    # stub's "## " sections, with the lesson links placed under a real
    # (non-excluded) heading so a section-aware excerpt surfaces them.
    real_stub_text = _REAL_STUB_PATH.read_text(encoding="utf-8")
    mem_content = real_stub_text.replace(
        "## Known Pitfalls\n"
        "<!-- Populated during work as mistakes are discovered -->\n",
        "## Known Pitfalls\n"
        "<!-- Populated during work as mistakes are discovered -->\n"
        "- [Lesson 1](lesson_1.md)\n- [Lesson 2](lesson_2.md)\n",
    )
    _write(td, ".devforge/memory.md", mem_content)


def _make_feature(td, slug="001-auth", with_spec=True, with_plan=True):
    # type: (str, str, bool, bool) -> str
    """Create a feature directory under td/specs/<slug>/ with optional artefacts.

    Returns the absolute path to the feature directory.
    """
    feature_dir = os.path.join(td, "specs", slug)
    os.makedirs(feature_dir, exist_ok=True)
    if with_spec:
        _write(feature_dir, "spec.md",
               "# Spec\n\n**Status**: Approved\n")
    if with_plan:
        _write(feature_dir, "plan.md",
               "# Plan\n\n**Status**: Approved\n")
    return feature_dir


def _write(td, rel_path, content):
    # type: (str, str, str) -> str
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
    """Ensure _grill uses the same sentinel set as _audit (parity requirement)."""

    def test_sentinel_set_is_nonempty(self):
        self.assertGreater(len(_UNPOPULATED_SENTINELS), 0)

    def test_constitution_body_sentinel_present(self):
        self.assertIn("{{CONSTITUTION_BODY}}", _UNPOPULATED_SENTINELS)

    def test_run_constitute_backtick_sentinel_present(self):
        self.assertIn("Run `/constitute`", _UNPOPULATED_SENTINELS)

    def test_run_constitute_to_populate_sentinel_present(self):
        self.assertIn("Run /constitute to populate", _UNPOPULATED_SENTINELS)

    def test_run_constitute_to_populate_legacy_no_slash_sentinel_present(self):
        # Pre-namespace stub literal (no slash) -- the form every existing
        # consumer install actually carries.
        self.assertIn("Run constitute to populate", _UNPOPULATED_SENTINELS)

    def test_run_devforge_constitute_to_populate_sentinel_present(self):
        # Post-namespace stub literal (current, plan 63 Phase 4c).
        self.assertIn(
            "Run /devforge:constitute to populate", _UNPOPULATED_SENTINELS
        )

    def test_sentinel_parity_with_audit(self):
        """The sentinel tuple must match _audit._preflight._UNPOPULATED_SENTINELS."""
        from _audit._preflight import _UNPOPULATED_SENTINELS as audit_sentinels
        self.assertEqual(
            set(_UNPOPULATED_SENTINELS),
            set(audit_sentinels),
            msg=(
                "_grill sentinels diverge from _audit sentinels. "
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
                "_grill sentinels diverge from _review sentinels. "
                "Keep them in sync so all helpers enforce the same gate."
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
# TestPreflightContext — pure function: setup-chain checks
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

    def test_full_install_memory_present(self):
        # plan 79 Phase 1: _make_full_install()'s memory.md is now
        # production-shaped (real "## " sections), with the lesson links
        # under "## Known Pitfalls" -- a section-aware excerpt surfaces
        # them.
        _make_full_install(self.td)
        r = preflight_context(self.td)
        self.assertTrue(r["memory_present"])
        self.assertIn("Lesson 1", r["memory_excerpt"])

    # --- Constitution sentinel checks (real sentinel strings from the module) ---

    def test_constitution_with_body_sentinel_unpopulated(self):
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
        # Pre-namespace stub literal (no slash) -- the form every existing
        # consumer install actually carries (src/constitution.md has always
        # shipped this exact text).
        self.assertEqual(
            _UNPOPULATED_SENTINELS[2], "Run constitute to populate"
        )
        _write(self.td, "constitution.md",
               "{0} — see instructions.".format(_UNPOPULATED_SENTINELS[2]))
        r = preflight_context(self.td)
        self.assertTrue(r["constitution_present"])
        self.assertFalse(r["constitution_populated"])

    def test_constitution_with_legacy_slash_sentinel_unpopulated(self):
        # Index [2] (used by test_constitution_with_populate_sentinel_unpopulated
        # above) is the pre-namespace NO-slash form -- the form every existing
        # consumer install actually carries. This test covers index [3], the
        # pre-namespace WITH-slash form, kept for back-compat.
        self.assertEqual(
            _UNPOPULATED_SENTINELS[3], "Run /constitute to populate"
        )
        _write(self.td, "constitution.md",
               "{0} — see instructions.".format(_UNPOPULATED_SENTINELS[3]))
        r = preflight_context(self.td)
        self.assertTrue(r["constitution_present"])
        self.assertFalse(r["constitution_populated"])

    def test_constitution_with_devforge_namespaced_sentinel_unpopulated(self):
        # Post-namespace stub literal (current, plan 63 Phase 4c).
        self.assertEqual(
            _UNPOPULATED_SENTINELS[4], "Run /devforge:constitute to populate"
        )
        _write(self.td, "constitution.md",
               "{0} — see instructions.".format(_UNPOPULATED_SENTINELS[4]))
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
        self.assertIn("/devforge:constitute", r["missing_artefacts"])

    def test_missing_claude_md_flagged(self):
        _make_full_install(self.td)
        os.unlink(os.path.join(self.td, "CLAUDE.md"))
        r = preflight_context(self.td)
        self.assertFalse(r["setup_chain_ok"])
        self.assertIn("/devforge:init-forge", r["missing_artefacts"])

    def test_missing_project_config_flagged(self):
        _make_full_install(self.td)
        os.unlink(os.path.join(self.td, ".devforge", "project-config.json"))
        r = preflight_context(self.td)
        self.assertFalse(r["setup_chain_ok"])
        self.assertIn("/devforge:configure", r["missing_artefacts"])

    def test_missing_index_json_flagged(self):
        _make_full_install(self.td)
        os.unlink(os.path.join(self.td, ".devforge", "index.json"))
        r = preflight_context(self.td)
        self.assertFalse(r["setup_chain_ok"])
        self.assertIn("/devforge:generate-docs", r["missing_artefacts"])

    def test_three_missing_artefacts_lists_three(self):
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

    # --- .devforge/memory.md (correct path, NOT .claude/memory/MEMORY.md) ---

    def test_memory_present_at_devforge_path(self):
        """Memory is read from .devforge/memory.md (the correct forge path).

        plan 79 Phase 1: re-fixtured with a real "## " heading -- a
        headingless fixture is 100% preamble and excerpts "".
        """
        real_stub_text = _REAL_STUB_PATH.read_text(encoding="utf-8")
        mem_content = real_stub_text.replace(
            "## Known Pitfalls\n"
            "<!-- Populated during work as mistakes are discovered -->\n",
            "## Known Pitfalls\n"
            "<!-- Populated during work as mistakes are discovered -->\n"
            "- [Session 1](s1.md)\n- [Session 2](s2.md)\n",
        )
        _write(self.td, ".devforge/memory.md", mem_content)
        r = preflight_context(self.td)
        self.assertTrue(r["memory_present"])
        self.assertIn("Session 1", r["memory_excerpt"])

    def test_memory_absent(self):
        r = preflight_context(self.td)
        self.assertFalse(r["memory_present"])
        self.assertEqual(r["memory_excerpt"], "")

    def test_memory_excerpt_capped_at_default_excerpt_lines(self):
        # RENAMED (was test_memory_excerpt_capped_at_40_lines): plan 79
        # Phase 1 raises the excerpt budget to DEFAULT_EXCERPT_LINES (120)
        # CONTENT lines and makes it section-aware. The old headingless
        # 60-line fixture is 100% preamble under the new algorithm and
        # renders "" -- the old assertLessEqual(len(lines), 40) still
        # "passed" on that empty result, but vacuously: it no longer
        # exercised a cap at all. Re-fixtured with a single real "## "
        # section carrying more lines than the budget, so the cap is
        # genuinely tested again.
        mem_content = "## Lessons\n" + "\n".join(
            ["Line {0}".format(i) for i in range(200)]
        ) + "\n"
        _write(self.td, ".devforge/memory.md", mem_content)
        r = preflight_context(self.td)
        self.assertTrue(r["memory_present"])
        lines = r["memory_excerpt"].splitlines()
        self.assertEqual(len(lines), 2 + DEFAULT_EXCERPT_LINES)
        self.assertIn("Line 199", r["memory_excerpt"])
        self.assertNotIn("Line 0\n", r["memory_excerpt"])

    def test_stale_claude_memory_path_not_read(self):
        """Files at .claude/memory/MEMORY.md are NOT the memory source for /grill."""
        # Write to the stale path only — _grill must NOT read it.
        _write(self.td, ".claude/memory/MEMORY.md",
               "stale path content\n")
        r = preflight_context(self.td)
        # .devforge/memory.md is absent → memory_present must be False.
        self.assertFalse(r["memory_present"])
        self.assertEqual(r["memory_excerpt"], "")

    # --- Result keyset ---

    def test_result_has_all_expected_keys(self):
        r = preflight_context(self.td)
        expected_keys = {
            "constitution_present", "constitution_populated",
            "setup_chain_ok", "missing_artefacts",
            "source_root", "wrapper_mode",
            "project_type", "framework", "language",
            "claude_md_present", "memory_present", "memory_excerpt",
            "spec_present", "plan_present",
            "feature_gate_ok", "missing_feature_artefacts",
        }
        self.assertEqual(set(r.keys()), expected_keys)


# ---------------------------------------------------------------------------
# TestFeatureGate — /grill-specific feature-level gate
# ---------------------------------------------------------------------------

class TestFeatureGate(unittest.TestCase):
    """Verify the feature-level gate: spec.md + plan.md must exist."""

    def setUp(self):
        self.td = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.td)

    # --- feature_dir=None (no feature-level check requested) ---

    def test_no_feature_dir_feature_gate_not_ok(self):
        r = preflight_context(self.td, feature_dir=None)
        self.assertFalse(r["feature_gate_ok"])
        self.assertFalse(r["spec_present"])
        self.assertFalse(r["plan_present"])
        self.assertEqual(r["missing_feature_artefacts"], [])

    # --- Both artefacts present ---

    def test_both_spec_and_plan_present_gate_ok(self):
        feature_dir = _make_feature(self.td, with_spec=True, with_plan=True)
        r = preflight_context(self.td, feature_dir=feature_dir)
        self.assertTrue(r["spec_present"])
        self.assertTrue(r["plan_present"])
        self.assertTrue(r["feature_gate_ok"])
        self.assertEqual(r["missing_feature_artefacts"], [])

    # --- spec.md missing ---

    def test_missing_spec_md_gate_not_ok(self):
        feature_dir = _make_feature(self.td, with_spec=False, with_plan=True)
        r = preflight_context(self.td, feature_dir=feature_dir)
        self.assertFalse(r["spec_present"])
        self.assertTrue(r["plan_present"])
        self.assertFalse(r["feature_gate_ok"])
        self.assertIn("spec.md", r["missing_feature_artefacts"])

    def test_missing_spec_md_lists_in_missing_feature_artefacts(self):
        feature_dir = _make_feature(self.td, with_spec=False, with_plan=True)
        r = preflight_context(self.td, feature_dir=feature_dir)
        self.assertIn("spec.md", r["missing_feature_artefacts"])
        self.assertNotIn("plan.md", r["missing_feature_artefacts"])

    # --- plan.md missing ---

    def test_missing_plan_md_gate_not_ok(self):
        feature_dir = _make_feature(self.td, with_spec=True, with_plan=False)
        r = preflight_context(self.td, feature_dir=feature_dir)
        self.assertTrue(r["spec_present"])
        self.assertFalse(r["plan_present"])
        self.assertFalse(r["feature_gate_ok"])
        self.assertIn("plan.md", r["missing_feature_artefacts"])

    def test_missing_plan_md_lists_in_missing_feature_artefacts(self):
        feature_dir = _make_feature(self.td, with_spec=True, with_plan=False)
        r = preflight_context(self.td, feature_dir=feature_dir)
        self.assertIn("plan.md", r["missing_feature_artefacts"])
        self.assertNotIn("spec.md", r["missing_feature_artefacts"])

    # --- Both artefacts missing ---

    def test_both_missing_lists_both(self):
        feature_dir = _make_feature(self.td, with_spec=False, with_plan=False)
        r = preflight_context(self.td, feature_dir=feature_dir)
        self.assertFalse(r["spec_present"])
        self.assertFalse(r["plan_present"])
        self.assertFalse(r["feature_gate_ok"])
        self.assertEqual(len(r["missing_feature_artefacts"]), 2)
        self.assertIn("spec.md", r["missing_feature_artefacts"])
        self.assertIn("plan.md", r["missing_feature_artefacts"])

    # --- Nonexistent feature_dir ---

    def test_nonexistent_feature_dir_no_raise(self):
        r = preflight_context(
            self.td,
            feature_dir=os.path.join(self.td, "specs", "does_not_exist"),
        )
        self.assertFalse(r["spec_present"])
        self.assertFalse(r["plan_present"])
        self.assertFalse(r["feature_gate_ok"])

    # --- All-green pass: full install + both feature artefacts ---

    def test_all_green_setup_chain_and_feature(self):
        """The all-green path: full setup chain + spec.md + plan.md."""
        _make_full_install(self.td)
        feature_dir = _make_feature(self.td, with_spec=True, with_plan=True)
        r = preflight_context(self.td, feature_dir=feature_dir)
        # Setup chain
        self.assertTrue(r["setup_chain_ok"])
        self.assertTrue(r["constitution_present"])
        self.assertTrue(r["constitution_populated"])
        self.assertEqual(r["missing_artefacts"], [])
        # Feature gate
        self.assertTrue(r["spec_present"])
        self.assertTrue(r["plan_present"])
        self.assertTrue(r["feature_gate_ok"])
        self.assertEqual(r["missing_feature_artefacts"], [])
        # Memory
        self.assertTrue(r["memory_present"])

    # --- Setup-chain failure does not affect feature gate ---

    def test_incomplete_setup_chain_does_not_affect_feature_gate(self):
        """Feature gate checks are independent of the setup-chain gate."""
        # Only write feature artefacts, no setup chain.
        feature_dir = _make_feature(self.td, with_spec=True, with_plan=True)
        r = preflight_context(self.td, feature_dir=feature_dir)
        # Setup chain should fail.
        self.assertFalse(r["setup_chain_ok"])
        # Feature gate should still pass (independent check).
        self.assertTrue(r["feature_gate_ok"])

    # --- feature_dir provided but points at workspace_root (edge case) ---

    def test_feature_dir_same_as_workspace_no_crash(self):
        """Providing feature_dir == workspace_root doesn't raise."""
        r = preflight_context(self.td, feature_dir=self.td)
        # No files exist, so feature gate is not ok.
        self.assertFalse(r["feature_gate_ok"])


# ---------------------------------------------------------------------------
# TestSetupChainInteractionWithFeatureGate — combined gate tests
# ---------------------------------------------------------------------------

class TestSetupChainInteractionWithFeatureGate(unittest.TestCase):
    """Verify setup-chain and feature-gate return correct combined state."""

    def setUp(self):
        self.td = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.td)

    def test_setup_ok_feature_missing_plan(self):
        _make_full_install(self.td)
        feature_dir = _make_feature(self.td, with_spec=True, with_plan=False)
        r = preflight_context(self.td, feature_dir=feature_dir)
        self.assertTrue(r["setup_chain_ok"])
        self.assertFalse(r["feature_gate_ok"])
        self.assertIn("plan.md", r["missing_feature_artefacts"])

    def test_setup_ok_feature_missing_spec(self):
        _make_full_install(self.td)
        feature_dir = _make_feature(self.td, with_spec=False, with_plan=True)
        r = preflight_context(self.td, feature_dir=feature_dir)
        self.assertTrue(r["setup_chain_ok"])
        self.assertFalse(r["feature_gate_ok"])
        self.assertIn("spec.md", r["missing_feature_artefacts"])

    def test_setup_sentinel_constitution_feature_ok(self):
        _make_full_install(self.td)
        feature_dir = _make_feature(self.td, with_spec=True, with_plan=True)
        # Overwrite constitution with sentinel.
        _write(self.td, "constitution.md",
               "{0}".format(_UNPOPULATED_SENTINELS[0]))
        r = preflight_context(self.td, feature_dir=feature_dir)
        # Setup chain: constitution present but unpopulated.
        self.assertTrue(r["constitution_present"])
        self.assertFalse(r["constitution_populated"])
        self.assertTrue(r["setup_chain_ok"])  # constitution.md file IS present
        # Feature gate unaffected.
        self.assertTrue(r["feature_gate_ok"])


if __name__ == "__main__":
    unittest.main()
