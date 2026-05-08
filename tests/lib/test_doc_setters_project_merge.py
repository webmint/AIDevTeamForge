"""Tests for _doc_setters.py project-tier section coexistence merge — Fix 2.

Cases:
  1.  Cold start (no file): init-doc emits fresh skeleton verbatim
  2.  Existing file with constitute stub anchors only → init merges:
      adds Purpose + Packages placeholders, preserves stub anchors
  3.  Existing file with both stubs + filled generate-docs sections →
      init resets owned anchors to placeholders, preserves stubs
  4.  Custom user anchor (neither stub nor owned) preserved verbatim
  5.  Owned anchors NOT in existing file get appended in declared order
  6.  Architecture-tier merge: Layers + Cross-Cuts owned, Architectural
      Decisions stub preserved
  7.  Frontmatter merge: existing keys preserved + fresh keys override
  8.  Existing file with malformed frontmatter → cold-write fresh skeleton
  9.  Idempotent re-run: second init-doc produces same output as first

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
    _PROJECT_ARCHITECTURE_OWNED_ANCHORS,
    _PROJECT_OVERVIEW_OWNED_ANCHORS,
    _merge_project_skeleton,
    cmd_init_doc,
)


_FRESH_OVERVIEW_SKELETON = (
    "---\n"
    "project: my-proj\n"
    "source_stamp: fresh1234\n"
    "last_indexed: 2026-05-08\n"
    "---\n"
    "\n"
    "# my-proj\n\n"
    "## Purpose\n\n"
    "<!-- TODO: purpose -->\n\n"
    "## Packages\n\n"
    "<!-- TODO: packages -->\n"
)


_CONSTITUTE_STUB_OVERVIEW = """---
project: my-proj
last_indexed: 2026-05-01
---

# my-proj

## What this project is for

_Populated by `constitute` (goals, users, scope)._

## How it's used

