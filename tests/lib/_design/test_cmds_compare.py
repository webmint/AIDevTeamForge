"""Tests for src/devforge/lib/_design/_cmds_compare.py -- the `compare` CLI
verb (plan 53 Phase 4/5).

Real-fixture discipline: these tests write real bag/binding JSON files to a
temp dir and invoke the REAL argparse-driven `main()` entry point (the same
one design_helper's POSIX launcher calls), then parse the REAL stdout JSON
-- an end-to-end round-trip through the actual CLI surface Phase 6 will
wire the design-auditor to call, not a hand-authored shortcut around it.

Coverage:
  - --built-bag missing file -> exit 2, stderr names the flag
  - --built-bag required, absent entirely -> exit 2
  - malformed bag JSON at --built-bag -> exit 2, stderr names the problem
  - a NOT_COVERED run (region_found:false) -> exit 0, stdout status
    NOT_COVERED
  - a CLEAN run (built bag only, no intent/binding) -> exit 0, stdout status
    CLEAN, fidelity_covered false
  - a DEFECT run (floor violation, built bag only) -> exit 0, stdout status
    DEFECT, floor_findings populated
  - a full run with --intent-bag + --binding, zero mismatch -> exit 0,
    status CLEAN, fidelity_covered true
  - a full run with --intent-bag + --binding, a mismatch -> exit 0, status
    DEFECT, fidelity_findings populated
  - --intent-bag file missing -> exit 2
  - --binding file missing -> exit 2
  - malformed --binding JSON (retired data-ref shape) -> exit 2
  - --route is required -> exit 2 (missing) via argparse
  - reachable via the package's main([...]) entry point (mirrors how the
    POSIX launcher invokes it)

FIX F1: --route "" (present but blank) satisfies argparse's required=True,
  so it must be rejected explicitly inside cmd_compare -- exit 2, not an
  uncaught ValueError traceback -- both when a floor defect would otherwise
  be produced (the crash's original data-dependent trigger) and when the
  run would otherwise be clean (proving the rejection is unconditional, not
  only triggered by the presence of a finding).

FIX F6: --intent-bag without --binding (or vice versa) silently degrades to
  floor-only coverage with no signal to the caller -- a stderr diagnostic
  note must be emitted (non-fatal; the floor still runs) for both
  asymmetric combinations.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _design._cli import main  # noqa: E402
from _design._schema import Binding, BindingPair, binding_to_json  # noqa: E402

_ROUTE = "/dashboard"


def _style(**overrides):
    style = {
        "color": "rgb(0, 0, 0)",
        "background": "rgba(0, 0, 0, 0)",
        "border": "1px solid rgb(0, 0, 0)",
        "border_radius": "4px",
        "padding": "8px",
        "margin": "0px",
        "gap": "8px",
        "font_family": '"Inter", sans-serif',
        "font_size": "14px",
        "line_height": "20px",
        "font_weight": "400",
    }
    style.update(overrides)
    return style


def _geometry(width=100.0, height=40.0):
    return {
        "x": 0.0,
        "y": 0.0,
        "width": width,
        "height": height,
        "scroll_width": width,
        "client_width": width,
    }


def _element(found=True, style=None):
    if not found:
        return {"found": False}
    return {
        "found": True,
        "style": style if style is not None else _style(),
        "geometry": _geometry(),
        "overflow_x": "visible",
        "position": "static",
    }


class CmdComparePathTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        self.tmp = self._tmpdir.name

    def _write_json(self, name, data):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return path

    def _run(self, argv):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(argv)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_built_bag_missing_file(self):
        missing = os.path.join(self.tmp, "nope.json")
        code, out, err = self._run(["compare", "--built-bag", missing, "--route", _ROUTE])
        self.assertEqual(code, 2)
        self.assertIn("--built-bag", err)

    def test_built_bag_required(self):
        # argparse enforces required=True by raising SystemExit(2) directly
        # from parse_args(), before cmd_compare ever runs.
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as ctx:
                main(["compare", "--route", _ROUTE])
        self.assertEqual(ctx.exception.code, 2)

    def test_malformed_built_bag_json(self):
        path = os.path.join(self.tmp, "built.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{not valid json")
        code, out, err = self._run(["compare", "--built-bag", path, "--route", _ROUTE])
        self.assertEqual(code, 2)
        self.assertIn("bag", err)

    def test_not_covered_run(self):
        built_path = self._write_json("built.json", {"region_found": False, "elements": {}})
        code, out, err = self._run(["compare", "--built-bag", built_path, "--route", _ROUTE])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["status"], "NOT_COVERED")
        self.assertIsNotNone(result["not_covered_reason"])

    def test_clean_run_built_bag_only(self):
        built_path = self._write_json("built.json", {"region_found": True, "elements": {}})
        code, out, err = self._run(["compare", "--built-bag", built_path, "--route", _ROUTE])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["status"], "CLEAN")
        self.assertFalse(result["fidelity_covered"])

    def test_defect_run_floor_violation(self):
        built_path = self._write_json(
            "built.json",
            {
                "region_found": True,
                "elements": {},
                "overflow_candidates": [
                    {
                        "label": "a",
                        "scroll_width": 500,
                        "client_width": 100,
                        "overflow_x": "visible",
                    }
                ],
            },
        )
        code, out, err = self._run(["compare", "--built-bag", built_path, "--route", _ROUTE])
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["status"], "DEFECT")
        self.assertEqual(len(result["floor_findings"]), 1)
        self.assertEqual(result["floor_findings"][0]["kind"], "overflow")

    def test_full_run_with_intent_and_binding_clean(self):
        built_path = self._write_json(
            "built.json", {"region_found": True, "elements": {"built-el": _element()}}
        )
        intent_path = self._write_json(
            "intent.json", {"region_found": True, "elements": {".ref": _element()}}
        )
        binding = Binding(route=_ROUTE, pairs=[BindingPair(".ref", "built-el")])
        binding_path = os.path.join(self.tmp, "binding.json")
        with open(binding_path, "w", encoding="utf-8") as fh:
            fh.write(binding_to_json(binding))

        code, out, err = self._run(
            [
                "compare",
                "--built-bag",
                built_path,
                "--intent-bag",
                intent_path,
                "--binding",
                binding_path,
                "--route",
                _ROUTE,
            ]
        )
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["status"], "CLEAN")
        self.assertTrue(result["fidelity_covered"])

    def test_full_run_with_intent_and_binding_defect(self):
        built_path = self._write_json(
            "built.json",
            {
                "region_found": True,
                "elements": {"built-el": _element(style=_style(color="rgb(255,0,0)"))},
            },
        )
        intent_path = self._write_json(
            "intent.json", {"region_found": True, "elements": {".ref": _element()}}
        )
        binding = Binding(route=_ROUTE, pairs=[BindingPair(".ref", "built-el")])
        binding_path = os.path.join(self.tmp, "binding.json")
        with open(binding_path, "w", encoding="utf-8") as fh:
            fh.write(binding_to_json(binding))

        code, out, err = self._run(
            [
                "compare",
                "--built-bag",
                built_path,
                "--intent-bag",
                intent_path,
                "--binding",
                binding_path,
                "--route",
                _ROUTE,
            ]
        )
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["status"], "DEFECT")
        self.assertEqual(len(result["fidelity_findings"]), 1)

    def test_intent_bag_missing_file(self):
        built_path = self._write_json("built.json", {"region_found": True, "elements": {}})
        missing = os.path.join(self.tmp, "nope.json")
        code, out, err = self._run(
            [
                "compare",
                "--built-bag",
                built_path,
                "--intent-bag",
                missing,
                "--route",
                _ROUTE,
            ]
        )
        self.assertEqual(code, 2)
        self.assertIn("--intent-bag", err)

    def test_binding_missing_file(self):
        built_path = self._write_json("built.json", {"region_found": True, "elements": {}})
        missing = os.path.join(self.tmp, "nope.json")
        code, out, err = self._run(
            ["compare", "--built-bag", built_path, "--binding", missing, "--route", _ROUTE]
        )
        self.assertEqual(code, 2)
        self.assertIn("--binding", err)

    def test_binding_retired_schema_rejected(self):
        built_path = self._write_json("built.json", {"region_found": True, "elements": {}})
        binding_path = self._write_json(
            "binding.json", {"version": "1", "elements": [], "gap_list": []}
        )
        code, out, err = self._run(
            ["compare", "--built-bag", built_path, "--binding", binding_path, "--route", _ROUTE]
        )
        self.assertEqual(code, 2)
        self.assertIn("--binding", err)

    def test_route_required(self):
        built_path = self._write_json("built.json", {"region_found": True, "elements": {}})
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as ctx:
                main(["compare", "--built-bag", built_path])
        self.assertEqual(ctx.exception.code, 2)

    def test_route_blank_with_defect_exits_2_not_traceback(self):
        # FIX F1: the original bug only crashed when a real finding was
        # produced (DesignFinding rejects a blank `file`) -- reproduce that
        # exact trigger (an overflow floor violation) and assert a clean
        # exit 2, not an uncaught exception propagating out of main().
        built_path = self._write_json(
            "built.json",
            {
                "region_found": True,
                "elements": {},
                "overflow_candidates": [
                    {
                        "label": "a",
                        "scroll_width": 500,
                        "client_width": 100,
                        "overflow_x": "visible",
                    }
                ],
            },
        )
        code, out, err = self._run(["compare", "--built-bag", built_path, "--route", ""])
        self.assertEqual(code, 2)
        self.assertIn("--route", err)
        self.assertNotIn("Traceback", err)

    def test_route_blank_with_clean_run_still_exits_2(self):
        # Proves the rejection is UNCONDITIONAL, not data-dependent on a
        # finding being produced -- a blank route is rejected even when the
        # comparison would otherwise be a clean pass.
        built_path = self._write_json("built.json", {"region_found": True, "elements": {}})
        code, out, err = self._run(["compare", "--built-bag", built_path, "--route", ""])
        self.assertEqual(code, 2)
        self.assertIn("--route", err)

    def test_route_whitespace_only_rejected(self):
        built_path = self._write_json("built.json", {"region_found": True, "elements": {}})
        code, out, err = self._run(["compare", "--built-bag", built_path, "--route", "   "])
        self.assertEqual(code, 2)
        self.assertIn("--route", err)

    def test_intent_bag_without_binding_note(self):
        # FIX F6: --intent-bag given without --binding degrades silently to
        # floor-only coverage -- a stderr note must surface it.
        built_path = self._write_json(
            "built.json", {"region_found": True, "elements": {"built-el": _element()}}
        )
        intent_path = self._write_json(
            "intent.json", {"region_found": True, "elements": {".ref": _element()}}
        )
        code, out, err = self._run(
            [
                "compare",
                "--built-bag",
                built_path,
                "--intent-bag",
                intent_path,
                "--route",
                _ROUTE,
            ]
        )
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertFalse(result["fidelity_covered"])
        self.assertIn("--intent-bag", err)
        self.assertIn("--binding", err)
        self.assertIn("note:", err)

    def test_binding_without_intent_bag_note(self):
        built_path = self._write_json(
            "built.json", {"region_found": True, "elements": {"built-el": _element()}}
        )
        binding = Binding(route=_ROUTE, pairs=[BindingPair(".ref", "built-el")])
        binding_path = os.path.join(self.tmp, "binding.json")
        with open(binding_path, "w", encoding="utf-8") as fh:
            fh.write(binding_to_json(binding))

        code, out, err = self._run(
            ["compare", "--built-bag", built_path, "--binding", binding_path, "--route", _ROUTE]
        )
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertFalse(result["fidelity_covered"])
        self.assertIn("--binding", err)
        self.assertIn("--intent-bag", err)
        self.assertIn("note:", err)

    def test_symmetric_intent_and_binding_no_note(self):
        # Sanity check: giving BOTH --intent-bag and --binding together
        # (the well-formed case) must NOT emit the asymmetry note.
        built_path = self._write_json(
            "built.json", {"region_found": True, "elements": {"built-el": _element()}}
        )
        intent_path = self._write_json(
            "intent.json", {"region_found": True, "elements": {".ref": _element()}}
        )
        binding = Binding(route=_ROUTE, pairs=[BindingPair(".ref", "built-el")])
        binding_path = os.path.join(self.tmp, "binding.json")
        with open(binding_path, "w", encoding="utf-8") as fh:
            fh.write(binding_to_json(binding))

        code, out, err = self._run(
            [
                "compare",
                "--built-bag",
                built_path,
                "--intent-bag",
                intent_path,
                "--binding",
                binding_path,
                "--route",
                _ROUTE,
            ]
        )
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertTrue(result["fidelity_covered"])
        self.assertNotIn("note:", err)

    def test_binding_null_top_level_exits_2(self):
        # FIX F2: a binding JSON whose top level is `null` must not crash
        # with an uncaught TypeError -- exit 2 via the same --binding catch
        # site.
        built_path = self._write_json("built.json", {"region_found": True, "elements": {}})
        binding_path = os.path.join(self.tmp, "binding.json")
        with open(binding_path, "w", encoding="utf-8") as fh:
            fh.write("null")
        code, out, err = self._run(
            ["compare", "--built-bag", built_path, "--binding", binding_path, "--route", _ROUTE]
        )
        self.assertEqual(code, 2)
        self.assertIn("--binding", err)
        self.assertNotIn("Traceback", err)

    def test_binding_list_top_level_exits_2(self):
        built_path = self._write_json("built.json", {"region_found": True, "elements": {}})
        binding_path = self._write_json("binding.json", [1, 2, 3])
        code, out, err = self._run(
            ["compare", "--built-bag", built_path, "--binding", binding_path, "--route", _ROUTE]
        )
        self.assertEqual(code, 2)
        self.assertIn("--binding", err)
        self.assertNotIn("Traceback", err)

    def test_binding_pairs_non_dict_entry_exits_2(self):
        built_path = self._write_json("built.json", {"region_found": True, "elements": {}})
        binding_path = self._write_json(
            "binding.json", {"route": "/x", "pairs": ["x"]}
        )
        code, out, err = self._run(
            ["compare", "--built-bag", built_path, "--binding", binding_path, "--route", _ROUTE]
        )
        self.assertEqual(code, 2)
        self.assertIn("--binding", err)
        self.assertNotIn("Traceback", err)


if __name__ == "__main__":
    unittest.main()
