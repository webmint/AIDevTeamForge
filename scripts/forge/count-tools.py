#!/usr/bin/env python3
"""Small generic counters that print one integer, for use as ratchet `countCommand`s, and listers that print the
locations behind a count, for use as ratchet `locationsCommand`s and `groupsCommand`s (`scripts/forge/ratchet.py`).

Usage:
  python3 scripts/forge/count-tools.py json-value <file> <dotted.path>      # a number inside a JSON file
  python3 scripts/forge/count-tools.py json-sum <file> [<dotted.path>]      # sum of every integer leaf under the path
                                                                          # (default: whole file)
  python3 scripts/forge/count-tools.py json-sum-under <file> <key>          # sum of integer leaves under every key
                                                                          # named <key>, at any depth
  python3 scripts/forge/count-tools.py matches <regex> <dir-or-file>...     # lines matching the regex in tracked files
                                                                          # under the paths
  python3 scripts/forge/count-tools.py json-rows <file> <dotted.path> <field>...   # one line per element of the array
                                                                          # at the path: its fields (dotted, relative)
                                                                          # joined by spaces, largest first by the first
  python3 scripts/forge/count-tools.py json-leaves <file> [<dotted.path>]   # one line per integer leaf:
                                                                          # `<value> <key :: key ...>`, largest first
  python3 scripts/forge/count-tools.py clone-lines <jscpd report> <ratchet name> [--superseded]
                                                                          # duplicated lines of a jscpd JSON report,
                                                                          # minus the clone pairs that are redefinitions
  python3 scripts/forge/count-tools.py clone-rows <jscpd report> <ratchet name> [--superseded]
                                                                          # one line per remaining clone pair:
                                                                          # `<lines> <file> <start> <file> <start>`
  python3 scripts/forge/count-tools.py renamed-lines <jscpd report> <ratchet name> <formats> [--superseded]
                                                                          # source lines inside renamed clones (below)
  python3 scripts/forge/count-tools.py renamed-rows <jscpd report> <ratchet name> <formats> [--superseded]
                                                                          # one line per counted renamed pair
  python3 scripts/forge/count-tools.py kind-pairs <jscpd report> <kind> [<formats>]   # number of clone pairs of a kind
  python3 scripts/forge/count-tools.py kind-rows <jscpd report> <kind> [<formats>]    # one line per such pair
  python3 scripts/forge/count-tools.py clone-groups <jscpd report> <ratchet name> [<kinds> [<formats>]] [--superseded]
                                                                          # one line per copy group:
                                                                          # `<copies> <lines> <file>:<start>-<end> ...`

The clone commands read a jscpd JSON report (`--reporters json`): `statistics.total.duplicatedLines` and the
`duplicates` list of clone pairs (`firstFile` / `secondFile` with `name`, `start`, `end`; `lines`, `format`, `kind`).
Another clone detector works when its report is converted to that shape.

Redefinitions: in files where a later definition of an object supersedes an earlier one (database migrations are the
usual case: a later migration repeats the body of an object it replaces), a clone detector reports the old and the new
body as a duplicate, and every fix of an existing object would grow the ratchet. The clone commands read the named
ratchet's `redefinitions` entry of the binding (`ratchets` in `.claude/quality-profile.json`): `files` (globs,
relative to the source root) and `definition` (a regex whose one group is the defined object's name). A clone pair is
a redefinition when both sides lie in such files and the set of objects whose definitions overlap the cloned lines is
the same, non-empty set on both sides, with no cloned line before the file's first definition. Duplication between
different objects still counts. Without a `redefinitions` entry every clone pair counts.

Superseded pairs (opt-in, `--superseded`; off by default): for files whose definitions are statements ended by `;`
(SQL-family migrations), two more kinds of pair are skipped. A definition is superseded when a later file of the
`files` set (path order) defines the same object name; its region is its own statement, from the definition line to
the `;` that ends it outside quotes, `--` and `/* */` comments and `$tag$` quotes. (1) A pair is skipped when every
line of both sides lies wholly inside superseded statements: dead text cannot be refactored. (2) A pair is skipped
when one side lies wholly inside superseded statements and the other side lies in a later file that redefines one of
them: the replacing change may move the old text into helpers, and the dead original is then the only other copy. Any
other line (text before the first definition, statements that define nothing) is live, so a clone that reaches it
still counts; a live definition in a file that does not redefine the superseded object, and two live bodies of the
replacing file, count against each other. Objects are matched by name only; a same-file redefinition supersedes
nothing. The flag has no effect without a `redefinitions` entry.

Near-miss clones: a jscpd run with `--ignore-identifiers` reports, besides the exact pairs, `renamed` pairs: the same
token sequence once identifiers are normalized (a copy with other names). `renamed-lines` counts the distinct source
lines (file and line number, both sides of every pair) that lie inside a renamed pair of one of the given formats
(comma-separated jscpd format names, e.g. the languages whose clones are real code and not markup sub-blocks), minus the
lines of any exact pair of the same report, because the exact ratchet already counts them; renamed pairs that are
redefinitions (or superseded, with the flag) are skipped like exact ones. `renamed-rows` lists the counted pairs,
largest first. A jscpd run with `--similarity` reports `similar` pairs: functions whose normalized syntax trees share
most subtrees (Type-3). `kind-pairs` counts the pairs of a kind (the number of pairs, not their lines: a pair is one
decision to merge or leave, and the count does not depend on function size); `kind-rows` lists them as
`<lines> <similarity> <file> <start> <file> <start>`, largest first. `<formats>` is optional there.

Copy groups (the third-copy trigger): a jscpd report lists pairs, so one piece of logic copied three times shows as
two or three pairs. `clone-groups` joins pairs that share a side (sides that overlap in the same file are one copy)
into groups and prints one line per group, most copies first: the number of copies (distinct regions), the longest
pair in lines, then every region as `<file>:<start>-<end>` (file names as jscpd prints them, relative to the scanned
directory). `<kinds>` (comma-separated: exact, renamed, similar) and `<formats>` restrict the pairs; redefinitions
are skipped as in `clone-lines`. A ratchet's `groupsCommand` prints these lines, and `ratchet.py copies` filters them
to the files a plan or a diff touches.

`matches` reads only git-tracked files (`git ls-files`) under the paths it is given, so it never reaches directories the
caller did not name. Product code is read in the source root (`SOURCE_ROOT` of `.claude/project-config.json`, see
quality_profile.py): `matches` runs git there and its paths, like the `redefinitions` globs, are relative to it (a
`<SOURCE_ROOT>/` prefix is accepted); a path that does not exist there exits 2. Counters exit 0 with one integer on stdout, listers exit 0 with one line per location; both exit 2
with a message on stderr when the input is unusable (a clone command also when the binding is missing or does not name
the ratchet: it runs from a ratchet's command, so the ratchet is configured).
"""
from __future__ import annotations

