"""argparse parser + dispatch + main entry for spec_check_helper.

build_parser composes the top-level + subparsers.
_register_subcommands attaches each cmd_* handler via set_defaults(func=...).
main parses argv + dispatches (prints help + returns 2 when no subcommand).

Phase 6 ships all 7 verbs of the /spec-check scratch chain -- the orchestrator
captures each verb's stdout to a file and passes it to the next verb via a
--*-file argument, since a subprocess helper cannot call MCP/Task directly:

  preflight               -- gate on setup-chain artefacts + spec + z3
  resolve-scope           -- extract ACs from the feature's spec.md
  render-formalize-brief  -- assemble the spec-formalizer dispatch brief
  consume-ir              -- parse + validate the LLM's raw IR JSON
  solve                   -- run the Z3 solver over a canonical IR
  quorum-core             -- analyze k solve-result passes for D13
                              cross-run reproducibility (confirmed_unsat /
                              unstable / consistent)
  render-report           -- render + write specs/<feature>/spec-check.md
  write-seed              -- build + write spec-check-seed.json (REVISE-SPEC
                              backward re-entry arm)

Exit-code convention (matches the sibling _grill/_audit/_review CLIs):
  0  -- success
  1  -- unexpected top-level error (caught in main())
  2  -- gate failure / bad or missing input
  3  -- consume-ir only: IR parsed but failed cross-record validation
       (distinct from 2 so main.md can tell "malformed IR" -- re-prompt with
       a syntax fix -- from "IR inconsistent with the ACs" -- re-prompt with
       the validation errors -- since the stderr content differs)

Stdlib only. Targets Python 3.8+. No from __future__ import annotations.
"""

import argparse
import dataclasses
import datetime
import json
import os
import sys

# ---------------------------------------------------------------------------
# _spec_check / _shared import resolution
#
# _spec_check is this file's own package; _shared is a sibling package under
# src/devforge/lib/. The sys.path insert below makes both importable when
# _cli.py is invoked directly or imported by spec_check_helper.py (the
# Python shim). In-repo tests add _LIB_DIR explicitly in their own
# path-setup block.
# ---------------------------------------------------------------------------

_LIB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

from _spec_check._consume import (  # noqa: E402
    IRParseError,
    IRValidationError,
    extract_acs,
    parse_ir,
    validate_ir,
)
from _spec_check._preflight import Z3_INSTALL_MESSAGE, preflight  # noqa: E402


# ---------------------------------------------------------------------------
# Serde helpers -- the scratch-chain wire format.
# ---------------------------------------------------------------------------


def _ir_to_dict(ir):
    # type: (object) -> dict
    """Serialize a SpecCheckIR to a plain nested dict (dataclasses.asdict)."""
    return dataclasses.asdict(ir)


def _ir_from_dict(data):
    # type: (dict) -> object
    """Reconstruct a SpecCheckIR from a plain dict.

    Reuses parse_ir -- verified (test_ir_round_trip) that
    parse_ir(dataclasses.asdict(ir)) round-trips byte-for-byte through
    dataclasses.asdict's flat {var,op,value} Atom shape and parse_ir's
    generic atom branch.
    """
    return parse_ir(data)


def _solve_result_to_dict(result):
    # type: (object) -> dict
    """Serialize a SolveResult to {"status": ..., "unsat_core": [...]}."""
    return {"status": result.status, "unsat_core": result.unsat_core}


def _solve_result_from_dict(data):
    # type: (dict) -> object
    """Reconstruct a SolveResult from a plain dict.

    Deferred import: _spec_check._solve imports the third-party z3 package
    at module level. By the time render-report / write-seed consume a
    --solve-file, /spec-check's own preflight has already gated on
    z3_available earlier in the pipeline (solve() itself must have run to
    produce that file) -- so z3 is expected to be importable here too.
    """
    from _spec_check._solve import SolveResult  # noqa: E402

    return SolveResult(status=data["status"], unsat_core=data["unsat_core"])


# ---------------------------------------------------------------------------
# JSON-file loading helpers (shared read-and-report-error boilerplate).
# ---------------------------------------------------------------------------


