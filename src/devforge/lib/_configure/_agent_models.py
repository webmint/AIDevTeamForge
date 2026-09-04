"""Pure logic for rewriting emitted `.claude/agents/*.md` AND
`.claude/commands/devforge/*.md` frontmatter from
`.devforge/project-config.json`
(92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md D1, Phase 1 Deliverable 3;
extended to commands by 94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md D1,
Phase 1 Deliverables 1/2/5).

Two classes of file, two keying mechanisms:
  - AGENT: keyed on the emitted `model_tier: <tier>` frontmatter line
    (`scripts/generate-agents.py`'s `emit_claude`); a file with no
    `model_tier:` line -- a consumer's own hand-written agent -- is left
    byte-identical.
  - COMMAND: keyed on `COMMAND_TIERS` (this module) by file stem.
    Commands carry NO tier marker line at all -- plan 94 D1 declined that
    route (unknown frontmatter keys in a LOCAL command file are not
    documented either way, and commands are re-emitted wholesale from
    `src/commands/<name>/main.md`, which would put a second tier
    declaration in the same file as the advisory line's tier word with
    nothing pinning them equal). A command whose stem is not a
    `COMMAND_TIERS` member is left byte-identical.

The framework ships no model of its own (plan 94 D2): every agent is
emitted with an explicit `model: inherit` line (never omitted -- `inherit`
is step 2 of Claude Code's documented subagent model-resolution order and
beats the `CLAUDE_CODE_SUBAGENT_MODEL` environment variable at step 3; an
absent line would fall through to that variable, handing the choice to an
owner the framework cannot see) and no command is emitted with a `model:`
line at all. `_resolve_tier`'s `kind` parameter is what makes "not
configured" resolve differently per class -- see its own docstring.

No file I/O lives here -- `_cmds_agent_models.py` owns reading
`project-config.json`, walking both directories, and writing the result.
This module only ever sees text in, text out.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ._schema import CLAUDE_MODEL_ALIASES

# The four valid model_tier values (plan 94 D2 part 4 retires "scan" --
# it had zero members for the life of the roster and the static default
# map that gave it meaning is gone; plan 94 D3 adds "security" as the
# fourth tier, security-reviewer's sole member). A plain tuple, not a
# dict -- there is no longer a default value living beside each tier
# name, only a name to validate against.
VALID_TIERS = ("think", "do", "verify", "security")

# Per-tier project-config.json key pair (model key, effort key), one
# entry per VALID_TIERS member -- every tier now has a configuration
# knob (plan 94 D3 gave "security" one; "scan" never had one and is
# retired, so there is no longer a tier this dict deliberately omits).
_TIER_CONFIG_KEYS = {
    "think": ("CLAUDE_TIER_THINK", "CLAUDE_EFFORT_THINK"),
    "do": ("CLAUDE_TIER_DO", "CLAUDE_EFFORT_DO"),
    "verify": ("CLAUDE_TIER_VERIFY", "CLAUDE_EFFORT_VERIFY"),
    "security": ("CLAUDE_TIER_SECURITY", "CLAUDE_EFFORT_SECURITY"),
}

# The helper-owned map from a promoted command's file stem to the tier
# its judgment work belongs to (94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md
# D1). This is the ONLY place the framework says which command belongs
# to which tier: the emitted commands carry no marker key (see the
# module docstring), so there is nothing in a consumer's own tree to read
# it back from. The eight command sources' own advisory steps
# (`src/commands/<name>/main.md`, the "This command's judgment work
# belongs to the <tier> tier..." line) name the SAME tier in prose, and
# `tests/lib/_configure/test_command_tiers.py` pins the two equal by
# reading the live command sources -- so the map and the printed advice
# cannot disagree, and adding a ninth command to one without the other
# fails that test.
COMMAND_TIERS = {
    "specify": "think",
    "plan": "think",
    "grill": "think",
    "breakdown": "think",
    "implement": "do",
    "fix": "do",
    "review": "verify",
    "verify": "verify",
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
REASON_NOT_IN_COMMAND_TIERS = "not-in-command-tiers"


class AgentValidationError(ValueError):
    """Raised by plan_rewrite for a resolved tier/effort -- or a
    frontmatter shape -- the emitted contract cannot honor: an unknown
    model_tier, a claude_effort value outside the six-member enum, a
    duplicated model_tier:/model:/effort: key, a model_tier: line with
    no sibling model: line (agents), or a command frontmatter with no
    description: line to anchor an inserted model:/effort: line after.
    Carries only the semantic message -- this module sees frontmatter
    text, never a file path, so the command layer
    (_cmds_agent_models.py) is the one that names the offending file
    when it catches this."""


def extract_tier_config(
    project_config: dict,
) -> Tuple[Dict[str, Optional[str]], Dict[str, Optional[str]]]:
    """Build (tier_models, tier_efforts), each keyed by tier name (every
    VALID_TIERS member), from a parsed project-config.json dict.

    Uses _TIER_CONFIG_KEYS as the single tier -> project-config-key
    mapping, so the command layer and plan_rewrite's error messages never
    duplicate that literal.
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
    kind: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve (model, effort) for one tier from configured values, for
    either an AGENT or a COMMAND file (`kind`, one of "agent"/"command").

    model: the tier's configured value when it is a non-empty string,
    normalized case-insensitively against CLAUDE_MODEL_ALIASES to
    lowercase -- a legacy capitalized value stored before that
    normalization existed at set-time (e.g. "Opus") must not reach a
    rewritten model: line -- any other non-empty string passes through
    verbatim as a pin. IDENTICAL for both classes.

    When the configured value is missing, None, or not a string ("not
    configured"), model resolves CLASS-DEPENDENTLY (plan 94 D2 -- the
    framework ships no model of its own, so there is no shared default
    to fall back to): the literal string "inherit" for kind="agent"
    (explicit rather than omitted -- see the module docstring), or
    `None` for kind="command", meaning "write no model: line at all".
    This is the one place the two classes diverge in this function; a
    parameter carries it rather than two entry points because every
    other branch here (effort resolution, alias normalization, the tier
    validity check) is identical between the classes and would
    otherwise be duplicated for a four-line difference (plan 94 Phase 1
    Deliverable 5).

    effort: None (meaning "no effort: line") when the configured value
    is missing, None, empty, or the "default" sentinel; otherwise the
    configured value, validated against the six-member enum. IDENTICAL
    for both classes.

    Raises AgentValidationError for an unknown tier (message lists every
    VALID_TIERS member) or an out-of-enum effort value (naming the
    offending config key in the message).
    """
    if tier not in VALID_TIERS:
        raise AgentValidationError(
            "unknown model_tier {0!r} (expected one of {1})".format(
                tier, sorted(VALID_TIERS)
            )
        )

    # A direct index, not .get(tier, (None, None)): VALID_TIERS and
    # _TIER_CONFIG_KEYS are two hand-kept literals with nothing else
    # pinning their key sets equal (test_agent_models.py does that), so
    # a .get default would turn a desync between them into a silent
    # "not configured" instead of a loud KeyError at the one call site
    # that would notice (python-reviewer run B finding 1).
    _, effort_key = _TIER_CONFIG_KEYS[tier]

    raw_model = tier_models.get(tier)
    if isinstance(raw_model, str) and raw_model.strip():
        model = raw_model.strip()  # type: Optional[str]
        if model.lower() in CLAUDE_MODEL_ALIASES:
            model = model.lower()
    else:
        model = "inherit" if kind == "agent" else None

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
    produces, so a CRLF file's rewritten line(s) come back CRLF too and a
    second run is a byte-level no-op (python-reviewer run B finding 3). A
    file that MIXES endings (some lines CRLF, others bare LF) is
    explicitly OUT OF SCOPE: every UNCHANGED line is copied through
    byte-identical regardless (so it keeps whatever ending it already
    had), but a line this module REWRITES or INSERTS always gets the
    single ending detected here from line one -- there is no well-defined
    "correct" answer for a file that already disagrees with itself, and
    this module does not try to invent one.
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
    describe for skipping a subagent file (plan 92 Phase 1 Step 0 answer
    1); applied identically to command files, whose frontmatter is
    fenced the same way.

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


def _rewrite_command_field(
    lines: List[str],
    key: str,
    value: Optional[str],
    anchor_keys: Tuple[str, ...],
    fm_start: int,
    fm_end: int,
    ending: str,
) -> int:
    """Mutate `lines` (a full-file line list, including the frontmatter
    fences and body) IN PLACE to set/remove one `<key>: <value>` line
    inside the frontmatter span [fm_start, fm_end). COMMAND rewriting
    only -- an agent's model:/effort: lines already exist by the
    emitter's own contract, so plan_rewrite's agent path never inserts a
    model: line and only ever inserts effort: at a fixed position
    relative to an existing model: line (see plan_rewrite). Returns the
    (possibly shifted) `fm_end`, since inserting or deleting a line
    inside the span moves it.

    value=None removes an existing `<key>:` line (used for an
    unconfigured tier's model:, or an unset/"default" effort:); a
    non-None value replaces an existing line in place, or INSERTS one
    immediately after the FIRST line found by searching `anchor_keys` in
    order. `effort:` is called with anchor_keys=("model", "description")
    so it lands right after a model: line when one exists (matching
    plan_rewrite's agent-path insertion rule) and falls back to landing
    right after description: when no model: line exists at all (a
    command whose tier configures an effort but no model). `model:` is
    called with anchor_keys=("description",) -- every real command
    source carries a description: line (scripts/emitters/claude.py's own
    contract), so that anchor is expected to exist; a file that lacks
    one at all raises AgentValidationError naming the LAST anchor key
    tried, since that is the one the caller cannot omit.

    Re-locates the key and its anchor by SCANNING `lines` after every
    mutation rather than tracking an index by hand across the two calls
    (model, then effort) plan_rewrite makes -- the frontmatter blocks
    this ever runs against are a handful of lines, and a hand-adjusted
    index after an insert/delete is a wrong number waiting to happen.
    """
    matches = _find_key_lines(lines, key, fm_start, fm_end)
    idx = matches[0] if matches else None

    if value is None:
        if idx is not None:
            del lines[idx]
            fm_end -= 1
        return fm_end

    new_line = "{0}: {1}{2}".format(key, value, ending)
    if idx is not None:
        lines[idx] = new_line
        return fm_end

    anchor_idx = None
    for anchor_key in anchor_keys:
        anchor_matches = _find_key_lines(lines, anchor_key, fm_start, fm_end)
        if anchor_matches:
            anchor_idx = anchor_matches[0]
            break
    if anchor_idx is None:
        raise AgentValidationError(
            "no {0} line to anchor {1}: after".format(anchor_keys[-1], key)
        )
    lines.insert(anchor_idx + 1, new_line)
    return fm_end + 1


def plan_rewrite(
    text: str,
    tier_models: Dict[str, Optional[str]],
    tier_efforts: Dict[str, Optional[str]],
    kind: str = "agent",
    tier: Optional[str] = None,
) -> Tuple[str, Dict[str, object]]:
    """Compute the rewritten text (or the untouched original) for one
    emitted agent OR command file, plus a decision dict describing what
    happened.

    kind: "agent" (default) or "command" -- the one parameter that makes
    both the KEYING and the RENDERING of a null-tier model class-
    dependent (94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md D1/D2). Taken
    as a parameter on this function (as well as on `_resolve_tier`,
    which it also threads through to) rather than as two entry points:
    every step below that is NOT keying or a null-model render --
    locating the frontmatter fence, detecting the line ending, finding a
    duplicated key, resolving an effort value -- is byte-identical
    between the classes, and splitting into two top-level functions
    would duplicate all of that machinery for the two genuinely
    different steps.

    kind="agent" (unchanged behavior from plan 92 Phase 1 Deliverable 3):
    the tier comes from the file's OWN `model_tier:` frontmatter line
    (`tier` is ignored); a file with no frontmatter, an unclosed
    frontmatter, or no `model_tier:` line is left untouched (returns
    (text, {"status": "skipped", "reason": <REASON_*>})). `model:` is
    REQUIRED to already exist alongside `model_tier:` (an emitter
    contract -- a `model_tier:` line with no sibling `model:` line is a
    validation error, not a skip) and is rewritten in place; `effort:`
    is removed/replaced/inserted immediately after `model:` (Phase 1
    Step 0 answer 2's insertion point).

    kind="command": `tier` is REQUIRED (the caller resolves it from
    COMMAND_TIERS by file stem -- commands carry no tier marker line at
    all, see the module docstring). A file with no frontmatter or an
    unclosed frontmatter is left untouched, same as an agent. `model:`
    and `effort:` are each OPTIONAL in the source text (most commands
    carry neither, until a prior apply run wrote one): each is replaced
    in place if present, removed if present and the resolved value is
    None, or inserted (see `_rewrite_command_field`) if absent and a
    value is resolved. A null-tier command's `model:` becomes `None` --
    no line at all, not "inherit" -- which is what makes a previously-
    configured-then-unconfigured command's stray `model:` line get
    REMOVED rather than left to linger.

    Every line this function does not touch -- frontmatter and body -- is
    byte-identical to the input, for both classes. A rewritten or newly-
    inserted line's ending matches the FILE's own (detected via
    _detect_line_ending), so CRLF input stays CRLF and a second run is a
    byte-level no-op (python-reviewer run B finding 3). Returns
    (new_text, {"status": "applied", "tier": ..., "model": ... or None,
    "effort": ... or None, "changed": bool}) -- "model" is only ever
    None for kind="command" (an agent always resolves to a real value,
    "inherit" included).

    Raises AgentValidationError (propagated, not caught here) for: an
    unknown tier; an out-of-enum effort value; a duplicated
    model_tier:/model:/effort: key inside the frontmatter (rejected
    rather than guessed at -- python-reviewer run B finding 2); a
    model_tier: line with no sibling model: line (kind="agent" only);
    or a command frontmatter with no description: line to anchor an
    inserted model:/effort: line after (kind="command" only). The
    caller decides how to batch and report those across a whole run.
    """
    lines = text.splitlines(keepends=True)
    status, open_idx, close_idx = _locate_frontmatter(lines)
    if status != "ok":
        return text, {"status": "skipped", "reason": status}

    ending = _detect_line_ending(text)
    fm_start = open_idx + 1
    fm_end = close_idx

    if kind == "agent":
        model_tier_matches = _find_key_lines(lines, "model_tier", fm_start, fm_end)
        if not model_tier_matches:
            return text, {"status": "skipped", "reason": REASON_NO_MODEL_TIER}
        if len(model_tier_matches) > 1:
            raise AgentValidationError("duplicate model_tier: line")
        resolved_tier = lines[model_tier_matches[0]].partition(":")[2].strip()
    else:
        resolved_tier = tier

    model, effort = _resolve_tier(resolved_tier, tier_models, tier_efforts, kind)

    model_matches = _find_key_lines(lines, "model", fm_start, fm_end)
    if len(model_matches) > 1:
        raise AgentValidationError("duplicate model: line")
    effort_matches = _find_key_lines(lines, "effort", fm_start, fm_end)
    if len(effort_matches) > 1:
        raise AgentValidationError("duplicate effort: line")

    new_lines = list(lines)

    if kind == "agent":
        if not model_matches:
            raise AgentValidationError("model_tier present with no model: line")
        model_idx = model_matches[0]
        # model is never None for kind="agent" (see _resolve_tier) -- an
        # unconfigured tier resolves to the literal "inherit", so this
        # always rewrites the existing line rather than removing it.
        new_lines[model_idx] = "model: {0}{1}".format(model, ending)
        effort_idx = effort_matches[0] if effort_matches else None
        if effort is None:
            if effort_idx is not None:
                del new_lines[effort_idx]
        else:
            effort_line = "effort: {0}{1}".format(effort, ending)
            if effort_idx is not None:
                new_lines[effort_idx] = effort_line
            else:
                new_lines.insert(model_idx + 1, effort_line)
    else:
        fm_end = _rewrite_command_field(
            new_lines, "model", model, ("description",), fm_start, fm_end, ending
        )
        fm_end = _rewrite_command_field(
            new_lines, "effort", effort, ("model", "description"), fm_start, fm_end, ending
        )

    new_text = "".join(new_lines)
    decision = {
        "status": "applied",
        "tier": resolved_tier,
        "model": model,
        "effort": effort,
        "changed": new_text != text,
    }  # type: Dict[str, object]
    return new_text, decision
