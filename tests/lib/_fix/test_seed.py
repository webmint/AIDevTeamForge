"""Tests for src/devforge/lib/_fix/_seed.py + the write-seed CLI verb.

Mirrors tests/lib/_spec_check/test_seed.py's structure (the module under
test is modeled on _spec_check/_seed.py per plan 83 D5). Unlike that file,
this one also exercises the CLI verb end-to-end via _fix's own harness
convention -- main(argv) with captured stdout/stderr (see
tests/lib/_fix/test_fix_helper.py's _capture helper, mirrored below) --
rather than calling cmd_write_seed directly with a hand-built _Args stand-in.

Coverage:

build_seed:
  - happy path: returns ReEntrySeed with source="fix", target_stage="spec"
    fixed regardless of caller input
  - seed_version equals SEED_SCHEMA_VERSION
  - all supplied fields preserved
  - cycle_count defaults to 1; carried_findings defaults to []
  - carried_findings=None normalizes to []
  - build_seed has no target_stage parameter at all (TypeError on attempt)
  - empty prior_conclusion / invalidating_evidence / must_satisfy /
    provenance / feature -> ValueError (delegated to __post_init__)
  - cycle_count == 0 / negative / bool -> ValueError
  - carried_findings non-str element -> ValueError
  - plan 83 OQ-4 case-3: the ratified conversational-defect provenance
    literal constructs successfully [MANDATORY case 4]

write_seed:
  - writes fix-seed.json (NOT grill-seed.json / spec-check-seed.json) at
    the correct path
  - creates feature_dir if missing
  - round-trips back into an equal ReEntrySeed
  - overwrites idempotently on a second call with different content
    [MANDATORY case 3 -- atomic overwrite]
  - no leftover temp files after a successful write
  - unconditional: writes whatever seed it is given, no verdict gating here
  - plan 83 OQ-4 multi-item bounce: one call whose carried_findings carries
    two items' reasoning produces ONE file carrying both -- option (i),
    mechanically forced by the fixed fix-seed.json name (D4)
    [MANDATORY case 5]

CLI (write-seed verb, via main(argv)):
  - --help exits 0
  - top-level --help lists write-seed
  - write-seed registered in _SUBCOMMAND_REGISTRY
  - missing required args (argparse-level) -> exit 2
  - happy path -> exit 0, {"seed_path": ...} JSON ack, file written,
    source/target_stage/all fields round-trip [MANDATORY case 1]
  - empty --must-satisfy (argparse-level present, value empty) -> exit 2,
    NO file written [MANDATORY case 2]
  - empty --prior-conclusion / --invalidating-evidence / --provenance ->
    exit 2, no file written
  - bad --cycle-count (non-integer) -> exit 2
  - bad --carried-findings (not JSON) -> exit 2
  - bad --carried-findings (JSON but not an array) -> exit 2
"""

from __future__ import annotations

import dataclasses
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

from _shared.seed_schema import ReEntrySeed, SEED_SCHEMA_VERSION  # noqa: E402
from _fix._cli import _SUBCOMMAND_REGISTRY, main  # noqa: E402
from _fix._seed import build_seed, write_seed  # noqa: E402


# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


