"""bug_file.py — write bug reports to bugs/NNN-*.md in storage-rules.md format.

Extracted from _verify/_bugs.py and promoted to _shared/ so callers other
than /verify can file bugs with a custom Source field.

Public surface
--------------
  scan_highest_number(dir_path) -> int
  slugify(title, max_len=30) -> str
      Directory-generic (not bug-specific despite living here): the
      NNN-prefix scan and the filename-slug rule.  Promoted from
      _scan_highest_bug_number / _slugify (95-TICKET-CAPTURE-LANE-PLAN.md
      OQ-1's ratified PROMOTE arm) so _shared/ticket_file.py can reuse
      them rather than copy them -- single owner, no drift between
      bugs/ and tickets/ numbering or slug rules.  Behavior-preserving
      renames only; nothing about either function's logic changed.

  close_bug(bug_file_path, date, fix_notes) -> None
      Plan 88 D4 -- the cold-fix lane's single bugs/ write.  Flips exactly
      the ONE named bug file's own **Status**: line from Open/In Progress to
      Fixed, fills its empty **Fixed**: line with date, and replaces its
      ## Fix Notes placeholder body with fix_notes.  Every other byte is
      preserved.  Raises ValueError (writing NOTHING) if the file is
      missing, if date/fix_notes is empty, or if the file's own Status is
      not Open/In Progress (already Fixed, or unrecognized).  Atomic write
      (mkstemp + os.replace), matching file_bugs's convention.  See the
      close_bug docstring below for the full contract.

  file_bugs(bugs_dir, issues, feature_spec_path, date, source="verify")
      -> list[str]

      Scan bugs_dir for highest existing NNN prefix, assign sequential
      numbers from there.  For each issue dict, write bugs/NNN-<slug>.md
      in the EXACT src/devforge/storage-rules.md format.

      Parameters
      ----------
      bugs_dir : str
          Path to the bugs/ directory.  Created if absent.
      issues : list[dict]
          List of issue dicts.  Each dict:
            {
              title:     str   — short title (1-5 words, used for slug)
              severity:  str   — Critical | Warning | Info
                                 (storage-rules vocabulary; NOT Critical/High/Medium/Info
                                 from findings — the caller must map if needed)
              description: str — what is wrong (1-3 sentences)
              expected:  str   — expected behavior (from spec AC or "" when unknown)
              actual:    str   — actual behavior (from verification evidence or "")
              files:     list[{path: str, detail: str}]  — file table rows
              evidence:  str   — how this was discovered
              ac_ref:    str   — "AC-N" or "N/A"
              category:  str   — optional, for tagging (not in format, used for slug)
            }
          Missing keys default to sensible placeholders.
      feature_spec_path : str
          Path to the feature spec file (e.g. specs/001-auth/spec.md),
          or "N/A" for standalone bugs.
      date : str
          YYYY-MM-DD.  REQUIRED — never call the clock.
      source : str
          Value for the **Source** field in the bug file.  Defaults to
          "verify" so existing callers need no change.

      Returns
      -------
      list[str]  Paths of the bug files written, in order.

Bug file format (verbatim from storage-rules.md)
-------------------------------------------------
  # Bug NNN: [Short Title]

  **Status**: Open
  **Severity**: Critical | Warning | Info
  **Source**: <source>
  **Feature**: [spec path]
  **AC**: [AC-N or N/A]
  **Reported**: [YYYY-MM-DD]
  **Fixed**: [empty]

  ## Description
  ...

  ## Expected Behavior
  ...

  ## Actual Behavior
  ...

  ## File(s)
  | File | Detail |
  |------|--------|
  | ... | ... |

  ## Evidence
  ...

  ## Related Issues
  [cross-links to other bugs filed in the same batch, or omitted if standalone]

  ## Fix Notes
  [Filled in after resolution]

Numbering
---------
  Scan bugs_dir for all *.md files whose name starts with a sequence of digits
  followed by a hyphen (e.g. 001-*, 042-*).  The highest such prefix + 1 is
  the first number for this batch.  Numbers are zero-padded to 3 digits.
  If bugs_dir is empty, start at 001.

  The scan is performed ONCE before writing any file in the batch; numbers
  are assigned sequentially from that point so a crash-and-retry won't
  produce gaps (the same number would simply be overwritten by the retry).

Slug sanitisation
-----------------
  title → lowercase, replace non-alphanumeric (except hyphen) → hyphen,
  collapse runs of hyphens → single hyphen, strip leading/trailing hyphens,
  cap at 30 chars.

Stdlib only.  Python 3.8+.  Atomic writes (mkstemp + os.replace).
"""

