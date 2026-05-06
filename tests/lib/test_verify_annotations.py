"""Tests for `verify-annotations` post-batch aggregator (Step A.4 of VALIDATOR-LOOP-PLAN.md).

Exit-code contract under test:
  0 — all gates pass
  2 — at least one gate failed
  5 — schema/state error (package not registered, concern not registered,
      or state-corrupt confidence value)

Gate thresholds (locked):
  banned_phrase   : 0 tolerated
  ambiguous_rate  : <= 10%
  cross_concern_duplicate: <= 5%

Metrics reported but NOT gated:
  sibling_collision_count  — validated by validate-annotation; aggregator reports only
  missing_cite_count       — validated by validate-annotation; aggregator reports only

22 test cases (brief §"Tests" + Fix 2 cross-directory case + 5 vacuous-pass tests for the post-empirical Fix A):
  1.  Happy path — clean annotations → exit 0, report correct.
  2.  Banned phrase present → exit 2, stderr "banned_phrase gate FAIL".
  3.  Sibling collision — reported in JSON but NOT gated → exit 0 + collision_count in report.
  3b. Sibling collision — cross-directory (different parent dirs, identical labels) → count = 2, exit 0.
  4.  Missing cite-file — reported in JSON, NOT gated → exit 0.
  5.  Ambiguous rate exactly 10% (threshold is <=) → "pass" → exit 0.
  6.  Ambiguous rate 12% (12/100) → gate fail → exit 2.
  7.  Cross-concern duplicates 5% (20 ann / 1 match) → "pass" → exit 0.
  8.  Cross-concern duplicates 6% (10 ann / 1 match = 10%) → gate fail → exit 2.
  9.  Empty annotations dict → all rates 0.0, all gates pass → exit 0.
 10.  Legacy concern (no "annotations" key) → treated as empty → exit 0.
 11.  Concern not registered → exit 5.
 12.  Package not registered → exit 5.
 13.  Multi-gate failure: banned phrase + ambiguous rate both fail → exit 2, both named.
 14.  Schema-corrupted confidence value → exit 5.
 15.  Cross-concern check with single-concern package → cross_concern_duplicate_count=0 → exit 0.
 16.  JSON output parseability — all 11 top-level keys present.

Infrastructure mirrors test_validate_annotation.py: subprocess invocations,
isolated TemporaryDirectory, DEVFORGE_DIR + DEVFORGE_PROJECT_ROOT env vars.

Stdlib only. Python 3.8+.
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
# Shared base class
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


def _compute_hash(path: Path, start: int, end: int) -> str:
    """Reproduce the setter's content_hash computation."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    joined = "\n".join(lines[start - 1:end])
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


