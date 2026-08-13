"""Tests for discover_helper record-absence-probe + its finalize-handoff
declaration-exists guard (plan 73 D6 -- the /discover absence-claim
provenance lane).

Covers:
  - record-absence-probe persists {claim, symbol, path, found,
    deleted_commit_sha, deleted_commit_subject} rows to
    discover-report.json (report.absence_probes). Append-only, no dedup.
  - --found true requires --deleted-commit-sha (7-40 hex) and
    --deleted-commit-subject (non-empty); --found false forbids both.
  - --symbol / --path: either may be the literal "none", but not both.
  - finalize-handoff's declaration-exists guard fires ONLY when
    build_vs_buy.recommendation == "Build" with zero internal prior-art
    hits recorded (requires_absence_probe), and ONLY checks that
    record-absence-probe was called at least once -- identically whether
    the recorded row's --found is true or false. A survey that never
    makes an absence-founded Build conclusion (Buy/Hybrid recommendation,
    or a Build grounded in an internal prior-art hit) is unaffected.

Subprocess pattern (matches test_discover_design_anchor.py /
test_discover_helper.py): each test runs in its own
tempfile.TemporaryDirectory, invoking the real discover_helper.py CLI --
no hand-authored handoff.json fixtures.

Stdlib only. Python 3.8+.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "discover_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))


def _run(argv, cwd=None):
    """Run discover_helper.py with argv; capture stdout/stderr/exit."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(argv),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def _read_report(devforge):
    return json.loads((Path(devforge) / "discover-report.json").read_text())


# ---------------------------------------------------------------------------
# record-absence-probe setter.
# ---------------------------------------------------------------------------


