"""Tests for _validate_doc.py split-parent rules — Plan F 3a.5.

Cases:
  1.  _validate_split_parent_doc: well-formed parent doc → no errors
  2.  _validate_split_parent_doc: missing required frontmatter key → error
  3.  _validate_split_parent_doc: missing `## Purpose` → error
  4.  _validate_split_parent_doc: missing `## Sub-concerns` → error
  5.  _validate_split_parent_doc: forbidden `## Structure` → error
  6.  _validate_split_parent_doc: empty Sub-concerns section → error
  7.  _validate_split_parent_doc: bullet missing locked shape → error
  8.  _validate_split_parent_doc: doc_path that doesn't resolve → error
  9.  _validate_split_parent_doc: multi-line bullet continuation parses + resolves
 10.  _validate_split_parent_doc: summary over 200 chars → error
 11.  _validate_split_parent_doc: bullet over 300 chars → error
 12.  _validate_split_parent_doc: banned phrase in body → error
 13.  cmd_validate_doc: tier=concern + --split routes to parent validator
 14.  cmd_validate_doc: tier=concern WITHOUT --split keeps leaf validator
 15.  cmd_validate_doc: split flag on missing parent → exit 2
 16.  cmd_validate_doc: split flag with malformed bullet → exit 2
 17.  cmd_validate_doc: split flag on non-concern tier → exit 2

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _generate_docs._validate_doc import (  # noqa: E402
    _validate_split_parent_doc,
    cmd_validate_doc,
)


_VALID_PARENT_DOC = """---
concern: components
package: pkg-a
source_stamp: abc1234567890def
last_indexed: 2026-05-08
split: true
---

# components

## Purpose
Cross-package presentation layer aggregating account, catalog, and order children.

