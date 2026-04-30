"""Persists the generate_docs helper's JSON state file with atomic writes.

State path is `<DEVFORGE_DIR>/.generate-docs-state.json`, resolved at
call time so tests can override via `DEVFORGE_DIR`. The file IS the
source of truth: each setter does a read-modify-write cycle. Atomicity
is guaranteed via `tempfile.mkstemp` + `os.replace` in the target
directory; on any write failure the temp file is unlinked and the
exception re-raised (anti-pattern #4 — fixed-name temp files are NOT
used).

This module also exposes the small `_die` / `_info` stderr printers
used by every other submodule to report state-related success and
failure to the CLI. They live here because they are inseparable from
the state-error flow (a failed `_load_state` immediately routes through
`_die`); centralizing them avoids duplicating a 2-line printer in five
modules. No other module-level concerns belong here — argparse wiring,
field validation, manifest detection, and rendering all live elsewhere.

Stdlib only. Targets Python 3.8+.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


STATE_FILE_NAME = ".generate-docs-state.json"
STATE_VERSION = 1


def _state_file_path() -> Path:
    """Resolve the state file path at call time (not import time).

    Honors `DEVFORGE_DIR` when set; otherwise falls back to the helper's
    own location's parent (`<install>/.devforge/`) following the same
    convention as `init_helper`.
    """
    env_dir = os.environ.get("DEVFORGE_DIR")
    if env_dir:
        return Path(env_dir) / STATE_FILE_NAME
    # `Path(__file__).resolve().parent` -> `_generate_docs/`
    # `.parent` -> `lib/`
    # `.parent` -> `devforge/`
    # The state lives at `<devforge>/.generate-docs-state.json` (one
    # level above `lib/`), matching the prior monolith's layout.
    return Path(__file__).resolve().parent.parent.parent / STATE_FILE_NAME


def default_state() -> Dict[str, Any]:
    """Return a fresh defaults dict for a brand-new state file."""
    return {"version": STATE_VERSION, "packages": {}}


def default_package_record(name: str, path: str) -> Dict[str, Any]:
    """Return the per-package skeleton dict — every field initialized."""
    return {
        "name": name,
        "path": path,
        "overview": None,
        "directory_tree": None,
        "primary_language": None,
        "framework": None,
        "build_tool": None,
        "scripts": {},
        "exports": [],
        "dependencies": [],
        "hazards": [],
        "usage_example": None,
        "consumer_pattern": None,
    }


class StateLoadError(Exception):
    """Raised when the on-disk state file is unreadable or malformed."""


def _load_state() -> Dict[str, Any]:
    """Read JSON state from disk if present; otherwise return defaults.

    A missing file is normal (first invocation). A present-but-corrupt
    file is surfaced as `StateLoadError` so the CLI can exit non-zero
    with a clear message rather than silently resetting.

    Wrong-type top-level keys (`packages` not a dict, etc.) are also
    surfaced — silently coercing them would hide data loss. Missing
    keys, by contrast, are backfilled from defaults (legitimate
    forward-compat for older state shapes).
    """
    path = _state_file_path()
    if not path.exists():
        return default_state()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        raise StateLoadError(
            "cannot read state file {0}: {1}".format(path, err)
        )
    try:
        data = json.loads(text)
    except json.JSONDecodeError as err:
        raise StateLoadError(
            "state file {0} is corrupt: {1}".format(path, err)
        )
    if not isinstance(data, dict):
        raise StateLoadError(
            "state file {0} root must be an object".format(path)
        )
    # Defensive backfill — preserve forward compat with older state
    # shapes if/when version migrations happen.
    if "version" not in data:
        data["version"] = STATE_VERSION
    if "packages" not in data:
        data["packages"] = {}
    elif not isinstance(data["packages"], dict):
        # Wrong-type — surfaced rather than silently reset, so a
        # corrupt file does NOT cause silent data loss. (Reviewer
        # finding #1.)
        raise StateLoadError(
            "state file {0}: 'packages' must be an object, got {1}".format(
                path, type(data["packages"]).__name__
            )
        )
    return data


def _write_state(state: Dict[str, Any]) -> None:
    """Atomically write `state` to the state file path.

    Uses `tempfile.mkstemp` in the target directory + `os.replace` to
    guarantee atomicity. Cleans up the temp file on any failure.
    """
    target = _state_file_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".generate-docs-state-",
        suffix=".json",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _die(message: str, code: int = 2) -> int:
    """Print `message` to stderr and return `code` for the CLI dispatcher."""
    sys.stderr.write("generate_docs_helper: {0}\n".format(message))
    return code


def _info(message: str) -> None:
    """Print a success message to stderr (stdout is reserved for data)."""
    sys.stderr.write("generate_docs_helper: {0}\n".format(message))


def _require_package(state: Dict[str, Any], path: str) -> Optional[Dict[str, Any]]:
    """Return the package record for `path` or None if absent.

    The caller is responsible for surfacing the "package not registered"
    error — this helper just looks it up so the call site stays linear.
    """
    return state["packages"].get(path)
