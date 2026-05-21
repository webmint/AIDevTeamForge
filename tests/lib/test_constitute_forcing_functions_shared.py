"""Tests for _constitute._forcing_functions._shared (Phase 0 substrate).

Coverage
--------
test_finding_dataclass_frozen          -- frozen dataclass raises on field assign.
test_finding_to_json_via_emit_findings -- emit_findings serializes Finding to JSON
                                          correctly; round-trip test.
test_emit_findings_exit_code_clean     -- empty list -> EXIT_CLEAN, no output.
test_emit_findings_exit_code_dirty     -- one finding -> EXIT_FINDINGS + correct
                                          stderr line + valid stdout JSON.
test_emit_findings_multi               -- two findings -> both appear in stderr and
                                          stdout JSON list.
test_inline_escape_detection_typescript -- TS-style escape with reason -> True.
test_inline_escape_detection_python    -- Python-style escape with reason -> True.
test_inline_escape_naked_rejected      -- escape marker but no reason text -> False.
test_inline_escape_other_line_negative -- escape on line 5; query line 3 -> False.
test_inline_escape_missing_file        -- non-existent path -> False (no exception).
test_inline_escape_line_out_of_range   -- file has 3 lines; query line 10 -> False.
test_path_allowlist_match_positive     -- path matches a glob -> True.
test_path_allowlist_match_negative     -- path does not match -> False.
test_path_allowlist_empty_list         -- empty list -> always False.
test_schema_accepts_forcing_functions_block -- round-trip via _constitute/_schema.py
                                             validator: state dict with
                                             forcing_functions key validates; without
                                             key also validates (backward compat).
"""

from __future__ import annotations

import dataclasses
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Make the devforge lib importable without installing the package.
_LIB_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "src", "devforge", "lib")
if _LIB_ROOT not in sys.path:
    sys.path.insert(0, _LIB_ROOT)

from _constitute._forcing_functions._shared import (  # noqa: E402
    EXIT_CLEAN,
    EXIT_FINDINGS,
    Finding,
    emit_findings,
    has_inline_escape,
    path_in_allowlist,
)
from _constitute._schema import FIELD_SCHEMA  # noqa: E402
from _constitute._state import default_state  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _capture_emit(rule, findings):
    """Call emit_findings with stdout/stderr captured; return (exit_code, stdout, stderr)."""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        code = emit_findings(rule, findings)
        out = sys.stdout.getvalue()
        err = sys.stderr.getvalue()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return code, out, err


def _make_temp_file(lines):
    """Write lines (list of str) to a temp file; return (Path, fd) for cleanup."""
    fd, path = tempfile.mkstemp(suffix=".ts")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if lines else ""))
    return Path(path)


# ---------------------------------------------------------------------------
# Finding dataclass tests
# ---------------------------------------------------------------------------

class TestFindingDataclass(unittest.TestCase):

    def test_finding_dataclass_frozen(self):
        """Assigning to a Finding field after construction raises FrozenInstanceError."""
        f = Finding(rule="r", path="x.ts", line=1, kind="VIOLATION", summary="s")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            f.summary = "mutated"  # type: ignore[misc]

    def test_finding_fix_hint_optional(self):
        """fix_hint defaults to None when not provided."""
        f = Finding(rule="r", path="x.ts", line=1, kind="VIOLATION", summary="s")
        self.assertIsNone(f.fix_hint)

    def test_finding_fix_hint_set(self):
        """fix_hint is preserved when provided."""
        f = Finding(
            rule="r", path="x.ts", line=1, kind="VIOLATION",
            summary="s", fix_hint="import the enum"
        )
        self.assertEqual(f.fix_hint, "import the enum")


# ---------------------------------------------------------------------------
# emit_findings tests
# ---------------------------------------------------------------------------