class _VerifyAnnotationsBase(unittest.TestCase):
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

    def _write_state_direct(self, state):
        self.state_file.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _write_source(self, rel_path, lines):
        full = self.project_root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return full

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

    def _verify_annotations(self, package="apps/web", concern="auth"):
        return self._run(
            "verify-annotations",
            "--package", package,
            "--concern", concern,
        )

    def _setup_source_file(self, rel_path="src/auth/index.ts", line_count=5):
        """Write a source file with the given number of lines."""
        lines = ["line{0}".format(i + 1) for i in range(line_count)]
        return self._write_source(rel_path, lines)

    def _build_clean_annotations(
        self,
        n=5,
        package="apps/web",
        concern="auth",
        source_file="src/auth/index.ts",
    ):
        """Set up pkg + concern + source file + N clean extracted annotations."""
        self._init_pkg_concern(package=package, concern=concern)
        src_path = self._setup_source_file(source_file, line_count=max(n, 5))
        for i in range(n):
            target = "src/module_{0}/entry.ts".format(i)
            label = "Module {0} entry point".format(i)
            r = self._add_annotation(
                package=package,
                concern=concern,
                target_path=target,
                label=label,
                confidence="extracted",
                cite_file=source_file,
                cite_start=1,
                cite_end=1,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
        return src_path


# ---------------------------------------------------------------------------
# Test 1: Happy path
# ---------------------------------------------------------------------------


class HappyPathTest(_VerifyAnnotationsBase):

    def test_clean_annotations_exit_0(self):
        self._build_clean_annotations(n=5)
        r = self._verify_annotations()
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["total_annotations"], 5)
        self.assertEqual(report["banned_phrase_count"], 0)
        self.assertEqual(report["sibling_collision_count"], 0)
        self.assertEqual(report["missing_cite_count"], 0)
        self.assertEqual(report["cross_concern_duplicate_count"], 0)
        self.assertEqual(report["cross_concern_duplicate_rate"], 0.0)
        self.assertEqual(report["ambiguous_rate"], 0.0)
        self.assertEqual(report["confidence_distribution"]["extracted"], 5)
        self.assertEqual(report["confidence_distribution"]["inferred"], 0)
        self.assertEqual(report["confidence_distribution"]["ambiguous"], 0)
        self.assertEqual(report["gates"]["banned_phrase"], "pass")
        self.assertEqual(report["gates"]["ambiguous_rate"], "pass")
        self.assertEqual(report["gates"]["cross_concern_duplicate"], "pass")
        # Check distribution sums to total
        dist = report["confidence_distribution"]
        self.assertEqual(
            dist["extracted"] + dist["inferred"] + dist["ambiguous"],
            report["total_annotations"],
        )


# ---------------------------------------------------------------------------
# Test 2: Banned phrase present
# ---------------------------------------------------------------------------


