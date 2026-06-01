"""Tests for src/devforge/lib/_audit/_cli.py (CLI smoke tests for Phase 5).

Coverage:
  build_parser    — returns ArgumentParser; exactly 17 subcommands registered.
  main            — no subcommand → exit 2; help → exit 2.
  per-verb args   — each verb's namespace has a `func` attribute wired.
  e2e smokes      — resolve-mode --full → exit 0 + JSON {mode: broad};
                    check-agents --agents-dir /nonexistent → exit 3.
  verb guard      — registered set matches expected 17-verb constant.
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

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _audit._cli import build_parser, main  # noqa: E402


# ---------------------------------------------------------------------------
# The canonical 17-verb list (Phase 0–4). Guard against accidental drops.
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

    def test_exactly_17_verbs_registered(self):
        """build_parser registers exactly the 17 expected verbs — no more, no fewer."""
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


if __name__ == "__main__":
    unittest.main()
