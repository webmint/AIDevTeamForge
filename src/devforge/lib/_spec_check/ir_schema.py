"""ir_schema -- pure IR dataclasses for the /spec-check acceptance-criteria solver.

Provides ``Variable``, ``Atom``, ``Constraint``, ``Coverage``, and the
top-level container ``SpecCheckIR``, plus the ``SORTS``, ``COMPARISON_OPS``,
``CONSTRAINT_KINDS``, and ``COVERAGE_STATUSES`` module constants.

What this is: the normalized intermediate representation an LLM (in a later
phase) translates a feature spec's acceptance criteria into, so a deterministic
Z3 solver (``_solve.py``, this same subpackage) can prove the AC set is
self-consistent (or extract a minimal conflicting subset when it is not).

Design notes:

- Dataclasses are pure records. No serialization (to_dict / from_dict), no
  rendering, no I/O, no LLM-JSON parsing. Those responsibilities live in a
  later phase's ``_consume.py`` so this schema stays small and independently
  testable.

- Schema-level validation runs in __post_init__ and is mechanical (field-local
  only). Cross-record validation -- "every atom's var is declared in
  variables", "coverage accounts for every AC" -- is explicitly OUT of scope
  here; it belongs to a later phase's consumer. The one exception is
  ``_solve.py``'s build step, which must resolve every atom's var against the
  variable table in order to construct the corresponding Z3 constant -- that
  check is unavoidable at solve time, not a schema concern.

- Type-hint convention: explicit typing.List / typing.Optional per house
  convention. PEP 604 ``X | None`` / PEP 585 ``list[str]`` syntax and
  ``from __future__ import annotations`` are not used in this subpackage.
  Targets Python 3.8+.

Stdlib only. No third-party dependencies. (``_solve.py`` in this same
subpackage imports z3; this module does not.)
"""

from dataclasses import dataclass
from typing import List, Optional

# ---------------------------------------------------------------------------
# Allowed enum values.
# ---------------------------------------------------------------------------

SORTS = ("Int", "Real", "Bool", "Enum")

COMPARISON_OPS = ("<", "<=", "=", "!=", ">", ">=")

CONSTRAINT_KINDS = ("assertion", "implication")

COVERAGE_STATUSES = ("formalized", "skipped_prose", "skipped_unsupported")

# ---------------------------------------------------------------------------
# Validation helpers.
# (Self-contained so this schema is independently importable.)
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
                field_name, list(allowed), value
            )
        )


# ---------------------------------------------------------------------------
# Variable.
# ---------------------------------------------------------------------------


@dataclass
class Variable:
    """A declared IR variable.

    name is the variable identifier; non-empty.
    sort must be one of SORTS ("Int", "Real", "Bool", "Enum").
    gloss is a human-readable one-line description; non-empty and load-bearing
      -- it is what a human reads to catch a bad LLM translation, so an empty
      gloss is a schema error, not merely a style nit.
    domain is required (non-empty list of non-empty, non-duplicate str) IFF
      sort == "Enum"; it MUST be None for the other three sorts.
    """

    name: str
    sort: str
    gloss: str
    domain: Optional[List[str]] = None

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.name, "Variable.name")
        _require_in_enum(self.sort, SORTS, "Variable.sort")
        _require_nonempty(self.gloss, "Variable.gloss")

        if self.sort == "Enum":
            if self.domain is None:
                raise ValueError(
                    "Variable.domain is required when sort='Enum'"
                )
            if not isinstance(self.domain, list):
                raise ValueError(
                    "Variable.domain must be a list, got {0}".format(
                        type(self.domain).__name__
                    )
                )
            if len(self.domain) == 0:
                raise ValueError(
                    "Variable.domain must be non-empty when sort='Enum'"
                )
            for i, member in enumerate(self.domain):
                if not isinstance(member, str):
                    raise ValueError(
                        "Variable.domain[{0}] must be a str, got {1}".format(
                            i, type(member).__name__
                        )
                    )
                if member.strip() == "":
                    raise ValueError(
                        "Variable.domain[{0}] must be a non-empty string".format(i)
                    )
            if len(set(self.domain)) != len(self.domain):
                raise ValueError(
                    "Variable.domain must not contain duplicate members"
                )
        else:
            if self.domain is not None:
                raise ValueError(
                    "Variable.domain must be None when sort={0!r}".format(self.sort)
                )


# ---------------------------------------------------------------------------
# Atom -- flat, no nesting.
# ---------------------------------------------------------------------------


@dataclass
class Atom:
    """A single normalized IR atom: ``var <op> value``.

    This is the normalized INTERNAL atom form. A later phase maps raw LLM
    JSON into these; this schema is the normalized dataclass only.

    var is the referenced variable name; non-empty. (Cross-referencing the
      variable table is NOT done here -- that is _solve's build step.)
    op must be one of COMPARISON_OPS.
    value holds an int, float, bool, or str -- the three D6 atom kinds are
      represented in this one normalized class:
        - numeric comparison: Atom(var, op, <int|float>), any of the 6 ops.
        - Bool: Atom(var, "=", True) / Atom(var, "=", False).
        - Enum: Atom(var, "=", "shipped") / Atom(var, "!=", "pending").
      The op-vs-sort restriction (e.g. Bool only takes "="; Enum only takes
      "="/"!=") is NOT enforced here -- it is enforced at _solve build time,
      where the referenced variable's sort is known.
    """

    var: str
    op: str
    value: object

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.var, "Atom.var")
        _require_in_enum(self.op, COMPARISON_OPS, "Atom.op")

        if not isinstance(self.value, (int, float, bool, str)):
            raise ValueError(
                "Atom.value must be one of int, float, bool, or str, "
                "got {0}".format(type(self.value).__name__)
            )


