"""configure_helper — composes the configuration state file for /configure.

Owns the shape of `.devforge/configure.yaml`: 27 fields covering project
metadata, language/framework stacks, build/lint/type-check commands,
per-package stack records, workflow enforcement, AI attribution, Claude
tier settings, and AC verification parameters. `/configure` is the third
command in the 4-command pivot (init-forge → generate-docs → configure →
constitute).

Step 1 is fully implemented: FIELD_SCHEMA + ENUM_FIELDS populated,
emit_yaml/parse_yaml schema-driven, `reset` writes proper defaults,
read-init / read-docs / read-manifests / read-configs subcommands implemented.
Steps 2-4 (setters, render-config, substitute-templates) remain future work.

Architecture notes:

- The yaml IS the state. Each setter reads yaml from disk (or loads
  defaults if the file is absent), mutates an in-memory dict, and writes
  yaml back atomically via tempfile.mkstemp + os.replace in the same
  directory as the target.

- Field order in the emitted yaml is fixed (deterministic output for
  diff stability) and matches the source-of-truth schema below.

- `reset` writes a fresh defaults yaml; it does NOT delete the file.
  The artifact always exists post-reset. Idempotent: byte-identical on
  re-run.

- FIELD_SCHEMA contains 27 fields in locked order (project_name,
  project_description, project_type, primary_language, languages,
  frameworks, architectures, error_handlings, api_layers, testings,
  build_tools, build_commands, type_check_commands, lint_commands,
  package_stacks, project_structure, dev_commands, architecture_details,
  workflow_enforcement, ai_attribution, claude_tier_think, claude_tier_do,
  claude_tier_verify, ac_verification_mode, ac_runtime_url,
  ac_runtime_api_base, ac_runtime_cli_command).

- ENUM_FIELDS enforces allowed values at set-time for workflow_enforcement,
  ai_attribution, claude_tier_think, claude_tier_do, claude_tier_verify,
  ac_verification_mode.

- `default_state()` walks FIELD_SCHEMA and returns all 27 keys with
  type-appropriate defaults: scalars → None, arrays → [].

- `emit_yaml(state)` walks FIELD_SCHEMA in locked order, applying the same
  quoting/escaping rules as init_helper (double-quote scalars containing
  YAML special chars; null for None; block-style arrays).

- `parse_yaml(text)` is the inverse of emit_yaml. Raises YamlParseError
  on input outside the closed shape.

- `read-init` reads `.devforge/init.yaml` via init_helper.parse_yaml and
  emits JSON to stdout.

- `read-docs` parses Plan F sections from `docs/overview.md` and
  `docs/architecture.md` and emits structured JSON. Uses --install-root
  (default: parent of --devforge-dir).

- `read-manifests` reads `.devforge/index.json` and emits per-package
  script tables as JSON.

- `read-configs` reads `.devforge/index.json`, basename-matches config
  files in each package's file list, reads matched files, emits JSON.
  Uses --install-root (default: parent of --devforge-dir). Caps individual
  files at 10 KB.

- Setters, render-config, substitute-templates are not yet implemented
  (Steps 2-4 per CONFIGURE-PLAN.md).

- Validation is set-time per-field shape only. No cross-field invariants
  in Step 1 (setters not yet implemented).

- `--devforge-dir` CLI argument (default: DEVFORGE_DIR env var, falling
  back to `.devforge`) is threaded through args to all subcommand handlers.

Stdlib only. No third-party dependencies. Targets Python 3.8+.
"""

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union

# Resolve siblings as importable when invoked as `python3 configure_helper.py`.
_LIB_DIR = str(Path(__file__).resolve().parent)
if _LIB_DIR not in sys.path:
    sys.path.insert(0, _LIB_DIR)

import init_helper  # noqa: E402

# Published artifact name (NOT a hidden state file — downstream commands
# read it).
OUTPUT_FILE_NAME = "configure.yaml"


# ---------------------------------------------------------------------------
# Schema — single source of truth for field order, kind, and defaults.
# ---------------------------------------------------------------------------

