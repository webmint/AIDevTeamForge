"""Tests for specify_helper finalize-handoff (cmd_finalize_handoff).

Covers:
- Round-trip: fully-populated Approved state -> handoff.json -> reconstruct
  via _dict_to_dataclass(specify_handoff_schema.Handoff, ...) and assert
  key fields survive.
- Default emit path: specs/{number}-{slug}/handoff.json when --emit-handoff-json
  omitted.
- Status handling: status='Draft' succeeds (normal emit); status outside
  SPEC_STATUS_ENUM fails schema validation.
- No-upstream provenance: source.handoff_path=None + handoff_kind=None ->
  valid handoff with all-None provenance.
- Provenance completed_at mapping: research kind pulls research_completed_at;
  discover kind pulls discover_completed_at.
- --completed-at injection produces deterministic specify_completed_at.

Design notes:
- cmd_finalize_handoff is called directly with a fake argparse.Namespace.
- State written to a temp .devforge/specify-state.json.
- Output path is a temp directory to avoid filesystem pollution.
- No mutation of specify-state.json (verified by re-reading state after call).

Stdlib only. Python 3.8+. No third-party deps.
"""

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Import path setup.
# ---------------------------------------------------------------------------

_LIB_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "src" / "devforge" / "lib"
)
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _specify._cmds_handoff import _dict_to_dataclass, cmd_finalize_handoff  # noqa: E402
from _specify import handoff_schema as specify_handoff_schema  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture factories.
# ---------------------------------------------------------------------------


def _make_ac(**kwargs):
    defaults = dict(
        ac_id="AC-1",
        subsection="behavior_change",
        ears_variant="event_driven",
        statement="WHEN an event occurs, the system shall log it.",
        verification_command="pytest tests/test_log.py",
        test_anchor="test_log_event",
        n_a_reason="",
    )
    defaults.update(kwargs)
    return defaults


def _make_constraint_nfr(**kwargs):
    defaults = dict(
        kind="nfr",
        content="Writes must complete within 100ms",
        quantifier="p99 < 100ms",
    )
    defaults.update(kwargs)
    return defaults


def _make_affected_area(**kwargs):
    defaults = dict(
        area="EventService",
        files=["src/services/event_service.py"],
        impact="Audit events written here",
    )
    defaults.update(kwargs)
    return defaults


def _make_oos(**kwargs):
    defaults = dict(
        content="Real-time streaming of audit events",
        finding_ref="",
    )
    defaults.update(kwargs)
    return defaults


def _make_open_question(**kwargs):
    defaults = dict(
        question_id="OQ-1",
        content="Which table stores audit events?",
        category_no_dp_reason="",
    )
    defaults.update(kwargs)
    return defaults


def _make_risk(**kwargs):
    defaults = dict(
        risk="DB latency spikes under write load",
        likelihood="Med",
        impact="High",
        mitigation="Use async write queue with retry logic",
    )
    defaults.update(kwargs)
    return defaults


def _make_state(**kwargs):
    """Minimal Approved specify state dict ready for finalize-handoff."""
    base = {
        "topic": "audit-log-persistence",
        "topic_slug": "audit-log-persistence",
        "date": "2026-05-22",
        "spec_number": "001",
        "feature_name": "audit-log-persistence",
        "feature_slug": "audit-log-persistence",
        "spec_type": "feature_addition",
        "spec_type_rationale": "Adding a new audit log persistence feature",
        "spec_type_seeded_by_upstream": False,
        # /specify leaves status "Draft" through approval; the handoff is
        # emitted with Draft (the Phase 5.3 approve branch is the gate, not a
        # state flip). /plan owns the Draft->Approved flip.
        "status": "Draft",
        "overview": "Add structured audit log persistence to the EventService.",
        "current_state": None,
        "desired_behavior": None,
        "affected_areas": [_make_affected_area()],
        "acceptance_criteria": [_make_ac()],
        "ac_subsection_na": {"ci_pipeline": "No CI changes required"},
        "out_of_scope": [_make_oos()],
        "constraints": [_make_constraint_nfr()],
        "open_questions": [_make_open_question()],
        "risks": [_make_risk()],
        "approval_summary": None,
        "plan_handoff_block": None,
        "open_question_resolutions": [],
        "conflicts": [],
        "source": {
            "handoff_path": None,
            "handoff_kind": None,
            "research_completed_at": None,
            "discover_completed_at": None,
            "discover_recommended_summary": None,
        },
        # Additional fields that default_state() includes:
        "input_reads": [],
        "phase1_finalized": False,
        "findings": [],
        "source_no_items_relevant": {},
        "findings_finalized": False,
        "decision_points": [],
        "dp_finalized": False,
        "mode": None,
        "mandatory_reads": [],
        "discretionary_reads": [],
        "phase3_finalized": False,
        "current_branch": None,
        "default_branch": None,
        "branch_decision": None,
        "branch_created": None,
    }
    base.update(kwargs)
    return base


