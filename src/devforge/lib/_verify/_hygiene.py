"""_hygiene.py — scope-creep + leftover-artifact flags for /verify.

Public surface
--------------
  check_hygiene(changed_files, scope_baseline, source_root, install_root=None) -> dict
      Flag (a) scope-creep — files in ``changed_files`` but not in the
      declared scope baseline — and (b) leftover artifacts across the changed
      files: debug prints, bare TODOs/FIXMEs, obvious commented-out blocks,
      and (wrapper mode only) framework-artifact mentions leaking into the
      client-owned source repo.

      Parameters
      ----------
      changed_files : list[str]
          File paths that changed during implementation (relative or absolute;
          relative paths are resolved against ``source_root``, or against
          ``install_root`` in wrapper mode — see "Wrapper path resolution"
          below).  Typically the ``files_for_finders`` array from
          ``resolve-feature-scope``.
      scope_baseline : list[str] or None
          The declared planned file set — the union of ``touched_files`` across
          all tasks in ``breakdown-handoff.json``.  Pass ``None`` or ``[]`` to
          skip scope-creep checking (only leftover artifacts are reported).
      source_root : str
          Absolute path to the source tree.  Changed files are read from
          here.
      install_root : str or None
          Absolute path to the forge install root (where ``.devforge/``
          lives).  ``None`` (the default) means standalone — every existing
          behavior is byte-identical to the pre-``install_root`` contract.
          Wrapper mode is detected when ``install_root`` is truthy AND
          ``os.path.realpath(install_root) != os.path.realpath(source_root)``
          — the same predicate ``_shared/feature_scope.py``'s
          ``_prefix_paths`` uses.  Wrapper mode enables the ``framework_mention``
          kind (see below) and the install-root-prefixed path resolution fix
          (see "Wrapper path resolution" below).

      Returns
      -------
      dict with:
        "scope_creep" : list[str]
            Files in ``changed_files`` not found in ``scope_baseline`` (after
            normalisation).  Empty list when scope-creep check is skipped.
            Non-code files (prose artifacts, forge-managed dirs) are never
            reported as scope-creep regardless of baseline contents.
        "leftover_artifacts" : list[dict]
            One dict per flagged line:
              "file"    : str  — path as given in ``changed_files``
              "line"    : int  — 1-based line number
              "kind"    : str  — one of "debug_print" | "debug_statement" |
                                 "bare_todo" | "bare_fixme" |
                                 "commented_code_block" | "framework_mention"
                                 ("framework_mention" only ever appears in
                                 wrapper mode — see below).
              "snippet" : str  — the flagged line, stripped
        "scope_creep_checked" : bool
            True when a scope baseline was supplied and the check ran.
        "files_checked" : int
            Number of changed files that were successfully read and scanned
            for artifacts.  Non-code files are not counted here.
        "files_unreadable" : list[str]
            Files that could not be read (missing, binary, permission error).
        "files_skipped" : int
            Number of changed files that were skipped by the file-type gate
            (non-code prose/data files).  Additive and back-compatible key.

File-type gate (_is_code_file)
--------------------------------
The artifact scanner and scope-creep check operate only on source-code files.
Pipeline prose artifacts (specs/, docs/, design/, audits/, research/, etc.)
and data/lock files (.json, .yaml, .lock, etc.) are excluded via a DENYLIST
approach — we exclude KNOWN prose/data, rather than allowlisting code languages.
Reason: this codebase targets polyglot consumers; hardcoding code-file extensions
would be language-specific and would break on new stacks.  False negatives (a
prose file slips through) are preferable to false positives (a legitimate source
file in an unlisted language gets skipped).

Design notes — conservative posture
-------------------------------------
The hygiene check PREFERS false negatives over false positives; trust is
eroded faster by spurious flags than by occasional misses.

Scope-creep
~~~~~~~~~~~
Comparison is done on normalised paths (both sides stripped) after stripping
leading "./" from relative paths.  If either ``changed_files`` or
``scope_baseline`` uses absolute paths, they are made relative to
``source_root`` before comparison.  Comparison is CASE-SENSITIVE — lowercasing
was removed because it produces false negatives on case-sensitive filesystems
(e.g. Linux, where ``src/Components/MyButton.tsx`` and
``src/components/mybutton.tsx`` are distinct files).

Leftover-artifact patterns (conservative)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1. ``debug_print``:
   - ``console.log(`` — JS/TS/Vue debug log.
   - ``print(`` — Python debug print.  Matched with a negative lookbehind
     ``(?<![.\\w])`` so that method calls like ``self.print(``, ``rich.print(``,
     and ``obj.print(`` are NOT flagged — only bare ``print(`` and ``(print(``
     (or other non-identifier, non-dot prefixes) trigger the rule.
     False-positive risk: legitimate bare ``print()`` in scripts/CLIs.  We flag
     it anyway because the caller reviews the snippet.  The kind makes it clear.
   - ``console.error(`` / ``console.warn(`` are NOT flagged — those are often
     legitimate error-boundary logging.
   NOTE: ``print(`` is matched on any matching line, including inside string
   literals or docstrings — the scanner does not track open-quote state.  The
   caller reviews the snippet to confirm intent.

2. ``debug_statement``:
   - ``debugger`` on its own line (JavaScript ``debugger;`` statement).
     Matched as a whole-line token to avoid false positives in comments/strings.
   - ``pdb.set_trace()`` — Python interactive debugger.
   - ``breakpoint()`` — Python 3.7+ built-in breakpoint.  Flagged only when
     it appears as a standalone call (not as a method or in a comment).

3. ``bare_todo`` / ``bare_fixme``:
   - ``TODO`` or ``FIXME`` (case-insensitive) on a line that does NOT contain
     a ticket/issue reference.  A ticket reference is anything matching
     ``#NNN`` (hash + digits), ``PROJ-NNN`` (JIRA-style), or a URL (``http``).
     ``TODO(name):`` with no ticket is still flagged.
     This is intentionally strict — a bare "TODO: do X" without a reference is
     a leftover.

4. ``commented_code_block``:
   A line is flagged ONLY when it is a comment-only line (``#`` or ``//``
   prefix after stripping) AND the de-commented body triggers one of four
   conservative rules:

   Rule A — assignment-call: body contains ``<ident> = <something>(`` (the
   ``=`` + ``(`` together are a reliable code signal, e.g. "const x = getConfig();").

   Rule B — bare call ending ``;``: body ends with ``;`` AND contains ``(``
   (catches "// oldFunc();" and "// doSomething(a, b);" without a keyword).

   Rule C — structure + terminator (dual signal):
     (a) Body starts with a narrow code-structure pattern:
           ``def ``  ``async def ``  ``function ``  ``async function ``
           ``if (``  ``for (``  ``while (``  ``foreach (``  ``module.exports``
         Bare tokens ``return ``, ``from ``, ``import ``, ``class ``, ``const ``,
         ``let ``, ``var ``, ``export `` are EXCLUDED — all common in English prose.
     (b) Body ends with one of: ``:``  ``{``  ``}``  ``)``  ``;``

   Rule D — call-expression ending ``)``: body ends with ``)`` AND contains an
   ident-call pattern ``<ident>(`` (catches "// return compute(x)" and
   "// fetchData(url)" but NOT parenthetical prose like "// the result (lazy)").

   Multi-line blocks are not tracked — each qualifying line is flagged
   independently.  The multi-rule requirement prevents prose comments like
   "// from the spec", "// return type is X", or "// class is immutable" from
   firing.

5. ``framework_mention`` (wrapper mode ONLY, ADVISORY — plan 97 Phase 1 item 1):
   In wrapper mode nothing written into the client-owned source repo may name
   a framework artifact — comment, docstring, string literal, identifier, or
   test name all count; the scanner tracks no quote state, so a mention
   inside a string literal is flagged exactly like one in a comment.  This
   kind is emitted ONLY when ``install_root`` puts ``check_hygiene`` in
   wrapper mode (see the ``install_root`` parameter doc above); a standalone
   run (``install_root=None`` or equal to ``source_root``) never produces it
   — behavior there is byte-identical to before this kind existed.

   The check is a ratified TOKEN list, never a stem match — "spec", "plan",
   "task", "feature", and "forge" are deliberately NOT tokens (they are
   ordinary English words far too common in legitimate source).  Every token
   below is fixed; regexes may be refined for correctness but no token may be
   added or removed without a fresh ratification.  ``intake-rerun`` was added
   by a fresh ratification: 109-REENTRY-CHAIN-CONTINUITY-PLAN.md, Phase 0
   close, OQ-2 (2026-10-03).

   Filename/path tokens are CASE-SENSITIVE (a real path segment has one true
   case): ``spec.md``, ``plan.md``, ``specs/``, ``tasks/README.md``,
   ``constitution.md``, ``CLAUDE.md``, ``.devforge``, ``.claude/``,
   ``breakdown-handoff``, ``research-handoff``, ``discover-handoff``,
   ``plan-handoff``, ``grill.md``, ``verification.md``, ``review.md``,
   ``summary.md``, ``fix-seed``, ``grill-seed``, ``intake-rerun``.
   Each is wrapped with a negative lookbehind ``(?<![\\w-])`` so a token
   embedded inside a longer identifier or filename does not fire
   (``myspecs/`` does NOT match ``specs/``; ``my-spec.md`` does NOT match
   ``spec.md``); tokens NOT ending in ``/`` additionally get a trailing
   negative lookahead ``(?![\\w-])`` so ``specfile.md`` does not match
   ``spec.md``.  Tokens ending in ``/`` get NO trailing lookahead —
   ``specs/2026/…`` must match, and the character after the ``/`` is
   legitimately a word character.  ``.devforge`` still matches ``.devforge/``
   under the trailing lookahead because ``/`` is not ``[\\w-]``.

   Vocabulary tokens are word-bounded and case-INSENSITIVE, with two named
   exceptions kept case-sensitive because a case-insensitive match would
   erase a real discriminator (an all-caps acronym / a capitalized task
   label): ``\\bdevforge\\b`` (i, refined — see below), ``(?<![\\w-])/devforge:``
   (i), ``\\bTask \\d{3}\\b`` (case-sensitive), ``\\bAC-\\d+\\b``
   (case-sensitive), ``\\bacceptance criteri`` (i — matches both "criteria"
   and "criterion"), ``\\bspec criteria\\b`` (i), ``\\bDone When\\b`` (i),
   ``\\bconstitution\\b`` (i).

   Refinement recorded: the ratified ``\\bdevforge\\b`` vocabulary token, taken
   literally, also fires inside a bare filename like ``cfg.devforge`` — ``.``
   is a non-word character, so plain ``\\b`` sees a boundary right after it.
   That would contradict the ratified false-negative for ``cfg.devforge``.
   The regex is refined (token list unchanged) to
   ``(?<![\\w.-])devforge(?![\\w-])`` — the lookbehind additionally excludes a
   leading ``.`` so a dotted filename does not trigger the bare-word
   vocabulary token, while a standalone mention ("the devforge framework",
   "DevForge") still fires normally.

   Combining case-sensitive and case-insensitive alternatives in one
   pre-compiled pattern uses Python's scoped inline flag group ``(?i:...)``
   per case-insensitive alternative (supported since Python 3.6) rather than
   a module-level ``re.IGNORECASE`` flag, since that flag would also
   silence the two case-sensitive exceptions.

   At most ONE ``framework_mention`` finding is emitted per line even when
   several tokens match that line — the finding says "this line needs a
   look", not "here is every token".  The check is INDEPENDENT of the
   existing-kind chain above: a line can carry both an existing-kind finding
   (e.g. ``debug_print``) and a ``framework_mention`` finding, and when it
   does the existing-kind finding is ordered first in ``leftover_artifacts``.

   Four false-positive classes are RECORDED, not excluded — the posture is
   the same as the rest of this module (prefer a documented false positive
   the caller can dismiss on sight over a silent miss):
     - ``AC-3`` as an audio codec or HVAC label (e.g. "// AC-3 audio track").
     - ``Task 001`` as fixture data inside a task-management app (e.g. a
       literal ``"Task 001"`` string in a test fixture).
     - ``specs/`` as a project's own test-fixtures directory name (e.g.
       ``"specs/fixtures/"``).
     - "constitution" inside a legal-domain application (e.g. "the
       constitution of the client").
   A test name such as ``it('AC-3 paginates')`` and a string literal such as
   ``"specs/"`` match by the same design — the scanner tracks no quote state
   and reads test names as content.
   None of these four are carved out of the token list — the caller reviews
   the ``snippet`` field and nothing here blocks the verdict (the
   ``leftover_artifacts`` channel is advisory end to end; see plan 34).

Wrapper path resolution (install_root parameter — closes a pre-existing defect)
--------------------------------------------------------------------------------
``resolve-feature-scope`` emits ``files_for_finders`` INSTALL-ROOT-relative in
wrapper mode (``_shared/feature_scope.py``'s ``_prefix_paths`` prefixes each
source-relative path with ``os.path.relpath(source_root, install_root)``,
e.g. ``my-project/src/main.py``).  Before this parameter existed,
``check_hygiene`` always joined a relative changed path onto ``source_root``
— in wrapper mode that read ``<source_root>/my-project/src/main.py``, a path
that does not exist, so EVERY changed file landed in ``files_unreadable``.
The scope-creep comparison had the mirror defect: it normalised the changed
path against ``source_root`` while the baseline ``touched_files`` are
source-relative, so every file read as creep.

The fix (active ONLY when ``check_hygiene`` is in wrapper mode — see the
``install_root`` parameter doc above): compute
``rel_prefix = os.path.relpath(realpath(source_root), realpath(install_root))``,
normalised to ``/`` separators.  For a RELATIVE changed path that starts with
``rel_prefix + "/"``, its source-relative form is the remainder after that
prefix, and the file is read from ``os.path.join(install_root, cf)``; a
relative path that does NOT start with the prefix is resolved exactly as
before (against ``source_root``) — the fix never guesses at an unrecognised
shape.  Absolute paths are unchanged in every mode.  The reported ``"file"``
value in every finding, and in ``scope_creep`` / ``files_unreadable``, is
always EXACTLY the string given in ``changed_files`` — only the path used to
OPEN the file and the path used for scope-creep NORMALISATION are affected.
Scope-creep compares the source-relative form against the baseline
normalised with the existing ``_normalise_path(p, source_root)``.  In
standalone mode (``install_root`` ``None`` or realpath-equal to
``source_root``) this whole block is inert — behavior is byte-identical to
before ``install_root`` existed.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# File-type gate — polyglot denylist (not a code-extension allowlist)
# ---------------------------------------------------------------------------
# We exclude KNOWN prose/data path segments and extensions rather than
# enumerating source-code languages.  This avoids false negatives on
# unlisted language extensions (Go, Rust, Kotlin, …) at the cost of
# occasionally letting a prose file slip through — which is the correct
# trade-off for a framework that targets polyglot consumer projects.
#
# Skip-dirs: matched against every SEGMENT of the normalised path so that
# both top-level "specs/foo.md" and wrapper-prefixed "subdir/specs/foo.md"
# are caught.  The check is case-insensitive to handle macOS/Windows paths.
#
# "research" / "discover" are legacy top-level dirs: plan 68 relocated
# /research and /discover artifacts inside the feature directory (already
# listed above) for all NEW work -- specs/NNN-slug/ at the time, also
# specs/YYYY/MM/<leaf>/ as of 91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-
# PLAN.md Phase 3.  Kept here only so a grandfathered install's
# pre-plan-68 research/ and discover/ dirs stay skipped by the hygiene scan
# (D3 clean cut — old dirs persist on disk, nothing migrates).
_SKIP_PATH_SEGMENTS = frozenset([
    "specs", "docs", "design", "audits",
    "research", "discover", "bugs", ".devforge",
])

# Skip-extensions: matched case-insensitively against the file's suffix.
_SKIP_EXTENSIONS = frozenset([
    ".md", ".html", ".htm", ".txt",
    ".json", ".yaml", ".yml",
    ".csv", ".svg", ".lock",
])


def _is_code_file(path):
    # type: (str) -> bool
    """Return True when path should be treated as a source-code file.

    Returns False (skip) for:
      - Files whose normalised path contains a known forge-artifact directory
        segment (``specs``, ``docs``, ``design``, ``audits``, ``research``,
        ``discover``, ``bugs``, ``.devforge``).  Matching is done on every
        individual path segment so that wrapper-mode prefixes (e.g.
        ``subproject/specs/…``) are also excluded.
      - Files with known prose/data extensions (``.md``, ``.html``, etc.).

    Returns True for everything else (prefer false negatives over false
    positives — an unrecognised code extension passes through rather than
    being silently skipped).

    Note on dotfiles: ``.env``, ``.gitignore``, and similar dotfiles have an
    empty string as their extension under ``os.path.splitext`` (the leading dot
    is part of the name, not a suffix separator).  An empty extension is not in
    ``_SKIP_EXTENSIONS``, so dotfiles pass through and are scanned — consistent
    with the denylist design.
    """
    # Strip leading "./" and normalise separators, matching _normalise_path.
    if path.startswith("./"):
        path = path[2:]
    path = path.replace("\\", "/")

    # Check extension (case-insensitive).
    _, ext = os.path.splitext(path)
    if ext.lower() in _SKIP_EXTENSIONS:
        return False

    # Check every path segment against the known forge-artifact directories.
    segments = path.split("/")
    for seg in segments[:-1]:  # exclude the filename itself
        if seg.lower() in _SKIP_PATH_SEGMENTS:
            return False

    return True


# ---------------------------------------------------------------------------
# Leftover-artifact regex patterns
# ---------------------------------------------------------------------------

# debug_print: console.log( or bare print(
# The negative lookbehind (?<![.\w]) on print ensures that .print( (method
# calls like self.print(), rich.print(), obj.print()) are NOT matched.
# \w covers [a-zA-Z0-9_], so any identifier or dot before print is excluded.
# console.log( is already qualified so the lookbehind there is harmless.
_DEBUG_PRINT_RE = re.compile(r"\bconsole\.log\s*\(|(?<![.\w])print\s*\(")

# debug_statement: debugger (whole-word), pdb.set_trace(), breakpoint()
_DEBUG_STMT_DEBUGGER_RE = re.compile(r"\bdebugger\b")
_DEBUG_STMT_PDB_RE = re.compile(r"\bpdb\.set_trace\s*\(")
_DEBUG_STMT_BREAKPOINT_RE = re.compile(r"\bbreakpoint\s*\(\s*\)")

# bare_todo / bare_fixme: TODO or FIXME not followed by a ticket reference.
# A "ticket reference" is: #digits, JIRA-style (LETTERS-digits), or http URL.
_TODO_RE = re.compile(r"\bTODO\b", re.IGNORECASE)
_FIXME_RE = re.compile(r"\bFIXME\b", re.IGNORECASE)
_TICKET_REF_RE = re.compile(
    r"#\d+|[A-Z]{2,}-\d+|https?://",
    re.IGNORECASE,
)

# commented_code_block: comment-only line whose body carries a dual code signal.
# Python comment: # (stripped)
# JS/TS/Vue comment: // (stripped)
_COMMENT_PREFIX_RE = re.compile(r"^(//|#)\s*(.*)")

# Structure patterns that — combined with a terminator — signal commented code.
# These are deliberately NARROW: only forms unlikely to appear in English prose.
# Excluded: return/from/import/class/const/let/var/export — all common in English.
_STRUCTURE_START_RE = re.compile(
    r"^(def |async def |function |async function |if \(|for \(|while \(|foreach \(|module\.exports)",
    re.IGNORECASE,
)

# Assignment-call pattern: <ident> = <something>( — the = and ( together signal code.
# Matches "x = foo(" or "self.x = Bar(" etc.
_ASSIGN_CALL_RE = re.compile(r"\w[\w.]*\s*=\s*\S+\s*\(")

# Code terminators that — after a structure match — confirm a code statement.
# Ends with : { } ) or ;
_CODE_TERMINATOR_RE = re.compile(r"[:{})]$|;$")

# Call-expression pattern: an identifier immediately followed by ( — signals a real
# function call (e.g. compute(, fetchData(, doSomething() — NOT a parenthetical note).
_IDENT_CALL_RE = re.compile(r"\w\s*\(")


# ---------------------------------------------------------------------------
# framework_mention — wrapper-mode-only, advisory (see module docstring for
# the full design rationale, the ratified token list, and the recorded
# false-positive classes).  ONE combined pattern; the case-sensitive
# filename/path tokens sit at module level, the case-insensitive vocabulary
# tokens are scoped with an inline (?i:...) group so the two case-sensitive
# exceptions (Task NNN, AC-N) are not silenced by a blanket re.IGNORECASE.
# ---------------------------------------------------------------------------
_FRAMEWORK_MENTION_PATTERNS = [
    # --- Filename / path tokens (CASE-SENSITIVE) ---
    r"(?<![\w-])spec\.md(?![\w-])",
    r"(?<![\w-])plan\.md(?![\w-])",
    r"(?<![\w-])specs/",
    r"(?<![\w-])tasks/README\.md(?![\w-])",
    r"(?<![\w-])constitution\.md(?![\w-])",
    r"(?<![\w-])CLAUDE\.md(?![\w-])",
    r"(?<![\w-])\.devforge(?![\w-])",
    r"(?<![\w-])\.claude/",
    r"(?<![\w-])breakdown-handoff(?![\w-])",
    r"(?<![\w-])research-handoff(?![\w-])",
    r"(?<![\w-])discover-handoff(?![\w-])",
    r"(?<![\w-])plan-handoff(?![\w-])",
    r"(?<![\w-])grill\.md(?![\w-])",
    r"(?<![\w-])verification\.md(?![\w-])",
    r"(?<![\w-])review\.md(?![\w-])",
    r"(?<![\w-])summary\.md(?![\w-])",
    r"(?<![\w-])fix-seed(?![\w-])",
    r"(?<![\w-])grill-seed(?![\w-])",
    r"(?<![\w-])intake-rerun(?![\w-])",
    # --- Vocabulary tokens ---
    # Refined boundary (module docstring "Refinement recorded"): excludes a
    # leading "." too, so "cfg.devforge" does not fire via the bare word.
    r"(?i:(?<![\w.-])devforge(?![\w-]))",
    r"(?i:(?<![\w-])/devforge:)",
    r"\bTask \d{3}\b",           # case-sensitive
    r"\bAC-\d+\b",               # case-sensitive
    r"(?i:\bacceptance criteri)",
    r"(?i:\bspec criteria\b)",
    r"(?i:\bDone When\b)",
    r"(?i:\bconstitution\b)",
]
_FRAMEWORK_MENTION_RE = re.compile("|".join(_FRAMEWORK_MENTION_PATTERNS))


def _is_commented_code(line_stripped):
    # type: (str) -> bool
    """Return True when line_stripped is a comment-only line with a dual code signal.

    Rules (any one match fires):

    Rule A — assignment-call pattern:
      The body contains ``<ident> = <something>(`` — the ``=`` and ``(`` together
      signal a commented-out assignment to a function call, regardless of leading
      keyword.  Catches "// const x = getConfig();" even without a code terminator.

    Rule B — bare call-statement ending with ``;`` and containing ``(``:
      e.g. "// oldFunc();" "// doSomething(a, b);"  The ``;`` is a strong
      code-statement signal.

    Rule C — structure-pattern + code-terminator (dual signal):
      (a) Body starts with a narrow code-structure pattern:
            ``def ``         ``async def ``   — Python function definition
            ``function ``    ``async function `` — JS/TS function definition
            ``if (``         ``for (``   ``while (``   ``foreach (`` — control flow with paren
            ``module.exports``                          — CommonJS export
      (b) Body ends with a code terminator: ``:`` ``{`` ``}`` ``)`` or ``;``.
      Note: bare tokens like ``return ``, ``from ``, ``import ``, ``class ``,
      ``const ``, ``let ``, ``var ``, and ``export `` are EXCLUDED from (a) because
      they match common English prose ("// from the spec", "// class is immutable").

    Rule D — call-expression ending with ``)``:
      Body ends with ``)`` AND contains ``(``.  This catches return/assignment
      patterns whose body IS a call expression, e.g. "# return compute(x)" or
      "// fetchData(url)".  English prose like "// return type is X" does not end
      with ``)`` so it is safe.

    English prose comments like "// from the spec", "// return type is X",
    "// class is immutable", "// let me explain" do NOT fire under any rule.
    """
    m = _COMMENT_PREFIX_RE.match(line_stripped)
    if m is None:
        return False
    body = m.group(2).strip()
    if not body:
        return False

    body_lower = body.lower()

    # Rule A: assignment-call pattern (ident = func_call() — regardless of prefix)
    if _ASSIGN_CALL_RE.search(body):
        return True

    # Rule B: bare call-statement ending with ; that contains (
    # e.g. "oldFunc();" "doSomething(a, b);"
    if body.endswith(";") and "(" in body:
        return True

    # Rule C: structure-pattern + code-terminator (dual signal)
    if _STRUCTURE_START_RE.match(body_lower):
        # Terminators: : { } ) or ;
        if re.search(r"[:{})]\s*$|;\s*$", body):
            return True

    # Rule D: call-expression ending with ) that contains an ident-call pattern.
    # Catches "return compute(x)", "fetchData(url)" but NOT "the result (lazy)".
    # Requires <ident>( somewhere in the body so parenthetical prose doesn't fire.
    if body.endswith(")") and _IDENT_CALL_RE.search(body):
        return True

    return False


def _has_ticket_ref(line):
    # type: (str) -> bool
    """Return True when the line contains a ticket/issue reference."""
    return bool(_TICKET_REF_RE.search(line))


def _normalise_path(path, source_root):
    # type: (str, str) -> str
    """Normalise a file path to a source-root-relative form.

    Absolute paths inside source_root are made relative.  Leading "./" is
    stripped.  Path separators are normalised to "/".  Case is preserved —
    lowercasing is NOT applied because it produces false negatives on
    case-sensitive filesystems (Linux) where ``src/Components/MyButton.tsx``
    and ``src/components/mybutton.tsx`` are distinct files.
    """
    # Strip leading "./"
    if path.startswith("./"):
        path = path[2:]

    # If absolute and under source_root, make relative.
    if os.path.isabs(path) and source_root:
        rel = os.path.relpath(path, source_root)
        if not rel.startswith(".."):
            path = rel

    # Normalise separators only (no case change).
    return path.replace("\\", "/")


def _check_file_artifacts(filepath, file_lines):
    # type: (str, List[str]) -> List[Dict]
    """Scan file_lines for leftover artifacts.  Returns list of finding dicts."""
    findings = []  # type: List[Dict]

    for lineno, raw_line in enumerate(file_lines, start=1):
        stripped = raw_line.rstrip("\n\r").strip()
        if not stripped:
            continue

        # --- debug_print ---
        if _DEBUG_PRINT_RE.search(stripped):
            findings.append({
                "file": filepath,
                "line": lineno,
                "kind": "debug_print",
                "snippet": stripped[:200],
            })
            continue  # one finding per line

        # --- debug_statement ---
        if (
            _DEBUG_STMT_DEBUGGER_RE.search(stripped)
            or _DEBUG_STMT_PDB_RE.search(stripped)
            or _DEBUG_STMT_BREAKPOINT_RE.search(stripped)
        ):
            findings.append({
                "file": filepath,
                "line": lineno,
                "kind": "debug_statement",
                "snippet": stripped[:200],
            })
            continue

        # --- bare_todo / bare_fixme ---
        if _TODO_RE.search(stripped) and not _has_ticket_ref(stripped):
            findings.append({
                "file": filepath,
                "line": lineno,
                "kind": "bare_todo",
                "snippet": stripped[:200],
            })
            continue
        if _FIXME_RE.search(stripped) and not _has_ticket_ref(stripped):
            findings.append({
                "file": filepath,
                "line": lineno,
                "kind": "bare_fixme",
                "snippet": stripped[:200],
            })
            continue

        # --- commented_code_block ---
        if _is_commented_code(stripped):
            findings.append({
                "file": filepath,
                "line": lineno,
                "kind": "commented_code_block",
                "snippet": stripped[:200],
            })
            continue

    return findings


def _check_framework_mentions(filepath, file_lines):
    # type: (str, List[str]) -> List[Dict]
    """Scan file_lines for framework-artifact mentions.  Wrapper-mode only.

    Independent of _check_file_artifacts's existing-kind chain — this scans
    EVERY line regardless of whether an existing-kind finding already fired
    on it, so a single line may carry both.  At most one "framework_mention"
    finding is produced per line even when several tokens match it.  See the
    module docstring's "framework_mention" section for the ratified token
    list and the recorded false-positive classes.
    """
    findings = []  # type: List[Dict]

    for lineno, raw_line in enumerate(file_lines, start=1):
        stripped = raw_line.rstrip("\n\r").strip()
        if not stripped:
            continue
        if _FRAMEWORK_MENTION_RE.search(stripped):
            findings.append({
                "file": filepath,
                "line": lineno,
                "kind": "framework_mention",
                "snippet": stripped[:200],
            })

    return findings


def _merge_hygiene_findings(existing, mentions):
    # type: (List[Dict], List[Dict]) -> List[Dict]
    """Merge two per-file, line-ascending finding lists into one.

    Both ``existing`` (from _check_file_artifacts) and ``mentions`` (from
    _check_framework_mentions) carry at most one entry per line and are
    already produced in ascending-line order.  On a line shared by both, the
    existing-kind finding is ordered first, then the framework_mention
    finding — a simple two-pointer merge with an existing-first tie-break
    achieves this without re-sorting either input.
    """
    merged = []  # type: List[Dict]
    i = 0
    j = 0
    while i < len(existing) and j < len(mentions):
        if existing[i]["line"] <= mentions[j]["line"]:
            merged.append(existing[i])
            i += 1
        else:
            merged.append(mentions[j])
            j += 1
    merged.extend(existing[i:])
    merged.extend(mentions[j:])
    return merged


def check_hygiene(changed_files, scope_baseline, source_root, install_root=None):
    # type: (List[str], Optional[List[str]], str, Optional[str]) -> Dict
    """Flag scope-creep and leftover artifacts across the changed files.

    Parameters
    ----------
    changed_files : list[str]
        File paths changed during implementation.
    scope_baseline : list[str] or None
        Planned file set (``touched_files`` union from breakdown-handoff.json).
        ``None`` or ``[]`` skips scope-creep checking.
    source_root : str
        Absolute path to the source tree; relative paths in ``changed_files``
        are resolved against this (except in wrapper mode — see below).
    install_root : str or None
        Absolute path to the forge install root.  ``None`` (default) means
        standalone: byte-identical to the pre-``install_root`` contract.
        Wrapper mode is ``install_root`` truthy AND its realpath differs
        from ``source_root``'s — see the module docstring's "Wrapper path
        resolution" section for the full resolution algorithm, and the
        "framework_mention" section for the wrapper-only advisory kind this
        enables.

    Returns
    -------
    dict with keys:
        scope_creep : list[str]
            Files in ``changed_files`` not in ``scope_baseline``, after
            normalisation.  Non-code files are never reported here.
        leftover_artifacts : list[dict]
            See module docstring for the per-finding shape.
        scope_creep_checked : bool
        files_checked : int
            Count of code files actually read and scanned.
        files_unreadable : list[str]
            Code files that could not be read.
        files_skipped : int
            Count of files bypassed by the file-type gate (prose/data files).
            Additive key — callers that only check the pre-existing keys are
            not affected.
    """
    source_root = source_root or os.getcwd()

    wrapper = bool(install_root) and (
        os.path.realpath(install_root) != os.path.realpath(source_root)
    )

    # rel_prefix is the source_root subdirectory name as seen from
    # install_root (the same direction _shared/feature_scope.py's
    # _prefix_paths computes) — only meaningful, and only computed, in
    # wrapper mode.
    rel_prefix = None  # type: Optional[str]
    if wrapper:
        try:
            rel_prefix = os.path.relpath(
                os.path.realpath(source_root), os.path.realpath(install_root)
            ).replace(os.sep, "/")
        except ValueError:
            # Different drives on Windows — cannot compute a relative path;
            # fall back to resolving every changed path against source_root
            # (the pre-existing, non-wrapper-aware behavior).
            rel_prefix = None

    def _wrapper_source_relative(cf):
        # type: (str) -> Optional[str]
        """Return cf's source-relative form when it carries rel_prefix, else None."""
        if not rel_prefix:
            return None
        prefix = rel_prefix + "/"
        if cf.startswith(prefix):
            return cf[len(prefix):]
        return None

    # --- Scope-creep check ---
    # Non-code files are excluded from scope-creep reporting: they live in
    # forge-managed directories (specs/, docs/, …) that are never declared in
    # the breakdown-handoff scope baseline, so they would always appear as
    # "creep" without the gate.
    scope_creep_checked = scope_baseline is not None and len(scope_baseline) > 0
    scope_creep = []  # type: List[str]

    if scope_creep_checked:
        baseline_set = {
            _normalise_path(p, source_root) for p in scope_baseline
        }
        for cf in changed_files:
            if not _is_code_file(cf):
                continue  # prose/data file — never scope-creep
            if wrapper and not os.path.isabs(cf):
                source_rel = _wrapper_source_relative(cf)
                norm = _normalise_path(
                    source_rel if source_rel is not None else cf, source_root
                )
            else:
                norm = _normalise_path(cf, source_root)
            if norm not in baseline_set:
                scope_creep.append(cf)

    # --- Leftover-artifact check ---
    leftover_artifacts = []  # type: List[Dict]
    files_unreadable = []  # type: List[str]
    files_checked = 0
    files_skipped = 0

    for cf in changed_files:
        # Gate: skip prose/data files — artifact patterns are meaningless there
        # and produce false positives (e.g. HTML comment blocks matching
        # _DEBUG_PRINT_RE, spec headings matching commented-code rules).
        if not _is_code_file(cf):
            files_skipped += 1
            continue

        # Resolve the path to read.
        if os.path.isabs(cf):
            full_path = cf
        elif wrapper and _wrapper_source_relative(cf) is not None:
            # cf already carries the install-root prefix (e.g.
            # "my-project/src/main.py") — join it straight onto install_root.
            full_path = os.path.join(install_root, cf)
        else:
            full_path = os.path.join(source_root, cf)

        try:
            with open(full_path, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            files_unreadable.append(cf)
            continue

        files_checked += 1
        findings = _check_file_artifacts(cf, lines)
        if wrapper:
            mention_findings = _check_framework_mentions(cf, lines)
            findings = _merge_hygiene_findings(findings, mention_findings)
        leftover_artifacts.extend(findings)

    return {
        "scope_creep": scope_creep,
        "leftover_artifacts": leftover_artifacts,
        "scope_creep_checked": scope_creep_checked,
        "files_checked": files_checked,
        "files_unreadable": files_unreadable,
        "files_skipped": files_skipped,
    }
