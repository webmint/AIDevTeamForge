"""Tests for F.7b package-tier setters in _doc_setters.py.

Cases:
  1.  init-doc tier=package-overview: writes overview.md.skeleton with
      ## Purpose + ## Concerns + placeholders
  2.  init-doc tier=package-architecture: writes architecture.md.skeleton
      with ## Layers + ## Patterns + placeholders
  3.  init-doc tier=package-overview: --tree NOT required (concern only)
  4.  init-doc rejects unknown tier
  5.  set-doc-purpose accepts tier=package-overview
  6.  set-doc-purpose rejects tier=package-architecture
  7.  set-doc-concerns: replaces placeholder with bullet list
  8.  set-doc-concerns: rejects tier other than package-overview
  9.  set-doc-concerns: invalid JSON → exit 2
 10.  set-doc-concerns: not a JSON list → exit 2
 11.  set-doc-concerns: idempotent re-run replaces existing block
 12.  set-doc-layers: replaces placeholder with bullet list
 13.  set-doc-layers: rejects non-architecture tier
 14.  set-doc-patterns: replaces placeholder with bullet list
 15.  render-doc: package-overview tier renames overview.md.skeleton →
      overview.md
 16.  render-doc: package-architecture tier renames architecture.md.skeleton
       → architecture.md
 17.  end-to-end: init + 2 setters + render produces a valid package
       overview doc
 18.  end-to-end: same for package architecture

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
    cmd_init_doc,
    cmd_render_doc,
    cmd_set_doc_concerns,
    cmd_set_doc_files,
    cmd_set_doc_layers,
    cmd_set_doc_patterns,
    cmd_set_doc_purpose,
    cmd_set_doc_structure,
)


def _run(handler, args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = handler(args)
    return code, out.getvalue(), err.getvalue()


def _ns(devforge: Path, tier: str, target: str = "pkg-a", **overrides) -> argparse.Namespace:
    base = {
        "tier": tier,
        "target": target,
        "devforge_dir": str(devforge),
    }
    base.update(overrides)
    return argparse.Namespace(**base)


class CmdInitDocPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"

    def test_package_overview_skeleton(self):
        args = _ns(
            self.devforge,
            "package-overview",
            target="pkg-a",
            frontmatter=json.dumps(
                {"package": "pkg-a", "last_indexed": "2026-05-08", "source_stamp": "abc"}
            ),
            tree="",
        )
        code, _, _ = _run(cmd_init_doc, args)
        self.assertEqual(code, 0)
        skel = self.root / "docs" / "pkg-a" / "overview.md.skeleton"
        self.assertTrue(skel.is_file())
        content = skel.read_text(encoding="utf-8")
        self.assertIn("## Purpose", content)
        self.assertIn("## Concerns", content)
        self.assertIn("## Files", content)
        self.assertIn("<!-- TODO: purpose -->", content)
        self.assertIn("<!-- TODO: concerns -->", content)
        self.assertIn("<!-- TODO: files -->", content)
        self.assertNotIn("```text", content)  # no fenced tree on overview

    def test_package_architecture_skeleton(self):
        args = _ns(
            self.devforge,
            "package-architecture",
            target="pkg-a",
            frontmatter=json.dumps(
                {"package": "pkg-a", "last_indexed": "2026-05-08", "source_stamp": "abc"}
            ),
            tree="",
        )
        code, _, _ = _run(cmd_init_doc, args)
        self.assertEqual(code, 0)
        skel = self.root / "docs" / "pkg-a" / "architecture.md.skeleton"
        self.assertTrue(skel.is_file())
        content = skel.read_text(encoding="utf-8")
        self.assertIn("## Layers", content)
        self.assertIn("## Patterns", content)
        self.assertIn("<!-- TODO: layers -->", content)
        self.assertIn("<!-- TODO: patterns -->", content)

    def test_package_tier_does_not_require_tree(self):
        args = _ns(
            self.devforge,
            "package-overview",
            frontmatter=json.dumps({"package": "pkg-a"}),
            tree="",
        )
        code, _, _ = _run(cmd_init_doc, args)
        self.assertEqual(code, 0)

    def test_unknown_tier_returns_2(self):
        args = _ns(
            self.devforge,
            "bogus-tier",
            frontmatter=json.dumps({"package": "pkg-a"}),
            tree="",
        )
        code, _, err = _run(cmd_init_doc, args)
        self.assertEqual(code, 2)
        self.assertIn("unknown tier", err)


class CmdSetDocPurposePackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        # init package-overview
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "package-overview",
                frontmatter=json.dumps({"package": "pkg-a"}),
                tree="",
            ),
        )
        # init package-architecture
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "package-architecture",
                frontmatter=json.dumps({"package": "pkg-a"}),
                tree="",
            ),
        )

    def test_purpose_accepts_package_overview(self):
        args = _ns(self.devforge, "package-overview", text="Pkg purpose.")
        code, _, _ = _run(cmd_set_doc_purpose, args)
        self.assertEqual(code, 0)
        skel = self.root / "docs" / "pkg-a" / "overview.md.skeleton"
        self.assertIn("Pkg purpose.", skel.read_text(encoding="utf-8"))

    def test_purpose_rejects_package_architecture(self):
        args = _ns(self.devforge, "package-architecture", text="X")
        code, _, err = _run(cmd_set_doc_purpose, args)
        self.assertEqual(code, 2)
        self.assertIn("set-doc-purpose supports", err)


class CmdSetDocConcernsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "package-overview",
                frontmatter=json.dumps({"package": "pkg-a"}),
                tree="",
            ),
        )

    def test_replaces_placeholder_with_bullets(self):
        args = _ns(
            self.devforge,
            "package-overview",
            concerns=json.dumps(
                [
                    {"name": "alpha", "role": "first concern"},
                    {"name": "beta", "role": "second", "cite": "src/beta/"},
                ]
            ),
        )
        code, _, _ = _run(cmd_set_doc_concerns, args)
        self.assertEqual(code, 0)
        skel = self.root / "docs" / "pkg-a" / "overview.md.skeleton"
        content = skel.read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: concerns -->", content)
        self.assertIn("- alpha — first concern", content)
        self.assertIn("- beta — second; src/beta/", content)

    def test_rejects_other_tier(self):
        args = _ns(self.devforge, "concern", concerns=json.dumps([]))
        code, _, err = _run(cmd_set_doc_concerns, args)
        self.assertEqual(code, 2)
        self.assertIn("set-doc-concerns supports", err)

    def test_invalid_json(self):
        args = _ns(self.devforge, "package-overview", concerns="not-json")
        code, _, err = _run(cmd_set_doc_concerns, args)
        self.assertEqual(code, 2)
        self.assertIn("valid JSON", err)

    def test_not_a_list(self):
        args = _ns(self.devforge, "package-overview", concerns=json.dumps({"k": "v"}))
        code, _, err = _run(cmd_set_doc_concerns, args)
        self.assertEqual(code, 2)
        self.assertIn("JSON array", err)

    def test_idempotent_rerun(self):
        for label in ("X", "Y"):
            args = _ns(
                self.devforge,
                "package-overview",
                concerns=json.dumps([{"name": "alpha", "role": label}]),
            )
            _run(cmd_set_doc_concerns, args)
        skel = self.root / "docs" / "pkg-a" / "overview.md.skeleton"
        content = skel.read_text(encoding="utf-8")
        self.assertIn("- alpha — Y", content)
        self.assertNotIn("- alpha — X", content)


class CmdSetDocFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "package-overview",
                frontmatter=json.dumps({"package": "pkg-a"}),
                tree="",
            ),
        )

    def test_replaces_files_placeholder(self):
        args = _ns(
            self.devforge,
            "package-overview",
            files=json.dumps(
                [
                    {"name": "index.ts", "role": "barrel re-export"},
                    {"name": "env.d.ts", "role": "ambient module decls"},
                ]
            ),
        )
        code, _, _ = _run(cmd_set_doc_files, args)
        self.assertEqual(code, 0)
        skel = self.root / "docs" / "pkg-a" / "overview.md.skeleton"
        content = skel.read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: files -->", content)
        self.assertIn("- index.ts — barrel re-export", content)
        self.assertIn("- env.d.ts — ambient module decls", content)
        # Concerns placeholder unchanged
        self.assertIn("<!-- TODO: concerns -->", content)

    def test_rejects_non_overview_tier(self):
        args = _ns(self.devforge, "concern", files=json.dumps([]))
        code, _, err = _run(cmd_set_doc_files, args)
        self.assertEqual(code, 2)
        self.assertIn("set-doc-files supports", err)


class CmdSetDocLayersPatternsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "package-architecture",
                frontmatter=json.dumps({"package": "pkg-a"}),
                tree="",
            ),
        )

    def test_set_layers(self):
        args = _ns(
            self.devforge,
            "package-architecture",
            layers=json.dumps(
                [
                    {"name": "presentation", "role": "Vue components", "cite": "src/components/"},
                    {"name": "data", "role": "repos", "cite": "src/data/"},
                ]
            ),
        )
        code, _, _ = _run(cmd_set_doc_layers, args)
        self.assertEqual(code, 0)
        skel = self.root / "docs" / "pkg-a" / "architecture.md.skeleton"
        content = skel.read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: layers -->", content)
        self.assertIn("- presentation — Vue components; src/components/", content)
        # Patterns placeholder should remain (only layers replaced)
        self.assertIn("<!-- TODO: patterns -->", content)

    def test_set_layers_rejects_non_architecture_tier(self):
        args = _ns(self.devforge, "concern", layers=json.dumps([]))
        code, _, err = _run(cmd_set_doc_layers, args)
        self.assertEqual(code, 2)
        self.assertIn("set-doc-layers supports", err)

    def test_set_patterns(self):
        args = _ns(
            self.devforge,
            "package-architecture",
            patterns=json.dumps(
                [
                    {"name": "BLoC over Pinia", "rule": "for cross-package state"},
                    {"name": "ref vs reactive", "rule": "primitives use ref()", "cite": "src/lib.ts:5"},
                ]
            ),
        )
        code, _, _ = _run(cmd_set_doc_patterns, args)
        self.assertEqual(code, 0)
        skel = self.root / "docs" / "pkg-a" / "architecture.md.skeleton"
        content = skel.read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: patterns -->", content)
        self.assertIn("- BLoC over Pinia — for cross-package state", content)


class CmdRenderDocPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"

    def test_renames_package_overview(self):
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "package-overview",
                frontmatter=json.dumps({"package": "pkg-a"}),
                tree="",
            ),
        )
        code, _, _ = _run(cmd_render_doc, _ns(self.devforge, "package-overview", out=""))
        self.assertEqual(code, 0)
        skel = self.root / "docs" / "pkg-a" / "overview.md.skeleton"
        doc = self.root / "docs" / "pkg-a" / "overview.md"
        self.assertFalse(skel.is_file())
        self.assertTrue(doc.is_file())

    def test_renames_package_architecture(self):
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "package-architecture",
                frontmatter=json.dumps({"package": "pkg-a"}),
                tree="",
            ),
        )
        code, _, _ = _run(cmd_render_doc, _ns(self.devforge, "package-architecture", out=""))
        self.assertEqual(code, 0)
        doc = self.root / "docs" / "pkg-a" / "architecture.md"
        self.assertTrue(doc.is_file())


class EndToEndPackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"

    def test_overview_pipeline(self):
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "package-overview",
                frontmatter=json.dumps(
                    {"package": "pkg-a", "last_indexed": "2026-05-08", "source_stamp": "stamp1"}
                ),
                tree="",
            ),
        )
        _run(
            cmd_set_doc_purpose,
            _ns(self.devforge, "package-overview", text="Package purpose paragraph."),
        )
        _run(
            cmd_set_doc_concerns,
            _ns(
                self.devforge,
                "package-overview",
                concerns=json.dumps(
                    [
                        {"name": "alpha", "role": "first concern role"},
                        {"name": "beta", "role": "second concern role"},
                    ]
                ),
            ),
        )
        _run(
            cmd_set_doc_files,
            _ns(
                self.devforge,
                "package-overview",
                files=json.dumps(
                    [{"name": "index.ts", "role": "barrel re-export"}]
                ),
            ),
        )
        _run(cmd_render_doc, _ns(self.devforge, "package-overview", out=""))
        doc = self.root / "docs" / "pkg-a" / "overview.md"
        self.assertTrue(doc.is_file())
        text = doc.read_text(encoding="utf-8")
        self.assertIn("Package purpose paragraph.", text)
        self.assertIn("- alpha — first concern role", text)
        self.assertIn("- beta — second concern role", text)
        self.assertIn("- index.ts — barrel re-export", text)
        self.assertNotIn("<!-- TODO: files -->", text)

    def test_architecture_pipeline(self):
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "package-architecture",
                frontmatter=json.dumps(
                    {"package": "pkg-a", "last_indexed": "2026-05-08", "source_stamp": "stamp1"}
                ),
                tree="",
            ),
        )
        _run(
            cmd_set_doc_layers,
            _ns(
                self.devforge,
                "package-architecture",
                layers=json.dumps(
                    [{"name": "presentation", "role": "Vue components"}]
                ),
            ),
        )
        _run(
            cmd_set_doc_patterns,
            _ns(
                self.devforge,
                "package-architecture",
                patterns=json.dumps(
                    [{"name": "BLoC over Pinia", "rule": "cross-package state"}]
                ),
            ),
        )
        _run(cmd_render_doc, _ns(self.devforge, "package-architecture", out=""))
        doc = self.root / "docs" / "pkg-a" / "architecture.md"
        self.assertTrue(doc.is_file())
        text = doc.read_text(encoding="utf-8")
        self.assertIn("- presentation — Vue components", text)
        self.assertIn("- BLoC over Pinia — cross-package state", text)


if __name__ == "__main__":
    unittest.main()
