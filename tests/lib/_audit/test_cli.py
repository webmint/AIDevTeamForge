"""Tests for src/devforge/lib/_audit/_cli.py (CLI smoke tests for Phase 5).

Coverage:
  build_parser    — returns ArgumentParser; exactly 18 subcommands registered.
  main            — no subcommand → exit 2; help → exit 2.
  per-verb args   — each verb's namespace has a `func` attribute wired.
  e2e smokes      — resolve-mode --full → exit 0 + JSON {mode: broad};
                    check-agents --agents-dir /nonexistent → exit 3.
  verb guard      — registered set matches expected 18-verb constant.
"""

import argparse
import json
import sys
import tempfile
import os
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "audit_helper.py"
_REFERENCES_DIR = _REPO_ROOT / "src" / "commands" / "audit" / "references"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _audit._cli import build_parser, main  # noqa: E402


# ---------------------------------------------------------------------------
# The canonical 18-verb list (Phase 0–5). Guard against accidental drops.
# ---------------------------------------------------------------------------
_EXPECTED_VERBS = frozenset([
    "resolve-mode",
    "check-agents",
    "preflight-context",
    "check-status-and-flip",
    "compute-hotspots",
    "render-hotspot-summary",
    "resolve-scope",
    "render-scope-block",
    "render-agent-brief",
    "consume-tmp",
    "validate-findings",
    "compute-consensus",
    "force-rank-top10",
    "map-recurring-issues",
    "render-report",
    "render-inline-summary",
    "cleanup-tmps",
    "merge-passes",
])


def _capture_main(argv):
    """Run main(argv) and return (exit_code, stdout_str, stderr_str).

    Redirects sys.stdout / sys.stderr to StringIO for capture.
    """
    import io

    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        code = main(argv)
    finally:
        out = sys.stdout.getvalue()
        err = sys.stderr.getvalue()
        sys.stdout, sys.stderr = old_out, old_err
    return code, out, err


# ---------------------------------------------------------------------------
# Parser structure tests
# ---------------------------------------------------------------------------


class TestBuildParser(unittest.TestCase):
    def test_returns_argument_parser(self):
        parser = build_parser()
        self.assertIsInstance(parser, argparse.ArgumentParser)

    def test_exactly_18_verbs_registered(self):
        """build_parser registers exactly the 18 expected verbs — no more, no fewer."""
        parser = build_parser()
        # Walk the _subparsers action to collect registered verb names.
        registered = set()
        for action in parser._subparsers._actions:
            if hasattr(action, "_name_parser_map"):
                registered.update(action._name_parser_map.keys())
        self.assertEqual(registered, _EXPECTED_VERBS,
                         msg="Verb set mismatch — check _SUBCOMMAND_REGISTRY in _cli.py")

    def test_no_subcommand_has_no_func(self):
        """Parsing with no subcommand produces no `func` attribute."""
        parser = build_parser()
        args = parser.parse_args([])
        self.assertFalse(hasattr(args, "func"))

    def test_prog_name(self):
        parser = build_parser()
        self.assertEqual(parser.prog, "audit_helper")


# ---------------------------------------------------------------------------
# Per-verb: func attribute is wired + minimal required args parse cleanly
# ---------------------------------------------------------------------------


