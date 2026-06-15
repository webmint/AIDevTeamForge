"""Tests for src/devforge/lib/_shared/findings_schema.py.

Coverage:
  Happy-path construction of Finding and AuditReport.
  JSON round-trip: build -> asdict -> json.dumps -> json.loads -> reconstruct.
  Every __post_init__ validation branch (one rejecting test per raise).
  Edge cases: line=-1 accepted, empty references/scope_files/top10/next_candidates,
  empty findings list accepted, empty lists for agent tracking fields.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import pytest

_LIB_DIR = Path(__file__).resolve().parents[3] / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _shared import findings_schema  # noqa: E402
from _shared.findings_schema import (  # noqa: E402
    Finding,
    SCHEMA_VERSION,
    SEVERITY_ENUM,
    CATEGORY_ENUM,
)
from _audit.hotspot_schema import FileScore  # noqa: E402
from _audit.report_schema import AuditReport, MODE_ENUM  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_finding(**overrides):
    """Return a valid Finding, overriding any fields."""
    defaults = dict(
        finding_id="F-001",
        agent="code-reviewer",
        severity="High",
        file="src/main.py",
        line=42,
        title="Off-by-one in loop",
        explanation="The loop runs one too many times.",
        suggested_fix="Change `<= n` to `< n`.",
        references=["https://example.com/ref"],
        source_pass="mislogic-hunt",
    )
    defaults.update(overrides)
    return Finding(**defaults)


def make_file_score(**overrides):
    """Return a valid FileScore."""
    defaults = dict(
        file="src/hot.py",
        churn=20,
        callers=8,
        size_loc=300,
        churn_norm=0.8,
        callers_norm=0.6,
        size_norm=0.4,
        score=0.74,
        rank=1,
    )
    defaults.update(overrides)
    return FileScore(**defaults)


def make_audit_report(**overrides):
    """Return a valid AuditReport, overriding any fields."""
    defaults = dict(
        schema_version=SCHEMA_VERSION,
        audit_date="2026-05-31",
        mode="narrow",
        scope_description="src/main.py",
        scope_files=["src/main.py"],
        agents_run=["code-reviewer", "architect"],
        agents_skipped=[],
        findings=[make_finding()],
        consensus={"F-001": ["code-reviewer", "architect"]},
        top10=["F-001"],
        recurring_issues_resolved=[],
        recurring_issues_unresolved=[],
        next_candidates=[],
    )
    defaults.update(overrides)
    return AuditReport(**defaults)


def reconstruct_finding(d):
    """Reconstruct Finding from plain dict."""
    return Finding(**d)


def reconstruct_file_score(d):
    """Reconstruct FileScore from plain dict."""
    return FileScore(**d)


def reconstruct_audit_report(d):
    """Reconstruct AuditReport from plain dict."""
    d = dict(d)
    d["findings"] = [reconstruct_finding(f) for f in d["findings"]]
    d["next_candidates"] = [reconstruct_file_score(x) for x in d["next_candidates"]]
    return AuditReport(**d)


# ---------------------------------------------------------------------------
# Happy-path construction
# ---------------------------------------------------------------------------

class TestFindingHappyPath:
    def test_basic_construction(self):
        f = make_finding()
        assert f.finding_id == "F-001"
        assert f.agent == "code-reviewer"
        assert f.severity == "High"
        assert f.file == "src/main.py"
        assert f.line == 42
        assert f.title == "Off-by-one in loop"
        assert f.source_pass == "mislogic-hunt"

    def test_all_severity_values_accepted(self):
        for sev in SEVERITY_ENUM:
            f = make_finding(severity=sev)
            assert f.severity == sev

    def test_line_negative_one_accepted(self):
        f = make_finding(line=-1)
        assert f.line == -1

    def test_line_one_accepted(self):
        f = make_finding(line=1)
        assert f.line == 1

    def test_line_large_accepted(self):
        f = make_finding(line=9999)
        assert f.line == 9999

    def test_empty_references_accepted(self):
        f = make_finding(references=[])
        assert f.references == []

    def test_multiple_references_accepted(self):
        refs = ["https://a.com", "https://b.com"]
        f = make_finding(references=refs)
        assert f.references == refs


class TestAuditReportHappyPath:
    def test_basic_construction(self):
        r = make_audit_report()
        assert r.schema_version == SCHEMA_VERSION
        assert r.audit_date == "2026-05-31"
        assert r.mode == "narrow"
        assert r.scope_description == "src/main.py"
        assert len(r.findings) == 1

    def test_all_mode_values_accepted(self):
        for mode in MODE_ENUM:
            r = make_audit_report(mode=mode)
            assert r.mode == mode

    def test_empty_findings_accepted(self):
        r = make_audit_report(findings=[])
        assert r.findings == []

    def test_empty_scope_files_accepted(self):
        r = make_audit_report(scope_files=[])
        assert r.scope_files == []

    def test_empty_top10_accepted(self):
        r = make_audit_report(top10=[])
        assert r.top10 == []

    def test_empty_next_candidates_accepted(self):
        r = make_audit_report(next_candidates=[])
        assert r.next_candidates == []

    def test_hotspot_mode_with_next_candidates(self):
        fs = make_file_score()
        r = make_audit_report(mode="hotspot", next_candidates=[fs])
        assert len(r.next_candidates) == 1
        assert isinstance(r.next_candidates[0], FileScore)

    def test_multiple_findings(self):
        f1 = make_finding(finding_id="F-001")
        f2 = make_finding(finding_id="F-002", severity="Critical")
        r = make_audit_report(findings=[f1, f2])
        assert len(r.findings) == 2

    def test_empty_agents_skipped(self):
        r = make_audit_report(agents_skipped=[])
        assert r.agents_skipped == []


# ---------------------------------------------------------------------------
# JSON round-trip
# ---------------------------------------------------------------------------

class TestFindingRoundTrip:
    def test_round_trip(self):
        original = make_finding()
        d = dataclasses.asdict(original)
        serialized = json.dumps(d)
        loaded = json.loads(serialized)
        reconstructed = reconstruct_finding(loaded)
        assert reconstructed == original

    def test_round_trip_with_empty_references(self):
        original = make_finding(references=[])
        d = dataclasses.asdict(original)
        reconstructed = reconstruct_finding(json.loads(json.dumps(d)))
        assert reconstructed == original

    def test_round_trip_line_negative_one(self):
        original = make_finding(line=-1)
        d = dataclasses.asdict(original)
        reconstructed = reconstruct_finding(json.loads(json.dumps(d)))
        assert reconstructed == original


class TestAuditReportRoundTrip:
    def test_round_trip_basic(self):
        original = make_audit_report()
        d = dataclasses.asdict(original)
        serialized = json.dumps(d)
        loaded = json.loads(serialized)
        reconstructed = reconstruct_audit_report(loaded)
        assert reconstructed == original

    def test_round_trip_with_next_candidates(self):
        fs = make_file_score()
        original = make_audit_report(mode="hotspot", next_candidates=[fs])
        d = dataclasses.asdict(original)
        serialized = json.dumps(d)
        loaded = json.loads(serialized)
        reconstructed = reconstruct_audit_report(loaded)
        assert reconstructed == original

    def test_round_trip_multiple_findings(self):
        f1 = make_finding(finding_id="F-001")
        f2 = make_finding(finding_id="F-002", severity="Critical", line=-1)
        original = make_audit_report(
            findings=[f1, f2],
            top10=["F-002", "F-001"],
        )
        d = dataclasses.asdict(original)
        serialized = json.dumps(d)
        loaded = json.loads(serialized)
        reconstructed = reconstruct_audit_report(loaded)
        assert reconstructed == original

    def test_round_trip_empty_everything(self):
        original = make_audit_report(
            findings=[],
            scope_files=[],
            agents_run=[],
            agents_skipped=[],
            top10=[],
            recurring_issues_resolved=[],
            recurring_issues_unresolved=[],
            next_candidates=[],
            consensus={},
        )
        d = dataclasses.asdict(original)
        reconstructed = reconstruct_audit_report(json.loads(json.dumps(d)))
        assert reconstructed == original


# ---------------------------------------------------------------------------
# Finding validation failures
# ---------------------------------------------------------------------------

class TestFindingValidation:
    def test_empty_finding_id_raises(self):
        with pytest.raises(ValueError, match="Finding.finding_id"):
            make_finding(finding_id="")

    def test_whitespace_finding_id_raises(self):
        with pytest.raises(ValueError, match="Finding.finding_id"):
            make_finding(finding_id="   ")

    def test_non_string_finding_id_raises(self):
        with pytest.raises(ValueError, match="Finding.finding_id"):
            make_finding(finding_id=1)

    def test_empty_agent_raises(self):
        with pytest.raises(ValueError, match="Finding.agent"):
            make_finding(agent="")

    def test_bad_severity_raises(self):
        with pytest.raises(ValueError, match="Finding.severity"):
            make_finding(severity="Warning")

    def test_empty_severity_raises(self):
        with pytest.raises(ValueError, match="Finding.severity"):
            make_finding(severity="")

    def test_empty_file_raises(self):
        with pytest.raises(ValueError, match="Finding.file"):
            make_finding(file="")

    def test_line_zero_raises(self):
        with pytest.raises(ValueError, match="Finding.line"):
            make_finding(line=0)

    def test_line_negative_two_raises(self):
        with pytest.raises(ValueError, match="Finding.line"):
            make_finding(line=-2)

    def test_line_large_negative_raises(self):
        with pytest.raises(ValueError, match="Finding.line"):
            make_finding(line=-100)

    def test_bool_line_raises(self):
        with pytest.raises(ValueError, match="Finding.line"):
            make_finding(line=True)

    def test_non_int_line_raises(self):
        with pytest.raises(ValueError, match="Finding.line"):
            make_finding(line=3.5)

    def test_empty_title_raises(self):
        with pytest.raises(ValueError, match="Finding.title"):
            make_finding(title="")

    def test_empty_explanation_raises(self):
        with pytest.raises(ValueError, match="Finding.explanation"):
            make_finding(explanation="")

    def test_empty_suggested_fix_raises(self):
        with pytest.raises(ValueError, match="Finding.suggested_fix"):
            make_finding(suggested_fix="")

    def test_references_not_list_raises(self):
        with pytest.raises(ValueError, match="Finding.references"):
            make_finding(references="https://example.com")

    def test_references_non_string_element_raises(self):
        with pytest.raises(ValueError, match="Finding.references"):
            make_finding(references=[42])

    def test_empty_source_pass_raises(self):
        with pytest.raises(ValueError, match="Finding.source_pass"):
            make_finding(source_pass="")

    def test_invalid_category_raises(self):
        with pytest.raises(ValueError, match="Finding.category"):
            make_finding(category="bogus")

    def test_empty_category_raises(self):
        with pytest.raises(ValueError, match="Finding.category"):
            make_finding(category="")

    def test_category_case_sensitive_raises(self):
        # "Mislogic" is not a valid value — enum is lower-case only.
        with pytest.raises(ValueError, match="Finding.category"):
            make_finding(category="Mislogic")


# ---------------------------------------------------------------------------
# Finding.category — valid values and default
# ---------------------------------------------------------------------------

class TestFindingCategory:
    def test_default_category_is_mislogic(self):
        """Backward-compat: omitting category yields 'mislogic'."""
        f = make_finding()
        assert f.category == "mislogic"

    def test_all_valid_category_values_accepted(self):
        """Every value in CATEGORY_ENUM constructs successfully."""
        for cat in CATEGORY_ENUM:
            f = make_finding(category=cat)
            assert f.category == cat

    def test_mislogic_explicit(self):
        f = make_finding(category="mislogic")
        assert f.category == "mislogic"

    def test_system_design(self):
        f = make_finding(category="system_design")
        assert f.category == "system_design"

    def test_best_practice(self):
        f = make_finding(category="best_practice")
        assert f.category == "best_practice"

    def test_duplication(self):
        f = make_finding(category="duplication")
        assert f.category == "duplication"

    def test_security(self):
        f = make_finding(category="security")
        assert f.category == "security"

    def test_blind_spot(self):
        f = make_finding(category="blind_spot")
        assert f.category == "blind_spot"

    def test_category_round_trip(self):
        """category survives dataclasses.asdict -> json -> reconstruct."""
        original = make_finding(category="security")
        d = dataclasses.asdict(original)
        reconstructed = reconstruct_finding(json.loads(json.dumps(d)))
        assert reconstructed.category == "security"
        assert reconstructed == original

    def test_category_default_round_trip(self):
        """Default category survives round-trip (backward-compat call sites)."""
        original = make_finding()  # no category kwarg
        d = dataclasses.asdict(original)
        reconstructed = reconstruct_finding(json.loads(json.dumps(d)))
        assert reconstructed.category == "mislogic"
        assert reconstructed == original

    def test_none_category_raises(self):
        """category=None must raise — guards Step 2/3 dict.get('category') -> None."""
        with pytest.raises(ValueError, match="Finding.category"):
            make_finding(category=None)

    def test_int_category_raises(self):
        """A non-string category must raise (enum membership rejects it)."""
        with pytest.raises(ValueError, match="Finding.category"):
            make_finding(category=42)


# ---------------------------------------------------------------------------
# AuditReport validation failures
# ---------------------------------------------------------------------------

class TestAuditReportValidation:
    def test_wrong_schema_version_raises(self):
        with pytest.raises(ValueError, match="schema_version"):
            make_audit_report(schema_version="99")

    def test_empty_schema_version_raises(self):
        with pytest.raises(ValueError, match="schema_version"):
            make_audit_report(schema_version="")

    def test_empty_audit_date_raises(self):
        with pytest.raises(ValueError, match="audit_date"):
            make_audit_report(audit_date="")

    def test_bad_mode_raises(self):
        with pytest.raises(ValueError, match="AuditReport.mode"):
            make_audit_report(mode="full")

    def test_empty_mode_raises(self):
        with pytest.raises(ValueError, match="AuditReport.mode"):
            make_audit_report(mode="")

    def test_empty_scope_description_raises(self):
        with pytest.raises(ValueError, match="scope_description"):
            make_audit_report(scope_description="")

    def test_scope_files_not_list_raises(self):
        with pytest.raises(ValueError, match="scope_files"):
            make_audit_report(scope_files="src/main.py")

    def test_scope_files_non_string_element_raises(self):
        with pytest.raises(ValueError, match="scope_files"):
            make_audit_report(scope_files=[123])

    def test_agents_run_not_list_raises(self):
        with pytest.raises(ValueError, match="agents_run"):
            make_audit_report(agents_run="code-reviewer")

    def test_agents_skipped_non_string_element_raises(self):
        with pytest.raises(ValueError, match="agents_skipped"):
            make_audit_report(agents_skipped=[None])

    def test_findings_not_list_raises(self):
        with pytest.raises(ValueError, match="findings"):
            make_audit_report(findings="not-a-list")

    def test_findings_wrong_element_type_raises(self):
        with pytest.raises(ValueError, match="findings"):
            make_audit_report(findings=["not-a-finding"])

    def test_consensus_not_dict_raises(self):
        with pytest.raises(ValueError, match="consensus"):
            make_audit_report(consensus=[("F-001", ["code-reviewer"])])

    def test_top10_not_list_raises(self):
        with pytest.raises(ValueError, match="top10"):
            make_audit_report(top10="F-001")

    def test_top10_non_string_element_raises(self):
        with pytest.raises(ValueError, match="top10"):
            make_audit_report(top10=[1])

    def test_recurring_issues_resolved_non_string_element_raises(self):
        with pytest.raises(ValueError, match="recurring_issues_resolved"):
            make_audit_report(recurring_issues_resolved=[42])

    def test_recurring_issues_unresolved_non_string_element_raises(self):
        with pytest.raises(ValueError, match="recurring_issues_unresolved"):
            make_audit_report(recurring_issues_unresolved=[None])

    def test_next_candidates_not_list_raises(self):
        with pytest.raises(ValueError, match="next_candidates"):
            make_audit_report(next_candidates="not-a-list")

    def test_next_candidates_wrong_element_type_raises(self):
        with pytest.raises(ValueError, match="next_candidates"):
            make_audit_report(next_candidates=["not-a-filescore"])
