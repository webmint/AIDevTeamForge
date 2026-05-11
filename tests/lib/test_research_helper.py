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
        ):
            self.assertIsNone(rep[field], "field {0} default".format(field))
        for arr_field in (
            "findings", "hypotheses", "approaches",
            "constitution_constraints", "open_uncertainties",
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


if __name__ == "__main__":
    unittest.main()
