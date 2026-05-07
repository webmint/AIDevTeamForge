"""Tests for _validate_doc.py — F.5 concern-tier doc validator (v0).

Cases:
  1.  _split_sections: parses ## anchors into {name: body} dict
  2.  _split_sections: empty body returns empty dict
  3.  _parse_bullets: simple bullets at start-of-line
  4.  _parse_bullets: multi-line bullet (continuation indented)
  5.  _resolve_cite_path: full project-relative path resolves
  6.  _resolve_cite_path: in-concern basename shortening resolves
  7.  _resolve_cite_path: nonexistent → mode "miss"
  8.  _validate_concern_doc: well-formed doc → no errors
  9.  _validate_concern_doc: frontmatter missing required key → error
 10.  _validate_concern_doc: missing section anchor → error
 11.  _validate_concern_doc: banned phrase → error with line number
 12.  _validate_concern_doc: hazard count below 3 → error
 13.  _validate_concern_doc: hazard count above 15 → error
 14.  _validate_concern_doc: hazard missing cite-back → error
 15.  _validate_concern_doc: hazard exceeds 200 chars → error
 16.  _validate_concern_doc: structure annotation > 60 chars → error
 17.  _validate_concern_doc: cite-back to nonexistent file → error
 18.  _validate_concern_doc: cite-back line out of range → error
 19.  cmd_validate_doc: tier other than concern → exit 2
 20.  cmd_validate_doc: missing doc → exit 2

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
    _parse_bullets,
    _resolve_cite_path,
    _split_sections,
    _validate_concern_doc,
    cmd_validate_doc,
)


_VALID_DOC_TEMPLATE = """---
concern: order
package: pkg-a
files: 3
source_stamp: abc123def456
last_indexed: 2026-05-07
---

# order

## Purpose
Cross-cutting order flow for pkg-a.

## Structure
src/order/
├── OrderFooter.ts — submit/cancel + T&C handler
└── OrderLines.ts — line-item editor

