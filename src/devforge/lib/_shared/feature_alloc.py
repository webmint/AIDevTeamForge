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

Two directory layouts, coexisting forever (91-FEATURE-DIR-IDENTITY-AND-
PROVENANCE-PLAN.md D2/D3/D6)
-----------------------------------------------------------------------
Every allocate_feature_dir call from this point forward writes
specs/<YYYY>/<MM>/<leaf>/ -- two date levels (the allocation moment, UTC;
see allocate_feature_dir's own "Date source" paragraph), then an identity
leaf, never a slug-bearing composite and never NNN. `leaf` is the
normalized ticket when one was supplied, or the validated slug when it
was not -- REQUIRE_TICKET is opt-in and defaults false (Phase 2, OQ-1),
so a ticketless allocation must still succeed, and once the ticket IS the
directory name there is nothing else to fall back to; see
allocate_feature_dir's own docstring for the exact rule and the ratified
scope this falls outside of (D3 describes only the ticket-bearing leaf).

NNN is retired as an identity: nothing new is numbered, next_spec_number
is no longer called by this module, and SPEC_NUMBER_DIR_RE is now a
LEGACY-READ pattern only. Existing specs/NNN-slug/ directories are NOT
migrated (plan 68 D3's precedent) and remain resolvable forever --
iter_feature_dirs below reads both shapes in one pass, disjoint by
construction (a legacy name is exactly three digits then a dash; a year
name is exactly four bare digits with no dash). A future session must not
read "NNN" anywhere in this module as describing a NEW allocation; every
remaining NNN reference below is explicitly a legacy-read concern.

What lives here
----------------
FEATURE_NAME_RE        -- 2-4 word lowercase kebab-case slug validator.
                           Moved from _specify/_schema.py; re-exported there
                           under the same name so existing `from ._schema
                           import FEATURE_NAME_RE` imports are unaffected.
SPECS_ROOT_DEFAULT, SPEC_NUMBER_WIDTH, SPEC_NUMBER_DIR_RE
                        -- legacy NNN dir-naming constants.
                           SPEC_NUMBER_WIDTH and SPEC_NUMBER_DIR_RE now
                           serve LEGACY-READ consumers only
                           (SPEC_NUMBER_DIR_RE: iter_feature_dirs' legacy
                           arm below, and next_spec_number's own scan;
                           SPEC_NUMBER_WIDTH: only
                           _specify/_cmds_phase4_setters.py's
                           assign-spec-number, the specify-only
                           genuine-fallback path this module's own
                           allocate_feature_dir no longer feeds -- see
                           that function's docstring). SPECS_ROOT_DEFAULT
                           stays live for every caller, old shape or new.
YEAR_DIR_RE, MONTH_DIR_RE
                        -- the forward shape's own dir-naming constants: a
                           4-digit year, a 2-digit month. Both the READ
                           side (iter_feature_dirs) and the WRITE side
                           (allocate_feature_dir) key off strftime("%Y") /
                           strftime("%m"), which always produce exactly
                           this shape.
next_spec_number        -- pure filesystem scan: next NNN under specs/.
                           DEAD as of 91-FEATURE-DIR-IDENTITY-AND-
                           PROVENANCE-PLAN.md Phase 3 (D6): no longer
                           called by allocate_feature_dir. Retained,
                           unmodified, for its one remaining production
                           caller (_specify/_cmds_phase4_setters.py's
                           assign-spec-number -- the specify-only
                           genuine-fallback path this plan takes no
                           decision on) and for its own direct test
                           coverage.
decide_branch_action    -- pure decision: what to print / do for branch
                           creation, given (current, default, ticket,
                           slug).  Three named arms (see its docstring);
                           /specify's cmd_create_branch delegates to this
                           for its two reachable arms.  Branch name is
                           spec/<ticket> when a ticket is given, else
                           spec/<slug> (91-FEATURE-DIR-IDENTITY-AND-
                           PROVENANCE-PLAN.md D5, plus the same
                           ticket-or-slug fallback allocate_feature_dir
                           uses for the directory leaf).
allocate_feature_dir    -- creates specs/<YYYY>/<MM>/<leaf>/ on disk
                           (FRESH allocation only -- see "Attach mode"
                           below).
specs_root_for          -- explicit devforge_dir -> specs_root derivation
                           (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-
                           PLAN.md Phase 1, revised).  A small pure-path
                           helper, not a scan: it makes the devforge_dir
                           -> repo_root -> specs_root arithmetic visible
                           at the call site instead of hidden inside a
                           scan function.
iter_feature_dirs       -- every feature directory under a GIVEN specs
                           root, across both the legacy NNN-slug/ shape
                           and the Phase-3 YYYY/MM/<leaf>/ shape (91-
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
classify_feature_dir_identity
                        -- given a RESOLVED feature directory (not a
                           specs_root -- a single directory, e.g. what
                           _specify/_cmds_handoff.py's import-handoff
                           already has as handoff_path.parent), returns
                           whatever legacy NNN-slug identity it carries:
                           {"spec_number": Optional[str], "feature_slug":
                           Optional[str]}.  Closes 91-FEATURE-DIR-IDENTITY-
                           AND-PROVENANCE-PLAN.md Phase 3's own "depth-
                           branch problem" ⚠ for the SEEDING half only --
                           see the function's own docstring for the full
                           three-shape argument and for what it deliberately
                           does NOT fix (specify/main.md Step 4.1's
                           warm/cold/fallback routing, which is prose, not
                           seeding).
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

Attach mode (plan 68's D6) is out of scope here -- read this before wiring
a caller -- NOTE this is a DIFFERENT D6 than the one this module's own
opening section discusses (this module's "Two directory layouts" section
above and the "Slug collisions" section below both cite 91-FEATURE-DIR-
IDENTITY-AND-PROVENANCE-PLAN.md's D6, the NNN-retirement decision; this
section cites plan 68's D6, the grill-re-entry attach-mode decision --
same label, two different plans, do not conflate them)
------------------------------------------------------------------------
allocate_feature_dir is a FRESH-ALLOCATION-ONLY function.  Plan 68 D6
(repeat intake on the same feature via a /grill RE-ENTER-UPSTREAM seed)
needs the OPPOSITE behavior: skip allocation and branch creation entirely,
because the seed's own location (grill-seed.json, inside the existing
feature directory -- whichever shape it was allocated under, legacy
specs/NNN-slug/ or the specs/<YYYY>/<MM>/<leaf>/ shape D2/D3 introduce)
already identifies the existing feature dir.  This module deliberately does NOT
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
that target happens to be exactly the leaf a fresh allocation would compute
next (a race between two concurrent invocations, or a manual retry after a
partial failure).  It fails loudly with a clear error string; the caller
writes that to stderr and exits non-zero.  There is no silent-reuse path.
This holds identically whether the leaf collision is on a ticket (two
allocations naming the same ticket in the same YYYY/MM bucket) or on a
slug (two ticketless allocations naming the same slug in the same bucket
-- see "leaf" below).

Slug collisions (OQ-4 of plan 68, extended by 91-FEATURE-DIR-IDENTITY-AND-
PROVENANCE-PLAN.md's ticket-or-slug leaf)
---------------------------------------------------------------------------
When a ticket is supplied, allocate_feature_dir does NOT check whether the
slug is already used by another ticket -- plan 68's OQ-4 ratified this: the
ticket is the identity, the slug is a label, and two features may
legitimately want the same slug (they land at two different tickets, so no
collision is possible; historically, at two different NNNs, for a legacy
allocation). See the module's test file for the round-trip proof.

When NO ticket is supplied (REQUIRE_TICKET is opt-in and defaults false --
see allocate_feature_dir's own docstring), the slug itself becomes the
leaf, so two ticketless allocations that land in the SAME YYYY/MM bucket
with the SAME slug DO collide, loudly, per "Never overwrite" above -- this
is a real, disclosed narrowing of OQ-4's original guarantee, scoped to the
ticketless path only. It is not a decision this plan's D2/D3/D6 text
states outright (they describe only the ticket-bearing leaf); it is the
narrowest reading that keeps a ticketless allocation working (Phase 2's
own shipped, tested contract) without inventing a second, un-ratified
identity scheme.  See the module's test file for both the same-ticket and
the same-slug collision cases.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


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
# sits in, instead of leaving them for a fresh NNN scan. As of Phase 3,
# import-handoff reaches this regex indirectly, via
# classify_feature_dir_identity below (which also covers the two new-shape
# cases that regex alone cannot) -- this regex itself is unchanged.
#
# Deliberately kept at EXACTLY 3 digits (not widened to \d{3,}) -- a
# widened digit count would flip next_spec_number's existing "4+-digit
# dirs are not recognized as spec dirs" contract (pinned by
# tests/lib/_shared/test_feature_alloc.py::test_non_nnn_dirs_ignored,
# which asserts a "9999-too-many-digits" dir is ignored), silently
# growing that scanner's matching surface as an unintended side effect of
# this unrelated change. Every existing group(1)-only consumer
# (next_spec_number / _cmds_phase4_setters._existing_spec_numbers) is
# therefore match/non-match-identical to before this edit; only the added
# group(2) + the `$` end-anchor (harmless -- real dir basenames never
# have trailing content past the slug) are new.
#
# 91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 3 (D6): as of this
# plan, allocate_feature_dir below is NO LONGER a consumer of this pattern
# (directly or via next_spec_number) -- it is LEGACY-READ ONLY now,
# matched by iter_feature_dirs' legacy arm and by next_spec_number's own
# scan (next_spec_number itself is dead code from allocate_feature_dir's
# point of view; see the module docstring).
SPEC_NUMBER_DIR_RE = re.compile(r"^(\d{3})-(.+)$")

# Phase-3 forward structure (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-
# PLAN.md D2): specs/<YYYY>/<MM>/<leaf>/, the layout allocate_feature_dir
# below now writes unconditionally for every fresh allocation (Phase 3).
# Defined here (from Phase 1, before any writer produced this shape) so
# iter_feature_dirs below could read it before allocate_feature_dir wrote
# it -- see that function's docstring and Phase 1's ⚠ instruction to build
# the variable-depth branch from the start, not as a later rewrite.
#
# No ambiguity with SPEC_NUMBER_DIR_RE above: a legacy dir name is exactly
# three digits followed by a dash (the dash is required); a year dir name
# is exactly four bare digits with no dash at all.  A name matching neither
# (e.g. "9999-too-many-digits") is claimed by neither pattern.
YEAR_DIR_RE = re.compile(r"^\d{4}$")
MONTH_DIR_RE = re.compile(r"^\d{2}$")

# The branch-name prefix every spec branch carries: spec/<ticket> when a
# ticket is given, else spec/<slug> (91-FEATURE-DIR-IDENTITY-AND-
# PROVENANCE-PLAN.md D5); historically spec/NNN-slug for a legacy
# allocation's own branch (decide_branch_action no longer composes that
# form for a NEW branch, but an existing one is not renamed).
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

    DEAD as of 91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 3 (D6)
    from allocate_feature_dir's point of view: allocate_feature_dir below
    no longer calls this function -- a fresh allocation is keyed on the
    ticket-or-slug leaf, never on NNN. This function's body is otherwise
    UNCHANGED and it is retained, unmodified, for its one remaining
    production caller (_specify/_cmds_phase4_setters.py's
    assign-spec-number, the specify-only genuine-fallback path this plan
    takes no decision on) and for its own direct test coverage.
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


def allocate_feature_dir(devforge_dir, slug, ticket=None, require_ticket=False, now=None):
    # type: (Union[str, "os.PathLike[str]"], str, Optional[str], bool, Optional[datetime]) -> Tuple[dict, Optional[str]]
    """Allocate a fresh specs/<YYYY>/<MM>/<leaf>/ directory.

    FRESH ALLOCATION ONLY -- see the module docstring's "Attach mode"
    section before wiring a plan-68-D6 attach-mode caller into this
    function.

    Validates slug (2-4 word lowercase kebab-case, the same shape
    specify_helper assign-feature-name enforces via FEATURE_NAME_RE), then
    creates repo_root/specs/<YYYY>/<MM>/<leaf>/.  repo_root is the parent
    of devforge_dir (== the install root in wrapper mode -- see module
    docstring).  `parents=True` on the mkdir below means the year and
    month directories are created as needed and are NOT themselves
    exist_ok-gated -- only the leaf is; see "Never overwrite" in the
    module docstring.

    Date source (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md OQ-3):
    YYYY/MM come from `now` (an injectable datetime, for deterministic
    testing -- mirrors this codebase's existing "inject the timestamp,
    don't mock the clock" convention, e.g.
    _implement/_cmds_complete.py's mark-complete --completed-at), UTC when
    not supplied (datetime.now(timezone.utc)).  UTC, NOT local time: OQ-3's
    own text reads "local date, as set-date already enforces YYYY-MM-DD
    elsewhere", but that claim does not survive a check against the actual
    code. specify_helper's cmd_set_date (_cmds_phase4_setters.py) has NO
    clock logic at all -- it only validates a caller-supplied string
    against `^\\d{4}-\\d{2}-\\d{2}$` -- so "set-date already enforces" is
    true of the FORMAT only, never of a timezone. The value that actually
    reaches --date is composed by src/commands/specify/main.md's own
    prose via `date -u +%Y-%m-%d` -- UTC, the opposite of what OQ-3
    claims. Every other "now" timestamp in this codebase
    (_implement/_cmds_complete.py, _implement/_cmds_session.py,
    _research/_handoff_build.py, _discover/_handoff_build.py,
    _generate_docs/_glossary.py, cbm_sync_helper.py, _pr_review/_output.py,
    among others) also uses datetime.now(timezone.utc). UTC is therefore
    both the actually-dominant convention and the one immune to a
    server/operator timezone changing which YYYY/MM bucket "today"
    resolves to. OQ-3's parenthetical is corrected here rather than
    followed -- do not cite it as evidence for local time.

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
    require_ticket is True.

    Ticket-or-slug leaf (Phase 3's item this plan's own text left open --
    see the module's "Slug collisions" section for the full argument):
    D2/D3 ratified the ticket AS the directory leaf, with no fallback
    named for a ticket-LESS allocation -- yet OQ-1 ratified
    REQUIRE_TICKET defaulting to false, and Phase 2 shipped (and tests)
    a ticketless allocation succeeding. Those two facts do not close on
    their own. The rule this function applies: `leaf` is the normalized
    ticket when one was supplied and valid, else the validated slug.
    This is the narrowest resolution available -- it invents no new
    identity scheme (no synthetic "LOCAL-1"-shaped placeholder ticket,
    which would fabricate an identity nobody typed and contradict this
    plan's own D9 "a fake value is worse than no value" principle stated
    elsewhere for a different field), reuses input this function already
    validates for an unrelated reason (FEATURE_NAME_RE), and keeps
    REQUIRE_TICKET's ratified "opt-in, imposes nothing when off"
    semantics intact: a ticketless allocation with require_ticket=False
    still succeeds with ZERO extra input demanded of the operator. The
    cost, stated once here and in the module docstring: two ticketless
    allocations with the SAME slug in the SAME YYYY/MM bucket now collide
    (loudly -- see "Never overwrite"), narrowing plan 68 OQ-4's original
    "same slug, different identity, no collision" guarantee for that one
    path. This reading is NOT literally written in D2/D3's ratified text
    (which describes only the ticket-bearing leaf) and is flagged here as
    a candidate for explicit ratification, not asserted as settled.
    decide_branch_action below applies the identical ticket-or-slug rule
    to the branch name (D5 names only the ticket-given case too).

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
                                  .parent), e.g. "specs/2026/08/PROJ-123".
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
        slug             str  -- the validated slug (echoed back, stripped)
        ticket           str | None -- the normalized ticket (canonical
                                  uppercase, per normalize_ticket) when
                                  one was supplied and valid; None when
                                  none was supplied (only possible when
                                  require_ticket is False).
        year             str  -- the YYYY bucket actually used (4 digits).
        month            str  -- the MM bucket actually used (2 digits).
        leaf             str  -- the directory's final path segment: equal
                                  to `ticket` when one was given, else
                                  equal to `slug` (see the ticket-or-slug
                                  paragraph above).
        created          bool -- always True on success
      NOTE: `number`, `formatted_number` and `dirname` -- present on the
      pre-Phase-3 result dict for the legacy specs/NNN-<slug>/ shape --
      are ABSENT here. There is no NNN for a fresh allocation to report
      (next_spec_number is no longer called; see the module docstring),
      and emitting them as None/empty would be a dead field pretending to
      still mean something. A caller reading this dict must not assume
      those keys exist.
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
          reused, including on a race between two concurrent calls)
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
    moment = now if now is not None else datetime.now(timezone.utc)
    year = moment.strftime("%Y")
    month = moment.strftime("%m")
    leaf = norm_ticket if norm_ticket else cleaned_slug
    target = specs_root / year / month / leaf

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
        "slug": cleaned_slug,
        "ticket": norm_ticket,
        "year": year,
        "month": month,
        "leaf": leaf,
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
# classify_feature_dir_identity (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-
# PLAN.md Phase 3's "depth-branch problem" -- see the function's own
# docstring for the full argument).
# ---------------------------------------------------------------------------


def classify_feature_dir_identity(feature_dir):
    # type: (Union[str, "os.PathLike[str]"]) -> Dict[str, Optional[str]]
    """Classify a RESOLVED feature directory's own legacy NNN-slug identity.

    91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md Phase 3's own ⚠ names
    this "the depth-branch problem": _specify/_cmds_handoff.py's
    import-handoff seeds state["spec_number"] / state["feature_slug"] by
    matching SPEC_NUMBER_DIR_RE against the handoff's containing directory
    name alone -- a test that only ever recognized the legacy
    specs/NNN-slug/ shape. Under the Phase-3 layout
    (specs/<YYYY>/<MM>/<leaf>/) that match always fails, so a fresh
    install silently stopped seeding either field for every new-shape
    intake. This function closes that gap. It is extracted here (not left
    inline at the call site) because directory-shape knowledge --
    SPEC_NUMBER_DIR_RE, FEATURE_NAME_RE, YEAR_DIR_RE, MONTH_DIR_RE -- all
    already lives in this module and nowhere else; duplicating even one of
    those four regexes at the call site would create a second place a
    future layout change has to remember to edit.

    Takes the feature directory itself (e.g. handoff_path.parent), not a
    specs_root -- this is a single-directory classification, not a scan.

    Returns {"spec_number": Optional[str], "feature_slug": Optional[str]}.
    Never fabricates a value -- an unrecoverable field is None, never a
    placeholder (this plan's own D9, "a fake value is worse than no
    value", stated there for a different field but the same principle
    applies here):

    - Legacy shape (feature_dir's OWN basename matches SPEC_NUMBER_DIR_RE,
      e.g. "003-auth-token-refresh"): spec_number = "003", feature_slug =
      "auth-token-refresh" -- BYTE-IDENTICAL to the pre-Phase-3 behaviour
      every existing caller depends on. Checked first and unconditionally:
      a legacy name can never also satisfy the new-shape ancestry check
      below (a legacy match requires a literal "-" at index 3, which a
      bare 2-digit MONTH or 4-digit YEAR ancestor never has), so there is
      no ordering hazard between the two branches.
    - New shape, ticketless leaf: feature_dir's PARENT matches
      MONTH_DIR_RE and its GRANDPARENT matches YEAR_DIR_RE (the exact
      ancestry iter_feature_dirs already requires to admit a directory as
      new-shape -- reused here, not reinvented) AND feature_dir's own
      basename matches FEATURE_NAME_RE: feature_slug = that basename
      verbatim (a REAL value -- allocate_feature_dir only ever writes a
      FEATURE_NAME_RE-shaped ticketless leaf, so this is read-back, not a
      guess), spec_number = None (there never was an NNN for this
      directory; synthesising one would manufacture an identity nobody
      assigned).
    - New shape, ticketed leaf (e.g. "PROJ-123"): the same ancestry check
      passes, but the basename is a ticket, not a slug, so it FAILS
      FEATURE_NAME_RE (a ticket's first character is always uppercase;
      FEATURE_NAME_RE's first-character class is `[a-z]` -- the two
      patterns are structurally disjoint, so no separate ticket regex is
      needed here to tell them apart). Both fields stay None: there is no
      NNN, and writing the ticket into feature_slug would inject a value
      that fails the very pattern every other feature_slug consumer
      assumes (specify_helper's own assign-feature-name validates against
      exactly FEATURE_NAME_RE). Recovering neither field is not a
      limitation of this function -- it is the correct answer for a
      directory whose only identity is a ticket.
    - Anything else (a hand-made or pre-migration directory whose basename
      matches neither shape, e.g. a handoff imported from an arbitrary
      path outside the specs/ tree): both fields stay None, exactly as
      before this function existed. The ancestry check is what keeps this
      case honest -- a directory that merely HAS a FEATURE_NAME_RE-shaped
      basename but is not actually sitting under a real YYYY/MM pair (an
      arbitrary tempdir in a test, for instance) does not get
      feature_slug seeded either.

    What this function does NOT do: it does not fix
    src/commands/specify/main.md's Step 4.1 warm/cold/fallback routing,
    which independently re-parses the resolved directory's basename text
    and requires the exact legacy <NNN>-<slug> shape for its own warm and
    cold paths. A new-shape directory -- ticketed or ticketless -- still
    falls through to Step 4.1's genuine-fallback arm today, which
    allocates an UNRELATED fresh legacy-shaped directory rather than
    reusing this one. That routing gap is prose, not seeding, and is
    unchanged by this function -- closing it needs a fourth Step 4.1 path,
    which is a command-spec edit this function does not make.
    """
    feature_dir = Path(feature_dir)
    leaf = feature_dir.name

    legacy_match = SPEC_NUMBER_DIR_RE.match(leaf)
    if legacy_match:
        return {
            "spec_number": legacy_match.group(1),
            "feature_slug": legacy_match.group(2),
        }

    month_name = feature_dir.parent.name
    year_name = feature_dir.parent.parent.name
    is_new_shape = bool(MONTH_DIR_RE.match(month_name) and YEAR_DIR_RE.match(year_name))
    if is_new_shape and FEATURE_NAME_RE.match(leaf):
        return {"spec_number": None, "feature_slug": leaf}

    return {"spec_number": None, "feature_slug": None}


# ---------------------------------------------------------------------------
# decide_branch_action (extracted from
# _specify/_cmds_phase4_setters.py::cmd_create_branch).
# ---------------------------------------------------------------------------


def decide_branch_action(current_branch, default_branch, ticket, slug):
    # type: (str, str, Optional[str], Optional[str]) -> Tuple[str, str, Optional[str]]
    """Decide the branch-creation action for a feature branch.

    Pure function -- no filesystem or git access; the caller runs the
    returned git command (or does nothing, on a "keep" decision).

    91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md D5: the branch name is
    spec/<ticket> when a ticket is given (e.g. "spec/PROJ-123"), never
    spec/NNN-slug for a NEW branch. D5's own text names only the
    ticket-given case; it is silent on what a ticketless branch (legal --
    REQUIRE_TICKET defaults false) should be named. This function applies
    the SAME ticket-or-slug fallback allocate_feature_dir uses for the
    directory leaf, for the same reason (see that function's docstring):
    when no ticket is given, the branch is spec/<slug> instead, so a
    ticketless run still gets a real feature branch with zero extra input
    demanded of the operator. Existing spec/NNN-slug branches (from a
    legacy allocation) are unaffected -- this function only decides the
    name for a BRAND-NEW branch; it never renames one that already exists.

    Three arms:
      1. current_branch == default_branch
         -> decision "create".  Requires ticket or slug (at least one
            truthy, ticket taking priority when both are given -- see
            above); if NEITHER is supplied, returns decision="create" with
            a non-None error and an empty line -- the caller must not
            treat that as success.  On success, line is the checkout
            command "git checkout -b spec/<ticket>" or
            "git checkout -b spec/<slug>" (no trailing newline -- the
            caller appends one).
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
                  be "create" but neither ticket nor slug was supplied.
    """
    current = (current_branch or "").strip()
    default = (default_branch or "").strip()

    if current == default:
        cleaned_ticket = (ticket or "").strip()
        cleaned_slug = (slug or "").strip()
        identity = cleaned_ticket or cleaned_slug
        if not identity:
            return (
                "create",
                "",
                "a ticket or a slug is required to create a branch "
                "when on the default branch",
            )
        branch = "{0}{1}".format(_SPEC_BRANCH_PREFIX, identity)
        return "create", "git checkout -b {0}".format(branch), None

    skip_line = "# already on non-default branch {0!r}; no checkout emitted".format(
        current
    )
    if current.startswith(_SPEC_BRANCH_PREFIX):
        return "keep-spec", skip_line, None
    return "keep-other", skip_line, None
