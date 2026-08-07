"""Tests for _project_input.py — F.8a project-input helper.

Cases:
  1.  _enumerate_packages_with_overviews: walks docs/ for overview.md
      excluding the project-tier docs/overview.md
  2.  _enumerate_packages_with_overviews: missing docs/ → []
  3.  _read_package_seed: parses frontmatter + Purpose section
  4.  _read_package_seed: missing doc → None
  5.  _read_package_seed: malformed frontmatter → None
  6.  _collect_project_root_files: README + CHANGELOG + package.json
  7.  _collect_project_root_files: empty when none exist
  8.  _compute_source_stamp: deterministic across reorderings
  9.  _compute_source_stamp: changes when package stamp changes
 10.  cmd_project_input: synthetic project end-to-end
 11.  cmd_project_input: no package overviews AND no concern docs → exit 2
 12.  cmd_project_input: --project label override
 13.  _enumerate_concern_docs: depth-1 index.md discovery
 14.  _enumerate_concern_docs: nested index.md not picked up at depth-1
 15.  _enumerate_concern_docs: missing docs/ → []
 16.  _read_concern_seed: parses frontmatter + Purpose from index.md
 17.  _read_concern_seed: missing file → None
 18.  _read_concern_seed: malformed frontmatter → None
 19.  cmd_project_input: single-root fallback via concern docs (end-to-end)
 20.  cmd_project_input: package-overview path unaffected when overviews exist (regression)

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

from _generate_docs._project_input import (  # noqa: E402
    _build_cross_module_deps_tree,
    _build_dep_graph_mermaid,
    _build_project_structure_tree,
    _classify_packages,
    _collect_project_root_files,
    _compute_source_stamp,
    _detect_tech_stack,
    _enumerate_concern_docs,
    _enumerate_packages_with_overviews,
    _extract_key_commands,
    _read_concern_seed,
    _read_package_seed,
    _resolve_effective_project_root,
    _walk_entry_point_candidates,
    _walk_nav_guard_files,
    _walk_router_route_files,
    _walk_test_file_paths,
    cmd_project_input,
)


def _run(handler, args):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = handler(args)
    return code, out.getvalue(), err.getvalue()


_PKG_OVERVIEW_TEMPLATE = """---
package: {pkg}
last_indexed: 2026-05-08
source_stamp: stamp-{stamp}
---


# {pkg}

## Purpose

{purpose}

## Concerns

- alpha — first concern

## Files

