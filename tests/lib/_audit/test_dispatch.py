"""Tests for render_agent_brief in src/devforge/lib/_audit/_scope.py.

Coverage:
  render_agent_brief — all 4 agents contain preamble + checklist + focus +
                       contract + closing; closing is LAST; structure stable
                       (only focus block differs between agents); unknown agent
                       raises ValueError; missing references-dir raises ValueError.
"""

import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_REFERENCES_DIR = (
    _REPO_ROOT / "src" / "commands" / "audit" / "references"
)

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _audit._scope import (  # noqa: E402
    _CLOSING_REMINDER,
    _FOCUS_BLOCKS,
    _OUTPUT_CONTRACT,
    render_agent_brief,
    render_scope_block,
    resolve_scope,
)

_AGENTS = ["code-reviewer", "architect", "qa-engineer", "security-reviewer"]

# ---------------------------------------------------------------------------
# Read reference file contents once for assertion helpers
# ---------------------------------------------------------------------------

def _read_ref(name):
    path = _REFERENCES_DIR / name
    with open(str(path), "r", encoding="utf-8") as fh:
        return fh.read()


_PREAMBLE_TEXT = _read_ref("adversarial-preamble.md")
_CHECKLIST_TEXT = _read_ref("mislogic-checklist.md")
_BEST_PRACTICES_TEXT = _read_ref("best-practices-checklist.md")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_scope_block():
    scope_result = {
        "scope_kind": "file",
        "pipeline": "simplified",
        "files": ["src/main.py"],
        "file_count": 1,
        "scope_limit": 200,
        "scope_oversize": False,
        "line_range": None,
        "error": None,
    }
    return render_scope_block(scope_result, "/test/repo")


# ---------------------------------------------------------------------------
# Tests — content presence for all 4 agents
# ---------------------------------------------------------------------------

class TestRenderAgentBriefContentPresence(unittest.TestCase):
    """Each agent's brief must contain every required section verbatim."""

    def _make_brief(self, agent, extra_context=""):
        scope_block = _make_scope_block()
        return render_agent_brief(
            agent=agent,
            references_dir=str(_REFERENCES_DIR),
            scope_block=scope_block,
            source_root="/test/repo",
            extra_context=extra_context,
        )

    def _assert_contains_preamble(self, brief):
        # Use a distinctive substring from the preamble file to verify verbatim inclusion.
        self.assertIn("ADVERSARIAL AUDIT MODE", brief)
        # Verify the full preamble is byte-for-byte present.
        self.assertIn(_PREAMBLE_TEXT, brief)

    def _assert_contains_checklist(self, brief):
        self.assertIn("MISLOGIC HUNT CHECKLIST", brief)
        self.assertIn(_CHECKLIST_TEXT, brief)

    def _assert_contains_output_contract(self, brief):
        # _OUTPUT_CONTRACT contains __FINDING_CAP__ which is substituted in the
        # rendered brief with the numeric cap value. Compare with token replaced.
        self.assertIn(_OUTPUT_CONTRACT.replace("__FINDING_CAP__", "30"), brief)

    def _assert_ends_with_closing(self, brief):
        # _CLOSING_REMINDER contains __FINDING_CAP__ which is substituted in the
        # rendered brief with the numeric cap value. Compare with token replaced.
        closing_rendered = _CLOSING_REMINDER.replace("__FINDING_CAP__", "30").rstrip()
        self.assertTrue(
            brief.rstrip().endswith(closing_rendered),
            "Brief does not end with the closing reminder.\n"
            "Expected tail:\n{0!r}\nActual tail:\n{1!r}".format(
                closing_rendered[-100:], brief[-200:]
            ),
        )

    def test_code_reviewer_all_sections(self):
        brief = self._make_brief("code-reviewer")
        self._assert_contains_preamble(brief)
        self._assert_contains_checklist(brief)
        self._assert_contains_output_contract(brief)
        self._assert_ends_with_closing(brief)

    def test_architect_all_sections(self):
        brief = self._make_brief("architect")
        self._assert_contains_preamble(brief)
        self._assert_contains_checklist(brief)
        self._assert_contains_output_contract(brief)
        self._assert_ends_with_closing(brief)

    def test_qa_engineer_all_sections(self):
        brief = self._make_brief("qa-engineer")
        self._assert_contains_preamble(brief)
        self._assert_contains_checklist(brief)
        self._assert_contains_output_contract(brief)
        self._assert_ends_with_closing(brief)

    def test_security_reviewer_all_sections(self):
        brief = self._make_brief("security-reviewer")
        self._assert_contains_preamble(brief)
        self._assert_contains_checklist(brief)
        self._assert_contains_output_contract(brief)
        self._assert_ends_with_closing(brief)


