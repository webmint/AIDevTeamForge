#!/usr/bin/env python3
"""Tests for scripts/forge/spec-cost.py (stdlib unittest; Python 3.9+).

Each test builds a throwaway transcript dir in the Claude Code JSONL shape: main sessions `<session>.jsonl` and
subagents `<session>/subagents/agent-<id>.jsonl` with their `.meta.json` sidecars, plus a throwaway prices file.
No real transcript is read. All data is invented.

Run: python3 -m unittest discover -s tests/scripts/forge -v
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SCRIPT = os.path.join(REPO, "scripts", "forge", "spec-cost.py")
_spec = importlib.util.spec_from_file_location("spec_cost", SCRIPT)
sc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sc)

SINCE, UNTIL = "2026-01-01T09:00:00Z", "2026-01-01T18:00:00Z"
# 1M input tokens and 1M output tokens: the cost is input rate + output rate.
MILLION = {"input_tokens": 1_000_000, "output_tokens": 1_000_000}
PRICES = {
    "verified": "UNVERIFIED", "source": "https://example.invalid/prices", "fast_multiplier": 2.0,
    "models": {
        "model-alpha": {"input": 1.0, "output": 2.0, "cache_write_5m": 1.25, "cache_write_1h": 2.0, "cache_read": 0.1},
        "model-beta": {"input": 10.0, "output": 20.0, "cache_write_5m": 12.5, "cache_write_1h": 20.0,
                       "cache_read": 1.0},
        "model-small": {"input": 0.1, "output": 0.5, "cache_write_5m": 0.125, "cache_write_1h": 0.2,
                        "cache_read": 0.01,
                        "long_context": {"threshold": 100_000, "input": 0.5, "output": 2.5, "cache_write_5m": 0.625,
                                         "cache_write_1h": 1.0, "cache_read": 0.05}},
    },
}
RUNNER = "Forge conductor mode, phase runner. Phase: {}. Feature: specs/900-fixture. Branch: spec/900-fixture."
GATE = "Independent gate reviewer. Gate: {}. Feature: specs/900-fixture."
SPEC = "spec/900-fixture"


def ts(minute: int, hour: int = 10) -> str:
    return f"2026-01-01T{hour:02d}:{minute:02d}:00.000Z"


class Fixture:
    """A transcript dir under a temp root; calls get unique message and request ids."""

    def __init__(self, root: str) -> None:
        self.dir = os.path.join(root, "projects", "-tmp-fixture")
        os.makedirs(self.dir)
        self.serial = 0

    def assistant(self, when: str, branch: str = SPEC, model: str = "model-alpha", usage: dict | None = None,
                  msg_id: str | None = None, cwd: str = "/tmp/fixture") -> dict:
        self.serial += 1
        msg_id = msg_id or f"msg-{self.serial}"
        return {"type": "assistant", "timestamp": when, "uuid": f"u-{self.serial}", "requestId": f"req-{msg_id}",
                "gitBranch": branch, "cwd": cwd,
                "message": {"id": msg_id, "model": model, "usage": dict(usage or MILLION)}}

    @staticmethod
    def user(when: str, text: str, origin: str | None = None) -> dict:
        entry = {"type": "user", "timestamp": when, "message": {"role": "user", "content": text}}
        if origin:
            entry["origin"] = {"kind": origin}
        return entry

    def write(self, rel: str, entries: list[dict]) -> str:
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(json.dumps(e) for e in entries) + "\n")
        return path

    def session(self, name: str, calls: list[dict], prompt: str = "hello") -> str:
        return self.write(f"{name}.jsonl", [self.user(ts(0), prompt, origin="human"), *calls])

    def agent(self, session: str, agent_id: str, prompt: str, calls: list[dict], parent: str | None = None) -> str:
        meta = {"agentType": "general-purpose", "spawnDepth": 2 if parent else 1}
        if parent:
            meta["parentAgentId"] = parent
        path = self.write(f"{session}/subagents/agent-{agent_id}.jsonl", [self.user(calls[0]["timestamp"], prompt),
                                                                         *calls])
        with open(path[:-len(".jsonl")] + ".meta.json", "w", encoding="utf-8") as handle:
            json.dump(meta, handle)
        return path


class SpecCostCase(unittest.TestCase):
    def setUp(self) -> None:
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        self.fx = Fixture(self.root)
        self.prices = self.write_prices(PRICES)

    def write_prices(self, data: object, name: str = "prices.json") -> str:
        path = os.path.join(self.root, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(data if isinstance(data, str) else json.dumps(data))
        return path

    def run_cli(self, *extra: str, window: bool = True) -> tuple[int, str, str]:
        argv = (["--since", SINCE, "--until", UNTIL] if window else []) + [
            "--project-dir", self.fx.dir, "--prices", self.prices, "--integration-branch", "trunk", *extra]
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = sc.main(argv)
        return code, out.getvalue(), err.getvalue()

    @staticmethod
    def line(out: str, prefix: str) -> str:
        return next(ln for ln in out.splitlines() if ln.lstrip().startswith(prefix))


class PricesTests(SpecCostCase):
    def test_shipped_prices_file_loads_and_is_marked(self) -> None:
        prices = sc.load_prices(sc.DEFAULT_PRICES)
        self.assertIn("claude-opus-5-5", prices["models"])
        self.assertTrue(prices["verified"])
        self.assertTrue(prices["source"].startswith("https://"))

    def test_cost_is_input_plus_output_rate_per_million(self) -> None:
        prices = sc.load_prices(self.prices)
        tokens = {"in": 1_000_000, "cw5m": 0, "cw1h": 0, "cr": 0, "out": 1_000_000}
        self.assertAlmostEqual(sc.call_cost("model-alpha", tokens, None, prices), 3.0)
        self.assertAlmostEqual(sc.call_cost("model-alpha", tokens, "fast", prices), 6.0)

    def test_cache_fields_use_their_rates(self) -> None:
        prices = sc.load_prices(self.prices)
        tokens = {"in": 0, "cw5m": 1_000_000, "cw1h": 1_000_000, "cr": 1_000_000, "out": 0}
        self.assertAlmostEqual(sc.call_cost("model-alpha", tokens, None, prices), 1.25 + 2.0 + 0.1)

    def test_long_context_rates_apply_above_the_threshold(self) -> None:
        prices = sc.load_prices(self.prices)
        short = {"in": 100_000, "cw5m": 0, "cw1h": 0, "cr": 0, "out": 0}
        long = {"in": 100_001, "cw5m": 0, "cw1h": 0, "cr": 0, "out": 0}
        self.assertAlmostEqual(sc.call_cost("model-small", short, None, prices), 0.01)
        self.assertAlmostEqual(sc.call_cost("model-small", long, None, prices), 100_001 * 0.5 / 1_000_000)

    def test_model_id_tags_are_stripped(self) -> None:
        prices = sc.load_prices(self.prices)
        self.assertIs(sc.model_rates("model-alpha[1m]", prices), prices["models"]["model-alpha"])
        self.assertIs(sc.model_rates("model-alpha-20260101", prices), prices["models"]["model-alpha"])
        self.assertIsNone(sc.model_rates("model-gamma", prices))

    def test_a_newer_id_sharing_a_prefix_is_unpriced(self) -> None:
        # Regression: a family-prefix match priced an unknown newer id at an older model's rates.
        prices = sc.load_prices(self.prices)
        self.assertIsNone(sc.model_rates("model-alpha-7", prices))
        tokens = {"in": 1, "cw5m": 0, "cw1h": 0, "cr": 0, "out": 1}
        self.assertIsNone(sc.call_cost("model-alpha-7", tokens, None, prices))

    def test_unknown_model_and_unpriced_fast_mode_are_none_not_zero(self) -> None:
        data = json.loads(json.dumps(PRICES))
        del data["fast_multiplier"]
        prices = sc.load_prices(self.write_prices(data))
        tokens = {"in": 1, "cw5m": 0, "cw1h": 0, "cr": 0, "out": 1}
        self.assertIsNone(sc.call_cost("model-gamma", tokens, None, prices))
        self.assertIsNone(sc.call_cost("model-alpha", tokens, "fast", prices))

    def test_unusable_prices_files_exit_2(self) -> None:
        self.fx.session("s1", [self.fx.assistant(ts(1))])
        bad_rate = json.loads(json.dumps(PRICES))
        bad_rate["models"]["model-alpha"]["cache_read"] = "cheap"
        no_verified = {k: v for k, v in PRICES.items() if k != "verified"}
        cases = {"missing": None, "not json": "{nope", "no models": {**PRICES, "models": {}},
                 "bad rate": bad_rate, "no verified": no_verified}
        for label, data in cases.items():
            with self.subTest(label):
                self.prices = (os.path.join(self.root, "absent.json") if data is None
                               else self.write_prices(data, f"{label}.json"))
                code, out, err = self.run_cli()
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                self.assertIn("prices file", err)


class TotalsTests(SpecCostCase):
    def test_total_is_marked_as_a_lower_bound(self) -> None:
        self.fx.session("s1", [self.fx.assistant(ts(1))])
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        lines = out.splitlines()
        total = next(i for i, ln in enumerate(lines) if ln.startswith("total "))
        self.assertEqual(lines[total + 1], "note: lower bound (assistant responses only)")

    def test_broken_lines_are_skipped_not_fatal(self) -> None:
        # Regression: a half-written UTF-8 character, a JSON list and a string message each raised a traceback.
        path = self.fx.session("s1", [self.fx.assistant(ts(1))])
        with open(path, "ab") as handle:
            handle.write(b'{"type": "assistant", "usage": "\xe2\x82\n')
            handle.write(b'["usage", 1]\n')
            handle.write(json.dumps({"type": "assistant", "timestamp": ts(2), "message": "usage"}).encode() + b"\n")
            handle.write(json.dumps({"type": "user", "timestamp": ts(3), "message": "usage"}).encode() + b"\n")
        agent = self.fx.agent("s1", "a1", "\u00e9 chore", [self.fx.assistant(ts(4))])
        with open(agent, "rb") as handle:
            raw = handle.read()
        with open(agent, "wb") as handle:
            handle.write(b'["user"]\n{"type": "user", "x": "\xff"}\n' + raw)
        code, out, err = self.run_cli("--by-phase", "--by-branch")
        self.assertEqual(code, 0, err)
        self.assertIn("api calls 2", out)
        with open(os.path.join(self.root, "list.jsonl"), "w", encoding="utf-8") as handle:
            handle.write('["user"]\n')
        self.assertIsNone(sc.first_user_text(os.path.join(self.root, "list.jsonl")))
        self.assertIsNone(sc.message_text({"type": "user", "message": "text"}))

    def test_a_call_straddling_until_counts_whole_in_its_first_window(self) -> None:
        # Regression: only the streamed lines before --until were counted, so the output tokens were cut short.
        first = self.fx.assistant("2026-01-01T17:59:59.000Z", usage={"input_tokens": 1_000_000, "output_tokens": 1},
                                  msg_id="m1")
        last = self.fx.assistant("2026-01-01T18:00:01.000Z", msg_id="m1")
        late = self.fx.assistant("2026-01-01T18:00:02.000Z", msg_id="m2")
        self.fx.session("s1", [first, last, late])
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("total $3.00  api calls 1", out)

    def test_timestamps_with_compact_offsets_and_odd_fractions_parse_on_every_python(self) -> None:
        # Regression: Python 3.9's fromisoformat rejected `+0200` and `.5Z`.
        self.fx.session("s1", [self.fx.assistant(ts(1))])
        code, out, err = self.run_cli("--since", "2026-01-01T11:00:00+0200", "--until", "2026-01-01T18:00:00.5Z",
                                      window=False)
        self.assertEqual(code, 0, err)
        self.assertIn("window 2026-01-01T09:00:00Z -> 2026-01-01T18:00:00Z", out)
        self.assertEqual(sc.parse_ts("2026-01-01T10:00:00.1234567-0130").isoformat(),
                         "2026-01-01T11:30:00.123456+00:00")
        self.assertEqual(sc.parse_ts("2026-01-01T10:00:00").isoformat(), "2026-01-01T10:00:00+00:00")

    def test_streamed_lines_are_deduplicated_keeping_the_largest_counters(self) -> None:
        partial = self.fx.assistant(ts(1), usage={"input_tokens": 1_000_000, "output_tokens": 10}, msg_id="m1")
        final = self.fx.assistant(ts(1), usage={"input_tokens": 1_000_000, "output_tokens": 1_000_000}, msg_id="m1")
        self.fx.session("s1", [partial, final, self.fx.assistant(ts(2))])
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("total $6.00  api calls 2  transcript files 1", out)
        self.assertIn("SUMMARY wall=9:00 cost=$6.00", out)
        self.assertIn("verified UNVERIFIED", out)

    def test_window_bounds_and_subagents_count(self) -> None:
        self.fx.session("s1", [self.fx.assistant(ts(0, hour=8)), self.fx.assistant(ts(1)),
                               self.fx.assistant(ts(0, hour=19))])
        self.fx.agent("s1", "a1", "chore", [self.fx.assistant(ts(5), model="model-beta")])
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("total $33.00  api calls 2  transcript files 2", out)

    def test_unknown_model_is_counted_in_tokens_and_cost_unknown(self) -> None:
        self.fx.session("s1", [self.fx.assistant(ts(1)), self.fx.assistant(ts(2), model="model-gamma")])
        code, out, _ = self.run_cli("--by-branch")
        self.assertEqual(code, 0)
        row = self.line(out, "model-gamma")
        self.assertIn("in 1.00M", row)
        self.assertIn("cost unknown", row)
        self.assertIn("unpriced models: model-gamma", self.line(out, "total "))
        self.assertIn("unpriced 1", self.line(out, SPEC))
        self.assertTrue(out.rstrip().endswith("SUMMARY wall=9:00 cost=$3.00 unpriced=yes"))

    def test_branch_filter_and_by_branch_lists_the_integration_branch_first(self) -> None:
        self.fx.session("s1", [self.fx.assistant(ts(1), branch="trunk"), self.fx.assistant(ts(2)),
                               self.fx.assistant(ts(3), model="model-beta")])
        code, out, _ = self.run_cli("--by-branch")
        self.assertEqual(code, 0)
        rows = out.split("by branch (trunk = conductor overhead):\n")[1].splitlines()
        self.assertTrue(rows[0].lstrip().startswith("trunk "))
        self.assertTrue(rows[1].lstrip().startswith(SPEC))
        code, out, _ = self.run_cli("--branch", SPEC)
        self.assertIn("total $33.00  api calls 2", out)
        self.assertIn(f"branch {SPEC}: window wall 9:00, active span 0:01", out)

    def test_since_first_prompt_starts_at_the_human_prompt(self) -> None:
        self.fx.write("s1.jsonl", [self.fx.user(ts(0, hour=8), "<system-reminder>x</system-reminder>"),
                                   self.fx.user(ts(30), "go", origin="human"), self.fx.assistant(ts(10)),
                                   self.fx.assistant(ts(40))])
        code, out, _ = self.run_cli("--since-first-prompt", "s1", "--until", UNTIL, window=False)
        self.assertEqual(code, 0)
        self.assertIn("window 2026-01-01T10:30:00Z -> 2026-01-01T18:00:00Z  wall 7:30", out)
        self.assertIn("api calls 1", out)

    def test_bad_arguments_exit_2(self) -> None:
        self.fx.session("s1", [self.fx.assistant(ts(1))])
        with self.assertRaises(SystemExit) as raised:  # --since missing: argparse exits 2
            self.run_cli("--until", UNTIL, window=False)
        self.assertEqual(raised.exception.code, 2)
        cases = {
            "until before since": ["--since", UNTIL, "--until", SINCE],
            "bad timestamp": ["--since", "yesterday"],
            "unknown session": ["--since-first-prompt", "nope"],
        }
        for label, argv in cases.items():
            with self.subTest(label):
                code, _, err = self.run_cli(*argv, window=False)
                self.assertEqual(code, 2)
                self.assertIn("error:", err)
        os.rename(self.fx.dir, self.fx.dir + "-gone")
        self.assertEqual(self.run_cli()[0], 2)

    def test_cli_entry_point_is_executable(self) -> None:
        self.fx.session("s1", [self.fx.assistant(ts(1))])
        self.assertTrue(os.access(SCRIPT, os.X_OK))
        proc = subprocess.run([sys.executable, SCRIPT, "--since", SINCE, "--until", UNTIL, "--project-dir",
                               self.fx.dir, "--prices", self.prices], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("SUMMARY wall=9:00 cost=$3.00", proc.stdout)
        proc = subprocess.run([sys.executable, SCRIPT, "--until", UNTIL], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)


class IntegrationBranchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.repo)

    def write_config(self, text: str) -> None:
        os.makedirs(os.path.join(self.repo, ".claude"), exist_ok=True)
        with open(os.path.join(self.repo, ".claude", "project-config.json"), "w", encoding="utf-8") as handle:
            handle.write(text)

    def test_defaults_to_main(self) -> None:
        self.assertEqual(sc.integration_branch(self.repo), "main")
        self.write_config(json.dumps({"PROJECT_NAME": "x"}))
        self.assertEqual(sc.integration_branch(self.repo), "main")

    def test_reads_default_branch(self) -> None:
        self.write_config(json.dumps({"DEFAULT_BRANCH": "develop"}))
        self.assertEqual(sc.integration_branch(self.repo), "develop")

    def test_broken_config_is_a_usage_error(self) -> None:
        for text in ("{nope", json.dumps({"DEFAULT_BRANCH": ""}), json.dumps({"DEFAULT_BRANCH": 3})):
            with self.subTest(text):
                self.write_config(text)
                with self.assertRaises(sc.UsageError):
                    sc.integration_branch(self.repo)


class AllTreesTests(unittest.TestCase):
    def test_dirs_and_cwd_of_worktrees_and_removed_siblings(self) -> None:
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        main, lane = "/work/app", "/work/lanes/app-b"
        for name in ("-work-app", "-work-app-old", "-work-app2", "-work-lanes-app-b", "-elsewhere"):
            os.makedirs(os.path.join(root, name))
        dirs = [os.path.basename(d) for d in sc.tree_project_dirs(root, [main, lane], main)]
        self.assertEqual(dirs, ["-work-app", "-work-app-old", "-work-lanes-app-b"])
        allowed = ["/work/app", "/work/app/sub", "/work/lanes/app-b", "/work/app-old"]
        for cwd in allowed:
            self.assertTrue(sc.cwd_allowed(cwd, [main, lane], main), cwd)
        for cwd in ("/work/application", "/work/other", None):
            self.assertFalse(sc.cwd_allowed(cwd, [main, lane], main), cwd)


class LabelTests(unittest.TestCase):
    def test_phase_runner_labels(self) -> None:
        cases = {
            RUNNER.format("/specify"): "/specify",
            RUNNER.format("plan"): "/plan",
            RUNNER.format("/execute-task task 003"): "/execute-task",
            RUNNER.format("/execute-task wave W2"): "/execute-task",
            RUNNER.format("research"): "/research",
            RUNNER.format("closing (/summarize + /finalize)"): "closing",
            RUNNER.format("rebase"): "rebase",
            RUNNER.format("pr-update"): "pr-update",
            RUNNER.format("closing"): "closing",
            # Regression: the conductor's Phases table names the wave phase `wave`; it was not counted as waves.
            "Forge conductor mode, phase runner. Phase: wave W2. Feature: specs/001-x. Branch: spec/001-x.":
                "/execute-task",
            "  \n" + RUNNER.format("/verify"): "/verify",
        }
        for text, phase in cases.items():
            with self.subTest(text):
                self.assertEqual(sc.parse_label(text), (phase, "runner"))

    def test_gate_reviewer_labels(self) -> None:
        self.assertEqual(sc.parse_label(GATE.format("spec-gate")), ("spec-gate", "gate"))
        self.assertEqual(sc.parse_label(GATE.format("plan-gate, lens security")), ("plan-gate-security", "gate"))
        self.assertEqual(sc.parse_label(GATE.format("breakdown-gate")), ("breakdown-gate", "gate"))

    def test_anything_else_is_other(self) -> None:
        for text in (None, "", "Fix the flaky test", "Acme conductor mode, phase runner. Phase: /plan.",
                     "Forge conductor mode, gate reviewer. Gate: spec-gate.", "Forge conductor mode, phase runner."):
            with self.subTest(text):
                self.assertEqual(sc.parse_label(text), ("other", "other"))


class ByPhaseTests(SpecCostCase):
    def build_spec(self) -> None:
        """A spec flow: main session on trunk; a /specify runner (10:00-10:30) whose nested spec-gate reviewer
        (10:10-10:20) has a nested helper; a /plan runner on trunk then the spec branch; two /verify runs, the first
        launching a nested /fix runner; an unlabeled run."""
        fx = self.fx
        fx.session("s1", [fx.assistant(ts(0), branch="trunk"), fx.assistant(ts(59), branch="trunk")])
        fx.agent("s1", "spec", RUNNER.format("/specify"), [fx.assistant(ts(0)), fx.assistant(ts(30))])
        fx.agent("s1", "gate", GATE.format("spec-gate"), [fx.assistant(ts(10)), fx.assistant(ts(20))],
                 parent="spec")
        fx.agent("s1", "helper", "look up the callers", [fx.assistant(ts(15))], parent="gate")
        fx.agent("s1", "plan", RUNNER.format("/plan"), [fx.assistant(ts(0, hour=11), branch="trunk"),
                                                        fx.assistant(ts(20, hour=11))])
        fx.agent("s1", "v1", RUNNER.format("/verify"), [fx.assistant(ts(0, hour=12)), fx.assistant(ts(30, hour=12))])
        fx.agent("s1", "fix", RUNNER.format("/fix"), [fx.assistant(ts(5, hour=12)), fx.assistant(ts(15, hour=12))],
                 parent="v1")
        fx.agent("s1", "v2", RUNNER.format("/verify"), [fx.assistant(ts(0, hour=13)), fx.assistant(ts(10, hour=13))])
        fx.agent("s1", "misc", "Resume where you stopped", [fx.assistant(ts(0, hour=14)),
                                                           fx.assistant(ts(5, hour=14))])

    def test_wave_runner_counts_as_waves(self) -> None:
        fx = self.fx
        fx.agent("s1", "w2", "Forge conductor mode, phase runner. Phase: wave W2. Feature: specs/001-x. "
                 "Branch: spec/001-x.", [fx.assistant(ts(0), branch="spec/001-x"),
                                         fx.assistant(ts(25), branch="spec/001-x")])
        code, out, _ = self.run_cli("--by-phase")
        self.assertEqual(code, 0)
        self.assertIn("runs   1  wall   0:25", self.line(out, "/execute-task "))
        self.assertIn("TIMING spec/001-x wall 0:25; gates 0:00 (0%); rework 0:00 (0%); waves 0:25;", out)

    def test_phase_rows_gate_split_and_timing(self) -> None:
        self.build_spec()
        code, out, _ = self.run_cli("--by-phase", "--branch", SPEC)
        self.assertEqual(code, 0)
        specify = self.line(out, "/specify ")
        self.assertIn("runs   1  wall   0:20  span   0:30  calls     2", specify)  # gate time taken out
        gate = self.line(out, "spec-gate ")
        self.assertIn("runs   1  wall   0:10  span   0:10  calls     3", gate)  # helper rolled into the gate
        self.assertIn("$    9.00", gate)
        plan = self.line(out, "/plan ")
        self.assertIn("runs   1  wall   0:20", plan)  # kept whole: one call was on the named branch
        verify = self.line(out, "/verify ")
        self.assertIn("runs   2  wall   0:40  span   1:10  calls     6", verify)
        self.assertIn("runs   1  wall   0:10", self.line(out, "(nested /fix)"))
        self.assertIn("(main sessions)", out)
        self.assertIn("calls 0  $0.00", self.line(out, "(main sessions)"))  # trunk calls filtered out
        order = [ln.split()[0] for ln in out.split("by phase")[1].splitlines()[1:6]]
        self.assertEqual(order, ["/specify", "spec-gate", "/plan", "/verify", "other"])
        # wall = 20 + 10 + 20 + 30 + 10 = 1:30; gates 10m; rework = second /verify 10m + nested /fix 10m.
        self.assertIn(f"TIMING {SPEC} wall 1:30; gates 0:10 (11%); rework 0:20 (22%); waves 0:00; "
                      "unlabeled 1 runs 0:05", out)

    def test_main_sessions_without_branch_filter(self) -> None:
        self.build_spec()
        code, out, _ = self.run_cli("--by-phase")
        self.assertEqual(code, 0)
        self.assertIn("calls 2  $6.00", self.line(out, "(main sessions)"))
        self.assertIn("by phase", out)

    def test_parallel_gate_lenses_are_each_taken_out_of_the_runner_once(self) -> None:
        fx = self.fx
        fx.agent("s1", "plan", RUNNER.format("/plan"), [fx.assistant(ts(0)), fx.assistant(ts(40))])
        for lens, (start, end) in {"architect": (10, 20), "security": (15, 25), "qa": (30, 35)}.items():
            fx.agent("s1", lens, GATE.format(f"plan-gate, lens {lens}"), [fx.assistant(ts(start)),
                                                                         fx.assistant(ts(end))], parent="plan")
        code, out, _ = self.run_cli("--by-phase")
        self.assertEqual(code, 0)
        self.assertIn("wall   0:20", self.line(out, "/plan "))  # 40 minus the union 10-25 and 30-35
        for lens in ("architect", "security", "qa"):
            self.assertIn("runs   1", self.line(out, f"plan-gate-{lens} "))
        self.assertIn(f"TIMING {SPEC} wall 0:45; gates 0:25 (56%)", out)

    def test_unpriced_calls_are_marked_in_phase_rows(self) -> None:
        fx = self.fx
        fx.agent("s1", "rev", RUNNER.format("/review"), [fx.assistant(ts(0)), fx.assistant(ts(5), model="model-z")])
        code, out, _ = self.run_cli("--by-phase")
        self.assertEqual(code, 0)
        row = self.line(out, "/review ")
        self.assertIn("$    3.00", row)
        self.assertTrue(row.endswith("unpriced 1"))

    def test_resume_message_does_not_change_the_phase(self) -> None:
        fx = self.fx
        fx.write("s1/subagents/agent-spec.jsonl", [
            fx.user(ts(0), RUNNER.format("/specify")), fx.assistant(ts(1)),
            fx.user(ts(20), "The coordinator sent a message while you were working:\n" + RUNNER.format("/plan")),
            fx.assistant(ts(25))])
        code, out, _ = self.run_cli("--by-phase")
        self.assertEqual(code, 0)
        self.assertIn("runs   1  wall   0:24", self.line(out, "/specify "))
        self.assertNotIn("/plan ", out)


if __name__ == "__main__":
    unittest.main()