import glob
import io
import json
import os
import re
import stat
import subprocess
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_profile  # noqa: E402  (sibling module; path set above)


def walk(data: Any, path: str) -> Any:
    """Follow a dotted path through nested dicts; an empty path returns the data itself."""
    for part in [p for p in path.split(".") if p]:
        if not isinstance(data, dict) or part not in data:
            raise KeyError(path)
        data = data[part]
    return data


def sum_leaves(data: Any) -> int:
    """Sum every integer leaf (booleans excluded) in a nested structure."""
    if isinstance(data, bool):
        return 0
    if isinstance(data, int):
        return data
    if isinstance(data, dict):
        return sum(sum_leaves(v) for v in data.values())
    if isinstance(data, list):
        return sum(sum_leaves(v) for v in data)
    return 0


def sum_under_key(data: Any, key: str) -> int:
    """Sum the integer leaves below every dict entry named `key`, at any depth."""
    total = 0
    if isinstance(data, dict):
        for name, value in data.items():
            total += sum_leaves(value) if name == key else sum_under_key(value, key)
    elif isinstance(data, list):
        total += sum(sum_under_key(v, key) for v in data)
    return total


def field(data: Any, path: str) -> str:
    """A dotted field of one element as text; a missing field is `?`, so one odd element never hides the others."""
    try:
        return str(walk(data, path))
    except KeyError:
        return "?"


