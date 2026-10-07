"""Plan 112 Phase 7 -- the fallback concern for a package with no `src/`.

Every fixture goes through the real chain: `init_helper` setters +
`add-package` (`--no-manifest` / `--manifest`) -> `index_helper build-index`
-> the `_generate_docs` helpers (CLI or the module function under test).
No `init.yaml` / `index.json` is hand-authored.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_LIB_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _generate_docs import _concern_input, _concern_root, _nested_packages  # noqa: E402
from _generate_docs import _package_input, _preflight  # noqa: E402
from _generate_docs._setters_concern import (  # noqa: E402
    _check_tree_entry_coverage,
    _load_index_files,
)
from _generate_docs._validate_doc import _resolve_cite_path  # noqa: E402
from _generate_docs._validators_concern import _check_file_docs_complete  # noqa: E402
from _generate_docs._validators_decomposition import _check_decomposition  # noqa: E402


def _run(script, install_root, *args):
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(install_root / ".devforge")
    env.pop("DEVFORGE_PROJECT_ROOT", None)
    return subprocess.run(
        [sys.executable, str(_LIB_DIR / script)] + list(args),
        env=env, cwd=str(install_root),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )


class _Base(unittest.TestCase):
    """Install root in a temp dir; built through the real producer chain."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir()
        # `project_root` = the directory the planted packages live under
        # (the install root unless a test builds a wrapper install).
        self.project = self.root

    def write(self, rel, text="# a line\n", base=None):
        path = (base or self.project) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def ok(self, script, *args):
        proc = _run(script, self.root, *args)
        self.assertEqual(
            proc.returncode, 0, "{0} {1}: {2}".format(script, args, proc.stderr.decode())
        )
        return proc.stdout.decode()

    def init(self, packages, mode="standalone", project_root="."):
        """`packages`: list of (path, manifest-or-None)."""
        self.ok("init_helper.py", "reset")
        self.ok("init_helper.py", "set-workspace-mode", mode)
        self.ok("init_helper.py", "set-project-root", project_root)
        self.ok("init_helper.py", "set-project-state", "brownfield")
        self.ok("init_helper.py", "set-default-branch", "main")
        for path, manifest in packages:
            flag = ("--manifest", manifest) if manifest else ("--no-manifest",)
            self.ok("init_helper.py", "add-package", "--path", path, *flag)
        self.ok("index_helper.py", "build-index")

    def concern_input(self, pkg, concern, *extra, expect=0):
        proc = _run(
            "generate_docs_helper.py", self.root,
            "concern-input", "--package", pkg, "--concern", concern,
            "--devforge-dir", str(self.devforge), *extra,
        )
        self.assertEqual(proc.returncode, expect, proc.stderr.decode())
        return json.loads(proc.stdout.decode()) if expect == 0 else None

    def plant_terraform(self, pkg="infra/tf"):
        for rel in ("main.tf", "variables.tf", "outputs.tf", "versions.tf",
                    "modules/vpc/main.tf", ".terraform/providers/x.tf",
                    ".terraform.lock.hcl"):
            self.write("{0}/{1}".format(pkg, rel))


class OwnerFallbackTests(_Base):
    def test_fallback_concern_is_dir_basename(self):
        self.write("infra/tf/main.tf")
        self.assertEqual(_concern_root.fallback_concern(self.root, "infra/tf"), "tf")

    def test_not_fallback_with_src_dir(self):
        (self.root / "pkg" / "src").mkdir(parents=True)
        self.assertIsNone(_concern_root.fallback_concern(self.root, "pkg"))

    def test_not_fallback_when_dir_missing(self):
        self.assertIsNone(_concern_root.fallback_concern(self.root, "nope"))

    def test_dot_never_falls_back(self):
        self.write("README.md")
        self.assertIsNone(_concern_root.fallback_concern(self.root, "."))
        self.assertIsNone(_concern_root.fallback_concern(self.root, "./"))

    def test_path_forms_for_fallback_concern(self):
        self.write("infra/tf/main.tf")
        r = self.root
        self.assertEqual(_concern_root.concern_dir(r, "infra/tf", "tf"), r / "infra/tf")
        self.assertEqual(_concern_root.concern_rel_prefix(r, "infra/tf", "tf"), "infra/tf/")
        self.assertEqual(_concern_root.concern_pkg_prefix(r, "infra/tf", "tf"), "")
        self.assertTrue(_concern_root.is_fallback_concern(r, "infra/tf", "tf"))

    def test_other_concern_name_keeps_src_path(self):
        self.write("infra/tf/main.tf")
        r = self.root
        self.assertEqual(
            _concern_root.concern_dir(r, "infra/tf", "other"), r / "infra/tf/src/other"
        )
        self.assertEqual(
            _concern_root.concern_rel_prefix(r, "infra/tf", "other"), "infra/tf/src/other/"
        )
        self.assertEqual(
            _concern_root.concern_pkg_prefix(r, "infra/tf", "other"), "src/other/"
        )
        self.assertFalse(_concern_root.is_fallback_concern(r, "infra/tf", "other"))


