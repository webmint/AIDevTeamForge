"""Tests for `write-file-doc` subcommand (Step B.3 of VALIDATOR-LOOP-B-PLAN.md).

13 test cases:
  1.  Happy path: writes .md file with expected front-matter + body header.
  2.  Overwrites a pre-existing skeleton (zero-byte) with full content.
  3.  Overwrites a pre-existing FILLED .md (fill is idempotent at higher level).
  4.  Relative md-path resolves against _project_root() (DEVFORGE_DIR.parent).
  5.  Validation: invalid confidence enum -> exit 2.
  6.  Round-trip: write-file-doc then parse_frontmatter returns equivalent record
      with hash matching manually-computed sha256 of cite range.
  7.  cite-start zero -> exit 2.
  8.  cite-end < cite-start -> exit 2.
  9.  Body header uses source filename (strips .md suffix from md-path).
 10.  cite-file missing -> exit 2.
 11.  cite-end exceeds file line count -> exit 2.

Stdlib only. Python 3.8+.
"""

import hashlib
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
if str(_LIB_DIR / "_generate_docs") not in sys.path:
    sys.path.insert(0, str(_LIB_DIR / "_generate_docs"))

from _generate_docs._md_frontmatter import parse_frontmatter  # noqa: E402


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


class _WriteFileDocBase(unittest.TestCase):
    """Isolated tmp dir per test."""

    def setUp(self):
        self._saved_devforge = os.environ.pop("DEVFORGE_DIR", None)
        self._saved_root = os.environ.pop("DEVFORGE_PROJECT_ROOT", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self._tmp.name)
        self.devforge_dir = self.project_root / ".devforge"
        self.devforge_dir.mkdir(parents=True, exist_ok=True)

        # Write source files that tests use as cite targets.
        # src/auth/index.ts: 5 predictable lines.
        src_auth = self.project_root / "src" / "auth"
        src_auth.mkdir(parents=True, exist_ok=True)
        self._src_index_ts = src_auth / "index.ts"
        self._src_index_ts.write_text(
            "line 1\nline 2\nline 3\nline 4\nline 5\n",
            encoding="utf-8",
        )
        # src/auth/Login.vue: 5 predictable lines.
        self._src_login_vue = src_auth / "Login.vue"
        self._src_login_vue.write_text(
            "vue 1\nvue 2\nvue 3\nvue 4\nvue 5\n",
            encoding="utf-8",
        )

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

    def _write_file_doc(
        self,
        md_path,
        label="Authentication entry point",
        confidence="extracted",
        cite_file="src/auth/index.ts",
        cite_start=1,
        cite_end=3,
        model_version="haiku",
    ):
        return self._run(
            "write-file-doc",
            "--md-path", str(md_path),
            "--label", label,
            "--confidence", confidence,
            "--cite-file", cite_file,
            "--cite-start", str(cite_start),
            "--cite-end", str(cite_end),
            "--model-version", model_version,
        )


# ---------------------------------------------------------------------------
# Test 1: Happy path.
# ---------------------------------------------------------------------------


class TestHappyPath(_WriteFileDocBase):

    def test_writes_md_with_expected_content(self):
        md_path = self.project_root / "docs" / "apps" / "web" / "auth" / "Login.vue.md"
        r = self._write_file_doc(md_path)

        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertTrue(md_path.exists())

        content = md_path.read_text(encoding="utf-8")
        self.assertIn("---", content)
        self.assertIn("Authentication entry point", content)
        self.assertIn("extracted", content)
        self.assertIn("src/auth/index.ts", content)
        # content_hash is now computed by the helper — check it's a 64-hex string.
        import re
        self.assertRegex(content, r"content_hash: \"[0-9a-f]{64}\"")
        self.assertIn("haiku", content)

    def test_stdout_reports_path_and_bytes(self):
        md_path = self.project_root / "docs" / "apps" / "web" / "auth" / "Login.vue.md"
        r = self._write_file_doc(md_path)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        stdout = r.stdout.decode()
        self.assertIn("write-file-doc", stdout)
        self.assertIn("bytes", stdout)