from __future__ import annotations

import os
import re
import tempfile
from typing import Dict, List

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LEADING_DIGITS_RE = re.compile(r"^(\d+)-")
# Replaces any run of non-alphanumeric characters (including hyphens) with a
# single hyphen.  Consecutive hyphens are collapsed by the follow-up
# _SLUG_COLLAPSE_RE pass.
_SLUG_NONALNUM_RE = re.compile(r"[^a-z0-9]+")
_SLUG_COLLAPSE_RE = re.compile(r"-{2,}")


def scan_highest_number(dir_path):
    # type: (str) -> int
    """Return the highest NNN prefix found in dir_path, or 0 if none.

    Directory-generic: scans *.md filenames for a leading digit-run +
    hyphen, independent of what the files inside are named or contain.
    Shared by bug_file.file_bugs (bugs/) and ticket_file.file_ticket
    (tickets/) -- each directory's sequence is scanned independently
    (95-TICKET-CAPTURE-LANE-PLAN.md OQ-3), so passing bugs_dir here never
    affects tickets_dir's numbering or vice versa.
    """
    if not os.path.isdir(dir_path):
        return 0
    highest = 0
    try:
        entries = os.listdir(dir_path)
    except OSError:
        return 0
    for name in entries:
        if not name.endswith(".md"):
            continue
        m = _LEADING_DIGITS_RE.match(name)
        if m:
            n = int(m.group(1))
            if n > highest:
                highest = n
    return highest


def slugify(title, max_len=30):
    # type: (str, int) -> str
    """Convert title to a filename slug, truncating at a word boundary.

    Truncation rule: if the slug exceeds max_len, find the last hyphen that
    fits within the cap and cut there (dropping the trailing partial word).
    If no hyphen exists within the cap (i.e. the first word alone exceeds the
    cap), keep the full first word so the slug is never empty.
    """
    slug = title.lower()
    slug = _SLUG_NONALNUM_RE.sub("-", slug)
    slug = _SLUG_COLLAPSE_RE.sub("-", slug)
    slug = slug.strip("-")
    if len(slug) > max_len:
        candidate = slug[:max_len]
        last_hyphen = candidate.rfind("-")
        if last_hyphen > 0:
            # Cut at the word boundary, then strip any trailing hyphen.
            slug = candidate[:last_hyphen].rstrip("-")
        else:
            # No hyphen within the cap: the first word exceeds max_len.
            # Keep it intact rather than producing an empty slug.
            slug = candidate.rstrip("-")
    return slug or "bug"


def _format_bug(
    number,            # type: int
    issue,             # type: Dict
    feature_spec_path, # type: str
    date,              # type: str
    related_paths,     # type: List[str]
    source,            # type: str
):
    # type: (...) -> str
    """Render a single bug file in storage-rules.md format."""
    title = (issue.get("title") or "Untitled bug").strip()
    severity = (issue.get("severity") or "Info").strip()
    description = (issue.get("description") or "").strip()
    expected = (issue.get("expected") or "").strip()
    actual = (issue.get("actual") or "").strip()
    files = issue.get("files") or []
    evidence = (issue.get("evidence") or "").strip()
    ac_ref = (issue.get("ac_ref") or "N/A").strip()

    lines = []  # type: List[str]

    lines.append("# Bug {0:03d}: {1}".format(number, title))
    lines.append("")
    lines.append("**Status**: Open")
    lines.append("**Severity**: {0}".format(severity))
    lines.append("**Source**: {0}".format(source))
    lines.append("**Feature**: {0}".format(feature_spec_path or "N/A"))
    lines.append("**AC**: {0}".format(ac_ref))
    lines.append("**Reported**: {0}".format(date))
    lines.append("**Fixed**: ")
    lines.append("")
    lines.append("## Description")
    lines.append("")
    lines.append(description if description else "_No description provided._")
    lines.append("")
    lines.append("## Expected Behavior")
    lines.append("")
    lines.append(
        expected if expected else "_Expected behavior not specified — see spec AC._"
    )
    lines.append("")
    lines.append("## Actual Behavior")
    lines.append("")
    lines.append(
        actual if actual else "_Actual behavior not specified — see verification evidence._"
    )
    lines.append("")
    lines.append("## File(s)")
    lines.append("")
    lines.append("| File | Detail |")
    lines.append("|------|--------|")
    if files:
        for f in files:
            fpath = (f.get("path") or "").strip()
            fdetail = (f.get("detail") or "").strip()
            lines.append("| {0} | {1} |".format(fpath, fdetail))
    else:
        lines.append("| (unknown) | (see evidence) |")
    lines.append("")
    lines.append("## Evidence")
    lines.append("")
    lines.append(evidence if evidence else "_No evidence provided._")
    lines.append("")
    lines.append("## Related Issues")
    lines.append("")
    if related_paths:
        for rp in related_paths:
            slug_part = os.path.basename(rp)
            title_part = re.sub(r"^\d+-", "", os.path.splitext(slug_part)[0])
            lines.append("- {0} — {1}".format(rp, title_part.replace("-", " ")))
    else:
        lines.append("_None — standalone bug._")
    lines.append("")
    lines.append("## Fix Notes")
    lines.append("")
    lines.append("_Filled in after resolution._")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# file_bugs
