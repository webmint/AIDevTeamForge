"""Tests for src/devforge/lib/_spec_check/_seed.py.

Coverage:

build_seed:
  - happy path: returns ReEntrySeed with source="spec-check",
    target_stage="spec" fixed regardless of caller input
  - seed_version equals SEED_SCHEMA_VERSION
  - all supplied fields preserved
  - cycle_count defaults to 1; carried_findings defaults to []
  - carried_findings=None normalizes to []
  - empty prior_conclusion / invalidating_evidence / must_satisfy /
    provenance / feature -> ValueError (delegated to __post_init__)
  - cycle_count == 0 / negative / bool -> ValueError

write_seed:
  - writes spec-check-seed.json (NOT grill-seed.json) at the correct path
  - creates feature_dir if missing
  - round-trips back into an equal ReEntrySeed
  - overwrites idempotently on a second call
  - no leftover temp files after a successful write
  - unconditional: writes whatever seed it is given, no verdict gating here
"""

import dataclasses
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

from _shared.seed_schema import ReEntrySeed, SEED_SCHEMA_VERSION  # noqa: E402
from _spec_check._seed import build_seed, write_seed  # noqa: E402


# ---------------------------------------------------------------------------
# Helper to build valid build_seed kwargs, overriding specific fields.
# ---------------------------------------------------------------------------

def _valid_seed_kwargs(**overrides):
    defaults = dict(
        feature="007-catalog-filters",
        prior_conclusion="The spec asserted AC-3 and AC-7 hold simultaneously.",
        invalidating_evidence=(
            "unsat core: {AC-3, AC-7} -- both cannot hold for the same input."
        ),
        must_satisfy="Resolve the conflict between AC-3 and AC-7.",
        provenance="specs/007-catalog-filters/spec-check.md",
    )
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# build_seed
# ---------------------------------------------------------------------------

class TestBuildSeed(unittest.TestCase):

    def test_happy_path_returns_re_entry_seed(self):
        seed = build_seed(**_valid_seed_kwargs())
        self.assertIsInstance(seed, ReEntrySeed)

    def test_source_is_spec_check(self):
        seed = build_seed(**_valid_seed_kwargs())
        self.assertEqual(seed.source, "spec-check")

    def test_target_stage_is_spec(self):
        seed = build_seed(**_valid_seed_kwargs())
        self.assertEqual(seed.target_stage, "spec")

    def test_seed_version_is_schema_version(self):
        seed = build_seed(**_valid_seed_kwargs())
        self.assertEqual(seed.seed_version, SEED_SCHEMA_VERSION)

    def test_cycle_count_defaults_to_one(self):
        seed = build_seed(**_valid_seed_kwargs())
        self.assertEqual(seed.cycle_count, 1)

    def test_carried_findings_defaults_to_empty_list(self):
        seed = build_seed(**_valid_seed_kwargs())
        self.assertEqual(seed.carried_findings, [])

    def test_carried_findings_none_normalizes_to_empty_list(self):
        seed = build_seed(**_valid_seed_kwargs(), carried_findings=None)
        self.assertEqual(seed.carried_findings, [])

    def test_fields_preserved(self):
        seed = build_seed(
            feature="feat-011-orders",
            prior_conclusion="prior claim",
            invalidating_evidence="evidence text",
            must_satisfy="must resolve X",
            provenance="specs/011-orders/spec-check.md",
            cycle_count=3,
            carried_findings=["F-001: conflicting AC pair"],
        )
        self.assertEqual(seed.feature, "feat-011-orders")
        self.assertEqual(seed.prior_conclusion, "prior claim")
        self.assertEqual(seed.invalidating_evidence, "evidence text")
        self.assertEqual(seed.must_satisfy, "must resolve X")
        self.assertEqual(seed.provenance, "specs/011-orders/spec-check.md")
        self.assertEqual(seed.cycle_count, 3)
        self.assertEqual(seed.carried_findings, ["F-001: conflicting AC pair"])

    def test_target_stage_is_always_spec_regardless_of_caller(self):
        """build_seed takes no target_stage param -- always 'spec'."""
        seed = build_seed(**_valid_seed_kwargs())
        self.assertEqual(seed.target_stage, "spec")
        # Confirm build_seed has no target_stage parameter at all.
        with self.assertRaises(TypeError):
            build_seed(**_valid_seed_kwargs(), target_stage="plan")  # type: ignore[call-arg]

    def test_empty_feature_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(feature=""))

    def test_empty_prior_conclusion_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(prior_conclusion=""))

    def test_empty_invalidating_evidence_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(invalidating_evidence=""))

    def test_empty_must_satisfy_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(must_satisfy=""))

    def test_empty_provenance_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(provenance=""))

    def test_cycle_count_zero_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(cycle_count=0))

    def test_cycle_count_negative_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(cycle_count=-1))

    def test_cycle_count_bool_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(cycle_count=True))

    def test_carried_findings_non_str_element_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(carried_findings=["ok", 42]))


