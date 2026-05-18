"""constitute_helper — composes the constitution.md state file for /constitute.

Owns the shape of `.devforge/constitute.json` (canonical state) and
`<install_root>/constitution.md` (render artifact). Schema-anchored:
helper owns markdown structure, LLM provides values via setters. Mirrors
the helper-owns-shape pattern established by init_helper / configure_helper /
generate_docs_helper.

`/constitute` is the fourth and last command in the 4-command pivot
(init-forge → generate-docs → configure → constitute).

Step 4 (this commit): `validate` — 4-dimension content quality framework.
  Dim 1 (weight 0.30) slot_fill: required sections/fields populated (9 slots
    for existing-codebase, 10 for greenfield). Pass >= 0.95.
  Dim 2 (weight 0.25) citation: path-like tokens in rule text / table cells /
    code_example.annotation resolved relative to install_root; package-name
    lookup via init.yaml.packages_detected. Pass >= 0.95.
  Dim 3 (weight 0.25) code_syntax: python → ast.parse; json → json.loads;
    ts/tsx/js/jsx → balanced-brace + non-empty heuristic; other → non-empty.
    Pass >= 0.95. Zero examples → N/A (1.0).
  Dim 4 (weight 0.20) rule_tag: every rule tag in closed enum. Pass = 1.0.
  Composite >= 0.95 → exit 0; below → exit 2 (stderr enumerates failures).
  stdout always receives JSON: {composite, dimensions, failed_items}.
  Exit 1 on state file unreadable/corrupted.

Step 3 (prior): `render` walks FIELD_SCHEMA + state to emit
constitution.md (7 sections — Section 7 only when mode == greenfield).
Atomic write at <install_root>/constitution.md. Exit 0 / 1 (state
unreadable) / 2 (required field missing). `verify` checks required
scalars + closed-enum tag membership + table column/row consistency +
scaffolding-guide shape (greenfield mode requires non-null) + minimal
round-trip identity check; exit 0 / 2. `summary` writes deterministic
field-by-field stdout report (mirrors init/configure summary); exit 0
on success, 1 on corrupted JSON.

Step 2 (prior): 5 validation helpers (_validate_scalar, _validate_enum
case-insensitive → canonical, _validate_string_array JSON-array OR comma-sep,
_validate_path_value, _validate_verbatim); _load / _dump / _lock_file_path /
_state_transaction (fcntl.LOCK_EX on constitute.json.lock sidecar; mirrors
configure_helper plumbing); _find_section helper (first-match across the 4
section_array buckets); 10 setter subcommands (set-project-name, set-mode,
set-dates, set-project-identity, add-section idempotent on (bucket, number),
add-rule, add-table, add-code-example, add-pattern-rule, set-scaffolding-guide).

Step 1 (prior): FIELD_SCHEMA + ENUM_FIELDS populated; default_state()
expanded to full schema shape; four read-* subcommands added (read-init,
read-configure, read-docs, read-glossary). The `reset` subcommand from
Step 0 is preserved and verified unchanged.

FIELD_SCHEMA defines the top-level key order (11 keys):
  project_name, generated_date, last_updated, mode,
  project_identity, architecture_rules, code_quality_standards,
  patterns_and_antipatterns, domain_rules, workflow_rules, scaffolding_guide.

ENUM_FIELDS defines 4 closed enums:
  mode (existing-codebase | greenfield),
  rule_tag (extracted | enforced | universal | project-specific),
  section_tag (universal | project-specific | greenfield-only),
  code_label (CORRECT | WRONG | EXAMPLE).

Section records shape: {number, title, tag, description, rules[], tables[], code_examples[]}.
Rule shape: {tag, text}. Table shape: {columns[], rows[][]}.
CodeExample shape: {label, language, code, annotation}.

State format is JSON (not YAML) — constitute data is 2-3 levels deep
(Section → rules + tables + code_examples per bucket per scope) and
JSON's native nesting fits cleaner than extending the configure-style
YAML emitter to handle the depth.

Architecture notes for read-* subcommands:
- read-init reads <devforge_dir>/init.yaml via init_helper.parse_yaml.
- read-configure reads <devforge_dir>/configure.yaml via configure_helper.parse_yaml.
- read-docs reads <install_root>/docs/overview.md + architecture.md via
  configure_helper's section parsers (imported as sibling module).
- read-glossary reads <install_root>/docs/glossary.md and parses per-term
  blocks (## <term> / definition para / Used in: / Related: lines).
- All read-* subcommands: exit 0 on success, 1 if file missing / unreadable,
  2 if malformed (malformed yaml/json/markdown where we can detect it).
- read-docs: malformed markdown → graceful skip of unparseable sections,
  warnings to stderr, exit 0 (best-effort parse).

Stdlib only. Python 3.8+.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Union

try:
    import fcntl  # POSIX-only.
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - non-POSIX fallback path
    # AIDevTeamForge targets POSIX (macOS, Linux, WSL) only. The graceful-
    # degradation flag avoids an import crash on Windows native but no-op
    # locking is NOT a supported configuration: concurrent add-rule
    # invocations on Windows would silently lose writes.
    _HAVE_FCNTL = False


# ---------------------------------------------------------------------------
# Sibling-module import plumbing.
# ---------------------------------------------------------------------------

_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

import init_helper  # noqa: E402
import configure_helper  # noqa: E402


# ---------------------------------------------------------------------------
# Schema — single source of truth for field order and kind.
# ---------------------------------------------------------------------------

OUTPUT_FILE_NAME = "constitute.json"

# Top-level key order is locked. Reordering changes on-disk byte order.
# Kind abbreviations:
#   "scalar"           — string-or-None
#   "date_scalar"      — string-or-None expected as YYYY-MM-DD
#   "enum_scalar"      — string-or-None restricted by ENUM_FIELDS["mode"]
#   "nullable_record"  — None or a nested record. Step 2 setters populate
#                        the dict shape (project_identity = 4 subfields;
#                        scaffolding_guide = 2 subfields). Both default to
#                        None — greenfield mode may legitimately leave
#                        scaffolding_guide null until set, and project_identity
#                        is null until set-project-identity runs in Phase 2.
#   "section_array"    — list of section records (default [])
#   "patterns_section" — dict with 6 named buckets, each a rule_array
FIELD_SCHEMA = (
    ("project_name",              "scalar"),
    ("generated_date",            "date_scalar"),
    ("last_updated",              "date_scalar"),
    ("mode",                      "enum_scalar"),
    ("project_identity",          "nullable_record"),
    ("architecture_rules",        "section_array"),
    ("code_quality_standards",    "section_array"),
    ("patterns_and_antipatterns", "patterns_section"),
    ("domain_rules",              "section_array"),
    ("workflow_rules",            "section_array"),
    ("scaffolding_guide",         "nullable_record"),
)

# Closed enum sets. Step 2 setters enforce these at set-time.
# Exposed here so Step 2 can import and tests can validate completeness.
ENUM_FIELDS = {
    "mode":        {"existing-codebase", "greenfield"},
    "rule_tag":    {"extracted", "enforced", "universal", "project-specific"},
    "section_tag": {"universal", "project-specific", "greenfield-only"},
    "code_label":  {"CORRECT", "WRONG", "EXAMPLE"},
}

# Patterns-and-antipatterns bucket names (locked order for deterministic JSON).
_PATTERNS_BUCKETS = (
    "always_universal",
    "always_project_specific",
    "never_universal",
    "never_project_specific",
    "prefer_universal",
    "prefer_project_specific",
)


# ---------------------------------------------------------------------------
# State shape helpers.
# ---------------------------------------------------------------------------


def _empty_section() -> dict:
    """Return a fresh section record with all subfields at defaults."""
    return {
        "number": None,
        "title": None,
        "tag": None,
        "description": None,
        "rules": [],
        "tables": [],
        "code_examples": [],
    }


def _empty_patterns_section() -> dict:
    """Return the patterns_and_antipatterns 6-bucket default."""
    return {bucket: [] for bucket in _PATTERNS_BUCKETS}


def _empty_scaffolding_guide() -> dict:
    """Return a fresh scaffolding_guide record (when non-null)."""
    return {
        "starter_directories": [],
        "sample_files": [],
    }


# ---------------------------------------------------------------------------
# Public API: default_state + _write_state + cmd_reset.
# ---------------------------------------------------------------------------


def default_state() -> dict:
    """Return a fresh defaults state dict matching FIELD_SCHEMA.

    All scalars default to None; section_arrays default to []; the
    patterns_section defaults to its 6-bucket structure with empty lists;
    project_identity and scaffolding_guide default to None (nullable).
    """
    state = {}  # type: Dict[str, object]
    for name, kind in FIELD_SCHEMA:
        if kind in ("scalar", "date_scalar", "enum_scalar", "nullable_record"):
            state[name] = None
        elif kind == "section_array":
            state[name] = []
        elif kind == "patterns_section":
            state[name] = _empty_patterns_section()
        else:
            raise AssertionError("unknown field kind: {0}".format(kind))
    return state


def _output_file_path(devforge_dir: Union[str, "os.PathLike[str]"]) -> Path:
    """Return the canonical state file path for the given devforge dir."""
    return Path(devforge_dir) / OUTPUT_FILE_NAME


def _write_state(state: dict, devforge_dir: Union[str, "os.PathLike[str]"]) -> None:
    """Atomically write `state` to the output JSON path.

    Uses tempfile.mkstemp in the same directory as the target so
    os.replace is atomic on a single filesystem. flush + fsync before
    os.replace adds a durability barrier. On any failure, attempts to
    remove the temp file and re-raises.
    """
    target = _output_file_path(devforge_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="constitute-",
        suffix=".json.tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=False)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def cmd_reset(args: argparse.Namespace) -> int:
    """Write a fresh defaults state file. Idempotent: byte-identical re-runs."""
    _write_state(default_state(), args.devforge_dir)
    return 0


# ---------------------------------------------------------------------------
# _load / _dump / _lock_file_path / _state_transaction helpers.
# ---------------------------------------------------------------------------


def _load(devforge_dir: Union[str, "os.PathLike[str]"]) -> dict:
    """Load constitute.json into a state dict.

    If the file is missing, returns default_state() — normal on first run.
    Malformed JSON propagates json.JSONDecodeError so the caller can exit
    non-zero with a clear message rather than silently resetting.
    """
    path = _output_file_path(devforge_dir)
    if not path.exists():
        return default_state()
    text = path.read_text(encoding="utf-8")
    return json.loads(text)


def _dump(state: dict, devforge_dir: Union[str, "os.PathLike[str]"]) -> None:
    """Write state dict to constitute.json atomically.

    Thin wrapper around _write_state so setters can call paired
    _load/_dump without depending on _write_state's signature directly.
    """
    _write_state(state, devforge_dir)


def _lock_file_path(devforge_dir: Union[str, "os.PathLike[str]"]) -> Path:
    """Return the sidecar lock path for constitute.json in devforge_dir.

    The lock is purely metadata — the json is never opened in r+/w+ mode.
    Created on first use; intentionally never deleted.
    """
    return _output_file_path(devforge_dir).parent / (OUTPUT_FILE_NAME + ".lock")


@contextlib.contextmanager
def _state_transaction(devforge_dir: Union[str, "os.PathLike[str]"]) -> Iterator[dict]:
    """Read-modify-write constitute.json under an exclusive process lock.

    Usage:
        with _state_transaction(args.devforge_dir) as state:
            state["project_name"] = "my-project"
        # state written to disk on context exit; NOT written if body raises

    Lock: fcntl.flock(LOCK_EX) on POSIX. On Windows (no fcntl) the
    manager degrades to no-op locking — that platform is out of scope.

    If the body raises ANY exception, the write is skipped and the lock
    is released cleanly. The exception propagates to the caller.
    """
    devforge_path = Path(devforge_dir)
    devforge_path.mkdir(parents=True, exist_ok=True)
    lock_path = _lock_file_path(devforge_dir)
    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        if _HAVE_FCNTL:
            fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            state = _load(devforge_dir)
            yield state
            _dump(state, devforge_dir)
        finally:
            if _HAVE_FCNTL:
                fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Validation helpers (private).
# ---------------------------------------------------------------------------


def _validate_scalar(value: str, field_name: str) -> str:
    """Strip and validate a scalar string value.

    Returns the stripped string. Raises ValueError if empty after strip.
    """
    stripped = value.strip()
    if not stripped:
        raise ValueError("{0}: value cannot be empty".format(field_name))
    return stripped


def _validate_enum(value: str, field_name: str, allowed_set: set) -> str:
    """Validate an enum scalar against an explicit allowed_set.

    Case-insensitive match; returns the canonical (exact-case) member from
    allowed_set. Raises ValueError if empty or no case-insensitive match,
    with an error message that enumerates the allowed values.
    """
    stripped = _validate_scalar(value, field_name)
    # Exact match first (fast path; preserves canonical case).
    if stripped in allowed_set:
        return stripped
    # Case-insensitive fallback: normalize to the canonical member.
    lower_to_canonical = {member.lower(): member for member in allowed_set}
    if stripped.lower() in lower_to_canonical:
        return lower_to_canonical[stripped.lower()]
    raise ValueError(
        "{0}: invalid value {1!r}; allowed: {2}".format(
            field_name, stripped, sorted(allowed_set)
        )
    )


def _validate_string_array(value: str, field_name: str) -> List[str]:
    """Parse a string-array value and validate each item.

    Accepts two input forms:

    1. Comma-separated string (default): ``"vue, vue-router, pinia"`` →
       ``["vue", "vue-router", "pinia"]``.
    2. JSON-array string (when input starts with ``[`` and ends with ``]``
       after strip): ``'["Either<DataError, T>", "Result<Ok, Err>"]'``
       → ``["Either<DataError, T>", "Result<Ok, Err>"]``. JSON form
       allows individual items to contain literal commas without breaking
       the comma split.

    Returns a list of stripped, non-empty strings. Raises ValueError if
    any item is empty after strip, the result list is empty, or the JSON
    form is malformed.
    """
    stripped_value = value.strip()
    items_raw = []  # type: List[str]
    if stripped_value.startswith("[") and stripped_value.endswith("]"):
        # JSON-array form. Decode + validate.
        try:
            decoded = json.loads(stripped_value)
        except ValueError as err:
            raise ValueError(
                "{0}: JSON-array form is malformed: {1}".format(field_name, err)
            )
        if not isinstance(decoded, list):
            raise ValueError(
                "{0}: JSON-array form must decode to a list, got {1}".format(
                    field_name, type(decoded).__name__
                )
            )
        for item in decoded:
            if not isinstance(item, str):
                raise ValueError(
                    "{0}: JSON-array items must be strings, got {1}".format(
                        field_name, type(item).__name__
                    )
                )
            items_raw.append(item)
    else:
        # Comma-separated form (default).
        items_raw = stripped_value.split(",")

    result = []
    for raw in items_raw:
        stripped = raw.strip()
        if not stripped:
            raise ValueError(
                "{0}: each item must be non-empty (got an empty item in "
                "{1!r}; for values with literal commas use JSON-array form)".format(
                    field_name, value
                )
            )
        result.append(stripped)
    if not result:
        raise ValueError("{0}: value cannot be empty".format(field_name))
    return result


def _validate_path_value(value: str, field_name: str) -> str:
    """Validate a path-shaped string: non-empty after strip, no newlines.

    Paths should not contain newline or carriage-return characters.
    Returns the stripped string. Raises ValueError on failure.
    """
    stripped = value.strip()
    if not stripped:
        raise ValueError("{0}: value cannot be empty".format(field_name))
    if "\n" in stripped or "\r" in stripped:
        raise ValueError(
            "{0}: path value must not contain newline characters".format(field_name)
        )
    return stripped


def _validate_verbatim(value: str, field_name: str) -> str:
    """Validate a verbatim multi-line value: non-empty after outer strip only.

    Internal whitespace is preserved — rule text and code examples are
    multi-line. Returns the original value (NOT stripped). Raises
    ValueError if the value is all whitespace.
    """
    if not value.strip():
        raise ValueError("{0}: value cannot be empty".format(field_name))
    return value


# ---------------------------------------------------------------------------
# Section + pattern lookup helpers (private).
# ---------------------------------------------------------------------------

_SECTION_BUCKET_TO_KEY = {
    "architecture":  "architecture_rules",
    "code-quality":  "code_quality_standards",
    "domain":        "domain_rules",
    "workflow":      "workflow_rules",
}

_PATTERN_SCOPE_TO_SUFFIX = {
    "universal":        "universal",
    "project-specific": "project_specific",
}


def _find_section(state: dict, number: str):
    """Return (bucket_list, section_dict) for the section with given number.

    Searches in this order: architecture_rules, code_quality_standards,
    domain_rules, workflow_rules. Numbers are strings ("2.1", "3.5", etc.).
    Returns (None, None) if not found.

    First-match policy: if the same number exists in two buckets (e.g.,
    "1.1" in both architecture_rules and workflow_rules), the architecture
    bucket wins — add-rule / add-table / add-code-example would always
    route to the architecture copy and silently miss the workflow copy.
    The Phase 5 spec convention numbers each bucket non-overlappingly
    (2.x = architecture, 3.x = code-quality, 5.x = domain, 6.x = workflow,
    matching cse-strata-ws-forge/constitution.md), so cross-bucket
    duplicates are a caller bug to avoid, not a helper bug to enforce.
    """
    for bucket_key in ("architecture_rules", "code_quality_standards",
                       "domain_rules", "workflow_rules"):
        bucket = state.get(bucket_key, [])
        for section in bucket:
            if section.get("number") == number:
                return bucket, section
    return None, None


# ---------------------------------------------------------------------------
# Error helpers.
# ---------------------------------------------------------------------------


def _die(message: str, code: int = 1) -> int:
    """Write an error message to stderr and return the given exit code."""
    sys.stderr.write("constitute_helper: {0}\n".format(message))
    return code


# ---------------------------------------------------------------------------
# Universal-section constants.
# ---------------------------------------------------------------------------

# Closed list of universal section numbers (§-prefixed, as used in return shapes).
_UNIVERSAL_SECTIONS = (
    "§3.5", "§3.6", "§3.7",
    "§4.1", "§4.2", "§4.3",
    "§6.1", "§6.2", "§6.3", "§6.4",
)

# Maps patterns_and_antipatterns bucket names to §-number keys.
_PATTERNS_BUCKET_TO_SECTION = {
    "always_universal":  "§4.1",
    "never_universal":   "§4.2",
    "prefer_universal":  "§4.3",
}


# ---------------------------------------------------------------------------
# Private parsers for forge-internal:verify-universal-defaults substrate.
# ---------------------------------------------------------------------------


def _parse_universal_blocks(constitution_md_path: "Path") -> "Dict[str, Dict]":
    """Parse universal sections from a constitution.md file.

    Reads the markdown file at `constitution_md_path` and returns a dict
    keyed by §-prefixed section number (e.g. "§3.5") for each section in
    _UNIVERSAL_SECTIONS.

    Return shape per section::

        {
            "heading": "<exact heading text after the section number>",
            "rules": [
                {"tag_or_label": "<label>", "body": "<rule body text>"},
                ...
            ],
        }

    Section-specific splitting:
    - §3.6: splits the SOLID block into individual sub-rules (one entry per
      ``- **Name**`` bullet) plus DRY and KISS as additional entries.
      Single Responsibility is included when present.
    - §4.1, §4.2, §4.3: splits on ``- **Label.**`` / ``- **Label**`` bullets
      (each top-level bullet becomes one rule entry).
    - All other sections: emits a single rule entry with tag_or_label equal to
      the section heading and body equal to the full section body text.

    Missing file: raises ``FileNotFoundError`` (caller decides how to handle).
    Section absent from file: that section key is absent from the returned dict.
    """
    text = Path(constitution_md_path).read_text(encoding="utf-8")
    lines = text.splitlines()

    # --- Step 1: locate each heading and extract the body slice. ---
    # Match lines like "### 3.5 Universal Code Quality [universal]"
    # or "## 3. Code Quality Standards" (## level used for H2 section separators).
    # We only care about ### headings that carry a section number matching our
    # universal list.  We detect section boundaries by the next heading at the
    # same or higher level (## or ###).
    heading_re = re.compile(r"^(#{2,})\s+([\d]+\.[\d]+(?:\.[\d]+)*)\s+(.*)")
    # Collect (line_index, level, number, title_raw).
    heading_positions = []  # type: List[tuple]
    for idx, line in enumerate(lines):
        m = heading_re.match(line)
        if m:
            level = len(m.group(1))
            number = m.group(2)
            title_raw = m.group(3).strip()
            heading_positions.append((idx, level, number, title_raw))

    # Build a map: number_str -> (title_raw, body_lines).
    section_map = {}  # type: Dict[str, tuple]
    for i, (idx, level, number, title_raw) in enumerate(heading_positions):
        # Body ends at the next heading of same or higher level (lower #-count).
        body_start = idx + 1
        body_end = len(lines)
        for j in range(i + 1, len(heading_positions)):
            nxt_idx, nxt_level, _, _ = heading_positions[j]
            if nxt_level <= level:
                body_end = nxt_idx
                break
        body_lines = lines[body_start:body_end]
        section_map[number] = (title_raw, body_lines)

    # --- Step 2: build the result dict for universal sections. ---
    result = {}  # type: Dict[str, Dict]
    for sect_key in _UNIVERSAL_SECTIONS:
        # Strip the leading §.
        number = sect_key[1:]  # e.g. "3.5"
        if number not in section_map:
            continue
        title_raw, body_lines = section_map[number]
        # Strip [tag] suffix from title_raw (e.g. "[universal]").
        heading = re.sub(r"\s*\[.*?\]\s*$", "", title_raw).strip()
        body_text = "\n".join(body_lines).strip()

        if sect_key == "§3.6":
            rules = _split_design_principles(body_text)
        elif sect_key in ("§4.1", "§4.2", "§4.3"):
            rules = _split_bullet_rules(heading, body_text)
        else:
            rules = [{"tag_or_label": heading, "body": body_text}]

        result[sect_key] = {"heading": heading, "rules": rules}

    return result


def _split_design_principles(body_text: str) -> "List[Dict]":
    """Split §3.6 body into individual design-principle rule entries.

    Recognises two block shapes:
    - SOLID sub-rules: ``- **Name** — ...`` top-level bullets within the
      ``**SOLID:**`` block.  Each becomes a separate rule with the principle
      name as tag_or_label.
    - Top-level bold-header blocks (DRY, KISS): ``**Name (...):**`` paragraphs.
      Each becomes a rule with the short name as tag_or_label and the full
      paragraph text (including its sub-bullets) as body.

    Returns a list of rule dicts in document order.
    """
    rules = []  # type: List[Dict]

    # Split on bold top-level block headers: lines like "**SOLID:**", "**DRY ...:**".
    # These are bare bold lines (not inside a list item).
    block_header_re = re.compile(r"^\*\*([^*]+):\*\*\s*$")
    # SOLID sub-rule bullets: "- **Name** — ..." or "- **Name —..."
    solid_bullet_re = re.compile(r"^- \*\*([^*]+)\*\*")

    lines = body_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        bm = block_header_re.match(line.strip())
        if bm:
            block_name = bm.group(1).strip()
            # Gather block body (lines until next bare bold-header or end).
            block_lines = []
            i += 1
            while i < len(lines):
                peek = lines[i]
                if block_header_re.match(peek.strip()):
                    break
                block_lines.append(peek)
                i += 1
            block_body = "\n".join(block_lines).strip()

            if block_name == "SOLID":
                # Split the SOLID block into individual sub-rule entries.
                rules.extend(_split_solid_sub_rules(block_body))
            else:
                # DRY, KISS, or any future top-level block.
                # Use the first word(s) before parenthesis / space as label.
                short_name = re.split(r"\s*[\(\s]", block_name)[0].strip()
                rules.append({"tag_or_label": short_name, "body": block_body})
        else:
            i += 1

    return rules


def _split_solid_sub_rules(solid_body: str) -> "List[Dict]":
    """Split the SOLID block body into one entry per principle.

    Each principle starts with ``- **Name** — ...`` at the top indent level.
    Lines that are continuations (indented or blank) belong to the previous
    principle.  Returns list of dicts with tag_or_label and body.
    """
    bullet_re = re.compile(r"^- \*\*([^*]+)\*\*")
    lines = solid_body.splitlines()
    entries = []   # type: List[tuple]  # (name, [body_lines])
    current_name = None
    current_lines = []  # type: List[str]

    for line in lines:
        m = bullet_re.match(line)
        if m:
            if current_name is not None:
                entries.append((current_name, current_lines))
            current_name = m.group(1).strip()
            # Body starts after "- **Name**" on the same line.
            rest = line[m.end():].strip()
            # Strip leading " — " or "—" separator.
            rest = re.sub(r"^\s*—\s*", "", rest)
            current_lines = [rest] if rest else []
        else:
            if current_name is not None:
                current_lines.append(line)

    if current_name is not None:
        entries.append((current_name, current_lines))

    result = []
    for name, body_lines in entries:
        body = "\n".join(body_lines).strip()
        result.append({"tag_or_label": name, "body": body})
    return result


def _split_bullet_rules(heading: str, body_text: str) -> "List[Dict]":
    """Split §4.1 / §4.2 / §4.3 body into per-bullet rule entries.

    Each top-level bullet ``- **Label.** ...`` or ``- **Label** ...``
    becomes a rule entry.  Continuation lines (indented or blank) belong to
    the previous bullet.

    If no bullets are found, falls back to a single rule entry with
    ``tag_or_label = heading`` and ``body = body_text``.
    """
    bullet_re = re.compile(r"^- \*\*([^*]+?)[.\*]*\*\*")
    lines = body_text.splitlines()
    entries = []   # type: List[tuple]
    current_label = None
    current_lines = []  # type: List[str]

    for line in lines:
        m = bullet_re.match(line)
        if m:
            if current_label is not None:
                entries.append((current_label, current_lines))
            raw_label = m.group(1).strip().rstrip(".")
            current_label = raw_label
            rest = line[m.end():].strip().lstrip("* ")
            rest = re.sub(r"^\.?\s*", "", rest)
            current_lines = [rest] if rest else []
        else:
            if current_label is not None:
                current_lines.append(line)
            # Lines before first bullet (e.g. blank lines) are ignored.

    if current_label is not None:
        entries.append((current_label, current_lines))

    if not entries:
        return [{"tag_or_label": heading, "body": body_text}]

    result = []
    for label, body_lines in entries:
        body = "\n".join(body_lines).strip()
        result.append({"tag_or_label": label, "body": body})
    return result


def _extract_universal_rules_from_state(
    constitute_json_path: "Path",
) -> "Dict[str, Dict]":
    """Extract universal-section rules from a .devforge/constitute.json file.

    Reads the JSON state file at `constitute_json_path` and returns a dict
    keyed by §-prefixed section number for each universal section that has
    rules populated in the state.

    Return shape matches ``_parse_universal_blocks``::

        {
            "§3.5": {
                "heading": "<section title from state>",
                "rules": [
                    {"tag_or_label": "<rule tag>", "body": "<rule text>"},
                    ...
                ],
            },
            ...
        }

    Sources:
    - ``code_quality_standards``, ``workflow_rules``: sections with
      ``tag == "universal"``, keyed by ``§<section.number>``.  Only sections
      whose number matches ``_UNIVERSAL_SECTIONS`` (stripped of §) are included.
    - ``patterns_and_antipatterns``: ``always_universal`` → §4.1,
      ``never_universal`` → §4.2, ``prefer_universal`` → §4.3.  Rules in
      each bucket are included regardless of the rule's own ``tag`` field.

    Rule mapping: each ``{"tag": t, "text": txt}`` record maps to
    ``{"tag_or_label": t, "body": txt}``.

    Returns ``{}`` if the state file has no universal sections populated.
    Raises ``FileNotFoundError`` if the path does not exist.
    Raises ``json.JSONDecodeError`` if the file is malformed JSON.
    """
    text = Path(constitute_json_path).read_text(encoding="utf-8")
    state = json.loads(text)

    result = {}  # type: Dict[str, Dict]

    # Universal section numbers stripped of §, for fast membership check.
    universal_numbers = {s[1:] for s in _UNIVERSAL_SECTIONS}

    # --- Walk section_array buckets. ---
    for bucket_key in ("code_quality_standards", "workflow_rules"):
        for section in state.get(bucket_key, []):
            if section.get("tag") != "universal":
                continue
            number = section.get("number")
            if number is None or number not in universal_numbers:
                continue
            sect_key = "§{0}".format(number)
            title = section.get("title") or ""
            rules_raw = section.get("rules", [])
            rules = [
                {"tag_or_label": r.get("tag", ""), "body": r.get("text", "")}
                for r in rules_raw
            ]
            result[sect_key] = {"heading": title, "rules": rules}

    # --- Walk patterns_and_antipatterns universal buckets. ---
    patterns = state.get("patterns_and_antipatterns", {})
    for bucket_name, sect_key in _PATTERNS_BUCKET_TO_SECTION.items():
        bucket_rules = patterns.get(bucket_name, [])
        if not bucket_rules:
            continue
        rules = [
            {"tag_or_label": r.get("tag", ""), "body": r.get("text", "")}
            for r in bucket_rules
        ]
        result[sect_key] = {"heading": bucket_name, "rules": rules}

    return result


# ---------------------------------------------------------------------------
# Setter subcommands (10).
# ---------------------------------------------------------------------------


def cmd_set_project_name(args: argparse.Namespace) -> int:
    """Set project_name scalar."""
    try:
        value = _validate_scalar(args.value, "project_name")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["project_name"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-project-name: {0}".format(err))
    return 0


def cmd_set_mode(args: argparse.Namespace) -> int:
    """Set mode enum (existing-codebase | greenfield)."""
    try:
        value = _validate_enum(args.value, "mode", ENUM_FIELDS["mode"])
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["mode"] = value
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-mode: {0}".format(err))
    return 0


def cmd_set_dates(args: argparse.Namespace) -> int:
    """Set generated_date and last_updated (both YYYY-MM-DD)."""
    date_re = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for date_value, field_name in (
        (args.generated, "generated_date"),
        (args.updated, "last_updated"),
    ):
        if not date_re.match(date_value):
            return _die(
                "{0}: invalid date format {1!r}; expected YYYY-MM-DD".format(
                    field_name, date_value
                ),
                code=2,
            )
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["generated_date"] = args.generated
            state["last_updated"] = args.updated
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-dates: {0}".format(err))
    return 0


def cmd_set_project_identity(args: argparse.Namespace) -> int:
    """Set project_identity record (name, type, domain, stack). Replaces prior value."""
    try:
        name = _validate_scalar(args.name, "project_identity.name")
        ptype = _validate_scalar(args.type, "project_identity.type")
        domain = _validate_scalar(args.domain, "project_identity.domain")
        stack = _validate_scalar(args.stack, "project_identity.stack")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        with _state_transaction(args.devforge_dir) as state:
            state["project_identity"] = {
                "name": name,
                "type": ptype,
                "domain": domain,
                "stack": stack,
            }
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-project-identity: {0}".format(err))
    return 0


def cmd_add_section(args: argparse.Namespace) -> int:
    """Append (or replace-metadata-of) a Section in the given bucket.

    Idempotent on (bucket, number): second call with same (bucket, number)
    replaces the section's metadata while preserving its rules/tables/
    code_examples. Idempotency is bucket-local — same number in a different
    bucket creates a phantom duplicate that downstream add-rule will never
    reach (per _find_section's first-match policy). Phase 5 spec convention
    avoids this by numbering each bucket non-overlappingly.
    """
    bucket_arg = args.bucket
    if bucket_arg not in _SECTION_BUCKET_TO_KEY:
        return _die(
            "add-section: unknown bucket {0!r}; allowed: {1}".format(
                bucket_arg, sorted(_SECTION_BUCKET_TO_KEY.keys())
            ),
            code=2,
        )
    bucket_key = _SECTION_BUCKET_TO_KEY[bucket_arg]

    number = args.number
    if not re.match(r"^\d+(\.\d+)*$", number):
        return _die(
            "add-section: invalid section number {0!r}; expected format like '2', '2.1', '5.3.1'".format(number),
            code=2,
        )

    try:
        title = _validate_scalar(args.title, "section.title")
    except ValueError as err:
        return _die(str(err), code=2)

    tag = None
    if args.tag is not None:
        try:
            tag = _validate_enum(args.tag, "section_tag", ENUM_FIELDS["section_tag"])
        except ValueError as err:
            return _die(str(err), code=2)

    description = args.description  # Optional; no validation beyond presence.

    try:
        with _state_transaction(args.devforge_dir) as state:
            bucket = state[bucket_key]
            # Idempotency: look for existing section with same number.
            for existing in bucket:
                if existing.get("number") == number:
                    # Replace metadata; preserve content arrays.
                    existing["title"] = title
                    existing["tag"] = tag
                    existing["description"] = description
                    break
            else:
                # New section.
                section = _empty_section()
                section["number"] = number
                section["title"] = title
                section["tag"] = tag
                section["description"] = description
                bucket.append(section)
    except (OSError, json.JSONDecodeError) as err:
        return _die("add-section: {0}".format(err))
    return 0


def cmd_add_rule(args: argparse.Namespace) -> int:
    """Append a rule to the section identified by --section number."""
    try:
        tag = _validate_enum(args.tag, "rule_tag", ENUM_FIELDS["rule_tag"])
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        text = _validate_verbatim(args.text, "rule.text")
    except ValueError as err:
        return _die(str(err), code=2)

    # Pre-check section exists (read-only — no lock). Avoids entering the
    # _state_transaction on a guaranteed-fail path; `return` inside the
    # with-block would still trigger _dump and silently re-write identical
    # state, breaking the transaction's "NOT written if body raises" contract.
    try:
        prev_state = _load(args.devforge_dir)
    except (OSError, ValueError) as err:
        return _die("add-rule: {0}".format(err))
    if _find_section(prev_state, args.section)[1] is None:
        return _die(
            "add-rule: section {0!r} not found; run add-section first".format(
                args.section
            ),
            code=2,
        )

    try:
        with _state_transaction(args.devforge_dir) as state:
            _bucket, section = _find_section(state, args.section)
            # Race window (concurrent delete) is impossible today — no
            # delete-section subcmd exists. assert aborts the transaction
            # cleanly via exception propagation if a future subcmd changes that.
            assert section is not None, (
                "add-rule: section {0!r} disappeared between check and lock".format(
                    args.section
                )
            )
            section["rules"].append({"tag": tag, "text": text})
    except (OSError, json.JSONDecodeError) as err:
        return _die("add-rule: {0}".format(err))
    return 0


def cmd_add_table(args: argparse.Namespace) -> int:
    """Append a table to the section identified by --section number."""
    try:
        columns = _validate_string_array(args.columns, "table.columns")
    except ValueError as err:
        return _die(str(err), code=2)

    try:
        rows_raw = json.loads(args.rows_json)
    except ValueError as err:
        return _die(
            "add-table: --rows-json is malformed JSON: {0}".format(err), code=2
        )
    if not isinstance(rows_raw, list):
        return _die(
            "add-table: --rows-json must be a JSON array of arrays, got {0}".format(
                type(rows_raw).__name__
            ),
            code=2,
        )
    rows = []  # type: List[List[str]]
    for i, row in enumerate(rows_raw):
        if not isinstance(row, list):
            return _die(
                "add-table: row {0} must be a JSON array, got {1}".format(
                    i, type(row).__name__
                ),
                code=2,
            )
        if len(row) != len(columns):
            return _die(
                "add-table: row {0} has {1} cells but table has {2} columns".format(
                    i, len(row), len(columns)
                ),
                code=2,
            )
        row_strs = []
        for j, cell in enumerate(row):
            if not isinstance(cell, str):
                return _die(
                    "add-table: row {0} cell {1} must be a string, got {2}".format(
                        i, j, type(cell).__name__
                    ),
                    code=2,
                )
            row_strs.append(cell)
        rows.append(row_strs)

    # Pre-check section exists outside the transaction; see cmd_add_rule.
    try:
        prev_state = _load(args.devforge_dir)
    except (OSError, ValueError) as err:
        return _die("add-table: {0}".format(err))
    if _find_section(prev_state, args.section)[1] is None:
        return _die(
            "add-table: section {0!r} not found; run add-section first".format(
                args.section
            ),
            code=2,
        )

    try:
        with _state_transaction(args.devforge_dir) as state:
            _bucket, section = _find_section(state, args.section)
            assert section is not None, (
                "add-table: section {0!r} disappeared between check and lock".format(
                    args.section
                )
            )
            section["tables"].append({"columns": columns, "rows": rows})
    except (OSError, json.JSONDecodeError) as err:
        return _die("add-table: {0}".format(err))
    return 0


def cmd_add_code_example(args: argparse.Namespace) -> int:
    """Append a code example to the section identified by --section number."""
    try:
        label = _validate_enum(args.label, "code_label", ENUM_FIELDS["code_label"])
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        language = _validate_scalar(args.language, "code_example.language")
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        code = _validate_verbatim(args.code, "code_example.code")
    except ValueError as err:
        return _die(str(err), code=2)
    annotation = args.annotation  # Optional; no validation.

    # Pre-check section exists outside the transaction; see cmd_add_rule.
    try:
        prev_state = _load(args.devforge_dir)
    except (OSError, ValueError) as err:
        return _die("add-code-example: {0}".format(err))
    if _find_section(prev_state, args.section)[1] is None:
        return _die(
            "add-code-example: section {0!r} not found; run add-section first".format(
                args.section
            ),
            code=2,
        )

    try:
        with _state_transaction(args.devforge_dir) as state:
            _bucket, section = _find_section(state, args.section)
            assert section is not None, (
                "add-code-example: section {0!r} disappeared between check and lock".format(
                    args.section
                )
            )
            section["code_examples"].append({
                "label": label,
                "language": language,
                "code": code,
                "annotation": annotation,
            })
    except (OSError, json.JSONDecodeError) as err:
        return _die("add-code-example: {0}".format(err))
    return 0


def cmd_add_pattern_rule(args: argparse.Namespace) -> int:
    """Append a rule to a patterns_and_antipatterns bucket."""
    allowed_buckets = {"always", "never", "prefer"}
    if args.bucket not in allowed_buckets:
        return _die(
            "add-pattern-rule: unknown bucket {0!r}; allowed: {1}".format(
                args.bucket, sorted(allowed_buckets)
            ),
            code=2,
        )
    if args.scope not in _PATTERN_SCOPE_TO_SUFFIX:
        return _die(
            "add-pattern-rule: unknown scope {0!r}; allowed: {1}".format(
                args.scope, sorted(_PATTERN_SCOPE_TO_SUFFIX.keys())
            ),
            code=2,
        )
    pattern_key = "{0}_{1}".format(args.bucket, _PATTERN_SCOPE_TO_SUFFIX[args.scope])

    try:
        tag = _validate_enum(args.tag, "rule_tag", ENUM_FIELDS["rule_tag"])
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        text = _validate_verbatim(args.text, "pattern_rule.text")
    except ValueError as err:
        return _die(str(err), code=2)

    try:
        with _state_transaction(args.devforge_dir) as state:
            state["patterns_and_antipatterns"][pattern_key].append(
                {"tag": tag, "text": text}
            )
    except (OSError, json.JSONDecodeError) as err:
        return _die("add-pattern-rule: {0}".format(err))
    return 0


def cmd_set_scaffolding_guide(args: argparse.Namespace) -> int:
    """Set scaffolding_guide record (starter_directories + sample_files). Replaces prior value."""
    try:
        starter_dirs = _validate_string_array(args.starter_dirs, "scaffolding_guide.starter_directories")
    except ValueError as err:
        return _die(str(err), code=2)

    try:
        sample_files_raw = json.loads(args.sample_files_json)
    except ValueError as err:
        return _die(
            "set-scaffolding-guide: --sample-files-json is malformed JSON: {0}".format(err),
            code=2,
        )
    if not isinstance(sample_files_raw, list):
        return _die(
            "set-scaffolding-guide: --sample-files-json must be a JSON array, got {0}".format(
                type(sample_files_raw).__name__
            ),
            code=2,
        )
    required_keys = {"path", "language", "content"}
    for i, item in enumerate(sample_files_raw):
        if not isinstance(item, dict):
            return _die(
                "set-scaffolding-guide: sample file {0} must be a JSON object, got {1}".format(
                    i, type(item).__name__
                ),
                code=2,
            )
        missing = required_keys - set(item.keys())
        if missing:
            return _die(
                "set-scaffolding-guide: sample file {0} is missing keys: {1}".format(
                    i, sorted(missing)
                ),
                code=2,
            )

    try:
        with _state_transaction(args.devforge_dir) as state:
            state["scaffolding_guide"] = {
                "starter_directories": starter_dirs,
                "sample_files": sample_files_raw,
            }
    except (OSError, json.JSONDecodeError) as err:
        return _die("set-scaffolding-guide: {0}".format(err))
    return 0


# ---------------------------------------------------------------------------
# read-init implementation.
# ---------------------------------------------------------------------------


def cmd_read_init(args: argparse.Namespace) -> int:
    """Read .devforge/init.yaml and emit JSON to stdout.

    Uses init_helper.parse_yaml so the real producer is the inverse.
    Exit 1 if file is missing or unreadable. Exit 2 if malformed yaml.
    """
    init_yaml_path = Path(args.devforge_dir) / init_helper.OUTPUT_FILE_NAME
    if not init_yaml_path.exists():
        return _die(
            "read-init: init.yaml not found at {0}".format(init_yaml_path)
        )
    try:
        text = init_yaml_path.read_text(encoding="utf-8")
    except OSError as err:
        return _die("read-init: cannot read {0}: {1}".format(init_yaml_path, err))
    try:
        state = init_helper.parse_yaml(text)
    except init_helper.YamlParseError as err:
        return _die(
            "read-init: cannot parse {0}: {1}".format(init_yaml_path, err),
            code=2,
        )
    sys.stdout.write(json.dumps(state, indent=2))
    sys.stdout.write("\n")
    return 0


# ---------------------------------------------------------------------------
# read-configure implementation.
# ---------------------------------------------------------------------------


def cmd_read_configure(args: argparse.Namespace) -> int:
    """Read .devforge/configure.yaml and emit JSON to stdout.

    Uses configure_helper.parse_yaml so the real producer is the inverse.
    Exit 1 if file is missing or unreadable. Exit 2 if malformed yaml.
    """
    configure_yaml_path = Path(args.devforge_dir) / configure_helper.OUTPUT_FILE_NAME
    if not configure_yaml_path.exists():
        return _die(
            "read-configure: configure.yaml not found at {0}".format(
                configure_yaml_path
            )
        )
    try:
        text = configure_yaml_path.read_text(encoding="utf-8")
    except OSError as err:
        return _die(
            "read-configure: cannot read {0}: {1}".format(configure_yaml_path, err)
        )
    try:
        state = configure_helper.parse_yaml(text)
    except configure_helper.YamlParseError as err:
        return _die(
            "read-configure: cannot parse {0}: {1}".format(configure_yaml_path, err),
            code=2,
        )
    sys.stdout.write(json.dumps(state, indent=2))
    sys.stdout.write("\n")
    return 0


# ---------------------------------------------------------------------------
# read-docs implementation.
# ---------------------------------------------------------------------------


def cmd_read_docs(args: argparse.Namespace) -> int:
    """Parse docs/overview.md + docs/architecture.md and emit JSON.

    Reuses configure_helper's section parsers (_parse_overview_md,
    _parse_architecture_md, _extract_section). Missing sections emit
    empty values (graceful). Exit 1 if either file is missing.
    """
    install_root = Path(args.install_root)
    overview_path = install_root / "docs" / "overview.md"
    arch_path = install_root / "docs" / "architecture.md"

    if not overview_path.exists():
        return _die(
            "read-docs: docs/overview.md not found at {0}".format(overview_path)
        )
    if not arch_path.exists():
        return _die(
            "read-docs: docs/architecture.md not found at {0}".format(arch_path)
        )

    try:
        overview_text = overview_path.read_text(encoding="utf-8")
    except OSError as err:
        return _die(
            "read-docs: cannot read {0}: {1}".format(overview_path, err)
        )
    try:
        arch_text = arch_path.read_text(encoding="utf-8")
    except OSError as err:
        return _die(
            "read-docs: cannot read {0}: {1}".format(arch_path, err)
        )

    # Delegate parsing to configure_helper's existing section parsers.
    # Missing sections emit empty values; no parse error is raised for
    # missing/malformed markdown (graceful best-effort, warnings to stderr).
    try:
        overview_parsed = configure_helper._parse_overview_md(overview_text)
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(
            "constitute_helper read-docs: warning — overview parse error: {0}\n".format(exc)
        )
        overview_parsed = {}

    try:
        arch_parsed = configure_helper._parse_architecture_md(arch_text)
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(
            "constitute_helper read-docs: warning — architecture parse error: {0}\n".format(exc)
        )
        arch_parsed = {}

    output = {
        "overview": overview_parsed,
        "architecture": arch_parsed,
    }
    sys.stdout.write(json.dumps(output, indent=2))
    sys.stdout.write("\n")
    return 0


# ---------------------------------------------------------------------------
# Glossary parser helpers.
# ---------------------------------------------------------------------------


def _parse_used_in_line(line: str) -> List[str]:
    """Parse '- **Used in**: a, b, c (and N others)' → [a, b, c].

    Strips the ' (and N others)' suffix. Returns [] if the line doesn't
    match the pattern.
    """
    # Expected: "- **Used in**: item1, item2, item3 (and N others)"
    m = re.match(r"^-\s+\*\*Used in\*\*:\s*(.+)$", line.strip())
    if not m:
        return []
    raw = m.group(1).strip()
    # Strip trailing " (and N others)" annotation.
    raw = re.sub(r"\s*\(and \d+ others?\)\s*$", "", raw)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _parse_related_line(line: str) -> List[str]:
    """Parse '- **Related**: a, b, c' → [a, b, c].

    Returns [] if the line doesn't match the pattern.
    """
    m = re.match(r"^-\s+\*\*Related\*\*:\s*(.+)$", line.strip())
    if not m:
        return []
    return [item.strip() for item in m.group(1).split(",") if item.strip()]


def _parse_glossary_md(text: str) -> List[dict]:
    """Parse a glossary.md file into a list of term records.

    Each term block:
      ## <term>
      <definition paragraph(s)>
      - **Used in**: ...
      - **Related**: ...

    Returns list of {"term": str, "definition": str, "used_in": [str], "related": [str]}.
    Empty file → []. Terms with no definition/used_in/related emit empty
    strings / lists for those subfields (graceful).
    """
    lines = text.splitlines()
    terms = []

    current_term = None
    current_body_lines = []  # type: List[str]

    def _flush_term():
        if current_term is None:
            return
        # Separate definition (prose) from metadata lines.
        definition_lines = []
        used_in = []
        related = []
        for body_line in current_body_lines:
            stripped = body_line.strip()
            if stripped.startswith("- **Used in**:"):
                parsed = _parse_used_in_line(stripped)
                if parsed:
                    used_in = parsed
            elif stripped.startswith("- **Related**:"):
                parsed = _parse_related_line(stripped)
                if parsed:
                    related = parsed
            elif re.match(r"^---\s*$", stripped):
                # Skip horizontal-rule / stray frontmatter delimiter lines.
                # Match exactly `---` (with optional trailing whitespace) — a
                # broader startswith("---") would silently swallow definition
                # text that begins with `---` (e.g., CLI flags like `---verbose`).
                pass
            else:
                definition_lines.append(body_line)
        definition = "\n".join(definition_lines).strip()
        terms.append(
            {
                "term": current_term,
                "definition": definition,
                "used_in": used_in,
                "related": related,
            }
        )

    # State: are we inside the YAML frontmatter block?
    in_frontmatter = False
    frontmatter_done = False
    frontmatter_start_seen = False

    for line in lines:
        stripped = line.strip()

        # Handle YAML frontmatter (--- ... ---) at file start.
        if not frontmatter_done:
            if stripped == "---" and not frontmatter_start_seen:
                frontmatter_start_seen = True
                in_frontmatter = True
                continue
            if in_frontmatter:
                if stripped == "---":
                    in_frontmatter = False
                    frontmatter_done = True
                continue
            # No frontmatter present.
            frontmatter_done = True

        # h1 heading (# Title) — skip.
        if stripped.startswith("# ") and not stripped.startswith("## "):
            continue

        # h2 heading = new term.
        if stripped.startswith("## "):
            _flush_term()
            current_term = stripped[3:].strip()
            current_body_lines = []
            continue

        # Inside a term block: collect body lines.
        if current_term is not None:
            current_body_lines.append(line)

    # Flush last term.
    _flush_term()
    return terms


# ---------------------------------------------------------------------------
# read-glossary implementation.
# ---------------------------------------------------------------------------


def cmd_read_glossary(args: argparse.Namespace) -> int:
    """Read docs/glossary.md and emit JSON list of term records.

    Each record: {term, definition, used_in, related}.
    Exit 1 if file is missing or unreadable. Exit 0 for empty file (empty list).
    """
    install_root = Path(args.install_root)
    glossary_path = install_root / "docs" / "glossary.md"

    if not glossary_path.exists():
        return _die(
            "read-glossary: docs/glossary.md not found at {0}".format(glossary_path)
        )
    try:
        text = glossary_path.read_text(encoding="utf-8")
    except OSError as err:
        return _die(
            "read-glossary: cannot read {0}: {1}".format(glossary_path, err)
        )

    terms = _parse_glossary_md(text)
    sys.stdout.write(json.dumps(terms, indent=2))
    sys.stdout.write("\n")
    return 0


# ---------------------------------------------------------------------------
# Step 3: render helpers.
# ---------------------------------------------------------------------------

_MODE_PRETTY = {
    "existing-codebase": "Existing Codebase",
    "greenfield": "Greenfield",
}

# Required top-level scalars for render (fields whose absence → exit 2).
_RENDER_REQUIRED_SCALARS = (
    "project_name",
    "generated_date",
    "last_updated",
    "mode",
)

# project_identity subfields required for render.
_IDENTITY_REQUIRED_SUBFIELDS = ("name", "type", "domain", "stack")


def _render_table(table: dict) -> str:
    """Render a table record as a GFM markdown table string.

    table shape: {columns: [str, ...], rows: [[str, ...], ...]}
    Returns a string ending in a newline. If columns is empty, returns "".
    """
    columns = table.get("columns", [])
    rows = table.get("rows", [])
    if not columns:
        return ""

    # Header row.
    header = "| " + " | ".join(columns) + " |\n"
    # Separator row — fixed width (3 dashes per column minimum).
    sep = "|" + "|".join("-" * (len(c) + 2) if len(c) >= 3 else "----"
                         for c in columns) + "|\n"
    data_lines = []
    for row in rows:
        data_lines.append("| " + " | ".join(str(cell) for cell in row) + " |\n")
    return header + sep + "".join(data_lines)


def _render_code_example(ex: dict) -> str:
    """Render a code example record as a labelled fenced block.

    ex shape: {label, language, code, annotation}
    Format:
        **<label>** — <annotation>   (annotation only if non-null/non-empty)

        ```<language>
        <code>
        ```
    Returns a string. The fenced block is followed by a blank line.
    """
    label = ex.get("label", "EXAMPLE")
    language = ex.get("language", "")
    code = ex.get("code", "")
    annotation = ex.get("annotation")

    parts = []
    if annotation:
        parts.append("**{0}** — {1}\n".format(label, annotation))
    else:
        parts.append("**{0}**\n".format(label))
    parts.append("\n```{0}\n".format(language))
    # Ensure code ends with exactly one newline before the closing fence.
    code_body = code.rstrip("\n")
    parts.append(code_body + "\n")
    parts.append("```\n")
    return "".join(parts)


def _render_section_body(section: dict, include_tag_suffix: bool) -> str:
    """Render a single section record into markdown.

    Produces:
        ### <number> <title> [<tag>]      (tag suffix only when include_tag_suffix=True and tag non-null)
        [<description paragraph>]
        [<table(s)>]
        - [<rule.tag>] <rule.text>
        [<code_example(s)>]

    Returns a string. Always ends without a trailing newline (caller adds spacing).
    """
    number = section.get("number", "")
    title = section.get("title", "")
    tag = section.get("tag")
    description = section.get("description")
    rules = section.get("rules", [])
    tables = section.get("tables", [])
    code_examples = section.get("code_examples", [])

    lines = []
    if include_tag_suffix and tag:
        lines.append("### {0} {1} [{2}]\n".format(number, title, tag))
    else:
        lines.append("### {0} {1}\n".format(number, title))

    if description:
        lines.append("\n{0}\n".format(description))

    for table in tables:
        lines.append("\n")
        lines.append(_render_table(table))

    for rule in rules:
        rule_tag = rule.get("tag", "")
        rule_text = rule.get("text", "")
        lines.append("- [{0}] {1}\n".format(rule_tag, rule_text))

    for ex in code_examples:
        lines.append("\n")
        lines.append(_render_code_example(ex))

    return "".join(lines)


def _render_section_array(
    sections: List[dict],
    h2_title: str,
    intro_text: Optional[str],
    include_tag_suffix: bool,
) -> str:
    """Render a whole section_array bucket as a markdown H2 block.

    If sections is empty, renders:
        ## <h2_title>
        _(no rules defined)_

    intro_text (if non-None) is rendered as a paragraph between the H2 heading
    and the first section. Returns a string; caller adds surrounding --- separators.
    """
    lines = []
    lines.append("## {0}\n".format(h2_title))
    if intro_text:
        lines.append("\n{0}\n".format(intro_text))
    if not sections:
        lines.append("\n_(no rules defined)_\n")
    else:
        for section in sections:
            lines.append("\n")
            lines.append(_render_section_body(section, include_tag_suffix))
    return "".join(lines)


def _render_pattern_bucket(
    patterns_state: dict,
    bucket_key: str,
    heading: str,
) -> str:
    """Render one patterns_and_antipatterns bucket as a ### sub-section.

    Returns a string (heading + bullet list). If empty, renders heading +
    _(no rules defined)_ marker.
    """
    rules = patterns_state.get(bucket_key, [])
    lines = []
    lines.append("### {0}\n".format(heading))
    if not rules:
        lines.append("_(no rules defined)_\n")
    else:
        for rule in rules:
            rule_tag = rule.get("tag", "")
            rule_text = rule.get("text", "")
            lines.append("- [{0}] {1}\n".format(rule_tag, rule_text))
    return "".join(lines)


def _render_constitution(state: dict) -> str:
    """Render state dict into a constitution.md string.

    Returns the full file text. Raises ValueError with a message enumerating
    missing required fields if project_name, generated_date, last_updated,
    mode, or project_identity (with all 4 subfields) are None.
    """
    # --- Required field validation ---
    missing = []
    for field in _RENDER_REQUIRED_SCALARS:
        if state.get(field) is None:
            missing.append(field)
    identity = state.get("project_identity")
    if identity is None:
        missing.append("project_identity")
    else:
        for sub in _IDENTITY_REQUIRED_SUBFIELDS:
            if identity.get(sub) is None:
                missing.append("project_identity.{0}".format(sub))
    if missing:
        raise ValueError(
            "render: missing required fields: {0}".format(", ".join(missing))
        )

    mode = state["mode"]
    mode_pretty = _MODE_PRETTY.get(mode, mode)
    parts = []  # type: List[str]

    # --- Header ---
    parts.append("# Project Constitution — {0}\n".format(state["project_name"]))
    parts.append("\n")
    parts.append("Generated: {0}\n".format(state["generated_date"]))
    parts.append("Last updated: {0}\n".format(state["last_updated"]))
    parts.append("Mode: {0}\n".format(mode_pretty))
    parts.append("\n")
    parts.append(
        "> Sections marked `[universal]` are pre-populated with rules that apply"
        " to ALL projects.\n"
    )
    parts.append(
        "> Sections marked `[project-specific]` are populated by `/constitute`"
        " based on your codebase or interview answers.\n"
    )
    parts.append("\n---\n\n")

    # --- Section 1: Project Identity ---
    parts.append("## 1. Project Identity\n")
    parts.append("\n")
    parts.append("**Name**: {0}\n".format(identity["name"]))
    parts.append("**Type**: {0}\n".format(identity["type"]))
    parts.append("**Domain**: {0}\n".format(identity["domain"]))
    parts.append("**Stack**: {0}\n".format(identity["stack"]))
    parts.append("\n---\n\n")

    # --- Section 2: Architecture Rules ---
    arch_intro = (
        "These rules MUST be followed in every code change. Violating these"
        " rules requires explicit user approval."
    )
    parts.append(_render_section_array(
        state.get("architecture_rules", []),
        "2. Architecture Rules (NON-NEGOTIABLE)",
        arch_intro,
        include_tag_suffix=False,
    ))
    parts.append("\n---\n\n")

    # --- Section 3: Code Quality Standards ---
    parts.append(_render_section_array(
        state.get("code_quality_standards", []),
        "3. Code Quality Standards",
        None,
        include_tag_suffix=True,
    ))
    parts.append("\n---\n\n")

    # --- Section 4: Patterns & Anti-Patterns ---
    pat = state.get("patterns_and_antipatterns", _empty_patterns_section())
    parts.append("## 4. Patterns & Anti-Patterns\n")
    parts.append("\n")
    parts.append(_render_pattern_bucket(pat, "always_universal", "Always Do (Universal)"))
    parts.append("\n")
    parts.append(_render_pattern_bucket(pat, "always_project_specific", "Always Do (Project-Specific)"))
    parts.append("\n")
    parts.append(_render_pattern_bucket(pat, "never_universal", "Never Do (Universal)"))
    parts.append("\n")
    parts.append(_render_pattern_bucket(pat, "never_project_specific", "Never Do (Project-Specific)"))
    parts.append("\n")
    parts.append(_render_pattern_bucket(pat, "prefer_universal", "Prefer (Universal)"))
    parts.append("\n")
    parts.append(_render_pattern_bucket(pat, "prefer_project_specific", "Prefer (Project-Specific)"))
    parts.append("\n---\n\n")

    # --- Section 5: Domain Rules ---
    parts.append(_render_section_array(
        state.get("domain_rules", []),
        "5. Domain Rules",
        None,
        include_tag_suffix=False,
    ))
    parts.append("\n---\n\n")

    # --- Section 6: Workflow Rules ---
    parts.append(_render_section_array(
        state.get("workflow_rules", []),
        "6. Workflow Rules",
        None,
        include_tag_suffix=False,
    ))

    # --- Section 7: Scaffolding Guide (greenfield only) ---
    scaffolding = state.get("scaffolding_guide")
    if mode == "greenfield" and scaffolding is not None:
        parts.append("\n---\n\n")
        parts.append("## 7. Scaffolding Guide [greenfield-only]\n")
        starter_dirs = scaffolding.get("starter_directories", [])
        if starter_dirs:
            parts.append("\n**Starter Directories**:\n")
            for d in starter_dirs:
                parts.append("- {0}\n".format(d))
        sample_files = scaffolding.get("sample_files", [])
        if sample_files:
            parts.append("\n**Sample Files**:\n")
            for sf in sample_files:
                sf_path = sf.get("path", "")
                sf_lang = sf.get("language", "")
                sf_content = sf.get("content", "")
                parts.append("\n#### {0}\n".format(sf_path))
                parts.append("```{0}\n".format(sf_lang))
                content_body = sf_content.rstrip("\n")
                parts.append(content_body + "\n")
                parts.append("```\n")

    # Ensure exactly one trailing newline.
    result = "".join(parts)
    return result.rstrip("\n") + "\n"


def _write_constitution_atomic(text: str, install_root: Union[str, "os.PathLike[str]"]) -> None:
    """Atomically write text to <install_root>/constitution.md.

    Uses tempfile.mkstemp in the same directory. flush + fsync + os.replace
    for durability. On failure, unlinks temp file and re-raises.
    """
    target = Path(install_root) / "constitution.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="constitution-",
        suffix=".md.tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def cmd_render(args: argparse.Namespace) -> int:
    """Walk schema, concatenate constitution.md, atomic write.

    Reads <devforge_dir>/constitute.json. Concatenates and writes
    <install_root>/constitution.md atomically.

    Exit 0 = success.
    Exit 1 = state file missing / unreadable (JSON parse error).
    Exit 2 = required field missing (project_name, generated_date,
             last_updated, mode, project_identity with all 4 subfields).
    """
    try:
        state = _load(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write(
            "constitute_helper render: cannot load constitute.json: {0}\n".format(err)
        )
        return 1

    try:
        text = _render_constitution(state)
    except ValueError as err:
        sys.stderr.write("constitute_helper {0}\n".format(err))
        return 2

    try:
        _write_constitution_atomic(text, args.install_root)
    except OSError as err:
        sys.stderr.write(
            "constitute_helper render: cannot write constitution.md: {0}\n".format(err)
        )
        return 1

    return 0


# ---------------------------------------------------------------------------
# Step 3: verify helpers.
# ---------------------------------------------------------------------------


def _parse_rendered_constitution(text: str) -> dict:
    """Minimal parser for round-trip identity check in verify.

    Extracts project_name and the number of top-level ## sections
    (H2 headings). Returns {"project_name": str | None, "section_count": int}.

    This is intentionally minimal — full re-parse fidelity is out of scope
    for Step 3. The Step 4 validate subcommand will do deeper structural checks.
    """
    project_name = None
    section_count = 0

    name_match = re.search(r"^# Project Constitution — (.+)$", text, re.MULTILINE)
    if name_match:
        project_name = name_match.group(1).strip()

    # Count H2 headings (## lines).
    section_count = len(re.findall(r"^## ", text, re.MULTILINE))

    return {"project_name": project_name, "section_count": section_count}


def _expected_section_count(state: dict) -> int:
    """Return the expected number of H2 sections for round-trip identity.

    Sections 1-6 are always present. Section 7 (Scaffolding Guide) is
    present when mode==greenfield AND scaffolding_guide is non-null.
    """
    count = 6
    if state.get("mode") == "greenfield" and state.get("scaffolding_guide") is not None:
        count = 7
    return count


def cmd_verify(args: argparse.Namespace) -> int:
    """Cross-check constitute.json for correctness and round-trip identity.

    Checks:
    1. Required scalars non-null: project_name, generated_date, last_updated,
       mode, project_identity (all 4 subfields).
    2. Each section in section_arrays: number + title populated; tag in enum or
       None; each rule has tag in enum + non-empty text; each code_example has
       label in enum + non-empty code; each table: len(row)==len(columns) for
       every row.
    3. patterns_and_antipatterns: each of 6 buckets is a list; each rule has
       tag in enum + non-empty text.
    4. ScaffoldingGuide: when mode==greenfield, scaffolding_guide must be
       non-null; when non-null, starter_directories is a list of strings;
       sample_files is a list of {path, language, content} dicts.
    5. Round-trip identity: render to string; re-parse project_name + section
       count; compare to state.

    Exit 0 = all checks pass.
    Exit 2 = at least one violation (stderr enumerates each).
    """
    try:
        state = _load(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write(
            "constitute_helper verify: cannot load constitute.json: {0}\n".format(err)
        )
        return 2

    violations = []  # type: List[str]

    # --- Check 1: Required scalars ---
    for field in _RENDER_REQUIRED_SCALARS:
        if state.get(field) is None:
            violations.append("required field {0!r} is null".format(field))

    identity = state.get("project_identity")
    if identity is None:
        violations.append("required field 'project_identity' is null")
    else:
        for sub in _IDENTITY_REQUIRED_SUBFIELDS:
            if identity.get(sub) is None:
                violations.append(
                    "project_identity.{0} is null".format(sub)
                )

    # --- Check 2: Section arrays ---
    section_bucket_keys = [
        "architecture_rules",
        "code_quality_standards",
        "domain_rules",
        "workflow_rules",
    ]
    for bucket_key in section_bucket_keys:
        sections = state.get(bucket_key, [])
        if not isinstance(sections, list):
            violations.append("{0} must be a list".format(bucket_key))
            continue
        for i, section in enumerate(sections):
            prefix = "{0}[{1}]".format(bucket_key, i)
            if not section.get("number"):
                violations.append("{0}: number is missing or empty".format(prefix))
            if not section.get("title"):
                violations.append("{0}: title is missing or empty".format(prefix))
            tag = section.get("tag")
            if tag is not None and tag not in ENUM_FIELDS["section_tag"]:
                violations.append(
                    "{0}: tag {1!r} not in allowed set {2}".format(
                        prefix, tag, sorted(ENUM_FIELDS["section_tag"])
                    )
                )
            for j, rule in enumerate(section.get("rules", [])):
                rule_prefix = "{0}.rules[{1}]".format(prefix, j)
                rtag = rule.get("tag")
                if rtag not in ENUM_FIELDS["rule_tag"]:
                    violations.append(
                        "{0}: tag {1!r} not in allowed set {2}".format(
                            rule_prefix, rtag, sorted(ENUM_FIELDS["rule_tag"])
                        )
                    )
                if not rule.get("text", "").strip():
                    violations.append("{0}: text is empty".format(rule_prefix))
            for j, ex in enumerate(section.get("code_examples", [])):
                ex_prefix = "{0}.code_examples[{1}]".format(prefix, j)
                elabel = ex.get("label")
                if elabel not in ENUM_FIELDS["code_label"]:
                    violations.append(
                        "{0}: label {1!r} not in allowed set {2}".format(
                            ex_prefix, elabel, sorted(ENUM_FIELDS["code_label"])
                        )
                    )
                if not ex.get("code", "").strip():
                    violations.append("{0}: code is empty".format(ex_prefix))
            for j, table in enumerate(section.get("tables", [])):
                tbl_prefix = "{0}.tables[{1}]".format(prefix, j)
                cols = table.get("columns", [])
                for k, row in enumerate(table.get("rows", [])):
                    if len(row) != len(cols):
                        violations.append(
                            "{0}.rows[{1}]: has {2} cells but table has {3} columns".format(
                                tbl_prefix, k, len(row), len(cols)
                            )
                        )

    # --- Check 3: patterns_and_antipatterns ---
    pat = state.get("patterns_and_antipatterns", {})
    if not isinstance(pat, dict):
        violations.append("patterns_and_antipatterns must be a dict")
    else:
        for bucket_key in _PATTERNS_BUCKETS:
            bucket = pat.get(bucket_key)
            if not isinstance(bucket, list):
                violations.append(
                    "patterns_and_antipatterns.{0} must be a list".format(bucket_key)
                )
                continue
            for j, rule in enumerate(bucket):
                rule_prefix = "patterns_and_antipatterns.{0}[{1}]".format(bucket_key, j)
                rtag = rule.get("tag")
                if rtag not in ENUM_FIELDS["rule_tag"]:
                    violations.append(
                        "{0}: tag {1!r} not in allowed set {2}".format(
                            rule_prefix, rtag, sorted(ENUM_FIELDS["rule_tag"])
                        )
                    )
                if not rule.get("text", "").strip():
                    violations.append("{0}: text is empty".format(rule_prefix))

    # --- Check 4: scaffolding_guide ---
    mode = state.get("mode")
    scaffolding = state.get("scaffolding_guide")
    if mode == "greenfield" and scaffolding is None:
        violations.append(
            "scaffolding_guide is null but mode is 'greenfield'; "
            "set-scaffolding-guide is required for greenfield projects"
        )
    if scaffolding is not None:
        starter_dirs = scaffolding.get("starter_directories")
        if not isinstance(starter_dirs, list):
            violations.append("scaffolding_guide.starter_directories must be a list")
        else:
            for i, d in enumerate(starter_dirs):
                if not isinstance(d, str):
                    violations.append(
                        "scaffolding_guide.starter_directories[{0}] must be a string".format(i)
                    )
        sample_files = scaffolding.get("sample_files")
        if not isinstance(sample_files, list):
            violations.append("scaffolding_guide.sample_files must be a list")
        else:
            required_sf_keys = {"path", "language", "content"}
            for i, sf in enumerate(sample_files):
                sf_prefix = "scaffolding_guide.sample_files[{0}]".format(i)
                if not isinstance(sf, dict):
                    violations.append("{0}: must be a dict".format(sf_prefix))
                    continue
                missing_keys = required_sf_keys - set(sf.keys())
                if missing_keys:
                    violations.append(
                        "{0}: missing keys {1}".format(sf_prefix, sorted(missing_keys))
                    )

    # --- Check 5: Round-trip identity (minimal) ---
    # Only attempt round-trip if required fields pass (can't render without them).
    if not violations:
        try:
            rendered_text = _render_constitution(state)
            parsed = _parse_rendered_constitution(rendered_text)
        except ValueError as err:
            violations.append("round-trip render error: {0}".format(err))
        else:
            if parsed.get("project_name") != state.get("project_name"):
                violations.append(
                    "round-trip identity: project_name mismatch: "
                    "rendered={0!r}, state={1!r}".format(
                        parsed.get("project_name"), state.get("project_name")
                    )
                )
            expected_secs = _expected_section_count(state)
            actual_secs = parsed.get("section_count", 0)
            if actual_secs != expected_secs:
                violations.append(
                    "round-trip identity: section count mismatch: "
                    "rendered={0}, expected={1}".format(actual_secs, expected_secs)
                )

    if violations:
        for v in violations:
            sys.stderr.write("verify: {0}\n".format(v))
        return 2

    sys.stderr.write("verify: ok\n")
    return 0


# ---------------------------------------------------------------------------
# Step 3: summary subcommand.
# ---------------------------------------------------------------------------


def _render_constitute_summary(state: dict) -> str:
    """Build the deterministic constitute summary string from state.

    Format:
        ## Constitute Helper Summary

        Project Name:        <value or '(unset)'>
        Generated:           <value or '(unset)'>
        Last Updated:        <value or '(unset)'>
        Mode:                <value or '(unset)'>

        Project Identity:
          Name:              <value or '(unset)'>
          ...

        Architecture Rules:  <N sections>
          ...

        ...

    Stable across re-runs (deterministic). Returns string ending in one newline.
    """
    def _val(v: object) -> str:
        if v is None:
            return "(unset)"
        return str(v)

    def _section_line(section: dict) -> str:
        num = section.get("number", "?")
        title = section.get("title", "(untitled)")
        r = len(section.get("rules", []))
        t = len(section.get("tables", []))
        c = len(section.get("code_examples", []))
        return "  {0} {1}: {2} rules, {3} tables, {4} code examples\n".format(
            num, title, r, t, c
        )

    lines = []
    lines.append("## Constitute Helper Summary\n")
    lines.append("\n")
    lines.append("Project Name:        {0}\n".format(_val(state.get("project_name"))))
    lines.append("Generated:           {0}\n".format(_val(state.get("generated_date"))))
    lines.append("Last Updated:        {0}\n".format(_val(state.get("last_updated"))))
    lines.append("Mode:                {0}\n".format(_val(state.get("mode"))))
    lines.append("\n")

    identity = state.get("project_identity")
    lines.append("Project Identity:\n")
    if identity is None:
        lines.append("  Name:              (unset)\n")
        lines.append("  Type:              (unset)\n")
        lines.append("  Domain:            (unset)\n")
        lines.append("  Stack:             (unset)\n")
    else:
        lines.append("  Name:              {0}\n".format(_val(identity.get("name"))))
        lines.append("  Type:              {0}\n".format(_val(identity.get("type"))))
        lines.append("  Domain:            {0}\n".format(_val(identity.get("domain"))))
        lines.append("  Stack:             {0}\n".format(_val(identity.get("stack"))))
    lines.append("\n")

    arch = state.get("architecture_rules", [])
    lines.append("Architecture Rules:  {0} sections\n".format(len(arch)))
    for section in arch:
        lines.append(_section_line(section))

    cqs = state.get("code_quality_standards", [])
    lines.append("Code Quality Standards:  {0} sections\n".format(len(cqs)))
    for section in cqs:
        lines.append(_section_line(section))

    pat = state.get("patterns_and_antipatterns", _empty_patterns_section())
    lines.append("Patterns & Anti-Patterns:\n")
    lines.append("  Always (Universal):         {0} rules\n".format(
        len(pat.get("always_universal", []))
    ))
    lines.append("  Always (Project-Specific):  {0} rules\n".format(
        len(pat.get("always_project_specific", []))
    ))
    lines.append("  Never (Universal):          {0} rules\n".format(
        len(pat.get("never_universal", []))
    ))
    lines.append("  Never (Project-Specific):   {0} rules\n".format(
        len(pat.get("never_project_specific", []))
    ))
    lines.append("  Prefer (Universal):         {0} rules\n".format(
        len(pat.get("prefer_universal", []))
    ))
    lines.append("  Prefer (Project-Specific):  {0} rules\n".format(
        len(pat.get("prefer_project_specific", []))
    ))
    lines.append("\n")

    domain = state.get("domain_rules", [])
    lines.append("Domain Rules:        {0} sections\n".format(len(domain)))
    for section in domain:
        lines.append(_section_line(section))

    workflow = state.get("workflow_rules", [])
    lines.append("Workflow Rules:      {0} sections\n".format(len(workflow)))
    for section in workflow:
        lines.append(_section_line(section))
    lines.append("\n")

    scaffolding = state.get("scaffolding_guide")
    if scaffolding is None:
        lines.append("Scaffolding Guide:   unset\n")
    else:
        lines.append("Scaffolding Guide:   set\n")
        starter_dirs = scaffolding.get("starter_directories", [])
        sample_files = scaffolding.get("sample_files", [])
        lines.append("  Starter Dirs:      {0}\n".format(len(starter_dirs)))
        lines.append("  Sample Files:      {0}\n".format(len(sample_files)))

    return "".join(lines)


def cmd_summary(args: argparse.Namespace) -> int:
    """Render the constitute helper summary to stdout. Read-only.

    Reads constitute.json (defaults if missing → exit 0 with all-unset
    output). Corrupted JSON → exit 1 + stderr message (matches init/
    configure helper precedent; preserves the script-pipeable signal).
    Output is deterministic across re-runs — suitable for piping + diffing.
    """
    try:
        state = _load(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write(
            "constitute_helper summary: cannot load constitute.json: {0}\n".format(err)
        )
        return 1
    sys.stdout.write(_render_constitute_summary(state))
    return 0


# ---------------------------------------------------------------------------
# Step 4: validate subcommand — 4-dimension content quality framework.
# ---------------------------------------------------------------------------

# Regex to extract path-like tokens that look like source/doc file references.
# Matches tokens with a common code/doc extension. Applied to rule text,
# table cells, and code_example annotations.
#
# Alternation order matters: longer suffixes MUST come first so the regex
# engine matches `.tsx` before `.ts`, `.json` before `.js`, `.jsx` before
# `.js`, `.yaml` before `.yml`. Otherwise `tsconfig.json` extracts as
# `tsconfig.js` and the existence check fails on the wrong path.
_PATH_TOKEN_RE = re.compile(
    r"[\w\-\./]+"
    r"\.(?:tsx|ts|jsx|json|yaml|js|vue|py|md|yml|toml)"
)

# Composite weights (must sum to 1.0).
_VALIDATE_WEIGHTS = {
    "slot_fill":   0.30,
    "citation":    0.25,
    "code_syntax": 0.25,
    "rule_tag":    0.20,
}

# Composite pass threshold.
_COMPOSITE_PASS_THRESHOLD = 0.95

# Per-dimension pass thresholds. rule_tag is mechanical (any invalid tag is
# a helper bug); the other 3 dimensions allow up to 5% slop.
_DIM_PASS_THRESHOLDS = {
    "slot_fill":   0.95,
    "citation":    0.95,
    "code_syntax": 0.95,
    "rule_tag":    1.0,
}


# ---------------------------------------------------------------------------
# Dim 1 — Slot-fill rate.
# ---------------------------------------------------------------------------


def _count_slot_fill(state: dict) -> "tuple":
    """Return (filled_slots, total_slots, list_of_failed_slot_names).

    Required slots:
      - project_identity 4 subfields (4 slots)
      - architecture_rules: ≥1 section (1 slot)
      - code_quality_standards: ≥1 section (1 slot)
      - patterns_and_antipatterns: ≥1 rule across 6 buckets (1 slot)
      - domain_rules: ≥1 section (1 slot)
      - workflow_rules: ≥1 section (1 slot)
      - scaffolding_guide (greenfield only): ≥1 starter_directory OR ≥1 sample_file (1 slot)
    Total: 9 (existing-codebase) or 10 (greenfield)
    """
    filled = 0
    total = 0
    failed = []  # type: List[str]

    # Project identity 4 subfields.
    identity = state.get("project_identity") or {}
    for subfield in _IDENTITY_REQUIRED_SUBFIELDS:
        total += 1
        val = identity.get(subfield)
        if val and str(val).strip():
            filled += 1
        else:
            failed.append("project_identity.{0}".format(subfield))

    # Section arrays: ≥1 section each.
    for bucket_key, label in [
        ("architecture_rules", "Section 2"),
        ("code_quality_standards", "Section 3"),
        ("domain_rules", "Section 5"),
        ("workflow_rules", "Section 6"),
    ]:
        total += 1
        sections = state.get(bucket_key) or []
        if sections:
            filled += 1
        else:
            failed.append("{0} ({1}): no sub-sections".format(label, bucket_key))

    # Patterns-and-antipatterns: ≥1 rule across 6 buckets.
    total += 1
    pat = state.get("patterns_and_antipatterns") or {}
    any_rule = any(
        isinstance(pat.get(b), list) and pat.get(b)
        for b in _PATTERNS_BUCKETS
    )
    if any_rule:
        filled += 1
    else:
        failed.append("Section 4 (patterns_and_antipatterns): no rules in any bucket")

    # Greenfield-only Section 7.
    mode = state.get("mode")
    if mode == "greenfield":
        total += 1
        scaffolding = state.get("scaffolding_guide") or {}
        starter_dirs = scaffolding.get("starter_directories") or []
        sample_files = scaffolding.get("sample_files") or []
        if starter_dirs or sample_files:
            filled += 1
        else:
            failed.append("Section 7 (scaffolding_guide): no starter_directory or sample_file")

    return filled, total, failed


# ---------------------------------------------------------------------------
# Dim 2 — Citation validity.
# ---------------------------------------------------------------------------


def _extract_path_tokens(text: str) -> "List[str]":
    """Return list of path-like tokens extracted from text using _PATH_TOKEN_RE."""
    if not text:
        return []
    return _PATH_TOKEN_RE.findall(text)


def _collect_citation_texts(state: dict) -> "List[str]":
    """Collect all text fields that may contain path references.

    Walks:
    - rule.text in all section buckets + patterns buckets
    - table cell strings (all cells in all rows)
    - code_example.annotation strings

    Returns list of individual text strings (one per field value, not per token).
    """
    texts = []  # type: List[str]

    def _add_rule(rule: dict) -> None:
        t = rule.get("text")
        if t:
            texts.append(t)

    def _add_section(section: dict) -> None:
        for rule in section.get("rules", []):
            _add_rule(rule)
        for table in section.get("tables", []):
            for row in table.get("rows", []):
                for cell in row:
                    if cell:
                        texts.append(str(cell))
        for ex in section.get("code_examples", []):
            ann = ex.get("annotation")
            if ann:
                texts.append(ann)

    for bucket_key in ["architecture_rules", "code_quality_standards", "domain_rules", "workflow_rules"]:
        for section in state.get(bucket_key) or []:
            _add_section(section)

    pat = state.get("patterns_and_antipatterns") or {}
    for bucket in _PATTERNS_BUCKETS:
        for rule in pat.get(bucket) or []:
            _add_rule(rule)

    return texts


def _resolve_effective_root(
    install_root: "Union[str, os.PathLike[str]]",
    init_yaml_path: "Optional[Path]",
) -> "Optional[Path]":
    """Return wrapper-mode effective root, or None for standalone.

    Reads init.yaml; if workspace_mode == "wrapper" AND project_root is set
    (and != "."), return install_root / project_root. Otherwise return None
    (standalone — citation resolution uses install_root directly).

    Wrapper-mode quirk: docs/architecture.md citations are paths inside the
    inner project (e.g., "BLoC.ts"), but `_count_citations` resolves against
    install_root (the wrapper). Without the project_root prefix every
    inner-project citation fails the existence check. This fn surfaces the
    wrapper effective root so the caller can try BOTH install_root AND
    effective_root before counting an unresolved.
    """
    if init_yaml_path is None or not Path(init_yaml_path).exists():
        return None
    try:
        text = Path(init_yaml_path).read_text(encoding="utf-8")
        state = init_helper.parse_yaml(text)
    except Exception:
        return None
    if state.get("workspace_mode") != "wrapper":
        return None
    project_root = state.get("project_root") or ""
    if not project_root or project_root == ".":
        return None
    return Path(install_root) / project_root


def _build_package_name_map(init_yaml_path: "Optional[Path]") -> "Dict[str, str]":
    """Build {package_name: path} from init.yaml packages_detected list.

    If init.yaml is missing/unreadable/malformed, returns empty dict
    (citation check degrades gracefully to path-only mode).
    """
    if init_yaml_path is None or not Path(init_yaml_path).exists():
        return {}
    try:
        text = Path(init_yaml_path).read_text(encoding="utf-8")
        state = init_helper.parse_yaml(text)
    except Exception:
        return {}
    result = {}  # type: Dict[str, str]
    for record in state.get("packages_detected") or []:
        p = record.get("path", "")
        # Use the last path segment (the "name") as the key.
        name = Path(p).name if p else ""
        if name and p:
            result[name] = p
    return result


def _count_citations(
    state: dict,
    install_root: "Union[str, os.PathLike[str]]",
    devforge_dir: "Union[str, os.PathLike[str]]",
) -> "tuple":
    """Return (score_float, resolved, unresolved, failed_items).

    score = resolved / (resolved + unresolved); if 0 tokens found → 1.0 (N/A).
    failed_items is a list of strings describing unresolved references.
    """
    install_root_path = Path(install_root)
    init_yaml_path = Path(devforge_dir) / init_helper.OUTPUT_FILE_NAME
    pkg_map = _build_package_name_map(init_yaml_path)
    # Wrapper-mode effective root (None in standalone). When non-None, citation
    # tokens citing inner-project paths (e.g., "BLoC.ts" extracted from
    # docs/architecture.md) resolve relative to this root, not the wrapper.
    effective_root = _resolve_effective_root(install_root, init_yaml_path)

    texts = _collect_citation_texts(state)
    all_tokens = []  # type: List[str]
    for text in texts:
        all_tokens.extend(_extract_path_tokens(text))

    # Filter URL remnants. _PATH_TOKEN_RE strips the `https:` prefix because
    # `:` is not in [\w\-\./], leaving `//example.com/x.json` which would
    # resolve to a bogus absolute POSIX path and always-fail the existence
    # check. Skip any token starting with `//` or containing `:` (any URL
    # scheme that survived the regex).
    all_tokens = [t for t in all_tokens if not t.startswith("//") and ":" not in t]

    if not all_tokens:
        return 1.0, 0, 0, []

    resolved = 0
    unresolved = 0
    failed_items = []  # type: List[str]

    def _try_resolve(token):
        # Try install_root first (works for standalone + for files at wrapper
        # root like docs/architecture.md). Fall through to effective_root
        # (wrapper-mode inner-project paths).
        if (install_root_path / token).exists():
            return True
        if effective_root is not None and (effective_root / token).exists():
            return True
        # Package-name lookup against pkg_map. Try both roots for the package
        # path (pkg_map values are relative to install_root in standalone but
        # relative to the wrapper-root context in wrapper mode).
        token_name = Path(token).name
        if token_name in pkg_map:
            if (install_root_path / pkg_map[token_name]).exists():
                return True
            if effective_root is not None and (effective_root / pkg_map[token_name]).exists():
                return True
        # Recursive find within effective_root (wrapper) — the citation
        # `BLoC.ts` may be at packages/pkg-cse-common/src/classes/BLoC.ts,
        # `routes/index.ts` at apps/app-web/src/router/routes/index.ts, etc.
        # Neither install_root nor effective_root resolves bare basenames or
        # partial sub-paths without the full dirname. Walk the tree and accept
        # any match. rglob handles both single-segment and multi-segment
        # patterns ("routes/index.ts" matches via `**/routes/index.ts`).
        if effective_root is not None:
            try:
                for found in effective_root.rglob(token):
                    if found.exists():
                        return True
            except (OSError, ValueError):
                pass
            # Wildcard suffix fallback for bare basenames. `Repository.ts` may
            # be a pattern reference that matches concrete files like
            # `CoreCatalogRepository.ts`. Only try this for single-segment
            # tokens (no `/`) to avoid over-resolving multi-segment paths
            # (e.g., `tasks/README.md` should not match `*tasks/README.md`).
            if "/" not in token:
                try:
                    for found in effective_root.rglob("*" + token):
                        if found.exists():
                            return True
                except (OSError, ValueError):
                    pass
        return False

    seen = set()  # type: set
    for token in all_tokens:
        if token in seen:
            continue
        seen.add(token)
        if _try_resolve(token):
            resolved += 1
            continue
        unresolved += 1
        failed_items.append("citation unresolved: {0!r}".format(token))

    total = resolved + unresolved
    score = resolved / total if total > 0 else 1.0
    return score, resolved, unresolved, failed_items


# ---------------------------------------------------------------------------
# Dim 3 — Code-example syntax.
# ---------------------------------------------------------------------------


def _check_python_syntax(code: str) -> bool:
    """Return True if code parses as valid Python via ast.parse."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _check_json_syntax(code: str) -> bool:
    """Return True if code parses as valid JSON via json.loads."""
    try:
        json.loads(code)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def _check_balanced_braces(code: str) -> bool:
    """Return True if brace count is balanced (abs(open - close) <= 1) and code is non-empty.

    Used for TS/JS/TSX/JSX — tolerates single-brace imbalance from string literals.
    """
    stripped = code.strip()
    if not stripped:
        return False
    count_open = stripped.count("{")
    count_close = stripped.count("}")
    return abs(count_open - count_close) <= 1


