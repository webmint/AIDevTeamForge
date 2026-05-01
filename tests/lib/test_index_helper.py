"""Tests for src/devforge/lib/index_helper.py.

Covers the build-index subcommand end-to-end: file walking, manifest
detection across all supported ecosystems, atomic writes, idempotency,
and the round-trip path from a real init.yaml (produced by
init_helper.py) through index.json + docs/structure.md.

Each test runs in its own `tempfile.TemporaryDirectory` and points the
helper at it via `DEVFORGE_DIR`. End-to-end tests invoke index_helper.py
as a subprocess, exercising the real argparse + dispatch path. Round-
trip tests pre-populate init.yaml via the init_helper CLI before
running build-index, so the on-disk yaml is always the helper's own
output (no hand-authored fixtures).

Stdlib only.
"""

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_INDEX_PY = _LIB_DIR / "index_helper.py"
_INDEX_LAUNCHER = _LIB_DIR / "index_helper"
_INIT_PY = _LIB_DIR / "init_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import index_helper  # noqa: E402
import init_helper  # noqa: E402


def _run_index(devforge_dir, *args):
    """Invoke `index_helper.py <args>` as a subprocess."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_INDEX_PY)] + list(args),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _run_init(devforge_dir, *args):
    """Invoke `init_helper.py <args>` as a subprocess.

    Used to pre-populate `init.yaml` via the real CLI rather than hand-
    authored fixtures, so the parser always sees what the emitter
    actually emits.
    """
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_INIT_PY)] + list(args),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _run_index_launcher(devforge_dir, *args):
    """Invoke the POSIX shell launcher as a subprocess."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        ["sh", str(_INDEX_LAUNCHER)] + list(args),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class _EnvIsolationMixin:
    """Save/restore DEVFORGE_DIR around each test + provide a tmp project."""

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        # Layout mimics a real install: <project>/.devforge/ holds state,
        # the project root is the parent.
        self.project_root = Path(self._tmp.name)
        self.devforge_dir = self.project_root / ".devforge"
        self.devforge_dir.mkdir()
        self.index_path = self.devforge_dir / index_helper.INDEX_FILE_NAME
        self.structure_path = self.project_root / index_helper.STRUCTURE_DOC_REL

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    def _seed_init_yaml(self, packages, project_root_value="."):
        """Write a minimal init.yaml using the real init_helper CLI.

        `packages` is a list of `{"path": ..., "manifest": ...}`. The
        scalar fields are filled with placeholder values so init.yaml
        passes its own shape checks.
        """
        proc = _run_init(self.devforge_dir, "reset")
        assert proc.returncode == 0, proc.stderr
        proc = _run_init(
            self.devforge_dir, "set-workspace-mode", "standalone",
        )
        assert proc.returncode == 0, proc.stderr
        proc = _run_init(
            self.devforge_dir, "set-project-root", project_root_value,
        )
        assert proc.returncode == 0, proc.stderr
        proc = _run_init(
            self.devforge_dir, "set-project-state", "brownfield",
        )
        assert proc.returncode == 0, proc.stderr
        proc = _run_init(
            self.devforge_dir, "set-default-branch", "main",
        )
        assert proc.returncode == 0, proc.stderr
        for pkg in packages:
            proc = _run_init(
                self.devforge_dir, "add-package",
                "--path", pkg["path"],
                "--manifest", pkg["manifest"],
            )
            assert proc.returncode == 0, proc.stderr


# ---------------------------------------------------------------------------
# File-walker tests.
# ---------------------------------------------------------------------------


class FileListingTests(_EnvIsolationMixin, unittest.TestCase):
    """`_list_package_files` filtering rules — one assertion class per
    skip-list/limit edge case."""

    def test_files_listing_excludes_node_modules_and_hidden(self):
        # Layout: src/main.ts (kept) + node_modules/foo.ts (skipped) +
        # .git/HEAD (skipped) + dist/bundle.js (skipped) + .DS_Store
        # (hidden file, skipped).
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        (pkg / "src").mkdir()
        (pkg / "src" / "main.ts").write_text("//", encoding="utf-8")
        (pkg / "node_modules").mkdir()
        (pkg / "node_modules" / "foo.ts").write_text("//", encoding="utf-8")
        (pkg / ".git").mkdir()
        (pkg / ".git" / "HEAD").write_text("ref", encoding="utf-8")
        (pkg / "dist").mkdir()
        (pkg / "dist" / "bundle.js").write_text("//", encoding="utf-8")
        (pkg / ".DS_Store").write_text("", encoding="utf-8")
        files, truncated = index_helper._list_package_files(pkg)
        self.assertEqual(files, ["src/main.ts"])
        self.assertFalse(truncated)

    def test_files_listing_truncates_at_500(self):
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        # 600 sibling files exceeds the cap of 500.
        for i in range(600):
            (pkg / "f{0:04d}.txt".format(i)).write_text("x", encoding="utf-8")
        files, truncated = index_helper._list_package_files(pkg)
        self.assertEqual(len(files), 500)
        self.assertTrue(truncated)

    def test_files_listing_empty_package(self):
        pkg = self.project_root / "empty"
        pkg.mkdir()
        files, truncated = index_helper._list_package_files(pkg)
        self.assertEqual(files, [])
        self.assertFalse(truncated)


