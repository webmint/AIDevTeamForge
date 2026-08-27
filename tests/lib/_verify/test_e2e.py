"""Tests for src/devforge/lib/_verify/_e2e.py and its compute_verdict fold.

Coverage:
  _e2e.run_e2e_gate:
    - config present, E2E_COMMAND absent/blank → status:"off" (successfully
      parsed, key absent/blank — D8)
    - E2E_COMMAND is blank/whitespace → status:"off"
    - config file entirely MISSING → status:"inconclusive" (python-reviewer
      FIX 1 — a read/parse failure is distinguished from "off"; see
      _e2e.py's "Config key" docstring section for the missing-file-is-
      inconclusive reasoning)
    - config file present but corrupt JSON → status:"inconclusive", note
      names "not valid JSON" (FIX 1)
    - config file parses to a non-object top-level JSON value (e.g. a
      list) → status:"inconclusive" (FIX 1, the third read/parse-failure
      branch)
    - command exits 0 → status:"e2e-clean"
    - command exits non-zero (not 126/127) → status:"e2e-failing", output_tail present
    - command exits 0 but "e2e-clean" has no output_tail key
    - missing binary (shell exit 127) → status:"inconclusive"
    - a non-executable file as the command (shell exit 126) →
      status:"inconclusive" (FIX 5, mirrors the 127 case's shape)
    - a suite that itself legitimately exits 127 after printing real
      output → misread as "inconclusive", output_tail lost — the
      ACCEPTED heuristic false negative, PINNED by a regression test
      (FIX 2), not merely implied by the docstring
    - timeout (module timeout constant monkeypatched small) → status:"inconclusive",
      never "e2e-failing"
    - note field is ALWAYS present, on every status
    - the verb (run_e2e_gate) never raises — every path returns a dict
    - wrapper mode (PROJECT_ROOT set) → the command's cwd, and therefore
      its observable side effect, lands in source_root
      (install_root / PROJECT_ROOT), never workspace_root itself (FIX 3)

  _e2e verify_helper CLI verb (e2e-gate):
    - registered, appears in --help
    - always exits 0, including a deliberately broken command
    - stdout is valid JSON matching run_e2e_gate's contract

  compute_verdict e2e fold (_verdict.py):
    - e2e=None (omitted) → verdict unaffected, backward compatible
    - status "off" → no e2e line in reasons at all (D8: silent)
    - status "inconclusive"/"e2e-clean"/"e2e-failing" → one reasons line added,
      mentioning status and note
    - e2e NEVER adds a blocker, for any status
    - the verdict is IDENTICAL for off/inconclusive/e2e-clean/e2e-failing given
      the same other (clean) inputs — the single test that mechanically proves
      D3 fork (i) (advisory-only), not fork (ii)

Stdlib only.  Python 3.8+.  Real subprocess runs — no hand-authored mocks.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import _verify._e2e as e2e_mod  # noqa: E402
from _verify._e2e import run_e2e_gate  # noqa: E402
from _verify._verdict import compute_verdict  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_config(install_root, e2e_command=None):
    # type: (str, str) -> None
    """Write .devforge/project-config.json, optionally with E2E_COMMAND."""
    devforge = os.path.join(install_root, ".devforge")
    os.makedirs(devforge, exist_ok=True)
    data = {}
    if e2e_command is not None:
        data["E2E_COMMAND"] = e2e_command
    with open(os.path.join(devforge, "project-config.json"), "w", encoding="utf-8") as fh:
        json.dump(data, fh)


class _TmpWorkspace(unittest.TestCase):
    """Base class providing a throwaway workspace_root per test."""

    def setUp(self):
        # type: () -> None
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        # type: () -> None
        shutil.rmtree(self.tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Tests: off status
# ---------------------------------------------------------------------------


class TestOffStatus(_TmpWorkspace):
    """Config read cleanly, E2E_COMMAND absent/blank → status:"off" (D8)."""

    def test_config_present_but_no_e2e_command_key(self):
        """project-config.json exists but has no E2E_COMMAND key → off."""
        _write_config(self.tmpdir)  # no e2e_command kwarg → key omitted
        result = run_e2e_gate(self.tmpdir)
        self.assertEqual(result["status"], "off")
        self.assertIn("note", result)
        self.assertNotIn("output_tail", result)

    def test_e2e_command_empty_string(self):
        """E2E_COMMAND="" (the FIELD_DEFAULTS baseline) → off."""
        _write_config(self.tmpdir, e2e_command="")
        result = run_e2e_gate(self.tmpdir)
        self.assertEqual(result["status"], "off")

    def test_e2e_command_whitespace_only(self):
        """E2E_COMMAND="   " → off (stripped to empty)."""
        _write_config(self.tmpdir, e2e_command="   ")
        result = run_e2e_gate(self.tmpdir)
        self.assertEqual(result["status"], "off")


# ---------------------------------------------------------------------------
# Tests: read/parse-failure paths (python-reviewer FIX 1) — inconclusive,
# distinguished from "successfully parsed, key absent/blank" (off, above).
# ---------------------------------------------------------------------------


class TestConfigReadFailureIsInconclusive(_TmpWorkspace):
    """A config read or parse failure is "inconclusive", never "off".

    FIX 1's missing-file decision (argued and pinned here, not just in the
    module docstring): a MISSING project-config.json surfaces as
    "inconclusive", not "off". Reasoning: (1) _regression.py's own gate,
    given an entirely absent config file, resolves through to
    "inconclusive" too (its REGRESSION_GATE lookup defaults the mode to
    "full" on a missing key rather than treating the absence as "off" —
    "off" there requires an EXPLICIT "REGRESSION_GATE": "off" value), so
    this codebase already reserves "off" for an explicit or
    completed-configuration signal, never for an absent file. (2) By the
    time /devforge:verify PHASE 4.5 runs this gate, /devforge:configure
    has necessarily already run in the setup chain — so a wholly missing
    project-config.json at THIS call site is an install anomaly (configure
    skipped, or workspace_root misresolved), not the everyday "small
    project, no e2e infrastructure" case D8's silent "off" targets. D8's
    "off" prints nothing anywhere, which would hide exactly that anomaly
    instead of surfacing it as a diagnosable "inconclusive" note.
    """

    def test_missing_config_file_entirely_is_inconclusive(self):
        """No .devforge/project-config.json at all → inconclusive (FIX 1's
        decision — see class docstring for the argued reasoning), never
        "off"."""
        result = run_e2e_gate(self.tmpdir)
        self.assertEqual(result["status"], "inconclusive")
        self.assertIn("note", result)
        self.assertIn("missing or unreadable", result["note"])
        self.assertNotIn("output_tail", result)

    def test_missing_devforge_dir_entirely_is_inconclusive(self):
        """Not even a .devforge/ directory exists → inconclusive (same
        missing-file branch as above, via a different intermediate dir)."""
        result = run_e2e_gate(self.tmpdir)
        self.assertEqual(result["status"], "inconclusive")
        self.assertFalse(os.path.isdir(os.path.join(self.tmpdir, ".devforge")))

    def test_corrupt_json_is_inconclusive(self):
        """project-config.json exists but is not valid JSON → inconclusive,
        with the note naming the actual cause (not silently "off")."""
        devforge = os.path.join(self.tmpdir, ".devforge")
        os.makedirs(devforge, exist_ok=True)
        with open(os.path.join(devforge, "project-config.json"), "w") as fh:
            fh.write("{not valid json")
        result = run_e2e_gate(self.tmpdir)
        self.assertEqual(result["status"], "inconclusive")
        self.assertIn("not valid JSON", result["note"])
        self.assertNotIn("output_tail", result)

    def test_non_object_top_level_json_is_inconclusive(self):
        """project-config.json parses, but the top-level value is a JSON
        array (not an object) → inconclusive — a read/parse-shape failure,
        not a "successfully parsed, key absent" case."""
        devforge = os.path.join(self.tmpdir, ".devforge")
        os.makedirs(devforge, exist_ok=True)
        with open(os.path.join(devforge, "project-config.json"), "w") as fh:
            fh.write("[1, 2, 3]")
        result = run_e2e_gate(self.tmpdir)
        self.assertEqual(result["status"], "inconclusive")
        self.assertIn("did not parse to a JSON object", result["note"])


# ---------------------------------------------------------------------------
# Tests: real subprocess runs
# ---------------------------------------------------------------------------


class TestRealRuns(_TmpWorkspace):
    """Real subprocess round-trips with tiny Python one-liners as the suite."""

    def test_clean_run(self):
        """Command exits 0 → e2e-clean, no output_tail key."""
        _write_config(self.tmpdir, e2e_command="python3 -c \"import sys; sys.exit(0)\"")
        result = run_e2e_gate(self.tmpdir)
        self.assertEqual(result["status"], "e2e-clean")
        self.assertIn("note", result)
        self.assertNotIn("output_tail", result)

    def test_failing_run_has_tail(self):
        """Command exits non-zero (not 126/127) → e2e-failing with output_tail."""
        cmd = (
            "python3 -c \""
            "import sys; print('flow: checkout failed'); sys.exit(1)"
            "\""
        )
        _write_config(self.tmpdir, e2e_command=cmd)
        result = run_e2e_gate(self.tmpdir)
        self.assertEqual(result["status"], "e2e-failing")
        self.assertIn("note", result)
        self.assertIn("output_tail", result)
        self.assertIn("checkout failed", result["output_tail"])

    def test_missing_binary_is_inconclusive(self):
        """A shell command-not-found (exit 127) → inconclusive, NOT e2e-failing."""
        _write_config(
            self.tmpdir, e2e_command="totally_nonexistent_binary_xyz_12345"
        )
        result = run_e2e_gate(self.tmpdir)
        self.assertEqual(result["status"], "inconclusive")
        self.assertNotIn("output_tail", result)

    def test_non_executable_file_is_inconclusive(self):
        """A file that exists but lacks the executable bit → shell exit 126
        ("found but not executable") → inconclusive, mirroring the 127
        (command-not-found) test's shape (FIX 5)."""
        script_path = os.path.join(self.tmpdir, "not_executable.sh")
        with open(script_path, "w") as fh:
            fh.write("#!/bin/sh\necho hi\n")
        os.chmod(script_path, 0o644)  # no execute bit
        _write_config(self.tmpdir, e2e_command=script_path)
        result = run_e2e_gate(self.tmpdir)
        self.assertEqual(result["status"], "inconclusive")
        self.assertNotIn("output_tail", result)
        self.assertIn("note", result)

    def test_126_127_heuristic_pins_accepted_false_negative(self):
        """FIX 2: the module docstring's "Missing-binary detection" section
        documents an ACCEPTED false negative — a suite that legitimately
        exits 127 itself (e.g. it shells out to a child process and
        propagates that child's exit code verbatim) is indistinguishable
        from a genuinely missing binary and is misread as "inconclusive",
        losing its output_tail even though it printed real output before
        exiting. This test PINS that intentional misclassification so a
        future reader finds the bound recorded and enforced by a
        regression test, not merely implied by prose."""
        cmd = (
            "python3 -c \""
            "print('suite output the reader will never see'); "
            "import sys; sys.exit(127)"
            "\""
        )
        _write_config(self.tmpdir, e2e_command=cmd)
        result = run_e2e_gate(self.tmpdir)
        self.assertEqual(result["status"], "inconclusive")
        self.assertNotEqual(result["status"], "e2e-failing")
        self.assertNotIn("output_tail", result)
        self.assertIn("note", result)

    def test_timeout_is_inconclusive_never_failing(self):
        """A run that exceeds the (monkeypatched, shrunk) timeout → inconclusive."""
        _write_config(self.tmpdir, e2e_command="python3 -c \"import time; time.sleep(5)\"")
        with mock.patch.object(e2e_mod, "_E2E_TIMEOUT", 1):
            result = run_e2e_gate(self.tmpdir)
        self.assertEqual(result["status"], "inconclusive")
        self.assertNotEqual(result["status"], "e2e-failing")
        self.assertIn("timed out", result["note"])
        self.assertNotIn("output_tail", result)

    def test_note_always_present_across_statuses(self):
        """Every status this module can return carries a 'note' key."""
        cases = [
            (None, "off"),
            ("python3 -c \"import sys; sys.exit(0)\"", "e2e-clean"),
            ("python3 -c \"import sys; sys.exit(1)\"", "e2e-failing"),
            ("totally_nonexistent_binary_xyz_12345", "inconclusive"),
        ]
        for cmd, expected_status in cases:
            tmp = tempfile.mkdtemp()
            try:
                _write_config(tmp, e2e_command=cmd)
                result = run_e2e_gate(tmp)
                self.assertEqual(result["status"], expected_status)
                self.assertIn("note", result, "note missing for status={0}".format(
                    expected_status))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)

    def test_never_raises_on_bad_workspace_root(self):
        """A nonexistent workspace_root path does not raise (fail-soft) — and,
        per FIX 1, is a read/parse failure (unreadable config path) so it
        surfaces as "inconclusive", not "off"."""
        result = run_e2e_gate("/this/path/does/not/exist/at/all")
        self.assertEqual(result["status"], "inconclusive")
        self.assertIn("note", result)