class TerraformFallbackChainTests(_Base):
    """The planted `infra/tf` package end to end (Phase 7 Verify, bullet 1-2)."""

    def setUp(self):
        super().setUp()
        self.plant_terraform()
        self.init([("infra/tf", None)])
        self.ok("generate_docs_helper.py", "add-package", "--path", "infra/tf", "--name", "tf")
        self.ok("generate_docs_helper.py", "add-concern", "--package", "infra/tf",
                "--concern", "tf")

    def test_preflight_enumerates_exactly_one_concern(self):
        pairs = _preflight._enumerate_concerns(self.devforge, self.root)
        self.assertEqual(pairs, [("infra/tf", "tf")])

    def test_preflight_cli_reports_new_concern(self):
        out = json.loads(self.ok("generate_docs_helper.py", "preflight",
                                 "--skip-index", "--skip-vue-extract"))
        self.assertEqual(len(out["concerns"]), 1)
        self.assertEqual(out["concerns"][0]["concern"], "tf")
        self.assertEqual(out["concerns"][0]["status"], "new")

    def test_concern_input_lists_tf_files_and_nothing_under_dot_terraform(self):
        out = self.concern_input("infra/tf", "tf")
        paths = [f["path"] for f in out["files"]]
        self.assertEqual(paths, [
            "infra/tf/main.tf", "infra/tf/modules/vpc/main.tf",
            "infra/tf/outputs.tf", "infra/tf/variables.tf", "infra/tf/versions.tf",
        ])
        self.assertFalse([p for p in paths if ".terraform" in p])
        # The walk and the index.json-driven prefix sites see the same set.
        index_files = _load_index_files(self.devforge, "infra/tf")
        self.assertEqual(sorted(p[len("infra/tf/"):] for p in paths), sorted(index_files))
        self.assertEqual(out["subfolder"], "infra/tf/")
        self.assertTrue(out["tree_text"].startswith("infra/tf/"))

    def test_concern_input_unknown_concern_name_still_not_found(self):
        proc = _run("generate_docs_helper.py", self.root, "concern-input",
                    "--package", "infra/tf", "--concern", "other",
                    "--devforge-dir", str(self.devforge))
        self.assertEqual(proc.returncode, 2)
        self.assertIn("concern subfolder not found", proc.stderr.decode())

    def _render_concern_doc(self):
        fm = json.dumps({
            "concern": "tf", "package": "infra/tf", "files": 5,
            "source_stamp": "abc123", "last_indexed": "2026-10-07",
        })
        tree = "infra/tf/\n├── main.tf\n└── variables.tf\n"
        for args in (
            ("init-doc", "--tier", "concern", "--target", "infra/tf/tf",
             "--frontmatter", fm, "--tree", tree),
            ("set-doc-purpose", "--tier", "concern", "--target", "infra/tf/tf",
             "--text", "Root module of the tf package."),
            ("render-doc", "--tier", "concern", "--target", "infra/tf/tf"),
        ):
            self.ok("generate_docs_helper.py", *args)

    def test_init_doc_render_validate_doc_and_cite_backs_resolve(self):
        self._render_concern_doc()
        self.assertTrue((self.root / "docs/infra/tf/tf/index.md").is_file())
        self.ok("generate_docs_helper.py", "validate-doc", "--tier", "concern",
                "--target", "infra/tf/tf", "--devforge-dir", str(self.devforge))
        path, mode = _resolve_cite_path("main.tf", "infra/tf/tf", self.root)
        self.assertEqual(mode, "basename")
        self.assertTrue(path.is_file())
        path, mode = _resolve_cite_path("infra/tf/main.tf", "infra/tf/tf", self.root)
        self.assertEqual(mode, "full")

    def test_prefix_sites_see_the_packages_files(self):
        files = _load_index_files(self.devforge, "infra/tf")
        self.assertIn("main.tf", files)
        self.assertIn("modules/vpc/main.tf", files)
        # set-concern-tree coverage: 5 files + modules + modules/vpc = 7 expected.
        err = _check_tree_entry_coverage("infra/tf/\n├── main.tf\n", "infra/tf", "tf",
                                         self.devforge)
        self.assertIsNotNone(err)
        self.assertIn("expected 7", err)
        self.assertIn("subfolder=<package root>", err)
        # render-file-skeletons writes a skeleton per indexed file, none for .terraform.
        self.ok("generate_docs_helper.py", "render-file-skeletons",
                "--package", "infra/tf", "--concern", "tf")
        docs = self.root / "docs/infra/tf/tf"
        self.assertTrue((docs / "main.tf.md").is_file())
        self.assertTrue((docs / "modules/vpc/main.tf.md").is_file())
        self.assertFalse((docs / ".terraform").exists())
        # validate-concern's file-docs gate expects the same 5 skeletons (empty -> reported).
        errors = _check_file_docs_complete("infra/tf", "tf", self.root, self.devforge)
        self.assertEqual(len(errors), 1)
        self.assertIn("5", json.dumps(errors))

    def test_package_input_one_concern_empty_src_root_and_stable_stamp(self):
        self._render_concern_doc()
        run = lambda: _run("generate_docs_helper.py", self.root, "package-input",
                           "--package", "infra/tf", "--devforge-dir", str(self.devforge))
        first = run()
        self.assertEqual(first.returncode, 0, first.stderr.decode())
        payload = json.loads(first.stdout.decode())
        self.assertEqual([s["concern"] for s in payload["concern_seeds"]], ["tf"])
        self.assertEqual(payload["src_root_files"], [])
        self.assertIn('"src_root_files": []', first.stdout.decode())
        second = json.loads(run().stdout.decode())
        self.assertEqual(second["source_stamp"], payload["source_stamp"])
        self.assertEqual(_package_input._collect_src_root_files(self.root, "infra/tf"),
                         ([], []))
        self.assertEqual(_package_input._enumerate_concerns(self.root, "infra/tf"), ["tf"])

    def test_decomposition_validator_passes(self):
        self.assertEqual(
            _check_decomposition({"concerns": {"tf": {}}}, "infra/tf", self.root), []
        )
        self.assertEqual(_check_decomposition({}, "infra/tf", self.root), [])

    def test_trivial_leaf_below_package_root_still_dropped(self):
        self.write("infra/tf/vendor/x.tf")
        self.init([("infra/tf", None)])
        paths = [f["path"] for f in self.concern_input("infra/tf", "tf")["files"]]
        self.assertFalse([p for p in paths if "vendor" in p])


