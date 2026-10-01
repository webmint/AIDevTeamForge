"""Tests for the §4 Affected Areas render of change_kind / path_evidence.

State is built through the real producers (the specify_helper CLI's
record-affected-area, and the import-handoff serializer for an
"unclassified" seeded row) and rendered with the real renderer. Downstream
consumers of the rendered table (cbm_sync_helper's §4 harvest and
plan_helper render-findings-from-spec) are exercised over that real output.

Stdlib only. Python 3.8+.
"""

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

import cbm_sync_helper  # noqa: E402
from _research import handoff_schema  # noqa: E402
from _specify._cmds_handoff import _affected_area_to_dict  # noqa: E402
from _specify._render import render_spec  # noqa: E402
from _specify._state import _load_state, default_state  # noqa: E402

_SPECIFY = _LIB_DIR / "specify_helper.py"
_PLAN = _LIB_DIR / "plan_helper.py"

_HEADER = "| Area | Files | Impact | Change kind | Path evidence |"
_SEPARATOR = "|------|-------|--------|-------------|---------------|"
_PLACEHOLDER = "| _(none)_ | _(none)_ | _(none)_ | _(none)_ | _(none)_ |"


def _record(dev, area, files, impact, change_kind, path_evidence=None):
    argv = [
        sys.executable, str(_SPECIFY), "--devforge-dir", str(dev),
        "record-affected-area", "--area", area,
        "--files", json.dumps(files), "--impact", impact,
        "--change-kind", change_kind,
    ]
    if path_evidence is not None:
        argv += ["--path-evidence", path_evidence]
    proc = subprocess.run(argv, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc


def _append_unclassified(dev, area, files, impact):
    """Append a row via the import-handoff serializer: no new keys."""
    state_path = Path(dev) / "specify-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["affected_areas"].append(_affected_area_to_dict(
        handoff_schema.AffectedArea(area=area, files=files, impact=impact)
    ))
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def _section4(rendered):
    start = rendered.index("## 4. Affected Areas")
    end = rendered.index("## 5. Acceptance Criteria")
    return rendered[start:end].splitlines()


def _table_rows(rendered):
    return [ln for ln in _section4(rendered) if ln.startswith("|")]


def _cells(row):
    """Split a rendered row into its cells, keeping empty ones."""
    return [c.strip() for c in row.strip()[1:-1].split("|")]


