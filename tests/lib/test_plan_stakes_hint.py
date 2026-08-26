"""Tests for plan_helper stakes-hint + _plan/_stakes.py.

Round-trip discipline: every "shape-valid" scenario writes a minimal but
real plan.md, runs it through the REAL `plan_helper finalize-handoff`
producer (subprocess) to get a genuine plan-handoff.json, then runs
`stakes-hint` on that file. No hand-authored plan-handoff.json fixtures for
the shape-valid cases.

Two deliberate exceptions, called out inline at the test: the malformed-JSON
case and the missing-breakdown_seeds case. Both simulate corrupted/legacy
producer output that the real producer cannot itself emit (finalize-handoff
always writes syntactically valid JSON with breakdown_seeds present), so
there is no "real producer path" to round-trip through for those two shapes
-- they mutate a real producer's output after the fact instead of hand-
authoring a fixture from scratch.

Anonymous content: domain terms use the "widget catalog search" theme
consistent with the existing plan-handoff fixture family; no real project
names.

Stdlib only.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
HELPER_PY = REPO_ROOT / "src" / "devforge" / "lib" / "plan_helper.py"


# ---------------------------------------------------------------------------
# Subprocess helper (matches test_plan_handoff.py convention).
# ---------------------------------------------------------------------------


def _run(*args, cwd=None):
    """Invoke plan_helper.py as a subprocess."""
    return subprocess.run(
        [sys.executable, str(HELPER_PY)] + list(args),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Minimal plan.md builders -- only the sections stakes-hint's signals read.
# ---------------------------------------------------------------------------


def _file_impact_table(n):
    # type: (int) -> str
    header = (
        "### File Impact\n\n"
        "| File | Action | What Changes |\n"
        "| --- | --- | --- |\n"
    )
    rows = "".join(
        "| src/widgets/module_{0}.py | Modify | Change {0} |\n".format(i)
        for i in range(1, n + 1)
    )
    return header + rows + "\n"


def _risk_table(risk_rows):
    # type: (List[Tuple[str, str]]) -> str
    header = (
        "## Risk Assessment\n\n"
        "| Risk | Likelihood | Impact | Mitigation |\n"
        "| --- | --- | --- | --- |\n"
    )
    rows = "".join(
        "| {0} | Low | {1} | Monitor closely |\n".format(risk, impact)
        for risk, impact in risk_rows
    )
    return header + rows + "\n"


def _decision_table(decision_rows):
    # type: (List[Tuple[str, str]]) -> str
    header = (
        "### Key Design Decisions\n\n"
        "| Decision | Chosen Approach | Why | Alternatives Rejected |\n"
        "| --- | --- | --- | --- |\n"
    )
    rows = "".join(
        "| {0} | Straightforward approach | {1} | None considered |\n".format(
            decision, why
        )
        for decision, why in decision_rows
    )
    return header + rows + "\n"


def _dependencies_section(lines):
    # type: (List[str]) -> str
    header = "## Dependencies\n\n"
    body = "\n".join(lines) + "\n" if lines else ""
    return header + body + "\n"


def _build_plan_md(
    file_impact_n=2,
    risk_rows=None,
    decision_rows=None,
    dependency_lines=None,
):
    # type: (int, Optional[List[Tuple[str, str]]], Optional[List[Tuple[str, str]]], Optional[List[str]]) -> str
    """Build a minimal-but-real plan.md exercising just the sections stakes-hint reads."""
    if risk_rows is None:
        risk_rows = [("Minor edge case in empty catalog", "Low")]
    if dependency_lines is None:
        dependency_lines = ["No external package dependencies."]

    content = (
        "# Plan: Widget Catalog Feature\n\n"
        "**Date**: 2026-07-04\n"
        "**Status**: Draft\n\n"
    )
    content += _file_impact_table(file_impact_n)
    if decision_rows:
        content += _decision_table(decision_rows)
    content += _risk_table(risk_rows)
    content += _dependencies_section(dependency_lines)
    return content


# ---------------------------------------------------------------------------
# Base test case: produces a real plan-handoff.json via the real producer.
# ---------------------------------------------------------------------------


class _StakesHintTestBase(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.plan_dir = self.tmp / "specs" / "011-widget-catalog-feature"

    def tearDown(self):
        self._tmp.cleanup()

    def _produce_handoff(self, **plan_md_kwargs):
        # type: (...) -> Path
        """Write plan.md, run the real finalize-handoff producer, return the
        path to the resulting plan-handoff.json."""
        self.plan_dir.mkdir(parents=True, exist_ok=True)
        plan_path = self.plan_dir / "plan.md"
        plan_path.write_text(_build_plan_md(**plan_md_kwargs), encoding="utf-8")

        result = _run("finalize-handoff", str(plan_path), cwd=self.tmp)
        self.assertEqual(
            result.returncode, 0,
            "finalize-handoff (real producer) failed: {0}".format(result.stderr),
        )
        return self.plan_dir / "plan-handoff.json"

    def _stakes_hint(self, handoff_path):
        return _run("stakes-hint", str(handoff_path), cwd=self.tmp)


# ---------------------------------------------------------------------------
# Below-threshold: silent.
# ---------------------------------------------------------------------------


class BelowThresholdTests(_StakesHintTestBase):
    """A small, typical plan (few files, few risks, no deps/data-model/security)
    must NOT fire -- proves the threshold isn't so eager it becomes noise."""

    def test_small_plan_produces_no_stdout(self):
        handoff_path = self._produce_handoff(
            file_impact_n=2,
            risk_rows=[("Minor edge case in empty catalog", "Low")],
            dependency_lines=["No external package dependencies."],
        )
        result = self._stakes_hint(handoff_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_small_plan_no_data_model_sibling(self):
        """Sanity check: no data-model.md was written for the below-threshold case."""
        handoff_path = self._produce_handoff(file_impact_n=2)
        self.assertFalse((handoff_path.parent / "data-model.md").exists())

        result = self._stakes_hint(handoff_path)
        self.assertEqual(result.stdout, "")


# ---------------------------------------------------------------------------
# Individual signals fire.
# ---------------------------------------------------------------------------


class IndividualSignalTests(_StakesHintTestBase):
    """Each signal, in isolation (all others absent), crosses the threshold."""

    def test_large_file_impact_fires(self):
        handoff_path = self._produce_handoff(
            file_impact_n=9,  # >= FILE_IMPACT_THRESHOLD (8)
            risk_rows=[("Minor edge case", "Low")],
            dependency_lines=["No external package dependencies."],
        )
        result = self._stakes_hint(handoff_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("9 files", result.stdout)
        self.assertNotIn("new data model", result.stdout)
        self.assertNotIn("security-relevant", result.stdout)
        self.assertNotIn("introduces a dependency", result.stdout)

    def test_data_model_present_fires(self):
        handoff_path = self._produce_handoff(
            file_impact_n=2,
            risk_rows=[("Minor edge case", "Low")],
            dependency_lines=["No external package dependencies."],
        )
        (handoff_path.parent / "data-model.md").write_text(
            "# Data Model\n\nWidget { id, name, tags }\n", encoding="utf-8"
        )

        result = self._stakes_hint(handoff_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("new data model", result.stdout)
        self.assertNotIn("touches", result.stdout)
        self.assertNotIn("security-relevant", result.stdout)
        self.assertNotIn("introduces a dependency", result.stdout)

    def test_security_keyword_in_risk_fires(self):
        handoff_path = self._produce_handoff(
            file_impact_n=2,
            risk_rows=[("Search index may leak user passwords", "High")],
            dependency_lines=["No external package dependencies."],
        )
        result = self._stakes_hint(handoff_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("security-relevant", result.stdout)
        self.assertNotIn("new data model", result.stdout)
        self.assertNotIn("introduces a dependency", result.stdout)

    def test_security_keyword_in_decision_fires(self):
        handoff_path = self._produce_handoff(
            file_impact_n=2,
            decision_rows=[
                ("Session handling", "Needed a stable OAuth token store"),
            ],
            risk_rows=[("Minor edge case", "Low")],
            dependency_lines=["No external package dependencies."],
        )
        result = self._stakes_hint(handoff_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("security-relevant", result.stdout)

    def test_new_dependency_fires(self):
        handoff_path = self._produce_handoff(
            file_impact_n=2,
            risk_rows=[("Minor edge case", "Low")],
            dependency_lines=[
                "Introduces a new dependency on the redux-toolkit package "
                "for state management."
            ],
        )
        result = self._stakes_hint(handoff_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("introduces a dependency", result.stdout)
        self.assertNotIn("touches", result.stdout)
        self.assertNotIn("new data model", result.stdout)
        self.assertNotIn("security-relevant", result.stdout)

    def test_many_risks_fires(self):
        handoff_path = self._produce_handoff(
            file_impact_n=2,
            risk_rows=[
                ("Risk one", "Low"),
                ("Risk two", "Low"),
                ("Risk three", "Low"),
                ("Risk four", "Low"),  # >= RISK_THRESHOLD (4)
            ],
            dependency_lines=["No external package dependencies."],
        )
        result = self._stakes_hint(handoff_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("4 risks recorded", result.stdout)


# ---------------------------------------------------------------------------
# Combined signals.
# ---------------------------------------------------------------------------


class CombinedSignalTests(_StakesHintTestBase):

    def test_combined_signals_all_named(self):
        handoff_path = self._produce_handoff(
            file_impact_n=11,
            risk_rows=[("Search index may leak user passwords", "High")],
            dependency_lines=["No external package dependencies."],
        )
        (handoff_path.parent / "data-model.md").write_text(
            "# Data Model\n\nWidget { id, name, tags }\n", encoding="utf-8"
        )

        result = self._stakes_hint(handoff_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("11 files", result.stdout)
        self.assertIn("new data model", result.stdout)
        self.assertIn("security-relevant", result.stdout)
        self.assertNotIn("introduces a dependency", result.stdout)

    def test_output_ends_with_literal_grill_next_step(self):
        handoff_path = self._produce_handoff(
            file_impact_n=9,
            risk_rows=[("Minor edge case", "Low")],
            dependency_lines=["No external package dependencies."],
        )
        result = self._stakes_hint(handoff_path)

        plan_path = handoff_path.resolve().parent / "plan.md"
        last_line = result.stdout.strip().splitlines()[-1]
        self.assertEqual(last_line, "/devforge:grill {0}".format(plan_path))

    def test_grill_line_uses_handoffs_recorded_plan_path(self):
        """FIX 4: plan_path must come from the handoff's own plan_path field,
        not be re-derived as handoff_dir/plan.md -- mutate the recorded
        plan_path to a location outside the handoff dir (simulating a
        moved/copied plan-handoff.json) and confirm that value wins."""
        handoff_path = self._produce_handoff(
            file_impact_n=9,
            risk_rows=[("Minor edge case", "Low")],
            dependency_lines=["No external package dependencies."],
        )
        d = json.loads(handoff_path.read_text(encoding="utf-8"))
        custom_plan_path = str(self.tmp / "elsewhere" / "plan.md")
        d["plan_path"] = custom_plan_path
        handoff_path.write_text(json.dumps(d), encoding="utf-8")

        result = self._stakes_hint(handoff_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        last_line = result.stdout.strip().splitlines()[-1]
        self.assertEqual(last_line, "/devforge:grill {0}".format(custom_plan_path))

    def test_grill_line_falls_back_to_derived_plan_path_when_field_absent(self):
        """FIX 4 fallback: real finalize-handoff always writes plan_path
        (schema-required); this mutates a real producer's output after the
        fact to simulate a corrupted/legacy handoff missing that field --
        the sibling handoff_dir/plan.md derivation must still be used."""
        handoff_path = self._produce_handoff(
            file_impact_n=9,
            risk_rows=[("Minor edge case", "Low")],
            dependency_lines=["No external package dependencies."],
        )
        d = json.loads(handoff_path.read_text(encoding="utf-8"))
        del d["plan_path"]
        handoff_path.write_text(json.dumps(d), encoding="utf-8")

        result = self._stakes_hint(handoff_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        derived_path = handoff_path.resolve().parent / "plan.md"
        last_line = result.stdout.strip().splitlines()[-1]
        self.assertEqual(last_line, "/devforge:grill {0}".format(derived_path))


# ---------------------------------------------------------------------------
# Robustness: malformed / missing / absent input -- always silent, exit 0.
# ---------------------------------------------------------------------------


class RobustnessTests(_StakesHintTestBase):

    def test_absent_file_silent(self):
        missing_path = self.tmp / "specs" / "999-nonexistent" / "plan-handoff.json"
        result = self._stakes_hint(missing_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_malformed_json_silent(self):
        """Real finalize-handoff never emits invalid JSON; this deliberately
        writes garbage bytes to exercise the parse-failure fallback."""
        bad_dir = self.tmp / "specs" / "012-bad"
        bad_dir.mkdir(parents=True, exist_ok=True)
        bad_path = bad_dir / "plan-handoff.json"
        bad_path.write_text("{ not valid json !!", encoding="utf-8")

        result = self._stakes_hint(bad_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_missing_breakdown_seeds_silent(self):
        """Real finalize-handoff always writes breakdown_seeds (schema-required);
        this mutates a real producer's output after the fact to simulate a
        corrupted/legacy file -- there is no real-producer path to a shape
        missing a mandatory field."""
        handoff_path = self._produce_handoff(file_impact_n=9)  # would otherwise fire
        d = json.loads(handoff_path.read_text(encoding="utf-8"))
        del d["breakdown_seeds"]
        handoff_path.write_text(json.dumps(d), encoding="utf-8")

        result = self._stakes_hint(handoff_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_non_dict_root_silent(self):
        weird_dir = self.tmp / "specs" / "013-weird"
        weird_dir.mkdir(parents=True, exist_ok=True)
        weird_path = weird_dir / "plan-handoff.json"
        weird_path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

        result = self._stakes_hint(weird_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_breakdown_seeds_wrong_type_silent(self):
        handoff_path = self._produce_handoff(file_impact_n=9)  # would otherwise fire
        d = json.loads(handoff_path.read_text(encoding="utf-8"))
        d["breakdown_seeds"] = "not-a-dict"
        handoff_path.write_text(json.dumps(d), encoding="utf-8")

        result = self._stakes_hint(handoff_path)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")


# ---------------------------------------------------------------------------
# _plan/_stakes.py unit tests (signal computation + rendering, direct import).
# ---------------------------------------------------------------------------

_LIB_DIR = REPO_ROOT / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _plan._stakes import (  # noqa: E402
    compute_signals,
    render_hint,
    FILE_IMPACT_THRESHOLD,
    RISK_THRESHOLD,
    _has_real_dependency,
)


class ComputeSignalsUnitTests(unittest.TestCase):

    def test_empty_seeds_no_fire(self):
        seeds = {
            "file_impact": [],
            "risks": [],
            "key_design_decisions": [],
            "dependencies": [],
        }
        signals = compute_signals(seeds, Path("/nonexistent"))
        self.assertFalse(signals["fires"])

    def test_file_impact_threshold_boundary(self):
        seeds = {
            "file_impact": [{"file": "x"}] * FILE_IMPACT_THRESHOLD,
            "risks": [],
            "key_design_decisions": [],
            "dependencies": [],
        }
        signals = compute_signals(seeds, Path("/nonexistent"))
        self.assertTrue(signals["large_blast_radius"])
        self.assertTrue(signals["fires"])

    def test_file_impact_one_below_threshold_does_not_fire_alone(self):
        seeds = {
            "file_impact": [{"file": "x"}] * (FILE_IMPACT_THRESHOLD - 1),
            "risks": [],
            "key_design_decisions": [],
            "dependencies": [],
        }
        signals = compute_signals(seeds, Path("/nonexistent"))
        self.assertFalse(signals["large_blast_radius"])
        self.assertFalse(signals["fires"])

    def test_risk_threshold_boundary(self):
        seeds = {
            "file_impact": [],
            "risks": [{"risk": "r", "impact": "Low"}] * RISK_THRESHOLD,
            "key_design_decisions": [],
            "dependencies": [],
        }
        signals = compute_signals(seeds, Path("/nonexistent"))
        self.assertTrue(signals["many_risks"])
        self.assertTrue(signals["fires"])

    def test_risk_one_below_threshold_does_not_fire_alone(self):
        """FIX 3: pins the below-threshold boundary for risks -- file_impact
        already has both an at-threshold and a one-below test; risks only
        had the at-threshold case until now."""
        seeds = {
            "file_impact": [],
            "risks": [{"risk": "r", "impact": "Low"}] * (RISK_THRESHOLD - 1),
            "key_design_decisions": [],
            "dependencies": [],
        }
        signals = compute_signals(seeds, Path("/nonexistent"))
        self.assertFalse(signals["many_risks"])
        self.assertFalse(signals["fires"])

    def test_malformed_field_types_degrade_gracefully(self):
        """A non-list field must not raise -- degrades to signal False."""
        seeds = {
            "file_impact": "not-a-list",
            "risks": None,
            "key_design_decisions": 42,
            "dependencies": {"not": "a-list"},
        }
        signals = compute_signals(seeds, Path("/nonexistent"))
        self.assertFalse(signals["fires"])

    def test_data_model_sibling_detected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            (tmp / "data-model.md").write_text("x", encoding="utf-8")
            seeds = {
                "file_impact": [],
                "risks": [],
                "key_design_decisions": [],
                "dependencies": [],
            }
            signals = compute_signals(seeds, tmp)
            self.assertTrue(signals["new_data_model"])
            self.assertTrue(signals["fires"])

    def test_non_string_risk_and_impact_fields_do_not_raise(self):
        """FIX 2: a non-string risk/impact field value (a malformed/hand-
        constructed shape the real producer cannot emit -- mirrors the
        rationale in test_breakdown_seeds_wrong_type_silent) must not raise
        in the security regex scan; it simply doesn't contribute a signal."""
        seeds = {
            "file_impact": [],
            "risks": [{"risk": 12345, "impact": 67890}],
            "key_design_decisions": [],
            "dependencies": [],
        }
        signals = compute_signals(seeds, Path("/nonexistent"))
        self.assertFalse(signals["security_relevant"])
        self.assertFalse(signals["fires"])

    def test_non_string_decision_and_why_fields_do_not_raise(self):
        """FIX 2: same as above but for key_design_decisions' decision/why
        fields."""
        seeds = {
            "file_impact": [],
            "risks": [],
            "key_design_decisions": [{"decision": 111, "why": [1, 2]}],
            "dependencies": [],
        }
        signals = compute_signals(seeds, Path("/nonexistent"))
        self.assertFalse(signals["security_relevant"])
        self.assertFalse(signals["fires"])

    def test_non_string_dependency_entries_do_not_raise(self):
        """FIX 2: a non-string entry in the dependencies list (int, None,
        dict, list) must not raise in the .strip() dependency scan; each
        such entry is simply treated as not-a-dependency."""
        seeds = {
            "file_impact": [],
            "risks": [],
            "key_design_decisions": [],
            "dependencies": [123, None, {"x": 1}, ["y"]],
        }
        signals = compute_signals(seeds, Path("/nonexistent"))
        self.assertFalse(signals["new_dependency"])
        self.assertFalse(signals["fires"])


class HasRealDependencyUnitTests(unittest.TestCase):

    def test_negation_only_is_not_real(self):
        self.assertFalse(_has_real_dependency(["No external dependencies."]))
        self.assertFalse(_has_real_dependency(["None."]))
        self.assertFalse(_has_real_dependency(["N/A"]))

    def test_blank_lines_ignored(self):
        self.assertFalse(_has_real_dependency(["", "   "]))

    def test_real_dependency_detected(self):
        self.assertTrue(
            _has_real_dependency(["Requires adding the redux-toolkit package."])
        )

    def test_mixed_negation_then_real_detected(self):
        self.assertTrue(
            _has_real_dependency(
                ["No breaking changes.", "Adds a new dependency on lodash."]
            )
        )

    # -- FIX 1 matrix: a line opening with a negation but stating a real
    # dependency later must be detected as True; a pure negation (even one
    # that negates a positive verb, e.g. "Requires no changes.") must stay
    # False. See _plan/_stakes.py's _has_positive_dependency_verb.

    def test_fix1_true_negation_then_real_dependency_core(self):
        self.assertTrue(
            _has_real_dependency(
                ["None needed for the core, but adds Redux for state management."]
            )
        )

    def test_fix1_true_negation_then_real_dependency_backend(self):
        self.assertTrue(
            _has_real_dependency(
                ["No new dependency for backend but adds jwt library."]
            )
        )

    def test_fix1_true_plain_adds(self):
        self.assertTrue(_has_real_dependency(["Adds Redux."]))

    def test_fix1_true_plain_requires(self):
        self.assertTrue(_has_real_dependency(["Requires PostgreSQL 15."]))

    def test_fix1_false_none(self):
        self.assertFalse(_has_real_dependency(["None"]))

    def test_fix1_false_none_lowercase(self):
        self.assertFalse(_has_real_dependency(["none"]))

    def test_fix1_false_n_a(self):
        self.assertFalse(_has_real_dependency(["N/A"]))

    def test_fix1_false_nil(self):
        self.assertFalse(_has_real_dependency(["nil"]))

    def test_fix1_false_no_new_dependencies(self):
        self.assertFalse(_has_real_dependency(["No new dependencies."]))

    def test_fix1_false_none_needed(self):
        self.assertFalse(_has_real_dependency(["None needed."]))

    def test_fix1_false_negated_positive_verb(self):
        """The trap case: a positive verb (Requires) immediately followed
        by a negation word (no) must NOT flip to a false positive."""
        self.assertFalse(_has_real_dependency(["Requires no changes."]))

    def test_fix1_false_empty_string(self):
        self.assertFalse(_has_real_dependency([""]))

    # --- Negation-object false-positive class (confirm-pass finding) ---
    # A positive verb whose object is a run-on negation (`nothing`/`nobody`)
    # or `zero` must NOT fire -- the naive `no\b` missed these because there
    # is no word boundary after `no` in `nothing`/`nobody`.

    def test_fix2_false_needs_nothing_new(self):
        self.assertFalse(_has_real_dependency(["Needs nothing new."]))

    def test_fix2_false_requires_nothing(self):
        self.assertFalse(_has_real_dependency(["Requires nothing."]))

    def test_fix2_false_depends_on_nothing(self):
        self.assertFalse(_has_real_dependency(["depends on nothing"]))

    def test_fix2_false_uses_nobody(self):
        self.assertFalse(_has_real_dependency(["Uses nobody else's code."]))

    def test_fix2_false_adds_no_dependencies(self):
        self.assertFalse(_has_real_dependency(["Adds no dependencies."]))

    def test_fix2_false_introduces_no_new_libraries(self):
        self.assertFalse(
            _has_real_dependency(["Introduces no new libraries."])
        )

    def test_fix2_false_uses_no_external_packages(self):
        self.assertFalse(_has_real_dependency(["Uses no external packages."]))

    def test_fix2_false_bare_nothing(self):
        self.assertFalse(_has_real_dependency(["nothing"]))

    # --- Over-suppression guard: a REAL dependency plus an unrelated
    # trailing negation must stay True (the negation is of a DIFFERENT thing,
    # not of the verb's own object). ---

    def test_fix2_true_real_dep_with_trailing_negation(self):
        self.assertTrue(
            _has_real_dependency(["Adds Redux, no other config needed."])
        )

    # --- Documented KNOWN limitation (not a bug): a negation separated from
    # its verb by an interposed clause is not detected, so this currently
    # returns True (a spurious, low-harm, advisory-only fire). Pinned to the
    # ACTUAL behavior + labeled so a future reader sees it is intentional. ---

    def test_fix2_known_limitation_interposed_clause_fires(self):
        self.assertTrue(
            _has_real_dependency(
                ["Requires, after review, no changes at all."]
            )
        )


class RenderHintUnitTests(unittest.TestCase):

    def test_ends_with_grill_line(self):
        signals = {"large_blast_radius": True, "file_count": 12}
        text = render_hint(signals, "specs/001-x/plan.md")
        last_line = text.strip().splitlines()[-1]
        self.assertEqual(last_line, "/devforge:grill specs/001-x/plan.md")

    def test_no_reasons_still_renders_grill_line(self):
        """Defensive: even an empty signals dict renders a valid block (callers
        are expected to gate on 'fires' before calling, but this must not raise)."""
        text = render_hint({}, "specs/001-x/plan.md")
        last_line = text.strip().splitlines()[-1]
        self.assertEqual(last_line, "/devforge:grill specs/001-x/plan.md")

    def test_hint_names_grill_as_required_not_optional(self):
        """/devforge:breakdown carries a mandatory grill entry gate (PHASE
        0a.6) -- the hint must tell the author to run grill NOW because it is
        required before /devforge:breakdown, not merely suggest considering
        it. Pins the substantive claim (required + name both commands),
        not the exact sentence, so a harmless rephrase doesn't need a test
        edit. Also pins the stale phrasing's absence so it cannot silently
        drift back."""
        signals = {"large_blast_radius": True, "file_count": 9}
        text = render_hint(signals, "specs/001-x/plan.md")

        # Stale optional-sounding phrasing must be gone.
        self.assertNotIn("Consider running", text)
        self.assertNotIn("optional, not", text)
        self.assertNotIn("not a gate", text)

        # Both commands named.
        self.assertIn("/devforge:grill", text)
        self.assertIn("/devforge:breakdown", text)

        # Substantive claim: grill is required before breakdown will run.
        self.assertIn("required", text)

        # Must NOT claim the gate reads the verdict or freshness, and must
        # NOT imply revising the plan invalidates the grill run.
        self.assertNotIn("verdict", text)
        self.assertNotIn("disposition", text)
        self.assertNotIn("stale", text)
        self.assertNotIn("invalidat", text)


if __name__ == "__main__":
    unittest.main()
