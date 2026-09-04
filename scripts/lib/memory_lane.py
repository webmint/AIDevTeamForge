"""memory_lane.py — maintainer-side memory-lane coverage checker.

Problem this module addresses
------------------------------
``.devforge/memory.md`` is the framework's persistent cross-session lessons
file, and it has historically been write-mostly. Four distinct mechanisms
caused that (see ``74-MEMORY-LANE-INTEGRITY-PLAN.md`` for the full
write-up): a dead read path, a forcing function that certified a read of a
file that never existed, a truncated digest, and — the ONE this module
mechanizes — a coverage gap: nothing enumerated which commands SHOULD read
memory at all, and a helper preflight could build the field while NO
consuming surface ever read it back (the "orphaned payload" case).

Public API
----------
find_gaps(repo_root) -> dict
    Scan the live ``src/`` tree (plus ``scripts/emitters/claude.py``'s
    ``_PROMOTED`` tuple) rooted at ``repo_root`` (a path-like or str).
    Returns::

        {
            "no_disposition":            [str, ...],  # Rule 1a
            "empty_reason":               [str, ...],  # Rule 1b
            "reads_missing_helper_read":  [str, ...],  # Rule 2a
            "reads_missing_consumption":  [str, ...],  # Rule 2b
            "na_leaks_memory":            [str, ...],  # Rule 3
            "dead_path_literal":          [str, ...],  # Rule 4 ("path:line")
        }

    All six lists empty = all clear.

DISPOSITIONS
    ``{command: (disposition, reason)}`` — the maintainer's classification
    of every command in ``scripts/emitters/claude.py``'s ``_PROMOTED``
    tuple as either READS or N/A, with a recorded reason for each. See
    "A false inference to pre-empt" below before deriving anything from
    the 13/7 split.

SCOPE STATEMENT — honest non-coverage (mandatory, not optional polish)
------------------------------------------------------------------------
This checker verifies TWO things and nothing more, for READS commands:

  1. that a memory READ is PERFORMED (a call to one of
     ``_shared/memory.py``'s read primitives somewhere in that command's
     helper source), AND
  2. that a CONSUMING SURFACE (the command's ``main.md`` or a
     ``references/*.md`` file) explicitly NAMES the field it reads.

It does NOT verify:

  - that the consumption is SUBSTANTIVE — naming ``memory_excerpt`` in a
    sentence is enough to pass; whether that sentence actually changes
    what the command does is not checked and cannot be checked
    mechanically from text alone.
  - that the RIGHT memory entries were selected, or that memory.md's
    CONTENT is accurate.
  - (Rule 3) that an N/A command is truly memory-read-free — only that
    none of the two KNOWN tokens appear in its surfaces or helper
    package. A read performed through some other, unnamed mechanism
    would not be caught.

A green run from this checker is NOT a claim about memory quality, and NOT
a claim that every command that reads memory does anything useful with
what it read. It is a claim about two specific, narrow, mechanically
checkable properties: read-performed and read-named.

A false inference to pre-empt
------------------------------
The 21 ``_PROMOTED`` commands also split model-invocable /
human-typed-only (see ``63-SKILL-COLLISION-SUPPRESSION-PLAN.md``): 13/7
under plan 63, and 16/4 since plan 93 narrowed the human-typed set to the
four setup commands on 2026-09-03. Either way it is a DIFFERENT SET from
this module's 13 READS / 8 N/A split: ``summarize`` and ``report-bug``
are model-invocable yet N/A here (``spec-check`` joined them under plan
93), and ``grill`` and ``fix`` were human-typed-only yet READS here until
plan 93. The counts coincided
at 13/7 by arithmetic accident, never by a shared structural cause, and
no longer coincide at all — do not derive one split from the other.

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple

# ---------------------------------------------------------------------------
# Disposition constants
# ---------------------------------------------------------------------------

READS = "READS"
NOT_APPLICABLE = "N/A"

# {command: (disposition, reason)}. Every name in scripts/emitters/claude.py's
# `_PROMOTED` tuple MUST have exactly one entry here (Rule 1) — a command
# added to `_PROMOTED` with no entry fails immediately, which is the point:
# it forces a classification decision instead of leaving silent unclassified
# coverage. Reasons are the audit trail that makes an exclusion a DECISION,
# not an oversight.
DISPOSITIONS = {
    # ---- READS (13) --------------------------------------------------------
    "research": (
        READS,
        "Investigates a bug/enhancement against existing code — a memory "
        "entry can name a related file or a known pitfall that must steer "
        "Phase 1's scope questions and Phase 2's investigation before they "
        "commit to a scope; a lesson arriving later is too late to change "
        "what the run searches.",
    ),
    "discover": (
        READS,
        "Surveys a greenfield feature idea — the same rationale as "
        "research, applied to discovery's integration-points and "
        "functional-scope questions.",
    ),
    "specify": (
        READS,
        "Drafts spec.md — .devforge/memory.md is one of the four "
        "mandatory base reads specify's own finalize-handoff step records "
        "as read before the acceptance criteria are written, so known "
        "constraints can inform them.",
    ),
    "plan": (
        READS,
        "Produces the technical plan — architect-level design decisions "
        "should reuse lessons about similar past technical approaches "
        "instead of repeating a documented mistake in a fresh design.",
    ),
    "breakdown": (
        READS,
        "Decomposes the plan into tasks — memory.md is listed among "
        "Phase 0's required reads specifically for lessons about similar "
        "past decompositions, so a known pitfall in how a similar feature "
        "was split can inform task boundaries.",
    ),
    "implement": (
        READS,
        "Per-task preflight surfaces a section-aware memory excerpt so the "
        "dispatched engineer's brief carries known pitfalls forward "
        "instead of rediscovering the same lesson task after task.",
    ),
    "pr-review": (
        READS,
        "Reviews a foreign PR's diff for AI-slop, blast-radius, and "
        "scope-drift — pitfalls recorded from past reviews of this same "
        "codebase are exactly the context a reviewer should carry into an "
        "unfamiliar diff.",
    ),
    "audit": (
        READS,
        "The whole-codebase adversarial audit explicitly treats "
        "memory.md's pitfalls and past incidents as one of its context "
        "inputs when hunting for recurring issues.",
    ),
    "review": (
        READS,
        "Feature-level emergent cross-task review is the natural place to "
        "check whether an assembled change repeats a previously logged "
        "mistake that no single task's diff would surface alone.",
    ),
    "verify": (
        READS,
        "The single verdict-owning gate should weigh a finding against "
        "known repeat-offender patterns recorded from past features "
        "before rendering APPROVED / NEEDS WORK / REJECTED.",
    ),
    "grill": (
        READS,
        "The devil's-advocate design attack on plan.md should already "
        "know this codebase's documented past failure modes, so it does "
        "not raise a novel version of an already-fixed lesson.",
    ),
    "finalize": (
        READS,
        "Dispatches tech-writer with a surgical docs brief and commits "
        "the feature's memory.md delta — carrying forward known pitfalls "
        "into that brief keeps the shipped docs from omitting a "
        "documented gotcha at the last pipeline step that touches them.",
    ),
    "fix": (
        READS,
        "The gated remediation loop reuses /implement's back half, and a "
        "fix is exactly where a documented past mistake is most likely to "
        "resurface — the same per-task memory read /implement performs "
        "applies here.",
    ),
    # ---- N/A (8) -------------------------------------------------------------
    "init-forge": (
        NOT_APPLICABLE,
        "First command in the 4-command setup chain — captures five "
        "structural fields via mechanical prompts before any feature has "
        "ever been built in this install, so no project-specific lesson "
        "can yet exist to read.",
    ),
    "generate-docs": (
        NOT_APPLICABLE,
        "Second command in the setup chain — reads the indexed codebase "
        "to build the docs/ tiers, a mechanical code-reading pass with no "
        "judgment call that a prior-session lesson would inform.",
    ),
    "configure": (
        NOT_APPLICABLE,
        "Third command in the setup chain — substitutes file templates "
        "from init-forge + generate-docs state already captured; "
        "mechanical substitution, no judgment call for memory to bear on.",
    ),
    "constitute": (
        NOT_APPLICABLE,
        "Fourth command in the setup chain — establishes the rules "
        "memory.md entries will later be judged against, so it runs "
        "before any project-specific lesson exists to consult (mirrors "
        "init-forge's ordering argument).",
    ),
    "spec-check": (
        NOT_APPLICABLE,
        "Solves over a spec's OWN acceptance criteria for internal "
        "contradiction via the Z3 SMT solver — project lessons in "
        "memory.md do not bear on whether two ACs mathematically "
        "contradict each other.",
    ),
    "summarize": (
        NOT_APPLICABLE,
        "Pure synthesis over artifacts other commands already produced "
        "(verification.md, review.md, plan.md, task completion notes) — "
        "it renders no judgment of its own that memory could inform.",
    ),
    "report-bug": (
        NOT_APPLICABLE,
        "Pure capture — writes one bugs/NNN-slug.md and stops; "
        "dispatches no agent and renders no judgment for memory to "
        "inform.",
    ),
    "report-ticket": (
        NOT_APPLICABLE,
        "Pure capture — writes one tickets/NNN-slug.md and stops; "
        "dispatches no agent and renders no judgment for memory to "
        "inform.",
    ),
}  # type: Dict[str, Tuple[str, str]]


# ---------------------------------------------------------------------------
# Detection tokens / literals
# ---------------------------------------------------------------------------

# Rule 2(b) / Rule 3 token set — the field names a consuming surface must
# NAME to prove it actually reads back what a preflight produced. Also used
# (per the spec) for Rule 3, so an N/A command carrying ANY of these tokens
# anywhere in its surfaces or helper package fails, whether or not it names
# them "for consumption."
MEMORY_TOKENS = ("memory_excerpt", "memory_state")

# Rule 4 — the dead path this checker forbids under src/. Scoped to src/
# ONLY (see module docstring): tests/ deliberately keeps this literal in
# anti-regression assertions, and repo-root plan files cite it as history.
# A repo-wide rule would fail on its own regression net.
DEAD_PATH_LITERAL = ".claude/memory"

# Rule 2(a) — "a memory read is PERFORMED" is detected as a call to one of
# _shared/memory.py's read primitives (the single source of truth for the
# memory.md path + bounded-read shapes; see that module's docstring). A bare
# string like "memory_excerpt" appearing in a comment or docstring is NOT
# enough on its own to prove a read happens — an actual call is.
_MEMORY_READ_CALL_RE = re.compile(
    r"\b(read_memory_context|read_memory_excerpt|"
    r"probe_memory_state|memory_present)\s*\("
)

# A pre-existing launcher-naming exception: init-forge's helper is the
# monolithic init_helper.py, not init_forge_helper.py, and there is no
# _init_forge/ package dir. install.sh's --only surgical-delivery path
# computes the SAME cmd_u -> "_<cmd_u>/<cmd_u>_helper" mapping used below
# and would print "(no helper subpackage/launcher for 'init-forge')"
# without an equivalent special case — this is a known, pre-existing
# naming quirk, not something this checker invents.
_LAUNCHER_NAME_OVERRIDES = {"init-forge": "init"}

# Binary / generated file extensions to skip during the Rule 4 sweep — a
# .pyc decodes fine under errors="replace" but is never a place the dead
# literal would meaningfully appear, and skipping keeps the sweep fast.
_SKIP_EXTENSIONS = frozenset({
    ".pyc", ".pyo", ".png", ".jpg", ".jpeg", ".gif",
    ".ico", ".woff", ".woff2", ".ttf", ".eot",
})
_SKIP_DIR_NAMES = frozenset({"__pycache__"})


# ---------------------------------------------------------------------------
# Helper-source / command-surface path resolution
# ---------------------------------------------------------------------------

def _cmd_underscore(command):
    # type: (str) -> str
    return command.replace("-", "_")


def _helper_source_paths(src_root, command):
    # type: (Path, str) -> List[Path]
    """Return every existing .py source path for `command`'s helper.

    Covers BOTH the package dir (``_<cmd_u>/**/*.py``) and the single-file
    launcher (``<cmd_u>_helper.py``) — some commands (research, discover,
    ...) are thin shims over a package; others (plan, breakdown, ...) are
    still monolithic single files with no matching package. Both shapes
    are scanned so neither is silently skipped.
    """
    cmd_u = _LAUNCHER_NAME_OVERRIDES.get(command, _cmd_underscore(command))
    lib_root = src_root / "devforge" / "lib"
    paths = []  # type: List[Path]
    pkg_dir = lib_root / ("_" + cmd_u)
    if pkg_dir.is_dir():
        paths.extend(sorted(pkg_dir.rglob("*.py")))
    launcher = lib_root / (cmd_u + "_helper.py")
    if launcher.is_file():
        paths.append(launcher)
    return paths


def _command_surface_paths(src_root, command):
    # type: (Path, str) -> List[Path]
    """Return `main.md` + every `references/*.md` path for `command`."""
    cmd_dir = src_root / "commands" / command
    paths = []  # type: List[Path]
    main_md = cmd_dir / "main.md"
    if main_md.is_file():
        paths.append(main_md)
    refs_dir = cmd_dir / "references"
    if refs_dir.is_dir():
        paths.extend(sorted(refs_dir.glob("*.md")))
    return paths


def _read_text(path):
    # type: (Path) -> str
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _contains_any_memory_token(paths):
    # type: (List[Path]) -> bool
    for p in paths:
        text = _read_text(p)
        for tok in MEMORY_TOKENS:
            if tok in text:
                return True
    return False


def _helper_performs_read(paths):
    # type: (List[Path]) -> bool
    for p in paths:
        if _MEMORY_READ_CALL_RE.search(_read_text(p)):
            return True
    return False


# ---------------------------------------------------------------------------
# Rule 1: the promoted-command roster, parsed from the live emitter source
# ---------------------------------------------------------------------------

def _extract_promoted(repo_root):
    # type: (Path) -> Tuple[str, ...]
    """Parse ``_PROMOTED = (...)`` out of scripts/emitters/claude.py via AST.

    Reads the SOURCE FILE, not an imported module — avoids the sys.path /
    namespace-shadow gymnastics an actual import of the emitter needs (see
    tests/scripts/test_claude_emitter.py's ``_load_claude_emitter``), and
    mirrors the AST-parse-a-constant convention
    scripts/lib/agent_reachability.py already uses for the same reason
    (read-only, no import side effects).

    Returns an empty tuple if the file is missing, unparseable, or the
    assignment is not found — callers decide whether that is an error.
    """
    emitter_path = repo_root / "scripts" / "emitters" / "claude.py"
    if not emitter_path.is_file():
        return ()
    try:
        tree = ast.parse(
            emitter_path.read_text(encoding="utf-8", errors="replace"),
            filename=str(emitter_path),
        )
    except SyntaxError:
        return ()

    def _tuple_from_node(node):
        if isinstance(node, (ast.Tuple, ast.List)):
            return tuple(
                elt.value
                for elt in node.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            )
        return None

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == "_PROMOTED":
                    result = _tuple_from_node(node.value)
                    if result is not None:
                        return result
        elif isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Name)
                and node.target.id == "_PROMOTED"
                and node.value is not None
            ):
                result = _tuple_from_node(node.value)
                if result is not None:
                    return result
    return ()


# ---------------------------------------------------------------------------
# Rule 4: dead-path literal sweep
# ---------------------------------------------------------------------------

def _sweep_dead_path_literal(src_root):
    # type: (Path) -> List[str]
    """Return "path:line" strings for every occurrence of DEAD_PATH_LITERAL.

    Scoped to src_root ONLY (see module docstring / DEAD_PATH_LITERAL).
    Paths are rendered relative to src_root's parent (the repo root) with
    forward slashes, matching the forward-slash path-literal convention
    used throughout this framework.
    """
    hits = []  # type: List[str]
    repo_root = src_root.parent
    for path in sorted(src_root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix in _SKIP_EXTENSIONS:
            continue
        if any(part in _SKIP_DIR_NAMES for part in path.parts):
            continue
        text = _read_text(path)
        if DEAD_PATH_LITERAL not in text:
            continue
        rel = path.relative_to(repo_root).as_posix()
        for lineno, line in enumerate(text.splitlines(), start=1):
            if DEAD_PATH_LITERAL in line:
                hits.append("{}:{}".format(rel, lineno))
    return hits


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def find_gaps(repo_root):
    # type: (object) -> Dict[str, List[str]]
    """Scan `repo_root` for memory-lane coverage gaps.

    Parameters
    ----------
    repo_root : path-like or str
        Root of the repository (the directory containing ``src/`` and
        ``scripts/``).

    See the module docstring for the return shape and the SCOPE STATEMENT
    (honest non-coverage) — a clean result is not a claim about memory
    quality.
    """
    repo_root = Path(repo_root)
    src_root = repo_root / "src"

    promoted = _extract_promoted(repo_root)

    no_disposition = []       # type: List[str]
    empty_reason = []         # type: List[str]
    reads_missing_read = []   # type: List[str]
    reads_missing_named = []  # type: List[str]
    na_leaks = []              # type: List[str]

    for command in promoted:
        entry = DISPOSITIONS.get(command)
        if entry is None:
            no_disposition.append(command)
            continue

        disposition, reason = entry
        if not reason or not reason.strip():
            empty_reason.append(command)
            # Fall through — an empty reason does not excuse the
            # read-coverage check for this command; still evaluate it.

        helper_paths = _helper_source_paths(src_root, command)
        surface_paths = _command_surface_paths(src_root, command)

        if disposition == READS:
            if not _helper_performs_read(helper_paths):
                reads_missing_read.append(command)
            if not _contains_any_memory_token(surface_paths):
                reads_missing_named.append(command)
        elif disposition == NOT_APPLICABLE:
            if (
                _contains_any_memory_token(helper_paths)
                or _contains_any_memory_token(surface_paths)
            ):
                na_leaks.append(command)
        # An unrecognized disposition value would be a bug in DISPOSITIONS
        # itself (not a live-src violation) — a suite-level sanity test
        # covers that; it is not reported by find_gaps().

    dead_path = _sweep_dead_path_literal(src_root) if src_root.is_dir() else []

    return {
        "no_disposition": sorted(no_disposition),
        "empty_reason": sorted(empty_reason),
        "reads_missing_helper_read": sorted(reads_missing_read),
        "reads_missing_consumption": sorted(reads_missing_named),
        "na_leaks_memory": sorted(na_leaks),
        "dead_path_literal": sorted(dead_path),
    }
