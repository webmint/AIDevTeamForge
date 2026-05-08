"""Tests for _concern_input.py split-dispatch logic — Plan F 3a.

Cases:
  1.  Concern with 3 child dirs + over-threshold total → split:true with 3 sub_concerns
  2.  Concern with 5 small files, all under threshold → split:false (single-batch)
  3.  Concern over threshold but only 1 subdir → split:false (need ≥2 children)
  4.  --split-threshold-kb 0 disables split (always single-batch)
  5.  --split-threshold-kb 1 forces split for any non-trivial input
  6.  Aggregate stamp: change one sub_concern's file → parent stamp flips
  7.  Aggregate stamp: identical input → identical parent stamp
  8.  Loose files at concern root listed in parent_meta.loose_files when split fires
  9.  Each sub_concern has its own source_stamp (subset of files, not aggregate)
 10.  Files re-grouped by immediate-dir; sibling sub_concerns are disjoint
 11.  Trivial-leaf dirs (node_modules) excluded from immediate_dirs enumeration
 12.  Truncated flag on single-batch single-child over-threshold case
 13.  Each sub_concern's tree_text has the child subfolder header
 14.  Single-batch shape preserved for backward-compat with default threshold

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
    _DEFAULT_SPLIT_THRESHOLD_KB,
    _enumerate_immediate_dirs,
    _partition_files_by_immediate_dir,
    cmd_concern_input,
)


def _make_args(
    devforge_dir: Path,
    package: str,
    concern: str,
    split_threshold_kb: int = _DEFAULT_SPLIT_THRESHOLD_KB,
) -> argparse.Namespace:
    devforge_dir.mkdir(parents=True, exist_ok=True)
    return argparse.Namespace(
        devforge_dir=str(devforge_dir),
        package=package,
        concern=concern,
        split_threshold_kb=split_threshold_kb,
    )


def _run_cmd(args: argparse.Namespace):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cmd_concern_input(args)
    return code, out.getvalue(), err.getvalue()


def _make_big_file(path: Path, kb: int) -> None:
    """Write `kb` KB of content with TODO markers so spans don't compress to nothing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = "// TODO real content here padded out: " + ("X" * 100) + "\n"
    bytes_per_line = len(line.encode("utf-8"))
    n_lines = max(1, (kb * 1024) // bytes_per_line + 1)
    path.write_text(line * n_lines, encoding="utf-8")


class EnumerateImmediateDirsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_immediate_dirs_alphabetical(self):
        base = self.root / "concern"
        for name in ("zeta", "alpha", "mu"):
            (base / name).mkdir(parents=True)
        names = _enumerate_immediate_dirs(base, self.root)
        self.assertEqual(names, ["alpha", "mu", "zeta"])

    def test_immediate_dirs_excludes_trivial(self):
        base = self.root / "concern"
        for name in ("real", "node_modules", "dist"):
            (base / name).mkdir(parents=True)
        names = _enumerate_immediate_dirs(base, self.root)
        self.assertEqual(names, ["real"])

    def test_immediate_dirs_files_not_listed(self):
        base = self.root / "concern"
        base.mkdir()
        (base / "loose.ts").write_text("x\n", encoding="utf-8")
        (base / "child").mkdir()
        names = _enumerate_immediate_dirs(base, self.root)
        self.assertEqual(names, ["child"])

    def test_immediate_dirs_missing_subfolder(self):
        names = _enumerate_immediate_dirs(self.root / "nope", self.root)
        self.assertEqual(names, [])


class PartitionFilesTests(unittest.TestCase):
    def test_groups_by_first_dir(self):
        files = [
            "pkg/src/c/a/x.ts",
            "pkg/src/c/a/y.ts",
            "pkg/src/c/b/z.ts",
            "pkg/src/c/loose.ts",
        ]
        groups, loose = _partition_files_by_immediate_dir(
            files, "pkg/src/c/", ["a", "b"]
        )
        self.assertEqual(sorted(groups["a"]), ["pkg/src/c/a/x.ts", "pkg/src/c/a/y.ts"])
        self.assertEqual(sorted(groups["b"]), ["pkg/src/c/b/z.ts"])
        self.assertEqual(loose, ["pkg/src/c/loose.ts"])

    def test_files_outside_subfolder_skipped(self):
        files = ["pkg/src/c/a/x.ts", "pkg/src/d/y.ts"]
        groups, loose = _partition_files_by_immediate_dir(
            files, "pkg/src/c/", ["a"]
        )
        self.assertEqual(groups["a"], ["pkg/src/c/a/x.ts"])
        self.assertEqual(loose, [])


class CmdConcernInputSplitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.devforge = self.root / ".devforge"

    def _seed_three_children(self, total_kb_per_child: int = 25):
        """Concern with 3 child dirs, each with one big file."""
        base = self.root / "pkg-a" / "src" / "components"
        for child in ("alpha", "beta", "gamma"):
            _make_big_file(base / child / "file.ts", kb=total_kb_per_child)

    def test_split_fires_on_three_children_over_threshold(self):
        # Each child has ~25 KB. Top 30 lines → ~4 KB span each. 3 children × 4 KB
        # = 12 KB total span. Threshold 5 KB → triggers split.
        self._seed_three_children(total_kb_per_child=25)
        args = _make_args(self.devforge, "pkg-a", "components", split_threshold_kb=5)
        code, out, err = _run_cmd(args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertTrue(payload.get("split"), msg=f"expected split:true, got {payload}")
        self.assertEqual(len(payload["sub_concerns"]), 3)
        names = sorted(sc["concern"] for sc in payload["sub_concerns"])
        self.assertEqual(names, ["alpha", "beta", "gamma"])
        # Each sub_concern records its parent
        for sc in payload["sub_concerns"]:
            self.assertEqual(sc["parent_concern"], "components")
            self.assertEqual(sc["package"], "pkg-a")

    def test_split_does_not_fire_under_threshold(self):
        # 3 children but tiny content → total well under default 50 KB
        base = self.root / "pkg-a" / "src" / "components"
        for child in ("alpha", "beta", "gamma"):
            (base / child).mkdir(parents=True)
            (base / child / "f.ts").write_text("export const x = 1;\n", encoding="utf-8")
        args = _make_args(self.devforge, "pkg-a", "components")  # default 50
        code, out, err = _run_cmd(args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertNotIn("split", payload)
        self.assertIn("files", payload)

    def test_split_disabled_with_threshold_zero(self):
        self._seed_three_children(total_kb_per_child=25)
        args = _make_args(self.devforge, "pkg-a", "components", split_threshold_kb=0)
        code, out, err = _run_cmd(args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertNotIn("split", payload)
        self.assertIn("files", payload)

    def test_force_split_with_tiny_threshold(self):
        self._seed_three_children(total_kb_per_child=2)
        args = _make_args(self.devforge, "pkg-a", "components", split_threshold_kb=1)
        code, out, err = _run_cmd(args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertTrue(payload.get("split"))

    def test_single_child_over_threshold_does_not_split(self):
        # 5 small files in ONE subdir. Each yields ~4 KB span (top-30 lines
        # of padded content). Total ~20 KB > 5 KB threshold. Only 1 subdir
        # → must NOT split despite total exceeding threshold.
        base = self.root / "pkg-a" / "src" / "components" / "only-child"
        for i in range(5):
            _make_big_file(base / f"f{i}.ts", kb=10)
        args = _make_args(self.devforge, "pkg-a", "components", split_threshold_kb=5)
        code, out, err = _run_cmd(args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertNotIn("split", payload, msg="single-child concern must not split")
        # Single-batch shape preserved.
        self.assertIn("files", payload)
        self.assertEqual(len(payload["files"]), 5)

    def test_aggregate_stamp_changes_with_child_content(self):
        self._seed_three_children(total_kb_per_child=25)
        args = _make_args(self.devforge, "pkg-a", "components", split_threshold_kb=5)
        code, out, _ = _run_cmd(args)
        payload_before = json.loads(out)
        stamp_before = payload_before["source_stamp"]
        # Change one child's content
        target = self.root / "pkg-a" / "src" / "components" / "alpha" / "file.ts"
        target.write_text(target.read_text() + "\n// extra line\n", encoding="utf-8")
        code, out, _ = _run_cmd(args)
        payload_after = json.loads(out)
        self.assertNotEqual(stamp_before, payload_after["source_stamp"])
        # The unchanged sub_concerns retain their stamps
        sc_alpha_before = next(s for s in payload_before["sub_concerns"] if s["concern"] == "alpha")
        sc_alpha_after = next(s for s in payload_after["sub_concerns"] if s["concern"] == "alpha")
        self.assertNotEqual(sc_alpha_before["source_stamp"], sc_alpha_after["source_stamp"])
        sc_beta_before = next(s for s in payload_before["sub_concerns"] if s["concern"] == "beta")
        sc_beta_after = next(s for s in payload_after["sub_concerns"] if s["concern"] == "beta")
        self.assertEqual(sc_beta_before["source_stamp"], sc_beta_after["source_stamp"])

    def test_aggregate_stamp_deterministic(self):
        self._seed_three_children(total_kb_per_child=10)
        args = _make_args(self.devforge, "pkg-a", "components", split_threshold_kb=5)
        code, out1, _ = _run_cmd(args)
        code, out2, _ = _run_cmd(args)
        p1 = json.loads(out1)
        p2 = json.loads(out2)
        self.assertEqual(p1["source_stamp"], p2["source_stamp"])

    def test_loose_files_listed_in_parent_meta(self):
        base = self.root / "pkg-a" / "src" / "components"
        # Two children + one loose file at concern root
        _make_big_file(base / "alpha" / "f.ts", kb=10)
        _make_big_file(base / "beta" / "f.ts", kb=10)
        (base / "README.md").write_text("# components root\n", encoding="utf-8")
        args = _make_args(self.devforge, "pkg-a", "components", split_threshold_kb=1)
        code, out, _ = _run_cmd(args)
        payload = json.loads(out)
        self.assertTrue(payload.get("split"))
        loose = payload["parent_meta"]["loose_files"]
        self.assertEqual(loose, ["pkg-a/src/components/README.md"])

    def test_sub_concerns_disjoint_groups(self):
        base = self.root / "pkg-a" / "src" / "components"
        _make_big_file(base / "alpha" / "x.ts", kb=10)
        _make_big_file(base / "alpha" / "y.ts", kb=10)
        _make_big_file(base / "beta" / "z.ts", kb=10)
        args = _make_args(self.devforge, "pkg-a", "components", split_threshold_kb=1)
        code, out, _ = _run_cmd(args)
        payload = json.loads(out)
        sc_alpha = next(s for s in payload["sub_concerns"] if s["concern"] == "alpha")
        sc_beta = next(s for s in payload["sub_concerns"] if s["concern"] == "beta")
        alpha_paths = {f["path"] for f in sc_alpha["files"]}
        beta_paths = {f["path"] for f in sc_beta["files"]}
        self.assertEqual(
            alpha_paths,
            {"pkg-a/src/components/alpha/x.ts", "pkg-a/src/components/alpha/y.ts"},
        )
        self.assertEqual(beta_paths, {"pkg-a/src/components/beta/z.ts"})
        self.assertEqual(alpha_paths & beta_paths, set())

    def test_sub_concern_stamp_independent(self):
        self._seed_three_children(total_kb_per_child=10)
        args = _make_args(self.devforge, "pkg-a", "components", split_threshold_kb=1)
        code, out, _ = _run_cmd(args)
        payload = json.loads(out)
        sub_stamps = [sc["source_stamp"] for sc in payload["sub_concerns"]]
        # All distinct (children have different paths)
        self.assertEqual(len(set(sub_stamps)), len(sub_stamps))
        # Each is the expected hex format
        for s in sub_stamps:
            self.assertRegex(s, r"^[0-9a-f]{16}$")
        # Aggregate stamp also valid format, distinct from any sub stamp
        self.assertRegex(payload["source_stamp"], r"^[0-9a-f]{16}$")
        self.assertNotIn(payload["source_stamp"], sub_stamps)

    def test_trivial_dirs_excluded_from_immediate_dirs(self):
        base = self.root / "pkg-a" / "src" / "components"
        _make_big_file(base / "real-a" / "f.ts", kb=10)
        _make_big_file(base / "real-b" / "f.ts", kb=10)
        # node_modules at concern root — must not become a sub_concern
        (base / "node_modules" / "ignored").mkdir(parents=True)
        (base / "node_modules" / "ignored" / "junk.ts").write_text("x\n", encoding="utf-8")
        args = _make_args(self.devforge, "pkg-a", "components", split_threshold_kb=1)
        code, out, _ = _run_cmd(args)
        payload = json.loads(out)
        self.assertTrue(payload.get("split"))
        names = [sc["concern"] for sc in payload["sub_concerns"]]
        self.assertEqual(sorted(names), ["real-a", "real-b"])
        self.assertNotIn("node_modules", names)

    def test_subconcern_tree_text_has_child_header(self):
        self._seed_three_children(total_kb_per_child=10)
        args = _make_args(self.devforge, "pkg-a", "components", split_threshold_kb=1)
        code, out, _ = _run_cmd(args)
        payload = json.loads(out)
        sc_alpha = next(s for s in payload["sub_concerns"] if s["concern"] == "alpha")
        # First line is the child subfolder header
        self.assertTrue(sc_alpha["tree_text"].startswith("pkg-a/src/components/alpha/\n"))

    def test_single_child_with_loose_files_does_not_split(self):
        # Single subdir + loose file at concern root → only 1 immediate dir
        # → must not split (loose file is NOT counted as a second child).
        base = self.root / "pkg-a" / "src" / "components"
        for i in range(5):
            _make_big_file(base / "only-child" / f"f{i}.ts", kb=10)
        (base / "loose.ts").write_text(
            "// loose file at concern root\nexport const x = 1;\n",
            encoding="utf-8",
        )
        args = _make_args(self.devforge, "pkg-a", "components", split_threshold_kb=5)
        code, out, err = _run_cmd(args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertNotIn("split", payload)
        paths = {f["path"] for f in payload["files"]}
        self.assertIn("pkg-a/src/components/loose.ts", paths)
        self.assertEqual(len(payload["files"]), 6)  # 5 subdir files + 1 loose

    def test_stamp_equivalence_split_enabled_vs_disabled_when_no_split(self):
        # Same content, threshold high enough that no split fires, vs
        # threshold=0 disabling split entirely. Both single-batch paths
        # MUST produce the same source_stamp for equivalent input.
        base = self.root / "pkg-a" / "src" / "components"
        for child in ("a", "b", "c"):
            (base / child).mkdir(parents=True)
            (base / child / "f.ts").write_text(
                f"export const {child} = 1;\n", encoding="utf-8"
            )
        args_default = _make_args(self.devforge, "pkg-a", "components", split_threshold_kb=50)
        args_disabled = _make_args(self.devforge, "pkg-a", "components", split_threshold_kb=0)
        _, out1, _ = _run_cmd(args_default)
        _, out2, _ = _run_cmd(args_disabled)
        p1 = json.loads(out1)
        p2 = json.loads(out2)
        self.assertNotIn("split", p1)
        self.assertNotIn("split", p2)
        self.assertEqual(
            p1["source_stamp"], p2["source_stamp"],
            "single-batch stamp must match between split-enabled-but-no-split "
            "and split-disabled paths",
        )

    def test_default_threshold_preserves_legacy_shape(self):
        # 3 children with very small content → under default 50 KB → single-batch
        base = self.root / "pkg-a" / "src" / "components"
        for child in ("a", "b", "c"):
            (base / child).mkdir(parents=True)
            (base / child / "f.ts").write_text("export const x = 1;\n", encoding="utf-8")
        # No split_threshold_kb in args → use default
        args = argparse.Namespace(
            devforge_dir=str(self.devforge),
            package="pkg-a",
            concern="components",
        )
        self.devforge.mkdir(parents=True, exist_ok=True)
        code, out, _ = _run_cmd(args)
        payload = json.loads(out)
        self.assertNotIn("split", payload)
        self.assertIn("files", payload)
        self.assertIn("tree_text", payload)
        # Legacy fields all present
        for key in ("concern", "package", "subfolder", "tree_text", "files", "source_stamp"):
            self.assertIn(key, payload)


if __name__ == "__main__":
    unittest.main()