class TestPerVerbFuncWired(unittest.TestCase):
    """Each verb's namespace must have a callable `func` attribute after parsing."""

    def _parse(self, argv):
        return build_parser().parse_args(argv)

    def test_resolve_mode_func_wired(self):
        # resolve-mode has only an optional positional; bare verb is valid.
        args = self._parse(["resolve-mode"])
        self.assertTrue(callable(args.func))

    def test_resolve_mode_positional_optional(self):
        """resolve-mode positional is optional — parsing bare verb works."""
        args = self._parse(["resolve-mode"])
        self.assertTrue(callable(args.func))

    def test_render_agent_brief_finding_cap_default(self):
        args = self._parse(
            ["render-agent-brief", "--agent", "code-reviewer",
             "--scope", "/tmp/sc.json"]
        )
        self.assertEqual(args.finding_cap, 30)

    def test_render_agent_brief_finding_cap_custom(self):
        args = self._parse(
            ["render-agent-brief", "--agent", "code-reviewer",
             "--scope", "/tmp/sc.json", "--finding-cap", "58"]
        )
        self.assertEqual(args.finding_cap, 58)

    def test_check_agents_func_wired(self):
        args = self._parse(["check-agents"])
        self.assertTrue(callable(args.func))

    def test_check_agents_agents_dir_default(self):
        args = self._parse(["check-agents"])
        self.assertEqual(args.agents_dir, ".claude/agents")

    def test_check_agents_agents_dir_override(self):
        args = self._parse(["check-agents", "--agents-dir", "/tmp/agents"])
        self.assertEqual(args.agents_dir, "/tmp/agents")

    def test_preflight_context_func_wired(self):
        args = self._parse(["preflight-context"])
        self.assertTrue(callable(args.func))

    def test_preflight_context_workspace_root_default(self):
        args = self._parse(["preflight-context"])
        self.assertEqual(args.workspace_root, ".")

    def test_check_status_and_flip_func_wired(self):
        args = self._parse(["check-status-and-flip"])
        self.assertTrue(callable(args.func))

    def test_check_status_and_flip_to_optional(self):
        args = self._parse(["check-status-and-flip"])
        self.assertIsNone(args.to)

    def test_check_status_and_flip_with_to(self):
        args = self._parse(["check-status-and-flip", "--to", "1"])
        self.assertEqual(args.to, "1")

    def test_compute_hotspots_func_wired(self):
        # --callers is not required at parse-time (only at handler time).
        args = self._parse(["compute-hotspots"])
        self.assertTrue(callable(args.func))

    def test_compute_hotspots_defaults(self):
        args = self._parse(["compute-hotspots"])
        self.assertEqual(args.top, 25)
        self.assertEqual(args.since, "90.days.ago")

    def test_compute_hotspots_top_override(self):
        args = self._parse(["compute-hotspots", "--top", "10"])
        self.assertEqual(args.top, 10)

    def test_render_hotspot_summary_requires_hotspot(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["render-hotspot-summary"])

    def test_render_hotspot_summary_func_wired(self):
        args = self._parse(["render-hotspot-summary", "--hotspot", "/tmp/hs.json"])
        self.assertTrue(callable(args.func))

    def test_resolve_scope_requires_mode_result(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["resolve-scope"])

    def test_resolve_scope_func_wired(self):
        args = self._parse(["resolve-scope", "--mode-result", "/tmp/mr.json"])
        self.assertTrue(callable(args.func))

    def test_render_scope_block_requires_scope(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["render-scope-block"])

    def test_render_scope_block_func_wired(self):
        args = self._parse(["render-scope-block", "--scope", "/tmp/sc.json"])
        self.assertTrue(callable(args.func))

    def test_render_agent_brief_requires_agent_and_scope(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["render-agent-brief"])

    def test_render_agent_brief_func_wired(self):
        args = self._parse([
            "render-agent-brief",
            "--agent", "code-reviewer",
            "--scope", "/tmp/sc.json",
        ])
        self.assertTrue(callable(args.func))

    def test_render_agent_brief_tmp_path_default_none(self):
        """--tmp-path defaults to None when omitted."""
        args = self._parse([
            "render-agent-brief",
            "--agent", "architect",
            "--scope", "/tmp/sc.json",
        ])
        self.assertIsNone(args.tmp_path)

    def test_render_agent_brief_tmp_path_custom(self):
        """--tmp-path stores the provided path string verbatim."""
        path = "/tmp/forge-audit-abc/tmp-architect-p1.md"
        args = self._parse([
            "render-agent-brief",
            "--agent", "architect",
            "--scope", "/tmp/sc.json",
            "--tmp-path", path,
        ])
        self.assertEqual(args.tmp_path, path)

    def test_consume_tmp_requires_tmp(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["consume-tmp"])

    def test_consume_tmp_func_wired(self):
        args = self._parse(["consume-tmp", "--tmp", "/tmp/agent.md"])
        self.assertTrue(callable(args.func))

    def test_validate_findings_requires_findings(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["validate-findings"])

    def test_validate_findings_func_wired(self):
        args = self._parse(["validate-findings", "--findings", "/tmp/f.json"])
        self.assertTrue(callable(args.func))

    def test_compute_consensus_requires_findings(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["compute-consensus"])

    def test_compute_consensus_func_wired(self):
        args = self._parse(["compute-consensus", "--findings", "/tmp/f.json"])
        self.assertTrue(callable(args.func))

    def test_force_rank_top10_requires_findings(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["force-rank-top10"])

    def test_force_rank_top10_func_wired(self):
        args = self._parse(["force-rank-top10", "--findings", "/tmp/f.json"])
        self.assertTrue(callable(args.func))

    def test_force_rank_top10_narrow_default_false(self):
        args = self._parse(["force-rank-top10", "--findings", "/tmp/f.json"])
        self.assertFalse(args.narrow)

    def test_force_rank_top10_narrow_flag(self):
        args = self._parse(["force-rank-top10", "--findings", "/tmp/f.json", "--narrow"])
        self.assertTrue(args.narrow)

    def test_map_recurring_issues_requires_both(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["map-recurring-issues"])

    def test_map_recurring_issues_func_wired(self):
        args = self._parse([
            "map-recurring-issues",
            "--findings", "/tmp/f.json",
            "--recurring", "/tmp/r.json",
        ])
        self.assertTrue(callable(args.func))

    def test_render_report_requires_report_and_date(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["render-report"])

    def test_render_report_func_wired(self):
        args = self._parse([
            "render-report",
            "--report", "/tmp/r.json",
            "--date", "2026-06-01",
        ])
        self.assertTrue(callable(args.func))

    def test_render_inline_summary_requires_report(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["render-inline-summary"])

    def test_render_inline_summary_func_wired(self):
        args = self._parse(["render-inline-summary", "--report", "/tmp/r.json"])
        self.assertTrue(callable(args.func))

    def test_cleanup_tmps_func_wired(self):
        args = self._parse(["cleanup-tmps"])
        self.assertTrue(callable(args.func))

    def test_cleanup_tmps_audits_dir_default(self):
        args = self._parse(["cleanup-tmps"])
        self.assertEqual(args.audits_dir, "audits")