# ---------------------------------------------------------------------------
# write_seed
# ---------------------------------------------------------------------------

class TestWriteSeed(unittest.TestCase):

    def _make_seed(self, **overrides):
        return build_seed(**_valid_seed_kwargs(**overrides))

    def test_writes_spec_check_seed_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "specs", "007-catalog-filters")
            os.makedirs(feature_dir)
            seed = self._make_seed()
            path = write_seed(feature_dir, seed)
            self.assertEqual(
                path, os.path.join(feature_dir, "spec-check-seed.json")
            )
            self.assertTrue(os.path.isfile(path))

    def test_does_not_write_grill_seed_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            os.makedirs(feature_dir)
            seed = self._make_seed()
            write_seed(feature_dir, seed)
            self.assertFalse(
                os.path.isfile(os.path.join(feature_dir, "grill-seed.json"))
            )

    def test_creates_feature_dir_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "specs", "new-feat")
            seed = self._make_seed()
            path = write_seed(feature_dir, seed)
            self.assertTrue(os.path.isfile(path))

    def test_round_trip_fields_preserved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            os.makedirs(feature_dir)
            seed = self._make_seed(
                feature="feat-042-payment",
                prior_conclusion="Spec assumed synchronous settlement.",
                invalidating_evidence="unsat core: {AC-2, AC-9}.",
                must_satisfy="Resolve settlement timing conflict.",
                cycle_count=2,
                carried_findings=["F-001: missing null check", "F-002: race on login"],
                provenance="specs/042-payment/spec-check.md",
            )
            path = write_seed(feature_dir, seed)
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)

            loaded = ReEntrySeed(**raw)
            self.assertEqual(loaded.target_stage, seed.target_stage)
            self.assertEqual(loaded.feature, seed.feature)
            self.assertEqual(loaded.prior_conclusion, seed.prior_conclusion)
            self.assertEqual(loaded.invalidating_evidence, seed.invalidating_evidence)
            self.assertEqual(loaded.must_satisfy, seed.must_satisfy)
            self.assertEqual(loaded.cycle_count, seed.cycle_count)
            self.assertEqual(loaded.carried_findings, seed.carried_findings)
            self.assertEqual(loaded.provenance, seed.provenance)
            self.assertEqual(loaded.source, seed.source)
            self.assertEqual(loaded.seed_version, seed.seed_version)

    def test_round_trip_equality(self):
        """Full dataclasses equality after write + re-read round-trip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            os.makedirs(feature_dir)
            original = self._make_seed()
            path = write_seed(feature_dir, original)
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)
            loaded = ReEntrySeed(**raw)
            self.assertEqual(dataclasses.asdict(loaded), dataclasses.asdict(original))

    def test_overwrites_idempotently(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            os.makedirs(feature_dir)
            seed1 = self._make_seed(cycle_count=1)
            path1 = write_seed(feature_dir, seed1)
            seed2 = self._make_seed(cycle_count=2)
            path2 = write_seed(feature_dir, seed2)
            self.assertEqual(path1, path2)
            with open(path2, encoding="utf-8") as fh:
                raw = json.load(fh)
            self.assertEqual(raw["cycle_count"], 2)

    def test_no_temp_files_left_behind(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            os.makedirs(feature_dir)
            seed = self._make_seed()
            write_seed(feature_dir, seed)
            files = os.listdir(feature_dir)
            temp_files = [f for f in files if f.startswith(".tmp-")]
            self.assertEqual(temp_files, [])

    def test_unconditional_write_no_verdict_gating(self):
        """write_seed writes any valid seed it is given -- no gating logic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            os.makedirs(feature_dir)
            seed = self._make_seed(cycle_count=5)
            path = write_seed(feature_dir, seed)
            self.assertTrue(os.path.isfile(path))


if __name__ == "__main__":
    unittest.main()
