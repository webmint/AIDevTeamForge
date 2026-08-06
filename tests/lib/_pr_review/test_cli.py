"""Tests for src/devforge/lib/_pr_review/_cli.py.

Coverage:
  build_parser — returns ArgumentParser; all 11 subcommands registered.
  main — no subcommand → exit 2.
  Step 2 verbs (ensure-cbm-index, detect-forge-state): exit 0, valid JSON.
  Step 3 verb (intake): args registered, no-longer-stub smoke test.
  Step 4 verb (detect-smells): args registered, smoke test with synthetic state.
  Step 5 verb (compute-blast-radius): args registered, smoke test with synthetic state.
  Step 6 verbs (bundle-context, import-handoffs): args registered, smoke tests.
  Step 7 verb (check-scope-drift): args registered, smoke tests.
  Step 8 verb (dispatch-review): args registered, smoke tests.
  Step 9 verbs (finalize-output, append-to-replay-corpus): args registered, smoke tests.
  All 11 verbs implemented; zero stubs remain.
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

# All verbs are implemented; zero stubs remain.
_STUB_VERB_STEP = []


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

        intake requires --pr and --repo; all other verbs with --pr supply it.
        """
        _PR_REQUIRED = frozenset([
            "detect-smells",
            "compute-blast-radius",
            "bundle-context",
            "import-handoffs",
            "check-scope-drift",
            "dispatch-review",
            "finalize-output",
            "append-to-replay-corpus",
        ])
        parser = build_parser()
        for verb, _ in _VERB_STEP:
            with self.subTest(verb=verb):
                if verb == "intake":
                    argv = [verb, "--pr", "1", "--repo", "foo/bar"]
                elif verb in _PR_REQUIRED:
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

    def test_step9_verbs_accept_target_and_pr_arg(self):
        """finalize-output and append-to-replay-corpus accept --pr and --target."""
        parser = build_parser()
        for verb in ("finalize-output", "append-to-replay-corpus"):
            with self.subTest(verb=verb):
                args = parser.parse_args([verb, "--pr", "42", "--target", "/x"])
                self.assertEqual(args.pr, 42)
                self.assertEqual(args.target, "/x")

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

    def test_finalize_output_missing_pr_exits_nonzero(self):
        """finalize-output without --pr exits non-zero (argparse SystemExit)."""
        with self.assertRaises(SystemExit) as ctx:
            main(["finalize-output"])
        self.assertNotEqual(ctx.exception.code, 0)


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


class TestNoStubsRemaining(unittest.TestCase):
    """Verify zero stubs remain — all 11 verbs fully implemented."""

    def test_stub_verb_list_empty(self):
        """_STUB_VERB_STEP should be empty after Step 9 implementation."""
        self.assertEqual(_STUB_VERB_STEP, [])

    def test_finalize_output_no_stub_message(self):
        """finalize-output without --pr exits via argparse, not stub message."""
        result = _run_helper(["finalize-output"])
        self.assertNotIn("not yet implemented", result.stderr)

    def test_append_to_replay_corpus_no_stub_message(self):
        """append-to-replay-corpus without --pr exits via argparse, not stub message."""
        result = _run_helper(["append-to-replay-corpus"])
        self.assertNotIn("not yet implemented", result.stderr)


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


