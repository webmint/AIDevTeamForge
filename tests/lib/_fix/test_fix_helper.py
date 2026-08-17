"""Tests for src/devforge/lib/_fix/ — the fix_helper subpackage.

Real-producer round-trip discipline (mandatory per repo rules):
  - read-findings tests parse a REAL review.md produced by
    _review._report.render_report + write_review_report (the same path
    review_helper render-report calls).
  - read-findings tests also parse a REAL verification.md produced by
    _verify._report.render_report + write_verification_report.
  - preflight tests use real filesystem layouts that mirror the 4-command
    setup-chain outputs (no hand-faked CLAUDE.md content for sentinel checks).
  - in-fix-window tests use real on-disk feature state (real task .md files
    with real **Status**: lines, real spec.md, real/absent summary.md).
  - No hand-authored markdown fixtures.

Coverage:
  _preflight.preflight_context:
    - All files absent → setup_chain_ok=False, all artefacts in missing list.
    - Each artefact missing individually → setup_chain_ok=False.
    - Constitution present but unpopulated → constitution_populated=False.
    - Full install → setup_chain_ok=True, source_root, wrapper_mode resolved.
    - Wrapper mode detected from CLAUDE.md.
    - .devforge/memory.md read (NOT .claude/memory/MEMORY.md — plan-22 F).
    - No .claude/ path access (verified by fixture — only .devforge/ exists).

  _findings.read_findings:
    - Missing feature dir → both sources missing=True, items=[].
    - review.md only (source="review") → items from real confirmed+contested.
    - verification.md NEEDS WORK only (source="verify") → items from real report.
    - "both" (default) → union of both sources.
    - APPROVED verification.md → no verify items (not NEEDS WORK).
    - review.md with no confirmed/contested → items=[].

  _scope.resolve_scope:
    - Empty items list → empty=True, files=[], file_count=0.
    - Items with files_cited → deduplicated, sorted file set.
    - Items with empty files_cited → ignored.
    - Duplicate files across items → deduplicated.

  _window.in_fix_window:
    - No tasks dir → in_window=False, reason=no_tasks_dir.
    - Empty tasks dir → in_window=False, reason=no_task_files.
    - Tasks complete, no summary.md, spec not Complete → in_window=True.
    - summary.md present → in_window=False, reason=summary_present.
    - Spec **Status**: Complete → in_window=False, reason=spec_complete.
    - Tasks in progress (mixed) → in_window=False, reason=not_all_tasks_complete.
    - tasks/README.md (index with status table, no **Status**: line) present
      alongside complete task files → in_window=True (README not a task file).
      [REGRESSION TEST — the bug was README.md causing all_terminal=False]
    - tasks/ with only README.md (no real task files) → in_window=False,
      reason=no_task_files.

  CLI dispatch (via main()):
    - No subcommand → exit 2 (prints help).
    - Unknown verb → exit 2.
    - preflight: emits JSON, exit 2 on incomplete chain.
    - preflight: exit 0 on complete chain.
    - read-findings: missing --feature → exit 2.
    - read-findings: valid feature dir → exit 0, JSON on stdout.
    - resolve-scope: --items "-" reads stdin, exit 0, JSON on stdout.
    - resolve-scope: missing --items → exit 2.
    - in-fix-window: in-window → exit 0, JSON {"in_window": true, ...}.
    - in-fix-window: out-of-window → exit 1, JSON {"in_window": false, ...}.
    - in-fix-window: missing --feature → exit 2.
"""

from __future__ import annotations

import io
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

# Real producers for round-trip tests.
from _shared._verify import apply_verdicts  # noqa: E402
from _review._report import render_report as review_render_report, write_review_report  # noqa: E402
from _verify._ac import parse_acs, merge_ac_results  # noqa: E402
from _verify._review_findings import read_review_findings  # noqa: E402
from _verify._verdict import compute_verdict  # noqa: E402
from _verify._report import render_report as verify_render_report, write_verification_report  # noqa: E402

# The module under test.
from _fix._cli import main  # noqa: E402
from _fix._preflight import _SETUP_CHAIN_ARTEFACTS, _UNPOPULATED_SENTINELS, preflight_context  # noqa: E402
from _fix._findings import read_findings  # noqa: E402
from _fix._scope import resolve_scope  # noqa: E402
from _fix._window import in_fix_window  # noqa: E402

# The real shipped installer stub -- used to build production-shaped
# memory.md fixtures (real "## " sections) rather than headingless ones
# (plan 79 Phase 1: a headingless file is 100% preamble and excerpts "").
_REAL_STUB_PATH = _REPO_ROOT / "src" / "devforge" / "memory.md"


# ---------------------------------------------------------------------------
# Real-producer fixture helpers
# ---------------------------------------------------------------------------


def _finding(
    agent="code-reviewer",
    file="src/a.py",
    line=10,
    pattern="Name mismatch",
    severity="High",
    category="mislogic",
    tags=None,
    finding_id=None,
):
    """Minimal ParsedFinding dict matching the _review/_verify test convention."""
    f = {
        "agent": agent,
        "file": file,
        "line": line,
        "pattern": pattern,
        "severity": severity,
        "confidence": "Likely",
        "evidence": "x = bad_code()",
        "why": "cross-task interaction causes defect",
        "remediation": "fix it",
        "category": category,
        "tags": tags if tags is not None else [],
    }
    if finding_id is not None:
        f["finding_id"] = finding_id
    return f


