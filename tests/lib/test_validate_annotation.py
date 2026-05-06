"""Tests for `validate-annotation` mechanical validator (Step A.2 of VALIDATOR-LOOP-PLAN.md).

Exit-code contract under test:
  0 — all checks pass
  2 — banned-phrase hit OR lookup failure (not registered)
  3 — cite unresolvable (missing / range / hash_drift)
  4 — specificity fail (sibling label collision in same concern)
  5 — schema invalid
  6 — cite-file is binary

19 test cases (brief §"Tests"):
  1.  Happy path — all checks pass → exit 0.
  2.  Schema fail — missing label → exit 5.
  3.  Schema fail — confidence not in enum → exit 5.
  4.  Schema fail — content_hash wrong format (16 chars) → exit 5.
  5.  Banned phrase — `handles` → exit 2, stderr names `handles`.
  6.  Banned phrase — `responsible for` (multi-word) → exit 2.
  7.  Banned phrase — case-insensitive (`Handles`) → exit 2.
  8.  Banned phrase — substring NOT counted (`handler` not `handles`) → exit 0.
  9.  Cite-file missing → exit 3, stderr says "not found".
 10.  Cite-file binary (NUL byte) → exit 6, stderr says "binary".
 11.  Cite range out of bounds (end > line_count) → exit 3.
 12.  Content-hash drift (file modified after annotation) → exit 3, "content_hash mismatch".
 13.  Specificity collision (same label, different target_path) → exit 4.
 14.  Specificity case-insensitive (`User Service` vs `user service`) → exit 4.
 15.  No sibling collision across DIFFERENT concerns → exit 0.
 16.  Annotation not registered → exit 2, "annotation not registered".
 17.  Concern not registered → exit 2.
 18.  Package not registered → exit 2.
 19.  Order test — both banned phrase AND hash drift; banned-phrase wins (exit 2).

Infrastructure mirrors test_add_annotation.py: subprocess invocations,
isolated TemporaryDirectory, devforge_dir + project_root env vars.

Stdlib only.
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
# Shared helpers
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


class _ValidateAnnotationBase(unittest.TestCase):
    """Isolated tmp dir + shared setup helpers."""

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

    def _write_state_direct(self, state):
        """Overwrite the state file directly (for injecting corrupt records)."""
        self.state_file.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _init_pkg_concern(self, package="apps/web", concern="auth", name="web"):
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

    def _validate_annotation(
        self,
        package="apps/web",
        concern="auth",
        target_path="src/auth/index.ts",
    ):
        return self._run(
            "validate-annotation",
            "--package", package,
            "--concern", concern,
            "--target-path", target_path,
        )

    def _setup_happy_annotation(
        self,
        lines=None,
        label="Authentication entry point",
        package="apps/web",
        concern="auth",
        target_path="src/auth/index.ts",
        cite_file="src/auth/index.ts",
        cite_start=1,
        cite_end=3,
    ):
        """Register pkg + concern + source file + annotation. Returns source lines."""
        if lines is None:
            lines = [
                "export default function auth() {",
                "  return true;",
                "}",
            ]
        self._init_pkg_concern(package=package, concern=concern)
        self._write_source(cite_file, lines)
        r = self._add_annotation(
            package=package,
            concern=concern,
            target_path=target_path,
            label=label,
            confidence="extracted",
            cite_file=cite_file,
            cite_start=cite_start,
            cite_end=cite_end,
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        return lines


# ---------------------------------------------------------------------------
# Test 1: Happy path
# ---------------------------------------------------------------------------


class HappyPathTest(_ValidateAnnotationBase):

    def test_all_checks_pass_exit_0(self):
        self._setup_happy_annotation()
        r = self._validate_annotation()
        self.assertEqual(r.returncode, 0, r.stderr)


# ---------------------------------------------------------------------------
# Test 2: Schema fail — missing label
# ---------------------------------------------------------------------------


class SchemaFailMissingLabelTest(_ValidateAnnotationBase):

    def test_missing_label_exits_5(self):
        self._setup_happy_annotation()
        # Corrupt state: remove label.
        state = self._read_state()
        ann = state["packages"]["apps/web"]["concerns"]["auth"]["annotations"][
            "src/auth/index.ts"
        ]
        del ann["label"]
        self._write_state_direct(state)

        r = self._validate_annotation()
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertIn(b"label", r.stderr)


# ---------------------------------------------------------------------------
# Test 3: Schema fail — confidence not in enum
# ---------------------------------------------------------------------------


class SchemaFailBadConfidenceTest(_ValidateAnnotationBase):

    def test_bad_confidence_exits_5(self):
        self._setup_happy_annotation()
        state = self._read_state()
        ann = state["packages"]["apps/web"]["concerns"]["auth"]["annotations"][
            "src/auth/index.ts"
        ]
        ann["confidence"] = "BOGUS_CONFIDENCE"
        self._write_state_direct(state)

        r = self._validate_annotation()
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertIn(b"confidence", r.stderr)


# ---------------------------------------------------------------------------
# Test 4: Schema fail — content_hash wrong format
# ---------------------------------------------------------------------------


class SchemaFailBadHashFormatTest(_ValidateAnnotationBase):

    def test_short_content_hash_exits_5(self):
        self._setup_happy_annotation()
        state = self._read_state()
        ann = state["packages"]["apps/web"]["concerns"]["auth"]["annotations"][
            "src/auth/index.ts"
        ]
        # Only 16 chars — far short of the required 64.
        ann["content_hash"] = "deadbeef12345678"
        self._write_state_direct(state)

        r = self._validate_annotation()
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertIn(b"content_hash", r.stderr)


# ---------------------------------------------------------------------------
# Test 5: Banned phrase — `handles`
# ---------------------------------------------------------------------------


class BannedPhraseHandlesTest(_ValidateAnnotationBase):

    def test_handles_in_label_exits_2(self):
        self._setup_happy_annotation(label="handles authentication flow")
        r = self._validate_annotation()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"handles", r.stderr)


# ---------------------------------------------------------------------------
# Test 6: Banned phrase — `responsible for` (multi-word)
# ---------------------------------------------------------------------------


class BannedPhraseResponsibleForTest(_ValidateAnnotationBase):

    def test_responsible_for_in_label_exits_2(self):
        self._setup_happy_annotation(label="module responsible for auth")
        r = self._validate_annotation()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"responsible for", r.stderr)


# ---------------------------------------------------------------------------
# Test 7: Banned phrase — case-insensitive
# ---------------------------------------------------------------------------


class BannedPhraseCaseInsensitiveTest(_ValidateAnnotationBase):

    def test_handles_uppercase_in_label_exits_2(self):
        self._setup_happy_annotation(label="Handles user data")
        r = self._validate_annotation()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"handles", r.stderr)


# ---------------------------------------------------------------------------
# Test 8: Banned phrase — substring NOT counted (word boundary)
# ---------------------------------------------------------------------------


class BannedPhraseWordBoundaryTest(_ValidateAnnotationBase):

    def test_handler_does_not_trigger_handles(self):
        # "handler" contains "handle" but NOT "handles" as a whole word.
        self._setup_happy_annotation(label="request handler dispatch")
        r = self._validate_annotation()
        # Should pass all checks (exit 0) — "handler" is not "handles".
        self.assertEqual(r.returncode, 0, r.stderr)


# ---------------------------------------------------------------------------
# Test 9: Cite-file missing
# ---------------------------------------------------------------------------


class CiteFileMissingTest(_ValidateAnnotationBase):

    def test_missing_cite_file_exits_3(self):
        self._setup_happy_annotation()
        # Delete the source file after annotation was recorded.
        src = self.project_root / "src" / "auth" / "index.ts"
        src.unlink()

        r = self._validate_annotation()
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn(b"not found", r.stderr)


# ---------------------------------------------------------------------------
# Test 10: Cite-file binary
# ---------------------------------------------------------------------------


class CiteFileBinaryTest(_ValidateAnnotationBase):

    def test_binary_cite_file_exits_6(self):
        self._setup_happy_annotation()
        # Overwrite the source file with binary content (NUL byte).
        src = self.project_root / "src" / "auth" / "index.ts"
        src.write_bytes(b"export default " + b"\x00" + b" function auth() {}")

        r = self._validate_annotation()
        self.assertEqual(r.returncode, 6, r.stderr)
        self.assertIn(b"binary", r.stderr)


# ---------------------------------------------------------------------------
# Test 11: Cite range out of bounds
# ---------------------------------------------------------------------------


class CiteRangeOutOfBoundsTest(_ValidateAnnotationBase):

    def test_file_shrunk_range_exits_3(self):
        # Annotation recorded with end=3 on a 3-line file.
        self._setup_happy_annotation(
            lines=["line1", "line2", "line3"],
            cite_start=1,
            cite_end=3,
        )
        # Shrink file to 1 line so end=3 exceeds line count.
        src = self.project_root / "src" / "auth" / "index.ts"
        src.write_text("line1\n", encoding="utf-8")

        r = self._validate_annotation()
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn(b"exceed", r.stderr)


# ---------------------------------------------------------------------------
# Test 12: Content-hash drift
# ---------------------------------------------------------------------------


class ContentHashDriftTest(_ValidateAnnotationBase):

    def test_file_modified_after_annotation_exits_3(self):
        self._setup_happy_annotation(
            lines=["original line 1", "original line 2", "original line 3"],
            cite_start=1,
            cite_end=3,
        )
        # Modify the file AFTER annotation was recorded.
        src = self.project_root / "src" / "auth" / "index.ts"
        src.write_text("changed content\nline2\nline3\n", encoding="utf-8")

        r = self._validate_annotation()
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn(b"content_hash mismatch", r.stderr)


# ---------------------------------------------------------------------------
# Test 13: Specificity collision (same label, different target_path)
# ---------------------------------------------------------------------------


class SpecificityCollisionTest(_ValidateAnnotationBase):

    def test_sibling_same_label_exits_4(self):
        self._init_pkg_concern()
        self._write_source("src/auth/index.ts", ["line1", "line2", "line3"])

        # First annotation — target_path="path_a.ts".
        r = self._add_annotation(
            target_path="path_a.ts",
            label="Auth entry point",
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=2,
        )
        self.assertEqual(r.returncode, 0, r.stderr)

        # Second annotation — same label, different target_path.
        r = self._add_annotation(
            target_path="path_b.ts",
            label="Auth entry point",
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=2,
        )
        self.assertEqual(r.returncode, 0, r.stderr)

        # Validate the second annotation — should collide with path_a.ts.
        r = self._validate_annotation(target_path="path_b.ts")
        self.assertEqual(r.returncode, 4, r.stderr)
        self.assertIn(b"label collides", r.stderr)


# ---------------------------------------------------------------------------
# Test 14: Specificity case-insensitive collision
# ---------------------------------------------------------------------------


class SpecificityCaseInsensitiveTest(_ValidateAnnotationBase):

    def test_case_insensitive_label_collision_exits_4(self):
        self._init_pkg_concern()
        self._write_source("src/auth/index.ts", ["line1", "line2", "line3"])

        # "User Service" in path_a.ts
        r = self._add_annotation(
            target_path="path_a.ts",
            label="User Service",
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=1,
        )
        self.assertEqual(r.returncode, 0, r.stderr)

        # "user service" (lowercase) in path_b.ts — same after normalization.
        r = self._add_annotation(
            target_path="path_b.ts",
            label="user service",
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=1,
        )
        self.assertEqual(r.returncode, 0, r.stderr)

        # Both path_b validate should detect collision with path_a.
        r = self._validate_annotation(target_path="path_b.ts")
        self.assertEqual(r.returncode, 4, r.stderr)
        self.assertIn(b"label collides", r.stderr)


# ---------------------------------------------------------------------------
# Test 15: Same label across DIFFERENT concerns is OK
# ---------------------------------------------------------------------------


class SiblingAcrossConcernsOkTest(_ValidateAnnotationBase):

    def test_same_label_different_concern_exit_0(self):
        # Register two concerns under the same package.
        self._run("add-package", "--path", "apps/web", "--name", "web")
        self._run("add-concern", "--package", "apps/web", "--concern", "auth")
        self._run("add-concern", "--package", "apps/web", "--concern", "payments")

        self._write_source("src/auth/index.ts", ["line1", "line2", "line3"])

        # Same label in auth concern.
        r = self._add_annotation(
            concern="auth",
            target_path="src/auth/index.ts",
            label="Module entry point",
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=1,
        )
        self.assertEqual(r.returncode, 0, r.stderr)

        # Same label in payments concern — should NOT be a collision.
        r = self._add_annotation(
            concern="payments",
            target_path="src/auth/index.ts",
            label="Module entry point",
            cite_file="src/auth/index.ts",
            cite_start=1,
            cite_end=1,
        )
        self.assertEqual(r.returncode, 0, r.stderr)

        # Validate the payments annotation — no sibling in payments concern, exit 0.
        r = self._validate_annotation(
            concern="payments",
            target_path="src/auth/index.ts",
        )
        self.assertEqual(r.returncode, 0, r.stderr)


# ---------------------------------------------------------------------------
# Test 16: Annotation not registered
# ---------------------------------------------------------------------------


class AnnotationNotRegisteredTest(_ValidateAnnotationBase):

    def test_missing_annotation_exits_2(self):
        self._init_pkg_concern()
        # Do NOT add any annotation.
        r = self._validate_annotation(target_path="nonexistent.ts")
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"annotation not registered", r.stderr)


# ---------------------------------------------------------------------------
# Test 17: Concern not registered
# ---------------------------------------------------------------------------


class ConcernNotRegisteredTest(_ValidateAnnotationBase):

    def test_missing_concern_exits_2(self):
        self._run("add-package", "--path", "apps/web", "--name", "web")
        # Concern "ghost" was never added.
        r = self._validate_annotation(concern="ghost")
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"concern", r.stderr)


# ---------------------------------------------------------------------------
# Test 18: Package not registered
# ---------------------------------------------------------------------------


class PackageNotRegisteredTest(_ValidateAnnotationBase):

    def test_missing_package_exits_2(self):
        r = self._validate_annotation(package="apps/ghost", concern="auth")
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"package not registered", r.stderr)


# ---------------------------------------------------------------------------
# Test 19: Order test — banned phrase wins over hash drift
# ---------------------------------------------------------------------------


class OrderBannedPhraseBeforeHashDriftTest(_ValidateAnnotationBase):
    """Annotation has BOTH a banned phrase AND a hash drift.

    The spec orders: schema -> banned-phrase -> cite-exists -> binary ->
    range -> hash-drift. So banned-phrase (exit 2) must fire before
    hash-drift (exit 3).
    """

    def test_banned_phrase_before_hash_drift(self):
        # Set up annotation with a banned phrase.
        self._setup_happy_annotation(label="handles authentication requests")

        # Now modify the source file so the hash would drift.
        src = self.project_root / "src" / "auth" / "index.ts"
        src.write_text("totally different content\n", encoding="utf-8")

        # Banned phrase check runs before hash check → must exit 2, not 3.
        r = self._validate_annotation()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"handles", r.stderr)


# ---------------------------------------------------------------------------
# Fix 1 regression: production env (DEVFORGE_DIR set, DEVFORGE_PROJECT_ROOT
# unset) must not produce false hash drift when invoked from a different cwd.
# ---------------------------------------------------------------------------


class ProductionEnvRoundTripTest(unittest.TestCase):
    """Round-trip add-annotation → validate-annotation in the production
    environment shape: DEVFORGE_DIR is set, DEVFORGE_PROJECT_ROOT is NOT set.
    Invocation is from a cwd that differs from DEVFORGE_DIR.parent.

    Before Fix 1, the setter resolved cite-file from cwd while the validator
    resolved from DEVFORGE_DIR.parent — different roots → hash drift → exit 3.
    After Fix 1, both use _project_root() (DEVFORGE_DIR.parent), so hashes
    agree regardless of cwd.
    """

    def setUp(self):
        self._saved_devforge = os.environ.pop("DEVFORGE_DIR", None)
        self._saved_root = os.environ.pop("DEVFORGE_PROJECT_ROOT", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self._tmp.name) / "myproject"
        self.project_root.mkdir(parents=True, exist_ok=True)
        self.devforge_dir = self.project_root / ".devforge"
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        # A separate directory to use as cwd — intentionally different from
        # project_root so any cwd-based resolution diverges from DEVFORGE_DIR.parent.
        self.other_cwd = Path(self._tmp.name) / "othercwd"
        self.other_cwd.mkdir(parents=True, exist_ok=True)

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

    def _run_from_cwd(self, cwd, *args):
        """Run the helper with DEVFORGE_DIR set but DEVFORGE_PROJECT_ROOT unset,
        from the given cwd."""
        env = os.environ.copy()
        env["DEVFORGE_DIR"] = str(self.devforge_dir)
        env.pop("DEVFORGE_PROJECT_ROOT", None)
        return subprocess.run(
            [sys.executable, str(_HELPER_PY)] + list(args),
            env=env,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_no_hash_drift_when_devforge_dir_set_and_cwd_differs(self):
        """Setter and validator both route through _project_root() which derives
        project root from DEVFORGE_DIR.parent. The cwd (other_cwd) is different,
        so any cwd-based resolution would produce a divergent root and a
        false hash drift (exit 3). The fix eliminates this false positive."""
        # Write source file under project_root (where _project_root() points).
        src = self.project_root / "src" / "auth" / "index.ts"
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text("line1\nline2\nline3\n", encoding="utf-8")

        # Register package and concern (cwd=other_cwd; DEVFORGE_DIR is the key).
        r = self._run_from_cwd(
            self.other_cwd,
            "add-package", "--path", "apps/web", "--name", "web",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._run_from_cwd(
            self.other_cwd,
            "add-concern", "--package", "apps/web", "--concern", "auth",
        )
        self.assertEqual(r.returncode, 0, r.stderr)

        # add-annotation from other_cwd — cite-file is relative to project_root
        # (via DEVFORGE_DIR.parent), not cwd.
        r = self._run_from_cwd(
            self.other_cwd,
            "add-annotation",
            "--package", "apps/web",
            "--concern", "auth",
            "--target-path", "src/auth/index.ts",
            "--label", "Authentication entry point",
            "--confidence", "extracted",
            "--cite-file", "src/auth/index.ts",
            "--cite-start", "1",
            "--cite-end", "3",
            "--model-version", "v-test",
        )
        self.assertEqual(r.returncode, 0, r.stderr)

        # validate-annotation from other_cwd — must agree on the same project_root.
        r = self._run_from_cwd(
            self.other_cwd,
            "validate-annotation",
            "--package", "apps/web",
            "--concern", "auth",
            "--target-path", "src/auth/index.ts",
        )
        # Before Fix 1: exit 3 (false hash drift). After Fix 1: exit 0.
        self.assertEqual(r.returncode, 0, r.stderr)


# ---------------------------------------------------------------------------
# Fix 2: hyphenated compound triggers banned phrase (word-boundary behavior).
# ---------------------------------------------------------------------------


class BannedPhraseHyphenatedCompoundTest(_ValidateAnnotationBase):
    """A hyphen counts as a word boundary in Python's `\\b` regex, so
    `validates-input` triggers the `validates` ban.

    This is intentional: annotation labels are noun-phrase descriptions,
    not identifier copies. A hyphenated compound carrying a banned verb
    is still archetype substitution.
    """

    def test_hyphenated_compound_triggers_banned_phrase(self):
        self._setup_happy_annotation(label="validates-input guard layer")
        r = self._validate_annotation()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"validates", r.stderr)


if __name__ == "__main__":
    unittest.main()
