"""Tests for src/devforge/lib/specify_helper.py.

Coverage matrix (Step 2 schemas + Step 3 Phase 0/1/1.5/2/3 subcommands +
cross-phase summary). Phase 4-5 subcommands ship next session per
SPECIFY-REDESIGN-PLAN.md.

Subprocess pattern: each test runs in its own tempfile.TemporaryDirectory.
Real subcommands (subprocess) produce fixture state — no hand-fabricated
JSON. Mirrors test_discover_helper / test_research_helper discipline.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Project layout: tests/lib/<this>.py → ../../ is repo root.
ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "src" / "devforge" / "lib"
sys.path.insert(0, str(LIB))

import specify_helper  # noqa: E402

HELPER = LIB / "specify_helper.py"


def _run(argv, cwd=None, env=None):
    cmd = [sys.executable, str(HELPER)] + list(argv)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        env=env or os.environ.copy(),
    )


def _setup_full_install(root: Path) -> None:
    """Create the 4-artefact valid install tree for preflight tests."""
    (root / ".devforge").mkdir(parents=True, exist_ok=True)
    (root / ".devforge" / "init.yaml").write_text(
        "workspace_mode: standalone\n", encoding="utf-8",
    )
    (root / ".devforge" / "configure.yaml").write_text(
        "project_name: x\n", encoding="utf-8",
    )
    (root / "docs").mkdir(exist_ok=True)
    (root / "docs" / "architecture.md").write_text(
        "# arch\n", encoding="utf-8",
    )
    (root / "constitution.md").write_text(
        "# Constitution\n\nRules.\n", encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Schema constants — Step 2.
# ---------------------------------------------------------------------------


class TestSchemaConstants(unittest.TestCase):
    def test_source_origin_enum(self):
        self.assertEqual(
            specify_helper.SOURCE_ORIGIN_ENUM,
            ("discover", "research", "prior_spec", "context"),
        )

    def test_spec_status_enum(self):
        self.assertEqual(
            specify_helper.SPEC_STATUS_ENUM,
            ("Draft", "Approved", "In Progress", "Complete"),
        )
        self.assertEqual(specify_helper.SPEC_STATUS_DEFAULT, "Draft")

    def test_spec_type_enum_5_values_with_greenfield(self):
        self.assertEqual(len(specify_helper.SPEC_TYPE_ENUM), 5)
        for needed in ("migration_tooling", "feature_addition",
                       "bug_fix", "refactor", "greenfield_feature"):
            self.assertIn(needed, specify_helper.SPEC_TYPE_ENUM)

    def test_landed_in_enum(self):
        self.assertEqual(
            specify_helper.LANDED_IN_ENUM,
            ("AC", "Constraint", "OOS", "Risk", "unlanded"),
        )
        self.assertEqual(specify_helper.LANDED_IN_DEFAULT, "unlanded")

    def test_dp_category_enum_7_locked_order(self):
        self.assertEqual(
            specify_helper.DP_CATEGORY_ENUM,
            (
                "scope_boundaries", "existing_behavior", "data_flow_state",
                "edge_cases", "ui_ux_details", "breaking_changes",
                "tooling_configuration",
            ),
        )

    def test_dp_status_enum_6(self):
        self.assertEqual(len(specify_helper.DP_STATUS_ENUM), 6)
        for needed in ("pending", "answered", "default_applied",
                       "deferred_OOS", "deferred_open_question",
                       "no_DP_in_category"):
            self.assertIn(needed, specify_helper.DP_STATUS_ENUM)

    def test_dp_coverage_state_enum(self):
        self.assertEqual(
            specify_helper.DP_COVERAGE_STATE_ENUM,
            ("Clear", "Partial", "Missing", "NoDPInCategory"),
        )

    def test_dp_turn_cap_3(self):
        self.assertEqual(specify_helper.DP_TURN_CAP, 3)

    def test_ac_subsection_enum_7_locked_order(self):
        self.assertEqual(
            specify_helper.AC_SUBSECTION_ENUM,
            (
                "tooling_artifact_presence",
                "behavior_preservation",
                "behavior_change",
                "ci_pipeline",
                "hooks_gates",
                "documentation",
                "hygiene",
            ),
        )

    def test_ac_ubiquitous_only_subsections(self):
        self.assertEqual(
            specify_helper.AC_UBIQUITOUS_ONLY_SUBSECTIONS,
            ("tooling_artifact_presence", "hygiene"),
        )

    def test_ears_variant_enum_5(self):
        self.assertEqual(len(specify_helper.EARS_VARIANT_ENUM), 5)
        self.assertEqual(
            set(specify_helper.EARS_VARIANT_ENUM),
            {"ubiquitous", "event_driven", "state_driven",
             "optional", "unwanted"},
        )

    def test_ears_regex_covers_every_variant(self):
        for v in specify_helper.EARS_VARIANT_ENUM:
            self.assertIn(v, specify_helper.EARS_REGEX)
            pattern = specify_helper.EARS_REGEX[v]
            self.assertIsNotNone(pattern, "regex missing for " + v)

    def test_ears_ubiquitous_regex_accepts_canonical(self):
        ok = "The repository shall contain no occurrences of `lerna`."
        self.assertIsNotNone(
            specify_helper.EARS_REGEX["ubiquitous"].match(ok)
        )

    def test_ears_event_driven_regex_accepts_canonical(self):
        ok = "WHEN the build finishes, the CI shall publish artifacts."
        self.assertIsNotNone(
            specify_helper.EARS_REGEX["event_driven"].match(ok)
        )

    def test_ears_unwanted_regex_accepts_canonical(self):
        ok = "IF the token is expired, THEN the system shall reject the request."
        self.assertIsNotNone(
            specify_helper.EARS_REGEX["unwanted"].match(ok)
        )

    def test_ears_state_driven_regex_accepts_canonical(self):
        ok = "WHILE the user is admin, the dashboard shall show debug info."
        self.assertIsNotNone(
            specify_helper.EARS_REGEX["state_driven"].match(ok)
        )

    def test_ears_optional_regex_accepts_canonical(self):
        ok = "WHERE the dark-mode flag is enabled, the UI shall use a dark palette."
        self.assertIsNotNone(
            specify_helper.EARS_REGEX["optional"].match(ok)
        )

    def test_ears_regex_rejects_freeform(self):
        bad = "System should sometimes maybe respond fast."
        for v in specify_helper.EARS_VARIANT_ENUM:
            self.assertIsNone(
                specify_helper.EARS_REGEX[v].match(bad),
                "{0} regex wrongly accepted free-form".format(v),
            )

    def test_conflict_type_enum(self):
        self.assertEqual(
            specify_helper.CONFLICT_TYPE_ENUM,
            ("direct", "drift", "refinement"),
        )

    def test_likelihood_impact_enums(self):
        self.assertEqual(specify_helper.LIKELIHOOD_ENUM, ("Low", "Med", "High"))
        self.assertEqual(specify_helper.IMPACT_ENUM, ("Low", "Med", "High"))

    def test_constraint_kind_enum(self):
        self.assertEqual(
            specify_helper.CONSTRAINT_KIND_ENUM,
            ("follow", "not_break", "nfr", "constitution_anchor", "external_system"),
        )

    def test_mode_detection_signals(self):
        self.assertEqual(
            specify_helper.AUTO_MODE_ENV_VAR, "DEVFORGE_AUTO_MODE",
        )
        self.assertEqual(
            specify_helper.AUTO_MODE_REMINDER_SUBSTRINGS,
            ("auto mode is active", "auto mode still active"),
        )

    def test_preflight_prereqs_match_existing_helpers(self):
        rels = [r for r, _ in specify_helper.PREFLIGHT_PREREQS]
        self.assertEqual(
            rels,
            [
                ".devforge/init.yaml",
                "docs/architecture.md",
                ".devforge/configure.yaml",
                "constitution.md",
            ],
        )

    def test_constitution_populate_guard_literal(self):
        self.assertEqual(
            specify_helper.CONSTITUTION_POPULATE_GUARDS,
            (
                "_Run constitute to populate_",
                "_Run /constitute to populate_",
                "_Run /devforge:constitute to populate_",
            ),
        )

    def test_phase1_mandatory_reads_4(self):
        self.assertEqual(
            specify_helper.PHASE1_MANDATORY_READS,
            (
                "constitution.md",
                ".claude/memory/MEMORY.md",
                "CLAUDE.md",
                "docs/architecture.md",
            ),
        )


# ---------------------------------------------------------------------------
# Default state.
# ---------------------------------------------------------------------------


class TestDefaultState(unittest.TestCase):
    def test_all_phase_buckets_present(self):
        s = specify_helper.default_state()
        for key in (
            "input_reads", "findings", "decision_points",
            "mandatory_reads", "discretionary_reads",
            "acceptance_criteria", "ac_subsection_na",
            "affected_areas", "out_of_scope", "constraints",
            "open_questions", "risks", "open_question_resolutions",
            "conflicts", "source_no_items_relevant",
        ):
            self.assertIn(key, s, "missing key: " + key)

    def test_lists_default_empty(self):
        s = specify_helper.default_state()
        for key in (
            "input_reads", "findings", "decision_points",
            "mandatory_reads", "discretionary_reads",
            "acceptance_criteria", "affected_areas", "out_of_scope",
            "constraints", "open_questions", "risks",
            "open_question_resolutions", "conflicts",
        ):
            self.assertEqual(s[key], [], "non-empty default for " + key)

    def test_dicts_default_empty(self):
        s = specify_helper.default_state()
        for key in ("ac_subsection_na", "source_no_items_relevant"):
            self.assertEqual(s[key], {})

    def test_phase_finalize_flags_false(self):
        s = specify_helper.default_state()
        for key in (
            "phase1_finalized", "findings_finalized",
            "dp_finalized", "phase3_finalized",
        ):
            self.assertFalse(s[key], "unexpected truthy " + key)

    def test_status_default_draft(self):
        s = specify_helper.default_state()
        self.assertEqual(s["status"], "Draft")

    def test_spec_type_default_none(self):
        s = specify_helper.default_state()
        self.assertIsNone(s["spec_type"])
        self.assertFalse(s["spec_type_seeded_by_upstream"])

    def test_header_classification_fields_present(self):
        s = specify_helper.default_state()
        for key in (
            "topic", "topic_slug", "date", "spec_number",
            "feature_name", "feature_slug", "spec_type",
            "spec_type_rationale", "status",
        ):
            self.assertIn(key, s)


# ---------------------------------------------------------------------------
# source_origin_for_path.
# ---------------------------------------------------------------------------


class TestSourceOriginForPath(unittest.TestCase):
    def test_discover_prefix(self):
        self.assertEqual(
            specify_helper.source_origin_for_path(
                "discover/2026-05-14-feature.md"
            ),
            "discover",
        )

    def test_research_prefix(self):
        self.assertEqual(
            specify_helper.source_origin_for_path(
                "research/2026-05-14-bug.md"
            ),
            "research",
        )

    def test_specs_prefix(self):
        self.assertEqual(
            specify_helper.source_origin_for_path(
                "specs/001-foo/spec.md"
            ),
            "prior_spec",
        )

    # -----------------------------------------------------------------
    # 68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 4 — filename-aware dispatch.
    # Both directions asserted per the plan's explicit test requirement:
    # the two new intake report basenames tag research/discover even
    # though they live under the same "specs/" prefix as prior_spec files,
    # and every OTHER specs/ file still tags prior_spec.
    # -----------------------------------------------------------------

    def test_specs_research_report_basename_tags_research(self):
        self.assertEqual(
            specify_helper.source_origin_for_path(
                "specs/001-auth-token-refresh/research-report.md"
            ),
            "research",
        )

    def test_specs_discovery_report_basename_tags_discover(self):
        self.assertEqual(
            specify_helper.source_origin_for_path(
                "specs/001-audit-log-persistence/discovery-report.md"
            ),
            "discover",
        )

    def test_specs_spec_md_still_tags_prior_spec_alongside_intake_files(self):
        """A prior_spec file coexists in the SAME feature dir as the intake
        reports — filename-aware dispatch must not over-broadly tag the
        whole dir; only the two known intake basenames flip to research/
        discover, spec.md (and everything else under specs/) stays
        prior_spec."""
        self.assertEqual(
            specify_helper.source_origin_for_path(
                "specs/001-auth-token-refresh/spec.md"
            ),
            "prior_spec",
        )

    def test_context_constitution(self):
        self.assertEqual(
            specify_helper.source_origin_for_path("constitution.md"),
            "context",
        )

    def test_context_memory(self):
        self.assertEqual(
            specify_helper.source_origin_for_path(
                ".claude/memory/MEMORY.md"
            ),
            "context",
        )

    def test_context_claude_md(self):
        self.assertEqual(
            specify_helper.source_origin_for_path("CLAUDE.md"),
            "context",
        )

    def test_context_docs(self):
        self.assertEqual(
            specify_helper.source_origin_for_path("docs/architecture.md"),
            "context",
        )

    def test_leading_dot_slash_stripped(self):
        self.assertEqual(
            specify_helper.source_origin_for_path("./discover/foo.md"),
            "discover",
        )

    def test_leading_whitespace_stripped(self):
        self.assertEqual(
            specify_helper.source_origin_for_path("  research/foo.md"),
            "research",
        )


# ---------------------------------------------------------------------------
# filename_matches_topic (Phase 1 adapter, F4 Option A).
# ---------------------------------------------------------------------------


class TestFilenameMatchesTopic(unittest.TestCase):
    def test_single_token_overlap_hits(self):
        self.assertTrue(
            specify_helper.filename_matches_topic(
                "2026-05-14-auth-token-refresh.md",
                "auth flow rewrite",
            )
        )

    def test_zero_overlap_misses(self):
        self.assertFalse(
            specify_helper.filename_matches_topic(
                "2026-05-14-billing-report.md",
                "auth flow rewrite",
            )
        )

    def test_case_insensitive(self):
        self.assertTrue(
            specify_helper.filename_matches_topic(
                "2026-05-14-AUTH-Token.md",
                "auth flow",
            )
        )

    def test_short_tokens_dropped(self):
        # "a", "of" do not produce false positives.
        self.assertFalse(
            specify_helper.filename_matches_topic(
                "a-of-the.md",
                "billing pipeline",
            )
        )

    def test_year_prefix_does_not_match(self):
        # Both files prefixed with "2026" must not match a topic
        # mentioning "2026" — year-like 4-digit tokens are suppressed.
        self.assertFalse(
            specify_helper.filename_matches_topic(
                "2026-05-14-billing.md",
                "auth flow 2026",
            )
        )

    def test_stopwords_dropped(self):
        # "the" must not produce false-positive overlap.
        self.assertFalse(
            specify_helper.filename_matches_topic(
                "the-thing.md",
                "the other matter",
            )
        )

    def test_hyphen_boundary_split(self):
        self.assertTrue(
            specify_helper.filename_matches_topic(
                "feature-auth-flow.md",
                "auth integration",
            )
        )


# ---------------------------------------------------------------------------
# reset-state / read-state.
# ---------------------------------------------------------------------------


class TestResetState(unittest.TestCase):
    def test_file_created(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            r = _run(["--devforge-dir", str(dev), "reset-state"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((dev / "specify-state.json").exists())

    def test_matches_default_state(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            r = _run(["--devforge-dir", str(dev), "reset-state"])
            self.assertEqual(r.returncode, 0, r.stderr)
            content = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(content, specify_helper.default_state())

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            for _ in range(3):
                r = _run(["--devforge-dir", str(dev), "reset-state"])
                self.assertEqual(r.returncode, 0, r.stderr)
            content = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(content, specify_helper.default_state())


class TestReadState(unittest.TestCase):
    def test_default_on_missing(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            r = _run(["--devforge-dir", str(dev), "read-state"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(
                json.loads(r.stdout), specify_helper.default_state()
            )

    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run(["--devforge-dir", str(dev), "read-state"])
            self.assertEqual(
                json.loads(r.stdout), specify_helper.default_state()
            )


# ---------------------------------------------------------------------------
# Preflight.
# ---------------------------------------------------------------------------


class TestPreflight(unittest.TestCase):
    def test_all_present_exits_0(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _setup_full_install(root)
            r = _run([
                "--devforge-dir", str(root / ".devforge"),
                "preflight", "--install-root", str(root),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_missing_constitution(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _setup_full_install(root)
            (root / "constitution.md").unlink()
            r = _run([
                "--devforge-dir", str(root / ".devforge"),
                "preflight", "--install-root", str(root),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("Missing: constitution.md", r.stderr)
            self.assertIn("BLOCKED", r.stderr)

    def test_missing_docs_architecture(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _setup_full_install(root)
            (root / "docs" / "architecture.md").unlink()
            r = _run([
                "--devforge-dir", str(root / ".devforge"),
                "preflight", "--install-root", str(root),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("docs/architecture.md", r.stderr)

    def test_missing_init_yaml(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _setup_full_install(root)
            (root / ".devforge" / "init.yaml").unlink()
            r = _run([
                "--devforge-dir", str(root / ".devforge"),
                "preflight", "--install-root", str(root),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn(".devforge/init.yaml", r.stderr)

    def test_missing_configure_yaml(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _setup_full_install(root)
            (root / ".devforge" / "configure.yaml").unlink()
            r = _run([
                "--devforge-dir", str(root / ".devforge"),
                "preflight", "--install-root", str(root),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn(".devforge/configure.yaml", r.stderr)

    def test_empty_file_treated_as_missing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _setup_full_install(root)
            (root / "docs" / "architecture.md").write_text(
                "", encoding="utf-8",
            )
            r = _run([
                "--devforge-dir", str(root / ".devforge"),
                "preflight", "--install-root", str(root),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("docs/architecture.md", r.stderr)

    def test_constitution_populate_guard_blocks(self):
        """Pre-namespace guard literal (with slash) -- never actually shipped
        by the stub template, but kept for back-compat with a hand-edited
        constitution.md carrying this exact text.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _setup_full_install(root)
            (root / "constitution.md").write_text(
                "# Constitution\n\n_Run /constitute to populate_\n",
                encoding="utf-8",
            )
            r = _run([
                "--devforge-dir", str(root / ".devforge"),
                "preflight", "--install-root", str(root),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("populate-guard", r.stderr)

    def test_constitution_populate_guard_blocks_legacy_no_slash_form(self):
        """Pre-namespace stub literal (no slash) -- the form every existing
        consumer install actually carries (src/constitution.md has always
        shipped this exact text).
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _setup_full_install(root)
            (root / "constitution.md").write_text(
                "# Constitution\n\n_Run constitute to populate_\n",
                encoding="utf-8",
            )
            r = _run([
                "--devforge-dir", str(root / ".devforge"),
                "preflight", "--install-root", str(root),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("populate-guard", r.stderr)

    def test_constitution_populate_guard_blocks_devforge_namespaced_form(self):
        """Post-namespace stub literal (current, plan 63 Phase 4c)."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _setup_full_install(root)
            (root / "constitution.md").write_text(
                "# Constitution\n\n_Run /devforge:constitute to populate_\n",
                encoding="utf-8",
            )
            r = _run([
                "--devforge-dir", str(root / ".devforge"),
                "preflight", "--install-root", str(root),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("populate-guard", r.stderr)

    def test_multiple_problems_all_listed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _setup_full_install(root)
            (root / "constitution.md").unlink()
            (root / ".devforge" / "init.yaml").unlink()
            r = _run([
                "--devforge-dir", str(root / ".devforge"),
                "preflight", "--install-root", str(root),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("init.yaml", r.stderr)
            self.assertIn("constitution.md", r.stderr)


# ---------------------------------------------------------------------------
# record-input-read.
# ---------------------------------------------------------------------------


class TestRecordInputRead(unittest.TestCase):
    def _setup(self, td: Path) -> Path:
        dev = td / ".devforge"
        r = _run(["--devforge-dir", str(dev), "reset-state"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return dev

    def test_auto_tag_discover(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            r = _run([
                "--devforge-dir", str(dev), "record-input-read",
                "--path", "discover/2026-05-14-foo.md",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(len(state["input_reads"]), 1)
            entry = state["input_reads"][0]
            self.assertEqual(entry["source_origin"], "discover")
            self.assertEqual(entry["path"], "discover/2026-05-14-foo.md")

    def test_auto_tag_research(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            _run([
                "--devforge-dir", str(dev), "record-input-read",
                "--path", "research/2026-05-14-bug.md",
            ])
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["input_reads"][0]["source_origin"], "research")

    def test_auto_tag_prior_spec(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            _run([
                "--devforge-dir", str(dev), "record-input-read",
                "--path", "specs/001-foo/spec.md",
            ])
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["input_reads"][0]["source_origin"], "prior_spec")

    def test_auto_tag_context(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            for path in ("constitution.md", ".claude/memory/MEMORY.md",
                         "CLAUDE.md", "docs/architecture.md"):
                _run([
                    "--devforge-dir", str(dev), "record-input-read",
                    "--path", path,
                ])
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(len(state["input_reads"]), 4)
            for entry in state["input_reads"]:
                self.assertEqual(entry["source_origin"], "context")

    def test_dedupe_same_path(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            for _ in range(3):
                _run([
                    "--devforge-dir", str(dev), "record-input-read",
                    "--path", "CLAUDE.md",
                ])
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(len(state["input_reads"]), 1)

    def test_iso_timestamp_present(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            _run([
                "--devforge-dir", str(dev), "record-input-read",
                "--path", "CLAUDE.md",
            ])
            state = json.loads((dev / "specify-state.json").read_text())
            ts = state["input_reads"][0]["read_timestamp"]
            self.assertRegex(
                ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
            )

    def test_empty_path_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            r = _run([
                "--devforge-dir", str(dev), "record-input-read",
                "--path", "   ",
            ])
            self.assertEqual(r.returncode, 2)


# ---------------------------------------------------------------------------
# phase1-finalize.
# ---------------------------------------------------------------------------


class TestPhase1Finalize(unittest.TestCase):
    def _record_all_4(self, dev: Path) -> None:
        for p in specify_helper.PHASE1_MANDATORY_READS:
            _run([
                "--devforge-dir", str(dev),
                "record-input-read", "--path", p,
            ])

    def test_all_4_present_exits_0(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            self._record_all_4(dev)
            r = _run(["--devforge-dir", str(dev), "phase1-finalize"])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertTrue(state["phase1_finalized"])

    def test_missing_one_exits_2(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            for p in specify_helper.PHASE1_MANDATORY_READS[:-1]:
                _run([
                    "--devforge-dir", str(dev),
                    "record-input-read", "--path", p,
                ])
            r = _run(["--devforge-dir", str(dev), "phase1-finalize"])
            self.assertEqual(r.returncode, 2)
            self.assertIn(
                specify_helper.PHASE1_MANDATORY_READS[-1], r.stderr,
            )
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertFalse(state["phase1_finalized"])

    def test_none_recorded_lists_all_4(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run(["--devforge-dir", str(dev), "phase1-finalize"])
            self.assertEqual(r.returncode, 2)
            for p in specify_helper.PHASE1_MANDATORY_READS:
                self.assertIn(p, r.stderr)

    def test_extra_optional_reads_do_not_block(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            self._record_all_4(dev)
            _run([
                "--devforge-dir", str(dev), "record-input-read",
                "--path", "discover/2026-05-14-foo.md",
            ])
            _run([
                "--devforge-dir", str(dev), "record-input-read",
                "--path", "research/2026-05-14-bug.md",
            ])
            r = _run(["--devforge-dir", str(dev), "phase1-finalize"])
            self.assertEqual(r.returncode, 0, r.stderr)


# ---------------------------------------------------------------------------
# record-finding.
# ---------------------------------------------------------------------------


class TestRecordFinding(unittest.TestCase):
    def test_basic_record_lands_unlanded(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "record-finding",
                "--source-path", "constitution.md",
                "--content", "Forbids global mutable state.",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "F-constitution-1")
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(len(state["findings"]), 1)
            f = state["findings"][0]
            self.assertEqual(f["source_path"], "constitution.md")
            self.assertEqual(f["landed_in"], "unlanded")
            self.assertEqual(f["finding_id"], "F-constitution-1")
            self.assertEqual(
                f["content"], "Forbids global mutable state.",
            )

    def test_finding_id_increments_per_source(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            for i in range(3):
                _run([
                    "--devforge-dir", str(dev), "record-finding",
                    "--source-path", "constitution.md",
                    "--content", "Item {0}.".format(i),
                ])
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(
                [f["finding_id"] for f in state["findings"]],
                ["F-constitution-1", "F-constitution-2", "F-constitution-3"],
            )

    def test_finding_id_per_source_slug(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev), "record-finding",
                "--source-path", "constitution.md",
                "--content", "C1.",
            ])
            _run([
                "--devforge-dir", str(dev), "record-finding",
                "--source-path", "research/2026-05-14-foo.md",
                "--content", "R1.",
            ])
            state = json.loads((dev / "specify-state.json").read_text())
            ids = [f["finding_id"] for f in state["findings"]]
            self.assertIn("F-constitution-1", ids)
            self.assertIn("F-2026-05-14-foo-1", ids)

    def test_landed_in_explicit_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "record-finding",
                "--source-path", "constitution.md",
                "--content", "x",
                "--landed-in", "AC",
                "--landed-ref", "AC-3",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["findings"][0]["landed_in"], "AC")
            self.assertEqual(state["findings"][0]["landed_ref"], "AC-3")

    def test_landed_in_rejects_bad_enum(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "record-finding",
                "--source-path", "constitution.md",
                "--content", "x",
                "--landed-in", "Bogus",
            ])
            self.assertEqual(r.returncode, 2)

    def test_empty_content_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "record-finding",
                "--source-path", "constitution.md",
                "--content", "   ",
            ])
            self.assertEqual(r.returncode, 2)

    def test_recording_clears_no_items_marker(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev),
                "record-input-read", "--path", "CLAUDE.md",
            ])
            _run([
                "--devforge-dir", str(dev),
                "mark-source-no-items-relevant",
                "--source-path", "CLAUDE.md",
            ])
            _run([
                "--devforge-dir", str(dev), "record-finding",
                "--source-path", "CLAUDE.md",
                "--content", "Actually relevant after all.",
            ])
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertNotIn("CLAUDE.md", state["source_no_items_relevant"])


# ---------------------------------------------------------------------------
# mark-source-no-items-relevant.
# ---------------------------------------------------------------------------


class TestMarkSourceNoItemsRelevant(unittest.TestCase):
    def test_basic_marker(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev),
                "record-input-read", "--path", "CLAUDE.md",
            ])
            r = _run([
                "--devforge-dir", str(dev),
                "mark-source-no-items-relevant",
                "--source-path", "CLAUDE.md",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertTrue(
                state["source_no_items_relevant"].get("CLAUDE.md")
            )

    def test_rejects_unread_source(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev),
                "mark-source-no-items-relevant",
                "--source-path", "CLAUDE.md",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("not in input_reads", r.stderr)

    def test_rejects_when_findings_exist(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev),
                "record-input-read", "--path", "CLAUDE.md",
            ])
            _run([
                "--devforge-dir", str(dev), "record-finding",
                "--source-path", "CLAUDE.md", "--content", "found",
            ])
            r = _run([
                "--devforge-dir", str(dev),
                "mark-source-no-items-relevant",
                "--source-path", "CLAUDE.md",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("already has findings", r.stderr)


# ---------------------------------------------------------------------------
# verify-findings.
# ---------------------------------------------------------------------------


class TestVerifyFindings(unittest.TestCase):
    def _seed(
        self,
        dev: Path,
        per_source: dict,
        marker_paths=(),
    ) -> None:
        _run(["--devforge-dir", str(dev), "reset-state"])
        for path, n in per_source.items():
            _run([
                "--devforge-dir", str(dev),
                "record-input-read", "--path", path,
            ])
            for i in range(n):
                _run([
                    "--devforge-dir", str(dev), "record-finding",
                    "--source-path", path,
                    "--content", "{0} bullet {1}.".format(path, i),
                ])
        for path in marker_paths:
            _run([
                "--devforge-dir", str(dev),
                "record-input-read", "--path", path,
            ])
            _run([
                "--devforge-dir", str(dev),
                "mark-source-no-items-relevant",
                "--source-path", path,
            ])

    def test_3_per_source_exits_0(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            self._seed(dev, {
                "constitution.md": 3,
                ".claude/memory/MEMORY.md": 4,
                "CLAUDE.md": 3,
                "docs/architecture.md": 5,
            })
            r = _run(["--devforge-dir", str(dev), "verify-findings"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_2_findings_per_source_fails(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            self._seed(dev, {"constitution.md": 2})
            r = _run(["--devforge-dir", str(dev), "verify-findings"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("constitution.md", r.stderr)
            self.assertIn("partial", r.stderr)

    def test_no_items_relevant_marker_waives(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            self._seed(
                dev,
                {"constitution.md": 3},
                marker_paths=("CLAUDE.md",),
            )
            r = _run(["--devforge-dir", str(dev), "verify-findings"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_read_with_zero_findings_no_marker_fails(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev),
                "record-input-read", "--path", "CLAUDE.md",
            ])
            r = _run(["--devforge-dir", str(dev), "verify-findings"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("CLAUDE.md", r.stderr)

    def test_no_reads_no_problems(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run(["--devforge-dir", str(dev), "verify-findings"])
            self.assertEqual(r.returncode, 0)


# ---------------------------------------------------------------------------
# render-findings.
# ---------------------------------------------------------------------------


class TestRenderFindings(unittest.TestCase):
    def test_header_emitted(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev),
                "record-input-read", "--path", "constitution.md",
            ])
            for i in range(3):
                _run([
                    "--devforge-dir", str(dev), "record-finding",
                    "--source-path", "constitution.md",
                    "--content", "Bullet {0}.".format(i),
                ])
            r = _run(["--devforge-dir", str(dev), "render-findings"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("## Findings from Inputs", r.stdout)
            self.assertIn("### From constitution.md", r.stdout)
            self.assertIn("1. Bullet 0.", r.stdout)
            self.assertIn("3. Bullet 2.", r.stdout)

    def test_discover_subheading_renders(self):
        # F3 fix — discover/ block must appear when discover source read.
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            path = "discover/2026-05-14-foo.md"
            _run([
                "--devforge-dir", str(dev),
                "record-input-read", "--path", path,
            ])
            for i in range(3):
                _run([
                    "--devforge-dir", str(dev), "record-finding",
                    "--source-path", path,
                    "--content", "D-bullet {0}.".format(i),
                ])
            r = _run(["--devforge-dir", str(dev), "render-findings"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("### From {0}".format(path), r.stdout)
            self.assertIn("1. D-bullet 0.", r.stdout)

    def test_no_items_relevant_marker_rendered(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev),
                "record-input-read", "--path", "CLAUDE.md",
            ])
            _run([
                "--devforge-dir", str(dev),
                "mark-source-no-items-relevant",
                "--source-path", "CLAUDE.md",
            ])
            r = _run(["--devforge-dir", str(dev), "render-findings"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("### From CLAUDE.md", r.stdout)
            self.assertIn("No items relevant to this spec.", r.stdout)

    def test_unread_section_omitted(self):
        # Sources never recorded as reads must not produce headings.
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev),
                "record-input-read", "--path", "constitution.md",
            ])
            for i in range(3):
                _run([
                    "--devforge-dir", str(dev), "record-finding",
                    "--source-path", "constitution.md",
                    "--content", "c{0}".format(i),
                ])
            r = _run(["--devforge-dir", str(dev), "render-findings"])
            self.assertNotIn("### From CLAUDE.md", r.stdout)
            self.assertNotIn("### From docs/", r.stdout)
            self.assertNotIn("### From discover/", r.stdout)

    def test_section_ordering(self):
        # constitution > MEMORY > research/ > discover/ > CLAUDE > docs/ > specs/
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            paths_in_random_order = [
                "specs/001-foo/spec.md",
                "docs/architecture.md",
                "CLAUDE.md",
                "discover/2026-05-14-x.md",
                "research/2026-05-14-y.md",
                ".claude/memory/MEMORY.md",
                "constitution.md",
            ]
            for p in paths_in_random_order:
                _run([
                    "--devforge-dir", str(dev),
                    "record-input-read", "--path", p,
                ])
                for i in range(3):
                    _run([
                        "--devforge-dir", str(dev), "record-finding",
                        "--source-path", p,
                        "--content", "{0} item {1}".format(p, i),
                    ])
            r = _run(["--devforge-dir", str(dev), "render-findings"])
            self.assertEqual(r.returncode, 0, r.stderr)
            out = r.stdout
            positions = {p: out.find("### From " + p) for p in paths_in_random_order}
            for p, pos in positions.items():
                self.assertGreaterEqual(pos, 0, "heading missing: " + p)
            # Locked order — every later section's heading position > prior.
            order = [
                "constitution.md",
                ".claude/memory/MEMORY.md",
                "research/2026-05-14-y.md",
                "discover/2026-05-14-x.md",
                "CLAUDE.md",
                "docs/architecture.md",
                "specs/001-foo/spec.md",
            ]
            for a, b in zip(order, order[1:]):
                self.assertLess(
                    positions[a], positions[b],
                    "{0} should render before {1}".format(a, b),
                )


# ---------------------------------------------------------------------------
# findings-finalize.
# ---------------------------------------------------------------------------


class TestFindingsFinalize(unittest.TestCase):
    def test_gate_passes_when_per_source_clear(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev),
                "record-input-read", "--path", "constitution.md",
            ])
            for i in range(3):
                _run([
                    "--devforge-dir", str(dev), "record-finding",
                    "--source-path", "constitution.md",
                    "--content", "x{0}".format(i),
                ])
            r = _run(["--devforge-dir", str(dev), "findings-finalize"])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertTrue(state["findings_finalized"])

    def test_gate_fails_on_partial_source(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev),
                "record-input-read", "--path", "constitution.md",
            ])
            _run([
                "--devforge-dir", str(dev), "record-finding",
                "--source-path", "constitution.md",
                "--content", "only-one",
            ])
            r = _run(["--devforge-dir", str(dev), "findings-finalize"])
            self.assertEqual(r.returncode, 2)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertFalse(state["findings_finalized"])


# ---------------------------------------------------------------------------
# Atomicity — body-raising transaction leaves state intact.
# ---------------------------------------------------------------------------


class TestStateAtomicity(unittest.TestCase):
    def test_no_tmp_files_left_after_normal_ops(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev),
                "record-input-read", "--path", "CLAUDE.md",
            ])
            tmp_residue = list(dev.glob("specify-*.json.tmp"))
            self.assertEqual(tmp_residue, [], "atomic-write debris")

    def test_state_transaction_on_failure_preserves_state(self):
        """Body-raising _state_transaction skips write."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            sentinel_path = dev / "specify-state.json"
            before = sentinel_path.read_text()
            with self.assertRaises(RuntimeError):
                with specify_helper._state_transaction(dev) as state:
                    state["topic"] = "ignored — should not persist"
                    raise RuntimeError("simulated failure")
            after = sentinel_path.read_text()
            self.assertEqual(before, after)


# ---------------------------------------------------------------------------
# Phase 2 — detect-mode (C-strict, no LLM judgment).
# ---------------------------------------------------------------------------


class TestDetectModePure(unittest.TestCase):
    """Unit-test pure detect_mode() — env / flag / reminder substring."""

    def test_default_interactive(self):
        self.assertEqual(
            specify_helper.detect_mode({}, False, ""), "interactive",
        )

    def test_env_var_triggers_auto(self):
        self.assertEqual(
            specify_helper.detect_mode(
                {"DEVFORGE_AUTO_MODE": "1"}, False, "",
            ),
            "auto",
        )

    def test_env_var_value_2_does_not_trigger(self):
        self.assertEqual(
            specify_helper.detect_mode(
                {"DEVFORGE_AUTO_MODE": "2"}, False, "",
            ),
            "interactive",
        )

    def test_flag_triggers_auto(self):
        self.assertEqual(
            specify_helper.detect_mode({}, True, ""), "auto",
        )

    def test_reminder_substring_is_active(self):
        self.assertEqual(
            specify_helper.detect_mode(
                {}, False, "AUTO MODE IS ACTIVE per project conventions",
            ),
            "auto",
        )

    def test_reminder_substring_still_active(self):
        self.assertEqual(
            specify_helper.detect_mode(
                {}, False, "...auto mode still active...",
            ),
            "auto",
        )

    def test_reminder_case_insensitive(self):
        self.assertEqual(
            specify_helper.detect_mode(
                {}, False, "Auto Mode Is Active",
            ),
            "auto",
        )

    def test_reminder_no_substring_stays_interactive(self):
        self.assertEqual(
            specify_helper.detect_mode(
                {}, False,
                "User wants automation but no exact substring match.",
            ),
            "interactive",
        )

    def test_natural_language_prose_ignored(self):
        # Per Variance rule #8 — only literal substrings count.
        self.assertEqual(
            specify_helper.detect_mode(
                {}, False, "please run in auto mode for me",
            ),
            "interactive",
        )


class TestDetectModeSubcommand(unittest.TestCase):
    def test_interactive_default_persisted(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run(["--devforge-dir", str(dev), "detect-mode"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "interactive")
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["mode"], "interactive")

    def test_auto_via_env(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            env = os.environ.copy()
            env["DEVFORGE_AUTO_MODE"] = "1"
            r = _run(
                ["--devforge-dir", str(dev), "detect-mode"], env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "auto")
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["mode"], "auto")

    def test_auto_via_flag(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "detect-mode", "--auto",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "auto")

    def test_auto_via_reminder_text(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "detect-mode",
                "--reminder-text",
                "...some context... auto mode is active ...end...",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "auto")


# ---------------------------------------------------------------------------
# Phase 2 — record-decision-point.
# ---------------------------------------------------------------------------


class TestRecordDecisionPoint(unittest.TestCase):
    def _setup(self, td: Path) -> Path:
        dev = td / ".devforge"
        r = _run(["--devforge-dir", str(dev), "reset-state"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return dev

    def test_basic_record_pending(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            r = _run([
                "--devforge-dir", str(dev), "record-decision-point",
                "--category", "scope_boundaries",
                "--description", "Touch only module X or modules X+Y?",
                "--valid-implementations",
                json.dumps(["X only", "X and Y"]),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "DP-scope_boundaries-1")
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(len(state["decision_points"]), 1)
            dp = state["decision_points"][0]
            self.assertEqual(dp["status"], "pending")
            self.assertEqual(dp["category"], "scope_boundaries")
            self.assertEqual(dp["valid_implementations"], ["X only", "X and Y"])
            self.assertEqual(dp["turns"], 0)

    def test_dp_id_increments_per_category(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            for i in range(3):
                _run([
                    "--devforge-dir", str(dev), "record-decision-point",
                    "--category", "edge_cases",
                    "--description", "Case {0}?".format(i),
                    "--valid-implementations", json.dumps(["a", "b"]),
                ])
            state = json.loads((dev / "specify-state.json").read_text())
            ids = [d["dp_id"] for d in state["decision_points"]]
            self.assertEqual(
                ids,
                ["DP-edge_cases-1", "DP-edge_cases-2", "DP-edge_cases-3"],
            )

    def test_rejects_unknown_category(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            r = _run([
                "--devforge-dir", str(dev), "record-decision-point",
                "--category", "bogus_category",
                "--description", "x",
                "--valid-implementations", json.dumps(["a", "b"]),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("category", r.stderr)

    def test_rejects_single_implementation(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            r = _run([
                "--devforge-dir", str(dev), "record-decision-point",
                "--category", "scope_boundaries",
                "--description", "x",
                "--valid-implementations", json.dumps(["only one"]),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("≥2", r.stderr)

    def test_rejects_non_array_valid_implementations(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            r = _run([
                "--devforge-dir", str(dev), "record-decision-point",
                "--category", "scope_boundaries",
                "--description", "x",
                "--valid-implementations", json.dumps({"a": "b"}),
            ])
            self.assertEqual(r.returncode, 2)

    def test_rejects_invalid_json(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            r = _run([
                "--devforge-dir", str(dev), "record-decision-point",
                "--category", "scope_boundaries",
                "--description", "x",
                "--valid-implementations", "[oops",
            ])
            self.assertEqual(r.returncode, 2)

    def test_no_dp_in_category_marker(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            r = _run([
                "--devforge-dir", str(dev), "record-decision-point",
                "--category", "ui_ux_details",
                "--description",
                "Spec touches CLI only — no UI surface affected.",
                "--no-dp-in-category",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            dp = state["decision_points"][0]
            self.assertEqual(dp["status"], "no_DP_in_category")
            self.assertEqual(dp["valid_implementations"], [])


# ---------------------------------------------------------------------------
# Phase 2 — set-dp-answer / set-dp-default-applied / set-dp-deferral.
# ---------------------------------------------------------------------------


class TestSetDpSetters(unittest.TestCase):
    def _setup_with_dp(self, td: Path, mode: str) -> Path:
        dev = td / ".devforge"
        _run(["--devforge-dir", str(dev), "reset-state"])
        # Force mode by writing state directly via setter helper.
        # detect-mode used so persisted mode matches.
        if mode == "auto":
            _run([
                "--devforge-dir", str(dev), "detect-mode", "--auto",
            ])
        else:
            _run(["--devforge-dir", str(dev), "detect-mode"])
        _run([
            "--devforge-dir", str(dev), "record-decision-point",
            "--category", "scope_boundaries",
            "--description", "narrow or broad?",
            "--valid-implementations", json.dumps(["narrow", "broad"]),
        ])
        return dev

    def test_set_answer_interactive_ok(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup_with_dp(Path(td), "interactive")
            r = _run([
                "--devforge-dir", str(dev), "set-dp-answer",
                "--dp-id", "DP-scope_boundaries-1",
                "--user-answer", "narrow",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            dp = state["decision_points"][0]
            self.assertEqual(dp["status"], "answered")
            self.assertEqual(dp["user_answer"], "narrow")

    def test_set_answer_rejected_in_auto_mode(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup_with_dp(Path(td), "auto")
            r = _run([
                "--devforge-dir", str(dev), "set-dp-answer",
                "--dp-id", "DP-scope_boundaries-1",
                "--user-answer", "narrow",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("auto", r.stderr)

    def test_set_default_applied_auto_ok(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup_with_dp(Path(td), "auto")
            r = _run([
                "--devforge-dir", str(dev), "set-dp-default-applied",
                "--dp-id", "DP-scope_boundaries-1",
                "--default-applied", "narrow",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            dp = state["decision_points"][0]
            self.assertEqual(dp["status"], "default_applied")
            self.assertEqual(dp["default_applied"], "narrow")

    def test_set_default_applied_rejected_in_interactive(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup_with_dp(Path(td), "interactive")
            r = _run([
                "--devforge-dir", str(dev), "set-dp-default-applied",
                "--dp-id", "DP-scope_boundaries-1",
                "--default-applied", "narrow",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("interactive", r.stderr)

    def test_set_answer_unknown_dp_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup_with_dp(Path(td), "interactive")
            r = _run([
                "--devforge-dir", str(dev), "set-dp-answer",
                "--dp-id", "DP-bogus-99",
                "--user-answer", "x",
            ])
            self.assertEqual(r.returncode, 2)

    def test_set_deferral_oos_basic(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup_with_dp(Path(td), "interactive")
            r = _run([
                "--devforge-dir", str(dev), "set-dp-deferral",
                "--dp-id", "DP-scope_boundaries-1",
                "--deferral-kind", "OOS",
                "--reason", "scope-creep — defer to v2",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            dp = state["decision_points"][0]
            self.assertEqual(dp["status"], "deferred_OOS")
            self.assertEqual(dp["deferral_reason"], "scope-creep — defer to v2")
            self.assertEqual(dp["turns"], 0)

    def test_set_deferral_open_question_basic(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup_with_dp(Path(td), "interactive")
            r = _run([
                "--devforge-dir", str(dev), "set-dp-deferral",
                "--dp-id", "DP-scope_boundaries-1",
                "--deferral-kind", "open_question",
                "--reason", "needs PM input post-spec",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            dp = state["decision_points"][0]
            self.assertEqual(dp["status"], "deferred_open_question")
            self.assertEqual(dp["deferral_reason"], "needs PM input post-spec")

    def test_increment_turn_bumps_counter(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup_with_dp(Path(td), "interactive")
            r = _run([
                "--devforge-dir", str(dev), "set-dp-deferral",
                "--dp-id", "DP-scope_boundaries-1",
                "--deferral-kind", "OOS",
                "--reason", "round 1",
                "--increment-turn",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["decision_points"][0]["turns"], 1)
            # Status reflects supplied kind because turns < cap.
            self.assertEqual(
                state["decision_points"][0]["status"], "deferred_OOS",
            )

    def test_turn_cap_forces_open_question(self):
        # 3 increments → turns=3 == DP_TURN_CAP → forced open_question.
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup_with_dp(Path(td), "interactive")
            for i in range(3):
                _run([
                    "--devforge-dir", str(dev), "set-dp-deferral",
                    "--dp-id", "DP-scope_boundaries-1",
                    "--deferral-kind", "OOS",
                    "--reason", "round {0}".format(i),
                    "--increment-turn",
                ])
            state = json.loads((dev / "specify-state.json").read_text())
            dp = state["decision_points"][0]
            self.assertEqual(dp["turns"], 3)
            self.assertEqual(dp["status"], "deferred_open_question")
            self.assertEqual(
                dp["deferral_reason"],
                specify_helper.DP_TURN_CAP_REASON,
            )

    def test_set_deferral_unknown_kind_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup_with_dp(Path(td), "interactive")
            r = _run([
                "--devforge-dir", str(dev), "set-dp-deferral",
                "--dp-id", "DP-scope_boundaries-1",
                "--deferral-kind", "bogus",
                "--reason", "x",
            ])
            self.assertEqual(r.returncode, 2)


# ---------------------------------------------------------------------------
# Phase 2 — coverage helpers (dp-coverage / rubric-coverage).
# ---------------------------------------------------------------------------


class TestDpAndRubricCoverage(unittest.TestCase):
    def _setup(self, td: Path) -> Path:
        dev = td / ".devforge"
        _run(["--devforge-dir", str(dev), "reset-state"])
        _run(["--devforge-dir", str(dev), "detect-mode"])
        return dev

    def test_dp_coverage_emits_dp_id_status_map(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            _run([
                "--devforge-dir", str(dev), "record-decision-point",
                "--category", "scope_boundaries",
                "--description", "x",
                "--valid-implementations", json.dumps(["a", "b"]),
            ])
            r = _run(["--devforge-dir", str(dev), "dp-coverage"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data["DP-scope_boundaries-1"], "pending")

    def test_rubric_missing_for_categories_with_no_dp(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            r = _run(["--devforge-dir", str(dev), "rubric-coverage"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            for cat in specify_helper.DP_CATEGORY_ENUM:
                self.assertEqual(data[cat], "Missing")

    def test_rubric_partial_then_clear(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            _run([
                "--devforge-dir", str(dev), "record-decision-point",
                "--category", "data_flow_state",
                "--description", "x",
                "--valid-implementations", json.dumps(["a", "b"]),
            ])
            r = _run(["--devforge-dir", str(dev), "rubric-coverage"])
            data = json.loads(r.stdout)
            self.assertEqual(data["data_flow_state"], "Partial")
            _run([
                "--devforge-dir", str(dev), "set-dp-answer",
                "--dp-id", "DP-data_flow_state-1",
                "--user-answer", "a",
            ])
            r = _run(["--devforge-dir", str(dev), "rubric-coverage"])
            data = json.loads(r.stdout)
            self.assertEqual(data["data_flow_state"], "Clear")

    def test_rubric_no_dp_in_category_state(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            _run([
                "--devforge-dir", str(dev), "record-decision-point",
                "--category", "ui_ux_details",
                "--description", "no UI surface",
                "--no-dp-in-category",
            ])
            r = _run(["--devforge-dir", str(dev), "rubric-coverage"])
            data = json.loads(r.stdout)
            self.assertEqual(data["ui_ux_details"], "NoDPInCategory")

    def test_rubric_no_dp_wins_over_pending_in_same_category(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            _run([
                "--devforge-dir", str(dev), "record-decision-point",
                "--category", "ui_ux_details",
                "--description", "no UI surface",
                "--no-dp-in-category",
            ])
            _run([
                "--devforge-dir", str(dev), "record-decision-point",
                "--category", "ui_ux_details",
                "--description", "stray DP",
                "--valid-implementations", json.dumps(["a", "b"]),
            ])
            r = _run(["--devforge-dir", str(dev), "rubric-coverage"])
            data = json.loads(r.stdout)
            self.assertEqual(data["ui_ux_details"], "NoDPInCategory")

    def test_clear_when_deferred_oos(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            _run([
                "--devforge-dir", str(dev), "record-decision-point",
                "--category", "breaking_changes",
                "--description", "x",
                "--valid-implementations", json.dumps(["a", "b"]),
            ])
            _run([
                "--devforge-dir", str(dev), "set-dp-deferral",
                "--dp-id", "DP-breaking_changes-1",
                "--deferral-kind", "OOS",
                "--reason", "v2",
            ])
            r = _run(["--devforge-dir", str(dev), "rubric-coverage"])
            data = json.loads(r.stdout)
            self.assertEqual(data["breaking_changes"], "Clear")


# ---------------------------------------------------------------------------
# Phase 2 — verify-decision-coverage / rubric-finalize / dp-finalize.
# ---------------------------------------------------------------------------


def _seed_all_categories_clear(dev: Path) -> None:
    _run(["--devforge-dir", str(dev), "reset-state"])
    _run(["--devforge-dir", str(dev), "detect-mode"])
    for cat in specify_helper.DP_CATEGORY_ENUM:
        _run([
            "--devforge-dir", str(dev), "record-decision-point",
            "--category", cat,
            "--description", "no surface for " + cat,
            "--no-dp-in-category",
        ])


class TestVerifyDecisionCoverage(unittest.TestCase):
    def test_all_no_dp_passes(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_all_categories_clear(dev)
            r = _run([
                "--devforge-dir", str(dev), "verify-decision-coverage",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_pending_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_all_categories_clear(dev)
            # Add a stray pending DP — replaces NoDPInCategory in
            # tooling_configuration with Partial coverage. Actually no —
            # NoDPInCategory wins. Easier: clear one cat, leave it Missing.
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run(["--devforge-dir", str(dev), "detect-mode"])
            cats = list(specify_helper.DP_CATEGORY_ENUM)
            for cat in cats[:-1]:
                _run([
                    "--devforge-dir", str(dev), "record-decision-point",
                    "--category", cat,
                    "--description", "no surface",
                    "--no-dp-in-category",
                ])
            # Last cat → Pending.
            _run([
                "--devforge-dir", str(dev), "record-decision-point",
                "--category", cats[-1],
                "--description", "x",
                "--valid-implementations", json.dumps(["a", "b"]),
            ])
            r = _run([
                "--devforge-dir", str(dev), "verify-decision-coverage",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn(cats[-1], r.stderr)
            self.assertIn("Partial", r.stderr)

    def test_missing_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run(["--devforge-dir", str(dev), "detect-mode"])
            r = _run([
                "--devforge-dir", str(dev), "verify-decision-coverage",
            ])
            self.assertEqual(r.returncode, 2)
            for cat in specify_helper.DP_CATEGORY_ENUM:
                self.assertIn(cat, r.stderr)


class TestRubricFinalize(unittest.TestCase):
    def test_passes_when_clear(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_all_categories_clear(dev)
            r = _run(["--devforge-dir", str(dev), "rubric-finalize"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_fails_when_missing(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run(["--devforge-dir", str(dev), "rubric-finalize"])
            self.assertEqual(r.returncode, 2)


class TestDpFinalize(unittest.TestCase):
    def test_passes_and_stamps(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _seed_all_categories_clear(dev)
            r = _run(["--devforge-dir", str(dev), "dp-finalize"])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertTrue(state["dp_finalized"])

    def test_does_not_stamp_when_failing(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run(["--devforge-dir", str(dev), "dp-finalize"])
            self.assertEqual(r.returncode, 2)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertFalse(state["dp_finalized"])


# ---------------------------------------------------------------------------
# Phase 3 — classify-spec-type.
# ---------------------------------------------------------------------------


class TestClassifySpecType(unittest.TestCase):
    def _setup(self, td: Path) -> Path:
        dev = td / ".devforge"
        _run(["--devforge-dir", str(dev), "reset-state"])
        return dev

    def test_basic_classification(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            r = _run([
                "--devforge-dir", str(dev), "classify-spec-type",
                "--spec-type", "feature_addition",
                "--rationale", "Net-new behavior in existing module.",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["spec_type"], "feature_addition")
            self.assertEqual(
                state["spec_type_rationale"],
                "Net-new behavior in existing module.",
            )
            self.assertFalse(state["spec_type_seeded_by_upstream"])

    def test_seeded_by_upstream_flag(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            r = _run([
                "--devforge-dir", str(dev), "classify-spec-type",
                "--spec-type", "greenfield_feature",
                "--rationale", "/discover seed",
                "--seeded-by-upstream",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertTrue(state["spec_type_seeded_by_upstream"])

    def test_rejects_unknown_type(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td))
            r = _run([
                "--devforge-dir", str(dev), "classify-spec-type",
                "--spec-type", "bogus",
                "--rationale", "x",
            ])
            self.assertEqual(r.returncode, 2)


# ---------------------------------------------------------------------------
# Phase 3 — record-mandatory-read + verify-mandatory-reads.
# ---------------------------------------------------------------------------


def _classify(dev: Path, spec_type: str) -> None:
    _run([
        "--devforge-dir", str(dev), "classify-spec-type",
        "--spec-type", spec_type,
        "--rationale", "test",
    ])


class TestRecordMandatoryRead(unittest.TestCase):
    def _setup(self, td: Path, spec_type: str) -> Path:
        dev = td / ".devforge"
        _run(["--devforge-dir", str(dev), "reset-state"])
        _classify(dev, spec_type)
        return dev

    def test_record_read_path(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td), "migration_tooling")
            r = _run([
                "--devforge-dir", str(dev), "record-mandatory-read",
                "--read-path", "package.json",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(len(state["mandatory_reads"]), 1)
            entry = state["mandatory_reads"][0]
            self.assertEqual(entry["read_path"], "package.json")
            self.assertEqual(entry["spec_type"], "migration_tooling")
            self.assertEqual(entry["n_a_reason"], "")

    def test_record_na_marker(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td), "migration_tooling")
            r = _run([
                "--devforge-dir", str(dev), "record-mandatory-read",
                "--slot-pattern", "rush.json",
                "--n-a-reason", "Repo uses pnpm, not rush.",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            entry = state["mandatory_reads"][0]
            self.assertEqual(entry["slot_pattern"], "rush.json")
            self.assertEqual(entry["n_a_reason"], "Repo uses pnpm, not rush.")

    def test_record_rejects_no_args(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td), "migration_tooling")
            r = _run([
                "--devforge-dir", str(dev), "record-mandatory-read",
            ])
            self.assertEqual(r.returncode, 2)

    def test_record_rejects_both_read_and_na(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td), "migration_tooling")
            r = _run([
                "--devforge-dir", str(dev), "record-mandatory-read",
                "--read-path", "package.json",
                "--n-a-reason", "x",
            ])
            self.assertEqual(r.returncode, 2)

    def test_record_rejects_na_without_slot(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td), "migration_tooling")
            r = _run([
                "--devforge-dir", str(dev), "record-mandatory-read",
                "--n-a-reason", "no slot named",
            ])
            self.assertEqual(r.returncode, 2)

    def test_record_rejects_when_spec_type_unset(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "record-mandatory-read",
                "--read-path", "package.json",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("spec_type", r.stderr)


class TestVerifyMandatoryReads(unittest.TestCase):
    def _setup(self, td: Path, spec_type: str) -> Path:
        dev = td / ".devforge"
        _run(["--devforge-dir", str(dev), "reset-state"])
        _classify(dev, spec_type)
        return dev

    def _cover_all(self, dev: Path, spec_type: str) -> None:
        for slot, _ in specify_helper.MANDATORY_READS_BY_TYPE[spec_type]:
            if slot.startswith("__") and slot.endswith("__"):
                _run([
                    "--devforge-dir", str(dev), "record-mandatory-read",
                    "--slot-pattern", slot,
                    "--n-a-reason", "stub coverage for " + slot,
                ])
            else:
                _run([
                    "--devforge-dir", str(dev), "record-mandatory-read",
                    "--slot-pattern", slot,
                    "--n-a-reason", "n/a in test fixture",
                ])

    def test_passes_when_all_slots_covered(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td), "bug_fix")
            self._cover_all(dev, "bug_fix")
            r = _run([
                "--devforge-dir", str(dev), "verify-mandatory-reads",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_fails_when_slot_missing(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td), "refactor")
            # Only one of the three slots covered.
            _run([
                "--devforge-dir", str(dev), "record-mandatory-read",
                "--slot-pattern", "__refactored_files__",
                "--n-a-reason", "x",
            ])
            r = _run([
                "--devforge-dir", str(dev), "verify-mandatory-reads",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("__all_callers__", r.stderr)
            self.assertIn("__all_tests__", r.stderr)

    def test_fails_when_spec_type_unset(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "verify-mandatory-reads",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("spec_type", r.stderr)

    def test_concrete_pattern_matches_via_fnmatch(self):
        # Migration tooling pkg slot matches root package.json.
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td), "migration_tooling")
            for slot, _ in (
                specify_helper.MANDATORY_READS_BY_TYPE["migration_tooling"]
            ):
                if slot == "package.json":
                    _run([
                        "--devforge-dir", str(dev), "record-mandatory-read",
                        "--read-path", "package.json",
                    ])
                else:
                    _run([
                        "--devforge-dir", str(dev), "record-mandatory-read",
                        "--slot-pattern", slot,
                        "--n-a-reason", "n/a",
                    ])
            r = _run([
                "--devforge-dir", str(dev), "verify-mandatory-reads",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_substring_pattern_matches_workflows(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td), "migration_tooling")
            # Cover the workflows slot via concrete file path.
            for slot, _ in (
                specify_helper.MANDATORY_READS_BY_TYPE["migration_tooling"]
            ):
                if slot == ".github/workflows/*":
                    _run([
                        "--devforge-dir", str(dev), "record-mandatory-read",
                        "--read-path", ".github/workflows/ci.yml",
                    ])
                else:
                    _run([
                        "--devforge-dir", str(dev), "record-mandatory-read",
                        "--slot-pattern", slot,
                        "--n-a-reason", "n/a",
                    ])
            r = _run([
                "--devforge-dir", str(dev), "verify-mandatory-reads",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_nested_package_json_matches_doublestar(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td), "migration_tooling")
            for slot, _ in (
                specify_helper.MANDATORY_READS_BY_TYPE["migration_tooling"]
            ):
                if slot == "**/package.json":
                    _run([
                        "--devforge-dir", str(dev), "record-mandatory-read",
                        "--read-path", "packages/api/package.json",
                    ])
                else:
                    _run([
                        "--devforge-dir", str(dev), "record-mandatory-read",
                        "--slot-pattern", slot,
                        "--n-a-reason", "n/a",
                    ])
            r = _run([
                "--devforge-dir", str(dev), "verify-mandatory-reads",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_greenfield_discovery_report_slot_matches_new_specs_layout(self):
        """68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 4: the greenfield slot
        moved from "discover/*.md" to "specs/*/discovery-report.md"
        (_schema.py) — a real intake-layout read-path must satisfy it via
        Path.match, not just via an --n-a-reason bypass."""
        with tempfile.TemporaryDirectory() as td:
            dev = self._setup(Path(td), "greenfield_feature")
            for slot, _ in (
                specify_helper.MANDATORY_READS_BY_TYPE["greenfield_feature"]
            ):
                if slot == "specs/*/discovery-report.md":
                    _run([
                        "--devforge-dir", str(dev), "record-mandatory-read",
                        "--read-path",
                        "specs/001-scheduled-export-jobs/discovery-report.md",
                    ])
                else:
                    _run([
                        "--devforge-dir", str(dev), "record-mandatory-read",
                        "--slot-pattern", slot,
                        "--n-a-reason", "n/a",
                    ])
            r = _run([
                "--devforge-dir", str(dev), "verify-mandatory-reads",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)


class TestPhase3Finalize(unittest.TestCase):
    def test_passes_and_stamps(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _classify(dev, "bug_fix")
            for slot, _ in (
                specify_helper.MANDATORY_READS_BY_TYPE["bug_fix"]
            ):
                _run([
                    "--devforge-dir", str(dev), "record-mandatory-read",
                    "--slot-pattern", slot,
                    "--n-a-reason", "n/a",
                ])
            r = _run(["--devforge-dir", str(dev), "phase3-finalize"])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertTrue(state["phase3_finalized"])

    def test_does_not_stamp_when_failing(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _classify(dev, "bug_fix")
            r = _run(["--devforge-dir", str(dev), "phase3-finalize"])
            self.assertEqual(r.returncode, 2)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertFalse(state["phase3_finalized"])


# ---------------------------------------------------------------------------
# Phase 3 — MANDATORY_READS_BY_TYPE schema sanity.
# ---------------------------------------------------------------------------


class TestMandatoryReadsTable(unittest.TestCase):
    def test_every_spec_type_has_table(self):
        for st in specify_helper.SPEC_TYPE_ENUM:
            self.assertIn(
                st, specify_helper.MANDATORY_READS_BY_TYPE,
                "missing slot table for spec_type " + st,
            )

    def test_every_slot_has_pattern_and_description(self):
        for st, slots in (
            specify_helper.MANDATORY_READS_BY_TYPE.items()
        ):
            for entry in slots:
                self.assertEqual(
                    len(entry), 2,
                    "{0} slot wrong shape: {1!r}".format(st, entry),
                )
                pattern, desc = entry
                self.assertTrue(pattern.strip(), "empty pattern in " + st)
                self.assertTrue(desc.strip(), "empty description in " + st)

    def test_greenfield_includes_constitution_and_memory(self):
        slots = dict(
            specify_helper.MANDATORY_READS_BY_TYPE["greenfield_feature"]
        )
        self.assertIn("constitution.md#scaffolding-guide", slots)
        self.assertIn(".claude/memory/MEMORY.md", slots)

    def test_greenfield_discover_slot_moved_under_specs(self):
        """68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 4: the discover-
        reference-md slot's pattern literal moved from "discover/*.md" to
        "specs/*/discovery-report.md"; the old top-level literal must not
        survive as a slot key."""
        slots = dict(
            specify_helper.MANDATORY_READS_BY_TYPE["greenfield_feature"]
        )
        self.assertIn("specs/*/discovery-report.md", slots)
        self.assertNotIn("discover/*.md", slots)


# ---------------------------------------------------------------------------
# Cross-phase — summary subcommand.
# ---------------------------------------------------------------------------


class TestSummarySubcommand(unittest.TestCase):
    def test_empty_state_dashboard(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run(["--devforge-dir", str(dev), "summary"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertIsNone(data["spec_type"])
            self.assertEqual(data["status"], "Draft")
            self.assertFalse(data["phase_finalized"]["phase1"])
            self.assertEqual(data["counts"]["input_reads"], 0)
            for cat in specify_helper.DP_CATEGORY_ENUM:
                self.assertEqual(data["rubric_coverage"][cat], "Missing")

    def test_counts_reflect_state(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run(["--devforge-dir", str(dev), "detect-mode"])
            _run([
                "--devforge-dir", str(dev), "record-input-read",
                "--path", "constitution.md",
            ])
            for i in range(3):
                _run([
                    "--devforge-dir", str(dev), "record-finding",
                    "--source-path", "constitution.md",
                    "--content", "x{0}".format(i),
                ])
            _run([
                "--devforge-dir", str(dev), "record-decision-point",
                "--category", "scope_boundaries",
                "--description", "x",
                "--valid-implementations", json.dumps(["a", "b"]),
            ])
            _run([
                "--devforge-dir", str(dev), "set-dp-answer",
                "--dp-id", "DP-scope_boundaries-1",
                "--user-answer", "a",
            ])
            r = _run(["--devforge-dir", str(dev), "summary"])
            data = json.loads(r.stdout)
            self.assertEqual(data["counts"]["input_reads"], 1)
            self.assertEqual(data["counts"]["findings"], 3)
            self.assertEqual(data["counts"]["decision_points"], 1)
            self.assertEqual(
                data["counts"]["decision_points_by_status"]["answered"], 1,
            )
            self.assertEqual(data["mode"], "interactive")


# ---------------------------------------------------------------------------
# Phase 4 — header / branch setters.
# ---------------------------------------------------------------------------


def _phase4_seed(dev: Path) -> None:
    """Common seed for Phase 4 tests: state, date, feature_name."""
    _run(["--devforge-dir", str(dev), "reset-state"])


class TestPhase4AssignSpecNumber(unittest.TestCase):
    def test_emits_001_when_specs_dir_missing(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "assign-spec-number",
                "--specs-root", str(Path(td) / "specs"),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "001")
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["spec_number"], "001")

    def test_emits_next_after_existing_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            specs = Path(td) / "specs"
            specs.mkdir()
            (specs / "001-old-spec").mkdir()
            (specs / "003-jumpy").mkdir()
            (specs / "not-a-spec-dir").mkdir()
            (specs / "010-bigger").mkdir()
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "assign-spec-number",
                "--specs-root", str(specs),
            ])
            self.assertEqual(r.stdout.strip(), "011")


class TestSetSpecNumber(unittest.TestCase):
    """python-reviewer finding 1(b): the explicit-value spec_number setter
    (D5 cold-path seeding; mirrors assign-feature-name's contract)."""

    def test_happy_path_persists_value_verbatim(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "set-spec-number",
                "--value", "007",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["spec_number"], "007")

    def test_accepts_wider_than_3_digits(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "set-spec-number",
                "--value", "1042",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["spec_number"], "1042")

    def test_rejects_non_digit_value(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "set-spec-number",
                "--value", "abc",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("set-spec-number", r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertIsNone(state["spec_number"])

    def test_rejects_fewer_than_3_digits(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "set-spec-number",
                "--value", "7",
            ])
            self.assertEqual(r.returncode, 2)

    def test_rejects_empty_value(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "set-spec-number",
                "--value", "",
            ])
            self.assertEqual(r.returncode, 2)

    def test_no_scan_ignores_existing_specs_dirs(self):
        """Unlike assign-spec-number, set-spec-number performs NO scan --
        pre-existing specs/ dirs must not influence the persisted value."""
        with tempfile.TemporaryDirectory() as td:
            specs = Path(td) / "specs"
            (specs / "001-old-spec").mkdir(parents=True)
            (specs / "010-bigger").mkdir()
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "set-spec-number",
                "--value", "003",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["spec_number"], "003")


class TestPhase4AssignFeatureName(unittest.TestCase):
    def test_accepts_2_word_kebab(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "assign-feature-name",
                "--feature-name", "add-feature",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["feature_name"], "add-feature")
            self.assertEqual(state["feature_slug"], "add-feature")

    def test_accepts_4_word_kebab(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "assign-feature-name",
                "--feature-name", "migrate-monorepo-to-pnpm",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_rejects_single_word(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "assign-feature-name",
                "--feature-name", "feature",
            ])
            self.assertEqual(r.returncode, 2)

    def test_rejects_5_word_kebab(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "assign-feature-name",
                "--feature-name", "a-b-c-d-e",
            ])
            self.assertEqual(r.returncode, 2)

    def test_rejects_uppercase(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "assign-feature-name",
                "--feature-name", "Add-Feature",
            ])
            self.assertEqual(r.returncode, 2)

    def test_rejects_snake_case(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "assign-feature-name",
                "--feature-name", "add_feature",
            ])
            self.assertEqual(r.returncode, 2)


class TestPhase4SetDate(unittest.TestCase):
    def test_accepts_iso_date(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "set-date",
                "--date", "2026-05-15",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["date"], "2026-05-15")

    def test_rejects_garbled_date(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "set-date",
                "--date", "May 15",
            ])
            self.assertEqual(r.returncode, 2)


class TestPhase4CreateBranch(unittest.TestCase):
    def test_emits_checkout_on_default_branch(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev), "assign-spec-number",
                "--specs-root", str(Path(td) / "specs"),
            ])
            _run([
                "--devforge-dir", str(dev), "assign-feature-name",
                "--feature-name", "add-darkmode",
            ])
            r = _run([
                "--devforge-dir", str(dev), "create-branch",
                "--current-branch", "main", "--default-branch", "main",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn(
                "git checkout -b spec/001-add-darkmode", r.stdout,
            )
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["branch_decision"], "create")
            self.assertTrue(state["branch_created"])

    def test_keep_on_non_default_branch(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "create-branch",
                "--current-branch", "spec/000-other",
                "--default-branch", "main",
            ])
            self.assertEqual(r.returncode, 0)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["branch_decision"], "keep")
            self.assertFalse(state["branch_created"])

    def test_rejects_missing_spec_number_when_default(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "create-branch",
                "--current-branch", "main", "--default-branch", "main",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("spec_number", r.stderr)


# ---------------------------------------------------------------------------
# Phase 4 — section setters.
# ---------------------------------------------------------------------------


class TestPhase4SectionSetters(unittest.TestCase):
    def _dev(self, td: str) -> Path:
        dev = Path(td) / ".devforge"
        _run(["--devforge-dir", str(dev), "reset-state"])
        return dev

    def test_set_overview_persists(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "set-overview",
                "--content", "Migrate to pnpm.",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["overview"], "Migrate to pnpm.")

    def test_set_overview_rejects_empty(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "set-overview",
                "--content", "  ",
            ])
            self.assertEqual(r.returncode, 2)

    def test_set_current_state_persists(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            _run([
                "--devforge-dir", str(dev), "set-current-state",
                "--content", "Yarn workspaces today.",
            ])
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["current_state"], "Yarn workspaces today.")

    def test_set_desired_behavior_persists(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            _run([
                "--devforge-dir", str(dev), "set-desired-behavior",
                "--content", "Pnpm workspaces.",
            ])
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["desired_behavior"], "Pnpm workspaces.")

    def test_record_affected_area_appends(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            _run([
                "--devforge-dir", str(dev), "record-affected-area",
                "--area", "Tooling",
                "--files", json.dumps(["pkg.json", "tsconfig.json"]),
                "--impact", "rewrite",
            ])
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(len(state["affected_areas"]), 1)
            self.assertEqual(state["affected_areas"][0]["area"], "Tooling")
            self.assertEqual(
                state["affected_areas"][0]["files"],
                ["pkg.json", "tsconfig.json"],
            )

    def test_record_affected_area_rejects_non_array(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "record-affected-area",
                "--area", "X",
                "--files", json.dumps({"oops": "bad"}),
                "--impact", "Y",
            ])
            self.assertEqual(r.returncode, 2)

    def test_record_out_of_scope_with_finding_ref(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            # Record the finding first so the ref is valid.
            r = _run([
                "--devforge-dir", str(dev), "record-finding",
                "--source-path", "constitution.md",
                "--content", "CI runner migration finding",
            ])
            fid = r.stdout.strip()
            _run([
                "--devforge-dir", str(dev), "record-out-of-scope",
                "--content", "Migrate CI runner",
                "--finding-ref", fid,
            ])
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["out_of_scope"][0]["content"], "Migrate CI runner")
            self.assertEqual(state["out_of_scope"][0]["finding_ref"], fid)

    def test_record_constraint_enforces_kind_enum(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "bogus", "--content", "x",
            ])
            self.assertEqual(r.returncode, 2)

    def test_record_constraint_accepts_each_kind(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            # constitution.md required for constitution_anchor kind.
            (Path(td) / "constitution.md").write_text(
                "# Constitution\n\n### §3.6 Open/Closed pattern\n\nRules.\n",
                encoding="utf-8",
            )
            # Per-kind required extra flags.
            extra: Dict[str, List[str]] = {
                "follow": [],
                "not_break": [],
                "nfr": ["--quantifier", "p95 < 200ms"],
                "constitution_anchor": ["--constitution-ref", "§3.6"],
                "external_system": ["--protocol", "REST"],
            }
            for kind in specify_helper.CONSTRAINT_KIND_ENUM:
                r = _run(
                    ["--devforge-dir", str(dev), "record-constraint",
                     "--kind", kind, "--content", "c-{0}".format(kind)]
                    + extra[kind]
                )
                self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(
                [c["kind"] for c in state["constraints"]],
                list(specify_helper.CONSTRAINT_KIND_ENUM),
            )

    def test_record_open_question_with_no_dp_reason(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            _run([
                "--devforge-dir", str(dev), "record-open-question",
                "--question-id", "Q1",
                "--content", "Pin runtime version?",
                "--category-no-dp-reason", "no UI surfaces touched",
            ])
            state = json.loads((dev / "specify-state.json").read_text())
            entry = state["open_questions"][0]
            self.assertEqual(entry["question_id"], "Q1")
            self.assertEqual(
                entry["category_no_dp_reason"], "no UI surfaces touched",
            )

    def test_record_risk_enforces_likelihood_impact_enums(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "record-risk",
                "--risk", "x", "--likelihood", "Yuge",
                "--impact", "Med", "--mitigation", "y",
            ])
            self.assertEqual(r.returncode, 2)
            r2 = _run([
                "--devforge-dir", str(dev), "record-risk",
                "--risk", "x", "--likelihood", "Med",
                "--impact", "Med", "--mitigation", "y",
            ])
            self.assertEqual(r2.returncode, 0, r2.stderr)


# ---------------------------------------------------------------------------
# Phase 4 — record-constraint kind-split tests (nfr / constitution_anchor /
# external_system / legacy-use rejection / follow / not_break regression).
# ---------------------------------------------------------------------------


class RecordConstraintKindSplitTests(unittest.TestCase):
    """Round-trip tests for the expanded constraint kind taxonomy.

    All happy-path cases invoke the real subprocess and read state JSON.
    Fixture constitution.md is placed at install_root (parent of .devforge/).
    """

    def _dev(self, td: str) -> Path:
        dev = Path(td) / ".devforge"
        _run(["--devforge-dir", str(dev), "reset-state"])
        return dev

    def _dev_with_constitution(self, td: str, extra_content: str = "") -> Path:
        """Create .devforge/ and write a constitution.md with §3.6 heading."""
        root = Path(td)
        (root / "constitution.md").write_text(
            "# Constitution\n\n### §3.6 Open/Closed pattern\n\nFollow it.\n"
            + extra_content,
            encoding="utf-8",
        )
        return self._dev(td)

    # --- nfr ---

    def test_nfr_valid_numeric_threshold(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "nfr",
                "--quantifier", "10K users @ p95 < 200ms",
                "--content", "System must handle load",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            c = state["constraints"][0]
            self.assertEqual(c["kind"], "nfr")
            self.assertEqual(c["quantifier"], "10K users @ p95 < 200ms")
            self.assertEqual(c["content"], "System must handle load")

    def test_nfr_valid_named_class(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "nfr",
                "--quantifier", "PCI-DSS Level 1",
                "--content", "Payment data handling",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            c = state["constraints"][0]
            self.assertEqual(c["kind"], "nfr")
            self.assertEqual(c["quantifier"], "PCI-DSS Level 1")

    def test_nfr_rejects_empty_quantifier(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "nfr",
                "--content", "System must handle load",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("required and non-empty", r.stderr)

    def test_nfr_rejects_vague_high(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "nfr",
                "--quantifier", "high",
                "--content", "System must perform well",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("vague quantifier", r.stderr)

    def test_nfr_rejects_bare_adjective(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "nfr",
                "--quantifier", "fast and scalable",
                "--content", "System must perform well",
            ])
            self.assertEqual(r.returncode, 2)
            # Error must mention numeric threshold or named-class
            self.assertTrue(
                "numeric threshold" in r.stderr or "named-class" in r.stderr,
                "expected numeric threshold or named-class in stderr: {0!r}".format(r.stderr),
            )

    # --- constitution_anchor ---

    def test_constitution_anchor_valid_existing_section(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev_with_constitution(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "constitution_anchor",
                "--constitution-ref", "§3.6",
                "--content", "Must follow Open/Closed pattern",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            c = state["constraints"][0]
            self.assertEqual(c["kind"], "constitution_anchor")
            self.assertEqual(c["constitution_ref"], "§3.6")
            self.assertEqual(c["content"], "Must follow Open/Closed pattern")

    def test_constitution_anchor_valid_bare_ref(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev_with_constitution(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "constitution_anchor",
                "--constitution-ref", "3.6",
                "--content", "Must follow Open/Closed pattern",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            c = state["constraints"][0]
            self.assertEqual(c["constitution_ref"], "3.6")

    def test_constitution_anchor_rejects_missing_ref(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev_with_constitution(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "constitution_anchor",
                "--content", "Must follow something",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("constitution_anchor", r.stderr)

    def test_constitution_anchor_rejects_nonexistent_section(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev_with_constitution(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "constitution_anchor",
                "--constitution-ref", "§99.99",
                "--content", "Must follow nonexistent rule",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("99.99", r.stderr)

    def test_constitution_anchor_rejects_no_constitution_file(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            # No constitution.md at install_root (td).
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "constitution_anchor",
                "--constitution-ref", "§3.6",
                "--content", "Must follow something",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("constitution.md", r.stderr)

    # --- external_system ---

    def test_external_system_with_protocol(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "external_system",
                "--protocol", "REST",
                "--content", "Payment gateway integration",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            c = state["constraints"][0]
            self.assertEqual(c["kind"], "external_system")
            self.assertEqual(c["protocol"], "REST")
            self.assertEqual(c["content"], "Payment gateway integration")

    def test_external_system_with_contract_doc_ref(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "external_system",
                "--contract-doc-ref", "api/openapi.yaml",
                "--content", "Auth provider integration",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            c = state["constraints"][0]
            self.assertEqual(c["kind"], "external_system")
            self.assertEqual(c["contract_doc_ref"], "api/openapi.yaml")

    def test_external_system_rejects_neither_protocol_nor_contract(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "external_system",
                "--content", "Some external thing",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("--protocol", r.stderr)
            self.assertIn("--contract-doc-ref", r.stderr)

    # --- legacy use rejection ---

    def test_legacy_use_kind_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "use",
                "--content", "foo",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("nfr", r.stderr)
            self.assertIn("constitution_anchor", r.stderr)
            self.assertIn("external_system", r.stderr)

    # --- regression: follow + not_break still work ---

    def test_follow_still_works(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "follow",
                "--content", "Wrapper pattern per §3.6",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["constraints"][0]["kind"], "follow")

    def test_not_break_still_works(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "not_break",
                "--content", "Existing API contract",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["constraints"][0]["kind"], "not_break")


# ---------------------------------------------------------------------------
# Phase 4 — add-ac (EARS + subsection constraints).
# ---------------------------------------------------------------------------


class TestPhase4AddAc(unittest.TestCase):
    def _dev(self, td: str) -> Path:
        dev = Path(td) / ".devforge"
        _run(["--devforge-dir", str(dev), "reset-state"])
        return dev

    def test_happy_path_each_ears_variant(self):
        canon = {
            "ubiquitous":
                "The system shall log every request.",
            "event_driven":
                "WHEN the build finishes, the CI shall publish artifacts.",
            "state_driven":
                "WHILE the user is admin, the dashboard shall show debug info.",
            "optional":
                "WHERE the dark-mode flag is enabled, the UI shall use a dark palette.",
            "unwanted":
                "IF the token is expired, THEN the system shall reject the request.",
        }
        # Use a subsection that allows any variant — behavior_change accepts all.
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            for variant, stmt in canon.items():
                r = _run([
                    "--devforge-dir", str(dev), "add-ac",
                    "--subsection", "behavior_change",
                    "--ears-variant", variant,
                    "--statement", stmt,
                ])
                self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(len(state["acceptance_criteria"]), 5)
            self.assertEqual(
                {a["ears_variant"] for a in state["acceptance_criteria"]},
                set(canon.keys()),
            )

    def test_auto_assigns_ac_ids(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            for i in range(3):
                r = _run([
                    "--devforge-dir", str(dev), "add-ac",
                    "--subsection", "behavior_change",
                    "--ears-variant", "ubiquitous",
                    "--statement",
                    "The system shall do thing {0}.".format(i),
                ])
                self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(
                [a["ac_id"] for a in state["acceptance_criteria"]],
                ["AC-1", "AC-2", "AC-3"],
            )

    def test_accepts_explicit_ac_id(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "add-ac",
                "--ac-id", "AC-X",
                "--subsection", "behavior_change",
                "--ears-variant", "ubiquitous",
                "--statement", "The system shall do thing X.",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "AC-X")

    def test_rejects_freeform_statement(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "behavior_change",
                "--ears-variant", "ubiquitous",
                "--statement", "System should sometimes do stuff",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("EARS", r.stderr)

    def test_511_requires_ubiquitous(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "tooling_artifact_presence",
                "--ears-variant", "event_driven",
                "--statement",
                "WHEN x, the system shall y.",
                "--verification-command", "grep x",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("ubiquitous", r.stderr)

    def test_511_requires_verification_command(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "tooling_artifact_presence",
                "--ears-variant", "ubiquitous",
                "--statement", "The repo shall contain no `lerna`.",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("verification-command", r.stderr)

    def test_511_happy(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "tooling_artifact_presence",
                "--ears-variant", "ubiquitous",
                "--statement",
                "The repository shall contain no occurrences of `lerna`.",
                "--verification-command", "grep -r lerna . returns 0 matches",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_57_hygiene_requires_ubiquitous_and_verification(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "hygiene",
                "--ears-variant", "event_driven",
                "--statement",
                "WHEN x, the repo shall be clean.",
                "--verification-command", "grep nothing",
            ])
            self.assertEqual(r.returncode, 2)

    def test_mark_subsection_na(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "ci_pipeline",
                "--mark-na",
                "--n-a-reason", "no CI in scope",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(
                state["ac_subsection_na"]["ci_pipeline"], "no CI in scope",
            )
            self.assertEqual(state["acceptance_criteria"], [])

    def test_mark_na_rejects_empty_reason(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._dev(td)
            r = _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "ci_pipeline",
                "--mark-na", "--n-a-reason", "  ",
            ])
            self.assertEqual(r.returncode, 2)


# ---------------------------------------------------------------------------
# Phase 4 — verify subcommands.
# ---------------------------------------------------------------------------


class TestPhase4VerifyCoverage(unittest.TestCase):
    def test_passes_when_all_findings_landed(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev), "record-input-read",
                "--path", "constitution.md",
            ])
            for i in range(2):
                _run([
                    "--devforge-dir", str(dev), "record-finding",
                    "--source-path", "constitution.md",
                    "--content", "x{0}".format(i),
                    "--landed-in", "AC",
                ])
            r = _run(["--devforge-dir", str(dev), "verify-coverage"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_fails_on_any_unlanded(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev), "record-input-read",
                "--path", "constitution.md",
            ])
            _run([
                "--devforge-dir", str(dev), "record-finding",
                "--source-path", "constitution.md", "--content", "x",
            ])  # default landed_in="unlanded"
            r = _run(["--devforge-dir", str(dev), "verify-coverage"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("Variance rule #5", r.stderr)


class TestPhase4VerifyAcSubsectionCoverage(unittest.TestCase):
    def test_fails_on_empty(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev),
                "verify-ac-subsection-coverage",
            ])
            self.assertEqual(r.returncode, 2)
            for sub in specify_helper.AC_SUBSECTION_ENUM:
                self.assertIn(sub, r.stderr)

    def test_passes_when_all_marked_na(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            for sub in specify_helper.AC_SUBSECTION_ENUM:
                _run([
                    "--devforge-dir", str(dev), "add-ac",
                    "--subsection", sub,
                    "--mark-na", "--n-a-reason", "n/a",
                ])
            r = _run([
                "--devforge-dir", str(dev),
                "verify-ac-subsection-coverage",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_passes_with_mix_of_ac_and_na(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "tooling_artifact_presence",
                "--ears-variant", "ubiquitous",
                "--statement",
                "The repo shall contain no `lerna`.",
                "--verification-command", "grep -r lerna",
            ])
            _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "hygiene",
                "--ears-variant", "ubiquitous",
                "--statement",
                "The repo shall contain no stray lockfiles.",
                "--verification-command", "find lockfiles",
            ])
            for sub in (
                "behavior_preservation", "behavior_change",
                "ci_pipeline", "hooks_gates", "documentation",
            ):
                _run([
                    "--devforge-dir", str(dev), "add-ac",
                    "--subsection", sub,
                    "--mark-na", "--n-a-reason", "out of scope",
                ])
            r = _run([
                "--devforge-dir", str(dev),
                "verify-ac-subsection-coverage",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)


class TestPhase4VerifyAcShape(unittest.TestCase):
    def test_fails_when_state_corrupted(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            sp = dev / "specify-state.json"
            state = json.loads(sp.read_text())
            state["acceptance_criteria"].append({
                "ac_id": "AC-bad",
                "subsection": "behavior_change",
                "ears_variant": "ubiquitous",
                "statement": "Bad statement no shall here.",
                "verification_command": "",
                "test_anchor": "",
                "n_a_reason": "",
            })
            sp.write_text(json.dumps(state))
            r = _run(["--devforge-dir", str(dev), "verify-ac-shape"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("AC-bad", r.stderr)

    def test_passes_on_clean_state(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "behavior_change",
                "--ears-variant", "event_driven",
                "--statement",
                "WHEN the build finishes, the CI shall publish artifacts.",
            ])
            r = _run(["--devforge-dir", str(dev), "verify-ac-shape"])
            self.assertEqual(r.returncode, 0, r.stderr)


class TestPhase4VerifyNumericalConsistency(unittest.TestCase):
    def test_passes_on_consistent_render(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev), "set-overview",
                "--content", "Migrate across 3 packages of the workspace.",
            ])
            _run([
                "--devforge-dir", str(dev), "set-current-state",
                "--content", "All 3 packages share the same lockfile.",
            ])
            r = _run([
                "--devforge-dir", str(dev), "verify-numerical-consistency",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_fails_on_inconsistent_render(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run([
                "--devforge-dir", str(dev), "set-overview",
                "--content", "Migrate 3 packages of the monorepo.",
            ])
            _run([
                "--devforge-dir", str(dev), "set-current-state",
                "--content", "Today 5 packages live in the monorepo.",
            ])
            r = _run([
                "--devforge-dir", str(dev), "verify-numerical-consistency",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("packages", r.stderr)

    def test_ignores_section_heading_numbers(self):
        """5.1 / 5.2 in headings must not flag false inconsistency."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            # No body numbers; heading text "1 Tooling" etc would be a
            # false positive without skip-heading logic.
            r = _run([
                "--devforge-dir", str(dev), "verify-numerical-consistency",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)


class TestPhase4CheckConstitutionCompliance(unittest.TestCase):
    def test_skips_silently_when_constitution_missing(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev),
                "check-constitution-compliance",
                "--constitution-path", str(Path(td) / "nope.md"),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("not found", r.stderr)

    def test_emits_warnings_on_overlap(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            cpath = Path(td) / "constitution.md"
            cpath.write_text(
                "# Constitution\n\n"
                "Rule 1: The pipeline MUST NOT publish broken artifacts.\n",
                encoding="utf-8",
            )
            _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "behavior_change",
                "--ears-variant", "ubiquitous",
                "--statement",
                "The pipeline shall publish artifacts after every build.",
            ])
            r = _run([
                "--devforge-dir", str(dev),
                "check-constitution-compliance",
                "--constitution-path", str(cpath),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("overlap", r.stderr.lower())
            self.assertIn("publish", r.stderr)

    def test_clean_state_emits_no_warnings(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            cpath = Path(td) / "constitution.md"
            cpath.write_text(
                "# Constitution\n\nRule 1: The pipeline MUST NOT publish "
                "broken artifacts.\n",
                encoding="utf-8",
            )
            # No AC / Constraint / OOS to overlap with.
            r = _run([
                "--devforge-dir", str(dev),
                "check-constitution-compliance",
                "--constitution-path", str(cpath),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("review", r.stderr.lower())


# ---------------------------------------------------------------------------
# Phase 4 — verify-scope-coherence (non-blocking §5↔§6 token-overlap check).
# ---------------------------------------------------------------------------


class TestPhase4VerifyScopeCoherence(unittest.TestCase):
    """Tests for verify-scope-coherence.

    All tests use the real producer (record-out-of-scope / add-ac /
    record-affected-area subcommands) to populate state — no hand-authored
    JSON fixtures.

    The check is intentionally NON-BLOCKING: it always exits 0 even when it
    surfaces warnings.  A hard exit-2 would block on heuristic false positives,
    which is explicitly rejected by OQ-3 (RESOLVED: non-blocking warning).
    """

    # ------------------------------------------------------------------
    # Trip-wire test: the canonical §5↔§6 contradiction from the plan.
    # §6 marks "overlapping-load race hardening" OOS; §5 mandates
    # "branch on the load outcome [to avoid the shared slot]".
    # Both share salient tokens (load, branch, slot, etc.) — the check
    # must surface a WARNING naming both entries, then exit 0.
    # ------------------------------------------------------------------

    def test_tripwire_oos_vs_ac_flags_warning_and_exits_zero(self):
        """§6 OOS + §5 AC sharing salient tokens → WARNING to stderr, exit 0."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])

            # Producer: record the §6 OOS entry (overlapping-load race hardening).
            r_oos = _run([
                "--devforge-dir", str(dev), "record-out-of-scope",
                "--content",
                "overlapping-load race hardening — out of scope",
            ])
            self.assertEqual(r_oos.returncode, 0, r_oos.stderr)

            # Producer: record a §5 AC that mandates branching on load outcome.
            r_ac = _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "behavior_change",
                "--ears-variant", "event_driven",
                "--statement",
                "WHEN a section's load fails, the system shall branch on"
                " the load outcome to avoid the shared slot.",
            ])
            self.assertEqual(r_ac.returncode, 0, r_ac.stderr)

            r = _run([
                "--devforge-dir", str(dev), "verify-scope-coherence",
            ])
            self.assertEqual(r.returncode, 0,
                             "verify-scope-coherence must exit 0 (non-blocking); "
                             "stderr: " + r.stderr)
            # A warning must appear naming the OOS entry.
            self.assertIn("overlapping-load race hardening", r.stderr,
                          "Expected OOS entry text in warning")
            # The warning must name the AC (either its id or statement fragment).
            self.assertTrue(
                "load" in r.stderr or "branch" in r.stderr or "slot" in r.stderr,
                "Expected overlap token reference in warning; stderr: " + r.stderr,
            )
            # The warning must tag the conflicting entry as an AC.
            self.assertIn("AC", r.stderr,
                          "Expected 'AC' tag in warning; stderr: " + r.stderr)
            # The reconcile advisory must be present.
            self.assertIn("reconcile", r.stderr,
                          "Expected reconciliation advisory in warning")

    # ------------------------------------------------------------------
    # Clean spec: no §5/§4 mandate overlapping §6 → no warning, exit 0.
    # ------------------------------------------------------------------

    def test_clean_spec_no_warning_exit_zero(self):
        """A spec where §5 and §6 don't overlap → no warning, exit 0."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])

            # §6: authentication is out of scope.
            _run([
                "--devforge-dir", str(dev), "record-out-of-scope",
                "--content", "authentication and authorisation — out of scope",
            ])
            # §5: an AC about rendering — no overlap with auth.
            _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "behavior_change",
                "--ears-variant", "ubiquitous",
                "--statement",
                "The renderer shall produce deterministic markdown output.",
            ])

            r = _run([
                "--devforge-dir", str(dev), "verify-scope-coherence",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            # No warning should be surfaced.
            self.assertNotIn(
                "verify-scope-coherence:", r.stderr,
                "Expected no warning for a clean spec; stderr: " + r.stderr,
            )

    # ------------------------------------------------------------------
    # False-positive tolerance: §6 and §5 share an incidental noun
    # (e.g. "system") — acceptable false-positive, must not block (exit 0).
    # The test documents the known false-positive posture explicitly.
    # ------------------------------------------------------------------

    def test_false_positive_incidental_noun_is_warned_but_non_blocking(self):
        """Incidental shared noun causes a false-positive warning — exit 0."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])

            # §6 entry mentions "distributed caching" (with generic noun "cache").
            _run([
                "--devforge-dir", str(dev), "record-out-of-scope",
                "--content", "distributed caching layer — out of scope",
            ])
            # §5 AC about invalidating cache entries — shares token "cache".
            # This is a false positive: the AC refers to a local cache, not the
            # distributed layer, but the token overlap fires anyway.
            _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "behavior_change",
                "--ears-variant", "event_driven",
                "--statement",
                "WHEN a configuration changes, the system shall"
                " invalidate local cache entries.",
            ])

            r = _run([
                "--devforge-dir", str(dev), "verify-scope-coherence",
            ])
            # Non-blocking: must exit 0 even on a false-positive warning.
            self.assertEqual(
                r.returncode, 0,
                "verify-scope-coherence must exit 0 on false-positive; "
                "stderr: " + r.stderr,
            )
            # The check will have flagged "cache" as the overlap token.
            # That is acceptable — the advisory prompts author review, not auto-block.
            # (We don't assert *no* warning here: the false-positive is expected.)

    # ------------------------------------------------------------------
    # §4 affected-area check: OOS entry overlaps §4 area impact.
    # ------------------------------------------------------------------

    def test_oos_vs_affected_area_impact_flags_warning_exit_zero(self):
        """§6 OOS tokens overlap a §4 affected-area impact → WARNING, exit 0."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])

            # §6: retry logic is out of scope.
            _run([
                "--devforge-dir", str(dev), "record-out-of-scope",
                "--content", "retry logic for transient network failures — out of scope",
            ])
            # §4 affected area whose impact description mentions retry behaviour.
            _run([
                "--devforge-dir", str(dev), "record-affected-area",
                "--area", "API client",
                "--files", '["src/api/client.py"]',
                "--impact",
                "Must implement retry with exponential backoff on network failures.",
            ])

            r = _run([
                "--devforge-dir", str(dev), "verify-scope-coherence",
            ])
            self.assertEqual(r.returncode, 0,
                             "Non-blocking: must exit 0; stderr: " + r.stderr)
            # Warning must name the OOS entry and the affected area.
            self.assertIn("retry", r.stderr,
                          "Expected 'retry' token in warning; stderr: " + r.stderr)
            self.assertIn("Affected area", r.stderr,
                          "Expected affected-area tag in warning; stderr: " + r.stderr)

    # ------------------------------------------------------------------
    # Empty §6 (no OOS entries): no warning, exit 0.
    # ------------------------------------------------------------------

    def test_empty_oos_no_warning_exit_zero(self):
        """No §6 entries → no-op, exit 0, no stderr output."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])

            # Add a §5 AC but no §6 OOS entry.
            _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "behavior_preservation",
                "--ears-variant", "ubiquitous",
                "--statement",
                "The system shall preserve existing API contracts.",
            ])

            r = _run([
                "--devforge-dir", str(dev), "verify-scope-coherence",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stderr.strip(), "",
                             "Expected no stderr for empty OOS; got: " + r.stderr)

    # ------------------------------------------------------------------
    # §6 OOS present but no §5 ACs or §4 affected areas: no targets,
    # must exit 0 and emit no warnings (exercises the `if not targets`
    # early-return path in cmd_verify_scope_coherence).
    # ------------------------------------------------------------------

    def test_oos_present_no_targets_exit_zero(self):
        """§6 OOS entry recorded, no §5 AC or §4 affected-area → exit 0, no stderr."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])

            # Record an OOS entry but deliberately add no AC and no affected area.
            _run([
                "--devforge-dir", str(dev), "record-out-of-scope",
                "--content", "system-level monitoring integration — out of scope",
            ])

            r = _run([
                "--devforge-dir", str(dev), "verify-scope-coherence",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(
                r.stderr.strip(), "",
                "Expected no stderr when no targets exist; got: " + r.stderr,
            )

    # ------------------------------------------------------------------
    # Stopword regression: "system" and "shall" in OOS + EARS ACs must
    # NOT fire a spurious overlap warning (F1 fix verification).
    # ------------------------------------------------------------------

    def test_system_shall_scope_stopwords_no_spurious_warning(self):
        """OOS entry containing 'system' + EARS ACs starting 'The system shall'
        → NO spurious overlap warning after stopword fix (F1)."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])

            # §6 OOS entry that mentions "system" and "scope" — universal words
            # that should NOT match every EARS AC that starts "The system shall".
            _run([
                "--devforge-dir", str(dev), "record-out-of-scope",
                "--content",
                "system-level monitoring integration — out of scope",
            ])

            # §5 ACs using canonical EARS ubiquitous form ("The system shall …")
            # sharing ONLY the stopwords "system", "shall", "scope" with the OOS entry.
            _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "behavior_change",
                "--ears-variant", "ubiquitous",
                "--statement",
                "The system shall emit deterministic markdown output.",
            ])
            _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "behavior_preservation",
                "--ears-variant", "ubiquitous",
                "--statement",
                "The system shall preserve existing API contracts.",
            ])

            r = _run([
                "--devforge-dir", str(dev), "verify-scope-coherence",
            ])
            self.assertEqual(r.returncode, 0,
                             "verify-scope-coherence must exit 0; stderr: " + r.stderr)
            # No warning should be surfaced — "system", "shall", "scope" are
            # stopwords and must NOT create spurious overlap.
            self.assertNotIn(
                "verify-scope-coherence:", r.stderr,
                "Spurious warning from stopword tokens; stderr: " + r.stderr,
            )

    # ------------------------------------------------------------------
    # Empty spec (no §5, no §4, no §6): no-op, exit 0.
    # ------------------------------------------------------------------

    def test_empty_state_exit_zero(self):
        """Fresh-reset state with nothing recorded → exit 0, no output."""
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])

            r = _run([
                "--devforge-dir", str(dev), "verify-scope-coherence",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stderr.strip(), "",
                             "Expected no stderr for empty state; got: " + r.stderr)


# ---------------------------------------------------------------------------
# Phase 4 — render (deterministic 9-section markdown).
# ---------------------------------------------------------------------------


class TestPhase4Render(unittest.TestCase):
    def _seed(self, td: str) -> Path:
        dev = Path(td) / ".devforge"
        _run(["--devforge-dir", str(dev), "reset-state"])
        _run(["--devforge-dir", str(dev), "set-date",
              "--date", "2026-05-15"])
        _run(["--devforge-dir", str(dev), "assign-feature-name",
              "--feature-name", "test-spec"])
        return dev

    def test_emits_9_sections(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            r = _run(["--devforge-dir", str(dev), "render"])
            self.assertEqual(r.returncode, 0, r.stderr)
            for heading in (
                "# Spec: test-spec",
                "**Date**: 2026-05-15",
                "**Status**: Draft",
                "**Design source**: none",
                "**Author**: Claude + User",
                "## 1. Overview",
                "## 2. Current State",
                "## 3. Desired Behavior",
                "## 4. Affected Areas",
                "## 5. Acceptance Criteria",
                "## 6. Out of Scope",
                "## 7. Technical Constraints",
                "## 8. Open Questions",
                "## 9. Risks",
            ):
                self.assertIn(heading, r.stdout, "missing: " + heading)

    def test_emits_7_ac_subsections_in_locked_order(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            r = _run(["--devforge-dir", str(dev), "render"])
            for sub_num, sub_label in (
                ("5.1", "Tooling / artifact presence and absence"),
                ("5.2", "Behavior preservation"),
                ("5.3", "Behavior change"),
                ("5.4", "CI / pipeline"),
                ("5.5", "Hooks / gates"),
                ("5.6", "Documentation"),
                ("5.7", "Hygiene"),
            ):
                heading = "### {0} {1}".format(sub_num, sub_label)
                self.assertIn(heading, r.stdout)
            # Locked order check
            positions = [
                r.stdout.index("### {0} ".format(n))
                for n in ("5.1", "5.2", "5.3", "5.4", "5.5", "5.6", "5.7")
            ]
            self.assertEqual(positions, sorted(positions))

    def test_emits_coverage_rule_banner_verbatim(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            r = _run(["--devforge-dir", str(dev), "render"])
            self.assertIn(specify_helper.COVERAGE_RULE_BANNER, r.stdout)

    def test_emits_ac_framing_line_verbatim(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            r = _run(["--devforge-dir", str(dev), "render"])
            self.assertIn(specify_helper.AC_FRAMING_LINE, r.stdout)

    def test_render_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            _run(["--devforge-dir", str(dev), "set-overview",
                  "--content", "x"])
            _run(["--devforge-dir", str(dev), "add-ac",
                  "--subsection", "behavior_change",
                  "--ears-variant", "ubiquitous",
                  "--statement", "The system shall x."])
            r1 = _run(["--devforge-dir", str(dev), "render"])
            r2 = _run(["--devforge-dir", str(dev), "render"])
            self.assertEqual(r1.stdout, r2.stdout)

    def test_renders_ac_verification_and_test_anchor(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "tooling_artifact_presence",
                "--ears-variant", "ubiquitous",
                "--statement",
                "The repo shall contain no `lerna`.",
                "--verification-command", "grep -r lerna . returns 0 matches",
                "--test-anchor", "tests/repo.test.ts::no_lerna",
            ])
            r = _run(["--devforge-dir", str(dev), "render"])
            self.assertIn(
                "> Verification: grep -r lerna . returns 0 matches",
                r.stdout,
            )
            self.assertIn(
                "> Test: tests/repo.test.ts::no_lerna", r.stdout,
            )

    def test_renders_subsection_na_marker(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "ci_pipeline",
                "--mark-na",
                "--n-a-reason", "no CI in scope",
            ])
            r = _run(["--devforge-dir", str(dev), "render"])
            self.assertIn("N/A — no CI in scope", r.stdout)

    def test_renders_constraints_in_kind_order(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "nfr",
                "--quantifier", "p95 < 200ms",
                "--content", "nfr thing",
            ])
            _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "follow", "--content", "follow thing",
            ])
            _run([
                "--devforge-dir", str(dev), "record-constraint",
                "--kind", "not_break", "--content", "not break thing",
            ])
            r = _run(["--devforge-dir", str(dev), "render"])
            pf = r.stdout.index("Must follow")
            pn = r.stdout.index("Must not break")
            pnfr = r.stdout.index("Must satisfy NFR")
            self.assertLess(pf, pn)
            self.assertLess(pn, pnfr)

    def test_renders_dp_default_applied_in_open_questions(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            env = os.environ.copy()
            env[specify_helper.AUTO_MODE_ENV_VAR] = "1"
            _run(["--devforge-dir", str(dev), "detect-mode"], env=env)
            _run([
                "--devforge-dir", str(dev), "record-decision-point",
                "--category", "tooling_configuration",
                "--description", "package manager",
                "--valid-implementations", json.dumps(["pnpm", "yarn"]),
            ])
            _run([
                "--devforge-dir", str(dev), "set-dp-default-applied",
                "--dp-id", "DP-tooling_configuration-1",
                "--default-applied", "pnpm",
            ])
            r = _run(["--devforge-dir", str(dev), "render"])
            self.assertIn("[default applied]", r.stdout)
            self.assertIn("pnpm", r.stdout)


# ---------------------------------------------------------------------------
# Phase 5 — approval + handoff.
# ---------------------------------------------------------------------------


class TestPhase5RenderSummary(unittest.TestCase):
    def test_emits_4_bullets_and_persists(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run(["--devforge-dir", str(dev), "assign-feature-name",
                  "--feature-name", "test-spec"])
            _run([
                "--devforge-dir", str(dev), "assign-spec-number",
                "--specs-root", str(Path(td) / "specs"),
            ])
            _run(["--devforge-dir", str(dev), "set-overview",
                  "--content", "Migrate the thing."])
            _run([
                "--devforge-dir", str(dev), "record-affected-area",
                "--area", "Tooling",
                "--files", json.dumps(["a.json", "b.json"]),
                "--impact", "rewrite",
            ])
            _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "behavior_change",
                "--ears-variant", "ubiquitous",
                "--statement", "The thing shall change.",
            ])
            _run([
                "--devforge-dir", str(dev), "record-out-of-scope",
                "--content", "Unrelated stuff",
            ])
            r = _run(["--devforge-dir", str(dev), "render-summary"])
            self.assertEqual(r.returncode, 0, r.stderr)
            for needle in (
                "specs/001-test-spec/spec.md",
                "**What changes**:",
                "**Files affected**:",
                "**Acceptance criteria**:",
                "**Out of scope**:",
                "Please review and either approve or request changes.",
                "run `/devforge:plan`",
            ):
                self.assertIn(needle, r.stdout)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(state["approval_summary"], r.stdout.rstrip("\n"))


class TestPhase5SetStatus(unittest.TestCase):
    def test_accepts_each_status(self):
        for status in specify_helper.SPEC_STATUS_ENUM:
            with tempfile.TemporaryDirectory() as td:
                dev = Path(td) / ".devforge"
                _run(["--devforge-dir", str(dev), "reset-state"])
                r = _run([
                    "--devforge-dir", str(dev), "set-status",
                    "--status", status,
                ])
                self.assertEqual(r.returncode, 0, r.stderr)
                state = json.loads((dev / "specify-state.json").read_text())
                self.assertEqual(state["status"], status)

    def test_rejects_bogus_status(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "set-status",
                "--status", "Bogus",
            ])
            self.assertEqual(r.returncode, 2)


class TestPhase5RenderPlanHandoff(unittest.TestCase):
    def test_emits_handoff_block(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run(["--devforge-dir", str(dev), "assign-feature-name",
                  "--feature-name", "test-spec"])
            _run([
                "--devforge-dir", str(dev), "assign-spec-number",
                "--specs-root", str(Path(td) / "specs"),
            ])
            _run([
                "--devforge-dir", str(dev), "classify-spec-type",
                "--spec-type", "feature_addition",
                "--rationale", "new feature",
            ])
            _run(["--devforge-dir", str(dev), "set-status",
                  "--status", "Approved"])
            _run([
                "--devforge-dir", str(dev), "add-ac",
                "--subsection", "behavior_change",
                "--ears-variant", "ubiquitous",
                "--statement", "The thing shall change.",
            ])
            r = _run([
                "--devforge-dir", str(dev), "render-plan-handoff",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            for needle in (
                "## Manual next step — run /devforge:plan",
                "specs/001-test-spec/handoff.json) is written for /devforge:plan",
                "auto-discovers it on its first run",
                "Restart Claude Code",
                "/devforge:plan specs/001-test-spec/spec.md",
                "Spec status: Approved",
                "Spec type: feature_addition",
                "AC count: 1",
                "Phase 1.5 finding coverage: 100% (all findings landed)",
                "Reference: specs/001-test-spec/spec.md",
            ):
                self.assertIn(needle, r.stdout)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(
                state["plan_handoff_block"], r.stdout.rstrip("\n"),
            )

    def test_handoff_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run(["--devforge-dir", str(dev), "assign-feature-name",
                  "--feature-name", "test-spec"])
            r1 = _run(["--devforge-dir", str(dev), "render-plan-handoff"])
            r2 = _run(["--devforge-dir", str(dev), "render-plan-handoff"])
            self.assertEqual(r1.stdout, r2.stdout)


# ---------------------------------------------------------------------------
# Downstream — resolve-open-question.
# ---------------------------------------------------------------------------


class TestDownstreamResolveOpenQuestion(unittest.TestCase):
    def test_appends_audit_entry(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "resolve-open-question",
                "--question-id", "Q1",
                "--resolution-text", "answered by /plan",
                "--resolution-phase", "plan",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((dev / "specify-state.json").read_text())
            self.assertEqual(len(state["open_question_resolutions"]), 1)
            entry = state["open_question_resolutions"][0]
            self.assertEqual(entry["question_id"], "Q1")
            self.assertEqual(entry["resolution_phase"], "plan")
            self.assertTrue(entry["resolution_timestamp"].endswith("Z"))

    def test_rejects_bogus_phase(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            r = _run([
                "--devforge-dir", str(dev), "resolve-open-question",
                "--question-id", "Q1",
                "--resolution-text", "x",
                "--resolution-phase", "verify",
            ])
            self.assertEqual(r.returncode, 2)

    def test_render_strikes_through_resolved_question(self):
        with tempfile.TemporaryDirectory() as td:
            dev = Path(td) / ".devforge"
            _run(["--devforge-dir", str(dev), "reset-state"])
            _run(["--devforge-dir", str(dev), "assign-feature-name",
                  "--feature-name", "test-spec"])
            _run([
                "--devforge-dir", str(dev), "record-open-question",
                "--question-id", "Q1",
                "--content", "Should X happen?",
            ])
            r1 = _run(["--devforge-dir", str(dev), "render"])
            self.assertIn("**Q1**: Should X happen?", r1.stdout)
            self.assertNotIn("~~", r1.stdout)
            _run([
                "--devforge-dir", str(dev), "resolve-open-question",
                "--question-id", "Q1",
                "--resolution-text", "yes, in plan",
                "--resolution-phase", "plan",
            ])
            r2 = _run(["--devforge-dir", str(dev), "render"])
            self.assertIn("~~", r2.stdout)
            self.assertIn("resolved in plan", r2.stdout)
            self.assertIn("yes, in plan", r2.stdout)


# ---------------------------------------------------------------------------
# Fixture round-trip — migration_tooling + greenfield_feature.
# ---------------------------------------------------------------------------

FIXTURE_DIR = ROOT / "tests" / "lib" / "fixtures"


def _build_migration_fixture_state(td_path: Path) -> Path:
    """Compose the migration_tooling fixture state via real helper calls."""
    dev = td_path / ".devforge"
    specs_root = td_path / "specs"
    specs_root.mkdir(exist_ok=True)
    _run(["--devforge-dir", str(dev), "reset-state"])
    _run(["--devforge-dir", str(dev), "set-date",
          "--date", "2026-05-15"])
    _run([
        "--devforge-dir", str(dev), "assign-feature-name",
        "--feature-name", "monorepo-pnpm-migration",
    ])
    _run([
        "--devforge-dir", str(dev), "assign-spec-number",
        "--specs-root", str(specs_root),
    ])
    _run([
        "--devforge-dir", str(dev), "create-branch",
        "--current-branch", "main", "--default-branch", "main",
    ])

    # Phase 1
    for path in (
        "constitution.md", ".claude/memory/MEMORY.md",
        "CLAUDE.md", "docs/architecture.md",
    ):
        _run([
            "--devforge-dir", str(dev), "record-input-read",
            "--path", path,
        ])
    _run(["--devforge-dir", str(dev), "phase1-finalize"])

    # Phase 1.5 — every finding lands somewhere.
    findings = [
        ("constitution.md", "Workspace forbids `lerna`",       "Constraint"),
        ("constitution.md", "Every package must declare engines field", "Constraint"),
        ("constitution.md", "Single root install required",    "Constraint"),
        ("docs/architecture.md", "Workspace deps via workspace-protocol", "AC"),
        ("docs/architecture.md", "CI runs install before build",         "AC"),
        ("docs/architecture.md", "Build writes artifacts to dist/",      "AC"),
    ]
    for path, content, landed in findings:
        _run([
            "--devforge-dir", str(dev), "record-finding",
            "--source-path", path, "--content", content,
            "--landed-in", landed,
        ])
    for path in (".claude/memory/MEMORY.md", "CLAUDE.md"):
        _run([
            "--devforge-dir", str(dev),
            "mark-source-no-items-relevant",
            "--source-path", path,
        ])
    _run(["--devforge-dir", str(dev), "findings-finalize"])

    # Phase 2
    _run(["--devforge-dir", str(dev), "detect-mode"])
    _run([
        "--devforge-dir", str(dev), "record-decision-point",
        "--category", "scope_boundaries",
        "--description", "Which packages migrate to pnpm",
        "--valid-implementations",
        json.dumps(["all packages", "core packages only"]),
    ])
    _run([
        "--devforge-dir", str(dev), "set-dp-answer",
        "--dp-id", "DP-scope_boundaries-1",
        "--user-answer", "all packages",
    ])
    _run([
        "--devforge-dir", str(dev), "record-decision-point",
        "--category", "breaking_changes",
        "--description", "Behavior on lockfile conflict",
        "--valid-implementations",
        json.dumps(["fail builds on conflict", "warn only"]),
    ])
    _run([
        "--devforge-dir", str(dev), "set-dp-answer",
        "--dp-id", "DP-breaking_changes-1",
        "--user-answer", "fail builds on conflict",
    ])
    _run([
        "--devforge-dir", str(dev), "record-decision-point",
        "--category", "tooling_configuration",
        "--description", "How pnpm gets installed in CI",
        "--valid-implementations",
        json.dumps(["corepack", "global install"]),
    ])
    _run([
        "--devforge-dir", str(dev), "set-dp-answer",
        "--dp-id", "DP-tooling_configuration-1",
        "--user-answer", "corepack",
    ])
    for cat in (
        "existing_behavior", "data_flow_state",
        "edge_cases", "ui_ux_details",
    ):
        _run([
            "--devforge-dir", str(dev), "record-decision-point",
            "--category", cat,
            "--description",
            "no relevant decision point for {0}".format(cat),
            "--no-dp-in-category",
        ])
    _run(["--devforge-dir", str(dev), "dp-finalize"])

    # Phase 3
    _run([
        "--devforge-dir", str(dev), "classify-spec-type",
        "--spec-type", "migration_tooling",
        "--rationale", "swap lerna+yarn for pnpm workspaces",
    ])
    for slot, _desc in (
        specify_helper.MANDATORY_READS_BY_TYPE["migration_tooling"]
    ):
        _run([
            "--devforge-dir", str(dev), "record-mandatory-read",
            "--slot-pattern", slot,
            "--n-a-reason", "covered in subsequent investigation",
        ])
    _run(["--devforge-dir", str(dev), "phase3-finalize"])

    # Phase 4 — narrative + AC + OOS + Constraints + Risks
    _run([
        "--devforge-dir", str(dev), "set-overview",
        "--content",
        "Migrate the monorepo from lerna with yarn to pnpm "
        "workspaces using corepack.",
    ])
    _run([
        "--devforge-dir", str(dev), "set-current-state",
        "--content",
        "Workspace uses lerna for orchestration and yarn for "
        "package install. Lockfiles are yarn.lock files.",
    ])
    _run([
        "--devforge-dir", str(dev), "set-desired-behavior",
        "--content",
        "Workspace uses pnpm workspaces for orchestration. "
        "Lockfile is pnpm-lock.yaml. Corepack pins pnpm version.",
    ])
    _run([
        "--devforge-dir", str(dev), "record-affected-area",
        "--area", "Root tooling",
        "--files", json.dumps([
            "package.json", "pnpm-workspace.yaml",
        ]),
        "--impact", "switch package manager and workspace layout",
    ])
    _run([
        "--devforge-dir", str(dev), "add-ac",
        "--subsection", "tooling_artifact_presence",
        "--ears-variant", "ubiquitous",
        "--statement",
        "The repository shall contain no occurrences of `lerna`.",
        "--verification-command",
        "grep -rE 'lerna' . returns no matches",
    ])
    _run([
        "--devforge-dir", str(dev), "add-ac",
        "--subsection", "behavior_preservation",
        "--ears-variant", "ubiquitous",
        "--statement",
        "The build system shall produce the same dist artifacts as before.",
    ])
    _run([
        "--devforge-dir", str(dev), "add-ac",
        "--subsection", "behavior_change",
        "--ears-variant", "event_driven",
        "--statement",
        "WHEN the developer runs install, the workspace shall use the pnpm lockfile.",
    ])
    _run([
        "--devforge-dir", str(dev), "add-ac",
        "--subsection", "ci_pipeline",
        "--ears-variant", "ubiquitous",
        "--statement",
        "The CI pipeline shall install dependencies via pnpm.",
    ])
    _run([
        "--devforge-dir", str(dev), "add-ac",
        "--subsection", "hooks_gates",
        "--ears-variant", "unwanted",
        "--statement",
        "IF a yarn lockfile is committed, THEN the pre-commit hook shall reject the commit.",
    ])
    _run([
        "--devforge-dir", str(dev), "add-ac",
        "--subsection", "documentation",
        "--ears-variant", "ubiquitous",
        "--statement",
        "The README shall describe pnpm install steps.",
    ])
    _run([
        "--devforge-dir", str(dev), "add-ac",
        "--subsection", "hygiene",
        "--ears-variant", "ubiquitous",
        "--statement",
        "The repository shall contain no leftover yarn lockfiles.",
        "--verification-command",
        "find . -name 'yarn-lock' returns no matches",
    ])
    _run([
        "--devforge-dir", str(dev), "record-out-of-scope",
        "--content", "Migrating CI runner base image",
    ])
    _run([
        "--devforge-dir", str(dev), "record-out-of-scope",
        "--content", "Migrating off TypeScript",
    ])
    _run([
        "--devforge-dir", str(dev), "record-constraint",
        "--kind", "follow",
        "--content",
        "Use pnpm workspace-protocol for intra-repo dependencies",
    ])
    _run([
        "--devforge-dir", str(dev), "record-constraint",
        "--kind", "not_break",
        "--content", "Existing dist output paths",
    ])
    _run([
        "--devforge-dir", str(dev), "record-constraint",
        "--kind", "external_system",
        "--protocol", "corepack",
        "--content", "Corepack to pin pnpm version",
    ])
    _run([
        "--devforge-dir", str(dev), "record-risk",
        "--risk",
        "Phantom dependency surfacing after install switch",
        "--likelihood", "Med", "--impact", "Med",
        "--mitigation",
        "Run typecheck and tests on each package before merge",
    ])
    return dev


def _build_greenfield_fixture_state(td_path: Path) -> Path:
    """Compose the greenfield_feature fixture state via real helper calls."""
    dev = td_path / ".devforge"
    specs_root = td_path / "specs"
    specs_root.mkdir(exist_ok=True)
    _run(["--devforge-dir", str(dev), "reset-state"])
    _run(["--devforge-dir", str(dev), "set-date",
          "--date", "2026-05-15"])
    _run([
        "--devforge-dir", str(dev), "assign-feature-name",
        "--feature-name", "scheduled-export-jobs",
    ])
    _run([
        "--devforge-dir", str(dev), "assign-spec-number",
        "--specs-root", str(specs_root),
    ])
    _run([
        "--devforge-dir", str(dev), "create-branch",
        "--current-branch", "main", "--default-branch", "main",
    ])

    # Phase 1 — include discover/ companion as auto-mode pre-seed source.
    for path in (
        "constitution.md", ".claude/memory/MEMORY.md",
        "CLAUDE.md", "docs/architecture.md",
        "discover/2026-05-14-scheduled-export-jobs.md",
    ):
        _run([
            "--devforge-dir", str(dev), "record-input-read",
            "--path", path,
        ])
    _run(["--devforge-dir", str(dev), "phase1-finalize"])

    findings = [
        ("constitution.md",
         "Section 7 names scaffolding location for new jobs",
         "Constraint"),
        ("constitution.md",
         "Background jobs must emit structured logs",
         "Constraint"),
        ("constitution.md",
         "All new endpoints require auth middleware",
         "Constraint"),
        ("discover/2026-05-14-scheduled-export-jobs.md",
         "Internal canonical: existing job runner under src/jobs/",
         "AC"),
        ("discover/2026-05-14-scheduled-export-jobs.md",
         "Recommended option: extend existing job runner",
         "AC"),
        ("discover/2026-05-14-scheduled-export-jobs.md",
         "Discovery report enumerates two design options",
         "AC"),
    ]
    for path, content, landed in findings:
        _run([
            "--devforge-dir", str(dev), "record-finding",
            "--source-path", path, "--content", content,
            "--landed-in", landed,
        ])
    for path in (
        ".claude/memory/MEMORY.md", "CLAUDE.md",
        "docs/architecture.md",
    ):
        _run([
            "--devforge-dir", str(dev),
            "mark-source-no-items-relevant",
            "--source-path", path,
        ])
    _run(["--devforge-dir", str(dev), "findings-finalize"])

    # Phase 2 — auto-mode default-applied entries demo.
    env = os.environ.copy()
    env[specify_helper.AUTO_MODE_ENV_VAR] = "1"
    _run(["--devforge-dir", str(dev), "detect-mode"], env=env)
    _run([
        "--devforge-dir", str(dev), "record-decision-point",
        "--category", "scope_boundaries",
        "--description", "Export targets supported",
        "--valid-implementations",
        json.dumps(["csv", "csv and json", "csv json parquet"]),
    ])
    _run([
        "--devforge-dir", str(dev), "set-dp-default-applied",
        "--dp-id", "DP-scope_boundaries-1",
        "--default-applied", "csv and json",
    ])
    _run([
        "--devforge-dir", str(dev), "record-decision-point",
        "--category", "tooling_configuration",
        "--description", "Scheduler component to use",
        "--valid-implementations",
        json.dumps(["existing job runner", "new cron service"]),
    ])
    _run([
        "--devforge-dir", str(dev), "set-dp-default-applied",
        "--dp-id", "DP-tooling_configuration-1",
        "--default-applied", "existing job runner",
    ])
    for cat in (
        "existing_behavior", "data_flow_state",
        "edge_cases", "ui_ux_details", "breaking_changes",
    ):
        _run([
            "--devforge-dir", str(dev), "record-decision-point",
            "--category", cat,
            "--description",
            "no relevant decision point for {0}".format(cat),
            "--no-dp-in-category",
        ])
    _run(["--devforge-dir", str(dev), "dp-finalize"])

    # Phase 3 — greenfield_feature.
    _run([
        "--devforge-dir", str(dev), "classify-spec-type",
        "--spec-type", "greenfield_feature",
        "--rationale", "new feature; pre-seeded by /discover handoff",
        "--seeded-by-upstream",
    ])
    _run([
        "--devforge-dir", str(dev), "record-mandatory-read",
        "--read-path", "constitution.md#scaffolding-guide",
    ])
    _run([
        "--devforge-dir", str(dev), "record-mandatory-read",
        "--slot-pattern", "__framework_docs__",
        "--n-a-reason", "no third-party framework involved",
    ])
    _run([
        "--devforge-dir", str(dev), "record-mandatory-read",
        "--read-path", ".claude/memory/MEMORY.md",
    ])
    _run([
        # 68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 4: the greenfield slot
        # for MANDATORY_READS_BY_TYPE moved from "discover/*.md" to
        # "specs/*/discovery-report.md" (_schema.py); this literal must
        # match the new pattern for verify-mandatory-reads to still pass.
        # Not rendered into spec.md (record-input-read/record-finding above
        # cover that; unaffected), so this change does not touch the
        # committed specify-sample-greenfield.md golden fixture.
        "--devforge-dir", str(dev), "record-mandatory-read",
        "--read-path", "specs/001-scheduled-export-jobs/discovery-report.md",
    ])
    _run(["--devforge-dir", str(dev), "phase3-finalize"])

    # Phase 4
    _run([
        "--devforge-dir", str(dev), "set-overview",
        "--content",
        "Introduce scheduled export jobs for tenant data via the "
        "existing job runner.",
    ])
    _run([
        "--devforge-dir", str(dev), "set-current-state",
        "--content",
        "Scaffolding for scheduled jobs lives under src/jobs/ per "
        "constitution Section 7; no export jobs exist yet.",
    ])
    _run([
        "--devforge-dir", str(dev), "set-desired-behavior",
        "--content",
        "Tenants can register a recurring export job and receive a "
        "result file via the existing storage hook.",
    ])
    _run([
        "--devforge-dir", str(dev), "record-affected-area",
        "--area", "Jobs",
        "--files", json.dumps([
            "src/jobs/exports.ts", "src/jobs/registry.ts",
        ]),
        "--impact", "add new job registration and runner glue",
    ])
    _run([
        "--devforge-dir", str(dev), "add-ac",
        "--subsection", "tooling_artifact_presence",
        "--ears-variant", "ubiquitous",
        "--statement",
        "The repository shall contain a new exports job module under src/jobs/.",
        "--verification-command",
        "ls src/jobs/exports.ts returns the file",
    ])
    _run([
        "--devforge-dir", str(dev), "add-ac",
        "--subsection", "behavior_preservation",
        "--mark-na",
        "--n-a-reason", "greenfield surface; nothing to preserve yet",
    ])
    _run([
        "--devforge-dir", str(dev), "add-ac",
        "--subsection", "behavior_change",
        "--ears-variant", "event_driven",
        "--statement",
        "WHEN a tenant registers an export schedule, the runner shall enqueue the job.",
    ])
    _run([
        "--devforge-dir", str(dev), "add-ac",
        "--subsection", "ci_pipeline",
        "--mark-na",
        "--n-a-reason", "no pipeline change required",
    ])
    _run([
        "--devforge-dir", str(dev), "add-ac",
        "--subsection", "hooks_gates",
        "--ears-variant", "state_driven",
        "--statement",
        "WHILE the export job is running, the storage hook shall hold the partial file.",
    ])
    _run([
        "--devforge-dir", str(dev), "add-ac",
        "--subsection", "documentation",
        "--ears-variant", "ubiquitous",
        "--statement",
        "The exports README shall document the new registration flow.",
    ])
    _run([
        "--devforge-dir", str(dev), "add-ac",
        "--subsection", "hygiene",
        "--ears-variant", "ubiquitous",
        "--statement",
        "The repository shall contain no stray TODO markers in the new job module.",
        "--verification-command",
        "grep -E 'TODO' src/jobs/exports.ts returns no matches",
    ])
    _run([
        "--devforge-dir", str(dev), "record-out-of-scope",
        "--content", "Ad-hoc on-demand exports outside scheduling",
    ])
    _run([
        "--devforge-dir", str(dev), "record-constraint",
        "--kind", "follow",
        "--content", "Constitution Section 7 scaffolding rules",
    ])
    _run([
        "--devforge-dir", str(dev), "record-constraint",
        "--kind", "follow",
        "--content", "Existing job runner from src/jobs/registry.ts",
    ])
    _run([
        "--devforge-dir", str(dev), "record-risk",
        "--risk", "Storage hook contention under concurrent exports",
        "--likelihood", "Low", "--impact", "Med",
        "--mitigation",
        "Add per-tenant queue to serialize exports",
    ])
    return dev


def _read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _render_via_helper(devforge_dir: Path) -> str:
    r = _run(["--devforge-dir", str(devforge_dir), "render"])
    if r.returncode != 0:
        raise AssertionError(
            "render failed: rc={0}, stderr={1!r}".format(
                r.returncode, r.stderr,
            )
        )
    return r.stdout


class TestMigrationFixtureRoundTrip(unittest.TestCase):
    fixture_name = "specify-sample-migration.md"

    def test_render_matches_committed_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            dev = _build_migration_fixture_state(Path(td))
            rendered = _render_via_helper(dev)
            state_text = (dev / "specify-state.json").read_text()
        fp = FIXTURE_DIR / self.fixture_name
        if os.environ.get("UPDATE_SPECIFY_FIXTURES") == "1":
            fp.write_text(rendered, encoding="utf-8")
            state = json.loads(state_text)
            (FIXTURE_DIR / "specify-sample-migration-state.json").write_text(
                json.dumps(state, indent=2) + "\n", encoding="utf-8",
            )
        expected = _read_fixture(self.fixture_name)
        self.assertEqual(rendered, expected)

    def test_state_satisfies_phase_gates(self):
        with tempfile.TemporaryDirectory() as td:
            dev = _build_migration_fixture_state(Path(td))
            for cmd in (
                "verify-findings", "verify-decision-coverage",
                "verify-mandatory-reads", "verify-coverage",
                "verify-ac-subsection-coverage", "verify-ac-shape",
                "verify-numerical-consistency",
            ):
                r = _run(["--devforge-dir", str(dev), cmd])
                self.assertEqual(
                    r.returncode, 0,
                    "{0} failed for migration fixture: {1}".format(
                        cmd, r.stderr,
                    ),
                )


class TestGreenfieldFixtureRoundTrip(unittest.TestCase):
    fixture_name = "specify-sample-greenfield.md"

    def test_render_matches_committed_fixture(self):
        with tempfile.TemporaryDirectory() as td:
            dev = _build_greenfield_fixture_state(Path(td))
            rendered = _render_via_helper(dev)
            state_text = (dev / "specify-state.json").read_text()
        fp = FIXTURE_DIR / self.fixture_name
        if os.environ.get("UPDATE_SPECIFY_FIXTURES") == "1":
            fp.write_text(rendered, encoding="utf-8")
            state = json.loads(state_text)
            (FIXTURE_DIR / "specify-sample-greenfield-state.json").write_text(
                json.dumps(state, indent=2) + "\n", encoding="utf-8",
            )
        expected = _read_fixture(self.fixture_name)
        self.assertEqual(rendered, expected)

    def test_state_satisfies_phase_gates(self):
        with tempfile.TemporaryDirectory() as td:
            dev = _build_greenfield_fixture_state(Path(td))
            for cmd in (
                "verify-findings", "verify-decision-coverage",
                "verify-mandatory-reads", "verify-coverage",
                "verify-ac-subsection-coverage", "verify-ac-shape",
                "verify-numerical-consistency",
            ):
                r = _run(["--devforge-dir", str(dev), cmd])
                self.assertEqual(
                    r.returncode, 0,
                    "{0} failed for greenfield fixture: {1}".format(
                        cmd, r.stderr,
                    ),
                )


class TestUpstreamCompanionFixtures(unittest.TestCase):
    def test_research_input_fixture_exists_and_has_handoff_block(self):
        fp = FIXTURE_DIR / "specify-sample-research-input.md"
        self.assertTrue(
            fp.exists(),
            "specify-sample-research-input.md not committed",
        )
        text = fp.read_text(encoding="utf-8")
        # Must contain a /devforge:specify handoff block (single-tilde fence).
        self.assertIn("/devforge:specify", text)

    def test_greenfield_discover_input_fixture_exists(self):
        fp = FIXTURE_DIR / "specify-sample-greenfield-discover-input.md"
        self.assertTrue(
            fp.exists(),
            "specify-sample-greenfield-discover-input.md not committed",
        )
        text = fp.read_text(encoding="utf-8")
        self.assertIn("/devforge:specify", text)


# ---------------------------------------------------------------------------
# Phase 4 — verify-rendered (post-Write integrity gate).
# ---------------------------------------------------------------------------


class TestVerifyRendered(unittest.TestCase):
    """verify-rendered subcommand — canonical-form comparison of on-disk
    spec.md against re-render of current state.

    Render determinism is the precondition for this gate to be meaningful;
    `TestPhase4Render.test_render_is_byte_deterministic` already locks
    that invariant. These tests exercise the gate itself: happy path,
    tamper detection, and cosmetic-noise tolerance (CRLF / trailing
    whitespace / extra trailing newlines).
    """

    def _seed(self, td: str) -> Path:
        """Build a minimal valid state via real setters."""
        dev = Path(td) / ".devforge"
        _run(["--devforge-dir", str(dev), "reset-state"])
        _run(["--devforge-dir", str(dev), "set-date", "--date", "2026-05-18"])
        _run(["--devforge-dir", str(dev), "assign-feature-name",
              "--feature-name", "verify-rendered-fixture"])
        _run(["--devforge-dir", str(dev), "set-overview",
              "--content", "Test fixture for verify-rendered."])
        _run(["--devforge-dir", str(dev), "add-ac",
              "--subsection", "behavior_change",
              "--ears-variant", "ubiquitous",
              "--statement", "The system shall verify rendered specs."])
        return dev

    def _write_render(self, dev: Path, td: str) -> Path:
        """Render via cmd_render + write to disk; return the path."""
        spec_dir = Path(td) / "specs" / "001-verify-rendered-fixture"
        spec_dir.mkdir(parents=True, exist_ok=True)
        spec_path = spec_dir / "spec.md"
        r = _run(["--devforge-dir", str(dev), "render"])
        self.assertEqual(r.returncode, 0, r.stderr)
        spec_path.write_text(r.stdout, encoding="utf-8")
        return spec_path

    def test_render_is_deterministic(self):
        """PRECONDITION: render(state) twice must be byte-identical.

        If this fails the entire verify-rendered gate is meaningless.
        Fix render (strip clock / env / cwd / random reads) before
        shipping the gate.
        """
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            r1 = _run(["--devforge-dir", str(dev), "render"])
            r2 = _run(["--devforge-dir", str(dev), "render"])
            self.assertEqual(
                r1.stdout, r2.stdout,
                "render is non-deterministic — fix render "
                "(strip clock / env / cwd / random reads) "
                "BEFORE shipping verify-rendered gate.",
            )

    def test_verify_rendered_happy_path(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            spec = self._write_render(dev, td)
            r = _run([
                "--devforge-dir", str(dev),
                "verify-rendered",
                "--path", str(spec),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stderr.strip(), "")

    def test_verify_rendered_tamper_path(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            spec = self._write_render(dev, td)
            # Append a stray byte mid-content (not just at EOF — must
            # survive canonical EOF-newline collapse).
            disk = spec.read_text(encoding="utf-8")
            tampered = disk.replace(
                "## 1. Overview",
                "## 1. OverviewTAMPERED",
                1,
            )
            spec.write_text(tampered, encoding="utf-8")
            r = _run([
                "--devforge-dir", str(dev),
                "verify-rendered",
                "--path", str(spec),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("drift at line", r.stderr)

    def test_verify_rendered_tolerates_crlf(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            spec = self._write_render(dev, td)
            disk = spec.read_bytes()
            spec.write_bytes(disk.replace(b"\n", b"\r\n"))
            r = _run([
                "--devforge-dir", str(dev),
                "verify-rendered",
                "--path", str(spec),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_verify_rendered_tolerates_trailing_whitespace(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            spec = self._write_render(dev, td)
            disk = spec.read_text(encoding="utf-8")
            # Append two spaces to the end of every non-empty line.
            mangled = "\n".join(
                (line + "  ") if line.strip() else line
                for line in disk.split("\n")
            )
            spec.write_text(mangled, encoding="utf-8")
            r = _run([
                "--devforge-dir", str(dev),
                "verify-rendered",
                "--path", str(spec),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_verify_rendered_tolerates_extra_trailing_newlines(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            spec = self._write_render(dev, td)
            disk = spec.read_text(encoding="utf-8")
            spec.write_text(disk + "\n\n\n", encoding="utf-8")
            r = _run([
                "--devforge-dir", str(dev),
                "verify-rendered",
                "--path", str(spec),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_verify_rendered_missing_file(self):
        with tempfile.TemporaryDirectory() as td:
            dev = self._seed(td)
            missing = Path(td) / "does-not-exist.md"
            r = _run([
                "--devforge-dir", str(dev),
                "verify-rendered",
                "--path", str(missing),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("path not found", r.stderr)


# ---------------------------------------------------------------------------
# Handoff integration tests — import-handoff + find-handoffs.
# ---------------------------------------------------------------------------

# Path to research_helper.py (to build real handoff.json fixtures).
_RESEARCH_HELPER = ROOT / "src" / "devforge" / "lib" / "research_helper.py"


def _run_research(argv, cwd=None):
    """Run research_helper.py with argv; capture stdout/stderr/exit."""
    cmd = [sys.executable, str(_RESEARCH_HELPER)] + list(argv)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def _build_minimal_handoff(
    devforge: Path,
    handoff_out: Path,
    design_anchor_value: str = None,
    design_anchor_selectors: str = None,
) -> subprocess.CompletedProcess:
    """Build a minimal feature_addition handoff.json via real research_helper setters.

    Non-presentation-layer files → no data_flow_chain required.
    Produces a valid schema handoff.json at handoff_out.
    Returns the finalize-handoff subprocess result (caller asserts returncode).

    design_anchor_value/design_anchor_selectors (plan 53 Phase 2 test support):
    when both are given, calls the real set-design-anchor setter before
    finalize-handoff so the emitted handoff.json carries a captured
    spec_seeds.design_anchor. Omitted (default None) → no anchor captured,
    matching every pre-existing call site's behavior unchanged.
    """
    df = str(devforge)
    _run_research(["--devforge-dir", df, "reset-memo"])
    _run_research(["--devforge-dir", df, "reset-report"])

    # Phase 0 — 6 dimensions.
    for d, val in (
        ("symptom", "Auth token not refreshed on expiry"),
        ("affected-area", "services/auth/token_manager.py"),
        ("repro-or-current", "Log in; wait 1 hour; next request fails 401"),
        ("desired", "Token refreshed transparently before expiry"),
        ("scope", "one module"),
        ("unchanged-behavior", "logout flow unchanged"),
    ):
        _run_research([
            "--devforge-dir", df,
            "set-" + d, "--value", val, "--state", "Clear",
        ])

    _run_research(["--devforge-dir", df, "detect-mode", "--override", "enhancement"])
    _run_research(["--devforge-dir", df, "set-topic", "--value", "auth-token-refresh"])
    _run_research([
        "--devforge-dir", df, "set-verbatim-prompt",
        "--value", "Auth token not refreshed on expiry in services/auth",
    ])
    _run_research(["--devforge-dir", df, "set-date", "--value", "2026-05-19"])

    # Phase 1 — 2 findings + 2 hypotheses + required fields.
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

    # Phase 2 — approaches + recommended.
    for name, desc, complexity in (
        ("Option A: add refresh timer", "Add background timer to refresh token", "Low"),
        ("Option B: check on request", "Check expiry before each request", "Med"),
    ):
        _run_research([
            "--devforge-dir", df, "set-approach",
            "--name", name,
            "--description", desc,
            "--addresses-hypotheses", "[]",
            "--does-not-cover", "[]",
            "--pros", "[]",
            "--cons", "[]",
            "--complexity", complexity,
        ])

    _run_research([
        "--devforge-dir", df, "set-recommended-approach",
        "--name", "Option B: check on request",
        "--rationale", "Simpler; avoids background timer complexity",
        "--hypotheses-addressed", "[]",
        "--hypotheses-not-covered", "[]",
    ])
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
        "--devforge-dir", df, "set-verdict",
        "--value", "Feasible",
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

    # record-fix-path-helper and record-inbound-caller for verify checks.
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

    # set-probe-feasibility — all False → tier=3 (no test framework required).
    _run_research([
        "--devforge-dir", df, "set-probe-feasibility",
        "--data-shape-only", "false",
        "--auth-required", "false",
        "--network-dependent", "false",
        "--timing-dependent", "false",
        "--is-test-code", "false",
    ])
    # Plan 73 D7: declaration-exists guard requires set-evidence-lanes to
    # have been called before finalize-handoff (any true/false combination
    # is accepted -- all False is a valid declaration).
    _run_research([
        "--devforge-dir", df, "set-evidence-lanes",
        "--static-graph", "false",
        "--text-search", "false",
        "--runtime-probe", "false",
        "--history", "false",
    ])

    if design_anchor_value is not None and design_anchor_selectors is not None:
        _run_research([
            "--devforge-dir", df, "set-design-anchor",
            "--value", design_anchor_value,
            "--selectors", design_anchor_selectors,
            "--state", "Clear",
        ])

    # Finalize handoff.
    return _run_research([
        "--devforge-dir", df,
        "finalize-handoff",
        "--emit-handoff-json", str(handoff_out),
    ])


class TestImportHandoff(unittest.TestCase):
    """Tests for specify_helper import-handoff subcommand."""

    def _make_devforge(self, tmp: str) -> Path:
        """Create a minimal .devforge dir inside tmp."""
        d = Path(tmp) / ".devforge"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _run_import(self, devforge: Path, handoff_path: Path, extra: list = None):
        argv = [
            "--devforge-dir", str(devforge),
            "import-handoff",
            "--handoff-path", str(handoff_path),
        ]
        if extra:
            argv += extra
        return _run(argv)

    # ------------------------------------------------------------------

    def test_import_handoff_round_trip(self):
        """Valid handoff.json → import → all 5 fields + source populated.

        Also verifies open_question shape (F1): question_id, content, category_no_dp_reason.
        Blocking OQ gets '[blocking]' suffix in content.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_devforge"
            research_df.mkdir()
            handoff_out = Path(tmp) / "handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0,
                             "finalize-handoff failed: " + r.stderr)
            self.assertTrue(handoff_out.exists())

            # Patch handoff.json to inject one blocking open_question so we
            # can assert the specify-state dict shape (question_id, content,
            # category_no_dp_reason) produced by the updated emitter.
            handoff_data = json.loads(handoff_out.read_text(encoding="utf-8"))
            handoff_data["spec_seeds"]["open_questions"] = [
                {"question": "Is the token refresh idempotent?", "blocking": True},
            ]
            handoff_out.write_text(json.dumps(handoff_data, indent=2), encoding="utf-8")

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertIn("imported:", r2.stdout)
            self.assertIn("downstream_links.spec_path set to", r2.stdout)

            state_path = devforge / "specify-state.json"
            self.assertTrue(state_path.exists())
            state = json.loads(state_path.read_text(encoding="utf-8"))

            # spec_type must be seeded.
            self.assertIsNotNone(state.get("spec_type"))
            # source.handoff_path is install-root-relative (D9(d),
            # 68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 4) — repo_root here
            # is tmp (devforge_dir.parent), and handoff_out sits directly at
            # tmp/handoff.json, so the relative form is just "handoff.json".
            self.assertEqual(state["source"]["handoff_path"], "handoff.json")
            self.assertFalse(state["source"]["handoff_path"].startswith("/"))
            self.assertEqual(
                (Path(tmp) / state["source"]["handoff_path"]).resolve(),
                handoff_out.resolve(),
            )
            self.assertIsNotNone(state["source"]["research_completed_at"])
            # Pre-seeded lists set.
            self.assertIsInstance(state["constraints"], list)
            self.assertIsInstance(state["affected_areas"], list)
            self.assertIsInstance(state["risks"], list)
            self.assertIsInstance(state["open_questions"], list)

            # F1 — open_question shape: {question_id, content, category_no_dp_reason}.
            oqs = state["open_questions"]
            self.assertEqual(len(oqs), 1, "Expected 1 open_question, got: " + repr(oqs))
            oq = oqs[0]
            self.assertEqual(oq["question_id"], "hq-1")
            self.assertTrue(oq["content"], "content must be non-empty")
            # Blocking OQ gets '[blocking]' suffix.
            self.assertIn("[blocking]", oq["content"])
            self.assertIn("category_no_dp_reason", oq)

    def test_import_handoff_rejects_missing_file(self):
        """--handoff-path /nonexistent → exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            r = self._run_import(devforge, Path(tmp) / "nonexistent.json")
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("not found", r.stderr)

    def test_import_handoff_rejects_invalid_json(self):
        """Corrupt file → exit 2 + stderr cite."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            corrupt = Path(tmp) / "bad.json"
            corrupt.write_text("{ not json }", encoding="utf-8")
            r = self._run_import(devforge, corrupt)
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("invalid JSON", r.stderr)

    def test_import_handoff_rejects_schema_validation_fail(self):
        """Handoff.json with bad SHA in literal_archaeology → exit 2 + stderr cite."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            # Build a technically valid JSON but break schema: bad schema_version.
            bad_data = {
                "schema_version": "9.9",   # wrong version
                "research_path": "research/2026-05-19-test.md",
                "research_completed_at": "2026-05-19T10:00:00Z",
                "mode": "feature_addition",
                "intent": {
                    "symptom_summary": "some bug",
                    "desired_summary": "it works",
                    "scope": "file-local",
                },
                "spec_seeds": {
                    "spec_type_hint": "feature_addition",
                    "constraints": [],
                    "affected_areas": [],
                    "risks": [],
                    "open_questions": [],
                },
                "plan_seeds": {
                    "recommended_approach_id": "A",
                    "recommended_approach_summary": "Fix it",
                    "layer_destination": "service layer",
                    "layer_justification": "business logic",
                    "complexity": {"changes": "Low", "risk": "Low", "verify_cost": "Low"},
                },
                "probe": {
                    "tier": "3",
                    "actor": "user",
                    "discriminator": {
                        "primary_confirms_if": "X",
                        "runner_up_confirms_if": "Y",
                        "both_disproved_if": "Z",
                        "production_site_check": None,
                    },
                    "feasibility_check": {
                        "data_shape_only": False,
                        "auth_required": False,
                        "network_dependent": False,
                        "timing_dependent": False,
                        "is_test_code": False,
                    },
                    "test_framework": None,
                    "test_path": None,
                    "script_path": None,
                    "is_first_test_for_file": False,
                },
                "downstream_links": {},
            }
            bad_path = Path(tmp) / "bad_schema.json"
            bad_path.write_text(json.dumps(bad_data), encoding="utf-8")
            r = self._run_import(devforge, bad_path)
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("schema validation failed", r.stderr)

    def test_import_handoff_accepts_legacy_schema_version_enhancement_empty_archaeology(self):
        """Plan 73 OQ-5 Finding-2 fix: reconstruct a pre-plan-73-shaped handoff
        dict through the real import-handoff read path (_dict_to_dataclass
        under the hood, same call site _import_handoff_research uses) and
        assert it imports cleanly.

        Base handoff built via the real research_helper producer
        (_build_minimal_handoff — enhancement/feature_addition mode, empty
        literal_archaeology), then mutated to the EXACT Finding-2 shape:
        schema_version downgraded to "1.1" (predates plan 73 D1) +
        recommended_approach_summary rewritten to a replacement-shaped string
        matching the schema's own narrow presence-gate regex
        (_has_literal_replacement). Before the Finding-2 fix, reconstructing
        this via _dict_to_dataclass (which re-runs Handoff.__post_init__ on
        already-persisted JSON) would raise — even though the file was
        legally valid when research_helper's own finalize-handoff produced
        it under the pre-plan-73 rules (presence was bug-mode-gated then).
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_df_legacy"
            research_df.mkdir()
            handoff_out = Path(tmp) / "legacy_handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            handoff_data = json.loads(handoff_out.read_text(encoding="utf-8"))
            self.assertEqual(handoff_data["mode"], "feature_addition")
            self.assertEqual(handoff_data["spec_seeds"]["literal_archaeology"], [])
            # Simulate a handoff.json written before plan 73 shipped.
            handoff_data["schema_version"] = "1.1"
            handoff_data["plan_seeds"]["recommended_approach_summary"] = (
                "Replace `false` with `isExternal` in loadData call"
            )
            handoff_out.write_text(json.dumps(handoff_data, indent=2), encoding="utf-8")

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertIn("imported:", r2.stdout)

    def test_import_handoff_rejects_current_schema_version_enhancement_empty_archaeology(self):
        """Same mutation, but schema_version LEFT at the CURRENT (post-plan-73)
        value — import-handoff still REJECTS it. Proves the Finding-2 fix
        does not weaken the presence gate for a handoff produced under the
        new (mode-independent) regime — only a handoff stamped with a
        version predating plan 73 D1 is exempted.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_df_current"
            research_df.mkdir()
            handoff_out = Path(tmp) / "current_handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            handoff_data = json.loads(handoff_out.read_text(encoding="utf-8"))
            current_schema_version = handoff_data["schema_version"]
            # Sanity: confirms this handoff really was stamped with the
            # current (post-plan-73) schema_version, not accidentally the
            # legacy one the sibling test downgrades to.
            self.assertNotEqual(current_schema_version, "1.1")
            handoff_data["plan_seeds"]["recommended_approach_summary"] = (
                "Replace `false` with `isExternal` in loadData call"
            )
            handoff_out.write_text(json.dumps(handoff_data, indent=2), encoding="utf-8")

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 2, r2.stderr)
            self.assertIn("schema validation failed", r2.stderr)
            self.assertIn("literal_archaeology", r2.stderr)

    def test_import_handoff_idempotent_re_import_overwrites_pre_seeds(self):
        """Second import succeeds + pre-seed blocks overwritten."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_df"
            research_df.mkdir()
            handoff_out = Path(tmp) / "handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            # First import.
            r1 = self._run_import(devforge, handoff_out)
            self.assertEqual(r1.returncode, 0, r1.stderr)

            state1 = json.loads(
                (devforge / "specify-state.json").read_text(encoding="utf-8")
            )
            spec_type_1 = state1["spec_type"]

            # Second import — same file, must succeed.
            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)

            state2 = json.loads(
                (devforge / "specify-state.json").read_text(encoding="utf-8")
            )
            # Pre-seeded spec_type still same value (re-seeded from same handoff).
            self.assertEqual(state2["spec_type"], spec_type_1)
            # source.handoff_path still set, install-root-relative (D9(d)).
            self.assertEqual(state2["source"]["handoff_path"], "handoff.json")
            self.assertEqual(
                (Path(tmp) / state2["source"]["handoff_path"]).resolve(),
                handoff_out.resolve(),
            )

    def test_import_handoff_warns_when_user_content_present(self):
        """Re-import after user sets overview → WARNING on stderr; overview preserved."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_df"
            research_df.mkdir()
            handoff_out = Path(tmp) / "handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            # First import.
            r1 = self._run_import(devforge, handoff_out)
            self.assertEqual(r1.returncode, 0, r1.stderr)

            # User sets overview after first import.
            _run([
                "--devforge-dir", str(devforge),
                "set-overview",
                "--content", "User-composed overview text",
            ])

            # Second import should succeed + warn.
            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertIn("warning", r2.stderr.lower())
            self.assertIn("user-composed content", r2.stderr)

            # User content preserved.
            state = json.loads(
                (devforge / "specify-state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["overview"], "User-composed overview text")

    def test_import_handoff_future_spec_path_is_handoff_containing_dir(self):
        """68-INTAKE-OWNS-FEATURE-DIR-PLAN.md D5: spec_path is simply the
        handoff's own containing dir + spec.md — NOT a freshly-scanned NNN.
        The handoff here sits at specs/001-auth-token-refresh/handoff.json
        (mimicking the real /research intake layout), so downstream_links
        .spec_path must be exactly "specs/001-auth-token-refresh/spec.md"
        regardless of what else is under specs/.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_df"
            research_df.mkdir()
            feature_dir = Path(tmp) / "specs" / "001-auth-token-refresh"
            handoff_out = feature_dir / "handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)

            handoff_data = json.loads(handoff_out.read_text(encoding="utf-8"))
            spec_path = handoff_data["downstream_links"]["spec_path"]
            self.assertEqual(spec_path, "specs/001-auth-token-refresh/spec.md")

    def test_import_handoff_future_spec_path_ignores_existing_specs_dirs(self):
        """Pre-existing specs/001-foo/ + specs/002-bar/ dirs must NOT shift
        the computed spec_path — no NEW NNN is allocated at import time
        (next_spec_number is never called on this path)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            # Two unrelated existing spec dirs — under the OLD behavior these
            # would have bumped the scanned NNN to 003.
            (Path(tmp) / "specs" / "001-foo").mkdir(parents=True)
            (Path(tmp) / "specs" / "002-bar").mkdir(parents=True)

            research_df = Path(tmp) / "research_df"
            research_df.mkdir()
            feature_dir = Path(tmp) / "specs" / "099-auth-token-refresh"
            handoff_out = feature_dir / "handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)

            handoff_data = json.loads(handoff_out.read_text(encoding="utf-8"))
            spec_path = handoff_data["downstream_links"]["spec_path"]
            self.assertEqual(
                spec_path, "specs/099-auth-token-refresh/spec.md",
                "spec_path must come from the handoff's own dir, not a"
                " fresh NNN scan over sibling specs/ dirs",
            )

    def test_import_handoff_constraint_shapes_preserved(self):
        """Handoff follow constraints arrive in specify state with kind field intact."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_df"
            research_df.mkdir()
            handoff_out = Path(tmp) / "handoff.json"

            # Build minimal handoff (has follow-kind constraints from constitution).
            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            # Patch the handoff.json to inject multiple constraint kinds.
            handoff_data = json.loads(handoff_out.read_text(encoding="utf-8"))
            handoff_data["spec_seeds"]["constraints"] = [
                {"kind": "nfr", "content": "p99 < 200ms", "quantifier": "< 200ms"},
                {
                    "kind": "constitution_anchor",
                    "content": "Follow §3.6 error handling",
                    "constitution_ref": "§3.6",
                },
                {"kind": "follow", "content": "Follow existing logging pattern"},
            ]
            handoff_out.write_text(json.dumps(handoff_data, indent=2), encoding="utf-8")

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)

            state = json.loads(
                (devforge / "specify-state.json").read_text(encoding="utf-8")
            )
            kinds = {c["kind"] for c in state["constraints"]}
            self.assertIn("nfr", kinds)
            self.assertIn("constitution_anchor", kinds)
            self.assertIn("follow", kinds)

            # Check nfr quantifier preserved.
            nfr_rows = [c for c in state["constraints"] if c["kind"] == "nfr"]
            self.assertTrue(len(nfr_rows) >= 1)
            self.assertEqual(nfr_rows[0].get("quantifier"), "< 200ms")

            # Check constitution_anchor ref preserved.
            ca_rows = [c for c in state["constraints"] if c["kind"] == "constitution_anchor"]
            self.assertTrue(len(ca_rows) >= 1)
            self.assertEqual(ca_rows[0].get("constitution_ref"), "§3.6")

    def test_import_handoff_sets_spec_type_seeded_by_upstream(self):
        """import-handoff sets spec_type_seeded_by_upstream=True in state (F4)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_df"
            research_df.mkdir()
            handoff_out = Path(tmp) / "handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)

            state = json.loads(
                (devforge / "specify-state.json").read_text(encoding="utf-8")
            )
            self.assertIs(state.get("spec_type_seeded_by_upstream"), True)

    def test_import_handoff_then_finalize_handoff_carries_root_relative_provenance(self):
        """End-to-end plan-68 D9(d) round trip: a real /research handoff at
        specs/NNN-slug/research-handoff.json -> import-handoff -> (assign
        spec_number/feature_name, mirroring /specify Phase 4's fallback
        guard) -> finalize-handoff -> the WRITTEN specify->plan handoff.json
        carries an install-root-relative provenance.upstream_handoff_path
        (no leading '/'), and it resolves back to the real handoff file."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)
            research_df = tmp_path / "research_df"
            research_df.mkdir()

            feature_dir = tmp_path / "specs" / "001-auth-token-refresh"
            handoff_out = feature_dir / "research-handoff.json"
            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)

            r3 = _run([
                "--devforge-dir", str(devforge), "assign-spec-number",
                "--specs-root", str(tmp_path / "specs"),
            ])
            self.assertEqual(r3.returncode, 0, r3.stderr)
            r4 = _run([
                "--devforge-dir", str(devforge), "assign-feature-name",
                "--feature-name", "auth-token-refresh",
            ])
            self.assertEqual(r4.returncode, 0, r4.stderr)
            # import-handoff seeds spec_type but not spec_type_rationale;
            # finalize-handoff's Classification requires both non-empty.
            state_before = json.loads(
                (devforge / "specify-state.json").read_text(encoding="utf-8")
            )
            r4b = _run([
                "--devforge-dir", str(devforge), "classify-spec-type",
                "--spec-type", state_before["spec_type"],
                "--rationale", "seeded from /research handoff",
                "--seeded-by-upstream",
            ])
            self.assertEqual(r4b.returncode, 0, r4b.stderr)
            r4c = _run([
                "--devforge-dir", str(devforge), "set-overview",
                "--content", "Refresh the auth token before it expires.",
            ])
            self.assertEqual(r4c.returncode, 0, r4c.stderr)

            out_handoff = tmp_path / "plan-handoff.json"
            r5 = _run([
                "--devforge-dir", str(devforge), "finalize-handoff",
                "--emit-handoff-json", str(out_handoff),
            ])
            self.assertEqual(r5.returncode, 0, r5.stderr)

            written = json.loads(out_handoff.read_text(encoding="utf-8"))
            upstream_path = written["provenance"]["upstream_handoff_path"]
            self.assertEqual(
                upstream_path,
                "specs/001-auth-token-refresh/research-handoff.json",
            )
            self.assertFalse(upstream_path.startswith("/"))
            # Resolves correctly against the install root (repo_root == tmp,
            # the parent of the .devforge dir passed to every verb here).
            self.assertEqual(
                (tmp_path / upstream_path).resolve(), handoff_out.resolve(),
            )

    def test_import_handoff_seeds_spec_number_and_slug_research(self):
        """python-reviewer finding 1(a): a research handoff at
        specs/NNN-slug/research-handoff.json seeds state["spec_number"] +
        state["feature_slug"] from the handoff's own containing dir name --
        without this, a later fresh assign-spec-number scan would send
        spec.md to a DIFFERENT dir than the one the intake artifacts live
        in."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)
            research_df = tmp_path / "research_df"
            research_df.mkdir()
            feature_dir = tmp_path / "specs" / "003-auth-token-refresh"
            handoff_out = feature_dir / "research-handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)

            state = json.loads(
                (devforge / "specify-state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["spec_number"], "003")
            self.assertEqual(state["feature_slug"], "auth-token-refresh")

    def test_import_handoff_non_nnn_parent_leaves_spec_number_slug_unseeded(self):
        """python-reviewer finding 1(a): a handoff whose containing dir does
        NOT match NNN-slug (e.g. a pre-migration handoff imported from an
        arbitrary path) leaves spec_number/feature_slug unseeded -- no
        error. The D5 fallback guard (assign-spec-number / set-spec-number)
        covers this case downstream."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_devforge"
            research_df.mkdir()
            # handoff.json directly at tmp/ -- its parent dir name is
            # whatever tmp's own basename is, never "NNN-slug" shaped.
            handoff_out = Path(tmp) / "handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)

            state = json.loads(
                (devforge / "specify-state.json").read_text(encoding="utf-8")
            )
            self.assertIsNone(state["spec_number"])
            self.assertIsNone(state["feature_slug"])

    def test_import_handoff_outside_repo_root_stores_absolute_handoff_path(self):
        """python-reviewer finding 3: _root_relative's outside-root
        fallback -- a --handoff-path pointing at a file in a SIBLING tmp
        dir outside the repo root (devforge_dir.parent) stores the
        absolute string verbatim in state["source"]["handoff_path"], no
        exception."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo_root = tmp_path / "repo"
            repo_root.mkdir()
            devforge = repo_root / ".devforge"
            devforge.mkdir()

            # The handoff lives in a SIBLING dir, outside repo_root.
            outside_dir = tmp_path / "outside"
            outside_dir.mkdir()
            research_df = tmp_path / "research_df"
            research_df.mkdir()
            handoff_out = outside_dir / "handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            r2 = _run([
                "--devforge-dir", str(devforge),
                "import-handoff",
                "--handoff-path", str(handoff_out),
            ])
            self.assertEqual(r2.returncode, 0, r2.stderr)

            state = json.loads(
                (devforge / "specify-state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                Path(state["source"]["handoff_path"]).resolve(),
                handoff_out.resolve(),
            )
            self.assertTrue(
                Path(state["source"]["handoff_path"]).is_absolute(),
                "outside-root handoff_path must fall back to the absolute"
                " string, not raise or produce a nonsense relative path",
            )
            # The outside-root dir isn't NNN-slug shaped either, so
            # spec_number/feature_slug stay unseeded (finding 1(a)'s
            # no-match arm exercised simultaneously by this fixture).
            self.assertIsNone(state["spec_number"])
            self.assertIsNone(state["feature_slug"])


class TestFindHandoffs(unittest.TestCase):
    """Tests for specify_helper find-handoffs subcommand.

    68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 4: fixtures now anchor at
    specs/NNN-slug/research-handoff.json (the new intake layout) instead of
    the retired top-level research/<date>-<slug>/handoff.json. Deeper
    coverage of the D5 predicate + --since deprecation lives in the
    dedicated tests/lib/_specify/test_find_handoffs_require.py; this class
    keeps the specify_helper.py-adjacent smoke coverage for the same verb.
    """

    def _make_devforge(self, tmp: str) -> Path:
        d = Path(tmp) / ".devforge"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _run_find(self, devforge: Path):
        return _run(["--devforge-dir", str(devforge), "find-handoffs"])

    def _build_handoff_at(self, tmp: Path, research_df: Path, feature_dirname: str) -> Path:
        """Build a research-handoff.json at tmp/specs/<feature_dirname>/ via real setters."""
        feature_dir = tmp / "specs" / feature_dirname
        handoff_out = feature_dir / "research-handoff.json"
        r = _build_minimal_handoff(research_df, handoff_out)
        if r.returncode != 0:
            raise RuntimeError("finalize-handoff failed: " + r.stderr)
        return handoff_out

    # ------------------------------------------------------------------

    def test_find_handoffs_surfaces_pending_feature(self):
        """A pending feature dir (handoff present, spec.md absent) surfaces."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)

            df_a = tmp_path / "df_a"
            df_a.mkdir()
            self._build_handoff_at(tmp_path, df_a, "001-auth-token-refresh")

            r = self._run_find(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)

            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 1, "Expected 1 hit, got: " + r.stdout)
            self.assertIn("kind=research", lines[0])

    def test_find_handoffs_zero_hits(self):
        """No handoffs → exit 0, empty stdout."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            # No specs/ dir → zero hits.
            r = self._run_find(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "")

    def test_find_handoffs_invalid_since_rejected(self):
        """--since 'foo' → exit 2 (format still validated when supplied)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            r = _run([
                "--devforge-dir", str(devforge),
                "find-handoffs", "--since", "foo",
            ])
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("--since", r.stderr)

    def test_find_handoffs_skips_corrupt_handoff_silently(self):
        """One valid + one corrupt → only valid in output, exit 0.

        The valid handoff is built via real research_helper setters; its
        research_path contains the topic slug 'auth-token-refresh'. The
        corrupt handoff is raw JSON that will fail schema parsing. Only 1
        line in output.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)

            # Build one valid handoff.
            df_a = tmp_path / "df_a"
            df_a.mkdir()
            self._build_handoff_at(tmp_path, df_a, "001-valid-feature")

            # Create a corrupt handoff in a sibling feature dir.
            corrupt_dir = tmp_path / "specs" / "002-corrupt"
            corrupt_dir.mkdir(parents=True)
            corrupt = corrupt_dir / "research-handoff.json"
            corrupt.write_text("{ not json }", encoding="utf-8")

            r = self._run_find(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)

            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            # Only the valid handoff should appear; corrupt is skipped silently.
            self.assertEqual(len(lines), 1, "Expected 1 hit, got: " + r.stdout)
            # The valid handoff's output line contains the mode and summary fields.
            self.assertIn("feature_addition", lines[0])

    def test_find_handoffs_excludes_feature_with_spec_md(self):
        """D5: a feature dir whose spec.md already exists is not pending."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)

            df_a = tmp_path / "df_a"
            df_a.mkdir()
            handoff_out = self._build_handoff_at(tmp_path, df_a, "001-auth-token-refresh")
            (handoff_out.parent / "spec.md").write_text("# spec\n", encoding="utf-8")

            r = self._run_find(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "")

    def test_find_handoffs_surfaces_legacy_schema_version_enhancement_empty_archaeology(self):
        """Plan 73 Phase 1 LOW review finding: find-handoffs' read path
        (_try_research_hit -> _dict_to_dataclass, the second call site to
        _import_handoff_research's, at _cmds_handoff.py's cmd_find_handoffs
        helper) must honor the same schema_version carve-out as
        import-handoff -- a legacy (pre-plan-73) enhancement-mode handoff
        with empty literal_archaeology and a replacement-shaped
        recommended_approach_summary must surface as a hit, not be
        silently dropped by _try_research_hit's bare
        `except Exception: return None`.

        Same fixture shape as
        TestImportHandoff.test_import_handoff_accepts_legacy_schema_version_enhancement_empty_archaeology
        (built via the real research_helper producer, then mutated
        on-disk to schema_version="1.1" + a replacement-shaped summary),
        but driven through find-handoffs instead of import-handoff so the
        _try_research_hit call site gets its own coverage.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)

            df_legacy = tmp_path / "df_legacy"
            df_legacy.mkdir()
            handoff_out = self._build_handoff_at(tmp_path, df_legacy, "001-legacy-handoff")

            handoff_data = json.loads(handoff_out.read_text(encoding="utf-8"))
            self.assertEqual(handoff_data["mode"], "feature_addition")
            self.assertEqual(handoff_data["spec_seeds"]["literal_archaeology"], [])
            # Simulate a research-handoff.json written before plan 73 shipped.
            handoff_data["schema_version"] = "1.1"
            handoff_data["plan_seeds"]["recommended_approach_summary"] = (
                "Replace `false` with `isExternal` in loadData call"
            )
            handoff_out.write_text(json.dumps(handoff_data, indent=2), encoding="utf-8")

            r = self._run_find(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)

            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 1, "Expected 1 hit, got: " + r.stdout)
            self.assertIn("kind=research", lines[0])
            self.assertIn("mode=feature_addition", lines[0])

    def test_find_handoffs_skips_current_schema_version_enhancement_empty_archaeology(self):
        """Negative counterpart: the SAME mutation, but schema_version LEFT
        at the CURRENT (post-plan-73) value -- reconstruction fails schema
        validation, and _try_research_hit's bare
        `except Exception: return None` skips the file SILENTLY (exit 0,
        zero hits) rather than surfacing or erroring on it. Confirms the
        Finding-2 carve-out is version-gated on the find-handoffs path too
        -- not a blanket loosening of _try_research_hit's schema check.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)

            df_current = tmp_path / "df_current"
            df_current.mkdir()
            handoff_out = self._build_handoff_at(tmp_path, df_current, "001-current-handoff")

            handoff_data = json.loads(handoff_out.read_text(encoding="utf-8"))
            current_schema_version = handoff_data["schema_version"]
            # Sanity: confirms this handoff really was stamped with the
            # current (post-plan-73) schema_version, not accidentally the
            # legacy one the sibling test downgrades to.
            self.assertNotEqual(current_schema_version, "1.1")
            handoff_data["plan_seeds"]["recommended_approach_summary"] = (
                "Replace `false` with `isExternal` in loadData call"
            )
            handoff_out.write_text(json.dumps(handoff_data, indent=2), encoding="utf-8")

            r = self._run_find(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "")


# ---------------------------------------------------------------------------
# Discover handoff integration tests — import-handoff (discover kind) +
# find-handoffs cross-kind.
# ---------------------------------------------------------------------------

_DISCOVER_HELPER = ROOT / "src" / "devforge" / "lib" / "discover_helper.py"
_DISCOVER_LIB = ROOT / "src" / "devforge" / "lib"


def _run_discover(argv, cwd=None):
    """Run discover_helper.py with argv; capture stdout/stderr/exit."""
    cmd = [sys.executable, str(_DISCOVER_HELPER)] + list(argv)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def _build_minimal_discover_handoff(
    devforge: Path,
    handoff_out: Path,
    design_anchor_value: str = None,
    design_anchor_selectors: str = None,
) -> subprocess.CompletedProcess:
    """Build a minimal 'Worth pursuing' discover handoff.json via real discover_helper setters.

    Uses flat discover/<slug>.handoff.json naming (discover schema).
    Returns the finalize-handoff subprocess result (caller asserts returncode).

    design_anchor_value/design_anchor_selectors (plan 53 Phase 2 test support):
    when both are given, calls the real set-scope-design-anchor setter before
    finalize-handoff so the emitted handoff.json carries a captured
    spec_seeds.design_anchor. Omitted (default None) → no anchor captured,
    matching every pre-existing call site's behavior unchanged.
    """
    df = str(devforge)
    # Reset state.
    _run_discover(["--devforge-dir", df, "reset-memo"])
    _run_discover(["--devforge-dir", df, "reset-report"])

    # Set topic.
    _run_discover(["--devforge-dir", df, "set-topic", "--value", "audit-log-persistence"])
    _run_discover([
        "--devforge-dir", df, "set-verbatim-prompt",
        "--value", "Build an audit log persistence system for tracking state changes",
    ])
    _run_discover(["--devforge-dir", df, "set-date", "--value", "2026-05-20"])

    # Set all 8 rubric dimensions to Clear.
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

    # Set report fields.
    _run_discover([
        "--devforge-dir", df, "set-summary",
        "--value", "Audit log persistence system",
    ])
    _run_discover([
        "--devforge-dir", df, "set-overall-fit",
        "--value", "Good",
    ])
    _run_discover([
        "--devforge-dir", df, "set-effort-estimate",
        "--value", "Low",
    ])
    _run_discover([
        "--devforge-dir", df, "set-fit-rationale",
        "--value", "Straightforward ORM extension",
    ])
    _run_discover([
        "--devforge-dir", df, "set-verdict",
        "--value", "Worth pursuing",
    ])
    # Record one integration touchpoint (required by discover verify).
    _run_discover([
        "--devforge-dir", df, "record-integration-touchpoint",
        "--name", "ORM layer",
        "--module-path", "src/db/orm.py",
        "--reason", "Audit writes through ORM",
    ])
    # Add one design option.
    _run_discover([
        "--devforge-dir", df, "set-design-option",
        "--name", "PostgreSQL table",
        "--shape", "ORM table",
        "--pros", '["Simple"]',
        "--cons", '["Single DB"]',
        "--complexity", "Low",
    ])
    # Set recommended option.
    _run_discover([
        "--devforge-dir", df, "set-recommended-option",
        "--name", "PostgreSQL table",
        "--rationale", "Lowest complexity for current scale",
    ])
    # Set build-vs-buy.
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
    # Set derisk plan (must be a JSON array of strings).
    _run_discover([
        "--devforge-dir", df, "set-derisk-plan",
        "--items", '["Spike: write load test against ORM layer before committing"]',
    ])
    # Set recommendation.
    _run_discover([
        "--devforge-dir", df, "set-recommendation",
        "--action", "Proceed with PostgreSQL table approach",
        "--next", "Run /specify audit-log-persistence",
    ])
    # set-next-step-text auto-composes from memo + report state.
    _run_discover([
        "--devforge-dir", df, "set-next-step-text",
        "--feature-dir", "specs/001-audit-log-persistence",
    ])

    if design_anchor_value is not None and design_anchor_selectors is not None:
        _run_discover([
            "--devforge-dir", df, "set-scope-design-anchor",
            "--value", design_anchor_value,
            "--selectors", design_anchor_selectors,
            "--state", "Clear",
        ])

    # Finalize handoff.
    return _run_discover([
        "--devforge-dir", df,
        "finalize-handoff",
        "--emit-handoff-json", str(handoff_out),
    ])


class TestImportHandoffDiscover(unittest.TestCase):
    """Tests for specify_helper import-handoff with kind=discover dispatch."""

    def _make_devforge(self, tmp: str) -> Path:
        d = Path(tmp) / ".devforge"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _run_import(self, devforge: Path, handoff_path: Path):
        return _run([
            "--devforge-dir", str(devforge),
            "import-handoff",
            "--handoff-path", str(handoff_path),
        ])

    def _build_discover_handoff(self, tmp: Path) -> Path:
        devforge_d = tmp / "discover_df"
        devforge_d.mkdir(exist_ok=True)
        discover_dir = tmp / "discover"
        discover_dir.mkdir(exist_ok=True)
        handoff_out = discover_dir / "2026-05-20-audit-log-persistence.handoff.json"
        r = _build_minimal_discover_handoff(devforge_d, handoff_out)
        if r.returncode != 0:
            raise RuntimeError(
                "_build_minimal_discover_handoff failed: " + r.stderr
            )
        return handoff_out

    # ------------------------------------------------------------------

    def test_import_handoff_discover_round_trip(self):
        """Discover handoff.json -> import -> state pre-seeded correctly.

        Verifies: spec_type=greenfield_feature, source.handoff_kind='discover',
        source.discover_completed_at non-None, constraints/areas/risks/open_questions
        populated (lists exist).
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)
            handoff_out = self._build_discover_handoff(tmp_path)

            r = self._run_import(devforge, handoff_out)
            self.assertEqual(r.returncode, 0, "import failed: " + r.stderr)
            self.assertIn("imported:", r.stdout)
            self.assertIn("kind=discover", r.stdout)
            self.assertIn("downstream_links.spec_path set to", r.stdout)

            state = json.loads(
                (devforge / "specify-state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["spec_type"], "greenfield_feature")
            self.assertIs(state["spec_type_seeded_by_upstream"], True)
            self.assertEqual(state["source"]["handoff_kind"], "discover")
            self.assertIsNotNone(state["source"]["discover_completed_at"])
            self.assertIsNone(state["source"]["research_completed_at"])
            self.assertIsInstance(state["constraints"], list)
            self.assertIsInstance(state["affected_areas"], list)
            self.assertIsInstance(state["risks"], list)
            self.assertIsInstance(state["open_questions"], list)

    def test_import_handoff_discover_rejects_unknown_kind(self):
        """handoff_kind='bogus' -> exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            bad_path = Path(tmp) / "bogus.handoff.json"
            bad_path.write_text(
                json.dumps({"handoff_kind": "bogus", "schema_version": "1.0"}),
                encoding="utf-8",
            )
            r = self._run_import(devforge, bad_path)
            self.assertEqual(r.returncode, 2, "expected exit 2, stderr: " + r.stderr)
            self.assertIn("unknown handoff_kind", r.stderr)

    def test_import_handoff_research_default_when_kind_field_absent(self):
        """Research handoff (no handoff_kind field) -> dispatch to research branch -> exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_df"
            research_df.mkdir()
            handoff_out = Path(tmp) / "handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            # Verify no handoff_kind field in the produced file.
            data = json.loads(handoff_out.read_text(encoding="utf-8"))
            self.assertNotIn("handoff_kind", data)

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, "research import failed: " + r2.stderr)
            self.assertIn("imported:", r2.stdout)
            # Research branch uses kind=research in stdout.
            self.assertIn("kind=research", r2.stdout)

            state = json.loads(
                (devforge / "specify-state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["source"]["handoff_kind"], "research")

    def test_import_handoff_discover_preserves_is_internal_extension_candidate(self):
        """Discover AffectedArea.is_internal_extension_candidate flows through to state."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)
            handoff_out = self._build_discover_handoff(tmp_path)

            # Patch handoff.json to inject an affected area with is_internal_extension_candidate=true.
            data = json.loads(handoff_out.read_text(encoding="utf-8"))
            data["spec_seeds"]["affected_areas"] = [
                {
                    "area": "ORM persistence layer",
                    "files": ["src/db/orm.py"],
                    "impact": "Major write path",
                    "is_internal_extension_candidate": True,
                }
            ]
            handoff_out.write_text(json.dumps(data, indent=2), encoding="utf-8")

            r = self._run_import(devforge, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            state = json.loads(
                (devforge / "specify-state.json").read_text(encoding="utf-8")
            )
            areas = state["affected_areas"]
            self.assertEqual(len(areas), 1)
            self.assertIs(areas[0]["is_internal_extension_candidate"], True)

    def test_import_handoff_discover_rejects_spec_type_override(self):
        """Discover handoff with spec_type_hint != 'greenfield_feature' -> exit 2.

        The discover schema already enforces this at construction, so the
        schema validation itself fires before the helper's extra guard.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            tmp_path = Path(tmp)
            handoff_out = self._build_discover_handoff(tmp_path)

            # Corrupt spec_type_hint to something invalid.
            data = json.loads(handoff_out.read_text(encoding="utf-8"))
            data["spec_seeds"]["spec_type_hint"] = "bug_fix"
            handoff_out.write_text(json.dumps(data, indent=2), encoding="utf-8")

            r = self._run_import(devforge, handoff_out)
            self.assertEqual(r.returncode, 2, "expected exit 2, got: " + r.stdout)
            self.assertIn("schema validation failed", r.stderr)

    def test_import_handoff_discover_records_recommended_summary(self):
        """source.discover_recommended_summary is populated with rationale | bvb-rec."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)
            handoff_out = self._build_discover_handoff(tmp_path)

            r = self._run_import(devforge, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            state = json.loads(
                (devforge / "specify-state.json").read_text(encoding="utf-8")
            )
            summary = state["source"]["discover_recommended_summary"]
            self.assertIsNotNone(summary)
            # Format: "<rationale> | <build_vs_buy.recommendation>"
            self.assertIn("|", summary)
            # Must contain the bvb recommendation.
            self.assertIn("Build", summary)

    def test_import_handoff_research_unchanged_behavior(self):
        """Regression anchor: research handoff (kind absent) still populates all 5 pre-seed fields + source."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_df"
            research_df.mkdir()
            handoff_out = Path(tmp) / "handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)

            state = json.loads(
                (devforge / "specify-state.json").read_text(encoding="utf-8")
            )
            self.assertIsNotNone(state["spec_type"])
            self.assertIsInstance(state["constraints"], list)
            self.assertIsInstance(state["affected_areas"], list)
            self.assertIsInstance(state["risks"], list)
            self.assertIsInstance(state["open_questions"], list)
            self.assertIsNotNone(state["source"]["handoff_path"])
            self.assertIsNotNone(state["source"]["research_completed_at"])
            self.assertIs(state["spec_type_seeded_by_upstream"], True)

    def test_import_handoff_seeds_spec_number_and_slug_discover(self):
        """python-reviewer finding 1(a), discover lane: a discover handoff
        at specs/NNN-slug/discover-handoff.json seeds state["spec_number"]
        + state["feature_slug"] from the handoff's own containing dir
        name -- identical rationale to the research-lane test in
        TestImportHandoff."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)
            devforge_d = tmp_path / "discover_df"
            devforge_d.mkdir()
            feature_dir = tmp_path / "specs" / "004-audit-log-persistence"
            handoff_out = feature_dir / "discover-handoff.json"

            r = _build_minimal_discover_handoff(devforge_d, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)

            state = json.loads(
                (devforge / "specify-state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(state["spec_number"], "004")
            self.assertEqual(state["feature_slug"], "audit-log-persistence")


# ---------------------------------------------------------------------------
# Plan 53 Phase 2 — design_anchor carry (Task A), persistence + source_hash
# (Task B), and the /specify backstop composition (Task C).
# ---------------------------------------------------------------------------


class TestDesignAnchorCarryAndPersist(unittest.TestCase):
    """Carry design_anchor across the intake→specify hop, persist
    specs/[feature]/design-anchor.json (with a source_hash provenance
    signal), and the /specify backstop composition from design_source.
    """

    def _make_devforge(self, tmp: str) -> Path:
        d = Path(tmp) / ".devforge"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _run_import(self, devforge: Path, handoff_path: Path):
        return _run([
            "--devforge-dir", str(devforge),
            "import-handoff",
            "--handoff-path", str(handoff_path),
        ])

    def _prep_feature_state(
        self, tmp_path: Path, feature_slug: str = "test-anchor-feature",
    ) -> Path:
        """Create a .devforge dir with spec_number + feature_slug assigned."""
        devforge = self._make_devforge(str(tmp_path))
        r1 = _run(["--devforge-dir", str(devforge), "assign-spec-number"])
        self.assertEqual(r1.returncode, 0, r1.stderr)
        r2 = _run([
            "--devforge-dir", str(devforge), "assign-feature-name",
            "--feature-name", feature_slug,
        ])
        self.assertEqual(r2.returncode, 0, r2.stderr)
        return devforge

    # ------------------------------------------------------------------
    # Task A — carry via cmd_import_handoff (research branch).
    # ------------------------------------------------------------------

    def test_import_handoff_carries_captured_design_anchor_research(self):
        """Real research handoff with a captured design_anchor → carried into specify state verbatim."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_df"
            research_df.mkdir()
            handoff_out = Path(tmp) / "handoff.json"

            r = _build_minimal_handoff(
                research_df, handoff_out,
                design_anchor_value="html:design/reference.html",
                design_anchor_selectors='[".fooBar"]',
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(handoff_out.read_text(encoding="utf-8"))
            self.assertEqual(
                data["spec_seeds"]["design_anchor"],
                {"kind": "html", "file": "design/reference.html", "selectors": [".fooBar"]},
            )

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)

            state = json.loads((devforge / "specify-state.json").read_text(encoding="utf-8"))
            self.assertEqual(
                state["design_anchor"],
                {"kind": "html", "file": "design/reference.html", "selectors": [".fooBar"]},
            )

    def test_import_handoff_empty_design_anchor_research_yields_empty_in_state(self):
        """Research handoff with NO captured anchor → empty anchor in state (not missing)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_df"
            research_df.mkdir()
            handoff_out = Path(tmp) / "handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)

            state = json.loads((devforge / "specify-state.json").read_text(encoding="utf-8"))
            self.assertIn("design_anchor", state)
            self.assertEqual(state["design_anchor"], {"kind": "", "file": "", "selectors": []})

    # ------------------------------------------------------------------
    # Task A — carry via cmd_import_handoff (discover branch).
    # ------------------------------------------------------------------

    def test_import_handoff_carries_captured_design_anchor_discover(self):
        """Real discover handoff with a captured design_anchor → carried into specify state verbatim."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)
            devforge_d = tmp_path / "discover_df"
            devforge_d.mkdir()
            discover_dir = tmp_path / "discover"
            discover_dir.mkdir()
            handoff_out = discover_dir / "2026-07-06-audit-log-persistence.handoff.json"

            r = _build_minimal_discover_handoff(
                devforge_d, handoff_out,
                design_anchor_value="figma:https://figma.com/file/x?node-id=1:2",
                design_anchor_selectors='["Frame 1", "Button/Primary"]',
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(handoff_out.read_text(encoding="utf-8"))
            self.assertEqual(
                data["spec_seeds"]["design_anchor"],
                {
                    "kind": "figma",
                    "file": "https://figma.com/file/x?node-id=1:2",
                    "selectors": ["Frame 1", "Button/Primary"],
                },
            )

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)

            state = json.loads((devforge / "specify-state.json").read_text(encoding="utf-8"))
            self.assertEqual(
                state["design_anchor"],
                {
                    "kind": "figma",
                    "file": "https://figma.com/file/x?node-id=1:2",
                    "selectors": ["Frame 1", "Button/Primary"],
                },
            )

    def test_import_handoff_empty_design_anchor_discover_yields_empty_in_state(self):
        """Discover handoff with NO captured anchor → empty anchor in state (not missing)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)
            devforge_d = tmp_path / "discover_df"
            devforge_d.mkdir()
            discover_dir = tmp_path / "discover"
            discover_dir.mkdir()
            handoff_out = discover_dir / "2026-07-06-audit-log-persistence.handoff.json"

            r = _build_minimal_discover_handoff(devforge_d, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)

            state = json.loads((devforge / "specify-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["design_anchor"], {"kind": "", "file": "", "selectors": []})

    # ------------------------------------------------------------------
    # Back-compat — an intake handoff JSON with NO design_anchor key at all
    # (pre-plan-53 shape) still imports cleanly via the real loader.
    # ------------------------------------------------------------------

    def test_import_handoff_research_backcompat_missing_design_anchor_key(self):
        """Real handoff.json with spec_seeds.design_anchor deleted entirely → still imports; empty anchor in state."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_df"
            research_df.mkdir()
            handoff_out = Path(tmp) / "handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            data = json.loads(handoff_out.read_text(encoding="utf-8"))
            del data["spec_seeds"]["design_anchor"]
            handoff_out.write_text(json.dumps(data, indent=2), encoding="utf-8")

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)

            state = json.loads((devforge / "specify-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["design_anchor"], {"kind": "", "file": "", "selectors": []})

    # ------------------------------------------------------------------
    # Task B — write-design-anchor persists design-anchor.json + source_hash.
    # ------------------------------------------------------------------

    def test_write_design_anchor_html_kind_computes_nonempty_source_hash(self):
        """Carried html anchor + a real reference.html on disk → non-empty source_hash."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._prep_feature_state(tmp_path)

            design_dir = tmp_path / "design"
            design_dir.mkdir()
            ref_html = design_dir / "reference.html"
            ref_html.write_text("<html><body class='fooBar'>Hi</body></html>", encoding="utf-8")

            # Directly seed the carried anchor in state (the carry itself is
            # covered by the Task A tests above).
            state_path = devforge / "specify-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["design_anchor"] = {
                "kind": "html", "file": "design/reference.html", "selectors": [".fooBar"],
            }
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

            r = _run(
                ["--devforge-dir", str(devforge), "write-design-anchor",
                 "--workspace-root", str(tmp_path)],
                cwd=tmp_path,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("wrote:", r.stdout)

            anchor_path = tmp_path / "specs" / "001-test-anchor-feature" / "design-anchor.json"
            self.assertTrue(anchor_path.exists())
            persisted = json.loads(anchor_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["kind"], "html")
            self.assertEqual(persisted["file"], "design/reference.html")
            self.assertEqual(persisted["selectors"], [".fooBar"])
            self.assertTrue(persisted["source_hash"])

            expected_hash = hashlib.sha256(ref_html.read_bytes()).hexdigest()
            self.assertEqual(persisted["source_hash"], expected_hash)

    def test_write_design_anchor_figma_kind_empty_source_hash(self):
        """Carried figma anchor → source_hash is '' (fail-soft, no crash)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._prep_feature_state(tmp_path)

            state_path = devforge / "specify-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["design_anchor"] = {
                "kind": "figma", "file": "https://figma.com/file/x", "selectors": [],
            }
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

            r = _run(
                ["--devforge-dir", str(devforge), "write-design-anchor",
                 "--workspace-root", str(tmp_path)],
                cwd=tmp_path,
            )
            self.assertEqual(r.returncode, 0, r.stderr)

            anchor_path = tmp_path / "specs" / "001-test-anchor-feature" / "design-anchor.json"
            persisted = json.loads(anchor_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["kind"], "figma")
            self.assertEqual(persisted["source_hash"], "")

    def test_write_design_anchor_html_kind_absent_file_empty_source_hash(self):
        """Carried html anchor whose file does not exist on disk → source_hash '' (fail-soft, no crash)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._prep_feature_state(tmp_path)

            state_path = devforge / "specify-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["design_anchor"] = {
                "kind": "html", "file": "design/nonexistent.html", "selectors": [],
            }
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

            r = _run(
                ["--devforge-dir", str(devforge), "write-design-anchor",
                 "--workspace-root", str(tmp_path)],
                cwd=tmp_path,
            )
            self.assertEqual(r.returncode, 0, r.stderr)

            anchor_path = tmp_path / "specs" / "001-test-anchor-feature" / "design-anchor.json"
            persisted = json.loads(anchor_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["kind"], "html")
            self.assertEqual(persisted["source_hash"], "")

    def test_write_design_anchor_html_kind_unreadable_file_empty_source_hash(self):
        """Carried html anchor whose file EXISTS but is unreadable (chmod 0o000) -> source_hash '' (fail-soft, no crash).

        Exercises the `except OSError` branch in _compute_source_hash
        (:109-110) -- distinct from the absent-file branch above, which never
        reaches read_bytes() at all.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._prep_feature_state(tmp_path)

            design_dir = tmp_path / "design"
            design_dir.mkdir()
            ref_html = design_dir / "reference.html"
            ref_html.write_text("<html><body>Hi</body></html>", encoding="utf-8")
            os.chmod(str(ref_html), 0o000)

            try:
                state_path = devforge / "specify-state.json"
                state = json.loads(state_path.read_text(encoding="utf-8"))
                state["design_anchor"] = {
                    "kind": "html", "file": "design/reference.html", "selectors": [],
                }
                state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

                r = _run(
                    ["--devforge-dir", str(devforge), "write-design-anchor",
                     "--workspace-root", str(tmp_path)],
                    cwd=tmp_path,
                )
                self.assertEqual(r.returncode, 0, r.stderr)

                anchor_path = tmp_path / "specs" / "001-test-anchor-feature" / "design-anchor.json"
                persisted = json.loads(anchor_path.read_text(encoding="utf-8"))
                self.assertEqual(persisted["kind"], "html")
                self.assertEqual(persisted["source_hash"], "")
            finally:
                os.chmod(str(ref_html), 0o644)

    def test_write_design_anchor_is_idempotent_on_rerun(self):
        """Re-running write-design-anchor overwrites with byte-identical content (no crash, no append)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._prep_feature_state(tmp_path)

            design_dir = tmp_path / "design"
            design_dir.mkdir()
            (design_dir / "reference.html").write_text("<html></html>", encoding="utf-8")

            state_path = devforge / "specify-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["design_anchor"] = {
                "kind": "html", "file": "design/reference.html", "selectors": [],
            }
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

            anchor_path = tmp_path / "specs" / "001-test-anchor-feature" / "design-anchor.json"

            r1 = _run(
                ["--devforge-dir", str(devforge), "write-design-anchor",
                 "--workspace-root", str(tmp_path)],
                cwd=tmp_path,
            )
            self.assertEqual(r1.returncode, 0, r1.stderr)
            first = anchor_path.read_text(encoding="utf-8")

            r2 = _run(
                ["--devforge-dir", str(devforge), "write-design-anchor",
                 "--workspace-root", str(tmp_path)],
                cwd=tmp_path,
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)
            second = anchor_path.read_text(encoding="utf-8")

            self.assertEqual(first, second)

    def test_write_design_anchor_requires_spec_number_and_feature_slug(self):
        """No spec_number/feature_slug in state → exit 2, no file written."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(str(tmp_path))
            r = _run(
                ["--devforge-dir", str(devforge), "write-design-anchor",
                 "--workspace-root", str(tmp_path)],
                cwd=tmp_path,
            )
            self.assertEqual(r.returncode, 2)
            self.assertIn("spec_number and feature_slug", r.stderr)

    # ------------------------------------------------------------------
    # Task C — backstop composition from design_source when no anchor was
    # captured at intake.
    # ------------------------------------------------------------------

    def test_write_design_anchor_backstop_composes_from_design_source(self):
        """Empty carried anchor + design_source='html:design/reference.html' → composed {kind, file, selectors:[]} persisted."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._prep_feature_state(tmp_path)

            design_dir = tmp_path / "design"
            design_dir.mkdir()
            ref_html = design_dir / "reference.html"
            ref_html.write_text("<html></html>", encoding="utf-8")

            r_ds = _run([
                "--devforge-dir", str(devforge), "set-design-source",
                "--value", "html:design/reference.html",
            ])
            self.assertEqual(r_ds.returncode, 0, r_ds.stderr)

            # Confirm the carried design_anchor is still the empty default
            # (no import-handoff ran in this test) before the backstop fires.
            state = json.loads((devforge / "specify-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["design_anchor"], {"kind": "", "file": "", "selectors": []})

            r = _run(
                ["--devforge-dir", str(devforge), "write-design-anchor",
                 "--workspace-root", str(tmp_path)],
                cwd=tmp_path,
            )
            self.assertEqual(r.returncode, 0, r.stderr)

            anchor_path = tmp_path / "specs" / "001-test-anchor-feature" / "design-anchor.json"
            persisted = json.loads(anchor_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["kind"], "html")
            self.assertEqual(persisted["file"], "design/reference.html")
            self.assertEqual(persisted["selectors"], [])
            self.assertEqual(
                persisted["source_hash"], hashlib.sha256(ref_html.read_bytes()).hexdigest()
            )

    def test_write_design_anchor_backstop_composes_screenshot_scheme(self):
        """Empty carried anchor + design_source='screenshot:design/mock.png' → composed {kind:"screenshot", file, selectors:[]}, source_hash=='' (hash computed only for html)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._prep_feature_state(tmp_path)

            r_ds = _run([
                "--devforge-dir", str(devforge), "set-design-source",
                "--value", "screenshot:design/mock.png",
            ])
            self.assertEqual(r_ds.returncode, 0, r_ds.stderr)

            # Confirm the carried design_anchor is still the empty default
            # (no import-handoff ran in this test) before the backstop fires.
            state = json.loads((devforge / "specify-state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["design_anchor"], {"kind": "", "file": "", "selectors": []})

            r = _run(
                ["--devforge-dir", str(devforge), "write-design-anchor",
                 "--workspace-root", str(tmp_path)],
                cwd=tmp_path,
            )
            self.assertEqual(r.returncode, 0, r.stderr)

            anchor_path = tmp_path / "specs" / "001-test-anchor-feature" / "design-anchor.json"
            persisted = json.loads(anchor_path.read_text(encoding="utf-8"))
            self.assertEqual(
                persisted,
                {"kind": "screenshot", "file": "design/mock.png", "selectors": [], "source_hash": ""},
            )

    def test_write_design_anchor_both_empty_persists_empty_anchor_no_error(self):
        """No carried anchor AND design_source='none' (default) → empty anchor persisted, exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._prep_feature_state(tmp_path)

            r = _run(
                ["--devforge-dir", str(devforge), "write-design-anchor",
                 "--workspace-root", str(tmp_path)],
                cwd=tmp_path,
            )
            self.assertEqual(r.returncode, 0, r.stderr)

            anchor_path = tmp_path / "specs" / "001-test-anchor-feature" / "design-anchor.json"
            persisted = json.loads(anchor_path.read_text(encoding="utf-8"))
            self.assertEqual(
                persisted, {"kind": "", "file": "", "selectors": [], "source_hash": ""}
            )

    def test_write_design_anchor_carried_anchor_wins_over_design_source(self):
        """Non-empty carried design_anchor takes priority over a differing design_source declaration."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._prep_feature_state(tmp_path)

            r_ds = _run([
                "--devforge-dir", str(devforge), "set-design-source",
                "--value", "figma:https://figma.com/file/should-be-ignored",
            ])
            self.assertEqual(r_ds.returncode, 0, r_ds.stderr)

            state_path = devforge / "specify-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["design_anchor"] = {
                "kind": "html", "file": "design/reference.html", "selectors": [".fooBar"],
            }
            state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")

            r = _run(
                ["--devforge-dir", str(devforge), "write-design-anchor",
                 "--workspace-root", str(tmp_path)],
                cwd=tmp_path,
            )
            self.assertEqual(r.returncode, 0, r.stderr)

            anchor_path = tmp_path / "specs" / "001-test-anchor-feature" / "design-anchor.json"
            persisted = json.loads(anchor_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted["kind"], "html")
            self.assertEqual(persisted["file"], "design/reference.html")
            self.assertEqual(persisted["selectors"], [".fooBar"])


class TestFindHandoffsCrossKind(unittest.TestCase):
    """Tests for specify_helper find-handoffs with both research and discover
    handoffs pending in specs/ at once (68-INTAKE-OWNS-FEATURE-DIR-PLAN.md
    Phase 4 — a single glob pass over both lanes, D5 predicate)."""

    def _make_devforge(self, tmp: str) -> Path:
        d = Path(tmp) / ".devforge"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _run_find(self, devforge: Path):
        return _run(["--devforge-dir", str(devforge), "find-handoffs"])

    def _build_research_handoff_at(self, tmp: Path, research_df: Path, feature_dirname: str) -> Path:
        """Build a research-handoff.json at tmp/specs/<feature_dirname>/."""
        feature_dir = tmp / "specs" / feature_dirname
        handoff_out = feature_dir / "research-handoff.json"
        r = _build_minimal_handoff(research_df, handoff_out)
        if r.returncode != 0:
            raise RuntimeError("finalize-handoff (research) failed: " + r.stderr)
        return handoff_out

    def _build_discover_handoff_at(self, tmp: Path, discover_df: Path, feature_dirname: str) -> Path:
        """Build a discover-handoff.json at tmp/specs/<feature_dirname>/."""
        feature_dir = tmp / "specs" / feature_dirname
        handoff_out = feature_dir / "discover-handoff.json"
        r = _build_minimal_discover_handoff(discover_df, handoff_out)
        if r.returncode != 0:
            raise RuntimeError("finalize-handoff (discover) failed: " + r.stderr)
        return handoff_out

    # ------------------------------------------------------------------

    def test_find_handoffs_globs_both_research_and_discover(self):
        """One research + one discover feature dir -> both appear in one pass."""
        import time
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)

            df_r = tmp_path / "df_r"
            df_r.mkdir()
            df_d = tmp_path / "df_d"
            df_d.mkdir()

            h_research = self._build_research_handoff_at(
                tmp_path, df_r, "001-auth-token-refresh"
            )
            h_discover = self._build_discover_handoff_at(
                tmp_path, df_d, "002-audit-log-persistence"
            )

            now = time.time()
            os.utime(str(h_research), (now - 3600, now - 3600))
            os.utime(str(h_discover), (now - 7200, now - 7200))

            r = self._run_find(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)

            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 2, "Expected 2 hits, got: " + r.stdout)

    def test_find_handoffs_emits_kind_discriminator(self):
        """Output lines contain 'kind=research' and 'kind=discover' tags."""
        import time
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)

            df_r = tmp_path / "df_r"
            df_r.mkdir()
            df_d = tmp_path / "df_d"
            df_d.mkdir()

            h_research = self._build_research_handoff_at(
                tmp_path, df_r, "001-auth-token-refresh"
            )
            h_discover = self._build_discover_handoff_at(
                tmp_path, df_d, "002-audit-log-persistence"
            )

            now = time.time()
            os.utime(str(h_research), (now - 3600, now - 3600))
            os.utime(str(h_discover), (now - 7200, now - 7200))

            r = self._run_find(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)

            kinds = set()
            for line in r.stdout.strip().split("\n"):
                if "kind=research" in line:
                    kinds.add("research")
                if "kind=discover" in line:
                    kinds.add("discover")
            self.assertIn("research", kinds, "No research line: " + r.stdout)
            self.assertIn("discover", kinds, "No discover line: " + r.stdout)

    def test_find_handoffs_research_uses_mode_discriminator_value(self):
        """Research output lines contain 'mode=<mode>'."""
        import time
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)
            df_r = tmp_path / "df_r"
            df_r.mkdir()

            h_research = self._build_research_handoff_at(
                tmp_path, df_r, "001-auth-token-refresh"
            )
            now = time.time()
            os.utime(str(h_research), (now - 3600, now - 3600))

            r = self._run_find(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)

            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 1)
            self.assertIn("mode=", lines[0])
            self.assertIn("kind=research", lines[0])

    def test_find_handoffs_discover_uses_verdict_discriminator_value(self):
        """Discover output lines contain 'verdict=<verdict>'."""
        import time
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)
            df_d = tmp_path / "df_d"
            df_d.mkdir()

            h_discover = self._build_discover_handoff_at(
                tmp_path, df_d, "001-audit-log-persistence"
            )
            now = time.time()
            os.utime(str(h_discover), (now - 3600, now - 3600))

            r = self._run_find(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)

            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 1, "Expected 1 hit, got: " + r.stdout)
            self.assertIn("verdict=", lines[0])
            self.assertIn("kind=discover", lines[0])

    def test_find_handoffs_sorts_newest_first_across_kinds(self):
        """Research (newest) + discover (older) -> research appears first."""
        import time
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)
            df_r = tmp_path / "df_r"
            df_r.mkdir()
            df_d = tmp_path / "df_d"
            df_d.mkdir()

            h_research = self._build_research_handoff_at(
                tmp_path, df_r, "001-auth-token-refresh"
            )
            h_discover = self._build_discover_handoff_at(
                tmp_path, df_d, "002-audit-log-persistence"
            )

            now = time.time()
            # Research is 1hr old (newest); discover is 2hr old (older).
            os.utime(str(h_research), (now - 3600, now - 3600))
            os.utime(str(h_discover), (now - 7200, now - 7200))

            r = self._run_find(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)

            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 2, "Expected 2 hits, got: " + r.stdout)
            # First line should be research (newest).
            self.assertIn("kind=research", lines[0])
            # Second line should be discover (older).
            self.assertIn("kind=discover", lines[1])

    def test_find_handoffs_skips_invalid_discover_silently(self):
        """Invalid discover-handoff.json skipped silently; valid research appears."""
        import time
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)
            df_r = tmp_path / "df_r"
            df_r.mkdir()

            # One valid research handoff.
            h_research = self._build_research_handoff_at(
                tmp_path, df_r, "001-auth-token-refresh"
            )

            # One corrupt discover handoff in a sibling feature dir.
            corrupt_dir = tmp_path / "specs" / "002-corrupt"
            corrupt_dir.mkdir(parents=True)
            corrupt = corrupt_dir / "discover-handoff.json"
            corrupt.write_text("{ not json }", encoding="utf-8")

            now = time.time()
            os.utime(str(h_research), (now - 3600, now - 3600))
            os.utime(str(corrupt), (now - 1800, now - 1800))

            r = self._run_find(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)

            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            # Only the valid research handoff should appear.
            self.assertEqual(len(lines), 1, "Expected 1 hit, got: " + r.stdout)
            self.assertIn("kind=research", lines[0])

    def test_find_handoffs_same_feature_dir_surfaces_both_lanes(self):
        """A single feature dir carrying BOTH research-handoff.json and
        discover-handoff.json (an unusual but not-forbidden state) surfaces
        both hits — cmd_find_handoffs checks each lane independently per
        feature dir, it does not treat them as mutually exclusive."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp)
            df_r = tmp_path / "df_r"
            df_r.mkdir()
            df_d = tmp_path / "df_d"
            df_d.mkdir()

            self._build_research_handoff_at(tmp_path, df_r, "001-hybrid-feature")
            self._build_discover_handoff_at(tmp_path, df_d, "001-hybrid-feature")

            r = self._run_find(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 2, "Expected 2 hits, got: " + r.stdout)
            kinds = {("research" if "kind=research" in l else "discover") for l in lines}
            self.assertEqual(kinds, {"research", "discover"})


# ---------------------------------------------------------------------------
# Dedupe boundary tests — import-handoff dedupe for both discover and research lanes.
# ---------------------------------------------------------------------------

class TestImportHandoffDedupe(unittest.TestCase):
    """Tests for boundary dedupe in specify_helper import-handoff (both lanes).

    Cases:
      (a) clean (no-dup) handoff ingests UNCHANGED — regression anchor.
      (b) duplicate/whitespace-variant handoff lands DEDUPED — per-bucket,
          first-occurrence values preserved, relative order preserved, and a
          same-content constraint with DIFFERENT kind is NOT merged.
      (c) re-importing either handoff a second time is a state NO-OP — the
          four buckets are byte-identical to after the first import.
    Also verifies per-entry stderr drop lines are emitted for case (b).
    Unit-test for the shared _dedupe_seeds helper directly (research lane coverage
    without building a full research handoff round-trip).
    """

    def _make_devforge(self, tmp_path: Path) -> Path:
        d = tmp_path / ".devforge"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _run_import(self, devforge: Path, handoff_path: Path):
        return _run([
            "--devforge-dir", str(devforge),
            "import-handoff",
            "--handoff-path", str(handoff_path),
        ])

    def _build_discover_handoff(self, tmp_path: Path) -> Path:
        """Build a real discover handoff via the real producer (no hand-authored fixtures)."""
        devforge_d = tmp_path / "discover_df"
        devforge_d.mkdir(exist_ok=True)
        discover_dir = tmp_path / "discover"
        discover_dir.mkdir(exist_ok=True)
        handoff_out = discover_dir / "2026-05-20-audit-log-persistence.handoff.json"
        r = _build_minimal_discover_handoff(devforge_d, handoff_out)
        if r.returncode != 0:
            raise RuntimeError(
                "_build_minimal_discover_handoff failed: " + r.stderr
            )
        return handoff_out

    def _read_seed_buckets(self, devforge: Path) -> dict:
        """Return the four seed buckets from specify-state.json as a plain dict."""
        state = json.loads(
            (devforge / "specify-state.json").read_text(encoding="utf-8")
        )
        return {
            "constraints": state["constraints"],
            "affected_areas": state["affected_areas"],
            "risks": state["risks"],
            "open_questions": state["open_questions"],
        }

    # ------------------------------------------------------------------
    # Case (a): clean (no-dup) discover handoff ingests UNCHANGED.
    # ------------------------------------------------------------------

    def test_dedupe_case_a_clean_handoff_unchanged(self):
        """(a) A clean handoff (no dups) ingests byte-identical to a non-deduped run.

        Regression anchor: the dedupe step must be a no-op on well-formed input.
        Asserts that each bucket contains exactly the entries the real producer
        emitted — no items dropped.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp_path)
            handoff_out = self._build_discover_handoff(tmp_path)

            # Read the producer output to know ground-truth counts.
            data = json.loads(handoff_out.read_text(encoding="utf-8"))
            seeds = data["spec_seeds"]
            expected_constraints = len(seeds["constraints"])
            expected_areas = len(seeds["affected_areas"])
            expected_risks = len(seeds["risks"])
            expected_oqs = len(seeds["open_questions"])

            r = self._run_import(devforge, handoff_out)
            self.assertEqual(r.returncode, 0, "import failed: " + r.stderr)

            # No drop lines should appear on stderr (clean input).
            self.assertNotIn("dedupe", r.stderr, "unexpected dedupe drop on clean input")

            buckets = self._read_seed_buckets(devforge)
            self.assertEqual(len(buckets["constraints"]), expected_constraints,
                             "constraints count changed on clean input")
            self.assertEqual(len(buckets["affected_areas"]), expected_areas,
                             "affected_areas count changed on clean input")
            self.assertEqual(len(buckets["risks"]), expected_risks,
                             "risks count changed on clean input")
            self.assertEqual(len(buckets["open_questions"]), expected_oqs,
                             "open_questions count changed on clean input")

    # ------------------------------------------------------------------
    # Case (b): duplicate + whitespace-variant handoff lands DEDUPED.
    # ------------------------------------------------------------------

    def test_dedupe_case_b_dedupes_all_four_buckets(self):
        """(b) Duplicate/whitespace-variant entries land deduped; same-content different-kind NOT merged.

        Injects:
        - duplicate constraint (exact copy of first constraint) — should drop to 1
        - whitespace-variant constraint (extra trailing space) — same kind/content → drop
        - same-content DIFFERENT-kind constraint — must survive (NOT a dup)
        - duplicate affected_area (exact area name) — drop to 1
        - whitespace-variant risk (internal whitespace added) — drop to 1
        - duplicate open_question — drop to 1
        Asserts: each bucket has the correct distinct count; first-occurrence
        value preserved (not the whitespace variant); order preserved; stderr
        contains per-entry drop lines naming section and surviving key.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp_path)
            handoff_out = self._build_discover_handoff(tmp_path)

            data = json.loads(handoff_out.read_text(encoding="utf-8"))
            seeds = data["spec_seeds"]

            # --- Patch spec_seeds to inject duplicates ---

            # Constraint: use first constraint as base, add two duplicates + one different-kind.
            # The producer emits 2 nfr constraints; we'll take the first and create dups.
            orig_c0 = seeds["constraints"][0]  # e.g. kind=nfr, content="100ms p99 write latency"
            c_exact_dup = dict(orig_c0)  # exact duplicate
            # whitespace variant: trailing space on content
            c_ws_variant = dict(orig_c0, content=orig_c0["content"] + " ")
            # different kind — same content, kind=constitution_anchor; requires constitution_ref
            # Use kind=follow (not in discover schema). Actually discover schema has nfr/constitution_anchor/external_system.
            # Use constitution_anchor with a constitution_ref — same content, different kind.
            c_diff_kind = {
                "kind": "constitution_anchor",
                "content": orig_c0["content"],
                "quantifier": None,
                "constitution_ref": "§3.1 Example",
                "protocol": None,
                "contract_doc_ref": None,
            }
            seeds["constraints"] = [
                orig_c0,          # survivor 1
                c_exact_dup,      # exact dup → drop
                c_ws_variant,     # ws-variant dup → drop
                c_diff_kind,      # different kind → survivor 2
            ]
            self.assertEqual(len(seeds["constraints"]), 4,
                             "pre-import: expected 4 injected constraints (3 nfr dups + 1 different-kind)")

            # Affected area: use the only area, add exact dup and ws-variant.
            orig_a0 = seeds["affected_areas"][0]
            a_exact_dup = dict(orig_a0)
            a_ws_variant = dict(orig_a0, area="  " + orig_a0["area"] + "  ")
            seeds["affected_areas"] = [
                orig_a0,        # survivor
                a_exact_dup,    # exact dup → drop
                a_ws_variant,   # ws-variant → drop
            ]
            self.assertEqual(len(seeds["affected_areas"]), 3,
                             "pre-import: expected 3 injected affected_areas")

            # Risk: use first risk, add one with internal whitespace variation.
            orig_r0 = seeds["risks"][0]
            # Insert an extra space inside the risk text
            risk_text_parts = orig_r0["risk"].split(" ", 1)
            if len(risk_text_parts) == 2:
                r_ws_variant = dict(orig_r0,
                                    risk=risk_text_parts[0] + "  " + risk_text_parts[1])
            else:
                r_ws_variant = dict(orig_r0, risk=orig_r0["risk"] + "  ")
            seeds["risks"] = [
                orig_r0,        # survivor
                r_ws_variant,   # ws-variant dup → drop
            ]
            self.assertEqual(len(seeds["risks"]), 2,
                             "pre-import: expected 2 injected risks (1 original + 1 ws-variant)")

            # Open questions: add two identical questions.
            q_text = "Should we index the audit table?"
            seeds["open_questions"] = [
                {"question": q_text, "blocking": False},
                {"question": q_text, "blocking": False},   # exact dup → drop
                {"question": q_text + " ", "blocking": False},  # ws-variant → drop
            ]
            self.assertEqual(len(seeds["open_questions"]), 3,
                             "pre-import: expected 3 injected open_questions")

            handoff_out.write_text(json.dumps(data, indent=2), encoding="utf-8")

            r = self._run_import(devforge, handoff_out)
            self.assertEqual(r.returncode, 0, "import with dups failed: " + r.stderr)

            # --- Assert stderr drop lines ---
            stderr = r.stderr
            # Expect at least one drop line per section that had dups.
            self.assertIn("dedupe constraints", stderr,
                          "expected constraint drop lines in stderr")
            self.assertIn("dedupe affected_areas", stderr,
                          "expected affected_area drop lines in stderr")
            self.assertIn("dedupe risks", stderr,
                          "expected risk drop lines in stderr")
            self.assertIn("dedupe open_questions", stderr,
                          "expected open_question drop lines in stderr")
            # Each drop line must contain "collapsed into surviving".
            for line in stderr.splitlines():
                if "dedupe" in line:
                    self.assertIn("collapsed into surviving", line,
                                  "drop line missing 'collapsed into surviving': " + line)

            buckets = self._read_seed_buckets(devforge)

            # Constraints: orig_c0 + c_diff_kind survive (exact + ws-variant dropped).
            self.assertEqual(len(buckets["constraints"]), 2,
                             "expected 2 distinct constraints (1 nfr + 1 constitution_anchor)")
            surviving_kinds = {c["kind"] for c in buckets["constraints"]}
            self.assertEqual(surviving_kinds, {"nfr", "constitution_anchor"},
                             "different-kind constraint must survive")

            # First occurrence value preserved (NOT the whitespace variant).
            nfr_survivors = [c for c in buckets["constraints"] if c["kind"] == "nfr"]
            self.assertEqual(len(nfr_survivors), 1)
            self.assertEqual(nfr_survivors[0]["content"], orig_c0["content"],
                             "first-occurrence value must be preserved, not ws-variant")

            # Affected areas: 1 survivor (exact + ws-variant dropped).
            self.assertEqual(len(buckets["affected_areas"]), 1,
                             "expected 1 distinct affected_area")
            self.assertEqual(buckets["affected_areas"][0]["area"], orig_a0["area"],
                             "first-occurrence area value must be preserved")

            # Risks: 1 survivor (ws-variant dropped).
            self.assertEqual(len(buckets["risks"]), 1,
                             "expected 1 distinct risk")
            self.assertEqual(buckets["risks"][0]["risk"], orig_r0["risk"],
                             "first-occurrence risk value must be preserved")

            # Open questions: 1 survivor (exact dup + ws-variant dropped).
            self.assertEqual(len(buckets["open_questions"]), 1,
                             "expected 1 distinct open_question")
            # question_id must be gap-free (hq-1, not hq-2 or hq-3).
            self.assertEqual(buckets["open_questions"][0]["question_id"], "hq-1",
                             "open_question_id must be gap-free after dedupe")

    # ------------------------------------------------------------------
    # Case (c): re-import is a state NO-OP.
    # ------------------------------------------------------------------

    def test_dedupe_case_c_reimport_is_noop(self):
        """(c) Re-importing a handoff a second time leaves the four buckets byte-identical.

        Verifies idempotency: the second import overwrites with the same data so
        the parsed JSON buckets before and after are identical.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp_path)
            handoff_out = self._build_discover_handoff(tmp_path)

            # Inject a duplicate to make dedupe fire on both imports.
            data = json.loads(handoff_out.read_text(encoding="utf-8"))
            seeds = data["spec_seeds"]
            if seeds["constraints"]:
                orig_c = seeds["constraints"][0]
                seeds["constraints"].append(dict(orig_c))  # duplicate
            handoff_out.write_text(json.dumps(data, indent=2), encoding="utf-8")

            # First import.
            r1 = self._run_import(devforge, handoff_out)
            self.assertEqual(r1.returncode, 0, "first import failed: " + r1.stderr)
            buckets_after_first = self._read_seed_buckets(devforge)

            # Second import (re-import same handoff).
            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, "second import failed: " + r2.stderr)
            buckets_after_second = self._read_seed_buckets(devforge)

            # Buckets must be byte-identical (same JSON content).
            self.assertEqual(
                json.dumps(buckets_after_first, sort_keys=True),
                json.dumps(buckets_after_second, sort_keys=True),
                "re-import must be a NO-OP — buckets differ after second import",
            )

    # ------------------------------------------------------------------
    # Unit test: _dedupe_seeds helper directly (research lane coverage).
    # ------------------------------------------------------------------

    def test_dedupe_seeds_unit_research_lane(self):
        """Unit test of _dedupe_seeds via research-schema dataclass instances.

        Exercises the shared helper on hand-built research.handoff_schema
        objects — avoids the cost of a full research handoff round-trip while
        still covering the research-schema types (Constraint / AffectedArea /
        Risk / OpenQuestion from _research.handoff_schema).
        """
        import sys
        sys.path.insert(0, str(ROOT / "src" / "devforge" / "lib"))
        from _research import handoff_schema as rhs
        from _specify._cmds_handoff import (
            _dedupe_seeds,
            _constraint_key,
            _affected_area_key,
            _risk_key,
            _open_question_key,
        )

        # --- Constraint dedupe (research schema uses "follow" and "nfr" kinds) ---
        c1 = rhs.Constraint(kind="nfr", content="Latency < 100ms", quantifier="p99")
        c2_exact = rhs.Constraint(kind="nfr", content="Latency < 100ms", quantifier="p99")
        c2_ws = rhs.Constraint(kind="nfr", content="Latency  <  100ms", quantifier="p99")
        # Different kind: same content — must NOT be merged.
        c3_follow = rhs.Constraint(kind="follow", content="Latency < 100ms")

        result_c = _dedupe_seeds(
            [c1, c2_exact, c2_ws, c3_follow],
            _constraint_key, "constraints"
        )
        self.assertEqual(len(result_c), 2,
                         "expected 2 survivors (nfr + follow, not 4 or 1)")
        self.assertIs(result_c[0], c1, "first-occurrence object must survive")
        self.assertIs(result_c[1], c3_follow, "different-kind constraint must survive")

        # --- AffectedArea dedupe (research schema: no is_internal_extension_candidate) ---
        a1 = rhs.AffectedArea(area="services/auth", files=["auth.py:10"], impact="Major")
        a2_exact = rhs.AffectedArea(area="services/auth", files=["auth.py:20"], impact="Minor")
        a3_ws = rhs.AffectedArea(area="  services/auth  ", files=[], impact="None")

        result_a = _dedupe_seeds(
            [a1, a2_exact, a3_ws],
            _affected_area_key, "affected_areas"
        )
        self.assertEqual(len(result_a), 1, "expected 1 survivor for affected_areas")
        self.assertIs(result_a[0], a1, "first-occurrence object must survive")

        # --- Risk dedupe ---
        r1 = rhs.Risk(risk="DB migration fails",
                      likelihood="Med", impact="High", mitigation="test in staging")
        r2_ws = rhs.Risk(risk="DB  migration  fails",
                         likelihood="Low", impact="Low", mitigation="different")

        result_r = _dedupe_seeds(
            [r1, r2_ws],
            _risk_key, "risks"
        )
        self.assertEqual(len(result_r), 1, "expected 1 survivor for risks")
        self.assertIs(result_r[0], r1, "first-occurrence object must survive")

        # --- OpenQuestion dedupe ---
        q1 = rhs.OpenQuestion(question="Is the token idempotent?", blocking=True)
        q2_exact = rhs.OpenQuestion(question="Is the token idempotent?", blocking=False)
        q3_ws = rhs.OpenQuestion(question=" Is the token idempotent? ", blocking=False)

        result_q = _dedupe_seeds(
            [q1, q2_exact, q3_ws],
            _open_question_key, "open_questions"
        )
        self.assertEqual(len(result_q), 1, "expected 1 survivor for open_questions")
        self.assertIs(result_q[0], q1, "first-occurrence object must survive")

        # --- Empty list is a no-op ---
        result_empty = _dedupe_seeds([], _constraint_key, "constraints")
        self.assertEqual(result_empty, [])

        # --- No duplicates: output equals input ---
        c_distinct = rhs.Constraint(kind="follow", content="Auth must be deterministic")
        result_nodups = _dedupe_seeds([c1, c_distinct], _constraint_key, "constraints")
        self.assertEqual(len(result_nodups), 2)
        self.assertIs(result_nodups[0], c1)
        self.assertIs(result_nodups[1], c_distinct)

    def test_dedupe_case_b_stderr_names_section_and_keys(self):
        """(b) Stderr drop lines are per-entry, naming section + surviving key + dropped key.

        Complementary to test_dedupe_case_b_dedupes_all_four_buckets:
        focuses specifically on the stderr output shape (not just 'dedupe' in stderr).
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._make_devforge(tmp_path)
            handoff_out = self._build_discover_handoff(tmp_path)

            data = json.loads(handoff_out.read_text(encoding="utf-8"))
            seeds = data["spec_seeds"]
            orig_constraint_count = len(seeds["constraints"])

            # Add one exact duplicate constraint.
            if seeds["constraints"]:
                seeds["constraints"].append(dict(seeds["constraints"][0]))
            self.assertEqual(len(seeds["constraints"]), orig_constraint_count + 1,
                             "pre-import: constraint injection should have added one dup")

            # Add one whitespace-variant open question.
            q_raw = "Test question alpha"
            q_ws_variant = " Test question alpha "  # leading + trailing space
            seeds["open_questions"] = [
                {"question": q_raw, "blocking": False},
                {"question": q_ws_variant, "blocking": False},  # ws-variant dup
            ]
            self.assertEqual(len(seeds["open_questions"]), 2,
                             "pre-import: expected 2 open_questions (1 original + 1 ws-variant)")

            handoff_out.write_text(json.dumps(data, indent=2), encoding="utf-8")

            r = self._run_import(devforge, handoff_out)
            self.assertEqual(r.returncode, 0, "import failed: " + r.stderr)

            drop_lines = [
                line for line in r.stderr.splitlines() if "dedupe" in line
            ]
            self.assertGreater(len(drop_lines), 0,
                               "expected at least one dedupe drop line")

            for line in drop_lines:
                # Must name the section.
                self.assertTrue(
                    any(sec in line for sec in
                        ("constraints", "affected_areas", "risks", "open_questions")),
                    "drop line must name section: " + line,
                )
                # Must name the surviving key.
                self.assertIn("collapsed into surviving", line,
                              "drop line must name surviving key: " + line)
                # Must name the dropped key.
                self.assertIn("dropped", line,
                              "drop line must name dropped key: " + line)

            # For the whitespace-variant open_question drop, the logged dropped text
            # must DIFFER from the logged surviving text — proving raw field values
            # are logged, not the normalized key (which would be identical for both).
            oq_drop_lines = [
                line for line in r.stderr.splitlines()
                if "dedupe open_questions" in line
            ]
            self.assertEqual(len(oq_drop_lines), 1,
                             "expected exactly 1 open_questions drop line")
            oq_line = oq_drop_lines[0]
            # Extract the dropped and surviving repr sections.
            # Line shape: "... dropped <repr> → collapsed into surviving <repr>"
            dropped_part = oq_line.split("→ collapsed into surviving")[0]
            surviving_part = oq_line.split("→ collapsed into surviving")[1]
            # The raw variant text has whitespace; the raw original does not.
            # They must differ in the log — if they were identical, the log is useless.
            self.assertNotEqual(
                dropped_part.strip(), surviving_part.strip(),
                "dropped and surviving repr must differ for a whitespace-variant dup; "
                "got identical text — raw field values are not being logged: " + oq_line,
            )


# ---------------------------------------------------------------------------
# Plan 73 D7 — evidence_lanes read-path back-compat (import-handoff consumes
# a Handoff carrying the new top-level field via _dict_to_dataclass — the
# SAME reconstruction call site the design_anchor back-compat tests above
# exercise).
# ---------------------------------------------------------------------------


class TestImportHandoffEvidenceLanes(unittest.TestCase):
    """import-handoff tolerates evidence_lanes present, and absent (pre-plan-73-D7 shape)."""

    def _make_devforge(self, tmp: str) -> Path:
        """Create a minimal .devforge dir inside tmp (mirrors TestImportHandoff)."""
        d = Path(tmp) / ".devforge"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _run_import(self, devforge: Path, handoff_path: Path, extra: list = None):
        argv = [
            "--devforge-dir", str(devforge),
            "import-handoff",
            "--handoff-path", str(handoff_path),
        ]
        if extra:
            argv += extra
        return _run(argv)

    def test_import_handoff_current_shape_round_trips(self):
        """A freshly-produced handoff.json (evidence_lanes present, all-False
        default since the fixture builder never calls set-evidence-lanes)
        imports cleanly via the real read path.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_df"
            research_df.mkdir()
            handoff_out = Path(tmp) / "handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(handoff_out.read_text(encoding="utf-8"))
            self.assertIn("evidence_lanes", data)
            self.assertEqual(data["evidence_lanes"], {
                "static_graph": False,
                "text_search": False,
                "runtime_probe": False,
                "history": False,
            })

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertIn("imported:", r2.stdout)

    def test_import_handoff_backcompat_missing_evidence_lanes_key(self):
        """Real handoff.json with the top-level evidence_lanes key deleted
        entirely (the pre-plan-73-D7 shape) -> still imports cleanly through
        the real _dict_to_dataclass read path (same call site the
        design_anchor back-compat test above exercises) -- axis (a) of
        Build discipline's back-compat proof, at the actual consumer read
        site, not just the schema constructor.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._make_devforge(tmp)
            research_df = Path(tmp) / "research_df"
            research_df.mkdir()
            handoff_out = Path(tmp) / "handoff.json"

            r = _build_minimal_handoff(research_df, handoff_out)
            self.assertEqual(r.returncode, 0, r.stderr)

            data = json.loads(handoff_out.read_text(encoding="utf-8"))
            del data["evidence_lanes"]
            handoff_out.write_text(json.dumps(data, indent=2), encoding="utf-8")

            r2 = self._run_import(devforge, handoff_out)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertIn("imported:", r2.stdout)


if __name__ == "__main__":
    unittest.main()