class TestEmitFindings(unittest.TestCase):

    def test_emit_findings_exit_code_clean(self):
        """Empty findings list -> returns EXIT_CLEAN; no stderr or stdout output."""
        code, out, err = _capture_emit("some_rule", [])
        self.assertEqual(code, EXIT_CLEAN)
        self.assertEqual(EXIT_CLEAN, 0)
        self.assertEqual(out, "")
        self.assertEqual(err, "")

    def test_emit_findings_exit_code_dirty(self):
        """One finding -> returns EXIT_FINDINGS."""
        f = Finding(rule="test_rule", path="src/foo.ts", line=42,
                    kind="VIOLATION", summary="bad literal")
        code, _out, _err = _capture_emit("test_rule", [f])
        self.assertEqual(code, EXIT_FINDINGS)
        self.assertEqual(EXIT_FINDINGS, 2)

    def test_emit_findings_stderr_format(self):
        """Stderr line follows <path>:<line>: <KIND> [<rule>] <summary> format."""
        f = Finding(rule="magic_enum", path="src/order.ts", line=7,
                    kind="VIOLATION", summary="literal 'SHIPPING' matches OrgV2AddressType")
        _code, _out, err = _capture_emit("magic_enum", [f])
        expected = "src/order.ts:7: VIOLATION [magic_enum] literal 'SHIPPING' matches OrgV2AddressType\n"
        self.assertEqual(err, expected)

    def test_finding_to_json_via_emit_findings(self):
        """emit_findings serializes Finding to valid JSON; round-trip check."""
        f = Finding(
            rule="magic_enum",
            path="src/order.ts",
            line=7,
            kind="VIOLATION",
            summary="literal 'SHIPPING' matches OrgV2AddressType.Shipping",
            fix_hint="import { OrgV2AddressType } from 'generated'",
        )
        _code, out, _err = _capture_emit("magic_enum", [f])
        parsed = json.loads(out)

        self.assertEqual(parsed["rule"], "magic_enum")
        self.assertEqual(len(parsed["findings"]), 1)
        entry = parsed["findings"][0]
        self.assertEqual(entry["path"], "src/order.ts")
        self.assertEqual(entry["line"], 7)
        self.assertEqual(entry["kind"], "VIOLATION")
        self.assertEqual(entry["summary"],
                         "literal 'SHIPPING' matches OrgV2AddressType.Shipping")
        self.assertEqual(entry["fix_hint"],
                         "import { OrgV2AddressType } from 'generated'")

    def test_emit_findings_json_fix_hint_none(self):
        """fix_hint serializes to null when not set."""
        f = Finding(rule="r", path="x.ts", line=1, kind="VIOLATION", summary="s")
        _code, out, _err = _capture_emit("r", [f])
        parsed = json.loads(out)
        self.assertIsNone(parsed["findings"][0]["fix_hint"])

    def test_emit_findings_multi(self):
        """Two findings -> both appear in stderr and stdout JSON findings list."""
        f1 = Finding(rule="rule_x", path="a.ts", line=1, kind="VIOLATION",
                     summary="first violation")
        f2 = Finding(rule="rule_x", path="b.ts", line=5, kind="VIOLATION",
                     summary="second violation")
        code, out, err = _capture_emit("rule_x", [f1, f2])

        self.assertEqual(code, EXIT_FINDINGS)

        # stderr: two lines
        lines = err.strip().split("\n")
        self.assertEqual(len(lines), 2)
        self.assertIn("a.ts:1:", lines[0])
        self.assertIn("first violation", lines[0])
        self.assertIn("b.ts:5:", lines[1])
        self.assertIn("second violation", lines[1])

        # stdout: JSON with 2 findings
        parsed = json.loads(out)
        self.assertEqual(len(parsed["findings"]), 2)
        self.assertEqual(parsed["findings"][0]["path"], "a.ts")
        self.assertEqual(parsed["findings"][1]["path"], "b.ts")


# ---------------------------------------------------------------------------
# has_inline_escape tests
# ---------------------------------------------------------------------------

