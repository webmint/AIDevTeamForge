"""handoff_schema -- dataclass schema for the breakdown-handoff artefact.

Single source of truth for the shape of ``specs/NNN-<slug>/breakdown-handoff.json``
emitted by ``breakdown_helper finalize-handoff`` and consumed by ``/implement``
(consumer not yet implemented; will conform to this schema).

Design notes:

- Dataclasses are pure records. No serialization (to_dict / from_dict),
  no rendering, no I/O. Those responsibilities live in the helper command
  layer (breakdown_helper.py) so this schema stays small and independently testable.

- Schema-level validation runs in __post_init__ and is mechanical:
    * Required string fields are non-empty after .strip().
    * Nested records receive isinstance checks at the Breakdown level.
    * handoff_kind is a constant "breakdown" -- any other value is rejected.
    * Provenance co-vary invariant: upstream_handoff_path and
      upstream_handoff_kind must both be set or both be None.

- handoff_kind is a CONSTANT "breakdown" -- any other value is rejected.
  breakdown_helper.finalize-handoff is the only producer.

- TaskRow.review_checkpoint is a strict bool (int is rejected). The
  isinstance(x, bool) guard accepts True/False and rejects int values
  (including 1/0), because bool is a subclass of int so a plain int does
  not pass an isinstance(x, bool) test.

- TaskRow.ac_addressed may be empty at schema level. The rule that each task
  must address at least one AC is enforced by the helper command layer, NOT
  by this schema.

- Type-hint convention: explicit typing.Optional / List
  (no PEP 604 X | None, no PEP 585 list[str]). Targets Python 3.8+.
  from __future__ import annotations intentionally NOT used so
  __post_init__ introspection sees real type objects.

Stdlib only. No third-party dependencies.
"""

from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Schema version constant.
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0"
HANDOFF_KIND = "breakdown"

# ---------------------------------------------------------------------------
# Allowed values for Provenance.upstream_handoff_kind.
# ---------------------------------------------------------------------------

_VALID_UPSTREAM_HANDOFF_KIND = ("plan",)

REVIEW_CHECKPOINT_ENUM = (True, False)  # type: tuple

# ---------------------------------------------------------------------------
# Allowed values for DeadCodeRow.kind (plan 71 D8(b) passthrough).
# ---------------------------------------------------------------------------

DEAD_CODE_KIND_ENUM = ("arm", "function", "param", "import", "branch")

# ---------------------------------------------------------------------------
# Validation helpers.
# (Self-contained so this schema is independently importable without
# cross-dependency on other schema modules.)
# ---------------------------------------------------------------------------


def _require_nonempty(value, field_name):
    # type: (object, str) -> None
    """Raise ValueError if value is not a non-empty (post-strip) string."""
    if not isinstance(value, str):
        raise ValueError(
            "{0} must be a string, got {1}".format(field_name, type(value).__name__)
        )
    if value.strip() == "":
        raise ValueError("{0} must be a non-empty string".format(field_name))


def _require_in_enum(value, allowed, field_name):
    # type: (object, tuple, str) -> None
    """Raise ValueError if value is not in allowed."""
    if value not in allowed:
        raise ValueError(
            "{0} must be one of {1}, got {2!r}".format(
                field_name, sorted(allowed), value
            )
        )


# ---------------------------------------------------------------------------
# TaskRow -- one task record in the breakdown.
# ---------------------------------------------------------------------------


@dataclass
class TaskRow:
    """One task in the breakdown task list.

    number is a zero-padded string (e.g. "001"); padding is NOT validated here —
    the producer is responsible for zero-padding. Only non-empty is required.
    agent is the assigned agent name; the roster is NOT validated at THIS schema
    layer — only non-empty is required. Roster membership (the agent exists in the
    project's .claude/agents/) is enforced by the helper layer: breakdown_helper
    verify-agent-roster (the /breakdown Phase 3.5 gate) and finalize-handoff.
    review_checkpoint is a strict bool. int (including 1/0) is rejected.
    ac_addressed may be empty; the ≥1 AC rule is enforced by the helper layer.
    All list fields may be empty lists.
    """

    number: str
    title: str
    agent: str
    depends_on: List[str]
    blocks: List[str]
    touched_files: List[str]
    expects: List[str]
    produces: List[str]
    ac_addressed: List[str]
    doc_refs: List[str]
    review_checkpoint: bool

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.number, "TaskRow.number")
        _require_nonempty(self.title, "TaskRow.title")
        _require_nonempty(self.agent, "TaskRow.agent")

        for fname in (
            "depends_on",
            "blocks",
            "touched_files",
            "expects",
            "produces",
            "ac_addressed",
            "doc_refs",
        ):
            val = getattr(self, fname)
            if not isinstance(val, list):
                raise ValueError(
                    "TaskRow.{0} must be a list".format(fname)
                )

        # Strict bool check: bool is a subclass of int, so isinstance(x, int)
        # would accept True/False AND 1/0. We want only bool.
        if not isinstance(self.review_checkpoint, bool):
            raise ValueError(
                "TaskRow.review_checkpoint must be a bool, "
                "got {0}".format(type(self.review_checkpoint).__name__)
            )