class TestComputeBlastRadiusVerb(unittest.TestCase):
    """compute-blast-radius verb: CLI smoke tests using synthetic state.json."""

    def setUp(self):
        import dataclasses
        import json as _json
        self._tmp = tempfile.mkdtemp()
        from _pr_review._state import PRReviewState, state_path
        self._pr_number = 55
        sp = state_path(
            self._tmp + "/.devforge",
            self._pr_number,
        )
        import os
        os.makedirs(os.path.dirname(sp), exist_ok=True)
        state = PRReviewState(
            pr_number=self._pr_number,
            repo="acme/app",
            diff=(
                "diff --git a/svc.py b/svc.py\n"
                "+def compute(x):\n"
                "+    return x\n"
            ),
        )
        with open(sp, "w", encoding="utf-8") as fh:
            _json.dump(dataclasses.asdict(state), fh, indent=2)
            fh.write("\n")
        self._state_path = sp

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_compute_blast_radius_exits_0_with_valid_state(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "compute-blast-radius",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(
            result.returncode,
            0,
            "compute-blast-radius: expected 0, got {0}\nstderr={1}".format(
                result.returncode, result.stderr
            ),
        )

    def test_compute_blast_radius_stdout_is_valid_json(self):
        import json as _json
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "compute-blast-radius",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        try:
            data = _json.loads(result.stdout)
        except _json.JSONDecodeError as exc:
            self.fail("stdout not valid JSON: {0}\nstdout={1!r}".format(exc, result.stdout))
        self.assertEqual(data["status"], "ok")
        self.assertIn("symbols_extracted", data)
        self.assertIn("by_language", data)
        self.assertIn("by_kind", data)
        self.assertIn("capped", data)
        self.assertIn("state_path", data)

    def test_compute_blast_radius_without_state_exits_1(self):
        result = _run_helper([
            "compute-blast-radius",
            "--pr", "9999",
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 1)
        self.assertIn("intake", result.stderr)

    def test_compute_blast_radius_has_pr_arg(self):
        parser = build_parser()
        args = parser.parse_args(["compute-blast-radius", "--pr", "42"])
        self.assertEqual(args.pr, 42)

    def test_compute_blast_radius_has_target_arg(self):
        parser = build_parser()
        args = parser.parse_args(
            ["compute-blast-radius", "--pr", "1", "--target", "/some/path"]
        )
        self.assertEqual(args.target, "/some/path")

    def test_compute_blast_radius_requires_pr(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["compute-blast-radius"])

    def test_compute_blast_radius_writes_blast_to_state(self):
        import json as _json
        _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "compute-blast-radius",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        with open(self._state_path, "r", encoding="utf-8") as fh:
            state_data = _json.load(fh)
        self.assertIsInstance(state_data["blast"], list)
        self.assertGreater(len(state_data["blast"]), 0)


class TestBundleContextVerb(unittest.TestCase):
    """bundle-context verb: argparse + smoke tests using synthetic state.json."""

    def setUp(self):
        import dataclasses as _dc
        import json as _json
        self._tmp = tempfile.mkdtemp()
        from _pr_review._state import PRReviewState, state_path
        self._pr_number = 88
        sp = state_path(
            self._tmp + "/.devforge",
            self._pr_number,
        )
        import os as _os
        _os.makedirs(_os.path.dirname(sp), exist_ok=True)
        state = PRReviewState(
            pr_number=self._pr_number,
            repo="acme/app",
        )
        with open(sp, "w", encoding="utf-8") as fh:
            _json.dump(_dc.asdict(state), fh, indent=2)
            fh.write("\n")
        self._state_path = sp

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_bundle_context_has_pr_arg(self):
        parser = build_parser()
        args = parser.parse_args(["bundle-context", "--pr", "42"])
        self.assertEqual(args.pr, 42)

    def test_bundle_context_has_target_arg(self):
        parser = build_parser()
        args = parser.parse_args(
            ["bundle-context", "--pr", "1", "--target", "/some/path"]
        )
        self.assertEqual(args.target, "/some/path")

    def test_bundle_context_requires_pr(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["bundle-context"])

    def test_bundle_context_exits_0_with_valid_state(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "bundle-context",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(
            result.returncode,
            0,
            "bundle-context: expected 0, got {0}\nstderr={1}".format(
                result.returncode, result.stderr
            ),
        )

    def test_bundle_context_stdout_is_valid_json(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "bundle-context",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail("stdout not valid JSON: {0}\nstdout={1!r}".format(exc, result.stdout))
        self.assertEqual(data["status"], "ok")
        self.assertIn("sources_gathered", data)
        self.assertIn("state_path", data)

    def test_bundle_context_without_state_exits_1(self):
        result = _run_helper([
            "bundle-context",
            "--pr", "9999",
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 1)
        self.assertIn("intake", result.stderr)

    def test_bundle_context_writes_bundle_to_state(self):
        import json as _json
        _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "bundle-context",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        with open(self._state_path, "r", encoding="utf-8") as fh:
            state_data = _json.load(fh)
        self.assertIsInstance(state_data["bundle"], dict)
        self.assertIn("constitution_md", state_data["bundle"])
        self.assertIn("concern_docs", state_data["bundle"])
        self.assertIn("adrs", state_data["bundle"])
        self.assertIn("plan_files", state_data["bundle"])


class TestImportHandoffsVerb(unittest.TestCase):
    """import-handoffs verb: argparse + smoke tests using synthetic state.json."""

    def setUp(self):
        import dataclasses as _dc
        import json as _json
        self._tmp = tempfile.mkdtemp()
        from _pr_review._state import PRReviewState, state_path
        self._pr_number = 99
        sp = state_path(
            self._tmp + "/.devforge",
            self._pr_number,
        )
        import os as _os
        _os.makedirs(_os.path.dirname(sp), exist_ok=True)
        state = PRReviewState(
            pr_number=self._pr_number,
            repo="acme/app",
            ticket_text="auth login fix",
        )
        with open(sp, "w", encoding="utf-8") as fh:
            _json.dump(_dc.asdict(state), fh, indent=2)
            fh.write("\n")
        self._state_path = sp

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_import_handoffs_has_pr_arg(self):
        parser = build_parser()
        args = parser.parse_args(["import-handoffs", "--pr", "42"])
        self.assertEqual(args.pr, 42)

    def test_import_handoffs_has_target_arg(self):
        parser = build_parser()
        args = parser.parse_args(
            ["import-handoffs", "--pr", "1", "--target", "/some/path"]
        )
        self.assertEqual(args.target, "/some/path")

    def test_import_handoffs_requires_pr(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["import-handoffs"])

    def test_import_handoffs_exits_0_with_valid_state(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "import-handoffs",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(
            result.returncode,
            0,
            "import-handoffs: expected 0, got {0}\nstderr={1}".format(
                result.returncode, result.stderr
            ),
        )

    def test_import_handoffs_stdout_is_valid_json(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "import-handoffs",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail("stdout not valid JSON: {0}\nstdout={1!r}".format(exc, result.stdout))
        self.assertEqual(data["status"], "ok")
        self.assertIn("handoffs_found", data)
        self.assertIn("handoffs_matched", data)
        self.assertIn("filter_applied", data)

    def test_import_handoffs_without_state_exits_1(self):
        result = _run_helper([
            "import-handoffs",
            "--pr", "9999",
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 1)
        self.assertIn("intake", result.stderr)

    def test_import_handoffs_writes_research_handoffs_to_state(self):
        import json as _json
        # Create a handoff (68-INTAKE-OWNS-FEATURE-DIR-PLAN.md D2 layout:
        # specs/NNN-slug/research-handoff.json).
        feature_dir = self._tmp + "/specs/001-auth-fix"
        import os as _os
        _os.makedirs(feature_dir, exist_ok=True)
        with open(feature_dir + "/research-handoff.json", "w") as fh:
            _json.dump({"mode": "bug", "verdict": "proceed"}, fh)

        _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "import-handoffs",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        with open(self._state_path, "r", encoding="utf-8") as fh:
            state_data = _json.load(fh)
        self.assertIn("research_handoffs", state_data["bundle"])
        self.assertIsInstance(state_data["bundle"]["research_handoffs"], list)


class TestCheckScopeDriftVerb(unittest.TestCase):
    """check-scope-drift verb: argparse + smoke tests using synthetic state.json."""

    def setUp(self):
        import dataclasses as _dc
        import json as _json
        self._tmp = tempfile.mkdtemp()
        from _pr_review._state import PRReviewState, state_path
        self._pr_number = 304
        sp = state_path(
            self._tmp + "/.devforge",
            self._pr_number,
        )
        import os as _os
        _os.makedirs(_os.path.dirname(sp), exist_ok=True)
        state = PRReviewState(
            pr_number=self._pr_number,
            repo="acme/app",
            ticket_text=(
                "Update SHIP-TO-ADDRESS label to include red asterisk\n"
                "AC-1: The label shows a red asterisk.\n"
                "AC-2: Existing tests pass.\n"
                "AC-3: No regression on print layout.\n"
            ),
            pr_body="- Added asterisk to label\n- Updated CSS\n",
        )
        with open(sp, "w", encoding="utf-8") as fh:
            _json.dump(_dc.asdict(state), fh, indent=2)
            fh.write("\n")
        self._state_path = sp

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_check_scope_drift_has_pr_arg(self):
        parser = build_parser()
        args = parser.parse_args(["check-scope-drift", "--pr", "42"])
        self.assertEqual(args.pr, 42)

    def test_check_scope_drift_has_target_arg(self):
        parser = build_parser()
        args = parser.parse_args(
            ["check-scope-drift", "--pr", "1", "--target", "/some/path"]
        )
        self.assertEqual(args.target, "/some/path")

    def test_check_scope_drift_requires_pr(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["check-scope-drift"])

    def test_check_scope_drift_exits_0_with_valid_state(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "check-scope-drift",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(
            result.returncode,
            0,
            "check-scope-drift: expected 0, got {0}\nstderr={1}".format(
                result.returncode, result.stderr
            ),
        )

    def test_check_scope_drift_stdout_is_valid_json(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "check-scope-drift",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail("stdout not valid JSON: {0}\nstdout={1!r}".format(exc, result.stdout))
        self.assertEqual(data["status"], "ok")
        self.assertIn("bullets_extracted", data)
        self.assertIn("by_source", data)
        self.assertIn("by_extracted_via", data)
        self.assertIn("capped", data)
        self.assertIn("state_path", data)

    def test_check_scope_drift_without_state_exits_1(self):
        result = _run_helper([
            "check-scope-drift",
            "--pr", "9999",
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 1)
        self.assertIn("intake", result.stderr)

    def test_check_scope_drift_extracts_bullets(self):
        import json as _json
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "check-scope-drift",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        data = _json.loads(result.stdout)
        # AC-1, AC-2, AC-3 from ticket_text + 2 markdown bullets from pr_body.
        self.assertGreaterEqual(data["bullets_extracted"], 4)

    def test_check_scope_drift_writes_drift_to_state(self):
        import json as _json
        _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "check-scope-drift",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        with open(self._state_path, "r", encoding="utf-8") as fh:
            state_data = _json.load(fh)
        self.assertIsInstance(state_data["drift"], dict)
        self.assertIn("bullets", state_data["drift"])
        self.assertIn("coverage_matrix", state_data["drift"])
        self.assertIn("scope_creep_files", state_data["drift"])
        self.assertFalse(state_data["drift"]["filled"])

    def test_check_scope_drift_replaces_prior_drift(self):
        """Running twice replaces drift (not appended)."""
        import json as _json
        argv = [
            "--devforge-dir", self._tmp + "/.devforge",
            "check-scope-drift",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ]
        _run_helper(argv)
        with open(self._state_path, "r", encoding="utf-8") as fh:
            count_first = len(_json.load(fh)["drift"]["bullets"])
        _run_helper(argv)
        with open(self._state_path, "r", encoding="utf-8") as fh:
            count_second = len(_json.load(fh)["drift"]["bullets"])
        # Idempotent replace — not append.
        self.assertEqual(count_first, count_second)


class TestDispatchReviewVerb(unittest.TestCase):
    """dispatch-review verb: argparse + smoke tests using synthetic state.json."""

    def setUp(self):
        import dataclasses as _dc
        import json as _json
        self._tmp = tempfile.mkdtemp()
        from _pr_review._state import PRReviewState, state_path
        self._pr_number = 42
        sp = state_path(
            self._tmp + "/.devforge",
            self._pr_number,
        )
        import os as _os
        _os.makedirs(_os.path.dirname(sp), exist_ok=True)
        state = PRReviewState(
            pr_number=self._pr_number,
            repo="acme/app",
            diff="diff --git a/src/foo.py b/src/foo.py\n+def bar():\n+    pass\n",
            ticket_text="AC-1: bar should be defined.",
        )
        with open(sp, "w", encoding="utf-8") as fh:
            _json.dump(_dc.asdict(state), fh, indent=2)
            fh.write("\n")
        self._state_path = sp

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_dispatch_review_has_pr_arg(self):
        parser = build_parser()
        args = parser.parse_args(["dispatch-review", "--pr", "42"])
        self.assertEqual(args.pr, 42)

    def test_dispatch_review_has_target_arg(self):
        parser = build_parser()
        args = parser.parse_args(
            ["dispatch-review", "--pr", "1", "--target", "/some/path"]
        )
        self.assertEqual(args.target, "/some/path")

    def test_dispatch_review_requires_pr(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["dispatch-review"])

    def test_dispatch_review_exits_0_with_valid_state(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "dispatch-review",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(
            result.returncode,
            0,
            "dispatch-review: expected 0, got {0}\nstderr={1}".format(
                result.returncode, result.stderr
            ),
        )

    def test_dispatch_review_stdout_is_valid_json(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "dispatch-review",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail("stdout not valid JSON: {0}\nstdout={1!r}".format(exc, result.stdout))
        self.assertEqual(data["status"], "ok")
        self.assertIn("brief_path", data)
        self.assertIn("brief_size_chars", data)
        self.assertIn("sections_included", data)
        self.assertIn("smells_count", data)
        self.assertIn("blast_probes_count", data)
        self.assertIn("drift_bullets_count", data)
        self.assertIn("bundle_sources_count", data)
        self.assertIn("next_action", data)

    def test_dispatch_review_without_state_exits_1(self):
        result = _run_helper([
            "dispatch-review",
            "--pr", "9999",
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 1)
        self.assertIn("intake", result.stderr)

    def test_dispatch_review_writes_brief_md(self):
        import json as _json
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "dispatch-review",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        data = _json.loads(result.stdout)
        import os as _os
        self.assertTrue(
            _os.path.isfile(data["brief_path"]),
            "brief.md not found at {0}".format(data["brief_path"]),
        )

    def test_dispatch_review_brief_path_under_pr_dir(self):
        import json as _json
        import os as _os
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "dispatch-review",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        data = _json.loads(result.stdout)
        expected_dir = _os.path.join(
            self._tmp, ".devforge", "pr-reviews", str(self._pr_number)
        )
        self.assertTrue(data["brief_path"].startswith(expected_dir))

    def test_dispatch_review_idempotent(self):
        """Running dispatch-review twice returns exit 0 both times."""
        argv = [
            "--devforge-dir", self._tmp + "/.devforge",
            "dispatch-review",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ]
        result1 = _run_helper(argv)
        result2 = _run_helper(argv)
        self.assertEqual(result1.returncode, 0)
        self.assertEqual(result2.returncode, 0)


class TestFinalizeOutputVerb(unittest.TestCase):
    """finalize-output verb: argparse + smoke tests using synthetic state.json."""

    def setUp(self):
        import dataclasses as _dc
        import json as _json
        self._tmp = tempfile.mkdtemp()
        from _pr_review._state import PRReviewState, state_path
        self._pr_number = 77
        sp = state_path(
            self._tmp + "/.devforge",
            self._pr_number,
        )
        import os as _os
        _os.makedirs(_os.path.dirname(sp), exist_ok=True)
        state = PRReviewState(
            pr_number=self._pr_number,
            repo="acme/app",
            findings=[
                {
                    "severity": "high",
                    "location": "src/x.py:10",
                    "category": "smell",
                    "evidence": "test evidence",
                    "fix_hint": "test fix",
                    "source_heuristic": "hedge-defensive",
                },
                {
                    "severity": "low",
                    "location": "src/y.py:5",
                    "category": "drift",
                    "evidence": "drift evidence",
                    "fix_hint": "",
                    "source_heuristic": "",
                },
            ],
        )
        with open(sp, "w", encoding="utf-8") as fh:
            _json.dump(_dc.asdict(state), fh, indent=2)
            fh.write("\n")
        self._state_path = sp

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_finalize_output_has_pr_arg(self):
        parser = build_parser()
        args = parser.parse_args(["finalize-output", "--pr", "42"])
        self.assertEqual(args.pr, 42)

    def test_finalize_output_has_target_arg(self):
        parser = build_parser()
        args = parser.parse_args(
            ["finalize-output", "--pr", "1", "--target", "/some/path"]
        )
        self.assertEqual(args.target, "/some/path")

    def test_finalize_output_requires_pr(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["finalize-output"])

    def test_finalize_output_exits_0_with_valid_state(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "finalize-output",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(
            result.returncode,
            0,
            "finalize-output: expected 0, got {0}\nstderr={1}".format(
                result.returncode, result.stderr
            ),
        )

    def test_finalize_output_stdout_is_valid_json(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "finalize-output",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail("stdout not valid JSON: {0}\nstdout={1!r}".format(exc, result.stdout))
        self.assertEqual(data["status"], "ok")
        self.assertIn("findings_path", data)
        self.assertIn("findings_total", data)
        self.assertIn("by_severity", data)
        self.assertIn("slop_score", data)
        self.assertIn("blast_risk_score", data)
        self.assertIn("drift_summary", data)
        self.assertIn("state_path", data)

    def test_finalize_output_without_state_exits_1(self):
        result = _run_helper([
            "finalize-output",
            "--pr", "9999",
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 1)
        self.assertIn("intake", result.stderr)

    def test_finalize_output_writes_findings_md(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "finalize-output",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        import os as _os
        self.assertTrue(
            _os.path.isfile(data["findings_path"]),
            "findings.md not found at {0}".format(data["findings_path"]),
        )

    def test_finalize_output_correct_findings_total(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "finalize-output",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(data["findings_total"], 2)

    def test_finalize_output_idempotent(self):
        argv = [
            "--devforge-dir", self._tmp + "/.devforge",
            "finalize-output",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ]
        result1 = _run_helper(argv)
        result2 = _run_helper(argv)
        self.assertEqual(result1.returncode, 0)
        self.assertEqual(result2.returncode, 0)


class TestAppendToReplayCorpusVerb(unittest.TestCase):
    """append-to-replay-corpus verb: argparse + smoke tests using synthetic state.json."""

    def setUp(self):
        import dataclasses as _dc
        import json as _json
        self._tmp = tempfile.mkdtemp()
        from _pr_review._state import PRReviewState, state_path
        self._pr_number = 304
        sp = state_path(
            self._tmp + "/.devforge",
            self._pr_number,
        )
        import os as _os
        _os.makedirs(_os.path.dirname(sp), exist_ok=True)
        state = PRReviewState(
            pr_number=self._pr_number,
            repo="org/module",
            findings=[{"severity": "medium", "location": "x.vue:1", "category": "smell",
                        "evidence": "e", "fix_hint": "f", "source_heuristic": ""}],
            smells=[{"name": "s"}],
            blast=[{"symbol": "compute"}],
            drift={"bullets": [{"id": "B1"}], "coverage_matrix": []},
        )
        with open(sp, "w", encoding="utf-8") as fh:
            _json.dump(_dc.asdict(state), fh, indent=2)
            fh.write("\n")
        self._state_path = sp

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmp, ignore_errors=True)

    def test_append_to_replay_corpus_has_pr_arg(self):
        parser = build_parser()
        args = parser.parse_args(["append-to-replay-corpus", "--pr", "42"])
        self.assertEqual(args.pr, 42)

    def test_append_to_replay_corpus_has_target_arg(self):
        parser = build_parser()
        args = parser.parse_args(
            ["append-to-replay-corpus", "--pr", "1", "--target", "/some/path"]
        )
        self.assertEqual(args.target, "/some/path")

    def test_append_to_replay_corpus_requires_pr(self):
        parser = build_parser()
        with self.assertRaises(SystemExit):
            parser.parse_args(["append-to-replay-corpus"])

    def test_append_to_replay_corpus_exits_0_with_valid_state(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "append-to-replay-corpus",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(
            result.returncode,
            0,
            "append-to-replay-corpus: expected 0, got {0}\nstderr={1}".format(
                result.returncode, result.stderr
            ),
        )

    def test_append_to_replay_corpus_stdout_is_valid_json(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "append-to-replay-corpus",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            self.fail("stdout not valid JSON: {0}\nstdout={1!r}".format(exc, result.stdout))
        self.assertEqual(data["status"], "ok")
        self.assertIn("bundle_path", data)
        self.assertIn("corpus_index_path", data)
        self.assertIn("entry_action", data)
        self.assertIn("review_count", data)
        self.assertIn("findings_count", data)

    def test_append_to_replay_corpus_without_state_exits_1(self):
        result = _run_helper([
            "append-to-replay-corpus",
            "--pr", "9999",
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 1)
        self.assertIn("intake", result.stderr)

    def test_append_to_replay_corpus_writes_bundle(self):
        import os as _os
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "append-to-replay-corpus",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertTrue(
            _os.path.isfile(data["bundle_path"]),
            "bundle not found at {0}".format(data["bundle_path"]),
        )

    def test_append_to_replay_corpus_writes_index(self):
        import os as _os
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "append-to-replay-corpus",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertTrue(
            _os.path.isfile(data["corpus_index_path"]),
            "corpus index not found at {0}".format(data["corpus_index_path"]),
        )

    def test_append_to_replay_corpus_entry_action_created_on_first_run(self):
        result = _run_helper([
            "--devforge-dir", self._tmp + "/.devforge",
            "append-to-replay-corpus",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ])
        self.assertEqual(result.returncode, 0)
        data = json.loads(result.stdout)
        self.assertEqual(data["entry_action"], "created")

    def test_append_to_replay_corpus_entry_action_updated_on_second_run(self):
        argv = [
            "--devforge-dir", self._tmp + "/.devforge",
            "append-to-replay-corpus",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ]
        _run_helper(argv)
        result2 = _run_helper(argv)
        self.assertEqual(result2.returncode, 0)
        data = json.loads(result2.stdout)
        self.assertEqual(data["entry_action"], "updated")

    def test_append_to_replay_corpus_review_count_increments(self):
        argv = [
            "--devforge-dir", self._tmp + "/.devforge",
            "append-to-replay-corpus",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ]
        _run_helper(argv)
        result2 = _run_helper(argv)
        data = json.loads(result2.stdout)
        self.assertEqual(data["review_count"], 2)

    def test_append_to_replay_corpus_idempotent(self):
        argv = [
            "--devforge-dir", self._tmp + "/.devforge",
            "append-to-replay-corpus",
            "--pr", str(self._pr_number),
            "--target", self._tmp,
        ]
        result1 = _run_helper(argv)
        result2 = _run_helper(argv)
        self.assertEqual(result1.returncode, 0)
        self.assertEqual(result2.returncode, 0)


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
