"""Tests for src/devforge/lib/_grill/_brief.py.

Coverage:
  render_agent_brief   -- happy path (all paths present), handoff_path=None,
                          custom ring1_cap, custom finding_cap, custom tmp_path,
                          default tmp_path token not leaked, missing preamble
                          raises ValueError, missing checklist raises ValueError,
                          bad ring1_cap falls back to default, bad finding_cap
                          falls back to default, __FINDING_CAP__ token not in
                          rendered output, __RING1_CAP__ token not in rendered
                          output, output contract fields present, six Category
                          values present, all manifest paths appear in output,
                          three-ring instruction present, refutation preamble
                          injected when present
  _render_scope_block  -- handoff present, handoff absent, feature_id included
  GRILL_AGENT          -- constant value
  DEFAULT_RING1_CAP    -- default value used when ring1_cap falls back
  DEFAULT_FINDING_CAP  -- default value used when finding_cap falls back

Real-fixture approach: reference files are written via tempfile to tmp dirs
so that file reads inside render_agent_brief hit real filesystem I/O, matching
the production usage pattern.  GrillScopeManifest instances are built via
build_scope_manifest on a real tmp-dir fixture (real-producer round-trip).
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _grill._brief import (  # noqa: E402
    DEFAULT_FINDING_CAP,
    DEFAULT_RING1_CAP,
    GRILL_AGENT,
    _DEFAULT_TMP_PATH_TOKEN,
    _render_scope_block,
    render_agent_brief,
)
from _grill._scope import GrillScopeManifest, build_scope_manifest  # noqa: E402
from _shared.findings_schema import CATEGORY_ENUM  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write(path, content="stub\n"):
    # type: (str, str) -> str
    """Write content to path, creating parent dirs.  Returns path."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def _make_refs(refs_dir, preamble_content="PREAMBLE TEXT\n",
               checklist_content="ATTACK CHECKLIST\n",
               refutation_content=None):
    # type: (str, str, str, object) -> None
    """Write standard reference files into refs_dir."""
    _write(os.path.join(refs_dir, "anti-relitigation-preamble.md"), preamble_content)
    _write(os.path.join(refs_dir, "design-attack-checklist.md"), checklist_content)
    if refutation_content is not None:
        _write(os.path.join(refs_dir, "refutation-preamble.md"), refutation_content)


def _make_manifest_with_handoff(tmp_root):
    # type: (str) -> GrillScopeManifest
    """Build a real GrillScopeManifest with all optional paths present."""
    feature_dir = os.path.join(tmp_root, "specs", "001-auth")
    workspace_root = os.path.join(tmp_root, "workspace")
    _write(os.path.join(feature_dir, "plan.md"), "# Plan\n")
    _write(os.path.join(feature_dir, "spec.md"), "# Spec\n")
    _write(os.path.join(feature_dir, "handoff.json"), '{"handoff_kind":"specify"}\n')
    _write(os.path.join(workspace_root, "constitution.md"), "# Constitution\n")
    _write(os.path.join(workspace_root, "CLAUDE.md"), "# CLAUDE\n")
    manifest, err = build_scope_manifest(feature_dir, workspace_root)
    assert err is None, "fixture build failed: {0}".format(err)
    return manifest


def _make_manifest_no_handoff(tmp_root):
    # type: (str) -> GrillScopeManifest
    """Build a real GrillScopeManifest without handoff.json."""
    feature_dir = os.path.join(tmp_root, "specs", "002-search")
    workspace_root = os.path.join(tmp_root, "workspace2")
    _write(os.path.join(feature_dir, "plan.md"), "# Plan\n")
    _write(os.path.join(feature_dir, "spec.md"), "# Spec\n")
    _write(os.path.join(workspace_root, "constitution.md"), "# Constitution\n")
    _write(os.path.join(workspace_root, "CLAUDE.md"), "# CLAUDE\n")
    manifest, err = build_scope_manifest(feature_dir, workspace_root)
    assert err is None, "fixture build failed: {0}".format(err)
    return manifest


# ---------------------------------------------------------------------------
# Test: GRILL_AGENT and default constants
# ---------------------------------------------------------------------------


