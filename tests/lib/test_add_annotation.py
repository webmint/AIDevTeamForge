"""Tests for `add-annotation` concern-tier setter (Step A.1 of VALIDATOR-LOOP-PLAN.md).

All 11 mandatory test cases from the brief are covered:

1.  Happy path — exit 0; state JSON contains correct 6-field annotation record;
    content_hash matches sha256 of file slice.
2.  Concern not registered → exit 2, stderr message.
3.  Package not registered → exit 2, stderr message.
4.  Invalid confidence enum → exit 2.
5.  Empty label → exit 2.
6.  Label with control chars (\\x01) → exit 2.
7.  Bad line range (start=0, end<start, non-int string) → exit 2.
8.  Cite-file unreadable (path does not exist) → exit 2.
9.  Content-hash determinism — same inputs → same hash; different range → different hash.
10. Overwrite semantics — second call at same target_path replaces first; no accumulation.
11. State validator round-trip — after add-annotation, validate-concern passes on well-formed
    annotation; hand-corrupted confidence makes validate-concern fail.

Test infrastructure mirrors _ConcernTestBase from test_generate_docs_helper.py:
- Each test runs in an isolated TemporaryDirectory.
- devforge_dir is `<tmproot>/.devforge/`.
- project_root is the tmproot (DEVFORGE_PROJECT_ROOT env var).
- CLI invocations go through `_run_cli` (subprocess → real argparse path).

Stdlib only.
"""

import hashlib
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
# Helpers
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


class _AnnotationTestBase(unittest.TestCase):
    """Isolated project root + devforge dir, shared helpers."""

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

    def _read_state(self):
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def _write_source(self, rel_path, lines):
        """Write a UTF-8 text file under project_root and return its Path."""
        full = self.project_root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return full

    def _init_pkg_concern(self, package="apps/web", concern="auth", name="web"):
        """Register a package and a concern under it."""
        r = self._run("add-package", "--path", package, "--name", name)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._run("add-concern", "--package", package, "--concern", concern)
        self.assertEqual(r.returncode, 0, r.stderr)

    def _add_annotation(
        self,
        package="apps/web",
        concern="auth",
        target_path="src/auth/index.ts",
        label="Authentication entry point",
        confidence="extracted",
        cite_file="src/auth/index.ts",
        cite_start=1,
        cite_end=3,
        model_version="claude-haiku-4-5-20251001",
    ):
        """Invoke add-annotation with the given (or defaulted) args."""
        return self._run(
            "add-annotation",
            "--package", package,
            "--concern", concern,
            "--target-path", target_path,
            "--label", label,
            "--confidence", confidence,
            "--cite-file", cite_file,
            "--cite-start", str(cite_start),
            "--cite-end", str(cite_end),
            "--model-version", model_version,
        )


# ---------------------------------------------------------------------------
# Test 1: Happy path
# ---------------------------------------------------------------------------


