"""Tests for `validate-file-doc` subcommand (Step B.3 of VALIDATOR-LOOP-B-PLAN.md).

13 test cases covering all 6 exit codes:
  1.  Happy path: all checks pass -> exit 0.
  2.  File missing -> exit 5 ("file not found").
  3.  Front-matter parse error (no leading ---) -> exit 5.
  4.  Schema invalid (bad confidence enum) -> exit 5.
  5.  Banned phrase in label -> exit 2.
  6.  Binary cite-file (NUL byte) -> exit 6.
  7.  Cite range out-of-bounds -> exit 3.
  8.  Hash drift (content_hash doesn't match recomputed) -> exit 3.
  9.  Sibling collision (two mds in same dir, same label) -> exit 4.
 10.  Sibling parse error doesn't propagate -> still exit 0 if current is valid.
 11.  Case-insensitive sibling collision -> exit 4.
 12.  Missing cite-file -> exit 3.
 13.  Order: banned phrase before cite check (banned wins at exit 2).

Infrastructure: round-trip via real `write-file-doc` helper to produce .md files.
For tests that require malformed front-matter or unreachable error conditions
(binary file, missing cite, invalid schema), .md files are written directly via
Path.write_text -- the helper would reject these inputs before writing. This is
documented inline where used.

Source files written directly (plain text) for cite-resolution checks.

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

# A valid sha256 hex (64 lowercase hex chars) for use in directly-written .md files.
_VALID_HASH = "a" * 64


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


def _compute_hash(path, start, end):
    """Compute sha256 of inclusive 1-based line slice [start, end].

    Matches _recompute_content_hash algorithm exactly: splitlines() + join '\n'.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    file_lines = text.splitlines()
    slice_lines = file_lines[start - 1:end]
    joined = "\n".join(slice_lines)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


class _ValidateFileDocBase(unittest.TestCase):
    """Isolated project root + devforge dir with shared setup helpers."""

    def setUp(self):
        self._saved_devforge = os.environ.pop("DEVFORGE_DIR", None)
        self._saved_root = os.environ.pop("DEVFORGE_PROJECT_ROOT", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self._tmp.name)
        self.devforge_dir = self.project_root / ".devforge"
        self.devforge_dir.mkdir(parents=True, exist_ok=True)

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
        """Write a source file with given lines and return its absolute path."""
        full = self.project_root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return full

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
        """Call write-file-doc CLI. cite-file must exist with enough lines."""
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

    def _validate_file_doc(self, md_path):
        return self._run("validate-file-doc", "--md-path", str(md_path))

    def _setup_happy_md(
        self,
        source_lines=None,
        label="Authentication entry point",
        evidence_rel="src/auth/index.ts",
        md_path=None,
    ):
        """Write a source file and a filled .md for it; return (md_path, source_path).

        write-file-doc computes content_hash from the cite range; the resulting
        .md is hash-consistent and validate-file-doc will exit 0.
        """
        if source_lines is None:
            source_lines = [
                "export default function auth() {",
                "  return true;",
                "}",
            ]
        source_path = self._write_source(evidence_rel, source_lines)

        if md_path is None:
            md_path = self.project_root / "docs" / "apps" / "web" / "auth" / "index.ts.md"

        r = self._write_file_doc(
            md_path,
            label=label,
            cite_file=evidence_rel,
            cite_start=1,
            cite_end=len(source_lines),
        )
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        return md_path, source_path


# ---------------------------------------------------------------------------
# Test 1: Happy path -- all checks pass -> exit 0.
# ---------------------------------------------------------------------------


class TestHappyPath(_ValidateFileDocBase):

    def test_all_checks_pass_exit_0(self):
        md_path, _ = self._setup_happy_md()
        r = self._validate_file_doc(md_path)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        self.assertIn(b"ok", r.stdout)


# ---------------------------------------------------------------------------
# Test 2: File missing -> exit 5.
# ---------------------------------------------------------------------------


class TestFileMissing(_ValidateFileDocBase):

    def test_missing_md_exits_5(self):
        md_path = self.project_root / "docs" / "nonexistent.ts.md"
        r = self._validate_file_doc(md_path)
        self.assertEqual(r.returncode, 5, r.stderr.decode())
        self.assertIn(b"not found", r.stderr)


