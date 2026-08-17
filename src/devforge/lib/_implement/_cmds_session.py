"""_cmds_session -- update-session-state verb for implement_helper.

Fully overwrite .devforge/session-state.md after each approved task.

Algorithm (update-session-state)
---------------------------------
1. Parse --recent-tasks (JSON array of {number, title, status}), cap to last 3.
2. Parse --recent-decisions (JSON array of strings), cap to last 3.
3. Build the session-state.md content (always fully overwritten):
     # Session State — /devforge:implement
     **Feature**: <feature>
     **Progress**: <completed>/<total> tasks complete
     **Updated**: <UTC timestamp>

     ## Recent Task Modifications
     - [NNN] <title> (<status>)
     ...

     ## Recent Decisions
     - <decision>
     ...
   The file MUST be ≤ 40 lines (hard cap). Sliding windows (last 3 each)
   guarantee this: the fixed header is 6 lines, 2 section headings = 2 lines,
   3 task lines = 3 lines, 3 decision lines = 3 lines → max ~18 lines.
4. Atomically overwrite .devforge/session-state.md.

Arguments (argparse):
  --feature             <str>   Required. Current feature name/dir.
  --completed-count     <int>   Required. Tasks completed so far.
  --total-count         <int>   Required. Total tasks in the feature.
  --recent-tasks        <json>  Optional. JSON array of {number, title, status}.
                                Default: [].
  --recent-decisions    <json>  Optional. JSON array of decision strings.
                                Default: [].
  --root                <path>  Optional. Root dir. Default: cwd.
  --timestamp           <str>   Optional. Override UTC timestamp (for tests).

Emitted JSON (stdout, exit 0):
  {"updated": true}

Exit codes:
  0 — success.
  1 — I/O or parse error.

Design notes:
- session-state.md is ALWAYS fully overwritten (never appended). The sliding
  windows are enforced by slicing the inputs to at most 3 items each.
- The ≤40-line cap is enforced by counting lines before write and truncating
  the "Recent Decisions" window further if needed (in practice the hard-coded
  3-item cap already keeps the file under 40 lines).
- Atomic write for session-state.md (tempfile.mkstemp + os.replace).
- This command does not touch .devforge/memory.md. Prior to plan 79 Phase 2
  it also appended a per-task receipt line under memory.md's "## Task
  Outcomes" section; that write was removed because plan 79 Phase 1 excludes
  "## Task Outcomes" from every memory read, so the section was a write-only
  dead end. .devforge/session-state.md (this file) already tracks the last 3
  tasks.

Stdlib only. Python 3.8+.
"""

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_ERR = 1

# Sliding window size (max items each for tasks and decisions).
_WINDOW_SIZE = 3

# Hard line-count cap for session-state.md.
_MAX_LINES = 40


# ---------------------------------------------------------------------------
# Atomic write helpers
# ---------------------------------------------------------------------------


