"""Tests for src/devforge/lib/_pr_review/_cli.py.

Coverage:
  build_parser — returns ArgumentParser; all 11 subcommands registered.
  main — no subcommand → exit 2.
  Step 2 verbs (ensure-cbm-index, detect-forge-state): exit 0, valid JSON.
  Step 3 verb (intake): args registered, no-longer-stub smoke test.
  Step 4 verb (detect-smells): args registered, smoke test with synthetic state.
  The 7 remaining stub verbs: exit 1 + correct "not yet implemented" message.
"""

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "pr_review_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._cli import build_parser, main  # noqa: E402


# All 11 verbs with their expected plan-step numbers.
# Used for --help coverage check only; stub assertion uses _STUB_VERB_STEP.
_VERB_STEP = [
    ("ensure-cbm-index", 2),
    ("detect-forge-state", 2),
    ("intake", 3),
    ("detect-smells", 4),
    ("compute-blast-radius", 5),
    ("bundle-context", 6),
    ("import-handoffs", 6),
    ("check-scope-drift", 7),
    ("dispatch-review", 8),
    ("finalize-output", 9),
    ("append-to-replay-corpus", 9),
]

# The 7 still-stub verbs (Steps 5-9); intake (Step 3) + detect-smells (Step 4)
# are now implemented.
_STUB_VERB_STEP = [
    ("compute-blast-radius", 5),
    ("bundle-context", 6),
    ("import-handoffs", 6),
    ("check-scope-drift", 7),
    ("dispatch-review", 8),
    ("finalize-output", 9),
    ("append-to-replay-corpus", 9),
]


