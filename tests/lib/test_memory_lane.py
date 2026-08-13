"""tests/lib/test_memory_lane.py

Tests for scripts/lib/memory_lane.py.

Structure
---------
TestLiveSrc                — the PERMANENT GATE: runs find_gaps against the
                              real src/ tree. CURRENTLY EXPECTED TO FAIL —
                              the memory-lane wire-in this checker verifies
                              has not landed yet (see
                              74-MEMORY-LANE-INTEGRITY-PLAN.md). Once a
                              future session lands the wire-in, this test
                              starts passing with no test-code change.
TestDispositionTableSanity — the DISPOSITIONS constant itself: every entry
                              has a valid disposition + non-empty reason,
                              and the 13/7 split matches the ratified table.
TestNoDisposition          — synthetic fixture: a _PROMOTED command with no
                              entry in DISPOSITIONS → FAIL (Rule 1a).
TestReadsNoRead            — synthetic fixture: a READS command performing
                              no memory read at all → FAIL both halves of
                              Rule 2.
TestMechanism3Regression   — MANDATORY: a READS command whose ONLY memory
                              touchpoint is a helper preflight (read
                              performed, nobody names the field) → FAILS
                              Rule 2b but NOT Rule 2a. This is precisely
                              the case a disjunctive Rule 2 would wrongly
                              pass; it pins the conjunctive design.
TestPositiveControl        — synthetic fixture: a READS command with both
                              halves satisfied → PASS (no false positive).
TestNAHelperReads          — synthetic fixture: an N/A command whose
                              helper package carries a memory token → FAIL
                              (Rule 3).
TestNAClean                — synthetic fixture: an N/A command with no
                              memory touchpoint at all → PASS.
TestDeadPathLiteral         — synthetic fixture: a planted '.claude/memory'
                              literal under src/ → FAIL (Rule 4).
TestPromotedExtraction     — unit tests for _extract_promoted's AST parse.
TestCLI                     — the CLI's mechanics (exit codes on synthetic
                              fixtures; does not hardcode a live-tree exit
                              code since the true current value is a FAIL —
                              see TestLiveSrc for the real enforcement).
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
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

import memory_lane as _mod  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers for synthetic fixtures
# ---------------------------------------------------------------------------

def _write(path, text):
    # type: (Path, str) -> None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")


def _make_repo(tmp_path, promoted, commands=None, extra_src_files=None):
    # type: (Path, list, dict, dict) -> Path
    """Build a minimal synthetic repo under tmp_path for memory_lane tests.

    Parameters
    ----------
    promoted : list of str
        The `_PROMOTED` tuple contents written into a synthetic
        scripts/emitters/claude.py.
    commands : dict, optional
        Per-command overrides, keyed by command name::

            {
              "cmd-name": {
                "main_md": "<content for src/commands/cmd-name/main.md>",
                "references": {"<file>.md": "<content>"},
                "helper_pkg": {"<relpath>.py": "<content>"},  # under
                    # src/devforge/lib/_<cmd_u>/<relpath>.py
                "launcher": "<content for <cmd_u>_helper.py>",
              },
              ...
            }
    extra_src_files : dict, optional
        Arbitrary extra files under src/, keyed by path relative to src/
        (used by the dead-path-literal fixture).
    """
    repo = tmp_path
    _write(
        repo / "scripts" / "emitters" / "claude.py",
        "_PROMOTED = {!r}\n".format(tuple(promoted)),
    )
    # Ensure src/ exists even for a promoted-only fixture (e.g. the
    # no-disposition case) — the CLI's own precondition check requires
    # src/ to be a directory before it will even call find_gaps().
    (repo / "src").mkdir(parents=True, exist_ok=True)

    for cmd, spec in (commands or {}).items():
        cmd_u = cmd.replace("-", "_")
        if "main_md" in spec:
            _write(repo / "src" / "commands" / cmd / "main.md", spec["main_md"])
        for ref_name, ref_text in spec.get("references", {}).items():
            _write(
                repo / "src" / "commands" / cmd / "references" / ref_name,
                ref_text,
            )
        for rel, text in spec.get("helper_pkg", {}).items():
            _write(
                repo / "src" / "devforge" / "lib" / ("_" + cmd_u) / rel,
                text,
            )
        if "launcher" in spec:
            _write(
                repo / "src" / "devforge" / "lib" / (cmd_u + "_helper.py"),
                spec["launcher"],
            )

    for rel, text in (extra_src_files or {}).items():
        _write(repo / "src" / rel, text)

    return repo


# ---------------------------------------------------------------------------
# TestLiveSrc — the PERMANENT GATE
# ---------------------------------------------------------------------------

class TestLiveSrc(unittest.TestCase):
    """Live-src check: every READS command reads memory AND names the field;
    every N/A command carries none of the tokens; no dead path literal.

    This test IS the permanent enforcement gate (the repo has no CI, no
    Makefile, and no pytest config — this pytest test is the only
    automated place this invariant is checked).

    CURRENTLY EXPECTED TO FAIL. The wire-in this checker verifies (memory
    reads performed AND consumed for every READS command) has not landed
    for most of the 13 READS commands yet — see
    74-MEMORY-LANE-INTEGRITY-PLAN.md and the accompanying report. Do NOT
    "fix" this test by loosening a rule; fix it by doing the wire-in.
    """

    def test_no_gaps_in_live_src(self):
        result = _mod.find_gaps(_REPO_ROOT)

        msg_parts = []
        labels = (
            ("no_disposition", "Commands with no disposition (Rule 1a)"),
            ("empty_reason", "Commands with an empty reason (Rule 1b)"),
            ("reads_missing_helper_read", "READS commands with no memory read performed (Rule 2a)"),
            ("reads_missing_consumption", "READS commands with no consuming surface naming the field (Rule 2b)"),
            ("na_leaks_memory", "N/A commands carrying a memory token (Rule 3)"),
            ("dead_path_literal", "Dead '.claude/memory' literal occurrences (Rule 4)"),
        )
        for key, label in labels:
            if result[key]:
                msg_parts.append("{}: {}".format(label, result[key]))

        if msg_parts:
            self.fail(
                "memory_lane check found violations (this documents the "
                "wire-in worklist — see 74-MEMORY-LANE-INTEGRITY-PLAN.md; "
                "do not fix by editing src/commands/** as part of building "
                "this checker):\n" + "\n".join(msg_parts)
            )

    def test_result_shape(self):
        """find_gaps always returns a dict with the six expected keys."""
        result = _mod.find_gaps(_REPO_ROOT)
        for key in (
            "no_disposition", "empty_reason", "reads_missing_helper_read",
            "reads_missing_consumption", "na_leaks_memory", "dead_path_literal",
        ):
            self.assertIn(key, result)
            self.assertIsInstance(result[key], list)

    def test_find_gaps_side_effect_free(self):
        """Calling find_gaps twice gives the same result (no state mutation)."""
        result1 = _mod.find_gaps(_REPO_ROOT)
        result2 = _mod.find_gaps(_REPO_ROOT)
        self.assertEqual(result1, result2)


# ---------------------------------------------------------------------------
# TestDispositionTableSanity — the DISPOSITIONS constant itself
# ---------------------------------------------------------------------------

class TestDispositionTableSanity(unittest.TestCase):
    """DISPOSITIONS is a hardcoded module constant — sanity-check its shape."""

    def test_every_entry_has_valid_disposition_and_nonempty_reason(self):
        for cmd, (disposition, reason) in _mod.DISPOSITIONS.items():
            self.assertIn(
                disposition, (_mod.READS, _mod.NOT_APPLICABLE),
                msg="{} has an unrecognized disposition {!r}".format(cmd, disposition),
            )
            self.assertTrue(
                reason and reason.strip(),
                msg="{} has an empty reason".format(cmd),
            )

    def test_reads_and_na_counts_match_the_ratified_split(self):
        reads = [c for c, (d, _r) in _mod.DISPOSITIONS.items() if d == _mod.READS]
        na = [c for c, (d, _r) in _mod.DISPOSITIONS.items() if d == _mod.NOT_APPLICABLE]
        self.assertEqual(len(_mod.DISPOSITIONS), 20)
        self.assertEqual(sorted(reads), sorted([
            "research", "discover", "specify", "plan", "breakdown",
            "implement", "pr-review", "audit", "review", "verify",
            "grill", "finalize", "fix",
        ]))
        self.assertEqual(sorted(na), sorted([
            "init-forge", "generate-docs", "configure", "constitute",
            "spec-check", "summarize", "report-bug",
        ]))

    def test_reads_and_na_are_different_sets_from_the_invocability_split(self):
        """Pins the 'false inference to pre-empt' documented in the module.

        summarize/report-bug are model-invocable yet N/A; grill/fix are
        human-typed-only yet READS. The 13/7 counts coincide with the
        model-invocable split but the SETS differ — this test proves it.
        """
        reads = {c for c, (d, _r) in _mod.DISPOSITIONS.items() if d == _mod.READS}
        self.assertIn("summarize", _mod.DISPOSITIONS)
        self.assertNotIn("summarize", reads)
        self.assertIn("report-bug", _mod.DISPOSITIONS)
        self.assertNotIn("report-bug", reads)
        self.assertIn("grill", reads)
        self.assertIn("fix", reads)


# ---------------------------------------------------------------------------
# TestNoDisposition — Rule 1a
# ---------------------------------------------------------------------------

class TestNoDisposition(unittest.TestCase):
    """A _PROMOTED command with no entry in DISPOSITIONS → FAIL, naming it."""

    def test_unclassified_command_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_repo(tmp_path, promoted=["widget-launcher"])
            result = _mod.find_gaps(tmp_path)
            self.assertIn("widget-launcher", result["no_disposition"])

    def test_classified_command_not_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_repo(
                tmp_path,
                promoted=["report-bug"],
                commands={"report-bug": {"main_md": "# /devforge:report-bug\n"}},
            )
            result = _mod.find_gaps(tmp_path)
            self.assertEqual(result["no_disposition"], [])


# ---------------------------------------------------------------------------
# TestReadsNoRead — Rule 2 (both halves), zero touchpoint
# ---------------------------------------------------------------------------

class TestReadsNoRead(unittest.TestCase):
    """A READS command performing no read at all → FAIL both halves of Rule 2."""

    def test_reads_command_with_no_touchpoint_fails_both(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_repo(
                tmp_path,
                promoted=["grill"],
                commands={
                    "grill": {
                        "main_md": "# /devforge:grill\n\nNo memory mention at all.\n",
                    },
                },
            )
            result = _mod.find_gaps(tmp_path)
            self.assertIn("grill", result["reads_missing_helper_read"])
            self.assertIn("grill", result["reads_missing_consumption"])


# ---------------------------------------------------------------------------
# TestMechanism3Regression — the MANDATORY conjunctive-rule pin
# ---------------------------------------------------------------------------

class TestMechanism3Regression(unittest.TestCase):
    """The ONE test a disjunctive Rule 2 would wrongly pass.

    A READS command whose ONLY memory touchpoint is a helper preflight —
    the read is performed (2a satisfied), but no main.md/references file
    names the field it produced (2b fails). Rule 2 is CONJUNCTIVE: this
    MUST still be reported as a failure overall (via
    reads_missing_consumption), even though the read-performed half is
    genuinely satisfied. Without this test, Rule 2 could later be loosened
    to an OR and the suite would stay green.
    """

    def test_preflight_only_touchpoint_fails_consumption_not_read(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_repo(
                tmp_path,
                promoted=["verify"],
                commands={
                    "verify": {
                        "main_md": (
                            "# /devforge:verify\n\n"
                            "Persist high-level lessons to `.devforge/memory.md` "
                            "when the feature is approved.\n"
                        ),
                        "helper_pkg": {
                            "_preflight.py": (
                                "from _shared.memory import read_memory_context\n"
                                "mem_ctx = read_memory_context(workspace_root)\n"
                                'result["memory_present"] = mem_ctx["present"]\n'
                                'result["memory_excerpt"] = mem_ctx["excerpt"]\n'
                            ),
                        },
                    },
                },
            )
            result = _mod.find_gaps(tmp_path)
            self.assertIn(
                "verify", result["reads_missing_consumption"],
                msg="preflight-builds-it/nobody-consumes-it must still FAIL",
            )
            self.assertNotIn(
                "verify", result["reads_missing_helper_read"],
                msg="the read itself genuinely IS performed — 2a must PASS",
            )


# ---------------------------------------------------------------------------
# TestPositiveControl — no false positive when both halves hold
# ---------------------------------------------------------------------------

class TestPositiveControl(unittest.TestCase):
    """A READS command with a real read AND a naming consumer → PASS."""

    def test_reads_command_with_read_and_naming_passes(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_repo(
                tmp_path,
                promoted=["research"],
                commands={
                    "research": {
                        "main_md": (
                            "Capture `memory_state` from stdout; the object "
                            "also carries `memory_excerpt`.\n"
                        ),
                        "helper_pkg": {
                            "_cmds_basic.py": (
                                "from _shared.memory import read_memory_context\n"
                                "mem_ctx = read_memory_context(str(install_root))\n"
                            ),
                        },
                    },
                },
            )
            result = _mod.find_gaps(tmp_path)
            self.assertNotIn("research", result["reads_missing_helper_read"])
            self.assertNotIn("research", result["reads_missing_consumption"])

    def test_reads_via_launcher_file_not_only_package_dir(self):
        """A read performed in the single-file launcher (no package dir) also counts."""
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_repo(
                tmp_path,
                promoted=["plan"],
                commands={
                    "plan": {
                        "main_md": "Reads `memory_digest` from the launcher's preflight.\n",
                        "launcher": (
                            "from _shared.memory import read_memory_digest\n"
                            "memory_digest = read_memory_digest(root)\n"
                        ),
                    },
                },
            )
            result = _mod.find_gaps(tmp_path)
            self.assertNotIn("plan", result["reads_missing_helper_read"])
            self.assertNotIn("plan", result["reads_missing_consumption"])


# ---------------------------------------------------------------------------
# TestNAHelperReads — Rule 3
# ---------------------------------------------------------------------------

class TestNAHelperReads(unittest.TestCase):
    """An N/A command whose helper package reads memory → FAIL (Rule 3)."""

    def test_na_command_with_helper_read_fails(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_repo(
                tmp_path,
                promoted=["summarize"],
                commands={
                    "summarize": {
                        "main_md": "# /devforge:summarize\n",
                        "helper_pkg": {
                            "_preflight.py": (
                                "from _shared.memory import read_memory_context\n"
                                "mem_ctx = read_memory_context(workspace_root)\n"
                                'result["memory_present"] = mem_ctx["present"]\n'
                                'result["memory_excerpt"] = mem_ctx["excerpt"]\n'
                            ),
                        },
                    },
                },
            )
            result = _mod.find_gaps(tmp_path)
            self.assertIn("summarize", result["na_leaks_memory"])

    def test_na_command_with_token_in_main_md_also_fails(self):
        """Rule 3 scans the command's surfaces too, not just its helper."""
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_repo(
                tmp_path,
                promoted=["spec-check"],
                commands={
                    "spec-check": {
                        "main_md": "Somehow this mentions `memory_digest` in prose.\n",
                    },
                },
            )
            result = _mod.find_gaps(tmp_path)
            self.assertIn("spec-check", result["na_leaks_memory"])


