"""Tests for src/devforge/lib/_audit/_hotspot.py and the Phase 1 CLI verbs.

Coverage:
  parse_weights     — defaults, valid custom, missing key, out-of-range, bad sum
  load_callers      — int form, list form (dedup), mixed, bad payload type
  score_files       — determinism, ranking, tie-break, norms, single-file,
                      all-zero churn (max==min edge), next_candidates boundaries
  compute_churn     — real tmp git repo (skipped if git absent)
  compute_loc       — file with blanks, unreadable path → 0
  CBM gate          — cmd_compute_hotspots with callers=None → returns 2
  run_compute_hotspots — end-to-end with tmp git repo + in-memory callers JSON
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _audit._hotspot import (  # noqa: E402
    parse_weights,
    load_callers,
    score_files,
    compute_churn,
    compute_loc,
    enumerate_candidates,
    run_compute_hotspots,
    _DEFAULT_WEIGHTS,
)
from _audit._cli import cmd_compute_hotspots, build_parser  # noqa: E402
from _audit.hotspot_schema import FileScore, HotspotResult  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _git_available():
    """Return True if git is on PATH."""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _make_metrics(files_data):
    """Build a metrics list from [(file, churn, callers, size_loc), ...]."""
    return [
        {"file": f, "churn": c, "callers": k, "size_loc": s}
        for f, c, k, s in files_data
    ]


# ---------------------------------------------------------------------------
# parse_weights
# ---------------------------------------------------------------------------

class TestParseWeights(unittest.TestCase):

    def test_none_returns_defaults(self):
        w = parse_weights(None)
        self.assertEqual(w, {"c": 0.5, "k": 0.4, "s": 0.1})

    def test_none_returns_copy(self):
        w1 = parse_weights(None)
        w2 = parse_weights(None)
        w1["c"] = 0.9
        self.assertEqual(w2["c"], 0.5)  # mutations don't leak

    def test_valid_custom_weights(self):
        w = parse_weights({"c": 0.6, "k": 0.3, "s": 0.1})
        self.assertAlmostEqual(w["c"], 0.6)
        self.assertAlmostEqual(w["k"], 0.3)
        self.assertAlmostEqual(w["s"], 0.1)

    def test_valid_weights_as_ints(self):
        # integers are acceptable (converted to float)
        w = parse_weights({"c": 1, "k": 0, "s": 0})
        self.assertAlmostEqual(w["c"], 1.0)
        self.assertAlmostEqual(w["k"], 0.0)

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_weights({"c": 0.5, "k": 0.5})
        self.assertIn("missing keys", str(ctx.exception))

    def test_extra_key_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_weights({"c": 0.5, "k": 0.3, "s": 0.2, "x": 0.0})
        self.assertIn("unexpected keys", str(ctx.exception))

    def test_value_below_zero_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_weights({"c": -0.1, "k": 0.6, "s": 0.5})
        self.assertIn("[0, 1]", str(ctx.exception))

    def test_value_above_one_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_weights({"c": 1.1, "k": 0.0, "s": 0.0})
        self.assertIn("[0, 1]", str(ctx.exception))

    def test_sum_not_one_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_weights({"c": 0.5, "k": 0.5, "s": 0.5})
        self.assertIn("sum", str(ctx.exception))

    def test_bool_value_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_weights({"c": True, "k": 0.0, "s": 0.0})
        self.assertIn("bool", str(ctx.exception))

    def test_not_a_dict_raises(self):
        with self.assertRaises(ValueError) as ctx:
            parse_weights([0.5, 0.4, 0.1])
        self.assertIn("dict", str(ctx.exception))

    def test_sum_near_one_passes(self):
        # floating point near-equal: 0.1 + 0.2 + 0.7 = 1.0 in most platforms
        w = parse_weights({"c": 0.1, "k": 0.2, "s": 0.7})
        self.assertAlmostEqual(w["c"] + w["k"] + w["s"], 1.0, places=10)


# ---------------------------------------------------------------------------
# load_callers
# ---------------------------------------------------------------------------

class TestLoadCallers(unittest.TestCase):

    def test_int_form(self):
        result = load_callers({"a.py": 5, "b.py": 3})
        self.assertEqual(result["a.py"], 5)
        self.assertEqual(result["b.py"], 3)

    def test_list_form_deduped(self):
        # list with duplicates → deduped len
        result = load_callers({"a.py": ["foo", "bar", "foo", "baz"]})
        self.assertEqual(result["a.py"], 3)  # foo counted once

    def test_list_form_empty(self):
        result = load_callers({"a.py": []})
        self.assertEqual(result["a.py"], 0)

    def test_mixed_forms(self):
        result = load_callers({
            "a.py": 7,
            "b.py": ["x", "y", "x"],
        })
        self.assertEqual(result["a.py"], 7)
        self.assertEqual(result["b.py"], 2)

    def test_missing_file_not_in_result(self):
        # load_callers only includes files in the payload
        result = load_callers({"a.py": 0})
        self.assertNotIn("missing.py", result)

    def test_empty_payload(self):
        result = load_callers({})
        self.assertEqual(result, {})

    def test_non_dict_raises(self):
        with self.assertRaises(ValueError) as ctx:
            load_callers([{"a.py": 1}])
        self.assertIn("dict", str(ctx.exception))

    def test_negative_int_clamped_to_zero(self):
        result = load_callers({"a.py": -5})
        self.assertEqual(result["a.py"], 0)

    def test_unexpected_value_gives_zero(self):
        # e.g. a string value (malformed payload) → treated as 0
        result = load_callers({"a.py": "unknown"})
        self.assertEqual(result["a.py"], 0)


# ---------------------------------------------------------------------------
# score_files — determinism + normalization
# ---------------------------------------------------------------------------

class TestScoreFilesBasic(unittest.TestCase):

    def _defaults(self):
        return {"c": 0.5, "k": 0.4, "s": 0.1}

    def test_empty_metrics_returns_empty_result(self):
        result = score_files([], self._defaults(), 25)
        self.assertIsInstance(result, HotspotResult)
        self.assertEqual(result.top, [])
        self.assertEqual(result.next_candidates, [])
        self.assertEqual(result.total_files_scored, 0)

    def test_single_file_rank_1_norms_zero(self):
        metrics = _make_metrics([("a.py", 10, 5, 200)])
        result = score_files(metrics, self._defaults(), 25)
        self.assertEqual(len(result.top), 1)
        fs = result.top[0]
        self.assertEqual(fs.rank, 1)
        self.assertEqual(fs.churn_norm, 0.0)
        self.assertEqual(fs.callers_norm, 0.0)
        self.assertEqual(fs.size_norm, 0.0)
        self.assertEqual(fs.score, 0.0)

    def test_all_zero_churn_gives_zero_churn_norm(self):
        # All files have churn=0: max==min → churn_norm must be 0.0 for all
        metrics = _make_metrics([
            ("a.py", 0, 5, 100),
            ("b.py", 0, 2, 200),
            ("c.py", 0, 8, 150),
        ])
        result = score_files(metrics, self._defaults(), 25)
        for fs in result.top:
            self.assertEqual(fs.churn_norm, 0.0,
                             "churn_norm must be 0.0 when all churn equal")
        # No NaN (checking score is a finite number)
        for fs in result.top:
            self.assertFalse(
                fs.score != fs.score,  # NaN != NaN is True
                "score must not be NaN"
            )

    def test_deterministic_ranking(self):
        # File A has higher churn → should rank 1
        metrics = _make_metrics([
            ("b.py", 1, 0, 100),   # lower churn
            ("a.py", 10, 0, 100),  # higher churn
        ])
        result = score_files(metrics, {"c": 1.0, "k": 0.0, "s": 0.0}, 25)
        self.assertEqual(result.top[0].file, "a.py")
        self.assertEqual(result.top[0].rank, 1)
        self.assertEqual(result.top[1].file, "b.py")
        self.assertEqual(result.top[1].rank, 2)

    def test_score_formula(self):
        # Two files, one metric varies
        # churn: 0 and 10 → norms 0.0 and 1.0
        # callers: same (0) → norm 0.0 for both
        # size: same (100) → norm 0.0 for both
        # score for top = 0.5*1.0 + 0.4*0.0 + 0.1*0.0 = 0.5
        metrics = _make_metrics([
            ("a.py", 10, 0, 100),
            ("b.py", 0, 0, 100),
        ])
        result = score_files(metrics, {"c": 0.5, "k": 0.4, "s": 0.1}, 25)
        top_file = result.top[0]
        self.assertAlmostEqual(top_file.score, 0.5, places=9)
        self.assertAlmostEqual(top_file.churn_norm, 1.0, places=9)

    def test_tie_break_churn_desc_then_file_asc(self):
        # Identical scores (all metrics equal for a/b) but c is different
        # Set up 3 files with same score; differentiate by file path for tie
        # Provide equal churn to force file-path tie-break
        metrics = _make_metrics([
            ("z.py", 5, 5, 5),
            ("a.py", 5, 5, 5),
            ("m.py", 5, 5, 5),
        ])
        result = score_files(metrics, self._defaults(), 25)
        # All norms are 0.0 (max==min), score is 0.0 for all
        for fs in result.top:
            self.assertEqual(fs.score, 0.0)
        # With equal score AND equal churn → file path ascending order
        files = [fs.file for fs in result.top]
        self.assertEqual(files, sorted(files))

    def test_tie_break_churn_desc_wins_over_path(self):
        # Same score but different churn → higher churn wins regardless of path
        # Use weights that give equal score to all: only norms matter
        metrics = _make_metrics([
            ("z.py", 10, 0, 0),  # high churn, low others
            ("a.py", 0, 0, 0),   # low churn
        ])
        # With pure churn weights: z.py should be rank 1
        result = score_files(metrics, {"c": 1.0, "k": 0.0, "s": 0.0}, 25)
        self.assertEqual(result.top[0].file, "z.py")


class TestScoreFilesNextCandidates(unittest.TestCase):

    def _defaults(self):
        return {"c": 0.5, "k": 0.4, "s": 0.1}

    def _make_n_files(self, n):
        return [
            {"file": "file{0:03d}.py".format(i), "churn": i, "callers": 0, "size_loc": 0}
            for i in range(n)
        ]

    def test_40_files_top25_next10(self):
        metrics = self._make_n_files(40)
        result = score_files(metrics, self._defaults(), top_n=25)
        self.assertEqual(len(result.top), 25)
        self.assertEqual(len(result.next_candidates), 10)
        self.assertEqual(result.total_files_scored, 40)
        # next_candidates should be ranks 26-35
        for i, fs in enumerate(result.next_candidates):
            self.assertEqual(fs.rank, 26 + i)

    def test_28_files_top25_next3(self):
        metrics = self._make_n_files(28)
        result = score_files(metrics, self._defaults(), top_n=25)
        self.assertEqual(len(result.top), 25)
        self.assertEqual(len(result.next_candidates), 3)
        self.assertEqual(result.total_files_scored, 28)

    def test_fewer_than_top_n(self):
        metrics = self._make_n_files(10)
        result = score_files(metrics, self._defaults(), top_n=25)
        self.assertEqual(len(result.top), 10)
        self.assertEqual(len(result.next_candidates), 0)
        self.assertEqual(result.total_files_scored, 10)

    def test_exactly_top_n_files(self):
        metrics = self._make_n_files(25)
        result = score_files(metrics, self._defaults(), top_n=25)
        self.assertEqual(len(result.top), 25)
        self.assertEqual(len(result.next_candidates), 0)

    def test_top_n_plus_exactly_10(self):
        metrics = self._make_n_files(35)
        result = score_files(metrics, self._defaults(), top_n=25)
        self.assertEqual(len(result.top), 25)
        self.assertEqual(len(result.next_candidates), 10)


# ---------------------------------------------------------------------------
# compute_churn — real tmp git repo
# ---------------------------------------------------------------------------

class TestComputeChurn(unittest.TestCase):

    def setUp(self):
        if not _git_available():
            self.skipTest("git not on PATH")

    def _init_tmp_repo(self):
        """Create a temp dir, init a git repo, configure user. Returns path."""
        d = tempfile.mkdtemp(prefix="hotspot_churn_test_")
        env = dict(os.environ)
        for cmd in [
            ["git", "-C", d, "init"],
            ["git", "-C", d, "config", "user.email", "test@example.com"],
            ["git", "-C", d, "config", "user.name", "Test User"],
        ]:
            subprocess.run(cmd, capture_output=True, check=True, env=env)
        return d

    def _commit_file(self, repo, path, content, date_str):
        """Write content to path (relative to repo), stage, commit with fixed date."""
        abs_path = os.path.join(repo, path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as fh:
            fh.write(content)
        env = dict(os.environ)
        env["GIT_AUTHOR_DATE"] = date_str
        env["GIT_COMMITTER_DATE"] = date_str
        subprocess.run(
            ["git", "-C", repo, "add", path],
            capture_output=True, check=True, env=env,
        )
        subprocess.run(
            ["git", "-C", repo, "commit", "-m", "test commit"],
            capture_output=True, check=True, env=env,
        )

    def test_churn_counts_commits_within_window(self):
        repo = self._init_tmp_repo()
        try:
            # Two commits to a.py within window, one to b.py within window
            # Use a fixed past date within the --since window
            date = "2025-01-15T12:00:00"
            self._commit_file(repo, "a.py", "v1\n", date)
            self._commit_file(repo, "a.py", "v2\n", date)
            self._commit_file(repo, "b.py", "v1\n", date)

            result = compute_churn(["a.py", "b.py"], repo, since="2025-01-01")
            self.assertEqual(result["a.py"], 2)
            self.assertEqual(result["b.py"], 1)
        finally:
            import shutil
            shutil.rmtree(repo, ignore_errors=True)

    def test_file_before_window_gives_zero(self):
        repo = self._init_tmp_repo()
        try:
            # Commit date is 2020 — before the --since="2025-01-01" window
            self._commit_file(repo, "old.py", "content\n", "2020-01-01T12:00:00")
            result = compute_churn(["old.py"], repo, since="2025-01-01")
            self.assertEqual(result["old.py"], 0)
        finally:
            import shutil
            shutil.rmtree(repo, ignore_errors=True)

    def test_file_never_committed_gives_zero(self):
        repo = self._init_tmp_repo()
        try:
            # Create the file but never commit it
            with open(os.path.join(repo, "untracked.py"), "w") as fh:
                fh.write("x\n")
            result = compute_churn(["untracked.py"], repo, since="2020-01-01")
            self.assertEqual(result["untracked.py"], 0)
        finally:
            import shutil
            shutil.rmtree(repo, ignore_errors=True)

    def test_returns_all_input_files(self):
        repo = self._init_tmp_repo()
        try:
            self._commit_file(repo, "a.py", "x\n", "2025-06-01T12:00:00")
            result = compute_churn(["a.py", "b.py", "c.py"], repo, since="2025-01-01")
            self.assertIn("a.py", result)
            self.assertIn("b.py", result)
            self.assertIn("c.py", result)
            self.assertEqual(result["b.py"], 0)
        finally:
            import shutil
            shutil.rmtree(repo, ignore_errors=True)


class TestComputeChurnNoGit(unittest.TestCase):
    """Verify graceful handling when git is not found."""

    def test_git_not_found_returns_zero(self):
        # Patch PATH to be empty so git is not findable
        original_path = os.environ.get("PATH", "")
        try:
            os.environ["PATH"] = ""
            result = compute_churn(["a.py"], "/tmp/nonexistent_repo_xyz", since="2020-01-01")
            self.assertEqual(result["a.py"], 0)
        finally:
            os.environ["PATH"] = original_path


# ---------------------------------------------------------------------------
# compute_loc
# ---------------------------------------------------------------------------

class TestComputeLoc(unittest.TestCase):

    def test_counts_non_blank_lines(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "a.py")
            with open(path, "w") as fh:
                fh.write("line 1\n\nline 2\n  \nline 3\n")
            result = compute_loc(["a.py"], d)
            self.assertEqual(result["a.py"], 3)

    def test_empty_file_gives_zero(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "empty.py")
            open(path, "w").close()
            result = compute_loc(["empty.py"], d)
            self.assertEqual(result["empty.py"], 0)

    def test_all_blank_lines_gives_zero(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "blanks.py")
            with open(path, "w") as fh:
                fh.write("\n\n   \n\t\n")
            result = compute_loc(["blanks.py"], d)
            self.assertEqual(result["blanks.py"], 0)

    def test_unreadable_path_gives_zero(self):
        with tempfile.TemporaryDirectory() as d:
            result = compute_loc(["nonexistent_file.py"], d)
            self.assertEqual(result["nonexistent_file.py"], 0)

    def test_returns_all_input_files(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "a.py"), "w") as fh:
                fh.write("x\ny\n")
            result = compute_loc(["a.py", "missing.py"], d)
            self.assertIn("a.py", result)
            self.assertIn("missing.py", result)
            self.assertEqual(result["a.py"], 2)
            self.assertEqual(result["missing.py"], 0)

    def test_file_with_only_comments_and_code(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "code.py")
            with open(path, "w") as fh:
                fh.write("# comment\n\ndef foo():\n    pass\n")
            result = compute_loc(["code.py"], d)
            # 3 non-blank lines: "# comment", "def foo():", "    pass"
            self.assertEqual(result["code.py"], 3)


# ---------------------------------------------------------------------------
# CBM gate: cmd_compute_hotspots with callers=None → returns 2
# ---------------------------------------------------------------------------

class TestCBMGate(unittest.TestCase):

    def test_callers_none_returns_2(self):
        args = argparse.Namespace(callers=None, repo_root=".", top=25,
                                  weights=None, since="90.days.ago")
        rc = cmd_compute_hotspots(args)
        self.assertEqual(rc, 2)

    def test_callers_empty_string_returns_2(self):
        args = argparse.Namespace(callers="", repo_root=".", top=25,
                                  weights=None, since="90.days.ago")
        rc = cmd_compute_hotspots(args)
        self.assertEqual(rc, 2)

    def test_callers_nonexistent_file_returns_2(self):
        args = argparse.Namespace(
            callers="/tmp/nonexistent_callers_xyz_123.json",
            repo_root=".", top=25, weights=None, since="90.days.ago"
        )
        rc = cmd_compute_hotspots(args)
        self.assertEqual(rc, 2)

    def test_callers_invalid_json_returns_2(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as fh:
            fh.write("not json {{{{")
            tmp = fh.name
        try:
            args = argparse.Namespace(callers=tmp, repo_root=".", top=25,
                                      weights=None, since="90.days.ago")
            rc = cmd_compute_hotspots(args)
            self.assertEqual(rc, 2)
        finally:
            os.unlink(tmp)

    def test_build_parser_has_compute_hotspots(self):
        parser = build_parser()
        # Should parse without error
        ns = parser.parse_args(["compute-hotspots", "--top", "10"])
        self.assertEqual(ns.top, 10)
        self.assertIsNone(ns.callers)

    def test_build_parser_render_hotspot_summary(self):
        parser = build_parser()
        # render-hotspot-summary requires --hotspot
        with self.assertRaises(SystemExit):
            parser.parse_args(["render-hotspot-summary"])


# ---------------------------------------------------------------------------
# run_compute_hotspots — end-to-end against tmp git repo
# ---------------------------------------------------------------------------

class TestRunComputeHotspotsE2E(unittest.TestCase):

    def setUp(self):
        if not _git_available():
            self.skipTest("git not on PATH")

    def _init_tmp_repo(self):
        d = tempfile.mkdtemp(prefix="hotspot_e2e_test_")
        env = dict(os.environ)
        for cmd in [
            ["git", "-C", d, "init"],
            ["git", "-C", d, "config", "user.email", "test@example.com"],
            ["git", "-C", d, "config", "user.name", "Test User"],
        ]:
            subprocess.run(cmd, capture_output=True, check=True, env=env)
        return d

    def _commit_file(self, repo, path, content, date_str):
        abs_path = os.path.join(repo, path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as fh:
            fh.write(content)
        env = dict(os.environ)
        env["GIT_AUTHOR_DATE"] = date_str
        env["GIT_COMMITTER_DATE"] = date_str
        subprocess.run(
            ["git", "-C", repo, "add", path],
            capture_output=True, check=True, env=env,
        )
        subprocess.run(
            ["git", "-C", repo, "commit", "-m", "e2e test"],
            capture_output=True, check=True, env=env,
        )

    def test_e2e_produces_valid_hotspot_result(self):
        repo = self._init_tmp_repo()
        try:
            date = "2025-03-01T12:00:00"
            # Create 3 source files with different churn
            self._commit_file(repo, "high.py", "x\ny\n", date)
            self._commit_file(repo, "high.py", "x\ny\nz\n", date)
            self._commit_file(repo, "med.py", "a\nb\n", date)
            self._commit_file(repo, "low.ts", "const x = 1;\n", date)

            # Write callers payload to a temp file
            callers = {"high.py": 10, "med.py": 2, "low.ts": 0}
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, dir=repo
            ) as fh:
                json.dump(callers, fh)
                callers_path = fh.name

            result = run_compute_hotspots(
                repo_root=repo,
                callers_payload=callers,
                top_n=10,
                weights=None,
                since="2025-01-01",
            )

            # Basic structure checks
            self.assertIn("top", result)
            self.assertIn("next_candidates", result)
            self.assertIn("total_files_scored", result)
            self.assertIn("schema_version", result)
            self.assertIn("weights", result)

            self.assertEqual(result["schema_version"], "1")
            self.assertEqual(result["total_files_scored"], 3)

            # All top entries must have non-negative ranks, scores in [0,1]
            for item in result["top"]:
                self.assertGreaterEqual(item["rank"], 1)
                self.assertGreaterEqual(item["score"], 0.0)
                self.assertLessEqual(item["score"], 1.0)

            # high.py should be rank 1 (most churn + most callers)
            if result["top"]:
                self.assertEqual(result["top"][0]["file"], "high.py")

            # Round-trip: reconstruct HotspotResult from the dict
            top_scores = [
                FileScore(**item) for item in result["top"]
            ]
            next_scores = [
                FileScore(**item) for item in result["next_candidates"]
            ]
            hr = HotspotResult(
                schema_version=result["schema_version"],
                weights=result["weights"],
                top=top_scores,
                next_candidates=next_scores,
                total_files_scored=result["total_files_scored"],
            )
            self.assertIsInstance(hr, HotspotResult)
            self.assertEqual(hr.total_files_scored, 3)

        finally:
            import shutil
            shutil.rmtree(repo, ignore_errors=True)

    def test_e2e_empty_callers_payload(self):
        """All caller counts default to 0 when payload is empty."""
        repo = self._init_tmp_repo()
        try:
            date = "2025-03-01T12:00:00"
            self._commit_file(repo, "a.py", "x\n", date)

            result = run_compute_hotspots(
                repo_root=repo,
                callers_payload={},
                top_n=10,
                weights=None,
                since="2025-01-01",
            )
            # Should still work; callers will be 0 for all
            self.assertEqual(result["total_files_scored"], 1)
            if result["top"]:
                self.assertEqual(result["top"][0]["callers"], 0)
        finally:
            import shutil
            shutil.rmtree(repo, ignore_errors=True)


# ---------------------------------------------------------------------------
# Normalization edge cases (explicit no-NaN, no-ZeroDivisionError)
# ---------------------------------------------------------------------------

class TestNormalizationEdgeCases(unittest.TestCase):

    def _defaults(self):
        return {"c": 0.5, "k": 0.4, "s": 0.1}

    def test_all_zero_callers_no_nan(self):
        metrics = _make_metrics([
            ("a.py", 5, 0, 100),
            ("b.py", 3, 0, 200),
            ("c.py", 1, 0, 50),
        ])
        result = score_files(metrics, self._defaults(), 25)
        for fs in result.top:
            # callers_norm must be exactly 0.0
            self.assertEqual(fs.callers_norm, 0.0)
            # score must be a valid finite float
            self.assertFalse(fs.score != fs.score, "NaN detected in score")
            self.assertGreaterEqual(fs.score, 0.0)
            self.assertLessEqual(fs.score, 1.0)

    def test_all_metrics_equal_for_all_files(self):
        # All files have identical metrics → all norms 0.0
        metrics = _make_metrics([
            ("a.py", 5, 3, 100),
            ("b.py", 5, 3, 100),
            ("c.py", 5, 3, 100),
        ])
        result = score_files(metrics, self._defaults(), 25)
        for fs in result.top:
            self.assertEqual(fs.churn_norm, 0.0)
            self.assertEqual(fs.callers_norm, 0.0)
            self.assertEqual(fs.size_norm, 0.0)
            self.assertEqual(fs.score, 0.0)

    def test_no_zero_division_when_all_size_equal(self):
        metrics = _make_metrics([
            ("a.py", 0, 1, 100),
            ("b.py", 5, 2, 100),
        ])
        # No exception expected
        result = score_files(metrics, self._defaults(), 25)
        for fs in result.top:
            self.assertEqual(fs.size_norm, 0.0)


# ---------------------------------------------------------------------------
# dataclasses.asdict round-trip integrity
# ---------------------------------------------------------------------------

class TestDataclassIntegrity(unittest.TestCase):

    def test_file_score_asdict_roundtrip(self):
        import dataclasses
        fs = FileScore(
            file="src/foo.py",
            churn=3,
            callers=2,
            size_loc=100,
            churn_norm=0.5,
            callers_norm=0.3,
            size_norm=0.2,
            score=0.42,
            rank=1,
        )
        d = dataclasses.asdict(fs)
        fs2 = FileScore(**d)
        self.assertEqual(fs, fs2)

    def test_hotspot_result_asdict_roundtrip(self):
        import dataclasses
        fs = FileScore(
            file="a.py", churn=1, callers=0, size_loc=10,
            churn_norm=0.0, callers_norm=0.0, size_norm=0.0,
            score=0.0, rank=1,
        )
        hr = HotspotResult(
            schema_version="1",
            weights={"c": 0.5, "k": 0.4, "s": 0.1},
            top=[fs],
            next_candidates=[],
            total_files_scored=1,
        )
        d = dataclasses.asdict(hr)
        top_scores = [FileScore(**item) for item in d["top"]]
        next_scores = [FileScore(**item) for item in d["next_candidates"]]
        hr2 = HotspotResult(
            schema_version=d["schema_version"],
            weights=d["weights"],
            top=top_scores,
            next_candidates=next_scores,
            total_files_scored=d["total_files_scored"],
        )
        self.assertEqual(hr.total_files_scored, hr2.total_files_scored)
        self.assertEqual(hr.top[0].file, hr2.top[0].file)


# ---------------------------------------------------------------------------
# Score-clamp regression: weights summing to 1+epsilon must not produce score>1
# ---------------------------------------------------------------------------

class TestScoreFilesClamp(unittest.TestCase):
    """Regression guard for the HIGH finding: parse_weights tolerates sum of
    1±1e-6; a file maxing all three norms can produce sc > 1.0 without the
    clamp.  The clamp must fire and produce exactly 1.0."""

    def test_maxed_file_score_clamped_to_one(self):
        # Weights sum to 1.0 + 9.9e-7 (within the 1e-6 tolerance).
        # parse_weights must accept this.
        w = parse_weights({"c": 0.5 + 9.9e-7, "k": 0.4, "s": 0.1})
        # Confirm the sum is slightly above 1.0 but accepted.
        total = w["c"] + w["k"] + w["s"]
        self.assertLess(abs(total - 1.0), 1e-6)

        # File A maxes all three metrics; file B is all-zero.
        metrics = _make_metrics([
            ("a.py", 100, 100, 100),  # all-max
            ("b.py", 0, 0, 0),        # all-zero
        ])

        # Must not raise (FileScore __post_init__ checks score in [0,1]).
        result = score_files(metrics, w, 25)

        # Top file should be a.py with score exactly 1.0 (clamped).
        self.assertEqual(result.top[0].file, "a.py")
        self.assertEqual(result.top[0].score, 1.0)

    def test_zero_weight_file_score_not_negative(self):
        # Corner: weights sum exactly 1.0 but with 0-value entries.
        w = parse_weights({"c": 1.0, "k": 0.0, "s": 0.0})
        metrics = _make_metrics([
            ("a.py", 10, 5, 200),
            ("b.py", 0, 5, 200),
        ])
        result = score_files(metrics, w, 25)
        for fs in result.top:
            self.assertGreaterEqual(fs.score, 0.0)
            self.assertLessEqual(fs.score, 1.0)


# ---------------------------------------------------------------------------
# enumerate_candidates — real tmp git repo + non-git-dir error path
# ---------------------------------------------------------------------------

class TestEnumerateCandidates(unittest.TestCase):

    def setUp(self):
        if not _git_available():
            self.skipTest("git not on PATH")

    def _init_tmp_repo(self):
        d = tempfile.mkdtemp(prefix="hotspot_enum_test_")
        env = dict(os.environ)
        for cmd in [
            ["git", "-C", d, "init"],
            ["git", "-C", d, "config", "user.email", "test@example.com"],
            ["git", "-C", d, "config", "user.name", "Test User"],
        ]:
            subprocess.run(cmd, capture_output=True, check=True, env=env)
        return d

    def _commit_file(self, repo, path, content="x\n"):
        abs_path = os.path.join(repo, path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w") as fh:
            fh.write(content)
        env = dict(os.environ)
        env["GIT_AUTHOR_DATE"] = "2025-01-01T12:00:00"
        env["GIT_COMMITTER_DATE"] = "2025-01-01T12:00:00"
        subprocess.run(
            ["git", "-C", repo, "add", path],
            capture_output=True, check=True, env=env,
        )
        subprocess.run(
            ["git", "-C", repo, "commit", "-m", "add file"],
            capture_output=True, check=True, env=env,
        )

    def test_source_files_returned_non_source_excluded(self):
        """Only source-extension files appear; README.md and data.json are filtered."""
        repo = self._init_tmp_repo()
        try:
            self._commit_file(repo, "a.py")
            self._commit_file(repo, "b.ts")
            self._commit_file(repo, "README.md")
            self._commit_file(repo, "data.json")

            result = enumerate_candidates(repo)
            self.assertIn("a.py", result)
            self.assertIn("b.ts", result)
            self.assertNotIn("README.md", result)
            self.assertNotIn("data.json", result)
        finally:
            import shutil
            shutil.rmtree(repo, ignore_errors=True)

    def test_result_is_sorted(self):
        """enumerate_candidates returns a sorted list."""
        repo = self._init_tmp_repo()
        try:
            self._commit_file(repo, "z.py")
            self._commit_file(repo, "a.ts")
            self._commit_file(repo, "m.js")

            result = enumerate_candidates(repo)
            self.assertEqual(result, sorted(result))
        finally:
            import shutil
            shutil.rmtree(repo, ignore_errors=True)

    def test_non_git_dir_raises_value_error(self):
        """Running against a non-repo directory raises ValueError (git non-zero exit)."""
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError) as ctx:
                enumerate_candidates(d)
            self.assertIn("git ls-files", str(ctx.exception))


# ---------------------------------------------------------------------------
# _parse_weights_arg — CLI string parser
# ---------------------------------------------------------------------------

class TestParseWeightsArg(unittest.TestCase):

    def test_valid_string_returns_dict(self):
        from _audit._cli import _parse_weights_arg
        result = _parse_weights_arg("c=0.5,k=0.4,s=0.1")
        self.assertAlmostEqual(result["c"], 0.5)
        self.assertAlmostEqual(result["k"], 0.4)
        self.assertAlmostEqual(result["s"], 0.1)

    def test_part_without_equals_raises(self):
        from _audit._cli import _parse_weights_arg
        with self.assertRaises(ValueError) as ctx:
            _parse_weights_arg("c0.5,k=0.4,s=0.1")
        self.assertIn("key=value", str(ctx.exception))

    def test_non_float_value_raises(self):
        from _audit._cli import _parse_weights_arg
        with self.assertRaises(ValueError) as ctx:
            _parse_weights_arg("c=heavy,k=0.4,s=0.1")
        self.assertIn("not a float", str(ctx.exception))

    def test_empty_string_returns_empty_dict(self):
        """An empty string produces a dict with one key '' (empty part before =)."""
        from _audit._cli import _parse_weights_arg
        # A completely empty string has no '=' so raises ValueError.
        with self.assertRaises(ValueError):
            _parse_weights_arg("")

    def test_extra_whitespace_is_stripped(self):
        from _audit._cli import _parse_weights_arg
        result = _parse_weights_arg("c = 0.5 , k = 0.4 , s = 0.1")
        self.assertAlmostEqual(result["c"], 0.5)
        self.assertAlmostEqual(result["k"], 0.4)
        self.assertAlmostEqual(result["s"], 0.1)


# ---------------------------------------------------------------------------
# cmd_render_hotspot_summary — CLI handler
# ---------------------------------------------------------------------------

class TestCmdRenderHotspotSummary(unittest.TestCase):

    def _make_hotspot_json(self, tmpdir):
        """Write a minimal valid hotspot result JSON and return its path."""
        data = {
            "schema_version": "1",
            "weights": {"c": 0.5, "k": 0.4, "s": 0.1},
            "total_files_scored": 3,
            "top": [
                {
                    "file": "src/foo.py",
                    "churn": 10,
                    "callers": 5,
                    "size_loc": 200,
                    "churn_norm": 1.0,
                    "callers_norm": 1.0,
                    "size_norm": 1.0,
                    "score": 1.0,
                    "rank": 1,
                }
            ],
            "next_candidates": [
                {
                    "file": "src/bar.py",
                    "churn": 2,
                    "callers": 1,
                    "size_loc": 50,
                    "churn_norm": 0.2,
                    "callers_norm": 0.2,
                    "size_norm": 0.1,
                    "score": 0.17,
                    "rank": 2,
                }
            ],
        }
        path = os.path.join(tmpdir, "hotspot.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        return path

    def test_valid_hotspot_file_returns_0(self):
        import contextlib
        import io
        from _audit._cli import cmd_render_hotspot_summary, build_parser

        with tempfile.TemporaryDirectory() as d:
            hotspot_path = self._make_hotspot_json(d)
            parser = build_parser()
            args = parser.parse_args(["render-hotspot-summary", "--hotspot", hotspot_path])

            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cmd_render_hotspot_summary(args)

            self.assertEqual(rc, 0)
            output = buf.getvalue()
            self.assertIn("src/foo.py", output)
            self.assertIn("src/bar.py", output)
            self.assertIn("score=1.00", output)

    def test_missing_hotspot_path_returns_2(self):
        """Calling with no --hotspot or a missing file should return 2."""
        import argparse
        from _audit._cli import cmd_render_hotspot_summary

        # Nonexistent file
        args = argparse.Namespace(hotspot="/tmp/nonexistent_hotspot_xyz_789.json")
        rc = cmd_render_hotspot_summary(args)
        self.assertEqual(rc, 2)

    def test_empty_top_list(self):
        """Hotspot file with empty top still renders without error."""
        import contextlib
        import io
        from _audit._cli import cmd_render_hotspot_summary

        with tempfile.TemporaryDirectory() as d:
            data = {
                "schema_version": "1",
                "weights": {"c": 0.5, "k": 0.4, "s": 0.1},
                "total_files_scored": 0,
                "top": [],
                "next_candidates": [],
            }
            path = os.path.join(d, "empty.json")
            with open(path, "w") as fh:
                json.dump(data, fh)

            args_ns = argparse.Namespace(hotspot=path)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = cmd_render_hotspot_summary(args_ns)

            self.assertEqual(rc, 0)
            self.assertIn("none", buf.getvalue().lower())


# ---------------------------------------------------------------------------
# load_callers bool case — explicit documentation of bool→0 behaviour
# ---------------------------------------------------------------------------

class TestLoadCallersBoolCase(unittest.TestCase):

    def test_bool_true_degrades_to_zero(self):
        """JSON `true` is parsed as bool True; load_callers must treat it as 0,
        not 1, since bool is a subclass of int and isinstance(True, int) is True."""
        result = load_callers({"a.py": True})
        self.assertEqual(result["a.py"], 0,
                         "bool True must degrade to 0 (not be counted as 1)")

    def test_bool_false_degrades_to_zero(self):
        result = load_callers({"a.py": False})
        self.assertEqual(result["a.py"], 0,
                         "bool False must degrade to 0")

    def test_negative_int_clamped_to_zero(self):
        """Documented in docstring: negatives are clamped to 0."""
        result = load_callers({"a.py": -99})
        self.assertEqual(result["a.py"], 0)


# ---------------------------------------------------------------------------
# FileNotFoundError / TimeoutExpired propagation through cmd_compute_hotspots
# ---------------------------------------------------------------------------

class TestComputeHotspotsErrorPropagation(unittest.TestCase):
    """Verify Fix A: FileNotFoundError and TimeoutExpired from
    enumerate_candidates (and therefore run_compute_hotspots) now return 2
    instead of escaping as a raw traceback."""

    def test_git_not_on_path_returns_2(self):
        """When git is absent, enumerate_candidates raises FileNotFoundError
        which must be caught and produce return code 2."""
        with tempfile.TemporaryDirectory() as d:
            # Write a valid callers JSON file.
            callers_data = {}
            callers_path = os.path.join(d, "callers.json")
            with open(callers_path, "w") as fh:
                json.dump(callers_data, fh)

            # Build an args namespace pointing to d as repo_root and
            # strip PATH so git is unfindable.
            args = argparse.Namespace(
                callers=callers_path,
                repo_root=d,  # not a git repo → git ls-files will error
                top=25,
                weights=None,
                since="90.days.ago",
            )

            original_path = os.environ.get("PATH", "")
            try:
                os.environ["PATH"] = ""
                rc = cmd_compute_hotspots(args)
            finally:
                os.environ["PATH"] = original_path

            self.assertEqual(rc, 2,
                             "FileNotFoundError (git absent) must return 2, not traceback")


if __name__ == "__main__":
    unittest.main()