class TestHasInlineEscape(unittest.TestCase):

    def test_inline_escape_detection_typescript(self):
        """TS-style // forcing-fn-ok: with reason text -> True."""
        path = _make_temp_file([
            "const x = 1;",
            "const role = 'SHIPPING'; // forcing-fn-ok: legacy contract",
            "const y = 2;",
        ])
        try:
            self.assertTrue(has_inline_escape(path, 2))
        finally:
            path.unlink()

    def test_inline_escape_detection_python(self):
        """Python-style # forcing-fn-ok: with reason text -> True."""
        path = _make_temp_file([
            "def foo():",
            "    x = 'SHIPPING'  # forcing-fn-ok: legacy",
        ])
        try:
            self.assertTrue(has_inline_escape(path, 2))
        finally:
            path.unlink()

    def test_inline_escape_naked_rejected(self):
        """Escape marker with no reason text after colon -> False."""
        path = _make_temp_file([
            "const x = 'VAL'; // forcing-fn-ok:",
        ])
        try:
            self.assertFalse(has_inline_escape(path, 1))
        finally:
            path.unlink()

    def test_inline_escape_naked_whitespace_only_rejected(self):
        """Escape marker with only whitespace after colon -> False."""
        path = _make_temp_file([
            "const x = 'VAL'; // forcing-fn-ok:   ",
        ])
        try:
            self.assertFalse(has_inline_escape(path, 1))
        finally:
            path.unlink()

    def test_inline_escape_other_line_negative(self):
        """Escape on line 5; querying line 3 -> False."""
        path = _make_temp_file([
            "line1",
            "line2",
            "const x = 'SHIPPING';",
            "line4",
            "const y = 'OTHER'; // forcing-fn-ok: reason here",
        ])
        try:
            self.assertFalse(has_inline_escape(path, 3))
        finally:
            path.unlink()

    def test_inline_escape_missing_file(self):
        """Non-existent path -> False (no exception raised)."""
        result = has_inline_escape(Path("/tmp/__no_such_file_forcing_fn__.ts"), 1)
        self.assertFalse(result)

    def test_inline_escape_line_out_of_range(self):
        """File has 3 lines; querying line 10 -> False (no exception)."""
        path = _make_temp_file(["line1", "line2", "line3"])
        try:
            self.assertFalse(has_inline_escape(path, 10))
        finally:
            path.unlink()

    def test_inline_escape_line_zero_out_of_range(self):
        """Line number 0 (before any 1-based line) -> False."""
        path = _make_temp_file(["const x = 'v'; // forcing-fn-ok: reason"])
        try:
            self.assertFalse(has_inline_escape(path, 0))
        finally:
            path.unlink()

    def test_inline_escape_line_positive_on_exact_escape(self):
        """Line 1 of single-line file with escape -> True."""
        path = _make_temp_file([
            "const z = 'VAL'; // forcing-fn-ok: deliberate",
        ])
        try:
            self.assertTrue(has_inline_escape(path, 1))
        finally:
            path.unlink()

    def test_inline_escape_single_char_reason(self):
        """Single-char reason text ('a') -> True (no minimum length enforced)."""
        path = _make_temp_file([
            "const x = 'VAL'; // forcing-fn-ok: a",
        ])
        try:
            self.assertTrue(has_inline_escape(path, 1))
        finally:
            path.unlink()

    def test_inline_escape_last_line_of_multi_line_file(self):
        """Escape on line N of N-line file -> True (no off-by-one at file end)."""
        path = _make_temp_file([
            "const a = 1;",
            "const b = 2;",
            "const z = 'VAL'; // forcing-fn-ok: legacy contract",
        ])
        try:
            self.assertTrue(has_inline_escape(path, 3))
        finally:
            path.unlink()


# ---------------------------------------------------------------------------
# path_in_allowlist tests
# ---------------------------------------------------------------------------

class TestPathInAllowlist(unittest.TestCase):

    def test_path_allowlist_match_positive(self):
        """Path matches the glob -> True."""
        result = path_in_allowlist(
            Path("tests/fixtures/foo.fixture.ts"),
            ["**/*.fixture.ts"],
        )
        self.assertTrue(result)

    def test_path_allowlist_match_negative(self):
        """Path does not match any glob -> False."""
        result = path_in_allowlist(
            Path("src/code.ts"),
            ["**/*.fixture.ts"],
        )
        self.assertFalse(result)

    def test_path_allowlist_empty_list(self):
        """Empty allowlist -> always False."""
        result = path_in_allowlist(Path("src/anything.ts"), [])
        self.assertFalse(result)

    def test_path_allowlist_first_glob_matches(self):
        """Returns True when the first glob in a multi-glob list matches.

        Note: fnmatch does not treat ** specially — it is equivalent to */.
        Globs that match a path starting with "scripts/" must not require a
        leading path component (use "scripts/*" not "**/scripts/**").
        """
        result = path_in_allowlist(
            Path("scripts/seed.ts"),
            ["scripts/*", "**/*.log.ts"],
        )
        self.assertTrue(result)

    def test_path_allowlist_second_glob_matches(self):
        """Returns True when only the second glob matches."""
        result = path_in_allowlist(
            Path("src/ops.log.ts"),
            ["**/*.fixture.ts", "**/*.log.ts"],
        )
        self.assertTrue(result)

    def test_path_allowlist_no_glob_matches_unrelated_path(self):
        """Returns False when no glob in a multi-glob list matches.

        Note: this tests the negative path for an unrelated file
        (src/real-code.ts).  It does NOT validate the plan's example globs
        cover their intended top-level paths — see
        test_path_allowlist_fnmatch_double_star_does_not_match_top_level
        for the substrate-correctness gap that informed the F1 finding.
        """
        result = path_in_allowlist(
            Path("src/real-code.ts"),
            ["**/*.fixture.ts", "**/*.log.ts", "**/scripts/**"],
        )
        self.assertFalse(result)

    def test_path_allowlist_fnmatch_double_star_does_not_match_top_level(self):
        """Documents the fnmatch limitation: ``**/x/**`` does NOT match ``x/y``.

        ``fnmatch.fnmatch`` treats ``**`` as equivalent to ``*`` — no
        recursive directory-separator expansion (unlike shell-glob ``**``
        or ``pathlib.Path.match`` in Python 3.13+).  Callers MUST pair
        ``**/<x>`` with a top-level twin (``<x>`` or ``<x>/**``) to cover
        both cases.  See _shared.path_in_allowlist docstring + plan
        §"Allowlist glob behavior" for full guidance.
        """
        # Bare **/scripts/** does NOT match top-level scripts/seed.ts.
        self.assertFalse(
            path_in_allowlist(Path("scripts/seed.ts"), ["**/scripts/**"]),
        )
        # The paired top-level twin DOES match — the recommended pattern.
        self.assertTrue(
            path_in_allowlist(
                Path("scripts/seed.ts"),
                ["scripts/**", "**/scripts/**"],
            ),
        )


