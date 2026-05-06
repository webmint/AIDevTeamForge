"""Tests for `verify-file-docs` post-batch aggregator (Step B.4 of
VALIDATOR-LOOP-B-PLAN.md).

Exit-code contract under test:
  0 — all gates pass
  2 — at least one gate failed
  5 — state error (package not registered, concern not registered,
      front-matter parse error in any filled md, or state-corrupt
      confidence value)

Gate thresholds (locked):
  banned_phrase   : 0 tolerated
  ambiguous_rate  : <= 10%
  cross_concern_duplicate : <= 5%
  vacuous_pass    : tree-set + zero filled mds → fail

Metrics reported but NOT gated:
  sibling_collision_count  — diagnostic only
  missing_cite_count       — diagnostic only

18 test cases (17 plan-required + 1 bonus):
  1.  Happy path: 5 mds, all extracted/inferred, no banned phrases, all
      cites resolve → all gates pass, exit 0, total_md_files=5.
  2.  Banned phrase fires: one md with label "handles auth flow" → gate_banned fail,
      exit 2.
  3.  Ambiguous rate fires: 12 mds, 2 ambiguous (rate=16.7%>10%) → gate_ambiguous
      fail, exit 2.
  4.  Cross-concern duplicate fires: concern B has 1 md with same label as concern A's
      1 md (out of 10 in B) → cross_dup_rate=10%>5% → gate_cross fail.
  5.  Vacuous pass fires: directory_tree set in state, docs/<P>/<C>/ empty → fail.
  6.  Vacuous pass exempt: directory_tree NOT set, docs/<P>/<C>/ empty → pass.
  7.  Sibling collision counted but NOT gated: 2 mds with same label →
      sibling_collision_count=2, all gates still pass.
  8.  Missing cite counted but NOT gated: 1 md evidence_file pointing at
      non-existent path → missing_cite_count=1, no exit 2 from this alone.
  9.  Empty skeleton ignored: 3 mds total, 1 is zero-byte → total_md_files=2.
  10. Front-matter parse error: malformed .md → exit 5 with parse error message.
  11. State-corrupt confidence: md with confidence=bogus → exit 5.
  12. Package not registered: --package nope → exit 5.
  13. Concern not registered: --concern nope → exit 5.
  14. Threshold boundary — ambiguous exactly at 10%: 10 mds, 1 ambiguous →
      rate=10%, gate_ambiguous pass.
  15. Threshold boundary — ambiguous just over 10%: 9 mds, 1 ambiguous →
      rate≈11.1%, gate_ambiguous fail.
  16. Cross-concern boundary: 20 mds, 1 cross-dup → rate=5%, gate_cross pass.
  17. Empty docs dir (no directory): directory_tree NOT set, docs/<P>/<C>/ doesn't
      exist → total_md_files=0, gate_vacuous pass, exit 0.
  18. JSON report key completeness (bonus): all top-level keys + gate sub-keys +
      confidence_distribution keys match the locked report shape.

Infrastructure: subprocess invocations, isolated TemporaryDirectory,
DEVFORGE_DIR + DEVFORGE_PROJECT_ROOT env vars. Real `write-file-doc` CLI
produces happy-path fixtures; hand-crafted frontmatter for error paths.

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


def _compute_hash(path: Path, start: int, end: int) -> str:
    """Reproduce the write-file-doc content_hash computation."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    joined = "\n".join(lines[start - 1:end])
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class _VerifyFileDocsBase(unittest.TestCase):
    """Isolated tmp dir + shared setup helpers."""

    DEFAULT_PACKAGE = "apps/web"
    DEFAULT_CONCERN = "auth"

    def setUp(self):
        self._saved_devforge = os.environ.pop("DEVFORGE_DIR", None)
        self._saved_root = os.environ.pop("DEVFORGE_PROJECT_ROOT", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.project_root = Path(self._tmp.name)
        self.devforge_dir = self.project_root / ".devforge"
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.devforge_dir / gdh.STATE_FILE_NAME

        # Default source file used as cite target by most tests.
        src_dir = self.project_root / "src" / "auth"
        src_dir.mkdir(parents=True, exist_ok=True)
        self._src_file = src_dir / "index.ts"
        self._src_file.write_text(
            "\n".join("line{0}".format(i + 1) for i in range(20)) + "\n",
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

    def _read_state(self):
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def _write_state_direct(self, state):
        self.state_file.write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _init_pkg_concern(self, package=None, concern=None, name="web"):
        package = package or self.DEFAULT_PACKAGE
        concern = concern or self.DEFAULT_CONCERN
        r = self._run("add-package", "--path", package, "--name", name)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._run("add-concern", "--package", package, "--concern", concern)
        self.assertEqual(r.returncode, 0, r.stderr)

    def _docs_dir(self, package=None, concern=None):
        package = package or self.DEFAULT_PACKAGE
        concern = concern or self.DEFAULT_CONCERN
        return self.project_root / "docs" / package / concern

    def _write_file_doc(
        self,
        md_path,
        label="Auth entry point",
        confidence="extracted",
        cite_file=None,
        cite_start=1,
        cite_end=3,
        model_version="claude-haiku-4-5-20251001",
    ):
        """Call write-file-doc via CLI. Returns subprocess result."""
        cite_file = cite_file or str(self._src_file.relative_to(self.project_root))
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

    def _verify_file_docs(self, package=None, concern=None):
        package = package or self.DEFAULT_PACKAGE
        concern = concern or self.DEFAULT_CONCERN
        return self._run(
            "verify-file-docs",
            "--package", package,
            "--concern", concern,
        )

    def _build_clean_mds(self, n=5, package=None, concern=None):
        """Init pkg+concern, write N clean extracted mds, return docs dir path."""
        package = package or self.DEFAULT_PACKAGE
        concern = concern or self.DEFAULT_CONCERN
        self._init_pkg_concern(package=package, concern=concern)
        docs_dir = self._docs_dir(package=package, concern=concern)
        docs_dir.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            md = docs_dir / "module_{0}.ts.md".format(i)
            r = self._write_file_doc(
                md,
                label="Module {0} entry point".format(i),
                confidence="extracted",
            )
            self.assertEqual(r.returncode, 0, r.stderr)
        return docs_dir

    def _hand_craft_md(self, md_path, label, confidence, cite_file_rel=None):
        """Write a hand-crafted .md with valid frontmatter using real hash."""
        cite_file_rel = cite_file_rel or str(
            self._src_file.relative_to(self.project_root)
        )
        cite_path = self.project_root / cite_file_rel
        content_hash = _compute_hash(cite_path, 1, 3)
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(
            "---\n"
            'label: "{label}"\n'
            "confidence: {confidence}\n"
            'evidence_file: "{cite_file}"\n'
            "evidence_start: 1\n"
            "evidence_end: 3\n"
            'content_hash: "{hash}"\n'
            'model_version: "claude-haiku-4-5-20251001"\n'
            "---\n\n"
            "# {name}\n".format(
                label=label,
                confidence=confidence,
                cite_file=cite_file_rel,
                hash=content_hash,
                name=md_path.stem,
            ),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Test 1: Happy path
# ---------------------------------------------------------------------------


class HappyPathTest(_VerifyFileDocsBase):

    def test_clean_mds_exit_0(self):
        self._build_clean_mds(n=5)
        r = self._verify_file_docs()
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["total_md_files"], 5)
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
        self.assertEqual(report["gates"]["vacuous_pass"], "pass")
        dist = report["confidence_distribution"]
        self.assertEqual(
            dist["extracted"] + dist["inferred"] + dist["ambiguous"],
            report["total_md_files"],
        )


# ---------------------------------------------------------------------------
# Test 2: Banned phrase fires
# ---------------------------------------------------------------------------


class BannedPhraseTest(_VerifyFileDocsBase):

    def test_banned_phrase_gate_fail_exit_2(self):
        self._init_pkg_concern()
        docs_dir = self._docs_dir()
        docs_dir.mkdir(parents=True, exist_ok=True)
        # 4 clean mds.
        for i in range(4):
            md = docs_dir / "clean_{0}.ts.md".format(i)
            r = self._write_file_doc(md, label="Clean module {0}".format(i))
            self.assertEqual(r.returncode, 0, r.stderr)
        # 1 md with a banned phrase ("handles").
        banned_md = docs_dir / "bad.ts.md"
        self._hand_craft_md(banned_md, label="handles auth flow", confidence="extracted")

        r = self._verify_file_docs()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"banned_phrase gate FAIL", r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["banned_phrase_count"], 1)
        self.assertEqual(report["gates"]["banned_phrase"], "fail")


# ---------------------------------------------------------------------------
# Test 3: Ambiguous rate fires (12 mds, 2 ambiguous = 16.7% > 10%)
# ---------------------------------------------------------------------------


class AmbiguousRateAboveThresholdTest(_VerifyFileDocsBase):

    def test_ambiguous_rate_above_10_percent_fails(self):
        self._init_pkg_concern()
        docs_dir = self._docs_dir()
        docs_dir.mkdir(parents=True, exist_ok=True)
        for i in range(10):
            md = docs_dir / "clean_{0}.ts.md".format(i)
            r = self._write_file_doc(md, label="Clean module {0}".format(i))
            self.assertEqual(r.returncode, 0, r.stderr)
        for i in range(2):
            md = docs_dir / "ambig_{0}.ts.md".format(i)
            r = self._write_file_doc(
                md, label="Ambiguous module {0}".format(i), confidence="ambiguous"
            )
            self.assertEqual(r.returncode, 0, r.stderr)

        r = self._verify_file_docs()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"ambiguous_rate gate FAIL", r.stderr)
        report = json.loads(r.stdout)
        self.assertAlmostEqual(report["ambiguous_rate"], 2 / 12, places=9)
        self.assertEqual(report["gates"]["ambiguous_rate"], "fail")
        self.assertEqual(report["total_md_files"], 12)