class PackagePathHoldsTrivialNameTests(_Base):
    """D5 (v) / F21 -- the package's own path components never count."""

    def test_fallback_package_named_build(self):
        self.write("infra/build/main.tf")
        self.write("infra/build/net.tf")
        self.init([("infra/build", None)])
        # Preflight's skip predicate is never applied to the fallback name.
        self.assertEqual(_preflight._enumerate_concerns(self.devforge, self.root),
                         [("infra/build", "build")])
        out = self.concern_input("infra/build", "build")
        self.assertEqual([f["path"] for f in out["files"]],
                         ["infra/build/main.tf", "infra/build/net.tf"])

    def test_src_layout_package_under_assets_path(self):
        self.write("packages/assets/src/ui/button.ts")
        self.write("packages/assets/src/ui/node_modules/x.ts")
        self.init([("packages/assets", None)])
        out = self.concern_input("packages/assets", "ui")
        self.assertEqual([f["path"] for f in out["files"]],
                         ["packages/assets/src/ui/button.ts"])
        self.assertEqual(_preflight._enumerate_concerns(self.devforge, self.root),
                         [("packages/assets", "ui")])

    def test_src_layout_dot_dir_is_not_skipped(self):
        self.write("pkg/src/c/.hidden/f.ts")
        self.write("pkg/src/c/a.ts")
        self.init([("pkg", None)])
        paths = [f["path"] for f in self.concern_input("pkg", "c")["files"]]
        self.assertEqual(paths, ["pkg/src/c/.hidden/f.ts", "pkg/src/c/a.ts"])

    def test_src_layout_dotfile_is_not_skipped(self):
        self.write("pkg/src/c/.env.example")
        self.write("pkg/src/c/a.ts")
        self.init([("pkg", None)])
        paths = [f["path"] for f in self.concern_input("pkg", "c")["files"]]
        self.assertEqual(paths, ["pkg/src/c/.env.example", "pkg/src/c/a.ts"])

    def test_symlinked_src_concern_outside_package_keeps_files(self):
        for rel in ("shared/c/a.ts", "shared/c/x/one.ts", "shared/c/y/two.ts"):
            self.write(rel, "".join("# l{0:03d} ".format(i) + "x" * 60 + "\n" for i in range(30)))
        (self.root / "pkg" / "src").mkdir(parents=True)
        (self.root / "pkg" / "src" / "c").symlink_to(self.root / "shared" / "c")
        self.init([("pkg", None)])
        out = self.concern_input("pkg", "c")
        self.assertEqual([f["path"] for f in out["files"]],
                         ["shared/c/a.ts", "shared/c/x/one.ts", "shared/c/y/two.ts"])

    def test_src_layout_without_trivial_name_output_is_unchanged(self):
        a = "export const a = 1;\n"
        b = "export const b = 2;\n"
        self.write("pkg-a/src/order/a.ts", a)
        self.write("pkg-a/src/order/sub/b.ts", b)
        self.init([("pkg-a", None)])
        out = self.concern_input("pkg-a", "order")
        sha = lambda t: hashlib.sha256(t.encode("utf-8")).hexdigest()
        lines = "\n".join(sorted([
            "pkg-a/src/order/a.ts\t" + sha(a), "pkg-a/src/order/sub/b.ts\t" + sha(b),
        ]))
        self.assertEqual(out["source_stamp"], hashlib.sha256(lines.encode()).hexdigest()[:16])
        self.assertEqual(out["subfolder"], "pkg-a/src/order/")
        self.assertEqual([f["path"] for f in out["files"]],
                         ["pkg-a/src/order/a.ts", "pkg-a/src/order/sub/b.ts"])
        self.assertEqual(out["tree_text"],
                         "pkg-a/src/order/\n├── sub\n│   └── b.ts\n└── a.ts")


