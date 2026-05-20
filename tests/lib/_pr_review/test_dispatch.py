"""Tests for src/devforge/lib/_pr_review/_dispatch.py (PR-REVIEW Step 8).

Coverage:
  _section_metadata        — minimal vs full state; missing fields handled
  _section_ticket_text     — short text passthrough; long text truncation marker
  _section_linked_issues   — empty list → "_None._"; multiple URLs
  _section_diff            — under cap unchanged; over cap excerpted with mid marker
  _section_smells          — empty list → "_No smells._"; multiple smells formatted
  _section_blast           — unfilled probes render as TODO; filled → resolved
  _section_drift           — bullets only (coverage empty); with coverage_matrix
  _section_bundle          — constitution/constitute_json/concern_docs/adrs/plans/handoffs
  _section_instructions    — standard text emitted; includes brief_size_chars
  _excerpt_diff            — short pass-through; long → middle truncated with marker
  _truncate                — under cap unchanged; over cap with marker
  run (happy path)         — full populated state → brief.md written + summary JSON keys
  run (minimal state)      — state with only intake fields → brief still written
  run (no state file)      — missing → ValueError
  brief size               — synthetic large state → brief written
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
_LIB_DIR = os.path.join(_REPO_ROOT, "src", "devforge", "lib")
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _pr_review._dispatch import (  # noqa: E402
    _BRIEF_TOTAL_TARGET,
    _DIFF_CAP,
    _excerpt_diff,
    _section_blast,
    _section_bundle,
    _section_diff,
    _section_drift,
    _section_instructions,
    _section_linked_issues,
    _section_metadata,
    _section_smells,
    _section_ticket_text,
    _truncate,
    run,
)
from _pr_review._state import PRReviewState  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _make_state(**kwargs) -> PRReviewState:
    """Return a PRReviewState with optional field overrides."""
    return PRReviewState(**kwargs)


def _make_full_state(tmp_devforge: str, pr_number: int = 42) -> PRReviewState:
    """Return a PRReviewState with all major sections populated."""
    return PRReviewState(
        pr_number=pr_number,
        repo="acme/myapp",
        diff=(
            "diff --git a/src/foo.py b/src/foo.py\n"
            "index abc..def 100644\n"
            "--- a/src/foo.py\n"
            "+++ b/src/foo.py\n"
            "@@ -1,2 +1,3 @@\n"
            "+def bar():\n"
            "+    return 42\n"
        ),
        pr_body="## Summary\n- Added bar()\n",
        linked_issues=["https://github.com/acme/myapp/issues/10"],
        ticket_text="MIG-100: Add bar function\nAC-1: bar returns 42.",
        commit_subjects=["feat: add bar function"],
        smells=[
            {
                "name": "empty_pr_body",
                "severity": "medium",
                "location": "*",
                "evidence": "PR body is empty",
            }
        ],
        blast=[
            {
                "symbol": "bar",
                "file": "src/foo.py",
                "kind": "function",
                "language": "python",
                "diff_line_hint": "diff:line+0",
                "mcp_hints": {
                    "trace_path_in": "bar",
                    "trace_path_out": "bar",
                    "data_flow": "bar",
                },
                "callers": [],
                "callees": [],
                "data_flow_targets": [],
                "tests_referencing": [],
                "filled": False,
            }
        ],
        drift={
            "bullets": [
                {
                    "id": "B1",
                    "text": "bar returns 42",
                    "source": "ticket_text",
                    "extracted_via": "ac_marker",
                }
            ],
            "coverage_matrix": [],
            "scope_creep_files": [],
            "filled": False,
        },
        bundle={
            "constitution_md": "/tmp/constitution.md",
            "constitution_md_content": "# Constitution\nSOLID rules here.",
            "constitute_json": {"primary_language": "python"},
            "concern_docs": [
                {
                    "concern": "auth",
                    "overview_path": "/tmp/docs/auth/overview.md",
                    "overview_content": "Auth overview content.",
                    "architecture_path": "/tmp/docs/auth/architecture.md",
                    "architecture_content": "Auth architecture content.",
                }
            ],
            "adrs": [
                {
                    "path": "/tmp/docs/adrs/001-use-jwt.md",
                    "filename": "001-use-jwt.md",
                    "content": "# ADR 001\nUse JWT for auth.",
                }
            ],
            "plan_files": [
                {
                    "path": "/tmp/AUTH-PLAN.md",
                    "name": "AUTH-PLAN.md",
                    "content": "# Auth plan\nPhase 1: ...",
                }
            ],
            "research_handoffs": [
                {
                    "path": "/tmp/research/2026-05-01-auth/handoff.json",
                    "date": "2026-05-01",
                    "slug": "auth",
                    "verdict": "proceed",
                    "mode": "bug",
                    "matched_via": "ticket_text_substring",
                    "content_excerpt": '{"verdict": "proceed", "mode": "bug"}',
                }
            ],
        },
        findings=[],
    )


def _write_state_to_disk(state: PRReviewState, devforge_dir: str) -> str:
    """Write state to disk and return the state_path."""
    from _pr_review._state import state_path as _state_path
    sp = _state_path(devforge_dir, state.pr_number)
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    with open(sp, "w", encoding="utf-8") as fh:
        json.dump(dataclasses.asdict(state), fh, indent=2)
        fh.write("\n")
    return sp


# ---------------------------------------------------------------------------
# TestTruncate
# ---------------------------------------------------------------------------


class TestTruncate(unittest.TestCase):
    def test_under_cap_unchanged(self):
        text = "hello world"
        self.assertEqual(_truncate(text, 100), text)

    def test_exact_cap_unchanged(self):
        text = "a" * 50
        self.assertEqual(_truncate(text, 50), text)

    def test_over_cap_appends_marker(self):
        text = "a" * 100
        result = _truncate(text, 50)
        self.assertTrue(result.startswith("a" * 50))
        self.assertIn("... [truncated]", result)

    def test_over_cap_custom_marker(self):
        text = "b" * 100
        result = _truncate(text, 10, marker="[cut]")
        self.assertEqual(result, "b" * 10 + "[cut]")

    def test_empty_string_unchanged(self):
        self.assertEqual(_truncate("", 50), "")

    def test_marker_not_added_when_exactly_cap(self):
        text = "x" * 5
        result = _truncate(text, 5)
        self.assertNotIn("[truncated]", result)
        self.assertEqual(result, text)


# ---------------------------------------------------------------------------
# TestExcerptDiff
# ---------------------------------------------------------------------------


class TestExcerptDiff(unittest.TestCase):
    def test_short_diff_unchanged(self):
        diff = "diff --git a/f.py b/f.py\n+x = 1\n"
        result = _excerpt_diff(diff, cap=10000)
        self.assertEqual(result, diff)

    def test_exact_cap_unchanged(self):
        diff = "x" * _DIFF_CAP
        result = _excerpt_diff(diff)
        self.assertEqual(result, diff)

    def test_long_diff_has_mid_marker(self):
        diff = "a" * (_DIFF_CAP + 100)
        result = _excerpt_diff(diff)
        self.assertIn("... [truncated mid-diff] ...", result)

    def test_long_diff_starts_with_first_half(self):
        diff = "A" * (_DIFF_CAP + 200) + "Z" * 100
        half = _DIFF_CAP // 2
        result = _excerpt_diff(diff)
        self.assertEqual(result[:half], "A" * half)

    def test_long_diff_ends_with_last_half(self):
        diff = "A" * 200 + "Z" * (_DIFF_CAP + 200)
        half = _DIFF_CAP // 2
        result = _excerpt_diff(diff)
        self.assertTrue(result.endswith("Z" * half))

    def test_empty_diff_unchanged(self):
        self.assertEqual(_excerpt_diff(""), "")


# ---------------------------------------------------------------------------
# TestSectionMetadata
# ---------------------------------------------------------------------------


class TestSectionMetadata(unittest.TestCase):
    def test_header_present(self):
        state = _make_state(pr_number=42, repo="acme/app")
        result = _section_metadata(state)
        self.assertIn("## Metadata", result)

    def test_repo_rendered(self):
        state = _make_state(pr_number=1, repo="owner/repo")
        result = _section_metadata(state)
        self.assertIn("owner/repo", result)

    def test_pr_url_derived_from_repo_and_number(self):
        state = _make_state(pr_number=99, repo="acme/app")
        result = _section_metadata(state)
        self.assertIn("https://github.com/acme/app/pull/99", result)

    def test_pr_url_not_available_when_no_repo(self):
        state = _make_state(pr_number=0, repo="")
        result = _section_metadata(state)
        self.assertIn("not available", result)

    def test_files_changed_counted_from_diff(self):
        state = _make_state(
            pr_number=1,
            repo="a/b",
            diff=(
                "diff --git a/f1.py b/f1.py\n+x=1\n"
                "diff --git a/f2.py b/f2.py\n+y=2\n"
            ),
        )
        result = _section_metadata(state)
        self.assertIn("2", result)

    def test_reviewer_line_present(self):
        state = _make_state(pr_number=1, repo="a/b")
        result = _section_metadata(state)
        self.assertIn("cavecrew-reviewer", result)

    def test_author_assumption_present(self):
        state = _make_state(pr_number=1, repo="a/b")
        result = _section_metadata(state)
        self.assertIn("time-constrained", result)


# ---------------------------------------------------------------------------
# TestSectionTicketText
# ---------------------------------------------------------------------------


class TestSectionTicketText(unittest.TestCase):
    def test_header_present(self):
        state = _make_state(ticket_text="some text")
        result = _section_ticket_text(state)
        self.assertIn("## Ticket text", result)

    def test_short_text_passthrough(self):
        state = _make_state(ticket_text="short ticket text")
        result = _section_ticket_text(state)
        self.assertIn("short ticket text", result)

    def test_long_text_truncated(self):
        state = _make_state(ticket_text="T" * 25000)
        result = _section_ticket_text(state)
        self.assertIn("[truncated at 20000 chars]", result)

    def test_long_text_starts_with_original(self):
        state = _make_state(ticket_text="A" * 25000)
        result = _section_ticket_text(state)
        self.assertIn("A" * 100, result)

    def test_empty_text_placeholder(self):
        state = _make_state(ticket_text="")
        result = _section_ticket_text(state)
        self.assertIn("_No ticket text provided._", result)


# ---------------------------------------------------------------------------
# TestSectionLinkedIssues
# ---------------------------------------------------------------------------


class TestSectionLinkedIssues(unittest.TestCase):
    def test_header_present(self):
        state = _make_state()
        result = _section_linked_issues(state)
        self.assertIn("## Linked issues", result)

    def test_empty_list_placeholder(self):
        state = _make_state(linked_issues=[])
        result = _section_linked_issues(state)
        self.assertIn("_None._", result)

    def test_single_url_rendered(self):
        state = _make_state(
            linked_issues=["https://github.com/acme/app/issues/1"]
        )
        result = _section_linked_issues(state)
        self.assertIn("https://github.com/acme/app/issues/1", result)

    def test_multiple_urls_all_rendered(self):
        urls = [
            "https://github.com/acme/app/issues/1",
            "https://github.com/acme/app/issues/2",
            "https://github.com/acme/app/issues/3",
        ]
        state = _make_state(linked_issues=urls)
        result = _section_linked_issues(state)
        for url in urls:
            self.assertIn(url, result)

    def test_each_url_on_bullet(self):
        state = _make_state(
            linked_issues=["https://github.com/acme/app/issues/5"]
        )
        result = _section_linked_issues(state)
        self.assertIn("- https://github.com/acme/app/issues/5", result)


# ---------------------------------------------------------------------------
# TestSectionDiff
# ---------------------------------------------------------------------------


class TestSectionDiff(unittest.TestCase):
    def test_header_present(self):
        state = _make_state(diff="diff --git a/f.py b/f.py\n+x=1\n")
        result = _section_diff(state)
        self.assertIn("## Diff", result)

    def test_short_diff_unchanged(self):
        diff = "diff --git a/f.py b/f.py\n+x = 1\n"
        state = _make_state(diff=diff)
        result = _section_diff(state)
        self.assertIn(diff, result)

    def test_over_cap_has_truncation_marker(self):
        diff = "A" * (_DIFF_CAP + 1000)
        state = _make_state(diff=diff)
        result = _section_diff(state, cap=_DIFF_CAP)
        self.assertIn("... [truncated mid-diff] ...", result)

    def test_empty_diff_placeholder(self):
        state = _make_state(diff="")
        result = _section_diff(state)
        self.assertIn("_No diff available._", result)


# ---------------------------------------------------------------------------
# TestSectionSmells
# ---------------------------------------------------------------------------


class TestSectionSmells(unittest.TestCase):
    def test_header_present(self):
        state = _make_state(smells=[])
        result = _section_smells(state)
        self.assertIn("## Code-smell findings (Step 4)", result)

    def test_empty_smells_placeholder(self):
        state = _make_state(smells=[])
        result = _section_smells(state)
        self.assertIn("_No smells detected._", result)

    def test_single_smell_formatted(self):
        state = _make_state(smells=[
            {
                "name": "empty_pr_body",
                "severity": "medium",
                "location": "*",
                "evidence": "PR body is empty",
            }
        ])
        result = _section_smells(state)
        self.assertIn("[medium]", result)
        self.assertIn("empty_pr_body", result)
        self.assertIn("PR body is empty", result)

    def test_multiple_smells_all_rendered(self):
        state = _make_state(smells=[
            {"name": "smell_a", "severity": "high", "location": "f.py", "evidence": "ev-a"},
            {"name": "smell_b", "severity": "low", "location": "*", "evidence": "ev-b"},
        ])
        result = _section_smells(state)
        self.assertIn("smell_a", result)
        self.assertIn("smell_b", result)
        self.assertIn("[high]", result)
        self.assertIn("[low]", result)
        self.assertIn("ev-a", result)
        self.assertIn("ev-b", result)

    def test_severity_in_brackets(self):
        state = _make_state(smells=[
            {"name": "x", "severity": "nit", "location": "f.py", "evidence": "e"}
        ])
        result = _section_smells(state)
        self.assertIn("**[nit]**", result)


# ---------------------------------------------------------------------------
# TestSectionBlast
# ---------------------------------------------------------------------------


class TestSectionBlast(unittest.TestCase):
    def test_header_present(self):
        state = _make_state(blast=[])
        result = _section_blast(state)
        self.assertIn("## Blast-radius probe specs (Step 5)", result)

    def test_empty_blast_placeholder(self):
        state = _make_state(blast=[])
        result = _section_blast(state)
        self.assertIn("_No blast-radius probe specs extracted._", result)

    def test_unfilled_probe_rendered_as_todo(self):
        state = _make_state(blast=[
            {
                "symbol": "myFunc",
                "file": "src/utils.py",
                "kind": "function",
                "language": "python",
                "diff_line_hint": "diff:line+0",
                "mcp_hints": {
                    "trace_path_in": "myFunc",
                    "trace_path_out": "myFunc",
                    "data_flow": "myFunc",
                },
                "callers": [],
                "callees": [],
                "data_flow_targets": [],
                "tests_referencing": [],
                "filled": False,
            }
        ])
        result = _section_blast(state)
        self.assertIn("myFunc", result)
        self.assertIn("mcp__codebase-memory-mcp__trace_path", result)
        self.assertIn("trace_path_in", result)
        self.assertIn("trace_path_out", result)
        self.assertIn("data_flow", result)

    def test_unfilled_probe_header_has_kind_and_language(self):
        state = _make_state(blast=[
            {
                "symbol": "MyClass",
                "file": "src/model.py",
                "kind": "class",
                "language": "python",
                "diff_line_hint": "diff:line+0",
                "mcp_hints": {
                    "trace_path_in": "MyClass",
                    "trace_path_out": "MyClass",
                    "data_flow": "MyClass",
                },
                "callers": [],
                "callees": [],
                "data_flow_targets": [],
                "tests_referencing": [],
                "filled": False,
            }
        ])
        result = _section_blast(state)
        self.assertIn("class", result)
        self.assertIn("python", result)

    def test_filled_probe_rendered_as_resolved(self):
        state = _make_state(blast=[
            {
                "symbol": "authService",
                "file": "src/auth.ts",
                "kind": "function",
                "language": "typescript",
                "diff_line_hint": "diff:line+0",
                "mcp_hints": {
                    "trace_path_in": "authService",
                    "trace_path_out": "authService",
                    "data_flow": "authService",
                },
                "callers": ["loginController"],
                "callees": ["jwtSign"],
                "data_flow_targets": ["sessionStore"],
                "tests_referencing": ["test_auth.ts"],
                "filled": True,
            }
        ])
        result = _section_blast(state)
        self.assertIn("(resolved)", result)
        self.assertIn("loginController", result)
        self.assertIn("jwtSign", result)
        self.assertIn("sessionStore", result)
        self.assertIn("test_auth.ts", result)

    def test_filled_probe_does_not_render_mcp_hints(self):
        state = _make_state(blast=[
            {
                "symbol": "doThing",
                "file": "f.py",
                "kind": "function",
                "language": "python",
                "diff_line_hint": "diff:line+0",
                "mcp_hints": {
                    "trace_path_in": "doThing",
                    "trace_path_out": "doThing",
                    "data_flow": "doThing",
                },
                "callers": [],
                "callees": [],
                "data_flow_targets": [],
                "tests_referencing": [],
                "filled": True,
            }
        ])
        result = _section_blast(state)
        # Resolved section should NOT show the MCP invocation instructions.
        self.assertNotIn("mcp__codebase-memory-mcp__trace_path", result)


# ---------------------------------------------------------------------------
# TestSectionDrift
# ---------------------------------------------------------------------------


class TestSectionDrift(unittest.TestCase):
    def test_header_present(self):
        state = _make_state(drift={})
        result = _section_drift(state)
        self.assertIn("## Scope-drift bullets (Step 7)", result)

    def test_empty_drift_placeholder(self):
        state = _make_state(drift={})
        result = _section_drift(state)
        self.assertIn("_No scope-drift bullets extracted._", result)

    def test_bullets_rendered(self):
        state = _make_state(drift={
            "bullets": [
                {
                    "id": "B1",
                    "text": "button shows red asterisk",
                    "source": "ticket_text",
                    "extracted_via": "ac_marker",
                }
            ],
            "coverage_matrix": [],
            "scope_creep_files": [],
            "filled": False,
        })
        result = _section_drift(state)
        self.assertIn("B1", result)
        self.assertIn("button shows red asterisk", result)
        self.assertIn("ac_marker", result)
        self.assertIn("ticket_text", result)

    def test_coverage_matrix_not_rendered_when_not_filled(self):
        state = _make_state(drift={
            "bullets": [
                {"id": "B1", "text": "x", "source": "ticket_text", "extracted_via": "ac_marker"}
            ],
            "coverage_matrix": [],
            "scope_creep_files": [],
            "filled": False,
        })
        result = _section_drift(state)
        self.assertNotIn("Coverage status", result)

    def test_coverage_matrix_rendered_when_filled(self):
        state = _make_state(drift={
            "bullets": [
                {"id": "B1", "text": "x", "source": "ticket_text", "extracted_via": "ac_marker"}
            ],
            "coverage_matrix": [
                {
                    "bullet_id": "B1",
                    "status": "satisfied",
                    "evidence": "diff:line+5",
                    "confidence": 0.9,
                }
            ],
            "scope_creep_files": [],
            "filled": True,
        })
        result = _section_drift(state)
        self.assertIn("Coverage status", result)
        self.assertIn("satisfied", result)
        self.assertIn("B1", result)

    def test_reviewer_task_note_present(self):
        state = _make_state(drift={
            "bullets": [
                {"id": "B1", "text": "x", "source": "ticket_text", "extracted_via": "ac_marker"}
            ],
            "coverage_matrix": [],
            "scope_creep_files": [],
            "filled": False,
        })
        result = _section_drift(state)
        self.assertIn("Reviewer task", result)
        self.assertIn("scope_creep_files", result)

    def test_multiple_bullets_all_rendered(self):
        state = _make_state(drift={
            "bullets": [
                {"id": "B1", "text": "first", "source": "ticket_text", "extracted_via": "ac_marker"},
                {"id": "B2", "text": "second", "source": "pr_body", "extracted_via": "markdown_bullet"},
            ],
            "coverage_matrix": [],
            "scope_creep_files": [],
            "filled": False,
        })
        result = _section_drift(state)
        self.assertIn("B1", result)
        self.assertIn("B2", result)
        self.assertIn("first", result)
        self.assertIn("second", result)

    def test_section_drift_handles_null_confidence(self):
        """F1: confidence=null in coverage_matrix must not crash (float(None) fix)."""
        state = _make_state(drift={
            "bullets": [
                {
                    "id": "B1",
                    "text": "foo",
                    "source": "ticket_text",
                    "extracted_via": "ac_marker",
                }
            ],
            "coverage_matrix": [
                {
                    "bullet_id": "B1",
                    "status": "satisfied",
                    "evidence": "x",
                    "confidence": None,
                }
            ],
            "scope_creep_files": [],
            "filled": True,
        })
        # Must not raise TypeError; null confidence → 0.0 displayed.
        try:
            result = _section_drift(state)
        except TypeError as exc:
            self.fail("_section_drift raised TypeError on null confidence: {0}".format(exc))
        self.assertIn("0.0", result)
        self.assertIn("satisfied", result)


# ---------------------------------------------------------------------------
# TestSectionBundle
# ---------------------------------------------------------------------------


class TestSectionBundle(unittest.TestCase):
    def test_header_present(self):
        state = _make_state(bundle={})
        result = _section_bundle(state)
        self.assertIn("## Context bundle (Step 6)", result)

    def test_constitution_content_rendered(self):
        state = _make_state(bundle={
            "constitution_md": "/path/to/constitution.md",
            "constitution_md_content": "# Constitution\nSOLID rules.",
            "constitute_json": None,
            "concern_docs": [],
            "adrs": [],
            "plan_files": [],
            "research_handoffs": [],
        })
        result = _section_bundle(state)
        self.assertIn("# Constitution", result)
        self.assertIn("SOLID rules.", result)

    def test_constitution_absent_placeholder(self):
        state = _make_state(bundle={
            "constitution_md": None,
            "constitution_md_content": "",
            "constitute_json": None,
            "concern_docs": [],
            "adrs": [],
            "plan_files": [],
            "research_handoffs": [],
        })
        result = _section_bundle(state)
        self.assertIn("_Not present._", result)

    def test_constitute_json_rendered(self):
        state = _make_state(bundle={
            "constitution_md_content": "",
            "constitute_json": {"primary_language": "python"},
            "concern_docs": [],
            "adrs": [],
            "plan_files": [],
            "research_handoffs": [],
        })
        result = _section_bundle(state)
        self.assertIn("primary_language", result)
        self.assertIn("python", result)

    def test_constitute_json_absent_placeholder(self):
        state = _make_state(bundle={
            "constitution_md_content": "",
            "constitute_json": None,
            "concern_docs": [],
            "adrs": [],
            "plan_files": [],
            "research_handoffs": [],
        })
        result = _section_bundle(state)
        self.assertIn("_not present_", result)

    def test_concern_docs_rendered(self):
        state = _make_state(bundle={
            "constitution_md_content": "",
            "constitute_json": None,
            "concern_docs": [
                {
                    "concern": "auth",
                    "overview_path": "/docs/auth/overview.md",
                    "overview_content": "Auth overview",
                    "architecture_path": "/docs/auth/arch.md",
                    "architecture_content": "Auth arch",
                }
            ],
            "adrs": [],
            "plan_files": [],
            "research_handoffs": [],
        })
        result = _section_bundle(state)
        self.assertIn("`auth`", result)
        self.assertIn("Auth overview", result)
        self.assertIn("Auth arch", result)

    def test_concern_docs_empty_placeholder(self):
        state = _make_state(bundle={
            "constitution_md_content": "",
            "constitute_json": None,
            "concern_docs": [],
            "adrs": [],
            "plan_files": [],
            "research_handoffs": [],
        })
        result = _section_bundle(state)
        self.assertIn("_None._", result)

    def test_adrs_rendered(self):
        state = _make_state(bundle={
            "constitution_md_content": "",
            "constitute_json": None,
            "concern_docs": [],
            "adrs": [
                {
                    "path": "/adrs/001-jwt.md",
                    "filename": "001-jwt.md",
                    "content": "# ADR 001\nUse JWT.",
                }
            ],
            "plan_files": [],
            "research_handoffs": [],
        })
        result = _section_bundle(state)
        self.assertIn("001-jwt.md", result)

    def test_adrs_capped_at_10(self):
        adrs = [
            {"path": "/adrs/{n}.md".format(n=i), "filename": "{n}.md".format(n=i), "content": "x"}
            for i in range(15)
        ]
        state = _make_state(bundle={
            "constitution_md_content": "",
            "constitute_json": None,
            "concern_docs": [],
            "adrs": adrs,
            "plan_files": [],
            "research_handoffs": [],
        })
        result = _section_bundle(state)
        # Only first 10 shown; 14.md should be absent.
        self.assertNotIn("14.md", result)
        self.assertIn("9.md", result)

    def test_plan_files_rendered(self):
        state = _make_state(bundle={
            "constitution_md_content": "",
            "constitute_json": None,
            "concern_docs": [],
            "adrs": [],
            "plan_files": [
                {
                    "path": "/AUTH-PLAN.md",
                    "name": "AUTH-PLAN.md",
                    "content": "# Auth plan content",
                }
            ],
            "research_handoffs": [],
        })
        result = _section_bundle(state)
        self.assertIn("AUTH-PLAN.md", result)

    def test_plan_files_capped_at_5(self):
        plans = [
            {"path": "/PLAN-{n}.md".format(n=i), "name": "PLAN-{n}.md".format(n=i), "content": "x"}
            for i in range(8)
        ]
        state = _make_state(bundle={
            "constitution_md_content": "",
            "constitute_json": None,
            "concern_docs": [],
            "adrs": [],
            "plan_files": plans,
            "research_handoffs": [],
        })
        result = _section_bundle(state)
        # Only first 5 plans shown; PLAN-7.md absent.
        self.assertNotIn("PLAN-7.md", result)
        self.assertIn("PLAN-4.md", result)

    def test_research_handoffs_rendered(self):
        state = _make_state(bundle={
            "constitution_md_content": "",
            "constitute_json": None,
            "concern_docs": [],
            "adrs": [],
            "plan_files": [],
            "research_handoffs": [
                {
                    "path": "/research/2026-05-01-auth/handoff.json",
                    "date": "2026-05-01",
                    "slug": "auth",
                    "verdict": "proceed",
                    "mode": "bug",
                    "matched_via": "ticket_text_substring",
                    "content_excerpt": "verdict=proceed",
                }
            ],
        })
        result = _section_bundle(state)
        self.assertIn("auth", result)
        self.assertIn("proceed", result)
        self.assertIn("2026-05-01", result)

    def test_research_handoffs_empty_placeholder(self):
        state = _make_state(bundle={
            "constitution_md_content": "",
            "constitute_json": None,
            "concern_docs": [],
            "adrs": [],
            "plan_files": [],
            "research_handoffs": [],
        })
        result = _section_bundle(state)
        self.assertIn("_None._", result)

    def test_empty_bundle_dict_does_not_raise(self):
        state = _make_state(bundle={})
        try:
            _section_bundle(state)
        except Exception as exc:
            self.fail("_section_bundle raised with empty bundle: {0}".format(exc))

    def test_constitution_truncated_at_cap(self):
        long_content = "C" * 40000
        state = _make_state(bundle={
            "constitution_md_content": long_content,
            "constitute_json": None,
            "concern_docs": [],
            "adrs": [],
            "plan_files": [],
            "research_handoffs": [],
        })
        result = _section_bundle(state, caps={"constitution": 30000})
        self.assertIn("[truncated]", result)


# ---------------------------------------------------------------------------
# TestSectionInstructions
# ---------------------------------------------------------------------------


class TestSectionInstructions(unittest.TestCase):
    def test_header_present(self):
        result = _section_instructions(0)
        self.assertIn("## Reviewer instructions", result)

    def test_brief_size_embedded(self):
        result = _section_instructions(12345)
        self.assertIn("12345", result)

    def test_cavecrew_reviewer_mentioned(self):
        result = _section_instructions(0)
        self.assertIn("cavecrew-reviewer", result)

    def test_findings_format_block_present(self):
        result = _section_instructions(0)
        self.assertIn("severity", result)
        self.assertIn("location", result)
        self.assertIn("evidence", result)
        self.assertIn("fix_hint", result)
        self.assertIn("source_heuristic", result)

    def test_verbatim_copy_instruction_present(self):
        result = _section_instructions(0)
        self.assertIn("VERBATIM", result)

    def test_state_findings_mentioned(self):
        result = _section_instructions(0)
        self.assertIn("state.findings", result)


# ---------------------------------------------------------------------------
# TestRunHappyPath
# ---------------------------------------------------------------------------


class TestRunHappyPath(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._devforge = os.path.join(self._tmp, ".devforge")
        self._pr_number = 42
        state = _make_full_state(self._devforge, self._pr_number)
        _write_state_to_disk(state, self._devforge)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_returns_status_ok(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        self.assertEqual(result["status"], "ok")

    def test_state_path_key_present(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        self.assertIn("state_path", result)
        self.assertTrue(os.path.isabs(result["state_path"]))

    def test_brief_path_key_present(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        self.assertIn("brief_path", result)
        self.assertTrue(os.path.isabs(result["brief_path"]))

    def test_brief_file_written(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        self.assertTrue(
            os.path.isfile(result["brief_path"]),
            "brief.md file not found at {0}".format(result["brief_path"]),
        )

    def test_brief_file_nonempty(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        with open(result["brief_path"], "r", encoding="utf-8") as fh:
            content = fh.read()
        self.assertGreater(len(content), 500)

    def test_brief_size_chars_matches_file(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        with open(result["brief_path"], "r", encoding="utf-8") as fh:
            content = fh.read()
        self.assertEqual(result["brief_size_chars"], len(content))

    def test_sections_included_key(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        expected = {
            "metadata", "ticket_text", "linked_issues", "diff",
            "smells", "blast", "drift", "bundle", "instructions", "notes",
        }
        self.assertEqual(set(result["sections_included"]), expected)

    def test_smells_count(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        self.assertEqual(result["smells_count"], 1)

    def test_blast_probes_count(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        self.assertEqual(result["blast_probes_count"], 1)

    def test_drift_bullets_count(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        self.assertEqual(result["drift_bullets_count"], 1)

    def test_bundle_sources_count_keys(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        bsc = result["bundle_sources_count"]
        self.assertIn("constitution_md", bsc)
        self.assertIn("constitute_json", bsc)
        self.assertIn("concern_docs", bsc)
        self.assertIn("adrs", bsc)
        self.assertIn("plan_files", bsc)
        self.assertIn("research_handoffs", bsc)

    def test_bundle_sources_count_values(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        bsc = result["bundle_sources_count"]
        self.assertTrue(bsc["constitution_md"])
        self.assertTrue(bsc["constitute_json"])
        self.assertEqual(bsc["concern_docs"], 1)
        self.assertEqual(bsc["adrs"], 1)
        self.assertEqual(bsc["plan_files"], 1)
        self.assertEqual(bsc["research_handoffs"], 1)

    def test_next_action_key(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        self.assertIn("next_action", result)
        self.assertIn("cavecrew-reviewer", result["next_action"])

    def test_brief_path_under_pr_dir(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        expected_dir = os.path.join(
            self._tmp, ".devforge", "pr-reviews", str(self._pr_number)
        )
        self.assertTrue(result["brief_path"].startswith(expected_dir))

    def test_brief_filename_is_brief_md(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        self.assertEqual(os.path.basename(result["brief_path"]), "brief.md")

    def test_brief_contains_pr_number(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        with open(result["brief_path"], "r", encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("PR #42", content)

    def test_brief_contains_all_sections(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        with open(result["brief_path"], "r", encoding="utf-8") as fh:
            content = fh.read()
        for section_header in [
            "## Metadata",
            "## Ticket text",
            "## Linked issues",
            "## Diff",
            "## Code-smell findings",
            "## Blast-radius probe specs",
            "## Scope-drift bullets",
            "## Context bundle",
            "## Reviewer instructions",
        ]:
            self.assertIn(section_header, content, "section missing: {0!r}".format(section_header))

    def test_idempotent_second_run_overwrites(self):
        """Second invocation regenerates brief.md — no error, same sections."""
        run(target=self._tmp, pr_number=self._pr_number)
        result2 = run(target=self._tmp, pr_number=self._pr_number)
        self.assertEqual(result2["status"], "ok")
        self.assertTrue(os.path.isfile(result2["brief_path"]))


# ---------------------------------------------------------------------------
# TestRunMinimalState
# ---------------------------------------------------------------------------


class TestRunMinimalState(unittest.TestCase):
    """State with only intake fields (no smells / blast / drift / bundle)."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._devforge = os.path.join(self._tmp, ".devforge")
        self._pr_number = 7
        state = PRReviewState(
            pr_number=self._pr_number,
            repo="acme/minimal",
        )
        _write_state_to_disk(state, self._devforge)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_run_exits_ok(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        self.assertEqual(result["status"], "ok")

    def test_brief_written(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        self.assertTrue(os.path.isfile(result["brief_path"]))

    def test_placeholders_present_for_empty_sections(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        with open(result["brief_path"], "r", encoding="utf-8") as fh:
            content = fh.read()
        self.assertIn("_No smells detected._", content)
        self.assertIn("_No blast-radius probe specs extracted._", content)
        self.assertIn("_No scope-drift bullets extracted._", content)
        self.assertIn("_No diff available._", content)
        self.assertIn("_No ticket text provided._", content)

    def test_smells_count_zero(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        self.assertEqual(result["smells_count"], 0)

    def test_blast_probes_count_zero(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        self.assertEqual(result["blast_probes_count"], 0)

    def test_drift_bullets_count_zero(self):
        result = run(target=self._tmp, pr_number=self._pr_number)
        self.assertEqual(result["drift_bullets_count"], 0)


# ---------------------------------------------------------------------------
# TestRunNoStateFile
# ---------------------------------------------------------------------------


class TestRunNoStateFile(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_missing_state_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            run(target=self._tmp, pr_number=9999)
        self.assertIn("intake", str(ctx.exception))

    def test_error_message_contains_state_path(self):
        with self.assertRaises(ValueError) as ctx:
            run(target=self._tmp, pr_number=9999)
        self.assertIn("state.json", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestBriefSizeCap
# ---------------------------------------------------------------------------


class TestBriefSizeCap(unittest.TestCase):
    """Verify that section content is capped so the brief stays manageable."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._devforge = os.path.join(self._tmp, ".devforge")
        self._pr_number = 100

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_large_diff_is_capped(self):
        state = PRReviewState(
            pr_number=self._pr_number,
            repo="acme/app",
            diff="A" * 200000,  # 200K — well over _DIFF_CAP
        )
        _write_state_to_disk(state, self._devforge)
        result = run(target=self._tmp, pr_number=self._pr_number)
        with open(result["brief_path"], "r", encoding="utf-8") as fh:
            content = fh.read()
        # Brief must contain mid-diff truncation marker.
        self.assertIn("... [truncated mid-diff] ...", content)
        # Total size should not exceed _DIFF_CAP * 2 greatly.
        # (sections other than diff are small here)
        self.assertLess(result["brief_size_chars"], 200000)

    def test_large_constitution_is_capped(self):
        state = PRReviewState(
            pr_number=self._pr_number,
            repo="acme/app",
            bundle={
                "constitution_md": "/tmp/constitution.md",
                "constitution_md_content": "C" * 60000,
                "constitute_json": None,
                "concern_docs": [],
                "adrs": [],
                "plan_files": [],
                "research_handoffs": [],
            },
        )
        _write_state_to_disk(state, self._devforge)
        result = run(target=self._tmp, pr_number=self._pr_number)
        with open(result["brief_path"], "r", encoding="utf-8") as fh:
            content = fh.read()
        # Brief must contain truncation marker for constitution.
        self.assertIn("[truncated]", content)


if __name__ == "__main__":
    unittest.main()