# ---------------------------------------------------------------------------
# Test 4: Cross-concern duplicate fires
# ---------------------------------------------------------------------------


class CrossConcernDuplicateAboveThresholdTest(_VerifyFileDocsBase):

    def test_cross_concern_duplicate_above_5_percent_fails(self):
        """Concern B has 10 mds, 1 with same label as concern A's 1 md → 10% > 5%."""
        # Register package + both concerns.
        r = self._run("add-package", "--path", "apps/web", "--name", "web")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._run("add-concern", "--package", "apps/web", "--concern", "auth")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._run("add-concern", "--package", "apps/web", "--concern", "payments")
        self.assertEqual(r.returncode, 0, r.stderr)

        # Write 1 md for concern A (auth).
        auth_docs = self.project_root / "docs" / "apps/web" / "auth"
        auth_docs.mkdir(parents=True, exist_ok=True)
        self._hand_craft_md(auth_docs / "login.ts.md", label="Login entry", confidence="extracted")

        # Write 10 mds for concern B (payments), 1 sharing label with concern A.
        pay_docs = self.project_root / "docs" / "apps/web" / "payments"
        pay_docs.mkdir(parents=True, exist_ok=True)
        self._hand_craft_md(pay_docs / "login.ts.md", label="Login entry", confidence="extracted")
        for i in range(9):
            md = pay_docs / "pay_{0}.ts.md".format(i)
            r = self._write_file_doc(
                md, label="Payment module {0}".format(i)
            )
            self.assertEqual(r.returncode, 0, r.stderr)

        # Verify payments concern → cross_dup_rate = 1/10 = 10% > 5%.
        r = self._run(
            "verify-file-docs",
            "--package", "apps/web",
            "--concern", "payments",
        )
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"cross_concern_duplicate gate FAIL", r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["cross_concern_duplicate_count"], 1)
        self.assertAlmostEqual(report["cross_concern_duplicate_rate"], 1 / 10, places=9)
        self.assertEqual(report["gates"]["cross_concern_duplicate"], "fail")


