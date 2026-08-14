"""handoff_schema — dataclass schema for the research → specify → plan → /implement handoff artefact.

Single source of truth for the shape of `handoff.json` emitted by
`research_helper finalize-handoff` (Step 3) and consumed by
`specify_helper import-handoff` (Step 6).

Design notes:

- Dataclasses are pure records. No serialization (`to_dict` /
  `from_dict`), no rendering, no I/O. Those responsibilities live in the
  helper command layer so this schema stays small, importable, and
  independently testable.

- Schema-level validation runs in `__post_init__` and is mechanical:
    * Required string fields are non-empty after `.strip()`.
    * Enum-typed fields validated against module-level frozenset constants.
    * Conditional requireds enforced at construction (constraint kind rules,
      probe-tier interlocks, V2/V3 cross-field invariants).

- V2 fields: `DataFlowChain`, `ValueSemantics`, `ValueProductionSite`.
  Required gating: bug mode + presentation-layer symptom heuristic.
  Stability-axis gating: invariant classification + presentation-layer
  symptom. Production-site gating: stable_across_calls="false" requires
  a matching production site row.

- V3 fields: `LiteralArchaeology`, `proposed_call_shape`.
  literal_archaeology PRESENCE (a non-empty list) is required when the
  recommended approach is a literal-replacement approach as detected by
  THIS module's own narrow `_has_literal_replacement` (`_LITERAL_REPLACEMENT_RE`
  -- "replace X with Y" / "change X to Y" / "X -> Y", single-token X/Y
  only). That detector is DELIBERATELY NARROWER than, and independent of,
  the shared detector `_shared/literal_call_shape.py:_detect_literal_replacement`
  that governs verify check 17 (`_cmds_render_verify.py`) -- check 17's
  detector also matches "swap <X> with/for <Y>" prose that this module's
  regex does not. The two can and do diverge on real prose: check 17 can
  compel `record-literal-archaeology` on a summary this module's own
  presence gate never fires on. This is not a bug to reconcile here --
  check 17 is the MANDATORY-at-verify-time forcing function; this gate is
  a narrower, independent finalize-handoff-time backstop using its own
  regex on purpose (defense-in-depth, not a mirror). The escalation-cite
  loop below (`PlanSeeds._validate_cross_field`, plan 73 D2/OQ-5) is
  independent of BOTH detectors -- it iterates every recorded
  literal_archaeology row regardless of whether either replacement regex
  matched, and is scoped by each row's `use` field (`fix-layer` vs
  `evidence`), not by prose.
  Presence REQUIREDNESS is mode-independent (plan 73 D1; widened from
  bug-mode-gated, mirroring plan 67's check-8 decouple) for handoffs
  produced under the new regime -- see `_requires_literal_archaeology_presence`
  for the schema_version-scoped carve-out that keeps a handoff.json written
  BEFORE plan 73 shipped readable under the RULES IT WAS WRITTEN UNDER
  (finding 2 of the plan-73 OQ-5 build: `_dict_to_dataclass`-driven
  reconstruction on read, e.g. specify's import-handoff, re-runs this same
  validator against already-persisted JSON). proposed_call_shape
  required when bug mode + single-layer or literal-replacement approach --
  that REQUIREDNESS rule is bug-mode-gated and unchanged. The value's
  PRESENCE is not: plan 69 D6/WI-F widened `research_helper
  set-recommended-approach`'s storage of proposed_call_shape (and the
  mirroring verify check 18) to mode-independent, so an enhancement-mode
  handoff MAY legitimately carry a populated proposed_call_shape even
  though bug mode is the only mode that requires one. Argument-duplication
  detection with optional-chaining support; fail-soft on nested calls.

- Type-hint convention: explicit `typing.Optional` / `List` / `Dict`
  (no PEP 604 `X | None`, no PEP 585 `list[str]`). Targets Python 3.8+.
  `from __future__ import annotations` intentionally NOT used so
  `__post_init__` introspection sees real type objects.

Stdlib only. No third-party dependencies.
"""

import datetime
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Schema version constant.
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.2"

# Plan 73 OQ-5 Finding-2 fix: 1.1 -> 1.2 bump marks the point at which the
# literal_archaeology presence gate in PlanSeeds._validate_cross_field became
# mode-independent (plan 73 D1). See _requires_literal_archaeology_presence
# and _VERSIONS_PREDATING_LITERAL_ARCHAEOLOGY_MODE_INDEPENDENCE below for why
# this is a *behavioral* version, not just a field-vocabulary one: V2 and V3
# both added fields WITHOUT a version bump (field-level Optional/default
# defaulting was sufficient for additive fields), but a REQUIREDNESS change on
# an already-existing field cannot be back-compat-guarded by a field default
# -- reconstructing an old handoff.json via _dict_to_dataclass (specify's
# import-handoff read path) re-runs this same validator against
# already-persisted JSON, so the validator must know which regime produced
# the artifact it is checking.


# ---------------------------------------------------------------------------
# Enum allow-sets (frozensets for O(1) membership, similar to
# generate_docs_schema.py's tuple approach but frozenset preferred for
# sets that are checked frequently at construction time).
# ---------------------------------------------------------------------------

_VALID_MODE = frozenset({"bug", "feature_addition", "migration", "refactor", "greenfield"})
_VALID_SCOPE = frozenset({"feature-wide", "file-local", "package-local", "system-wide"})
_VALID_SPEC_TYPE_HINT = frozenset({
    "migration_tooling", "feature_addition", "bug_fix", "refactor", "greenfield_feature"
})
_VALID_CONSTRAINT_KIND = frozenset({"nfr", "constitution_anchor", "external_system", "follow", "not_break"})
_VALID_LIKELIHOOD = frozenset({"Low", "Med", "High"})
_VALID_IMPACT = frozenset({"Low", "Med", "High"})
_VALID_COMPLEXITY = frozenset({"Low", "Med", "High"})
_VALID_TRACE_MODE = frozenset({"data_flow", "calls"})
_VALID_VALUE_CLASSIFICATION = frozenset({"preference", "invariant", "unclassified"})
_VALID_STABLE_ACROSS_CALLS = frozenset({"true", "false", "unknown"})
_VALID_LITERAL_INTENT = frozenset({
    "placeholder", "migrated", "deliberate", "forgotten", "inherited-refactor", "generated"
})
# Plan 73 OQ-5 -- discriminates why a literal_archaeology row was recorded:
# "fix-layer" = the literal IS the thing being replaced (the original V3
# Patch 8 use case; the escalation-cite loop in
# PlanSeeds._validate_cross_field applies to these rows).
# "evidence" = the literal's CURRENT value was cited as grounds for a scope
# call (dead/live, keep/delete) and nothing is being replaced -- D3's
# recovery rule applies instead, and the escalation-cite loop is scoped
# OFF these rows (demanding fix-layer-escalation prose when nothing is
# being replaced is meaningless -- see the escalation-cite loop below).
# Absent on a pre-plan-73 handoff.json (no such row could have been
# anything but fix-layer before the evidence arm existed) -> defaults to
# "fix-layer" at the LiteralArchaeology field level (see the `use` field
# default below), independent of the schema_version-scoped presence-gate
# carve-out (_requires_literal_archaeology_presence), which is a SEPARATE
# back-compat mechanism for a different validator.
_VALID_LITERAL_ARCHAEOLOGY_USE = frozenset({"fix-layer", "evidence"})
_VALID_PROBE_TIER = frozenset({"1", "1.5", "2", "3"})
_VALID_PROBE_ACTOR = frozenset({"llm", "user"})
_VALID_TEST_FRAMEWORK = frozenset({"vitest", "jest", "pytest", "go-test", "cargo-test", "rspec"})
_VALID_HYPOTHESIS_CONFIRMED = frozenset({"primary", "runner_up", "none", "inconclusive"})
_VALID_EVIDENCE_SOURCE = frozenset({"test-result", "llm-ui-session-log", "user-observation"})
_VALID_CONFIDENCE_GRADE = frozenset({"HIGH", "MEDIUM", "LOW"})
# Plan 69 D5/WI-E — InboundCaller.scope. "" means unclassified (a row
# recorded via record-inbound-caller but never augmented by
# classify-caller-scope, or a handoff.json predating plan 69) -- not a
# third scope value alongside "in"/"out".
_VALID_CALLER_SCOPE = frozenset({"", "in", "out"})

