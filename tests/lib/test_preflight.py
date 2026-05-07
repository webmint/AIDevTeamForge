"""Tests for _preflight.py — F.0 preflight subcommand.

Cases:
  1.  _enumerate_concerns: index.json with 2 packages × N src/ subdirs returns
      every (pkg, concern) pair; trivial-leaf names excluded.
  2.  _enumerate_concerns: package without src/ dir is skipped.
  3.  _enumerate_concerns: missing/malformed index.json returns [].
  4.  _read_prior_stamp: doc with valid frontmatter source_stamp returns it.
  5.  _read_prior_stamp: nonexistent doc returns None.
  6.  _read_prior_stamp: malformed frontmatter returns None.
  7.  _diff_concern: concern with no doc → status "new".
  8.  _diff_concern: concern with matching doc stamp → status "unchanged".
  9.  _diff_concern: concern with stale doc stamp → status "changed".
 10.  _diff_concern: concern with empty subfolder → status "empty".
 11.  cmd_preflight: vue-extract + cli index_repository SKIPPED via flags →
      emits valid JSON without those sections; concerns[] still computed.
 12.  cmd_preflight: writes .preflight-stamp on success.
 13.  cmd_preflight: stamp content changes when one source file is touched.

Skipping live vue-extract / CBM tests — those require external binaries.
The mechanical paths (skip-flag mode + concern enumeration + stamp diff)
are covered without subprocess invocation.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _generate_docs._preflight import (  # noqa: E402
    _diff_concern,
    _enumerate_concerns,
    _read_prior_stamp,
    cmd_preflight,
)


def _write_index_json(devforge_dir: Path, packages: dict) -> None:
    devforge_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "generated_at": "2026-05-07T00:00:00Z",
        "project_root": str(devforge_dir.parent),
        "packages": packages,
    }
    (devforge_dir / "index.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def _make_args(devforge_dir: Path, **overrides) -> argparse.Namespace:
    base = {
        "devforge_dir": str(devforge_dir),
        "skip_vue_extract": False,
        "skip_index": False,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


class EnumerateConcernsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.devforge = self.root / ".devforge"

    def test_two_packages_with_concerns(self):
        for pkg in ("pkg-a", "pkg-b"):
            for concern in ("order", "auth"):
                (self.root / pkg / "src" / concern).mkdir(parents=True)
        _write_index_json(self.devforge, packages={"pkg-a": {}, "pkg-b": {}, ".": {}})
        pairs = _enumerate_concerns(self.devforge, self.root)
        self.assertEqual(
            sorted(pairs),
            [("pkg-a", "auth"), ("pkg-a", "order"), ("pkg-b", "auth"), ("pkg-b", "order")],
        )

    def test_package_without_src_skipped(self):
        (self.root / "pkg-with-src" / "src" / "ok").mkdir(parents=True)
        (self.root / "pkg-no-src").mkdir(parents=True)
        _write_index_json(
            self.devforge, packages={"pkg-with-src": {}, "pkg-no-src": {}}
        )
        pairs = _enumerate_concerns(self.devforge, self.root)
        self.assertEqual(pairs, [("pkg-with-src", "ok")])

    def test_missing_index_returns_empty(self):
        pairs = _enumerate_concerns(self.devforge, self.root)
        self.assertEqual(pairs, [])

    def test_malformed_index_returns_empty(self):
        self.devforge.mkdir(parents=True)
        (self.devforge / "index.json").write_text("not json", encoding="utf-8")
        pairs = _enumerate_concerns(self.devforge, self.root)
        self.assertEqual(pairs, [])

    def test_trivial_leaf_dir_excluded(self):
        (self.root / "pkg-a" / "src" / "node_modules").mkdir(parents=True)
        (self.root / "pkg-a" / "src" / "real").mkdir(parents=True)
        _write_index_json(self.devforge, packages={"pkg-a": {}})
        pairs = _enumerate_concerns(self.devforge, self.root)
        self.assertEqual(pairs, [("pkg-a", "real")])


class ReadPriorStampTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_doc_with_source_stamp(self):
        doc = self.root / "index.md"
        doc.write_text(
            "---\nconcern: order\nsource_stamp: abc123def456\n---\n\nbody\n",
            encoding="utf-8",
        )
        self.assertEqual(_read_prior_stamp(doc), "abc123def456")

    def test_nonexistent_doc_returns_none(self):
        doc = self.root / "missing.md"
        self.assertIsNone(_read_prior_stamp(doc))

    def test_malformed_frontmatter_returns_none(self):
        doc = self.root / "bad.md"
        doc.write_text("no frontmatter here\n", encoding="utf-8")
        self.assertIsNone(_read_prior_stamp(doc))

    def test_doc_without_source_stamp_field_returns_none(self):
        doc = self.root / "no_stamp.md"
        doc.write_text("---\nconcern: order\n---\n\nbody\n", encoding="utf-8")
        self.assertIsNone(_read_prior_stamp(doc))


class DiffConcernTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.docs = self.root / "docs"
        self.src = self.root / "pkg-a" / "src" / "order"
        self.src.mkdir(parents=True)
        (self.src / "Real.ts").write_text("export const x = 1;\n", encoding="utf-8")

    def test_no_existing_doc_status_new(self):
        result = _diff_concern("pkg-a", "order", self.root, self.docs)
        self.assertEqual(result["status"], "new")
        self.assertIsNone(result["prior_stamp"])
        self.assertTrue(result["source_stamp"])

    def test_matching_stamp_status_unchanged(self):
        first = _diff_concern("pkg-a", "order", self.root, self.docs)
        doc_dir = self.docs / "pkg-a" / "order"
        doc_dir.mkdir(parents=True)
        (doc_dir / "index.md").write_text(
            f"---\nconcern: order\nsource_stamp: {first['source_stamp']}\n---\n\nbody\n",
            encoding="utf-8",
        )
        result = _diff_concern("pkg-a", "order", self.root, self.docs)
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(result["prior_stamp"], first["source_stamp"])

    def test_stale_stamp_status_changed(self):
        doc_dir = self.docs / "pkg-a" / "order"
        doc_dir.mkdir(parents=True)
        (doc_dir / "index.md").write_text(
            "---\nconcern: order\nsource_stamp: deadbeefdeadbeef\n---\n\nbody\n",
            encoding="utf-8",
        )
        result = _diff_concern("pkg-a", "order", self.root, self.docs)
        self.assertEqual(result["status"], "changed")
        self.assertEqual(result["prior_stamp"], "deadbeefdeadbeef")
        self.assertNotEqual(result["source_stamp"], "deadbeefdeadbeef")

    def test_empty_subfolder_status_empty(self):
        empty_concern = self.root / "pkg-a" / "src" / "ghost"
        empty_concern.mkdir()
        result = _diff_concern("pkg-a", "ghost", self.root, self.docs)
        self.assertEqual(result["status"], "empty")


class CmdPreflightTests(unittest.TestCase):
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

    def test_skip_both_flags_emits_concerns_only(self):
        (self.root / "pkg-a" / "src" / "order").mkdir(parents=True)
        (self.root / "pkg-a" / "src" / "order" / "Real.ts").write_text(
            "export const x = 1;\n", encoding="utf-8"
        )
        _write_index_json(self.devforge, packages={"pkg-a": {}})
        args = _make_args(self.devforge, skip_vue_extract=True, skip_index=True)
        code, out, _ = self._run(args)
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["vue_extract"]["ran"], False)
        self.assertEqual(payload["index_repository"]["ran"], False)
        self.assertEqual(len(payload["concerns"]), 1)
        self.assertEqual(payload["concerns"][0]["status"], "new")
        self.assertEqual(payload["concern_counts"]["new"], 1)

    def test_writes_preflight_stamp(self):
        (self.root / "pkg-a" / "src" / "order").mkdir(parents=True)
        (self.root / "pkg-a" / "src" / "order" / "x.ts").write_text(
            "1\n", encoding="utf-8"
        )
        _write_index_json(self.devforge, packages={"pkg-a": {}})
        args = _make_args(self.devforge, skip_vue_extract=True, skip_index=True)
        before = time.time()
        code, _, _ = self._run(args)
        after = time.time()
        self.assertEqual(code, 0)
        stamp_file = self.devforge / ".preflight-stamp"
        self.assertTrue(stamp_file.exists())
        recorded = int(stamp_file.read_text().strip())
        self.assertGreaterEqual(recorded, int(before))
        self.assertLessEqual(recorded, int(after) + 1)

    def test_stamp_changes_when_source_touched(self):
        src_file = self.root / "pkg-a" / "src" / "order" / "x.ts"
        src_file.parent.mkdir(parents=True)
        src_file.write_text("1\n", encoding="utf-8")
        _write_index_json(self.devforge, packages={"pkg-a": {}})
        args = _make_args(self.devforge, skip_vue_extract=True, skip_index=True)
        _, out1, _ = self._run(args)
        stamp1 = json.loads(out1)["concerns"][0]["source_stamp"]
        src_file.write_text("2\n", encoding="utf-8")
        _, out2, _ = self._run(args)
        stamp2 = json.loads(out2)["concerns"][0]["source_stamp"]
        self.assertNotEqual(stamp1, stamp2)


if __name__ == "__main__":
    unittest.main()
