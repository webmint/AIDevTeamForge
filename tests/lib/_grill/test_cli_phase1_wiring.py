"""Tests for the CLI wiring of three previously-library-only /devforge:grill
helpers, added on top of src/devforge/lib/_grill/_cli.py:

1. render-report's ack gains a "clean" key -- the verbatim return of
   _partition.partition_is_clean(partition), cross-checked directly
   against that function in every test so the two cannot drift.
2. merge-passes -- a new verb, fixed 2-pool UNION merge over
   _merge.merge_two_passes.
3. check-status-and-flip gains --adversary-status / --plan-sha256,
   persisting GrillState's like-named fields. Omitting a flag leaves the
   corresponding field UNCHANGED (never blanked); an unrecognised
   --adversary-status value exits 2 and writes nothing.

Drives argv -> exit code -> stdout through the real main() entry point
(the same _capture pattern test_cli.py uses), not the underlying library
functions directly -- except where cross-checking against the library
function IS the point (see (1) above).

Coverage:

render-report "clean" ack key:
  False for confirmed-only / contested-only / uncertain-only
  True for dismissed-only and for all-empty
  every case cross-checked against partition_is_clean(partition) directly

merge-passes:
  a finding present in exactly one pass survives
  an identical finding in both passes dedups to one
  output is a bare JSON array, not a dict
  accepts the {"passed": [...]} wrapper shape (validate-findings output)
  missing pool path -> exit 2, no traceback
  malformed JSON pool -> exit 2, no traceback
  a pool containing a non-dict top-level element -> exit 2, no traceback
    (review finding 1: used to crash with an unhandled AttributeError)
  wrong --pools count (argparse nargs=2) -> exit 2
  CLI output equals merge_two_passes(...) called directly (no CLI-layer
    reinterpretation of the union semantics)

check-status-and-flip new fields:
  --adversary-status round-trips and is readable via the real adversary_ran()
  "clean" also counts as ran (mirrors _state.py's contract)
  "failed" does not count as ran
  --plan-sha256 round-trips
  malformed --plan-sha256 (wrong length / non-hex chars) -> exit 2, writes
    nothing (review finding 5: a shape check, never a comparison)
  omitting both flags on an unrelated --to flip leaves prior values intact
  invalid --adversary-status value -> exit 2, writes nothing (new file case
    AND pre-existing-file-untouched case)
  combined --to + new-field invocation performs exactly ONE write_state()
    call (review finding 4: no more flip_phase-then-second-write window)

No-hash-comparison surface:
  every option string containing "sha"/"hash" across the whole parser is
  exactly {"--plan-sha256"} -- a SET flag, not a compare flag; no verb name
  contains "compare"
  source-level guard (review finding 3): plan_sha256 never appears adjacent
    to == or != anywhere in _cli.py, _merge_cli.py, or _state.py -- a
    behavioral check that survives a future flag whose NAME doesn't say
    "sha"/"hash"/"compare"
"""

import argparse
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import io  # noqa: E402

from _grill._cli import _SUBCOMMAND_REGISTRY, build_parser, main  # noqa: E402
from _grill._merge import merge_two_passes  # noqa: E402
from _grill._partition import partition_is_clean  # noqa: E402
from _grill._state import (  # noqa: E402
    GrillState,
    adversary_ran,
    read_state,
    state_path,
    write_state,
)


# ---------------------------------------------------------------------------
# Shared test helpers (same shapes/pattern as test_cli.py)
# ---------------------------------------------------------------------------


def _finding(file="src/auth/login.py", line=42, pattern="SQLi via string concat"):
    # type: (str, object, str) -> dict
    """Minimal ParsedFinding-shaped dict. (file, line, pattern) is the
    identity key _merge._identity_key reads; other fields are filler.
    """
    return {
        "agent": "devils-advocate",
        "severity": "High",
        "file": file,
        "line": line,
        "pattern": pattern,
        "confidence": "Certain",
        "evidence": "def login(user):",
        "why": "Some reason.",
        "remediation": "Some fix.",
        "category": "security",
        "tags": [],
    }


def _write_json(obj, path):
    # type: (object, str) -> None
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2)


