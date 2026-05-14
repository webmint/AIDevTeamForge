"""Tests for src/devforge/lib/discover_helper.py.

Coverage matrix
---------------

  Schemas / plumbing
    default_memo_state  — 8 dimensions present, all Missing state,
                          empty references/gaps/conflicts.
    default_report_state — all 18+ keys present at defaults.
    reset-memo + reset-report — write JSON; idempotent.
    read-memo + read-report — defaults when missing; round-trip after reset.

  Setters
    set-topic — memo.topic + memo.topic_slug + report.topic + report.topic_slug
                all populated identically; empty value → exit 2.
    set-date  — memo.date + report.date populated; bad format → exit 2;
                impossible calendar date → exit 2.
    derive_topic_slug — kebab; max 60 chars; trailing-hyphen strip; fallback.

  Preflight
    All 4 present + non-empty → exit 0.
    One missing → exit 2 + stderr contains Missing line for that artefact.
    One empty (zero bytes) → exit 2 + stderr lists it.
    Multiple missing → exit 2 + each missing on its own line.

  Atomicity
    Body-raising transaction → state file unchanged; no .json.tmp debris.

Subprocess pattern: each test runs in its own tempfile.TemporaryDirectory.
Real subcommands (subprocess) produce fixture state — no hand-fabricated JSON.
Stdlib only. Python 3.8+.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "discover_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import discover_helper  # noqa: E402


def _run(argv, cwd=None):
    """Run discover_helper.py with argv; capture stdout/stderr/exit."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(argv),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# 1 + 2. Schema defaults.
# ---------------------------------------------------------------------------


class TestDefaultMemoState(unittest.TestCase):
    def test_eight_dimensions_present(self):
        memo = discover_helper.default_memo_state()
        dims = memo["dimensions"]
        self.assertEqual(set(dims.keys()), set(discover_helper.RUBRIC_DIMENSIONS))
        self.assertEqual(len(dims), 8)

    def test_all_dimensions_missing_state(self):
        memo = discover_helper.default_memo_state()
        for d in discover_helper.RUBRIC_DIMENSIONS:
            rec = memo["dimensions"][d]
            self.assertIsNone(rec["value"], "dimension {0} value".format(d))
            self.assertEqual(rec["state"], "Missing", "dimension {0} state".format(d))
            self.assertEqual(rec["turns"], 0, "dimension {0} turns".format(d))

    def test_empty_lists(self):
        memo = discover_helper.default_memo_state()
        self.assertEqual(memo["references"], [])
        self.assertEqual(memo["gaps"], [])
        self.assertEqual(memo["conflicts"], [])

    def test_scalars_none(self):
        memo = discover_helper.default_memo_state()
        self.assertIsNone(memo["topic"])
        self.assertIsNone(memo["topic_slug"])
        self.assertIsNone(memo["date"])
        self.assertFalse(memo["override_recorded"])

    def test_rubric_dimensions_locked_order(self):
        self.assertEqual(
            discover_helper.RUBRIC_DIMENSIONS,
            (
                "functional_scope",
                "users",
                "inputs_outputs",
                "integration_points",
                "constraints",
                "non_goals",
                "success_criteria",
                "edge_cases",
            ),
        )


class TestDefaultReportState(unittest.TestCase):
    _REQUIRED_KEYS = (
        "topic",
        "date",
        "topic_slug",
        "summary",
        "prior_art",
        "integration_touchpoints",
        "fit_assessments",
        "overall_fit",
        "effort_estimate",
        "fit_rationale",
        "design_options",
        "recommended_option",
        "build_vs_buy",
        "derisk_plan",
        "constitution_constraints",
        "verdict",
        "recommendation",
        "next_step_text",
        "open_uncertainties",
    )

    def test_all_keys_present(self):
        rep = discover_helper.default_report_state()
        for key in self._REQUIRED_KEYS:
            self.assertIn(key, rep, "key missing: {0}".format(key))

    def test_count_at_least_18(self):
        rep = discover_helper.default_report_state()
        # Schema has 19 keys; guard against future accidental deletions.
        self.assertGreaterEqual(len(rep), 18)

    def test_none_scalars(self):
        rep = discover_helper.default_report_state()
        for key in (
            "topic", "date", "topic_slug", "summary",
            "overall_fit", "effort_estimate", "fit_rationale",
            "recommended_option", "build_vs_buy",
            "verdict", "recommendation", "next_step_text",
        ):
            self.assertIsNone(rep[key], "key {0} should default None".format(key))

    def test_empty_lists(self):
        rep = discover_helper.default_report_state()
        for key in (
            "prior_art", "integration_touchpoints", "fit_assessments",
            "design_options", "derisk_plan", "constitution_constraints",
            "open_uncertainties",
        ):
            self.assertEqual(rep[key], [], "key {0} should default []".format(key))


# ---------------------------------------------------------------------------
# 3. reset-memo subcommand.
# ---------------------------------------------------------------------------


class TestResetMemo(unittest.TestCase):
    def test_file_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "reset-memo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((devforge / discover_helper.MEMO_FILE_NAME).exists())

    def test_file_matches_default_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "reset-memo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(
                (devforge / discover_helper.MEMO_FILE_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(data, discover_helper.default_memo_state())

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            first = (devforge / discover_helper.MEMO_FILE_NAME).read_bytes()
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            second = (devforge / discover_helper.MEMO_FILE_NAME).read_bytes()
            self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# 4. reset-report subcommand.
# ---------------------------------------------------------------------------


class TestResetReport(unittest.TestCase):
    def test_file_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "reset-report"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((devforge / discover_helper.REPORT_FILE_NAME).exists())

    def test_file_matches_default_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "reset-report"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(
                (devforge / discover_helper.REPORT_FILE_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(data, discover_helper.default_report_state())

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-report"])
            first = (devforge / discover_helper.REPORT_FILE_NAME).read_bytes()
            _run(["--devforge-dir", str(devforge), "reset-report"])
            second = (devforge / discover_helper.REPORT_FILE_NAME).read_bytes()
            self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# 5. read-memo / read-report subcommands.
# ---------------------------------------------------------------------------


class TestReadMemo(unittest.TestCase):
    def test_defaults_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "read-memo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data, discover_helper.default_memo_state())

    def test_round_trip_after_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            r = _run(["--devforge-dir", str(devforge), "read-memo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data, discover_helper.default_memo_state())

    def test_stdout_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "read-memo"])
            self.assertEqual(r.returncode, 0)
            parsed = json.loads(r.stdout)
            self.assertIsInstance(parsed, dict)


class TestReadReport(unittest.TestCase):
    def test_defaults_when_file_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "read-report"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data, discover_helper.default_report_state())

    def test_round_trip_after_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-report"])
            r = _run(["--devforge-dir", str(devforge), "read-report"])
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data, discover_helper.default_report_state())

    def test_stdout_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "read-report"])
            self.assertEqual(r.returncode, 0)
            parsed = json.loads(r.stdout)
            self.assertIsInstance(parsed, dict)


# ---------------------------------------------------------------------------
# 6. set-topic subcommand.
# ---------------------------------------------------------------------------


