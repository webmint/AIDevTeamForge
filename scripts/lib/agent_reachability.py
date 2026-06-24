"""agent_reachability.py — maintainer-side agent-executor-reachability checker.

Checks that every agent authored in ``src/agents/`` has at least one executor
somewhere in ``src/``, and that every agent named in an assignment row exists
in the roster.

Public API
----------
find_orphans(repo_root) -> dict
    Scan the live ``src/`` tree rooted at ``repo_root`` (a path-like or str).
    Returns::

        {
            "orphan_agents":        [str, ...],   # roster agents with NO executor
            "unknown_assignments":  [str, ...],   # names in assignment table not in roster
            "relay_only":           [str, ...],   # roster agents reachable ONLY via relay,
                                                  #   and NOT in RELAY_ONLY_ALLOWLIST
        }

    All three lists empty = all clear.

SCOPE STATEMENT (D5/D8)
-----------------------
This checker covers TWO mechanizable failure classes only:

  1. **Orphaned agent (type-1):** an authored agent with no executor path
     in ``src/``.
  2. **Unknown assignment:** an agent name in the ``/breakdown`` Agent
     Assignment table that is not in the roster (typo / removed agent).

It does NOT cover:
  - Type-2 forward-prose orphans ("verified at X" in spec prose).
  - Type-3 finding-inertness (an agent produces findings that gate nothing).

A passing check MUST NOT be read as proof that all orphans are closed.
Those two classes remain human review conventions (D8).

Stdlib only.  Targets Python 3.8+.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Allowlist for legitimately relay-only agents.
# An agent named here is allowed to appear ONLY in consult-relay lists
# with no other executor path.  Add entries with a comment explaining why
# the agent is legitimately relay-only by design.
# An empty frozenset is the default; add entries only when a specific,
# documented design decision requires relay-only reachability.
# ---------------------------------------------------------------------------

RELAY_ONLY_ALLOWLIST = frozenset()  # type: FrozenSet[str]


# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

# Regex matching a literal ``subagent_type: <name>`` in command markdown.
# Captures the agent name token (no angle brackets, no wildcards).
# The name must be a non-whitespace run that does NOT start with '<'.
_RE_SUBAGENT_TYPE = re.compile(
    r'subagent_type:\s*`?([A-Za-z0-9_-]+)`?'
)

# Regex matching a row in the Agent Assignment markdown table.
# The table looks like:
#   | Files in... | Agent |
#   |-------------|-------|
#   | some text   | agent-name |
#
# We want the SECOND column (Agent column), which may contain prose like
# "owning stack engineer (backend-engineer / frontend-engineer …)".
# We extract ALL tokens that look like agent-name slugs from the cell.
_RE_TABLE_ROW = re.compile(r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$')

# Regex to extract individual agent-name tokens from a prose cell.
# Agent names follow the pattern: <word>-<word>(-<word>)* in ASCII.
_RE_AGENT_TOKEN = re.compile(r'\b([a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)+)\b')

# Regex to extract backtick-quoted agent names from a prose cell.
# Used for prose cells where agent names are quoted: `agent-name`.
_RE_BACKTICK_AGENT = re.compile(r'`([a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)+)`')

# Regex to detect backtick-quoted agent names that are explicitly negated
# in a prose cell — e.g. "NOT `backend-engineer` by default".
# Such names are NOT assignment targets and must be excluded.
_RE_NEGATED_BACKTICK = re.compile(
    r'\bNOT\s+`([a-z][a-z0-9]*(?:-[a-z][a-z0-9]*)+)`'
)

# The header/separator rows of the markdown table — skip them.
_TABLE_HEADER_RE = re.compile(r'^\|[-:\s|]+\|$')

# Marker text for the breakdown Agent Assignment table header.
_ASSIGNMENT_TABLE_HEADER_RE = re.compile(
    r'\|\s*Files in\b', re.IGNORECASE
)

# Relay availability list markers (both files).
# These lines list agents that MAY be consulted via relay — NOT dispatched.
_RELAY_MARKER_RE = re.compile(
    r'(?:Any\s+(?:decomposition|planning)-relevant\s+specialist\s+may\s+be\s+named|'
    r'Any\s+(?:decomposition|planning)-relevant\s+specialist\s+may\s+be\s+used)',
    re.IGNORECASE,
)

# Path of the breakdown command relative to src/
_BREAKDOWN_MAIN = Path("commands") / "breakdown" / "main.md"
# Path of the plan command relative to src/
_PLAN_MAIN = Path("commands") / "plan" / "main.md"


# ---------------------------------------------------------------------------
# Helper: extract agent names from an AST node (list or dict literal)
# ---------------------------------------------------------------------------

def _extract_names_from_ast_node(node):
    # type: (ast.AST) -> List[str]
    """Extract string values from an AST List or Dict node.

    For a List: returns the string values of all constant elements.
    For a Dict: returns the string values of all constant KEYS.
    Returns empty list for any other node type or on any parse failure.
    """
    names = []  # type: List[str]
    if isinstance(node, ast.List):
        for elt in node.elts:
            # ast.Constant covers both Python 3.8+ and 3.12+ (ast.Str is
            # deprecated in 3.12 and removed in 3.14).
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                names.append(elt.value)
    elif isinstance(node, ast.Dict):
        for key in node.keys:
            if isinstance(key, ast.Constant) and isinstance(key.value, str):
                names.append(key.value)
    return names


def _extract_from_assignment(tree, target_name):
    # type: (ast.Module, str) -> List[str]
    """Walk an AST and return string elements from the named top-level assignment.

    Handles both list literals and dict literals (keys extracted for dicts).
    Covers BOTH plain assignment (``ast.Assign``) and annotated assignment
    (``ast.AnnAssign`` — e.g. ``_AUDIT_AGENTS: List[str] = [...]``), because
    the real ``_AUDIT_AGENTS`` in _audit/_preflight.py uses the annotated form.
    Returns empty list if the name is not found or the value is not a
    list/dict literal.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == target_name:
                    return _extract_names_from_ast_node(node.value)
        elif isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Name)
                and node.target.id == target_name
                and node.value is not None
            ):
                return _extract_names_from_ast_node(node.value)
    return []


