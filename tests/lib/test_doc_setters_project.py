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
    cmd_set_doc_cross_cuts,
    cmd_set_doc_layers,
    cmd_set_doc_packages,
    cmd_set_doc_purpose,
    cmd_set_overview_cross_module_deps,
    cmd_set_overview_key_commands,
    cmd_set_overview_project_structure_tree,
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
        # No leftover placeholders.
        self.assertNotIn("<!-- TODO:", text)


if __name__ == "__main__":
    unittest.main()