# ---------------------------------------------------------------------------
# Test 5: Vacuous pass fires (tree set, docs dir empty)
# ---------------------------------------------------------------------------


class VacuousPassFiresWhenTreeSetEmptyDirTest(_VerifyFileDocsBase):

    def test_vacuous_pass_gate_fail_when_tree_set_zero_filled_mds(self):
        self._init_pkg_concern()
        # Set directory_tree in state.
        state = self._read_state()
        state["packages"]["apps/web"]["concerns"]["auth"]["directory_tree"] = (
            "auth/\n├── login.ts\n└── session.ts"
        )
        self._write_state_direct(state)
        # docs dir exists but contains no filled mds (dir not created = zero).

        r = self._verify_file_docs()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn(b"vacuous_pass gate FAIL", r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["gates"]["vacuous_pass"], "fail")
        self.assertEqual(report["total_md_files"], 0)


# ---------------------------------------------------------------------------
# Test 6: Vacuous pass exempt (tree NOT set, docs dir empty)
# ---------------------------------------------------------------------------


class VacuousPassExemptWhenTreeUnsetTest(_VerifyFileDocsBase):

    def test_vacuous_pass_gate_pass_when_tree_unset_empty_dir(self):
        self._init_pkg_concern()
        # No directory_tree set, no docs dir created.
        r = self._verify_file_docs()
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["gates"]["vacuous_pass"], "pass")
        self.assertEqual(report["total_md_files"], 0)


