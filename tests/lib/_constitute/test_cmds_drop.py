"""Tests for _cmds_drop.cmd_drop_rule / cmd_drop_section (D6(a), plan 104
Phase 3 Unit D).

Moved out of tests/lib/test_constitute_helper.py in a behavior-preserving
restructure (mirrors the _cmds_drop.py source-module split): test bodies
and the real-CLI subprocess approach are unchanged from the original file
-- only the location and the path-computation prologue moved, following
the pattern this package's other test files use (see
test_verify_forcing_function_keys.py) adjusted for the subprocess-based
CLI invocation these classes need.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "constitute_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))


def _run(argv, cwd=None, env=None):
    """Run constitute_helper.py with given argv; capture output."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(argv),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


class TestDropRule(unittest.TestCase):
    def _setup_section_with_rules(self, devforge, texts):
        _run(["--devforge-dir", str(devforge), "add-section",
              "--bucket", "architecture", "--number", "1.1",
              "--title", "Test Section"])
        for text in texts:
            _run(["--devforge-dir", str(devforge), "add-rule",
                  "--section", "1.1", "--tag", "extracted", "--text", text])

    def test_happy_path_section_form_removes_correct_rule(self):
        """drop-rule --section --index removes the 1-based i-th rule only."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section_with_rules(devforge, ["Rule 1", "Rule 2", "Rule 3"])

            result = _run(["--devforge-dir", str(devforge), "drop-rule",
                           "--section", "1.1", "--index", "2"])
            self.assertEqual(result.returncode, 0, result.stderr)

            state = json.loads((devforge / "constitute.json").read_text())
            texts = [r["text"] for r in state["architecture_rules"][0]["rules"]]
            self.assertEqual(texts, ["Rule 1", "Rule 3"])

    def test_happy_path_pattern_bucket_form_removes_correct_rule(self):
        """drop-rule --bucket/--scope --index removes the i-th pattern rule."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            for text in ["Pattern 1", "Pattern 2"]:
                _run(["--devforge-dir", str(devforge), "add-pattern-rule",
                      "--bucket", "always", "--scope", "universal",
                      "--tag", "universal", "--text", text])

            result = _run(["--devforge-dir", str(devforge), "drop-rule",
                           "--bucket", "always", "--scope", "universal",
                           "--index", "1"])
            self.assertEqual(result.returncode, 0, result.stderr)

            state = json.loads((devforge / "constitute.json").read_text())
            texts = [r["text"] for r in state["patterns_and_antipatterns"]["always_universal"]]
            self.assertEqual(texts, ["Pattern 2"])

    def test_both_forms_given_exits_2_state_unchanged(self):
        """--section AND --bucket/--scope together is rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section_with_rules(devforge, ["Rule 1"])
            before = (devforge / "constitute.json").read_bytes()

            result = _run(["--devforge-dir", str(devforge), "drop-rule",
                           "--section", "1.1", "--bucket", "always",
                           "--scope", "universal", "--index", "1"])
            self.assertEqual(result.returncode, 2)

            after = (devforge / "constitute.json").read_bytes()
            self.assertEqual(before, after)

    def test_neither_form_given_exits_2_state_unchanged(self):
        """Neither --section nor --bucket/--scope given is rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section_with_rules(devforge, ["Rule 1"])
            before = (devforge / "constitute.json").read_bytes()

            result = _run(["--devforge-dir", str(devforge), "drop-rule", "--index", "1"])
            self.assertEqual(result.returncode, 2)

            after = (devforge / "constitute.json").read_bytes()
            self.assertEqual(before, after)

    def test_bucket_without_scope_exits_2_state_unchanged(self):
        """--bucket without --scope is rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section_with_rules(devforge, ["Rule 1"])
            before = (devforge / "constitute.json").read_bytes()

            result = _run(["--devforge-dir", str(devforge), "drop-rule",
                           "--bucket", "always", "--index", "1"])
            self.assertEqual(result.returncode, 2)

            after = (devforge / "constitute.json").read_bytes()
            self.assertEqual(before, after)

    def test_scope_without_bucket_exits_2_state_unchanged(self):
        """--scope without --bucket is rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section_with_rules(devforge, ["Rule 1"])
            before = (devforge / "constitute.json").read_bytes()

            result = _run(["--devforge-dir", str(devforge), "drop-rule",
                           "--scope", "universal", "--index", "1"])
            self.assertEqual(result.returncode, 2)

            after = (devforge / "constitute.json").read_bytes()
            self.assertEqual(before, after)

    def test_invalid_bucket_choice_rejected_by_argparse(self):
        """An unknown --bucket value is rejected by argparse (choices=)."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section_with_rules(devforge, ["Rule 1"])
            result = _run(["--devforge-dir", str(devforge), "drop-rule",
                           "--bucket", "sometimes", "--scope", "universal",
                           "--index", "1"])
            self.assertNotEqual(result.returncode, 0)

    def test_index_out_of_range_exits_2_state_unchanged(self):
        """An --index beyond the rule count is rejected; state unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section_with_rules(devforge, ["Rule 1"])
            before = (devforge / "constitute.json").read_bytes()

            result = _run(["--devforge-dir", str(devforge), "drop-rule",
                           "--section", "1.1", "--index", "5"])
            self.assertEqual(result.returncode, 2)

            after = (devforge / "constitute.json").read_bytes()
            self.assertEqual(before, after)

    def test_index_zero_exits_2_state_unchanged(self):
        """--index 0 (not 1-based) is rejected; state unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            self._setup_section_with_rules(devforge, ["Rule 1"])
            before = (devforge / "constitute.json").read_bytes()

            result = _run(["--devforge-dir", str(devforge), "drop-rule",
                           "--section", "1.1", "--index", "0"])
            self.assertEqual(result.returncode, 2)

            after = (devforge / "constitute.json").read_bytes()
            self.assertEqual(before, after)

    def test_section_not_found_exits_2_state_unchanged(self):
        """A nonexistent --section is rejected; state unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset"])
            before = (devforge / "constitute.json").read_bytes()

            result = _run(["--devforge-dir", str(devforge), "drop-rule",
                           "--section", "99.99", "--index", "1"])
            self.assertEqual(result.returncode, 2)
            self.assertIn("99.99", result.stderr)

            after = (devforge / "constitute.json").read_bytes()
            self.assertEqual(before, after)