def _read_json_file(path, arg_label):
    # type: (str, str) -> tuple
    """Read + json.load(path). Returns (data, None) or (None, error_str)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh), None
    except OSError as exc:
        return None, "cannot read {0} file: {1}".format(arg_label, exc)
    except json.JSONDecodeError as exc:
        return None, "{0} file is not valid JSON: {1}".format(arg_label, exc)


def _stability_from_data(data):
    # type: (object) -> object
    """Pull a render_report-shaped stability dict out of --stability-file.

    Accepts either the full analyze_quorum() dict (with a nested
    "stability": {"reproduced_in", "of"} and a top-level "verdict") or an
    already-flat {"reproduced_in", "of", "verdict"} dict. Returns
    {"reproduced_in", "of", "verdict"} on success, or None when data is
    not a dict or is missing any of the three required fields (caller
    reports the error).
    """
    if not isinstance(data, dict):
        return None

    nested = data.get("stability")
    source = nested if isinstance(nested, dict) else data

    reproduced_in = source.get("reproduced_in")
    of = source.get("of")
    verdict = data.get("verdict", source.get("verdict"))

    if reproduced_in is None or of is None or verdict is None:
        return None

    return {"reproduced_in": reproduced_in, "of": of, "verdict": verdict}


def _extract_acs_list(data):
    # type: (object) -> object
    """Pull the acs list out of a resolve-scope-shaped payload.

    Accepts either the resolve-scope stdout object ({"acs": [...], "count":
    N}) or a bare JSON array of AC dicts. Returns None when neither shape
    matches, the resolved value is not a list, or any element is not a
    dict (caller reports the error in all cases) -- a bare array of
    non-dict elements (e.g. ["AC-1", "AC-2"]) is a valid top-level JSON
    array but not a valid AC list, and must not reach a downstream .get()
    call.
    """
    if isinstance(data, dict) and "acs" in data:
        acs = data["acs"]
    elif isinstance(data, list):
        acs = data
    else:
        return None

    if not isinstance(acs, list):
        return None
    for item in acs:
        if not isinstance(item, dict):
            return None
    return acs


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_preflight(args):
    # type: (argparse.Namespace) -> int
    """Gate on z3 availability + setup-chain artefacts + feature spec.md.

    Always emits the full preflight JSON to stdout before any non-zero exit.

    Gate order (first failure wins):
      1. z3_available False       -> Z3_INSTALL_MESSAGE on stderr
      2. setup_chain_ok False     -> missing setup-chain artefacts on stderr
      3. constitution_populated False -> unpopulated-sentinel message
      4. feature_dir given and feature_gate_ok False -> missing spec.md

    Returns 0 on success, 2 on any gate failure.
    """
    workspace_root = getattr(args, "workspace_root", ".") or "."
    feature_dir = getattr(args, "feature_dir", None) or None

    result = preflight(workspace_root=workspace_root, feature_dir=feature_dir)

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")

    if not result["z3_available"]:
        sys.stderr.write(
            "spec_check_helper preflight: {0}\n".format(Z3_INSTALL_MESSAGE)
        )
        return 2

    if not result["setup_chain_ok"]:
        missing = result.get("missing_artefacts", [])
        sys.stderr.write(
            "spec_check_helper preflight: setup chain incomplete. "
            "Run the 4-command setup sequence first:\n"
            "  /init-forge -> /generate-docs -> /configure -> /constitute\n"
            "Missing: {0}\n".format(", ".join(missing))
        )
        return 2

    if not result["constitution_populated"]:
        sys.stderr.write(
            "spec_check_helper preflight: constitution.md contains an "
            "unpopulated sentinel. Run /constitute to populate it before "
            "running /spec-check.\n"
        )
        return 2

    if feature_dir is not None and not result["feature_gate_ok"]:
        missing_feat = result.get("missing_feature_artefacts", [])
        sys.stderr.write(
            "spec_check_helper preflight: feature artefacts missing in "
            "{0!r}: {1}\n"
            "Run /specify to produce these before running /spec-check.\n".format(
                feature_dir, ", ".join(missing_feat)
            )
        )
        return 2

    return 0


def cmd_resolve_scope(args):
    # type: (argparse.Namespace) -> int
    """Extract acceptance criteria from the feature's spec.md.

    --spec-file, when given, takes precedence over --feature-dir (an
    explicit file path is a more specific instruction than a directory
    convention). At least one of the two is required.

    Returns 0 on success (prints {"acs": [...], "count": N} to stdout).
    Returns 2 when neither arg is given, the spec file does not exist, or
    it yields zero acceptance criteria.
    """
    feature_dir = getattr(args, "feature_dir", None) or None
    spec_file = getattr(args, "spec_file", None) or None

    if spec_file:
        spec_path = spec_file
    elif feature_dir:
        spec_path = os.path.join(feature_dir, "spec.md")
    else:
        sys.stderr.write(
            "spec_check_helper resolve-scope: --feature-dir or --spec-file "
            "required\n"
        )
        return 2

    if not os.path.isfile(spec_path):
        sys.stderr.write(
            "spec_check_helper resolve-scope: spec file not found: "
            "{0}\n".format(spec_path)
        )
        return 2

    acs = extract_acs(spec_path)

    if not acs:
        sys.stderr.write(
            "spec_check_helper resolve-scope: no acceptance criteria found "
            "in {0}\n".format(spec_path)
        )
        return 2

    result = {"acs": acs, "count": len(acs)}
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_render_formalize_brief(args):
    # type: (argparse.Namespace) -> int
    """Render the spec-formalizer dispatch brief from a resolve-scope file.

    Returns 0 on success (prints the brief text -- NOT JSON -- to stdout).
    Returns 2 on missing/unreadable/malformed --acs-file.
    """
    from _spec_check._brief import render_formalize_brief

    acs_file = getattr(args, "acs_file", None)
    if not acs_file:
        sys.stderr.write(
            "spec_check_helper render-formalize-brief: --acs-file <path> "
            "required\n"
        )
        return 2

    data, err = _read_json_file(acs_file, "--acs-file")
    if err:
        sys.stderr.write(
            "spec_check_helper render-formalize-brief: {0}\n".format(err)
        )
        return 2

    acs = _extract_acs_list(data)
    if acs is None:
        sys.stderr.write(
            "spec_check_helper render-formalize-brief: --acs-file must be "
            "a resolve-scope JSON object (with an 'acs' key) or a bare JSON "
            "array of AC dicts\n"
        )
        return 2

    brief = render_formalize_brief(acs)
    sys.stdout.write(brief)
    if not brief.endswith("\n"):
        sys.stdout.write("\n")
    return 0


def cmd_consume_ir(args):
    # type: (argparse.Namespace) -> int
    """Parse + cross-validate the LLM's raw IR JSON.

    Returns 0 on success (prints the canonical IR as JSON to stdout).
    Returns 2 when --ir-file / --acs-file are missing or unreadable, or the
      IR is shape-malformed (IRParseError) -- re-prompt the formalizer with
      a syntax fix.
    Returns 3 when the IR parses fine but fails cross-record validation
      against the ACs -- re-prompt the formalizer with the validation
      errors (a distinct exit code so main.md can tell the two failure
      modes apart; the stderr content differs).
    """
    ir_file = getattr(args, "ir_file", None)
    acs_file = getattr(args, "acs_file", None)

    if not ir_file:
        sys.stderr.write(
            "spec_check_helper consume-ir: --ir-file <path> required\n"
        )
        return 2
    if not acs_file:
        sys.stderr.write(
            "spec_check_helper consume-ir: --acs-file <path> required\n"
        )
        return 2

    raw, err = _read_json_file(ir_file, "--ir-file")
    if err:
        sys.stderr.write("spec_check_helper consume-ir: {0}\n".format(err))
        return 2

    acs_data, err = _read_json_file(acs_file, "--acs-file")
    if err:
        sys.stderr.write("spec_check_helper consume-ir: {0}\n".format(err))
        return 2

    acs = _extract_acs_list(acs_data)
    if acs is None:
        sys.stderr.write(
            "spec_check_helper consume-ir: --acs-file must be a "
            "resolve-scope JSON object (with an 'acs' key) or a bare JSON "
            "array of AC dicts\n"
        )
        return 2

    try:
        ir = parse_ir(raw)
    except IRParseError as exc:
        sys.stderr.write(
            "spec_check_helper consume-ir: {0}\n".format(exc)
        )
        return 2

    ac_ids = [a.get("id", "") for a in acs]
    errors = validate_ir(ir, ac_ids)
    if errors:
        sys.stderr.write("spec_check_helper consume-ir: IR validation failed:\n")
        for line in errors:
            sys.stderr.write("  - {0}\n".format(line))
        return 3

    sys.stdout.write(json.dumps(_ir_to_dict(ir), indent=2, sort_keys=True) + "\n")
    return 0


def cmd_solve(args):
    # type: (argparse.Namespace) -> int
    """Run the Z3 solver over a canonical IR (from consume-ir's output).

    Returns 0 on success (prints {"status": ..., "unsat_core": [...]} to
      stdout).
    Returns 2 on missing/unreadable/malformed --ir-file, when z3 is not
      importable, or when solve()'s build-time defense-in-depth backstop
      rejects the IR (a ValueError on a cross-record problem the schema
      defers to solve-time -- undeclared var, wrong op/value for a var's
      sort -- e.g. a hand-edited / stale canonical IR that bypassed
      consume-ir's validate_ir).
    """
    ir_file = getattr(args, "ir_file", None)
    if not ir_file:
        sys.stderr.write("spec_check_helper solve: --ir-file <path> required\n")
        return 2

    data, err = _read_json_file(ir_file, "--ir-file")
    if err:
        sys.stderr.write("spec_check_helper solve: {0}\n".format(err))
        return 2

    try:
        ir = _ir_from_dict(data)
    except IRParseError as exc:
        sys.stderr.write("spec_check_helper solve: {0}\n".format(exc))
        return 2

    try:
        from _spec_check._solve import solve as _solve
    except ImportError:
        sys.stderr.write(
            "spec_check_helper solve: {0}\n".format(Z3_INSTALL_MESSAGE)
        )
        return 2

    try:
        result = _solve(ir)
    except ValueError as exc:
        sys.stderr.write("spec_check_helper solve: {0}\n".format(exc))
        return 2

    sys.stdout.write(
        json.dumps(_solve_result_to_dict(result), indent=2, sort_keys=True) + "\n"
    )
    return 0


def cmd_quorum_core(args):
    # type: (argparse.Namespace) -> int
    """Analyze k solve-result passes for D13 cross-run reproducibility.

    --passes-file is a JSON array of k solve-result objects (each the
    stdout shape of the solve verb: {"status", "unsat_core"}) -- the
    orchestrator captures each pass's `solve` stdout and assembles them
    into this array. --k is the DECLARED pass count; it defaults to
    len(passes) when omitted. When --k is explicitly given and does not
    match the actual number of passes found in --passes-file (e.g. a
    dropped pass), this is a NON-FATAL condition: a warning is emitted
    on stderr and the run continues (exit 0) -- analyze_quorum never
    crashes on the mismatch, but the discrepancy must not be silently
    absorbed, since D13's whole value is a trustworthy count.

    Returns 0 on success (prints the full analyze_quorum() dict as JSON
      to stdout; a --k/actual-count mismatch is a stderr warning, not a
      failure).
    Returns 2 when --passes-file is missing/unreadable/not-valid-JSON, or
      decodes to something other than a non-empty JSON array.
    """
    from _spec_check._quorum import analyze_quorum

    passes_file = getattr(args, "passes_file", None)
    if not passes_file:
        sys.stderr.write(
            "spec_check_helper quorum-core: --passes-file <path> required\n"
        )
        return 2

    data, err = _read_json_file(passes_file, "--passes-file")
    if err:
        sys.stderr.write("spec_check_helper quorum-core: {0}\n".format(err))
        return 2

    if not isinstance(data, list) or not data:
        sys.stderr.write(
            "spec_check_helper quorum-core: --passes-file must decode to "
            "a non-empty JSON array of solve-result objects\n"
        )
        return 2

    k_raw = getattr(args, "k", None)
    k = k_raw if k_raw is not None else len(data)

    if k_raw is not None and k_raw != len(data):
        sys.stderr.write(
            "spec_check_helper quorum-core: warning: declared --k {0} but "
            "got {1} passes in --passes-file; using {1} for the quorum "
            "math\n".format(k_raw, len(data))
        )

    try:
        quorum = analyze_quorum(data, k)
    except ValueError as exc:
        sys.stderr.write("spec_check_helper quorum-core: {0}\n".format(exc))
        return 2

    sys.stdout.write(json.dumps(quorum, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_render_report(args):
    # type: (argparse.Namespace) -> int
    """Render + write specs/<feature>/spec-check.md from the solved IR.

    Returns 0 on success (prints {"report_path", "recommended_disposition",
      "unsat_core", "status"} as JSON to stdout).
    Returns 2 on missing/unreadable/malformed input files, including a
      --solve-file that does not reconstruct into a valid SolveResult (e.g.
      a self-contradictory {"status": "sat", "unsat_core": [...]} that
      SolveResult.__post_init__ rejects).
    """
    from _spec_check._report import (
        recommend_disposition,
        render_report,
        write_spec_check_report,
    )

    ir_file = getattr(args, "ir_file", None)
    solve_file = getattr(args, "solve_file", None)
    acs_file = getattr(args, "acs_file", None)
    feature = getattr(args, "feature", None) or "."
    feature_dir = getattr(args, "feature_dir", None)
    stability_file = getattr(args, "stability_file", None)

    if not ir_file:
        sys.stderr.write(
            "spec_check_helper render-report: --ir-file <path> required\n"
        )
        return 2
    if not solve_file:
        sys.stderr.write(
            "spec_check_helper render-report: --solve-file <path> required\n"
        )
        return 2
    if not acs_file:
        sys.stderr.write(
            "spec_check_helper render-report: --acs-file <path> required\n"
        )
        return 2
    if not feature_dir:
        sys.stderr.write(
            "spec_check_helper render-report: --feature-dir <dir> required\n"
        )
        return 2

    ir_data, err = _read_json_file(ir_file, "--ir-file")
    if err:
        sys.stderr.write("spec_check_helper render-report: {0}\n".format(err))
        return 2

    solve_data, err = _read_json_file(solve_file, "--solve-file")
    if err:
        sys.stderr.write("spec_check_helper render-report: {0}\n".format(err))
        return 2

    acs_data, err = _read_json_file(acs_file, "--acs-file")
    if err:
        sys.stderr.write("spec_check_helper render-report: {0}\n".format(err))
        return 2

    acs = _extract_acs_list(acs_data)
    if acs is None:
        sys.stderr.write(
            "spec_check_helper render-report: --acs-file must be a "
            "resolve-scope JSON object (with an 'acs' key) or a bare JSON "
            "array of AC dicts\n"
        )
        return 2

    stability = None
    if stability_file:
        stability_data, err = _read_json_file(stability_file, "--stability-file")
        if err:
            sys.stderr.write("spec_check_helper render-report: {0}\n".format(err))
            return 2
        stability = _stability_from_data(stability_data)
        if stability is None:
            sys.stderr.write(
                "spec_check_helper render-report: --stability-file must be "
                "a quorum dict (from quorum-core) or a "
                "{\"reproduced_in\", \"of\", \"verdict\"} stability "
                "object\n"
            )
            return 2

    try:
        ir = _ir_from_dict(ir_data)
    except IRParseError as exc:
        sys.stderr.write("spec_check_helper render-report: {0}\n".format(exc))
        return 2

    try:
        solve_result = _solve_result_from_dict(solve_data)
    except (KeyError, TypeError, ValueError) as exc:
        sys.stderr.write(
            "spec_check_helper render-report: --solve-file is not a valid "
            "SolveResult: {0}\n".format(exc)
        )
        return 2

    rec = recommend_disposition(solve_result)
    date_str = datetime.date.today().isoformat()

    try:
        content = render_report(
            feature, date_str, solve_result, ir, acs, rec, stability=stability
        )
    except ValueError as exc:
        sys.stderr.write("spec_check_helper render-report: {0}\n".format(exc))
        return 2

    try:
        report_path = write_spec_check_report(feature_dir, content)
    except OSError as exc:
        sys.stderr.write(
            "spec_check_helper render-report: cannot write spec-check.md: "
            "{0}\n".format(exc)
        )
        return 2

    ack = {
        "report_path": report_path,
        "recommended_disposition": rec,
        "unsat_core": solve_result.unsat_core,
        "status": solve_result.status,
    }
    sys.stdout.write(json.dumps(ack, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_write_seed(args):
    # type: (argparse.Namespace) -> int
    """Build + write spec-check-seed.json (REVISE-SPEC re-entry arm).

    source/target_stage are fixed internally by build_seed ("spec-check" /
    "spec") -- /spec-check has exactly one backward direction, unlike
    /grill's multi-target write-seed.

    Returns 0 on success (prints {"seed_path": ...} as JSON to stdout).
    Returns 2 on missing/invalid required fields.
    """
    from _spec_check._seed import build_seed, write_seed

    feature = getattr(args, "feature", None) or ""
    feature_dir = getattr(args, "feature_dir", None)
    prior_conclusion = getattr(args, "prior_conclusion", None) or ""
    invalidating_evidence = getattr(args, "invalidating_evidence", None) or ""
    must_satisfy = getattr(args, "must_satisfy", None) or ""
    provenance = getattr(args, "provenance", None) or ""
    cycle_count_raw = getattr(args, "cycle_count", None)
    if cycle_count_raw is None:
        cycle_count_raw = "1"
    carried_raw = getattr(args, "carried_findings", None)
    if carried_raw is None:
        carried_raw = "[]"

    if not feature_dir:
        sys.stderr.write(
            "spec_check_helper write-seed: --feature-dir <dir> required\n"
        )
        return 2
    if not prior_conclusion:
        sys.stderr.write(
            "spec_check_helper write-seed: --prior-conclusion required\n"
        )
        return 2
    if not invalidating_evidence:
        sys.stderr.write(
            "spec_check_helper write-seed: --invalidating-evidence required\n"
        )
        return 2
    if not must_satisfy:
        sys.stderr.write(
            "spec_check_helper write-seed: --must-satisfy required\n"
        )
        return 2
    if not provenance:
        sys.stderr.write(
            "spec_check_helper write-seed: --provenance required\n"
        )
        return 2

    try:
        cycle_count = int(cycle_count_raw)
    except (ValueError, TypeError):
        sys.stderr.write(
            "spec_check_helper write-seed: --cycle-count must be an "
            "integer, got {0!r}\n".format(cycle_count_raw)
        )
        return 2

    try:
        carried_findings = json.loads(carried_raw)
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "spec_check_helper write-seed: --carried-findings must be a "
            "JSON array string: {0}\n".format(exc)
        )
        return 2
    if not isinstance(carried_findings, list):
        sys.stderr.write(
            "spec_check_helper write-seed: --carried-findings must decode "
            "to a JSON array, got {0}\n".format(type(carried_findings).__name__)
        )
        return 2

    try:
        seed = build_seed(
            feature=feature,
            prior_conclusion=prior_conclusion,
            invalidating_evidence=invalidating_evidence,
            must_satisfy=must_satisfy,
            provenance=provenance,
            cycle_count=cycle_count,
            carried_findings=carried_findings,
        )
    except ValueError as exc:
        sys.stderr.write("spec_check_helper write-seed: {0}\n".format(exc))
        return 2

    try:
        seed_path = write_seed(feature_dir, seed)
    except OSError as exc:
        sys.stderr.write(
            "spec_check_helper write-seed: cannot write "
            "spec-check-seed.json: {0}\n".format(exc)
        )
        return 2

    sys.stdout.write(json.dumps({"seed_path": seed_path}, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Registry + parser construction
# ---------------------------------------------------------------------------

# _SUBCOMMAND_REGISTRY is the extension point for new verbs.
# Each entry is a (verb_name, help_text, handler_function) triple.
# To add a future verb:
#   1. Write the cmd_<verb> function above.
#   2. Append (kebab-name, help, cmd_func) to this list.
#   3. Add the argument block for the verb in the elif chain in
#      _register_subcommands below.
_SUBCOMMAND_REGISTRY = [
    (
        "preflight",
        "Gate on z3 availability + setup-chain artefacts + feature spec.md.",
        cmd_preflight,
    ),
    (
        "resolve-scope",
        "Extract acceptance criteria from the feature's spec.md.",
        cmd_resolve_scope,
    ),
    (
        "render-formalize-brief",
        "Assemble the spec-formalizer dispatch brief from a resolve-scope file.",
        cmd_render_formalize_brief,
    ),
    (
        "consume-ir",
        "Parse + cross-validate the LLM's raw IR JSON against the ACs.",
        cmd_consume_ir,
    ),
    (
        "solve",
        "Run the Z3 solver over a canonical IR and emit sat/unsat + core.",
        cmd_solve,
    ),
    (
        "quorum-core",
        "Analyze k solve-result passes for D13 cross-run reproducibility.",
        cmd_quorum_core,
    ),
    (
        "render-report",
        "Render + write specs/<feature>/spec-check.md from the solved IR.",
        cmd_render_report,
    ),
    (
        "write-seed",
        "Build + write spec-check-seed.json (REVISE-SPEC backward re-entry arm).",
        cmd_write_seed,
    ),
]


def build_parser():
    # type: () -> argparse.ArgumentParser
    """Build and return the top-level ArgumentParser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="spec_check_helper",
        description=(
            "Helper for /spec-check -- proves a feature's acceptance "
            "criteria are mutually consistent via a deterministic Z3 SMT "
            "solve over an LLM-formalized IR. Runs between /specify and "
            "/plan; on a proven contradiction (REVISE-SPEC) emits a "
            "backward spec-check-seed.json re-entry seed."
        ),
    )

    subparsers = parser.add_subparsers(dest="subcommand")
    _register_subcommands(subparsers)
    return parser


def _register_subcommands(subparsers):
    # type: (object) -> None
    """Attach all handlers from _SUBCOMMAND_REGISTRY."""
    for verb, help_text, handler in _SUBCOMMAND_REGISTRY:
        sp = subparsers.add_parser(verb, help=help_text)

        if verb == "preflight":
            sp.add_argument(
                "--workspace-root",
                default=".",
                dest="workspace_root",
                metavar="DIR",
                help=(
                    "Workspace root to check for setup-chain artefacts "
                    "(constitution.md / CLAUDE.md / .devforge/). "
                    "Default: CWD."
                ),
            )
            sp.add_argument(
                "--feature-dir",
                default=None,
                dest="feature_dir",
                metavar="DIR",
                help=(
                    "Feature directory to check for spec.md "
                    "(e.g. specs/001-auth/). "
                    "When omitted, the feature gate is skipped."
                ),
            )

        elif verb == "resolve-scope":
            sp.add_argument(
                "--feature-dir",
                default=None,
                dest="feature_dir",
                metavar="DIR",
                help=(
                    "Feature directory; spec.md is read from "
                    "<feature-dir>/spec.md. Ignored when --spec-file is "
                    "given."
                ),
            )
            sp.add_argument(
                "--spec-file",
                default=None,
                dest="spec_file",
                metavar="PATH",
                help=(
                    "Explicit path to a spec.md file. Takes precedence "
                    "over --feature-dir."
                ),
            )

        elif verb == "render-formalize-brief":
            sp.add_argument(
                "--acs-file",
                required=True,
                dest="acs_file",
                metavar="PATH",
                help=(
                    "Path to the JSON file produced by resolve-scope's "
                    "stdout ({\"acs\": [...], \"count\": N})."
                ),
            )

        elif verb == "consume-ir":
            sp.add_argument(
                "--ir-file",
                required=True,
                dest="ir_file",
                metavar="PATH",
                help=(
                    "Path to the raw LLM IR JSON captured from the "
                    "spec-formalizer Task's response."
                ),
            )
            sp.add_argument(
                "--acs-file",
                required=True,
                dest="acs_file",
                metavar="PATH",
                help=(
                    "Path to the JSON file produced by resolve-scope's "
                    "stdout ({\"acs\": [...], \"count\": N})."
                ),
            )

        elif verb == "solve":
            sp.add_argument(
                "--ir-file",
                required=True,
                dest="ir_file",
                metavar="PATH",
                help=(
                    "Path to the canonical IR JSON produced by consume-ir's "
                    "stdout."
                ),
            )

        elif verb == "quorum-core":
            sp.add_argument(
                "--passes-file",
                required=True,
                dest="passes_file",
                metavar="PATH",
                help=(
                    "Path to a JSON array of k solve-result objects (each "
                    "the stdout shape of the solve verb)."
                ),
            )
            sp.add_argument(
                "--k",
                type=int,
                default=None,
                metavar="N",
                help=(
                    "Declared pass count. Default: the length of "
                    "--passes-file's array."
                ),
            )

        elif verb == "render-report":
            sp.add_argument(
                "--ir-file",
                required=True,
                dest="ir_file",
                metavar="PATH",
                help="Path to the canonical IR JSON (from consume-ir).",
            )
            sp.add_argument(
                "--solve-file",
                required=True,
                dest="solve_file",
                metavar="PATH",
                help="Path to the SolveResult JSON (from solve).",
            )
            sp.add_argument(
                "--acs-file",
                required=True,
                dest="acs_file",
                metavar="PATH",
                help=(
                    "Path to the JSON file produced by resolve-scope's "
                    "stdout ({\"acs\": [...], \"count\": N})."
                ),
            )
            sp.add_argument(
                "--feature",
                default=".",
                metavar="STR",
                help=(
                    "Feature identity label printed in the report header "
                    "(e.g. specs/001-widget). Default: '.'."
                ),
            )
            sp.add_argument(
                "--feature-dir",
                required=True,
                dest="feature_dir",
                metavar="DIR",
                help=(
                    "Feature directory path (e.g. specs/001-auth/). "
                    "spec-check.md is written here."
                ),
            )
            sp.add_argument(
                "--stability-file",
                default=None,
                dest="stability_file",
                metavar="PATH",
                help=(
                    "Optional path to a JSON file carrying a D13 quorum "
                    "dict (from quorum-core) or its "
                    "{\"reproduced_in\", \"of\", \"verdict\"} stability "
                    "sub-object. When given, renders a formalization "
                    "stability line in the report. Default: omitted -- "
                    "renders exactly as before quorum support existed."
                ),
            )

        elif verb == "write-seed":
            sp.add_argument(
                "--feature",
                default="",
                metavar="STR",
                help="Feature slug / id (non-empty; passed to build_seed).",
            )
            sp.add_argument(
                "--feature-dir",
                required=True,
                dest="feature_dir",
                metavar="DIR",
                help=(
                    "Feature directory path (e.g. specs/001-auth/). "
                    "spec-check-seed.json is written here."
                ),
            )
            sp.add_argument(
                "--prior-conclusion",
                required=True,
                dest="prior_conclusion",
                metavar="TEXT",
                help="The spec's now-invalidated claim (the conflicting AC set).",
            )
            sp.add_argument(
                "--invalidating-evidence",
                required=True,
                dest="invalidating_evidence",
                metavar="TEXT",
                help=(
                    "The proven contradiction (unsat-core ac_ids plus the "
                    "logic reading that derives it)."
                ),
            )
            sp.add_argument(
                "--must-satisfy",
                required=True,
                dest="must_satisfy",
                metavar="TEXT",
                help="What the revised spec must resolve.",
            )
            sp.add_argument(
                "--provenance",
                required=True,
                metavar="PATH",
                help="Pointer to specs/<feature>/spec-check.md.",
            )
            sp.add_argument(
                "--cycle-count",
                default="1",
                dest="cycle_count",
                metavar="N",
                help=(
                    "Bounded-compounding-loop counter (int >= 1). "
                    "Default: 1."
                ),
            )
            sp.add_argument(
                "--carried-findings",
                default="[]",
                dest="carried_findings",
                metavar="JSON_ARRAY",
                help=(
                    "JSON array string of prior finding descriptions "
                    "carried forward. Default: '[]'."
                ),
            )

        sp.set_defaults(func=handler)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv=None):
    # type: (object) -> int
    """Parse argv and dispatch to the selected subcommand handler.

    Returns the handler's exit code (0 = success, non-zero = error).
    When no subcommand is given, prints help and returns 2.

    Unlike the sibling _grill/_audit/_review CLIs, this one adds an
    explicit top-level try/except around the handler call, reporting any
    unexpected exception cleanly on stderr with exit code 1 instead of a
    raw traceback. Exit-code parity with the siblings holds regardless --
    an uncaught exception also terminates the process with status 1 -- this
    guard only changes what lands on stderr, not the exit code contract.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help(sys.stderr)
        return 2

    try:
        return args.func(args)
    except Exception as exc:  # noqa: BLE001 -- top-level safety net
        sys.stderr.write(
            "spec_check_helper: unexpected error: {0}: {1}\n".format(
                type(exc).__name__, exc
            )
        )
        return 1
