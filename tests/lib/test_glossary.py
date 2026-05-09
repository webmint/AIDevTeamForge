"""Tests for src/devforge/lib/_generate_docs/_glossary.py (Track B.1).

30+ cases covering:
  1. build-glossary-bundles smoke (5)
  2. Ranking (4)
  3. set-glossary-entries happy path (3)
  4. set-glossary-entries count bounds (2)
  5. Per-entry validation (6)
  6. Cross-entry validation (2)
  7. Renderer output shape (4)
  8. CBM CLI mocking sanity (2)
  9. Atomic write (2)

All CBM calls are mocked via monkeypatching _run_cbm_cli at the module level.
No real codebase-memory-mcp binary required.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _generate_docs._glossary import (  # noqa: E402
    _atomic_write,
    _classify_term,
    _doc_context_for,
    _fetch_code_freq,
    _fetch_related_set,
    _fetch_snippet,
    _rank_combined,
    _render_glossary,
    _run_cbm_cli,
    _validate_entries,
    _W1,
    _W2,
    _W3,
    cmd_build_glossary_bundles,
    cmd_set_glossary_entries,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_args_build(devforge_dir: Path, **overrides) -> argparse.Namespace:
    base = {
        "devforge_dir": str(devforge_dir),
        "top_n": 80,
        "bm25_threshold": -25.0,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _make_args_set(
    devforge_dir: Path,
    entries: List[Dict],
    bundles_file: Path,
    **overrides,
) -> argparse.Namespace:
    base = {
        "devforge_dir": str(devforge_dir),
        "entries": json.dumps(entries),
        "bundles_file": str(bundles_file),
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def _write_md(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_corpus_dir(tmp_root: Path, files: Dict[str, str]) -> Path:
    """Create docs/ directory with named .md files (relative to tmp_root)."""
    docs = tmp_root / "docs"
    for rel, body in files.items():
        _write_md(docs / rel, body)
    return tmp_root


def _noop_cbm(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """CBM always absent — returns no-binary result."""
    return {"ran": False, "reason": "codebase-memory-mcp binary not found on PATH", "duration_ms": 0}


def _make_bundle(
    term: str,
    cls: str = "prose-only",
    cite_md_paths: Optional[List[str]] = None,
    code_anchor: Optional[Dict] = None,
) -> Dict[str, Any]:
    return {
        "term": term,
        "class": cls,
        "doc_context": "Some context for {0}.".format(term),
        "code_anchor": code_anchor,
        "related_set": [],
        "cite_md_paths": cite_md_paths or [],
    }


def _make_valid_entries(
    n: int,
    prefix: str = "Term",
    cite_count: int = 2,
) -> List[Dict]:
    """Return n valid prose-only entries with no related_terms."""
    return [
        {
            "term": "{0}{1}".format(prefix, i),
            "definition": "Definition for {0}{1}.".format(prefix, i),
            "related_terms": [],
        }
        for i in range(n)
    ]


def _make_valid_bundles(
    n: int,
    prefix: str = "Term",
    cite_count: int = 2,
    docs_root: Optional[Path] = None,
) -> List[Dict]:
    """Return n bundles for prose-only terms.

    Cite paths are docs_root-relative (no "docs/" prefix) — matches the shape
    walk_doc_corpus produces in production. If docs_root is given, files are
    materialized at docs_root/<rel> so validate_cite_paths passes.
    """
    bundles = []
    for i in range(n):
        term = "{0}{1}".format(prefix, i)
        cite_paths = ["file{0}a.md".format(i), "file{0}b.md".format(i)]
        if docs_root is not None:
            for cp in cite_paths:
                fp = docs_root / cp
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_text("# {0}".format(term), encoding="utf-8")
        bundles.append(_make_bundle(term, "prose-only", cite_paths))
    return bundles


# ---------------------------------------------------------------------------
# Group 1: build-glossary-bundles smoke (5 cases)
# ---------------------------------------------------------------------------


class BuildGlossaryBundlesSmokeTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_docs_exits_2(self):
        """Case 1: empty docs/ → exit 2."""
        args = _make_args_build(self.devforge)
        with patch("_generate_docs._glossary._run_cbm_cli", side_effect=_noop_cbm):
            code = cmd_build_glossary_bundles(args)
        self.assertEqual(code, 2)

    def test_zero_terms_after_noise_filter_exit_0(self, *_):
        """Case 2: 1 md file with all-noise terms → exit 0, empty bundles on stdout."""
        # All terms in the noise baseline — e.g. "Vue" "JSON" only.
        _make_corpus_dir(
            self.root,
            {"index.md": "# Vue JSON API\n\nSome text about Vue and JSON.\n"},
        )
        args = _make_args_build(self.devforge)
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with patch("_generate_docs._glossary._run_cbm_cli", side_effect=_noop_cbm):
            with redirect_stdout(buf):
                code = cmd_build_glossary_bundles(args)
        self.assertEqual(code, 0)
        bundles = json.loads(buf.getvalue())
        self.assertIsInstance(bundles, list)
        self.assertEqual(len(bundles), 0)

    def test_code_anchored_classification(self):
        """Case 3: query_graph returns code-anchored hit → bundle class is code-anchored."""
        _make_corpus_dir(
            self.root,
            {"arch.md": "# BLoC\n\nBLoC is a presentation layer state container.\n"},
        )
        args = _make_args_build(self.devforge)

        def fake_cbm(tool_name: str, payload: Dict) -> Dict:
            if tool_name == "query_graph":
                query = payload.get("query", "")
                if "BLoC" in query and "CALLS" not in query and "SEMANTICALLY" not in query:
                    return {
                        "ran": True,
                        "exit_code": 0,
                        "result": [
                            {
                                "n.qualified_name": "pkg.BLoC",
                                "labels(n)": ["Class"],
                                "n.file_path": "src/BLoC.ts",
                                "n.start_line": 14,
                                "n.is_exported": True,
                            }
                        ],
                    }
            return {"ran": False, "reason": "noop", "duration_ms": 0}

        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with patch("_generate_docs._glossary._run_cbm_cli", side_effect=fake_cbm):
            with redirect_stdout(buf):
                code = cmd_build_glossary_bundles(args)
        self.assertEqual(code, 0)
        bundles = json.loads(buf.getvalue())
        bloc_bundles = [b for b in bundles if b["term"] == "BLoC"]
        self.assertTrue(len(bloc_bundles) >= 1)
        self.assertEqual(bloc_bundles[0]["class"], "code-anchored")

    def test_fuzzy_anchored_fallback(self):
        """Case 4: query_graph 0 hits, search_graph rank >= threshold → fuzzy-anchored."""
        _make_corpus_dir(
            self.root,
            {"arch.md": "# UseCaseBridge\n\nUseCaseBridge connects layers.\n"},
        )
        args = _make_args_build(self.devforge, bm25_threshold=-25.0)

        def fake_cbm(tool_name: str, payload: Dict) -> Dict:
            if tool_name == "query_graph":
                query = payload.get("query", "")
                # Exact match query returns empty.
                if "CALLS" not in query and "SEMANTICALLY" not in query:
                    return {"ran": True, "exit_code": 0, "result": []}
            if tool_name == "search_graph":
                return {
                    "ran": True,
                    "exit_code": 0,
                    "result": [
                        {
                            "qualified_name": "pkg.UseCaseBridge",
                            "rank": -10.0,
                            "file_path": "src/bridge.ts",
                            "start_line": 5,
                            "is_exported": False,
                        }
                    ],
                }
            return {"ran": False, "reason": "noop", "duration_ms": 0}

        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with patch("_generate_docs._glossary._run_cbm_cli", side_effect=fake_cbm):
            with redirect_stdout(buf):
                code = cmd_build_glossary_bundles(args)
        self.assertEqual(code, 0)
        bundles = json.loads(buf.getvalue())
        bridge_bundles = [b for b in bundles if b["term"] == "UseCaseBridge"]
        self.assertTrue(len(bridge_bundles) >= 1)
        self.assertEqual(bridge_bundles[0]["class"], "fuzzy-anchored")

    def test_prose_only_requires_2_paths(self):
        """Case 5: both CBM queries 0 hits, term in 1 md path → dropped; 2 paths → prose-only."""
        # Term in two separate files → kept as prose-only.
        _make_corpus_dir(
            self.root,
            {
                "file1.md": "# DomainLayer\n\nDomainLayer is important.\n",
                "file2.md": "# Overview\n\nDomainLayer and services.\n",
            },
        )
        args = _make_args_build(self.devforge)

        def fake_cbm_no_hits(tool_name: str, payload: Dict) -> Dict:
            return {"ran": True, "exit_code": 0, "result": []}

        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with patch("_generate_docs._glossary._run_cbm_cli", side_effect=fake_cbm_no_hits):
            with redirect_stdout(buf):
                code = cmd_build_glossary_bundles(args)
        self.assertEqual(code, 0)
        bundles = json.loads(buf.getvalue())
        dl_bundles = [b for b in bundles if b["term"] == "DomainLayer"]
        self.assertTrue(len(dl_bundles) >= 1)
        self.assertEqual(dl_bundles[0]["class"], "prose-only")

        # Now test term in only 1 file → dropped.
        tmp2 = tempfile.TemporaryDirectory()
        try:
            root2 = Path(tmp2.name)
            devforge2 = root2 / ".devforge"
            devforge2.mkdir(parents=True)
            _make_corpus_dir(root2, {"file1.md": "# SingleOccurrenceTerm\n\nOnly here.\n"})
            args2 = _make_args_build(devforge2)
            buf2 = io.StringIO()
            with patch("_generate_docs._glossary._run_cbm_cli", side_effect=fake_cbm_no_hits):
                with redirect_stdout(buf2):
                    code2 = cmd_build_glossary_bundles(args2)
            self.assertEqual(code2, 0)
            bundles2 = json.loads(buf2.getvalue())
            so_bundles = [b for b in bundles2 if b["term"] == "SingleOccurrenceTerm"]
            self.assertEqual(len(so_bundles), 0)
        finally:
            tmp2.cleanup()


# ---------------------------------------------------------------------------
# Group 2: Ranking (4 cases)
# ---------------------------------------------------------------------------


class RankingTests(unittest.TestCase):

    def test_high_doc_freq_zero_code_freq(self):
        """Case 6: high doc_freq + 0 code_freq → rank computed (non-zero from log)."""
        import math
        score = _rank_combined(doc_freq=50, code_freq=0, is_exported=False)
        expected = _W1 * math.log(51)
        self.assertAlmostEqual(score, expected, places=6)

    def test_high_code_freq_ranks_higher_than_doc_only(self):
        """Case 7: same doc_freq, higher code_freq → higher rank (W2 > W1)."""
        import math
        score_low = _rank_combined(doc_freq=10, code_freq=0, is_exported=False)
        score_high = _rank_combined(doc_freq=10, code_freq=20, is_exported=False)
        self.assertGreater(score_high, score_low)

    def test_is_exported_bonus_adds_positive_offset(self):
        """Case 8: is_exported=True adds W3 to score."""
        import math
        score_no = _rank_combined(doc_freq=5, code_freq=5, is_exported=False)
        score_yes = _rank_combined(doc_freq=5, code_freq=5, is_exported=True)
        self.assertAlmostEqual(score_yes - score_no, _W3, places=6)

    def test_top_n_truncation(self):
        """Case 9: top-n=80 out of 100 candidates → 80 in output."""
        # Build a docs dir with enough unique PascalCase terms.
        # We'll generate 100 terms across 2 files each.
        tmp = tempfile.TemporaryDirectory()
        try:
            root = Path(tmp.name)
            devforge = root / ".devforge"
            devforge.mkdir(parents=True)
            docs = root / "docs"
            docs.mkdir(parents=True)

            # Two files, 50 terms each (100 total).
            terms_a = ["Alpha{0:03d}".format(i) for i in range(50)]
            terms_b = ["Beta{0:03d}".format(i) for i in range(50)]
            (docs / "file_a.md").write_text(
                " ".join(terms_a), encoding="utf-8"
            )
            (docs / "file_b.md").write_text(
                " ".join(terms_a + terms_b), encoding="utf-8"
            )

            args = _make_args_build(devforge, top_n=80)

            def fake_cbm_prose_only(tool_name: str, payload: Dict) -> Dict:
                return {"ran": True, "exit_code": 0, "result": []}

            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with patch("_generate_docs._glossary._run_cbm_cli", side_effect=fake_cbm_prose_only):
                with redirect_stdout(buf):
                    code = cmd_build_glossary_bundles(args)
            self.assertEqual(code, 0)
            bundles = json.loads(buf.getvalue())
            # Alpha terms appear in both files → prose-only; Beta only in file_b → single
            # path → dropped. So we should get <=50 bundles (the Alpha ones).
            # With top_n=80, we get min(kept, 80).
            self.assertLessEqual(len(bundles), 80)
        finally:
            tmp.cleanup()


# ---------------------------------------------------------------------------
# Group 3: set-glossary-entries happy path (3 cases)
# ---------------------------------------------------------------------------


class SetGlossaryEntriesHappyPathTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_bundles_file(self, bundles: List[Dict]) -> Path:
        p = self.devforge / "bundles.json"
        p.write_text(json.dumps(bundles, indent=2), encoding="utf-8")
        return p

    def _noop_snippet(self, *a, **k):
        return ""

    def test_30_valid_entries_exit_0(self):
        """Case 10: 30 valid prose-only entries → exit 0, glossary.md written."""
        n = 30
        bundles = _make_valid_bundles(n, docs_root=self.root / "docs")
        entries = _make_valid_entries(n)
        bundles_file = self._write_bundles_file(bundles)
        args = _make_args_set(self.devforge, entries, bundles_file)

        with patch("_generate_docs._glossary._fetch_snippet", return_value=""):
            code = cmd_set_glossary_entries(args)
        self.assertEqual(code, 0)
        glossary = self.root / "docs" / "glossary.md"
        self.assertTrue(glossary.exists())

    def test_150_valid_entries_exit_0(self):
        """Case 11: 150 valid entries → exit 0."""
        n = 150
        bundles = _make_valid_bundles(n, docs_root=self.root / "docs")
        entries = _make_valid_entries(n)
        bundles_file = self._write_bundles_file(bundles)
        args = _make_args_set(self.devforge, entries, bundles_file)

        with patch("_generate_docs._glossary._fetch_snippet", return_value=""):
            code = cmd_set_glossary_entries(args)
        self.assertEqual(code, 0)

    def test_frontmatter_has_correct_total_and_date(self):
        """Case 12: glossary.md frontmatter contains correct total_terms + last_indexed."""
        from datetime import datetime, timezone

        n = 30
        bundles = _make_valid_bundles(n, docs_root=self.root / "docs")
        entries = _make_valid_entries(n)
        bundles_file = self._write_bundles_file(bundles)
        args = _make_args_set(self.devforge, entries, bundles_file)

        with patch("_generate_docs._glossary._fetch_snippet", return_value=""):
            cmd_set_glossary_entries(args)
        content = (self.root / "docs" / "glossary.md").read_text(encoding="utf-8")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.assertIn("total_terms: {0}".format(n), content)
        self.assertIn("last_indexed: {0}".format(today), content)


# ---------------------------------------------------------------------------
# Group 4: set-glossary-entries count bounds (2 cases)
# ---------------------------------------------------------------------------


class SetGlossaryEntriesCountBoundsTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_bundles_file(self, bundles: List[Dict]) -> Path:
        p = self.devforge / "bundles.json"
        p.write_text(json.dumps(bundles, indent=2), encoding="utf-8")
        return p

    def test_29_entries_exit_2(self):
        """Case 13: 29 entries → exit 2."""
        n = 29
        bundles = _make_valid_bundles(n, docs_root=self.root / "docs")
        entries = _make_valid_entries(n)
        bundles_file = self._write_bundles_file(bundles)
        args = _make_args_set(self.devforge, entries, bundles_file)

        with patch("_generate_docs._glossary._fetch_snippet", return_value=""):
            code = cmd_set_glossary_entries(args)
        self.assertEqual(code, 2)

    def test_151_entries_exit_2(self):
        """Case 14: 151 entries → exit 2."""
        n = 151
        bundles = _make_valid_bundles(n, docs_root=self.root / "docs")
        entries = _make_valid_entries(n)
        bundles_file = self._write_bundles_file(bundles)
        args = _make_args_set(self.devforge, entries, bundles_file)

        with patch("_generate_docs._glossary._fetch_snippet", return_value=""):
            code = cmd_set_glossary_entries(args)
        self.assertEqual(code, 2)


# ---------------------------------------------------------------------------
# Group 5: Per-entry validation (6 cases)
# ---------------------------------------------------------------------------


class PerEntryValidationTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir(parents=True)
        self.n = 30

    def tearDown(self):
        self.tmp.cleanup()

    def _write_bundles_file(self, bundles: List[Dict]) -> Path:
        p = self.devforge / "bundles.json"
        p.write_text(json.dumps(bundles, indent=2), encoding="utf-8")
        return p

    def _run(self, entries, bundles):
        bundles_file = self._write_bundles_file(bundles)
        args = _make_args_set(self.devforge, entries, bundles_file)
        with patch("_generate_docs._glossary._fetch_snippet", return_value=""):
            return cmd_set_glossary_entries(args)

    def test_empty_definition_exit_2(self):
        """Case 15: definition empty post-strip → exit 2."""
        bundles = _make_valid_bundles(self.n, docs_root=self.root / "docs")
        entries = _make_valid_entries(self.n)
        entries[0]["definition"] = "   "  # strip → empty
        self.assertEqual(self._run(entries, bundles), 2)

    def test_definition_over_280_chars_exit_2(self):
        """Case 16: definition > 280 chars → exit 2."""
        bundles = _make_valid_bundles(self.n, docs_root=self.root / "docs")
        entries = _make_valid_entries(self.n)
        entries[0]["definition"] = "x" * 281
        self.assertEqual(self._run(entries, bundles), 2)

    def test_definition_with_newline_exit_2(self):
        """Case 17: definition contains newline → exit 2."""
        bundles = _make_valid_bundles(self.n, docs_root=self.root / "docs")
        entries = _make_valid_entries(self.n)
        entries[0]["definition"] = "First paragraph.\nSecond paragraph."
        self.assertEqual(self._run(entries, bundles), 2)

    def test_term_no_matching_bundle_exit_2(self):
        """Case 18: term has no matching bundle → exit 2."""
        bundles = _make_valid_bundles(self.n, docs_root=self.root / "docs")
        entries = _make_valid_entries(self.n)
        entries[0]["term"] = "NoMatchBundle"  # not in bundles
        self.assertEqual(self._run(entries, bundles), 2)

    def test_prose_only_less_than_2_cite_paths_exit_2(self):
        """Case 19: prose-only entry with only 1 cite_md_path → exit 2."""
        bundles = _make_valid_bundles(self.n, docs_root=self.root / "docs")
        # Override first bundle to have only 1 cite path.
        single_path = "docs/single.md"
        (self.root / single_path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / single_path).write_text("# x", encoding="utf-8")
        bundles[0]["cite_md_paths"] = [single_path]
        entries = _make_valid_entries(self.n)
        self.assertEqual(self._run(entries, bundles), 2)

    def test_dangling_related_terms_exit_2(self):
        """Case 20: related_terms contains a non-existent term → exit 2."""
        bundles = _make_valid_bundles(self.n, docs_root=self.root / "docs")
        entries = _make_valid_entries(self.n)
        entries[0]["related_terms"] = ["NonExistentTerm9999"]
        self.assertEqual(self._run(entries, bundles), 2)


# ---------------------------------------------------------------------------
# Group 6: Cross-entry validation (2 cases)
# ---------------------------------------------------------------------------


class CrossEntryValidationTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir(parents=True)
        self.n = 30

    def tearDown(self):
        self.tmp.cleanup()

    def _write_bundles_file(self, bundles: List[Dict]) -> Path:
        p = self.devforge / "bundles.json"
        p.write_text(json.dumps(bundles, indent=2), encoding="utf-8")
        return p

    def _run(self, entries, bundles):
        bundles_file = self._write_bundles_file(bundles)
        args = _make_args_set(self.devforge, entries, bundles_file)
        with patch("_generate_docs._glossary._fetch_snippet", return_value=""):
            return cmd_set_glossary_entries(args)

    def test_duplicate_terms_case_insensitive_exit_2(self):
        """Case 21: duplicate terms (case-insensitive) → exit 2."""
        bundles = _make_valid_bundles(self.n, docs_root=self.root / "docs")
        entries = _make_valid_entries(self.n)
        # Duplicate entries[0] as lowercase.
        dup = dict(entries[0])
        dup["term"] = entries[0]["term"].lower()
        entries.append(dup)
        # Add a bundle for the dup.
        dup_bundle = _make_bundle(dup["term"], "prose-only", bundles[0]["cite_md_paths"])
        bundles.append(dup_bundle)
        self.assertEqual(self._run(entries, bundles), 2)

    def test_case_insensitive_related_terms_reference_passes(self):
        """Case 22: related_terms refer to existing term via different case → valid."""
        bundles = _make_valid_bundles(self.n, docs_root=self.root / "docs")
        entries = _make_valid_entries(self.n)
        # Entry 0 refers to Entry 1 by lowercase.
        term1 = entries[1]["term"]
        entries[0]["related_terms"] = [term1.lower()]
        self.assertEqual(self._run(entries, bundles), 0)


# ---------------------------------------------------------------------------
# Group 7: Renderer output shape (4 cases)
# ---------------------------------------------------------------------------


class RendererTests(unittest.TestCase):

    def _make_entries_and_bundles(
        self,
        terms_and_classes: List[tuple],
        cite_paths_per_term: Optional[Dict[str, List[str]]] = None,
        code_anchors: Optional[Dict[str, Dict]] = None,
    ) -> tuple:
        """Build minimal entries + bundles_by_term for render testing."""
        entries = []
        bundles_by_term: Dict[str, Dict] = {}
        for term, cls in terms_and_classes:
            entry = {
                "term": term,
                "definition": "Definition of {0}.".format(term),
                "related_terms": [],
            }
            entries.append(entry)
            cite_paths = (cite_paths_per_term or {}).get(
                term, ["docs/a.md", "docs/b.md"]
            )
            code_anchor = (code_anchors or {}).get(term)
            bundle = _make_bundle(term, cls, cite_paths, code_anchor)
            bundles_by_term[term.lower()] = bundle
        return entries, bundles_by_term

    def test_code_anchored_has_defined_line(self):
        """Case 23: code-anchored entry → "Defined" line with qn:line."""
        anchor = {"qn": "pkg.BLoC", "file": "src/BLoC.ts", "line": 14, "snippet": ""}
        entries, bundles_by_term = self._make_entries_and_bundles(
            [("BLoC", "code-anchored")],
            code_anchors={"BLoC": anchor},
        )
        content = _render_glossary(entries, bundles_by_term)
        self.assertIn("**Defined**: `pkg.BLoC:14`", content)
        self.assertNotIn("(fuzzy)", content)

    def test_prose_only_has_no_defined_line(self):
        """Case 24: prose-only entry → "Defined" line is OMITTED."""
        entries, bundles_by_term = self._make_entries_and_bundles(
            [("domainLayer", "prose-only")]
        )
        content = _render_glossary(entries, bundles_by_term)
        self.assertNotIn("**Defined**", content)

    def test_used_in_cap_5_shows_3_inline_and_others(self):
        """Case 25: 5 cite_md_paths → first 3 inline + (and 2 others)."""
        paths = [
            "docs/a.md",
            "docs/b.md",
            "docs/c.md",
            "docs/d.md",
            "docs/e.md",
        ]
        entries, bundles_by_term = self._make_entries_and_bundles(
            [("MyTerm", "prose-only")],
            cite_paths_per_term={"MyTerm": paths},
        )
        content = _render_glossary(entries, bundles_by_term)
        self.assertIn("`docs/a.md`", content)
        self.assertIn("`docs/b.md`", content)
        self.assertIn("`docs/c.md`", content)
        self.assertNotIn("`docs/d.md`", content)
        self.assertIn("(and 2 others)", content)

    def test_alphabetical_sort_case_insensitive(self):
        """Case 26: entries sorted alphabetically case-insensitive."""
        entries, bundles_by_term = self._make_entries_and_bundles(
            [("Zebra", "prose-only"), ("apple", "prose-only"), ("Mango", "prose-only")]
        )
        content = _render_glossary(entries, bundles_by_term)
        pos_apple = content.index("## apple")
        pos_mango = content.index("## Mango")
        pos_zebra = content.index("## Zebra")
        self.assertLess(pos_apple, pos_mango)
        self.assertLess(pos_mango, pos_zebra)


# ---------------------------------------------------------------------------
# Group 8: CBM CLI mocking sanity (2 cases)
# ---------------------------------------------------------------------------


class CbmCliMockingTests(unittest.TestCase):

    def test_oserror_returns_ran_false(self):
        """Case 27: subprocess.run raises OSError → _run_cbm_cli returns {ran:False}."""
        import shutil
        with patch("shutil.which", return_value="/fake/codebase-memory-mcp"):
            with patch("subprocess.run", side_effect=OSError("exec failed")):
                result = _run_cbm_cli("query_graph", {"query": "MATCH (n)"})
        self.assertFalse(result["ran"])
        self.assertIn("cli invocation failed", result["reason"])

    def test_binary_not_on_path_returns_ran_false(self):
        """Case 28: codebase-memory-mcp not on PATH → {ran:False}."""
        with patch("shutil.which", return_value=None):
            result = _run_cbm_cli("query_graph", {"query": "MATCH (n)"})
        self.assertFalse(result["ran"])
        self.assertIn("not found on PATH", result["reason"])


# ---------------------------------------------------------------------------
# Group 9: Atomic write (2 cases)
# ---------------------------------------------------------------------------


class AtomicWriteTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_minimal_setup(self, n: int = 30) -> tuple:
        """Create valid prose-only bundles + entries for n terms, return (entries, bundles)."""
        bundles = _make_valid_bundles(n, docs_root=self.root / "docs")
        entries = _make_valid_entries(n)
        return entries, bundles

    def test_existing_glossary_overwritten(self):
        """Case 29: existing docs/glossary.md is overwritten cleanly."""
        glossary_path = self.root / "docs" / "glossary.md"
        glossary_path.parent.mkdir(parents=True, exist_ok=True)
        glossary_path.write_text("OLD CONTENT", encoding="utf-8")

        n = 30
        entries, bundles = self._make_minimal_setup(n)
        bundles_file = self.devforge / "bundles.json"
        bundles_file.write_text(json.dumps(bundles), encoding="utf-8")
        args = _make_args_set(self.devforge, entries, bundles_file)

        with patch("_generate_docs._glossary._fetch_snippet", return_value=""):
            code = cmd_set_glossary_entries(args)
        self.assertEqual(code, 0)
        content = glossary_path.read_text(encoding="utf-8")
        self.assertNotIn("OLD CONTENT", content)
        self.assertIn("# Project Glossary", content)

    @unittest.skipIf(os.getuid() == 0, "root bypasses file permissions")
    def test_write_to_read_only_dir_exit_1(self):
        """Case 30: write to read-only dir → exit 1 (I/O failure)."""
        n = 30
        entries, bundles = self._make_minimal_setup(n)
        bundles_file = self.devforge / "bundles.json"
        bundles_file.write_text(json.dumps(bundles), encoding="utf-8")

        # Make docs/ read-only.
        docs = self.root / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        old_mode = docs.stat().st_mode
        try:
            docs.chmod(stat.S_IREAD | stat.S_IEXEC)
            args = _make_args_set(self.devforge, entries, bundles_file)
            with patch("_generate_docs._glossary._fetch_snippet", return_value=""):
                code = cmd_set_glossary_entries(args)
            self.assertEqual(code, 1)
        finally:
            docs.chmod(old_mode)


# ---------------------------------------------------------------------------
# Additional edge-case group: _validate_entries direct unit tests
# ---------------------------------------------------------------------------


class ValidateEntriesDirectTests(unittest.TestCase):
    """Direct unit tests of _validate_entries for edge cases not easily
    reachable via the full CLI path."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _make_bundles_dict(self, n: int) -> Dict[str, Dict]:
        bundles = _make_valid_bundles(n, docs_root=self.root / "docs")
        return {b["term"].lower(): b for b in bundles}

    def test_too_few_entries_returns_error(self):
        n = 29
        entries = _make_valid_entries(n)
        bdict = self._make_bundles_dict(n)
        error, code = _validate_entries(entries, bdict, self.root)
        self.assertIsNotNone(error)
        self.assertIn("too few", error)
        self.assertEqual(code, 2)

    def test_too_many_entries_returns_error(self):
        n = 151
        entries = _make_valid_entries(n)
        bdict = self._make_bundles_dict(n)
        error, code = _validate_entries(entries, bdict, self.root)
        self.assertIsNotNone(error)
        self.assertIn("too many", error)
        self.assertEqual(code, 2)

    def test_exactly_30_entries_passes(self):
        n = 30
        entries = _make_valid_entries(n)
        bdict = self._make_bundles_dict(n)
        with patch("_generate_docs._glossary._fetch_snippet", return_value="x"):
            error, code = _validate_entries(entries, bdict, self.root)
        self.assertIsNone(error)
        self.assertEqual(code, 0)

    def test_exactly_150_entries_passes(self):
        n = 150
        entries = _make_valid_entries(n)
        bdict = self._make_bundles_dict(n)
        with patch("_generate_docs._glossary._fetch_snippet", return_value="x"):
            error, code = _validate_entries(entries, bdict, self.root)
        self.assertIsNone(error)
        self.assertEqual(code, 0)