def _write_state(devforge_dir, state):
    """Write state dict to specify-state.json under devforge_dir."""
    Path(devforge_dir).mkdir(parents=True, exist_ok=True)
    state_path = Path(devforge_dir) / "specify-state.json"
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state_path


def _make_args(devforge_dir, emit_path=None, specs_root="specs", completed_at=None):
    """Build a fake argparse.Namespace for cmd_finalize_handoff."""
    return argparse.Namespace(
        devforge_dir=str(devforge_dir),
        emit_handoff_json=emit_path,
        specs_root=specs_root,
        completed_at=completed_at,
    )


# ---------------------------------------------------------------------------
# TestRoundTrip.
# ---------------------------------------------------------------------------


class TestRoundTrip(unittest.TestCase):
    """Fully-populated state -> handoff.json -> reconstruct via _dict_to_dataclass."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.devforge_dir = self.tmp / ".devforge"

    def tearDown(self):
        self._tmp.cleanup()

    def test_round_trip_fully_populated(self):
        """Approved state with all section types -> handoff.json reconstructable."""
        state = _make_state(
            source={
                "handoff_path": "research/2026-05-20-audit/handoff.json",
                "handoff_kind": "research",
                "research_completed_at": "2026-05-20T08:00:00Z",
                "discover_completed_at": None,
                "discover_recommended_summary": None,
            }
        )
        _write_state(self.devforge_dir, state)

        emit_path = str(self.tmp / "out" / "handoff.json")
        args = _make_args(
            self.devforge_dir,
            emit_path=emit_path,
            completed_at="2026-05-22T10:00:00Z",
        )
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 0, "Expected exit 0 from finalize-handoff")

        # Verify file exists.
        out_path = Path(emit_path)
        self.assertTrue(out_path.exists(), "handoff.json was not written")

        # Reconstruct via _dict_to_dataclass.
        with open(str(out_path), encoding="utf-8") as f:
            raw = json.load(f)

        handoff = _dict_to_dataclass(specify_handoff_schema.Handoff, raw)
        self.assertIsInstance(handoff, specify_handoff_schema.Handoff)

        # Key field assertions.
        self.assertEqual(handoff.spec_path, "specs/001-audit-log-persistence/spec.md")
        self.assertEqual(handoff.handoff_kind, "specify")
        self.assertEqual(handoff.schema_version, specify_handoff_schema.SCHEMA_VERSION)
        self.assertEqual(handoff.specify_completed_at, "2026-05-22T10:00:00Z")
        self.assertEqual(handoff.classification.status, "Draft")
        self.assertEqual(handoff.classification.spec_number, "001")
        self.assertEqual(handoff.classification.spec_type, "feature_addition")

        # AC survives.
        self.assertEqual(len(handoff.spec_seeds.acceptance_criteria), 1)
        self.assertEqual(
            handoff.spec_seeds.acceptance_criteria[0].statement,
            "WHEN an event occurs, the system shall log it.",
        )

        # Constraint kind survives.
        self.assertEqual(len(handoff.spec_seeds.constraints), 1)
        self.assertEqual(handoff.spec_seeds.constraints[0].kind, "nfr")
        self.assertEqual(handoff.spec_seeds.constraints[0].quantifier, "p99 < 100ms")

        # Provenance kind+path survive.
        self.assertEqual(handoff.provenance.upstream_handoff_kind, "research")
        self.assertEqual(
            handoff.provenance.upstream_handoff_path,
            "research/2026-05-20-audit/handoff.json",
        )
        self.assertEqual(handoff.provenance.upstream_completed_at, "2026-05-20T08:00:00Z")

        # DownstreamLinks defaults.
        self.assertIsNone(handoff.downstream_links.plan_path)
        self.assertEqual(handoff.downstream_links.execute_task_commit_shas, [])

        # ac_subsection_na survives.
        self.assertIn("ci_pipeline", handoff.spec_seeds.ac_subsection_na)

    def test_state_not_mutated_after_finalize(self):
        """specify-state.json is unchanged after cmd_finalize_handoff (read-only)."""
        state = _make_state()
        state_path = _write_state(self.devforge_dir, state)
        original_bytes = state_path.read_bytes()

        emit_path = str(self.tmp / "out" / "handoff.json")
        args = _make_args(self.devforge_dir, emit_path=emit_path)
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 0)

        after_bytes = state_path.read_bytes()
        self.assertEqual(original_bytes, after_bytes, "specify-state.json was mutated!")


# ---------------------------------------------------------------------------
# TestDefaultEmitPath.
# ---------------------------------------------------------------------------


class TestDefaultEmitPath(unittest.TestCase):
    """When --emit-handoff-json is omitted, path = specs/{N}-{slug}/handoff.json."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.devforge_dir = self.tmp / ".devforge"

    def tearDown(self):
        self._tmp.cleanup()

    def test_default_emit_path_is_specs_number_slug(self):
        """Absent --emit-handoff-json -> default path specs/001-audit-log-persistence/handoff.json."""
        # Change cwd to tmp so the relative path is written under tmp.
        import os
        original_cwd = os.getcwd()
        os.chdir(str(self.tmp))
        try:
            state = _make_state()
            _write_state(self.devforge_dir, state)
            args = _make_args(self.devforge_dir)  # emit_path=None
            rc = cmd_finalize_handoff(args)
            self.assertEqual(rc, 0)
            expected = self.tmp / "specs" / "001-audit-log-persistence" / "handoff.json"
            self.assertTrue(expected.exists(), "Default emit path not created: {0}".format(expected))
        finally:
            os.chdir(original_cwd)

    def test_specs_root_override_changes_default_path(self):
        """--specs-root override changes the default emit path."""
        import os
        original_cwd = os.getcwd()
        os.chdir(str(self.tmp))
        try:
            state = _make_state()
            _write_state(self.devforge_dir, state)
            args = _make_args(self.devforge_dir, specs_root="custom-specs")
            rc = cmd_finalize_handoff(args)
            self.assertEqual(rc, 0)
            expected = (
                self.tmp / "custom-specs" / "001-audit-log-persistence" / "handoff.json"
            )
            self.assertTrue(
                expected.exists(),
                "Custom specs-root path not created: {0}".format(expected),
            )
        finally:
            os.chdir(original_cwd)