# V3 Patch 8 literal-replacement detector regex -- THIS MODULE'S OWN, narrow
# detector for the literal_archaeology PRESENCE gate below
# (PlanSeeds._validate_cross_field). Matches ONLY: "Replace X with Y" /
# "change X to Y" / "X -> Y", single-token X/Y. This is NOT the same
# detector that governs verify check 17 (`_cmds_render_verify.py`, via
# `_shared/literal_call_shape.py:_detect_literal_replacement`) -- that
# shared detector is BROADER (also matches "swap X with/for Y" and
# multi-token prose) and is the one that actually forces
# `record-literal-archaeology` to be called at verify time. The two
# detectors are independent by design (defense-in-depth backstops at two
# different chokepoints, not a mirrored pair) and can diverge on real
# prose -- do not assume a match on one implies a match on the other.
_LITERAL_REPLACEMENT_RE = re.compile(
    r'(?:replace|change)\s+\S+\s+(?:with|to)\s+\S+|^\S+\s*->\s*\S+$',
    re.IGNORECASE | re.MULTILINE,
)

# V3 Patch 9 — proposed_call_shape first-gate regex: top-level function call.
_CALL_SHAPE_RE = re.compile(r'^[A-Za-z_][\w.]*\([^)]*\)$')

# Commit SHA format: 7-40 hex characters.
_COMMIT_SHA_RE = re.compile(r'^[0-9a-f]{7,40}$')

# Escalation prose tokens (any of these case-insensitively in summary = OK).
_ESCALATION_TOKENS = ("default", "wrapper", "caller", "escalat")

# Literal intent values that require escalation cite.
_INTENTS_REQUIRING_ESCALATION = frozenset({"placeholder", "forgotten", "inherited-refactor"})


# ---------------------------------------------------------------------------
# Validation helpers.
# ---------------------------------------------------------------------------


def _require_nonempty(value, field_name):
    """Raise ValueError if `value` is not a non-empty (post-strip) string."""
    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} must be a string, got {type(value).__name__}"
        )
    if value.strip() == "":
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_in_enum(value, allowed, field_name):
    """Raise ValueError if `value` is not in `allowed`."""
    if value not in allowed:
        raise ValueError(
            f"{field_name} must be one of {sorted(allowed)}, got {value!r}"
        )


def _is_presentation_layer_symptom(affected_areas):
    """Return True if any affected_area file path matches a presentation-layer extension.

    Uses a structural heuristic matching file extensions .vue, .tsx?, .jsx?,
    .svelte, .html (with optional :line suffix). This is a schema-level sketch;
    the real research_helper.py performs richer detection. Acceptable here
    because the schema enforces shape structurally, not semantically.
    """
    pattern = re.compile(r'\.(vue|tsx?|jsx?|svelte|html)(:|$)')
    for area in affected_areas:
        for file_ref in area.files:
            if pattern.search(file_ref):
                return True
    return False


def _has_literal_replacement(summary):
    """Return True if the summary text matches the V3 literal-replacement regex."""
    return bool(_LITERAL_REPLACEMENT_RE.search(summary))


def _has_escalation_cite(summary):
    """Return True if the summary contains any escalation-direction token."""
    lower = summary.lower()
    return any(token in lower for token in _ESCALATION_TOKENS)


# Plan 73 OQ-5 Finding-2 fix -- schema_version values that predate the
# mode-independent literal_archaeology presence gate (plan 73 D1). A
# handoff.json stamped with one of these versions was produced when the
# presence requirement was bug-mode-gated ("mode == 'bug' and
# is_literal_replacement"); reconstructing one via _dict_to_dataclass
# (specify's import-handoff read path re-runs Handoff.__post_init__, which
# re-runs this same validator against already-persisted JSON) must honor the
# rules it was WRITTEN under, or an enhancement-mode handoff with a
# replacement-shaped summary and an empty literal_archaeology list --
# legally valid before plan 73 D1 shipped, since only bug mode required
# populating the list -- would newly fail on read after an upgrade, even
# though the user did nothing wrong producing it. A schema_version NOT in
# this set (i.e. SCHEMA_VERSION and any future bump) is written under the
# NEW regime and must satisfy the mode-independent rule unconditionally --
# this set never grows going forward; only the schema_version threshold at
# which handoffs stop predating the new regime is what's being encoded.
_VERSIONS_PREDATING_LITERAL_ARCHAEOLOGY_MODE_INDEPENDENCE = frozenset({"1.0", "1.1"})


def _requires_literal_archaeology_presence(mode, schema_version):
    """True when the literal_archaeology presence gate must fire for this handoff.

    schema_version is guaranteed to be a member of _ACCEPTED_SCHEMA_VERSIONS
    by the time this runs (Handoff.__post_init__ validates schema_version
    before calling into PlanSeeds._validate_cross_field), so a plain
    membership check against the closed predating-set is sufficient --
    no numeric version-tuple parsing is needed for a 3-member accepted set.

    - schema_version predates plan 73 D1 (written under the old regime):
      presence required only when mode == "bug" -- BYTE-IDENTICAL to the
      rule that handoff was validated against when it was first written
      (research_helper's own finalize-handoff also runs this validator).
    - schema_version is current or newer (written under the new regime):
      presence required unconditionally (plan 73 D1's mode-independent
      widening) -- this is the ONLY branch that governs a freshly-produced
      handoff, since research_helper's finalize-handoff always stamps the
      live SCHEMA_VERSION constant.
    """
    if schema_version in _VERSIONS_PREDATING_LITERAL_ARCHAEOLOGY_MODE_INDEPENDENCE:
        return mode == "bug"
    return True


def _is_single_layer_fix(layer_justification):
    """Return True if layer_justification implies a single-layer fix."""
    lower = layer_justification.lower()
    return "single-layer" in lower or "single layer" in lower


def _parse_proposed_call_shape(proposed_call_shape):
    """Parse proposed_call_shape for argument duplication.

    Returns (parse_failed: bool, duplicate_identifier: Optional[str]).
    - parse_failed=True means the shape failed the first-gate regex (fail-soft).
    - duplicate_identifier non-None means a duplicate was detected (hard reject).
    """
    if not _CALL_SHAPE_RE.match(proposed_call_shape):
        return True, None  # fail-soft — nested call, spread, template literal, etc.

    # Extract argument list: everything between the outermost parens.
    inner_start = proposed_call_shape.index('(')
    inner = proposed_call_shape[inner_start + 1:-1]

    if not inner.strip():
        return False, None  # zero-arg call, no duplication possible

    # Split on top-level commas. Since the first-gate regex requires
    # [^)]* in the paren group (no nested parens), a simple split is safe.
    args = inner.split(',')

    # Collect identifier tokens per arg using optional-chaining-aware regex.
    ident_re = re.compile(r'[A-Za-z_]\w*(?:\??\.[A-Za-z_]\w*)*')
    # For duplication detection, we look at ROOT identifiers (the leading
    # name before any '.') since optional-chain variants of the same root
    # are semantically the same binding.
    root_re = re.compile(r'^([A-Za-z_]\w*)')

    seen_roots = {}  # root_identifier -> first arg index
    for arg_idx, arg in enumerate(args):
        tokens = ident_re.findall(arg.strip())
        for token in tokens:
            m = root_re.match(token)
            if not m:
                continue
            root = m.group(1)
            if root in seen_roots:
                return False, root
            seen_roots[root] = arg_idx

    return False, None


# ---------------------------------------------------------------------------
# Confidence grade derivation.
# ---------------------------------------------------------------------------