# ---------------------------------------------------------------------------
# Nested record: Provenance.
# ---------------------------------------------------------------------------


@dataclass
class Provenance:
    """Upstream handoff provenance for the breakdown-handoff artefact.

    Upstream refers to the sibling plan handoff (specs/NNN/plan-handoff.json).
    Both upstream_handoff_path and upstream_handoff_kind must be set or
    both must be None (co-vary invariant). plan_path points to plan.md
    (best-effort, may be None). spec_path points to spec.md (best-effort,
    may be None).
    """

    upstream_handoff_path: Optional[str] = None
    upstream_handoff_kind: Optional[str] = None
    plan_path: Optional[str] = None
    spec_path: Optional[str] = None

    def __post_init__(self):
        # type: () -> None
        if self.upstream_handoff_path is not None:
            if not isinstance(self.upstream_handoff_path, str):
                raise ValueError(
                    "Provenance.upstream_handoff_path must be a string or None, "
                    "got {0}".format(type(self.upstream_handoff_path).__name__)
                )
            _require_nonempty(
                self.upstream_handoff_path, "Provenance.upstream_handoff_path"
            )

        if self.upstream_handoff_kind is not None:
            if not isinstance(self.upstream_handoff_kind, str):
                raise ValueError(
                    "Provenance.upstream_handoff_kind must be a string or None, "
                    "got {0}".format(type(self.upstream_handoff_kind).__name__)
                )
            _require_nonempty(
                self.upstream_handoff_kind, "Provenance.upstream_handoff_kind"
            )
            _require_in_enum(
                self.upstream_handoff_kind,
                _VALID_UPSTREAM_HANDOFF_KIND,
                "Provenance.upstream_handoff_kind",
            )

        if self.plan_path is not None:
            if not isinstance(self.plan_path, str):
                raise ValueError(
                    "Provenance.plan_path must be a string or None, "
                    "got {0}".format(type(self.plan_path).__name__)
                )
            _require_nonempty(self.plan_path, "Provenance.plan_path")

        if self.spec_path is not None:
            if not isinstance(self.spec_path, str):
                raise ValueError(
                    "Provenance.spec_path must be a string or None, "
                    "got {0}".format(type(self.spec_path).__name__)
                )
            _require_nonempty(self.spec_path, "Provenance.spec_path")

        # Co-vary invariant: path and kind must both be set or both be None.
        if (self.upstream_handoff_path is None) != (self.upstream_handoff_kind is None):
            raise ValueError(
                "Provenance.upstream_handoff_path and upstream_handoff_kind must "
                "both be set or both be None; got path={0!r}, kind={1!r}".format(
                    self.upstream_handoff_path, self.upstream_handoff_kind
                )
            )


# ---------------------------------------------------------------------------
# DeadCodeRow -- passthrough carrier for plan-declared change-induced dead
# code (plan 71 D8(b)).
# ---------------------------------------------------------------------------


