"""End-to-end replay test for PR #304 synthetic fixture (PR-REVIEW Step 11).

Runs all 11 helper verbs in pipeline order against the synthetic
DoosanICA/db-cse-ui-strata#304 fixture.  LLM-side phases (3.5 CBM
trace_path; 6.5 cavecrew dispatch) are SKIPPED — state.findings stays
empty and state.blast probes have filled=False.

Test gates only what the deterministic helper phases produce:
  - intake:                  state.json created with base fields
  - detect-smells:           4 required smells present
  - compute-blast-radius:    >= 3 probe specs
  - bundle-context:          does not crash; state.bundle populated
  - import-handoffs:         does not crash; returns ok
  - check-scope-drift:       >= 9 drift bullets; at least one ac_marker
  - dispatch-review:         brief.md created; contains PR#304 + AC-1 + smell names
  - finalize-output:         findings.md created; contains no-findings marker
  - append-to-replay-corpus: pr-review-bundle.json + _corpus_index.json created

Subprocess (gh) calls are mocked via unittest.mock.patch.
All other phases are invoked in-process via their module run() functions.
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Path bootstrap — lib directory must be on sys.path so that _pr_review.*
# imports work without package installation.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

# ---------------------------------------------------------------------------
# Fixture paths.
# ---------------------------------------------------------------------------

_FIXTURE_DIR = (
    Path(__file__).resolve().parent.parent.parent / "fixtures" / "pr_review_replay_corpus" / "304"
)


def _load_pr_view() -> dict:
    """Read pr_view.json fixture."""
    with open(str(_FIXTURE_DIR / "pr_view.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _load_pr_diff() -> str:
    """Read pr_diff.patch fixture."""
    with open(str(_FIXTURE_DIR / "pr_diff.patch"), "r", encoding="utf-8") as fh:
        return fh.read()


def _load_ticket() -> str:
    """Read ticket.txt fixture."""
    with open(str(_FIXTURE_DIR / "ticket.txt"), "r", encoding="utf-8") as fh:
        return fh.read()


def _load_expected() -> dict:
    """Read expected_outcomes.json fixture."""
    with open(str(_FIXTURE_DIR / "expected_outcomes.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Mock factory for subprocess.run (gh CLI calls).
# ---------------------------------------------------------------------------

def _mock_proc(stdout: str = "", returncode: int = 0, stderr: str = "") -> MagicMock:
    """Build a mock subprocess.CompletedProcess-like object."""
    m = MagicMock()
    m.stdout = stdout
    m.returncode = returncode
    m.stderr = stderr
    return m


def _make_gh_side_effect(pr_view_payload: dict, diff_text: str):
    """Return a side_effect for patching subprocess.run.

    First call → gh pr view (returns pr_view_payload as JSON).
    Second call → gh pr diff (returns diff_text).
    """
    view_json = json.dumps(pr_view_payload)
    calls = [0]

    def _side_effect(cmd, **kwargs):
        idx = calls[0]
        calls[0] += 1
        if idx == 0:
            return _mock_proc(stdout=view_json, returncode=0)
        return _mock_proc(stdout=diff_text, returncode=0)

    return _side_effect


# ---------------------------------------------------------------------------
# Test class.
# ---------------------------------------------------------------------------


class TestPR304Replay(unittest.TestCase):
    """Full pipeline replay against the synthetic PR #304 fixture."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_view = _load_pr_view()
        self._diff = _load_pr_diff()
        self._ticket = _load_ticket()
        self._expected = _load_expected()

        # Write ticket.txt to tmp dir so we can pass --ticket-file path.
        self._ticket_path = os.path.join(self._tmp, "ticket.txt")
        with open(self._ticket_path, "w", encoding="utf-8") as fh:
            fh.write(self._ticket)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    # ------------------------------------------------------------------
    # Helpers.
    # ------------------------------------------------------------------

    def _state_path(self, pr_number: int = 304) -> str:
        from _pr_review._state import state_path
        devforge = os.path.join(self._tmp, ".devforge")
        return state_path(devforge, pr_number)

    def _read_state(self, pr_number: int = 304) -> dict:
        sp = self._state_path(pr_number)
        with open(sp, "r", encoding="utf-8") as fh:
            return json.load(fh)

    # ------------------------------------------------------------------
    # Phase 1: intake.
    # ------------------------------------------------------------------

    def test_01_intake_creates_state(self):
        """intake populates state.json with base fields from fixture."""
        from _pr_review._intake import run as intake_run

        with patch(
            "_pr_review._intake.subprocess.run",
            side_effect=_make_gh_side_effect(self._pr_view, self._diff),
        ):
            result = intake_run(
                target=self._tmp,
                pr_number=304,
                repo="DoosanICA/db-cse-ui-strata",
                ticket_text=self._ticket,
            )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["pr_number"], 304)
        self.assertTrue(os.path.isfile(result["state_path"]))

        state = self._read_state()
        self.assertEqual(state["pr_number"], 304)
        self.assertEqual(state["repo"], "DoosanICA/db-cse-ui-strata")
        self.assertIn("MIG-2198", state["pr_title"])
        self.assertEqual(state["pr_body"], "")
        self.assertGreater(len(state["diff"]), 100)
        self.assertGreater(len(state["ticket_text"]), 50)
        self.assertGreater(len(state["commit_subjects"]), 0)

    # ------------------------------------------------------------------
    # Phase 4: detect-smells.
    # ------------------------------------------------------------------

    def test_02_detect_smells_required_smells_present(self):
        """detect-smells emits all 4 required smell types."""
        from _pr_review._intake import run as intake_run
        from _pr_review._cli import cmd_detect_smells
        import argparse

        with patch(
            "_pr_review._intake.subprocess.run",
            side_effect=_make_gh_side_effect(self._pr_view, self._diff),
        ):
            intake_run(
                target=self._tmp,
                pr_number=304,
                repo="DoosanICA/db-cse-ui-strata",
                ticket_text=self._ticket,
            )

        ns = argparse.Namespace(
            pr=304,
            target=self._tmp,
            devforge_dir=".devforge",
        )
        exit_code = cmd_detect_smells(ns)
        self.assertEqual(exit_code, 0)

        state = self._read_state()
        smells = state["smells"]

        # Minimum count from expected_outcomes.json.
        min_total = self._expected["expected_smells_min_total"]
        self.assertGreaterEqual(len(smells), min_total)

        # All required smell names must be present.
        found_names = {s["name"] for s in smells}
        for required_name in self._expected["expected_smells_must_include"]:
            self.assertIn(
                required_name,
                found_names,
                "Expected smell '{0}' not in {1}".format(required_name, found_names),
            )

    # ------------------------------------------------------------------
    # Phase 5: compute-blast-radius.
    # ------------------------------------------------------------------

    def test_03_blast_radius_symbols_extracted(self):
        """compute-blast-radius produces >= 3 probe specs across 2 languages."""
        from _pr_review._intake import run as intake_run
        from _pr_review._blast import run as blast_run

        with patch(
            "_pr_review._intake.subprocess.run",
            side_effect=_make_gh_side_effect(self._pr_view, self._diff),
        ):
            intake_run(
                target=self._tmp,
                pr_number=304,
                repo="DoosanICA/db-cse-ui-strata",
                ticket_text=self._ticket,
            )

        result = blast_run(
            target=self._tmp,
            pr_number=304,
        )

        self.assertEqual(result["status"], "ok")
        min_symbols = self._expected["expected_blast_symbols_min_count"]
        self.assertGreaterEqual(result["symbols_extracted"], min_symbols)

        state = self._read_state()
        blast = state["blast"]
        self.assertGreaterEqual(len(blast), min_symbols)

        # All probe specs must be unfilled (LLM-side phase skipped).
        for spec in blast:
            self.assertFalse(
                spec["filled"],
                "Expected filled=False but got True for {0}".format(spec["symbol"]),
            )

        # Must include both vue and typescript.
        langs = {s["language"] for s in blast}
        self.assertIn("vue", langs)
        self.assertIn("typescript", langs)

    # ------------------------------------------------------------------
    # Phase 6a: bundle-context.
    # ------------------------------------------------------------------

    def test_04_bundle_context_does_not_crash(self):
        """bundle-context succeeds with an empty .devforge dir (no docs)."""
        from _pr_review._intake import run as intake_run
        from _pr_review._bundle import run as bundle_run

        with patch(
            "_pr_review._intake.subprocess.run",
            side_effect=_make_gh_side_effect(self._pr_view, self._diff),
        ):
            intake_run(
                target=self._tmp,
                pr_number=304,
                repo="DoosanICA/db-cse-ui-strata",
                ticket_text=self._ticket,
            )

        result = bundle_run(
            target=self._tmp,
            pr_number=304,
        )

        self.assertEqual(result["status"], "ok")

        state = self._read_state()
        self.assertIsInstance(state["bundle"], dict)

    # ------------------------------------------------------------------
    # Phase 6b: import-handoffs.
    # ------------------------------------------------------------------

    def test_05_import_handoffs_returns_ok(self):
        """import-handoffs succeeds with no research/ dir (returns empty list)."""
        from _pr_review._intake import run as intake_run
        from _pr_review._handoff_import import run as handoff_run

        with patch(
            "_pr_review._intake.subprocess.run",
            side_effect=_make_gh_side_effect(self._pr_view, self._diff),
        ):
            intake_run(
                target=self._tmp,
                pr_number=304,
                repo="DoosanICA/db-cse-ui-strata",
                ticket_text=self._ticket,
            )

        result = handoff_run(
            target=self._tmp,
            pr_number=304,
        )

        self.assertEqual(result["status"], "ok")

    # ------------------------------------------------------------------
    # Phase 7: check-scope-drift.
    # ------------------------------------------------------------------

    def test_06_scope_drift_ac_bullets_extracted(self):
        """check-scope-drift extracts >= 9 AC-marker bullets from ticket."""
        from _pr_review._intake import run as intake_run
        from _pr_review._scope_drift import run as drift_run

        with patch(
            "_pr_review._intake.subprocess.run",
            side_effect=_make_gh_side_effect(self._pr_view, self._diff),
        ):
            intake_run(
                target=self._tmp,
                pr_number=304,
                repo="DoosanICA/db-cse-ui-strata",
                ticket_text=self._ticket,
            )

        result = drift_run(
            target=self._tmp,
            pr_number=304,
        )

        self.assertEqual(result["status"], "ok")
        min_bullets = self._expected["expected_drift_bullets_min_count"]
        self.assertGreaterEqual(result["bullets_extracted"], min_bullets)

        state = self._read_state()
        bullets = state["drift"]["bullets"]
        self.assertGreaterEqual(len(bullets), min_bullets)

        # At least one bullet must be extracted via ac_marker.
        ac_bullets = [b for b in bullets if b.get("extracted_via") == "ac_marker"]
        must_include_ac = self._expected["expected_drift_bullets_must_include_ac_markers"]
        if must_include_ac:
            self.assertGreater(
                len(ac_bullets),
                0,
                "Expected at least one ac_marker bullet but found none",
            )

        # LLM-side: coverage_matrix must be empty (not populated yet).
        self.assertEqual(state["drift"]["coverage_matrix"], [])
        self.assertFalse(state["drift"]["filled"])

    # ------------------------------------------------------------------
    # Phase 8: dispatch-review.
    # ------------------------------------------------------------------

    def test_07_dispatch_review_creates_brief(self):
        """dispatch-review creates brief.md with PR#304, AC-1, and smell names."""
        from _pr_review._intake import run as intake_run
        from _pr_review._blast import run as blast_run
        from _pr_review._bundle import run as bundle_run
        from _pr_review._handoff_import import run as handoff_run
        from _pr_review._scope_drift import run as drift_run
        from _pr_review._dispatch import run as dispatch_run
        from _pr_review._cli import cmd_detect_smells
        import argparse

        # Run full pipeline up to dispatch-review.
        with patch(
            "_pr_review._intake.subprocess.run",
            side_effect=_make_gh_side_effect(self._pr_view, self._diff),
        ):
            intake_run(
                target=self._tmp,
                pr_number=304,
                repo="DoosanICA/db-cse-ui-strata",
                ticket_text=self._ticket,
            )

        ns = argparse.Namespace(pr=304, target=self._tmp, devforge_dir=".devforge")
        cmd_detect_smells(ns)

        blast_run(target=self._tmp, pr_number=304)
        bundle_run(target=self._tmp, pr_number=304)
        handoff_run(target=self._tmp, pr_number=304)
        drift_run(target=self._tmp, pr_number=304)

        result = dispatch_run(target=self._tmp, pr_number=304)

        self.assertEqual(result["status"], "ok")
        brief_path = result["brief_path"]
        self.assertTrue(os.path.isfile(brief_path))

        with open(brief_path, "r", encoding="utf-8") as fh:
            brief_content = fh.read()

        self.assertIn("PR #304", brief_content)
        self.assertIn("AC-1", brief_content)
        # At least one required smell name must appear in the brief.
        found_smell_in_brief = any(
            name in brief_content
            for name in self._expected["expected_smells_must_include"]
        )
        self.assertTrue(
            found_smell_in_brief,
            "Expected at least one smell name in brief.md but found none",
        )

    # ------------------------------------------------------------------
    # Phase 9a: finalize-output.
    # ------------------------------------------------------------------

    def test_08_finalize_output_no_findings_marker(self):
        """finalize-output creates findings.md with the no-findings sentinel."""
        from _pr_review._intake import run as intake_run
        from _pr_review._blast import run as blast_run
        from _pr_review._bundle import run as bundle_run
        from _pr_review._handoff_import import run as handoff_run
        from _pr_review._scope_drift import run as drift_run
        from _pr_review._dispatch import run as dispatch_run
        from _pr_review._output import run as output_run
        from _pr_review._cli import cmd_detect_smells
        import argparse

        with patch(
            "_pr_review._intake.subprocess.run",
            side_effect=_make_gh_side_effect(self._pr_view, self._diff),
        ):
            intake_run(
                target=self._tmp,
                pr_number=304,
                repo="DoosanICA/db-cse-ui-strata",
                ticket_text=self._ticket,
            )

        ns = argparse.Namespace(pr=304, target=self._tmp, devforge_dir=".devforge")
        cmd_detect_smells(ns)

        blast_run(target=self._tmp, pr_number=304)
        bundle_run(target=self._tmp, pr_number=304)
        handoff_run(target=self._tmp, pr_number=304)
        drift_run(target=self._tmp, pr_number=304)
        dispatch_run(target=self._tmp, pr_number=304)

        result = output_run(target=self._tmp, pr_number=304)

        self.assertEqual(result["status"], "ok")
        findings_path = result["findings_path"]
        self.assertTrue(os.path.isfile(findings_path))

        with open(findings_path, "r", encoding="utf-8") as fh:
            findings_content = fh.read()

        # state.findings is empty (LLM-side phase was skipped).
        self.assertIn(
            "_No findings recorded",
            findings_content,
            "Expected no-findings sentinel in findings.md",
        )

    # ------------------------------------------------------------------
    # Phase 9b: append-to-replay-corpus.
    # ------------------------------------------------------------------

    def test_09_append_to_replay_corpus_index_entry(self):
        """append-to-replay-corpus creates bundle + corpus index with pr=304."""
        from _pr_review._intake import run as intake_run
        from _pr_review._blast import run as blast_run
        from _pr_review._bundle import run as bundle_run
        from _pr_review._handoff_import import run as handoff_run
        from _pr_review._scope_drift import run as drift_run
        from _pr_review._dispatch import run as dispatch_run
        from _pr_review._output import run as output_run
        from _pr_review._replay import run as replay_run
        from _pr_review._cli import cmd_detect_smells
        from _pr_review._state import _PR_REVIEWS_DIR
        import argparse

        with patch(
            "_pr_review._intake.subprocess.run",
            side_effect=_make_gh_side_effect(self._pr_view, self._diff),
        ):
            intake_run(
                target=self._tmp,
                pr_number=304,
                repo="DoosanICA/db-cse-ui-strata",
                ticket_text=self._ticket,
            )

        ns = argparse.Namespace(pr=304, target=self._tmp, devforge_dir=".devforge")
        cmd_detect_smells(ns)

        blast_run(target=self._tmp, pr_number=304)
        bundle_run(target=self._tmp, pr_number=304)
        handoff_run(target=self._tmp, pr_number=304)
        drift_run(target=self._tmp, pr_number=304)
        dispatch_run(target=self._tmp, pr_number=304)
        output_run(target=self._tmp, pr_number=304)

        result = replay_run(target=self._tmp, pr_number=304)

        self.assertEqual(result["status"], "ok")

        devforge = os.path.join(self._tmp, ".devforge")

        # Bundle file must exist.
        bundle_path = os.path.join(devforge, _PR_REVIEWS_DIR, "304", "pr-review-bundle.json")
        self.assertTrue(os.path.isfile(bundle_path))

        with open(bundle_path, "r", encoding="utf-8") as fh:
            bundle = json.load(fh)
        self.assertEqual(bundle["pr_number"], 304)
        self.assertEqual(bundle["schema_version"], "1")

        # Corpus index must exist and contain entry for pr=304.
        index_path = os.path.join(devforge, _PR_REVIEWS_DIR, "_corpus_index.json")
        self.assertTrue(os.path.isfile(index_path))

        with open(index_path, "r", encoding="utf-8") as fh:
            index = json.load(fh)

        entries = index.get("entries", [])
        self.assertGreater(len(entries), 0)

        pr304_entries = [
            e for e in entries
            if e.get("pr_number") == 304
            and e.get("repo") == "DoosanICA/db-cse-ui-strata"
        ]
        self.assertEqual(len(pr304_entries), 1)

        entry = pr304_entries[0]
        self.assertGreaterEqual(entry.get("review_count", 0), 1)
        self.assertGreater(entry.get("smells_count", 0), 0)
        self.assertGreater(entry.get("blast_probes_count", 0), 0)
        self.assertGreater(entry.get("drift_bullets_count", 0), 0)


