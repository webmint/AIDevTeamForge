"""plan_helper — structural emission helper for the /plan slash command.

Subcommands:

  pick-spec [path]
      Resolve which spec to plan against.
      With path: validate the file exists and has the 9-section shape,
                 print its absolute path.
      No path:   glob specs/*/spec.md under cwd, pick highest mtime,
                 print its absolute path.
      Exit 0 on success; exit 2 if no valid spec found or path invalid.

  render-pick-summary <spec-path>
      Print a deterministic 5-line preview block the LLM copies verbatim
      into its AskUserQuestion context.
      Lines emitted:
        **Spec**: <path>
        **Type**: <spec-type or "unknown">
        **AC count**: <N> criteria across <M> subsections
        **Status**: <Draft|Approved|Complete|unknown>
        **Last modified**: <YYYY-MM-DD>
      Exit 0; exit 2 if file missing.

  list-specs
      List all specs/*/spec.md under cwd sorted by mtime desc.
      One line per spec: <index>) <relative-path> [Status: <X>] (<N> ACs)
      Exit 0 (even if empty); exit 2 if specs/ dir missing.

  check-status-and-flip <spec-path>
      Read the **Status**: line from spec frontmatter and act:
        Draft     -> rewrite to Approved, print "flipped"
        Approved  -> no change, print "already-approved"
        Complete  -> no change, print "complete"
        missing   -> insert after **Date**: line, print "inserted"
        unknown   -> no change, print "unknown-status:<value>" (surfaces anomaly to LLM)
        malformed -> exit 2 (no Date or Status line at all)
      Writes are atomic (tempfile.mkstemp + os.replace).
      Exit 0 on all success paths.

  render-findings-from-spec <spec-path>
      Emit a Phase 1.5 skeleton enumerating every spec §3-§9 finding.
      LLM fills [PLAN COVERAGE: ?] markers.
      Exit 0; exit 2 if spec missing or lacks expected sections.

  render-breakdown-handoff <spec-path> <plan-path>
      Emit the Phase 4 manual handoff block targeting /breakdown.
      Reads AC count from spec, file-impact + risk counts from plan.
      Exit 0; exit 2 if either file missing.

Exit codes:
  0 — success
  1 — reserved for I/O failures (write errors)
  2 — usage error / not-found / malformed input

Stdout is the canonical channel for output tokens; stderr for errors.
No state file — every subcommand re-reads input files.
Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Constants.
# ---------------------------------------------------------------------------

# Expected section headings in order (index = section number - 1).
_SECTION_TITLES = [
    "Overview",
    "Current State",
    "Desired Behavior",
    "Affected Areas",
    "Acceptance Criteria",
    "Out of Scope",
    "Technical Constraints",
    "Open Questions",
    "Risks",
]

_REQUIRED_SECTION_PATTERN = re.compile(
    r"^##\s+(\d+)\.\s+", re.MULTILINE
)

# AC line pattern: "- [x] **AC-N**: ..." or "- [ ] **AC-N**: ..."
_AC_LINE_PATTERN = re.compile(r"^\s*-\s+\[[xX ]\]\s+\*\*AC-\d+\*\*", re.MULTILINE)

# Subsection heading pattern (e.g. "### 5.1 Tooling / artifact presence...")
_AC_SUBSECTION_PATTERN = re.compile(r"^###\s+5\.\d+\s+", re.MULTILINE)

# Frontmatter field patterns.
_STATUS_PATTERN = re.compile(r"^\*\*Status\*\*:\s*(.+)$", re.MULTILINE)
_DATE_PATTERN = re.compile(r"^\*\*Date\*\*:\s*(.+)$", re.MULTILINE)
_SPEC_TYPE_PATTERN = re.compile(r"^\*\*Spec type\*\*:\s*(.+)$", re.MULTILINE)


# ---------------------------------------------------------------------------
# Spec parsing utilities.
# ---------------------------------------------------------------------------


def _read_file(path: str) -> Optional[str]:
    """Return file contents as string, or None if unreadable."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, IOError):
        return None