def _numeric(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


def json_rows(data: Any, path: str, fields: list[str]) -> list[str]:
    """One line per element of the array at `path`: the fields joined by spaces, largest first by the first field."""
    node = walk(data, path)
    if not isinstance(node, list):
        raise TypeError(f"{path or '<root>'} is not an array")
    rows = [[field(element, name) for name in fields] for element in node]
    rows.sort(key=lambda row: -(_numeric(row[0]) or 0.0))
    return [" ".join(row) for row in rows]


def json_leaves(data: Any, prefix: tuple[str, ...] = ()) -> list[tuple[int, str]]:
    """Every integer leaf (booleans excluded) with its key path joined by ` :: `, largest first."""
    found: list[tuple[int, str]] = []
    if isinstance(data, bool):
        return found
    if isinstance(data, int):
        return [(data, " :: ".join(prefix))]
    items = data.items() if isinstance(data, dict) else enumerate(data) if isinstance(data, list) else []
    for key, value in items:
        found.extend(json_leaves(value, (*prefix, str(key))))
    if not prefix:
        found.sort(key=lambda leaf: (-leaf[0], leaf[1]))
    return found


def count_matches(pattern: str, paths: list[str], repo: str | None = None) -> int:
    """Count lines matching `pattern` in the git-tracked files under `paths`, read with git in the source root of the
    project at `repo` (default: the working directory, where `ratchet.py` runs its commands). The paths are relative
    to the source root (a `<SOURCE_ROOT>/` prefix is accepted); a literal path that does not exist there raises ValueError,
    so a misplaced path never counts as 0 (a glob pathspec is passed to git as it is)."""
    regex = re.compile(pattern)
    repo = os.getcwd() if repo is None else repo
    source = quality_profile.source_root(repo)
    specs = [quality_profile.source_path(p, repo) for p in paths]
    # A glob pathspec (`src/*.py`) is git's to expand; only a literal path is checked for existence.
    missing = [p for p, spec in zip(paths, specs)
               if not re.search(r"[*?\[]", spec) and not os.path.exists(os.path.join(source, spec))]
    if missing:
        raise ValueError(f"not under the source root {source}: {', '.join(missing)}")
    listing = subprocess.run(["git", "-C", source, "ls-files", "-z", "--", *specs], capture_output=True)
    if listing.returncode != 0:
        reason = listing.stderr.decode("utf-8", "replace").strip()
        raise ValueError(f"git ls-files failed in {source}: {reason}")
    total = 0
    for raw in filter(None, listing.stdout.split(b"\0")):
        path = os.path.join(source, os.fsdecode(raw))
        # Only regular files carry lines: a tracked symlink (to a directory, or a second name of a counted file), a
        # submodule and a file deleted from the working tree are skipped.
        try:
            if not stat.S_ISREG(os.lstat(path).st_mode):
                continue
            with open(path, "rb") as handle:
                data = handle.read()
        except FileNotFoundError:
            continue
        if b"\0" in data[:8000]:
            continue  # a binary file (git's own test: a NUL byte near the start)
        # One undecodable byte must not drop the file's other lines from the count.
        lines = io.TextIOWrapper(io.BytesIO(data), encoding="utf-8", errors="replace")  # the same lines as open()
        total += sum(1 for line in lines if regex.search(line))
    return total


def redefinition_config(ratchet: str, profile_path: str = quality_profile.DEFAULT_PROFILE) -> dict | None:
    """Return the `redefinitions` entry of the named ratchet (binding key `ratchets`), or None when it has none."""
    profile = quality_profile.load_valid(profile_path)
    for entry in profile.get("ratchets") or []:
        if isinstance(entry, dict) and entry.get("name") == ratchet:
            section = entry.get("redefinitions")
            return section if isinstance(section, dict) else None
    raise KeyError(f"no ratchet named {ratchet}")


class Redefinitions:
    """Decides whether a clone pair of a jscpd report is the redefinition of one object (see the module docstring)."""

    def __init__(self, config: dict | None, root: str, superseded: bool = False, repo: str | None = None) -> None:
        """`root` is the directory the `files` globs are relative to: the source root. With `repo` (the project root),
        a glob that starts with `<SOURCE_ROOT>/` is read without that prefix."""
        self.superseded = superseded
        self.pattern = re.compile(config["definition"]) if config else None
        self.files: list[str] = []
        if config:
            for spec in config["files"]:
                spec = quality_profile.source_path(spec, repo) if repo else spec
                self.files.extend(os.path.relpath(p, root) for p in glob.glob(os.path.join(root, spec), recursive=True))
        self.root = root
        self._defs: dict[str, list[tuple[int, str]]] = {}
        self._superseded: dict[str, list[tuple[int, int]]] | None = None
        self._statements: dict[str, list[tuple[int, int, str]]] | None = None
        self._definers: dict[str, set[str]] | None = None

    def resolve(self, name: str) -> str | None:
        """The configured file a report name denotes (jscpd names files relative to the scanned directory)."""
        for path in self.files:
            if path == name or path.endswith("/" + name):
                return path
        return None

    def definitions(self, path: str) -> list[tuple[int, str]]:
        """`(line, normalized object name)` of every definition in the file, in order (lines are 1-based)."""
        if path not in self._defs:
            found: list[tuple[int, str]] = []
            with open(os.path.join(self.root, path), encoding="utf-8") as handle:
                for number, line in enumerate(handle, start=1):
                    match = self.pattern.search(line) if self.pattern else None
                    if match:
                        found.append((number, match.group(1).replace('"', "").lower()))
            self._defs[path] = found
        return self._defs[path]

    def objects(self, path: str, start: int, end: int) -> frozenset[str] | None:
        """Objects whose definition region overlaps lines start..end; None when a cloned line precedes every definition."""
        defs = self.definitions(path)
        if not defs or start < defs[0][0]:
            return None
        names = set()
        for index, (line, name) in enumerate(defs):
            region_end = defs[index + 1][0] - 1 if index + 1 < len(defs) else float("inf")
            if line <= end and region_end >= start:
                names.add(name)
        return frozenset(names)

    def statement_ends(self, path: str) -> list[int]:
        """Character offsets of every `;` outside quotes, dollar quotes and comments in the file, in order."""
        with open(os.path.join(self.root, path), encoding="utf-8") as handle:
            text = handle.read()
        ends: list[int] = []
        i, size = 0, len(text)
        while i < size:
            ch = text[i]
            if ch == "-" and text.startswith("--", i):
                newline = text.find("\n", i)
                i = size if newline < 0 else newline
            elif ch == "/" and text.startswith("/*", i):
                close = text.find("*/", i + 2)
                i = size if close < 0 else close + 2
            elif ch in "'\"":
                close = text.find(ch, i + 1)
                while close >= 0 and text.startswith(ch, close + 1):  # doubled quote is an escape
                    close = text.find(ch, close + 2)
                i = size if close < 0 else close + 1
            elif ch == "$" and (tag := re.compile(r"\$(?:[A-Za-z_]\w*)?\$").match(text, i)):
                close = text.find(tag.group(0), tag.end())
                i = size if close < 0 else close + len(tag.group(0))
            else:
                if ch == ";":
                    ends.append(i)
                i += 1
        return ends

    def definers(self) -> dict[str, set[str]]:
        """Object name -> the configured files that define it."""
        if self._definers is None:
            found: dict[str, set[str]] = {}
            for path in sorted(self.files):
                for _, name in self.definitions(path):
                    found.setdefault(name, set()).add(path)
            self._definers = found
        return self._definers

    def superseded_statements(self) -> dict[str, list[tuple[int, int, str]]]:
        """Per file, the `(first line, last line, object name)` of every statement a later file redefines."""
        if self._statements is not None:
            return self._statements
        definers = self.definers()
        result: dict[str, list[tuple[int, int, str]]] = {}
        for path in sorted(self.files):
            with open(os.path.join(self.root, path), encoding="utf-8") as handle:
                lines = handle.read().split("\n")
            offsets, total = [], 0
            for line in lines:
                offsets.append(total)
                total += len(line) + 1
            ends = None
            statements: list[tuple[int, int, str]] = []
            for number, name in self.definitions(path):
                if not any(other > path for other in definers[name]):
                    continue
                ends = self.statement_ends(path) if ends is None else ends
                terminator = next((e for e in ends if e >= offsets[number - 1]), None)
                last = len(lines) if terminator is None else next(
                    n for n in range(number, len(lines) + 1) if n == len(lines) or offsets[n] > terminator)
                statements.append((number, last, name))
            result[path] = statements
        self._statements = result
        return result

    def superseded_ranges(self) -> dict[str, list[tuple[int, int]]]:
        """Per file, the merged `(first line, last line)` ranges of statements a later file redefines."""
        if self._superseded is not None:
            return self._superseded
        result: dict[str, list[tuple[int, int]]] = {}
        for path, statements in self.superseded_statements().items():
            merged: list[tuple[int, int]] = []
            for first, last in sorted((first, last) for first, last, _ in statements):
                if merged and first <= merged[-1][1] + 1:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], last))
                else:
                    merged.append((first, last))
            result[path] = merged
        self._superseded = result
        return result

    def _side(self, clone: dict, key: str) -> tuple[str, int, int] | None:
        """`(configured file, first line, last line)` of one side of a clone pair, or None outside the configured files."""
        side = clone.get(key) or {}
        path = self.resolve(str(side.get("name", "")))
        return None if path is None else (path, int(side["start"]), int(side["end"]))

    def is_superseded_pair(self, clone: dict) -> bool:
        """True when every cloned line of both sides lies inside statements a later file redefines."""
        if self.pattern is None:
            return False
        for key in ("firstFile", "secondFile"):
            side = self._side(clone, key)
            if side is None:
                return False
            path, start, end = side
            if not any(first <= start and end <= last for first, last in self.superseded_ranges().get(path, [])):
                return False
        return True

    def is_superseding_change_pair(self, clone: dict) -> bool:
        """True when one side lies wholly inside superseded statements and the other side lies in a file that
        redefines one of those statements: a change that replaces a definition may move its old text into
        helpers or split it, and the dead original is the only other copy. A live definition in any other file
        is not covered."""
        if self.pattern is None:
            return False
        sides = [self._side(clone, key) for key in ("firstFile", "secondFile")]
        if None in sides:
            return False
        for dead, other in (sides, sides[::-1]):
            path, start, end = dead
            names = {name for first, last, name in self.superseded_statements().get(path, []) if first <= end and last >= start}
            wholly = any(first <= start and end <= last for first, last in self.superseded_ranges().get(path, []))
            if wholly and any(other[0] > path and other[0] in self.definers()[name] for name in names):
                return True
        return False

    def skips(self, clone: dict) -> bool:
        """True when the clone pair is not counted: a redefinition, or (with `superseded`) a superseded pair or a
        pair of superseded text with the change that replaced it."""
        if self.is_redefinition(clone):
            return True
        return self.superseded and (self.is_superseded_pair(clone) or self.is_superseding_change_pair(clone))

    def is_redefinition(self, clone: dict) -> bool:
        if self.pattern is None:
            return False
        sides = []
        for key in ("firstFile", "secondFile"):
            side = clone.get(key) or {}
            path = self.resolve(str(side.get("name", "")))
            if path is None:
                return False
            sides.append(self.objects(path, int(side["start"]), int(side["end"])))
        return sides[0] is not None and bool(sides[0]) and sides[0] == sides[1]


