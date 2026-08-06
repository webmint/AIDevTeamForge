"""Intake handoff importer for pr_review_helper (PR-REVIEW Step 6).

`run(target, pr_number, devforge_dir)` is the Phase 4b entry point.

It reads state.json (written by Step 3 intake), scans
<target>/specs/*/{research-handoff.json,discover-handoff.json} (the
68-INTAKE-OWNS-FEATURE-DIR-PLAN.md D2/D7 unified layout), filters by
relevance to state.ticket_text or PR title, and APPENDS/REPLACES the
`research_handoffs` key in state.bundle.

## Re-point note (68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 5, D3 clean cut)

Both intake lanes now write inside the feature dir they allocate:
`specs/NNN-slug/research-handoff.json` (the `/research` lane) and
`specs/NNN-slug/discover-handoff.json` (the `/discover` lane). This module
reads ONLY the new layout — the old top-level `<target>/research/<date>-
<slug>/handoff.json` dirs are never scanned again (D3: no dual-glob
transition code; old installs' pre-migration `research/` dirs are simply
invisible to this scanner now, matching `/specify`'s `find-handoffs`
re-point). Discover-lane handoffs are a NEW addition here — the pre-68
version of this module scanned research only; discover is added because
every consumer of `state.bundle["research_handoffs"]` (`_dispatch.py`'s
render step, this module's own filter) is kind-agnostic: it renders
whatever slug/date/verdict/mode/matched_via/excerpt fields are present
without branching on which lane produced them. The bundle key stays named
`research_handoffs` (renaming it would be a wider, out-of-scope schema
change touching `_dispatch.py` + `_bundle.py` + `pr-review/main.md`); a
new per-entry `kind` field (`"research"` or `"discover"`) disambiguates
provenance for the Step 8 LLM consumer.

## research_handoffs schema (helper-owns; LLM at Step 8 consumes it)

After import-handoffs, state.bundle["research_handoffs"] contains:

    [
        {
            "path": "<absolute path to research-handoff.json / discover-handoff.json>",
            "date": "YYYY-MM-DD",
            "slug": "<feature slug, from the specs/NNN-slug/ dir name>",
            "verdict": "<see per-kind extraction below>",
            "mode": "<top-level 'mode' from the handoff, or '' (discover has none)>",
            "kind": "research" | "discover",
            "matched_via": "ticket_text_substring" | "title_substring" | "all",
            "content_excerpt": "<first 5000 chars of the handoff JSON>"
        },
        ...
    ]

`date` is read from the handoff's own completion timestamp
(`research_completed_at` for research-handoff.json, `discover_completed_at`
for discover-handoff.json) — the new `NNN-slug` feature-dir name carries no
date, unlike the old `YYYY-MM-DD-slug` research dir name.

`verdict` extraction is kind-aware (research and discover carry the concept
in different places):
  research-handoff.json:  top-level 'verdict' (future-proofing) > top-level
                           'mode' > ""
  discover-handoff.json:  nested 'discovery_block.verdict' (the D-mirror
                           build-vs-buy verdict) > top-level 'mode'
                           (absent on discover today, so this is a
                           forward-compat fallback) > ""

`matched_via` values:
  "ticket_text_substring" — the feature slug or handoff mode/verdict
                            contains a substring of state.ticket_text.
  "title_substring"       — the feature slug contains a substring
                            of the PR title (from state.pr_body header
                            or state.repo field).
  "all"                   — no filter criteria available (ticket_text and
                            pr_title both empty); all handoffs returned.

## Filtering

Substring matching is case-insensitive. The filter checks whether `slug`
(the feature-dir name with its `NNN-` prefix stripped) contains any word
from ticket_text or PR title (split on whitespace, minimum 3 chars).

If both ticket_text and a derivable PR title are empty, the filter is
skipped and all handoffs are returned with matched_via="all".

## Bounds

- Handoffs are sorted most-recent-first by date (from the handoff's own
  completion timestamp — see above).
- Capped at _MAX_HANDOFFS = 20 after filtering.

## Re-invocation semantics

Running import-handoffs REPLACES state.bundle["research_handoffs"] on
each invocation. Prior values are discarded.

## CBM constraint

This module does NOT call CBM / MCP tools. All data comes from the
local filesystem. Does NOT invoke `gh` or any subprocess.

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import dataclasses
import json
import os
import tempfile
from typing import Dict, List, Optional

from _shared.feature_alloc import SPEC_NUMBER_DIR_RE  # type: ignore[import]

from ._state import PRReviewState, state_path


# ---------------------------------------------------------------------------
# Constants.
# ---------------------------------------------------------------------------

_MAX_HANDOFFS = 20
_EXCERPT_CHARS = 5000
_MIN_FILTER_TOKEN_LEN = 3   # tokens shorter than this are ignored in filter

# The two intake handoff filenames a feature dir may carry (68-INTAKE-OWNS-
# FEATURE-DIR-PLAN.md D2), keyed to the `kind` value each produces.
_INTAKE_HANDOFF_KINDS = (
    ("research-handoff.json", "research"),
    ("discover-handoff.json", "discover"),
)


# ---------------------------------------------------------------------------
# specs/ directory scanner.
# ---------------------------------------------------------------------------


def _scan_specs_dir(target: str) -> List[str]:
    """Return sorted list of intake handoff paths under <target>/specs/.

    Scans every `specs/<feature-dir>/` subdirectory for
    `research-handoff.json` and `discover-handoff.json` (68-INTAKE-OWNS-
    FEATURE-DIR-PLAN.md D2/D7 unified layout — both lanes write inside the
    feature dir they allocate). Unlike `/specify`'s `find-handoffs`, this
    scanner does NOT filter out feature dirs that already contain
    `spec.md` — pr-review wants historical research context regardless of
    whether the feature's spec was ever finished.

    Args:
        target: Absolute path to the repository root.

    Returns:
        List of absolute paths to research-handoff.json / discover-
        handoff.json files (may be empty).
    """
    specs_dir = os.path.join(target, "specs")
    if not os.path.isdir(specs_dir):
        return []

    try:
        entries = os.listdir(specs_dir)
    except OSError:
        return []

    paths = []
    for name in entries:
        subdir = os.path.join(specs_dir, name)
        if not os.path.isdir(subdir):
            continue
        for filename, _kind in _INTAKE_HANDOFF_KINDS:
            hf_path = os.path.join(subdir, filename)
            if os.path.isfile(hf_path):
                paths.append(hf_path)

    paths.sort()
    return paths


# ---------------------------------------------------------------------------
# Handoff parser.
# ---------------------------------------------------------------------------


def _parse_handoff(path: str) -> Optional[Dict]:
    """Parse a handoff.json file and extract key metadata.

    Returns a dict with keys: path, date, slug, verdict, mode, kind.
    Returns None on any parse error (fail-soft).

    `kind` is derived from the filename: "research-handoff.json" ->
    "research", "discover-handoff.json" -> "discover"; any other filename
    (a foreign/hand-placed file) defaults to "research" (the pre-68
    default kind, preserved for fail-soft tolerance).

    The parent dir name is expected to be the plan-68 feature-dir shape
    `NNN-<slug>` (e.g. `003-checkout-flow`) — see `SPEC_NUMBER_DIR_RE`. If
    the name does not match, `slug` falls back to the full dir name
    (fail-soft — a foreign/non-conforming dir still parses).

    `date` is read from the handoff's own completion timestamp
    (`research_completed_at` for a research-handoff.json,
    `discover_completed_at` for a discover-handoff.json), truncated to the
    first 10 chars (the ISO date prefix of an ISO 8601 timestamp) — the
    new `NNN-slug` dir name carries no date, unlike the retired
    `YYYY-MM-DD-slug` research dir name.

    The `verdict` output field uses a kind-aware fallback chain (research
    and discover carry the concept in different places):
      research:  handoff['verdict'] (future-proofing) > handoff['mode'] > ""
      discover:  handoff['discovery_block']['verdict'] > handoff['mode']
                 (absent on discover today; forward-compat fallback) > ""

    Args:
        path: Absolute path to a research-handoff.json / discover-
              handoff.json file.

    Returns:
        Metadata dict, or None on failure.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = fh.read()
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None

    filename = os.path.basename(path)
    kind = "discover" if filename == "discover-handoff.json" else "research"

    # Extract slug from the parent feature-dir name: NNN-<slug>.
    dir_name = os.path.basename(os.path.dirname(path))
    dir_match = SPEC_NUMBER_DIR_RE.match(dir_name)
    slug = dir_match.group(2) if dir_match else dir_name

    date = ""
    verdict = ""
    mode = ""
    if isinstance(data, dict):
        mode = str(data.get("mode", ""))
        if kind == "discover":
            discovery_block = data.get("discovery_block")
            block_verdict = (
                discovery_block.get("verdict", "")
                if isinstance(discovery_block, dict) else ""
            )
            verdict = str(data.get("verdict", block_verdict or mode))
            completed_at = str(data.get("discover_completed_at", ""))
        else:
            verdict = str(data.get("verdict", mode))
            completed_at = str(data.get("research_completed_at", ""))
        date = completed_at[:10]

    # content_excerpt: first _EXCERPT_CHARS characters of the raw JSON text.
    excerpt = _excerpt_handoff(raw)

    return {
        "path": path,
        "date": date,
        "slug": slug,
        "verdict": verdict,
        "mode": mode,
        "kind": kind,
        "content_excerpt": excerpt,
    }