def _check_code_example_syntax(lang: str, code: str) -> bool:
    """Check syntax for a single code example given its language tag.

    python/python3/py → ast.parse
    json → json.loads
    ts/tsx/typescript/js/jsx/javascript → balanced-brace + non-empty heuristic
    other → non-empty heuristic only
    """
    lang_lower = (lang or "").strip().lower()
    if lang_lower in ("python", "python3", "py"):
        return _check_python_syntax(code)
    if lang_lower == "json":
        return _check_json_syntax(code)
    if lang_lower in ("ts", "tsx", "typescript", "js", "jsx", "javascript"):
        return _check_balanced_braces(code)
    # Other languages: non-empty is sufficient.
    return bool(code.strip())


def _collect_code_examples(state: dict) -> "List[dict]":
    """Collect all code_example records from all section buckets."""
    examples = []  # type: List[dict]
    for bucket_key in ["architecture_rules", "code_quality_standards", "domain_rules", "workflow_rules"]:
        for section in state.get(bucket_key) or []:
            examples.extend(section.get("code_examples") or [])
    return examples


def _count_code_syntax(state: dict) -> "tuple":
    """Return (score_float, parsed_clean, total, failed_items).

    score = parsed_clean / total; total == 0 → 1.0 (N/A).
    failed_items lists examples that failed syntax check.
    """
    examples = _collect_code_examples(state)
    if not examples:
        return 1.0, 0, 0, []

    parsed_clean = 0
    failed_items = []  # type: List[str]
    for i, ex in enumerate(examples):
        lang = ex.get("language") or ""
        code = ex.get("code") or ""
        label = ex.get("label") or "?"
        if _check_code_example_syntax(lang, code):
            parsed_clean += 1
        else:
            failed_items.append(
                "code_example[{0}] label={1!r} lang={2!r}: syntax check failed".format(
                    i, label, lang
                )
            )

    total = len(examples)
    score = parsed_clean / total if total > 0 else 1.0
    return score, parsed_clean, total, failed_items


