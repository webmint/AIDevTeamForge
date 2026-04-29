"""wizard_render — composes Phase 3 + Phase 4 file population for /setup-wizard.

This helper substitutes user-supplied values into template files (CLAUDE.md,
constitution.md, agent files, docs/) and atomically writes the populated
results. It is the bridge between user answers (collected in Phase 2) and
the on-disk state of the configured project.

State model:

- `<.devforge>/.wizard-render-state.json` is the on-disk staging area for
  wizard answers. Keys mirror `src/devforge/project-config.json` (so they
  are UPPERCASE_SNAKE_CASE), but the state file is an intermediate: it
  accumulates answers across Phase 2 questions and is consumed by Phase 3
  composition. The agent never reads this file directly — it only invokes
  setters.
- Each setter performs a read-modify-write: load existing JSON (empty dict
  on missing file), merge the new key, and atomically replace via
  `tempfile.mkstemp` + `os.replace`.
- Pretty-printed with `indent=2, sort_keys=True` so diffs are reviewable
  during wizard development.

Stdlib only. No third-party dependencies. Targets Python 3.8+.

REBUILD IN PROGRESS: subcommands are added incrementally during the spec
migration in .vault/setup-wizard/. The reference implementation (with known
issues) is preserved at .vault/devforge/lib/wizard_render.py.
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

# State file name (leading dot keeps it hidden in `.devforge/` listings).
STATE_FILE_NAME = ".wizard-render-state.json"


def _state_file_path():
    """Resolve the state file path at call time (not import time).

    Honors the `DEVFORGE_DIR` environment variable when set — used by tests
    and by unusual install layouts. When unset, computes the path from this
    script's own location: `<target>/.devforge/lib/wizard_render.py` lives
    one directory below `<target>/.devforge/`, where the state file belongs.

    Returning a fresh Path each call (rather than caching at import) keeps
    tests free of monkey-patching: each test sets `DEVFORGE_DIR` and the
    next resolution sees the override.
    """
    env_dir = os.environ.get("DEVFORGE_DIR")
    if env_dir:
        return Path(env_dir) / STATE_FILE_NAME
    return Path(__file__).resolve().parent.parent / STATE_FILE_NAME


# ---------------------------------------------------------------------------
# Validation.
# ---------------------------------------------------------------------------


def _has_control_chars(value, allow_newlines=False):
    """Return True if `value` contains a forbidden control character.

    Tab (0x09) is always permitted because horizontal tabs occur in
    legitimate prose. LF (0x0A) and CR (0x0D) are permitted ONLY when
    `allow_newlines=True` — the per-field policy is set at the call site,
    not inside the validator, because some fields substitute into
    single-line template contexts (e.g. PROJECT_NAME → `{{PROJECT_NAME}}`)
    where an embedded newline silently corrupts the rendered output.

    All other control chars (NUL through 0x1F minus the whitespace
    exceptions, plus DEL 0x7F) are always rejected so they never reach the
    JSON encoder, downstream consumers, or template substitution.
    """
    allowed_controls = {0x09}
    if allow_newlines:
        allowed_controls = allowed_controls | {0x0A, 0x0D}
    for ch in value:
        code = ord(ch)
        if code < 0x20 and code not in allowed_controls:
            return True
        if code == 0x7F:
            return True
    return False


def _validate_string(value, field_name, allow_newlines=False):
    """Reject non-string / empty / control-char inputs at set-time.

    The field name appears in the error message so the operator sees which
    setter rejected the value, not just "invalid input". `allow_newlines`
    is threaded through to `_has_control_chars`; default False keeps this
    helper single-purpose (strictest policy) and forces callers to opt in.
    """
    if not isinstance(value, str):
        raise ValueError(
            "{0}: expected string, got {1}".format(
                field_name, type(value).__name__
            )
        )
    if not value.strip():
        raise ValueError(
            "{0}: empty value not allowed".format(field_name)
        )
    if _has_control_chars(value, allow_newlines=allow_newlines):
        raise ValueError(
            "{0}: control characters are not permitted".format(field_name)
        )


# ---------------------------------------------------------------------------
# State read / write.
# ---------------------------------------------------------------------------


def _load_state():
    """Read JSON from disk if present; otherwise return an empty dict.

    Missing file is normal (first setter call). A present-but-malformed file
    raises — we do NOT silently overwrite a corrupted state, because that
    would mask data loss from prior runs.
    """
    path = _state_file_path()
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        # Empty file — treat as no prior state. This handles the corner case
        # where an aborted write left a zero-byte file.
        return {}
    return json.loads(text)


def _write_state(state):
    """Atomically write `state` to the JSON path.

    Uses `tempfile.mkstemp` in the same directory as the target so
    `os.replace` is atomic on a single filesystem (cross-mount renames are
    not atomic and would corrupt state under crash). On any failure during
    write or replace, the temp file is unlinked and the exception
    re-raised so the caller can convert to a CLI exit code.
    """
    target = _state_file_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="wizard-render-state-",
        suffix=".json.tmp",
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


# ---------------------------------------------------------------------------
# Subcommand implementations.
# ---------------------------------------------------------------------------


def _die(message, code=1):
    """Write a prefixed error to stderr and return the CLI exit code."""
    sys.stderr.write("wizard_render: {0}\n".format(message))
    return code


def cmd_reset(args):
    """Delete the state file. Idempotent.

    - Missing state file: exit 0, no output (clean no-op).
    - Existing state file (any content): unlink, exit 0.
    - State path is a directory or unlinking fails: write a clear error to
      stderr naming the path and the OS error, return non-zero.

    Reset never reads the file's contents — empty, valid JSON, and invalid
    JSON are all handled identically by `os.unlink`.
    """
    path = _state_file_path()
    try:
        os.unlink(str(path))
    except FileNotFoundError:
        # Idempotent: nothing to delete.
        return 0
    except OSError as err:
        sys.stderr.write(
            "wizard_render reset: cannot delete {0}: {1}\n".format(str(path), err)
        )
        return 1
    return 0


# Per-field newline policy. PROJECT_NAME substitutes into single-line
# template contexts (e.g. `{{PROJECT_NAME}}` in a markdown heading) where
# an embedded LF/CR silently corrupts the rendered output — we reject at
# set-time. PROJECT_DESCRIPTION is multi-line free text (README quote,
# multi-sentence summary) so newlines are legitimate. Future setters add
# their own entry here; absence means strictest policy (no newlines), so
# new fields fail safe by default.
_ALLOW_NEWLINES_FIELDS = {"PROJECT_DESCRIPTION"}


def _set_string_field(field_name, value, subcommand_label):
    """Common path for scalar string setters writing to the JSON state file.

    `field_name` is the UPPERCASE_SNAKE_CASE key written to the state dict.
    `subcommand_label` (e.g. "set-project-name") is used in error messages
    so operators can identify the failing CLI invocation. Returns the CLI
    exit code (0 on success, non-zero on validation / I/O failure).

    Validation runs BEFORE state load — a malformed value never causes a
    state read, which keeps validation failures cheap and side-effect-free.
    """
    allow_newlines = field_name in _ALLOW_NEWLINES_FIELDS
    try:
        _validate_string(value, field_name, allow_newlines=allow_newlines)
    except ValueError as err:
        return _die("{0}: {1}".format(subcommand_label, err), code=2)
    try:
        state = _load_state()
    except (OSError, ValueError) as err:
        # ValueError covers JSONDecodeError (subclass) — corrupt state file
        # surfaces here, not silently overwritten.
        return _die(
            "{0}: cannot load state: {1}".format(subcommand_label, err)
        )
    state[field_name] = value
    try:
        _write_state(state)
    except OSError as err:
        return _die(
            "{0}: cannot write state: {1}".format(subcommand_label, err)
        )
    return 0


def cmd_set_project_name(args):
    """Persist Phase 2 Q1 answer (PROJECT_NAME) to the state file."""
    return _set_string_field("PROJECT_NAME", args.value, "set-project-name")


def cmd_set_project_description(args):
    """Persist Phase 2 Q2 answer (PROJECT_DESCRIPTION) to the state file."""
    return _set_string_field(
        "PROJECT_DESCRIPTION", args.value, "set-project-description"
    )


def cmd_set_project_type(args):
    """Persist Phase 2 Q3 answer (PROJECT_TYPE) to the state file.

    PROJECT_TYPE is a single-line category label — either one of the
    fixed taxonomy values (e.g. "Frontend / web application") or a
    free-text custom category. Newlines are rejected (not in
    `_ALLOW_NEWLINES_FIELDS`); the helper does not validate against an
    enum because Q3 permits free-text custom values.
    """
    return _set_string_field("PROJECT_TYPE", args.value, "set-project-type")


# ---------------------------------------------------------------------------
# CLI wiring.
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="wizard_render",
        description="Compose Phase 3 + Phase 4 file population for /setup-wizard.",
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    reset_parser = subparsers.add_parser(
        "reset",
        help="Delete the helper's state file. Idempotent.",
    )
    reset_parser.set_defaults(func=cmd_reset)

    set_project_name_parser = subparsers.add_parser(
        "set-project-name",
        help="Save Phase 2 Q1 answer (PROJECT_NAME) into the state file.",
    )
    set_project_name_parser.add_argument("value")
    set_project_name_parser.set_defaults(func=cmd_set_project_name)

    set_project_description_parser = subparsers.add_parser(
        "set-project-description",
        help="Save Phase 2 Q2 answer (PROJECT_DESCRIPTION) into the state file.",
    )
    set_project_description_parser.add_argument("value")
    set_project_description_parser.set_defaults(func=cmd_set_project_description)

    set_project_type_parser = subparsers.add_parser(
        "set-project-type",
        help="Save Phase 2 Q3 answer (PROJECT_TYPE) into the state file.",
    )
    set_project_type_parser.add_argument("value")
    set_project_type_parser.set_defaults(func=cmd_set_project_type)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        sys.stderr.write(
            "wizard_render: no subcommand specified. Run with --help for "
            "available subcommands.\n"
        )
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
