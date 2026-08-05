"""Tests for src/devforge/lib/research_helper.py.

Coverage matrix
---------------

  Schemas / plumbing
    default_memo_state + default_report_state — locked top-level shape, defaults.
    reset-memo + reset-report — write JSON; idempotent byte-identical.
    read-memo + read-report — defaults when missing; round-trip after setters.
    _state_transaction — fcntl lock; body raise → write skipped.

  Validation
    _validate_scalar — empty rejected, stripped.
    _validate_enum — case-insensitive → canonical; allowed enumerated on error.
    _validate_string_array_json — JSON array; empty / non-string / malformed rejected.
    _validate_verbatim — all-whitespace rejected; internal whitespace preserved.
    derive_topic_slug — kebab-case + word-truncation; fallback for empty/non-alnum.
    detect_mode_from_symptom — bug tokens, enhancement tokens, mixed → None, empty → None.
    detect_direct_conflicts — alphabetical vs numeric, async vs sync, ascending vs
      descending (both directions), latency budget contradiction; no false positives
      when only one dim populated.

  Preflight
    Missing all → exit 2 with BLOCKED message listing all 4 + producer.
    All present + non-empty → exit 0.
    Any single empty file → exit 2.

  Phase 0 setters
    All 6 dimension setters — value persisted; state explicit; turn counter
      increments only when --increment-turn; bounded-turn cap stamps Partial
      after TURN_CAP (2) without explicit Clear.
    set-symptom auto-derives memo.topic_slug.
    detect-mode persists memo.mode; --override forces a value; ambiguous
      returns null + source="ambiguous"; auto returns "bug" / "enhancement".
    record-gap appends + flips dim to Partial.
    check-conflicts emits JSON list; idempotent on description text; only
      open conflicts surfaced.
    record-conflict-resolution mutates resolution; --rewrite-dimension clears
      the loser dim; out-of-range index → exit 2.
    symptom-coverage emits state map + counts.
    symptom-finalize — all Clear → exit 0; blocked conflict → exit 2 even
      with --accept-gaps; Partial/Missing without --accept-gaps → exit 2;
      with --accept-gaps + no blocked → exit 0 with override_recorded=true.

  Phase 1 setters
    record-finding appends.
    record-hypothesis appends with runtime_probe_needed bool; enforces
      verify-time minimum 2.
    set-root-cause-hypothesis / set-confidence — confidence enum rejected
      on bad value.
    set-trigger / set-root-cause-systemic — populate structured_root_cause
      record on demand.
    record-contributing-factor — appends; rejects 4th entry.
    set-verify-step — 3 sub-fields populated; empty sub-field rejected.

  Phase 2 setters
    set-approach — appends with full payload; complexity enum enforced.
    set-recommended-approach — rejects name not in approaches; persists
      both addressed + not-covered arrays.
    set-constitution-constraints — appends record.
    set-complexity — 6-tuple populated.
    set-verdict — mode-aware; rejects values outside mode's allowed set;
      rejects when memo.mode unset.
    set-next-step-text — emits only when verdict ∈ proceeding-set;
      omits otherwise.

  Render + verify (full round-trip)
    Bug-mode fixture — build via setters, render, byte-compare against
      tests/lib/fixtures/research-sample-bug-report.md.
    Enhancement-mode fixture — same, against research-sample-enhancement-report.md.
    verify — happy bug path → exit 0; 1 hypothesis → exit 2;
      verdict outside mode → exit 2; unchanged_behavior violation → exit 2;
      verify-step missing when runtime probe needed → exit 2;
      structured_root_cause missing for bug+confirmed → exit 2;
      enhancement mode skips structured-root-cause check.

Subprocess pattern: each test runs in its own tempfile.TemporaryDirectory.
Stdlib only. Python 3.8+.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "research_helper.py"
_FIXTURES_DIR = _REPO_ROOT / "tests" / "lib" / "fixtures"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import research_helper  # noqa: E402


def _run(argv, cwd=None):
    """Run research_helper.py with argv; capture stdout/stderr/exit."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(argv),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# Schemas + plumbing.
# ---------------------------------------------------------------------------


class TestSchemas(unittest.TestCase):
    def test_default_memo_state_shape(self):
        memo = research_helper.default_memo_state()
        self.assertIsNone(memo["mode"])
        self.assertIsNone(memo["topic_slug"])
        self.assertEqual(memo["gaps"], [])
        self.assertEqual(memo["conflicts"], [])
        self.assertFalse(memo["override_recorded"])
        self.assertEqual(
            sorted(memo["dimensions"].keys()),
            sorted(research_helper.RUBRIC_DIMENSIONS),
        )
        for d in research_helper.RUBRIC_DIMENSIONS:
            rec = memo["dimensions"][d]
            self.assertIsNone(rec["value"])
            self.assertEqual(rec["state"], "Missing")
            self.assertEqual(rec["turns"], 0)

    def test_default_report_state_shape(self):
        rep = research_helper.default_report_state()
        for field in (
            "topic", "date", "mode", "summary", "root_cause_hypothesis",
            "confidence", "structured_root_cause", "verify_step",
            "recommended_approach", "complexity", "verdict", "next_step_text",
            # Phase 2.3b field
            "runner_up_framing",
            # Patch 6 field
            "data_flow_chain",
        ):
            self.assertIsNone(rep[field], "field {0} default".format(field))
        for arr_field in (
            "findings", "hypotheses", "approaches",
            "constitution_constraints", "open_uncertainties",
            # Phase 2.4c fields
            "fix_path_helpers", "inbound_callers", "dead_siblings",
            "consumer_chain", "value_semantics",
            # Patch 5 anchor-gate rejection log
            "helper_rejection_log",
            # Patch 7 value production sites
            "value_production_sites",
            # Patch 8 literal archaeology
            "literal_archaeology",
            # Step 5 probe scripts
            "probe_scripts",
        ):
            self.assertEqual(rep[arr_field], [], "field {0} default".format(arr_field))
        self.assertEqual(
            sorted(rep["symptom_snapshot"].keys()),
            sorted(research_helper.RUBRIC_DIMENSIONS),
        )

    def test_rubric_dimensions_locked_order(self):
        self.assertEqual(
            research_helper.RUBRIC_DIMENSIONS,
            (
                "symptom",
                "affected_area",
                "repro_or_current",
                "desired",
                "scope",
                "unchanged_behavior",
            ),
        )

    def test_verdict_enum_mode_keys(self):
        self.assertEqual(
            sorted(research_helper.VERDICT_ENUM.keys()),
            ["bug", "enhancement"],
        )
        self.assertIn("Root cause confirmed", research_helper.VERDICT_ENUM["bug"])
        self.assertIn("Feasible", research_helper.VERDICT_ENUM["enhancement"])

    def test_reset_memo_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "reset-memo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads((devforge / "research-state.json").read_text())
            self.assertEqual(data, research_helper.default_memo_state())

    def test_reset_report_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "reset-report"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads((devforge / "research-report.json").read_text())
            self.assertEqual(data, research_helper.default_report_state())

    def test_reset_idempotent_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            first = (devforge / "research-state.json").read_bytes()
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            second = (devforge / "research-state.json").read_bytes()
            self.assertEqual(first, second)

    def test_read_memo_defaults_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = _run(["--devforge-dir", str(Path(tmp) / ".devforge"), "read-memo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout), research_helper.default_memo_state())

    def test_read_report_defaults_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = _run(["--devforge-dir", str(Path(tmp) / ".devforge"), "read-report"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(r.stdout), research_helper.default_report_state())


# ---------------------------------------------------------------------------
# Validation helpers.
# ---------------------------------------------------------------------------


class TestValidation(unittest.TestCase):
    def test_validate_scalar_strips_and_rejects_empty(self):
        self.assertEqual(research_helper._validate_scalar("  x  ", "f"), "x")
        with self.assertRaises(ValueError):
            research_helper._validate_scalar("   ", "f")

    def test_validate_enum_case_insensitive_canonical(self):
        out = research_helper._validate_enum("BUG", "mode", research_helper.MODE_ENUM)
        self.assertEqual(out, "bug")
        with self.assertRaises(ValueError) as ctx:
            research_helper._validate_enum("typo", "mode", research_helper.MODE_ENUM)
        self.assertIn("allowed", str(ctx.exception))

    def test_validate_string_array_json(self):
        self.assertEqual(
            research_helper._validate_string_array_json('["a", "b"]', "f"),
            ["a", "b"],
        )
        # Empty array is allowed at validator layer — callers enforce
        # non-emptiness where required (e.g., set-recommended-approach
        # hypotheses_addressed).
        self.assertEqual(
            research_helper._validate_string_array_json('[]', "f"),
            [],
        )
        with self.assertRaises(ValueError):
            research_helper._validate_string_array_json('["a", ""]', "f")
        with self.assertRaises(ValueError):
            research_helper._validate_string_array_json('[1, 2]', "f")
        with self.assertRaises(ValueError):
            research_helper._validate_string_array_json('not json', "f")

    def test_validate_verbatim_preserves_internal(self):
        self.assertEqual(
            research_helper._validate_verbatim("line1\nline2\n", "f"),
            "line1\nline2\n",
        )
        with self.assertRaises(ValueError):
            research_helper._validate_verbatim("    \t\n  ", "f")

    def test_derive_topic_slug_kebab_truncate(self):
        self.assertEqual(
            research_helper.derive_topic_slug("Items not sorted in admin products view"),
            "items-not-sorted-in",
        )
        self.assertEqual(research_helper.derive_topic_slug("foo-bar"), "foo-bar")
        self.assertEqual(research_helper.derive_topic_slug("   "), "topic")
        self.assertEqual(research_helper.derive_topic_slug("!!!"), "topic")
        self.assertEqual(
            research_helper.derive_topic_slug("Caching strategy for API responses"),
            "caching-strategy-for-api",
        )


class TestModeDetection(unittest.TestCase):
    def test_bug_token_hits(self):
        for txt in (
            "login fails on Safari",
            "the page is broken after deploy",
            "wrong total in cart",
            "auth token missing on refresh",
            "service crashes on cold start",
            "regress on Mac",
            "page freezes when scrolling",
            "the form is stuck",
        ):
            with self.subTest(txt=txt):
                self.assertEqual(
                    research_helper.detect_mode_from_symptom(txt), "bug",
                    "expected bug for {0!r}".format(txt),
                )

    def test_enhancement_token_hits(self):
        for txt in (
            "export should be faster on large datasets",
            "add WebSocket support",
            "optimize the export pipeline",
            "we should integrate with Stripe",
            "improve dashboard responsiveness",
        ):
            with self.subTest(txt=txt):
                self.assertEqual(
                    research_helper.detect_mode_from_symptom(txt), "enhancement",
                    "expected enhancement for {0!r}".format(txt),
                )

    def test_mixed_signal_returns_none(self):
        self.assertIsNone(
            research_helper.detect_mode_from_symptom(
                "we should add Redis but the current cache fails on cold start"
            )
        )

    def test_empty_returns_none(self):
        self.assertIsNone(research_helper.detect_mode_from_symptom(""))
        self.assertIsNone(research_helper.detect_mode_from_symptom("xyz"))


class TestConflictDetection(unittest.TestCase):
    def _memo_with(self, desired, unchanged):
        memo = research_helper.default_memo_state()
        memo["dimensions"]["desired"]["value"] = desired
        memo["dimensions"]["unchanged_behavior"]["value"] = unchanged
        return memo

    def test_alphabetical_vs_numeric(self):
        memo = self._memo_with(
            "alphabetical sort by name A->Z",
            "current numeric order must remain",
        )
        out = research_helper.detect_direct_conflicts(memo)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["type"], "direct")
        self.assertEqual(out[0]["resolution"], "blocked-pending-user")

    def test_async_vs_sync(self):
        memo = self._memo_with(
            "make export async with progress",
            "existing synchronous exports must still complete in 2s",
        )
        self.assertEqual(len(research_helper.detect_direct_conflicts(memo)), 1)

    def test_ascending_vs_descending(self):
        memo = self._memo_with(
            "sort ascending by created_at",
            "current descending order must remain in dashboard",
        )
        out = research_helper.detect_direct_conflicts(memo)
        self.assertGreaterEqual(len(out), 1)

    def test_no_conflict_when_only_one_dim_populated(self):
        memo = self._memo_with("alphabetical sort by name", "")
        self.assertEqual(research_helper.detect_direct_conflicts(memo), [])

    def test_no_conflict_on_unrelated_text(self):
        memo = self._memo_with(
            "fix the login flow",
            "the dashboard render must keep working",
        )
        self.assertEqual(research_helper.detect_direct_conflicts(memo), [])


# ---------------------------------------------------------------------------
# Preflight.
# ---------------------------------------------------------------------------


class TestPreflight(unittest.TestCase):
    def _populate(self, root, paths):
        for rel in paths:
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("x\n")

    def test_all_missing_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = _run(
                [
                    "--devforge-dir", str(Path(tmp) / ".devforge"),
                    "--install-root", tmp,
                    "preflight",
                ]
            )
            self.assertEqual(r.returncode, 2)
            self.assertIn("BLOCKED", r.stderr)
            for rel, producer in research_helper.PREFLIGHT_PREREQS:
                self.assertIn(rel, r.stderr)
                self.assertIn(producer, r.stderr)

    def test_all_present_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._populate(root, [rel for rel, _ in research_helper.PREFLIGHT_PREREQS])
            r = _run(
                [
                    "--devforge-dir", str(root / ".devforge"),
                    "--install-root", tmp,
                    "preflight",
                ]
            )
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_empty_file_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._populate(root, [rel for rel, _ in research_helper.PREFLIGHT_PREREQS])
            (root / "docs" / "architecture.md").write_text("")
            r = _run(
                [
                    "--devforge-dir", str(root / ".devforge"),
                    "--install-root", tmp,
                    "preflight",
                ]
            )
            self.assertEqual(r.returncode, 2)
            self.assertIn("docs/architecture.md", r.stderr)


# ---------------------------------------------------------------------------
# Phase 0 setters.
# ---------------------------------------------------------------------------


class TestPhase0Setters(unittest.TestCase):
    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset-memo"])
        return tmp, devforge

    def _read_memo(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "read-memo"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_set_each_dimension_persists(self):
        tmp, devforge = self._fresh()
        try:
            for d in research_helper.RUBRIC_DIMENSIONS:
                sub = "set-" + d.replace("_", "-")
                r = _run([
                    "--devforge-dir", str(devforge), sub,
                    "--value", "v for {0}".format(d),
                    "--state", "Clear",
                ])
                self.assertEqual(r.returncode, 0, r.stderr)
            memo = self._read_memo(devforge)
            for d in research_helper.RUBRIC_DIMENSIONS:
                self.assertEqual(memo["dimensions"][d]["value"], "v for {0}".format(d))
                self.assertEqual(memo["dimensions"][d]["state"], "Clear")
        finally:
            tmp.cleanup()

    def test_set_symptom_auto_derives_slug(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-symptom",
                "--value", "Caching strategy for API responses",
                "--state", "Clear",
            ])
            memo = self._read_memo(devforge)
            self.assertEqual(memo["topic_slug"], "caching-strategy-for-api")
        finally:
            tmp.cleanup()

    def test_bounded_turn_cap_stamps_partial(self):
        """After TURN_CAP follow-ups without explicit Clear, dimension flips to Partial."""
        tmp, devforge = self._fresh()
        try:
            for i in range(research_helper.TURN_CAP):
                r = _run([
                    "--devforge-dir", str(devforge), "set-symptom",
                    "--value", "partial value {0}".format(i),
                    "--state", "Missing",
                    "--increment-turn",
                ])
                self.assertEqual(r.returncode, 0, r.stderr)
            memo = self._read_memo(devforge)
            rec = memo["dimensions"]["symptom"]
            self.assertEqual(rec["turns"], research_helper.TURN_CAP)
            self.assertEqual(rec["state"], "Partial")
        finally:
            tmp.cleanup()

    def test_detect_mode_auto(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-symptom",
                "--value", "login fails on Safari", "--state", "Clear",
            ])
            r = _run(["--devforge-dir", str(devforge), "detect-mode"])
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)
            self.assertEqual(out["mode"], "bug")
            self.assertEqual(out["source"], "auto")
        finally:
            tmp.cleanup()

    def test_detect_mode_override(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-symptom",
                "--value", "unclear input here", "--state", "Clear",
            ])
            r = _run([
                "--devforge-dir", str(devforge), "detect-mode",
                "--override", "enhancement",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)
            self.assertEqual(out["mode"], "enhancement")
            self.assertEqual(out["source"], "override")
        finally:
            tmp.cleanup()

    def test_detect_mode_ambiguous(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-symptom",
                "--value", "we should add Redis but the current cache fails on cold start",
                "--state", "Clear",
            ])
            r = _run(["--devforge-dir", str(devforge), "detect-mode"])
            self.assertEqual(r.returncode, 0, r.stderr)
            out = json.loads(r.stdout)
            self.assertIsNone(out["mode"])
            self.assertEqual(out["source"], "ambiguous")
        finally:
            tmp.cleanup()

    def test_record_gap_flips_partial(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "record-gap",
                "--dimension", "scope",
                "--description", "user did not confirm whether feature-wide or single component",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = self._read_memo(devforge)
            self.assertEqual(len(memo["gaps"]), 1)
            self.assertEqual(memo["dimensions"]["scope"]["state"], "Partial")
        finally:
            tmp.cleanup()

    def test_check_conflicts_emits_and_persists(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-desired",
                "--value", "alphabetical sort by name A->Z", "--state", "Clear",
            ])
            _run([
                "--devforge-dir", str(devforge), "set-unchanged-behavior",
                "--value", "current numeric order must remain", "--state", "Clear",
            ])
            r = _run(["--devforge-dir", str(devforge), "check-conflicts"])
            self.assertEqual(r.returncode, 0, r.stderr)
            arr = json.loads(r.stdout)
            self.assertEqual(len(arr), 1)
            self.assertEqual(arr[0]["resolution"], "blocked-pending-user")
            # Second call must NOT duplicate.
            r2 = _run(["--devforge-dir", str(devforge), "check-conflicts"])
            arr2 = json.loads(r2.stdout)
            self.assertEqual(len(arr2), 1)
            memo = self._read_memo(devforge)
            self.assertEqual(len(memo["conflicts"]), 1)
        finally:
            tmp.cleanup()

    def test_record_conflict_resolution_rewrites_loser(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-desired",
                "--value", "alphabetical sort by name", "--state", "Clear",
            ])
            _run([
                "--devforge-dir", str(devforge), "set-unchanged-behavior",
                "--value", "current numeric order must remain", "--state", "Clear",
            ])
            _run(["--devforge-dir", str(devforge), "check-conflicts"])
            r = _run([
                "--devforge-dir", str(devforge), "record-conflict-resolution",
                "--index", "0",
                "--resolution", "user-chose-desired",
                "--rewrite-dimension", "unchanged_behavior",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = self._read_memo(devforge)
            self.assertEqual(memo["conflicts"][0]["resolution"], "user-chose-desired")
            self.assertIsNone(memo["dimensions"]["unchanged_behavior"]["value"])
            self.assertEqual(memo["dimensions"]["unchanged_behavior"]["state"], "Missing")
        finally:
            tmp.cleanup()

    def test_record_conflict_resolution_out_of_range(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "record-conflict-resolution",
                "--index", "5", "--resolution", "skipped",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("out of range", r.stderr)
        finally:
            tmp.cleanup()

    def _set_all_clear(self, devforge):
        for d in research_helper.RUBRIC_DIMENSIONS:
            _run([
                "--devforge-dir", str(devforge),
                "set-" + d.replace("_", "-"),
                "--value", "value for {0}".format(d), "--state", "Clear",
            ])

    def test_symptom_finalize_all_clear_no_conflicts(self):
        tmp, devforge = self._fresh()
        try:
            self._set_all_clear(devforge)
            r = _run(["--devforge-dir", str(devforge), "symptom-finalize"])
            self.assertEqual(r.returncode, 0, r.stderr)
        finally:
            tmp.cleanup()

    def test_symptom_finalize_blocked_conflict_fails_even_with_accept(self):
        tmp, devforge = self._fresh()
        try:
            self._set_all_clear(devforge)
            # Overwrite desired + unchanged with antagonist text.
            _run([
                "--devforge-dir", str(devforge), "set-desired",
                "--value", "alphabetical sort by name", "--state", "Clear",
            ])
            _run([
                "--devforge-dir", str(devforge), "set-unchanged-behavior",
                "--value", "current numeric order must remain", "--state", "Clear",
            ])
            _run(["--devforge-dir", str(devforge), "check-conflicts"])
            r = _run([
                "--devforge-dir", str(devforge), "symptom-finalize",
                "--accept-gaps",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("blocked conflict", r.stderr)
        finally:
            tmp.cleanup()

    def test_symptom_finalize_gaps_without_accept_fails(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-symptom",
                "--value", "x", "--state", "Clear",
            ])
            r = _run(["--devforge-dir", str(devforge), "symptom-finalize"])
            self.assertEqual(r.returncode, 2)
        finally:
            tmp.cleanup()

    def test_symptom_finalize_accept_gaps_records_override(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-symptom",
                "--value", "x", "--state", "Clear",
            ])
            r = _run([
                "--devforge-dir", str(devforge), "symptom-finalize",
                "--accept-gaps",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = self._read_memo(devforge)
            self.assertTrue(memo["override_recorded"])
        finally:
            tmp.cleanup()


# ---------------------------------------------------------------------------
# Phase 1 setters.
# ---------------------------------------------------------------------------


class TestPhase1Setters(unittest.TestCase):
    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset-memo"])
        _run(["--devforge-dir", str(devforge), "reset-report"])
        return tmp, devforge

    def _read_report(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "read-report"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_record_finding(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "record-finding",
                "--surface", "list component",
                "--file-line", "src/list.vue:42",
                "--relevance", "inline sort call",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["findings"]), 1)
            self.assertEqual(rep["findings"][0]["file_line"], "src/list.vue:42")
        finally:
            tmp.cleanup()

    def test_record_hypothesis_runtime_flag(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "record-hypothesis",
                "--cause", "race",
                "--falsifier", "probe race",
                "--runtime-probe-needed", "yes",
            ])
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["hypotheses"]), 1)
            self.assertTrue(rep["hypotheses"][0]["runtime_probe_needed"])
            # First recorded hypothesis auto-assigned label "A".
            self.assertEqual(rep["hypotheses"][0]["label"], "A")
        finally:
            tmp.cleanup()

    def test_record_hypothesis_label_sequence(self):
        """Second and third hypotheses get labels B and C in record order."""
        tmp, devforge = self._fresh()
        try:
            for cause in ("first cause", "second cause", "third cause"):
                _run([
                    "--devforge-dir", str(devforge), "record-hypothesis",
                    "--cause", cause,
                    "--falsifier", "falsifier for " + cause,
                    "--runtime-probe-needed", "no",
                ])
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["hypotheses"]), 3)
            self.assertEqual(rep["hypotheses"][0]["label"], "A")
            self.assertEqual(rep["hypotheses"][1]["label"], "B")
            self.assertEqual(rep["hypotheses"][2]["label"], "C")
        finally:
            tmp.cleanup()

    def test_set_confidence_enum(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-confidence",
                "--value", "Hypothesis",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            r_bad = _run([
                "--devforge-dir", str(devforge), "set-confidence",
                "--value", "Maybe",
            ])
            self.assertEqual(r_bad.returncode, 2)
        finally:
            tmp.cleanup()

    def test_structured_root_cause_lazy_record(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-trigger",
                "--value", "user clicks button",
            ])
            rep = self._read_report(devforge)
            self.assertIsNotNone(rep["structured_root_cause"])
            self.assertEqual(rep["structured_root_cause"]["trigger"], "user clicks button")
        finally:
            tmp.cleanup()

    def test_record_contributing_factor_max_3(self):
        tmp, devforge = self._fresh()
        try:
            for i in range(3):
                r = _run([
                    "--devforge-dir", str(devforge), "record-contributing-factor",
                    "--value", "factor {0}".format(i),
                ])
                self.assertEqual(r.returncode, 0, r.stderr)
            r4 = _run([
                "--devforge-dir", str(devforge), "record-contributing-factor",
                "--value", "factor 4",
            ])
            self.assertEqual(r4.returncode, 2)
            self.assertIn("max 3", r4.stderr)
        finally:
            tmp.cleanup()

    def test_set_verify_step_3_fields_required(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-verify-step",
                "--probe", "p",
                "--reproduction", "r",
                "--discriminator", "d",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(rep["verify_step"]["probe"], "p")
        finally:
            tmp.cleanup()


# ---------------------------------------------------------------------------
# Phase 2 setters.
# ---------------------------------------------------------------------------


class TestPhase2Setters(unittest.TestCase):
    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset-memo"])
        _run(["--devforge-dir", str(devforge), "reset-report"])
        return tmp, devforge

    def _read_report(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "read-report"])
        return json.loads(r.stdout)

    def test_set_approach_full_payload(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-approach",
                "--name", "Option A",
                "--description", "desc A",
                "--addresses-hypotheses", '["H1"]',
                "--does-not-cover", '["H2"]',
                "--pros", '["fast"]',
                "--cons", '["partial"]',
                "--complexity", "Low",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(rep["approaches"][0]["complexity"], "Low")
        finally:
            tmp.cleanup()

    def test_set_recommended_approach_rejects_unknown_name(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Nothing",
                "--rationale", "r",
                "--hypotheses-addressed", '["H1"]',
                "--hypotheses-not-covered", '[]',
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("does not match", r.stderr)
        finally:
            tmp.cleanup()

    def test_set_verdict_mode_aware_rejects_cross_mode(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-symptom",
                "--value", "login fails", "--state", "Clear",
            ])
            _run(["--devforge-dir", str(devforge), "detect-mode"])
            r_good = _run([
                "--devforge-dir", str(devforge), "set-verdict",
                "--value", "Root cause confirmed",
            ])
            self.assertEqual(r_good.returncode, 0, r_good.stderr)
            r_bad = _run([
                "--devforge-dir", str(devforge), "set-verdict",
                "--value", "Feasible",
            ])
            self.assertEqual(r_bad.returncode, 2)
            # _validate_enum produces "invalid value ...; allowed: [...]";
            # caller sees the bug-mode allowed set in the error message.
            self.assertIn("invalid value", r_bad.stderr)
            self.assertIn("Root cause confirmed", r_bad.stderr)
        finally:
            tmp.cleanup()

    def test_set_verdict_rejects_when_mode_unset(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-verdict",
                "--value", "Feasible",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("mode must be set", r.stderr)
        finally:
            tmp.cleanup()

    def test_set_complexity_full(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-complexity",
                "--codebase-changes", "Low", "--codebase-notes", "a",
                "--risk", "Med", "--risk-notes", "b",
                "--verify-cost", "High", "--verify-notes", "c",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(rep["complexity"]["risk"], "Med")
        finally:
            tmp.cleanup()

    def test_set_next_step_text_omits_on_not_recommended(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-symptom",
                "--value", "should add WebSocket", "--state", "Clear",
            ])
            _run(["--devforge-dir", str(devforge), "detect-mode"])
            _run([
                "--devforge-dir", str(devforge), "set-verdict",
                "--value", "Not Recommended",
            ])
            r = _run(["--devforge-dir", str(devforge), "set-next-step-text"])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertIsNone(rep["next_step_text"])
        finally:
            tmp.cleanup()

    def test_set_next_step_text_emits_on_feasible(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-symptom",
                "--value", "should add WebSocket", "--state", "Clear",
            ])
            _run([
                "--devforge-dir", str(devforge), "set-desired",
                "--value", "real-time push", "--state", "Clear",
            ])
            _run(["--devforge-dir", str(devforge), "detect-mode"])
            _run([
                "--devforge-dir", str(devforge), "set-approach",
                "--name", "Option A", "--description", "use SSE",
                "--addresses-hypotheses", '["H1"]', "--does-not-cover", '[]',
                "--pros", '["simple"]', "--cons", '["less interactive"]',
                "--complexity", "Low",
            ])
            _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A", "--rationale", "fits stack",
                "--hypotheses-addressed", '["H1"]',
                "--hypotheses-not-covered", '[]',
            ])
            _run([
                "--devforge-dir", str(devforge), "set-verdict",
                "--value", "Feasible",
            ])
            r = _run(["--devforge-dir", str(devforge), "set-next-step-text"])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertIsNotNone(rep["next_step_text"])
            self.assertIn("/specify", rep["next_step_text"])
            self.assertIn("Recommended approach: Option A", rep["next_step_text"])
        finally:
            tmp.cleanup()


# ---------------------------------------------------------------------------
# verify + render — full pipeline.
# ---------------------------------------------------------------------------


def _build_bug_state(devforge):
    """Build a complete bug-mode state by running real setters via subprocess.

    Mirrors the smoke flow used in REDESIGN-RESEARCH-PLAN testing. Used by
    both the verify happy-path test and the round-trip render-vs-fixture test.
    """
    _run(["--devforge-dir", str(devforge), "reset-memo"])
    _run(["--devforge-dir", str(devforge), "reset-report"])

    for d, val in (
        ("symptom", "Items not sorted in admin products list (sort fails)"),
        ("affected_area", "Admin > Products > List"),
        ("repro_or_current", "Open list with 50+ items"),
        ("desired", "alphabetical sort by name A->Z"),
        ("scope", "One component"),
        ("unchanged_behavior", "Filter + pagination must keep working"),
    ):
        _run([
            "--devforge-dir", str(devforge),
            "set-" + d.replace("_", "-"),
            "--value", val, "--state", "Clear",
        ])
    _run(["--devforge-dir", str(devforge), "detect-mode"])
    _run([
        "--devforge-dir", str(devforge), "set-topic",
        "--value", "items-not-sorted",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-date",
        "--value", "2026-05-11",
    ])

    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "products list component",
        "--file-line", "src/admin/Products.vue:201",
        "--relevance", "inline .sort() call inside watch body",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "list helper",
        "--file-line", "src/admin/helpers.ts:45",
        "--relevance", "shared comparator unused here",
    ])

    _run([
        "--devforge-dir", str(devforge), "record-hypothesis",
        "--cause", "unstable comparator in inline sort",
        "--falsifier", "swap comparator; verify order stable",
        "--runtime-probe-needed", "no",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-hypothesis",
        "--cause", "race between fetch and watch",
        "--falsifier", "log fetch ids before sort",
        "--runtime-probe-needed", "yes",
    ])

    _run([
        "--devforge-dir", str(devforge), "set-root-cause-hypothesis",
        "--value", "Inline .sort() in watch body uses unstable comparator while fetch mutates source list.",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-confidence",
        "--value", "Hypothesis",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-trigger",
        "--value", "User scrolls past 50 items + new item created concurrently",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-root-cause-systemic",
        "--value", "Inline sort in reactive body without stable comparator; no shared helper",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-contributing-factor",
        "--value", "No e2e covers paginate-while-mutating",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-contributing-factor",
        "--value", "Component uses inline .sort() vs shared helper",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-verify-step",
        "--probe", "console.log sort-input + sort-output at Products.vue:201/204",
        "--reproduction", "Open Products; sort by name; create item in another tab; switch back",
        "--discriminator", "if sort-input randomized then race; if input ordered + output not then comparator; both ordered then render",
    ])

    _run([
        "--devforge-dir", str(devforge), "set-approach",
        "--name", "Option A: Replace inline sort with shared comparator",
        "--description", "Use existing helper",
        "--addresses-hypotheses", json.dumps(["unstable comparator in inline sort"]),
        "--does-not-cover", json.dumps(["race between fetch and watch"]),
        "--pros", json.dumps(["small diff", "reuses helper"]),
        "--cons", json.dumps(["does not address race"]),
        "--complexity", "Low",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-approach",
        "--name", "Option B: Move sort to derived computed + stabilize comparator",
        "--description", "Reactive computed instead of watch body",
        "--addresses-hypotheses", json.dumps([
            "unstable comparator in inline sort",
            "race between fetch and watch",
        ]),
        "--does-not-cover", json.dumps([]),
        "--pros", json.dumps(["covers both", "reactive primitive"]),
        "--cons", json.dumps(["bigger refactor"]),
        "--complexity", "Med",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-recommended-approach",
        "--name", "Option B: Move sort to derived computed + stabilize comparator",
        "--rationale", "Closes both hypotheses; preserves pagination + filter behavior",
        "--hypotheses-addressed", json.dumps([
            "unstable comparator in inline sort",
            "race between fetch and watch",
        ]),
        "--hypotheses-not-covered", json.dumps([]),
    ])
    _run([
        "--devforge-dir", str(devforge), "set-constitution-constraints",
        "--rule", "Rule 2.1 — UI sort logic must be deterministic",
        "--impact", "Forces stable comparator",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-complexity",
        "--codebase-changes", "Low", "--codebase-notes", "1 component",
        "--risk", "Low", "--risk-notes", "pagination preserved",
        "--verify-cost", "Med", "--verify-notes", "needs e2e for paginate-while-mutating",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-verdict",
        "--value", "Root cause hypothesis (needs repro)",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-summary",
        "--value", "Inline sort in reactive body is unstable; recommended fix is a derived computed with stable comparator. Falsifier probe added for race hypothesis.",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-next-step-text",
    ])

    # Phase 2.4c: satisfy checks 8 + 9 (required for bug mode verify).
    # Two helpers: one same-package (src/admin) with its DEFINITION file_line
    # in src/admin, and one cross-layer (pkg-shared) with its definition in
    # pkg-shared — so check 8b (cross-layer rule) passes because at least one
    # helper's definition is in a different package than the symptom (src/admin).
    #
    # Patch 5 migration: record-fix-path-helper now enforces anchor gate —
    # every helper's file_line must collide with a recorded finding (exact or ±5).
    # The first helper anchors to the existing src/admin/Products.vue:201 finding
    # (exact match). The second helper (pkg-shared/sort.ts:10) requires a finding
    # at that path — added here to represent the CBM hit that surfaced the
    # cross-layer helper during Phase 2.4b canonical-pattern search.
    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "shared sort helper",
        "--file-line", "pkg-shared/sort.ts:10",
        "--relevance", "canonical comparator used by other packages — cross-layer fix candidate",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-fix-path-helper",
        "--helper-qn", "ProductsListComponent.sortItems",
        "--file-line", "src/admin/Products.vue:201",  # helper defined in same package (presentation)
    ])
    _run([
        "--devforge-dir", str(devforge), "record-inbound-caller",
        "--helper-qn", "ProductsListComponent.sortItems",
        "--caller-qn", "ProductsListComponent.watchItems",
        "--file-line", "src/admin/Products.vue:201",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-fix-path-helper",
        "--helper-qn", "SharedProductsHelper.compare",
        "--file-line", "pkg-shared/sort.ts:10",  # helper defined in cross-layer package
    ])
    _run([
        "--devforge-dir", str(devforge), "record-inbound-caller",
        "--helper-qn", "SharedProductsHelper.compare",
        "--caller-qn", "ProductsListComponent.sortItems",
        "--file-line", "src/admin/Products.vue:215",  # this is the CALL SITE in admin
    ])

    # Phase 2.3b: satisfy check 12 (mandatory runner-up framing + ≥1 tagged finding).
    _run([
        "--devforge-dir", str(devforge), "record-runner-up-framing",
        "--frame", "Race between fetch and watch (not comparator)",
        "--falsifier", "Stabilizing comparator alone fixes order under repro",
        "--confidence-vs-primary", "lower",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "fetch / watch race window",
        "--file-line", "src/admin/Products.vue:180",
        "--relevance", "fetch can complete while watch still iterating — runner-up probe",
        "--framing", "runner-up",
    ])

    # Patch 6 — satisfy check 15: bug mode + presentation-layer primary symptom
    # requires data_flow_chain to be set. Empty intermediates are valid (direct
    # handler→write-boundary without adapter hops in this particular scenario).
    _run([
        "--devforge-dir", str(devforge), "record-data-flow-chain",
        "--handler-qn", "ProductsListComponent.sortItems",
        "--write-boundary-qn", "SharedProductsHelper.compare",
        "--intermediate-qns", "[]",
    ])


def _build_enhancement_state(devforge):
    """Build a complete enhancement-mode state.

    Reused for verify happy-path + round-trip fixture comparison.
    """
    _run(["--devforge-dir", str(devforge), "reset-memo"])
    _run(["--devforge-dir", str(devforge), "reset-report"])

    for d, val in (
        ("symptom", "Export should be faster on large datasets"),
        ("affected_area", "ExportService background job"),
        ("repro_or_current", "5 min runtime on 100K rows; synchronous"),
        ("desired", "under 30 seconds OR async with progress"),
        ("scope", "Feature-wide; touches DB + service + UI"),
        ("unchanged_behavior", "Existing small-dataset exports complete in 2s"),
    ):
        _run([
            "--devforge-dir", str(devforge),
            "set-" + d.replace("_", "-"),
            "--value", val, "--state", "Clear",
        ])
    _run(["--devforge-dir", str(devforge), "detect-mode"])
    _run([
        "--devforge-dir", str(devforge), "set-topic",
        "--value", "export-performance",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-date",
        "--value", "2026-05-11",
    ])

    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "ExportService",
        "--file-line", "services/export.ts:88",
        "--relevance", "synchronous fetch + serialize on the request thread",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "JobsQueue",
        "--file-line", "services/jobs.ts:12",
        "--relevance", "available but unused for exports",
    ])

    _run([
        "--devforge-dir", str(devforge), "record-hypothesis",
        "--cause", "Serial DB fetch is the bottleneck",
        "--falsifier", "Profile DB time vs total runtime",
        "--runtime-probe-needed", "yes",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-hypothesis",
        "--cause", "Serializer hot loop dominates",
        "--falsifier", "Profile serializer vs fetch",
        "--runtime-probe-needed", "yes",
    ])

    _run([
        "--devforge-dir", str(devforge), "set-root-cause-hypothesis",
        "--value", "Current synchronous design serializes on the request thread; both fetch and serialize contribute.",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-confidence",
        "--value", "Speculative",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-verify-step",
        "--probe", "Time fetch vs serialize on a 100K-row export",
        "--reproduction", "Trigger export on 100K-row dataset",
        "--discriminator", "if fetch > 80% then DB; if serialize > 80% then serializer; otherwise mixed",
    ])

    _run([
        "--devforge-dir", str(devforge), "set-approach",
        "--name", "Option A: Async via JobsQueue",
        "--description", "Move export to background job; user polls progress",
        "--addresses-hypotheses", json.dumps([
            "Serial DB fetch is the bottleneck",
            "Serializer hot loop dominates",
        ]),
        "--does-not-cover", json.dumps([]),
        "--pros", json.dumps(["unblocks UI", "reuses JobsQueue"]),
        "--cons", json.dumps(["progress UI required"]),
        "--complexity", "Med",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-approach",
        "--name", "Option B: Streaming response",
        "--description", "Chunked streaming serializer",
        "--addresses-hypotheses", json.dumps(["Serializer hot loop dominates"]),
        "--does-not-cover", json.dumps(["Serial DB fetch is the bottleneck"]),
        "--pros", json.dumps(["no new infra"]),
        "--cons", json.dumps(["request thread still busy"]),
        "--complexity", "Low",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-recommended-approach",
        "--name", "Option A: Async via JobsQueue",
        "--rationale", "Closes both hypotheses; preserves small-dataset path",
        "--hypotheses-addressed", json.dumps([
            "Serial DB fetch is the bottleneck",
            "Serializer hot loop dominates",
        ]),
        "--hypotheses-not-covered", json.dumps([]),
    ])
    _run([
        "--devforge-dir", str(devforge), "set-constitution-constraints",
        "--rule", "Rule 4.2 — long-running work must move off request thread",
        "--impact", "Pushes toward async",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-complexity",
        "--codebase-changes", "Med", "--codebase-notes", "ExportService + UI + 1 new endpoint",
        "--risk", "Med", "--risk-notes", "queue saturation if backlog",
        "--verify-cost", "Med", "--verify-notes", "load test on 100K-row dataset",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-verdict",
        "--value", "Feasible with caveats",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-summary",
        "--value", "Async via JobsQueue moves export off the request thread; preserves small-dataset behavior. Probe runtime breakdown first.",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-next-step-text",
    ])

    # Phase 2.3b: satisfy check 12 (mandatory runner-up framing + ≥1 tagged finding).
    _run([
        "--devforge-dir", str(devforge), "record-runner-up-framing",
        "--frame", "Network IO dominates — fetch + chunked write upstream",
        "--falsifier", "Profile shows CPU-bound serializer, not network",
        "--confidence-vs-primary", "lower",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "upstream chunked write",
        "--file-line", "services/network.ts:54",
        "--relevance", "egress buffer saturates before serializer completes — runner-up probe",
        "--framing", "runner-up",
    ])


class TestVerifyHappyPath(unittest.TestCase):
    def test_bug_mode_verify_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_enhancement_mode_verify_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_enhancement_state(devforge)
            # Check 8 (plan 67) is mode-independent — _build_enhancement_state
            # leaves fix_path_helpers empty, so the escape must be recorded
            # for an otherwise-complete enhancement state to pass verify.
            _run([
                "--devforge-dir", str(devforge),
                "record-no-shared-callers-justification",
                "--justification", "Export perf change is additive in a new job runner module.",
            ])
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)


class TestVerifyFailures(unittest.TestCase):
    def test_single_hypothesis_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            # Wipe one hypothesis by editing JSON directly.
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["hypotheses"] = data["hypotheses"][:1]
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("hypothesis enumeration", r.stderr)

    def test_verdict_outside_mode_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["verdict"] = "Feasible"
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("not allowed", r.stderr)

    def test_unchanged_behavior_violation_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            memo_path = devforge / "research-state.json"
            memo = json.loads(memo_path.read_text())
            memo["dimensions"]["unchanged_behavior"]["value"] = (
                "current numeric order must remain"
            )
            memo_path.write_text(json.dumps(memo, indent=2) + "\n")
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["recommended_approach"]["rationale"] = (
                "alphabetical sort by name preserves nothing else"
            )
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("violates unchanged_behavior", r.stderr)

    def test_missing_verify_step_when_probe_needed_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["verify_step"] = None
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("verify_step required", r.stderr)

    def test_structured_root_cause_missing_for_bug_confirmed_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["confidence"] = "Confirmed"
            data["structured_root_cause"] = None
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("structured_root_cause", r.stderr)

    def test_structured_root_cause_skipped_for_speculative(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_enhancement_state(devforge)
            # Check 8 (plan 67) is mode-independent — record the escape so
            # this test's overall-clean assertion isolates check 5's skip.
            _run([
                "--devforge-dir", str(devforge),
                "record-no-shared-callers-justification",
                "--justification", "Export perf change is additive in a new job runner module.",
            ])
            # enhancement mode + Speculative confidence → no check.
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)


# ---------------------------------------------------------------------------
# Round-trip render against canonical fixtures.
# ---------------------------------------------------------------------------


class TestRoundTripFixtures(unittest.TestCase):
    def _render(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "render"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_bug_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            actual = self._render(devforge)
            fixture = (_FIXTURES_DIR / "research-sample-bug-report.md").read_text()
            self.assertEqual(actual, fixture)

    def test_enhancement_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_enhancement_state(devforge)
            actual = self._render(devforge)
            fixture = (_FIXTURES_DIR / "research-sample-enhancement-report.md").read_text()
            self.assertEqual(actual, fixture)


# ---------------------------------------------------------------------------
# Phase 2.4c — helper-API surface enumeration setters + verify checks.
# ---------------------------------------------------------------------------


class TestValidateFileLine(unittest.TestCase):
    """Unit tests for the _validate_file_line helper."""

    def test_valid_path_colon_line(self):
        self.assertEqual(
            research_helper._validate_file_line("src/foo.ts:42", "f"),
            "src/foo.ts:42",
        )

    def test_sentinel_none_accepted(self):
        self.assertEqual(
            research_helper._validate_file_line("(none)", "f"),
            "(none)",
        )

    def test_path_with_colon_in_path_uses_rfind(self):
        # Windows-style path with drive letter — rfind picks the last colon.
        self.assertEqual(
            research_helper._validate_file_line("C:/src/foo.ts:10", "f"),
            "C:/src/foo.ts:10",
        )

    def test_missing_colon_rejected(self):
        with self.assertRaises(ValueError):
            research_helper._validate_file_line("src/foo.ts", "f")

    def test_zero_line_rejected(self):
        with self.assertRaises(ValueError):
            research_helper._validate_file_line("src/foo.ts:0", "f")

    def test_negative_line_rejected(self):
        with self.assertRaises(ValueError):
            research_helper._validate_file_line("src/foo.ts:-1", "f")

    def test_non_integer_line_rejected(self):
        with self.assertRaises(ValueError):
            research_helper._validate_file_line("src/foo.ts:abc", "f")

    def test_empty_string_rejected(self):
        with self.assertRaises(ValueError):
            research_helper._validate_file_line("", "f")


class TestPhase24cSetters(unittest.TestCase):
    """Round-trip tests for all 5 Phase 2.4c setters."""

    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset-report"])
        # Patch 5: pre-seed findings for the file_lines used across these tests
        # so the anchor gate passes when record-fix-path-helper is called.
        _run([
            "--devforge-dir", str(devforge), "record-finding",
            "--surface", "BLoC dispatch",
            "--file-line", "lib/blocs/order_bloc.dart:42",
            "--relevance", "primary symptom site",
        ])
        _run([
            "--devforge-dir", str(devforge), "record-finding",
            "--surface", "fetch use case",
            "--file-line", "lib/use_cases/fetch_order.dart:10",
            "--relevance", "use-case entry point",
        ])
        return tmp, devforge

    def _read_report(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "read-report"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    # --- record-fix-path-helper ---

    def test_record_fix_path_helper_round_trip(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-fix-path-helper",
                "--helper-qn", "Service.loadData",
                "--file-line", "lib/blocs/order_bloc.dart:42",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            qns = [h["qn"] for h in rep["fix_path_helpers"]]
            self.assertIn("Service.loadData", qns)
            # Verify full dict shape.
            entry = rep["fix_path_helpers"][0]
            self.assertEqual(entry["qn"], "Service.loadData")
            self.assertEqual(entry["file_line"], "lib/blocs/order_bloc.dart:42")
        finally:
            tmp.cleanup()

    def test_record_fix_path_helper_deduplication(self):
        tmp, devforge = self._fresh()
        try:
            r1 = _run([
                "--devforge-dir", str(devforge),
                "record-fix-path-helper",
                "--helper-qn", "Service.loadData",
                "--file-line", "lib/blocs/order_bloc.dart:42",
            ])
            self.assertEqual(r1.returncode, 0, r1.stderr)
            # Second call: same qn, different file_line within anchor ±5 so the
            # call reaches the dedupe path (not blocked by Patch 5 anchor gate).
            r2 = _run([
                "--devforge-dir", str(devforge),
                "record-fix-path-helper",
                "--helper-qn", "Service.loadData",
                "--file-line", "lib/blocs/order_bloc.dart:44",  # Δ=2 vs finding at :42 → anchored; same qn → deduped
            ])
            self.assertEqual(r2.returncode, 0, r2.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["fix_path_helpers"]), 1)
        finally:
            tmp.cleanup()

    def test_record_fix_path_helper_multiple_distinct(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge),
                "record-fix-path-helper",
                "--helper-qn", "Service.loadData",
                "--file-line", "lib/blocs/order_bloc.dart:42",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "record-fix-path-helper",
                "--helper-qn", "FetchOrderUseCase.execute",
                "--file-line", "lib/use_cases/fetch_order.dart:10",
            ])
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["fix_path_helpers"]), 2)
        finally:
            tmp.cleanup()

    def test_record_fix_path_helper_rejects_none_sentinel(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-fix-path-helper",
                "--helper-qn", "Service.loadData",
                "--file-line", "(none)",
            ])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("(none)", r.stderr)
        finally:
            tmp.cleanup()

    def test_record_fix_path_helper_rejects_missing_file_line(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-fix-path-helper",
                "--helper-qn", "Service.loadData",
                # --file-line deliberately omitted
            ])
            # argparse must reject with exit 2.
            self.assertNotEqual(r.returncode, 0)
        finally:
            tmp.cleanup()

    def test_record_fix_path_helper_rejects_bad_file_line(self):
        """file_line without colon is rejected by _validate_file_line."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-fix-path-helper",
                "--helper-qn", "Service.loadData",
                "--file-line", "no-colon-here",
            ])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("file_line", r.stderr)
        finally:
            tmp.cleanup()

    # --- record-inbound-caller ---

    def test_record_inbound_caller_round_trip(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-inbound-caller",
                "--helper-qn", "Service.loadData",
                "--caller-qn", "OrderViewWidget.build",
                "--file-line", "lib/order_view.dart:88",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["inbound_callers"]), 1)
            row = rep["inbound_callers"][0]
            self.assertEqual(row["helper_qn"], "Service.loadData")
            self.assertEqual(row["caller_qn"], "OrderViewWidget.build")
            self.assertEqual(row["file_line"], "lib/order_view.dart:88")
        finally:
            tmp.cleanup()

    def test_record_inbound_caller_accepts_sentinel(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-inbound-caller",
                "--helper-qn", "Service.loadData",
                "--caller-qn", "dynamic_dispatch",
                "--file-line", "(none)",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(rep["inbound_callers"][0]["file_line"], "(none)")
        finally:
            tmp.cleanup()

    def test_record_inbound_caller_rejects_bad_file_line(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-inbound-caller",
                "--helper-qn", "Service.loadData",
                "--caller-qn", "foo.bar",
                "--file-line", "no-colon-here",
            ])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("file_line", r.stderr)
        finally:
            tmp.cleanup()

    # --- record-dead-sibling ---

    def test_record_dead_sibling_round_trip(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-dead-sibling",
                "--class-qn", "Service",
                "--method-qn", "Service.toggle",
                "--verified-via", "trace_path",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["dead_siblings"]), 1)
            row = rep["dead_siblings"][0]
            self.assertEqual(row["class_qn"], "Service")
            self.assertEqual(row["method_qn"], "Service.toggle")
            self.assertEqual(row["verified_via"], "trace_path")
        finally:
            tmp.cleanup()

    def test_record_dead_sibling_search_code_variant(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-dead-sibling",
                "--class-qn", "Service",
                "--method-qn", "Service.toggle",
                "--verified-via", "search_code",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
        finally:
            tmp.cleanup()

    def test_record_dead_sibling_rejects_invalid_verified_via(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-dead-sibling",
                "--class-qn", "Service",
                "--method-qn", "Service.toggle",
                "--verified-via", "grep",
            ])
            # argparse will exit 2 with error about choices
            self.assertNotEqual(r.returncode, 0)
        finally:
            tmp.cleanup()

    # --- record-consumer-chain ---

    def test_record_consumer_chain_round_trip(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-consumer-chain",
                "--value", "flag",
                "--consumer-qn", "OrderCreationUseCase.execute",
                "--file-line", "lib/order_creation.dart:55",
                "--role", "enforces Q&O parity at server boundary",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["consumer_chain"]), 1)
            row = rep["consumer_chain"][0]
            self.assertEqual(row["value"], "flag")
            self.assertEqual(row["consumer_qn"], "OrderCreationUseCase.execute")
            self.assertEqual(row["file_line"], "lib/order_creation.dart:55")
            self.assertEqual(row["role"], "enforces Q&O parity at server boundary")
        finally:
            tmp.cleanup()

    def test_record_consumer_chain_rejects_bad_file_line(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-consumer-chain",
                "--value", "flag",
                "--consumer-qn", "foo",
                "--file-line", "bad-file-line",
                "--role", "some role",
            ])
            self.assertNotEqual(r.returncode, 0)
        finally:
            tmp.cleanup()

    # --- set-value-semantics ---

    def test_set_value_semantics_preference_round_trip(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "flag",
                "--classification", "preference",
                "--evidence", "only set per user action",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["value_semantics"]), 1)
            row = rep["value_semantics"][0]
            self.assertEqual(row["value"], "flag")
            self.assertEqual(row["classification"], "preference")
            self.assertEqual(row["evidence"], "only set per user action")
        finally:
            tmp.cleanup()

    def test_set_value_semantics_last_write_wins(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "flag",
                "--classification", "preference",
                "--evidence", "first evidence",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "flag",
                "--classification", "unclassified",
                "--evidence", "second evidence",
            ])
            rep = self._read_report(devforge)
            # Only one row for the same value.
            rows = [r for r in rep["value_semantics"] if r["value"] == "flag"]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["classification"], "unclassified")
            self.assertEqual(rows[0]["evidence"], "second evidence")
        finally:
            tmp.cleanup()

    def test_set_value_semantics_different_values_append(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "flag",
                "--classification", "preference",
                "--evidence", "e1",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "isExternal",
                "--classification", "preference",
                "--evidence", "e2",
            ])
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["value_semantics"]), 2)
        finally:
            tmp.cleanup()

    def test_set_value_semantics_invariant_requires_consumer_chain(self):
        tmp, devforge = self._fresh()
        try:
            # Patch 7: --stable-across-calls is now required for invariant; pass it so
            # the consumer_chain gate (not the stable_across_calls gate) fires.
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "flag",
                "--classification", "invariant",
                "--evidence", "Q&O parity rule",
                "--stable-across-calls", "true",
            ])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("requires at least one consumer_chain entry", r.stderr)
        finally:
            tmp.cleanup()

    def test_set_value_semantics_invariant_succeeds_with_consumer_chain(self):
        tmp, devforge = self._fresh()
        try:
            # Record consumer_chain first.
            _run([
                "--devforge-dir", str(devforge),
                "record-consumer-chain",
                "--value", "flag",
                "--consumer-qn", "OrderCreationUseCase.execute",
                "--file-line", "lib/order.dart:10",
                "--role", "enforces invariant",
            ])
            # Patch 7: --stable-across-calls is now required for invariant.
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "flag",
                "--classification", "invariant",
                "--evidence", "OrderCreationUseCase.execute enforces Q&O parity",
                "--stable-across-calls", "true",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            rows = [row for row in rep["value_semantics"] if row["value"] == "flag"]
            self.assertEqual(rows[0]["classification"], "invariant")
        finally:
            tmp.cleanup()

    def test_set_value_semantics_rejects_invalid_classification(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "flag",
                "--classification", "definitely-not-valid",
                "--evidence", "e",
            ])
            self.assertNotEqual(r.returncode, 0)
        finally:
            tmp.cleanup()


class TestRecordNoSharedCallersJustification(unittest.TestCase):
    """record-no-shared-callers-justification — plan 67's check-8 escape."""

    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset-report"])
        return tmp, devforge

    def _read_report(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "read-report"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_round_trip(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-no-shared-callers-justification",
                "--justification", "Purely additive helper in a new module; no existing callers.",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(
                rep["no_shared_callers_justification"],
                "Purely additive helper in a new module; no existing callers.",
            )
        finally:
            tmp.cleanup()

    def test_rejects_empty_justification(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-no-shared-callers-justification",
                "--justification", "   ",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("no_shared_callers_justification", r.stderr)
        finally:
            tmp.cleanup()

    def test_last_write_wins(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge),
                "record-no-shared-callers-justification",
                "--justification", "First reason.",
            ])
            r2 = _run([
                "--devforge-dir", str(devforge),
                "record-no-shared-callers-justification",
                "--justification", "Second, corrected reason.",
            ])
            self.assertEqual(r2.returncode, 0, r2.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(rep["no_shared_callers_justification"], "Second, corrected reason.")
        finally:
            tmp.cleanup()

    def test_rejects_when_fix_path_helpers_already_recorded(self):
        tmp, devforge = self._fresh()
        try:
            # Seed a finding + a fix_path_helper (anchor gate requires the finding).
            _run([
                "--devforge-dir", str(devforge), "record-finding",
                "--surface", "shared helper",
                "--file-line", "src/lib/helper.ts:10",
                "--relevance", "existing shared helper",
            ])
            _run([
                "--devforge-dir", str(devforge), "record-fix-path-helper",
                "--helper-qn", "SharedHelper.doThing",
                "--file-line", "src/lib/helper.ts:10",
            ])
            r = _run([
                "--devforge-dir", str(devforge),
                "record-no-shared-callers-justification",
                "--justification", "No shared callers.",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("fix-path helper", r.stderr)
            rep = self._read_report(devforge)
            self.assertIsNone(rep["no_shared_callers_justification"])
        finally:
            tmp.cleanup()

    def test_fix_path_helper_rejects_when_justification_already_recorded(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-no-shared-callers-justification",
                "--justification", "No shared callers.",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            _run([
                "--devforge-dir", str(devforge), "record-finding",
                "--surface", "shared helper",
                "--file-line", "src/lib/helper.ts:10",
                "--relevance", "existing shared helper",
            ])
            r = _run([
                "--devforge-dir", str(devforge), "record-fix-path-helper",
                "--helper-qn", "SharedHelper.doThing",
                "--file-line", "src/lib/helper.ts:10",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("no-shared-callers justification is already recorded", r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(rep["fix_path_helpers"], [])
            self.assertEqual(rep["no_shared_callers_justification"], "No shared callers.")
        finally:
            tmp.cleanup()


class TestVerifyCheck8(unittest.TestCase):
    """Check 8: fix_path_helpers non-empty OR a no-shared-callers
    justification recorded. Mode-independent (plan 67 D1/D2)."""

    def _build_base_state(self, devforge):
        _build_bug_state(devforge)

    def test_check8_fails_when_fix_path_helpers_empty_bug_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._build_base_state(devforge)
            # Clear fix_path_helpers + inbound_callers by editing JSON directly.
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["fix_path_helpers"] = []
            data["inbound_callers"] = []
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("fix_path_helpers", r.stderr)
            self.assertIn("Phase 2.4c", r.stderr)

    def test_check8_passes_when_fix_path_helpers_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._build_base_state(devforge)
            # Add a finding at the helper's definition file_line so the
            # Patch 5 anchor gate passes.
            _run([
                "--devforge-dir", str(devforge),
                "record-finding",
                "--surface", "some helper",
                "--file-line", "lib/helpers/some.ts:10",
                "--relevance", "cross-layer helper definition",
            ])
            # Add a fix_path_helper and a matching inbound_caller.
            # --file-line gives the helper's definition location (cross-layer from src/admin).
            _run([
                "--devforge-dir", str(devforge),
                "record-fix-path-helper",
                "--helper-qn", "SomeHelper.doThing",
                "--file-line", "lib/helpers/some.ts:10",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "record-inbound-caller",
                "--helper-qn", "SomeHelper.doThing",
                "--caller-qn", "SomeCaller.call",
                "--file-line", "src/caller.ts:10",
            ])
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_check8_fires_for_enhancement_mode_empty_no_justification(self):
        """Plan 67 headline regression: enhancement mode no longer skips check 8.

        Previously (mode-gated check 8) this exact state passed verify —
        that was the bug this plan fixes. Flipped deliberately, not an
        accidental behavior change.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_enhancement_state(devforge)
            # fix_path_helpers empty + no justification → check 8 now fires
            # regardless of mode.
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("fix_path_helpers", r.stderr)
            self.assertIn("no-shared-callers", r.stderr)

    def test_check8_passes_for_enhancement_mode_with_justification(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_enhancement_state(devforge)
            r = _run([
                "--devforge-dir", str(devforge),
                "record-no-shared-callers-justification",
                "--justification", "Export perf change is additive in a new job runner module.",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_check8_passes_for_bug_mode_with_justification_and_empty_helpers(self):
        """Bug mode + empty helpers + justification recorded → clean.

        NEW behavior — mode no longer determines whether the justification
        escape is honored; bug mode gets the same escape enhancement mode
        does.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._build_base_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["fix_path_helpers"] = []
            data["inbound_callers"] = []
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run([
                "--devforge-dir", str(devforge),
                "record-no-shared-callers-justification",
                "--justification", "Bug fix is local; no other callers touch this path.",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_check8_fires_when_mode_unset(self):
        """Fresh state (mode None) + empty helpers + no justification → violation.

        Check 8 reads only fix_path_helpers / no_shared_callers_justification
        now — it no longer reads mode at all, so an unset mode still triggers it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run(["--devforge-dir", str(devforge), "reset-report"])
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("fix_path_helpers", r.stderr)
            self.assertIn("no-shared-callers", r.stderr)

    def test_check8_contradiction_when_both_helpers_and_justification_set(self):
        """fix_path_helpers non-empty AND justification present → contradiction.

        Both setters refuse this combination going forward regardless of call
        order (TestRecordNoSharedCallersJustification::
        test_rejects_when_fix_path_helpers_already_recorded and
        TestPhase24cSetters covering the reverse order); this exercises
        verify's own cross-guard against a direct-JSON-mutation bypass of
        both setter guards.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._build_base_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["no_shared_callers_justification"] = "No shared callers (bypassed setter guard)."
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("no_shared_callers_justification", r.stderr)
            self.assertIn("both are set", r.stderr)

    def test_check8_fires_for_whitespace_only_justification_via_direct_json(self):
        """A whitespace-only justification (direct JSON write) does not satisfy check 8.

        record-no-shared-callers-justification rejects empty/whitespace input
        at set time (TestRecordNoSharedCallersJustification::
        test_rejects_empty_justification); this exercises verify's own
        .strip() defense against a direct-JSON-mutation bypass of that gate.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._build_base_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["fix_path_helpers"] = []
            data["inbound_callers"] = []
            data["no_shared_callers_justification"] = "   "
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("fix_path_helpers", r.stderr)
            self.assertIn("no-shared-callers", r.stderr)


class TestVerifyCheck9(unittest.TestCase):
    """Check 9: every enumerated helper needs at least one inbound caller row."""

    def test_check9_fails_when_helper_missing_caller(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            # Add helper without a corresponding caller.
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["fix_path_helpers"] = [{"qn": "Service.loadData", "file_line": "lib/blocs/order_bloc.dart:42"}]
            data["inbound_callers"] = []
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("inbound_callers", r.stderr)
            self.assertIn("Service.loadData", r.stderr)

    def test_check9_passes_when_all_helpers_have_callers(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["fix_path_helpers"] = [{"qn": "Service.loadData", "file_line": "lib/blocs/order_bloc.dart:42"}]
            data["inbound_callers"] = [
                {"helper_qn": "Service.loadData", "caller_qn": "View.build", "file_line": "src/v.dart:5"}
            ]
            # Patch 5: add finding anchoring the helper's file_line (check 14 requires it).
            data.setdefault("findings", []).append({
                "surface": "BLoC dispatch", "file_line": "lib/blocs/order_bloc.dart:42",
                "relevance": "cross-layer helper candidate", "framing": "primary",
            })
            # Single-layer helpers (lib/blocs) — add justification + cites to satisfy check 13.
            data["consumer_chain"] = [
                {"value": "loadData", "consumer_qn": "View.build",
                 "file_line": "src/v.dart:5", "role": "caller"}
            ]
            if data.get("recommended_approach"):
                data["recommended_approach"]["single_layer_justification"] = (
                    "Bug is local to the BLoC layer; no cross-layer helpers involved."
                )
                data["recommended_approach"]["cites"] = ["View.build"]
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)


class TestVerifyCheck10(unittest.TestCase):
    """Check 10: invariant + dead siblings demands signature-touching approach."""

    def _state_with_invariant_and_dead_sibling(self, devforge, approach_desc):
        _build_bug_state(devforge)
        rep_path = devforge / "research-report.json"
        data = json.loads(rep_path.read_text())
        # Satisfy checks 8 + 9.
        data["fix_path_helpers"] = [{"qn": "Service.loadData", "file_line": "lib/blocs/order_bloc.dart:42"}]
        data["inbound_callers"] = [
            {"helper_qn": "Service.loadData", "caller_qn": "View.build", "file_line": "src/v.dart:5"}
        ]
        # Patch 5: add finding anchoring the helper's file_line (check 14 requires it).
        data.setdefault("findings", []).append({
            "surface": "BLoC dispatch", "file_line": "lib/blocs/order_bloc.dart:42",
            "relevance": "cross-layer helper candidate", "framing": "primary",
        })
        # Set value_semantics with invariant + consumer_chain.
        data["consumer_chain"] = [
            {"value": "flag", "consumer_qn": "OrderCreationUseCase.execute",
             "file_line": "lib/order.dart:10", "role": "enforces parity"}
        ]
        data["value_semantics"] = [
            {"value": "flag", "classification": "invariant", "evidence": "Q&O rule"}
        ]
        data["dead_siblings"] = [
            {"class_qn": "Service", "method_qn": "Service.toggle", "verified_via": "trace_path"}
        ]
        # Replace approach description.
        for ap in data["approaches"]:
            ap["description"] = approach_desc
            ap["pros"] = ["some pro"]
            ap["cons"] = ["some con"]
        # Make recommended approach rationale cite consumer to satisfy check 11.
        # Single-layer helpers (lib/blocs) — add justification + cites to satisfy check 13.
        if data.get("recommended_approach"):
            data["recommended_approach"]["rationale"] = (
                "OrderCreationUseCase.execute enforces invariant"
            )
            data["recommended_approach"]["single_layer_justification"] = (
                "Bug is local to the BLoC layer; consumer_chain confirms OrderCreationUseCase.execute enforces invariant."
            )
            data["recommended_approach"]["cites"] = ["OrderCreationUseCase.execute"]
        rep_path.write_text(json.dumps(data, indent=2) + "\n")

    def test_check10_fails_when_no_approach_mentions_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._state_with_invariant_and_dead_sibling(devforge, "use inline fix")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("dead_siblings non-empty", r.stderr)

    def test_check10_passes_when_approach_mentions_signature(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._state_with_invariant_and_dead_sibling(
                devforge,
                "change the helper signature to enforce invariant",
            )
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_check10_passes_when_approach_mentions_dead_sibling_qn(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._state_with_invariant_and_dead_sibling(
                devforge,
                "revive Service.toggle to enforce invariant",
            )
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_check10_not_triggered_when_no_dead_siblings(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Satisfy checks 8 + 9.
            data["fix_path_helpers"] = [{"qn": "Service.loadData", "file_line": "lib/blocs/order_bloc.dart:42"}]
            data["inbound_callers"] = [
                {"helper_qn": "Service.loadData", "caller_qn": "V.build", "file_line": "src/v.dart:5"}
            ]
            # Patch 5: add finding anchoring the helper's file_line (check 14 requires it).
            data.setdefault("findings", []).append({
                "surface": "BLoC dispatch", "file_line": "lib/blocs/order_bloc.dart:42",
                "relevance": "cross-layer helper candidate", "framing": "primary",
            })
            # Invariant but no dead siblings.
            data["consumer_chain"] = [
                {"value": "x", "consumer_qn": "SomeUseCase.run",
                 "file_line": "lib/s.dart:1", "role": "enforces it"}
            ]
            data["value_semantics"] = [
                {"value": "x", "classification": "invariant", "evidence": "SomeUseCase.run"}
            ]
            data["dead_siblings"] = []
            # Single-layer helpers (lib/blocs) — add justification + cites to satisfy check 13.
            if data.get("recommended_approach"):
                data["recommended_approach"]["rationale"] = "SomeUseCase.run enforces the rule"
                data["recommended_approach"]["single_layer_justification"] = (
                    "Bug is local to the BLoC layer; SomeUseCase.run confirms no cross-layer fix needed."
                )
                data["recommended_approach"]["cites"] = ["SomeUseCase.run"]
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)


class TestVerifyCheck11(unittest.TestCase):
    """Check 11: invariant requires evidence cite in recommended approach rationale."""

    def _state_with_invariant_and_rationale(self, devforge, rationale):
        _build_bug_state(devforge)
        rep_path = devforge / "research-report.json"
        data = json.loads(rep_path.read_text())
        # Satisfy checks 8 + 9.
        data["fix_path_helpers"] = [{"qn": "Service.loadData", "file_line": "lib/blocs/order_bloc.dart:42"}]
        data["inbound_callers"] = [
            {"helper_qn": "Service.loadData", "caller_qn": "View.build", "file_line": "src/v.dart:5"}
        ]
        # Patch 5: add finding anchoring the helper's file_line (check 14 requires it).
        data.setdefault("findings", []).append({
            "surface": "BLoC dispatch", "file_line": "lib/blocs/order_bloc.dart:42",
            "relevance": "cross-layer helper candidate", "framing": "primary",
        })
        data["consumer_chain"] = [
            {"value": "flag", "consumer_qn": "OrderCreationUseCase.execute",
             "file_line": "lib/order.dart:10", "role": "enforces parity"}
        ]
        data["value_semantics"] = [
            {"value": "flag", "classification": "invariant", "evidence": "Q&O parity rule"}
        ]
        data["dead_siblings"] = []
        # Single-layer helpers (lib/blocs) — add justification + cites to satisfy check 13.
        # The rationale param is set by the caller so check 11 can test different scenarios;
        # check 13 cites are always valid (consumer_qn is always present).
        if data.get("recommended_approach"):
            data["recommended_approach"]["rationale"] = rationale
            data["recommended_approach"]["single_layer_justification"] = (
                "Bug is local to the BLoC layer; OrderCreationUseCase.execute consumer_chain confirms it."
            )
            data["recommended_approach"]["cites"] = ["OrderCreationUseCase.execute"]
        rep_path.write_text(json.dumps(data, indent=2) + "\n")

    def test_check11_fails_when_rationale_cites_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._state_with_invariant_and_rationale(
                devforge,
                "this fix is the minimal change",
            )
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("recommended_approach.rationale", r.stderr)

    def test_check11_passes_when_rationale_cites_consumer_qn(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._state_with_invariant_and_rationale(
                devforge,
                "OrderCreationUseCase.execute enforces the invariant so fix lives there",
            )
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_check11_passes_when_rationale_cites_evidence_string(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._state_with_invariant_and_rationale(
                devforge,
                "Q&O parity rule means the BLoC must enforce it, not the UI",
            )
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_check11_not_triggered_when_no_invariant(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Satisfy checks 8 + 9.
            data["fix_path_helpers"] = [{"qn": "Service.loadData", "file_line": "lib/blocs/order_bloc.dart:42"}]
            data["inbound_callers"] = [
                {"helper_qn": "Service.loadData", "caller_qn": "V.build", "file_line": "s:1"}
            ]
            # Patch 5: add finding anchoring the helper's file_line (check 14 requires it).
            data.setdefault("findings", []).append({
                "surface": "BLoC dispatch", "file_line": "lib/blocs/order_bloc.dart:42",
                "relevance": "cross-layer helper candidate", "framing": "primary",
            })
            # Preference only, no invariant.
            data["consumer_chain"] = [
                {"value": "x", "consumer_qn": "V.build",
                 "file_line": "s:1", "role": "uses it"}
            ]
            data["value_semantics"] = [
                {"value": "x", "classification": "preference", "evidence": "user sets it"}
            ]
            # Single-layer helpers (lib/blocs) — add justification + cites to satisfy check 13.
            if data.get("recommended_approach"):
                data["recommended_approach"]["single_layer_justification"] = (
                    "Bug is preference-level in the BLoC layer only."
                )
                data["recommended_approach"]["cites"] = ["V.build"]
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)


class TestVerifyHappyPathWithPhase24c(unittest.TestCase):
    """Full happy-path verify with all Phase 2.4c fields populated."""

    def test_full_happy_path_bug_with_phase24c(self):
        """Bug mode: helpers, callers, invariant value, dead sibling, approaches, rationale all wired."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)

            # Satisfy check 8: fix_path_helpers non-empty.
            _run([
                "--devforge-dir", str(devforge),
                "record-fix-path-helper",
                "--helper-qn", "Service.loadData",
            ])
            # Satisfy check 9: inbound caller for every helper.
            _run([
                "--devforge-dir", str(devforge),
                "record-inbound-caller",
                "--helper-qn", "Service.loadData",
                "--caller-qn", "OrderViewWidget.build",
                "--file-line", "lib/order_view.dart:88",
            ])
            # Set up consumer_chain (required before invariant classification).
            _run([
                "--devforge-dir", str(devforge),
                "record-consumer-chain",
                "--value", "flag",
                "--consumer-qn", "OrderCreationUseCase.execute",
                "--file-line", "lib/order_creation.dart:55",
                "--role", "enforces Q&O parity at server boundary",
            ])
            # Set value_semantics to invariant.
            # Patch 7: --stable-across-calls required for invariant.
            _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "flag",
                "--classification", "invariant",
                "--evidence", "OrderCreationUseCase.execute enforces Q&O parity",
                "--stable-across-calls", "true",
            ])
            # Add dead sibling.
            _run([
                "--devforge-dir", str(devforge),
                "record-dead-sibling",
                "--class-qn", "Service",
                "--method-qn", "Service.toggle",
                "--verified-via", "trace_path",
            ])

            # Satisfy check 10: patch an approach to mention "signature".
            # Satisfy check 11: patch recommended_approach.rationale to cite consumer_qn.
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Patch first approach description to contain "signature".
            if data["approaches"]:
                data["approaches"][0]["description"] = (
                    "Change helper signature to enforce invariant at BLoC layer"
                )
            if data.get("recommended_approach"):
                data["recommended_approach"]["rationale"] = (
                    "OrderCreationUseCase.execute already enforces invariant; "
                    "fix belongs in helper signature, not view layer"
                )
            rep_path.write_text(json.dumps(data, indent=2) + "\n")

            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)


class TestResetReportClearsPhase24cFields(unittest.TestCase):
    """reset-report must clear Phase 2.4c fields back to empty lists."""

    def test_reset_clears_all_phase24c_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-report"])
            # Populate some fields.
            _run([
                "--devforge-dir", str(devforge),
                "record-fix-path-helper",
                "--helper-qn", "Foo.bar",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "record-dead-sibling",
                "--class-qn", "Foo",
                "--method-qn", "Foo.dead",
                "--verified-via", "search_code",
            ])
            # Reset.
            _run(["--devforge-dir", str(devforge), "reset-report"])
            data = json.loads((devforge / "research-report.json").read_text())
            for field in ("fix_path_helpers", "inbound_callers", "dead_siblings",
                          "consumer_chain", "value_semantics", "helper_rejection_log",
                          "value_production_sites"):  # Patch 7
                self.assertEqual(data[field], [], "field {0} not reset".format(field))


# ---------------------------------------------------------------------------
# Fix 1: transaction-escape — invariant rejection must NOT rewrite state file.
# ---------------------------------------------------------------------------


class TestSetValueSemanticsTransactionEscape(unittest.TestCase):
    """Invariant rejection must use exit code 2 and must not rewrite the state file."""

    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset-report"])
        return tmp, devforge

    def test_invariant_rejection_exit_code_is_2(self):
        """Rejecting invariant (no consumer_chain) must exit 2, not 1.
        Patch 7: pass --stable-across-calls true so the consumer_chain gate
        (not the stable_across_calls gate) fires and produces exit 2.
        """
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "flag",
                "--classification", "invariant",
                "--evidence", "Q&O parity rule",
                "--stable-across-calls", "true",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("requires at least one consumer_chain entry", r.stderr)
        finally:
            tmp.cleanup()

    def test_invariant_rejection_does_not_rewrite_state_file(self):
        """Rejecting invariant must not touch research-report.json (mtime unchanged).
        Patch 7: pass --stable-across-calls true so the consumer_chain gate fires
        and the state file is still not rewritten (pre-transaction guard).
        """
        tmp, devforge = self._fresh()
        try:
            rep_path = devforge / "research-report.json"
            mtime_before = rep_path.stat().st_mtime_ns
            _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "flag",
                "--classification", "invariant",
                "--evidence", "Q&O parity rule",
                "--stable-across-calls", "true",
            ])
            mtime_after = rep_path.stat().st_mtime_ns
            self.assertEqual(
                mtime_before,
                mtime_after,
                "research-report.json was rewritten despite invariant validation failure",
            )
        finally:
            tmp.cleanup()


# ---------------------------------------------------------------------------
# Fix 2: Check 11 — empty candidate token list must not fire the violation.
# ---------------------------------------------------------------------------


class TestVerifyCheck11EmptyTokenList(unittest.TestCase):
    """Check 11 must degrade gracefully when no citable tokens exist."""

    def test_check11_no_violation_when_token_list_empty(self):
        """has_invariant=True but consumer_chain empty + evidence empty + no dead_siblings
        → candidate token list is empty → Check 11 must NOT fire."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Use cross-layer helpers so check 13 doesn't fire (this test focuses on check 11).
            # src/admin (presentation) + lib/blocs (domain) = two packages → cross-layer.
            data["fix_path_helpers"] = [
                {"qn": "ProductsHelper.sort", "file_line": "src/admin/helpers.ts:10"},
                {"qn": "Service.loadData", "file_line": "lib/blocs/order_bloc.dart:42"},
            ]
            data["inbound_callers"] = [
                {"helper_qn": "ProductsHelper.sort", "caller_qn": "View.render", "file_line": "src/v.ts:5"},
                {"helper_qn": "Service.loadData", "caller_qn": "V.build", "file_line": "src/v.dart:5"},
            ]
            # Patch 5: add findings anchoring both helper file_lines (check 14 requires it).
            # src/admin/helpers.ts:45 is in the existing bug state but Δ=35 from :10 — add
            # an explicit finding at :10. lib/blocs/order_bloc.dart:42 is new.
            data.setdefault("findings", []).extend([
                {"surface": "helpers entry", "file_line": "src/admin/helpers.ts:10",
                 "relevance": "anchor for ProductsHelper.sort", "framing": "primary"},
                {"surface": "BLoC dispatch", "file_line": "lib/blocs/order_bloc.dart:42",
                 "relevance": "anchor for Service.loadData", "framing": "primary"},
            ])
            # Invariant entry: empty evidence, no consumer_chain, no dead_siblings.
            # Hand-authored to bypass the setter's consumer_chain prerequisite.
            data["consumer_chain"] = []
            data["value_semantics"] = [
                {"value": "X", "classification": "invariant", "evidence": ""}
            ]
            data["dead_siblings"] = []
            if data.get("recommended_approach"):
                data["recommended_approach"]["rationale"] = "anything goes here"
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            # Check 11 must not fire — empty token list means nothing to cite.
            self.assertNotIn("recommended_approach.rationale", r.stderr)
            # Overall result depends only on other checks; as long as Check 11
            # doesn't produce its specific message we've confirmed the fix.


# ---------------------------------------------------------------------------
# Fix 3: Check 10 — approach name included in haystack.
# ---------------------------------------------------------------------------


class TestVerifyCheck10NameInHaystack(unittest.TestCase):
    """Check 10 haystack must include approach.name (not just description/pros/cons)."""

    def _state_with_invariant_dead_sibling_name_only(self, devforge, approach_name):
        """Build state where the dead-sibling QN is in approach name only."""
        _build_bug_state(devforge)
        rep_path = devforge / "research-report.json"
        data = json.loads(rep_path.read_text())
        # Satisfy checks 8 + 9.
        data["fix_path_helpers"] = [{"qn": "Service.loadData", "file_line": "lib/blocs/order_bloc.dart:42"}]
        data["inbound_callers"] = [
            {"helper_qn": "Service.loadData", "caller_qn": "View.build", "file_line": "src/v.dart:5"}
        ]
        # Patch 5: add finding anchoring the helper's file_line (check 14 requires it).
        data.setdefault("findings", []).append({
            "surface": "BLoC dispatch", "file_line": "lib/blocs/order_bloc.dart:42",
            "relevance": "cross-layer helper candidate", "framing": "primary",
        })
        data["consumer_chain"] = [
            {"value": "flag", "consumer_qn": "OrderCreationUseCase.execute",
             "file_line": "lib/order.dart:10", "role": "enforces parity"}
        ]
        data["value_semantics"] = [
            {"value": "flag", "classification": "invariant", "evidence": "Q&O rule"}
        ]
        data["dead_siblings"] = [
            {"class_qn": "Service", "method_qn": "Service.toggle", "verified_via": "trace_path"}
        ]
        # Approach: dead-sibling QN only in name; description/pros/cons are generic.
        for ap in data["approaches"]:
            ap["name"] = approach_name
            ap["description"] = "generic description with no relevant tokens"
            ap["pros"] = ["some improvement"]
            ap["cons"] = ["some cost"]
        # recommended_approach.name must match one of the (now-renamed) approaches.
        # Single-layer helpers (lib/blocs) — add justification + cites to satisfy check 13.
        if data.get("recommended_approach"):
            data["recommended_approach"]["name"] = approach_name
            data["recommended_approach"]["rationale"] = (
                "OrderCreationUseCase.execute enforces invariant"
            )
            data["recommended_approach"]["single_layer_justification"] = (
                "Bug is local to the BLoC layer; consumer_chain confirms via OrderCreationUseCase.execute."
            )
            data["recommended_approach"]["cites"] = ["OrderCreationUseCase.execute"]
        rep_path.write_text(json.dumps(data, indent=2) + "\n")

    def test_check10_passes_when_approach_name_mentions_dead_sibling_qn(self):
        """Dead-sibling QN in approach.name only must satisfy Check 10."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._state_with_invariant_dead_sibling_name_only(
                devforge,
                "Revive Service.toggle",
            )
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_check10_case_insensitive_signature(self):
        """Uppercase 'SIGNATURE' in approach description must match (both sides lowercased)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Satisfy checks 8 + 9.
            data["fix_path_helpers"] = [{"qn": "Service.loadData", "file_line": "lib/blocs/order_bloc.dart:42"}]
            data["inbound_callers"] = [
                {"helper_qn": "Service.loadData", "caller_qn": "View.build",
                 "file_line": "src/v.dart:5"}
            ]
            # Patch 5: add finding anchoring the helper's file_line (check 14 requires it).
            data.setdefault("findings", []).append({
                "surface": "BLoC dispatch", "file_line": "lib/blocs/order_bloc.dart:42",
                "relevance": "cross-layer helper candidate", "framing": "primary",
            })
            data["consumer_chain"] = [
                {"value": "X", "consumer_qn": "SomeUseCase.run",
                 "file_line": "lib/s.dart:1", "role": "enforces it"}
            ]
            data["value_semantics"] = [
                {"value": "X", "classification": "invariant", "evidence": "SomeUseCase.run"}
            ]
            data["dead_siblings"] = [
                {"class_qn": "C", "method_qn": "m", "verified_via": "trace_path"}
            ]
            for ap in data["approaches"]:
                ap["description"] = "Use SIGNATURE-level enforcement at chokepoint"
                ap["pros"] = ["clean"]
                ap["cons"] = ["effort"]
            # Single-layer helpers (lib/blocs) — add justification + cites to satisfy check 13.
            if data.get("recommended_approach"):
                data["recommended_approach"]["rationale"] = "SomeUseCase.run enforces the rule"
                data["recommended_approach"]["single_layer_justification"] = (
                    "Bug is local to the BLoC layer; SomeUseCase.run consumer_chain confirms it."
                )
                data["recommended_approach"]["cites"] = ["SomeUseCase.run"]
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)


# ---------------------------------------------------------------------------
# Fix 4b: record-dead-sibling no-dedupe behavior.
# ---------------------------------------------------------------------------


class TestRecordDeadSiblingNoDedupe(unittest.TestCase):
    """record-dead-sibling must NOT dedupe identical (class_qn, method_qn) pairs."""

    def test_record_dead_sibling_no_dedupe(self):
        """Two calls with identical (class_qn, method_qn) produce two entries."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-report"])
            for _ in range(2):
                _run([
                    "--devforge-dir", str(devforge),
                    "record-dead-sibling",
                    "--class-qn", "Service",
                    "--method-qn", "Service.toggle",
                    "--verified-via", "trace_path",
                ])
            data = json.loads((devforge / "research-report.json").read_text())
            self.assertEqual(
                len(data["dead_siblings"]),
                2,
                "expected 2 entries (no dedupe); got {0}".format(len(data["dead_siblings"])),
            )


# ---------------------------------------------------------------------------
# Phase 2.3b — record-runner-up-framing setter + record-finding --framing arg
# + verify Check 12.
# ---------------------------------------------------------------------------


class TestRecordRunnerUpFraming(unittest.TestCase):
    """Tests for the record-runner-up-framing setter."""

    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset-report"])
        return tmp, devforge

    def _read_report(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "read-report"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_record_runner_up_framing_happy_path(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-runner-up-framing",
                "--frame", "shallow walk misses nested options",
                "--falsifier", "if recursive walk finds duplicates, shallow walk is the cause",
                "--confidence-vs-primary", "comparable",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            ruf = rep["runner_up_framing"]
            self.assertIsNotNone(ruf)
            self.assertEqual(ruf["frame"], "shallow walk misses nested options")
            self.assertEqual(
                ruf["falsifier"],
                "if recursive walk finds duplicates, shallow walk is the cause",
            )
            self.assertEqual(ruf["confidence_vs_primary"], "comparable")
        finally:
            tmp.cleanup()

    def test_record_runner_up_framing_invalid_confidence(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-runner-up-framing",
                "--frame", "some frame",
                "--falsifier", "some falsifier",
                "--confidence-vs-primary", "maybe",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("maybe", r.stderr)
        finally:
            tmp.cleanup()

    def test_record_runner_up_framing_empty_frame(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-runner-up-framing",
                "--frame", "",
                "--falsifier", "some falsifier",
                "--confidence-vs-primary", "lower",
            ])
            self.assertEqual(r.returncode, 2)
        finally:
            tmp.cleanup()

    def test_record_runner_up_framing_overwrites_on_resave(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge),
                "record-runner-up-framing",
                "--frame", "first frame",
                "--falsifier", "first falsifier",
                "--confidence-vs-primary", "lower",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "record-runner-up-framing",
                "--frame", "second frame",
                "--falsifier", "second falsifier",
                "--confidence-vs-primary", "higher",
            ])
            rep = self._read_report(devforge)
            ruf = rep["runner_up_framing"]
            self.assertEqual(ruf["frame"], "second frame")
            self.assertEqual(ruf["falsifier"], "second falsifier")
            self.assertEqual(ruf["confidence_vs_primary"], "higher")
        finally:
            tmp.cleanup()


class TestRecordFindingFramingArg(unittest.TestCase):
    """Tests for the --framing arg added to record-finding."""

    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset-report"])
        return tmp, devforge

    def _read_report(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "read-report"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_record_finding_framing_default_primary(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-finding",
                "--surface", "list component",
                "--file-line", "src/list.vue:42",
                "--relevance", "inline sort call",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["findings"]), 1)
            self.assertEqual(rep["findings"][0]["framing"], "primary")
        finally:
            tmp.cleanup()

    def test_record_finding_framing_runner_up(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-finding",
                "--surface", "deep walker",
                "--file-line", "src/walker.ts:10",
                "--relevance", "only traverses one level",
                "--framing", "runner-up",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["findings"]), 1)
            self.assertEqual(rep["findings"][0]["framing"], "runner-up")
        finally:
            tmp.cleanup()

    def test_record_finding_framing_invalid(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-finding",
                "--surface", "list component",
                "--file-line", "src/list.vue:42",
                "--relevance", "inline sort call",
                "--framing", "wibble",
            ])
            self.assertEqual(r.returncode, 2)
        finally:
            tmp.cleanup()


class TestVerifyCheck12(unittest.TestCase):
    """Check 12a: Phase 2.3b mandatory (runner_up_framing must be set).
    Check 12b: when set, at least one finding must carry framing=runner-up."""

    def test_verify_fails_when_runner_up_framing_unset(self):
        """12a unconditional: report w/o runner_up_framing → exit 2 + Phase 2.3b reminder."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["runner_up_framing"] = None
            data["findings"] = [
                f for f in data.get("findings") or []
                if f.get("framing") != "runner-up"
            ]
            rep_path.write_text(json.dumps(data, indent=2))
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("runner_up_framing", r.stderr)
            self.assertIn("Phase 2.3b", r.stderr)

    def test_verify_fails_when_runner_up_set_but_no_runner_up_findings(self):
        """12b conditional: framing set, zero runner-up findings → exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            self.assertIsNotNone(data.get("runner_up_framing"))
            data["findings"] = [
                f for f in data.get("findings") or []
                if f.get("framing") != "runner-up"
            ]
            rep_path.write_text(json.dumps(data, indent=2))
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("runner_up_framing", r.stderr)
            self.assertIn("runner-up", r.stderr)

    def test_verify_passes_when_runner_up_set_with_runner_up_finding(self):
        """Happy path: _build_bug_state already sets framing + tagged finding."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)


# ---------------------------------------------------------------------------
# Render — framing column + runner-up section.
# ---------------------------------------------------------------------------


class TestRenderFramingColumn(unittest.TestCase):
    """Findings table must include a Framing column in rendered markdown."""

    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset-memo"])
        _run(["--devforge-dir", str(devforge), "reset-report"])
        return tmp, devforge

    def _render(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "render"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_render_includes_framing_column_default_primary(self):
        """Findings recorded without --framing → rendered table shows 'primary' in Framing cell."""
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "record-finding",
                "--surface", "auth module",
                "--file-line", "src/auth.ts:10",
                "--relevance", "login handler",
            ])
            md = self._render(devforge)
            self.assertIn("| Surface | File:line | Relevance | Framing |", md)
            self.assertIn("|---|---|---|---|", md)
            self.assertIn("| primary |", md)
        finally:
            tmp.cleanup()

    def test_render_includes_framing_column_runner_up(self):
        """Finding recorded with --framing runner-up → rendered table shows 'runner-up' for that row."""
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "record-finding",
                "--surface", "deep walker",
                "--file-line", "src/walker.ts:10",
                "--relevance", "only traverses one level",
                "--framing", "runner-up",
            ])
            md = self._render(devforge)
            self.assertIn("| Surface | File:line | Relevance | Framing |", md)
            self.assertIn("| runner-up |", md)
            self.assertNotIn("| primary |", md)
        finally:
            tmp.cleanup()

    def test_render_omits_runner_up_section_when_unset(self):
        """When runner_up_framing is None, rendered output has no ## Runner-up framing section."""
        tmp, devforge = self._fresh()
        try:
            md = self._render(devforge)
            self.assertNotIn("## Runner-up framing", md)
        finally:
            tmp.cleanup()

    def test_render_includes_runner_up_section_when_set(self):
        """When record-runner-up-framing was called, rendered output has the full section."""
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge),
                "record-runner-up-framing",
                "--frame", "shallow walk misses nested options",
                "--falsifier", "if recursive walk finds duplicates, shallow walk is the cause",
                "--confidence-vs-primary", "comparable",
            ])
            md = self._render(devforge)
            self.assertIn("## Runner-up framing", md)
            self.assertIn("| Frame | shallow walk misses nested options |", md)
            self.assertIn("| Falsifier | if recursive walk finds duplicates, shallow walk is the cause |", md)
            self.assertIn("| Confidence vs primary | comparable |", md)
        finally:
            tmp.cleanup()

    def test_render_runner_up_section_before_hypothesis_enumeration(self):
        """## Runner-up framing must appear before ## Hypothesis Enumeration in the output."""
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge),
                "record-runner-up-framing",
                "--frame", "alternative cause",
                "--falsifier", "probe X",
                "--confidence-vs-primary", "lower",
            ])
            md = self._render(devforge)
            idx_runner_up = md.find("## Runner-up framing")
            idx_hypo = md.find("## Hypothesis Enumeration")
            self.assertNotEqual(idx_runner_up, -1, "## Runner-up framing not found")
            self.assertNotEqual(idx_hypo, -1, "## Hypothesis Enumeration not found")
            self.assertLess(
                idx_runner_up, idx_hypo,
                "## Runner-up framing must appear before ## Hypothesis Enumeration",
            )
        finally:
            tmp.cleanup()

    def test_render_section_order_with_root_cause_and_runner_up(self):
        tmp, devforge = self._fresh()
        try:
            _run(["--devforge-dir", str(devforge), "detect-mode", "--override", "bug"])
            _run(["--devforge-dir", str(devforge), "set-confidence", "--value", "Hypothesis"])
            _run([
                "--devforge-dir", str(devforge), "set-trigger",
                "--value", "User opens list with 50+ items",
            ])
            _run([
                "--devforge-dir", str(devforge), "set-root-cause-systemic",
                "--value", "Inline sort without stable comparator",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "record-runner-up-framing",
                "--frame", "race condition between fetch and render",
                "--falsifier", "log fetch ids before sort",
                "--confidence-vs-primary", "lower",
            ])
            md = self._render(devforge)
            self.assertIn("### Structured root cause", md)
            self.assertIn("## Runner-up framing", md)
            self.assertIn("## Hypothesis Enumeration", md)
            idx_src = md.index("### Structured root cause")
            idx_runner_up = md.index("## Runner-up framing")
            idx_hypo = md.index("## Hypothesis Enumeration")
            self.assertLess(idx_src, idx_runner_up)
            self.assertLess(idx_runner_up, idx_hypo)
        finally:
            tmp.cleanup()

    def test_render_legacy_finding_without_framing_key(self):
        tmp, devforge = self._fresh()
        try:
            state = research_helper.default_report_state()
            state["findings"] = [
                {
                    "surface": "auth module",
                    "file_line": "src/x.py:10",
                    "relevance": "login path",
                }
            ]
            (devforge / "research-report.json").write_text(
                json.dumps(state, indent=2) + "\n"
            )
            r = _run(["--devforge-dir", str(devforge), "render"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("| primary |", r.stdout)
        finally:
            tmp.cleanup()


# ---------------------------------------------------------------------------
# Layer-boundary detection — unit tests for _is_presentation_layer and
# _extract_package (Patch 2 / check 8b).
# ---------------------------------------------------------------------------


class TestLayerBoundaryDetection(unittest.TestCase):
    """Unit tests for _is_presentation_layer and _extract_package."""

    # --- _is_presentation_layer ---

    def test_vue_extension_is_presentation(self):
        self.assertTrue(research_helper._is_presentation_layer("src/Foo.vue"))

    def test_tsx_extension_is_presentation(self):
        self.assertTrue(research_helper._is_presentation_layer("src/Bar.tsx"))

    def test_jsx_extension_is_presentation(self):
        self.assertTrue(research_helper._is_presentation_layer("src/Baz.jsx"))

    def test_views_fragment_is_presentation(self):
        self.assertTrue(research_helper._is_presentation_layer("src/views/Foo.ts"))

    def test_components_fragment_is_presentation(self):
        self.assertTrue(research_helper._is_presentation_layer("src/components/Bar.ts"))

    def test_pages_fragment_is_presentation(self):
        self.assertTrue(research_helper._is_presentation_layer("src/pages/Home.ts"))

    def test_screens_fragment_is_presentation(self):
        self.assertTrue(research_helper._is_presentation_layer("src/screens/Login.ts"))

    def test_ui_fragment_is_presentation(self):
        self.assertTrue(research_helper._is_presentation_layer("src/ui/Button.ts"))

    def test_apps_app_prefix_is_presentation(self):
        self.assertTrue(research_helper._is_presentation_layer("apps/app/index.ts"))

    def test_apps_web_prefix_is_presentation(self):
        self.assertTrue(research_helper._is_presentation_layer("apps/web/main.ts"))

    def test_apps_frontend_prefix_is_presentation(self):
        self.assertTrue(research_helper._is_presentation_layer("apps/frontend/App.vue"))

    def test_regular_ts_is_not_presentation(self):
        self.assertFalse(research_helper._is_presentation_layer("src/utils/helpers.ts"))

    def test_domain_package_is_not_presentation(self):
        self.assertFalse(research_helper._is_presentation_layer("foo/QuoteLine.ts"))

    def test_empty_string_is_not_presentation(self):
        self.assertFalse(research_helper._is_presentation_layer(""))

    def test_none_is_not_presentation(self):
        self.assertFalse(research_helper._is_presentation_layer(None))

    def test_subviews_does_not_match_views_fragment(self):
        # '/views/' guard — 'subviews/' must not match.
        self.assertFalse(research_helper._is_presentation_layer("src/subviews/Foo.ts"))

    def test_src_admin_products_vue_is_presentation(self):
        # Validates the actual fixture path used in _build_bug_state.
        self.assertTrue(research_helper._is_presentation_layer("src/admin/Products.vue"))

    # --- _extract_package ---

    def test_extract_deep_path(self):
        self.assertEqual(
            research_helper._extract_package("apps/app/src/foo.vue"),
            "apps/app",
        )

    def test_extract_two_component_path(self):
        # File sits at second component slot — still returns first two components.
        self.assertEqual(
            research_helper._extract_package("foo/utils.ts"),
            "foo",
        )

    def test_extract_src_admin(self):
        self.assertEqual(
            research_helper._extract_package("src/admin/Products.vue"),
            "src/admin",
        )

    def test_extract_single_component(self):
        # Degenerate: no slash → return the single segment as-is.
        self.assertEqual(
            research_helper._extract_package("foo.vue"),
            "foo.vue",
        )

    def test_extract_dotslash_prefix_stripped(self):
        self.assertEqual(
            research_helper._extract_package("./apps/web/x.ts"),
            "apps/web",
        )

    def test_extract_leading_slash_stripped(self):
        self.assertEqual(
            research_helper._extract_package("/apps/web/x.ts"),
            "apps/web",
        )

    def test_extract_empty_string(self):
        self.assertEqual(research_helper._extract_package(""), "")

    def test_extract_none(self):
        self.assertEqual(research_helper._extract_package(None), "")

    def test_extract_pkg_shared(self):
        self.assertEqual(
            research_helper._extract_package("pkg-shared/sort.ts"),
            "pkg-shared",
        )

    def test_extract_whitespace_only(self):
        # F4: whitespace-only input must return empty string, not the space chars.
        self.assertEqual(research_helper._extract_package("   "), "")


# ---------------------------------------------------------------------------
# Check 8b integration tests — presentation-layer symptom cross-layer rule.
# ---------------------------------------------------------------------------


def _build_bug_state_same_package(devforge):
    """Bug state variant where ALL fix_path_helpers' inbound callers are in
    the SAME package as the (presentation-layer) symptom site.

    Used exclusively for check 8b failure tests so that _build_bug_state can
    stay cross-layer compliant (the exemplar).
    """
    _run(["--devforge-dir", str(devforge), "reset-memo"])
    _run(["--devforge-dir", str(devforge), "reset-report"])

    for d, val in (
        ("symptom", "Items not sorted in admin products list"),
        ("affected_area", "Admin > Products > List"),
        ("repro_or_current", "Open list with 50+ items"),
        ("desired", "alphabetical sort by name A->Z"),
        ("scope", "One component"),
        ("unchanged_behavior", "Filter + pagination must keep working"),
    ):
        _run([
            "--devforge-dir", str(devforge),
            "set-" + d.replace("_", "-"),
            "--value", val, "--state", "Clear",
        ])
    _run(["--devforge-dir", str(devforge), "detect-mode", "--override", "bug"])
    _run(["--devforge-dir", str(devforge), "set-topic", "--value", "items-not-sorted"])
    _run(["--devforge-dir", str(devforge), "set-date", "--value", "2026-05-11"])

    # Primary finding — presentation layer (src/admin).
    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "products list component",
        "--file-line", "src/admin/Products.vue:201",
        "--relevance", "inline .sort() call inside watch body",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "list helper",
        "--file-line", "src/admin/helpers.ts:45",
        "--relevance", "shared comparator unused here",
    ])

    _run([
        "--devforge-dir", str(devforge), "record-hypothesis",
        "--cause", "unstable comparator in inline sort",
        "--falsifier", "swap comparator; verify order stable",
        "--runtime-probe-needed", "no",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-hypothesis",
        "--cause", "race between fetch and watch",
        "--falsifier", "log fetch ids before sort",
        "--runtime-probe-needed", "no",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-root-cause-hypothesis",
        "--value", "Inline .sort() in watch body uses unstable comparator.",
    ])
    _run(["--devforge-dir", str(devforge), "set-confidence", "--value", "Hypothesis"])
    _run([
        "--devforge-dir", str(devforge), "set-trigger",
        "--value", "User scrolls past 50 items",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-root-cause-systemic",
        "--value", "Inline sort in reactive body without stable comparator",
    ])

    _run([
        "--devforge-dir", str(devforge), "set-approach",
        "--name", "Option A: Use stable comparator",
        "--description", "Replace inline sort",
        "--addresses-hypotheses", json.dumps(["unstable comparator in inline sort"]),
        "--does-not-cover", json.dumps(["race between fetch and watch"]),
        "--pros", json.dumps(["simple"]),
        "--cons", json.dumps(["partial"]),
        "--complexity", "Low",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-recommended-approach",
        "--name", "Option A: Use stable comparator",
        "--rationale", "Closes primary hypothesis",
        "--hypotheses-addressed", json.dumps(["unstable comparator in inline sort"]),
        "--hypotheses-not-covered", json.dumps([]),
    ])
    _run([
        "--devforge-dir", str(devforge), "set-constitution-constraints",
        "--rule", "Rule 2.1 — sort must be deterministic",
        "--impact", "Forces stable comparator",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-complexity",
        "--codebase-changes", "Low", "--codebase-notes", "1 component",
        "--risk", "Low", "--risk-notes", "pagination preserved",
        "--verify-cost", "Low", "--verify-notes", "quick visual check",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-verdict",
        "--value", "Root cause hypothesis (needs repro)",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-summary",
        "--value", "Inline sort is unstable; fix with stable comparator.",
    ])
    _run(["--devforge-dir", str(devforge), "set-next-step-text"])

    # SAME-PACKAGE helpers: DEFINITION file_line also in src/admin (same as symptom src/admin).
    # This means check 8b will fire — no helper defined outside presentation package.
    _run([
        "--devforge-dir", str(devforge), "record-fix-path-helper",
        "--helper-qn", "ProductsListComponent.sortItems",
        "--file-line", "src/admin/Products.vue:201",  # definition in same package
    ])
    _run([
        "--devforge-dir", str(devforge), "record-inbound-caller",
        "--helper-qn", "ProductsListComponent.sortItems",
        "--caller-qn", "ProductsListComponent.watchItems",
        "--file-line", "src/admin/Products.vue:201",
    ])
    # Anchor for the second same-package helper (Patch 5 anchor gate requires
    # every fix_path_helper.file_line to collide with a recorded finding).
    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "admin helpers entry",
        "--file-line", "src/admin/helpers.ts:10",
        "--relevance", "doSort helper definition — same-package (src/admin)",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-fix-path-helper",
        "--helper-qn", "ProductsAdminHelper.doSort",
        "--file-line", "src/admin/helpers.ts:10",  # definition also in same package
    ])
    _run([
        "--devforge-dir", str(devforge), "record-inbound-caller",
        "--helper-qn", "ProductsAdminHelper.doSort",
        "--caller-qn", "ProductsListComponent.sortItems",
        "--file-line", "src/admin/Products.vue:205",
    ])

    # Mandatory runner-up framing (check 12a).
    _run([
        "--devforge-dir", str(devforge), "record-runner-up-framing",
        "--frame", "Race between fetch and watch",
        "--falsifier", "Stabilizing comparator alone fixes order",
        "--confidence-vs-primary", "lower",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "fetch / watch race window",
        "--file-line", "src/admin/Products.vue:180",
        "--relevance", "race probe — runner-up",
        "--framing", "runner-up",
    ])


class TestVerifyCheck8b(unittest.TestCase):
    """Check 8b: presentation-layer symptom + all helpers in same package → violation."""

    def test_verify_check8b_passes_when_symptom_is_domain_layer(self):
        """Domain-layer symptom: check 8b skipped regardless of helper packages.
        Check 13 still fires for single-layer helpers — must add justification + cites."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            # Rewrite findings + helpers so symptom is domain-layer (foo).
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Symptom finding → domain-layer file.
            data["findings"] = [
                {
                    "surface": "core util",
                    "file_line": "foo/utils.ts:10",
                    "relevance": "comparison logic",
                    "framing": "primary",
                },
                {
                    "surface": "race probe",
                    "file_line": "foo/utils.ts:20",
                    "relevance": "runner-up probe",
                    "framing": "runner-up",
                },
            ]
            # All helpers also in foo — would trigger 8b for presentation
            # but domain symptom means 8b is skipped.
            # Check 13 still fires for single-layer, so add justification + cites.
            data["fix_path_helpers"] = [{"qn": "CoreUtil.compare", "file_line": "foo/utils.ts:10"}]
            data["inbound_callers"] = [
                {
                    "helper_qn": "CoreUtil.compare",
                    "caller_qn": "CoreUtil.sort",
                    "file_line": "foo/sort.ts:5",
                },
            ]
            # Provide consumer_chain to anchor cites for check 13.
            data["consumer_chain"] = [
                {"value": "compareResult", "consumer_qn": "CoreUtil.sort",
                 "file_line": "foo/sort.ts:5", "role": "consumes compare result"}
            ]
            if data.get("recommended_approach"):
                data["recommended_approach"]["single_layer_justification"] = (
                    "Symptom is domain-local (foo comparison logic); no cross-layer trace needed."
                )
                data["recommended_approach"]["cites"] = ["CoreUtil.sort"]
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertNotIn("cross-layer rule", r.stderr)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_verify_check8b_passes_when_helpers_cross_layer(self):
        """Presentation symptom + helpers split across packages → check 8b passes."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # _build_bug_state already provides cross-layer helpers.
            _build_bug_state(devforge)
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertNotIn("cross-layer rule", r.stderr)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_verify_check8b_fails_when_presentation_symptom_all_helpers_same_package(self):
        """Presentation symptom + all helpers same package → 8b violation."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state_same_package(devforge)
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("cross-layer rule", r.stderr)
            self.assertIn("src/admin/Products.vue", r.stderr)

    def test_verify_check8b_skipped_when_no_primary_finding(self):
        """No findings recorded → check 8b silently skipped (no cross-layer violation)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            # Remove all findings so there's no primary finding to evaluate.
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["findings"] = []
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            # 8b must not contribute a violation — only 12b (no runner-up finding)
            # might fire; confirm 8b's specific message is absent.
            self.assertNotIn("cross-layer rule", r.stderr)


# ---------------------------------------------------------------------------
# Patch 3 — set-scope evidence gate tests.
# ---------------------------------------------------------------------------


class TestSetScopeEvidenceGate(unittest.TestCase):
    """Verify the 'one place' evidence requirement gate on set-scope."""

    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset-memo"])
        return tmp, devforge

    def _read_memo(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "read-memo"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    # --- narrow-framing (gate MUST fire) ---

    def test_set_scope_one_place_with_evidence_passes(self):
        """--value 'one place' + valid --evidence → exit 0; evidence stored on dim."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "one place",
                "--evidence", "src/admin/Products.vue:201",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = self._read_memo(devforge)
            scope_rec = memo["dimensions"]["scope"]
            self.assertEqual(scope_rec["value"], "one place")
            self.assertEqual(scope_rec["evidence"], "src/admin/Products.vue:201")
        finally:
            tmp.cleanup()

    def test_set_scope_one_place_without_evidence_fails(self):
        """--value 'one place' with no --evidence → exit 2 + stderr explains the rule."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "one place",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("--evidence is required", r.stderr)
            # Stable rationale phrase locked in assertion.
            self.assertIn("Phase 2 exploration depth", r.stderr)
        finally:
            tmp.cleanup()

    def test_set_scope_one_place_empty_evidence_fails(self):
        """--value 'one place' + --evidence '' (empty string) → exit 2."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "one place",
                "--evidence", "",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("--evidence is required", r.stderr)
        finally:
            tmp.cleanup()

    def test_set_scope_one_place_none_sentinel_fails(self):
        """--value 'one place' + --evidence '(none)' → exit 2; concrete citation required."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "one place",
                "--evidence", "(none)",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("(none)", r.stderr)
        finally:
            tmp.cleanup()

    def test_set_scope_one_place_case_insensitive_gate(self):
        """Gate fires case-insensitively: 'One Place' normalizes to 'one place'."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "One Place",
                "--evidence", "src/x.ts:1",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = self._read_memo(devforge)
            self.assertEqual(memo["dimensions"]["scope"]["evidence"], "src/x.ts:1")
        finally:
            tmp.cleanup()

    def test_set_scope_one_place_whitespace_value_gate(self):
        """Gate fires when value has surrounding whitespace: '  one place  '."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "  one place  ",
                "--evidence", "src/x.ts:1",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = self._read_memo(devforge)
            self.assertEqual(memo["dimensions"]["scope"]["evidence"], "src/x.ts:1")
        finally:
            tmp.cleanup()

    def test_set_scope_evidence_invalid_file_line_fails(self):
        """--value 'one place' + --evidence 'not a file:line' → exit 2 via _validate_file_line."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "one place",
                "--evidence", "not a file line no colon",
            ])
            self.assertEqual(r.returncode, 2)
            # Confirm inner validator's error message surfaces.
            self.assertIn("scope.evidence", r.stderr)
        finally:
            tmp.cleanup()

    # --- non-narrow framings (gate must NOT fire) ---

    def test_set_scope_feature_wide_no_evidence_passes(self):
        """--value 'feature-wide' without --evidence → exit 0 (gate does not fire)."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "feature-wide",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
        finally:
            tmp.cleanup()

    def test_set_scope_cross_cutting_no_evidence_passes(self):
        """--value 'cross-cutting' without --evidence → exit 0."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "cross-cutting",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
        finally:
            tmp.cleanup()

    def test_set_scope_one_component_freeform_no_evidence_passes(self):
        """Free-form synonym 'One component' (not exact 'one place') → exit 0.

        This is the value used in _build_bug_state; gate matches literal 'one place'
        only — free-form synonyms are NOT gated.
        """
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "One component",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
        finally:
            tmp.cleanup()

    def test_set_scope_feature_wide_with_evidence_ignored(self):
        """--value 'feature-wide' + --evidence provided → exit 0; evidence NOT stored.

        Non-narrow framings accept (and silently discard) --evidence so callers
        that always pass --evidence don't break. The dim record must NOT gain an
        'evidence' key for non-narrow values.
        """
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "feature-wide",
                "--evidence", "src/x.ts:1",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = self._read_memo(devforge)
            # Evidence must NOT be stored for non-narrow framings.
            self.assertNotIn("evidence", memo["dimensions"]["scope"])
        finally:
            tmp.cleanup()

    # --- render + summary integration ---

    def test_render_shows_evidence_for_one_place(self):
        """Render output includes '(evidence: ...)' inline with scope value."""
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "one place",
                "--evidence", "src/admin/Products.vue:201",
            ])
            r = _run(["--devforge-dir", str(devforge), "render"])
            self.assertIn("one place (evidence: src/admin/Products.vue:201)", r.stdout)
        finally:
            tmp.cleanup()

    def test_render_no_evidence_annotation_for_feature_wide(self):
        """Render output has no '(evidence:' annotation for non-narrow scope."""
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "feature-wide",
            ])
            r = _run(["--devforge-dir", str(devforge), "render"])
            self.assertNotIn("(evidence:", r.stdout)
        finally:
            tmp.cleanup()

    def test_summary_shows_evidence_for_one_place(self):
        """Summary output includes 'evidence=...' in scope line."""
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "one place",
                "--evidence", "src/admin/Products.vue:201",
            ])
            r = _run(["--devforge-dir", str(devforge), "summary"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("evidence=src/admin/Products.vue:201", r.stdout)
        finally:
            tmp.cleanup()

    def test_summary_no_evidence_annotation_for_feature_wide(self):
        """Summary output has no 'evidence=' annotation for non-narrow scope."""
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "feature-wide",
            ])
            r = _run(["--devforge-dir", str(devforge), "summary"])
            self.assertEqual(r.returncode, 0, r.stderr)
            # Scope line should not contain evidence key.
            scope_line = next(
                (l for l in r.stdout.splitlines() if l.strip().startswith("scope:")), None
            )
            self.assertIsNotNone(scope_line)
            self.assertNotIn("evidence=", scope_line)
        finally:
            tmp.cleanup()

    # --- anti-regression: _build_bug_state uses 'One component' (free-form) ---

    def test_build_bug_state_scope_not_gated(self):
        """_build_bug_state's 'One component' scope value doesn't trigger the gate.

        Verifies that no existing test fixture is broken by Patch 3.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # set-scope with 'One component' must succeed without --evidence.
            r = _run([
                "--devforge-dir", str(devforge), "set-scope",
                "--value", "One component",
                "--state", "Clear",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)


# ---------------------------------------------------------------------------
# Patch 4 — single-layer recommendation gate (check 13).
# ---------------------------------------------------------------------------


def _build_single_layer_bug_state(devforge):
    """Build a bug state with ALL fix_path_helpers in the same package (src/admin).

    Used for Patch 4 single-layer gate tests. The symptom site and BOTH helpers
    are in src/admin — so _extract_package maps all to 'src/admin', triggering
    the single-layer gate in set-recommended-approach and verify check 13.
    Compared with _build_bug_state (cross-layer): that has one helper in src/admin
    and one in pkg-shared, so the gate does NOT fire there.
    """
    _run(["--devforge-dir", str(devforge), "reset-memo"])
    _run(["--devforge-dir", str(devforge), "reset-report"])

    for d, val in (
        ("symptom", "Items not sorted in admin products list (sort fails)"),
        ("affected_area", "Admin > Products > List"),
        ("repro_or_current", "Open list with 50+ items"),
        ("desired", "alphabetical sort by name A->Z"),
        ("scope", "One component"),
        ("unchanged_behavior", "Filter + pagination must keep working"),
    ):
        _run([
            "--devforge-dir", str(devforge),
            "set-" + d.replace("_", "-"),
            "--value", val, "--state", "Clear",
        ])
    _run(["--devforge-dir", str(devforge), "detect-mode"])
    _run(["--devforge-dir", str(devforge), "set-topic", "--value", "items-not-sorted"])
    _run(["--devforge-dir", str(devforge), "set-date", "--value", "2026-05-11"])

    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "products list component",
        "--file-line", "src/admin/Products.vue:201",
        "--relevance", "inline .sort() call inside watch body",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "race probe",
        "--file-line", "src/admin/Products.vue:180",
        "--relevance", "race between fetch and watch — runner-up probe",
        "--framing", "runner-up",
    ])

    _run([
        "--devforge-dir", str(devforge), "record-hypothesis",
        "--cause", "unstable comparator in inline sort",
        "--falsifier", "swap comparator; verify order stable",
        "--runtime-probe-needed", "no",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-hypothesis",
        "--cause", "race between fetch and watch",
        "--falsifier", "log fetch ids before sort",
        "--runtime-probe-needed", "yes",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-root-cause-hypothesis",
        "--value", "Inline .sort() in watch body uses unstable comparator.",
    ])
    _run(["--devforge-dir", str(devforge), "set-confidence", "--value", "Hypothesis"])
    _run([
        "--devforge-dir", str(devforge), "set-trigger",
        "--value", "User scrolls past 50 items + new item created concurrently",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-root-cause-systemic",
        "--value", "Inline sort in reactive body without stable comparator; no shared helper",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-verify-step",
        "--probe", "console.log sort-input at Products.vue:201",
        "--reproduction", "Open Products; sort by name; create item in another tab; switch back",
        "--discriminator", "if sort-input randomized then race; if ordered and output not then comparator",
    ])

    _run([
        "--devforge-dir", str(devforge), "set-approach",
        "--name", "Option A: comparator fix",
        "--description", "Fix the inline comparator in src/admin/Products.vue",
        "--addresses-hypotheses", json.dumps(["unstable comparator in inline sort"]),
        "--does-not-cover", json.dumps(["race between fetch and watch"]),
        "--pros", json.dumps(["small diff"]),
        "--cons", json.dumps(["does not address race"]),
        "--complexity", "Low",
    ])
    # Note: set-recommended-approach is NOT called here — each test calls it with
    # different args to exercise the gate. Callers must call it themselves.

    _run([
        "--devforge-dir", str(devforge), "set-constitution-constraints",
        "--rule", "Rule 2.1 — UI sort logic must be deterministic",
        "--impact", "Forces stable comparator",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-complexity",
        "--codebase-changes", "Low", "--codebase-notes", "1 component",
        "--risk", "Low", "--risk-notes", "pagination preserved",
        "--verify-cost", "Med", "--verify-notes", "needs e2e",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-verdict",
        "--value", "Root cause hypothesis (needs repro)",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-summary",
        "--value", "Inline sort in reactive body is unstable.",
    ])

    # BOTH helpers are in src/admin — single-layer (presentation layer).
    # This triggers the single-layer gate in set-recommended-approach.
    _run([
        "--devforge-dir", str(devforge), "record-fix-path-helper",
        "--helper-qn", "ProductsListComponent.sortItems",
        "--file-line", "src/admin/Products.vue:201",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-inbound-caller",
        "--helper-qn", "ProductsListComponent.sortItems",
        "--caller-qn", "ProductsListComponent.watchItems",
        "--file-line", "src/admin/Products.vue:201",
    ])

    # Mandatory runner-up framing.
    _run([
        "--devforge-dir", str(devforge), "record-runner-up-framing",
        "--frame", "Race between fetch and watch (not comparator)",
        "--falsifier", "Stabilizing comparator alone fixes order under repro",
        "--confidence-vs-primary", "lower",
    ])


def _build_domain_single_layer_bug_state(devforge):
    """Single-layer bug state in a NON-presentation package (Dart BLoC layer).

    Used by Patch 4 check-13 tests. Symptom + all helpers live in
    `lib/blocs/order_bloc.dart` — single-package AND non-presentation, so
    check 8b does NOT fire (its suppression of check 13 does not apply)
    AND check 13's single-layer detection DOES fire. This is the only
    configuration where the --single-layer-justification gate is the
    blocking constraint.
    """
    _run(["--devforge-dir", str(devforge), "reset-memo"])
    _run(["--devforge-dir", str(devforge), "reset-report"])

    for d, val in (
        ("symptom", "Order BLoC fetch returns stale rows after refresh"),
        ("affected_area", "Service.loadData"),
        ("repro_or_current", "Trigger refresh while a fetch is in-flight"),
        ("desired", "Latest fetch's rows always emitted last"),
        ("scope", "One component"),
        ("unchanged_behavior", "Single-fetch path must keep working"),
    ):
        _run([
            "--devforge-dir", str(devforge),
            "set-" + d.replace("_", "-"),
            "--value", val, "--state", "Clear",
        ])
    _run(["--devforge-dir", str(devforge), "detect-mode", "--override", "bug"])
    _run(["--devforge-dir", str(devforge), "set-topic", "--value", "order-bloc-stale"])
    _run([
        "--devforge-dir", str(devforge), "set-verbatim-prompt",
        "--value",
        "Order BLoC fetch returns stale rows after refresh. Suspected cause: last-fetch-wins race in Service.loadData.",
    ])
    _run(["--devforge-dir", str(devforge), "set-date", "--value", "2026-05-17"])

    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "BLoC dispatch",
        "--file-line", "lib/blocs/order_bloc.dart:42",
        "--relevance", "primary symptom site",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "race-window probe",
        "--file-line", "lib/blocs/order_bloc.dart:99",
        "--relevance", "runner-up probe",
        "--framing", "runner-up",
    ])

    _run([
        "--devforge-dir", str(devforge), "record-hypothesis",
        "--cause", "last-fetch-wins racing in loadData",
        "--falsifier", "serialize fetches; verify order stable",
        "--runtime-probe-needed", "no",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-hypothesis",
        "--cause", "subscription resubscribed mid-stream",
        "--falsifier", "log subscription identity across refresh",
        "--runtime-probe-needed", "yes",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-root-cause-hypothesis",
        "--value", "Service.loadData lacks fetch-id guard.",
    ])
    _run(["--devforge-dir", str(devforge), "set-confidence", "--value", "Hypothesis"])
    _run([
        "--devforge-dir", str(devforge), "set-trigger",
        "--value", "Concurrent refresh while in-flight fetch pending",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-root-cause-systemic",
        "--value", "Internal BLoC state not guarded against concurrent fetch IDs",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-verify-step",
        "--probe", "log fetch ids before sink at order_bloc.dart:42",
        "--reproduction", "Trigger refresh twice within 100ms",
        "--discriminator", "if older fetch wins then race; else state mutation",
    ])

    _run([
        "--devforge-dir", str(devforge), "set-approach",
        "--name", "Option A: fetch-id guard",
        "--description", "Add fetch-id guard inside Service.loadData",
        "--addresses-hypotheses", json.dumps(["last-fetch-wins racing in loadData"]),
        "--does-not-cover", json.dumps(["subscription resubscribed mid-stream"]),
        "--pros", json.dumps(["small diff", "no public-API change"]),
        "--cons", json.dumps(["does not address resubscription"]),
        "--complexity", "Low",
    ])

    _run([
        "--devforge-dir", str(devforge), "set-constitution-constraints",
        "--rule", "Rule 4.1 — Concurrent state must be guarded",
        "--impact", "Forces fetch-id check",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-complexity",
        "--codebase-changes", "Low", "--codebase-notes", "1 BLoC method",
        "--risk", "Low", "--risk-notes", "single-fetch path preserved",
        "--verify-cost", "Med", "--verify-notes", "needs race repro",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-verdict",
        "--value", "Root cause hypothesis (needs repro)",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-summary",
        "--value", "Service.loadData vulnerable to concurrent-fetch race.",
    ])

    # BOTH helpers in lib/blocs — single-package AND non-presentation-layer.
    # Triggers check 13 single-layer gate; does NOT trigger check 8b suppression.
    _run([
        "--devforge-dir", str(devforge), "record-fix-path-helper",
        "--helper-qn", "Service.loadData",
        "--file-line", "lib/blocs/order_bloc.dart:42",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-inbound-caller",
        "--helper-qn", "Service.loadData",
        "--caller-qn", "Service.handleRefresh",
        "--file-line", "lib/blocs/order_bloc.dart:5",
    ])

    _run([
        "--devforge-dir", str(devforge), "record-runner-up-framing",
        "--frame", "Subscription resubscribed mid-stream (not fetch-id race)",
        "--falsifier", "Adding fetch-id guard alone fixes order",
        "--confidence-vs-primary", "lower",
    ])


class TestRecommendedApproachSingleLayerGate(unittest.TestCase):
    """Patch 4 — single-layer gate on set-recommended-approach (setter-time).

    When all fix_path_helpers resolve to the same package (bug mode)
    AND check 8b does NOT fire (symptom is NOT presentation-layer),
    --single-layer-justification + non-empty --cites are required.
    Each cite must match a recorded consumer_chain / value_semantics /
    dead_siblings row token.

    Fixture uses Dart BLoC layer (`lib/blocs/order_bloc.dart`) — single-package
    AND non-presentation, so check 8b does not suppress the gate.
    """

    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _build_domain_single_layer_bug_state(devforge)
        return tmp, devforge

    def _read_report(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "read-report"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def _add_consumer_chain(self, devforge, consumer_qn="FetchConsumer.handleResult"):
        """Helper to record a consumer_chain row so valid cites exist."""
        _run([
            "--devforge-dir", str(devforge),
            "record-consumer-chain",
            "--value", "fetchId",
            "--consumer-qn", consumer_qn,
            "--file-line", "lib/blocs/order_bloc.dart:80",
            "--role", "drives sink emission",
        ])

    # --- cross-layer passes without justification ---

    def test_set_recommended_approach_cross_layer_passes_without_justification(self):
        """Cross-layer helpers (src/admin + pkg-shared): gate does not fire.

        No --single-layer-justification / --cites required. New fields NOT written.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)  # already cross-layer
            # Confirm _build_bug_state helpers are in different packages.
            # (src/admin + pkg-shared → two distinct packages → not single-layer)
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option B: Move sort to derived computed + stabilize comparator",
                "--rationale", "Closes both hypotheses; preserves pagination + filter behavior",
                "--hypotheses-addressed", json.dumps([
                    "unstable comparator in inline sort",
                    "race between fetch and watch",
                ]),
                "--hypotheses-not-covered", json.dumps([]),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            rec = rep["recommended_approach"]
            self.assertIsNone(rec.get("single_layer_justification"))
            self.assertIsNone(rec.get("cites"))

    # --- single-layer: gate fires ---

    def test_set_recommended_approach_single_layer_requires_justification(self):
        """Single-layer helpers (lib/blocs only, non-presentation): gate rejects without --single-layer-justification."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard is the minimal fix",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps([]),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("--single-layer-justification is required", r.stderr)
            # Error must name the detected package.
            self.assertIn("lib/blocs", r.stderr)
        finally:
            tmp.cleanup()

    def test_set_recommended_approach_single_layer_requires_cites(self):
        """Justification supplied but --cites omitted: gate rejects."""
        tmp, devforge = self._fresh()
        try:
            self._add_consumer_chain(devforge)
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard is the minimal fix",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "Bug is local to the BLoC layer.",
                # --cites deliberately omitted
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("--cites is required", r.stderr)
        finally:
            tmp.cleanup()

    def test_set_recommended_approach_single_layer_requires_cites_empty_array(self):
        """--cites '[]' (empty array) also triggers the cites-required error."""
        tmp, devforge = self._fresh()
        try:
            self._add_consumer_chain(devforge)
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard is the minimal fix",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "Bug is local to the BLoC layer.",
                "--cites", "[]",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("--cites is required", r.stderr)
        finally:
            tmp.cleanup()

    def test_set_recommended_approach_cites_must_resolve_to_recorded_row(self):
        """Cite token not in consumer_chain / value_semantics / dead_siblings: rejected."""
        tmp, devforge = self._fresh()
        try:
            self._add_consumer_chain(devforge)
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard is the minimal fix",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "Bug is local to the BLoC layer.",
                "--cites", json.dumps(["NotARecordedQN"]),
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("NotARecordedQN", r.stderr)
            self.assertIn("Recorded tokens", r.stderr)
        finally:
            tmp.cleanup()

    # --- cite sources: consumer_chain.consumer_qn ---

    def test_set_recommended_approach_single_layer_consumer_chain_cite_passes(self):
        """consumer_chain.consumer_qn token accepted as a valid cite."""
        tmp, devforge = self._fresh()
        try:
            self._add_consumer_chain(devforge, consumer_qn="FetchConsumer.handleResult")
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard closes the race",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "Bug is local to the BLoC layer; no cross-layer trace needed.",
                "--cites", json.dumps(["FetchConsumer.handleResult"]),
                "--proposed-call-shape", "loadData(quoteId, fetchId)",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            rec = rep["recommended_approach"]
            self.assertEqual(rec["single_layer_justification"],
                             "Bug is local to the BLoC layer; no cross-layer trace needed.")
            self.assertEqual(rec["cites"], ["FetchConsumer.handleResult"])
        finally:
            tmp.cleanup()

    # --- cite sources: dead_siblings.method_qn ---

    def test_set_recommended_approach_single_layer_dead_sibling_cite_passes(self):
        """dead_siblings.method_qn accepted as a valid cite token."""
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge),
                "record-dead-sibling",
                "--class-qn", "Service",
                "--method-qn", "OldFetchOrderMethod",
                "--verified-via", "search_code",
            ])
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard closes the race",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "Bug is local to BLoC; OldFetchOrderMethod was already removed.",
                "--cites", json.dumps(["OldFetchOrderMethod"]),
                "--proposed-call-shape", "loadData(quoteId, fetchId)",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(rep["recommended_approach"]["cites"], ["OldFetchOrderMethod"])
        finally:
            tmp.cleanup()

    # --- cite sources: value_semantics.value ---

    def test_set_recommended_approach_single_layer_value_semantics_cite_passes(self):
        """value_semantics.value accepted as a valid cite token."""
        tmp, devforge = self._fresh()
        try:
            # Record consumer_chain first (required for invariant classification).
            _run([
                "--devforge-dir", str(devforge),
                "record-consumer-chain",
                "--value", "fetchId",
                "--consumer-qn", "FetchConsumer.handleResult",
                "--file-line", "lib/blocs/order_bloc.dart:80",
                "--role", "drives sink emission",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "fetchId",
                "--classification", "preference",
                "--evidence", "incremented per refresh trigger",
            ])
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard closes the race",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "fetchId is a BLoC-internal counter; bug is layer-local.",
                "--cites", json.dumps(["fetchId"]),
                "--proposed-call-shape", "loadData(quoteId, fetchId)",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(rep["recommended_approach"]["cites"], ["fetchId"])
        finally:
            tmp.cleanup()

    # --- cite sources: value_semantics.evidence ---

    def test_set_recommended_approach_single_layer_value_semantics_evidence_cite_passes(self):
        """value_semantics.evidence string accepted as a valid cite token."""
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge),
                "record-consumer-chain",
                "--value", "fetchId",
                "--consumer-qn", "FetchConsumer.handleResult",
                "--file-line", "lib/blocs/order_bloc.dart:80",
                "--role", "drives sink emission",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "fetchId",
                "--classification", "preference",
                "--evidence", "lib/blocs/order_bloc.dart:42",
            ])
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard closes the race",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "fetchId is a BLoC-internal counter scoped to Service.",
                "--cites", json.dumps(["lib/blocs/order_bloc.dart:42"]),
                "--proposed-call-shape", "loadData(quoteId, fetchId)",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(rep["recommended_approach"]["cites"], ["lib/blocs/order_bloc.dart:42"])
        finally:
            tmp.cleanup()

    # --- enhancement mode skips the gate ---

    def test_set_recommended_approach_skips_gate_when_check_8b_would_fire(self):
        """Presentation-layer single-package: check 8b will veto verify, so the
        setter gate is suppressed — supplying --single-layer-justification cannot
        rescue an 8b-failing state, so the setter does not demand it. The LLM
        gets a single actionable error from 8b at verify time instead.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_single_layer_bug_state(devforge)  # presentation-layer single-package
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: comparator fix",
                "--rationale", "Comparator swap is the minimal fix",
                "--hypotheses-addressed", json.dumps(["unstable comparator in inline sort"]),
                "--hypotheses-not-covered", json.dumps([]),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_set_recommended_approach_enhancement_mode_skipped(self):
        """Enhancement mode: single-layer gate does not fire even with same-package helpers."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_enhancement_state(devforge)
            # The enhancement state has no fix_path_helpers, so gate definitely
            # doesn't fire. Confirm exit 0 without --single-layer-justification.
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: Async via JobsQueue",
                "--rationale", "Closes both hypotheses; preserves small-dataset path",
                "--hypotheses-addressed", json.dumps([
                    "Serial DB fetch is the bottleneck",
                    "Serializer hot loop dominates",
                ]),
                "--hypotheses-not-covered", json.dumps([]),
            ])
            self.assertEqual(r.returncode, 0, r.stderr)


class TestVerifyCheck13(unittest.TestCase):
    """Check 13: cross-layer recommendation enforcement (verify-time).

    Catches out-of-order setter calls where recommended_approach was written
    before fix_path_helpers collapsed to single-layer.
    """

    def test_verify_check13_passes_cross_layer(self):
        """Cross-layer helpers: check 13 does not fire. _build_bug_state is cross-layer."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("check 13", r.stderr)

    def test_verify_check13_fails_single_layer_no_justification(self):
        """Single-layer state (non-presentation) without single_layer_justification → check 13 violation."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            # Mutate state directly: collapse to single-layer NON-presentation
            # (Dart BLoC layer). Use non-presentation so check 8b does NOT fire
            # and suppress check 13 — we need check 13 itself to fire here.
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["findings"] = [
                {"surface": "BLoC dispatch", "file_line": "lib/blocs/order_bloc.dart:42",
                 "relevance": "primary symptom site", "framing": "primary"},
                {"surface": "race probe", "file_line": "lib/blocs/order_bloc.dart:99",
                 "relevance": "runner-up", "framing": "runner-up"},
            ]
            data["fix_path_helpers"] = [
                {"qn": "Service.loadData", "file_line": "lib/blocs/order_bloc.dart:42"},
            ]
            data["inbound_callers"] = [
                {"helper_qn": "Service.loadData", "caller_qn": "Service.handleRefresh",
                 "file_line": "lib/blocs/order_bloc.dart:5"},
            ]
            if data.get("recommended_approach"):
                data["recommended_approach"].pop("single_layer_justification", None)
                data["recommended_approach"].pop("cites", None)
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("check 13", r.stderr)
            self.assertIn("single_layer_justification", r.stderr)

    def test_verify_check13_fails_single_layer_no_cites(self):
        """Single-layer state (non-presentation) with justification but no cites → check 13 violation (cites)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["findings"] = [
                {"surface": "BLoC dispatch", "file_line": "lib/blocs/order_bloc.dart:42",
                 "relevance": "primary symptom site", "framing": "primary"},
                {"surface": "race probe", "file_line": "lib/blocs/order_bloc.dart:99",
                 "relevance": "runner-up", "framing": "runner-up"},
            ]
            data["fix_path_helpers"] = [
                {"qn": "Service.loadData", "file_line": "lib/blocs/order_bloc.dart:42"},
            ]
            data["inbound_callers"] = [
                {"helper_qn": "Service.loadData", "caller_qn": "Service.handleRefresh",
                 "file_line": "lib/blocs/order_bloc.dart:5"},
            ]
            if data.get("recommended_approach"):
                # Has justification but no cites.
                data["recommended_approach"]["single_layer_justification"] = (
                    "Bug is layer-local to Service."
                )
                data["recommended_approach"].pop("cites", None)
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("check 13", r.stderr)
            self.assertIn("cites", r.stderr)

    def test_verify_check13_skipped_for_enhancement_mode(self):
        """Enhancement mode: check 13 never fires."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_enhancement_state(devforge)
            # Check 8 (plan 67) is mode-independent — record the escape so
            # this test's overall-clean assertion isolates check 13's skip.
            _run([
                "--devforge-dir", str(devforge),
                "record-no-shared-callers-justification",
                "--justification", "Export perf change is additive in a new job runner module.",
            ])
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("check 13", r.stderr)

    def test_verify_check13_skipped_when_no_fix_path_helpers(self):
        """No fix_path_helpers: check 13 does not fire."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["fix_path_helpers"] = []
            data["inbound_callers"] = []
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            # Check 8 fires (fix_path_helpers empty for bug mode) but NOT check 13.
            self.assertIn("fix_path_helpers", r.stderr)
            self.assertNotIn("check 13", r.stderr)

    def test_verify_check13_passes_single_layer_with_justification_and_cites(self):
        """Domain-layer single-package + valid justification + cites → verify exits 0.

        Confirms the check 13 escape path is reachable: when symptom is NOT
        presentation-layer (so check 8b doesn't fire) AND all helpers are in
        one non-presentation package AND set-recommended-approach is called
        with --single-layer-justification + --cites pointing at a recorded row,
        verify accepts the report.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_domain_single_layer_bug_state(devforge)
            # Add a consumer_chain row so cites have something to resolve to.
            _run([
                "--devforge-dir", str(devforge), "record-consumer-chain",
                "--value", "fetchId",
                "--consumer-qn", "FetchConsumer.handleResult",
                "--file-line", "lib/blocs/order_bloc.dart:80",
                "--role", "drives sink emission",
            ])
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard closes the race",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "Bug is local to BLoC layer; consumer chain confirms layer-locality.",
                "--cites", json.dumps(["FetchConsumer.handleResult"]),
                "--proposed-call-shape", "loadData(quoteId, fetchId)",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            v = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(v.returncode, 0, v.stderr)
            self.assertNotIn("check 13", v.stderr)
            self.assertNotIn("check 8b", v.stderr)

    def test_verify_check13_suppressed_when_check_8b_fires(self):
        """Presentation-layer single-package + no justification → only check 8b
        violation surfaces; check 13 is suppressed.

        Without suppression, the LLM would see TWO violations (8b + 13) and a
        confusing "supply --single-layer-justification" recommendation that
        could not satisfy verify (8b would still veto). Suppression ensures
        the LLM sees only the one actionable error from 8b.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_single_layer_bug_state(devforge)
            # Set a recommended_approach WITHOUT justification (setter gate also
            # suppressed by 8b, so this succeeds at write time).
            _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: comparator fix",
                "--rationale", "Comparator swap is the minimal fix",
                "--hypotheses-addressed", json.dumps(["unstable comparator in inline sort"]),
                "--hypotheses-not-covered", json.dumps([]),
            ])
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("cross-layer rule", r.stderr)  # check 8b fires
            self.assertNotIn("check 13", r.stderr)        # check 13 suppressed
            self.assertNotIn("single_layer_justification", r.stderr)


# ---------------------------------------------------------------------------
# Patch 4 — render + summary integration for single-layer justification.
# ---------------------------------------------------------------------------


class TestSingleLayerRenderAndSummary(unittest.TestCase):
    """Render and summary output for single-layer justification fields."""

    def _fresh_cross_layer(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _build_bug_state(devforge)
        return tmp, devforge

    def _render(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "render"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def _summary(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "summary"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_render_omits_single_layer_section_when_not_set(self):
        """Cross-layer recommendation: single_layer_justification absent → no extra render section."""
        tmp, devforge = self._fresh_cross_layer()
        try:
            md = self._render(devforge)
            self.assertNotIn("Single-layer justification:", md)
            self.assertNotIn("**Cites:**", md)
        finally:
            tmp.cleanup()

    def test_render_includes_single_layer_section_when_set(self):
        """State with single_layer_justification + cites → render section present."""
        tmp, devforge = self._fresh_cross_layer()
        try:
            # Inject single_layer_justification directly to test render independently.
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            if data.get("recommended_approach"):
                data["recommended_approach"]["single_layer_justification"] = (
                    "Bug is layer-local to admin comparator."
                )
                data["recommended_approach"]["cites"] = ["SortConsumer.handleSort", "sortKey"]
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            md = self._render(devforge)
            self.assertIn("**Single-layer justification:**", md)
            self.assertIn("Bug is layer-local to admin comparator.", md)
            self.assertIn("**Cites:**", md)
            self.assertIn("- SortConsumer.handleSort", md)
            self.assertIn("- sortKey", md)
        finally:
            tmp.cleanup()

    def test_summary_shows_single_layer_yes_for_single_package(self):
        """summary shows 'recommended_approach.single_layer: yes' for single-package state."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Collapse to single-layer for summary test.
            data["fix_path_helpers"] = [
                {"qn": "ProductsListComponent.sortItems", "file_line": "src/admin/Products.vue:201"},
            ]
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            out = self._summary(devforge)
            self.assertIn("recommended_approach.single_layer: yes", out)

    def test_summary_shows_single_layer_no_for_cross_layer(self):
        """summary shows 'recommended_approach.single_layer: no' for cross-layer state."""
        tmp, devforge = self._fresh_cross_layer()
        try:
            out = self._summary(devforge)
            self.assertIn("recommended_approach.single_layer: no", out)
        finally:
            tmp.cleanup()

    def test_summary_omits_single_layer_line_for_enhancement(self):
        """Enhancement mode: summary has no 'recommended_approach.single_layer' line."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_enhancement_state(devforge)
            out = self._summary(devforge)
            self.assertNotIn("recommended_approach.single_layer", out)


# ---------------------------------------------------------------------------
# Patch 5 — unit tests for _split_path_line + _has_anchor_finding.
# ---------------------------------------------------------------------------


class TestSplitPathLine(unittest.TestCase):
    """Unit tests for _split_path_line."""

    def test_normal_path_colon_line(self):
        self.assertEqual(
            research_helper._split_path_line("src/x.ts:42"),
            ("src/x.ts", 42),
        )

    def test_sentinel_none(self):
        path, line = research_helper._split_path_line("(none)")
        self.assertEqual(path, "(none)")
        self.assertIsNone(line)

    def test_empty_string(self):
        self.assertEqual(research_helper._split_path_line(""), (None, None))

    def test_whitespace_only(self):
        self.assertEqual(research_helper._split_path_line("   "), (None, None))

    def test_no_colon(self):
        self.assertEqual(research_helper._split_path_line("src/x.ts"), (None, None))

    def test_colon_at_start(self):
        # colon_idx <= 0 → (None, None)
        self.assertEqual(research_helper._split_path_line(":42"), (None, None))

    def test_non_integer_line(self):
        self.assertEqual(research_helper._split_path_line("src/x.ts:abc"), (None, None))

    def test_path_with_multiple_colons_rfind(self):
        # rfind picks last colon
        path, line = research_helper._split_path_line("C:/src/foo.ts:10")
        self.assertEqual(path, "C:/src/foo.ts")
        self.assertEqual(line, 10)


class TestHasAnchorFinding(unittest.TestCase):
    """Unit tests for _has_anchor_finding."""

    def _finding(self, file_line, framing="primary"):
        return {"surface": "s", "file_line": file_line, "relevance": "r", "framing": framing}

    def test_exact_match(self):
        findings = [self._finding("src/x.ts:42")]
        self.assertTrue(research_helper._has_anchor_finding("src/x.ts:42", findings))

    def test_within_5_above(self):
        # target :46, finding :42 → Δ=4 ≤ 5
        findings = [self._finding("src/x.ts:42")]
        self.assertTrue(research_helper._has_anchor_finding("src/x.ts:46", findings))

    def test_within_5_below(self):
        # target :38, finding :42 → Δ=4 ≤ 5
        findings = [self._finding("src/x.ts:42")]
        self.assertTrue(research_helper._has_anchor_finding("src/x.ts:38", findings))

    def test_exactly_5_boundary(self):
        findings = [self._finding("src/x.ts:42")]
        self.assertTrue(research_helper._has_anchor_finding("src/x.ts:47", findings))

    def test_outside_5_lines(self):
        # Δ=8 > 5
        findings = [self._finding("src/x.ts:42")]
        self.assertFalse(research_helper._has_anchor_finding("src/x.ts:50", findings))

    def test_different_file_same_line(self):
        findings = [self._finding("src/x.ts:42")]
        self.assertFalse(research_helper._has_anchor_finding("src/y.ts:42", findings))

    def test_sentinel_target_never_matches(self):
        findings = [self._finding("(none)")]
        self.assertFalse(research_helper._has_anchor_finding("(none)", findings))

    def test_none_target_path_never_matches(self):
        # malformed target → False
        self.assertFalse(research_helper._has_anchor_finding("no-colon", []))

    def test_sentinel_finding_does_not_match_real_target(self):
        # (none) in findings must not match a real helper path
        findings = [self._finding("(none)")]
        self.assertFalse(research_helper._has_anchor_finding("src/x.ts:42", findings))

    def test_empty_findings_list(self):
        self.assertFalse(research_helper._has_anchor_finding("src/x.ts:42", []))


# ---------------------------------------------------------------------------
# Patch 5 — anchor gate + sticky-reject tests for record-fix-path-helper.
# ---------------------------------------------------------------------------


class TestFixPathHelperAnchorGate(unittest.TestCase):
    """Anchor gate (Patch 5): record-fix-path-helper must anchor to a finding."""

    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset-report"])
        return tmp, devforge

    def _read_report(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "read-report"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def _record_finding(self, devforge, file_line, framing="primary"):
        return _run([
            "--devforge-dir", str(devforge), "record-finding",
            "--surface", "s",
            "--file-line", file_line,
            "--relevance", "r",
            "--framing", framing,
        ])

    def _record_helper(self, devforge, helper_qn, file_line):
        return _run([
            "--devforge-dir", str(devforge), "record-fix-path-helper",
            "--helper-qn", helper_qn,
            "--file-line", file_line,
        ])

    def test_rejects_when_no_finding_anchors(self):
        """Fresh state, no findings → helper rejected; rejection_log populated."""
        tmp, devforge = self._fresh()
        try:
            r = self._record_helper(devforge, "QN_A", "src/x.ts:42")
            self.assertEqual(r.returncode, 2)
            self.assertIn("does not anchor", r.stderr)
            # Rejection log must contain the entry.
            rep = self._read_report(devforge)
            log = rep.get("helper_rejection_log") or []
            self.assertEqual(len(log), 1)
            self.assertEqual(log[0]["qn"], "QN_A")
            self.assertEqual(log[0]["file_line"], "src/x.ts:42")
        finally:
            tmp.cleanup()

    def test_accepts_exact_file_line_match(self):
        """Finding at src/x.ts:42, helper at src/x.ts:42 → exact match → exit 0."""
        tmp, devforge = self._fresh()
        try:
            self._record_finding(devforge, "src/x.ts:42")
            r = self._record_helper(devforge, "QN_A", "src/x.ts:42")
            self.assertEqual(r.returncode, 0, r.stderr)
        finally:
            tmp.cleanup()

    def test_accepts_within_5_lines_above(self):
        """Finding at src/x.ts:42, helper at src/x.ts:46 (Δ=4) → exit 0."""
        tmp, devforge = self._fresh()
        try:
            self._record_finding(devforge, "src/x.ts:42")
            r = self._record_helper(devforge, "QN_A", "src/x.ts:46")
            self.assertEqual(r.returncode, 0, r.stderr)
        finally:
            tmp.cleanup()

    def test_accepts_within_5_lines_below(self):
        """Finding at src/x.ts:42, helper at src/x.ts:38 (Δ=4) → exit 0."""
        tmp, devforge = self._fresh()
        try:
            self._record_finding(devforge, "src/x.ts:42")
            r = self._record_helper(devforge, "QN_A", "src/x.ts:38")
            self.assertEqual(r.returncode, 0, r.stderr)
        finally:
            tmp.cleanup()

    def test_rejects_outside_5_line_tolerance(self):
        """Finding at src/x.ts:42, helper at src/x.ts:50 (Δ=8) → exit 2."""
        tmp, devforge = self._fresh()
        try:
            self._record_finding(devforge, "src/x.ts:42")
            r = self._record_helper(devforge, "QN_A", "src/x.ts:50")
            self.assertEqual(r.returncode, 2)
            self.assertIn("does not anchor", r.stderr)
        finally:
            tmp.cleanup()

    def test_rejects_different_file_same_line(self):
        """Finding at src/x.ts:42, helper at src/y.ts:42 → different file → exit 2."""
        tmp, devforge = self._fresh()
        try:
            self._record_finding(devforge, "src/x.ts:42")
            r = self._record_helper(devforge, "QN_A", "src/y.ts:42")
            self.assertEqual(r.returncode, 2)
            self.assertIn("does not anchor", r.stderr)
        finally:
            tmp.cleanup()

    def test_sticky_rejects_after_post_hoc_finding(self):
        """Reject, then add finding at same path, then retry → STILL rejected (sticky).

        Closes the adversarial path where LLM records a finding post-hoc to
        unblock a rejected helper.
        """
        tmp, devforge = self._fresh()
        try:
            # Step 1: try helper with no findings → rejected.
            r1 = self._record_helper(devforge, "QN_A", "src/x.ts:42")
            self.assertEqual(r1.returncode, 2)
            self.assertIn("does not anchor", r1.stderr)

            # Step 2: add finding at the exact path.
            self._record_finding(devforge, "src/x.ts:42")

            # Step 3: retry the same (qn, file_line) combo → sticky-rejected.
            r2 = self._record_helper(devforge, "QN_A", "src/x.ts:42")
            self.assertEqual(r2.returncode, 2)
            self.assertIn("previously rejected", r2.stderr)
            self.assertIn("sticky-reject", r2.stderr)
        finally:
            tmp.cleanup()

    def test_sticky_reject_per_combo(self):
        """Sticky-reject scoped to (qn, file_line) combo — different qn or file_line is not blocked."""
        tmp, devforge = self._fresh()
        try:
            # Reject (QN_A, src/x.ts:42) — no findings yet.
            self._record_helper(devforge, "QN_A", "src/x.ts:42")
            # Add a finding far from :42 (at :60 — would normally be outside ±5).
            self._record_finding(devforge, "src/x.ts:60")

            # (QN_A, src/x.ts:60): different file_line — but check anchor first.
            # src/x.ts:60 has a finding at :60 (exact match) → should succeed.
            r2 = self._record_helper(devforge, "QN_A", "src/x.ts:60")
            self.assertEqual(r2.returncode, 0, r2.stderr)

            # (QN_B, src/x.ts:42): different qn — sticky-reject doesn't apply.
            # But no finding anchors src/x.ts:42 (finding is at :60, Δ=18 > 5) → rejected.
            r3 = self._record_helper(devforge, "QN_B", "src/x.ts:42")
            self.assertEqual(r3.returncode, 2)
            # Confirm it's the anchor error, NOT the sticky-reject error.
            self.assertIn("does not anchor", r3.stderr)
            self.assertNotIn("previously rejected", r3.stderr)
        finally:
            tmp.cleanup()

    def test_anchor_skips_none_sentinel_in_findings(self):
        """(none) in findings does not count as anchor for a real helper file_line."""
        tmp, devforge = self._fresh()
        try:
            # record-inbound-caller accepts (none) as file_line; record-finding also does.
            _run([
                "--devforge-dir", str(devforge), "record-finding",
                "--surface", "s",
                "--file-line", "(none)",
                "--relevance", "r",
            ])
            r = self._record_helper(devforge, "QN_A", "src/x.ts:42")
            self.assertEqual(r.returncode, 2)
            self.assertIn("does not anchor", r.stderr)
        finally:
            tmp.cleanup()

    def test_dedupe_still_works_after_anchor_accept(self):
        """After anchor-accepted helper, recording same (qn, file_line) again is a no-op (deduped)."""
        tmp, devforge = self._fresh()
        try:
            self._record_finding(devforge, "src/x.ts:42")
            r1 = self._record_helper(devforge, "QN_A", "src/x.ts:42")
            self.assertEqual(r1.returncode, 0, r1.stderr)
            # Second call with same qn (even different file_line) → deduped on qn.
            r2 = self._record_helper(devforge, "QN_A", "src/x.ts:42")
            self.assertEqual(r2.returncode, 0, r2.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["fix_path_helpers"]), 1)
        finally:
            tmp.cleanup()


# ---------------------------------------------------------------------------
# Patch 5 — verify check 14 tests.
# ---------------------------------------------------------------------------


class TestVerifyCheck14(unittest.TestCase):
    """Check 14: every fix_path_helpers[].file_line must anchor to a finding.

    Catches direct state mutation that bypassed the record-fix-path-helper
    anchor gate setter. Gated on bug mode.
    """

    def test_check14_passes_when_all_helpers_anchored(self):
        """_build_bug_state happy path: both helpers are anchored to findings."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("check 14", r.stderr)

    def test_check14_fails_when_helper_lacks_anchor(self):
        """Direct JSON mutation bypasses setter; unanchored helper → check 14 violation."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Insert a helper at a path with no matching finding.
            data["fix_path_helpers"].append({
                "qn": "UnanchoredHelper.method",
                "file_line": "some/novel/path.ts:999",
            })
            # Add a matching inbound_caller to satisfy check 9.
            data.setdefault("inbound_callers", []).append({
                "helper_qn": "UnanchoredHelper.method",
                "caller_qn": "SomeCaller.call",
                "file_line": "src/admin/Products.vue:201",
            })
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("check 14", r.stderr)
            self.assertIn("some/novel/path.ts:999", r.stderr)

    def test_check14_within_5_line_tolerance(self):
        """Helper at src/x.ts:46, finding at src/x.ts:42 (Δ=4) → check 14 passes."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Add finding at :46 and helper at :46 (or within ±5 of an existing finding).
            # Use pkg-shared/sort.ts:10 as base (from Patch 5 migration in _build_bug_state).
            # Add helper at pkg-shared/sort.ts:14 (Δ=4 from :10 → passes).
            data["fix_path_helpers"].append({
                "qn": "TolerantHelper.method",
                "file_line": "pkg-shared/sort.ts:14",
            })
            data.setdefault("inbound_callers", []).append({
                "helper_qn": "TolerantHelper.method",
                "caller_qn": "SomeCaller.call",
                "file_line": "src/admin/Products.vue:201",
            })
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("check 14", r.stderr)

    def test_check14_enhancement_mode_skipped(self):
        """Enhancement mode: check 14 does not fire even with unanchored helpers."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_enhancement_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Insert helpers with no matching findings (enhancement has no helpers by default).
            data["fix_path_helpers"] = [{"qn": "SomeHelper.method", "file_line": "novel/path.ts:1"}]
            data["inbound_callers"] = [{"helper_qn": "SomeHelper.method",
                                        "caller_qn": "C.m", "file_line": "novel/path.ts:1"}]
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            # Check 14 is bug-mode-gated; enhancement mode → check 14 cannot fire.
            self.assertNotIn("check 14", r.stderr)


# ---------------------------------------------------------------------------
# Patch 6 — record-data-flow-chain setter tests.
# ---------------------------------------------------------------------------


class TestRecordDataFlowChain(unittest.TestCase):
    """Round-trip + validation tests for the record-data-flow-chain setter."""

    def _fresh(self):
        """Return (TemporaryDirectory, devforge Path) with a reset report."""
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset-report"])
        return tmp, devforge

    def _read_report(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "read-report"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def _seed_finding(self, devforge, surface, relevance, file_line="src/x.ts:1"):
        _run([
            "--devforge-dir", str(devforge), "record-finding",
            "--surface", surface,
            "--file-line", file_line,
            "--relevance", relevance,
        ])

    def test_record_data_flow_chain_rejects_empty_handler_qn(self):
        """--handler-qn '' exits 2 with validation error."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "record-data-flow-chain",
                "--handler-qn", "",
                "--write-boundary-qn", "SomeRepo.save",
                "--intermediate-qns", "[]",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("handler_qn", r.stderr)
        finally:
            tmp.cleanup()

    def test_record_data_flow_chain_rejects_empty_write_boundary_qn(self):
        """--write-boundary-qn '' exits 2 with validation error."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "record-data-flow-chain",
                "--handler-qn", "SomeHandler.onClick",
                "--write-boundary-qn", "",
                "--intermediate-qns", "[]",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("write_boundary_qn", r.stderr)
        finally:
            tmp.cleanup()

    def test_record_data_flow_chain_rejects_malformed_json(self):
        """--intermediate-qns 'not json' exits 2 with JSON parse error."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "record-data-flow-chain",
                "--handler-qn", "SomeHandler.onClick",
                "--write-boundary-qn", "SomeRepo.save",
                "--intermediate-qns", "not json",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("intermediate_qns", r.stderr)
        finally:
            tmp.cleanup()

    def test_record_data_flow_chain_rejects_intermediate_without_finding(self):
        """Intermediate QN not referenced in any Finding exits 2."""
        tmp, devforge = self._fresh()
        try:
            # Seed a finding that does NOT reference qn_X.
            self._seed_finding(devforge, "Some surface", "Some relevance about foo", "src/foo.ts:1")
            r = _run([
                "--devforge-dir", str(devforge), "record-data-flow-chain",
                "--handler-qn", "SomeHandler.onClick",
                "--write-boundary-qn", "SomeRepo.save",
                "--intermediate-qns", '["qn_X"]',
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("qn_X", r.stderr)
            self.assertIn("no Finding row referencing it", r.stderr)
        finally:
            tmp.cleanup()

    def test_record_data_flow_chain_accepts_intermediate_in_relevance(self):
        """Intermediate QN found in a finding's relevance field exits 0."""
        tmp, devforge = self._fresh()
        try:
            # Seed a finding whose relevance contains qn_A.
            self._seed_finding(
                devforge,
                "Adapter surface",
                "data-flow intermediate: qn_A transforms the payload",
                "src/adapter.ts:10",
            )
            r = _run([
                "--devforge-dir", str(devforge), "record-data-flow-chain",
                "--handler-qn", "ClickHandler.handle",
                "--write-boundary-qn", "Repo.persist",
                "--intermediate-qns", '["qn_A"]',
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            chain = rep.get("data_flow_chain")
            self.assertIsNotNone(chain)
            self.assertEqual(chain["handler_qn"], "ClickHandler.handle")
            self.assertEqual(chain["write_boundary_qn"], "Repo.persist")
            self.assertEqual(chain["intermediate_qns"], ["qn_A"])
        finally:
            tmp.cleanup()

    def test_record_data_flow_chain_accepts_intermediate_in_surface(self):
        """Intermediate QN found in a finding's surface field exits 0."""
        tmp, devforge = self._fresh()
        try:
            # Seed a finding whose surface contains qn_B.
            self._seed_finding(
                devforge,
                "qn_B adapter layer",
                "Transforms payload before write",
                "src/adapters/b.ts:5",
            )
            r = _run([
                "--devforge-dir", str(devforge), "record-data-flow-chain",
                "--handler-qn", "ClickHandler.handle",
                "--write-boundary-qn", "Repo.persist",
                "--intermediate-qns", '["qn_B"]',
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            chain = rep.get("data_flow_chain")
            self.assertIsNotNone(chain)
            self.assertEqual(chain["intermediate_qns"], ["qn_B"])
        finally:
            tmp.cleanup()

    def test_record_data_flow_chain_accepts_empty_intermediates(self):
        """Empty --intermediate-qns '[]' exits 0 and persists empty list."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge), "record-data-flow-chain",
                "--handler-qn", "ClickHandler.handle",
                "--write-boundary-qn", "Repo.persist",
                "--intermediate-qns", "[]",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            chain = rep.get("data_flow_chain")
            self.assertIsNotNone(chain)
            self.assertEqual(chain["handler_qn"], "ClickHandler.handle")
            self.assertEqual(chain["write_boundary_qn"], "Repo.persist")
            self.assertEqual(chain["intermediate_qns"], [])
        finally:
            tmp.cleanup()

    def test_record_data_flow_chain_last_write_wins(self):
        """Calling record-data-flow-chain twice overwrites the prior chain."""
        tmp, devforge = self._fresh()
        try:
            # First call.
            r1 = _run([
                "--devforge-dir", str(devforge), "record-data-flow-chain",
                "--handler-qn", "HandlerA.handle",
                "--write-boundary-qn", "RepoA.save",
                "--intermediate-qns", "[]",
            ])
            self.assertEqual(r1.returncode, 0, r1.stderr)
            # Second call with different values — overwrites.
            r2 = _run([
                "--devforge-dir", str(devforge), "record-data-flow-chain",
                "--handler-qn", "HandlerB.handle",
                "--write-boundary-qn", "RepoB.save",
                "--intermediate-qns", "[]",
            ])
            self.assertEqual(r2.returncode, 0, r2.stderr)
            rep = self._read_report(devforge)
            chain = rep.get("data_flow_chain")
            self.assertIsNotNone(chain)
            # State should match the SECOND call, not the first.
            self.assertEqual(chain["handler_qn"], "HandlerB.handle")
            self.assertEqual(chain["write_boundary_qn"], "RepoB.save")
        finally:
            tmp.cleanup()

    def test_record_data_flow_chain_default_state_has_none(self):
        """Fresh default_report_state() has data_flow_chain == None."""
        rep = research_helper.default_report_state()
        self.assertIsNone(rep["data_flow_chain"])


# ---------------------------------------------------------------------------
# Patch 6 — verify check 15 tests.
# ---------------------------------------------------------------------------


class TestVerifyCheck15(unittest.TestCase):
    """Check 15: bug mode + presentation-layer primary symptom requires data_flow_chain.

    Uses _build_bug_state (which sets data_flow_chain via Patch 6 migration),
    then surgically mutates state JSON to exercise each gate condition.
    """

    def test_check_15_fires_on_bug_presentation_unset_chain(self):
        """Bug mode + presentation-layer primary finding + no chain → check 15 violation."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            # Remove data_flow_chain to simulate unset state.
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # _build_bug_state now seeds data_flow_chain — reset it to exercise the unset path.
            data["data_flow_chain"] = None
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("check 15", r.stderr)
            self.assertIn("data_flow_chain", r.stderr)

    def test_check_15_skipped_on_bug_domain_symptom(self):
        """Bug mode + domain-layer primary finding → check 15 does NOT fire."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            # Replace the primary finding's file_line with a domain-layer path
            # (packages/pkg-core/src/services/foo.ts:5 — not presentation-layer).
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # _build_bug_state now seeds data_flow_chain — reset it to exercise the unset path.
            data["data_flow_chain"] = None
            # Rewrite primary finding to a non-presentation path.
            for f in data["findings"]:
                framing = f.get("framing") or "primary"
                if framing == "primary":
                    f["file_line"] = "packages/pkg-core/src/services/foo.ts:5"
                    break
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            # Check 15 must NOT fire (other checks may fire, but not check 15).
            self.assertNotIn("check 15", r.stderr)

    def test_check_15_skipped_on_enhancement_mode(self):
        """Enhancement mode + presentation-layer finding + no chain → check 15 does NOT fire."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_enhancement_state(devforge)
            # Inject a presentation-layer finding as primary and leave chain unset.
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # data_flow_chain is None by default in enhancement state.
            # Make the first finding a presentation-layer path.
            if data["findings"]:
                data["findings"][0]["file_line"] = "apps/app/src/components/Foo.vue:5"
            data["data_flow_chain"] = None
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            # Enhancement mode → check 15 must NOT fire.
            self.assertNotIn("check 15", r.stderr)

    def test_check_15_passes_with_chain_set(self):
        """Bug mode + presentation-layer finding + data_flow_chain set → check 15 passes."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            # _build_bug_state already sets data_flow_chain; verify exits 0.
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("check 15", r.stderr)


# ---------------------------------------------------------------------------
# Patch 7: set-value-semantics stability axis + record-value-production-site
# + verify check 16 + render.
# ---------------------------------------------------------------------------


class TestSetValueSemanticsStability(unittest.TestCase):
    """Tests for the --stable-across-calls stability axis on set-value-semantics."""

    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset-report"])
        return tmp, devforge

    def _add_consumer_chain(self, devforge, value="itemId"):
        _run([
            "--devforge-dir", str(devforge),
            "record-consumer-chain",
            "--value", value,
            "--consumer-qn", "CartService.addItem",
            "--file-line", "lib/cart_service.dart:10",
            "--role", "persists id",
        ])

    def test_set_value_semantics_invariant_requires_stable_across_calls(self):
        """--classification invariant without --stable-across-calls exits 2 with 'is required' error."""
        tmp, devforge = self._fresh()
        try:
            self._add_consumer_chain(devforge)
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "itemId",
                "--classification", "invariant",
                "--evidence", "persisted in orders table",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("is required when --classification == 'invariant'", r.stderr)
        finally:
            tmp.cleanup()

    def test_set_value_semantics_invariant_unknown_rejected_on_presentation(self):
        """--stable-across-calls unknown + presentation-layer primary finding exits 2."""
        tmp, devforge = self._fresh()
        try:
            # Add a presentation-layer primary finding.
            _run([
                "--devforge-dir", str(devforge),
                "record-finding",
                "--surface", "item card component",
                "--file-line", "apps/app/src/components/Foo.vue:5",
                "--relevance", "renders item id",
            ])
            self._add_consumer_chain(devforge)
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "itemId",
                "--classification", "invariant",
                "--evidence", "server assigns once",
                "--stable-across-calls", "unknown",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("cannot be 'unknown'", r.stderr)
            self.assertIn("presentation-layer", r.stderr)
        finally:
            tmp.cleanup()

    def test_set_value_semantics_invariant_unknown_accepted_on_domain(self):
        """--stable-across-calls unknown + domain-layer primary finding exits 0 and row persisted."""
        tmp, devforge = self._fresh()
        try:
            # Add a domain-layer primary finding (not presentation).
            _run([
                "--devforge-dir", str(devforge),
                "record-finding",
                "--surface", "cart service",
                "--file-line", "packages/pkg-core/src/services/foo.ts:5",
                "--relevance", "assigns id to item",
            ])
            self._add_consumer_chain(devforge)
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "itemId",
                "--classification", "invariant",
                "--evidence", "server assigns once",
                "--stable-across-calls", "unknown",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads((devforge / "research-report.json").read_text())
            rows = [row for row in data["value_semantics"] if row["value"] == "itemId"]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["stable_across_calls"], "unknown")
        finally:
            tmp.cleanup()

    def test_set_value_semantics_invariant_false_requires_production_site(self):
        """--stable-across-calls false with no production site exits 2."""
        tmp, devforge = self._fresh()
        try:
            self._add_consumer_chain(devforge)
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "itemId",
                "--classification", "invariant",
                "--evidence", "server assigns once",
                "--stable-across-calls", "false",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("requires at least one record-value-production-site call", r.stderr)
        finally:
            tmp.cleanup()

    def test_set_value_semantics_invariant_false_accepted_after_production_site(self):
        """--stable-across-calls false + production site already recorded exits 0."""
        tmp, devforge = self._fresh()
        try:
            # Record production site first.
            _run([
                "--devforge-dir", str(devforge),
                "record-value-production-site",
                "--value", "itemId",
                "--file-line", "src/adapters/item_adapter.js:42",
                "--is-stable", "false",
            ])
            self._add_consumer_chain(devforge)
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "itemId",
                "--classification", "invariant",
                "--evidence", "adapter randomizes on each call",
                "--stable-across-calls", "false",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads((devforge / "research-report.json").read_text())
            rows = [row for row in data["value_semantics"] if row["value"] == "itemId"]
            self.assertEqual(rows[0]["stable_across_calls"], "false")
        finally:
            tmp.cleanup()

    def test_set_value_semantics_invariant_true_accepted_without_production_site(self):
        """--stable-across-calls true exits 0 without needing a production site."""
        tmp, devforge = self._fresh()
        try:
            self._add_consumer_chain(devforge)
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "itemId",
                "--classification", "invariant",
                "--evidence", "server assigns stable UUID",
                "--stable-across-calls", "true",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads((devforge / "research-report.json").read_text())
            rows = [row for row in data["value_semantics"] if row["value"] == "itemId"]
            self.assertEqual(rows[0]["stable_across_calls"], "true")
        finally:
            tmp.cleanup()

    def test_set_value_semantics_non_invariant_ignores_stability(self):
        """Non-invariant classification: --stable-across-calls is accepted but stripped from row."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "sortOrder",
                "--classification", "preference",
                "--evidence", "user sets via UI",
                "--stable-across-calls", "false",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads((devforge / "research-report.json").read_text())
            rows = [row for row in data["value_semantics"] if row["value"] == "sortOrder"]
            self.assertEqual(len(rows), 1)
            # Non-invariant rows must NOT carry stable_across_calls (keep row shape stable).
            self.assertNotIn("stable_across_calls", rows[0])
        finally:
            tmp.cleanup()


class TestRecordValueProductionSite(unittest.TestCase):
    """Tests for the record-value-production-site setter."""

    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset-report"])
        return tmp, devforge

    def _read_report(self, devforge):
        return json.loads((devforge / "research-report.json").read_text())

    def test_record_value_production_site_rejects_empty_value(self):
        """--value '' exits 2."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-value-production-site",
                "--value", "",
                "--file-line", "src/adapters/item.js:10",
                "--is-stable", "false",
            ])
            self.assertEqual(r.returncode, 2)
        finally:
            tmp.cleanup()

    def test_record_value_production_site_rejects_none_sentinel_file_line(self):
        """--file-line '(none)' exits 2."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-value-production-site",
                "--value", "itemId",
                "--file-line", "(none)",
                "--is-stable", "false",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("cannot be (none)", r.stderr)
        finally:
            tmp.cleanup()

    def test_record_value_production_site_rejects_malformed_file_line(self):
        """--file-line without colon exits 2 via _validate_file_line."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-value-production-site",
                "--value", "itemId",
                "--file-line", "no-colon-here",
                "--is-stable", "false",
            ])
            self.assertEqual(r.returncode, 2)
        finally:
            tmp.cleanup()

    def test_record_value_production_site_appends_row(self):
        """Single call appends row with correct shape {value, file_line, is_stable}."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-value-production-site",
                "--value", "itemId",
                "--file-line", "src/adapters/item.js:42",
                "--is-stable", "false",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = self._read_report(devforge)
            sites = data.get("value_production_sites", [])
            self.assertEqual(len(sites), 1)
            self.assertEqual(sites[0]["value"], "itemId")
            self.assertEqual(sites[0]["file_line"], "src/adapters/item.js:42")
            self.assertEqual(sites[0]["is_stable"], "false")
        finally:
            tmp.cleanup()

    def test_record_value_production_site_dedupes_same_value_same_file_line(self):
        """Two identical calls produce only one row (dedupe by (value, file_line))."""
        tmp, devforge = self._fresh()
        try:
            for _ in range(2):
                _run([
                    "--devforge-dir", str(devforge),
                    "record-value-production-site",
                    "--value", "itemId",
                    "--file-line", "src/adapters/item.js:42",
                    "--is-stable", "false",
                ])
            data = self._read_report(devforge)
            sites = [s for s in data["value_production_sites"] if s["value"] == "itemId"]
            self.assertEqual(len(sites), 1, "expected 1 row (deduped); got {0}".format(len(sites)))
        finally:
            tmp.cleanup()

    def test_record_value_production_site_accepts_same_value_different_file_line(self):
        """Multi-site: two calls with same value, different file_lines both append."""
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge),
                "record-value-production-site",
                "--value", "itemId",
                "--file-line", "src/adapters/item.js:42",
                "--is-stable", "false",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "record-value-production-site",
                "--value", "itemId",
                "--file-line", "src/adapters/cart.js:17",
                "--is-stable", "false",
            ])
            data = self._read_report(devforge)
            sites = [s for s in data["value_production_sites"] if s["value"] == "itemId"]
            self.assertEqual(len(sites), 2, "expected 2 rows (multi-site); got {0}".format(len(sites)))
            file_lines = {s["file_line"] for s in sites}
            self.assertIn("src/adapters/item.js:42", file_lines)
            self.assertIn("src/adapters/cart.js:17", file_lines)
        finally:
            tmp.cleanup()

    def test_record_value_production_site_accepts_same_file_line_different_values(self):
        """Two values randomized at the SAME file:line → both rows append (not deduped).

        Closes Finding 4 from python-reviewer: dedupe key is (value, file_line) AND,
        not file_line alone. Real case: an adapter rewrites two symbols (itemId +
        bqItemId) at the same line — both records must persist.
        """
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge),
                "record-value-production-site",
                "--value", "itemId",
                "--file-line", "src/adapters/item.js:42",
                "--is-stable", "false",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "record-value-production-site",
                "--value", "bqItemId",
                "--file-line", "src/adapters/item.js:42",
                "--is-stable", "false",
            ])
            data = self._read_report(devforge)
            sites = data.get("value_production_sites", [])
            self.assertEqual(len(sites), 2, "expected 2 rows for distinct values at same line")
            values = {s["value"] for s in sites}
            self.assertEqual(values, {"itemId", "bqItemId"})
        finally:
            tmp.cleanup()

    def test_record_value_production_site_default_state_has_empty_list(self):
        """fresh default_report_state has value_production_sites: []."""
        state = research_helper.default_report_state()
        self.assertIn("value_production_sites", state)
        self.assertEqual(state["value_production_sites"], [])


class TestVerifyCheck16(unittest.TestCase):
    """Tests for verify check 16: hypothesis must cite production-site file_line."""

    def _build_check16_state(self, devforge, hypothesis_cause, production_site_file_line="src/adapters/item.js:42"):
        """Build bug-mode state with an unstable value + production site + one hypothesis."""
        _build_bug_state(devforge)
        rep_path = devforge / "research-report.json"
        data = json.loads(rep_path.read_text())
        # Inject unstable value_semantics row (stable_across_calls=false).
        data.setdefault("value_semantics", []).append({
            "value": "itemId",
            "classification": "invariant",
            "evidence": "server assigns once",
            "stable_across_calls": "false",
        })
        # Inject production site.
        data.setdefault("value_production_sites", []).append({
            "value": "itemId",
            "file_line": production_site_file_line,
            "is_stable": "false",
        })
        # Overwrite hypotheses with controlled set.
        data["hypotheses"] = [
            {
                "cause": hypothesis_cause,
                "falsifier": "check if value changes per call",
                "runtime_probe_needed": False,
            },
            {
                "cause": "second hypothesis to satisfy min-2 check",
                "falsifier": "observe two sequential calls",
                "runtime_probe_needed": False,
            },
        ]
        rep_path.write_text(json.dumps(data, indent=2) + "\n")

    def test_check_16_fires_on_unstable_value_no_hypothesis_citation(self):
        """Unstable value + production site + hypothesis not citing file_line → check 16 fires."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._build_check16_state(
                devforge,
                hypothesis_cause="comparator is wrong",  # does NOT cite the production site
            )
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("check 16", r.stderr)

    def test_check_16_passes_when_hypothesis_cites_production_site(self):
        """One hypothesis cause contains the production-site file_line → check 16 passes."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._build_check16_state(
                devforge,
                hypothesis_cause="id is randomized at src/adapters/item.js:42 via Math.random()",
            )
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertNotIn("check 16", r.stderr)

    def test_check_16_skipped_when_no_unstable_values(self):
        """value_semantics has only stable rows → check 16 does NOT fire."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Only stable rows, no production sites.
            data["value_semantics"] = [
                {"value": "sortField", "classification": "invariant",
                 "evidence": "fixed by server", "stable_across_calls": "true"},
            ]
            data["value_production_sites"] = []
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertNotIn("check 16", r.stderr)

    def test_check_16_fires_on_prefix_collision_only_cite(self):
        """Hypothesis citing :50 must NOT satisfy a production site at :5 (word-boundary).

        Closes Finding 2 from python-reviewer: bare substring match would allow
        prefix collisions ("src/foo.ts:5" in "src/foo.ts:50"). Check 16 uses a
        regex lookahead (?!\\d) to require word-boundary after the line number.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._build_check16_state(
                devforge,
                production_site_file_line="src/adapters/item.js:5",
                hypothesis_cause="bug at src/adapters/item.js:50",  # prefix collision only
            )
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("check 16", r.stderr)

    def test_check_16_fires_on_unstable_value_no_production_site(self):
        """Unstable value_semantics row + EMPTY value_production_sites → check 16 fires.

        Closes Finding 5: direct JSON mutation can create stable_across_calls=false
        without a production site; the setter prevents this path but the check must
        still catch state injected via raw JSON write.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["value_semantics"] = [{
                "value": "itemId",
                "classification": "invariant",
                "evidence": "adapter assigns",
                "stable_across_calls": "false",
            }]
            data["value_production_sites"] = []
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("check 16", r.stderr)

    def test_check_16_skipped_on_enhancement_mode(self):
        """Enhancement mode + unstable value + no hypothesis citation → check 16 does NOT fire."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_enhancement_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Inject unstable row + production site + hypothesis without citation.
            data["value_semantics"] = [{
                "value": "itemId",
                "classification": "invariant",
                "evidence": "adapter assigns",
                "stable_across_calls": "false",
            }]
            data["value_production_sites"] = [{
                "value": "itemId",
                "file_line": "src/adapters/item.js:42",
                "is_stable": "false",
            }]
            # Keep existing hypotheses (none cite the production site).
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            # Enhancement mode → check 16 must NOT fire.
            self.assertNotIn("check 16", r.stderr)


class TestRenderPatch7(unittest.TestCase):
    """Tests for the Patch 7 render extensions: stability column + production sites section."""

    def _render(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "render"])
        return r.stdout

    def test_render_shows_stability_column_in_value_semantics(self):
        """Render output contains the stability column for an invariant row."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run(["--devforge-dir", str(devforge), "reset-report"])
            # Inject value_semantics with invariant + stable_across_calls directly
            # (bypassing setter for render-only test).
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["value_semantics"] = [
                {"value": "itemId", "classification": "invariant",
                 "evidence": "server assigns", "stable_across_calls": "false"},
                {"value": "sortOrder", "classification": "preference",
                 "evidence": "user choice"},
            ]
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            output = self._render(devforge)
            self.assertIn("## Value Semantics", output)
            self.assertIn("Stability", output)
            # Invariant row must show stable_across_calls value in the table cell.
            self.assertIn("| itemId | invariant | server assigns | false |", output)
            # Preference row stability column renders "—" (no stability axis applies).
            self.assertIn("| sortOrder | preference | user choice | — |", output)

    def test_render_shows_production_sites_section(self):
        """Render output contains the Value Production Sites section when rows exist."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run(["--devforge-dir", str(devforge), "reset-report"])
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["value_production_sites"] = [
                {"value": "itemId", "file_line": "src/adapters/item.js:42", "is_stable": "false"},
            ]
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            output = self._render(devforge)
            self.assertIn("## Value Production Sites", output)
            self.assertIn("src/adapters/item.js:42", output)
            self.assertIn("Is Stable", output)


# ---------------------------------------------------------------------------
# Patch 8 (V3) — literal-archaeology gate (Gap 8)
# ---------------------------------------------------------------------------


class TestDefaultReportStateLiteralArchaeology(unittest.TestCase):
    """Test 1: default_report_state() has literal_archaeology: []."""

    def test_default_report_state_has_literal_archaeology_empty_list(self):
        """fresh default_report_state has literal_archaeology: []."""
        state = research_helper.default_report_state()
        self.assertIn("literal_archaeology", state)
        self.assertEqual(state["literal_archaeology"], [])


class TestRecordLiteralArchaeology(unittest.TestCase):
    """Tests for record-literal-archaeology setter."""

    def _fresh(self):
        tmp = tempfile.TemporaryDirectory()
        devforge = Path(tmp.name) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset-memo"])
        _run(["--devforge-dir", str(devforge), "reset-report"])
        return tmp, devforge

    def _read_report(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "read-report"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def _record(self, devforge, **kwargs):
        """Convenience wrapper: call record-literal-archaeology with given kwargs."""
        defaults = {
            "literal": "false",
            "file_line": "OrderViewer.vue:290",
            "introduced_by": "cca3514",
            "introduced_when": "2023-12-12",
            "commit_subject": "DEAL-292 refactor inline call into wrapper",
            "intent": "inherited-refactor",
        }
        defaults.update(kwargs)
        return _run([
            "--devforge-dir", str(devforge),
            "record-literal-archaeology",
            "--literal", defaults["literal"],
            "--file-line", defaults["file_line"],
            "--introduced-by", defaults["introduced_by"],
            "--introduced-when", defaults["introduced_when"],
            "--commit-subject", defaults["commit_subject"],
            "--intent", defaults["intent"],
        ])

    def test_record_literal_archaeology_happy_path(self):
        """Basic call with all 6 args, intent=inherited-refactor. Row present + return 0."""
        tmp, devforge = self._fresh()
        try:
            r = self._record(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = self._read_report(devforge)
            rows = data.get("literal_archaeology", [])
            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["literal"], "false")
            self.assertEqual(row["file_line"], "OrderViewer.vue:290")
            self.assertEqual(row["introduced_by"], "cca3514")
            self.assertEqual(row["introduced_when"], "2023-12-12")
            self.assertEqual(row["commit_subject"], "DEAL-292 refactor inline call into wrapper")
            self.assertEqual(row["intent"], "inherited-refactor")
        finally:
            tmp.cleanup()

    def test_record_literal_archaeology_dedupes_same_literal_and_file_line(self):
        """Two calls with same (literal, file_line), different intent → only 1 row, original intent retained."""
        tmp, devforge = self._fresh()
        try:
            r1 = self._record(devforge, intent="inherited-refactor")
            self.assertEqual(r1.returncode, 0, r1.stderr)
            r2 = self._record(devforge, intent="deliberate")
            self.assertEqual(r2.returncode, 0, r2.stderr)
            data = self._read_report(devforge)
            rows = data.get("literal_archaeology", [])
            self.assertEqual(len(rows), 1, "expected 1 row (deduped); got {0}".format(len(rows)))
            self.assertEqual(rows[0]["intent"], "inherited-refactor", "original intent must be retained")
        finally:
            tmp.cleanup()

    def test_record_literal_archaeology_appends_when_file_line_differs(self):
        """Same literal, different file_line → 2 rows appended."""
        tmp, devforge = self._fresh()
        try:
            self._record(devforge, file_line="OrderViewer.vue:290")
            self._record(devforge, file_line="OrderViewer.vue:310")
            data = self._read_report(devforge)
            rows = data.get("literal_archaeology", [])
            self.assertEqual(len(rows), 2)
            file_lines = {r["file_line"] for r in rows}
            self.assertEqual(file_lines, {"OrderViewer.vue:290", "OrderViewer.vue:310"})
        finally:
            tmp.cleanup()

    def test_record_literal_archaeology_rejects_unrecognized_literal(self):
        """--literal arr[0] and --literal foo() are rejected with exit 2 + message."""
        tmp, devforge = self._fresh()
        try:
            for bad_lit in ("arr[0]", "foo()"):
                r = self._record(devforge, literal=bad_lit)
                self.assertEqual(r.returncode, 2, "expected exit 2 for literal {0!r}".format(bad_lit))
                self.assertIn("is not a recognizable literal token", r.stderr)
        finally:
            tmp.cleanup()

    def test_record_literal_archaeology_accepts_boolean_number_null_string_template(self):
        """All recognized primitive literal forms are accepted (return 0)."""
        tmp, devforge = self._fresh()
        try:
            for idx, lit in enumerate([
                "false", "True", "null", "undefined", "None",
                "0", "-42", "3.14", "1e-9", "0xff", "100n",
                '"hello"', "'x'", "`tmpl`",
            ]):
                # Use distinct file_line to avoid dedupe short-circuit.
                r = self._record(
                    devforge,
                    literal=lit,
                    file_line="src/foo.ts:{0}".format(10 + idx),
                )
                self.assertEqual(
                    r.returncode, 0,
                    "expected exit 0 for literal {0!r}, got {1}: {2}".format(lit, r.returncode, r.stderr),
                )
        finally:
            tmp.cleanup()

    def test_record_literal_archaeology_rejects_invalid_sha(self):
        """--introduced-by 123 (too short) and zzz1234 (non-hex) → exit 2."""
        tmp, devforge = self._fresh()
        try:
            r_short = self._record(devforge, introduced_by="123")
            self.assertEqual(r_short.returncode, 2)
            self.assertIn("7-40 char hex", r_short.stderr)

            r_nonhex = self._record(devforge, introduced_by="zzz1234")
            self.assertEqual(r_nonhex.returncode, 2)
            self.assertIn("7-40 char hex", r_nonhex.stderr)
        finally:
            tmp.cleanup()

    def test_record_literal_archaeology_rejects_invalid_date(self):
        """--introduced-when with wrong format or invalid date → exit 2."""
        tmp, devforge = self._fresh()
        try:
            r_slash = self._record(devforge, introduced_when="2026/05/18")
            self.assertEqual(r_slash.returncode, 2)
            self.assertIn("ISO date YYYY-MM-DD", r_slash.stderr)

            r_bad = self._record(devforge, introduced_when="2026-13-99")
            self.assertEqual(r_bad.returncode, 2)
            self.assertIn("ISO date YYYY-MM-DD", r_bad.stderr)
        finally:
            tmp.cleanup()

    def test_record_literal_archaeology_rejects_none_sentinel_file_line(self):
        """--file-line '(none)' → exit 2 (rejected by handler)."""
        tmp, devforge = self._fresh()
        try:
            r = self._record(devforge, file_line="(none)")
            self.assertEqual(r.returncode, 2)
        finally:
            tmp.cleanup()

    def test_record_literal_archaeology_rejects_empty_commit_subject(self):
        """--commit-subject '' → exit 2."""
        tmp, devforge = self._fresh()
        try:
            r = self._record(devforge, commit_subject="")
            self.assertEqual(r.returncode, 2)
        finally:
            tmp.cleanup()


class TestDetectLiteralReplacement(unittest.TestCase):
    """Tests for _detect_literal_replacement module-level helper."""

    def test_returns_source_literal_replace_in_call(self):
        """'replace loadData(false) with ...' → 'false'."""
        result = research_helper._detect_literal_replacement(
            "replace loadData(false) with loadData(isExternalUser.value)"
        )
        self.assertEqual(result, "false")

    def test_returns_source_literal_change_to(self):
        """'change false to isExternalUser.value at line 290' → 'false'."""
        result = research_helper._detect_literal_replacement(
            "change false to isExternalUser.value at line 290"
        )
        self.assertEqual(result, "false")

    def test_returns_source_literal_arrow(self):
        """'false -> isExternalUser.value' → 'false'."""
        result = research_helper._detect_literal_replacement("false -> isExternalUser.value")
        self.assertEqual(result, "false")

    def test_returns_source_literal_swap_for(self):
        """'swap the literal false for the identity-derived bool' → 'false'."""
        result = research_helper._detect_literal_replacement(
            "swap the literal false for the identity-derived bool"
        )
        self.assertEqual(result, "false")

    def test_returns_none_for_non_replacement_prose(self):
        """'add a new wrapper function' → None."""
        result = research_helper._detect_literal_replacement("add a new wrapper function")
        self.assertIsNone(result)

    def test_returns_none_for_empty_string(self):
        """'' → None."""
        result = research_helper._detect_literal_replacement("")
        self.assertIsNone(result)

    def test_returns_null_for_null_in_english_prose(self):
        """FP: 'null' treated as literal even in English prose ('null check').
        Documented acceptable per plan §Patch 8 ('over-matching is acceptable').
        Pinned to prevent silent regression of the documented-FP behavior.
        """
        result = research_helper._detect_literal_replacement(
            "replace the null check with an assertion"
        )
        self.assertEqual(result, "null")


class TestVerifyCheck17(unittest.TestCase):
    """Tests for verify check 17: literal-archaeology gate."""

    def _build_check17_state(self, devforge, rationale="", approach_desc=""):
        """Build a minimal bug-mode state with a recommended approach.

        Uses _build_bug_state as base, then overwrites recommended_approach
        and approaches to contain the given rationale/description.
        """
        _build_bug_state(devforge)
        rep_path = devforge / "research-report.json"
        data = json.loads(rep_path.read_text())

        # Ensure there's a finding at OrderViewer.vue:290 (anchor for archaeology).
        data["findings"].append({
            "surface": "OrderViewer component",
            "file_line": "OrderViewer.vue:290",
            "relevance": "hardcoded false literal for flag",
            "framing": "primary",
        })

        # Set approach with the given description.
        data["approaches"] = [
            {
                "name": "Fix flag literal",
                "description": approach_desc,
                "addresses_hypotheses": ["unstable comparator in inline sort"],
                "does_not_cover": [],
                "pros": ["minimal change"],
                "cons": [],
                "complexity": "Low",
            }
        ]
        data["recommended_approach"] = {
            "name": "Fix flag literal",
            "rationale": rationale,
            "hypotheses_addressed": ["unstable comparator in inline sort"],
            "hypotheses_not_covered": [],
        }
        rep_path.write_text(json.dumps(data, indent=2) + "\n")

    def test_verify_check_17_fires_when_archaeology_missing(self):
        """Bug-mode + rationale with literal-replacement + no archaeology row → check 17 fires."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._build_check17_state(
                devforge,
                rationale="replace false with isExternalUser.value",
            )
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("check 17", r.stderr)

    def test_verify_check_17_passes_when_archaeology_recorded(self):
        """Bug-mode + rationale with literal-replacement + archaeology row present → check 17 absent."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._build_check17_state(
                devforge,
                rationale="replace false with isExternalUser.value",
            )
            # Record archaeology via setter (round-trip per test_first_python_helpers).
            r = _run([
                "--devforge-dir", str(devforge),
                "record-literal-archaeology",
                "--literal", "false",
                "--file-line", "OrderViewer.vue:290",
                "--introduced-by", "cca3514",
                "--introduced-when", "2023-12-12",
                "--commit-subject", "DEAL-292 refactor inline call into wrapper",
                "--intent", "inherited-refactor",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            r_verify = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertNotIn("check 17", r_verify.stderr)

    def test_verify_check_17_silent_in_enhancement_mode(self):
        """Enhancement mode + same literal-replacement prose → check 17 does NOT fire."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_enhancement_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Add approach + recommended_approach with literal-replacement rationale.
            data["findings"].append({
                "surface": "some file",
                "file_line": "src/foo.ts:42",
                "relevance": "literal false here",
                "framing": "primary",
            })
            data["approaches"] = [
                {
                    "name": "Fix literal",
                    "description": "change false to isExternalUser.value",
                    "addresses_hypotheses": ["export speed"],
                    "does_not_cover": [],
                    "pros": [],
                    "cons": [],
                    "complexity": "Low",
                }
            ]
            data["recommended_approach"] = {
                "name": "Fix literal",
                "rationale": "change false to isExternalUser.value",
                "hypotheses_addressed": ["export speed"],
                "hypotheses_not_covered": [],
            }
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            # Enhancement mode → check 17 must NOT fire.
            self.assertNotIn("check 17", r.stderr)

    def test_verify_check_17_uses_linked_approach_description_too(self):
        """Rationale has no literal-replacement, but linked approach.description does → check 17 fires."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._build_check17_state(
                devforge,
                rationale="Fix the bug by updating the call site",  # no literal-replacement here
                approach_desc="change false to isExternalUser.value",  # literal-replacement here
            )
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("check 17", r.stderr)

    def test_verify_check_17_silent_when_no_recommended_approach(self):
        """Bug mode but no set-recommended-approach → check 17 does NOT fire."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            # Do NOT set recommended_approach — verify will emit other errors but not check 17.
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["recommended_approach"] = None
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertNotIn("check 17", r.stderr)

    def test_verify_check_17_fires_when_archaeology_at_wrong_file_line(self):
        """Archaeology row with matching literal but file_line NOT in findings → check 17 still fires.
        Cross-check on row.file_line ∈ findings[].file_line must reject wrong-location records.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._build_check17_state(
                devforge,
                rationale="replace false with isExternalUser.value",
            )
            # Record archaeology at WRONG file_line (not in findings).
            r = _run([
                "--devforge-dir", str(devforge),
                "record-literal-archaeology",
                "--literal", "false",
                "--file-line", "OtherFile.ts:10",
                "--introduced-by", "abc1234",
                "--introduced-when", "2024-01-15",
                "--commit-subject", "unrelated commit",
                "--intent", "deliberate",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            r_verify = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r_verify.returncode, 2)
            self.assertIn("check 17", r_verify.stderr)


class TestRenderPatch8(unittest.TestCase):
    """Tests for the Patch 8 render extension: Literal Archaeology section."""

    def _render(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "render"])
        return r.stdout

    def test_render_includes_literal_archaeology_section_when_present(self):
        """Render output contains ## Literal Archaeology and the row's literal value."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run(["--devforge-dir", str(devforge), "reset-report"])
            # Record 1 row via setter (round-trip).
            r = _run([
                "--devforge-dir", str(devforge),
                "record-literal-archaeology",
                "--literal", "false",
                "--file-line", "OrderViewer.vue:290",
                "--introduced-by", "cca3514",
                "--introduced-when", "2023-12-12",
                "--commit-subject", "DEAL-292 refactor inline call into wrapper",
                "--intent", "inherited-refactor",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            output = self._render(devforge)
            self.assertIn("## Literal Archaeology", output)
            self.assertIn("false", output)
            self.assertIn("OrderViewer.vue:290", output)
            self.assertIn("inherited-refactor", output)

    def test_render_omits_literal_archaeology_section_when_empty(self):
        """Fresh report state → no ## Literal Archaeology section in render output."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run(["--devforge-dir", str(devforge), "reset-report"])
            output = self._render(devforge)
            self.assertNotIn("Literal Archaeology", output)


# ---------------------------------------------------------------------------
# Patch 9 (V3) — argument-duplication shape-check (Gap 9)
# ---------------------------------------------------------------------------


class TestSplitTopLevelArgs(unittest.TestCase):
    """Tests for _split_top_level_args module-level helper."""

    def test_split_top_level_args_simple(self):
        """'a, b, c' splits into ['a', 'b', 'c']."""
        result = research_helper._split_top_level_args("a, b, c")
        self.assertEqual(result, ["a", "b", "c"])

    def test_split_top_level_args_handles_nested_parens(self):
        """'a, f(b, c), d' — nested parens don't count as split points."""
        result = research_helper._split_top_level_args("a, f(b, c), d")
        self.assertEqual(result, ["a", "f(b, c)", "d"])

    def test_split_top_level_args_returns_none_on_imbalanced(self):
        """'a, f(b, c' (unclosed paren) → None (parser failure)."""
        result = research_helper._split_top_level_args("a, f(b, c")
        self.assertIsNone(result)

    def test_split_top_level_args_empty_string(self):
        """'' → [] (no args)."""
        result = research_helper._split_top_level_args("")
        self.assertEqual(result, [])


class TestDetectArgDuplication(unittest.TestCase):
    """Tests for _detect_arg_duplication module-level helper."""

    def test_detect_arg_duplication_finds_simple_dup(self):
        """f(x, y, x) → ('x', 2)."""
        result = research_helper._detect_arg_duplication("f(x, y, x)")
        self.assertEqual(result, ("x", 2))

    def test_detect_arg_duplication_finds_dotted_dup(self):
        """f(isExternalUser.value, q, isExternalUser.value) → ('isExternalUser.value', 2)."""
        result = research_helper._detect_arg_duplication(
            "f(isExternalUser.value, q, isExternalUser.value)"
        )
        self.assertEqual(result, ("isExternalUser.value", 2))

    def test_detect_arg_duplication_finds_optional_chain_dup(self):
        """f(a?.b, c, a?.b) → ('a?.b', 2)."""
        result = research_helper._detect_arg_duplication("f(a?.b, c, a?.b)")
        self.assertEqual(result, ("a?.b", 2))

    def test_detect_arg_duplication_finds_method_call_target_dup(self):
        """Empirical flag case: isExternalUser.value passed twice."""
        result = research_helper._detect_arg_duplication(
            "orderBLoC.loadData(quoteId, isExternalUser.value, isExternalUser.value, getQuoteType, isEmeaUser.value)"
        )
        self.assertEqual(result, ("isExternalUser.value", 2))

    def test_detect_arg_duplication_returns_none_on_no_dup(self):
        """f(a, b, c) — no duplicate identifiers → None."""
        result = research_helper._detect_arg_duplication("f(a, b, c)")
        self.assertIsNone(result)

    def test_detect_arg_duplication_returns_none_on_parser_failure(self):
        """Non-call shapes and imbalanced parens → None (fail-soft)."""
        self.assertIsNone(research_helper._detect_arg_duplication("not a call"))
        self.assertIsNone(research_helper._detect_arg_duplication("f(a, b"))

    def test_detect_arg_duplication_ignores_literal_duplication(self):
        """f(0, 0) — literals don't match IDENT_CHAIN_RE → None."""
        result = research_helper._detect_arg_duplication("f(0, 0)")
        self.assertIsNone(result)

    def test_detect_arg_duplication_ignores_function_call_duplication(self):
        """f(g(), g()) — 'g()' doesn't match IDENT_CHAIN_RE → None."""
        result = research_helper._detect_arg_duplication("f(g(), g())")
        self.assertIsNone(result)

    def test_detect_arg_duplication_handles_multiline(self):
        """Multi-line call shape is normalized before match → ('a', 2)."""
        result = research_helper._detect_arg_duplication("f(\n  a,\n  b,\n  a\n)")
        self.assertEqual(result, ("a", 2))

    def test_detect_arg_duplication_returns_none_on_nested_call(self):
        """CALL_SHAPE_RE's inner `[^)]*` stops at the first `)`, so any shape
        with a nested function call in its arg list fails to match and returns
        None (fail-soft, no block). Documented limitation per CALL_SHAPE_RE
        comment block. Pinned to prevent silent regression of the documented
        nested-call fail-soft behavior.
        """
        result = research_helper._detect_arg_duplication("f(g(x), y)")
        self.assertIsNone(result)
        # Even when the nested-call shape WOULD contain duplication if parsed:
        result_dup = research_helper._detect_arg_duplication("loadData(makeId(user), value, value)")
        self.assertIsNone(result_dup)


class TestSetRecommendedApproachProposedCallShape(unittest.TestCase):
    """Patch 9 — proposed-call-shape gate on set-recommended-approach.

    When bug mode AND (--single-layer-justification set OR rationale /
    linked approach description contains literal-replacement prose),
    --proposed-call-shape is required and checked for argument duplication.
    """

    def _read_report(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "read-report"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def _add_consumer_chain(self, devforge):
        """Record a consumer_chain row so valid cites exist for single-layer scenarios."""
        _run([
            "--devforge-dir", str(devforge),
            "record-consumer-chain",
            "--value", "fetchId",
            "--consumer-qn", "FetchConsumer.handleResult",
            "--file-line", "lib/blocs/order_bloc.dart:80",
            "--role", "drives sink emission",
        ])

    def test_set_recommended_approach_requires_proposed_call_shape_when_single_layer(self):
        """Single-layer bug mode WITHOUT --proposed-call-shape → exit 2 demanding it."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_domain_single_layer_bug_state(devforge)
            self._add_consumer_chain(devforge)
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard is the minimal fix",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "Bug is local to the BLoC layer.",
                "--cites", json.dumps(["FetchConsumer.handleResult"]),
                # --proposed-call-shape deliberately omitted
            ])
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("--proposed-call-shape is required", r.stderr)

    def test_set_recommended_approach_requires_proposed_call_shape_when_literal_replacement_in_rationale(self):
        """Bug mode + literal-replacement rationale + NO --proposed-call-shape → exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Use cross-layer bug state (no single-layer gate) so only literal-replacement
            # prose in rationale triggers the Patch 9 gate.
            _build_bug_state(devforge)
            # Overwrite recommended_approach with literal-replacement rationale via direct
            # JSON write (simulates the multi-layer path where Patch 4 gate doesn't fire).
            # We call set-recommended-approach directly with literal-replacement rationale.
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option B: Move sort to derived computed + stabilize comparator",
                "--rationale", "replace false with isExternalUser.value",
                "--hypotheses-addressed", json.dumps([
                    "unstable comparator in inline sort",
                    "race between fetch and watch",
                ]),
                "--hypotheses-not-covered", json.dumps([]),
                # --proposed-call-shape deliberately omitted
            ])
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("--proposed-call-shape is required", r.stderr)

    def test_set_recommended_approach_rejects_duplicating_shape(self):
        """Single-layer + all required args + duplicating shape → exit 2 with duplication message."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_domain_single_layer_bug_state(devforge)
            self._add_consumer_chain(devforge)
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard is the minimal fix",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "Bug is local to the BLoC layer.",
                "--cites", json.dumps(["FetchConsumer.handleResult"]),
                "--proposed-call-shape",
                "orderBLoC.loadData(quoteId, isExternalUser.value, isExternalUser.value, getQuoteType, isEmeaUser.value)",
            ])
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("argument duplication", r.stderr)
            self.assertIn("isExternalUser.value", r.stderr)
            self.assertIn("appears 2 times", r.stderr)

    def test_set_recommended_approach_accepts_non_duplicating_shape(self):
        """Single-layer + non-duplicating shape → exit 0; state has proposed_call_shape."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_domain_single_layer_bug_state(devforge)
            self._add_consumer_chain(devforge)
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard is the minimal fix",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "Bug is local to the BLoC layer.",
                "--cites", json.dumps(["FetchConsumer.handleResult"]),
                "--proposed-call-shape", "loadData(quoteId, fetchId)",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = self._read_report(devforge)
            rec = data.get("recommended_approach") or {}
            self.assertEqual(rec.get("proposed_call_shape"), "loadData(quoteId, fetchId)")

    def test_set_recommended_approach_accepts_when_no_shape_required(self):
        """Bug mode + multi-layer + rationale WITHOUT literal-replacement → no shape required; exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            # Overwrite recommended_approach to ensure no literal-replacement prose in rationale.
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option B: Move sort to derived computed + stabilize comparator",
                "--rationale", "add wrapper function to centralize policy",
                "--hypotheses-addressed", json.dumps([
                    "unstable comparator in inline sort",
                    "race between fetch and watch",
                ]),
                "--hypotheses-not-covered", json.dumps([]),
                # --proposed-call-shape NOT provided
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_set_recommended_approach_stores_shape_even_on_parser_failure(self):
        """Parser fails (not a parseable call) → fail-soft → exit 0; shape stored verbatim."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_domain_single_layer_bug_state(devforge)
            self._add_consumer_chain(devforge)
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard is the minimal fix",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "Bug is local to the BLoC layer.",
                "--cites", json.dumps(["FetchConsumer.handleResult"]),
                "--proposed-call-shape", "not a parseable call shape",
            ])
            # Parser failure is advisory — no block; exit 0.
            self.assertEqual(r.returncode, 0, r.stderr)
            data = self._read_report(devforge)
            rec = data.get("recommended_approach") or {}
            self.assertEqual(rec.get("proposed_call_shape"), "not a parseable call shape")
            # Patch 9 plan §Argue: parser failure emits stderr advisory.
            self.assertIn("could not be fully parsed", r.stderr)
            self.assertIn("argument-duplication check skipped", r.stderr)

    def test_set_recommended_approach_emits_no_advisory_on_clean_parse(self):
        """Successful parse (no dup) → no stderr advisory (silent success)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_domain_single_layer_bug_state(devforge)
            self._add_consumer_chain(devforge)
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard is the minimal fix",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "Bug is local to the BLoC layer.",
                "--cites", json.dumps(["FetchConsumer.handleResult"]),
                "--proposed-call-shape", "loadData(quoteId, fetchId)",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("could not be fully parsed", r.stderr)

    def test_set_recommended_approach_skips_shape_gate_in_enhancement_mode(self):
        """Enhancement mode + literal-replacement rationale → Patch 9 gate is bug-mode only; exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_enhancement_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Enhancement state needs an approach to set recommended_approach against.
            data["approaches"] = [
                {
                    "name": "Option A: Export speed boost",
                    "description": "replace false with isExternalUser.value",
                    "addresses_hypotheses": ["export speed"],
                    "does_not_cover": [],
                    "pros": [],
                    "cons": [],
                    "complexity": "Low",
                }
            ]
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: Export speed boost",
                "--rationale", "replace false with isExternalUser.value",
                "--hypotheses-addressed", json.dumps(["export speed"]),
                "--hypotheses-not-covered", json.dumps([]),
                # --proposed-call-shape NOT provided — enhancement mode, gate should not fire
            ])
            self.assertEqual(r.returncode, 0, r.stderr)


class TestVerifyCheck18(unittest.TestCase):
    """Tests for verify check 18: argument-duplication shape check at verify time.

    Mirrors the setter gate; catches state-mutation bypass where someone
    wrote proposed_call_shape directly to JSON without going through
    set-recommended-approach.
    """

    def _build_check18_state(self, devforge, proposed_call_shape=None, mode="bug"):
        """Build a minimal bug/enhancement state with a recommended approach.

        Uses _build_check17_state pattern but writes proposed_call_shape directly
        to simulate state-mutation bypass (the gap check 18 defends against).
        """
        _build_bug_state(devforge)
        rep_path = devforge / "research-report.json"
        data = json.loads(rep_path.read_text())

        data["approaches"] = [
            {
                "name": "Fix literal",
                "description": "update the call",
                "addresses_hypotheses": ["unstable comparator in inline sort"],
                "does_not_cover": [],
                "pros": [],
                "cons": [],
                "complexity": "Low",
            }
        ]
        rec = {
            "name": "Fix literal",
            "rationale": "apply fix",
            "hypotheses_addressed": ["unstable comparator in inline sort"],
            "hypotheses_not_covered": [],
        }
        if proposed_call_shape is not None:
            rec["proposed_call_shape"] = proposed_call_shape
        data["recommended_approach"] = rec
        if mode == "enhancement":
            data["mode"] = "enhancement"
        rep_path.write_text(json.dumps(data, indent=2) + "\n")

    def test_verify_check_18_fires_when_shape_has_dup(self):
        """Bug mode + proposed_call_shape with dup written directly to JSON → check 18 fires."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._build_check18_state(
                devforge,
                proposed_call_shape=(
                    "orderBLoC.loadData(quoteId, isExternalUser.value, "
                    "isExternalUser.value, getQuoteType, isEmeaUser.value)"
                ),
            )
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("check 18", r.stderr)

    def test_verify_check_18_silent_when_no_proposed_call_shape(self):
        """Bug mode + no proposed_call_shape → check 18 does NOT fire."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._build_check18_state(devforge, proposed_call_shape=None)
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertNotIn("check 18", r.stderr)

    def test_verify_check_18_silent_when_shape_has_no_dup(self):
        """Bug mode + proposed_call_shape without dup → check 18 NOT fired."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._build_check18_state(devforge, proposed_call_shape="loadData(quoteId, fetchId)")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertNotIn("check 18", r.stderr)

    def test_verify_check_18_silent_in_enhancement_mode(self):
        """Enhancement mode + duplicating shape → check 18 NOT fired (bug-mode only)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Use _build_enhancement_state so BOTH memo and report are in enhancement mode.
            _build_enhancement_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["approaches"] = [
                {
                    "name": "Option A: Export speed boost",
                    "description": "update the call",
                    "addresses_hypotheses": ["export speed"],
                    "does_not_cover": [],
                    "pros": [],
                    "cons": [],
                    "complexity": "Low",
                }
            ]
            data["recommended_approach"] = {
                "name": "Option A: Export speed boost",
                "rationale": "apply fix",
                "hypotheses_addressed": ["export speed"],
                "hypotheses_not_covered": [],
                "proposed_call_shape": "f(x, x)",  # duplicating — but enhancement mode, gate must not fire
            }
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            # Enhancement mode — check 18 must not fire.
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertNotIn("check 18", r.stderr)


class TestRenderPatch9(unittest.TestCase):
    """Tests for the Patch 9 render extension: proposed_call_shape sub-block."""

    def _render(self, devforge):
        r = _run(["--devforge-dir", str(devforge), "render"])
        return r.stdout

    def test_render_surfaces_proposed_call_shape(self):
        """When proposed_call_shape is present, render includes it under Recommended approach."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_domain_single_layer_bug_state(devforge)
            # Record consumer_chain for valid cite.
            _run([
                "--devforge-dir", str(devforge),
                "record-consumer-chain",
                "--value", "fetchId",
                "--consumer-qn", "FetchConsumer.handleResult",
                "--file-line", "lib/blocs/order_bloc.dart:80",
                "--role", "drives sink emission",
            ])
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard is the minimal fix",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "Bug is local to the BLoC layer.",
                "--cites", json.dumps(["FetchConsumer.handleResult"]),
                "--proposed-call-shape", "loadData(quoteId, fetchId)",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            output = self._render(devforge)
            self.assertIn("**Proposed call shape:**", output)
            self.assertIn("loadData(quoteId, fetchId)", output)

    def test_render_omits_proposed_call_shape_when_absent(self):
        """When proposed_call_shape is absent from state, render omits the sub-block."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run(["--devforge-dir", str(devforge), "reset-report"])
            output = self._render(devforge)
            self.assertNotIn("Proposed call shape", output)


# ---------------------------------------------------------------------------
# finalize-handoff tests.
# ---------------------------------------------------------------------------


def _build_minimal_bug_state_for_handoff(devforge):
    """Populate minimal valid bug-mode state for finalize-handoff round-trip tests.

    Uses real CLI setters (round-trip discipline). Produces enough state to
    satisfy all required-field guards in cmd_finalize_handoff. State uses
    non-presentation-layer files so data_flow_chain is NOT required.
    """
    _run(["--devforge-dir", str(devforge), "reset-memo"])
    _run(["--devforge-dir", str(devforge), "reset-report"])

    # Phase 0: set all 6 dimensions.
    for d, val in (
        ("symptom", "Config value not applied at startup"),
        ("affected-area", "services/api/config.py"),
        ("repro-or-current", "Run server; config default used"),
        ("desired", "env var applied on startup"),
        ("scope", "one function"),
        ("unchanged-behavior", "other config keys remain unchanged"),
    ):
        _run([
            "--devforge-dir", str(devforge),
            "set-" + d, "--value", val, "--state", "Clear",
        ])

    _run(["--devforge-dir", str(devforge), "detect-mode", "--override", "bug"])
    _run(["--devforge-dir", str(devforge), "set-topic", "--value", "config-not-applied"])
    _run([
        "--devforge-dir", str(devforge), "set-verbatim-prompt",
        "--value",
        "Config value not applied at startup. Suspected cause: env var read before process env is populated by the launcher.",
    ])
    _run(["--devforge-dir", str(devforge), "set-date", "--value", "2026-05-19"])

    # Phase 1: findings, hypotheses, root cause, verify-step.
    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "config loader",
        "--file-line", "services/api/config.py:42",
        "--relevance", "reads env var but ignores None guard",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "startup init",
        "--file-line", "services/api/main.py:15",
        "--relevance", "config.load() called before env is set",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-hypothesis",
        "--cause", "env var read before process env is populated",
        "--falsifier", "add print before config.load(); verify env present",
        "--runtime-probe-needed", "yes",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-hypothesis",
        "--cause", "config key name mismatch in .env file",
        "--falsifier", "check .env key names vs config loader keys",
        "--runtime-probe-needed", "no",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-root-cause-hypothesis",
        "--value", "env var read before process env is populated on startup",
    ])
    _run(["--devforge-dir", str(devforge), "set-confidence", "--value", "Hypothesis"])
    _run(["--devforge-dir", str(devforge), "set-trigger", "--value", "server startup sequence"])
    _run([
        "--devforge-dir", str(devforge), "set-root-cause-systemic",
        "--value", "No startup-order guard for env var loading",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-verify-step",
        "--probe", "add print(os.environ.get('CONFIG_KEY')) before config.load()",
        "--reproduction", "Run server; check stdout for env value",
        "--discriminator", "if None then env not set at read time; if correct value then ordering ok",
    ])

    # Phase 2: approaches + recommended.
    _run([
        "--devforge-dir", str(devforge), "set-approach",
        "--name", "Option A: lazy load config",
        "--description", "Defer config loading until first use",
        "--addresses-hypotheses", json.dumps(["env var read before process env is populated"]),
        "--does-not-cover", json.dumps(["config key name mismatch in .env file"]),
        "--pros", json.dumps(["simple"]),
        "--cons", json.dumps(["deferred errors"]),
        "--complexity", "Low",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-approach",
        "--name", "Option B: move load to after env init",
        "--description", "Ensure env is initialized before config.load()",
        "--addresses-hypotheses", json.dumps([
            "env var read before process env is populated",
            "config key name mismatch in .env file",
        ]),
        "--does-not-cover", json.dumps([]),
        "--pros", json.dumps(["covers both", "explicit ordering"]),
        "--cons", json.dumps(["requires startup refactor"]),
        "--complexity", "Med",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-recommended-approach",
        "--name", "Option B: move load to after env init",
        "--rationale", "Explicit startup ordering prevents env-before-config race",
        "--hypotheses-addressed", json.dumps([
            "env var read before process env is populated",
        ]),
        "--hypotheses-not-covered", json.dumps(["config key name mismatch in .env file"]),
    ])
    _run([
        "--devforge-dir", str(devforge), "set-constitution-constraints",
        "--rule", "Config loading must be deterministic at startup",
        "--impact", "Prevents silent env var misses",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-complexity",
        "--codebase-changes", "Low", "--codebase-notes", "1 file",
        "--risk", "Low", "--risk-notes", "narrow change",
        "--verify-cost", "Low", "--verify-notes", "unit test suffices",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-verdict",
        "--value", "Root cause hypothesis (needs repro)",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-summary",
        "--value", "Config not applied because env is read before population. Fix: move load after env init.",
    ])

    # Phase 2.4c: fix-path-helpers for verify checks.
    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "cross-layer helper",
        "--file-line", "services/core/env_loader.py:10",
        "--relevance", "canonical env loading helper",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-fix-path-helper",
        "--helper-qn", "config.load",
        "--file-line", "services/api/config.py:42",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-fix-path-helper",
        "--helper-qn", "env_loader.init",
        "--file-line", "services/core/env_loader.py:10",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-inbound-caller",
        "--helper-qn", "config.load",
        "--caller-qn", "main.startup",
        "--file-line", "services/api/main.py:15",
    ])
    # Phase 2.3b: runner-up framing for check 12.
    _run([
        "--devforge-dir", str(devforge), "record-runner-up-framing",
        "--frame", "config key name mismatch",
        "--falsifier", "check .env key names",
        "--confidence-vs-primary", "lower",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-finding",
        "--surface", "env config key",
        "--file-line", "services/api/config.py:10",
        "--relevance", "key name cross-check for runner-up",
        "--framing", "runner-up",
    ])

    # Step 4: set-probe-feasibility (all False → no-signal fallback → tier=3, actor=user).
    _run([
        "--devforge-dir", str(devforge), "set-probe-feasibility",
        "--data-shape-only", "false",
        "--auth-required", "false",
        "--network-dependent", "false",
        "--timing-dependent", "false",
        "--is-test-code", "false",
    ])


def _run_finalize(devforge, emit_path, research_md_path=None):
    """Run finalize-handoff and return subprocess result."""
    argv = [
        "--devforge-dir", str(devforge),
        "finalize-handoff",
        "--emit-handoff-json", str(emit_path),
    ]
    if research_md_path is not None:
        argv += ["--research-md-path", research_md_path]
    return _run(argv)


class TestFinalizeHandoff(unittest.TestCase):
    """Tests for research_helper finalize-handoff subcommand."""

    def test_finalize_handoff_rejects_missing_mode(self):
        """Bare state (no detect-mode) → exit 2 with stderr memo.mode not set."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run_finalize(devforge, Path(tmp) / "handoff.json")
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("memo.mode not set", r.stderr)

    def test_finalize_handoff_rejects_missing_topic_slug(self):
        """State with mode but no topic_slug → exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            # Set mode but no topic
            _run(["--devforge-dir", str(devforge), "detect-mode", "--override", "bug"])
            r = _run_finalize(devforge, Path(tmp) / "handoff.json")
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("topic_slug not set", r.stderr)

    def test_finalize_handoff_rejects_missing_recommended_approach(self):
        """State with mode + slug but no recommended_approach → exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run(["--devforge-dir", str(devforge), "reset-report"])
            _run(["--devforge-dir", str(devforge), "detect-mode", "--override", "bug"])
            _run(["--devforge-dir", str(devforge), "set-topic", "--value", "test-topic"])
            _run(["--devforge-dir", str(devforge), "set-date", "--value", "2026-05-19"])
            r = _run_finalize(devforge, Path(tmp) / "handoff.json")
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("recommended_approach not set", r.stderr)

    def test_finalize_handoff_rejects_missing_complexity(self):
        """State with recommended_approach but no complexity → exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run(["--devforge-dir", str(devforge), "reset-report"])
            _run(["--devforge-dir", str(devforge), "detect-mode", "--override", "bug"])
            _run(["--devforge-dir", str(devforge), "set-topic", "--value", "test-topic"])
            _run(["--devforge-dir", str(devforge), "set-date", "--value", "2026-05-19"])
            # Add minimal approach + recommended.
            _run([
                "--devforge-dir", str(devforge), "set-approach",
                "--name", "Option A",
                "--description", "fix it",
                "--addresses-hypotheses", "[]",
                "--does-not-cover", "[]",
                "--pros", "[]",
                "--cons", "[]",
                "--complexity", "Low",
            ])
            _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A",
                "--rationale", "best option",
                "--hypotheses-addressed", "[]",
                "--hypotheses-not-covered", "[]",
            ])
            r = _run_finalize(devforge, Path(tmp) / "handoff.json")
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("complexity not set", r.stderr)

    def test_finalize_handoff_rejects_missing_verbatim_prompt(self):
        """State with all other required fields set but verbatim_prompt omitted -> exit 2.

        F2: required-on-write guard for verbatim_prompt must fire and identify
        the missing field in stderr. Mirrors test_finalize_handoff_rejects_missing_*.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run(["--devforge-dir", str(devforge), "reset-report"])
            _run(["--devforge-dir", str(devforge), "detect-mode", "--override", "bug"])
            _run(["--devforge-dir", str(devforge), "set-topic", "--value", "config-not-applied"])
            _run(["--devforge-dir", str(devforge), "set-date", "--value", "2026-05-19"])
            # Intentionally skip set-verbatim-prompt.
            _run([
                "--devforge-dir", str(devforge), "set-approach",
                "--name", "Option A",
                "--description", "fix it",
                "--addresses-hypotheses", "[]",
                "--does-not-cover", "[]",
                "--pros", "[]",
                "--cons", "[]",
                "--complexity", "Low",
            ])
            _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A",
                "--rationale", "best option",
                "--hypotheses-addressed", "[]",
                "--hypotheses-not-covered", "[]",
            ])
            _run([
                "--devforge-dir", str(devforge), "set-complexity",
                "--codebase-changes", "Low", "--codebase-notes", "1 file",
                "--risk", "Low", "--risk-notes", "narrow",
                "--verify-cost", "Low", "--verify-notes", "unit test",
            ])
            _run([
                "--devforge-dir", str(devforge), "set-probe-feasibility",
                "--data-shape-only", "false",
                "--auth-required", "false",
                "--network-dependent", "false",
                "--timing-dependent", "false",
                "--is-test-code", "false",
            ])
            r = _run_finalize(devforge, Path(tmp) / "handoff.json")
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("verbatim_prompt not set", r.stderr)

    def test_finalize_handoff_round_trip_bug_mode(self):
        """Write full bug-mode state via setters; run finalize-handoff; parse output JSON.

        Asserts all 7 top-level keys present and types match schema.
        F1: assert verbatim_prompt in the emitted JSON equals the FULL seeded prompt,
        NOT the topic or topic slug.
        """
        # The verbatim prompt seeded in _build_minimal_bug_state_for_handoff.
        _FULL_PROMPT = (
            "Config value not applied at startup. Suspected cause: env var read before "
            "process env is populated by the launcher."
        )
        _TOPIC_SLUG = "config-not-applied"
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("wrote:", r.stdout)
            data = json.loads(out.read_text())
            # All 7 top-level keys must be present.
            for key in ("schema_version", "research_path", "research_completed_at",
                        "mode", "intent", "spec_seeds", "plan_seeds",
                        "probe", "downstream_links"):
                self.assertIn(key, data, "missing top-level key: {0}".format(key))
            self.assertEqual(data["schema_version"], "1.1")
            self.assertEqual(data["mode"], "bug")
            self.assertIsInstance(data["intent"], dict)
            self.assertIsInstance(data["spec_seeds"], dict)
            self.assertIsInstance(data["plan_seeds"], dict)
            self.assertIsInstance(data["probe"], dict)
            self.assertIsInstance(data["downstream_links"], dict)
            self.assertIsNone(data.get("outcome"))
            # F1: integration round-trip must carry the full verbatim prompt through
            # state -> finalize-handoff -> emitted JSON. A topic-vs-prompt regression
            # (where the topic slug is emitted instead) must fail this assertion.
            self.assertEqual(
                data["intent"]["verbatim_prompt"],
                _FULL_PROMPT,
                "verbatim_prompt in emitted JSON must equal the full seeded prompt, "
                "not a paraphrased topic or slug",
            )
            self.assertNotEqual(
                data["intent"]["verbatim_prompt"],
                _TOPIC_SLUG,
                "verbatim_prompt must not be the topic slug",
            )

    def test_finalize_handoff_feature_addition_mode(self):
        """Non-bug mode (enhancement) populates spec_type_hint as feature_addition.

        research_helper MODE_ENUM uses "enhancement"; the handoff schema maps
        it to "feature_addition" (closest schema equivalent).
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run(["--devforge-dir", str(devforge), "reset-report"])
            # Use "enhancement" (actual MODE_ENUM value; "feature_addition" is schema-only).
            _run(["--devforge-dir", str(devforge), "detect-mode", "--override", "enhancement"])
            _run(["--devforge-dir", str(devforge), "set-topic", "--value", "add-export"])
            _run([
                "--devforge-dir", str(devforge), "set-verbatim-prompt",
                "--value", "Add an export endpoint to the API so users can download their data as CSV.",
            ])
            _run(["--devforge-dir", str(devforge), "set-date", "--value", "2026-05-19"])
            _run([
                "--devforge-dir", str(devforge), "set-approach",
                "--name", "Option A",
                "--description", "add export endpoint",
                "--addresses-hypotheses", "[]",
                "--does-not-cover", "[]",
                "--pros", "[]",
                "--cons", "[]",
                "--complexity", "Low",
            ])
            _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A",
                "--rationale", "minimal implementation",
                "--hypotheses-addressed", "[]",
                "--hypotheses-not-covered", "[]",
            ])
            _run([
                "--devforge-dir", str(devforge), "set-complexity",
                "--codebase-changes", "Low", "--codebase-notes", "1 endpoint",
                "--risk", "Low", "--risk-notes", "no existing deps",
                "--verify-cost", "Low", "--verify-notes", "unit test",
            ])
            # Step 4: set-probe-feasibility required before finalize-handoff.
            _run([
                "--devforge-dir", str(devforge), "set-probe-feasibility",
                "--data-shape-only", "false",
                "--auth-required", "false",
                "--network-dependent", "false",
                "--timing-dependent", "false",
                "--is-test-code", "false",
            ])
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            self.assertEqual(data["spec_seeds"]["spec_type_hint"], "feature_addition")

    def test_finalize_handoff_writes_atomically(self):
        """Emit to pre-existing file; on success file is fully replaced."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            out = Path(tmp) / "handoff.json"
            # Write sentinel content before finalize.
            out.write_text('{"old": true}')
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            # New content replaces old.
            self.assertNotIn("old", data)
            self.assertIn("schema_version", data)

    def test_finalize_handoff_creates_parent_dirs(self):
        """--emit-handoff-json with nested path → parent dirs created."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            out = Path(tmp) / "nested" / "sub" / "handoff.json"
            self.assertFalse(out.parent.exists())
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(out.exists())
            data = json.loads(out.read_text())
            self.assertIn("schema_version", data)

    def test_finalize_handoff_research_md_path_defaults(self):
        """Omit --research-md-path → derived as research/<date>-<slug>.md."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            # date=2026-05-19, slug=config-not-applied
            self.assertEqual(data["research_path"], "research/2026-05-19-config-not-applied.md")

    def test_finalize_handoff_research_md_path_explicit(self):
        """When --research-md-path is set, it's used verbatim."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out, research_md_path="research/custom-path.md")
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            self.assertEqual(data["research_path"], "research/custom-path.md")

    def test_finalize_handoff_probe_defaults_to_tier_3(self):
        """Output probe.tier == '3', actor == 'user'."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            self.assertEqual(data["probe"]["tier"], "3")
            self.assertEqual(data["probe"]["actor"], "user")
            self.assertIsNone(data["probe"]["test_framework"])
            self.assertIsNone(data["probe"]["test_path"])
            self.assertIsNone(data["probe"]["script_path"])
            self.assertFalse(data["probe"]["is_first_test_for_file"])

    def test_finalize_handoff_primary_confirms_if_from_discriminator(self):
        """verify_step discriminator string → probe.discriminator.primary_confirms_if.

        The discriminator field is the PASS/FAIL criterion (what result confirms
        primary). primary_confirms_if matches discriminator semantics, NOT probe
        (which is the action to perform). This test asserts that the discriminator
        string is carried through, not the probe string.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            disc = data["probe"]["discriminator"]
            # The discriminator set in _build_minimal_bug_state_for_handoff is:
            # "if None then env not set at read time; if correct value then ordering ok"
            primary = disc["primary_confirms_if"]
            self.assertIn("if None then env not set at read time", primary)
            # The probe string must NOT appear in primary_confirms_if.
            probe_action = "add print(os.environ.get"
            self.assertNotIn(probe_action, primary)

    def test_finalize_handoff_primary_confirms_if_fallback_when_no_discriminator(self):
        """When verify_step has no discriminator value, primary_confirms_if falls back to tbd sentinel.

        Exercises the branch where verify_step is absent (report default is None).
        Written by injecting state JSON directly because the setter requires --discriminator;
        if the field is cleared post-set, the fallback path is triggered.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            # Clear verify_step.discriminator by writing null directly to state.
            report_path = devforge / "research-report.json"
            data = json.loads(report_path.read_text())
            vs = data.get("verify_step") or {}
            vs["discriminator"] = ""
            data["verify_step"] = vs
            report_path.write_text(json.dumps(data))
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            out_data = json.loads(out.read_text())
            primary = out_data["probe"]["discriminator"]["primary_confirms_if"]
            self.assertEqual(primary, "tbd — populated by Step 4 probe-tier classifier")

    def test_finalize_handoff_constraints_all_follow_kind(self):
        """constitution_constraints rows with no anchor → mapped to follow kind."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            constraints = data["spec_seeds"]["constraints"]
            self.assertEqual(len(constraints), 1)
            self.assertEqual(constraints[0]["kind"], "follow")
            self.assertIn("deterministic", constraints[0]["content"])

    def test_finalize_handoff_alternatives_excludes_recommended(self):
        """3 approaches with one recommended → alternatives_considered has only the 2 non-recommended."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            # Add a third approach.
            _run([
                "--devforge-dir", str(devforge), "set-approach",
                "--name", "Option C: config validation layer",
                "--description", "Add validation at load time",
                "--addresses-hypotheses", "[]",
                "--does-not-cover", "[]",
                "--pros", "[]",
                "--cons", "[]",
                "--complexity", "High",
            ])
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            alts = data["plan_seeds"]["alternatives_considered"]
            # 2 non-recommended (Option A + Option C).
            self.assertEqual(len(alts), 2)
            alt_ids = [a["id"] for a in alts]
            self.assertNotIn("option_b_move_load_to_after_env_init", alt_ids)
            self.assertIn("option_a_lazy_load_config", alt_ids)
            self.assertIn("option_c_config_validation_layer", alt_ids)

    def test_finalize_handoff_v2_fields_propagate(self):
        """Write state with value_production_sites set → handoff.json has field populated."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            # Add value production site.
            _run([
                "--devforge-dir", str(devforge), "record-value-production-site",
                "--value", "config_value",
                "--file-line", "services/api/config.py:42",
                "--is-stable", "true",
            ])
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            sites = data["spec_seeds"]["value_production_sites"]
            self.assertEqual(len(sites), 1)
            self.assertEqual(sites[0]["value"], "config_value")
            self.assertEqual(sites[0]["file_line"], "services/api/config.py:42")
            self.assertTrue(sites[0]["is_stable"])

    def test_finalize_handoff_v3_fields_propagate(self):
        """Write state with literal_archaeology set → output preserves it."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            # Record literal archaeology.
            _run([
                "--devforge-dir", str(devforge), "record-literal-archaeology",
                "--literal", "42",
                "--file-line", "services/api/config.py:42",
                "--introduced-by", "abc1234",
                "--introduced-when", "2024-01-15",
                "--commit-subject", "add config loader",
                "--intent", "deliberate",
            ])
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            la = data["spec_seeds"]["literal_archaeology"]
            self.assertEqual(len(la), 1)
            self.assertEqual(la[0]["literal"], "42")
            self.assertEqual(la[0]["intent"], "deliberate")
            self.assertEqual(la[0]["introduced_by"], "abc1234")

    def test_finalize_handoff_production_site_check_when_unstable(self):
        """value_production_sites with is_stable=False → probe.discriminator.production_site_check non-null."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            # Record unstable production site.
            _run([
                "--devforge-dir", str(devforge), "record-value-production-site",
                "--value", "request_id",
                "--file-line", "services/api/config.py:55",
                "--is-stable", "false",
            ])
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            check = data["probe"]["discriminator"]["production_site_check"]
            self.assertIsNotNone(check)
            self.assertIn("services/api/config.py:55", check)

    def test_finalize_handoff_validates_via_schema(self):
        """Corrupt literal_archaeology (bad SHA) → exit 2 + stderr cites schema error.

        Also verifies atomicity: pre-existing file content is preserved when
        validation fails (the write is never committed).
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            # Directly corrupt the report state to inject a bad SHA.
            report_path = devforge / "research-report.json"
            data = json.loads(report_path.read_text())
            data["literal_archaeology"] = [{
                "literal": "42",
                "file_line": "services/api/config.py:42",
                "introduced_by": "NOTASHA",  # invalid SHA
                "introduced_when": "2024-01-15",
                "commit_subject": "add config",
                "intent": "deliberate",
            }]
            report_path.write_text(json.dumps(data))
            out = Path(tmp) / "handoff.json"
            # Write sentinel content so we can verify it's preserved on failure.
            out.write_text('{"old_sentinel": true}\n')
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("schema validation failed", r.stderr)
            self.assertEqual(json.loads(out.read_text()), {"old_sentinel": True})

    def test_finalize_handoff_downstream_links_empty(self):
        """downstream_links has all None/empty fields on fresh output."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            dl = data["downstream_links"]
            self.assertIsNone(dl["spec_path"])
            self.assertIsNone(dl["plan_path"])
            self.assertEqual(dl["execute_task_commit_shas"], [])

    def test_finalize_handoff_rejects_partial_recommended_approach(self):
        """recommended_approach dict missing 'name' key → exit 2 + stderr names the fields."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            # Mutate report: replace recommended_approach with one missing 'name'.
            report_path = devforge / "research-report.json"
            data = json.loads(report_path.read_text())
            data["recommended_approach"] = {"rationale": "x"}
            report_path.write_text(json.dumps(data))
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("missing 'name' or 'rationale'", r.stderr)

    def test_finalize_handoff_cited_patterns_resolves_to_file_line(self):
        """cite token matching a consumer_chain.consumer_qn → file_line resolves to that row's path:line.

        Uses the single-layer Dart BLoC fixture so that --cites is accepted by
        set-recommended-approach. Records a consumer_chain row with
        consumer_qn='FetchConsumer.handleResult' + file_line='lib/blocs/order_bloc.dart:80'.
        Uses 'FetchConsumer.handleResult' as the cite token. Finalize must carry
        the resolved file_line through to cited_canonical_patterns[].file_line.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Build single-layer bug state (all helpers in lib/blocs — non-presentation).
            _build_domain_single_layer_bug_state(devforge)

            # Record a consumer_chain row so the cite token resolves to a real file_line.
            _run([
                "--devforge-dir", str(devforge),
                "record-consumer-chain",
                "--value", "fetchId",
                "--consumer-qn", "FetchConsumer.handleResult",
                "--file-line", "lib/blocs/order_bloc.dart:80",
                "--role", "drives sink emission",
            ])

            # Set recommended approach with single-layer-justification + cite pointing
            # to the consumer_chain row. proposed-call-shape required in bug mode + justification.
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard closes the race",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in loadData"]),
                "--hypotheses-not-covered", json.dumps(["subscription resubscribed mid-stream"]),
                "--single-layer-justification", "Bug is local to the BLoC layer; FetchConsumer confirms layer boundary.",
                "--cites", json.dumps(["FetchConsumer.handleResult"]),
                "--proposed-call-shape", "loadData(quoteId, fetchId)",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

            # Step 4: set-probe-feasibility required before finalize-handoff.
            _run([
                "--devforge-dir", str(devforge), "set-probe-feasibility",
                "--data-shape-only", "false",
                "--auth-required", "false",
                "--network-dependent", "false",
                "--timing-dependent", "false",
                "--is-test-code", "false",
            ])

            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            patterns = data["plan_seeds"]["cited_canonical_patterns"]
            self.assertEqual(len(patterns), 1)
            self.assertEqual(patterns[0]["qn"], "FetchConsumer.handleResult")
            # file_line must resolve to the consumer_chain row's file_line, not the cite token.
            self.assertEqual(patterns[0]["file_line"], "lib/blocs/order_bloc.dart:80")

    def test_finalize_handoff_rejects_missing_date(self):
        """State with mode + topic but no date → exit 2 + stderr names the field."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run(["--devforge-dir", str(devforge), "reset-report"])
            _run(["--devforge-dir", str(devforge), "detect-mode", "--override", "bug"])
            _run(["--devforge-dir", str(devforge), "set-topic", "--value", "test-topic"])
            # No set-date call → date guard fires.
            r = _run_finalize(devforge, Path(tmp) / "handoff.json")
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("report.date not set", r.stderr)

    # -------------------------------------------------------------------
    # Plan 67 D6 — caller-enumeration handoff carry.
    # -------------------------------------------------------------------

    def test_finalize_handoff_carries_caller_enumeration_verbatim(self):
        """fix_path_helpers + inbound_callers recorded at /research ride the
        handoff verbatim -- plan 67 D6 (the plan-66 seam).

        _build_minimal_bug_state_for_handoff records two fix_path_helpers
        (config.load, env_loader.init) and one inbound_callers row (for
        config.load only). Asserts the exact rows, not just presence, and
        that env_loader.init (with zero recorded callers) is not fabricated
        an entry.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            ce = data["plan_seeds"]["caller_enumeration"]
            self.assertEqual(
                ce["fix_path_helpers"],
                [
                    {"qn": "config.load", "file_line": "services/api/config.py:42"},
                    {"qn": "env_loader.init", "file_line": "services/core/env_loader.py:10"},
                ],
            )
            self.assertEqual(
                ce["inbound_callers"],
                [
                    {
                        "helper_qn": "config.load",
                        "caller_qn": "main.startup",
                        "file_line": "services/api/main.py:15",
                    },
                ],
            )
            self.assertIsNone(ce["no_shared_callers_justification"])

    def test_finalize_handoff_carries_no_shared_callers_justification(self):
        """The check-8 escape path (record-no-shared-callers-justification
        instead of any fix-path helper) carries the justification text and
        an empty fix_path_helpers/inbound_callers list.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_enhancement_state_no_callers(devforge)
            r = _run([
                "--devforge-dir", str(devforge), "record-no-shared-callers-justification",
                "--justification",
                "purely additive new endpoint module; no existing helper touched",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            ce = data["plan_seeds"]["caller_enumeration"]
            self.assertEqual(ce["fix_path_helpers"], [])
            self.assertEqual(ce["inbound_callers"], [])
            self.assertEqual(
                ce["no_shared_callers_justification"],
                "purely additive new endpoint module; no existing helper touched",
            )

    def test_finalize_handoff_caller_enumeration_empty_when_neither_recorded(self):
        """Neither Phase 2.4c path recorded -> caller_enumeration is the empty
        shape (all fields empty/None), never fabricated. This is the
        pre-plan-67-shaped state (a report where the LLM recorded neither
        helpers nor the escape).
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_enhancement_state_no_callers(devforge)
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            ce = data["plan_seeds"]["caller_enumeration"]
            self.assertEqual(ce, {
                "fix_path_helpers": [],
                "inbound_callers": [],
                "no_shared_callers_justification": None,
            })


def _build_minimal_enhancement_state_no_callers(devforge):
    """Populate minimal valid enhancement-mode state for finalize-handoff,
    recording neither fix_path_helpers nor the no-shared-callers escape.

    Shared by the caller-enumeration carry tests above (mirrors
    test_finalize_handoff_feature_addition_mode's setup).
    """
    _run(["--devforge-dir", str(devforge), "reset-memo"])
    _run(["--devforge-dir", str(devforge), "reset-report"])
    _run(["--devforge-dir", str(devforge), "detect-mode", "--override", "enhancement"])
    _run(["--devforge-dir", str(devforge), "set-topic", "--value", "add-export"])
    _run([
        "--devforge-dir", str(devforge), "set-verbatim-prompt",
        "--value", "Add an export endpoint to the API so users can download their data as CSV.",
    ])
    _run(["--devforge-dir", str(devforge), "set-date", "--value", "2026-05-19"])
    _run([
        "--devforge-dir", str(devforge), "set-approach",
        "--name", "Option A",
        "--description", "add export endpoint",
        "--addresses-hypotheses", "[]",
        "--does-not-cover", "[]",
        "--pros", "[]",
        "--cons", "[]",
        "--complexity", "Low",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-recommended-approach",
        "--name", "Option A",
        "--rationale", "minimal implementation",
        "--hypotheses-addressed", "[]",
        "--hypotheses-not-covered", "[]",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-complexity",
        "--codebase-changes", "Low", "--codebase-notes", "1 endpoint",
        "--risk", "Low", "--risk-notes", "no existing deps",
        "--verify-cost", "Low", "--verify-notes", "unit test",
    ])
    _run([
        "--devforge-dir", str(devforge), "set-probe-feasibility",
        "--data-shape-only", "false",
        "--auth-required", "false",
        "--network-dependent", "false",
        "--timing-dependent", "false",
        "--is-test-code", "false",
    ])


_INIT_HELPER_PY = _LIB_DIR / "init_helper.py"


def _run_init(argv, cwd=None):
    """Run init_helper.py with argv; capture stdout/stderr/exit."""
    return subprocess.run(
        [sys.executable, str(_INIT_HELPER_PY)] + list(argv),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_init_yaml_with_test_infra(devforge_dir, frontend=None, backend=None, e2e=None, status="present"):
    """Write .devforge/init.yaml with a given test_infra shape via init_helper CLI.

    Round-trips through the real producer (init_helper CLI) per
    feedback_test_first_python_helpers: tests must not hand-craft fixtures that
    bypass the producer. Uses DEVFORGE_DIR env var (init_helper's redirect
    mechanism) + set-test-infra subcommand to write the correct YAML shape.
    """
    devforge_path = Path(devforge_dir)
    devforge_path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_path)

    def _run_init_env(argv):
        return subprocess.run(
            [sys.executable, str(_INIT_HELPER_PY)] + list(argv),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    # Reset to fresh init state.
    r = _run_init_env(["reset"])
    if r.returncode != 0:
        raise RuntimeError("init_helper reset failed: {0}".format(r.stderr))
    # Set test_infra via the set-test-infra subcommand.
    argv = [
        "set-test-infra",
        "--status", status,
        "--frontend", frontend if frontend else "null",
        "--backend", backend if backend else "null",
        "--e2e", e2e if e2e else "null",
    ]
    r = _run_init_env(argv)
    if r.returncode != 0:
        raise RuntimeError("init_helper set-test-infra failed: {0}".format(r.stderr))
    return devforge_path / "init.yaml"


class TestSetProbeFeasibility(unittest.TestCase):
    """Step 4 — set-probe-feasibility subcommand tests."""

    def test_set_probe_feasibility_round_trip(self):
        """All five flags accepted, state populated correctly as Python bools."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-report"])
            r = _run([
                "--devforge-dir", str(devforge), "set-probe-feasibility",
                "--data-shape-only", "true",
                "--auth-required", "false",
                "--network-dependent", "false",
                "--timing-dependent", "false",
                "--is-test-code", "false",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            # Verify state via read-report.
            r2 = _run(["--devforge-dir", str(devforge), "read-report"])
            self.assertEqual(r2.returncode, 0, r2.stderr)
            data = json.loads(r2.stdout)
            feas = data["probe_feasibility"]
            self.assertIs(feas["data_shape_only"], True)
            self.assertIs(feas["auth_required"], False)
            self.assertIs(feas["network_dependent"], False)
            self.assertIs(feas["timing_dependent"], False)
            self.assertIs(feas["is_test_code"], False)

    def test_set_probe_feasibility_rejects_non_boolean_string(self):
        """--data-shape-only maybe → exit 2 + enum cite."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-report"])
            r = _run([
                "--devforge-dir", str(devforge), "set-probe-feasibility",
                "--data-shape-only", "maybe",
                "--auth-required", "false",
                "--network-dependent", "false",
                "--timing-dependent", "false",
                "--is-test-code", "false",
            ])
            # argparse choices validation fires before handler, exit 2.
            self.assertNotEqual(r.returncode, 0, "should have failed")
            # The error should mention the invalid choice.
            self.assertTrue(
                "maybe" in r.stderr or "invalid choice" in r.stderr,
                "stderr: {0}".format(r.stderr)
            )

    def test_set_probe_feasibility_accepts_lowercase_canonical(self):
        """Argparse choices are exact match; only lowercase 'true' / 'false' accepted."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-report"])
            # argparse choices are exact match; "True" won't match "true".
            # Test with lowercase (canonical).
            r = _run([
                "--devforge-dir", str(devforge), "set-probe-feasibility",
                "--data-shape-only", "false",
                "--auth-required", "true",
                "--network-dependent", "false",
                "--timing-dependent", "true",
                "--is-test-code", "false",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            r2 = _run(["--devforge-dir", str(devforge), "read-report"])
            data = json.loads(r2.stdout)
            feas = data["probe_feasibility"]
            self.assertIs(feas["auth_required"], True)
            self.assertIs(feas["timing_dependent"], True)

    def test_default_report_state_has_probe_feasibility_all_none(self):
        """default_report_state() includes probe_feasibility with all-None defaults."""
        state = research_helper.default_report_state()
        feas = state.get("probe_feasibility")
        self.assertIsInstance(feas, dict)
        for key in ("data_shape_only", "auth_required", "network_dependent",
                    "timing_dependent", "is_test_code"):
            self.assertIn(key, feas)
            self.assertIsNone(feas[key])


class TestProbeTierClassifier(unittest.TestCase):
    """Step 4 — _classify_probe_tier() + full finalize-handoff pipeline tests."""

    def test_finalize_rejects_when_probe_feasibility_missing(self):
        """Full bug-mode state minus set-probe-feasibility → exit 2 + stderr 'probe_feasibility incomplete'."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            # Corrupt the probe_feasibility back to all-None to simulate missing set.
            report_path = devforge / "research-report.json"
            data = json.loads(report_path.read_text())
            data["probe_feasibility"] = {
                "data_shape_only": None,
                "auth_required": None,
                "network_dependent": None,
                "timing_dependent": None,
                "is_test_code": None,
            }
            report_path.write_text(json.dumps(data))
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("probe_feasibility incomplete", r.stderr)
            self.assertIn("set-probe-feasibility", r.stderr)

    def test_probe_tier_3_when_is_test_code(self):
        """feasibility.is_test_code=True → tier='3', actor='user' (circular-test-code gate)."""
        result = research_helper._classify_probe_tier(
            feasibility={"data_shape_only": False, "auth_required": False,
                         "network_dependent": False, "timing_dependent": False,
                         "is_test_code": True},
            test_infra_status="present",
            chrome_mcp=True,  # even with chrome_mcp, test_code forces tier=3
            test_infra={"frontend": "vitest", "backend": None, "e2e": None, "status": "present"},
            topic_slug="my-probe",
            research_date="2026-05-19",
        )
        self.assertEqual(result["tier"], "3")
        self.assertEqual(result["actor"], "user")
        self.assertIsNone(result["test_framework"])
        self.assertIsNone(result["test_path"])

    def test_probe_tier_1_when_data_shape_only_and_test_infra_present(self):
        """data_shape_only=True + test_infra.status=present + vitest in frontend → tier='1', test_framework='vitest', test_path includes '.spec.ts'."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            # Override feasibility to data_shape_only=True, others False.
            _run([
                "--devforge-dir", str(devforge), "set-probe-feasibility",
                "--data-shape-only", "true",
                "--auth-required", "false",
                "--network-dependent", "false",
                "--timing-dependent", "false",
                "--is-test-code", "false",
            ])
            # Write init.yaml with vitest as frontend framework.
            _write_init_yaml_with_test_infra(devforge, frontend="vitest", status="present")
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            probe = data["probe"]
            self.assertEqual(probe["tier"], "1")
            self.assertEqual(probe["actor"], "llm")
            self.assertEqual(probe["test_framework"], "vitest")
            self.assertIn(".spec.ts", probe["test_path"])
            self.assertIn("config-not-applied", probe["test_path"])
            self.assertTrue(probe["is_first_test_for_file"])

    def test_probe_tier_1_5_when_data_shape_only_and_test_infra_absent(self):
        """data_shape_only=True + test_infra.status=absent → tier='1.5', script_path populated, test_framework=None."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            # Override feasibility to data_shape_only=True.
            _run([
                "--devforge-dir", str(devforge), "set-probe-feasibility",
                "--data-shape-only", "true",
                "--auth-required", "false",
                "--network-dependent", "false",
                "--timing-dependent", "false",
                "--is-test-code", "false",
            ])
            # Write init.yaml with status=absent (no frameworks).
            _write_init_yaml_with_test_infra(devforge, status="absent")
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            probe = data["probe"]
            self.assertEqual(probe["tier"], "1.5")
            self.assertEqual(probe["actor"], "llm")
            self.assertIsNone(probe["test_framework"])
            self.assertIsNone(probe["test_path"])
            self.assertIn("probe-script.mjs", probe["script_path"])
            self.assertIn("config-not-applied", probe["script_path"])

    def test_probe_tier_2_when_auth_required_and_chrome_mcp(self):
        """feasibility.auth_required=True + env DEVFORGE_CHROME_MCP_AVAILABLE=1 → tier='2', actor='llm'."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            _run([
                "--devforge-dir", str(devforge), "set-probe-feasibility",
                "--data-shape-only", "false",
                "--auth-required", "true",
                "--network-dependent", "false",
                "--timing-dependent", "false",
                "--is-test-code", "false",
            ])
            out = Path(tmp) / "handoff.json"
            env = os.environ.copy()
            env["DEVFORGE_CHROME_MCP_AVAILABLE"] = "1"
            r = subprocess.run(
                [sys.executable, str(_HELPER_PY),
                 "--devforge-dir", str(devforge),
                 "finalize-handoff",
                 "--emit-handoff-json", str(out)],
                capture_output=True, text=True, check=False, env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            probe = data["probe"]
            self.assertEqual(probe["tier"], "2")
            self.assertEqual(probe["actor"], "llm")

    def test_probe_tier_3_when_auth_required_and_no_chrome_mcp(self):
        """feasibility.auth_required=True + no env var → tier='3', actor='user'."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            _run([
                "--devforge-dir", str(devforge), "set-probe-feasibility",
                "--data-shape-only", "false",
                "--auth-required", "true",
                "--network-dependent", "false",
                "--timing-dependent", "false",
                "--is-test-code", "false",
            ])
            out = Path(tmp) / "handoff.json"
            env = os.environ.copy()
            env.pop("DEVFORGE_CHROME_MCP_AVAILABLE", None)
            r = subprocess.run(
                [sys.executable, str(_HELPER_PY),
                 "--devforge-dir", str(devforge),
                 "finalize-handoff",
                 "--emit-handoff-json", str(out)],
                capture_output=True, text=True, check=False, env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            probe = data["probe"]
            self.assertEqual(probe["tier"], "3")
            self.assertEqual(probe["actor"], "user")

    def test_probe_tier_3_when_no_feasibility_signal(self):
        """All five booleans False (no specific signal) → tier='3', actor='user' (fallback)."""
        result = research_helper._classify_probe_tier(
            feasibility={"data_shape_only": False, "auth_required": False,
                         "network_dependent": False, "timing_dependent": False,
                         "is_test_code": False},
            test_infra_status=None,
            chrome_mcp=False,
            test_infra=None,
            topic_slug="no-signal",
            research_date="2026-05-19",
        )
        self.assertEqual(result["tier"], "3")
        self.assertEqual(result["actor"], "user")
        self.assertIsNone(result["test_framework"])
        self.assertIsNone(result["test_path"])
        self.assertIsNone(result["script_path"])

    def test_probe_tier_1_demotes_to_1_5_when_test_infra_present_but_empty_buckets(self):
        """test_infra.status=present but all buckets None → demotes to tier='1.5' (inconsistent state)."""
        result = research_helper._classify_probe_tier(
            feasibility={"data_shape_only": True, "auth_required": False,
                         "network_dependent": False, "timing_dependent": False,
                         "is_test_code": False},
            test_infra_status="present",
            chrome_mcp=False,
            test_infra={"frontend": None, "backend": None, "e2e": None, "status": "present"},
            topic_slug="empty-buckets",
            research_date="2026-05-19",
        )
        # Demoted because no recognizable framework found.
        self.assertEqual(result["tier"], "1.5")
        self.assertIn("probe-script.mjs", result["script_path"])
        self.assertIsNone(result["test_framework"])

    def test_finalize_writes_classified_probe_to_handoff_json(self):
        """Full pipeline: set-probe-feasibility (all False) + finalize → output JSON has probe.tier='3'."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            probe = data["probe"]
            self.assertEqual(probe["tier"], "3")
            self.assertEqual(probe["actor"], "user")
            # feasibility_check should have all booleans set.
            fc = probe["feasibility_check"]
            self.assertIs(fc["data_shape_only"], False)
            self.assertIs(fc["auth_required"], False)
            self.assertIs(fc["network_dependent"], False)
            self.assertIs(fc["timing_dependent"], False)
            self.assertIs(fc["is_test_code"], False)

    def test_chrome_mcp_default_false_when_env_unset(self):
        """env var absent → tier-2-eligible feasibility downgrades to tier=3."""
        # Direct function call with chrome_mcp=False (simulates no env var).
        result = research_helper._classify_probe_tier(
            feasibility={"data_shape_only": False, "auth_required": True,
                         "network_dependent": False, "timing_dependent": False,
                         "is_test_code": False},
            test_infra_status=None,
            chrome_mcp=False,  # no env var
            test_infra=None,
            topic_slug="auth-probe",
            research_date="2026-05-19",
        )
        self.assertEqual(result["tier"], "3")
        self.assertEqual(result["actor"], "user")

    def test_test_path_extension_maps_per_framework(self):
        """Parametrized over 6 schema-valid frameworks: vitest→.spec.ts, pytest→.py,
        cargo-test→.rs, go-test→_test.go, rspec→_spec.rb, jest→.spec.ts."""
        cases = [
            ("vitest", "present", "frontend", ".spec.ts"),
            ("pytest", "present", "backend", ".py"),
            ("cargo-test", "present", "backend", ".rs"),
            ("go-test", "present", "backend", "_test.go"),
            ("rspec", "present", "backend", "_spec.rb"),
            ("jest", "present", "frontend", ".spec.ts"),
        ]
        for framework, status, bucket, expected_ext in cases:
            test_infra = {"frontend": None, "backend": None, "e2e": None, "status": status}
            test_infra[bucket] = framework
            result = research_helper._classify_probe_tier(
                feasibility={"data_shape_only": True, "auth_required": False,
                             "network_dependent": False, "timing_dependent": False,
                             "is_test_code": False},
                test_infra_status=status,
                chrome_mcp=False,
                test_infra=test_infra,
                topic_slug="my-feature",
                research_date="2026-05-19",
            )
            self.assertEqual(result["tier"], "1", "framework={0}".format(framework))
            self.assertIn(
                expected_ext, result["test_path"],
                "framework={0} expected ext={1} in path={2}".format(
                    framework, expected_ext, result["test_path"]
                ),
            )

    def test_probe_feasibility_round_trip_via_finalize(self):
        """feasibility flags set, finalize emits, output handoff.json.probe.feasibility_check has same boolean values."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            # Override just data_shape_only and timing_dependent to True.
            _run([
                "--devforge-dir", str(devforge), "set-probe-feasibility",
                "--data-shape-only", "true",
                "--auth-required", "false",
                "--network-dependent", "false",
                "--timing-dependent", "true",
                "--is-test-code", "false",
            ])
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            fc = data["probe"]["feasibility_check"]
            self.assertIs(fc["data_shape_only"], True)
            self.assertIs(fc["auth_required"], False)
            self.assertIs(fc["network_dependent"], False)
            self.assertIs(fc["timing_dependent"], True)
            self.assertIs(fc["is_test_code"], False)
            # timing_dependent=True prevents clean tier=1 classification → tier=3 fallback.
            self.assertEqual(data["probe"]["tier"], "3")

    def test_discriminator_runner_up_populated_for_tier_1_5(self):
        """tier=1.5 → runner_up_confirms_if cites LLM evaluation, both_disproved_if cites test passes."""
        result = research_helper._classify_probe_tier(
            feasibility={"data_shape_only": True, "auth_required": False,
                         "network_dependent": False, "timing_dependent": False,
                         "is_test_code": False},
            test_infra_status="absent",
            chrome_mcp=False,
            test_infra=None,
            topic_slug="slug",
            research_date="2026-05-19",
        )
        self.assertEqual(result["tier"], "1.5")
        self.assertIn("LLM", result["runner_up_confirms_if"])
        self.assertIn("PASSES", result["both_disproved_if"])

    def test_discriminator_runner_up_tbd_for_tier_3(self):
        """tier=3 → runner_up_confirms_if='tbd — manual observation required'."""
        result = research_helper._classify_probe_tier(
            feasibility={"data_shape_only": False, "auth_required": False,
                         "network_dependent": False, "timing_dependent": False,
                         "is_test_code": False},
            test_infra_status=None,
            chrome_mcp=False,
            test_infra=None,
            topic_slug="slug",
            research_date="2026-05-19",
        )
        self.assertEqual(result["tier"], "3")
        self.assertIn("manual observation", result["runner_up_confirms_if"])


class TestRecordProbeScript(unittest.TestCase):
    """Step 5 — record-probe-script subcommand tests."""

    # ------------------------------------------------------------------
    # Fixture helpers
    # ------------------------------------------------------------------

    def _setup_state_for_probe_script(self, devforge):
        """Build minimal state (date + topic_slug) needed for record-probe-script."""
        _run(["--devforge-dir", str(devforge), "reset-memo"])
        _run(["--devforge-dir", str(devforge), "reset-report"])
        _run(["--devforge-dir", str(devforge), "set-topic", "--value", "probe-test-bug"])
        _run(["--devforge-dir", str(devforge), "set-date", "--value", "2026-05-19"])

    def _make_script_file(self, research_dir, filename="probe-script.mjs"):
        """Create the research/<date>-<slug>/ directory and a script file in it."""
        research_dir.mkdir(parents=True, exist_ok=True)
        script = research_dir / filename
        script.write_text("// probe script\nconsole.log('hello');\n")
        return script

    # ------------------------------------------------------------------
    # Test 1: happy path round-trip
    # ------------------------------------------------------------------

    def test_record_probe_script_round_trip(self):
        """Script exists under research/<date>-<slug>/, runtime=node on PATH, valid inlines-from
        → exit 0, probe_scripts populated with correct fields."""
        import shutil as _shutil
        if _shutil.which("node") is None:
            self.skipTest("node not on PATH — skipping round-trip test")
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_state_for_probe_script(devforge)
            research_dir = Path(tmp) / "research" / "2026-05-19-probe-test-bug"
            script = self._make_script_file(research_dir)
            r = _run([
                "--devforge-dir", str(devforge),
                "record-probe-script",
                "--script-path", str(script),
                "--runtime", "node",
                "--inlines-from", '["src/foo.ts:42", "src/bar.ts:7"]',
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            # Verify state persisted.
            r2 = _run(["--devforge-dir", str(devforge), "read-report"])
            self.assertEqual(r2.returncode, 0, r2.stderr)
            report = json.loads(r2.stdout)
            self.assertEqual(len(report["probe_scripts"]), 1)
            entry = report["probe_scripts"][0]
            self.assertEqual(entry["script_path"], str(script))
            self.assertEqual(entry["runtime"], "node")
            self.assertEqual(entry["inlines_from"], ["src/foo.ts:42", "src/bar.ts:7"])
            self.assertIn("recorded_at", entry)
            # recorded_at should be an ISO-format timestamp ending in 'Z' or '+00:00'
            self.assertRegex(entry["recorded_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    # ------------------------------------------------------------------
    # Test 2: script outside research dir
    # ------------------------------------------------------------------

    def test_record_probe_script_rejects_script_outside_research_dir(self):
        """Script at /tmp path → exit 2, stderr cites 'script-path must exist'."""
        import shutil as _shutil
        if _shutil.which("node") is None:
            self.skipTest("node not on PATH")
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_state_for_probe_script(devforge)
            # Create a script OUTSIDE the research dir.
            outside_script = Path(tmp) / "probe-script.mjs"
            outside_script.write_text("// outside\n")
            r = _run([
                "--devforge-dir", str(devforge),
                "record-probe-script",
                "--script-path", str(outside_script),
                "--runtime", "node",
                "--inlines-from", '["src/foo.ts:1"]',
            ])
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("script-path must exist", r.stderr)

    # ------------------------------------------------------------------
    # Test 3: missing script file (correct dir prefix, file absent)
    # ------------------------------------------------------------------

    def test_record_probe_script_rejects_missing_script_file(self):
        """script-path under correct dir but file does not exist → exit 2, stderr
        cites 'file does not exist' (distinct from the structural-rejection message)."""
        import shutil as _shutil
        if _shutil.which("node") is None:
            self.skipTest("node not on PATH")
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_state_for_probe_script(devforge)
            # Build the path prefix but don't create the file.
            research_dir = Path(tmp) / "research" / "2026-05-19-probe-test-bug"
            research_dir.mkdir(parents=True, exist_ok=True)
            nonexistent = research_dir / "probe-script.mjs"
            r = _run([
                "--devforge-dir", str(devforge),
                "record-probe-script",
                "--script-path", str(nonexistent),
                "--runtime", "node",
                "--inlines-from", '["src/foo.ts:1"]',
            ])
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("file does not exist", r.stderr)

    # ------------------------------------------------------------------
    # Test 4: runtime not on PATH (bogus value within argparse choices)
    # ------------------------------------------------------------------

    def test_record_probe_script_rejects_runtime_not_on_path(self):
        """Runtime 'bun' assumed not on PATH in CI — if it IS on PATH, skip gracefully."""
        import shutil as _shutil
        # 'bun' is the least-likely runtime to be installed.
        if _shutil.which("bun") is not None:
            self.skipTest("bun is on PATH on this machine — skip not-on-PATH test")
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_state_for_probe_script(devforge)
            research_dir = Path(tmp) / "research" / "2026-05-19-probe-test-bug"
            script = self._make_script_file(research_dir)
            r = _run([
                "--devforge-dir", str(devforge),
                "record-probe-script",
                "--script-path", str(script),
                "--runtime", "bun",
                "--inlines-from", '["src/foo.ts:1"]',
            ])
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("not found on PATH", r.stderr)

    # ------------------------------------------------------------------
    # Test 5: invalid --inlines-from JSON
    # ------------------------------------------------------------------

    def test_record_probe_script_rejects_invalid_inlines_from_json(self):
        """--inlines-from 'not json' → exit 2, stderr cites format requirement."""
        import shutil as _shutil
        if _shutil.which("node") is None:
            self.skipTest("node not on PATH")
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_state_for_probe_script(devforge)
            research_dir = Path(tmp) / "research" / "2026-05-19-probe-test-bug"
            script = self._make_script_file(research_dir)
            r = _run([
                "--devforge-dir", str(devforge),
                "record-probe-script",
                "--script-path", str(script),
                "--runtime", "node",
                "--inlines-from", "not json",
            ])
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("path:line", r.stderr)

    # ------------------------------------------------------------------
    # Test 6: empty --inlines-from array
    # ------------------------------------------------------------------

    def test_record_probe_script_rejects_empty_inlines_from(self):
        """--inlines-from '[]' → exit 2."""
        import shutil as _shutil
        if _shutil.which("node") is None:
            self.skipTest("node not on PATH")
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_state_for_probe_script(devforge)
            research_dir = Path(tmp) / "research" / "2026-05-19-probe-test-bug"
            script = self._make_script_file(research_dir)
            r = _run([
                "--devforge-dir", str(devforge),
                "record-probe-script",
                "--script-path", str(script),
                "--runtime", "node",
                "--inlines-from", "[]",
            ])
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("non-empty", r.stderr)

    # ------------------------------------------------------------------
    # Test 7: --inlines-from contains non-path:line token
    # ------------------------------------------------------------------

    def test_record_probe_script_rejects_inlines_from_non_path_line(self):
        """--inlines-from '["just a string"]' → exit 2 (no colon+digit suffix)."""
        import shutil as _shutil
        if _shutil.which("node") is None:
            self.skipTest("node not on PATH")
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_state_for_probe_script(devforge)
            research_dir = Path(tmp) / "research" / "2026-05-19-probe-test-bug"
            script = self._make_script_file(research_dir)
            r = _run([
                "--devforge-dir", str(devforge),
                "record-probe-script",
                "--script-path", str(script),
                "--runtime", "node",
                "--inlines-from", '["just a string"]',
            ])
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("path:line", r.stderr)

    # ------------------------------------------------------------------
    # Test 8: idempotent — same script_path is a no-op
    # ------------------------------------------------------------------

    def test_record_probe_script_idempotent_same_path(self):
        """Two calls with identical script_path + runtime + inlines_from → second call
        no-op (exit 0), stderr contains '(exact match)', probe_scripts has exactly one
        entry (strict-match idempotency)."""
        import shutil as _shutil
        if _shutil.which("node") is None:
            self.skipTest("node not on PATH")
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_state_for_probe_script(devforge)
            research_dir = Path(tmp) / "research" / "2026-05-19-probe-test-bug"
            script = self._make_script_file(research_dir)
            argv = [
                "--devforge-dir", str(devforge),
                "record-probe-script",
                "--script-path", str(script),
                "--runtime", "node",
                "--inlines-from", '["src/foo.ts:1"]',
            ]
            r1 = _run(argv)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            r2 = _run(argv)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertIn("already recorded", r2.stderr)
            self.assertIn("(exact match)", r2.stderr)
            # Only one entry.
            r3 = _run(["--devforge-dir", str(devforge), "read-report"])
            report = json.loads(r3.stdout)
            self.assertEqual(len(report["probe_scripts"]), 1)

    # ------------------------------------------------------------------
    # Test 9: append distinct paths
    # ------------------------------------------------------------------

    def test_record_probe_script_appends_distinct_paths(self):
        """Two calls with different script_path → both entries in probe_scripts list."""
        import shutil as _shutil
        if _shutil.which("node") is None:
            self.skipTest("node not on PATH")
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_state_for_probe_script(devforge)
            research_dir = Path(tmp) / "research" / "2026-05-19-probe-test-bug"
            script_a = self._make_script_file(research_dir, "probe-script-a.mjs")
            script_b = self._make_script_file(research_dir, "probe-script-b.mjs")
            _run([
                "--devforge-dir", str(devforge),
                "record-probe-script",
                "--script-path", str(script_a),
                "--runtime", "node",
                "--inlines-from", '["src/foo.ts:1"]',
            ])
            _run([
                "--devforge-dir", str(devforge),
                "record-probe-script",
                "--script-path", str(script_b),
                "--runtime", "node",
                "--inlines-from", '["src/bar.ts:99"]',
            ])
            r = _run(["--devforge-dir", str(devforge), "read-report"])
            report = json.loads(r.stdout)
            self.assertEqual(len(report["probe_scripts"]), 2)
            paths = [e["script_path"] for e in report["probe_scripts"]]
            self.assertIn(str(script_a), paths)
            self.assertIn(str(script_b), paths)

    # ------------------------------------------------------------------
    # Test 10: finalize-handoff uses recorded script_path when tier=1.5
    # ------------------------------------------------------------------

    def test_finalize_handoff_uses_recorded_script_path_when_tier_1_5(self):
        """tier=1.5 feasibility + record-probe-script → finalize-handoff output
        probe.script_path matches the recorded value (not the deterministic default)."""
        import shutil as _shutil
        if _shutil.which("node") is None:
            self.skipTest("node not on PATH")
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            # Override feasibility to data_shape_only=True → tier=1.5 (no test infra).
            _run([
                "--devforge-dir", str(devforge), "set-probe-feasibility",
                "--data-shape-only", "true",
                "--auth-required", "false",
                "--network-dependent", "false",
                "--timing-dependent", "false",
                "--is-test-code", "false",
            ])
            # Ensure test_infra is absent so tier=1.5 is chosen.
            _write_init_yaml_with_test_infra(devforge, status="absent")
            # Create the probe script file in the research dir.
            # _build_minimal_bug_state_for_handoff uses date=2026-05-19, slug=config-not-applied.
            research_dir = Path(tmp) / "research" / "2026-05-19-config-not-applied"
            research_dir.mkdir(parents=True, exist_ok=True)
            custom_script = research_dir / "my-custom-probe.mjs"
            custom_script.write_text("// custom probe\n")
            _run([
                "--devforge-dir", str(devforge),
                "record-probe-script",
                "--script-path", str(custom_script),
                "--runtime", "node",
                "--inlines-from", '["services/api/config.py:42"]',
            ])
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            probe = data["probe"]
            self.assertEqual(probe["tier"], "1.5")
            self.assertEqual(probe["script_path"], str(custom_script),
                             "script_path should be the recorded value, not the deterministic default")

    # ------------------------------------------------------------------
    # Test 11: finalize-handoff defaults script_path when no probe_script recorded
    # ------------------------------------------------------------------

    def test_finalize_handoff_defaults_script_path_when_no_recorded(self):
        """tier=1.5 feasibility + NO record-probe-script → finalize-handoff output
        probe.script_path uses deterministic default 'research/<date>-<slug>/probe-script.mjs'."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            # Override feasibility to data_shape_only=True.
            _run([
                "--devforge-dir", str(devforge), "set-probe-feasibility",
                "--data-shape-only", "true",
                "--auth-required", "false",
                "--network-dependent", "false",
                "--timing-dependent", "false",
                "--is-test-code", "false",
            ])
            # Ensure test_infra is absent so tier=1.5 is chosen.
            _write_init_yaml_with_test_infra(devforge, status="absent")
            # Do NOT call record-probe-script.
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(out.read_text())
            probe = data["probe"]
            self.assertEqual(probe["tier"], "1.5")
            self.assertIn("probe-script.mjs", probe["script_path"])
            self.assertIn("config-not-applied", probe["script_path"])

    # ------------------------------------------------------------------
    # Test 12: accepts python runtime (skips gracefully if python absent)
    # ------------------------------------------------------------------

    def test_record_probe_script_accepts_python_runtime(self):
        """runtime=python → exit 0 if python is on PATH; skip gracefully otherwise."""
        import shutil as _shutil
        if _shutil.which("python") is None:
            self.skipTest("python not on PATH — skipping python-runtime test")
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_state_for_probe_script(devforge)
            research_dir = Path(tmp) / "research" / "2026-05-19-probe-test-bug"
            script = self._make_script_file(research_dir, "probe-script.py")
            r = _run([
                "--devforge-dir", str(devforge),
                "record-probe-script",
                "--script-path", str(script),
                "--runtime", "python",
                "--inlines-from", '["src/module.py:10"]',
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            r2 = _run(["--devforge-dir", str(devforge), "read-report"])
            report = json.loads(r2.stdout)
            self.assertEqual(len(report["probe_scripts"]), 1)
            self.assertEqual(report["probe_scripts"][0]["runtime"], "python")

    # ------------------------------------------------------------------
    # Test 13: F2 — subdir path rejected (direct-child-only enforcement)
    # ------------------------------------------------------------------

    def test_record_probe_script_rejects_subdir_path(self):
        """script-path file exists but lives in research/<date>-<slug>/subdir/
        (not a direct child of the date-slug dir) → exit 2, stderr 'script-path must'.
        Locks the 'direct child only' structural invariant."""
        import shutil as _shutil
        if _shutil.which("node") is None:
            self.skipTest("node not on PATH")
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_state_for_probe_script(devforge)
            # Create file inside a *subdir* of the date-slug dir.
            subdir = (
                Path(tmp) / "research" / "2026-05-19-probe-test-bug" / "subdir"
            )
            subdir.mkdir(parents=True, exist_ok=True)
            script = subdir / "probe.mjs"
            script.write_text("// nested probe\n")
            r = _run([
                "--devforge-dir", str(devforge),
                "record-probe-script",
                "--script-path", str(script),
                "--runtime", "node",
                "--inlines-from", '["src/foo.ts:1"]',
            ])
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("script-path must", r.stderr)

    # ------------------------------------------------------------------
    # Test 14: F3 — same path, different runtime → error (strict-match)
    # ------------------------------------------------------------------

    def test_record_probe_script_rejects_same_path_different_runtime(self):
        """First call records script_path with runtime=node; second call with same
        script_path but runtime=python → exit 2, stderr 'different runtime'.
        Strict-match idempotency prevents silent overwrite."""
        import shutil as _shutil
        if _shutil.which("node") is None:
            self.skipTest("node not on PATH")
        if _shutil.which("python") is None:
            self.skipTest("python not on PATH")
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_state_for_probe_script(devforge)
            research_dir = Path(tmp) / "research" / "2026-05-19-probe-test-bug"
            script = self._make_script_file(research_dir)
            base_argv = [
                "--devforge-dir", str(devforge),
                "record-probe-script",
                "--script-path", str(script),
                "--inlines-from", '["src/foo.ts:1"]',
            ]
            r1 = _run(base_argv + ["--runtime", "node"])
            self.assertEqual(r1.returncode, 0, r1.stderr)
            r2 = _run(base_argv + ["--runtime", "python"])
            self.assertEqual(r2.returncode, 2, r2.stderr)
            self.assertIn("different runtime", r2.stderr)
            # State must be unchanged: exactly one entry with runtime=node.
            r3 = _run(["--devforge-dir", str(devforge), "read-report"])
            report = json.loads(r3.stdout)
            self.assertEqual(len(report["probe_scripts"]), 1)
            self.assertEqual(report["probe_scripts"][0]["runtime"], "node")


# ---------------------------------------------------------------------------
# Step 7 — append-outcome + check-outcome tests.
# ---------------------------------------------------------------------------


def _build_tier1_handoff(devforge, tmp_root):
    # type: (Path, str) -> Path
    """Produce a tier-1 handoff.json via real CLI producers.

    Requires:
    - _build_minimal_bug_state_for_handoff (full bug state)
    - set-probe-feasibility with data_shape_only=true
    - _write_init_yaml_with_test_infra with frontend=vitest, status=present

    Returns the path to the written handoff.json.
    """
    _build_minimal_bug_state_for_handoff(devforge)
    _run([
        "--devforge-dir", str(devforge), "set-probe-feasibility",
        "--data-shape-only", "true",
        "--auth-required", "false",
        "--network-dependent", "false",
        "--timing-dependent", "false",
        "--is-test-code", "false",
    ])
    _write_init_yaml_with_test_infra(devforge, frontend="vitest", status="present")
    out = Path(tmp_root) / "handoff.json"
    r = _run_finalize(devforge, out)
    if r.returncode != 0:
        raise RuntimeError("finalize-handoff failed: {0}".format(r.stderr))
    return out


def _build_tier3_handoff(devforge, tmp_root):
    # type: (Path, str) -> Path
    """Produce a tier-3 handoff.json via real CLI producers (default feasibility flags).

    Returns the path to the written handoff.json.
    """
    _build_minimal_bug_state_for_handoff(devforge)
    # _build_minimal_bug_state_for_handoff already sets all-false probe feasibility → tier=3.
    out = Path(tmp_root) / "handoff.json"
    r = _run_finalize(devforge, out)
    if r.returncode != 0:
        raise RuntimeError("finalize-handoff failed: {0}".format(r.stderr))
    return out


def _run_append_outcome(handoff_path, hypothesis_confirmed, evidence_source, evidence_cite,
                        actual_fix_path, delta=None, commit_sha=None):
    # type: (str, str, str, str, str, str, str) -> object
    """Run append-outcome and return subprocess result."""
    argv = [
        "append-outcome",
        "--handoff-path", handoff_path,
        "--hypothesis-confirmed", hypothesis_confirmed,
        "--evidence-source", evidence_source,
        "--evidence-cite", evidence_cite,
        "--actual-fix-path", actual_fix_path,
    ]
    if delta is not None:
        argv += ["--delta-from-recommendation", delta]
    if commit_sha is not None:
        argv += ["--confirmed-commit-sha", commit_sha]
    return _run(argv)


def _run_check_outcome(handoff_path):
    # type: (str) -> object
    """Run check-outcome and return subprocess result."""
    return _run(["check-outcome", "--handoff-path", handoff_path])


class TestAppendOutcome(unittest.TestCase):
    """Tests for research_helper append-outcome subcommand (Step 7)."""

    def test_append_outcome_round_trip_high_confidence_tier_1(self):
        """tier=1 + evidence-source=test-result + hypothesis=primary → confidence_grade=HIGH.

        Real-producer fixture: finalize-handoff with data_shape_only=true + vitest → tier=1.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            handoff_path = _build_tier1_handoff(devforge, tmp)
            r = _run_append_outcome(
                str(handoff_path),
                hypothesis_confirmed="primary",
                evidence_source="test-result",
                evidence_cite="tests/research/config-not-applied.probe.spec.ts:42",
                actual_fix_path="services/api/main.py",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("HIGH", r.stdout)
            data = json.loads(handoff_path.read_text())
            outcome = data["outcome"]
            self.assertIsNotNone(outcome)
            self.assertEqual(outcome["hypothesis_confirmed"], "primary")
            self.assertEqual(outcome["evidence_source"], "test-result")
            self.assertEqual(outcome["confidence_grade"], "HIGH")

    def test_append_outcome_low_confidence_tier_3(self):
        """tier=3 + evidence-source=user-observation → confidence_grade=LOW.

        Real-producer fixture: default all-false feasibility → tier=3.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            handoff_path = _build_tier3_handoff(devforge, tmp)
            r = _run_append_outcome(
                str(handoff_path),
                hypothesis_confirmed="primary",
                evidence_source="user-observation",
                evidence_cite="User confirmed fix in browser",
                actual_fix_path="services/api/config.py:42",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("LOW", r.stdout)
            data = json.loads(handoff_path.read_text())
            self.assertEqual(data["outcome"]["confidence_grade"], "LOW")

    def test_append_outcome_inconclusive_tier_1_5_yields_medium(self):
        """tier=1.5 + test-result + hypothesis=inconclusive → MEDIUM.

        Real-producer: data_shape_only=true + test_infra absent → tier=1.5.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            _run([
                "--devforge-dir", str(devforge), "set-probe-feasibility",
                "--data-shape-only", "true",
                "--auth-required", "false",
                "--network-dependent", "false",
                "--timing-dependent", "false",
                "--is-test-code", "false",
            ])
            # No init.yaml → test_infra absent → tier=1.5.
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            # Verify tier is actually 1.5.
            probe_tier = json.loads(out.read_text())["probe"]["tier"]
            self.assertEqual(probe_tier, "1.5")

            r = _run_append_outcome(
                str(out),
                hypothesis_confirmed="inconclusive",
                evidence_source="test-result",
                evidence_cite="tests/probe-script-output.txt",
                actual_fix_path="services/api/config.py",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("MEDIUM", r.stdout)
            data = json.loads(out.read_text())
            self.assertEqual(data["outcome"]["confidence_grade"], "MEDIUM")

    def test_append_outcome_idempotent_overwrites_handoff_block(self):
        """First append; second append with different evidence-source → handoff.outcome reflects 2nd call."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            handoff_path = _build_tier3_handoff(devforge, tmp)
            # First append.
            r1 = _run_append_outcome(
                str(handoff_path),
                hypothesis_confirmed="primary",
                evidence_source="user-observation",
                evidence_cite="First observation",
                actual_fix_path="services/api/config.py",
            )
            self.assertEqual(r1.returncode, 0, r1.stderr)
            data1 = json.loads(handoff_path.read_text())
            self.assertEqual(data1["outcome"]["evidence_source"], "user-observation")

            # Second append with different evidence-source.
            r2 = _run_append_outcome(
                str(handoff_path),
                hypothesis_confirmed="runner_up",
                evidence_source="llm-ui-session-log",
                evidence_cite="session-log-2026-05-19.txt",
                actual_fix_path="services/api/config.py",
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)
            data2 = json.loads(handoff_path.read_text())
            # Second call overwrites; evidence_source is from 2nd call.
            self.assertEqual(data2["outcome"]["evidence_source"], "llm-ui-session-log")
            self.assertEqual(data2["outcome"]["hypothesis_confirmed"], "runner_up")

    def test_append_outcome_appends_md_outcome_section(self):
        """Create md file at handoff.research_path; append-outcome → md gets '## Outcome' section."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            handoff_path = _build_tier3_handoff(devforge, tmp)
            data = json.loads(handoff_path.read_text())

            # Create the md file at research_path, resolved relative to the handoff dir.
            # append-outcome resolves research_path against handoff dir (F4), so we must
            # create the file at the same resolved location.
            research_path = data.get("research_path")
            if research_path:
                md_path = (handoff_path.parent / research_path).resolve()
            else:
                # If research_path is None in the handoff, inject one so we can test.
                # Use a sibling .md file in the same dir.
                md_path = handoff_path.parent / "research.md"
                data["research_path"] = "research.md"
                handoff_path.write_text(json.dumps(data, indent=2) + "\n")
            md_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text("# Research Report\n\nContent here.\n")

            r = _run_append_outcome(
                str(handoff_path),
                hypothesis_confirmed="primary",
                evidence_source="user-observation",
                evidence_cite="Verified manually",
                actual_fix_path="services/api/config.py",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            md_content = md_path.read_text()
            self.assertIn("## Outcome", md_content)
            self.assertIn("hypothesis_confirmed", md_content)
            self.assertIn("confidence_grade", md_content)

    def test_append_outcome_skips_md_when_md_missing(self):
        """No md file at research_path → outcome still written to handoff.json + exit 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            handoff_path = _build_tier3_handoff(devforge, tmp)
            # Ensure no md file exists for the research_path.
            data = json.loads(handoff_path.read_text())
            # Set research_path to a non-existent file.
            data["research_path"] = str(Path(tmp) / "nonexistent" / "research.md")
            handoff_path.write_text(json.dumps(data, indent=2) + "\n")

            r = _run_append_outcome(
                str(handoff_path),
                hypothesis_confirmed="none",
                evidence_source="user-observation",
                evidence_cite="No evidence found",
                actual_fix_path="services/api/config.py",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            # handoff.json has outcome.
            data_after = json.loads(handoff_path.read_text())
            self.assertIsNotNone(data_after.get("outcome"))
            # No md file was created.
            self.assertFalse(Path(data["research_path"]).exists())

    def test_append_outcome_rejects_invalid_evidence_source_enum(self):
        """--evidence-source bogus → argparse choices reject → exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            handoff_path = _build_tier3_handoff(devforge, tmp)
            r = _run([
                "append-outcome",
                "--handoff-path", str(handoff_path),
                "--hypothesis-confirmed", "primary",
                "--evidence-source", "bogus-source",
                "--evidence-cite", "some cite",
                "--actual-fix-path", "some/path.py",
            ])
            self.assertNotEqual(r.returncode, 0)
            # argparse emits 'invalid choice' or the value name.
            self.assertTrue(
                "bogus-source" in r.stderr or "invalid choice" in r.stderr,
                "stderr: {0}".format(r.stderr)
            )

    def test_append_outcome_rejects_invalid_hypothesis_confirmed_enum(self):
        """--hypothesis-confirmed bogus → argparse choices reject → exit non-0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            handoff_path = _build_tier3_handoff(devforge, tmp)
            r = _run([
                "append-outcome",
                "--handoff-path", str(handoff_path),
                "--hypothesis-confirmed", "definitely",
                "--evidence-source", "user-observation",
                "--evidence-cite", "some cite",
                "--actual-fix-path", "some/path.py",
            ])
            self.assertNotEqual(r.returncode, 0)
            self.assertTrue(
                "definitely" in r.stderr or "invalid choice" in r.stderr,
                "stderr: {0}".format(r.stderr)
            )

    def test_append_outcome_rejects_bad_commit_sha(self):
        """--confirmed-commit-sha 'NOTHEX' → Outcome schema validator rejects (hex 7-40 char)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            handoff_path = _build_tier3_handoff(devforge, tmp)
            r = _run_append_outcome(
                str(handoff_path),
                hypothesis_confirmed="primary",
                evidence_source="user-observation",
                evidence_cite="Verified manually",
                actual_fix_path="services/api/config.py",
                commit_sha="NOTHEX",
            )
            self.assertEqual(r.returncode, 2, "expected exit 2, got {0}: {1}".format(
                r.returncode, r.stderr))
            self.assertIn("sha", r.stderr.lower())

    def test_append_outcome_writes_confirmed_date_iso_utc(self):
        """outcome.confirmed_date is a parseable ISO-8601 datetime."""
        import datetime as _dt
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            handoff_path = _build_tier3_handoff(devforge, tmp)
            r = _run_append_outcome(
                str(handoff_path),
                hypothesis_confirmed="primary",
                evidence_source="user-observation",
                evidence_cite="User saw fix work",
                actual_fix_path="services/api/config.py",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(handoff_path.read_text())
            confirmed_date = data["outcome"]["confirmed_date"]
            # Must parse as ISO-8601; strptime with UTC suffix.
            try:
                _dt.datetime.strptime(confirmed_date, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                self.fail(
                    "confirmed_date {0!r} is not ISO-8601 UTC format".format(confirmed_date)
                )

    def test_append_outcome_medium_grade_production_site_check_with_user_observation(self):
        """tier=3 + is_stable=False + hypothesis=primary + user-observation → MEDIUM.

        Grade rule: production_site_check present + primary confirmed + non-test-result → MEDIUM.
        Real-producer fixture: _build_minimal_bug_state_for_handoff + record-value-production-site
        (is_stable=false) → finalize-handoff populates probe.discriminator.production_site_check
        non-None → append-outcome computes MEDIUM.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_minimal_bug_state_for_handoff(devforge)
            # Record unstable production site before finalize → production_site_check non-None.
            # Use a non-presentation-layer path (no .ts/.tsx/.vue/.jsx/.svelte/.html) so
            # data_flow_chain is not required by the schema invariant.
            _run([
                "--devforge-dir", str(devforge), "record-value-production-site",
                "--value", "request_id",
                "--file-line", "services/api/config.py:55",
                "--is-stable", "false",
            ])
            out = Path(tmp) / "handoff.json"
            r = _run_finalize(devforge, out)
            self.assertEqual(r.returncode, 0, r.stderr)
            # Confirm production_site_check is non-None in the produced handoff.
            data = json.loads(out.read_text())
            self.assertIsNotNone(
                data["probe"]["discriminator"]["production_site_check"],
                "precondition: finalize-handoff must set production_site_check",
            )
            r = _run_append_outcome(
                str(out),
                hypothesis_confirmed="primary",
                evidence_source="user-observation",
                evidence_cite="User confirmed fix in browser",
                actual_fix_path="src/x.ts",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("MEDIUM", r.stdout)
            data = json.loads(out.read_text())
            self.assertEqual(data["outcome"]["confidence_grade"], "MEDIUM")

    def test_append_outcome_md_gets_two_sections_on_double_call(self):
        """Two sequential append-outcome calls each append '## Outcome' to the md file.

        After two calls, the md file must contain exactly two '## Outcome' headings.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            handoff_path = _build_tier3_handoff(devforge, tmp)
            data = json.loads(handoff_path.read_text())

            # Inject a research_path pointing to a file we control.
            md_path = handoff_path.parent / "research.md"
            md_path.write_text("# Research Report\n\nContent here.\n")
            data["research_path"] = str(md_path)
            handoff_path.write_text(json.dumps(data, indent=2) + "\n")

            # First append-outcome call.
            r1 = _run_append_outcome(
                str(handoff_path),
                hypothesis_confirmed="primary",
                evidence_source="user-observation",
                evidence_cite="First observation",
                actual_fix_path="services/api/config.py",
            )
            self.assertEqual(r1.returncode, 0, r1.stderr)

            # Second append-outcome call (overwrites handoff.json block; appends to md).
            r2 = _run_append_outcome(
                str(handoff_path),
                hypothesis_confirmed="runner_up",
                evidence_source="user-observation",
                evidence_cite="Second observation",
                actual_fix_path="services/api/config.py",
            )
            self.assertEqual(r2.returncode, 0, r2.stderr)

            md_content = md_path.read_text()
            count = md_content.count("## Outcome")
            self.assertEqual(
                count, 2,
                "Expected 2 '## Outcome' sections in md, got {0}. Content:\n{1}".format(
                    count, md_content
                ),
            )

    def test_append_outcome_resolves_relative_research_md_path(self):
        """research_path stored as relative name → resolved against handoff dir, not cwd.

        Build handoff at /tmp/test/handoff.json with research_path='report.md'.
        Create file at /tmp/test/report.md.
        chdir to a DIFFERENT dir and invoke append-outcome.
        Assert md was found and appended.
        """
        import subprocess as _sp
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            handoff_path = _build_tier3_handoff(devforge, tmp)
            data = json.loads(handoff_path.read_text())

            # Store a relative research_path (just a filename, no directory component).
            md_path = handoff_path.parent / "report.md"
            md_path.write_text("# Report\n\nBody.\n")
            data["research_path"] = "report.md"
            handoff_path.write_text(json.dumps(data, indent=2) + "\n")

            # Run from a completely different directory (the system tmp root).
            other_cwd = tempfile.gettempdir()
            result = _sp.run(
                [
                    sys.executable, str(_HELPER_PY),
                    "append-outcome",
                    "--handoff-path", str(handoff_path),
                    "--hypothesis-confirmed", "primary",
                    "--evidence-source", "user-observation",
                    "--evidence-cite", "Verified in browser",
                    "--actual-fix-path", "services/api/config.py",
                ],
                cwd=other_cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            md_content = md_path.read_text()
            self.assertIn("## Outcome", md_content,
                          "md file should have been found + appended via relative path resolution")


class TestCheckOutcome(unittest.TestCase):
    """Tests for research_helper check-outcome subcommand (Step 7)."""

    def test_check_outcome_returns_unmarked_when_outcome_null(self):
        """Fresh handoff.json (outcome=None) → stdout 'unmarked'."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            handoff_path = _build_tier3_handoff(devforge, tmp)
            # Fresh handoff has no outcome.
            data = json.loads(handoff_path.read_text())
            self.assertIsNone(data.get("outcome"))

            r = _run_check_outcome(str(handoff_path))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("unmarked", r.stdout)

    def test_check_outcome_returns_marked_when_filled(self):
        """After append-outcome → stdout matches 'marked: primary (confidence=HIGH, evidence=test-result)'."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            handoff_path = _build_tier1_handoff(devforge, tmp)
            r_append = _run_append_outcome(
                str(handoff_path),
                hypothesis_confirmed="primary",
                evidence_source="test-result",
                evidence_cite="tests/research/config-not-applied.probe.spec.ts:42",
                actual_fix_path="services/api/main.py",
            )
            self.assertEqual(r_append.returncode, 0, r_append.stderr)

            r = _run_check_outcome(str(handoff_path))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("marked:", r.stdout)
            self.assertIn("primary", r.stdout)
            self.assertIn("HIGH", r.stdout)
            self.assertIn("test-result", r.stdout)

    def test_check_outcome_rejects_missing_file(self):
        """Missing handoff.json → exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            missing_path = Path(tmp) / "nonexistent" / "handoff.json"
            r = _run_check_outcome(str(missing_path))
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertTrue(
                "not found" in r.stderr or "cannot" in r.stderr,
                "stderr: {0}".format(r.stderr)
            )


# ---------------------------------------------------------------------------
# check-outcome dispatch on handoff_kind — research_helper check-outcome
# must dispatch to research or discover branch based on handoff_kind field.
# ---------------------------------------------------------------------------

_DISCOVER_HELPER_PY = _LIB_DIR / "discover_helper.py"


def _run_discover(argv, cwd=None):
    # type: (list, object) -> object
    """Run discover_helper.py with argv; capture stdout/stderr/exit."""
    cmd = [sys.executable, str(_DISCOVER_HELPER_PY)] + list(argv)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def _build_minimal_discover_handoff_for_check_outcome(tmp_root):
    # type: (str) -> Path
    """Build a minimal discover handoff.json using real discover_helper setters.

    Returns the path to the written discover handoff.json.
    """
    tmp_path = Path(tmp_root)
    devforge = tmp_path / ".devforge_discover"
    devforge.mkdir(parents=True, exist_ok=True)
    df = str(devforge)

    _run_discover(["--devforge-dir", df, "reset-memo"])
    _run_discover(["--devforge-dir", df, "reset-report"])

    _run_discover(["--devforge-dir", df, "set-topic", "--value", "audit-log-persistence"])
    _run_discover([
        "--devforge-dir", df, "set-verbatim-prompt",
        "--value", "Audit log persistence feature. Persist structured audit events to durable storage so all state changes are logged.",
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

    _run_discover(["--devforge-dir", df, "set-summary", "--value", "Audit log system"])
    _run_discover(["--devforge-dir", df, "set-overall-fit", "--value", "Good"])
    _run_discover(["--devforge-dir", df, "set-effort-estimate", "--value", "Low"])
    _run_discover(["--devforge-dir", df, "set-fit-rationale", "--value", "ORM extension"])
    _run_discover(["--devforge-dir", df, "set-verdict", "--value", "Worth pursuing"])
    _run_discover([
        "--devforge-dir", df, "record-integration-touchpoint",
        "--name", "ORM layer", "--module-path", "src/db/orm.py",
        "--reason", "Audit writes through ORM",
    ])
    _run_discover([
        "--devforge-dir", df, "set-design-option",
        "--name", "PostgreSQL table", "--shape", "ORM table",
        "--pros", '["Simple"]', "--cons", '["Single DB"]', "--complexity", "Low",
    ])
    _run_discover([
        "--devforge-dir", df, "set-recommended-option",
        "--name", "PostgreSQL table", "--rationale", "Lowest complexity",
    ])
    _run_discover([
        "--devforge-dir", df, "set-build-vs-buy",
        "--recommendation", "Build",
        "--build", "Extend ORM with new table",
        "--buy", "Third-party audit library",
        "--reasoning", "ORM already in place",
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
    _run_discover(["--devforge-dir", df, "set-next-step-text"])

    discover_dir = tmp_path / "discover"
    discover_dir.mkdir(exist_ok=True)
    out = discover_dir / "2026-05-20-audit-log-persistence.handoff.json"

    r = _run_discover([
        "--devforge-dir", df,
        "finalize-handoff",
        "--emit-handoff-json", str(out),
    ])
    if r.returncode != 0:
        raise RuntimeError(
            "_build_minimal_discover_handoff_for_check_outcome failed: " + r.stderr
        )
    return out


class TestCheckOutcomeDispatch(unittest.TestCase):
    """Tests for research_helper check-outcome dispatch on handoff_kind."""

    def test_check_outcome_dispatches_to_research_kind_when_handoff_kind_field_absent(self):
        """Research handoff (no handoff_kind) -> research branch -> marked: hypothesis..."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            handoff_path = _build_tier1_handoff(devforge, tmp)

            # Verify no handoff_kind field in research handoff.
            data = json.loads(handoff_path.read_text())
            self.assertNotIn("handoff_kind", data)

            # Append a research outcome.
            r_append = _run_append_outcome(
                str(handoff_path),
                hypothesis_confirmed="primary",
                evidence_source="test-result",
                evidence_cite="tests/research/config-not-applied.probe.spec.ts:42",
                actual_fix_path="services/api/main.py",
            )
            self.assertEqual(r_append.returncode, 0, r_append.stderr)

            r = _run_check_outcome(str(handoff_path))
            self.assertEqual(r.returncode, 0, r.stderr)
            # Research branch output: marked: <hypothesis> (confidence=..., evidence=...)
            self.assertIn("marked:", r.stdout)
            self.assertIn("primary", r.stdout)
            self.assertIn("confidence=", r.stdout)
            self.assertIn("evidence=", r.stdout)

    def test_check_outcome_dispatches_to_discover_kind_when_handoff_kind_field_present(self):
        """Discover handoff (handoff_kind='discover') -> discover branch -> marked: shipped=..."""
        with tempfile.TemporaryDirectory() as tmp:
            handoff_path = _build_minimal_discover_handoff_for_check_outcome(tmp)

            # Verify handoff_kind='discover' is present.
            data = json.loads(handoff_path.read_text())
            self.assertEqual(data.get("handoff_kind"), "discover")

            # Append a discover outcome via discover_helper.
            r_append = _run_discover([
                "append-outcome",
                "--handoff-path", str(handoff_path),
                "--design-option-shipped-id", "A",
                "--design-option-shipped-summary", "Shipped PostgreSQL table approach",
                "--build-vs-buy-actual", "Build",
            ])
            self.assertEqual(r_append.returncode, 0, r_append.stderr)

            r = _run_check_outcome(str(handoff_path))
            self.assertEqual(r.returncode, 0, r.stderr)
            # Discover branch output: marked: shipped=<id> (confidence=..., build_vs_buy=..., ...)
            self.assertIn("marked:", r.stdout)
            self.assertIn("shipped=A", r.stdout)
            self.assertIn("confidence=", r.stdout)
            self.assertIn("build_vs_buy=Build", r.stdout)
            self.assertIn("internal_extension=", r.stdout)

    def test_check_outcome_rejects_unknown_handoff_kind(self):
        """handoff_kind='bogus' -> exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            bad_path = Path(tmp) / "bad.handoff.json"
            bad_path.write_text(
                json.dumps({"handoff_kind": "bogus", "schema_version": "1.0"}),
                encoding="utf-8",
            )
            r = _run_check_outcome(str(bad_path))
            self.assertEqual(r.returncode, 2, "expected exit 2, stderr: " + r.stderr)
            self.assertIn("unknown handoff_kind", r.stderr)

    def test_check_outcome_discover_marked_format(self):
        """Discover outcome present -> emits 'marked: shipped=<id> (...)'."""
        with tempfile.TemporaryDirectory() as tmp:
            handoff_path = _build_minimal_discover_handoff_for_check_outcome(tmp)
            r_append = _run_discover([
                "append-outcome",
                "--handoff-path", str(handoff_path),
                "--design-option-shipped-id", "A",
                "--design-option-shipped-summary", "Shipped PostgreSQL table approach",
                "--build-vs-buy-actual", "Build",
            ])
            self.assertEqual(r_append.returncode, 0, r_append.stderr)

            r = _run_check_outcome(str(handoff_path))
            self.assertEqual(r.returncode, 0, r.stderr)

            out = r.stdout.strip()
            self.assertTrue(out.startswith("marked: shipped="), out)
            self.assertIn("confidence=", out)

    def test_check_outcome_discover_internal_extension_na_when_no_internal_prior_art(self):
        """Discover handoff with no internal prior-art -> internal_extension=n/a."""
        with tempfile.TemporaryDirectory() as tmp:
            handoff_path = _build_minimal_discover_handoff_for_check_outcome(tmp)

            # Verify no internal prior-art in the handoff (minimal fixture has none).
            data = json.loads(handoff_path.read_text())
            cited = data.get("plan_seeds", {}).get("cited_canonical_patterns", [])
            internal_entries = [c for c in cited if c.get("is_internal")]
            self.assertEqual(
                len(internal_entries), 0,
                "Fixture should have no internal prior-art entries"
            )

            r_append = _run_discover([
                "append-outcome",
                "--handoff-path", str(handoff_path),
                "--design-option-shipped-id", "A",
                "--design-option-shipped-summary", "Shipped PostgreSQL table approach",
                "--build-vs-buy-actual", "Build",
            ])
            self.assertEqual(r_append.returncode, 0, r_append.stderr)

            r = _run_check_outcome(str(handoff_path))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("internal_extension=n/a", r.stdout)

    def test_check_outcome_discover_unmarked_emits_reminder(self):
        """Discover handoff with outcome=None -> stdout starts with 'unmarked' and contains reminder."""
        with tempfile.TemporaryDirectory() as tmp:
            handoff_path = _build_minimal_discover_handoff_for_check_outcome(tmp)

            # Do NOT append-outcome — leave outcome absent.
            data = json.loads(handoff_path.read_text())
            self.assertIsNone(data.get("outcome"), "Fixture must have no outcome for this test")

            r = _run_check_outcome(str(handoff_path))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(
                r.stdout.startswith("unmarked"),
                "stdout must start with 'unmarked', got: " + repr(r.stdout),
            )
            self.assertIn(
                "discover_helper append-outcome",
                r.stdout,
                "stdout must contain reminder text with discover_helper command",
            )

    def test_check_outcome_research_unmarked_unchanged(self):
        """Research handoff (no handoff_kind) with outcome=None -> stdout == 'unmarked\\n' exactly."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            handoff_path = _build_tier1_handoff(devforge, tmp)

            # Do NOT append-outcome — leave outcome absent.
            data = json.loads(handoff_path.read_text())
            self.assertIsNone(data.get("outcome"), "Fixture must have no outcome for this test")
            self.assertNotIn("handoff_kind", data, "Research fixture must lack handoff_kind field")

            r = _run_check_outcome(str(handoff_path))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(
                r.stdout,
                "unmarked\n",
                "Research unmarked must be exactly 'unmarked\\n', got: " + repr(r.stdout),
            )


def _run_verify_hyp_suppression(devforge, extra_env=None):
    """Run research_helper verify-hypothesis-suppression and return CompletedProcess."""
    env = None
    if extra_env:
        import os as _os
        env = dict(_os.environ)
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(_HELPER_PY), "--devforge-dir", str(devforge),
         "verify-hypothesis-suppression"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


class TestVerifyHypothesisSuppression(unittest.TestCase):
    """verify-hypothesis-suppression: unverified hypothesis must not appear in plan direction.

    Round-trip via real research_helper setters (subprocess). State is built
    with actual helper calls; only post-build JSON edits are used to set up
    specific overlap or probe-feasibility scenarios.

    Covered cases:
      1. Trip-wire regression: tier-3 suspected-cause cause-text overlaps
         recommended-approach rationale → exit 2 with stderr naming the hypothesis.
         Overlap fires HONESTLY on the shared identifier "getconfigurationitems",
         NOT on hand-inserted padding.
      2. HIGH-grade (tier-1.5) hypothesis CONFIRMED (in hypotheses_addressed) →
         exit 0 (a confirmed primary hypothesis may become the design).
      3. HIGH-grade session, runner-up hypothesis NOT in hypotheses_addressed but
         overlapping rationale → exit 2 (runner-up is gated even in HIGH-grade session).
      4. Clean handoff with no unverified-hypothesis overlap → exit 0.
      5. Unverified hypothesis present but NOT overlapping the rationale → exit 0.
      6. Pure-paraphrase approach (same mechanism, disjoint vocabulary) → exit 0.
         KNOWN LIMITATION: the check catches identifier/vocabulary reuse only; it
         does NOT catch semantic paraphrase. Pure-paraphrase leakage is caught by
         the Step-5 intake echo-back human gate, not by this mechanical backstop.
    """

    def _build_base_and_inject(self, devforge, cause_text, rationale_text,
                                probe_feasibility=None, hypotheses_addressed=None):
        """Build bug state via real setters, then patch cause + rationale + probe_feasibility.

        Uses _build_bug_state for the skeleton, then overwrites:
        - hypotheses[0].cause with cause_text (the first hypothesis is the
          suspected-cause under test; the second is left unchanged).
        - recommended_approach.rationale with rationale_text.
        - probe_feasibility dict if supplied (else leave None fields intact).
        - recommended_approach.hypotheses_addressed if supplied (else leave
          the _build_bug_state default intact).
        """
        _build_bug_state(devforge)
        rep_path = devforge / "research-report.json"
        data = json.loads(rep_path.read_text())

        # Replace first hypothesis cause with the test-specific cause.
        if data.get("hypotheses"):
            data["hypotheses"][0]["cause"] = cause_text

        # Replace rationale to control overlap.
        if data.get("recommended_approach") is None:
            data["recommended_approach"] = {}
        data["recommended_approach"]["rationale"] = rationale_text

        # Patch hypotheses_addressed when specified.
        if hypotheses_addressed is not None:
            data["recommended_approach"]["hypotheses_addressed"] = hypotheses_addressed

        # Patch probe_feasibility when specified.
        if probe_feasibility is not None:
            data["probe_feasibility"] = probe_feasibility

        rep_path.write_text(json.dumps(data, indent=2) + "\n")

    def test_trip_wire_tier3_cause_overlaps_rationale_exits_nonzero(self):
        """Regression: tier-3 suspected cause 'getConfigurationItems returns Promise void'
        overlaps the realistic testForge20 approach summary
        'widen getConfigurationItems to a discriminated outcome carrying items inline'
        → exit 2 naming the hypothesis.

        This is the concrete trip-wire from Step 2 line 125 of the plan:
          "Suspected cause: getConfigurationItems returns Promise<void>" (tier-3)
          should NOT appear in: "widen getConfigurationItems to a discriminated
          outcome carrying items inline."
        Overlap fires HONESTLY on the shared identifier "getconfigurationitems"
        (len=24, well above min_len=4). "void" is 4 chars and passes the length
        filter but does not appear in the rationale — the overlap is solely on
        "getconfigurationitems". No tokens are hand-inserted into the rationale
        to force a match.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            cause = "getConfigurationItems returns Promise void"
            # Realistic testForge20-style recommended-approach summary.
            # Shares "getconfigurationitems" with the cause honestly — the
            # identifier names the API being changed, so it MUST appear in both.
            rationale = (
                "widen getConfigurationItems to a discriminated outcome "
                "carrying items inline"
            )
            # probe_feasibility: None fields → unresolved → unverified (tier unknown).
            # This is the default state from _build_bug_state (no set-probe-feasibility call).
            self._build_base_and_inject(devforge, cause, rationale)
            r = _run_verify_hyp_suppression(devforge)
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("verify-hypothesis-suppression", r.stderr)
            # Stderr must name the hypothesis cause; the overlapping token is
            # "getconfigurationitems" (the shared API identifier).
            self.assertIn("getConfigurationItems", r.stderr)

    def test_trip_wire_tier3_via_explicit_feasibility(self):
        """Tier-3 from explicit feasibility (auth_required=True, no chrome_mcp) +
        cause overlaps rationale → exit 2.

        auth_required=True without Chrome MCP → _classify_probe_tier returns tier=3.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            cause = "promise resolution timing causes data loss"
            rationale = "resolve timing issue by reordering promise resolution calls"
            probe_feasibility = {
                "data_shape_only": False,
                "auth_required": True,
                "network_dependent": False,
                "timing_dependent": False,
                "is_test_code": False,
            }
            self._build_base_and_inject(devforge, cause, rationale, probe_feasibility)
            # Ensure chrome MCP is NOT available (no env var override).
            r = _run_verify_hyp_suppression(devforge, extra_env={"DEVFORGE_CHROME_MCP_AVAILABLE": ""})
            self.assertEqual(r.returncode, 2, r.stderr)
            # Stderr must name the overlapping hypothesis cause.
            self.assertIn("promise", r.stderr.lower())

    def test_high_grade_tier1_5_confirmed_hypothesis_in_rationale_exits_zero(self):
        """HIGH-grade (tier-1.5) session: hypothesis explicitly confirmed in
        hypotheses_addressed may appear in the recommended approach → exit 0.

        Tier-1 requires: data_shape_only=True, not auth/network/timing, not is_test_code,
        AND test_infra_status = present. Since we cannot control init.yaml in the temp
        dir to fake test_infra, we use tier=1.5 instead (data_shape_only=True,
        test_infra absent → tier=1.5), which also grades HIGH.

        The gate exempts a hypothesis only when BOTH: (1) session is HIGH-grade AND
        (2) the hypothesis LABEL appears in recommended_approach.hypotheses_addressed.

        _build_base_and_inject replaces hypotheses[0].cause with the test-specific cause;
        that hypothesis still carries label "A" (auto-assigned by record-hypothesis in
        record order). hypotheses_addressed must contain "A" (the label), not the cause
        text, to trigger the exemption.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Hypothesis cause uses tokens that also appear in rationale.
            cause = "sortItems comparator returns incorrect ordering"
            rationale = "fix the sortItems comparator to return stable ordering"
            probe_feasibility = {
                "data_shape_only": True,
                "auth_required": False,
                "network_dependent": False,
                "timing_dependent": False,
                "is_test_code": False,
            }
            # data_shape_only=True + no auth/network + test_infra absent
            # → _classify_probe_tier → tier=1.5 → HIGH grade.
            # Hypothesis at index 0 carries label "A" (first recorded).
            # "A" in hypotheses_addressed → label match → confirmed → exempt → exit 0.
            self._build_base_and_inject(
                devforge, cause, rationale, probe_feasibility,
                hypotheses_addressed=["A"],
            )
            r = _run_verify_hyp_suppression(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_high_grade_runner_up_not_in_hypotheses_addressed_still_gated(self):
        """HIGH-grade (tier-1.5) session but runner-up hypothesis NOT in
        hypotheses_addressed: the runner-up is still gated even in a HIGH-grade session.

        Validates F2 fix: the gate evaluates per-hypothesis, not per-session.
        A runner-up whose cause overlaps the rationale is flagged exit 2
        even though the session tier is HIGH-grade.

        _build_base_and_inject replaces hypotheses[0].cause with runner_up_cause.
        That hypothesis carries label "A" (first recorded). hypotheses_addressed
        contains only "B" (the second, primary hypothesis at index 1), so "A" is
        NOT in confirmed_labels → runner-up is gated → exit 2.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Runner-up cause shares the identifier "getOrderItems" with the rationale.
            # This hypothesis is at index 0 (label "A") but is NOT in hypotheses_addressed.
            runner_up_cause = "getOrderItems caches stale data on retry"
            rationale = "widen getOrderItems to return a discriminated result"
            probe_feasibility = {
                "data_shape_only": True,
                "auth_required": False,
                "network_dependent": False,
                "timing_dependent": False,
                "is_test_code": False,
            }
            # hypotheses_addressed names only the primary hypothesis (label "B",
            # i.e. the SECOND recorded hypothesis), NOT the runner-up (label "A").
            self._build_base_and_inject(
                devforge, runner_up_cause, rationale, probe_feasibility,
                hypotheses_addressed=["B"],
            )
            r = _run_verify_hyp_suppression(devforge)
            # Runner-up (label "A") overlaps rationale via "getorderitems" → exit 2.
            self.assertEqual(r.returncode, 2, "runner-up should be gated: " + r.stderr)
            self.assertIn("getOrderItems", r.stderr)

    def test_pure_paraphrase_exits_zero_known_limitation(self):
        """KNOWN LIMITATION: pure-paraphrase approach that encodes the same mechanism
        as an unverified hypothesis using entirely different vocabulary → exit 0.

        The check is a literal identifier/vocabulary-reuse backstop only. A recommended
        approach that says "widen the outcome to carry success or failure inline" encodes
        the same mechanism as "getConfigurationItems returns Promise<void>" but shares
        NO significant token with that cause text (no shared identifier or keyword passes
        the min_len=4 + stopword filter). The gate correctly exits 0 — it cannot detect
        pure paraphrase by design. This gap is caught by the Step-5 intake echo-back
        human gate, not by this mechanical check.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Unverified cause (None feasibility → unresolved → unverified).
            cause = "getConfigurationItems returns Promise void"
            # Pure-paraphrase rationale: encodes the same mechanism (widen the
            # outcome type to carry items vs. void) but shares NO significant token
            # with the cause. "widen", "outcome", "carry", "success", "failure",
            # "inline" are all unique to the rationale; "getconfigurationitems",
            # "returns", "promise" appear only in the cause. No overlap → exit 0.
            rationale = "widen the outcome to carry success or failure inline"
            self._build_base_and_inject(devforge, cause, rationale)
            r = _run_verify_hyp_suppression(devforge)
            # KNOWN LIMITATION: pure paraphrase is not detected. Exit 0.
            self.assertEqual(r.returncode, 0,
                             "pure paraphrase should exit 0 (known limitation): " + r.stderr)

    def test_clean_handoff_no_overlap_exits_zero(self):
        """Clean handoff: unverified probe (None feasibility) but no hypothesis
        cause-token overlaps the rationale → exit 0.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Cause and rationale share no significant tokens.
            cause = "cache invalidation stale data"
            rationale = "move sort logic into derived computed property"
            self._build_base_and_inject(devforge, cause, rationale)
            r = _run_verify_hyp_suppression(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_unverified_hypothesis_not_in_rationale_exits_zero(self):
        """Unverified hypothesis is present as an open concern but its cause-text
        does NOT appear in the recommended approach → exit 0.

        This is the 'hypothesis in open question, not in plan direction' case.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Tier-3 because feasibility unresolved (None fields).
            cause = "network timeout causes partial write corruption"
            # Rationale about sort logic — completely disjoint tokens.
            rationale = "replace inline sort with stable comparator function"
            self._build_base_and_inject(devforge, cause, rationale)
            r = _run_verify_hyp_suppression(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_empty_state_exits_zero(self):
        """Missing state files (no prior setter calls) → no hypotheses, no rationale,
        gate exits 0 without error.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Do NOT call any setters — state files are absent.
            r = _run_verify_hyp_suppression(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_no_recommended_approach_exits_zero(self):
        """Unresolved feasibility + hypotheses but no recommended_approach yet
        → nothing to gate against → exit 0.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Wipe the recommended approach.
            data["recommended_approach"] = None
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run_verify_hyp_suppression(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_tier2_chrome_mcp_cause_overlaps_rationale_exits_nonzero(self):
        """Tier-2 (auth_required=True WITH chrome MCP available) is also MEDIUM-grade.
        Hypothesis cause overlapping rationale → exit 2.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            cause = "authentication token expires during long running session"
            rationale = "refresh authentication token before session expiration"
            probe_feasibility = {
                "data_shape_only": False,
                "auth_required": True,
                "network_dependent": False,
                "timing_dependent": False,
                "is_test_code": False,
            }
            self._build_base_and_inject(devforge, cause, rationale, probe_feasibility)
            # DEVFORGE_CHROME_MCP_AVAILABLE=1 → tier=2 (MEDIUM).
            r = _run_verify_hyp_suppression(devforge, extra_env={"DEVFORGE_CHROME_MCP_AVAILABLE": "1"})
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("authentication", r.stderr.lower())

    def test_confirmed_exempt_label_match_exits_zero(self):
        """Confirmed-exempt: HIGH-grade session, hypothesis whose label IS in
        hypotheses_addressed, cause-text overlaps the rationale → exit 0.

        This is the case that was wrongly flagged before the label-match fix:
        when hypotheses_addressed holds labels ("A", "B", ...) but the old
        code compared cause text against those labels, the exemption could
        NEVER fire (a cause like "processOrders reads stale cache" != "A").
        After the fix the exemption fires correctly.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Tier-1.5 (data_shape_only=True, test_infra absent) → HIGH grade.
            probe_feasibility = {
                "data_shape_only": True,
                "auth_required": False,
                "network_dependent": False,
                "timing_dependent": False,
                "is_test_code": False,
            }
            # Hypothesis at index 0 (label "A") shares "processorders" and "cache"
            # with the rationale — strong identifier overlap.
            cause = "processOrders reads stale cache on retry"
            rationale = "flush processOrders cache before each retry attempt"
            # hypotheses_addressed contains label "A" → confirmed → exempt → exit 0.
            self._build_base_and_inject(
                devforge, cause, rationale, probe_feasibility,
                hypotheses_addressed=["A"],
            )
            r = _run_verify_hyp_suppression(devforge)
            self.assertEqual(
                r.returncode, 0,
                "confirmed hypothesis (label A in hypotheses_addressed) should be "
                "exempt but was flagged: " + r.stderr,
            )

    def test_unconfirmed_gated_label_not_in_addressed(self):
        """Unconfirmed-gated: HIGH-grade session, hypothesis whose label is NOT in
        hypotheses_addressed (a runner-up), cause overlaps rationale → exit 2.

        The hypothesis at index 0 carries label "A". hypotheses_addressed contains
        only "B" (the second hypothesis, which is the primary confirmed one). "A"
        is not in confirmed_labels → runner-up is gated → exit 2.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            probe_feasibility = {
                "data_shape_only": True,
                "auth_required": False,
                "network_dependent": False,
                "timing_dependent": False,
                "is_test_code": False,
            }
            # Runner-up at index 0 (label "A") shares "fetchProducts" with rationale.
            runner_up_cause = "fetchProducts returns incomplete dataset on pagination"
            rationale = "extend fetchProducts to include total count in response"
            # Only label "B" (the second hypothesis) is addressed — "A" is the runner-up.
            self._build_base_and_inject(
                devforge, runner_up_cause, rationale, probe_feasibility,
                hypotheses_addressed=["B"],
            )
            r = _run_verify_hyp_suppression(devforge)
            self.assertEqual(
                r.returncode, 2,
                "runner-up hypothesis (label A not in hypotheses_addressed) should "
                "be gated but was exempt: " + r.stderr,
            )
            self.assertIn("fetchProducts", r.stderr)

    def test_low_grade_gated_regardless_of_hypotheses_addressed(self):
        """Low-grade-gated: MEDIUM-grade session, any hypothesis with cause overlapping
        rationale → exit 2 even if its label is in hypotheses_addressed.

        Grade MEDIUM means session_is_high_grade=False → confirmed_labels stays empty
        → no hypothesis is exempt regardless of hypotheses_addressed content.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # auth_required=True, no Chrome MCP → tier-3 → LOW grade.
            probe_feasibility = {
                "data_shape_only": False,
                "auth_required": True,
                "network_dependent": False,
                "timing_dependent": False,
                "is_test_code": False,
            }
            cause = "refreshSession token expires before request completes"
            rationale = "pre-warm refreshSession token before issuing the request"
            # Put label "A" in hypotheses_addressed — but grade is LOW so the
            # session is NOT high-grade and confirmed_labels stays empty.
            self._build_base_and_inject(
                devforge, cause, rationale, probe_feasibility,
                hypotheses_addressed=["A"],
            )
            # No DEVFORGE_CHROME_MCP_AVAILABLE → tier-3 → LOW grade.
            r = _run_verify_hyp_suppression(
                devforge, extra_env={"DEVFORGE_CHROME_MCP_AVAILABLE": ""}
            )
            self.assertEqual(
                r.returncode, 2,
                "LOW-grade session should gate hypothesis regardless of "
                "hypotheses_addressed content: " + r.stderr,
            )
            self.assertIn("refreshsession", r.stderr.lower())


# ---------------------------------------------------------------------------
# Step 5 — intake-interrogation gate: record-intake-classification +
#           render-intake-echo for research_helper.
# ---------------------------------------------------------------------------


class TestRecordIntakeClassification(unittest.TestCase):
    """record-intake-classification setter: persists binary classification + minimal_fix."""

    def test_requirement_kind_persisted(self):
        """A requirement statement is stored with kind='requirement'."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            r = _run([
                "--devforge-dir", str(devforge),
                "record-intake-classification",
                "--statement", "render empty section + error toast on load failure",
                "--kind", "requirement",
                "--minimal-fix", "branch render on load-failure flag; show empty + toast",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((Path(devforge) / "research-state.json").read_text())
            classifications = state.get("intake_classifications", [])
            self.assertEqual(len(classifications), 1)
            entry = classifications[0]
            self.assertEqual(entry["statement"], "render empty section + error toast on load failure")
            self.assertEqual(entry["kind"], "requirement")
            self.assertEqual(entry["minimal_fix"], "branch render on load-failure flag; show empty + toast")

    def test_hypothesis_kind_persisted(self):
        """A hypothesis statement is stored with kind='hypothesis' and optional minimal_fix."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            r = _run([
                "--devforge-dir", str(devforge),
                "record-intake-classification",
                "--statement", "Suspected cause: last-fetch-wins race in Service.loadData",
                "--kind", "hypothesis",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((Path(devforge) / "research-state.json").read_text())
            classifications = state.get("intake_classifications", [])
            self.assertEqual(len(classifications), 1)
            entry = classifications[0]
            self.assertEqual(entry["kind"], "hypothesis")
            self.assertIsNone(entry["minimal_fix"])

    def test_multiple_statements_appended(self):
        """Multiple calls append distinct entries."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run([
                "--devforge-dir", str(devforge),
                "record-intake-classification",
                "--statement", "render empty section on load failure",
                "--kind", "requirement",
                "--minimal-fix", "branch on load_failed flag",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "record-intake-classification",
                "--statement", "Suspected cause: fetch race",
                "--kind", "hypothesis",
            ])
            state = json.loads((Path(devforge) / "research-state.json").read_text())
            classifications = state["intake_classifications"]
            self.assertEqual(len(classifications), 2)
            kinds = [e["kind"] for e in classifications]
            self.assertIn("requirement", kinds)
            self.assertIn("hypothesis", kinds)

    def test_idempotent_re_record_same_statement(self):
        """Re-recording the same statement replaces the entry (idempotent)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            stmt = "render empty section on load failure"
            _run([
                "--devforge-dir", str(devforge),
                "record-intake-classification",
                "--statement", stmt,
                "--kind", "requirement",
                "--minimal-fix", "old fix",
            ])
            # Re-record with corrected minimal_fix.
            r = _run([
                "--devforge-dir", str(devforge),
                "record-intake-classification",
                "--statement", stmt,
                "--kind", "requirement",
                "--minimal-fix", "corrected fix",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            state = json.loads((Path(devforge) / "research-state.json").read_text())
            classifications = state["intake_classifications"]
            self.assertEqual(len(classifications), 1, "should not append duplicate")
            self.assertEqual(classifications[0]["minimal_fix"], "corrected fix")

    def test_invalid_kind_rejected(self):
        """An invalid --kind value is rejected with exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            r = _run([
                "--devforge-dir", str(devforge),
                "record-intake-classification",
                "--statement", "some statement",
                "--kind", "context",   # not in INTAKE_KIND_ENUM
            ])
            self.assertEqual(r.returncode, 2, "invalid kind should exit 2")

    def test_empty_statement_rejected(self):
        """An empty --statement is rejected with exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            r = _run([
                "--devforge-dir", str(devforge),
                "record-intake-classification",
                "--statement", "   ",
                "--kind", "requirement",
            ])
            self.assertEqual(r.returncode, 2, "empty statement should exit 2")

    def test_default_memo_has_intake_classifications_field(self):
        """default_memo_state must include intake_classifications as empty list."""
        memo = research_helper.default_memo_state()
        self.assertIn("intake_classifications", memo)
        self.assertEqual(memo["intake_classifications"], [])

    def test_round_trip_no_minimal_fix_is_none(self):
        """When --minimal-fix is not passed, minimal_fix persists as None."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run([
                "--devforge-dir", str(devforge),
                "record-intake-classification",
                "--statement", "desired outcome: items never leak from prior load",
                "--kind", "requirement",
            ])
            state = json.loads((Path(devforge) / "research-state.json").read_text())
            entry = state["intake_classifications"][0]
            self.assertIsNone(entry["minimal_fix"])


class TestRenderIntakeEcho(unittest.TestCase):
    """render-intake-echo verb: produces structured echo-back block."""

    def _record(self, devforge, statement, kind, minimal_fix=None):
        """Helper: call record-intake-classification."""
        argv = [
            "--devforge-dir", str(devforge),
            "record-intake-classification",
            "--statement", statement,
            "--kind", kind,
        ]
        if minimal_fix is not None:
            argv += ["--minimal-fix", minimal_fix]
        _run(argv)

    def test_requirements_section_present(self):
        """Requirements section lists requirement statements."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            self._record(
                devforge,
                "render empty section on load failure",
                "requirement",
                minimal_fix="branch on load_failed flag",
            )
            r = _run(["--devforge-dir", str(devforge), "render-intake-echo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            out = r.stdout
            self.assertIn("## Intake interpretation", out)
            self.assertIn("### Requirements (what you asked for)", out)
            self.assertIn("render empty section on load failure", out)
            self.assertIn("branch on load_failed flag", out)

    def test_hypothesis_section_present_when_hypotheses_exist(self):
        """When hypotheses exist, the 'Hypotheses to verify' section appears."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            self._record(devforge, "render empty + toast", "requirement", "branch on flag")
            self._record(devforge, "Suspected cause: fetch race in loadData", "hypothesis")
            r = _run(["--devforge-dir", str(devforge), "render-intake-echo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            out = r.stdout
            self.assertIn("### Hypotheses to verify", out)
            self.assertIn("NOT requirements", out)
            self.assertIn("Suspected cause: fetch race in loadData", out)
            # Must also surface the requirement.
            self.assertIn("render empty + toast", out)

    def test_hypothesis_section_omitted_when_no_hypotheses(self):
        """Proportionality: when there are no hypotheses the section is absent."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            self._record(devforge, "show empty section on failure", "requirement", "if flag: empty")
            r = _run(["--devforge-dir", str(devforge), "render-intake-echo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            out = r.stdout
            self.assertNotIn("Hypotheses to verify", out)
            self.assertNotIn("NOT requirements", out)

    def test_minimal_scope_section_present(self):
        """Minimal scope section is always present and surfaces the first req's minimal_fix."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            self._record(
                devforge,
                "render empty section on load failure",
                "requirement",
                minimal_fix="branch render on load_failed; show empty + toast",
            )
            r = _run(["--devforge-dir", str(devforge), "render-intake-echo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            out = r.stdout
            self.assertIn("### Minimal scope", out)
            self.assertIn("branch render on load_failed; show empty + toast", out)

    def test_empty_classifications_emits_notice(self):
        """When no classifications recorded, emits the notice comment."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            r = _run(["--devforge-dir", str(devforge), "render-intake-echo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("no classifications recorded", r.stdout)

    def test_minimal_scope_not_set_when_no_minimal_fix(self):
        """When requirement has no minimal_fix, minimal scope shows '(not set)'."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            self._record(devforge, "render empty section", "requirement")
            r = _run(["--devforge-dir", str(devforge), "render-intake-echo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("(not set)", r.stdout)

    def test_hypothesis_only_omits_requirements_header_and_minimal_scope(self):
        """F2: when only a hypothesis is recorded (no requirements), the
        '### Requirements' header, '*(no requirements classified)*' placeholder,
        and '### Minimal scope' section must all be absent."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            self._record(devforge, "Suspected cause: race in loadData", "hypothesis")
            r = _run(["--devforge-dir", str(devforge), "render-intake-echo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            out = r.stdout
            self.assertNotIn("### Minimal scope", out)
            self.assertNotIn("no requirements classified", out)
            # The hypothesis itself must still be present.
            self.assertIn("Suspected cause: race in loadData", out)

    def test_requirement_inline_label_uses_minimal_scope(self):
        """F3: inline per-requirement label must read 'Minimal scope:' not 'Minimal fix:'."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            self._record(
                devforge,
                "render empty section on failure",
                "requirement",
                minimal_fix="branch on load_failed flag",
            )
            r = _run(["--devforge-dir", str(devforge), "render-intake-echo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            out = r.stdout
            self.assertIn("Minimal scope:", out)
            self.assertNotIn("Minimal fix:", out)

    def test_testforge20_trip_wire(self):
        """Concrete trip-wire from plan Step 5: suspected-cause → hypothesis,
        desired outcome → requirement; hypothesis section NOT requirements."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            # The over-build scenario: desired outcome is the requirement.
            self._record(
                devforge,
                "render empty section and error toast; never leak prior items on load failure",
                "requirement",
                minimal_fix="branch the render on load-failure; show empty + toast",
            )
            # The suspected cause is a hypothesis — must NOT be treated as requirement.
            self._record(
                devforge,
                "Suspected cause: inline-items mechanism not handling empty state",
                "hypothesis",
            )
            r = _run(["--devforge-dir", str(devforge), "render-intake-echo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            out = r.stdout
            # Requirement must be in the Requirements section.
            self.assertIn("render empty section and error toast", out)
            # Suspected cause must be labeled as NOT requirement.
            self.assertIn("Suspected cause: inline-items mechanism not handling empty state", out)
            self.assertIn("NOT requirements", out)
            # Minimal scope must surface the minimal change (no inline-items mechanism).
            self.assertIn("branch the render on load-failure", out)
            # The hypothesis section must clearly separate hypotheses from requirements.
            req_pos = out.index("### Requirements")
            hyp_pos = out.index("### Hypotheses to verify")
            self.assertLess(req_pos, hyp_pos, "Requirements section must precede Hypotheses section")


if __name__ == "__main__":
    unittest.main()