def _has_nine_sections(content: str) -> bool:
    """Return True if content contains headings ## 1. through ## 9."""
    found = set()
    for m in _REQUIRED_SECTION_PATTERN.finditer(content):
        found.add(int(m.group(1)))
    return all(i in found for i in range(1, 10))


def _extract_section(content: str, section_num: int) -> str:
    """Extract text of section N (between ## N. heading and ## N+1. heading or EOF)."""
    # Build pattern matching the exact section heading.
    start_pat = re.compile(
        r"^##\s+" + str(section_num) + r"\.\s+", re.MULTILINE
    )
    m_start = start_pat.search(content)
    if not m_start:
        return ""
    start = m_start.start()
    # Find next ## heading at the same or higher level.
    next_h2 = re.compile(r"^##\s+", re.MULTILINE)
    m_next = next_h2.search(content, m_start.end())
    if m_next:
        return content[start:m_next.start()]
    return content[start:]


def _parse_frontmatter_field(content: str, pattern: re.Pattern) -> Optional[str]:
    """Extract the value of a frontmatter field."""
    m = pattern.search(content)
    if not m:
        return None
    return m.group(1).strip()


def _count_acs(content: str) -> Tuple[int, int]:
    """Return (total_ac_count, subsections_with_acs).

    Counts AC lines matching ``- [x/X/ ] **AC-N**`` in section 5 only,
    and counts the number of ### 5.x subsections that contain at least
    one such line.
    """
    sec5 = _extract_section(content, 5)
    total = len(_AC_LINE_PATTERN.findall(sec5))

    # Count subsections with ≥1 AC.
    subsections_with_acs = 0
    for sub_m in _AC_SUBSECTION_PATTERN.finditer(sec5):
        sub_start = sub_m.start()
        # Find next ### heading or end of section.
        next_sub = _AC_SUBSECTION_PATTERN.search(sec5, sub_m.end())
        sub_text = sec5[sub_start:(next_sub.start() if next_sub else len(sec5))]
        if _AC_LINE_PATTERN.search(sub_text):
            subsections_with_acs += 1

    return total, subsections_with_acs


def _file_mtime_iso(path: str) -> str:
    """Return file mtime as YYYY-MM-DD."""
    ts = os.path.getmtime(path)
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def _glob_specs(cwd: str) -> List[str]:
    """Return list of absolute paths to specs/*/spec.md under cwd."""
    specs_dir = Path(cwd) / "specs"
    if not specs_dir.is_dir():
        return []
    result = []
    for sub in specs_dir.iterdir():
        candidate = sub / "spec.md"
        if candidate.is_file():
            result.append(str(candidate.resolve()))
    return result


def _valid_specs(paths: List[str]) -> List[str]:
    """Filter to paths whose content has the full 9-section shape."""
    valid = []
    for p in paths:
        content = _read_file(p)
        if content is not None and _has_nine_sections(content):
            valid.append(p)
    return valid


# ---------------------------------------------------------------------------
# Subcommand: pick-spec
# ---------------------------------------------------------------------------


def cmd_pick_spec(args) -> int:
    """Resolve the spec path and print it to stdout."""
    spec_path = getattr(args, "path", None)

    if spec_path:
        # Explicit path given.
        resolved = Path(spec_path)
        if not resolved.is_absolute():
            resolved = Path.cwd() / resolved
        if not resolved.is_file():
            sys.stderr.write(
                "plan_helper: spec not found: {0}\n".format(spec_path)
            )
            return 2
        content = _read_file(str(resolved))
        if content is None or not _has_nine_sections(content):
            sys.stderr.write(
                "plan_helper: spec at {0} does not have the required "
                "9-section shape (## 1. Overview ... ## 9. Risks)\n".format(spec_path)
            )
            return 2
        sys.stdout.write(str(resolved) + "\n")
        return 0

    # Auto-pick: find highest-mtime valid spec under specs/.
    cwd = str(Path.cwd())
    specs_dir = Path(cwd) / "specs"
    if not specs_dir.is_dir():
        sys.stderr.write(
            "plan_helper: no valid spec found under specs/; run /specify first\n"
        )
        return 2

    all_paths = _glob_specs(cwd)
    valid = _valid_specs(all_paths)
    if not valid:
        sys.stderr.write(
            "plan_helper: no valid spec found under specs/; run /specify first\n"
        )
        return 2

    # Pick highest mtime.
    best = max(valid, key=lambda p: os.path.getmtime(p))
    sys.stdout.write(best + "\n")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: render-pick-summary