## Hazards
- OrderFooter mutates props.lines silently — pkg-a/src/order/OrderFooter.ts:5
- OrderLines deep-watches lines triggering full re-render — pkg-a/src/order/OrderLines.ts:3
- Pricing rounds with Banker's rounding; do NOT swap to Math.round — pkg-a/src/order/OrderFooter.ts:8
"""


class SplitSectionsTests(unittest.TestCase):
    def test_parses_anchors_into_dict(self):
        body = "# title\n\n## A\nbody-a\n\n## B\nbody-b\nmore-b\n"
        result = _split_sections(body)
        self.assertIn("A", result)
        self.assertIn("B", result)
        self.assertIn("body-a", result["A"])
        self.assertIn("body-b", result["B"])
        self.assertIn("more-b", result["B"])

    def test_empty_body(self):
        self.assertEqual(_split_sections(""), {})


class ParseBulletsTests(unittest.TestCase):
    def test_simple_bullets(self):
        text = "- one\n- two\n- three\n"
        self.assertEqual(_parse_bullets(text), ["one", "two", "three"])

    def test_multi_line_bullet(self):
        text = "- first part\n  continuation\n- second\n"
        result = _parse_bullets(text)
        self.assertEqual(len(result), 2)
        self.assertIn("first part", result[0])
        self.assertIn("continuation", result[0])
        self.assertEqual(result[1], "second")


class ResolveCitePathTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "pkg-a" / "src" / "order").mkdir(parents=True)
        (self.root / "pkg-a" / "src" / "order" / "OrderFooter.ts").write_text(
            "x\n", encoding="utf-8"
        )

    def test_full_path_resolves(self):
        path, mode = _resolve_cite_path(
            "pkg-a/src/order/OrderFooter.ts", "pkg-a/order", self.root
        )
        self.assertEqual(mode, "full")
        self.assertTrue(path.is_file())

    def test_basename_shortening_resolves(self):
        # target is `<pkg>/<concern>` (no src/); resolver must insert src/
        # to match the on-disk source layout.
        path, mode = _resolve_cite_path(
            "OrderFooter.ts", "pkg-a/order", self.root
        )
        self.assertEqual(mode, "basename")
        self.assertTrue(path.is_file())

    def test_basename_resolves_for_nested_package_target(self):
        # Multi-component package targets (db-cse-ui-strata/packages/pkg-x)
        # split correctly: last segment is concern, prior segments are pkg.
        nested_root = self.root / "ws" / "packages" / "pkg-x"
        (nested_root / "src" / "feature").mkdir(parents=True)
        (nested_root / "src" / "feature" / "Inner.ts").write_text("x\n", encoding="utf-8")
        path, mode = _resolve_cite_path(
            "Inner.ts", "ws/packages/pkg-x/feature", self.root
        )
        self.assertEqual(mode, "basename")
        self.assertTrue(path.is_file())

    def test_verbatim_fallback_when_target_already_has_src(self):
        # Caller passes target that already includes `src/` — verbatim
        # append still resolves (covers tests that pass full path).
        path, mode = _resolve_cite_path(
            "OrderFooter.ts", "pkg-a/src/order", self.root
        )
        self.assertEqual(mode, "verbatim")

    def test_miss(self):
        path, mode = _resolve_cite_path("nonexistent.ts", "pkg-a/order", self.root)
        self.assertEqual(mode, "miss")


class ValidateConcernDocTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        # Source files for cite-back resolution
        src = self.root / "pkg-a" / "src" / "order"
        src.mkdir(parents=True)
        (src / "OrderFooter.ts").write_text("x\n" * 20, encoding="utf-8")
        (src / "OrderLines.ts").write_text("y\n" * 20, encoding="utf-8")
        # Doc location
        self.doc_path = self.root / "docs" / "pkg-a" / "src" / "order" / "index.md"
        self.doc_path.parent.mkdir(parents=True)

    def _write(self, content: str) -> None:
        self.doc_path.write_text(content, encoding="utf-8")

    def test_well_formed_doc_no_errors(self):
        self._write(_VALID_DOC_TEMPLATE)
        errors = _validate_concern_doc(self.doc_path, "pkg-a/src/order", self.root)
        self.assertEqual(errors, [])

    def test_frontmatter_missing_key(self):
        broken = _VALID_DOC_TEMPLATE.replace("source_stamp: abc123def456\n", "")
        self._write(broken)
        errors = _validate_concern_doc(self.doc_path, "pkg-a/src/order", self.root)
        self.assertTrue(any("source_stamp" in e for e in errors))

    def test_missing_section_anchor(self):
        broken = _VALID_DOC_TEMPLATE.replace("## Hazards", "## Hzrds_typo")
        self._write(broken)
        errors = _validate_concern_doc(self.doc_path, "pkg-a/src/order", self.root)
        self.assertTrue(any("missing required section" in e and "Hazards" in e for e in errors))

    def test_banned_phrase(self):
        broken = _VALID_DOC_TEMPLATE.replace(
            "Cross-cutting order flow for pkg-a.",
            "This document covers various aspects of order flow.",
        )
        self._write(broken)
        errors = _validate_concern_doc(self.doc_path, "pkg-a/src/order", self.root)
        self.assertTrue(any("banned phrase" in e for e in errors))

    def test_hazard_count_below_three(self):
        broken = _VALID_DOC_TEMPLATE.replace(
            "## Hazards\n"
            "- OrderFooter mutates props.lines silently — pkg-a/src/order/OrderFooter.ts:5\n"
            "- OrderLines deep-watches lines triggering full re-render — pkg-a/src/order/OrderLines.ts:3\n"
            "- Pricing rounds with Banker's rounding; do NOT swap to Math.round — pkg-a/src/order/OrderFooter.ts:8\n",
            "## Hazards\n- only one hazard — pkg-a/src/order/OrderFooter.ts:5\n",
        )
        self._write(broken)
        errors = _validate_concern_doc(self.doc_path, "pkg-a/src/order", self.root)
        self.assertTrue(any("hazard count 1 outside range" in e for e in errors))

    def test_hazard_count_above_fifteen(self):
        # Build a doc with 16 hazards
        many_hazards = "\n".join(
            f"- hazard #{i} description — pkg-a/src/order/OrderFooter.ts:{i}"
            for i in range(1, 17)
        )
        replacement_section = "## Hazards\n" + many_hazards + "\n"
        broken = _VALID_DOC_TEMPLATE[: _VALID_DOC_TEMPLATE.index("## Hazards")] + replacement_section
        self._write(broken)
        errors = _validate_concern_doc(self.doc_path, "pkg-a/src/order", self.root)
        self.assertTrue(any("outside range" in e and "16" in e for e in errors))

    def test_hazard_missing_cite_back(self):
        broken = _VALID_DOC_TEMPLATE.replace(
            "- Pricing rounds with Banker's rounding; do NOT swap to Math.round — pkg-a/src/order/OrderFooter.ts:8",
            "- Pricing rounds with Banker's rounding; do NOT swap to Math.round",
        )
        self._write(broken)
        errors = _validate_concern_doc(self.doc_path, "pkg-a/src/order", self.root)
        self.assertTrue(any("missing cite-back" in e for e in errors))

    def test_hazard_exceeds_length_cap(self):
        long_hazard = "- " + ("X" * 250) + " — pkg-a/src/order/OrderFooter.ts:1"
        broken = _VALID_DOC_TEMPLATE.replace(
            "- OrderFooter mutates props.lines silently — pkg-a/src/order/OrderFooter.ts:5",
            long_hazard,
        )
        self._write(broken)
        errors = _validate_concern_doc(self.doc_path, "pkg-a/src/order", self.root)
        self.assertTrue(any("hazard 1 length" in e and "200" in e for e in errors))

    def test_structure_annotation_exceeds_cap(self):
        long_annotation = "├── X.ts — " + ("a" * 70)
        broken = _VALID_DOC_TEMPLATE.replace(
            "├── OrderFooter.ts — submit/cancel + T&C handler",
            long_annotation,
        )
        self._write(broken)
        errors = _validate_concern_doc(self.doc_path, "pkg-a/src/order", self.root)
        self.assertTrue(any("annotation" in e and "60" in e for e in errors))

    def test_cite_path_not_found(self):
        broken = _VALID_DOC_TEMPLATE.replace(
            "pkg-a/src/order/OrderFooter.ts:5",
            "pkg-a/src/order/Missing.ts:5",
        )
        self._write(broken)
        errors = _validate_concern_doc(self.doc_path, "pkg-a/src/order", self.root)
        self.assertTrue(any("cite path not found" in e for e in errors))

    def test_cite_line_out_of_range(self):
        broken = _VALID_DOC_TEMPLATE.replace(
            "pkg-a/src/order/OrderFooter.ts:5",
            "pkg-a/src/order/OrderFooter.ts:9999",
        )
        self._write(broken)
        errors = _validate_concern_doc(self.doc_path, "pkg-a/src/order", self.root)
        self.assertTrue(any("9999 out of range" in e for e in errors))


class CmdValidateDocTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir()

    def _run(self, args: argparse.Namespace):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cmd_validate_doc(args)
        return code, out.getvalue(), err.getvalue()

    def test_unsupported_tier_returns_2(self):
        args = argparse.Namespace(
            tier="package-overview",
            target="pkg-a",
            devforge_dir=str(self.devforge),
        )
        code, _, err = self._run(args)
        self.assertEqual(code, 2)
        self.assertIn("only tier=concern", err)

    def test_missing_doc_returns_2(self):
        args = argparse.Namespace(
            tier="concern",
            target="pkg-a/order",
            devforge_dir=str(self.devforge),
        )
        code, _, err = self._run(args)
        self.assertEqual(code, 2)
        self.assertIn("doc not found", err)


if __name__ == "__main__":
    unittest.main()