# ---------------------------------------------------------------------------
# Test 2: Overwrites a pre-existing zero-byte skeleton.
# ---------------------------------------------------------------------------


class TestOverwritesSkeleton(_WriteFileDocBase):

    def test_zero_byte_skeleton_replaced(self):
        md_path = self.project_root / "docs" / "auth" / "login.ts.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        # Write a zero-byte skeleton (as render-file-skeletons would).
        md_path.write_bytes(b"")
        self.assertEqual(md_path.stat().st_size, 0)

        r = self._write_file_doc(md_path)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertGreater(md_path.stat().st_size, 0)

        content = md_path.read_text(encoding="utf-8")
        self.assertIn("Authentication entry point", content)


# ---------------------------------------------------------------------------
# Test 3: Overwrites a pre-existing FILLED .md.
# ---------------------------------------------------------------------------


class TestOverwritesFilled(_WriteFileDocBase):

    def test_filled_md_replaced(self):
        md_path = self.project_root / "docs" / "auth" / "login.ts.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text("old content here", encoding="utf-8")

        r = self._write_file_doc(md_path, label="Replacement label here")
        self.assertEqual(r.returncode, 0, r.stderr.decode())

        content = md_path.read_text(encoding="utf-8")
        self.assertNotIn("old content here", content)
        self.assertIn("Replacement label here", content)


# ---------------------------------------------------------------------------
# Test 4: Relative md-path resolves against project_root.
# ---------------------------------------------------------------------------


class TestRelativePathResolution(_WriteFileDocBase):

    def test_relative_path_resolves_to_project_root(self):
        # Relative path (no leading /).
        rel_path = "docs/auth/login.ts.md"
        r = self._write_file_doc(rel_path)
        self.assertEqual(r.returncode, 0, r.stderr.decode())

        # The file should be written under project_root.
        expected = self.project_root / rel_path
        self.assertTrue(expected.exists(), "Expected file at {0}".format(expected))
        content = expected.read_text(encoding="utf-8")
        self.assertIn("Authentication entry point", content)


# ---------------------------------------------------------------------------
# Test 5: Invalid confidence enum -> exit 2.
# ---------------------------------------------------------------------------


class TestInvalidConfidenceEnum(_WriteFileDocBase):

    def test_bad_confidence_exits_2(self):
        md_path = self.project_root / "docs" / "auth" / "login.ts.md"
        r = self._write_file_doc(md_path, confidence="INVALID_CONFIDENCE")
        self.assertEqual(r.returncode, 2, r.stderr.decode())
        # File should NOT have been created.
        self.assertFalse(md_path.exists())


# ---------------------------------------------------------------------------
# Test 6: Round-trip — write then parse returns equivalent record.
# The content_hash in the record must equal sha256 of the cite slice.
# ---------------------------------------------------------------------------


class TestRoundTrip(_WriteFileDocBase):

    def test_parse_frontmatter_after_write(self):
        md_path = self.project_root / "docs" / "auth" / "Login.vue.md"
        label = "Authentication form component"
        # cite_end=5 reads all 5 lines of Login.vue.
        r = self._write_file_doc(
            md_path,
            label=label,
            confidence="inferred",
            cite_file="src/auth/Login.vue",
            cite_start=1,
            cite_end=5,
            model_version="sonnet",
        )
        self.assertEqual(r.returncode, 0, r.stderr.decode())

        content = md_path.read_text(encoding="utf-8")
        record, _ = parse_frontmatter(content)

        self.assertEqual(record["label"], label)
        self.assertEqual(record["confidence"], "inferred")
        self.assertEqual(record["evidence_file"], "src/auth/Login.vue")
        self.assertEqual(record["evidence_start"], 1)
        self.assertEqual(record["evidence_end"], 5)
        self.assertEqual(record["model_version"], "sonnet")

        # Verify the helper computed the correct hash for the cite slice.
        # This proves helper-computed hash matches the expected algorithm:
        # sha256("\n".join(splitlines()[start-1:end])).
        vue_text = self._src_login_vue.read_text(encoding="utf-8", errors="replace")
        slice_lines = vue_text.splitlines()[0:5]
        expected_hash = hashlib.sha256("\n".join(slice_lines).encode("utf-8")).hexdigest()
        self.assertEqual(record["content_hash"], expected_hash)


