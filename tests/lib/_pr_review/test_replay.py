"""Tests for src/devforge/lib/_pr_review/_replay.py.

Coverage:
  TestWriteBundle: bundle written; schema fields present; content correct.
  TestCorpusIndexLoad: existing valid; absent -> default empty; malformed -> default.
  TestUpsertNew: empty index -> new entry; first_reviewed_at=last; review_count=1.
  TestUpsertExisting: existing entry -> updated; review_count incremented; first preserved.
  TestUpsertDifferentRepo: same PR# but different repo -> new entry (not collision).
  TestAtomicWrite: temp file cleaned after success.
  TestRunHappyPath: state.json + run replay -> bundle + index updated.
  TestRunCreatedEntry: fresh index -> entry_action=created.
  TestRunUpdatedEntry: existing index entry -> entry_action=updated.
  TestRunNoStateFile: missing -> raises ValueError.
  TestCountsInIndex: counts correctly reflected in index entry.
"""

import dataclasses
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._replay import (  # noqa: E402
    _corpus_index_path,
    _load_corpus_index,
    _upsert_corpus_entry,
    _write_corpus_index,
    _write_bundle,
    _BUNDLE_FILENAME,
    _CORPUS_INDEX_FILENAME,
    _SCHEMA_VERSION,
    run,
)
from _pr_review._state import PRReviewState, state_path, _PR_REVIEWS_DIR  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------

_NOW = "2026-05-21T10:00:00Z"
_NOW2 = "2026-05-21T11:00:00Z"


def _make_state(pr_number=42, repo="acme/app", findings=None, smells=None,
                blast=None, drift=None):
    return PRReviewState(
        pr_number=pr_number,
        repo=repo,
        findings=findings if findings is not None else [],
        smells=smells if smells is not None else [],
        blast=blast if blast is not None else [],
        drift=drift if drift is not None else {},
    )


def _write_state_to_dir(tmp_dir, state):
    devforge = os.path.join(tmp_dir, ".devforge")
    sp = state_path(devforge, state.pr_number)
    os.makedirs(os.path.dirname(sp), exist_ok=True)
    with open(sp, "w", encoding="utf-8") as fh:
        json.dump(dataclasses.asdict(state), fh, indent=2)
        fh.write("\n")
    return sp


# ---------------------------------------------------------------------------
# TestWriteBundle
# ---------------------------------------------------------------------------

