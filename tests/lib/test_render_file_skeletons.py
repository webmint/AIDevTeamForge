"""Tests for `render-file-skeletons` subcommand (Step B.1 of VALIDATOR-LOOP-B-PLAN.md).

Covers all 10 mandatory test cases from the brief plus edge cases.

Test infrastructure mirrors test_add_annotation.py:
- Subclass _RenderSkeletonsBase (TestCase with isolated TemporaryDirectory).
- devforge_dir = <tmproot>/.devforge/
- project_root = <tmproot>  (passed via DEVFORGE_PROJECT_ROOT env var)
- CLI invocations go through _run_cli (subprocess → real argparse path).
- Round-trip: package + concern registered via real CLI calls.
- index.json written as a JSON file directly (it is a fixture input, not a
  generate_docs_helper output — build-index is not available in this helper).

Stdlib only. Python 3.8+.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "generate_docs_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import generate_docs_helper as gdh  # noqa: E402


# ---------------------------------------------------------------------------
# Shared infrastructure
# ---------------------------------------------------------------------------


def _run_cli(devforge_dir, *args, project_root=None):
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    if project_root is not None:
        env["DEVFORGE_PROJECT_ROOT"] = str(project_root)
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(args),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class _RenderSkeletonsBase(unittest.TestCase):
    """Isolated project root + devforge dir with shared setup helpers."""

    def setUp(self):
        self._saved_devforge = os.environ.pop("DEVFORGE_DIR", None)
        self._saved_root = os.environ.pop("DEVFORGE_PROJECT_ROOT", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self._tmp.name)
        self.devforge_dir = self.project_root / ".devforge"
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.devforge_dir / gdh.STATE_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_devforge is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_devforge
        if self._saved_root is None:
            os.environ.pop("DEVFORGE_PROJECT_ROOT", None)
        else:
            os.environ["DEVFORGE_PROJECT_ROOT"] = self._saved_root

    def _run(self, *args):
        return _run_cli(self.devforge_dir, *args, project_root=self.project_root)

    def _register_package(self, pkg_path="apps/auth-service"):
        r = self._run("add-package", "--path", pkg_path, "--name", "Auth Service")
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        return pkg_path

    def _register_concern(self, pkg_path="apps/auth-service", concern="auth"):
        r = self._run("add-concern", "--package", pkg_path, "--concern", concern)
        self.assertEqual(r.returncode, 0, r.stderr.decode())

    def _write_index(self, pkg_path, files):
        """Write an index.json with the given files list under pkg_path."""
        index = {"packages": {pkg_path: {"files": files}}}
        index_path = self.devforge_dir / "index.json"
        index_path.write_text(json.dumps(index), encoding="utf-8")

    def _run_render(self, pkg_path="apps/auth-service", concern="auth"):
        return self._run(
            "render-file-skeletons",
            "--package", pkg_path,
            "--concern", concern,
        )

    def _docs_dir(self, pkg_path="apps/auth-service", concern="auth"):
        return self.project_root / "docs" / pkg_path / concern


# ---------------------------------------------------------------------------
# Test 1 — Happy path: 5 source files → 5 empty .md files.
# ---------------------------------------------------------------------------


class TestHappyPath(_RenderSkeletonsBase):
    def test_five_files_created(self):
        pkg = self._register_package()
        self._register_concern(pkg)
        self._write_index(pkg, [
            "src/auth/login.ts",
            "src/auth/logout.ts",
            "src/auth/forms/SignUp.tsx",
            "src/auth/forms/Login.vue",
            "src/auth/utils/token.ts",
        ])

        r = self._run_render(pkg)

        self.assertEqual(r.returncode, 0, r.stderr.decode())
        stdout = r.stdout.decode()
        self.assertIn("created=5", stdout)
        self.assertIn("preexisting=0", stdout)

        docs = self._docs_dir(pkg)
        self.assertTrue((docs / "login.ts.md").exists())
        self.assertTrue((docs / "logout.ts.md").exists())
        self.assertTrue((docs / "forms" / "SignUp.tsx.md").exists())
        self.assertTrue((docs / "forms" / "Login.vue.md").exists())
        self.assertTrue((docs / "utils" / "token.ts.md").exists())

        # All created files are empty (zero bytes).
        for md_path in [
            docs / "login.ts.md",
            docs / "logout.ts.md",
            docs / "forms" / "SignUp.tsx.md",
            docs / "forms" / "Login.vue.md",
            docs / "utils" / "token.ts.md",
        ]:
            self.assertEqual(md_path.stat().st_size, 0)


# ---------------------------------------------------------------------------
# Test 2 — Trivial-leaf exclusion.
# ---------------------------------------------------------------------------


class TestTrivialLeafExclusion(_RenderSkeletonsBase):
    def test_trivial_dirs_excluded(self):
        pkg = self._register_package()
        self._register_concern(pkg)
        self._write_index(pkg, [
            "src/auth/login.ts",
            "src/auth/__pycache__/login.cpython-311.pyc",
            "src/auth/node_modules/some-dep/index.js",
        ])

        r = self._run_render(pkg)

        self.assertEqual(r.returncode, 0, r.stderr.decode())
        stdout = r.stdout.decode()
        self.assertIn("created=1", stdout)
        self.assertIn("preexisting=0", stdout)

        docs = self._docs_dir(pkg)
        self.assertTrue((docs / "login.ts.md").exists())
        # Trivial-leaf paths must produce no md files.
        self.assertFalse((docs / "__pycache__" / "login.cpython-311.pyc.md").exists())
        self.assertFalse((docs / "node_modules" / "some-dep" / "index.js.md").exists())


# ---------------------------------------------------------------------------
# Test 3 — Idempotency: second run leaves existing (possibly filled) mds untouched.
# ---------------------------------------------------------------------------


class TestIdempotency(_RenderSkeletonsBase):
    def test_second_run_leaves_filled_md_untouched(self):
        pkg = self._register_package()
        self._register_concern(pkg)
        self._write_index(pkg, [
            "src/auth/login.ts",
            "src/auth/logout.ts",
        ])

        # First run: create 2 skeletons.
        r1 = self._run_render(pkg)
        self.assertEqual(r1.returncode, 0, r1.stderr.decode())
        self.assertIn("created=2", r1.stdout.decode())

        # Simulate a partial fill: write content into one of the mds.
        docs = self._docs_dir(pkg)
        filled_path = docs / "login.ts.md"
        filled_path.write_text("filled content", encoding="utf-8")

        # Second run: existing files are counted as preexisting, not recreated.
        r2 = self._run_render(pkg)
        self.assertEqual(r2.returncode, 0, r2.stderr.decode())
        stdout2 = r2.stdout.decode()
        self.assertIn("created=0", stdout2)
        self.assertIn("preexisting=2", stdout2)

        # Filled content must be preserved exactly.
        self.assertEqual(filled_path.read_text(encoding="utf-8"), "filled content")
        # The other md still exists.
        self.assertTrue((docs / "logout.ts.md").exists())


# ---------------------------------------------------------------------------
# Test 4 — Package not in index.json → exit 2.
# ---------------------------------------------------------------------------


class TestPackageNotInIndex(_RenderSkeletonsBase):
    def test_package_absent_from_index(self):
        pkg = self._register_package()
        self._register_concern(pkg)
        # Write index.json with a DIFFERENT package key.
        index = {"packages": {"apps/other-service": {"files": ["src/other/foo.ts"]}}}
        (self.devforge_dir / "index.json").write_text(
            json.dumps(index), encoding="utf-8"
        )

        r = self._run_render(pkg)

        self.assertEqual(r.returncode, 2)
        self.assertIn("index.json missing or package", r.stderr.decode())


# ---------------------------------------------------------------------------
# Test 5 — index.json missing entirely → exit 2.
# ---------------------------------------------------------------------------


class TestIndexMissing(_RenderSkeletonsBase):
    def test_no_index_file(self):
        pkg = self._register_package()
        self._register_concern(pkg)
        # Deliberately do not write index.json.

        r = self._run_render(pkg)

        self.assertEqual(r.returncode, 2)
        self.assertIn("index.json missing or package", r.stderr.decode())


# ---------------------------------------------------------------------------
# Test 6 — Empty subfolder: all files outside src/<concern>/ → soft warn, exit 0.
# ---------------------------------------------------------------------------


class TestEmptySubfolder(_RenderSkeletonsBase):
    def test_files_outside_concern_subfolder(self):
        pkg = self._register_package()
        self._register_concern(pkg, concern="auth")
        # All files are under src/billing/, NOT src/auth/.
        self._write_index(pkg, [
            "src/billing/invoice.ts",
            "src/billing/payment.ts",
        ])

        r = self._run_render(pkg, concern="auth")

        self.assertEqual(r.returncode, 0)
        stdout = r.stdout.decode()
        self.assertIn("created=0", stdout)
        self.assertIn("preexisting=0", stdout)
        # Soft warning on stderr.
        self.assertIn("no source files under", r.stderr.decode())


# ---------------------------------------------------------------------------
# Test 7 — Package not registered → exit 2.
# ---------------------------------------------------------------------------


class TestPackageNotRegistered(_RenderSkeletonsBase):
    def test_unregistered_package(self):
        # Do NOT call add-package.
        self._write_index("apps/auth-service", ["src/auth/login.ts"])

        r = self._run_render("apps/auth-service", "auth")

        self.assertEqual(r.returncode, 2)
        self.assertIn("package not registered", r.stderr.decode())


# ---------------------------------------------------------------------------
# Test 8 — Concern not registered → exit 2.
# ---------------------------------------------------------------------------


class TestConcernNotRegistered(_RenderSkeletonsBase):
    def test_unregistered_concern(self):
        pkg = self._register_package()
        # Do NOT call add-concern.
        self._write_index(pkg, ["src/auth/login.ts"])

        r = self._run_render(pkg, "auth")

        self.assertEqual(r.returncode, 2)
        self.assertIn("concern", r.stderr.decode())
        self.assertIn("not registered", r.stderr.decode())


# ---------------------------------------------------------------------------
# Test 9 — Nested subdirectories: parent dirs auto-created.
# ---------------------------------------------------------------------------


class TestNestedSubdirectories(_RenderSkeletonsBase):
    def test_deep_nested_path(self):
        pkg = self._register_package()
        self._register_concern(pkg)
        self._write_index(pkg, [
            "src/auth/forms/login/Login.vue",
        ])

        r = self._run_render(pkg)

        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertIn("created=1", r.stdout.decode())

        expected_md = (
            self.project_root
            / "docs" / pkg / "auth"
            / "forms" / "login" / "Login.vue.md"
        )
        self.assertTrue(expected_md.exists())
        self.assertEqual(expected_md.stat().st_size, 0)


# ---------------------------------------------------------------------------
# Test 10 — Vue file extension preserved: Login.vue → Login.vue.md (not Login.md).
# ---------------------------------------------------------------------------


class TestVueExtensionPreserved(_RenderSkeletonsBase):
    def test_vue_extension_in_md_name(self):
        pkg = self._register_package()
        self._register_concern(pkg)
        self._write_index(pkg, [
            "src/auth/Login.vue",
        ])

        r = self._run_render(pkg)

        self.assertEqual(r.returncode, 0, r.stderr.decode())
        docs = self._docs_dir(pkg)
        # Must be Login.vue.md, NOT Login.md.
        self.assertTrue((docs / "Login.vue.md").exists())
        self.assertFalse((docs / "Login.md").exists())


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


class TestFilesOutsideConcernAreIgnored(_RenderSkeletonsBase):
    """Files in index that are NOT under src/<concern>/ do not produce mds."""

    def test_mixed_concerns_only_target_concern_processed(self):
        pkg = self._register_package()
        self._register_concern(pkg, concern="auth")
        self._write_index(pkg, [
            "src/auth/login.ts",       # matches auth
            "src/billing/invoice.ts",  # different concern, must not produce md
            "README.md",               # top-level, no prefix match
        ])

        r = self._run_render(pkg, concern="auth")

        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertIn("created=1", r.stdout.decode())
        docs = self._docs_dir(pkg, concern="auth")
        self.assertTrue((docs / "login.ts.md").exists())
        billing_md = self.project_root / "docs" / pkg / "billing"
        self.assertFalse(billing_md.exists())


class TestStdoutFormat(_RenderSkeletonsBase):
    """Stdout line must match the exact documented format."""

    def test_stdout_contains_pkg_and_concern(self):
        pkg = "apps/auth-service"
        concern = "auth"
        self._register_package(pkg)
        self._register_concern(pkg, concern)
        self._write_index(pkg, ["src/auth/login.ts"])

        r = self._run_render(pkg, concern)

        self.assertEqual(r.returncode, 0)
        stdout = r.stdout.decode().strip()
        self.assertTrue(
            stdout.startswith("render-file-skeletons {0}/{1}:".format(pkg, concern)),
            "stdout={!r}".format(stdout),
        )


class TestSmokeEmptyState(_RenderSkeletonsBase):
    """Smoke: completely empty state (no add-package) returns exit 2, not a crash."""

    def test_no_state_file_returns_exit_2_not_crash(self):
        # No state file exists at all — _load_state returns default empty state.
        r = self._run(
            "render-file-skeletons",
            "--package", "apps/nonexistent",
            "--concern", "auth",
        )
        self.assertEqual(r.returncode, 2)
        # Should have a human-readable error, not a Python traceback.
        stderr = r.stderr.decode()
        self.assertNotIn("Traceback", stderr)
        self.assertIn("package not registered", stderr)


if __name__ == "__main__":
    unittest.main()
