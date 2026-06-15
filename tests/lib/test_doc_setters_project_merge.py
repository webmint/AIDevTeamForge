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
  8.  Existing file with no frontmatter (install-shipped stub) → merge
      treats whole text as body, owned anchors appended, fresh frontmatter applied
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
from typing import Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _generate_docs._doc_setters._skeletons import (  # noqa: E402
    _PROJECT_ARCHITECTURE_OWNED_ANCHORS,
    _PROJECT_OVERVIEW_OWNED_ANCHORS,
)
from _generate_docs._doc_setters._cmds_package import (  # noqa: E402
    _merge_project_skeleton,
)
from _generate_docs._doc_setters import (  # noqa: E402
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

    def test_no_frontmatter_treated_as_body(self):
        # Stub files at src/docs/overview.md ship WITHOUT frontmatter
        # (install copies them verbatim; constitute populates frontmatter
        # later). Merger must treat the whole text as body so stub
        # content (H1 + intro prose + section anchors) survives.
        self.doc_path.write_text(
            "# {{PROJECT_NAME}}\n\n## What this project is for\n\nstub.\n",
            encoding="utf-8",
        )
        out = _merge_project_skeleton(
            self.doc_path, _FRESH_OVERVIEW_SKELETON, _PROJECT_OVERVIEW_OWNED_ANCHORS
        )
        # Stub content preserved
        self.assertIn("{{PROJECT_NAME}}", out)
        self.assertIn("## What this project is for", out)
        self.assertIn("stub.", out)
        # Owned anchors appended with placeholders
        self.assertIn("## Purpose", out)
        self.assertIn("<!-- TODO: purpose -->", out)
        self.assertIn("## Packages", out)
        self.assertIn("<!-- TODO: packages -->", out)
        # Fresh frontmatter applied (existing had none to merge from)
        self.assertIn("project: my-proj", out)
        self.assertIn("source_stamp: fresh1234", out)

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


# ── Declared-order insertion tests (Unit B — JUDGMENT-LAYER-PLAN Step 0) ────


# A controlled 4-anchor tuple for isolation — independent of the production
# tuple — declared-order insertion is required so that any new owned-anchor
# additions land in their declared position relative to anchors already in
# the body, not appended at end. The fix is anchor-agnostic.
_TEST_ANCHORS: Tuple[Tuple[str, str], ...] = (
    ("A", "<!-- A -->"),
    ("B", "<!-- B -->"),
    ("C", "<!-- C -->"),
    ("D", "<!-- D -->"),
)

_FRESH_TEST_SKELETON = (
    "---\n"
    "project: my-proj\n"
    "source_stamp: s1\n"
    "---\n"
    "\n"
    "# my-proj\n\n"
    "## A\n\n<!-- A -->\n\n"
    "## B\n\n<!-- B -->\n\n"
    "## C\n\n<!-- C -->\n\n"
    "## D\n\n<!-- D -->\n"
)


def _body_with_anchors(*sections: str) -> str:
    """Build a minimal existing-file body containing only the given section names."""
    parts = ["# my-proj"]
    for sec in sections:
        placeholder = dict(_TEST_ANCHORS).get(sec, f"<!-- {sec} content -->")
        parts.append(f"\n## {sec}\n\n{placeholder}")
    return "\n".join(parts) + "\n"


def _existing_file(doc_path: Path, *sections: str) -> None:
    """Write a minimal existing doc file with frontmatter + given sections."""
    body = _body_with_anchors(*sections)
    content = "---\nproject: my-proj\nlast_indexed: 2025-01-01\n---\n\n" + body
    doc_path.write_text(content, encoding="utf-8")


class DeclaredOrderInsertionTests(unittest.TestCase):
    """Unit B — declared-order insertion of missing owned anchors."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.doc_path = self.root / "docs" / "overview.md"
        self.doc_path.parent.mkdir(parents=True, exist_ok=True)

    def test_missing_middle_anchor_inserted_before_next_existing(self):
        """Body has A, C, D (B missing) → B inserted before C."""
        _existing_file(self.doc_path, "A", "C", "D")
        out = _merge_project_skeleton(self.doc_path, _FRESH_TEST_SKELETON, _TEST_ANCHORS)

        self.assertIn("## A", out)
        self.assertIn("## B", out)
        self.assertIn("## C", out)
        self.assertIn("## D", out)

        i_b = out.index("## B")
        i_c = out.index("## C")
        i_a = out.index("## A")
        # B must appear after A and before C (declared order).
        self.assertLess(i_a, i_b)
        self.assertLess(i_b, i_c)

    def test_missing_last_anchor_appended_at_end(self):
        """Body has A, B, C (D missing) → D appended at end."""
        _existing_file(self.doc_path, "A", "B", "C")
        out = _merge_project_skeleton(self.doc_path, _FRESH_TEST_SKELETON, _TEST_ANCHORS)

        self.assertIn("## D", out)

        i_c = out.index("## C")
        i_d = out.index("## D")
        self.assertLess(i_c, i_d)

    def test_all_missing_series_inserted_before_next_existing(self):
        """Body has A, D (B and C missing) → output order is A, B, C, D."""
        _existing_file(self.doc_path, "A", "D")
        out = _merge_project_skeleton(self.doc_path, _FRESH_TEST_SKELETON, _TEST_ANCHORS)

        self.assertIn("## B", out)
        self.assertIn("## C", out)

        i_a = out.index("## A")
        i_b = out.index("## B")
        i_c = out.index("## C")
        i_d = out.index("## D")
        self.assertLess(i_a, i_b)
        self.assertLess(i_b, i_c)
        self.assertLess(i_c, i_d)

    def test_cold_start_unchanged_regression(self):
        """Cold start (doc_path does not exist) → fresh_skeleton returned verbatim."""
        # doc_path must NOT exist for this test.
        self.assertFalse(self.doc_path.exists())
        out = _merge_project_skeleton(self.doc_path, _FRESH_TEST_SKELETON, _TEST_ANCHORS)
        self.assertEqual(out, _FRESH_TEST_SKELETON)

    def test_prefix_match_heading_not_treated_as_anchor_present(self):
        """Finding 1 regression: a heading that PREFIX-matches an owned anchor
        must NOT suppress insertion of the real anchor.

        Scenario: existing body has '## Key Commands Reference' (a non-owned
        heading that prefix-matches the owned anchor 'Key Commands').  The body
        does NOT contain '## Key Commands'.  Expected: merge MUST insert
        '## Key Commands' at the correct declared-order position; the spurious
        '## Key Commands Reference' heading must be preserved verbatim.

        Implemented using _TEST_ANCHORS with a short anchor ('B') whose name is
        a prefix of a non-owned heading ('B Reference') present in the file.
        """
        # Build a body that has "## B Reference" (non-owned) but NOT "## B".
        # Also include A, C, D so we have a well-defined insertion target.
        body = (
            "---\n"
            "project: my-proj\n"
            "last_indexed: 2025-01-01\n"
            "---\n"
            "\n"
            "# my-proj\n\n"
            "## A\n\n<!-- A -->\n\n"
            "## B Reference\n\nSome non-owned content.\n\n"
            "## C\n\n<!-- C -->\n\n"
            "## D\n\n<!-- D -->\n"
        )
        self.doc_path.write_text(body, encoding="utf-8")
        out = _merge_project_skeleton(self.doc_path, _FRESH_TEST_SKELETON, _TEST_ANCHORS)

        # '## B' MUST be inserted (not suppressed by the prefix match).
        self.assertIn("## B\n", out)
        # The non-owned heading must be preserved verbatim.
        self.assertIn("## B Reference", out)
        self.assertIn("Some non-owned content.", out)
        # '## B' must appear BEFORE '## C' (declared order).
        i_b = out.index("## B\n")
        i_c = out.index("## C\n")
        self.assertLess(i_b, i_c)

    def test_multi_pattern_missing_then_existing_then_missing(self):
        """Body has B, C (A and D missing) → output order is A, B, C, D."""
        _existing_file(self.doc_path, "B", "C")
        out = _merge_project_skeleton(self.doc_path, _FRESH_TEST_SKELETON, _TEST_ANCHORS)

        self.assertIn("## A", out)
        self.assertIn("## D", out)

        i_a = out.index("## A")
        i_b = out.index("## B")
        i_c = out.index("## C")
        i_d = out.index("## D")
        # A inserted before B (A is missing, next existing is B).
        self.assertLess(i_a, i_b)
        # D appended after C (D is missing, no later anchors exist in body).
        self.assertLess(i_c, i_d)


if __name__ == "__main__":
    unittest.main()
