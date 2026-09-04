"""Tests for src/devforge/lib/_profile/_segment.py.

Coverage:
  match_command_marker    -- pre-63 bare form, post-63 devforge: namespaced
                              form, /clear, non-marker text, embedded (not
                              leading) marker text is rejected.
  match_helper_fallback   -- every known command's helper stem matches its
                              own command; the pr-review / review stem
                              disambiguation (word-boundary, no cross-match);
                              init-forge's irregular init_helper stem;
                              no match on unrelated text.
  KNOWN_COMMANDS / HELPER_STEMS -- all 21 names present, no duplicates.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _profile._segment import (  # noqa: E402
    HELPER_STEMS,
    KNOWN_COMMANDS,
    match_command_marker,
    match_helper_fallback,
)


# ---------------------------------------------------------------------------
# match_command_marker
# ---------------------------------------------------------------------------


def test_marker_pre63_bare_form():
    text = "<command-name>/plan</command-name><command-message>plan</command-message><command-args></command-args>"
    assert match_command_marker(text) == "plan"


def test_marker_post63_namespaced_form():
    text = "<command-name>/devforge:plan</command-name><command-message>plan</command-message><command-args></command-args>"
    assert match_command_marker(text) == "plan"


def test_marker_clear_recognized():
    text = "<command-name>/clear</command-name><command-message>clear</command-message><command-args></command-args>"
    assert match_command_marker(text) == "clear"


def test_marker_all_pre63_observed_names():
    # Every name the Phase 0 probe observed in a real pre-63 transcript.
    names = [
        "implement", "review", "clear", "fix", "plan", "grill", "verify",
        "finalize", "research", "summarize", "breakdown", "specify",
        "spec-check", "discover", "generate-docs", "report-bug",
    ]
    for name in names:
        text = "<command-name>/{0}</command-name><command-message>x</command-message><command-args></command-args>".format(name)
        assert match_command_marker(text) == name


def test_marker_non_marker_text_returns_none():
    assert match_command_marker("just a normal message") is None


def test_marker_embedded_not_leading_returns_none():
    # The marker must be at the START of the content, not just present.
    text = "some preamble <command-name>/plan</command-name>"
    assert match_command_marker(text) is None


def test_marker_non_string_returns_none():
    assert match_command_marker(None) is None
    assert match_command_marker(123) is None


# ---------------------------------------------------------------------------
# match_helper_fallback
# ---------------------------------------------------------------------------


def test_fallback_matches_every_known_command_stem():
    for cmd, stem in HELPER_STEMS.items():
        command_string = "{0} preflight --workspace-root .".format(stem)
        assert match_helper_fallback(command_string) == cmd


def test_fallback_pr_review_does_not_crossmatch_review():
    # "review_helper" is a literal substring of "pr_review_helper" -- the
    # word-boundary match must NOT let the shorter stem win here.
    assert match_helper_fallback("pr_review_helper preflight") == "pr-review"


def test_fallback_review_alone_matches_review():
    assert match_helper_fallback("review_helper preflight") == "review"


def test_fallback_init_forge_irregular_stem():
    assert match_helper_fallback("init_helper set-project-name") == "init-forge"


def test_fallback_no_match_on_unrelated_command():
    assert match_helper_fallback("ls -la") is None
    assert match_helper_fallback("git status") is None


def test_fallback_empty_string_returns_none():
    assert match_helper_fallback("") is None
    assert match_helper_fallback(None) is None


# ---------------------------------------------------------------------------
# Registry integrity
# ---------------------------------------------------------------------------


def test_known_commands_has_21_unique_entries():
    assert len(KNOWN_COMMANDS) == 21
    assert len(set(KNOWN_COMMANDS)) == 21


def test_known_commands_matches_helper_stems_keys():
    assert set(KNOWN_COMMANDS) == set(HELPER_STEMS.keys())