class TestFixtureParseable(unittest.TestCase):
    """Sanity: fixture files are parseable and contain expected keys."""

    def test_pr_view_json_parseable(self):
        data = _load_pr_view()
        self.assertEqual(data["number"], 304)
        self.assertIn("MIG-2198", data["title"])
        self.assertEqual(data["body"], "")
        self.assertEqual(len(data["files"]), 5)
        self.assertEqual(len(data["commits"]), 1)

    def test_pr_diff_patch_starts_with_diff_git(self):
        diff = _load_pr_diff()
        self.assertTrue(
            diff.startswith("diff --git "),
            "pr_diff.patch first line must be 'diff --git ...'",
        )

    def test_ticket_txt_contains_ac_markers(self):
        ticket = _load_ticket()
        for i in range(1, 10):
            self.assertIn(
                "AC-{0}:".format(i),
                ticket,
                "ticket.txt missing AC-{0}".format(i),
            )

    def test_expected_outcomes_json_parseable(self):
        data = _load_expected()
        self.assertEqual(data["schema_version"], "1")
        self.assertEqual(data["pr_number"], 304)
        self.assertEqual(
            set(data["expected_smells_must_include"]),
            {"empty_pr_body", "atomic_dump", "hedge_defensive", "verbose_commit_msg"},
        )
        self.assertGreaterEqual(data["expected_blast_symbols_min_count"], 3)
        self.assertGreaterEqual(data["expected_drift_bullets_min_count"], 9)
        self.assertTrue(data["expected_drift_bullets_must_include_ac_markers"])


if __name__ == "__main__":
    unittest.main()