class _Base(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.tmp = Path(self._td.name)
        self.dev = self.tmp / ".devforge"
        self.dev.mkdir()
        (self.dev / "specify-state.json").write_text(
            json.dumps(default_state(), indent=2), encoding="utf-8",
        )

    def render(self):
        return render_spec(_load_state(str(self.dev)))


class RenderShapeTests(_Base):
    def test_no_rows_placeholder_has_five_cells(self):
        rows = _table_rows(self.render())
        self.assertEqual(rows, [_HEADER, _SEPARATOR, _PLACEHOLDER])
        self.assertEqual(len(_cells(rows[2])), 5)

    def test_header_and_separator_are_five_columns_in_order(self):
        _record(self.dev, "Feed", ["a.ts"], "x", "code-change")
        rows = _table_rows(self.render())
        self.assertEqual(rows[0], _HEADER)
        self.assertEqual(rows[1], _SEPARATOR)
        self.assertEqual(
            _cells(rows[0]),
            ["Area", "Files", "Impact", "Change kind", "Path evidence"],
        )
        self.assertEqual(len(_cells(rows[1])), 5)

    def test_no_code_change_row_shows_kind_and_backticked_evidence(self):
        _record(self.dev, "Feed", ["a.ts"], "none", "no-code-change",
                "src/a/b.ts:412")
        row = _table_rows(self.render())[2]
        self.assertEqual(
            _cells(row),
            ["Feed", "a.ts", "none", "no-code-change", "`src/a/b.ts:412`"],
        )

    def test_code_change_without_evidence_has_empty_last_cell(self):
        _record(self.dev, "Feed", ["a.ts"], "edit", "code-change")
        row = _table_rows(self.render())[2]
        self.assertEqual(_cells(row), ["Feed", "a.ts", "edit",
                                       "code-change", ""])
        self.assertNotIn("``", row)

    def test_files_cell_stays_bare(self):
        _record(self.dev, "Feed", ["src/x/y.ts", "b.ts"], "i", "code-change")
        row = _table_rows(self.render())[2]
        self.assertEqual(_cells(row)[1], "src/x/y.ts, b.ts")


class UnclassifiedRowTests(_Base):
    def test_unclassified_row_renders_both_new_cells_empty(self):
        _append_unclassified(self.dev, "Seeded", ["s/a.ts"], "seeded impact")
        row = _table_rows(self.render())[2]
        self.assertEqual(
            _cells(row), ["Seeded", "s/a.ts", "seeded impact", "", ""],
        )
        self.assertNotIn("code-change", row)
        self.assertNotIn("`", row)

    def test_unclassified_row_beside_classified_rows(self):
        _record(self.dev, "Feed", ["a.ts"], "i", "code-change")
        _append_unclassified(self.dev, "Seeded", ["s/a.ts"], "j")
        rows = _table_rows(self.render())
        self.assertEqual(_cells(rows[2])[3], "code-change")
        self.assertEqual(_cells(rows[3])[3:], ["", ""])


class HandEditedEvidenceTests(_Base):
    def test_blank_or_none_evidence_renders_empty_cell_no_backticks(self):
        _record(self.dev, "Blank", ["a.ts"], "i", "code-change")
        _record(self.dev, "Null", ["b.ts"], "j", "code-change")
        state_path = self.dev / "specify-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["affected_areas"][0]["path_evidence"] = "   "
        state["affected_areas"][1]["path_evidence"] = None
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        rows = _table_rows(self.render())[2:]
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(_cells(row)[4], "")
            self.assertNotIn("`", row)


class CbmHarvestTests(_Base):
    def _harvest(self):
        spec = self.tmp / "spec.md"
        spec.write_text(self.render(), encoding="utf-8")
        return cbm_sync_helper._parse_affected_areas(str(spec))

    def test_bare_files_cell_contributes_nothing(self):
        _record(self.dev, "Feed", ["src/x/y.ts"], "plain", "code-change")
        self.assertEqual(self._harvest(), [])

    def test_backticked_path_line_evidence_contributes_nothing(self):
        _record(self.dev, "Feed", ["src/x/y.ts"], "plain", "no-code-change",
                "src/app/Feed.tsx:412")
        spec_text = self.render()
        self.assertIn("`src/app/Feed.tsx:412`", spec_text)
        self.assertEqual(self._harvest(), [])

    def test_backticked_path_in_impact_is_harvested(self):
        _record(self.dev, "Feed", ["src/x/y.ts"], "plain", "no-code-change",
                "src/app/Feed.tsx:412")
        _record(self.dev, "Zed", ["q.ts"], "touches `src/z/w.ts` only",
                "code-change")
        self.assertEqual(self._harvest(), ["src/z/w.ts"])


class PlanHelperRoundTripTests(_Base):
    def _findings(self, name):
        spec = self.tmp / name
        spec.write_text(self.render(), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(_PLAN), "render-findings-from-spec",
             str(spec)],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return [ln for ln in proc.stdout.splitlines()
                if ln.startswith("- §4 row")]

    def test_rows_identical_with_and_without_new_keys(self):
        _record(self.dev, "Alpha", ["a/one.ts"], "first", "no-code-change",
                "a/one.ts:7")
        _record(self.dev, "Beta", ["b/two.ts"], "second", "code-change",
                "b/two.ts:9")
        _append_unclassified(self.dev, "Gamma", ["g/three.ts"], "third")
        with_keys = self._findings("with.md")
        self.assertEqual(len(with_keys), 3)

        state_path = self.dev / "specify-state.json"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        for a in state["affected_areas"]:
            a.pop("change_kind", None)
            a.pop("path_evidence", None)
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        without_keys = self._findings("without.md")

        self.assertEqual(with_keys, without_keys)
        self.assertIn("Gamma", with_keys[2])
        self.assertIn("g/three.ts", with_keys[2])
        self.assertIn("Alpha", with_keys[0])
        self.assertIn("b/two.ts", with_keys[1])


if __name__ == "__main__":
    unittest.main()