# Order is locked: the emitter walks this list, so reordering changes the
# on-disk byte order. Diff stability is part of the contract.
#
# Field kinds:
#   "scalar"               — string-or-None value
#   "string_array"         — list of strings (default [])
#   "package_stack_array"  — list of per-package stack records (default [])
FIELD_SCHEMA = (
    # Identity
    ("project_name",           "scalar"),
    ("project_description",    "scalar"),
    ("project_type",           "scalar"),

    # Stack
    ("primary_language",       "scalar"),
    ("languages",              "string_array"),
    ("frameworks",             "string_array"),
    ("architectures",          "string_array"),
    ("error_handlings",        "string_array"),
    ("api_layers",             "string_array"),
    ("testings",               "string_array"),
    ("build_tools",            "string_array"),

    # Per-package
    ("build_commands",         "string_array"),
    ("type_check_commands",    "string_array"),
    ("lint_commands",          "string_array"),
    ("package_stacks",         "package_stack_array"),

    # Verbatim from docs/
    ("project_structure",      "scalar"),
    ("dev_commands",           "scalar"),
    ("architecture_details",   "scalar"),

    # User-only preferences
    ("workflow_enforcement",   "scalar"),
    ("ai_attribution",         "scalar"),
    ("claude_tier_think",      "scalar"),
    ("claude_tier_do",         "scalar"),
    ("claude_tier_verify",     "scalar"),

    # AC verification
    ("ac_verification_mode",   "scalar"),
    ("ac_runtime_url",         "scalar"),
    ("ac_runtime_api_base",    "scalar"),
    ("ac_runtime_cli_command", "scalar"),
)

# Enum-restricted scalars; key = field name, value = allowed set.
# Enforced at set-time by setters (Step 2). Exposed here for documentation
# and future validation; emit_yaml/parse_yaml do NOT enforce enum values.
ENUM_FIELDS = {
    "workflow_enforcement":  {"Strict", "Moderate", "Light"},
    "ai_attribution":        {"Yes", "No"},
    "claude_tier_think":     {"Opus", "Sonnet", "Haiku", "Other"},
    "claude_tier_do":        {"Opus", "Sonnet", "Haiku", "Other"},
    "claude_tier_verify":    {"Opus", "Sonnet", "Haiku", "Other"},
    "ac_verification_mode":  {"code-only", "tests", "runtime-assisted", "off"},
}

# package_stack_array record field order — locked so emit is deterministic.
_PACKAGE_STACK_FIELDS = (
    "path",
    "language",
    "framework",
    "build_tool",
    "build_command",
    "type_check_command",
    "lint_command",
)

# YAML reserved words (case-insensitive); a bare scalar matching one of
# these would be ambiguous, so it must be quoted.
_YAML_RESERVED_WORDS = {
    "null", "true", "false", "yes", "no", "on", "off", "~", "n/a",
}

# Characters whose presence in a scalar forces quoting. Newlines/CR are
# included so multi-line scalars (e.g. project_structure verbatim from
# docs/) round-trip via \n/\r escape sequences instead of producing
# broken yaml that splits across physical lines.
_YAML_SPECIAL_CHARS = set(" :[]{},#&*!|>'\"%@`\n\r")


# ---------------------------------------------------------------------------
# Path resolution.
# ---------------------------------------------------------------------------


def _output_file_path(devforge_dir: Union[str, "os.PathLike[str]"]) -> Path:
    """Return the output file path for the given devforge directory.

    Joins OUTPUT_FILE_NAME to devforge_dir. The devforge_dir is supplied
    explicitly by callers (threaded from CLI args or from the DEVFORGE_DIR
    env var via main()) — not resolved from the environment at call time.
    This makes the path explicit at every call site.
    """
    return Path(devforge_dir) / OUTPUT_FILE_NAME


# ---------------------------------------------------------------------------
# Defaults.
# ---------------------------------------------------------------------------


def default_state() -> dict:
    """Return a fresh defaults dict matching FIELD_SCHEMA shape.

    Walks FIELD_SCHEMA and returns all 27 keys with type-appropriate
    defaults: scalars → None, string_array → [], package_stack_array → [].
    """
    state = {}
    for name, kind in FIELD_SCHEMA:
        if kind == "scalar":
            state[name] = None
        else:
            state[name] = []
    return state