# ---------------------------------------------------------------------------
# TestStatusGuard.
# ---------------------------------------------------------------------------


class TestStatusHandling(unittest.TestCase):
    """/specify emits the handoff with status 'Draft' (no Approved guard);
    a status outside SPEC_STATUS_ENUM fails via schema validation."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.devforge_dir = self.tmp / ".devforge"

    def tearDown(self):
        self._tmp.cleanup()

    def _run_with_status(self, status):
        state = _make_state(status=status)
        _write_state(self.devforge_dir, state)
        emit_path = str(self.tmp / "out" / "handoff.json")
        args = _make_args(self.devforge_dir, emit_path=emit_path)

        import io
        captured = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = captured
        try:
            rc = cmd_finalize_handoff(args)
        finally:
            sys.stderr = old_stderr

        return rc, captured.getvalue(), emit_path

    def test_draft_status_succeeds(self):
        """Draft is the normal emit-time status -> exit 0, handoff written."""
        rc, _, emit_path = self._run_with_status("Draft")
        self.assertEqual(rc, 0)
        self.assertTrue(Path(emit_path).exists())

    def test_approved_status_succeeds(self):
        """Approved is also valid (e.g. re-run after a manual flip)."""
        rc, _, emit_path = self._run_with_status("Approved")
        self.assertEqual(rc, 0)
        self.assertTrue(Path(emit_path).exists())

    def test_status_outside_enum_exits_nonzero(self):
        """A corrupt status not in SPEC_STATUS_ENUM fails schema validation."""
        rc, msg, emit_path = self._run_with_status("Bogus")
        self.assertEqual(rc, 2)
        self.assertIn("status", msg)
        self.assertFalse(Path(emit_path).exists(), "handoff written despite invalid status")


# ---------------------------------------------------------------------------
# TestNoUpstreamProvenance.
# ---------------------------------------------------------------------------


class TestNoUpstreamProvenance(unittest.TestCase):
    """source.handoff_path=None + handoff_kind=None -> all-None provenance."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.devforge_dir = self.tmp / ".devforge"

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_upstream_produces_all_none_provenance(self):
        state = _make_state()  # source all-None by default
        _write_state(self.devforge_dir, state)
        emit_path = str(self.tmp / "out" / "handoff.json")
        args = _make_args(self.devforge_dir, emit_path=emit_path)
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 0)

        with open(emit_path, encoding="utf-8") as f:
            raw = json.load(f)
        handoff = _dict_to_dataclass(specify_handoff_schema.Handoff, raw)

        self.assertIsNone(handoff.provenance.upstream_handoff_path)
        self.assertIsNone(handoff.provenance.upstream_handoff_kind)
        self.assertIsNone(handoff.provenance.upstream_completed_at)

    def test_missing_source_key_treated_as_no_upstream(self):
        """State without a 'source' key at all -> all-None provenance (defensive)."""
        state = _make_state()
        del state["source"]
        _write_state(self.devforge_dir, state)
        emit_path = str(self.tmp / "out" / "handoff.json")
        args = _make_args(self.devforge_dir, emit_path=emit_path)
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 0)

        with open(emit_path, encoding="utf-8") as f:
            raw = json.load(f)
        handoff = _dict_to_dataclass(specify_handoff_schema.Handoff, raw)
        self.assertIsNone(handoff.provenance.upstream_handoff_path)