def clone_lines(report: dict, redefinitions: Redefinitions) -> int:
    """The report's duplicated lines minus the lines of the clone pairs that are redefinitions."""
    total = int(walk(report, "statistics.total.duplicatedLines"))
    return total - sum(int(c.get("lines", 0)) for c in report.get("duplicates", []) if redefinitions.skips(c))


def clone_rows(report: dict, redefinitions: Redefinitions) -> list[str]:
    """One line per clone pair that is not a redefinition: lines, first file and start, second file and start."""
    kept = {"duplicates": [c for c in report.get("duplicates", []) if not redefinitions.skips(c)]}
    return json_rows(kept, "duplicates", ["lines", "firstFile.name", "firstFile.start", "secondFile.name", "secondFile.start"])


def _sides(clone: dict) -> list[tuple[str, int, int]]:
    """`(file, first line, last line)` of both sides of a clone pair."""
    return [(str(clone[key]["name"]), int(clone[key]["start"]), int(clone[key]["end"]))
            for key in ("firstFile", "secondFile")]


def _positions(clones: list[dict]) -> set[tuple[str, int]]:
    """Every `(file, line)` inside either side of the given clone pairs."""
    return {(name, line) for clone in clones for name, start, end in _sides(clone) for line in range(start, end + 1)}


