"""init_helper — composes the bootstrap state file for /init-forge.

Owns the shape of `.devforge/init.yaml`: 5 fields, no classification, no
inference. `/init-forge` is the first command in the 4-command pivot
(init-forge → generate-docs → configure → constitute); later commands
persist their output to their own helpers' state files.

Architecture notes:

- The yaml IS the state. Each setter reads yaml from disk (or loads
  defaults if the file is absent), mutates an in-memory dict, and writes
  yaml back atomically via tempfile.mkstemp + os.replace in the same
  directory as the target.

- Field order in the emitted yaml is fixed (deterministic output for
  diff stability) and matches the source-of-truth schema below.

- All scalars default to `None`; the array defaults to `[]`. Loud-fail
  downstream when a required field is `None` is the design — no
  "sensible default" overrides.

- `reset` writes a fresh defaults yaml; it does NOT delete the file.
  The artifact always exists post-reset. Idempotent: byte-identical on
  re-run.

- Validation is set-time per-field shape only. No cross-field invariants
  (none apply: all 5 fields are independent at this stage).

Stdlib only. No third-party dependencies. Targets Python 3.8+.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

# Published artifact name (NOT a hidden state file — downstream commands
# read it).
OUTPUT_FILE_NAME = "init.yaml"


# ---------------------------------------------------------------------------
# Schema — single source of truth for field order, kind, and defaults.
# ---------------------------------------------------------------------------

# Order is locked: the emitter walks this list, so reordering changes the
# on-disk byte order. Diff stability is part of the contract.
#
# Field kinds:
#   "scalar"               — string-or-None value
#   "package_record_array" — list of {"path": str, "manifest": str} records
FIELD_SCHEMA = (
    ("workspace_mode", "scalar"),
    ("project_root", "scalar"),
    ("project_state", "scalar"),
    ("default_branch", "scalar"),
    ("packages_detected", "package_record_array"),
)

# Enum-restricted scalars; key = field name, value = allowed set.
ENUM_FIELDS = {
    "workspace_mode": {"standalone", "wrapper"},
    "project_state": {"empty", "brownfield"},
}

# Locked field order for the `summary` subcommand. Mirrors the scalar
# fields in FIELD_SCHEMA but lives as a separate tuple so the summary
# never silently picks up a new scalar without an explicit edit here
# (and so the renderer doesn't depend on dict iteration order).
SUMMARY_WORKSPACE_FIELDS = (
    "workspace_mode",
    "project_root",
    "project_state",
    "default_branch",
)

# Built-in skip list for find-nested-git. Mirrors detect_report's set
# verbatim so /init-forge and the legacy wizard agree on which dirs to ignore.
NESTED_GIT_SKIP = {
    "node_modules",
    "target",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
    ".git",
}

# Manifest filenames recognized for the anti-corruption check in `verify`.
# Closed enum — do not expand at runtime.
_MANIFEST_FILENAMES = (
    "package.json",
    "pyproject.toml",
    "setup.py",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Gemfile",
    "composer.json",
)

# YAML reserved words (case-insensitive); a bare scalar matching one of
# these would be ambiguous, so it must be quoted.
YAML_RESERVED_WORDS = {
    "null", "true", "false", "yes", "no", "on", "off", "~", "n/a",
}

# Characters whose presence in a scalar forces quoting.
YAML_SPECIAL_CHARS = set(" :[]{},#&*!|>'\"%@`")


# ---------------------------------------------------------------------------
# Path resolution.
# ---------------------------------------------------------------------------


def _output_file_path():
    """Resolve the output file path at call time (not import time).

    Honors the `DEVFORGE_DIR` environment variable when set — used by
    tests and by unusual install layouts. When unset, computes the path
    from this script's own location: `<target>/.devforge/lib/init_helper.py`
    lives one directory below `<target>/.devforge/`, where the artifact
    belongs.
    """
    env_dir = os.environ.get("DEVFORGE_DIR")
    if env_dir:
        return Path(env_dir) / OUTPUT_FILE_NAME
    return Path(__file__).resolve().parent.parent / OUTPUT_FILE_NAME


# ---------------------------------------------------------------------------
# Defaults + validators.
# ---------------------------------------------------------------------------


def default_state():
    """Return a fresh defaults dict matching FIELD_SCHEMA shape."""
    state = {}
    for name, kind in FIELD_SCHEMA:
        if kind == "scalar":
            state[name] = None
        else:
            state[name] = []
    return state


def _has_control_chars(value):
    """Return True if `value` contains any control char (< 0x20 or DEL)."""
    for ch in value:
        code = ord(ch)
        if code < 0x20 or code == 0x7F:
            return True
    return False


def _validate_string(value, field_name):
    """Reject empty / control-char strings at set-time. Raises ValueError."""
    if not isinstance(value, str):
        raise ValueError(
            "{0}: expected string, got {1}".format(field_name, type(value).__name__)
        )
    if not value.strip():
        raise ValueError("{0}: value must be non-empty".format(field_name))
    if _has_control_chars(value):
        raise ValueError(
            "{0}: control characters are not permitted".format(field_name)
        )


def _validate_enum(value, field_name):
    """Reject values not in the allowed enum set."""
    allowed = ENUM_FIELDS[field_name]
    if value not in allowed:
        raise ValueError(
            "{0}: must be one of {1}, got {2!r}".format(
                field_name, sorted(allowed), value
            )
        )


def _validate_path(value, field_name):
    """Reject paths that escape the project root or are absolute.

    A valid path is either `.` (the project-root sentinel) or a relative
    path rooted inside the project (no leading `/` or `\\`, no Windows
    drive prefix like `C:\\` or `c:/`, and no `..` path segment that
    could traverse upward).

    Path-segment splitting recognizes BOTH `/` and `\\` as separators so
    that a Windows-style `foo\\..\\bar` is caught the same as the POSIX
    form. The trailing slash is permitted at this stage; `_normalize_path`
    strips it for storage. Empty / control-char strings are rejected
    up-front via `_validate_string` so the existing checks still run.
    """
    _validate_string(value, field_name)
    if value.startswith("/") or value.startswith("\\"):
        raise ValueError(
            "{0}: absolute paths are not permitted, got {1!r}".format(
                field_name, value
            )
        )
    if len(value) >= 2 and value[0].isalpha() and value[1] == ":":
        raise ValueError(
            "{0}: absolute paths are not permitted, got {1!r}".format(
                field_name, value
            )
        )
    segments = value.replace("\\", "/").split("/")
    for seg in segments:
        if seg == "..":
            raise ValueError(
                "{0}: parent-directory traversal '..' is not permitted, got {1!r}".format(
                    field_name, value
                )
            )


def _normalize_path(p):
    """Strip a single trailing slash. Used for path comparison + storage.

    `client/` and `client` should refer to the same directory. We
    normalize at every compare site AND at the storage site so callers
    passing either form end up with one canonical record.
    `_normalize_path("")` returns `""`, which is fine — empty strings
    are already rejected by `_validate_string`.
    """
    return p.rstrip("/")


# ---------------------------------------------------------------------------
# YAML emitter (closed-shape).
# ---------------------------------------------------------------------------


def _needs_quoting(s):
    """Return True if a string scalar must be double-quoted on emit."""
    if s == "":
        return True
    if s.lower() in YAML_RESERVED_WORDS:
        return True
    # Purely numeric (int or float-ish) — must be quoted to avoid YAML
    # interpreting as a number on read. `int(s, 0)` catches hex/octal/binary
    # prefixes (`0x...`, `0o...`, `0b...`) and leading-zero octal forms that
    # `float()` alone misses.
    try:
        int(s, 0)
        return True
    except (ValueError, TypeError):
        pass
    try:
        float(s)
        return True
    except ValueError:
        pass
    for ch in s:
        if ch in YAML_SPECIAL_CHARS:
            return True
    return False


def _emit_scalar(value):
    """Render a scalar value (str or None) as a YAML token."""
    if value is None:
        return "null"
    # Control chars are rejected at set-time; emitter only escapes " and \.
    if _needs_quoting(value):
        escaped = value.replace("\\", "\\\\").replace("\"", "\\\"")
        return "\"{0}\"".format(escaped)
    return value


def emit_yaml(state):
    """Serialize `state` to a deterministic YAML string.

    Field order follows FIELD_SCHEMA. The empty array renders as
    `packages_detected: []`. Populated arrays use block style with
    two-space indentation.
    """
    lines = []
    for name, kind in FIELD_SCHEMA:
        value = state.get(name)
        if kind == "scalar":
            lines.append("{0}: {1}".format(name, _emit_scalar(value)))
        elif kind == "package_record_array":
            if not value:
                lines.append("{0}: []".format(name))
            else:
                lines.append("{0}:".format(name))
                for record in value:
                    lines.append(
                        "  - path: {0}".format(_emit_scalar(record["path"]))
                    )
                    lines.append(
                        "    manifest: {0}".format(_emit_scalar(record["manifest"]))
                    )
        else:
            raise AssertionError("unknown field kind: {0}".format(kind))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# YAML parser (closed-shape — inverse of emitter).
# ---------------------------------------------------------------------------


class YamlParseError(ValueError):
    """Raised when parser encounters input outside the closed shape."""


def _parse_scalar_token(token, lineno):
    """Parse a single scalar token (the RHS of `key: <token>`)."""
    token = token.strip()
    if token == "null":
        return None
    if token == "[]":
        raise YamlParseError(
            "line {0}: unexpected inline empty list".format(lineno)
        )
    if token.startswith("\""):
        if not token.endswith("\"") or len(token) < 2:
            raise YamlParseError(
                "line {0}: unterminated double-quoted string".format(lineno)
            )
        body = token[1:-1]
        result = []
        i = 0
        while i < len(body):
            ch = body[i]
            if ch == "\\" and i + 1 < len(body):
                nxt = body[i + 1]
                if nxt == "\\":
                    result.append("\\")
                elif nxt == "\"":
                    result.append("\"")
                else:
                    raise YamlParseError(
                        "line {0}: unknown escape sequence \\{1}".format(lineno, nxt)
                    )
                i += 2
            else:
                result.append(ch)
                i += 1
        return "".join(result)
    if token.startswith("&") or token.startswith("*"):
        raise YamlParseError(
            "line {0}: anchors/aliases are not supported".format(lineno)
        )
    if token in ("|", ">"):
        raise YamlParseError(
            "line {0}: multi-line scalars are not supported".format(lineno)
        )
    if token.startswith("{"):
        raise YamlParseError(
            "line {0}: flow-style mappings are not supported".format(lineno)
        )
    if token.startswith("'"):
        raise YamlParseError(
            "line {0}: single-quoted strings are not supported".format(lineno)
        )
    return token


def parse_yaml(text):
    """Parse a YAML string previously emitted by `emit_yaml`.

    Returns a state dict. Raises YamlParseError on input outside the
    closed shape (anchors, flow mappings, multi-line scalars, deeper
    than one nested array level).
    """
    field_kinds = dict(FIELD_SCHEMA)
    state = default_state()
    current_field = None
    current_kind = None
    current_record = None

    lines = text.splitlines()
    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        if line == "":
            continue

        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if indent == 0:
            current_record = None
            if ":" not in stripped:
                raise YamlParseError(
                    "line {0}: expected 'key: value' or 'key:'".format(idx)
                )
            key, _, rest = stripped.partition(":")
            key = key.strip()
            rest = rest.strip()
            if key not in field_kinds:
                raise YamlParseError(
                    "line {0}: unknown top-level field {1!r}".format(idx, key)
                )
            current_field = key
            current_kind = field_kinds[key]
            if current_kind == "scalar":
                state[key] = _parse_scalar_token(rest, idx)
                current_field = None
                current_kind = None
            else:
                if rest == "[]":
                    state[key] = []
                    current_field = None
                    current_kind = None
                elif rest == "":
                    state[key] = []
                else:
                    raise YamlParseError(
                        "line {0}: expected '[]' or empty after array key, got {1!r}".format(
                            idx, rest
                        )
                    )
        elif indent == 2:
            if current_field is None or current_kind == "scalar":
                raise YamlParseError(
                    "line {0}: nested content without an open array".format(idx)
                )
            if not stripped.startswith("- "):
                raise YamlParseError(
                    "line {0}: array item must start with '- '".format(idx)
                )
            item_body = stripped[2:]
            if ":" not in item_body:
                raise YamlParseError(
                    "line {0}: array item must be 'key: value'".format(idx)
                )
            key, _, rest = item_body.partition(":")
            key = key.strip()
            rest = rest.strip()
            current_record = {key: _parse_scalar_token(rest, idx)}
            state[current_field].append(current_record)
        elif indent == 4:
            if current_record is None:
                raise YamlParseError(
                    "line {0}: continuation line without an open record".format(idx)
                )
            if ":" not in stripped:
                raise YamlParseError(
                    "line {0}: continuation must be 'key: value'".format(idx)
                )
            key, _, rest = stripped.partition(":")
            key = key.strip()
            rest = rest.strip()
            current_record[key] = _parse_scalar_token(rest, idx)
        else:
            raise YamlParseError(
                "line {0}: unexpected indentation {1}".format(idx, indent)
            )

    return state


# ---------------------------------------------------------------------------
# Read-modify-write helpers.
# ---------------------------------------------------------------------------


def _load_state():
    """Read yaml from disk if present; otherwise return defaults."""
    path = _output_file_path()
    if not path.exists():
        return default_state()
    text = path.read_text(encoding="utf-8")
    state = parse_yaml(text)
    # Backfill any field that wasn't present on disk (defensive — same
    # shape today, but cheap insurance against schema drift on read).
    for name, kind in FIELD_SCHEMA:
        if name not in state:
            state[name] = None if kind == "scalar" else []
    return state


def _write_state(state):
    """Atomically write `state` to the output yaml path.

    Uses tempfile.mkstemp in the same directory as the target so
    os.replace is atomic on a single filesystem. On any failure,
    attempts to remove the temp file and re-raises.
    """
    target = _output_file_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="init-",
        suffix=".yaml.tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(emit_yaml(state))
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
    sys.stderr.write("init_helper: {0}\n".format(message))
    return code


def cmd_reset(args):
    """Write a fresh defaults yaml. Idempotent: byte-identical on re-run."""
    try:
        _write_state(default_state())
    except OSError as err:
        return _die("reset: cannot write {0}: {1}".format(_output_file_path(), err))
    return 0


def _set_scalar(field_name, value):
    """Common path for scalar setters. Returns CLI exit code."""
    try:
        _validate_string(value, field_name)
        if field_name in ENUM_FIELDS:
            _validate_enum(value, field_name)
    except ValueError as err:
        return _die(str(err), code=2)
    try:
        state = _load_state()
    except (OSError, YamlParseError) as err:
        return _die("cannot load state: {0}".format(err))
    state[field_name] = value
    try:
        _write_state(state)
    except OSError as err:
        return _die("cannot write state: {0}".format(err))
    return 0


def cmd_set_workspace_mode(args):
    return _set_scalar("workspace_mode", args.value)


def cmd_set_project_root(args):
    # project_root is a path (`.` for standalone, an inner folder name
    # for wrapper mode), so it gets path-shape validation.  Path
    # validation runs `_validate_string` first, so empty / control-char
    # rejection still applies.
    try:
        _validate_path(args.value, "project_root")
    except ValueError as err:
        return _die(str(err), code=2)
    # Normalize trailing slash for storage so `client/` and `client`
    # land on the same on-disk value.
    value = _normalize_path(args.value)
    try:
        state = _load_state()
    except (OSError, YamlParseError) as err:
        return _die("cannot load state: {0}".format(err))
    state["project_root"] = value
    try:
        _write_state(state)
    except OSError as err:
        return _die("cannot write state: {0}".format(err))
    return 0


def cmd_set_project_state(args):
    return _set_scalar("project_state", args.value)


def cmd_set_default_branch(args):
    return _set_scalar("default_branch", args.value)


def cmd_add_package(args):
    """Append a {path, manifest} record. Errors on duplicate path."""
    try:
        _validate_path(args.path, "packages_detected.path")
        _validate_string(args.manifest, "packages_detected.manifest")
    except ValueError as err:
        return _die(str(err), code=2)
    path = _normalize_path(args.path)
    try:
        state = _load_state()
    except (OSError, YamlParseError) as err:
        return _die("cannot load state: {0}".format(err))
    for record in state["packages_detected"]:
        if _normalize_path(record.get("path", "")) == path:
            return _die(
                "add-package: path {0!r} already present in packages_detected".format(
                    path
                ),
                code=2,
            )
    state["packages_detected"].append({"path": path, "manifest": args.manifest})
    try:
        _write_state(state)
    except OSError as err:
        return _die("cannot write state: {0}".format(err))
    return 0


def _render_scalar_for_summary(value):
    """Render a scalar (str or None) as a human-readable summary token.

    `None` becomes the literal lowercase string `null` (matching the
    on-disk yaml form so the summary mirrors the file). Strings render
    verbatim — no quoting, escaping, or transformation.
    """
    if value is None:
        return "null"
    return value


def _render_summary(state):
    """Build the deterministic init-report summary string from `state`.

    Output ends with exactly one trailing newline. Field order is locked
    by SUMMARY_WORKSPACE_FIELDS — never re-derived from yaml dict order.
    Package list is rendered with a fixed-width path column (max-path
    + 2 spaces of padding) so manifests line up vertically.
    """
    lines = []
    lines.append("## Init Report")
    lines.append("")
    lines.append("### Workspace")
    for field in SUMMARY_WORKSPACE_FIELDS:
        lines.append(
            "- {0}: {1}".format(field, _render_scalar_for_summary(state.get(field)))
        )
    lines.append("")

    packages = state.get("packages_detected") or []
    pkg_count = len(packages)
    lines.append("### Packages ({0} detected)".format(pkg_count))
    if pkg_count == 0:
        lines.append("- no packages detected")
    else:
        # Column-align manifest column to (max path width + 2). Padding
        # is computed from the longest path so all manifests start at
        # the same column regardless of path length.
        max_path = max(len(record.get("path", "")) for record in packages)
        col_width = max_path + 2
        for record in packages:
            path = record.get("path", "")
            manifest = record.get("manifest", "")
            padding = " " * (col_width - len(path))
            lines.append("- {0}{1}{2}".format(path, padding, manifest))

    return "\n".join(lines) + "\n"


def cmd_summary(args):
    """Render the deterministic init-report summary to stdout.

    Reads `.devforge/init.yaml`. If the file is missing, fails with a
    clear stderr message naming the absent path. If the yaml is
    unreadable or malformed, fails with the underlying error on stderr.
    """
    path = _output_file_path()
    if not path.exists():
        sys.stderr.write(
            "init_helper summary: init.yaml not found at {0}\n".format(path)
        )
        return 1
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "init_helper summary: cannot read {0}: {1}\n".format(path, err)
        )
        return 1
    try:
        state = parse_yaml(text)
    except YamlParseError as err:
        sys.stderr.write(
            "init_helper summary: cannot parse {0}: {1}\n".format(path, err)
        )
        return 1
    sys.stdout.write(_render_summary(state))
    return 0


def _resolve_project_root(value, install_root):
    """Resolve a stored project_root value to an absolute Path.

    Honors absolute paths verbatim; treats anything else as relative to
    install_root (parent of `.devforge/`).  Returns the candidate path
    without checking existence — callers verify existence themselves.
    """
    if value is None:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    return (install_root / value).resolve()


def _scan_for_manifests(project_root, max_depth=2):
    """Return the first manifest path found at depth <= max_depth, or None.

    Depth 1 = direct child of project_root.  Depth 2 = grandchild.
    Hidden directories (names starting with '.') and common skip-dirs
    (NESTED_GIT_SKIP) are pruned at every level to avoid false positives
    in `.git`, `node_modules`, `__pycache__`, etc.
    """
    if not project_root or not project_root.is_dir():
        return None
    def _walk(directory, current_depth):
        if current_depth > max_depth:
            return None
        try:
            entries = sorted(directory.iterdir())
        except OSError:
            return None
        # Manifest scan at this level first (BFS-ish: same-depth before deeper).
        for entry in entries:
            if entry.is_file() and entry.name in _MANIFEST_FILENAMES:
                return entry
        for entry in entries:
            if not entry.is_dir():
                continue
            if entry.name.startswith("."):
                continue
            if entry.name in NESTED_GIT_SKIP:
                continue
            found = _walk(entry, current_depth + 1)
            if found is not None:
                return found
        return None
    return _walk(project_root, 1)


def cmd_verify(args):
    """State-integrity gate for /init-forge — read-only.

    Cross-checks `.devforge/init.yaml` + `.devforge/index.json` +
    `<install_root>/docs/structure.md`.  Exit 0 if every invariant holds;
    exit 2 with one stderr line per violation (`verify: <field>: <reason>`).
    """
    path = _output_file_path()
    if not path.exists():
        sys.stderr.write(
            "verify: init.yaml: not found at {0}\n".format(path)
        )
        return 2
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "verify: init.yaml: cannot read {0}: {1}\n".format(path, err)
        )
        return 2
    try:
        state = parse_yaml(text)
    except YamlParseError as err:
        sys.stderr.write(
            "verify: init.yaml: cannot parse {0}: {1}\n".format(path, err)
        )
        return 2

    install_root = path.parent.parent  # <install>/.devforge/init.yaml -> <install>

    violations = []

    workspace_mode = state.get("workspace_mode")
    if workspace_mode is None or (
        isinstance(workspace_mode, str) and not workspace_mode.strip()
    ):
        violations.append("workspace_mode: required, was empty")
    elif workspace_mode not in ENUM_FIELDS["workspace_mode"]:
        violations.append(
            "workspace_mode: invalid value {0!r} (allowed: {1})".format(
                workspace_mode,
                sorted(ENUM_FIELDS["workspace_mode"]),
            )
        )

    project_root_value = state.get("project_root")
    project_root_path = None
    if project_root_value is None or (
        isinstance(project_root_value, str) and not project_root_value.strip()
    ):
        violations.append("project_root: required, was empty")
    else:
        project_root_path = _resolve_project_root(project_root_value, install_root)
        if not project_root_path or not project_root_path.exists():
            violations.append(
                "project_root: path {0!r} does not exist (resolved to {1})".format(
                    project_root_value, project_root_path
                )
            )

    project_state = state.get("project_state")
    if project_state is None or (
        isinstance(project_state, str) and not project_state.strip()
    ):
        violations.append("project_state: required, was empty")
    elif project_state not in ENUM_FIELDS["project_state"]:
        violations.append(
            "project_state: invalid value {0!r} (allowed: {1})".format(
                project_state,
                sorted(ENUM_FIELDS["project_state"]),
            )
        )

    default_branch = state.get("default_branch")
    if default_branch is None or (
        isinstance(default_branch, str) and not default_branch.strip()
    ):
        violations.append("default_branch: required, was empty")

    packages_detected = state.get("packages_detected", [])
    if not isinstance(packages_detected, list):
        violations.append(
            "packages_detected: must be a list, got {0}".format(
                type(packages_detected).__name__
            )
        )
    elif (
        len(packages_detected) == 0
        and project_root_path
        and project_root_path.is_dir()
    ):
        found = _scan_for_manifests(project_root_path, max_depth=2)
        if found is not None:
            violations.append(
                "packages_detected: empty but on-disk manifest found at {0}".format(
                    found
                )
            )

    index_json = install_root / ".devforge" / "index.json"
    if not index_json.is_file():
        violations.append(
            "index.json: missing at {0}".format(index_json)
        )

    structure_md = install_root / "docs" / "structure.md"
    if not structure_md.is_file():
        violations.append(
            "structure.md: missing at {0}".format(structure_md)
        )

    if not violations:
        return 0
    for v in violations:
        sys.stderr.write("verify: {0}\n".format(v))
    return 2


def cmd_find_nested_git(args):
    """List depth-1 directories under the install root that contain `.git/`.

    The install root is the parent of `.devforge/` (the directory that
    owns the wizard install). Hidden dirs and the built-in skip list
    are filtered out. One path per line on stdout. No state is written.
    """
    devforge_dir = _output_file_path().parent
    install_root = devforge_dir.parent
    try:
        children = sorted(install_root.iterdir())
    except OSError as err:
        return _die(
            "find-nested-git: cannot list {0}: {1}".format(install_root, err)
        )
    for entry in children:
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith("."):
            continue
        if name in NESTED_GIT_SKIP:
            continue
        if (entry / ".git").is_dir():
            sys.stdout.write("{0}\n".format(name))
    return 0


# ---------------------------------------------------------------------------
# CLI wiring.
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="init_helper",
        description="Compose the bootstrap state file for /init-forge.",
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    sp = subparsers.add_parser("reset", help="Write a fresh defaults yaml.")
    sp.set_defaults(func=cmd_reset)

    sp = subparsers.add_parser("set-workspace-mode")
    sp.add_argument("value")
    sp.set_defaults(func=cmd_set_workspace_mode)

    sp = subparsers.add_parser("set-project-root")
    sp.add_argument("value")
    sp.set_defaults(func=cmd_set_project_root)

    sp = subparsers.add_parser("set-project-state")
    sp.add_argument("value")
    sp.set_defaults(func=cmd_set_project_state)

    sp = subparsers.add_parser("set-default-branch")
    sp.add_argument("value")
    sp.set_defaults(func=cmd_set_default_branch)

    sp = subparsers.add_parser("add-package")
    sp.add_argument("--path", required=True)
    sp.add_argument("--manifest", required=True)
    sp.set_defaults(func=cmd_add_package)

    sp = subparsers.add_parser("find-nested-git")
    sp.set_defaults(func=cmd_find_nested_git)

    sp = subparsers.add_parser("summary", help="Render the init report to stdout.")
    sp.set_defaults(func=cmd_summary)

    sp = subparsers.add_parser(
        "verify",
        help="State-integrity gate: cross-check init.yaml + index.json + docs/structure.md.",
    )
    sp.set_defaults(func=cmd_verify)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