# ---------------------------------------------------------------------------
# Manifest parser tests — one class per ecosystem.
# ---------------------------------------------------------------------------


class PackageJsonParseTests(_EnvIsolationMixin, unittest.TestCase):

    def test_package_json_scripts_and_deps_parsed(self):
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        manifest = pkg / "package.json"
        manifest.write_text(json.dumps({
            "name": "demo",
            "scripts": {"build": "vite build", "test": "vitest"},
            "dependencies": {"vue": "^3.4.0", "axios": "^1.0.0"},
            "devDependencies": {"vitest": "^1.0.0"},
        }), encoding="utf-8")
        scripts, deps, ok = index_helper._parse_package_json(manifest)
        self.assertTrue(ok)
        self.assertEqual(scripts, {"build": "vite build", "test": "vitest"})
        # Order: dependencies block first, then devDependencies.
        names = [d["name"] for d in deps]
        self.assertIn("vue", names)
        self.assertIn("axios", names)
        self.assertIn("vitest", names)
        # Each dep has both name + version.
        for dep in deps:
            self.assertIn("name", dep)
            self.assertIn("version", dep)


class CargoTomlParseTests(_EnvIsolationMixin, unittest.TestCase):

    def test_cargo_toml_deps_parsed(self):
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        manifest = pkg / "Cargo.toml"
        manifest.write_text(
            '[package]\nname = "demo"\nversion = "0.1.0"\n'
            '\n[dependencies]\nserde = "1.0"\n'
            'tokio = { version = "1.30", features = ["full"] }\n'
            '\n[dev-dependencies]\ncriterion = "0.5"\n',
            encoding="utf-8",
        )
        scripts, deps, ok = index_helper._parse_cargo_toml(manifest)
        self.assertTrue(ok)
        self.assertEqual(scripts, {})
        names = [d["name"] for d in deps]
        self.assertIn("serde", names)
        self.assertIn("tokio", names)
        self.assertIn("criterion", names)


class PyprojectPoetryParseTests(_EnvIsolationMixin, unittest.TestCase):

    def test_pyproject_toml_poetry_format(self):
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        manifest = pkg / "pyproject.toml"
        manifest.write_text(
            '[tool.poetry]\nname = "demo"\nversion = "0.1.0"\n'
            '\n[tool.poetry.dependencies]\n'
            'python = "^3.10"\nrequests = "^2.31"\n'
            '\n[tool.poetry.dev-dependencies]\npytest = "^8.0"\n'
            '\n[tool.poetry.scripts]\ncli = "demo.main:run"\n',
            encoding="utf-8",
        )
        scripts, deps, ok = index_helper._parse_pyproject_toml(manifest)
        self.assertTrue(ok)
        self.assertEqual(scripts, {"cli": "demo.main:run"})
        names = [d["name"] for d in deps]
        self.assertIn("requests", names)
        self.assertIn("pytest", names)


class PyprojectPep621ParseTests(_EnvIsolationMixin, unittest.TestCase):

    def test_pyproject_toml_pep621_inline_format(self):
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        manifest = pkg / "pyproject.toml"
        manifest.write_text(
            '[project]\nname = "demo"\nversion = "0.1.0"\n'
            'dependencies = ["requests>=2.31", "click==8.1"]\n',
            encoding="utf-8",
        )
        scripts, deps, ok = index_helper._parse_pyproject_toml(manifest)
        self.assertTrue(ok)
        names = [d["name"] for d in deps]
        self.assertIn("requests", names)
        self.assertIn("click", names)

    def test_pyproject_toml_pep621_multiline_format(self):
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        manifest = pkg / "pyproject.toml"
        manifest.write_text(
            '[project]\nname = "demo"\nversion = "0.1.0"\n'
            'dependencies = [\n'
            '    "requests>=2.31",\n'
            '    "click==8.1",\n'
            ']\n',
            encoding="utf-8",
        )
        scripts, deps, ok = index_helper._parse_pyproject_toml(manifest)
        self.assertTrue(ok)
        names = [d["name"] for d in deps]
        self.assertIn("requests", names)
        self.assertIn("click", names)


