"""Tests for src/devforge/lib/_review/_brief.py and Phase 3 CLI verbs.

Coverage:
  render_agent_brief — all 5 finders present expected sections (verbatim text)
  render_agent_brief — unknown agent raises ValueError
  render_agent_brief — assembly order: preamble before checklist before focus
                       before scope before closing
  render_agent_brief — tmp_path appears in the closing instruction
  render_agent_brief — default tmp_path used when None
  render_agent_brief — missing reference file raises ValueError

  CRITICAL ROUND-TRIP: brief output contract → parse_agent_tmp → validate_findings
    - Positive: single-anchor evidence (anchor file contains the snippet) → passes
    - Negative (dual-file): Evidence quoting partner file's code → quote_mismatch discard
    - Negative (missing): Evidence not present in file at all → quote_mismatch discard

  CLI verb: render-agent-brief — dispatches via main(), exit 0
  CLI verb: consume-tmp        — dispatches via main(), exit 0
  CLI verb: validate-findings  — dispatches via main(), exit 0
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# sys.path wiring — same pattern as all other _review tests
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_REFS_DIR = _REPO_ROOT / "src" / "commands" / "review" / "references"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _review._brief import render_agent_brief, _FOCUS_BLOCKS  # noqa: E402
from _review._cli import main as review_main  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ALL_AGENTS = list(_FOCUS_BLOCKS.keys())
_REFS_DIR_STR = str(_REFS_DIR)


def _load_ref(filename):
    # type: (str) -> str
    """Read a reference file from the real references_dir."""
    path = _REFS_DIR / filename
    with open(str(path), "r", encoding="utf-8") as fh:
        return fh.read()


# Load real reference content once for assertion checks.
_PREAMBLE_TEXT = _load_ref("anti-relitigation-preamble.md")
_CHECKLIST_TEXT = _load_ref("emergent-issue-checklist.md")

# Distinctive sentence from each reference (used for verbatim-contains checks).
_PREAMBLE_SENTINEL = "EMERGENT CROSS-TASK REVIEW — SCOPE DISCIPLINE"
_CHECKLIST_SENTINEL = "EMERGENT CROSS-TASK ISSUE CHECKLIST"


# ---------------------------------------------------------------------------
# TestBriefAssemblyAllAgents
# ---------------------------------------------------------------------------


class TestBriefAssemblyAllAgents(unittest.TestCase):
    """For each of the 5 finders, assert the brief contains all required sections."""

    def _render(self, agent, tmp_path=None):
        return render_agent_brief(
            agent=agent,
            references_dir=_REFS_DIR_STR,
            scope_block="=== Review Scope ===\nFiles: 3\n  src/a.py\n  src/b.py\n  src/c.py",
            tmp_path=tmp_path,
        )

    def test_all_agents_produce_brief(self):
        for agent in _ALL_AGENTS:
            with self.subTest(agent=agent):
                brief = self._render(agent)
                self.assertIsInstance(brief, str)
                self.assertGreater(len(brief), 100)

    def test_preamble_verbatim_present_all_agents(self):
        """Anti-relitigation preamble is present verbatim in every brief."""
        for agent in _ALL_AGENTS:
            with self.subTest(agent=agent):
                brief = self._render(agent)
                self.assertIn(_PREAMBLE_SENTINEL, brief,
                              "preamble sentinel missing for agent {0}".format(agent))

    def test_checklist_verbatim_present_all_agents(self):
        """Emergent-issue checklist is present verbatim in every brief."""
        for agent in _ALL_AGENTS:
            with self.subTest(agent=agent):
                brief = self._render(agent)
                self.assertIn(_CHECKLIST_SENTINEL, brief,
                              "checklist sentinel missing for agent {0}".format(agent))

    def test_focus_block_present_all_agents(self):
        """Each brief contains at least 10 chars of the agent's own focus block."""
        for agent in _ALL_AGENTS:
            with self.subTest(agent=agent):
                brief = self._render(agent)
                focus = _FOCUS_BLOCKS[agent]
                # Use first 50 chars as a distinctive slice.
                self.assertIn(focus[:50], brief,
                              "focus block not present for agent {0}".format(agent))

    def test_scope_block_present_all_agents(self):
        """Pre-rendered scope block appears in every brief."""
        for agent in _ALL_AGENTS:
            with self.subTest(agent=agent):
                brief = self._render(agent)
                self.assertIn("=== Review Scope ===", brief)
                self.assertIn("src/a.py", brief)

    def test_closing_present_all_agents(self):
        """Closing instruction (Bash write command) appears in every brief."""
        for agent in _ALL_AGENTS:
            with self.subTest(agent=agent):
                brief = self._render(agent)
                # The closing includes the write-command HEREDOC marker.
                self.assertIn("REVIEW_FINDINGS_EOF", brief)

    def test_tmp_path_in_closing(self):
        """Custom tmp_path is emitted in the closing instruction."""
        brief = self._render("code-reviewer", tmp_path="/tmp/forge-review/.tmp-code-reviewer.md")
        self.assertIn("/tmp/forge-review/.tmp-code-reviewer.md", brief)

    def test_default_tmp_path_when_none(self):
        """Default tmp_path token appears in the closing when no override given."""
        brief = self._render("architect")
        self.assertIn("specs/.tmp-{agent-name}.md", brief)

    def test_agent_name_in_closing(self):
        """Agent name is substituted into the closing Bash command."""
        for agent in _ALL_AGENTS:
            with self.subTest(agent=agent):
                brief = self._render(agent)
                # The closing says "# Agent: <agent>"
                self.assertIn("# Agent: {0}".format(agent), brief)

    def test_no_unresolved_tokens(self):
        """No {tmp_path} or {agent} tokens remain after rendering."""
        for agent in _ALL_AGENTS:
            with self.subTest(agent=agent):
                brief = self._render(agent, tmp_path="/tmp/test.md")
                self.assertNotIn("{tmp_path}", brief)
                self.assertNotIn("{agent}", brief)


