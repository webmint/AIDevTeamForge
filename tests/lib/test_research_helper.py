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
        ):
            self.assertIsNone(rep[field], "field {0} default".format(field))
        for arr_field in (
            "findings", "hypotheses", "approaches",
            "constitution_constraints", "open_uncertainties",
            # Phase 2.4c fields
            "fix_path_helpers", "inbound_callers", "dead_siblings",
            "consumer_chain", "value_semantics",
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
                "--helper-qn", "OrderBLoC.fetchOrder",
                "--file-line", "lib/blocs/order_bloc.dart:42",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            qns = [h["qn"] for h in rep["fix_path_helpers"]]
            self.assertIn("OrderBLoC.fetchOrder", qns)
            # Verify full dict shape.
            entry = rep["fix_path_helpers"][0]
            self.assertEqual(entry["qn"], "OrderBLoC.fetchOrder")
            self.assertEqual(entry["file_line"], "lib/blocs/order_bloc.dart:42")
        finally:
            tmp.cleanup()

    def test_record_fix_path_helper_deduplication(self):
        tmp, devforge = self._fresh()
        try:
            _run([
                "--devforge-dir", str(devforge),
                "record-fix-path-helper",
                "--helper-qn", "OrderBLoC.fetchOrder",
                "--file-line", "lib/blocs/order_bloc.dart:42",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "record-fix-path-helper",
                "--helper-qn", "OrderBLoC.fetchOrder",
                "--file-line", "lib/blocs/order_bloc.dart:99",  # different file_line, same qn → deduped
            ])
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
                "--helper-qn", "OrderBLoC.fetchOrder",
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
                "--helper-qn", "OrderBLoC.fetchOrder",
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
                "--helper-qn", "OrderBLoC.fetchOrder",
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
                "--helper-qn", "OrderBLoC.fetchOrder",
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
                "--helper-qn", "OrderBLoC.fetchOrder",
                "--caller-qn", "OrderViewWidget.build",
                "--file-line", "lib/order_view.dart:88",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["inbound_callers"]), 1)
            row = rep["inbound_callers"][0]
            self.assertEqual(row["helper_qn"], "OrderBLoC.fetchOrder")
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
                "--helper-qn", "OrderBLoC.fetchOrder",
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
                "--helper-qn", "OrderBLoC.fetchOrder",
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
                "--class-qn", "OrderBLoC",
                "--method-qn", "OrderBLoC.toggleSplit",
                "--verified-via", "trace_path",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["dead_siblings"]), 1)
            row = rep["dead_siblings"][0]
            self.assertEqual(row["class_qn"], "OrderBLoC")
            self.assertEqual(row["method_qn"], "OrderBLoC.toggleSplit")
            self.assertEqual(row["verified_via"], "trace_path")
        finally:
            tmp.cleanup()

    def test_record_dead_sibling_search_code_variant(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "record-dead-sibling",
                "--class-qn", "OrderBLoC",
                "--method-qn", "OrderBLoC.toggleSplit",
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
                "--class-qn", "OrderBLoC",
                "--method-qn", "OrderBLoC.toggleSplit",
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
                "--value", "splitOnSNA",
                "--consumer-qn", "OrderCreationUseCase.execute",
                "--file-line", "lib/order_creation.dart:55",
                "--role", "enforces Q&O parity at server boundary",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["consumer_chain"]), 1)
            row = rep["consumer_chain"][0]
            self.assertEqual(row["value"], "splitOnSNA")
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
                "--value", "splitOnSNA",
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
                "--value", "splitOnSNA",
                "--classification", "preference",
                "--evidence", "only set per user action",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            self.assertEqual(len(rep["value_semantics"]), 1)
            row = rep["value_semantics"][0]
            self.assertEqual(row["value"], "splitOnSNA")
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
                "--value", "splitOnSNA",
                "--classification", "preference",
                "--evidence", "first evidence",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "splitOnSNA",
                "--classification", "unclassified",
                "--evidence", "second evidence",
            ])
            rep = self._read_report(devforge)
            # Only one row for the same value.
            rows = [r for r in rep["value_semantics"] if r["value"] == "splitOnSNA"]
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
                "--value", "splitOnSNA",
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
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "splitOnSNA",
                "--classification", "invariant",
                "--evidence", "Q&O parity rule",
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
                "--value", "splitOnSNA",
                "--consumer-qn", "OrderCreationUseCase.execute",
                "--file-line", "lib/order.dart:10",
                "--role", "enforces invariant",
            ])
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "splitOnSNA",
                "--classification", "invariant",
                "--evidence", "OrderCreationUseCase.execute enforces Q&O parity",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            rep = self._read_report(devforge)
            rows = [row for row in rep["value_semantics"] if row["value"] == "splitOnSNA"]
            self.assertEqual(rows[0]["classification"], "invariant")
        finally:
            tmp.cleanup()

    def test_set_value_semantics_rejects_invalid_classification(self):
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "splitOnSNA",
                "--classification", "definitely-not-valid",
                "--evidence", "e",
            ])
            self.assertNotEqual(r.returncode, 0)
        finally:
            tmp.cleanup()