def _renamed_pairs(report: dict, redefinitions: Redefinitions, formats: set[str]) -> list[dict]:
    """The renamed pairs of the given formats that are neither redefinitions nor superseded."""
    return [c for c in report.get("duplicates", [])
            if c.get("kind") == "renamed" and c.get("format") in formats and not redefinitions.skips(c)]


def renamed_lines(report: dict, redefinitions: Redefinitions, formats: set[str]) -> int:
    """Distinct source lines inside counted renamed pairs, minus the lines of the report's exact pairs."""
    exact = _positions([c for c in report.get("duplicates", []) if c.get("kind") == "exact"])
    return len(_positions(_renamed_pairs(report, redefinitions, formats)) - exact)


def renamed_rows(report: dict, redefinitions: Redefinitions, formats: set[str]) -> list[str]:
    """One line per counted renamed pair: lines, first file and start, second file and start."""
    kept = {"duplicates": _renamed_pairs(report, redefinitions, formats)}
    return json_rows(kept, "duplicates", ["lines", "firstFile.name", "firstFile.start", "secondFile.name", "secondFile.start"])


def _of_kind(report: dict, kind: str, formats: set[str]) -> list[dict]:
    """The clone pairs of one kind, restricted to the formats when any are given."""
    return [c for c in report.get("duplicates", []) if c.get("kind") == kind and (not formats or c.get("format") in formats)]