# ---------------------------------------------------------------------------
# YAML emitter (schema-driven).
# ---------------------------------------------------------------------------


def _needs_quoting(s: str) -> bool:
    """Return True if a string scalar must be double-quoted on emit.

    Matches init_helper._needs_quoting logic exactly: empty string,
    YAML reserved words, purely numeric strings, and strings containing
    YAML special chars all require quoting.
    """
    if s == "":
        return True
    if s.lower() in _YAML_RESERVED_WORDS:
        return True
    # Purely numeric (int or float-ish) — must be quoted.
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
        if ch in _YAML_SPECIAL_CHARS:
            return True
    return False


def _emit_scalar(value: Optional[str]) -> str:
    """Render a scalar value (str or None) as a YAML token.

    None → null. Strings are double-quoted when _needs_quoting is True,
    with embedded backslashes, double-quotes, newlines, and carriage
    returns escaped. Mirrors init_helper._emit_scalar plus newline
    escaping (intentional divergence so verbatim multi-line docs
    sections round-trip).
    """
    if value is None:
        return "null"
    if _needs_quoting(value):
        escaped = (
            value.replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
        )
        return "\"{0}\"".format(escaped)
    return value


def emit_yaml(state: dict) -> str:
    """Serialize `state` to a deterministic YAML string.

    Walks FIELD_SCHEMA in locked order. Field order is part of the
    diff-stability contract — do not sort or reorder.

    scalar None → null
    scalar str  → double-quoted when needed; unquoted otherwise
    string_array empty → []
    string_array populated → block list, each item double-quoted
    package_stack_array empty → []
    package_stack_array populated → block records, nullable sub-fields as null
    """
    lines = []
    for name, kind in FIELD_SCHEMA:
        value = state.get(name)
        if kind == "scalar":
            lines.append("{0}: {1}".format(name, _emit_scalar(value)))
        elif kind == "string_array":
            if not value:
                lines.append("{0}: []".format(name))
            else:
                lines.append("{0}:".format(name))
                for item in value:
                    lines.append("  - {0}".format(_emit_scalar(item)))
        elif kind == "package_stack_array":
            if not value:
                lines.append("{0}: []".format(name))
            else:
                lines.append("{0}:".format(name))
                for record in value:
                    first = True
                    for field in _PACKAGE_STACK_FIELDS:
                        fval = record.get(field)
                        token = _emit_scalar(fval)
                        if first:
                            lines.append("  - {0}: {1}".format(field, token))
                            first = False
                        else:
                            lines.append("    {0}: {1}".format(field, token))
        else:
            raise AssertionError("unknown field kind: {0}".format(kind))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# YAML parser (closed-shape — inverse of emitter).
# ---------------------------------------------------------------------------


class YamlParseError(ValueError):
    """Raised when parser encounters input outside the closed shape."""


def _parse_scalar_token(token: str, lineno: int) -> Optional[str]:
    """Parse a single scalar token (the RHS of `key: <token>`).

    Mirrors init_helper._parse_scalar_token exactly.
    """
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
                elif nxt == "n":
                    result.append("\n")
                elif nxt == "r":
                    result.append("\r")
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