class SplitPathTests(_Base):
    def _big(self, rel):
        self.write(rel, "".join("# line {0:03d} ".format(i) + "x" * 60 + "\n" for i in range(30)))

    def test_flat_fallback_package_splits_and_skips_dot_dirs(self):
        for rel in ("a/one.tf", "b/two.tf", ".terraform/p/three.tf", "loose.tf"):
            self._big("infra/big/" + rel)
        self.init([("infra/big", None)])
        out = self.concern_input("infra/big", "big", "--split-threshold-kb", "1")
        self.assertTrue(out["split"])
        self.assertEqual(out["parent_meta"]["subconcern_names"], ["a", "b"])
        self.assertEqual(out["parent_meta"]["loose_files"], ["infra/big/loose.tf"])
        diff = _preflight._diff_concern(
            "infra/big", "big", self.root, self.root / "docs", split_threshold_kb=1
        )
        self.assertTrue(diff["split"])
        self.assertEqual([s["concern"] for s in diff["sub_concerns"]], ["a", "b"])
        self.assertEqual(diff["source_stamp"], out["source_stamp"])

    def test_src_layout_under_trivial_named_path_splits(self):
        for rel in ("x/one.ts", "y/two.ts"):
            self._big("packages/assets/src/ui/" + rel)
        self.init([("packages/assets", None)])
        out = self.concern_input("packages/assets", "ui", "--split-threshold-kb", "1")
        self.assertTrue(out["split"])
        self.assertEqual(out["parent_meta"]["subconcern_names"], ["x", "y"])


class DotPackageTests(_Base):
    def test_standalone_dot_without_src_yields_zero_concerns(self):
        self.write("README.md")
        self.write("docs/note.md")
        self.init([(".", None)])
        self.assertEqual(_preflight._enumerate_concerns(self.devforge, self.root), [])
        self.assertEqual(_package_input._enumerate_concerns(self.root, "."), [])

    def test_monorepo_dot_is_still_skipped(self):
        self.write("src/real/a.ts")
        self.write("infra/tf/main.tf")
        self.init([(".", None), ("infra/tf", None)])
        self.assertEqual(_preflight._enumerate_concerns(self.devforge, self.root),
                         [("infra/tf", "tf")])