# ---------------------------------------------------------------------------
# Test 3: Front-matter parse error -> exit 5.
# ---------------------------------------------------------------------------


class TestFrontmatterParseError(_ValidateFileDocBase):

    def test_no_leading_fence_exits_5(self):
        md_path = self.project_root / "docs" / "auth" / "index.ts.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        # Write a .md without the leading `---` fence.
        md_path.write_text("label: foo\nconfidence: extracted\n", encoding="utf-8")
        r = self._validate_file_doc(md_path)
        self.assertEqual(r.returncode, 5, r.stderr.decode())
        self.assertIn(b"parse error", r.stderr)


# ---------------------------------------------------------------------------
# Test 4: Schema invalid (bad confidence) -> exit 5.
# The helper rejects bad confidence at write time, so the .md is written
# directly here to get an invalid schema on disk for the validator to reject.
# ---------------------------------------------------------------------------


class TestSchemaInvalid(_ValidateFileDocBase):

    def test_bad_confidence_in_frontmatter_exits_5(self):
        md_path = self.project_root / "docs" / "auth" / "index.ts.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        # Write a .md with invalid confidence value directly -- write-file-doc
        # would reject "BOGUS" at the CLI boundary before writing.
        content = (
            "---\n"
            'label: "Authentication entry point"\n'
            "confidence: BOGUS\n"
            'evidence_file: "src/auth/index.ts"\n'
            "evidence_start: 1\n"
            "evidence_end: 3\n"
            'content_hash: "{0}"\n'
            'model_version: "haiku"\n'
            "---\n\n# index.ts\n"
        ).format(_VALID_HASH)
        md_path.write_text(content, encoding="utf-8")
        r = self._validate_file_doc(md_path)
        self.assertEqual(r.returncode, 5, r.stderr.decode())
        self.assertIn(b"confidence", r.stderr)


# ---------------------------------------------------------------------------
# Test 5: Banned phrase in label -> exit 2.
# ---------------------------------------------------------------------------


class TestBannedPhrase(_ValidateFileDocBase):

    def test_banned_phrase_in_label_exits_2(self):
        source_lines = ["line1", "line2", "line3"]
        self._write_source("src/auth/index.ts", source_lines)

        md_path = self.project_root / "docs" / "auth" / "index.ts.md"
        r = self._write_file_doc(
            md_path,
            label="handles authentication flow",
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=3,
        )
        self.assertEqual(r.returncode, 0, r.stderr.decode())

        r = self._validate_file_doc(md_path)
        self.assertEqual(r.returncode, 2, r.stderr.decode())
        self.assertIn(b"handles", r.stderr)


# ---------------------------------------------------------------------------
# Test 6: Binary cite-file -> exit 6.
# write-file-doc would fail computing hash from a binary file (OSError or
# decode errors surfacing as bad content), so the .md is written directly
# here with a placeholder hash. validate-file-doc opens the binary cite-file
# and detects NUL bytes -> exit 6.
# ---------------------------------------------------------------------------


class TestBinaryCiteFile(_ValidateFileDocBase):

    def test_binary_cite_file_exits_6(self):
        source_path = self.project_root / "src" / "auth" / "index.ts"
        source_path.parent.mkdir(parents=True, exist_ok=True)
        # Write a binary file (NUL byte).
        source_path.write_bytes(b"export default " + b"\x00" + b"function auth(){}")

        # Write the .md directly because write-file-doc now computes the hash
        # from the cite-file; a binary file would produce a hash but the
        # validate side's binary detection fires on the raw bytes. We use a
        # placeholder hash (any valid 64-char hex passes schema validation) so
        # validate-file-doc reaches the cite-file binary check.
        md_path = self.project_root / "docs" / "auth" / "index.ts.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            "---\n"
            'label: "Authentication entry point"\n'
            "confidence: extracted\n"
            'evidence_file: "src/auth/index.ts"\n'
            "evidence_start: 1\n"
            "evidence_end: 1\n"
            'content_hash: "{0}"\n'
            'model_version: "haiku"\n'
            "---\n\n# index.ts\n"
        ).format(_VALID_HASH)
        md_path.write_text(content, encoding="utf-8")

        r = self._validate_file_doc(md_path)
        self.assertEqual(r.returncode, 6, r.stderr.decode())
        self.assertIn(b"binary", r.stderr)


