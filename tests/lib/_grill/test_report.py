"""Tests for src/devforge/lib/_grill/_report.py.

Coverage:

render_report:
  - writes grill.md containing ## Confirmed Findings section
  - confirmed finding appears in headline section, not in appendix
  - contested ([CONTESTED] tag) finding appears in headline section
  - dismissed finding appears only in ## Dismissed / Worth a Glance appendix
  - uncertain finding appears only in ## Dismissed / Worth a Glance appendix
  - ## Disposition section present with the verdict for all four verdicts:
      PROCEED / REVISE-PLAN / RE-ENTER-UPSTREAM / KILL
  - RE-ENTER-UPSTREAM includes target stage in the Disposition section
  - ## Summary section present with correct counts + "Disposition: <verdict>"
  - invalid disposition string -> ValueError
  - RE-ENTER-UPSTREAM with None re_entry_target -> ValueError
  - RE-ENTER-UPSTREAM with bad re_entry_target -> ValueError
  - non-RE-ENTER-UPSTREAM with re_entry_target set -> ValueError
  - all-empty partition -> valid report, no crash, appendix absent
  - empty partition with PROCEED -> appendix absent, disposition PROCEED

write_grill_report:
  - creates grill.md in a temp feature_dir
  - returns correct path
  - creates feature_dir if it does not exist
  - overwrites on second call (idempotent path)

build_seed:
  - happy path: returns ReEntrySeed with correct fields
  - invalid target_stage -> ValueError (from ReEntrySeed.__post_init__)
  - cycle_count == 0 -> ValueError
  - cycle_count as bool -> ValueError
  - empty prior_conclusion -> ValueError
  - carried_findings with non-str element -> ValueError

write_seed:
  - writes grill-seed.json that round-trips back into a ReEntrySeed
  - fields are preserved exactly after round-trip
  - creates feature_dir on demand

Round-trip (real apply_verdicts):
  - Build a realistic partition via the real apply_verdicts function,
    render to grill.md via render_report + write_grill_report,
    and assert the structural invariants of the output file:
      * ## Disposition present
      * confirmed findings in headline
      * dismissed/uncertain in appendix
      * ## Summary has correct Disposition line
"""

from __future__ import annotations

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

from _grill._report import (  # noqa: E402
    DISPOSITION_VERDICTS,
    _UPSTREAM_STAGES,
    build_seed,
    render_report,
    write_grill_report,
    write_seed,
)
from _grill.seed_schema import (  # noqa: E402
    SEED_SCHEMA_VERSION,
    SEED_SOURCE,
    SEED_TARGET_STAGES,
    ReEntrySeed,
)
from _shared._verify import apply_verdicts  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers to build minimal finding dicts and partitions.
# ---------------------------------------------------------------------------


def _finding(
    file="plan.md",
    line=10,
    pattern="Missing error boundary",
    why="No fallback on API failure.",
    severity="High",
    confidence="Likely",
    category="mislogic",
    tags=None,
    finding_id=None,
):
    """Return a minimal finding dict matching the shape apply_verdicts produces."""
    return {
        "file": file,
        "line": line,
        "pattern": pattern,
        "why": why,
        "severity": severity,
        "confidence": confidence,
        "category": category,
        "tags": tags or [],
        "finding_id": finding_id,
        "evidence": "evidence snippet here",
    }


def _contested_finding(**overrides):
    """Return a finding tagged [CONTESTED]."""
    base = _finding(**overrides)
    base["tags"] = list(base.get("tags") or []) + ["[CONTESTED]"]
    base["confidence"] = "uncertain"
    return base


def _dismissed_finding(**overrides):
    """Return a simple dismissed finding dict (no special tags)."""
    return _finding(confidence="dismissed", **overrides)


def _minimal_render_kwargs(disposition="PROCEED", re_entry_target=None):
    """Return minimal keyword args for render_report."""
    return dict(
        partition={"confirmed": [], "dismissed": [], "uncertain": [], "contested": []},
        feature="specs/001-widget",
        date_str="2026-06-17",
        finders=["architect", "code-reviewer"],
        refuters=["qa-reviewer"],
        source_root="src/",
        framework="Python / FastAPI",
        n_scope_files=5,
        disposition=disposition,
        rationale="The plan logic is sound.",
        re_entry_target=re_entry_target,
    )