_Populated by tech-writer as the project grows._
"""


class MergeProjectSkeletonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.doc_path = self.root / "docs" / "overview.md"
        self.doc_path.parent.mkdir(parents=True, exist_ok=True)

    def test_cold_start_returns_fresh_verbatim(self):
        out = _merge_project_skeleton(
            self.doc_path, _FRESH_OVERVIEW_SKELETON, _PROJECT_OVERVIEW_OWNED_ANCHORS
        )
        self.assertEqual(out, _FRESH_OVERVIEW_SKELETON)

    def test_constitute_stubs_preserved_owned_anchors_added(self):
        self.doc_path.write_text(_CONSTITUTE_STUB_OVERVIEW, encoding="utf-8")
        out = _merge_project_skeleton(
            self.doc_path, _FRESH_OVERVIEW_SKELETON, _PROJECT_OVERVIEW_OWNED_ANCHORS
        )
        # Constitute stubs preserved
        self.assertIn("## What this project is for", out)
        self.assertIn("Populated by `constitute`", out)
        self.assertIn("## How it's used", out)
        # Owned anchors appended with placeholders
        self.assertIn("## Purpose", out)
        self.assertIn("<!-- TODO: purpose -->", out)
        self.assertIn("## Packages", out)
        self.assertIn("<!-- TODO: packages -->", out)

    def test_existing_owned_anchor_reset_to_placeholder(self):
        existing = (
            "---\n"
            "project: my-proj\n"
            "last_indexed: 2025-01-01\n"
            "---\n"
            "\n"
            "# my-proj\n\n"
            "## What this project is for\n\nLong-form decisions.\n\n"
            "## Purpose\n\nStale text from previous run.\n\n"
            "## Packages\n\nStale package list.\n"
        )
        self.doc_path.write_text(existing, encoding="utf-8")
        out = _merge_project_skeleton(
            self.doc_path, _FRESH_OVERVIEW_SKELETON, _PROJECT_OVERVIEW_OWNED_ANCHORS
        )
        # Stale owned-anchor body replaced with placeholder
        self.assertNotIn("Stale text from previous run", out)
        self.assertNotIn("Stale package list", out)
        self.assertIn("<!-- TODO: purpose -->", out)
        self.assertIn("<!-- TODO: packages -->", out)
        # Constitute stub preserved
        self.assertIn("Long-form decisions.", out)

    def test_custom_user_anchor_preserved_verbatim(self):
        existing = (
            "---\n"
            "project: my-proj\n"
            "---\n"
            "\n"
            "# my-proj\n\n"
            "## My custom thoughts\n\nUser-authored content here.\n\n"
            "## Purpose\n\nold purpose.\n"
        )
        self.doc_path.write_text(existing, encoding="utf-8")
        out = _merge_project_skeleton(
            self.doc_path, _FRESH_OVERVIEW_SKELETON, _PROJECT_OVERVIEW_OWNED_ANCHORS
        )
        self.assertIn("## My custom thoughts", out)
        self.assertIn("User-authored content here.", out)
        # Owned anchors still reset
        self.assertIn("<!-- TODO: purpose -->", out)
        self.assertIn("<!-- TODO: packages -->", out)

    def test_owned_anchors_appended_in_declared_order_when_missing(self):
        # Stub has only constitute anchors → both Purpose + Packages get appended.
        # Declared order is (Purpose, Packages) per _PROJECT_OVERVIEW_OWNED_ANCHORS.
        self.doc_path.write_text(_CONSTITUTE_STUB_OVERVIEW, encoding="utf-8")
        out = _merge_project_skeleton(
            self.doc_path, _FRESH_OVERVIEW_SKELETON, _PROJECT_OVERVIEW_OWNED_ANCHORS
        )
        i_purpose = out.index("## Purpose")
        i_packages = out.index("## Packages")
        self.assertLess(i_purpose, i_packages)

    def test_architecture_tier_merge(self):
        existing = (
            "---\n"
            "project: my-proj\n"
            "---\n"
            "\n"
            "# my-proj architecture\n\n"
            "## Architectural Decisions\n\n_Populated by `constitute`._\n\n"
            "## Layer Boundaries & Dependency Rules\n\n_Populated by `constitute`._\n"
        )
        self.doc_path.write_text(existing, encoding="utf-8")
        fresh_arch = (
            "---\n"
            "project: my-proj\n"
            "source_stamp: fresh\n"
            "---\n"
            "\n"
            "# my-proj architecture\n\n"
            "## Layers\n\n<!-- TODO: layers -->\n\n"
            "## Cross-Cuts\n\n<!-- TODO: cross-cuts -->\n"
        )
        out = _merge_project_skeleton(
            self.doc_path, fresh_arch, _PROJECT_ARCHITECTURE_OWNED_ANCHORS
        )
        self.assertIn("## Architectural Decisions", out)
        self.assertIn("## Layer Boundaries & Dependency Rules", out)
        self.assertIn("## Layers", out)
        self.assertIn("<!-- TODO: layers -->", out)
        self.assertIn("## Cross-Cuts", out)
        self.assertIn("<!-- TODO: cross-cuts -->", out)

    def test_frontmatter_merge_existing_keys_kept_fresh_overrides(self):
        existing = (
            "---\n"
            "project: my-proj\n"
            "extra_constitute_key: keep-me\n"
            "last_indexed: 2025-01-01\n"
            "---\n"
            "\n"
            "# my-proj\n\n## What this project is for\n\nstub\n"
        )
        self.doc_path.write_text(existing, encoding="utf-8")
        out = _merge_project_skeleton(
            self.doc_path, _FRESH_OVERVIEW_SKELETON, _PROJECT_OVERVIEW_OWNED_ANCHORS
        )
        self.assertIn("extra_constitute_key: keep-me", out)  # existing preserved
        self.assertIn("last_indexed: 2026-05-08", out)  # fresh overrides
        self.assertIn("source_stamp: fresh1234", out)  # fresh adds

    def test_malformed_frontmatter_falls_back_to_cold_write(self):
        self.doc_path.write_text("not even frontmatter\n", encoding="utf-8")
        out = _merge_project_skeleton(
            self.doc_path, _FRESH_OVERVIEW_SKELETON, _PROJECT_OVERVIEW_OWNED_ANCHORS
        )
        self.assertEqual(out, _FRESH_OVERVIEW_SKELETON)

    def test_idempotent_rerun_stable_output(self):
        # First run merges stub + adds owned anchors
        self.doc_path.write_text(_CONSTITUTE_STUB_OVERVIEW, encoding="utf-8")
        out1 = _merge_project_skeleton(
            self.doc_path, _FRESH_OVERVIEW_SKELETON, _PROJECT_OVERVIEW_OWNED_ANCHORS
        )
        # Plant the merged result + run again — should produce the SAME merged output.
        self.doc_path.write_text(out1, encoding="utf-8")
        out2 = _merge_project_skeleton(
            self.doc_path, _FRESH_OVERVIEW_SKELETON, _PROJECT_OVERVIEW_OWNED_ANCHORS
        )
        self.assertEqual(out1, out2)


class CmdInitDocProjectMergeTests(unittest.TestCase):
    """End-to-end: cmd_init_doc with project-tier preserves stub anchors."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir(parents=True, exist_ok=True)

    def _ns(self, **overrides):
        base = {
            "tier": "project-overview",
            "target": "my-proj",
            "devforge_dir": str(self.devforge),
            "frontmatter": json.dumps(
                {"project": "my-proj", "source_stamp": "abc", "last_indexed": "2026-05-08"}
            ),
            "tree": "",
            "split": False,
        }
        base.update(overrides)
        return argparse.Namespace(**base)

    def _run(self, args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cmd_init_doc(args)
        return code, out.getvalue(), err.getvalue()

    def test_existing_constitute_stubs_preserved_through_init(self):
        existing = self.root / "docs" / "overview.md"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.write_text(_CONSTITUTE_STUB_OVERVIEW, encoding="utf-8")
        code, _, err = self._run(self._ns())
        self.assertEqual(code, 0, msg=err)
        skel = self.root / "docs" / "overview.md.skeleton"
        body = skel.read_text(encoding="utf-8")
        self.assertIn("## What this project is for", body)
        self.assertIn("Populated by `constitute`", body)
        self.assertIn("## Purpose", body)
        self.assertIn("<!-- TODO: purpose -->", body)
        self.assertIn("## Packages", body)
        self.assertIn("<!-- TODO: packages -->", body)


if __name__ == "__main__":
    unittest.main()