@dataclass
class DeadCodeRow:
    """One dead-code row carried from the sibling plan-handoff.json.

    Self-contained duplicate of _plan.handoff_schema.DeadCodeRow (same
    shape, same validation) -- this schema module stays independently
    importable without a cross-dependency on _plan.handoff_schema (see the
    design notes above). Columns mirror the plan.md ### Change-Induced Dead
    Code table: File | Anchor token | Kind | Why dead.

    kind classifies what the anchor names -- "arm" is a switch/match/case
    arm; "branch" is an if/else (or ternary) conditional branch; the two
    are distinct kinds even though both are conditional-dispatch shapes.
    anchor_token must NOT contain a semicolon -- the '**Dead code
    removal**:' task field's value is a semicolon-separated list of anchor
    tokens (plan 71 D9); a literal token containing a semicolon (e.g. a
    C-style for-loop header) cannot be carried through that field
    unambiguously, so construction raises ValueError.

    Populated only when /plan declared change-induced dead code (plan 71
    D3); breakdown_helper finalize-handoff reads
    breakdown_seeds.dead_code_rows from the sibling plan-handoff.json and
    copies each row here verbatim (a pure passthrough -- this schema layer
    re-validates, but invents nothing). The /verify removal-confirmation
    check (plan 71 D8(b), Phase 4) reads this passthrough directly from
    breakdown-handoff.json, which /verify already reads for other purposes,
    rather than /verify reading plan-handoff.json directly.
    """

    file: str
    anchor_token: str
    kind: str
    why_dead: str

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.file, "DeadCodeRow.file")
        _require_nonempty(self.anchor_token, "DeadCodeRow.anchor_token")
        if ";" in self.anchor_token:
            raise ValueError(
                "DeadCodeRow.anchor_token must not contain ';' -- the "
                "'**Dead code removal**:' task field's value is "
                "semicolon-delimited (plan 71 D9); a literal anchor token "
                "containing a semicolon (e.g. a C-style for-loop header) "
                "cannot be carried through that field unambiguously"
            )
        _require_in_enum(self.kind, DEAD_CODE_KIND_ENUM, "DeadCodeRow.kind")
        _require_nonempty(self.why_dead, "DeadCodeRow.why_dead")


# ---------------------------------------------------------------------------
# Top-level Breakdown record.
# ---------------------------------------------------------------------------


@dataclass
class Breakdown:
    """Top-level breakdown-handoff.json record.

    handoff_kind is a constant 'breakdown' -- any other value is rejected.
    tasks_dir and breakdown_completed_at are required non-empty strings.
    provenance points at the sibling plan handoff (both-set-or-both-null).
    tasks is a list of TaskRow records (list-ness validated; element types
    are NOT deep-validated here -- mirrors how _plan.Handoff treats list fields
    in BreakdownSeeds).
    additions is a list of free-form note strings (may be empty).
    dependency_graph is a string rendering of the dependency graph (may be "").
    dead_code_rows is the plan 71 D8(b) passthrough carrier: a list of
    DeadCodeRow records copied verbatim from the sibling plan-handoff.json's
    breakdown_seeds.dead_code_rows (empty when /plan declared none, or when
    the sibling plan-handoff.json is absent/unreadable at breakdown-handoff
    build time). Appended LAST with a default so existing positional
    constructions keep working unchanged (list-ness validated only, same as
    tasks/additions -- element types are not deep-validated here).
    """

    schema_version: str
    handoff_kind: str
    tasks_dir: str
    breakdown_completed_at: str
    provenance: Provenance
    tasks: List[TaskRow]
    additions: List[str]
    dependency_graph: str
    dead_code_rows: List[DeadCodeRow] = field(default_factory=list)

    def __post_init__(self):
        # type: () -> None
        # schema_version lock.
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(
                "Breakdown.schema_version must be {0!r}, "
                "got {1!r}".format(SCHEMA_VERSION, self.schema_version)
            )

        # handoff_kind constant.
        if self.handoff_kind != HANDOFF_KIND:
            raise ValueError(
                "Breakdown.handoff_kind must be 'breakdown', "
                "got {0!r}".format(self.handoff_kind)
            )

        _require_nonempty(self.tasks_dir, "Breakdown.tasks_dir")
        _require_nonempty(self.breakdown_completed_at, "Breakdown.breakdown_completed_at")

        if not isinstance(self.provenance, Provenance):
            raise ValueError(
                "Breakdown.provenance must be a Provenance, "
                "got {0}".format(type(self.provenance).__name__)
            )

        if not isinstance(self.tasks, list):
            raise ValueError(
                "Breakdown.tasks must be a list"
            )

        if not isinstance(self.additions, list):
            raise ValueError(
                "Breakdown.additions must be a list"
            )

        if not isinstance(self.dependency_graph, str):
            raise ValueError(
                "Breakdown.dependency_graph must be a string, "
                "got {0}".format(type(self.dependency_graph).__name__)
            )

        if not isinstance(self.dead_code_rows, list):
            raise ValueError(
                "Breakdown.dead_code_rows must be a list"
            )