class TestConstants(unittest.TestCase):

    def test_grill_agent_value(self):
        self.assertEqual(GRILL_AGENT, "devils-advocate")

    def test_default_ring1_cap_positive(self):
        self.assertGreater(DEFAULT_RING1_CAP, 0)

    def test_default_finding_cap_positive(self):
        self.assertGreater(DEFAULT_FINDING_CAP, 0)

    def test_default_tmp_path_token_nonempty(self):
        self.assertTrue(len(_DEFAULT_TMP_PATH_TOKEN) > 0)


# ---------------------------------------------------------------------------
# Test: _render_scope_block
# ---------------------------------------------------------------------------


class TestRenderScopeBlock(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_all_paths_in_block(self):
        manifest = _make_manifest_with_handoff(self._tmp)
        block = _render_scope_block(manifest)
        self.assertIn(manifest.plan_path, block)
        self.assertIn(manifest.spec_path, block)
        self.assertIn(manifest.handoff_path, block)
        self.assertIn(manifest.constitution_path, block)
        self.assertIn(manifest.claude_md_path, block)

    def test_feature_id_in_block(self):
        manifest = _make_manifest_with_handoff(self._tmp)
        block = _render_scope_block(manifest)
        self.assertIn(manifest.feature_id, block)
        self.assertIn("001-auth", block)

    def test_handoff_absent_message(self):
        manifest = _make_manifest_no_handoff(self._tmp)
        self.assertIsNone(manifest.handoff_path)
        block = _render_scope_block(manifest)
        self.assertIn("not present", block)

    def test_handoff_present_path_shown(self):
        manifest = _make_manifest_with_handoff(self._tmp)
        self.assertIsNotNone(manifest.handoff_path)
        block = _render_scope_block(manifest)
        # The actual path should appear, not the "not present" message.
        self.assertIn(manifest.handoff_path, block)
        self.assertNotIn("not present", block)

    def test_block_contains_read_context_heading(self):
        manifest = _make_manifest_with_handoff(self._tmp)
        block = _render_scope_block(manifest)
        self.assertIn("Read Context", block)


# ---------------------------------------------------------------------------
# Test: render_agent_brief — happy path
# ---------------------------------------------------------------------------


class TestRenderAgentBriefHappyPath(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._refs = os.path.join(self._tmp, "refs")
        os.makedirs(self._refs)
        _make_refs(
            self._refs,
            preamble_content="## Anti-Relitigation\nDo not re-litigate.\n",
            checklist_content="## Attack Checklist\n- Check scope creep\n- Check assumptions\n",
        )
        self._manifest = _make_manifest_with_handoff(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_returns_string(self):
        result = render_agent_brief(self._manifest, self._refs)
        self.assertIsInstance(result, str)

    def test_preamble_injected(self):
        result = render_agent_brief(self._manifest, self._refs)
        self.assertIn("Anti-Relitigation", result)
        self.assertIn("Do not re-litigate.", result)

    def test_checklist_injected(self):
        result = render_agent_brief(self._manifest, self._refs)
        self.assertIn("Attack Checklist", result)
        self.assertIn("Check scope creep", result)
        self.assertIn("Check assumptions", result)

    def test_manifest_plan_path_in_brief(self):
        result = render_agent_brief(self._manifest, self._refs)
        self.assertIn(self._manifest.plan_path, result)

    def test_manifest_spec_path_in_brief(self):
        result = render_agent_brief(self._manifest, self._refs)
        self.assertIn(self._manifest.spec_path, result)

    def test_manifest_handoff_path_in_brief(self):
        result = render_agent_brief(self._manifest, self._refs)
        self.assertIn(self._manifest.handoff_path, result)

    def test_manifest_constitution_path_in_brief(self):
        result = render_agent_brief(self._manifest, self._refs)
        self.assertIn(self._manifest.constitution_path, result)

    def test_manifest_claude_md_path_in_brief(self):
        result = render_agent_brief(self._manifest, self._refs)
        self.assertIn(self._manifest.claude_md_path, result)

    def test_three_ring_instruction_present(self):
        result = render_agent_brief(self._manifest, self._refs)
        self.assertIn("Ring 0", result)
        self.assertIn("Ring 1", result)
        self.assertIn("Ring 2", result)
        self.assertIn("Three-Ring", result)

    def test_three_ring_instruction_mentions_cbm(self):
        result = render_agent_brief(self._manifest, self._refs)
        # The traversal block mentions the CBM tools.
        self.assertIn("trace_path", result)
        self.assertIn("search_graph", result)
        self.assertIn("query_graph", result)


# ---------------------------------------------------------------------------
# Test: output contract fields present
# ---------------------------------------------------------------------------


class TestOutputContractFields(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._refs = os.path.join(self._tmp, "refs")
        os.makedirs(self._refs)
        _make_refs(self._refs)
        self._manifest = _make_manifest_with_handoff(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _brief(self, **kwargs):
        return render_agent_brief(self._manifest, self._refs, **kwargs)

    def test_severity_field_present(self):
        self.assertIn("Severity:", self._brief())

    def test_file_field_present(self):
        self.assertIn("File:", self._brief())

    def test_line_field_present(self):
        self.assertIn("Line:", self._brief())

    def test_pattern_field_present(self):
        self.assertIn("Pattern:", self._brief())

    def test_category_field_present(self):
        self.assertIn("Category:", self._brief())

    def test_confidence_field_present(self):
        self.assertIn("Confidence:", self._brief())

    def test_evidence_field_present(self):
        self.assertIn("Evidence:", self._brief())

    def test_why_field_present(self):
        self.assertIn("Why it's wrong:", self._brief())

    def test_remediation_field_present(self):
        self.assertIn("Remediation:", self._brief())

    def test_all_six_category_values_present(self):
        # CATEGORY_ENUM = mislogic, system_design, best_practice,
        #                 duplication, security, blind_spot
        brief = self._brief()
        for cat in CATEGORY_ENUM:
            self.assertIn(cat, brief,
                          msg="Category value {0!r} missing from brief".format(cat))

    def test_severity_values_mentioned(self):
        brief = self._brief()
        for sev in ("Critical", "High", "Medium", "Info"):
            self.assertIn(sev, brief)

    def test_confidence_values_mentioned(self):
        brief = self._brief()
        for conf in ("Certain", "Likely", "Speculative"):
            self.assertIn(conf, brief)

    def test_finding_block_header_present(self):
        self.assertIn("## Finding 1", self._brief())

    def test_agent_header_template_present(self):
        self.assertIn("# Agent:", self._brief())

    def test_status_header_template_present(self):
        self.assertIn("# Status:", self._brief())

    def test_finding_count_header_template_present(self):
        self.assertIn("# Finding count:", self._brief())


# ---------------------------------------------------------------------------
# Test: cap parametrization
# ---------------------------------------------------------------------------


class TestCapParametrization(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._refs = os.path.join(self._tmp, "refs")
        os.makedirs(self._refs)
        _make_refs(self._refs)
        self._manifest = _make_manifest_with_handoff(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _brief(self, **kwargs):
        return render_agent_brief(self._manifest, self._refs, **kwargs)

    def test_finding_cap_token_not_in_output(self):
        brief = self._brief(finding_cap=25)
        self.assertNotIn("__FINDING_CAP__", brief)

    def test_ring1_cap_token_not_in_output(self):
        brief = self._brief(ring1_cap=20)
        self.assertNotIn("__RING1_CAP__", brief)

    def test_custom_finding_cap_appears_in_output(self):
        brief = self._brief(finding_cap=42)
        self.assertIn("42", brief)

    def test_custom_ring1_cap_appears_in_output(self):
        brief = self._brief(ring1_cap=18)
        self.assertIn("18", brief)

    def test_default_finding_cap_appears_when_not_overridden(self):
        brief = self._brief()
        self.assertIn(str(DEFAULT_FINDING_CAP), brief)

    def test_default_ring1_cap_appears_when_not_overridden(self):
        brief = self._brief()
        self.assertIn(str(DEFAULT_RING1_CAP), brief)

    def test_bad_finding_cap_zero_falls_back(self):
        brief = self._brief(finding_cap=0)
        self.assertIn(str(DEFAULT_FINDING_CAP), brief)
        self.assertNotIn("__FINDING_CAP__", brief)

    def test_bad_finding_cap_negative_falls_back(self):
        brief = self._brief(finding_cap=-5)
        self.assertIn(str(DEFAULT_FINDING_CAP), brief)
        self.assertNotIn("__FINDING_CAP__", brief)

    def test_bad_ring1_cap_zero_falls_back(self):
        brief = self._brief(ring1_cap=0)
        self.assertIn(str(DEFAULT_RING1_CAP), brief)
        self.assertNotIn("__RING1_CAP__", brief)

    def test_bad_ring1_cap_negative_falls_back(self):
        brief = self._brief(ring1_cap=-3)
        self.assertIn(str(DEFAULT_RING1_CAP), brief)
        self.assertNotIn("__RING1_CAP__", brief)

    def test_bad_finding_cap_wrong_type_falls_back(self):
        brief = self._brief(finding_cap="lots")  # type: ignore
        self.assertIn(str(DEFAULT_FINDING_CAP), brief)
        self.assertNotIn("__FINDING_CAP__", brief)

    def test_bad_ring1_cap_wrong_type_falls_back(self):
        brief = self._brief(ring1_cap=3.14)  # type: ignore
        self.assertIn(str(DEFAULT_RING1_CAP), brief)
        self.assertNotIn("__RING1_CAP__", brief)

    def test_ring1_cap_bool_true_falls_back(self):
        """bool is an int subclass; ring1_cap=True must be rejected and fall
        back to DEFAULT_RING1_CAP (not be silently treated as 1)."""
        brief = self._brief(ring1_cap=True)  # type: ignore
        self.assertIn(str(DEFAULT_RING1_CAP), brief)
        self.assertNotIn("__RING1_CAP__", brief)

    def test_finding_cap_bool_false_falls_back(self):
        """bool is an int subclass; finding_cap=False must be rejected and fall
        back to DEFAULT_FINDING_CAP (not be silently treated as 0)."""
        brief = self._brief(finding_cap=False)  # type: ignore
        self.assertIn(str(DEFAULT_FINDING_CAP), brief)
        self.assertNotIn("__FINDING_CAP__", brief)


# ---------------------------------------------------------------------------
# Test: tmp_path parametrization
# ---------------------------------------------------------------------------


class TestTmpPathParametrization(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._refs = os.path.join(self._tmp, "refs")
        os.makedirs(self._refs)
        _make_refs(self._refs)
        self._manifest = _make_manifest_with_handoff(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _brief(self, **kwargs):
        return render_agent_brief(self._manifest, self._refs, **kwargs)

    def test_custom_tmp_path_appears_in_output(self):
        custom = "/tmp/forge-grill/run-123/devils-advocate.md"
        brief = self._brief(tmp_path=custom)
        self.assertIn(custom, brief)

    def test_default_tmp_path_token_appears_when_none(self):
        brief = self._brief(tmp_path=None)
        self.assertIn(_DEFAULT_TMP_PATH_TOKEN, brief)

    def test_no_leftover_tmp_path_placeholder(self):
        # When tmp_path is provided, the {tmp-path} and {tmp_path} placeholders
        # must not appear verbatim in the output.
        custom = "/tmp/my-custom-path.md"
        brief = self._brief(tmp_path=custom)
        self.assertNotIn("{tmp-path}", brief)
        self.assertNotIn("{tmp_path}", brief)

    def test_closing_reminder_contains_bash_write(self):
        # The closing instruction includes a cat > ... << 'EOF' snippet.
        brief = self._brief()
        self.assertIn("cat >", brief)
        self.assertIn("GRILL_FINDINGS_EOF", brief)

    def test_closing_reminder_contains_status_failed(self):
        brief = self._brief()
        self.assertIn("Status: failed", brief)

    def test_closing_reminder_contains_finding_count_zero(self):
        brief = self._brief()
        self.assertIn("Finding count: 0", brief)


# ---------------------------------------------------------------------------
# Test: handoff absent in manifest
# ---------------------------------------------------------------------------


class TestHandoffAbsent(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._refs = os.path.join(self._tmp, "refs")
        os.makedirs(self._refs)
        _make_refs(self._refs)
        self._manifest = _make_manifest_no_handoff(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_not_present_message_in_brief(self):
        brief = render_agent_brief(self._manifest, self._refs)
        self.assertIn("not present", brief)

    def test_plan_and_spec_still_present(self):
        brief = render_agent_brief(self._manifest, self._refs)
        self.assertIn(self._manifest.plan_path, brief)
        self.assertIn(self._manifest.spec_path, brief)


# ---------------------------------------------------------------------------
# Test: error paths
# ---------------------------------------------------------------------------


class TestErrorPaths(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._refs = os.path.join(self._tmp, "refs")
        os.makedirs(self._refs)
        self._manifest = _make_manifest_with_handoff(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_missing_preamble_raises_valueerror(self):
        # Only write the checklist; omit the preamble.
        _write(
            os.path.join(self._refs, "design-attack-checklist.md"),
            "checklist\n",
        )
        with self.assertRaises(ValueError) as ctx:
            render_agent_brief(self._manifest, self._refs)
        self.assertIn("anti-relitigation-preamble.md", str(ctx.exception))

    def test_missing_checklist_raises_valueerror(self):
        # Only write the preamble; omit the checklist.
        _write(
            os.path.join(self._refs, "anti-relitigation-preamble.md"),
            "preamble\n",
        )
        with self.assertRaises(ValueError) as ctx:
            render_agent_brief(self._manifest, self._refs)
        self.assertIn("design-attack-checklist.md", str(ctx.exception))

    def test_nonexistent_references_dir_raises_valueerror(self):
        bad_dir = os.path.join(self._tmp, "no-such-refs")
        with self.assertRaises(ValueError):
            render_agent_brief(self._manifest, bad_dir)

    def test_error_message_includes_references_dir(self):
        bad_dir = os.path.join(self._tmp, "missing-refs-dir")
        with self.assertRaises(ValueError) as ctx:
            render_agent_brief(self._manifest, bad_dir)
        self.assertIn("missing-refs-dir", str(ctx.exception))


# ---------------------------------------------------------------------------
# Test: assembly order (parts appear in correct relative order)
# ---------------------------------------------------------------------------


class TestAssemblyOrder(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._refs = os.path.join(self._tmp, "refs")
        os.makedirs(self._refs)
        _make_refs(
            self._refs,
            preamble_content="PREAMBLE_MARKER\n",
            checklist_content="CHECKLIST_MARKER\n",
        )
        self._manifest = _make_manifest_with_handoff(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def _positions(self, *markers):
        # type: (*str) -> list
        brief = render_agent_brief(self._manifest, self._refs)
        return [brief.index(m) for m in markers]

    def test_preamble_before_checklist(self):
        pos_p, pos_c = self._positions("PREAMBLE_MARKER", "CHECKLIST_MARKER")
        self.assertLess(pos_p, pos_c)

    def test_checklist_before_scope_block(self):
        brief = render_agent_brief(self._manifest, self._refs)
        pos_c = brief.index("CHECKLIST_MARKER")
        pos_s = brief.index("Read Context")
        self.assertLess(pos_c, pos_s)

    def test_scope_block_before_traversal(self):
        brief = render_agent_brief(self._manifest, self._refs)
        pos_s = brief.index("Read Context")
        pos_t = brief.index("Three-Ring")
        self.assertLess(pos_s, pos_t)

    def test_traversal_before_output_contract(self):
        brief = render_agent_brief(self._manifest, self._refs)
        pos_t = brief.index("Three-Ring")
        pos_o = brief.index("fixed parseable format")
        self.assertLess(pos_t, pos_o)

    def test_output_contract_before_closing(self):
        brief = render_agent_brief(self._manifest, self._refs)
        pos_o = brief.index("fixed parseable format")
        pos_c = brief.index("ADVERSARIAL DEVILS-ADVOCATE MODE")
        self.assertLess(pos_o, pos_c)

    def test_closing_is_last_non_empty_section(self):
        brief = render_agent_brief(self._manifest, self._refs)
        pos_closing = brief.rindex("ADVERSARIAL DEVILS-ADVOCATE MODE")
        # Nothing from preamble or checklist appears after the closing block.
        self.assertGreater(pos_closing, brief.index("PREAMBLE_MARKER"))
        self.assertGreater(pos_closing, brief.index("CHECKLIST_MARKER"))


# ---------------------------------------------------------------------------
# Test: adversarial/design note present
# ---------------------------------------------------------------------------


class TestAdversarialNote(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._refs = os.path.join(self._tmp, "refs")
        os.makedirs(self._refs)
        _make_refs(self._refs)
        self._manifest = _make_manifest_with_handoff(self._tmp)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_devils_advocate_mode_label_in_closing(self):
        brief = render_agent_brief(self._manifest, self._refs)
        self.assertIn("DEVILS-ADVOCATE MODE", brief)

    def test_adversarial_term_present(self):
        brief = render_agent_brief(self._manifest, self._refs)
        self.assertIn("ADVERSARIAL", brief)

    def test_external_web_citation_instruction_present(self):
        # The output contract explains how to handle URL/web citations.
        brief = render_agent_brief(self._manifest, self._refs)
        self.assertIn("URL", brief)


if __name__ == "__main__":
    unittest.main()