# ---------------------------------------------------------------------------
# Tests: render_report -- structural
# ---------------------------------------------------------------------------


class TestRenderReportStructure(unittest.TestCase):
    def test_header_present(self):
        kwargs = _minimal_render_kwargs()
        result = render_report(**kwargs)
        self.assertIn("# Plan Grill --", result)
        self.assertIn("specs/001-widget", result)
        self.assertIn("2026-06-17", result)

    def test_disposition_section_present_for_all_verdicts(self):
        for verdict in DISPOSITION_VERDICTS:
            target = "spec" if verdict == "RE-ENTER-UPSTREAM" else None
            kwargs = _minimal_render_kwargs(disposition=verdict, re_entry_target=target)
            result = render_report(**kwargs)
            self.assertIn("## Disposition", result, msg=verdict)
            self.assertIn("**Verdict**: {0}".format(verdict), result, msg=verdict)

    def test_re_enter_upstream_includes_target_stage_in_disposition(self):
        # Iterate only _UPSTREAM_STAGES (spec/discovery/research) -- "plan" is
        # a valid SEED_TARGET_STAGES entry for write-seed/build_seed but is NOT
        # a valid re_entry_target for RE-ENTER-UPSTREAM (REVISE-PLAN is the
        # correct disposition for same-stage plan revisions; "plan" passed here
        # raises ValueError per the _UPSTREAM_STAGES guard).
        for stage in _UPSTREAM_STAGES:
            kwargs = _minimal_render_kwargs(
                disposition="RE-ENTER-UPSTREAM", re_entry_target=stage
            )
            result = render_report(**kwargs)
            self.assertIn(stage, result)
            # Disposition line must include both verdict and target
            self.assertIn(
                "**Verdict**: RE-ENTER-UPSTREAM (target: `{0}`)".format(stage), result
            )

    def test_summary_section_present(self):
        kwargs = _minimal_render_kwargs()
        result = render_report(**kwargs)
        self.assertIn("## Summary", result)

    def test_summary_contains_disposition_line(self):
        for verdict in DISPOSITION_VERDICTS:
            target = "discovery" if verdict == "RE-ENTER-UPSTREAM" else None
            kwargs = _minimal_render_kwargs(disposition=verdict, re_entry_target=target)
            result = render_report(**kwargs)
            self.assertIn("- Disposition: {0}".format(verdict), result, msg=verdict)

    def test_confirmed_findings_section_present(self):
        kwargs = _minimal_render_kwargs()
        result = render_report(**kwargs)
        self.assertIn("## Confirmed Findings", result)

    def test_top_priorities_section_present(self):
        kwargs = _minimal_render_kwargs()
        result = render_report(**kwargs)
        self.assertIn("## Confirmed -- Top Priorities", result)

    def test_ends_with_newline(self):
        kwargs = _minimal_render_kwargs()
        result = render_report(**kwargs)
        self.assertTrue(result.endswith("\n"))


# ---------------------------------------------------------------------------
# Tests: render_report -- findings routing
# ---------------------------------------------------------------------------


