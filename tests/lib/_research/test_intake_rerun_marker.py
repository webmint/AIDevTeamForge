"""Tests for research_helper finalize-handoff's intake-rerun marker and
check-seed-consumed (109-REENTRY-CHAIN-CONTINUITY-PLAN.md D4(b) / D6 / OQ-4).

Drives the real CLI via subprocess. Intake state is built through the real
setters (the _build_research_handoff factory from the find-handoffs tests,
which round-trips research_helper); seeds go through the real ReEntrySeed
schema. No mocks: the failing marker write is a real os.replace failure
(the marker path is made a directory).

_build_research_handoff is mirrored from tests/lib/_specify/test_find_handoffs_require.py,
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

RESEARCH_HELPER = LIB / "research_helper.py"
LANE_STAGE = "research"
OTHER_STAGE = "plan"
HANDOFF_NAME = "research-handoff.json"
MARKER_NAME = "intake-rerun.json"


def _run_research(argv, cwd=None):
    """Run research_helper.py; capture stdout/stderr/exit."""
    cmd = [sys.executable, str(RESEARCH_HELPER)] + list(argv)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def _build_research_handoff(devforge: Path, feature_dir: Path) -> Path:
    """Build a valid research-handoff.json under feature_dir via real setters.

    Returns feature_dir / "research-handoff.json" (created by
    finalize-handoff itself — feature_dir need not pre-exist).
    """
    df = str(devforge)
    _run_research(["--devforge-dir", df, "reset-memo"])
    _run_research(["--devforge-dir", df, "reset-report"])

    for dim, val in (
        ("symptom", "Auth token not refreshed on expiry"),
        ("affected-area", "services/auth/token_manager.py"),
        ("repro-or-current", "Log in; wait 1 hour; next request fails 401"),
        ("desired", "Token refreshed transparently before expiry"),
        ("scope", "one module"),
        ("unchanged-behavior", "logout flow unchanged"),
    ):
        _run_research([
            "--devforge-dir", df,
            "set-" + dim, "--value", val, "--state", "Clear",
        ])

    _run_research(["--devforge-dir", df, "detect-mode", "--override", "enhancement"])
    _run_research(["--devforge-dir", df, "set-topic", "--value", "auth-token-refresh"])
    _run_research([
        "--devforge-dir", df, "set-verbatim-prompt",
        "--value", "Auth token not refreshed on expiry in services/auth",
    ])
    _run_research(["--devforge-dir", df, "set-date", "--value", "2026-05-19"])

    for surface, file_line, relevance in (
        ("token manager", "services/auth/token_manager.py:55", "no refresh on expiry"),
        ("refresh client", "services/auth/refresh_client.py:12", "client code present"),
    ):
        _run_research([
            "--devforge-dir", df, "record-finding",
            "--surface", surface,
            "--file-line", file_line,
            "--relevance", relevance,
        ])

    for cause, falsifier, probe in (
        ("expiry timer missing", "add logging before request; verify timer", "yes"),
        ("refresh endpoint wrong URL", "check API docs vs code", "no"),
    ):
        _run_research([
            "--devforge-dir", df, "record-hypothesis",
            "--cause", cause,
            "--falsifier", falsifier,
            "--runtime-probe-needed", probe,
        ])

    _run_research([
        "--devforge-dir", df, "set-verify-step",
        "--probe", "add print before token check",
        "--reproduction", "run server; wait expiry; call API",
        "--discriminator", "if 401 = timer missing; if 200 = something else",
    ])

    for name, desc, complexity in (
        ("Option A: add refresh timer", "Add background timer to refresh token", "Low"),
        ("Option B: check on request", "Check expiry before each request", "Med"),
    ):
        r_approach = _run_research([
            "--devforge-dir", df, "set-approach",
            "--name", name,
            "--description", desc,
            "--addresses-hypotheses", "[]",
            "--does-not-cover", "[]",
            "--pros", "[]",
            "--cons", "[]",
            "--complexity", complexity,
        ])
        assert r_approach.returncode == 0, (
            "set-approach fixture setup failed: " + r_approach.stderr
        )

    r_recommended = _run_research([
        "--devforge-dir", df, "set-recommended-approach",
        "--name", "Option B: check on request",
        "--rationale", "Simpler; avoids background timer complexity",
        "--hypotheses-addressed", "[]",
        "--hypotheses-not-covered", "[]",
    ])
    assert r_recommended.returncode == 0, (
        "set-recommended-approach fixture setup failed: " + r_recommended.stderr
    )
    _run_research([
        "--devforge-dir", df, "set-constitution-constraints",
        "--rule", "Auth must be deterministic",
        "--impact", "No silent token failures",
    ])
    _run_research([
        "--devforge-dir", df, "set-complexity",
        "--codebase-changes", "Low", "--codebase-notes", "1 file",
        "--risk", "Low", "--risk-notes", "narrow",
        "--verify-cost", "Low", "--verify-notes", "unit test",
    ])
    _run_research([
        "--devforge-dir", df, "set-verdict", "--value", "Feasible",
    ])
    _run_research([
        "--devforge-dir", df, "set-summary",
        "--value", "Token refresh missing. Add expiry check before request.",
    ])
    _run_research([
        "--devforge-dir", df, "record-runner-up-framing",
        "--frame", "refresh endpoint wrong URL",
        "--falsifier", "check docs vs code",
        "--confidence-vs-primary", "lower",
    ])
    _run_research([
        "--devforge-dir", df, "record-fix-path-helper",
        "--helper-qn", "token_manager.refresh",
        "--file-line", "services/auth/token_manager.py:55",
    ])
    _run_research([
        "--devforge-dir", df, "record-inbound-caller",
        "--helper-qn", "token_manager.refresh",
        "--caller-qn", "request_interceptor.before_request",
        "--file-line", "services/auth/interceptor.py:10",
    ])
    _run_research([
        "--devforge-dir", df, "record-finding",
        "--surface", "runner-up cross-ref",
        "--file-line", "services/auth/refresh_client.py:1",
        "--relevance", "URL config key",
        "--framing", "runner-up",
    ])
    _run_research([
        "--devforge-dir", df, "set-probe-feasibility",
        "--data-shape-only", "false",
        "--auth-required", "false",
        "--network-dependent", "false",
        "--timing-dependent", "false",
        "--is-test-code", "false",
    ])
    # Plan 73 D7: declaration-exists guard requires set-evidence-lanes to
    # have been called before finalize-handoff.
    _run_research([
        "--devforge-dir", df, "set-evidence-lanes",
        "--static-graph", "false",
        "--text-search", "false",
        "--runtime-probe", "false",
        "--history", "false",
    ])

    r = _run_research([
        "--devforge-dir", df,
        "finalize-handoff",
        "--feature-dir", str(feature_dir),
    ])
    if r.returncode != 0:
        raise RuntimeError(
            "research finalize-handoff failed:\n"
            "stdout: {0}\nstderr: {1}".format(r.stdout, r.stderr)
        )
    return feature_dir / "research-handoff.json"


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


class IntakeRerunMarkerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.devforge = tmp / "df"
        self.devforge.mkdir()
        self.feature_dir = tmp / "specs" / "2026" / "10" / "feat"
        # Real setters + a first finalize (no spec.md yet).
        _build_research_handoff(self.devforge, self.feature_dir)
        self.handoff = self.feature_dir / HANDOFF_NAME
        self.marker = self.feature_dir / MARKER_NAME
        self.spec = self.feature_dir / "spec.md"
        self.seed = self.feature_dir / "grill-seed.json"

    def _finalize(self, *extra):
        return _run_research(["--devforge-dir", str(self.devforge), "finalize-handoff"]
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
        return _run_research(["--devforge-dir", str(self.devforge),
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