# ---------------------------------------------------------------------------
# TestUpstreamHandoffPathRootRelative (68-INTAKE-OWNS-FEATURE-DIR-PLAN.md
# Phase 4 / D9(d)). cmd_finalize_handoff copies state["source"]["handoff_path"]
# into Provenance.upstream_handoff_path VERBATIM (no path manipulation) --
# so a root-relative source.handoff_path (as import-handoff now produces;
# see tests/lib/test_specify_helper.py::TestImportHandoff for the producer
# side) must survive finalize-handoff unchanged, with no leading "/".
# ---------------------------------------------------------------------------


class TestUpstreamHandoffPathRootRelative(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.devforge_dir = self.tmp / ".devforge"

    def tearDown(self):
        self._tmp.cleanup()

    def test_root_relative_research_handoff_path_survives_verbatim(self):
        state = _make_state(
            source={
                "handoff_path": "specs/001-audit-log-persistence/research-handoff.json",
                "handoff_kind": "research",
                "research_completed_at": "2026-05-20T08:00:00Z",
                "discover_completed_at": None,
                "discover_recommended_summary": None,
            }
        )
        _write_state(self.devforge_dir, state)
        emit_path = str(self.tmp / "out" / "handoff.json")
        args = _make_args(self.devforge_dir, emit_path=emit_path)
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 0)

        with open(emit_path, encoding="utf-8") as f:
            raw = json.load(f)
        handoff = _dict_to_dataclass(specify_handoff_schema.Handoff, raw)

        self.assertEqual(
            handoff.provenance.upstream_handoff_path,
            "specs/001-audit-log-persistence/research-handoff.json",
        )
        self.assertFalse(
            handoff.provenance.upstream_handoff_path.startswith("/"),
            "provenance.upstream_handoff_path must stay root-relative,"
            " never absolutized by finalize-handoff",
        )
        # Same assertion against the raw written JSON (not just the
        # reconstructed dataclass) -- the "WRITTEN handoff JSON" the plan
        # item requires.
        self.assertEqual(
            raw["provenance"]["upstream_handoff_path"],
            "specs/001-audit-log-persistence/research-handoff.json",
        )
        self.assertFalse(raw["provenance"]["upstream_handoff_path"].startswith("/"))

    def test_root_relative_discover_handoff_path_survives_verbatim(self):
        state = _make_state(
            source={
                "handoff_path": "specs/002-scheduled-export-jobs/discover-handoff.json",
                "handoff_kind": "discover",
                "research_completed_at": None,
                "discover_completed_at": "2026-05-19T14:32:00Z",
                "discover_recommended_summary": "Extend ORM | Build",
            }
        )
        _write_state(self.devforge_dir, state)
        emit_path = str(self.tmp / "out" / "handoff.json")
        args = _make_args(self.devforge_dir, emit_path=emit_path)
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 0)

        with open(emit_path, encoding="utf-8") as f:
            raw = json.load(f)

        self.assertEqual(
            raw["provenance"]["upstream_handoff_path"],
            "specs/002-scheduled-export-jobs/discover-handoff.json",
        )
        self.assertFalse(raw["provenance"]["upstream_handoff_path"].startswith("/"))


