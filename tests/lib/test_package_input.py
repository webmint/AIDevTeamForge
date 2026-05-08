"""Tests for _package_input.py — F.7a package-input helper.

Cases:
  1.  _enumerate_concerns: lists subdirs of <pkg>/src/, alphabetically
  2.  _enumerate_concerns: skips trivial dirs + dot-prefixed
  3.  _enumerate_concerns: missing src/ → empty
  4.  _read_concern_seed: parses frontmatter + Purpose section
  5.  _read_concern_seed: missing doc → None
  6.  _read_concern_seed: malformed frontmatter → None
  7.  _read_concern_seed: doc without ## Purpose → empty purpose_text
  8.  _collect_package_root_files: README + CHANGELOG → records + hashes
  9.  _collect_package_root_files: no eligible files → empty
 10.  _compute_source_stamp: deterministic across reorderings
 11.  _compute_source_stamp: changes when concern stamp changes
 12.  cmd_package_input: synthetic project end-to-end → valid JSON
 13.  cmd_package_input: no concerns under <pkg>/src/ → exit 2
 14.  cmd_package_input: concerns exist but no docs rendered → exit 2
 15.  cmd_package_input: missing concern docs surfaced under
       `missing_concern_docs` key (graceful)

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

from _generate_docs._package_input import (  # noqa: E402
    _collect_package_root_files,
    _compute_source_stamp,
    _enumerate_concerns,
    _read_concern_seed,
    cmd_package_input,
)


def _run(handler, args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = handler(args)
    return code, out.getvalue(), err.getvalue()


def _ns(devforge: Path, package: str = "pkg-a") -> argparse.Namespace:
    return argparse.Namespace(devforge_dir=str(devforge), package=package)


class EnumerateConcernsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_lists_subdirs(self):
        for c in ("zebra", "alpha", "mid"):
            (self.root / "pkg-a" / "src" / c).mkdir(parents=True)
        self.assertEqual(
            _enumerate_concerns(self.root, "pkg-a"),
            ["alpha", "mid", "zebra"],
        )

    def test_skips_trivial_and_dotfiles(self):
        for c in ("real", "node_modules", ".hidden", "build"):
            (self.root / "pkg-a" / "src" / c).mkdir(parents=True)
        self.assertEqual(_enumerate_concerns(self.root, "pkg-a"), ["real"])

    def test_missing_src(self):
        (self.root / "pkg-a").mkdir()
        self.assertEqual(_enumerate_concerns(self.root, "pkg-a"), [])


_DOC_TEMPLATE = """---
concern: order
package: pkg-a
files: 3
source_stamp: stamp-{stamp}
last_indexed: 2026-05-08
---


# order

## Purpose

Order flow for pkg-a.

## Structure