class WrapperRootNeverFallsBackTests(_Base):
    """D5 (iii): the indexed project root (`.`) keeps the `src/` requirement."""

    def _wrapper(self, packages):
        self.project = self.root / "inner"
        self.init(packages, mode="wrapper", project_root="inner")

    def test_inner_root_without_src_yields_zero_concerns(self):
        self.write("inner/main.tf", base=self.root)
        self._wrapper([(".", None)])
        self.assertEqual(_preflight._enumerate_concerns(self.devforge, self.root), [])
        self.assertIsNone(_concern_root.fallback_concern(self.root, "inner"))
        proc = _run("generate_docs_helper.py", self.root, "package-input",
                    "--package", "inner", "--devforge-dir", str(self.devforge))
        self.assertEqual(proc.returncode, 2, proc.stderr.decode())
        self.assertIn("no `src/<concern>/` subdirs", proc.stderr.decode())

    def test_inner_root_with_src_keeps_concern(self):
        self.write("inner/src/ui/x.ts", base=self.root)
        self.write("inner/package.json", "{}\n", base=self.root)
        self._wrapper([(".", "package.json")])
        self.assertEqual(_preflight._enumerate_concerns(self.devforge, self.root),
                         [("inner/.", "ui")])

    def test_non_root_package_still_falls_back(self):
        self.write("inner/infra/tf/main.tf", base=self.root)
        self._wrapper([("infra/tf", None)])
        self.assertEqual(_preflight._enumerate_concerns(self.devforge, self.root),
                         [("inner/infra/tf", "tf")])

    def test_unit_index_root_and_no_index(self):
        self.write("inner/main.tf", base=self.root)
        self.write("other/main.tf", base=self.root)
        # No index.json yet: only the literal "." check applies.
        self.assertEqual(_concern_root.fallback_concern(self.root, "inner"), "inner")
        self._wrapper([(".", None)])
        self.assertIsNone(_concern_root.fallback_concern(self.root, "inner"))
        self.assertIsNone(_concern_root.fallback_concern(self.root, "inner/."))
        self.assertEqual(_concern_root.fallback_concern(self.root, "other"), "other")


class NestedPackageExclusionTests(_Base):
    """OQ-5 -- a registered package nested below a fallback package."""

    def _plant(self, base):
        self.write("infra/tf/main.tf", base=base)
        for i in range(6):
            self.write("infra/tf/f{0}.tf".format(i), base=base)
        self.write("infra/tf/app/index.js", base=base)
        self.write("infra/tf/app/package.json", '{"name": "app"}\n', base=base)

    def _assert_walk_and_sites(self, pkg, state_pkg, nested_prefix):
        # Walk (concern-input) and preflight diff.
        out = self.concern_input(pkg, "tf")
        paths = [f["path"] for f in out["files"]]
        self.assertIn(pkg + "/main.tf", paths)
        self.assertFalse([p for p in paths if p.startswith(nested_prefix)], paths)
        pairs = _preflight._enumerate_concerns(self.devforge, self.root)
        self.assertIn((pkg, "tf"), pairs)
        diff = _preflight._diff_concern(
            pkg, "tf", self.root, self.root / "docs",
            exclude_rels=_nested_packages.fallback_excluded_rels(self.devforge, pkg, "tf"),
        )
        self.assertEqual(diff["source_stamp"], out["source_stamp"])
        # index.json prefix sites.
        self.assertIn("app/index.js", _load_index_files(self.devforge, state_pkg))
        self.ok("generate_docs_helper.py", "add-package", "--path", state_pkg, "--name", "tf")
        self.ok("generate_docs_helper.py", "add-concern", "--package", state_pkg,
                "--concern", "tf")
        self.ok("generate_docs_helper.py", "render-file-skeletons",
                "--package", state_pkg, "--concern", "tf")
        docs = self.root / "docs" / state_pkg / "tf"
        self.assertTrue((docs / "main.tf.md").is_file())
        self.assertFalse((docs / "app").exists())
        # 7 .tf files expected, nested app files not counted.
        errors = _check_file_docs_complete(state_pkg, "tf", self.root, self.devforge)
        self.assertIn("7", json.dumps(errors))
        self.assertNotIn("app/index", json.dumps(errors))
        err = _check_tree_entry_coverage("x/\n├── main.tf\n", state_pkg, "tf", self.devforge)
        self.assertIn("expected 7", err)

    def test_standalone(self):
        self._plant(self.root)
        self.init([("infra/tf", None), ("infra/tf/app", "package.json")])
        self.assertEqual(
            _nested_packages.nested_package_rels(self.devforge, "infra/tf"), ["app"]
        )
        self._assert_walk_and_sites("infra/tf", "infra/tf", "infra/tf/app/")

    def test_wrapper_install_root_differs_from_index_project_root(self):
        inner = self.root / "inner"
        self._plant(inner)
        self.project = inner
        self.init([("infra/tf", None), ("infra/tf/app", "package.json")],
                  mode="wrapper", project_root="inner")
        index = json.loads((self.devforge / "index.json").read_text(encoding="utf-8"))
        self.assertNotEqual(Path(index["project_root"]).resolve(), self.root)
        self.assertEqual(
            _nested_packages.nested_package_rels(self.devforge, "inner/infra/tf"), ["app"]
        )
        self._assert_walk_and_sites("inner/infra/tf", "inner/infra/tf", "inner/infra/tf/app/")

    def test_src_concern_does_not_exclude(self):
        self.write("pkg/src/c/a.ts")
        self.write("pkg/src/c/inner/b.ts")
        self.write("pkg/src/c/inner/package.json", "{}\n")
        self.init([("pkg", None), ("pkg/src/c/inner", "package.json")])
        paths = [f["path"] for f in self.concern_input("pkg", "c")["files"]]
        self.assertIn("pkg/src/c/inner/b.ts", paths)
        self.assertEqual(_nested_packages.fallback_excluded_rels(self.devforge, "pkg", "c"), [])


