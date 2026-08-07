"""Tests for src/devforge/lib/_profile/_storage.py.

Coverage:
  build_run_record        -- assembles the JSON-serializable shape.
  write_run                -- filename derived from LAST-EVENT timestamp
                               (not wall clock) -> idempotent re-run
                               (same filename, overwritten); JSON round-trips.
  render_summary_block     -- contains session id + per-segment row.
  append_summary            -- creates summary.md with header when absent,
                               appends (does not overwrite) on a second call.
  aggregate_runs            -- median/max across N stored runs; largest-
                               bucket tally; ignores malformed/foreign JSON
                               files in the same dir; zero runs.

Uses tmp_path throughout; never touches a real project's .devforge/.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _profile._storage import (  # noqa: E402
    aggregate_runs,
    append_summary,
    build_run_record,
    write_run,
)


def _make_run_record(session_id="sess1", command="plan", wall=10.0, llm_s=5.0,
                      bash_s=3.0, task_s=1.0, human_s=1.0, agent_busy_s=0.0):
    segments = [{
        "command": command,
        "session_id": session_id,
        "start_ts": 1000.0,
        "last_ts": 1000.0 + wall,
        "wall": wall,
        "llm_s": llm_s,
        "bash_s": bash_s,
        "task_s": task_s,
        "human_s": human_s,
        "agent_busy_s": agent_busy_s,
        "n_turns": 2,
        "n_helpers": 1,
        "n_agents": 0,
        "n_unmatched_tools": 0,
    }]
    totals = dict(segments[0])
    totals.pop("command")
    totals.pop("session_id")
    totals.pop("start_ts")
    totals.pop("last_ts")
    return build_run_record(
        session_id=session_id,
        harness_version="2.1.195",
        source_paths=["/tmp/{0}.jsonl".format(session_id)],
        segments=segments,
        totals=totals,
        n_lines_skipped=0,
    )


# ---------------------------------------------------------------------------
# build_run_record
# ---------------------------------------------------------------------------


def test_build_run_record_shape():
    record = _make_run_record()
    assert record["schema_version"] == 1
    assert record["session_id"] == "sess1"
    assert record["harness_version"] == "2.1.195"
    assert record["n_lines_skipped"] == 0
    assert len(record["segments"]) == 1
    assert "wall" in record["totals"]


# ---------------------------------------------------------------------------
# write_run
# ---------------------------------------------------------------------------


def test_write_run_creates_json_file(tmp_path):
    record = _make_run_record()
    path = write_run(str(tmp_path), "sess1", 1234567890.0, record)
    assert os.path.isfile(path)
    with open(path, "r", encoding="utf-8") as fh:
        loaded = json.load(fh)
    assert loaded == record


def test_write_run_filename_uses_last_event_ts_not_wall_clock(tmp_path):
    import datetime

    record = _make_run_record()
    last_ts = datetime.datetime(2026, 8, 5, 12, 0, 0, tzinfo=datetime.timezone.utc).timestamp()
    path = write_run(str(tmp_path), "sess1", last_ts, record)
    assert "20260805T120000" in os.path.basename(path)


def test_write_run_idempotent_on_rerun(tmp_path):
    record = _make_run_record()
    path1 = write_run(str(tmp_path), "sess1", 1234567890.0, record)
    path2 = write_run(str(tmp_path), "sess1", 1234567890.0, record)
    assert path1 == path2
    # Only one file exists in the profile dir.
    profile_dir = os.path.dirname(path1)
    assert len([f for f in os.listdir(profile_dir) if f.endswith(".json")]) == 1


def test_write_run_creates_profile_dir(tmp_path):
    record = _make_run_record()
    path = write_run(str(tmp_path), "sess1", 1000.0, record)
    assert ".devforge" in path
    assert "profile" in path


# ---------------------------------------------------------------------------
# append_summary
# ---------------------------------------------------------------------------


def test_append_summary_creates_with_header(tmp_path):
    record = _make_run_record()
    summary_path = append_summary(str(tmp_path), record)
    text = Path(summary_path).read_text(encoding="utf-8")
    assert text.startswith("# Profile Run Summary")
    assert "sess1" in text
    assert "plan" in text


def test_append_summary_appends_not_overwrites(tmp_path):
    record1 = _make_run_record(session_id="sess1")
    record2 = _make_run_record(session_id="sess2")
    append_summary(str(tmp_path), record1)
    summary_path = append_summary(str(tmp_path), record2)
    text = Path(summary_path).read_text(encoding="utf-8")
    assert text.count("# Profile Run Summary") == 1
    assert "sess1" in text
    assert "sess2" in text


# ---------------------------------------------------------------------------
# aggregate_runs
# ---------------------------------------------------------------------------


def test_aggregate_runs_median_and_max(tmp_path):
    r1 = _make_run_record(session_id="run1", wall=10.0, llm_s=8.0, human_s=2.0)
    r2 = _make_run_record(session_id="run2", wall=20.0, llm_s=18.0, human_s=2.0)
    write_run(str(tmp_path), "run1", 1000.0, r1)
    write_run(str(tmp_path), "run2", 2000.0, r2)

    agg = aggregate_runs(str(tmp_path))
    assert agg["n_runs"] == 2
    plan_stats = agg["per_command"]["plan"]
    assert plan_stats["wall"]["median"] == 15.0
    assert plan_stats["wall"]["max"] == 20.0


def test_aggregate_runs_largest_bucket_tally(tmp_path):
    # run1's totals: llm_s dominant. run2's: human_s dominant (via bash_s=0
    # task_s=0 and human_s > llm_s).
    r1 = _make_run_record(session_id="run1", wall=10.0, llm_s=8.0, bash_s=0.0, task_s=0.0, human_s=2.0)
    r2 = _make_run_record(session_id="run2", wall=10.0, llm_s=1.0, bash_s=0.0, task_s=0.0, human_s=9.0)
    write_run(str(tmp_path), "run1", 1000.0, r1)
    write_run(str(tmp_path), "run2", 2000.0, r2)

    agg = aggregate_runs(str(tmp_path))
    assert agg["largest_bucket_tally"] == {"llm_s": 1, "human_s": 1}


def test_aggregate_runs_ignores_malformed_json(tmp_path):
    profile_dir = tmp_path / ".devforge" / "profile"
    profile_dir.mkdir(parents=True)
    (profile_dir / "broken.json").write_text("not valid json {{{")
    (profile_dir / "unrelated.json").write_text(json.dumps({"foo": "bar"}))

    r1 = _make_run_record(session_id="run1")
    write_run(str(tmp_path), "run1", 1000.0, r1)

    agg = aggregate_runs(str(tmp_path))
    assert agg["n_runs"] == 1


def test_aggregate_runs_zero_runs(tmp_path):
    agg = aggregate_runs(str(tmp_path))
    assert agg["n_runs"] == 0
    assert agg["per_command"] == {}
    assert agg["largest_bucket_tally"] == {}