# ---------------------------------------------------------------------------
# Test 7: Cite range out-of-bounds -> exit 3.
# Strategy: write .md with cite_end=2 for a 2-line source file (valid), then
# shrink the source to 1 line. validate-file-doc re-reads the source and finds
# cite_end=2 exceeds the new 1-line count.
# ---------------------------------------------------------------------------


class TestCiteRangeOutOfBounds(_ValidateFileDocBase):

    def test_end_exceeds_line_count_exits_3(self):
        source_path = self._write_source("src/auth/index.ts", ["line1", "line2"])

        md_path = self.project_root / "docs" / "auth" / "index.ts.md"
        r = self._write_file_doc(
            md_path,
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=2,
        )
        self.assertEqual(r.returncode, 0, r.stderr.decode())

        # Shrink the source file to 1 line -- range 1-2 now exceeds line count.
        source_path.write_text("line1\n", encoding="utf-8")

        r = self._validate_file_doc(md_path)
        self.assertEqual(r.returncode, 3, r.stderr.decode())
        self.assertIn(b"exceed", r.stderr)


# ---------------------------------------------------------------------------
# Test 8: Hash drift -> exit 3.
# write-file-doc records the hash of the original source; mutating the source
# file afterwards causes validate-file-doc to recompute a different hash.
# ---------------------------------------------------------------------------


class TestHashDrift(_ValidateFileDocBase):

    def test_file_modified_after_write_exits_3(self):
        # Set up 3-line source file and matching .md.
        source_lines = ["original line 1", "original line 2", "original line 3"]
        md_path, source_path = self._setup_happy_md(source_lines=source_lines)

        # Modify the source file AFTER writing the .md; keep same line count
        # so range check passes and hash drift check fires.
        source_path.write_text(
            "modified line 1\nmodified line 2\nmodified line 3\n",
            encoding="utf-8",
        )

        r = self._validate_file_doc(md_path)
        self.assertEqual(r.returncode, 3, r.stderr.decode())
        self.assertIn(b"content_hash mismatch", r.stderr)


# ---------------------------------------------------------------------------
# Test 9: Sibling collision -> exit 4.
# ---------------------------------------------------------------------------


class TestSiblingCollision(_ValidateFileDocBase):

    def test_two_mds_same_label_exits_4(self):
        # Set up two source files.
        self._write_source("src/auth/login.ts", ["line1", "line2"])
        self._write_source("src/auth/logout.ts", ["line1", "line2"])

        # Both share the same label.
        docs_dir = self.project_root / "docs" / "auth"
        md_a = docs_dir / "login.ts.md"
        md_b = docs_dir / "logout.ts.md"

        label = "Authentication flow entry"

        r = self._write_file_doc(
            md_a, label=label,
            cite_file="src/auth/login.ts", cite_start=1, cite_end=2,
        )
        self.assertEqual(r.returncode, 0, r.stderr.decode())

        r = self._write_file_doc(
            md_b, label=label,
            cite_file="src/auth/logout.ts", cite_start=1, cite_end=2,
        )
        self.assertEqual(r.returncode, 0, r.stderr.decode())

        # Validating md_b should detect collision with md_a.
        r = self._validate_file_doc(md_b)
        self.assertEqual(r.returncode, 4, r.stderr.decode())
        self.assertIn(b"label collides", r.stderr)


# ---------------------------------------------------------------------------
# Test 10: Sibling parse error doesn't propagate -> exit 0 if current is valid.
# ---------------------------------------------------------------------------


class TestSiblingParseErrorIgnored(_ValidateFileDocBase):

    def test_unparseable_sibling_does_not_fail_current(self):
        self._write_source("src/auth/index.ts", ["line1", "line2"])

        docs_dir = self.project_root / "docs" / "auth"
        md_main = docs_dir / "index.ts.md"
        # Write a corrupted sibling (no leading fence).
        docs_dir.mkdir(parents=True, exist_ok=True)
        bad_sibling = docs_dir / "corrupted.ts.md"
        bad_sibling.write_text("this is not valid frontmatter\n", encoding="utf-8")

        r = self._write_file_doc(
            md_main,
            label="Authentication entry point",
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=2,
        )
        self.assertEqual(r.returncode, 0, r.stderr.decode())

        # Validate the good md -- corrupted sibling must not propagate failure.
        r = self._validate_file_doc(md_main)
        self.assertEqual(r.returncode, 0, r.stderr.decode())