# ---------------------------------------------------------------------------
# Dim 4 — Rule-tag validity.
# ---------------------------------------------------------------------------


def _collect_all_rule_tags(state: dict) -> "List[tuple]":
    """Collect all (tag, context_label) from all rule records in all buckets.

    Used to validate every rule tag against the closed enum.
    """
    entries = []  # type: List[tuple]

    for bucket_key in ["architecture_rules", "code_quality_standards", "domain_rules", "workflow_rules"]:
        for i, section in enumerate(state.get(bucket_key) or []):
            for j, rule in enumerate(section.get("rules") or []):
                label = "{0}[{1}].rules[{2}]".format(bucket_key, i, j)
                entries.append((rule.get("tag"), label))

    pat = state.get("patterns_and_antipatterns") or {}
    for bucket in _PATTERNS_BUCKETS:
        for j, rule in enumerate(pat.get(bucket) or []):
            label = "patterns_and_antipatterns.{0}[{1}]".format(bucket, j)
            entries.append((rule.get("tag"), label))

    return entries


def _count_rule_tags(state: dict) -> "tuple":
    """Return (score_float, valid_count, total_count, failed_items).

    score = valid_tags / total_tags. Zero tags → 1.0 (N/A).
    Pass threshold = 1.0 (mechanical check; failure indicates helper bug).
    """
    entries = _collect_all_rule_tags(state)
    if not entries:
        return 1.0, 0, 0, []

    valid_enum = ENUM_FIELDS["rule_tag"]
    valid_count = 0
    failed_items = []  # type: List[str]
    for tag, label in entries:
        if tag in valid_enum:
            valid_count += 1
        else:
            failed_items.append(
                "{0}: invalid rule tag {1!r} (allowed: {2})".format(
                    label, tag, sorted(valid_enum)
                )
            )

    total = len(entries)
    score = valid_count / total if total > 0 else 1.0
    return score, valid_count, total, failed_items