# ---------------------------------------------------------------------------
# TestProvenanceCompletedAtMapping.
# ---------------------------------------------------------------------------


class TestProvenanceCompletedAtMapping(unittest.TestCase):
    """Provenance.upstream_completed_at pulls from the right source key."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.devforge_dir = self.tmp / ".devforge"

    def tearDown(self):
        self._tmp.cleanup()

    def _run_and_load(self, source_overrides):
        source = {
            "handoff_path": None,
            "handoff_kind": None,
            "research_completed_at": None,
            "discover_completed_at": None,
            "discover_recommended_summary": None,
        }
        source.update(source_overrides)
        state = _make_state(source=source)
        _write_state(self.devforge_dir, state)
        emit_path = str(self.tmp / "out" / "handoff.json")
        args = _make_args(self.devforge_dir, emit_path=emit_path)
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 0, "finalize-handoff failed unexpectedly")
        with open(emit_path, encoding="utf-8") as f:
            raw = json.load(f)
        return _dict_to_dataclass(specify_handoff_schema.Handoff, raw)

    def test_research_kind_pulls_research_completed_at(self):
        handoff = self._run_and_load({
            "handoff_path": "research/2026-05-20-audit/handoff.json",
            "handoff_kind": "research",
            "research_completed_at": "2026-05-20T08:00:00Z",
            "discover_completed_at": None,
        })
        self.assertEqual(handoff.provenance.upstream_completed_at, "2026-05-20T08:00:00Z")
        self.assertEqual(handoff.provenance.upstream_handoff_kind, "research")

    def test_discover_kind_pulls_discover_completed_at(self):
        handoff = self._run_and_load({
            "handoff_path": "discover/2026-05-19-audit-log.handoff.json",
            "handoff_kind": "discover",
            "research_completed_at": None,
            "discover_completed_at": "2026-05-19T14:32:00Z",
        })
        self.assertEqual(handoff.provenance.upstream_completed_at, "2026-05-19T14:32:00Z")
        self.assertEqual(handoff.provenance.upstream_handoff_kind, "discover")

    def test_research_kind_does_not_pull_discover_completed_at(self):
        """When kind=research, discover_completed_at is ignored."""
        handoff = self._run_and_load({
            "handoff_path": "research/2026-05-20-audit/handoff.json",
            "handoff_kind": "research",
            "research_completed_at": "2026-05-20T08:00:00Z",
            "discover_completed_at": "2026-05-19T14:32:00Z",  # present but should be ignored
        })
        self.assertEqual(handoff.provenance.upstream_completed_at, "2026-05-20T08:00:00Z")


# ---------------------------------------------------------------------------
# TestCompletedAtInjection.
# ---------------------------------------------------------------------------


class TestCompletedAtInjection(unittest.TestCase):
    """--completed-at produces a deterministic specify_completed_at in output."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.devforge_dir = self.tmp / ".devforge"

    def tearDown(self):
        self._tmp.cleanup()

    def test_completed_at_injection(self):
        state = _make_state()
        _write_state(self.devforge_dir, state)
        emit_path = str(self.tmp / "out" / "handoff.json")
        args = _make_args(
            self.devforge_dir,
            emit_path=emit_path,
            completed_at="2026-01-15T12:34:56Z",
        )
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 0)

        with open(emit_path, encoding="utf-8") as f:
            raw = json.load(f)
        self.assertEqual(raw["specify_completed_at"], "2026-01-15T12:34:56Z")

    def test_without_completed_at_generates_timestamp(self):
        """Without --completed-at, specify_completed_at is a non-empty string."""
        state = _make_state()
        _write_state(self.devforge_dir, state)
        emit_path = str(self.tmp / "out" / "handoff.json")
        args = _make_args(self.devforge_dir, emit_path=emit_path)
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 0)

        with open(emit_path, encoding="utf-8") as f:
            raw = json.load(f)
        ts = raw.get("specify_completed_at", "")
        self.assertTrue(len(ts) > 0, "specify_completed_at not generated")
        # Basic ISO-8601 shape check.
        self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


