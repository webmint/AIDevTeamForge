"""_solve -- deterministic Z3 solver core for the /spec-check IR.

Provides ``SolveResult`` and ``solve(ir)``: translates a ``SpecCheckIR``
(``ir_schema.py``, this same subpackage) into Z3 constraints, checks
satisfiability, and -- on unsat -- extracts a minimal conflicting subset of
acceptance-criteria ids (``unsat_core``) via Z3's tracking-literal mechanism.

Design notes:

- No LLM, no I/O, no report rendering. Pure translation + solve. Those
  responsibilities live in a later phase.

- Atom-vs-variable cross-checking (does ``atom.var`` exist in the variable
  table; does the atom's op/value shape match the variable's sort) is
  enforced HERE, at build time -- not in ``ir_schema.py`` -- because the
  variable table is only known once the full IR is assembled. This is the
  one deliberate exception to "ir_schema owns all validation" (see its
  module docstring).

- Reachability semantics (ratified plan decision D9, low-false-positive
  reading): plain Z3 ``Implies`` semantics. Antecedents of an
  ``implication`` constraint are NOT auto-asserted as reachable. A
  permission/role clash surfaces only when some AC actually *asserts* the
  conflicting scenario (an ``assertion`` constraint) alongside the
  implication -- this keeps v1 free of spurious unsat from mutually
  exclusive triggers. Any "assumed reachable, surfaced to a human" honesty
  framing is a later report-layer concern, not solver logic; no
  reachability injection is implemented here.

- Each ``Constraint`` gets its own Z3 tracking literal named
  ``track!{ac_id}!{i}`` (index ``i`` is the constraint's position in
  ``ir.constraints``), registered via ``solver.assert_and_track``. Multiple
  constraints may share an ``ac_id``; each still gets a distinct literal.
  "!" is used as the delimiter; ``ir_schema.py`` places no character
  restriction on ``ac_id``, so an ``ac_id`` containing "!" (e.g. "AC!3") is
  valid IR -- the parse is robust to that regardless, because
  ``_ac_id_from_tracking_literal_name`` splits on the *rightmost* "!" via
  ``str.rpartition("!")``, which always isolates the trailing numeric index
  no matter how many "!" characters appear earlier in the ac_id.

- Every ``solve()`` call builds its own fresh ``z3.Context()`` and threads it
  explicitly through every leaf-level z3 constructor that accepts a ``ctx=``
  parameter (``Int``, ``Real``, ``Bool``, ``EnumSort``, ``Solver``, and the
  tracking ``Bool`` literals). This was discovered empirically, not assumed:
  ``z3.EnumSort`` registers its sort name in z3's *global default context*
  when no ``ctx=`` is given, so two ``solve()`` calls in the same process
  that both declare an Enum variable with the same name (e.g. "order_state"
  used across two independent /spec-check runs, or simply across two
  unittest cases) raise
  ``Z3Exception: b'enumeration sort name is already declared'`` on the
  second call. A per-call ``Context()`` isolates each solve so repeated
  invocations never collide. ``z3.Const(name, sort)`` (used for Enum
  constants) has NO ``ctx=`` parameter at all -- passing one raises
  ``TypeError`` -- so it is isolated indirectly: it derives its context from
  the already-``ctx``-bound ``enum_sort`` passed in as its second argument.
  Likewise, derived formulas (``z3.Not``, ``z3.And``, ``z3.Implies``) take no
  explicit ``ctx=`` -- they infer it from their z3-typed arguments, which
  already carry the call's context.

Stdlib + z3-solver third-party dependency (this module only; ``ir_schema.py``
stays stdlib-only per house convention).
"""

import operator
from dataclasses import dataclass
from typing import Dict, List

import z3

from _spec_check.ir_schema import Atom, Constraint, SpecCheckIR, Variable

# ---------------------------------------------------------------------------
# Solver-status enum + delimiter constant.
# ---------------------------------------------------------------------------

SOLVE_STATUSES = ("sat", "unsat", "unknown")

_TRACK_PREFIX = "track!"

_NUMERIC_OPS = {
    "<": operator.lt,
    "<=": operator.le,
    "=": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
}

# ---------------------------------------------------------------------------
# SolveResult.
# ---------------------------------------------------------------------------