# ---------------------------------------------------------------------------
# Composite + cmd_validate.
# ---------------------------------------------------------------------------


def _compute_composite(scores: "Dict[str, float]") -> float:
    """Compute weighted composite score from per-dimension float scores."""
    return sum(_VALIDATE_WEIGHTS[d] * scores[d] for d in _VALIDATE_WEIGHTS)


def cmd_validate(args: argparse.Namespace) -> int:
    """4-dimension content quality check for constitute.json.

    Dimensions:
      1. slot_fill   — required sections/fields populated (weight 0.30)
      2. citation    — path citations resolve under install_root (weight 0.25)
      3. code_syntax — code examples parse as declared language (weight 0.25)
      4. rule_tag    — every rule tag in closed enum (weight 0.20)

    Composite >= 0.95 → exit 0 (pass).
    Composite < 0.95  → exit 2 (fail; stderr enumerates per-dimension + failed items).
    Exit 1 on state file unreadable / corrupted JSON.

    stdout always receives a JSON object:
      {"composite": float, "dimensions": {dim: {"score": float, "pass": bool}}, "failed_items": [...]}
    """
    try:
        state = _load(args.devforge_dir)
    except (OSError, json.JSONDecodeError) as err:
        sys.stderr.write(
            "constitute_helper validate: cannot load constitute.json: {0}\n".format(err)
        )
        return 1

    # Dim 1 — slot fill.
    filled, total_slots, slot_failed = _count_slot_fill(state)
    slot_score = filled / total_slots if total_slots > 0 else 1.0

    # Dim 2 — citation validity.
    citation_score, _resolved, _unresolved, citation_failed = _count_citations(
        state, args.install_root, args.devforge_dir
    )

    # Dim 3 — code-example syntax.
    syntax_score, _parsed, _total_ex, syntax_failed = _count_code_syntax(state)

    # Dim 4 — rule-tag validity.
    tag_score, _valid_tags, _total_tags, tag_failed = _count_rule_tags(state)

    scores = {
        "slot_fill":   slot_score,
        "citation":    citation_score,
        "code_syntax": syntax_score,
        "rule_tag":    tag_score,
    }
    composite = _compute_composite(scores)
    pass_threshold = _COMPOSITE_PASS_THRESHOLD

    all_failed = slot_failed + citation_failed + syntax_failed + tag_failed

    dimensions = {}
    for dim in ("slot_fill", "citation", "code_syntax", "rule_tag"):
        dimensions[dim] = {
            "score": round(scores[dim], 6),
            "pass": scores[dim] >= _DIM_PASS_THRESHOLDS[dim],
        }

    result_obj = {
        "composite": round(composite, 6),
        "dimensions": dimensions,
        "failed_items": all_failed,
    }
    sys.stdout.write(json.dumps(result_obj, indent=2))
    sys.stdout.write("\n")

    if composite < pass_threshold:
        sys.stderr.write(
            "constitute_helper validate: composite={0:.4f} < {1:.2f} — FAIL\n".format(
                composite, pass_threshold
            )
        )
        for dim in ("slot_fill", "citation", "code_syntax", "rule_tag"):
            sys.stderr.write(
                "  {0}: score={1:.4f} weight={2}\n".format(
                    dim, scores[dim], _VALIDATE_WEIGHTS[dim]
                )
            )
        for item in all_failed:
            sys.stderr.write("  FAIL: {0}\n".format(item))
        return 2

    sys.stderr.write(
        "constitute_helper validate: composite={0:.4f} >= {1:.2f} — PASS\n".format(
            composite, pass_threshold
        )
    )
    return 0