class TestRenderReportFindingsRouting(unittest.TestCase):
    def _make_kwargs_with_all_buckets(self):
        confirmed = _finding(pattern="confirmed-pattern", finding_id="F-001")
        contested = _contested_finding(
            pattern="contested-pattern",
            finding_id="F-002",
            severity="High",
            category="security",
        )
        dismissed = _finding(pattern="dismissed-pattern", finding_id="D-001")
        uncertain = _finding(pattern="uncertain-pattern", finding_id="U-001")
        partition = {
            "confirmed": [confirmed],
            "contested": [contested],
            "dismissed": [dismissed],
            "uncertain": [uncertain],
        }
        kwargs = _minimal_render_kwargs()
        kwargs["partition"] = partition
        return kwargs

    def test_confirmed_finding_in_headline(self):
        result = render_report(**self._make_kwargs_with_all_buckets())
        # The confirmed finding's pattern must appear in the Confirmed Findings section
        # which comes before the appendix.
        self.assertIn("confirmed-pattern", result)
        # And it must NOT appear in the Dismissed section.
        dismissed_pos = result.find("## Dismissed")
        confirmed_pos = result.find("confirmed-pattern")
        self.assertGreater(dismissed_pos, -1)
        self.assertLess(confirmed_pos, dismissed_pos)

    def test_contested_finding_in_headline_flagged(self):
        result = render_report(**self._make_kwargs_with_all_buckets())
        self.assertIn("[CONTESTED]", result)
        # contested-pattern appears in headline, not appendix
        contested_pos = result.find("contested-pattern")
        dismissed_pos = result.find("## Dismissed")
        self.assertGreater(dismissed_pos, -1)
        self.assertLess(contested_pos, dismissed_pos)

    def test_dismissed_finding_in_appendix_only(self):
        result = render_report(**self._make_kwargs_with_all_buckets())
        self.assertIn("dismissed-pattern", result)
        # dismissed-pattern must appear AFTER ## Dismissed / Worth a Glance
        dismissed_section_pos = result.find("## Dismissed / Worth a Glance")
        dismissed_pattern_pos = result.find("dismissed-pattern")
        self.assertGreater(dismissed_section_pos, -1)
        self.assertGreater(dismissed_pattern_pos, dismissed_section_pos)

    def test_uncertain_finding_in_appendix_only(self):
        result = render_report(**self._make_kwargs_with_all_buckets())
        self.assertIn("uncertain-pattern", result)
        dismissed_section_pos = result.find("## Dismissed / Worth a Glance")
        uncertain_pattern_pos = result.find("uncertain-pattern")
        self.assertGreater(dismissed_section_pos, -1)
        self.assertGreater(uncertain_pattern_pos, dismissed_section_pos)

    def test_summary_counts_match_partition(self):
        result = render_report(**self._make_kwargs_with_all_buckets())
        self.assertIn("Confirmed: 1 | Contested: 1 | Dismissed: 1 | Uncertain: 1", result)

    def test_all_empty_partition_no_appendix(self):
        kwargs = _minimal_render_kwargs()
        result = render_report(**kwargs)
        self.assertNotIn("## Dismissed / Worth a Glance", result)

    def test_all_empty_partition_no_findings_message(self):
        kwargs = _minimal_render_kwargs()
        result = render_report(**kwargs)
        self.assertIn("(no confirmed findings)", result)

    def test_dismissed_only_appendix_present(self):
        partition = {
            "confirmed": [],
            "contested": [],
            "dismissed": [_finding(pattern="only-dismissed")],
            "uncertain": [],
        }
        kwargs = _minimal_render_kwargs()
        kwargs["partition"] = partition
        result = render_report(**kwargs)
        self.assertIn("## Dismissed / Worth a Glance", result)
        self.assertIn("only-dismissed", result)

    def test_uncertain_only_appendix_present(self):
        partition = {
            "confirmed": [],
            "contested": [],
            "dismissed": [],
            "uncertain": [_finding(pattern="only-uncertain")],
        }
        kwargs = _minimal_render_kwargs()
        kwargs["partition"] = partition
        result = render_report(**kwargs)
        self.assertIn("## Dismissed / Worth a Glance", result)
        self.assertIn("only-uncertain", result)

    def test_constitution_violation_tag_overrides_category_bucket(self):
        """A security-category finding tagged [CONSTITUTION-VIOLATION] must
        route to the Constitution Violations bucket (the tag takes priority
        over the category field per the bucket priority rules).

        The pattern appears twice: once in ## Confirmed -- Top Priorities, and
        once under the bucket heading in ## Confirmed Findings.  We assert on
        the occurrence that is inside the grouped-by-file section, i.e. after
        ## Confirmed Findings.
        """
        cv_finding = _finding(
            pattern="cv-tagged-security-finding",
            category="security",
            severity="High",
            tags=["[CONSTITUTION-VIOLATION]"],
            finding_id="F-CV1",
        )
        partition = {
            "confirmed": [cv_finding],
            "dismissed": [],
            "uncertain": [],
            "contested": [],
        }
        kwargs = _minimal_render_kwargs()
        kwargs["partition"] = partition
        result = render_report(**kwargs)

        # Locate the ## Confirmed Findings section (grouped-by-file section).
        confirmed_section_pos = result.find("## Confirmed Findings")
        self.assertGreater(confirmed_section_pos, -1,
                           "## Confirmed Findings section not found")

        # Find the Constitution Violations bucket heading INSIDE that section.
        cv_section_pos = result.find("#### Constitution Violations", confirmed_section_pos)
        self.assertGreater(cv_section_pos, -1,
                           "Constitution Violations bucket heading not found in "
                           "## Confirmed Findings section")

        # The pattern must appear AFTER the bucket heading (inside the bucket).
        pattern_pos = result.find("cv-tagged-security-finding", cv_section_pos)
        self.assertGreater(pattern_pos, cv_section_pos,
                           "cv finding did not appear under Constitution Violations bucket")

        # Confirm there is no Security bucket heading in the confirmed section
        # (because the tag override routes it away from Security entirely).
        security_bucket_pos = result.find("#### Security", confirmed_section_pos)
        self.assertEqual(security_bucket_pos, -1,
                         "Security bucket appeared in confirmed section but should not "
                         "(finding was routed to Constitution Violations)")

    def test_blind_spot_category_routes_to_mislogic_bucket(self):
        """A finding with category='blind_spot' must appear under the Mislogic
        bucket (blind_spot aliases to the mislogic display bucket).

        The pattern appears twice: once in ## Confirmed -- Top Priorities, and
        once under the bucket heading in ## Confirmed Findings.  We assert on
        the occurrence that is inside the grouped-by-file section.
        """
        bs_finding = _finding(
            pattern="blind-spot-finding",
            category="blind_spot",
            severity="Medium",
            finding_id="F-BS1",
        )
        partition = {
            "confirmed": [bs_finding],
            "dismissed": [],
            "uncertain": [],
            "contested": [],
        }
        kwargs = _minimal_render_kwargs()
        kwargs["partition"] = partition
        result = render_report(**kwargs)

        # Locate the ## Confirmed Findings section (grouped-by-file section).
        confirmed_section_pos = result.find("## Confirmed Findings")
        self.assertGreater(confirmed_section_pos, -1,
                           "## Confirmed Findings section not found")

        # Find the Mislogic bucket heading INSIDE that section.
        mislogic_section_pos = result.find("#### Mislogic", confirmed_section_pos)
        self.assertGreater(mislogic_section_pos, -1,
                           "Mislogic bucket heading not found in ## Confirmed Findings section")

        # The pattern must appear AFTER the Mislogic bucket heading.
        pattern_pos = result.find("blind-spot-finding", mislogic_section_pos)
        self.assertGreater(pattern_pos, mislogic_section_pos,
                           "blind_spot finding did not appear under Mislogic bucket")


