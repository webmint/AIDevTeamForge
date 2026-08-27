"""_e2e.py — fail-soft e2e-suite run for /verify PHASE 4.5 (plan 90).

Public surface
--------------
  run_e2e_gate(workspace_root) -> dict

      Fail-soft: always returns a dict, never raises.  Exit code semantics
      are handled by the CLI verb (cmd_e2e_gate in _cli.py), which always
      returns 0 — every internal failure is a ``status``, never a crash
      (plan 90 fact 13's contract, mirrored from ``_regression.py``).

      Parameters
      ----------
      workspace_root : str
          Absolute path to the install root (where .devforge/ lives).
          Read the same way ``_regression.py`` reads it — wrapper-aware,
          via ``_implement._workspace.resolve_workspace``.

      Returns
      -------
      dict with keys:
        status      : str  — "off" | "inconclusive" | "e2e-clean" |
                              "e2e-failing"
        note        : str  — human-readable explanation (ALWAYS present)
        output_tail : str  — last 50 lines of combined stdout+stderr from
                              the e2e run (present ONLY on "e2e-failing")

Scope — what this module deliberately does NOT do (plan 90 D3/D6/D7)
----------------------------------------------------------------------
Runs the configured E2E_COMMAND **once, at HEAD, in the real
source_root** — never against an isolated historical checkout, never
twice.  Unlike ``_regression.py``'s baseline-diff pattern (an earlier
detached checkout compared against the current tree), there is no
second (earlier-commit) run here: an e2e suite that needs a running
application would fail for reasons unrelated to the feature inside a
bare isolated checkout (plan 90 ``## Origin``, the rejected alternative),
so this module reproduces only the HEAD-run half of that pattern and
none of the isolated-checkout / earlier-commit-comparison machinery.

The framework starts NO application (D6): E2E_COMMAND is invoked as a
single shell command in source_root: the suite owns its own process
lifecycle (browser launch, dev server, docker compose, etc.) and this
module starts nothing, waits on nothing beyond the command itself, and
tears down nothing.

Config key
----------
Reads E2E_COMMAND from .devforge/project-config.json.  ``_read_config``
distinguishes two failure classes (python-reviewer FIX 1, plan 90 Phase 4):

  - READ/PARSE FAILURE — the file is missing or unreadable, its content
    is not valid JSON, or the top-level JSON value isn't an object —
    surfaces as status "inconclusive", with the returned ``note`` naming
    the actual cause.  A MISSING project-config.json is deliberately
    grouped into this bucket rather than into "off", even though D8
    frames "off" as the default state of an unconfigured project.  Two
    reasons: (1) precedent — ``_regression.py``'s own fail-soft gate,
    when project-config.json is entirely absent, resolves through to
    "inconclusive" (its ``REGRESSION_GATE`` lookup defaults the MODE to
    "full" on a missing key, and the gate then goes inconclusive via its
    separate absent-``TEST_COMMANDS`` check) — "off" there requires an
    EXPLICIT ``"REGRESSION_GATE": "off"`` value, so this codebase already
    reserves "off" for an explicit or completed-configuration signal, not
    for an absent file.  (2) sequencing — E2E_COMMAND is read at
    ``/devforge:verify`` PHASE 4.5, downstream of the mandatory
    ``/devforge:configure`` step in the setup chain; by the time this
    gate runs on a real install, project-config.json necessarily exists.
    A totally missing file at this call site is therefore an install
    anomaly (configure skipped, or ``workspace_root`` misresolved), not
    the everyday "small project, no e2e infrastructure" case D8 targets —
    and D8's own silence (no note printed anywhere for "off") would hide
    exactly that anomaly instead of surfacing it.
  - SUCCESSFULLY PARSED, key absent or blank — status "off" (D8): the
    presence of a non-empty E2E_COMMAND string IS the on/off signal, so
    there is no separate REGRESSION_GATE-style mode key.

``_read_config`` is deliberately NOT imported from ``_regression.py``:
two independent config readers for two independent keys, so a change to
one gate's read path can never silently move the other's.

Timeout (OQ-5)
--------------
A SEPARATE module-level timeout constant, ``_E2E_TIMEOUT``, deliberately
NOT imported from ``_regression._TEST_TIMEOUT`` — the two tiers are
different tuning dials, and even prose-coupling this docstring's
reasoning to a sibling constant's value would rot silently the moment
that sibling is retuned, so the reasoning below stands on its own.
Defaulted to 1800s (30 minutes): a full e2e run typically launches a
browser or runtime, seeds fixtures or a database, and drives several
multi-step user flows end to end — each step paying real wall-clock
(process startup, network round-trips, UI settle time) that a unit
assertion never pays.  1800s gives a suite of that shape genuine
headroom without being unbounded.  A timeout produces "inconclusive",
NEVER "e2e-failing" — a suite that ran out of clock has not reported a
defect (OQ-5's explicit rule).

Missing-binary detection
-------------------------
The command runs via ``subprocess.run(..., shell=True)``, exactly as
``_regression._run_test_cmd`` does.  A shell that cannot find or execute
the named command exits 126 (found, not executable) or 127 (command not
found) by POSIX shell convention — neither of those codes means "the
e2e suite ran and reported failures", so both are treated as
"inconclusive" rather than "e2e-failing".  Every other non-zero exit
code is read as a genuine suite failure.

Accepted bound (documented, not an oversight — python-reviewer FIX 2):
this heuristic cannot distinguish "the shell couldn't find/execute the
command" from "the e2e suite's own process legitimately exited with
code 126 or 127" — for example a suite that shells out to a child
process and propagates that child's exit code verbatim.  Such a run is
misread as "inconclusive" and loses its ``output_tail``, exactly as a
genuinely missing binary would be — even though it may have printed
real, diagnostically useful output before exiting.  This is the same
shape as the OQ-5 timeout tradeoff immediately above (a suite that ran
out of clock is reported "inconclusive" rather than "e2e-failing", even
though it may in fact have been failing): a coarse, cheaply-computed
status is preferred over a more precise one that would require parsing
suite-specific output or re-implementing the shell's own command
resolution.  The false negative is ACCEPTED, not fixed — see
``test_126_127_heuristic_pins_accepted_false_negative`` in
``tests/lib/_verify/test_e2e.py``, which pins the misclassification so a
future reader finds the intent recorded, not silently regressed.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import Dict, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Number of tail lines to capture from a failing e2e run (kept small so the
# result JSON stays reasonably compact — same size as _regression.py's tail).
_TAIL_LINES = 50

# Max seconds for the e2e command.  See module docstring "Timeout (OQ-5)"
# for the standalone reasoning behind 1800s.
# Deliberately a SEPARATE constant — never import _regression._TEST_TIMEOUT.
_E2E_TIMEOUT = 1800

# project-config.json key for the e2e command (plan 90 D1 / OQ-7).
_CONFIG_E2E_COMMAND_KEY = "E2E_COMMAND"

# Shell exit codes meaning "the shell could not execute the command at
# all" (POSIX convention: 126 = found but not executable, 127 = command
# not found) — these mean "inconclusive", not "the suite ran and failed".
_NOT_EXECUTABLE_EXIT_CODES = frozenset([126, 127])


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _read_config(workspace_root):
    # type: (str) -> Tuple[Dict, Optional[str]]
    """Read .devforge/project-config.json from workspace_root.

    Returns (config, error):
      - Success (file exists, is valid JSON, top-level value is an
        object): (dict, None).
      - Failure (file missing/unreadable, invalid JSON, or a top-level
        value that isn't an object): ({}, "<cause naming what failed>").

    Never raises.  The caller (_run_e2e_gate_inner) uses `error` to
    distinguish "read/parse failed" (-> status "inconclusive") from
    "successfully parsed, key absent/blank" (-> status "off", D8) — see
    the module docstring's "Config key" section for the full reasoning,
    including the deliberate missing-file-is-inconclusive decision.
    Deliberately independent of _regression._read_config.
    """
    config_path = os.path.join(workspace_root, ".devforge", "project-config.json")
    try:
        with open(config_path, encoding="utf-8") as fh:
            raw = fh.read()
    except OSError as exc:
        return {}, "project-config.json missing or unreadable: {0}".format(exc)

    try:
        data = json.loads(raw)
    except ValueError as exc:
        return {}, "project-config.json is not valid JSON: {0}".format(exc)

    if not isinstance(data, dict):
        return {}, (
            "project-config.json did not parse to a JSON object "
            "(got {0})".format(type(data).__name__)
        )

    return data, None


def _get_e2e_command(config):
    # type: (Dict) -> Optional[str]
    """Return the configured e2e command, or None when unconfigured.

    None means "off" (D8), given a config dict that was ALREADY
    successfully parsed by _read_config (a read/parse failure never
    reaches this function — it short-circuits to "inconclusive" at the
    config_error check in _run_e2e_gate_inner, per FIX 1).  The three
    reachable causes: the E2E_COMMAND key is absent, its value is not a
    string, or it is empty/blank after stripping.
    """
    raw = config.get(_CONFIG_E2E_COMMAND_KEY)
    if not isinstance(raw, str):
        return None
    stripped = raw.strip()
    return stripped or None


# ---------------------------------------------------------------------------
# Output capture
# ---------------------------------------------------------------------------


def _tail_text(text, n=_TAIL_LINES):
    # type: (str, int) -> str
    """Return the last n lines of text (for output capture)."""
    lines = text.splitlines()
    if not lines:
        return ""
    return "\n".join(lines[-n:])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_e2e_gate(workspace_root):
    # type: (str) -> Dict
    """Run the e2e gate and return a result dict.

    ALWAYS returns a dict, never raises, and never signals failure via
    exit code — every internal error is caught and reported as
    status="inconclusive" (plan 90 fact 13's fail-soft contract).

    See module docstring for full parameter and return-value documentation.
    """
    try:
        return _run_e2e_gate_inner(workspace_root)
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "inconclusive",
            "note": "unexpected error in e2e gate: {0}".format(exc),
        }


def _run_e2e_gate_inner(workspace_root):
    # type: (str) -> Dict
    """Inner implementation; may propagate exceptions — caller wraps in try/except."""
    config, config_error = _read_config(workspace_root)

    # --- inconclusive: the config file itself could not be read or
    #     parsed — distinguished from "successfully parsed, key
    #     absent/blank" (off, below).  See module docstring "Config key"
    #     for the missing-file-vs-off decision and its reasoning. ---
    if config_error is not None:
        return {
            "status": "inconclusive",
            "note": config_error,
        }

    e2e_cmd = _get_e2e_command(config)

    # --- off: config read cleanly, but no E2E_COMMAND configured
    #     (D8 — silent, no gating) ---
    if not e2e_cmd:
        return {
            "status": "off",
            "note": "no E2E_COMMAND configured",
        }

    # --- Resolve workspace (source_root for the run) ---
    # Same resolve_workspace function _regression.py uses for wrapper-mode
    # support (source_root may differ from workspace_root).
    from _implement._workspace import resolve_workspace  # type: ignore[import]
    ws = resolve_workspace(workspace_root)
    source_root = str(ws.source_root)

    # --- Run once, at HEAD, in source_root (D3/D6 — no isolated checkout,
    #     no earlier-commit comparison, no second run, no app lifecycle
    #     management) ---
    try:
        proc = subprocess.run(
            e2e_cmd,
            cwd=source_root,
            shell=True,
            capture_output=True,
            text=True,
            check=False,
            timeout=_E2E_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "inconclusive",
            "note": "e2e command timed out after {0}s".format(_E2E_TIMEOUT),
        }
    except OSError as exc:
        return {
            "status": "inconclusive",
            "note": "subprocess error running e2e command: {0}".format(exc),
        }

    if proc.returncode in _NOT_EXECUTABLE_EXIT_CODES:
        return {
            "status": "inconclusive",
            "note": (
                "e2e command could not be executed (shell exit {0} — "
                "missing binary or not executable): {1!r}"
            ).format(proc.returncode, e2e_cmd),
        }

    if proc.returncode == 0:
        return {
            "status": "e2e-clean",
            "note": "e2e suite passed",
        }

    combined = proc.stdout + proc.stderr
    return {
        "status": "e2e-failing",
        "note": "e2e suite reported failures (exit code {0})".format(proc.returncode),
        "output_tail": _tail_text(combined),
    }
