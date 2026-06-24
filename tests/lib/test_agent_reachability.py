"""tests/lib/test_agent_reachability.py

Tests for scripts/lib/agent_reachability.py.

Structure
---------
TestLiveSrc   — the PERMANENT GATE: runs find_orphans against the real
                src/ tree.  This test IS the enforcement gate — it fails
                the pytest suite if an orphan is introduced.
TestOrphans   — synthetic fixture: a roster agent with no dispatch → FAIL
TestUnknown   — synthetic fixture: breakdown table names unknown agent → FAIL
TestRelayOnly — synthetic fixture: relay-only agent → relay_only FAIL
TestDictKeys  — synthetic fixture: agent reachable ONLY via dict-keyed helper
                list (e.g. _FOCUS_BLOCKS) → PASS (dict-key parsing works)
TestTableOnly — synthetic fixture: agent reachable ONLY via breakdown table row
                → PASS (data-driven engineer-agent path)
TestAllowlist — synthetic fixture: relay-only agent in RELAY_ONLY_ALLOWLIST
                → NOT flagged
TestCLI       — the CLI exits non-zero on a fixture with an orphan, 0 on live tree
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Make scripts/lib importable
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
_SCRIPTS_LIB = _REPO_ROOT / "scripts" / "lib"
if str(_SCRIPTS_LIB) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_LIB))

import agent_reachability as _mod  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers for synthetic fixtures
# ---------------------------------------------------------------------------

def _write(path, text):
    # type: (Path, str) -> None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")


def _make_minimal_repo(tmp_path, agents, subagent_dispatches=None,
                       breakdown_table_rows=None, py_files=None,
                       relay_line_breakdown=None, relay_line_plan=None):
    # type: (Path, list, list, list, dict, str, str) -> Path
    """Build a minimal synthetic repo under tmp_path.

    Parameters
    ----------
    agents : list of str
        Agent file stems to create under src/agents/.
    subagent_dispatches : list of str, optional
        Agent names to include as ``subagent_type: <name>`` in a command.
    breakdown_table_rows : list of str, optional
        Raw table-row strings like ``| some files | agent-name |``
        inserted into the breakdown Agent Assignment table.
    py_files : dict, optional
        Mapping from relative-to-lib-root path string to file content string.
        These simulate helper Python files with dispatch constants.
    relay_line_breakdown : str, optional
        The "may be named:" line for breakdown/main.md.
    relay_line_plan : str, optional
        The "may be named:" line for plan/main.md.
    """
    repo = tmp_path

    # src/agents/
    for name in agents:
        _write(repo / "src" / "agents" / f"{name}.md", f"# {name}\n")

    # src/commands/test-cmd/main.md (for subagent_type dispatches)
    if subagent_dispatches:
        dispatch_lines = "\n".join(
            f"Dispatch with `subagent_type: {a}`."
            for a in subagent_dispatches
        )
        _write(
            repo / "src" / "commands" / "test-cmd" / "main.md",
            f"# Test command\n\n{dispatch_lines}\n",
        )

    # src/commands/breakdown/main.md
    breakdown_rows_text = ""
    if breakdown_table_rows:
        breakdown_rows_text = "\n".join(breakdown_table_rows)

    relay_bd = relay_line_breakdown or ""
    relay_pl_content = ""
    if relay_line_plan:
        relay_pl_content = relay_line_plan

    breakdown_content = f"""# /breakdown

## Phase 2 (consult)

{relay_bd}

### Agent Assignment table

| Files in... | Agent |
|-------------|-------|
{breakdown_rows_text}
"""
    _write(repo / "src" / "commands" / "breakdown" / "main.md", breakdown_content)

    # src/commands/plan/main.md
    plan_content = f"""# /plan

## Phase 3 (consult)