# ---------------------------------------------------------------------------
# Tests: render_report -- disposition-specific guidance text
# ---------------------------------------------------------------------------


class TestRenderReportDispositionGuidance(unittest.TestCase):
    def test_proceed_guidance_text(self):
        result = render_report(**_minimal_render_kwargs(disposition="PROCEED"))
        self.assertIn("no disqualifying plan-level defect", result)

    def test_revise_plan_guidance_text(self):
        result = render_report(**_minimal_render_kwargs(disposition="REVISE-PLAN"))
        self.assertIn("correctable at the plan level", result)
        # Must route to /plan (not /breakdown) as the immediate next step.
        self.assertIn("re-run `/plan`", result)
        # /breakdown is mentioned only as the step AFTER /plan, not as the immediate next step.
        # The guidance string references /breakdown after "proceeding to", so it is present
        # but comes AFTER the /plan re-run instruction, not before it.
        self.assertIn("/breakdown", result)
        plan_pos = result.index("re-run `/plan`")
        breakdown_pos = result.index("/breakdown")
        self.assertLess(
            plan_pos,
            breakdown_pos,
            "re-run `/plan` must appear before `/breakdown` in the REVISE-PLAN guidance",
        )

    def test_re_enter_upstream_guidance_text(self):
        result = render_report(
            **_minimal_render_kwargs(
                disposition="RE-ENTER-UPSTREAM", re_entry_target="research"
            )
        )
        self.assertIn("rooted upstream", result)
        self.assertIn("grill-seed.json", result)

    def test_re_enter_upstream_spec_stage_uses_slash_specify(self):
        """re_entry_target='spec' must produce '/specify' in guidance, not '/spec'."""
        result = render_report(
            **_minimal_render_kwargs(
                disposition="RE-ENTER-UPSTREAM", re_entry_target="spec"
            )
        )
        self.assertIn("/specify", result)
        self.assertNotIn("`/spec`", result)

    def test_re_enter_upstream_discovery_stage_uses_slash_discover(self):
        """re_entry_target='discovery' must produce '/discover' in guidance,
        not '/discovery'."""
        result = render_report(
            **_minimal_render_kwargs(
                disposition="RE-ENTER-UPSTREAM", re_entry_target="discovery"
            )
        )
        self.assertIn("/discover", result)
        self.assertNotIn("`/discovery`", result)

    def test_re_enter_upstream_research_stage_uses_slash_research(self):
        """re_entry_target='research' must produce '/research' in guidance
        (already correct -- regression guard)."""
        result = render_report(
            **_minimal_render_kwargs(
                disposition="RE-ENTER-UPSTREAM", re_entry_target="research"
            )
        )
        self.assertIn("/research", result)

    def test_kill_guidance_text(self):
        result = render_report(**_minimal_render_kwargs(disposition="KILL"))
        self.assertIn("abandoned", result)