def parse_yaml(text: str) -> dict:
    """Parse a YAML string previously emitted by `emit_yaml`.

    Returns a state dict matching FIELD_SCHEMA shape. Raises YamlParseError
    on input outside the closed shape (anchors, flow mappings, multi-line
    scalars, unknown fields, unexpected indentation).

    Round-trip invariant: parse_yaml(emit_yaml(state)) == state for all
    valid state shapes.
    """
    field_kinds = dict(FIELD_SCHEMA)
    state = default_state()
    current_field = None
    current_kind = None
    current_record = None  # for package_stack_array records
    current_record_lineno = 0  # for missing-subfield error message

    def _close_record(at_lineno):
        # Close the open package_stack record (if any) by validating it
        # has all 7 required subfields. Closed-shape contract: a record
        # missing any subfield is rejected at parse time.
        if current_record is None:
            return
        missing = [f for f in _PACKAGE_STACK_FIELDS if f not in current_record]
        if missing:
            raise YamlParseError(
                "line {0}: package_stack record opened at line {1} "
                "is missing required subfield(s): {2}".format(
                    at_lineno, current_record_lineno, ", ".join(missing)
                )
            )

    lines = text.splitlines()
    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.rstrip()
        if line == "":
            continue

        stripped = line.lstrip()
        indent = len(line) - len(stripped)

        if indent == 0:
            _close_record(idx)
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
                # string_array or package_stack_array
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
            if current_kind == "string_array":
                # Items are scalars.
                state[current_field].append(_parse_scalar_token(item_body, idx))
                current_record = None
            elif current_kind == "package_stack_array":
                # New record starting — close prior (if any) before opening.
                _close_record(idx)
                # First field of a record.
                if ":" not in item_body:
                    raise YamlParseError(
                        "line {0}: package_stack record item must be 'key: value'".format(idx)
                    )
                key, _, rest = item_body.partition(":")
                key = key.strip()
                rest = rest.strip()
                current_record = {key: _parse_scalar_token(rest, idx)}
                current_record_lineno = idx
                state[current_field].append(current_record)
        elif indent == 4:
            # Continuation of a package_stack_array record.
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

    # End of input — validate any record still open.
    _close_record(len(lines))
    return state


# ---------------------------------------------------------------------------
# Atomic write helper.
# ---------------------------------------------------------------------------


def _write_state(state: dict, devforge_dir: Union[str, "os.PathLike[str]"]) -> None:
    """Atomically write `state` to the output yaml path.

    Uses tempfile.mkstemp in the same directory as the target so
    os.replace is atomic on a single filesystem. flush + fsync before
    os.replace adds a durability barrier. On any failure, attempts to
    remove the temp file and re-raises.
    """
    target = _output_file_path(devforge_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="configure-",
        suffix=".yaml.tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(emit_yaml(state))
            f.flush()
            os.fsync(f.fileno())
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


def _die(message: str, code: int = 1) -> int:
    sys.stderr.write("configure_helper: {0}\n".format(message))
    return code


def cmd_reset(args: argparse.Namespace) -> int:
    """Write a fresh defaults yaml. Idempotent: byte-identical on re-run."""
    try:
        _write_state(default_state(), args.devforge_dir)
    except OSError as err:
        return _die(
            "reset: cannot write {0}: {1}".format(
                _output_file_path(args.devforge_dir), err
            )
        )
    return 0


def cmd_read_init(args: argparse.Namespace) -> int:
    """Read .devforge/init.yaml and emit JSON to stdout.

    Uses init_helper.parse_yaml so the parser is the real producer.
    Exits 1 with a stderr message if init.yaml is missing or malformed.
    """
    init_yaml_path = Path(args.devforge_dir) / init_helper.OUTPUT_FILE_NAME
    if not init_yaml_path.exists():
        sys.stderr.write(
            "configure_helper read-init: init.yaml not found at {0}\n".format(
                init_yaml_path
            )
        )
        return 1
    try:
        text = init_yaml_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "configure_helper read-init: cannot read {0}: {1}\n".format(
                init_yaml_path, err
            )
        )
        return 1
    try:
        state = init_helper.parse_yaml(text)
    except init_helper.YamlParseError as err:
        sys.stderr.write(
            "configure_helper read-init: cannot parse {0}: {1}\n".format(
                init_yaml_path, err
            )
        )
        return 1
    sys.stdout.write(json.dumps(state, indent=2))
    sys.stdout.write("\n")
    return 0


# ---------------------------------------------------------------------------
# Markdown parsing helpers for read-docs.
# ---------------------------------------------------------------------------