def kind_pairs(report: dict, kind: str, formats: set[str]) -> int:
    """The number of clone pairs of one kind."""
    return len(_of_kind(report, kind, formats))


def kind_rows(report: dict, kind: str, formats: set[str]) -> list[str]:
    """One line per clone pair of one kind: lines, similarity (1 when the report has none), both sides, largest first."""
    pairs = [dict(c, similarity=c.get("similarity", 1)) for c in _of_kind(report, kind, formats)]
    return json_rows({"duplicates": pairs}, "duplicates",
                     ["lines", "similarity", "firstFile.name", "firstFile.start", "secondFile.name", "secondFile.start"])


def clone_groups(report: dict, redefinitions: Redefinitions, kinds: set[str], formats: set[str]) -> list[str]:
    """One line per copy group: the copies (distinct regions), the longest pair's lines, then each region."""
    pairs = [c for c in report.get("duplicates", [])
             if (not kinds or c.get("kind", "exact") in kinds) and (not formats or c.get("format") in formats)
             and not redefinitions.skips(c)]
    sides: list[tuple[str, int, int]] = []
    parent: list[int] = []

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        parent[find(a)] = find(b)

    for clone in pairs:
        first = len(sides)
        sides.extend(_sides(clone))
        parent.extend((first, first))
        union(first, first + 1)
    by_file: dict[str, list[int]] = {}
    for index, (name, _, _) in enumerate(sides):
        by_file.setdefault(name, []).append(index)
    for indexes in by_file.values():  # overlapping sides in one file are one copy
        indexes.sort(key=lambda i: sides[i][1])
        reach, owner = -1, -1
        for i in indexes:
            if sides[i][1] <= reach:
                union(i, owner)
            if sides[i][2] > reach:
                reach, owner = sides[i][2], i
    lines_of = {}
    members: dict[int, list[int]] = {}
    for index in range(len(sides)):
        members.setdefault(find(index), []).append(index)
    for number, clone in enumerate(pairs):
        root = find(2 * number)
        lines_of[root] = max(lines_of.get(root, 0), int(clone.get("lines", 0)))
    rows = []
    for root, indexes in members.items():
        regions: list[list] = []
        for name, start, end in sorted(sides[i] for i in indexes):
            if regions and regions[-1][0] == name and start <= regions[-1][2]:
                regions[-1][2] = max(regions[-1][2], end)
            else:
                regions.append([name, start, end])
        rows.append((len(regions), lines_of[root], " ".join(f"{n}:{a}-{b}" for n, a, b in regions)))
    rows.sort(key=lambda row: (-row[0], -row[1], row[2]))
    return [f"{copies} {lines} {where}" for copies, lines, where in rows]