{relay_pl_content}
"""
    _write(repo / "src" / "commands" / "plan" / "main.md", plan_content)

    # Helper Python files
    if py_files:
        lib_root = repo / "src" / "devforge" / "lib"
        for rel_path, content in py_files.items():
            target = lib_root / rel_path
            _write(target, content)

    return repo


# ---------------------------------------------------------------------------
# TestLiveSrc — the PERMANENT GATE
# ---------------------------------------------------------------------------

class TestLiveSrc(unittest.TestCase):
    """Live-src check: all roster agents must have an executor.

    This test IS the permanent enforcement gate.  If it fails, an orphan
    was introduced into src/.  Fix the orphan before merging.

    SCOPE: covers type-1 (orphaned agent) + unknown-assignment only.
    Does NOT cover type-2 forward-prose or type-3 finding-inertness.
    """

    def test_no_orphans_in_live_src(self):
        result = _mod.find_orphans(_REPO_ROOT)
        orphans = result["orphan_agents"]
        unknowns = result["unknown_assignments"]
        relay_only = result["relay_only"]

        msg_parts = []
        if orphans:
            msg_parts.append(
                "Orphaned agents (no executor): {}".format(orphans)
            )
        if unknowns:
            msg_parts.append(
                "Unknown assignments in /breakdown table: {}".format(unknowns)
            )
        if relay_only:
            msg_parts.append(
                "Relay-only agents (relay is not an executor): {}".format(relay_only)
            )

        if msg_parts:
            self.fail(
                "agent_reachability check found violations:\n"
                + "\n".join(msg_parts)
                + "\n\nFix the orphan(s) in src/ before merging."
            )

    def test_result_shape(self):
        """find_orphans always returns a dict with the three expected keys."""
        result = _mod.find_orphans(_REPO_ROOT)
        self.assertIn("orphan_agents", result)
        self.assertIn("unknown_assignments", result)
        self.assertIn("relay_only", result)
        self.assertIsInstance(result["orphan_agents"], list)
        self.assertIsInstance(result["unknown_assignments"], list)
        self.assertIsInstance(result["relay_only"], list)


# ---------------------------------------------------------------------------
# TestOrphans — orphaned agent (type-1 FAIL)
# ---------------------------------------------------------------------------

class TestOrphans(unittest.TestCase):
    """An agent in the roster with no dispatch path → appears in orphan_agents."""

    def test_orphaned_agent_detected(self, tmp_path=None):
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        _make_minimal_repo(
            tmp_path,
            agents=["code-reviewer", "orphan-agent"],
            subagent_dispatches=["code-reviewer"],  # code-reviewer is dispatched
            # orphan-agent has no dispatch
        )
        result = _mod.find_orphans(tmp_path)
        self.assertIn("orphan-agent", result["orphan_agents"])
        self.assertNotIn("code-reviewer", result["orphan_agents"])

    def test_all_dispatched_agents_not_orphaned(self, tmp_path=None):
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        _make_minimal_repo(
            tmp_path,
            agents=["code-reviewer"],
            subagent_dispatches=["code-reviewer"],
        )
        result = _mod.find_orphans(tmp_path)
        self.assertEqual(result["orphan_agents"], [])

    def test_empty_roster_no_orphans(self, tmp_path=None):
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        # No agents at all
        _make_minimal_repo(tmp_path, agents=[])
        result = _mod.find_orphans(tmp_path)
        self.assertEqual(result["orphan_agents"], [])


# ---------------------------------------------------------------------------
# TestUnknown — unknown assignment in breakdown table (FAIL)
# ---------------------------------------------------------------------------

class TestUnknown(unittest.TestCase):
    """A breakdown table row naming an agent not in the roster → unknown_assignments."""

    def test_unknown_assignment_detected(self, tmp_path=None):
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        _make_minimal_repo(
            tmp_path,
            agents=["backend-engineer"],
            subagent_dispatches=[],
            breakdown_table_rows=[
                "| API endpoints | backend-engineer |",
                "| Widgets       | ghost-agent |",  # not in roster
            ],
        )
        result = _mod.find_orphans(tmp_path)
        self.assertIn("ghost-agent", result["unknown_assignments"])
        self.assertNotIn("backend-engineer", result["unknown_assignments"])

    def test_known_assignment_not_flagged(self, tmp_path=None):
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        _make_minimal_repo(
            tmp_path,
            agents=["backend-engineer"],
            breakdown_table_rows=["| API endpoints | backend-engineer |"],
        )
        result = _mod.find_orphans(tmp_path)
        self.assertEqual(result["unknown_assignments"], [])


# ---------------------------------------------------------------------------
# TestRelayOnly — relay-only agent (OQ-4 hard-fail)
# ---------------------------------------------------------------------------

class TestRelayOnly(unittest.TestCase):
    """An agent named ONLY in a consult-relay list (no other executor) → relay_only."""

    def test_relay_only_agent_in_relay_only_list(self, tmp_path=None):
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        _make_minimal_repo(
            tmp_path,
            agents=["relay-agent", "code-reviewer"],
            subagent_dispatches=["code-reviewer"],  # code-reviewer has a real executor
            relay_line_breakdown=(
                "Any decomposition-relevant specialist may be named: "
                "`relay-agent`, `code-reviewer`."
            ),
        )
        result = _mod.find_orphans(tmp_path)
        self.assertIn("relay-agent", result["relay_only"])
        # relay-agent also has no real executor, so it's also an orphan
        self.assertIn("relay-agent", result["orphan_agents"])
        # code-reviewer has a subagent_type dispatch, so NOT relay-only
        self.assertNotIn("code-reviewer", result["relay_only"])

    def test_relay_and_real_executor_not_relay_only(self, tmp_path=None):
        """An agent in the relay list AND dispatched via subagent_type → NOT relay_only."""
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        _make_minimal_repo(
            tmp_path,
            agents=["mixed-agent"],
            subagent_dispatches=["mixed-agent"],  # real executor
            relay_line_breakdown=(
                "Any decomposition-relevant specialist may be named: `mixed-agent`."
            ),
        )
        result = _mod.find_orphans(tmp_path)
        self.assertNotIn("mixed-agent", result["relay_only"])
        self.assertNotIn("mixed-agent", result["orphan_agents"])

    def test_plan_relay_line_also_detected(self, tmp_path=None):
        """The plan/main.md relay line is also parsed."""
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        _make_minimal_repo(
            tmp_path,
            agents=["plan-relay-agent"],
            relay_line_plan=(
                "Any planning-relevant specialist may be named: `plan-relay-agent`."
            ),
        )
        result = _mod.find_orphans(tmp_path)
        self.assertIn("plan-relay-agent", result["relay_only"])
        self.assertIn("plan-relay-agent", result["orphan_agents"])


# ---------------------------------------------------------------------------
# TestDictKeys — agent reachable via dict-keyed helper list → PASS
# ---------------------------------------------------------------------------

class TestDictKeys(unittest.TestCase):
    """An agent dispatched ONLY via a dict-keyed constant (_FOCUS_BLOCKS-style) → NOT flagged."""

    def test_dict_key_agent_not_orphaned(self, tmp_path=None):
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        # Simulate a _FOCUS_BLOCKS-style dict in a helper py file
        py_content = '''\
"""Mock _brief.py"""
_FOCUS_BLOCKS = {
    "dict-dispatch-agent": "does some review",
}
'''
        _make_minimal_repo(
            tmp_path,
            agents=["dict-dispatch-agent"],
            py_files={
                "_review/_brief.py": py_content,
            },
        )
        result = _mod.find_orphans(tmp_path)
        self.assertNotIn("dict-dispatch-agent", result["orphan_agents"])

    def test_list_agent_not_orphaned(self, tmp_path=None):
        """An agent in a flat-list constant is also NOT orphaned."""
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        # Use the ANNOTATED form (matches the real _preflight.py declaration
        # ``_AUDIT_AGENTS: List[str] = [...]``) so this fixture would have
        # caught the AnnAssign bug in FIX 1 if it had been written first.
        py_content = '''\
"""Mock _preflight.py"""
from typing import List
_AUDIT_AGENTS: List[str] = ["list-dispatch-agent"]
'''
        _make_minimal_repo(
            tmp_path,
            agents=["list-dispatch-agent"],
            py_files={
                "_audit/_preflight.py": py_content,
            },
        )
        result = _mod.find_orphans(tmp_path)
        self.assertNotIn("list-dispatch-agent", result["orphan_agents"])

    def test_reviewer_vocab_dict_keys_not_orphaned(self, tmp_path=None):
        """Dict keys in a _REVIEWER_VOCAB-style constant are parsed correctly."""
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        py_content = '''\
"""Mock _cmds_review_panel.py"""
_REVIEWER_VOCAB = {
    "vocab-agent": ("APPROVE", frozenset(["APPROVE", "REJECT"])),
}
'''
        _make_minimal_repo(
            tmp_path,
            agents=["vocab-agent"],
            py_files={
                "_implement/_cmds_review_panel.py": py_content,
            },
        )
        result = _mod.find_orphans(tmp_path)
        self.assertNotIn("vocab-agent", result["orphan_agents"])


# ---------------------------------------------------------------------------
# TestTableOnly — agent reachable only via breakdown table row → PASS
# ---------------------------------------------------------------------------

class TestTableOnly(unittest.TestCase):
    """Engineer agents dispatched via the breakdown table (never subagent_type) → PASS."""

    def test_table_row_agent_not_orphaned(self, tmp_path=None):
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        _make_minimal_repo(
            tmp_path,
            agents=["backend-engineer", "frontend-engineer"],
            breakdown_table_rows=[
                "| API endpoints | backend-engineer |",
                "| UI components | frontend-engineer |",
            ],
        )
        result = _mod.find_orphans(tmp_path)
        self.assertNotIn("backend-engineer", result["orphan_agents"])
        self.assertNotIn("frontend-engineer", result["orphan_agents"])

    def test_prose_agent_cell_extracts_roster_names(self, tmp_path=None):
        """Table cells with prose like 'owning stack engineer (backend-engineer / ...)' → extracted."""
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        _make_minimal_repo(
            tmp_path,
            agents=["backend-engineer", "frontend-engineer"],
            breakdown_table_rows=[
                "| Perf-critical path | owning stack engineer (backend-engineer / frontend-engineer) |",
            ],
        )
        result = _mod.find_orphans(tmp_path)
        self.assertNotIn("backend-engineer", result["orphan_agents"])
        self.assertNotIn("frontend-engineer", result["orphan_agents"])


# ---------------------------------------------------------------------------
# TestAllowlist — allowlisted relay-only agent → NOT flagged
# ---------------------------------------------------------------------------

class TestAllowlist(unittest.TestCase):
    """A relay-only agent in RELAY_ONLY_ALLOWLIST is NOT flagged."""

    def test_allowlisted_agent_not_flagged(self, tmp_path=None):
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        _make_minimal_repo(
            tmp_path,
            agents=["allowlisted-relay-agent"],
            relay_line_breakdown=(
                "Any decomposition-relevant specialist may be named: "
                "`allowlisted-relay-agent`."
            ),
        )

        # Patch the allowlist temporarily
        original = _mod.RELAY_ONLY_ALLOWLIST
        _mod.RELAY_ONLY_ALLOWLIST = frozenset(["allowlisted-relay-agent"])
        try:
            result = _mod.find_orphans(tmp_path)
        finally:
            _mod.RELAY_ONLY_ALLOWLIST = original

        # An allowlisted relay-only agent is exempt from BOTH relay_only AND
        # orphan_agents — relay IS its declared executor by design.
        # The allowlist is the OQ-4 escape valve: legitimately relay-only
        # agents earn an explicit named entry here, not a rule relaxation.
        self.assertNotIn("allowlisted-relay-agent", result["relay_only"])
        self.assertNotIn("allowlisted-relay-agent", result["orphan_agents"])


# ---------------------------------------------------------------------------
# TestCLI — CLI exit codes
# ---------------------------------------------------------------------------

class TestCLI(unittest.TestCase):
    """The CLI exits non-zero on a fixture with an orphan, 0 on the live tree."""

    def _run_cli(self, *args):
        # type: (*str) -> subprocess.CompletedProcess
        cli = _REPO_ROOT / "scripts" / "verify-agent-reachability.py"
        cmd = [sys.executable, str(cli)] + list(args)
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

    def test_cli_live_tree_exits_zero(self):
        proc = self._run_cli(str(_REPO_ROOT))
        self.assertEqual(
            proc.returncode, 0,
            msg=(
                "CLI returned non-zero on live tree.\n"
                "stdout: {}\nstderr: {}".format(proc.stdout, proc.stderr)
            ),
        )

    def test_cli_orphan_fixture_exits_nonzero(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_minimal_repo(
                tmp_path,
                agents=["code-reviewer", "orphan-agent"],
                subagent_dispatches=["code-reviewer"],
            )
            proc = self._run_cli(str(tmp_path))
            self.assertNotEqual(
                proc.returncode, 0,
                msg=(
                    "CLI should exit non-zero when an orphan exists.\n"
                    "stdout: {}".format(proc.stdout)
                ),
            )
            self.assertIn("orphan-agent", proc.stdout)

    def test_cli_clean_fixture_exits_zero(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_minimal_repo(
                tmp_path,
                agents=["code-reviewer"],
                subagent_dispatches=["code-reviewer"],
            )
            proc = self._run_cli(str(tmp_path))
            self.assertEqual(
                proc.returncode, 0,
                msg=(
                    "CLI should exit 0 when all agents are reachable.\n"
                    "stdout: {}\nstderr: {}".format(proc.stdout, proc.stderr)
                ),
            )

    def test_cli_missing_src_exits_2(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            # A completely empty directory — no src/
            proc = self._run_cli(td)
            self.assertEqual(proc.returncode, 2)

    def test_cli_scope_disclaimer_in_output(self):
        """The CLI output must include the scope disclaimer (D5/D8)."""
        proc = self._run_cli(str(_REPO_ROOT))
        self.assertIn("type-1", proc.stdout)
        self.assertIn("type-2", proc.stdout)


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------

class TestEdgeCases(unittest.TestCase):

    def test_single_word_tokens_not_flagged_as_unknown(self, tmp_path=None):
        """Plain English words in breakdown table cells are not flagged as unknown."""
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        # Row with only non-hyphenated words in agent column
        _make_minimal_repo(
            tmp_path,
            agents=["backend-engineer"],
            breakdown_table_rows=[
                "| Some files | owning stack engineer |",
                "| API | backend-engineer |",
            ],
        )
        result = _mod.find_orphans(tmp_path)
        # "owning", "stack", "engineer" are single-word tokens, not agent slugs
        self.assertEqual(result["unknown_assignments"], [])

    def test_multiple_agents_in_prose_cell(self, tmp_path=None):
        """Multiple agent names extracted from a single prose cell."""
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        _make_minimal_repo(
            tmp_path,
            agents=["backend-engineer", "frontend-engineer", "mobile-engineer"],
            breakdown_table_rows=[
                "| Cross-stack | backend-engineer / frontend-engineer / mobile-engineer |",
            ],
        )
        result = _mod.find_orphans(tmp_path)
        self.assertNotIn("backend-engineer", result["orphan_agents"])
        self.assertNotIn("frontend-engineer", result["orphan_agents"])
        self.assertNotIn("mobile-engineer", result["orphan_agents"])

    def test_nonexistent_py_files_dont_crash(self, tmp_path=None):
        """Missing helper py files return empty sets, don't crash."""
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        # No py_files at all — the lib directory won't exist
        _make_minimal_repo(
            tmp_path,
            agents=["some-agent"],
            subagent_dispatches=["some-agent"],
        )
        # Should not raise
        result = _mod.find_orphans(tmp_path)
        self.assertIsInstance(result, dict)

    def test_subagent_nonroster_not_unknown(self, tmp_path=None):
        """A subagent_type naming a non-roster agent (external plugin) is not flagged.

        The spec says: a subagent_type naming a NON-roster agent (e.g.
        cavecrew-reviewer) is NOT a roster agent and NOT a failure.
        We only flag unknown_assignments from the breakdown table, not from
        subagent_type dispatches.
        """
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        _make_minimal_repo(
            tmp_path,
            agents=["code-reviewer"],
            subagent_dispatches=["code-reviewer", "external-plugin-agent"],
        )
        result = _mod.find_orphans(tmp_path)
        # external-plugin-agent is not in roster — but it's a subagent_type dispatch,
        # not a breakdown-table assignment, so it should NOT appear in unknown_assignments
        self.assertNotIn("external-plugin-agent", result["unknown_assignments"])

    def test_negated_backtick_not_extracted(self, tmp_path=None):
        """A backtick-quoted agent name preceded by NOT must NOT be extracted.

        The live "Non-server host" row contains ``NOT `backend-engineer` by
        default`` in its Agent column — this is a negation, not a dispatch.
        It must not be counted as a dispatch of backend-engineer (FIX 3).
        """
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)

        # Agent "negated-agent" appears ONLY in a NOT `…` negation context.
        # It should still appear as an orphan (no real executor).
        _make_minimal_repo(
            tmp_path,
            agents=["negated-agent", "code-reviewer"],
            subagent_dispatches=["code-reviewer"],
            breakdown_table_rows=[
                # The negation row: agent cell has NOT `negated-agent`
                "| Some files | owning stack implementer — NOT `negated-agent` by default |",
            ],
        )
        result = _mod.find_orphans(tmp_path)
        # negated-agent is mentioned but negated → not a dispatch → orphan
        self.assertIn("negated-agent", result["orphan_agents"])
        # negated-agent must NOT appear in unknown_assignments
        # (it IS in the roster; the negation just means it's not assigned here)
        self.assertNotIn("negated-agent", result["unknown_assignments"])

    def test_find_orphans_side_effect_free(self, tmp_path=None):
        """Calling find_orphans twice gives the same result (no state mutation)."""
        result1 = _mod.find_orphans(_REPO_ROOT)
        result2 = _mod.find_orphans(_REPO_ROOT)
        self.assertEqual(result1, result2)