# ---------------------------------------------------------------------------


def cmd_render_pick_summary(args) -> int:
    """Print a 5-line deterministic pick-summary block."""
    spec_path = args.spec_path
    content = _read_file(spec_path)
    if content is None:
        sys.stderr.write(
            "plan_helper: cannot read spec: {0}\n".format(spec_path)
        )
        return 2

    status = _parse_frontmatter_field(content, _STATUS_PATTERN) or "unknown"
    spec_type = _parse_frontmatter_field(content, _SPEC_TYPE_PATTERN) or "unknown"
    total_acs, subsections = _count_acs(content)
    last_modified = _file_mtime_iso(spec_path)

    sys.stdout.write("**Spec**: {0}\n".format(spec_path))
    sys.stdout.write("**Type**: {0}\n".format(spec_type))
    sys.stdout.write(
        "**AC count**: {0} criteria across {1} subsections\n".format(
            total_acs, subsections
        )
    )
    sys.stdout.write("**Status**: {0}\n".format(status))
    sys.stdout.write("**Last modified**: {0}\n".format(last_modified))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: list-specs
# ---------------------------------------------------------------------------


def cmd_list_specs(args) -> int:
    """List all specs sorted by mtime desc."""
    cwd = str(Path.cwd())
    specs_dir = Path(cwd) / "specs"
    if not specs_dir.is_dir():
        sys.stderr.write(
            "plan_helper: specs/ directory not found under cwd\n"
        )
        return 2

    all_paths = _glob_specs(cwd)
    if not all_paths:
        # Empty dir is valid; emit nothing.
        return 0

    # Sort by mtime descending.
    sorted_paths = sorted(all_paths, key=lambda p: os.path.getmtime(p), reverse=True)

    for idx, abs_path in enumerate(sorted_paths, start=1):
        content = _read_file(abs_path)
        if content is None:
            status = "unknown"
            ac_count = 0
        else:
            status = _parse_frontmatter_field(content, _STATUS_PATTERN) or "unknown"
            ac_count, _ = _count_acs(content)

        # Relative path from cwd.
        try:
            rel_path = str(Path(abs_path).relative_to(Path(cwd)))
        except ValueError:
            rel_path = abs_path

        sys.stdout.write(
            "{0}) {1} [Status: {2}] ({3} ACs)\n".format(
                idx, rel_path, status, ac_count
            )
        )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: check-status-and-flip
# ---------------------------------------------------------------------------


