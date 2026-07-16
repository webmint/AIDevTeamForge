"""_consume.py -- AC extraction + LLM-IR ingestion for the /spec-check command.

Note: this module shares its bare filename with the unrelated
``_shared/_consume.py`` (the audit/review findings-tmp parser) -- do not
confuse the two; they are independent modules in different subpackages with
no shared code.

Three responsibilities:

1. ``extract_acs(source)`` -- the command's stable AC-extraction entry point.
   Thin delegation to ``_shared.spec_acs.parse_acs``; the command imports
   this from ``_spec_check._consume``, not by reaching into ``_shared`` directly,
   so the /spec-check surface has one AC-extraction seam.

2. ``parse_ir(raw)`` -- parses the LLM's raw IR JSON (a ``dict`` or a JSON
   ``str``) into the Phase-1 dataclasses (``_spec_check.ir_schema``). Every
   IR-shape failure -- bad JSON, a missing top-level key, a malformed
   element, a dataclass ``__post_init__`` rejection -- surfaces as a single
   exception type, ``IRParseError``, carrying a locator (e.g.
   ``"variables[1]: missing key 'sort'"`` or
   ``"constraints[2] (AC-3): Constraint.antecedent is required when
   kind='implication'"``) so the command can point the LLM at exactly what
   to fix and re-prompt.

3. ``validate_ir(ir, ac_ids)`` / ``validate_ir_or_raise(ir, ac_ids)`` --
   cross-record validation the dataclasses deliberately do NOT perform
   (see ``ir_schema.py``'s module docstring): undeclared variable
   references, atom value/sort mismatches, AC coverage completeness, and
   status/constraint agreement. These are logical-consistency problems, not
   shape problems -- an IR that fails ``validate_ir`` parsed FINE; it is
   surfaced to a human via ``IRValidationError``, not re-prompted
   automatically. ``validate_ir`` collects every problem before returning
   (never fail-fast) so a human sees the whole picture in one pass.

Two atom input shapes are accepted by ``parse_ir`` (mirroring the IR's own
Bool/numeric/Enum representation, see ``ir_schema.Atom``):

  - generic: ``{"var": str, "op": <one of the 6 comparison ops>,
    "value": <int|float|bool|str>}``
  - Bool short-form: ``{"var": str, "negated": <bool>}`` -- normalizes to
    ``Atom(var, "=", not negated)``. Supplying both ``negated`` and
    (``op`` or ``value``) on the same atom is ambiguous and rejected.

Atom-vs-variable sort consistency is checked here (in ``validate_ir``), not
in ``_solve.py``'s build step -- catching it earlier gives the human an
AC-scoped error message before any Z3 translation is attempted.
``_solve.py``'s own build-time checks remain as a backstop (defense in
depth, not the primary catch).

Does NOT import ``_solve`` -- solving is a separate phase's responsibility.
No formalize-brief rendering, no report rendering, no z3 call, no
preflight/CLI wiring here.

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional

from _shared.spec_acs import parse_acs
from _spec_check.ir_schema import Atom, Constraint, Coverage, SpecCheckIR, Variable

# ---------------------------------------------------------------------------
# Exceptions.
# ---------------------------------------------------------------------------


class IRParseError(ValueError):
    """The LLM's IR JSON is malformed or shape-invalid.

    Raised by ``parse_ir`` on anything that prevents building a well-formed
    ``SpecCheckIR`` -- bad JSON, a missing/mistyped top-level key, a
    malformed element, or a dataclass ``__post_init__`` rejection. The
    command re-prompts the LLM on this exception.
    """


class IRValidationError(ValueError):
    """The IR parsed fine but is logically inconsistent with the ACs.

    Raised by ``validate_ir_or_raise`` when ``validate_ir`` returns one or
    more errors. Surfaced to a human, not auto-re-prompted -- a logically
    inconsistent IR may reflect a genuinely inconsistent spec, not merely a
    translation mistake.
    """


# ---------------------------------------------------------------------------
# extract_acs.
# ---------------------------------------------------------------------------


def extract_acs(source):
    # type: (str) -> List[Dict]
    """The /spec-check command's stable AC-extraction entry point.

    Thin delegation to ``_shared.spec_acs.parse_acs`` -- see that module for
    the full behaviour contract. Returns its dicts unchanged.
    """
    return parse_acs(source)


# ---------------------------------------------------------------------------
# parse_ir -- element parsers.
# ---------------------------------------------------------------------------


def _require_list_key(data, key):
    # type: (Dict, str) -> list
    if key not in data:
        raise IRParseError("missing top-level key '{0}'".format(key))
    value = data[key]
    if not isinstance(value, list):
        raise IRParseError(
            "'{0}' must be a list, got {1}".format(key, type(value).__name__)
        )
    return value


def _parse_variable(d, i):
    # type: (object, int) -> Variable
    locator = "variables[{0}]".format(i)
    if not isinstance(d, dict):
        raise IRParseError(
            "{0}: expected an object, got {1}".format(locator, type(d).__name__)
        )
    for key in ("name", "sort", "gloss"):
        if key not in d:
            raise IRParseError("{0}: missing key '{1}'".format(locator, key))
    try:
        return Variable(
            name=d["name"], sort=d["sort"], gloss=d["gloss"], domain=d.get("domain")
        )
    except ValueError as exc:
        raise IRParseError("{0}: {1}".format(locator, exc))


def _parse_atom(d, locator):
    # type: (object, str) -> Atom
    if not isinstance(d, dict):
        raise IRParseError(
            "{0}: expected an object, got {1}".format(locator, type(d).__name__)
        )
    if "var" not in d:
        raise IRParseError("{0}: missing key 'var'".format(locator))
    var = d["var"]

    has_negated = "negated" in d
    has_op_or_value = ("op" in d) or ("value" in d)

    if has_negated and has_op_or_value:
        raise IRParseError(
            "{0}: ambiguous atom -- has both 'negated' and 'op'/'value'".format(
                locator
            )
        )

    if has_negated:
        negated = d["negated"]
        if not isinstance(negated, bool):
            raise IRParseError(
                "{0}: 'negated' must be a bool, got {1}".format(
                    locator, type(negated).__name__
                )
            )
        try:
            return Atom(var=var, op="=", value=(not negated))
        except ValueError as exc:
            raise IRParseError("{0}: {1}".format(locator, exc))

    # Generic shape: {"var", "op", "value"}.
    if "op" not in d:
        raise IRParseError("{0}: missing key 'op'".format(locator))
    if "value" not in d:
        raise IRParseError("{0}: missing key 'value'".format(locator))
    try:
        return Atom(var=var, op=d["op"], value=d["value"])
    except ValueError as exc:
        raise IRParseError("{0}: {1}".format(locator, exc))


def _parse_atom_list(raw, locator):
    # type: (object, str) -> List[Atom]
    if not isinstance(raw, list):
        raise IRParseError(
            "{0}: must be a list, got {1}".format(locator, type(raw).__name__)
        )
    return [
        _parse_atom(item, "{0}[{1}]".format(locator, j))
        for j, item in enumerate(raw)
    ]


def _parse_constraint(d, i):
    # type: (object, int) -> Constraint
    locator = "constraints[{0}]".format(i)
    if not isinstance(d, dict):
        raise IRParseError(
            "{0}: expected an object, got {1}".format(locator, type(d).__name__)
        )
    for key in ("ac_id", "kind", "consequent"):
        if key not in d:
            raise IRParseError("{0}: missing key '{1}'".format(locator, key))

    ac_id = d["ac_id"]
    kind = d["kind"]

    # Compute the AC-labeled locator prefix up front (guarded via d.get, so
    # a constraint dict with a missing/mistyped 'ac_id' still yields a
    # usable locator rather than crashing while building it) -- atom-list
    # errors below carry the AC label too, since a malformed atom is the
    # LLM's likeliest failure mode and the label is what lets a human/
    # re-prompt point at exactly what to fix.
    _ac_id_for_label = d.get("ac_id")
    labeled_locator = (
        "{0} ({1})".format(locator, _ac_id_for_label)
        if isinstance(_ac_id_for_label, str)
        else locator
    )

    consequent = _parse_atom_list(
        d["consequent"], "{0}.consequent".format(labeled_locator)
    )

    antecedent = None  # type: Optional[List[Atom]]
    if d.get("antecedent") is not None:
        antecedent = _parse_atom_list(
            d["antecedent"], "{0}.antecedent".format(labeled_locator)
        )

    try:
        return Constraint(
            ac_id=ac_id, kind=kind, consequent=consequent, antecedent=antecedent
        )
    except ValueError as exc:
        raise IRParseError("{0}: {1}".format(labeled_locator, exc))


def _parse_coverage(d, i):
    # type: (object, int) -> Coverage
    locator = "coverage[{0}]".format(i)
    if not isinstance(d, dict):
        raise IRParseError(
            "{0}: expected an object, got {1}".format(locator, type(d).__name__)
        )
    for key in ("ac_id", "status"):
        if key not in d:
            raise IRParseError("{0}: missing key '{1}'".format(locator, key))
    try:
        return Coverage(ac_id=d["ac_id"], status=d["status"], reason=d.get("reason"))
    except ValueError as exc:
        raise IRParseError("{0}: {1}".format(locator, exc))


# ---------------------------------------------------------------------------
# parse_ir.
# ---------------------------------------------------------------------------


def parse_ir(raw):
    # type: (object) -> SpecCheckIR
    """Parse the LLM's raw IR (a dict or a JSON str) into a SpecCheckIR.

    Raises IRParseError (with a locator prefix) on any shape problem: bad
    JSON, a missing/mistyped top-level key, a malformed element, or a
    dataclass __post_init__ rejection.
    """
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise IRParseError("invalid JSON: {0}".format(exc))
    elif isinstance(raw, dict):
        data = raw
    else:
        raise IRParseError(
            "raw must be a dict or a JSON string, got {0}".format(
                type(raw).__name__
            )
        )

    if not isinstance(data, dict):
        raise IRParseError(
            "parsed JSON root must be an object, got {0}".format(
                type(data).__name__
            )
        )

    variables_raw = _require_list_key(data, "variables")
    constraints_raw = _require_list_key(data, "constraints")
    coverage_raw = _require_list_key(data, "coverage")

    variables = [_parse_variable(d, i) for i, d in enumerate(variables_raw)]
    constraints = [_parse_constraint(d, i) for i, d in enumerate(constraints_raw)]
    coverage = [_parse_coverage(d, i) for i, d in enumerate(coverage_raw)]

    try:
        return SpecCheckIR(
            variables=variables, constraints=constraints, coverage=coverage
        )
    except ValueError as exc:
        # Defense-in-depth backstop -- element parsers above already build
        # each item as the correct dataclass type, so SpecCheckIR's own
        # __post_init__ element-type checks should never fire in practice.
        raise IRParseError(str(exc))


# ---------------------------------------------------------------------------
# validate_ir -- cross-record checks.
# ---------------------------------------------------------------------------

_SKIPPED_STATUSES = ("skipped_prose", "skipped_unsupported")


def _check_atom_sort(atom, var):
    # type: (Atom, Variable) -> Optional[str]
    """Check one atom's op/value against its variable's declared sort.

    Returns an error string (without the ac_id prefix) or None when
    consistent.
    """
    if var.sort == "Int":
        if isinstance(atom.value, bool) or not isinstance(atom.value, int):
            return "Int variable '{0}' given non-int value {1!r}".format(
                var.name, atom.value
            )
        return None

    if var.sort == "Real":
        if isinstance(atom.value, bool) or not isinstance(
            atom.value, (int, float)
        ):
            return "Real variable '{0}' given non-numeric value {1!r}".format(
                var.name, atom.value
            )
        return None

    if var.sort == "Bool":
        if atom.op != "=" or not isinstance(atom.value, bool):
            return (
                "Bool variable '{0}' given invalid op/value "
                "(op={1!r}, value={2!r})".format(var.name, atom.op, atom.value)
            )
        return None

    # var.sort == "Enum"
    if atom.op not in ("=", "!="):
        return "Enum variable '{0}' given invalid op {1!r}".format(
            var.name, atom.op
        )
    domain = var.domain or []
    if not isinstance(atom.value, str) or atom.value not in domain:
        return (
            "Enum variable '{0}' value {1!r} not in domain {2!r}".format(
                var.name, atom.value, domain
            )
        )
    return None


def validate_ir(ir, ac_ids):
    # type: (SpecCheckIR, List[str]) -> List[str]
    """Cross-record validation the schema does not do.

    Collects ALL problems (never fail-fast) and returns them as a sorted,
    deduplicated list of human-readable strings. An empty list means the IR
    is valid.
    """
    errors = []  # type: List[str]
    ac_id_set = set(ac_ids)

    # --- 1. Duplicate variable names; build the lookup table. ---
    seen_var_names = set()  # type: set
    duplicate_var_names = set()  # type: set
    var_table = {}  # type: Dict[str, Variable]
    for var in ir.variables:
        if var.name in seen_var_names:
            duplicate_var_names.add(var.name)
        else:
            seen_var_names.add(var.name)
            var_table[var.name] = var
    for name in duplicate_var_names:
        errors.append("duplicate variable name '{0}'".format(name))

    # --- 2 + 3 + constraint-ac_id check: walk every constraint's atoms. ---
    for constraint in ir.constraints:
        if constraint.ac_id not in ac_id_set:
            errors.append(
                "constraint references unknown AC '{0}'".format(constraint.ac_id)
            )

        atoms = list(constraint.consequent) + list(constraint.antecedent or [])
        for atom in atoms:
            if atom.var not in var_table:
                errors.append(
                    "{0}: atom references undeclared variable '{1}'".format(
                        constraint.ac_id, atom.var
                    )
                )
                continue
            if atom.var in duplicate_var_names:
                # The duplicate-name error above already flags this row; a
                # sort opinion resolved against the arbitrary first-seen
                # declaration would be noise (the atom may have been meant
                # for a different, later declaration of the same name).
                continue
            sort_err = _check_atom_sort(atom, var_table[atom.var])
            if sort_err is not None:
                errors.append("{0}: {1}".format(constraint.ac_id, sort_err))

    # --- 4. Coverage completeness. ---
    seen_coverage_ac_ids = set()  # type: set
    duplicate_coverage_ac_ids = set()  # type: set
    coverage_status = {}  # type: Dict[str, str]
    for cov in ir.coverage:
        if cov.ac_id not in ac_id_set:
            errors.append(
                "coverage references unknown AC '{0}'".format(cov.ac_id)
            )

        if cov.ac_id in seen_coverage_ac_ids:
            duplicate_coverage_ac_ids.add(cov.ac_id)
        else:
            seen_coverage_ac_ids.add(cov.ac_id)
            coverage_status[cov.ac_id] = cov.status

    for dup in duplicate_coverage_ac_ids:
        errors.append("duplicate coverage entry for AC '{0}'".format(dup))

    for ac_id in ac_id_set:
        if ac_id not in seen_coverage_ac_ids:
            errors.append("AC coverage missing for {0}".format(ac_id))

    # --- 5. Status/constraint agreement. ---
    constraint_count_by_ac = {}  # type: Dict[str, int]
    for constraint in ir.constraints:
        constraint_count_by_ac[constraint.ac_id] = (
            constraint_count_by_ac.get(constraint.ac_id, 0) + 1
        )

    for ac_id, status in coverage_status.items():
        count = constraint_count_by_ac.get(ac_id, 0)
        if status == "formalized" and count == 0:
            errors.append(
                "{0} marked formalized but has no constraint".format(ac_id)
            )
        elif status in _SKIPPED_STATUSES and count > 0:
            errors.append(
                "{0} marked {1} but has {2} constraint(s)".format(
                    ac_id, status, count
                )
            )

    return sorted(set(errors))


def validate_ir_or_raise(ir, ac_ids):
    # type: (SpecCheckIR, List[str]) -> None
    """Raise IRValidationError when validate_ir(ir, ac_ids) finds problems."""
    errors = validate_ir(ir, ac_ids)
    if errors:
        raise IRValidationError("\n".join(errors))
