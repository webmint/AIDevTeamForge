"""_bucket.py -- command segmentation + wall-clock bucket profiling.

`profile_events` is the core entry point.  It runs in three passes over a
chronological event stream (as produced by `_parse.parse_transcript_file` /
`parse_transcript_chain`):

  Pass 1 (`_segment_windows`) -- walk the stream once to determine per-command
    SEGMENT WINDOWS: `{command, session_id, start_ts, end_ts}`.  This is pure
    boundary detection (markers + the helper-fallback signal); it does NOT
    touch tool_use/tool_result pairing or bucket math at all.

  Pass 2 -- walk the stream again to (a) count per-segment `n_turns` /
    `n_helpers` / `n_agents` / `n_unmatched_tools` / `n_orphan_results` and
    `agent_busy_s` (all POINT-IN-TIME classifications -- each belongs to
    whichever segment window contains the classifying event's own
    timestamp, via `_segment_index_for_ts`), and (b) collect GLOBAL
    (session-wide, not yet segment-attributed) lists of resolved [start,
    end] intervals for the three interval-bearing kinds: bash, task
    (Agent/Task dispatch), and human (both a genuine human-text gap and an
    AskUserQuestion tool_use->tool_result span).

  Pass 3 -- for EACH segment window, independently CLIP every global
    interval of every kind against that segment's own [start_ts, end_ts]
    (`_clip_intervals`).  A tool interval that spans a segment boundary
    (Finding 1: a tool_use still open when a boundary fires) is thereby
    SPLIT -- each segment gets only its own in-window portion, and no
    portion is ever counted twice.  Two-or-more tool intervals that overlap
    IN REAL TIME (Finding 2: parallel tool_use blocks in one assistant
    turn) are combined via INTERVAL UNION (`_merge_intervals`), not naive
    summation, so concurrent windows are counted once.

Bucket-priority partition (the disjointness invariant): within one
segment, the three interval-bearing buckets must never overlap EACH
OTHER -- every covered instant is attributed to exactly one bucket, by the
FIXED PRIORITY order `_BUCKET_PRIORITY = ("human", "task", "bash")`.
Human wins any overlap because an AskUserQuestion (or a genuine human
reply) means the main thread is truly idle -- the human's wall-clock, not
tool wall-clock.  Task outranks bash next (a dispatch is a
coarser-grained, usually-longer-running unit than an individual Bash
call).  The partition is computed by walking `_BUCKET_PRIORITY` in order
and, for each kind, subtracting the UNION of every higher-priority kind's
already-claimed time before measuring that kind's own length -- so
`human_s` = length of the human interval union; `task_s` = length of
(task union MINUS human union); `bash_s` = length of (bash union MINUS
(human union UNION task union)).  `llm_s` is a TRUE RESIDUAL: `wall -
length(union of ALL THREE raw interval sets)`, floored at 0.  Because
every raw interval was clipped to [start_ts, end_ts] before any of this
arithmetic, the covered union can never exceed `wall`, so `llm_s +
bash_s + task_s + human_s == wall` holds EXACTLY (not just
approximately) for every segment -- this is what makes Finding 1/2's
"boundary + overlap can break the invariant" class of bug structurally
impossible rather than patched around.

Segment dict shape (one per row in the eventual report):

    {
        "command":            str,    # command name, or "(preamble)"
        "session_id":          str,
        "start_ts":            float, # epoch seconds
        "last_ts":             float, # epoch seconds (segment's end_ts)
        "wall":                float, # seconds; last_ts - start_ts
        "llm_s":               float, # residual: wall - covered-union, floored 0
        "bash_s":              float, # union of Bash intervals, minus human/task priority
        "task_s":              float, # union of Agent/Task PARENT-side dispatch intervals, minus human priority
        "human_s":             float, # union of genuine-human-gap + AskUserQuestion intervals
        "agent_busy_s":        float, # non-summing: child-transcript span (or parent gap fallback)
        "n_turns":             int,   # assistant lines in this segment
        "n_helpers":           int,   # Bash tool_use calls matching a known command's helper stem
        "n_agents":            int,   # Agent/Task tool_use dispatches
        "n_unmatched_tools":   int,   # tool_use with no matching tool_result (crash/abandon)
        "n_orphan_results":    int,   # tool_result with no matching open tool_use (truncated transcript)
    }

Segment-boundary attribution (the "who owns the inter-command gap" design
call): a command-marker `user` line (or `/clear`) closes the segment
window that was open BEFORE it (that segment's `end_ts` becomes exactly
this marker's timestamp) and opens a brand-new window starting AT that
same timestamp.  Because segment windows are therefore CONTIGUOUS at a
marker boundary, a genuine-human-gap interval ending at the marker's own
timestamp clips ENTIRELY into the closing (old) segment when intersected
against its window, and clips to a zero-length (empty, dropped) interval
against the new segment's window -- the old segment gets full credit for
the "human was thinking about what to run next" gap, the new segment gets
none, with NO special-casing required: this falls straight out of the
generic clip-per-segment machinery in Pass 3.  A helper-fallback-triggered
switch (Finding-1-adjacent case: no preceding human text) has no such gap
to attribute; it simply closes the old segment at its own last-observed
event and opens the new one at the triggering event's timestamp -- any
real elapsed time between those two instants is untracked by design (not
credited to either segment; documented, not a bug).

durationMs interaction (Finding 3): OQ1's per-event `durationMs`, when
present (checked on the tool_result first, then the tool_use, matching
the OQ1 priority), OVERRIDES the interval LENGTH: the interval's END is
always the tool_result event's own timestamp; its START becomes
`result_ts - duration_s`, CLAMPED to never precede the tool_use's own
timestamp (a precise-but-implausibly-large durationMs cannot retroactively
claim time before the tool was even dispatched).  Absent durationMs, the
interval is the plain timestamp-diff gap `[tool_use.ts, tool_result.ts]`.
See `_resolve_interval`.

Overlap semantics for `agent_busy_s` (D4/OQ2 in the plan, UNCHANGED by
this design): it is a SEPARATE, non-summing, non-interval-clipped column
-- the dispatched agent's own child-transcript span when found, else the
same parent-side interval length as a fallback -- attributed to whichever
segment was active when the dispatch's tool_use was REGISTERED (a
point-in-time classification, exactly like `n_agents`).  It is reported
for visibility but deliberately excluded from the wall-sum invariant,
because an async agent's child span can overlap the parent thread's own
subsequent `llm_s` (the main thread keeps working while the agent runs in
the background) -- it never participates in the priority partition above.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ._agents import resolve_agent_span
from ._segment import match_helper_fallback

_DISPATCH_TOOL_NAMES = ("Agent", "Task")

# Fixed bucket priority for overlap resolution (highest first).  See module
# docstring "Bucket-priority partition" for the rationale.
_BUCKET_PRIORITY = ("human", "task", "bash")


# ---------------------------------------------------------------------------
# Interval arithmetic (pure, stdlib-only; no I/O)
# ---------------------------------------------------------------------------


def _merge_intervals(intervals):
    # type: (List[Tuple[float, float]]) -> List[Tuple[float, float]]
    """Sort + merge overlapping/touching intervals into a disjoint, ordered list.

    An interval with end <= start (zero/negative length) is dropped by the
    caller (`_clip_intervals`) before it ever reaches this function.
    """
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged = [list(ordered[0])]
    for start, end in ordered[1:]:
        if start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1][1] = end
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]


def _interval_length(intervals):
    # type: (List[Tuple[float, float]]) -> float
    """Sum of (end - start) across a list of intervals (disjoint or not)."""
    return sum(e - s for s, e in intervals)


def _clip_intervals(intervals, window):
    # type: (List[Tuple[float, float]], Tuple[float, float]) -> List[Tuple[float, float]]
    """Clip every interval to `window`, dropping any that end up empty.

    This is the operation that SPLITS a boundary-spanning interval: called
    once per segment window, an interval that spans multiple windows
    contributes only its own in-window portion to each one (Finding 1's fix).
    """
    win_start, win_end = window
    clipped = []
    for start, end in intervals:
        cs = max(start, win_start)
        ce = min(end, win_end)
        if ce > cs:
            clipped.append((cs, ce))
    return clipped


def _subtract_intervals(a_intervals, b_intervals):
    # type: (List[Tuple[float, float]], List[Tuple[float, float]]) -> List[Tuple[float, float]]
    """Return the portions of `a_intervals` not covered by `b_intervals`.

    Both inputs MUST already be merged (disjoint, sorted ascending) -- the
    early-break optimization below assumes `b_intervals` is sorted.  This
    is the mechanism that enforces the fixed bucket priority: a
    lower-priority bucket's raw interval union has the higher-priority
    bucket(s)' union subtracted out before its own length is measured.
    """
    if not b_intervals:
        return list(a_intervals)
    result = []
    for a_s, a_e in a_intervals:
        cur = a_s
        for b_s, b_e in b_intervals:
            if b_e <= cur:
                continue
            if b_s >= a_e:
                break
            if b_s > cur:
                result.append((cur, min(b_s, a_e)))
            cur = max(cur, b_e)
            if cur >= a_e:
                break
        if cur < a_e:
            result.append((cur, a_e))
    return result


# ---------------------------------------------------------------------------
# Pass 1: segmentation (boundary detection only -- no bucket math)
# ---------------------------------------------------------------------------


def _segment_windows(events):
    # type: (List[Dict]) -> List[Dict]
    """Walk the event stream once and return segment window shells:
    `[{command, session_id, start_ts, end_ts}, ...]` in chronological order.

    Boundary rules (unchanged from the original single-pass design):
      - a command-marker `user` line closes the currently-open window
        (its end_ts becomes this marker's own ts) and opens a new one
        starting at that same ts; "clear" opens a "(preamble)" window.
      - a Bash tool_use whose command matches a known helper stem NOT
        already the active command closes the currently-open window at
        its own last-observed event ts and opens a new one starting at
        the triggering event's own ts (see module docstring for the
        untracked-gap note).
    """
    shells = []  # type: List[Dict]
    current = None  # type: Optional[Dict]

    for ev in events:
        is_marker = ev["type"] == "user" and ev["command_marker"] is not None

        if is_marker:
            marker = ev["command_marker"]
            if current is not None:
                shells.append({
                    "command": current["command"],
                    "session_id": current["session_id"],
                    "start_ts": current["start_ts"],
                    "end_ts": ev["ts"],
                })
            new_name = "(preamble)" if marker == "clear" else marker
            current = {
                "command": new_name,
                "session_id": ev["session_id"],
                "start_ts": ev["ts"],
                "last_ts": ev["ts"],
            }
            continue

        if current is None:
            current = {
                "command": "(preamble)",
                "session_id": ev["session_id"],
                "start_ts": ev["ts"],
                "last_ts": ev["ts"],
            }

        if ev["type"] == "assistant":
            fallback_cmd = None
            for tu in ev["tool_uses"]:
                if tu["name"] == "Bash" and tu["command"]:
                    cand = match_helper_fallback(tu["command"])
                    if cand and current["command"] != cand:
                        fallback_cmd = cand
                        break
            if fallback_cmd is not None:
                shells.append({
                    "command": current["command"],
                    "session_id": current["session_id"],
                    "start_ts": current["start_ts"],
                    "end_ts": current["last_ts"],
                })
                current = {
                    "command": fallback_cmd,
                    "session_id": ev["session_id"],
                    "start_ts": ev["ts"],
                    "last_ts": ev["ts"],
                }

        current["last_ts"] = ev["ts"]

    if current is not None:
        shells.append({
            "command": current["command"],
            "session_id": current["session_id"],
            "start_ts": current["start_ts"],
            "end_ts": current["last_ts"],
        })

    return shells


def _segment_index_for_ts(shells, ts):
    # type: (List[Dict], float) -> int
    """Return the index of the shell active at `ts`: the LAST shell whose
    start_ts <= ts (shells are chronologically ordered by construction).
    Falls back to 0 for a ts before the first shell's start (should not
    happen for any event actually inside the profiled stream).
    """
    best = 0
    for i, sh in enumerate(shells):
        if sh["start_ts"] <= ts:
            best = i
        else:
            break
    return best


# ---------------------------------------------------------------------------
# Per-tool interval resolution (Finding 3: durationMs interaction)
# ---------------------------------------------------------------------------


def _resolve_interval(open_entry, tool_result, result_ts):
    # type: (Dict, Dict, float) -> Tuple[float, float]
    """Return the (start, end) interval attributed to one resolved tool call.

    `end` is always the tool_result event's own timestamp.  `start` is
    `result_ts - duration_s` when a durationMs is present on either side of
    the pair (tool_result checked first, then the tool_use -- OQ1's
    honored-when-present priority), CLAMPED to never precede the tool_use's
    own timestamp; otherwise `start` is the tool_use's own timestamp (the
    plain timestamp-diff gap).
    """
    dur_ms = tool_result.get("duration_ms")
    if dur_ms is None:
        dur_ms = open_entry.get("duration_ms")
    open_ts = open_entry["ts"]
    if dur_ms is not None:
        try:
            duration_s = max(0.0, float(dur_ms) / 1000.0)
        except (TypeError, ValueError):
            return open_ts, result_ts
        return max(open_ts, result_ts - duration_s), result_ts
    return open_ts, result_ts


# ---------------------------------------------------------------------------
# Passes 2+3: counts, interval collection, per-segment partition
# ---------------------------------------------------------------------------


def profile_events(events):
    # type: (List[Dict]) -> List[Dict]
    """Segment + bucket-profile a chronological event stream.

    Returns the list of segment dicts (see module docstring for shape),
    in chronological order.  Callers compute session totals separately
    via `compute_totals`.
    """
    shells = _segment_windows(events)
    if not shells:
        return []

    n_shells = len(shells)
    n_turns = [0] * n_shells
    n_helpers = [0] * n_shells
    n_agents = [0] * n_shells
    n_unmatched_tools = [0] * n_shells
    n_orphan_results = [0] * n_shells
    agent_busy_s = [0.0] * n_shells

    bash_intervals = []  # type: List[Tuple[float, float]]
    task_intervals = []  # type: List[Tuple[float, float]]
    human_intervals = []  # type: List[Tuple[float, float]]

    open_tool_uses = {}  # type: Dict[str, Dict]
    prev_ts = None  # type: Optional[float]

    for ev in events:
        if ev["type"] == "user":
            if ev["text"] is not None and not ev["is_meta"] and prev_ts is not None:
                gap_start, gap_end = prev_ts, ev["ts"]
                if gap_end > gap_start:
                    human_intervals.append((gap_start, gap_end))

            for tr in ev["tool_results"]:
                tu_id = tr.get("tool_use_id")
                open_entry = open_tool_uses.pop(tu_id, None) if tu_id else None
                if open_entry is None:
                    seg_idx = _segment_index_for_ts(shells, ev["ts"])
                    n_orphan_results[seg_idx] += 1
                    continue

                start, end = _resolve_interval(open_entry, tr, ev["ts"])
                name = open_entry["name"]
                if name == "Bash":
                    bash_intervals.append((start, end))
                elif name in _DISPATCH_TOOL_NAMES:
                    task_intervals.append((start, end))
                    busy, found = resolve_agent_span(open_entry["source_path"], tu_id)
                    agent_busy_s[open_entry["seg_idx"]] += busy if found else (end - start)
                elif name == "AskUserQuestion":
                    human_intervals.append((start, end))
                # Any other tool name: no interval collected -- its time is
                # part of the residual llm_s via the covered-union subtraction.

        elif ev["type"] == "assistant":
            seg_idx = _segment_index_for_ts(shells, ev["ts"])
            n_turns[seg_idx] += 1
            for tu in ev["tool_uses"]:
                name = tu["name"]
                if name == "Bash" and tu["command"] and match_helper_fallback(tu["command"]):
                    n_helpers[seg_idx] += 1
                elif name in _DISPATCH_TOOL_NAMES:
                    n_agents[seg_idx] += 1
                tu_id = tu.get("id")
                if tu_id:
                    open_tool_uses[tu_id] = {
                        "name": name,
                        "ts": ev["ts"],
                        "source_path": ev["source_path"],
                        "duration_ms": tu.get("duration_ms"),
                        "seg_idx": seg_idx,
                    }

        prev_ts = ev["ts"]

    for entry in open_tool_uses.values():
        n_unmatched_tools[entry["seg_idx"]] += 1

    kind_globals = {"human": human_intervals, "task": task_intervals, "bash": bash_intervals}
    bucket_key_for_kind = {"human": "human_s", "task": "task_s", "bash": "bash_s"}

    segments = []
    for i, sh in enumerate(shells):
        wall = max(0.0, sh["end_ts"] - sh["start_ts"])
        window = (sh["start_ts"], sh["end_ts"])

        clipped_by_kind = {
            kind: _clip_intervals(kind_globals[kind], window) for kind in _BUCKET_PRIORITY
        }

        # Walk the fixed priority order (human > task > bash), subtracting
        # everything already claimed by a higher-priority kind so the three
        # buckets end up a disjoint partition of the covered timeline.
        bucket_seconds = {}  # type: Dict[str, float]
        higher_union = []  # type: List[Tuple[float, float]]
        for kind in _BUCKET_PRIORITY:
            own_union = _subtract_intervals(_merge_intervals(clipped_by_kind[kind]), higher_union)
            bucket_seconds[bucket_key_for_kind[kind]] = _interval_length(own_union)
            higher_union = _merge_intervals(higher_union + own_union)

        all_raw = []  # type: List[Tuple[float, float]]
        for kind in _BUCKET_PRIORITY:
            all_raw.extend(clipped_by_kind[kind])
        covered_len = _interval_length(_merge_intervals(all_raw))
        llm_s = max(0.0, wall - covered_len)

        segments.append({
            "command": sh["command"],
            "session_id": sh["session_id"],
            "start_ts": sh["start_ts"],
            "last_ts": sh["end_ts"],
            "wall": wall,
            "llm_s": llm_s,
            "bash_s": bucket_seconds["bash_s"],
            "task_s": bucket_seconds["task_s"],
            "human_s": bucket_seconds["human_s"],
            "agent_busy_s": agent_busy_s[i],
            "n_turns": n_turns[i],
            "n_helpers": n_helpers[i],
            "n_agents": n_agents[i],
            "n_unmatched_tools": n_unmatched_tools[i],
            "n_orphan_results": n_orphan_results[i],
        })

    return segments


_TOTAL_FLOAT_KEYS = ("wall", "llm_s", "bash_s", "task_s", "human_s", "agent_busy_s")
_TOTAL_INT_KEYS = (
    "n_turns", "n_helpers", "n_agents", "n_unmatched_tools", "n_orphan_results",
)


def compute_totals(segments):
    # type: (List[Dict]) -> Dict
    """Sum every segment's buckets into one session-totals dict."""
    totals = {}  # type: Dict
    for key in _TOTAL_FLOAT_KEYS:
        totals[key] = 0.0
    for key in _TOTAL_INT_KEYS:
        totals[key] = 0
    for seg in segments:
        for key in _TOTAL_FLOAT_KEYS:
            totals[key] += seg[key]
        for key in _TOTAL_INT_KEYS:
            totals[key] += seg[key]
    return totals