class GoModParseTests(_EnvIsolationMixin, unittest.TestCase):

    def test_go_mod_require_block_parsed(self):
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        manifest = pkg / "go.mod"
        manifest.write_text(
            "module example.com/demo\n"
            "\n"
            "go 1.21\n"
            "\n"
            "require (\n"
            "    github.com/stretchr/testify v1.8.4\n"
            "    golang.org/x/text v0.14.0\n"
            ")\n",
            encoding="utf-8",
        )
        scripts, deps, ok = index_helper._parse_go_mod(manifest)
        self.assertTrue(ok)
        self.assertEqual(scripts, {})
        names = [d["name"] for d in deps]
        self.assertIn("github.com/stretchr/testify", names)
        self.assertIn("golang.org/x/text", names)

    def test_go_mod_single_line_require(self):
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        manifest = pkg / "go.mod"
        manifest.write_text(
            "module example.com/demo\n"
            "\n"
            "require github.com/stretchr/testify v1.8.4\n",
            encoding="utf-8",
        )
        scripts, deps, ok = index_helper._parse_go_mod(manifest)
        self.assertTrue(ok)
        names = [d["name"] for d in deps]
        self.assertIn("github.com/stretchr/testify", names)


class RequirementsTxtParseTests(_EnvIsolationMixin, unittest.TestCase):

    def test_requirements_txt_basic(self):
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        manifest = pkg / "requirements.txt"
        manifest.write_text(
            "# top-level deps\n"
            "requests>=2.31\n"
            "click==8.1.0\n"
            "-r other.txt\n"  # skipped (directive)
            "\n"
            "flask  # web framework\n",
            encoding="utf-8",
        )
        scripts, deps, ok = index_helper._parse_requirements_txt(manifest)
        self.assertTrue(ok)
        names = [d["name"] for d in deps]
        self.assertIn("requests", names)
        self.assertIn("click", names)
        self.assertIn("flask", names)
        self.assertNotIn("-r", names)


class GemfileParseTests(_EnvIsolationMixin, unittest.TestCase):

    def test_gemfile_gem_lines_parsed(self):
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        manifest = pkg / "Gemfile"
        manifest.write_text(
            'source "https://rubygems.org"\n'
            '\n'
            'gem "rails", "7.1.0"\n'
            'gem "puma"\n'
            '# gem "commented-out"\n',
            encoding="utf-8",
        )
        scripts, deps, ok = index_helper._parse_gemfile(manifest)
        self.assertTrue(ok)
        names = [d["name"] for d in deps]
        self.assertIn("rails", names)
        self.assertIn("puma", names)
        self.assertNotIn("commented-out", names)


class PomXmlParseTests(_EnvIsolationMixin, unittest.TestCase):

    def test_pom_xml_dependencies_parsed(self):
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        manifest = pkg / "pom.xml"
        manifest.write_text(
            '<project>\n'
            '  <dependencies>\n'
            '    <dependency>\n'
            '      <groupId>org.springframework</groupId>\n'
            '      <artifactId>spring-core</artifactId>\n'
            '      <version>6.1.0</version>\n'
            '    </dependency>\n'
            '    <dependency>\n'
            '      <groupId>junit</groupId>\n'
            '      <artifactId>junit</artifactId>\n'
            '      <version>4.13.2</version>\n'
            '    </dependency>\n'
            '  </dependencies>\n'
            '</project>\n',
            encoding="utf-8",
        )
        scripts, deps, ok = index_helper._parse_pom_xml(manifest)
        self.assertTrue(ok)
        names = [d["name"] for d in deps]
        self.assertIn("org.springframework:spring-core", names)
        self.assertIn("junit:junit", names)


