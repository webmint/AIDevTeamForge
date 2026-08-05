"""Feature-directory allocation substrate shared by /research, /discover, /specify.

Extracted from src/devforge/lib/_specify/_cmds_handoff.py (next_spec_number,
formerly `_next_spec_number`) and _specify/_cmds_phase4_setters.py
(decide_branch_action, the decision core of cmd_create_branch), per
68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 1 / OQ-1.

Why shared, not a cross-helper shell-out: OQ-1 rejected having research_helper
or discover_helper shell out to specify_helper, because that would make one
command's helper a runtime dependency of another's -- nothing in the
framework does that today.  The precedent is _shared/feature_scope.py
(extracted from _review/, re-imported by /review, /verify, /summarize,
/finalize).  This module follows the exact same shape: pure functions here,
thin per-package re-exports / CLI verbs in each consumer package.

What lives here
----------------
FEATURE_NAME_RE        -- 2-4 word lowercase kebab-case slug validator.
                           Moved from _specify/_schema.py; re-exported there
                           under the same name so existing `from ._schema
                           import FEATURE_NAME_RE` imports are unaffected.
SPECS_ROOT_DEFAULT, SPEC_NUMBER_WIDTH, SPEC_NUMBER_DIR_RE
                        -- NNN dir-naming constants.  Same relocate-and-
                           re-export treatment as FEATURE_NAME_RE (single
                           source of truth for the constants
                           next_spec_number / allocate_feature_dir use).
next_spec_number        -- pure filesystem scan: next NNN under specs/.
decide_branch_action    -- pure decision: what to print / do for branch
                           creation, given (current, default, spec_number,
                           slug).  Three named arms (see its docstring);
                           /specify's cmd_create_branch delegates to this
                           for its two reachable arms and stays byte-
                           identical on stdout for both (see docstring).
allocate_feature_dir    -- creates specs/NNN-slug/ on disk (FRESH
                           allocation only -- see "Attach mode" below).

Repo-root / install-root resolution
------------------------------------
Every function here takes a `devforge_dir` argument and resolves the repo
root (== install root in wrapper mode) as `Path(devforge_dir).resolve().parent`
-- the same convention `_next_spec_number` used before this move, and the
same one every wrapper-mode-aware verb in this codebase relies on: the
caller passes `--devforge-dir <install-root>/.devforge`, and the install
root falls out as its parent.  No separate wrapper-mode branch is needed
here because the wrapper/standalone distinction is already baked into
which `--devforge-dir` value the caller passed in.

Attach mode (D6) is out of scope here -- read this before wiring a caller
------------------------------------------------------------------------
allocate_feature_dir is a FRESH-ALLOCATION-ONLY function.  Plan 68 D6
(repeat intake on the same feature via a /grill RE-ENTER-UPSTREAM seed)
needs the OPPOSITE behavior: skip allocation and branch creation entirely,
because the seed's own location (specs/NNN-slug/grill-seed.json) already
identifies the existing feature dir.  This module deliberately does NOT
provide an "allocate-or-attach" mode, an `existing_dir` parameter, or any
form of "give me the dir whether or not it already exists" -- adding one
would let a caller silently paper over a real allocation bug (a second
"fresh" call landing on an already-populated dir) with attach semantics
that were never asked for.

The decision (recorded for Phase 2/3, which wire the actual command specs):
a caller in attach mode must already know the feature dir path (it read it
off the seed) and must skip calling allocate_feature_dir altogether -- it
writes directly into the known dir.  allocate_feature_dir's own idempotence
story is therefore simple: it always either creates a brand-new directory
or fails loudly (see "Never overwrite" below); it is never asked to be
idempotent across two calls for the "same" feature, because attach-mode
callers never call it a second time for that feature in the first place.

Never overwrite
----------------
allocate_feature_dir refuses to reuse an existing target directory, even if
that target happens to be exactly the NNN the scan would have picked next
(a race between two concurrent invocations, or a manual retry after a
partial failure).  It fails loudly with a clear error string; the caller
writes that to stderr and exits non-zero.  There is no silent-reuse path.

Slug collisions across different NNN (OQ-4)
--------------------------------------------
allocate_feature_dir does NOT check whether the slug is already used by
another NNN.  OQ-4 ratified this: NNN is the identity, the slug is a label,
and two features may legitimately want the same slug.  See the module's
test file for the round-trip proof (two allocations, same slug, two NNNs).

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Constants (moved from _specify/_schema.py -- see module docstring).
# ---------------------------------------------------------------------------

FEATURE_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+){1,3}$")

SPECS_ROOT_DEFAULT = "specs"
SPEC_NUMBER_WIDTH = 3
SPEC_NUMBER_DIR_RE = re.compile(r"^(\d{3})-")

# The branch-name prefix every spec branch carries (spec/NNN-slug).
_SPEC_BRANCH_PREFIX = "spec/"


# ---------------------------------------------------------------------------
# next_spec_number (moved from _specify/_cmds_handoff.py::_next_spec_number).
# ---------------------------------------------------------------------------


def next_spec_number(devforge_dir):
    # type: (Union[str, "os.PathLike[str]"]) -> int
    """Compute the next NNN spec number by scanning the specs/ directory.

    Looks for subdirectories matching the NNN-* pattern under
    repo_root/specs/, where repo_root is the parent of devforge_dir.
    Returns 1 if specs/ does not exist, is not a directory, or contains no
    NNN-* subdirectories.  Pure filesystem scan -- no state file involved.
    """
    repo_root = Path(devforge_dir).resolve().parent
    specs_root = repo_root / SPECS_ROOT_DEFAULT
    if not specs_root.exists() or not specs_root.is_dir():
        return 1
    existing = []  # type: List[int]
    for entry in specs_root.iterdir():
        if entry.is_dir():
            m = SPEC_NUMBER_DIR_RE.match(entry.name)
            if m:
                existing.append(int(m.group(1)))
    return (max(existing) + 1) if existing else 1


# ---------------------------------------------------------------------------
# allocate_feature_dir
# ---------------------------------------------------------------------------


def allocate_feature_dir(devforge_dir, slug):
    # type: (Union[str, "os.PathLike[str]"], str) -> Tuple[dict, Optional[str]]
    """Allocate a fresh specs/NNN-<slug>/ directory.

    FRESH ALLOCATION ONLY -- see the module docstring's "Attach mode"
    section before wiring an attach-mode (D6) caller into this function.

    Validates slug (2-4 word lowercase kebab-case, the same shape
    specify_helper assign-feature-name enforces via FEATURE_NAME_RE),
    computes the next NNN via next_spec_number, and creates
    repo_root/specs/NNN-<slug>/.  repo_root is the parent of devforge_dir
    (== the install root in wrapper mode -- see module docstring).

    Returns (result, error), mirroring _shared/feature_scope.py's
    resolve_feature_scope convention:
      On success: (dict, None).  dict keys:
        path             str  -- absolute path to the created directory
        number           int  -- the allocated NNN, unpadded
        formatted_number str  -- zero-padded NNN, e.g. "004"
        slug             str  -- the validated slug (echoed back, stripped)
        dirname          str  -- "NNN-slug" (the directory's basename)
        created          bool -- always True on success
      On error: ({}, message).  The caller writes message to stderr and
      exits non-zero.  Errors:
        - slug is empty or fails FEATURE_NAME_RE
        - the computed target directory already exists (see "Never
          overwrite" in the module docstring -- this is never silently
          reused, including on a race between the scan and the mkdir)
        - the directory cannot be created (permissions, etc.)
    """
    cleaned_slug = (slug or "").strip()
    if not FEATURE_NAME_RE.match(cleaned_slug):
        return {}, (
            "invalid slug {0!r}: expected 2-4 word lowercase kebab-case "
            "(lower-case alnum segments joined by '-', first char a "
            "letter, 2-4 segments)".format(slug)
        )

    repo_root = Path(devforge_dir).resolve().parent
    specs_root = repo_root / SPECS_ROOT_DEFAULT
    number = next_spec_number(devforge_dir)
    formatted_number = "{0:0{w}d}".format(number, w=SPEC_NUMBER_WIDTH)
    dirname = "{0}-{1}".format(formatted_number, cleaned_slug)
    target = specs_root / dirname

    if target.exists():
        return {}, (
            "feature dir already exists: {0} (refusing to reuse -- "
            "allocate_feature_dir is fresh-allocation-only; an attach-mode "
            "caller must already know the existing dir and must not call "
            "this function)".format(target)
        )

    try:
        target.mkdir(parents=True, exist_ok=False)
    except OSError as err:
        return {}, "cannot create {0}: {1}".format(target, err)

    return {
        "path": str(target),
        "number": number,
        "formatted_number": formatted_number,
        "slug": cleaned_slug,
        "dirname": dirname,
        "created": True,
    }, None


# ---------------------------------------------------------------------------
# decide_branch_action (extracted from
# _specify/_cmds_phase4_setters.py::cmd_create_branch).
# ---------------------------------------------------------------------------


def decide_branch_action(current_branch, default_branch, spec_number, slug):
    # type: (str, str, Optional[str], Optional[str]) -> Tuple[str, str, Optional[str]]
    """Decide the branch-creation action for a spec/NNN-slug feature.

    Pure function -- no filesystem or git access; the caller runs the
    returned git command (or does nothing, on a "keep" decision).

    Three arms:
      1. current_branch == default_branch
         -> decision "create".  Requires spec_number and slug (both
            truthy); if either is missing, returns decision="create" with
            a non-None error and an empty line -- the caller must not
            treat that as success.  On success, line is the checkout
            command "git checkout -b spec/<spec_number>-<slug>" (no
            trailing newline -- the caller appends one).
      2. current_branch != default_branch AND current_branch already
         starts with "spec/"
         -> decision "keep-spec".  The session is already on a feature
            branch; no checkout is emitted.  line carries the SAME text
            as arm 3 (see below) -- the original /specify implementation
            never distinguished this case textually, only arm 1 vs
            "everything else"; decision distinguishes the arms for
            callers that care, without changing the rendered text.
      3. current_branch != default_branch AND current_branch does NOT
         start with "spec/"
         -> decision "keep-other".  Informational comment, no checkout:
            "# already on non-default branch '<current_branch>'; no
            checkout emitted" (no trailing newline).

    This exact wording for arms 2/3 is load-bearing: it must stay
    byte-identical to the string /specify's cmd_create_branch has always
    emitted for its "keep" arm, because cmd_create_branch delegates to
    this function and its existing tests assert on that text indirectly
    via state fields (not the string itself), but future callers should
    not assume the string is free to change -- see
    _specify/_cmds_phase4_setters.py::cmd_create_branch.

    Returns (decision, line, error):
      decision -- one of "create", "keep-spec", "keep-other".
      line     -- the text to print (git command or informational
                  comment), WITHOUT a trailing newline; "" when error is
                  not None.
      error    -- None on success; a message string when decision would
                  be "create" but spec_number/slug were not supplied.
    """
    current = (current_branch or "").strip()
    default = (default_branch or "").strip()

    if current == default:
        if not spec_number or not slug:
            return (
                "create",
                "",
                "spec_number and slug are required to create a branch "
                "when on the default branch",
            )
        branch = "{0}{1}-{2}".format(_SPEC_BRANCH_PREFIX, spec_number, slug)
        return "create", "git checkout -b {0}".format(branch), None

    skip_line = "# already on non-default branch {0!r}; no checkout emitted".format(
        current
    )
    if current.startswith(_SPEC_BRANCH_PREFIX):
        return "keep-spec", skip_line, None
    return "keep-other", skip_line, None