- index.ts — barrel re-export
"""


class EnumeratePackagesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.docs = self.root / "docs"

    def _write_overview(self, rel_pkg: str, content: str = "stub"):
        path = self.docs / rel_pkg / "overview.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_walks_docs_for_overviews(self):
        self._write_overview("pkg-a")
        self._write_overview("nested/pkg-b")
        # Project-tier overview MUST be excluded
        (self.docs / "overview.md").write_text("project\n", encoding="utf-8")
        result = _enumerate_packages_with_overviews(self.root)
        self.assertEqual(sorted(result), ["nested/pkg-b", "pkg-a"])

    def test_missing_docs_dir(self):
        self.assertEqual(_enumerate_packages_with_overviews(self.root), [])


class ReadPackageSeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _write(self, rel_pkg: str, content: str):
        path = self.root / "docs" / rel_pkg / "overview.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_parses_frontmatter_and_purpose(self):
        self._write(
            "pkg-a",
            _PKG_OVERVIEW_TEMPLATE.format(pkg="pkg-a", stamp="A", purpose="Pkg-A purpose paragraph."),
        )
        seed = _read_package_seed(self.root, "pkg-a")
        self.assertIsNotNone(seed)
        self.assertEqual(seed["package"], "pkg-a")
        self.assertEqual(seed["frontmatter"]["source_stamp"], "stamp-A")
        self.assertIn("Pkg-A purpose paragraph.", seed["purpose_text"])

    def test_missing_doc_returns_none(self):
        self.assertIsNone(_read_package_seed(self.root, "pkg-ghost"))

    def test_malformed_frontmatter_returns_none(self):
        self._write("pkg-a", "no frontmatter\n")
        self.assertIsNone(_read_package_seed(self.root, "pkg-a"))


class CollectProjectRootFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_picks_up_top_level_files(self):
        (self.root / "README.md").write_text("# project\nintro\n", encoding="utf-8")
        (self.root / "package.json").write_text("{}\n", encoding="utf-8")
        records, hashes = _collect_project_root_files(self.root)
        names = sorted(r["path"] for r in records)
        self.assertIn("README.md", names)
        self.assertIn("package.json", names)
        self.assertEqual(len(hashes), len(records))

    def test_no_eligible_files(self):
        records, hashes = _collect_project_root_files(self.root)
        self.assertEqual(records, [])
        self.assertEqual(hashes, [])


class ComputeSourceStampTests(unittest.TestCase):
    def test_deterministic_across_reordering(self):
        seed_a = {"package": "pkg-a", "frontmatter": {"source_stamp": "1"}}
        seed_b = {"package": "pkg-b", "frontmatter": {"source_stamp": "2"}}
        hashes_1 = [("README.md", "h1"), ("package.json", "h2")]
        hashes_2 = [("package.json", "h2"), ("README.md", "h1")]
        s1 = _compute_source_stamp([seed_a, seed_b], hashes_1)
        s2 = _compute_source_stamp([seed_b, seed_a], hashes_2)
        self.assertEqual(s1, s2)

    def test_changes_when_package_stamp_changes(self):
        v1 = {"package": "pkg-a", "frontmatter": {"source_stamp": "1"}}
        v2 = {"package": "pkg-a", "frontmatter": {"source_stamp": "2"}}
        self.assertNotEqual(
            _compute_source_stamp([v1], []),
            _compute_source_stamp([v2], []),
        )


class CmdProjectInputTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir()

    def _write_overview(self, rel_pkg: str, stamp: str = "X", purpose: str = "stub purpose"):
        path = self.root / "docs" / rel_pkg / "overview.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _PKG_OVERVIEW_TEMPLATE.format(pkg=rel_pkg, stamp=stamp, purpose=purpose),
            encoding="utf-8",
        )

    def test_end_to_end(self):
        self._write_overview("pkg-a", purpose="Alpha purpose.")
        self._write_overview("packages/pkg-b", purpose="Beta purpose.")
        (self.root / "README.md").write_text("# project\n", encoding="utf-8")
        args = argparse.Namespace(
            project="my-project",
            devforge_dir=str(self.devforge),
        )
        code, out, _ = _run(cmd_project_input, args)
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["project"], "my-project")
        self.assertEqual(len(payload["package_seeds"]), 2)
        self.assertEqual(
            sorted(s["package"] for s in payload["package_seeds"]),
            ["packages/pkg-b", "pkg-a"],
        )
        names = [r["path"] for r in payload["project_root_files"]]
        self.assertIn("README.md", names)
        self.assertRegex(payload["source_stamp"], r"^[0-9a-f]{16}$")

    def test_no_package_overviews_and_no_concern_docs_exit_2(self):
        # Neither docs/<pkg>/overview.md nor docs/<concern>/index.md exist.
        # The docs/ dir itself is absent — guarantees both enumerators return [].
        args = argparse.Namespace(project="", devforge_dir=str(self.devforge))
        code, _, err = _run(cmd_project_input, args)
        self.assertEqual(code, 2)
        self.assertIn("no package overviews or concern docs", err)

    def test_project_label_default_to_root_basename(self):
        self._write_overview("pkg-a")
        args = argparse.Namespace(project="", devforge_dir=str(self.devforge))
        code, out, _ = _run(cmd_project_input, args)
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["project"], self.root.name)


class DetectTechStackTests(unittest.TestCase):
    """Track 4 Phase 1 — _detect_tech_stack reads package.json + manifests."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_detects_vue_typescript_vite_from_deps(self):
        (self.root / "package.json").write_text(
            json.dumps({
                "dependencies": {"vue": "^3.0.0", "pinia": "^2.0.0"},
                "devDependencies": {"typescript": "^5.0.0", "vite": "^5.0.0", "vitest": "^1.0.0"},
            }),
            encoding="utf-8",
        )
        result = _detect_tech_stack(self.root)
        layers = {e["layer"]: e["technology"] for e in result}
        self.assertEqual(layers["Framework"], "Vue")
        self.assertEqual(layers["Language"], "TypeScript")
        self.assertEqual(layers["Build Tool"], "Vite")
        self.assertEqual(layers["Testing"], "Vitest")
        self.assertEqual(layers["State Management"], "Pinia")

    def test_falls_back_to_javascript_when_no_typescript(self):
        (self.root / "package.json").write_text(
            json.dumps({"dependencies": {"react": "^18.0.0"}}),
            encoding="utf-8",
        )
        result = _detect_tech_stack(self.root)
        layers = {e["layer"]: e["technology"] for e in result}
        self.assertEqual(layers["Framework"], "React")
        self.assertEqual(layers["Language"], "JavaScript")

    def test_python_manifest_only(self):
        (self.root / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
        result = _detect_tech_stack(self.root)
        layers = {e["layer"]: e["technology"] for e in result}
        self.assertEqual(layers["Language"], "Python")

    def test_empty_when_no_manifests(self):
        self.assertEqual(_detect_tech_stack(self.root), [])

    def test_monorepo_aggregates_workspace_deps(self):
        # Root package.json has only tooling — Vue/TS live in workspace package.
        (self.root / "package.json").write_text(
            json.dumps({
                "name": "root",
                "workspaces": ["packages/*"],
                "devDependencies": {"turbo": "^2.0.0", "eslint": "^9.0.0"},
            }),
            encoding="utf-8",
        )
        ws = self.root / "packages" / "app"
        ws.mkdir(parents=True)
        (ws / "package.json").write_text(
            json.dumps({
                "name": "app",
                "dependencies": {"vue": "^3.0.0", "pinia": "^2.0.0"},
                "devDependencies": {"typescript": "^5.0.0"},
            }),
            encoding="utf-8",
        )
        result = _detect_tech_stack(self.root)
        layers = {e["layer"]: e["technology"] for e in result}
        self.assertEqual(layers.get("Framework"), "Vue")
        self.assertEqual(layers.get("Language"), "TypeScript")
        self.assertEqual(layers.get("State Management"), "Pinia")
        self.assertEqual(layers.get("Monorepo"), "Turborepo")

    def test_first_match_wins_per_layer(self):
        # Both `vue` and `react` in deps — first rule (vue) wins.
        (self.root / "package.json").write_text(
            json.dumps({"dependencies": {"vue": "^3.0.0", "react": "^18.0.0"}}),
            encoding="utf-8",
        )
        result = _detect_tech_stack(self.root)
        framework = [e for e in result if e["layer"] == "Framework"]
        self.assertEqual(len(framework), 1)
        self.assertEqual(framework[0]["technology"], "Vue")


class ExtractKeyCommandsTests(unittest.TestCase):
    """Track 4 Phase 1 — _extract_key_commands reads package.json scripts."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_returns_npm_run_commands(self):
        (self.root / "package.json").write_text(
            json.dumps({
                "scripts": {"build": "tsc && vite build", "test": "vitest"},
            }),
            encoding="utf-8",
        )
        result = _extract_key_commands(self.root)
        commands = {e["command"]: e["description"] for e in result}
        self.assertEqual(commands["npm run build"], "tsc && vite build")
        self.assertEqual(commands["npm run test"], "vitest")

    def test_empty_when_no_package_json(self):
        self.assertEqual(_extract_key_commands(self.root), [])

    def test_empty_when_no_scripts_block(self):
        (self.root / "package.json").write_text("{}", encoding="utf-8")
        self.assertEqual(_extract_key_commands(self.root), [])


class WalkTestFilePathsTests(unittest.TestCase):
    """Track 4 Phase 1 — _walk_test_file_paths discovers test dirs + files."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_finds_test_directories(self):
        (self.root / "tests").mkdir()
        (self.root / "src" / "__tests__").mkdir(parents=True)
        result = _walk_test_file_paths(self.root)
        paths = [e["path"] for e in result]
        self.assertIn("tests", paths)
        self.assertIn("src/__tests__", paths)

    def test_finds_test_files_via_suffix(self):
        (self.root / "src").mkdir()
        (self.root / "src" / "foo.test.ts").write_text("// stub", encoding="utf-8")
        result = _walk_test_file_paths(self.root)
        paths = [e["path"] for e in result]
        self.assertIn("src", paths)

    def test_python_test_files(self):
        (self.root / "lib").mkdir()
        (self.root / "lib" / "test_foo.py").write_text("# stub", encoding="utf-8")
        result = _walk_test_file_paths(self.root)
        paths = [e["path"] for e in result]
        self.assertIn("lib", paths)

    def test_skips_node_modules(self):
        (self.root / "node_modules" / "foo" / "tests").mkdir(parents=True)
        result = _walk_test_file_paths(self.root)
        # node_modules walk pruned — no result inside it.
        paths = [e["path"] for e in result]
        self.assertFalse(any(p.startswith("node_modules") for p in paths))

    def test_empty_project(self):
        self.assertEqual(_walk_test_file_paths(self.root), [])


class BuildCrossModuleDepsTreeTests(unittest.TestCase):
    """Track 4 Phase 1 — _build_cross_module_deps_tree renders ASCII tree."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_workspace_internal_deps(self):
        (self.root / "package.json").write_text(
            json.dumps({"name": "root", "workspaces": ["packages/*"]}),
            encoding="utf-8",
        )
        for sub in ("pkg-a", "pkg-b", "pkg-c"):
            (self.root / "packages" / sub).mkdir(parents=True)
        (self.root / "packages" / "pkg-a" / "package.json").write_text(
            json.dumps({
                "name": "pkg-a",
                "dependencies": {"pkg-b": "*", "pkg-c": "*", "lodash": "^4.0.0"},
            }),
            encoding="utf-8",
        )
        (self.root / "packages" / "pkg-b" / "package.json").write_text(
            json.dumps({"name": "pkg-b", "dependencies": {"pkg-c": "*"}}),
            encoding="utf-8",
        )
        (self.root / "packages" / "pkg-c" / "package.json").write_text(
            json.dumps({"name": "pkg-c"}),
            encoding="utf-8",
        )
        result = _build_cross_module_deps_tree(self.root)
        # External dep `lodash` filtered out (not a workspace package).
        self.assertNotIn("lodash", result)
        self.assertIn("pkg-a", result)
        self.assertIn("  +-- pkg-b", result)
        self.assertIn("  +-- pkg-c", result)

    def test_non_monorepo_lists_root_deps(self):
        (self.root / "package.json").write_text(
            json.dumps({"name": "single-pkg", "dependencies": {"react": "^18.0.0"}}),
            encoding="utf-8",
        )
        result = _build_cross_module_deps_tree(self.root)
        self.assertIn("single-pkg", result)
        self.assertIn("  +-- react", result)

    def test_empty_when_no_package_json(self):
        self.assertEqual(_build_cross_module_deps_tree(self.root), "")


class BuildProjectStructureTreeTests(unittest.TestCase):
    """Track 4 Phase 1 — _build_project_structure_tree renders ASCII tree."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_renders_root_basename(self):
        (self.root / "src").mkdir()
        result = _build_project_structure_tree(self.root)
        self.assertTrue(result.startswith(self.root.name + "/"))
        self.assertIn("src/", result)

    def test_skips_ignored_dirs(self):
        (self.root / "node_modules" / "foo").mkdir(parents=True)
        (self.root / "src").mkdir()
        (self.root / ".git" / "hooks").mkdir(parents=True)
        result = _build_project_structure_tree(self.root)
        self.assertNotIn("node_modules", result)
        self.assertNotIn(".git", result)
        self.assertIn("src/", result)

    def test_max_depth_respected(self):
        # Build 4 levels deep; max_depth=2 should cut at level 2. Use distinct
        # multi-char names so substring matches don't collide with the
        # tempdir basename (which can contain single-letter suffixes).
        deep = self.root / "alpha" / "beta" / "gamma" / "delta"
        deep.mkdir(parents=True)
        result = _build_project_structure_tree(self.root, max_depth=2)
        self.assertIn("alpha/", result)
        self.assertIn("beta/", result)
        self.assertNotIn("gamma/", result)
        self.assertNotIn("delta/", result)

    def test_uses_ascii_connectors(self):
        (self.root / "alpha").mkdir()
        (self.root / "beta").mkdir()
        result = _build_project_structure_tree(self.root)
        # Either ├── or └── must appear.
        self.assertTrue("├── " in result or "└── " in result)

    def test_empty_when_root_missing(self):
        self.assertEqual(_build_project_structure_tree(self.root / "nonexistent"), "")

    def test_fanout_truncation(self):
        for i in range(50):
            (self.root / f"dir{i:02d}").mkdir()
        result = _build_project_structure_tree(self.root, max_fanout=10)
        self.assertIn("more)", result)


class ResolveEffectiveProjectRootTests(unittest.TestCase):
    """Track 4 Phase 1 fix — wrapper-mode picks inner monorepo dir.

    Standalone: project_root has package.json → returned verbatim.
    Wrapper: init.yaml `project_root: <inner>` → returns project_root/<inner>.
    Wrapper without init.yaml: package_paths share first segment → that.
    Fallback: project_root.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir()

    def test_standalone_root_with_package_json(self):
        (self.root / "package.json").write_text("{}", encoding="utf-8")
        result = _resolve_effective_project_root(self.root, self.devforge, [])
        self.assertEqual(result.resolve(), self.root.resolve())

    def test_wrapper_via_init_yaml(self):
        inner = self.root / "inner-monorepo"
        inner.mkdir()
        (inner / "package.json").write_text("{}", encoding="utf-8")
        (self.devforge / "init.yaml").write_text(
            'project_root: "inner-monorepo"\n', encoding="utf-8"
        )
        result = _resolve_effective_project_root(self.root, self.devforge, [])
        self.assertEqual(result.resolve(), inner.resolve())

    def test_wrapper_via_common_path_prefix(self):
        # No package.json at root, no init.yaml — fall through to common-prefix
        # walk over package_paths (mirrors `_resolve_project_label` priority).
        inner = self.root / "monorepo"
        inner.mkdir()
        result = _resolve_effective_project_root(
            self.root,
            self.devforge,
            ["monorepo/apps/a", "monorepo/packages/b"],
        )
        self.assertEqual(result.resolve(), inner.resolve())

    def test_fallback_to_project_root(self):
        # Bare wrapper, no signals → fall back to project_root unchanged.
        result = _resolve_effective_project_root(self.root, self.devforge, [])
        self.assertEqual(result.resolve(), self.root.resolve())

    def test_init_yaml_dot_value_treated_as_standalone(self):
        # `project_root: .` is the standalone-mode marker; ignore it.
        (self.devforge / "init.yaml").write_text("project_root: .\n", encoding="utf-8")
        result = _resolve_effective_project_root(self.root, self.devforge, [])
        self.assertEqual(result.resolve(), self.root.resolve())


class CmdProjectInputWrapperModeTests(unittest.TestCase):
    """Track 4 Phase 1 fix — cmd_project_input mechanical fields read inner monorepo."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir()
        # Wrapper layout: inner/ has package.json + tests/; outer doesn't.
        self.inner = self.root / "monorepo"
        self.inner.mkdir()
        (self.inner / "package.json").write_text(
            json.dumps({
                "name": "root",
                "dependencies": {"vue": "^3.0.0"},
                "scripts": {"build": "vite build"},
            }),
            encoding="utf-8",
        )
        (self.inner / "tests").mkdir()
        (self.devforge / "init.yaml").write_text(
            'project_root: "monorepo"\n', encoding="utf-8"
        )
        # One package overview so cmd_project_input can run.
        path = self.root / "docs" / "monorepo/apps/app" / "overview.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _PKG_OVERVIEW_TEMPLATE.format(
                pkg="monorepo/apps/app", stamp="X", purpose="alpha"
            ),
            encoding="utf-8",
        )

    def test_mechanical_fields_read_inner_monorepo(self):
        args = argparse.Namespace(project="my-proj", devforge_dir=str(self.devforge))
        code, out, err = _run(cmd_project_input, args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        layers = {e["layer"]: e["technology"] for e in payload["tech_stack_candidates"]}
        self.assertEqual(layers.get("Framework"), "Vue")
        self.assertEqual(
            payload["key_commands"],
            [{"command": "npm run build", "description": "vite build"}],
        )
        # Tree rooted at inner monorepo basename, not wrapper.
        self.assertTrue(
            payload["project_structure_tree"].startswith("monorepo/"),
            msg=f"tree did not root at inner: {payload['project_structure_tree'][:80]}",
        )


class CmdProjectInputPhase1FieldsTests(unittest.TestCase):
    """Track 4 Phase 1 — cmd_project_input surfaces 5 new mechanical fields."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir()
        # Minimum viable: one package overview + a package.json so mechanical
        # extractions return non-empty data.
        path = self.root / "docs" / "pkg-a" / "overview.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _PKG_OVERVIEW_TEMPLATE.format(pkg="pkg-a", stamp="X", purpose="alpha"),
            encoding="utf-8",
        )
        (self.root / "package.json").write_text(
            json.dumps({
                "name": "root",
                "dependencies": {"vue": "^3.0.0"},
                "devDependencies": {"typescript": "^5.0.0"},
                "scripts": {"build": "vite build"},
            }),
            encoding="utf-8",
        )
        (self.root / "tests").mkdir()

    def test_phase1_fields_present(self):
        args = argparse.Namespace(project="my-proj", devforge_dir=str(self.devforge))
        code, out, err = _run(cmd_project_input, args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertIn("tech_stack_candidates", payload)
        self.assertIn("key_commands", payload)
        self.assertIn("test_file_paths", payload)
        self.assertIn("cross_module_deps_tree", payload)
        self.assertIn("project_structure_tree", payload)
        # Tech stack populated from package.json.
        layers = {e["layer"]: e["technology"] for e in payload["tech_stack_candidates"]}
        self.assertEqual(layers["Framework"], "Vue")
        self.assertEqual(layers["Language"], "TypeScript")
        # Key commands.
        self.assertEqual(
            payload["key_commands"],
            [{"command": "npm run build", "description": "vite build"}],
        )
        # Test files include `tests` dir.
        test_paths = [e["path"] for e in payload["test_file_paths"]]
        self.assertIn("tests", test_paths)
        # Project structure tree includes root basename.
        self.assertTrue(payload["project_structure_tree"].startswith(self.root.name + "/"))


class WalkEntryPointCandidatesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_finds_main_ts(self):
        (self.root / "src").mkdir()
        (self.root / "src" / "main.ts").write_text("// stub", encoding="utf-8")
        result = _walk_entry_point_candidates(self.root)
        paths = [e["path"] for e in result]
        self.assertIn("src/main.ts", paths)
        labels = {e["path"]: e["label"] for e in result}
        self.assertEqual(labels["src/main.ts"], "App entry")

    def test_finds_router_index(self):
        (self.root / "src" / "router").mkdir(parents=True)
        (self.root / "src" / "router" / "index.ts").write_text("// stub", encoding="utf-8")
        result = _walk_entry_point_candidates(self.root)
        paths = [e["path"] for e in result]
        self.assertIn("src/router/index.ts", paths)
        labels = {e["path"]: e["label"] for e in result}
        self.assertEqual(labels["src/router/index.ts"], "Router")

    def test_finds_plugin_files(self):
        (self.root / "src" / "plugins").mkdir(parents=True)
        (self.root / "src" / "plugins" / "okta.ts").write_text("// stub", encoding="utf-8")
        result = _walk_entry_point_candidates(self.root)
        paths = [e["path"] for e in result]
        self.assertIn("src/plugins/okta.ts", paths)

    def test_skips_node_modules(self):
        (self.root / "node_modules" / "foo" / "src").mkdir(parents=True)
        (self.root / "node_modules" / "foo" / "src" / "main.ts").write_text("// stub", encoding="utf-8")
        result = _walk_entry_point_candidates(self.root)
        paths = [e["path"] for e in result]
        self.assertFalse(any(p.startswith("node_modules") for p in paths))

    def test_empty_when_no_entries(self):
        self.assertEqual(_walk_entry_point_candidates(self.root), [])

    def test_skips_module_barrel_index_outside_entry_dirs(self):
        # locales/<lang>/index.ts is a module barrel, not an app entry —
        # exclude even though `index.ts` appears in _ENTRY_POINT_FILENAMES.
        # Including these produces noise in the orchestrator's compose step
        # (testForge20 has 7 locale index.ts files which polluted candidates).
        deep = self.root / "src" / "locales" / "en"
        deep.mkdir(parents=True)
        (deep / "index.ts").write_text("// stub", encoding="utf-8")
        result = _walk_entry_point_candidates(self.root)
        paths = [e["path"] for e in result]
        self.assertNotIn("src/locales/en/index.ts", paths)

    def test_index_inside_entry_dir_kept(self):
        # `router/index.ts` IS an app entry — keep.
        d = self.root / "src" / "router"
        d.mkdir(parents=True)
        (d / "index.ts").write_text("// stub", encoding="utf-8")
        result = _walk_entry_point_candidates(self.root)
        paths = [e["path"] for e in result]
        self.assertIn("src/router/index.ts", paths)


class WalkRouterRouteFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_finds_router_routes_files(self):
        routes_dir = self.root / "src" / "router" / "routes"
        routes_dir.mkdir(parents=True)
        (routes_dir / "quote.ts").write_text("// stub", encoding="utf-8")
        (routes_dir / "catalog.ts").write_text("// stub", encoding="utf-8")
        result = _walk_router_route_files(self.root)
        self.assertIn("src/router/routes/quote.ts", result)
        self.assertIn("src/router/routes/catalog.ts", result)

    def test_ignores_routes_dir_outside_router(self):
        # `routes/` not under `router/` is unrelated (e.g. server routes).
        d = self.root / "server" / "routes"
        d.mkdir(parents=True)
        (d / "users.ts").write_text("// stub", encoding="utf-8")
        result = _walk_router_route_files(self.root)
        self.assertEqual(result, [])

    def test_empty_when_no_router(self):
        self.assertEqual(_walk_router_route_files(self.root), [])


class WalkNavGuardFilesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_finds_router_guards_dir(self):
        d = self.root / "src" / "helpers" / "router-guards"
        d.mkdir(parents=True)
        (d / "okta-guard.ts").write_text("// stub", encoding="utf-8")
        (d / "identity-guard.ts").write_text("// stub", encoding="utf-8")
        result = _walk_nav_guard_files(self.root)
        self.assertIn("src/helpers/router-guards/okta-guard.ts", result)
        self.assertIn("src/helpers/router-guards/identity-guard.ts", result)

    def test_finds_guards_dir(self):
        d = self.root / "guards"
        d.mkdir()
        (d / "auth.ts").write_text("// stub", encoding="utf-8")
        result = _walk_nav_guard_files(self.root)
        self.assertEqual(result, ["guards/auth.ts"])

    def test_sorted_alphabetically(self):
        d = self.root / "guards"
        d.mkdir()
        for name in ("zebra.ts", "alpha.ts", "mango.ts"):
            (d / name).write_text("// stub", encoding="utf-8")
        result = _walk_nav_guard_files(self.root)
        self.assertEqual(result, ["guards/alpha.ts", "guards/mango.ts", "guards/zebra.ts"])


class ClassifyPackagesTests(unittest.TestCase):
    def test_infrastructure_bucket(self):
        result = _classify_packages(["pkg-acme-common", "foo-types", "pkg-acme-client", "pkg-acme-notifications"])
        self.assertEqual(
            result["infrastructure"],
            sorted(["pkg-acme-common", "foo-types", "pkg-acme-client", "pkg-acme-notifications"]),
        )
        self.assertEqual(result["core"], [])
        self.assertEqual(result["domain"], [])

    def test_core_bucket(self):
        result = _classify_packages(["foo-core"])
        self.assertEqual(result["core"], ["foo-core"])

    def test_domain_residual(self):
        result = _classify_packages(["pkg-acme-quote", "pkg-acme-order", "pkg-acme-catalog"])
        self.assertEqual(
            result["domain"],
            sorted(["pkg-acme-quote", "pkg-acme-order", "pkg-acme-catalog"]),
        )

    def test_first_match_wins(self):
        # `pkg-acme-common-test` matches both `common` (infra) and `test` (infra)
        # — both rules same bucket, first match wins is fine.
        result = _classify_packages(["pkg-acme-common-test"])
        self.assertEqual(result["infrastructure"], ["pkg-acme-common-test"])

    def test_empty_input(self):
        result = _classify_packages([])
        self.assertEqual(result, {"infrastructure": [], "core": [], "domain": []})


class CmdProjectInputPhase2FieldsTests(unittest.TestCase):
    """Track 4 Phase 2 — cmd_project_input surfaces 4 new candidate fields."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir()
        # Minimal viable project with router + guards + workspace pkgs.
        path = self.root / "docs" / "pkg-a" / "overview.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _PKG_OVERVIEW_TEMPLATE.format(pkg="pkg-a", stamp="X", purpose="alpha"),
            encoding="utf-8",
        )
        (self.root / "package.json").write_text(
            json.dumps({
                "name": "root",
                "workspaces": ["packages/*"],
                "dependencies": {"vue": "^3.0.0"},
            }),
            encoding="utf-8",
        )
        (self.root / "packages" / "pkg-common").mkdir(parents=True)
        (self.root / "packages" / "pkg-common" / "package.json").write_text(
            json.dumps({"name": "pkg-common"}),
            encoding="utf-8",
        )
        (self.root / "packages" / "pkg-feature").mkdir(parents=True)
        (self.root / "packages" / "pkg-feature" / "package.json").write_text(
            json.dumps({"name": "pkg-feature"}),
            encoding="utf-8",
        )
        # Entry point + router + guards.
        (self.root / "src").mkdir()
        (self.root / "src" / "main.ts").write_text("// boot", encoding="utf-8")
        (self.root / "src" / "router" / "routes").mkdir(parents=True)
        (self.root / "src" / "router" / "routes" / "home.ts").write_text("// route", encoding="utf-8")
        (self.root / "src" / "helpers" / "router-guards").mkdir(parents=True)
        (self.root / "src" / "helpers" / "router-guards" / "okta-guard.ts").write_text("// guard", encoding="utf-8")

    def test_phase2_fields_present(self):
        args = argparse.Namespace(project="my-proj", devforge_dir=str(self.devforge))
        code, out, err = _run(cmd_project_input, args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertIn("entry_point_candidates", payload)
        self.assertIn("router_route_files", payload)
        self.assertIn("nav_guard_files", payload)
        self.assertIn("package_classification_hints", payload)
        ep_paths = [e["path"] for e in payload["entry_point_candidates"]]
        self.assertIn("src/main.ts", ep_paths)
        self.assertIn("src/router/routes/home.ts", payload["router_route_files"])
        self.assertIn("src/helpers/router-guards/okta-guard.ts", payload["nav_guard_files"])
        # Classification: pkg-common → infrastructure, pkg-feature → domain.
        hints = payload["package_classification_hints"]
        self.assertIn("pkg-common", hints["infrastructure"])
        self.assertIn("pkg-feature", hints["domain"])


class BuildDepGraphMermaidTests(unittest.TestCase):
    """Track 4 Phase 3 — _build_dep_graph_mermaid renders graph TD syntax."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_workspace_internal_deps_emitted(self):
        (self.root / "package.json").write_text(
            json.dumps({"name": "root", "workspaces": ["packages/*"]}),
            encoding="utf-8",
        )
        for sub in ("pkg-a", "pkg-b"):
            (self.root / "packages" / sub).mkdir(parents=True)
        (self.root / "packages" / "pkg-a" / "package.json").write_text(
            json.dumps({"name": "pkg-a", "dependencies": {"pkg-b": "*", "lodash": "^4"}}),
            encoding="utf-8",
        )
        (self.root / "packages" / "pkg-b" / "package.json").write_text(
            json.dumps({"name": "pkg-b"}),
            encoding="utf-8",
        )
        result = _build_dep_graph_mermaid(self.root)
        self.assertTrue(result.startswith("graph TD"))
        self.assertIn("[pkg-a]", result)
        self.assertIn("[pkg-b]", result)
        # External lodash filtered.
        self.assertNotIn("lodash", result)
        # Edge syntax present.
        self.assertIn(" --> ", result)

    def test_no_workspaces_returns_empty(self):
        (self.root / "package.json").write_text(
            json.dumps({"name": "single"}),
            encoding="utf-8",
        )
        self.assertEqual(_build_dep_graph_mermaid(self.root), "")

    def test_no_package_json(self):
        self.assertEqual(_build_dep_graph_mermaid(self.root), "")

    def test_node_id_sanitization(self):
        # Package names with non-alnum chars (e.g. @scope/name) sanitize cleanly.
        (self.root / "package.json").write_text(
            json.dumps({"name": "root", "workspaces": ["packages/*"]}),
            encoding="utf-8",
        )
        ws = self.root / "packages" / "scoped"
        ws.mkdir(parents=True)
        (ws / "package.json").write_text(
            json.dumps({"name": "@scope/pkg-name"}),
            encoding="utf-8",
        )
        result = _build_dep_graph_mermaid(self.root)
        # Node id must be alnum-only (mermaid requirement).
        self.assertIn("[@scope/pkg-name]", result)
        # Verify the id token before `[` contains only alnum.
        for line in result.split("\n"):
            stripped = line.strip()
            if "[" in stripped and not stripped.startswith("graph"):
                node_id = stripped.split("[", 1)[0].strip()
                if node_id:
                    self.assertTrue(
                        node_id.isalnum() or all(c.isalnum() for c in node_id),
                        msg=f"non-alnum node id: {node_id!r}",
                    )


_CONCERN_INDEX_TEMPLATE = """---
concern: {concern}
package: {concern}
files: {files}
source_stamp: stamp-{stamp}
last_indexed: {last_indexed}
---

# {concern}

## Purpose

{purpose}

## Structure

- module.ts — exports
"""


class EnumerateConcernDocsTests(unittest.TestCase):
    """Tests for _enumerate_concern_docs (cases 13-15)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.docs = self.root / "docs"

    def _write_index(self, rel_concern: str, content: str = "stub"):
        path = self.docs / rel_concern / "index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_depth1_index_md_discovered(self):
        self._write_index("main")
        self._write_index("preload")
        result = _enumerate_concern_docs(self.root)
        self.assertEqual(result, ["main", "preload"])

    def test_sorted_output(self):
        self._write_index("zzz-concern")
        self._write_index("aaa-concern")
        self._write_index("mmm-concern")
        result = _enumerate_concern_docs(self.root)
        self.assertEqual(result, sorted(result))

    def test_nested_index_does_not_register_grandparent(self):
        # docs/pkg-a/foo/index.md exists but docs/pkg-a/index.md does NOT.
        # pkg-a must NOT appear in the result.
        nested = self.docs / "pkg-a" / "foo"
        nested.mkdir(parents=True)
        (nested / "index.md").write_text("nested", encoding="utf-8")
        result = _enumerate_concern_docs(self.root)
        self.assertNotIn("pkg-a", result)

    def test_nested_index_does_not_register_when_no_depth1(self):
        # Only nested layout — depth-1 enumerator returns empty list.
        nested = self.docs / "pkg-a" / "foo"
        nested.mkdir(parents=True)
        (nested / "index.md").write_text("nested", encoding="utf-8")
        result = _enumerate_concern_docs(self.root)
        self.assertEqual(result, [])

    def test_grandparent_appears_only_when_depth1_index_also_exists(self):
        # docs/pkg-a/index.md exists AND docs/pkg-a/foo/index.md exists.
        # pkg-a should appear (depth-1), foo should NOT (it's a grandchild of docs/).
        self._write_index("pkg-a")
        nested = self.docs / "pkg-a" / "foo"
        nested.mkdir(parents=True)
        (nested / "index.md").write_text("nested", encoding="utf-8")
        result = _enumerate_concern_docs(self.root)
        self.assertIn("pkg-a", result)
        self.assertNotIn("foo", result)

    def test_non_dir_entries_skipped(self):
        self.docs.mkdir(parents=True, exist_ok=True)
        (self.docs / "some-file.md").write_text("# top-level\n", encoding="utf-8")
        self._write_index("real-concern")
        result = _enumerate_concern_docs(self.root)
        self.assertEqual(result, ["real-concern"])

    def test_missing_docs_dir_returns_empty(self):
        result = _enumerate_concern_docs(self.root)
        self.assertEqual(result, [])

    @unittest.skipUnless(
        hasattr(os, "symlink"), "platform does not support symlinks"
    )
    def test_intra_docs_symlink_not_deduplicated(self):
        # docs/real/index.md exists; docs/alias -> docs/real is a symlink.
        # Both `alias` and `real` are distinct depth-1 dirs so both must appear
        # exactly once. The old resolve()-based path would yield `real` for both,
        # deduplicating them incorrectly; entry.name yields `alias` and `real`.
        self._write_index("real")
        try:
            os.symlink(str(self.docs / "real"), str(self.docs / "alias"))
        except (OSError, NotImplementedError):
            self.skipTest("symlink creation failed on this FS")
        result = _enumerate_concern_docs(self.root)
        self.assertIn("real", result)
        self.assertIn("alias", result)
        # No duplicate entries — both appear exactly once.
        self.assertEqual(result.count("real"), 1)
        self.assertEqual(result.count("alias"), 1)


class ReadConcernSeedTests(unittest.TestCase):
    """Tests for _read_concern_seed (cases 16-18)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def _write_index(self, concern: str, content: str):
        path = self.root / "docs" / concern / "index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_parses_frontmatter_and_purpose(self):
        self._write_index(
            "main",
            _CONCERN_INDEX_TEMPLATE.format(
                concern="main", stamp="abc123", purpose="Main concern purpose.",
                files=3, last_indexed="2026-05-08",
            ),
        )
        seed = _read_concern_seed(self.root, "main")
        self.assertIsNotNone(seed)
        self.assertEqual(seed["package"], "main")
        self.assertEqual(seed["frontmatter"]["source_stamp"], "stamp-abc123")
        self.assertIn("Main concern purpose.", seed["purpose_text"])

    def test_purpose_bounded_at_next_heading(self):
        self._write_index(
            "renderer",
            "---\npackage: \".\"\nsource_stamp: \"xyz\"\n---\n"
            "\n# renderer\n\n## Purpose\n\nRenderer does rendering.\n\n"
            "## Structure\n\n- render.ts\n",
        )
        seed = _read_concern_seed(self.root, "renderer")
        self.assertIsNotNone(seed)
        self.assertIn("Renderer does rendering.", seed["purpose_text"])
        self.assertNotIn("render.ts", seed["purpose_text"])

    def test_package_key_is_concern_name(self):
        self._write_index(
            "worker",
            "---\npackage: \".\"\nsource_stamp: \"s1\"\n---\n\n## Purpose\n\nWorker purpose.\n",
        )
        seed = _read_concern_seed(self.root, "worker")
        self.assertIsNotNone(seed)
        self.assertEqual(seed["package"], "worker")

    def test_missing_file_returns_none(self):
        self.assertIsNone(_read_concern_seed(self.root, "ghost-concern"))

    def test_malformed_frontmatter_returns_none(self):
        self._write_index("bad", "no frontmatter at all\n")
        self.assertIsNone(_read_concern_seed(self.root, "bad"))


class CmdProjectInputConcernFallbackTests(unittest.TestCase):
    """Tests for single-root fallback via concern docs (case 19)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir()

    def _write_concern_index(self, concern: str, stamp: str = "X", purpose: str = "stub purpose"):
        path = self.root / "docs" / concern / "index.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _CONCERN_INDEX_TEMPLATE.format(
                concern=concern, stamp=stamp, purpose=purpose,
                files=2, last_indexed="2026-05-08",
            ),
            encoding="utf-8",
        )

    def test_single_root_fallback_exits_0(self):
        self._write_concern_index("main", stamp="m1", purpose="Main module purpose.")
        self._write_concern_index("renderer", stamp="r1", purpose="Renderer purpose.")
        # Provide a root manifest so mechanical extraction has something.
        (self.root / "package.json").write_text("{}", encoding="utf-8")
        args = argparse.Namespace(project="my-single-root", devforge_dir=str(self.devforge))
        code, out, err = _run(cmd_project_input, args)
        self.assertEqual(code, 0, msg=err)

    def test_single_root_fallback_seeds_from_concerns(self):
        self._write_concern_index("main", stamp="m1", purpose="Main module purpose.")
        self._write_concern_index("renderer", stamp="r1", purpose="Renderer purpose.")
        (self.root / "README.md").write_text("# single-root project\n", encoding="utf-8")
        args = argparse.Namespace(project="single", devforge_dir=str(self.devforge))
        code, out, err = _run(cmd_project_input, args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertEqual(payload["project"], "single")
        self.assertEqual(
            sorted(s["package"] for s in payload["package_seeds"]),
            ["main", "renderer"],
        )
        self.assertRegex(payload["source_stamp"], r"^[0-9a-f]{16}$")
        root_file_paths = [r["path"] for r in payload["project_root_files"]]
        self.assertIn("README.md", root_file_paths)

    def test_single_root_fallback_purpose_text_in_seed(self):
        self._write_concern_index("main", stamp="m1", purpose="The main concern is entry.")
        (self.root / "package.json").write_text("{}", encoding="utf-8")
        args = argparse.Namespace(project="", devforge_dir=str(self.devforge))
        code, out, _ = _run(cmd_project_input, args)
        self.assertEqual(code, 0)
        payload = json.loads(out)
        main_seed = next(s for s in payload["package_seeds"] if s["package"] == "main")
        self.assertIn("The main concern is entry.", main_seed["purpose_text"])

    def test_single_root_fallback_not_triggered_when_overviews_exist(self):
        # Both concern index AND package overview exist — package path wins.
        overview_dir = self.root / "docs" / "pkg-a"
        overview_dir.mkdir(parents=True)
        (overview_dir / "overview.md").write_text(
            _PKG_OVERVIEW_TEMPLATE.format(pkg="pkg-a", stamp="pA", purpose="Pkg-A purpose."),
            encoding="utf-8",
        )
        # Also write a concern index — it should NOT be used.
        self._write_concern_index("main", stamp="m1", purpose="Concern purpose.")
        args = argparse.Namespace(project="", devforge_dir=str(self.devforge))
        code, out, _ = _run(cmd_project_input, args)
        self.assertEqual(code, 0)
        payload = json.loads(out)
        pkg_names = [s["package"] for s in payload["package_seeds"]]
        self.assertIn("pkg-a", pkg_names)
        # concern seed must not appear — package-overview path was taken
        self.assertNotIn("main", pkg_names)

    def test_both_empty_exits_2_with_updated_message(self):
        # No docs/ dir at all — both enumerators return [].
        args = argparse.Namespace(project="", devforge_dir=str(self.devforge))
        code, _, err = _run(cmd_project_input, args)
        self.assertEqual(code, 2)
        self.assertIn("no package overviews or concern docs", err)

    def test_concern_docs_found_but_all_malformed_exits_2(self):
        # docs/bad/index.md exists (no frontmatter) — _enumerate_concern_docs
        # returns ['bad'] but _read_concern_seed returns None → package_seeds == [].
        # Exit code must be 2 AND stderr must use the concern-specific message
        # (not the package-overview message), validating FIX 2's gating logic.
        bad_dir = self.root / "docs" / "bad"
        bad_dir.mkdir(parents=True)
        (bad_dir / "index.md").write_text("no frontmatter here\n", encoding="utf-8")
        args = argparse.Namespace(project="", devforge_dir=str(self.devforge))
        code, _, err = _run(cmd_project_input, args)
        self.assertEqual(code, 2)
        # Concern-path message (FIX 2).
        self.assertIn("concern docs", err)
        self.assertIn("concern index.md", err)
        # Must NOT say "package overviews" (that's the wrong path's message).
        self.assertNotIn("package overviews", err)


class CmdProjectInputRegressionTests(unittest.TestCase):
    """Regression: multi-package path still works after concern fallback added (case 20)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir()

    def _write_overview(self, rel_pkg: str, stamp: str = "X", purpose: str = "stub purpose"):
        path = self.root / "docs" / rel_pkg / "overview.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _PKG_OVERVIEW_TEMPLATE.format(pkg=rel_pkg, stamp=stamp, purpose=purpose),
            encoding="utf-8",
        )

    def test_multi_package_path_unaffected(self):
        self._write_overview("pkg-a", purpose="Alpha.")
        self._write_overview("packages/pkg-b", purpose="Beta.")
        (self.root / "README.md").write_text("# project\n", encoding="utf-8")
        args = argparse.Namespace(project="multi-pkg", devforge_dir=str(self.devforge))
        code, out, err = _run(cmd_project_input, args)
        self.assertEqual(code, 0, msg=err)
        payload = json.loads(out)
        self.assertEqual(payload["project"], "multi-pkg")
        self.assertEqual(len(payload["package_seeds"]), 2)
        self.assertEqual(
            sorted(s["package"] for s in payload["package_seeds"]),
            ["packages/pkg-b", "pkg-a"],
        )


if __name__ == "__main__":
    unittest.main()
