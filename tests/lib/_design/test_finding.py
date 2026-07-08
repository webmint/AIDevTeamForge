"""Tests for src/devforge/lib/_design/_finding.py -- DesignFinding (plan 53
Phase 4/5).

Coverage:
  - a fully-specified DesignFinding constructs cleanly and to_dict() round-
    trips every field
  - invalid kind -> ValueError naming 'kind'
  - invalid severity -> ValueError naming 'severity'
  - empty/blank file, selector, title, explanation, suggested_fix -> ValueError
  - optional fields (property/expected/actual) default to None and are
    accepted when supplied
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _design._finding import DesignFinding, FINDING_KINDS  # noqa: E402
from _shared.findings_schema import SEVERITY_ENUM  # noqa: E402


def _make(**overrides):
    kwargs = dict(
        kind="overflow",
        severity="High",
        file="/dashboard",
        selector="my-region",
        title="Unintended horizontal overflow",
        explanation="scrollWidth > clientWidth",
        suggested_fix="constrain width",
    )
    kwargs.update(overrides)
    return DesignFinding(**kwargs)


class DesignFindingConstructionTests(unittest.TestCase):
    def test_valid_construction(self):
        finding = _make(property="overflow-x", expected="a", actual="b")
        self.assertEqual(finding.kind, "overflow")
        self.assertEqual(finding.severity, "High")
        self.assertEqual(finding.file, "/dashboard")
        self.assertEqual(finding.selector, "my-region")
        self.assertEqual(finding.property, "overflow-x")
        self.assertEqual(finding.expected, "a")
        self.assertEqual(finding.actual, "b")

    def test_optional_fields_default_none(self):
        finding = _make()
        self.assertIsNone(finding.property)
        self.assertIsNone(finding.expected)
        self.assertIsNone(finding.actual)

    def test_to_dict_round_trips_every_field(self):
        finding = _make(property="p", expected="e", actual="a")
        d = finding.to_dict()
        self.assertEqual(
            d,
            {
                "kind": "overflow",
                "severity": "High",
                "file": "/dashboard",
                "selector": "my-region",
                "title": "Unintended horizontal overflow",
                "explanation": "scrollWidth > clientWidth",
                "suggested_fix": "constrain width",
                "property": "p",
                "expected": "e",
                "actual": "a",
            },
        )

    def test_all_finding_kinds_accepted(self):
        for kind in FINDING_KINDS:
            finding = _make(kind=kind)
            self.assertEqual(finding.kind, kind)

    def test_all_severities_accepted(self):
        for severity in SEVERITY_ENUM:
            finding = _make(severity=severity)
            self.assertEqual(finding.severity, severity)

    def test_invalid_kind_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _make(kind="not-a-real-kind")
        self.assertIn("kind", str(ctx.exception))

    def test_invalid_severity_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _make(severity="Catastrophic")
        self.assertIn("severity", str(ctx.exception))

    def test_empty_file_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _make(file="")
        self.assertIn("file", str(ctx.exception))

    def test_blank_file_rejected(self):
        with self.assertRaises(ValueError):
            _make(file="   ")

    def test_empty_selector_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _make(selector="")
        self.assertIn("selector", str(ctx.exception))

    def test_empty_title_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _make(title="")
        self.assertIn("title", str(ctx.exception))

    def test_empty_explanation_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _make(explanation="")
        self.assertIn("explanation", str(ctx.exception))

    def test_empty_suggested_fix_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            _make(suggested_fix="")
        self.assertIn("suggested_fix", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
