"""Tests for _research/_cmds_feature_alloc.py's --ticket wiring.

91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 2 -- allocate-feature-dir
gained an optional --ticket argument, read alongside REQUIRE_TICKET
(_shared.feature_alloc.read_require_ticket) at the CLI verb, and both are
passed through to _shared.feature_alloc.allocate_feature_dir unchanged.

This is the FIRST test file under tests/lib/_research/ for the
allocate-feature-dir verb -- a pre-existing gap the plan-91 build flagged:
prior coverage for that verb lives only in the legacy monolith
tests/lib/test_research_helper.py::TestAllocateFeatureDirCli (slug-only
behaviour, no --ticket). This file covers ONLY the new --ticket surface and
does not duplicate that file's slug-only cases.

Coverage:
  REQUIRE_TICKET off (no project-config.json at all -- the default,
    fail-open state) + no --ticket
      -> allocates exactly as before this wiring landed (zero behaviour
         change for every pre-existing caller).
  REQUIRE_TICKET off + a valid --ticket
      -> allocates and echoes the normalized ticket in the result.
  REQUIRE_TICKET off + a malformed --ticket
      -> still refuses (format is always checked once a ticket is
         supplied, regardless of the config key) -- exit 2, message does
         NOT invoke REQUIRE_TICKET.
  REQUIRE_TICKET on (real producer round trip: init_helper +
    configure_helper set-require-ticket true + render-config write the
    actual project-config.json this verb's read_require_ticket call
    reads) + a valid --ticket -> allocates.
  REQUIRE_TICKET on + no --ticket
      -> exit 2, stderr names BOTH routes out verbatim (supply a ticket /
         turn REQUIRE_TICKET off) -- the substrate's own message, which
         this wrapper must forward unaltered.
  REQUIRE_TICKET on + a malformed --ticket -> exit 2, same message shape.
  The "ticket" key is present in the stdout JSON on every success case
    (asserted inline in each success test below, not as a separate check).

Every allocate-feature-dir call here is a real subprocess invocation of
research_helper.py, parsing the CLI's actual stdout JSON -- never a
hand-authored fixture. The REQUIRE_TICKET=on cases additionally round-trip
through the real config producer chain (init_helper + configure_helper),
mirroring tests/lib/_configure/test_require_ticket.py's
RealProducerRoundTripTests precedent, rather than hand-writing
project-config.json directly.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_RESEARCH_HELPER_PY = _LIB_DIR / "research_helper.py"
_CONFIGURE_HELPER_PY = _LIB_DIR / "configure_helper.py"
_INIT_HELPER_PY = _LIB_DIR / "init_helper.py"


def _run_research(devforge_dir, *args):
    """Invoke research_helper.py <args> as a subprocess."""
    return subprocess.run(
        [sys.executable, str(_RESEARCH_HELPER_PY), "--devforge-dir", str(devforge_dir)]
        + list(args),
        capture_output=True,
        text=True,
    )


def _run_configure(devforge_dir, *args):
    """Invoke configure_helper.py <args> as a subprocess."""
    return subprocess.run(
        [sys.executable, str(_CONFIGURE_HELPER_PY), "--devforge-dir", str(devforge_dir)]
        + list(args),
        capture_output=True,
        text=True,
    )


def _run_init(devforge_dir, *args):
    """Invoke init_helper.py <args> as a subprocess."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_INIT_HELPER_PY)] + list(args),
        env=env,
        capture_output=True,
        text=True,
    )


def _enable_require_ticket(devforge_dir):
    """Real-producer round trip: write the actual project-config.json with
    REQUIRE_TICKET="true" via init_helper + configure_helper -- the same
    file allocate-feature-dir's read_require_ticket call reads. Never a
    hand-authored fixture."""
    _run_init(devforge_dir, "reset")
    _run_init(devforge_dir, "set-workspace-mode", "standalone")
    _run_init(devforge_dir, "set-project-root", ".")
    _run_init(devforge_dir, "set-project-state", "brownfield")
    _run_init(devforge_dir, "set-default-branch", "main")
    _run_configure(devforge_dir, "reset")
    _run_configure(devforge_dir, "set-require-ticket", "true")
    proc = _run_configure(devforge_dir, "render-config")
    assert proc.returncode == 0, proc.stderr


class TestAllocateFeatureDirTicketRequireTicketOff(unittest.TestCase):
    """REQUIRE_TICKET unset -- no project-config.json exists at all, so
    read_require_ticket's documented fail-open default (False) applies."""

    def test_no_ticket_allocates_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            r = _run_research(
                devforge, "allocate-feature-dir", "--slug", "no-ticket-needed",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            payload = json.loads(r.stdout)
            self.assertEqual(payload["dirname"], "001-no-ticket-needed")
            self.assertIn("ticket", payload)
            self.assertIsNone(payload["ticket"])

    def test_valid_ticket_allocates_and_echoes(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            r = _run_research(
                devforge, "allocate-feature-dir",
                "--slug", "optional-ticket-here", "--ticket", "PROJ-123",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            payload = json.loads(r.stdout)
            self.assertEqual(payload["dirname"], "001-optional-ticket-here")
            self.assertIn("ticket", payload)
            self.assertEqual(payload["ticket"], "PROJ-123")

    def test_malformed_ticket_still_refuses(self):
        """Format is always checked once a ticket is supplied, regardless
        of REQUIRE_TICKET -- but the message must not invoke REQUIRE_
        TICKET, since the gate itself is not what refused."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            r = _run_research(
                devforge, "allocate-feature-dir",
                "--slug", "bad-ticket-format", "--ticket", "not-a-ticket",
            )
            self.assertEqual(r.returncode, 2)
            self.assertIn("invalid ticket", r.stderr)
            self.assertNotIn("REQUIRE_TICKET", r.stderr)
            self.assertFalse((Path(tmp) / "specs").exists())


class TestAllocateFeatureDirTicketRequireTicketOn(unittest.TestCase):
    """REQUIRE_TICKET enabled via the real configure_helper producer chain."""

    def test_valid_ticket_allocates(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            _enable_require_ticket(devforge)
            r = _run_research(
                devforge, "allocate-feature-dir",
                "--slug", "ticketed-feature", "--ticket", "ENG-42",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            payload = json.loads(r.stdout)
            self.assertEqual(payload["dirname"], "001-ticketed-feature")
            self.assertIn("ticket", payload)
            self.assertEqual(payload["ticket"], "ENG-42")

    def test_no_ticket_exits_2_naming_both_routes(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            _enable_require_ticket(devforge)
            r = _run_research(
                devforge, "allocate-feature-dir", "--slug", "needs-a-ticket",
            )
            self.assertEqual(r.returncode, 2)
            self.assertIn("REQUIRE_TICKET", r.stderr)
            self.assertIn("supply a ticket", r.stderr)
            self.assertIn("turn REQUIRE_TICKET off", r.stderr)
            self.assertFalse((Path(tmp) / "specs").exists())

    def test_malformed_ticket_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            _enable_require_ticket(devforge)
            r = _run_research(
                devforge, "allocate-feature-dir",
                "--slug", "malformed-ticket-here", "--ticket", "proj-123",
            )
            self.assertEqual(r.returncode, 2)
            self.assertIn("REQUIRE_TICKET", r.stderr)
            self.assertIn("supply a ticket", r.stderr)
            self.assertIn("turn REQUIRE_TICKET off", r.stderr)
            self.assertFalse((Path(tmp) / "specs").exists())


if __name__ == "__main__":
    unittest.main()
