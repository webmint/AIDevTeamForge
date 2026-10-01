"""Tests for the §4 Affected Areas change_kind / path_evidence keys.

Covers CHANGE_KIND_ENUM, PATH_EVIDENCE_RE, _validate_path_evidence and
cmd_record_affected_area (called directly with a fake argparse.Namespace,
mirroring test_record_handoff_path.py). The CLI round trip lives in
tests/lib/test_specify_helper.py.

Stdlib only. Python 3.8+.
"""

import argparse
import contextlib
import io
import json
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

from _specify._cmds_phase4_setters import cmd_record_affected_area  # noqa: E402
from _specify._schema import CHANGE_KIND_ENUM, PATH_EVIDENCE_RE  # noqa: E402
from _specify._state import _load_state, default_state  # noqa: E402
from _specify._validators import _validate_path_evidence  # noqa: E402

_SENTENCE = "reached through the feed screen"


def _args(devforge_dir, change_kind, path_evidence="", area="Feed"):
    return argparse.Namespace(
        devforge_dir=str(devforge_dir),
        area=area,
        files=json.dumps(["a.ts"]),
        impact="none",
        change_kind=change_kind,
        path_evidence=path_evidence,
    )


def _write_state(devforge_dir, state):
    Path(devforge_dir).mkdir(parents=True, exist_ok=True)
    (Path(devforge_dir) / "specify-state.json").write_text(
        json.dumps(state, indent=2), encoding="utf-8",
    )


def _call(args):
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        rc = cmd_record_affected_area(args)
    return rc, err.getvalue()


class SchemaTests(unittest.TestCase):
    def test_change_kind_enum_is_exactly_two_values(self):
        self.assertEqual(CHANGE_KIND_ENUM, ("code-change", "no-code-change"))

    def test_path_evidence_re_is_compiled_and_anchored(self):
        self.assertTrue(PATH_EVIDENCE_RE.fullmatch("a.ts:1"))
        self.assertIsNone(PATH_EVIDENCE_RE.fullmatch("a.ts:1\nextra"))

    def test_path_evidence_re_rejects_trailing_newline_directly(self):
        self.assertIsNone(PATH_EVIDENCE_RE.fullmatch("a.ts:1\n"))


class ValidatePathEvidenceTests(unittest.TestCase):
    def test_accepts(self):
        for v in ("src/a/b.ts:412", "Makefile:3", "a.py:10"):
            with self.subTest(v):
                self.assertEqual(_validate_path_evidence(v), v)

    def test_strips_surrounding_whitespace(self):
        self.assertEqual(_validate_path_evidence("  a.py:3 "), "a.py:3")

    def test_rejects(self):
        bad = [
            _SENTENCE, "", "   ", "src/a.ts", "path:0", "path:", ":12",
            "path:12-14", "my file.ts:3", "a.ts:3 and more", "see a.ts:3",
            "a:b.ts:3", "a.ts:03", "a.ts:-1", "a.ts:3\nb.ts:4",
        ]
        for v in bad:
            with self.subTest(v):
                with self.assertRaises(ValueError) as ctx:
                    _validate_path_evidence(v)
                self.assertIn("path_evidence", str(ctx.exception))
                self.assertIn("file:line", str(ctx.exception))

    def test_none_rejected(self):
        with self.assertRaises(ValueError):
            _validate_path_evidence(None)


class RecordAffectedAreaTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.dev = Path(self._td.name) / ".devforge"
        _write_state(self.dev, default_state())

    def _areas(self):
        return _load_state(str(self.dev))["affected_areas"]

    def _assert_rejected(self, args):
        rc, err = _call(args)
        self.assertEqual(rc, 2, err)
        self.assertEqual(self._areas(), [])
        return err

    def test_invalid_change_kind(self):
        self._assert_rejected(_args(self.dev, "maybe"))

    def test_none_change_kind(self):
        self._assert_rejected(_args(self.dev, None))

    def test_no_code_change_without_evidence(self):
        err = self._assert_rejected(_args(self.dev, "no-code-change", ""))
        self.assertIn("path_evidence", err)
        self.assertIn("construction site", err)
        self.assertIn("record-open-question", err)

    def test_no_code_change_whitespace_evidence(self):
        self._assert_rejected(_args(self.dev, "no-code-change", "  "))

    def test_no_code_change_with_sentence(self):
        self._assert_rejected(_args(self.dev, "no-code-change", _SENTENCE))

    def test_code_change_with_sentence(self):
        self._assert_rejected(_args(self.dev, "code-change", _SENTENCE))

    def test_code_change_without_evidence(self):
        rc, err = _call(_args(self.dev, "code-change"))
        self.assertEqual(rc, 0, err)
        row = self._areas()[0]
        self.assertEqual(row["change_kind"], "code-change")
        self.assertEqual(row["path_evidence"], "")

    def test_code_change_with_none_evidence(self):
        rc, err = _call(_args(self.dev, "code-change", None))
        self.assertEqual(rc, 0, err)
        self.assertEqual(self._areas()[0]["path_evidence"], "")

    def test_no_code_change_with_evidence(self):
        ev = "src/app/screens/Feed.tsx:412"
        rc, err = _call(_args(self.dev, "no-code-change", ev))
        self.assertEqual(rc, 0, err)
        row = self._areas()[0]
        self.assertEqual(row["change_kind"], "no-code-change")
        self.assertEqual(row["path_evidence"], ev)
        self.assertEqual(
            set(row), {"area", "files", "impact", "change_kind",
                       "path_evidence"},
        )

    def test_code_change_with_valid_evidence(self):
        rc, err = _call(_args(self.dev, "code-change", "Makefile:3"))
        self.assertEqual(rc, 0, err)
        self.assertEqual(self._areas()[0]["path_evidence"], "Makefile:3")

    def test_legacy_row_not_fabricated_and_untouched(self):
        state = default_state()
        legacy = {"area": "Old", "files": ["o.ts"], "impact": "x"}
        state["affected_areas"] = [dict(legacy)]
        _write_state(self.dev, state)
        self.assertEqual(self._areas(), [legacy])
        self.assertNotIn("change_kind", self._areas()[0])
        rc, err = _call(_args(self.dev, "code-change"))
        self.assertEqual(rc, 0, err)
        rows = self._areas()
        self.assertEqual(rows[0], legacy)
        self.assertEqual(rows[1]["change_kind"], "code-change")


if __name__ == "__main__":
    unittest.main()