def compute_confidence_grade(
    tier,                    # type: str
    evidence_source,         # type: str
    hypothesis_confirmed,    # type: str
    has_production_site_check,  # type: bool
):
    # type: (...) -> str
    """Compute the expected confidence grade from a (tier, evidence_source, hypothesis_confirmed, has_production_site_check) tuple.

    This function is the single source of truth for grade derivation;
    `Outcome.__post_init__` asserts the stored `confidence_grade` matches.
    Exported for `append-outcome` (Step 7) to call directly.

    Grade rules (checked in priority order):
    - Tier 1 + test-result + confirmed in {primary, runner_up, none} → HIGH
    - Tier 1.5 + test-result → HIGH
    - production_site_check present + primary confirmed + non-test-result → MEDIUM
      (production-site bugs need executable evidence; observation is insufficient)
    - Tier 2 + llm-ui-session-log → MEDIUM
    - Tier 2 + user-observation → LOW
    - Tier 3 → LOW
    - fallback → LOW
    """
    if (tier == "1"
            and evidence_source == "test-result"
            and hypothesis_confirmed in {"primary", "runner_up", "none"}):
        return "HIGH"
    if tier == "1.5" and evidence_source == "test-result" and hypothesis_confirmed != "inconclusive":
        return "HIGH"
    if (has_production_site_check
            and hypothesis_confirmed == "primary"
            and evidence_source != "test-result"):
        return "MEDIUM"
    if tier == "2" and evidence_source == "llm-ui-session-log":
        return "MEDIUM"
    if tier in {"1", "1.5"} and evidence_source == "test-result" and hypothesis_confirmed == "inconclusive":
        return "MEDIUM"
    if tier == "2" and evidence_source == "user-observation":
        return "LOW"
    if tier == "3":
        return "LOW"
    return "LOW"


# ---------------------------------------------------------------------------
# Nested record: Intent.
# ---------------------------------------------------------------------------


@dataclass
class Intent:
    """Research intent block — symptom, desired state, scope, and verbatim prompt.

    verbatim_prompt (added v1.1): the raw user prompt text, unmodified.

    Back-compat (OQ-1 RESOLVED): the field defaults to None so that pre-v1.1
    handoff.json records loaded via _dict_to_dataclass do not raise on
    construction (absent field -> None -> tolerate-missing-on-read branch).
    When non-None, it must be non-empty after strip (same _require_nonempty
    idiom as other optional string fields). New handoffs always supply a
    non-empty string via _build_handoff_from_state, which guards on the
    state value before constructing Intent.
    """

    symptom_summary: str
    desired_summary: str
    scope: str  # one of _VALID_SCOPE
    verbatim_prompt: Optional[str] = None

    def __post_init__(self):
        _require_nonempty(self.symptom_summary, "Intent.symptom_summary")
        _require_nonempty(self.desired_summary, "Intent.desired_summary")
        _require_in_enum(self.scope, _VALID_SCOPE, "Intent.scope")
        if self.verbatim_prompt is not None:
            _require_nonempty(self.verbatim_prompt, "Intent.verbatim_prompt")


# ---------------------------------------------------------------------------
# Nested records: spec_seeds sub-records.
# ---------------------------------------------------------------------------


@dataclass
class Constraint:
    """One spec constraint, using Gap-A taxonomy.

    kind `use` is hard-rejected with a migration message.
    kind `nfr` requires `quantifier`.
    kind `constitution_anchor` requires `constitution_ref`.
    kind `external_system` requires `protocol` OR `contract_doc_ref`.
    """

    kind: str
    content: str
    quantifier: Optional[str] = None
    constitution_ref: Optional[str] = None
    protocol: Optional[str] = None
    contract_doc_ref: Optional[str] = None

    def __post_init__(self):
        # Hard-reject legacy `use` kind before the enum check.
        if self.kind == "use":
            raise ValueError(
                "Constraint.kind='use' is rejected. Use one of: "
                "'nfr' (scale/latency NFRs), "
                "'constitution_anchor' (code-pattern rules), "
                "'external_system' (third-party protocol contracts)."
            )
        _require_in_enum(self.kind, _VALID_CONSTRAINT_KIND, "Constraint.kind")
        _require_nonempty(self.content, "Constraint.content")

        if self.kind == "nfr":
            if not self.quantifier or not self.quantifier.strip():
                raise ValueError(
                    "Constraint.quantifier is required when kind='nfr'"
                )

        if self.kind == "constitution_anchor":
            if not self.constitution_ref or not self.constitution_ref.strip():
                raise ValueError(
                    "Constraint.constitution_ref is required when kind='constitution_anchor'"
                )

        if self.kind == "external_system":
            proto_ok = self.protocol and self.protocol.strip()
            ref_ok = self.contract_doc_ref and self.contract_doc_ref.strip()
            if not proto_ok and not ref_ok:
                raise ValueError(
                    "Constraint.protocol OR Constraint.contract_doc_ref is required "
                    "when kind='external_system'"
                )


@dataclass
class AffectedArea:
    """One affected area in the codebase."""

    area: str
    files: List[str]  # list of "path:line" strings
    impact: str

    def __post_init__(self):
        _require_nonempty(self.area, "AffectedArea.area")
        _require_nonempty(self.impact, "AffectedArea.impact")
        if not isinstance(self.files, list):
            raise ValueError("AffectedArea.files must be a list")
        for f in self.files:
            if not isinstance(f, str):
                raise ValueError(
                    f"AffectedArea.files elements must be strings, got {type(f).__name__!r} in area {self.area!r}"
                )


@dataclass
class Risk:
    """One identified risk."""

    risk: str
    likelihood: str  # one of _VALID_LIKELIHOOD
    impact: str      # one of _VALID_IMPACT
    mitigation: str

    def __post_init__(self):
        _require_nonempty(self.risk, "Risk.risk")
        _require_in_enum(self.likelihood, _VALID_LIKELIHOOD, "Risk.likelihood")
        _require_in_enum(self.impact, _VALID_IMPACT, "Risk.impact")
        _require_nonempty(self.mitigation, "Risk.mitigation")


@dataclass
class OpenQuestion:
    """One open question that may block progress."""

    question: str
    blocking: bool

    def __post_init__(self):
        _require_nonempty(self.question, "OpenQuestion.question")
        if not isinstance(self.blocking, bool):
            raise ValueError(
                f"OpenQuestion.blocking must be a bool, got {type(self.blocking).__name__}"
            )


@dataclass
class DataFlowChain:
    """V2 Patch 6 — data-flow chain from user-action handler to write-boundary.

    Required when mode=bug AND symptom is presentation-layer (enforced at
    SpecSeeds level). Null otherwise.
    """

    handler_qn: str
    write_boundary_qn: str
    intermediate_qns: List[str]
    trace_mode: str  # one of _VALID_TRACE_MODE

    def __post_init__(self):
        _require_nonempty(self.handler_qn, "DataFlowChain.handler_qn")
        _require_nonempty(self.write_boundary_qn, "DataFlowChain.write_boundary_qn")
        if not isinstance(self.intermediate_qns, list):
            raise ValueError("DataFlowChain.intermediate_qns must be a list")
        _require_in_enum(self.trace_mode, _VALID_TRACE_MODE, "DataFlowChain.trace_mode")


@dataclass
class ValueSemantics:
    """V2 Patch 7 — id-stability axis classification for one value/symbol.

    stable_across_calls is required when classification=invariant AND symptom
    is presentation-layer (enforced at SpecSeeds level with the affected_areas
    heuristic). Accepted as None for domain-layer symptoms per V2 C4.
    """

    value: str
    classification: str           # one of _VALID_VALUE_CLASSIFICATION
    stable_across_calls: Optional[str]  # one of _VALID_STABLE_ACROSS_CALLS or None

    def __post_init__(self):
        _require_nonempty(self.value, "ValueSemantics.value")
        _require_in_enum(self.classification, _VALID_VALUE_CLASSIFICATION, "ValueSemantics.classification")
        if self.stable_across_calls is not None:
            _require_in_enum(
                self.stable_across_calls,
                _VALID_STABLE_ACROSS_CALLS,
                "ValueSemantics.stable_across_calls",
            )


@dataclass
class ValueProductionSite:
    """V2 Patch 7 — one site where a value is produced/assigned.

    file_line rejects the '(none)' sentinel — archaeology requires a real path.
    is_stable=False means the production site rewrites the value per call
    (Math.random / Date.now / uuid pattern).
    """

    value: str
    file_line: str
    is_stable: bool

    def __post_init__(self):
        _require_nonempty(self.value, "ValueProductionSite.value")
        _require_nonempty(self.file_line, "ValueProductionSite.file_line")
        if self.file_line.strip() == "(none)":
            raise ValueError(
                "ValueProductionSite.file_line rejects '(none)' sentinel — "
                "a real path:line is required"
            )
        if not isinstance(self.is_stable, bool):
            raise ValueError(
                f"ValueProductionSite.is_stable must be a bool, got {type(self.is_stable).__name__}"
            )


