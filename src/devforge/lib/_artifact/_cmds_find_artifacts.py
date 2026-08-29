"""_artifact._cmds_find_artifacts -- find-feature-artifacts verb for artifact_helper.

Shared discovery verb: locate a named artifact (or set of artifacts) across
every feature directory under specs/, regardless of directory-nesting shape
(the legacy specs/NNN-slug/ layout or the 91-FEATURE-DIR-IDENTITY-AND-
PROVENANCE-PLAN.md Phase 3 forward specs/YYYY/MM/TICKET/ layout).

Why this verb exists (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md
Phase 1b): several command specs run a depth-1 glob over specs/ themselves
(specs/*/grill-seed.json, specs/*/*-seed.json, specs/NNN-* directory
enumerations, specs/*/review.md) instead of asking a helper. Phase 1
retired that same depth-1 assumption from all six Python resolvers by
extracting _shared/feature_alloc.py's iter_feature_dirs /
find_feature_dirs_with; this verb is the ONE place those globs move to
once the owning command's prose is migrated (a separate, later task --
this module only needs to exist and be tested here).

Why artifact_helper, not a command-owned helper: every consumer the
Phase 1b inventory names (research, discover, plan, specify, review, fix,
verify, finalize, summarize, spec-check, breakdown, grill) already calls
artifact_helper for commit-artifacts. artifact_helper is nobody's
PRODUCING helper -- it is shared infrastructure every command already
depends on -- so a verb here does not weaken the decoupling constraint
that keeps a seed-reading block valid even if the producing command is
ever removed (unlike putting this on e.g. grill_helper, which IS a
producing helper for some of these consumers).

Why its own module rather than growing _cli.py in place: _cli.py was
already 493 lines before this verb existed (commit-artifacts's own git
primitives, verb handler, and Cyrillic language guard). Adding a second
full verb's docstring + handler in place would push it past this
repository's 600-line automatic-split-finding threshold. _cli.py stays
the thin argparse registry + main(); this module owns the second verb's
logic end to end (Controller / SRP).

Verb
----
find-feature-artifacts  --filenames <json>  [--root <path>]

--filenames is a JSON array of one or more entries. Each entry is either:
  - a LITERAL basename (e.g. "research-handoff.json") -- matched by
    delegating to _shared/feature_alloc.find_feature_dirs_with, which
    already knows both directory shapes. Covers /specify's two-name
    lookup (research-handoff.json AND discover-handoff.json) in one call.
  - an fnmatch-style GLOB pattern containing '*', '?', or '[' (e.g.
    "*-seed.json") -- matched against each feature directory's own file
    listing (fnmatch.fnmatchcase, case-sensitive on every platform).
    Covers /plan's seed-producer lookup, which must not need editing every
    time a new *-seed.json producer is added -- an exact-name-only array
    would force that edit.
A single flag carries both shapes rather than a second --suffix flag: a
literal name with no glob metacharacter behaves identically whichever way
it is matched, so one JSON-array flag (matching commit-artifacts's
--paths convention in this same package) covers every consumer the
Phase 1b inventory names, without a second flag to document and parse.

find_feature_dirs_with itself takes only an exact filename (see its own
docstring) -- ALL glob-suffix matching happens in this module, never
smuggled into the shared primitive. Directory-LAYOUT scanning (which
directories exist, in which shape, in what order) is still 100%
delegated to iter_feature_dirs / find_feature_dirs_with; this module adds
no scanning logic for that part -- only per-directory filename filtering.

Exit codes
----------
0  -- success, REGARDLESS of hit count. Zero matches is a normal outcome
      (e.g. "no seed found yet") for several real consumers and must not
      be reported as an error -- matches commit-artifacts's own
      EXIT_OK-includes-benign-no-op convention in this package.
1  -- clean error: bad --filenames JSON, --filenames not a JSON array, or
      workspace resolution raising (message on stderr, no traceback, no
      exception escaping the handler).

Output (stdout, one JSON object)
---------------------------------
{
  "matches": [
    {"feature_dir": "specs/003-foo",
     "file": "specs/003-foo/research-handoff.json",
     "filename": "research-handoff.json"},
    ...
  ],
  "feature_dirs": ["specs/003-foo", ...]
}
"matches" is one entry per (feature directory, matched file) pair, in
iter_feature_dirs's documented order (legacy family first, ascending by
NNN; then the new-shape family, ascending by (YYYY, MM, leaf dir name)),
deduplicated on the (feature_dir, file) pair -- a directory that holds
BOTH a research-handoff.json and a discover-handoff.json contributes two
distinct entries (different files); a directory that would otherwise
match the SAME file twice (two overlapping --filenames entries, or a
literal name repeated in the array) contributes exactly one. "feature_dirs"
is the feature_dir field of "matches", deduplicated in first-seen order --
a convenience view for a caller that only needs the directory list, not
which file matched (e.g. a /devforge:review-style directory enumeration).
"filename" is always the matched file's OWN basename (never the glob
pattern that matched it), so a caller can dispatch on it directly (e.g.
filename == "research-handoff.json" vs "discover-handoff.json").

Both "feature_dir" and "file" are relative to the install root
(forward-slash separated, never platform-joined) -- the same
relative_path discipline _shared/feature_alloc.py's allocate_feature_dir
documents for itself: a value that may be passed as a path ARGUMENT to
another helper verb must not leak the local filesystem layout via an
absolute path. This is a deliberate departure from
_specify/_cmds_handoff.py's find-handoffs verb, whose handoff_path field
is absolute -- find-handoffs predates the relative_path convention
_shared/feature_alloc.py later established; this new verb is written to
that later convention from the start rather than to find-handoffs's
older one.

--root follows commit-artifacts's own convention exactly (same package,
_cli.py): a path (default ".") resolved via
_implement._workspace.resolve_workspace, so specs/ is always found under
the INSTALL root, never the source root, in wrapper mode -- the same D2
invariant commit-artifacts documents for itself.

Stdlib only. Python 3.8+.
"""