## Sub-concerns
- accounts — Account UI ([→](accounts/index.md))
- catalog — Item browse ([→](catalog/index.md))
- order — Order workflow ([→](order/index.md))
"""


def _seed_parent_with_children(root: Path, children=("accounts", "catalog", "order")) -> Path:
    """Write a valid parent doc + matching child stub docs. Returns parent path."""
    parent_dir = root / "docs" / "pkg-a" / "components"
    parent_dir.mkdir(parents=True, exist_ok=True)
    parent_path = parent_dir / "index.md"
    parent_path.write_text(_VALID_PARENT_DOC, encoding="utf-8")
    for child in children:
        child_dir = parent_dir / child
        child_dir.mkdir(parents=True, exist_ok=True)
        (child_dir / "index.md").write_text(
            f"---\nconcern: {child}\n---\n\n# {child}\n",
            encoding="utf-8",
        )
    return parent_path


class ValidateSplitParentDocTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_well_formed_doc_no_errors(self):
        parent = _seed_parent_with_children(self.root)
        errors = _validate_split_parent_doc(parent, "pkg-a/components", self.root)
        self.assertEqual(errors, [])

    def test_missing_frontmatter_key(self):
        parent = _seed_parent_with_children(self.root)
        # Strip source_stamp from frontmatter
        text = parent.read_text(encoding="utf-8").replace(
            "source_stamp: abc1234567890def\n", ""
        )
        parent.write_text(text, encoding="utf-8")
        errors = _validate_split_parent_doc(parent, "pkg-a/components", self.root)
        self.assertTrue(any("source_stamp" in e for e in errors), msg=errors)

    def test_missing_purpose_section(self):
        parent = _seed_parent_with_children(self.root)
        text = parent.read_text(encoding="utf-8").replace("## Purpose\n", "")
        parent.write_text(text, encoding="utf-8")
        errors = _validate_split_parent_doc(parent, "pkg-a/components", self.root)
        self.assertTrue(any("Purpose" in e for e in errors), msg=errors)

    def test_missing_subconcerns_section(self):
        parent = _seed_parent_with_children(self.root)
        # Strip "## Sub-concerns" header (and the leaf bullets become loose lines)
        text = parent.read_text(encoding="utf-8").replace("## Sub-concerns\n", "")
        parent.write_text(text, encoding="utf-8")
        errors = _validate_split_parent_doc(parent, "pkg-a/components", self.root)
        self.assertTrue(any("Sub-concerns" in e for e in errors), msg=errors)

    def test_forbidden_structure_section(self):
        parent = _seed_parent_with_children(self.root)
        text = parent.read_text(encoding="utf-8") + "\n## Structure\nsrc/components/\n"
        parent.write_text(text, encoding="utf-8")
        errors = _validate_split_parent_doc(parent, "pkg-a/components", self.root)
        self.assertTrue(
            any("Structure" in e and "forbidden" in e for e in errors),
            msg=errors,
        )

    def test_empty_subconcerns_section(self):
        parent_dir = self.root / "docs" / "pkg-a" / "components"
        parent_dir.mkdir(parents=True, exist_ok=True)
        parent_path = parent_dir / "index.md"
        parent_path.write_text(
            "---\nconcern: components\npackage: pkg-a\nsource_stamp: x\nlast_indexed: 2026-05-08\n---\n\n"
            "# components\n\n## Purpose\np\n\n## Sub-concerns\n",
            encoding="utf-8",
        )
        errors = _validate_split_parent_doc(parent_path, "pkg-a/components", self.root)
        self.assertTrue(
            any("no bullets" in e for e in errors),
            msg=errors,
        )

    def test_bullet_fails_locked_shape(self):
        parent = _seed_parent_with_children(self.root)
        # Insert a malformed bullet
        text = parent.read_text(encoding="utf-8") + "- bare-bullet-no-arrow\n"
        parent.write_text(text, encoding="utf-8")
        errors = _validate_split_parent_doc(parent, "pkg-a/components", self.root)
        self.assertTrue(
            any("fails locked shape" in e for e in errors),
            msg=errors,
        )

    def test_doc_path_does_not_resolve(self):
        parent = _seed_parent_with_children(self.root)
        # Add a bullet pointing to a non-existent child
        text = parent.read_text(encoding="utf-8") + "- ghost — Missing ([→](ghost/index.md))\n"
        parent.write_text(text, encoding="utf-8")
        errors = _validate_split_parent_doc(parent, "pkg-a/components", self.root)
        self.assertTrue(
            any("doc_path does not resolve" in e and "ghost" in e for e in errors),
            msg=errors,
        )

    def test_multiline_bullet_continuation_resolves(self):
        # Edge case 11 from 3a.5 brief: parent bullet split across two lines
        # (continuation indented). _parse_bullets joins them on a space —
        # the regex must still match + path must still resolve.
        parent_dir = self.root / "docs" / "pkg-a" / "components"
        parent_dir.mkdir(parents=True, exist_ok=True)
        (parent_dir / "accounts").mkdir()
        (parent_dir / "accounts" / "index.md").write_text("x", encoding="utf-8")
        parent_path = parent_dir / "index.md"
        parent_path.write_text(
            "---\nconcern: components\npackage: pkg-a\nsource_stamp: x\nlast_indexed: 2026-05-08\n---\n\n"
            "# components\n\n## Purpose\np\n\n"
            "## Sub-concerns\n"
            "- accounts — Account UI\n"
            "  continued ([→](accounts/index.md))\n",
            encoding="utf-8",
        )
        errors = _validate_split_parent_doc(parent_path, "pkg-a/components", self.root)
        self.assertEqual(errors, [])

    def test_summary_over_200_chars(self):
        # Whole bullet under 300 (passes _BULLET_CAP) but summary alone > 200
        # → must error per 3a.3 spec's `purpose_summary ≤ 200` rule.
        parent_dir = self.root / "docs" / "pkg-a" / "components"
        parent_dir.mkdir(parents=True, exist_ok=True)
        (parent_dir / "x").mkdir()
        (parent_dir / "x" / "index.md").write_text("x", encoding="utf-8")
        parent_path = parent_dir / "index.md"
        long_summary = "X" * 250  # > 200 cap
        parent_path.write_text(
            "---\nconcern: components\npackage: pkg-a\nsource_stamp: x\nlast_indexed: 2026-05-08\n---\n\n"
            "# components\n\n## Purpose\np\n\n"
            "## Sub-concerns\n"
            f"- x — {long_summary} ([→](x/index.md))\n",
            encoding="utf-8",
        )
        errors = _validate_split_parent_doc(parent_path, "pkg-a/components", self.root)
        self.assertTrue(
            any("summary length 250 > 200" in e for e in errors),
            msg=errors,
        )

    def test_bullet_over_300_chars(self):
        parent = _seed_parent_with_children(self.root)
        long_summary = "X" * 280
        long_bullet = f"- huge — {long_summary} ([→](huge/index.md))\n"
        text = parent.read_text(encoding="utf-8") + long_bullet
        parent.write_text(text, encoding="utf-8")
        # Also seed the child so doc_path check passes
        (self.root / "docs" / "pkg-a" / "components" / "huge").mkdir(parents=True)
        (self.root / "docs" / "pkg-a" / "components" / "huge" / "index.md").write_text(
            "x", encoding="utf-8"
        )
        errors = _validate_split_parent_doc(parent, "pkg-a/components", self.root)
        self.assertTrue(
            any("> 300" in e for e in errors),
            msg=errors,
        )

    def test_banned_phrase_in_body(self):
        parent_dir = self.root / "docs" / "pkg-a" / "components"
        parent_dir.mkdir(parents=True, exist_ok=True)
        parent_path = parent_dir / "index.md"
        # "this document" is in the banned-phrases regex
        parent_path.write_text(
            "---\nconcern: components\npackage: pkg-a\nsource_stamp: x\nlast_indexed: 2026-05-08\n---\n\n"
            "# components\n\n## Purpose\nThis document covers nothing.\n\n"
            "## Sub-concerns\n- a — A ([→](a/index.md))\n",
            encoding="utf-8",
        )
        (parent_dir / "a").mkdir()
        (parent_dir / "a" / "index.md").write_text("x", encoding="utf-8")
        errors = _validate_split_parent_doc(parent_path, "pkg-a/components", self.root)
        self.assertTrue(
            any("banned phrase" in e for e in errors),
            msg=errors,
        )


class CmdValidateDocSplitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir(parents=True, exist_ok=True)

    def _run(self, **overrides):
        base = {
            "tier": "concern",
            "target": "pkg-a/components",
            "devforge_dir": str(self.devforge),
            "split": False,
        }
        base.update(overrides)
        args = argparse.Namespace(**base)
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cmd_validate_doc(args)
        return code, out.getvalue(), err.getvalue()

    def test_split_flag_routes_to_parent_validator(self):
        _seed_parent_with_children(self.root)
        code, _, err = self._run(split=True)
        self.assertEqual(code, 0, msg=err)

    def test_no_split_flag_uses_leaf_validator(self):
        # Plant a parent-shaped doc but DON'T pass --split → leaf validator
        # rejects it for missing `## Structure`.
        _seed_parent_with_children(self.root)
        code, _, err = self._run(split=False)
        self.assertEqual(code, 2)
        self.assertIn("Structure", err)

    def test_split_flag_on_missing_parent_returns_2(self):
        code, _, err = self._run(split=True)
        self.assertEqual(code, 2)
        self.assertIn("doc not found", err)

    def test_split_flag_with_malformed_bullet_returns_2(self):
        parent = _seed_parent_with_children(self.root)
        text = parent.read_text(encoding="utf-8") + "- malformed-no-arrow\n"
        parent.write_text(text, encoding="utf-8")
        code, _, err = self._run(split=True)
        self.assertEqual(code, 2)
        self.assertIn("locked shape", err)

    def test_split_flag_on_non_concern_tier_returns_2(self):
        code, _, err = self._run(tier="package-overview", target="pkg-a", split=True)
        self.assertEqual(code, 2)
        self.assertIn("--split", err)
        self.assertIn("concern", err)


if __name__ == "__main__":
    unittest.main()