@dataclass
class SupplyChangingCommit:
    """One commit that changed HOW a literal's value is SUPPLIED (a prop
    removed from a parent, a default relocated, a flag stripped from a
    caller) -- found by the plan-73-Phase-1 widened sweep over
    `git log <introducing-sha>..HEAD` on the literal's file AND its
    already-enumerated inbound callers. This dataclass is only the
    CARRIER for that sweep's output; the sweep itself is orchestrator
    prose in a later step, not built here.

    sha / subject are validated the same way LiteralArchaeology's own
    introduced_by / commit_subject are: sha is a 7-40 char hex commit SHA,
    subject is a non-empty one-line commit subject.
    """

    sha: str
    subject: str

    def __post_init__(self):
        _require_nonempty(self.sha, "SupplyChangingCommit.sha")
        if not _COMMIT_SHA_RE.match(self.sha):
            raise ValueError(
                f"SupplyChangingCommit.sha must be a 7-40 char hex commit SHA, "
                f"got {self.sha!r}"
            )
        _require_nonempty(self.subject, "SupplyChangingCommit.subject")


@dataclass
class LiteralArchaeology:
    """V3 Patch 8 — git-archaeology record for one hardcoded literal proposed for
    replacement, OR (plan 73 D2) cited as evidence for a scope call.

    introduced_by must be a 7-40 char hex commit SHA.
    introduced_when must parse as an ISO date (YYYY-MM-DD).
    file_line rejects the '(none)' sentinel.
    intent must be one of the 6-value locked enum.

    use (plan 73 OQ-5, added last with a default so a pre-plan-73
    handoff.json without the key deserializes cleanly): "fix-layer" (the
    literal IS the thing being replaced -- the original V3 Patch 8 use case)
    or "evidence" (the literal's CURRENT value was cited as grounds for a
    scope call; nothing is being replaced). Every row recorded before this
    field existed is unambiguously "fix-layer" -- that is the back-compat
    default. See PlanSeeds._validate_cross_field for how `use` scopes the
    escalation-cite requirement.

    supply_changing_commits (plan 73 Phase 1, the widened-window sweep;
    appended LAST, after `use`, so a handoff.json predating this field
    deserializes unchanged) is a SEARCH-STEP carrier,
    not a gate: this field's presence, absence, or content MUST NOT be
    validated as a requirement anywhere (no __post_init__ raise keyed on
    it beyond shape-checking the type of a value that IS supplied; no
    finalize-handoff exit code keyed on it; no verify check numbered or
    otherwise). Its THREE states are load-bearing and must stay
    distinguishable end to end:
      - None  -- the widened sweep was NOT RUN for this literal.
      - []    -- the sweep RAN and found nothing since introduced_by.
      - [SupplyChangingCommit, ...] -- the sweep ran and found these.
    This deliberately mirrors EvidenceLanes' None-vs-False reasoning
    elsewhere in this module (see that class's docstring): collapsing
    None into [] would destroy the distinction between "never looked"
    and "looked, found nothing" that this field exists to preserve. DO
    NOT default this to `field(default_factory=list)` -- that collapses
    the not-run state into the found-nothing state and defeats the
    field's entire purpose.
    """

    literal: str
    file_line: str
    introduced_by: str
    introduced_when: str   # ISO date string YYYY-MM-DD
    commit_subject: str
    intent: str            # one of _VALID_LITERAL_INTENT
    use: str = "fix-layer"  # one of _VALID_LITERAL_ARCHAEOLOGY_USE
    supply_changing_commits: Optional[List["SupplyChangingCommit"]] = None

    def __post_init__(self):
        _require_nonempty(self.literal, "LiteralArchaeology.literal")
        _require_nonempty(self.file_line, "LiteralArchaeology.file_line")
        if self.file_line.strip() == "(none)":
            raise ValueError(
                "LiteralArchaeology.file_line rejects '(none)' sentinel — "
                "a real path:line is required"
            )
        _require_nonempty(self.introduced_by, "LiteralArchaeology.introduced_by")
        if not _COMMIT_SHA_RE.match(self.introduced_by):
            raise ValueError(
                f"LiteralArchaeology.introduced_by must be a 7-40 char hex commit SHA, "
                f"got {self.introduced_by!r}"
            )
        _require_nonempty(self.introduced_when, "LiteralArchaeology.introduced_when")
        try:
            datetime.date.fromisoformat(self.introduced_when)
        except ValueError:
            raise ValueError(
                f"LiteralArchaeology.introduced_when must be an ISO date (YYYY-MM-DD), "
                f"got {self.introduced_when!r}"
            )
        _require_nonempty(self.commit_subject, "LiteralArchaeology.commit_subject")
        _require_in_enum(self.intent, _VALID_LITERAL_INTENT, "LiteralArchaeology.intent")
        _require_in_enum(self.use, _VALID_LITERAL_ARCHAEOLOGY_USE, "LiteralArchaeology.use")
        # supply_changing_commits (plan 73 Phase 1): SHAPE-only check of a
        # value that IS supplied -- None is always valid (sweep not run) and
        # is deliberately NOT coerced to []. This is not a requiredness gate
        # (nothing here raises on None or on an empty list); it only rejects
        # a malformed non-None value (wrong container type, or an element
        # that is not a SupplyChangingCommit).
        if self.supply_changing_commits is not None:
            if not isinstance(self.supply_changing_commits, list):
                raise ValueError(
                    "LiteralArchaeology.supply_changing_commits must be a list or "
                    f"None, got {type(self.supply_changing_commits).__name__}"
                )
            for commit in self.supply_changing_commits:
                if not isinstance(commit, SupplyChangingCommit):
                    raise ValueError(
                        "LiteralArchaeology.supply_changing_commits elements must be "
                        f"SupplyChangingCommit, got {type(commit).__name__}"
                    )


# ---------------------------------------------------------------------------
# Design anchor — plan 53 Phase 1.
# ---------------------------------------------------------------------------


@dataclass
class DesignAnchor:
    """Captured design intent — open-discriminator kind + source file + selectors.

    Plan 53 Phase 1: design intent as a first-class pipeline input, captured
    once at /research or /discover intake and carried into SpecSeeds.

    - kind is an OPEN discriminator (D3) at THIS layer — any string is
      shape-valid and deserializes cleanly here; only "html" is implemented
      downstream (verification/binding machinery), and an unrecognized kind
      resolves to NOT-COVERED there, never a schema error. This openness is
      about deserialization safety, not about what can be CAPTURED today —
      the one shipped capture setter (set-design-anchor) is narrower: it
      reuses parse_design_source(), which validates kind against a fixed
      recognized-scheme set (see _design/_source.py:_KNOWN_SCHEMES). So an
      arbitrary kind can arrive here via a hand-edited or future-producer
      handoff.json, but cannot be captured via the setter today.
    - file is the source file/URL path (e.g. "design/reference.html").
    - selectors is the list of intent selectors (e.g. [".fooBar"]); may be
      empty.

    Empty/unset anchor — {kind:"", file:"", selectors:[]} — is the valid
    default so an old handoff.json without a design_anchor key deserializes
    cleanly (back-compat).
    """

    kind: str = ""
    file: str = ""
    selectors: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.kind, str):
            raise ValueError(
                f"DesignAnchor.kind must be a string, got {type(self.kind).__name__}"
            )
        if not isinstance(self.file, str):
            raise ValueError(
                f"DesignAnchor.file must be a string, got {type(self.file).__name__}"
            )
        if not isinstance(self.selectors, list):
            raise ValueError("DesignAnchor.selectors must be a list")
        for s in self.selectors:
            if not isinstance(s, str):
                raise ValueError(
                    f"DesignAnchor.selectors elements must be strings, got {type(s).__name__!r}"
                )


# ---------------------------------------------------------------------------
# Spec seeds aggregate.
# ---------------------------------------------------------------------------