class NestedPackagesUnitTests(_Base):
    def test_under_any(self):
        self.assertTrue(_nested_packages.under_any("app/x.js", ["app"]))
        self.assertTrue(_nested_packages.under_any("app", ["app"]))
        self.assertFalse(_nested_packages.under_any("apple/x.js", ["app"]))
        self.assertFalse(_nested_packages.under_any("x.js", []))

    def test_load_index_missing_or_malformed(self):
        self.assertIsNone(_nested_packages.load_index(self.devforge))
        (self.devforge / "index.json").write_text("not json", encoding="utf-8")
        self.assertIsNone(_nested_packages.load_index(self.devforge))
        (self.devforge / "index.json").write_text("[]", encoding="utf-8")
        self.assertIsNone(_nested_packages.load_index(self.devforge))
        self.assertEqual(_nested_packages.nested_package_rels(self.devforge, "x"), [])

    def test_bridge_prefix_edge_cases(self):
        self.assertEqual(_nested_packages.bridge_prefix({}, self.root), "")
        self.assertEqual(_nested_packages.bridge_prefix({"project_root": ""}, self.root), "")
        self.assertEqual(
            _nested_packages.bridge_prefix({"project_root": str(self.root)}, self.root), ""
        )
        self.assertEqual(
            _nested_packages.bridge_prefix(
                {"project_root": str(self.root / "inner")}, self.root), "inner/"
        )
        # An index root outside the install root cannot be bridged.
        self.assertEqual(
            _nested_packages.bridge_prefix({"project_root": "/"}, self.root), ""
        )


class EnumerateImmediateDirsTests(_Base):
    def test_package_root_components_not_tested(self):
        base = self.root / "packages" / "assets" / "src" / "ui"
        for n in ("a", "b", "dist", ".hid"):
            (base / n).mkdir(parents=True)
        pkg_root = self.root / "packages" / "assets"
        names = _concern_input._enumerate_immediate_dirs(base, self.root, pkg_root)
        self.assertEqual(names, [".hid", "a", "b"])

    def test_skip_hidden_and_exclude(self):
        base = self.root / "infra" / "tf"
        for n in ("a", ".terraform", "app"):
            (base / n).mkdir(parents=True)
        names = _concern_input._enumerate_immediate_dirs(
            base, self.root, base, skip_hidden=True, exclude_rels=["app"]
        )
        self.assertEqual(names, ["a"])


if __name__ == "__main__":
    unittest.main()