# ---------------------------------------------------------------------------
# main() dispatch tests
# ---------------------------------------------------------------------------


class TestMainDispatch(unittest.TestCase):
    def test_no_subcommand_returns_2(self):
        """main([]) prints help to stderr and returns 2."""
        code, out, err = _capture_main([])
        self.assertEqual(code, 2)

    def test_help_flag_triggers_sys_exit(self):
        """--help causes SystemExit (argparse default behavior)."""
        with self.assertRaises(SystemExit) as cm:
            main(["--help"])
        self.assertEqual(cm.exception.code, 0)

    def test_resolve_mode_full_returns_0_and_broad_json(self):
        """resolve-mode with '--full' as positional string exits 0, mode=broad.

        The positional `arguments` is the raw $ARGUMENTS string — it must be
        passed after the '--' separator so argparse treats the '--full' token
        as a value, not an unrecognised flag.
        """
        code, out, err = _capture_main(["resolve-mode", "--", "--full"])
        self.assertEqual(code, 0, msg="stderr: " + err)
        data = json.loads(out)
        self.assertEqual(data.get("mode"), "broad")

    def test_resolve_mode_empty_returns_0_and_broad_json(self):
        """resolve-mode with no positional (empty $ARGUMENTS) exits 0, mode=broad."""
        code, out, err = _capture_main(["resolve-mode"])
        self.assertEqual(code, 0, msg="stderr: " + err)
        data = json.loads(out)
        self.assertEqual(data.get("mode"), "broad")

    def test_resolve_mode_uncommitted_returns_0_and_narrow_json(self):
        """resolve-mode with '--uncommitted' as positional string → mode=narrow."""
        code, out, err = _capture_main(["resolve-mode", "--", "--uncommitted"])
        self.assertEqual(code, 0, msg="stderr: " + err)
        data = json.loads(out)
        self.assertEqual(data.get("mode"), "narrow")

    def test_resolve_mode_top_returns_0_and_hotspot_json(self):
        """resolve-mode with '--top 10' as positional string → mode=hotspot."""
        code, out, err = _capture_main(["resolve-mode", "--", "--top 10"])
        self.assertEqual(code, 0, msg="stderr: " + err)
        data = json.loads(out)
        self.assertEqual(data.get("mode"), "hotspot")

    def test_check_agents_missing_dir_returns_3(self):
        """check-agents with a non-existent --agents-dir exits 3 (all_missing)."""
        code, out, err = _capture_main(["check-agents", "--agents-dir", "/nonexistent"])
        self.assertEqual(code, 3)
        # Should still emit JSON with all_missing=true
        data = json.loads(out)
        self.assertTrue(data.get("all_missing"))

    def test_check_agents_returns_valid_json(self):
        """check-agents always emits parseable JSON on stdout."""
        code, out, err = _capture_main(["check-agents", "--agents-dir", "/nonexistent"])
        data = json.loads(out)
        self.assertIn("all_missing", data)
        self.assertIn("present", data)
        self.assertIn("missing", data)

    def test_cleanup_tmps_empty_dir_returns_0(self):
        """cleanup-tmps with a non-existent audits dir returns 0 and {deleted:0}."""
        code, out, err = _capture_main(["cleanup-tmps", "--audits-dir", "/nonexistent"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data.get("deleted"), 0)

    def test_cleanup_tmps_real_dir_no_tmps(self):
        """cleanup-tmps with a real dir that has no .tmp files returns {deleted:0}."""
        with tempfile.TemporaryDirectory() as tmpdir:
            code, out, err = _capture_main(["cleanup-tmps", "--audits-dir", tmpdir])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data.get("deleted"), 0)
        self.assertEqual(data.get("files"), [])

    def test_cleanup_tmps_deletes_tmp_files(self):
        """cleanup-tmps deletes .tmp-*.md files and reports count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two .tmp-*.md files
            for name in [".tmp-code-reviewer.md", ".tmp-architect.md"]:
                path = os.path.join(tmpdir, name)
                with open(path, "w") as fh:
                    fh.write("# Agent output\n")
            # Also create a real report file (must NOT be deleted)
            real_report = os.path.join(tmpdir, "2026-06-01-audit.md")
            with open(real_report, "w") as fh:
                fh.write("# Audit Report\n")

            code, out, err = _capture_main(["cleanup-tmps", "--audits-dir", tmpdir])

        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data.get("deleted"), 2)
        self.assertEqual(len(data.get("files", [])), 2)
        # Real report must still exist (not in the deleted list)
        deleted_names = [os.path.basename(f) for f in data["files"]]
        self.assertNotIn("2026-06-01-audit.md", deleted_names)


# ---------------------------------------------------------------------------
# __init__.py re-export smoke
# ---------------------------------------------------------------------------


class TestInitExport(unittest.TestCase):
    def test_main_importable_from_package(self):
        """_audit package re-exports main via __init__.py (Phase 5 wiring)."""
        import importlib
        pkg = importlib.import_module("_audit")
        self.assertTrue(callable(getattr(pkg, "main", None)),
                        msg="_audit.main not callable after Phase 5 __init__ wiring")

    def test_all_contains_main(self):
        import importlib
        pkg = importlib.import_module("_audit")
        self.assertIn("main", pkg.__all__)


# ---------------------------------------------------------------------------
# Shim import smoke
# ---------------------------------------------------------------------------


class TestShimImport(unittest.TestCase):
    def test_audit_helper_py_imports_main(self):
        """audit_helper.py shim can be imported without error and exposes main."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "audit_helper", str(_HELPER_PY)
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # The module-level import of main must have succeeded.
        self.assertTrue(hasattr(mod, "main"))
        self.assertTrue(callable(mod.main))