class HappyPathTests(_AnnotationTestBase):

    def test_exit_0_and_annotation_in_state(self):
        self._init_pkg_concern()
        source = self._write_source(
            "src/auth/index.ts",
            ["export default function auth() {", "  return true;", "}"],
        )
        proc = self._add_annotation(
            target_path="src/auth/index.ts",
            label="Authentication entry point",
            confidence="extracted",
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=3,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        state = self._read_state()
        concern = state["packages"]["apps/web"]["concerns"]["auth"]
        self.assertIn("src/auth/index.ts", concern["annotations"])
        ann = concern["annotations"]["src/auth/index.ts"]

        # All 6 fields present.
        self.assertEqual(ann["label"], "Authentication entry point")
        self.assertEqual(ann["confidence"], "extracted")
        self.assertIsInstance(ann["evidence"], dict)
        self.assertEqual(ann["evidence"]["file"], "src/auth/index.ts")
        self.assertEqual(ann["evidence"]["start"], 1)
        self.assertEqual(ann["evidence"]["end"], 3)
        self.assertEqual(ann["model_version"], "claude-haiku-4-5-20251001")
        self.assertIn("content_hash", ann)
        self.assertIsInstance(ann["content_hash"], str)
        self.assertTrue(len(ann["content_hash"]) == 64)  # sha256 hex

    def test_content_hash_matches_sha256_of_slice(self):
        self._init_pkg_concern()
        lines = [
            "export default function auth() {",
            "  return true;",
            "}",
            "// extra line",
        ]
        self._write_source("src/auth/index.ts", lines)
        proc = self._add_annotation(
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=3,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        # Compute expected hash the same way the setter does:
        # join lines 1-3 with '\n' (splitlines strips endings).
        slice_text = "\n".join(lines[0:3])
        expected_hash = hashlib.sha256(slice_text.encode("utf-8")).hexdigest()

        state = self._read_state()
        ann = state["packages"]["apps/web"]["concerns"]["auth"]["annotations"][
            "src/auth/index.ts"
        ]
        self.assertEqual(ann["content_hash"], expected_hash)

    def test_stderr_info_message_emitted(self):
        self._init_pkg_concern()
        self._write_source("src/auth/index.ts", ["a", "b", "c"])
        proc = self._add_annotation()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(b"annotation recorded", proc.stderr)
        self.assertIn(b"apps/web/auth", proc.stderr)
        self.assertIn(b"src/auth/index.ts", proc.stderr)


# ---------------------------------------------------------------------------
# Test 2: Concern not registered
# ---------------------------------------------------------------------------


class ConcernNotRegisteredTests(_AnnotationTestBase):

    def test_concern_missing_exits_2(self):
        # Package registered, concern not.
        self._run("add-package", "--path", "apps/web", "--name", "web")
        self._write_source("src/auth/index.ts", ["a", "b", "c"])
        proc = self._add_annotation(package="apps/web", concern="missing")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"concern not registered", proc.stderr)


# ---------------------------------------------------------------------------
# Test 3: Package not registered
# ---------------------------------------------------------------------------


class PackageNotRegisteredTests(_AnnotationTestBase):

    def test_package_missing_exits_2(self):
        self._write_source("src/auth/index.ts", ["a", "b", "c"])
        proc = self._add_annotation(package="apps/ghost", concern="auth")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"package not registered", proc.stderr)


# ---------------------------------------------------------------------------
# Test 4: Invalid confidence enum
# ---------------------------------------------------------------------------


class InvalidConfidenceTests(_AnnotationTestBase):

    def test_bad_confidence_exits_2(self):
        self._init_pkg_concern()
        self._write_source("src/auth/index.ts", ["a", "b", "c"])
        proc = self._add_annotation(confidence="BOGUS")
        self.assertEqual(proc.returncode, 2)
        # Should mention the bad value or "must be one of".
        self.assertTrue(
            b"must be one of" in proc.stderr or b"BOGUS" in proc.stderr,
            proc.stderr,
        )


# ---------------------------------------------------------------------------
# Test 5: Empty label
# ---------------------------------------------------------------------------


class EmptyLabelTests(_AnnotationTestBase):

    def test_empty_label_exits_2(self):
        self._init_pkg_concern()
        self._write_source("src/auth/index.ts", ["a", "b", "c"])
        proc = self._add_annotation(label="")
        self.assertEqual(proc.returncode, 2)

    def test_whitespace_only_label_exits_2(self):
        self._init_pkg_concern()
        self._write_source("src/auth/index.ts", ["a", "b", "c"])
        proc = self._add_annotation(label="   ")
        self.assertEqual(proc.returncode, 2)


# ---------------------------------------------------------------------------
# Test 6: Label with control chars
# ---------------------------------------------------------------------------