# ---------------------------------------------------------------------------
# TestBriefAssemblyOrder
# ---------------------------------------------------------------------------


class TestBriefAssemblyOrder(unittest.TestCase):
    """Assert sections appear in the mandated order."""

    def _render(self, agent="code-reviewer"):
        return render_agent_brief(
            agent=agent,
            references_dir=_REFS_DIR_STR,
            scope_block="=== Scope ===",
        )

    def test_preamble_before_checklist(self):
        brief = self._render()
        preamble_pos = brief.find(_PREAMBLE_SENTINEL)
        checklist_pos = brief.find(_CHECKLIST_SENTINEL)
        self.assertGreater(checklist_pos, preamble_pos,
                           "checklist should appear after preamble")

    def test_checklist_before_focus(self):
        brief = self._render("architect")
        checklist_pos = brief.find(_CHECKLIST_SENTINEL)
        focus_snippet = _FOCUS_BLOCKS["architect"][:40]
        focus_pos = brief.find(focus_snippet)
        self.assertGreater(focus_pos, checklist_pos,
                           "focus block should appear after checklist")

    def test_focus_before_scope(self):
        brief = self._render("qa-reviewer")
        focus_snippet = _FOCUS_BLOCKS["qa-reviewer"][:40]
        focus_pos = brief.find(focus_snippet)
        scope_pos = brief.find("=== Scope ===")
        self.assertGreater(scope_pos, focus_pos,
                           "scope should appear after focus block")

    def test_scope_before_closing(self):
        brief = self._render()
        scope_pos = brief.find("=== Scope ===")
        closing_pos = brief.find("REVIEW_FINDINGS_EOF")
        self.assertGreater(closing_pos, scope_pos,
                           "closing instruction should appear after scope")


# ---------------------------------------------------------------------------
# TestBriefErrorPaths
# ---------------------------------------------------------------------------


