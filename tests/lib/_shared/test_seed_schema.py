"""Tests for src/devforge/lib/_shared/seed_schema.py.

Coverage:
- Happy path: valid seed constructs for each target_stage value.
- Required string fields empty -> ValueError (one test per field).
- source not in SEED_SOURCES -> ValueError; each SEED_SOURCES member accepted.
- target_stage not in SEED_TARGET_STAGES -> ValueError.
- cycle_count as bool / 0 / negative -> ValueError; >= 1 passes.
- carried_findings non-list -> ValueError; non-str element -> ValueError;
  empty list passes; list with items passes.
- provenance empty -> ValueError.
- Module constants exported correctly.
"""

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _shared.seed_schema import (  # noqa: E402
    SEED_SCHEMA_VERSION,
    SEED_SOURCES,
    SEED_TARGET_STAGES,
    ReEntrySeed,
)


# ---------------------------------------------------------------------------
# Helper to build a minimal valid seed, overriding specific fields.
# ---------------------------------------------------------------------------

def _make_seed(**overrides):
    """Return a ReEntrySeed with all valid defaults, applying overrides."""
    defaults = dict(
        seed_version="1",
        source="grill",
        target_stage="spec",
        feature="feat-001-widget-catalog",
        prior_conclusion="The spec assumed synchronous processing was sufficient.",
        invalidating_evidence="grill finding F-003: queue depth exceeds 10k under load.",
        must_satisfy="Spec must address async processing path explicitly.",
        cycle_count=1,
        carried_findings=[],
        provenance="specs/001-widget-catalog/grill.md",
    )
    defaults.update(overrides)
    return ReEntrySeed(**defaults)


# ---------------------------------------------------------------------------
# Module-level constants.
# ---------------------------------------------------------------------------

class TestModuleConstants(unittest.TestCase):

    def test_seed_sources_value(self):
        self.assertEqual(SEED_SOURCES, ("grill", "spec-check"))

    def test_seed_sources_is_tuple(self):
        self.assertIsInstance(SEED_SOURCES, tuple)

    def test_seed_target_stages_tuple(self):
        self.assertIsInstance(SEED_TARGET_STAGES, tuple)
        self.assertIn("spec", SEED_TARGET_STAGES)
        self.assertIn("discovery", SEED_TARGET_STAGES)
        self.assertIn("research", SEED_TARGET_STAGES)

    def test_seed_schema_version_is_string(self):
        self.assertIsInstance(SEED_SCHEMA_VERSION, str)
        self.assertTrue(len(SEED_SCHEMA_VERSION) > 0)

    def test_plan_in_seed_target_stages(self):
        self.assertIn("plan", SEED_TARGET_STAGES)

    def test_seed_target_stages_has_exactly_four_members(self):
        self.assertEqual(len(SEED_TARGET_STAGES), 4)


# ---------------------------------------------------------------------------
# Happy path: one test per target_stage value.
# ---------------------------------------------------------------------------

class TestReEntrySeedHappyPath(unittest.TestCase):

    def test_target_stage_spec(self):
        seed = _make_seed(target_stage="spec")
        self.assertEqual(seed.target_stage, "spec")
        self.assertEqual(seed.source, "grill")
        self.assertEqual(seed.cycle_count, 1)
        self.assertEqual(seed.carried_findings, [])

    def test_target_stage_discovery(self):
        seed = _make_seed(target_stage="discovery")
        self.assertEqual(seed.target_stage, "discovery")

    def test_target_stage_research(self):
        seed = _make_seed(target_stage="research")
        self.assertEqual(seed.target_stage, "research")

    def test_target_stage_plan(self):
        seed = _make_seed(
            target_stage="plan",
            carried_findings=["prior finding from first grill pass"],
            cycle_count=2,
        )
        self.assertEqual(seed.target_stage, "plan")
        self.assertEqual(seed.source, "grill")
        self.assertEqual(seed.cycle_count, 2)
        self.assertEqual(seed.carried_findings, ["prior finding from first grill pass"])

    def test_target_stage_plan_all_ten_fields(self):
        """Full 10-field construction with target_stage='plan'."""
        seed = ReEntrySeed(
            seed_version="1",
            source="grill",
            target_stage="plan",
            feature="005-payment-flow",
            prior_conclusion="Plan assumed synchronous payment processing.",
            invalidating_evidence="grill F-002: SLA requires < 200ms; sync path is 800ms.",
            must_satisfy="Plan must address async payment processing with idempotency.",
            cycle_count=1,
            carried_findings=[],
            provenance="specs/005-payment-flow/grill.md",
        )
        self.assertEqual(seed.seed_version, "1")
        self.assertEqual(seed.source, "grill")
        self.assertEqual(seed.target_stage, "plan")
        self.assertEqual(seed.feature, "005-payment-flow")
        self.assertEqual(seed.cycle_count, 1)
        self.assertEqual(seed.carried_findings, [])

    def test_carried_findings_with_items(self):
        seed = _make_seed(
            carried_findings=["Finding A: missed edge case.", "Finding B: stale assumption."]
        )
        self.assertEqual(len(seed.carried_findings), 2)
        self.assertEqual(seed.carried_findings[0], "Finding A: missed edge case.")

    def test_cycle_count_greater_than_one(self):
        seed = _make_seed(cycle_count=3)
        self.assertEqual(seed.cycle_count, 3)

    def test_seed_is_frozen(self):
        seed = _make_seed()
        with self.assertRaises((AttributeError, TypeError)):
            seed.cycle_count = 99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Required string fields empty -> ValueError.
