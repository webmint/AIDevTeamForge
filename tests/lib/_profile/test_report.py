"""Tests for src/devforge/lib/_profile/_report.py.

Coverage:
  format_duration            -- seconds / minutes / hours formatting, zero,
                                 negative clamped to zero.
  _largest_main_thread_bucket -- picks the dominant bucket, excludes
                                 agent_busy_s, deterministic tie-break,
                                 empty totals.
  render_table                -- contains every segment + TOTAL row +
                                 largest-bucket line + skipped-lines line.
  render_aggregate_table      -- per-command rows + tally rendering +
                                 empty-aggregate rendering.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _profile._report import (  # noqa: E402
    _largest_main_thread_bucket,
    format_duration,
    render_aggregate_table,
    render_table,
)


# ---------------------------------------------------------------------------
# format_duration
# ---------------------------------------------------------------------------


def test_format_duration_seconds_only():
    assert format_duration(5) == "5s"


def test_format_duration_minutes_and_seconds():
    assert format_duration(65) == "1m 5s"


def test_format_duration_hours_minutes_seconds():
    assert format_duration(3723) == "1h 2m 3s"


def test_format_duration_zero():
    assert format_duration(0) == "0s"


def test_format_duration_negative_clamped_to_zero():
    assert format_duration(-5) == "0s"


def test_format_duration_rounds():
    assert format_duration(59.6) == "1m 0s"


# ---------------------------------------------------------------------------
# _largest_main_thread_bucket
# ---------------------------------------------------------------------------


def test_largest_bucket_picks_dominant():
    totals = {"llm_s": 10.0, "bash_s": 100.0, "task_s": 5.0, "human_s": 1.0, "agent_busy_s": 999.0}
    key, val = _largest_main_thread_bucket(totals)
    assert key == "bash_s"
    assert val == 100.0


def test_largest_bucket_excludes_agent_busy_s():
    # agent_busy_s dwarfs everything but must never be picked.
    totals = {"llm_s": 1.0, "bash_s": 1.0, "task_s": 1.0, "human_s": 1.0, "agent_busy_s": 5000.0}
    key, _ = _largest_main_thread_bucket(totals)
    assert key != "agent_busy_s"


def test_largest_bucket_tie_break_deterministic():
    totals = {"llm_s": 5.0, "bash_s": 5.0, "task_s": 5.0, "human_s": 5.0}
    key, _ = _largest_main_thread_bucket(totals)
    assert key == "llm_s"


def test_largest_bucket_empty_totals():
    key, val = _largest_main_thread_bucket({})
    assert key is None
    assert val == 0.0


# ---------------------------------------------------------------------------
# render_table
# ---------------------------------------------------------------------------


def _sample_segment(command="plan"):
    return {
        "command": command,
        "wall": 10.0,
        "llm_s": 5.0,
        "bash_s": 3.0,
        "task_s": 1.0,
        "human_s": 1.0,
        "agent_busy_s": 0.0,
        "n_turns": 2,
        "n_helpers": 1,
        "n_agents": 0,
    }


def test_render_table_contains_segment_and_total_rows():
    seg = _sample_segment()
    totals = {
        "wall": 10.0, "llm_s": 5.0, "bash_s": 3.0, "task_s": 1.0, "human_s": 1.0,
        "agent_busy_s": 0.0, "n_turns": 2, "n_helpers": 1, "n_agents": 0,
    }
    table = render_table([seg], totals, n_lines_skipped=0)
    assert "plan" in table
    assert "TOTAL" in table
    assert "Largest main-thread bucket: llm_s" in table
    assert "Lines skipped during parse (unparseable or non-event types): 0" in table


def test_render_table_reports_skipped_count():
    seg = _sample_segment()
    totals = dict(seg)
    del totals["command"]
    table = render_table([seg], totals, n_lines_skipped=7)
    assert "Lines skipped during parse (unparseable or non-event types): 7" in table


def test_render_table_empty_segments():
    totals = {
        "wall": 0.0, "llm_s": 0.0, "bash_s": 0.0, "task_s": 0.0, "human_s": 0.0,
        "agent_busy_s": 0.0, "n_turns": 0, "n_helpers": 0, "n_agents": 0,
    }
    table = render_table([], totals, n_lines_skipped=0)
    assert "TOTAL" in table


# ---------------------------------------------------------------------------
# render_aggregate_table
# ---------------------------------------------------------------------------


def test_render_aggregate_table_with_data():
    agg = {
        "n_runs": 3,
        "per_command": {
            "plan": {
                "wall": {"median": 60.0, "max": 120.0},
                "llm_s": {"median": 30.0, "max": 60.0},
                "bash_s": {"median": 5.0, "max": 10.0},
                "task_s": {"median": 0.0, "max": 0.0},
                "human_s": {"median": 25.0, "max": 50.0},
                "agent_busy_s": {"median": 0.0, "max": 0.0},
            },
        },
        "largest_bucket_tally": {"human_s": 2, "llm_s": 1},
    }
    table = render_aggregate_table(agg)
    assert "Aggregated across 3 stored run(s)" in table
    assert "plan" in table
    assert "human_s: 2" in table
    assert "llm_s: 1" in table


def test_render_aggregate_table_empty():
    agg = {"n_runs": 0, "per_command": {}, "largest_bucket_tally": {}}
    table = render_aggregate_table(agg)
    assert "Aggregated across 0 stored run(s)" in table
    assert "(no per-command data)" in table
    assert "(no runs)" in table