# ---------------------------------------------------------------------------
# TestCLIParserDispatch.
# ---------------------------------------------------------------------------


class TestCLIParserDispatch(unittest.TestCase):
    """finalize-handoff is registered in the CLI parser and dispatches correctly."""

    def test_finalize_handoff_subparser_registered(self):
        """build_parser() produces a parser that recognises 'finalize-handoff'."""
        from _specify._cli import build_parser
        parser = build_parser()
        # If 'finalize-handoff' is registered, parse_args won't raise.
        # We pass --devforge-dir to satisfy the parent subparser.
        args = parser.parse_args([
            "--devforge-dir", "/tmp/fake",
            "finalize-handoff",
        ])
        self.assertEqual(args.func, cmd_finalize_handoff)
        self.assertEqual(args.specs_root, "specs")
        self.assertIsNone(args.emit_handoff_json)
        self.assertIsNone(args.completed_at)

    def test_finalize_handoff_accepts_all_optional_args(self):
        """All optional args parse without error."""
        from _specify._cli import build_parser
        parser = build_parser()
        args = parser.parse_args([
            "--devforge-dir", "/tmp/fake",
            "finalize-handoff",
            "--emit-handoff-json", "/tmp/out/handoff.json",
            "--specs-root", "custom-specs",
            "--completed-at", "2026-05-22T10:00:00Z",
        ])
        self.assertEqual(args.emit_handoff_json, "/tmp/out/handoff.json")
        self.assertEqual(args.specs_root, "custom-specs")
        self.assertEqual(args.completed_at, "2026-05-22T10:00:00Z")


# ---------------------------------------------------------------------------
# TestMissingRequiredStateFields.
# ---------------------------------------------------------------------------


class TestMissingRequiredStateFields(unittest.TestCase):
    """Missing spec_number or feature_slug -> non-zero exit."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.devforge_dir = self.tmp / ".devforge"

    def tearDown(self):
        self._tmp.cleanup()

    def _run_with_state(self, state):
        _write_state(self.devforge_dir, state)
        emit_path = str(self.tmp / "out" / "handoff.json")
        args = _make_args(self.devforge_dir, emit_path=emit_path)
        import io
        old_stderr = sys.stderr
        sys.stderr = io.StringIO()
        try:
            rc = cmd_finalize_handoff(args)
        finally:
            sys.stderr = old_stderr
        return rc

    def test_missing_spec_number_exits_nonzero(self):
        state = _make_state(spec_number=None)
        rc = self._run_with_state(state)
        self.assertNotEqual(rc, 0)

    def test_missing_feature_slug_exits_nonzero(self):
        state = _make_state(feature_slug=None)
        rc = self._run_with_state(state)
        self.assertNotEqual(rc, 0)


# ---------------------------------------------------------------------------
# TestDiscoverSeededState.
# ---------------------------------------------------------------------------


class TestDiscoverSeededState(unittest.TestCase):
    """State seeded via /discover -> import-handoff carries the discover-only
    affected_area key is_internal_extension_candidate. finalize-handoff must
    drop it (not crash) so the greenfield path works end-to-end."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.devforge_dir = self.tmp / ".devforge"

    def tearDown(self):
        self._tmp.cleanup()

    def test_discover_seeded_affected_area_does_not_crash(self):
        """affected_area with is_internal_extension_candidate -> rc 0, key dropped."""
        seeded_area = _make_affected_area(is_internal_extension_candidate=True)
        state = _make_state(
            spec_type="greenfield_feature",
            spec_type_rationale="Seeded from /discover",
            affected_areas=[seeded_area],
            source={
                "handoff_path": "discover/2026-05-19-audit-log.handoff.json",
                "handoff_kind": "discover",
                "research_completed_at": None,
                "discover_completed_at": "2026-05-19T14:32:00Z",
                "discover_recommended_summary": "Build new persistence layer",
            },
        )
        _write_state(self.devforge_dir, state)
        emit_path = str(self.tmp / "out" / "handoff.json")
        args = _make_args(self.devforge_dir, emit_path=emit_path)
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 0, "discover-seeded affected_area must not crash finalize-handoff")

        with open(emit_path, encoding="utf-8") as f:
            raw = json.load(f)
        handoff = _dict_to_dataclass(specify_handoff_schema.Handoff, raw)
        self.assertEqual(len(handoff.spec_seeds.affected_areas), 1)
        self.assertEqual(handoff.spec_seeds.affected_areas[0].area, "EventService")
        # The discover-only key must not survive into the specify handoff JSON.
        self.assertNotIn(
            "is_internal_extension_candidate",
            raw["spec_seeds"]["affected_areas"][0],
        )