@dataclass
class SolveResult:
    """Result of a solve() call.

    status is one of SOLVE_STATUSES ("sat", "unsat", "unknown").
    unsat_core is a deduped, sorted list of ac_ids in the minimal conflicting
      set; empty unless status == "unsat".

    This is solve()'s public output contract (a later phase imports it), so
    it is validated exhaustively -- same discipline as ir_schema.py -- not
    just at the status field.
    """

    status: str
    unsat_core: List[str]

    def __post_init__(self):
        # type: () -> None
        if self.status not in SOLVE_STATUSES:
            raise ValueError(
                "SolveResult.status must be one of {0}, got {1!r}".format(
                    list(SOLVE_STATUSES), self.status
                )
            )

        if not isinstance(self.unsat_core, list):
            raise ValueError(
                "SolveResult.unsat_core must be a list, got {0}".format(
                    type(self.unsat_core).__name__
                )
            )
        for i, item in enumerate(self.unsat_core):
            if not isinstance(item, str):
                raise ValueError(
                    "SolveResult.unsat_core[{0}] must be a str, got {1}".format(
                        i, type(item).__name__
                    )
                )

        if self.status != "unsat" and self.unsat_core:
            raise ValueError(
                "SolveResult.unsat_core must be empty when status is not "
                "'unsat', got status={0!r} unsat_core={1!r}".format(
                    self.status, self.unsat_core
                )
            )

        if self.unsat_core != sorted(set(self.unsat_core)):
            raise ValueError(
                "SolveResult.unsat_core must be sorted and deduplicated, "
                "got {0!r}".format(self.unsat_core)
            )


# ---------------------------------------------------------------------------
# Variable-table construction.
# ---------------------------------------------------------------------------


def _build_var_table(variables, ctx=None):
    # type: (List[Variable], object) -> Dict[str, tuple]
    """Build name -> (sort, z3_const, enum_member_map) for every variable.

    enum_member_map is None for non-Enum sorts; for Enum it maps each domain
    member string to its z3 EnumSort member constant.

    ctx is the caller's per-solve() z3.Context() -- every leaf constructor
    must be pinned to it (see the module docstring for why). When omitted
    (ctx=None), a fresh Context() is created for this call, which is enough
    isolation for a single standalone call (e.g. a unit test exercising this
    function directly) but NOT what solve() uses -- solve() must pass its own
    ctx explicitly so the same context is shared with its Solver and
    tracking literals.
    """
    if ctx is None:
        ctx = z3.Context()
    table = {}
    for var in variables:
        if var.sort == "Int":
            const = z3.Int(var.name, ctx=ctx)
            table[var.name] = (var.sort, const, None)
        elif var.sort == "Real":
            const = z3.Real(var.name, ctx=ctx)
            table[var.name] = (var.sort, const, None)
        elif var.sort == "Bool":
            const = z3.Bool(var.name, ctx=ctx)
            table[var.name] = (var.sort, const, None)
        else:
            # var.sort == "Enum" (ir_schema guarantees domain is a
            # non-empty list of non-empty, non-duplicate str for this sort).
            enum_sort, members = z3.EnumSort(var.name, list(var.domain), ctx=ctx)
            const = z3.Const(var.name, enum_sort)
            member_map = dict(zip(var.domain, members))
            table[var.name] = (var.sort, const, member_map)
    return table


# ---------------------------------------------------------------------------
# Atom -> z3 formula.
# ---------------------------------------------------------------------------