class TestNAClean(unittest.TestCase):
    """An N/A command with no memory touchpoint at all → PASS."""

    def test_na_command_with_no_memory_touch_passes(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_repo(
                tmp_path,
                promoted=["report-bug"],
                commands={"report-bug": {"main_md": "# /devforge:report-bug\n"}},
            )
            result = _mod.find_gaps(tmp_path)
            self.assertNotIn("report-bug", result["na_leaks_memory"])


# ---------------------------------------------------------------------------
# TestDeadPathLiteral — Rule 4
# ---------------------------------------------------------------------------

class TestDeadPathLiteral(unittest.TestCase):
    """A planted '.claude/memory' literal under src/ → FAIL (Rule 4)."""

    def test_planted_literal_flagged(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_repo(
                tmp_path,
                promoted=[],
                extra_src_files={
                    "commands/foo/main.md": (
                        "Read `.claude/memory/MEMORY.md` for lessons.\n"
                    ),
                },
            )
            result = _mod.find_gaps(tmp_path)
            hits = result["dead_path_literal"]
            self.assertTrue(
                any("commands/foo/main.md" in h and h.endswith(":1") for h in hits),
                msg="expected a commands/foo/main.md:1 hit, got {}".format(hits),
            )

    def test_no_literal_no_hits(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_repo(
                tmp_path,
                promoted=[],
                extra_src_files={"commands/foo/main.md": "Read `.devforge/memory.md`.\n"},
            )
            result = _mod.find_gaps(tmp_path)
            self.assertEqual(result["dead_path_literal"], [])

    def test_pycache_and_binary_extensions_skipped(self):
        """A .pyc under __pycache__/ carrying the literal must not be reported."""
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_repo(
                tmp_path,
                promoted=[],
                extra_src_files={
                    "devforge/lib/__pycache__/mod.pyc": ".claude/memory garbage bytes",
                },
            )
            result = _mod.find_gaps(tmp_path)
            self.assertEqual(result["dead_path_literal"], [])


# ---------------------------------------------------------------------------
# TestPromotedExtraction — unit tests for _extract_promoted
# ---------------------------------------------------------------------------

class TestPromotedExtraction(unittest.TestCase):

    def test_extracts_tuple_literal(self, tmp_path=None):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _write(
                tmp_path / "scripts" / "emitters" / "claude.py",
                '_PROMOTED = ("alpha", "beta")\n',
            )
            result = _mod._extract_promoted(tmp_path)
            self.assertEqual(result, ("alpha", "beta"))

    def test_missing_file_returns_empty_tuple(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            result = _mod._extract_promoted(tmp_path)
            self.assertEqual(result, ())

    def test_syntax_error_returns_empty_tuple(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _write(
                tmp_path / "scripts" / "emitters" / "claude.py",
                "def (broken syntax:\n",
            )
            result = _mod._extract_promoted(tmp_path)
            self.assertEqual(result, ())

    def test_live_repo_matches_the_20_known_names(self):
        result = _mod._extract_promoted(_REPO_ROOT)
        self.assertEqual(len(result), 20)
        self.assertEqual(set(result), set(_mod.DISPOSITIONS.keys()))


# ---------------------------------------------------------------------------
# TestCLI — CLI mechanics (no hardcoded live-tree exit code)
# ---------------------------------------------------------------------------

class TestCLI(unittest.TestCase):
    """The CLI's mechanics.

    Does NOT hardcode the live-tree exit code — the true current value is
    a FAIL (see TestLiveSrc, which IS the enforcement gate and needs no
    update once the wire-in lands). This class only proves the CLI runs,
    reports correctly, and produces the right exit code on synthetic
    fixtures where the expected outcome is under this test's own control.
    """

    def _run_cli(self, *args):
        # type: (*str) -> subprocess.CompletedProcess
        cli = _REPO_ROOT / "scripts" / "verify-memory-lane.py"
        cmd = [sys.executable, str(cli)] + list(args)
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_cli_runs_on_live_tree_without_crashing(self):
        proc = self._run_cli(str(_REPO_ROOT))
        self.assertIn(
            proc.returncode, (0, 1),
            msg="stdout: {}\nstderr: {}".format(proc.stdout, proc.stderr),
        )
        self.assertIn("Memory-lane coverage check", proc.stdout)

    def test_cli_scope_disclaimer_in_output(self):
        proc = self._run_cli(str(_REPO_ROOT))
        self.assertIn("Does NOT verify", proc.stdout)
        self.assertIn("CONJUNCTIVE", proc.stdout)

    def test_cli_missing_src_exits_2(self):
        with tempfile.TemporaryDirectory() as td:
            proc = self._run_cli(td)
            self.assertEqual(proc.returncode, 2)

    def test_cli_missing_emitter_exits_2(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            (tmp_path / "src").mkdir()
            proc = self._run_cli(str(tmp_path))
            self.assertEqual(proc.returncode, 2)

    def test_cli_clean_fixture_exits_zero(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_repo(
                tmp_path,
                promoted=["report-bug"],
                commands={"report-bug": {"main_md": "# /devforge:report-bug\n"}},
            )
            proc = self._run_cli(str(tmp_path))
            self.assertEqual(
                proc.returncode, 0,
                msg="stdout: {}\nstderr: {}".format(proc.stdout, proc.stderr),
            )

    def test_cli_violation_fixture_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            tmp_path = Path(td)
            _make_repo(tmp_path, promoted=["widget-launcher"])
            proc = self._run_cli(str(tmp_path))
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("widget-launcher", proc.stdout)


if __name__ == "__main__":
    unittest.main()