# ---------------------------------------------------------------------------

class TestRequiredStringFieldsEmpty(unittest.TestCase):

    def test_seed_version_empty(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(seed_version="")
        self.assertIn("seed_version", str(ctx.exception))

    def test_seed_version_whitespace_only(self):
        with self.assertRaises(ValueError):
            _make_seed(seed_version="   ")

    def test_feature_empty(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(feature="")
        self.assertIn("feature", str(ctx.exception))

    def test_prior_conclusion_empty(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(prior_conclusion="")
        self.assertIn("prior_conclusion", str(ctx.exception))

    def test_invalidating_evidence_empty(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(invalidating_evidence="")
        self.assertIn("invalidating_evidence", str(ctx.exception))

    def test_must_satisfy_empty(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(must_satisfy="")
        self.assertIn("must_satisfy", str(ctx.exception))

    def test_provenance_empty(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(provenance="")
        self.assertIn("provenance", str(ctx.exception))

    def test_provenance_whitespace_only(self):
        with self.assertRaises(ValueError):
            _make_seed(provenance="  \t  ")

    def test_seed_version_wrong_type(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(seed_version=1)  # type: ignore[arg-type]
        self.assertIn("seed_version", str(ctx.exception))

    def test_feature_wrong_type(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(feature=None)  # type: ignore[arg-type]
        self.assertIn("feature", str(ctx.exception))


# ---------------------------------------------------------------------------
# source field validation (multi-source: SEED_SOURCES membership).
# ---------------------------------------------------------------------------

class TestSourceValidation(unittest.TestCase):

    def test_source_unknown_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(source="audit")
        self.assertIn("source", str(ctx.exception))

    def test_source_empty_string(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(source="")
        self.assertIn("source", str(ctx.exception))

    def test_source_grill_uppercase_rejected(self):
        # "GRILL" is not in SEED_SOURCES -- case-sensitive enum match.
        with self.assertRaises(ValueError):
            _make_seed(source="GRILL")

    def test_source_grill_accepted(self):
        seed = _make_seed(source="grill")
        self.assertEqual(seed.source, "grill")

    def test_source_spec_check_accepted(self):
        seed = _make_seed(source="spec-check")
        self.assertEqual(seed.source, "spec-check")

    def test_all_seed_sources_accepted(self):
        for source in SEED_SOURCES:
            with self.subTest(source=source):
                seed = _make_seed(source=source)
                self.assertEqual(seed.source, source)


# ---------------------------------------------------------------------------
# target_stage enum validation.
# ---------------------------------------------------------------------------

class TestTargetStageValidation(unittest.TestCase):

    def test_invalid_target_stage(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(target_stage="bogus")
        self.assertIn("target_stage", str(ctx.exception))

    def test_invalid_target_stage_empty(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(target_stage="")
        self.assertIn("target_stage", str(ctx.exception))

    def test_invalid_target_stage_case_sensitive(self):
        with self.assertRaises(ValueError):
            _make_seed(target_stage="Spec")

    def test_all_valid_target_stages(self):
        for stage in SEED_TARGET_STAGES:
            with self.subTest(stage=stage):
                seed = _make_seed(target_stage=stage)
                self.assertEqual(seed.target_stage, stage)


# ---------------------------------------------------------------------------
# cycle_count validation.
# ---------------------------------------------------------------------------

class TestCycleCountValidation(unittest.TestCase):

    def test_cycle_count_bool_true_rejected(self):
        # bool is a subclass of int in Python; must be explicitly rejected.
        with self.assertRaises(ValueError) as ctx:
            _make_seed(cycle_count=True)
        self.assertIn("bool", str(ctx.exception))

    def test_cycle_count_bool_false_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(cycle_count=False)
        self.assertIn("bool", str(ctx.exception))

    def test_cycle_count_zero_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(cycle_count=0)
        self.assertIn("cycle_count", str(ctx.exception))

    def test_cycle_count_negative_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(cycle_count=-1)
        self.assertIn("cycle_count", str(ctx.exception))

    def test_cycle_count_one_accepted(self):
        seed = _make_seed(cycle_count=1)
        self.assertEqual(seed.cycle_count, 1)

    def test_cycle_count_large_positive_accepted(self):
        seed = _make_seed(cycle_count=100)
        self.assertEqual(seed.cycle_count, 100)

    def test_cycle_count_string_rejected(self):
        with self.assertRaises((ValueError, TypeError)):
            _make_seed(cycle_count="1")  # type: ignore[arg-type]

    def test_cycle_count_float_rejected(self):
        with self.assertRaises((ValueError, TypeError)):
            _make_seed(cycle_count=1.0)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# carried_findings validation.
# ---------------------------------------------------------------------------

class TestCarriedFindingsValidation(unittest.TestCase):

    def test_carried_findings_non_list_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(carried_findings="not a list")  # type: ignore[arg-type]
        self.assertIn("carried_findings", str(ctx.exception))

    def test_carried_findings_tuple_rejected(self):
        with self.assertRaises(ValueError):
            _make_seed(carried_findings=("finding one",))  # type: ignore[arg-type]

    def test_carried_findings_non_str_element_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(carried_findings=["valid finding", 42])  # type: ignore[list-item]
        self.assertIn("carried_findings[1]", str(ctx.exception))

    def test_carried_findings_none_element_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _make_seed(carried_findings=[None])  # type: ignore[list-item]
        self.assertIn("carried_findings[0]", str(ctx.exception))

    def test_carried_findings_empty_list_accepted(self):
        seed = _make_seed(carried_findings=[])
        self.assertEqual(seed.carried_findings, [])

    def test_carried_findings_empty_string_element_accepted(self):
        # An empty-string element is intentionally accepted for consistency with
        # findings_schema.Finding.references (the loop only checks isinstance(item, str)).
        # Do NOT add element-level non-empty validation here.
        seed = _make_seed(carried_findings=[""])
        self.assertEqual(seed.carried_findings, [""])

    def test_carried_findings_list_of_strings_accepted(self):
        findings = ["finding A", "finding B", "finding C"]
        seed = _make_seed(carried_findings=findings)
        self.assertEqual(seed.carried_findings, findings)

    def test_carried_findings_single_item_accepted(self):
        seed = _make_seed(carried_findings=["single prior finding"])
        self.assertEqual(len(seed.carried_findings), 1)


# ---------------------------------------------------------------------------
# Integration: full round-trip with non-trivial values.
# ---------------------------------------------------------------------------

class TestReEntrySeedRoundTrip(unittest.TestCase):

    def test_full_seed_round_trip(self):
        """Construct a seed with all fields populated; verify field identity."""
        seed = ReEntrySeed(
            seed_version="1",
            source="grill",
            target_stage="discovery",
            feature="003-async-orders",
            prior_conclusion="Discovery concluded polling was sufficient at 1 RPS.",
            invalidating_evidence=(
                "grill F-007: load test shows 50 RPS burst; polling latency 12s."
            ),
            must_satisfy=(
                "Discovery must evaluate event-driven alternatives for burst traffic."
            ),
            cycle_count=2,
            carried_findings=[
                "F-004: missing idempotency key on retry path",
                "F-007: polling latency unacceptable under burst",
            ],
            provenance="specs/003-async-orders/grill.md",
        )
        self.assertEqual(seed.seed_version, "1")
        self.assertEqual(seed.source, "grill")
        self.assertEqual(seed.target_stage, "discovery")
        self.assertEqual(seed.feature, "003-async-orders")
        self.assertEqual(seed.cycle_count, 2)
        self.assertEqual(len(seed.carried_findings), 2)
        self.assertEqual(seed.provenance, "specs/003-async-orders/grill.md")

    def test_full_seed_round_trip_spec_check_source(self):
        """spec-check source constructs and validates identically to grill."""
        seed = ReEntrySeed(
            seed_version="1",
            source="spec-check",
            target_stage="spec",
            feature="007-catalog-filters",
            prior_conclusion="Spec asserted AC-3 and AC-7 are simultaneously satisfiable.",
            invalidating_evidence=(
                "spec-check unsat core: {AC-3, AC-7} -- both cannot hold for the same input."
            ),
            must_satisfy="Resolve the conflict between AC-3 and AC-7.",
            cycle_count=1,
            carried_findings=[],
            provenance="specs/007-catalog-filters/spec-check.md",
        )
        self.assertEqual(seed.source, "spec-check")
        self.assertEqual(seed.target_stage, "spec")


if __name__ == "__main__":
    unittest.main()
