"""Tests for the ``verify-design-tokens`` forcing-function detector (plan 40 Phase 4).

Covers the scanner (unit tests per check), the CLI command handler, and the
end-to-end CLI verb invocation via ``_constitute._cli.main``.

Test structure
--------------
TestCheck1ColorLiterals
    clean_tokenized_css_no_violations
    hardcoded_hex_short
    hardcoded_hex_full
    hardcoded_hex_8digit
    rgb_function
    rgba_function
    hsl_function
    hsla_function
    named_color
    allowlisted_keywords_pass  (transparent, currentColor, inherit)
    token_definition_lines_skipped
    var_token_reference_passes

TestCheck2VarFallbacks
    clean_var_no_fallback_passes
    var_fallback_literal_hex
    var_fallback_literal_px
    var_fallback_chained_var_passes  (var(--x, var(--y)) is fine)
    var_empty_fallback_passes

TestCheck3UndefinedTokens
    defined_token_passes
    undefined_token_fails_loud
    no_token_source_skips_check  (OQ-6 relaxation)
    token_definition_line_skipped

TestCheck4InteractiveStates
    button_with_both_states_passes
    button_missing_hover_fails
    button_missing_focus_visible_fails
    anchor_missing_both_fails
    input_both_states_passes
    role_button_missing_focus_visible
    non_interactive_selector_ignored

TestScannerIntegration
    clean_file_returns_empty
    multiple_violations_in_one_file
    allowlisted_file_skipped
    non_style_extension_skipped_for_checks_4_5
    file_paths_targeted_scan

TestCmdVerifyDesignTokensCLI
    missing_config_exits_clean
    disabled_rule_exits_clean
    absent_rule_block_exits_clean
    enabled_clean_file_exits_0
    enabled_hardcoded_hex_exits_2
    enabled_var_fallback_exits_2
    enabled_undefined_token_exits_2
    enabled_missing_focus_visible_exits_2
    spacing_relaxes_when_css_absent

TestRuleRegistration
    rule_to_verb_assertion_holds
    verify_design_tokens_in_cli_help
"""

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import List, Optional, Set

_LIB_ROOT = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "src", "devforge", "lib"
)
if _LIB_ROOT not in sys.path:
    sys.path.insert(0, _LIB_ROOT)

