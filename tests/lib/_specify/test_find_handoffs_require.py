"""Tests for find-handoffs --require gate (Step 6 of 18-SCOPE-FIDELITY plan).

Covers:
- zero handoffs + --require -> exit 2, BLOCKED message mentioning /research and /discover
- research handoff present + --require -> exit 0 (gate passes)
- discover handoff present + --require -> exit 0 (gate passes)
- zero handoffs WITHOUT --require -> exit 0 (regression: existing contract unchanged)
- non-zero handoffs WITHOUT --require -> exit 0, output unchanged (regression)

Uses real producer round-trips:
- research handoffs built via research_helper finalize-handoff
- discover handoffs built via discover_helper finalize-handoff
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
# Real fixture factories (round-trip via producers).
# ---------------------------------------------------------------------------


def _build_research_handoff(devforge: Path, handoff_out: Path) -> None:
    """Build a valid research handoff.json via real research_helper setters."""
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
        "--emit-handoff-json", str(handoff_out),
    ])
    if r.returncode != 0:
        raise RuntimeError(
            "research finalize-handoff failed:\n"
            "stdout: {0}\nstderr: {1}".format(r.stdout, r.stderr)
        )


def _build_discover_handoff(devforge: Path, handoff_out: Path) -> None:
    """Build a valid discover handoff.json via real discover_helper setters."""
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
        "--emit-handoff-json", str(handoff_out),
    ])
    if r.returncode != 0:
        raise RuntimeError(
            "discover finalize-handoff failed:\n"
            "stdout: {0}\nstderr: {1}".format(r.stdout, r.stderr)
        )


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


class TestFindHandoffsRequireGate(unittest.TestCase):
    """Gate behaviour of find-handoffs --require (Step 6 precondition gate)."""

    def _devforge(self, tmp: str) -> Path:
        d = Path(tmp) / ".devforge"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _run_find(self, devforge: Path, since: str, require: bool = False):
        argv = [
            "--devforge-dir", str(devforge),
            "find-handoffs",
            "--since", since,
        ]
        if require:
            argv.append("--require")
        return _run_specify(argv)

    # ------------------------------------------------------------------
    # Core gate behaviour.
    # ------------------------------------------------------------------

    def test_zero_handoffs_require_exits_nonzero(self):
        """Zero handoffs + --require → exit 2."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, "7 days", require=True)
            self.assertEqual(r.returncode, 2, "Expected exit 2, got {0}; stderr={1}".format(
                r.returncode, r.stderr
            ))

    def test_zero_handoffs_require_blocked_message_mentions_blocked(self):
        """Zero handoffs + --require → stderr contains BLOCKED."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, "7 days", require=True)
            self.assertIn("BLOCKED", r.stderr)

    def test_zero_handoffs_require_blocked_message_mentions_research(self):
        """Zero handoffs + --require → stderr instructs to run /research."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, "7 days", require=True)
            self.assertIn("/research", r.stderr)

    def test_zero_handoffs_require_blocked_message_mentions_discover(self):
        """Zero handoffs + --require → stderr instructs to run /discover."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, "7 days", require=True)
            self.assertIn("/discover", r.stderr)

    def test_zero_handoffs_require_stdout_empty(self):
        """Zero handoffs + --require → stdout is empty (no confusing output)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, "7 days", require=True)
            self.assertEqual(r.stdout.strip(), "")

    # ------------------------------------------------------------------
    # Research handoff satisfies the gate.
    # ------------------------------------------------------------------

    def test_research_handoff_present_require_exits_zero(self):
        """Research handoff within window + --require → exit 0 (gate passes)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_r = tmp_path / "df_r"
            df_r.mkdir()
            research_dir = tmp_path / "research" / "2026-05-19-auth-token-refresh"
            research_dir.mkdir(parents=True)
            handoff_out = research_dir / "handoff.json"
            _build_research_handoff(df_r, handoff_out)

            # Set mtime to 1 hour ago (within "7 days").
            now = time.time()
            os.utime(str(handoff_out), (now - 3600, now - 3600))

            r = self._run_find(devforge, "7 days", require=True)
            self.assertEqual(r.returncode, 0, "Expected exit 0; stderr={0}".format(r.stderr))

    def test_research_handoff_present_require_emits_output_line(self):
        """Research handoff within window + --require → output line on stdout."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_r = tmp_path / "df_r"
            df_r.mkdir()
            research_dir = tmp_path / "research" / "2026-05-19-auth-token-refresh"
            research_dir.mkdir(parents=True)
            handoff_out = research_dir / "handoff.json"
            _build_research_handoff(df_r, handoff_out)

            now = time.time()
            os.utime(str(handoff_out), (now - 3600, now - 3600))

            r = self._run_find(devforge, "7 days", require=True)
            self.assertEqual(r.returncode, 0)
            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 1, "Expected 1 output line; got: " + r.stdout)
            self.assertIn("kind=research", lines[0])

    # ------------------------------------------------------------------
    # Discover handoff satisfies the gate.
    # ------------------------------------------------------------------

    def test_discover_handoff_present_require_exits_zero(self):
        """Discover handoff within window + --require → exit 0 (gate passes)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_d = tmp_path / "df_d"
            df_d.mkdir()
            discover_dir = tmp_path / "discover"
            discover_dir.mkdir()
            handoff_out = discover_dir / "2026-05-20-audit-log-persistence.handoff.json"
            _build_discover_handoff(df_d, handoff_out)

            now = time.time()
            os.utime(str(handoff_out), (now - 3600, now - 3600))

            r = self._run_find(devforge, "7 days", require=True)
            self.assertEqual(r.returncode, 0, "Expected exit 0; stderr={0}".format(r.stderr))

    def test_discover_handoff_present_require_emits_output_line(self):
        """Discover handoff within window + --require → output line on stdout."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_d = tmp_path / "df_d"
            df_d.mkdir()
            discover_dir = tmp_path / "discover"
            discover_dir.mkdir()
            handoff_out = discover_dir / "2026-05-20-audit-log-persistence.handoff.json"
            _build_discover_handoff(df_d, handoff_out)

            now = time.time()
            os.utime(str(handoff_out), (now - 3600, now - 3600))

            r = self._run_find(devforge, "7 days", require=True)
            self.assertEqual(r.returncode, 0)
            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 1, "Expected 1 output line; got: " + r.stdout)
            self.assertIn("kind=discover", lines[0])

    # ------------------------------------------------------------------
    # Regression: existing contract unchanged (no --require flag).
    # ------------------------------------------------------------------

    def test_zero_handoffs_no_require_exits_zero(self):
        """Zero handoffs WITHOUT --require → exit 0 (original contract preserved)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, "7 days", require=False)
            self.assertEqual(r.returncode, 0, "Expected exit 0; stderr={0}".format(r.stderr))

    def test_zero_handoffs_no_require_stdout_empty(self):
        """Zero handoffs WITHOUT --require → stdout empty (original contract preserved)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = self._devforge(tmp)
            r = self._run_find(devforge, "7 days", require=False)
            self.assertEqual(r.stdout.strip(), "")

    def test_nonzero_handoffs_no_require_exits_zero(self):
        """Non-zero handoffs WITHOUT --require → exit 0, output unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_r = tmp_path / "df_r"
            df_r.mkdir()
            research_dir = tmp_path / "research" / "2026-05-19-auth-token-refresh"
            research_dir.mkdir(parents=True)
            handoff_out = research_dir / "handoff.json"
            _build_research_handoff(df_r, handoff_out)

            now = time.time()
            os.utime(str(handoff_out), (now - 3600, now - 3600))

            r = self._run_find(devforge, "7 days", require=False)
            self.assertEqual(r.returncode, 0, "Expected exit 0; stderr={0}".format(r.stderr))
            lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            self.assertEqual(len(lines), 1, "Expected 1 output line; got: " + r.stdout)

    def test_out_of_window_handoff_require_exits_nonzero(self):
        """Handoff older than --since window + --require → exit 2 (not in window = zero hits)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = self._devforge(tmp)

            df_r = tmp_path / "df_r"
            df_r.mkdir()
            research_dir = tmp_path / "research" / "2026-04-01-old-feature"
            research_dir.mkdir(parents=True)
            handoff_out = research_dir / "handoff.json"
            _build_research_handoff(df_r, handoff_out)

            # Set mtime to 10 days ago (outside "7 days" window).
            now = time.time()
            os.utime(str(handoff_out), (now - 10 * 86400, now - 10 * 86400))

            r = self._run_find(devforge, "7 days", require=True)
            self.assertEqual(r.returncode, 2, "Expected exit 2; stderr={0}".format(r.stderr))
            self.assertIn("BLOCKED", r.stderr)


if __name__ == "__main__":
    unittest.main()
