#!/usr/bin/env python3
"""Context guard (PostToolUse hook, Forge-owned).

Reads the hook payload from stdin, finds the latest main-session (non-sidechain)
assistant message in the transcript, and estimates the current context size from
its usage (input + cache creation + cache read + output tokens).

Thresholds, as a share of the context window:
- >= warn (default 75 %): tell Claude to wind down: finish the current task or
  command, start nothing new (see .claude/commands/_multi-task-continuation.md,
  "Context Health").
- >= stop (default 85 %): tell Claude to stop at the nearest safe point.

Configuration (environment, e.g. the "env" block of .claude/settings.json):
- FORGE_CONTEXT_WINDOW  context window in tokens (default 200000). When the
  measured context is already larger, a 1,000,000-token window is assumed.
- FORGE_CONTEXT_WARN / FORGE_CONTEXT_STOP  absolute token thresholds; they
  override the percentages.

Never fails the tool call: any error results in a silent exit 0.

Report mode:
    python3 .claude/hooks/forge/context-guard.py --report
prints the main-session context size of the newest transcript of this project
and exits 1 when no transcript or usage entry is found.
"""
import glob
import json
import os
import re
import sys
from typing import Optional, Tuple

TAIL_BYTES = 8 * 1024 * 1024
DEFAULT_WINDOW = 200_000
LARGE_WINDOW = 1_000_000
WARN_SHARE = 0.75
STOP_SHARE = 0.85


def _env_int(name: str) -> Optional[int]:
    value = os.environ.get(name, "").strip()
    return int(value) if value.isdigit() else None


def thresholds(tokens: int) -> Tuple[int, int]:
    """Return (warn, stop) token thresholds for the measured context size."""
    window = _env_int("FORGE_CONTEXT_WINDOW") or DEFAULT_WINDOW
    if tokens > window:
        window = max(window, LARGE_WINDOW)
    warn = _env_int("FORGE_CONTEXT_WARN") or int(window * WARN_SHARE)
    stop = _env_int("FORGE_CONTEXT_STOP") or int(window * STOP_SHARE)
    return warn, stop


def context_tokens(transcript_path: str) -> int:
    """Return the context size of the latest main-session assistant turn, or 0."""
    size = os.path.getsize(transcript_path)
    with open(transcript_path, "rb") as f:
        f.seek(max(0, size - TAIL_BYTES))
        lines = f.read().splitlines()
    for raw in reversed(lines):
        try:
            entry = json.loads(raw)
        except ValueError:
            continue
        message = entry.get("message")
        if entry.get("type") != "assistant" or entry.get("isSidechain") or not isinstance(message, dict):
            continue
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue
        keys = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")
        return sum(int(usage.get(k) or 0) for k in keys)
    return 0


def newest_transcript() -> Optional[str]:
    """Return the most recently modified main-session transcript of this project, or None.

    Transcripts live in <config dir>/projects/<project path with non-alphanumerics as '-'>/*.jsonl;
    subagent transcripts sit in per-session subdirectories, so a top-level glob sees main sessions only.
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    slug = re.sub(r"[^A-Za-z0-9]", "-", project_dir)
    files = glob.glob(os.path.join(config_dir, "projects", slug, "*.jsonl"))
    return max(files, key=os.path.getmtime) if files else None


def report() -> int:
    """Print the main-session context size of the newest transcript; return the exit code."""
    path = newest_transcript()
    if not path:
        print("context-guard: no transcript found for this project")
        return 1
    tokens = context_tokens(path)
    if not tokens:
        print("context-guard: no usage entry in %s" % os.path.basename(path))
        return 1
    warn, stop = thresholds(tokens)
    print("main-session context ~%dk tokens (%s) - transcript %s; warn %dk, stop %dk"
          % (round(tokens / 1000), format(tokens, ","), os.path.basename(path), warn // 1000, stop // 1000))
    return 0


def message_for(tokens: int) -> Optional[dict]:
    """Return the hook output for this context size, or None below the warn threshold."""
    warn, stop = thresholds(tokens)
    if tokens < warn:
        return None
    k = round(tokens / 1000)
    assumed = "" if _env_int("FORGE_CONTEXT_WINDOW") or _env_int("FORGE_CONTEXT_STOP") else (
        " (Window assumed 200k. If this session's window is larger, this threshold is too low: tell the user"
        " to set FORGE_CONTEXT_WINDOW in the env block of .claude/settings.json and ask whether to continue.)")
    if tokens >= stop:
        text = ("CONTEXT GUARD: main-session context ~%dk tokens (stop at %dk). "
                "STOP at the nearest safe point: finish only the current atomic step, leave the tree "
                "consistent (WIP commit or checkpoint), update .claude/session-state.md, then stop and "
                "tell the user to run /compact (or /clear) and resume. Do not start a new task or command. "
                "(Subagents: ignore this and finish your task.)" % (k, stop // 1000) + assumed)
        return {"systemMessage": "Context ~%dk tokens - stop requested (limit %dk)." % (k, stop // 1000),
                "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}
    text = ("CONTEXT GUARD: main-session context ~%dk tokens (stop at %dk). "
            "Wind down: finish the current task or command, do not start a new one, then follow "
            "\"Context Health\" in .claude/commands/_multi-task-continuation.md. (Subagents: ignore this.)"
            % (k, stop // 1000) + assumed)
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}


def main() -> None:
    payload = json.load(sys.stdin)
    path = payload.get("transcript_path")
    if not path or not os.path.isfile(path):
        return
    out = message_for(context_tokens(path))
    if out:
        print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    if "--report" in sys.argv[1:]:
        sys.exit(report())
    try:
        main()
    except Exception:  # noqa: BLE001 - a guard must never break tool calls; it simply stays silent
        sys.exit(0)