# ---------------------------------------------------------------------------
# Test 11: Case-insensitive sibling collision -> exit 4.
# ---------------------------------------------------------------------------


class TestSiblingCaseInsensitiveCollision(_ValidateFileDocBase):

    def test_case_insensitive_label_collision_exits_4(self):
        self._write_source("src/auth/login.ts", ["line1", "line2"])
        self._write_source("src/auth/logout.ts", ["line1", "line2"])

        docs_dir = self.project_root / "docs" / "auth"
        md_a = docs_dir / "login.ts.md"
        md_b = docs_dir / "logout.ts.md"

        r = self._write_file_doc(
            md_a, label="User Auth Flow",
            cite_file="src/auth/login.ts", cite_start=1, cite_end=2,
        )
        self.assertEqual(r.returncode, 0)

        r = self._write_file_doc(
            md_b, label="user auth flow",
            cite_file="src/auth/logout.ts", cite_start=1, cite_end=2,
        )
        self.assertEqual(r.returncode, 0)

        r = self._validate_file_doc(md_b)
        self.assertEqual(r.returncode, 4, r.stderr.decode())
        self.assertIn(b"label collides", r.stderr)


# ---------------------------------------------------------------------------
# Test 12: Missing cite-file -> exit 3.
# write-file-doc now also checks cite-file existence (exits 2 if missing), so
# we cannot seed the .md via the helper for this case. Write the .md directly
# referencing a nonexistent source file; validate-file-doc -> exit 3.
# ---------------------------------------------------------------------------


class TestMissingCiteFile(_ValidateFileDocBase):

    def test_missing_cite_file_exits_3(self):
        md_path = self.project_root / "docs" / "auth" / "index.ts.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        # Write .md directly -- helper would exit 2 on missing cite-file.
        content = (
            "---\n"
            'label: "Authentication entry point"\n'
            "confidence: extracted\n"
            'evidence_file: "src/auth/does_not_exist.ts"\n'
            "evidence_start: 1\n"
            "evidence_end: 3\n"
            'content_hash: "{0}"\n'
            'model_version: "haiku"\n'
            "---\n\n# index.ts\n"
        ).format(_VALID_HASH)
        md_path.write_text(content, encoding="utf-8")

        r = self._validate_file_doc(md_path)
        self.assertEqual(r.returncode, 3, r.stderr.decode())
        self.assertIn(b"not found", r.stderr)


# ---------------------------------------------------------------------------
# Test 13: Order -- banned phrase before cite check (banned wins at exit 2).
# write-file-doc now requires cite-file to exist; write .md directly so we
# can have both banned label AND missing cite in the same file.
# ---------------------------------------------------------------------------


class TestOrderBannedBeforeCite(_ValidateFileDocBase):

    def test_banned_phrase_wins_over_missing_cite(self):
        md_path = self.project_root / "docs" / "auth" / "index.ts.md"
        md_path.parent.mkdir(parents=True, exist_ok=True)
        # Write .md directly -- helper would exit 2 on missing cite-file.
        content = (
            "---\n"
            'label: "handles authentication flow"\n'
            "confidence: extracted\n"
            'evidence_file: "src/auth/does_not_exist.ts"\n'
            "evidence_start: 1\n"
            "evidence_end: 3\n"
            'content_hash: "{0}"\n'
            'model_version: "haiku"\n'
            "---\n\n# index.ts\n"
        ).format(_VALID_HASH)
        md_path.write_text(content, encoding="utf-8")

        # Banned phrase (exit 2) must fire before cite check (exit 3).
        r = self._validate_file_doc(md_path)
        self.assertEqual(r.returncode, 2, r.stderr.decode())
        self.assertIn(b"handles", r.stderr)


if __name__ == "__main__":
    unittest.main()
