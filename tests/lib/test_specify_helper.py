"""Tests for src/devforge/lib/specify_helper.py.

Coverage matrix (Step 2 schemas + Step 3 Phase 0/1/1.5/2/3 subcommands +
cross-phase summary). Phase 4-5 subcommands ship next session per
SPECIFY-REDESIGN-PLAN.md.

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


if __name__ == "__main__":
    unittest.main()