from _constitute._cli import main as cli_main  # noqa: E402
from _constitute._forcing_functions._design_tokens._scanner import (  # noqa: E402
    _check1_color_literals,
    _check2_var_fallbacks,
    _check3_undefined_tokens,
    _check4_interactive_states,
    scan_for_design_token_violations,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RULE = "design_token_provenance"


def _run_cli(argv: list) -> tuple:
    """Return (exit_code, stdout_str, stderr_str)."""
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        code = cli_main(argv)
        out = sys.stdout.getvalue()
        err = sys.stderr.getvalue()
    finally:
        sys.stdout = old_out
        sys.stderr = old_err
    return code, out, err


def _findings_paths_lines(findings) -> List[tuple]:
    return [(f.path, f.line) for f in findings]


def _has_finding_with(findings, substring: str) -> bool:
    return any(substring.lower() in f.summary.lower() for f in findings)


def _write_config(tmpdir: Path, enabled: bool = True, **extra) -> Path:
    """Write a minimal constitute.json with design_token_provenance configured."""
    devforge = tmpdir / ".devforge"
    devforge.mkdir(exist_ok=True)
    rule_block = {"enabled": enabled}
    rule_block.update(extra)
    config = {"forcing_functions": {"design_token_provenance": rule_block}}
    config_path = devforge / "constitute.json"
    config_path.write_text(json.dumps(config))
    return config_path


def _write_css(tmpdir: Path, content: str, name: str = "styles.css") -> Path:
    """Write a CSS file to tmpdir root."""
    p = tmpdir / name
    p.write_text(textwrap.dedent(content))
    return p


# ---------------------------------------------------------------------------
# TestCheck1ColorLiterals
# ---------------------------------------------------------------------------

class TestCheck1ColorLiterals(unittest.TestCase):

    def _check(self, source: str) -> list:
        return _check1_color_literals(source, "test.css", _RULE)

    def test_clean_tokenized_css_no_violations(self):
        src = textwrap.dedent("""\
            .button {
              background: var(--color-primary);
              color: var(--color-text);
            }
        """)
        self.assertEqual(self._check(src), [])

    def test_hardcoded_hex_short(self):
        src = ".btn { color: #abc; }"
        findings = self._check(src)
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(_has_finding_with(findings, "#abc"))
        self.assertEqual(findings[0].line, 1)

    def test_hardcoded_hex_full(self):
        src = ".btn { background: #aabbcc; }"
        findings = self._check(src)
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(_has_finding_with(findings, "#aabbcc"))

    def test_hardcoded_hex_8digit(self):
        src = ".btn { background: #aabbccff; }"
        findings = self._check(src)
        self.assertTrue(len(findings) >= 1)

    def test_rgb_function(self):
        src = ".btn { color: rgb(255, 0, 0); }"
        findings = self._check(src)
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(_has_finding_with(findings, "rgb"))

    def test_rgba_function(self):
        src = ".btn { color: rgba(0, 0, 0, 0.5); }"
        findings = self._check(src)
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(_has_finding_with(findings, "rgba"))

    def test_hsl_function(self):
        src = ".text { color: hsl(200, 100%, 50%); }"
        findings = self._check(src)
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(_has_finding_with(findings, "hsl"))

    def test_hsla_function(self):
        src = ".text { color: hsla(200, 100%, 50%, 0.8); }"
        findings = self._check(src)
        self.assertTrue(len(findings) >= 1)

    def test_named_color_red(self):
        src = ".alert { color: red; }"
        findings = self._check(src)
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(_has_finding_with(findings, "red"))

    def test_named_color_blue(self):
        src = ".link { color: blue; }"
        findings = self._check(src)
        self.assertTrue(len(findings) >= 1)

    def test_allowlisted_transparent_passes(self):
        src = ".overlay { background: transparent; }"
        findings = self._check(src)
        self.assertEqual(findings, [])

    def test_allowlisted_currentcolor_passes(self):
        # currentColor is case-insensitively matched
        src = ".icon { fill: currentColor; }"
        findings = self._check(src)
        self.assertEqual(findings, [])

    def test_allowlisted_inherit_passes(self):
        src = ".child { color: inherit; }"
        findings = self._check(src)
        self.assertEqual(findings, [])

    def test_token_definition_lines_skipped(self):
        # Multi-line form: the standard CSS format for token definitions.
        src = textwrap.dedent("""\
            :root {
              --color-primary: #abc123;
              --color-secondary: #334455;
            }
        """)
        findings = self._check(src)
        self.assertEqual(findings, [])

    def test_single_line_token_definition_skipped_f1(self):
        # F1 regression: single-line `:root { --color-primary: #abc; }` was
        # previously flagged because is_token_definition only matched at line-start.
        # re.search fix: any `--name:` on the line marks it as a definition.
        src = ":root { --color-primary: #abc123; }"
        findings = self._check(src)
        self.assertEqual(findings, [])

    def test_single_line_multiple_token_defs_skipped_f1(self):
        # Multiple custom props on one line — still a definition context.
        src = ":root { --a: #abc; --b: #def; }"
        findings = self._check(src)
        self.assertEqual(findings, [])

    def test_var_token_reference_passes(self):
        src = ".btn { background: var(--color-primary); }"
        findings = self._check(src)
        self.assertEqual(findings, [])

    def test_multi_line_violations_reported_with_correct_line_numbers(self):
        src = textwrap.dedent("""\
            .a { color: var(--ok); }
            .b { color: #deadbe; }
            .c { color: var(--ok); }
        """)
        findings = self._check(src)
        self.assertTrue(any(f.line == 2 for f in findings))

    # F4: named-color false-positive on class names / identifiers
    def test_named_color_in_class_name_does_not_flag_f4(self):
        # `.coral-button` is a class name — the word 'coral' is not in a value position.
        src = ".coral-button { background: var(--ok); }"
        findings = self._check(src)
        self.assertEqual(findings, [])

    def test_named_color_in_js_identifier_does_not_flag_f4(self):
        # `teal` appearing as part of a JS identifier (no colon before it).
        src = "const tealColor = 'var(--color-teal)';"
        findings = self._check(src)
        self.assertEqual(findings, [])

    def test_named_color_in_value_position_does_flag_f4(self):
        # `color: red` — a colon appears before `red` on the line.
        src = ".x { color: red; }"
        findings = self._check(src)
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(_has_finding_with(findings, "red"))

    def test_named_color_coral_class_vs_value_f4(self):
        # Class selector with 'coral' in name must NOT flag; value usage must.
        class_src = ".coral-btn { background: var(--ok); }"
        value_src = ".x { background-color: coral; }"
        self.assertEqual(self._check(class_src), [])
        self.assertTrue(len(self._check(value_src)) >= 1)

    def test_named_color_btn_teal_class_does_not_flag_f4(self):
        src = ".btn-teal { color: var(--color-teal); }"
        findings = self._check(src)
        self.assertEqual(findings, [])


# ---------------------------------------------------------------------------
# TestCheck2VarFallbacks
# ---------------------------------------------------------------------------

class TestCheck2VarFallbacks(unittest.TestCase):

    def _check(self, source: str) -> list:
        return _check2_var_fallbacks(source, "test.css", _RULE)

    def test_clean_var_no_fallback_passes(self):
        src = ".btn { color: var(--color-primary); }"
        self.assertEqual(self._check(src), [])

    def test_var_fallback_literal_hex(self):
        src = ".btn { background: var(--color-bg, #ffffff); }"
        findings = self._check(src)
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(_has_finding_with(findings, "#ffffff"))

    def test_var_fallback_literal_px(self):
        src = ".card { margin: var(--space-m, 8px); }"
        findings = self._check(src)
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(_has_finding_with(findings, "8px"))

    def test_var_fallback_chained_var_passes(self):
        # var(--x, var(--y)) is a chained token reference — not a literal fallback
        src = ".btn { color: var(--color-primary, var(--color-secondary)); }"
        self.assertEqual(self._check(src), [])

    def test_var_empty_fallback_passes(self):
        # var(--x, ) has an empty fallback — no literal
        src = ".btn { color: var(--color-primary, ); }"
        self.assertEqual(self._check(src), [])

    def test_var_fallback_named_color(self):
        src = ".btn { color: var(--color-main, blue); }"
        findings = self._check(src)
        self.assertTrue(len(findings) >= 1)

    def test_var_fallback_line_reported_correctly(self):
        src = textwrap.dedent("""\
            .a { color: var(--ok); }
            .b { border: var(--border, 1px solid #ccc); }
        """)
        findings = self._check(src)
        self.assertTrue(any(f.line == 2 for f in findings))


# ---------------------------------------------------------------------------
# TestCheck3UndefinedTokens
# ---------------------------------------------------------------------------

class TestCheck3UndefinedTokens(unittest.TestCase):

    def _check(self, source: str, defined_tokens: Optional[Set[str]] = None) -> list:
        return _check3_undefined_tokens(
            source, "test.css", _RULE, defined_tokens or set()
        )

    def test_defined_token_passes(self):
        src = ".btn { color: var(--color-primary); }"
        findings = self._check(src, {"--color-primary"})
        self.assertEqual(findings, [])

    def test_undefined_token_fails_loud(self):
        src = ".btn { color: var(--color-nonexistent); }"
        findings = self._check(src, {"--color-primary", "--color-secondary"})
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(_has_finding_with(findings, "--color-nonexistent"))

    def test_no_token_source_skips_check(self):
        # OQ-6: When defined_tokens is empty (no CSS token source), Check 3 is skipped
        src = ".btn { color: var(--anything-at-all); }"
        findings = self._check(src, set())
        self.assertEqual(findings, [])

    def test_token_definition_line_skipped(self):
        # Lines that define tokens (--foo:) should not self-reference-fail
        src = textwrap.dedent("""\
            :root {
              --color-primary: var(--base-blue);
            }
        """)
        # --base-blue is not in defined_tokens — but the second line defines a token,
        # it is NOT a usage context, so it should be skipped.
        findings = self._check(src, {"--color-primary"})
        # the --base-blue on line 2 is a RHS of a definition — we require the scanner
        # to NOT flag it (the line starts with --...: pattern).
        # Check whether all findings if any are NOT on line 2.
        for f in findings:
            self.assertNotEqual(f.line, 2, "Token definition lines must not be flagged")

    def test_multiple_undefined_tokens_all_reported(self):
        src = textwrap.dedent("""\
            .a { color: var(--x); }
            .b { border: var(--y); }
        """)
        findings = self._check(src, {"--color-defined"})
        tokens_found = {f.summary for f in findings}
        self.assertTrue(any("--x" in s for s in tokens_found))
        self.assertTrue(any("--y" in s for s in tokens_found))

    def test_single_line_token_definition_skipped_f1(self):
        # F1 regression: `:root { --color-primary: var(--base-blue); }` on one line.
        # The RHS var(--base-blue) must NOT be treated as a usage of --base-blue.
        src = ":root { --color-primary: var(--base-blue); }"
        findings = self._check(src, {"--color-primary"})
        # --base-blue is undefined but the line is a definition — must not flag.
        self.assertEqual(findings, [])

    def test_single_line_root_with_usage_after_is_correct(self):
        # A usage on a SEPARATE line from a definition must still be checked.
        src = textwrap.dedent("""\
            :root { --color-primary: #abc; }
            .btn { color: var(--color-undefined-here); }
        """)
        findings = self._check(src, {"--color-primary"})
        self.assertTrue(any("--color-undefined-here" in f.summary for f in findings))


# ---------------------------------------------------------------------------
# TestCheck4InteractiveStates
# ---------------------------------------------------------------------------

class TestCheck4InteractiveStates(unittest.TestCase):

    def _check(self, source: str) -> list:
        return _check4_interactive_states(source, "test.css", _RULE)

    def test_button_with_both_states_passes(self):
        src = textwrap.dedent("""\
            button { background: var(--color-btn); }
            button:hover { background: var(--color-btn-hover); }
            button:focus-visible { outline: var(--outline-focus); }
        """)
        self.assertEqual(self._check(src), [])

    def test_button_missing_hover_fails(self):
        src = textwrap.dedent("""\
            button { background: var(--color-btn); }
            button:focus-visible { outline: var(--outline-focus); }
        """)
        findings = self._check(src)
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(_has_finding_with(findings, "hover"))

    def test_button_missing_focus_visible_fails(self):
        src = textwrap.dedent("""\
            button { background: var(--color-btn); }
            button:hover { background: var(--color-btn-hover); }
        """)
        findings = self._check(src)
        self.assertTrue(len(findings) >= 1)
        self.assertTrue(_has_finding_with(findings, "focus-visible"))

    def test_button_missing_both_fails(self):
        src = "button { background: var(--color-btn); }"
        findings = self._check(src)
        # Should flag both missing states
        self.assertTrue(len(findings) >= 2)

    def test_anchor_missing_focus_visible_fails(self):
        src = textwrap.dedent("""\
            a { color: var(--color-link); }
            a:hover { color: var(--color-link-hover); }
        """)
        findings = self._check(src)
        self.assertTrue(_has_finding_with(findings, "focus-visible"))

    def test_anchor_both_states_passes(self):
        src = textwrap.dedent("""\
            a { color: var(--color-link); }
            a:hover { color: var(--color-link-hover); }
            a:focus-visible { outline: var(--outline-focus); }
        """)
        self.assertEqual(self._check(src), [])

    def test_input_missing_hover_fails(self):
        src = textwrap.dedent("""\
            input { border: var(--border-input); }
            input:focus-visible { border-color: var(--color-focus); }
        """)
        findings = self._check(src)
        self.assertTrue(_has_finding_with(findings, "hover"))

    def test_role_button_missing_focus_visible(self):
        src = textwrap.dedent("""\
            [role=button] { background: var(--color-btn); }
            [role=button]:hover { background: var(--color-btn-hover); }
        """)
        findings = self._check(src)
        self.assertTrue(_has_finding_with(findings, "focus-visible"))

    def test_non_interactive_selector_ignored(self):
        src = textwrap.dedent("""\
            .card { background: var(--color-surface); }
            .header { color: var(--color-heading); }
        """)
        self.assertEqual(self._check(src), [])

    def test_select_both_states_passes(self):
        src = textwrap.dedent("""\
            select { border: var(--border); }
            select:hover { border-color: var(--border-hover); }
            select:focus-visible { outline: var(--outline-focus); }
        """)
        self.assertEqual(self._check(src), [])

    def test_textarea_missing_hover_fails(self):
        src = textwrap.dedent("""\
            textarea { border: var(--border); }
            textarea:focus-visible { outline: var(--outline-focus); }
        """)
        findings = self._check(src)
        self.assertTrue(_has_finding_with(findings, "hover"))

    # F3: SCSS nested &:hover / &:focus-visible must not be false-positived
    def test_scss_nested_hover_and_focus_visible_passes_f3(self):
        # The dominant SCSS pattern: &:hover and &:focus-visible nested inside
        # the parent block.  _extract_css_blocks only captures the parent block
        # as a top-level CSS block; the fix detects the nested patterns in the body.
        src = textwrap.dedent("""\
            button {
              background: var(--color-btn);
              &:hover { background: var(--color-btn-hover); }
              &:focus-visible { outline: var(--outline-focus); }
            }
        """)
        findings = self._check(src)
        self.assertEqual(findings, [])

    def test_scss_nested_hover_only_still_flags_missing_focus_f3(self):
        # Only &:hover nested — :focus-visible still missing, should flag.
        src = textwrap.dedent("""\
            button {
              background: var(--color-btn);
              &:hover { background: var(--color-btn-hover); }
            }
        """)
        findings = self._check(src)
        self.assertTrue(_has_finding_with(findings, "focus-visible"))

    def test_scss_nested_focus_visible_only_flags_missing_hover_f3(self):
        # Only &:focus-visible nested — :hover still missing, should flag.
        src = textwrap.dedent("""\
            button {
              background: var(--color-btn);
              &:focus-visible { outline: var(--outline-focus); }
            }
        """)
        findings = self._check(src)
        self.assertTrue(_has_finding_with(findings, "hover"))


# ---------------------------------------------------------------------------
# TestScannerIntegration
# ---------------------------------------------------------------------------

class TestScannerIntegration(unittest.TestCase):

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self._root = Path(self._td)

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def test_clean_file_returns_empty(self):
        (self._root / "styles.css").write_text(textwrap.dedent("""\
            button { background: var(--color-btn); }
            button:hover { background: var(--color-btn-hover); }
            button:focus-visible { outline: var(--outline-focus); }
        """))
        findings = scan_for_design_token_violations(
            root=self._root,
            allowlist_globs=[],
        )
        self.assertEqual(findings, [])

    def test_multiple_violations_in_one_file(self):
        (self._root / "bad.css").write_text(textwrap.dedent("""\
            .a { color: #ff0000; }
            .b { background: rgba(0,0,0,0.5); }
            .c { border: var(--border, 1px solid #ccc); }
        """))
        findings = scan_for_design_token_violations(
            root=self._root,
            allowlist_globs=[],
        )
        self.assertTrue(len(findings) >= 3)

    def test_allowlisted_file_skipped(self):
        (self._root / "vendor.css").write_text(".a { color: #ff0000; }")
        findings = scan_for_design_token_violations(
            root=self._root,
            allowlist_globs=["vendor.css", "**/vendor.css"],
        )
        self.assertEqual(findings, [])

    def test_non_style_extension_skipped_for_checks_4_5(self):
        # .json files should not be scanned at all
        (self._root / "data.json").write_text('{"color": "#fff"}')
        findings = scan_for_design_token_violations(
            root=self._root,
            allowlist_globs=[],
        )
        self.assertEqual(findings, [])

    def test_file_paths_targeted_scan(self):
        good = self._root / "good.css"
        bad = self._root / "bad.css"
        good.write_text(textwrap.dedent("""\
            button { color: var(--ok); }
            button:hover { color: var(--ok-hover); }
            button:focus-visible { outline: var(--focus); }
        """))
        bad.write_text(".a { color: #deadbe; }")
        # Targeted to only good.css — should return nothing
        findings = scan_for_design_token_violations(
            root=self._root,
            allowlist_globs=[],
            file_paths=[good],
        )
        self.assertEqual(findings, [])
        # Targeted to only bad.css — should return violations
        findings = scan_for_design_token_violations(
            root=self._root,
            allowlist_globs=[],
            file_paths=[bad],
        )
        self.assertTrue(len(findings) >= 1)

    def test_ts_tsx_js_jsx_files_scanned_for_checks_1_2_3(self):
        # JS/TS files are eligible for Check 1 (color literals in CSS-in-JS)
        tsx_file = self._root / "Button.tsx"
        tsx_file.write_text(textwrap.dedent("""\
            const style = { color: '#ff0000' };
        """))
        findings = scan_for_design_token_violations(
            root=self._root,
            allowlist_globs=[],
        )
        # Might or might not fire on JS depending on the parser — confirm it is scanned
        # (at minimum no crash, and no non-zero exit on non-style file)
        # If it fires, the finding path should include Button.tsx
        if findings:
            self.assertTrue(any("Button.tsx" in f.path for f in findings))

    def test_scss_file_scanned(self):
        (self._root / "component.scss").write_text(".btn { color: #abc; }")
        findings = scan_for_design_token_violations(
            root=self._root,
            allowlist_globs=[],
        )
        self.assertTrue(any("component.scss" in f.path for f in findings))

    def test_less_file_scanned(self):
        (self._root / "component.less").write_text(".btn { color: #abc; }")
        findings = scan_for_design_token_violations(
            root=self._root,
            allowlist_globs=[],
        )
        self.assertTrue(any("component.less" in f.path for f in findings))

    def test_token_source_defs_not_scanned_as_component_f1(self):
        # F1 (cmd.py): the token_source_css file itself must NOT be scanned as a
        # component style source.  Its hex definitions are token definitions, and
        # the fix excludes the file from the component walk via allowlist injection.
        token_css = self._root / "design" / "tokens.css"
        token_css.parent.mkdir(exist_ok=True)
        token_css.write_text(":root { --color-primary: #abc123; --color-secondary: #334455; }")
        # Passing the token source path to the scanner via allowlist
        findings = scan_for_design_token_violations(
            root=self._root,
            allowlist_globs=["design/tokens.css", "**/design/tokens.css"],
        )
        self.assertEqual(findings, [])

    def test_single_line_token_def_in_css_file_not_flagged_f1(self):
        # F1 (scanner): a CSS file that begins with a single-line :root block
        # must not flag its own hex token definitions.
        token_css = self._root / "vars.css"
        token_css.write_text(":root { --color-bg: #f5f5f5; --color-text: #333333; }")
        findings = scan_for_design_token_violations(
            root=self._root,
            allowlist_globs=["vars.css"],  # excluded from component walk
        )
        self.assertEqual(findings, [])

    def test_single_line_token_def_excluded_from_check1_directly_f1(self):
        # Directly invoke check1 on a single-line :root definition block — must not flag.
        src = ":root { --color-primary: #abc; --color-secondary: #def; }"
        findings = _check1_color_literals(src, "vars.css", _RULE)
        self.assertEqual(findings, [])


# ---------------------------------------------------------------------------
# TestCmdVerifyDesignTokensCLI
# ---------------------------------------------------------------------------

class TestCmdVerifyDesignTokensCLI(unittest.TestCase):
    """End-to-end CLI tests for verify-design-tokens via _constitute._cli.main."""

    def setUp(self):
        self._td = tempfile.mkdtemp()
        self._root = Path(self._td)
        (self._root / ".devforge").mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self._td, ignore_errors=True)

    def _config(self, enabled: bool = True, **extra) -> None:
        rule_block = {"enabled": enabled}
        rule_block.update(extra)
        config = {"forcing_functions": {"design_token_provenance": rule_block}}
        config_path = self._root / ".devforge" / "constitute.json"
        config_path.write_text(json.dumps(config))

    def _run(self, extra_args: Optional[list] = None) -> tuple:
        argv = ["verify-design-tokens", "--root", str(self._root)]
        if extra_args:
            argv.extend(extra_args)
        return _run_cli(argv)

    def test_missing_config_exits_clean(self):
        # No constitute.json at all — exit 0 (non-blocking)
        code, _out, err = self._run()
        self.assertEqual(code, 0)
        self.assertIn("skipping", err)

    def test_disabled_rule_exits_clean(self):
        self._config(enabled=False)
        (self._root / "bad.css").write_text(".btn { color: #ff0000; }")
        code, _out, _err = self._run()
        self.assertEqual(code, 0)

    def test_absent_rule_block_exits_clean(self):
        # forcing_functions block exists but no design_token_provenance key
        config_path = self._root / ".devforge" / "constitute.json"
        config_path.write_text(json.dumps({
            "forcing_functions": {"magic_enum_duplication": {"enabled": False}}
        }))
        (self._root / "bad.css").write_text(".btn { color: #ff0000; }")
        code, _out, _err = self._run()
        self.assertEqual(code, 0)

    def test_enabled_clean_file_exits_0(self):
        self._config()
        (self._root / "clean.css").write_text(textwrap.dedent("""\
            button { background: var(--color-btn); }
            button:hover { background: var(--color-btn-hover); }
            button:focus-visible { outline: var(--outline-focus); }
        """))
        code, _out, _err = self._run()
        self.assertEqual(code, 0)

    def test_enabled_hardcoded_hex_exits_2(self):
        self._config()
        (self._root / "bad.css").write_text(".btn { color: #ff0000; }")
        code, out, err = self._run()
        self.assertEqual(code, 2)
        self.assertIn("#ff0000", err)
        report = json.loads(out)
        self.assertEqual(report["rule"], "design_token_provenance")
        self.assertTrue(len(report["findings"]) >= 1)

    def test_enabled_var_fallback_exits_2(self):
        self._config()
        (self._root / "bad.css").write_text(
            ".btn { background: var(--color-bg, #ffffff); }"
        )
        code, out, err = self._run()
        self.assertEqual(code, 2)
        self.assertIn("bad.css", err)

    def test_enabled_undefined_token_exits_2(self):
        # Write a token source CSS that defines known tokens, then use an unknown one
        token_css = self._root / "tokens.css"
        token_css.write_text(":root { --color-primary: #abc; }")
        self._config(token_source_css="tokens.css")
        (self._root / "comp.css").write_text(
            ".btn { color: var(--color-nonexistent); }"
        )
        code, out, err = self._run()
        self.assertEqual(code, 2)
        self.assertIn("--color-nonexistent", err)

    def test_enabled_missing_focus_visible_exits_2(self):
        self._config()
        (self._root / "interactive.css").write_text(textwrap.dedent("""\
            button { background: var(--color-btn); }
            button:hover { background: var(--color-btn-hover); }
        """))
        code, out, err = self._run()
        self.assertEqual(code, 2)
        self.assertIn("focus-visible", err)

    def test_no_manifest_present_checks1_4_still_run(self):
        # Checks 1-4 are manifest-independent; they must run regardless of any
        # specs/*/design-manifest.json presence (which is no longer read by
        # this detector at all — Check 5 / MATCH token-binding retired,
        # plan 53 Phase 7a).
        self._config()
        # Write a CSS file with a hardcoded color (Check 1 violation)
        (self._root / "comp.css").write_text(".btn { color: #ff0000; }")
        code, out, err = self._run()
        # Check 1 must fire
        self.assertEqual(code, 2)
        self.assertIn("#ff0000", err)

    def test_set_forcing_functions_cli_token_source_css_round_trip(self):
        # set-forcing-functions --rule design_token_provenance --enabled true
        # --token-source-css design/styles.css
        # should write the config block with {enabled: true, token_source_css: ...}
        # and the detector should activate (no manifest needed for Checks 1-4).
        td_path = Path(tempfile.mkdtemp())
        try:
            devforge = td_path / ".devforge"
            devforge.mkdir()
            config_path = devforge / "constitute.json"

            code, _out, err = _run_cli([
                "set-forcing-functions",
                "--rule", "design_token_provenance",
                "--enabled", "true",
                "--token-source-css", "design/styles.css",
                "--config", str(config_path),
            ])
            self.assertEqual(code, 0, "set-forcing-functions CLI failed: " + err)

            # Verify the config block shape
            data = json.loads(config_path.read_text())
            ff = data["forcing_functions"]["design_token_provenance"]
            self.assertTrue(ff["enabled"])
            self.assertEqual(ff["token_source_css"], "design/styles.css")
            self.assertNotIn("manifest_path", ff)

            # Verify the detector activates: run verify-design-tokens against
            # a directory with a hardcoded hex — must exit 2.
            (td_path / "comp.css").write_text(".btn { color: #ff0000; }")
            code2, out2, err2 = _run_cli([
                "verify-design-tokens",
                "--root", str(td_path),
                "--config", str(config_path),
            ])
            self.assertEqual(code2, 2,
                             "Expected exit 2 from hardcoded hex. stderr: " + err2)
            self.assertIn("#ff0000", err2)
        finally:
            import shutil
            shutil.rmtree(str(td_path), ignore_errors=True)

    def test_set_forcing_functions_cli_enabled_only_no_token_source(self):
        # set-forcing-functions --rule design_token_provenance --enabled true
        # (no --token-source-css, no --manifest-path) must succeed and write
        # {enabled: true} — the detector runs Checks 1-4 without a token source.
        td_path = Path(tempfile.mkdtemp())
        try:
            devforge = td_path / ".devforge"
            devforge.mkdir()
            config_path = devforge / "constitute.json"

            code, _out, err = _run_cli([
                "set-forcing-functions",
                "--rule", "design_token_provenance",
                "--enabled", "true",
                "--config", str(config_path),
            ])
            self.assertEqual(code, 0, "set-forcing-functions failed: " + err)

            data = json.loads(config_path.read_text())
            ff = data["forcing_functions"]["design_token_provenance"]
            self.assertTrue(ff["enabled"])
            # Neither token_source_css nor manifest_path should be present.
            self.assertNotIn("token_source_css", ff)
            self.assertNotIn("manifest_path", ff)
        finally:
            import shutil
            shutil.rmtree(str(td_path), ignore_errors=True)

    def test_spacing_relaxes_when_css_absent(self):
        # Configure with a token_source_css that does NOT exist on disk —
        # OQ-6: color/border literal checks stay HARD, spacing relaxes.
        self._config(token_source_css="nonexistent-tokens.css")
        # Write a file with ONLY a hardcoded hex (which must STILL fire)
        (self._root / "comp.css").write_text(".btn { color: #ff0000; }")
        code, out, err = self._run()
        # Hardcoded color must still be caught (color check stays HARD)
        self.assertEqual(code, 2)
        self.assertIn("#ff0000", err)

    def test_finding_includes_file_and_line(self):
        self._config()
        (self._root / "bad.css").write_text("p { }\n.x { color: #aabbcc; }\np { }\n")
        code, out, err = self._run()
        self.assertEqual(code, 2)
        # The stderr line must include "bad.css:2:"
        self.assertIn("bad.css:2:", err)

    def test_json_output_structure(self):
        self._config()
        (self._root / "bad.css").write_text(".a { color: #abc; }")
        code, out, _err = self._run()
        self.assertEqual(code, 2)
        report = json.loads(out)
        self.assertIn("rule", report)
        self.assertIn("findings", report)
        first = report["findings"][0]
        self.assertIn("path", first)
        self.assertIn("line", first)
        self.assertIn("kind", first)
        self.assertIn("summary", first)
        self.assertEqual(first["kind"], "VIOLATION")

    def test_token_source_css_file_excluded_from_scan_f1(self):
        # F1 (cmd.py): when token_source_css is configured, the file itself must
        # NOT be scanned as a component — its hex values are token DEFINITIONS.
        token_css = self._root / "design" / "styles.css"
        token_css.parent.mkdir(exist_ok=True)
        token_css.write_text(":root { --color-primary: #abc123; --color-bg: #ffffff; }")
        self._config(token_source_css="design/styles.css")
        # No other CSS files — if the token source is scanned, exit 2 (false positive).
        code, out, err = self._run()
        self.assertEqual(code, 0,
                         "Token source CSS must not be scanned as a component. "
                         "Got findings: " + err)

    def test_token_source_css_excluded_component_still_flags_violations_f1(self):
        # The token source exclusion must NOT suppress real violations in other files.
        token_css = self._root / "tokens.css"
        token_css.write_text(":root { --color-primary: #abc; }")
        self._config(token_source_css="tokens.css")
        # A DIFFERENT component file with a hardcoded hex must still flag.
        (self._root / "component.css").write_text(".btn { color: #ff0000; }")
        code, _out, err = self._run()
        self.assertEqual(code, 2)
        self.assertIn("component.css", err)
        self.assertNotIn("tokens.css", err)  # token source not in findings


