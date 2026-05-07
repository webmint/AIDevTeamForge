"""Tests for _doc_setters.py — F.4 concern-tier setters + render-doc (v0).

Cases:
  1.  init-doc: creates state slot with frontmatter
  2.  init-doc: invalid JSON → exit 2
  3.  init-doc: idempotent (second call overwrites frontmatter cleanly)
  4.  set-doc-purpose: stores text in slot
  5.  set-doc-purpose: works on existing slot
  6.  set-doc-structure: appends ` — <annotation>` to leaves
  7.  set-doc-structure: skips canonical-aggregator filenames
  8.  set-doc-structure: skips path-header line + directory entries
  9.  set-doc-structure: invalid annotations JSON → exit 2
  (Hazards dropped 2026-05-07 — moved to /audit; concern docs ship
   only ## Purpose + ## Structure)
 10.  render-doc: writes valid markdown to docs/<target>/index.md
 11.  render-doc: emits frontmatter + 2 sections (Purpose + Structure)
 12.  render-doc: missing slot → exit 2
 15.  render-doc: --out override path used
 16.  end-to-end: init + 3 setters + render → output validates against F.5

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
    _annotate_tree,
    _load_state,
    cmd_init_doc,
    cmd_render_doc,
    cmd_set_doc_purpose,
    cmd_set_doc_structure,
)
from _generate_docs._validate_doc import _validate_concern_doc  # noqa: E402


def _run(handler, args: argparse.Namespace):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = handler(args)
    return code, out.getvalue(), err.getvalue()


class AnnotateTreeTests(unittest.TestCase):
    def test_appends_annotation_to_leaves(self):
        tree = (
            "src/order/\n"
            "├── OrderFooter.ts\n"
            "└── OrderLines.ts\n"
        )
        annotated = _annotate_tree(
            tree,
            {"OrderFooter.ts": "submit/cancel handler", "OrderLines.ts": "line editor"},
        )
        self.assertIn("OrderFooter.ts — submit/cancel handler", annotated)
        self.assertIn("OrderLines.ts — line editor", annotated)
        # path header untouched
        self.assertEqual(annotated.split("\n")[0], "src/order/")

    def test_skips_canonical_aggregators(self):
        tree = "src/lib/\n├── mod.rs\n└── inner.rs\n"
        annotated = _annotate_tree(
            tree, {"mod.rs": "should-be-skipped", "inner.rs": "kept"}
        )
        self.assertNotIn("should-be-skipped", annotated)
        self.assertIn("inner.rs — kept", annotated)

    def test_skips_lines_without_connector(self):
        # A bare directory line without leaf connector should not be touched.
        tree = (
            "src/order/\n"
            "├── nested\n"
            "│   └── inner.ts\n"
            "└── leaf.ts\n"
        )
        annotated = _annotate_tree(tree, {"nested": "ANNO", "leaf.ts": "L"})
        # `nested` IS a leaf-style line in this snippet (├── nested) — picks up annotation.
        # but path header (line 1) does not.
        self.assertEqual(annotated.split("\n")[0], "src/order/")
        self.assertIn("leaf.ts — L", annotated)


class CmdInitDocTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.devforge = Path(self.tmp.name) / ".devforge"

    def test_creates_state_slot_with_frontmatter(self):
        args = argparse.Namespace(
            tier="concern",
            target="pkg-a/order",
            devforge_dir=str(self.devforge),
            frontmatter=json.dumps(
                {
                    "concern": "order",
                    "package": "pkg-a",
                    "files": 3,
                    "source_stamp": "abc",
                    "last_indexed": "2026-05-07",
                }
            ),
        )
        code, _, _ = _run(cmd_init_doc, args)
        self.assertEqual(code, 0)
        state = _load_state(self.devforge)
        self.assertIn("concern:pkg-a/order", state["docs"])
        slot = state["docs"]["concern:pkg-a/order"]
        self.assertEqual(slot["frontmatter"]["concern"], "order")

    def test_invalid_json_returns_2(self):
        args = argparse.Namespace(
            tier="concern",
            target="pkg-a/order",
            devforge_dir=str(self.devforge),
            frontmatter="not-json",
        )
        code, _, err = _run(cmd_init_doc, args)
        self.assertEqual(code, 2)
        self.assertIn("valid JSON", err)

    def test_second_call_overwrites_frontmatter(self):
        for stamp in ("v1", "v2"):
            args = argparse.Namespace(
                tier="concern",
                target="pkg-a/order",
                devforge_dir=str(self.devforge),
                frontmatter=json.dumps({"concern": "order", "source_stamp": stamp}),
            )
            _run(cmd_init_doc, args)
        state = _load_state(self.devforge)
        self.assertEqual(state["docs"]["concern:pkg-a/order"]["frontmatter"]["source_stamp"], "v2")

    def test_reinit_clears_sections(self):
        """init-doc on an existing slot wipes Purpose/Structure.

        Otherwise a re-run would carry stale prior content. Forcing the
        orchestrator to clean state before init-doc is bad UX — init-doc
        owns the reset.
        """
        target = "pkg-a/order"
        first_init = argparse.Namespace(
            tier="concern",
            target=target,
            devforge_dir=str(self.devforge),
            frontmatter=json.dumps({"concern": "order", "source_stamp": "v1"}),
        )
        _run(cmd_init_doc, first_init)
        # Populate Purpose
        from _generate_docs._doc_setters import (  # noqa: E402
            cmd_set_doc_purpose,
        )
        _run(
            cmd_set_doc_purpose,
            argparse.Namespace(
                tier="concern",
                target=target,
                devforge_dir=str(self.devforge),
                text="prior purpose",
            ),
        )
        # Re-init
        second_init = argparse.Namespace(
            tier="concern",
            target=target,
            devforge_dir=str(self.devforge),
            frontmatter=json.dumps({"concern": "order", "source_stamp": "v2"}),
        )
        _run(cmd_init_doc, second_init)
        slot = _load_state(self.devforge)["docs"][f"concern:{target}"]
        self.assertEqual(slot["sections"]["Purpose"], "")
        self.assertEqual(slot["sections"]["Structure"], "")
        self.assertNotIn("Hazards", slot["sections"])
        self.assertEqual(slot["frontmatter"]["source_stamp"], "v2")


class CmdSettersTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.devforge = Path(self.tmp.name) / ".devforge"
        # init the slot first
        init_args = argparse.Namespace(
            tier="concern",
            target="pkg-a/order",
            devforge_dir=str(self.devforge),
            frontmatter=json.dumps({"concern": "order"}),
        )
        _run(cmd_init_doc, init_args)

    def _make_args(self, **overrides):
        base = {
            "tier": "concern",
            "target": "pkg-a/order",
            "devforge_dir": str(self.devforge),
        }
        base.update(overrides)
        return argparse.Namespace(**base)

    def test_set_purpose_stores_text(self):
        args = self._make_args(text="Cross-cutting order flow.")
        code, _, _ = _run(cmd_set_doc_purpose, args)
        self.assertEqual(code, 0)
        state = _load_state(self.devforge)
        self.assertEqual(
            state["docs"]["concern:pkg-a/order"]["sections"]["Purpose"],
            "Cross-cutting order flow.",
        )

    def test_set_structure_annotates_tree(self):
        tree = "src/order/\n├── X.ts\n└── Y.ts\n"
        args = self._make_args(
            tree=tree,
            annotations=json.dumps({"X.ts": "x desc", "Y.ts": "y desc"}),
        )
        code, _, _ = _run(cmd_set_doc_structure, args)
        self.assertEqual(code, 0)
        state = _load_state(self.devforge)
        struct = state["docs"]["concern:pkg-a/order"]["sections"]["Structure"]
        self.assertIn("X.ts — x desc", struct)
        self.assertIn("Y.ts — y desc", struct)

    def test_set_structure_invalid_annotations_returns_2(self):
        args = self._make_args(tree="src/order/\n", annotations="not-json")
        code, _, err = _run(cmd_set_doc_structure, args)
        self.assertEqual(code, 2)
        self.assertIn("valid JSON", err)



class CmdRenderDocTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"

    def _run_full_pipeline(self):
        # init
        _run(
            cmd_init_doc,
            argparse.Namespace(
                tier="concern",
                target="pkg-a/order",
                devforge_dir=str(self.devforge),
                frontmatter=json.dumps(
                    {
                        "concern": "order",
                        "package": "pkg-a",
                        "files": 2,
                        "source_stamp": "stamp123",
                        "last_indexed": "2026-05-07",
                    }
                ),
            ),
        )
        # purpose
        _run(
            cmd_set_doc_purpose,
            argparse.Namespace(
                tier="concern",
                target="pkg-a/order",
                devforge_dir=str(self.devforge),
                text="Order flow.",
            ),
        )
        # structure
        _run(
            cmd_set_doc_structure,
            argparse.Namespace(
                tier="concern",
                target="pkg-a/order",
                devforge_dir=str(self.devforge),
                tree="src/order/\n├── A.ts\n└── B.ts\n",
                annotations=json.dumps({"A.ts": "a desc", "B.ts": "b desc"}),
            ),
        )

    def test_render_writes_doc(self):
        self._run_full_pipeline()
        out_path = self.root / "custom-out" / "doc.md"
        args = argparse.Namespace(
            tier="concern",
            target="pkg-a/order",
            devforge_dir=str(self.devforge),
            out=str(out_path),
        )
        code, stdout, _ = _run(cmd_render_doc, args)
        self.assertEqual(code, 0)
        self.assertTrue(out_path.is_file())
        text = out_path.read_text(encoding="utf-8")
        self.assertIn("---", text)
        self.assertIn("source_stamp:", text)
        self.assertIn("## Purpose", text)
        self.assertIn("## Structure", text)
        # Hazards moved to /audit; concern docs no longer carry that section
        self.assertNotIn("## Hazards", text)
        self.assertIn("A.ts — a desc", text)

    def test_missing_slot_returns_2(self):
        args = argparse.Namespace(
            tier="concern",
            target="pkg-x/missing",
            devforge_dir=str(self.devforge),
            out="",
        )
        code, _, err = _run(cmd_render_doc, args)
        self.assertEqual(code, 2)
        self.assertIn("no state for", err)

    def test_default_out_path_under_docs_dir(self):
        self._run_full_pipeline()
        args = argparse.Namespace(
            tier="concern",
            target="pkg-a/order",
            devforge_dir=str(self.devforge),
            out="",
        )
        code, _, _ = _run(cmd_render_doc, args)
        self.assertEqual(code, 0)
        expected = self.root / "docs" / "pkg-a" / "order" / "index.md"
        self.assertTrue(expected.is_file())


class EndToEndValidateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        # Source files for cite-back resolution
        src = self.root / "pkg-a" / "src" / "order"
        src.mkdir(parents=True)
        (src / "A.ts").write_text("a\n" * 20, encoding="utf-8")
        (src / "B.ts").write_text("b\n" * 20, encoding="utf-8")

    def test_init_setters_render_then_validate_passes(self):
        _run(
            cmd_init_doc,
            argparse.Namespace(
                tier="concern",
                target="pkg-a/src/order",
                devforge_dir=str(self.devforge),
                frontmatter=json.dumps(
                    {
                        "concern": "order",
                        "package": "pkg-a",
                        "files": 2,
                        "source_stamp": "stamp123",
                        "last_indexed": "2026-05-07",
                    }
                ),
            ),
        )
        _run(
            cmd_set_doc_purpose,
            argparse.Namespace(
                tier="concern",
                target="pkg-a/src/order",
                devforge_dir=str(self.devforge),
                text="Order flow for pkg-a.",
            ),
        )
        _run(
            cmd_set_doc_structure,
            argparse.Namespace(
                tier="concern",
                target="pkg-a/src/order",
                devforge_dir=str(self.devforge),
                tree="src/order/\n├── A.ts\n└── B.ts\n",
                annotations=json.dumps({"A.ts": "alpha", "B.ts": "beta"}),
            ),
        )
        _run(
            cmd_render_doc,
            argparse.Namespace(
                tier="concern",
                target="pkg-a/src/order",
                devforge_dir=str(self.devforge),
                out="",
            ),
        )
        doc_path = self.root / "docs" / "pkg-a" / "src" / "order" / "index.md"
        self.assertTrue(doc_path.is_file())
        errors = _validate_concern_doc(doc_path, "pkg-a/src/order", self.root)
        self.assertEqual(errors, [], f"validate-doc errors: {errors}")


if __name__ == "__main__":
    unittest.main()
