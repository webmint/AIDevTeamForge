"""Topic-token + filename-match helpers + source-origin path tagging."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple


_TOPIC_TOKEN_RE = re.compile(r"[a-z0-9]+")
_TOPIC_MIN_TOKEN_LEN = 3
# Common date-prefix tokens that exist on every dated filename — match on
# these alone yields false positives.
_TOPIC_STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "into", "this", "that",
})

# 68-INTAKE-OWNS-FEATURE-DIR-PLAN.md D2 -- the two intake report basenames
# that now live INSIDE specs/NNN-slug/, side-by-side with the spec's own
# prior_spec artifacts (spec.md, handoff.json, plan.md, ...). Filename-aware
# dispatch (not prefix-based) is required because both share the "specs/"
# prefix with prior_spec files -- a prefix-only test would silently mis-tag
# them "prior_spec" (this was flagged as the plan's single highest-risk
# edit). Shared by source_origin_for_path below and
# _cmds_phase01._group_for_path so the two classifiers cannot drift apart.
#
# 91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md: the two functions answer
# DIFFERENT questions (source_origin_for_path returns a 4-way provenance
# tag; _group_for_path returns a render-heading key, and collapses several
# distinct provenance tags' worth of context files under their OWN
# per-file headings rather than one shared bucket) -- they are correctly
# NOT merged into one function. What they share, and what used to be
# duplicated independently in each, is normalize_source_path below: strip
# + "./"-prefix removal + (given a root) absolute-to-root-relative
# rebasing. Both classifiers call it as their first step so an absolute
# and a repo-relative spelling of the same file feed the SAME string into
# each one's own (still-independent, still-correct-to-be-independent)
# prefix/basename rules.
RESEARCH_REPORT_BASENAME = "research-report.md"
DISCOVERY_REPORT_BASENAME = "discovery-report.md"


def topic_tokens(topic: str) -> List[str]:
    """Tokens from a free-form topic string (≥3 alnum chars, not stopword)."""
    out = []
    for t in _TOPIC_TOKEN_RE.findall(topic.lower()):
        if len(t) < _TOPIC_MIN_TOKEN_LEN:
            continue
        if t in _TOPIC_STOPWORDS:
            continue
        if t.isdigit() and len(t) == 4:
            continue
        out.append(t)
    return out


def filename_tokens(filename: str) -> List[str]:
    """Tokens from a filename stem (extension dropped)."""
    stem = Path(filename).stem.lower()
    out = []
    for t in _TOPIC_TOKEN_RE.findall(stem):
        if len(t) < _TOPIC_MIN_TOKEN_LEN:
            continue
        if t in _TOPIC_STOPWORDS:
            continue
        if t.isdigit() and len(t) == 4:
            continue
        out.append(t)
    return out


def filename_matches_topic(filename: str, topic: str) -> bool:
    """Filename has ≥1 token overlap with task-topic tokens.

    Deterministic; no LLM. Used by orchestrator (or callers) to decide
    which research/, discover/, specs/ files to enumerate in Phase 1.
    Variance rule #5: no LLM re-interpretation in adapter — filename only,
    no content match.
    """
    return bool(set(topic_tokens(topic)) & set(filename_tokens(filename)))


def source_origin_for_path(path: str, root: Optional[str] = None) -> str:
    """Auto-tag source_origin from file path. Variance rule #5.

    68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 4: /research and /discover now
    write their durable intake artifacts INSIDE specs/NNN-slug/ (D1/D2/D7)
    instead of top-level research/ or discover/ dirs. specs/*/research-
    report.md and specs/*/discovery-report.md must therefore be checked by
    FILENAME before the generic "specs/" prefix is allowed to fall through
    to prior_spec -- otherwise every new intake report would silently
    mis-tag as prior_spec (no error, just degraded corpus grouping).

    The legacy top-level "discover/" and "research/" prefix checks are kept
    for origin-TAGGING only (D3 clean cut: they exist so a pre-migration
    consumer's already-on-disk research/ or discover/ files -- never
    deleted, D3 -- still tag correctly if read; find-handoffs itself never
    globs those directories, so this is not a discovery path for new work).

    `root`, 91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md: a path names a
    file, so the same file must classify identically whichever way it is
    spelled. `find-handoffs` emits absolute `handoff_path` values (off a
    `.resolve()`d root), and Phase 1's `<feature_dir>`-token reads pass
    those straight to `record-input-read` -- an absolute spelling of a
    `specs/.../research-report.md` file must therefore classify exactly
    as the repo-relative spelling does, not fall through to "context" for
    no reason but how the caller wrote the path.

    When `root` is given and `path` is absolute, `path` is first
    re-expressed relative to `root` (Path.relative_to -- pure component
    comparison, no filesystem access, matching this package's existing
    `_cmds_handoff._root_relative` convention) and the SAME prefix/
    filename rules below are then applied to that relative form, so the
    legacy "discover/" and "research/" prefixes get identical
    absolute-vs-relative treatment as "specs/" -- there is no reason for
    identity-consistency to stop at one prefix. An absolute path that is
    NOT under `root` (a different checkout, a sibling path, or -- on a
    case where the two share no common ancestor -- an unrelated tree)
    returns "context" unconditionally: it must never borrow `root`'s
    classification for a same-named file that isn't actually part of
    this install.

    `root` is optional and defaults to None, which reproduces the exact
    prior behaviour (an absolute `path` falls through every prefix check
    to "context", as it always did) -- callers that never see absolute
    paths, including every existing test in this suite, are unaffected.

    Purity note: this function does not itself call `.resolve()` or stat
    the filesystem, so it stays pure -- but it also does not resolve `..`
    segments or symlinks, so a caller wanting identity-correct results
    for such paths must pass an already-canonical `root` AND an
    already-canonical `path` (the production caller does exactly that:
    `record-input-read` resolves `--devforge-dir` before deriving `root`,
    and `find-handoffs` already resolves the paths it emits).
    """
    p, in_root = normalize_source_path(path, root)
    if not in_root:
        return "context"
    return _classify_relative(p)


def normalize_source_path(
    path: str, root: Optional[str] = None,
) -> Tuple[str, bool]:
    """Shared first step for source_origin_for_path AND _group_for_path.

    Strips whitespace and a leading "./", then -- when `root` is given
    and the result is an absolute path -- re-expresses it relative to
    `root` (Path.relative_to: pure component comparison, no filesystem
    access, matching this package's existing `_cmds_handoff._root_relative`
    convention).

    Returns (normalized, in_root). `in_root` is False EXACTLY when `path`
    is absolute, `root` was given, and `path` does not lie under `root`
    (a different checkout, a sibling path, or an unrelated tree); in that
    case `normalized` is the stripped ABSOLUTE original, unchanged --
    callers must not run it through their own prefix/basename rules, since
    it was never rebased and would risk colliding with an unrelated
    same-named prefix. Each caller picks its own "doesn't belong here"
    fallback: source_origin_for_path returns "context" outright;
    _group_for_path (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md) uses
    `normalized` itself as a private, non-borrowing render-group key --
    the same "own group" fallback it already gives any other path that
    matches none of its prefixes.

    In every other case `in_root` is True and `normalized` is ready for a
    caller's own relative-path classification: unchanged when `path` was
    already relative (or `root` was None), or the root-relative POSIX
    string when it was absolute and under `root`.
    """
    p = path.strip()
    if p.startswith("./"):
        p = p[2:]
    if root is not None and Path(p).is_absolute():
        rel = _root_relative_or_none(p, root)
        if rel is None:
            return p, False
        return rel, True
    return p, True


def _root_relative_or_none(p: str, root: str) -> Optional[str]:
    """POSIX-style `p` relative to `root`, or None when `p` is not under it."""
    try:
        return Path(p).relative_to(Path(root)).as_posix()
    except ValueError:
        return None


def _classify_relative(p: str) -> str:
    """Prefix/filename classification for an already-relative path."""
    if p.startswith("specs/"):
        basename = p.rsplit("/", 1)[-1]
        if basename == RESEARCH_REPORT_BASENAME:
            return "research"
        if basename == DISCOVERY_REPORT_BASENAME:
            return "discover"
        return "prior_spec"
    if p.startswith("discover/"):
        return "discover"
    if p.startswith("research/"):
        return "research"
    return "context"