# ---------------------------------------------------------------------------
# Test 7: Sibling collision counted but NOT gated
# ---------------------------------------------------------------------------


class SiblingCollisionNotGatedTest(_VerifyFileDocsBase):

    def test_sibling_collision_counted_not_gated(self):
        self._init_pkg_concern()
        docs_dir = self._docs_dir()
        docs_dir.mkdir(parents=True, exist_ok=True)
        # Two mds with identical labels.
        self._hand_craft_md(docs_dir / "a.ts.md", label="Duplicate label", confidence="extracted")
        self._hand_craft_md(docs_dir / "b.ts.md", label="Duplicate label", confidence="extracted")

        r = self._verify_file_docs()
        # Collision is diagnostic, not gated → exit 0 (other gates pass).
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        # Both mds collide with each other: count = 2.
        self.assertEqual(report["sibling_collision_count"], 2)
        # All gates pass.
        self.assertEqual(report["gates"]["banned_phrase"], "pass")
        self.assertEqual(report["gates"]["ambiguous_rate"], "pass")
        self.assertEqual(report["gates"]["cross_concern_duplicate"], "pass")
        self.assertEqual(report["gates"]["vacuous_pass"], "pass")


# ---------------------------------------------------------------------------
# Test 8: Missing cite counted but NOT gated
# ---------------------------------------------------------------------------


class MissingCiteNotGatedTest(_VerifyFileDocsBase):

    def test_missing_cite_counted_not_gated(self):
        self._init_pkg_concern()
        docs_dir = self._docs_dir()
        docs_dir.mkdir(parents=True, exist_ok=True)
        md = docs_dir / "entry.ts.md"
        r = self._write_file_doc(md, label="Auth entry")
        self.assertEqual(r.returncode, 0, r.stderr)
        # Delete the cite target.
        self._src_file.unlink()

        r = self._verify_file_docs()
        # Missing cite is diagnostic only → exit 0.
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["missing_cite_count"], 1)
        self.assertEqual(report["gates"]["banned_phrase"], "pass")


# ---------------------------------------------------------------------------
# Test 9: Empty skeleton ignored (zero-byte file skipped from total)
# ---------------------------------------------------------------------------


class EmptySkeletonIgnoredTest(_VerifyFileDocsBase):

    def test_zero_byte_md_skipped_from_total(self):
        self._init_pkg_concern()
        docs_dir = self._docs_dir()
        docs_dir.mkdir(parents=True, exist_ok=True)
        # 2 filled mds.
        for i in range(2):
            md = docs_dir / "filled_{0}.ts.md".format(i)
            r = self._write_file_doc(md, label="Filled module {0}".format(i))
            self.assertEqual(r.returncode, 0, r.stderr)
        # 1 zero-byte skeleton.
        (docs_dir / "skeleton.ts.md").write_bytes(b"")

        r = self._verify_file_docs()
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        # Only 2 filled mds counted; skeleton excluded.
        self.assertEqual(report["total_md_files"], 2)


# ---------------------------------------------------------------------------
# Test 10: Front-matter parse error → exit 5
# ---------------------------------------------------------------------------


class FrontmatterParseErrorTest(_VerifyFileDocsBase):

    def test_malformed_md_parse_error_exit_5(self):
        self._init_pkg_concern()
        docs_dir = self._docs_dir()
        docs_dir.mkdir(parents=True, exist_ok=True)
        # Write a malformed md (no closing fence).
        bad_md = docs_dir / "bad.ts.md"
        bad_md.write_text(
            "---\nlabel: \"Broken frontmatter\"\n# no closing fence\n",
            encoding="utf-8",
        )

        r = self._verify_file_docs()
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertIn(b"file-doc parse error", r.stderr)
        self.assertIn(b"bad.ts.md", r.stderr)


# ---------------------------------------------------------------------------
# Test 11: State-corrupt confidence → exit 5
# ---------------------------------------------------------------------------