def _run_helper(argv):
    """Invoke pr_review_helper.py with argv as a subprocess."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(argv),
        capture_output=True,
        text=True,
        check=False,
    )


class TestBuildParser(unittest.TestCase):
    def test_returns_argument_parser(self):
        parser = build_parser()
        self.assertIsInstance(parser, argparse.ArgumentParser)

    def test_all_11_verbs_registered(self):
        """Each verb can be parsed without argparse raising SystemExit.

        intake requires --pr and --repo; detect-smells requires --pr; supply
        minimal valid values for those.
        """
        parser = build_parser()
        for verb, _ in _VERB_STEP:
            with self.subTest(verb=verb):
                if verb == "intake":
                    argv = [verb, "--pr", "1", "--repo", "foo/bar"]
                elif verb == "detect-smells":
                    argv = [verb, "--pr", "1"]
                else:
                    argv = [verb]
                args = parser.parse_args(argv)
                self.assertEqual(args.subcommand, verb)

    def test_devforge_dir_default(self):
        parser = build_parser()
        args = parser.parse_args(["intake", "--pr", "1", "--repo", "foo/bar"])
        self.assertEqual(args.devforge_dir, ".devforge")

    def test_devforge_dir_override(self):
        parser = build_parser()
        args = parser.parse_args(
            ["--devforge-dir", "/tmp/forge", "intake", "--pr", "1", "--repo", "foo/bar"]
        )
        self.assertEqual(args.devforge_dir, "/tmp/forge")

    def test_no_subcommand_sets_no_func(self):
        """With no subcommand, args.func is absent (dispatch returns 2)."""
        parser = build_parser()
        args = parser.parse_args([])
        self.assertFalse(hasattr(args, "func"))

    def test_step2_verbs_have_target_arg(self):
        """ensure-cbm-index and detect-forge-state accept --target."""
        parser = build_parser()
        for verb in ("ensure-cbm-index", "detect-forge-state"):
            with self.subTest(verb=verb):
                args = parser.parse_args([verb, "--target", "/some/path"])
                self.assertEqual(args.target, "/some/path")

    def test_stub_verbs_do_not_have_target_arg(self):
        """Stub verbs (steps 5-9) do not accept --target yet."""
        parser = build_parser()
        for verb, _ in _STUB_VERB_STEP:
            with self.subTest(verb=verb):
                with self.assertRaises(SystemExit):
                    parser.parse_args([verb, "--target", "/x"])

    def test_detect_smells_has_pr_arg(self):
        """detect-smells accepts --pr (int, required)."""
        parser = build_parser()
        args = parser.parse_args(["detect-smells", "--pr", "42"])
        self.assertEqual(args.pr, 42)

    def test_detect_smells_has_target_arg(self):
        """detect-smells accepts --target."""
        parser = build_parser()
        args = parser.parse_args(
            ["detect-smells", "--pr", "1", "--target", "/some/path"]
        )
        self.assertEqual(args.target, "/some/path")

    def test_detect_smells_requires_pr(self):
        """detect-smells without --pr exits non-zero."""
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["detect-smells"])

    def test_intake_has_required_args(self):
        """intake accepts --pr (int, required) and --repo (required)."""
        parser = build_parser()
        args = parser.parse_args(["intake", "--pr", "42", "--repo", "acme/app"])
        self.assertEqual(args.pr, 42)
        self.assertEqual(args.repo, "acme/app")

    def test_intake_has_target_arg(self):
        """intake accepts --target."""
        parser = build_parser()
        args = parser.parse_args(
            ["intake", "--pr", "1", "--repo", "foo/bar", "--target", "/some/path"]
        )
        self.assertEqual(args.target, "/some/path")

    def test_intake_ticket_text_arg(self):
        """intake accepts --ticket-text."""
        parser = build_parser()
        args = parser.parse_args(
            ["intake", "--pr", "1", "--repo", "foo/bar", "--ticket-text", "Fix spinner"]
        )
        self.assertEqual(args.ticket_text, "Fix spinner")
        self.assertIsNone(args.ticket_file)

    def test_intake_ticket_file_arg(self):
        """intake accepts --ticket-file."""
        parser = build_parser()
        args = parser.parse_args(
            ["intake", "--pr", "1", "--repo", "foo/bar", "--ticket-file", "/tmp/ticket.txt"]
        )
        self.assertEqual(args.ticket_file, "/tmp/ticket.txt")
        self.assertIsNone(args.ticket_text)

    def test_intake_ticket_text_and_file_mutually_exclusive(self):
        """--ticket-text and --ticket-file are mutually exclusive."""
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args([
                "intake", "--pr", "1", "--repo", "foo/bar",
                "--ticket-text", "x", "--ticket-file", "/tmp/t.txt",
            ])

    def test_intake_requires_pr(self):
        """intake without --pr exits non-zero."""
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["intake", "--repo", "foo/bar"])

    def test_intake_requires_repo(self):
        """intake without --repo exits non-zero."""
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["intake", "--pr", "1"])


class TestMainDispatch(unittest.TestCase):
    def test_no_subcommand_returns_2(self):
        code = main([])
        self.assertEqual(code, 2)

    def test_stub_verb_returns_1(self):
        """Any remaining stub verb returns 1 (not yet implemented)."""
        code = main(["compute-blast-radius"])
        self.assertEqual(code, 1)


class TestStep2VerbsViaCLI(unittest.TestCase):
    """ensure-cbm-index and detect-forge-state: exit 0, valid JSON output."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_ensure_cbm_index_exits_0(self):
        result = _run_helper(["ensure-cbm-index", "--target", self._tmp])
        self.assertEqual(
            result.returncode,
            0,
            "ensure-cbm-index: expected exit 0, got {0}\nstderr={1}".format(
                result.returncode, result.stderr
            ),
        )

    def test_ensure_cbm_index_stdout_is_valid_json(self):
        result = _run_helper(["ensure-cbm-index", "--target", self._tmp])
        self.assertEqual(result.returncode, 0)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail(
                "ensure-cbm-index stdout is not valid JSON: {0}\nstdout={1}".format(
                    exc, result.stdout
                )
            )
        self.assertIn("status", data)
        self.assertIn("next_action", data)
        self.assertIn("target_path", data)
        self.assertIn("cbm_state_token", data)

    def test_detect_forge_state_exits_0(self):
        result = _run_helper(["detect-forge-state", "--target", self._tmp])
        self.assertEqual(
            result.returncode,
            0,
            "detect-forge-state: expected exit 0, got {0}\nstderr={1}".format(
                result.returncode, result.stderr
            ),
        )

    def test_detect_forge_state_stdout_is_valid_json(self):
        result = _run_helper(["detect-forge-state", "--target", self._tmp])
        self.assertEqual(result.returncode, 0)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail(
                "detect-forge-state stdout is not valid JSON: {0}\nstdout={1}".format(
                    exc, result.stdout
                )
            )
        self.assertIn("tier", data)
        self.assertIn("manifest", data)
        self.assertIn("target_path", data)

    def test_detect_forge_state_empty_dir_tier_none(self):
        result = _run_helper(["detect-forge-state", "--target", self._tmp])
        data = json.loads(result.stdout)
        self.assertEqual(data["tier"], "none")