def _capture(argv):
    # type: (list) -> tuple
    """Run main(argv) with captured stdout/stderr. Returns (stdout, stderr, rc).

    Catches SystemExit (raised by argparse on bad args / --help) and converts
    the exit code to an integer. Mirrors test_fix_helper.py's _capture.
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


def _valid_seed_kwargs(**overrides):
    defaults = dict(
        feature="009-multi-item-bounce",
        prior_conclusion=(
            "The named item was diagnosed as a mechanical repair but the "
            "fix requires a new data model."
        ),
        invalidating_evidence=(
            'quoted review.md evidence: "the filter needs a persisted '
            'facet table" -- scope change (new data model)'
        ),
        must_satisfy="Resolve the data-model gap before remediation continues.",
        provenance="specs/009-multi-item-bounce/review.md",
    )
    defaults.update(overrides)
    return defaults


def _valid_cli_argv(feature_dir, **overrides):
    args = {
        "--feature": "009-multi-item-bounce",
        "--feature-dir": feature_dir,
        "--prior-conclusion": "conclusion text",
        "--invalidating-evidence": "evidence text",
        "--must-satisfy": "must satisfy text",
        "--provenance": "specs/009-multi-item-bounce/review.md",
    }
    args.update(overrides)
    argv = ["write-seed"]
    for flag, value in args.items():
        if value is None:
            continue
        argv.extend([flag, value])
    return argv


# ---------------------------------------------------------------------------
# build_seed
# ---------------------------------------------------------------------------


class TestBuildSeed(unittest.TestCase):

    def test_happy_path_returns_re_entry_seed(self):
        seed = build_seed(**_valid_seed_kwargs())
        self.assertIsInstance(seed, ReEntrySeed)

    def test_source_is_fix(self):
        seed = build_seed(**_valid_seed_kwargs())
        self.assertEqual(seed.source, "fix")

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
            feature="feat-014-search",
            prior_conclusion="prior claim",
            invalidating_evidence="evidence text",
            must_satisfy="must resolve X",
            provenance="specs/014-search/verification.md",
            cycle_count=3,
            carried_findings=["F-001: scope change on AC-4"],
        )
        self.assertEqual(seed.feature, "feat-014-search")
        self.assertEqual(seed.prior_conclusion, "prior claim")
        self.assertEqual(seed.invalidating_evidence, "evidence text")
        self.assertEqual(seed.must_satisfy, "must resolve X")
        self.assertEqual(seed.provenance, "specs/014-search/verification.md")
        self.assertEqual(seed.cycle_count, 3)
        self.assertEqual(seed.carried_findings, ["F-001: scope change on AC-4"])

    def test_target_stage_is_always_spec_regardless_of_caller(self):
        """build_seed takes no target_stage param -- always 'spec'."""
        seed = build_seed(**_valid_seed_kwargs())
        self.assertEqual(seed.target_stage, "spec")
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

    def test_conversational_defect_provenance_literal_constructs(self):
        """MANDATORY case 4 (plan 83 OQ-4 case-3): the ratified literal for a
        case-3 conversational defect (no report file on disk) constructs a
        valid seed."""
        seed = build_seed(
            **_valid_seed_kwargs(
                provenance="conversational (in-window user report; no report file)"
            )
        )
        self.assertEqual(
            seed.provenance,
            "conversational (in-window user report; no report file)",
        )


# ---------------------------------------------------------------------------
# write_seed
# ---------------------------------------------------------------------------


class TestWriteSeed(unittest.TestCase):

    def _make_seed(self, **overrides):
        return build_seed(**_valid_seed_kwargs(**overrides))

    def test_writes_fix_seed_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "specs", "009-multi-item-bounce")
            os.makedirs(feature_dir)
            seed = self._make_seed()
            path = write_seed(feature_dir, seed)
            self.assertEqual(
                path, os.path.join(feature_dir, "fix-seed.json")
            )
            self.assertTrue(os.path.isfile(path))

    def test_does_not_write_sibling_producer_filenames(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            os.makedirs(feature_dir)
            seed = self._make_seed()
            write_seed(feature_dir, seed)
            self.assertFalse(
                os.path.isfile(os.path.join(feature_dir, "grill-seed.json"))
            )
            self.assertFalse(
                os.path.isfile(os.path.join(feature_dir, "spec-check-seed.json"))
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
                prior_conclusion="Fix assumed a config toggle; needs a new table.",
                invalidating_evidence='quoted evidence: "..." -- scope change',
                must_satisfy="Resolve the payment settlement data-model gap.",
                cycle_count=2,
                carried_findings=["F-001: missing table", "F-002: race on write"],
                provenance="specs/042-payment/review.md",
            )
            path = write_seed(feature_dir, seed)
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)

            loaded = ReEntrySeed(**raw)
            self.assertEqual(loaded.target_stage, seed.target_stage)
            self.assertEqual(loaded.source, seed.source)
            self.assertEqual(loaded.feature, seed.feature)
            self.assertEqual(loaded.prior_conclusion, seed.prior_conclusion)
            self.assertEqual(loaded.invalidating_evidence, seed.invalidating_evidence)
            self.assertEqual(loaded.must_satisfy, seed.must_satisfy)
            self.assertEqual(loaded.cycle_count, seed.cycle_count)
            self.assertEqual(loaded.carried_findings, seed.carried_findings)
            self.assertEqual(loaded.provenance, seed.provenance)
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

    def test_overwrites_in_place_atomically(self):
        """MANDATORY case 3: a second write with different content replaces
        the file in place at the same path (atomic overwrite)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            os.makedirs(feature_dir)
            seed1 = self._make_seed(cycle_count=1, must_satisfy="first cycle")
            path1 = write_seed(feature_dir, seed1)
            seed2 = self._make_seed(cycle_count=2, must_satisfy="second cycle")
            path2 = write_seed(feature_dir, seed2)
            self.assertEqual(path1, path2)
            with open(path2, encoding="utf-8") as fh:
                raw = json.load(fh)
            self.assertEqual(raw["cycle_count"], 2)
            self.assertEqual(raw["must_satisfy"], "second cycle")
            # Exactly one fix-seed.json survives -- no stale copy left behind.
            seed_files = [f for f in os.listdir(feature_dir) if f == "fix-seed.json"]
            self.assertEqual(seed_files, ["fix-seed.json"])

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

    def test_multi_item_bounce_one_seed_carries_both_items_reasoning(self):
        """MANDATORY case 5 (plan 83 OQ-4 third sub-case): two working-list
        items each independently trigger a scope-change bounce in the same
        run. Option (i) -- one seed whose flat strings synthesize across the
        items, with each item's own reasoning carried in carried_findings --
        is mechanically forced by D4's fixed fix-seed.json name: there is no
        way to call write_seed twice in the same feature_dir and end up with
        two files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "specs", "009-multi-item-bounce")
            os.makedirs(feature_dir)
            seed = build_seed(
                feature="009-multi-item-bounce",
                prior_conclusion=(
                    "Item A (AC-2) and Item B (AC-5) were both diagnosed as "
                    "mechanical repairs but each requires an architectural "
                    "change."
                ),
                invalidating_evidence=(
                    "Item A: quoted review.md evidence -- scope change (new "
                    "data model). Item B: quoted verification.md evidence -- "
                    "scope change (new external dependency)."
                ),
                must_satisfy=(
                    "Resolve AC-2's data-model gap and AC-5's dependency gap."
                ),
                provenance="specs/009-multi-item-bounce/review.md",
                carried_findings=[
                    "Item A: AC-2 scope change -- new data model required.",
                    "Item B: AC-5 scope change -- new external dependency "
                    "required.",
                ],
            )
            path = write_seed(feature_dir, seed)
            self.assertEqual(path, os.path.join(feature_dir, "fix-seed.json"))

            # Exactly one seed file in the directory (D4's fixed naming).
            seed_files = [
                f for f in os.listdir(feature_dir) if f.endswith("-seed.json")
            ]
            self.assertEqual(seed_files, ["fix-seed.json"])

            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)
            self.assertEqual(len(raw["carried_findings"]), 2)
            self.assertIn("Item A", raw["carried_findings"][0])
            self.assertIn("Item B", raw["carried_findings"][1])
            self.assertIn("AC-2", raw["prior_conclusion"])
            self.assertIn("AC-5", raw["prior_conclusion"])


# ---------------------------------------------------------------------------
# CLI: write-seed verb (via main(argv))
# ---------------------------------------------------------------------------


class TestWriteSeedCli(unittest.TestCase):

    def test_write_seed_registered_in_subcommand_registry(self):
        names = [verb for verb, _, _ in _SUBCOMMAND_REGISTRY]
        self.assertIn("write-seed", names)

    def test_top_level_help_lists_write_seed(self):
        out, err, rc = _capture(["--help"])
        self.assertEqual(rc, 0)
        self.assertIn("write-seed", out)

    def test_write_seed_help_exits_zero(self):
        out, err, rc = _capture(["write-seed", "--help"])
        self.assertEqual(rc, 0)

    def test_missing_feature_dir_exits_2(self):
        # argparse-level: --feature-dir is required=True.
        out, err, rc = _capture(["write-seed"])
        self.assertEqual(rc, 2)

    def test_happy_path_cli_writes_file_and_round_trips(self):
        """MANDATORY case 1: the written JSON has source == "fix" and
        target_stage == "spec", all fields round-trip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "specs", "009-multi-item-bounce")
            argv = _valid_cli_argv(
                feature_dir,
                **{
                    "--prior-conclusion": "the item needs a schema change",
                    "--invalidating-evidence": 'quoted evidence: "..."',
                    "--must-satisfy": "resolve the schema gap",
                    "--provenance": "specs/009-multi-item-bounce/review.md",
                    "--cycle-count": "1",
                    "--carried-findings": json.dumps(["F-001: schema gap"]),
                }
            )
            out, err, rc = _capture(argv)
            self.assertEqual(rc, 0, msg=err)
            ack = json.loads(out)
            self.assertIn("seed_path", ack)
            seed_path = ack["seed_path"]
            self.assertEqual(
                seed_path, os.path.join(feature_dir, "fix-seed.json")
            )
            self.assertTrue(os.path.isfile(seed_path))

            with open(seed_path, encoding="utf-8") as fh:
                raw = json.load(fh)
            self.assertEqual(raw["source"], "fix")
            self.assertEqual(raw["target_stage"], "spec")
            self.assertEqual(raw["feature"], "009-multi-item-bounce")
            self.assertEqual(raw["prior_conclusion"], "the item needs a schema change")
            self.assertEqual(raw["invalidating_evidence"], 'quoted evidence: "..."')
            self.assertEqual(raw["must_satisfy"], "resolve the schema gap")
            self.assertEqual(
                raw["provenance"], "specs/009-multi-item-bounce/review.md"
            )
            self.assertEqual(raw["cycle_count"], 1)
            self.assertEqual(raw["carried_findings"], ["F-001: schema gap"])
            self.assertEqual(raw["seed_version"], SEED_SCHEMA_VERSION)

    def test_empty_must_satisfy_exits_2_and_writes_no_file(self):
        """MANDATORY case 2: empty --must-satisfy through the CLI path exits
        2 and writes NO file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "specs", "001-empty-must-satisfy")
            argv = _valid_cli_argv(feature_dir, **{"--must-satisfy": ""})
            out, err, rc = _capture(argv)
            self.assertEqual(rc, 2)
            self.assertIn("--must-satisfy", err)
            seed_path = os.path.join(feature_dir, "fix-seed.json")
            self.assertFalse(os.path.isfile(seed_path))
            # The handler validates before write_seed ever runs, so it must
            # not even create feature_dir.
            self.assertFalse(os.path.isdir(feature_dir))

    def test_empty_prior_conclusion_exits_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            argv = _valid_cli_argv(feature_dir, **{"--prior-conclusion": ""})
            out, err, rc = _capture(argv)
            self.assertEqual(rc, 2)
            self.assertFalse(os.path.isfile(os.path.join(feature_dir, "fix-seed.json")))

    def test_empty_invalidating_evidence_exits_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            argv = _valid_cli_argv(feature_dir, **{"--invalidating-evidence": ""})
            out, err, rc = _capture(argv)
            self.assertEqual(rc, 2)
            self.assertFalse(os.path.isfile(os.path.join(feature_dir, "fix-seed.json")))

    def test_empty_provenance_exits_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            argv = _valid_cli_argv(feature_dir, **{"--provenance": ""})
            out, err, rc = _capture(argv)
            self.assertEqual(rc, 2)
            self.assertFalse(os.path.isfile(os.path.join(feature_dir, "fix-seed.json")))

    def test_bad_cycle_count_exits_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            argv = _valid_cli_argv(feature_dir, **{"--cycle-count": "not-a-number"})
            out, err, rc = _capture(argv)
            self.assertEqual(rc, 2)
            self.assertIn("--cycle-count", err)
            self.assertFalse(os.path.isfile(os.path.join(feature_dir, "fix-seed.json")))

    def test_bad_carried_findings_not_json_exits_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            argv = _valid_cli_argv(feature_dir, **{"--carried-findings": "not json"})
            out, err, rc = _capture(argv)
            self.assertEqual(rc, 2)
            self.assertIn("--carried-findings", err)
            self.assertFalse(os.path.isfile(os.path.join(feature_dir, "fix-seed.json")))

    def test_bad_carried_findings_not_array_exits_2(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            argv = _valid_cli_argv(feature_dir, **{"--carried-findings": '{"a": 1}'})
            out, err, rc = _capture(argv)
            self.assertEqual(rc, 2)
            self.assertIn("--carried-findings", err)
            self.assertFalse(os.path.isfile(os.path.join(feature_dir, "fix-seed.json")))

    def test_cli_overwrites_in_place_on_second_run(self):
        """CLI-level companion to the module-level atomic-overwrite test."""
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            argv1 = _valid_cli_argv(feature_dir, **{"--must-satisfy": "first"})
            out1, err1, rc1 = _capture(argv1)
            self.assertEqual(rc1, 0, msg=err1)
            argv2 = _valid_cli_argv(feature_dir, **{"--must-satisfy": "second"})
            out2, err2, rc2 = _capture(argv2)
            self.assertEqual(rc2, 0, msg=err2)
            seed_path = os.path.join(feature_dir, "fix-seed.json")
            with open(seed_path, encoding="utf-8") as fh:
                raw = json.load(fh)
            self.assertEqual(raw["must_satisfy"], "second")


if __name__ == "__main__":
    unittest.main()
