"""_parse.py -- tolerant transcript JSONL parsing for profile_helper.

Reads a Claude Code session transcript (one JSON object per line) and
normalizes each usable line into a flat event dict.  The transcript format
is internal to the harness and version-unstable (see
70-PIPELINE-WALLCLOCK-PROFILING-PLAN.md Empirical Grounding + Phase 0
RESULTS) -- this parser never raises on a malformed line; it skips and
counts it instead.

Normalized event shape (one dict per usable line):

    {
        "type":           "user" | "assistant" | "system",
        "ts":              float,       # epoch seconds (UTC)
        "is_meta":         bool,
        "session_id":      str,
        "version":         str,         # harness version, "" if absent
        "source_path":     str,         # transcript file this line came from
        "command_marker":  Optional[str],  # lowercased name, "user" lines only
        "text":            Optional[str],  # plain-string user content
        "tool_results":    List[Dict],  # "user" lines: [{tool_use_id, duration_ms}]
        "tool_uses":       List[Dict],  # "assistant" lines: [{id, name, command, duration_ms}]
        "turn_duration_ms": Optional[int],  # "system" lines, subtype turn_duration
        "message_count":   Optional[int],   # "system" lines, subtype turn_duration
    }

Only "user" / "assistant" / "system" lines are usable -- every other line
`type` (mode, attachment, file-history-snapshot, last-prompt, ai-title,
queue-operation, pr-link, permission-mode, or any future/unknown value) is
skipped and counted, matching the Empirical Grounding's documented type
list plus a version-unstable-format tolerance margin.  A line that fails
JSON parsing, is not a JSON object, or carries no parseable `timestamp` is
also skipped and counted -- it cannot be placed on the timeline.

n_lines_skipped is reported once per parsed file/chain (a session-level
diagnostic), NOT per command segment: a skipped line has no usable
timestamp/type, so there is no principled way to attribute it to any one
segment.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import datetime
import json
import os
from typing import Dict, List, Optional, Tuple

from ._segment import match_command_marker

# ---------------------------------------------------------------------------
# Timestamp parsing
# ---------------------------------------------------------------------------

# Harness timestamps are ISO8601 with a trailing "Z" and millisecond
# precision, e.g. "2026-08-05T10:00:00.000Z".  We deliberately do NOT rely
# on datetime.fromisoformat (its fractional-second handling differs across
# 3.8-3.10 vs 3.11+) -- a manual strptime keeps this portable across the
# whole 3.8+ target.


def _parse_ts(raw):
    # type: (Optional[str]) -> Optional[float]
    """Parse an ISO8601 'Z'-suffixed timestamp into epoch seconds (UTC).

    Returns None on any malformed/absent input -- callers treat that as
    "cannot place this line on the timeline" and skip it.
    """
    if not raw or not isinstance(raw, str):
        return None
    s = raw[:-1] if raw.endswith("Z") else raw
    try:
        if "." in s:
            date_part, frac = s.split(".", 1)
            frac_digits = "".join(ch for ch in frac if ch.isdigit())
            if not frac_digits:
                return None
            frac_digits = (frac_digits + "000000")[:6]
            dt = datetime.datetime.strptime(
                date_part + "." + frac_digits, "%Y-%m-%dT%H:%M:%S.%f"
            )
        else:
            dt = datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None
    dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.timestamp()


# ---------------------------------------------------------------------------
# Line normalization
# ---------------------------------------------------------------------------

_USABLE_TYPES = ("user", "assistant", "system")


def _normalize_line(obj, line_type, source_path, session_id_fallback):
    # type: (Dict, str, str, str) -> Optional[Dict]
    """Normalize one parsed JSON line into an event dict, or None to skip."""
    ts = _parse_ts(obj.get("timestamp"))
    if ts is None:
        return None

    event = {
        "type": line_type,
        "ts": ts,
        "is_meta": bool(obj.get("isMeta")),
        "session_id": obj.get("sessionId") or session_id_fallback,
        "version": obj.get("version") or "",
        "source_path": source_path,
        "command_marker": None,
        "text": None,
        "tool_results": [],
        "tool_uses": [],
        "turn_duration_ms": None,
        "message_count": None,
    }  # type: Dict

    if line_type == "system":
        if obj.get("subtype") == "turn_duration":
            event["turn_duration_ms"] = obj.get("durationMs")
            event["message_count"] = obj.get("messageCount")
        return event

    message = obj.get("message")
    if not isinstance(message, dict):
        return event
    content = message.get("content")

    if line_type == "user":
        if isinstance(content, str):
            event["text"] = content
            event["command_marker"] = match_command_marker(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    event["tool_results"].append({
                        "tool_use_id": block.get("tool_use_id"),
                        "duration_ms": block.get("durationMs"),
                    })
        return event

    # line_type == "assistant"
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            input_obj = block.get("input")
            command = None
            if isinstance(input_obj, dict):
                cmd_val = input_obj.get("command")
                if isinstance(cmd_val, str):
                    command = cmd_val
            event["tool_uses"].append({
                "id": block.get("id"),
                "name": block.get("name"),
                "command": command,
                "duration_ms": block.get("durationMs"),
            })
    return event


# ---------------------------------------------------------------------------
# File-level parsing
# ---------------------------------------------------------------------------


def parse_transcript_file(path):
    # type: (str) -> Tuple[List[Dict], int]
    """Parse one transcript .jsonl file into (events, n_skipped).

    Never raises.  A missing/unreadable file returns ([], 0).
    """
    events = []  # type: List[Dict]
    n_skipped = 0

    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw_lines = fh.readlines()
    except OSError:
        return events, n_skipped

    session_id_fallback = os.path.splitext(os.path.basename(path))[0]

    for raw_line in raw_lines:
        stripped = raw_line.strip()
        if not stripped:
            continue
        try:
            obj = json.loads(stripped)
        except (ValueError, TypeError):
            n_skipped += 1
            continue
        if not isinstance(obj, dict):
            n_skipped += 1
            continue

        line_type = obj.get("type")
        if line_type not in _USABLE_TYPES:
            n_skipped += 1
            continue

        event = _normalize_line(obj, line_type, path, session_id_fallback)
        if event is None:
            n_skipped += 1
            continue
        events.append(event)

    return events, n_skipped


def parse_transcript_chain(paths):
    # type: (List[str]) -> Tuple[List[Dict], int]
    """Parse + concatenate multiple transcript files into one event stream.

    Callers pass paths pre-ordered by mtime (see _locate.list_transcripts_by_mtime);
    this function defensively re-sorts the merged event list by timestamp so
    out-of-order files never corrupt segmentation.
    """
    all_events = []  # type: List[Dict]
    total_skipped = 0
    for path in paths:
        events, skipped = parse_transcript_file(path)
        all_events.extend(events)
        total_skipped += skipped

    all_events.sort(key=lambda e: e["ts"])
    return all_events, total_skipped