class GradleParseTests(_EnvIsolationMixin, unittest.TestCase):

    def test_build_gradle_implementation_lines(self):
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        manifest = pkg / "build.gradle"
        manifest.write_text(
            "dependencies {\n"
            "    implementation 'org.springframework:spring-core:6.1.0'\n"
            "    testImplementation 'junit:junit:4.13.2'\n"
            "}\n",
            encoding="utf-8",
        )
        scripts, deps, ok = index_helper._parse_build_gradle(manifest)
        self.assertTrue(ok)
        names = [d["name"] for d in deps]
        self.assertIn("org.springframework:spring-core", names)
        self.assertIn("junit:junit", names)


class CsprojParseTests(_EnvIsolationMixin, unittest.TestCase):

    def test_csproj_packagereference_parsed(self):
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        manifest = pkg / "MyApp.csproj"
        manifest.write_text(
            '<Project Sdk="Microsoft.NET.Sdk">\n'
            '  <ItemGroup>\n'
            '    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />\n'
            '    <PackageReference Include="Serilog" Version="3.1.0" />\n'
            '  </ItemGroup>\n'
            '</Project>\n',
            encoding="utf-8",
        )
        scripts, deps, ok = index_helper._parse_csproj(manifest)
        self.assertTrue(ok)
        names = [d["name"] for d in deps]
        self.assertIn("Newtonsoft.Json", names)
        self.assertIn("Serilog", names)


class ComposerJsonParseTests(_EnvIsolationMixin, unittest.TestCase):

    def test_composer_json_scripts_and_deps_parsed(self):
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        manifest = pkg / "composer.json"
        manifest.write_text(json.dumps({
            "name": "demo/app",
            "scripts": {"test": "phpunit"},
            "require": {"php": "^8.1", "symfony/console": "^6.0"},
            "require-dev": {"phpunit/phpunit": "^10.0"},
        }), encoding="utf-8")
        scripts, deps, ok = index_helper._parse_composer_json(manifest)
        self.assertTrue(ok)
        self.assertEqual(scripts, {"test": "phpunit"})
        names = [d["name"] for d in deps]
        self.assertIn("symfony/console", names)
        self.assertIn("phpunit/phpunit", names)


# ---------------------------------------------------------------------------
# build-index integration tests (subprocess invocation).
# ---------------------------------------------------------------------------