# ---------------------------------------------------------------------------
# Tests: wrapper mode (python-reviewer FIX 3)
# ---------------------------------------------------------------------------


class TestWrapperMode(_TmpWorkspace):
    """PROJECT_ROOT in project-config.json → the command runs in source_root
    (install_root / PROJECT_ROOT), never in workspace_root itself. Does NOT
    touch _regression.py or its tests — that gate's symmetric gap is
    pre-existing and out of this plan's scope (recorded at orchestrator
    level, not repeated here)."""

    def test_wrapper_mode_runs_in_source_root(self):
        """The e2e command's cwd is source_root, proven by an observable
        side effect (a marker file) landing inside the nested PROJECT_ROOT
        directory and NOT in workspace_root."""
        nested = os.path.join(self.tmpdir, "nested-app")
        os.makedirs(nested, exist_ok=True)
        devforge = os.path.join(self.tmpdir, ".devforge")
        os.makedirs(devforge, exist_ok=True)
        marker_cmd = "python3 -c \"open('marker.txt', 'w').close()\""
        with open(os.path.join(devforge, "project-config.json"), "w", encoding="utf-8") as fh:
            json.dump(
                {"E2E_COMMAND": marker_cmd, "PROJECT_ROOT": "nested-app"}, fh
            )

        result = run_e2e_gate(self.tmpdir)

        self.assertEqual(result["status"], "e2e-clean")
        self.assertTrue(
            os.path.exists(os.path.join(nested, "marker.txt")),
            "marker must land inside source_root (nested-app/), "
            "not workspace_root",
        )
        self.assertFalse(
            os.path.exists(os.path.join(self.tmpdir, "marker.txt")),
            "marker must NOT land in workspace_root when PROJECT_ROOT "
            "designates wrapper mode",
        )