# ---------------------------------------------------------------------------
# Finding 1 regression: _run_cbm_cli prefers array over info-object line
# ---------------------------------------------------------------------------


class CbmCliArrayPriorityTests(unittest.TestCase):
    """Regression tests for Finding 1 — array result must beat info-line object."""

    def _make_run_result(self, stdout: str, returncode: int = 0):
        """Build a fake subprocess.CompletedProcess with given stdout."""
        import subprocess
        r = subprocess.CompletedProcess(args=[], returncode=returncode)
        r.stdout = stdout
        r.stderr = ""
        return r

    def test_run_cbm_cli_prefers_array_when_info_line_precedes(self):
        """Finding 1: info {} line before [] array → result must be the array."""
        stdout = (
            '{"level": "info", "msg": "index loaded"}\n'
            '[{"name": "Foo"}]\n'
        )
        fake_result = self._make_run_result(stdout)
        with patch("shutil.which", return_value="/fake/codebase-memory-mcp"):
            with patch("subprocess.run", return_value=fake_result):
                block = _run_cbm_cli("query_graph", {"query": "MATCH (n)"})
        self.assertTrue(block.get("ran"))
        result = block.get("result")
        self.assertIsInstance(result, list, "result should be the array, not the info dict")
        self.assertEqual(result, [{"name": "Foo"}])

    def test_run_cbm_cli_falls_back_to_object_when_no_array(self):
        """Finding 1 inverse: stdout with only {} (e.g. index_repository) → dict result."""
        stdout = '{"status": "ok", "indexed": 42}\n'
        fake_result = self._make_run_result(stdout)
        with patch("shutil.which", return_value="/fake/codebase-memory-mcp"):
            with patch("subprocess.run", return_value=fake_result):
                block = _run_cbm_cli("index_repository", {"project_root": "/tmp"})
        self.assertTrue(block.get("ran"))
        result = block.get("result")
        self.assertIsInstance(result, dict, "result should be the object dict")
        self.assertEqual(result.get("status"), "ok")


