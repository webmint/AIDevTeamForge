"""Tests for F.8b project-tier setters in _doc_setters.py.

Cases:
  1.  init-doc tier=project-overview: writes docs/overview.md.skeleton
      (no per-target subdir)
  2.  init-doc tier=project-architecture: writes docs/architecture.md.skeleton
  3.  set-doc-purpose: tier=project-overview accepted
  4.  set-doc-purpose: tier=project-architecture rejected
  5.  set-doc-packages: replaces placeholder with bullet list
  6.  set-doc-packages: rejects non-overview tier
  7.  set-doc-packages: invalid JSON → exit 2
  8.  set-doc-layers: now accepts tier=project-architecture
  9.  set-doc-cross-cuts: replaces placeholder with bullet list
 10.  set-doc-cross-cuts: rejects non-architecture tier
 11.  render-doc: project-overview renames docs/overview.md.skeleton →
       docs/overview.md (NO target subdir)
 12.  render-doc: project-architecture renames docs/architecture.md.skeleton
       → docs/architecture.md
 13.  end-to-end: project-overview pipeline
 14.  end-to-end: project-architecture pipeline

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import io
import json
import os
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
    cmd_set_architecture_conventions,
    cmd_set_architecture_cross_cuts_detailed,
    cmd_set_architecture_dependency_direction_rules,
    cmd_set_architecture_dependency_overview_mermaid,
    cmd_set_architecture_module_structure,
    cmd_set_architecture_overview_narrative,
    cmd_set_architecture_patterns,
    cmd_set_doc_cross_cuts,
    cmd_set_doc_layers,
    cmd_set_doc_packages,
    cmd_set_doc_purpose,
    cmd_set_overview_application_routes,
    cmd_set_overview_cross_module_deps,
    cmd_set_overview_entry_points,
    cmd_set_overview_key_commands,
    cmd_set_overview_module_map,
    cmd_set_overview_navigation_guards,
    cmd_set_overview_project_structure_annotations,
    cmd_set_overview_project_structure_tree,
    cmd_set_overview_suggested_research_starts,
    cmd_set_overview_tech_stack,
    cmd_set_overview_test_files,
)


def _run(handler, args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = handler(args)
    return code, out.getvalue(), err.getvalue()


def _ns(devforge: Path, tier: str, target: str = "my-project", **overrides):
    base = {
        "tier": tier,
        "target": target,
        "devforge_dir": str(devforge),
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _section_body(content: str, heading: str) -> str:
    """Extract body text under `## <heading>` up to the next `## ` (level-2)
    heading or EOF. Walks line-by-line so `### subsection` headings INSIDE
    the section (Phase 3 Patterns / Cross-Cuts use them) are preserved
    rather than incorrectly cutting the section short — naive
    `content.split("##")` does that.
    """
    in_section = False
    out_lines = []
    for line in content.split("\n"):
        if line.startswith(f"## {heading}"):
            in_section = True
            continue
        if in_section and line.startswith("## ") and not line.startswith("### "):
            break
        if in_section:
            out_lines.append(line)
    return "\n".join(out_lines)


class CmdInitDocProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"

    def test_project_overview_skeleton_no_subdir(self):
        args = _ns(
            self.devforge,
            "project-overview",
            frontmatter=json.dumps(
                {"project": "my-project", "last_indexed": "2026-05-08", "source_stamp": "x"}
            ),
            tree="",
        )
        code, _, _ = _run(cmd_init_doc, args)
        self.assertEqual(code, 0)
        # Project tier doc lives directly under docs/, NOT docs/<target>/
        skel = self.root / "docs" / "overview.md.skeleton"
        self.assertTrue(skel.is_file())
        self.assertFalse((self.root / "docs" / "my-project").exists())
        content = skel.read_text(encoding="utf-8")
        self.assertIn("# my-project", content)
        self.assertIn("## Purpose", content)
        self.assertIn("## Packages", content)
        self.assertIn("<!-- TODO: purpose -->", content)
        self.assertIn("<!-- TODO: packages -->", content)

    def test_project_architecture_skeleton(self):
        args = _ns(
            self.devforge,
            "project-architecture",
            frontmatter=json.dumps(
                {"project": "my-project", "last_indexed": "2026-05-08", "source_stamp": "x"}
            ),
            tree="",
        )
        code, _, _ = _run(cmd_init_doc, args)
        self.assertEqual(code, 0)
        skel = self.root / "docs" / "architecture.md.skeleton"
        self.assertTrue(skel.is_file())
        content = skel.read_text(encoding="utf-8")
        self.assertIn("## Layers", content)
        self.assertIn("## Cross-Cuts", content)
        self.assertIn("<!-- TODO: layers -->", content)
        self.assertIn("<!-- TODO: cross-cuts -->", content)


class CmdSetDocPurposeProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-project"}),
                tree="",
            ),
        )
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-architecture",
                frontmatter=json.dumps({"project": "my-project"}),
                tree="",
            ),
        )

    def test_purpose_accepts_project_overview(self):
        args = _ns(self.devforge, "project-overview", text="Project purpose.")
        code, _, _ = _run(cmd_set_doc_purpose, args)
        self.assertEqual(code, 0)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertIn("Project purpose.", content)

    def test_argparse_factory_accepts_project_overview(self):
        """Regression test: cmd handler accepts project-overview but argparse
        factory must list it in --tier choices too. Earlier bug — cmd was
        wired but factory's tier-allowlist was stale."""
        from _generate_docs._doc_setters import _build_set_doc_purpose
        parser = argparse.ArgumentParser()
        _build_set_doc_purpose(parser)
        args = parser.parse_args(
            [
                "--tier", "project-overview",
                "--target", "x",
                "--text", "purpose",
                "--devforge-dir", "/tmp",
            ]
        )
        self.assertEqual(args.tier, "project-overview")

    def test_purpose_rejects_project_architecture(self):
        args = _ns(self.devforge, "project-architecture", text="X")
        code, _, err = _run(cmd_set_doc_purpose, args)
        self.assertEqual(code, 2)
        self.assertIn("set-doc-purpose supports", err)


class CmdSetDocPackagesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-project"}),
                tree="",
            ),
        )

    def test_replaces_placeholder(self):
        args = _ns(
            self.devforge,
            "project-overview",
            packages=json.dumps(
                [
                    {"name": "pkg-a", "role": "first package"},
                    {"name": "pkg-b", "role": "second", "cite": "docs/pkg-b/"},
                ]
            ),
        )
        code, _, _ = _run(cmd_set_doc_packages, args)
        self.assertEqual(code, 0)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: packages -->", content)
        self.assertIn("- pkg-a — first package", content)
        self.assertIn("- pkg-b — second; docs/pkg-b/", content)

    def test_rejects_other_tier(self):
        args = _ns(self.devforge, "concern", packages=json.dumps([]))
        code, _, err = _run(cmd_set_doc_packages, args)
        self.assertEqual(code, 2)
        self.assertIn("set-doc-packages supports", err)

    def test_invalid_json(self):
        args = _ns(self.devforge, "project-overview", packages="not-json")
        code, _, err = _run(cmd_set_doc_packages, args)
        self.assertEqual(code, 2)
        self.assertIn("valid JSON", err)


class CmdSetDocLayersProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-architecture",
                frontmatter=json.dumps({"project": "my-project"}),
                tree="",
            ),
        )

    def test_layers_accepts_project_architecture(self):
        args = _ns(
            self.devforge,
            "project-architecture",
            layers=json.dumps(
                [{"name": "presentation", "role": "Vue components in apps/app-web"}]
            ),
        )
        code, _, _ = _run(cmd_set_doc_layers, args)
        self.assertEqual(code, 0)
        content = (self.root / "docs" / "architecture.md.skeleton").read_text(encoding="utf-8")
        self.assertIn("- presentation — Vue components", content)


class CmdSetDocCrossCutsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-architecture",
                frontmatter=json.dumps({"project": "my-project"}),
                tree="",
            ),
        )

    def test_replaces_placeholder(self):
        args = _ns(
            self.devforge,
            "project-architecture",
            cross_cuts=json.dumps(
                [{"name": "auth", "role": "Okta + identity span", "cite": "pkg-cse-identity/"}]
            ),
        )
        code, _, _ = _run(cmd_set_doc_cross_cuts, args)
        self.assertEqual(code, 0)
        content = (self.root / "docs" / "architecture.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: cross-cuts -->", content)
        self.assertIn("- auth — Okta + identity span; pkg-cse-identity/", content)

    def test_rejects_other_tier(self):
        args = _ns(
            self.devforge,
            "concern",
            cross_cuts=json.dumps([{"name": "x", "role": "y"}]),
        )
        code, _, err = _run(cmd_set_doc_cross_cuts, args)
        self.assertEqual(code, 2)
        self.assertIn("set-doc-cross-cuts supports", err)


class CmdRenderDocProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"

    def test_renames_project_overview(self):
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-project"}),
                tree="",
            ),
        )
        code, _, _ = _run(cmd_render_doc, _ns(self.devforge, "project-overview", out=""))
        self.assertEqual(code, 0)
        self.assertFalse((self.root / "docs" / "overview.md.skeleton").is_file())
        self.assertTrue((self.root / "docs" / "overview.md").is_file())

    def test_renames_project_architecture(self):
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-architecture",
                frontmatter=json.dumps({"project": "my-project"}),
                tree="",
            ),
        )
        code, _, _ = _run(cmd_render_doc, _ns(self.devforge, "project-architecture", out=""))
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "docs" / "architecture.md").is_file())


class EndToEndProjectTests(unittest.TestCase):
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
                "project-overview",
                frontmatter=json.dumps(
                    {"project": "my-project", "last_indexed": "2026-05-08", "source_stamp": "p1"}
                ),
                tree="",
            ),
        )
        _run(
            cmd_set_doc_purpose,
            _ns(self.devforge, "project-overview", text="Project purpose paragraph."),
        )
        _run(
            cmd_set_doc_packages,
            _ns(
                self.devforge,
                "project-overview",
                packages=json.dumps(
                    [
                        {"name": "pkg-a", "role": "first package role"},
                        {"name": "pkg-b", "role": "second package role"},
                    ]
                ),
            ),
        )
        _run(cmd_render_doc, _ns(self.devforge, "project-overview", out=""))
        text = (self.root / "docs" / "overview.md").read_text(encoding="utf-8")
        self.assertIn("Project purpose paragraph.", text)
        self.assertIn("- pkg-a — first package role", text)

    def test_architecture_pipeline(self):
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-architecture",
                frontmatter=json.dumps(
                    {"project": "my-project", "last_indexed": "2026-05-08", "source_stamp": "p1"}
                ),
                tree="",
            ),
        )
        _run(
            cmd_set_doc_layers,
            _ns(
                self.devforge,
                "project-architecture",
                layers=json.dumps([{"name": "presentation", "role": "Vue UI"}]),
            ),
        )
        _run(
            cmd_set_doc_cross_cuts,
            _ns(
                self.devforge,
                "project-architecture",
                cross_cuts=json.dumps(
                    [{"name": "auth", "role": "Okta-mediated identity"}]
                ),
            ),
        )
        _run(cmd_render_doc, _ns(self.devforge, "project-architecture", out=""))
        text = (self.root / "docs" / "architecture.md").read_text(encoding="utf-8")
        self.assertIn("- presentation — Vue UI", text)
        self.assertIn("- auth — Okta-mediated identity", text)


