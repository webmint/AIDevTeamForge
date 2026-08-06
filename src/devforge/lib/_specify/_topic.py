"""Topic-token + filename-match helpers + source-origin path tagging."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List


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


def source_origin_for_path(path: str) -> str:
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
    """
    p = path.strip()
    if p.startswith("./"):
        p = p[2:]
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