class ControlCharLabelTests(_AnnotationTestBase):

    def test_control_char_in_label_exits_2(self):
        self._init_pkg_concern()
        self._write_source("src/auth/index.ts", ["a", "b", "c"])
        # \x01 is a control char (< 0x20, not \t/\n/\r).
        proc = self._add_annotation(label="bad\x01label")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"control character", proc.stderr)

    def test_del_byte_in_label_exits_2(self):
        self._init_pkg_concern()
        self._write_source("src/auth/index.ts", ["a", "b", "c"])
        proc = self._add_annotation(label="bad\x7flabel")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"control character", proc.stderr)


# ---------------------------------------------------------------------------
# Test 7: Bad line range
# ---------------------------------------------------------------------------


class BadLineRangeTests(_AnnotationTestBase):

    def _setup(self):
        self._init_pkg_concern()
        self._write_source("src/auth/index.ts", ["a", "b", "c"])

    def test_start_zero_exits_2(self):
        self._setup()
        proc = self._run(
            "add-annotation",
            "--package", "apps/web",
            "--concern", "auth",
            "--target-path", "src/auth/index.ts",
            "--label", "ok",
            "--confidence", "extracted",
            "--cite-file", "src/auth/index.ts",
            "--cite-start", "0",
            "--cite-end", "2",
            "--model-version", "v1",
        )
        self.assertEqual(proc.returncode, 2)

    def test_end_less_than_start_exits_2(self):
        self._setup()
        proc = self._run(
            "add-annotation",
            "--package", "apps/web",
            "--concern", "auth",
            "--target-path", "src/auth/index.ts",
            "--label", "ok",
            "--confidence", "extracted",
            "--cite-file", "src/auth/index.ts",
            "--cite-start", "5",
            "--cite-end", "3",
            "--model-version", "v1",
        )
        self.assertEqual(proc.returncode, 2)

    def test_non_int_cite_start_rejected_by_argparse(self):
        # argparse declares --cite-start type=int; non-int fails at parse.
        self._setup()
        proc = self._run(
            "add-annotation",
            "--package", "apps/web",
            "--concern", "auth",
            "--target-path", "src/auth/index.ts",
            "--label", "ok",
            "--confidence", "extracted",
            "--cite-file", "src/auth/index.ts",
            "--cite-start", "abc",
            "--cite-end", "3",
            "--model-version", "v1",
        )
        # argparse exits with code 2 on type-conversion failure.
        self.assertEqual(proc.returncode, 2)

    def test_cite_start_beyond_line_count_exits_2(self):
        # 3-line file, cite_start=10 exceeds line count.
        self._init_pkg_concern()
        self._write_source("src/auth/index.ts", ["a", "b", "c"])
        proc = self._run(
            "add-annotation",
            "--package", "apps/web",
            "--concern", "auth",
            "--target-path", "src/auth/index.ts",
            "--label", "ok",
            "--confidence", "extracted",
            "--cite-file", "src/auth/index.ts",
            "--cite-start", "10",
            "--cite-end", "10",
            "--model-version", "v1",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"exceed", proc.stderr)

    def test_cite_end_beyond_line_count_exits_2(self):
        # 3-line file, cite_end=100 exceeds line count.
        self._init_pkg_concern()
        self._write_source("src/auth/index.ts", ["a", "b", "c"])
        proc = self._run(
            "add-annotation",
            "--package", "apps/web",
            "--concern", "auth",
            "--target-path", "src/auth/index.ts",
            "--label", "ok",
            "--confidence", "extracted",
            "--cite-file", "src/auth/index.ts",
            "--cite-start", "1",
            "--cite-end", "100",
            "--model-version", "v1",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"exceed", proc.stderr)


# ---------------------------------------------------------------------------
# Test 8: Cite-file unreadable
# ---------------------------------------------------------------------------


class CiteFileUnreadableTests(_AnnotationTestBase):

    def test_missing_cite_file_exits_2(self):
        self._init_pkg_concern()
        # Do NOT write the source file.
        proc = self._add_annotation(cite_file="nonexistent/path.ts")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"cite-file not readable", proc.stderr)


# ---------------------------------------------------------------------------
# Test 9: Content-hash determinism
# ---------------------------------------------------------------------------


