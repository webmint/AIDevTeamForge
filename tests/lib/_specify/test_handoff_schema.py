"""Tests for src/devforge/lib/_specify/handoff_schema.py.

Covers all test cases as enumerated in the task spec.  Grouped by concern:

- TestHappyPath (1 case): fully-valid Handoff constructs.
- TestConstantLocks (2 cases): wrong schema_version, wrong handoff_kind.
- TestClassification: status enum-validated (Draft valid, bad rejected), bad spec_type, nonempty
  fields reject empty/whitespace.
- TestSpecSeeds (4 cases): ac_subsection_na bad key, empty value; AffectedArea
  files non-string element; list-type checks.
- TestAcceptanceCriterion (3 cases): bad subsection, bad ears_variant, empty
  ac_id; empty-string allowed fields accept "".
- TestConstraint (3 cases): bad kind, empty content, nfr without quantifier
  DOES NOT raise (proving we did not re-implement specify's conditional rule).
- TestAffectedArea (1 case): files rejects non-string element.
- TestRisk (2 cases): bad likelihood, bad impact.
- TestOpenQuestion (1 case): nonempty checks.
- TestProvenance: all-None valid, bad upstream_handoff_kind enum, accepts
  "research"/"discover" (with path), and path/kind co-variance rejection.
- TestDownstreamLinks (1 case): execute_task_commit_shas not a list rejects.
- TestEmptyStringAllowed (1 case): empty-string optional fields accept "".

Stdlib only. No third-party dependencies.
"""

import sys
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Import path setup.  The schema imports from ._schema which is a relative
# import, so we add the _specify package directory parent to sys.path and
# import via the package.
# ---------------------------------------------------------------------------

_LIB_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "src" / "devforge" / "lib"
)
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _specify import handoff_schema as hs  # noqa: E402


# ---------------------------------------------------------------------------
# Fixture factories.
# ---------------------------------------------------------------------------


def _classification(**kwargs):
    defaults = dict(
        spec_number="001",
        feature_name="audit-log-persistence",
        feature_slug="audit-log-persistence",
        spec_type="feature_addition",
        spec_type_rationale="Adding a new audit log feature to existing service",
        status="Approved",
    )
    defaults.update(kwargs)
    return hs.Classification(**defaults)


def _ac(**kwargs):
    defaults = dict(
        ac_id="AC-1",
        subsection="behavior_change",
        ears_variant="event_driven",
        statement="WHEN an audit event is emitted, the system shall persist it to the database.",
        verification_command="pytest tests/test_audit.py",
        test_anchor="test_audit_persistence",
        n_a_reason="",
    )
    defaults.update(kwargs)
    return hs.AcceptanceCriterion(**defaults)


def _constraint(kind="follow", **kwargs):
    defaults = {
        "follow": dict(content="Follow existing repository patterns"),
        "not_break": dict(content="Must not break the existing authentication flow"),
        "nfr": dict(content="Writes must complete within 100ms", quantifier="p99 < 100ms"),
        "constitution_anchor": dict(
            content="Follow SOLID principles",
            constitution_ref="constitution.md#solid",
        ),
        "external_system": dict(
            content="Write via REST API",
            protocol="REST/HTTP",
        ),
    }
    base = defaults[kind].copy()
    base["kind"] = kind
    base.update(kwargs)
    return hs.Constraint(**base)


def _affected_area(**kwargs):
    defaults = dict(
        area="EventService",
        files=["src/services/event_service.py"],
        impact="Audit events written here",
    )
    defaults.update(kwargs)
    return hs.AffectedArea(**defaults)


def _out_of_scope_item(**kwargs):
    defaults = dict(
        content="Real-time streaming of audit events",
        finding_ref="",
    )
    defaults.update(kwargs)
    return hs.OutOfScopeItem(**defaults)


def _open_question(**kwargs):
    defaults = dict(
        question_id="OQ-1",
        content="Which database table should store audit events?",
        category_no_dp_reason="",
    )
    defaults.update(kwargs)
    return hs.OpenQuestion(**defaults)