class TestWriteBundle(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._devforge = os.path.join(self._tmp, ".devforge")
        os.makedirs(self._devforge, exist_ok=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_bundle_written(self):
        state_dict = dataclasses.asdict(_make_state(pr_number=10, repo="x/y"))
        bundle_path = _write_bundle(
            self._devforge, pr_number=10, state_dict=state_dict,
            repo="x/y", now_ts=_NOW
        )
        self.assertTrue(os.path.isfile(bundle_path))

    def test_bundle_filename_correct(self):
        state_dict = dataclasses.asdict(_make_state(pr_number=10))
        bundle_path = _write_bundle(
            self._devforge, pr_number=10, state_dict=state_dict,
            repo="x/y", now_ts=_NOW
        )
        self.assertEqual(os.path.basename(bundle_path), _BUNDLE_FILENAME)

    def test_bundle_schema_version(self):
        state_dict = dataclasses.asdict(_make_state(pr_number=10))
        bundle_path = _write_bundle(
            self._devforge, pr_number=10, state_dict=state_dict,
            repo="x/y", now_ts=_NOW
        )
        with open(bundle_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["schema_version"], _SCHEMA_VERSION)

    def test_bundle_has_generated_at(self):
        state_dict = dataclasses.asdict(_make_state(pr_number=10))
        bundle_path = _write_bundle(
            self._devforge, pr_number=10, state_dict=state_dict,
            repo="x/y", now_ts=_NOW
        )
        with open(bundle_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["generated_at"], _NOW)

    def test_bundle_pr_number(self):
        state_dict = dataclasses.asdict(_make_state(pr_number=304))
        bundle_path = _write_bundle(
            self._devforge, pr_number=304, state_dict=state_dict,
            repo="org/x", now_ts=_NOW
        )
        with open(bundle_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["pr_number"], 304)

    def test_bundle_repo(self):
        state_dict = dataclasses.asdict(_make_state(pr_number=1, repo="org/proj"))
        bundle_path = _write_bundle(
            self._devforge, pr_number=1, state_dict=state_dict,
            repo="org/proj", now_ts=_NOW
        )
        with open(bundle_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["repo"], "org/proj")

    def test_bundle_state_present(self):
        state_dict = dataclasses.asdict(_make_state(pr_number=5, repo="a/b"))
        bundle_path = _write_bundle(
            self._devforge, pr_number=5, state_dict=state_dict,
            repo="a/b", now_ts=_NOW
        )
        with open(bundle_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertIn("state", data)
        self.assertEqual(data["state"]["pr_number"], 5)

    def test_bundle_under_pr_dir(self):
        state_dict = dataclasses.asdict(_make_state(pr_number=20))
        bundle_path = _write_bundle(
            self._devforge, pr_number=20, state_dict=state_dict,
            repo="a/b", now_ts=_NOW
        )
        expected_dir = os.path.join(
            self._devforge, _PR_REVIEWS_DIR, "20"
        )
        self.assertTrue(bundle_path.startswith(expected_dir))


# ---------------------------------------------------------------------------
# TestCorpusIndexLoad
# ---------------------------------------------------------------------------

class TestCorpusIndexLoad(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_absent_returns_empty_default(self):
        path = os.path.join(self._tmp, "missing.json")
        result = _load_corpus_index(path)
        self.assertEqual(result["schema_version"], _SCHEMA_VERSION)
        self.assertEqual(result["entries"], [])

    def test_malformed_json_returns_empty_default(self):
        path = os.path.join(self._tmp, "bad.json")
        with open(path, "w") as fh:
            fh.write("{not valid json}")
        result = _load_corpus_index(path)
        self.assertEqual(result["entries"], [])

    def test_non_dict_returns_empty_default(self):
        path = os.path.join(self._tmp, "list.json")
        with open(path, "w") as fh:
            json.dump([{"a": 1}], fh)
        result = _load_corpus_index(path)
        self.assertEqual(result["entries"], [])

    def test_missing_entries_key_returns_empty_default(self):
        path = os.path.join(self._tmp, "no_entries.json")
        with open(path, "w") as fh:
            json.dump({"schema_version": "1"}, fh)
        result = _load_corpus_index(path)
        self.assertEqual(result["entries"], [])

    def test_entries_not_list_returns_empty_default(self):
        path = os.path.join(self._tmp, "bad_entries.json")
        with open(path, "w") as fh:
            json.dump({"schema_version": "1", "entries": "bad"}, fh)
        result = _load_corpus_index(path)
        self.assertEqual(result["entries"], [])

    def test_valid_existing_index_loaded(self):
        path = os.path.join(self._tmp, "index.json")
        original = {
            "schema_version": "1",
            "entries": [
                {"pr_number": 10, "repo": "a/b", "review_count": 3}
            ],
        }
        with open(path, "w") as fh:
            json.dump(original, fh)
        result = _load_corpus_index(path)
        self.assertEqual(len(result["entries"]), 1)
        self.assertEqual(result["entries"][0]["pr_number"], 10)

    def test_empty_file_returns_empty_default(self):
        path = os.path.join(self._tmp, "empty.json")
        with open(path, "w") as fh:
            fh.write("")
        result = _load_corpus_index(path)
        self.assertEqual(result["entries"], [])


# ---------------------------------------------------------------------------
# TestUpsertNew
# ---------------------------------------------------------------------------

class TestUpsertNew(unittest.TestCase):
    def _empty_index(self):
        return {"schema_version": _SCHEMA_VERSION, "entries": []}

    def test_creates_new_entry(self):
        index = self._empty_index()
        action = _upsert_corpus_entry(
            index, 42, "org/repo", "/path/bundle.json", 3, 2, 1, 4, _NOW
        )
        self.assertEqual(action, "created")
        self.assertEqual(len(index["entries"]), 1)

    def test_new_entry_fields(self):
        index = self._empty_index()
        _upsert_corpus_entry(
            index, 42, "org/repo", "/path/bundle.json", 3, 2, 1, 4, _NOW
        )
        entry = index["entries"][0]
        self.assertEqual(entry["pr_number"], 42)
        self.assertEqual(entry["repo"], "org/repo")
        self.assertEqual(entry["bundle_path"], "/path/bundle.json")
        self.assertEqual(entry["first_reviewed_at"], _NOW)
        self.assertEqual(entry["last_reviewed_at"], _NOW)
        self.assertEqual(entry["review_count"], 1)
        self.assertEqual(entry["findings_count"], 3)
        self.assertEqual(entry["smells_count"], 2)
        self.assertEqual(entry["blast_probes_count"], 1)
        self.assertEqual(entry["drift_bullets_count"], 4)

    def test_first_reviewed_equals_last_reviewed(self):
        index = self._empty_index()
        _upsert_corpus_entry(
            index, 1, "a/b", "/p", 0, 0, 0, 0, _NOW
        )
        entry = index["entries"][0]
        self.assertEqual(entry["first_reviewed_at"], entry["last_reviewed_at"])

    def test_review_count_is_one(self):
        index = self._empty_index()
        _upsert_corpus_entry(index, 1, "a/b", "/p", 0, 0, 0, 0, _NOW)
        self.assertEqual(index["entries"][0]["review_count"], 1)


# ---------------------------------------------------------------------------
# TestUpsertExisting
# ---------------------------------------------------------------------------

class TestUpsertExisting(unittest.TestCase):
    def _index_with_entry(self, pr_number=10, repo="a/b", review_count=1,
                           first_ts=_NOW):
        return {
            "schema_version": _SCHEMA_VERSION,
            "entries": [
                {
                    "pr_number": pr_number,
                    "repo": repo,
                    "bundle_path": "/old/path",
                    "first_reviewed_at": first_ts,
                    "last_reviewed_at": first_ts,
                    "review_count": review_count,
                    "findings_count": 0,
                    "smells_count": 0,
                    "blast_probes_count": 0,
                    "drift_bullets_count": 0,
                }
            ],
        }

    def test_returns_updated(self):
        index = self._index_with_entry()
        action = _upsert_corpus_entry(
            index, 10, "a/b", "/new/path", 5, 3, 2, 1, _NOW2
        )
        self.assertEqual(action, "updated")

    def test_review_count_incremented(self):
        index = self._index_with_entry(review_count=2)
        _upsert_corpus_entry(index, 10, "a/b", "/new/path", 5, 3, 2, 1, _NOW2)
        self.assertEqual(index["entries"][0]["review_count"], 3)

    def test_first_reviewed_at_preserved(self):
        index = self._index_with_entry(first_ts=_NOW)
        _upsert_corpus_entry(index, 10, "a/b", "/new/path", 5, 3, 2, 1, _NOW2)
        self.assertEqual(index["entries"][0]["first_reviewed_at"], _NOW)

    def test_last_reviewed_at_updated(self):
        index = self._index_with_entry(first_ts=_NOW)
        _upsert_corpus_entry(index, 10, "a/b", "/new/path", 5, 3, 2, 1, _NOW2)
        self.assertEqual(index["entries"][0]["last_reviewed_at"], _NOW2)

    def test_counts_refreshed(self):
        index = self._index_with_entry()
        _upsert_corpus_entry(index, 10, "a/b", "/new/path", 7, 4, 3, 5, _NOW2)
        entry = index["entries"][0]
        self.assertEqual(entry["findings_count"], 7)
        self.assertEqual(entry["smells_count"], 4)
        self.assertEqual(entry["blast_probes_count"], 3)
        self.assertEqual(entry["drift_bullets_count"], 5)

    def test_bundle_path_updated(self):
        index = self._index_with_entry()
        _upsert_corpus_entry(index, 10, "a/b", "/new/path", 0, 0, 0, 0, _NOW2)
        self.assertEqual(index["entries"][0]["bundle_path"], "/new/path")

    def test_entry_count_unchanged(self):
        index = self._index_with_entry()
        _upsert_corpus_entry(index, 10, "a/b", "/new/path", 0, 0, 0, 0, _NOW2)
        self.assertEqual(len(index["entries"]), 1)


# ---------------------------------------------------------------------------
# TestUpsertDifferentRepo
# ---------------------------------------------------------------------------

class TestUpsertDifferentRepo(unittest.TestCase):
    def test_same_pr_different_repo_creates_new_entry(self):
        index = {
            "schema_version": _SCHEMA_VERSION,
            "entries": [
                {
                    "pr_number": 42,
                    "repo": "org/repo-a",
                    "bundle_path": "/path/a",
                    "first_reviewed_at": _NOW,
                    "last_reviewed_at": _NOW,
                    "review_count": 1,
                    "findings_count": 0,
                    "smells_count": 0,
                    "blast_probes_count": 0,
                    "drift_bullets_count": 0,
                }
            ],
        }
        action = _upsert_corpus_entry(
            index, 42, "org/repo-b", "/path/b", 2, 1, 0, 0, _NOW2
        )
        self.assertEqual(action, "created")
        self.assertEqual(len(index["entries"]), 2)

    def test_different_pr_same_repo_creates_new_entry(self):
        index = {
            "schema_version": _SCHEMA_VERSION,
            "entries": [
                {
                    "pr_number": 1,
                    "repo": "org/repo",
                    "bundle_path": "/path/1",
                    "first_reviewed_at": _NOW,
                    "last_reviewed_at": _NOW,
                    "review_count": 1,
                    "findings_count": 0,
                    "smells_count": 0,
                    "blast_probes_count": 0,
                    "drift_bullets_count": 0,
                }
            ],
        }
        action = _upsert_corpus_entry(
            index, 2, "org/repo", "/path/2", 0, 0, 0, 0, _NOW2
        )
        self.assertEqual(action, "created")
        self.assertEqual(len(index["entries"]), 2)


# ---------------------------------------------------------------------------
# TestAtomicWrite
# ---------------------------------------------------------------------------

class TestAtomicWrite(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_no_temp_files_after_success(self):
        path = os.path.join(self._tmp, "index.json")
        index = {"schema_version": _SCHEMA_VERSION, "entries": []}
        _write_corpus_index(path, index)
        # No .tmp.json files should remain.
        tmp_files = [f for f in os.listdir(self._tmp) if f.endswith(".tmp.json")]
        self.assertEqual(tmp_files, [])

    def test_index_file_written_correctly(self):
        path = os.path.join(self._tmp, "index.json")
        index = {
            "schema_version": _SCHEMA_VERSION,
            "entries": [{"pr_number": 1}],
        }
        _write_corpus_index(path, index)
        with open(path, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
        self.assertEqual(loaded["entries"][0]["pr_number"], 1)


# ---------------------------------------------------------------------------
# TestRunHappyPath
# ---------------------------------------------------------------------------

class TestRunHappyPath(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 304
        self._state = _make_state(
            pr_number=self._pr_number,
            repo="org/module",
            findings=[{"severity": "high", "location": "x.py"}],
            smells=[{"name": "s"}],
            blast=[{"symbol": "foo"}],
            drift={"bullets": [{"id": "B1"}, {"id": "B2"}], "coverage_matrix": []},
        )
        _write_state_to_dir(self._tmp, self._state)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_returns_status_ok(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertEqual(result["status"], "ok")

    def test_bundle_path_is_file(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertTrue(os.path.isfile(result["bundle_path"]))

    def test_corpus_index_is_file(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertTrue(os.path.isfile(result["corpus_index_path"]))

    def test_bundle_path_under_pr_dir(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        expected = os.path.join(
            self._tmp, ".devforge", _PR_REVIEWS_DIR, str(self._pr_number)
        )
        self.assertTrue(result["bundle_path"].startswith(expected))

    def test_corpus_index_path_correct(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        expected = os.path.join(
            self._tmp, ".devforge", _PR_REVIEWS_DIR, _CORPUS_INDEX_FILENAME
        )
        self.assertEqual(result["corpus_index_path"], expected)

    def test_findings_count_in_result(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertEqual(result["findings_count"], 1)

    def test_review_count_in_result(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertEqual(result["review_count"], 1)


# ---------------------------------------------------------------------------
# TestRunCreatedEntry
# ---------------------------------------------------------------------------

class TestRunCreatedEntry(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        state = _make_state(pr_number=100, repo="new/repo")
        _write_state_to_dir(self._tmp, state)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_entry_action_created(self):
        result = run(self._tmp, 100, ".devforge")
        self.assertEqual(result["entry_action"], "created")

    def test_index_has_one_entry(self):
        result = run(self._tmp, 100, ".devforge")
        with open(result["corpus_index_path"], "r", encoding="utf-8") as fh:
            index = json.load(fh)
        self.assertEqual(len(index["entries"]), 1)

    def test_index_entry_pr_number(self):
        result = run(self._tmp, 100, ".devforge")
        with open(result["corpus_index_path"], "r", encoding="utf-8") as fh:
            index = json.load(fh)
        self.assertEqual(index["entries"][0]["pr_number"], 100)

    def test_index_entry_repo(self):
        result = run(self._tmp, 100, ".devforge")
        with open(result["corpus_index_path"], "r", encoding="utf-8") as fh:
            index = json.load(fh)
        self.assertEqual(index["entries"][0]["repo"], "new/repo")

    def test_index_schema_version(self):
        result = run(self._tmp, 100, ".devforge")
        with open(result["corpus_index_path"], "r", encoding="utf-8") as fh:
            index = json.load(fh)
        self.assertEqual(index["schema_version"], _SCHEMA_VERSION)


# ---------------------------------------------------------------------------
# TestRunUpdatedEntry
# ---------------------------------------------------------------------------

class TestRunUpdatedEntry(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 200
        state = _make_state(pr_number=self._pr_number, repo="upd/repo")
        _write_state_to_dir(self._tmp, state)
        # First run establishes the entry.
        run(self._tmp, self._pr_number, ".devforge")

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_second_run_returns_updated(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertEqual(result["entry_action"], "updated")

    def test_review_count_incremented(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertEqual(result["review_count"], 2)

    def test_entry_count_unchanged(self):
        result = run(self._tmp, self._pr_number, ".devforge")
        with open(result["corpus_index_path"], "r", encoding="utf-8") as fh:
            index = json.load(fh)
        self.assertEqual(len(index["entries"]), 1)

    def test_first_reviewed_at_preserved(self):
        # Read first_reviewed_at after first run.
        result1_path = os.path.join(
            self._tmp, ".devforge", _PR_REVIEWS_DIR, _CORPUS_INDEX_FILENAME
        )
        with open(result1_path, "r", encoding="utf-8") as fh:
            index1 = json.load(fh)
        first_ts = index1["entries"][0]["first_reviewed_at"]

        # Second run.
        run(self._tmp, self._pr_number, ".devforge")
        with open(result1_path, "r", encoding="utf-8") as fh:
            index2 = json.load(fh)
        self.assertEqual(index2["entries"][0]["first_reviewed_at"], first_ts)


# ---------------------------------------------------------------------------
# TestRunNoStateFile
# ---------------------------------------------------------------------------

class TestRunNoStateFile(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            run(self._tmp, 999, ".devforge")
        self.assertIn("state.json", str(ctx.exception))

    def test_error_message_mentions_intake(self):
        with self.assertRaises(ValueError) as ctx:
            run(self._tmp, 999, ".devforge")
        self.assertIn("intake", str(ctx.exception))


# ---------------------------------------------------------------------------
# TestCountsInIndex
# ---------------------------------------------------------------------------

class TestCountsInIndex(unittest.TestCase):
    """Verify index entry counts match actual state contents."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()
        self._pr_number = 50

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_findings_count(self):
        state = _make_state(
            pr_number=self._pr_number,
            findings=[{"severity": "low"}, {"severity": "high"}],
        )
        _write_state_to_dir(self._tmp, state)
        result = run(self._tmp, self._pr_number, ".devforge")
        self.assertEqual(result["findings_count"], 2)
        with open(result["corpus_index_path"], "r", encoding="utf-8") as fh:
            index = json.load(fh)
        self.assertEqual(index["entries"][0]["findings_count"], 2)

    def test_smells_count(self):
        state = _make_state(
            pr_number=self._pr_number,
            smells=[{"name": "s1"}, {"name": "s2"}, {"name": "s3"}],
        )
        _write_state_to_dir(self._tmp, state)
        result = run(self._tmp, self._pr_number, ".devforge")
        with open(result["corpus_index_path"], "r", encoding="utf-8") as fh:
            index = json.load(fh)
        self.assertEqual(index["entries"][0]["smells_count"], 3)

    def test_blast_probes_count(self):
        state = _make_state(
            pr_number=self._pr_number,
            blast=[{"symbol": "a"}, {"symbol": "b"}],
        )
        _write_state_to_dir(self._tmp, state)
        result = run(self._tmp, self._pr_number, ".devforge")
        with open(result["corpus_index_path"], "r", encoding="utf-8") as fh:
            index = json.load(fh)
        self.assertEqual(index["entries"][0]["blast_probes_count"], 2)

    def test_drift_bullets_count(self):
        state = _make_state(
            pr_number=self._pr_number,
            drift={"bullets": [{"id": "B1"}, {"id": "B2"}, {"id": "B3"}]},
        )
        _write_state_to_dir(self._tmp, state)
        result = run(self._tmp, self._pr_number, ".devforge")
        with open(result["corpus_index_path"], "r", encoding="utf-8") as fh:
            index = json.load(fh)
        self.assertEqual(index["entries"][0]["drift_bullets_count"], 3)


if __name__ == "__main__":
    unittest.main()
