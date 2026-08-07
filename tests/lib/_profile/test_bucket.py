"""Tests for src/devforge/lib/_profile/_bucket.py -- the core segmentation +
bucket-profiling algorithm.

Coverage (per the plan-70 build brief's required minimum):
  - a Bash call bucketed into bash_s
  - a sync-style Agent dispatch (no child subagent file -> parent-gap
    fallback for BOTH task_s and agent_busy_s)
  - an async Agent dispatch (short parent gap + a real child
    subagents/agent-<id>.jsonl + meta.json giving a longer span) --
    asserts task_s uses the parent gap, agent_busy_s uses the child span,
    and neither is double-counted
  - a legacy "Task"-named dispatch (pre-2.1.195 tool name) behaves
    identically to "Agent"
  - an AskUserQuestion tool_use->tool_result gap lands in human_s, not
    bash_s/task_s/llm_s (D4)
  - a genuine human text gap is classified human_s, not llm_s (D4)
  - the four main-thread buckets (llm_s + bash_s + task_s + human_s) sum
    to wall (+/- floating-point rounding) for every segment
  - multi-command segmentation: a pre-63 bare marker, a post-63
    devforge:-namespaced marker, a <cmd>_helper fallback-only segment (no
    marker at all), and a leading (preamble) segment, all in one stream
  - the unmatched tool_use guard (n_unmatched_tools) for a tool_use with
    no matching tool_result

Coverage added for the interval-based redesign (python-reviewer findings
1-5, see _bucket.py's module docstring for the full mechanism):
  - Finding 1: a dispatch's tool_result arriving AFTER a marker-triggered
    segment close, and after a helper-fallback-triggered close -- both
    segments' main-thread buckets must sum to their OWN wall (no spill).
  - Finding 2: parallel Bash tool_use blocks in one assistant turn with
    overlapping windows -- bash_s is the interval UNION, not the naive sum.
  - Finding 2 (priority): overlapping Bash + AskUserQuestion windows --
    human wins the overlap per the fixed human > task > bash priority.
  - Finding 3: durationMs overrides interval LENGTH (end always the
    tool_result ts; start = result_ts - duration_s), clamped to the
    tool_use's own ts when durationMs would predate it.
  - Finding 4: an orphan tool_result (no matching open tool_use) is
    counted in n_orphan_results and contributes to no bucket.
  - Finding 5: n_helpers uses match_helper_fallback's word-boundary stem
    match, not a loose "_helper" substring check.
  - Direct unit coverage of the interval-arithmetic primitives
    (_merge_intervals, _subtract_intervals, _clip_intervals,
    _interval_length, _resolve_interval, _segment_index_for_ts).
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

from _profile._bucket import (  # noqa: E402
    _clip_intervals,
    _interval_length,
    _merge_intervals,
    _resolve_interval,
    _segment_index_for_ts,
    _subtract_intervals,
    compute_totals,
    profile_events,
)
from _profile._parse import parse_transcript_file  # noqa: E402

from _fixtures import (  # noqa: E402
    assistant_multi_tooluse_line,
    assistant_text_line,
    assistant_tooluse_line,
    command_marker_text,
    user_text_line,
    user_toolresult_line,
    write_jsonl,
    write_subagent_file,
)


def _profile(tmp_path, lines, filename="sess1.jsonl"):
    path = tmp_path / filename
    write_jsonl(str(path), lines)
    events, n_skipped = parse_transcript_file(str(path))
    segments = profile_events(events)
    return segments, n_skipped, str(path)


def _assert_main_thread_sums_to_wall(seg):
    computed = seg["llm_s"] + seg["bash_s"] + seg["task_s"] + seg["human_s"]
    assert abs(computed - seg["wall"]) < 1e-6, seg


# ---------------------------------------------------------------------------
# Bash call
# ---------------------------------------------------------------------------


def test_bash_call_bucketed_into_bash_s(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_tooluse_line(1, "toolu_bash1", "Bash", command="plan_helper preflight"),
        user_toolresult_line(3, "toolu_bash1"),
    ]
    segments, n_skipped, _ = _profile(tmp_path, lines)
    assert n_skipped == 0
    seg = segments[0]
    assert seg["command"] == "plan"
    assert seg["bash_s"] == 2.0
    assert seg["n_helpers"] == 1
    _assert_main_thread_sums_to_wall(seg)


# ---------------------------------------------------------------------------
# sync-style Agent dispatch -- no child file, parent-gap fallback both places
# ---------------------------------------------------------------------------


def test_sync_agent_dispatch_no_child_file_uses_parent_gap_for_both(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_tooluse_line(1, "toolu_agent1", "Agent"),
        user_toolresult_line(1 + 30, "toolu_agent1"),  # 30s parent gap, no child file
    ]
    segments, _, _ = _profile(tmp_path, lines)
    seg = segments[0]
    assert seg["task_s"] == 30.0
    assert seg["agent_busy_s"] == 30.0  # fallback: no child file found
    assert seg["n_agents"] == 1
    _assert_main_thread_sums_to_wall(seg)


# ---------------------------------------------------------------------------
# async Agent dispatch -- short parent gap, long child span, no double-count
# ---------------------------------------------------------------------------


def test_async_agent_dispatch_task_s_uses_parent_gap_agent_busy_uses_child_span(tmp_path):
    session_id = "sess-async"
    lines = [
        user_text_line(0, command_marker_text("/plan"), session_id=session_id),
        assistant_tooluse_line(1, "toolu_agent1", "Agent", session_id=session_id),
        # Parent-side tool_result returns quickly (3s) -- the async pattern.
        user_toolresult_line(4, "toolu_agent1", session_id=session_id),
    ]
    transcript_path = tmp_path / "{0}.jsonl".format(session_id)
    write_jsonl(str(transcript_path), lines)

    # The child ran for 120s in its own transcript, well past the 3s parent gap.
    write_subagent_file(
        str(tmp_path), session_id, "1", "toolu_agent1",
        child_lines=[assistant_text_line(1, "start"), assistant_text_line(121, "end")],
    )

    events, n_skipped = parse_transcript_file(str(transcript_path))
    segments = profile_events(events)
    seg = segments[0]

    assert n_skipped == 0
    assert seg["task_s"] == 3.0          # parent-side gap: main-thread blocked time
    assert seg["agent_busy_s"] == 120.0  # child file span: real agent runtime
    assert seg["n_agents"] == 1
    # The wall-sum invariant only covers the four MAIN-THREAD buckets;
    # agent_busy_s is deliberately excluded (can overlap llm_s for async work).
    _assert_main_thread_sums_to_wall(seg)
    # Explicitly confirm agent_busy_s is NOT part of that sum (no double-count
    # of the async agent's real runtime into the main-thread wall).
    assert seg["wall"] == 4.0


# ---------------------------------------------------------------------------
# Legacy "Task"-named dispatch behaves like "Agent"
# ---------------------------------------------------------------------------


def test_legacy_task_named_dispatch_behaves_like_agent(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_tooluse_line(1, "toolu_task1", "Task"),
        user_toolresult_line(1 + 12, "toolu_task1"),
    ]
    segments, _, _ = _profile(tmp_path, lines)
    seg = segments[0]
    assert seg["task_s"] == 12.0
    assert seg["agent_busy_s"] == 12.0  # no child file -> parent-gap fallback
    assert seg["n_agents"] == 1


# ---------------------------------------------------------------------------
# AskUserQuestion -> human_s
# ---------------------------------------------------------------------------


def test_askuserquestion_gap_is_human_s_not_other_buckets(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_tooluse_line(1, "toolu_ask1", "AskUserQuestion"),
        user_toolresult_line(1 + 45, "toolu_ask1"),  # 45s answering
    ]
    segments, _, _ = _profile(tmp_path, lines)
    seg = segments[0]
    assert seg["human_s"] == 45.0
    assert seg["bash_s"] == 0.0
    assert seg["task_s"] == 0.0
    _assert_main_thread_sums_to_wall(seg)


# ---------------------------------------------------------------------------
# Genuine human text gap -> human_s, not llm_s
# ---------------------------------------------------------------------------


def test_genuine_human_text_gap_is_human_s(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_text_line(1, "sure, working on it"),
        # A genuine follow-up human message, 20s later.
        user_text_line(21, "actually also do X"),
    ]
    segments, _, _ = _profile(tmp_path, lines)
    seg = segments[0]
    assert seg["human_s"] == 20.0
    _assert_main_thread_sums_to_wall(seg)


def test_ismeta_user_line_does_not_count_as_human(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_text_line(1, "working"),
        user_text_line(21, "some harness-injected caveat text", is_meta=True),
    ]
    segments, _, _ = _profile(tmp_path, lines)
    seg = segments[0]
    assert seg["human_s"] == 0.0


# ---------------------------------------------------------------------------
# Multi-command segmentation
# ---------------------------------------------------------------------------


def test_multi_command_segmentation_pre63_post63_fallback_and_preamble(tmp_path):
    lines = [
        # (preamble) -- no marker yet.
        user_text_line(0, "hey, quick question"),
        assistant_text_line(1, "sure"),
        # pre-63 bare marker starts a "plan" segment.
        user_text_line(10, command_marker_text("/plan")),
        assistant_tooluse_line(11, "toolu_p1", "Bash", command="plan_helper preflight"),
        user_toolresult_line(12, "toolu_p1"),
        # post-63 namespaced marker starts a "breakdown" segment.
        user_text_line(20, command_marker_text("/devforge:breakdown")),
        assistant_tooluse_line(21, "toolu_b1", "Bash", command="breakdown_helper preflight"),
        user_toolresult_line(22, "toolu_b1"),
        # No marker at all -- a MODEL-invoked command detected purely via
        # the helper fallback signal.  Starts a fresh "verify" segment.
        assistant_tooluse_line(30, "toolu_v1", "Bash", command="verify_helper preflight"),
        user_toolresult_line(31, "toolu_v1"),
        # A second helper call for the SAME command must NOT fragment into
        # another new segment (still verify).
        assistant_tooluse_line(32, "toolu_v2", "Bash", command="verify_helper check-hygiene"),
        user_toolresult_line(33, "toolu_v2"),
    ]
    segments, n_skipped, _ = _profile(tmp_path, lines)
    assert n_skipped == 0
    commands = [s["command"] for s in segments]
    assert commands == ["(preamble)", "plan", "breakdown", "verify"]

    verify_seg = segments[-1]
    assert verify_seg["n_helpers"] == 2  # both verify_helper calls counted once
    for seg in segments:
        _assert_main_thread_sums_to_wall(seg)


def test_clear_marker_resets_to_preamble(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_tooluse_line(1, "toolu_p1", "Bash", command="plan_helper preflight"),
        user_toolresult_line(2, "toolu_p1"),
        user_text_line(10, command_marker_text("/clear")),
        assistant_text_line(11, "fresh context"),
    ]
    segments, _, _ = _profile(tmp_path, lines)
    commands = [s["command"] for s in segments]
    assert commands == ["plan", "(preamble)"]


def test_repeated_marker_forms_separate_segments(tmp_path):
    # Re-invoking the same command later produces a SEPARATE row, not a
    # merge into the earlier segment of the same name.
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_text_line(1, "first plan run"),
        user_text_line(10, command_marker_text("/plan")),
        assistant_text_line(11, "second plan run"),
    ]
    segments, _, _ = _profile(tmp_path, lines)
    commands = [s["command"] for s in segments]
    assert commands == ["plan", "plan"]
    assert len(segments) == 2


# ---------------------------------------------------------------------------
# Unmatched tool_use guard
# ---------------------------------------------------------------------------


def test_unmatched_tool_use_counted_and_contributes_zero(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_tooluse_line(1, "toolu_orphan", "Bash", command="plan_helper preflight"),
        # No matching tool_result -- simulates a crash/abandon.
    ]
    segments, _, _ = _profile(tmp_path, lines)
    seg = segments[0]
    assert seg["n_unmatched_tools"] == 1
    assert seg["bash_s"] == 0.0


# ---------------------------------------------------------------------------
# compute_totals
# ---------------------------------------------------------------------------


def test_compute_totals_sums_all_segments(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_tooluse_line(1, "toolu_p1", "Bash", command="plan_helper preflight"),
        user_toolresult_line(3, "toolu_p1"),
        user_text_line(10, command_marker_text("/breakdown")),
        assistant_tooluse_line(11, "toolu_b1", "Bash", command="breakdown_helper preflight"),
        user_toolresult_line(14, "toolu_b1"),
    ]
    segments, _, _ = _profile(tmp_path, lines)
    totals = compute_totals(segments)
    assert totals["bash_s"] == 2.0 + 3.0
    assert totals["n_helpers"] == 2
    assert totals["wall"] == sum(s["wall"] for s in segments)


def test_compute_totals_empty_segments():
    totals = compute_totals([])
    assert totals["wall"] == 0.0
    assert totals["n_turns"] == 0


# ---------------------------------------------------------------------------
# Finding 1 -- boundary-spanning interval split (no spill into the
# closed segment; the tail lands in the following segment(s))
# ---------------------------------------------------------------------------


def test_dispatch_result_after_marker_boundary_close_splits_across_segments(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_tooluse_line(0.2, "toolu_agent1", "Agent"),
        assistant_text_line(1.8, "still working on other things"),
        user_text_line(2, command_marker_text("/breakdown")),
        assistant_text_line(2.5, "starting breakdown"),
        # The agent's PARENT-side tool_result finally arrives well INSIDE the
        # "breakdown" segment's own window -- the interval [0.2, 10] spans
        # the marker boundary at t=2.
        user_toolresult_line(10, "toolu_agent1"),
    ]
    segments, n_skipped, _ = _profile(tmp_path, lines)
    assert n_skipped == 0
    commands = [s["command"] for s in segments]
    assert commands == ["plan", "breakdown"]

    plan_seg, breakdown_seg = segments
    assert abs(plan_seg["wall"] - 2.0) < 1e-6
    assert abs(breakdown_seg["wall"] - 8.0) < 1e-6

    # The interval is SPLIT, not dumped wholly into the closed "plan"
    # segment (the reviewer's repro: wall=2.0, bucket-sum=10.0).
    assert abs(plan_seg["task_s"] - 1.6) < 1e-6
    assert abs(breakdown_seg["task_s"] - 8.0) < 1e-6

    for seg in segments:
        _assert_main_thread_sums_to_wall(seg)


def test_dispatch_result_after_fallback_boundary_close_splits_across_segments(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_tooluse_line(0.2, "toolu_agent1", "Agent"),
        assistant_text_line(1.0, "thinking..."),
        # No marker at all -- a helper-fallback trigger closes "plan" and
        # opens "verify" at t=2.0.
        assistant_tooluse_line(2.0, "toolu_v1", "Bash", command="verify_helper preflight"),
        user_toolresult_line(2.5, "toolu_v1"),
        # The agent's parent tool_result arrives late, well inside "verify".
        user_toolresult_line(10, "toolu_agent1"),
    ]
    segments, n_skipped, _ = _profile(tmp_path, lines)
    assert n_skipped == 0
    commands = [s["command"] for s in segments]
    assert commands == ["plan", "verify"]

    plan_seg, verify_seg = segments
    # Both segments must have gotten a genuine, non-zero SHARE of the
    # spanning dispatch's interval -- proving the split actually happened,
    # not that one side silently swallowed everything.
    assert plan_seg["task_s"] > 0.0
    assert verify_seg["task_s"] > 0.0

    for seg in segments:
        _assert_main_thread_sums_to_wall(seg)


# ---------------------------------------------------------------------------
# Finding 2 -- concurrent windows are a UNION, not a sum; fixed priority
# ---------------------------------------------------------------------------


def test_parallel_bash_tool_use_overlap_is_union_not_sum(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_multi_tooluse_line(1, [
            ("toolu_a", "Bash", "plan_helper preflight"),
            ("toolu_b", "Bash", "plan_helper list-specs"),
        ]),
        user_toolresult_line(4, "toolu_a"),  # [1, 4] -> 3s
        user_toolresult_line(6, "toolu_b"),  # [1, 6] -> 5s, overlaps toolu_a entirely
    ]
    segments, _, _ = _profile(tmp_path, lines)
    seg = segments[0]
    # Union of [1,4] and [1,6] is [1,6] -> 5.0s, NOT the naive sum 3+5=8.0s.
    assert abs(seg["bash_s"] - 5.0) < 1e-6
    assert abs(seg["wall"] - 6.0) < 1e-6
    _assert_main_thread_sums_to_wall(seg)


def test_bash_and_askuserquestion_overlap_human_wins_priority(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_multi_tooluse_line(1, [
            ("toolu_bash", "Bash", "plan_helper preflight"),
            ("toolu_ask", "AskUserQuestion", None),
        ]),
        user_toolresult_line(5, "toolu_bash"),  # [1, 5] -> 4s
        user_toolresult_line(8, "toolu_ask"),   # [1, 8] -> 7s, overlaps bash entirely
    ]
    segments, _, _ = _profile(tmp_path, lines)
    seg = segments[0]
    assert abs(seg["human_s"] - 7.0) < 1e-6  # human wins the whole overlap
    assert seg["bash_s"] == 0.0              # entirely swallowed by higher priority
    _assert_main_thread_sums_to_wall(seg)


# ---------------------------------------------------------------------------
# Finding 3 -- durationMs overrides interval LENGTH
# ---------------------------------------------------------------------------


def test_duration_ms_overrides_interval_length_for_bash(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_tooluse_line(1, "toolu_1", "Bash", command="plan_helper preflight"),
        # tool_result carries durationMs=500ms even though the raw
        # timestamp gap is 10s -- the precise duration wins.
        user_toolresult_line(11, "toolu_1", duration_ms=500),
    ]
    segments, _, _ = _profile(tmp_path, lines)
    seg = segments[0]
    assert abs(seg["bash_s"] - 0.5) < 1e-6
    _assert_main_thread_sums_to_wall(seg)


def test_duration_ms_clamped_to_not_precede_tool_use_ts(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_tooluse_line(1, "toolu_1", "Bash", command="plan_helper preflight"),
        # durationMs (5000ms=5s) EXCEEDS the actual 2s gap -- clamp to
        # open_ts=1, giving [1,3]=2.0s, NOT a retroactive 5.0s.
        user_toolresult_line(3, "toolu_1", duration_ms=5000),
    ]
    segments, _, _ = _profile(tmp_path, lines)
    seg = segments[0]
    assert abs(seg["bash_s"] - 2.0) < 1e-6
    _assert_main_thread_sums_to_wall(seg)


# ---------------------------------------------------------------------------
# Finding 4 -- orphan tool_result guard
# ---------------------------------------------------------------------------


def test_orphan_tool_result_counted_and_contributes_no_bucket(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        # No matching open tool_use at all -- e.g. a truncated transcript
        # that starts mid-tool-call.
        user_toolresult_line(1, "toolu_ghost"),
    ]
    segments, _, _ = _profile(tmp_path, lines)
    seg = segments[0]
    assert seg["n_orphan_results"] == 1
    assert seg["bash_s"] == 0.0
    assert seg["task_s"] == 0.0
    assert seg["human_s"] == 0.0


def test_compute_totals_includes_n_orphan_results(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        user_toolresult_line(1, "toolu_ghost"),
    ]
    segments, _, _ = _profile(tmp_path, lines)
    totals = compute_totals(segments)
    assert totals["n_orphan_results"] == 1


# ---------------------------------------------------------------------------
# Finding 5 -- n_helpers uses word-boundary stem matching
# ---------------------------------------------------------------------------


def test_n_helpers_uses_word_boundary_not_loose_substring(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        # Contains the literal substring "_helper" but matches NO registered
        # command's helper stem -- must NOT count under the tightened rule.
        assistant_tooluse_line(1, "toolu_1", "Bash", command="./scripts/some_custom_helper_thing.sh --run"),
        user_toolresult_line(2, "toolu_1"),
    ]
    segments, _, _ = _profile(tmp_path, lines)
    seg = segments[0]
    assert seg["n_helpers"] == 0


def test_n_helpers_still_counts_real_stem_matches(tmp_path):
    lines = [
        user_text_line(0, command_marker_text("/plan")),
        assistant_tooluse_line(1, "toolu_1", "Bash", command="plan_helper preflight"),
        user_toolresult_line(2, "toolu_1"),
    ]
    segments, _, _ = _profile(tmp_path, lines)
    seg = segments[0]
    assert seg["n_helpers"] == 1


# ---------------------------------------------------------------------------
# Direct unit coverage: interval arithmetic primitives
# ---------------------------------------------------------------------------


def test_merge_intervals_overlapping():
    assert _merge_intervals([(1, 5), (3, 8)]) == [(1, 8)]


def test_merge_intervals_touching_endpoints_merge():
    assert _merge_intervals([(0, 5), (5, 10)]) == [(0, 10)]


def test_merge_intervals_disjoint_stay_separate():
    assert _merge_intervals([(0, 1), (5, 6)]) == [(0, 1), (5, 6)]


def test_merge_intervals_unsorted_input():
    assert _merge_intervals([(5, 6), (0, 1), (2, 4)]) == [(0, 1), (2, 4), (5, 6)]


def test_merge_intervals_empty():
    assert _merge_intervals([]) == []


def test_interval_length_sums_disjoint():
    assert _interval_length([(0, 2), (5, 8)]) == 5


def test_interval_length_empty():
    assert _interval_length([]) == 0


def test_clip_intervals_partial_overlap():
    assert _clip_intervals([(1, 10)], (0, 5)) == [(1, 5)]


def test_clip_intervals_fully_outside_dropped():
    assert _clip_intervals([(10, 20)], (0, 5)) == []


def test_clip_intervals_fully_inside_unchanged():
    assert _clip_intervals([(2, 3)], (0, 5)) == [(2, 3)]


def test_clip_intervals_touching_edge_dropped_as_empty():
    # Clipping [5, 10] to window (0, 5) yields (5, 5) -- zero length, dropped.
    assert _clip_intervals([(5, 10)], (0, 5)) == []


def test_subtract_intervals_full_removal():
    assert _subtract_intervals([(1, 5)], [(0, 10)]) == []


def test_subtract_intervals_partial_removal_punches_hole():
    assert _subtract_intervals([(0, 10)], [(3, 5)]) == [(0, 3), (5, 10)]


def test_subtract_intervals_no_overlap_returns_original():
    assert _subtract_intervals([(0, 2)], [(5, 8)]) == [(0, 2)]


def test_subtract_intervals_empty_b_returns_a():
    assert _subtract_intervals([(0, 2)], []) == [(0, 2)]


def test_subtract_intervals_empty_a_returns_empty():
    assert _subtract_intervals([], [(0, 2)]) == []


def test_resolve_interval_no_duration_uses_timestamp_diff():
    open_entry = {"ts": 1.0, "duration_ms": None}
    start, end = _resolve_interval(open_entry, {"duration_ms": None}, 5.0)
    assert (start, end) == (1.0, 5.0)


def test_resolve_interval_duration_ms_on_tool_result_wins():
    open_entry = {"ts": 1.0, "duration_ms": None}
    start, end = _resolve_interval(open_entry, {"duration_ms": 500}, 11.0)
    assert end == 11.0
    assert abs(start - 10.5) < 1e-9


def test_resolve_interval_duration_ms_on_tool_use_used_when_result_absent():
    open_entry = {"ts": 1.0, "duration_ms": 500}
    start, end = _resolve_interval(open_entry, {"duration_ms": None}, 11.0)
    assert end == 11.0
    assert abs(start - 10.5) < 1e-9


def test_resolve_interval_duration_ms_clamped_to_open_ts():
    open_entry = {"ts": 1.0, "duration_ms": None}
    start, end = _resolve_interval(open_entry, {"duration_ms": 5000}, 3.0)
    assert (start, end) == (1.0, 3.0)


def test_segment_index_for_ts_basic():
    shells = [
        {"start_ts": 0.0}, {"start_ts": 10.0}, {"start_ts": 20.0},
    ]
    assert _segment_index_for_ts(shells, 0.0) == 0
    assert _segment_index_for_ts(shells, 5.0) == 0
    assert _segment_index_for_ts(shells, 10.0) == 1
    assert _segment_index_for_ts(shells, 25.0) == 2