def _write_text(content, path):
    # type: (str, str) -> None
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def _capture(argv):
    # type: (list) -> tuple
    """Run main(argv), capture stdout/stderr, return (exit_code, out, err)."""
    buf_out = io.StringIO()
    buf_err = io.StringIO()
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = buf_out
    sys.stderr = buf_err
    try:
        code = main(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return code, buf_out.getvalue(), buf_err.getvalue()


# ---------------------------------------------------------------------------
# Test: render-report "clean" ack key
# ---------------------------------------------------------------------------


class TestRenderReportCleanAck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, partition, disposition="PROCEED", rationale="ok"):
        # type: (dict, str, str) -> tuple
        partition_path = os.path.join(self.tmp, "partition.json")
        _write_json(partition, partition_path)
        feature_dir = os.path.join(self.tmp, "specs", "001-auth")
        os.makedirs(feature_dir, exist_ok=True)
        return _capture(
            ["render-report",
             "--partition", partition_path,
             "--feature", feature_dir,
             "--date", "2026-08-23",
             "--disposition", disposition,
             "--rationale", rationale]
        )

    def _assert_clean_matches(self, partition, expected):
        # type: (dict, bool) -> None
        # Cross-check directly against the library function so the CLI's
        # reported value and partition_is_clean's own return cannot drift.
        direct = partition_is_clean(partition)
        self.assertEqual(direct, expected)
        code, out, err = self._run(partition)
        self.assertEqual(code, 0, err)
        ack = json.loads(out)
        self.assertIn("clean", ack)
        self.assertEqual(ack["clean"], direct)

    def test_false_when_confirmed_nonempty(self):
        self._assert_clean_matches(
            {"confirmed": [_finding()], "dismissed": [], "uncertain": [],
             "contested": []},
            False,
        )

    def test_false_when_contested_nonempty(self):
        self._assert_clean_matches(
            {"confirmed": [], "dismissed": [], "uncertain": [],
             "contested": [_finding()]},
            False,
        )

    def test_false_when_uncertain_nonempty(self):
        self._assert_clean_matches(
            {"confirmed": [], "dismissed": [], "uncertain": [_finding()],
             "contested": []},
            False,
        )

    def test_true_when_only_dismissed_nonempty(self):
        self._assert_clean_matches(
            {"confirmed": [], "dismissed": [_finding()], "uncertain": [],
             "contested": []},
            True,
        )

    def test_true_when_all_empty(self):
        self._assert_clean_matches(
            {"confirmed": [], "dismissed": [], "uncertain": [], "contested": []},
            True,
        )


# ---------------------------------------------------------------------------
# Test: merge-passes
# ---------------------------------------------------------------------------