@dataclass
class SpecSeeds:
    """Spec-seeds block — all inputs /specify needs from /research.

    Cross-field validators enforced in __post_init__:
    - data_flow_chain required when mode=bug + presentation-layer symptom.
    - stable_across_calls required when invariant + presentation-layer symptom.
    - stable_across_calls="false" requires at least one matching value_production_sites row.
    - value_production_sites distinct (value, file_line) pairs.
    - literal_archaeology required when the recommended approach is a
      literal-replacement approach (mode-independent for handoffs written
      under the new regime, plan 73 D1; checked at Handoff level since it
      needs plan_seeds AND schema_version context -- schema_version-scoped
      for a handoff.json written before plan 73 shipped, see
      _requires_literal_archaeology_presence).
    - literal_archaeology distinct (literal, file_line) pairs.

    Note: mode is passed in from the Handoff constructor for cross-field checks.

    design_anchor (plan 53 Phase 1) is appended LAST and defaults to an
    empty DesignAnchor so an old handoff.json (pre-plan-53) without the key
    deserializes cleanly.
    """

    spec_type_hint: str
    constraints: List[Constraint]
    affected_areas: List[AffectedArea]
    risks: List[Risk]
    open_questions: List[OpenQuestion]
    value_semantics: List[ValueSemantics] = field(default_factory=list)
    value_production_sites: List[ValueProductionSite] = field(default_factory=list)
    literal_archaeology: List[LiteralArchaeology] = field(default_factory=list)
    data_flow_chain: Optional[DataFlowChain] = None
    design_anchor: DesignAnchor = field(default_factory=DesignAnchor)

    def __post_init__(self):
        _require_in_enum(self.spec_type_hint, _VALID_SPEC_TYPE_HINT, "SpecSeeds.spec_type_hint")
        if not isinstance(self.constraints, list):
            raise ValueError("SpecSeeds.constraints must be a list")
        if not isinstance(self.affected_areas, list):
            raise ValueError("SpecSeeds.affected_areas must be a list")
        if not isinstance(self.risks, list):
            raise ValueError("SpecSeeds.risks must be a list")
        if not isinstance(self.open_questions, list):
            raise ValueError("SpecSeeds.open_questions must be a list")
        if not isinstance(self.value_semantics, list):
            raise ValueError("SpecSeeds.value_semantics must be a list")
        if not isinstance(self.value_production_sites, list):
            raise ValueError("SpecSeeds.value_production_sites must be a list")
        if not isinstance(self.literal_archaeology, list):
            raise ValueError("SpecSeeds.literal_archaeology must be a list")
        if not isinstance(self.design_anchor, DesignAnchor):
            raise ValueError(
                f"SpecSeeds.design_anchor must be a DesignAnchor, "
                f"got {type(self.design_anchor).__name__}"
            )

        # V2: distinct (value, file_line) tuples for value_production_sites.
        seen_prod = set()  # type: ignore
        for vps in self.value_production_sites:
            key = (vps.value, vps.file_line)
            if key in seen_prod:
                raise ValueError(
                    f"SpecSeeds.value_production_sites duplicate row: "
                    f"(value={vps.value!r}, file_line={vps.file_line!r})"
                )
            seen_prod.add(key)

        # V3: distinct (literal, file_line) tuples for literal_archaeology.
        seen_arch = set()  # type: ignore
        for la in self.literal_archaeology:
            key = (la.literal, la.file_line)
            if key in seen_arch:
                raise ValueError(
                    f"SpecSeeds.literal_archaeology duplicate row: "
                    f"(literal={la.literal!r}, file_line={la.file_line!r})"
                )
            seen_arch.add(key)

    def _validate_cross_field(self, mode):
        # type: (str) -> None
        """Cross-field validators that need mode from the parent Handoff.

        Called by Handoff.__post_init__ after setting mode.
        """
        is_presentation = _is_presentation_layer_symptom(self.affected_areas)

        # V2: data_flow_chain required when bug + presentation-layer.
        if mode == "bug" and is_presentation and self.data_flow_chain is None:
            raise ValueError(
                "SpecSeeds.data_flow_chain is required when mode='bug' and "
                "affected_areas contain a presentation-layer file "
                "(.vue, .tsx, .jsx, .svelte, .html)"
            )

        # V2: stable_across_calls rules per value_semantics row.
        for vs in self.value_semantics:
            if vs.classification == "invariant" and is_presentation:
                if vs.stable_across_calls is None:
                    raise ValueError(
                        f"ValueSemantics.stable_across_calls is required when "
                        f"classification='invariant' and symptom is presentation-layer "
                        f"(value={vs.value!r})"
                    )

            # V2: stable_across_calls="false" requires a matching production site.
            if vs.stable_across_calls == "false":
                matching = [
                    vps for vps in self.value_production_sites
                    if vps.value == vs.value
                ]
                if not matching:
                    raise ValueError(
                        f"ValueSemantics stable_across_calls='false' requires at least "
                        f"one ValueProductionSite row with value={vs.value!r}"
                    )


# ---------------------------------------------------------------------------
# Plan seeds.
# ---------------------------------------------------------------------------


@dataclass
class CitedPattern:
    """One cited canonical pattern from CBM."""

    qn: str
    file_line: str

    def __post_init__(self):
        _require_nonempty(self.qn, "CitedPattern.qn")
        _require_nonempty(self.file_line, "CitedPattern.file_line")


@dataclass
class Alternative:
    """One alternative approach that was considered and rejected."""

    id: str
    summary: str
    rejected_reason: str

    def __post_init__(self):
        _require_nonempty(self.id, "Alternative.id")
        _require_nonempty(self.summary, "Alternative.summary")
        _require_nonempty(self.rejected_reason, "Alternative.rejected_reason")


@dataclass
class Complexity:
    """Complexity assessment for a recommended approach."""

    changes: str    # one of _VALID_COMPLEXITY
    risk: str       # one of _VALID_COMPLEXITY
    verify_cost: str  # one of _VALID_COMPLEXITY

    def __post_init__(self):
        _require_in_enum(self.changes, _VALID_COMPLEXITY, "Complexity.changes")
        _require_in_enum(self.risk, _VALID_COMPLEXITY, "Complexity.risk")
        _require_in_enum(self.verify_cost, _VALID_COMPLEXITY, "Complexity.verify_cost")


# ---------------------------------------------------------------------------
# Caller enumeration — plan 67 D6 (research handoff carry).
# ---------------------------------------------------------------------------


@dataclass
class FixPathHelper:
    """One helper touched by the fix — qn + its definition file:line.

    Copies a research_helper record-fix-path-helper row verbatim. file_line
    is the helper's DEFINITION location, not a call-site.
    """

    qn: str
    file_line: str

    def __post_init__(self):
        _require_nonempty(self.qn, "FixPathHelper.qn")
        _require_nonempty(self.file_line, "FixPathHelper.file_line")


@dataclass
class InboundCaller:
    """One inbound caller of a fix_path_helper — caller qn + call-site file:line.

    Copies a research_helper record-inbound-caller row verbatim.

    surface / scope / justification carry the optional per-caller
    classification a research_helper classify-caller-scope call augments
    the row with (plan 69 D5/WI-E, Step 2b — trace the caller UP to its
    user-facing entry point, then classify it in/out of scope for the
    change). All three default to "" so:
      - a handoff.json predating plan 69 deserializes cleanly (back-compat,
        same convention as CallerEnumeration's other fields), and
      - a row recorded via record-inbound-caller but never classified
        carries an explicit "unclassified" empty state rather than a
        fabricated value.
    Only scope is enum-validated (against _VALID_CALLER_SCOPE, "" meaning
    unclassified). surface / justification are not non-empty-enforced
    here -- classify-caller-scope already enforces non-empty at the
    setter boundary, so this schema stays a straight verbatim carrier
    rather than re-running a check the producer already ran.
    """

    helper_qn: str
    caller_qn: str
    file_line: str
    surface: str = ""
    scope: str = ""
    justification: str = ""

    def __post_init__(self):
        _require_nonempty(self.helper_qn, "InboundCaller.helper_qn")
        _require_nonempty(self.caller_qn, "InboundCaller.caller_qn")
        _require_nonempty(self.file_line, "InboundCaller.file_line")
        if not isinstance(self.surface, str):
            raise ValueError(
                f"InboundCaller.surface must be a string, got {type(self.surface).__name__}"
            )
        if not isinstance(self.justification, str):
            raise ValueError(
                f"InboundCaller.justification must be a string, got {type(self.justification).__name__}"
            )
        _require_in_enum(self.scope, _VALID_CALLER_SCOPE, "InboundCaller.scope")


