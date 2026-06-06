"""Validation helpers + _die exit-code wrapper + command-executability probe."""

from __future__ import annotations

import shlex
import shutil
import sys
from typing import Dict, List, Optional

from ._schema import ENUM_FIELDS


def _validate_scalar(value: str, field_name: str) -> str:
    """Strip and validate a scalar string value.

    Returns the stripped string. Raises ValueError if empty after strip.
    """
    stripped = value.strip()
    if not stripped:
        raise ValueError("{0}: value cannot be empty".format(field_name))
    return stripped


def _validate_enum(value: str, field_name: str) -> str:
    """Validate an enum scalar: must pass _validate_scalar AND be in allowed set.

    Case-insensitive match; returns the canonical (exact-case) member from
    ENUM_FIELDS. Accepts e.g. 'strict' / 'STRICT' / 'Strict' for the
    workflow_enforcement enum and stores 'Strict'. Saves the LLM (and CLI
    users) from having to know the exact case. Raises ValueError if empty
    or no case-insensitive match.
    """
    stripped = _validate_scalar(value, field_name)
    allowed = ENUM_FIELDS[field_name]
    # Exact match first (fast path; preserves canonical case).
    if stripped in allowed:
        return stripped
    # Case-insensitive fallback: normalize to the canonical member.
    lower_to_canonical = {member.lower(): member for member in allowed}
    if stripped.lower() in lower_to_canonical:
        return lower_to_canonical[stripped.lower()]
    raise ValueError(
        "{0}: invalid value {1!r}; allowed: {2}".format(
            field_name, stripped, sorted(allowed)
        )
    )


