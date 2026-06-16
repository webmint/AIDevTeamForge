"""Tests for the Phase 4 refutation verbs exposed via review_helper CLI.

Coverage:

Asymmetry test (most important — validates review's 5-finder/4-refuter split):
  - route-refutation with 5 present finders including performance-analyst;
    a performance-analyst-authored finding is routed to a non-perf refuter;
    performance-analyst NEVER appears as a refuter in any routing group.

Verb dispatch round-trips (real CLI dispatch via main([...]), exit 0):
  route-refutation:
    - basic round-trip: findings routed, groups emitted as JSON
    - perf-analyst asymmetry: 5-finder/4-refuter split (the critical check)
    - missing --findings returns 2
    - non-JSON --findings returns 2
    - non-array JSON --findings returns 2

  render-verify-brief:
    - round-trip with real refutation-preamble.md fixture → brief contains
      preamble text + findings block + scope block
    - missing --findings returns 2
    - missing --refuter returns 2
    - missing --scope-block returns 2
    - missing refutation-preamble.md in references-dir returns 2

  consume-verdicts:
    - round-trip on a sample verdict file in the contract format
      (# Refuter: / ## Verdict N / ...) → parsed status=complete
    - missing --verdicts returns 2
    - non-existent file → status=missing in JSON + exit 2
    - refuter hint applied when header absent

  apply-verdicts:
    - round-trip on findings+verdicts pair → four buckets emitted
    - high-stakes security uncertain → contested
    - [CONSTITUTION-VIOLATION] dismissed → contested (D7 carve-out)
    - missing --findings returns 2
    - missing --verdicts returns 2
    - bare-array verdicts accepted (not only consume-verdicts wrapper objects)
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

from _review._cli import main  # noqa: E402


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _finding(agent="code-reviewer", file="src/a.py", line=10,
             pattern="Naming lie", category="mislogic", tags=None):
    """Return a minimal ParsedFinding dict."""
    return {
        "agent": agent,
        "file": file,
        "line": line,
        "pattern": pattern,
        "severity": "High",
        "confidence": "Likely",
        "evidence": "x = bad_code()",
        "why": "why text",
        "remediation": "fix it",
        "category": category,
        "tags": tags if tags is not None else [],
    }


def _verdict_text(refuter="code-reviewer", status="complete", verdicts=None, reason=""):
    """Build a verdict file string matching the refutation-preamble.md contract."""
    if verdicts is None:
        verdicts = []
    count = len(verdicts)
    lines = [
        "# Refuter: {0}".format(refuter),
        "# Status: {0}".format(status),
    ]
    if reason:
        lines.append("# Reason: {0}".format(reason))
    lines.append("# Verdict count: {0}".format(count))
    lines.append("")
    for i, v in enumerate(verdicts, 1):
        lines.append("## Verdict {0}".format(i))
        lines.append("File: {0}".format(v.get("file", "src/a.py")))
        lines.append("Line: {0}".format(v.get("line", 10)))
        lines.append("Pattern: {0}".format(v.get("pattern", "Naming lie")))
        lines.append("Agent: {0}".format(v.get("agent", "code-reviewer")))
        lines.append("Verdict: {0}".format(v.get("verdict", "dismissed")))
        lines.append("Justification: {0}".format(v.get("justification", "no defect")))
        lines.append("Evidence:")
        lines.append("```")
        lines.append(v.get("evidence", "(no counter-quote)"))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def _write_json(d, path):
    """Write JSON to a file path (str)."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(d, fh)