class CmdInitDocPhase1AnchorsTests(unittest.TestCase):
    """Track 4 Phase 1 — verify project-overview skeleton emits 5 new anchors."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"

    def test_project_overview_skeleton_includes_phase1_anchors(self):
        args = _ns(
            self.devforge,
            "project-overview",
            frontmatter=json.dumps({"project": "my-proj"}),
            tree="",
        )
        code, _, _ = _run(cmd_init_doc, args)
        self.assertEqual(code, 0)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        # Phase 0 anchors (still required).
        self.assertIn("## Purpose", content)
        self.assertIn("## Packages", content)
        # Phase 1 mechanical anchors.
        self.assertIn("## Tech Stack", content)
        self.assertIn("## Project Structure", content)
        self.assertIn("## Key Commands", content)
        self.assertIn("## Cross-Module Dependencies", content)
        self.assertIn("## Test Files", content)
        # Phase 1 placeholder markers.
        self.assertIn("<!-- TODO: tech-stack -->", content)
        self.assertIn("<!-- TODO: project-structure -->", content)
        self.assertIn("<!-- TODO: key-commands -->", content)
        self.assertIn("<!-- TODO: cross-module-dependencies -->", content)
        self.assertIn("<!-- TODO: test-files -->", content)

    def test_skeleton_anchor_order_matches_emit_order(self):
        args = _ns(
            self.devforge,
            "project-overview",
            frontmatter=json.dumps({"project": "my-proj"}),
            tree="",
        )
        _run(cmd_init_doc, args)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        # Expected order: Purpose, Tech Stack, Project Structure, Key Commands,
        # Cross-Module Dependencies, Test Files, Packages.
        positions = [
            content.index(f"## {anchor}")
            for anchor in (
                "Purpose",
                "Tech Stack",
                "Project Structure",
                "Key Commands",
                "Cross-Module Dependencies",
                "Test Files",
                "Packages",
            )
        ]
        self.assertEqual(positions, sorted(positions), msg=f"out-of-order: {positions}")


class CmdSetOverviewTechStackTests(unittest.TestCase):
    """Track 4 Phase 1 — set-overview-tech-stack writes a markdown table."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_replaces_placeholder_with_table(self):
        args = _ns(
            self.devforge,
            "project-overview",
            tech_stack=json.dumps([
                {"layer": "Framework", "technology": "Vue 3"},
                {"layer": "Language", "technology": "TypeScript"},
            ]),
        )
        code, _, err = _run(cmd_set_overview_tech_stack, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: tech-stack -->", content)
        self.assertIn("| Layer | Technology |", content)
        self.assertIn("|---|---|", content)
        self.assertIn("| Framework | Vue 3 |", content)
        self.assertIn("| Language | TypeScript |", content)

    def test_rejects_non_project_overview_tier(self):
        args = _ns(
            self.devforge,
            "project-architecture",
            tech_stack=json.dumps([{"layer": "X", "technology": "Y"}]),
        )
        code, _, err = _run(cmd_set_overview_tech_stack, args)
        self.assertEqual(code, 2)
        self.assertIn("set-overview-tech-stack supports", err)

    def test_invalid_json_exits_2(self):
        args = _ns(self.devforge, "project-overview", tech_stack="not-json")
        code, _, err = _run(cmd_set_overview_tech_stack, args)
        self.assertEqual(code, 2)
        self.assertIn("valid JSON", err)

    def test_skips_partial_entries(self):
        args = _ns(
            self.devforge,
            "project-overview",
            tech_stack=json.dumps([
                {"layer": "Framework", "technology": "Vue 3"},
                {"layer": "Language"},   # missing technology — skipped
                {"technology": "Vite"},  # missing layer — skipped
            ]),
        )
        code, _, _ = _run(cmd_set_overview_tech_stack, args)
        self.assertEqual(code, 0)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertIn("| Framework | Vue 3 |", content)
        self.assertNotIn("| Language |  |", content)


class CmdSetOverviewKeyCommandsTests(unittest.TestCase):
    """Track 4 Phase 1 — set-overview-key-commands writes Command table."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_replaces_placeholder_with_table(self):
        args = _ns(
            self.devforge,
            "project-overview",
            key_commands=json.dumps([
                {"command": "npm run build", "description": "turbo run build"},
                {"command": "npm run test", "description": "vitest"},
            ]),
        )
        code, _, err = _run(cmd_set_overview_key_commands, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: key-commands -->", content)
        self.assertIn("| Command | Description |", content)
        self.assertIn("| `npm run build` | turbo run build |", content)
        self.assertIn("| `npm run test` | vitest |", content)


class CmdSetOverviewTestFilesTests(unittest.TestCase):
    """Track 4 Phase 1 — set-overview-test-files writes bulleted list."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_replaces_placeholder_with_bullets(self):
        args = _ns(
            self.devforge,
            "project-overview",
            test_files=json.dumps([
                {"path": "tests/unit/", "description": "App-level tests"},
                {"path": "src/test/", "description": "Core tests"},
            ]),
        )
        code, _, err = _run(cmd_set_overview_test_files, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: test-files -->", content)
        self.assertIn("- `tests/unit/` — App-level tests", content)
        self.assertIn("- `src/test/` — Core tests", content)


class CmdSetOverviewCrossModuleDepsTests(unittest.TestCase):
    """Track 4 Phase 1 — set-overview-cross-module-deps writes fenced text block."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_replaces_placeholder_with_fence(self):
        args = _ns(
            self.devforge,
            "project-overview",
            text="app-web\n  +-- pkg-core\n  +-- pkg-utils",
        )
        code, _, err = _run(cmd_set_overview_cross_module_deps, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: cross-module-dependencies -->", content)
        self.assertIn("```text\napp-web\n  +-- pkg-core\n  +-- pkg-utils\n```", content)


class CmdSetOverviewProjectStructureTreeTests(unittest.TestCase):
    """Track 4 Phase 1 — set-overview-project-structure-tree writes fenced tree."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_replaces_placeholder(self):
        args = _ns(
            self.devforge,
            "project-overview",
            text="my-proj/\n├── apps/\n└── packages/",
        )
        code, _, err = _run(cmd_set_overview_project_structure_tree, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: project-structure -->", content)
        self.assertIn("```text\nmy-proj/\n├── apps/\n└── packages/\n```", content)

    def test_rejects_non_project_overview_tier(self):
        args = _ns(
            self.devforge,
            "concern",
            text="x",
        )
        code, _, err = _run(cmd_set_overview_project_structure_tree, args)
        self.assertEqual(code, 2)
        self.assertIn("set-overview-project-structure-tree supports", err)


class EndToEndPhase1OverviewPipelineTests(unittest.TestCase):
    """Track 4 Phase 1 — full project-overview pipeline with all 7 sections."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"

    def test_full_pipeline_renders_all_phase1_sections(self):
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps(
                    {"project": "my-proj", "last_indexed": "2026-05-08", "source_stamp": "p1"}
                ),
                tree="",
            ),
        )
        _run(
            cmd_set_doc_purpose,
            _ns(self.devforge, "project-overview", text="Project does X."),
        )
        _run(
            cmd_set_overview_tech_stack,
            _ns(
                self.devforge,
                "project-overview",
                tech_stack=json.dumps([{"layer": "Framework", "technology": "Vue 3"}]),
            ),
        )
        _run(
            cmd_set_overview_project_structure_tree,
            _ns(self.devforge, "project-overview", text="my-proj/\n├── apps/"),
        )
        _run(
            cmd_set_overview_key_commands,
            _ns(
                self.devforge,
                "project-overview",
                key_commands=json.dumps([{"command": "npm run build", "description": "turbo build"}]),
            ),
        )
        _run(
            cmd_set_overview_cross_module_deps,
            _ns(self.devforge, "project-overview", text="app-web\n  +-- pkg-core"),
        )
        _run(
            cmd_set_overview_test_files,
            _ns(
                self.devforge,
                "project-overview",
                test_files=json.dumps([{"path": "tests/", "description": "unit tests"}]),
            ),
        )
        _run(
            cmd_set_doc_packages,
            _ns(
                self.devforge,
                "project-overview",
                packages=json.dumps([{"name": "pkg-core", "role": "shared utilities"}]),
            ),
        )
        _run(cmd_render_doc, _ns(self.devforge, "project-overview", out=""))

        text = (self.root / "docs" / "overview.md").read_text(encoding="utf-8")
        # Every Phase 1 section + Phase 0 sections present.
        self.assertIn("Project does X.", text)
        self.assertIn("| Framework | Vue 3 |", text)
        self.assertIn("```text\nmy-proj/", text)
        self.assertIn("| `npm run build` | turbo build |", text)
        self.assertIn("```text\napp-web", text)
        self.assertIn("- `tests/` — unit tests", text)
        self.assertIn("- pkg-core — shared utilities", text)
        # Phase 1 setters leave Phase 2 placeholders untouched (Entry Points,
        # Module Map, Application Routes, Navigation Guards). Phase 2 setters
        # fill those — see EndToEndPhase2OverviewPipelineTests below.
        self.assertNotIn("<!-- TODO: purpose -->", text)
        self.assertNotIn("<!-- TODO: tech-stack -->", text)
        self.assertNotIn("<!-- TODO: project-structure -->", text)
        self.assertNotIn("<!-- TODO: key-commands -->", text)
        self.assertNotIn("<!-- TODO: cross-module-dependencies -->", text)
        self.assertNotIn("<!-- TODO: test-files -->", text)
        self.assertNotIn("<!-- TODO: packages -->", text)


class EndToEndPhase2OverviewPipelineTests(unittest.TestCase):
    """Track 4 Phase 2 — full project-overview pipeline filling all 12 sections."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"

    def test_all_12_sections_render_no_placeholders(self):
        # Create cite_path stub files so validate_cite_paths passes (helper
        # resolves paths relative to cwd — save and restore around the call).
        (self.root / "src").mkdir(parents=True, exist_ok=True)
        (self.root / "src" / "main.ts").write_text("// stub", encoding="utf-8")
        (self.root / "src" / "router.ts").write_text("// stub", encoding="utf-8")

        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps(
                    {"project": "my-proj", "last_indexed": "2026-05-08", "source_stamp": "p2"}
                ),
                tree="",
            ),
        )
        # Phase 0
        _run(cmd_set_doc_purpose, _ns(self.devforge, "project-overview", text="Project does X."))
        # Phase 1
        _run(
            cmd_set_overview_tech_stack,
            _ns(
                self.devforge,
                "project-overview",
                tech_stack=json.dumps([{"layer": "Framework", "technology": "Vue 3"}]),
            ),
        )
        _run(
            cmd_set_overview_project_structure_tree,
            _ns(self.devforge, "project-overview", text="my-proj/\n├── apps/"),
        )
        _run(
            cmd_set_overview_key_commands,
            _ns(
                self.devforge,
                "project-overview",
                key_commands=json.dumps([{"command": "npm run build", "description": "turbo build"}]),
            ),
        )
        _run(
            cmd_set_overview_cross_module_deps,
            _ns(self.devforge, "project-overview", text="app-web\n  +-- pkg-core"),
        )
        _run(
            cmd_set_overview_test_files,
            _ns(
                self.devforge,
                "project-overview",
                test_files=json.dumps([{"path": "tests/", "description": "unit tests"}]),
            ),
        )
        # Phase 2
        _run(
            cmd_set_overview_entry_points,
            _ns(
                self.devforge,
                "project-overview",
                entry_points=json.dumps([
                    {"label": "App entry", "path": "src/main.ts", "purpose": "Boots Vue"},
                ]),
            ),
        )
        # Track A.1 — Suggested Research Starts (chdir to tmp so cite_paths resolve).
        orig_cwd = os.getcwd()
        try:
            os.chdir(str(self.root))
            _run(
                cmd_set_overview_suggested_research_starts,
                _ns(
                    self.devforge,
                    "project-overview",
                    suggested_research_starts=json.dumps([
                        {
                            "question": "How does the app bootstrap?",
                            "scope_hint": "entry + router",
                            "cite_paths": ["src/main.ts", "src/router.ts"],
                        },
                        {
                            "question": "How are routes registered?",
                            "scope_hint": "router module",
                            "cite_paths": ["src/main.ts", "src/router.ts"],
                        },
                        {
                            "question": "What is the top-level component tree?",
                            "scope_hint": "App.vue + layout",
                            "cite_paths": ["src/main.ts", "src/router.ts"],
                        },
                    ]),
                ),
            )
        finally:
            os.chdir(orig_cwd)
        _run(
            cmd_set_overview_module_map,
            _ns(
                self.devforge,
                "project-overview",
                modules=json.dumps({
                    "infrastructure": [{"name": "pkg-common", "purpose": "Base"}],
                    "core": [],
                    "domain": [{"name": "pkg-quote", "purpose": "Quote"}],
                }),
            ),
        )
        _run(
            cmd_set_overview_application_routes,
            _ns(
                self.devforge,
                "project-overview",
                routes=json.dumps([
                    {"path": "/", "component": "PageHome.vue", "description": "Home"},
                ]),
            ),
        )
        _run(
            cmd_set_overview_navigation_guards,
            _ns(
                self.devforge,
                "project-overview",
                guards=json.dumps([{"name": "oktaGuard", "role": "Auth"}]),
            ),
        )
        _run(
            cmd_set_overview_project_structure_annotations,
            _ns(
                self.devforge,
                "project-overview",
                annotations=json.dumps({"apps": "Application shells"}),
            ),
        )
        _run(
            cmd_set_doc_packages,
            _ns(
                self.devforge,
                "project-overview",
                packages=json.dumps([{"name": "pkg-core", "role": "shared"}]),
            ),
        )
        _run(cmd_render_doc, _ns(self.devforge, "project-overview", out=""))

        text = (self.root / "docs" / "overview.md").read_text(encoding="utf-8")
        # Phase 0 / 1 / 2 spot-checks.
        self.assertIn("Project does X.", text)
        self.assertIn("| Framework | Vue 3 |", text)
        self.assertIn("├── apps/  # Application shells", text)
        self.assertIn("| App entry | `src/main.ts` | Boots Vue |", text)
        self.assertIn("| `npm run build` | turbo build |", text)
        self.assertIn("### Infrastructure Packages", text)
        self.assertIn("| `pkg-common` | Base |", text)
        self.assertIn("```text\napp-web", text)
        self.assertIn("| `/` | `PageHome.vue` | Home |", text)
        self.assertIn("1. **oktaGuard** — Auth", text)
        self.assertIn("- `tests/` — unit tests", text)
        self.assertIn("- pkg-core — shared", text)
        # Track A.1 spot-check.
        self.assertIn("| Question | Scope hint | Start here |", text)
        self.assertIn("How does the app bootstrap?", text)
        # NO leftover placeholders anywhere.
        self.assertNotIn("<!-- TODO:", text)


class CmdInitDocPhase2AnchorsTests(unittest.TestCase):
    """Track 4 Phase 2 — verify project-overview skeleton emits 4 new anchors."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"

    def test_phase2_anchors_in_skeleton(self):
        args = _ns(
            self.devforge,
            "project-overview",
            frontmatter=json.dumps({"project": "my-proj"}),
            tree="",
        )
        code, _, _ = _run(cmd_init_doc, args)
        self.assertEqual(code, 0)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertIn("## Entry Points", content)
        self.assertIn("## Module Map", content)
        self.assertIn("## Application Routes", content)
        self.assertIn("## Navigation Guards", content)
        self.assertIn("<!-- TODO: entry-points -->", content)
        self.assertIn("<!-- TODO: module-map -->", content)
        self.assertIn("<!-- TODO: application-routes -->", content)
        self.assertIn("<!-- TODO: navigation-guards -->", content)
        self.assertIn("## Suggested Research Starts", content)
        self.assertIn("<!-- TODO: suggested-research-starts -->", content)

    def test_phase2_full_section_order(self):
        args = _ns(
            self.devforge,
            "project-overview",
            frontmatter=json.dumps({"project": "my-proj"}),
            tree="",
        )
        _run(cmd_init_doc, args)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        # Expected order: Purpose, Tech Stack, Project Structure, Entry Points,
        # Suggested Research Starts, Key Commands, Module Map, Cross-Module Deps,
        # Application Routes, Navigation Guards, Test Files, Packages.
        positions = [
            content.index(f"## {anchor}")
            for anchor in (
                "Purpose",
                "Tech Stack",
                "Project Structure",
                "Entry Points",
                "Suggested Research Starts",
                "Key Commands",
                "Module Map",
                "Cross-Module Dependencies",
                "Application Routes",
                "Navigation Guards",
                "Test Files",
                "Packages",
            )
        ]
        self.assertEqual(positions, sorted(positions), msg=f"out-of-order: {positions}")


class CmdSetOverviewEntryPointsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_replaces_placeholder_with_3col_table(self):
        args = _ns(
            self.devforge,
            "project-overview",
            entry_points=json.dumps([
                {"label": "App entry", "path": "src/main.ts", "purpose": "Boots Vue"},
                {"label": "Router", "path": "src/router/index.ts", "purpose": "Routes"},
            ]),
        )
        code, _, err = _run(cmd_set_overview_entry_points, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: entry-points -->", content)
        self.assertIn("| Entry Point | Path | Purpose |", content)
        self.assertIn("| App entry | `src/main.ts` | Boots Vue |", content)
        self.assertIn("| Router | `src/router/index.ts` | Routes |", content)

    def test_skips_rows_missing_label_or_path(self):
        args = _ns(
            self.devforge,
            "project-overview",
            entry_points=json.dumps([
                {"label": "X", "path": "p"},
                {"label": "no-path"},
                {"path": "no-label"},
            ]),
        )
        code, _, _ = _run(cmd_set_overview_entry_points, args)
        self.assertEqual(code, 0)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertIn("| X | `p` |", content)
        self.assertNotIn("no-path", content)
        self.assertNotIn("no-label", content)


class CmdSetOverviewApplicationRoutesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_replaces_placeholder(self):
        args = _ns(
            self.devforge,
            "project-overview",
            routes=json.dumps([
                {"path": "/", "component": "PageHome.vue", "description": "Dashboard"},
                {"path": "/quote", "component": "PageQuote.vue", "description": "Quote editing"},
            ]),
        )
        code, _, err = _run(cmd_set_overview_application_routes, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: application-routes -->", content)
        self.assertIn("| Route | Component | Description |", content)
        self.assertIn("| `/` | `PageHome.vue` | Dashboard |", content)
        self.assertIn("| `/quote` | `PageQuote.vue` | Quote editing |", content)


class CmdSetOverviewNavigationGuardsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_emits_numbered_bold_list(self):
        args = _ns(
            self.devforge,
            "project-overview",
            guards=json.dumps([
                {"name": "oktaGuard", "role": "Checks Okta auth"},
                {"name": "identityGuard", "role": "Fetches user identity"},
            ]),
        )
        code, _, err = _run(cmd_set_overview_navigation_guards, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: navigation-guards -->", content)
        self.assertIn("1. **oktaGuard** — Checks Okta auth", content)
        self.assertIn("2. **identityGuard** — Fetches user identity", content)


class CmdSetOverviewModuleMapTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_emits_three_subsections(self):
        args = _ns(
            self.devforge,
            "project-overview",
            modules=json.dumps({
                "infrastructure": [{"name": "pkg-common", "purpose": "Base classes"}],
                "core": [{"name": "pkg-core", "purpose": "Business logic"}],
                "domain": [{"name": "pkg-quote", "purpose": "Quote feature"}],
            }),
        )
        code, _, err = _run(cmd_set_overview_module_map, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: module-map -->", content)
        self.assertIn("### Infrastructure Packages", content)
        self.assertIn("### Core Package", content)
        self.assertIn("### Domain Packages", content)
        self.assertIn("| `pkg-common` | Base classes |", content)
        self.assertIn("| `pkg-quote` | Quote feature |", content)

    def test_omits_empty_subsections(self):
        args = _ns(
            self.devforge,
            "project-overview",
            modules=json.dumps({"infrastructure": [{"name": "X", "purpose": "Y"}]}),
        )
        code, _, _ = _run(cmd_set_overview_module_map, args)
        self.assertEqual(code, 0)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertIn("### Infrastructure Packages", content)
        self.assertNotIn("### Core Package", content)
        self.assertNotIn("### Domain Packages", content)


class CmdSetOverviewProjectStructureAnnotationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )
        # Plant a Phase 1 tree first so annotations have something to walk.
        _run(
            cmd_set_overview_project_structure_tree,
            _ns(
                self.devforge,
                "project-overview",
                text="my-proj/\n├── apps/\n│   └── app-web/\n└── packages/",
            ),
        )

    def test_annotates_directory_leaves(self):
        args = _ns(
            self.devforge,
            "project-overview",
            annotations=json.dumps({
                "apps": "Application shells",
                "app-web": "Vue 3 SPA",
                "packages": "Shared package monorepo",
            }),
        )
        code, _, err = _run(cmd_set_overview_project_structure_annotations, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertIn("├── apps/  # Application shells", content)
        self.assertIn("└── app-web/  # Vue 3 SPA", content)
        self.assertIn("└── packages/  # Shared package monorepo", content)

    def test_unannotated_lines_unchanged(self):
        args = _ns(
            self.devforge,
            "project-overview",
            annotations=json.dumps({"apps": "Application shells"}),
        )
        _run(cmd_set_overview_project_structure_annotations, args)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertIn("├── apps/  # Application shells", content)
        # `packages/` had no annotation registered → stays bare.
        self.assertIn("└── packages/", content)
        self.assertNotIn("packages/  #", content)

    def test_idempotent_reapply(self):
        # First pass.
        _run(
            cmd_set_overview_project_structure_annotations,
            _ns(
                self.devforge,
                "project-overview",
                annotations=json.dumps({"apps": "Application shells"}),
            ),
        )
        first = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        # Second pass with same annotation — must not duplicate.
        _run(
            cmd_set_overview_project_structure_annotations,
            _ns(
                self.devforge,
                "project-overview",
                annotations=json.dumps({"apps": "Application shells"}),
            ),
        )
        second = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertEqual(first, second)
        # No double-annotation accidentally formed.
        self.assertNotIn("Application shells  # Application shells", second)

    def test_rejects_when_no_tree_fence(self):
        # Re-init to wipe the tree fence (init-doc resets owned anchors).
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )
        # The skeleton has the anchor but the placeholder is `<!-- TODO: project-structure -->`,
        # not a tree fence. Annotations setter must reject.
        code, _, err = _run(
            cmd_set_overview_project_structure_annotations,
            _ns(
                self.devforge,
                "project-overview",
                annotations=json.dumps({"apps": "x"}),
            ),
        )
        self.assertEqual(code, 2)
        self.assertIn("no `", err)


class CmdInitDocPhase3ArchitectureAnchorsTests(unittest.TestCase):
    """Track 4 Phase 3 — verify project-architecture skeleton emits 8 anchors."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"

    def test_phase3_anchors_in_skeleton(self):
        args = _ns(
            self.devforge,
            "project-architecture",
            frontmatter=json.dumps({"project": "my-proj"}),
            tree="",
        )
        code, _, _ = _run(cmd_init_doc, args)
        self.assertEqual(code, 0)
        content = (self.root / "docs" / "architecture.md.skeleton").read_text(encoding="utf-8")
        for anchor in (
            "## Architecture Overview",
            "## Module / Package Structure",
            "## Patterns",
            "## Conventions",
            "## Layers",
            "## Cross-Cuts",
            "## Dependency Direction Rules",
            "## Dependency Overview",
        ):
            self.assertIn(anchor, content, msg=f"missing anchor {anchor!r}")
        for placeholder in (
            "<!-- TODO: architecture-overview-narrative -->",
            "<!-- TODO: module-structure -->",
            "<!-- TODO: architecture-patterns -->",
            "<!-- TODO: conventions -->",
            "<!-- TODO: dependency-direction-rules -->",
            "<!-- TODO: dependency-overview-mermaid -->",
        ):
            self.assertIn(placeholder, content)

    def test_skeleton_anchor_order(self):
        args = _ns(
            self.devforge,
            "project-architecture",
            frontmatter=json.dumps({"project": "my-proj"}),
            tree="",
        )
        _run(cmd_init_doc, args)
        content = (self.root / "docs" / "architecture.md.skeleton").read_text(encoding="utf-8")
        positions = [
            content.index(f"## {anchor}")
            for anchor in (
                "Architecture Overview",
                "Module / Package Structure",
                "Patterns",
                "Conventions",
                "Layers",
                "Cross-Cuts",
                "Dependency Direction Rules",
                "Dependency Overview",
            )
        ]
        self.assertEqual(positions, sorted(positions))


class CmdSetArchitectureOverviewNarrativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-architecture",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_replaces_placeholder(self):
        args = _ns(
            self.devforge,
            "project-architecture",
            text="Multi-paragraph narrative.\n\nSecond paragraph.",
        )
        code, _, err = _run(cmd_set_architecture_overview_narrative, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "architecture.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: architecture-overview-narrative -->", content)
        self.assertIn("Multi-paragraph narrative.", content)
        self.assertIn("Second paragraph.", content)

    def test_rejects_other_tier(self):
        args = _ns(self.devforge, "project-overview", text="x")
        code, _, err = _run(cmd_set_architecture_overview_narrative, args)
        self.assertEqual(code, 2)
        self.assertIn("set-architecture-overview-narrative supports", err)


class CmdSetArchitectureModuleStructureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-architecture",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_writes_fenced_text_block(self):
        args = _ns(
            self.devforge,
            "project-architecture",
            text="root/\n  apps/\n  packages/",
        )
        code, _, err = _run(cmd_set_architecture_module_structure, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "architecture.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: module-structure -->", content)
        self.assertIn("```text\nroot/\n  apps/\n  packages/\n```", content)


class CmdSetArchitecturePatternsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-architecture",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_renders_subsection_per_pattern(self):
        args = _ns(
            self.devforge,
            "project-architecture",
            patterns=json.dumps([
                {
                    "name": "Clean Architecture",
                    "applies_in": "every pkg",
                    "rule": "data/domain/presentation split",
                    "language": "typescript",
                    "code_snippet": "export class X {}",
                    "cite": "pkg/x.ts:1",
                },
            ]),
        )
        code, _, err = _run(cmd_set_architecture_patterns, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "architecture.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: architecture-patterns -->", content)
        self.assertIn("### Clean Architecture", content)
        self.assertIn("**Applies in**: every pkg", content)
        self.assertIn("data/domain/presentation split", content)
        self.assertIn("<!-- pkg/x.ts:1 -->", content)
        self.assertIn("```typescript\nexport class X {}\n```", content)

    def test_skips_entry_without_name(self):
        args = _ns(
            self.devforge,
            "project-architecture",
            patterns=json.dumps([{"applies_in": "x", "rule": "y"}]),
        )
        code, _, _ = _run(cmd_set_architecture_patterns, args)
        self.assertEqual(code, 0)
        content = (self.root / "docs" / "architecture.md.skeleton").read_text(encoding="utf-8")
        section = _section_body(content, "Patterns")
        self.assertNotIn("### ", section)

    def test_no_snippet_no_cite(self):
        # When snippet empty, no fenced block + no cite-back comment.
        args = _ns(
            self.devforge,
            "project-architecture",
            patterns=json.dumps([
                {"name": "P1", "rule": "rule prose"}
            ]),
        )
        _run(cmd_set_architecture_patterns, args)
        content = (self.root / "docs" / "architecture.md.skeleton").read_text(encoding="utf-8")
        section = _section_body(content, "Patterns")
        self.assertIn("### P1", section)
        self.assertIn("rule prose", section)
        self.assertNotIn("```", section)


class CmdSetArchitectureConventionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-architecture",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_emits_four_subsections(self):
        args = _ns(
            self.devforge,
            "project-architecture",
            conventions=json.dumps({
                "naming": ["Classes: PascalCase", "Factories: camelCase"],
                "file_organization": ["Feature dir per module"],
                "import_style": ["Use package root names"],
                "error_handling": ["Either monad outside core"],
            }),
        )
        code, _, err = _run(cmd_set_architecture_conventions, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "architecture.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: conventions -->", content)
        self.assertIn("**Naming**", content)
        self.assertIn("**File Organization**", content)
        self.assertIn("**Import Style**", content)
        self.assertIn("**Error Handling**", content)
        self.assertIn("- Classes: PascalCase", content)
        self.assertIn("- Either monad outside core", content)

    def test_omits_empty_buckets(self):
        args = _ns(
            self.devforge,
            "project-architecture",
            conventions=json.dumps({"naming": ["X"]}),
        )
        _run(cmd_set_architecture_conventions, args)
        content = (self.root / "docs" / "architecture.md.skeleton").read_text(encoding="utf-8")
        conv_section = _section_body(content, "Conventions")
        self.assertIn("**Naming**", conv_section)
        self.assertNotIn("**File Organization**", conv_section)
        self.assertNotIn("**Import Style**", conv_section)
        self.assertNotIn("**Error Handling**", conv_section)


class CmdSetArchitectureCrossCutsDetailedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-architecture",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_renders_subsection_with_snippet(self):
        args = _ns(
            self.devforge,
            "project-architecture",
            cross_cuts=json.dumps([
                {
                    "name": "Authentication",
                    "description": "Okta + Apollo singleton",
                    "language": "typescript",
                    "code_snippet": "const TOKEN = getToken();",
                    "cite": "pkg-cse-client/src/x.ts:29",
                },
            ]),
        )
        code, _, err = _run(cmd_set_architecture_cross_cuts_detailed, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "architecture.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: cross-cuts -->", content)
        self.assertIn("### Authentication", content)
        self.assertIn("Okta + Apollo singleton", content)
        self.assertIn("<!-- pkg-cse-client/src/x.ts:29 -->", content)
        self.assertIn("```typescript\nconst TOKEN = getToken();\n```", content)

    def test_replaces_phase0_bullet_list(self):
        # Phase 0's set-doc-cross-cuts uses bullet shape; Phase 3's enriched
        # setter targets same anchor — last call wins.
        _run(
            cmd_set_doc_cross_cuts,
            _ns(
                self.devforge,
                "project-architecture",
                cross_cuts=json.dumps([{"name": "old", "role": "bullet shape"}]),
            ),
        )
        _run(
            cmd_set_architecture_cross_cuts_detailed,
            _ns(
                self.devforge,
                "project-architecture",
                cross_cuts=json.dumps([{"name": "new", "description": "subsection shape"}]),
            ),
        )
        content = (self.root / "docs" / "architecture.md.skeleton").read_text(encoding="utf-8")
        cross_section = _section_body(content, "Cross-Cuts")
        self.assertNotIn("- old", cross_section)
        self.assertIn("### new", cross_section)


class CmdSetArchitectureDependencyDirectionRulesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-architecture",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_renders_bullets(self):
        args = _ns(
            self.devforge,
            "project-architecture",
            rules=json.dumps([
                "pkg-types is a leaf — no upstream pkg deps",
                "feature pkgs depend on common + types + client",
            ]),
        )
        code, _, err = _run(cmd_set_architecture_dependency_direction_rules, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "architecture.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: dependency-direction-rules -->", content)
        self.assertIn("- pkg-types is a leaf — no upstream pkg deps", content)
        self.assertIn("- feature pkgs depend on common + types + client", content)


class CmdSetArchitectureDependencyOverviewMermaidTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-architecture",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )

    def test_writes_mermaid_fenced_block(self):
        args = _ns(
            self.devforge,
            "project-architecture",
            text="graph TD\n    a[A]\n    b[B]\n    a --> b",
        )
        code, _, err = _run(cmd_set_architecture_dependency_overview_mermaid, args)
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "architecture.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: dependency-overview-mermaid -->", content)
        self.assertIn("```mermaid\ngraph TD\n    a[A]\n    b[B]\n    a --> b\n```", content)