def _extract_section(md_text: str, heading: str) -> str:
    """Return body of '## <heading>' section from md_text.

    Body = lines AFTER the '## <heading>' line, UP TO (not including)
    the next '## ' heading or EOF. Preserves whitespace and fenced code
    blocks; a '## ' line INSIDE a fenced code block does NOT terminate
    the section (fence-aware). Returns empty string if heading not found.
    """
    target = "## {0}".format(heading)
    lines = md_text.splitlines(keepends=True)
    in_section = False
    in_fence = False
    body_lines = []
    for line in lines:
        rstripped = line.rstrip()
        if in_section:
            if rstripped.startswith("```"):
                in_fence = not in_fence
            if not in_fence and rstripped.startswith("## "):
                break
            body_lines.append(line)
        elif rstripped == target:
            in_section = True
    body = "".join(body_lines)
    # Strip leading/trailing blank lines but preserve internal structure.
    return body.strip()


def _parse_md_table(text: str) -> List[Dict[str, str]]:
    """Parse the first GitHub-style markdown table found in text.

    Returns a list of dicts keyed by header column names (lowercased,
    spaces replaced with underscores). Skips the alignment row (|---|---|).
    Returns [] if no table is found.
    """
    lines = text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|") and "|" in stripped[1:]:
            # Check if the next line is an alignment row.
            if i + 1 < len(lines):
                next_stripped = lines[i + 1].strip()
                if re.match(r"^\|[-| :]+\|$", next_stripped):
                    header_idx = i
                    break
    if header_idx is None:
        return []

    # Parse header.
    header_line = lines[header_idx].strip()
    headers = [
        col.strip().lower().replace(" ", "_")
        for col in header_line.strip("|").split("|")
    ]

    # Skip alignment row and parse data rows.
    records = []
    for i in range(header_idx + 2, len(lines)):
        row = lines[i].strip()
        if not row.startswith("|"):
            break
        cols = [col.strip() for col in row.strip("|").split("|")]
        # Pad or trim to match header count.
        while len(cols) < len(headers):
            cols.append("")
        record = {headers[j]: cols[j] for j in range(len(headers))}
        records.append(record)

    return records


def _parse_md_bullets(text: str) -> List[str]:
    """Parse bullet and numbered list items from text.

    Accepts '- ' prefix or '1. ' / 'N. ' numbered list. Returns flat list
    of stripped item texts. Returns [] if no list items found.
    """
    items = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
        elif re.match(r"^\d+\.\s", stripped):
            items.append(re.sub(r"^\d+\.\s+", "", stripped))
    return items


def _parse_module_map(text: str) -> dict:
    """Parse ### Infrastructure Packages / ### Core Package / ### Domain Packages sub-sections.

    Each sub-section contains a markdown table. Returns a dict with keys
    'infrastructure', 'core', 'domain' — only includes keys whose sub-sections
    are present and parse to non-empty tables.
    """
    result = {}
    buckets = {
        "infrastructure": "Infrastructure Packages",
        "core": "Core Package",
        "domain": "Domain Packages",
    }
    for key, heading in buckets.items():
        target = "### {0}".format(heading)
        lines = text.splitlines(keepends=True)
        in_sub = False
        sub_lines = []
        for line in lines:
            if in_sub:
                if line.startswith("### ") or line.startswith("## "):
                    break
                sub_lines.append(line)
            elif line.rstrip() == target:
                in_sub = True
        if sub_lines:
            sub_text = "".join(sub_lines)
            rows = _parse_md_table(sub_text)
            if rows:
                result[key] = rows
    return result


def _parse_patterns(text: str) -> List[dict]:
    """Parse ### <name> sub-sections from text.

    Each sub-section may contain:
    - **Applies in**: <text>
    - Prose paragraphs
    - Fenced code blocks (``` ... ```)

    Returns one record per pattern with keys:
      name, applies_in, snippet_lang, snippet (empty string if no code block).
    """
    patterns = []
    lines = text.splitlines(keepends=True)
    current_name = None
    current_lines = []

    def _flush():
        if current_name is None:
            return
        body = "".join(current_lines).strip()
        applies_in = ""
        m = re.search(r"\*\*Applies in\*\*:\s*(.+)", body)
        if m:
            applies_in = m.group(1).strip()
        snippet_lang = ""
        snippet = ""
        fence_m = re.search(r"```(\w*)\n(.*?)```", body, re.DOTALL)
        if fence_m:
            snippet_lang = fence_m.group(1).strip()
            snippet = fence_m.group(2).rstrip()
        patterns.append({
            "name": current_name,
            "applies_in": applies_in,
            "snippet_lang": snippet_lang,
            "snippet": snippet,
        })

    for line in lines:
        if line.startswith("### "):
            _flush()
            current_name = line[4:].strip()
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    _flush()
    return patterns