def _capture_stdout(argv):
    """Run main(argv), capture stdout, return (exit_code, stdout_text).

    Catches SystemExit from argparse (missing required args etc.) and returns
    the exit code from the exception rather than letting it propagate.
    Stderr is swallowed to keep test output clean.
    """
    buf = io.StringIO()
    err_buf = io.StringIO()
    old_out = sys.stdout
    old_err = sys.stderr
    sys.stdout = buf
    sys.stderr = err_buf
    try:
        code = main(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
    return code, buf.getvalue()


# ---------------------------------------------------------------------------
# Tests: route-refutation — asymmetry (5-finder / 4-refuter split)
# ---------------------------------------------------------------------------

class TestRouteRefutationAsymmetry(unittest.TestCase):
    """Critical: performance-analyst is a FINDER only — never a refuter."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _findings_path(self, findings):
        p = os.path.join(self.tmp, "findings.json")
        _write_json(findings, p)
        return p

    def test_perf_analyst_finding_routed_to_priority_refuter(self):
        """A perf-authored finding is assigned to a priority-list refuter, not perf."""
        findings = [_finding(agent="performance-analyst")]
        fp = self._findings_path(findings)
        # 5 present finders including performance-analyst
        finders = "code-reviewer,architect,qa-reviewer,security-reviewer,performance-analyst"

        code, out = _capture_stdout([
            "route-refutation",
            "--findings", fp,
            "--finders", finders,
        ])
        self.assertEqual(code, 0, "exit code must be 0")
        groups = json.loads(out)
        self.assertIsInstance(groups, list)
        self.assertEqual(len(groups), 1)

        refuter = groups[0]["refuter"]
        # (a) The perf-authored finding is routed to a NON-author priority refuter
        self.assertNotEqual(
            refuter, "performance-analyst",
            "performance-analyst must not be assigned as a refuter for its own findings",
        )
        # The refuter must be one of the four priority refuters
        priority_set = {"code-reviewer", "architect", "qa-reviewer", "security-reviewer"}
        self.assertIn(
            refuter, priority_set,
            "refuter must be one of the four priority-list refuters, got {0!r}".format(refuter),
        )

    def test_performance_analyst_never_appears_as_refuter(self):
        """With any mix of findings, performance-analyst NEVER appears as a refuter."""
        # Mixed authorship: code-reviewer + security-reviewer + performance-analyst
        findings = [
            _finding(agent="code-reviewer", file="src/a.py", line=1, pattern="P1"),
            _finding(agent="security-reviewer", file="src/b.py", line=2, pattern="P2"),
            _finding(agent="performance-analyst", file="src/c.py", line=3, pattern="P3"),
        ]
        fp = self._findings_path(findings)
        finders = "code-reviewer,architect,qa-reviewer,security-reviewer,performance-analyst"

        code, out = _capture_stdout([
            "route-refutation",
            "--findings", fp,
            "--finders", finders,
        ])
        self.assertEqual(code, 0)
        groups = json.loads(out)

        all_refuters = {g["refuter"] for g in groups}
        self.assertNotIn(
            "performance-analyst", all_refuters,
            "performance-analyst must never appear as a refuter; got refuters: {0}".format(
                all_refuters
            ),
        )

    def test_perf_finding_routes_to_code_reviewer_first(self):
        """Code-reviewer (highest priority) takes the perf-authored finding."""
        findings = [_finding(agent="performance-analyst")]
        fp = self._findings_path(findings)
        # All 5 present
        finders = "code-reviewer,architect,qa-reviewer,security-reviewer,performance-analyst"

        code, out = _capture_stdout([
            "route-refutation",
            "--findings", fp,
            "--finders", finders,
        ])
        self.assertEqual(code, 0)
        groups = json.loads(out)
        # code-reviewer is first in the default priority list and is present
        self.assertEqual(groups[0]["refuter"], "code-reviewer")

    def test_perf_analyst_absent_from_finders_has_no_effect(self):
        """Explicitly omitting perf from finders still works; perf never a refuter."""
        findings = [_finding(agent="security-reviewer")]
        fp = self._findings_path(findings)
        # Only 4 finders (no performance-analyst)
        finders = "code-reviewer,architect,qa-reviewer,security-reviewer"

        code, out = _capture_stdout([
            "route-refutation",
            "--findings", fp,
            "--finders", finders,
        ])
        self.assertEqual(code, 0)
        groups = json.loads(out)
        all_refuters = {g["refuter"] for g in groups}
        self.assertNotIn("performance-analyst", all_refuters)
        self.assertEqual(groups[0]["refuter"], "code-reviewer")


# ---------------------------------------------------------------------------
# Tests: route-refutation — basic round-trips and error paths
# ---------------------------------------------------------------------------

class TestRouteRefutationVerb(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_basic_round_trip(self):
        """Multiple findings from different agents → correctly grouped."""
        findings = [
            _finding(agent="code-reviewer", file="a.py", line=1, pattern="P1"),
            _finding(agent="qa-reviewer",   file="b.py", line=2, pattern="P2"),
        ]
        fp = os.path.join(self.tmp, "findings.json")
        _write_json(findings, fp)

        code, out = _capture_stdout([
            "route-refutation",
            "--findings", fp,
            "--finders", "code-reviewer,architect,qa-reviewer,security-reviewer",
        ])
        self.assertEqual(code, 0)
        groups = json.loads(out)
        self.assertIsInstance(groups, list)
        # Two different authors → at most two routing groups
        self.assertGreaterEqual(len(groups), 1)
        for g in groups:
            self.assertIn("refuter", g)
            self.assertIn("findings", g)

    def test_missing_findings_flag_returns_2(self):
        """--findings absent → exit 2."""
        code, _ = _capture_stdout(["route-refutation"])
        self.assertEqual(code, 2)

    def test_nonexistent_findings_file_returns_2(self):
        """Non-existent --findings path → exit 2."""
        code, _ = _capture_stdout([
            "route-refutation",
            "--findings", "/nonexistent/path/findings.json",
        ])
        self.assertEqual(code, 2)

    def test_non_json_findings_file_returns_2(self):
        """Malformed JSON in findings file → exit 2."""
        fp = os.path.join(self.tmp, "bad.json")
        with open(fp, "w") as fh:
            fh.write("not json{{")
        code, _ = _capture_stdout(["route-refutation", "--findings", fp])
        self.assertEqual(code, 2)

    def test_non_array_json_returns_2(self):
        """Object (not array) findings JSON → exit 2."""
        fp = os.path.join(self.tmp, "obj.json")
        _write_json({"not": "an array"}, fp)
        code, _ = _capture_stdout(["route-refutation", "--findings", fp])
        self.assertEqual(code, 2)

    def test_empty_findings_returns_empty_list(self):
        """Empty findings array → empty groups list, exit 0."""
        fp = os.path.join(self.tmp, "empty.json")
        _write_json([], fp)
        code, out = _capture_stdout([
            "route-refutation",
            "--findings", fp,
            "--finders", "code-reviewer",
        ])
        self.assertEqual(code, 0)
        groups = json.loads(out)
        self.assertEqual(groups, [])


# ---------------------------------------------------------------------------
# Tests: render-verify-brief
# ---------------------------------------------------------------------------

class TestRenderVerifyBriefVerb(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        # Build a references dir with a minimal refutation-preamble.md
        self.refs_dir = os.path.join(self.tmp, "references")
        os.makedirs(self.refs_dir)
        self.preamble_text = (
            "# Refutation Preamble\n"
            "Cross-examine the assigned findings rigorously.\n"
            "Output format: # Refuter: / # Status: / ## Verdict N\n"
        )
        with open(os.path.join(self.refs_dir, "refutation-preamble.md"), "w") as fh:
            fh.write(self.preamble_text)

        # Minimal findings file
        self.findings = [
            _finding(agent="code-reviewer", file="src/auth.py", line=42,
                     pattern="Naming lie in authenticate()"),
        ]
        self.findings_path = os.path.join(self.tmp, "findings.json")
        _write_json(self.findings, self.findings_path)

        # Scope block file
        self.scope_text = "Scope: 3 files changed in feature/auth\n- src/auth.py\n"
        self.scope_path = os.path.join(self.tmp, "scope_block.txt")
        with open(self.scope_path, "w") as fh:
            fh.write(self.scope_text)

    def test_brief_contains_preamble_text(self):
        """Brief stdout must contain the preamble content from refutation-preamble.md."""
        code, out = _capture_stdout([
            "render-verify-brief",
            "--findings", self.findings_path,
            "--refuter", "architect",
            "--references-dir", self.refs_dir,
            "--scope-block", self.scope_path,
            "--source-root", self.tmp,
        ])
        self.assertEqual(code, 0, "exit code must be 0; got: {0}".format(code))
        self.assertIn("Cross-examine the assigned findings rigorously", out)

    def test_brief_contains_findings(self):
        """Brief stdout must contain the finding's pattern text."""
        code, out = _capture_stdout([
            "render-verify-brief",
            "--findings", self.findings_path,
            "--refuter", "architect",
            "--references-dir", self.refs_dir,
            "--scope-block", self.scope_path,
        ])
        self.assertEqual(code, 0)
        self.assertIn("Naming lie in authenticate()", out)

    def test_brief_contains_scope_block(self):
        """Brief stdout must contain the scope block text."""
        code, out = _capture_stdout([
            "render-verify-brief",
            "--findings", self.findings_path,
            "--refuter", "architect",
            "--references-dir", self.refs_dir,
            "--scope-block", self.scope_path,
        ])
        self.assertEqual(code, 0)
        self.assertIn("src/auth.py", out)

    def test_tmp_path_appears_in_brief(self):
        """Custom --tmp-path value must appear in the brief's closing instruction."""
        custom_path = "/tmp/forge-review/verdicts-architect.md"
        code, out = _capture_stdout([
            "render-verify-brief",
            "--findings", self.findings_path,
            "--refuter", "architect",
            "--references-dir", self.refs_dir,
            "--scope-block", self.scope_path,
            "--tmp-path", custom_path,
        ])
        self.assertEqual(code, 0)
        self.assertIn(custom_path, out)

    def test_missing_findings_returns_2(self):
        """--findings absent → exit 2."""
        code, _ = _capture_stdout([
            "render-verify-brief",
            "--refuter", "architect",
            "--references-dir", self.refs_dir,
            "--scope-block", self.scope_path,
        ])
        self.assertEqual(code, 2)

    def test_missing_refuter_returns_2(self):
        """--refuter absent → exit 2."""
        code, _ = _capture_stdout([
            "render-verify-brief",
            "--findings", self.findings_path,
            "--references-dir", self.refs_dir,
            "--scope-block", self.scope_path,
        ])
        self.assertEqual(code, 2)

    def test_missing_scope_block_returns_2(self):
        """--scope-block absent → exit 2."""
        code, _ = _capture_stdout([
            "render-verify-brief",
            "--findings", self.findings_path,
            "--refuter", "architect",
            "--references-dir", self.refs_dir,
        ])
        self.assertEqual(code, 2)

    def test_missing_preamble_file_returns_2(self):
        """references-dir without refutation-preamble.md → exit 2."""
        empty_refs = os.path.join(self.tmp, "empty_refs")
        os.makedirs(empty_refs)
        code, _ = _capture_stdout([
            "render-verify-brief",
            "--findings", self.findings_path,
            "--refuter", "architect",
            "--references-dir", empty_refs,
            "--scope-block", self.scope_path,
        ])
        self.assertEqual(code, 2)


# ---------------------------------------------------------------------------
# Tests: consume-verdicts
# ---------------------------------------------------------------------------

class TestConsumeVerdictsVerb(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _write_verdict_file(self, text, name="verdicts.md"):
        p = os.path.join(self.tmp, name)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    def test_round_trip_complete_verdict_file(self):
        """A well-formed verdict file parses to status=complete with verdicts."""
        text = _verdict_text(
            refuter="architect",
            status="complete",
            verdicts=[{
                "file": "src/auth.py",
                "line": 42,
                "pattern": "Naming lie",
                "agent": "code-reviewer",
                "verdict": "dismissed",
                "justification": "The function name accurately describes its purpose.",
            }],
        )
        vp = self._write_verdict_file(text)
        code, out = _capture_stdout([
            "consume-verdicts",
            "--verdicts", vp,
            "--refuter", "architect",
        ])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["refuter"], "architect")
        self.assertEqual(result["verdict_count"], 1)
        self.assertEqual(len(result["verdicts"]), 1)
        self.assertEqual(result["verdicts"][0]["verdict"], "dismissed")

    def test_confirmed_verdict_parses(self):
        """A verdict with verdict=confirmed parses correctly."""
        text = _verdict_text(
            refuter="qa-reviewer",
            status="complete",
            verdicts=[{
                "file": "src/db.py",
                "line": 10,
                "pattern": "Missing null check",
                "agent": "security-reviewer",
                "verdict": "confirmed",
                "justification": "The defect is real — no null guard exists.",
            }],
        )
        vp = self._write_verdict_file(text, "verdicts-qa.md")
        code, out = _capture_stdout(["consume-verdicts", "--verdicts", vp])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["verdicts"][0]["verdict"], "confirmed")

    def test_missing_verdicts_flag_returns_2(self):
        """--verdicts absent → exit 2."""
        code, _ = _capture_stdout(["consume-verdicts"])
        self.assertEqual(code, 2)

    def test_nonexistent_verdicts_file_returns_2_and_status_missing(self):
        """Non-existent file → exit 2 + status=missing in JSON output."""
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            code = main(["consume-verdicts", "--verdicts", "/nonexistent/v.md"])
        finally:
            sys.stdout = old
        out = buf.getvalue()
        self.assertEqual(code, 2)
        result = json.loads(out)
        self.assertEqual(result["status"], "missing")

    def test_refuter_hint_applied_when_header_absent(self):
        """--refuter hint fills in 'unknown' when # Refuter: header is missing."""
        # Build a verdict file without the # Refuter: header
        text = (
            "# Status: complete\n"
            "# Verdict count: 1\n"
            "\n"
            "## Verdict 1\n"
            "File: src/x.py\n"
            "Line: 5\n"
            "Pattern: Dead branch\n"
            "Agent: code-reviewer\n"
            "Verdict: dismissed\n"
            "Justification: Branch is reachable.\n"
            "Evidence:\n"
            "```\n"
            "if x: pass\n"
            "```\n"
        )
        vp = self._write_verdict_file(text, "no_header.md")
        code, out = _capture_stdout([
            "consume-verdicts",
            "--verdicts", vp,
            "--refuter", "security-reviewer",
        ])
        self.assertEqual(code, 0)
        result = json.loads(out)
        # The hint must have replaced "unknown"
        self.assertEqual(result["refuter"], "security-reviewer")


