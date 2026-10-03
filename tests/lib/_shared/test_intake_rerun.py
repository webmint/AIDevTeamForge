"""Tests for src/devforge/lib/_shared/intake_rerun.py.

Coverage: file_sha256, compose_marker, write_marker, marker_admits,
seed_consumed (109-REENTRY-CHAIN-CONTINUITY-PLAN.md D3/D6/OQ-4).  Seed
fixtures are built through the real _shared.seed_schema.ReEntrySeed with the
same serialization the grill writer uses (dataclasses.asdict + json.dumps).
"""

import dataclasses
import hashlib
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

from _shared import intake_rerun as ir  # noqa: E402
from _shared.seed_schema import ReEntrySeed, SEED_SCHEMA_VERSION  # noqa: E402


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_seed(feature_dir: Path, target_stage: str) -> Path:
    seed = ReEntrySeed(
        seed_version=SEED_SCHEMA_VERSION,
        source="grill",
        target_stage=target_stage,
        feature=feature_dir.name,
        prior_conclusion="Prior conclusion.",
        invalidating_evidence="grill.md: conflict.",
        must_satisfy="Resolve the conflict.",
        cycle_count=1,
        carried_findings=[],
        provenance="specs/{0}/grill.md".format(feature_dir.name),
    )
    p = feature_dir / "grill-seed.json"
    p.write_text(json.dumps(dataclasses.asdict(seed), indent=2) + "\n", encoding="utf-8")
    return p


def _snapshot(d: Path):
    return {p.name: p.read_bytes() for p in sorted(d.iterdir()) if p.is_file()}