def _atomic_write(target_path, content):
    # type: (Path, str) -> None
    """Atomically overwrite target_path with content."""
    fd, tmp_path = tempfile.mkstemp(
        prefix="session-state-",
        suffix=".tmp",
        dir=str(target_path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(target_path))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Content builders
# ---------------------------------------------------------------------------


def _build_session_state(
    feature,           # type: str
    completed_count,   # type: int
    total_count,       # type: int
    recent_tasks,      # type: List[dict]
    recent_decisions,  # type: List[str]
    timestamp,         # type: str
):
    # type: (...) -> str
    """Build the session-state.md content string.

    Applies the sliding-window cap (last 3 items each). The result is
    guaranteed to be ≤ _MAX_LINES lines because:
    - Fixed header: 5 lines (heading + 3 fields + blank).
    - Task section heading + blank: 2 lines.
    - Up to 3 task lines.
    - Blank between sections: 1 line.
    - Decision section heading + blank: 2 lines.
    - Up to 3 decision lines.
    Total max: 5 + 2 + 3 + 1 + 2 + 3 = 16 lines — well under 40.
    """
    # Apply sliding windows.
    tasks = recent_tasks[-_WINDOW_SIZE:] if recent_tasks else []
    decisions = recent_decisions[-_WINDOW_SIZE:] if recent_decisions else []

    lines = []  # type: List[str]

    # Header.
    lines.append("# Session State — /devforge:implement")
    lines.append("")
    lines.append("**Feature**: {0}".format(feature))
    lines.append("**Progress**: {0}/{1} tasks complete".format(completed_count, total_count))
    lines.append("**Updated**: {0}".format(timestamp))
    lines.append("")

    # Recent task modifications.
    lines.append("## Recent Task Modifications")
    lines.append("")
    if tasks:
        for t in tasks:
            num = t.get("number", "?")
            title = t.get("title", "?")
            status = t.get("status", "?")
            lines.append("- [{0}] {1} ({2})".format(num, title, status))
    else:
        lines.append("- (none)")
    lines.append("")

    # Recent decisions.
    lines.append("## Recent Decisions")
    lines.append("")
    if decisions:
        for d in decisions:
            lines.append("- {0}".format(d))
    else:
        lines.append("- (none)")

    content = "\n".join(lines) + "\n"

    # Hard cap enforcement (defensive — the math above guarantees < 40 lines
    # for the specified inputs, but enforce it regardless).
    content_lines = content.splitlines(keepends=True)
    if len(content_lines) > _MAX_LINES:
        content = "".join(content_lines[:_MAX_LINES])

    return content


# ---------------------------------------------------------------------------
# argparse setup
# ---------------------------------------------------------------------------


def add_args_update_session_state(parser):
    # type: (object) -> None
    """Register update-session-state arguments on the given subparser."""
    parser.add_argument(
        "--feature",
        required=True,
        help="Current feature name or directory (e.g. '001-widget-catalog').",
    )
    parser.add_argument(
        "--completed-count",
        required=True,
        dest="completed_count",
        type=int,
        help="Number of tasks completed so far in this feature.",
    )
    parser.add_argument(
        "--total-count",
        required=True,
        dest="total_count",
        type=int,
        help="Total number of tasks in this feature.",
    )
    parser.add_argument(
        "--recent-tasks",
        default="[]",
        dest="recent_tasks",
        help=(
            "JSON array of recent task objects {number, title, status}. "
            "Only the last 3 are kept (sliding window). Default: []."
        ),
    )
    parser.add_argument(
        "--recent-decisions",
        default="[]",
        dest="recent_decisions",
        help=(
            "JSON array of decision strings. "
            "Only the last 3 are kept (sliding window). Default: []."
        ),
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Project root directory. Default: cwd.",
    )
    parser.add_argument(
        "--timestamp",
        default="",
        help=(
            "Override UTC timestamp string for the session-state header "
            "(for deterministic tests). If absent, current UTC time is used."
        ),
    )


# ---------------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------------


def cmd_update_session_state(args):
    # type: (object) -> int
    """Overwrite session-state.md.

    Parameters
    ----------
    args : argparse.Namespace

    Returns
    -------
    int
        0 on success; 1 on error.
    """
    root = Path(getattr(args, "root", ".")).resolve()
    devforge_dir = root / ".devforge"
    devforge_dir.mkdir(parents=True, exist_ok=True)

    feature = getattr(args, "feature", "").strip()
    if not feature:
        sys.stderr.write("update-session-state: --feature is required\n")
        return EXIT_ERR

    try:
        completed_count = int(getattr(args, "completed_count", 0))
    except (ValueError, TypeError):
        sys.stderr.write(
            "update-session-state: --completed-count must be an integer\n"
        )
        return EXIT_ERR

    try:
        total_count = int(getattr(args, "total_count", 0))
    except (ValueError, TypeError):
        sys.stderr.write(
            "update-session-state: --total-count must be an integer\n"
        )
        return EXIT_ERR

    # --- Parse --recent-tasks ---
    recent_tasks_json = getattr(args, "recent_tasks", "[]")
    try:
        recent_tasks = json.loads(recent_tasks_json)
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "update-session-state: --recent-tasks is not valid JSON: {0}\n".format(exc)
        )
        return EXIT_ERR
    if not isinstance(recent_tasks, list):
        sys.stderr.write(
            "update-session-state: --recent-tasks must be a JSON array\n"
        )
        return EXIT_ERR

    # --- Parse --recent-decisions ---
    recent_decisions_json = getattr(args, "recent_decisions", "[]")
    try:
        recent_decisions = json.loads(recent_decisions_json)
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "update-session-state: --recent-decisions is not valid JSON: {0}\n".format(exc)
        )
        return EXIT_ERR
    if not isinstance(recent_decisions, list):
        sys.stderr.write(
            "update-session-state: --recent-decisions must be a JSON array\n"
        )
        return EXIT_ERR

    # --- Timestamp ---
    timestamp = (getattr(args, "timestamp", "") or "").strip()
    if not timestamp:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # --- Build and write session-state.md ---
    session_state_path = devforge_dir / "session-state.md"
    content = _build_session_state(
        feature=feature,
        completed_count=completed_count,
        total_count=total_count,
        recent_tasks=recent_tasks,
        recent_decisions=recent_decisions,
        timestamp=timestamp,
    )

    try:
        _atomic_write(session_state_path, content)
    except OSError as exc:
        sys.stderr.write(
            "update-session-state: cannot write session-state.md: {0}\n".format(exc)
        )
        return EXIT_ERR

    sys.stdout.write(json.dumps({"updated": True}) + "\n")
    return EXIT_OK