class TestBriefErrorPaths(unittest.TestCase):
    """Unknown agent and missing reference file raise ValueError."""

    def test_unknown_agent_raises(self):
        with self.assertRaises(ValueError) as ctx:
            render_agent_brief(
                agent="nonexistent-agent",
                references_dir=_REFS_DIR_STR,
                scope_block="scope",
            )
        self.assertIn("unknown agent", str(ctx.exception))
        self.assertIn("nonexistent-agent", str(ctx.exception))

    def test_missing_preamble_file_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create only the checklist, not the preamble.
            checklist_path = os.path.join(tmpdir, "emergent-issue-checklist.md")
            with open(checklist_path, "w") as fh:
                fh.write("checklist content")
            with self.assertRaises(ValueError) as ctx:
                render_agent_brief(
                    agent="code-reviewer",
                    references_dir=tmpdir,
                    scope_block="scope",
                )
            self.assertIn("anti-relitigation-preamble.md", str(ctx.exception))

    def test_missing_checklist_file_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create only the preamble, not the checklist.
            preamble_path = os.path.join(tmpdir, "anti-relitigation-preamble.md")
            with open(preamble_path, "w") as fh:
                fh.write("preamble content")
            with self.assertRaises(ValueError) as ctx:
                render_agent_brief(
                    agent="code-reviewer",
                    references_dir=tmpdir,
                    scope_block="scope",
                )
            self.assertIn("emergent-issue-checklist.md", str(ctx.exception))

    def test_empty_string_agent_raises(self):
        with self.assertRaises((ValueError, KeyError)):
            render_agent_brief(
                agent="",
                references_dir=_REFS_DIR_STR,
                scope_block="scope",
            )


# ---------------------------------------------------------------------------
# TestBriefFocusBlockContent
# ---------------------------------------------------------------------------


class TestBriefFocusBlockContent(unittest.TestCase):
    """Focus blocks are tuned to emergent cross-task concerns."""

    def test_code_reviewer_mentions_cross_task(self):
        self.assertIn("cross-task", _FOCUS_BLOCKS["code-reviewer"].lower())

    def test_architect_mentions_architectural_drift(self):
        focus = _FOCUS_BLOCKS["architect"].lower()
        self.assertTrue(
            "architectural drift" in focus or "globally inconsistent" in focus,
            "architect focus should reference architectural drift"
        )

    def test_qa_reviewer_mentions_test_gaps(self):
        self.assertIn("test", _FOCUS_BLOCKS["qa-reviewer"].lower())

    def test_security_reviewer_mentions_cross_task_security(self):
        focus = _FOCUS_BLOCKS["security-reviewer"].lower()
        self.assertIn("cross-task", focus)

    def test_performance_analyst_mentions_assembled_data_flow(self):
        focus = _FOCUS_BLOCKS["performance-analyst"].lower()
        self.assertTrue(
            "assembled" in focus or "data flow" in focus,
            "performance-analyst focus should reference assembled data flow"
        )

    def test_five_focus_blocks_defined(self):
        self.assertEqual(len(_FOCUS_BLOCKS), 5)
        expected = {
            "code-reviewer", "architect", "qa-reviewer",
            "security-reviewer", "performance-analyst",
        }
        self.assertEqual(set(_FOCUS_BLOCKS.keys()), expected)


# ---------------------------------------------------------------------------
# TestCriticalRoundTrip  — THE CRITICAL TEST
# ---------------------------------------------------------------------------