class TestVerifyCheck8(unittest.TestCase):
    """Check 8: bug mode requires fix_path_helpers non-empty."""

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

    def test_check8_not_triggered_for_enhancement_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_enhancement_state(devforge)
            # fix_path_helpers empty + enhancement mode → check 8 should not fire.
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)


class TestVerifyCheck9(unittest.TestCase):
    """Check 9: every enumerated helper needs at least one inbound caller row."""

    def test_check9_fails_when_helper_missing_caller(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            # Add helper without a corresponding caller.
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["fix_path_helpers"] = [{"qn": "OrderBLoC.fetchOrder", "file_line": "lib/blocs/order_bloc.dart:42"}]
            data["inbound_callers"] = []
            rep_path.write_text(json.dumps(data, indent=2) + "\n")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("inbound_callers", r.stderr)
            self.assertIn("OrderBLoC.fetchOrder", r.stderr)

    def test_check9_passes_when_all_helpers_have_callers(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_bug_state(devforge)
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            data["fix_path_helpers"] = [{"qn": "OrderBLoC.fetchOrder", "file_line": "lib/blocs/order_bloc.dart:42"}]
            data["inbound_callers"] = [
                {"helper_qn": "OrderBLoC.fetchOrder", "caller_qn": "View.build", "file_line": "src/v.dart:5"}
            ]
            # Single-layer helpers (lib/blocs) — add justification + cites to satisfy check 13.
            data["consumer_chain"] = [
                {"value": "fetchOrder", "consumer_qn": "View.build",
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
        data["fix_path_helpers"] = [{"qn": "OrderBLoC.fetchOrder", "file_line": "lib/blocs/order_bloc.dart:42"}]
        data["inbound_callers"] = [
            {"helper_qn": "OrderBLoC.fetchOrder", "caller_qn": "View.build", "file_line": "src/v.dart:5"}
        ]
        # Set value_semantics with invariant + consumer_chain.
        data["consumer_chain"] = [
            {"value": "splitOnSNA", "consumer_qn": "OrderCreationUseCase.execute",
             "file_line": "lib/order.dart:10", "role": "enforces parity"}
        ]
        data["value_semantics"] = [
            {"value": "splitOnSNA", "classification": "invariant", "evidence": "Q&O rule"}
        ]
        data["dead_siblings"] = [
            {"class_qn": "OrderBLoC", "method_qn": "OrderBLoC.toggleSplit", "verified_via": "trace_path"}
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
                "revive OrderBLoC.toggleSplit to enforce invariant",
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
            data["fix_path_helpers"] = [{"qn": "OrderBLoC.fetchOrder", "file_line": "lib/blocs/order_bloc.dart:42"}]
            data["inbound_callers"] = [
                {"helper_qn": "OrderBLoC.fetchOrder", "caller_qn": "V.build", "file_line": "src/v.dart:5"}
            ]
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
        data["fix_path_helpers"] = [{"qn": "OrderBLoC.fetchOrder", "file_line": "lib/blocs/order_bloc.dart:42"}]
        data["inbound_callers"] = [
            {"helper_qn": "OrderBLoC.fetchOrder", "caller_qn": "View.build", "file_line": "src/v.dart:5"}
        ]
        data["consumer_chain"] = [
            {"value": "splitOnSNA", "consumer_qn": "OrderCreationUseCase.execute",
             "file_line": "lib/order.dart:10", "role": "enforces parity"}
        ]
        data["value_semantics"] = [
            {"value": "splitOnSNA", "classification": "invariant", "evidence": "Q&O parity rule"}
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
            data["fix_path_helpers"] = [{"qn": "OrderBLoC.fetchOrder", "file_line": "lib/blocs/order_bloc.dart:42"}]
            data["inbound_callers"] = [
                {"helper_qn": "OrderBLoC.fetchOrder", "caller_qn": "V.build", "file_line": "s:1"}
            ]
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
                "--helper-qn", "OrderBLoC.fetchOrder",
            ])
            # Satisfy check 9: inbound caller for every helper.
            _run([
                "--devforge-dir", str(devforge),
                "record-inbound-caller",
                "--helper-qn", "OrderBLoC.fetchOrder",
                "--caller-qn", "OrderViewWidget.build",
                "--file-line", "lib/order_view.dart:88",
            ])
            # Set up consumer_chain (required before invariant classification).
            _run([
                "--devforge-dir", str(devforge),
                "record-consumer-chain",
                "--value", "splitOnSNA",
                "--consumer-qn", "OrderCreationUseCase.execute",
                "--file-line", "lib/order_creation.dart:55",
                "--role", "enforces Q&O parity at server boundary",
            ])
            # Set value_semantics to invariant.
            _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "splitOnSNA",
                "--classification", "invariant",
                "--evidence", "OrderCreationUseCase.execute enforces Q&O parity",
            ])
            # Add dead sibling.
            _run([
                "--devforge-dir", str(devforge),
                "record-dead-sibling",
                "--class-qn", "OrderBLoC",
                "--method-qn", "OrderBLoC.toggleSplit",
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
                          "consumer_chain", "value_semantics"):
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
        """Rejecting invariant (no consumer_chain) must exit 2, not 1."""
        tmp, devforge = self._fresh()
        try:
            r = _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "splitOnSNA",
                "--classification", "invariant",
                "--evidence", "Q&O parity rule",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("requires at least one consumer_chain entry", r.stderr)
        finally:
            tmp.cleanup()

    def test_invariant_rejection_does_not_rewrite_state_file(self):
        """Rejecting invariant must not touch research-report.json (mtime unchanged)."""
        tmp, devforge = self._fresh()
        try:
            rep_path = devforge / "research-report.json"
            mtime_before = rep_path.stat().st_mtime_ns
            _run([
                "--devforge-dir", str(devforge),
                "set-value-semantics",
                "--value", "splitOnSNA",
                "--classification", "invariant",
                "--evidence", "Q&O parity rule",
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
                {"qn": "OrderBLoC.fetchOrder", "file_line": "lib/blocs/order_bloc.dart:42"},
            ]
            data["inbound_callers"] = [
                {"helper_qn": "ProductsHelper.sort", "caller_qn": "View.render", "file_line": "src/v.ts:5"},
                {"helper_qn": "OrderBLoC.fetchOrder", "caller_qn": "V.build", "file_line": "src/v.dart:5"},
            ]
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
        data["fix_path_helpers"] = [{"qn": "OrderBLoC.fetchOrder", "file_line": "lib/blocs/order_bloc.dart:42"}]
        data["inbound_callers"] = [
            {"helper_qn": "OrderBLoC.fetchOrder", "caller_qn": "View.build", "file_line": "src/v.dart:5"}
        ]
        data["consumer_chain"] = [
            {"value": "splitOnSNA", "consumer_qn": "OrderCreationUseCase.execute",
             "file_line": "lib/order.dart:10", "role": "enforces parity"}
        ]
        data["value_semantics"] = [
            {"value": "splitOnSNA", "classification": "invariant", "evidence": "Q&O rule"}
        ]
        data["dead_siblings"] = [
            {"class_qn": "OrderBLoC", "method_qn": "OrderBLoC.toggleSplit", "verified_via": "trace_path"}
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
                "Revive OrderBLoC.toggleSplit",
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
            data["fix_path_helpers"] = [{"qn": "OrderBLoC.fetchOrder", "file_line": "lib/blocs/order_bloc.dart:42"}]
            data["inbound_callers"] = [
                {"helper_qn": "OrderBLoC.fetchOrder", "caller_qn": "View.build",
                 "file_line": "src/v.dart:5"}
            ]
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
                    "--class-qn", "OrderBLoC",
                    "--method-qn", "OrderBLoC.toggleSplit",
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

    def test_apps_app_web_prefix_is_presentation(self):
        self.assertTrue(research_helper._is_presentation_layer("apps/app-web/index.ts"))

    def test_apps_web_prefix_is_presentation(self):
        self.assertTrue(research_helper._is_presentation_layer("apps/web/main.ts"))

    def test_apps_frontend_prefix_is_presentation(self):
        self.assertTrue(research_helper._is_presentation_layer("apps/frontend/App.vue"))

    def test_regular_ts_is_not_presentation(self):
        self.assertFalse(research_helper._is_presentation_layer("src/utils/helpers.ts"))

    def test_domain_package_is_not_presentation(self):
        self.assertFalse(research_helper._is_presentation_layer("pkg-cse-core/QuoteLine.ts"))

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
            research_helper._extract_package("apps/app-web/src/foo.vue"),
            "apps/app-web",
        )

    def test_extract_two_component_path(self):
        # File sits at second component slot — still returns first two components.
        self.assertEqual(
            research_helper._extract_package("pkg-cse-core/utils.ts"),
            "pkg-cse-core",
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
            # Rewrite findings + helpers so symptom is domain-layer (pkg-cse-core).
            rep_path = devforge / "research-report.json"
            data = json.loads(rep_path.read_text())
            # Symptom finding → domain-layer file.
            data["findings"] = [
                {
                    "surface": "core util",
                    "file_line": "pkg-cse-core/utils.ts:10",
                    "relevance": "comparison logic",
                    "framing": "primary",
                },
                {
                    "surface": "race probe",
                    "file_line": "pkg-cse-core/utils.ts:20",
                    "relevance": "runner-up probe",
                    "framing": "runner-up",
                },
            ]
            # All helpers also in pkg-cse-core — would trigger 8b for presentation
            # but domain symptom means 8b is skipped.
            # Check 13 still fires for single-layer, so add justification + cites.
            data["fix_path_helpers"] = [{"qn": "CoreUtil.compare", "file_line": "pkg-cse-core/utils.ts:10"}]
            data["inbound_callers"] = [
                {
                    "helper_qn": "CoreUtil.compare",
                    "caller_qn": "CoreUtil.sort",
                    "file_line": "pkg-cse-core/sort.ts:5",
                },
            ]
            # Provide consumer_chain to anchor cites for check 13.
            data["consumer_chain"] = [
                {"value": "compareResult", "consumer_qn": "CoreUtil.sort",
                 "file_line": "pkg-cse-core/sort.ts:5", "role": "consumes compare result"}
            ]
            if data.get("recommended_approach"):
                data["recommended_approach"]["single_layer_justification"] = (
                    "Symptom is domain-local (pkg-cse-core comparison logic); no cross-layer trace needed."
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
        ("affected_area", "OrderBLoC.fetchOrder"),
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
        "--cause", "last-fetch-wins racing in fetchOrder",
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
        "--value", "OrderBLoC.fetchOrder lacks fetch-id guard.",
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
        "--description", "Add fetch-id guard inside OrderBLoC.fetchOrder",
        "--addresses-hypotheses", json.dumps(["last-fetch-wins racing in fetchOrder"]),
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
        "--value", "OrderBLoC.fetchOrder vulnerable to concurrent-fetch race.",
    ])

    # BOTH helpers in lib/blocs — single-package AND non-presentation-layer.
    # Triggers check 13 single-layer gate; does NOT trigger check 8b suppression.
    _run([
        "--devforge-dir", str(devforge), "record-fix-path-helper",
        "--helper-qn", "OrderBLoC.fetchOrder",
        "--file-line", "lib/blocs/order_bloc.dart:42",
    ])
    _run([
        "--devforge-dir", str(devforge), "record-inbound-caller",
        "--helper-qn", "OrderBLoC.fetchOrder",
        "--caller-qn", "OrderBLoC.handleRefresh",
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
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in fetchOrder"]),
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
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in fetchOrder"]),
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
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in fetchOrder"]),
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
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in fetchOrder"]),
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
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in fetchOrder"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "Bug is local to the BLoC layer; no cross-layer trace needed.",
                "--cites", json.dumps(["FetchConsumer.handleResult"]),
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
                "--class-qn", "OrderBLoC",
                "--method-qn", "OldFetchOrderMethod",
                "--verified-via", "search_code",
            ])
            r = _run([
                "--devforge-dir", str(devforge), "set-recommended-approach",
                "--name", "Option A: fetch-id guard",
                "--rationale", "Fetch-id guard closes the race",
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in fetchOrder"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "Bug is local to BLoC; OldFetchOrderMethod was already removed.",
                "--cites", json.dumps(["OldFetchOrderMethod"]),
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
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in fetchOrder"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "fetchId is a BLoC-internal counter; bug is layer-local.",
                "--cites", json.dumps(["fetchId"]),
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
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in fetchOrder"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "fetchId is a BLoC-internal counter scoped to OrderBLoC.",
                "--cites", json.dumps(["lib/blocs/order_bloc.dart:42"]),
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
                {"qn": "OrderBLoC.fetchOrder", "file_line": "lib/blocs/order_bloc.dart:42"},
            ]
            data["inbound_callers"] = [
                {"helper_qn": "OrderBLoC.fetchOrder", "caller_qn": "OrderBLoC.handleRefresh",
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
                {"qn": "OrderBLoC.fetchOrder", "file_line": "lib/blocs/order_bloc.dart:42"},
            ]
            data["inbound_callers"] = [
                {"helper_qn": "OrderBLoC.fetchOrder", "caller_qn": "OrderBLoC.handleRefresh",
                 "file_line": "lib/blocs/order_bloc.dart:5"},
            ]
            if data.get("recommended_approach"):
                # Has justification but no cites.
                data["recommended_approach"]["single_layer_justification"] = (
                    "Bug is layer-local to OrderBLoC."
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
                "--hypotheses-addressed", json.dumps(["last-fetch-wins racing in fetchOrder"]),
                "--hypotheses-not-covered", json.dumps([]),
                "--single-layer-justification", "Bug is local to BLoC layer; consumer chain confirms layer-locality.",
                "--cites", json.dumps(["FetchConsumer.handleResult"]),
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


if __name__ == "__main__":
    unittest.main()
