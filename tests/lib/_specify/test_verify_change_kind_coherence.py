"""Tests for specify_helper verify-change-kind-coherence.

Advisory §4 <-> §5 cross-check. State is built through the real producers:
the record-affected-area / add-ac setter CLI, plus the import-handoff row
serializer for the unclassified (no change_kind) case.

Stdlib only. Python 3.8+.
"""

import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_LIB_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "src" / "devforge" / "lib"
)
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _research import handoff_schema  # noqa: E402
from _specify import _cmds_phase4_verify  # noqa: E402
from _specify._cmds_handoff import _affected_area_to_dict  # noqa: E402
from _specify._cmds_phase4_verify import (  # noqa: E402
    _change_kind_pairs,
    _norm_for_substring,
)

_SPECIFY = _LIB_DIR / "specify_helper.py"
_EVIDENCE = "src/screens/Saved.tsx:42"


def _cli(dev, *argv):
    return subprocess.run(
        [sys.executable, str(_SPECIFY), "--devforge-dir", str(dev)]
        + list(argv),
        capture_output=True, text=True,
    )


def _must(proc):
    assert proc.returncode == 0, proc.stderr
    return proc


def _row(dev, area, change_kind, evidence=_EVIDENCE):
    argv = ["record-affected-area", "--area", area, "--files", "[]",
            "--impact", "impact text", "--change-kind", change_kind]
    if evidence and change_kind == "no-code-change":
        argv += ["--path-evidence", evidence]
    _must(_cli(dev, *argv))


def _ac(dev, subsection, statement, variant="ubiquitous"):
    _must(_cli(
        dev, "add-ac", "--subsection", subsection,
        "--ears-variant", variant, "--statement", statement,
    ))


def _unclassified_row(dev, area):
    path = Path(dev) / "specify-state.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["affected_areas"].append(_affected_area_to_dict(
        handoff_schema.AffectedArea(area=area, files=[], impact="impact")
    ))
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _verify(dev, verb="verify-change-kind-coherence"):
    return _cli(dev, verb)