# ---------------------------------------------------------------------------
# Tests: render_report -- validation errors
# ---------------------------------------------------------------------------


class TestRenderReportValidation(unittest.TestCase):
    def test_invalid_disposition_raises_value_error(self):
        kwargs = _minimal_render_kwargs()
        kwargs["disposition"] = "BOGUS"
        with self.assertRaises(ValueError) as ctx:
            render_report(**kwargs)
        self.assertIn("BOGUS", str(ctx.exception))

    def test_re_enter_upstream_none_target_raises(self):
        kwargs = _minimal_render_kwargs(
            disposition="RE-ENTER-UPSTREAM", re_entry_target=None
        )
        with self.assertRaises(ValueError):
            render_report(**kwargs)

    def test_re_enter_upstream_bad_target_raises(self):
        kwargs = _minimal_render_kwargs(
            disposition="RE-ENTER-UPSTREAM", re_entry_target="bogus-stage"
        )
        with self.assertRaises(ValueError) as ctx:
            render_report(**kwargs)
        self.assertIn("bogus-stage", str(ctx.exception))

    def test_re_enter_upstream_plan_target_raises(self):
        # "plan" is valid in SEED_TARGET_STAGES (for write-seed/build_seed
        # with a REVISE-PLAN seed) but is NOT valid as a RE-ENTER-UPSTREAM
        # re_entry_target.  RE-ENTER-UPSTREAM means the defect is rooted in an
        # upstream stage (spec/discovery/research).  "plan" passed here must
        # raise ValueError per the _UPSTREAM_STAGES guard added in the
        # Design-X fix.
        kwargs = _minimal_render_kwargs(
            disposition="RE-ENTER-UPSTREAM", re_entry_target="plan"
        )
        with self.assertRaises(ValueError) as ctx:
            render_report(**kwargs)
        self.assertIn("plan", str(ctx.exception))

    def test_non_re_enter_with_target_raises(self):
        for verdict in ("PROCEED", "REVISE-PLAN", "KILL"):
            kwargs = _minimal_render_kwargs(
                disposition=verdict, re_entry_target="spec"
            )
            with self.assertRaises(ValueError, msg=verdict):
                render_report(**kwargs)


# ---------------------------------------------------------------------------
# Tests: write_grill_report
# ---------------------------------------------------------------------------