def _atom_to_formula(atom, var_table, ac_id):
    # type: (Atom, Dict[str, tuple], str) -> object
    """Translate one Atom to a z3 BoolRef, given the built variable table.

    Raises ValueError (naming the offending ac_id/var) on any atom-vs-var
    mismatch: undeclared var, wrong op for the var's sort, or a value that
    does not match the var's sort.
    """
    if atom.var not in var_table:
        raise ValueError(
            "{0}: Atom references undeclared variable {1!r}".format(
                ac_id, atom.var
            )
        )

    sort, const, member_map = var_table[atom.var]

    if sort in ("Int", "Real"):
        if isinstance(atom.value, bool) or not isinstance(atom.value, (int, float)):
            raise ValueError(
                "{0}: Atom on {1!r} ({2} var) must have an int/float value, "
                "got {3}".format(ac_id, atom.var, sort, type(atom.value).__name__)
            )
        if sort == "Int" and isinstance(atom.value, float):
            raise ValueError(
                "{0}: Atom on {1!r} (Int var) must have an int value, "
                "got float".format(ac_id, atom.var)
            )
        op_fn = _NUMERIC_OPS[atom.op]
        return op_fn(const, atom.value)

    if sort == "Bool":
        if atom.op != "=":
            raise ValueError(
                "{0}: Atom on {1!r} (Bool var) only supports op='=', "
                "got {2!r}".format(ac_id, atom.var, atom.op)
            )
        if not isinstance(atom.value, bool):
            raise ValueError(
                "{0}: Atom on {1!r} (Bool var) must have a bool value, "
                "got {2}".format(ac_id, atom.var, type(atom.value).__name__)
            )
        return const if atom.value else z3.Not(const)

    # sort == "Enum"
    if atom.op not in ("=", "!="):
        raise ValueError(
            "{0}: Atom on {1!r} (Enum var) only supports op='=' or '!=', "
            "got {2!r}".format(ac_id, atom.var, atom.op)
        )
    if not isinstance(atom.value, str) or atom.value not in member_map:
        raise ValueError(
            "{0}: Atom on {1!r} (Enum var) value {2!r} is not in its "
            "declared domain".format(ac_id, atom.var, atom.value)
        )
    member_const = member_map[atom.value]
    if atom.op == "=":
        return const == member_const
    return const != member_const


# ---------------------------------------------------------------------------
# Constraint -> z3 formula.
# ---------------------------------------------------------------------------


def _atoms_to_formulas(atoms, var_table, ac_id):
    # type: (List[Atom], Dict[str, tuple], str) -> list
    return [_atom_to_formula(atom, var_table, ac_id) for atom in atoms]


def _constraint_to_formula(constraint, var_table):
    # type: (Constraint, Dict[str, tuple]) -> object
    consequent_formulas = _atoms_to_formulas(
        constraint.consequent, var_table, constraint.ac_id
    )
    consequent = (
        consequent_formulas[0]
        if len(consequent_formulas) == 1
        else z3.And(*consequent_formulas)
    )

    if constraint.kind == "assertion":
        return consequent

    # kind == "implication"
    antecedent_formulas = _atoms_to_formulas(
        constraint.antecedent, var_table, constraint.ac_id
    )
    antecedent = (
        antecedent_formulas[0]
        if len(antecedent_formulas) == 1
        else z3.And(*antecedent_formulas)
    )
    return z3.Implies(antecedent, consequent)


# ---------------------------------------------------------------------------
# Tracking-literal helpers.
# ---------------------------------------------------------------------------


def _tracking_literal_name(ac_id, index):
    # type: (str, int) -> str
    return "{0}{1}!{2}".format(_TRACK_PREFIX, ac_id, index)


def _ac_id_from_tracking_literal_name(name):
    # type: (str) -> str
    """Parse an ac_id back out of a 'track!{ac_id}!{i}' literal name."""
    body = name[len(_TRACK_PREFIX):]
    ac_id, _, _index = body.rpartition("!")
    return ac_id


# ---------------------------------------------------------------------------
# solve().
# ---------------------------------------------------------------------------


def solve(ir):
    # type: (SpecCheckIR) -> SolveResult
    """Translate ir to Z3, check satisfiability, extract the unsat core."""
    # A fresh Context() per call keeps repeated solve() invocations isolated
    # -- see the module docstring for the empirically-discovered EnumSort
    # name collision this avoids.
    ctx = z3.Context()
    var_table = _build_var_table(ir.variables, ctx)

    solver = z3.Solver(ctx=ctx)
    tracking_name_to_ac_id = {}

    for i, constraint in enumerate(ir.constraints):
        formula = _constraint_to_formula(constraint, var_table)
        track_name = _tracking_literal_name(constraint.ac_id, i)
        tracking_literal = z3.Bool(track_name, ctx=ctx)
        solver.assert_and_track(formula, tracking_literal)
        tracking_name_to_ac_id[track_name] = constraint.ac_id

    result = solver.check()

    if result == z3.sat:
        return SolveResult(status="sat", unsat_core=[])

    if result == z3.unsat:
        core = solver.unsat_core()
        ac_ids = set()
        for lit in core:
            name = str(lit)
            ac_ids.add(tracking_name_to_ac_id.get(name, _ac_id_from_tracking_literal_name(name)))
        return SolveResult(status="unsat", unsat_core=sorted(ac_ids))

    # result == z3.unknown
    return SolveResult(status="unknown", unsat_core=[])