import argparse
import fnmatch
import json
import sys
from pathlib import Path
from typing import Dict, List, Set

from _implement._workspace import resolve_workspace  # type: ignore[import]
from _shared.feature_alloc import (  # type: ignore[import]
    SPECS_ROOT_DEFAULT,
    find_feature_dirs_with,
    iter_feature_dirs,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_ERR = 1

# fnmatch metacharacters. An entry containing none of these is matched as
# a literal basename (delegated to find_feature_dirs_with); an entry
# containing any of these is matched as a glob pattern against each
# feature dir's own listing (see module docstring).
_GLOB_CHARS = frozenset("*?[")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_glob_pattern(name):
    # type: (str) -> bool
    """True if name contains an fnmatch metacharacter (*, ?, or [)."""
    return any(ch in _GLOB_CHARS for ch in name)


def _relative_posix(path, root):
    # type: (Path, Path) -> str
    """path relative to root, forward-slash separated on every platform.

    Mirrors the discipline _shared/feature_alloc.py documents for its own
    relative_path key (allocate_feature_dir): never platform-joined, never
    leaking the local filesystem layout into a value that might be
    written into a committed artifact or passed as a path argument to
    another helper verb.
    """
    return path.relative_to(root).as_posix()


def _record_match(matches, seen, feature_dir, file_path, filename, install_root):
    # type: (List[Dict[str, str]], Set, Path, Path, str, Path) -> None
    """Append one match dict, skipping an already-recorded (dir, file) pair."""
    key = (str(feature_dir), str(file_path))
    if key in seen:
        return
    seen.add(key)
    matches.append({
        "feature_dir": _relative_posix(feature_dir, install_root),
        "file": _relative_posix(file_path, install_root),
        "filename": filename,
    })


# ---------------------------------------------------------------------------
# Verb handler
# ---------------------------------------------------------------------------


def cmd_find_feature_artifacts(args):
    # type: (argparse.Namespace) -> int
    """find-feature-artifacts verb: locate named artifacts across feature dirs.

    See the module docstring for the full contract (flag shape, output
    shape, exit codes). Zero matches is success (exit 0), never an error.
    """
    filenames_json = getattr(args, "filenames", "[]") or "[]"
    try:
        raw_filenames = json.loads(filenames_json)
    except (json.JSONDecodeError, ValueError) as exc:
        sys.stderr.write(
            "find-feature-artifacts: --filenames is not valid JSON: {0}\n".format(exc)
        )
        return EXIT_ERR

    if not isinstance(raw_filenames, list):
        sys.stderr.write(
            "find-feature-artifacts: --filenames must be a JSON array, got {0}\n".format(
                type(raw_filenames).__name__
            )
        )
        return EXIT_ERR

    # Blank entries are a benign skip (mirrors commit-artifacts's own
    # treatment of a blank --paths entry) -- not a usage error.
    patterns = []  # type: List[str]
    for item in raw_filenames:
        if not item or not str(item).strip():
            continue
        patterns.append(str(item).strip())

    root_str = getattr(args, "root", ".") or "."
    install_root_arg = Path(root_str).resolve()
    try:
        workspace = resolve_workspace(install_root_arg)
    except Exception as exc:  # resolve_workspace is fail-soft but guard anyway
        sys.stderr.write(
            "find-feature-artifacts: workspace resolution failed: {0}\n".format(exc)
        )
        return EXIT_ERR

    install_root = workspace.install_root
    specs_root = install_root / SPECS_ROOT_DEFAULT

    literal_patterns = [p for p in patterns if not _is_glob_pattern(p)]
    glob_patterns = [p for p in patterns if _is_glob_pattern(p)]

    # Directory-layout scanning is 100% delegated -- this is the ONLY call
    # that walks specs/ itself, and it is also what determines the
    # documented output order (legacy family first, then new-shape).
    feature_dirs = iter_feature_dirs(specs_root)

    # One find_feature_dirs_with call per literal filename -- delegated,
    # not reimplemented. This re-walks specs/ once per literal name (on
    # top of the iter_feature_dirs call above); accepted for a specs/
    # tree of this repository's realistic size in exchange for using the
    # shared primitive as-is rather than special-casing it.
    literal_hits = {
        name: set(find_feature_dirs_with(specs_root, name))
        for name in literal_patterns
    }

    matches = []  # type: List[Dict[str, str]]
    seen = set()  # type: Set

    for feature_dir in feature_dirs:
        for name in literal_patterns:
            if feature_dir in literal_hits[name]:
                _record_match(
                    matches, seen, feature_dir, feature_dir / name, name, install_root
                )

        if not glob_patterns:
            continue
        try:
            entries = sorted(feature_dir.iterdir())
        except OSError:
            continue
        for entry in entries:
            try:
                if not entry.is_file():
                    continue
            except OSError:
                continue
            for pattern in glob_patterns:
                if fnmatch.fnmatchcase(entry.name, pattern):
                    _record_match(
                        matches, seen, feature_dir, entry, entry.name, install_root
                    )
                    break

    feature_dir_list = []  # type: List[str]
    feature_dir_seen = set()  # type: Set[str]
    for m in matches:
        if m["feature_dir"] not in feature_dir_seen:
            feature_dir_seen.add(m["feature_dir"])
            feature_dir_list.append(m["feature_dir"])

    result_obj = {
        "matches": matches,
        "feature_dirs": feature_dir_list,
    }
    sys.stdout.write(json.dumps(result_obj) + "\n")
    return EXIT_OK


# ---------------------------------------------------------------------------
# argparse registration (registry callback -- see _cli.py's
# _SUBCOMMAND_REGISTRY)
# ---------------------------------------------------------------------------


def add_find_feature_artifacts_args(parser):
    # type: (argparse.ArgumentParser) -> None
    """Register find-feature-artifacts's flags on parser (registry callback)."""
    parser.add_argument(
        "--filenames",
        required=True,
        help=(
            "JSON array of filenames to search for in every feature "
            "directory under specs/ (both the legacy specs/NNN-slug/ shape "
            "and the specs/YYYY/MM/TICKET/ shape). Each entry is either an "
            "exact basename (e.g. 'research-handoff.json') or an "
            "fnmatch-style glob pattern containing '*', '?', or '[' (e.g. "
            "'*-seed.json')."
        ),
    )
    parser.add_argument(
        "--root",
        default=".",
        help=(
            "Install root path. Defaults to cwd. specs/ is always resolved "
            "under the install root (never the source root), matching "
            "commit-artifacts."
        ),
    )
