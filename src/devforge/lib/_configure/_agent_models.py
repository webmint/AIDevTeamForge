"""Pure logic for rewriting emitted `.claude/agents/*.md` frontmatter from
`.devforge/project-config.json` (92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md
D1, Phase 1 Deliverable 3).

Keyed on the emitted `model_tier: <tier>` frontmatter line
(`scripts/generate-agents.py`'s `emit_claude`); a file with no
`model_tier:` line -- an agent pinned via `model_pin` (D6), or a
consumer's own hand-written agent -- is left byte-identical (D1, D6).

No file I/O lives here -- `_cmds_agent_models.py` owns reading
`project-config.json`, walking `.claude/agents/*.md`, and writing the
result. This module only ever sees text in, text out.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ._schema import CLAUDE_MODEL_ALIASES

# Consumer-side TWIN of scripts/lib/install_defaults.py's
# CLAUDE_AGENT_DEFAULTS_BY_TIER. `scripts/` is never shipped to a
# consumer install -- only `src/devforge/lib/` is -- so importing across
# that boundary would be a maintainer-tree-into-shipped-tree dependency
# this repo does not take (plan 92 D2 half 1). The literal is duplicated
# here instead; tests/lib/_configure/test_apply_agent_models.py pins the
# two literals equal by loading scripts/lib/install_defaults.py by path,
# so editing either one alone fails that test.
CLAUDE_AGENT_DEFAULTS_BY_TIER = {
    "think": "opus",
    "do": "sonnet",
    "verify": "sonnet",
    "scan": "haiku",
}

# Per-tier project-config.json key pair (model key, effort key). Only the
# three tiers plan 92 D4 gave a configuration knob to appear here --
# "scan" has zero members (plan 92 OQ-3) and no CLAUDE_TIER_SCAN /
# CLAUDE_EFFORT_SCAN field exists to read, so a scan-tier agent (should
# one ever exist) always resolves through the "not configured" branch
# below to CLAUDE_AGENT_DEFAULTS_BY_TIER's static default with no effort
# line -- the same outcome a `null` configured value produces for a
# think/do/verify tier.
_TIER_CONFIG_KEYS = {
    "think": ("CLAUDE_TIER_THINK", "CLAUDE_EFFORT_THINK"),
    "do": ("CLAUDE_TIER_DO", "CLAUDE_EFFORT_DO"),
    "verify": ("CLAUDE_TIER_VERIFY", "CLAUDE_EFFORT_VERIFY"),
}

# The six-member closed enum from plan 92 D4 (ENUM_FIELDS in _schema.py);
# "default" is a real sentinel meaning "remove the effort: line", not an
# unset marker.
_EFFORT_ENUM = frozenset({"default", "low", "medium", "high", "xhigh", "max"})

# Skip reasons -- also the literal `reason` values in the command's JSON
# report, so a caller can match on them.
REASON_NO_FRONTMATTER = "no-frontmatter"
REASON_UNCLOSED_FRONTMATTER = "unclosed-frontmatter"
REASON_NO_MODEL_TIER = "no-model-tier"


class AgentValidationError(ValueError):
    """Raised by plan_rewrite for a resolved tier/effort -- or a
    frontmatter shape -- the emitted contract cannot honor: an unknown
    model_tier, a claude_effort value outside the six-member enum, a
    duplicated model_tier:/model:/effort: key, or a model_tier: line
    with no sibling model: line. Carries only the semantic message --
    this module sees frontmatter text, never a file path, so the command
    layer (_cmds_agent_models.py) is the one that names the offending
    file when it catches this."""


def extract_tier_config(
    project_config: dict,
) -> Tuple[Dict[str, Optional[str]], Dict[str, Optional[str]]]:
    """Build (tier_models, tier_efforts), each keyed by tier name
    ("think" / "do" / "verify"), from a parsed project-config.json dict.

    Uses _TIER_CONFIG_KEYS as the single tier -> project-config-key
    mapping, so the command layer and plan_rewrite's error messages never
    duplicate that literal. "scan" is deliberately absent from both dicts
    -- see _TIER_CONFIG_KEYS's own comment.
    """
    tier_models = {}  # type: Dict[str, Optional[str]]
    tier_efforts = {}  # type: Dict[str, Optional[str]]
    for tier, (model_key, effort_key) in _TIER_CONFIG_KEYS.items():
        tier_models[tier] = project_config.get(model_key)
        tier_efforts[tier] = project_config.get(effort_key)
    return tier_models, tier_efforts


def _resolve_tier(
    tier: str,
    tier_models: Dict[str, Optional[str]],
    tier_efforts: Dict[str, Optional[str]],
) -> Tuple[str, Optional[str]]:
    """Resolve (model, effort) for one tier from configured values.

    model: the tier's configured value when it is a non-empty string,
    normalized case-insensitively against CLAUDE_MODEL_ALIASES to
    lowercase -- a legacy capitalized value stored before that
    normalization existed at set-time (e.g. "Opus") must not reach a
    rewritten model: line -- any other non-empty string passes through
    verbatim as a pin. Falls back to CLAUDE_AGENT_DEFAULTS_BY_TIER[tier]
    when the configured value is missing, None, or not a string (D2's
    "null tier value applies the tier default").

    effort: None (meaning "no effort: line") when the configured value
    is missing, None, empty, or the "default" sentinel; otherwise the
    configured value, validated against the six-member enum.

    Raises AgentValidationError for an unknown tier or an out-of-enum
    effort value (naming the offending config key in the message).
    """
    if tier not in CLAUDE_AGENT_DEFAULTS_BY_TIER:
        raise AgentValidationError(
            "unknown model_tier {0!r} (expected one of {1})".format(
                tier, sorted(CLAUDE_AGENT_DEFAULTS_BY_TIER)
            )
        )

    _, effort_key = _TIER_CONFIG_KEYS.get(tier, (None, None))

    raw_model = tier_models.get(tier)
    if isinstance(raw_model, str) and raw_model.strip():
        model = raw_model.strip()
        if model.lower() in CLAUDE_MODEL_ALIASES:
            model = model.lower()
    else:
        model = CLAUDE_AGENT_DEFAULTS_BY_TIER[tier]

    raw_effort = tier_efforts.get(tier)
    if raw_effort in (None, "", "default"):
        effort = None  # type: Optional[str]
    elif raw_effort in _EFFORT_ENUM:
        effort = raw_effort
    else:
        raise AgentValidationError(
            "invalid claude_effort value {0!r} for {1}".format(
                raw_effort, effort_key or "claude_effort_{0}".format(tier)
            )
        )
    return model, effort


def _detect_line_ending(text: str) -> str:
    """Return the file's own line ending -- "\\r\\n" or "\\n" -- detected
    from its FIRST line break. Defaults to "\\n" when the text has no
    line break at all (a pathological single-line file).

    Applied uniformly to every NEW or REWRITTEN line plan_rewrite
    produces, so a CRLF file's rewritten model:/effort: line(s) come
    back CRLF too and a second run is a byte-level no-op
    (python-reviewer run B finding 3). A file that MIXES endings (some
    lines CRLF, others bare LF) is explicitly OUT OF SCOPE: every
    UNCHANGED line is copied through byte-identical regardless (so it
    keeps whatever ending it already had), but a line this module
    REWRITES or INSERTS always gets the single ending detected here from
    line one -- there is no well-defined "correct" answer for a file
    that already disagrees with itself, and this module does not try to
    invent one.
    """
    idx = text.find("\n")
    if idx == -1:
        return "\n"
    if idx > 0 and text[idx - 1] == "\r":
        return "\r\n"
    return "\n"


def _locate_frontmatter(lines: List[str]) -> Tuple[str, int, int]:
    """Return (status, open_idx, close_idx), 0-based indices into `lines`.

    status is "ok" (open_idx == 0, close_idx = the closing '---' line's
    index), "no-frontmatter" (the first line isn't '---'), or
    "unclosed-frontmatter" (starts with '---' but no closing '---' line
    is found before EOF). Matches the conditions Claude Code's own docs
    describe for skipping a subagent file (Phase 1 Step 0 answer 1).

    Comparisons strip BOTH '\\r' and '\\n' (`rstrip("\\r\\n")`), not just
    '\\n' -- a CRLF file (e.g. a consumer tree whose git re-normalized
    line endings) must resolve its frontmatter exactly like an LF one,
    not fall through to "no-frontmatter" as a silent no-op
    (python-reviewer run B finding 3).
    """
    if not lines or lines[0].rstrip("\r\n") != "---":
        return ("no-frontmatter", -1, -1)
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            return ("ok", 0, i)
    return ("unclosed-frontmatter", -1, -1)


def _find_key_lines(lines: List[str], key: str, start: int, end: int) -> List[int]:
    """Return EVERY absolute index in `lines` within [start, end) whose
    key -- the text before the FIRST ':', stripped -- equals `key`.
    Splitting on the first ':' only (never re-serializing the value) is
    what lets a `description:` value containing colons survive matching
    untouched.

    Returns [] when no line matches. Returning ALL matches (not just the
    first) is deliberate: a file with the same key twice inside its
    frontmatter is malformed, and the caller (plan_rewrite) must be able
    to tell "zero matches" apart from "more than one match" to reject the
    latter as a validation error instead of silently picking the first
    and leaving a stray duplicate line behind (python-reviewer run B
    finding 2).
    """
    result = []
    for i in range(start, end):
        line = lines[i]
        if ":" not in line:
            continue
        candidate, _, _ = line.partition(":")
        if candidate.strip() == key:
            result.append(i)
    return result


def plan_rewrite(
    text: str,
    tier_models: Dict[str, Optional[str]],
    tier_efforts: Dict[str, Optional[str]],
) -> Tuple[str, Dict[str, object]]:
    """Compute the rewritten text (or the untouched original) for one
    emitted agent file, plus a decision dict describing what happened.

    A file with no frontmatter, an unclosed frontmatter, or no
    `model_tier:` line is left untouched: returns (text, {"status":
    "skipped", "reason": <REASON_*>}).

    Otherwise resolves the file's tier via _resolve_tier and rewrites the
    `model:` line's value in place; `effort:` is removed if present (when
    the resolved effort is None), replaced in place (when present and an
    effort is resolved), or inserted immediately after the `model:` line
    (when absent and an effort is resolved) -- see Phase 1 Step 0 answer
    2 for why that position. Every other line -- frontmatter and body --
    is byte-identical. A rewritten or newly-inserted line's ending
    matches the FILE's own (detected via _detect_line_ending), so CRLF
    input stays CRLF and a second run is a byte-level no-op
    (python-reviewer run B finding 3). Returns (new_text, {"status":
    "applied", "tier": ..., "model": ..., "effort": ... or None,
    "changed": bool}).

    Raises AgentValidationError (propagated, not caught here) for: an
    unknown tier; an out-of-enum effort value; a duplicated
    model_tier:/model:/effort: key inside the frontmatter (rejected
    rather than guessed at -- python-reviewer run B finding 2); or a
    model_tier: line with no sibling model: line. The caller decides how
    to batch and report those across a whole run.
    """
    lines = text.splitlines(keepends=True)
    status, open_idx, close_idx = _locate_frontmatter(lines)
    if status != "ok":
        return text, {"status": "skipped", "reason": status}

    ending = _detect_line_ending(text)
    fm_start = open_idx + 1
    fm_end = close_idx

    model_tier_matches = _find_key_lines(lines, "model_tier", fm_start, fm_end)
    if not model_tier_matches:
        return text, {"status": "skipped", "reason": REASON_NO_MODEL_TIER}
    if len(model_tier_matches) > 1:
        raise AgentValidationError("duplicate model_tier: line")
    model_tier_idx = model_tier_matches[0]

    tier = lines[model_tier_idx].partition(":")[2].strip()
    model, effort = _resolve_tier(tier, tier_models, tier_efforts)

    model_matches = _find_key_lines(lines, "model", fm_start, fm_end)
    if len(model_matches) > 1:
        raise AgentValidationError("duplicate model: line")
    if not model_matches:
        raise AgentValidationError("model_tier present with no model: line")
    model_idx = model_matches[0]

    effort_matches = _find_key_lines(lines, "effort", fm_start, fm_end)
    if len(effort_matches) > 1:
        raise AgentValidationError("duplicate effort: line")
    effort_idx = effort_matches[0] if effort_matches else None

    new_lines = list(lines)
    new_lines[model_idx] = "model: {0}{1}".format(model, ending)
    if effort is None:
        if effort_idx is not None:
            del new_lines[effort_idx]
    else:
        effort_line = "effort: {0}{1}".format(effort, ending)
        if effort_idx is not None:
            new_lines[effort_idx] = effort_line
        else:
            new_lines.insert(model_idx + 1, effort_line)

    new_text = "".join(new_lines)
    decision = {
        "status": "applied",
        "tier": tier,
        "model": model,
        "effort": effort,
        "changed": new_text != text,
    }  # type: Dict[str, object]
    return new_text, decision