# ---------------------------------------------------------------------------
# Collection: roster
# ---------------------------------------------------------------------------

def _collect_roster(src_root):
    # type: (Path) -> Set[str]
    """Return the set of agent file stems from src/agents/*.md."""
    agents_dir = src_root / "agents"
    return {p.stem for p in agents_dir.glob("*.md")}


# ---------------------------------------------------------------------------
# Collection: literal subagent_type dispatches
# ---------------------------------------------------------------------------

def _collect_subagent_type_dispatches(src_root):
    # type: (Path) -> Set[str]
    """Return agent names from literal 'subagent_type: <name>' in src/commands/**/*.md."""
    found = set()  # type: Set[str]
    commands_dir = src_root / "commands"
    for md_file in commands_dir.rglob("*.md"):
        text = md_file.read_text(encoding="utf-8", errors="replace")
        for m in _RE_SUBAGENT_TYPE.finditer(text):
            found.add(m.group(1))
    return found


# ---------------------------------------------------------------------------
# Collection: /breakdown Agent Assignment table
# ---------------------------------------------------------------------------

def _collect_breakdown_table_agents(src_root):
    # type: (Path) -> Tuple[Set[str], Set[str]]
    """Parse the /breakdown Agent Assignment table.

    Returns (dispatched_agents, table_agent_tokens):
      dispatched_agents: all roster-like names found in Agent column cells —
                         these are valid executor paths.
      table_agent_tokens: same set, used to detect unknown assignments.
    """
    breakdown_path = src_root / _BREAKDOWN_MAIN
    if not breakdown_path.is_file():
        return set(), set()

    text = breakdown_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    in_table = False
    past_header_sep = False
    dispatched = set()  # type: Set[str]

    for line in lines:
        # Detect table start: a row whose first column contains "Files in"
        if _ASSIGNMENT_TABLE_HEADER_RE.search(line):
            in_table = True
            past_header_sep = False
            continue

        if not in_table:
            continue

        # The separator line immediately after the header row
        if _TABLE_HEADER_RE.match(line.strip()):
            past_header_sep = True
            continue

        if not past_header_sep:
            continue

        # A data row
        m = _RE_TABLE_ROW.match(line.strip())
        if not m:
            # A blank line or non-table line ends the table
            if line.strip() == "" or not line.strip().startswith("|"):
                in_table = False
            continue

        agent_cell = m.group(2).strip()
        # Heuristic: if the agent cell contains ANY backtick-quoted slug
        # (even if all are negated), treat it as a PROSE cell — only the
        # non-negated, explicitly quoted names are dispatch targets.
        # Simple cells (bare agent names or slash-separated names without
        # any backticks at all) fall through to the slug regex.
        #
        # First collect all backtick-quoted slugs in this cell.
        all_backtick = [
            bm.group(1) for bm in _RE_BACKTICK_AGENT.finditer(agent_cell)
        ]
        if all_backtick:
            # Prose cell — filter out negated names (e.g. "NOT `backend-engineer`
            # by default" must not count as a backend-engineer dispatch).
            negated = {
                neg_m.group(1)
                for neg_m in _RE_NEGATED_BACKTICK.finditer(agent_cell)
            }
            for name in all_backtick:
                if name not in negated:
                    dispatched.add(name)
        else:
            # Simple cell: no backtick quoting → extract all slug-shaped tokens
            for token_match in _RE_AGENT_TOKEN.finditer(agent_cell):
                dispatched.add(token_match.group(1))

    return dispatched, dispatched.copy()