# ---------------------------------------------------------------------------
# Filter helper.
# ---------------------------------------------------------------------------


def _filter_by_ticket_text(
    handoffs: List[Dict],
    ticket_text: str,
    pr_title: str,
) -> List[Dict]:
    """Filter handoffs by relevance to ticket_text or PR title.

    Splitting on whitespace, extracts tokens of >= _MIN_FILTER_TOKEN_LEN
    chars from ticket_text and pr_title. A handoff matches if its `slug`
    contains any of those tokens (case-insensitive substring match).

    When both ticket_text and pr_title are empty (no filter criteria),
    returns all handoffs with matched_via="all".

    Args:
        handoffs:    List of handoff metadata dicts from _parse_handoff.
        ticket_text: From state.ticket_text (may be empty).
        pr_title:    PR title string (may be empty).

    Returns:
        Filtered list with matched_via field added to each entry.
    """
    # Build filter tokens from both sources.
    def _tokens(text: str) -> List[str]:
        return [
            t.lower() for t in text.split()
            if len(t) >= _MIN_FILTER_TOKEN_LEN
        ]

    ticket_tokens = _tokens(ticket_text)
    title_tokens = _tokens(pr_title)

    if not ticket_tokens and not title_tokens:
        # No filter criteria: return all with matched_via="all".
        return [dict(h, matched_via="all") for h in handoffs]

    results = []
    for h in handoffs:
        slug_lower = h["slug"].lower()
        matched_via = None

        # Check ticket_text tokens first.
        if ticket_tokens:
            for tok in ticket_tokens:
                if tok in slug_lower:
                    matched_via = "ticket_text_substring"
                    break

        # If no ticket match, try title tokens.
        if matched_via is None and title_tokens:
            for tok in title_tokens:
                if tok in slug_lower:
                    matched_via = "title_substring"
                    break

        if matched_via is not None:
            results.append(dict(h, matched_via=matched_via))

    return results