# ---------------------------------------------------------------------------
# Tests — per-agent focus block
# ---------------------------------------------------------------------------

class TestRenderAgentBriefFocusBlocks(unittest.TestCase):
    def _make_brief(self, agent):
        return render_agent_brief(
            agent=agent,
            references_dir=str(_REFERENCES_DIR),
            scope_block=_make_scope_block(),
            source_root="/test/repo",
        )

    def test_code_reviewer_focus_text(self):
        brief = self._make_brief("code-reviewer")
        self.assertIn(_FOCUS_BLOCKS["code-reviewer"], brief)
        # Distinctive phrase
        self.assertIn("naming-vs-behavior mismatches", brief)

    def test_architect_focus_text(self):
        brief = self._make_brief("architect")
        self.assertIn(_FOCUS_BLOCKS["architect"], brief)
        self.assertIn("cross-module contradictions", brief)

    def test_qa_engineer_focus_text(self):
        brief = self._make_brief("qa-engineer")
        self.assertIn(_FOCUS_BLOCKS["qa-engineer"], brief)
        self.assertIn("logic blind spots", brief)

    def test_security_reviewer_focus_text(self):
        brief = self._make_brief("security-reviewer")
        self.assertIn(_FOCUS_BLOCKS["security-reviewer"], brief)
        self.assertIn("security regressions", brief)


# ---------------------------------------------------------------------------
# Tests — structure stable across agents (only focus block differs)
# ---------------------------------------------------------------------------

class TestRenderAgentBriefStructureStability(unittest.TestCase):
    """Swapping agent changes exactly the focus section; shared sections identical."""

    def _make_brief(self, agent):
        return render_agent_brief(
            agent=agent,
            references_dir=str(_REFERENCES_DIR),
            scope_block=_make_scope_block(),
            source_root="/test/repo",
        )

    def test_preamble_identical_across_agents(self):
        briefs = {a: self._make_brief(a) for a in _AGENTS}
        for agent, brief in briefs.items():
            self.assertIn(
                _PREAMBLE_TEXT, brief,
                "Agent {0} missing preamble".format(agent),
            )

    def test_checklist_identical_across_agents(self):
        briefs = {a: self._make_brief(a) for a in _AGENTS}
        for agent, brief in briefs.items():
            self.assertIn(
                _CHECKLIST_TEXT, brief,
                "Agent {0} missing checklist".format(agent),
            )

    def test_best_practices_checklist_identical_across_agents(self):
        briefs = {a: self._make_brief(a) for a in _AGENTS}
        for agent, brief in briefs.items():
            self.assertIn(
                _BEST_PRACTICES_TEXT, brief,
                "Agent {0} missing best-practices checklist".format(agent),
            )

    def test_output_contract_identical_across_agents(self):
        # _OUTPUT_CONTRACT has __FINDING_CAP__ substituted to "30" in the brief.
        contract_rendered = _OUTPUT_CONTRACT.replace("__FINDING_CAP__", "30")
        briefs = {a: self._make_brief(a) for a in _AGENTS}
        for agent, brief in briefs.items():
            self.assertIn(
                contract_rendered, brief,
                "Agent {0} missing output contract".format(agent),
            )

    def test_closing_reminder_identical_across_agents(self):
        # _CLOSING_REMINDER has __FINDING_CAP__ substituted to "30" in the brief.
        closing_rendered = _CLOSING_REMINDER.replace("__FINDING_CAP__", "30").rstrip()
        for agent in _AGENTS:
            brief = self._make_brief(agent)
            self.assertTrue(
                brief.rstrip().endswith(closing_rendered),
                "Agent {0} brief does not end with closing reminder".format(agent),
            )

    def test_briefs_differ_by_focus_only(self):
        """Two agents produce different briefs, and the diff is the focus block."""
        brief_cr = self._make_brief("code-reviewer")
        brief_ar = self._make_brief("architect")
        # They should differ
        self.assertNotEqual(brief_cr, brief_ar)
        # The difference: one has code-reviewer focus, other has architect focus
        self.assertIn(_FOCUS_BLOCKS["code-reviewer"], brief_cr)
        self.assertNotIn(_FOCUS_BLOCKS["architect"], brief_cr)
        self.assertIn(_FOCUS_BLOCKS["architect"], brief_ar)
        self.assertNotIn(_FOCUS_BLOCKS["code-reviewer"], brief_ar)


