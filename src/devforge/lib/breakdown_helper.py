"""breakdown_helper — structural emission helper for the /breakdown slash command.

Subcommands:

  pick-plan [path]
      Resolve which plan.md to break down.
      With path: validate the file exists, is a file (not dir), and that
                 its basename is exactly 'plan.md'. Print its absolute
                 resolved path on stdout, exit 0.
      No path:   glob specs/*/plan.md under cwd, pick highest mtime,
                 print its absolute path, exit 0.
      Exit 2 on any failure.

  render-pick-summary <plan-path>
      Print a deterministic 5-line preview block the LLM copies verbatim.
      Lines emitted:
        **Plan**: <abs-path>
        **Status**: <Draft|Approved|Complete|unknown>
        **File-impact rows**: <N>
        **Risk rows**: <M>
        **Last modified**: <YYYY-MM-DD>
      Exit 0; exit 2 if file missing.

  list-plans
      List all specs/*/plan.md under cwd sorted by mtime desc.
      One line per plan: <index>) <relative-path> [Status: <X>]
      Exit 0 (even if empty); exit 2 if specs/ dir missing.

  check-status-and-flip <plan-path>
      Read the **Status**: line from plan frontmatter and act:
        Draft     -> rewrite to Approved, print "flipped"
        Approved  -> no change, print "already-approved"
        Complete  -> no change, print "complete"
        missing   -> insert after **Date**: line, print "inserted"
        unknown   -> no change, print "unknown-status:<value>"
        malformed -> exit 2 (no Date or Status line at all)
      Writes are atomic (tempfile.mkstemp + os.replace).
      Exit 0 on all success paths.

  read-plan-handoff <plan-path>
      CONSUMER: locate the sibling plan-handoff.json in the same directory.
      Sibling absent: print "no-handoff" on stdout, exit 0.
      Sibling present: validate handoff_kind=="plan" and schema_version=="1.0".
        Valid: render a "## Upstream plan seeds" block to stdout, exit 0.
        Invalid: exit 2 with message on stderr.
      The rendered block surfaces: Layer Map, File Impact, Key Design
      Decisions, Dependencies, Risks. Empty sub-sections render as _(none)_.

  verify-agent-roster <tasks-dir> [--agents-dir <path>]
      Verify that every task's resolved **Agent**: value exists in the
      installed roster (*.md stems in --agents-dir, default .claude/agents).
      Skips tasks with empty or placeholder agents (those are finalize-handoff's
      concern). Fails closed when the roster directory is absent or empty.
      Exit 0: all assigned agents are installed (or all agents are placeholders).
              Prints "agent-roster: ok (N tasks, M agents installed)".
      Exit 2: roster absent/empty, task files missing, or at least one offender.
              Prints a "## Agent roster findings" block to stdout on offenders.

  verify-manifest-present <tasks-dir> [--reference-path <path>] [--manifest-path <path>] [--scope-only]
      Assert design/reference.html present => specs/[feature]/design-manifest.json
      present AND valid (plan 42 WI-1 — the 4th PHASE 3.5 integrity gate).
      Exit 0: reference absent (non-UI feature) or manifest present-and-valid.
      Exit 2: reference present but manifest absent, unreadable, or invalid.
      Exit 3 (--scope-only): reference absent; Exit 0 (--scope-only): reference present.
      Workspace root is cwd; feature-dir is parent of tasks-dir.

  verify-contract-chain <tasks-dir>
      Walk every *.md task file in <tasks-dir> (ignoring README.md). Parse
      each task's ### Expects and ### Produces bullet lists, skipping
      placeholder bullets (bracketed lines like [precondition: ...]).
      Normalize bullets and check chain integrity:
        - Orphan Produces: a Produces item no other task Expects.
        - Unsatisfied Expects: an Expects item no task Produces.
      Both are advisory findings (may map to spec ACs or existing-codebase
      state not visible here). Output "contract-chain: ok (N tasks, P
      produces, E expects)" on stdout and exit 0 when clean. Print a
      "## Contract chain findings" block to stdout and exit 2 when findings
      exist. Exit 2 with stderr message when no task files found.

  verify-ac-coverage <tasks-dir> <spec-path>
      Parse spec §5 ACs (reusing _parse_acs). Parse every task's
      **Spec criteria**: line. Report uncovered ACs. Exit 0 when all
      covered (or when spec has zero ACs). Exit 2 with stderr when
      tasks-dir or spec unreadable/empty.

  verify-property-coverage <tasks-dir> [--plan-handoff <path>]
      Verify that every pure-builder target declared in the sibling
      plan-handoff.json (breakdown_seeds.pure_builder_targets, plan 66 WI-1)
      is covered by at least one task's '**Property targets**:' line.
      --plan-handoff defaults to <tasks-dir's parent>/plan-handoff.json.
      On a missing/unreadable/malformed handoff, falls back to sibling
      plan.md via _plan_declares_pure_builder_targets (the SAME criterion
      the producer uses: heading present AND >=1 non-placeholder row, not
      just the heading alone): no real target declared (heading absent,
      plan.md itself absent, or heading present but every row is a
      placeholder) => the feature never declared targets => skip, exit 0
      (matches /breakdown PHASE 0a.5's tolerance for a missing
      plan-handoff.json); a REAL target declared => fails closed, exit 2,
      since a declared-but-unverifiable target must not silently evaporate.
      Exit 0: no declared targets (skip — no task files required; covers
              both an empty pure_builder_targets list AND a missing/
              malformed handoff with no real pure-builder target declared
              in plan.md), or all declared targets covered. Prints
              "property-coverage: skip (no declared pure-builder targets)",
              "property-coverage: skip (no plan-handoff.json and no
              pure-builder targets declared in plan.md)", or
              "property-coverage: ok (N targets, M covering tasks)".
      Exit 2: a missing/malformed handoff paired with at least one real
              pure-builder target declared in plan.md (remedy printed), no
              task files found (when targets ARE declared), or at least one
              uncovered target.
              Prints a "## Property coverage findings" block on offenders.

  verify-dead-code-coverage <tasks-dir> [--plan-handoff <path>]
      Verify that every change-induced dead-code row declared in the
      sibling plan-handoff.json (breakdown_seeds.dead_code_rows, plan 71
      D9) is covered by EXACTLY ONE task's '**Dead code removal**:' field
      (semicolon-separated anchor tokens; see cmd_render_task_file's
      --dead-code-removal docstring). Mirrors verify-property-coverage's
      structure + never-declared-vs-declared-but-unverifiable asymmetry
      EXACTLY (fallback to sibling plan.md via _plan_declares_dead_code_rows
      on any handoff error), plus a NEW duplicate-assignment check: a row
      claimed by 2+ tasks is as much a violation as zero (D7 requires
      exactly one owning task).
      --plan-handoff defaults to <tasks-dir's parent>/plan-handoff.json.
      Exit 0: no declared rows (skip), or every declared row covered by
              exactly one task. Prints "dead-code-coverage: skip (no
              declared dead-code rows)", "dead-code-coverage: skip (no
              plan-handoff.json and no change-induced dead code declared in
              plan.md)", or "dead-code-coverage: ok (N rows, M covering
              tasks)".
      Exit 2: a missing/malformed handoff paired with at least one real
              dead-code row declared in plan.md (remedy printed), no task
              files found (when rows ARE declared), at least one uncovered
              row, or at least one row claimed by 2+ tasks. Prints a
              "## Dead-code coverage findings" block naming both kinds.

  finalize-handoff <plan-path> [--completed-at ISO] [--agents-dir <path>]
      PRODUCER: parse tasks/*.md (+ tasks/README.md) into a schema-validated
      Breakdown record and write <plan-dir>/breakdown-handoff.json (sibling
      to plan.md). Fields parsed per task file: number, title, agent,
      depends_on, blocks, ac_addressed, doc_refs, review_checkpoint,
      touched_files, expects, produces. README fields: dependency_graph,
      additions. Provenance: sibling plan-handoff.json (kind='plan') sets
      upstream fields; sibling spec.md sets spec_path.
      After per-task parsing, validates all resolved agent names against the
      installed roster in --agents-dir (default .claude/agents). Fails closed
      when the roster is empty/absent; exits 2 naming offenders when any
      assigned agent is not installed. Also chokepoints property coverage
      (plan 66 WI-1): when a sibling plan-handoff.json declares
      breakdown_seeds.pure_builder_targets, every declared target must be
      covered by a task's '**Property targets**:' line; a missing/malformed
      sibling handoff is silently skipped here (see verify-property-coverage
      for the strict fail-closed arm). Carries + chokepoints dead-code rows
      (plan 71 D8(b)/D9): copies breakdown_seeds.dead_code_rows into the
      written handoff verbatim (WARNs on stderr, non-fatal, if the sibling
      is malformed); fails closed if plan.md declares change-induced dead
      code the sibling carries none of; and, mirroring the pure-builder
      chokepoint above, fails closed if a sibling-declared dead-code row is
      not covered by EXACTLY ONE task's '**Dead code removal**:' field
      (see verify-dead-code-coverage for the strict fail-closed arm on
      handoff errors).
      Exit 0 + prints written path on success.
      Exit 2: plan.md/tasks missing or empty, placeholder **Agent**: detected
              (names the offending file), roster absent or agent not installed,
              schema validation failure, an uncovered pure-builder target,
              plan.md declaring dead code the sibling handoff carries none
              of, or a sibling-declared dead-code row left uncovered/
              double-covered by the task files.
      Exit 1: I/O write failure.
      Idempotent: re-running overwrites the previous breakdown-handoff.json.

  render-implement-handoff <plan-path>
      Emit a deterministic manual next-step block the LLM copies verbatim,
      targeting /implement. Reads tasks/*.md to determine task count and
      first task number. Includes a restart-Claude-Code reminder.
      Exit 0; exit 2 if plan.md or tasks-dir missing/empty.

Exit codes:
  0 — success
  1 — reserved for I/O failures (write errors)
  2 — usage error / not-found / malformed input / violations found

Stdout is the canonical channel for output tokens; stderr for errors.
No state file — every subcommand re-reads input files.
Stdlib only. Python 3.8+.
"""

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Error helper.
# ---------------------------------------------------------------------------


def _die(msg: str, code: int = 2) -> int:
    """Write msg to stderr and return code."""
    sys.stderr.write("breakdown_helper: " + msg + "\n")
    return code


# ---------------------------------------------------------------------------
# File utilities.
# ---------------------------------------------------------------------------


