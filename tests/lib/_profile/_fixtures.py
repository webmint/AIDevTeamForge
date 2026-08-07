"""Shared hand-authored transcript-line builders for tests/lib/_profile/.

Not a test module itself (no test_* functions) -- pytest will not collect it.

No real "producer" for a Claude Code session transcript exists inside a test
sandbox (it is a live-harness artifact) -- the format IS empirically verified
against real transcripts (see 70-PIPELINE-WALLCLOCK-PROFILING-PLAN.md Phase 0
RESULTS), and these builders reproduce that verified shape field-for-field.
This is the documented exception to the repo's "round-trip via the real
producer" testing discipline: there is no producer command to shell out to.
"""

from __future__ import annotations

import datetime
import json
import os
from typing import Dict, List, Optional

_BASE = datetime.datetime(2026, 8, 5, 10, 0, 0, tzinfo=datetime.timezone.utc)


def iso_ts(offset_s):
    # type: (float) -> str
    """Return an ISO8601 'Z'-suffixed ms-precision timestamp offset_s seconds
    after a fixed base instant -- matches the harness's observed shape.
    """
    dt = _BASE + datetime.timedelta(seconds=offset_s)
    ms = int(round((offset_s - int(offset_s)) * 1000)) % 1000
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + "{0:03d}Z".format(ms)


def user_text_line(offset_s, text, session_id="sess1", is_meta=False, version="2.1.195"):
    # type: (float, str, str, bool, str) -> Dict
    return {
        "type": "user",
        "timestamp": iso_ts(offset_s),
        "sessionId": session_id,
        "version": version,
        "cwd": "/x",
        "gitBranch": "main",
        "isMeta": is_meta,
        "message": {"role": "user", "content": text},
    }


def user_toolresult_line(offset_s, tool_use_id, session_id="sess1", duration_ms=None, version="2.1.195"):
    # type: (float, str, str, Optional[int], str) -> Dict
    block = {"type": "tool_result", "tool_use_id": tool_use_id}
    if duration_ms is not None:
        block["durationMs"] = duration_ms
    return {
        "type": "user",
        "timestamp": iso_ts(offset_s),
        "sessionId": session_id,
        "version": version,
        "message": {"role": "user", "content": [block]},
    }


def assistant_tooluse_line(offset_s, tool_id, name, command=None, session_id="sess1",
                            duration_ms=None, version="2.1.195", extra_input=None):
    # type: (float, str, str, Optional[str], str, Optional[int], str, Optional[Dict]) -> Dict
    input_obj = dict(extra_input) if extra_input else {}
    if command is not None:
        input_obj["command"] = command
    block = {"type": "tool_use", "id": tool_id, "name": name, "input": input_obj}
    if duration_ms is not None:
        block["durationMs"] = duration_ms
    return {
        "type": "assistant",
        "timestamp": iso_ts(offset_s),
        "sessionId": session_id,
        "version": version,
        "message": {"role": "assistant", "content": [block]},
    }


def assistant_multi_tooluse_line(offset_s, tool_specs, session_id="sess1", version="2.1.195"):
    # type: (float, List[tuple], str, str) -> Dict
    """Build ONE assistant line carrying MULTIPLE tool_use blocks -- the
    routine parallel-dispatch shape (several tool calls in a single turn).

    `tool_specs` is a list of (tool_id, name, command_or_None) tuples; all
    blocks share this line's single timestamp, matching the real harness
    shape (tool_use blocks within one assistant message have no per-block
    timestamp of their own).
    """
    blocks = []
    for tool_id, name, command in tool_specs:
        input_obj = {}
        if command is not None:
            input_obj["command"] = command
        blocks.append({"type": "tool_use", "id": tool_id, "name": name, "input": input_obj})
    return {
        "type": "assistant",
        "timestamp": iso_ts(offset_s),
        "sessionId": session_id,
        "version": version,
        "message": {"role": "assistant", "content": blocks},
    }


def assistant_text_line(offset_s, text, session_id="sess1", version="2.1.195"):
    # type: (float, str, str, str) -> Dict
    return {
        "type": "assistant",
        "timestamp": iso_ts(offset_s),
        "sessionId": session_id,
        "version": version,
        "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
    }


def system_turn_duration_line(offset_s, duration_ms, message_count, session_id="sess1", version="2.1.195"):
    # type: (float, int, int, str, str) -> Dict
    return {
        "type": "system",
        "subtype": "turn_duration",
        "timestamp": iso_ts(offset_s),
        "sessionId": session_id,
        "version": version,
        "durationMs": duration_ms,
        "messageCount": message_count,
    }


def command_marker_text(name):
    # type: (str) -> str
    return "<command-name>{0}</command-name><command-message>{1}</command-message><command-args></command-args>".format(
        name, name.lstrip("/")
    )


def write_jsonl(path, lines):
    # type: (str, List) -> None
    """Write a mix of dict lines (JSON-serialized) and raw str lines verbatim."""
    with open(path, "w", encoding="utf-8") as fh:
        for line in lines:
            if isinstance(line, str):
                fh.write(line + "\n")
            else:
                fh.write(json.dumps(line) + "\n")


def write_subagent_file(transcripts_dir, session_id, agent_id, tool_use_id,
                         child_lines, agent_type="architect", description="work"):
    # type: (str, str, str, str, List[Dict], str, str) -> None
    """Write <transcripts_dir>/<session_id>/subagents/agent-<agent_id>.jsonl
    + the sibling .meta.json, matching the empirically-verified shape.
    """
    subagents_dir = os.path.join(transcripts_dir, session_id, "subagents")
    os.makedirs(subagents_dir, exist_ok=True)
    write_jsonl(os.path.join(subagents_dir, "agent-{0}.jsonl".format(agent_id)), child_lines)
    meta = {
        "agentType": agent_type,
        "description": description,
        "toolUseId": tool_use_id,
        "spawnDepth": 1,
    }
    with open(os.path.join(subagents_dir, "agent-{0}.meta.json".format(agent_id)), "w", encoding="utf-8") as fh:
        json.dump(meta, fh)
