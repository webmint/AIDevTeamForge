"""Tests for src/devforge/lib/specify_helper.py.

Coverage matrix (Step 2 schemas + Step 3 Phase 0/1/1.5 subcommands).
Phase 2-5 subcommands ship next session per SPECIFY-REDESIGN-PLAN.md.

Subprocess pattern: each test runs in its own tempfile.TemporaryDirectory.
Real subcommands (subprocess) produce fixture state — no hand-fabricated
JSON. Mirrors test_discover_helper / test_research_helper discipline.
"""
from __future__ import annotations

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
            ("follow", "not_break", "use"),
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
            specify_helper.CONSTITUTION_POPULATE_GUARD,
            "_Run /constitute to populate_",
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


if __name__ == "__main__":
    unittest.main()