@dataclass
class CallerEnumeration:
    """Phase 2.4c caller-enumeration carry (plan 67 D6 — the plan-66 seam).

    fix_path_helpers / inbound_callers copy research_helper's
    record-fix-path-helper / record-inbound-caller rows VERBATIM — no
    re-derivation, no lossy grouping. (Contrast SpecSeeds.affected_areas,
    built by _build_affected_areas, which groups fix_path_helpers by
    package and drops the helper qn + caller rows — that shape serves a
    different consumer and is untouched by this carry.)

    no_shared_callers_justification carries the check-8 escape text
    (research_helper record-no-shared-callers-justification) when the LLM
    asserted the touched symbol has zero other callers instead of
    recording helpers. Mutually exclusive with a non-empty
    fix_path_helpers by construction on the producer side (the research
    helper's setters reject the contradictory combination), but this
    schema does not re-enforce that invariant — it is a straight carrier.

    All three fields default empty/None so a handoff.json predating plan
    67 (or a report where Phase 2.4c never ran — e.g. non-bug mode before
    the check-8 mode-decouple) deserializes cleanly (back-compat).
    """

    fix_path_helpers: List[FixPathHelper] = field(default_factory=list)
    inbound_callers: List[InboundCaller] = field(default_factory=list)
    no_shared_callers_justification: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.fix_path_helpers, list):
            raise ValueError("CallerEnumeration.fix_path_helpers must be a list")
        for h in self.fix_path_helpers:
            if not isinstance(h, FixPathHelper):
                raise ValueError(
                    "CallerEnumeration.fix_path_helpers elements must be FixPathHelper, "
                    f"got {type(h).__name__}"
                )
        if not isinstance(self.inbound_callers, list):
            raise ValueError("CallerEnumeration.inbound_callers must be a list")
        for c in self.inbound_callers:
            if not isinstance(c, InboundCaller):
                raise ValueError(
                    "CallerEnumeration.inbound_callers elements must be InboundCaller, "
                    f"got {type(c).__name__}"
                )
        if self.no_shared_callers_justification is not None:
            _require_nonempty(
                self.no_shared_callers_justification,
                "CallerEnumeration.no_shared_callers_justification",
            )


@dataclass
class PlanSeeds:
    """Plan-seeds block — recommended approach + layer + complexity + V3 call shape.

    Cross-field validators enforced at Handoff level (needs mode context).
    """

    recommended_approach_id: str
    recommended_approach_summary: str
    layer_destination: str
    layer_justification: str
    complexity: Complexity
    cited_canonical_patterns: List[CitedPattern] = field(default_factory=list)
    alternatives_considered: List[Alternative] = field(default_factory=list)
    proposed_call_shape: Optional[str] = None

    # Provenance marker: True only when an explicit correctness-vetting step has
    # verified this recommendation bundle beyond token/enum shape-checks.
    # Default False because the current pipeline validates shape only (enum
    # membership and token-overlap); no step currently vets correctness.
    # A future correctness-vetting step would set this True.
    correctness_vetted: bool = False

    # Phase 2.4c caller-enumeration carry (plan 67 D6). Appended last with a
    # default so existing positional constructions keep working unchanged —
    # same convention as design_anchor on SpecSeeds.
    caller_enumeration: CallerEnumeration = field(default_factory=CallerEnumeration)

    # Internal flag set by parser when proposed_call_shape fails first-gate regex.
    # Exposed for tests to assert fail-soft behavior.
    _proposed_call_shape_parse_failed: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self):
        _require_nonempty(self.recommended_approach_id, "PlanSeeds.recommended_approach_id")
        _require_nonempty(self.recommended_approach_summary, "PlanSeeds.recommended_approach_summary")
        _require_nonempty(self.layer_destination, "PlanSeeds.layer_destination")
        _require_nonempty(self.layer_justification, "PlanSeeds.layer_justification")
        if not isinstance(self.complexity, Complexity):
            raise ValueError(
                "PlanSeeds.complexity must be a Complexity, got {0}".format(
                    type(self.complexity).__name__
                )
            )
        if not isinstance(self.cited_canonical_patterns, list):
            raise ValueError("PlanSeeds.cited_canonical_patterns must be a list")
        if not isinstance(self.alternatives_considered, list):
            raise ValueError("PlanSeeds.alternatives_considered must be a list")
        if not isinstance(self.caller_enumeration, CallerEnumeration):
            raise ValueError(
                "PlanSeeds.caller_enumeration must be a CallerEnumeration, got {0}".format(
                    type(self.caller_enumeration).__name__
                )
            )
        if not isinstance(self.correctness_vetted, bool):
            raise ValueError(
                "PlanSeeds.correctness_vetted must be a bool, got {0}".format(
                    type(self.correctness_vetted).__name__
                )
            )

        # Validate and parse proposed_call_shape when non-None.
        if self.proposed_call_shape is not None:
            _require_nonempty(self.proposed_call_shape, "PlanSeeds.proposed_call_shape")
            parse_failed, duplicate = _parse_proposed_call_shape(self.proposed_call_shape)
            if parse_failed:
                # Fail-soft: accept value but set advisory flag.
                object.__setattr__(self, '_proposed_call_shape_parse_failed', True)
            elif duplicate is not None:
                raise ValueError(
                    f"PlanSeeds.proposed_call_shape contains duplicate identifier "
                    f"{duplicate!r} across argument positions"
                )

    def _validate_cross_field(self, mode, spec_seeds, schema_version):
        # type: (str, SpecSeeds, str) -> None
        """Cross-field validators that need mode + spec_seeds + schema_version from Handoff.

        Called by Handoff.__post_init__. Checks are ordered so that the
        most-fundamental missing-data errors fire before secondary derived errors:
        1. literal_archaeology presence (required before we can check its rows).
        2. escalation cite per intent, scoped to `use="fix-layer"` rows only
           (requires non-empty literal_archaeology).
        3. proposed_call_shape presence (requires literal-replacement confirmed).

        schema_version (plan 73 OQ-5 Finding-2 fix) scopes check 1 ONLY --
        see _requires_literal_archaeology_presence. It does not affect check
        2 or 3: check 2 was already mode-independent before plan 73 (no
        regression to guard there), and check 3 is bug-mode-gated by a rule
        plan 69 left untouched.
        """
        summary = self.recommended_approach_summary
        is_literal_replacement = _has_literal_replacement(summary)
        is_single_layer = _is_single_layer_fix(self.layer_justification)

        # V3: literal_archaeology required when the recommended approach
        # proposes a literal replacement, per THIS module's own narrow
        # detector (_has_literal_replacement -- see its definition for how
        # this differs from verify check 17's broader shared detector).
        # Requiredness is mode-independent (plan 73 D1) for handoffs written
        # under the new regime, and schema_version-scoped for one written
        # under the old regime (plan 73 OQ-5 Finding-2 fix) -- see
        # _requires_literal_archaeology_presence for the full rule and why
        # this can't be a plain field default. Check this FIRST so the
        # error names the missing collection, not the secondary requirement
        # (proposed_call_shape) that depends on it.
        if is_literal_replacement:
            if (
                _requires_literal_archaeology_presence(mode, schema_version)
                and not spec_seeds.literal_archaeology
            ):
                raise ValueError(
                    "SpecSeeds.literal_archaeology must be non-empty when "
                    "recommended_approach_summary matches a literal-replacement pattern"
                )

        # V3: escalation cite required for certain literal_archaeology
        # intents, scoped to `use="fix-layer"` rows only (plan 73 D2/OQ-5).
        # An `evidence`-use row (the literal's value was cited as grounds
        # for a scope call, nothing is being replaced) has no fix-layer to
        # escalate -- demanding escalation prose for it is meaningless and
        # was Finding 1 of the plan-73 OQ-5 build. This loop is independent
        # of is_literal_replacement above and of schema_version: it was
        # already mode-independent before plan 73 D1 (no regression to
        # guard for schema_version), and a pre-plan-73 row has no `use`
        # field, which defaults to "fix-layer" (LiteralArchaeology.use) --
        # every row recorded before the evidence arm existed was
        # unambiguously fix-layer, so this loop's behavior on old rows is
        # byte-identical to before.
        for la in spec_seeds.literal_archaeology:
            if la.use != "fix-layer":
                continue
            if la.intent in _INTENTS_REQUIRING_ESCALATION:
                if not _has_escalation_cite(summary):
                    raise ValueError(
                        f"PlanSeeds.recommended_approach_summary must cite escalation "
                        f"of default-source (contain 'default', 'wrapper', 'caller', or "
                        f"'escalat') when literal_archaeology intent={la.intent!r}. "
                        f"Intent 'deliberate', 'generated', 'migrated' do not require this."
                    )

        # V3: proposed_call_shape required when bug + (single-layer OR literal-replacement).
        # This requiredness rule is bug-mode-gated -- unchanged by plan 69. It does
        # NOT mean the field is bug-mode-exclusive: plan 69 D6/WI-F widened the
        # producer-side storage (+ verify check 18) to mode-independent, so a
        # non-bug mode may legitimately carry a populated value here too; this
        # check simply never REQUIRES one outside bug mode.
        if mode == "bug" and (is_single_layer or is_literal_replacement):
            if self.proposed_call_shape is None:
                raise ValueError(
                    "PlanSeeds.proposed_call_shape is required when mode='bug' and "
                    "(layer_justification implies single-layer fix OR "
                    "recommended_approach_summary matches literal-replacement pattern)"
                )