def _parse_overview_md(md_text: str) -> dict:
    """Parse docs/overview.md into a structured dict.

    Extracts all Plan F sections. Missing sections emit empty values.
    """
    purpose = _extract_section(md_text, "Purpose")
    tech_stack_body = _extract_section(md_text, "Tech Stack")
    tech_stack = _parse_md_table(tech_stack_body)
    project_structure = _extract_section(md_text, "Project Structure")
    entry_points_body = _extract_section(md_text, "Entry Points")
    entry_points = _parse_md_table(entry_points_body)
    key_commands_body = _extract_section(md_text, "Key Commands")
    key_commands = _parse_md_table(key_commands_body)
    module_map_body = _extract_section(md_text, "Module Map")
    module_map = _parse_module_map(module_map_body)
    cross_module_dependencies = _extract_section(md_text, "Cross-Module Dependencies")
    app_routes_body = _extract_section(md_text, "Application Routes")
    application_routes = _parse_md_table(app_routes_body)
    nav_guards_body = _extract_section(md_text, "Navigation Guards")
    navigation_guards = _parse_md_bullets(nav_guards_body)
    test_files_body = _extract_section(md_text, "Test Files")
    test_files = _parse_md_bullets(test_files_body)
    packages_body = _extract_section(md_text, "Packages")
    packages = _parse_md_bullets(packages_body)

    return {
        "purpose": purpose,
        "tech_stack": tech_stack,
        "project_structure": project_structure,
        "entry_points": entry_points,
        "key_commands": key_commands,
        "module_map": module_map,
        "cross_module_dependencies": cross_module_dependencies,
        "application_routes": application_routes,
        "navigation_guards": navigation_guards,
        "test_files": test_files,
        "packages": packages,
    }


def _parse_architecture_md(md_text: str) -> dict:
    """Parse docs/architecture.md into a structured dict.

    Extracts all Plan F sections. Missing sections emit empty values.
    """
    architecture_overview = _extract_section(md_text, "Architecture Overview")
    module_structure = _extract_section(md_text, "Module/Package Structure")
    if not module_structure:
        module_structure = _extract_section(md_text, "Module Structure")
    patterns_body = _extract_section(md_text, "Patterns")
    patterns = _parse_patterns(patterns_body)
    conventions = _extract_section(md_text, "Conventions")
    layers_body = _extract_section(md_text, "Layers")
    layers = _parse_md_bullets(layers_body)
    cross_cuts_body = _extract_section(md_text, "Cross-Cuts")
    cross_cuts = _parse_md_bullets(cross_cuts_body)
    dep_rules_body = _extract_section(md_text, "Dependency Direction Rules")
    dependency_direction_rules = _parse_md_bullets(dep_rules_body)
    dependency_overview = _extract_section(md_text, "Dependency Overview")

    return {
        "architecture_overview": architecture_overview,
        "module_structure": module_structure,
        "patterns": patterns,
        "conventions": conventions,
        "layers": layers,
        "cross_cuts": cross_cuts,
        "dependency_direction_rules": dependency_direction_rules,
        "dependency_overview": dependency_overview,
    }


