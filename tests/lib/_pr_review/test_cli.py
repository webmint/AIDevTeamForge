"""Tests for src/devforge/lib/_pr_review/_cli.py.

Coverage:
  build_parser — returns ArgumentParser; all 11 subcommands registered.
  main — no subcommand → exit 2.
  Step 2 verbs (ensure-cbm-index, detect-forge-state): exit 0, valid JSON.
  The 9 remaining stub verbs: exit 1 + correct "not yet implemented" message.
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

# Only the 9 still-stub verbs (Steps 3-9).
_STUB_VERB_STEP = [
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
        """Each verb can be parsed without argparse raising SystemExit."""
        parser = build_parser()
        for verb, _ in _VERB_STEP:
            with self.subTest(verb=verb):
                args = parser.parse_args([verb])
                self.assertEqual(args.subcommand, verb)

    def test_devforge_dir_default(self):
        parser = build_parser()
        args = parser.parse_args(["intake"])
        self.assertEqual(args.devforge_dir, ".devforge")

    def test_devforge_dir_override(self):
        parser = build_parser()
        args = parser.parse_args(["--devforge-dir", "/tmp/forge", "intake"])
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
        """Stub verbs (steps 3-9) do not accept --target yet."""
        parser = build_parser()
        for verb, _ in _STUB_VERB_STEP:
            with self.subTest(verb=verb):
                with self.assertRaises(SystemExit):
                    parser.parse_args([verb, "--target", "/x"])


class TestMainDispatch(unittest.TestCase):
    def test_no_subcommand_returns_2(self):
        code = main([])
        self.assertEqual(code, 2)

    def test_stub_verb_returns_1(self):
        """Any stub verb returns 1 (not yet implemented)."""
        code = main(["intake"])
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
    """Each of the 9 stub verbs: exit 1 + stderr contains the 'not yet implemented' message."""

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

    def test_intake_stub(self):
        self._assert_stub("intake", 3)

    def test_detect_smells_stub(self):
        self._assert_stub("detect-smells", 4)

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