# ---------------------------------------------------------------------------
# Probe block.
# ---------------------------------------------------------------------------


@dataclass
class FeasibilityCheck:
    """Feasibility flags for the probe."""

    data_shape_only: bool
    auth_required: bool
    network_dependent: bool
    timing_dependent: bool
    is_test_code: bool

    def __post_init__(self):
        for fname in ("data_shape_only", "auth_required", "network_dependent",
                      "timing_dependent", "is_test_code"):
            v = getattr(self, fname)
            if not isinstance(v, bool):
                raise ValueError(
                    f"FeasibilityCheck.{fname} must be a bool, got {type(v).__name__}"
                )


@dataclass
class Discriminator:
    """Discriminator conditions for the probe."""

    primary_confirms_if: str
    runner_up_confirms_if: str
    both_disproved_if: str
    production_site_check: Optional[str]  # non-None when any is_stable=False in value_production_sites

    def __post_init__(self):
        _require_nonempty(self.primary_confirms_if, "Discriminator.primary_confirms_if")
        _require_nonempty(self.runner_up_confirms_if, "Discriminator.runner_up_confirms_if")
        _require_nonempty(self.both_disproved_if, "Discriminator.both_disproved_if")
        if self.production_site_check is not None:
            if not isinstance(self.production_site_check, str) or not self.production_site_check.strip():
                raise ValueError(
                    "Discriminator.production_site_check must be a non-empty string or None"
                )


@dataclass
class Probe:
    """Probe-tier classification block.

    Tier interlocks enforced in __post_init__:
    - feasibility_check.is_test_code=True AND tier='1' → rejected (circular).
    - tier='1' → test_framework non-None AND test_path non-empty.
    - tier='1.5' → script_path non-empty AND test_framework is None.
    """

    tier: str            # one of _VALID_PROBE_TIER
    actor: str           # one of _VALID_PROBE_ACTOR
    discriminator: Discriminator
    feasibility_check: FeasibilityCheck
    test_framework: Optional[str]   # one of _VALID_TEST_FRAMEWORK or None
    test_path: Optional[str]
    script_path: Optional[str]
    is_first_test_for_file: bool

    def __post_init__(self):
        _require_in_enum(self.tier, _VALID_PROBE_TIER, "Probe.tier")
        _require_in_enum(self.actor, _VALID_PROBE_ACTOR, "Probe.actor")
        if not isinstance(self.discriminator, Discriminator):
            raise ValueError(
                f"Probe.discriminator must be a Discriminator, got {type(self.discriminator).__name__}"
            )
        if not isinstance(self.feasibility_check, FeasibilityCheck):
            raise ValueError(
                f"Probe.feasibility_check must be a FeasibilityCheck, got {type(self.feasibility_check).__name__}"
            )
        if not isinstance(self.is_first_test_for_file, bool):
            raise ValueError(
                f"Probe.is_first_test_for_file must be a bool, got {type(self.is_first_test_for_file).__name__}"
            )

        # Validate test_framework enum when present.
        if self.test_framework is not None:
            _require_in_enum(self.test_framework, _VALID_TEST_FRAMEWORK, "Probe.test_framework")

        # Tier interlocks.
        if self.feasibility_check.is_test_code and self.tier == "1":
            raise ValueError(
                "Probe.tier='1' is rejected when feasibility_check.is_test_code=True "
                "(circular: tier-1 probe of test code is meaningless)"
            )

        if self.tier == "1":
            if self.test_framework is None:
                raise ValueError(
                    "Probe.test_framework must be non-None when tier='1'"
                )
            if not self.test_path or not self.test_path.strip():
                raise ValueError(
                    "Probe.test_path must be non-empty when tier='1'"
                )

        if self.tier == "1.5":
            if not self.script_path or not self.script_path.strip():
                raise ValueError(
                    "Probe.script_path must be non-empty when tier='1.5'"
                )
            if self.test_framework is not None:
                raise ValueError(
                    "Probe.test_framework must be None when tier='1.5' "
                    "(tier-1.5 uses a script, not a test suite)"
                )


# ---------------------------------------------------------------------------
# Outcome block.
# ---------------------------------------------------------------------------


@dataclass
class Outcome:
    """Outcome block — filled by `append-outcome` after probe runs.

    confidence_grade is derived from (tier, evidence_source, hypothesis_confirmed,
    has_production_site_check) via compute_confidence_grade(); __post_init__
    validates that the stored value matches.
    """

    hypothesis_confirmed: str    # one of _VALID_HYPOTHESIS_CONFIRMED
    evidence_source: str         # one of _VALID_EVIDENCE_SOURCE
    evidence_cite: str
    actual_fix_path: str
    confirmed_date: str          # ISO-8601
    confidence_grade: str        # one of _VALID_CONFIDENCE_GRADE
    delta_from_recommendation: Optional[str] = None
    confirmed_commit_sha: Optional[str] = None

    def __post_init__(self):
        _require_in_enum(self.hypothesis_confirmed, _VALID_HYPOTHESIS_CONFIRMED, "Outcome.hypothesis_confirmed")
        _require_in_enum(self.evidence_source, _VALID_EVIDENCE_SOURCE, "Outcome.evidence_source")
        _require_nonempty(self.evidence_cite, "Outcome.evidence_cite")
        _require_nonempty(self.actual_fix_path, "Outcome.actual_fix_path")
        _require_nonempty(self.confirmed_date, "Outcome.confirmed_date")
        _require_in_enum(self.confidence_grade, _VALID_CONFIDENCE_GRADE, "Outcome.confidence_grade")
        # ISO-8601 date parse check.
        try:
            datetime.date.fromisoformat(self.confirmed_date[:10])
        except ValueError:
            raise ValueError(
                f"Outcome.confirmed_date must be an ISO-8601 date, got {self.confirmed_date!r}"
            )
        # Commit SHA format: 7-40 hex chars, lowercase only.
        if self.confirmed_commit_sha is not None:
            if not _COMMIT_SHA_RE.match(self.confirmed_commit_sha):
                raise ValueError(
                    f"Outcome.confirmed_commit_sha must be 7-40 lowercase hex chars, "
                    f"got {self.confirmed_commit_sha!r}"
                )

    def _validate_grade(self, tier, has_production_site_check):
        # type: (str, bool) -> None
        """Validate confidence_grade against the derivation function.

        Called by Handoff.__post_init__ with probe context.
        """
        expected = compute_confidence_grade(
            tier=tier,
            evidence_source=self.evidence_source,
            hypothesis_confirmed=self.hypothesis_confirmed,
            has_production_site_check=has_production_site_check,
        )
        if self.confidence_grade != expected:
            raise ValueError(
                f"Outcome.confidence_grade={self.confidence_grade!r} does not match "
                f"derived grade={expected!r} for "
                f"(tier={tier!r}, evidence_source={self.evidence_source!r}, "
                f"hypothesis_confirmed={self.hypothesis_confirmed!r}, "
                f"has_production_site_check={has_production_site_check})"
            )