# ---------------------------------------------------------------------------
# Schema extension tests
# ---------------------------------------------------------------------------

class TestSchemaForcingFunctions(unittest.TestCase):

    def test_schema_includes_forcing_functions_field(self):
        """FIELD_SCHEMA includes 'forcing_functions' with kind 'optional_dict'."""
        schema_dict = {name: kind for name, kind in FIELD_SCHEMA}
        self.assertIn("forcing_functions", schema_dict)
        self.assertEqual(schema_dict["forcing_functions"], "optional_dict")

    def test_schema_accepts_forcing_functions_block(self):
        """Real-producer round-trip: _write_state -> filesystem -> _load.

        Per feedback_test_first_python_helpers.md, parsers and state
        round-trips MUST use the real producer path, not hand-authored
        json.dumps/json.loads.  Exercises the same write+load path that
        production code calls.
        """
        from _constitute._state import _write_state, _load  # noqa: E402

        # default_state() should include the key set to None.
        state = default_state()
        self.assertIn("forcing_functions", state)
        self.assertIsNone(state["forcing_functions"])

        # Set the expected dict shape (per-rule config block).
        state["forcing_functions"] = {
            "magic_enum_duplication": {
                "enabled": True,
                "generated_types_dirs": ["packages/cse-types/src"],
                "allowlist_paths": ["*.fixture.ts", "**/*.fixture.ts"],
            }
        }

        # Real-producer round-trip via the actual _write_state -> _load path.
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            _write_state(state, devforge)
            reloaded = _load(devforge)

        ff = reloaded["forcing_functions"]
        self.assertIsInstance(ff, dict)
        self.assertIn("magic_enum_duplication", ff)
        self.assertTrue(ff["magic_enum_duplication"]["enabled"])
        self.assertEqual(
            ff["magic_enum_duplication"]["generated_types_dirs"],
            ["packages/cse-types/src"],
        )
        self.assertEqual(
            ff["magic_enum_duplication"]["allowlist_paths"],
            ["*.fixture.ts", "**/*.fixture.ts"],
        )

    def test_schema_backward_compat_without_forcing_functions(self):
        """A state JSON without forcing_functions (pre-Phase 0) is tolerated by _load."""
        from _constitute._state import _load  # noqa: E402

        # Build a minimal 11-key state dict without forcing_functions.
        state_without_ff = {k: v for k, v in default_state().items()
                            if k != "forcing_functions"}
        self.assertNotIn("forcing_functions", state_without_ff)

        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            devforge.mkdir()
            (devforge / "constitute.json").write_text(
                json.dumps(state_without_ff, indent=2), encoding="utf-8"
            )
            loaded = _load(devforge)
            # Key is absent from the loaded state (no injection from _load).
            # This is the correct backward-compat behavior: _load returns the
            # raw JSON; callers use .get("forcing_functions") defensively.
            self.assertNotIn("forcing_functions", loaded)


if __name__ == "__main__":
    unittest.main()