def _atomic_write(path: str, content: str) -> None:
    """Write content to path atomically using tempfile + os.replace."""
    target = Path(path)
    fd, tmp_path = tempfile.mkstemp(
        prefix="plan-status-",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def cmd_check_status_and_flip(args) -> int:
    """Read **Status**: line and flip Draft → Approved as needed."""
    spec_path = args.spec_path
    content = _read_file(spec_path)
    if content is None:
        sys.stderr.write(
            "plan_helper: cannot read spec: {0}\n".format(spec_path)
        )
        return 2

    status_match = _STATUS_PATTERN.search(content)
    date_match = _DATE_PATTERN.search(content)

    if status_match:
        status_val = status_match.group(1).strip()
        if status_val == "Draft":
            new_content = (
                content[: status_match.start()]
                + "**Status**: Approved"
                + content[status_match.end():]
            )
            try:
                _atomic_write(spec_path, new_content)
            except OSError as err:
                sys.stderr.write(
                    "plan_helper: cannot write spec: {0}\n".format(err)
                )
                return 1
            sys.stdout.write("flipped\n")
            return 0
        elif status_val == "Approved":
            sys.stdout.write("already-approved\n")
            return 0
        elif status_val == "Complete":
            sys.stdout.write("complete\n")
            return 0
        else:
            sys.stdout.write("unknown-status:{0}\n".format(status_val))
            return 0

    # No **Status**: line found.
    if date_match is None:
        sys.stderr.write(
            "plan_helper: no Date or Status frontmatter line found; "
            "spec malformed\n"
        )
        return 2

    # Insert **Status**: Approved immediately after the **Date**: line.
    insert_pos = date_match.end()
    # Find the end of the date line (the newline character).
    # date_match.end() is right after the matched text on that line.
    # We need to move past the newline if present.
    new_content = (
        content[:insert_pos]
        + "\n**Status**: Approved"
        + content[insert_pos:]
    )
    try:
        _atomic_write(spec_path, new_content)
    except OSError as err:
        sys.stderr.write(
            "plan_helper: cannot write spec: {0}\n".format(err)
        )
        return 1
    sys.stdout.write("inserted\n")
    return 0


# ---------------------------------------------------------------------------
# Section rendering helpers for render-findings-from-spec.
# ---------------------------------------------------------------------------


def _truncate(text: str, max_len: int = 80) -> str:
    """Return text truncated to max_len chars with '...' suffix if truncated."""
    text = text.strip()
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _render_sec3(sec_text: str) -> List[str]:
    """Enumerate §3 Desired Behavior items."""
    lines_out = []

    # Try numbered bullets first: "1. ", "2. ", etc.
    numbered_pat = re.compile(r"^\d+\.\s+(.+)", re.MULTILINE)
    numbered = numbered_pat.findall(sec_text)
    if numbered:
        for i, item in enumerate(numbered, start=1):
            lines_out.append(
                "- §3 item {0}: {1} [PLAN COVERAGE: ?]".format(
                    i, _truncate(item)
                )
            )
        return lines_out

    # Try bullet list: "- text" (but skip the heading line itself).
    bullet_pat = re.compile(r"^\s*-\s+(?!\[)(.+)", re.MULTILINE)
    bullets = bullet_pat.findall(sec_text)
    if bullets:
        for i, item in enumerate(bullets, start=1):
            lines_out.append(
                "- §3 item {0}: {1} [PLAN COVERAGE: ?]".format(
                    i, _truncate(item)
                )
            )
        return lines_out

    # Fallback: non-blank paragraphs (skip heading line).
    paras = []
    current = []
    for line in sec_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("##"):
            continue
        if stripped:
            current.append(stripped)
        else:
            if current:
                paras.append(" ".join(current))
                current = []
    if current:
        paras.append(" ".join(current))

    for i, para in enumerate(paras, start=1):
        lines_out.append(
            "- §3 item {0}: {1} [PLAN COVERAGE: ?]".format(i, _truncate(para))
        )
    return lines_out


def _parse_table_rows(sec_text: str) -> List[List[str]]:
    """Return list of non-header, non-separator table rows as cell lists."""
    rows = []
    header_seen = False
    for line in sec_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        # Check separator row: only |, -, spaces.
        if re.match(r"^\|[\s\-|:]+\|?\s*$", stripped):
            header_seen = True
            continue
        # First non-separator pipe row is the header.
        if not header_seen:
            header_seen = True
            continue
        # Data row.
        cells = [c.strip() for c in stripped.split("|") if c.strip()]
        if cells:
            rows.append(cells)
    return rows


def _is_empty_placeholder_row(cells: List[str]) -> bool:
    """Return True if the first cell is an '_(none)_' placeholder."""
    if not cells:
        return False
    return bool(re.match(r"_\(none\)_", cells[0]))


def _render_sec4(sec_text: str) -> List[str]:
    """Enumerate §4 Affected Areas table rows."""
    rows = _parse_table_rows(sec_text)
    if not rows:
        return ["- §4: (no affected areas recorded)"]
    if len(rows) == 1 and _is_empty_placeholder_row(rows[0]):
        return ["- §4: (no affected areas recorded)"]
    lines_out = []
    for i, cells in enumerate(rows, start=1):
        area = cells[0] if len(cells) > 0 else "?"
        files = cells[1] if len(cells) > 1 else "?"
        lines_out.append(
            "- §4 row {0}: {1} → {2}: [PLAN COVERAGE: ?]".format(
                i, _truncate(area, 40), _truncate(files, 40)
            )
        )
    return lines_out


def _render_sec5(sec_text: str) -> List[str]:
    """Enumerate §5 AC subsections with per-AC entries."""
    lines_out = []

    # Split by ### 5.x headings.
    subsection_pat = re.compile(r"^(###\s+5\.\d+\s+.+)$", re.MULTILINE)
    subsection_starts = list(subsection_pat.finditer(sec_text))

    if not subsection_starts:
        # No subsections found — emit raw ACs if any.
        acs = _AC_LINE_PATTERN.findall(sec_text)
        if acs:
            lines_out.append("- §5: {0} ACs".format(len(acs)))
        return lines_out

    for idx, sub_m in enumerate(subsection_starts):
        sub_heading = sub_m.group(1).strip()
        sub_start = sub_m.start()
        if idx + 1 < len(subsection_starts):
            sub_end = subsection_starts[idx + 1].start()
        else:
            sub_end = len(sec_text)
        sub_text = sec_text[sub_start:sub_end]

        # Find AC lines.
        # Pattern handles optional annotation between AC number and colon,
        # e.g. "**AC-10** (repro pass): text" as well as "**AC-1**: text".
        ac_lines_raw = re.findall(
            r"^\s*-\s+\[[xX ]\]\s+\*\*AC-(\d+)\*\*(?:[^:]*)?:\s*(.+)$",
            sub_text,
            re.MULTILINE,
        )
        if not ac_lines_raw:
            continue  # Skip empty subsections.

        # Subsection title: strip "### 5.N " prefix for readability.
        # Extract actual subsection number from heading so missing/skipped
        # subsections in the spec don't shift labels in the output.
        sub_num_m = re.search(r"###\s+5\.(\d+)\s+", sub_heading)
        sub_num = sub_num_m.group(1) if sub_num_m else str(idx + 1)
        sub_title = re.sub(r"^###\s+5\.\d+\s+", "", sub_heading)
        lines_out.append(
            "- §5.{0} ({1}): {2} ACs".format(
                sub_num, sub_title, len(ac_lines_raw)
            )
        )
        for ac_num, ac_text in ac_lines_raw:
            lines_out.append(
                "  - AC-{0}: {1} [PLAN COVERAGE: ?]".format(
                    ac_num, _truncate(ac_text)
                )
            )

    return lines_out


def _render_sec6(sec_text: str) -> List[str]:
    """Enumerate §6 Out of Scope bullets."""
    lines_out = []
    # Pattern: "- NOT included: <text>"
    not_included_pat = re.compile(
        r"^\s*-\s+NOT included:\s*(.+)$", re.MULTILINE
    )
    items = not_included_pat.findall(sec_text)
    if not items:
        return ["- §6: (no out-of-scope items recorded)"]
    for i, item in enumerate(items, start=1):
        lines_out.append(
            "- §6 item {0}: {1} [must not contradict]".format(
                i, _truncate(item)
            )
        )
    return lines_out


def _render_sec7(sec_text: str) -> List[str]:
    """Enumerate §7 Technical Constraints bullets."""
    lines_out = []
    # Pattern: "- **Label**: text" or "- Label: text" (bold optional)
    constraint_pat = re.compile(
        r"^\s*-\s+(?:\*\*)?([^:*\n]+?)(?:\*\*)?:\s+(.+)$", re.MULTILINE
    )
    items = constraint_pat.findall(sec_text)
    # Filter out placeholder lines.
    real_items = [
        (label, text)
        for label, text in items
        if not re.match(r"_\(no", label.strip())
    ]
    if not real_items:
        return ["- §7: (no constraints recorded)"]
    for i, (label, text) in enumerate(real_items, start=1):
        lines_out.append(
            "- §7 item {0} ({1}): {2} [LANDS IN: ?]".format(
                i, label.strip(), _truncate(text)
            )
        )
    return lines_out


def _render_sec8(sec_text: str) -> List[str]:
    """Enumerate §8 Open Questions + Decision-Point bullets.

    Captures both Q-prefixed open-question entries and DP-prefixed
    decision-point entries (specify_helper emits both shapes into §8).
    """
    lines_out = []
    # Pattern: "- **ID**: content" where ID is Q<digit-or-hyphen>... or DP-...
    # (possibly struck-through with ~~ when resolved).
    # ID grammar:
    #   Q[\d-][\w-]*  matches Q1, Q12, Q1-scope, Q-1, Q-scope (rejects
    #                 Question, Quality, Quack — first char after Q must be
    #                 digit or hyphen, not letter)
    #   DP-[\w-]+     matches DP-A, DP-1, DP-foo (rejects DPR, DPA, DP)
    item_pat = re.compile(
        r"^\s*-\s+(?:~~)?(?:\*\*)?(Q[\d-][\w-]*|DP-[\w-]+)(?:\*\*)?:?\s*"
        r"(?:~~)?(.+?)(?:~~)?\s*$",
        re.MULTILINE,
    )
    items = item_pat.findall(sec_text)
    real_items = [
        (item_id, text)
        for item_id, text in items
        if not re.match(r"_\(no", text.strip())
    ]
    if not real_items:
        return ["- §8: (no open questions recorded)"]
    for i, (item_id, text) in enumerate(real_items, start=1):
        # Strip any remaining ~~ or ** markers that survived the capture.
        clean_text = re.sub(r"~~|\*\*", "", text).strip()
        lines_out.append(
            "- §8 item {0} ({1}): {2} [RESOLUTION: ?]".format(
                i, item_id, _truncate(clean_text)
            )
        )
    return lines_out


def _render_sec9(sec_text: str) -> List[str]:
    """Enumerate §9 Risks table rows."""
    rows = _parse_table_rows(sec_text)
    if not rows:
        return ["- §9: (no risks recorded)"]
    if len(rows) == 1 and _is_empty_placeholder_row(rows[0]):
        return ["- §9: (no risks recorded)"]
    lines_out = []
    for i, cells in enumerate(rows, start=1):
        risk = cells[0] if cells else "?"
        lines_out.append(
            "- §9 risk {0}: {1} [MITIGATION CARRIED: ?]".format(
                i, _truncate(risk)
            )
        )
    return lines_out


# ---------------------------------------------------------------------------
# Subcommand: render-findings-from-spec
# ---------------------------------------------------------------------------


def cmd_render_findings_from_spec(args) -> int:
    """Emit the Phase 1.5 findings skeleton from the spec."""
    spec_path = args.spec_path
    content = _read_file(spec_path)
    if content is None:
        sys.stderr.write(
            "plan_helper: cannot read spec: {0}\n".format(spec_path)
        )
        return 2
    if not _has_nine_sections(content):
        sys.stderr.write(
            "plan_helper: spec does not have the required 9-section shape "
            "(## 1. Overview ... ## 9. Risks)\n"
        )
        return 2

    output_lines: List[str] = ["## Findings from Spec", ""]

    # §3 Desired Behavior.
    sec3 = _extract_section(content, 3)
    output_lines.append("### From spec §3 (Desired Behavior)")
    output_lines.extend(_render_sec3(sec3))
    output_lines.append("")

    # §4 Affected Areas.
    sec4 = _extract_section(content, 4)
    output_lines.append("### From spec §4 (Affected Areas)")
    output_lines.extend(_render_sec4(sec4))
    output_lines.append("")

    # §5 Acceptance Criteria.
    sec5 = _extract_section(content, 5)
    output_lines.append("### From spec §5 (Acceptance Criteria)")
    output_lines.extend(_render_sec5(sec5))
    output_lines.append("")

    # §6 Out of Scope.
    sec6 = _extract_section(content, 6)
    output_lines.append("### From spec §6 (Out of Scope)")
    output_lines.extend(_render_sec6(sec6))
    output_lines.append("")

    # §7 Technical Constraints.
    sec7 = _extract_section(content, 7)
    output_lines.append("### From spec §7 (Technical Constraints)")
    output_lines.extend(_render_sec7(sec7))
    output_lines.append("")

    # §8 Open Questions.
    sec8 = _extract_section(content, 8)
    output_lines.append("### From spec §8 (Open Questions)")
    output_lines.extend(_render_sec8(sec8))
    output_lines.append("")

    # §9 Risks.
    sec9 = _extract_section(content, 9)
    output_lines.append("### From spec §9 (Risks)")
    output_lines.extend(_render_sec9(sec9))

    sys.stdout.write("\n".join(output_lines) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Plan parsing helpers for render-breakdown-handoff.
# ---------------------------------------------------------------------------


def _count_file_impact(plan_content: str) -> Tuple[int, int, int]:
    """Return (total_files, new_files, modified_files) from the File Impact table.

    Returns (0, 0, 0) if no File Impact table is found.
    """
    # Find the "### File Impact" section.
    fi_match = re.search(
        r"###\s+File Impact\b", plan_content, re.IGNORECASE
    )
    if not fi_match:
        return 0, 0, 0

    # Extract text from the heading to the next heading (any level >= ##) or
    # end. Using ^#{2,}\s+ stops at the next ## or ### heading so the
    # File Impact table doesn't bleed into a sibling ## Risk Assessment table.
    next_heading = re.search(
        r"^#{2,}\s+", plan_content[fi_match.end():], re.MULTILINE
    )
    if next_heading:
        fi_text = plan_content[fi_match.start():fi_match.end() + next_heading.start()]
    else:
        fi_text = plan_content[fi_match.start():]

    rows = _parse_table_rows(fi_text)
    total = 0
    new_count = 0
    modified_count = 0
    for cells in rows:
        if len(cells) < 2:
            continue
        action = cells[1].strip() if len(cells) > 1 else ""
        if re.search(r"Create|New|create|new", action):
            new_count += 1
            total += 1
        elif re.search(r"Modify|modify|Update|update", action):
            modified_count += 1
            total += 1
        elif re.search(r"Verify|verify", action):
            # Verify rows are confirm-only — count in total, not modified.
            total += 1
        else:
            total += 1
    return total, new_count, modified_count


def _count_risks(plan_content: str) -> int:
    """Return risk count from the Risk Assessment table.

    Returns 0 if no Risk Assessment table is found.
    """
    risk_match = re.search(
        r"###?\s+Risk Assessment\b", plan_content, re.IGNORECASE
    )
    if not risk_match:
        # Also try "## Risk" heading variant.
        risk_match = re.search(
            r"##\s+Risk", plan_content, re.IGNORECASE
        )
    if not risk_match:
        return 0

    # Extract text to next heading of any level >= ##. Using ^#{2,}\s+
    # stops at sibling ### headings (e.g., ### Dependencies) so their
    # tables don't leak into the Risk Assessment count.
    next_h = re.search(
        r"^#{2,}\s+", plan_content[risk_match.end():], re.MULTILINE
    )
    if next_h:
        risk_text = plan_content[risk_match.start():risk_match.end() + next_h.start()]
    else:
        risk_text = plan_content[risk_match.start():]

    rows = _parse_table_rows(risk_text)
    return len(rows)


# ---------------------------------------------------------------------------
# Subcommand: render-breakdown-handoff
# ---------------------------------------------------------------------------


def cmd_render_breakdown_handoff(args) -> int:
    """Emit the Phase 4 manual handoff block targeting /breakdown."""
    spec_path = args.spec_path
    plan_path = args.plan_path

    spec_content = _read_file(spec_path)
    if spec_content is None:
        sys.stderr.write(
            "plan_helper: cannot read spec: {0}\n".format(spec_path)
        )
        return 2

    plan_content = _read_file(plan_path)
    if plan_content is None:
        sys.stderr.write(
            "plan_helper: cannot read plan: {0}\n".format(plan_path)
        )
        return 2

    total_acs, subsections = _count_acs(spec_content)
    total_files, new_files, modified_files = _count_file_impact(plan_content)
    risk_count = _count_risks(plan_content)

    output = (
        "## Manual next step — run /breakdown\n"
        "\n"
        "The plan is approved. No automated handoff exists — restart Claude Code "
        "(exit and relaunch the CLI/app so any newly-installed command is picked up), "
        "then run:\n"
        "\n"
        "```\n"
        "/breakdown {plan_path}\n"
        "```\n"
        "\n"
        "**Plan status**: Draft — plan stays Draft until `/breakdown` runs "
        "(forward reference: `/breakdown` spec not yet ported into this framework).\n"
        "**Spec ACs**: {total_acs} criteria across {subsections} subsections\n"
        "**Plan file impact**: {total_files} files ({new_files} new, "
        "{modified_files} modified)\n"
        "**Plan risks**: {risk_count}\n"
        "\n"
        "Phase 1.5 coverage: every spec §3–§9 finding accounted for in the plan "
        "(Phase 1.5 enumeration; Phase 2.5 AC-level cross-check).\n"
    ).format(
        plan_path=plan_path,
        total_acs=total_acs,
        subsections=subsections,
        total_files=total_files,
        new_files=new_files,
        modified_files=modified_files,
        risk_count=risk_count,
    )

    sys.stdout.write(output)
    return 0


# ---------------------------------------------------------------------------
# CLI wiring.
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plan_helper",
        description=(
            "Structural emission helper for the /plan slash command. "
            "Helper owns shape; LLM composes values."
        ),
    )
    sub = parser.add_subparsers(dest="subcommand")

    # pick-spec
    sp = sub.add_parser(
        "pick-spec",
        help="Resolve which spec to plan against (auto-picks by mtime if no path given).",
    )
    sp.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Explicit path to a spec.md (optional).",
    )
    sp.set_defaults(func=cmd_pick_spec)

    # render-pick-summary
    sp = sub.add_parser(
        "render-pick-summary",
        help="Print a 5-line deterministic spec summary block.",
    )
    sp.add_argument("spec_path", help="Path to spec.md.")
    sp.set_defaults(func=cmd_render_pick_summary)

    # list-specs
    sp = sub.add_parser(
        "list-specs",
        help="List all specs/*/spec.md sorted by mtime desc.",
    )
    sp.set_defaults(func=cmd_list_specs)

    # check-status-and-flip
    sp = sub.add_parser(
        "check-status-and-flip",
        help="Flip spec Status from Draft to Approved (idempotent).",
    )
    sp.add_argument("spec_path", help="Path to spec.md.")
    sp.set_defaults(func=cmd_check_status_and_flip)

    # render-findings-from-spec
    sp = sub.add_parser(
        "render-findings-from-spec",
        help="Emit Phase 1.5 findings skeleton from spec §3-§9.",
    )
    sp.add_argument("spec_path", help="Path to spec.md.")
    sp.set_defaults(func=cmd_render_findings_from_spec)

    # render-breakdown-handoff
    sp = sub.add_parser(
        "render-breakdown-handoff",
        help="Emit Phase 4 manual handoff block targeting /breakdown.",
    )
    sp.add_argument("spec_path", help="Path to spec.md.")
    sp.add_argument("plan_path", help="Path to plan.md.")
    sp.set_defaults(func=cmd_render_breakdown_handoff)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