```text
src/order/
└── x.ts
```
"""


class ReadConcernSeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _write_doc(self, package: str, concern: str, content: str) -> Path:
        path = self.root / "docs" / package / concern / "index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_parses_frontmatter_and_purpose(self):
        self._write_doc("pkg-a", "order", _DOC_TEMPLATE.format(stamp="A"))
        seed = _read_concern_seed(self.root, "pkg-a", "order")
        self.assertIsNotNone(seed)
        self.assertEqual(seed["concern"], "order")
        self.assertEqual(seed["frontmatter"]["source_stamp"], "stamp-A")
        self.assertIn("Order flow for pkg-a.", seed["purpose_text"])

    def test_missing_doc_returns_none(self):
        self.assertIsNone(_read_concern_seed(self.root, "pkg-a", "ghost"))

    def test_malformed_frontmatter_returns_none(self):
        self._write_doc("pkg-a", "order", "no frontmatter here\n")
        self.assertIsNone(_read_concern_seed(self.root, "pkg-a", "order"))

    def test_missing_purpose_section_returns_empty_purpose(self):
        body = (
            "---\n"
            "concern: order\n"
            "source_stamp: x\n"
            "---\n\n"
            "# order\n\n"
            "## Structure\n\nbody\n"
        )
        self._write_doc("pkg-a", "order", body)
        seed = _read_concern_seed(self.root, "pkg-a", "order")
        self.assertEqual(seed["purpose_text"], "")


class CollectPackageRootFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_picks_up_readme_and_changelog(self):
        pkg_dir = self.root / "pkg-a"
        pkg_dir.mkdir(parents=True)
        (pkg_dir / "README.md").write_text("# pkg-a\n\ndoc text\n", encoding="utf-8")
        (pkg_dir / "CHANGELOG.md").write_text("v1\n", encoding="utf-8")
        records, hashes = _collect_package_root_files(self.root, "pkg-a")
        names = sorted(r["path"] for r in records)
        self.assertIn("pkg-a/README.md", names)
        self.assertIn("pkg-a/CHANGELOG.md", names)
        self.assertEqual(len(hashes), len(records))

    def test_no_eligible_files(self):
        (self.root / "pkg-a").mkdir()
        records, hashes = _collect_package_root_files(self.root, "pkg-a")
        self.assertEqual(records, [])
        self.assertEqual(hashes, [])


class ComputeSourceStampTests(unittest.TestCase):
    def test_deterministic_across_reordering(self):
        seed_a = {"concern": "alpha", "frontmatter": {"source_stamp": "1"}}
        seed_b = {"concern": "beta", "frontmatter": {"source_stamp": "2"}}
        hashes_1 = [("pkg-a/README.md", "h1"), ("pkg-a/CHANGELOG.md", "h2")]
        hashes_2 = [("pkg-a/CHANGELOG.md", "h2"), ("pkg-a/README.md", "h1")]
        s1 = _compute_source_stamp([seed_a, seed_b], hashes_1)
        s2 = _compute_source_stamp([seed_b, seed_a], hashes_2)
        self.assertEqual(s1, s2)

    def test_changes_when_concern_stamp_changes(self):
        seed_v1 = {"concern": "alpha", "frontmatter": {"source_stamp": "1"}}
        seed_v2 = {"concern": "alpha", "frontmatter": {"source_stamp": "2"}}
        s1 = _compute_source_stamp([seed_v1], [])
        s2 = _compute_source_stamp([seed_v2], [])
        self.assertNotEqual(s1, s2)


class CmdPackageInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir()

    def _setup_concerns(self, package: str, concerns):
        for c in concerns:
            (self.root / package / "src" / c).mkdir(parents=True)

    def _write_doc(self, package: str, concern: str, stamp: str = "A"):
        path = self.root / "docs" / package / concern / "index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_DOC_TEMPLATE.format(stamp=stamp), encoding="utf-8")

    def test_end_to_end(self):
        self._setup_concerns("pkg-a", ["order", "accounts"])
        for c in ("order", "accounts"):
            self._write_doc("pkg-a", c)
        (self.root / "pkg-a" / "README.md").write_text(
            "# pkg-a\n\nintro\n", encoding="utf-8"
        )
        code, out, _ = _run(cmd_package_input, _ns(self.devforge, package="pkg-a"))
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["package"], "pkg-a")
        self.assertEqual(len(payload["concern_seeds"]), 2)
        self.assertEqual(
            sorted(s["concern"] for s in payload["concern_seeds"]),
            ["accounts", "order"],
        )
        names = [r["path"] for r in payload["package_root_files"]]
        self.assertIn("pkg-a/README.md", names)
        self.assertRegex(payload["source_stamp"], r"^[0-9a-f]{16}$")

    def test_no_concerns_returns_2(self):
        (self.root / "pkg-a").mkdir()
        code, _, err = _run(cmd_package_input, _ns(self.devforge, package="pkg-a"))
        self.assertEqual(code, 2)
        self.assertIn("no `src/<concern>/`", err)

    def test_no_docs_rendered_returns_2(self):
        self._setup_concerns("pkg-a", ["order"])
        code, _, err = _run(cmd_package_input, _ns(self.devforge, package="pkg-a"))
        self.assertEqual(code, 2)
        self.assertIn("no concern docs found", err)

    def test_missing_concern_docs_surfaced(self):
        self._setup_concerns("pkg-a", ["order", "ghost"])
        # Render only `order`
        self._write_doc("pkg-a", "order")
        code, out, _ = _run(cmd_package_input, _ns(self.devforge, package="pkg-a"))
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["missing_concern_docs"], ["ghost"])
        self.assertEqual(len(payload["concern_seeds"]), 1)


if __name__ == "__main__":
    unittest.main()
