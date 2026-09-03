"""tests/lib/test_model_version_tripwire.py

Tests for scripts/lib/model_version_tripwire.py (plan 92, Deliverable 5's
version-tripwire half — D3).

Structure
---------
TestLiveSrc            — THE GATE: find_version_strings against the real
                          src/ tree. Step 0b recorded zero hits for both
                          patterns on 2026-09-03; a non-zero result means
                          something landed since (see that module's
                          docstring).
TestAPIIDShape          — synthetic fixture: a planted `claude-opus-5`
                          (API-ID shape) is caught, with the right
                          path/line/pattern.
TestDisplayNameShape    — synthetic fixtures: `Opus 5`, `OPUS 5`,
                          `sonnet-4-5` (hyphen-joined pseudo-version, no
                          whitespace) and `Sonnet - 5` (spaced hyphen) are
                          all caught by the display-name-with-version
                          shape, case-insensitive, separator = whitespace
                          and/or hyphen.
TestNoFalsePositive     — synthetic fixture: `opus5` (no separator), a
                          bare `opus`, and `opus-route` (hyphen followed by
                          a LETTER, not a digit) are NOT caught — the tier
                          names legitimately appear all over src/ and must
                          not themselves trip the tripwire.
TestPycacheSkipped      — synthetic fixture: a version string planted only
                          inside a `__pycache__/` file is invisible.
TestSymlinkLoop         — synthetic fixture: a symlink cycle
                          (`root/sub/loop` -> `root`) returns promptly with
                          no findings and no recursion error.
TestCLI                 — main()'s exit codes on a clean tree, a planted
                          tree, and a missing root.

Both patterns are proven independently (TestAPIIDShape vs
TestDisplayNameShape) because the plan's own Verify bullet is explicit that
a test only catching the API-ID shape passes it "by half" — the
display-name shape is the likelier one a well-meaning author writes into
prose. Within TestDisplayNameShape, the hyphen-joined and spaced-hyphen
cases are proven separately from the whitespace-separated case because a
bare `\\s+` separator would have missed both — see
scripts/lib/model_version_tripwire.py's module docstring.
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Make scripts/lib importable
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # repo root
_SCRIPTS_LIB = _REPO_ROOT / "scripts" / "lib"
if str(_SCRIPTS_LIB) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_LIB))

import model_version_tripwire as m  # noqa: E402


def _write(path, text):
    # type: (Path, str) -> None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text), encoding="utf-8")


# ---------------------------------------------------------------------------
# TestLiveSrc — THE GATE
# ---------------------------------------------------------------------------


class TestLiveSrc(unittest.TestCase):
    """The permanent, standing regression gate over the real src/ tree.

    Step 0b (92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md, 2026-09-03) recorded
    zero hits on both patterns against the live src/ tree — this test pins
    that baseline rather than discovering it. A failure here means a
    version-bound string landed under src/ since that sweep; per the
    plan's own instruction, its premise ("src/ stays clean") must be
    re-derived at the failure site, not silently patched around.
    """

    def test_live_src_has_zero_version_string_findings(self):
        findings = m.find_version_strings(_REPO_ROOT / "src")
        self.assertEqual(
            findings,
            [],
            msg=(
                "version-bound string(s) found under src/ — plan 92 D3 "
                "requires the framework store no version, ever: "
                "{!r}".format(findings)
            ),
        )


# ---------------------------------------------------------------------------
# TestAPIIDShape
# ---------------------------------------------------------------------------


class TestAPIIDShape(unittest.TestCase):

    def test_planted_api_id_is_caught_with_right_path_line_pattern(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(
                root / "notes.md",
                """
                First line, nothing here.
                Second line: pin via claude-opus-5 for this agent.
                Third line, nothing here either.
                """,
            )
            findings = m.find_version_strings(root)
            api_findings = [f for f in findings if f.pattern == "api-id"]
            self.assertEqual(len(api_findings), 1, msg=repr(findings))
            finding = api_findings[0]
            self.assertEqual(finding.path, "notes.md")
            self.assertEqual(finding.text, "claude-opus-5")
            # Confirm the reported line actually contains the match, rather
            # than hardcoding a line number that shifts with dedent/leading
            # blank-line accounting.
            written_lines = (root / "notes.md").read_text(encoding="utf-8").splitlines()
            self.assertIn("claude-opus-5", written_lines[finding.line - 1])


# ---------------------------------------------------------------------------
# TestDisplayNameShape
# ---------------------------------------------------------------------------


class TestDisplayNameShape(unittest.TestCase):

    def test_planted_display_name_with_version_is_caught(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root / "rationale.md", "We recommend Opus 5 for this tier.\n")
            findings = m.find_version_strings(root)
            display_findings = [f for f in findings if f.pattern == "display-name"]
            self.assertEqual(len(display_findings), 1, msg=repr(findings))
            finding = display_findings[0]
            self.assertEqual(finding.path, "rationale.md")
            self.assertEqual(finding.text, "Opus 5")
            self.assertEqual(finding.line, 1)

    def test_planted_display_name_is_case_insensitive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root / "shout.md", "DO NOT SHIP OPUS 5 HARDCODED.\n")
            findings = m.find_version_strings(root)
            display_findings = [f for f in findings if f.pattern == "display-name"]
            self.assertEqual(len(display_findings), 1, msg=repr(findings))
            self.assertEqual(display_findings[0].text, "OPUS 5")

    def test_planted_hyphen_joined_pseudo_version_is_caught(self):
        # No whitespace at all — the shape that slips a bare `\s+`
        # separator AND has no `claude-` prefix to be caught by API_ID_RE.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root / "config-example.md", "Example pin: sonnet-4-5\n")
            findings = m.find_version_strings(root)
            display_findings = [f for f in findings if f.pattern == "display-name"]
            self.assertEqual(len(display_findings), 1, msg=repr(findings))
            self.assertEqual(display_findings[0].text, "sonnet-4")

    def test_planted_spaced_hyphen_is_caught(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root / "spaced.md", "We recommend Sonnet - 5 for this tier.\n")
            findings = m.find_version_strings(root)
            display_findings = [f for f in findings if f.pattern == "display-name"]
            self.assertEqual(len(display_findings), 1, msg=repr(findings))
            self.assertEqual(display_findings[0].text, "Sonnet - 5")


# ---------------------------------------------------------------------------
# TestNoFalsePositive
# ---------------------------------------------------------------------------


class TestNoFalsePositive(unittest.TestCase):

    def test_no_whitespace_and_bare_tier_names_do_not_match(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(
                root / "clean.md",
                """
                The opus5 build tag is unrelated to a model version.
                model_tier: opus
                Configured tier: opus
                """,
            )
            findings = m.find_version_strings(root)
            self.assertEqual(findings, [], msg=repr(findings))

    def test_hyphen_followed_by_letter_does_not_match(self):
        # The widened separator is `[\s-]+` followed by a DIGIT — a hyphen
        # followed by a letter (an ordinary hyphenated word, not a
        # pseudo-version) must not trip it.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root / "routing.md", "See the opus-route dispatch table.\n")
            findings = m.find_version_strings(root)
            self.assertEqual(findings, [], msg=repr(findings))


# ---------------------------------------------------------------------------
# TestPycacheSkipped
# ---------------------------------------------------------------------------


class TestPycacheSkipped(unittest.TestCase):

    def test_pycache_contents_are_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(
                root / "__pycache__" / "stale.py",
                "MODEL = 'claude-opus-5'  # Opus 5 in a compiled-cache leftover\n",
            )
            _write(root / "clean.py", "MODEL_TIER = 'think'\n")
            findings = m.find_version_strings(root)
            self.assertEqual(findings, [], msg=repr(findings))


# ---------------------------------------------------------------------------
# TestSymlinkLoop
# ---------------------------------------------------------------------------


class TestSymlinkLoop(unittest.TestCase):
    """A symlink cycle must terminate the walk, never recurse forever.

    `os.walk(followlinks=False)` lists a symlinked directory once in its
    parent's dirnames but never descends into it — see
    scripts/lib/model_version_tripwire.py's module docstring. This test is
    the proof: `root/sub/loop` points back at `root` itself.
    """

    def test_symlink_cycle_returns_promptly_with_no_findings(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root / "clean.py", "MODEL_TIER = 'think'\n")
            (root / "sub").mkdir()
            try:
                os.symlink(str(root), str(root / "sub" / "loop"), target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks not supported on this platform")
            findings = m.find_version_strings(root)
            self.assertEqual(findings, [], msg=repr(findings))


# ---------------------------------------------------------------------------
# TestCLI
# ---------------------------------------------------------------------------


class TestCLI(unittest.TestCase):

    def _run_main(self, *args):
        # type: (*str) -> tuple
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = m.main(list(args))
        return rc, buf.getvalue()

    def test_cli_exits_zero_on_clean_tree(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root / "clean.md", "Nothing version-bound here.\n")
            rc, out = self._run_main(str(root))
            self.assertEqual(rc, 0, msg=out)
            self.assertIn("PASS", out)

    def test_cli_exits_one_on_planted_tree(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _write(root / "dirty.md", "Pin: claude-opus-5\n")
            rc, out = self._run_main(str(root))
            self.assertEqual(rc, 1, msg=out)
            self.assertIn("FAIL", out)
            self.assertIn("claude-opus-5", out)

    def test_cli_exits_two_on_missing_root(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "does-not-exist"
            rc, _out = self._run_main(str(missing))
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
