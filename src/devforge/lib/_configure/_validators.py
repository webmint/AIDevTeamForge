"""Validation helpers + _die exit-code wrapper."""

from __future__ import annotations

import sys
from typing import List

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