# ---------------------------------------------------------------------------
# Tests: CLI verb — always exits 0, valid JSON, help text
# ---------------------------------------------------------------------------


class TestCLIVerb(_TmpWorkspace):
    """e2e-gate verb is registered, always exits 0, emits valid JSON."""

    def test_e2e_gate_in_help(self):
        """verify_helper --help mentions e2e-gate."""
        from _verify._cli import build_parser
        parser = build_parser()
        help_text = parser.format_help()
        self.assertIn("e2e-gate", help_text)

    def test_exits_0_with_off_status(self):
        """Config present, no E2E_COMMAND key → exits 0, status off."""
        _write_config(self.tmpdir)  # writes {} — successfully parsed, key absent
        from _verify._cli import main
        import io
        captured = io.StringIO()
        with mock.patch("sys.stdout", captured):
            rc = main(["e2e-gate", "--workspace-root", self.tmpdir])
        self.assertEqual(rc, 0)
        out = json.loads(captured.getvalue())
        self.assertEqual(out["status"], "off")

    def test_exits_0_with_inconclusive_status_on_missing_config(self):
        """No project-config.json at all (FIX 1's decision) → exits 0,
        status inconclusive — via the CLI verb, not just the library call."""
        from _verify._cli import main
        import io
        captured = io.StringIO()
        with mock.patch("sys.stdout", captured):
            rc = main(["e2e-gate", "--workspace-root", self.tmpdir])
        self.assertEqual(rc, 0)
        out = json.loads(captured.getvalue())
        self.assertEqual(out["status"], "inconclusive")

    def test_exits_0_on_deliberately_broken_command(self):
        """A deliberately broken (non-zero-exit) command → verb still exits 0."""
        _write_config(
            self.tmpdir,
            e2e_command="python3 -c \"import sys; sys.exit(1)\"",
        )
        from _verify._cli import main
        import io
        captured = io.StringIO()
        with mock.patch("sys.stdout", captured):
            rc = main(["e2e-gate", "--workspace-root", self.tmpdir])
        self.assertEqual(rc, 0)
        out = json.loads(captured.getvalue())
        self.assertEqual(out["status"], "e2e-failing")

    def test_exits_0_on_missing_binary(self):
        """A missing-binary command → verb still exits 0, status inconclusive."""
        _write_config(self.tmpdir, e2e_command="totally_nonexistent_binary_xyz_12345")
        from _verify._cli import main
        import io
        captured = io.StringIO()
        with mock.patch("sys.stdout", captured):
            rc = main(["e2e-gate", "--workspace-root", self.tmpdir])
        self.assertEqual(rc, 0)
        out = json.loads(captured.getvalue())
        self.assertEqual(out["status"], "inconclusive")