class BuildIndexEndToEndTests(_EnvIsolationMixin, unittest.TestCase):

    def test_full_build_index_produces_both_artifacts(self):
        # Two packages with different ecosystems.
        ts_pkg = self.project_root / "apps" / "web"
        ts_pkg.mkdir(parents=True)
        (ts_pkg / "package.json").write_text(json.dumps({
            "name": "web",
            "scripts": {"dev": "vite"},
            "dependencies": {"vue": "^3.4.0"},
        }), encoding="utf-8")
        (ts_pkg / "src").mkdir()
        (ts_pkg / "src" / "main.ts").write_text("//", encoding="utf-8")

        rust_pkg = self.project_root / "crates" / "core"
        rust_pkg.mkdir(parents=True)
        (rust_pkg / "Cargo.toml").write_text(
            '[package]\nname = "core"\nversion = "0.1.0"\n'
            '\n[dependencies]\nserde = "1.0"\n',
            encoding="utf-8",
        )
        (rust_pkg / "src").mkdir()
        (rust_pkg / "src" / "lib.rs").write_text("// lib", encoding="utf-8")

        self._seed_init_yaml([
            {"path": "apps/web", "manifest": "package.json"},
            {"path": "crates/core", "manifest": "Cargo.toml"},
        ])

        proc = _run_index(self.devforge_dir, "build-index")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # index.json shape.
        self.assertTrue(self.index_path.exists())
        index = json.loads(self.index_path.read_text(encoding="utf-8"))
        self.assertEqual(index["version"], 1)
        self.assertIn("apps/web", index["packages"])
        self.assertIn("crates/core", index["packages"])
        web = index["packages"]["apps/web"]
        self.assertEqual(web["manifest_file"], "package.json")
        self.assertIn("src/main.ts", web["files"])
        self.assertEqual(web["scripts"], {"dev": "vite"})
        self.assertEqual(
            [{"name": "vue", "version": "^3.4.0"}], web["manifest_deps"],
        )
        core = index["packages"]["crates/core"]
        self.assertEqual(core["manifest_file"], "Cargo.toml")
        self.assertIn("src/lib.rs", core["files"])
        self.assertEqual(
            [{"name": "serde", "version": "1.0"}], core["manifest_deps"],
        )
        # structure.md shape.
        self.assertTrue(self.structure_path.exists())
        text = self.structure_path.read_text(encoding="utf-8")
        self.assertIn("# Workspace Structure", text)
        self.assertIn("| Package |", text)
        self.assertIn("apps/web", text)
        self.assertIn("crates/core", text)

    def test_no_manifest_emits_empty_scripts_and_deps(self):
        # Package directory exists but has no recognized manifest file.
        # build-index should still produce a record with `manifest_file: null`,
        # `scripts: {}`, `manifest_deps: []`, `manifest_parse_skipped: false`.
        pkg = self.project_root / "lib"
        pkg.mkdir()
        (pkg / "main.txt").write_text("x", encoding="utf-8")
        # NB: init.yaml requires a `manifest` for each package, so we
        # simulate "no manifest" by referencing a manifest filename that
        # doesn't exist on disk. The init record stores its manifest tag
        # but `_detect_manifest` finds nothing.
        self._seed_init_yaml([
            {"path": "lib", "manifest": "package.json"},
        ])
        proc = _run_index(self.devforge_dir, "build-index")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        index = json.loads(self.index_path.read_text(encoding="utf-8"))
        rec = index["packages"]["lib"]
        self.assertIsNone(rec["manifest_file"])
        self.assertEqual(rec["scripts"], {})
        self.assertEqual(rec["manifest_deps"], [])
        self.assertFalse(rec["manifest_parse_skipped"])

    def test_unsupported_manifest_emits_skipped_flag(self):
        # Malformed JSON in package.json -> parse_ok=False in parser ->
        # manifest_parse_skipped=true on the index record. Other packages
        # in the same run must still succeed.
        bad_pkg = self.project_root / "bad"
        bad_pkg.mkdir()
        (bad_pkg / "package.json").write_text(
            "{not valid json", encoding="utf-8",
        )
        good_pkg = self.project_root / "good"
        good_pkg.mkdir()
        (good_pkg / "package.json").write_text(json.dumps({
            "name": "good",
            "dependencies": {"vue": "^3"},
        }), encoding="utf-8")
        self._seed_init_yaml([
            {"path": "bad", "manifest": "package.json"},
            {"path": "good", "manifest": "package.json"},
        ])
        proc = _run_index(self.devforge_dir, "build-index")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # Stderr surfaces a warning.
        self.assertIn(b"failed to parse manifest", proc.stderr)
        index = json.loads(self.index_path.read_text(encoding="utf-8"))
        # Bad package: skipped flag set, manifest_file recorded so the
        # consumer sees a parse was attempted.
        self.assertTrue(index["packages"]["bad"]["manifest_parse_skipped"])
        self.assertEqual(
            index["packages"]["bad"]["manifest_file"], "package.json",
        )
        # Good package: still parsed cleanly.
        self.assertFalse(index["packages"]["good"]["manifest_parse_skipped"])
        self.assertEqual(
            [{"name": "vue", "version": "^3"}],
            index["packages"]["good"]["manifest_deps"],
        )

    def test_init_yaml_missing_fails_cleanly(self):
        # No init.yaml at all. build-index must exit 2 with a clear
        # error, not a stack trace.
        proc = _run_index(self.devforge_dir, "build-index")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"init.yaml not found", proc.stderr)
        # Side effect: index.json must NOT be created when init.yaml is
        # missing (the run aborted before the write step).
        self.assertFalse(self.index_path.exists())

    def test_idempotent_re_run(self):
        # Run build-index twice with identical inputs. Both index.json
        # and structure.md must be byte-identical EXCEPT for the
        # generated_at timestamp (which legitimately differs between
        # invocations). We strip the timestamp and compare the rest.
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        (pkg / "package.json").write_text(json.dumps({
            "name": "pkg", "dependencies": {"vue": "^3"},
        }), encoding="utf-8")
        self._seed_init_yaml([
            {"path": "pkg", "manifest": "package.json"},
        ])
        proc1 = _run_index(self.devforge_dir, "build-index")
        self.assertEqual(proc1.returncode, 0, proc1.stderr)
        index1 = json.loads(self.index_path.read_text(encoding="utf-8"))
        struct1 = self.structure_path.read_text(encoding="utf-8")

        # Sleep 1.1s so generated_at provably differs (1-second
        # resolution in the ISO timestamp).
        time.sleep(1.1)
        proc2 = _run_index(self.devforge_dir, "build-index")
        self.assertEqual(proc2.returncode, 0, proc2.stderr)
        index2 = json.loads(self.index_path.read_text(encoding="utf-8"))
        struct2 = self.structure_path.read_text(encoding="utf-8")

        # generated_at allowed to differ.
        self.assertNotEqual(index1["generated_at"], index2["generated_at"])
        # Strip generated_at + recompare.
        index1.pop("generated_at")
        index2.pop("generated_at")
        self.assertEqual(index1, index2)
        # structure.md: replace the timestamp line with a placeholder
        # in both copies before comparing.
        def _strip_ts(text):
            # The timestamp lives on the "Generated by ... on <ts>." line.
            lines = text.splitlines()
            for i, ln in enumerate(lines):
                if ln.startswith("Generated by"):
                    lines[i] = "Generated by ... on <TS>."
            return "\n".join(lines)
        self.assertEqual(_strip_ts(struct1), _strip_ts(struct2))

    def test_atomic_write_no_temp_files_after_success(self):
        # After a successful build-index run, no `.tmp` files should
        # remain in the .devforge or docs directories — the atomic-write
        # contract says temp files are renamed, never left behind.
        pkg = self.project_root / "pkg"
        pkg.mkdir()
        (pkg / "package.json").write_text("{}", encoding="utf-8")
        self._seed_init_yaml([
            {"path": "pkg", "manifest": "package.json"},
        ])
        proc = _run_index(self.devforge_dir, "build-index")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # Walk every directory and assert no `.tmp`-suffixed leftovers.
        leftovers = []
        for root, dirs, fnames in os.walk(str(self.project_root)):
            for fname in fnames:
                if fname.endswith(".tmp"):
                    leftovers.append(os.path.join(root, fname))
        self.assertEqual(leftovers, [], "leftover temp files: {0}".format(leftovers))

    def test_files_truncated_flag_propagates_to_index(self):
        # End-to-end check that files_truncated: true shows up in
        # index.json when a package exceeds 500 files.
        pkg = self.project_root / "huge"
        pkg.mkdir()
        for i in range(550):
            (pkg / "f{0:04d}.txt".format(i)).write_text("x", encoding="utf-8")
        # Need a manifest so init.yaml `manifest` value is non-empty.
        (pkg / "package.json").write_text("{}", encoding="utf-8")
        self._seed_init_yaml([
            {"path": "huge", "manifest": "package.json"},
        ])
        proc = _run_index(self.devforge_dir, "build-index")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        index = json.loads(self.index_path.read_text(encoding="utf-8"))
        rec = index["packages"]["huge"]
        self.assertTrue(rec["files_truncated"])
        self.assertEqual(len(rec["files"]), 500)