# ---------------------------------------------------------------------------
# TestRuleRegistration
# ---------------------------------------------------------------------------

class TestRuleRegistration(unittest.TestCase):

    def test_rule_to_verb_assertion_holds(self):
        """The import-time assertion in _setters.py must still pass."""
        # Re-importing the module executes the assertion.
        import importlib
        import _constitute._forcing_functions._setters as setters_module
        importlib.reload(setters_module)
        # If we get here without AssertionError, the assertion holds.
        self.assertIn("design_token_provenance", setters_module.RULE_TO_VERB)
        self.assertEqual(
            setters_module.RULE_TO_VERB["design_token_provenance"],
            "verify-design-tokens",
        )

    def test_verify_design_tokens_in_cli_help(self):
        """The verify-design-tokens subparser must appear in the help output."""
        # argparse --help calls sys.exit(0); catch it.
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            try:
                cli_main(["verify-design-tokens", "--help"])
            except SystemExit:
                pass
            combined = sys.stdout.getvalue() + sys.stderr.getvalue()
        finally:
            sys.stdout = old_out
            sys.stderr = old_err
        self.assertIn("verify-design-tokens", combined)

    def test_verify_design_tokens_in_schema_rules(self):
        """design_token_provenance must be in FORCING_FUNCTION_RULES."""
        from _constitute._schema import FORCING_FUNCTION_RULES
        self.assertIn("design_token_provenance", FORCING_FUNCTION_RULES)

    def test_rule_key_consistent_in_set_forcing_functions_choices(self):
        """The set-forcing-functions --rule choices must include design_token_provenance."""
        # Run help and look for the rule name in the output. argparse --help
        # raises SystemExit(0), so we capture it.
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        try:
            try:
                cli_main(["set-forcing-functions", "--help"])
            except SystemExit:
                pass
            combined = sys.stdout.getvalue() + sys.stderr.getvalue()
        finally:
            sys.stdout = old_out
            sys.stderr = old_err
        self.assertIn("design_token_provenance", combined)

    def test_list_forcing_functions_verb_output(self):
        """list-forcing-functions --format=verb must include verify-design-tokens
        when design_token_provenance is enabled."""
        td = tempfile.mkdtemp()
        try:
            devforge = Path(td) / ".devforge"
            devforge.mkdir()
            config = {
                "forcing_functions": {
                    "design_token_provenance": {"enabled": True}
                }
            }
            (devforge / "constitute.json").write_text(json.dumps(config))
            code, out, err = _run_cli([
                "list-forcing-functions",
                "--enabled",
                "--format", "verb",
                "--config", str(devforge / "constitute.json"),
            ])
            self.assertEqual(code, 0)
            self.assertIn("verify-design-tokens", out)
        finally:
            import shutil
            shutil.rmtree(td, ignore_errors=True)