# ---------------------------------------------------------------------------
# TestTrustsBoundary.
# ---------------------------------------------------------------------------


class TestTrustsBoundary(unittest.TestCase):
    """finalize-handoff trusts the Approved gate and does NOT re-run specify's
    content quality gates (coverage / AC-subsection / AC-shape). An Approved
    state with thin content still emits a handoff. This documents the
    intentional trust boundary (the /specify Phase 5 spec runs gates before
    approval)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.devforge_dir = self.tmp / ".devforge"

    def tearDown(self):
        self._tmp.cleanup()

    def test_approved_with_unlanded_finding_still_emits(self):
        """Approved state with an unlanded finding + empty AC list -> rc 0."""
        state = _make_state(
            acceptance_criteria=[],
            ac_subsection_na={},
            findings=[{
                "source_path": "constitution.md",
                "content": "Some rule that was never landed",
                "section": None,
                "landed_in": "unlanded",
                "landed_ref": "",
            }],
        )
        _write_state(self.devforge_dir, state)
        emit_path = str(self.tmp / "out" / "handoff.json")
        args = _make_args(self.devforge_dir, emit_path=emit_path)
        rc = cmd_finalize_handoff(args)
        self.assertEqual(
            rc, 0,
            "finalize-handoff must trust the Approved gate, not re-run coverage gates",
        )


# ---------------------------------------------------------------------------
# TestDesignAnchorDeliberatelyEmpty (plan 53 D5 regression -- python-reviewer
# F1). design_anchor's single source of truth is the sibling
# specs/[feature]/design-anchor.json (written by write-design-anchor); the
# specify->plan handoff.json must NEVER carry a populated design_anchor, even
# when state["design_anchor"] is non-empty, or the two would desync.
# ---------------------------------------------------------------------------


class TestDesignAnchorDeliberatelyEmpty(unittest.TestCase):
    """finalize-handoff always emits an empty spec_seeds.design_anchor,
    regardless of state["design_anchor"] (D5 park-once, read-in-place)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.devforge_dir = self.tmp / ".devforge"

    def tearDown(self):
        self._tmp.cleanup()

    def test_nonempty_state_design_anchor_yields_empty_handoff_design_anchor(self):
        """state["design_anchor"] captured+non-empty -> handoff spec_seeds.design_anchor is still empty."""
        state = _make_state(
            design_anchor={
                "kind": "html",
                "file": "design/reference.html",
                "selectors": [".fooBar"],
            },
        )
        _write_state(self.devforge_dir, state)

        emit_path = str(self.tmp / "out" / "handoff.json")
        args = _make_args(self.devforge_dir, emit_path=emit_path)
        rc = cmd_finalize_handoff(args)
        self.assertEqual(rc, 0, "Expected exit 0 from finalize-handoff")

        with open(emit_path, encoding="utf-8") as f:
            raw = json.load(f)
        handoff = _dict_to_dataclass(specify_handoff_schema.Handoff, raw)

        self.assertEqual(
            handoff.spec_seeds.design_anchor,
            specify_handoff_schema.DesignAnchor(),
            "spec_seeds.design_anchor must stay empty -- design-anchor.json is the "
            "sole source of truth (D5); populating the handoff too would desync",
        )
        self.assertEqual(raw["spec_seeds"]["design_anchor"], {
            "kind": "", "file": "", "selectors": [],
        })


if __name__ == "__main__":
    unittest.main()