# ---------------------------------------------------------------------------
# Tests: compute_verdict e2e fold
# ---------------------------------------------------------------------------


class TestVerdictE2EFold(unittest.TestCase):
    """compute_verdict: e2e parameter is reasons-only, NEVER a blocker (D3 fork i)."""

    def _clean_inputs(self):
        """Return clean inputs that would otherwise yield APPROVED."""
        return dict(
            ac_results=[],
            mechanical_status="pass",
            review_findings={
                "missing": False,
                "confirmed": [],
                "contested": [],
                "summary": {
                    "critical": 0, "high": 0, "medium": 0, "info": 0,
                    "confirmed_count": 0, "contested_count": 0,
                    "dismissed_count": 0, "uncertain_count": 0,
                },
            },
            hygiene={
                "scope_creep": [],
                "leftover_artifacts": [],
                "scope_creep_checked": False,
                "files_checked": 0,
                "files_unreadable": [],
            },
            ac_verification_mode="code-only",
        )

    def test_e2e_omitted_backward_compat(self):
        """Omitting e2e kwarg → APPROVED; signature is backward-compatible."""
        inputs = self._clean_inputs()
        result = compute_verdict(**inputs)  # no e2e kwarg
        self.assertEqual(result["verdict"], "APPROVED")

    def test_e2e_none_backward_compat(self):
        """e2e=None (default) → APPROVED, no e2e reason line."""
        inputs = self._clean_inputs()
        result = compute_verdict(**inputs, e2e=None)
        self.assertEqual(result["verdict"], "APPROVED")
        combined = " ".join(result["reasons"]).lower()
        self.assertNotIn("e2e", combined)

    def test_e2e_off_produces_no_reasons_line(self):
        """status:"off" → D8: completely silent, no e2e mention in reasons."""
        inputs = self._clean_inputs()
        e2e = {"status": "off", "note": "no E2E_COMMAND configured"}
        result = compute_verdict(**inputs, e2e=e2e)
        combined = " ".join(result["reasons"]).lower()
        self.assertNotIn("e2e", combined)
        self.assertEqual(result["verdict"], "APPROVED")

    def test_e2e_clean_adds_reasons_line(self):
        """status:"e2e-clean" → one reasons line mentioning status + note."""
        inputs = self._clean_inputs()
        e2e = {"status": "e2e-clean", "note": "e2e suite passed"}
        result = compute_verdict(**inputs, e2e=e2e)
        combined = " ".join(result["reasons"])
        self.assertIn("e2e-clean", combined)
        self.assertIn("e2e suite passed", combined)

    def test_e2e_inconclusive_adds_reasons_line(self):
        """status:"inconclusive" → one reasons line mentioning status + note."""
        inputs = self._clean_inputs()
        e2e = {"status": "inconclusive", "note": "e2e command timed out after 1800s"}
        result = compute_verdict(**inputs, e2e=e2e)
        combined = " ".join(result["reasons"])
        self.assertIn("inconclusive", combined)
        self.assertIn("timed out", combined)

    def test_e2e_failing_adds_reasons_line_but_no_blocker(self):
        """status:"e2e-failing" → reasons line present, NO blocker added (D3 fork i)."""
        inputs = self._clean_inputs()
        e2e = {
            "status": "e2e-failing",
            "note": "e2e suite reported failures (exit code 1)",
            "output_tail": "flow: checkout failed",
        }
        result = compute_verdict(**inputs, e2e=e2e)
        combined = " ".join(result["reasons"])
        self.assertIn("e2e-failing", combined)
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertNotIn("e2e", blocker_types)
        self.assertFalse(
            any("e2e" in str(b.get("type", "")) for b in result["blockers"]),
            "e2e must never appear as a blocker type (D3 fork i)",
        )

    def test_verdict_identical_across_all_four_statuses(self):
        """THE criterion: verdict is IDENTICAL for off/inconclusive/e2e-clean/
        e2e-failing given the same other (clean) inputs — proves D3 fork (i)
        (advisory-only) mechanically, distinguishing it from fork (ii)
        (an e2e-failing blocker)."""
        inputs = self._clean_inputs()
        statuses_and_notes = [
            {"status": "off", "note": "no E2E_COMMAND configured"},
            {"status": "inconclusive", "note": "e2e command timed out after 1800s"},
            {"status": "e2e-clean", "note": "e2e suite passed"},
            {
                "status": "e2e-failing",
                "note": "e2e suite reported failures (exit code 1)",
                "output_tail": "flow: checkout failed",
            },
        ]
        verdicts = set()
        for e2e in statuses_and_notes:
            result = compute_verdict(**inputs, e2e=e2e)
            verdicts.add(result["verdict"])

        self.assertEqual(
            verdicts,
            {"APPROVED"},
            "verdict must be identical (APPROVED) across all four e2e statuses "
            "given the same other clean inputs — a differing verdict means "
            "fork (ii) shipped instead of the ratified fork (i)",
        )

    def test_e2e_true_with_other_blocker_still_reasons_only(self):
        """e2e-failing + an unrelated mechanical failure → NEEDS WORK from the
        mechanical failure alone; e2e still contributes no blocker."""
        inputs = self._clean_inputs()
        inputs["mechanical_status"] = "failed"
        e2e = {"status": "e2e-failing", "note": "e2e suite reported failures"}
        result = compute_verdict(**inputs, e2e=e2e)

        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("mechanical_failed", blocker_types)
        self.assertNotIn("e2e", blocker_types)
        self.assertEqual(len(blocker_types), 1, "e2e must not add a second blocker")


if __name__ == "__main__":
    unittest.main()