class ContentHashDeterminismTests(_AnnotationTestBase):

    def test_same_inputs_same_hash(self):
        self._init_pkg_concern()
        self._write_source("src/auth/index.ts", ["a", "b", "c"])
        proc1 = self._add_annotation(
            target_path="path1.ts",
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=2,
        )
        proc2 = self._add_annotation(
            target_path="path2.ts",
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=2,
        )
        self.assertEqual(proc1.returncode, 0, proc1.stderr)
        self.assertEqual(proc2.returncode, 0, proc2.stderr)

        state = self._read_state()
        annotations = state["packages"]["apps/web"]["concerns"]["auth"]["annotations"]
        self.assertEqual(
            annotations["path1.ts"]["content_hash"],
            annotations["path2.ts"]["content_hash"],
        )

    def test_different_cite_range_different_hash(self):
        self._init_pkg_concern()
        self._write_source("src/auth/index.ts", ["a", "b", "c"])
        proc1 = self._add_annotation(
            target_path="path1.ts",
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=1,
        )
        proc2 = self._add_annotation(
            target_path="path2.ts",
            cite_file="src/auth/index.ts",
            cite_start=2,
            cite_end=3,
        )
        self.assertEqual(proc1.returncode, 0, proc1.stderr)
        self.assertEqual(proc2.returncode, 0, proc2.stderr)

        state = self._read_state()
        annotations = state["packages"]["apps/web"]["concerns"]["auth"]["annotations"]
        self.assertNotEqual(
            annotations["path1.ts"]["content_hash"],
            annotations["path2.ts"]["content_hash"],
        )


# ---------------------------------------------------------------------------
# Test 10: Overwrite semantics
# ---------------------------------------------------------------------------


class OverwriteSemanticsTests(_AnnotationTestBase):

    def test_second_call_replaces_first_no_accumulation(self):
        self._init_pkg_concern()
        self._write_source("src/auth/index.ts", ["a", "b", "c"])

        proc1 = self._add_annotation(
            target_path="src/auth/index.ts",
            label="First label",
            confidence="inferred",
        )
        self.assertEqual(proc1.returncode, 0, proc1.stderr)

        proc2 = self._add_annotation(
            target_path="src/auth/index.ts",
            label="Second label (replacement)",
            confidence="ambiguous",
        )
        self.assertEqual(proc2.returncode, 0, proc2.stderr)

        state = self._read_state()
        annotations = state["packages"]["apps/web"]["concerns"]["auth"]["annotations"]
        # Exactly one entry at the target_path.
        self.assertEqual(len(annotations), 1)
        ann = annotations["src/auth/index.ts"]
        # Latest values win.
        self.assertEqual(ann["label"], "Second label (replacement)")
        self.assertEqual(ann["confidence"], "ambiguous")


# ---------------------------------------------------------------------------
# Test 11: State validator round-trip
# ---------------------------------------------------------------------------