class TestCriticalRoundTrip(unittest.TestCase):
    """Round-trip: brief output contract → parse_agent_tmp → validate_findings.

    The brief instructs agents to produce a ## Finding N block following the
    single-anchor evidence contract: the `Evidence:` block quotes ONLY the
    anchor file named in `File:`, and the partner file is named by path+line
    in `Why it's wrong:` prose.

    These tests:
      1. Positive round-trip: a finding with single-anchor evidence (anchor
         file contains the quoted snippet) → parses + passes validate_findings.
      2. Negative test: a finding whose Evidence block contains a snippet that
         is NOT present in the anchor file (someone tried to quote the partner
         file's code) → validate_findings DISCARDS it (reason = quote_mismatch).
         This locks in the single-anchor constraint and guards against a future
         regression that re-introduces two-file evidence.

    Both round-trip via the REAL parse_agent_tmp + validate_findings from
    _shared._consume / _shared._validate (no hand-rolled parse stubs).
    """

    def setUp(self):
        from _shared._consume import parse_agent_tmp  # type: ignore[import]
        from _shared._validate import validate_findings  # type: ignore[import]
        self.parse_agent_tmp = parse_agent_tmp
        self.validate_findings = validate_findings

    def _make_source_file(self, tmpdir, rel_path, content):
        # type: (str, str, str) -> str
        """Write a source file under tmpdir/rel_path and return rel_path."""
        abs_path = os.path.join(tmpdir, rel_path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return rel_path

    def test_round_trip_full_pipeline(self):
        """Single-anchor evidence: anchor file contains the quoted snippet → passes.

        Contract (corrected, per emergent-issue-checklist.md Grounding rule):
        - `File:` names the ANCHOR file — the defect/bypass site.
        - `Evidence:` is a verbatim snippet copied from the anchor file ONLY.
        - `Why it's wrong:` names the PARTNER file by path+line in prose.
        - No `// from <fileA>` / `// from <fileB>` separators; no second file's
          code inside `Evidence:`.

        The validator checks that Evidence is a whitespace-normalised substring
        of the anchor file.  This test proves that a correctly-formed single-
        anchor finding is NOT discarded.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # --- 1. Create the anchor file (src/bulk.py) ---
            # Contains the bypass/defect site: bulk_import calls process()
            # without going through the require_admin guard.
            anchor_content = (
                "# src/bulk.py — task B implementation\n"
                "\n"
                "def bulk_import(user, items):\n"
                "    # TODO: this path skips the auth guard added by task A\n"
                "    for item in items:\n"
                "        process(item)\n"
            )
            self._make_source_file(tmpdir, "src/bulk.py", anchor_content)

            # The evidence is a verbatim slice from bulk.py (lines 3-6).
            # No second file's code — only the anchor file's content.
            evidence_snippet = (
                "def bulk_import(user, items):\n"
                "    # TODO: this path skips the auth guard added by task A\n"
                "    for item in items:\n"
                "        process(item)\n"
            )

            # --- 2. Construct agent output in the shape the brief prescribes ---
            # Severity / File / Line / Pattern / Confidence / Category /
            # Evidence (single anchor snippet) / Why it's wrong (partner in prose)
            # / Remediation
            agent_output = (
                "# Agent: security-reviewer\n"
                "# Status: complete\n"
                "# Finding count: 1\n"
                "\n"
                "## Finding 1\n"
                "Severity: High\n"
                "File: src/bulk.py\n"
                "Line: 3\n"
                "Pattern: Auth boundary bypass across tasks\n"
                "Confidence: Certain\n"
                "Category: security\n"
                "Evidence:\n"
                "```\n"
                + evidence_snippet
                + "```\n"
                "Why it's wrong: task A (src/auth.py:12) established require_admin as the "
                "mandatory guard before any downstream process() call; task B's bulk_import "
                "reaches process() directly without going through that boundary.\n"
                "Remediation: Add require_admin(user) call at the top of bulk_import.\n"
                "\n"
                "## Top 5 Priorities (this agent only)\n"
                "1. Finding #1 — Auth boundary bypass in bulk_import\n"
            )

            # --- 3. Feed through the REAL parse_agent_tmp ---
            result = self.parse_agent_tmp(agent_output, agent_name="security-reviewer")

            self.assertEqual(result["status"], "complete",
                             "expected complete, got: {0}".format(result.get("reason", "")))
            self.assertEqual(result["finding_count"], 1)
            self.assertEqual(len(result["findings"]), 1)

            finding = result["findings"][0]
            self.assertEqual(finding["agent"], "security-reviewer")
            self.assertEqual(finding["severity"], "High")
            self.assertEqual(finding["file"], "src/bulk.py")
            self.assertEqual(finding["line"], 3)
            self.assertEqual(finding["pattern"], "Auth boundary bypass across tasks")
            self.assertEqual(finding["confidence"], "Certain")
            self.assertEqual(finding["category"], "security")
            # Evidence is non-empty and contains only the anchor file's content.
            self.assertTrue(finding["evidence"], "evidence field must be non-empty")
            self.assertIn("bulk_import", finding["evidence"])
            # Partner file is NOT in Evidence — it appears only in the prose why.
            self.assertNotIn("src/auth.py", finding["evidence"])
            # Why it's wrong names the partner file.
            self.assertIn("src/auth.py", finding["why"])

            # --- 4. Feed through the REAL validate_findings ---
            validate_result = self.validate_findings(
                [finding],
                repo_root=tmpdir,
                source_root="",
            )

            # The finding MUST PASS — single-anchor evidence is in the anchor file.
            self.assertEqual(
                len(validate_result["passed"]), 1,
                "single-anchor finding should pass validation; discarded: {0}".format(
                    [d["reason"] for d in validate_result["discarded"]]
                ),
            )
            self.assertEqual(len(validate_result["discarded"]), 0,
                             "no findings should be discarded for single-anchor evidence")

    def test_dual_file_evidence_is_discarded(self):
        """Dual-file Evidence (quoting the partner file's code) is discarded.

        This is the negative test that locks in the single-anchor constraint.

        If a finder violates the contract by putting two files' code in the
        Evidence block (separated by `// from <file>` markers or otherwise),
        the combined block is a substring of NEITHER anchor file alone.
        validate_findings MUST discard it with reason 'quote_mismatch'.

        This guards against a future regression that re-introduces two-file
        evidence (the old contract that was corrected).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # The anchor file: only contains bulk.py's code.
            anchor_content = (
                "def bulk_import(user, items):\n"
                "    for item in items:\n"
                "        process(item)\n"
            )
            self._make_source_file(tmpdir, "src/bulk.py", anchor_content)

            # Partner file: contains auth guard code — NOT in bulk.py.
            # We do NOT need the partner file to exist for the test;
            # we only need evidence that cites code from it inside the Evidence block.

            # Evidence block mixes anchor code + partner code (the OLD shape).
            # The combined text is NOT a substring of src/bulk.py alone.
            dual_evidence_snippet = (
                "// from src/auth.py\n"
                "def require_admin(user):\n"
                "    if not user.is_admin:\n"
                "        raise PermissionError('admin required')\n"
                "\n"
                "// from src/bulk.py\n"
                "def bulk_import(user, items):\n"
                "    for item in items:\n"
                "        process(item)\n"
            )

            agent_output = (
                "# Agent: security-reviewer\n"
                "# Status: complete\n"
                "# Finding count: 1\n"
                "\n"
                "## Finding 1\n"
                "Severity: High\n"
                "File: src/bulk.py\n"
                "Line: 1\n"
                "Pattern: Auth boundary bypass across tasks\n"
                "Confidence: Certain\n"
                "Category: security\n"
                "Evidence:\n"
                "```\n"
                + dual_evidence_snippet
                + "```\n"
                "Why it's wrong: bulk_import bypasses require_admin.\n"
                "Remediation: Add require_admin(user) at the top of bulk_import.\n"
            )

            result = self.parse_agent_tmp(agent_output, agent_name="security-reviewer")
            self.assertEqual(result["finding_count"], 1)

            finding = result["findings"][0]
            validate_result = self.validate_findings(
                [finding],
                repo_root=tmpdir,
                source_root="",
            )

            # The finding MUST be discarded — dual-file evidence is not a
            # substring of the single anchor file.
            self.assertEqual(
                len(validate_result["passed"]), 0,
                "dual-file evidence must be discarded; unexpectedly passed",
            )
            self.assertEqual(len(validate_result["discarded"]), 1)
            self.assertEqual(
                validate_result["discarded"][0]["reason"],
                "quote_mismatch",
                "dual-file evidence must be discarded with reason 'quote_mismatch'",
            )

    def test_round_trip_missing_evidence_is_discarded(self):
        """A finding with no Evidence block is discarded by validate_findings.

        Defensive negative case — proves the validator is checking, not passing
        everything through.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src_content = "def foo(): pass\n"
            self._make_source_file(tmpdir, "src/foo.py", src_content)

            agent_output = (
                "# Agent: code-reviewer\n"
                "# Status: complete\n"
                "# Finding count: 1\n"
                "\n"
                "## Finding 1\n"
                "Severity: Medium\n"
                "File: src/foo.py\n"
                "Line: 1\n"
                "Pattern: Some pattern\n"
                "Confidence: Likely\n"
                "Category: mislogic\n"
                "Evidence:\n"
                "```\n"
                "this text does not appear in the real file at all xyz_sentinel_12345\n"
                "```\n"
                "Why it's wrong: reason\n"
                "Remediation: fix\n"
            )

            result = self.parse_agent_tmp(agent_output, agent_name="code-reviewer")
            self.assertEqual(result["finding_count"], 1)

            finding = result["findings"][0]
            validate_result = self.validate_findings(
                [finding],
                repo_root=tmpdir,
                source_root="",
            )

            # The finding MUST be discarded — evidence not present in file.
            self.assertEqual(len(validate_result["passed"]), 0,
                             "finding with non-verbatim evidence must be discarded")
            self.assertEqual(len(validate_result["discarded"]), 1)
            self.assertEqual(validate_result["discarded"][0]["reason"], "quote_mismatch")


# ---------------------------------------------------------------------------
# TestCliConsumeTmp
# ---------------------------------------------------------------------------


class TestCliConsumeTmp(unittest.TestCase):
    """consume-tmp verb dispatches to _shared parse_agent_tmp and exits 0."""

    def test_consume_tmp_valid_file(self):
        agent_content = (
            "# Agent: qa-reviewer\n"
            "# Status: complete\n"
            "# Finding count: 0\n"
        )
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(agent_content)
            tmp_path = fh.name

        try:
            captured = []
            orig_write = sys.stdout.write

            def capture_write(s):
                captured.append(s)
                return orig_write(s)

            sys.stdout.write = capture_write  # type: ignore[method-assign]
            try:
                rc = review_main(["consume-tmp", "--tmp", tmp_path, "--agent", "qa-reviewer"])
            finally:
                sys.stdout.write = orig_write

            self.assertEqual(rc, 0)
            output = "".join(captured)
            data = json.loads(output)
            self.assertIn("status", data)
            self.assertEqual(data["agent"], "qa-reviewer")
            self.assertEqual(data["finding_count"], 0)
        finally:
            os.unlink(tmp_path)

    def test_consume_tmp_missing_file_exits_2(self):
        rc = review_main(
            ["consume-tmp", "--tmp", "/nonexistent/path/xyz.md"]
        )
        self.assertEqual(rc, 2)

    def test_consume_tmp_requires_tmp_arg(self):
        # argparse raises SystemExit(2) for missing required args.
        with self.assertRaises(SystemExit) as ctx:
            review_main(["consume-tmp"])
        self.assertEqual(ctx.exception.code, 2)


# ---------------------------------------------------------------------------
# TestCliValidateFindings
# ---------------------------------------------------------------------------


class TestCliValidateFindings(unittest.TestCase):
    """validate-findings verb dispatches to _shared validate_findings and exits 0."""

    def test_validate_findings_empty_list(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump([], fh)
            findings_path = fh.name

        try:
            captured = []
            orig_write = sys.stdout.write

            def capture_write(s):
                captured.append(s)
                return orig_write(s)

            sys.stdout.write = capture_write  # type: ignore[method-assign]
            try:
                rc = review_main([
                    "validate-findings",
                    "--findings", findings_path,
                    "--repo-root", str(_REPO_ROOT),
                ])
            finally:
                sys.stdout.write = orig_write

            self.assertEqual(rc, 0)
            output = "".join(captured)
            data = json.loads(output)
            self.assertIn("passed", data)
            self.assertIn("discarded", data)
            self.assertEqual(data["passed"], [])
            self.assertEqual(data["discarded"], [])
        finally:
            os.unlink(findings_path)

    def test_validate_findings_missing_file_exits_2(self):
        rc = review_main([
            "validate-findings",
            "--findings", "/nonexistent/findings.json",
        ])
        self.assertEqual(rc, 2)

    def test_validate_findings_requires_findings_arg(self):
        # argparse raises SystemExit(2) for missing required args.
        with self.assertRaises(SystemExit) as ctx:
            review_main(["validate-findings"])
        self.assertEqual(ctx.exception.code, 2)

    def test_validate_findings_non_array_json_exits_2(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as fh:
            json.dump({"not": "an array"}, fh)
            findings_path = fh.name

        try:
            rc = review_main([
                "validate-findings",
                "--findings", findings_path,
                "--repo-root", ".",
            ])
            self.assertEqual(rc, 2)
        finally:
            os.unlink(findings_path)


# ---------------------------------------------------------------------------
# TestCliRenderAgentBrief
# ---------------------------------------------------------------------------


class TestCliRenderAgentBrief(unittest.TestCase):
    """render-agent-brief verb assembles brief and exits 0."""

    def test_render_agent_brief_all_agents(self):
        """Each of the 5 agents produces a non-empty brief via the CLI."""
        for agent in _ALL_AGENTS:
            with self.subTest(agent=agent):
                scope_text = "=== Review Scope ===\nFiles: 2\n  src/a.py\n  src/b.py\n"
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", delete=False, encoding="utf-8"
                ) as scope_fh:
                    scope_fh.write(scope_text)
                    scope_path = scope_fh.name

                try:
                    captured = []
                    orig_write = sys.stdout.write

                    def capture_write(s):
                        captured.append(s)
                        return orig_write(s)

                    sys.stdout.write = capture_write  # type: ignore[method-assign]
                    try:
                        rc = review_main([
                            "render-agent-brief",
                            "--agent", agent,
                            "--scope-block", scope_path,
                            "--references-dir", _REFS_DIR_STR,
                        ])
                    finally:
                        sys.stdout.write = orig_write

                    self.assertEqual(rc, 0,
                                     "exit code should be 0 for agent {0}".format(agent))
                    output = "".join(captured)
                    self.assertIn(_PREAMBLE_SENTINEL, output)
                    self.assertIn(_CHECKLIST_SENTINEL, output)
                    self.assertIn("=== Review Scope ===", output)
                finally:
                    os.unlink(scope_path)

    def test_render_agent_brief_unknown_agent_exits_2(self):
        scope_text = "scope block"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(scope_text)
            scope_path = fh.name

        try:
            rc = review_main([
                "render-agent-brief",
                "--agent", "no-such-agent",
                "--scope-block", scope_path,
                "--references-dir", _REFS_DIR_STR,
            ])
            self.assertEqual(rc, 2)
        finally:
            os.unlink(scope_path)

    def test_render_agent_brief_missing_scope_block_arg_exits_2(self):
        # argparse raises SystemExit(2) for missing required args.
        with self.assertRaises(SystemExit) as ctx:
            review_main([
                "render-agent-brief",
                "--agent", "code-reviewer",
                "--references-dir", _REFS_DIR_STR,
            ])
        self.assertEqual(ctx.exception.code, 2)

    def test_render_agent_brief_requires_agent_arg(self):
        scope_text = "scope block"
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(scope_text)
            scope_path = fh.name

        try:
            # argparse raises SystemExit(2) for missing required args.
            with self.assertRaises(SystemExit) as ctx:
                review_main([
                    "render-agent-brief",
                    "--scope-block", scope_path,
                    "--references-dir", _REFS_DIR_STR,
                ])
            self.assertEqual(ctx.exception.code, 2)
        finally:
            os.unlink(scope_path)


# ---------------------------------------------------------------------------
# TestNoAuditImports
# ---------------------------------------------------------------------------


class TestNoAuditImports(unittest.TestCase):
    """_brief.py and _cli.py import nothing from _audit."""

    def test_brief_module_does_not_import_audit(self):
        from _review import _brief  # noqa: F401
        import _review._brief as brief_mod
        # Walk imported submodules: none should be from _audit.
        for name in list(sys.modules.keys()):
            if name.startswith("_audit"):
                # Only allowed if it was already loaded by another test module.
                # The brief module itself should not have triggered this import.
                # We check by verifying brief_mod doesn't reference _audit directly.
                pass
        # Check the source code text for any direct import of _audit.
        import inspect
        src = inspect.getsource(brief_mod)
        self.assertNotIn("from _audit", src)
        self.assertNotIn("import _audit", src)

    def test_cli_module_phase3_handlers_do_not_import_audit(self):
        import inspect
        from _review import _cli as cli_mod
        src = inspect.getsource(cli_mod)
        # _cli.py is allowed to import _shared but not _audit.
        self.assertNotIn("from _audit", src)
        self.assertNotIn("import _audit", src)


if __name__ == "__main__":
    unittest.main()