def _risk(**kwargs):
    defaults = dict(
        risk="Database latency spikes under write load",
        likelihood="Med",
        impact="High",
        mitigation="Use async write queue with retry logic",
    )
    defaults.update(kwargs)
    return hs.Risk(**defaults)


def _spec_seeds(**kwargs):
    defaults = dict(
        overview="Add structured audit log persistence to the EventService.",
        acceptance_criteria=[_ac()],
        ac_subsection_na={"ci_pipeline": "No CI changes required for this feature"},
        constraints=[_constraint()],
        affected_areas=[_affected_area()],
        out_of_scope=[_out_of_scope_item()],
        open_questions=[_open_question()],
        risks=[_risk()],
    )
    defaults.update(kwargs)
    return hs.SpecSeeds(**defaults)


def _provenance(**kwargs):
    defaults = dict(
        upstream_handoff_path=None,
        upstream_handoff_kind=None,
        upstream_completed_at=None,
    )
    defaults.update(kwargs)
    return hs.Provenance(**defaults)


def _downstream_links(**kwargs):
    return hs.DownstreamLinks(**kwargs)


def _make_valid(**kwargs):
    """Build a fully-valid Handoff. Tests override specific fields."""
    return hs.Handoff(
        schema_version=kwargs.pop("schema_version", hs.SCHEMA_VERSION),
        handoff_kind=kwargs.pop("handoff_kind", "specify"),
        spec_path=kwargs.pop("spec_path", "specs/001-audit-log-persistence/spec.md"),
        specify_completed_at=kwargs.pop("specify_completed_at", "2026-05-22T10:00:00Z"),
        classification=kwargs.pop("classification", _classification()),
        spec_seeds=kwargs.pop("spec_seeds", _spec_seeds()),
        provenance=kwargs.pop("provenance", _provenance()),
        downstream_links=kwargs.pop("downstream_links", _downstream_links()),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# TestHappyPath.
# ---------------------------------------------------------------------------


class TestHappyPath(unittest.TestCase):
    """A fully-valid Handoff constructs successfully."""

    def test_valid_handoff_constructs(self):
        h = _make_valid()
        self.assertIsInstance(h, hs.Handoff)
        self.assertEqual(h.handoff_kind, "specify")
        self.assertEqual(h.schema_version, hs.SCHEMA_VERSION)
        self.assertEqual(h.classification.status, "Approved")
        self.assertIsNone(h.downstream_links.plan_path)
        self.assertEqual(h.downstream_links.execute_task_commit_shas, [])

    def test_valid_handoff_with_all_optional_provenance_set(self):
        """Handoff with non-None provenance fields (research upstream) constructs."""
        prov = _provenance(
            upstream_handoff_path="research/2026-05-20-audit/handoff.json",
            upstream_handoff_kind="research",
            upstream_completed_at="2026-05-20T08:00:00Z",
        )
        h = _make_valid(provenance=prov)
        self.assertEqual(h.provenance.upstream_handoff_kind, "research")

    def test_valid_handoff_with_discover_provenance(self):
        """Handoff with upstream_handoff_kind='discover' constructs."""
        prov = _provenance(
            upstream_handoff_path="discover/2026-05-19-audit-log.handoff.json",
            upstream_handoff_kind="discover",
            upstream_completed_at="2026-05-19T14:32:00Z",
        )
        h = _make_valid(provenance=prov)
        self.assertEqual(h.provenance.upstream_handoff_kind, "discover")

    def test_valid_handoff_with_downstream_links_filled(self):
        """DownstreamLinks with plan_path + commit SHAs constructs."""
        dl = _downstream_links(
            plan_path="specs/001-audit-log-persistence/plan.md",
            execute_task_commit_shas=["abc1234", "def5678"],
        )
        h = _make_valid(downstream_links=dl)
        self.assertEqual(h.downstream_links.plan_path, "specs/001-audit-log-persistence/plan.md")
        self.assertEqual(len(h.downstream_links.execute_task_commit_shas), 2)

    def test_valid_handoff_empty_lists(self):
        """SpecSeeds with all empty lists (except overview) constructs."""
        ss = _spec_seeds(
            acceptance_criteria=[],
            ac_subsection_na={},
            constraints=[],
            affected_areas=[],
            out_of_scope=[],
            open_questions=[],
            risks=[],
        )
        h = _make_valid(spec_seeds=ss)
        self.assertEqual(h.spec_seeds.acceptance_criteria, [])


# ---------------------------------------------------------------------------
# TestConstantLocks.
# ---------------------------------------------------------------------------


class TestConstantLocks(unittest.TestCase):
    """Wrong schema_version or wrong handoff_kind raises ValueError."""

    def test_reject_wrong_schema_version(self):
        with self.assertRaises(ValueError) as ctx:
            _make_valid(schema_version="2.0")
        self.assertIn("schema_version", str(ctx.exception))

    def test_reject_wrong_handoff_kind(self):
        with self.assertRaises(ValueError) as ctx:
            _make_valid(handoff_kind="discover")
        self.assertIn("handoff_kind", str(ctx.exception))
        self.assertIn("specify", str(ctx.exception))

    def test_reject_handoff_kind_research(self):
        with self.assertRaises(ValueError) as ctx:
            _make_valid(handoff_kind="research")
        self.assertIn("handoff_kind", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestClassification.
# ---------------------------------------------------------------------------


class TestClassification(unittest.TestCase):
    """Classification field validation."""

    def test_draft_status_valid(self):
        """status 'Draft' is valid -- /specify emits the handoff with Draft."""
        c = _classification(status="Draft")
        self.assertEqual(c.status, "Draft")

    def test_all_valid_statuses_accepted(self):
        """Each member of SPEC_STATUS_ENUM is accepted."""
        from _specify._schema import SPEC_STATUS_ENUM
        for status in SPEC_STATUS_ENUM:
            c = _classification(status=status)
            self.assertEqual(c.status, status)

    def test_reject_status_not_in_enum(self):
        """status not in SPEC_STATUS_ENUM raises with field named."""
        with self.assertRaises(ValueError) as ctx:
            _classification(status="Bogus")
        self.assertIn("status", str(ctx.exception))

    def test_reject_bad_spec_type(self):
        with self.assertRaises(ValueError) as ctx:
            _classification(spec_type="unknown_type")
        self.assertIn("spec_type", str(ctx.exception))

    def test_all_valid_spec_types_accepted(self):
        """Each member of SPEC_TYPE_ENUM is accepted."""
        from _specify._schema import SPEC_TYPE_ENUM
        for spec_type in SPEC_TYPE_ENUM:
            c = _classification(spec_type=spec_type)
            self.assertEqual(c.spec_type, spec_type)

    def test_reject_empty_spec_number(self):
        with self.assertRaises(ValueError) as ctx:
            _classification(spec_number="")
        self.assertIn("spec_number", str(ctx.exception))

    def test_none_spec_number_accepted(self):
        """91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 3: a
        bucketed feature dir carries no NNN at all -- None is the honest
        value (D9, nothing invented), and is NOT the same thing as the
        empty string the test above still rejects."""
        c = _classification(spec_number=None)
        self.assertIsNone(c.spec_number)

    def test_reject_non_string_non_none_spec_number(self):
        """A non-string, non-None spec_number (e.g. a stray int) is still
        a type error -- only the literal None sentinel is exempted."""
        with self.assertRaises(ValueError) as ctx:
            _classification(spec_number=42)
        self.assertIn("spec_number", str(ctx.exception))

    def test_reject_whitespace_feature_name(self):
        with self.assertRaises(ValueError) as ctx:
            _classification(feature_name="   ")
        self.assertIn("feature_name", str(ctx.exception))

    def test_reject_empty_spec_type_rationale(self):
        with self.assertRaises(ValueError) as ctx:
            _classification(spec_type_rationale="")
        self.assertIn("spec_type_rationale", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestAcceptanceCriterion.
# ---------------------------------------------------------------------------


class TestAcceptanceCriterion(unittest.TestCase):
    """AcceptanceCriterion field validation."""

    def test_reject_bad_subsection(self):
        with self.assertRaises(ValueError) as ctx:
            _ac(subsection="nonexistent_section")
        self.assertIn("subsection", str(ctx.exception))

    def test_reject_bad_ears_variant(self):
        with self.assertRaises(ValueError) as ctx:
            _ac(ears_variant="future_driven")
        self.assertIn("ears_variant", str(ctx.exception))

    def test_reject_empty_ac_id(self):
        with self.assertRaises(ValueError) as ctx:
            _ac(ac_id="")
        self.assertIn("ac_id", str(ctx.exception))

    def test_reject_empty_statement(self):
        with self.assertRaises(ValueError) as ctx:
            _ac(statement="")
        self.assertIn("statement", str(ctx.exception))

    def test_empty_string_verification_command_accepted(self):
        """verification_command may be an empty string."""
        ac = _ac(verification_command="")
        self.assertEqual(ac.verification_command, "")

    def test_empty_string_test_anchor_accepted(self):
        """test_anchor may be an empty string."""
        ac = _ac(test_anchor="")
        self.assertEqual(ac.test_anchor, "")

    def test_empty_string_n_a_reason_accepted(self):
        """n_a_reason may be an empty string."""
        ac = _ac(n_a_reason="")
        self.assertEqual(ac.n_a_reason, "")

    def test_all_valid_subsections_accepted(self):
        """Each member of AC_SUBSECTION_ENUM is accepted."""
        from _specify._schema import AC_SUBSECTION_ENUM
        for subsection in AC_SUBSECTION_ENUM:
            ac = _ac(subsection=subsection)
            self.assertEqual(ac.subsection, subsection)

    def test_all_valid_ears_variants_accepted(self):
        """Each member of EARS_VARIANT_ENUM is accepted."""
        from _specify._schema import EARS_VARIANT_ENUM
        for variant in EARS_VARIANT_ENUM:
            ac = _ac(ears_variant=variant)
            self.assertEqual(ac.ears_variant, variant)


# ---------------------------------------------------------------------------
# TestConstraint.
# ---------------------------------------------------------------------------


class TestConstraint(unittest.TestCase):
    """Constraint field validation."""

    def test_reject_bad_kind(self):
        with self.assertRaises(ValueError) as ctx:
            hs.Constraint(kind="use", content="Use this library")
        self.assertIn("kind", str(ctx.exception))

    def test_reject_empty_content(self):
        with self.assertRaises(ValueError) as ctx:
            hs.Constraint(kind="follow", content="")
        self.assertIn("content", str(ctx.exception))

    def test_nfr_without_quantifier_does_not_raise(self):
        """Constraint kind='nfr' without quantifier does NOT raise.

        Proves we did NOT re-implement specify's conditional per-kind rule.
        The setter already enforced this; the schema is transport-only.
        """
        c = hs.Constraint(kind="nfr", content="Writes must complete within 100ms")
        self.assertEqual(c.kind, "nfr")
        self.assertIsNone(c.quantifier)

    def test_constitution_anchor_without_ref_does_not_raise(self):
        """Constraint kind='constitution_anchor' without constitution_ref does NOT raise."""
        c = hs.Constraint(kind="constitution_anchor", content="Follow SOLID principles")
        self.assertEqual(c.kind, "constitution_anchor")
        self.assertIsNone(c.constitution_ref)

    def test_external_system_without_protocol_or_ref_does_not_raise(self):
        """Constraint kind='external_system' without protocol/contract_doc_ref does NOT raise."""
        c = hs.Constraint(kind="external_system", content="Integrate with external API")
        self.assertEqual(c.kind, "external_system")

    def test_all_valid_constraint_kinds_accepted(self):
        """Each member of CONSTRAINT_KIND_ENUM is accepted."""
        from _specify._schema import CONSTRAINT_KIND_ENUM
        for kind in CONSTRAINT_KIND_ENUM:
            c = hs.Constraint(kind=kind, content="Some constraint content")
            self.assertEqual(c.kind, kind)

    def test_optional_fields_carry_through_when_provided(self):
        """Optional fields are stored and accessible when provided."""
        c = hs.Constraint(
            kind="nfr",
            content="Latency SLA",
            quantifier="p99 < 200ms",
        )
        self.assertEqual(c.quantifier, "p99 < 200ms")


# ---------------------------------------------------------------------------
# TestAffectedArea.
# ---------------------------------------------------------------------------


class TestAffectedArea(unittest.TestCase):
    """AffectedArea field validation."""

    def test_reject_non_string_file_element(self):
        """files list containing a non-string element raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            _affected_area(files=["src/valid.py", 42])
        self.assertIn("files", str(ctx.exception))

    def test_reject_empty_area(self):
        with self.assertRaises(ValueError) as ctx:
            _affected_area(area="")
        self.assertIn("area", str(ctx.exception))

    def test_reject_empty_impact(self):
        with self.assertRaises(ValueError) as ctx:
            _affected_area(impact="")
        self.assertIn("impact", str(ctx.exception))

    def test_reject_files_not_a_list(self):
        with self.assertRaises(ValueError) as ctx:
            _affected_area(files="not-a-list")
        self.assertIn("files", str(ctx.exception))

    def test_empty_files_list_accepted(self):
        """files may be an empty list."""
        aa = _affected_area(files=[])
        self.assertEqual(aa.files, [])

    def test_no_is_internal_extension_candidate_field(self):
        """AffectedArea does not have is_internal_extension_candidate (discover-only)."""
        aa = _affected_area()
        self.assertFalse(hasattr(aa, "is_internal_extension_candidate"))


# ---------------------------------------------------------------------------
# TestOutOfScopeItem.
# ---------------------------------------------------------------------------


class TestOutOfScopeItem(unittest.TestCase):
    """OutOfScopeItem field validation."""

    def test_reject_empty_content(self):
        with self.assertRaises(ValueError) as ctx:
            _out_of_scope_item(content="")
        self.assertIn("content", str(ctx.exception))

    def test_empty_string_finding_ref_accepted(self):
        """finding_ref may be an empty string."""
        item = _out_of_scope_item(finding_ref="")
        self.assertEqual(item.finding_ref, "")

    def test_nonempty_finding_ref_accepted(self):
        item = _out_of_scope_item(finding_ref="F-3")
        self.assertEqual(item.finding_ref, "F-3")


# ---------------------------------------------------------------------------
# TestOpenQuestion.
# ---------------------------------------------------------------------------


class TestOpenQuestion(unittest.TestCase):
    """OpenQuestion field validation (specify's shape, NOT discover's)."""

    def test_reject_empty_question_id(self):
        with self.assertRaises(ValueError) as ctx:
            _open_question(question_id="")
        self.assertIn("question_id", str(ctx.exception))

    def test_reject_empty_content(self):
        with self.assertRaises(ValueError) as ctx:
            _open_question(content="")
        self.assertIn("content", str(ctx.exception))

    def test_empty_string_category_no_dp_reason_accepted(self):
        """category_no_dp_reason may be an empty string."""
        oq = _open_question(category_no_dp_reason="")
        self.assertEqual(oq.category_no_dp_reason, "")

    def test_open_question_has_no_blocking_field(self):
        """OpenQuestion has no 'blocking' field (that is discover's shape)."""
        oq = _open_question()
        self.assertFalse(hasattr(oq, "blocking"))

    def test_open_question_has_no_question_field(self):
        """OpenQuestion has no 'question' field (that is discover's shape)."""
        oq = _open_question()
        self.assertFalse(hasattr(oq, "question"))


# ---------------------------------------------------------------------------
# TestRisk.
# ---------------------------------------------------------------------------


class TestRisk(unittest.TestCase):
    """Risk field validation."""

    def test_reject_bad_likelihood(self):
        with self.assertRaises(ValueError) as ctx:
            _risk(likelihood="Unlikely")
        self.assertIn("likelihood", str(ctx.exception))

    def test_reject_bad_impact(self):
        with self.assertRaises(ValueError) as ctx:
            _risk(impact="Critical")
        self.assertIn("impact", str(ctx.exception))

    def test_reject_empty_risk(self):
        with self.assertRaises(ValueError) as ctx:
            _risk(risk="")
        self.assertIn("risk", str(ctx.exception))

    def test_reject_empty_mitigation(self):
        with self.assertRaises(ValueError) as ctx:
            _risk(mitigation="")
        self.assertIn("mitigation", str(ctx.exception))

    def test_all_valid_likelihood_values_accepted(self):
        for val in ("Low", "Med", "High"):
            r = _risk(likelihood=val)
            self.assertEqual(r.likelihood, val)

    def test_all_valid_impact_values_accepted(self):
        for val in ("Low", "Med", "High"):
            r = _risk(impact=val)
            self.assertEqual(r.impact, val)


# ---------------------------------------------------------------------------
# TestSpecSeeds.
# ---------------------------------------------------------------------------


class TestSpecSeeds(unittest.TestCase):
    """SpecSeeds field validation."""

    def test_reject_ac_subsection_na_bad_key(self):
        """ac_subsection_na with a key not in AC_SUBSECTION_ENUM raises."""
        with self.assertRaises(ValueError) as ctx:
            _spec_seeds(ac_subsection_na={"nonexistent_section": "reason"})
        self.assertIn("ac_subsection_na", str(ctx.exception))

    def test_reject_ac_subsection_na_empty_value(self):
        """ac_subsection_na with an empty string value raises."""
        with self.assertRaises(ValueError) as ctx:
            _spec_seeds(ac_subsection_na={"ci_pipeline": ""})
        self.assertIn("ci_pipeline", str(ctx.exception))

    def test_reject_ac_subsection_na_whitespace_value(self):
        """ac_subsection_na with a whitespace-only value raises."""
        with self.assertRaises(ValueError) as ctx:
            _spec_seeds(ac_subsection_na={"ci_pipeline": "   "})
        self.assertIn("ci_pipeline", str(ctx.exception))

    def test_reject_overview_empty(self):
        with self.assertRaises(ValueError) as ctx:
            _spec_seeds(overview="")
        self.assertIn("overview", str(ctx.exception))

    def test_reject_constraints_not_a_list(self):
        with self.assertRaises(ValueError) as ctx:
            _spec_seeds(constraints="not-a-list")
        self.assertIn("constraints", str(ctx.exception))

    def test_reject_affected_areas_not_a_list(self):
        with self.assertRaises(ValueError) as ctx:
            _spec_seeds(affected_areas="not-a-list")
        self.assertIn("affected_areas", str(ctx.exception))

    def test_reject_acceptance_criteria_not_a_list(self):
        with self.assertRaises(ValueError) as ctx:
            _spec_seeds(acceptance_criteria="not-a-list")
        self.assertIn("acceptance_criteria", str(ctx.exception))

    def test_reject_out_of_scope_not_a_list(self):
        with self.assertRaises(ValueError) as ctx:
            _spec_seeds(out_of_scope="not-a-list")
        self.assertIn("out_of_scope", str(ctx.exception))

    def test_reject_open_questions_not_a_list(self):
        with self.assertRaises(ValueError) as ctx:
            _spec_seeds(open_questions="not-a-list")
        self.assertIn("open_questions", str(ctx.exception))

    def test_reject_risks_not_a_list(self):
        with self.assertRaises(ValueError) as ctx:
            _spec_seeds(risks="not-a-list")
        self.assertIn("risks", str(ctx.exception))

    def test_valid_multiple_ac_subsection_na_keys(self):
        """Multiple valid ac_subsection_na keys accepted."""
        ss = _spec_seeds(
            ac_subsection_na={
                "ci_pipeline": "No CI changes",
                "hooks_gates": "No hook changes",
            }
        )
        self.assertEqual(len(ss.ac_subsection_na), 2)


# ---------------------------------------------------------------------------
# TestProvenance.
# ---------------------------------------------------------------------------


class TestProvenance(unittest.TestCase):
    """Provenance field validation."""

    def test_all_none_provenance_valid(self):
        """All-None Provenance constructs without error."""
        prov = _provenance()
        self.assertIsNone(prov.upstream_handoff_path)
        self.assertIsNone(prov.upstream_handoff_kind)
        self.assertIsNone(prov.upstream_completed_at)

    def test_reject_bad_upstream_handoff_kind(self):
        """upstream_handoff_kind not in ('research', 'discover') raises."""
        with self.assertRaises(ValueError) as ctx:
            _provenance(upstream_handoff_kind="specify")
        self.assertIn("upstream_handoff_kind", str(ctx.exception))

    def test_reject_unknown_upstream_handoff_kind(self):
        with self.assertRaises(ValueError) as ctx:
            _provenance(upstream_handoff_kind="plan")
        self.assertIn("upstream_handoff_kind", str(ctx.exception))

    def test_research_upstream_handoff_kind_accepted(self):
        prov = _provenance(
            upstream_handoff_path="research/2026-05-20-audit/handoff.json",
            upstream_handoff_kind="research",
        )
        self.assertEqual(prov.upstream_handoff_kind, "research")

    def test_discover_upstream_handoff_kind_accepted(self):
        prov = _provenance(
            upstream_handoff_path="discover/2026-05-19-audit.handoff.json",
            upstream_handoff_kind="discover",
        )
        self.assertEqual(prov.upstream_handoff_kind, "discover")

    def test_partial_provenance_valid(self):
        """path + kind set, completed_at None is valid (timestamp optional)."""
        prov = _provenance(
            upstream_handoff_path="research/2026-05-20-audit/handoff.json",
            upstream_handoff_kind="research",
        )
        self.assertIsNone(prov.upstream_completed_at)

    def test_reject_path_set_without_kind(self):
        """Co-variance: path set, kind None raises."""
        with self.assertRaises(ValueError) as ctx:
            _provenance(upstream_handoff_path="research/2026-05-20-audit/handoff.json")
        self.assertIn("upstream_handoff_path", str(ctx.exception))

    def test_reject_kind_set_without_path(self):
        """Co-variance: kind set (valid enum), path None raises."""
        with self.assertRaises(ValueError) as ctx:
            _provenance(upstream_handoff_kind="research")
        self.assertIn("both be set or both be None", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestDownstreamLinks.
# ---------------------------------------------------------------------------


class TestDownstreamLinks(unittest.TestCase):
    """DownstreamLinks field validation."""

    def test_default_downstream_links_valid(self):
        """Default DownstreamLinks (all defaults) constructs."""
        dl = _downstream_links()
        self.assertIsNone(dl.plan_path)
        self.assertEqual(dl.execute_task_commit_shas, [])

    def test_reject_execute_task_commit_shas_not_a_list(self):
        with self.assertRaises(ValueError) as ctx:
            hs.DownstreamLinks(execute_task_commit_shas="abc1234")
        self.assertIn("execute_task_commit_shas", str(ctx.exception))

    def test_no_spec_path_field(self):
        """DownstreamLinks has no spec_path field (Handoff.spec_path is canonical)."""
        dl = _downstream_links()
        self.assertFalse(hasattr(dl, "spec_path"))


# ---------------------------------------------------------------------------
# TestHandoffNonemptyFields.
# ---------------------------------------------------------------------------


class TestHandoffNonemptyFields(unittest.TestCase):
    """Top-level Handoff nonempty string fields reject empty / whitespace."""

    def test_reject_empty_spec_path(self):
        with self.assertRaises(ValueError) as ctx:
            _make_valid(spec_path="")
        self.assertIn("spec_path", str(ctx.exception))

    def test_reject_whitespace_spec_path(self):
        with self.assertRaises(ValueError) as ctx:
            _make_valid(spec_path="   ")
        self.assertIn("spec_path", str(ctx.exception))

    def test_reject_empty_specify_completed_at(self):
        with self.assertRaises(ValueError) as ctx:
            _make_valid(specify_completed_at="")
        self.assertIn("specify_completed_at", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestHandoffNestedTypeChecks.
# ---------------------------------------------------------------------------


class TestHandoffNestedTypeChecks(unittest.TestCase):
    """Handoff.__post_init__ rejects wrong types for nested record fields."""

    def test_reject_classification_wrong_type(self):
        with self.assertRaises(ValueError) as ctx:
            _make_valid(classification={"spec_number": "001"})
        self.assertIn("classification", str(ctx.exception))

    def test_reject_spec_seeds_wrong_type(self):
        with self.assertRaises(ValueError) as ctx:
            _make_valid(spec_seeds="not-a-spec-seeds")
        self.assertIn("spec_seeds", str(ctx.exception))

    def test_reject_provenance_wrong_type(self):
        with self.assertRaises(ValueError) as ctx:
            _make_valid(provenance=None)
        self.assertIn("provenance", str(ctx.exception))

    def test_reject_downstream_links_wrong_type(self):
        with self.assertRaises(ValueError) as ctx:
            _make_valid(downstream_links=None)
        self.assertIn("downstream_links", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestModuleConstants.
# ---------------------------------------------------------------------------


class TestModuleConstants(unittest.TestCase):
    """Module-level constants have expected values."""

    def test_schema_version_value(self):
        self.assertEqual(hs.SCHEMA_VERSION, "1.0")

    def test_handoff_kind_value(self):
        self.assertEqual(hs.HANDOFF_KIND, "specify")


# ---------------------------------------------------------------------------
# Plan 53 Phase 1 — DesignAnchor + SpecSeeds.design_anchor.
#
# specify's SpecSeeds carried exactly 8 fields before this plan (overview,
# acceptance_criteria, ac_subsection_na, constraints, affected_areas,
# out_of_scope, open_questions, risks) and NO design field -- design_anchor
# is net-new here, appended last with a default so the existing 8-field
# round-trip stays green.
# ---------------------------------------------------------------------------


class TestDesignAnchor(unittest.TestCase):
    def test_empty_default_is_well_formed(self):
        da = hs.DesignAnchor()
        self.assertEqual(da.kind, "")
        self.assertEqual(da.file, "")
        self.assertEqual(da.selectors, [])

    def test_non_html_kind_is_shape_valid(self):
        """D3: kind is an OPEN discriminator -- any string is shape-valid."""
        da = hs.DesignAnchor(kind="figma", file="https://figma.com/x", selectors=[".a"])
        self.assertEqual(da.kind, "figma")
        da2 = hs.DesignAnchor(kind="some-future-tool", file="x", selectors=[])
        self.assertEqual(da2.kind, "some-future-tool")

    def test_reject_non_string_kind(self):
        with self.assertRaises(ValueError) as ctx:
            hs.DesignAnchor(kind=123)
        self.assertIn("kind", str(ctx.exception))

    def test_reject_non_string_file(self):
        with self.assertRaises(ValueError) as ctx:
            hs.DesignAnchor(file=123)
        self.assertIn("file", str(ctx.exception))

    def test_reject_selectors_not_a_list(self):
        with self.assertRaises(ValueError) as ctx:
            hs.DesignAnchor(selectors="not-a-list")
        self.assertIn("selectors", str(ctx.exception))

    def test_reject_selectors_non_string_element(self):
        with self.assertRaises(ValueError) as ctx:
            hs.DesignAnchor(selectors=[".a", 2])
        self.assertIn("selectors", str(ctx.exception))

    def test_spec_seeds_default_design_anchor_is_empty_and_existing_8_fields_unchanged(self):
        """SpecSeeds constructed with exactly the pre-plan-53 8 fields (no
        design_anchor kwarg) still constructs cleanly, and design_anchor
        defaults to an empty DesignAnchor -- proves the 8-field shape is
        undisturbed and back-compat deserialization holds.
        """
        ss = hs.SpecSeeds(
            overview="Add structured audit log persistence to the EventService.",
            acceptance_criteria=[_ac()],
            ac_subsection_na={"ci_pipeline": "No CI changes required for this feature"},
            constraints=[_constraint()],
            affected_areas=[_affected_area()],
            out_of_scope=[_out_of_scope_item()],
            open_questions=[_open_question()],
            risks=[_risk()],
            # design_anchor intentionally omitted.
        )
        self.assertIsInstance(ss.design_anchor, hs.DesignAnchor)
        self.assertEqual(ss.design_anchor.kind, "")
        self.assertEqual(ss.design_anchor.file, "")
        self.assertEqual(ss.design_anchor.selectors, [])

    def test_spec_seeds_carries_captured_design_anchor(self):
        anchor = hs.DesignAnchor(kind="html", file="design/reference.html", selectors=[".fooBar"])
        ss = _spec_seeds(design_anchor=anchor)
        self.assertIs(ss.design_anchor, anchor)

    def test_spec_seeds_reject_design_anchor_wrong_type(self):
        with self.assertRaises(ValueError) as ctx:
            _spec_seeds(design_anchor={"kind": "html"})
        self.assertIn("design_anchor", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