class TestWriteGrillReport(unittest.TestCase):
    def test_writes_grill_md(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "specs", "001-widget")
            os.makedirs(feature_dir)
            content = "# Test Report\n"
            path = write_grill_report(feature_dir, content)
            self.assertEqual(path, os.path.join(feature_dir, "grill.md"))
            with open(path, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), content)

    def test_creates_feature_dir_if_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "specs", "002-new")
            # Don't create the dir -- write_grill_report should do it.
            content = "hello\n"
            path = write_grill_report(feature_dir, content)
            self.assertTrue(os.path.isfile(path))

    def test_returns_correct_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            os.makedirs(feature_dir)
            path = write_grill_report(feature_dir, "x\n")
            self.assertTrue(path.endswith("grill.md"))
            self.assertTrue(path.startswith(feature_dir))

    def test_overwrite_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            os.makedirs(feature_dir)
            write_grill_report(feature_dir, "first\n")
            write_grill_report(feature_dir, "second\n")
            with open(os.path.join(feature_dir, "grill.md"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "second\n")

    def test_no_temp_files_left_behind(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            os.makedirs(feature_dir)
            write_grill_report(feature_dir, "content\n")
            files = os.listdir(feature_dir)
            temp_files = [f for f in files if f.startswith(".tmp-")]
            self.assertEqual(temp_files, [])


# ---------------------------------------------------------------------------
# Tests: build_seed
# ---------------------------------------------------------------------------


def _valid_seed_kwargs(**overrides):
    """Return valid build_seed kwargs, applying overrides."""
    defaults = dict(
        target_stage="spec",
        feature="feat-001-widget",
        prior_conclusion="Spec assumed sync processing was sufficient.",
        invalidating_evidence="grill F-001: queue depth exceeds 10k under load.",
        must_satisfy="Spec must address async processing explicitly.",
        cycle_count=1,
        carried_findings=[],
        provenance="specs/001-widget/plan.md",
    )
    defaults.update(overrides)
    return defaults


class TestBuildSeed(unittest.TestCase):
    def test_happy_path_returns_re_entry_seed(self):
        seed = build_seed(**_valid_seed_kwargs())
        self.assertIsInstance(seed, ReEntrySeed)

    def test_all_target_stages_accepted(self):
        for stage in SEED_TARGET_STAGES:
            seed = build_seed(**_valid_seed_kwargs(target_stage=stage))
            self.assertEqual(seed.target_stage, stage)

    def test_source_is_grill(self):
        seed = build_seed(**_valid_seed_kwargs())
        self.assertEqual(seed.source, SEED_SOURCE)

    def test_seed_version_is_schema_version(self):
        seed = build_seed(**_valid_seed_kwargs())
        self.assertEqual(seed.seed_version, SEED_SCHEMA_VERSION)

    def test_fields_preserved(self):
        kwargs = _valid_seed_kwargs(
            target_stage="research",
            feature="feat-007-payment",
            prior_conclusion="prior",
            invalidating_evidence="evidence",
            must_satisfy="must",
            cycle_count=3,
            carried_findings=["F-001: missing null check"],
            provenance="specs/007-payment/plan.md",
        )
        seed = build_seed(**kwargs)
        self.assertEqual(seed.target_stage, "research")
        self.assertEqual(seed.feature, "feat-007-payment")
        self.assertEqual(seed.prior_conclusion, "prior")
        self.assertEqual(seed.invalidating_evidence, "evidence")
        self.assertEqual(seed.must_satisfy, "must")
        self.assertEqual(seed.cycle_count, 3)
        self.assertEqual(seed.carried_findings, ["F-001: missing null check"])
        self.assertEqual(seed.provenance, "specs/007-payment/plan.md")

    def test_invalid_target_stage_raises(self):
        # "plan" was previously invalid here; it is now a valid stage per
        # Phase 1.  Use a genuinely bogus value.
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(target_stage="bogus"))

    def test_cycle_count_zero_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(cycle_count=0))

    def test_cycle_count_negative_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(cycle_count=-1))

    def test_cycle_count_bool_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(cycle_count=True))

    def test_empty_prior_conclusion_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(prior_conclusion=""))

    def test_empty_invalidating_evidence_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(invalidating_evidence=""))

    def test_empty_must_satisfy_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(must_satisfy="   "))

    def test_empty_feature_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(feature=""))

    def test_carried_findings_non_list_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(carried_findings="not-a-list"))

    def test_carried_findings_non_str_element_raises(self):
        with self.assertRaises(ValueError):
            build_seed(**_valid_seed_kwargs(carried_findings=[123]))

    def test_carried_findings_empty_list_accepted(self):
        seed = build_seed(**_valid_seed_kwargs(carried_findings=[]))
        self.assertEqual(seed.carried_findings, [])

    def test_carried_findings_with_items_accepted(self):
        seed = build_seed(**_valid_seed_kwargs(carried_findings=["a", "b"]))
        self.assertEqual(seed.carried_findings, ["a", "b"])