class CorruptConfidenceTest(_VerifyFileDocsBase):

    def test_unknown_confidence_in_md_exit_5(self):
        self._init_pkg_concern()
        docs_dir = self._docs_dir()
        docs_dir.mkdir(parents=True, exist_ok=True)
        # Write md with bogus confidence directly.
        bad_md = docs_dir / "corrupt.ts.md"
        cite_rel = str(self._src_file.relative_to(self.project_root))
        content_hash = _compute_hash(self._src_file, 1, 3)
        bad_md.write_text(
            "---\n"
            'label: "Some label"\n'
            "confidence: bogus\n"
            'evidence_file: "{cite}"\n'
            "evidence_start: 1\n"
            "evidence_end: 3\n"
            'content_hash: "{hash}"\n'
            'model_version: "claude-haiku-4-5-20251001"\n'
            "---\n\n# corrupt.ts\n".format(cite=cite_rel, hash=content_hash),
            encoding="utf-8",
        )

        r = self._verify_file_docs()
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertIn(b"state-corrupt confidence value", r.stderr)


# ---------------------------------------------------------------------------
# Test 12: Package not registered → exit 5
# ---------------------------------------------------------------------------


class PackageNotRegisteredTest(_VerifyFileDocsBase):

    def test_package_not_registered_exit_5(self):
        r = self._run(
            "verify-file-docs", "--package", "apps/nope", "--concern", "auth"
        )
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertIn(b"package not registered", r.stderr)


# ---------------------------------------------------------------------------
# Test 13: Concern not registered → exit 5
# ---------------------------------------------------------------------------


class ConcernNotRegisteredTest(_VerifyFileDocsBase):

    def test_concern_not_registered_exit_5(self):
        r = self._run("add-package", "--path", "apps/web", "--name", "web")
        self.assertEqual(r.returncode, 0, r.stderr)
        # No concern added.
        r = self._run(
            "verify-file-docs", "--package", "apps/web", "--concern", "ghost"
        )
        self.assertEqual(r.returncode, 5, r.stderr)
        self.assertIn(b"concern not registered", r.stderr)


# ---------------------------------------------------------------------------
# Test 14: Threshold boundary — ambiguous exactly 10% (should PASS)
# ---------------------------------------------------------------------------


class AmbiguousRateAtThresholdPassTest(_VerifyFileDocsBase):

    def test_ambiguous_rate_10_percent_passes(self):
        """10 mds, 1 ambiguous = 10.0% = threshold → gate_ambiguous pass (≤)."""
        self._init_pkg_concern()
        docs_dir = self._docs_dir()
        docs_dir.mkdir(parents=True, exist_ok=True)
        for i in range(9):
            md = docs_dir / "clean_{0}.ts.md".format(i)
            r = self._write_file_doc(md, label="Clean module {0}".format(i))
            self.assertEqual(r.returncode, 0, r.stderr)
        md_amb = docs_dir / "ambig.ts.md"
        r = self._write_file_doc(md_amb, label="Ambiguous module 9", confidence="ambiguous")
        self.assertEqual(r.returncode, 0, r.stderr)

        r = self._verify_file_docs()
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertAlmostEqual(report["ambiguous_rate"], 0.10, places=9)
        self.assertEqual(report["gates"]["ambiguous_rate"], "pass")


# ---------------------------------------------------------------------------
# Test 15: Threshold boundary — ambiguous just over 10% (should FAIL)
# ---------------------------------------------------------------------------


class AmbiguousRateJustOverThresholdFailTest(_VerifyFileDocsBase):

    def test_ambiguous_rate_just_over_10_percent_fails(self):
        """9 mds, 1 ambiguous = 1/9 ≈ 11.1% > 10% → gate_ambiguous fail."""
        self._init_pkg_concern()
        docs_dir = self._docs_dir()
        docs_dir.mkdir(parents=True, exist_ok=True)
        for i in range(8):
            md = docs_dir / "clean_{0}.ts.md".format(i)
            r = self._write_file_doc(md, label="Clean module {0}".format(i))
            self.assertEqual(r.returncode, 0, r.stderr)
        md_amb = docs_dir / "ambig.ts.md"
        r = self._write_file_doc(md_amb, label="Ambiguous module 8", confidence="ambiguous")
        self.assertEqual(r.returncode, 0, r.stderr)

        r = self._verify_file_docs()
        self.assertEqual(r.returncode, 2, r.stderr)
        report = json.loads(r.stdout)
        self.assertAlmostEqual(report["ambiguous_rate"], 1 / 9, places=9)
        self.assertEqual(report["gates"]["ambiguous_rate"], "fail")


