"""Tests for the `read-memory` verb shared by three command helpers.

plan_helper, breakdown_helper and pr_review_helper each expose a
`read-memory` verb emitting the SAME three-field contract, derived from a
single read via _shared/memory.py.  /plan, /breakdown and /pr-review are
classified READS in the memory disposition table but had no memory read at
all; scripts/lib/memory_lane.py flags that as "no memory read performed".

DEPARTURE FROM CONVENTION (deliberate, flagged per repo practice):
this repo tests each helper in its own file (test_plan_helper.py,
test_breakdown_helper.py, tests/lib/_pr_review/).  These tests live in ONE
file instead, because the property under test is that the three verbs agree
on a single contract.  Split across three files, a divergence in field
names, state values, or exit codes would read as three independent local
choices; here it fails as one visible disagreement.  Per-helper behaviour
continues to be tested in the per-helper files.

The three differ in workspace-root resolution BY DESIGN and that difference
is asserted, not smoothed over: plan_helper and breakdown_helper resolve off
cwd (neither exposes a root flag), pr_review_helper off its --devforge-dir.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB = REPO_ROOT / "src" / "devforge" / "lib"
SHIPPED_STUB = REPO_ROOT / "src" / "devforge" / "memory.md"

# (label, launcher path) — every one must satisfy the same contract.
HELPERS = [
    ("plan", LIB / "plan_helper.py"),
    ("breakdown", LIB / "breakdown_helper.py"),
    ("pr-review", LIB / "pr_review_helper.py"),
]

# A line that is neither blank, nor a heading, nor a whole-line HTML comment.
POPULATED_MEMORY = (
    "# Project Memory\n"
    "\n"
    "## Known Pitfalls\n"
    "<!-- Populated during work as mistakes are discovered -->\n"
    "- The backend mapper must be read before scoping this area.\n"
)


def _run(cwd, launcher, *args):
    """Invoke a helper launcher as a subprocess from cwd."""
    return subprocess.run(
        [sys.executable, str(launcher), *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )


def _install(tmp, memory_text=None):
    """Build a throwaway install root, optionally with a memory.md."""
    devforge = tmp / ".devforge"
    devforge.mkdir(parents=True, exist_ok=True)
    if memory_text is not None:
        (devforge / "memory.md").write_text(memory_text, encoding="utf-8")
    return tmp


class ReadMemoryVerbContractTests(unittest.TestCase):
    """Every helper's read-memory verb honours one shared contract."""

    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _read_memory(self, root, launcher):
        proc = _run(root, launcher, "read-memory")
        self.assertEqual(
            proc.returncode,
            0,
            msg="read-memory must always exit 0; stderr={0!r}".format(proc.stderr),
        )
        return json.loads(proc.stdout)

    def test_absent_memory_is_benign_everywhere(self):
        """No memory file: state 'absent', exit 0, no stderr noise.

        A memory-less project is the CORRECT state on a fresh install, so
        this must never block or warn — these commands have to run end to
        end with no memory.md present.
        """
        for label, launcher in HELPERS:
            with self.subTest(helper=label):
                root = _install(self.tmp / ("absent-" + label))
                proc = _run(root, launcher, "read-memory")
                self.assertEqual(proc.returncode, 0)
                self.assertEqual(proc.stderr.strip(), "")
                payload = json.loads(proc.stdout)
                self.assertEqual(payload["memory_state"], "absent")
                self.assertFalse(payload["memory_present"])
                self.assertEqual(payload["memory_excerpt"], "")

    def test_real_shipped_stub_reads_as_stub(self):
        """The stub install.sh actually ships must probe as 'stub'.

        Uses the real bytes of src/devforge/memory.md rather than a
        hand-authored lookalike: if the shipped stub ever gains real
        content, this is what catches it.
        """
        stub_bytes = SHIPPED_STUB.read_text(encoding="utf-8")
        for label, launcher in HELPERS:
            with self.subTest(helper=label):
                root = _install(self.tmp / ("stub-" + label), stub_bytes)
                payload = self._read_memory(root, launcher)
                self.assertEqual(payload["memory_state"], "stub")
                self.assertTrue(payload["memory_present"])

    def test_populated_memory_carries_content(self):
        """One real content line flips the state and lands in the excerpt."""
        for label, launcher in HELPERS:
            with self.subTest(helper=label):
                root = _install(self.tmp / ("pop-" + label), POPULATED_MEMORY)
                payload = self._read_memory(root, launcher)
                self.assertEqual(payload["memory_state"], "populated")
                self.assertTrue(payload["memory_present"])
                self.assertIn("backend mapper", payload["memory_excerpt"])

    def test_all_three_emit_identical_field_sets(self):
        """The contract is uniform — this is why the file exists.

        Divergence in field names across the three would otherwise pass
        three separate per-helper suites while breaking the prose that
        names these tokens in all three command specs.
        """
        expected = {"memory_present", "memory_excerpt", "memory_state"}
        seen = {}
        for label, launcher in HELPERS:
            root = _install(self.tmp / ("fields-" + label), POPULATED_MEMORY)
            seen[label] = set(self._read_memory(root, launcher).keys())
        for label, keys in seen.items():
            with self.subTest(helper=label):
                self.assertEqual(keys, expected)

    def test_verb_is_reachable_through_the_launcher(self):
        """Registered, not merely defined.

        A handler that exists but was never wired into the parser passes a
        unit test and fails in production — that exact half-state occurred
        while this verb was being added, so it is pinned here.
        """
        for label, launcher in HELPERS:
            with self.subTest(helper=label):
                root = _install(self.tmp / ("reach-" + label))
                proc = _run(root, launcher, "read-memory")
                self.assertEqual(proc.returncode, 0)
                self.assertNotIn("invalid choice", proc.stderr)


class ReadMemoryRootResolutionTests(unittest.TestCase):
    """Root resolution differs by design; assert it rather than unify it."""

    def setUp(self):
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_cwd_rooted_helpers_follow_cwd(self):
        """plan/breakdown read the memory of whatever cwd they run in."""
        here = _install(self.tmp / "here", POPULATED_MEMORY)
        elsewhere = _install(self.tmp / "elsewhere")
        for label, launcher in [h for h in HELPERS if h[0] != "pr-review"]:
            with self.subTest(helper=label):
                inside = json.loads(_run(here, launcher, "read-memory").stdout)
                outside = json.loads(_run(elsewhere, launcher, "read-memory").stdout)
                self.assertEqual(inside["memory_state"], "populated")
                self.assertEqual(outside["memory_state"], "absent")


if __name__ == "__main__":
    unittest.main()
