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
specs_root_for          -- explicit devforge_dir -> specs_root derivation
                           (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-
                           PLAN.md Phase 1, revised).  A small pure-path
                           helper, not a scan: it makes the devforge_dir
                           -> repo_root -> specs_root arithmetic visible
                           at the call site instead of hidden inside a
                           scan function.
iter_feature_dirs       -- every feature directory under a GIVEN specs
                           root, across both the legacy NNN-slug/ shape
                           and the Phase-3 YYYY/MM/TICKET/ shape (91-
                           FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md
                           Phase 1's resolution accessor).  Takes the
                           specs/ directory directly, NOT a devforge_dir
                           -- see "specs_root, not devforge_dir" below.
                           Returns [] -- never raises -- when specs_root
                           is absent, not a directory, or unreadable (any
                           OSError while probing it); a feature-less
                           caller (e.g. plan 88's cold /devforge:fix lane)
                           is a supported state, not an error.
find_feature_dirs_with  -- iter_feature_dirs filtered to dirs containing a
                           given filename.  Same specs_root-not-devforge_dir
                           signature.
TICKET_RE               -- OQ-2's ratified ticket-ID format:
                           [A-Z]+-[0-9]+ (e.g. "PROJ-123").  Full-string,
                           uppercase-only match -- see normalize_ticket's
                           docstring for why lowercase is rejected rather
                           than folded.
normalize_ticket        -- validate + normalize a ticket ID (OQ-2).
                           Format-only; never confirms the ticket exists
                           anywhere (91-FEATURE-DIR-IDENTITY-AND-
                           PROVENANCE-PLAN.md Phase 2, D4 point 1).
read_require_ticket      -- read REQUIRE_TICKET from
                           devforge_dir/project-config.json (OQ-1).
                           Fails open (False) on any read/parse problem
                           or on an absent key -- see its own docstring.

specs_root, not devforge_dir
-----------------------------
(91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 1, revised after the
first cut of this accessor shipped with a `devforge_dir` parameter.)

iter_feature_dirs and find_feature_dirs_with take a `specs_root` directly.
Their actual job is "enumerate feature directories under a given specs
root" -- the devforge_dir -> repo_root -> specs_root derivation is a
caller CONVENIENCE, not part of that job, and baking it into these two
functions forced every caller shape onto one parameter name:
  - a caller holding a real devforge_dir (e.g. a CLI verb that received
    --devforge-dir) derives its specs_root explicitly via
    specs_root_for(devforge_dir) before calling either function.
  - a caller holding a repo root it already knows about (most of the six
    depth-1 consumers this accessor replaces) passes `root / "specs"`
    directly -- no devforge_dir, fabricated or otherwise, anywhere in the
    call.
  - a caller holding an ARBITRARY, non-repo-root-derived specs directory
    (/grill's `--specs-dir` override) passes it straight through. The
    prior devforge_dir-only signature could not express this caller shape
    at all, which is why /grill was the one site that could not migrate
    onto the first cut of this accessor.
iter_feature_dirs performs NO implicit resolution of its own on
specs_root -- it is used exactly as given (see the function's own
docstring). A caller that wants repo-root-derived canonicalisation gets
it from specs_root_for (which does call Path(devforge_dir).resolve()); a
caller that never asked for symlink canonicalisation -- because its own
pre-migration behaviour never called resolve()/realpath() anywhere, e.g.
_pr_review/_handoff_import.py's _scan_specs_dir -- never silently
receives it now either.

next_spec_number and allocate_feature_dir are UNCHANGED by this: they
still take `devforge_dir` directly and resolve the repo root internally
as `Path(devforge_dir).resolve().parent` -- the same convention
`_next_spec_number` used before this module existed, and the same one
every wrapper-mode-aware verb in this codebase relies on: the caller
passes `--devforge-dir <install-root>/.devforge`, and the install root
falls out as its parent. No separate wrapper-mode branch is needed here
because the wrapper/standalone distinction is already baked into which
`--devforge-dir` value the caller passed in.

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
writes directly into the known dir.  This is also why REQUIRE_TICKET
(Phase 2, D4/OQ-5) is a deliberate no-op on the attach-mode path: since
attach mode never calls allocate_feature_dir, the ticket/require_ticket
parameters below never execute for it -- there is no separate attach-mode
branch to write inside this function, because the function itself is
simply never reached.  The ticket, if the resumed feature has one, is
already sitting in that feature's own directory/state, not re-asked.  allocate_feature_dir's own idempotence
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

import json
import re
from pathlib import Path
from typing import List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Constants (moved from _specify/_schema.py -- see module docstring).
# ---------------------------------------------------------------------------

FEATURE_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+){1,3}$")

SPECS_ROOT_DEFAULT = "specs"
SPEC_NUMBER_WIDTH = 3
# Gained a second capture group (68-INTAKE-OWNS-FEATURE-DIR-PLAN.md Phase 4
# python-reviewer finding 1): a feature-dir basename like "003-foo-bar" can
# now be split into (number, slug) in one match -- used by
# _specify/_cmds_handoff.py's import-handoff to seed state["spec_number"] /
# state["feature_slug"] from the RESOLVED intake dir the handoff already
# sits in, instead of leaving them for a fresh NNN scan.
#
# Deliberately kept at EXACTLY 3 digits (not widened to \d{3,}) -- a
# widened digit count would flip next_spec_number's existing "4+-digit
# dirs are not recognized as spec dirs" contract (pinned by
# tests/lib/_shared/test_feature_alloc.py::test_non_nnn_dirs_ignored,
# which asserts a "9999-too-many-digits" dir is ignored), silently
# growing that scanner's matching surface as an unintended side effect of
# this unrelated change. Every existing group(1)-only consumer
# (next_spec_number / allocate_feature_dir /
# _cmds_phase4_setters._existing_spec_numbers) is therefore
# match/non-match-identical to before this edit; only the added
# group(2) + the `$` end-anchor (harmless -- real dir basenames never
# have trailing content past the slug) are new.
SPEC_NUMBER_DIR_RE = re.compile(r"^(\d{3})-(.+)$")

# Phase-3 forward structure (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-
# PLAN.md D2): specs/<YYYY>/<MM>/<TICKET>/, the layout Phase 3 will start
# writing.  Matches nothing on any real install today -- allocate_feature_dir
# above still exclusively writes the legacy specs/NNN-slug/ shape.  Defined
# now (rather than at Phase 3) so iter_feature_dirs below can read this
# shape before any writer produces it -- see that function's docstring and
# Phase 1's ⚠ instruction to build the variable-depth branch from the
# start, not as a later rewrite.
#
# No ambiguity with SPEC_NUMBER_DIR_RE above: a legacy dir name is exactly
# three digits followed by a dash (the dash is required); a year dir name
# is exactly four bare digits with no dash at all.  A name matching neither
# (e.g. "9999-too-many-digits") is claimed by neither pattern.
YEAR_DIR_RE = re.compile(r"^\d{4}$")
MONTH_DIR_RE = re.compile(r"^\d{2}$")

# The branch-name prefix every spec branch carries (spec/NNN-slug).
_SPEC_BRANCH_PREFIX = "spec/"

# Ticket identity (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 2,
# OQ-2 ratified): one-or-more uppercase letters, a dash, one-or-more digits
# (e.g. "PROJ-123").  Full-string match (re.match anchors at the start;
# the trailing "$" anchors the end) -- see normalize_ticket's docstring
# below for why this is upper-case-only rather than case-insensitive.
# The same shape _implement/_cmds_commit.py's _TICKET_PATTERN extracts
# from a branch name (there via re.search with word boundaries, scraping
# a token out of a larger string; here via re.match, validating a value
# the operator typed directly) -- one ticket notion, not two.
TICKET_RE = re.compile(r"^[A-Z]+-[0-9]+$")

# project-config.json filename + key, read by read_require_ticket below.
_PROJECT_CONFIG_FILENAME = "project-config.json"
_REQUIRE_TICKET_KEY = "REQUIRE_TICKET"


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
# Ticket identity (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 2).
# ---------------------------------------------------------------------------


def normalize_ticket(raw):
    # type: (Optional[str]) -> Tuple[Optional[str], Optional[str]]
    """Validate and normalize a ticket ID (OQ-2, ratified).

    Format: TICKET_RE -- one-or-more uppercase letters, a dash, one-or-
    more digits (e.g. "PROJ-123").

    Canonical case is UPPERCASE.  The ONLY transformation this function
    applies is stripping leading/trailing whitespace (mirroring
    allocate_feature_dir's own `cleaned_slug = (slug or "").strip()`
    convention) -- it never folds case.  A lowercase or mixed-case value,
    e.g. "proj-123", is therefore REJECTED, not silently upper-cased into
    a spelling the caller never typed.

    This is the deliberate reading of OQ-2's "must be normalized at
    allocation, not left to the typist" instruction, chosen over case-
    folding for two reasons:

    1. OQ-2's own text lists lowercase input as a "close but wrong" case
       that "must fail cleanly, not silently normalize into something
       else" -- which rules out auto-uppercasing directly.
    2. Rejection closes the case-insensitive-filesystem hazard the same
       note names (on macOS, "PROJ-123" and "proj-123" would collide; on
       Linux they would not) BY CONSTRUCTION rather than by coercion:
       since only the one canonical (uppercase) spelling can ever pass
       this function, two differently-cased directories for "the same"
       ticket can never both be created downstream, on either kind of
       filesystem -- there is no second spelling left to collide with
       the first. Silently coercing the case instead would also bake a
       value the operator never confirmed into a directory name and a
       git branch (D5) -- the opposite of what "normalized at
       allocation" is trying to prevent.

    Returns (ticket, error):
      Success: (the stripped, already-canonical ticket string, None).
      Failure: (None, a message naming the expected format) when raw is
        None, empty, or blank after stripping, or does not match
        TICKET_RE once stripped -- covers a bare number ("123"), a space
        where the dash belongs ("PROJ 123"), lowercase or mixed case
        ("proj-123", "Proj-123"), and any other close-but-wrong
        spelling. Every failure returns a message; none is silently
        reinterpreted into something the caller did not type.

    This function checks FORMAT only. It never confirms the ticket
    exists in an external tracker -- nothing in this framework can. A
    caller must not read a successful return as verification of
    anything beyond "this string is shaped like a ticket ID".
    """
    stripped = (raw or "").strip()
    if not stripped:
        return None, (
            "no ticket supplied: expected the format LETTERS-NUMBER "
            "(e.g. 'PROJ-123', uppercase letters only)"
        )
    if not TICKET_RE.match(stripped):
        return None, (
            "invalid ticket {0!r}: expected the format LETTERS-NUMBER "
            "(e.g. 'PROJ-123', uppercase letters only -- lowercase and "
            "mixed case are rejected, never silently upper-cased)".format(raw)
        )
    return stripped, None


def read_require_ticket(devforge_dir):
    # type: (Union[str, "os.PathLike[str]"]) -> bool
    """Read REQUIRE_TICKET from devforge_dir/project-config.json (OQ-1).

    Returns True iff the key's value is EXACTLY the string "true". Every
    other case returns False:
      - project-config.json is absent or unreadable (any OSError)
      - its content is not valid JSON, or the top-level value is not a
        JSON object
      - the REQUIRE_TICKET key is absent
      - the key's value is anything other than the string "true"
        (including "false", "True", "TRUE", a JSON boolean, or garbage)

    This is a deliberate fail-OPEN default, matching OQ-1's ratified
    "opt-in, default false" policy: an install that never configured the
    key, or whose config this function could not read for any reason,
    must not be silently handed ticket-required friction it never chose
    (D4's own framing -- "a key nobody must enable imposes nothing").
    REQUIRE_TICKET is discipline, not verification (D4 point 1) -- it is
    not a security control -- so failing open here trades away no safety
    property for that guarantee.

    Never raises.

    Deliberately independent of any project-config.json reader elsewhere
    in this codebase (e.g. _verify/_e2e.py's own _read_config,
    _implement/_cmds_commit.py's _load_project_config): see
    _verify/_e2e.py's module docstring for the precedent this follows --
    "two independent config readers for two independent keys, so a
    change to one gate's read path can never silently move the other's".
    This module already avoids the opposite anti-pattern (a cross-helper
    shell-out) for a parallel reason -- see the module docstring's "Why
    shared" section -- but reading the SAME file that other helpers also
    read is not that anti-pattern: it is one file, several independent
    readers, each owning only the one key it needs.
    """
    config_path = Path(devforge_dir) / _PROJECT_CONFIG_FILENAME
    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError:
        return False
    try:
        data = json.loads(raw)
    except ValueError:
        return False
    if not isinstance(data, dict):
        return False
    return data.get(_REQUIRE_TICKET_KEY) == "true"


# ---------------------------------------------------------------------------
# allocate_feature_dir
# ---------------------------------------------------------------------------


def allocate_feature_dir(devforge_dir, slug, ticket=None, require_ticket=False):
    # type: (Union[str, "os.PathLike[str]"], str, Optional[str], bool) -> Tuple[dict, Optional[str]]
    """Allocate a fresh specs/NNN-<slug>/ directory.

    FRESH ALLOCATION ONLY -- see the module docstring's "Attach mode"
    section before wiring an attach-mode (D6) caller into this function.

    Validates slug (2-4 word lowercase kebab-case, the same shape
    specify_helper assign-feature-name enforces via FEATURE_NAME_RE),
    computes the next NNN via next_spec_number, and creates
    repo_root/specs/NNN-<slug>/.  repo_root is the parent of devforge_dir
    (== the install root in wrapper mode -- see module docstring).

    ticket / require_ticket (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-
    PLAN.md Phase 2): ticket is the raw string the operator supplied, or
    None/empty when none was given.  require_ticket is the caller's own
    read_require_ticket(devforge_dir) result -- passed in explicitly
    rather than read here, so this function stays a plain function of
    its arguments (testable with a bare boolean, no project-config.json
    fixture needed per case) and so config-file reading stays owned by
    read_require_ticket alone (one reader, not two).  ticket is
    validated via normalize_ticket whenever it is non-blank, regardless
    of require_ticket, so a malformed value is never silently accepted;
    it is additionally REQUIRED (missing/blank refuses too) when
    require_ticket is True.  Phase 3, not this one, teaches the
    directory layout itself to use the ticket -- see that plan's Phase 2
    scope note -- so on success here the directory is still
    specs/NNN-<slug>/ regardless of whether a ticket was supplied.

    Returns (result, error), mirroring _shared/feature_scope.py's
    resolve_feature_scope convention:
      On success: (dict, None).  dict keys:
        path             str  -- absolute path to the created directory.
                                  For USER-FACING MESSAGES only (a status
                                  line, an error string) -- never for a
                                  path ARGUMENT passed to another helper
                                  verb or a value WRITTEN into a committed
                                  artifact, because it leaks the local
                                  filesystem layout (e.g. a home directory)
                                  into text that gets committed. Use
                                  relative_path for those (see below); this
                                  key's meaning is unchanged and it is not
                                  deprecated.
        relative_path    str  -- CANONICAL for path ARGUMENTS and for
                                  anything WRITTEN into an artifact: the
                                  feature directory relative to the repo
                                  root (the same root `path` is resolved
                                  against -- Path(devforge_dir).resolve()
                                  .parent), e.g. "specs/007-user-auth".
                                  Always forward-slash-separated, on every
                                  platform -- this value is written into
                                  markdown artifacts and passed as CLI
                                  arguments, so a backslash variant on
                                  Windows would produce a different byte
                                  in a committed file. Follows the same
                                  discipline _shared/memory.py's
                                  MEMORY_RELATIVE_PATH documents for
                                  itself: a forward-slash path, never
                                  platform-joined. Never relative to the
                                  current working directory and never
                                  relative to specs/ itself -- always
                                  relative to the repo root.
        number           int  -- LEGACY-SHAPE-ONLY: the allocated NNN,
                                  unpadded.  Meaningless once a caller
                                  writes the Phase-3 specs/YYYY/MM/TICKET/
                                  layout -- still emitted for the current
                                  NNN-slug shape, but new prose must not
                                  consume it.
        formatted_number str  -- LEGACY-SHAPE-ONLY: zero-padded NNN, e.g.
                                  "004".  Same bound as `number` above.
                                  Still the value render-branch-command
                                  --number consumes.
        slug             str  -- the validated slug (echoed back, stripped)
        dirname          str  -- LEGACY-SHAPE-ONLY: "NNN-slug" (the
                                  directory's basename, UN-prefixed --
                                  callers that want the specs/-relative
                                  path use relative_path instead of
                                  composing "specs/" + dirname
                                  themselves).  Same bound as `number`
                                  above -- a Phase-3 ticket-keyed leaf has
                                  no "NNN-slug" shape to report.
        ticket           str | None -- the normalized ticket (canonical
                                  uppercase, per normalize_ticket) when
                                  one was supplied and valid; None when
                                  none was supplied (only possible when
                                  require_ticket is False).  Not yet
                                  consumed by the directory layout itself
                                  -- see the ticket/require_ticket
                                  paragraph above.
        created          bool -- always True on success
      On error: ({}, message).  The caller writes message to stderr and
      exits non-zero.  Errors:
        - slug is empty or fails FEATURE_NAME_RE
        - a ticket was supplied but fails normalize_ticket (checked
          regardless of require_ticket -- a malformed ticket is never
          silently accepted)
        - require_ticket is True and no ticket (or an invalid one) was
          supplied -- message names both routes out: supply one in the
          right format, or turn REQUIRE_TICKET off
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

    # Ticket identity (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md
    # Phase 2, D4/OQ-2).  Validate whenever a ticket was supplied (so a
    # malformed value is never silently accepted, whatever require_ticket
    # is); additionally REQUIRE a valid one when require_ticket is True.
    norm_ticket = None
    ticket_supplied = bool((ticket or "").strip())
    if ticket_supplied or require_ticket:
        norm_ticket, ticket_error = normalize_ticket(ticket)
        if ticket_error is not None:
            if require_ticket:
                return {}, (
                    "{0} -- REQUIRE_TICKET is enabled for this project. "
                    "Either supply a ticket in that format, or run "
                    "/devforge:configure and turn REQUIRE_TICKET off "
                    "(configure_helper set-require-ticket false) to "
                    "allocate without one.".format(ticket_error)
                )
            return {}, ticket_error

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
        "relative_path": target.relative_to(repo_root).as_posix(),
        "number": number,
        "formatted_number": formatted_number,
        "slug": cleaned_slug,
        "dirname": dirname,
        "ticket": norm_ticket,
        "created": True,
    }, None


# ---------------------------------------------------------------------------
# specs_root_for
# ---------------------------------------------------------------------------


def specs_root_for(devforge_dir):
    # type: (Union[str, "os.PathLike[str]"]) -> Path
    """Return the specs/ directory implied by a .devforge directory.

    repo_root/specs, where repo_root = Path(devforge_dir).resolve().parent
    -- the same convention next_spec_number / allocate_feature_dir use.
    Pure path arithmetic: does not stat devforge_dir, the returned
    specs_root, or any ancestor -- safe to call even when none of them
    exist on disk.

    Exists so a devforge_dir-holding caller can reach the specs_root
    iter_feature_dirs / find_feature_dirs_with actually take in one
    explicit call, without those two functions themselves needing a
    devforge_dir parameter (see the module docstring's "specs_root, not
    devforge_dir" section for why that split is the point, not an
    inconvenience).
    """
    repo_root = Path(devforge_dir).resolve().parent
    return repo_root / SPECS_ROOT_DEFAULT


# ---------------------------------------------------------------------------
# iter_feature_dirs / find_feature_dirs_with
# (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 1's resolution
# accessor -- see the module docstring's "What lives here" entry).
# ---------------------------------------------------------------------------


def iter_feature_dirs(specs_root):
    # type: (Union[str, "os.PathLike[str]"]) -> List[Path]
    """Return every feature directory under specs_root, across both layouts.

    Takes the specs/ directory DIRECTLY, not a devforge_dir -- see the
    module docstring's "specs_root, not devforge_dir" section. specs_root
    is used exactly as given: this function performs NO implicit
    .resolve() of its own, so a caller that never asked for symlink
    canonicalisation never gets it (a devforge_dir-holding caller that
    wants that canonicalisation gets it explicitly from specs_root_for).

    Reads two shapes in a SINGLE pass over specs/'s own listing, dispatched
    on directory-NAME shape -- not a flat iterdir() (that would only ever
    see the legacy shape's own dirs plus, under the new layout, YEAR
    directories, and could never see a new-shape feature dir at all; see
    Phase 1's ⚠ on why the depth branch is built now rather than at
    Phase 3):

      1. Legacy: specs/NNN-slug/ -- an immediate child of specs/ whose
         name matches SPEC_NUMBER_DIR_RE.  This is the ONLY shape any
         installation has today; allocate_feature_dir still exclusively
         writes it.
      2. Phase-3 forward shape: specs/YYYY/MM/TICKET/ -- a 4-digit year
         directory (YEAR_DIR_RE) containing a 2-digit month directory
         (MONTH_DIR_RE) containing feature directories.  No writer
         produces this shape yet, so this arm returns nothing on any real
         install as of this writing; it exists so a later Phase-3 layout
         switch does not require rewriting this accessor.

    There is no ambiguity between the two arms: a legacy dir name is
    exactly three digits then a dash (the dash is required); a year dir
    name is exactly four bare digits with no dash.  A name matching
    neither -- e.g. a stray "9999-too-many-digits" dir -- is claimed by
    neither arm and is silently excluded from the result, exactly as it
    always has been under next_spec_number's identical exclusion (see
    SPEC_NUMBER_DIR_RE's own comment and
    tests/lib/_shared/test_feature_alloc.py::test_non_nnn_dirs_ignored).
    Because the two patterns are provably disjoint (a legacy match
    requires a literal "-" at index 3, which disqualifies the all-digit
    year pattern), each specs/ entry is classified with a single
    if/elif -- one iterdir() of specs/ itself, not two -- so a directory
    created or removed between two independent scans can no longer be
    seen by one arm and missed by the other.

    Returns [] -- never raises -- when specs_root does not exist, is not a
    directory, or is UNREADABLE (any OSError -- e.g. EACCES from a
    locked-down specs_root or an ancestor directory -- while probing
    specs_root or walking its children is treated as "contains nothing"
    at that level, exactly like the missing-directory case). This is a
    SUPPORTED state,
    not an error path: a caller may legitimately hold no feature reference
    at all (plan 88's cold /devforge:fix lane runs with no feature
    directory at all, by design -- see
    91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 1's "Scope"
    paragraph). Do not add an exception path here for the
    missing/unreadable-specs/ case. Consequence for callers: collapsing
    "unreadable" into the same [] as "empty" means a caller cannot tell
    "no feature directories" apart from "the specs root is unreadable"
    from this return value alone -- a caller that needs that distinction
    must probe specs_root itself (e.g. its own os.access/os.listdir call)
    before calling this function, not after.

    Sort order (deliberate, not incidental Path/str comparison): every
    legacy-shape dir sorts before every new-shape dir; within the legacy
    family the order is by NNN (ascending); within the new-shape family
    the order is by (YYYY, MM, leaf directory name), lexicographic on each
    field. "Legacy first" is chosen because on any tree where both
    families are present, every legacy dir necessarily predates the new
    shape (no installation could have written specs/YYYY/MM/TICKET/ before
    Phase 3 ships), so the ordering matches temporal reality rather than
    an accident of how digits and letters compare. Non-directory entries
    are ignored at every level (a stray file directly under specs/, under
    a year directory, or under a month directory); symlinks are followed
    via Path.is_dir()'s default behaviour, so a valid dir-symlink is
    included and a dangling one is excluded like any other unreadable
    entry.
    """
    specs_root = Path(specs_root)
    try:
        if not specs_root.exists() or not specs_root.is_dir():
            return []
    except OSError:
        # e.g. EACCES walking an ancestor directory to stat specs_root --
        # treated the same as "specs/ does not exist" (see docstring).
        return []

    try:
        top_level = list(specs_root.iterdir())
    except OSError:
        # e.g. EACCES on specs_root itself (readable stat, unreadable
        # listing) -- same "contains nothing" treatment.
        return []

    entries = []  # type: List[Tuple[tuple, Path]]

    for entry in top_level:
        try:
            entry_is_dir = entry.is_dir()
        except OSError:
            continue
        if not entry_is_dir:
            continue

        legacy_match = SPEC_NUMBER_DIR_RE.match(entry.name)
        if legacy_match:
            entries.append(((0, int(legacy_match.group(1)), entry.name), entry))
        elif YEAR_DIR_RE.match(entry.name):
            # Phase-3 forward arm: specs/YYYY/MM/TICKET/.  Currently
            # matches nothing on any real install -- see the docstring.
            try:
                month_level = list(entry.iterdir())
            except OSError:
                continue
            for month_entry in month_level:
                try:
                    month_is_dir = month_entry.is_dir()
                except OSError:
                    continue
                if not month_is_dir or not MONTH_DIR_RE.match(month_entry.name):
                    continue
                try:
                    leaf_level = list(month_entry.iterdir())
                except OSError:
                    continue
                for leaf_entry in leaf_level:
                    try:
                        leaf_is_dir = leaf_entry.is_dir()
                    except OSError:
                        continue
                    if not leaf_is_dir:
                        continue
                    entries.append((
                        (1, entry.name, month_entry.name, leaf_entry.name),
                        leaf_entry,
                    ))

    entries.sort(key=lambda pair: pair[0])
    return [path for _, path in entries]


def find_feature_dirs_with(specs_root, filename):
    # type: (Union[str, "os.PathLike[str]"], str) -> List[Path]
    """Return iter_feature_dirs(specs_root) filtered to dirs holding filename.

    Takes the specs/ directory DIRECTLY, not a devforge_dir -- same
    signature change and same reasoning as iter_feature_dirs (see the
    module docstring's "specs_root, not devforge_dir" section).

    filename is a single sentinel basename (e.g. "spec.md",
    "breakdown-handoff.json", "research-handoff.json") -- not a glob, not
    a list. Several of the depth-1 consumers this accessor replaces want
    exactly one sentinel file's presence; a narrower single-filename
    signature is harder to misuse than a glob-accepting one.

    A feature dir containing a DIRECTORY named filename (not a file) does
    not match -- Path.is_file() is the test, not mere existence.  A
    symlink named filename that resolves to a regular file DOES match
    (Path.is_file()'s default symlink-following behaviour); a dangling
    symlink does not.

    Same empty-list-not-exception contract as iter_feature_dirs: a
    missing/unreadable specs_root (or a specs_root containing nothing
    matching either shape) returns [], never raises -- and a feature dir
    that itself becomes unreadable between iter_feature_dirs listing it
    and this function's own is_file() probe (any OSError, e.g. EACCES) is
    treated as "no match" rather than propagated. Sort order is inherited
    unchanged from iter_feature_dirs.
    """
    matches = []
    for feature_dir in iter_feature_dirs(specs_root):
        candidate = feature_dir / filename
        try:
            is_match = candidate.is_file()
        except OSError:
            is_match = False
        if is_match:
            matches.append(feature_dir)
    return matches


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
