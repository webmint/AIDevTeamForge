"""Pure preflight functions for spec_check_helper.

preflight — read and validate the 4-command setup chain artefacts and check
            that the target feature has a spec.md (required precondition for
            /spec-check, which runs AFTER /specify but BEFORE /plan). Unlike
            /grill (which gates on spec.md AND plan.md, since it runs between
            /plan and /breakdown), /spec-check deliberately does NOT require
            plan.md — requiring it would defeat the point: /spec-check exists
            to catch acceptance-criteria conflicts BEFORE planning starts.

check_z3 — probe for the z3-solver dependency /spec-check needs to
           actually run its satisfiability checks.

The functions return plain dicts / tuples; the CLI handler (a later phase)
decides whether to stop on a missing/unpopulated artefact or missing z3.

Sentinel set is intentionally identical to _grill/_preflight.py (and
_audit/_preflight.py, _review/_preflight.py) so every setup-chain preflight
enforces the same gate on the same markers. Duplicated here (not imported
from _grill) so /spec-check does not depend on another command's package —
the same per-command-package boundary _grill/_review/_audit already keep.
"""

import os
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants (identical to _grill/_preflight.py, _audit/_preflight.py, and
# _review/_preflight.py — must stay in sync with all three)
# ---------------------------------------------------------------------------

# Sentinels that indicate constitution.md has NOT been populated by /constitute.
_UNPOPULATED_SENTINELS = (
    "{{CONSTITUTION_BODY}}",
    "Run `/constitute`",
    # Pre-namespace stub literal (no slash) -- the form every existing
    # consumer install actually carries (src/constitution.md has always
    # shipped "_Run constitute to populate_", never the slash form below).
    "Run constitute to populate",
    # Pre-namespace guard literal (with slash) -- kept for back-compat with
    # any hand-edited constitution.md carrying this exact text.
    "Run /constitute to populate",
    # Post-namespace stub literal (plan 63 Phase 4c).
    "Run /devforge:constitute to populate",
)

# Setup-chain artefacts that must exist for /spec-check to run.
# Parallel to /audit, /review, and /grill preflights — same four-command chain.
_SETUP_CHAIN_ARTEFACTS = [
    # (relative_path, label) — label shown in missing_artefacts list
    ("constitution.md",                      "/devforge:constitute"),
    ("CLAUDE.md",                            "/devforge:init-forge"),
    (".devforge/project-config.json",        "/devforge:configure"),
    (".devforge/index.json",                 "/devforge:generate-docs"),
]

# ---------------------------------------------------------------------------
# check_z3 — z3-solver dependency probe.
# ---------------------------------------------------------------------------

Z3_INSTALL_MESSAGE = (
    "/devforge:spec-check requires the Z3 SMT solver. Install it once with:\n"
    "\n"
    "    pip install z3-solver\n"
    "\n"
    "(not installed by default -- /devforge:spec-check needs it, and "
    "/devforge:plan requires a fresh spec-check report before it will run.)"
)


def check_z3(importer=None):
    # type: (Optional[object]) -> Tuple[bool, str]
    """Probe whether the z3 SMT solver package is importable.

    Returns (available, message):
      available  True when `import z3` (or the injected importer) succeeds.
      message    Z3_INSTALL_MESSAGE when unavailable; "" when available.

    `importer` is an injectable stand-in for the real import, defaulting to
    None (real `import z3`). Pass a zero-arg callable that raises ImportError
    to force the absent path in a test without mutating sys.modules globally.
    """
    if importer is not None:
        try:
            importer()
        except ImportError:
            return False, Z3_INSTALL_MESSAGE
        return True, ""

    try:
        import z3  # noqa: F401
    except ImportError:
        return False, Z3_INSTALL_MESSAGE
    return True, ""


# ---------------------------------------------------------------------------
# preflight
# ---------------------------------------------------------------------------


def preflight(workspace_root=None, feature_dir=None, z3_importer=None):
    # type: (Optional[str], Optional[str], Optional[object]) -> Dict
    """Check setup-chain artefacts, constitution, feature spec, and z3.

    Never raises on a missing file — returns sane defaults.
    Returns a dict with keys always present:

      constitution_present      bool  — constitution.md exists
      constitution_populated    bool  — no unpopulated sentinel found
      setup_chain_ok            bool  — all 4 setup-chain artefacts present
      missing_artefacts         list  — labels of missing setup-chain artefacts
      spec_present               bool  — <feature_dir>/spec.md exists
      feature_gate_ok            bool  — spec.md exists (NO plan.md check —
                                          /spec-check runs before /plan)
      missing_feature_artefacts  list  — labels of missing feature artefacts
      z3_available                bool  — z3-solver package importable
      z3_message                  str   — install instructions when absent,
                                           "" when available

    workspace_root defaults to "." (CWD-relative) when None. /grill supplies
    the same "." default at its CLI layer (_grill/_cli.py) before calling
    preflight_context, which — unlike this function — takes workspace_root
    as a required argument with no internal default.
    feature_dir=None means "setup-chain-only mode" — spec_present and
    feature_gate_ok both stay False, matching /grill's convention.
    """
    if workspace_root is None:
        workspace_root = "."

    result = {
        "constitution_present": False,
        "constitution_populated": False,
        "setup_chain_ok": False,
        "missing_artefacts": [],
        "spec_present": False,
        "feature_gate_ok": False,
        "missing_feature_artefacts": [],
        "z3_available": False,
        "z3_message": "",
    }  # type: Dict

    # --- Check all setup-chain artefacts ---
    missing = []  # type: List[str]
    for rel_path, label in _SETUP_CHAIN_ARTEFACTS:
        full = os.path.join(workspace_root, rel_path)
        if not os.path.isfile(full):
            missing.append(label)
    result["missing_artefacts"] = missing
    result["setup_chain_ok"] = len(missing) == 0

    # --- constitution.md ---
    const_path = os.path.join(workspace_root, "constitution.md")
    try:
        with open(const_path, "r", encoding="utf-8") as fh:
            const_text = fh.read()
        result["constitution_present"] = True
        populated = True
        for sentinel in _UNPOPULATED_SENTINELS:
            if sentinel in const_text:
                populated = False
                break
        result["constitution_populated"] = populated
    except OSError:
        pass

    # --- Feature-level gate: spec.md only (NO plan.md) ---
    # /spec-check runs between /specify and /plan; requiring plan.md would
    # defeat the point (catching AC conflicts before planning starts).
    missing_feature = []  # type: List[str]
    if feature_dir is not None:
        spec_path = os.path.join(feature_dir, "spec.md")
        if os.path.isfile(spec_path):
            result["spec_present"] = True
        else:
            missing_feature.append("spec.md")
    result["missing_feature_artefacts"] = missing_feature
    result["feature_gate_ok"] = (
        feature_dir is not None and len(missing_feature) == 0
    )

    # --- z3-solver dependency ---
    z3_available, z3_message = check_z3(importer=z3_importer)
    result["z3_available"] = z3_available
    result["z3_message"] = z3_message

    return result