def cmd_read_docs(args: argparse.Namespace) -> int:
    """Parse Plan F sections from docs/overview.md + docs/architecture.md.

    Emits structured JSON to stdout. Exits 1 if either file is missing.
    Uses --install-root (default: parent of --devforge-dir).
    """
    install_root = Path(args.install_root)
    overview_path = install_root / "docs" / "overview.md"
    arch_path = install_root / "docs" / "architecture.md"

    if not overview_path.exists():
        sys.stderr.write(
            "configure_helper read-docs: docs/overview.md not found at {0}\n".format(
                overview_path
            )
        )
        return 1
    if not arch_path.exists():
        sys.stderr.write(
            "configure_helper read-docs: docs/architecture.md not found at {0}\n".format(
                arch_path
            )
        )
        return 1

    try:
        overview_text = overview_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "configure_helper read-docs: cannot read {0}: {1}\n".format(
                overview_path, err
            )
        )
        return 1
    try:
        arch_text = arch_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "configure_helper read-docs: cannot read {0}: {1}\n".format(
                arch_path, err
            )
        )
        return 1

    output = {
        "overview": _parse_overview_md(overview_text),
        "architecture": _parse_architecture_md(arch_text),
    }
    sys.stdout.write(json.dumps(output, indent=2))
    sys.stdout.write("\n")
    return 0


# ---------------------------------------------------------------------------
# read-manifests implementation.
# ---------------------------------------------------------------------------

# Build tool hint derivation: if any of these names appear in dependency
# keys (deps or devDeps), the corresponding hint is emitted. First match wins.
_BUILD_TOOL_HINTS = (
    ("vite",    "vite"),
    ("webpack", "webpack"),
    ("rollup",  "rollup"),
    ("next",    "next"),
    ("tsc",     "tsc"),
)


def _derive_build_tool_hint(
    dependencies: dict, dev_dependencies: dict
) -> Optional[str]:
    """Derive a build tool hint from package dependencies.

    Checks dep key names (case-insensitive exact match on the bare tool
    name component). Returns None if no known build tool is detected.
    """
    all_deps = {}
    all_deps.update(dependencies or {})
    all_deps.update(dev_dependencies or {})
    lower_keys = {k.lower() for k in all_deps}
    for tool, hint in _BUILD_TOOL_HINTS:
        if tool in lower_keys:
            return hint
    return None


def cmd_read_manifests(args: argparse.Namespace) -> int:
    """Read .devforge/index.json and emit per-package script tables as JSON.

    Exits 1 if index.json is missing or unreadable.
    """
    index_path = Path(args.devforge_dir) / "index.json"
    if not index_path.exists():
        sys.stderr.write(
            "configure_helper read-manifests: index.json not found at {0}\n".format(
                index_path
            )
        )
        return 1
    try:
        text = index_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "configure_helper read-manifests: cannot read {0}: {1}\n".format(
                index_path, err
            )
        )
        return 1
    try:
        index = json.loads(text)
    except (json.JSONDecodeError, ValueError) as err:
        sys.stderr.write(
            "configure_helper read-manifests: cannot parse {0}: {1}\n".format(
                index_path, err
            )
        )
        return 1

    packages_out = []
    for pkg in index.get("packages", []):
        path = pkg.get("path", "")
        manifest = pkg.get("manifest", "")
        scripts = pkg.get("manifest_scripts") or {}
        deps = pkg.get("manifest_dependencies") or {}
        dev_deps = pkg.get("manifest_dev_dependencies") or {}
        hint = _derive_build_tool_hint(deps, dev_deps)
        packages_out.append({
            "path": path,
            "manifest": manifest,
            "scripts": scripts,
            "dependencies": deps,
            "dev_dependencies": dev_deps,
            "build_tool_hint": hint,
        })

    sys.stdout.write(json.dumps({"packages": packages_out}, indent=2))
    sys.stdout.write("\n")
    return 0


# ---------------------------------------------------------------------------
# read-configs implementation.
# ---------------------------------------------------------------------------

# Fixed pattern set for config file basename matching.
_CONFIG_FILE_BASENAMES = {
    "vite.config.ts", "vite.config.js", "vite.config.mjs",
    "next.config.ts", "next.config.js", "next.config.mjs",
    "nuxt.config.ts", "nuxt.config.js",
    "webpack.config.ts", "webpack.config.js",
    "vitest.config.ts", "vitest.config.js",
    "jest.config.ts", "jest.config.js",
    ".env", ".env.local", ".env.development",
}

# Maximum bytes to read per config file (10 KB).
_CONFIG_FILE_MAX_BYTES = 10 * 1024