# ---------------------------------------------------------------------------
# Downstream links.
# ---------------------------------------------------------------------------


@dataclass
class DownstreamLinks:
    """Back-references filled as the artefact flows through the pipeline."""

    spec_path: Optional[str] = None
    plan_path: Optional[str] = None
    execute_task_commit_shas: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not isinstance(self.execute_task_commit_shas, list):
            raise ValueError("DownstreamLinks.execute_task_commit_shas must be a list")


# ---------------------------------------------------------------------------
# Evidence lanes — plan 73 D7.
# ---------------------------------------------------------------------------


@dataclass
class EvidenceLanes:
    """Plan 73 D7 -- self-declared record of which evidence lanes this
    research run consulted: static graph (CBM) / text search / runtime
    probe / history (git archaeology, Phase 2.5b).

    This is the "not-covered evidence-lane declaration": the report must
    say which lanes it consulted so structural confidence stops implying
    completeness. The plan-73 incident's laundering half was that a
    report's mandatory runner-up-framing / falsifier machinery can fire
    correctly while zero history-lane evidence backs any of it, and
    nothing in a structurally-complete report said so -- a reader could
    not tell "the history lane found nothing" from "the history lane
    never ran". Precedents: plan 53's NOT-COVERED coverage verdict, plan
    62's honest-scope strings.

    Gate on the DECLARATION existing, never on any lane's VALUE (D7): no
    field here is Optional, so every Handoff carries a complete 4-lane
    record -- a lane is either declared consulted or declared
    not-consulted, never simply absent from the artefact -- but no field
    is required to be True. A run legitimately consults a subset of the
    four lanes; what it must not do is leave that fact unrecorded.
    finalize-handoff (_cmds_handoff.py) enforces this at the REPORT-STATE
    layer with a call-happened guard mirroring probe_feasibility's
    completeness guard -- it asks only whether set-evidence-lanes was
    called at least once (report.evidence_lanes' four fields default to
    None/unset, not False, precisely so "never declared" is distinguishable
    from "declared false" at that layer); it never inspects which lane
    values were recorded, so it stays a call-happened check, not a
    per-lane-value check. THIS schema layer stays simpler on purpose: by
    the time a report reaches _build_evidence_lanes() (which the guard
    above has already required to be non-empty-of-None), every field is
    coerced `bool(...)`, so the persisted EvidenceLanes itself only ever
    needs to represent the two states a fully-declared record can be in --
    consulted or not-consulted -- never "undeclared". A hand-constructed
    or reconstructed (_dict_to_dataclass) Handoff that never passed through
    that guard (e.g. a legacy handoff.json) still gets an all-False default
    here, which is the correct back-compat reading for an artefact that
    predates this field entirely.

    Back-compat: all four fields default False so a handoff.json
    predating plan 73 D7 (no evidence_lanes key at all) deserializes
    cleanly.
    """

    static_graph: bool = False
    text_search: bool = False
    runtime_probe: bool = False
    history: bool = False

    def __post_init__(self):
        for fname in ("static_graph", "text_search", "runtime_probe", "history"):
            v = getattr(self, fname)
            if not isinstance(v, bool):
                raise ValueError(
                    f"EvidenceLanes.{fname} must be a bool, got {type(v).__name__}"
                )


# ---------------------------------------------------------------------------
# Top-level Handoff record.
# ---------------------------------------------------------------------------


@dataclass
class Handoff:
    """Top-level handoff.json record.

    Owns all cross-field invariant validation in __post_init__:
    - schema_version must equal SCHEMA_VERSION.
    - All sub-record cross-field checks (data_flow_chain, stable_across_calls,
      literal_archaeology, proposed_call_shape, production_site_check,
      confidence_grade) are delegated to sub-record _validate_cross_field()
      methods with the mode context they need. plan_seeds' also needs
      schema_version (plan 73 OQ-5 Finding-2 fix — see
      _requires_literal_archaeology_presence), since reconstructing an
      already-persisted handoff.json (e.g. specify's import-handoff, via
      _dict_to_dataclass) re-runs this same validation and must honor the
      rules the artifact was WRITTEN under, not the rules live in the code
      doing the reading.

    evidence_lanes (plan 73 D7) is appended LAST with a default so an old
    handoff.json (pre-plan-73-D7) without the key deserializes cleanly —
    same convention as design_anchor on SpecSeeds and caller_enumeration
    on PlanSeeds.
    """

    schema_version: str
    research_path: str
    research_completed_at: str
    mode: str              # one of _VALID_MODE
    intent: Intent
    spec_seeds: SpecSeeds
    plan_seeds: PlanSeeds
    probe: Probe
    downstream_links: DownstreamLinks
    outcome: Optional[Outcome] = None
    evidence_lanes: EvidenceLanes = field(default_factory=EvidenceLanes)

    def __post_init__(self):
        # schema_version check: accept all shipped versions:
        # 1.0 (original), 1.1 (added verbatim_prompt), 1.2 (plan 73 D1 —
        # literal_archaeology presence gate became mode-independent for
        # handoffs stamped at this version or later; see
        # _requires_literal_archaeology_presence).
        _ACCEPTED_SCHEMA_VERSIONS = frozenset({"1.0", "1.1", "1.2"})
        if self.schema_version not in _ACCEPTED_SCHEMA_VERSIONS:
            raise ValueError(
                f"Handoff.schema_version must be one of {sorted(_ACCEPTED_SCHEMA_VERSIONS)!r}, "
                f"got {self.schema_version!r}"
            )

        _require_nonempty(self.research_path, "Handoff.research_path")
        _require_nonempty(self.research_completed_at, "Handoff.research_completed_at")
        _require_in_enum(self.mode, _VALID_MODE, "Handoff.mode")

        if not isinstance(self.intent, Intent):
            raise ValueError(f"Handoff.intent must be an Intent, got {type(self.intent).__name__}")
        if not isinstance(self.spec_seeds, SpecSeeds):
            raise ValueError(f"Handoff.spec_seeds must be a SpecSeeds, got {type(self.spec_seeds).__name__}")
        if not isinstance(self.plan_seeds, PlanSeeds):
            raise ValueError(f"Handoff.plan_seeds must be a PlanSeeds, got {type(self.plan_seeds).__name__}")
        if not isinstance(self.probe, Probe):
            raise ValueError(f"Handoff.probe must be a Probe, got {type(self.probe).__name__}")
        if not isinstance(self.downstream_links, DownstreamLinks):
            raise ValueError(
                f"Handoff.downstream_links must be a DownstreamLinks, "
                f"got {type(self.downstream_links).__name__}"
            )
        if not isinstance(self.evidence_lanes, EvidenceLanes):
            raise ValueError(
                f"Handoff.evidence_lanes must be an EvidenceLanes, "
                f"got {type(self.evidence_lanes).__name__}"
            )

        # Cross-field validation requiring mode context.
        self.spec_seeds._validate_cross_field(self.mode)
        self.plan_seeds._validate_cross_field(self.mode, self.spec_seeds, self.schema_version)

        # V2: probe.discriminator.production_site_check required when any is_stable=False.
        has_unstable = any(
            not vps.is_stable for vps in self.spec_seeds.value_production_sites
        )
        if has_unstable and self.probe.discriminator.production_site_check is None:
            raise ValueError(
                "Probe.discriminator.production_site_check must be non-None when "
                "any SpecSeeds.value_production_sites[*].is_stable is False"
            )

        # Outcome cross-field validation.
        if self.outcome is not None:
            has_production_site_check = (
                self.probe.discriminator.production_site_check is not None
            )
            self.outcome._validate_grade(
                tier=self.probe.tier,
                has_production_site_check=has_production_site_check,
            )
