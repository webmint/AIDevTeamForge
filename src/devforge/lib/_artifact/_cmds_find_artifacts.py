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
find-feature-artifacts  --filenames <json>  [--root <path>]  [--limit N]

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
     "filename": "research-handoff.json",
     "mtime_ts": 1735689600.0,
     "mtime_iso": "2025-01-01T00:00:00Z"},
    ...
  ],
  "feature_dirs": ["specs/003-foo", ...],
  "matches_by_recency": [ <same dicts as "matches", most-recent-mtime-first> ]
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

mtime, and two output orders (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-
PLAN.md Phase 1b follow-up)
-----------------------------------------------------------------------
The Phase 1b inventory splits into two classes. Class A finds a named or
patterned file (/devforge:research, /devforge:discover, /devforge:plan,
/devforge:specify's seed globs) -- "matches" in its documented layout
order already serves this. Class B resolves the MOST-RECENTLY-MODIFIED
feature directory carrying a sentinel (/devforge:review, /devforge:fix,
/devforge:verify, /devforge:finalize, /devforge:summarize,
/devforge:spec-check; /devforge:audit's recurring-issue scan additionally
windows to the last 90 days before taking the 5 most recent) -- neither
of which "matches"'s layout order can answer.

"mtime_ts" / "mtime_iso" on every match, same field names and same
"%Y-%m-%dT%H:%M:%SZ" UTC format _specify/_cmds_handoff.py's find-handoffs
verb already uses for its own mtime fields -- the orchestrators that
already parse find-handoffs's output see a familiar shape here rather
than a third convention. Both are carried (not just one) because they
answer two different questions an LLM orchestrator asks: mtime_ts (a raw
float epoch, exactly what Path.stat().st_mtime returns, no rounding) is
an unambiguous magnitude for "which of these is newest" with no date
parsing; mtime_iso is a calendar date usable directly for a windowing
question like "is this within the last 90 days" without first
epoch-decoding anything. Neither field is derived from "now" -- both are
facts about the file itself, so two runs against an unchanged filesystem
emit byte-identical output regardless of when they are run. A THIRD,
"now"-relative field (e.g. a precomputed age_days) was considered and
rejected: it would make the verb's output non-deterministic across two
runs of an unchanged tree (a fact this discovery primitive should not
own), and neither of "newest" nor "within N days" actually needs it --
"newest" is a plain magnitude comparison on mtime_ts, and a window is a
comparison against a cutoff date the orchestrator derives once, not per
file.

"matches_by_recency" is the SAME list "matches" carries, re-sorted
most-recent mtime_ts first (ties broken by "file" for determinism,
mirroring find-handoffs's own tie-break-by-path convention exactly).
Always present, unconditionally, alongside "matches" -- not behind a
flag and not swapped in for "matches"'s existing order. This was the
additive-safe choice among three read: (1) a --sort flag choosing which
single order "matches" carries, (2) a --sort flag adding a *second* key
only when passed, (3) always emitting both. (1) risks a Class-A call
site silently keeping its old behavior only because nobody remembered to
pass the flag, and (2) still requires every Class-B prose site to learn
and pass a new flag to get a key that costs nothing to always compute
(the mtime stat already ran for every match regardless; sorting an
already-tiny list is negligible). (3) needs zero new flag, cannot regress
a Class-A call site's existing "matches" order by construction (the key
is genuinely NEW, matching this file's committed contract), and lets
Class-B's own prose migration (not built here) read "matches_by_recency"
directly with no CLI change to make first. A caller wanting the single
most recent feature dir reads matches_by_recency[0]["feature_dir"]; a
90-day-window "top 5" read is a slice of matches_by_recency filtered on
mtime_ts against a cutoff the caller computes once. No separate
recency-ordered feature_dirs list is added: the existing "feature_dirs"
key stays tied to "matches"'s layout order exactly as committed, and a
directory-level recency view was left out as unneeded speculative
surface -- every currently-named Class-B need is already answered by
matches_by_recency's per-match feature_dir field.

A file that vanishes between discovery and this verb's own mtime stat
(a genuine TOCTOU race -- a concurrent process deletes or replaces it)
drops that match silently: no exception escapes, and the match is
omitted from "matches", "feature_dirs" and "matches_by_recency" alike,
consistent with the verb's existing empty/partial-result-is-not-an-error
contract. A partial result from a filesystem race is not distinguishable
from "the file was never there" from this output alone -- a caller that
needs that distinction must stat the specific path itself, same
limitation _shared/feature_alloc.py's iter_feature_dirs documents for
its own OSError-means-absent collapsing.

--limit N: capping the population (91-FEATURE-DIR-IDENTITY-AND-
PROVENANCE-PLAN.md Phase 1b, second follow-up)
-----------------------------------------------------------------------
Why: a Class-B consumer with no single sentinel calls --filenames '["*"]'
-- one record per FILE per feature dir. At fifty features that is
thousands of records across two keys, for a caller that wants one
string (the newest feature_dir) or a handful (a windowed top-5). --limit
caps the emitted population instead of pushing a shell-redirect-plus-
python3-extraction workaround onto command prose with no python3
dependency today.

Absent by default = "no cap", the exact pre-existing behavior
byte-for-byte. When given, MUST be a base-10 integer >= 0; anything else
(non-integer, negative) is a clean EXIT_ERR (see _parse_limit) -- NOT
argparse type=int, whose own failure exits 2, a second and wrong
error-code convention for this file. --limit 0 is valid (an empty
result, not an error), the same contract zero matches already has.

Applied AFTER ordering, never before: the caller wants the N NEWEST
records. The SET is chosen ONCE, by recency -- matches_by_recency
(built over every match, before any cap) sliced to its first N -- and
every key presents that SAME set through its own pre-existing rule,
never three independently-capped populations that could disagree:
  - "matches_by_recency" -- the slice itself (already recency-order).
  - "matches" -- the same set, filtered out of the full layout-ordered
    list, so survivors keep matches's OWN order (layout), not the
    recency order used to pick them; only the POPULATION shrinks.
  - "feature_dirs" -- re-derived from the (capped) "matches" by the
    unchanged rule (dedup, first-seen order). It is a VIEW of matches,
    not an independent population -- capping matches first is
    sufficient; no limit-aware dedup logic exists or is needed.
That is what "consistent" means under a limit: one recency-selected set,
three existing presentations, never three independent caps.

--limit counts MATCH RECORDS (files), not feature directories: if the N
newest records land in fewer than N distinct dirs, "feature_dirs"
legitimately has fewer than N entries (the existing dedup rule on a
smaller input) -- exactly what --filenames '["*"]' --limit 1 wants: the
single most recently touched file and which directory it lives in,
regardless of how many other files that directory also holds. N >= the
total match count is a no-op: every key ends up identical to --limit's
absence (the slice `[:N]` keeps everything when N exceeds the length).

feature_dirs_by_recency was reconsidered (a real consumer now exists)
and still NOT added: --limit 1 already hands that consumer the single
most recent record's feature_dir directly, and --limit 5's window-filter
case reads feature_dir per record off matches_by_recency the same way --
neither needs a pre-deduplicated directory list. The earlier YAGNI call
stands, now for a demonstrated reason: --limit plus the existing
feature_dir field closes the gap the real consumer hit.

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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

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


def _file_mtime(path):
    # type: (Path) -> Optional[float]
    """path's mtime in epoch seconds, or None if it cannot be stat'd.

    None on any OSError -- e.g. the file vanished between discovery (the
    is_file() check already performed by find_feature_dirs_with or this
    module's own glob-matching loop) and this call, a genuine TOCTOU
    race. Never raises. The caller drops the match entirely rather than
    emitting a record with a missing or fabricated mtime -- the same
    absent-not-fake discipline 91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-
    PLAN.md D9 states for _specify/_render.py's own provenance line: a
    value that cannot be honestly known is omitted, never faked.
    """
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _mtime_iso(mtime_ts):
    # type: (float) -> str
    """UTC 'Z' ISO-8601 string for mtime_ts.

    Same field shape ("%Y-%m-%dT%H:%M:%SZ") _specify/_cmds_handoff.py's
    cmd_find_handoffs already emits for its own mtime_iso field -- see
    this module's docstring for why the field NAME and FORMAT are
    deliberately reused rather than invented fresh.
    """
    return datetime.fromtimestamp(mtime_ts, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def _parse_limit(raw):
    # type: (Optional[str]) -> Tuple[Optional[int], Optional[str]]
    """Parse --limit's raw string value.

    Returns (limit, error). raw is None (flag absent) -> (None, None):
    "no cap", the exact pre-existing default. Otherwise raw must be a
    base-10 integer >= 0; a non-integer string or a negative value
    returns (None, <message>) -- the caller reports it as a clean
    EXIT_ERR, matching this verb's other hand-validated inputs rather
    than argparse's own type=int failure (a different, wrong exit code
    for this file's convention). int() tolerates surrounding whitespace
    the same way it always does; no extra stripping is performed here.
    """
    if raw is None:
        return None, None
    try:
        value = int(raw)
    except ValueError:
        return None, "--limit must be an integer, got {0!r}".format(raw)
    if value < 0:
        return None, "--limit must be >= 0, got {0}".format(value)
    return value, None


def _record_match(matches, seen, feature_dir, file_path, filename, install_root):
    # type: (List[Dict[str, Any]], Set, Path, Path, str, Path) -> None
    """Append one match dict, or silently skip it.

    Skipped (not appended) in two cases, neither an error: the (dir,
    file) pair was already recorded (an overlapping --filenames entry or
    a repeated literal), or the file could not be stat'd for mtime (a
    TOCTOU race -- see _file_mtime). A race is NOT added to `seen`: a
    transient failure should not permanently suppress a later, different
    pattern's attempt to record the same file.
    """
    key = (str(feature_dir), str(file_path))
    if key in seen:
        return
    mtime_ts = _file_mtime(file_path)
    if mtime_ts is None:
        return
    seen.add(key)
    matches.append({
        "feature_dir": _relative_posix(feature_dir, install_root),
        "file": _relative_posix(file_path, install_root),
        "filename": filename,
        "mtime_ts": mtime_ts,
        "mtime_iso": _mtime_iso(mtime_ts),
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

    limit, limit_err = _parse_limit(getattr(args, "limit", None))
    if limit_err is not None:
        sys.stderr.write("find-feature-artifacts: {0}\n".format(limit_err))
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

    matches = []  # type: List[Dict[str, Any]]
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

    # Additive, always present -- see the module docstring's "mtime, and
    # two output orders" section for why this is unconditional rather
    # than flag-gated. Built over EVERY discovered match, before any
    # --limit is applied -- the cap always selects from the full
    # recency-ordered population, never a pre-truncated one.
    matches_by_recency_full = sorted(
        matches, key=lambda m: (-m["mtime_ts"], m["file"])
    )

    # --limit N (see the module docstring's "capping the population"
    # section for the full coherence rule): ONE set, chosen by recency,
    # presented through each key's own pre-existing order/derivation.
    # limit is None (flag absent) -> no cap, byte-identical to before
    # --limit existed: matches_capped IS matches (same object, same
    # order) and matches_by_recency_capped IS the full sorted list.
    if limit is None:
        matches_capped = matches
        matches_by_recency_capped = matches_by_recency_full
    else:
        matches_by_recency_capped = matches_by_recency_full[:limit]
        kept = {(m["feature_dir"], m["file"]) for m in matches_by_recency_capped}
        matches_capped = [
            m for m in matches if (m["feature_dir"], m["file"]) in kept
        ]

    # feature_dirs is a VIEW of (capped) matches -- same dedup/first-seen
    # rule as always, just fed fewer records under a limit. No separate
    # limit-aware dedup logic: capping matches first makes this
    # unconditional loop correct in both the limited and unlimited case.
    feature_dir_list = []  # type: List[str]
    feature_dir_seen = set()  # type: Set[str]
    for m in matches_capped:
        if m["feature_dir"] not in feature_dir_seen:
            feature_dir_seen.add(m["feature_dir"])
            feature_dir_list.append(m["feature_dir"])

    result_obj = {
        "matches": matches_capped,
        "feature_dirs": feature_dir_list,
        "matches_by_recency": matches_by_recency_capped,
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
    parser.add_argument(
        "--limit",
        default=None,
        help=(
            "Cap the emitted population to the N most recent records "
            "(by mtime), applied to \"matches\", \"feature_dirs\" and "
            "\"matches_by_recency\" coherently -- one recency-selected "
            "set, presented in each key's own existing order. Omit for "
            "the pre-existing unbounded behavior (the default). Must be "
            "a base-10 integer >= 0; 0 is valid (an empty result, not an "
            "error). Not declared as an int type here so a malformed "
            "value fails this verb's own EXIT_ERR convention rather than "
            "argparse's separate exit code."
        ),
    )
