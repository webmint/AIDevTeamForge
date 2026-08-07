"""_agents.py -- subagent child-transcript span resolution for profile_helper.

An Agent/Task dispatch's PARENT-side tool_use -> tool_result gap is NOT a
reliable measure of the dispatched agent's actual runtime for an
asynchronous (background) dispatch -- the parent-side tool_result can
return seconds after launch while the agent keeps running in its own
transcript file (verified at plan 70 Phase 0 / OQ2).  The agent's real
span lives in a SEPARATE per-dispatch transcript file:

    <transcript-dir>/<session-uuid>/subagents/agent-<id>.jsonl
    <transcript-dir>/<session-uuid>/subagents/agent-<id>.meta.json

`meta.json` carries `{"agentType", "description", "toolUseId", "spawnDepth"}`;
`toolUseId` is the join key back to the parent transcript's dispatching
tool_use block id.

Both are resolved RELATIVE TO EACH TRANSCRIPT'S OWN LOCATION (not a single
global subagents dir) -- this matters for `--dir`-stitched chains where
different segments may come from different session files.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import json
import os
from typing import Optional, Tuple

from ._parse import parse_transcript_file


def _subagents_dir(transcript_path):
    # type: (str) -> str
    transcript_dir = os.path.dirname(transcript_path)
    session_uuid = os.path.splitext(os.path.basename(transcript_path))[0]
    return os.path.join(transcript_dir, session_uuid, "subagents")


def _file_span(path):
    # type: (str) -> Optional[float]
    """Return (max_ts - min_ts) across all timestamped lines in `path`.

    Returns None when the file has zero usable (timestamped) lines --
    callers treat that as "child file present but empty/unusable", which
    falls back to the parent-side gap like a missing file would.
    """
    events, _n_skipped = parse_transcript_file(path)
    if not events:
        return None
    timestamps = [e["ts"] for e in events]
    return max(timestamps) - min(timestamps)


def resolve_agent_span(transcript_path, tool_use_id):
    # type: (str, str) -> Tuple[Optional[float], bool]
    """Resolve the child subagent transcript span for one dispatch.

    Returns (span_seconds, found):
      found=True   -> a matching meta.json + a non-empty agent transcript
                       were located; span_seconds is the child file's
                       first-to-last event span.
      found=False  -> no subagents dir, no matching meta.json, or the
                       matched agent transcript had no usable events;
                       span_seconds is None.  Callers fall back to the
                       parent-side gap in this case.
    """
    subagents_dir = _subagents_dir(transcript_path)
    if not os.path.isdir(subagents_dir):
        return None, False

    try:
        entries = os.listdir(subagents_dir)
    except OSError:
        return None, False

    for name in entries:
        if not name.endswith(".meta.json"):
            continue
        meta_path = os.path.join(subagents_dir, name)
        try:
            with open(meta_path, "r", encoding="utf-8") as fh:
                meta = json.load(fh)
        except (OSError, ValueError):
            continue
        if not isinstance(meta, dict) or meta.get("toolUseId") != tool_use_id:
            continue

        agent_filename = name[: -len(".meta.json")] + ".jsonl"
        agent_path = os.path.join(subagents_dir, agent_filename)
        span = _file_span(agent_path)
        if span is None:
            return None, False
        return span, True

    return None, False