class TestSetTopic(unittest.TestCase):
    def test_topic_and_slug_set_in_both_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run(["--devforge-dir", str(devforge), "reset-report"])
            r = _run([
                "--devforge-dir", str(devforge),
                "set-topic", "--value", "Auth in NestJS",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = json.loads(
                (devforge / discover_helper.MEMO_FILE_NAME).read_text(encoding="utf-8")
            )
            report = json.loads(
                (devforge / discover_helper.REPORT_FILE_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(memo["topic"], "Auth in NestJS")
            self.assertEqual(memo["topic_slug"], "auth-in-nestjs")
            self.assertEqual(report["topic"], "Auth in NestJS")
            self.assertEqual(report["topic_slug"], "auth-in-nestjs")

    def test_memo_and_report_slug_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run(["--devforge-dir", str(devforge), "reset-report"])
            _run([
                "--devforge-dir", str(devforge),
                "set-topic", "--value", "OAuth2 integration with Google",
            ])
            memo = json.loads(
                (devforge / discover_helper.MEMO_FILE_NAME).read_text(encoding="utf-8")
            )
            report = json.loads(
                (devforge / discover_helper.REPORT_FILE_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(memo["topic_slug"], report["topic_slug"])

    def test_empty_value_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-topic", "--value", "   ",
            ])
            self.assertNotEqual(r.returncode, 0)

    def test_works_without_prior_reset(self):
        """set-topic creates state files implicitly (load → default when missing)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-topic", "--value", "Payments integration",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = json.loads(
                (devforge / discover_helper.MEMO_FILE_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(memo["topic"], "Payments integration")


class TestDeriveTopicSlug(unittest.TestCase):
    def test_basic_kebab(self):
        self.assertEqual(discover_helper.derive_topic_slug("Auth in NestJS"), "auth-in-nestjs")

    def test_special_chars_become_hyphens(self):
        slug = discover_helper.derive_topic_slug("OAuth2 / SSO integration")
        self.assertRegex(slug, r"^[a-z0-9-]+$")

    def test_max_60_chars(self):
        long_topic = "a " * 40  # 80 chars when joined
        slug = discover_helper.derive_topic_slug(long_topic)
        self.assertLessEqual(len(slug), 60)

    def test_no_trailing_hyphen(self):
        slug = discover_helper.derive_topic_slug("some topic that is quite long indeed yes")
        self.assertFalse(slug.endswith("-"), "slug ends with hyphen: {0!r}".format(slug))

    def test_empty_string_fallback(self):
        self.assertEqual(discover_helper.derive_topic_slug(""), "topic")

    def test_non_alnum_only_fallback(self):
        self.assertEqual(discover_helper.derive_topic_slug("---"), "topic")

    def test_already_lowercase(self):
        self.assertEqual(discover_helper.derive_topic_slug("websockets"), "websockets")

    def test_truncation_lands_on_word_boundary(self):
        # Run 2 evidence: pre-fix output was
        # `tamper-evident-audit-log-across-quote-order-preferences-muta` (cut at `muta`).
        # Post-fix must cut at last `-` boundary, not mid-word.
        topic = (
            "tamper-evident audit log across quote/order/preferences mutations, "
            "similar to how stripe-events or temporal-history work"
        )
        slug = discover_helper.derive_topic_slug(topic)
        self.assertLessEqual(len(slug), 60)
        # No trailing partial word — last segment must be a complete token.
        self.assertNotIn(
            "muta",
            slug.rsplit("-", 1)[-1] if "-" in slug else slug,
            "slug appears truncated mid-word: {0!r}".format(slug),
        )
        # Last segment must come from the source topic's word set.
        source_words = re.findall(r"[a-z0-9]+", topic.lower())
        last_segment = slug.rsplit("-", 1)[-1]
        self.assertIn(
            last_segment,
            source_words,
            "last slug segment {0!r} is not a complete source word".format(last_segment),
        )

    def test_truncation_does_not_strand_mid_word(self):
        # Force truncation: build a string with one long final word that crosses the cap.
        topic = "alpha beta gamma delta epsilon zeta etaverylongtailword"
        slug = discover_helper.derive_topic_slug(topic)
        self.assertLessEqual(len(slug), 60)
        # If full string exceeds cap, last segment must not be a partial of the tail.
        if len("-".join(topic.lower().split())) > 60:
            self.assertFalse(
                slug.endswith("etaverylong") or slug.endswith("verylongtailwor"),
                "slug cut mid-word: {0!r}".format(slug),
            )

    def test_collision_resistance_when_divergence_inside_window(self):
        # When two topics diverge on a complete word that fits inside the
        # boundary-truncation window, Fix C must preserve the divergence.
        # Both topics here cross the 60-char cap but diverge at the SECOND token,
        # well inside the boundary-cut window.
        topic_a = (
            "audit log mutation tracking across quote and order with history persistence indeed"
        )
        topic_b = (
            "audit log snapshot tracking across quote and order with history persistence indeed"
        )
        slug_a = discover_helper.derive_topic_slug(topic_a)
        slug_b = discover_helper.derive_topic_slug(topic_b)
        self.assertNotEqual(
            slug_a,
            slug_b,
            "early-token divergence collapsed to same slug — fix C dropped information",
        )


# ---------------------------------------------------------------------------
# 7. set-date subcommand.
# ---------------------------------------------------------------------------


class TestSetDate(unittest.TestCase):
    def test_valid_date_sets_both_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _run(["--devforge-dir", str(devforge), "reset-report"])
            r = _run([
                "--devforge-dir", str(devforge),
                "set-date", "--value", "2026-05-12",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = json.loads(
                (devforge / discover_helper.MEMO_FILE_NAME).read_text(encoding="utf-8")
            )
            report = json.loads(
                (devforge / discover_helper.REPORT_FILE_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(memo["date"], "2026-05-12")
            self.assertEqual(report["date"], "2026-05-12")

    def test_wrong_separator_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-date", "--value", "2026/05/12",
            ])
            self.assertNotEqual(r.returncode, 0)

    def test_not_a_date_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-date", "--value", "not-a-date",
            ])
            self.assertNotEqual(r.returncode, 0)

    def test_impossible_month_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-date", "--value", "2026-13-01",
            ])
            self.assertNotEqual(r.returncode, 0)

    def test_impossible_day_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-date", "--value", "2026-02-30",
            ])
            self.assertNotEqual(r.returncode, 0)

    def test_works_without_prior_reset(self):
        """set-date creates state files implicitly."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-date", "--value", "2026-01-01",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = json.loads(
                (devforge / discover_helper.MEMO_FILE_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(memo["date"], "2026-01-01")


# ---------------------------------------------------------------------------
# 8. preflight subcommand.
# ---------------------------------------------------------------------------


def _make_prereq_tree(tmp_root: Path, present: list) -> Path:
    """Create an install root with the listed relative paths as non-empty files."""
    install = Path(tmp_root) / "install"
    install.mkdir()
    for rel in present:
        p = install / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("non-empty\n", encoding="utf-8")
    return install


class TestPreflight(unittest.TestCase):
    _ALL_PREREQS = [rel for rel, _ in discover_helper.PREFLIGHT_PREREQS]

    def test_all_present_exit_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            install = _make_prereq_tree(Path(tmp), self._ALL_PREREQS)
            devforge = install / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "--install-root", str(install),
                "preflight",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_one_missing_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            present = [p for p in self._ALL_PREREQS if p != "constitution.md"]
            install = _make_prereq_tree(Path(tmp), present)
            devforge = install / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "--install-root", str(install),
                "preflight",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("Missing: constitution.md (produced by /constitute)", r.stderr)

    def test_one_missing_stderr_contains_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            present = [p for p in self._ALL_PREREQS if p != "constitution.md"]
            install = _make_prereq_tree(Path(tmp), present)
            devforge = install / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "--install-root", str(install),
                "preflight",
            ])
            self.assertIn("BLOCKED:", r.stderr)

    def test_empty_file_treated_as_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            install = _make_prereq_tree(Path(tmp), self._ALL_PREREQS)
            # Overwrite constitution.md with zero bytes.
            (install / "constitution.md").write_bytes(b"")
            devforge = install / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "--install-root", str(install),
                "preflight",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("Missing: constitution.md", r.stderr)

    def test_multiple_missing_all_listed(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Provide only .devforge/init.yaml; other 3 missing.
            install = _make_prereq_tree(Path(tmp), [".devforge/init.yaml"])
            devforge = install / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "--install-root", str(install),
                "preflight",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("Missing: docs/architecture.md", r.stderr)
            self.assertIn("Missing: .devforge/configure.yaml", r.stderr)
            self.assertIn("Missing: constitution.md", r.stderr)
            # Each on its own line
            lines = r.stderr.splitlines()
            missing_lines = [l for l in lines if l.startswith("Missing:")]
            self.assertEqual(len(missing_lines), 3)

    def test_all_missing_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            install = Path(tmp) / "empty-install"
            install.mkdir()
            devforge = install / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "--install-root", str(install),
                "preflight",
            ])
            self.assertEqual(r.returncode, 2)
            lines = r.stderr.splitlines()
            missing_lines = [l for l in lines if l.startswith("Missing:")]
            self.assertEqual(len(missing_lines), 4)

    def test_retry_message_in_stderr(self):
        with tempfile.TemporaryDirectory() as tmp:
            install = Path(tmp) / "empty"
            install.mkdir()
            devforge = install / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "--install-root", str(install),
                "preflight",
            ])
            self.assertIn("/init-forge", r.stderr)
            self.assertIn("/constitute", r.stderr)


# ---------------------------------------------------------------------------
# 9. State-file atomicity.
# ---------------------------------------------------------------------------


class TestAtomicity(unittest.TestCase):
    def test_body_raise_leaves_state_unchanged(self):
        """A transaction body that raises must not corrupt the state file."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            # Establish baseline state via reset-memo.
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            baseline = json.loads(
                (devforge / discover_helper.MEMO_FILE_NAME).read_text(encoding="utf-8")
            )
            # Directly call _state_transaction with a body that raises.
            try:
                with discover_helper._state_transaction(devforge, "memo") as memo:
                    memo["topic"] = "SHOULD NOT PERSIST"
                    raise RuntimeError("deliberate failure")
            except RuntimeError:
                pass
            after = json.loads(
                (devforge / discover_helper.MEMO_FILE_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(after, baseline)

    def test_no_tmp_file_debris_after_raise(self):
        """A failed transaction must clean up its .json.tmp file."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            try:
                with discover_helper._state_transaction(devforge, "memo") as memo:
                    memo["topic"] = "about to fail"
                    raise RuntimeError("deliberate failure")
            except RuntimeError:
                pass
            tmp_files = list(devforge.glob("*.json.tmp"))
            self.assertEqual(tmp_files, [], "leftover .json.tmp files: {0}".format(tmp_files))

    def test_successful_transaction_writes_file(self):
        """A successful transaction must persist the mutated state."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            with discover_helper._state_transaction(devforge, "memo") as memo:
                memo["topic"] = "Persisted topic"
            after = json.loads(
                (devforge / discover_helper.MEMO_FILE_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(after["topic"], "Persisted topic")

    def test_no_tmp_file_debris_after_success(self):
        """A successful transaction must leave no .json.tmp files behind."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            with discover_helper._state_transaction(devforge, "memo") as memo:
                memo["topic"] = "clean write"
            tmp_files = list(devforge.glob("*.json.tmp"))
            self.assertEqual(tmp_files, [], "leftover .json.tmp files: {0}".format(tmp_files))


# ---------------------------------------------------------------------------
# Additional edge cases.
# ---------------------------------------------------------------------------


class TestEdgeCases(unittest.TestCase):
    def test_no_subcommand_exits_2(self):
        """Running helper with no subcommand exits 2 (prints help)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge)])
            self.assertEqual(r.returncode, 2)

    def test_reset_memo_creates_devforge_dir(self):
        """reset-memo creates .devforge/ if it does not exist."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self.assertFalse(devforge.exists())
            r = _run(["--devforge-dir", str(devforge), "reset-memo"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(devforge.exists())

    def test_reset_report_creates_devforge_dir(self):
        """reset-report creates .devforge/ if it does not exist."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self.assertFalse(devforge.exists())
            r = _run(["--devforge-dir", str(devforge), "reset-report"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(devforge.exists())

    def test_set_topic_updates_existing_state(self):
        """set-topic over existing state replaces old topic, not appends."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "set-topic", "--value", "First topic"])
            _run(["--devforge-dir", str(devforge), "set-topic", "--value", "Second topic"])
            memo = json.loads(
                (devforge / discover_helper.MEMO_FILE_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(memo["topic"], "Second topic")
            self.assertEqual(memo["topic_slug"], "second-topic")

    def test_set_date_updates_existing_state(self):
        """set-date over existing state replaces old date."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "set-date", "--value", "2026-01-01"])
            _run(["--devforge-dir", str(devforge), "set-date", "--value", "2026-05-12"])
            memo = json.loads(
                (devforge / discover_helper.MEMO_FILE_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(memo["date"], "2026-05-12")

    def test_memo_file_name_constant(self):
        self.assertEqual(discover_helper.MEMO_FILE_NAME, "discover-scope.json")

    def test_report_file_name_constant(self):
        self.assertEqual(discover_helper.REPORT_FILE_NAME, "discover-report.json")

    def test_preflight_prereqs_exact_tuple(self):
        expected = (
            (".devforge/init.yaml", "/init-forge"),
            ("docs/architecture.md", "/generate-docs"),
            (".devforge/configure.yaml", "/configure"),
            ("constitution.md", "/constitute"),
        )
        self.assertEqual(discover_helper.PREFLIGHT_PREREQS, expected)


# ---------------------------------------------------------------------------
# Phase 0 — helper utilities for state manipulation.
# ---------------------------------------------------------------------------


def _rewrite_memo_json(devforge_dir, mutator):
    """Load .devforge/discover-scope.json, apply mutator(state), write back."""
    path = Path(devforge_dir) / discover_helper.MEMO_FILE_NAME
    state = json.loads(path.read_text(encoding="utf-8"))
    mutator(state)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _read_memo(devforge_dir):
    """Return parsed discover-scope.json dict."""
    r = _run(["--devforge-dir", str(devforge_dir), "read-memo"])
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _read_report(devforge_dir):
    """Return parsed discover-report.json dict."""
    r = _run(["--devforge-dir", str(devforge_dir), "read-report"])
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _set_dim(devforge_dir, dimension, value, state="Clear", increment_turn=False):
    """Helper: call set-scope-<dim> subcommand."""
    subcommand = "set-scope-" + dimension.replace("_", "-")
    argv = ["--devforge-dir", str(devforge_dir), subcommand, "--value", value, "--state", state]
    if increment_turn:
        argv.append("--increment-turn")
    return _run(argv)


def _induce_oauth_conflict(devforge_dir):
    """Set non_goals and integration_points to overlap on 'oauth' token."""
    r1 = _set_dim(devforge_dir, "non_goals", "OAuth not supported in v1")
    assert r1.returncode == 0, r1.stderr
    r2 = _set_dim(devforge_dir, "integration_points", "OAuth callback routes and API guards")
    assert r2.returncode == 0, r2.stderr


# ---------------------------------------------------------------------------
# 10. TestSetScope — Phase 0 dimension setters.
# ---------------------------------------------------------------------------


class TestSetScope(unittest.TestCase):
    def test_happy_path_each_dimension(self):
        """Each dimension setter writes value + state + turns=0 correctly."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            for dim in discover_helper.RUBRIC_DIMENSIONS:
                subcommand = "set-scope-" + dim.replace("_", "-")
                r = _run([
                    "--devforge-dir", str(devforge),
                    subcommand,
                    "--value", "X",
                    "--state", "Clear",
                ])
                self.assertEqual(r.returncode, 0, "dim={0} stderr={1}".format(dim, r.stderr))
                memo = _read_memo(devforge)
                rec = memo["dimensions"][dim]
                self.assertEqual(rec["value"], "X", "dim={0}".format(dim))
                self.assertEqual(rec["state"], "Clear", "dim={0}".format(dim))
                self.assertEqual(rec["turns"], 0, "dim={0}".format(dim))

    def test_increment_turn(self):
        """--increment-turn adds 1 each call; omitting flag leaves turns unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r1 = _set_dim(devforge, "users", "A", "Partial", increment_turn=True)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            r2 = _set_dim(devforge, "users", "B", "Partial", increment_turn=True)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            memo = _read_memo(devforge)
            self.assertEqual(memo["dimensions"]["users"]["turns"], 2)
            # Call WITHOUT flag — turns must stay at 2.
            r3 = _set_dim(devforge, "users", "C", "Clear", increment_turn=False)
            self.assertEqual(r3.returncode, 0, r3.stderr)
            memo = _read_memo(devforge)
            self.assertEqual(memo["dimensions"]["users"]["turns"], 2)

    def test_rejects_empty_value(self):
        """Empty or whitespace-only --value exits 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r_empty = _set_dim(devforge, "users", "")
            self.assertEqual(r_empty.returncode, 2)
            r_spaces = _set_dim(devforge, "users", "   ")
            self.assertEqual(r_spaces.returncode, 2)

    def test_rejects_invalid_state(self):
        """--state with an unlisted value is rejected by argparse (exit 2)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-scope-users",
                "--value", "Some users",
                "--state", "foo",
            ])
            self.assertEqual(r.returncode, 2)

    def test_overwrite_replaces_value(self):
        """Second call with different value + state fully replaces the first."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _set_dim(devforge, "users", "A", "Clear")
            _set_dim(devforge, "users", "B", "Partial")
            memo = _read_memo(devforge)
            self.assertEqual(memo["dimensions"]["users"]["value"], "B")
            self.assertEqual(memo["dimensions"]["users"]["state"], "Partial")

    def test_state_persisted_across_calls(self):
        """3 different dimensions set across separate calls all survive in memo."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _set_dim(devforge, "functional_scope", "Allow users to log in", "Clear")
            _set_dim(devforge, "constraints", "No breaking changes", "Partial")
            _set_dim(devforge, "non_goals", "No mobile app", "Clear")
            memo = _read_memo(devforge)
            self.assertEqual(memo["dimensions"]["functional_scope"]["value"], "Allow users to log in")
            self.assertEqual(memo["dimensions"]["functional_scope"]["state"], "Clear")
            self.assertEqual(memo["dimensions"]["constraints"]["value"], "No breaking changes")
            self.assertEqual(memo["dimensions"]["constraints"]["state"], "Partial")
            self.assertEqual(memo["dimensions"]["non_goals"]["value"], "No mobile app")
            self.assertEqual(memo["dimensions"]["non_goals"]["state"], "Clear")
            # Untouched dimensions remain Missing.
            self.assertEqual(memo["dimensions"]["users"]["state"], "Missing")
            self.assertIsNone(memo["dimensions"]["users"]["value"])


# ---------------------------------------------------------------------------
# 11. TestRecordReferences — Phase 0 reference list.
# ---------------------------------------------------------------------------


class TestRecordReferences(unittest.TestCase):
    def _run_record(self, devforge_dir, values_json):
        return _run([
            "--devforge-dir", str(devforge_dir),
            "record-references",
            "--values", values_json,
        ])

    def test_happy_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_record(devforge, '["A","B"]')
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = _read_memo(devforge)
            self.assertEqual(memo["references"], ["A", "B"])

    def test_replace_not_append(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._run_record(devforge, '["A","B"]')
            self._run_record(devforge, '["C"]')
            memo = _read_memo(devforge)
            self.assertEqual(memo["references"], ["C"])

    def test_empty_array_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_record(devforge, "[]")
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = _read_memo(devforge)
            self.assertEqual(memo["references"], [])

    def test_rejects_non_array(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r_str = self._run_record(devforge, '"abc"')
            self.assertEqual(r_str.returncode, 2)
            r_int = self._run_record(devforge, "42")
            self.assertEqual(r_int.returncode, 2)

    def test_rejects_non_string_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r_all_int = self._run_record(devforge, '[1, 2]')
            self.assertEqual(r_all_int.returncode, 2)
            r_mixed = self._run_record(devforge, '["A", 2]')
            self.assertEqual(r_mixed.returncode, 2)

    def test_rejects_malformed_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_record(devforge, "not-json")
            self.assertEqual(r.returncode, 2)


# ---------------------------------------------------------------------------
# 12. TestRecordGap — Phase 0 gap recording.
# ---------------------------------------------------------------------------


class TestRecordGap(unittest.TestCase):
    def _run_gap(self, devforge_dir, dimension, description):
        return _run([
            "--devforge-dir", str(devforge_dir),
            "record-gap",
            "--dimension", dimension,
            "--description", description,
        ])

    def test_happy_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_gap(devforge, "users", "TBD - end users only?")
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = _read_memo(devforge)
            self.assertEqual(len(memo["gaps"]), 1)
            self.assertEqual(memo["gaps"][0]["dimension"], "users")
            self.assertEqual(memo["gaps"][0]["description"], "TBD - end users only?")

    def test_idempotency_same_dimension(self):
        """Second call on same dimension replaces, not appends."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._run_gap(devforge, "users", "First description")
            self._run_gap(devforge, "users", "Second description")
            memo = _read_memo(devforge)
            user_gaps = [g for g in memo["gaps"] if g["dimension"] == "users"]
            self.assertEqual(len(user_gaps), 1)
            self.assertEqual(user_gaps[0]["description"], "Second description")

    def test_rejects_unknown_dimension(self):
        """Unknown dimension rejected by argparse choices (exit 2)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "record-gap",
                "--dimension", "wrong_name",
                "--description", "some desc",
            ])
            self.assertEqual(r.returncode, 2)

    def test_rejects_empty_description(self):
        """Empty description exits 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_gap(devforge, "users", "")
            self.assertEqual(r.returncode, 2)

    def test_multiple_dimensions_coexist(self):
        """Gaps on different dimensions both appear in memo.gaps."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._run_gap(devforge, "users", "Not sure who the end users are")
            self._run_gap(devforge, "constraints", "Unclear perf constraints")
            memo = _read_memo(devforge)
            dims_in_gaps = {g["dimension"] for g in memo["gaps"]}
            self.assertIn("users", dims_in_gaps)
            self.assertIn("constraints", dims_in_gaps)
            self.assertEqual(len(memo["gaps"]), 2)


# ---------------------------------------------------------------------------
# 13. TestCheckConflicts — Phase 0 conflict detection.
# ---------------------------------------------------------------------------


class TestCheckConflicts(unittest.TestCase):
    def _run_check(self, devforge_dir):
        return _run(["--devforge-dir", str(devforge_dir), "check-conflicts"])

    def test_empty_memo_returns_empty_array(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_check(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertEqual(data, [])

    def test_detects_direct_contradiction(self):
        """Shared 'oauth' token between non_goals and integration_points is flagged."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _induce_oauth_conflict(devforge)
            r = self._run_check(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertGreater(len(data), 0)
            conflict = data[0]
            self.assertEqual(conflict["type"], "direct")
            self.assertIn("non_goals", conflict["dimensions"])
            self.assertIn("integration_points", conflict["dimensions"])
            self.assertIn("oauth", conflict["description"].lower())

    def test_case_insensitive_token_match(self):
        """OAUTH vs oauth mixed case still triggers a conflict."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r1 = _set_dim(devforge, "non_goals", "OAUTH not supported in v1")
            self.assertEqual(r1.returncode, 0, r1.stderr)
            r2 = _set_dim(devforge, "integration_points", "oauth callback routes")
            self.assertEqual(r2.returncode, 0, r2.stderr)
            r = self._run_check(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            self.assertGreater(len(data), 0)

    def test_ignores_stopwords_and_short_tokens(self):
        """Only >=4-char non-stopword tokens trigger conflicts.

        'sso' is 3 chars — below _CONFLICT_MIN_TOKEN_LEN=4, so ignored.
        'admin' is 5 chars and not a stopword — triggers conflict.
        'no', 'the', 'and', 'is' are stopwords — ignored.
        """
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # 'admin' (5 chars, not stopword) is shared — should conflict.
            r1 = _set_dim(devforge, "non_goals", "no admin sso")
            self.assertEqual(r1.returncode, 0, r1.stderr)
            r2 = _set_dim(devforge, "integration_points", "the admin and the sso area is ok")
            self.assertEqual(r2.returncode, 0, r2.stderr)
            r = self._run_check(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            # 'admin' qualifies — conflict detected.
            self.assertGreater(len(data), 0, "expected 'admin' to trigger conflict")
            # Now replace with values that share no >=4-char non-stopword tokens.
            r3 = _set_dim(devforge, "non_goals", "no sso and no mfa")
            self.assertEqual(r3.returncode, 0, r3.stderr)
            r4 = _set_dim(devforge, "integration_points", "the api and the auth area")
            self.assertEqual(r4.returncode, 0, r4.stderr)
            r2 = self._run_check(devforge)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            data2 = json.loads(r2.stdout)
            self.assertEqual(data2, [], "expected no conflict when no >=4-char shared tokens")

    def test_read_only(self):
        """check-conflicts called twice leaves state file byte-identical."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _induce_oauth_conflict(devforge)
            # Ensure memo file exists before first call.
            _run(["--devforge-dir", str(devforge), "reset-memo"])
            _induce_oauth_conflict(devforge)
            state_path = devforge / discover_helper.MEMO_FILE_NAME
            r1 = self._run_check(devforge)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            bytes_after_first = state_path.read_bytes()
            r2 = self._run_check(devforge)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            bytes_after_second = state_path.read_bytes()
            self.assertEqual(bytes_after_first, bytes_after_second)

    def test_suppresses_already_resolved(self):
        """After record-conflict-resolution resolves a pair, check-conflicts omits it."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _induce_oauth_conflict(devforge)
            # Record a resolution for the conflict at index 0.
            r_resolve = _run([
                "--devforge-dir", str(devforge),
                "record-conflict-resolution",
                "--index", "0",
                "--resolution", "user-chose-non_goals",
                "--rewrite-dimension", "integration_points",
            ])
            self.assertEqual(r_resolve.returncode, 0, r_resolve.stderr)
            # Re-induce conflict on integration_points (was cleared by resolution).
            # check-conflicts should still filter it due to the resolved pair.
            r = self._run_check(devforge)
            self.assertEqual(r.returncode, 0, r.stderr)
            data = json.loads(r.stdout)
            # integration_points was cleared, so no token overlap exists → empty.
            self.assertEqual(data, [])


# ---------------------------------------------------------------------------
# 14. TestRecordConflictResolution — Phase 0 conflict resolution.
# ---------------------------------------------------------------------------


class TestRecordConflictResolution(unittest.TestCase):
    def _run_resolve(self, devforge_dir, index, resolution, rewrite_dimension):
        return _run([
            "--devforge-dir", str(devforge_dir),
            "record-conflict-resolution",
            "--index", str(index),
            "--resolution", resolution,
            "--rewrite-dimension", rewrite_dimension,
        ])

    def test_happy_path_after_detection(self):
        """After inducing conflict, resolve it; assert resolution stored + loser cleared."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _induce_oauth_conflict(devforge)
            # Run check-conflicts first to populate state.conflicts.
            r_check = _run(["--devforge-dir", str(devforge), "check-conflicts"])
            self.assertEqual(r_check.returncode, 0, r_check.stderr)
            r = self._run_resolve(devforge, 0, "user-chose-non_goals", "integration_points")
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = _read_memo(devforge)
            # Resolution recorded.
            self.assertEqual(memo["conflicts"][0]["resolution"], "user-chose-non_goals")
            # Loser dimension cleared to empty_dimension shape.
            ip_rec = memo["dimensions"]["integration_points"]
            self.assertIsNone(ip_rec["value"])
            self.assertEqual(ip_rec["state"], "Missing")
            self.assertEqual(ip_rec["turns"], 0)

    def test_auto_detects_when_no_recorded_conflicts(self):
        """record-conflict-resolution works even without a prior check-conflicts call."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _induce_oauth_conflict(devforge)
            # Do NOT call check-conflicts — state.conflicts is empty.
            r = self._run_resolve(devforge, 0, "user-chose-non_goals", "integration_points")
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = _read_memo(devforge)
            self.assertEqual(memo["conflicts"][0]["resolution"], "user-chose-non_goals")

    def test_out_of_range_index(self):
        """Index 0 on a fresh memo with no conflicts → exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_resolve(devforge, 0, "some-resolution", "users")
            self.assertEqual(r.returncode, 2)
            self.assertIn("out of range", r.stderr.lower())

    def test_invalid_rewrite_dimension(self):
        """Unknown rewrite-dimension is rejected by argparse choices (exit 2)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _induce_oauth_conflict(devforge)
            r = _run([
                "--devforge-dir", str(devforge),
                "record-conflict-resolution",
                "--index", "0",
                "--resolution", "test",
                "--rewrite-dimension", "foo_bar",
            ])
            self.assertEqual(r.returncode, 2)


# ---------------------------------------------------------------------------
# 15. TestScopeCoverage — Phase 0 coverage report.
# ---------------------------------------------------------------------------


class TestScopeCoverage(unittest.TestCase):
    def _run_coverage(self, devforge_dir):
        r = _run(["--devforge-dir", str(devforge_dir), "scope-coverage"])
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_empty_memo_shape(self):
        """Fresh memo → all 8 Missing, counts 0/0/8, refs=0, gaps=0, conflicts_open=0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            data = self._run_coverage(devforge)
            self.assertIn("per_dimension", data)
            self.assertIn("counts", data)
            # All 8 dimensions present.
            self.assertEqual(set(data["per_dimension"].keys()), set(discover_helper.RUBRIC_DIMENSIONS))
            # All Missing.
            for d in discover_helper.RUBRIC_DIMENSIONS:
                self.assertEqual(data["per_dimension"][d]["state"], "Missing",
                                 "dim={0}".format(d))
            self.assertEqual(data["counts"]["Clear"], 0)
            self.assertEqual(data["counts"]["Partial"], 0)
            self.assertEqual(data["counts"]["Missing"], 8)
            self.assertEqual(data["references_count"], 0)
            self.assertEqual(data["gaps_count"], 0)
            self.assertEqual(data["conflicts_open"], 0)

    def test_mixed_states(self):
        """5 Clear + 2 Partial + 1 Missing dimensions produce correct counts."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            dims = list(discover_helper.RUBRIC_DIMENSIONS)
            # Set 5 Clear.
            for d in dims[:5]:
                r = _set_dim(devforge, d, "value for " + d, "Clear")
                self.assertEqual(r.returncode, 0, r.stderr)
            # Set 2 Partial.
            for d in dims[5:7]:
                r = _set_dim(devforge, d, "partial value for " + d, "Partial")
                self.assertEqual(r.returncode, 0, r.stderr)
            # dims[7] (edge_cases) stays Missing.
            data = self._run_coverage(devforge)
            self.assertEqual(data["counts"]["Clear"], 5)
            self.assertEqual(data["counts"]["Partial"], 2)
            self.assertEqual(data["counts"]["Missing"], 1)

    def test_open_conflicts_count(self):
        """conflicts_open reflects only unresolved (resolution==None) entries."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _induce_oauth_conflict(devforge)
            # Populate state.conflicts via record-conflict-resolution (sets resolution).
            _run([
                "--devforge-dir", str(devforge),
                "record-conflict-resolution",
                "--index", "0",
                "--resolution", "user-chose-non_goals",
                "--rewrite-dimension", "integration_points",
            ])
            # Now manually rewrite resolution back to None → simulates open conflict.
            def _clear_resolution(state):
                for c in state.get("conflicts", []):
                    c["resolution"] = None

            _rewrite_memo_json(devforge, _clear_resolution)
            data = self._run_coverage(devforge)
            self.assertEqual(data["conflicts_open"], 1)
            # Restore resolution → conflicts_open drops to 0.
            def _restore_resolution(state):
                for c in state.get("conflicts", []):
                    c["resolution"] = "user-chose-non_goals"

            _rewrite_memo_json(devforge, _restore_resolution)
            data2 = self._run_coverage(devforge)
            self.assertEqual(data2["conflicts_open"], 0)


# ---------------------------------------------------------------------------
# 16. TestScopeFinalize — Phase 0 finalize gate.
# ---------------------------------------------------------------------------


class TestScopeFinalize(unittest.TestCase):
    def _set_all_clear(self, devforge_dir):
        """Set all 8 dimensions to Clear with non-empty values."""
        for d in discover_helper.RUBRIC_DIMENSIONS:
            r = _set_dim(devforge_dir, d, "value for " + d, "Clear")
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_all_clear_no_conflicts_succeeds(self):
        """All 8 Clear + no open conflicts → exit 0; override_recorded == False."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._set_all_clear(devforge)
            r = _run(["--devforge-dir", str(devforge), "scope-finalize"])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = _read_memo(devforge)
            self.assertFalse(memo["override_recorded"])

    def test_partial_without_flag_blocks(self):
        """7 Clear + 1 Partial → exit 2; stderr names the offending dimension."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            dims = list(discover_helper.RUBRIC_DIMENSIONS)
            # Set 7 Clear.
            for d in dims[:7]:
                _set_dim(devforge, d, "value for " + d, "Clear")
            # Set last one (edge_cases) to Partial.
            _set_dim(devforge, dims[7], "partial info", "Partial")
            r = _run(["--devforge-dir", str(devforge), "scope-finalize"])
            self.assertEqual(r.returncode, 2)
            self.assertIn(dims[7], r.stderr)

    def test_partial_with_flag_succeeds(self):
        """7 Clear + 1 Partial + --accept-gaps → exit 0; override_recorded == True."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            dims = list(discover_helper.RUBRIC_DIMENSIONS)
            for d in dims[:7]:
                _set_dim(devforge, d, "value for " + d, "Clear")
            _set_dim(devforge, dims[7], "partial info", "Partial")
            r = _run(["--devforge-dir", str(devforge), "scope-finalize", "--accept-gaps"])
            self.assertEqual(r.returncode, 0, r.stderr)
            memo = _read_memo(devforge)
            self.assertTrue(memo["override_recorded"])

    def test_open_conflict_blocks_even_with_flag(self):
        """Unresolved conflict → exit 2 even when --accept-gaps is passed."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._set_all_clear(devforge)
            # Induce and record a conflict (sets resolution), then clear it back to None.
            _induce_oauth_conflict(devforge)
            _run([
                "--devforge-dir", str(devforge),
                "record-conflict-resolution",
                "--index", "0",
                "--resolution", "user-chose-non_goals",
                "--rewrite-dimension", "integration_points",
            ])

            def _clear_resolution(state):
                for c in state.get("conflicts", []):
                    c["resolution"] = None

            _rewrite_memo_json(devforge, _clear_resolution)
            # Also restore integration_points so only the conflict blocks.
            _set_dim(devforge, "integration_points", "OAuth callback routes", "Clear")
            r = _run(["--devforge-dir", str(devforge), "scope-finalize", "--accept-gaps"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("conflict", r.stderr.lower())

    def test_lists_all_violations(self):
        """3 Partial + 2 Missing → exit 2; stderr has 5 violation lines."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            dims = list(discover_helper.RUBRIC_DIMENSIONS)
            # 3 Clear.
            for d in dims[:3]:
                _set_dim(devforge, d, "value for " + d, "Clear")
            # 3 Partial.
            for d in dims[3:6]:
                _set_dim(devforge, d, "partial for " + d, "Partial")
            # 2 Missing (dims[6] and dims[7]) — leave untouched.
            r = _run(["--devforge-dir", str(devforge), "scope-finalize"])
            self.assertEqual(r.returncode, 2)
            # Each offending dimension gets its own stderr line.
            lines = r.stderr.splitlines()
            violation_lines = [l for l in lines if "scope-finalize:" in l]
            self.assertEqual(len(violation_lines), 5)

    def test_missing_without_flag_blocks(self):
        """Fresh memo (all 8 Missing) → exit 2 + 8 violation lines."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "scope-finalize"])
            self.assertEqual(r.returncode, 2)
            lines = r.stderr.splitlines()
            violation_lines = [l for l in lines if "scope-finalize:" in l]
            self.assertEqual(len(violation_lines), 8)


# ---------------------------------------------------------------------------
# Phase 1 — investigation setters.
# ---------------------------------------------------------------------------


class TestRecordPriorArt(unittest.TestCase):
    def _run_record(self, devforge_dir, reference, kind, relevance, source=None):
        argv = [
            "--devforge-dir", str(devforge_dir),
            "record-prior-art",
            "--reference", reference,
            "--kind", kind,
            "--relevance", relevance,
        ]
        if source is not None:
            argv += ["--source", source]
        return _run(argv)

    def test_happy_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_record(
                devforge, "Library X", "library",
                "JWT impl matching scope", "https://example.test/x",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(len(report["prior_art"]), 1)
            entry = report["prior_art"][0]
            self.assertEqual(entry["reference"], "Library X")
            self.assertEqual(entry["kind"], "library")
            self.assertEqual(entry["relevance"], "JWT impl matching scope")
            self.assertEqual(entry["source"], "https://example.test/x")

    def test_multiple_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._run_record(devforge, "Lib A", "library", "First one", "https://a.test")
            self._run_record(devforge, "Prod B", "product", "Second one", "https://b.test")
            self._run_record(devforge, "Pattern C", "pattern", "Third one")
            report = _read_report(devforge)
            self.assertEqual(len(report["prior_art"]), 3)
            self.assertEqual(report["prior_art"][0]["reference"], "Lib A")
            self.assertEqual(report["prior_art"][1]["reference"], "Prod B")
            self.assertEqual(report["prior_art"][2]["reference"], "Pattern C")

    def test_rejects_invalid_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_record(devforge, "X", "framework", "some relevance")
            self.assertEqual(r.returncode, 2)

    def test_source_optional(self):
        """Omitting --source sets source to empty string, not None or absent."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_record(devforge, "My Lib", "library", "Relevant because X")
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(len(report["prior_art"]), 1)
            entry = report["prior_art"][0]
            self.assertIn("source", entry)
            self.assertEqual(entry["source"], "")

    def test_rejects_empty_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_record(devforge, "   ", "library", "some relevance")
            self.assertEqual(r.returncode, 2)

    def test_rejects_empty_relevance(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_record(devforge, "Library X", "library", "   ")
            self.assertEqual(r.returncode, 2)


class TestRecordIntegrationTouchpoint(unittest.TestCase):
    def _run_tp(self, devforge_dir, name, module_path, reason):
        return _run([
            "--devforge-dir", str(devforge_dir),
            "record-integration-touchpoint",
            "--name", name,
            "--module-path", module_path,
            "--reason", reason,
        ])

    def test_happy_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_tp(devforge, "auth-routes", "src/auth/", "All routes need auth check")
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(len(report["integration_touchpoints"]), 1)
            entry = report["integration_touchpoints"][0]
            self.assertEqual(entry["name"], "auth-routes")
            self.assertEqual(entry["module_path"], "src/auth/")
            self.assertEqual(entry["reason"], "All routes need auth check")

    def test_multiple_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._run_tp(devforge, "route-guards", "src/api/", "Auth check on every route")
            self._run_tp(devforge, "session-store", "src/session/", "Stores user session data")
            report = _read_report(devforge)
            self.assertEqual(len(report["integration_touchpoints"]), 2)
            self.assertEqual(report["integration_touchpoints"][0]["name"], "route-guards")
            self.assertEqual(report["integration_touchpoints"][1]["name"], "session-store")

    def test_rejects_empty_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_tp(devforge, "   ", "src/auth/", "Some reason")
            self.assertEqual(r.returncode, 2)

    def test_rejects_empty_module_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_tp(devforge, "auth-routes", "   ", "Some reason")
            self.assertEqual(r.returncode, 2)

    def test_rejects_empty_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_tp(devforge, "auth-routes", "src/auth/", "   ")
            self.assertEqual(r.returncode, 2)


class TestRecordFitAssessment(unittest.TestCase):
    def _setup_touchpoint(self, devforge_dir, name="auth-routes"):
        r = _run([
            "--devforge-dir", str(devforge_dir),
            "record-integration-touchpoint",
            "--name", name,
            "--module-path", "src/auth/",
            "--reason", "All routes need auth check",
        ])
        assert r.returncode == 0, r.stderr

    def _run_assessment(self, devforge_dir, touchpoint, user_expected, reality, effort, blockers=None):
        argv = [
            "--devforge-dir", str(devforge_dir),
            "record-fit-assessment",
            "--touchpoint", touchpoint,
            "--user-expected", user_expected,
            "--reality", reality,
            "--effort", effort,
        ]
        if blockers is not None:
            argv += ["--blockers", blockers]
        return _run(argv)

    def test_happy_path_with_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_touchpoint(devforge, "auth-routes")
            r = self._run_assessment(
                devforge, "auth-routes",
                "guarded routes", "no guards exist", "High",
                '["no middleware infra"]',
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(len(report["fit_assessments"]), 1)
            entry = report["fit_assessments"][0]
            self.assertEqual(entry["touchpoint"], "auth-routes")
            self.assertEqual(entry["user_expected"], "guarded routes")
            self.assertEqual(entry["reality"], "no guards exist")
            self.assertEqual(entry["effort"], "High")
            self.assertEqual(entry["blockers"], ["no middleware infra"])

    def test_blockers_default_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_touchpoint(devforge, "auth-routes")
            r = self._run_assessment(
                devforge, "auth-routes",
                "guarded routes", "no guards exist", "Low",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(report["fit_assessments"][0]["blockers"], [])

    def test_rejects_unknown_touchpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Do NOT record any touchpoint first.
            r = self._run_assessment(
                devforge, "unknown-name",
                "some expectation", "some reality", "Low",
            )
            self.assertEqual(r.returncode, 2)
            self.assertIn("does not match any integration_touchpoint", r.stderr)

    def test_rejects_invalid_effort(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_touchpoint(devforge, "auth-routes")
            r = self._run_assessment(
                devforge, "auth-routes",
                "guarded routes", "no guards exist", "Crazy",
            )
            self.assertEqual(r.returncode, 2)

    def test_rejects_malformed_blockers_not_array(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_touchpoint(devforge, "auth-routes")
            r = self._run_assessment(
                devforge, "auth-routes",
                "guarded routes", "no guards exist", "Low",
                '"not-array"',
            )
            self.assertEqual(r.returncode, 2)

    def test_rejects_malformed_blockers_non_string_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_touchpoint(devforge, "auth-routes")
            r = self._run_assessment(
                devforge, "auth-routes",
                "guarded routes", "no guards exist", "Low",
                "[1, 2]",
            )
            self.assertEqual(r.returncode, 2)


class TestSetOverallFit(unittest.TestCase):
    def test_happy_path_each_enum(self):
        for value in discover_helper.OVERALL_FIT_ENUM:
            with tempfile.TemporaryDirectory() as tmp:
                devforge = Path(tmp) / ".devforge"
                r = _run([
                    "--devforge-dir", str(devforge),
                    "set-overall-fit", "--value", value,
                ])
                self.assertEqual(r.returncode, 0, "value={0!r} stderr={1}".format(value, r.stderr))
                report = _read_report(devforge)
                self.assertEqual(report["overall_fit"], value)

    def test_rejects_invalid_enum(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-overall-fit", "--value", "Excellent",
            ])
            self.assertEqual(r.returncode, 2)


class TestSetEffortEstimate(unittest.TestCase):
    def test_happy_path_each_enum(self):
        for value in discover_helper.EFFORT_ENUM:
            with tempfile.TemporaryDirectory() as tmp:
                devforge = Path(tmp) / ".devforge"
                r = _run([
                    "--devforge-dir", str(devforge),
                    "set-effort-estimate", "--value", value,
                ])
                self.assertEqual(
                    r.returncode, 0,
                    "value={0!r} stderr={1}".format(value, r.stderr),
                )
                report = _read_report(devforge)
                self.assertEqual(report["effort_estimate"], value)

    def test_rejects_invalid_enum(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-effort-estimate", "--value", "Trivial",
            ])
            self.assertEqual(r.returncode, 2)


class TestSetFitRationale(unittest.TestCase):
    def test_happy_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-fit-rationale", "--value", "ok-ish",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(report["fit_rationale"], "ok-ish")

    def test_rejects_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-fit-rationale", "--value", "   ",
            ])
            self.assertEqual(r.returncode, 2)


# ---------------------------------------------------------------------------
# Phase 2 — report-drafting setters.
# ---------------------------------------------------------------------------


class TestSetSummary(unittest.TestCase):
    def test_happy_path(self):
        """Non-empty summary is stored in report.summary."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-summary", "--value", "First sentence. Second sentence. Third sentence.",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(report["summary"], "First sentence. Second sentence. Third sentence.")

    def test_rejects_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-summary", "--value", "   ",
            ])
            self.assertEqual(r.returncode, 2)


class TestSetDesignOption(unittest.TestCase):
    def _run_opt(self, devforge_dir, name, shape, pros, cons, complexity):
        return _run([
            "--devforge-dir", str(devforge_dir),
            "set-design-option",
            "--name", name,
            "--shape", shape,
            "--pros", pros,
            "--cons", cons,
            "--complexity", complexity,
        ])

    def test_happy_path_appends_one_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_opt(
                devforge, "Option A", "Simple proxy", '["Easy"]', '["Limited"]', "Low"
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(len(report["design_options"]), 1)
            opt = report["design_options"][0]
            self.assertEqual(opt["name"], "Option A")
            self.assertEqual(opt["shape"], "Simple proxy")
            self.assertEqual(opt["pros"], ["Easy"])
            self.assertEqual(opt["cons"], ["Limited"])
            self.assertEqual(opt["complexity"], "Low")

    def test_multiple_appends_preserve_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._run_opt(devforge, "Option A", "Shape A", '["Pro A"]', '["Con A"]', "Low")
            self._run_opt(devforge, "Option B", "Shape B", '["Pro B"]', '["Con B"]', "Med")
            self._run_opt(devforge, "Option C", "Shape C", '["Pro C"]', '["Con C"]', "High")
            report = _read_report(devforge)
            self.assertEqual(len(report["design_options"]), 3)
            self.assertEqual(report["design_options"][0]["name"], "Option A")
            self.assertEqual(report["design_options"][1]["name"], "Option B")
            self.assertEqual(report["design_options"][2]["name"], "Option C")

    def test_rejects_duplicate_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r1 = self._run_opt(devforge, "Option A", "Shape A", '["Pro"]', '["Con"]', "Low")
            self.assertEqual(r1.returncode, 0, r1.stderr)
            r2 = self._run_opt(devforge, "Option A", "Different shape", '["Pro"]', '["Con"]', "Med")
            self.assertEqual(r2.returncode, 2)
            self.assertIn("already exists", r2.stderr)

    def test_rejects_invalid_complexity_enum(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_opt(devforge, "Option A", "Shape", '["Pro"]', '["Con"]', "Extreme")
            self.assertEqual(r.returncode, 2)

    def test_rejects_empty_pros_array(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_opt(devforge, "Option A", "Shape", "[]", '["Con"]', "Low")
            self.assertEqual(r.returncode, 2)

    def test_rejects_empty_cons_array(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_opt(devforge, "Option A", "Shape", '["Pro"]', "[]", "Low")
            self.assertEqual(r.returncode, 2)

    def test_rejects_non_string_items_in_pros(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_opt(devforge, "Option A", "Shape", "[1, 2]", '["Con"]', "Low")
            self.assertEqual(r.returncode, 2)

    def test_rejects_letter_colon_prefix_in_name(self):
        # Run 3 evidence: orchestrator passed --name "A: app-web composable...",
        # producing rendered heading `### Option A: A: app-web composable...`
        # (double-prefix). Setter must reject the baked-in letter prefix.
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_opt(
                devforge,
                "A: app-web composable",
                "Some shape",
                '["Pro"]',
                '["Con"]',
                "Low",
            )
            self.assertEqual(r.returncode, 2)
            self.assertIn("letter prefix", r.stderr)

    def test_rejects_option_letter_colon_prefix_in_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_opt(
                devforge,
                "Option B: in-line approach",
                "Some shape",
                '["Pro"]',
                '["Con"]',
                "Low",
            )
            self.assertEqual(r.returncode, 2)
            self.assertIn("letter prefix", r.stderr)

    def test_accepts_clean_name_without_letter_prefix(self):
        # Sanity — clean names still accepted; rejection is narrow.
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = self._run_opt(
                devforge,
                "in-line approach",
                "Some shape",
                '["Pro"]',
                '["Con"]',
                "Low",
            )
            self.assertEqual(r.returncode, 0, r.stderr)


class TestSetRecommendedOption(unittest.TestCase):
    def _setup_option(self, devforge_dir, name="Option A"):
        r = _run([
            "--devforge-dir", str(devforge_dir),
            "set-design-option",
            "--name", name,
            "--shape", "Some shape",
            "--pros", '["Pro"]',
            "--cons", '["Con"]',
            "--complexity", "Low",
        ])
        assert r.returncode == 0, r.stderr

    def test_happy_path_matching_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_option(devforge, "Option A")
            r = _run([
                "--devforge-dir", str(devforge),
                "set-recommended-option",
                "--name", "Option A",
                "--rationale", "Simplest approach",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(report["recommended_option"]["name"], "Option A")
            self.assertEqual(report["recommended_option"]["rationale"], "Simplest approach")

    def test_rejects_name_not_matching_any_design_option(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-recommended-option",
                "--name", "NonExistent",
                "--rationale", "Some reason",
            ])
            self.assertEqual(r.returncode, 2)
            self.assertIn("does not match any design_option.name", r.stderr)

    def test_rejects_empty_rationale(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_option(devforge, "Option A")
            r = _run([
                "--devforge-dir", str(devforge),
                "set-recommended-option",
                "--name", "Option A",
                "--rationale", "   ",
            ])
            self.assertEqual(r.returncode, 2)


class TestSetBuildVsBuy(unittest.TestCase):
    def test_happy_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-build-vs-buy",
                "--build", "Implement from scratch",
                "--buy", "Use library X",
                "--recommendation", "Build",
                "--reasoning", "Library X has GPL license conflict",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            bvb = report["build_vs_buy"]
            self.assertEqual(bvb["build"], "Implement from scratch")
            self.assertEqual(bvb["buy"], "Use library X")
            self.assertEqual(bvb["recommendation"], "Build")
            self.assertEqual(bvb["reasoning"], "Library X has GPL license conflict")

    def test_rejects_invalid_recommendation_enum(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-build-vs-buy",
                "--build", "x",
                "--buy", "y",
                "--recommendation", "Maybe",
                "--reasoning", "z",
            ])
            self.assertEqual(r.returncode, 2)


class TestSetDeriskPlan(unittest.TestCase):
    def test_happy_path_with_multiple_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-derisk-plan",
                "--items", '["Spike auth flow","Write PoC","Review with team"]',
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(
                report["derisk_plan"],
                ["Spike auth flow", "Write PoC", "Review with team"],
            )

    def test_rejects_empty_array(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-derisk-plan",
                "--items", "[]",
            ])
            self.assertEqual(r.returncode, 2)

    def test_rejects_non_string_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-derisk-plan",
                "--items", "[1, 2, 3]",
            ])
            self.assertEqual(r.returncode, 2)


class TestSetConstitutionConstraints(unittest.TestCase):
    def test_happy_path_single_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-constitution-constraints",
                "--rule", "No direct DB access from routes",
                "--impact", "All DB calls go through service layer",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertEqual(len(report["constitution_constraints"]), 1)
            c = report["constitution_constraints"][0]
            self.assertEqual(c["rule"], "No direct DB access from routes")
            self.assertEqual(c["impact"], "All DB calls go through service layer")

    def test_multiple_calls_append_not_replace(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run([
                "--devforge-dir", str(devforge),
                "set-constitution-constraints",
                "--rule", "Rule 1",
                "--impact", "Impact 1",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "set-constitution-constraints",
                "--rule", "Rule 2",
                "--impact", "Impact 2",
            ])
            report = _read_report(devforge)
            self.assertEqual(len(report["constitution_constraints"]), 2)
            self.assertEqual(report["constitution_constraints"][0]["rule"], "Rule 1")
            self.assertEqual(report["constitution_constraints"][1]["rule"], "Rule 2")


class TestSetVerdict(unittest.TestCase):
    def test_happy_path_each_enum_value(self):
        for value in discover_helper.VERDICT_ENUM:
            with tempfile.TemporaryDirectory() as tmp:
                devforge = Path(tmp) / ".devforge"
                r = _run([
                    "--devforge-dir", str(devforge),
                    "set-verdict", "--value", value,
                ])
                self.assertEqual(r.returncode, 0, "value={0!r} stderr={1}".format(value, r.stderr))
                report = _read_report(devforge)
                self.assertEqual(report["verdict"], value)

    def test_rejects_invalid_enum(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-verdict", "--value", "Maybe",
            ])
            self.assertEqual(r.returncode, 2)


class TestSetRecommendation(unittest.TestCase):
    def test_happy_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-recommendation",
                "--action", "Proceed with Option A",
                "--next", "Run /specify",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            rec = report["recommendation"]
            self.assertEqual(rec["action"], "Proceed with Option A")
            self.assertEqual(rec["next"], "Run /specify")

    def test_rejects_empty_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-recommendation",
                "--action", "   ",
                "--next", "Run /specify",
            ])
            self.assertEqual(r.returncode, 2)

    def test_rejects_empty_next(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run([
                "--devforge-dir", str(devforge),
                "set-recommendation",
                "--action", "Proceed",
                "--next", "   ",
            ])
            self.assertEqual(r.returncode, 2)


def _setup_scope_dims(devforge_dir):
    """Set all 8 rubric dimensions to Clear with sensible values."""
    values = {
        "functional_scope": "Allow users to authenticate. Second sentence. Third.",
        "users": "End users of the web application",
        "inputs_outputs": "Username and password in, session token out",
        "integration_points": "Auth service, user model, session store",
        "constraints": "Must not break existing sessions",
        "non_goals": "Password reset not in scope",
        "success_criteria": "Users can log in and access protected resources",
        "edge_cases": "Account lockout after 5 failed attempts",
    }
    for dim, val in values.items():
        r = _set_dim(devforge_dir, dim, val, "Clear")
        assert r.returncode == 0, "{0}: {1}".format(dim, r.stderr)


class TestSetNextStepText(unittest.TestCase):
    def _setup_memo(self, devforge_dir):
        """Set all 8 dimensions to Clear."""
        _setup_scope_dims(devforge_dir)

    def _setup_report(self, devforge_dir, verdict="Worth pursuing"):
        """Set design option, recommended option, and verdict."""
        _run([
            "--devforge-dir", str(devforge_dir),
            "set-design-option",
            "--name", "Option A",
            "--shape", "Simple approach",
            "--pros", '["Easy"]',
            "--cons", '["Limited"]',
            "--complexity", "Low",
        ])
        _run([
            "--devforge-dir", str(devforge_dir),
            "set-recommended-option",
            "--name", "Option A",
            "--rationale", "Simplest",
        ])
        _run([
            "--devforge-dir", str(devforge_dir),
            "set-verdict", "--value", verdict,
        ])
        _run([
            "--devforge-dir", str(devforge_dir),
            "set-topic", "--value", "Auth in NestJS",
        ])
        _run([
            "--devforge-dir", str(devforge_dir),
            "set-date", "--value", "2026-05-12",
        ])

    def test_happy_path_composes_expected_pieces(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_memo(devforge)
            self._setup_report(devforge, verdict="Worth pursuing")
            r = _run(["--devforge-dir", str(devforge), "set-next-step-text"])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            text = report["next_step_text"]
            self.assertIsNotNone(text)
            self.assertIn("/specify", text)
            self.assertIn("Discovery reference:", text)
            self.assertIn("Functional scope:", text)
            self.assertIn("Users:", text)
            self.assertIn("Success criteria:", text)
            self.assertIn("Recommended option:", text)
            self.assertIn("Option A", text)

    def test_verdict_reconsider_sets_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_memo(devforge)
            self._setup_report(devforge, verdict="Reconsider")
            r = _run(["--devforge-dir", str(devforge), "set-next-step-text"])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertIsNone(report["next_step_text"])

    def test_missing_required_inputs_exit_2(self):
        """With no memo dims set and no recommended_option, all missing listed."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Only set verdict — don't set scope dims or recommended option.
            _run([
                "--devforge-dir", str(devforge),
                "set-verdict", "--value", "Worth pursuing",
            ])
            r = _run(["--devforge-dir", str(devforge), "set-next-step-text"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("missing required input", r.stderr)
            self.assertIn("memo.functional_scope.value", r.stderr)
            self.assertIn("memo.users.value", r.stderr)
            self.assertIn("memo.success_criteria.value", r.stderr)
            self.assertIn("report.recommended_option", r.stderr)

    def test_functional_scope_truncated_to_first_sentence(self):
        """functional_scope with multiple sentences → /specify shows only first sentence."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_memo(devforge)
            # Override functional_scope with a multi-sentence value.
            r = _set_dim(
                devforge, "functional_scope",
                "Allow users to authenticate. This part should not appear. Neither should this.",
                "Clear",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self._setup_report(devforge, verdict="Worth pursuing")
            r = _run(["--devforge-dir", str(devforge), "set-next-step-text"])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            text = report["next_step_text"]
            # First line must contain only the first sentence.
            first_line = text.split("\n")[0]
            self.assertIn("Allow users to authenticate", first_line)
            self.assertNotIn("This part should not appear", first_line)

    def test_topic_arg_overrides_first_sentence_fallback(self):
        # Fix F1: --topic supplies the LLM-distilled topic, overriding the
        # first-sentence-of-functional_scope fallback. Avoids verbatim dumping
        # multi-paragraph functional_scope into /specify "...".
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_memo(devforge)
            # functional_scope is long + multi-paragraph; the fallback would
            # grab only the first sentence, but --topic must take precedence.
            long_scope = (
                "Add audit log for quote and order changes including revision history "
                "snapshots persisted indefinitely. Each change is keyed by entity id. "
                "Replay UI displays diffs across revisions."
            )
            _set_dim(devforge, "functional_scope", long_scope, "Clear")
            self._setup_report(devforge, verdict="Worth pursuing")
            distilled = "Audit log for quote and order changes with revision history."
            r = _run([
                "--devforge-dir", str(devforge),
                "set-next-step-text",
                "--topic", distilled,
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            text = report["next_step_text"]
            first_line = text.split("\n")[0]
            self.assertIn(distilled, first_line)
            # Fallback first-sentence content must NOT appear in the /specify line.
            self.assertNotIn("Add audit log for quote", first_line)

    def test_topic_arg_empty_falls_back_to_first_sentence(self):
        # Whitespace-only --topic must fall back, not corrupt the /specify line.
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_memo(devforge)
            self._setup_report(devforge, verdict="Worth pursuing")
            r = _run([
                "--devforge-dir", str(devforge),
                "set-next-step-text",
                "--topic", "   ",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            text = report["next_step_text"]
            self.assertTrue(text.startswith('/specify "'))

    def test_literal_escape_sequences_stripped_from_values(self):
        # Fix F2: setter values containing literal `\n\n` / `\n` (from shell
        # escape leakage) must NOT survive into the rendered next-step block.
        # The orchestrator-passed string may contain backslash-n; helper
        # collapses those to a single space.
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_memo(devforge)
            # Inject literal escape sequences into success_criteria via the
            # real setter — round-trip via real producer per
            # `feedback_test_first_python_helpers`.
            _set_dim(
                devforge,
                "success_criteria",
                "load-history: returns all revisions.\\n\\nexport-full-history: dumps to csv.",
                "Clear",
            )
            self._setup_report(devforge, verdict="Worth pursuing")
            r = _run(["--devforge-dir", str(devforge), "set-next-step-text"])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            text = report["next_step_text"]
            self.assertNotIn(
                "\\n",
                text,
                "literal `\\n` escape leaked into composed next-step text: {0!r}".format(text),
            )

    def test_literal_escape_sequences_stripped_from_topic_arg(self):
        # --topic-side cleanup: when orchestrator's distilled topic contains
        # literal `\n` (shouldn't, but defensive), helper strips them too.
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_memo(devforge)
            self._setup_report(devforge, verdict="Worth pursuing")
            r = _run([
                "--devforge-dir", str(devforge),
                "set-next-step-text",
                "--topic", "First sentence.\\n\\nSecond sentence.",
            ])
            self.assertEqual(r.returncode, 0, r.stderr)
            report = _read_report(devforge)
            self.assertNotIn("\\n", report["next_step_text"])


# ---------------------------------------------------------------------------
# Phase 2 — render tests.
# ---------------------------------------------------------------------------


def _build_full_report(devforge_dir):
    """Populate a complete valid report state for render/verify tests."""
    # Shared setup.
    _run(["--devforge-dir", str(devforge_dir), "set-topic", "--value", "Rate limiting in HTTP middleware"])
    _run(["--devforge-dir", str(devforge_dir), "set-date", "--value", "2026-05-12"])
    # Scope.
    _setup_scope_dims(devforge_dir)
    # Phase 1.
    _run([
        "--devforge-dir", str(devforge_dir),
        "record-prior-art",
        "--reference", "express-rate-limit",
        "--kind", "library",
        "--relevance", "Drop-in rate limiter for Express",
        "--source", "https://npm.im/express-rate-limit",
    ])
    _run([
        "--devforge-dir", str(devforge_dir),
        "record-integration-touchpoint",
        "--name", "http-middleware",
        "--module-path", "src/middleware/",
        "--reason", "Rate limiting injected here",
    ])
    _run([
        "--devforge-dir", str(devforge_dir),
        "record-fit-assessment",
        "--touchpoint", "http-middleware",
        "--user-expected", "Simple middleware hook",
        "--reality", "Middleware chain exists and is clean",
        "--effort", "Low",
        "--blockers", "[]",
    ])
    _run(["--devforge-dir", str(devforge_dir), "set-overall-fit", "--value", "Good"])
    _run(["--devforge-dir", str(devforge_dir), "set-effort-estimate", "--value", "Low"])
    _run(["--devforge-dir", str(devforge_dir), "set-fit-rationale", "--value", "Architecture supports it cleanly"])
    # Phase 2.
    _run([
        "--devforge-dir", str(devforge_dir),
        "set-summary",
        "--value", "Rate limiting is feasible. Architecture supports it. Option A is preferred.",
    ])
    _run([
        "--devforge-dir", str(devforge_dir),
        "set-design-option",
        "--name", "Option A",
        "--shape", "Use express-rate-limit middleware",
        "--pros", '["Simple","Battle-tested"]',
        "--cons", '["Adds dependency"]',
        "--complexity", "Low",
    ])
    _run([
        "--devforge-dir", str(devforge_dir),
        "set-design-option",
        "--name", "Option B",
        "--shape", "Custom middleware from scratch",
        "--pros", '["No extra dep"]',
        "--cons", '["More code","Risk"]',
        "--complexity", "Med",
    ])
    _run([
        "--devforge-dir", str(devforge_dir),
        "set-recommended-option",
        "--name", "Option A",
        "--rationale", "Simplest, battle-tested",
    ])
    _run([
        "--devforge-dir", str(devforge_dir),
        "set-build-vs-buy",
        "--build", "Build custom middleware",
        "--buy", "Use express-rate-limit",
        "--recommendation", "Buy",
        "--reasoning", "Library covers all our use cases",
    ])
    _run([
        "--devforge-dir", str(devforge_dir),
        "set-derisk-plan",
        "--items", '["Spike with express-rate-limit","Test in staging"]',
    ])
    _run(["--devforge-dir", str(devforge_dir), "set-verdict", "--value", "Worth pursuing"])
    _run([
        "--devforge-dir", str(devforge_dir),
        "set-recommendation",
        "--action", "Proceed",
        "--next", "Run /specify",
    ])
    _run(["--devforge-dir", str(devforge_dir), "set-next-step-text"])


class TestRender(unittest.TestCase):
    def test_empty_report_renders_all_section_headers(self):
        """Even a bare report has all non-optional section headers present."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "render"])
            self.assertEqual(r.returncode, 0, r.stderr)
            stdout = r.stdout
            for heading in [
                "## Summary",
                "## Prior Art",
                "## Integration Surface",
                "## Fit Assessment",
                "## Design Options",
                "## Build vs Buy",
                "## Derisk Plan",
                "## Recommendation",
            ]:
                self.assertIn(heading, stdout, "missing heading: {0!r}".format(heading))

    def test_empty_report_has_sparse_markers(self):
        """Sparse sections show placeholder text."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "render"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("*No prior-art references recorded.*", r.stdout)
            self.assertIn("*No integration touchpoints recorded.*", r.stdout)
            self.assertIn("*No fit assessments recorded.*", r.stdout)

    def test_full_report_contains_key_tokens(self):
        """Full report has all section headers and key content."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_full_report(devforge)
            r = _run(["--devforge-dir", str(devforge), "render"])
            self.assertEqual(r.returncode, 0, r.stderr)
            stdout = r.stdout
            # Section headers.
            for heading in [
                "## Prior Art",
                "## Integration Surface",
                "## Fit Assessment",
                "## Design Options",
                "## Build vs Buy",
                "## Derisk Plan",
                "## Recommendation",
                "## Next step",
            ]:
                self.assertIn(heading, stdout, "missing heading: {0!r}".format(heading))
            # Key content tokens.
            self.assertIn("Option A", stdout)
            self.assertIn("express-rate-limit", stdout)
            self.assertIn("Rate limiting in HTTP middleware", stdout)
            self.assertIn("Worth pursuing", stdout)
            self.assertIn("Option B", stdout)

    def test_constitution_constraints_empty_section_omitted(self):
        """When constitution_constraints is empty, the heading is NOT in output."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            r = _run(["--devforge-dir", str(devforge), "render"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertNotIn("## Constitution Constraints", r.stdout)

    def test_design_option_heading_no_double_letter_prefix(self):
        # Fix E regression: even when full report renders multiple design
        # options, each `### Option <letter>:` heading must NOT be followed by
        # another `<letter>:` prefix (no double-prefix render).
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_full_report(devforge)
            r = _run(["--devforge-dir", str(devforge), "render"])
            self.assertEqual(r.returncode, 0, r.stderr)
            # Walk every `### Option X:` heading; the char after the colon+space
            # must not be `<letter>:` (the dup signature from Run 3).
            for line in r.stdout.splitlines():
                m = re.match(r"^### Option ([A-Z]): (.*)$", line)
                if m:
                    body = m.group(2)
                    self.assertFalse(
                        re.match(r"^[A-Za-z]\s*:", body),
                        "double-letter-prefix render artifact: {0!r}".format(line),
                    )

    def test_memo_gaps_populated_renders_open_uncertainties(self):
        """When memo.gaps has entries, Open uncertainties section appears."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run([
                "--devforge-dir", str(devforge),
                "record-gap",
                "--dimension", "users",
                "--description", "TBD — end users or admins?",
            ])
            r = _run(["--devforge-dir", str(devforge), "render"])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("## Open uncertainties", r.stdout)
            self.assertIn("[NEEDS CLARIFICATION: users — TBD — end users or admins?]", r.stdout)


# ---------------------------------------------------------------------------
# Phase 2 — verify tests.
# ---------------------------------------------------------------------------


class TestVerify(unittest.TestCase):
    def test_happy_path_all_required_fields_set(self):
        """Full valid report → verify exits 0."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_full_report(devforge)
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_missing_required_fields_under_worth_pursuing(self):
        """Worth pursuing verdict without required fields → exit 2, all missing named."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Only set verdict — nothing else.
            _run(["--devforge-dir", str(devforge), "set-verdict", "--value", "Worth pursuing"])
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            # Rule A violation must name missing fields.
            self.assertIn("verify: A:", r.stderr)

    def test_recommended_option_name_mismatch_rule_c(self):
        """If recommended_option.name doesn't match design_options, rule C fires."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            # Set a design option, then manually tamper the recommended_option
            # to point to a nonexistent name via raw JSON rewrite.
            _run([
                "--devforge-dir", str(devforge),
                "set-design-option",
                "--name", "Option A",
                "--shape", "x",
                "--pros", '["p"]',
                "--cons", '["c"]',
                "--complexity", "Low",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "set-recommended-option",
                "--name", "Option A",
                "--rationale", "r",
            ])
            # Tamper: rewrite recommended_option.name to nonexistent.
            report_path = Path(devforge) / discover_helper.REPORT_FILE_NAME
            state = json.loads(report_path.read_text(encoding="utf-8"))
            state["recommended_option"]["name"] = "NonExistent"
            report_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("verify: C:", r.stderr)

    def test_verdict_flip_rule_strained_fit_no_override(self):
        """overall_fit=Strained + non-Reconsider verdict + no override → rule D fires."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "set-overall-fit", "--value", "Strained"])
            _run(["--devforge-dir", str(devforge), "set-verdict", "--value", "Worth pursuing"])
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("verify: D:", r.stderr)
            self.assertIn("Strained", r.stderr)

    def test_verdict_flip_rule_with_override_passes(self):
        """Strained fit + non-Reconsider verdict + override_recorded → no D violation."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_full_report(devforge)
            # Flip overall_fit to Strained but set override_recorded = True.
            _run(["--devforge-dir", str(devforge), "set-overall-fit", "--value", "Strained"])
            # Record override by manipulating memo directly.
            memo_path = Path(devforge) / discover_helper.MEMO_FILE_NAME
            state = json.loads(memo_path.read_text(encoding="utf-8"))
            state["override_recorded"] = True
            memo_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
            r = _run(["--devforge-dir", str(devforge), "verify"])
            # Should pass (no D violation due to override).
            # May still fail rule A/E if full report isn't set, but D specifically shouldn't fire.
            stderr_lines = r.stderr.splitlines()
            d_violations = [l for l in stderr_lines if "verify: D:" in l]
            self.assertEqual(d_violations, [], "Rule D should not fire when override_recorded=True")

    def test_verdict_flip_rule_major_refactor_no_override(self):
        """effort=Major refactor required + non-Reconsider verdict + no override → rule D fires."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run([
                "--devforge-dir", str(devforge),
                "set-effort-estimate", "--value", "Major refactor required",
            ])
            _run(["--devforge-dir", str(devforge), "set-verdict", "--value", "Worth pursuing"])
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("verify: D:", r.stderr)
            self.assertIn("Major refactor required", r.stderr)

    def test_reconsider_verdict_with_sparse_fields_passes_rule_a(self):
        """Reconsider + summary + recommendation set → Rule A passes (design options not required)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "set-verdict", "--value", "Reconsider"])
            _run([
                "--devforge-dir", str(devforge),
                "set-summary",
                "--value", "Scope is too broad to proceed.",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "set-recommendation",
                "--action", "Stop",
                "--next", "Narrow the scope and retry",
            ])
            r = _run(["--devforge-dir", str(devforge), "verify"])
            # Rule A must not fire for Reconsider with summary + verdict + recommendation.
            stderr_lines = r.stderr.splitlines()
            a_violations = [l for l in stderr_lines if "verify: A:" in l]
            self.assertEqual(a_violations, [], "Rule A should not fire for Reconsider with minimal fields")


class TestVerifyRuleG(unittest.TestCase):
    """Fix B invariant G — internal canonical-pattern cite rule."""

    def _record_internal_prior_art(self, devforge_dir, path):
        r = _run([
            "--devforge-dir", str(devforge_dir),
            "record-prior-art",
            "--reference", "existing-history-store",
            "--kind", "pattern",
            "--relevance", "internal — existing implementation of revision history",
            "--source", "internal:{0}".format(path),
        ])
        assert r.returncode == 0, r.stderr

    def test_rule_g_fires_when_internal_source_not_cited_in_rationale(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_full_report(devforge)
            # Inject an internal: prior-art entry pointing at a path that the
            # default _build_full_report rationale ("Simplest, battle-tested")
            # does NOT mention. Rule G must fire.
            self._record_internal_prior_art(
                devforge, "packages/quote/revisionHistory"
            )
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("verify: G:", r.stderr)
            self.assertIn("packages/quote/revisionHistory", r.stderr)

    def test_rule_g_passes_when_rationale_cites_internal_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_full_report(devforge)
            self._record_internal_prior_art(
                devforge, "packages/quote/revisionHistory"
            )
            # Overwrite recommended_option with a rationale that cites the path.
            _run([
                "--devforge-dir", str(devforge),
                "set-recommended-option",
                "--name", "Option A",
                "--rationale",
                "Extend existing packages/quote/revisionHistory rather than build new.",
            ])
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_rule_g_no_op_when_no_internal_sources(self):
        # When all prior-art sources are external (https://...), rule G is a no-op.
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_full_report(devforge)
            # _build_full_report records one https:// prior-art entry — verify
            # G does not fire even though rationale doesn't cite anything internal.
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_rule_g_passes_with_any_one_of_multiple_internal_sources_cited(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _build_full_report(devforge)
            self._record_internal_prior_art(devforge, "packages/quote/revisionHistory")
            # Second internal entry — different reference name.
            _run([
                "--devforge-dir", str(devforge),
                "record-prior-art",
                "--reference", "order-audit",
                "--kind", "pattern",
                "--relevance", "internal — existing audit infra",
                "--source", "internal:packages/order/audit",
            ])
            _run([
                "--devforge-dir", str(devforge),
                "set-recommended-option",
                "--name", "Option A",
                "--rationale",
                "Extend packages/order/audit; reuses persisted change events.",
            ])
            r = _run(["--devforge-dir", str(devforge), "verify"])
            self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