# ---------------------------------------------------------------------------
# Test 7: cite-start zero -> exit 2.
# ---------------------------------------------------------------------------


class TestCiteStartZero(_WriteFileDocBase):

    def test_cite_start_zero_exits_2(self):
        md_path = self.project_root / "docs" / "auth" / "login.ts.md"
        r = self._write_file_doc(md_path, cite_start=0, cite_end=3)
        self.assertEqual(r.returncode, 2, r.stderr.decode())
        self.assertFalse(md_path.exists())


# ---------------------------------------------------------------------------
# Test 8: cite-end < cite-start -> exit 2.
# ---------------------------------------------------------------------------


class TestCiteEndBeforeStart(_WriteFileDocBase):

    def test_end_before_start_exits_2(self):
        md_path = self.project_root / "docs" / "auth" / "login.ts.md"
        r = self._write_file_doc(md_path, cite_start=10, cite_end=5)
        self.assertEqual(r.returncode, 2, r.stderr.decode())
        self.assertFalse(md_path.exists())


# ---------------------------------------------------------------------------
# Test 9: Body header uses source filename (strips .md from md-path name).
# ---------------------------------------------------------------------------


class TestBodyHeaderFilename(_WriteFileDocBase):

    def test_body_header_strips_md_suffix(self):
        md_path = self.project_root / "docs" / "auth" / "Login.vue.md"
        r = self._write_file_doc(md_path)
        self.assertEqual(r.returncode, 0, r.stderr.decode())

        content = md_path.read_text(encoding="utf-8")
        # Body header should be "# Login.vue" (not "# Login.vue.md").
        self.assertIn("# Login.vue", content)
        self.assertNotIn("# Login.vue.md", content)

    def test_body_header_for_ts_file(self):
        md_path = self.project_root / "docs" / "auth" / "index.ts.md"
        r = self._write_file_doc(md_path)
        self.assertEqual(r.returncode, 0, r.stderr.decode())

        content = md_path.read_text(encoding="utf-8")
        self.assertIn("# index.ts", content)
        self.assertNotIn("# index.ts.md", content)


# ---------------------------------------------------------------------------
# Test 10: cite-file missing -> exit 2.
# ---------------------------------------------------------------------------


class TestCiteFileMissing(_WriteFileDocBase):

    def test_missing_cite_file_exits_2(self):
        md_path = self.project_root / "docs" / "auth" / "login.ts.md"
        r = self._write_file_doc(
            md_path,
            cite_file="src/auth/does_not_exist.ts",
        )
        self.assertEqual(r.returncode, 2, r.stderr.decode())
        self.assertIn("cite-file not found", r.stderr.decode())
        # .md must not be written when cite resolution fails.
        self.assertFalse(md_path.exists())


# ---------------------------------------------------------------------------
# Test 11: cite-end exceeds file line count -> exit 2.
# ---------------------------------------------------------------------------


class TestCiteRangeOutOfBounds(_WriteFileDocBase):

    def test_cite_end_exceeds_line_count_exits_2(self):
        # src/auth/index.ts has 5 lines; requesting end=99 exceeds it.
        md_path = self.project_root / "docs" / "auth" / "login.ts.md"
        r = self._write_file_doc(
            md_path,
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=99,
        )
        self.assertEqual(r.returncode, 2, r.stderr.decode())
        self.assertIn("exceeds file line count", r.stderr.decode())
        self.assertFalse(md_path.exists())


if __name__ == "__main__":
    unittest.main()
