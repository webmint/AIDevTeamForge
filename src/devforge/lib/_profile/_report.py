"""_report.py -- plain-text report rendering for profile_helper.

Two renderers:
  render_table            -- per-run stdout table (one row per segment + TOTAL).
  render_aggregate_table   -- cross-run verdict table (see _storage.aggregate_runs).

`_largest_main_thread_bucket` picks the dominant one of the four
MAIN-THREAD buckets (llm_s / bash_s / task_s / human_s) -- `agent_busy_s`
is deliberately excluded since it is a non-summing, potentially-overlapping
column (see _bucket.py module docstring), not one of the four buckets that
sum to wall.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

_MAIN_THREAD_BUCKETS = ("llm_s", "bash_s", "task_s", "human_s")


def format_duration(seconds):
    # type: (float) -> str
    """Render a second count as a human-readable "1h 5m 3s" / "5m 3s" / "3s" string."""
    seconds = max(0.0, float(seconds))
    total = int(round(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return "{0}h {1}m {2}s".format(hours, minutes, secs)
    if minutes:
        return "{0}m {1}s".format(minutes, secs)
    return "{0}s".format(secs)


def _largest_main_thread_bucket(totals):
    # type: (Dict) -> Tuple[Optional[str], float]
    """Return (bucket_key, value) for the largest of llm_s/bash_s/task_s/human_s.

    Ties resolve to the first key in _MAIN_THREAD_BUCKETS order (llm_s wins
    a tie, then bash_s, then task_s, then human_s) -- a deterministic,
    documented tie-break rather than dict-iteration-order luck.
    Returns (None, 0.0) when totals carries none of the four keys.
    """
    best_key = None  # type: Optional[str]
    best_val = -1.0
    for key in _MAIN_THREAD_BUCKETS:
        if key not in totals:
            continue
        val = totals[key]
        if val > best_val:
            best_val = val
            best_key = key
    return best_key, (best_val if best_key is not None else 0.0)


def _pad_table(headers, rows):
    # type: (List[str], List[List[str]]) -> List[str]
    """Left-align every column to the widest cell (header or data) in it."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    lines = ["  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))]
    lines.append("  ".join("-" * w for w in widths))
    for row in rows:
        lines.append("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)))
    return lines


def _segment_row(seg):
    # type: (Dict) -> List[str]
    return [
        seg["command"],
        format_duration(seg["wall"]),
        format_duration(seg["llm_s"]),
        format_duration(seg["bash_s"]),
        format_duration(seg["task_s"]),
        format_duration(seg["human_s"]),
        format_duration(seg["agent_busy_s"]),
        str(seg["n_turns"]),
        str(seg["n_helpers"]),
        str(seg["n_agents"]),
    ]


def render_table(segments, totals, n_lines_skipped):
    # type: (List[Dict], Dict, int) -> str
    """Render the per-run stdout report: one row per segment + a TOTAL row
    + a trailing line flagging the largest main-thread bucket.
    """
    headers = [
        "Command", "Wall", "LLM", "Bash", "Task", "Human", "AgentBusy",
        "Turns", "Helpers", "Agents",
    ]
    rows = [_segment_row(seg) for seg in segments]
    total_row = _segment_row(dict(totals, command="TOTAL"))
    rows.append(total_row)

    lines = _pad_table(headers, rows)

    largest_key, largest_val = _largest_main_thread_bucket(totals)
    lines.append("")
    if largest_key is not None:
        lines.append(
            "Largest main-thread bucket: {0} ({1})".format(
                largest_key, format_duration(largest_val)
            )
        )
    lines.append(
        "Lines skipped during parse (unparseable or non-event types): {0}".format(
            n_lines_skipped
        )
    )

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Cross-run aggregate rendering
# ---------------------------------------------------------------------------

_AGGREGATE_BUCKET_KEYS = ("wall", "llm_s", "bash_s", "task_s", "human_s", "agent_busy_s")


def render_aggregate_table(agg):
    # type: (Dict) -> str
    """Render the `aggregate` subcommand's cross-run verdict table.

    `agg` is the dict produced by `_storage.aggregate_runs`.
    """
    lines = ["Aggregated across {0} stored run(s)".format(agg["n_runs"]), ""]

    headers = [
        "Command", "MedianWall", "MaxWall", "MedianLLM", "MedianBash",
        "MedianTask", "MedianHuman",
    ]
    rows = []
    for cmd in sorted(agg["per_command"].keys()):
        stats = agg["per_command"][cmd]
        rows.append([
            cmd,
            format_duration(stats["wall"]["median"]),
            format_duration(stats["wall"]["max"]),
            format_duration(stats["llm_s"]["median"]),
            format_duration(stats["bash_s"]["median"]),
            format_duration(stats["task_s"]["median"]),
            format_duration(stats["human_s"]["median"]),
        ])

    if rows:
        lines.extend(_pad_table(headers, rows))
    else:
        lines.append("(no per-command data)")

    lines.append("")
    lines.append("Largest-main-thread-bucket-per-run tally:")
    tally = agg.get("largest_bucket_tally", {})
    if tally:
        for key in sorted(tally.keys()):
            lines.append("  {0}: {1}".format(key, tally[key]))
    else:
        lines.append("  (no runs)")

    return "\n".join(lines) + "\n"