class TestMergePasses(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _pool_path(self, name, findings):
        # type: (str, list) -> str
        path = os.path.join(self.tmp, name)
        _write_json(findings, path)
        return path

    def test_finding_in_exactly_one_pass_survives(self):
        f_a = _finding(pattern="only in A")
        f_b = _finding(pattern="only in B", line=99)
        path_a = self._pool_path("pass-a.json", [f_a])
        path_b = self._pool_path("pass-b.json", [f_b])
        code, out, err = _capture(
            ["merge-passes", "--pools", path_a, path_b]
        )
        self.assertEqual(code, 0, err)
        merged = json.loads(out)
        self.assertEqual(len(merged), 2)
        self.assertIn(f_a, merged)
        self.assertIn(f_b, merged)

    def test_identical_finding_in_both_passes_dedups_to_one(self):
        f = _finding(pattern="dup")
        # Same (file, line, pattern) identity, different evidence text --
        # must still dedup to one per _merge._identity_key.
        f_variant = dict(f)
        f_variant["evidence"] = "a different quoted span"
        path_a = self._pool_path("pass-a.json", [f])
        path_b = self._pool_path("pass-b.json", [f_variant])
        code, out, err = _capture(
            ["merge-passes", "--pools", path_a, path_b]
        )
        self.assertEqual(code, 0, err)
        merged = json.loads(out)
        self.assertEqual(len(merged), 1)

    def test_output_is_bare_array_not_dict(self):
        path_a = self._pool_path("pass-a.json", [_finding()])
        path_b = self._pool_path("pass-b.json", [])
        code, out, err = _capture(
            ["merge-passes", "--pools", path_a, path_b]
        )
        self.assertEqual(code, 0, err)
        merged = json.loads(out)
        self.assertIsInstance(merged, list)

    def test_accepts_passed_key_wrapper_shape(self):
        wrapped_a = {"status": "complete", "passed": [_finding(pattern="wrapped")]}
        path_a = self._pool_path("pass-a.json", wrapped_a)
        path_b = self._pool_path("pass-b.json", [])
        code, out, err = _capture(
            ["merge-passes", "--pools", path_a, path_b]
        )
        self.assertEqual(code, 0, err)
        merged = json.loads(out)
        self.assertEqual(len(merged), 1)

    def test_missing_pool_path_returns_2_no_traceback(self):
        path_a = os.path.join(self.tmp, "does-not-exist.json")
        path_b = self._pool_path("pass-b.json", [])
        code, out, err = _capture(
            ["merge-passes", "--pools", path_a, path_b]
        )
        self.assertEqual(code, 2)
        self.assertIn("merge-passes", err)
        self.assertNotIn("Traceback", err)

    def test_malformed_json_pool_returns_2_no_traceback(self):
        path_a = os.path.join(self.tmp, "bad.json")
        _write_text("{not valid json", path_a)
        path_b = self._pool_path("pass-b.json", [])
        code, out, err = _capture(
            ["merge-passes", "--pools", path_a, path_b]
        )
        self.assertEqual(code, 2)
        self.assertIn("merge-passes", err)
        self.assertNotIn("Traceback", err)

    def test_non_dict_pool_element_returns_2_no_traceback(self):
        """Review finding 1: a pool file whose top-level array contains a
        non-dict element (e.g. a bare string or int) used to crash with an
        unhandled AttributeError deep inside merge_two_passes's
        finding.get(...) calls, instead of the clean exit-2 every other
        malformed-shape branch in this handler already produces.
        """
        path_a = self._pool_path("pass-a.json", ["not-a-dict", 123])
        path_b = self._pool_path("pass-b.json", [])
        code, out, err = _capture(
            ["merge-passes", "--pools", path_a, path_b]
        )
        self.assertEqual(code, 2)
        self.assertIn("merge-passes", err)
        self.assertNotIn("Traceback", err)

    def test_non_dict_element_inside_passed_wrapper_returns_2(self):
        """Same defect, reached via the {"passed": [...]} wrapper shape
        rather than the bare-array shape -- the fix sits after both
        branches resolve pool_findings, so both paths must be covered.
        """
        wrapped_a = {"status": "complete", "passed": [_finding(), "oops"]}
        path_a = self._pool_path("pass-a.json", wrapped_a)
        path_b = self._pool_path("pass-b.json", [])
        code, out, err = _capture(
            ["merge-passes", "--pools", path_a, path_b]
        )
        self.assertEqual(code, 2)
        self.assertIn("merge-passes", err)
        self.assertNotIn("Traceback", err)

    def test_wrong_pools_count_returns_2(self):
        path_a = self._pool_path("pass-a.json", [])
        code, out, err = _capture(["merge-passes", "--pools", path_a])
        self.assertEqual(code, 2)

    def test_cli_output_matches_merge_two_passes_directly(self):
        """The CLI is a thin pass-through: its output equals a direct call
        to merge_two_passes on the same two pools, so the CLI layer cannot
        be silently reinterpreting the union semantics.
        """
        pool_a = [_finding(pattern="A1"), _finding(pattern="A2", line=10)]
        pool_b = [_finding(pattern="A1"), _finding(pattern="B1", line=20)]
        path_a = self._pool_path("pass-a.json", pool_a)
        path_b = self._pool_path("pass-b.json", pool_b)
        code, out, err = _capture(
            ["merge-passes", "--pools", path_a, path_b]
        )
        self.assertEqual(code, 0, err)
        merged = json.loads(out)
        direct = merge_two_passes(pool_a, pool_b)
        self.assertEqual(merged, direct)


# ---------------------------------------------------------------------------
# Test: check-status-and-flip -- --adversary-status / --plan-sha256
# ---------------------------------------------------------------------------


class TestCheckStatusAndFlipNewFields(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_adversary_status_round_trips_and_readable_by_adversary_ran(self):
        code, out, err = _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp,
             "--adversary-status", "complete"]
        )
        self.assertEqual(code, 0, err)
        ack = json.loads(out)
        self.assertEqual(ack["adversary_status"], "complete")

        state = read_state(state_path(self.tmp))
        self.assertIsNotNone(state)
        self.assertEqual(state.adversary_status, "complete")
        self.assertTrue(adversary_ran(state))

    def test_adversary_status_clean_also_counts_as_ran(self):
        _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp,
             "--adversary-status", "clean"]
        )
        state = read_state(state_path(self.tmp))
        self.assertTrue(adversary_ran(state))

    def test_adversary_status_failed_does_not_count_as_ran(self):
        _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp,
             "--adversary-status", "failed"]
        )
        state = read_state(state_path(self.tmp))
        self.assertFalse(adversary_ran(state))

    def test_plan_sha256_round_trips(self):
        digest = "a" * 64
        code, out, err = _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp,
             "--plan-sha256", digest]
        )
        self.assertEqual(code, 0, err)
        ack = json.loads(out)
        self.assertEqual(ack["plan_sha256"], digest)
        state = read_state(state_path(self.tmp))
        self.assertEqual(state.plan_sha256, digest)

    def test_new_fields_settable_alongside_a_to_flip(self):
        code, out, err = _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp,
             "--to", "report", "--status", "complete",
             "--adversary-status", "complete", "--plan-sha256", "b" * 64]
        )
        self.assertEqual(code, 0, err)
        state = read_state(state_path(self.tmp))
        self.assertEqual(state.phase, "report")
        self.assertEqual(state.status, "complete")
        self.assertEqual(state.adversary_status, "complete")
        self.assertEqual(state.plan_sha256, "b" * 64)

    def test_combined_to_and_fields_writes_state_exactly_once(self):
        """Review finding 4: the combined --to + new-field path used to call
        flip_phase() (an internal read+write) and THEN a second, separate
        write_state() to layer the new fields on -- two writes, each
        individually atomic but the SEQUENCE not. Patches
        _grill._state.write_state to count invocations while still
        delegating to the real implementation, so this is a direct
        assertion on the call count, not an inference from the end state.
        """
        from _grill import _state as state_module

        real_write_state = state_module.write_state
        calls = []

        def _counting_write_state(path, state):
            calls.append(1)
            return real_write_state(path, state)

        with mock.patch.object(
            state_module, "write_state", side_effect=_counting_write_state
        ):
            code, out, err = _capture(
                ["check-status-and-flip", "--feature-dir", self.tmp,
                 "--to", "report", "--status", "complete",
                 "--adversary-status", "complete",
                 "--plan-sha256", "d" * 64]
            )
        self.assertEqual(code, 0, err)
        self.assertEqual(len(calls), 1)

        state = read_state(state_path(self.tmp))
        self.assertEqual(state.phase, "report")
        self.assertEqual(state.status, "complete")
        self.assertEqual(state.adversary_status, "complete")
        self.assertEqual(state.plan_sha256, "d" * 64)

    def test_malformed_plan_sha256_wrong_length_returns_2_writes_nothing(self):
        sp = state_path(self.tmp)
        self.assertFalse(os.path.isfile(sp))
        code, out, err = _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp,
             "--plan-sha256", "abc123"]
        )
        self.assertEqual(code, 2)
        self.assertIn("check-status-and-flip", err)
        self.assertFalse(os.path.isfile(sp))

    def test_malformed_plan_sha256_non_hex_chars_returns_2_writes_nothing(self):
        sp = state_path(self.tmp)
        bogus = "z" * 64  # right length, not hex
        code, out, err = _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp,
             "--plan-sha256", bogus]
        )
        self.assertEqual(code, 2)
        self.assertIn("check-status-and-flip", err)
        self.assertFalse(os.path.isfile(sp))

    def test_malformed_plan_sha256_leaves_preexisting_state_untouched(self):
        sp = state_path(self.tmp)
        seeded = GrillState(phase="attack", plan_sha256="e" * 64)
        write_state(sp, seeded)

        code, out, err = _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp,
             "--plan-sha256", "not-hex-at-all"]
        )
        self.assertEqual(code, 2)

        state = read_state(sp)
        self.assertEqual(state.plan_sha256, "e" * 64)
        self.assertEqual(state.phase, "attack")

    def test_omitting_new_flags_on_unrelated_flip_leaves_values_unchanged(self):
        # Seed a state with both new fields set, via the real write_state
        # round trip (not a hand-authored fixture).
        sp = state_path(self.tmp)
        seeded = GrillState(
            phase="validate",
            adversary_status="complete",
            plan_sha256="c" * 64,
        )
        write_state(sp, seeded)

        # Flip an unrelated field (phase) WITHOUT passing either new flag.
        code, out, err = _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp,
             "--to", "attack"]
        )
        self.assertEqual(code, 0, err)

        state = read_state(sp)
        self.assertEqual(state.phase, "attack")
        # The regression this pins: an unrelated flip must NOT blank
        # fields whose flags were not passed on this invocation.
        self.assertEqual(state.adversary_status, "complete")
        self.assertEqual(state.plan_sha256, "c" * 64)

    def test_invalid_adversary_status_returns_2_and_writes_nothing_new_file(self):
        sp = state_path(self.tmp)
        self.assertFalse(os.path.isfile(sp))
        code, out, err = _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp,
             "--adversary-status", "bogus-value"]
        )
        self.assertEqual(code, 2)
        self.assertIn("check-status-and-flip", err)
        self.assertFalse(os.path.isfile(sp))

    def test_invalid_adversary_status_leaves_preexisting_state_untouched(self):
        sp = state_path(self.tmp)
        seeded = GrillState(phase="attack", adversary_status="complete")
        write_state(sp, seeded)

        code, out, err = _capture(
            ["check-status-and-flip", "--feature-dir", self.tmp,
             "--adversary-status", "bogus-value"]
        )
        self.assertEqual(code, 2)

        state = read_state(sp)
        self.assertEqual(state.adversary_status, "complete")
        self.assertEqual(state.phase, "attack")