# ---------------------------------------------------------------------------
# forge-internal:verify-universal-defaults — drift detector.
# ---------------------------------------------------------------------------


def _normalize_body(text: str) -> str:
    """Normalize a rule body for drift comparison: collapse whitespace.

    Strips leading/trailing whitespace AND collapses runs of internal
    whitespace (spaces, tabs, newlines) to single spaces, so cosmetic
    formatting differences don't surface as DRIFT findings. Body content
    must match semantically; cosmetic differences are silent.
    """
    return " ".join((text or "").split())


def cmd_verify_universal_defaults(args: argparse.Namespace) -> int:
    """Diff consumer's universal-rule bodies vs framework canonical.

    Reads both surfaces via the Phase 1.C parsers, compares per-section
    + per-rule, emits findings per line on stderr. Exit 0 if zero findings;
    exit 2 otherwise. Stdout = JSON report for downstream tooling.

    Args:
        args.consumer_path — consumer project root containing
            .devforge/constitute.json.
        args.canonical_path — path to canonical constitution.md (default:
            src/constitution.md relative to forge repo cwd).
    """
    consumer_path = Path(args.consumer_path).resolve()
    canonical_path = Path(args.canonical_path).resolve()

    consumer_json = consumer_path / ".devforge" / "constitute.json"

    if not canonical_path.is_file():
        sys.stderr.write(
            "verify-universal-defaults: canonical path not found: {0}\n".format(
                canonical_path
            )
        )
        return 2
    if not consumer_json.is_file():
        sys.stderr.write(
            "verify-universal-defaults: consumer constitute.json not found:"
            " {0}\n".format(consumer_json)
        )
        return 2

    canonical_blocks = _parse_universal_blocks(canonical_path)
    consumer_blocks = _extract_universal_rules_from_state(consumer_json)

    findings = []  # type: List[Dict[str, str]]

    for section_key, canonical_data in canonical_blocks.items():
        if section_key not in consumer_blocks:
            findings.append(
                {
                    "kind": "MISSING",
                    "section": section_key,
                    "detail": "consumer state has no entry for {0}".format(
                        section_key
                    ),
                }
            )
            continue
        consumer_data = consumer_blocks[section_key]
        canonical_rules = {
            r["tag_or_label"]: r["body"] for r in canonical_data["rules"]
        }
        consumer_rules = {
            r["tag_or_label"]: r["body"] for r in consumer_data["rules"]
        }
        for label, canonical_body in canonical_rules.items():
            if label not in consumer_rules:
                findings.append(
                    {
                        "kind": "MISSING",
                        "section": section_key,
                        "rule": label,
                        "detail": "consumer missing rule '{0}' in {1}".format(
                            label, section_key
                        ),
                    }
                )
                continue
            consumer_body = consumer_rules[label]
            if _normalize_body(canonical_body) != _normalize_body(consumer_body):
                findings.append(
                    {
                        "kind": "DRIFT",
                        "section": section_key,
                        "rule": label,
                        "detail": "body text differs",
                    }
                )

    report = {
        "consumer": str(consumer_path),
        "canonical": str(canonical_path),
        "findings": findings,
    }
    sys.stdout.write(json.dumps(report, indent=2) + "\n")

    if not findings:
        return 0

    for f in findings:
        line = "{kind} {section}".format(**f)
        if "rule" in f:
            line += " [{0}]".format(f["rule"])
        line += " — {detail}".format(**f)
        sys.stderr.write(line + "\n")
    return 2


