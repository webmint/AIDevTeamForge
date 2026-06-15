"""_consensus -- cross-agent consensus merge for ParsedFinding records.

Implements §4.3 of the /audit spec: exact-match consensus via SHA-1 hash
of (file_path, line_number, normalised_pattern).

Algorithm:
  1. Hash key = sha1(file + ":" + str(line) + ":" + normalise(pattern))
     normalise = lowercase + strip all punctuation chars
  2. Group findings by hash key.
  3. A group with ≥ 2 findings from DIFFERENT agent names → consensus.
     - Keep the finding with the highest severity (by SEVERITY_ENUM rank).
     - Tag it [CROSS-AGENT].
     - Bump severity one level (Info→Medium→High→Critical, capped at Critical).
  4. Singletons and same-agent duplicates pass through unchanged (no merge).

Tie-break for "highest severity": SEVERITY_ENUM order (Critical=0, High=1,
Medium=2, Info=3) — lower index = higher severity.  When multiple findings
share the same highest severity, the one with alphabetically first agent
name is kept for determinism.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import hashlib
import re
import string
from typing import List

from _shared.findings_schema import SEVERITY_ENUM  # type: ignore[import]

# ---------------------------------------------------------------------------
# Severity helpers (shared with _rank.py via _bump_severity)
# ---------------------------------------------------------------------------

# SEVERITY_ENUM = ("Critical", "High", "Medium", "Info") — index 0 is highest.
_SEV_RANK = {s: i for i, s in enumerate(SEVERITY_ENUM)}  # Critical=0 .. Info=3


def _bump_severity(severity, levels=1):
    # type: (str, int) -> str
    """Return severity bumped up by ``levels`` steps, capped at Critical.

    "Up" means towards Critical (lower index in SEVERITY_ENUM).
    If severity is not in SEVERITY_ENUM, it is returned unchanged.

    Examples:
        _bump_severity("Info", 1) → "Medium"
        _bump_severity("High", 1) → "Critical"
        _bump_severity("Critical", 1) → "Critical"   (capped)
        _bump_severity("Medium", 2) → "Critical"     (capped)
    """
    if severity not in _SEV_RANK:
        return severity
    current_idx = _SEV_RANK[severity]
    new_idx = max(0, current_idx - levels)
    return SEVERITY_ENUM[new_idx]


# ---------------------------------------------------------------------------
# Normalise pattern for hashing
# ---------------------------------------------------------------------------

_PUNCT_TABLE = str.maketrans("", "", string.punctuation)


def _normalise_pattern(pattern):
    # type: (str) -> str
    """Lowercase and strip all punctuation from a pattern string."""
    return pattern.lower().translate(_PUNCT_TABLE)


# ---------------------------------------------------------------------------
# Hash key
# ---------------------------------------------------------------------------

def _make_hash_key(finding):
    # type: (dict) -> str
    """Return the SHA-1 hex digest key for a ParsedFinding dict."""
    file_path = finding.get("file", "") or ""
    line_no = finding.get("line", 0)
    pattern = finding.get("pattern", "") or ""
    raw = "{0}:{1}:{2}".format(
        file_path,
        str(line_no),
        _normalise_pattern(pattern),
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_consensus(findings):
    # type: (List[dict]) -> dict
    """Merge findings from multiple agents into a deduplicated list.

    Returns a dict with keys:
      findings      : list of ParsedFinding dicts (merged where consensus exists)
      consensus_map : {hash_key: [agent_name, ...]} for merged findings only
    """
    import copy

    # Build groups keyed by hash
    groups = {}  # type: dict
    order = []   # preserve insertion order for output stability

    for finding in findings:
        key = _make_hash_key(finding)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(finding)

    result_findings = []
    consensus_map = {}

    for key in order:
        group = groups[key]
        distinct_agents = sorted(set(f.get("agent", "") for f in group))

        if len(distinct_agents) >= 2:
            # Consensus: merge
            merged = _merge_group(group)
            # Tag [CROSS-AGENT]
            tags = list(merged.get("tags", []) or [])
            if "[CROSS-AGENT]" not in tags:
                tags.append("[CROSS-AGENT]")
            merged = dict(merged)
            merged["tags"] = tags
            # Bump severity one level
            merged["severity"] = _bump_severity(merged.get("severity", "Info"), 1)
            result_findings.append(merged)
            consensus_map[key] = distinct_agents
        else:
            # No consensus: include all findings as-is (may be >1 same-agent dups)
            for finding in group:
                result_findings.append(copy.deepcopy(finding))

    return {
        "findings": result_findings,
        "consensus_map": consensus_map,
    }


def _merge_group(group):
    # type: (List[dict]) -> dict
    """Select the best representative finding from a consensus group.

    "Best" = highest severity (lowest SEVERITY_ENUM index).
    Tie-break: alphabetically first agent name.
    Returns a deep copy of the selected finding.
    """
    import copy

    def _sort_key(f):
        sev = f.get("severity", "Info")
        sev_idx = _SEV_RANK.get(sev, len(SEVERITY_ENUM))
        agent = f.get("agent", "")
        return (sev_idx, agent)

    best = min(group, key=_sort_key)
    return copy.deepcopy(best)