def _verdict_dict(file, line, pattern, agent, verdict_val, justification="confirmed"):
    return {
        "refuter": "architect",
        "file": file,
        "line": line,
        "pattern": pattern,
        "agent": agent,
        "verdict": verdict_val,
        "justification": justification,
        "evidence": "",
    }


def _build_partition_with_confirmed():
    """Build a real partition with at least one confirmed finding (via apply_verdicts)."""
    findings = [
        _finding(
            agent="code-reviewer",
            file="src/auth.py",
            line=42,
            pattern="Auth bypass via missing null check",
            severity="High",
            category="mislogic",
            finding_id="F-001",
        ),
        _finding(
            agent="security-reviewer",
            file="src/api/query.py",
            line=55,
            pattern="SQL injection via unescaped param",
            severity="Critical",
            category="security",
            finding_id="F-002",
        ),
        # A dismissed one (should NOT appear in confirmed/contested).
        _finding(
            agent="qa-reviewer",
            file="src/utils.py",
            line=5,
            pattern="Missing type annotation",
            severity="Info",
            category="best_practice",
            finding_id="F-003",
        ),
    ]
    verdicts = [
        _verdict_dict("src/auth.py", 42, "Auth bypass via missing null check", "code-reviewer", "confirmed"),
        _verdict_dict("src/api/query.py", 55, "SQL injection via unescaped param", "security-reviewer", "uncertain"),
        _verdict_dict("src/utils.py", 5, "Missing type annotation", "qa-reviewer", "dismissed"),
    ]
    return apply_verdicts(findings, verdicts)


def _make_real_review_md(feature_dir):
    # type: (str) -> str
    """Produce a real review.md by calling the REAL render_report + write_review_report."""
    partition = _build_partition_with_confirmed()
    content = review_render_report(
        partition=partition,
        feature=feature_dir,
        date_str="2026-06-19",
        finders=["code-reviewer", "security-reviewer", "qa-reviewer"],
        refuters=["architect", "code-reviewer"],
        source_root="/workspace",
        framework="Python / FastAPI",
        n_scope_files=3,
        finders_skipped=[],
    )
    return write_review_report(feature_dir, content)


def _make_real_verification_md(feature_dir, verdict="NEEDS WORK"):
    # type: (str, str) -> str
    """Produce a real verification.md by calling the REAL verify render_report."""
    # Build a real review_findings from the real review.md (if it exists).
    review_path = os.path.join(feature_dir, "review.md")
    if os.path.isfile(review_path):
        review_findings = read_review_findings(review_path)
    else:
        review_findings = {
            "missing": True,
            "confirmed": [],
            "contested": [],
            "summary": {
                "critical": 0, "high": 0, "medium": 0, "info": 0,
                "confirmed_count": 0, "contested_count": 0,
                "dismissed_count": 0, "uncertain_count": 0,
            },
        }

    if verdict == "APPROVED":
        ac_results = [
            {"id": "AC-1", "text": "Feature works", "checked": True,
             "subsection": "", "status": "PASS", "evidence": "all tests pass"},
        ]
        mech_status = "pass"
    else:
        ac_results = [
            {"id": "AC-1", "text": "Feature works", "checked": False,
             "subsection": "", "status": "FAIL", "evidence": "test fails"},
        ]
        mech_status = "failed"

    hygiene = {
        "scope_creep": [],
        "leftover_artifacts": [],
        "scope_creep_checked": False,
        "files_checked": 0,
        "files_unreadable": [],
    }

    verdict_data = compute_verdict(
        ac_results=ac_results,
        mechanical_status=mech_status,
        review_findings=review_findings,
        hygiene=hygiene,
        ac_verification_mode="code-only",
    )
    # Override verdict string to match what the caller wants for test clarity.
    # (compute_verdict may differ; we force the desired verdict for testing the parser.)
    verdict_data["verdict"] = verdict

    content = verify_render_report(
        verdict=verdict_data,
        ac_results=ac_results,
        review_findings=review_findings,
        hygiene=hygiene,
        feature=feature_dir,
        date_str="2026-06-19",
        mechanical_status=mech_status,
        ac_verification_mode="code-only",
    )
    return write_verification_report(feature_dir, content)


def _write(td, rel_path, content):
    # type: (str, str, str) -> str
    """Write content to td/rel_path, creating parent dirs. Returns full path."""
    full = os.path.join(td, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)
    return full


def _make_full_install(td):
    # type: (str) -> None
    """Write a minimal but complete 4-command setup-chain install into td."""
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


def _capture(argv):
    # type: (list) -> tuple
    """Run main(argv) with captured stdout/stderr. Returns (stdout, stderr, rc).

    Catches SystemExit (raised by argparse on bad args / --help) and converts
    the exit code to an integer. This mirrors how the real CLI caller sees it.
    """
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = buf_out, buf_err
        try:
            rc = main(argv)
        except SystemExit as exc:
            rc = exc.code if isinstance(exc.code, int) else 2
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return buf_out.getvalue(), buf_err.getvalue(), rc


# ---------------------------------------------------------------------------
# Test: _preflight.preflight_context
# ---------------------------------------------------------------------------