# ---------------------------------------------------------------------------
# Excerpt helper (exposed for testing; called by _parse_handoff).
# ---------------------------------------------------------------------------


def _excerpt_handoff(raw_content: str, max_chars: int = _EXCERPT_CHARS) -> str:
    """Return up to max_chars characters of raw_content with truncation marker.

    Called by _parse_handoff (single canonical truncation impl).

    Args:
        raw_content: Raw string to excerpt.
        max_chars:   Character cap (default: _EXCERPT_CHARS = 5000).

    Returns:
        Truncated string (with "... [truncated]" suffix if over cap),
        or the original string if under cap.
    """
    if len(raw_content) <= max_chars:
        return raw_content
    return raw_content[:max_chars] + "... [truncated]"


# ---------------------------------------------------------------------------
# Atomic state writer.
# ---------------------------------------------------------------------------


# TODO(Step 7+): consolidate _write_state across _intake.py / _blast.py /
# _bundle.py / _handoff_import.py / _scope_drift.py (5 copies). Extract to
# _state.py.write_state when next verb would otherwise create a 6th copy.
def _write_state(target_path: str, state: PRReviewState) -> None:
    """Write PRReviewState as JSON to target_path atomically.

    Uses tempfile.mkstemp in the same directory as target_path then os.replace.
    On failure, unlinks the temp file and re-raises.

    Args:
        target_path: Absolute path to the destination state.json.
                     Parent directory must already exist.
        state:       PRReviewState instance to serialise.

    Raises:
        OSError: if the write or rename fails.
    """
    target_dir = os.path.dirname(target_path)
    fd, tmp_path = tempfile.mkstemp(
        prefix="handoff-import-", suffix=".tmp.json", dir=target_dir
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(dataclasses.asdict(state), fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp_path, target_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------


def run(
    target: str,
    pr_number: int,
    devforge_dir: str = ".devforge",
) -> dict:
    """Scan specs/ for relevant intake handoffs and write to state.bundle.research_handoffs.

    Reads state.json (written by Step 3 intake), discovers
    research-handoff.json / discover-handoff.json files under
    <target>/specs/*/, filters by relevance to state.ticket_text and PR
    title, and REPLACES state.bundle["research_handoffs"] with the
    filtered set (capped at _MAX_HANDOFFS, most-recent-first).

    Other keys in state.bundle (from bundle-context) are preserved.

    Args:
        target:       Path to the reviewer's local repo root.
        pr_number:    PR number (positive int). Used to locate state.json.
        devforge_dir: Name of the devforge directory under target.

    Returns:
        dict with keys:
            status               — "ok"
            state_path           — absolute path of the (updated) state.json
            pr_number            — int
            handoffs_found       — int (total discovered)
            handoffs_matched     — int (after filter + cap)
            filter_applied       — bool (False when no filter criteria)

    Raises:
        ValueError: if state.json is missing or cannot be parsed.
        OSError:    if the atomic write fails.
    """
    abs_target = os.path.abspath(target)
    abs_devforge = os.path.join(abs_target, devforge_dir)
    sp = state_path(abs_devforge, pr_number)

    if not os.path.exists(sp):
        raise ValueError(
            "no state.json at {path}; run `intake` first".format(path=sp)
        )

    try:
        with open(sp, "r", encoding="utf-8") as fh:
            state_dict = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(
            "cannot read state: {exc}".format(exc=exc)
        ) from exc

    try:
        state = PRReviewState(**state_dict)
    except TypeError as exc:
        raise ValueError(
            "state schema error: {exc}".format(exc=exc)
        ) from exc

    # Scan for research-handoff.json / discover-handoff.json files.
    handoff_paths = _scan_specs_dir(abs_target)

    # Parse each handoff; fail-soft on broken files.
    parsed = []
    for hf_path in handoff_paths:
        result = _parse_handoff(hf_path)
        if result is not None:
            parsed.append(result)

    handoffs_found = len(parsed)

    # Sort most-recent-first by date string (ISO dates sort lexicographically).
    parsed.sort(key=lambda h: h["date"], reverse=True)

    # Derive PR title for filter — use state.pr_body first line or empty.
    pr_title = ""
    if state.pr_body:
        pr_title = state.pr_body.strip().splitlines()[0].strip()

    # Filter by relevance.
    filtered = _filter_by_ticket_text(parsed, state.ticket_text, pr_title)
    filter_applied = bool(state.ticket_text.strip() or pr_title.strip())

    # Cap.
    capped = filtered[:_MAX_HANDOFFS]

    # Replace state.bundle["research_handoffs"]; preserve other bundle keys.
    bundle = dict(state.bundle)
    bundle["research_handoffs"] = capped
    state.bundle = bundle

    # Atomic write.
    _write_state(sp, state)

    return {
        "status": "ok",
        "state_path": sp,
        "pr_number": pr_number,
        "handoffs_found": handoffs_found,
        "handoffs_matched": len(capped),
        "filter_applied": filter_applied,
    }