def cmd_read_configs(args: argparse.Namespace) -> int:
    """Basename-match config files from index.json; emit JSON.

    Reads .devforge/index.json, walks every package's files[], matches
    basenames against _CONFIG_FILE_BASENAMES. Reads matched files from
    <install_root>/<package_path>/<file>. Caps each file at 10 KB
    (truncated: true flag set when cap is hit).

    Exits 0 even if no matches found. Exits 1 only if index.json missing.
    """
    index_path = Path(args.devforge_dir) / "index.json"
    if not index_path.exists():
        sys.stderr.write(
            "configure_helper read-configs: index.json not found at {0}\n".format(
                index_path
            )
        )
        return 1
    try:
        text = index_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "configure_helper read-configs: cannot read {0}: {1}\n".format(
                index_path, err
            )
        )
        return 1
    try:
        index = json.loads(text)
    except (json.JSONDecodeError, ValueError) as err:
        sys.stderr.write(
            "configure_helper read-configs: cannot parse {0}: {1}\n".format(
                index_path, err
            )
        )
        return 1

    install_root = Path(args.install_root)
    matched_files = []

    for pkg in index.get("packages", []):
        pkg_path = pkg.get("path", "")
        for file_rel in pkg.get("files", []):
            basename = Path(file_rel).name
            if basename not in _CONFIG_FILE_BASENAMES:
                continue
            # Construct absolute path: install_root / pkg_path / file_rel
            if pkg_path and pkg_path != ".":
                abs_path = install_root / pkg_path / file_rel
            else:
                abs_path = install_root / file_rel
            # Relative path for output (package_path / file_rel).
            if pkg_path and pkg_path != ".":
                out_path = "{0}/{1}".format(pkg_path, file_rel)
            else:
                out_path = file_rel

            contents = ""
            truncated = False
            try:
                raw = abs_path.read_bytes()
                if len(raw) > _CONFIG_FILE_MAX_BYTES:
                    raw = raw[:_CONFIG_FILE_MAX_BYTES]
                    truncated = True
                contents = raw.decode("utf-8", errors="replace")
            except OSError:
                # File listed in index but not readable — skip.
                continue

            matched_files.append({
                "path": out_path,
                "basename": basename,
                "contents": contents,
                "truncated": truncated,
            })

    sys.stdout.write(json.dumps({"matched_files": matched_files}, indent=2))
    sys.stdout.write("\n")
    return 0


# ---------------------------------------------------------------------------
# CLI wiring.
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    default_devforge_dir = os.environ.get("DEVFORGE_DIR", ".devforge")

    parser = argparse.ArgumentParser(
        prog="configure_helper",
        description="Compose the configuration state file for /configure.",
    )
    parser.add_argument(
        "--devforge-dir",
        default=default_devforge_dir,
        dest="devforge_dir",
        help=(
            "Directory for devforge state files. "
            "Default: DEVFORGE_DIR env var, or '.devforge'."
        ),
    )
    parser.add_argument(
        "--install-root",
        dest="install_root",
        default=None,
        help=(
            "Install root (parent of devforge-dir). "
            "Default: parent of --devforge-dir. Used by read-docs + read-configs."
        ),
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    sp = subparsers.add_parser("reset", help="Write a fresh defaults yaml.")
    sp.set_defaults(func=cmd_reset)

    sp = subparsers.add_parser(
        "read-init",
        help="Read .devforge/init.yaml and emit JSON to stdout.",
    )
    sp.set_defaults(func=cmd_read_init)

    sp = subparsers.add_parser(
        "read-docs",
        help="Parse Plan F docs sections and emit structured JSON to stdout.",
    )
    sp.set_defaults(func=cmd_read_docs)

    sp = subparsers.add_parser(
        "read-manifests",
        help="Read index.json and emit per-package script tables as JSON.",
    )
    sp.set_defaults(func=cmd_read_manifests)

    sp = subparsers.add_parser(
        "read-configs",
        help="Basename-match config files from index.json and emit JSON.",
    )
    sp.set_defaults(func=cmd_read_configs)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2

    # Resolve --install-root default (top-level flag, used by read-docs + read-configs).
    if args.install_root is None:
        args.install_root = str(Path(args.devforge_dir).resolve().parent)

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