# The commands that skip redefinitions, and so accept `--superseded`.
CLONE_COMMANDS = ("clone-lines", "clone-rows", "renamed-lines", "renamed-rows", "clone-groups")


def _formats(text: str | None) -> set[str]:
    return {part for part in (text or "").split(",") if part}


def main(argv: list[str]) -> int:
    superseded = "--superseded" in argv
    argv = [arg for arg in argv if arg != "--superseded"]
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    command, rest = argv[0], argv[1:]
    if superseded and command not in CLONE_COMMANDS:
        print(f"count-tools: --superseded is valid only with {', '.join(CLONE_COMMANDS)}", file=sys.stderr)
        return 2
    try:
        if command in ("json-value", "json-sum"):
            with open(rest[0], encoding="utf-8") as handle:
                data = json.load(handle)
            node = walk(data, rest[1] if len(rest) > 1 else "")
            if command == "json-sum":
                print(sum_leaves(node))
            else:
                print(int(node))
        elif command == "json-sum-under" and len(rest) == 2:
            with open(rest[0], encoding="utf-8") as handle:
                print(sum_under_key(json.load(handle), rest[1]))
        elif command == "matches" and len(rest) >= 2:
            print(count_matches(rest[0], rest[1:]))
        elif command == "json-rows" and len(rest) >= 3:
            with open(rest[0], encoding="utf-8") as handle:
                lines = json_rows(json.load(handle), rest[1], rest[2:])
            print("\n".join(lines))
        elif command in ("clone-lines", "clone-rows") and len(rest) == 2:
            with open(rest[0], encoding="utf-8") as handle:
                report = json.load(handle)
            redefinitions = Redefinitions(redefinition_config(rest[1]), quality_profile.source_root(), superseded, quality_profile.REPO)
            if command == "clone-lines":
                print(clone_lines(report, redefinitions))
            else:
                print("\n".join(clone_rows(report, redefinitions)))
        elif command in ("renamed-lines", "renamed-rows") and len(rest) == 3:
            with open(rest[0], encoding="utf-8") as handle:
                report = json.load(handle)
            redefinitions = Redefinitions(redefinition_config(rest[1]), quality_profile.source_root(), superseded, quality_profile.REPO)
            if command == "renamed-lines":
                print(renamed_lines(report, redefinitions, _formats(rest[2])))
            else:
                print("\n".join(renamed_rows(report, redefinitions, _formats(rest[2]))))
        elif command in ("kind-pairs", "kind-rows") and len(rest) in (2, 3):
            with open(rest[0], encoding="utf-8") as handle:
                report = json.load(handle)
            formats = _formats(rest[2] if len(rest) > 2 else None)
            if command == "kind-pairs":
                print(kind_pairs(report, rest[1], formats))
            else:
                print("\n".join(kind_rows(report, rest[1], formats)))
        elif command == "clone-groups" and len(rest) in (2, 3, 4):
            with open(rest[0], encoding="utf-8") as handle:
                report = json.load(handle)
            redefinitions = Redefinitions(redefinition_config(rest[1]), quality_profile.source_root(), superseded, quality_profile.REPO)
            kinds = _formats(rest[2] if len(rest) > 2 else None)
            print("\n".join(clone_groups(report, redefinitions, kinds, _formats(rest[3] if len(rest) > 3 else None))))
        elif command == "json-leaves" and len(rest) in (1, 2):
            with open(rest[0], encoding="utf-8") as handle:
                node = walk(json.load(handle), rest[1] if len(rest) > 1 else "")
            print("\n".join(f"{value} {where}" for value, where in json_leaves(node)))
        else:
            print(__doc__, file=sys.stderr)
            return 2
    except (OSError, ValueError, KeyError, TypeError, IndexError, json.JSONDecodeError, re.error,
            subprocess.CalledProcessError, quality_profile.ProfileError) as exc:
        print(f"count-tools: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