# ---------------------------------------------------------------------------
# Task A: --passes flag in resolve-mode (via cmd_resolve_mode / main)
# ---------------------------------------------------------------------------


class TestResolveModePassesFlag(unittest.TestCase):
    """resolve-mode --passes N integration tests via main()."""

    def _run(self, args_str):
        # type: (str) -> tuple
        """Run main(["resolve-mode", "--", args_str]) and return (code, data, err)."""
        code, out, err = _capture_main(["resolve-mode", "--", args_str])
        data = json.loads(out) if out.strip() else {}
        return code, data, err

    # --- default (no --passes): mode-conditional default applies ---
    def test_default_passes_broad_is_2(self):
        # empty args → broad mode → mode-default passes = 2
        code, data, err = self._run("")
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertEqual(data.get("passes"), 2)

    def test_default_passes_clamp_note_empty(self):
        code, data, err = self._run("")
        self.assertEqual(code, 0)
        self.assertEqual(data.get("passes_clamp_note"), "")

    # --- valid in-range values ---
    def test_passes_2(self):
        code, data, err = self._run("--passes 2")
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertEqual(data.get("passes"), 2)
        self.assertEqual(data.get("passes_clamp_note"), "")

    def test_passes_3(self):
        code, data, err = self._run("--passes 3")
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertEqual(data.get("passes"), 3)
        self.assertEqual(data.get("passes_clamp_note"), "")

    def test_passes_1_explicit(self):
        code, data, err = self._run("--passes 1")
        self.assertEqual(code, 0)
        self.assertEqual(data.get("passes"), 1)
        self.assertEqual(data.get("passes_clamp_note"), "")

    # --- out-of-range: clamped, NOT an error ---
    def test_passes_10_clamped_to_3(self):
        code, data, err = self._run("--passes 10")
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertEqual(data.get("passes"), 3)
        self.assertNotEqual(data.get("passes_clamp_note"), "",
                            msg="clamp note should be non-empty when clamped")

    def test_passes_0_clamped_to_1(self):
        code, data, err = self._run("--passes 0")
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertEqual(data.get("passes"), 1)
        self.assertNotEqual(data.get("passes_clamp_note"), "")

    def test_passes_negative_clamped_to_1(self):
        code, data, err = self._run("--passes -5")
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertEqual(data.get("passes"), 1)
        self.assertNotEqual(data.get("passes_clamp_note"), "")

    def test_passes_clamp_note_written_to_stderr(self):
        """When a clamp occurs, a note line must appear on stderr (not stdout)."""
        code, data, err = self._run("--passes 10")
        self.assertEqual(code, 0)
        self.assertIn("clamped", err.lower(),
                      msg="Expected clamp note on stderr; got: " + repr(err))

    # --- non-integer: must set error, must not crash ---
    def test_passes_abc_sets_error(self):
        code, data, err = self._run("--passes abc")
        self.assertEqual(code, 2, msg="Expected exit 2 for non-integer --passes")
        self.assertIsNotNone(data.get("error"))
        self.assertIsNone(data.get("mode"))

    def test_passes_float_sets_error(self):
        code, data, err = self._run("--passes 1.5")
        self.assertEqual(code, 2)
        self.assertIsNotNone(data.get("error"))

    # --- Fix 4: edge cases for --passes ---
    def test_passes_trailing_no_value_exits_2_no_crash(self):
        """'--passes' as the final token with no value → error set, exit 2, no crash."""
        code, data, err = self._run("--passes")
        self.assertEqual(code, 2,
                         msg="Expected exit 2 when --passes has no value; stderr: " + err)
        self.assertIsNotNone(data.get("error"),
                             msg="error field should be set; data=" + repr(data))

    def test_passes_next_token_is_flag_exits_2_no_crash(self):
        """'--passes --full' (next token is a flag, not an int) → error set, no crash."""
        code, data, err = self._run("--passes --full")
        self.assertEqual(code, 2,
                         msg="Expected exit 2 when --passes value is a flag; stderr: " + err)
        self.assertIsNotNone(data.get("error"),
                             msg="error field should be set; data=" + repr(data))

    def test_passes_clamp_note_contains_original_and_clamped(self):
        """clamp_note for '--passes 10' must contain both the original value (10)
        and the clamped value (3)."""
        code, data, err = self._run("--passes 10")
        self.assertEqual(code, 0, msg="stderr: " + err)
        note = data.get("passes_clamp_note", "")
        self.assertIn("10", note,
                      msg="clamp note should mention original value 10; note=" + repr(note))
        self.assertIn("3", note,
                      msg="clamp note should mention clamped value 3; note=" + repr(note))

    # --- composes with existing modes ---
    def test_top_25_passes_2(self):
        code, data, err = self._run("--top 25 --passes 2")
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertEqual(data.get("mode"), "hotspot")
        self.assertEqual(data.get("top_n"), 25)
        self.assertEqual(data.get("passes"), 2)

    def test_full_passes_3(self):
        code, data, err = self._run("--full --passes 3")
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertEqual(data.get("mode"), "broad")
        self.assertEqual(data.get("passes"), 3)

    def test_uncommitted_passes_2(self):
        code, data, err = self._run("--uncommitted --passes 2")
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertEqual(data.get("mode"), "narrow")
        self.assertEqual(data.get("passes"), 2)

    def test_narrow_path_passes_2(self):
        code, data, err = self._run("src/auth.py --passes 2")
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertEqual(data.get("mode"), "narrow")
        self.assertEqual(data.get("passes"), 2)


