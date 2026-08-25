"""_merge -- 2-pass union merge for /devforge:grill validated findings.

Grill dispatches a single devils-advocate finder run twice and needs ONE
working findings list to feed the refutation stage. The model here is
/devforge:audit's plan-12 `--passes N` union merge
(`_audit/_merge.merge_passes`, read for SHAPE, deliberately NOT imported or
reused -- see merge_two_passes()'s docstring for why). Unlike audit, grill
has exactly one finder, so there is no cross-agent corroboration signal to
compute; the only axis here is cross-pass UNION.

This is explicitly NOT plan 62's spec-formalizer 2-pass quorum -- that
mechanism is a MAJORITY rule: a finding must reproduce across both passes
to be confirmed, which SUPPRESSES anything that only fired once. This
module does the opposite on purpose: UNION, not intersection, not
majority. A finding present in exactly ONE pass MUST survive. Catching an
attack line that only fired on one generation is the entire point of
running 2 passes -- an intersection or majority rule would silently
discard exactly the findings this exists to protect. This distinction was
raised and corrected at plan 85's ratification specifically so a future
reader would not rebuild spec-check's rule here from the word "quorum".

This module is deliberately a fixed 2-pool merge, not an N-pass
generalization; see merge_two_passes()'s signature. If a later phase needs
N passes, it can widen this function then.

Stdlib only. Python 3.8+.
"""

from typing import Dict, List, Optional, Tuple


def _identity_key(finding: dict) -> Tuple[str, Optional[int], str]:
    """(file, line, pattern) -- see merge_two_passes()'s docstring for why."""
    return (
        finding.get("file", ""),
        finding.get("line", None),
        finding.get("pattern", ""),
    )


def merge_two_passes(pass_a: List[dict], pass_b: List[dict]) -> List[dict]:
    """Union-merge exactly 2 passes' validated-findings lists, deduped.

    Parameters
    ----------
    pass_a, pass_b : list of dict
        Each element is a validated ParsedFinding dict -- the shape
        `_shared._validate.validate_findings` returns in its "passed" list
        (and so, unchanged, the shape `_shared._consume.parse_agent_tmp`
        originally produced): agent, severity, file, line, pattern,
        confidence, evidence, why, remediation, category, tags.

    Returns
    -------
    list of dict
        All of pass_a's findings, in order, followed by any pass_b finding
        whose identity key was not already seen in pass_a. Pure function:
        neither input list nor any finding dict is mutated or copied --
        each returned dict is the SAME object reference as in its source
        pool.

    Identity key for dedup: (file, line, pattern).

    Reasoning
    ---------
    - `file` + `line` pin the exact code location a finding cites. Grill's
      finder must verbatim-quote its `evidence` from that location
      (`_shared._validate`'s quote_mismatch check enforces this upstream),
      so an identical (file, line) pair recurring across 2 independent
      passes strongly indicates the same underlying code is being
      flagged.
    - `pattern` is the finder's terse, template-shaped one-line label for
      the defect (e.g. "SQL injection via string concatenation"). It is
      INCLUDED on the (weaker, stated-as-a-bet-not-a-fact) reasoning that a
      template-shaped label is somewhat more likely to stay stable across
      independent re-generations of the SAME real defect than `why` /
      `remediation` (free-form prose that legitimately rewords between
      passes even when describing the identical issue) -- but this is not
      backed by evidence from grill itself, and there is real prior art in
      this repo arguing the opposite: `_audit/_merge.py`'s cross-pass
      clustering deliberately EXCLUDES pattern from its identity and
      clusters by file + line-PROXIMITY instead, with its own docstring
      stating "Pattern differences within a cluster are intentionally
      ignored". That module solves a related-but-different problem
      (location-tolerant clustering across MULTIPLE agents, not an exact
      2-pass dedup for a single agent), so its choice does not directly
      transfer, but it is a real counter-signal and this key's confidence
      is stated accordingly: informed, not proven. See the trade-off
      paragraph below for the failure-direction argument that holds either
      way.
    - `evidence` is deliberately EXCLUDED: it is a verbatim file quote
      whose exact span can differ between two honest reports of the same
      defect (one pass may quote 2 lines, the other 4 including those 2).
      Including it would cause FALSE splits -- the same defect surviving
      as two entries.
    - `why` / `remediation` are excluded for the same reason (free-form
      prose, not identity).
    - `agent` is excluded: grill dispatches a single finder
      (devils-advocate), so it is constant across both passes and adds
      nothing to the key.
    - `severity` / `confidence` / `category` are excluded: they classify
      the defect, they are not part of its identity -- two passes rating
      the same defect at different confidence must not be treated as two
      different defects.

    Not comparable precedent: `_shared/_verify.py`'s `_verdict_key` also
    keys on (file, line, pattern, agent), but it matches a REFUTER's
    verdict block back to the finding whose Pattern the refuter was
    instructed to copy VERBATIM -- a different, much stronger reliability
    regime than two independent finder passes generating their own
    wording. Do not cite it as support for pattern's stability here.

    Trade-off, stated explicitly: this key is narrower than "every field
    matches" and wider than "file+line alone". A wider key (bare
    file+line) risks silently COLLAPSING two genuinely different defects
    that happen to land on the same line into one entry -- a silent data
    loss. The chosen key accepts the opposite, safer failure instead: two
    honest reports of the SAME defect that happen to phrase `pattern`
    differently will survive as two visible entries (a human-visible
    duplicate, not a silent drop) rather than one vanishing -- and this
    module's own tests pin exactly that case (see
    tests/lib/_grill/test_merge.py's differently-worded-pattern test), so a
    later switch to a file+line-only key would fail a test rather than
    silently flipping the failure direction.
    """
    result = list(pass_a)
    seen = set(_identity_key(f) for f in pass_a)
    for finding in pass_b:
        key = _identity_key(finding)
        if key not in seen:
            result.append(finding)
            seen.add(key)
    return result