def _validate_string_array(value: str, field_name: str) -> List[str]:
    """Parse a string-array value and validate each item.

    Accepts two input forms:

    1. Comma-separated string (default): `"vue, vue-router, pinia"` →
       `["vue", "vue-router", "pinia"]`.
    2. JSON-array string (when input starts with `[` and ends with `]`
       after strip): `'["Either<DataError, T>", "BLoC notifications"]'`
       → `["Either<DataError, T>", "BLoC notifications"]`. JSON form
       allows individual items to contain literal commas (TypeScript
       generic syntax, parenthetical clauses, etc.) without breaking
       the comma split.

    Returns a list of stripped, non-empty strings. Raises ValueError if
    any item is empty after strip, the result list is empty, or the JSON
    form is malformed.
    """
    stripped_value = value.strip()
    items_raw: List[str]
    if stripped_value.startswith("[") and stripped_value.endswith("]"):
        # JSON-array form. Decode + validate.
        import json as _json
        try:
            decoded = _json.loads(stripped_value)
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
        items_raw = []
        for item in decoded:
            if not isinstance(item, str):
                raise ValueError(
                    "{0}: JSON-array items must be strings, got {1}".format(
                        field_name, type(item).__name__
                    )
                )
            items_raw.append(item)
    else:
        # Comma-separated form (legacy default).
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

    Internal whitespace is preserved — these are verbatim docs sections.
    Returns the original value (NOT stripped) so callers store exactly
    what was passed. Raises ValueError if the value is all whitespace.
    """
    if not value.strip():
        raise ValueError("{0}: value cannot be empty".format(field_name))
    return value


def _die(message: str, code: int = 1) -> int:
    # code=1 default for I/O errors (OSError, malformed yaml, missing
    # input file). Validation errors pass code=2 explicitly so callers
    # can distinguish "your input was invalid" from "the system is
    # broken". Mirrors init_helper._die — NOT _generate_docs/_state.py
    # which defaults code=2; the divergence is intentional because
    # /configure surfaces validation errors more often than I/O errors,
    # and the user-facing distinction matters at exit-code level.
    sys.stderr.write("configure_helper: {0}\n".format(message))
    return code


# ---------------------------------------------------------------------------
# Command-executability probe (best-effort PATH resolution).
# ---------------------------------------------------------------------------

# Sentinel: commands stored as exactly this string (after strip) are
# legitimately absent — no tool is expected on PATH.
_NA_SENTINEL = "N/A"

# Segment separators that split a compound shell command into sequential
# segments, each with its own leading executable.
_CHAIN_SEPARATORS = ("&&", ";")


def _split_into_segments(command: str) -> List[List[str]]:
    """Split a shell command into segments on '&&' and ';' separators.

    Strategy: tokenize the whole command once with shlex (quote-aware),
    then walk the token list splitting on separators. A '&&' or ';' that
    appears as its own whitespace-delimited token is a separator. A
    separator fused to the end of a token (e.g. 'tsc&&eslint' or 'tsc;')
    is also detected by scanning each token for a trailing bare '&&' or
    ';' after stripping outer quotes — this handles the no-space form
    that shlex leaves as a single token.

    Returns a list of segments, each segment being a list of raw token
    strings (still quoted where the user quoted them). Returns an empty
    outer list if the command has no parseable tokens.
    """
    try:
        tokens = shlex.split(command, posix=False)
    except ValueError:
        tokens = command.split()

    segments: List[List[str]] = []
    current: List[str] = []

    for tok in tokens:
        # A token that is exactly a separator (with or without surrounding
        # whitespace in the raw command, shlex strips that).
        if tok in ("&&", ";"):
            if current:
                segments.append(current)
                current = []
            continue

        # A token that has a fused separator: e.g. "tsc&&" or "tsc&&eslint"
        # or "cmd;". shlex with posix=False won't split these because &&
        # and ; are not shell metacharacters in posix=False mode.
        # We detect: does this unquoted token contain '&&' or ';' ?
        # We only do this when the token is NOT entirely quoted (i.e. bare).
        bare = tok  # shlex posix=False leaves quotes intact
        if not (bare.startswith("'") or bare.startswith('"')):
            # Check for fused '&&' first (longer separator has priority).
            if "&&" in bare:
                parts = bare.split("&&")
                for i, part in enumerate(parts):
                    if part:
                        current.append(part)
                    if i < len(parts) - 1:
                        # separator between parts[i] and parts[i+1]
                        if current:
                            segments.append(current)
                            current = []
                continue
            if ";" in bare:
                parts = bare.split(";")
                for i, part in enumerate(parts):
                    if part:
                        current.append(part)
                    if i < len(parts) - 1:
                        if current:
                            segments.append(current)
                            current = []
                continue

        current.append(tok)

    if current:
        segments.append(current)

    return segments


# Shell-variable assignment prefix: matches tokens like VAR=value, VAR=,
# SOME_VAR123=anything. These are env-var overrides that precede the
# actual executable and must be skipped when probing.
import re as _re
_ENV_ASSIGN_RE = _re.compile(r'^\w+=')


def probe_command_executability(command: str) -> Optional[List[str]]:
    """Return unresolvable executable tokens for `command`, or None to skip.

    Best-effort PATH probe using shutil.which. Does NOT execute the command.

    Best-effort limitations:
    - Package-manager wrappers such as npm, npx, pnpm, and yarn resolve
      via shutil.which when the manager itself is on PATH — but the
      underlying script they invoke (e.g. 'vue-tsc' via 'npx vue-tsc')
      is not probed.
    - Shell env-var assignment prefixes (e.g. 'NODE_ENV=test tsc') are
      skipped; the first non-assignment token is probed as the executable.
      If a segment consists only of assignments, nothing is probed for it.

    Returns:
        None    — command is skipped (empty, blank, or the literal "N/A").
        []      — all executable tokens resolved; command is safe to run.
        [token] — list of unresolvable leading executable tokens (one per
                  chain-segment whose binary is missing); duplicates
                  deduplicated, order preserved by first occurrence.

    Chain handling:
        '&&' and ';' separators split the command into segments (quote-
        aware: a separator inside a quoted argument is NOT treated as a
        chain boundary). Each segment's first non-assignment, non-cd token
        is probed independently.
    """
    stripped = command.strip() if command else ""
    if not stripped or stripped == _NA_SENTINEL:
        return None

    segments = _split_into_segments(stripped)

    missing: List[str] = []
    seen: List[str] = []

    for seg_tokens in segments:
        if not seg_tokens:
            continue

        # Find the first non-assignment token as the executable.
        executable = None
        for tok in seg_tokens:
            # Strip surrounding quotes left by shlex posix=False.
            bare = tok.strip("'\"")
            if _ENV_ASSIGN_RE.match(bare):
                # Shell env-var assignment prefix — skip it.
                continue
            executable = bare
            break

        if executable is None:
            # Segment is entirely assignments — nothing to probe.
            continue

        # Skip 'cd' segments — they change directory, not a tool to probe.
        if executable == "cd":
            continue

        if shutil.which(executable) is None:
            # Deduplicate: skip if already in the missing list.
            if executable not in seen:
                missing.append(executable)
                seen.append(executable)

    return missing


def collect_executability_warnings(state: dict) -> List[Dict[str, str]]:
    """Probe all configured commands in `state` and return warning records.

    Probes the primary command arrays (type_check_commands[0],
    lint_commands[0], build_commands[0]) and every per-package record in
    package_stacks (type_check_command, lint_command, build_command).

    Only the FIRST entry of each primary array is probed — it is the
    command that /implement's verify gate will actually run.

    Returns a list of dicts, each with:
        scope         — human-readable location (e.g. "primary type_check",
                        "package packages/frontend lint")
        command       — the command string that was probed
        missing_token — the first unresolvable executable token found

    Empty list → no warnings (all commands resolvable or skipped).
    """
    warnings: List[Dict[str, str]] = []

    # Primary command arrays: probe the first entry only.
    _PRIMARY = (
        ("type_check_commands", "primary type_check"),
        ("lint_commands",       "primary lint"),
        ("build_commands",      "primary build"),
    )
    for field, scope_label in _PRIMARY:
        arr = state.get(field, [])
        if not arr:
            continue
        cmd = arr[0]
        result = probe_command_executability(cmd)
        if result:  # non-empty list → at least one missing token
            warnings.append({
                "scope": scope_label,
                "command": cmd,
                "missing_token": result[0],
            })

    # Per-package records.
    _PKG_FIELDS = (
        ("type_check_command", "type_check"),
        ("lint_command",       "lint"),
        ("build_command",      "build"),
    )
    for record in state.get("package_stacks", []):
        pkg_path = record.get("path", "")
        for field, kind_label in _PKG_FIELDS:
            cmd = record.get(field)
            if not cmd:
                continue
            result = probe_command_executability(cmd)
            if result:
                warnings.append({
                    "scope": "package {0} {1}".format(pkg_path, kind_label),
                    "command": cmd,
                    "missing_token": result[0],
                })

    return warnings