class _Base(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.dev = Path(self._td.name) / ".devforge"
        _must(_cli(self.dev, "reset-state"))


class TestVerifyChangeKindCoherence(_Base):
    def test_no_code_change_row_named_by_non_preservation_ac_warns(self):
        _row(self.dev, "Saved items screen", "no-code-change")
        _ac(self.dev, "behavior_change",
            "The Saved Items  Screen shall send the item id on delete.")
        r = _verify(self.dev)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(
            r.stderr,
            "verify-change-kind-coherence: WARNING — a §4 row claims this "
            "area takes the change with none of its own code changing, and "
            "a §5 AC asserts behavior on it (non-blocking — confirm the "
            "row's cited construction site reaches the area through the "
            "changed code; if it does not, correct the row first, and "
            "leave a correct AC alone):\n"
            "  - §4 row 'Saved items screen' (no-code-change)\n"
            "    path evidence: src/screens/Saved.tsx:42\n"
            "    AC-1 (behavior_change): The Saved Items  Screen shall "
            "send the item id on delete.\n",
        )

    def test_preservation_ac_is_exempt_and_silent(self):
        """The tripwire case: a behavior_preservation AC naming the area (exempt)."""
        _row(self.dev, "Saved items screen", "no-code-change")
        _ac(self.dev, "behavior_preservation",
            "The saved items screen shall continue to send the item id.")
        r = _verify(self.dev)
        self.assertEqual((r.returncode, r.stderr), (0, ""))

    def test_code_change_row_never_examined(self):
        _row(self.dev, "Saved items screen", "code-change")
        _ac(self.dev, "behavior_change",
            "The saved items screen shall send the item id.")
        r = _verify(self.dev)
        self.assertEqual((r.returncode, r.stderr), (0, ""))

    def test_unclassified_row_never_examined(self):
        _unclassified_row(self.dev, "Saved items screen")
        state = json.loads(
            (self.dev / "specify-state.json").read_text(encoding="utf-8"))
        self.assertNotIn("change_kind", state["affected_areas"][0])
        _ac(self.dev, "behavior_change",
            "The saved items screen shall send the item id.")
        r = _verify(self.dev)
        self.assertEqual((r.returncode, r.stderr), (0, ""))

    def test_whitespace_and_case_normalized(self):
        _row(self.dev, "Saved   Items\nScreen", "no-code-change")
        _ac(self.dev, "behavior_change",
            "The saved items screen shall send the item id.")
        r = _verify(self.dev)
        self.assertEqual(r.returncode, 0)
        self.assertIn("AC-1 (behavior_change)", r.stderr)

    def test_phrase_in_impact_does_not_trigger(self):
        """The trigger is the change_kind enum, never wording."""
        _must(_cli(self.dev, "record-affected-area", "--area",
                   "Saved items screen", "--files", "[]", "--impact",
                   "no code change needed", "--change-kind", "code-change"))
        _ac(self.dev, "behavior_change",
            "The saved items screen shall send the item id.")
        r = _verify(self.dev)
        self.assertEqual((r.returncode, r.stderr), (0, ""))

    def test_known_miss_preservation_ac_contradicting_row_is_silent(self):
        """KNOWN MISS of the §5.2 exemption, NOT correct behaviour.

        A behavior_preservation AC names the area but asserts behavior that
        contradicts the no-code-change claim. §5.2 is exempt, so no warning.
        """
        _row(self.dev, "Saved items screen", "no-code-change")
        _ac(self.dev, "behavior_preservation",
            "The saved items screen shall NOT send the item id.")
        r = _verify(self.dev)
        self.assertEqual((r.returncode, r.stderr), (0, ""))

    def test_statement_truncated_at_120_chars(self):
        _row(self.dev, "Saved items screen", "no-code-change")
        stmt = "The saved items screen shall send " + "the item id " * 20 + "now."
        _ac(self.dev, "behavior_change", stmt)
        r = _verify(self.dev)
        self.assertIn(": " + stmt[:120] + "\n", r.stderr)
        self.assertNotIn(stmt[:121], r.stderr)

    def test_oserror_state_read_is_non_blocking(self):
        (self.dev / "specify-state.json").unlink()
        (self.dev / "specify-state.json").mkdir()  # read raises OSError
        r = _verify(self.dev)
        self.assertEqual(r.returncode, 0)
        self.assertTrue(r.stderr.startswith(
            "verify-change-kind-coherence: state read failed: "))
        self.assertTrue(r.stderr.endswith("(non-blocking)\n"))

    def test_known_miss_other_words_is_silent(self):
        """KNOWN MISS of the substring predicate, NOT correct behaviour.

        The AC asserts a change on the same surface but calls it "the
        bookmarks view", so it does not contain the row's area string and no
        warning fires. Silence here means "matched nothing", not "spec clean".
        """
        _row(self.dev, "Saved items screen", "no-code-change")
        _ac(self.dev, "behavior_change",
            "The bookmarks view shall send the item id on delete.")
        r = _verify(self.dev)
        self.assertEqual((r.returncode, r.stderr), (0, ""))

    def test_multiple_rows_and_acs_exact_pairs_in_order(self):
        _row(self.dev, "Alpha panel", "no-code-change", "a.py:1")
        _row(self.dev, "Beta panel", "code-change")
        _row(self.dev, "Gamma panel", "no-code-change", "g.py:3")
        _ac(self.dev, "behavior_change", "The alpha panel shall do X.")
        _ac(self.dev, "behavior_change", "The beta panel shall do Y.")
        _ac(self.dev, "behavior_preservation", "The gamma panel shall stay.")
        _ac(self.dev, "documentation",
            "The docs shall describe the gamma panel and the alpha panel.")
        r = _verify(self.dev)
        self.assertEqual(r.returncode, 0)
        lines = [l for l in r.stderr.splitlines() if l.startswith("  - ")]
        self.assertEqual(lines, [
            "  - §4 row 'Alpha panel' (no-code-change)",
            "  - §4 row 'Alpha panel' (no-code-change)",
            "  - §4 row 'Gamma panel' (no-code-change)",
        ])
        ac_lines = [l.strip().split(" ")[0] for l in r.stderr.splitlines()
                    if l.startswith("    AC-")]
        self.assertEqual(ac_lines, ["AC-1", "AC-4", "AC-4"])

    def test_state_read_failure_matches_scope_coherence_shape(self):
        (self.dev / "specify-state.json").write_text("{not json")
        new = _verify(self.dev)
        old = _verify(self.dev, "verify-scope-coherence")
        self.assertEqual((new.returncode, old.returncode), (0, 0))
        self.assertTrue(new.stderr.startswith(
            "verify-change-kind-coherence: state read failed: "))
        self.assertTrue(new.stderr.endswith("(non-blocking)\n"))
        self.assertEqual(
            new.stderr.replace("verify-change-kind-coherence", "X"),
            old.stderr.replace("verify-scope-coherence", "X"),
        )

    def test_scope_coherence_output_unchanged_on_fixture(self):
        _row(self.dev, "Saved items screen", "no-code-change")
        _ac(self.dev, "behavior_change",
            "The saved items screen shall export billing reports.")
        _must(_cli(self.dev, "record-out-of-scope",
                   "--content", "Billing reports export"))
        r = _verify(self.dev, "verify-scope-coherence")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(
            r.stderr,
            "verify-scope-coherence: §5/§4 entries may mandate behaviour "
            "excluded by §6 Out-of-Scope (non-blocking — review and "
            "reconcile):\n"
            "  - §6 OOS: Billing reports export\n"
            "    AC AC-1: The saved items screen shall export billing "
            "reports.\n"
            "    overlap tokens: billing, export, reports\n"
            "    reconcile: drop the §6 entry (concern is in scope) OR "
            "weaken/remove the §5/§4 mandate (concern is out of scope).\n",
        )


class TestPredicateUnits(unittest.TestCase):
    def test_norm_for_substring(self):
        self.assertEqual(_norm_for_substring("  A \t B\n\nC  "), "a b c")
        self.assertEqual(_norm_for_substring(None), "")
        self.assertEqual(_norm_for_substring("a\u00a0\u00a0b"), "a b")

    def test_predicate_is_substring_plus_not_behavior_preservation(self):
        def st(kind, area, acs):
            return {
                "affected_areas": [{"area": area, "change_kind": kind}],
                "acceptance_criteria": [
                    {"ac_id": "A%d" % i, "subsection": sub, "statement": s}
                    for i, (sub, s) in enumerate(acs)
                ],
            }
        hit = ("behavior_change", "The Foo   Bar shall send x.")
        pres = ("behavior_preservation", "The foo bar shall stay.")
        miss = ("behavior_change", "The foo shall send x.")
        pairs = _change_kind_pairs(
            st("no-code-change", "foo bar", [hit, pres, miss]))
        self.assertEqual([ac["ac_id"] for _, ac in pairs], ["A0"])
        # Not token overlap: shared tokens without the contiguous string.
        self.assertEqual(_change_kind_pairs(
            st("no-code-change", "bar foo", [hit])), [])
        # Enum-keyed: other values and absent key never examined.
        self.assertEqual(
            _change_kind_pairs(st("code-change", "foo bar", [hit])), [])
        state = st("no-code-change", "foo bar", [hit])
        del state["affected_areas"][0]["change_kind"]
        self.assertEqual(_change_kind_pairs(state), [])
        # Empty area never matches everything.
        self.assertEqual(
            _change_kind_pairs(st("no-code-change", "  ", [hit])), [])

    def test_verb_does_not_call_tokenize_for_overlap(self):
        """The verb's functions must not call tokenize_for_overlap."""
        tree = ast.parse(Path(_cmds_phase4_verify.__file__).read_text(
            encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in (
                "_change_kind_pairs", "_norm_for_substring",
                "cmd_verify_change_kind_coherence",
            ):
                names = {n.id for n in ast.walk(node)
                         if isinstance(n, ast.Name)}
                names |= {n.attr for n in ast.walk(node)
                          if isinstance(n, ast.Attribute)}
                self.assertNotIn("tokenize_for_overlap", names, node.name)


if __name__ == "__main__":
    unittest.main()