# ---------------------------------------------------------------------------
# Tests — closing reminder is LAST
# ---------------------------------------------------------------------------

class TestRenderAgentBriefClosingIsLast(unittest.TestCase):
    def test_closing_is_last_for_all_agents(self):
        # _CLOSING_REMINDER has __FINDING_CAP__ substituted to "30" in the brief.
        closing_rendered = _CLOSING_REMINDER.replace("__FINDING_CAP__", "30").rstrip()
        scope_block = _make_scope_block()
        for agent in _AGENTS:
            brief = render_agent_brief(
                agent=agent,
                references_dir=str(_REFERENCES_DIR),
                scope_block=scope_block,
                source_root="/repo",
            )
            stripped = brief.rstrip()
            self.assertTrue(
                stripped.endswith(closing_rendered),
                "Agent {0}: closing reminder is not last.\n"
                "Final 200 chars: {1!r}".format(agent, stripped[-200:]),
            )

    def test_output_contract_before_closing(self):
        """Output contract must appear in the brief before the closing reminder."""
        # Use rendered (token-substituted) prefixes to locate positions.
        contract_prefix = _OUTPUT_CONTRACT.replace("__FINDING_CAP__", "30")[:50]
        closing_prefix = _CLOSING_REMINDER.replace("__FINDING_CAP__", "30")[:50]
        for agent in _AGENTS:
            brief = render_agent_brief(
                agent=agent,
                references_dir=str(_REFERENCES_DIR),
                scope_block=_make_scope_block(),
                source_root="/repo",
            )
            contract_pos = brief.find(contract_prefix)
            closing_pos = brief.find(closing_prefix)
            self.assertGreater(
                closing_pos, contract_pos,
                "Agent {0}: closing reminder does not appear after output contract".format(agent),
            )


# ---------------------------------------------------------------------------
# Tests — extra_context inclusion
# ---------------------------------------------------------------------------

class TestRenderAgentBriefExtraContext(unittest.TestCase):
    def test_extra_context_included(self):
        brief = render_agent_brief(
            agent="code-reviewer",
            references_dir=str(_REFERENCES_DIR),
            scope_block=_make_scope_block(),
            source_root="/repo",
            extra_context="RECURRING ISSUES: watch for X",
        )
        self.assertIn("RECURRING ISSUES: watch for X", brief)

    def test_empty_extra_context_no_artifact(self):
        brief = render_agent_brief(
            agent="architect",
            references_dir=str(_REFERENCES_DIR),
            scope_block=_make_scope_block(),
            source_root="/repo",
            extra_context="",
        )
        # Should not contain the extra context label
        self.assertNotIn("RECURRING ISSUES", brief)


# ---------------------------------------------------------------------------
# Tests — error paths
# ---------------------------------------------------------------------------

class TestRenderAgentBriefErrors(unittest.TestCase):
    def test_unknown_agent_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            render_agent_brief(
                agent="nonexistent-agent",
                references_dir=str(_REFERENCES_DIR),
                scope_block=_make_scope_block(),
                source_root="/repo",
            )
        self.assertIn("nonexistent-agent", str(ctx.exception))

    def test_missing_references_dir_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            render_agent_brief(
                agent="code-reviewer",
                references_dir="/definitely/not/a/real/dir",
                scope_block=_make_scope_block(),
                source_root="/repo",
            )
        self.assertIn("adversarial-preamble.md", str(ctx.exception))

    def test_missing_preamble_file_raises_value_error(self):
        """If preamble file is absent, ValueError is raised."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Only create mislogic-checklist.md, not adversarial-preamble.md
            with open(os.path.join(tmpdir, "mislogic-checklist.md"), "w") as fh:
                fh.write("checklist\n")
            with self.assertRaises(ValueError):
                render_agent_brief(
                    agent="code-reviewer",
                    references_dir=tmpdir,
                    scope_block=_make_scope_block(),
                    source_root="/repo",
                )

    def test_missing_checklist_file_raises_value_error(self):
        """If checklist file is absent, ValueError is raised."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Only create adversarial-preamble.md, not mislogic-checklist.md
            with open(os.path.join(tmpdir, "adversarial-preamble.md"), "w") as fh:
                fh.write("preamble\n")
            with self.assertRaises(ValueError):
                render_agent_brief(
                    agent="architect",
                    references_dir=tmpdir,
                    scope_block=_make_scope_block(),
                    source_root="/repo",
                )