# ---------------------------------------------------------------------------
# Constraint.
# ---------------------------------------------------------------------------


@dataclass
class Constraint:
    """A single IR constraint -- either a bare assertion or an implication.

    ac_id is the source acceptance-criterion identifier (e.g. "AC-3");
      non-empty.
    kind must be one of CONSTRAINT_KINDS ("assertion", "implication").
    consequent is a non-empty list of Atom.
    antecedent: for kind="assertion" it MUST be None or an empty list; for
      kind="implication" it MUST be a non-empty list of Atom.
    """

    ac_id: str
    kind: str
    consequent: List[Atom]
    antecedent: Optional[List[Atom]] = None

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.ac_id, "Constraint.ac_id")
        _require_in_enum(self.kind, CONSTRAINT_KINDS, "Constraint.kind")

        if not isinstance(self.consequent, list):
            raise ValueError(
                "Constraint.consequent must be a list, got {0}".format(
                    type(self.consequent).__name__
                )
            )
        if len(self.consequent) == 0:
            raise ValueError("Constraint.consequent must be non-empty")
        for i, item in enumerate(self.consequent):
            if not isinstance(item, Atom):
                raise ValueError(
                    "Constraint.consequent[{0}] must be an Atom, got {1}".format(
                        i, type(item).__name__
                    )
                )

        if self.kind == "assertion":
            if self.antecedent is not None and len(self.antecedent) > 0:
                raise ValueError(
                    "Constraint.antecedent must be None or empty when "
                    "kind='assertion'"
                )
        else:
            # kind == "implication"
            if self.antecedent is None:
                raise ValueError(
                    "Constraint.antecedent is required when kind='implication'"
                )
            if not isinstance(self.antecedent, list):
                raise ValueError(
                    "Constraint.antecedent must be a list, got {0}".format(
                        type(self.antecedent).__name__
                    )
                )
            if len(self.antecedent) == 0:
                raise ValueError(
                    "Constraint.antecedent must be non-empty when "
                    "kind='implication'"
                )
            for i, item in enumerate(self.antecedent):
                if not isinstance(item, Atom):
                    raise ValueError(
                        "Constraint.antecedent[{0}] must be an Atom, got "
                        "{1}".format(i, type(item).__name__)
                    )


# ---------------------------------------------------------------------------
# Coverage -- the honesty ledger.
# ---------------------------------------------------------------------------


@dataclass
class Coverage:
    """A per-AC coverage ledger entry.

    ac_id is the source acceptance-criterion identifier; non-empty.
    status must be one of COVERAGE_STATUSES ("formalized", "skipped_prose",
      "skipped_unsupported").
    reason: required (non-empty str) when status starts with "skipped_"; for
      status="formalized" reason may be None (if provided, must be a str).
    """

    ac_id: str
    status: str
    reason: Optional[str] = None

    def __post_init__(self):
        # type: () -> None
        _require_nonempty(self.ac_id, "Coverage.ac_id")
        _require_in_enum(self.status, COVERAGE_STATUSES, "Coverage.status")

        if self.status.startswith("skipped_"):
            _require_nonempty(self.reason, "Coverage.reason")
        else:
            # status == "formalized": reason may be None; if provided, must
            # be a str (not required to be non-empty).
            if self.reason is not None and not isinstance(self.reason, str):
                raise ValueError(
                    "Coverage.reason must be a string, got {0}".format(
                        type(self.reason).__name__
                    )
                )


# ---------------------------------------------------------------------------
# SpecCheckIR -- top-level container.
# ---------------------------------------------------------------------------


@dataclass
class SpecCheckIR:
    """The top-level IR container passed to the solver.

    variables is a list of Variable.
    constraints is a list of Constraint.
    coverage is a list of Coverage.

    Validation here is Phase-1 structural only -- element-type checks. NO
    cross-record validation (atoms-reference-declared-vars,
    coverage-covers-every-AC) is performed here; that is a later phase's
    consumer responsibility. Each list may be empty individually -- including
    the "nothing formalizable" case: all-skipped coverage with zero
    constraints is valid (the solver returns sat for it).
    """

    variables: List[Variable]
    constraints: List[Constraint]
    coverage: List[Coverage]

    def __post_init__(self):
        # type: () -> None
        if not isinstance(self.variables, list):
            raise ValueError(
                "SpecCheckIR.variables must be a list, got {0}".format(
                    type(self.variables).__name__
                )
            )
        for i, item in enumerate(self.variables):
            if not isinstance(item, Variable):
                raise ValueError(
                    "SpecCheckIR.variables[{0}] must be a Variable, got "
                    "{1}".format(i, type(item).__name__)
                )

        if not isinstance(self.constraints, list):
            raise ValueError(
                "SpecCheckIR.constraints must be a list, got {0}".format(
                    type(self.constraints).__name__
                )
            )
        for i, item in enumerate(self.constraints):
            if not isinstance(item, Constraint):
                raise ValueError(
                    "SpecCheckIR.constraints[{0}] must be a Constraint, got "
                    "{1}".format(i, type(item).__name__)
                )

        if not isinstance(self.coverage, list):
            raise ValueError(
                "SpecCheckIR.coverage must be a list, got {0}".format(
                    type(self.coverage).__name__
                )
            )
        for i, item in enumerate(self.coverage):
            if not isinstance(item, Coverage):
                raise ValueError(
                    "SpecCheckIR.coverage[{0}] must be a Coverage, got "
                    "{1}".format(i, type(item).__name__)
                )