# ---------------------------------------------------------------------------
# Tests: apply-verdicts
# ---------------------------------------------------------------------------

class TestApplyVerdictsVerb(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _write(self, obj, name):
        p = os.path.join(self.tmp, name)
        _write_json(obj, p)
        return p

    def _run(self, findings, verdicts, verdicts_name="verdicts.json"):
        fp = self._write(findings, "findings.json")
        vp = self._write(verdicts, verdicts_name)
        return _capture_stdout([
            "apply-verdicts",
            "--findings", fp,
            "--verdicts", vp,
        ])

    def test_four_buckets_always_present(self):
        """Output always has confirmed / dismissed / uncertain / contested keys."""
        code, out = self._run([], [])
        self.assertEqual(code, 0)
        result = json.loads(out)
        for key in ("confirmed", "dismissed", "uncertain", "contested"):
            self.assertIn(key, result)

    def test_confirmed_finding_lands_in_confirmed_bucket(self):
        """A verdict=confirmed finding goes to confirmed, carries verify_confidence."""
        f = _finding(agent="code-reviewer", file="src/a.py", line=10, pattern="P1")
        verdict = {
            "file": "src/a.py", "line": 10, "pattern": "P1",
            "agent": "code-reviewer", "verdict": "confirmed",
            "refuter": "architect", "justification": "real", "evidence": "...",
        }
        code, out = self._run([f], [verdict])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(len(result["confirmed"]), 1)
        self.assertEqual(result["confirmed"][0].get("verify_confidence"), "confirmed")
        self.assertEqual(len(result["dismissed"]), 0)

    def test_dismissed_finding_lands_in_dismissed_bucket(self):
        """A verdict=dismissed, non-constitution finding goes to dismissed."""
        f = _finding(agent="code-reviewer", file="src/a.py", line=10, pattern="P1",
                     category="mislogic", tags=[])
        verdict = {
            "file": "src/a.py", "line": 10, "pattern": "P1",
            "agent": "code-reviewer", "verdict": "dismissed",
            "refuter": "architect", "justification": "no defect", "evidence": "...",
        }
        code, out = self._run([f], [verdict])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(len(result["dismissed"]), 1)
        self.assertEqual(len(result["confirmed"]), 0)

    def test_high_stakes_security_uncertain_goes_to_contested(self):
        """A security-category uncertain finding surfaces in contested (D7)."""
        f = _finding(agent="security-reviewer", file="src/auth.py", line=20,
                     pattern="SQL injection risk", category="security", tags=[])
        verdict = {
            "file": "src/auth.py", "line": 20, "pattern": "SQL injection risk",
            "agent": "security-reviewer", "verdict": "uncertain",
            "refuter": "code-reviewer", "justification": "unsure", "evidence": "...",
        }
        code, out = self._run([f], [verdict])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(len(result["contested"]), 1)
        self.assertIn("[CONTESTED]", result["contested"][0].get("tags", []))
        self.assertEqual(len(result["uncertain"]), 0)

    def test_constitution_violation_dismissed_goes_to_contested(self):
        """A dismissed [CONSTITUTION-VIOLATION] finding → contested (D7 carve-out)."""
        f = _finding(
            agent="code-reviewer", file="src/b.py", line=5,
            pattern="Direct DOM mutation",
            category="mislogic",
            tags=["[CONSTITUTION-VIOLATION]"],
        )
        verdict = {
            "file": "src/b.py", "line": 5, "pattern": "Direct DOM mutation",
            "agent": "code-reviewer", "verdict": "dismissed",
            "refuter": "architect", "justification": "no issue", "evidence": "...",
        }
        code, out = self._run([f], [verdict])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(len(result["contested"]), 1)
        contested_finding = result["contested"][0]
        self.assertIn("[CONTESTED]", contested_finding.get("tags", []))
        self.assertEqual(len(result["dismissed"]), 0)

    def test_low_stakes_uncertain_goes_to_uncertain_bucket(self):
        """A mislogic uncertain finding lands in uncertain, not contested."""
        f = _finding(agent="code-reviewer", file="src/c.py", line=7,
                     pattern="Dead branch", category="mislogic", tags=[])
        verdict = {
            "file": "src/c.py", "line": 7, "pattern": "Dead branch",
            "agent": "code-reviewer", "verdict": "uncertain",
            "refuter": "architect", "justification": "unclear", "evidence": "...",
        }
        code, out = self._run([f], [verdict])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(len(result["uncertain"]), 1)
        self.assertEqual(len(result["contested"]), 0)

    def test_bare_array_verdicts_accepted(self):
        """--verdicts accepts a bare JSON array (not only wrapped objects)."""
        f = _finding(agent="architect", file="src/d.py", line=3, pattern="P")
        verdicts = [{
            "file": "src/d.py", "line": 3, "pattern": "P",
            "agent": "architect", "verdict": "confirmed",
            "refuter": "code-reviewer", "justification": "confirmed", "evidence": "...",
        }]
        code, out = self._run([f], verdicts)
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(len(result["confirmed"]), 1)

    def test_consume_verdicts_wrapper_object_accepted(self):
        """--verdicts accepts a consume-verdicts result object (dict with 'verdicts' key)."""
        f = _finding(agent="qa-reviewer", file="src/e.py", line=1, pattern="Q")
        verdict_dict = {
            "status": "complete",
            "refuter": "code-reviewer",
            "verdict_count": 1,
            "verdicts": [{
                "file": "src/e.py", "line": 1, "pattern": "Q",
                "agent": "qa-reviewer", "verdict": "dismissed",
                "refuter": "code-reviewer", "justification": "no bug", "evidence": "...",
            }],
        }
        fp = self._write([f], "findings2.json")
        vp = self._write(verdict_dict, "wrapped_verdict.json")
        code, out = _capture_stdout([
            "apply-verdicts",
            "--findings", fp,
            "--verdicts", vp,
        ])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(len(result["dismissed"]), 1)

    def test_missing_findings_returns_2(self):
        """--findings absent → exit 2."""
        vp = self._write([], "v.json")
        code, _ = _capture_stdout(["apply-verdicts", "--verdicts", vp])
        self.assertEqual(code, 2)

    def test_missing_verdicts_returns_2(self):
        """--verdicts absent → exit 2."""
        fp = self._write([], "f.json")
        code, _ = _capture_stdout(["apply-verdicts", "--findings", fp])
        self.assertEqual(code, 2)

    def test_nonexistent_findings_file_returns_2(self):
        """Non-existent --findings path → exit 2."""
        vp = self._write([], "v.json")
        code, _ = _capture_stdout([
            "apply-verdicts",
            "--findings", "/nonexistent/findings.json",
            "--verdicts", vp,
        ])
        self.assertEqual(code, 2)

    def test_nonexistent_verdicts_file_returns_2(self):
        """Non-existent --verdicts path → exit 2."""
        fp = self._write([], "f.json")
        code, _ = _capture_stdout([
            "apply-verdicts",
            "--findings", fp,
            "--verdicts", "/nonexistent/verdicts.json",
        ])
        self.assertEqual(code, 2)


# ---------------------------------------------------------------------------
# Tests: no _audit imports in _review source
# ---------------------------------------------------------------------------

class TestNoAuditImports(unittest.TestCase):
    """Structural: _review/ must not import from _audit/."""

    def test_cli_no_audit_import(self):
        """_review/_cli.py must not contain from _audit or import _audit."""
        cli_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "src" / "devforge" / "lib" / "_review" / "_cli.py"
        )
        with open(cli_path, "r", encoding="utf-8") as fh:
            text = fh.read()
        self.assertNotIn("from _audit", text)
        self.assertNotIn("import _audit", text)

    def test_review_package_no_audit_import(self):
        """No file under _review/ has Python import statements from _audit/."""
        import re
        # Match actual Python import lines, not docstring/comment mentions.
        # Examples of what to catch:
        #   from _audit._foo import bar
        #   from _audit import bar
        #   import _audit
        # The patterns below require the keyword at the start of a non-comment,
        # non-string line.  Docstring mentions like "mirrors _audit/_scope.py"
        # are permitted — they contain neither "from _audit" at line start nor
        # "import _audit" as a standalone import.
        _import_re = re.compile(
            r'^\s*(from\s+_audit\b|import\s+_audit\b)',
            re.MULTILINE,
        )
        review_dir = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "src" / "devforge" / "lib" / "_review"
        )
        for fname in os.listdir(review_dir):
            if not fname.endswith(".py"):
                continue
            fpath = review_dir / fname
            with open(fpath, "r", encoding="utf-8") as fh:
                text = fh.read()
            m = _import_re.search(text)
            self.assertIsNone(
                m,
                "{0} contains an import from _audit — not allowed. "
                "Match: {1!r}".format(fname, m.group(0) if m else ""),
            )


if __name__ == "__main__":
    unittest.main()
