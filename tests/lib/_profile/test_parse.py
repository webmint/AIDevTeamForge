"""Tests for src/devforge/lib/_profile/_parse.py.

Coverage:
  _parse_ts               -- ms-precision + no-fraction + malformed input.
  parse_transcript_file    -- tolerant parse: bad line + unknown-type lines
                               skipped and counted; user text -> command
                               marker extraction; user tool_result blocks;
                               assistant tool_use blocks; system
                               turn_duration; missing file returns ([], 0).
  parse_transcript_chain   -- multi-file concatenation + chronological
                               re-sort regardless of input file order.
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

from _profile._parse import _parse_ts, parse_transcript_chain, parse_transcript_file  # noqa: E402

from _fixtures import (  # noqa: E402
    assistant_tooluse_line,
    command_marker_text,
    system_turn_duration_line,
    user_text_line,
    user_toolresult_line,
    write_jsonl,
)


# ---------------------------------------------------------------------------
# _parse_ts
# ---------------------------------------------------------------------------


def test_parse_ts_ms_precision():
    result = _parse_ts("2026-08-05T10:00:00.123Z")
    assert result is not None
    assert abs(result - int(result) - 0.123) < 1e-6


def test_parse_ts_no_fraction():
    result = _parse_ts("2026-08-05T10:00:00Z")
    assert result is not None


def test_parse_ts_malformed_returns_none():
    assert _parse_ts("not-a-timestamp") is None
    assert _parse_ts("") is None
    assert _parse_ts(None) is None


def test_parse_ts_monotonic_offsets():
    t0 = _parse_ts("2026-08-05T10:00:00.000Z")
    t1 = _parse_ts("2026-08-05T10:00:05.500Z")
    assert t1 - t0 == 5.5


# ---------------------------------------------------------------------------
# parse_transcript_file -- tolerant parse
# ---------------------------------------------------------------------------


def test_tolerant_parse_bad_line_and_unknown_type_skipped_and_counted(tmp_path):
    path = tmp_path / "t.jsonl"
    write_jsonl(str(path), [
        user_text_line(0, "hello"),
        "not valid json {{{",
        {"type": "mystery-type", "timestamp": "2026-08-05T10:00:01.000Z"},
        {"type": "attachment", "timestamp": "2026-08-05T10:00:02.000Z"},
    ])
    events, n_skipped = parse_transcript_file(str(path))
    assert len(events) == 1
    assert n_skipped == 3


def test_parse_missing_file_returns_empty():
    events, n_skipped = parse_transcript_file("/nonexistent/path/does-not-exist.jsonl")
    assert events == []
    assert n_skipped == 0


def test_parse_blank_lines_ignored(tmp_path):
    path = tmp_path / "t.jsonl"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n")
        fh.write("   \n")
    events, n_skipped = parse_transcript_file(str(path))
    assert events == []
    assert n_skipped == 0


def test_parse_line_missing_timestamp_skipped(tmp_path):
    path = tmp_path / "t.jsonl"
    write_jsonl(str(path), [
        {"type": "user", "sessionId": "s", "message": {"role": "user", "content": "hi"}},
    ])
    events, n_skipped = parse_transcript_file(str(path))
    assert events == []
    assert n_skipped == 1


# ---------------------------------------------------------------------------
# user lines -- text vs tool_result carrier
# ---------------------------------------------------------------------------


def test_user_plain_text_line_has_text_and_no_marker(tmp_path):
    path = tmp_path / "t.jsonl"
    write_jsonl(str(path), [user_text_line(0, "just chatting")])
    events, _ = parse_transcript_file(str(path))
    assert events[0]["text"] == "just chatting"
    assert events[0]["command_marker"] is None
    assert events[0]["tool_results"] == []


def test_user_command_marker_extracted(tmp_path):
    path = tmp_path / "t.jsonl"
    write_jsonl(str(path), [user_text_line(0, command_marker_text("/plan"))])
    events, _ = parse_transcript_file(str(path))
    assert events[0]["command_marker"] == "plan"


def test_user_namespaced_command_marker_extracted(tmp_path):
    path = tmp_path / "t.jsonl"
    write_jsonl(str(path), [user_text_line(0, command_marker_text("/devforge:plan"))])
    events, _ = parse_transcript_file(str(path))
    assert events[0]["command_marker"] == "plan"


def test_user_tool_result_carrier_has_no_text(tmp_path):
    path = tmp_path / "t.jsonl"
    write_jsonl(str(path), [user_toolresult_line(0, "toolu_1")])
    events, _ = parse_transcript_file(str(path))
    assert events[0]["text"] is None
    assert events[0]["tool_results"] == [{"tool_use_id": "toolu_1", "duration_ms": None}]


def test_user_is_meta_flag_preserved(tmp_path):
    path = tmp_path / "t.jsonl"
    write_jsonl(str(path), [user_text_line(0, "meta note", is_meta=True)])
    events, _ = parse_transcript_file(str(path))
    assert events[0]["is_meta"] is True


def test_user_tool_result_duration_ms_captured(tmp_path):
    path = tmp_path / "t.jsonl"
    write_jsonl(str(path), [user_toolresult_line(0, "toolu_1", duration_ms=1500)])
    events, _ = parse_transcript_file(str(path))
    assert events[0]["tool_results"][0]["duration_ms"] == 1500


# ---------------------------------------------------------------------------
# assistant lines -- tool_use extraction
# ---------------------------------------------------------------------------


def test_assistant_bash_tool_use_captures_command(tmp_path):
    path = tmp_path / "t.jsonl"
    write_jsonl(str(path), [
        assistant_tooluse_line(0, "toolu_1", "Bash", command="plan_helper preflight"),
    ])
    events, _ = parse_transcript_file(str(path))
    tu = events[0]["tool_uses"][0]
    assert tu["id"] == "toolu_1"
    assert tu["name"] == "Bash"
    assert tu["command"] == "plan_helper preflight"


def test_assistant_non_bash_tool_use_command_is_none(tmp_path):
    path = tmp_path / "t.jsonl"
    write_jsonl(str(path), [
        assistant_tooluse_line(0, "toolu_1", "AskUserQuestion"),
    ])
    events, _ = parse_transcript_file(str(path))
    assert events[0]["tool_uses"][0]["command"] is None


def test_assistant_tool_use_duration_ms_captured(tmp_path):
    path = tmp_path / "t.jsonl"
    write_jsonl(str(path), [
        assistant_tooluse_line(0, "toolu_1", "Bash", command="x_helper", duration_ms=42),
    ])
    events, _ = parse_transcript_file(str(path))
    assert events[0]["tool_uses"][0]["duration_ms"] == 42


# ---------------------------------------------------------------------------
# system lines -- turn_duration
# ---------------------------------------------------------------------------


def test_system_turn_duration_captured(tmp_path):
    path = tmp_path / "t.jsonl"
    write_jsonl(str(path), [system_turn_duration_line(0, 2490719, 198)])
    events, _ = parse_transcript_file(str(path))
    assert events[0]["type"] == "system"
    assert events[0]["turn_duration_ms"] == 2490719
    assert events[0]["message_count"] == 198


def test_system_non_turn_duration_subtype_has_none(tmp_path):
    path = tmp_path / "t.jsonl"
    write_jsonl(str(path), [
        {"type": "system", "subtype": "something-else", "timestamp": "2026-08-05T10:00:00.000Z"},
    ])
    events, _ = parse_transcript_file(str(path))
    assert events[0]["turn_duration_ms"] is None


# ---------------------------------------------------------------------------
# parse_transcript_chain -- multi-file concatenation
# ---------------------------------------------------------------------------


def test_chain_concatenates_and_sorts_chronologically(tmp_path):
    early = tmp_path / "early.jsonl"
    later = tmp_path / "later.jsonl"
    write_jsonl(str(early), [user_text_line(0, "first")])
    write_jsonl(str(later), [user_text_line(100, "second")])

    # Pass in REVERSED order deliberately -- the chain must still come out
    # chronological, defending against an out-of-mtime-order caller.
    events, n_skipped = parse_transcript_chain([str(later), str(early)])
    assert n_skipped == 0
    assert [e["text"] for e in events] == ["first", "second"]


def test_chain_sums_skips_across_files(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    write_jsonl(str(a), ["bad json a"])
    write_jsonl(str(b), ["bad json b", user_text_line(0, "ok")])
    events, n_skipped = parse_transcript_chain([str(a), str(b)])
    assert len(events) == 1
    assert n_skipped == 2