# ---------------------------------------------------------------------------
# Test 16: Cross-concern boundary — exactly 5% (should PASS)
# ---------------------------------------------------------------------------


class CrossConcernAtThresholdPassTest(_VerifyFileDocsBase):

    def test_cross_concern_duplicate_5_percent_passes(self):
        """20 mds in concern B, 1 with same label as concern A → 5% → pass (≤)."""
        r = self._run("add-package", "--path", "apps/web", "--name", "web")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._run("add-concern", "--package", "apps/web", "--concern", "auth")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self._run("add-concern", "--package", "apps/web", "--concern", "payments")
        self.assertEqual(r.returncode, 0, r.stderr)

        auth_docs = self.project_root / "docs" / "apps/web" / "auth"
        auth_docs.mkdir(parents=True, exist_ok=True)
        self._hand_craft_md(auth_docs / "login.ts.md", label="Login entry", confidence="extracted")

        pay_docs = self.project_root / "docs" / "apps/web" / "payments"
        pay_docs.mkdir(parents=True, exist_ok=True)
        # 1 md matching auth's label.
        self._hand_craft_md(pay_docs / "login.ts.md", label="Login entry", confidence="extracted")
        # 19 unique mds.
        for i in range(19):
            md = pay_docs / "pay_{0}.ts.md".format(i)
            r = self._write_file_doc(md, label="Payment module {0}".format(i))
            self.assertEqual(r.returncode, 0, r.stderr)

        # Verify payments: 1/20 = 5.0% ≤ 5% → pass.
        r = self._run(
            "verify-file-docs", "--package", "apps/web", "--concern", "payments"
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["cross_concern_duplicate_count"], 1)
        self.assertAlmostEqual(report["cross_concern_duplicate_rate"], 1 / 20, places=9)
        self.assertEqual(report["gates"]["cross_concern_duplicate"], "pass")


# ---------------------------------------------------------------------------
# Test 17: Empty docs dir (directory doesn't exist) → exit 0, total=0
# ---------------------------------------------------------------------------


class EmptyDocsDirNonExistentTest(_VerifyFileDocsBase):

    def test_nonexistent_docs_dir_exit_0_total_zero(self):
        """docs/<P>/<C>/ does not exist + no directory_tree → all gates pass."""
        self._init_pkg_concern()
        # Docs dir never created; no tree set.
        r = self._verify_file_docs()
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads(r.stdout)
        self.assertEqual(report["total_md_files"], 0)
        self.assertEqual(report["gates"]["vacuous_pass"], "pass")
        self.assertEqual(report["gates"]["banned_phrase"], "pass")
        self.assertEqual(report["gates"]["ambiguous_rate"], "pass")
        self.assertEqual(report["gates"]["cross_concern_duplicate"], "pass")
        self.assertEqual(report["ambiguous_rate"], 0.0)
        self.assertEqual(report["cross_concern_duplicate_rate"], 0.0)
        self.assertEqual(report["banned_phrase_count"], 0)
        self.assertEqual(report["missing_cite_count"], 0)
        self.assertEqual(report["sibling_collision_count"], 0)


# ---------------------------------------------------------------------------
# Bonus: JSON report key completeness
# ---------------------------------------------------------------------------


class JsonOutputKeysTest(_VerifyFileDocsBase):

    def test_all_top_level_keys_present(self):
        """All 11 required top-level keys present; gates sub-keys match A.4."""
        self._build_clean_mds(n=3)
        r = self._verify_file_docs()
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
            "total_md_files",  # renamed from total_annotations
        }
        self.assertEqual(set(report.keys()), expected_keys)
        expected_gate_keys = {
            "ambiguous_rate",
            "banned_phrase",
            "cross_concern_duplicate",
            "vacuous_pass",
        }
        self.assertEqual(set(report["gates"].keys()), expected_gate_keys)
        expected_conf_keys = {"ambiguous", "extracted", "inferred"}
        self.assertEqual(set(report["confidence_distribution"].keys()), expected_conf_keys)


if __name__ == "__main__":
    unittest.main()
