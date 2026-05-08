"""Tests for _doc_setters.py split-aware setters — Plan F 3a.2.

Cases:
  1.  init-doc --split true: emits Purpose + Sub-concerns skeleton (NO Structure)
  2.  init-doc --split true: --tree value is ignored (no Structure section)
  3.  init-doc --split true: re-run wholesale-overwrites the skeleton
  4.  init-doc (no --split): default behaviour preserved (Purpose + Structure)
  5.  _render_subconcerns_bullets: full entry → '- name — summary ([→](path))'
  6.  _render_subconcerns_bullets: missing summary → '- name ([→](path))'
  7.  _render_subconcerns_bullets: missing doc_path → '- name — summary'
  8.  _render_subconcerns_bullets: missing name → entry skipped silently
  9.  set-doc-subconcerns: replaces placeholder with bulleted list
 10.  set-doc-subconcerns: idempotent re-run replaces filled block
 11.  set-doc-subconcerns: missing skeleton → exit 2
 12.  set-doc-subconcerns: invalid JSON → exit 2
 13.  set-doc-subconcerns: tier ≠ concern → exit 2
 14.  set-doc-subconcerns: doc lacks `## Sub-concerns` section → exit 2
 15.  end-to-end: init --split → set-purpose → set-subconcerns → render
       produces a parent doc whose body shape matches the spec

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

from _generate_docs._doc_setters import (  # noqa: E402
    _build_concern_split_skeleton,
    _render_subconcerns_bullets,
    cmd_init_doc,
    cmd_render_doc,
    cmd_set_doc_purpose,
    cmd_set_doc_subconcerns,
)


def _run(handler, args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = handler(args)
    return code, out.getvalue(), err.getvalue()


def _ns(devforge: Path, **overrides) -> argparse.Namespace:
    base = {
        "tier": "concern",
        "target": "pkg-a/components",
        "devforge_dir": str(devforge),
    }
    base.update(overrides)
    return argparse.Namespace(**base)


_VALID_FRONTMATTER = json.dumps(
    {"concern": "components", "package": "pkg-a", "source_stamp": "abc1234567890def"}
)


class BuildConcernSplitSkeletonTests(unittest.TestCase):
    def test_skeleton_has_purpose_and_subconcerns_no_structure(self):
        text = _build_concern_split_skeleton(
            {"concern": "components", "package": "pkg-a", "source_stamp": "x"}
        )
        self.assertIn("## Purpose", text)
        self.assertIn("## Sub-concerns", text)
        self.assertNotIn("## Structure", text)
        self.assertIn("<!-- TODO: purpose -->", text)
        self.assertIn("<!-- TODO: sub-concerns -->", text)
        # H1 header from concern field
        self.assertIn("# components", text)


class RenderSubconcernsBulletsTests(unittest.TestCase):
    def test_full_entry(self):
        out = _render_subconcerns_bullets(
            [{"name": "accounts", "purpose_summary": "Account UI", "doc_path": "accounts/index.md"}]
        )
        self.assertEqual(out, "- accounts — Account UI ([→](accounts/index.md))")

    def test_missing_summary_skipped(self):
        # 3a.5 validate-doc requires the full <name> — <summary> ([→](<path>))
        # shape; partial bullets would fail that regex, so we skip them.
        out = _render_subconcerns_bullets(
            [{"name": "x", "doc_path": "x/index.md"}]
        )
        self.assertEqual(out, "")

    def test_missing_doc_path_skipped(self):
        out = _render_subconcerns_bullets(
            [{"name": "x", "purpose_summary": "summary"}]
        )
        self.assertEqual(out, "")

    def test_missing_name_skipped(self):
        out = _render_subconcerns_bullets(
            [{"purpose_summary": "no name", "doc_path": "/x"}]
        )
        self.assertEqual(out, "")

    def test_only_name_skipped(self):
        # Bare entry — both optional fields absent; must NOT produce a "- foo" bullet.
        out = _render_subconcerns_bullets([{"name": "foo"}])
        self.assertEqual(out, "")

    def test_mixed_complete_and_partial_entries_keeps_only_complete(self):
        out = _render_subconcerns_bullets(
            [
                {"name": "good", "purpose_summary": "ok", "doc_path": "good/index.md"},
                {"name": "missing-path", "purpose_summary": "no path"},
                {"name": "missing-summary", "doc_path": "x/index.md"},
                {"name": "also-good", "purpose_summary": "yep", "doc_path": "also/index.md"},
            ]
        )
        self.assertEqual(
            out,
            "- good — ok ([→](good/index.md))\n- also-good — yep ([→](also/index.md))",
        )

    def test_multiple_entries_join_with_newline(self):
        out = _render_subconcerns_bullets(
            [
                {"name": "alpha", "purpose_summary": "A", "doc_path": "alpha/index.md"},
                {"name": "beta", "purpose_summary": "B", "doc_path": "beta/index.md"},
            ]
        )
        self.assertEqual(
            out,
            "- alpha — A ([→](alpha/index.md))\n- beta — B ([→](beta/index.md))",
        )


class CmdInitDocSplitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir(parents=True, exist_ok=True)

    def _skel_path(self) -> Path:
        return self.root / "docs" / "pkg-a" / "components" / "index.md.skeleton"

    def test_init_doc_split_emits_subconcerns_section(self):
        args = _ns(self.devforge, frontmatter=_VALID_FRONTMATTER, tree="", split=True)
        code, out, err = _run(cmd_init_doc, args)
        self.assertEqual(code, 0, msg=err)
        skel = self._skel_path()
        self.assertTrue(skel.is_file(), msg=f"missing skeleton at {skel}")
        body = skel.read_text(encoding="utf-8")
        self.assertIn("## Purpose", body)
        self.assertIn("## Sub-concerns", body)
        self.assertIn("<!-- TODO: sub-concerns -->", body)
        self.assertNotIn("## Structure", body)

    def test_init_doc_split_ignores_tree_arg(self):
        args = _ns(
            self.devforge,
            frontmatter=_VALID_FRONTMATTER,
            tree="this-should-not-appear",
            split=True,
        )
        code, _, err = _run(cmd_init_doc, args)
        self.assertEqual(code, 0, msg=err)
        body = self._skel_path().read_text(encoding="utf-8")
        self.assertNotIn("this-should-not-appear", body)
        self.assertNotIn("```text", body)

    def test_init_doc_split_rerun_wholesale_overwrites(self):
        args = _ns(self.devforge, frontmatter=_VALID_FRONTMATTER, tree="", split=True)
        _run(cmd_init_doc, args)
        # Mutate skeleton between runs
        self._skel_path().write_text("garbage\n", encoding="utf-8")
        code, _, err = _run(cmd_init_doc, args)
        self.assertEqual(code, 0, msg=err)
        body = self._skel_path().read_text(encoding="utf-8")
        self.assertNotIn("garbage", body)
        self.assertIn("## Sub-concerns", body)

    def test_init_doc_no_split_default_behaviour_preserved(self):
        # split=False (default) → original Purpose + Structure path
        args = _ns(
            self.devforge,
            frontmatter=_VALID_FRONTMATTER,
            tree="src/components/\n├── x.ts\n",
            split=False,
        )
        code, _, err = _run(cmd_init_doc, args)
        self.assertEqual(code, 0, msg=err)
        body = self._skel_path().read_text(encoding="utf-8")
        self.assertIn("## Structure", body)
        self.assertIn("```text", body)
        self.assertNotIn("## Sub-concerns", body)

    def test_init_doc_split_with_non_concern_tier_returns_2(self):
        args = _ns(
            self.devforge,
            tier="package-overview",
            target="pkg-a",
            frontmatter=_VALID_FRONTMATTER,
            tree="",
            split=True,
        )
        code, _, err = _run(cmd_init_doc, args)
        self.assertEqual(code, 2)
        self.assertIn("--split", err)
        self.assertIn("concern", err)

    def test_init_doc_no_split_attribute_defaults_to_false(self):
        # Older callers that don't pass --split → getattr default False.
        args = argparse.Namespace(
            tier="concern",
            target="pkg-a/components",
            devforge_dir=str(self.devforge),
            frontmatter=_VALID_FRONTMATTER,
            tree="src/components/\n├── x.ts\n",
            # split attribute deliberately absent
        )
        code, _, err = _run(cmd_init_doc, args)
        self.assertEqual(code, 0, msg=err)
        body = self._skel_path().read_text(encoding="utf-8")
        self.assertIn("## Structure", body)
        self.assertNotIn("## Sub-concerns", body)


class CmdSetDocSubconcernsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir(parents=True, exist_ok=True)

    def _skel_path(self) -> Path:
        return self.root / "docs" / "pkg-a" / "components" / "index.md.skeleton"

    def _seed_split_skeleton(self):
        args = _ns(self.devforge, frontmatter=_VALID_FRONTMATTER, tree="", split=True)
        _run(cmd_init_doc, args)

    def test_replaces_placeholder_with_bullets(self):
        self._seed_split_skeleton()
        entries = [
            {"name": "accounts", "purpose_summary": "Account UI", "doc_path": "accounts/index.md"},
            {"name": "catalog", "purpose_summary": "Item catalog", "doc_path": "catalog/index.md"},
        ]
        args = _ns(self.devforge, subconcerns=json.dumps(entries))
        code, _, err = _run(cmd_set_doc_subconcerns, args)
        self.assertEqual(code, 0, msg=err)
        body = self._skel_path().read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: sub-concerns -->", body)
        self.assertIn("- accounts — Account UI ([→](accounts/index.md))", body)
        self.assertIn("- catalog — Item catalog ([→](catalog/index.md))", body)

    def test_idempotent_rerun_replaces_filled_block(self):
        self._seed_split_skeleton()
        first = [{"name": "a", "purpose_summary": "First", "doc_path": "a/index.md"}]
        args = _ns(self.devforge, subconcerns=json.dumps(first))
        _run(cmd_set_doc_subconcerns, args)
        second = [{"name": "b", "purpose_summary": "Second", "doc_path": "b/index.md"}]
        args = _ns(self.devforge, subconcerns=json.dumps(second))
        code, _, err = _run(cmd_set_doc_subconcerns, args)
        self.assertEqual(code, 0, msg=err)
        body = self._skel_path().read_text(encoding="utf-8")
        self.assertNotIn("First", body)
        self.assertIn("Second", body)

    def test_missing_skeleton_returns_2(self):
        args = _ns(self.devforge, subconcerns=json.dumps([]))
        code, _, err = _run(cmd_set_doc_subconcerns, args)
        self.assertEqual(code, 2)
        self.assertIn("init-doc", err)

    def test_invalid_json_returns_2(self):
        self._seed_split_skeleton()
        args = _ns(self.devforge, subconcerns="not json")
        code, _, err = _run(cmd_set_doc_subconcerns, args)
        self.assertEqual(code, 2)
        self.assertIn("subconcerns", err)

    def test_wrong_tier_returns_2(self):
        self._seed_split_skeleton()
        args = _ns(
            self.devforge,
            tier="package-overview",
            subconcerns=json.dumps([]),
        )
        code, _, err = _run(cmd_set_doc_subconcerns, args)
        self.assertEqual(code, 2)
        self.assertIn("set-doc-subconcerns", err)

    def test_empty_entries_writes_empty_block(self):
        # Valid JSON but zero entries → section body becomes empty; placeholder
        # is consumed (no `<!-- TODO: sub-concerns -->`); 3a.5 validator will
        # reject this at validate time, but the setter itself exits 0.
        self._seed_split_skeleton()
        args = _ns(self.devforge, subconcerns=json.dumps([]))
        code, _, err = _run(cmd_set_doc_subconcerns, args)
        self.assertEqual(code, 0, msg=err)
        body = self._skel_path().read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: sub-concerns -->", body)
        self.assertNotIn("- ", body.split("## Sub-concerns")[1])

    def test_doc_without_subconcerns_section_returns_2(self):
        # Init a normal (non-split) concern doc, then try to write subconcerns.
        args = _ns(
            self.devforge,
            frontmatter=_VALID_FRONTMATTER,
            tree="src/components/\n├── x.ts\n",
            split=False,
        )
        _run(cmd_init_doc, args)
        args = _ns(self.devforge, subconcerns=json.dumps([]))
        code, _, err = _run(cmd_set_doc_subconcerns, args)
        self.assertEqual(code, 2)
        self.assertIn("Sub-concerns", err)


class EndToEndSplitFlowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir(parents=True, exist_ok=True)

    def test_init_purpose_subconcerns_render(self):
        target = "pkg-a/components"
        # 1. init-doc --split true
        args = _ns(
            self.devforge,
            target=target,
            frontmatter=_VALID_FRONTMATTER,
            tree="",
            split=True,
        )
        code, _, err = _run(cmd_init_doc, args)
        self.assertEqual(code, 0, msg=err)

        # 2. set-doc-purpose
        args = _ns(self.devforge, target=target, text="Cross-package presentation layer.")
        code, _, err = _run(cmd_set_doc_purpose, args)
        self.assertEqual(code, 0, msg=err)

        # 3. set-doc-subconcerns
        entries = [
            {"name": "accounts", "purpose_summary": "Account UI", "doc_path": "accounts/index.md"},
            {"name": "catalog", "purpose_summary": "Item browse", "doc_path": "catalog/index.md"},
            {"name": "order", "purpose_summary": "Order workflow", "doc_path": "order/index.md"},
        ]
        args = _ns(self.devforge, target=target, subconcerns=json.dumps(entries))
        code, _, err = _run(cmd_set_doc_subconcerns, args)
        self.assertEqual(code, 0, msg=err)

        # 4. render-doc
        args = _ns(self.devforge, target=target, out="")
        code, _, err = _run(cmd_render_doc, args)
        self.assertEqual(code, 0, msg=err)

        # Verify final shape
        final = self.root / "docs" / "pkg-a" / "components" / "index.md"
        self.assertTrue(final.is_file())
        body = final.read_text(encoding="utf-8")
        self.assertIn("Cross-package presentation layer.", body)
        self.assertIn("- accounts — Account UI ([→](accounts/index.md))", body)
        self.assertIn("- catalog — Item browse ([→](catalog/index.md))", body)
        self.assertIn("- order — Order workflow ([→](order/index.md))", body)
        self.assertNotIn("## Structure", body)
        self.assertNotIn("<!-- TODO:", body)
        # Skeleton was renamed away
        self.assertFalse((self.root / "docs" / "pkg-a" / "components" / "index.md.skeleton").exists())


if __name__ == "__main__":
    unittest.main()
