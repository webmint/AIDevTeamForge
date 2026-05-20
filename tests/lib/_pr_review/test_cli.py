"""Tests for src/devforge/lib/_pr_review/_cli.py.

Coverage:
  build_parser — returns ArgumentParser; all 11 subcommands registered.
  main — no subcommand → exit 2.
  Each stub verb via subprocess: exit 1 + correct "not yet implemented" message.
"""

import argparse
import subprocess
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "pr_review_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._cli import build_parser, main  # noqa: E402


# All 11 verbs with their expected plan-step numbers (for message verification).
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


class TestMainDispatch(unittest.TestCase):
    def test_no_subcommand_returns_2(self):
        code = main([])
        self.assertEqual(code, 2)

    def test_verb_returns_1(self):
        """Any stub verb returns 1 (not yet implemented)."""
        code = main(["intake"])
        self.assertEqual(code, 1)


class TestSubprocessStubs(unittest.TestCase):
    """Each verb: exit 1 + stderr contains the 'not yet implemented' message."""

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

    def test_ensure_cbm_index_stub(self):
        self._assert_stub("ensure-cbm-index", 2)

    def test_detect_forge_state_stub(self):
        self._assert_stub("detect-forge-state", 2)

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