# ---------------------------------------------------------------------------
# Tests: write_seed -- round-trip
# ---------------------------------------------------------------------------


class TestWriteSeed(unittest.TestCase):
    def _make_seed(self, **overrides):
        return build_seed(**_valid_seed_kwargs(**overrides))

    def test_writes_grill_seed_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "specs", "001-widget")
            os.makedirs(feature_dir)
            seed = self._make_seed()
            path = write_seed(feature_dir, seed)
            self.assertEqual(path, os.path.join(feature_dir, "grill-seed.json"))
            self.assertTrue(os.path.isfile(path))

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
                target_stage="discovery",
                feature="feat-042-payment",
                prior_conclusion="Discovery assumed OAuth2 was sufficient.",
                invalidating_evidence="grill F-007: API does not support OAuth2 scopes.",
                must_satisfy="Discovery must re-examine auth mechanism.",
                cycle_count=2,
                carried_findings=["F-001: missing null check", "F-002: race on login"],
                provenance="specs/042-payment/plan.md",
            )
            path = write_seed(feature_dir, seed)
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)

            # Reconstruct from the JSON dict
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
            self.assertEqual(original, loaded)

    def test_json_is_valid(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            os.makedirs(feature_dir)
            seed = self._make_seed()
            path = write_seed(feature_dir, seed)
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertIsInstance(data, dict)
            self.assertIn("target_stage", data)
            self.assertIn("source", data)
            self.assertEqual(data["source"], SEED_SOURCE)

    def test_no_temp_files_left_behind(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            os.makedirs(feature_dir)
            seed = self._make_seed()
            write_seed(feature_dir, seed)
            files = os.listdir(feature_dir)
            temp_files = [f for f in files if f.startswith(".tmp-")]
            self.assertEqual(temp_files, [])

    def test_overwrite_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "feat")
            os.makedirs(feature_dir)
            seed1 = self._make_seed(cycle_count=1)
            seed2 = self._make_seed(cycle_count=2)
            write_seed(feature_dir, seed1)
            write_seed(feature_dir, seed2)
            path = os.path.join(feature_dir, "grill-seed.json")
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            self.assertEqual(data["cycle_count"], 2)


# ---------------------------------------------------------------------------
# Tests: build_seed NOT called for non-RE-ENTER-UPSTREAM verdicts (design test)
# ---------------------------------------------------------------------------


class TestSeedNotCalledForNonReEnterVerdicts(unittest.TestCase):
    """Structural test: render_report does not produce a grill-seed.json side-effect
    (build_seed and write_seed are separate functions the caller invokes only for
    RE-ENTER-UPSTREAM). This test confirms that render_report does NOT call write_seed
    internally for other verdicts."""

    def test_proceed_report_contains_no_seed_reference(self):
        result = render_report(**_minimal_render_kwargs(disposition="PROCEED"))
        # The seed section / filename should not appear in a PROCEED report
        # (it appears only in the RE-ENTER-UPSTREAM guidance text -- but as
        # "grill-seed.json" that is specific to RE-ENTER guidance, so absent here).
        self.assertNotIn("grill-seed.json", result)

    def test_revise_plan_report_contains_no_seed_reference(self):
        result = render_report(**_minimal_render_kwargs(disposition="REVISE-PLAN"))
        self.assertNotIn("grill-seed.json", result)

    def test_kill_report_contains_no_seed_reference(self):
        result = render_report(**_minimal_render_kwargs(disposition="KILL"))
        self.assertNotIn("grill-seed.json", result)

    def test_re_enter_upstream_report_contains_seed_reference(self):
        result = render_report(
            **_minimal_render_kwargs(
                disposition="RE-ENTER-UPSTREAM", re_entry_target="spec"
            )
        )
        self.assertIn("grill-seed.json", result)


# ---------------------------------------------------------------------------
# Tests: real apply_verdicts round-trip
# ---------------------------------------------------------------------------


class TestRealApplyVerdictsRoundTrip(unittest.TestCase):
    """Round-trip via the real apply_verdicts function to ensure the partition
    dict shape matches what render_report expects."""

    def _make_finding(self, fid, agent, severity="High", file_="plan.md", line=5,
                      pattern="test-pattern", category="mislogic", tags=None):
        """Build a finding dict (no verdict field -- verdicts are separate)."""
        return {
            "finding_id": fid,
            "agent": agent,
            "severity": severity,
            "file": file_,
            "line": line,
            "pattern": pattern,
            "why": "Because it is wrong.",
            "evidence": "quoted code",
            "confidence": "Likely",
            "category": category,
            "tags": list(tags or []),
        }

    def _make_verdict(self, file_, line, pattern, agent, verdict, justification="ok"):
        """Build a verdict dict matching apply_verdicts input shape."""
        return {
            "file": file_,
            "line": line,
            "pattern": pattern,
            "agent": agent,
            "verdict": verdict,
            "justification": justification,
            "evidence": "",
        }

    def test_full_round_trip_writes_grill_md(self):
        """Build a 4-bucket partition via apply_verdicts, render, write, assert."""
        findings = [
            self._make_finding("F-001", "code-reviewer",
                               pattern="confirmed-test-pattern"),
            self._make_finding("F-002", "architect",
                               pattern="dismissed-test-pattern"),
            self._make_finding("F-003", "qa-reviewer",
                               pattern="uncertain-test-pattern", severity="Info"),
            self._make_finding("F-004", "security-reviewer",
                               pattern="security-test-pattern",
                               category="security", severity="High"),
        ]

        verdicts = [
            self._make_verdict("plan.md", 5, "confirmed-test-pattern",
                               "code-reviewer", "confirmed"),
            self._make_verdict("plan.md", 5, "dismissed-test-pattern",
                               "architect", "dismissed"),
            self._make_verdict("plan.md", 5, "uncertain-test-pattern",
                               "qa-reviewer", "uncertain"),
            # security + uncertain -> high-stakes -> contested
            self._make_verdict("plan.md", 5, "security-test-pattern",
                               "security-reviewer", "uncertain"),
        ]

        partition = apply_verdicts(findings, verdicts)

        with tempfile.TemporaryDirectory() as tmpdir:
            feature_dir = os.path.join(tmpdir, "specs", "001-widget")
            os.makedirs(feature_dir)

            content = render_report(
                partition=partition,
                feature="specs/001-widget",
                date_str="2026-06-17",
                finders=["architect", "code-reviewer", "qa-reviewer", "security-reviewer"],
                refuters=["architect", "code-reviewer", "qa-reviewer"],
                source_root="src/",
                framework="Python / FastAPI",
                n_scope_files=3,
                disposition="REVISE-PLAN",
                rationale="The confirmed security finding requires a plan revision.",
            )

            path = write_grill_report(feature_dir, content)
            with open(path, encoding="utf-8") as fh:
                written = fh.read()

        # Structural invariants
        self.assertIn("## Disposition", written)
        self.assertIn("**Verdict**: REVISE-PLAN", written)
        self.assertIn("## Confirmed Findings", written)
        self.assertIn("## Summary", written)
        # confirmed finding in headline
        self.assertIn("confirmed-test-pattern", written)
        # dismissed in appendix
        self.assertIn("## Dismissed / Worth a Glance", written)
        self.assertIn("dismissed-test-pattern", written)
        # contested in headline
        self.assertIn("security-test-pattern", written)
        self.assertIn("[CONTESTED]", written)
        # No verdict / approve headings (grill is NOT a verdict command)
        self.assertNotIn("## APPROVED", written)
        self.assertNotIn("## REJECTED", written)


if __name__ == "__main__":
    unittest.main()