# ---------------------------------------------------------------------------
# TestASTExtraction — unit tests for the AST helpers
# ---------------------------------------------------------------------------

class TestASTExtraction(unittest.TestCase):
    """Unit tests for _extract_from_assignment and _collect_from_py_file."""

    def test_list_literal_extracted(self):
        import ast as _ast
        src = '_AUDIT_AGENTS = ["alpha-reviewer", "beta-agent"]\n'
        tree = _ast.parse(src)
        result = _mod._extract_from_assignment(tree, "_AUDIT_AGENTS")
        self.assertEqual(sorted(result), ["alpha-reviewer", "beta-agent"])

    def test_list_literal_annotated_extracted(self):
        """AnnAssign form (``name: Type = value``) must be handled.

        The real _AUDIT_AGENTS in _audit/_preflight.py:21 is declared as
        ``_AUDIT_AGENTS: List[str] = [...]``, an annotated assignment.
        A parser that only walks ast.Assign silently misses it.
        """
        import ast as _ast
        src = 'from typing import List\n_AUDIT_AGENTS: List[str] = ["a-reviewer", "b-agent"]\n'
        tree = _ast.parse(src)
        result = _mod._extract_from_assignment(tree, "_AUDIT_AGENTS")
        self.assertEqual(sorted(result), ["a-reviewer", "b-agent"])

    def test_dict_keys_extracted(self):
        import ast as _ast
        src = '_FOCUS_BLOCKS = {"code-reviewer": "does things", "qa-reviewer": "tests"}\n'
        tree = _ast.parse(src)
        result = _mod._extract_from_assignment(tree, "_FOCUS_BLOCKS")
        self.assertEqual(sorted(result), ["code-reviewer", "qa-reviewer"])

    def test_unknown_identifier_returns_empty(self):
        import ast as _ast
        src = '_OTHER = ["x"]\n'
        tree = _ast.parse(src)
        result = _mod._extract_from_assignment(tree, "_NOT_PRESENT")
        self.assertEqual(result, [])

    def test_non_list_non_dict_returns_empty(self):
        import ast as _ast
        src = '_SOME_VAR = "just a string"\n'
        tree = _ast.parse(src)
        result = _mod._extract_from_assignment(tree, "_SOME_VAR")
        self.assertEqual(result, [])

    def test_collect_from_py_file_list(self, tmp_path=None):
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)
        py_file = tmp_path / "mock.py"
        py_file.write_text('_MY_LIST = ["agent-a", "agent-b"]\n', encoding="utf-8")
        result = _mod._collect_from_py_file(py_file, "_MY_LIST")
        self.assertEqual(result, {"agent-a", "agent-b"})

    def test_collect_from_py_file_dict(self, tmp_path=None):
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)
        py_file = tmp_path / "mock.py"
        py_file.write_text('_MY_DICT = {"agent-x": 1, "agent-y": 2}\n', encoding="utf-8")
        result = _mod._collect_from_py_file(py_file, "_MY_DICT")
        self.assertEqual(result, {"agent-x", "agent-y"})

    def test_collect_from_py_file_missing(self, tmp_path=None):
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)
        result = _mod._collect_from_py_file(tmp_path / "nonexistent.py", "_FOO")
        self.assertEqual(result, set())

    def test_collect_from_py_file_syntax_error(self, tmp_path=None):
        import tempfile
        if tmp_path is None:
            td = tempfile.mkdtemp()
            tmp_path = Path(td)
        py_file = tmp_path / "bad.py"
        py_file.write_text("def (broken syntax:\n", encoding="utf-8")
        result = _mod._collect_from_py_file(py_file, "_FOO")
        self.assertEqual(result, set())


if __name__ == "__main__":
    unittest.main()