def _read_file(path: str) -> Optional[str]:
    """Return file contents as string, or None if unreadable."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, IOError):
        return None


def _file_mtime_iso(path: str) -> str:
    """Return file mtime as YYYY-MM-DD."""
    ts = os.path.getmtime(path)
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Frontmatter parsing helpers.
# ---------------------------------------------------------------------------

# IMPORTANT: uses [ \t]* (horizontal whitespace only), NOT \s*.  The status
# value MUST appear on the same line as the **Status**: marker.  Using \s*
# would allow the match to bleed across a blank line and capture a value from
# the next non-empty line in a malformed plan (e.g. "**Status**:\n\nDraft\n"
# would wrongly yield "Draft").
_STATUS_PATTERN = re.compile(r"^\*\*Status\*\*:[ \t]*(.+)$", re.MULTILINE)
_DATE_PATTERN = re.compile(r"^\*\*Date\*\*:\s*(.+)$", re.MULTILINE)


def _parse_frontmatter_field(content: str, pattern: "re.Pattern[str]") -> Optional[str]:
    """Extract the value of a frontmatter field."""
    m = pattern.search(content)
    if not m:
        return None
    return m.group(1).strip()


# ---------------------------------------------------------------------------
# Plan-section parsing helpers (reused for render-pick-summary).
# ---------------------------------------------------------------------------


def _parse_table_rows(sec_text: str) -> List[List[str]]:
    """Return list of non-header, non-separator table rows as cell lists."""
    rows = []
    header_seen = False
    for line in sec_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        # Check separator row: only |, -, spaces, colon.
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


_PLACEHOLDER_CELL_RE = re.compile(
    r"^\s*(?:"
    r"\[.*\]"           # any [bracketed] placeholder
    r"|_\(none\)_"      # _(none)_ markdown italic
    r"|\(none\)"        # bare (none)
    r")\s*$"
)


def _is_placeholder_cell(text: str) -> bool:
    """Return True if text is a placeholder row that should be skipped."""
    return bool(_PLACEHOLDER_CELL_RE.match(text))


def _extract_plan_section(content: str, heading_pattern: "re.Pattern[str]") -> str:
    """Extract text of the section whose heading matches heading_pattern.

    Returns text from the heading line to the next ## or ### heading or EOF.
    Returns empty string when the heading is not found.
    """
    m = heading_pattern.search(content)
    if not m:
        return ""
    start = m.start()
    next_h = re.compile(r"^#{2,}\s+", re.MULTILINE)
    m_next = next_h.search(content, m.end())
    if m_next:
        return content[start:m_next.start()]
    return content[start:]


def _count_file_impact_rows(plan_content: str) -> int:
    """Return count of non-placeholder data rows from the File Impact table."""
    pat = re.compile(r"^###\s+File Impact\b", re.MULTILINE | re.IGNORECASE)
    section = _extract_plan_section(plan_content, pat)
    if not section:
        return 0
    rows = _parse_table_rows(section)
    count = 0
    for cells in rows:
        if cells and not _is_placeholder_cell(cells[0]):
            count += 1
    return count


def _count_risk_rows(plan_content: str) -> int:
    """Return count of non-placeholder data rows from the Risk Assessment table."""
    pat = re.compile(r"^###?\s+Risk Assessment\b", re.MULTILINE | re.IGNORECASE)
    section = _extract_plan_section(plan_content, pat)
    if not section:
        pat = re.compile(r"^##\s+Risk\b", re.MULTILINE | re.IGNORECASE)
        section = _extract_plan_section(plan_content, pat)
    if not section:
        return 0
    rows = _parse_table_rows(section)
    count = 0
    for cells in rows:
        if cells and not _is_placeholder_cell(cells[0]):
            count += 1
    return count


# ---------------------------------------------------------------------------
# Plan globbing helpers.
# ---------------------------------------------------------------------------


def _glob_plans(cwd: str) -> List[str]:
    """Return list of absolute paths to specs/*/plan.md under cwd."""
    specs_dir = Path(cwd) / "specs"
    if not specs_dir.is_dir():
        return []
    result = []
    for sub in specs_dir.iterdir():
        candidate = sub / "plan.md"
        if candidate.is_file():
            result.append(str(candidate.resolve()))
    return result


# ---------------------------------------------------------------------------
# Subcommand: pick-plan
# ---------------------------------------------------------------------------


def cmd_pick_plan(args: argparse.Namespace) -> int:
    """Resolve the plan path and print it to stdout."""
    plan_path_arg = getattr(args, "path", None)

    if plan_path_arg:
        # Explicit path given.
        resolved = Path(plan_path_arg)
        if not resolved.is_absolute():
            resolved = Path.cwd() / resolved
        # Must be a file, not a dir.
        if resolved.is_dir():
            return _die(
                "pick-plan: {0} is a directory, not a plan.md file".format(plan_path_arg)
            )
        if not resolved.is_file():
            return _die(
                "pick-plan: plan not found: {0}".format(plan_path_arg)
            )
        # Basename must be exactly 'plan.md'.
        if resolved.name != "plan.md":
            return _die(
                "pick-plan: file basename must be 'plan.md', "
                "got {0!r}".format(resolved.name)
            )
        sys.stdout.write(str(resolved.resolve()) + "\n")
        return 0

    # Auto-pick: find highest-mtime plan.md under specs/.
    cwd = str(Path.cwd())
    specs_dir = Path(cwd) / "specs"
    if not specs_dir.is_dir():
        return _die(
            "pick-plan: no plan found under specs/; run /devforge:plan first"
        )

    all_paths = _glob_plans(cwd)
    if not all_paths:
        return _die(
            "pick-plan: no plan found under specs/; run /devforge:plan first"
        )

    # Pick highest mtime.
    best = max(all_paths, key=lambda p: os.path.getmtime(p))
    sys.stdout.write(best + "\n")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: render-pick-summary
# ---------------------------------------------------------------------------


def cmd_render_pick_summary(args: argparse.Namespace) -> int:
    """Print a 5-line deterministic pick-summary block."""
    plan_path = args.plan_path
    content = _read_file(plan_path)
    if content is None:
        return _die("cannot read plan: {0}".format(plan_path))

    status = _parse_frontmatter_field(content, _STATUS_PATTERN) or "unknown"
    fi_rows = _count_file_impact_rows(content)
    risk_rows = _count_risk_rows(content)
    last_modified = _file_mtime_iso(plan_path)

    sys.stdout.write("**Plan**: {0}\n".format(plan_path))
    sys.stdout.write("**Status**: {0}\n".format(status))
    sys.stdout.write("**File-impact rows**: {0}\n".format(fi_rows))
    sys.stdout.write("**Risk rows**: {0}\n".format(risk_rows))
    sys.stdout.write("**Last modified**: {0}\n".format(last_modified))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: list-plans
# ---------------------------------------------------------------------------


def cmd_list_plans(args: argparse.Namespace) -> int:
    """List all plans sorted by mtime desc."""
    cwd = str(Path.cwd())
    specs_dir = Path(cwd) / "specs"
    if not specs_dir.is_dir():
        return _die("specs/ directory not found under cwd")

    all_paths = _glob_plans(cwd)
    if not all_paths:
        # Empty dir is valid; emit nothing.
        return 0

    # Sort by mtime descending.
    sorted_paths = sorted(all_paths, key=lambda p: os.path.getmtime(p), reverse=True)

    for idx, abs_path in enumerate(sorted_paths, start=1):
        content = _read_file(abs_path)
        if content is None:
            status = "unknown"
        else:
            status = _parse_frontmatter_field(content, _STATUS_PATTERN) or "unknown"

        # Relative path from cwd.
        try:
            rel_path = str(Path(abs_path).relative_to(Path(cwd)))
        except ValueError:
            rel_path = abs_path

        sys.stdout.write(
            "{0}) {1} [Status: {2}]\n".format(idx, rel_path, status)
        )
    return 0


# ---------------------------------------------------------------------------
# Atomic write helper.
# ---------------------------------------------------------------------------


def _atomic_write(path: str, content: str) -> None:
    """Write content to path atomically using tempfile + os.replace."""
    target = Path(path)
    fd, tmp_path = tempfile.mkstemp(
        prefix="breakdown-status-",
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


# ---------------------------------------------------------------------------
# Subcommand: check-status-and-flip
# ---------------------------------------------------------------------------


def cmd_check_status_and_flip(args: argparse.Namespace) -> int:
    """Read **Status**: line and flip Draft -> Approved as needed."""
    plan_path = args.plan_path
    content = _read_file(plan_path)
    if content is None:
        return _die("cannot read plan: {0}".format(plan_path))

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
                _atomic_write(plan_path, new_content)
            except OSError as err:
                sys.stderr.write(
                    "breakdown_helper: cannot write plan: {0}\n".format(err)
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
        return _die(
            "no Date or Status frontmatter line found; plan malformed"
        )

    # Insert **Status**: Approved immediately after the **Date**: line.
    insert_pos = date_match.end()
    new_content = (
        content[:insert_pos]
        + "\n**Status**: Approved"
        + content[insert_pos:]
    )
    try:
        _atomic_write(plan_path, new_content)
    except OSError as err:
        sys.stderr.write(
            "breakdown_helper: cannot write plan: {0}\n".format(err)
        )
        return 1
    sys.stdout.write("inserted\n")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: read-plan-handoff
# ---------------------------------------------------------------------------


# Constants imported from _breakdown (for comparison values).
# Import lazily inside the command to keep the module importable without
# the lib directory on sys.path.


def _render_plan_handoff_block(d: Dict[str, Any]) -> str:
    """Render the '## Upstream plan seeds' block from a plan-handoff dict.

    Surfaces breakdown_seeds: Layer Map, File Impact, Key Design Decisions,
    Dependencies, Risks. Empty sub-sections render as '_(none)_'.

    When breakdown_seeds.pure_builder_targets is present and non-empty, a
    trailing "Pure-Builder Targets (property-test lane)" sub-block is
    appended. Absent or empty (old producer JSON, or no architect-named
    targets) renders nothing extra -- byte-identical to the pre-change
    output (back-compat: `.get("pure_builder_targets") or []`).
    """
    seeds = d.get("breakdown_seeds") or {}

    # --- Layer Map ---
    layer_map = seeds.get("layer_map") or []
    if layer_map:
        lm_lines = []
        for row in layer_map:
            if isinstance(row, dict):
                lm_lines.append(
                    "- {0} | {1} | {2}".format(
                        row.get("layer", "?"),
                        row.get("what", "?"),
                        row.get("files", ""),
                    )
                )
        lm_block = "\n".join(lm_lines) if lm_lines else "_(none)_"
    else:
        lm_block = "_(none)_"

    # --- File Impact ---
    file_impact = seeds.get("file_impact") or []
    if file_impact:
        fi_lines = []
        for row in file_impact:
            if isinstance(row, dict):
                fi_lines.append(
                    "- {0} | {1} | {2}".format(
                        row.get("file", "?"),
                        row.get("action", "?"),
                        row.get("what_changes", ""),
                    )
                )
        fi_block = "\n".join(fi_lines) if fi_lines else "_(none)_"
    else:
        fi_block = "_(none)_"

    # --- Key Design Decisions ---
    decisions = seeds.get("key_design_decisions") or []
    if decisions:
        dec_lines = []
        for row in decisions:
            if isinstance(row, dict):
                dec_lines.append(
                    "- {0} → {1}".format(
                        row.get("decision", "?"),
                        row.get("chosen_approach", "?"),
                    )
                )
        dec_block = "\n".join(dec_lines) if dec_lines else "_(none)_"
    else:
        dec_block = "_(none)_"

    # --- Dependencies ---
    # plan_helper._parse_dependencies stores lines verbatim (already include
    # the leading "- " bullet from the source markdown).  Conditionally add
    # a bullet only when the stored line does not already have one, so we
    # never produce the double-bullet "- - text" form.
    dependencies = seeds.get("dependencies") or []
    if dependencies:
        dep_lines = [
            dep if dep.startswith("- ") else "- {0}".format(dep)
            for dep in dependencies
            if dep
        ]
        dep_block = "\n".join(dep_lines) if dep_lines else "_(none)_"
    else:
        dep_block = "_(none)_"

    # --- Risks ---
    risks = seeds.get("risks") or []
    if risks:
        risk_lines = []
        for row in risks:
            if isinstance(row, dict):
                risk_lines.append(
                    "- {0} (likelihood: {1}, impact: {2})".format(
                        row.get("risk", "?"),
                        row.get("likelihood", "?"),
                        row.get("impact", "?"),
                    )
                )
        risk_block = "\n".join(risk_lines) if risk_lines else "_(none)_"
    else:
        risk_block = "_(none)_"

    # --- Pure-Builder Targets (optional; back-compat via `or []`) ---
    pure_builder_targets = seeds.get("pure_builder_targets") or []
    pbt_lines = []
    for row in pure_builder_targets:
        if isinstance(row, dict):
            pbt_lines.append(
                "- {0} ({1}) — {2}".format(
                    row.get("target", "?"),
                    row.get("file", "?"),
                    row.get("why", ""),
                )
            )
    pbt_section = ""
    if pbt_lines:
        pbt_section = (
            "\n"
            "### Pure-Builder Targets (property-test lane)\n"
            "{0}\n"
        ).format("\n".join(pbt_lines))

    return (
        "## Upstream plan seeds\n"
        "\n"
        "### Layer Map\n"
        "{lm_block}\n"
        "\n"
        "### File Impact\n"
        "{fi_block}\n"
        "\n"
        "### Key Design Decisions\n"
        "{dec_block}\n"
        "\n"
        "### Dependencies\n"
        "{dep_block}\n"
        "\n"
        "### Risks\n"
        "{risk_block}\n"
        "{pbt_section}"
    ).format(
        lm_block=lm_block,
        fi_block=fi_block,
        dec_block=dec_block,
        dep_block=dep_block,
        risk_block=risk_block,
        pbt_section=pbt_section,
    )


def cmd_read_plan_handoff(args: argparse.Namespace) -> int:
    """Load sibling plan-handoff.json, validate, render seeds block.

    Sibling absent: print "no-handoff", exit 0.
    Sibling present + valid: render ## Upstream plan seeds block, exit 0.
    Sibling present + invalid: exit 2.

    The sibling is plan_path.parent / "plan-handoff.json".
    """
    # Ensure lib dir is on path so _plan is importable.
    _lib_dir = Path(__file__).resolve().parent
    if str(_lib_dir) not in sys.path:
        sys.path.insert(0, str(_lib_dir))

    # Import constants from the PLAN producer schema — this command is the
    # consumer of plan-handoff.json, so it validates against plan's constants.
    from _plan.handoff_schema import HANDOFF_KIND as _PLAN_HANDOFF_KIND
    from _plan.handoff_schema import SCHEMA_VERSION as _PLAN_SCHEMA_VERSION

    plan_path_raw = args.plan_path
    plan_path = Path(plan_path_raw)
    if not plan_path.is_absolute():
        plan_path = Path.cwd() / plan_path
    plan_path = plan_path.resolve()

    if not plan_path.is_file():
        return _die("plan not found: {0}".format(plan_path_raw))

    sibling = plan_path.parent / "plan-handoff.json"
    if not sibling.exists():
        sys.stdout.write("no-handoff\n")
        return 0

    # Sibling present — parse.
    try:
        raw_text = sibling.read_text(encoding="utf-8")
        d = json.loads(raw_text)
    except (OSError, IOError, json.JSONDecodeError) as err:
        return _die(
            "plan-handoff.json at {0} is malformed: {1}".format(sibling, err)
        )

    if not isinstance(d, dict):
        return _die(
            "malformed or wrong-kind plan handoff: root is not a JSON object"
        )

    # Validate kind — the sibling file is plan-handoff.json produced by
    # plan_helper; its handoff_kind constant is "plan".
    if d.get("handoff_kind") != _PLAN_HANDOFF_KIND:
        return _die(
            "plan handoff has wrong kind: "
            "expected handoff_kind={0!r}, got {1!r}".format(
                _PLAN_HANDOFF_KIND, d.get("handoff_kind")
            )
        )

    # Validate schema_version.
    if d.get("schema_version") != _PLAN_SCHEMA_VERSION:
        return _die(
            "plan handoff has wrong schema_version: "
            "expected schema_version={0!r}, got {1!r}".format(
                _PLAN_SCHEMA_VERSION, d.get("schema_version")
            )
        )

    block = _render_plan_handoff_block(d)
    sys.stdout.write(block)
    return 0


# ---------------------------------------------------------------------------
# AC parsing helpers (shared between render-findings-from-plan and tests).
# ---------------------------------------------------------------------------

# AC line pattern identical to plan_helper: "- [x/X/ ] **AC-N**: ..."
_AC_LINE_PATTERN = re.compile(
    r"^\s*-\s+\[[xX ]\]\s+\*\*AC-(\d+)\*\*(?:[^:]*)?:\s*(.+)$",
    re.MULTILINE,
)

# Section 5 extractor: find "## 5." heading and return text up to next "## "
_SEC5_START = re.compile(r"^##\s+5\.\s+", re.MULTILINE)


def _extract_ac_section(spec_content: str) -> str:
    """Return text of the '## 5. Acceptance Criteria' section, or empty string."""
    m = _SEC5_START.search(spec_content)
    if not m:
        return ""
    next_h2 = re.compile(r"^##\s+", re.MULTILINE)
    m_next = next_h2.search(spec_content, m.end())
    if m_next:
        return spec_content[m.start():m_next.start()]
    return spec_content[m.start():]


def _parse_acs(spec_content: str) -> List[Tuple[str, str]]:
    """Return list of (ac_number_str, ac_text_snippet) from spec §5.

    Matches lines of the form '- [ ] **AC-N**: text' (any checkbox state).
    """
    ac_section = _extract_ac_section(spec_content)
    return _AC_LINE_PATTERN.findall(ac_section)


def _truncate(text: str, max_len: int = 60) -> str:
    """Truncate text to max_len chars with '…' suffix if needed."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


# ---------------------------------------------------------------------------
# Plan-section row extractors for render-findings-from-plan.
# ---------------------------------------------------------------------------


def _extract_file_impact_rows(plan_content: str) -> List[Tuple[str, str]]:
    """Return list of (file, action) from the ### File Impact table.

    Skips placeholder rows. Returns empty list if section absent.
    """
    pat = re.compile(r"^###\s+File Impact\b", re.MULTILINE | re.IGNORECASE)
    section = _extract_plan_section(plan_content, pat)
    if not section:
        return []
    rows = _parse_table_rows(section)
    result = []
    for cells in rows:
        if not cells or _is_placeholder_cell(cells[0]):
            continue
        file_name = cells[0] if cells else "?"
        action = cells[1] if len(cells) > 1 else "?"
        result.append((file_name, action))
    return result


def _extract_layer_map_rows(plan_content: str) -> List[Tuple[str, str]]:
    """Return list of (layer, what) from the ### Layer Map table.

    Skips placeholder rows. Returns empty list if section absent.
    """
    pat = re.compile(r"^###\s+Layer Map\b", re.MULTILINE | re.IGNORECASE)
    section = _extract_plan_section(plan_content, pat)
    if not section:
        return []
    rows = _parse_table_rows(section)
    result = []
    for cells in rows:
        if not cells or _is_placeholder_cell(cells[0]):
            continue
        layer = cells[0] if cells else "?"
        what = cells[1] if len(cells) > 1 else "?"
        result.append((layer, what))
    return result


# ---------------------------------------------------------------------------
# Subcommand: render-findings-from-plan
# ---------------------------------------------------------------------------

# Verdict values for the consultation table (mirror plan_helper exactly).
_CONSULT_VERDICT_VALUES = frozenset({"accepted", "modified", "rejected", "no-response"})


def cmd_render_findings_from_plan(args: argparse.Namespace) -> int:
    """Emit the findings skeleton from a plan (and optionally spec) for /breakdown.

    For each ### File Impact row: emits a line with [TASK COVERAGE: ?].
    For each ### Layer Map row: emits a line with [TASK COVERAGE: ?].
    For each AC in spec §5 (if spec-path given): emits AC-N with [ADDRESSED BY: ?].
    Missing plan → exit 2.
    """
    plan_path = args.plan_path
    spec_path = getattr(args, "spec_path", None)

    plan_content = _read_file(plan_path)
    if plan_content is None:
        return _die("cannot read plan: {0}".format(plan_path))

    output_lines: List[str] = ["## Findings from Plan", ""]
    output_lines.append(
        "_Fill in each `?` marker with your task-number decision "
        "before writing any task files._"
    )
    output_lines.append("")

    # --- File Impact ---
    fi_rows = _extract_file_impact_rows(plan_content)
    output_lines.append("### File Impact")
    output_lines.append(
        "_For each file row, assign which task covers the change "
        "(replace `?` with the task number or `N/A`)._"
    )
    if fi_rows:
        for file_name, action in fi_rows:
            output_lines.append(
                "- {0} ({1}) [TASK COVERAGE: ?]".format(file_name, action)
            )
    else:
        output_lines.append("_(none — no File Impact table found in plan)_")
    output_lines.append("")

    # --- Layer Map ---
    lm_rows = _extract_layer_map_rows(plan_content)
    output_lines.append("### Layer Map")
    output_lines.append(
        "_For each layer row, assign which task covers it "
        "(replace `?` with the task number or `N/A`)._"
    )
    if lm_rows:
        for layer, what in lm_rows:
            output_lines.append(
                "- {0}: {1} [TASK COVERAGE: ?]".format(layer, what)
            )
    else:
        output_lines.append("_(none — no Layer Map table found in plan)_")
    output_lines.append("")

    # --- AC Coverage ---
    output_lines.append("### AC Coverage")
    if spec_path:
        spec_content = _read_file(spec_path)
        if spec_content is None:
            output_lines.append(
                "_(spec not readable: {0} — AC coverage check deferred to verify-ac-coverage)_".format(
                    spec_path
                )
            )
        else:
            acs = _parse_acs(spec_content)
            if acs:
                output_lines.append(
                    "_For each AC, assign which task addresses it "
                    "(replace `?` with the task number or `N/A`)._"
                )
                for ac_num, ac_text in acs:
                    output_lines.append(
                        "- AC-{0}: {1} [ADDRESSED BY: ?]".format(
                            ac_num, _truncate(ac_text)
                        )
                    )
            else:
                output_lines.append("_(no ACs found in spec §5)_")
    else:
        output_lines.append(
            "_(no spec provided — AC coverage check deferred to verify-ac-coverage)_"
        )

    sys.stdout.write("\n".join(output_lines) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: render-task-file
# ---------------------------------------------------------------------------

# The four helper-owned Done-When lines (verbatim from storage-rules.md).
_DONE_WHEN_FIXED_LINES = [
    "No debug artifacts left in changed files",
    "Type checker passes on changed files (see Development Commands section)",
    "Linter passes on changed files (see Development Commands section)",
    "No new secrets or credentials in code",
]


def cmd_render_task_file(args: argparse.Namespace) -> int:
    """Emit the exact task-file skeleton from storage-rules.md §Task File Format.

    All sections and the four fixed Done-When lines are helper-owned.
    The LLM fills in placeholders. Exit 0 always (pure emitter).

    --property-targets (plan 66 WI-1): when passed and non-empty (after
    stripping), a '**Property targets**:' line is emitted immediately after
    the '**Context docs**:' line, carrying the value verbatim (stripped).
    When absent (or empty after stripping), output is BYTE-IDENTICAL to the
    pre-flag skeleton -- no line is emitted, no back-compat branch needed
    since this is a pure additive emitter flag.

    --dead-code-removal (plan 71 D7/D8(b), tightened by the coverage-gate
    hardening): mirrors --property-targets' EMISSION mechanics exactly
    (placement, stripping, empty-omitted) but carries a DIFFERENT list
    format -- a semicolon-separated list of literal anchor tokens matching
    breakdown_seeds.dead_code_rows[].anchor_token character-for-character,
    NOT free-text prose. Semicolon (not comma) is the separator because
    anchor tokens are literal code fragments that commonly contain commas
    (e.g. multi-arg call-site literals); verify-dead-code-coverage parses
    this field by splitting on ';' and stripping each segment. An anchor
    token must not itself contain a semicolon (no escaping -- mirrors the
    property-targets no-escaping convention with the necessarily different
    delimiter). When passed and non-empty (after stripping the whole flag
    value), a '**Dead code removal**:' line is emitted immediately after
    the '**Property targets**:' line when present, else immediately after
    '**Context docs**:' -- so the D7 owning-task fold-in is visible on the
    task file. When absent (or empty after stripping), output is
    BYTE-IDENTICAL to the pre-flag skeleton -- no line is emitted.
    """
    number = getattr(args, "number", None) or "[NNN]"
    title = getattr(args, "title", None) or "[Title]"
    feature = getattr(args, "feature", None) or "[feature directory name]"
    property_targets_raw = getattr(args, "property_targets", None)
    property_targets = property_targets_raw.strip() if property_targets_raw else ""
    dead_code_removal_raw = getattr(args, "dead_code_removal", None)
    dead_code_removal = (
        dead_code_removal_raw.strip() if dead_code_removal_raw else ""
    )

    lines: List[str] = []

    # Heading.
    lines.append("# Task {0}: {1}".format(number, title))
    lines.append("")

    # Frontmatter fields.
    lines.append("**Feature**: {0}".format(feature))
    lines.append("**Agent**: [assigned agent name]")
    lines.append("**Status**: Pending")
    lines.append("**Depends on**: [task numbers] or None")
    lines.append("**Blocks**: [task numbers] or None")
    lines.append("**Spec criteria**: AC-[numbers]")
    lines.append("**Review checkpoint**: Yes/No")
    lines.append("**Context docs**: [doc file paths] or None")
    if property_targets:
        lines.append("**Property targets**: {0}".format(property_targets))
    if dead_code_removal:
        lines.append("**Dead code removal**: {0}".format(dead_code_removal))
    lines.append("")

    # Files table.
    lines.append("## Files")
    lines.append("")
    lines.append("| File | Action | Description |")
    lines.append("|------|--------|-------------|")
    lines.append("| [path] | Create/Modify | [what changes] |")
    lines.append("")

    # Description.
    lines.append("## Description")
    lines.append("")
    lines.append("[Detailed description of what to do]")
    lines.append("")

    # Change Details.
    lines.append("## Change Details")
    lines.append("")
    lines.append("- In `path/to/file`:")
    lines.append("  - [specific change]")
    lines.append("- In `path/to/other`:")
    lines.append("  - [specific change]")
    lines.append("")

    # Contracts.
    lines.append("## Contracts")
    lines.append("")
    lines.append("### Expects (checked before execution)")
    lines.append("- [precondition: what must be true in the codebase before this task runs]")
    lines.append("")
    lines.append("### Produces (checked after execution)")
    lines.append("- [postcondition: what must be true in the codebase after this task completes]")
    lines.append("")

    # Done When — task-specific placeholders + four fixed helper-owned lines.
    lines.append("## Done When")
    lines.append("")
    lines.append("- [ ] [Testable condition specific to this task]")
    lines.append("- [ ] [Another task-specific condition]")
    for fixed_line in _DONE_WHEN_FIXED_LINES:
        lines.append("- [ ] {0}".format(fixed_line))
    lines.append("")

    # Completion Notes — skeleton for /devforge:implement.
    lines.append("## Completion Notes")
    lines.append("")
    lines.append("[Filled in by /devforge:implement after completion]")
    lines.append("**Completed**: [date/time]")
    lines.append("**Files changed**: [actual files]")
    lines.append("**Contract**: Expects [X/Y verified] | Produces [X/Y verified]")
    lines.append("**Notes**: [deviations or observations]")

    sys.stdout.write("\n".join(lines) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: render-tasks-index
# ---------------------------------------------------------------------------


def cmd_render_tasks_index(args: argparse.Namespace) -> int:
    """Emit the tasks/README.md skeleton for a feature's task index.

    Stamps optional --feature/--spec/--plan args into the header fields.
    All table structures and section shapes are helper-owned. Exit 0 always.
    """
    feature = getattr(args, "feature", None) or "[Feature Name]"
    spec_path = getattr(args, "spec", None) or "[path to spec.md]"
    plan_path_arg = getattr(args, "plan", None) or "[path to plan.md]"
    generated = datetime.utcnow().strftime("%Y-%m-%d")

    lines: List[str] = []

    # Header.
    lines.append("# Tasks: {0}".format(feature))
    lines.append("")
    lines.append("**Spec**: {0}".format(spec_path))
    lines.append("**Plan**: {0}".format(plan_path_arg))
    lines.append("**Generated**: {0}".format(generated))
    lines.append("**Total tasks**: [count]")
    lines.append("")

    # Dependency Graph.
    lines.append("## Dependency Graph")
    lines.append("")
    lines.append("```")
    lines.append("001 ([title]) ──→ 002 ([title])")
    lines.append("               ──→ 003 ([title])")
    lines.append("```")
    lines.append("")

    # Task Index table.
    lines.append("## Task Index")
    lines.append("")
    lines.append("| # | Title | Agent | Depends on | Status |")
    lines.append("|---|-------|-------|-----------|--------|")
    lines.append("| 001 | [title] | [agent] | None | Pending |")
    lines.append("")

    # Additions to Spec.
    lines.append("## Additions to Spec")
    lines.append("")
    lines.append("[Files or changes discovered that weren't in the original spec]")
    lines.append("")

    # Risk Assessment table.
    lines.append("## Risk Assessment")
    lines.append("")
    lines.append("| Task | Risk | Reason |")
    lines.append("|------|------|--------|")
    lines.append("| 001 | Low/Med/High | [why] |")
    lines.append("")

    # Review Checkpoints table.
    lines.append("## Review Checkpoints")
    lines.append("")
    lines.append("| Before Task | Reason | What to Review |")
    lines.append("|-------------|--------|----------------|")
    lines.append("| [NNN] | [convergence / layer crossing / high risk] | [what to verify before proceeding] |")

    sys.stdout.write("\n".join(lines) + "\n")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: render-consultation-block
# ---------------------------------------------------------------------------


def cmd_render_consultation_block(args: argparse.Namespace) -> int:
    """Emit a Specialist Consultation table skeleton for tasks/README provenance.

    Mirror plan_helper cmd_render_consultation_block EXACTLY: no arguments,
    owns column names + verdict enum, emits a (none) row. Exit 0 always.
    """
    block = (
        "Record one row per specialist consulted during breakdown planning. "
        "The architect is the decision-authority and synthesizer; "
        "specialists supply domain input only. "
        "If a consult was requested but no response was relayed, record that too "
        "(use Verdict `no-response`). "
        "If NO specialists were consulted on this breakdown, keep the single `(none)` row below.\n"
        "\n"
        "| Specialist | Sub-question | Input summary | Verdict | Cites |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| db-engineer | <the specific sub-question> | <1-line summary of their input> | accepted | <file:line or doc ref> |\n"
        "| (none) | — | — | — | — |\n"
        "\n"
        "**Verdict** must be one of: `accepted` / `modified` / `rejected` / `no-response`. "
        "Every row requires a **Cites** entry: file:line, doc section, or `own-reasoning`.\n"
    )
    sys.stdout.write(block)
    return 0


# ---------------------------------------------------------------------------
# Task-file contract parsing helpers (shared by verify-contract-chain and
# verify-ac-coverage).
# ---------------------------------------------------------------------------

# Match the **Spec criteria**: frontmatter line and extract AC-\d+ references.
_SPEC_CRITERIA_PATTERN = re.compile(r"^\*\*Spec criteria\*\*:\s*(.+)$", re.MULTILINE)
# \b is technically redundant in typical usage because the greedy \d+ match stops at
# the first non-digit character, but the explicit word boundary makes intent clear and
# guards against pathological no-separator concatenations like "AC-1-and-AC-12" where
# "AC-1" would otherwise match inside "AC-12" if a naïve non-greedy variant were used.
_AC_REF_PATTERN = re.compile(r"AC-\d+\b")

# Bullet list marker prefix: "- " or "* " (with optional leading spaces).
_BULLET_PREFIX_RE = re.compile(r"^\s*[-*]\s+")

# Placeholder bullet: after stripping the bullet prefix, the remainder is
# a bracketed expression (e.g. "[precondition: ...]").  Square-bracket
# content may span multiple words and may contain punctuation.
_PLACEHOLDER_BULLET_RE = re.compile(r"^\[.+\]\s*$")


def _normalize_bullet(raw: str) -> str:
    """Normalize a contract bullet for equality comparison.

    Steps (documented here as the canonical matching rule):
      1. Strip leading bullet marker ('- ' / '* ' with optional indent).
      2. Strip surrounding whitespace.
      3. Collapse internal runs of whitespace to a single space.
      4. Casefold (lowercase for locale-neutral comparison).

    Two bullets are considered matching when their normalized forms are equal.
    """
    text = _BULLET_PREFIX_RE.sub("", raw)
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def _is_placeholder_bullet(raw: str) -> bool:
    """Return True if the bullet (after stripping its marker) is a placeholder.

    Placeholders are bracketed expressions like '[precondition: ...]' or
    '[postcondition: ...]'.  Empty lines are also considered placeholders
    (no content to contribute to the chain).
    """
    text = _BULLET_PREFIX_RE.sub("", raw).strip()
    if not text:
        return True
    return bool(_PLACEHOLDER_BULLET_RE.match(text))


def _parse_expects_produces(content: str) -> "Tuple[List[str], List[str]]":
    """Extract RAW, non-placeholder Expects and Produces bullets from a task
    file's ## Contracts section.

    Returns (expects_list, produces_list) where each element is the ORIGINAL
    bullet text: the leading bullet marker ('- '/'* ' with optional indent) is
    stripped, and surrounding whitespace is stripped, but original case and
    internal spacing are PRESERVED.

    Normalization (casefold + whitespace collapse) is intentionally NOT applied
    here.  Callers that need case-insensitive matching (e.g. verify-contract-chain)
    apply _normalize_bullet at COMPARISON TIME.  Callers that store the bullets
    for later consumption (e.g. finalize-handoff) receive the original-case text
    so downstream consumers (e.g. /implement) can verify real code symbols.

    The function locates:
      - '### Expects (checked before execution)' as the start of expects bullets.
      - '### Produces (checked after execution)' as the start of produces bullets.
    Each subsection ends at the next '##' heading or EOF.

    Heading-boundary note: the boundary pattern r"^##" matches ANY heading that
    starts with '##', including triple-hash headings ('### Produces') as well as
    double-hash headings ('## Done When').  This means each subsection (Expects,
    Produces) is bounded by the NEXT sibling '###' subsection OR the next '##'
    section — whichever comes first.  A future maintainer must NOT assume that a
    second '###' subsection inside ## Contracts would extend the Expects block;
    it will instead terminate it.
    """
    expects: List[str] = []
    produces: List[str] = []

    expects_pat = re.compile(r"^###\s+Expects\b[^\n]*$", re.MULTILINE)
    produces_pat = re.compile(r"^###\s+Produces\b[^\n]*$", re.MULTILINE)

    # Locate Expects section.
    m_exp = expects_pat.search(content)
    if m_exp:
        m_next = re.compile(r"^##", re.MULTILINE).search(content, m_exp.end())
        exp_text = content[m_exp.end(): m_next.start() if m_next else len(content)]
        for line in exp_text.splitlines():
            if _BULLET_PREFIX_RE.match(line) and not _is_placeholder_bullet(line):
                # Strip only the bullet marker + surrounding whitespace; preserve
                # original case and internal spacing.
                expects.append(_BULLET_PREFIX_RE.sub("", line).strip())

    # Locate Produces section.
    m_pro = produces_pat.search(content)
    if m_pro:
        m_next = re.compile(r"^##", re.MULTILINE).search(content, m_pro.end())
        pro_text = content[m_pro.end(): m_next.start() if m_next else len(content)]
        for line in pro_text.splitlines():
            if _BULLET_PREFIX_RE.match(line) and not _is_placeholder_bullet(line):
                # Strip only the bullet marker + surrounding whitespace; preserve
                # original case and internal spacing.
                produces.append(_BULLET_PREFIX_RE.sub("", line).strip())

    return expects, produces


def _parse_spec_criteria_ac_ids(content: str) -> "List[str]":
    """Extract AC-N ids from the **Spec criteria**: frontmatter line.

    Pattern used: AC-[digit]+ (via _AC_REF_PATTERN).
    Returns a list of AC id strings (e.g. ['AC-1', 'AC-3']).
    Returns empty list if the line is absent.
    """
    m = _SPEC_CRITERIA_PATTERN.search(content)
    if not m:
        return []
    return _AC_REF_PATTERN.findall(m.group(1))


def _glob_task_files(tasks_dir: str) -> "List[str]":
    """Return sorted list of *.md paths in tasks_dir excluding README.md.

    Returns empty list if tasks_dir does not exist or is not a directory.
    """
    p = Path(tasks_dir)
    if not p.is_dir():
        return []
    result = []
    for f in p.iterdir():
        if f.suffix == ".md" and f.name.upper() != "README.MD":
            result.append(str(f))
    return sorted(result)


# ---------------------------------------------------------------------------
# Subcommand: verify-contract-chain
# ---------------------------------------------------------------------------


def cmd_verify_contract_chain(args: argparse.Namespace) -> int:
    """Walk task files, parse Expects/Produces, verify chain integrity.

    For each *.md file in tasks_dir (excluding README.md):
      - Extract normalized Expects bullets (skipping placeholders).
      - Extract normalized Produces bullets (skipping placeholders).

    Then check:
      - Orphan Produces: a Produces item that no other task's Expects
        references.  Advisory: may map directly to a spec AC, which this
        verb cannot see.
      - Unsatisfied Expects: an Expects item that no task's Produces
        supplies.  Advisory: may be satisfied by existing-codebase state,
        which this verb cannot see.

    Matching rule: normalize both sides with _normalize_bullet (strip marker,
    strip whitespace, collapse internal whitespace, casefold) then compare
    for equality.

    Exit 0 when clean, printing:
        contract-chain: ok (<N> tasks, <P> produces, <E> expects)

    Exit 2 when violations found, printing a '## Contract chain findings'
    block to stdout.

    Exit 2 with a stderr 'no task files found in <dir>' message when the
    tasks-dir is missing or contains no qualifying *.md files.
    """
    tasks_dir = args.tasks_dir

    task_files = _glob_task_files(tasks_dir)
    if not task_files:
        sys.stderr.write(
            "breakdown_helper: no task files found in {0}\n".format(tasks_dir)
        )
        return 2

    # Collect per-task data: (filename, raw_expects_list, raw_produces_list).
    # _parse_expects_produces returns RAW bullets (original case + internal spacing).
    # Normalization is deferred to comparison time below.
    task_data: "List[Tuple[str, List[str], List[str]]]" = []
    for fpath in task_files:
        content = _read_file(fpath)
        if content is None:
            content = ""
        expects, produces = _parse_expects_produces(content)
        task_data.append((fpath, expects, produces))

    # Build normalized match sets (casefold + collapse) for chain-integrity checks.
    # These sets contain normalized forms only; raw text is kept in task_data for
    # display in finding messages.
    all_produces_norm: "set[str]" = set()
    for _, _, produces in task_data:
        for item in produces:
            all_produces_norm.add(_normalize_bullet(item))

    all_expects_norm: "set[str]" = set()
    for _, expects, _ in task_data:
        for item in expects:
            all_expects_norm.add(_normalize_bullet(item))

    total_tasks = len(task_data)
    total_produces = sum(len(p) for _, _, p in task_data)
    total_expects = sum(len(e) for _, e, _ in task_data)

    findings: "List[str]" = []

    for fpath, expects, produces in task_data:
        task_name = Path(fpath).name
        # Orphan Produces: produced here (normalized), not expected by any task.
        # Finding message shows the ORIGINAL-CASE text (raw item) — not the
        # casefolded form — so downstream readers see real code symbols.
        for item in produces:
            if _normalize_bullet(item) not in all_expects_norm:
                findings.append(
                    "- ORPHAN PRODUCES in {task}: {item!r}"
                    " (advisory: may map to a spec AC, which verify-contract-chain"
                    " cannot see)".format(task=task_name, item=item)
                )
        # Unsatisfied Expects: expected here (normalized), not produced by any task.
        for item in expects:
            if _normalize_bullet(item) not in all_produces_norm:
                findings.append(
                    "- UNSATISFIED EXPECTS in {task}: {item!r}"
                    " (advisory: may be existing-codebase state, which"
                    " verify-contract-chain cannot see)".format(
                        task=task_name, item=item
                    )
                )

    if findings:
        sys.stdout.write("## Contract chain findings\n\n")
        sys.stdout.write("\n".join(findings) + "\n")
        return 2

    sys.stdout.write(
        "contract-chain: ok ({n} tasks, {p} produces, {e} expects)\n".format(
            n=total_tasks, p=total_produces, e=total_expects
        )
    )
    return 0


# ---------------------------------------------------------------------------
# Subcommand: verify-ac-coverage
# ---------------------------------------------------------------------------


def cmd_verify_ac_coverage(args: argparse.Namespace) -> int:
    """Check that every AC in spec §5 is referenced by at least one task file.

    Parses spec ACs via _parse_acs (same helper used by render-findings-from-plan
    and plan_helper — do NOT re-implement).  Parses task **Spec criteria**: lines
    and collects the union of AC-N ids across all task files.

    Output when all covered:
        ac-coverage: ok (<N> ACs all covered)
    Exit 0.

    Output when spec has zero ACs:
        ac-coverage: no-acs (spec §5 has no acceptance criteria)
    Exit 0.  (Not a violation — nothing to cover.)

    Output when uncovered ACs exist:
        ## Uncovered acceptance criteria
        - AC-N: <snippet>
        ...
    Exit 2.

    Exit 2 with stderr message when tasks_dir is missing/empty or spec is
    unreadable.  Stderr vs stdout distinguishes 'no-files/bad-spec' from
    'violations found'.
    """
    tasks_dir = args.tasks_dir
    spec_path = args.spec_path

    # Validate tasks-dir.
    task_files = _glob_task_files(tasks_dir)
    if not task_files:
        sys.stderr.write(
            "breakdown_helper: no task files found in {0}\n".format(tasks_dir)
        )
        return 2

    # Read spec.
    spec_content = _read_file(spec_path)
    if spec_content is None:
        sys.stderr.write(
            "breakdown_helper: cannot read spec: {0}\n".format(spec_path)
        )
        return 2

    # Parse spec ACs — reuse existing helper.
    ac_pairs = _parse_acs(spec_content)  # List[Tuple[str, str]]: (num_str, snippet)
    if not ac_pairs:
        sys.stdout.write(
            "ac-coverage: no-acs (spec §5 has no acceptance criteria)\n"
        )
        return 0

    spec_ac_ids = {"AC-{0}".format(num) for num, _ in ac_pairs}

    # Collect AC ids referenced by task files.
    referenced_ac_ids: "set[str]" = set()
    for fpath in task_files:
        content = _read_file(fpath)
        if content is None:
            continue
        for ac_id in _parse_spec_criteria_ac_ids(content):
            referenced_ac_ids.add(ac_id)

    uncovered = sorted(
        spec_ac_ids - referenced_ac_ids,
        key=lambda s: int(s.split("-")[1]),
    )

    if not uncovered:
        sys.stdout.write(
            "ac-coverage: ok ({n} ACs all covered)\n".format(n=len(spec_ac_ids))
        )
        return 0

    # Build AC id → snippet map for the report.
    ac_snippet: "Dict[str, str]" = {
        "AC-{0}".format(num): snippet for num, snippet in ac_pairs
    }

    sys.stdout.write("## Uncovered acceptance criteria\n\n")
    for ac_id in uncovered:
        snippet = ac_snippet.get(ac_id, "")
        sys.stdout.write(
            "- {ac_id}: {snippet}\n".format(ac_id=ac_id, snippet=snippet)
        )
    return 2


# ---------------------------------------------------------------------------
# Phase 3.5 — agent-roster validation (shared function + verify-agent-roster).
# ---------------------------------------------------------------------------


def _validate_agent_roster(
    tasks_dir: str,
    agents_dir: str,
) -> "Tuple[List[Tuple[str, str]], List[str], bool, int]":
    """Validate every task's resolved **Agent**: value against the installed roster.

    Parameters
    ----------
    tasks_dir:   path to the tasks/ directory (passed to _glob_task_files).
    agents_dir:  path to the .claude/agents/ directory to glob for *.md stems.

    Returns
    -------
    (offenders, installed_roster_sorted, roster_found, task_count)

    offenders:
        List of (task_filename, agent_value) for each task whose resolved
        **Agent**: value is non-empty, NOT a placeholder, and NOT in the
        installed roster.  Tasks with empty or placeholder agents are SKIPPED
        — those are a separate error owned by finalize-handoff.

    installed_roster_sorted:
        Sorted list of stems of regular *.md FILES found in agents_dir
        (directories named *.md/ are excluded via f.is_file()).
        Empty list when roster_found is False.

    roster_found:
        False when agents_dir does not exist OR contains zero *.md files.
        Caller should treat this as fail-closed (cannot validate → error out).

    task_count:
        Number of task files found in tasks_dir via _glob_task_files.
        This is the single authoritative scan; callers must not re-glob.
    """
    agents_path = Path(agents_dir)
    if agents_path.is_dir():
        roster = sorted(
            f.stem
            for f in agents_path.iterdir()
            if f.suffix == ".md" and f.is_file()
        )
    else:
        roster = []

    if not roster:
        return [], [], False, 0

    roster_set = set(roster)

    task_files = _glob_task_files(tasks_dir)
    task_count = len(task_files)
    offenders: "List[Tuple[str, str]]" = []
    for fpath in task_files:
        content = _read_file(fpath)
        if content is None:
            continue
        m = _AGENT_LINE_RE.search(content)
        if not m:
            continue
        agent_val = m.group(1).strip()
        # Skip empty or placeholder — those are finalize-handoff's concern.
        if not agent_val or _AGENT_PLACEHOLDER_RE.match(agent_val):
            continue
        if agent_val not in roster_set:
            offenders.append((Path(fpath).name, agent_val))

    return offenders, roster, True, task_count


def cmd_verify_agent_roster(args: argparse.Namespace) -> int:
    """Verify every task's assigned agent exists in .claude/agents/*.md.

    Usage: verify-agent-roster <tasks-dir> [--agents-dir <path>]

    --agents-dir defaults to '.claude/agents' relative to cwd.

    Exit codes:
      0 — all assigned agents are installed (or tasks have no resolved agent).
      2 — missing task files, empty/absent roster, or at least one offender.
    """
    tasks_dir = args.tasks_dir
    agents_dir = args.agents_dir

    # Single scan: _validate_agent_roster globs task files internally and
    # returns the count as the 4th element.  Both the empty-tasks guard and
    # the ok-line "N tasks" count are derived from this single call — no
    # second _glob_task_files invocation in this function.
    offenders, roster, roster_found, task_count = _validate_agent_roster(
        tasks_dir, agents_dir
    )

    # roster_found is False when agents_dir is absent or has no *.md files.
    # The short-circuit in _validate_agent_roster returns task_count=0 in
    # this case regardless of the tasks dir, so we report the roster error
    # (the more actionable of the two possible issues).
    if not roster_found:
        return _die(
            "verify-agent-roster: no agent roster found at {0} "
            "— cannot validate assignments (expected *.md agent files)".format(
                agents_dir
            )
        )

    # task_count comes from the single internal _glob_task_files scan.
    if task_count == 0:
        sys.stderr.write(
            "breakdown_helper: no task files found in {0}\n".format(tasks_dir)
        )
        return 2

    if not offenders:
        sys.stdout.write(
            "agent-roster: ok ({n} tasks, {m} agents installed)\n".format(
                n=task_count, m=len(roster)
            )
        )
        return 0

    # One or more tasks assign an absent agent — report and exit 2.
    sys.stdout.write("## Agent roster findings\n\n")
    for task_filename, agent in offenders:
        sys.stdout.write(
            "- {fname}: assigned agent '{agent}' is not installed\n".format(
                fname=task_filename, agent=agent
            )
        )
    sys.stdout.write(
        "\nAvailable agents: {agents}\n".format(agents=", ".join(roster))
    )
    return 2


# ---------------------------------------------------------------------------
# Phase 3.5 — manifest-presence validation (shared predicate + verify-manifest-present).
# ---------------------------------------------------------------------------


def _reference_present(workspace_root, reference_path="design/reference.html"):
    # type: (str, str) -> bool
    """Return True iff the design reference file exists at workspace_root/reference_path.

    This is the SHARED, AUTHORITATIVE in-scope determination for the design-fidelity
    apparatus (plan 42 D4).  Both the PHASE 2.5 produce step and the PHASE 3.5
    backstop gate call this function so they cannot disagree about whether a feature
    is in design scope.

    Parameters
    ----------
    workspace_root : str
        The workspace root directory (cwd of the CLI invocation).
    reference_path : str
        Path to the reference HTML, relative to workspace_root.
        Default: 'design/reference.html'.

    Returns
    -------
    bool — True when the file exists as a regular file.
    """
    full_path = Path(workspace_root) / reference_path
    return full_path.is_file()


def _validate_manifest_present(
    feature_dir,
    workspace_root,
    reference_path="design/reference.html",
    manifest_path_override=None,
):
    # type: (str, str, str, Optional[str]) -> Tuple[int, str, str]
    """Core validation for the design-manifest-present invariant (plan 42 WI-1).

    Asserts: reference_present => binding_present AND binding_valid.

    Plan 53 Phase 3/7c retarget: the on-disk artifact `design-manifest.json`
    is unchanged (same filename, same call sites — plan 53 D4 successor), but
    its SCHEMA is now the BINDING (`{route, pairs: [{anchor_selector,
    built_testid}]}`, `_design._schema.Binding`) — the retired data-ref /
    disposition-manifest shape (`ElementRecord` / `disposition` / `gap_list`)
    is gone.  This function composes `_design._schema.validate_binding`.

    Used by both the standalone verb (verify-manifest-present) and the
    finalize-handoff chokepoint (Phase 2).

    Parameters
    ----------
    feature_dir : str
        The feature directory (parent of tasks/).  The binding is expected at
        feature_dir/design-manifest.json unless manifest_path_override is given.
    workspace_root : str
        Workspace root used to locate design/reference.html.
    reference_path : str
        Path to the reference HTML relative to workspace_root.
    manifest_path_override : str or None
        Override the binding path (for testing / explicit --manifest-path flag).

    Returns
    -------
    (exit_code, stdout_text, stderr_text)

    exit_code:
      0  — ok (either reference absent — not a design feature — or binding valid)
      2  — violation (reference present but binding absent or invalid)

    stdout_text:
      On exit 0 (no reference):  one-liner skip message.
      On exit 0 (valid):         one-liner ok message.
      On exit 2 (absent):        '## Design manifest findings' block with remedy.
      On exit 2 (invalid):       '## Design manifest findings' block with errors.

    stderr_text:
      Non-empty only when the feature-dir itself is broken/unresolvable (caller
      should write this to stderr directly and return the exit code).
    """
    # Ensure _design is importable from the same lib dir as this file.
    _lib_dir = Path(__file__).resolve().parent
    if str(_lib_dir) not in sys.path:
        sys.path.insert(0, str(_lib_dir))

    from _design._schema import validate_binding, binding_from_json  # type: ignore[import]

    feature_path = Path(feature_dir)

    # Determine binding path (the on-disk artifact is still design-manifest.json).
    if manifest_path_override:
        manifest_file = Path(manifest_path_override)
    else:
        manifest_file = feature_path / "design-manifest.json"

    # Infer feature name for messages from the feature dir basename.
    feature_name = feature_path.name

    # --- Step 1: is this a design-reference feature? ---
    if not _reference_present(workspace_root, reference_path):
        return (
            0,
            "design-manifest: skip (no {ref} — not a design-reference feature)\n".format(
                ref=reference_path
            ),
            "",
        )

    # --- Step 2: reference present, binding absent → hard fail ---
    if not manifest_file.is_file():
        stdout = (
            "## Design manifest findings\n"
            "\n"
            "- {ref} is present but {manifest} is absent.\n"
            "  The PHASE 2.5 design-intake gate was skipped or did not complete.\n"
            "\n"
            "Remedy: re-run /devforge:breakdown PHASE 2.5 to produce the binding for\n"
            "  feature '{feature}' before proceeding to PHASE 3.5.\n"
            "  The binding must declare a route and at least one\n"
            "  anchor_selector/built_testid pair (the container floor) before\n"
            "  running validate-binding.\n"
        ).format(
            ref=reference_path,
            manifest=str(manifest_file.relative_to(feature_path.parent)
                         if manifest_file.is_absolute() and manifest_file.parts[:len(feature_path.parent.parts)] == feature_path.parent.parts
                         else manifest_file),
            feature=feature_name,
        )
        return (2, stdout, "")

    # --- Step 3: both present → validate ---
    try:
        with open(str(manifest_file), "r", encoding="utf-8") as fh:
            binding = binding_from_json(fh.read())
    except (OSError, ValueError) as exc:
        stdout = (
            "## Design manifest findings\n"
            "\n"
            "- {manifest}: cannot be read or parsed: {exc}\n"
        ).format(manifest=manifest_file, exc=exc)
        return (2, stdout, "")

    errors = validate_binding(binding)

    if not errors:
        return (
            0,
            "design-manifest: ok (binding present and valid for '{feature}')\n".format(
                feature=feature_name
            ),
            "",
        )

    # Validation errors → findings block.
    lines = ["## Design manifest findings\n", "\n"]
    for err in errors:
        lines.append("- {0}\n".format(err))
    lines.append(
        "\nRemedy: supply a non-empty route and resolve every pair's\n"
        "  anchor_selector/built_testid before proceeding to PHASE 3.5.\n"
    )
    return (2, "".join(lines), "")


def cmd_verify_manifest_present(args):
    # type: (argparse.Namespace) -> int
    """Assert design/reference.html present => design-manifest.json present AND valid.

    This is the 4th PHASE 3.5 integrity gate (plan 42 WI-1), sibling to
    verify-contract-chain, verify-ac-coverage, and verify-agent-roster.

    Usage:
      verify-manifest-present <tasks-dir>
      verify-manifest-present <tasks-dir> [--reference-path <path>] [--manifest-path <path>]
      verify-manifest-present <tasks-dir> --scope-only

    Positional argument:
      tasks-dir — path to the feature's tasks/ directory (e.g. specs/001-foo/tasks).
        The feature directory is the parent of tasks-dir.
        The workspace root is cwd.

    Options:
      --reference-path PATH
        Reference file path relative to cwd (default: 'design/reference.html').
      --manifest-path PATH
        Override the manifest path (default: feature-dir/design-manifest.json).
      --scope-only
        In this mode: exit 0 if design/reference.html is present (feature IS in
        design scope); exit 3 if absent (NOT a design feature).  No manifest
        assertion is performed.  Callers use this to decide whether to run the
        PHASE 2.5 design-intake producer step.

    Exit codes (default mode):
      0 — ok: either reference absent (non-UI feature, trivial pass) or manifest
              present-and-valid.  Prints a one-liner ok/skip message to stdout.
      2 — violation: reference present but manifest absent or invalid.
              Prints a '## Design manifest findings' block to stdout (same shape
              as '## Agent roster findings' — the orchestrator can branch on it).
              Broken state (tasks-dir/feature-dir missing) also exits 2 with a
              short message on stderr.

    Exit codes (--scope-only mode):
      0 — reference is present (feature IS in design scope).
      3 — reference is absent (NOT a design feature).
    """
    tasks_dir_raw = args.tasks_dir
    reference_path = getattr(args, "reference_path", "design/reference.html") or "design/reference.html"
    manifest_path_override = getattr(args, "manifest_path_override", None)
    scope_only = getattr(args, "scope_only", False)

    # Resolve tasks dir and feature dir.
    tasks_path = Path(tasks_dir_raw)
    if not tasks_path.is_absolute():
        tasks_path = Path.cwd() / tasks_path

    workspace_root = str(Path.cwd())

    # Broken state: tasks dir does not exist.
    if not tasks_path.exists():
        sys.stderr.write(
            "breakdown_helper: tasks directory not found: {0}\n".format(tasks_dir_raw)
        )
        return 2

    feature_dir = tasks_path.parent

    # --scope-only: pure existence check, no manifest assertion.
    if scope_only:
        if _reference_present(workspace_root, reference_path):
            return 0
        return 3

    # Full assertion mode.
    exit_code, stdout_text, stderr_text = _validate_manifest_present(
        feature_dir=str(feature_dir),
        workspace_root=workspace_root,
        reference_path=reference_path,
        manifest_path_override=manifest_path_override,
    )

    if stdout_text:
        sys.stdout.write(stdout_text)
    if stderr_text:
        sys.stderr.write(stderr_text)
    return exit_code


# ---------------------------------------------------------------------------
# Property-coverage validation (plan 66 WI-1 — shared predicate +
# verify-property-coverage).  Sibling in shape to _validate_agent_roster /
# cmd_verify_agent_roster: a shared predicate consumed by both the standalone
# verb AND the finalize-handoff chokepoint.
# ---------------------------------------------------------------------------

# Property targets frontmatter line, mirroring _AGENT_LINE_RE / _CONTEXT_DOCS_RE
# in shape: horizontal-whitespace-only after the colon so a blank value never
# bleeds into the next line, MULTILINE so it matches anywhere in the task file.
_PROPERTY_TARGETS_LINE_RE = re.compile(
    r"^\*\*Property targets\*\*:[^\S\n]*(.+)$", re.MULTILINE
)

# Pure-Builder Targets section heading in plan.md -- IDENTICAL pattern to
# plan_helper's own producer-side heading matcher (same literal regex, same
# flags), so _plan_declares_pure_builder_targets's section boundary can
# never disagree with what the producer parsed.  Used ONLY via
# _plan_declares_pure_builder_targets, itself used ONLY by
# cmd_verify_property_coverage's fail-open/fail-closed fallback (amendment,
# instruction-review HIGH finding) -- NOT by _validate_property_coverage,
# which is unchanged.
_PURE_BUILDER_HEADING_RE = re.compile(
    r"^###\s+Pure-Builder Targets\b", re.MULTILINE | re.IGNORECASE
)

# Change-Induced Dead Code section heading in plan.md -- IDENTICAL pattern to
# plan_helper._parse_dead_code_rows's own producer-side heading matcher (same
# literal regex, same flags), so _plan_declares_dead_code_rows's section
# boundary can never disagree with what the producer parsed. Used ONLY via
# _plan_declares_dead_code_rows, itself used ONLY by the
# cmd_finalize_handoff_breakdown declared-but-unsubstantiated chokepoint
# (plan 71 review hardening, mirrors the plan-66 property-coverage
# fail-closed-fallback shape).
_DEAD_CODE_HEADING_RE = re.compile(
    r"^###\s+Change-Induced Dead Code\b", re.MULTILINE | re.IGNORECASE
)


def _validate_property_coverage(tasks_dir, plan_handoff_path):
    # type: (str, str) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]], int, Optional[str]]
    """Validate that every declared pure-builder target is covered by a task.

    Parameters
    ----------
    tasks_dir : str
        Path to the tasks/ directory (passed to _glob_task_files).
    plan_handoff_path : str
        Path to the sibling plan-handoff.json to read
        breakdown_seeds.pure_builder_targets from.

    Returns
    -------
    (declared, offenders, covering_task_count, error)

    declared:
        List of (target, file) tuples parsed from
        breakdown_seeds.pure_builder_targets.  Entries with an empty or
        missing 'target' value are skipped (they name nothing to cover).
        A target name is a comma-separated-format identifier and must not
        itself contain a comma (there is no escaping). A target name
        repeated across multiple rows is DEDUPED, keeping only the first
        occurrence's file value -- a twice-declared target renders as ONE
        offender, not two. Empty when the handoff has no key, an empty
        list, or the handoff cannot be read (co-varies with error being set
        in the latter case).

    offenders:
        Subset of declared whose target is not named by any task's
        '**Property targets**:' line.  Empty when declared is empty.

    covering_task_count:
        Number of task files whose '**Property targets**:' line names at
        least one declared target (each qualifying task file counted once,
        regardless of how many declared targets it names).

    error:
        None on success (including the "no declared targets" case — that is
        NOT an error).  A short string when plan_handoff_path is missing,
        unreadable, not valid JSON, or its root is not a JSON object.  The
        caller decides severity: the standalone verb fails closed on a
        non-None error; the finalize-handoff chokepoint treats it as a
        silent skip (an absent/malformed sibling handoff is not a NEW
        violation this predicate should invent — see the chokepoint's own
        comment for the asymmetry rationale).
    """
    handoff_path = Path(plan_handoff_path)
    if not handoff_path.is_file():
        return (
            [],
            [],
            0,
            "plan-handoff.json not found/unreadable at {0} "
            "— cannot verify property coverage".format(plan_handoff_path),
        )

    try:
        raw_text = handoff_path.read_text(encoding="utf-8")
        d = json.loads(raw_text)
    except (OSError, IOError, json.JSONDecodeError):
        return (
            [],
            [],
            0,
            "plan-handoff.json not found/unreadable at {0} "
            "— cannot verify property coverage".format(plan_handoff_path),
        )

    if not isinstance(d, dict):
        return (
            [],
            [],
            0,
            "plan-handoff.json not found/unreadable at {0} "
            "— cannot verify property coverage".format(plan_handoff_path),
        )

    # A present-but-wrong-shape breakdown_seeds / pure_builder_targets is a
    # MALFORMED handoff and must route through the error path (where the verb's
    # plan.md heading fallback decides skip vs fail-closed) — coercing it to
    # empty would silently skip a feature whose plan.md declares targets.
    # Absent/None is the legitimate no-targets case.
    seeds = d.get("breakdown_seeds")
    if seeds is None:
        seeds = {}
    elif not isinstance(seeds, dict):
        return (
            [],
            [],
            0,
            "plan-handoff.json not found/unreadable at {0} "
            "— cannot verify property coverage".format(plan_handoff_path),
        )
    raw_targets = seeds.get("pure_builder_targets")
    if raw_targets is None:
        raw_targets = []
    elif not isinstance(raw_targets, list):
        return (
            [],
            [],
            0,
            "plan-handoff.json not found/unreadable at {0} "
            "— cannot verify property coverage".format(plan_handoff_path),
        )

    declared: "List[Tuple[str, str]]" = []
    seen_targets: "set" = set()
    for row in raw_targets:
        if not isinstance(row, dict):
            continue
        target = (row.get("target") or "").strip()
        if not target:
            continue
        if target in seen_targets:
            # Dedup by target name, keeping the first occurrence's file
            # value -- a twice-declared target must render as ONE finding.
            continue
        seen_targets.add(target)
        file_val = row.get("file", "") or ""
        declared.append((target, file_val))

    if not declared:
        return [], [], 0, None

    declared_names = {target for target, _file in declared}

    task_files = _glob_task_files(tasks_dir)
    covered: "set" = set()
    covering_task_count = 0
    for fpath in task_files:
        content = _read_file(fpath)
        if content is None:
            continue
        m = _PROPERTY_TARGETS_LINE_RE.search(content)
        if not m:
            continue
        entries = [e.strip() for e in m.group(1).split(",")]
        entries = [e for e in entries if e]
        if not entries:
            continue
        matched_this_task = False
        for entry in entries:
            if entry in declared_names:
                covered.add(entry)
                matched_this_task = True
        if matched_this_task:
            covering_task_count += 1

    offenders = [(target, file_val) for target, file_val in declared if target not in covered]
    return declared, offenders, covering_task_count, None


def _plan_declares_pure_builder_targets(plan_md_content):
    # type: (str) -> bool
    """Return True iff plan.md declares at least one real pure-builder target.

    Mirrors plan_helper._parse_pure_builder_targets's OWN criterion --
    section exists (via the same '### Pure-Builder Targets' heading pattern,
    _PURE_BUILDER_HEADING_RE) AND at least one row whose first cell is
    non-empty and non-placeholder -- using breakdown_helper's OWN existing
    primitives (_extract_plan_section, _parse_table_rows, _is_placeholder_cell).
    Does NOT import plan_helper (breakdown_helper owns its own copies of
    these shared parsing primitives; the two modules deliberately do not
    depend on each other).

    A heading with ONLY placeholder rows (e.g. the '| [target] | [file] |
    [why] |' example row render-task-file-style fixtures seed) returns
    False -- the plan.md declared the SECTION but not an actual target, the
    same as if the section were absent entirely.
    """
    section = _extract_plan_section(plan_md_content, _PURE_BUILDER_HEADING_RE)
    if not section:
        return False
    for cells in _parse_table_rows(section):
        if cells and not _is_placeholder_cell(cells[0]):
            return True
    return False


def _plan_declares_dead_code_rows(plan_md_content):
    # type: (str) -> bool
    """Return True iff plan.md declares at least one real dead-code row.

    Mirrors plan_helper._parse_dead_code_rows's OWN criterion -- section
    exists (via the same '### Change-Induced Dead Code' heading pattern,
    _DEAD_CODE_HEADING_RE) AND at least one row whose first cell (File) is
    non-empty and non-placeholder -- using breakdown_helper's OWN existing
    primitives (_extract_plan_section, _parse_table_rows, _is_placeholder_cell).
    Does NOT import plan_helper (breakdown_helper owns its own copies of
    these shared parsing primitives; the two modules deliberately do not
    depend on each other). Mirrors _plan_declares_pure_builder_targets.

    A heading with ONLY placeholder rows returns False -- the plan.md
    declared the SECTION but not an actual dead-code row, the same as if
    the section were absent entirely.
    """
    section = _extract_plan_section(plan_md_content, _DEAD_CODE_HEADING_RE)
    if not section:
        return False
    for cells in _parse_table_rows(section):
        if cells and not _is_placeholder_cell(cells[0]):
            return True
    return False


def _render_property_coverage_findings(offenders):
    # type: (List[Tuple[str, str]]) -> str
    """Render the '## Property coverage findings' block for a list of
    (target, file) offenders.

    Shared by cmd_verify_property_coverage and the finalize-handoff
    chokepoint (mirrors the _validate_manifest_present shared-rendering
    precedent) so the two emission sites cannot drift apart.
    """
    parts = ["## Property coverage findings\n\n"]
    for target, file_val in offenders:
        parts.append(
            "- target '{t}' ({f}): no property-test task covers it\n".format(
                t=target, f=file_val
            )
        )
    parts.append(
        "\nDeclared in plan-handoff.json breakdown_seeds.pure_builder_targets; "
        "add a dedicated qa-engineer property-test task with a "
        "'**Property targets**:' line naming each uncovered target.\n"
    )
    return "".join(parts)


def cmd_verify_property_coverage(args):
    # type: (argparse.Namespace) -> int
    """Verify every declared pure-builder target is covered by a task.

    Usage: verify-property-coverage <tasks-dir> [--plan-handoff <path>]

    --plan-handoff defaults to Path(tasks_dir).parent / 'plan-handoff.json'.

    Never-declared-vs-declared-but-unverifiable asymmetry (amendment,
    instruction-review HIGH finding): a missing/unreadable/malformed
    plan-handoff.json is NOT automatically a hard failure. /breakdown PHASE
    0a.5 tolerates a missing plan-handoff.json as a normal degraded path
    ("decomposing from plan.md directly") -- a legacy/handoff-less feature
    that never declared any pure-builder targets must not dead-end at this
    gate. So on ANY handoff error, this verb falls back to sibling plan.md
    via _plan_declares_pure_builder_targets -- the SAME criterion the
    producer (plan_helper._parse_pure_builder_targets) uses: the
    '### Pure-Builder Targets' heading must be present AND at least one row
    must carry a real (non-placeholder) target, not just the heading alone:
      - the plan declares NO real target (heading absent, plan.md itself
        absent/unreadable, OR the heading is present but every row is a
        placeholder) => the feature never declared targets in the first
        place; this is the SAME "nothing to verify" case as an empty
        pure_builder_targets list => skip, exit 0.
      - the plan DOES declare at least one real target, but there is no
        verifiable handoff to prove coverage against. Silently skipping here
        would let a declared-but-unverified target evaporate -- exactly the
        silent-evaporation failure mode this gate exists to prevent => fail
        closed, exit 2, with a remedy pointing at plan_helper finalize-handoff.

    Exit codes:
      0 — no declared targets (skip; covers both an empty
          pure_builder_targets list AND a missing/malformed handoff paired
          with no real pure-builder target declared in plan.md), or all
          declared targets covered.
      2 — a missing/malformed handoff paired with at least one real
          pure-builder target declared in plan.md (fail-closed, remedy
          printed); no task files found while targets ARE declared; or at
          least one uncovered target.
    """
    tasks_dir_raw = args.tasks_dir
    plan_handoff_raw = getattr(args, "plan_handoff", None)

    tasks_path = Path(tasks_dir_raw)
    if not tasks_path.is_absolute():
        tasks_path = Path.cwd() / tasks_path

    if plan_handoff_raw:
        plan_handoff_path = Path(plan_handoff_raw)
        if not plan_handoff_path.is_absolute():
            plan_handoff_path = Path.cwd() / plan_handoff_path
    else:
        plan_handoff_path = tasks_path.parent / "plan-handoff.json"

    declared, offenders, covering_task_count, error = _validate_property_coverage(
        str(tasks_path), str(plan_handoff_path)
    )

    if error is not None:
        # Check whether plan.md actually declares a REAL pure-builder target
        # (not just the heading) before failing closed -- see the docstring
        # asymmetry note above.
        plan_md_path = tasks_path.parent / "plan.md"
        plan_md_content = _read_file(str(plan_md_path))
        declared_in_plan = (
            plan_md_content is not None
            and _plan_declares_pure_builder_targets(plan_md_content)
        )
        if not declared_in_plan:
            sys.stdout.write(
                "property-coverage: skip (no plan-handoff.json and no "
                "pure-builder targets declared in plan.md)\n"
            )
            return 0
        return _die(
            "verify-property-coverage: plan-handoff.json not found/unreadable "
            "at {0} — plan.md declares pure-builder targets; run plan_helper "
            "finalize-handoff {1} to produce it, then re-run this gate".format(
                plan_handoff_path, plan_md_path
            )
        )

    if not declared:
        sys.stdout.write(
            "property-coverage: skip (no declared pure-builder targets)\n"
        )
        return 0

    # Declared targets present — task files are now required.
    task_files = _glob_task_files(str(tasks_path))
    if not task_files:
        sys.stderr.write(
            "breakdown_helper: no task files found in {0}\n".format(tasks_dir_raw)
        )
        return 2

    if not offenders:
        sys.stdout.write(
            "property-coverage: ok ({n} targets, {m} covering tasks)\n".format(
                n=len(declared), m=covering_task_count
            )
        )
        return 0

    sys.stdout.write(_render_property_coverage_findings(offenders))
    return 2


# ---------------------------------------------------------------------------
# Dead-code coverage validation (plan 71 D9 amendment — shared predicate +
# verify-dead-code-coverage). Mirrors the property-coverage block above
# EXACTLY in shape (_validate_property_coverage / cmd_verify_property_coverage
# / _render_property_coverage_findings), with one new axis: D7 requires each
# declared row be folded into EXACTLY ONE owning task, so this predicate also
# reports DUPLICATE assignment (2+ covering tasks), not just zero coverage.
# ---------------------------------------------------------------------------

# Dead code removal frontmatter line, mirroring _PROPERTY_TARGETS_LINE_RE in
# shape: horizontal-whitespace-only after the colon so a blank value never
# bleeds into the next line, MULTILINE so it matches anywhere in the task
# file. Field VALUE format is semicolon-separated (NOT comma-separated like
# _PROPERTY_TARGETS_LINE_RE) -- see cmd_render_task_file's --dead-code-removal
# docstring for why: anchor tokens are literal code fragments that commonly
# contain commas.
_DEAD_CODE_REMOVAL_LINE_RE = re.compile(
    r"^\*\*Dead code removal\*\*:[^\S\n]*(.+)$", re.MULTILINE
)


def _validate_dead_code_coverage(tasks_dir, plan_handoff_path):
    # type: (str, str) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]], List[Tuple[str, str, List[str]]], int, Optional[str]]
    """Validate every declared dead-code row is covered by EXACTLY ONE task.

    Parameters
    ----------
    tasks_dir : str
        Path to the tasks/ directory (passed to _glob_task_files).
    plan_handoff_path : str
        Path to the sibling plan-handoff.json to read
        breakdown_seeds.dead_code_rows from.

    Returns
    -------
    (declared, offenders, duplicates, covering_task_count, error)

    declared:
        List of (anchor_token, file) tuples parsed from
        breakdown_seeds.dead_code_rows. Each raw row is validated by
        CONSTRUCTING a full _breakdown.handoff_schema.DeadCodeRow (the
        SAME validation _extract_dead_code_rows applies to the passthrough
        carrier) -- a row failing construction (empty file/anchor_token,
        invalid kind, empty why_dead, or a semicolon in anchor_token; see
        DeadCodeRow.__post_init__) is SKIPPED, not declared. This closes a
        review-hardening finding (plan 71 D9 amendment, finding B): declared
        must never be a superset of what _extract_dead_code_rows actually
        carries into breakdown-handoff.json -- otherwise this gate could
        demand coverage for a row that will never exist in the written
        handoff (an unsatisfiable exit-2). A token repeated across multiple
        declared rows is DEDUPED, keeping only the first occurrence's file
        value -- a twice-declared token renders as ONE finding, not two.
        Empty when the handoff has no key, an empty list, every row is
        invalid, or the handoff cannot be read (co-varies with error being
        set in the latter case).

    offenders:
        Subset of declared whose anchor_token is named by ZERO tasks'
        '**Dead code removal**:' field. Empty when declared is empty.

    duplicates:
        Subset of declared whose anchor_token is named by TWO OR MORE
        DISTINCT tasks' '**Dead code removal**:' field, rendered as
        (anchor_token, file, covering_task_filenames) -- D7 requires
        exactly one owning task per row; 2+ claimants is as much a
        violation as zero. "Distinct" is load-bearing (finding A): a
        single task listing the same token twice within its OWN field
        (e.g. 'foo; foo') is deduped per-task before aggregation, so it
        counts as ONE covering task, not two -- a task cannot claim a row
        twice by repeating itself. Empty when declared is empty or every
        declared token has exactly one covering task.

    covering_task_count:
        Number of task files whose '**Dead code removal**:' field names at
        least one declared anchor_token (each qualifying task file counted
        once, regardless of how many declared tokens it names).

    error:
        None on success (including the "no declared rows" case — that is
        NOT an error). A short string when plan_handoff_path is missing,
        unreadable, not valid JSON, its root is not a JSON object, or
        breakdown_seeds/dead_code_rows is present but wrong-shape. The
        caller decides severity: the standalone verb fails closed via the
        plan.md fallback (_plan_declares_dead_code_rows); the
        finalize-handoff chokepoint treats a non-None error the same way
        (this predicate mirrors _validate_property_coverage's error-path
        shape exactly for the JSON-structure axis; on the PER-ROW axis it
        is now STRICTER than _validate_property_coverage on purpose --
        property-targets rows have no second, stricter reader to diverge
        from, so that looseness was safe; a dead-code row DOES have one
        [_extract_dead_code_rows], so this predicate must apply the exact
        same per-row validity criterion or risk demanding coverage for a
        row that was never going to ship).
    """
    handoff_path = Path(plan_handoff_path)
    if not handoff_path.is_file():
        return (
            [], [], [], 0,
            "plan-handoff.json not found/unreadable at {0} "
            "— cannot verify dead-code coverage".format(plan_handoff_path),
        )

    try:
        raw_text = handoff_path.read_text(encoding="utf-8")
        d = json.loads(raw_text)
    except (OSError, IOError, json.JSONDecodeError):
        return (
            [], [], [], 0,
            "plan-handoff.json not found/unreadable at {0} "
            "— cannot verify dead-code coverage".format(plan_handoff_path),
        )

    if not isinstance(d, dict):
        return (
            [], [], [], 0,
            "plan-handoff.json not found/unreadable at {0} "
            "— cannot verify dead-code coverage".format(plan_handoff_path),
        )

    # A present-but-wrong-shape breakdown_seeds / dead_code_rows is a
    # MALFORMED handoff and must route through the error path (mirrors
    # _validate_property_coverage's own treatment). Absent/None is the
    # legitimate no-rows case.
    seeds = d.get("breakdown_seeds")
    if seeds is None:
        seeds = {}
    elif not isinstance(seeds, dict):
        return (
            [], [], [], 0,
            "plan-handoff.json not found/unreadable at {0} "
            "— cannot verify dead-code coverage".format(plan_handoff_path),
        )
    raw_rows = seeds.get("dead_code_rows")
    if raw_rows is None:
        raw_rows = []
    elif not isinstance(raw_rows, list):
        return (
            [], [], [], 0,
            "plan-handoff.json not found/unreadable at {0} "
            "— cannot verify dead-code coverage".format(plan_handoff_path),
        )

    from _breakdown.handoff_schema import DeadCodeRow

    declared: "List[Tuple[str, str]]" = []
    seen_tokens: "set" = set()
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        try:
            parsed_row = DeadCodeRow(
                file=row.get("file", ""),
                anchor_token=row.get("anchor_token", ""),
                kind=row.get("kind", ""),
                why_dead=row.get("why_dead", ""),
            )
        except (TypeError, ValueError):
            # Fails the SAME validation _extract_dead_code_rows applies to
            # the passthrough carrier (finding B) -- a row that will never
            # ship into breakdown-handoff.json must never be declared here.
            continue
        anchor_token = parsed_row.anchor_token
        if anchor_token in seen_tokens:
            # Dedup by anchor token, keeping the first occurrence's file
            # value -- a twice-declared token must render as ONE finding.
            continue
        seen_tokens.add(anchor_token)
        declared.append((anchor_token, parsed_row.file))

    if not declared:
        return [], [], [], 0, None

    declared_tokens = {token for token, _file in declared}

    task_files = _glob_task_files(tasks_dir)
    covering_tasks: "Dict[str, List[str]]" = {}
    covering_task_count = 0
    for fpath in task_files:
        content = _read_file(fpath)
        if content is None:
            continue
        m = _DEAD_CODE_REMOVAL_LINE_RE.search(content)
        if not m:
            continue
        entries = [e.strip() for e in m.group(1).split(";")]
        entries = [e for e in entries if e]
        # Dedup entries WITHIN this one task's own field (finding A) -- a
        # task listing the same token twice ('foo; foo') must not inflate
        # its own coverage into a phantom 2-claimant "duplicate assignment".
        entries = list(dict.fromkeys(entries))
        if not entries:
            continue
        matched_this_task = False
        fname = Path(fpath).name
        for entry in entries:
            if entry in declared_tokens:
                covering_tasks.setdefault(entry, []).append(fname)
                matched_this_task = True
        if matched_this_task:
            covering_task_count += 1

    offenders = [
        (token, file_val)
        for token, file_val in declared
        if token not in covering_tasks
    ]
    duplicates = [
        (token, file_val, sorted(set(covering_tasks[token])))
        for token, file_val in declared
        if token in covering_tasks and len(set(covering_tasks[token])) >= 2
    ]
    return declared, offenders, duplicates, covering_task_count, None


def _render_dead_code_coverage_findings(offenders, duplicates):
    # type: (List[Tuple[str, str]], List[Tuple[str, str, List[str]]]) -> str
    """Render the '## Dead-code coverage findings' block.

    Shared by cmd_verify_dead_code_coverage and the finalize-handoff
    chokepoint (mirrors the _render_property_coverage_findings shared-
    rendering precedent) so the two emission sites cannot drift apart.
    Renders BOTH finding kinds: zero-coverage offenders and 2+-coverage
    duplicates -- D7 requires exactly one owning task, so both are
    violations.
    """
    parts = ["## Dead-code coverage findings\n\n"]
    for token, file_val in offenders:
        parts.append(
            "- anchor '{t}' ({f}): no task's '**Dead code removal**:' "
            "field covers it\n".format(t=token, f=file_val)
        )
    for token, file_val, task_names in duplicates:
        parts.append(
            "- anchor '{t}' ({f}): claimed by {n} tasks ({names}) -- must "
            "be folded into exactly ONE owning task\n".format(
                t=token,
                f=file_val,
                n=len(task_names),
                names=", ".join(sorted(task_names)),
            )
        )
    parts.append(
        "\nDeclared in plan-handoff.json breakdown_seeds.dead_code_rows; "
        "fold each uncovered/duplicated anchor into exactly one task's "
        "'**Dead code removal**:' field (semicolon-separated list of "
        "anchor tokens, mirroring '**Property targets**:').\n"
    )
    return "".join(parts)


def cmd_verify_dead_code_coverage(args):
    # type: (argparse.Namespace) -> int
    """Verify every declared dead-code row is covered by EXACTLY ONE task.

    Usage: verify-dead-code-coverage <tasks-dir> [--plan-handoff <path>]

    --plan-handoff defaults to Path(tasks_dir).parent / 'plan-handoff.json'.

    Mirrors cmd_verify_property_coverage's never-declared-vs-declared-but-
    unverifiable asymmetry EXACTLY (same fallback to sibling plan.md via
    _plan_declares_dead_code_rows, the SAME criterion the producer
    plan_helper._parse_dead_code_rows uses: heading present AND >=1
    non-placeholder row, not just the heading alone), PLUS a NEW
    duplicate-assignment check (D7: exactly one owning task per row --
    zero coverage and 2+ coverage are BOTH violations).

    Exit codes:
      0 — no declared rows (skip; covers both an empty dead_code_rows list
          AND a missing/malformed handoff paired with no real dead-code
          row declared in plan.md), or every declared row covered by
          exactly one task.
      2 — a missing/malformed handoff paired with at least one real
          dead-code row declared in plan.md (fail-closed, remedy printed);
          no task files found while rows ARE declared; at least one
          uncovered row; or at least one row claimed by 2+ tasks.
    """
    tasks_dir_raw = args.tasks_dir
    plan_handoff_raw = getattr(args, "plan_handoff", None)

    tasks_path = Path(tasks_dir_raw)
    if not tasks_path.is_absolute():
        tasks_path = Path.cwd() / tasks_path

    if plan_handoff_raw:
        plan_handoff_path = Path(plan_handoff_raw)
        if not plan_handoff_path.is_absolute():
            plan_handoff_path = Path.cwd() / plan_handoff_path
    else:
        plan_handoff_path = tasks_path.parent / "plan-handoff.json"

    declared, offenders, duplicates, covering_task_count, error = (
        _validate_dead_code_coverage(str(tasks_path), str(plan_handoff_path))
    )

    if error is not None:
        # Check whether plan.md actually declares a REAL dead-code row (not
        # just the heading) before failing closed -- see the docstring
        # asymmetry note above.
        plan_md_path = tasks_path.parent / "plan.md"
        plan_md_content = _read_file(str(plan_md_path))
        declared_in_plan = (
            plan_md_content is not None
            and _plan_declares_dead_code_rows(plan_md_content)
        )
        if not declared_in_plan:
            sys.stdout.write(
                "dead-code-coverage: skip (no plan-handoff.json and no "
                "change-induced dead code declared in plan.md)\n"
            )
            return 0
        return _die(
            "verify-dead-code-coverage: plan-handoff.json not found/unreadable "
            "at {0} — plan.md declares change-induced dead code; run "
            "plan_helper finalize-handoff {1} to produce it, then re-run "
            "this gate".format(plan_handoff_path, plan_md_path)
        )

    if not declared:
        sys.stdout.write(
            "dead-code-coverage: skip (no declared dead-code rows)\n"
        )
        return 0

    # Declared rows present — task files are now required.
    task_files = _glob_task_files(str(tasks_path))
    if not task_files:
        sys.stderr.write(
            "breakdown_helper: no task files found in {0}\n".format(tasks_dir_raw)
        )
        return 2

    if not offenders and not duplicates:
        sys.stdout.write(
            "dead-code-coverage: ok ({n} rows, {m} covering tasks)\n".format(
                n=len(declared), m=covering_task_count
            )
        )
        return 0

    sys.stdout.write(_render_dead_code_coverage_findings(offenders, duplicates))
    return 2


# ---------------------------------------------------------------------------
# Phase 4 — task-file parsing helpers (for finalize-handoff).
# ---------------------------------------------------------------------------

# Heading pattern: "# Task NNN: Title" (with optional leading whitespace)
_TASK_HEADING_RE = re.compile(r"^#\s+Task\s+(\d+):\s+(.+)$", re.MULTILINE)

# Agent line pattern: "**Agent**: value"
# [^\S\n]* matches horizontal whitespace (spaces/tabs) but NOT the newline,
# preventing \s* from consuming the line terminator and greedily swallowing
# the next line's content when the agent field is blank.
_AGENT_LINE_RE = re.compile(r"^\*\*Agent\*\*:[^\S\n]*(.*)$", re.MULTILINE)

# Placeholder agent detector: the exact text emitted by render-task-file.
_AGENT_PLACEHOLDER_RE = re.compile(r"^\[assigned agent name\]\s*$")

# Depends-on / Blocks frontmatter line patterns.
_DEPENDS_ON_RE = re.compile(r"^\*\*Depends on\*\*:\s*(.+)$", re.MULTILINE)
_BLOCKS_RE = re.compile(r"^\*\*Blocks\*\*:\s*(.+)$", re.MULTILINE)

# Review checkpoint line pattern.
_REVIEW_CHECKPOINT_RE = re.compile(r"^\*\*Review checkpoint\*\*:\s*(.+)$", re.MULTILINE)

# Context docs line pattern.
# [^\S\n]* matches horizontal whitespace (spaces/tabs) but NOT the newline,
# preventing \s* from consuming the line terminator and greedily capturing
# the next line's content when the context-docs field is blank.
_CONTEXT_DOCS_RE = re.compile(r"^\*\*Context docs\*\*:[^\S\n]*(.+)$", re.MULTILINE)

# Task-number token: 3+ digits, word-boundary anchored, for depends_on/blocks.
_TASK_NUMBER_TOKEN_RE = re.compile(r"\b(\d{3,})\b")

# README Dependency Graph: fenced block under ## Dependency Graph.
_DEP_GRAPH_SECTION_RE = re.compile(r"^##\s+Dependency Graph\b", re.MULTILINE)

# README Additions to Spec heading.
_ADDITIONS_SECTION_RE = re.compile(r"^##\s+Additions to Spec\b", re.MULTILINE)


def _parse_task_number_from_filename(name: str) -> Optional[str]:
    """Return the leading digit sequence from a filename, zero-padded to 3 chars.

    For '001-define-types.md' returns '001'.
    For '42-thing.md' returns '042'.
    Returns None when no leading digits are present.
    """
    m = re.match(r"^(\d+)", name)
    if not m:
        return None
    digits = m.group(1)
    # Zero-pad to at least 3 digits.
    return digits.zfill(3)


def _parse_task_heading(content: str) -> "Tuple[Optional[str], Optional[str]]":
    """Return (number_str, title) from the first '# Task NNN: Title' heading.

    number_str is the digit string (zero-padded to 3 digits).
    Returns (None, None) when no matching heading is found.
    """
    m = _TASK_HEADING_RE.search(content)
    if not m:
        return None, None
    number = m.group(1).zfill(3)
    title = m.group(2).strip()
    return number, title


def _parse_task_number_token_list(value: str) -> "List[str]":
    """Parse a comma-separated task-number value into a list of zero-padded numbers.

    'None' / 'none' / empty → [].
    '001, 002' → ['001', '002'].
    '3' → ['003'].
    """
    stripped = value.strip()
    if not stripped or stripped.lower() in ("none", "n/a", "-", "—"):
        return []
    tokens = _TASK_NUMBER_TOKEN_RE.findall(stripped)
    return [t.zfill(3) for t in tokens]


def _parse_touched_files_from_task(content: str) -> "List[str]":
    """Return non-placeholder File column values from the ## Files table.

    Reuses _parse_table_rows and _is_placeholder_cell (defined in Phase 0).
    """
    pat = re.compile(r"^##\s+Files\b", re.MULTILINE)
    section = _extract_plan_section(content, pat)
    if not section:
        return []
    rows = _parse_table_rows(section)
    result = []
    for cells in rows:
        if not cells:
            continue
        file_cell = cells[0]
        if not _is_placeholder_cell(file_cell):
            result.append(file_cell)
    return result


def _extract_readme_dependency_graph(readme_content: str) -> str:
    """Return the raw text of the first fenced code block under ## Dependency Graph.

    Returns '' when not found or the section has no fenced block.
    """
    m_sec = _DEP_GRAPH_SECTION_RE.search(readme_content)
    if not m_sec:
        return ""
    # Locate the next ## heading (to bound the section).
    next_h2 = re.compile(r"^##\s+", re.MULTILINE)
    m_next = next_h2.search(readme_content, m_sec.end())
    section = (
        readme_content[m_sec.end():m_next.start()]
        if m_next
        else readme_content[m_sec.end():]
    )
    # Find first fenced block inside the section.
    m_fence = re.search(r"```[^\n]*\n(.*?)```", section, re.DOTALL)
    if not m_fence:
        return ""
    return m_fence.group(1).rstrip("\n")


def _extract_readme_additions(readme_content: str) -> "List[str]":
    """Return non-placeholder lines from the ## Additions to Spec section.

    A placeholder line is the exact text emitted by render-tasks-index:
    '[Files or changes discovered that weren't in the original spec]'
    or any line starting with '[' and ending with ']'.
    Returns [] when the section is absent or contains only placeholders.
    """
    m_sec = _ADDITIONS_SECTION_RE.search(readme_content)
    if not m_sec:
        return []
    # Bound section.
    next_h2 = re.compile(r"^##\s+", re.MULTILINE)
    m_next = next_h2.search(readme_content, m_sec.end())
    section = (
        readme_content[m_sec.end():m_next.start()]
        if m_next
        else readme_content[m_sec.end():]
    )
    result = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # Skip full-line placeholders: starts with '[' and ends with ']'.
        if line.startswith("[") and line.endswith("]"):
            continue
        result.append(line)
    return result


# ---------------------------------------------------------------------------
# Phase 4 — provenance resolver for sibling plan-handoff.json
# ---------------------------------------------------------------------------


def _extract_dead_code_rows(plan_handoff_path: Path) -> "Tuple[List[Any], Optional[str]]":
    """Read breakdown_seeds.dead_code_rows from a sibling plan-handoff.json.

    Pure passthrough (plan 71 D8(b) carrier). Mirrors
    _validate_property_coverage's SILENT-vs-LOUD asymmetry (NOT its
    tolerant-of-everything predecessor): extraction itself never blocks --
    it always returns a (possibly partial) rows list -- but it now
    distinguishes two failure classes via the returned warning:

    Returns (rows, warning).

    warning is None in the SILENT cases: plan_handoff_path is absent, OR
    the sibling is a well-formed JSON object whose 'breakdown_seeds' is
    absent/None, OR 'breakdown_seeds' is present but carries no
    'dead_code_rows' key (None). These are the legitimate "nothing
    declared, or a pre-plan-71 handoff" cases and must not warn -- an
    empty dead_code_rows list on disk is treated the same way.

    warning is a short non-empty diagnostic string in the LOUD cases: the
    sibling exists but is unreadable/not valid JSON/root not a JSON
    object, 'breakdown_seeds' is present but not a JSON object,
    'dead_code_rows' is present but not a JSON array, or at least one row
    dict failed DeadCodeRow construction (a PARTIAL loss -- the other rows
    still parse and are returned). The caller (cmd_finalize_handoff_breakdown)
    writes this to stderr as a non-fatal WARN naming what was lost
    (plan-42 D7 tripwire pattern) -- extraction still never blocks on its
    own; only the sibling declared-but-unsubstantiated CHOKEPOINT at the
    call site can fail closed, and only when plan.md independently
    declares real change-induced-dead-code rows that this extraction
    produced none of (a plan.md-declared MUST-lane kill-list may never
    ship as an empty breakdown-handoff.json carrier -- the plans-38/42
    silent-void class this hardening closes).
    """
    from _breakdown.handoff_schema import DeadCodeRow

    if not plan_handoff_path.is_file():
        return [], None
    try:
        raw_text = plan_handoff_path.read_text(encoding="utf-8")
        d = json.loads(raw_text)
    except (OSError, IOError, json.JSONDecodeError) as err:
        return [], (
            "sibling plan-handoff.json at {0} is unreadable/not valid "
            "JSON ({1}) -- breakdown_seeds.dead_code_rows could not be "
            "extracted".format(plan_handoff_path, err)
        )
    if not isinstance(d, dict):
        return [], (
            "sibling plan-handoff.json at {0}: root is not a JSON object "
            "-- breakdown_seeds.dead_code_rows could not be "
            "extracted".format(plan_handoff_path)
        )

    seeds = d.get("breakdown_seeds")
    if seeds is None:
        return [], None
    if not isinstance(seeds, dict):
        return [], (
            "sibling plan-handoff.json at {0}: 'breakdown_seeds' is "
            "present but not a JSON object -- dead_code_rows could not "
            "be extracted".format(plan_handoff_path)
        )

    raw_rows = seeds.get("dead_code_rows")
    if raw_rows is None:
        return [], None
    if not isinstance(raw_rows, list):
        return [], (
            "sibling plan-handoff.json at {0}: "
            "breakdown_seeds.dead_code_rows is present but not a JSON "
            "array -- dead_code_rows could not be extracted".format(
                plan_handoff_path
            )
        )

    result: "List[Any]" = []
    malformed = 0
    for raw in raw_rows:
        if not isinstance(raw, dict):
            malformed += 1
            continue
        try:
            result.append(
                DeadCodeRow(
                    file=raw.get("file", ""),
                    anchor_token=raw.get("anchor_token", ""),
                    kind=raw.get("kind", ""),
                    why_dead=raw.get("why_dead", ""),
                )
            )
        except (TypeError, ValueError):
            malformed += 1
            continue

    if malformed:
        return result, (
            "sibling plan-handoff.json at {0}: {1} of {2} "
            "breakdown_seeds.dead_code_rows entries were malformed and "
            "skipped".format(plan_handoff_path, malformed, len(raw_rows))
        )

    return result, None


def _resolve_sibling_plan_handoff(plan_dir: Path) -> Optional[str]:
    """Return path to the sibling plan-handoff.json if it is valid, else None.

    'Valid' means: exists, parses as JSON, has handoff_kind == 'plan'.
    Does NOT do full schema validation — just enough to confirm it is the
    sibling plan handoff and not a different artefact.

    Mirrors _resolve_sibling_specify_handoff in plan_helper.py exactly,
    but checks for handoff_kind == 'plan' instead of 'specify'.
    """
    candidate = plan_dir / "plan-handoff.json"
    if not candidate.exists():
        return None
    try:
        raw = candidate.read_text(encoding="utf-8")
        d = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(d, dict):
        return None
    if d.get("handoff_kind") != "plan":
        return None
    return str(candidate.resolve())


# ---------------------------------------------------------------------------
# Phase 4 — JSON serialization helpers
# ---------------------------------------------------------------------------


def _asdict_breakdown(breakdown: Any) -> "Dict[str, Any]":
    """Serialize a Breakdown dataclass to a plain JSON-ready dict.

    Uses dataclasses.asdict recursively to flatten nested dataclasses.
    Lists of dataclasses are converted to lists of dicts.
    """
    import dataclasses as _dc
    return _dc.asdict(breakdown)


def _atomic_write_json_breakdown(data: "Dict[str, Any]", target: Path) -> None:
    """Atomically write data as JSON to target.

    Uses tempfile.mkstemp + os.replace.  Cleans up temp on failure.
    Mirrors _atomic_write_json_plan in plan_helper.py.
    """
    fd, tmp_path = tempfile.mkstemp(
        prefix="breakdown-handoff-",
        suffix=".json.tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=False)
            f.write("\n")
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Subcommand: finalize-handoff (Phase 4, Verb 1)
# ---------------------------------------------------------------------------


def cmd_finalize_handoff_breakdown(args: argparse.Namespace) -> int:
    """Parse tasks/*.md + README.md -> build Breakdown -> validate -> write breakdown-handoff.json.

    Task fields parsed per file (each *.md excluding README.md):
      number:            from filename NNN-title.md leading digits (fallback: heading).
      title:             from '# Task NNN: Title' heading.
      agent:             from '**Agent**:' line; placeholder '[assigned agent name]'
                         treated as empty → exit 2 naming the offending file.
      depends_on/blocks: from '**Depends on**:'/'**Blocks**:' lines; task-number tokens.
      ac_addressed:      from '**Spec criteria**:' via AC-\\d+\\b regex.
      doc_refs:          from '**Context docs**:'; paths split on comma; placeholder → [].
      review_checkpoint: 'Yes' → True, 'No'/missing → False.
      touched_files:     File column of ## Files table (skip placeholder rows).
      expects/produces:  via _parse_expects_produces (Phase 3; do NOT re-implement).

    README.md fields:
      dependency_graph:  fenced block under ## Dependency Graph ('' if absent).
      additions:         non-placeholder lines under ## Additions to Spec ([] if absent).

    Provenance:
      plan_path:              absolute path to plan.md.
      spec_path:              sibling spec.md if it exists, else None.
      upstream_handoff_path:  sibling plan-handoff.json if present + kind=='plan'.
      upstream_handoff_kind:  'plan' if upstream set, else None. (co-vary)

    dead_code_rows (plan 71 D8(b) passthrough):
      Copied verbatim from the sibling plan-handoff.json's
      breakdown_seeds.dead_code_rows (see _extract_dead_code_rows) so
      /verify can read the declared change-induced-dead-code kill-list
      directly from breakdown-handoff.json. Empty when /plan declared none
      (the section is absent, or the sibling handoff has no
      dead_code_rows key -- SILENT, no warning). A sibling that is
      unreadable/malformed/wrong-shape, or that carries individual
      malformed row entries, WARNS on stderr but still does not block by
      itself. It IS gated, however: when plan.md's own
      '### Change-Induced Dead Code' section declares at least one real
      row but the passthrough produced none (for ANY reason -- absent,
      unreadable, or malformed sibling), finalize-handoff FAILS CLOSED
      (exit 2) rather than silently shipping an empty carrier for a
      declared MUST-lane kill-list -- see the declared-but-unsubstantiated
      chokepoint below.

    dead_code_rows task-coverage CHOKEPOINT (plan 71 D9 amendment):
      Mirrors the pure-builder-targets property-coverage chokepoint above
      EXACTLY in shape (same asymmetry: runs only when a sibling
      plan-handoff.json exists, silently skips on ANY predicate error).
      When the sibling declares breakdown_seeds.dead_code_rows, every
      declared row's anchor_token must be covered by EXACTLY ONE task's
      '**Dead code removal**:' field -- zero coverage OR 2+ coverage both
      fail closed (exit 2) with a '## Dead-code coverage findings' block.
      This closes the gap the declared-but-unsubstantiated chokepoint above
      does NOT cover: it proves plan.md and plan-handoff.json AGREE a row
      is declared, but says nothing about whether any TASK actually folds
      the removal in (D7's owning-task rule was prose-only before this).

    Output: <plan-dir>/breakdown-handoff.json (atomic write, sibling to plan.md).
    Idempotent: re-running overwrites the previous breakdown-handoff.json.

    Exit 0: prints written path on stdout.
    Exit 2: plan.md missing, tasks_dir missing/empty, placeholder agent detected,
            schema validation failure, unknown assigned agent (roster check),
            design-manifest violation (design/reference.html present but
            design-manifest.json absent/invalid — plan 42 WI-1 chokepoint),
            an uncovered pure-builder target when the sibling plan-handoff.json
            declares one (plan 66 WI-1 chokepoint), plan.md declaring
            change-induced dead code that the sibling plan-handoff.json
            carries none of (plan 71 declared-but-unsubstantiated
            chokepoint), or a sibling-declared dead-code row left
            uncovered/double-covered by the task files (plan 71 D9
            task-coverage chokepoint). The plan-66 chokepoint AND the
            plan-71 D9 task-coverage chokepoint are SKIPPED SILENTLY when
            the sibling plan-handoff.json is itself absent or
            unreadable/malformed — see the inline comment at each call site
            for the asymmetry vs. the strict fail-closed standalone
            verify-property-coverage / verify-dead-code-coverage verbs. The
            plan-71 declared-but-unsubstantiated chokepoint does NOT share
            that asymmetry — it fails closed on ANY reason the passthrough
            produced zero rows (absent, unreadable, or malformed sibling)
            whenever plan.md itself declares real rows; see
            _extract_dead_code_rows + the inline comment at the call site.
    Exit 1: I/O write failure.
    """
    # Ensure lib dir on path for schema imports.
    _lib_dir = Path(__file__).resolve().parent
    if str(_lib_dir) not in sys.path:
        sys.path.insert(0, str(_lib_dir))

    from _breakdown.handoff_schema import (  # type: ignore[import]
        Breakdown,
        Provenance,
        TaskRow,
        SCHEMA_VERSION,
        HANDOFF_KIND,
    )

    plan_path_raw = args.plan_path
    plan_path = Path(plan_path_raw)
    if not plan_path.is_absolute():
        plan_path = Path.cwd() / plan_path
    plan_path = plan_path.resolve()

    if not plan_path.is_file():
        return _die("finalize-handoff: plan not found: {0}".format(plan_path_raw))

    plan_dir = plan_path.parent
    tasks_dir = plan_dir / "tasks"

    if not tasks_dir.is_dir():
        return _die(
            "finalize-handoff: tasks directory not found: {0}".format(tasks_dir)
        )

    task_files = _glob_task_files(str(tasks_dir))
    if not task_files:
        return _die(
            "finalize-handoff: no task files found in {0}".format(tasks_dir)
        )

    # Parse each task file into a TaskRow.
    task_rows: "List[TaskRow]" = []
    for fpath in task_files:
        content = _read_file(fpath)
        if content is None:
            return _die(
                "finalize-handoff: cannot read task file: {0}".format(fpath)
            )

        fname = Path(fpath).name

        # Number: from filename, fallback to heading.
        number = _parse_task_number_from_filename(fname)
        heading_number, heading_title = _parse_task_heading(content)
        if number is None:
            number = heading_number
        if number is None:
            return _die(
                "finalize-handoff: cannot determine task number from: {0}".format(fname)
            )

        # Title: from heading.
        title = heading_title or ""
        if not title:
            return _die(
                "finalize-handoff: cannot determine task title from: {0}".format(fname)
            )

        # Agent: required, not a placeholder.
        m_agent = _AGENT_LINE_RE.search(content)
        if not m_agent:
            return _die(
                "finalize-handoff: missing **Agent**: line in {0}".format(fname)
            )
        agent_val = m_agent.group(1).strip()
        if not agent_val or _AGENT_PLACEHOLDER_RE.match(agent_val):
            return _die(
                "finalize-handoff: placeholder/empty **Agent**: in {0} "
                "— assign a real agent before running finalize-handoff".format(fname)
            )

        # Depends on / Blocks.
        m_dep = _DEPENDS_ON_RE.search(content)
        depends_on = _parse_task_number_token_list(m_dep.group(1)) if m_dep else []
        m_blk = _BLOCKS_RE.search(content)
        blocks = _parse_task_number_token_list(m_blk.group(1)) if m_blk else []

        # AC ids from **Spec criteria**:.
        ac_addressed = _parse_spec_criteria_ac_ids(content)

        # Context docs.
        m_docs = _CONTEXT_DOCS_RE.search(content)
        doc_refs: "List[str]" = []
        if m_docs:
            docs_val = m_docs.group(1).strip()
            # Skip known none-equivalent values.
            if docs_val.lower() not in ("none", "n/a", "-", "—"):
                # Real doc paths never start with '['; a leading '[' means
                # the whole value is an unfilled placeholder (e.g.
                # '[doc file paths] or None').  Prefix-check is more
                # robust than an exact-string match that would break if
                # render-task-file's placeholder text ever changes.
                if not docs_val.startswith("["):
                    for part in docs_val.split(","):
                        part = part.strip()
                        # Skip individual placeholder tokens: '[...]'.
                        if part and not (part.startswith("[") and part.endswith("]")):
                            doc_refs.append(part)

        # Review checkpoint.
        m_rc = _REVIEW_CHECKPOINT_RE.search(content)
        review_checkpoint = False
        if m_rc:
            rc_val = m_rc.group(1).strip()
            if rc_val.lower() in ("yes", "y", "true"):
                review_checkpoint = True

        # Touched files from ## Files table.
        touched_files = _parse_touched_files_from_task(content)

        # Expects / Produces — reuse Phase 3 helper (do NOT re-implement).
        expects, produces = _parse_expects_produces(content)

        try:
            row = TaskRow(
                number=number,
                title=title,
                agent=agent_val,
                depends_on=depends_on,
                blocks=blocks,
                touched_files=touched_files,
                expects=expects,
                produces=produces,
                ac_addressed=ac_addressed,
                doc_refs=doc_refs,
                review_checkpoint=review_checkpoint,
            )
        except (TypeError, ValueError) as err:
            return _die(
                "finalize-handoff: TaskRow validation failed for {0}: {1}".format(
                    fname, err
                )
            )
        task_rows.append(row)

    # Sort tasks by number for deterministic ordering.
    task_rows.sort(key=lambda r: r.number)

    # Agent-roster validation: all resolved agent names must be installed.
    # This check runs after the per-task loop so placeholder/empty agents
    # (caught above) are already handled.  _validate_agent_roster skips
    # tasks with empty or placeholder agents — it only checks resolved names.
    agents_dir_raw = getattr(args, "agents_dir", ".claude/agents")
    # The 4th element (task_count) is intentionally ignored here: finalize-handoff
    # already has its own authoritative task list in task_rows (which was parsed
    # and validated per-file above).  The roster check is the only concern.
    offenders, roster, roster_found, _task_count_ignored = _validate_agent_roster(
        str(tasks_dir), agents_dir_raw
    )
    if not roster_found:
        return _die(
            "finalize-handoff: no agent roster found at {0} "
            "— cannot validate assignments (expected *.md agent files)".format(
                agents_dir_raw
            )
        )
    if offenders:
        sys.stdout.write("## Agent roster findings\n\n")
        for task_filename, agent in offenders:
            sys.stdout.write(
                "- {fname}: assigned agent '{agent}' is not installed\n".format(
                    fname=task_filename, agent=agent
                )
            )
        sys.stdout.write(
            "\nAvailable agents: {agents}\n".format(agents=", ".join(roster))
        )
        return 2

    # Design-manifest validation (plan 42 WI-1 chokepoint): a reference-present
    # feature must have a present-and-valid design-manifest.json before the
    # handoff is written.  Uses the same _validate_manifest_present predicate as
    # the standalone verify-manifest-present verb (Phase 3.5).
    # feature_dir = plan_dir (the manifest is specs/NNN-slug/design-manifest.json,
    # sibling to plan.md; plan_dir is the parent of tasks_dir).
    # reference_path is always the default for finalize-handoff — the
    # finalize-handoff subparser registers no --reference-path flag (only
    # verify-manifest-present does), so this is the constant 'design/reference.html'.
    _manifest_exit, _manifest_out, _manifest_err = _validate_manifest_present(
        feature_dir=str(plan_dir),
        workspace_root=str(Path.cwd()),
        reference_path="design/reference.html",
    )
    if _manifest_exit != 0:
        sys.stdout.write(_manifest_out)
        if _manifest_err:
            sys.stderr.write(_manifest_err)
        return 2

    # Property-coverage validation (plan 66 WI-1 chokepoint): when the sibling
    # plan-handoff.json declares breakdown_seeds.pure_builder_targets, every
    # declared target must be covered by at least one task's
    # '**Property targets**:' line before the handoff is written.
    #
    # ASYMMETRY vs. the standalone verify-property-coverage verb: THIS
    # chokepoint SKIPS SILENTLY when the sibling plan-handoff.json is absent,
    # unreadable, or malformed — finalize-handoff already tolerates an absent
    # plan-handoff for provenance purposes (see _resolve_sibling_plan_handoff
    # above, which sets upstream_handoff_path=None in that case); an
    # absent/malformed sibling handoff is not a NEW violation for this
    # chokepoint to invent. verify-property-coverage is the strict,
    # explicitly-invoked fail-closed arm of this same predicate.
    _plan_handoff_candidate = plan_dir / "plan-handoff.json"
    if _plan_handoff_candidate.is_file():
        _pc_declared, _pc_offenders, _pc_covering, _pc_error = _validate_property_coverage(
            str(tasks_dir), str(_plan_handoff_candidate)
        )
        if _pc_error is None and _pc_declared and _pc_offenders:
            sys.stdout.write(_render_property_coverage_findings(_pc_offenders))
            return 2
        # _pc_error not None (unreadable/malformed sibling), or no declared
        # targets, or no offenders -> fall through silently (see comment above).

    # Dead-code-rows passthrough (plan 71 D8(b) carrier): copy
    # breakdown_seeds.dead_code_rows from the sibling plan-handoff.json (when
    # present) into breakdown-handoff.json verbatim, so /verify can read the
    # declared kill-list directly from breakdown-handoff.json without a new
    # cross-stage read of plan-handoff.json. Extraction itself never blocks
    # -- a loud, unreadable/malformed/wrong-shape sibling (or malformed
    # individual rows) only WARNS on stderr (see _extract_dead_code_rows
    # docstring for the SILENT-vs-LOUD asymmetry).
    dead_code_rows, dead_code_warning = _extract_dead_code_rows(_plan_handoff_candidate)
    if dead_code_warning:
        sys.stderr.write(
            "breakdown_helper: finalize-handoff: WARN: {0}\n".format(
                dead_code_warning
            )
        )

    # Declared-but-unsubstantiated CHOKEPOINT (plan 71 review hardening,
    # mirrors the plan-42 D7 tripwire + the plan-66 property-coverage
    # declared-but-handoff-less fail-closed shape): if plan.md's own
    # '### Change-Induced Dead Code' section declares at least one real row
    # (_plan_declares_dead_code_rows, the SAME criterion the producer uses)
    # but the passthrough above produced NONE, the MUST-lane kill-list
    # would silently ship as an empty breakdown-handoff.json carrier and a
    # future /verify would pass vacuously (the plans-38/42 silent-void
    # class). Unlike the pure-builder-targets chokepoint above, this one
    # does NOT tolerate an absent/malformed sibling -- a declared row in
    # plan.md that produced zero carried rows for ANY reason (no sibling,
    # unreadable sibling, or a sibling missing the key) is unsubstantiated
    # and fails closed with a remedy.
    if not dead_code_rows:
        plan_content_for_dead_code_check = _read_file(str(plan_path)) or ""
        if _plan_declares_dead_code_rows(plan_content_for_dead_code_check):
            return _die(
                "finalize-handoff: plan.md declares change-induced dead code "
                "in '### Change-Induced Dead Code', but the sibling "
                "plan-handoff.json carries none (breakdown_seeds.dead_code_rows "
                "is empty or the sibling is missing/unreadable) -- regenerate "
                "it with 'plan_helper finalize-handoff {0}' before re-running "
                "this command".format(plan_path)
            )

    # Dead-code coverage CHOKEPOINT (plan 71 D9 amendment): mirrors the
    # pure-builder-targets property-coverage chokepoint above EXACTLY in
    # shape (same asymmetry -- runs only when the sibling plan-handoff.json
    # exists, and silently skips on ANY predicate error such as an
    # unreadable/malformed sibling; the declared-but-unsubstantiated
    # chokepoint just above already guards the absent/malformed-sibling
    # case for dead code specifically). When the sibling declares
    # breakdown_seeds.dead_code_rows, every declared row's anchor_token
    # must be covered by EXACTLY ONE task's '**Dead code removal**:' field
    # before the handoff is written -- an owning-task fold-in the
    # orchestrator forgot (D7 prose-only until now) is caught here instead
    # of shipping as silent guard-and-leave.
    if _plan_handoff_candidate.is_file():
        (
            _dc_declared, _dc_offenders, _dc_duplicates, _dc_covering, _dc_error,
        ) = _validate_dead_code_coverage(
            str(tasks_dir), str(_plan_handoff_candidate)
        )
        if _dc_error is None and _dc_declared and (_dc_offenders or _dc_duplicates):
            sys.stdout.write(
                _render_dead_code_coverage_findings(_dc_offenders, _dc_duplicates)
            )
            return 2
        # _dc_error not None (unreadable/malformed sibling), or no declared
        # rows, or no offenders/duplicates -> fall through silently (mirrors
        # the property-coverage chokepoint's own asymmetry comment above).

    # Parse README.md for dependency_graph and additions.
    readme_path = tasks_dir / "README.md"
    readme_content = _read_file(str(readme_path)) or ""
    dependency_graph = _extract_readme_dependency_graph(readme_content)
    additions = _extract_readme_additions(readme_content)

    # Resolve completed_at.
    completed_at_raw = getattr(args, "completed_at", None)
    if completed_at_raw:
        breakdown_completed_at = completed_at_raw.strip()
    else:
        breakdown_completed_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Resolve provenance.
    sibling_plan_handoff_path = _resolve_sibling_plan_handoff(plan_dir)
    if sibling_plan_handoff_path is not None:
        upstream_handoff_path: Optional[str] = sibling_plan_handoff_path
        upstream_handoff_kind: Optional[str] = "plan"
    else:
        upstream_handoff_path = None
        upstream_handoff_kind = None

    # spec_path: sibling spec.md if it exists.
    sibling_spec = plan_dir / "spec.md"
    spec_path_val = str(sibling_spec.resolve()) if sibling_spec.is_file() else None

    try:
        provenance = Provenance(
            upstream_handoff_path=upstream_handoff_path,
            upstream_handoff_kind=upstream_handoff_kind,
            plan_path=str(plan_path),
            spec_path=spec_path_val,
        )
    except (TypeError, ValueError) as err:
        return _die(
            "finalize-handoff: schema validation failed building Provenance: {0}".format(err)
        )

    try:
        breakdown = Breakdown(
            schema_version=SCHEMA_VERSION,
            handoff_kind=HANDOFF_KIND,
            tasks_dir=str(tasks_dir.resolve()),
            breakdown_completed_at=breakdown_completed_at,
            provenance=provenance,
            tasks=task_rows,
            additions=additions,
            dependency_graph=dependency_graph,
            dead_code_rows=dead_code_rows,
        )
    except (TypeError, ValueError) as err:
        return _die(
            "finalize-handoff: schema validation failed: {0}".format(err)
        )

    # Atomic write to <plan-dir>/breakdown-handoff.json.
    target = plan_dir / "breakdown-handoff.json"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_json_breakdown(_asdict_breakdown(breakdown), target)
    except OSError as err:
        sys.stderr.write(
            "breakdown_helper: finalize-handoff: cannot write {0}: {1}\n".format(
                target, err
            )
        )
        return 1

    sys.stdout.write("{0}\n".format(target.resolve()))
    return 0


# ---------------------------------------------------------------------------
# Subcommand: render-implement-handoff (Phase 4, Verb 2)
# ---------------------------------------------------------------------------


def cmd_render_implement_handoff(args: argparse.Namespace) -> int:
    """Emit the manual next-step block targeting /implement.

    Reads plan.md to confirm it exists, then globs tasks/*.md to determine
    the first (lowest-numbered) task and total task count.

    The block emitted is the guaranteed human bridge the LLM copies verbatim
    into its reply after breakdown approval.  Mirror of plan_helper's
    cmd_render_breakdown_handoff style.

    Exit 0: prints the block to stdout.
    Exit 2: plan.md or tasks_dir missing or no task files found.
    """
    plan_path_raw = args.plan_path
    plan_path = Path(plan_path_raw)
    if not plan_path.is_absolute():
        plan_path = Path.cwd() / plan_path
    plan_path = plan_path.resolve()

    if not plan_path.is_file():
        return _die(
            "render-implement-handoff: plan not found: {0}".format(plan_path_raw)
        )

    plan_dir = plan_path.parent
    tasks_dir = plan_dir / "tasks"

    if not tasks_dir.is_dir():
        return _die(
            "render-implement-handoff: tasks directory not found: {0}".format(tasks_dir)
        )

    task_files = _glob_task_files(str(tasks_dir))
    if not task_files:
        return _die(
            "render-implement-handoff: no task files found in {0}".format(tasks_dir)
        )

    # Determine first task number and total count.
    # Selection is by PARSED leading integer value (numeric lowest), NOT by
    # alphabetical list position — non-zero-padded filenames like '2-foo.md'
    # and '10-bar.md' sort alphabetically as '10' < '2' but numerically 2 < 10.
    def _numeric_key(fpath: str) -> int:
        m = re.match(r"^(\d+)", Path(fpath).name)
        return int(m.group(1)) if m else 0

    first_file = min(task_files, key=_numeric_key)
    first_fname = Path(first_file).name
    first_content = _read_file(first_file) or ""
    first_number = _parse_task_number_from_filename(first_fname)
    _, first_title = _parse_task_heading(first_content)
    if first_number is None:
        first_number = "001"
    total_tasks = len(task_files)

    # Count review checkpoints across all task files.
    checkpoint_count = 0
    for fpath in task_files:
        content = _read_file(fpath) or ""
        m_rc = _REVIEW_CHECKPOINT_RE.search(content)
        if m_rc and m_rc.group(1).strip().lower() in ("yes", "y", "true"):
            checkpoint_count += 1

    output = (
        "## Manual next step — run /devforge:implement\n"
        "\n"
        "The breakdown is approved. No automated handoff exists — restart Claude Code "
        "(exit and relaunch the CLI/app so any newly-installed command is picked up), "
        "then run:\n"
        "\n"
        "```\n"
        "/devforge:implement\n"
        "```\n"
        "\n"
        "/devforge:implement will start with task {first_number}{title_suffix}.\n"
        "\n"
        "**Total tasks**: {total_tasks}\n"
        "**First task**: {first_number}{title_suffix}\n"
        "**Review checkpoints**: {checkpoint_count}\n"
    ).format(
        first_number=first_number,
        total_tasks=total_tasks,
        title_suffix=" — {0}".format(first_title) if first_title else "",
        checkpoint_count=checkpoint_count,
    )

    sys.stdout.write(output)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: read-memory
# ---------------------------------------------------------------------------


def cmd_read_memory(args: argparse.Namespace) -> int:
    """Read .devforge/memory.md under cwd and emit a JSON object.

    Workspace root is cwd -- the convention every other breakdown_helper
    subcommand already uses (no --workspace-root/--install-root flag exists
    in this file). .devforge/ is install-root-scoped, and cwd IS the install
    root for /devforge:breakdown, wrapper mode included.

    Emits exactly:
      memory_present   bool -- .devforge/memory.md exists and is readable
      memory_excerpt   str  -- the populated `## ` sections of memory.md
        (Task Outcomes excluded, empty sections dropped, truncation
        declared inline; "" if absent)
      memory_state     str  -- one of "absent" / "stub" / "populated"
        (MEMORY_STATE_KEY from _shared/memory.py)

    Absent/stub is never a fault -- a memory-less project is the correct
    state on a fresh install. Takes no arguments and always exits 0;
    read_memory_context() never raises on a missing or unreadable file.
    """
    _lib_dir = Path(__file__).resolve().parent
    if str(_lib_dir) not in sys.path:
        sys.path.insert(0, str(_lib_dir))

    from _shared.memory import MEMORY_STATE_KEY, read_memory_context

    mem_ctx = read_memory_context(str(Path.cwd()))
    result = {
        "memory_present": mem_ctx["present"],
        "memory_excerpt": mem_ctx["excerpt"],
        MEMORY_STATE_KEY: mem_ctx[MEMORY_STATE_KEY],
    }
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


# ---------------------------------------------------------------------------
# CLI wiring.
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="breakdown_helper",
        description=(
            "Structural emission helper for the /devforge:breakdown slash command. "
            "Helper owns shape; LLM composes values."
        ),
    )
    sub = parser.add_subparsers(dest="subcommand")

    # pick-plan
    sp = sub.add_parser(
        "pick-plan",
        help="Resolve which plan.md to break down (auto-picks by mtime if no path given).",
    )
    sp.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Explicit path to a plan.md (optional).",
    )
    sp.set_defaults(func=cmd_pick_plan)

    # render-pick-summary
    sp = sub.add_parser(
        "render-pick-summary",
        help="Print a 5-line deterministic plan summary block.",
    )
    sp.add_argument("plan_path", help="Path to plan.md.")
    sp.set_defaults(func=cmd_render_pick_summary)

    # list-plans
    sp = sub.add_parser(
        "list-plans",
        help="List all specs/*/plan.md sorted by mtime desc.",
    )
    sp.set_defaults(func=cmd_list_plans)

    # check-status-and-flip
    sp = sub.add_parser(
        "check-status-and-flip",
        help="Flip plan Status from Draft to Approved (idempotent).",
    )
    sp.add_argument("plan_path", help="Path to plan.md.")
    sp.set_defaults(func=cmd_check_status_and_flip)

    # read-plan-handoff
    sp = sub.add_parser(
        "read-plan-handoff",
        help=(
            "Load sibling plan-handoff.json, validate kind='plan', "
            "render upstream plan seeds block. Prints 'no-handoff' when "
            "no sibling exists; exits 2 on malformed sibling."
        ),
    )
    sp.add_argument("plan_path", help="Path to plan.md.")
    sp.set_defaults(func=cmd_read_plan_handoff)

    # render-findings-from-plan
    sp = sub.add_parser(
        "render-findings-from-plan",
        help=(
            "Emit a findings skeleton from plan (File Impact + Layer Map rows) "
            "so every file/layer is acknowledged before tasks are written. "
            "Optional spec-path enumerates ACs with [ADDRESSED BY: ?] markers. "
            "Exit 2 if plan missing."
        ),
    )
    sp.add_argument("plan_path", help="Path to plan.md.")
    sp.add_argument(
        "spec_path",
        nargs="?",
        default=None,
        help="Optional path to spec.md (enables AC coverage enumeration).",
    )
    sp.set_defaults(func=cmd_render_findings_from_plan)

    # render-task-file
    sp = sub.add_parser(
        "render-task-file",
        help=(
            "Emit the exact task-file skeleton from storage-rules.md §Task File Format. "
            "LLM fills in placeholders. Exit 0 always."
        ),
    )
    sp.add_argument("--number", default=None, help="Task number (e.g. 001).")
    sp.add_argument("--title", default=None, help="Task title.")
    sp.add_argument("--feature", default=None, help="Feature directory name.")
    sp.add_argument(
        "--property-targets",
        dest="property_targets",
        default=None,
        help=(
            "Comma-separated pure-builder target names (plan 66 WI-1). "
            "Target names must not themselves contain a comma (no escaping). "
            "When given and non-empty, emits a '**Property targets**:' line "
            "after '**Context docs**:'. Omit to leave the skeleton unchanged."
        ),
    )
    sp.add_argument(
        "--dead-code-removal",
        dest="dead_code_removal",
        default=None,
        help=(
            "Semicolon-separated list of change-induced dead-code anchor "
            "tokens folded into this owning task (plan 71 D7; each token "
            "must match breakdown_seeds.dead_code_rows[].anchor_token "
            "character-for-character -- verify-dead-code-coverage matches "
            "on it exactly). Anchor tokens must not themselves contain a "
            "semicolon (no escaping). When given and non-empty, emits a "
            "'**Dead code removal**:' line after '**Property targets**:' "
            "(or after '**Context docs**:' when no property targets). "
            "Omit to leave the skeleton unchanged."
        ),
    )
    sp.set_defaults(func=cmd_render_task_file)

    # render-tasks-index
    sp = sub.add_parser(
        "render-tasks-index",
        help=(
            "Emit the tasks/README.md skeleton: heading, Dependency Graph, "
            "Task Index table, Additions to Spec, Risk Assessment, Review Checkpoints. "
            "Exit 0 always."
        ),
    )
    sp.add_argument("--feature", default=None, help="Feature name for the heading.")
    sp.add_argument("--spec", default=None, help="Path to spec.md for the Spec field.")
    sp.add_argument("--plan", default=None, help="Path to plan.md for the Plan field.")
    sp.set_defaults(func=cmd_render_tasks_index)

    # render-consultation-block
    sp = sub.add_parser(
        "render-consultation-block",
        help=(
            "Emit the Specialist Consultation table skeleton with verdict enum "
            "and (none) row. Mirror of plan_helper render-consultation-block. "
            "Exit 0 always."
        ),
    )
    sp.set_defaults(func=cmd_render_consultation_block)

    # verify-agent-roster
    sp = sub.add_parser(
        "verify-agent-roster",
        help=(
            "Verify every task's resolved **Agent**: value exists in the installed "
            ".claude/agents/*.md roster.  Skips empty/placeholder agents (those are "
            "finalize-handoff's concern).  Exit 0 when all installed; exit 2 when "
            "any absent, roster missing, or no task files found."
        ),
    )
    sp.add_argument("tasks_dir", help="Directory containing task *.md files.")
    sp.add_argument(
        "--agents-dir",
        dest="agents_dir",
        default=".claude/agents",
        help="Path to the installed agent roster directory (default: .claude/agents).",
    )
    sp.set_defaults(func=cmd_verify_agent_roster)

    # verify-manifest-present
    sp = sub.add_parser(
        "verify-manifest-present",
        help=(
            "Assert design/reference.html present => specs/[feature]/design-manifest.json "
            "present AND valid (plan 42 WI-1).  The 4th PHASE 3.5 integrity gate.  "
            "Exit 0: reference absent (non-UI feature, trivial pass) or manifest valid.  "
            "Exit 2: reference present but manifest absent or invalid.  "
            "Exit 3 (--scope-only): reference absent (NOT a design feature).  "
            "Exit 0 (--scope-only): reference present (IS in design scope)."
        ),
    )
    sp.add_argument("tasks_dir", help="Directory containing task *.md files.")
    sp.add_argument(
        "--reference-path",
        dest="reference_path",
        default="design/reference.html",
        help=(
            "Reference HTML path relative to cwd (default: 'design/reference.html')."
        ),
    )
    sp.add_argument(
        "--manifest-path",
        dest="manifest_path_override",
        default=None,
        help=(
            "Override the manifest path (default: <feature-dir>/design-manifest.json)."
        ),
    )
    sp.add_argument(
        "--scope-only",
        dest="scope_only",
        action="store_true",
        default=False,
        help=(
            "Exit 0 if design/reference.html is present (feature in scope), "
            "exit 3 if absent (not a design feature). No manifest assertion."
        ),
    )
    sp.set_defaults(func=cmd_verify_manifest_present)

    # verify-contract-chain
    sp = sub.add_parser(
        "verify-contract-chain",
        help=(
            "Walk every *.md task file in tasks-dir (excluding README.md), "
            "parse Expects/Produces bullets, verify chain integrity. "
            "Exit 0 when clean; exit 2 when orphan/unsatisfied findings exist "
            "or when no task files are found."
        ),
    )
    sp.add_argument("tasks_dir", help="Directory containing task *.md files.")
    sp.set_defaults(func=cmd_verify_contract_chain)

    # verify-ac-coverage
    sp = sub.add_parser(
        "verify-ac-coverage",
        help=(
            "Parse spec §5 ACs and task **Spec criteria**: lines. "
            "Report any spec ACs not referenced by any task. "
            "Exit 0 when all covered or zero ACs; exit 2 when uncovered ACs "
            "exist or when tasks-dir/spec are unreadable."
        ),
    )
    sp.add_argument("tasks_dir", help="Directory containing task *.md files.")
    sp.add_argument("spec_path", help="Path to spec.md.")
    sp.set_defaults(func=cmd_verify_ac_coverage)

    # verify-property-coverage
    sp = sub.add_parser(
        "verify-property-coverage",
        help=(
            "Verify every pure-builder target declared in the sibling "
            "plan-handoff.json (breakdown_seeds.pure_builder_targets) is "
            "covered by a task's '**Property targets**:' line. "
            "Exit 0 when no targets are declared or all are covered; "
            "exit 2 on a missing/malformed handoff, no task files found "
            "(when targets are declared), or an uncovered target."
        ),
    )
    sp.add_argument("tasks_dir", help="Directory containing task *.md files.")
    sp.add_argument(
        "--plan-handoff",
        dest="plan_handoff",
        default=None,
        help=(
            "Path to plan-handoff.json (default: "
            "<tasks-dir's parent>/plan-handoff.json)."
        ),
    )
    sp.set_defaults(func=cmd_verify_property_coverage)

    # verify-dead-code-coverage
    sp = sub.add_parser(
        "verify-dead-code-coverage",
        help=(
            "Verify every change-induced dead-code row declared in the "
            "sibling plan-handoff.json (breakdown_seeds.dead_code_rows) is "
            "covered by EXACTLY ONE task's '**Dead code removal**:' field. "
            "Exit 0 when no rows are declared or all are covered by "
            "exactly one task; exit 2 on a missing/malformed handoff, no "
            "task files found (when rows are declared), an uncovered row, "
            "or a row claimed by 2+ tasks."
        ),
    )
    sp.add_argument("tasks_dir", help="Directory containing task *.md files.")
    sp.add_argument(
        "--plan-handoff",
        dest="plan_handoff",
        default=None,
        help=(
            "Path to plan-handoff.json (default: "
            "<tasks-dir's parent>/plan-handoff.json)."
        ),
    )
    sp.set_defaults(func=cmd_verify_dead_code_coverage)

    # finalize-handoff
    sp = sub.add_parser(
        "finalize-handoff",
        help=(
            "Parse tasks/*.md (+ tasks/README.md) into a schema-validated "
            "breakdown-handoff.json (sibling to plan.md). "
            "Exit 0 + prints written path; exit 2 on missing files, "
            "placeholder agent, or schema failure; exit 1 on I/O write failure."
        ),
    )
    sp.add_argument("plan_path", help="Path to plan.md.")
    sp.add_argument(
        "--completed-at",
        dest="completed_at",
        default=None,
        help="Optional UTC ISO timestamp (e.g. 2026-01-01T12:00:00Z). "
             "Defaults to now. Useful for deterministic test output.",
    )
    sp.add_argument(
        "--agents-dir",
        dest="agents_dir",
        default=".claude/agents",
        help="Path to the installed agent roster directory (default: .claude/agents). "
             "In wrapper mode, pass the install root's .claude/agents path.",
    )
    sp.set_defaults(func=cmd_finalize_handoff_breakdown)

    # render-implement-handoff
    sp = sub.add_parser(
        "render-implement-handoff",
        help=(
            "Emit the manual next-step block targeting /devforge:implement. "
            "Reads plan.md + tasks/*.md to compute task count and first task. "
            "Exit 0; exit 2 if plan.md or tasks-dir is missing or empty."
        ),
    )
    sp.add_argument("plan_path", help="Path to plan.md.")
    sp.set_defaults(func=cmd_render_implement_handoff)

    sp = sub.add_parser(
        "read-memory",
        help=(
            "Read .devforge/memory.md under CWD and emit JSON: memory_present, "
            "memory_excerpt (the populated `## ` sections, Task Outcomes "
            "excluded), memory_state "
            "(absent/stub/populated). Takes no arguments; always exits 0. "
            "Absent/stub is the correct state on a fresh install, not a fault."
        ),
    )
    sp.set_defaults(func=cmd_read_memory)

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