# ---------------------------------------------------------------------------
# Launcher (POSIX shell) tests.
# ---------------------------------------------------------------------------


class LauncherTests(_EnvIsolationMixin, unittest.TestCase):

    def test_launcher_invokes_python_helper(self):
        # `index_helper --help` via launcher must dispatch to the .py.
        proc = _run_index_launcher(self.devforge_dir, "--help")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(b"build-index", proc.stdout)


# ---------------------------------------------------------------------------
# Performance smoke test — ensures testForge20-shape inputs complete in
# under 5 seconds. Larger fixtures should also complete quickly because
# the file walker is linear in file count.
# ---------------------------------------------------------------------------


class PerformanceTests(_EnvIsolationMixin, unittest.TestCase):

    def test_runs_under_5_seconds_on_3_packages_x_100_files(self):
        # 3 packages × 100 files each = 300 files total, with manifests.
        for pkg_name in ("a", "b", "c"):
            pkg = self.project_root / pkg_name
            pkg.mkdir()
            (pkg / "package.json").write_text(json.dumps({
                "name": pkg_name,
                "dependencies": {"vue": "^3"},
            }), encoding="utf-8")
            for i in range(100):
                (pkg / "f{0:03d}.ts".format(i)).write_text("//", encoding="utf-8")
        self._seed_init_yaml([
            {"path": "a", "manifest": "package.json"},
            {"path": "b", "manifest": "package.json"},
            {"path": "c", "manifest": "package.json"},
        ])
        t0 = time.perf_counter()
        proc = _run_index(self.devforge_dir, "build-index")
        elapsed = time.perf_counter() - t0
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertLess(elapsed, 5.0, "build-index took {0:.2f}s".format(elapsed))


if __name__ == "__main__":
    unittest.main()
