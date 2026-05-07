"""Tests for the `file-docs-incomplete` validate-concern rule (Step B.2 of
VALIDATOR-LOOP-B-PLAN.md).

9 test methods covering 7 plan cases (cases 3 and 7 split into sub-tests):
1. All expected mds present + non-empty → rule passes.
2. One md missing → rule fails, error names path.
3a. Skeleton at zero bytes → rule fails (EMPTY classification).
3b. Skeleton at exactly threshold (50 bytes) → rule fails.
4. Concern with empty subfolder → rule passes vacuously.
5. Legacy concern without skeletons run → rule fails with "no skeletons
   rendered" guidance.
6. Missing index.json → rule graceful-degrades; validate-concern still
   proceeds (may fail on other rules but NOT on file-docs-incomplete).
7a. Threshold boundary: size exactly 50 bytes → fails.
7b. Threshold boundary: size 51 bytes → passes.

Test infrastructure mirrors test_render_file_skeletons.py:
- Isolated TemporaryDirectory per test class.
- devforge_dir = <tmproot>/.devforge/
- project_root = <tmproot>  (DEVFORGE_PROJECT_ROOT env var)
- All CLI calls via subprocess (real argparse + dispatch path).
- index.json written as a JSON fixture directly (build-index not available).

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


def setUpModule():
    # Part D revert (2026-05-07): _check_file_docs_complete rule is unwired
    # from validate_concern's active rule chain. Per-file md primitive proved
    # cost-prohibitive on testForge20 empirical run; reverted to concern-level
    # fill (single tree-annotator dispatch composes inline tree descriptions
    # for per-file recall). The rule function stays defined for future revival
    # via codegraph-augmented batch dispatch (Part C planning, parked).
    # These integration tests assert the rule fires through validate-concern
    # — they cannot pass while the rule is dormant. Skipped wholesale; revive
    # by deleting this setUpModule when the rule is rewired.
    raise unittest.SkipTest(
        "Part D revert: _check_file_docs_complete dormant; "
        "revive when codegraph batch dispatch lands"
    )


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


class _FileDocsBase(unittest.TestCase):
    """Isolated project root + devforge dir with shared setup helpers.

    Default package: apps/web  concern: auth  source: src/auth/login.ts
    """

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

    def _write_source(self, rel_path, lines):
        full = self.project_root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return full

    def _write_index(self, pkg_path, files):
        index = {"packages": {pkg_path: {"files": files}}}
        (self.devforge_dir / "index.json").write_text(
            json.dumps(index), encoding="utf-8"
        )

    def _register_package(self, pkg="apps/web", name="web"):
        r = self._run("add-package", "--path", pkg, "--name", name)
        self.assertEqual(r.returncode, 0, r.stderr.decode())

    def _register_concern(self, pkg="apps/web", concern="auth"):
        r = self._run("add-concern", "--package", pkg, "--concern", concern)
        self.assertEqual(r.returncode, 0, r.stderr.decode())

    def _register_pkg_concern(self, pkg="apps/web", name="web", concern="auth"):
        self._register_package(pkg, name)
        self._register_concern(pkg, concern)

    def _set_required_fields(self, pkg="apps/web", concern="auth"):
        """Populate the concern's required fields (overview + tree + export)
        so validate-concern can potentially pass on all rules except B.2."""
        self._write_source("src/auth/login.ts", [
            "export function login(id) {",
            "  return id;",
            "}",
        ])
        self._run("set-concern-overview",
                  "--package", pkg, "--concern", concern,
                  "--text", "Auth module.")
        self._run("set-concern-tree",
                  "--package", pkg, "--concern", concern,
                  "--text", "auth/\n  login.ts")
        self._run("add-concern-export",
                  "--package", pkg, "--concern", concern,
                  "--name", "login", "--kind", "function",
                  "--signature", "", "--description", "Logs in.",
                  "--language", "ts",
                  "--code-snippet",
                  "export function login(id) {\n  return id;\n}",
                  "--cite-file", "src/auth/login.ts",
                  "--cite-start", "1", "--cite-end", "3")

    def _render_skeletons(self, pkg="apps/web", concern="auth"):
        r = self._run("render-file-skeletons",
                      "--package", pkg, "--concern", concern)
        self.assertEqual(r.returncode, 0, r.stderr.decode())

    def _fill_skeletons(self, pkg="apps/web", concern="auth", size=100):
        """Fill all zero-byte skeletons under docs/<pkg>/<concern>/ with
        `size` bytes so they exceed FILE_DOC_MIN_SIZE_BYTES (50)."""
        docs_dir = self.project_root / "docs" / pkg / concern
        if docs_dir.exists():
            for md_path in docs_dir.rglob("*.md"):
                if md_path.stat().st_size == 0:
                    md_path.write_text("x" * size, encoding="utf-8")

    def _validate_concern(self, pkg="apps/web", concern="auth"):
        return self._run("validate-concern",
                         "--package", pkg, "--concern", concern)


# ---------------------------------------------------------------------------
# Test 1 — All expected mds present + non-empty → rule passes.
# ---------------------------------------------------------------------------


class TestAllFilledPasses(_FileDocsBase):
    def test_all_mds_present_and_non_empty(self):
        self._register_pkg_concern()
        self._set_required_fields()
        self._write_index("apps/web", ["src/auth/login.ts"])

        self._render_skeletons()
        self._fill_skeletons()

        proc = self._validate_concern()

        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertNotIn(b"file-docs-incomplete", proc.stderr)


# ---------------------------------------------------------------------------
# Test 2 — One md missing → rule fails, error names path.
# ---------------------------------------------------------------------------


class TestOneMissingFails(_FileDocsBase):
    def test_one_md_deleted_after_render(self):
        self._register_pkg_concern()
        self._set_required_fields()
        # Three source files: 3 skeletons created.
        self._write_index("apps/web", [
            "src/auth/login.ts",
            "src/auth/logout.ts",
            "src/auth/session.ts",
        ])
        # Also write the other source files so codeblock checks don't
        # confuse the offender path assertion.
        self._write_source("src/auth/logout.ts", ["export function logout() {}"])
        self._write_source("src/auth/session.ts", ["export function session() {}"])

        self._render_skeletons()
        self._fill_skeletons()

        # Delete one of the rendered mds.
        missing_md = (
            self.project_root / "docs" / "apps/web" / "auth" / "logout.ts.md"
        )
        missing_md.unlink()

        proc = self._validate_concern()

        self.assertEqual(proc.returncode, 2)
        stderr = proc.stderr.decode()
        self.assertIn("file-docs-incomplete", stderr)
        # Error message must name the missing path (relative to project root).
        self.assertIn("logout.ts.md", stderr)
        self.assertIn("MISSING", stderr)


# ---------------------------------------------------------------------------
# Test 3 — One md empty (size at/below threshold) → rule fails.
# ---------------------------------------------------------------------------


class TestEmptyMdFails(_FileDocsBase):
    def test_skeleton_left_at_zero_bytes_fails(self):
        """render-file-skeletons ran but fill loop skipped — md at 0 bytes."""
        self._register_pkg_concern()
        self._set_required_fields()
        self._write_index("apps/web", ["src/auth/login.ts"])

        self._render_skeletons()
        # Explicitly do NOT fill skeletons — leave them at 0 bytes.

        proc = self._validate_concern()

        self.assertEqual(proc.returncode, 2)
        stderr = proc.stderr.decode()
        self.assertIn("file-docs-incomplete", stderr)
        self.assertIn("EMPTY", stderr)
        self.assertIn("login.ts.md", stderr)

    def test_skeleton_at_exactly_threshold_fails(self):
        """File at exactly 50 bytes must fail (threshold is strictly >50)."""
        self._register_pkg_concern()
        self._set_required_fields()
        self._write_index("apps/web", ["src/auth/login.ts"])

        self._render_skeletons()

        # Write exactly FILE_DOC_MIN_SIZE_BYTES bytes.
        md = (
            self.project_root / "docs" / "apps/web" / "auth" / "login.ts.md"
        )
        from _generate_docs._validators_concern import FILE_DOC_MIN_SIZE_BYTES
        md.write_bytes(b"x" * FILE_DOC_MIN_SIZE_BYTES)

        proc = self._validate_concern()

        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"file-docs-incomplete", proc.stderr)


# ---------------------------------------------------------------------------
# Test 4 — Concern with empty subfolder → rule passes vacuously.
# ---------------------------------------------------------------------------


class TestEmptySubfolderVacuousPass(_FileDocsBase):
    def test_no_source_files_in_concern_subfolder(self):
        """index.json exists but all files are under a DIFFERENT concern's
        subfolder — expected_paths is empty → rule passes vacuously."""
        self._register_pkg_concern()
        self._set_required_fields()
        # All files are under src/billing/, not src/auth/.
        self._write_index("apps/web", [
            "src/billing/invoice.ts",
            "src/billing/payment.ts",
        ])

        proc = self._validate_concern()

        # Rule passes vacuously; other required-field rules may or may not
        # fire depending on state — but file-docs-incomplete must not fire.
        self.assertNotIn(b"file-docs-incomplete", proc.stderr)


# ---------------------------------------------------------------------------
# Test 5 — Legacy concern without skeletons → rule fails with guidance.
# ---------------------------------------------------------------------------


class TestNoSkeletonsGuidance(_FileDocsBase):
    def test_source_in_index_but_skeletons_never_run(self):
        """Source file registered in index.json but render-file-skeletons was
        never run — docs/<P>/<C>/ doesn't exist at all. Rule must fail and
        include 'no skeletons rendered' guidance."""
        self._register_pkg_concern()
        self._set_required_fields()
        self._write_index("apps/web", ["src/auth/login.ts"])
        # Deliberately do NOT run render-file-skeletons.

        proc = self._validate_concern()

        self.assertEqual(proc.returncode, 2)
        stderr = proc.stderr.decode()
        self.assertIn("file-docs-incomplete", stderr)
        self.assertIn("no skeletons rendered", stderr)


# ---------------------------------------------------------------------------
# Test 6 — Missing index.json → graceful degrade.
# ---------------------------------------------------------------------------


class TestMissingIndexGracefulDegrade(_FileDocsBase):
    def test_no_index_file_skips_rule(self):
        """When index.json is absent, _check_file_docs_complete returns []
        and writes a warning to stderr. validate-concern may fail on other
        rules (required fields), but NOT on a file-docs-incomplete ERROR.

        The rule name appears in the skip-warning but NOT as an error rule
        prefix — we check that the bracket-prefixed error form
        `[file-docs-incomplete]` is absent."""
        self._register_pkg_concern()
        # No index.json written.

        proc = self._validate_concern()

        # The bracket-prefixed error rule must NOT appear (that's the error form).
        self.assertNotIn(b"[file-docs-incomplete]", proc.stderr)
        # The skip-warning must appear on stderr so the operator knows.
        self.assertIn(b"file-docs-incomplete check skipped", proc.stderr)


# ---------------------------------------------------------------------------
# Test 7 — Threshold boundary: exactly 50 fails, 51 passes.
# ---------------------------------------------------------------------------


class TestThresholdBoundary(_FileDocsBase):
    """FILE_DOC_MIN_SIZE_BYTES = 50. Size must be STRICTLY > 50 to pass."""

    def _setup_with_md_size(self, size):
        """Register full concern state, seed index.json + skeleton, write
        the md with exactly `size` bytes. Return the validate-concern result."""
        self._register_pkg_concern()
        self._set_required_fields()
        self._write_index("apps/web", ["src/auth/login.ts"])
        self._render_skeletons()
        md = (
            self.project_root / "docs" / "apps/web" / "auth" / "login.ts.md"
        )
        md.write_bytes(b"x" * size)
        return self._validate_concern()

    def test_size_exactly_50_fails(self):
        from _generate_docs._validators_concern import FILE_DOC_MIN_SIZE_BYTES
        self.assertEqual(FILE_DOC_MIN_SIZE_BYTES, 50)
        proc = self._setup_with_md_size(50)
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"file-docs-incomplete", proc.stderr)

    def test_size_51_passes(self):
        proc = self._setup_with_md_size(51)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertNotIn(b"file-docs-incomplete", proc.stderr)


if __name__ == "__main__":
    unittest.main()