# ---------------------------------------------------------------------------
# Collection: relay availability lists
# ---------------------------------------------------------------------------

def _collect_relay_agents(src_root):
    # type: (Path) -> Set[str]
    """Return agent names that appear ONLY in consult-relay availability lists.

    Reads the single relay line from breakdown/main.md and plan/main.md.
    Returns the set of agent-slug tokens found on those lines.
    """
    relay_agents = set()  # type: Set[str]
    for rel_path in (_BREAKDOWN_MAIN, _PLAN_MAIN):
        path = src_root / rel_path
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if _RELAY_MARKER_RE.search(line):
                for m in _RE_AGENT_TOKEN.finditer(line):
                    relay_agents.add(m.group(1))
    return relay_agents


# ---------------------------------------------------------------------------
# Collection: helper ensemble / finder / refuter lists
# ---------------------------------------------------------------------------

def _collect_from_py_file(py_path, identifier):
    # type: (Path, str) -> Set[str]
    """Parse a Python file and extract string values from the named identifier.

    Handles both list literals (returns elements) and dict literals (returns
    keys).  Returns empty set on any parse failure or if the identifier is
    not found.
    """
    if not py_path.is_file():
        return set()
    try:
        source = py_path.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(py_path))
    except SyntaxError:
        return set()
    return set(_extract_from_assignment(tree, identifier))