class ValidatorRoundTripTests(_AnnotationTestBase):
    """After add-annotation, validate-concern must still handle the annotation
    field correctly.  We can't make validate-concern pass without all required
    concern fields, so we verify:
    (a) a well-formed annotation doesn't ADD new errors to validate-concern,
    (b) a hand-corrupted annotation record causes validate-concern to fail with
        a clear message about the malformed field.
    """

    def _populate_valid_concern(self, package="apps/web", concern="auth"):
        """Register a package + concern with all required fields populated
        so validate-concern can potentially pass (minus the annotation check).

        We populate all required fields (overview, directory_tree, public_surface).
        The cite source file needs to exist and the snippet must match verbatim.
        """
        self._init_pkg_concern(package=package, concern=concern)

        # Write a source file whose content we'll use for codeblocks.
        src_content = [
            "export function doAuth() {",
            "  return true;",
            "}",
        ]
        self._write_source("src/auth/index.ts", src_content)
        snippet = "\n".join(src_content)

        self._run(
            "set-concern-overview",
            "--package", package, "--concern", concern,
            "--text", "Auth module handles authentication.",
        )
        self._run(
            "set-concern-tree",
            "--package", package, "--concern", concern,
            "--text", "src/auth/\n  index.ts\n  helpers.ts",
        )
        # add-concern-export requires a code snippet that verbatim-matches the cite.
        self._run(
            "add-concern-export",
            "--package", package, "--concern", concern,
            "--name", "doAuth",
            "--kind", "function",
            "--description", "Performs authentication.",
            "--language", "typescript",
            "--code-snippet", snippet,
            "--cite-file", "src/auth/index.ts",
            "--cite-start", "1",
            "--cite-end", "3",
        )

    def test_well_formed_annotation_does_not_break_validate_concern(self):
        self._populate_valid_concern()
        self._write_source("src/auth/index.ts", [
            "export function doAuth() {",
            "  return true;",
            "}",
        ])
        proc = self._add_annotation(
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=2,
            label="Auth entry",
            confidence="extracted",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        # validate-concern should pass (zero errors) — the annotation
        # field is valid and does not surface additional errors.
        # NOTE: this fixture does not write index.json, so B.2's
        # `file-docs-incomplete` rule gracefully degrades and is skipped.
        # The test exercises annotation-shape rules, not B.2 enforcement.
        vproc = self._run(
            "validate-concern",
            "--package", "apps/web",
            "--concern", "auth",
        )
        self.assertEqual(vproc.returncode, 0, vproc.stderr)

    def test_corrupted_annotation_confidence_fails_validate_concern(self):
        self._populate_valid_concern()
        self._write_source("src/auth/index.ts", [
            "export function doAuth() {",
            "  return true;",
            "}",
        ])
        # Register a valid annotation first.
        proc = self._add_annotation(
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=2,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        # Directly corrupt the state: set confidence to an invalid value.
        state = self._read_state()
        annotation = state["packages"]["apps/web"]["concerns"]["auth"][
            "annotations"
        ]["src/auth/index.ts"]
        annotation["confidence"] = "INVALID_CONFIDENCE"
        self.state_file.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        # validate-concern should now fail and mention the confidence issue.
        vproc = self._run(
            "validate-concern",
            "--package", "apps/web",
            "--concern", "auth",
        )
        self.assertNotEqual(vproc.returncode, 0)
        self.assertTrue(
            b"confidence" in vproc.stderr or b"INVALID_CONFIDENCE" in vproc.stderr,
            vproc.stderr,
        )

    def test_corrupted_annotation_missing_label_fails_validate_concern(self):
        self._populate_valid_concern()
        self._write_source("src/auth/index.ts", [
            "export function doAuth() {",
            "  return true;",
            "}",
        ])
        proc = self._add_annotation(
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=2,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)

        # Remove the label field entirely.
        state = self._read_state()
        ann = state["packages"]["apps/web"]["concerns"]["auth"][
            "annotations"
        ]["src/auth/index.ts"]
        del ann["label"]
        self.state_file.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        vproc = self._run(
            "validate-concern",
            "--package", "apps/web",
            "--concern", "auth",
        )
        self.assertNotEqual(vproc.returncode, 0)
        self.assertIn(b"label", vproc.stderr)


# ---------------------------------------------------------------------------
# Smoke test: default_concern_record includes annotations key
# ---------------------------------------------------------------------------


class DefaultConcernRecordTests(unittest.TestCase):

    def test_annotations_key_present_and_empty_dict(self):
        rec = gdh.default_concern_record("myfeature")
        self.assertIn("annotations", rec)
        self.assertEqual(rec["annotations"], {})

    def test_all_existing_fields_still_present(self):
        rec = gdh.default_concern_record("myfeature")
        expected_fields = {
            "concern_name", "overview", "directory_tree",
            "public_surface", "types", "dependencies",
            "hazards", "usage_example", "annotations",
        }
        self.assertEqual(set(rec.keys()), expected_fields)


if __name__ == "__main__":
    unittest.main()