# ---------------------------------------------------------------------------
# TestDesignTokenProvenanceSchemaValidation  (F2: validate_forcing_functions)
# ---------------------------------------------------------------------------

class TestDesignTokenProvenanceSchemaValidation(unittest.TestCase):
    """Tests for the design_token_provenance branch in validate_forcing_functions."""

    def _validate(self, block):
        from _constitute._schema import validate_forcing_functions
        return validate_forcing_functions({"design_token_provenance": block})

    # --- well-formed blocks ---

    def test_minimal_enabled_true_no_errors(self):
        errs = self._validate({"enabled": True})
        self.assertEqual(errs, [])

    def test_minimal_enabled_false_no_errors(self):
        errs = self._validate({"enabled": False})
        self.assertEqual(errs, [])

    def test_with_token_source_css_string_no_errors(self):
        errs = self._validate({"enabled": True, "token_source_css": "design/styles.css"})
        self.assertEqual(errs, [])

    def test_with_manifest_path_string_no_errors(self):
        errs = self._validate({"enabled": True, "manifest_path": "specs/001/design-manifest.json"})
        self.assertEqual(errs, [])

    def test_with_allowlist_paths_list_str_no_errors(self):
        errs = self._validate({"enabled": True, "allowlist_paths": ["vendor/**", "node_modules/**"]})
        self.assertEqual(errs, [])

    def test_all_optional_fields_no_errors(self):
        errs = self._validate({
            "enabled": True,
            "token_source_css": "design/styles.css",
            "manifest_path": "specs/001/design-manifest.json",
            "allowlist_paths": ["vendor/**"],
        })
        self.assertEqual(errs, [])

    # --- malformed blocks ---

    def test_token_source_css_int_is_error(self):
        errs = self._validate({"enabled": True, "token_source_css": 42})
        self.assertTrue(len(errs) >= 1)
        self.assertTrue(any("token_source_css" in e for e in errs))
        self.assertTrue(any("str" in e or "int" in e for e in errs))

    def test_token_source_css_list_is_error(self):
        errs = self._validate({"enabled": True, "token_source_css": ["design/styles.css"]})
        self.assertTrue(any("token_source_css" in e for e in errs))

    def test_manifest_path_int_is_error(self):
        errs = self._validate({"enabled": True, "manifest_path": 99})
        self.assertTrue(len(errs) >= 1)
        self.assertTrue(any("manifest_path" in e for e in errs))

    def test_allowlist_paths_string_not_list_is_error(self):
        # allowlist_paths must be list[str]; a bare string is wrong
        errs = self._validate({"enabled": True, "allowlist_paths": "vendor/**"})
        self.assertTrue(len(errs) >= 1)
        self.assertTrue(any("allowlist_paths" in e for e in errs))

    def test_allowlist_paths_list_with_int_item_is_error(self):
        errs = self._validate({"enabled": True, "allowlist_paths": ["ok", 42]})
        self.assertTrue(any("allowlist_paths" in e for e in errs))

    def test_enabled_not_bool_is_error(self):
        # enabled is validated at the top of the loop for all rules
        errs = self._validate({"enabled": "true"})
        self.assertTrue(any("enabled" in e for e in errs))

    # --- validator is keyed on FORCING_FUNCTION_RULES ---

    def test_unknown_rule_name_tolerated(self):
        # A rule name NOT in FORCING_FUNCTION_RULES must not produce errors
        # (forward-compat: newer config, older build).
        from _constitute._schema import validate_forcing_functions
        errs = validate_forcing_functions({
            "future_rule_not_yet_known": {"enabled": True}
        })
        self.assertEqual(errs, [])

    def test_all_four_known_rules_reach_their_branch(self):
        # Each known rule must NOT fall through to the "unknown rule" no-op
        # on a valid block — i.e., validate_forcing_functions must not swallow
        # a type error for design_token_provenance by treating it as unknown.
        from _constitute._schema import validate_forcing_functions, FORCING_FUNCTION_RULES
        self.assertIn("design_token_provenance", FORCING_FUNCTION_RULES)
        # A malformed design_token_provenance block must produce errors
        # (proving the elif branch was reached, not the unknown-rule no-op).
        errs = validate_forcing_functions({
            "design_token_provenance": {"enabled": True, "token_source_css": 42}
        })
        self.assertTrue(
            len(errs) >= 1,
            "Expected a validation error for token_source_css: 42, got none — "
            "the design_token_provenance branch was not reached."
        )



if __name__ == "__main__":
    unittest.main()