class EndToEndPhase3ArchitecturePipelineTests(unittest.TestCase):
    """Track 4 Phase 3 — full project-architecture pipeline filling all 8 sections."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"

    def test_all_8_sections_render_no_placeholders(self):
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-architecture",
                frontmatter=json.dumps(
                    {"project": "my-proj", "last_indexed": "2026-05-08", "source_stamp": "p3"}
                ),
                tree="",
            ),
        )
        _run(
            cmd_set_architecture_overview_narrative,
            _ns(self.devforge, "project-architecture", text="Architecture is X."),
        )
        _run(
            cmd_set_architecture_module_structure,
            _ns(self.devforge, "project-architecture", text="root/\n  apps/"),
        )
        _run(
            cmd_set_architecture_patterns,
            _ns(
                self.devforge,
                "project-architecture",
                patterns=json.dumps([
                    {"name": "P1", "rule": "rule", "language": "ts", "code_snippet": "x", "cite": "f.ts:1"},
                ]),
            ),
        )
        _run(
            cmd_set_architecture_conventions,
            _ns(
                self.devforge,
                "project-architecture",
                conventions=json.dumps({"naming": ["PascalCase classes"]}),
            ),
        )
        _run(
            cmd_set_doc_layers,
            _ns(
                self.devforge,
                "project-architecture",
                layers=json.dumps([{"name": "presentation", "role": "Vue UI"}]),
            ),
        )
        _run(
            cmd_set_architecture_cross_cuts_detailed,
            _ns(
                self.devforge,
                "project-architecture",
                cross_cuts=json.dumps([
                    {"name": "Auth", "description": "Okta-Apollo handshake", "language": "ts", "code_snippet": "const t = getToken()", "cite": "x.ts:1"},
                ]),
            ),
        )
        _run(
            cmd_set_architecture_dependency_direction_rules,
            _ns(
                self.devforge,
                "project-architecture",
                rules=json.dumps(["pkg-types is leaf", "core depends on client + types"]),
            ),
        )
        _run(
            cmd_set_architecture_dependency_overview_mermaid,
            _ns(
                self.devforge,
                "project-architecture",
                text="graph TD\n    a[pkg-a]\n    b[pkg-b]\n    a --> b",
            ),
        )
        _run(cmd_render_doc, _ns(self.devforge, "project-architecture", out=""))

        text = (self.root / "docs" / "architecture.md").read_text(encoding="utf-8")
        # Every Phase 3 section spot-check.
        self.assertIn("Architecture is X.", text)
        self.assertIn("```text\nroot/", text)
        self.assertIn("### P1", text)
        self.assertIn("**Naming**", text)
        self.assertIn("- PascalCase classes", text)
        self.assertIn("- presentation — Vue UI", text)
        self.assertIn("### Auth", text)
        self.assertIn("Okta-Apollo handshake", text)
        self.assertIn("- pkg-types is leaf", text)
        self.assertIn("```mermaid\ngraph TD", text)
        # No leftover placeholders.
        self.assertNotIn("<!-- TODO:", text)


class CmdSetOverviewSuggestedResearchStartsTests(unittest.TestCase):
    """Track A.1 — set-overview-suggested-research-starts tests (~13 cases)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        # Create dummy source files for cite_paths existence checks.
        (self.root / "src").mkdir(parents=True, exist_ok=True)
        for fname in ["alpha.ts", "beta.ts", "gamma.ts", "delta.ts"]:
            (self.root / "src" / fname).write_text("// stub", encoding="utf-8")
        # Init the skeleton.
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )
        self._orig_cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._orig_cwd)

    def _valid_entries(self, n=3):
        """Return n valid entries using stubs that exist under self.root."""
        questions = [
            "How does the app bootstrap?",
            "How are routes registered?",
            "What is the component tree?",
            "How does auth flow work?",
            "How is state managed?",
            "Where does data fetching happen?",
        ]
        return [
            {
                "question": questions[i],
                "scope_hint": f"scope hint {i}",
                "cite_paths": ["src/alpha.ts", "src/beta.ts"],
            }
            for i in range(n)
        ]

    def _run_with_chdir(self, entries):
        """Call cmd with chdir to self.root so cite_paths resolve correctly."""
        os.chdir(str(self.root))
        args = _ns(
            self.devforge,
            "project-overview",
            suggested_research_starts=json.dumps(entries),
        )
        return _run(cmd_set_overview_suggested_research_starts, args)

    # ── Happy path ──────────────────────────────────────────────────────────

    def test_happy_3_entries_exit0_table_rendered(self):
        """3 valid entries → exit 0; rendered table appears in skeleton."""
        code, out, err = self._run_with_chdir(self._valid_entries(3))
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: suggested-research-starts -->", content)
        self.assertIn("| Question | Scope hint | Start here |", content)
        self.assertIn("How does the app bootstrap?", content)
        self.assertIn("`src/alpha.ts`", content)

    def test_happy_6_entries_exit0(self):
        """6 valid entries → exit 0."""
        code, _, err = self._run_with_chdir(self._valid_entries(6))
        self.assertEqual(code, 0, msg=err)
        content = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: suggested-research-starts -->", content)

    def test_happy_existing_placeholder_replaced(self):
        """Existing skeleton with placeholder → replaced with table on second run."""
        # Verify placeholder is present initially.
        content_before = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertIn("<!-- TODO: suggested-research-starts -->", content_before)
        code, _, err = self._run_with_chdir(self._valid_entries(3))
        self.assertEqual(code, 0, msg=err)
        content_after = (self.root / "docs" / "overview.md.skeleton").read_text(encoding="utf-8")
        self.assertNotIn("<!-- TODO: suggested-research-starts -->", content_after)
        self.assertIn("| Question | Scope hint | Start here |", content_after)

    # ── Count bounds ─────────────────────────────────────────────────────────

    def test_count_2_entries_exit2(self):
        """2 entries (below floor of 3) → exit 2."""
        code, _, err = self._run_with_chdir(self._valid_entries(2))
        self.assertEqual(code, 2)
        self.assertIn("at least 3", err)

    def test_count_7_entries_exit2(self):
        """7 entries (above ceiling of 6) → exit 2."""
        entries = self._valid_entries(6)
        entries.append({
            "question": "Extra question number seven?",
            "scope_hint": "some scope",
            "cite_paths": ["src/alpha.ts", "src/beta.ts"],
        })
        code, _, err = self._run_with_chdir(entries)
        self.assertEqual(code, 2)
        self.assertIn("at most 6", err)

    def test_count_0_entries_exit2(self):
        """Empty list → exit 2."""
        code, _, err = self._run_with_chdir([])
        self.assertEqual(code, 2)
        self.assertIn("at least 3", err)

    # ── Per-entry validation ─────────────────────────────────────────────────

    def test_empty_question_exit2(self):
        """question empty → exit 2."""
        entries = self._valid_entries(3)
        entries[0]["question"] = ""
        code, _, err = self._run_with_chdir(entries)
        self.assertEqual(code, 2)
        self.assertIn("question is empty", err)

    def test_question_no_question_mark_exit2(self):
        """question not ending with '?' → exit 2."""
        entries = self._valid_entries(3)
        entries[0]["question"] = "No question mark here"
        code, _, err = self._run_with_chdir(entries)
        self.assertEqual(code, 2)
        self.assertIn("must end with '?'", err)

    def test_question_exceeds_140_chars_exit2(self):
        """question > 140 chars → exit 2."""
        entries = self._valid_entries(3)
        entries[0]["question"] = "A" * 139 + "?"  # 140 chars — OK boundary
        code_ok, _, _ = self._run_with_chdir(entries)
        self.assertEqual(code_ok, 0)
        # Re-init skeleton for second call.
        _run(
            cmd_init_doc,
            _ns(
                self.devforge,
                "project-overview",
                frontmatter=json.dumps({"project": "my-proj"}),
                tree="",
            ),
        )
        entries2 = self._valid_entries(3)
        entries2[0]["question"] = "A" * 140 + "?"  # 141 chars — too long
        code_bad, _, err = self._run_with_chdir(entries2)
        self.assertEqual(code_bad, 2)
        self.assertIn("exceeds 140 chars", err)

    def test_scope_hint_contains_newline_exit2(self):
        """scope_hint contains \\n → exit 2."""
        entries = self._valid_entries(3)
        entries[0]["scope_hint"] = "good scope\nnewline"
        code, _, err = self._run_with_chdir(entries)
        self.assertEqual(code, 2)
        self.assertIn("contains newline", err)

    def test_cite_paths_only_1_path_exit2(self):
        """cite_paths with only 1 path → exit 2 (requires ≥2)."""
        entries = self._valid_entries(3)
        entries[0]["cite_paths"] = ["src/alpha.ts"]
        code, _, err = self._run_with_chdir(entries)
        self.assertEqual(code, 2)
        self.assertIn("at least 2 paths", err)

    # ── Cross-entry validation ────────────────────────────────────────────────

    def test_cite_path_not_on_disk_exit2(self):
        """cite_path that doesn't exist on disk → exit 2."""
        entries = self._valid_entries(3)
        entries[0]["cite_paths"] = ["src/alpha.ts", "src/nonexistent_file.ts"]
        code, _, err = self._run_with_chdir(entries)
        self.assertEqual(code, 2)
        self.assertIn("paths not found", err)
        self.assertIn("src/nonexistent_file.ts", err)

    def test_duplicate_questions_case_insensitive_exit2(self):
        """Duplicate questions (case-insensitive) → exit 2."""
        entries = self._valid_entries(3)
        entries[1]["question"] = entries[0]["question"].upper()
        code, _, err = self._run_with_chdir(entries)
        self.assertEqual(code, 2)
        self.assertIn("duplicate question", err)

    def test_scope_hint_with_trailing_newline_rejected(self):
        """scope_hint with trailing \\n (pre-strip) → exit 2, stderr mentions newline.

        Regression for Finding 1: newline check must run on raw value before strip,
        not on the stripped result which silently drops the trailing newline.
        """
        entries = self._valid_entries(3)
        entries[0]["scope_hint"] = "valid scope\n"
        code, _, err = self._run_with_chdir(entries)
        self.assertEqual(code, 2)
        self.assertIn("contains newline", err)

    def test_cite_paths_non_string_element_rejected(self):
        """cite_paths element that is not a string → exit 2, stderr mentions cite_paths[0].

        Regression for Finding 3: non-string elements must be rejected with a clear
        type error rather than silently coerced via str().
        """
        entries = self._valid_entries(3)
        entries[0]["cite_paths"] = [42, "src/alpha.ts", "src/beta.ts"]
        code, _, err = self._run_with_chdir(entries)
        self.assertEqual(code, 2)
        self.assertIn("cite_paths[0]", err)
        self.assertIn("must be a string", err)


if __name__ == "__main__":
    unittest.main()
