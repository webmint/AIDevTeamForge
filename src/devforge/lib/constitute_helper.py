"""constitute_helper — composes the constitution.md state file for /constitute.

Owns the shape of `.devforge/constitute.json` (canonical state) and
`<install_root>/constitution.md` (render artifact). Schema-anchored:
helper owns markdown structure, LLM provides values via setters. Mirrors
the helper-owns-shape pattern established by init_helper / configure_helper /
generate_docs_helper.

`/constitute` is the fourth and last command in the 4-command pivot
(init-forge → generate-docs → configure → constitute).

Step 2 (this commit): 5 validation helpers (_validate_scalar, _validate_enum
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
