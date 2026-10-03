"""Tests for discover_helper finalize-handoff's intake-rerun marker and
check-seed-consumed (109-REENTRY-CHAIN-CONTINUITY-PLAN.md D4(b) / D6 / OQ-4).

Drives the real CLI via subprocess. Intake state is built through the real
setters (the _build_discover_handoff factory from the find-handoffs tests,
which round-trips discover_helper); seeds go through the real ReEntrySeed
schema. No mocks: the failing marker write is a real os.replace failure
(the marker path is made a directory).

_build_discover_handoff is mirrored from tests/lib/_specify/test_find_handoffs_require.py,
not imported (house convention, see tests/lib/_configure/test_require_ticket.py).

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "src" / "devforge" / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from _shared.seed_schema import ReEntrySeed, SEED_SCHEMA_VERSION  # noqa: E402

DISCOVER_HELPER = LIB / "discover_helper.py"
LANE_STAGE = "discovery"
OTHER_STAGE = "plan"
HANDOFF_NAME = "discover-handoff.json"
MARKER_NAME = "intake-rerun.json"


def _run_discover(argv, cwd=None):
    """Run discover_helper.py; capture stdout/stderr/exit."""
    cmd = [sys.executable, str(DISCOVER_HELPER)] + list(argv)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def _build_discover_handoff(devforge: Path, feature_dir: Path) -> Path:
    """Build a valid discover-handoff.json under feature_dir via real setters.

    Returns feature_dir / "discover-handoff.json" (created by
    finalize-handoff itself — feature_dir need not pre-exist).
    """
    df = str(devforge)
    _run_discover(["--devforge-dir", df, "reset-memo"])
    _run_discover(["--devforge-dir", df, "reset-report"])
    _run_discover(["--devforge-dir", df, "set-topic", "--value", "audit-log-persistence"])
    _run_discover([
        "--devforge-dir", df, "set-verbatim-prompt",
        "--value", "Build an audit log persistence system for tracking state changes",
    ])
    _run_discover(["--devforge-dir", df, "set-date", "--value", "2026-05-20"])

    for dim, val in (
        ("functional-scope", "Persist audit events to DB"),
        ("users", "Backend services"),
        ("inputs-outputs", "AuditEvent -> DB"),
        ("integration-points", "ORM layer"),
        ("constraints", "100ms p99 write latency"),
        ("non-goals", "No real-time alerting"),
        ("success-criteria", "All state changes logged"),
        ("edge-cases", "DB down: queue and retry"),
    ):
        _run_discover([
            "--devforge-dir", df,
            "set-scope-" + dim, "--value", val, "--state", "Clear",
        ])

    _run_discover(["--devforge-dir", df, "set-summary", "--value", "Audit log persistence"])
    _run_discover(["--devforge-dir", df, "set-overall-fit", "--value", "Good"])
    _run_discover(["--devforge-dir", df, "set-effort-estimate", "--value", "Low"])
    _run_discover(["--devforge-dir", df, "set-fit-rationale", "--value", "Simple ORM ext"])
    _run_discover(["--devforge-dir", df, "set-verdict", "--value", "Worth pursuing"])
    _run_discover([
        "--devforge-dir", df, "record-integration-touchpoint",
        "--name", "ORM layer",
        "--module-path", "src/db/orm.py",
        "--reason", "Audit writes through ORM",
    ])
    _run_discover([
        "--devforge-dir", df, "set-design-option",
        "--name", "PostgreSQL table",
        "--shape", "ORM table",
        "--pros", '["Simple"]',
        "--cons", '["Single DB"]',
        "--complexity", "Low",
    ])
    _run_discover([
        "--devforge-dir", df, "set-recommended-option",
        "--name", "PostgreSQL table",
        "--rationale", "Lowest complexity for current scale",
    ])
    _run_discover([
        "--devforge-dir", df, "set-build-vs-buy",
        "--recommendation", "Build",
        "--build", "Extend ORM with new table",
        "--buy", "Third-party audit library",
        "--reasoning", "ORM already in place; avoid external dependency",
    ])
    # plan 73 D6: Build + zero internal prior-art hits is an absence-founded
    # conclusion -- finalize-handoff's declaration-exists guard requires a
    # record-absence-probe call before it will emit.
    _run_discover([
        "--devforge-dir", df, "record-absence-probe",
        "--claim", "no existing internal audit-log implementation",
        "--symbol", "AuditLogPersistence", "--path", "none",
        "--found", "false",
    ])
    _run_discover([
        "--devforge-dir", df, "set-derisk-plan",
        "--items", '["Spike: write load test against ORM layer before committing"]',
    ])
    _run_discover([
        "--devforge-dir", df, "set-recommendation",
        "--action", "Proceed with PostgreSQL table approach",
        "--next", "Run /specify audit-log-persistence",
    ])
    _run_discover([
        "--devforge-dir", df, "set-next-step-text",
        "--feature-dir", "specs/001-audit-log-persistence",
    ])

    r = _run_discover([
        "--devforge-dir", df,
        "finalize-handoff",
        "--feature-dir", str(feature_dir),
    ])
    if r.returncode != 0:
        raise RuntimeError(
            "discover finalize-handoff failed:\n"
            "stdout: {0}\nstderr: {1}".format(r.stdout, r.stderr)
        )
    return feature_dir / "discover-handoff.json"


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _seed_bytes(target_stage):
    seed = ReEntrySeed(
        seed_version=SEED_SCHEMA_VERSION,
        source="grill",
        target_stage=target_stage,
        feature="feat",
        prior_conclusion="The prior conclusion.",
        invalidating_evidence="grill.md: evidence.",
        must_satisfy="Resolve it.",
        cycle_count=1,
        carried_findings=[],
        provenance="specs/feat/grill.md",
    )
    return (json.dumps(dataclasses.asdict(seed), indent=2) + "\n").encode("utf-8")


class DiscoverIntakeRerunMarkerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.devforge = tmp / "df"
        self.devforge.mkdir()
        self.feature_dir = tmp / "specs" / "2026" / "10" / "feat"
        # Real setters + a first finalize (no spec.md yet).
        _build_discover_handoff(self.devforge, self.feature_dir)
        self.handoff = self.feature_dir / HANDOFF_NAME
        self.marker = self.feature_dir / MARKER_NAME
        self.spec = self.feature_dir / "spec.md"
        self.seed = self.feature_dir / "grill-seed.json"

    def _finalize(self, *extra):
        return _run_discover(["--devforge-dir", str(self.devforge), "finalize-handoff"]
                    + (list(extra) or ["--feature-dir", str(self.feature_dir)]))

    def _write_spec(self):
        self.spec.write_text("# Spec\n\nbody\n", encoding="utf-8")

    def _marker(self):
        return json.loads(self.marker.read_text(encoding="utf-8"))

    # 1
    def test_spec_present_writes_marker_and_two_lines(self):
        self._write_spec()
        r = self._finalize()
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(len(lines), 2, r.stdout)
        self.assertEqual(lines[0], "wrote: {0}".format(self.handoff.resolve()))
        self.assertEqual(lines[1], "wrote-marker: {0}".format(self.marker.resolve()))
        self.assertEqual(self._marker()["spec_sha256"], _sha(self.spec))

    # 1b
    def test_trailing_slash_feature_dir_marker_path_is_resolved(self):
        self._write_spec()
        r = self._finalize("--feature-dir", str(self.feature_dir) + "/")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(len(lines), 2, r.stdout)
        self.assertEqual(lines[1], "wrote-marker: {0}".format(self.marker.resolve()))

    # 2
    def test_spec_absent_single_line_no_marker(self):
        r = self._finalize()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines(),
                         ["wrote: {0}".format(self.handoff.resolve())])
        self.assertFalse(self.marker.exists())

    # 3
    def test_emit_handoff_json_never_writes_marker(self):
        self._write_spec()
        r = self._finalize("--emit-handoff-json",
                           str(self.feature_dir / "x-handoff.json"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("wrote-marker:", r.stdout)
        self.assertEqual(len(r.stdout.splitlines()), 1)
        self.assertFalse(self.marker.exists())

    # 4
    def test_rerun_marker_is_byte_identical(self):
        self._write_spec()
        self.assertEqual(self._finalize().returncode, 0)
        first = self.marker.read_bytes()
        self.assertEqual(self._finalize().returncode, 0)
        self.assertEqual(first, self.marker.read_bytes())

    # 5
    def test_matching_seed_hash_recorded_and_seed_untouched(self):
        self._write_spec()
        raw = _seed_bytes(LANE_STAGE)
        self.seed.write_bytes(raw)
        r = self._finalize()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self._marker()["seed_sha256"],
                         hashlib.sha256(raw).hexdigest())
        self.assertEqual(self.seed.read_bytes(), raw)

    def test_other_stage_seed_gives_null_seed_hash(self):
        self._write_spec()
        raw = _seed_bytes(OTHER_STAGE)
        self.seed.write_bytes(raw)
        self.assertEqual(self._finalize().returncode, 0)
        self.assertIsNone(self._marker()["seed_sha256"])
        self.assertEqual(self.seed.read_bytes(), raw)

    def test_no_seed_gives_null_seed_hash(self):
        self._write_spec()
        self.assertEqual(self._finalize().returncode, 0)
        self.assertIsNone(self._marker()["seed_sha256"])

    def test_unreadable_seed_gives_null_seed_hash(self):
        self._write_spec()
        raw = b"{not json"
        self.seed.write_bytes(raw)
        self.assertEqual(self._finalize().returncode, 0)
        self.assertIsNone(self._marker()["seed_sha256"])
        self.assertEqual(self.seed.read_bytes(), raw)

    # 6
    def test_marker_write_failure_exits_3_and_keeps_handoff(self):
        self._write_spec()
        self.marker.mkdir()  # os.replace(file -> dir) fails for real
        r = self._finalize()
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn("intake-rerun.json", r.stderr)
        self.assertIn("could not write", r.stderr)
        self.assertIn("handoff is kept", r.stderr)
        json.loads(self.handoff.read_text(encoding="utf-8"))
        self.assertEqual(r.stdout.splitlines(),
                         ["wrote: {0}".format(self.handoff.resolve())])
        self.assertNotIn("wrote-marker:", r.stdout)
        leftovers = [p.name for p in self.feature_dir.iterdir()
                     if p.name.startswith(".tmp-")]
        self.assertEqual(leftovers, [])

    # 7
    def _check(self, seed_path):
        return _run_discover(["--devforge-dir", str(self.devforge),
                     "check-seed-consumed", "--seed", str(seed_path)])

    def test_check_seed_consumed_matrix(self):
        self._write_spec()
        raw = _seed_bytes(LANE_STAGE)
        self.seed.write_bytes(raw)
        # No marker yet.
        r = self._check(self.seed)
        self.assertEqual((r.returncode, r.stdout), (0, "not-consumed\n"))
        self.assertEqual(self._finalize().returncode, 0)
        r = self._check(self.seed)
        self.assertEqual((r.returncode, r.stdout), (0, "consumed\n"))
        # Marker untouched by the check.
        before = self.marker.read_bytes()
        self._check(self.seed)
        self.assertEqual(before, self.marker.read_bytes())
        # Seed bytes change.
        self.seed.write_bytes(raw + b"\n")
        r = self._check(self.seed)
        self.assertEqual((r.returncode, r.stdout), (0, "not-consumed\n"))

    def test_check_seed_consumed_null_seed_hash_marker(self):
        self._write_spec()
        self.assertEqual(self._finalize().returncode, 0)  # no seed yet
        self.seed.write_bytes(_seed_bytes(LANE_STAGE))
        r = self._check(self.seed)
        self.assertEqual((r.returncode, r.stdout), (0, "not-consumed\n"))

    def test_check_seed_consumed_missing_seed_exits_2(self):
        r = self._check(self.feature_dir / "nope-seed.json")
        self.assertEqual(r.returncode, 2)
        self.assertIn("seed file not found", r.stderr)
        self.assertEqual(r.stdout, "")


if __name__ == "__main__":
    unittest.main()
