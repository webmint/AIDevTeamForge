"""_storage.py -- per-run + rolling storage for profile_helper (D5).

Each `profile_helper run` invocation writes:
  <workspace_root>/.devforge/profile/<session>-<YYYYMMDDTHHMMSS>.json
      -- the raw per-segment + totals bucket split (schema-versioned).
  <workspace_root>/.devforge/profile/summary.md
      -- a rolling, human-readable run-by-run log (created if absent,
         appended to otherwise).

The filename timestamp comes from the LAST EVENT in the profiled data
(not the current clock), so re-running the profiler over the exact same
input is idempotent -- it always resolves to the same JSON filename and
simply overwrites it with the same content.

`.devforge/profile/` is EPHEMERAL-class storage per plan 49's disposition
model -- gitignored via `src/files/devforge.gitignore` (Phase 1b wiring,
not part of this module).

`aggregate_runs` reads every stored per-run JSON back and rolls them up
into the cross-run verdict shape `_report.render_aggregate_table` prints
(OQ5).

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import datetime
import glob
import json
import os
import statistics
from typing import Dict, List

from ._report import _largest_main_thread_bucket, format_duration

_SCHEMA_VERSION = 1

_BUCKET_KEYS = ("wall", "llm_s", "bash_s", "task_s", "human_s", "agent_busy_s")

_SUMMARY_HEADER = (
    "# Profile Run Summary\n\n"
    "Appended by `profile_helper run` on every invocation (newest run at "
    "the bottom).  See plan 70 (PIPELINE-WALLCLOCK-PROFILING-PLAN.md) for "
    "the bucket definitions.\n\n"
)


def _profile_dir(workspace_root):
    # type: (str) -> str
    return os.path.join(workspace_root, ".devforge", "profile")


def build_run_record(session_id, harness_version, source_paths, segments, totals, n_lines_skipped):
    # type: (str, str, List[str], List[Dict], Dict, int) -> Dict
    """Assemble the JSON-serializable per-run record."""
    return {
        "schema_version": _SCHEMA_VERSION,
        "session_id": session_id,
        "harness_version": harness_version,
        "source_paths": list(source_paths),
        "n_lines_skipped": n_lines_skipped,
        "segments": segments,
        "totals": totals,
    }


def _filename_timestamp(last_event_ts):
    # type: (float) -> str
    dt = datetime.datetime.fromtimestamp(last_event_ts, tz=datetime.timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%S")


def write_run(workspace_root, session_id, last_event_ts, run_record):
    # type: (str, str, float, Dict) -> str
    """Write the per-run JSON report.  Returns the path written."""
    profile_dir = _profile_dir(workspace_root)
    os.makedirs(profile_dir, exist_ok=True)

    safe_session = (session_id or "unknown").replace("/", "_").replace(os.sep, "_")
    stamp = _filename_timestamp(last_event_ts)
    filename = "{0}-{1}.json".format(safe_session, stamp)
    path = os.path.join(profile_dir, filename)

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(run_record, fh, indent=2, sort_keys=True)
        fh.write("\n")

    return path


def render_summary_block(run_record):
    # type: (Dict) -> str
    """Render one run's rolling-summary.md entry."""
    totals = run_record.get("totals", {})
    largest_key, largest_val = _largest_main_thread_bucket(totals)

    lines = ["## {0}".format(run_record.get("session_id", "unknown")), ""]
    lines.append("- Source: {0}".format(", ".join(run_record.get("source_paths", []))))
    if largest_key is not None:
        lines.append(
            "- Largest bucket: {0} ({1})".format(largest_key, format_duration(largest_val))
        )
    lines.append("- Wall total: {0}".format(format_duration(totals.get("wall", 0.0))))
    lines.append("")
    lines.append("| Command | Wall | LLM | Bash | Task | Human | Agent busy |")
    lines.append("|---|---|---|---|---|---|---|")
    for seg in run_record.get("segments", []):
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} | {5} | {6} |".format(
                seg["command"],
                format_duration(seg["wall"]),
                format_duration(seg["llm_s"]),
                format_duration(seg["bash_s"]),
                format_duration(seg["task_s"]),
                format_duration(seg["human_s"]),
                format_duration(seg["agent_busy_s"]),
            )
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def append_summary(workspace_root, run_record):
    # type: (str, Dict) -> str
    """Append one run's block to the rolling summary.md (creating it with
    a header if absent).  Returns the summary.md path.
    """
    profile_dir = _profile_dir(workspace_root)
    os.makedirs(profile_dir, exist_ok=True)
    summary_path = os.path.join(profile_dir, "summary.md")

    if not os.path.isfile(summary_path):
        with open(summary_path, "w", encoding="utf-8") as fh:
            fh.write(_SUMMARY_HEADER)

    with open(summary_path, "a", encoding="utf-8") as fh:
        fh.write(render_summary_block(run_record))

    return summary_path


# ---------------------------------------------------------------------------
# Cross-run aggregation (OQ5)
# ---------------------------------------------------------------------------


def aggregate_runs(workspace_root):
    # type: (str) -> Dict
    """Read every stored per-run JSON and roll it up into the cross-run
    verdict shape `_report.render_aggregate_table` prints.

    Returns:
      {
        "n_runs": int,
        "per_command": {
            <command>: {
                <bucket_key>: {"median": float, "max": float}, ...
            }, ...
        },
        "largest_bucket_tally": {<bucket_key>: int, ...},
      }
    """
    profile_dir = _profile_dir(workspace_root)
    run_files = sorted(glob.glob(os.path.join(profile_dir, "*.json")))

    runs = []  # type: List[Dict]
    for rf in run_files:
        try:
            with open(rf, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and "segments" in data and "totals" in data:
            runs.append(data)

    by_command = {}  # type: Dict[str, Dict[str, List[float]]]
    largest_bucket_tally = {}  # type: Dict[str, int]

    for run in runs:
        largest_key, _val = _largest_main_thread_bucket(run.get("totals", {}))
        if largest_key is not None:
            largest_bucket_tally[largest_key] = largest_bucket_tally.get(largest_key, 0) + 1

        for seg in run.get("segments", []):
            cmd = seg.get("command", "")
            bucket = by_command.setdefault(cmd, {k: [] for k in _BUCKET_KEYS})
            for k in _BUCKET_KEYS:
                bucket[k].append(float(seg.get(k, 0.0)))

    per_command = {}  # type: Dict[str, Dict]
    for cmd, vals in by_command.items():
        per_command[cmd] = {}
        for k in _BUCKET_KEYS:
            samples = vals[k]
            per_command[cmd][k] = {
                "median": statistics.median(samples) if samples else 0.0,
                "max": max(samples) if samples else 0.0,
            }

    return {
        "n_runs": len(runs),
        "per_command": per_command,
        "largest_bucket_tally": largest_bucket_tally,
    }