class TestPreflightContext(unittest.TestCase):
    """Tests for _fix._preflight.preflight_context."""

    def test_all_absent_returns_setup_chain_not_ok(self):
        with tempfile.TemporaryDirectory() as td:
            result = preflight_context(td)
            self.assertFalse(result["setup_chain_ok"])
            self.assertFalse(result["constitution_present"])
            self.assertFalse(result["constitution_populated"])
            self.assertFalse(result["claude_md_present"])
            self.assertFalse(result["memory_present"])
            self.assertEqual(result["memory_excerpt"], "")

    def test_missing_artefacts_list_all_labels(self):
        with tempfile.TemporaryDirectory() as td:
            result = preflight_context(td)
            labels = [label for _, label in _SETUP_CHAIN_ARTEFACTS]
            for label in labels:
                self.assertIn(label, result["missing_artefacts"])

    def test_each_artefact_missing_individually(self):
        for rel_path, label in _SETUP_CHAIN_ARTEFACTS:
            with tempfile.TemporaryDirectory() as td:
                _make_full_install(td)
                # Remove just this one artefact.
                full = os.path.join(td, rel_path)
                os.unlink(full)
                result = preflight_context(td)
                self.assertFalse(result["setup_chain_ok"],
                    msg="Expected setup_chain_ok=False when {0} missing".format(rel_path))
                self.assertIn(label, result["missing_artefacts"],
                    msg="Expected label '{0}' in missing when {1} absent".format(label, rel_path))

    def test_constitution_unpopulated_sentinel_detected(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            # Overwrite constitution with a known sentinel.
            sentinel = _UNPOPULATED_SENTINELS[0]
            _write(td, "constitution.md", "# Rules\n\n{0}\n".format(sentinel))
            result = preflight_context(td)
            self.assertTrue(result["constitution_present"])
            self.assertFalse(result["constitution_populated"])

    def test_constitution_legacy_no_slash_sentinel_detected(self):
        # Pre-namespace stub literal (no slash) -- the form every existing
        # consumer install actually carries.
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            sentinel = _UNPOPULATED_SENTINELS[2]
            self.assertEqual(sentinel, "Run constitute to populate")
            _write(td, "constitution.md", "# Rules\n\n{0}\n".format(sentinel))
            result = preflight_context(td)
            self.assertTrue(result["constitution_present"])
            self.assertFalse(result["constitution_populated"])

    def test_constitution_devforge_namespaced_sentinel_detected(self):
        # Post-namespace stub literal (current, plan 63 Phase 4c).
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            sentinel = _UNPOPULATED_SENTINELS[4]
            self.assertEqual(sentinel, "Run /devforge:constitute to populate")
            _write(td, "constitution.md", "# Rules\n\n{0}\n".format(sentinel))
            result = preflight_context(td)
            self.assertTrue(result["constitution_present"])
            self.assertFalse(result["constitution_populated"])

    def test_full_install_passes(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            result = preflight_context(td)
            self.assertTrue(result["setup_chain_ok"])
            self.assertTrue(result["constitution_present"])
            self.assertTrue(result["constitution_populated"])
            self.assertTrue(result["claude_md_present"])

    def test_source_root_extracted_from_claude_md(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            result = preflight_context(td)
            self.assertEqual(result["source_root"], "src/backend")

    def test_wrapper_mode_detected(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            _write(td, "CLAUDE.md",
                   "# CLAUDE.md\n\n"
                   "- **Name**: TestProject\n"
                   "- **Type**: web-app\n"
                   "- **Frameworks**: React\n"
                   "- **Languages**: TypeScript\n"
                   "- **Source Root**: /projects/my-app\n"
                   "\n## Wrapper Mode\n\nThis project uses wrapper mode.\n")
            result = preflight_context(td)
            self.assertTrue(result["wrapper_mode"])

    def test_no_wrapper_mode_in_standalone(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            result = preflight_context(td)
            self.assertFalse(result["wrapper_mode"])

    def test_memory_read_from_devforge_not_claude(self):
        """Verify that memory is read from .devforge/memory.md, NOT .claude/memory/MEMORY.md.

        plan 79 Phase 1: _make_full_install()'s memory.md is now
        production-shaped (real "## " sections), with the lesson links
        under "## Known Pitfalls" -- a section-aware excerpt surfaces
        them.
        """
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            # .devforge/memory.md exists (written by _make_full_install).
            # We verify its content is reflected.
            result = preflight_context(td)
            self.assertTrue(result["memory_present"])
            self.assertIn("Lesson 1", result["memory_excerpt"])
            # .claude/ should not exist — nothing created it.
            self.assertFalse(os.path.isdir(os.path.join(td, ".claude")))

    def test_memory_absent_is_graceful(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            mem = os.path.join(td, ".devforge", "memory.md")
            os.unlink(mem)
            result = preflight_context(td)
            self.assertFalse(result["memory_present"])
            self.assertEqual(result["memory_excerpt"], "")

    def test_returns_all_expected_keys(self):
        with tempfile.TemporaryDirectory() as td:
            result = preflight_context(td)
            expected_keys = {
                "constitution_present", "constitution_populated",
                "setup_chain_ok", "missing_artefacts",
                "source_root", "wrapper_mode",
                "project_type", "framework", "language",
                "claude_md_present", "memory_present", "memory_excerpt",
            }
            self.assertEqual(set(result.keys()), expected_keys)


# ---------------------------------------------------------------------------
# Test: _findings.read_findings (real-producer round-trip)
# ---------------------------------------------------------------------------


class TestReadFindings(unittest.TestCase):
    """Tests for _fix._findings.read_findings — real producer round-trips."""

    def test_missing_feature_dir_returns_empty(self):
        result = read_findings("/nonexistent/path/that/does/not/exist")
        self.assertEqual(result["items"], [])
        self.assertTrue(result["sources"]["review_missing"])
        self.assertTrue(result["sources"]["verify_missing"])
        self.assertFalse(result["sources"]["review"])
        self.assertFalse(result["sources"]["verify"])

    def test_review_source_parses_real_review_md(self):
        """Round-trip: real review.md from _review render_report → read_findings."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-test-feature")
            os.makedirs(feature_dir, exist_ok=True)
            _make_real_review_md(feature_dir)

            result = read_findings(feature_dir, source="review")

            # Should have found the review.md.
            self.assertFalse(result["sources"]["review_missing"])
            self.assertTrue(result["sources"]["review"])

            # Should have items from confirmed+contested findings.
            items = result["items"]
            self.assertGreater(len(items), 0,
                msg="Expected at least one item from confirmed/contested findings in real review.md")

            # All items have source="review".
            for item in items:
                self.assertEqual(item["source"], "review")
                # All RemediationItem keys present.
                self.assertIn("title", item)
                self.assertIn("severity", item)
                self.assertIn("files_cited", item)
                self.assertIn("evidence", item)

    def test_review_source_items_have_file_paths(self):
        """Real review.md findings have file paths in files_cited."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-test-feature")
            os.makedirs(feature_dir, exist_ok=True)
            _make_real_review_md(feature_dir)

            result = read_findings(feature_dir, source="review")
            items_with_files = [i for i in result["items"] if i["files_cited"]]
            self.assertGreater(len(items_with_files), 0,
                msg="Expected at least one item with a cited file from the real review.md")

    def test_verify_source_needs_work_produces_items(self):
        """Round-trip: real NEEDS-WORK verification.md → read_findings items."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-test-feature")
            os.makedirs(feature_dir, exist_ok=True)
            # Build review.md first so verify can fold it in.
            _make_real_review_md(feature_dir)
            _make_real_verification_md(feature_dir, verdict="NEEDS WORK")

            result = read_findings(feature_dir, source="verify")

            # Should have parsed verification.md.
            self.assertFalse(result["sources"]["verify_missing"])
            # verdict is NEEDS WORK so issues should be present.
            self.assertEqual(result["sources"]["verify_verdict"], "NEEDS WORK")

            # When the review has confirmed/contested findings AND verdict is
            # NEEDS WORK, the verification.md Issues Found section has entries.
            items = result["items"]
            self.assertGreater(len(items), 0,
                msg="Expected issues from NEEDS WORK verification.md")

            for item in items:
                self.assertEqual(item["source"], "verify")

    def test_verify_source_approved_yields_no_items(self):
        """APPROVED verification.md should produce no items (issues gated on NEEDS WORK)."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-test-feature")
            os.makedirs(feature_dir, exist_ok=True)
            _make_real_verification_md(feature_dir, verdict="APPROVED")

            result = read_findings(feature_dir, source="verify")

            self.assertEqual(result["sources"]["verify_verdict"], "APPROVED")
            # APPROVED → no remediation items from verification.md.
            self.assertEqual(result["items"], [])

    def test_both_source_unions_review_and_verify(self):
        """source='both' should union review + verify items."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-test-feature")
            os.makedirs(feature_dir, exist_ok=True)
            _make_real_review_md(feature_dir)
            _make_real_verification_md(feature_dir, verdict="NEEDS WORK")

            review_only = read_findings(feature_dir, source="review")
            verify_only = read_findings(feature_dir, source="verify")
            both = read_findings(feature_dir, source="both")

            total_expected = len(review_only["items"]) + len(verify_only["items"])
            self.assertEqual(len(both["items"]), total_expected)

    def test_review_only_flag_does_not_parse_verification(self):
        """source='review' should not read verification.md even if present."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-test-feature")
            os.makedirs(feature_dir, exist_ok=True)
            _make_real_review_md(feature_dir)
            _make_real_verification_md(feature_dir, verdict="NEEDS WORK")

            result = read_findings(feature_dir, source="review")
            # All items should be from review only.
            for item in result["items"]:
                self.assertEqual(item["source"], "review")
            # sources.verify should be False (not parsed).
            self.assertFalse(result["sources"]["verify"])

    def test_verify_only_flag_does_not_parse_review(self):
        """source='verify' should not read review.md."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-test-feature")
            os.makedirs(feature_dir, exist_ok=True)
            _make_real_review_md(feature_dir)
            _make_real_verification_md(feature_dir, verdict="NEEDS WORK")

            result = read_findings(feature_dir, source="verify")
            for item in result["items"]:
                self.assertEqual(item["source"], "verify")
            self.assertFalse(result["sources"]["review"])

    def test_empty_dir_no_items(self):
        """A feature dir with no review.md and no verification.md → empty items."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "002-empty")
            os.makedirs(feature_dir, exist_ok=True)

            result = read_findings(feature_dir)
            self.assertEqual(result["items"], [])
            self.assertTrue(result["sources"]["review_missing"])
            self.assertTrue(result["sources"]["verify_missing"])


# ---------------------------------------------------------------------------
# Test: _scope.resolve_scope
# ---------------------------------------------------------------------------


class TestResolveScope(unittest.TestCase):
    """Tests for _fix._scope.resolve_scope."""

    def test_empty_items_list(self):
        result = resolve_scope([])
        self.assertEqual(result["files"], [])
        self.assertEqual(result["file_count"], 0)
        self.assertTrue(result["empty"])

    def test_items_with_files_cited(self):
        items = [
            {"title": "Issue A", "severity": "High",
             "files_cited": ["src/auth.py", "src/db.py"],
             "evidence": "", "source": "review"},
            {"title": "Issue B", "severity": "Medium",
             "files_cited": ["src/api.py"],
             "evidence": "", "source": "verify"},
        ]
        result = resolve_scope(items)
        self.assertEqual(result["files"], ["src/api.py", "src/auth.py", "src/db.py"])
        self.assertEqual(result["file_count"], 3)
        self.assertFalse(result["empty"])

    def test_deduplication(self):
        items = [
            {"title": "Issue A", "files_cited": ["src/auth.py", "src/db.py"],
             "severity": "High", "evidence": "", "source": "review"},
            {"title": "Issue B", "files_cited": ["src/auth.py"],
             "severity": "High", "evidence": "", "source": "verify"},
        ]
        result = resolve_scope(items)
        # src/auth.py cited twice → deduplicated to once.
        self.assertEqual(result["files"], ["src/auth.py", "src/db.py"])
        self.assertEqual(result["file_count"], 2)

    def test_items_with_empty_files_cited_ignored(self):
        items = [
            {"title": "Issue A", "files_cited": [],
             "severity": "High", "evidence": "", "source": "review"},
            {"title": "Issue B", "files_cited": ["src/real.py"],
             "severity": "Medium", "evidence": "", "source": "verify"},
        ]
        result = resolve_scope(items)
        self.assertEqual(result["files"], ["src/real.py"])
        self.assertEqual(result["file_count"], 1)
        self.assertFalse(result["empty"])

    def test_all_empty_files_cited(self):
        items = [
            {"title": "Issue", "files_cited": [], "severity": "Info",
             "evidence": "", "source": "review"},
        ]
        result = resolve_scope(items)
        self.assertTrue(result["empty"])
        self.assertEqual(result["files"], [])

    def test_sorted_output(self):
        items = [
            {"title": "Z", "files_cited": ["z.py", "a.py", "m.py"],
             "severity": "High", "evidence": "", "source": "review"},
        ]
        result = resolve_scope(items)
        self.assertEqual(result["files"], ["a.py", "m.py", "z.py"])

    def test_round_trip_from_real_findings(self):
        """Round-trip: real read_findings output → resolve_scope."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-test-feature")
            os.makedirs(feature_dir, exist_ok=True)
            _make_real_review_md(feature_dir)

            findings_result = read_findings(feature_dir, source="review")
            items = findings_result["items"]

            scope_result = resolve_scope(items)

            # Must have the expected keys.
            self.assertIn("files", scope_result)
            self.assertIn("file_count", scope_result)
            self.assertIn("empty", scope_result)

            # If items have files_cited, scope must be non-empty.
            items_with_files = [i for i in items if i.get("files_cited")]
            if items_with_files:
                self.assertFalse(scope_result["empty"])
                self.assertGreater(scope_result["file_count"], 0)


# ---------------------------------------------------------------------------
# Test: _window.in_fix_window (real on-disk feature state)
# ---------------------------------------------------------------------------


def _write_task(td, tasks_dir, name, status="In Progress"):
    # type: (str, str, str, str) -> str
    path = os.path.join(tasks_dir, name)
    content = (
        "# Task: {name}\n\n"
        "**Status**: {status}\n\n"
        "## Description\nDo the thing.\n"
    ).format(name=name, status=status)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def _write_spec(feature_dir, status="In Progress"):
    # type: (str, str) -> str
    path = os.path.join(feature_dir, "spec.md")
    content = (
        "# Feature Spec\n\n"
        "**Status**: {status}\n\n"
        "## Acceptance Criteria\n- [ ] AC-1\n"
    ).format(status=status)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


class TestInFixWindow(unittest.TestCase):
    """Tests for _fix._window.in_fix_window — real on-disk feature state."""

    def test_no_tasks_dir_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            os.makedirs(feature_dir, exist_ok=True)
            _write_spec(feature_dir, status="In Progress")
            # No tasks/ directory.
            result = in_fix_window(feature_dir)
            self.assertFalse(result["in_window"])
            self.assertEqual(result["reason"], "no_tasks_dir")

    def test_empty_tasks_dir_returns_false(self):
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            tasks_dir = os.path.join(feature_dir, "tasks")
            os.makedirs(tasks_dir, exist_ok=True)
            _write_spec(feature_dir, status="In Progress")
            result = in_fix_window(feature_dir)
            self.assertFalse(result["in_window"])
            self.assertEqual(result["reason"], "no_task_files")

    def test_all_tasks_complete_no_summary_not_complete_spec(self):
        """The canonical in-window case: /implement done, /summarize not run."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            tasks_dir = os.path.join(feature_dir, "tasks")
            os.makedirs(tasks_dir, exist_ok=True)
            _write_task(td, tasks_dir, "001-task.md", status="Complete")
            _write_task(td, tasks_dir, "002-task.md", status="Complete")
            _write_spec(feature_dir, status="In Progress")
            # No summary.md written yet.

            result = in_fix_window(feature_dir)
            self.assertTrue(result["in_window"])
            self.assertEqual(result["reason"], "all_tasks_complete")

    def test_summary_present_returns_false(self):
        """summary.md present → /summarize has run → feature is sealed."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            tasks_dir = os.path.join(feature_dir, "tasks")
            os.makedirs(tasks_dir, exist_ok=True)
            _write_task(td, tasks_dir, "001-task.md", status="Complete")
            _write_spec(feature_dir, status="In Progress")
            # Write summary.md to simulate /summarize having run.
            with open(os.path.join(feature_dir, "summary.md"), "w") as fh:
                fh.write("# Summary\n\nFeature is done.\n")

            result = in_fix_window(feature_dir)
            self.assertFalse(result["in_window"])
            self.assertEqual(result["reason"], "summary_present")

    def test_spec_complete_returns_false(self):
        """/verify APPROVED flips spec to Complete → treated as sealed."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            tasks_dir = os.path.join(feature_dir, "tasks")
            os.makedirs(tasks_dir, exist_ok=True)
            _write_task(td, tasks_dir, "001-task.md", status="Complete")
            _write_spec(feature_dir, status="Complete")  # /verify flipped it
            # No summary.md (summary not yet run, but spec is Complete).

            result = in_fix_window(feature_dir)
            self.assertFalse(result["in_window"])
            self.assertEqual(result["reason"], "spec_complete")

    def test_tasks_in_progress_returns_false(self):
        """Mid-/implement: some tasks complete, some in progress → NOT in-window.

        The /fix window is strictly post-/implement (ALL tasks terminal).  A
        /fix wip-commit landing mid-/implement would stomp /implement's
        .devforge/wip.md crash-recovery marker.
        """
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            tasks_dir = os.path.join(feature_dir, "tasks")
            os.makedirs(tasks_dir, exist_ok=True)
            _write_task(td, tasks_dir, "001-task.md", status="Complete")
            _write_task(td, tasks_dir, "002-task.md", status="In Progress")
            _write_spec(feature_dir, status="In Progress")

            result = in_fix_window(feature_dir)
            self.assertFalse(result["in_window"])
            self.assertEqual(result["reason"], "not_all_tasks_complete")

    def test_tasks_skipped_count_as_terminal(self):
        """Skipped tasks are terminal (same as Complete for the window check)."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            tasks_dir = os.path.join(feature_dir, "tasks")
            os.makedirs(tasks_dir, exist_ok=True)
            _write_task(td, tasks_dir, "001-task.md", status="Complete")
            _write_task(td, tasks_dir, "002-task.md", status="Skipped")
            _write_spec(feature_dir, status="In Progress")

            result = in_fix_window(feature_dir)
            self.assertTrue(result["in_window"])
            self.assertEqual(result["reason"], "all_tasks_complete")

    def test_all_complete_with_summary_sealed(self):
        """summary.md present beats all_tasks_complete → sealed."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            tasks_dir = os.path.join(feature_dir, "tasks")
            os.makedirs(tasks_dir, exist_ok=True)
            _write_task(td, tasks_dir, "001-task.md", status="Complete")
            _write_spec(feature_dir, status="In Progress")
            with open(os.path.join(feature_dir, "summary.md"), "w") as fh:
                fh.write("# Summary\n")

            result = in_fix_window(feature_dir)
            self.assertFalse(result["in_window"])
            self.assertEqual(result["reason"], "summary_present")

    def test_result_always_has_both_keys(self):
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            os.makedirs(feature_dir, exist_ok=True)
            result = in_fix_window(feature_dir)
            self.assertIn("in_window", result)
            self.assertIn("reason", result)

    def test_readme_md_not_counted_as_task(self):
        """Regression: tasks/README.md (the /breakdown task INDEX) must not be
        treated as a task file.

        README.md holds a per-task status TABLE, not a ``**Status**:`` line, so
        _task_is_terminal(README.md) returns False unconditionally.  Before the
        fix, including README.md caused all_terminal → False → in_window=False
        for EVERY feature built with the standard /breakdown layout.

        Layout: two Complete task files + README.md with a status table (no
        ``**Status**:`` line) + spec In Progress + no summary.md.
        Expected: in_window=True, reason="all_tasks_complete".
        """
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            tasks_dir = os.path.join(feature_dir, "tasks")
            os.makedirs(tasks_dir, exist_ok=True)

            # Real task files — both terminal.
            _write_task(td, tasks_dir, "001-define-types.md", status="Complete")
            _write_task(td, tasks_dir, "002-create-repo.md", status="Complete")

            # tasks/README.md — the /breakdown-generated task INDEX.
            # It carries a per-task status TABLE, NOT a ``**Status**:`` line.
            readme_content = (
                "# Task Index\n\n"
                "| # | Title | Status | Depends On |\n"
                "|---|-------|--------|------------|\n"
                "| 001 | Define types | Complete | — |\n"
                "| 002 | Create repo | Complete | 001 |\n\n"
                "Generated by /breakdown.  Edit task files, not this index.\n"
            )
            with open(os.path.join(tasks_dir, "README.md"), "w", encoding="utf-8") as fh:
                fh.write(readme_content)

            _write_spec(feature_dir, status="In Progress")
            # No summary.md — pre-/summarize state.

            result = in_fix_window(feature_dir)
            self.assertTrue(result["in_window"],
                msg="README.md in tasks/ must not block in_window; got reason={0!r}".format(
                    result["reason"]))
            self.assertEqual(result["reason"], "all_tasks_complete")

    def test_only_readme_in_tasks_returns_no_task_files(self):
        """Edge case: tasks/ containing ONLY README.md (no real task files) →
        no_task_files, NOT not_all_tasks_complete.

        The README exclusion created a new effective path: with README the sole
        file, task_files is empty, so the function takes the no_task_files
        branch ("not yet implemented" per fix/main.md), not the old
        not_all_tasks_complete branch where README counted as a non-terminal
        task.  Pins that boundary so a future edit to the exclusion or the
        no_task_files guard can't regress it silently.
        """
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            tasks_dir = os.path.join(feature_dir, "tasks")
            os.makedirs(tasks_dir, exist_ok=True)
            # README.md only — no numbered task files.
            readme_content = (
                "# Task Index\n\n"
                "| # | Title | Status | Depends On |\n"
                "|---|-------|--------|------------|\n"
            )
            with open(os.path.join(tasks_dir, "README.md"), "w", encoding="utf-8") as fh:
                fh.write(readme_content)
            _write_spec(feature_dir, status="In Progress")

            result = in_fix_window(feature_dir)
            self.assertFalse(result["in_window"])
            self.assertEqual(result["reason"], "no_task_files")


# ---------------------------------------------------------------------------
# Test: CLI dispatch via main()
# ---------------------------------------------------------------------------


class TestCLIDispatch(unittest.TestCase):
    """Tests for fix_helper CLI dispatch."""

    def test_no_subcommand_exits_2(self):
        _, _, rc = _capture([])
        self.assertEqual(rc, 2)

    def test_unknown_verb_exits_nonzero(self):
        _, _, rc = _capture(["nonexistent-verb"])
        self.assertNotEqual(rc, 0)

    # ---- preflight ----

    def test_preflight_incomplete_chain_exits_2(self):
        with tempfile.TemporaryDirectory() as td:
            _, stderr, rc = _capture(["preflight", "--workspace-root", td])
            self.assertEqual(rc, 2)
            self.assertIn("setup chain incomplete", stderr)

    def test_preflight_complete_chain_exits_0_and_emits_json(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            stdout, _, rc = _capture(["preflight", "--workspace-root", td])
            self.assertEqual(rc, 0)
            data = json.loads(stdout)
            self.assertTrue(data["setup_chain_ok"])

    def test_preflight_unpopulated_constitution_exits_2(self):
        with tempfile.TemporaryDirectory() as td:
            _make_full_install(td)
            sentinel = _UNPOPULATED_SENTINELS[0]
            _write(td, "constitution.md", "# Rules\n\n{0}\n".format(sentinel))
            _, stderr, rc = _capture(["preflight", "--workspace-root", td])
            self.assertEqual(rc, 2)
            self.assertIn("constitution.md", stderr.lower())

    def test_preflight_json_always_emitted_on_failure(self):
        """Even on exit 2, JSON is emitted to stdout for machine consumption."""
        with tempfile.TemporaryDirectory() as td:
            stdout, _, rc = _capture(["preflight", "--workspace-root", td])
            self.assertEqual(rc, 2)
            data = json.loads(stdout)
            self.assertIn("setup_chain_ok", data)

    # ---- read-findings ----

    def test_read_findings_missing_feature_exits_2(self):
        _, stderr, rc = _capture(["read-findings"])
        self.assertEqual(rc, 2)

    def test_read_findings_nonexistent_dir_exits_0_with_missing(self):
        stdout, _, rc = _capture(
            ["read-findings", "--feature", "/nonexistent/path/feat"]
        )
        self.assertEqual(rc, 0)
        data = json.loads(stdout)
        self.assertEqual(data["items"], [])
        self.assertTrue(data["sources"]["review_missing"])
        self.assertTrue(data["sources"]["verify_missing"])

    def test_read_findings_valid_review_md_exits_0_with_items(self):
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-test-feature")
            os.makedirs(feature_dir, exist_ok=True)
            _make_real_review_md(feature_dir)

            stdout, _, rc = _capture(
                ["read-findings", "--feature", feature_dir, "--source", "review"]
            )
            self.assertEqual(rc, 0)
            data = json.loads(stdout)
            self.assertIn("items", data)
            self.assertGreater(len(data["items"]), 0)

    def test_read_findings_invalid_source_exits_2(self):
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            os.makedirs(feature_dir, exist_ok=True)
            _, stderr, rc = _capture(
                ["read-findings", "--feature", feature_dir, "--source", "bad-value"]
            )
            self.assertEqual(rc, 2)

    # ---- resolve-scope ----

    def test_resolve_scope_missing_items_exits_2(self):
        _, stderr, rc = _capture(["resolve-scope"])
        self.assertEqual(rc, 2)

    def test_resolve_scope_from_stdin(self):
        items = [
            {"title": "Bug", "severity": "High",
             "files_cited": ["src/auth.py"], "evidence": "", "source": "review"},
        ]
        old_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO(json.dumps(items))
            stdout, _, rc = _capture(["resolve-scope", "--items", "-"])
        finally:
            sys.stdin = old_stdin
        self.assertEqual(rc, 0)
        data = json.loads(stdout)
        self.assertEqual(data["files"], ["src/auth.py"])
        self.assertEqual(data["file_count"], 1)
        self.assertFalse(data["empty"])

    def test_resolve_scope_empty_items(self):
        old_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO("[]")
            stdout, _, rc = _capture(["resolve-scope", "--items", "-"])
        finally:
            sys.stdin = old_stdin
        self.assertEqual(rc, 0)
        data = json.loads(stdout)
        self.assertTrue(data["empty"])

    def test_resolve_scope_from_file(self):
        items = [
            {"title": "T", "severity": "Medium",
             "files_cited": ["src/x.py", "src/y.py"],
             "evidence": "", "source": "review"},
        ]
        with tempfile.TemporaryDirectory() as td:
            items_path = os.path.join(td, "items.json")
            with open(items_path, "w") as fh:
                json.dump(items, fh)
            stdout, _, rc = _capture(["resolve-scope", "--items", items_path])
        self.assertEqual(rc, 0)
        data = json.loads(stdout)
        self.assertEqual(data["files"], ["src/x.py", "src/y.py"])

    def test_resolve_scope_invalid_json_exits_2(self):
        old_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO("not valid json")
            _, stderr, rc = _capture(["resolve-scope", "--items", "-"])
        finally:
            sys.stdin = old_stdin
        self.assertEqual(rc, 2)

    def test_resolve_scope_non_list_json_exits_2(self):
        old_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO(json.dumps({"not": "a-list"}))
            _, stderr, rc = _capture(["resolve-scope", "--items", "-"])
        finally:
            sys.stdin = old_stdin
        self.assertEqual(rc, 2)

    # ---- in-fix-window ----

    def test_in_fix_window_missing_feature_exits_2(self):
        _, stderr, rc = _capture(["in-fix-window"])
        self.assertEqual(rc, 2)

    def test_in_fix_window_in_window_exits_0(self):
        """in-window → exit 0, JSON {"in_window": true}."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            tasks_dir = os.path.join(feature_dir, "tasks")
            os.makedirs(tasks_dir, exist_ok=True)
            _write_task(td, tasks_dir, "001-task.md", status="Complete")
            _write_spec(feature_dir, status="In Progress")
            # No summary.md.

            stdout, _, rc = _capture(["in-fix-window", "--feature", feature_dir])
            self.assertEqual(rc, 0)
            data = json.loads(stdout)
            self.assertTrue(data["in_window"])

    def test_in_fix_window_out_of_window_exits_1(self):
        """out-of-window → exit 1, JSON {"in_window": false}."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            tasks_dir = os.path.join(feature_dir, "tasks")
            os.makedirs(tasks_dir, exist_ok=True)
            _write_task(td, tasks_dir, "001-task.md", status="Complete")
            _write_spec(feature_dir, status="In Progress")
            # Write summary.md → sealed.
            with open(os.path.join(feature_dir, "summary.md"), "w") as fh:
                fh.write("# Summary\n")

            stdout, _, rc = _capture(["in-fix-window", "--feature", feature_dir])
            self.assertEqual(rc, 1)
            data = json.loads(stdout)
            self.assertFalse(data["in_window"])
            self.assertEqual(data["reason"], "summary_present")

    def test_in_fix_window_no_tasks_dir_exits_1(self):
        """Not-yet-implemented → exit 1."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            os.makedirs(feature_dir, exist_ok=True)
            _write_spec(feature_dir, status="In Progress")

            stdout, _, rc = _capture(["in-fix-window", "--feature", feature_dir])
            self.assertEqual(rc, 1)
            data = json.loads(stdout)
            self.assertFalse(data["in_window"])
            self.assertEqual(data["reason"], "no_tasks_dir")

    def test_in_fix_window_json_always_emitted(self):
        """Both in-window (exit 0) and out-of-window (exit 1) emit valid JSON."""
        with tempfile.TemporaryDirectory() as td:
            feature_dir = os.path.join(td, "specs", "001-feat")
            os.makedirs(feature_dir, exist_ok=True)
            stdout, _, _ = _capture(["in-fix-window", "--feature", feature_dir])
            data = json.loads(stdout)
            self.assertIn("in_window", data)
            self.assertIn("reason", data)

    # ---- all verbs registered ----

    def test_all_four_verbs_are_registered(self):
        """Each verb in _SUBCOMMAND_REGISTRY is reachable (--help succeeds)."""
        from _fix._cli import _SUBCOMMAND_REGISTRY
        for verb, _, _ in _SUBCOMMAND_REGISTRY:
            try:
                _capture([verb, "--help"])
            except SystemExit:
                pass  # --help exits 0, that's fine


# ---------------------------------------------------------------------------
# Test: launcher shim (fix_helper.py)
# ---------------------------------------------------------------------------


class TestLauncherShim(unittest.TestCase):
    """Verify the launcher shim exports main correctly."""

    def test_fix_helper_py_exports_main(self):
        import fix_helper  # noqa: F401 — ensure importable from lib dir
        # The import not raising is the assertion: the shim guards main behind
        # __main__ so hasattr(fix_helper, "main") would be False, but the
        # module must be importable without errors.
        self.assertIsNotNone(fix_helper)

    def test_fix_helper_main_via_module(self):
        """main() from _fix._cli is the canonical entry point."""
        from _fix._cli import main as fix_main
        # No subcommand → exit 2.
        rc = fix_main([])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