# ---------------------------------------------------------------------------


def file_bugs(bugs_dir, issues, feature_spec_path, date, source="verify"):
    # type: (str, List[Dict], str, str, str) -> List[str]
    """Write bug files in bugs/NNN-<slug>.md format.

    Parameters
    ----------
    bugs_dir : str
        Path to the bugs/ directory.  Created if absent.
    issues : list[dict]
        Issue dicts — see module docstring for shape.
    feature_spec_path : str
        Path to the feature spec (e.g. specs/001-auth/spec.md).
    date : str
        YYYY-MM-DD.  REQUIRED — never call the clock.
    source : str
        Value for the **Source** field.  Defaults to "verify" so existing
        callers that omit the argument are byte-identical to before.

    Returns
    -------
    list[str]  Paths written, in order.
    """
    if not issues:
        return []

    os.makedirs(bugs_dir, exist_ok=True)

    # Scan ONCE for the highest existing bug number
    highest = scan_highest_number(bugs_dir)
    start_num = highest + 1

    # Pre-compute all file paths (for Related Issues cross-links)
    paths = []  # type: List[str]
    for i, issue in enumerate(issues):
        number = start_num + i
        title = (issue.get("title") or "bug").strip()
        slug = slugify(title)
        filename = "{0:03d}-{1}.md".format(number, slug)
        paths.append(os.path.join(bugs_dir, filename))

    written = []  # type: List[str]
    for i, issue in enumerate(issues):
        out_path = paths[i]
        number = start_num + i

        # Related Issues = all OTHER bug paths in this batch
        related = [p for j, p in enumerate(paths) if j != i]

        content = _format_bug(
            number=number,
            issue=issue,
            feature_spec_path=feature_spec_path,
            date=date,
            related_paths=related,
            source=source,
        )

        # Atomic write
        bugs_abs_dir = os.path.dirname(out_path) or "."
        tmp_fd, tmp_path = tempfile.mkstemp(
            prefix=".tmp-bug-",
            suffix=".md",
            dir=bugs_abs_dir,
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
                fh.write(content)
            os.replace(tmp_path, out_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        written.append(out_path)

    return written


# ---------------------------------------------------------------------------
# close_bug (plan 88 D4 -- the cold-fix lane's single bugs/ write)
# ---------------------------------------------------------------------------

_STATUS_LINE_PREFIX = "**Status**: "
_FIXED_LINE_PREFIX = "**Fixed**: "
_FIX_NOTES_HEADING = "## Fix Notes"
_FIX_NOTES_PLACEHOLDER = "_Filled in after resolution._"
_CLOSABLE_STATUSES = ("Open", "In Progress")


def close_bug(bug_file_path, date, fix_notes):
    # type: (str, str, str) -> None
    """Flip a single bug file's own Status to Fixed (plan 88 D4).

    Mutates exactly three fields in bug_file_path; every other byte is
    preserved:
      1. **Status**: Open | In Progress  ->  **Status**: Fixed
      2. the empty **Fixed**:  line      ->  **Fixed**: <date>
      3. the ## Fix Notes placeholder body ("_Filled in after resolution._")
         -> fix_notes

    Anchoring: each field is located by its OWN line start
    (`**Status**: `, `**Fixed**: `) or by the `## Fix Notes` heading plus its
    known literal placeholder body -- never by a substring match, so
    lookalike text legitimately appearing inside `## Description` /
    `## Evidence` prose is never mistaken for the bug's own fields.

    Parameters
    ----------
    bug_file_path : str
        Path to the bugs/NNN-*.md file to close (the ONE file a caller such
        as cold-mode /devforge:fix was handed).
    date : str
        YYYY-MM-DD.  REQUIRED -- the caller supplies it; this function never
        calls the clock (matches file_bugs's convention).
    fix_notes : str
        Root cause / what changed / the commit SHA -- replaces the Fix
        Notes placeholder body verbatim.  May contain embedded newlines.

    Raises
    ------
    ValueError
        - date or fix_notes is empty
        - bug_file_path does not exist (or is not a regular file)
        - the file's own Status is not "Open" or "In Progress" (already
          Fixed, or an unrecognized value) -- rejected WITHOUT writing
        - the file has no **Status**: line or no **Fixed**: line (a
          malformed or foreign file) -- rejected WITHOUT writing
        - the ## Fix Notes body is no longer the placeholder -- hand-edited
          (an Open/In Progress bug whose owner already wrote real notes
          before this automated close ever ran) or previously closed --
          rejected WITHOUT writing, so hand-written content is never
          silently overwritten

    On success the file is atomically replaced (tempfile.mkstemp +
    os.replace), matching file_bugs's atomic-write convention.
    """
    if not date:
        raise ValueError("close_bug: date is required")
    if not fix_notes:
        raise ValueError("close_bug: fix_notes is required")
    if not os.path.isfile(bug_file_path):
        raise ValueError(
            "close_bug: bug file not found: {0}".format(bug_file_path)
        )

    with open(bug_file_path, "r", encoding="utf-8") as fh:
        content = fh.read()
    lines = content.split("\n")

    status_idx = None
    for i, line in enumerate(lines):
        if line.startswith(_STATUS_LINE_PREFIX):
            status_idx = i
            break
    if status_idx is None:
        raise ValueError(
            "close_bug: no **Status**: line found in {0}".format(bug_file_path)
        )

    current_status = lines[status_idx][len(_STATUS_LINE_PREFIX):].strip()
    if current_status not in _CLOSABLE_STATUSES:
        raise ValueError(
            "close_bug: {0} has Status '{1}' (expected Open or In Progress) "
            "-- already closed or unrecognized, refusing to write".format(
                bug_file_path, current_status
            )
        )

    fixed_idx = None
    for i, line in enumerate(lines):
        if line.startswith(_FIXED_LINE_PREFIX):
            fixed_idx = i
            break
    if fixed_idx is None:
        raise ValueError(
            "close_bug: no **Fixed**: line found in {0}".format(bug_file_path)
        )

    heading_idx = None
    for i, line in enumerate(lines):
        if line == _FIX_NOTES_HEADING:
            heading_idx = i
            break
    if heading_idx is None:
        raise ValueError(
            "close_bug: no '## Fix Notes' section found in {0}".format(
                bug_file_path
            )
        )

    placeholder_idx = None
    for i in range(heading_idx + 1, len(lines)):
        if lines[i] == _FIX_NOTES_PLACEHOLDER:
            placeholder_idx = i
            break
    if placeholder_idx is None:
        raise ValueError(
            "close_bug: '## Fix Notes' body in {0} is no longer the "
            "placeholder -- hand-edited (real notes already written) or "
            "previously closed -- refusing to overwrite it".format(
                bug_file_path
            )
        )

    lines[status_idx] = _STATUS_LINE_PREFIX + "Fixed"
    lines[fixed_idx] = _FIXED_LINE_PREFIX + date
    lines[placeholder_idx] = fix_notes

    new_content = "\n".join(lines)

    out_dir = os.path.dirname(bug_file_path) or "."
    tmp_fd, tmp_path = tempfile.mkstemp(
        prefix=".tmp-bug-close-",
        suffix=".md",
        dir=out_dir,
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as fh:
            fh.write(new_content)
        os.replace(tmp_path, bug_file_path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
