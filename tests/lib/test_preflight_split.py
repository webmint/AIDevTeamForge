"""Tests for _preflight.py split-aware stamp aggregation — Plan F 3a.4.

Cases:
  1.  _diff_concern with split-eligible content + threshold > 0 → split:true,
      sub_concerns[] populated, aggregate stamp set
  2.  _diff_concern under threshold → existing single-batch shape preserved
  3.  _diff_concern: split with single subdir → does NOT split (need ≥ 2)
  4.  _diff_concern: split with threshold_kb=0 → never splits
  5.  Per-child status: no prior child docs → each child status "new"
  6.  Per-child status: prior child doc with matching stamp → "unchanged"
  7.  Per-child status: prior child doc with stale stamp → "changed"
  8.  Parent status: all children unchanged + agg stamp matches prior → "unchanged"
  9.  Parent status: all children unchanged + agg stamp DIFFERS from prior → "changed"
 10.  Parent status: one child changed → parent "changed" (regardless of agg match)
 11.  Parent status: parent doc missing → "new"
 12.  Aggregate stamp deterministic across runs
 13.  cmd_preflight: subconcern_counts populated when any concern split
 14.  cmd_preflight: subconcern_counts zeros when no concerns split
 15.  cross-helper consistency: preflight aggregate stamp matches concern-input
      aggregate stamp for same content

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _generate_docs._preflight import (  # noqa: E402
    _diff_concern,
    cmd_preflight,
)
from _generate_docs._concern_input import (  # noqa: E402
    cmd_concern_input,
)


def _write_index_json(devforge_dir: Path, packages: dict) -> None:
    devforge_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "generated_at": "2026-05-08T00:00:00Z",
        "project_root": str(devforge_dir.parent),
        "packages": packages,
    }
    (devforge_dir / "index.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def _make_big_file(path: Path, kb: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = "// TODO real content here padded out: " + ("X" * 100) + "\n"
    bytes_per_line = len(line.encode("utf-8"))
    n_lines = max(1, (kb * 1024) // bytes_per_line + 1)
    path.write_text(line * n_lines, encoding="utf-8")


def _seed_split_eligible(root: Path, pkg: str, concern: str, kb_per_child: int = 25):
    base = root / pkg / "src" / concern
    for child in ("alpha", "beta", "gamma"):
        _make_big_file(base / child / "f.ts", kb=kb_per_child)


def _write_doc(docs_root: Path, pkg: str, concern: str, source_stamp: str, sub: str = ""):
    """Write a minimal doc with the given source_stamp into the appropriate path."""
    if sub:
        path = docs_root / pkg / concern / sub / "index.md"
    else:
        path = docs_root / pkg / concern / "index.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nconcern: {sub or concern}\nsource_stamp: {source_stamp}\n---\n\nbody\n",
        encoding="utf-8",
    )


class DiffConcernSplitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.docs = self.root / "docs"

    def test_split_eligible_emits_split_true(self):
        _seed_split_eligible(self.root, "pkg-a", "components")
        result = _diff_concern(
            "pkg-a", "components", self.root, self.docs, split_threshold_kb=5
        )
        self.assertTrue(result.get("split"), msg=result)
        self.assertEqual(len(result["sub_concerns"]), 3)
        names = sorted(sc["concern"] for sc in result["sub_concerns"])
        self.assertEqual(names, ["alpha", "beta", "gamma"])
        # Aggregate stamp present + valid format
        self.assertRegex(result["source_stamp"], r"^[0-9a-f]{16}$")

    def test_under_threshold_does_not_split(self):
        # 3 small children; default 50 KB threshold not crossed
        base = self.root / "pkg-a" / "src" / "components"
        for child in ("a", "b", "c"):
            (base / child).mkdir(parents=True)
            (base / child / "f.ts").write_text("export const x = 1;\n", encoding="utf-8")
        result = _diff_concern("pkg-a", "components", self.root, self.docs)
        self.assertNotIn("split", result)
        self.assertNotIn("sub_concerns", result)

    def test_single_child_does_not_split(self):
        base = self.root / "pkg-a" / "src" / "components"
        for i in range(5):
            _make_big_file(base / "only-child" / f"f{i}.ts", kb=10)
        result = _diff_concern(
            "pkg-a", "components", self.root, self.docs, split_threshold_kb=5
        )
        self.assertNotIn("split", result)

    def test_threshold_zero_disables_split(self):
        _seed_split_eligible(self.root, "pkg-a", "components")
        result = _diff_concern(
            "pkg-a", "components", self.root, self.docs, split_threshold_kb=0
        )
        self.assertNotIn("split", result)

    def test_child_status_new_when_no_child_doc(self):
        # Fresh testbed: zero child docs exist anywhere → every sub_concern
        # entry must report status "new" (not "missing", not "" — the
        # _classify_status code path with prior_stamp=None must return "new").
        _seed_split_eligible(self.root, "pkg-a", "components")
        result = _diff_concern(
            "pkg-a", "components", self.root, self.docs, split_threshold_kb=5
        )
        for sc in result["sub_concerns"]:
            self.assertEqual(sc["status"], "new", msg=sc)
            self.assertIsNone(sc["prior_stamp"])

    def test_child_status_unchanged_when_doc_stamp_matches(self):
        _seed_split_eligible(self.root, "pkg-a", "components")
        # First pass to capture the per-child stamps
        first = _diff_concern(
            "pkg-a", "components", self.root, self.docs, split_threshold_kb=5
        )
        # Plant matching child docs for alpha + beta + gamma
        for sc in first["sub_concerns"]:
            _write_doc(self.docs, "pkg-a", "components", sc["source_stamp"], sub=sc["concern"])
        # Plant matching parent doc
        _write_doc(self.docs, "pkg-a", "components", first["source_stamp"])
        result = _diff_concern(
            "pkg-a", "components", self.root, self.docs, split_threshold_kb=5
        )
        for sc in result["sub_concerns"]:
            self.assertEqual(sc["status"], "unchanged", msg=sc)
        self.assertEqual(result["status"], "unchanged")

    def test_child_status_changed_when_one_child_differs(self):
        _seed_split_eligible(self.root, "pkg-a", "components")
        first = _diff_concern(
            "pkg-a", "components", self.root, self.docs, split_threshold_kb=5
        )
        # Plant ALL with matching stamps
        for sc in first["sub_concerns"]:
            _write_doc(self.docs, "pkg-a", "components", sc["source_stamp"], sub=sc["concern"])
        _write_doc(self.docs, "pkg-a", "components", first["source_stamp"])
        # Touch alpha's file → its stamp flips
        target = self.root / "pkg-a" / "src" / "components" / "alpha" / "f.ts"
        target.write_text(target.read_text() + "\n// extra\n", encoding="utf-8")
        result = _diff_concern(
            "pkg-a", "components", self.root, self.docs, split_threshold_kb=5
        )
        sc_alpha = next(sc for sc in result["sub_concerns"] if sc["concern"] == "alpha")
        sc_beta = next(sc for sc in result["sub_concerns"] if sc["concern"] == "beta")
        self.assertEqual(sc_alpha["status"], "changed")
        self.assertEqual(sc_beta["status"], "unchanged")
        self.assertEqual(result["status"], "changed")

    def test_parent_status_changed_when_agg_stamp_differs(self):
        _seed_split_eligible(self.root, "pkg-a", "components")
        first = _diff_concern(
            "pkg-a", "components", self.root, self.docs, split_threshold_kb=5
        )
        # Plant child docs matching, but parent doc with stale stamp
        for sc in first["sub_concerns"]:
            _write_doc(self.docs, "pkg-a", "components", sc["source_stamp"], sub=sc["concern"])
        _write_doc(self.docs, "pkg-a", "components", "deadbeefdeadbeef")
        result = _diff_concern(
            "pkg-a", "components", self.root, self.docs, split_threshold_kb=5
        )
        # Children unchanged, but parent stamp diff → parent "changed"
        for sc in result["sub_concerns"]:
            self.assertEqual(sc["status"], "unchanged")
        self.assertEqual(result["status"], "changed")
        self.assertEqual(result["prior_stamp"], "deadbeefdeadbeef")

    def test_parent_status_new_when_no_parent_doc(self):
        _seed_split_eligible(self.root, "pkg-a", "components")
        first = _diff_concern(
            "pkg-a", "components", self.root, self.docs, split_threshold_kb=5
        )
        # Plant only child docs, no parent doc
        for sc in first["sub_concerns"]:
            _write_doc(self.docs, "pkg-a", "components", sc["source_stamp"], sub=sc["concern"])
        result = _diff_concern(
            "pkg-a", "components", self.root, self.docs, split_threshold_kb=5
        )
        self.assertEqual(result["status"], "new")
        self.assertIsNone(result["prior_stamp"])

    def test_split_with_all_filtered_subdirs_falls_back_to_single_batch(self):
        # Edge case (Finding 2 from python-reviewer): ≥2 immediate dirs +
        # total span > threshold, but ALL surviving files are loose (every
        # subdir's contents got filtered by trivial-leaf rule). The split
        # branch must NOT emit `split:true, sub_concerns:[]` — fall back
        # to single-batch instead.
        base = self.root / "pkg-a" / "src" / "components"
        # Two immediate dirs, but each contains only filtered content.
        for sub in ("alpha", "beta"):
            nm = base / sub / "node_modules"
            nm.mkdir(parents=True)
            (nm / "junk.ts").write_text("filtered\n", encoding="utf-8")
        # One loose file at concern root big enough to push total span
        # past the test threshold.
        _make_big_file(base / "big.ts", kb=10)
        result = _diff_concern(
            "pkg-a", "components", self.root, self.docs, split_threshold_kb=3
        )
        self.assertNotIn("split", result)
        self.assertNotIn("sub_concerns", result)
        # Single-batch path must populate the standard fields.
        self.assertRegex(result["source_stamp"], r"^[0-9a-f]{16}$")
        self.assertEqual(result["status"], "new")

    def test_aggregate_stamp_deterministic(self):
        _seed_split_eligible(self.root, "pkg-a", "components")
        a = _diff_concern("pkg-a", "components", self.root, self.docs, split_threshold_kb=5)
        b = _diff_concern("pkg-a", "components", self.root, self.docs, split_threshold_kb=5)
        self.assertEqual(a["source_stamp"], b["source_stamp"])

    def test_cross_helper_aggregate_stamp_matches_concern_input(self):
        """Preflight's aggregate stamp must equal concern-input's for same content."""
        _seed_split_eligible(self.root, "pkg-a", "components")
        # Preflight-side
        pf = _diff_concern(
            "pkg-a", "components", self.root, self.docs, split_threshold_kb=5
        )
        # concern-input side: invoke as subprocess-equivalent (direct cmd call)
        devforge = self.root / ".devforge"
        devforge.mkdir(parents=True, exist_ok=True)
        ci_args = argparse.Namespace(
            devforge_dir=str(devforge),
            package="pkg-a",
            concern="components",
            split_threshold_kb=5,
        )
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cmd_concern_input(ci_args)
        self.assertEqual(code, 0, msg=err.getvalue())
        ci_payload = json.loads(out.getvalue())
        self.assertTrue(ci_payload.get("split"))
        self.assertEqual(pf["source_stamp"], ci_payload["source_stamp"])
        # Per-child stamps also match
        pf_children = {sc["concern"]: sc["source_stamp"] for sc in pf["sub_concerns"]}
        ci_children = {sc["concern"]: sc["source_stamp"] for sc in ci_payload["sub_concerns"]}
        self.assertEqual(pf_children, ci_children)


class CmdPreflightSplitCountsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"

    def _run(self, args: argparse.Namespace):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cmd_preflight(args)
        return code, out.getvalue(), err.getvalue()

    def test_subconcern_counts_populated_when_split(self):
        _seed_split_eligible(self.root, "pkg-a", "components")
        _write_index_json(self.devforge, packages={"pkg-a": {}})
        args = argparse.Namespace(
            devforge_dir=str(self.devforge),
            skip_vue_extract=True,
            skip_index=True,
            split_threshold_kb=5,
        )
        code, out, err = self._run(args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        # One concern entry, with split:true
        self.assertEqual(len(payload["concerns"]), 1)
        self.assertTrue(payload["concerns"][0].get("split"))
        # Subconcern counts: 3 new (no child docs exist yet)
        self.assertIn("subconcern_counts", payload)
        self.assertEqual(payload["subconcern_counts"]["new"], 3)
        self.assertEqual(payload["subconcern_counts"]["changed"], 0)
        self.assertEqual(payload["subconcern_counts"]["unchanged"], 0)

    def test_subconcern_counts_zero_when_no_split(self):
        # Small concern → no split → subconcern_counts all zero
        (self.root / "pkg-a" / "src" / "order").mkdir(parents=True)
        (self.root / "pkg-a" / "src" / "order" / "x.ts").write_text(
            "export const x = 1;\n", encoding="utf-8"
        )
        _write_index_json(self.devforge, packages={"pkg-a": {}})
        args = argparse.Namespace(
            devforge_dir=str(self.devforge),
            skip_vue_extract=True,
            skip_index=True,
            split_threshold_kb=50,  # default; small concern won't split
        )
        code, out, err = self._run(args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertNotIn("split", payload["concerns"][0])
        self.assertEqual(payload["subconcern_counts"]["new"], 0)
        self.assertEqual(payload["subconcern_counts"]["changed"], 0)
        self.assertEqual(payload["subconcern_counts"]["unchanged"], 0)

    def test_threshold_kb_zero_disables_split_in_cmd(self):
        _seed_split_eligible(self.root, "pkg-a", "components")
        _write_index_json(self.devforge, packages={"pkg-a": {}})
        args = argparse.Namespace(
            devforge_dir=str(self.devforge),
            skip_vue_extract=True,
            skip_index=True,
            split_threshold_kb=0,
        )
        code, out, err = self._run(args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        # No concern is split
        for c in payload["concerns"]:
            self.assertNotIn("split", c)


if __name__ == "__main__":
    unittest.main()
