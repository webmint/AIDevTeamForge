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
 11.  cmd_project_input: no package overviews → exit 2
 12.  cmd_project_input: --project label override

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

from _generate_docs._project_input import (  # noqa: E402
    _build_cross_module_deps_tree,
    _build_project_structure_tree,
    _collect_project_root_files,
    _compute_source_stamp,
    _detect_tech_stack,
    _enumerate_packages_with_overviews,
    _extract_key_commands,
    _read_package_seed,
    _resolve_effective_project_root,
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

    def test_no_package_overviews_exit_2(self):
        args = argparse.Namespace(project="", devforge_dir=str(self.devforge))
        code, _, err = _run(cmd_project_input, args)
        self.assertEqual(code, 2)
        self.assertIn("no package overviews", err)

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
        path = self.root / "docs" / "monorepo/apps/app-web" / "overview.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _PKG_OVERVIEW_TEMPLATE.format(
                pkg="monorepo/apps/app-web", stamp="X", purpose="alpha"
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


if __name__ == "__main__":
    unittest.main()