class BannedPhraseTest(_VerifyAnnotationsBase):

    def test_banned_phrase_exit_2_with_gate_fail_in_stderr(self):
        self._init_pkg_concern()
        self._setup_source_file()
        # Add 4 clean annotations
        for i in range(4):
            r = self._add_annotation(
                target_path="src/clean_{0}.ts".format(i),
                label="Clean module {0}".format(i),
                confidence="extracted",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
        # Add 1 annotation with banned phrase — use state corruption since
        # add-annotation itself would block it. Actually add-annotation allows
        # banned phrases at set time (only validate-annotation gates them), so
        # we can use the CLI directly.
        r = self._add_annotation(
            target_path="src/bad.ts",
            label="handles the authentication flow",
            confidence="extracted",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._verify_annotations()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"banned_phrase gate FAIL", r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["banned_phrase_count"], 1)
        self.assertEqual(report["gates"]["banned_phrase"], "fail")


# ---------------------------------------------------------------------------
# Test 3: Sibling collision — reported but NOT gated
# ---------------------------------------------------------------------------


class SiblingCollisionNotGatedTest(_VerifyAnnotationsBase):

    def test_sibling_collision_reported_not_gated(self):
        """Two annotations under same parent dir with identical labels → collision
        counted in report but no hard gate → exit 0 (unless other gates fail)."""
        self._init_pkg_concern()
        self._setup_source_file()
        # Two annotations in the same parent dir (src/order/) with identical labels.
        r = self._add_annotation(
            target_path="src/order/header.ts",
            label="Order header component",
            confidence="extracted",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._add_annotation(
            target_path="src/order/footer.ts",
            label="Order header component",  # identical label → sibling collision
            confidence="extracted",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._verify_annotations()
        # NOT gated → exit 0 (other gates pass).
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        # Both annotations collide with each other, so count = 2.
        self.assertEqual(report["sibling_collision_count"], 2)
        # Gates still all pass.
        self.assertEqual(report["gates"]["banned_phrase"], "pass")
        self.assertEqual(report["gates"]["ambiguous_rate"], "pass")
        self.assertEqual(report["gates"]["cross_concern_duplicate"], "pass")


# ---------------------------------------------------------------------------
# Test 3b: sibling_collision_count counts cross-directory collisions
# ---------------------------------------------------------------------------


class SiblingCollisionCrossDirectoryTest(_VerifyAnnotationsBase):

    def test_sibling_collision_counts_across_directories(self):
        """sibling_collision_count must match validate-annotation's per-record
        semantics: ANY two annotations in the same concern with identical
        normalized labels collide, regardless of parent directory."""
        self._init_pkg_concern()
        self._setup_source_file()
        # Two annotations in DIFFERENT parent directories, identical labels.
        r = self._add_annotation(
            target_path="src/auth/login.ts",
            label="Login entry",
            confidence="extracted",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._add_annotation(
            target_path="src/payments/login.ts",
            label="Login entry",  # identical label, different parent dir
            confidence="extracted",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._verify_annotations()
        # Collision is reported but NOT gated → exit 0.
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        # Both annotations collide (concern-scoped, not dir-scoped): count = 2.
        # The OLD code (parent-dir filter) would have returned 0 here because
        # src/auth != src/payments. The new code returns 2.
        self.assertEqual(report["sibling_collision_count"], 2)
        # Gates still all pass (collision is diagnostic, not gated).
        self.assertEqual(report["gates"]["banned_phrase"], "pass")
        self.assertEqual(report["gates"]["ambiguous_rate"], "pass")
        self.assertEqual(report["gates"]["cross_concern_duplicate"], "pass")


# ---------------------------------------------------------------------------
# Test 4: Missing cite-file — reported, NOT gated
# ---------------------------------------------------------------------------


class MissingCiteNotGatedTest(_VerifyAnnotationsBase):

    def test_missing_cite_reported_not_gated(self):
        self._init_pkg_concern()
        self._setup_source_file()
        # Add 1 annotation with a cite-file that exists at add time.
        r = self._add_annotation(
            target_path="src/auth/index.ts",
            label="Authentication entry point",
            confidence="extracted",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        # Delete the source file after annotation was recorded.
        (self.project_root / "src" / "auth" / "index.ts").unlink()
        r = self._verify_annotations()
        # NOT gated — should still exit 0.
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["missing_cite_count"], 1)
        self.assertEqual(report["gates"]["banned_phrase"], "pass")
        self.assertEqual(report["gates"]["ambiguous_rate"], "pass")
        self.assertEqual(report["gates"]["cross_concern_duplicate"], "pass")


# ---------------------------------------------------------------------------
# Test 5: Ambiguous rate exactly 10% → pass
# ---------------------------------------------------------------------------


class AmbiguousRateAtThresholdTest(_VerifyAnnotationsBase):

    def test_ambiguous_rate_10_percent_passes(self):
        """10 annotations, 1 ambiguous = 10.0% = threshold → pass (<=)."""
        self._init_pkg_concern()
        self._setup_source_file()
        for i in range(9):
            r = self._add_annotation(
                target_path="src/mod_{0}.ts".format(i),
                label="Module {0} entry".format(i),
                confidence="extracted",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
        # 10th annotation: ambiguous.
        r = self._add_annotation(
            target_path="src/mod_9.ts",
            label="Module 9 entry",
            confidence="ambiguous",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._verify_annotations()
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertAlmostEqual(report["ambiguous_rate"], 0.10, places=9)
        self.assertEqual(report["gates"]["ambiguous_rate"], "pass")


# ---------------------------------------------------------------------------
# Test 6: Ambiguous rate 12% → fail
# ---------------------------------------------------------------------------


class AmbiguousRateAboveThresholdTest(_VerifyAnnotationsBase):

    def test_ambiguous_rate_above_10_percent_fails(self):
        """100 annotations, 12 ambiguous = 12% > 10% → gate fail."""
        self._init_pkg_concern()
        src = self._setup_source_file(line_count=100)
        # We need 100 distinct target_paths with clean labels.
        for i in range(88):
            r = self._add_annotation(
                target_path="src/m{0}/e.ts".format(i),
                label="Module {0} entry point".format(i),
                confidence="extracted",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
        for i in range(12):
            r = self._add_annotation(
                target_path="src/a{0}/e.ts".format(i),
                label="Ambiguous module {0}".format(i),
                confidence="ambiguous",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
        r = self._verify_annotations()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"ambiguous_rate gate FAIL", r.stderr)
        report = json.loads(r.stdout)
        self.assertAlmostEqual(report["ambiguous_rate"], 0.12, places=9)
        self.assertEqual(report["gates"]["ambiguous_rate"], "fail")


# ---------------------------------------------------------------------------
# Test 7: Cross-concern duplicates 5% → pass
# ---------------------------------------------------------------------------


class CrossConcernDuplicateAtThresholdTest(_VerifyAnnotationsBase):

    def test_cross_concern_duplicate_5_percent_passes(self):
        """20 annotations in C, 1 matches label in concern D → 5% → pass (<=)."""
        # Register package and two concerns.
        r = self._run("add-package", "--path", "apps/web", "--name", "web")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._run("add-concern", "--package", "apps/web", "--concern", "auth")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._run("add-concern", "--package", "apps/web", "--concern", "payments")
        self.assertEqual(r.returncode, 0, r.stderr)

        self._setup_source_file()

        # Add 20 annotations to concern "auth".
        for i in range(20):
            label = "Auth module {0}".format(i)
            r = self._add_annotation(
                concern="auth",
                target_path="src/auth/m{0}.ts".format(i),
                label=label,
            )
            self.assertEqual(r.returncode, 0, r.stderr)

        # Add 1 annotation to concern "payments" whose label matches auth/m0.
        r = self._add_annotation(
            concern="payments",
            target_path="src/pay/entry.ts",
            label="Auth module 0",  # matches auth concern annotation 0
        )
        self.assertEqual(r.returncode, 0, r.stderr)

        r = self._verify_annotations(concern="auth")
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["cross_concern_duplicate_count"], 1)
        self.assertAlmostEqual(report["cross_concern_duplicate_rate"], 1 / 20, places=9)
        self.assertEqual(report["gates"]["cross_concern_duplicate"], "pass")


# ---------------------------------------------------------------------------
# Test 8: Cross-concern duplicates 6% → fail
# ---------------------------------------------------------------------------


class CrossConcernDuplicateAboveThresholdTest(_VerifyAnnotationsBase):

    def test_cross_concern_duplicate_above_5_percent_fails(self):
        """10 annotations in C, 1 matches label in D → 10% > 5% → gate fail."""
        r = self._run("add-package", "--path", "apps/web", "--name", "web")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._run("add-concern", "--package", "apps/web", "--concern", "auth")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._run("add-concern", "--package", "apps/web", "--concern", "payments")
        self.assertEqual(r.returncode, 0, r.stderr)

        self._setup_source_file()

        for i in range(10):
            r = self._add_annotation(
                concern="auth",
                target_path="src/auth/m{0}.ts".format(i),
                label="Auth component {0}".format(i),
            )
            self.assertEqual(r.returncode, 0, r.stderr)

        # 1 annotation in payments matches auth concern label → 10% > 5%.
        r = self._add_annotation(
            concern="payments",
            target_path="src/pay/entry.ts",
            label="Auth component 0",
        )
        self.assertEqual(r.returncode, 0, r.stderr)

        r = self._verify_annotations(concern="auth")
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"cross_concern_duplicate gate FAIL", r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["cross_concern_duplicate_count"], 1)
        self.assertEqual(report["gates"]["cross_concern_duplicate"], "fail")


# ---------------------------------------------------------------------------
# Test 9: Empty annotations dict
# ---------------------------------------------------------------------------


class EmptyAnnotationsTest(_VerifyAnnotationsBase):

    def test_empty_annotations_exit_0_all_zero(self):
        """Concern exists but has zero annotations → all rates 0.0, all gates pass."""
        self._init_pkg_concern()
        r = self._verify_annotations()
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["total_annotations"], 0)
        self.assertEqual(report["banned_phrase_count"], 0)
        self.assertEqual(report["sibling_collision_count"], 0)
        self.assertEqual(report["missing_cite_count"], 0)
        self.assertEqual(report["ambiguous_rate"], 0.0)
        self.assertEqual(report["cross_concern_duplicate_count"], 0)
        self.assertEqual(report["cross_concern_duplicate_rate"], 0.0)
        self.assertEqual(report["gates"]["banned_phrase"], "pass")
        self.assertEqual(report["gates"]["ambiguous_rate"], "pass")
        self.assertEqual(report["gates"]["cross_concern_duplicate"], "pass")


# ---------------------------------------------------------------------------
# Test 10: Legacy concern (no "annotations" key)
# ---------------------------------------------------------------------------


class LegacyConcernNoAnnotationsKeyTest(_VerifyAnnotationsBase):

    def test_legacy_concern_treated_as_empty(self):
        """Concern record missing 'annotations' key → treated as {} → exit 0."""
        self._init_pkg_concern()
        # Remove the 'annotations' key from state directly.
        state = self._read_state()
        concern = state["packages"]["apps/web"]["concerns"]["auth"]
        concern.pop("annotations", None)
        self._write_state_direct(state)

        r = self._verify_annotations()
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["total_annotations"], 0)
        self.assertEqual(report["ambiguous_rate"], 0.0)


# ---------------------------------------------------------------------------
# Test 11: Concern not registered
# ---------------------------------------------------------------------------


class ConcernNotRegisteredTest(_VerifyAnnotationsBase):

    def test_concern_not_registered_exit_5(self):
        self._run("add-package", "--path", "apps/web", "--name", "web")
        # No concern "ghost" added.
        r = self._verify_annotations(concern="ghost")
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertIn(b"concern not registered", r.stderr)


# ---------------------------------------------------------------------------
# Test 12: Package not registered
# ---------------------------------------------------------------------------


class PackageNotRegisteredTest(_VerifyAnnotationsBase):

    def test_package_not_registered_exit_5(self):
        r = self._verify_annotations(package="apps/ghost", concern="auth")
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertIn(b"package not registered", r.stderr)


# ---------------------------------------------------------------------------
# Test 13: Multi-gate failure — both banned phrase AND ambiguous rate fail
# ---------------------------------------------------------------------------


class MultiGateFailureTest(_VerifyAnnotationsBase):

    def test_both_banned_phrase_and_ambiguous_rate_fail(self):
        """When two gates fail simultaneously, both are named in stderr, exit 2."""
        self._init_pkg_concern()
        self._setup_source_file()

        # Add 9 clean extracted annotations.
        for i in range(9):
            r = self._add_annotation(
                target_path="src/m{0}.ts".format(i),
                label="Clean module {0}".format(i),
                confidence="extracted",
            )
            self.assertEqual(r.returncode, 0, r.stderr)

        # Add 1 ambiguous annotation with a banned phrase — both gates fail.
        # (9 + 1 = 10 total, 1 ambiguous = 10% = threshold → does NOT fail alone.
        # Need >10%, so add 2 ambiguous out of 10 total = 20%.)
        r = self._add_annotation(
            target_path="src/ambiguous.ts",
            label="handles ambiguous logic",  # banned phrase "handles"
            confidence="ambiguous",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        # Add another ambiguous to push rate above 10%.
        r = self._add_annotation(
            target_path="src/ambiguous2.ts",
            label="Ambiguous secondary module",
            confidence="ambiguous",
        )
        self.assertEqual(r.returncode, 0, r.stderr)

        r = self._verify_annotations()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"banned_phrase gate FAIL", r.stderr)
        self.assertIn(b"ambiguous_rate gate FAIL", r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["gates"]["banned_phrase"], "fail")
        self.assertEqual(report["gates"]["ambiguous_rate"], "fail")


# ---------------------------------------------------------------------------
# Test 14: Schema-corrupted confidence value → exit 5
# ---------------------------------------------------------------------------


class CorruptConfidenceValueTest(_VerifyAnnotationsBase):

    def test_unknown_confidence_value_exit_5(self):
        """An annotation with a non-enum confidence value triggers exit 5 (state error)."""
        self._init_pkg_concern()
        self._setup_source_file()
        r = self._add_annotation(
            target_path="src/auth/index.ts",
            label="Authentication entry point",
            confidence="extracted",
        )
        self.assertEqual(r.returncode, 0, r.stderr)

        # Corrupt the confidence value directly in state.
        state = self._read_state()
        ann = state["packages"]["apps/web"]["concerns"]["auth"]["annotations"][
            "src/auth/index.ts"
        ]
        ann["confidence"] = "unknown"
        self._write_state_direct(state)

        r = self._verify_annotations()
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertIn(b"state-corrupt", r.stderr)


# ---------------------------------------------------------------------------
# Test 15: Single-concern package → cross_concern_duplicate_count = 0
# ---------------------------------------------------------------------------


class SingleConcernPackageTest(_VerifyAnnotationsBase):

    def test_single_concern_cross_concern_duplicate_zero(self):
        """Package has only one concern → no other concerns to compare against
        → cross_concern_duplicate_count = 0 trivially → exit 0."""
        self._init_pkg_concern()
        self._setup_source_file()
        r = self._add_annotation(
            target_path="src/auth/index.ts",
            label="Authentication entry point",
            confidence="extracted",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._verify_annotations()
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["cross_concern_duplicate_count"], 0)
        self.assertEqual(report["cross_concern_duplicate_rate"], 0.0)
        self.assertEqual(report["gates"]["cross_concern_duplicate"], "pass")


# ---------------------------------------------------------------------------
# Test 16: JSON output parseability — all 11 top-level keys present
# ---------------------------------------------------------------------------


class JsonOutputParseabilityTest(_VerifyAnnotationsBase):

    def test_all_top_level_keys_present(self):
        """Parse stdout through json.loads; assert all 11 required keys exist."""
        self._build_clean_annotations(n=3)
        r = self._verify_annotations()
        self.assertEqual(r.returncode, 0, r.stderr)

        report = json.loads(r.stdout)
        expected_keys = {
            "ambiguous_rate",
            "banned_phrase_count",
            "concern",
            "confidence_distribution",
            "cross_concern_duplicate_count",
            "cross_concern_duplicate_rate",
            "gates",
            "missing_cite_count",
            "package",
            "sibling_collision_count",
            "total_annotations",
        }
        self.assertEqual(set(report.keys()), expected_keys)
        # Also check gates sub-keys — vacuous_pass is now the 4th gate.
        expected_gate_keys = {
            "ambiguous_rate",
            "banned_phrase",
            "cross_concern_duplicate",
            "vacuous_pass",
        }
        self.assertEqual(set(report["gates"].keys()), expected_gate_keys)
        # And confidence_distribution sub-keys.
        expected_conf_keys = {"ambiguous", "extracted", "inferred"}
        self.assertEqual(set(report["confidence_distribution"].keys()), expected_conf_keys)


# ---------------------------------------------------------------------------
# Fix A tests (Tests 1-5 of vacuous_pass gate).
# ---------------------------------------------------------------------------


class VacuousPassGateFailWhenTreeSetZeroAnnotations(_VerifyAnnotationsBase):
    """Test 1: Tree set to non-empty string + zero annotations → vacuous_pass FAIL."""

    def test_vacuous_pass_gate_fail_when_tree_set_zero_annotations(self):
        self._init_pkg_concern()
        # Set the directory_tree via state injection (set-concern-tree may
        # be called but no annotations added).
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        state["packages"]["apps/web"]["concerns"]["auth"]["directory_tree"] = (
            "auth/\n├── login.ts\n└── session.ts"
        )
        self._write_state_direct(state)

        r = self._verify_annotations()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"vacuous_pass gate FAIL", r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["gates"]["vacuous_pass"], "fail")


class VacuousPassGatePassWhenTreeUnset(_VerifyAnnotationsBase):
    """Test 2: No directory_tree set + zero annotations → vacuous_pass PASS."""

    def test_vacuous_pass_gate_pass_when_tree_unset(self):
        self._init_pkg_concern()
        # No tree set — directory_tree is None by default.
        r = self._verify_annotations()
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["gates"]["vacuous_pass"], "pass")


class VacuousPassGatePassWhenAnnotationsPresent(_VerifyAnnotationsBase):
    """Test 3: Non-empty tree + at least one annotation → vacuous_pass PASS."""

    def test_vacuous_pass_gate_pass_when_annotations_present(self):
        self._build_clean_annotations(n=3)
        # Inject a directory_tree value.
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        state["packages"]["apps/web"]["concerns"]["auth"]["directory_tree"] = (
            "auth/\n├── file1.ts\n└── file2.ts"
        )
        self._write_state_direct(state)

        r = self._verify_annotations()
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["gates"]["vacuous_pass"], "pass")


class VacuousPassGateInJsonReport(_VerifyAnnotationsBase):
    """Test 4: JSON report includes gates.vacuous_pass key for ALL invocations."""

    def test_vacuous_pass_gate_in_json_report(self):
        # Case A: zero annotations, no tree → should include the key with "pass".
        self._init_pkg_concern()
        r = self._verify_annotations()
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertIn("vacuous_pass", report["gates"])
        self.assertEqual(report["gates"]["vacuous_pass"], "pass")

        # Case B: with annotations (add without re-initializing pkg/concern).
        self._setup_source_file()
        r = self._add_annotation(
            target_path="src/auth/a.ts",
            label="Auth entry point",
            confidence="extracted",
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._verify_annotations()
        report = json.loads(r.stdout)
        self.assertIn("vacuous_pass", report["gates"])


class MultiGateWithVacuousPassFailsIndependently(_VerifyAnnotationsBase):
    """Test 5: vacuous_pass fails independently of the rate-based gates.

    The four gates (banned_phrase, ambiguous_rate, cross_concern_duplicate,
    vacuous_pass) evaluate independently: vacuous_pass fires when tree is set
    and total_annotations == 0; the rate-based gates all produce rate=0.0
    when there are no annotations (trivially pass). This confirms vacuous_pass
    fails alone without suppressing other gate results or being suppressed by
    them, and exit code is 2 because at least one gate fails.

    Note: banned_phrase, ambiguous_rate, and cross_concern_duplicate cannot
    simultaneously fail with vacuous_pass in a single invocation (they require
    annotations; vacuous_pass requires zero annotations). This test verifies
    the independent failure path and that stderr names the failing gate.
    """

    def test_multi_gate_with_vacuous_pass_fails_independently(self):
        self._init_pkg_concern()
        # Set the tree (triggers vacuous_pass gate check) + keep zero annotations.
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        state["packages"]["apps/web"]["concerns"]["auth"]["directory_tree"] = (
            "auth/\n├── login.ts\n└── session.ts"
        )
        self._write_state_direct(state)

        r = self._verify_annotations()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"vacuous_pass gate FAIL", r.stderr)
        # Only vacuous_pass fails; rate-based gates pass (no annotations → 0/0).
        report = json.loads(r.stdout)
        self.assertEqual(report["gates"]["vacuous_pass"], "fail")
        self.assertEqual(report["gates"]["banned_phrase"], "pass")
        self.assertEqual(report["gates"]["ambiguous_rate"], "pass")
        self.assertEqual(report["gates"]["cross_concern_duplicate"], "pass")
        self.assertEqual(report["total_annotations"], 0)


if __name__ == "__main__":
    unittest.main()
