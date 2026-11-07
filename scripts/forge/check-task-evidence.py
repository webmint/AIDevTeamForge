#!/usr/bin/env python3
"""Task completion evidence check: a task newly marked `Complete` has run evidence.

A task that a feature's task index (`specs/<feature>/tasks/README.md`, the Task Index table whose last column is the
status) newly marks `Complete` must have run evidence:
  - a filled "Completion Notes" section in its task file (`specs/<feature>/tasks/<NNN>-*.md`): at least one line that
    is not the template's placeholder text (a whole-line `[...]` placeholder, or a `**Field**:` line whose value is
    empty or still holds a `[...]` placeholder, as `/breakdown` writes it);
  - while the branch still holds its task commits (more than one non-merge commit since the merge base), a commit whose
    subject names the task: `Task N:` or `TN` (the `[WIP] Task N: <title> — complete` form of `/execute-task`).

Scope: only rows that turned `Complete` between the merge base of HEAD with the integration ref (`integrationRef` in
`.claude/quality-profile.json`, or `--base`) and the working tree. Historical features are never re-checked, and a task
index untouched by the branch is not read. After `/finalize` squashes the branch into one commit the subject no longer
names a task, so the commit evidence is required only when the range has more than one non-merge commit (a pull
request merge ref adds a merge commit on top of the squashed one); the Completion Notes check always applies.

When `integrationRef` is unset and no `--base` is given there is no range to check: the script prints one line saying
so and exits 0.

Usage: python3 scripts/forge/check-task-evidence.py [--base <ref>] [--profile <path>]
Exit codes: 0 ok, or no base ref configured; 1 a Complete task lacks evidence (one line each); 2 the base ref or the
profile is unusable.
A missing binding file counts as every key unset: one line (`no .claude/quality-profile.json; run python3
scripts/forge/quality_profile.py init`) and exit 0.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_profile  # noqa: E402  (sibling module; path set above)

PREFIX = "task-evidence"
README = re.compile(r"^specs/[^/]+/tasks/README\.md$")
# Template text of the Completion Notes section: a whole-line `[...]` placeholder, a `**Field**: value` line, and a
# `[...]` placeholder inside a value (two or more characters, so a `[x]` checkbox is not one; nor is a markdown link).
PLACEHOLDER_LINE = re.compile(r"^\s*\[[^\]]+\]\s*$")
FIELD = re.compile(r"^\s*\*\*[^*]+\*\*:?\s*(.*)$")
PLACEHOLDER = re.compile(r"\[[^\]]{2,}\](?!\()")


def git(repo: str, *args: str, check: bool = True) -> str:
    """Run git in the repository; raise ValueError on failure when `check`, else return an empty string."""
    result = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if result.returncode != 0:
        if check:
            raise ValueError(f"git {' '.join(args)}: {result.stderr.strip() or result.returncode}")
        return ""
    return result.stdout


def complete_ids(text: str) -> set[str]:
    """Task numbers of the table rows whose last cell is `Complete`."""
    ids: set[str] = set()
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.strip().startswith("|") and len(cells) >= 2 and re.fullmatch(r"\d+", cells[0]) and cells[-1] == "Complete":
            ids.add(cells[0])
    return ids


def _filled(line: str) -> bool:
    """Whether a Completion Notes line carries content, not the template's placeholder text."""
    if not line.strip() or PLACEHOLDER_LINE.match(line):
        return False
    field = FIELD.match(line)
    if field:
        value = field.group(1).strip()
        return bool(value) and PLACEHOLDER.search(value) is None
    return True


def completion_notes(text: str) -> str:
    """The filled lines of the `## Completion Notes` section (empty when it is missing or still the template)."""
    match = re.search(r"^##\s+Completion Notes\s*$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not match:
        return ""
    return "\n".join(line for line in match.group(1).splitlines() if _filled(line)).strip()


def names_task(subject: str, number: str) -> bool:
    """Whether a commit subject names the task (`Task 3:` or `T3`, leading zeros ignored)."""
    n = str(int(number))
    return re.search(rf"\b(task\s+0*{n}|t0*{n})\b", subject, re.I) is not None


def check(repo: str, base: str) -> tuple[list[str], int]:
    """Return (problems, number of newly Complete tasks examined)."""
    if not git(repo, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}", check=False).strip():
        raise ValueError(f"integrationRef {base} does not resolve (no remote or no commits yet); "
                         "fetch it or set integrationRef")
    merge_base = git(repo, "merge-base", base, "HEAD").strip()
    changed = git(repo, "diff", "--name-only", "--no-renames", merge_base, "--", "specs").split()
    subjects = git(repo, "log", "--no-merges", "--format=%s", f"{merge_base}..HEAD").splitlines()
    problems: list[str] = []
    examined = 0
    for path in sorted(p for p in changed if README.match(p)):
        full = os.path.join(repo, path)
        if not os.path.exists(full):
            continue
        with open(full, encoding="utf-8") as fh:
            now = complete_ids(fh.read())
        before = complete_ids(git(repo, "show", f"{merge_base}:{path}", check=False))
        feature = path.split("/")[1]
        for number in sorted(now - before):
            examined += 1
            files = sorted(glob.glob(os.path.join(repo, "specs", feature, "tasks", f"{number}-*.md")))
            if not files:
                problems.append(f"{feature} task {number}: marked Complete but has no task file")
            else:
                with open(files[0], encoding="utf-8") as fh:
                    if not completion_notes(fh.read()):
                        problems.append(f"{feature} task {number}: marked Complete without filled Completion Notes")
            if len(subjects) > 1 and not any(names_task(s, number) for s in subjects):
                problems.append(f"{feature} task {number}: marked Complete but no commit since {base} names the task")
    return problems, examined


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", default=quality_profile.DEFAULT_PROFILE)
    parser.add_argument("--base", help="the ref to diff against (default: the profile's integrationRef)")
    args = parser.parse_args(argv)
    try:
        profile = quality_profile.load_valid(args.profile)
        repo = os.path.dirname(os.path.dirname(os.path.abspath(args.profile)))
        base = args.base or profile.get("integrationRef")
        if not base:
            print(f"{PREFIX}: integrationRef is unset in the binding and no --base given; no range to check")
            return 0
        if not isinstance(base, str):
            raise ValueError("integrationRef: expected a string")
        problems, examined = check(repo, base)
    except quality_profile.MissingProfile:
        print(f"{PREFIX}: {quality_profile.MISSING}")
        return 0
    except (quality_profile.ProfileError, OSError, ValueError) as exc:
        print(f"{PREFIX}: {exc}", file=sys.stderr)
        return 2
    for problem in problems:
        print(f"{PREFIX}: {problem}")
    if problems:
        return 1
    print(f"{PREFIX}: ok ({examined} newly Complete task(s) since {base})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
