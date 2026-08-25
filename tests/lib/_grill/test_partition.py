"""Tests for src/devforge/lib/_grill/_partition.py.

Coverage:
  partition_is_clean — False per blocking bucket individually (confirmed,
                        contested, uncertain), True with only dismissed
                        populated, True for an all-empty partition (the
                        literal byte string from src/commands/grill/main.md's
                        PHASE-3.5 clean-pass shortcut), fail-closed False on
                        a missing bucket key (whole dict and single-key), and
                        a real _shared._verify.apply_verdicts round trip.
"""

import json
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _grill._partition import partition_is_clean  # noqa: E402


def _finding(finding_id="f1"):
    """Minimal ParsedFinding-shaped dict, enough for partition_is_clean's
    purposes (it only ever inspects list emptiness, never finding
    contents).
    """
    return {
        "agent": "devils-advocate",
        "severity": "High",
        "file": "src/auth/login.py",
        "line": 42,
        "pattern": finding_id,
        "confidence": "Certain",
        "evidence": "def login(user):",
        "why": "Some reason.",
        "remediation": "Some fix.",
        "category": "security",
        "tags": [],
    }


class TestPartitionIsCleanBlockingBuckets(unittest.TestCase):
    """Each blocking bucket tested individually, not combined — the clean
    predicate must fail closed on any ONE of them regardless of the other
    two being empty.
    """

    def test_false_when_confirmed_alone_nonempty(self):
        partition = {
            "confirmed": [_finding()],
            "dismissed": [],
            "uncertain": [],
            "contested": [],
        }
        self.assertFalse(partition_is_clean(partition))

    def test_false_when_contested_alone_nonempty(self):
        partition = {
            "confirmed": [],
            "dismissed": [],
            "uncertain": [],
            "contested": [_finding()],
        }
        self.assertFalse(partition_is_clean(partition))

    def test_false_when_uncertain_alone_nonempty(self):
        partition = {
            "confirmed": [],
            "dismissed": [],
            "uncertain": [_finding()],
            "contested": [],
        }
        self.assertFalse(partition_is_clean(partition))


class TestPartitionIsCleanDismissedDoesNotBlock(unittest.TestCase):
    def test_true_when_only_dismissed_nonempty(self):
        """The case distinguishing the ratified rule from 'the report is
        empty': a dismissed finding did not survive refutation, so its
        presence must NOT prevent a clean disposition.
        """
        partition = {
            "confirmed": [],
            "dismissed": [_finding("d1"), _finding("d2")],
            "uncertain": [],
            "contested": [],
        }
        self.assertTrue(partition_is_clean(partition))


class TestPartitionIsCleanAllEmpty(unittest.TestCase):
    def test_true_for_all_empty_partition(self):
        # The literal byte string src/commands/grill/main.md:198 writes to
        # $WORKDIR/partition.json via `printf '%s' '...'` when PHASE 4 is
        # skipped entirely (the adversary produced no grounded attack) —
        # parsed here, not re-derived as a hand-built Python dict, so this
        # test tracks the real producer's exact shape.
        partition = json.loads(
            '{"confirmed": [], "dismissed": [], "uncertain": [], "contested": []}'
        )
        self.assertTrue(partition_is_clean(partition))


class TestPartitionIsCleanFailsClosedOnMissingKeys(unittest.TestCase):
    """A malformed partition (missing bucket keys) must read as NOT clean —
    never True, never a crash. See partition_is_clean()'s fail-closed
    paragraph: the real producer (apply_verdicts) always writes all four
    keys, so tolerating a missing key bought nothing in the happy path and
    only mattered on already-anomalous input, which is exactly where
    fail-closed is wanted.
    """

    def test_false_for_empty_dict(self):
        self.assertFalse(partition_is_clean({}))

    def test_false_when_a_single_required_key_is_absent(self):
        """Even a non-blocking bucket's KEY (dismissed) is required — its
        absence alone must still fail closed, independent of its content
        never affecting the blocking check.
        """
        partition = {
            "confirmed": [],
            # "dismissed" key deliberately omitted.
            "uncertain": [],
            "contested": [],
        }
        self.assertFalse(partition_is_clean(partition))


class TestPartitionIsCleanRealProducer(unittest.TestCase):
    """Round-trip through the real producer: _shared._verify.apply_verdicts,
    the function whose output shape this predicate is meant to consume
    (grill's render-report handler reads the identical shape from
    --partition).
    """

    def test_clean_output_from_apply_verdicts_all_confirmed(self):
        from _shared._verify import apply_verdicts  # noqa: E402

        finding = _finding("f1")
        findings = [finding]
        # apply_verdicts keys a verdict to its finding by (file, line,
        # pattern, agent) — see _shared._verify._verdict_key.
        verdicts = [
            {
                "file": finding["file"],
                "line": finding["line"],
                "pattern": finding["pattern"],
                "agent": finding["agent"],
                "verdict": "confirmed",
            }
        ]
        partition = apply_verdicts(findings, verdicts)
        # A confirmed finding is NOT clean — sanity check the real shape
        # lands in the bucket this module expects.
        self.assertIn("confirmed", partition)
        self.assertFalse(partition_is_clean(partition))

    def test_clean_output_from_apply_verdicts_empty_input(self):
        from _shared._verify import apply_verdicts  # noqa: E402

        partition = apply_verdicts([], [])
        self.assertTrue(partition_is_clean(partition))


if __name__ == "__main__":
    unittest.main()
