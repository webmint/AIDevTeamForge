#!/usr/bin/env python3
"""Pre-wave check: is a worktree free of a previous runner's leftovers before the next runner starts there?

A runner may leave work behind: edits of a nested agent that is still writing, a task started and not committed, the
crash marker `.claude/wip.md`. The next runner's squash would fold such leftovers into another task's commit. The
conductor (`/conduct` → "Pre-Wave Check") runs this check before it launches a writing runner into a worktree that a previous runner used.

Usage:
  python3 scripts/forge/wave-preflight.py <worktree> [<expected-head>] [--stale-minutes N] [--allow-untracked PATH]...

It checks tree state only, and reports one line per problem:
  - tracked changes (staged or not), or untracked files that .gitignore does not cover, in the whole worktree;
    `--allow-untracked PATH` (repeatable; a file or a directory, relative to the checked repository) excuses
    untracked paths only, never a tracked change;
  - the crash marker `.claude/wip.md`;
  - a git operation in progress (merge, rebase, cherry-pick, revert) or a stale `index.lock`;
  - HEAD that is not the commit the previous runner reported (`<expected-head>`: a full or abbreviated hash, or any
    revision the worktree can resolve).
Wrapper mode: when `.claude/project-config.json` sets `SOURCE_ROOT` and that directory is a separate git repository,
its tree is checked the same way (state, in-progress operations; the expected head applies to the worktree only).
Advisory only: it also lists `sleep` processes and `until`/`while ... sleep` shell loops older than `--stale-minutes`
(default 15) whose working directory is inside the worktree, as `warning: stale wait: pid <pid> age <age> cwd <dir>:
<command>`. It cannot tell an orphan from the bounded wait of a runner that is still alive, so it warns, never changes
the exit code, and never kills anything. When `ps` is unavailable the check is skipped with one line saying so.
It cannot see agent state: a nested agent that is still running but has not touched the tree leaves a clean tree.

Prints `ok`, or one line per problem. Exit codes: 0 ok; 1 problems; 2 bad usage, not a git repository, or an unusable
revision.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_profile  # noqa: E402  (sibling module; path set above)

WIP_MARKER = os.path.join(".claude", "wip.md")
# `git rev-parse --git-path <name>` resolves each one for a linked worktree too.
IN_PROGRESS = (("MERGE_HEAD", "merge"), ("CHERRY_PICK_HEAD", "cherry-pick"), ("REVERT_HEAD", "revert"),
               ("rebase-merge", "rebase"), ("rebase-apply", "rebase"))
SHOWN = 8
STALE_MINUTES = 15
# A wait: the `sleep` program itself, a shell command line that runs `sleep <n>`, or an `until`/`while` loop around one.
WAIT_PATTERN = re.compile(r"(^|[\s;&|(/])sleep\s+[0-9]|\b(until|while)\b.*\bsleep\b")


def git(tree: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", tree, *args], capture_output=True, text=True, check=False)


def is_allowed(path: str, allowed: list) -> bool:
    return any(path == item or path.startswith(item + "/") for item in allowed)


def dirty_paths(tree: str, allowed: list) -> list:
    """Status lines for tracked changes and non-ignored untracked files; untracked paths in ``allowed`` are skipped."""
    result = git(tree, "status", "--porcelain", "--untracked-files=all")
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git status failed")
    lines = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"')
        if line.startswith("??") and is_allowed(path, allowed):
            continue
        if path == WIP_MARKER.replace(os.sep, "/"):
            continue  # reported on its own line
        lines.append(line)
    return lines


def operations_in_progress(tree: str) -> list:
    found: list = []
    for name, label in IN_PROGRESS:
        path = git(tree, "rev-parse", "--git-path", name).stdout.strip()
        if path and os.path.exists(path if os.path.isabs(path) else os.path.join(tree, path)):
            if label not in found:
                found.append(label)
    lock = git(tree, "rev-parse", "--git-path", "index.lock").stdout.strip()
    if lock and os.path.exists(lock if os.path.isabs(lock) else os.path.join(tree, lock)):
        found.append("index.lock (a git command is running or died)")
    return found


def parse_etime(text: str) -> int:
    """Seconds from a `ps` elapsed time, `[[dd-]hh:]mm:ss` (the form macOS and Linux both print); -1 when unparsable."""
    match = re.fullmatch(r"(?:(?:(\d+)-)?(\d+):)?(\d+):(\d+)", text.strip())
    if not match:
        return -1
    days, hours, minutes, seconds = (int(part or 0) for part in match.groups())
    return ((days * 24 + hours) * 60 + minutes) * 60 + seconds


def format_age(seconds: int) -> str:
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    if days:
        return f"{days}d {hours}h"
    return f"{hours}h {minutes}m" if hours else f"{minutes}m"


def ps_available() -> bool:
    try:
        return subprocess.run(["ps", "-axo", "pid="], capture_output=True, check=False).returncode == 0
    except OSError:
        return False


def list_processes() -> list:
    """(pid, age in seconds, command line) of every process, from `ps`; empty when `ps` is unusable."""
    try:
        result = subprocess.run(["ps", "-axo", "pid=,etime=,command="], capture_output=True, text=True, check=False)
    except OSError:
        return []
    if result.returncode != 0:
        return []
    processes: list = []
    for line in result.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and parts[0].isdigit():
            processes.append((int(parts[0]), parse_etime(parts[1]), parts[2]))
    return processes


def process_cwds(pids: list) -> dict:
    """The working directory of each pid, from one `lsof -a -d cwd -Fn -p ...` call (`p<pid>` then `n<path>` lines);
    a pid that has exited, or that lsof may not inspect, is simply missing."""
    if not pids:
        return {}
    try:
        result = subprocess.run(["lsof", "-a", "-d", "cwd", "-Fn", "-p", ",".join(str(pid) for pid in pids)],
                                capture_output=True, text=True, check=False)
    except OSError:
        return {}
    cwds: dict = {}
    current: object = None
    for line in result.stdout.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            current = int(line[1:])
        elif line.startswith("n") and current is not None:
            cwds[current] = line[1:]
    return cwds


def stale_waits(tree: str, stale_minutes: int = STALE_MINUTES) -> list:
    """One `stale wait: pid ...` line per wait process older than ``stale_minutes`` whose cwd is inside ``tree``."""
    root = os.path.realpath(tree)
    candidates = [(pid, age, command) for pid, age, command in list_processes()
                  if pid != os.getpid() and age >= stale_minutes * 60 and WAIT_PATTERN.search(command)]
    cwds = process_cwds([pid for pid, _, _ in candidates])
    lines: list = []
    for pid, age, command in candidates:
        cwd = os.path.realpath(cwds[pid]) if pid in cwds else ""
        if cwd == root or (cwd and cwd.startswith(root + os.sep)):
            lines.append(f"stale wait: pid {pid} age {format_age(age)} cwd {cwd}: {command[:120]}")
    return lines


def check_tree(tree: str, label: str, allowed: list) -> list:
    problems: list = []
    dirty = dirty_paths(tree, allowed)
    if dirty:
        problems.append(f"{label}tree not clean: {len(dirty)} path(s): "
                        + "; ".join(line.strip() for line in dirty[:SHOWN]) + ("; ..." if len(dirty) > SHOWN else ""))
    if os.path.exists(os.path.join(tree, WIP_MARKER)):
        problems.append(f"{label}{WIP_MARKER} exists: a task is between its checkpoint and its squash, "
                        "or a runner died")
    for op in operations_in_progress(tree):
        problems.append(f"{label}git operation in progress: {op}")
    return problems


def toplevel(tree: str) -> str:
    return os.path.realpath(git(tree, "rev-parse", "--show-toplevel").stdout.strip() or tree)


def check(tree: str, expected_head: "str | None", allowed: "list | None" = None) -> list:
    """The problems of ``tree`` (and of a separate source repository), one line each; raises RuntimeError when the tree
    or the revision is unusable."""
    allowed = [a.replace(os.sep, "/").strip("/") for a in (allowed or [])]
    if git(tree, "rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
        raise RuntimeError(f"{tree} is not a git worktree")
    problems = check_tree(tree, "", allowed)
    try:
        source = quality_profile.source_root(tree)
    except quality_profile.ProfileError as error:
        raise RuntimeError(str(error))
    if os.path.realpath(source) != os.path.realpath(tree) and toplevel(source) != toplevel(tree):
        if git(source, "rev-parse", "--is-inside-work-tree").stdout.strip() == "true":
            problems += check_tree(source, "source repo: ", allowed)
    if expected_head:
        want = git(tree, "rev-parse", "--verify", "--quiet", f"{expected_head}^{{commit}}")
        if want.returncode != 0:
            raise RuntimeError(f"expected head {expected_head} does not resolve to a commit in {tree}")
        head = git(tree, "rev-parse", "HEAD").stdout.strip()
        if want.stdout.strip() != head:
            problems.append(f"HEAD is {head[:12]}, the previous runner reported {want.stdout.strip()[:12]}")
    return problems


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description="Pre-wave tree check.")
    parser.add_argument("worktree", help="the worktree the next runner will use")
    parser.add_argument("expected_head", nargs="?", help="the commit the previous runner reported (optional)")
    parser.add_argument("--stale-minutes", type=int, default=STALE_MINUTES,
                        help=f"age from which a sleep or wait loop in the tree is reported (default {STALE_MINUTES})")
    parser.add_argument("--allow-untracked", action="append", default=[], metavar="PATH",
                        help="an untracked file or directory that is not a problem (repeatable)")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_:
        return 2 if exit_.code else 0
    if not os.path.isdir(args.worktree):
        print(f"wave-preflight: {args.worktree} is not a directory", file=sys.stderr)
        return 2
    try:
        problems = check(args.worktree, args.expected_head, args.allow_untracked)
    except RuntimeError as error:
        print(f"wave-preflight: {error}", file=sys.stderr)
        return 2
    # Advisory: printed, never part of the exit code, never acted on.
    if ps_available():
        warnings = [f"warning: {line}" for line in stale_waits(args.worktree, args.stale_minutes)]
    else:
        warnings = ["warning: ps is unavailable; the stale wait check was skipped"]
    if warnings:
        print("\n".join(warnings))
    if problems:
        print("\n".join(problems))
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