class _TmpCase(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.d = Path(self._td.name) / "feat"
        self.d.mkdir()
        self.spec = self.d / "spec.md"
        self.spec.write_text("# spec\n", encoding="utf-8")
        self.marker = self.d / ir.MARKER_FILENAME


class TestConstants(unittest.TestCase):
    def test_constants(self):
        self.assertEqual(ir.MARKER_FILENAME, "intake-rerun.json")
        self.assertFalse(ir.MARKER_FILENAME.endswith("-seed.json"))
        self.assertEqual(ir.MARKER_VERSION, 1)
        self.assertEqual(ir.SEED_FILENAME, "grill-seed.json")
        self.assertEqual(ir.INTAKE_SEED_STAGES, ("research", "discovery"))


class TestFileSha256(_TmpCase):
    def test_matches_hashlib_over_raw_bytes(self):
        data = b"\x00\xffraw\r\nbytes"
        p = self.d / "x.bin"
        p.write_bytes(data)
        self.assertEqual(ir.file_sha256(p), hashlib.sha256(data).hexdigest())

    def test_missing_file_raises_oserror(self):
        with self.assertRaises(OSError):
            ir.file_sha256(self.d / "nope")


class TestComposeMarker(unittest.TestCase):
    def test_with_seed_hash(self):
        self.assertEqual(
            ir.compose_marker("a" * 64, "b" * 64),
            {"marker_version": 1, "seed_sha256": "b" * 64, "spec_sha256": "a" * 64},
        )

    def test_without_seed_hash(self):
        self.assertEqual(
            ir.compose_marker("a" * 64, None),
            {"marker_version": 1, "seed_sha256": None, "spec_sha256": "a" * 64},
        )


class TestMarkerAdmits(_TmpCase):
    def test_1_written_marker_reads_back_true(self):
        _write_seed(self.d, "research")
        ir.write_marker(self.d, "research")
        self.assertTrue(ir.marker_admits(self.d))

    def test_2_matching_hash_true(self):
        self.marker.write_text(
            json.dumps({"spec_sha256": _sha(b"# spec\n")}), encoding="utf-8")
        self.assertTrue(ir.marker_admits(self.d))

    def test_3_diverged_hash_false(self):
        ir.write_marker(self.d, "research")
        self.spec.write_text("# spec changed\n", encoding="utf-8")
        self.assertFalse(ir.marker_admits(self.d))

    def test_4_marker_absent_false(self):
        self.assertFalse(ir.marker_admits(self.d))

    def test_5a_corrupt_json_false(self):
        self.marker.write_text("{not json", encoding="utf-8")
        self.assertFalse(ir.marker_admits(self.d))

    def test_5b_undecodable_bytes_false(self):
        self.marker.write_bytes(b"\xff\xfe\x00\x80")
        self.assertFalse(ir.marker_admits(self.d))

    def test_5c_directory_at_marker_path_false(self):
        self.marker.mkdir()
        self.assertFalse(ir.marker_admits(self.d))

    def test_5d_not_a_dict_false(self):
        self.marker.write_text("[1, 2]", encoding="utf-8")
        self.assertFalse(ir.marker_admits(self.d))

    def test_5e_non_str_spec_sha_false(self):
        self.marker.write_text(json.dumps({"spec_sha256": 5}), encoding="utf-8")
        self.assertFalse(ir.marker_admits(self.d))

    def test_6_spec_absent_false(self):
        ir.write_marker(self.d, "research")
        self.spec.unlink()
        self.assertFalse(ir.marker_admits(self.d))

    def test_7_byte_identical_rerender_still_true(self):
        ir.write_marker(self.d, "research")
        self.spec.write_bytes(self.spec.read_bytes())
        self.assertTrue(ir.marker_admits(self.d))

    def test_does_not_require_marker_version(self):
        self.marker.write_text(
            json.dumps({"spec_sha256": _sha(b"# spec\n"), "marker_version": 99}),
            encoding="utf-8")
        self.assertTrue(ir.marker_admits(self.d))

    def test_read_only(self):
        _write_seed(self.d, "research")
        ir.write_marker(self.d, "research")
        before = _snapshot(self.d)
        ir.marker_admits(self.d)
        self.assertEqual(_snapshot(self.d), before)


class TestSeedConsumed(_TmpCase):
    def test_matching_seed_true(self):
        seed = _write_seed(self.d, "research")
        ir.write_marker(self.d, "research")
        self.assertTrue(ir.seed_consumed(seed))

    def test_different_seed_bytes_false(self):
        seed = _write_seed(self.d, "research")
        ir.write_marker(self.d, "research")
        seed.write_text(seed.read_text(encoding="utf-8") + " ", encoding="utf-8")
        self.assertFalse(ir.seed_consumed(seed))

    def test_marker_absent_false(self):
        seed = _write_seed(self.d, "research")
        self.assertFalse(ir.seed_consumed(seed))

    def test_marker_corrupt_unreadable_not_dict_false(self):
        seed = _write_seed(self.d, "research")
        for payload in (b"{bad", b"\xff\xfe\x80", b"[1]"):
            self.marker.write_bytes(payload)
            self.assertFalse(ir.seed_consumed(seed), payload)
        self.marker.unlink()
        self.marker.mkdir()
        self.assertFalse(ir.seed_consumed(seed))

    def test_null_seed_hash_false(self):
        seed = _write_seed(self.d, "spec")  # non-matching stage -> null hash
        ir.write_marker(self.d, "research")
        self.assertIsNone(json.loads(self.marker.read_text())["seed_sha256"])
        self.assertFalse(ir.seed_consumed(seed))

    def test_absent_or_nonstr_seed_hash_false(self):
        seed = _write_seed(self.d, "research")
        self.marker.write_text(json.dumps({"spec_sha256": "x"}), encoding="utf-8")
        self.assertFalse(ir.seed_consumed(seed))
        self.marker.write_text(json.dumps({"seed_sha256": 7}), encoding="utf-8")
        self.assertFalse(ir.seed_consumed(seed))

    def test_seed_unreadable_false(self):
        ir.write_marker(self.d, "research")
        self.assertFalse(ir.seed_consumed(self.d / "grill-seed.json"))

    def test_read_only(self):
        seed = _write_seed(self.d, "research")
        ir.write_marker(self.d, "research")
        before = _snapshot(self.d)
        ir.seed_consumed(seed)
        self.assertEqual(_snapshot(self.d), before)


class TestPathologicalNesting(_TmpCase):
    def test_deeply_nested_marker_not_admitted_nor_consumed(self):
        seed = _write_seed(self.d, "research")
        self.marker.write_bytes(b"[" * 200000)
        self.assertFalse(ir.marker_admits(self.d))
        self.assertFalse(ir.seed_consumed(seed))

    def test_deeply_nested_seed_writes_marker_with_null_seed_hash(self):
        (self.d / "grill-seed.json").write_bytes(b"[" * 200000)
        self.assertIsNotNone(ir.write_marker(self.d, "research"))
        rec = json.loads(self.marker.read_text(encoding="utf-8"))
        self.assertIsNone(rec["seed_sha256"])
        self.assertEqual(rec["spec_sha256"], _sha(b"# spec\n"))


class TestWriteMarker(_TmpCase):
    def _record(self):
        return json.loads(self.marker.read_text(encoding="utf-8"))

    def test_spec_absent_returns_none_dir_unchanged(self):
        self.spec.unlink()
        _write_seed(self.d, "research")
        before = _snapshot(self.d)
        self.assertIsNone(ir.write_marker(self.d, "research"))
        self.assertEqual(_snapshot(self.d), before)
        self.assertEqual(sorted(os.listdir(self.d)), ["grill-seed.json"])

    def test_seed_absent_null_seed_hash(self):
        path = ir.write_marker(self.d, "research")
        self.assertEqual(path, self.marker.resolve())
        self.assertEqual(self._record(), {
            "marker_version": 1, "seed_sha256": None, "spec_sha256": _sha(b"# spec\n")})

    def test_seed_corrupt_or_unreadable_null(self):
        seed = self.d / "grill-seed.json"
        for payload in (b"{bad", b"\xff\xfe\x80", b"[]", b'"s"'):
            seed.write_bytes(payload)
            ir.write_marker(self.d, "research")
            self.assertIsNone(self._record()["seed_sha256"], payload)
        seed.unlink()
        seed.mkdir()
        ir.write_marker(self.d, "research")
        self.assertIsNone(self._record()["seed_sha256"])

    def test_non_matching_target_stage_null(self):
        _write_seed(self.d, "spec")
        ir.write_marker(self.d, "research")
        self.assertIsNone(self._record()["seed_sha256"])

    def test_matching_stage_records_raw_bytes_hash(self):
        for stage in ("research", "discovery"):
            seed = _write_seed(self.d, stage)
            ir.write_marker(self.d, stage)
            self.assertEqual(self._record()["seed_sha256"], _sha(seed.read_bytes()))

    def test_twice_byte_identical(self):
        _write_seed(self.d, "research")
        ir.write_marker(self.d, "research")
        first = self.marker.read_bytes()
        ir.write_marker(self.d, "research")
        self.assertEqual(self.marker.read_bytes(), first)

    def test_content_is_exact_serialization(self):
        seed = _write_seed(self.d, "research")
        ir.write_marker(self.d, "research")
        expected = json.dumps(
            {"marker_version": 1, "seed_sha256": _sha(seed.read_bytes()),
             "spec_sha256": _sha(b"# spec\n")},
            indent=2, sort_keys=True) + "\n"
        self.assertEqual(self.marker.read_text(encoding="utf-8"), expected)

    def test_invalid_stage_value_error(self):
        for bad in ("spec", "plan", "", None):
            with self.assertRaises(ValueError):
                ir.write_marker(self.d, bad)
        self.assertFalse(self.marker.exists())

    def test_failing_replace_propagates_and_cleans_temp(self):
        before = sorted(os.listdir(self.d))
        with mock.patch("_shared.intake_rerun.os.replace", side_effect=OSError("boom")):
            with self.assertRaises(OSError):
                ir.write_marker(self.d, "research")
        self.assertEqual(sorted(os.listdir(self.d)), before)

    def test_seed_never_modified(self):
        seed = _write_seed(self.d, "research")
        before = seed.read_bytes()
        ir.write_marker(self.d, "research")
        self.assertEqual(seed.read_bytes(), before)

    def test_no_temp_left_on_success(self):
        ir.write_marker(self.d, "research")
        self.assertEqual(sorted(os.listdir(self.d)), ["intake-rerun.json", "spec.md"])


if __name__ == "__main__":
    unittest.main()
