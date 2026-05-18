"""Validation + error helpers for discover_helper."""

from __future__ import annotations

import sys


def _die(message: str, code: int = 1) -> int:
    """Write error to stderr and return code (caller propagates as exit)."""
    sys.stderr.write("discover_helper: {0}\n".format(message))
    return code


def _validate_scalar(value: str, field_name: str) -> str:
    """Strip + reject empty. Returns stripped string."""
    stripped = value.strip()
    if not stripped:
        raise ValueError("{0}: value cannot be empty".format(field_name))
    return stripped
