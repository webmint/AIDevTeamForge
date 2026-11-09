#!/usr/bin/env python3
"""Pending nested work of a runner: which agents and background shells it launched have no final completion
notification yet?

The conductor runs it on a runner that returned, before it starts the next phase in that tree (`/conduct` ->
"Pre-Wave Check"; it is also what `scripts/forge/wave-preflight.py --runner <id>` calls):
  python3 scripts/forge/nested-pending.py <agent-id|transcript-path> [--projects-dir DIR] [--no-recursive]

An agent id is resolved to its transcript, the newest `<projects-dir>/*/*/subagents/agent-<id>.jsonl` (default projects
dir `$CLAUDE_CONFIG_DIR/projects`, else `~/.claude/projects`). The transcript is replayed by the parser of
`.claude/hooks/forge/nested-wait-guard.py` (loaded by path, so there is one parser). By default the check is recursive
(depth limit 3): a nested agent can hand back while its own shell still runs, so the pending work inside every agent the
runner launched is reported too, marked `via <parent id>`.

Prints only ids, kinds, agent types, tool names and timestamps, never commands, descriptions or text (a transcript can
hold restricted material). Output: `ok: no pending nested work (<n> launched)` and exit 0; one `pending: ...` line per
item and exit 1; an unresolvable id or an unreadable file: a message on stderr and exit 2.

A launched agent whose own transcript cannot be found is not inspected: it prints one
`unchecked: agent <id> (no transcript found)` line, and that line never changes the exit code (the agent itself is
still judged by the runner's own transcript). Known false positive: an agent stopped with TaskStop may still show the
shells it had started as pending, because its transcript holds no notification for them; the conductor checks that
the shell is really gone before it waits.

Python 3.9+, standard library only.
"""
from __future__ import annotations

import argparse
import glob
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOOK_RELATIVE = os.path.join(".claude", "hooks", "forge", "nested-wait-guard.py")
MAX_DEPTH = 3


class Unresolvable(Exception):
    """The target is not a readable transcript and not the id of a known subagent transcript."""


def hook_path() -> str:
    """The guard next to this script (`<project>/scripts/forge/` -> `<project>/.claude/hooks/forge/`), else the one
    under $CLAUDE_PROJECT_DIR."""
    local = os.path.join(os.path.dirname(os.path.dirname(HERE)), HOOK_RELATIVE)
    project = os.environ.get("CLAUDE_PROJECT_DIR")
    if not os.path.isfile(local) and project:
        return os.path.join(project, HOOK_RELATIVE)
    return local


def _load_hook():
    """The nested-wait-guard module, loaded by path (its file name is not importable)."""
    path = hook_path()
    spec = importlib.util.spec_from_file_location("nested_wait_guard", path)
    if spec is None or spec.loader is None or not os.path.isfile(path):
        raise Unresolvable(f"cannot load the parser at {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def default_projects_dir() -> str:
    """`$CLAUDE_CONFIG_DIR/projects`, else `~/.claude/projects`."""
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    return os.path.join(base, "projects")


def find_agent_transcript(agent_id: str, projects_dir: str) -> str | None:
    """The newest transcript of the subagent ``agent_id`` under ``projects_dir``, or None."""
    pattern = os.path.join(projects_dir, "*", "*", "subagents", f"agent-{agent_id}.jsonl")
    matches = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    return matches[0] if matches else None


def resolve_target(target: str, projects_dir: str) -> tuple[str, str]:
    """(transcript path, label) of ``target``, a transcript path or an agent id; raises Unresolvable."""
    if os.path.isfile(target):
        return target, os.path.basename(target)
    if os.sep in target or target.endswith(".jsonl"):
        raise Unresolvable(f"{target} is not a readable file")
    path = find_agent_transcript(target, projects_dir)
    if not path:
        raise Unresolvable(f"no transcript for agent {target} under {projects_dir}")
    return path, target


def _walk(hook, path: str, label: str, projects_dir: str, recursive: bool, depth: int, seen: set[str],
          parent: str | None) -> tuple[list[str], int, list[str]]:
    """(pending lines, launched count, unchecked lines) of the transcript at ``path``, recursing into the agents it
    launched."""
    try:
        records = hook.load_records(path)
    except OSError as error:
        raise Unresolvable(f"cannot read {path}: {error.__class__.__name__}") from error
    result = hook.scan(records)
    suffix = f" via {parent}" if parent else ""
    lines = [f"pending: {hook.describe(item)}{suffix}" for item in result.pending]
    unchecked: list[str] = []
    if recursive and depth < MAX_DEPTH:
        for item in result.launched:
            if item.kind != "agent" or item.id in seen:
                continue
            seen.add(item.id)
            nested_path = find_agent_transcript(item.id, projects_dir)
            if not nested_path:
                unchecked.append(f"unchecked: agent {item.id} (no transcript found)")
                continue
            nested_lines, _, nested_unchecked = _walk(hook, nested_path, item.id, projects_dir, recursive, depth + 1,
                                                      seen, item.id if parent is None else f"{parent} > {item.id}")
            lines.extend(nested_lines)
            unchecked.extend(nested_unchecked)
    return lines, len(result.launched), unchecked


def inspect(target: str, projects_dir: str | None = None,
            recursive: bool = True) -> tuple[list[str], int, list[str]]:
    """(pending lines, count launched by the target itself, unchecked lines); raises Unresolvable. Lines hold ids,
    kinds, types and timestamps only."""
    projects = projects_dir or default_projects_dir()
    path, label = resolve_target(target, projects)
    return _walk(_load_hook(), path, label, projects, recursive, 0, {label}, None)


def pending_for(target: str, projects_dir: str | None = None, recursive: bool = True) -> list[str]:
    """One `pending: ...` line per unfinished launch of the runner ``target`` (agent id or transcript path), plus the
    unfinished launches inside the agents it launched when ``recursive``; raises Unresolvable."""
    return inspect(target, projects_dir, recursive)[0]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Pending nested work of a runner.")
    parser.add_argument("target", help="the runner's agent id or the path of its transcript")
    parser.add_argument("--projects-dir", help="where agent transcripts live (default $CLAUDE_CONFIG_DIR/projects, "
                                               "else ~/.claude/projects)")
    parser.add_argument("--no-recursive", action="store_true", help="do not inspect the agents the runner launched")
    args = parser.parse_args(argv)
    try:
        lines, launched, unchecked = inspect(args.target, args.projects_dir, not args.no_recursive)
    except Unresolvable as error:
        print(f"nested-pending: {error}", file=sys.stderr)
        return 2
    if unchecked:
        print("\n".join(unchecked))
    if lines:
        print("\n".join(lines))
        return 1
    print(f"ok: no pending nested work ({launched} launched)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