# ---------------------------------------------------------------------------
# Argparse + main.
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="constitute_helper",
        description="State + render helper for /constitute. Owns constitution.md shape.",
    )
    parser.add_argument(
        "--devforge-dir",
        default=".devforge",
        help="Path to the .devforge directory (default: .devforge in CWD).",
    )
    parser.add_argument(
        "--install-root",
        default=None,
        help=(
            "Path to the install root (project root for standalone, wrapper root "
            "for wrapper mode). Default: parent of --devforge-dir."
        ),
    )

    subparsers = parser.add_subparsers(dest="subcommand")

    sp = subparsers.add_parser(
        "reset",
        help="Write a fresh defaults state file. Idempotent.",
    )
    sp.set_defaults(func=cmd_reset)

    sp = subparsers.add_parser(
        "read-init",
        help="Read .devforge/init.yaml and emit JSON to stdout.",
    )
    sp.set_defaults(func=cmd_read_init)

    sp = subparsers.add_parser(
        "read-configure",
        help="Read .devforge/configure.yaml and emit JSON to stdout.",
    )
    sp.set_defaults(func=cmd_read_configure)

    sp = subparsers.add_parser(
        "read-docs",
        help="Parse docs/overview.md + docs/architecture.md and emit JSON.",
    )
    sp.set_defaults(func=cmd_read_docs)

    sp = subparsers.add_parser(
        "read-glossary",
        help="Parse docs/glossary.md and emit JSON list of term records.",
    )
    sp.set_defaults(func=cmd_read_glossary)

    # -----------------------------------------------------------------------
    # Step 2 setters.
    # -----------------------------------------------------------------------

    sp = subparsers.add_parser(
        "set-project-name",
        help="Set project_name scalar.",
    )
    sp.add_argument("--value", required=True, help="Project name.")
    sp.set_defaults(func=cmd_set_project_name)

    sp = subparsers.add_parser(
        "set-mode",
        help="Set mode enum (existing-codebase | greenfield).",
    )
    sp.add_argument("--value", required=True, help="Mode value.")
    sp.set_defaults(func=cmd_set_mode)

    sp = subparsers.add_parser(
        "set-dates",
        help="Set generated_date and last_updated (both YYYY-MM-DD).",
    )
    sp.add_argument("--generated", required=True, help="Generated date (YYYY-MM-DD).")
    sp.add_argument("--updated", required=True, help="Last updated date (YYYY-MM-DD).")
    sp.set_defaults(func=cmd_set_dates)

    sp = subparsers.add_parser(
        "set-project-identity",
        help="Set project_identity record (name, type, domain, stack). Replaces prior value.",
    )
    sp.add_argument("--name", required=True, help="Project identity name.")
    sp.add_argument("--type", required=True, help="Project identity type.")
    sp.add_argument("--domain", required=True, help="Project identity domain.")
    sp.add_argument("--stack", required=True, help="Project identity stack.")
    sp.set_defaults(func=cmd_set_project_identity)

    sp = subparsers.add_parser(
        "add-section",
        help="Add (or update metadata of) a section in a bucket. Idempotent on (bucket, number).",
    )
    sp.add_argument(
        "--bucket",
        required=True,
        choices=list(_SECTION_BUCKET_TO_KEY.keys()),
        help="Section bucket (architecture | code-quality | domain | workflow).",
    )
    sp.add_argument("--number", required=True, help="Section number (e.g. '2', '2.1').")
    sp.add_argument("--title", required=True, help="Section title.")
    sp.add_argument(
        "--tag",
        default=None,
        help="Section tag (universal | project-specific | greenfield-only). Optional.",
    )
    sp.add_argument("--description", default=None, help="Section description. Optional.")
    sp.set_defaults(func=cmd_add_section)

    sp = subparsers.add_parser(
        "add-rule",
        help="Append a rule to the section identified by --section number.",
    )
    sp.add_argument("--section", required=True, help="Section number to append rule to.")
    sp.add_argument(
        "--tag",
        required=True,
        help="Rule tag (extracted | enforced | universal | project-specific).",
    )
    sp.add_argument("--text", required=True, help="Rule text.")
    sp.set_defaults(func=cmd_add_rule)

    sp = subparsers.add_parser(
        "add-table",
        help="Append a table to the section identified by --section number.",
    )
    sp.add_argument("--section", required=True, help="Section number to append table to.")
    sp.add_argument(
        "--columns",
        required=True,
        help="Column names as comma-separated string or JSON array.",
    )
    sp.add_argument(
        "--rows-json",
        required=True,
        dest="rows_json",
        help="Rows as JSON array of arrays of strings.",
    )
    sp.set_defaults(func=cmd_add_table)

    sp = subparsers.add_parser(
        "add-code-example",
        help="Append a code example to the section identified by --section number.",
    )
    sp.add_argument("--section", required=True, help="Section number to append code example to.")
    sp.add_argument(
        "--label",
        required=True,
        help="Code example label (CORRECT | WRONG | EXAMPLE).",
    )
    sp.add_argument("--language", required=True, help="Programming language.")
    sp.add_argument("--code", required=True, help="Code content (multi-line OK).")
    sp.add_argument("--annotation", default=None, help="Optional annotation text.")
    sp.set_defaults(func=cmd_add_code_example)

    sp = subparsers.add_parser(
        "add-pattern-rule",
        help="Append a rule to a patterns_and_antipatterns bucket.",
    )
    sp.add_argument(
        "--bucket",
        required=True,
        choices=["always", "never", "prefer"],
        help="Pattern bucket (always | never | prefer).",
    )
    sp.add_argument(
        "--scope",
        required=True,
        choices=list(_PATTERN_SCOPE_TO_SUFFIX.keys()),
        help="Scope (universal | project-specific).",
    )
    sp.add_argument(
        "--tag",
        required=True,
        help="Rule tag (extracted | enforced | universal | project-specific).",
    )
    sp.add_argument("--text", required=True, help="Pattern rule text.")
    sp.set_defaults(func=cmd_add_pattern_rule)

    sp = subparsers.add_parser(
        "set-scaffolding-guide",
        help="Set scaffolding_guide record (starter_directories + sample_files). Replaces prior value.",
    )
    sp.add_argument(
        "--starter-dirs",
        required=True,
        dest="starter_dirs",
        help="Starter directories as comma-separated string or JSON array.",
    )
    sp.add_argument(
        "--sample-files-json",
        required=True,
        dest="sample_files_json",
        help='Sample files as JSON array of {path, language, content} objects.',
    )
    sp.set_defaults(func=cmd_set_scaffolding_guide)

    # -----------------------------------------------------------------------
    # Step 3: render / verify / summary.
    # -----------------------------------------------------------------------

    sp = subparsers.add_parser(
        "render",
        help=(
            "Walk schema, concatenate constitution.md, atomic write to "
            "<install_root>/constitution.md."
        ),
    )
    sp.set_defaults(func=cmd_render)

    sp = subparsers.add_parser(
        "verify",
        help=(
            "Cross-check constitute.json for correctness + round-trip identity. "
            "Exit 0 = pass; exit 2 = violations (stderr enumerates)."
        ),
    )
    sp.set_defaults(func=cmd_verify)

    sp = subparsers.add_parser(
        "summary",
        help=(
            "Render constitute summary to stdout. Read-only. "
            "Exit 0 = success (incl. missing state → all-unset). "
            "Exit 1 = state file present but corrupted JSON."
        ),
    )
    sp.set_defaults(func=cmd_summary)

    sp = subparsers.add_parser(
        "validate",
        help=(
            "4-dimension content quality check: slot-fill, citation validity, "
            "code-example syntax, rule-tag enum. "
            "Exit 0 = composite >= 0.95. Exit 2 = below threshold. "
            "Exit 1 = state file unreadable."
        ),
    )
    sp.set_defaults(func=cmd_validate)

    # -----------------------------------------------------------------------
    # forge-internal subcommands.
    # -----------------------------------------------------------------------

    sp = subparsers.add_parser(
        "forge-internal:verify-universal-defaults",
        help=(
            "Diff consumer .devforge/constitute.json universal sections vs "
            "canonical src/constitution.md. Maintainer-only."
        ),
    )
    sp.add_argument(
        "--consumer-path",
        required=True,
        dest="consumer_path",
        help="Consumer project root containing .devforge/constitute.json.",
    )
    sp.add_argument(
        "--canonical-path",
        default="src/constitution.md",
        dest="canonical_path",
        help="Canonical constitution.md path (default: src/constitution.md).",
    )
    sp.set_defaults(func=cmd_verify_universal_defaults)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2

    if args.install_root is None:
        args.install_root = str(Path(args.devforge_dir).resolve().parent)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
