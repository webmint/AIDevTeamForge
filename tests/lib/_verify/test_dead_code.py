"""Tests for src/devforge/lib/_verify/_dead_code.py, the check-dead-code-removal
CLI verb, and the _verdict.py dead-code fold (plan 71 Phase 4).

Real-file discipline:
  All per-row tests write real temporary files and call
  check_dead_code_removal against them — no mocked content.

Coverage:
  check_dead_code_removal (function level):
    - anchor_token removed from an existing file → pass
    - anchor_token still present in an existing file → violation (guard-and-leave)
    - declared file absent (whole file deleted) → pass
    - empty dead_code_rows list → vacuous
    - None dead_code_rows → vacuous
    - multiple rows, mixed pass/violation → per-row results + correct counts
    - row with empty anchor_token → pass, not a false "" in text match
    - row with empty file → pass
    - relative vs absolute file path resolution against source_root
    - output shape: all required keys present, per-row keys present

  check-dead-code-removal CLI verb:
    - valid breakdown-handoff.json with dead_code_rows, token removed → status clean
    - valid breakdown-handoff.json with dead_code_rows, token present → status violation
    - breakdown-handoff.json with no dead_code_rows key → legit vacuous,
      handoff_read_error=False, no stderr
    - --breakdown-handoff none (literal) → legit vacuous, handoff_read_error=False,
      no stderr
    - missing --breakdown-handoff path, malformed JSON, dead_code_rows present
      but wrong type, or handoff top-level not a JSON object → READ-ERROR
      vacuous: status stays "vacuous" and exit is still 0 (non-fatal), but
      handoff_read_error=True + a stderr WARN — distinguished from the legit
      no-rows-declared case because this is a MUST-lane blocking gate, not an
      advisory check
    - the read-error note text differs from the legit-vacuous note text
    - clean/violation results always carry handoff_read_error=False
    - missing --breakdown-handoff flag → exit 2

  _verdict.py dead-code fold:
    - dead_code={"violation": True} → NEEDS WORK with blocker type "dead_code_unremoved"
    - dead_code={"violation": True} → NEVER REJECTED
    - dead_code={"violation": False} → no effect, APPROVED on clean inputs
    - dead_code=None (default) / omitted kwarg → APPROVED, backward-compatible
    - dead_code violation + confirmed constitution violation → REJECTED (constitution wins)
    - dead_code violation + mechanical failure → NEEDS WORK, both blockers present
    - reasons mention "dead code" / "guard-and-leave"
    - vacuous dead_code (status="vacuous", violation=False) → no blocker
    - plan-34 regression stance intact: hygiene-only flags stay APPROVED even
      alongside a clean (non-violating) dead_code result

  compute-verdict CLI --dead-code sentinel guard:
    - --dead-code pointing at malformed JSON → clean exit 2 (no traceback,
      no AttributeError from dead_code.get(...) on the "ERROR" sentinel string)
    - stderr names the --dead-code flag
    - valid --dead-code JSON still works
    - omitted --dead-code still works (backward-compatible)
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _verify._dead_code import check_dead_code_removal  # noqa: E402
from _verify._cli import main  # noqa: E402
from _verify._verdict import compute_verdict  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture(argv):
    """Run main(argv) with captured stdout/stderr.  Returns (stdout, stderr, rc)."""
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = buf_out, buf_err
    try:
        rc = main(argv)
    except SystemExit as exc:
        rc = exc.code if isinstance(exc.code, int) else 2
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return buf_out.getvalue(), buf_err.getvalue(), rc


def _write_tmp(tmp_dir, filename, content):
    # type: (str, str, str) -> str
    path = os.path.join(tmp_dir, filename)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


def _row(file, anchor_token="primaryShipToCity", kind="arm", why_dead="superseded"):
    return {
        "file": file,
        "anchor_token": anchor_token,
        "kind": kind,
        "why_dead": why_dead,
    }


# ---------------------------------------------------------------------------
# Tests — check_dead_code_removal (function level)
# ---------------------------------------------------------------------------


class TestCheckDeadCodeRemovalFunction(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_token_removed_is_pass(self):
        """anchor_token no longer present in the file → row status pass."""
        f = _write_tmp(self.tmp_dir, "clean.js", "buildFilters(query)\n")
        rows = [_row(f)]
        result = check_dead_code_removal(rows, self.tmp_dir)
        self.assertEqual(result["status"], "clean")
        self.assertFalse(result["violation"])
        self.assertEqual(result["rows"][0]["status"], "pass")

    def test_token_present_is_violation(self):
        """anchor_token still present in the file → guard-and-leave violation."""
        f = _write_tmp(
            self.tmp_dir, "dirty.js",
            "if (x) { return 'primaryShipToCity'; }\n",
        )
        rows = [_row(f)]
        result = check_dead_code_removal(rows, self.tmp_dir)
        self.assertEqual(result["status"], "violation")
        self.assertTrue(result["violation"])
        self.assertEqual(result["rows"][0]["status"], "violation")

    def test_file_absent_is_pass(self):
        """Declared file deleted entirely → legitimate removal, pass."""
        missing = os.path.join(self.tmp_dir, "gone.js")
        rows = [_row(missing)]
        result = check_dead_code_removal(rows, self.tmp_dir)
        self.assertEqual(result["status"], "clean")
        self.assertEqual(result["rows"][0]["status"], "pass")

    def test_empty_rows_list_is_vacuous(self):
        result = check_dead_code_removal([], self.tmp_dir)
        self.assertEqual(result["status"], "vacuous")
        self.assertFalse(result["violation"])
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["total_count"], 0)

    def test_none_rows_is_vacuous(self):
        result = check_dead_code_removal(None, self.tmp_dir)
        self.assertEqual(result["status"], "vacuous")
        self.assertFalse(result["violation"])

    def test_vacuous_note_states_honest_bound(self):
        """The vacuous note names the D4 honest bound explicitly."""
        result = check_dead_code_removal(None, self.tmp_dir)
        self.assertIn("honest bound", result["note"])
        self.assertIn("undeclared", result["note"])

    def test_mixed_rows_pass_and_violation(self):
        """Multiple rows: one clean removal, one guard-and-leave → correct counts."""
        clean_f = _write_tmp(self.tmp_dir, "clean2.js", "ok()\n")
        dirty_f = _write_tmp(
            self.tmp_dir, "dirty2.js", "case 'primaryShipToState':\n"
        )
        rows = [
            _row(clean_f, anchor_token="primaryShipToCity"),
            _row(dirty_f, anchor_token="primaryShipToState"),
        ]
        result = check_dead_code_removal(rows, self.tmp_dir)
        self.assertEqual(result["status"], "violation")
        self.assertTrue(result["violation"])
        self.assertEqual(result["total_count"], 2)
        self.assertEqual(result["pass_count"], 1)
        self.assertEqual(result["violation_count"], 1)
        statuses = {r["file"]: r["status"] for r in result["rows"]}
        self.assertEqual(statuses[clean_f], "pass")
        self.assertEqual(statuses[dirty_f], "violation")

    def test_empty_anchor_token_is_pass_not_false_match(self):
        """An empty anchor_token must never trivially match ('' in text)."""
        f = _write_tmp(self.tmp_dir, "anything.js", "whatever content\n")
        rows = [_row(f, anchor_token="")]
        result = check_dead_code_removal(rows, self.tmp_dir)
        self.assertEqual(result["status"], "clean")
        self.assertEqual(result["rows"][0]["status"], "pass")

    def test_empty_file_path_is_pass(self):
        rows = [_row("")]
        result = check_dead_code_removal(rows, self.tmp_dir)
        self.assertEqual(result["status"], "clean")
        self.assertEqual(result["rows"][0]["status"], "pass")

    def test_relative_path_resolved_against_source_root(self):
        f = _write_tmp(self.tmp_dir, "relcheck.js", "still 'primaryShipToCity' here\n")
        rows = [_row("relcheck.js")]
        result = check_dead_code_removal(rows, self.tmp_dir)
        self.assertEqual(result["rows"][0]["status"], "violation")

    def test_absolute_path_resolved_directly(self):
        f = _write_tmp(self.tmp_dir, "abscheck.js", "clean now\n")
        rows = [_row(f)]  # f is already absolute
        result = check_dead_code_removal(rows, "/some/unrelated/root")
        self.assertEqual(result["rows"][0]["status"], "pass")

    def test_output_shape_has_all_required_keys(self):
        f = _write_tmp(self.tmp_dir, "shape.js", "x\n")
        result = check_dead_code_removal([_row(f)], self.tmp_dir)
        expected = {
            "status", "violation", "rows",
            "pass_count", "violation_count", "total_count", "note",
        }
        self.assertEqual(set(result.keys()), expected)
        row = result["rows"][0]
        row_expected = {"file", "anchor_token", "kind", "why_dead", "status", "note"}
        self.assertEqual(set(row.keys()), row_expected)

    def test_kind_and_why_dead_carried_through(self):
        f = _write_tmp(self.tmp_dir, "carry.js", "ok\n")
        rows = [_row(f, kind="branch", why_dead="dominating condition added upstream")]
        result = check_dead_code_removal(rows, self.tmp_dir)
        self.assertEqual(result["rows"][0]["kind"], "branch")
        self.assertEqual(
            result["rows"][0]["why_dead"], "dominating condition added upstream"
        )


# ---------------------------------------------------------------------------
# Tests — check-dead-code-removal CLI verb
# ---------------------------------------------------------------------------


class TestCheckDeadCodeRemovalCLI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp()

        # A file that still contains the declared dead-code anchor.
        cls.dirty_file = _write_tmp(
            cls.tmp_dir, "dirty.js", "case 'primaryShipToCity':\n"
        )
        # A file where the anchor has been removed.
        cls.clean_file = _write_tmp(cls.tmp_dir, "clean.js", "buildFilters(q)\n")

        cls.handoff_violation = os.path.join(cls.tmp_dir, "bh-violation.json")
        with open(cls.handoff_violation, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "schema_version": "1.0",
                    "handoff_kind": "breakdown",
                    "dead_code_rows": [_row(cls.dirty_file)],
                },
                fh,
            )

        cls.handoff_clean = os.path.join(cls.tmp_dir, "bh-clean.json")
        with open(cls.handoff_clean, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "schema_version": "1.0",
                    "handoff_kind": "breakdown",
                    "dead_code_rows": [_row(cls.clean_file)],
                },
                fh,
            )

        cls.handoff_no_key = os.path.join(cls.tmp_dir, "bh-no-key.json")
        with open(cls.handoff_no_key, "w", encoding="utf-8") as fh:
            json.dump({"schema_version": "1.0", "handoff_kind": "breakdown"}, fh)

        cls.handoff_malformed = os.path.join(cls.tmp_dir, "bh-malformed.json")
        with open(cls.handoff_malformed, "w", encoding="utf-8") as fh:
            fh.write("{not valid json")

        # dead_code_rows present but the wrong type (a string, not an array).
        cls.handoff_wrong_type = os.path.join(cls.tmp_dir, "bh-wrong-type.json")
        with open(cls.handoff_wrong_type, "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "schema_version": "1.0",
                    "handoff_kind": "breakdown",
                    "dead_code_rows": "not-a-list",
                },
                fh,
            )

        # A handoff file whose top level is not a JSON object at all.
        cls.handoff_not_object = os.path.join(cls.tmp_dir, "bh-not-object.json")
        with open(cls.handoff_not_object, "w", encoding="utf-8") as fh:
            json.dump(["unexpected", "array"], fh)

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def test_violation_case_exits_0_status_violation(self):
        out, _, rc = _capture([
            "check-dead-code-removal",
            "--breakdown-handoff", self.handoff_violation,
            "--source-root", self.tmp_dir,
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "violation")
        self.assertTrue(data["violation"])

    def test_clean_case_status_clean(self):
        out, _, rc = _capture([
            "check-dead-code-removal",
            "--breakdown-handoff", self.handoff_clean,
            "--source-root", self.tmp_dir,
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "clean")
        self.assertFalse(data["violation"])

    def test_no_dead_code_rows_key_is_vacuous(self):
        """Legit case: handoff reads fine, key just absent — no rows declared."""
        out, err, rc = _capture([
            "check-dead-code-removal",
            "--breakdown-handoff", self.handoff_no_key,
            "--source-root", self.tmp_dir,
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "vacuous")
        self.assertFalse(data["handoff_read_error"])
        self.assertEqual(err, "")

    def test_literal_none_is_vacuous(self):
        """--breakdown-handoff none: explicit skip — legit, no warning."""
        out, err, rc = _capture([
            "check-dead-code-removal",
            "--breakdown-handoff", "none",
            "--source-root", self.tmp_dir,
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "vacuous")
        self.assertFalse(data["handoff_read_error"])
        self.assertEqual(err, "")

    def test_missing_handoff_path_is_read_error_vacuous(self):
        """Nonexistent --breakdown-handoff path → vacuous but flagged as a
        read failure (handoff_read_error=True + stderr WARN) — distinct from
        the legit "nothing declared" case, since this is a MUST-lane
        blocking gate, not an advisory check like check-hygiene."""
        nonexistent = os.path.join(self.tmp_dir, "does-not-exist.json")
        out, err, rc = _capture([
            "check-dead-code-removal",
            "--breakdown-handoff", nonexistent,
            "--source-root", self.tmp_dir,
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "vacuous")
        self.assertTrue(data["handoff_read_error"])
        self.assertIn("WARN", err)
        self.assertIn("check-dead-code-removal:", err)

    def test_malformed_json_is_read_error_vacuous(self):
        out, err, rc = _capture([
            "check-dead-code-removal",
            "--breakdown-handoff", self.handoff_malformed,
            "--source-root", self.tmp_dir,
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "vacuous")
        self.assertTrue(data["handoff_read_error"])
        self.assertIn("WARN", err)

    def test_wrong_type_dead_code_rows_is_read_error_vacuous(self):
        """dead_code_rows present but not a JSON array → read-error vacuous,
        not the legit no-rows-declared case."""
        out, err, rc = _capture([
            "check-dead-code-removal",
            "--breakdown-handoff", self.handoff_wrong_type,
            "--source-root", self.tmp_dir,
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "vacuous")
        self.assertTrue(data["handoff_read_error"])
        self.assertIn("WARN", err)

    def test_handoff_not_a_json_object_is_read_error_vacuous(self):
        """Handoff whose top level parses but isn't a JSON object → read-error
        vacuous (no AttributeError from calling .get on a list)."""
        out, err, rc = _capture([
            "check-dead-code-removal",
            "--breakdown-handoff", self.handoff_not_object,
            "--source-root", self.tmp_dir,
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["status"], "vacuous")
        self.assertTrue(data["handoff_read_error"])
        self.assertIn("WARN", err)

    def test_read_error_note_distinguishes_from_legit_vacuous(self):
        """The note text on a read-error vacuous result differs from the
        legit no-rows-declared note text."""
        out_legit, _, _ = _capture([
            "check-dead-code-removal",
            "--breakdown-handoff", "none",
            "--source-root", self.tmp_dir,
        ])
        out_error, _, _ = _capture([
            "check-dead-code-removal",
            "--breakdown-handoff", self.handoff_malformed,
            "--source-root", self.tmp_dir,
        ])
        legit_note = json.loads(out_legit)["note"]
        error_note = json.loads(out_error)["note"]
        self.assertNotEqual(legit_note, error_note)
        self.assertIn("could not be read or parsed", error_note)

    def test_clean_result_has_handoff_read_error_false(self):
        out, _, _ = _capture([
            "check-dead-code-removal",
            "--breakdown-handoff", self.handoff_clean,
            "--source-root", self.tmp_dir,
        ])
        data = json.loads(out)
        self.assertFalse(data["handoff_read_error"])

    def test_violation_result_has_handoff_read_error_false(self):
        out, _, _ = _capture([
            "check-dead-code-removal",
            "--breakdown-handoff", self.handoff_violation,
            "--source-root", self.tmp_dir,
        ])
        data = json.loads(out)
        self.assertFalse(data["handoff_read_error"])

    def test_missing_breakdown_handoff_flag_exits_2(self):
        _, _, rc = _capture([
            "check-dead-code-removal",
            "--source-root", self.tmp_dir,
        ])
        self.assertNotEqual(rc, 0)

    def test_registered_in_help(self):
        from _verify._cli import build_parser
        parser = build_parser()
        help_text = parser.format_help()
        self.assertIn("check-dead-code-removal", help_text)


# ---------------------------------------------------------------------------
# Tests: _verdict.py dead-code fold
# ---------------------------------------------------------------------------


class TestVerdictDeadCodeFold(unittest.TestCase):
    """compute_verdict: dead_code parameter folds into NEEDS WORK (OQ-2(a))."""

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

    def test_dead_code_violation_forces_needs_work(self):
        inputs = self._clean_inputs()
        dead_code = {"status": "violation", "violation": True}
        result = compute_verdict(**inputs, dead_code=dead_code)

        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("dead_code_unremoved", blocker_types)

    def test_dead_code_violation_never_rejected(self):
        inputs = self._clean_inputs()
        dead_code = {"status": "violation", "violation": True}
        result = compute_verdict(**inputs, dead_code=dead_code)

        self.assertNotEqual(result["verdict"], "REJECTED")

    def test_dead_code_clean_no_effect(self):
        inputs = self._clean_inputs()
        dead_code = {"status": "clean", "violation": False}
        result = compute_verdict(**inputs, dead_code=dead_code)

        self.assertEqual(result["verdict"], "APPROVED")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertNotIn("dead_code_unremoved", blocker_types)

    def test_dead_code_vacuous_no_effect(self):
        inputs = self._clean_inputs()
        dead_code = {"status": "vacuous", "violation": False}
        result = compute_verdict(**inputs, dead_code=dead_code)

        self.assertEqual(result["verdict"], "APPROVED")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertNotIn("dead_code_unremoved", blocker_types)

    def test_dead_code_none_backward_compat(self):
        inputs = self._clean_inputs()
        result = compute_verdict(**inputs, dead_code=None)
        self.assertEqual(result["verdict"], "APPROVED")

    def test_dead_code_omitted_backward_compat(self):
        inputs = self._clean_inputs()
        result = compute_verdict(**inputs)  # no dead_code kwarg
        self.assertEqual(result["verdict"], "APPROVED")

    def test_dead_code_violation_with_constitution_violation_is_rejected(self):
        inputs = self._clean_inputs()
        inputs["review_findings"]["confirmed"] = [
            {
                "pattern": "hard-coded key",
                "file": "src/main.py",
                "severity": "Critical",
                "tags": ["[CONSTITUTION-VIOLATION]"],
                "category": "constitution",
            }
        ]
        dead_code = {"status": "violation", "violation": True}
        result = compute_verdict(**inputs, dead_code=dead_code)

        self.assertEqual(result["verdict"], "REJECTED")

    def test_dead_code_violation_with_mechanical_failure_both_blockers(self):
        inputs = self._clean_inputs()
        inputs["mechanical_status"] = "failed"
        dead_code = {"status": "violation", "violation": True}
        result = compute_verdict(**inputs, dead_code=dead_code)

        self.assertEqual(result["verdict"], "NEEDS WORK")
        blocker_types = [b["type"] for b in result["blockers"]]
        self.assertIn("dead_code_unremoved", blocker_types)
        self.assertIn("mechanical_failed", blocker_types)

    def test_dead_code_reasons_mention_guard_and_leave(self):
        inputs = self._clean_inputs()
        dead_code = {"status": "violation", "violation": True}
        result = compute_verdict(**inputs, dead_code=dead_code)

        combined = " ".join(result["reasons"]).lower()
        self.assertIn("dead code", combined)

    def test_plan34_hygiene_advisory_stance_intact_alongside_clean_dead_code(self):
        """Plan-34 regression guard: hygiene-only flags stay APPROVED, even
        with a clean (non-violating) dead_code result present."""
        inputs = self._clean_inputs()
        inputs["hygiene"] = {
            "scope_creep": ["some/file.py"],
            "leftover_artifacts": [
                {"file": "some/file.py", "line": 1, "kind": "bare_todo", "snippet": "# TODO"}
            ],
            "scope_creep_checked": True,
            "files_checked": 1,
            "files_unreadable": [],
        }
        dead_code = {"status": "clean", "violation": False}
        result = compute_verdict(**inputs, dead_code=dead_code)

        self.assertEqual(result["verdict"], "APPROVED")


# ---------------------------------------------------------------------------
# Tests: compute-verdict CLI --dead-code malformed-JSON sentinel guard
# ---------------------------------------------------------------------------


class TestComputeVerdictDeadCodeSentinel(unittest.TestCase):
    """compute-verdict --dead-code pointing at malformed JSON must exit 2
    cleanly (not crash with AttributeError on dead_code.get(...)) — the
    same sentinel-check convention --ac-results already uses."""

    @classmethod
    def setUpClass(cls):
        cls.tmp_dir = tempfile.mkdtemp()

        cls.ac_results_path = os.path.join(cls.tmp_dir, "ac-results.json")
        with open(cls.ac_results_path, "w", encoding="utf-8") as fh:
            json.dump([], fh)

        cls.dead_code_malformed = os.path.join(cls.tmp_dir, "dead-code-malformed.json")
        with open(cls.dead_code_malformed, "w", encoding="utf-8") as fh:
            fh.write("{not valid json")

        cls.dead_code_valid = os.path.join(cls.tmp_dir, "dead-code-valid.json")
        with open(cls.dead_code_valid, "w", encoding="utf-8") as fh:
            json.dump({"status": "clean", "violation": False}, fh)

    @classmethod
    def tearDownClass(cls):
        import shutil
        shutil.rmtree(cls.tmp_dir, ignore_errors=True)

    def test_malformed_dead_code_json_exits_2_cleanly(self):
        """No traceback / no AttributeError — a clean exit 2."""
        out, err, rc = _capture([
            "compute-verdict",
            "--ac-results", self.ac_results_path,
            "--dead-code", self.dead_code_malformed,
        ])
        self.assertEqual(rc, 2)
        self.assertNotIn("Traceback", err)
        self.assertNotIn("AttributeError", err)

    def test_malformed_dead_code_json_stderr_names_flag(self):
        _, err, _ = _capture([
            "compute-verdict",
            "--ac-results", self.ac_results_path,
            "--dead-code", self.dead_code_malformed,
        ])
        self.assertIn("--dead-code", err)

    def test_valid_dead_code_json_still_works(self):
        """Sanity: the sentinel check doesn't break the valid-JSON path."""
        out, _, rc = _capture([
            "compute-verdict",
            "--ac-results", self.ac_results_path,
            "--dead-code", self.dead_code_valid,
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["verdict"], "APPROVED")

    def test_omitted_dead_code_still_works(self):
        """Sanity: omitting --dead-code entirely is unaffected (backward compat)."""
        out, _, rc = _capture([
            "compute-verdict",
            "--ac-results", self.ac_results_path,
        ])
        self.assertEqual(rc, 0)
        data = json.loads(out)
        self.assertEqual(data["verdict"], "APPROVED")


if __name__ == "__main__":
    unittest.main()
