#!/usr/bin/env python3
"""List the exported symbols a change adds (the reviewer's new-exports check).

The reviewer of a task or spec does not trust the implementer's Reuse check notes: it lists every new exported symbol
of the diff with this script and searches for each one itself. Which declarations count as exports is project data:
`.claude/quality-profile.json` → `newExports.patterns`, one entry per language:

  {"files": ["<glob>", ...], "exclude": ["<glob>", ...], "regex": "<pattern with one capture group: the name>"}
  {"files": ["<glob>", ...], "exclude": [...], "kind": "file"}     # every added file is one export, named by its stem

The script ships no patterns (an unset `newExports` is handled as the exit codes below say). Example entries (data
for the binding, not defaults): top-level Python definitions `{"files": ["src/**/*.py"], "exclude": ["**/test_*.py"],
"regex": "^(?:async )?(?:def|class) +([A-Za-z][A-Za-z0-9_]*)"}`; component files `{"files": ["ui/**/*.svelte"],
"kind": "file"}`.

A name is new when an added line of a matching file declares it and no file of the same entry declared it at the base
revision, so a redefinition, a move or a `create or replace` of an existing object is not listed. A definition that
moves between files stays known when the pattern's `regex` is unchanged: the base profile's files for that regex count
too (read with `git show <base>:<profile>`; an absent or unparseable base profile means the branch globs only). The
code graph's change detection, where a project has one, may add to this list; the script is the stack-neutral form.

Usage:
  python3 scripts/forge/new-exports.py [--base <rev>] [--profile <path>]

The base defaults to the merge base of HEAD with `integrationRef`; the change is the working tree against the base
(committed and uncommitted). Git runs in the source root (`SOURCE_ROOT`, see quality_profile.py): in a wrapper project
the base and `integrationRef` are revisions of the nested source repository, the globs are relative to it, and the base
profile is not read (branch globs only, since the profile lives in the wrapper repository). Output: one line `<path>:<line>: <name>` per new export, then `new-exports=<n>`.
Exit 0 with the list (it lists, it does not judge), or when `newExports.patterns` is unset: the script then prints
one line saying so and the reviewer lists the new exports from the diff by hand (the manual form). Exit 2 when the
binding file is invalid, or git fails. A missing binding file counts as every key unset: one line (`no .claude/quality-profile.json; run python3
scripts/forge/quality_profile.py init`) and exit 0.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_profile  # noqa: E402  (sibling module; path set above)

GIT_TIMEOUT = 60
HUNK = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


class ExportsError(Exception):
    """The binding or git cannot answer."""


def git(repo: str, *args: str, data: bytes | None = None) -> bytes:
    """Run one git command in the repository and return its stdout; raise ExportsError on failure. Paths are printed
    unquoted (`core.quotepath=off`), so a non-ASCII path reads as itself."""
    try:
        done = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=off", *args], input=data, capture_output=True,
                              timeout=GIT_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExportsError(f"git {args[0]} failed: {type(exc).__name__}") from exc
    if done.returncode != 0:
        reason = done.stderr.decode("utf-8", "replace").strip().splitlines()
        raise ExportsError(f"git {args[0]} exited {done.returncode} in {repo}" + (f": {reason[0]}" if reason else ""))
    return done.stdout


# The C-style escapes git uses in a quoted path (`"b/src/caf\303\251.ts"`).
_ESCAPES = {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}


def unquote(text: str) -> str:
    """A path as a diff header prints it: without the tab git adds after a name with a space, and unquoted when git
    quoted it (C-style escapes, octal bytes decoded as UTF-8)."""
    text = text.rstrip("\t")
    if not (len(text) >= 2 and text.startswith('"') and text.endswith('"')):
        return text
    raw, body, i = bytearray(), text[1:-1], 0
    while i < len(body):
        char = body[i]
        if char == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            if nxt in "01234567" and re.match(r"[0-7]{3}", body[i + 1:i + 4]):
                raw.append(int(body[i + 1:i + 4], 8))
                i += 4
                continue
            raw.extend(bytes([_ESCAPES[nxt]]) if nxt in _ESCAPES else nxt.encode("utf-8"))
            i += 2
            continue
        raw.extend(char.encode("utf-8"))
        i += 1
    return raw.decode("utf-8", "replace")


def names_z(out: bytes) -> list[str]:
    """The paths of a NUL-separated (`-z`) git listing."""
    return [name.decode("utf-8", "surrogateescape") for name in out.split(b"\0") if name]


def glob_regex(glob: str) -> re.Pattern[str]:
    """A glob as git's `:(glob)` pathspec reads it: `**/` any directories (or none), `*` and `?` within one name."""
    out = ""
    i = 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif glob.startswith("**", i):
            out, i = out + ".*", i + 2
        elif glob[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif glob[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(glob[i]), i + 1
    return re.compile(out + r"\Z")


def matches(path: str, entry: dict) -> bool:
    """True when the path is one of the entry's files and none of its exclusions."""
    return any(glob_regex(g).match(path) for g in entry.get("files", [])) and not any(
        glob_regex(g).match(path) for g in entry.get("exclude", []))


def entry_of(path: str, entries: list[dict]) -> int | None:
    """The index of the first entry that covers the path."""
    return next((i for i, entry in enumerate(entries) if matches(path, entry)), None)


def literal_root(glob: str) -> str:
    """The directories of a glob before its first wildcard (`ls-tree` takes paths, not pathspecs); "." for none."""
    head = re.split(r"[*?\[]", glob, maxsplit=1)[0]
    return head.rsplit("/", 1)[0] if "/" in head else "."


def stem(path: str) -> str:
    """The file name without its directory and last extension."""
    return os.path.splitext(os.path.basename(path))[0]


def added_lines(repo: str, base: str, pathspecs: list[str]) -> tuple[list[tuple[str, int, str]], set[str]]:
    """The added lines (path, line number, text) of the working tree against the base, and the added files."""
    diff = git(repo, "diff", "--no-color", "--unified=0", "--no-renames", base, "--", *pathspecs).decode("utf-8", "replace")
    lines: list[tuple[str, int, str]] = []
    added: set[str] = set()
    path = None
    number = 0
    was_new = False
    in_header = False  # between `diff --git` and the first hunk: only there is `+++ ` a file header
    for raw in diff.splitlines():
        if raw.startswith("diff --git "):
            path, was_new, in_header = None, False, True
        elif in_header and raw.startswith("new file mode"):
            was_new = True
        elif in_header and raw.startswith("+++ "):
            target = unquote(raw[4:])
            path = target[2:] if target.startswith("b/") else None
            if path and was_new:
                added.add(path)
        elif raw.startswith("@@"):
            in_header = False
            found = HUNK.match(raw)
            number = int(found.group(1)) if found else 0
        elif not in_header and raw.startswith("+") and path:
            lines.append((path, number, raw[1:]))
            number += 1
    untracked = names_z(git(repo, "ls-files", "-z", "--others", "--exclude-standard", "--", *pathspecs))
    for rel in untracked:
        full = os.path.join(repo, rel)
        # Only regular files carry lines: an untracked symlink (broken or not) or an unreadable file is skipped.
        try:
            if not stat.S_ISREG(os.lstat(full).st_mode):
                continue
            with open(full, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            continue
        added.add(rel)
        lines.extend((rel, i, line) for i, line in enumerate(text.splitlines(), start=1))
    return lines, added


def base_pattern_globs(repo: str, base: str, profile_path: str | None, entry: dict) -> list[str]:
    """The file globs of the base profile's pattern with the same `regex` as `entry`, read with `git show`.
    Empty when there is no profile path, the base profile is absent or unparseable, or no pattern matches."""
    if not profile_path or "regex" not in entry:
        return []
    try:
        rel = os.path.relpath(os.path.abspath(profile_path), repo)
        data = json.loads(git(repo, "show", f"{base}:{rel}"))
        patterns = data["newExports"]["patterns"]
        return [g for p in patterns if isinstance(p, dict) and p.get("regex") == entry["regex"] for g in p.get("files", [])]
    except (ExportsError, ValueError, KeyError, TypeError):
        return []


def base_names(repo: str, base: str, pathspecs: list[str], entries: list[dict],
               profile_path: str | None = None) -> list[set[str]]:
    """Per entry, the names its files declared at the base revision (regex entries) or their stems (file entries).
    A regex entry also counts the names that its regex captures in the base files matched by the base profile's
    pattern with the identical regex, so a definition that moves between files keeps its identity. Names have
    `"` dropped, as the names of the added lines do."""
    names: list[set[str]] = [set() for _ in entries]
    old_globs = {i: base_pattern_globs(repo, base, profile_path, e) for i, e in enumerate(entries)}
    roots = sorted({literal_root(spec.removeprefix(":(glob)")) for spec in pathspecs}
                   | {literal_root(g) for globs in old_globs.values() for g in globs})
    listing = names_z(git(repo, "ls-tree", "-r", "-z", "--name-only", base, "--", *roots))
    regex_files: list[tuple[str, int]] = []
    for path in listing:
        index = entry_of(path, entries)
        if index is not None and entries[index].get("kind") == "file":
            names[index].add(stem(path))
        elif index is not None:
            regex_files.append((path, index))
        regex_files += [(path, i) for i, globs in old_globs.items()
                        if globs and i != index and matches(path, {"files": globs, "exclude": entries[i].get("exclude", [])})]
    if regex_files:
        request = "".join(f"{base}:{path}\n" for path, _ in regex_files).encode()
        blob = git(repo, "cat-file", "--batch", data=request)
        offset = 0
        for _path, index in regex_files:
            header_end = blob.index(b"\n", offset)
            size = int(blob[offset:header_end].split()[2])
            text = blob[header_end + 1:header_end + 1 + size].decode("utf-8", "replace")
            offset = header_end + 1 + size + 1
            pattern = re.compile(entries[index]["regex"], re.MULTILINE)
            names[index].update(m.group(1).replace('"', "") for m in pattern.finditer(text))
    return names


def new_exports(repo: str, base: str, entries: list[dict], profile_path: str | None = None) -> list[tuple[str, int, str]]:
    """The new exports of the working tree against the base: (path, line, name), in diff order, each name once."""
    pathspecs = [f":(glob){g}" for entry in entries for g in entry.get("files", [])]
    lines, added = added_lines(repo, base, pathspecs)
    known = base_names(repo, base, pathspecs, entries, profile_path)
    found: list[tuple[str, int, str]] = []
    seen: set[tuple[int, str]] = set()
    for path in sorted(added):
        index = entry_of(path, entries)
        if index is not None and entries[index].get("kind") == "file":
            name = stem(path)
            if name not in known[index] and (index, name) not in seen:
                seen.add((index, name))
                found.append((path, 1, name))
    patterns = [re.compile(e["regex"]) if e.get("kind") != "file" else None for e in entries]
    for path, number, text in lines:
        index = entry_of(path, entries)
        if index is None or patterns[index] is None:
            continue
        hit = patterns[index].search(text)
        name = hit.group(1).replace('"', "") if hit else ""
        if hit and name not in known[index] and (index, name) not in seen:
            seen.add((index, name))
            found.append((path, number, name))
    return found


def run(base: str | None, profile_path: str) -> int:
    """Print the new exports; return the exit code."""
    workspace = os.path.dirname(os.path.dirname(os.path.abspath(profile_path)))
    try:
        profile = quality_profile.load(profile_path)
        section = profile.get("newExports")
        entries = section.get("patterns") if isinstance(section, dict) else section
        if entries in (None, [], {}):
            print("new-exports: newExports.patterns is unset; list the new exports from the diff by hand")
            return 0
        problems = quality_profile.validate(profile, repo=workspace)
    except quality_profile.MissingProfile:
        print(f"new-exports: {quality_profile.MISSING}")
        return 0
    except quality_profile.ProfileError as exc:
        print(f"new-exports: {exc}", file=sys.stderr)
        return 2
    if problems:
        print("new-exports: quality profile: " + "; ".join(problems), file=sys.stderr)
        return 2
    try:
        # Product code lives in the source root (wrapper mode: a nested repository); the globs are relative to it.
        repo = quality_profile.source_root(workspace)
        entries = [dict(e, **{k: [quality_profile.source_path(g, workspace) for g in e[k]]
                              for k in ("files", "exclude") if k in e}) for e in entries]
        # The base profile is read from the base revision, which is a revision of the repository holding the profile.
        base_profile = profile_path if repo == workspace else None
        if base is None:
            ref = profile.get("integrationRef") or "HEAD"
            base = git(repo, "merge-base", "HEAD", ref).decode().strip()
        found = new_exports(repo, base, entries, base_profile)
    except (ExportsError, quality_profile.ProfileError, ValueError, IndexError) as exc:
        print(f"new-exports: {exc}", file=sys.stderr)
        return 2
    for path, number, name in found:
        print(f"{path}:{number}: {name}")
    print(f"new-exports={len(found)}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base", help="the base revision (default: merge base of HEAD with integrationRef)")
    parser.add_argument("--profile", default=quality_profile.DEFAULT_PROFILE)
    args = parser.parse_args(argv)
    return run(args.base, args.profile)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