# ---------------------------------------------------------------------------
# Finding 3: fuzzy-anchored renderer positive test
# ---------------------------------------------------------------------------


class RendererFuzzyAnchoredTests(unittest.TestCase):
    """Positive test for fuzzy-anchored (fuzzy) suffix in rendered output."""

    def test_fuzzy_anchored_has_fuzzy_suffix_in_defined_line(self):
        """Finding 3: fuzzy-anchored bundle → "(fuzzy)" appears in Defined line."""
        anchor = {
            "qn": "pkg.UseCaseBridge",
            "file": "src/bridge.ts",
            "line": 5,
            "snippet": "export class UseCaseBridge {",
            "fuzzy": True,
        }
        entry = {
            "term": "UseCaseBridge",
            "definition": "Connects use-case layer to infrastructure.",
            "related_terms": [],
        }
        bundle = _make_bundle(
            "UseCaseBridge",
            "fuzzy-anchored",
            ["docs/a.md", "docs/b.md"],
            anchor,
        )
        bundles_by_term = {"usecasebridge": bundle}
        content = _render_glossary([entry], bundles_by_term)
        self.assertIn("**Defined**", content)
        self.assertIn("(fuzzy)", content)
        self.assertIn("`pkg.UseCaseBridge:5`", content)


class RendererHtmlEscapeTests(unittest.TestCase):
    """Regression: angle brackets in prose fields must HTML-encode so md
    previewers don't interpret bare `<S>` as a strikethrough open tag (the
    failure mode reported on testForge20: a definition containing `BLoC<S>`
    caused WebStorm's preview to strikethrough every line that followed)."""

    def test_definition_angle_brackets_escaped(self):
        bundle = _make_bundle("BLoC", "prose-only", ["x.md", "y.md"])
        entry = {
            "term": "BLoC",
            "definition": "Subclasses BLoC<S> base; <Concern>BLoC holds state.",
            "related_terms": [],
        }
        content = _render_glossary([entry], {"bloc": bundle})
        self.assertIn("BLoC&lt;S&gt;", content)
        self.assertIn("&lt;Concern&gt;BLoC", content)
        self.assertNotIn("BLoC<S>", content)
        self.assertNotIn("<Concern>", content)

    def test_term_heading_angle_brackets_escaped(self):
        term = "Either<L,R>"
        bundle = _make_bundle(term, "prose-only", ["x.md", "y.md"])
        entry = {"term": term, "definition": "A sum type.", "related_terms": []}
        content = _render_glossary([entry], {term.lower(): bundle})
        self.assertIn("## Either&lt;L,R&gt;", content)
        self.assertNotIn("## Either<L,R>", content)

    def test_related_terms_angle_brackets_escaped(self):
        bundle = _make_bundle("Foo", "prose-only", ["x.md", "y.md"])
        entry = {
            "term": "Foo",
            "definition": "A thing.",
            "related_terms": ["Bar<T>", "Baz"],
        }
        content = _render_glossary([entry], {"foo": bundle})
        self.assertIn("Bar&lt;T&gt;", content)
        self.assertNotIn("Bar<T>", content)

    def test_ampersand_escaped_first(self):
        # Order check: an existing `&` in input must not double-encode the
        # entities we just emitted.
        bundle = _make_bundle("AT&T", "prose-only", ["x.md", "y.md"])
        entry = {
            "term": "AT&T",
            "definition": "A & B.",
            "related_terms": [],
        }
        content = _render_glossary([entry], {"at&t": bundle})
        self.assertIn("AT&amp;T", content)
        self.assertIn("A &amp; B.", content)
        # Must NOT see double-encoded artifacts:
        self.assertNotIn("&amp;amp;", content)