# ---------------------------------------------------------------------------
# Task B: merge-passes verb via main()
# ---------------------------------------------------------------------------


def _make_finding_dict(
    agent="code-reviewer",
    severity="High",
    file_path="src/auth.py",
    line=10,
    pattern="naming lie",
    confidence="Certain",
    evidence="def validate(): return True",
    why="always True",
    remediation="fix it",
    category="mislogic",
    tags=None,
):
    # type: (...) -> dict
    return {
        "agent": agent,
        "severity": severity,
        "file": file_path,
        "line": line,
        "pattern": pattern,
        "confidence": confidence,
        "evidence": evidence,
        "why": why,
        "remediation": remediation,
        "category": category,
        "tags": list(tags) if tags is not None else [],
    }


class TestMergePassesVerb(unittest.TestCase):
    """merge-passes CLI verb integration tests via main()."""

    def setUp(self):
        import tempfile
        self._tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir)

    def _write_pool(self, filename, content):
        # type: (str, object) -> str
        """Write content as JSON to a temp file; return absolute path."""
        path = os.path.join(self._tmpdir, filename)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(content, fh)
        return path

    def _run_merge(self, pool_args):
        # type: (list) -> tuple
        """Run main(["merge-passes", "--pools"] + pool_args); return (code, list, err)."""
        argv = ["merge-passes", "--pools"] + pool_args
        code, out, err = _capture_main(argv)
        data = json.loads(out) if out.strip() else []
        return code, data, err

    # --- two passes with same defect within TOL → one merged finding ---
    def test_two_passes_same_defect_within_tol_collapses(self):
        """Same defect at lines 10 and 12 (within TOL=3) → one merged finding."""
        f1 = _make_finding_dict(line=10)
        f2 = _make_finding_dict(line=12)  # line 12 - 10 = 2 <= TOL
        p1 = self._write_pool("p1.json", {"passed": [f1], "discarded": []})
        p2 = self._write_pool("p2.json", {"passed": [f2], "discarded": []})
        code, data, err = self._run_merge([p1, p2])
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get("pass_count"), 2)
        tags = data[0].get("tags", [])
        self.assertTrue(
            any("[MULTI-PASS:2]" in t for t in tags),
            msg="Expected [MULTI-PASS:2] tag; tags={0}".format(tags),
        )

    def test_two_passes_bare_list_pool_accepted(self):
        """A bare JSON list (not a dict-with-passed) is also accepted as a pool."""
        f1 = _make_finding_dict(line=10)
        f2 = _make_finding_dict(line=11)
        # p1 = validate-findings object; p2 = bare list
        p1 = self._write_pool("p1.json", {"passed": [f1], "discarded": []})
        p2 = self._write_pool("p2.json", [f2])
        code, data, err = self._run_merge([p1, p2])
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get("pass_count"), 2)

    # --- glob expansion ---
    def test_glob_resolves_multiple_files_in_sorted_order(self):
        """A glob token expands to all matching files; lexical sort defines pass order."""
        f1 = _make_finding_dict(line=10, evidence="pass one evidence")
        f2 = _make_finding_dict(line=13, evidence="pass two evidence")  # 13-10=3 <= TOL
        # Use names that sort lexically as p1 before p2
        p1 = self._write_pool("validated-p1.json", {"passed": [f1]})
        p2 = self._write_pool("validated-p2.json", {"passed": [f2]})
        glob_pattern = os.path.join(self._tmpdir, "validated-p*.json")
        code, data, err = self._run_merge([glob_pattern])
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0].get("pass_count"), 2)

    # --- no matching files → nonzero exit + stderr message ---
    def test_no_matching_files_nonzero_exit(self):
        """No files matching the provided paths → exit 2 + stderr message."""
        nonexistent = os.path.join(self._tmpdir, "nonexistent*.json")
        code, data, err = self._run_merge([nonexistent])
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", err,
                         msg="Should not produce a raw traceback on no-match")
        self.assertIn("no files", err.lower(),
                      msg="Expected 'no files' message in stderr; got: " + repr(err))

    def test_nonexistent_explicit_path_nonzero_exit(self):
        """An explicit path that doesn't exist → exit 2, no traceback."""
        bad_path = os.path.join(self._tmpdir, "doesnotexist.json")
        code, data, err = self._run_merge([bad_path])
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", err)

    # --- malformed JSON → clear error, no crash ---
    def test_malformed_json_nonzero_exit(self):
        path = os.path.join(self._tmpdir, "bad.json")
        with open(path, "w") as fh:
            fh.write("not json {{{")
        code, data, err = self._run_merge([path])
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", err)

    # --- empty pool files → valid merge (empty output) ---
    def test_empty_pools_returns_empty_list(self):
        p1 = self._write_pool("p1.json", {"passed": []})
        p2 = self._write_pool("p2.json", {"passed": []})
        code, data, err = self._run_merge([p1, p2])
        self.assertEqual(code, 0)
        self.assertEqual(data, [])

    # --- output is a bare JSON array (not a wrapper object) ---
    def test_output_is_bare_json_array(self):
        f1 = _make_finding_dict(line=5)
        p1 = self._write_pool("p1.json", [f1])
        code, out, err = _capture_main(["merge-passes", "--pools", p1])
        self.assertEqual(code, 0)
        parsed = json.loads(out)
        self.assertIsInstance(parsed, list)

    # --- Fix 1: guard for passed value not being a list ---
    def test_passed_value_is_string_exits_2_no_traceback(self):
        """{'passed': 'not-a-list'} → exit 2, clean stderr, no traceback."""
        p1 = self._write_pool("bad_passed.json", {"passed": "not-a-list", "discarded": []})
        code, data, err = self._run_merge([p1])
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", err,
                         msg="Should not produce a raw traceback")
        # stderr must name the file and say something useful
        self.assertIn("bad_passed.json", err,
                      msg="Error should name the offending file; got: " + repr(err))

    def test_dict_without_passed_key_exits_2_no_traceback(self):
        """A dict with no 'passed' key → exit 2, clean error, no traceback."""
        p1 = self._write_pool("no_passed.json", {"other_key": [1, 2, 3]})
        code, data, err = self._run_merge([p1])
        self.assertEqual(code, 2)
        self.assertNotIn("Traceback", err,
                         msg="Should not produce a raw traceback")
        self.assertIn("no_passed.json", err,
                      msg="Error should name the offending file; got: " + repr(err))

    # --- Fix 3: glob + explicit overlap → pass_count equals unique file count ---
    def test_glob_and_explicit_overlap_deduplicates(self):
        """A glob token and an explicit path that both expand to the same file
        should be counted only once, so pass_count == number of UNIQUE files."""
        f1 = _make_finding_dict(line=10)
        f2 = _make_finding_dict(line=11)
        p1 = self._write_pool("dedup-p1.json", {"passed": [f1]})
        p2 = self._write_pool("dedup-p2.json", {"passed": [f2]})
        # Glob that matches both files
        glob_pattern = os.path.join(self._tmpdir, "dedup-p*.json")
        # Also pass p1 explicitly — this creates a duplicate for p1
        code, data, err = self._run_merge([glob_pattern, p1])
        self.assertEqual(code, 0, msg="stderr: " + err)
        # p1 and p2 each have one finding at lines 10 and 11 (within TOL=3),
        # so after deduplication they merge into 1 finding with pass_count=2.
        # Without dedup, p1 would appear twice giving pass_count=3.
        self.assertEqual(len(data), 1)
        self.assertEqual(
            data[0].get("pass_count"), 2,
            msg=(
                "pass_count should be 2 (2 unique files), not 3 "
                "(p1 counted twice without dedup); data={0}".format(data)
            ),
        )

    # --- func wired in argparse (structural) ---
    def test_merge_passes_func_wired(self):
        args = build_parser().parse_args([
            "merge-passes", "--pools", "/tmp/p1.json",
        ])
        self.assertTrue(callable(args.func))

    def test_merge_passes_requires_pools(self):
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["merge-passes"])