class TestDropSection(unittest.TestCase):
    def test_happy_path_removes_section(self):
        """drop-section removes the section with the given --number."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "add-section",
                  "--bucket", "architecture", "--number", "1.1",
                  "--title", "First"])
            _run(["--devforge-dir", str(devforge), "add-section",
                  "--bucket", "architecture", "--number", "1.2",
                  "--title", "Second"])

            result = _run(["--devforge-dir", str(devforge), "drop-section",
                           "--number", "1.1"])
            self.assertEqual(result.returncode, 0, result.stderr)

            state = json.loads((devforge / "constitute.json").read_text())
            numbers = [s["number"] for s in state["architecture_rules"]]
            self.assertEqual(numbers, ["1.2"])

    def test_section_not_found_exits_2_state_unchanged(self):
        """A nonexistent --number is rejected; state unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset"])
            before = (devforge / "constitute.json").read_bytes()

            result = _run(["--devforge-dir", str(devforge), "drop-section",
                           "--number", "99.99"])
            self.assertEqual(result.returncode, 2)
            self.assertIn("99.99", result.stderr)

            after = (devforge / "constitute.json").read_bytes()
            self.assertEqual(before, after)


class TestDropRuleD6UniversalOverride(unittest.TestCase):
    """D6(a) — overrides stay available against seeded universal sections,
    and the drift detector reports exactly the deliberate divergence.

    Real-CLI round trip: reset -> seed-universal -> drop-rule / drop-section
    -> forge-internal:verify-universal-defaults.
    """

    _CANONICAL = _REPO_ROOT / "src" / "constitution.md"

    def _seeded_devforge(self, tmp):
        devforge = Path(tmp) / ".devforge"
        _run(["--devforge-dir", str(devforge), "reset"])
        seed_result = _run(["--devforge-dir", str(devforge), "seed-universal",
                             "--canonical-path", str(self._CANONICAL)])
        self.assertEqual(seed_result.returncode, 0, seed_result.stderr)
        return devforge

    def _verify_universal_defaults(self, consumer_root):
        return subprocess.run(
            [
                sys.executable, str(_HELPER_PY),
                "forge-internal:verify-universal-defaults",
                "--consumer-path", str(consumer_root),
                "--canonical-path", str(self._CANONICAL),
            ],
            capture_output=True, text=True, check=False,
        )

    def test_drop_rule_section_reports_exactly_one_missing(self):
        """Dropping §3.6's rule 1 (Single Responsibility) -> exactly one
        MISSING finding naming that rule; nothing else drifts."""
        with tempfile.TemporaryDirectory() as tmp:
            consumer_root = Path(tmp)
            devforge = self._seeded_devforge(tmp)

            drop_result = _run(["--devforge-dir", str(devforge), "drop-rule",
                                 "--section", "3.6", "--index", "1"])
            self.assertEqual(drop_result.returncode, 0, drop_result.stderr)

            result = self._verify_universal_defaults(consumer_root)
            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(len(report["findings"]), 1, msg=report["findings"])
            finding = report["findings"][0]
            self.assertEqual(finding["kind"], "MISSING")
            self.assertEqual(finding["section"], "§3.6")
            self.assertEqual(finding["rule"], "Single Responsibility")

    def test_drop_then_add_unnamed_replacement_still_reports_missing(self):
        """Dropping §3.6's rule 1 and adding an UNNAMED replacement still
        reports the same single MISSING — an unnamed rule never satisfies a
        canonical name match (D4(a))."""
        with tempfile.TemporaryDirectory() as tmp:
            consumer_root = Path(tmp)
            devforge = self._seeded_devforge(tmp)

            _run(["--devforge-dir", str(devforge), "drop-rule",
                  "--section", "3.6", "--index", "1"])
            _run(["--devforge-dir", str(devforge), "add-rule",
                  "--section", "3.6", "--tag", "project-specific",
                  "--text", "Our own take on single responsibility."])

            result = self._verify_universal_defaults(consumer_root)
            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(len(report["findings"]), 1, msg=report["findings"])
            finding = report["findings"][0]
            self.assertEqual(finding["kind"], "MISSING")
            self.assertEqual(finding["section"], "§3.6")
            self.assertEqual(finding["rule"], "Single Responsibility")

    def test_drop_section_reports_section_level_missing_only(self):
        """drop-section --number 3.7 -> a single section-level MISSING §3.7,
        with no `rule` key and no other findings."""
        with tempfile.TemporaryDirectory() as tmp:
            consumer_root = Path(tmp)
            devforge = self._seeded_devforge(tmp)

            drop_result = _run(["--devforge-dir", str(devforge), "drop-section",
                                 "--number", "3.7"])
            self.assertEqual(drop_result.returncode, 0, drop_result.stderr)

            result = self._verify_universal_defaults(consumer_root)
            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(len(report["findings"]), 1, msg=report["findings"])
            finding = report["findings"][0]
            self.assertEqual(finding["kind"], "MISSING")
            self.assertEqual(finding["section"], "§3.7")
            self.assertNotIn("rule", finding)

    def test_drop_pattern_bucket_rule_reports_missing_for_that_rule(self):
        """drop-rule --bucket always --scope universal --index 1 (§4.1's
        "Read before write.") -> exactly one MISSING naming that rule."""
        with tempfile.TemporaryDirectory() as tmp:
            consumer_root = Path(tmp)
            devforge = self._seeded_devforge(tmp)

            drop_result = _run(["--devforge-dir", str(devforge), "drop-rule",
                                 "--bucket", "always", "--scope", "universal",
                                 "--index", "1"])
            self.assertEqual(drop_result.returncode, 0, drop_result.stderr)

            result = self._verify_universal_defaults(consumer_root)
            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(len(report["findings"]), 1, msg=report["findings"])
            finding = report["findings"][0]
            self.assertEqual(finding["kind"], "MISSING")
            self.assertEqual(finding["section"], "§4.1")
            self.assertEqual(finding["rule"], "Read before write")


if __name__ == "__main__":
    unittest.main()