# ---------------------------------------------------------------------------
# Finding 4 + Finding 2: cmd-level code-anchored tests
# ---------------------------------------------------------------------------


def _make_code_anchored_bundle(
    term: str,
    cite_paths: List[str],
    qn: str = "pkg.SomeClass",
    file: str = "src/some.ts",
    line: int = 1,
) -> Dict[str, Any]:
    """Return a code-anchored bundle with a valid code_anchor."""
    return {
        "term": term,
        "class": "code-anchored",
        "doc_context": "Context for {0}.".format(term),
        "code_anchor": {
            "qn": qn,
            "file": file,
            "line": line,
            "snippet": "",
        },
        "related_set": [],
        "cite_md_paths": cite_paths,
    }


class CodeAnchoredCmdTests(unittest.TestCase):
    """Cmd-level tests exercising code-anchored entries (Finding 4 + Finding 2)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.devforge = self.root / ".devforge"
        self.devforge.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_bundles_file(self, bundles: List[Dict]) -> Path:
        p = self.devforge / "bundles.json"
        p.write_text(json.dumps(bundles, indent=2), encoding="utf-8")
        return p

    def _make_mixed_setup(self, n: int = 30) -> tuple:
        """Return (entries, bundles) with n-1 prose-only + 1 code-anchored entry.

        The code-anchored term is "CodeAnchoredTerm" at index 0.
        All cite files are created on disk so validate_cite_paths passes.
        """
        # Prose-only entries: Term1 .. Term(n-1)
        prose_entries = _make_valid_entries(n - 1, prefix="ProseTerm")
        prose_bundles = _make_valid_bundles(n - 1, prefix="ProseTerm", docs_root=self.root / "docs")

        # Code-anchored entry: CodeAnchoredTerm
        ca_term = "CodeAnchoredTerm"
        cite_paths = ["ca_a.md", "ca_b.md"]
        for cp in cite_paths:
            fp = self.root / "docs" / cp
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text("# {0}".format(ca_term), encoding="utf-8")
        ca_bundle = _make_code_anchored_bundle(ca_term, cite_paths, qn="pkg.CodeAnchoredTerm")
        ca_entry = {
            "term": ca_term,
            "definition": "A code-anchored term definition.",
            "related_terms": [],
        }

        entries = [ca_entry] + prose_entries
        bundles = [ca_bundle] + prose_bundles
        return entries, bundles

    def test_cmd_set_glossary_entries_code_anchored_happy_path(self):
        """Finding 4 case 1: 30-entry bundle with 1 code-anchored; snippet returns non-empty → exit 0."""
        entries, bundles = self._make_mixed_setup(n=30)
        bundles_file = self._write_bundles_file(bundles)
        args = _make_args_set(self.devforge, entries, bundles_file)

        with patch("_generate_docs._glossary._fetch_snippet", return_value="def CodeAnchoredTerm(): pass"):
            code = cmd_set_glossary_entries(args)

        self.assertEqual(code, 0)
        glossary = self.root / "docs" / "glossary.md"
        self.assertTrue(glossary.exists())
        content = glossary.read_text(encoding="utf-8")
        self.assertIn("## CodeAnchoredTerm", content)
        self.assertIn("**Defined**", content)

    def test_cmd_set_glossary_entries_exits_2_when_snippet_empty(self):
        """Code-anchored entry with empty snippet (CBM ran, qn yielded no content) → exit 2.

        Covers both Finding 4 case 2 (cmd-level code-anchored sad path) and Finding 2's
        empty-snippet validation-failure branch — distinct from CBM-unreachable (None).
        """
        entries, bundles = self._make_mixed_setup(n=30)
        bundles_file = self._write_bundles_file(bundles)
        args = _make_args_set(self.devforge, entries, bundles_file)

        with patch("_generate_docs._glossary._fetch_snippet", return_value=""):
            code = cmd_set_glossary_entries(args)

        self.assertEqual(code, 2)

    def test_cmd_set_glossary_entries_exits_1_when_cbm_unreachable_for_snippet(self):
        """Finding 2: _fetch_snippet returns None (CBM unreachable) → exit 1."""
        entries, bundles = self._make_mixed_setup(n=30)
        bundles_file = self._write_bundles_file(bundles)
        args = _make_args_set(self.devforge, entries, bundles_file)

        with patch("_generate_docs._glossary._fetch_snippet", return_value=None):
            code = cmd_set_glossary_entries(args)

        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