def _collect_helper_dispatch_agents(src_root):
    # type: (Path) -> Set[str]
    """Return agents from all helper ensemble/finder/refuter list constants."""
    lib_root = src_root / "devforge" / "lib"

    # (file-path-relative-to-lib, identifier, shape-note)
    targets = [
        (
            Path("_audit") / "_preflight.py",
            "_AUDIT_AGENTS",            # flat list
        ),
        (
            Path("_review") / "_brief.py",
            "_FOCUS_BLOCKS",            # dict — keys are agent names
        ),
        (
            Path("_implement") / "_cmds_review_panel.py",
            "_REVIEWER_VOCAB",          # dict — keys are agent names
        ),
        (
            Path("_shared") / "_verify.py",
            "_REFUTER_PRIORITY",        # flat list
        ),
        (
            Path("_grill") / "_cli.py",
            "_GRILL_REFUTER_PRIORITY",  # flat list
        ),
    ]  # type: List[Tuple[Path, str]]

    found = set()  # type: Set[str]
    for rel_path, identifier in targets:
        full_path = lib_root / rel_path
        found.update(_collect_from_py_file(full_path, identifier))

    # Also capture the 'devils-advocate' dispatch from _grill/_cli.py
    # via the subagent_type scan in commands (already handled by
    # _collect_subagent_type_dispatches), but also cover the grill
    # _cli.py adversary dispatch (the string literal used in render-brief).
    grill_cli = lib_root / "_grill" / "_cli.py"
    if grill_cli.is_file():
        source = grill_cli.read_text(encoding="utf-8", errors="replace")
        # Find any string literal 'devils-advocate' in the file
        try:
            tree = ast.parse(source, filename=str(grill_cli))
            for node in ast.walk(tree):
                # ast.Constant covers Python 3.8+ (ast.Str deprecated 3.12,
                # removed 3.14); str literals appear as ast.Constant in 3.8+.
                if isinstance(node, ast.Constant) and node.value == "devils-advocate":
                    found.add("devils-advocate")
        except SyntaxError:
            pass

    return found


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def find_orphans(repo_root):
    # type: (object) -> Dict[str, List[str]]
    """Scan the live ``src/`` tree for agent-executor orphans and violations.

    Parameters
    ----------
    repo_root : path-like or str
        Root of the repository (the directory containing ``src/``).

    Returns
    -------
    dict with three keys, each a sorted list of strings:

    ``orphan_agents``
        Roster agents with zero executor path in any of the dispatch sources.
        A non-empty list is a FAIL.

    ``unknown_assignments``
        Agent names found in the ``/breakdown`` Agent Assignment table that
        are NOT in the roster (typo / retired agent).
        A non-empty list is a FAIL.

    ``relay_only``
        Roster agents reachable ONLY via a consult-relay availability list
        (``breakdown/main.md`` "may be named:" / ``plan/main.md`` "may be
        named:") and NOT via any other executor path, AND NOT in
        ``RELAY_ONLY_ALLOWLIST``.
        A non-empty list is a FAIL (OQ-4 hard-fail: relay is not an executor).

    All three lists empty = clean (all roster agents reachable, no unknown
    names, no relay-only violations).

    SCOPE (D5/D8): covers type-1 (orphaned agent) and unknown-assignment only.
    Does NOT cover type-2 forward-prose or type-3 finding-inertness.
    """
    repo_root = Path(repo_root)
    src_root = repo_root / "src"

    # 1. Roster
    roster = _collect_roster(src_root)

    # 2a. Literal subagent_type dispatches
    subagent_dispatches = _collect_subagent_type_dispatches(src_root)

    # 2b. /breakdown Agent Assignment table
    breakdown_dispatches, table_tokens = _collect_breakdown_table_agents(src_root)

    # 2c. Helper ensemble / finder / refuter lists
    helper_dispatches = _collect_helper_dispatch_agents(src_root)

    # Relay availability list agents (NOT executor paths)
    relay_agents = _collect_relay_agents(src_root)

    # Union of all real executor paths (relay is NOT an executor)
    real_executors = (
        subagent_dispatches | breakdown_dispatches | helper_dispatches
    )

    # -----------------------------------------------------------------------
    # Rule 4b: relay-only agents (computed first — used to build the orphan
    # exclusion set below).
    # Roster agent named in a relay list AND has no other real executor,
    # AND is not in the allowlist.
    # -----------------------------------------------------------------------
    relay_only = sorted(
        agent for agent in roster
        if (
            agent in relay_agents
            and agent not in real_executors
            and agent not in RELAY_ONLY_ALLOWLIST
        )
    )

    # Allowlisted relay-only agents are declared legitimately relay-only by
    # design — relay IS their declared executor.  They are exempt from both
    # relay_only (above) and orphan_agents (below).  Without this exemption
    # the allowlist is non-functional: the CLI would still exit non-zero,
    # defeating the OQ-4 escape valve.
    allowlisted_relay = {
        a for a in roster
        if a in relay_agents and a in RELAY_ONLY_ALLOWLIST
    }

    # -----------------------------------------------------------------------
    # Rule 3: orphaned agents — in roster but NOT in real executors,
    # and NOT in the allowlisted-relay set.
    # -----------------------------------------------------------------------
    orphan_agents = sorted(
        agent for agent in roster
        if agent not in real_executors and agent not in allowlisted_relay
    )

    # -----------------------------------------------------------------------
    # Rule 4a: unknown assignments — in breakdown table but NOT in roster
    # -----------------------------------------------------------------------
    # Filter: only consider tokens that look like roster agents (contain at
    # least one hyphen — plain English words like "owning", "stack", etc.
    # are not agent names).
    slug_shaped = {
        t for t in table_tokens
        if "-" in t  # agent names always contain at least one hyphen
    }
    unknown_assignments = sorted(
        token for token in slug_shaped
        if token not in roster
    )

    return {
        "orphan_agents": orphan_agents,
        "unknown_assignments": unknown_assignments,
        "relay_only": relay_only,
    }