class TestSubprocessStubs(unittest.TestCase):
    """Each of the 7 remaining stub verbs (Steps 5-9): exit 1 + 'not yet implemented'."""

    def _assert_stub(self, verb, step):
        result = _run_helper([verb])
        self.assertEqual(
            result.returncode,
            1,
            "verb={0}: expected exit 1, got {1}\nstderr={2}".format(
                verb, result.returncode, result.stderr
            ),
        )
        self.assertIn(
            "pr_review_helper {0}: not yet implemented".format(verb),
            result.stderr,
            "verb={0}: stub message not in stderr\nstderr={1}".format(
                verb, result.stderr
            ),
        )
        self.assertIn(
            "PR-REVIEW-PLAN Step {0} pending".format(step),
            result.stderr,
            "verb={0}: step number not in stderr\nstderr={1}".format(
                verb, result.stderr
            ),
        )

    def test_compute_blast_radius_stub(self):
        self._assert_stub("compute-blast-radius", 5)

    def test_bundle_context_stub(self):
        self._assert_stub("bundle-context", 6)

    def test_import_handoffs_stub(self):
        self._assert_stub("import-handoffs", 6)

    def test_check_scope_drift_stub(self):
        self._assert_stub("check-scope-drift", 7)

    def test_dispatch_review_stub(self):
        self._assert_stub("dispatch-review", 8)

    def test_finalize_output_stub(self):
        self._assert_stub("finalize-output", 9)

    def test_append_to_replay_corpus_stub(self):
        self._assert_stub("append-to-replay-corpus", 9)


class TestDetectSmellsVerb(unittest.TestCase):
    """detect-smells verb: integration smoke tests using synthetic state.json."""

    def setUp(self):
        import dataclasses
        import json as _json
        self._tmp = tempfile.mkdtemp()
        # Build a minimal state.json in the expected location.
        from _pr_review._state import PRReviewState, state_path
        self._pr_number = 99
        sp = state_path(
            self._tmp + "/.devforge",
            self._pr_number,
        )
        import os
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        state = PRReviewState(
            pr_number=self._pr_number,
            repo="acme/app",
            diff="diff --git a/foo.py b/foo.py\n+line1\n+line2\n",
            pr_body="",  # empty body triggers empty_pr_body finding on every run
            commit_subjects=["fix: concise commit"],
        )
        with open(sp, "w", encoding="utf-8") as fh:
            _json.dump(dataclasses.asdict(state), fh, indent=2)
            fh.write("\n")
        self._state_path = sp

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_detect_smells_exits_0_with_valid_state(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "detect-smells",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(
            result.returncode,
            0,
            "detect-smells: expected 0, got {0}\nstderr={1}".format(
                result.returncode, result.stderr
            ),
        )

    def test_detect_smells_stdout_is_valid_json(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "detect-smells",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail("stdout not valid JSON: {0}\nstdout={1!r}".format(exc, result.stdout))
        self.assertEqual(data["status"], "ok")
        self.assertIn("smells_count", data)
        self.assertIn("by_severity", data)
        self.assertIn("state_path", data)

    def test_detect_smells_without_state_exits_1(self):
        """When no state.json exists, detect-smells exits 1."""
        result = _run_helper([
            "detect-smells",
            "--pr", "9999",
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 1)
        self.assertIn("run `intake` first", result.stderr)

    def test_detect_smells_appends_to_state_smells(self):
        """After detect-smells, state.json smells list is updated."""
        import json as _json
        _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "detect-smells",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        with open(self._state_path, "r", encoding="utf-8") as fh:
            state_data = _json.load(fh)
        # smells is a list (may be empty if no heuristics fire on clean state).
        self.assertIsInstance(state_data["smells"], list)

    def test_detect_smells_idempotent_run_appends(self):
        """Running detect-smells twice accumulates findings (append semantics)."""
        import json as _json
        argv = [
            "--devforge-dir", self._tmp + "/.devforge",
            "detect-smells",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ]
        # First run.
        _run_helper(argv)
        with open(self._state_path, "r", encoding="utf-8") as fh:
            count_after_first = len(_json.load(fh)["smells"])
        # Second run appends.
        _run_helper(argv)
        with open(self._state_path, "r", encoding="utf-8") as fh:
            count_after_second = len(_json.load(fh)["smells"])
        self.assertGreaterEqual(count_after_first, 1, "test fixture must produce >=1 finding")
        self.assertEqual(count_after_second, count_after_first * 2)


class TestHelpOutput(unittest.TestCase):
    def test_help_exits_0(self):
        result = _run_helper(["--help"])
        self.assertEqual(result.returncode, 0)

    def test_help_lists_all_verbs(self):
        result = _run_helper(["--help"])
        for verb, _ in _VERB_STEP:
            self.assertIn(
                verb,
                result.stdout,
                "verb {0!r} not found in --help output".format(verb),
            )

    def test_no_subcommand_exits_2(self):
        result = _run_helper([])
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