# ---------------------------------------------------------------------------
# Task C: render-agent-brief --tmp-path flag via main()
# ---------------------------------------------------------------------------


class TestRenderAgentBriefTmpPathCLI(unittest.TestCase):
    """CLI round-trip tests for render-agent-brief --tmp-path flag."""

    _CUSTOM_PATH = "/tmp/forge-audit-abc/tmp-architect-p2.md"
    _DEFAULT_PATH_TOKEN = "audits/.tmp-{agent-name}.md"

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        # Write a minimal scope JSON for the verb to consume.
        scope = {
            "scope_kind": "file",
            "pipeline": "simplified",
            "files": ["src/main.py"],
            "file_count": 1,
            "scope_limit": 200,
            "scope_oversize": False,
            "line_range": None,
            "error": None,
        }
        self._scope_path = os.path.join(self._tmpdir, "scope.json")
        with open(self._scope_path, "w", encoding="utf-8") as fh:
            json.dump(scope, fh)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _run_brief(self, agent, extra_argv=None):
        # type: (str, list) -> tuple
        """Run render-agent-brief via main() and return (code, stdout, stderr)."""
        argv = [
            "render-agent-brief",
            "--agent", agent,
            "--scope", self._scope_path,
            "--references-dir", str(_REFERENCES_DIR),
        ]
        if extra_argv:
            argv.extend(extra_argv)
        return _capture_main(argv)

    def test_default_no_tmp_path_contains_default_token(self):
        """Without --tmp-path, output contains audits/.tmp-{agent-name}.md."""
        code, out, err = self._run_brief("architect")
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertIn(self._DEFAULT_PATH_TOKEN, out)

    def test_with_tmp_path_contains_custom_path(self):
        """With --tmp-path, output contains the custom path."""
        code, out, err = self._run_brief(
            "architect",
            extra_argv=["--tmp-path", self._CUSTOM_PATH],
        )
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertIn(self._CUSTOM_PATH, out)

    def test_with_tmp_path_no_default_token(self):
        """With --tmp-path, the default audits/.tmp-{agent-name}.md is not in output."""
        code, out, err = self._run_brief(
            "architect",
            extra_argv=["--tmp-path", self._CUSTOM_PATH],
        )
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertNotIn(self._DEFAULT_PATH_TOKEN, out)

    def test_with_tmp_path_failure_instruction_references_path(self):
        """With --tmp-path, failure instruction references the custom path."""
        code, out, err = self._run_brief(
            "code-reviewer",
            extra_argv=["--tmp-path", self._CUSTOM_PATH],
        )
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertIn(
            "write `{0}` with `# Status: failed`".format(self._CUSTOM_PATH),
            out,
        )

    def test_with_tmp_path_empty_instruction_references_path(self):
        """With --tmp-path, empty-file instruction references the custom path."""
        code, out, err = self._run_brief(
            "code-reviewer",
            extra_argv=["--tmp-path", self._CUSTOM_PATH],
        )
        self.assertEqual(code, 0, msg="stderr: " + err)
        self.assertIn(
            "write `{0}` with `# Status: complete`".format(self._CUSTOM_PATH),
            out,
        )


if __name__ == "__main__":
    unittest.main()
