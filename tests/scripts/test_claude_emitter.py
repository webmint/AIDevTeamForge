"""Tests for scripts/emitters/claude.py.

Covers the --only NAME selective-emit feature added alongside the existing
full-emit path.

All three cases use a real src/ (the repo's own src/ directory) emitting into
a TemporaryDirectory, so the round-trip exercises the real command-source
loader + reference rewriter — no hand-authored fixtures.

Test matrix:
  1. only="audit"  — emits audit.md + audit/references/, nothing else.
  2. only="nope"   — invalid name: main() returns 1, nothing written.
  3. only=None     — full emit: all _PROMOTED commands present (no-regression guard).

Stdlib only.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
_EMITTERS_DIR = _SCRIPTS_DIR / "emitters"
_CLAUDE_EMITTER_PY = _EMITTERS_DIR / "claude.py"
_SRC = _REPO_ROOT / "src"


def _load_claude_emitter():
    """Load scripts/emitters/claude.py as a module.

    claude.py does `from lib.command_source import ...` at import time.
    It inserts SCRIPTS_DIR into sys.path itself (line 39-40), so as long
    as we don't shadow `lib` beforehand we get the right module.  We
    pre-register the scripts/lib/ package in sys.modules under the bare
    name `lib` the same way test_generate_agents.py handles it, to avoid
    the `tests/lib/` namespace-package shadow on sys.path.
    """
    # Ensure the scripts/lib/ package is visible under the bare name `lib`
    # before the emitter's import runs.
    if "lib" not in sys.modules:
        import types
        lib_pkg = types.ModuleType("lib")
        lib_pkg.__path__ = [str(_SCRIPTS_DIR / "lib")]  # type: ignore[attr-defined]
        sys.modules["lib"] = lib_pkg

    lib_cs_key = "lib.command_source"
    if lib_cs_key not in sys.modules:
        cs_path = _SCRIPTS_DIR / "lib" / "command_source.py"
        cs_spec = importlib.util.spec_from_file_location(lib_cs_key, cs_path)
        cs_mod = importlib.util.module_from_spec(cs_spec)  # type: ignore[arg-type]
        sys.modules[lib_cs_key] = cs_mod
        cs_spec.loader.exec_module(cs_mod)  # type: ignore[union-attr]

    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))

    spec = importlib.util.spec_from_file_location("claude_emitter", _CLAUDE_EMITTER_PY)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


_claude = _load_claude_emitter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _emitted_commands(target: Path) -> set:
    """Return the set of command-stem names written under target/.claude/commands/."""
    commands_dir = target / ".claude" / "commands"
    if not commands_dir.is_dir():
        return set()
    return {p.stem for p in commands_dir.glob("*.md")}


# ---------------------------------------------------------------------------
# OnlyFlagTests
# ---------------------------------------------------------------------------

class OnlyFlagTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.target = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # 1 ─ --only audit emits exactly one command (audit) and no others
    def test_only_audit_emits_single_command(self):
        _claude.emit(_SRC, self.target, only="audit")
        emitted = _emitted_commands(self.target)

        # The emitted file for "audit" must be present.
        self.assertIn("audit", emitted, f"audit.md not found; emitted: {emitted!r}")

        # No other command-level .md files should exist.
        other = emitted - {"audit"}
        self.assertEqual(
            other,
            set(),
            f"unexpected command files emitted alongside audit: {other!r}",
        )

    def test_only_audit_emits_references_folder(self):
        _claude.emit(_SRC, self.target, only="audit")
        refs_dir = self.target / ".claude" / "commands" / "audit" / "references"
        self.assertTrue(
            refs_dir.is_dir(),
            "audit/references/ directory should be created when audit has references",
        )
        ref_files = list(refs_dir.glob("*.md"))
        self.assertGreater(
            len(ref_files),
            0,
            "audit/references/ should contain at least one reference file",
        )

    def test_only_audit_does_not_emit_implement(self):
        _claude.emit(_SRC, self.target, only="audit")
        implement_md = self.target / ".claude" / "commands" / "implement.md"
        self.assertFalse(
            implement_md.exists(),
            "implement.md must NOT be emitted when --only audit is used",
        )

    def test_only_audit_does_not_emit_plan(self):
        _claude.emit(_SRC, self.target, only="audit")
        plan_md = self.target / ".claude" / "commands" / "plan.md"
        self.assertFalse(
            plan_md.exists(),
            "plan.md must NOT be emitted when --only audit is used",
        )

    # 2 ─ invalid --only name: main() returns 1, nothing written
    def test_invalid_only_returns_nonzero_via_main(self):
        """main() must return 1 for an unknown --only value."""
        import io
        import contextlib

        stderr_buf = io.StringIO()
        with contextlib.redirect_stderr(stderr_buf):
            # Patch sys.argv so argparse sees our arguments.
            old_argv = sys.argv
            sys.argv = [
                "claude.py",
                "--src", str(_SRC),
                "--target", str(self.target),
                "--only", "nope",
            ]
            try:
                exit_code = _claude.main()
            finally:
                sys.argv = old_argv

        self.assertEqual(exit_code, 1, "main() must return 1 for an invalid --only value")
        stderr_output = stderr_buf.getvalue()
        self.assertIn("nope", stderr_output, "error message must mention the invalid name")
        self.assertIn("error", stderr_output.lower(), "error message must contain 'error'")

    def test_invalid_only_writes_nothing(self):
        """Nothing should be written to target when --only is invalid."""
        import io
        import contextlib

        stderr_buf = io.StringIO()
        with contextlib.redirect_stderr(stderr_buf):
            old_argv = sys.argv
            sys.argv = [
                "claude.py",
                "--src", str(_SRC),
                "--target", str(self.target),
                "--only", "nope",
            ]
            try:
                _claude.main()
            finally:
                sys.argv = old_argv

        emitted = _emitted_commands(self.target)
        self.assertEqual(emitted, set(), f"nothing should be emitted for invalid --only; got: {emitted!r}")

    def test_invalid_only_error_message_lists_choices(self):
        """The error message must list the valid promoted command names."""
        import io
        import contextlib

        stderr_buf = io.StringIO()
        with contextlib.redirect_stderr(stderr_buf):
            old_argv = sys.argv
            sys.argv = [
                "claude.py",
                "--src", str(_SRC),
                "--target", str(self.target),
                "--only", "nope",
            ]
            try:
                _claude.main()
            finally:
                sys.argv = old_argv

        stderr_output = stderr_buf.getvalue()
        # At minimum, a few known promoted names should appear in the choices list.
        for name in ("audit", "plan", "implement"):
            self.assertIn(
                name, stderr_output,
                f"promoted name '{name}' should appear in the choices error message",
            )

    # 3 ─ only=None still emits full _PROMOTED set (no-regression guard)
    def test_full_emit_when_only_is_none(self):
        """emit(src, target) with no only= must emit ALL promoted commands."""
        _claude.emit(_SRC, self.target, only=None)
        emitted = _emitted_commands(self.target)

        for name in _claude._PROMOTED:
            self.assertIn(
                name, emitted,
                f"command '{name}' from _PROMOTED not found in emitted set: {emitted!r}",
            )

    def test_full_emit_default_arg_identical_to_none(self):
        """emit(src, target) with no keyword arg must behave identically to only=None."""
        _claude.emit(_SRC, self.target)
        emitted = _emitted_commands(self.target)

        # Spot-check a handful of commands that have been stable since the
        # emitter was first written — if these are missing, the default-arg
        # path regressed.
        for name in ("plan", "implement", "audit", "constitute"):
            self.assertIn(
                name, emitted,
                f"command '{name}' missing in full emit (default only=None path): {emitted!r}",
            )


# ---------------------------------------------------------------------------
# ListFlagTests
# ---------------------------------------------------------------------------

class ListFlagTests(unittest.TestCase):
    """--list prints the canonical _PROMOTED names, one per line, exit 0,
    without requiring --src/--target."""

    def _run_main_with_argv(self, argv):
        import io
        import contextlib

        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        old_argv = sys.argv
        sys.argv = argv
        try:
            with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
                exit_code = _claude.main()
        finally:
            sys.argv = old_argv
        return exit_code, stdout_buf.getvalue(), stderr_buf.getvalue()

    def test_list_prints_promoted_one_per_line(self):
        exit_code, stdout, _ = self._run_main_with_argv(["claude.py", "--list"])
        self.assertEqual(exit_code, 0, "--list must exit 0")
        lines = stdout.splitlines()
        self.assertEqual(
            lines,
            list(_claude._PROMOTED),
            "--list output must be _PROMOTED names in order, one per line",
        )

    def test_list_requires_no_src_or_target(self):
        # No --src/--target supplied: must not error.
        exit_code, stdout, stderr = self._run_main_with_argv(["claude.py", "--list"])
        self.assertEqual(exit_code, 0)
        self.assertEqual(stderr, "", f"--list must produce no stderr; got: {stderr!r}")
        self.assertTrue(stdout.strip(), "--list must print something to stdout")


if __name__ == "__main__":
    unittest.main()