# ---------------------------------------------------------------------------
# Test: no CLI surface compares hashes
# ---------------------------------------------------------------------------


class TestNoHashComparisonSurface(unittest.TestCase):
    def _all_option_strings(self):
        # type: () -> list
        """Walk every registered subparser's Actions and collect every
        option string across the whole CLI. Uses argparse's internal
        Action tree (._actions / .choices) -- there is no public
        traversal API for "every flag of every subcommand"; this is the
        standard introspection pattern.
        """
        parser = build_parser()
        result = []
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction):
                for sub_parser in action.choices.values():
                    for sub_action in sub_parser._actions:
                        result.extend(sub_action.option_strings)
            else:
                result.extend(action.option_strings)
        return result

    def test_only_plan_sha256_flag_mentions_sha_or_hash(self):
        all_opts = self._all_option_strings()
        suspects = {
            opt for opt in all_opts
            if "sha" in opt.lower() or "hash" in opt.lower()
        }
        self.assertEqual(suspects, {"--plan-sha256"})

    def test_no_verb_name_mentions_compare(self):
        for verb, _help, _handler in _SUBCOMMAND_REGISTRY:
            self.assertNotIn("compare", verb)

    def test_plan_sha256_never_compared_in_source(self):
        """Review finding 3: the option-string check above is a NAMING
        heuristic -- it would not catch a future internal
        `if state.plan_sha256 == compute_plan_sha256(...)` added under a
        flag whose name says nothing about "sha"/"hash"/"compare". This
        reads the actual source of every module that owns or touches the
        field and asserts plan_sha256 never sits next to a comparison
        operator, so the guard survives the exact change designed to
        defeat the name grep. Strengthens, does not replace, the check
        above.
        """
        pattern = re.compile(r"plan_sha256\s*(==|!=)")
        paths = [
            _LIB_DIR / "_grill" / "_cli.py",
            _LIB_DIR / "_grill" / "_merge_cli.py",
            _LIB_DIR / "_grill" / "_state.py",
        ]
        for path in paths:
            self.assertTrue(path.is_file(), "expected file: {0}".format(path))
            source = path.read_text(encoding="utf-8")
            match = pattern.search(source)
            self.assertIsNone(
                match,
                "plan_sha256 must never be compared (found {0!r} in "
                "{1})".format(match.group(0) if match else None, path),
            )


if __name__ == "__main__":
    unittest.main()
