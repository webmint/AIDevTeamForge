"""Tests for _concern_input.py — F.2 concern-input helper.

Cases:
  1.  _build_tree: 5 files in 2 subdirs renders correct ASCII tree
  2.  _build_tree: directories grouped above leaves at each level
  3.  _build_tree: subfolder header line correctly formatted
  4.  _extract_comment_rich_span: file ≤30 lines returns full content
  5.  _extract_comment_rich_span: top 30 + TODO context window after
  6.  _extract_comment_rich_span: overlapping windows merge with no `...`
  7.  _extract_comment_rich_span: non-adjacent windows separated by `...`
  8.  _extract_comment_rich_span: max_bytes truncation marker appended
  9.  _extract_comment_rich_span: hazard markers FIXME/HACK/WARNING/XXX recognized
 10.  _build_spans_and_stamp: identical inputs → identical stamp
 11.  _build_spans_and_stamp: one file content changes → stamp changes
 12.  _build_spans_and_stamp: file-order does not affect stamp
 13.  _build_spans_and_stamp: unreadable file recorded but doesn't crash
 14.  cmd_concern_input: package not in index.json → exit 2
 15.  cmd_concern_input: concern subfolder empty → exit 2
 16.  cmd_concern_input: trivial-leaf paths excluded from tree + spans
 17.  cmd_concern_input: end-to-end on synthetic project → valid batch JSON

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
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

from _generate_docs._concern_input import (  # noqa: E402
    _build_spans_and_stamp,
    _build_tree,
    _extract_comment_rich_span,
    cmd_concern_input,
)


def _make_args(devforge_dir: Path, package: str, concern: str) -> argparse.Namespace:
    devforge_dir.mkdir(parents=True, exist_ok=True)  # helper expects it to exist
    return argparse.Namespace(
        devforge_dir=str(devforge_dir),
        package=package,
        concern=concern,
    )


class BuildTreeTests(unittest.TestCase):
    def test_five_files_two_subdirs(self):
        files = [
            "src/order/OrderFooter.vue",
            "src/order/OrderLines.vue",
            "src/order/orderLine/OrderLine.vue",
            "src/order/orderLine/OrderLinePrice.vue",
            "src/order/helpers/data.ts",
        ]
        tree = _build_tree(files, "src/order/")
        # Header line first.
        self.assertTrue(tree.startswith("src/order/\n"))
        # All 5 leaves present.
        for leaf in (
            "OrderFooter.vue",
            "OrderLines.vue",
            "OrderLine.vue",
            "OrderLinePrice.vue",
            "data.ts",
        ):
            self.assertIn(leaf, tree)
        # Two subdirs visible.
        self.assertIn("orderLine", tree)
        self.assertIn("helpers", tree)

    def test_directories_grouped_above_leaves(self):
        files = [
            "src/order/zfile.ts",
            "src/order/aaa/inside.ts",
        ]
        tree = _build_tree(files, "src/order/")
        # 'aaa' subdir line index < 'zfile.ts' leaf line index
        idx_aaa = tree.index("aaa")
        idx_zfile = tree.index("zfile.ts")
        self.assertLess(idx_aaa, idx_zfile)

    def test_subfolder_header_strips_trailing_slash(self):
        tree = _build_tree(["src/order/x.ts"], "src/order/")
        self.assertEqual(tree.split("\n", 1)[0], "src/order/")


class ExtractSpanTests(unittest.TestCase):
    def test_short_file_returns_full_content(self):
        content = "\n".join(f"line {i}" for i in range(1, 11))  # 10 lines
        span = _extract_comment_rich_span(content, 1024)
        self.assertIn("   1: line 1", span)
        self.assertIn("  10: line 10", span)

    def test_top_plus_todo_context_window(self):
        # Top is lines 1-30. Hazard at line 40 → window 38-42 (2-line context).
        # Gap between line 30 and line 38 is non-contiguous → `...` separator.
        lines = [f"top {i}" for i in range(1, 31)]  # lines 1-30
        lines.extend([f"filler {i}" for i in range(1, 8)])  # lines 31-37
        lines.append("// TODO fix me")  # line 38
        lines.extend(["aft 1", "aft 2", "aft 3"])  # lines 39-41
        content = "\n".join(lines)
        span = _extract_comment_rich_span(content, 4096)
        self.assertIn("top 1", span)
        self.assertIn("top 30", span)
        self.assertIn("TODO fix me", span)
        # Context window before TODO (lines 36-37 within 2-line context)
        self.assertIn("filler 6", span)
        self.assertIn("filler 7", span)
        # Context window after TODO (lines 39-40 within 2-line context)
        self.assertIn("aft 1", span)
        # Gap between top window and hazard window non-contiguous → `...`
        self.assertIn("...", span)
        # filler 1 (line 31) is past top + before hazard window → NOT in span
        self.assertNotIn("filler 1\n", span)

    def test_overlapping_windows_merge_no_ellipsis(self):
        # Hazard at line 31 — context window touches top of file (top is 1-30).
        lines = [f"top {i}" for i in range(1, 31)]
        lines.append("// TODO at 31")  # line 31
        lines.extend(["a", "b", "c"])
        content = "\n".join(lines)
        span = _extract_comment_rich_span(content, 4096)
        # Top window 1-30 and hazard window 29-33 overlap → no separator
        self.assertNotIn("...", span)

    def test_non_adjacent_windows_separated_by_ellipsis(self):
        lines = [f"top {i}" for i in range(1, 31)]
        lines.extend([f"middle {i}" for i in range(1, 50)])  # 31-79
        lines.append("// TODO late")  # line 80
        content = "\n".join(lines)
        span = _extract_comment_rich_span(content, 4096)
        # Top window 1-30 and hazard window 78-82 are non-adjacent → separator
        self.assertIn("...", span)

    def test_truncation_marker_when_over_max_bytes(self):
        big = "\n".join("X" * 120 for _ in range(100))  # ~12 KB
        span = _extract_comment_rich_span(big, 1024)
        self.assertLessEqual(len(span.encode("utf-8")), 1024 + 64)
        self.assertIn("<file span truncated>", span)

    def test_recognises_all_hazard_markers(self):
        markers = ["FIXME", "HACK", "WARNING", "XXX"]
        for m in markers:
            content = "\n".join([f"top {i}" for i in range(1, 31)] + [f"// {m} marker"])
            span = _extract_comment_rich_span(content, 4096)
            self.assertIn(m, span, f"marker {m!r} not surfaced in span")


class BuildSpansAndStampTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        (self.root / "a.ts").write_text("export const a = 1;\n", encoding="utf-8")
        (self.root / "b.ts").write_text("export const b = 2;\n", encoding="utf-8")

    def test_identical_inputs_same_stamp(self):
        records1, _h1, stamp1 = _build_spans_and_stamp(["a.ts", "b.ts"], self.root)
        records2, _h2, stamp2 = _build_spans_and_stamp(["a.ts", "b.ts"], self.root)
        self.assertEqual(stamp1, stamp2)
        self.assertEqual(len(records1), 2)
        self.assertEqual(len(records2), 2)

    def test_content_change_changes_stamp(self):
        _, _h1, stamp_before = _build_spans_and_stamp(["a.ts", "b.ts"], self.root)
        (self.root / "a.ts").write_text("export const a = 999;\n", encoding="utf-8")
        _, _h2, stamp_after = _build_spans_and_stamp(["a.ts", "b.ts"], self.root)
        self.assertNotEqual(stamp_before, stamp_after)

    def test_input_order_does_not_affect_stamp(self):
        _, _h1, stamp_a = _build_spans_and_stamp(["a.ts", "b.ts"], self.root)
        _, _h2, stamp_b = _build_spans_and_stamp(["b.ts", "a.ts"], self.root)
        self.assertEqual(stamp_a, stamp_b)

    def test_unreadable_file_recorded_does_not_crash(self):
        records, hashes, stamp = _build_spans_and_stamp(["a.ts", "missing.ts"], self.root)
        self.assertEqual(len(records), 2)
        missing = next(r for r in records if r["path"] == "missing.ts")
        self.assertEqual(missing["comment_rich_span"], "<unreadable>")
        self.assertTrue(stamp)
        # Sanity-check hashes shape
        self.assertEqual(len(hashes), 2)
        self.assertTrue(all(len(h) == 2 for h in hashes))


class CmdConcernInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.devforge = self.root / ".devforge"

    def _run(self, args: argparse.Namespace):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cmd_concern_input(args)
        return code, out.getvalue(), err.getvalue()

    def test_subfolder_missing_returns_2(self):
        args = _make_args(self.devforge, "pkg-a", "no-such-concern")
        code, _, err = self._run(args)
        self.assertEqual(code, 2)
        self.assertIn("no-such-concern", err)

    def test_subfolder_empty_returns_2(self):
        # Subfolder exists but contains only trivial-leaf paths — should fail.
        nm = self.root / "pkg-a" / "src" / "order" / "node_modules" / "junk"
        nm.mkdir(parents=True)
        (nm / "ignored.ts").write_text("x\n", encoding="utf-8")
        args = _make_args(self.devforge, "pkg-a", "order")
        code, _, err = self._run(args)
        self.assertEqual(code, 2)
        self.assertIn("order", err)

    def test_trivial_leaf_paths_excluded(self):
        src = self.root / "pkg-a" / "src" / "order"
        src.mkdir(parents=True)
        (src / "Real.ts").write_text("export const r = 1;\n", encoding="utf-8")
        nm = src / "node_modules" / "junk"
        nm.mkdir(parents=True)
        (nm / "ignored.ts").write_text("ignored content\n", encoding="utf-8")
        args = _make_args(self.devforge, "pkg-a", "order")
        code, out, _ = self._run(args)
        self.assertEqual(code, 0)
        payload = json.loads(out)
        paths = [f["path"] for f in payload["files"]]
        self.assertIn("pkg-a/src/order/Real.ts", paths)
        self.assertNotIn("pkg-a/src/order/node_modules/junk/ignored.ts", paths)
        self.assertNotIn("node_modules", payload["tree_text"])

    def test_end_to_end_synthetic_project(self):
        src = self.root / "pkg-a" / "src" / "order"
        src.mkdir(parents=True)
        (src / "OrderFooter.vue").write_text(
            "<template>\n  <div>{{ msg }}</div>\n</template>\n"
            "<script setup>\nimport { ref } from 'vue';\n"
            "// TODO refactor this\nconst msg = ref('hi');\n</script>\n",
            encoding="utf-8",
        )
        (src / "OrderLines.vue").write_text("<template></template>\n", encoding="utf-8")
        (src / "helpers").mkdir()
        (src / "helpers" / "data.ts").write_text(
            "export const cfg = {};\n", encoding="utf-8"
        )
        args = _make_args(self.devforge, "pkg-a", "order")
        code, out, _ = self._run(args)
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["concern"], "order")
        self.assertEqual(payload["package"], "pkg-a")
        self.assertEqual(payload["subfolder"], "pkg-a/src/order/")
        self.assertIn("OrderFooter.vue", payload["tree_text"])
        self.assertIn("helpers", payload["tree_text"])
        self.assertEqual(len(payload["files"]), 3)
        footer = next(f for f in payload["files"] if f["path"].endswith("OrderFooter.vue"))
        self.assertIn("TODO refactor this", footer["comment_rich_span"])
        self.assertIn("import { ref }", footer["comment_rich_span"])
        self.assertRegex(payload["source_stamp"], r"^[0-9a-f]{16}$")

    def test_single_root_pkg_dot_tree_renders_children(self):
        # FIX 2 (non-split path): pkg="." must NOT produce a "." component in
        # subfolder_prefix. PurePosixPath normalization: "src/main/" (no leading
        # "./"). This ensures _build_tree's startswith match finds the files and
        # renders child entries (not just the bare header line).
        src = self.root / "src" / "main"
        src.mkdir(parents=True)
        (src / "app.ts").write_text("export function main() {}\n", encoding="utf-8")
        (src / "helpers").mkdir()
        (src / "helpers" / "util.ts").write_text("export const x = 1;\n", encoding="utf-8")
        args = argparse.Namespace(
            devforge_dir=str(self.devforge),
            package=".",
            concern="main",
            split_threshold_kb=50,
        )
        self.devforge.mkdir(parents=True, exist_ok=True)
        code, out, err = self._run(args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertEqual(payload["concern"], "main")
        self.assertEqual(payload["package"], ".")
        # subfolder must be "src/main/" not "./src/main/"
        self.assertEqual(payload["subfolder"], "src/main/")
        # tree_text must have child entries, not just the header
        tree = payload["tree_text"]
        self.assertIn("app.ts", tree)
        self.assertIn("helpers", tree)
        self.assertIn("util.ts", tree)
        # files paths must be "src/main/..." not "./src/main/..."
        paths = {f["path"] for f in payload["files"]}
        self.assertIn("src/main/app.ts", paths)
        self.assertIn("src/main/helpers/util.ts", paths)
        self.assertRegex(payload["source_stamp"], r"^[0-9a-f]{16}$")

    def test_single_root_pkg_dot_split_yields_nonempty_sub_concerns(self):
        # FIX 2 (split path): pkg="." with split-eligible content must produce
        # non-empty sub_concerns. The bug was that "./src/components/" as prefix
        # matched zero files from the walk (stored as "src/components/alpha/f.ts"),
        # so every child group was empty and the defensive fallback collapsed it
        # to single-batch (emitting `split:true, sub_concerns:[]` before the fix).
        import sys
        # Import _make_big_file inline so this test is self-contained.
        def _make_big_file(path: Path, kb: int) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            line = "// TODO real content: " + ("X" * 100) + "\n"
            n = max(1, (kb * 1024) // len(line.encode("utf-8")) + 1)
            path.write_text(line * n, encoding="utf-8")

        base = self.root / "src" / "components"
        for child in ("alpha", "beta"):
            _make_big_file(base / child / "f.ts", kb=25)
        args = argparse.Namespace(
            devforge_dir=str(self.devforge),
            package=".",
            concern="components",
            split_threshold_kb=5,
        )
        self.devforge.mkdir(parents=True, exist_ok=True)
        code, out, err = self._run(args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertTrue(payload.get("split"), msg=f"expected split:true, got {payload}")
        self.assertEqual(len(payload["sub_concerns"]), 2)
        names = sorted(sc["concern"] for sc in payload["sub_concerns"])
        self.assertEqual(names, ["alpha", "beta"])
        # subfolder in parent_meta tree must not have leading "./"
        self.assertEqual(payload["subfolder"], "src/components/")
        # Each sub_concern subfolder also must not have leading "./"
        for sc in payload["sub_concerns"]:
            self.assertFalse(sc["subfolder"].startswith("./"), msg=sc["subfolder"])
            self.assertTrue(sc["subfolder"].startswith("src/components/"), msg=sc["subfolder"])
        self.assertRegex(payload["source_stamp"], r"^[0-9a-f]{16}$")


if __name__ == "__main__":
    unittest.main()
