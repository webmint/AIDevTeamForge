"""Tests for find-handoffs (68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 4).

Covers the D5 structural "pending intake" predicate that replaced the old
top-level research/**/handoff.json + discover/*.handoff.json glob pair and
the --since mtime-window filter:

- zero pending handoffs + --require -> exit 2, BLOCKED message naming the
  new specs/*/{research,discover}-handoff.json locations + /research and
  /discover
- research-handoff.json present, spec.md absent + --require -> exit 0
- discover-handoff.json present, spec.md absent + --require -> exit 0
- research-handoff.json present AND spec.md present -> excluded (D5:
  already consumed by /specify) — with --require, exit 2 (zero PENDING
  hits) even though the handoff.json file still exists on disk
- one glob pass surfaces both lanes at once (a research feature dir + a
  sibling discover feature dir in the same specs/ root)
- mtime orders hits (most-recent first) but is no longer applied as a
  --since FILTER — an old handoff still surfaces even under a narrow
  --since window, and --since may be omitted entirely
- zero handoffs WITHOUT --require -> exit 0 (regression: existing contract
  unchanged)
- non-zero handoffs WITHOUT --require -> exit 0, output unchanged
  (regression)
- --since format is still validated when supplied (a malformed value still
  exits 2), even though it is no longer applied as a filter
- corrupt handoff.json is skipped silently

Uses real producer round-trips:
- research handoffs built via research_helper finalize-handoff --feature-dir
- discover handoffs built via discover_helper finalize-handoff --feature-dir
No hand-authored JSON fixtures.

Stdlib only. Python 3.8+. No third-party deps.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup.
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[3]
LIB = ROOT / "src" / "devforge" / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

SPECIFY_HELPER = LIB / "specify_helper.py"
RESEARCH_HELPER = LIB / "research_helper.py"
DISCOVER_HELPER = LIB / "discover_helper.py"


# ---------------------------------------------------------------------------
# Subprocess runners.
# ---------------------------------------------------------------------------


def _run_specify(argv):
    """Run specify_helper.py; capture stdout/stderr/exit."""
    cmd = [sys.executable, str(SPECIFY_HELPER)] + list(argv)
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


def _run_research(argv, cwd=None):
    """Run research_helper.py; capture stdout/stderr/exit."""
    cmd = [sys.executable, str(RESEARCH_HELPER)] + list(argv)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_discover(argv, cwd=None):
    """Run discover_helper.py; capture stdout/stderr/exit."""
    cmd = [sys.executable, str(DISCOVER_HELPER)] + list(argv)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# Real fixture factories (round-trip via producers, --feature-dir anchored —
# the real /research and /discover call shape post plan 68).
# ---------------------------------------------------------------------------


def _build_research_handoff(devforge: Path, feature_dir: Path) -> Path:
    """Build a valid research-handoff.json under feature_dir via real setters.

    Returns feature_dir / "research-handoff.json" (created by
    finalize-handoff itself — feature_dir need not pre-exist).
    """
    df = str(devforge)
    _run_research(["--devforge-dir", df, "reset-memo"])
    _run_research(["--devforge-dir", df, "reset-report"])

    for dim, val in (
        ("symptom", "Auth token not refreshed on expiry"),
        ("affected-area", "services/auth/token_manager.py"),
        ("repro-or-current", "Log in; wait 1 hour; next request fails 401"),
        ("desired", "Token refreshed transparently before expiry"),
        ("scope", "one module"),
        ("unchanged-behavior", "logout flow unchanged"),
    ):
        _run_research([
            "--devforge-dir", df,
            "set-" + dim, "--value", val, "--state", "Clear",
        ])

    _run_research(["--devforge-dir", df, "detect-mode", "--override", "enhancement"])
    _run_research(["--devforge-dir", df, "set-topic", "--value", "auth-token-refresh"])
    _run_research([
        "--devforge-dir", df, "set-verbatim-prompt",
        "--value", "Auth token not refreshed on expiry in services/auth",
    ])
    _run_research(["--devforge-dir", df, "set-date", "--value", "2026-05-19"])

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
        "--devforge-dir", df, "set-verdict", "--value", "Feasible",
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
    _run_research([
        "--devforge-dir", df, "set-probe-feasibility",
        "--data-shape-only", "false",
        "--auth-required", "false",
        "--network-dependent", "false",
        "--timing-dependent", "false",
        "--is-test-code", "false",
    ])

    r = _run_research([
        "--devforge-dir", df,
        "finalize-handoff",
        "--feature-dir", str(feature_dir),
    ])
    if r.returncode != 0:
        raise RuntimeError(
            "research finalize-handoff failed:\n"
            "stdout: {0}\nstderr: {1}".format(r.stdout, r.stderr)
        )
    return feature_dir / "research-handoff.json"


def _build_discover_handoff(devforge: Path, feature_dir: Path) -> Path:
    """Build a valid discover-handoff.json under feature_dir via real setters.

    Returns feature_dir / "discover-handoff.json" (created by
    finalize-handoff itself — feature_dir need not pre-exist).
    """
    df = str(devforge)
    _run_discover(["--devforge-dir", df, "reset-memo"])
    _run_discover(["--devforge-dir", df, "reset-report"])
    _run_discover(["--devforge-dir", df, "set-topic", "--value", "audit-log-persistence"])
    _run_discover([
        "--devforge-dir", df, "set-verbatim-prompt",
        "--value", "Build an audit log persistence system for tracking state changes",
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

    _run_discover(["--devforge-dir", df, "set-summary", "--value", "Audit log persistence"])
    _run_discover(["--devforge-dir", df, "set-overall-fit", "--value", "Good"])
    _run_discover(["--devforge-dir", df, "set-effort-estimate", "--value", "Low"])
    _run_discover(["--devforge-dir", df, "set-fit-rationale", "--value", "Simple ORM ext"])
    _run_discover(["--devforge-dir", df, "set-verdict", "--value", "Worth pursuing"])
    _run_discover([
        "--devforge-dir", df, "record-integration-touchpoint",
        "--name", "ORM layer",
        "--module-path", "src/db/orm.py",
        "--reason", "Audit writes through ORM",
    ])
    _run_discover([
        "--devforge-dir", df, "set-design-option",
        "--name", "PostgreSQL table",
        "--shape", "ORM table",
        "--pros", '["Simple"]',
        "--cons", '["Single DB"]',
        "--complexity", "Low",
    ])
    _run_discover([
        "--devforge-dir", df, "set-recommended-option",
        "--name", "PostgreSQL table",
        "--rationale", "Lowest complexity for current scale",
    ])
    _run_discover([
        "--devforge-dir", df, "set-build-vs-buy",
        "--recommendation", "Build",
        "--build", "Extend ORM with new table",
        "--buy", "Third-party audit library",
        "--reasoning", "ORM already in place; avoid external dependency",
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
    _run_discover([
        "--devforge-dir", df, "set-next-step-text",
        "--feature-dir", "specs/001-audit-log-persistence",
    ])

    r = _run_discover([
        "--devforge-dir", df,
        "finalize-handoff",
        "--feature-dir", str(feature_dir),
    ])
    if r.returncode != 0:
        raise RuntimeError(
            "discover finalize-handoff failed:\n"
            "stdout: {0}\nstderr: {1}".format(r.stdout, r.stderr)
        )
    return feature_dir / "discover-handoff.json"


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


class TestFindHandoffsD5Predicate(unittest.TestCase):
    """D5: pending == (intake handoff present) AND (spec.md absent)."""

    def _devforge(self, tmp: str) -> Path:
        d = Path(tmp) / ".devforge"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _run_find(self, devforge: Path, require: bool = False, since=None):
        argv = ["--devforge-dir", str(devforge), "find-handoffs"]
        if since is not None:
            argv += ["--since", since]
        if require:
            argv.append("--require")
        return _run_specify(argv)

    # ------------------------------------------------------------------
    # Core gate behaviour — zero pending hits.
    # ------------------------------------------------------------------

    def test_zero_handoffs_require_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, require=True)
            self.assertEqual(r.returncode, 2, "stderr={0}".format(r.stderr))

    def test_zero_handoffs_require_blocked_message_mentions_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, require=True)
            self.assertIn("BLOCKED", r.stderr)

    def test_zero_handoffs_require_blocked_message_mentions_research(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, require=True)
            self.assertIn("/research", r.stderr)

    def test_zero_handoffs_require_blocked_message_mentions_discover(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, require=True)
            self.assertIn("/discover", r.stderr)

    def test_zero_handoffs_require_blocked_message_names_new_locations(self):
        """BLOCKED text names the new specs/*/{research,discover}-handoff.json paths."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, require=True)
            self.assertIn("specs/*/research-handoff.json", r.stderr)
            self.assertIn("specs/*/discover-handoff.json", r.stderr)

    def test_zero_handoffs_require_stdout_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, require=True)
            self.assertEqual(r.stdout.strip(), "")

    # ------------------------------------------------------------------
    # Positive: handoff present, spec.md absent -> pending, satisfies gate.
    # ------------------------------------------------------------------

    def test_research_handoff_pending_require_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_r = tmp_path / "df_r"
            df_r.mkdir()
            feature_dir = tmp_path / "specs" / "001-auth-token-refresh"
            _build_research_handoff(df_r, feature_dir)

            r = self._run_find(devforge, require=True)
            self.assertEqual(r.returncode, 0, "stderr={0}".format(r.stderr))
            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 1, "Expected 1 hit, got: " + r.stdout)
            self.assertIn("kind=research", lines[0])

    def test_discover_handoff_pending_require_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_d = tmp_path / "df_d"
            df_d.mkdir()
            feature_dir = tmp_path / "specs" / "001-audit-log-persistence"
            _build_discover_handoff(df_d, feature_dir)

            r = self._run_find(devforge, require=True)
            self.assertEqual(r.returncode, 0, "stderr={0}".format(r.stderr))
            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 1, "Expected 1 hit, got: " + r.stdout)
            self.assertIn("kind=discover", lines[0])

    # ------------------------------------------------------------------
    # Negative: handoff present AND spec.md present -> already consumed,
    # excluded from the pending list (D5).
    # ------------------------------------------------------------------

    def test_research_handoff_with_spec_md_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_r = tmp_path / "df_r"
            df_r.mkdir()
            feature_dir = tmp_path / "specs" / "001-auth-token-refresh"
            handoff_out = _build_research_handoff(df_r, feature_dir)
            self.assertTrue(handoff_out.exists())

            # Simulate a completed /specify run: spec.md now exists beside
            # the handoff.
            (feature_dir / "spec.md").write_text("# spec\n", encoding="utf-8")

            r = self._run_find(devforge, require=False)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(
                r.stdout.strip(), "",
                "feature with spec.md must not surface as pending",
            )

    def test_research_handoff_with_spec_md_require_exits_nonzero(self):
        """The D5 exclusion also drives --require: zero PENDING hits -> exit 2,
        even though the handoff.json file itself still exists on disk."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_r = tmp_path / "df_r"
            df_r.mkdir()
            feature_dir = tmp_path / "specs" / "001-auth-token-refresh"
            _build_research_handoff(df_r, feature_dir)
            (feature_dir / "spec.md").write_text("# spec\n", encoding="utf-8")

            r = self._run_find(devforge, require=True)
            self.assertEqual(r.returncode, 2, "stderr={0}".format(r.stderr))
            self.assertIn("BLOCKED", r.stderr)

    # ------------------------------------------------------------------
    # One glob pass surfaces both lanes.
    # ------------------------------------------------------------------

    def test_one_pass_surfaces_both_lanes(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_r = tmp_path / "df_r"
            df_r.mkdir()
            research_dir = tmp_path / "specs" / "001-auth-token-refresh"
            _build_research_handoff(df_r, research_dir)

            df_d = tmp_path / "df_d"
            df_d.mkdir()
            discover_dir = tmp_path / "specs" / "002-audit-log-persistence"
            _build_discover_handoff(df_d, discover_dir)

            r = self._run_find(devforge, require=False)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 2, "Expected 2 hits, got: " + r.stdout)
            kinds = {("research" if "kind=research" in l else "discover") for l in lines}
            self.assertEqual(kinds, {"research", "discover"})

    def test_both_lanes_in_one_feature_dir_surfaces_both_with_require(self):
        """python-reviewer finding 2: ONE specs/NNN-slug/ dir carrying BOTH
        research-handoff.json AND discover-handoff.json (real producers,
        same parent dir) -> find-handoffs --require surfaces both hits,
        sharing the parent dir, exit 0, exactly 2 lines."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            feature_dir = tmp_path / "specs" / "001-hybrid-feature"

            df_r = tmp_path / "df_r"
            df_r.mkdir()
            _build_research_handoff(df_r, feature_dir)

            df_d = tmp_path / "df_d"
            df_d.mkdir()
            _build_discover_handoff(df_d, feature_dir)

            r = self._run_find(devforge, require=True)
            self.assertEqual(r.returncode, 0, "stderr={0}".format(r.stderr))
            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 2, "Expected 2 hits, got: " + r.stdout)
            kinds = {("research" if "kind=research" in l else "discover") for l in lines}
            self.assertEqual(kinds, {"research", "discover"})
            # Both hits' handoff_path (2nd pipe-delimited field) share the
            # same parent dir.
            parents = {
                Path(l.split(" | ")[1]).parent for l in lines
            }
            self.assertEqual(len(parents), 1, "Both hits must share one parent dir")
            self.assertEqual(parents.pop().name, "001-hybrid-feature")

    # ------------------------------------------------------------------
    # Ordering + --since deprecation (OQ-2): mtime orders, never filters.
    # ------------------------------------------------------------------

    def test_ordering_newest_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_a = tmp_path / "df_a"
            df_a.mkdir()
            older_dir = tmp_path / "specs" / "001-older"
            older_handoff = _build_research_handoff(df_a, older_dir)

            df_b = tmp_path / "df_b"
            df_b.mkdir()
            newer_dir = tmp_path / "specs" / "002-newer"
            newer_handoff = _build_discover_handoff(df_b, newer_dir)

            now = time.time()
            os.utime(str(older_handoff), (now - 8 * 86400, now - 8 * 86400))
            os.utime(str(newer_handoff), (now - 3600, now - 3600))

            r = self._run_find(devforge, require=False)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 2)
            self.assertIn("kind=discover", lines[0], "newest (discover) must sort first")
            self.assertIn("kind=research", lines[1], "oldest (research) must sort last")

    def test_since_window_does_not_filter_old_handoff(self):
        """An 8-day-old handoff still surfaces under a narrow --since window
        (OQ-2: --since is accepted-but-ignored as a filter -- structural
        predicate replaced it)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_a = tmp_path / "df_a"
            df_a.mkdir()
            feature_dir = tmp_path / "specs" / "001-old-feature"
            handoff_out = _build_research_handoff(df_a, feature_dir)

            now = time.time()
            os.utime(str(handoff_out), (now - 8 * 86400, now - 8 * 86400))

            # A window that would have EXCLUDED this under the old semantics.
            r = self._run_find(devforge, require=True, since="1 hour")
            self.assertEqual(r.returncode, 0, "stderr={0}".format(r.stderr))
            self.assertIn("kind=research", r.stdout)

    def test_since_omitted_entirely_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_a = tmp_path / "df_a"
            df_a.mkdir()
            feature_dir = tmp_path / "specs" / "001-auth-token-refresh"
            _build_research_handoff(df_a, feature_dir)

            r = self._run_find(devforge, require=True, since=None)
            self.assertEqual(r.returncode, 0, "stderr={0}".format(r.stderr))
            self.assertIn("kind=research", r.stdout)

    def test_since_malformed_still_rejected(self):
        """--since format is still validated when supplied, even though it
        is never applied as a filter."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, require=False, since="foo")
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("--since", r.stderr)

    # ------------------------------------------------------------------
    # Regression: existing no-require / non-zero-hits contract unchanged.
    # ------------------------------------------------------------------

    def test_zero_handoffs_no_require_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, require=False)
            self.assertEqual(r.returncode, 0, "stderr={0}".format(r.stderr))

    def test_zero_handoffs_no_require_stdout_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, require=False)
            self.assertEqual(r.stdout.strip(), "")

    def test_nonzero_handoffs_no_require_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_r = tmp_path / "df_r"
            df_r.mkdir()
            feature_dir = tmp_path / "specs" / "001-auth-token-refresh"
            _build_research_handoff(df_r, feature_dir)

            r = self._run_find(devforge, require=False)
            self.assertEqual(r.returncode, 0, "stderr={0}".format(r.stderr))
            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 1, "Expected 1 hit, got: " + r.stdout)

    # ------------------------------------------------------------------
    # Corrupt file handling.
    # ------------------------------------------------------------------

    def test_corrupt_handoff_skipped_silently(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_r = tmp_path / "df_r"
            df_r.mkdir()
            valid_dir = tmp_path / "specs" / "001-auth-token-refresh"
            _build_research_handoff(df_r, valid_dir)

            corrupt_dir = tmp_path / "specs" / "002-corrupt"
            corrupt_dir.mkdir(parents=True)
            (corrupt_dir / "research-handoff.json").write_text(
                "{ not json }", encoding="utf-8",
            )

            r = self._run_find(devforge, require=False)
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 1, "Expected 1 hit, got: " + r.stdout)
            self.assertIn("kind=research", lines[0])

    def test_non_dir_entries_under_specs_root_skipped(self):
        """A stray file directly under specs/ (not a feature dir) is skipped."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)
            specs_root = tmp_path / "specs"
            specs_root.mkdir()
            (specs_root / "README.md").write_text("stray\n", encoding="utf-8")

            r = self._run_find(devforge, require=False)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