class TestRecordAbsenceProbe(unittest.TestCase):
    def test_found_false_records_row_with_null_commit_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing catalog audit-log utility",
                "--symbol", "AuditLogWriter",
                "--path", "none",
                "--found", "false",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(len(report["absence_probes"]), 1)
            row = report["absence_probes"][0]
            self.assertEqual(row["claim"], "no existing catalog audit-log utility")
            self.assertEqual(row["symbol"], "AuditLogWriter")
            self.assertEqual(row["path"], "none")
            self.assertIs(row["found"], False)
            self.assertIsNone(row["deleted_commit_sha"])
            self.assertIsNone(row["deleted_commit_subject"])

    def test_found_true_requires_and_records_commit_sha_and_subject(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing legacy-widget collapse component",
                "--symbol", "isLegacyItems",
                "--path", "none",
                "--found", "true",
                "--deleted-commit-sha", "ff93f35dd",
                "--deleted-commit-subject", "Strip isLegacyItems from parent",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            row = report["absence_probes"][0]
            self.assertIs(row["found"], True)
            self.assertEqual(row["deleted_commit_sha"], "ff93f35dd")
            self.assertEqual(row["deleted_commit_subject"], "Strip isLegacyItems from parent")

    def test_found_true_missing_sha_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing X", "--symbol", "X", "--path", "none",
                "--found", "true",
                "--deleted-commit-subject", "subject only",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("--deleted-commit-sha is required", r.stderr)

    def test_found_true_missing_subject_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing X", "--symbol", "X", "--path", "none",
                "--found", "true",
                "--deleted-commit-sha", "abc1234",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("--deleted-commit-subject is required", r.stderr)

    def test_found_true_invalid_sha_format_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing X", "--symbol", "X", "--path", "none",
                "--found", "true",
                "--deleted-commit-sha", "not-a-sha",
                "--deleted-commit-subject", "subject",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("must be a 7-40 char hex commit SHA", r.stderr)

    def test_found_false_with_sha_present_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing X", "--symbol", "X", "--path", "none",
                "--found", "false",
                "--deleted-commit-sha", "abc1234",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("--deleted-commit-sha must be omitted", r.stderr)

    def test_found_false_with_subject_present_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing X", "--symbol", "X", "--path", "none",
                "--found", "false",
                "--deleted-commit-subject", "stray subject",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("--deleted-commit-subject must be omitted", r.stderr)

    def test_symbol_and_path_both_none_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing X",
                "--symbol", "none", "--path", "none",
                "--found", "false",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("cannot both be 'none'", r.stderr)

    def test_path_only_probe_accepted_when_symbol_is_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing X",
                "--symbol", "none", "--path", "pkg-widget-family/",
                "--found", "false",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(report["absence_probes"][0]["path"], "pkg-widget-family/")

    def test_symbol_and_path_both_capitalized_none_exits_2(self):
        """The 'none' sentinel match is case-insensitive -- 'None'/'NONE'
        must trip the same guard as lowercase 'none', not silently pass
        through as though it named a real git target."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing X",
                "--symbol", "None", "--path", "NONE",
                "--found", "false",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("cannot both be 'none'", r.stderr)

    def test_capitalized_none_canonicalized_to_lowercase_on_store(self):
        """A capitalized sentinel on the non-'none' side of the pair is
        accepted (only one of the two is 'none') AND canonicalized to
        lowercase 'none' before storage -- a stored row must never carry
        'None'/'NONE' verbatim."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing X",
                "--symbol", "None", "--path", "pkg-widget-family/",
                "--found", "false",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            row = report["absence_probes"][0]
            self.assertEqual(row["symbol"], "none")
            self.assertEqual(row["path"], "pkg-widget-family/")

    def test_empty_claim_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "   ", "--symbol", "X", "--path", "none",
                "--found", "false",
            ])
            self.assertEqual(r.returncode, 2)

    def test_multiple_calls_append_no_dedup(self):
        """Pure append: two calls with identical arguments produce two rows
        (unlike record-literal-archaeology's (literal, file_line) dedup --
        nothing downstream reads absence_probes for per-row correctness,
        only for presence, so no dedup key is needed)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            argv = [
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing X", "--symbol", "X", "--path", "none",
                "--found", "false",
            ]
            r1 = _run(argv)
            r2 = _run(argv)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            report = _read_report(devforge)
            self.assertEqual(len(report["absence_probes"]), 2)


# ---------------------------------------------------------------------------
# finalize-handoff declaration-exists guard — real producer round trip.
# ---------------------------------------------------------------------------


def _build_worth_pursuing_state(devforge, recommendation="Build", internal_prior_art=False):
    """Populate a minimal valid 'Worth pursuing' state via real setters.

    recommendation: build_vs_buy.recommendation ("Build" / "Buy" / "Hybrid").
    internal_prior_art: when True, records one internal:<path> prior-art
    hit BEFORE recommended-option/build-vs-buy, and the recommended-option
    rationale cites that path -- satisfying cmd_verify's Rule G cite-back
    requirement as well as requires_absence_probe's exclusion (a "Build"
    grounded in an internal hit is not a bare absence claim).
    """
    _run(["--devforge-dir", str(devforge), "reset-memo"])
    _run(["--devforge-dir", str(devforge), "reset-report"])

    _run(["--devforge-dir", str(devforge), "set-topic", "--value", "Audit log persistence"])
    _run([
        "--devforge-dir", str(devforge), "set-verbatim-prompt",
        "--value", "Build an audit log persistence system for tracking state changes",
    ])
    _run(["--devforge-dir", str(devforge), "set-date", "--value", "2026-08-12"])

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
        _run([
            "--devforge-dir", str(devforge),
            "set-scope-" + dim, "--value", val, "--state", "Clear",
        ])

    rationale = "Lowest complexity for current scale"
    if internal_prior_art:
        _run([
            "--devforge-dir", str(devforge), "record-prior-art",
            "--reference", "AuditLogBase",
            "--kind", "pattern",
            "--relevance", "internal -- existing implementation of audit logging",
            "--source", "internal:src/db/audit_log_base.py",
        ])
        # Must cite the FULL "internal:<path>" source string, not just the
        # bare path -- PlanSeeds.__post_init__'s G-mirror check (stricter
        # than cmd_verify's Rule G, which strips the "internal:" prefix
        # before its substring test) requires the raw cited_pattern.source
        # verbatim in the rationale.
        rationale = "Extend existing internal:src/db/audit_log_base.py implementation"

    _run([
        "--devforge-dir", str(devforge), "set-design-option",
        "--name", "PostgreSQL table", "--shape", "ORM table",
        "--pros", '["Simple"]', "--cons", '["Single DB"]', "--complexity", "Low",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-recommended-option",
        "--name", "PostgreSQL table", "--rationale", rationale,
    ])
    _run([
        "--devforge-dir", str(devforge), "set-build-vs-buy",
        "--build", "Extend ORM with new table",
        "--buy", "Third-party audit library",
        "--recommendation", recommendation,
        "--reasoning", "ORM already in place; avoid external dependency",
    ])
    _run(["--devforge-dir", str(devforge), "set-overall-fit", "--value", "Good"])
    _run(["--devforge-dir", str(devforge), "set-effort-estimate", "--value", "Low"])
    _run(["--devforge-dir", str(devforge), "set-fit-rationale", "--value", "Straightforward ORM extension"])
    _run([
        "--devforge-dir", str(devforge), "record-integration-touchpoint",
        "--name", "ORM layer", "--module-path", "src/db/orm.py",
        "--reason", "Audit writes through ORM",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-derisk-plan",
        "--items", '["Spike: write load test against ORM layer before committing"]',
    ])
    _run(["--devforge-dir", str(devforge), "set-verdict", "--value", "Worth pursuing"])
    _run([
        "--devforge-dir", str(devforge), "set-summary",
        "--value", "Audit log persistence system",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-recommendation",
        "--action", "Proceed with PostgreSQL table approach",
        "--next", "Run /specify audit-log-persistence",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-next-step-text",
        "--feature-dir", "specs/001-audit-log-persistence",
    ])


class TestFinalizeHandoffAbsenceProbeGuard(unittest.TestCase):
    def test_build_no_prior_art_no_probe_rejected(self):
        """Absence-founded Build conclusion with zero absence_probes rows -> exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_worth_pursuing_state(devforge, recommendation="Build")
            emit = Path(tmp) / "out.handoff.json"
            r = _run([
                "--devforge-dir", str(devforge), "finalize-handoff",
                "--emit-handoff-json", str(emit),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("record-absence-probe", r.stderr)
            self.assertFalse(emit.is_file())

    def test_build_no_prior_art_with_found_false_probe_accepted(self):
        """A --found false probe satisfies the guard: 'found nothing' is a
        first-class outcome, not an absent record."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_worth_pursuing_state(devforge, recommendation="Build")
            _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing internal audit-log implementation",
                "--symbol", "AuditLogPersistence", "--path", "none",
                "--found", "false",
            ])
            emit = Path(tmp) / "out.handoff.json"
            r = _run([
                "--devforge-dir", str(devforge), "finalize-handoff",
                "--emit-handoff-json", str(emit),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(emit.is_file())

    def test_build_no_prior_art_with_found_true_probe_accepted(self):
        """A --found true probe (a prior deletion WAS found) satisfies the
        guard identically to a --found false probe -- the guard is a
        call-happened check, never a value check. The author's Build
        conclusion stands even though a deliberate deletion exists."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_worth_pursuing_state(devforge, recommendation="Build")
            _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing internal audit-log implementation",
                "--symbol", "AuditLogPersistence", "--path", "none",
                "--found", "true",
                "--deleted-commit-sha", "b925444ae",
                "--deleted-commit-subject", "Remove legacy audit-log prototype",
            ])
            emit = Path(tmp) / "out.handoff.json"
            r = _run([
                "--devforge-dir", str(devforge), "finalize-handoff",
                "--emit-handoff-json", str(emit),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(emit.is_file())

    def test_buy_recommendation_no_probe_unaffected(self):
        """Not an absence-founded conclusion (Buy, not Build) -> guard never
        fires; finalize-handoff succeeds with zero absence_probes rows."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_worth_pursuing_state(devforge, recommendation="Buy")
            emit = Path(tmp) / "out.handoff.json"
            r = _run([
                "--devforge-dir", str(devforge), "finalize-handoff",
                "--emit-handoff-json", str(emit),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(report["absence_probes"], [])

    def test_hybrid_recommendation_no_probe_unaffected(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_worth_pursuing_state(devforge, recommendation="Hybrid")
            emit = Path(tmp) / "out.handoff.json"
            r = _run([
                "--devforge-dir", str(devforge), "finalize-handoff",
                "--emit-handoff-json", str(emit),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_build_with_internal_prior_art_no_probe_unaffected(self):
        """A Build recommendation grounded in >=1 internal prior-art hit is
        NOT a bare absence claim (Rule G already forces citing the
        existing code) -- the guard does not require a probe here."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_worth_pursuing_state(
                devforge, recommendation="Build", internal_prior_art=True,
            )
            emit = Path(tmp) / "out.handoff.json"
            r = _run([
                "--devforge-dir", str(devforge), "finalize-handoff",
                "--emit-handoff-json", str(emit),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(report["absence_probes"], [])


# ---------------------------------------------------------------------------
# render -- ## Absence Probes section (coordinator MEDIUM finding).
#
# Conditional section, mirroring _research/_render.py's "## Literal
# Archaeology" pattern: renders only when report.absence_probes is
# non-empty. Placed immediately after "## Build vs Buy" in cmd_render
# (_cmds_core.py) -- these rows are the provenance trail FOR that
# section's conclusion.
# ---------------------------------------------------------------------------


class TestRenderAbsenceProbes(unittest.TestCase):
    def test_survey_with_probes_renders_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_worth_pursuing_state(devforge, recommendation="Build")
            _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing internal audit-log implementation",
                "--symbol", "AuditLogPersistence", "--path", "none",
                "--found", "true",
                "--deleted-commit-sha", "b925444ae",
                "--deleted-commit-subject", "Remove legacy audit-log prototype",
            ])
            r = _run(["--devforge-dir", str(devforge), "render"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("## Absence Probes", r.stdout)
            self.assertIn("no existing internal audit-log implementation", r.stdout)
            self.assertIn("AuditLogPersistence", r.stdout)
            self.assertIn("b925444ae", r.stdout)
            self.assertIn("Remove legacy audit-log prototype", r.stdout)
            self.assertIn("Yes", r.stdout)

    def test_survey_without_probes_renders_no_section(self):
        """A survey that never made an absence-founded claim (Buy, not
        Build) never calls record-absence-probe -- the section must be
        OMITTED, not rendered empty (mirrors _research's conditional
        Literal Archaeology, not D7's unconditional Evidence Lanes)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_worth_pursuing_state(devforge, recommendation="Buy")
            r = _run(["--devforge-dir", str(devforge), "render"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("## Absence Probes", r.stdout)

    def test_found_false_row_renders_not_skipped(self):
        """A --found false row is a real, rendered row -- not omitted or
        collapsed -- proving the section doesn't silently drop the
        'found nothing' outcome."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_worth_pursuing_state(devforge, recommendation="Build")
            _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing internal audit-log implementation",
                "--symbol", "AuditLogPersistence", "--path", "none",
                "--found", "false",
            ])
            r = _run(["--devforge-dir", str(devforge), "render"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("## Absence Probes", r.stdout)
            self.assertIn("no existing internal audit-log implementation", r.stdout)
            self.assertIn("AuditLogPersistence", r.stdout)
            self.assertIn("No", r.stdout)

    def test_section_placed_immediately_after_build_vs_buy(self):
        """Pins the placement decision: Absence Probes appears between
        Build vs Buy and Derisk Plan, not merely present anywhere."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_worth_pursuing_state(devforge, recommendation="Build")
            _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing internal audit-log implementation",
                "--symbol", "AuditLogPersistence", "--path", "none",
                "--found", "false",
            ])
            r = _run(["--devforge-dir", str(devforge), "render"])
            self.assertEqual(r.returncode, 0, r.stderr)
            bvb_idx = r.stdout.index("## Build vs Buy")
            probes_idx = r.stdout.index("## Absence Probes")
            derisk_idx = r.stdout.index("## Derisk Plan")
            self.assertTrue(bvb_idx < probes_idx < derisk_idx)


# ---------------------------------------------------------------------------
# Back-compat axis (a) -- missing-field defaulting on old discover-report.json.
#
# absence_probes never rides handoff_schema.Handoff (it lives only in
# discover-report.json, discover's own mid-investigation state -- see the
# module docstring on _cmds_absence.requires_absence_probe), so axis (b)
# ("previously-valid combinations still validating on reconstruction") does
# not apply here: _specify/_cmds_handoff.py's two
# _dict_to_dataclass(discover_handoff_schema.Handoff, ...) call sites
# (_import_handoff_discover, _try_discover_hit) reconstruct a schema this
# phase never touched. Only axis (a) applies, to discover-report.json
# itself: a report.json written by pre-plan-73 code has no "absence_probes"
# key at all (_load_report does a bare json.loads, no default-merge) -- both
# the setter and the guard must handle that missing key correctly.
# ---------------------------------------------------------------------------


class TestBackCompatMissingAbsenceProbesKey(unittest.TestCase):
    def _strip_absence_probes_key(self, devforge):
        report_path = Path(devforge) / "discover-report.json"
        data = json.loads(report_path.read_text(encoding="utf-8"))
        del data["absence_probes"]
        report_path.write_text(json.dumps(data), encoding="utf-8")

    def test_setter_appends_to_stored_report_missing_the_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_worth_pursuing_state(devforge, recommendation="Buy")
            self._strip_absence_probes_key(devforge)

            r = _run([
                "--devforge-dir", str(devforge), "record-absence-probe",
                "--claim", "no existing X", "--symbol", "X", "--path", "none",
                "--found", "false",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(len(report["absence_probes"]), 1)

    def test_guard_fires_against_stored_report_missing_the_key(self):
        """A missing key reads as 'no probes recorded', same as an empty
        list -- the guard's `report.get("absence_probes")` falsy-check
        treats None and [] identically."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_worth_pursuing_state(devforge, recommendation="Build")
            self._strip_absence_probes_key(devforge)

            emit = Path(tmp) / "out.handoff.json"
            r = _run([
                "--devforge-dir", str(devforge), "finalize-handoff",
                "--emit-handoff-json", str(emit),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("record-absence-probe", r.stderr)
            self.assertFalse(emit.is_file())


if __name__ == "__main__":
    unittest.main()
