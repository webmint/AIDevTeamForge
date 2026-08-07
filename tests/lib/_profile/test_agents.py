"""Tests for src/devforge/lib/_profile/_agents.py.

Coverage:
  resolve_agent_span -- meta.json toolUseId join finds the right child
                         file among several; span = child file's
                         first-to-last event timestamps; no subagents dir
                         -> (None, False); no matching meta.json -> (None,
                         False); child file present but unparseable/empty
                         -> (None, False); resolution is relative to the
                         GIVEN transcript path's own directory (not a
                         global lookup), matching a --dir stitch's
                         per-file subagents dirs.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_TESTS_DIR = Path(__file__).resolve().parent

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from _profile._agents import resolve_agent_span  # noqa: E402

from _fixtures import assistant_text_line, write_subagent_file  # noqa: E402


def test_resolve_agent_span_found(tmp_path):
    session_id = "sess1"
    transcript_path = tmp_path / "{0}.jsonl".format(session_id)
    transcript_path.write_text("")  # the transcript file itself need not have content here

    write_subagent_file(
        str(tmp_path), session_id, "1", "toolu_agent1",
        child_lines=[
            assistant_text_line(0, "start"),
            assistant_text_line(120, "end"),
        ],
    )

    span, found = resolve_agent_span(str(transcript_path), "toolu_agent1")
    assert found is True
    assert span == 120.0


def test_resolve_agent_span_picks_correct_dispatch_among_several(tmp_path):
    session_id = "sess1"
    transcript_path = tmp_path / "{0}.jsonl".format(session_id)
    transcript_path.write_text("")

    write_subagent_file(
        str(tmp_path), session_id, "1", "toolu_other",
        child_lines=[assistant_text_line(0, "a"), assistant_text_line(5, "b")],
    )
    write_subagent_file(
        str(tmp_path), session_id, "2", "toolu_target",
        child_lines=[assistant_text_line(0, "a"), assistant_text_line(50, "b")],
    )

    span, found = resolve_agent_span(str(transcript_path), "toolu_target")
    assert found is True
    assert span == 50.0


def test_resolve_agent_span_no_subagents_dir(tmp_path):
    transcript_path = tmp_path / "sess1.jsonl"
    transcript_path.write_text("")
    span, found = resolve_agent_span(str(transcript_path), "toolu_x")
    assert found is False
    assert span is None


def test_resolve_agent_span_no_matching_meta(tmp_path):
    session_id = "sess1"
    transcript_path = tmp_path / "{0}.jsonl".format(session_id)
    transcript_path.write_text("")
    write_subagent_file(
        str(tmp_path), session_id, "1", "toolu_unrelated",
        child_lines=[assistant_text_line(0, "a")],
    )
    span, found = resolve_agent_span(str(transcript_path), "toolu_target")
    assert found is False
    assert span is None


def test_resolve_agent_span_empty_child_file_falls_back(tmp_path):
    session_id = "sess1"
    transcript_path = tmp_path / "{0}.jsonl".format(session_id)
    transcript_path.write_text("")
    write_subagent_file(
        str(tmp_path), session_id, "1", "toolu_target",
        child_lines=[],
    )
    span, found = resolve_agent_span(str(transcript_path), "toolu_target")
    assert found is False
    assert span is None


def test_resolve_agent_span_relative_to_own_transcript_dir(tmp_path):
    # Two separate transcript directories (simulating a --dir stitch of
    # sessions from different session dirs) must not cross-resolve.
    dir_a = tmp_path / "a"
    dir_b = tmp_path / "b"
    dir_a.mkdir()
    dir_b.mkdir()

    session_id = "sessX"
    transcript_a = dir_a / "{0}.jsonl".format(session_id)
    transcript_a.write_text("")
    transcript_b = dir_b / "{0}.jsonl".format(session_id)
    transcript_b.write_text("")

    write_subagent_file(
        str(dir_a), session_id, "1", "toolu_shared",
        child_lines=[assistant_text_line(0, "a"), assistant_text_line(10, "b")],
    )
    # dir_b has NO matching subagents -- resolving against transcript_b
    # must not find dir_a's agent file even though the tool_use_id matches.
    span, found = resolve_agent_span(str(transcript_b), "toolu_shared")
    assert found is False
    assert span is None

    span_a, found_a = resolve_agent_span(str(transcript_a), "toolu_shared")
    assert found_a is True
    assert span_a == 10.0