# ---------------------------------------------------------------------------
# Tests — scope block in the brief
# ---------------------------------------------------------------------------

class TestRenderAgentBriefScopeSection(unittest.TestCase):
    def test_scope_block_included(self):
        scope_result = {
            "scope_kind": "directory",
            "pipeline": "full",
            "files": ["src/a.py", "src/b.py"],
            "file_count": 2,
            "scope_limit": 200,
            "scope_oversize": False,
            "line_range": None,
            "error": None,
        }
        scope_block = render_scope_block(scope_result, "/myproject")
        brief = render_agent_brief(
            agent="security-reviewer",
            references_dir=str(_REFERENCES_DIR),
            scope_block=scope_block,
            source_root="/myproject",
        )
        self.assertIn("directory", brief)
        self.assertIn("src/a.py", brief)
        self.assertIn("/myproject", brief)

    def test_source_root_in_brief(self):
        # source_root reaches the brief via the rendered scope block
        # (render_agent_brief no longer re-emits a separate Source root line —
        # render_scope_block is the single source of that label).
        scope_block = render_scope_block(
            {
                "scope_kind": "file",
                "pipeline": "simplified",
                "file_count": 1,
                "files": ["src/main.py"],
                "scope_limit": 200,
                "scope_oversize": False,
                "line_range": None,
                "error": None,
            },
            "/custom/root",
        )
        brief = render_agent_brief(
            agent="qa-engineer",
            references_dir=str(_REFERENCES_DIR),
            scope_block=scope_block,
            source_root="/custom/root",
        )
        self.assertIn("/custom/root", brief)
        # Label appears exactly once (no duplication from render_agent_brief).
        self.assertEqual(brief.count("Source root:"), 1)


# ---------------------------------------------------------------------------
# Tests — finding_cap in render_agent_brief (direct function, not CLI)
# ---------------------------------------------------------------------------

class TestRenderAgentBriefFindingCap(unittest.TestCase):
    """Verify finding_cap substitution via direct render_agent_brief calls."""

    def _make_brief(self, finding_cap=30):
        return render_agent_brief(
            agent="code-reviewer",
            references_dir=str(_REFERENCES_DIR),
            scope_block=_make_scope_block(),
            source_root="/repo",
            finding_cap=finding_cap,
        )

    def test_default_cap_no_token_leak(self):
        """Default cap (30) renders no literal __FINDING_CAP__ token."""
        brief = self._make_brief()
        self.assertNotIn("__FINDING_CAP__", brief)

    def test_default_cap_contains_30(self):
        """Default cap inserts '30' where the token was."""
        brief = self._make_brief()
        self.assertIn("Cap: 30 findings", brief)

    def test_cap_58_no_token_leak(self):
        """finding_cap=58 renders no literal __FINDING_CAP__ token."""
        brief = self._make_brief(finding_cap=58)
        self.assertNotIn("__FINDING_CAP__", brief)

    def test_cap_58_contains_58(self):
        """finding_cap=58 inserts '58' where the token was."""
        brief = self._make_brief(finding_cap=58)
        self.assertIn("Cap: 58 findings", brief)

    def test_cap_58_not_default_30(self):
        """finding_cap=58 inserts 58, not 30, in the cap position."""
        brief = self._make_brief(finding_cap=58)
        self.assertIn("up to 58", brief)

    def test_bad_cap_zero_fallback(self):
        """finding_cap=0 falls back to 30."""
        brief = self._make_brief(finding_cap=0)
        self.assertNotIn("__FINDING_CAP__", brief)
        self.assertIn("Cap: 30 findings", brief)

    def test_bad_cap_negative_fallback(self):
        """finding_cap=-1 falls back to 30."""
        brief = self._make_brief(finding_cap=-1)
        self.assertNotIn("__FINDING_CAP__", brief)
        self.assertIn("Cap: 30 findings", brief)


if __name__ == "__main__":
    unittest.main()
