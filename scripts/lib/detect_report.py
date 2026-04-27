#!/usr/bin/env python3
"""Detection Report composer for setup-wizard Phase 1.

The setup-wizard LLM calls this tool once per Detection Report field
(`set`, `add-package`), checks progress (`status`), and writes the
final YAML to `.devforge/detection_report.yaml` (`compose`).

Stdlib only. No third-party dependencies. Target Python: 3.8+.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# ─── Paths ───────────────────────────────────────────────────────────────────
# The wizard invokes this tool from the target project root. `.devforge/` is
# created by install.sh; we still mkdir defensively for ad-hoc / test use.

DEVFORGE_DIR = Path(".devforge")
STATE_FILE = DEVFORGE_DIR / ".detection-report-state.json"
OUTPUT_FILE = DEVFORGE_DIR / "detection_report.yaml"


# ─── Schema ──────────────────────────────────────────────────────────────────
# Dataclasses mirror the YAML template in
# src/commands/setup-wizard/references/detect.md (lines 358-427) 1:1.
# Field names, nesting, and ordering preserved so the compose-step emitter
# can produce byte-identical YAML shape.


@dataclass
class LanguageEntry:
    name: str | None = None
    file_count: int = 0
    runtime: str | None = None


@dataclass
class FrameworkEntry:
    name: str | None = None
    role: str | None = None  # frontend | backend | library | plugin
    evidence: str | None = None


@dataclass
class PackageManager:
    tool: str | None = None
    outer_tool: str | None = None
    evidence: str | None = None


@dataclass
class ErrorHandling:
    library: str | None = None
    usage_pattern: str | None = None


@dataclass
class RuntimeURL:
    value: str | None = None
    source: str | None = None


@dataclass
class Package:
    path: str | None = None
    manifest: str | None = None
    language_hint: str | None = None
    framework_hint: str | None = None
    build_command: str | None = None
    type_check_command: str | None = None
    lint_command: str | None = None
    test_command: str | None = None
    command_source: str | None = None  # manifest | fallback


@dataclass
class OptionalSection:
    utility_manifests: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)  # stack-specific slots


@dataclass
class DetectionReport:
    workspace_mode: str | None = None  # standalone | wrapper
    source_root: str | None = None
    project_state: str | None = None  # empty | greenfield | brownfield
    default_branch: str | None = None
    file_count: int = 0
    manifest_count: int = 0

    languages: list[LanguageEntry] = field(default_factory=list)
    primary_language: str | None = None

    frameworks: list[FrameworkEntry] = field(default_factory=list)

    package_manager: PackageManager = field(default_factory=PackageManager)
    monorepo_tool: str | None = None

    build_tool: str | None = None
    build_command: str | None = None
    type_check_command: str | None = None
    lint_command: str | None = None
    test_runner: str | None = None

    # Library-category fields (dep+usage double-check rule per detect.md Rule 6).
    auth_layer: str | None = None
    api_client: str | None = None
    state_management: str | None = None
    styling: str | None = None
    routing: str | None = None
    error_handling: ErrorHandling = field(default_factory=ErrorHandling)
    validation_library: str | None = None

    architecture_shape: str | None = None
    architecture_evidence: str | None = None

    enforcement_tooling: list[str] = field(default_factory=list)
    ci_cd: str | None = None
    containerization: str | None = None

    runtime_url: RuntimeURL = field(default_factory=RuntimeURL)

    packages: list[Package] = field(default_factory=list)

    optional: OptionalSection = field(default_factory=OptionalSection)


# ─── State file RW ───────────────────────────────────────────────────────────
# State between set / add-package / status / compose calls is persisted as
# JSON. Shape mirrors dataclasses.asdict(DetectionReport()). The state file
# is ephemeral — compose deletes it after successful emit.


def default_state() -> dict[str, Any]:
    """Return a fresh state dict matching the DetectionReport default shape."""
    return asdict(DetectionReport())


def load_state() -> dict[str, Any]:
    """Load existing state, or return default shape if no state file exists."""
    if not STATE_FILE.exists():
        return default_state()
    with STATE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict[str, Any]) -> None:
    """Write state atomically (temp file + rename) to resist partial writes.

    The mkdir is defensive: install.sh creates .devforge/ eagerly, but this
    composer is also exercised standalone (tests) and via update flows
    where install.sh may not have re-run. Belt-and-suspenders per
    PATH-B-IMPLEMENTATION.md Step 3.3 (option c).
    """
    DEVFORGE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(STATE_FILE.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=False)
        f.write("\n")
    os.replace(tmp, STATE_FILE)


def clear_state() -> None:
    """Delete the state file. Called by compose after successful emit."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()


# ─── Validation tables ───────────────────────────────────────────────────────
# Strict enums enforced at `set` time. Null passes (enum check runs only on
# non-None values). Soft enums (package_manager.tool, test_runner) are
# free-form per detect.md — not validated here.
#
# Deferred-decision note: these tables may relocate to a shared JSON schema
# (see PATH-B-IMPLEMENTATION.md "Deferred decisions") once Path B ships.

_ENUMS: dict[str, set[str]] = {
    "workspace_mode": {"standalone", "wrapper"},
    "project_state": {"empty", "greenfield", "brownfield"},
    "architecture_shape": {
        "layered",
        "feature-modular",
        "monorepo",
        "feature-modular-monorepo",
        "clean",
        "clean-feature-modular-monorepo",
        "hexagonal",
        "mvc",
        "bloc",
        "flat",
        "other",
    },
    "monorepo_tool": {
        "Lerna",
        "Turborepo",
        "Nx",
        "pnpm-workspaces",
        "Cargo-workspace",
        "Go-workspace",
    },
}

_FRAMEWORK_ROLES = ("frontend", "backend", "library", "plugin")

# compose refuses unless every required scalar appears in state["_set_fields"]
# (explicit `set` calls) and every required non-empty list has ≥1 entry.
_REQUIRED_SCALARS: tuple[str, ...] = (
    "workspace_mode",
    "source_root",
    "project_state",
    "default_branch",
    "file_count",
    "manifest_count",
    "primary_language",
    "package_manager.tool",
    "architecture_shape",
    "architecture_evidence",
    "runtime_url.value",
)
_REQUIRED_NONEMPTY_LISTS: tuple[str, ...] = ("languages", "packages")

# When the LLM sets these paths to null, --reason is mandatory. Narrow by
# design: these are fields where null signals a deliberate project property
# ("no web runtime: backend-only service") rather than absence-of-check.
# Can expand in Phase 4 if R5 evidence shows a gap.
_NULL_REASON_REQUIRED: tuple[str, ...] = ("runtime_url.value",)

# Library-category scalars. When set to a non-null value, --evidence must
# accompany the call. Evidence is stashed in state["_evidence"] and enforces
# LLM discipline per detect.md Rule 6 (dep+usage double-check); evidence is
# not emitted to the YAML today (schema promotion to {value, evidence}
# objects deferred to Phase 4 if R5 shows populate.md wants it).
_LIBRARY_CATEGORY_FIELDS: tuple[str, ...] = (
    "auth_layer",
    "api_client",
    "state_management",
    "styling",
    "routing",
    "validation_library",
)


# ─── Value coercion + path walking ───────────────────────────────────────────


def coerce_value(raw: str) -> Any:
    """Map shell string to a typed Python value. No validation — shape only.

    Rules (applied in order):
      - "null"            → None
      - integer literal   → int
      - float literal     → float
      - otherwise         → str (raw)

    Bool coercion is intentionally absent: no top-level schema field is bool.
    """
    if raw == "null":
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _extract_source_path(value: str) -> str:
    """Extract the file-path prefix from a runtime_url.source value.

    Accepts both `vite.config.ts` and `vite.config.ts: server.host/port/https`
    forms (the template shows the latter as an annotation-bearing sample).
    The path portion is everything before the first `: ` separator.
    """
    idx = value.find(": ")
    return value[:idx] if idx >= 0 else value


def walk_to_parent(state: dict[str, Any], path: str) -> tuple[dict[str, Any], str]:
    """Walk a dotted path; return (parent_dict, final_key).

    Raises KeyError for unknown intermediate segment, TypeError if an
    intermediate segment resolves to something other than a dict.
    """
    parts = path.split(".")
    cur: Any = state
    for p in parts[:-1]:
        if not isinstance(cur, dict):
            raise TypeError(f"path segment {p!r} parent is not a dict")
        if p not in cur:
            raise KeyError(f"unknown field segment {p!r}")
        cur = cur[p]
    if not isinstance(cur, dict):
        raise TypeError(f"final parent for {path!r} is not a dict")
    return cur, parts[-1]


# ─── CLI handlers ────────────────────────────────────────────────────────────


def cmd_set(args: argparse.Namespace) -> int:
    state = load_state()
    try:
        parent, key = walk_to_parent(state, args.field)
    except (KeyError, TypeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    if key not in parent:
        print(
            f"error: unknown field {args.field!r}. Use `status` to list known fields.",
            file=sys.stderr,
        )
        return 2

    current = parent[key]
    if isinstance(current, list):
        print(
            f"error: field {args.field!r} is a list; use the appropriate add-* "
            f"subcommand instead of `set`.",
            file=sys.stderr,
        )
        return 2

    new_value = coerce_value(args.value)

    if args.field in _ENUMS and new_value is not None:
        allowed = _ENUMS[args.field]
        if new_value not in allowed:
            print(
                f"error: {new_value!r} is not a valid value for {args.field!r}.\n"
                f"  allowed: {', '.join(sorted(allowed))}",
                file=sys.stderr,
            )
            return 2

    if new_value is None and args.field in _NULL_REASON_REQUIRED and args.reason is None:
        print(
            f"error: {args.field!r} cannot be set to null without --reason. "
            f"Null here must document why (e.g. --reason \"backend-only, no web UI\").",
            file=sys.stderr,
        )
        return 2

    if (
        new_value is not None
        and args.field in _LIBRARY_CATEGORY_FIELDS
        and args.evidence is None
    ):
        print(
            f"error: library-category field {args.field!r} cannot be set to a "
            f"non-null value without --evidence. Cite the dep + usage signal "
            f"(e.g. --evidence \"@okta/okta-vue in deps + plugin install\").",
            file=sys.stderr,
        )
        return 2

    if args.field == "runtime_url.source" and isinstance(new_value, str):
        if new_value != "framework-default":
            config_path = _extract_source_path(new_value)
            if not Path(config_path).is_file():
                print(
                    f"error: runtime_url.source {new_value!r} references a file "
                    f"that does not exist (resolved path: {config_path!r}). "
                    f"Use 'framework-default' if no dev-server config was found.",
                    file=sys.stderr,
                )
                return 2

    parent[key] = new_value

    if args.reason is not None:
        reasons = state.setdefault("_reasons", {})
        reasons[args.field] = args.reason

    if args.evidence is not None:
        evidence = state.setdefault("_evidence", {})
        evidence[args.field] = args.evidence

    set_fields = state.setdefault("_set_fields", [])
    if args.field not in set_fields:
        set_fields.append(args.field)

    save_state(state)
    return 0


def _coerce_opt(v: Any) -> Any:
    """Apply coerce_value to an optional arg; passthrough None."""
    return None if v is None else coerce_value(v)


def cmd_add_package(args: argparse.Namespace) -> int:
    pkg_dir = Path(args.path)
    manifest_path = pkg_dir / args.manifest

    if not pkg_dir.is_dir():
        print(
            f"error: --path {args.path!r} is not a directory under the current "
            f"working directory. Run `add-package` from the target project root "
            f"and pass a relative path that exists on disk.",
            file=sys.stderr,
        )
        return 2
    if not manifest_path.is_file():
        print(
            f"error: manifest {str(manifest_path)!r} does not exist. "
            f"Check --path and --manifest point to a real file.",
            file=sys.stderr,
        )
        return 2

    state = load_state()
    entry = {
        "path": args.path,
        "manifest": args.manifest,
        "language_hint": args.language_hint,
        "framework_hint": _coerce_opt(args.framework_hint),
        "build_command": _coerce_opt(args.build_command),
        "type_check_command": _coerce_opt(args.type_check_command),
        "lint_command": _coerce_opt(args.lint_command),
        "test_command": _coerce_opt(args.test_command),
        "command_source": args.command_source,
    }
    state["packages"].append(entry)
    save_state(state)
    return 0


def cmd_add_language(args: argparse.Namespace) -> int:
    state = load_state()
    state["languages"].append(
        {
            "name": args.name,
            "file_count": args.file_count,  # argparse already coerced int
            "runtime": _coerce_opt(args.runtime),
        }
    )
    save_state(state)
    return 0


def cmd_add_framework(args: argparse.Namespace) -> int:
    state = load_state()
    state["frameworks"].append(
        {
            "name": args.name,
            "role": _coerce_opt(args.role),
            "evidence": _coerce_opt(args.evidence),
        }
    )
    save_state(state)
    return 0


def cmd_add_enforcement_tool(args: argparse.Namespace) -> int:
    state = load_state()
    state["enforcement_tooling"].append(args.value)
    save_state(state)
    return 0


def cmd_reset(args: argparse.Namespace) -> int:
    """Delete the state file. Idempotent — no-op if missing.

    Call at the start of any fresh detection run to clear stale state from a
    previous interrupted run. Without this, `add-*` calls would append to
    existing arrays, producing silent duplicates.
    """
    if STATE_FILE.exists():
        STATE_FILE.unlink()
        print(f"cleared stale state at {STATE_FILE}", file=sys.stderr)
    else:
        print("no state file to clear", file=sys.stderr)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = load_state()
    for line in render_status(state):
        print(line)
    return 0


def render_status(state: dict[str, Any]) -> list[str]:
    """Produce one line per top-level field (recursing into nested dicts).

    - Scalar None        → `<path>: UNSET`
    - Scalar set         → `<path>: <value>`
    - List field         → `<path>: N entries`
    - Nested dict        → recurse, prefixing keys with `<path>.`
    - `_reasons` footer  → trailing line if any reasons stashed
    """
    out: list[str] = []
    # Iterate dataclass field order for parity-diff stability.
    for f in _report_field_names():
        if f == "_reasons":
            continue
        out.extend(_render_field(f, state.get(f)))

    reasons = state.get("_reasons")
    if reasons:
        n = len(reasons)
        out.append(f"_reasons: {n} {'entry' if n == 1 else 'entries'}")
    return out


def _report_field_names() -> list[str]:
    from dataclasses import fields as dc_fields

    return [f.name for f in dc_fields(DetectionReport)]


def _render_field(path: str, value: Any) -> list[str]:
    if value is None:
        return [f"{path}: UNSET"]
    if isinstance(value, list):
        n = len(value)
        return [f"{path}: {n} {'entry' if n == 1 else 'entries'}"]
    if isinstance(value, dict):
        lines: list[str] = []
        for sub_key, sub_val in value.items():
            lines.extend(_render_field(f"{path}.{sub_key}", sub_val))
        return lines
    return [f"{path}: {value}"]


def cmd_compose(args: argparse.Namespace) -> int:
    state = load_state()

    missing = _check_required(state)
    if missing:
        print("error: compose refused — required fields unset:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 2

    count_err = _check_package_count(state)
    if count_err:
        print(f"error: {count_err}", file=sys.stderr)
        return 2

    yaml_text = emit_yaml(state)

    DEVFORGE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = OUTPUT_FILE.with_suffix(OUTPUT_FILE.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        f.write(yaml_text)
    os.replace(tmp, OUTPUT_FILE)

    clear_state()
    print(f"wrote {OUTPUT_FILE}")
    return 0


# ─── Required-field check ────────────────────────────────────────────────────


def _check_required(state: dict[str, Any]) -> list[str]:
    """Return a list of missing required paths; empty if all satisfied."""
    missing: list[str] = []
    set_fields = set(state.get("_set_fields", []))
    for path in _REQUIRED_SCALARS:
        if path not in set_fields:
            missing.append(path)
    for path in _REQUIRED_NONEMPTY_LISTS:
        value = state.get(path)
        if not isinstance(value, list) or len(value) == 0:
            missing.append(f"{path} (must have ≥1 entry)")
    return missing


def _check_package_count(state: dict[str, Any]) -> str | None:
    """Finding 23B defense: len(packages) must match the declared manifest_count."""
    declared = state.get("manifest_count")
    packages = state.get("packages") or []
    if not isinstance(declared, int):
        return None  # required-field check handles "not set" already
    actual = len(packages)
    if actual == declared:
        return None
    delta = declared - actual
    if delta > 0:
        action = (
            f"Add the remaining {delta} package(s) via add-package, or correct "
            f"manifest_count."
        )
    else:
        action = (
            f"You added {-delta} more than declared. Correct manifest_count to "
            f"{actual}, or remove the extra package record(s)."
        )
    return (
        f"package count mismatch: manifest_count is {declared} but {actual} "
        f"package record(s) were added. {action} No abbreviation allowed."
    )


# ─── YAML emitter (stdlib only) ──────────────────────────────────────────────
# Produces block-style YAML matching the detect.md template shape.
# Not a general-purpose emitter — handles only what DetectionReport contains:
# scalars (str/int/None), dicts, lists of str, lists of dict with scalar values.

_YAML_RESERVED = {
    "null", "Null", "NULL", "~",
    "true", "True", "TRUE", "false", "False", "FALSE",
    "yes", "Yes", "YES", "no", "No", "NO",
    "on", "On", "ON", "off", "Off", "OFF",
}
_YAML_SPECIAL_CHARS = set(":#{}[],&*!|>'\"%@`")


def emit_yaml(state: dict[str, Any]) -> str:
    """Render the detection_report YAML from a state dict.

    Internal-state keys (any key starting with `_` — `_reasons`, `_evidence`,
    `_set_fields`, etc.) are skipped: they're tracking maps used by validation
    layers, not part of the schema downstream readers consume.
    """
    lines: list[str] = ["detection_report:"]
    for key, value in state.items():
        if key.startswith("_"):
            continue
        if key == "optional" and isinstance(value, dict):
            _emit_optional(key, value, lines, indent=2)
        else:
            _emit_field(key, value, lines, indent=2)
    return "\n".join(lines) + "\n"


def _emit_optional(key: str, value: dict[str, Any], lines: list[str], indent: int) -> None:
    """Flatten OptionalSection.extra into the optional: block to match template."""
    flat: dict[str, Any] = {}
    for k, v in value.items():
        if k == "extra":
            if isinstance(v, dict):
                flat.update(v)  # merge extra contents at optional level
            continue
        flat[k] = v
    lines.append(" " * indent + f"{key}:")
    for k, v in flat.items():
        _emit_field(k, v, lines, indent=indent + 2)


def _emit_field(key: str, value: Any, lines: list[str], indent: int) -> None:
    prefix = " " * indent
    if isinstance(value, dict):
        lines.append(f"{prefix}{key}:")
        for k, v in value.items():
            _emit_field(k, v, lines, indent=indent + 2)
        return
    if isinstance(value, list):
        if not value:
            lines.append(f"{prefix}{key}: []")
            return
        lines.append(f"{prefix}{key}:")
        for item in value:
            _emit_list_item(item, lines, indent=indent + 2)
        return
    lines.append(f"{prefix}{key}: {_yaml_scalar(value)}")


def _emit_list_item(item: Any, lines: list[str], indent: int) -> None:
    prefix = " " * indent
    if isinstance(item, dict):
        first = True
        for k, v in item.items():
            leader = "- " if first else "  "
            first = False
            if isinstance(v, (dict, list)):
                # Not expected in current schema, but emit gracefully.
                lines.append(f"{prefix}{leader}{k}:")
                if isinstance(v, dict):
                    for sk, sv in v.items():
                        _emit_field(sk, sv, lines, indent=indent + 4)
                else:
                    for sub in v:
                        _emit_list_item(sub, lines, indent=indent + 4)
            else:
                lines.append(f"{prefix}{leader}{k}: {_yaml_scalar(v)}")
        return
    lines.append(f"{prefix}- {_yaml_scalar(item)}")


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return _yaml_str(value)
    return _yaml_str(str(value))


def _yaml_str(s: str) -> str:
    """Emit a YAML-safe scalar string, double-quoting when necessary."""
    if s == "":
        return '""'
    if s in _YAML_RESERVED:
        return f'"{s}"'
    # Numeric-looking strings must be quoted to avoid type coercion by readers.
    try:
        int(s)
        return f'"{s}"'
    except ValueError:
        pass
    try:
        float(s)
        return f'"{s}"'
    except ValueError:
        pass
    needs_quote = (
        s != s.strip()
        or any(c in _YAML_SPECIAL_CHARS for c in s)
        or s[0] in "-?"
    )
    if needs_quote:
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return s


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="detect_report",
        description="Compose the Phase 1 Detection Report for setup-wizard.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_set = sub.add_parser("set", help="Set a single Detection Report field.")
    p_set.add_argument("field", help="Field name (supports dotted paths, e.g. runtime_url.source).")
    p_set.add_argument("--value", required=True, help="Value to set.")
    p_set.add_argument("--reason", help="Required when value is null for null-allowed fields.")
    p_set.add_argument("--evidence", help="Required for library-category fields set to non-null.")
    p_set.set_defaults(func=cmd_set)

    p_add = sub.add_parser("add-package", help="Append one package record to packages[].")
    p_add.add_argument("--path", required=True)
    p_add.add_argument("--manifest", required=True)
    p_add.add_argument("--language-hint", required=True)
    p_add.add_argument("--framework-hint")
    p_add.add_argument("--build-command")
    p_add.add_argument("--type-check-command")
    p_add.add_argument("--lint-command")
    p_add.add_argument("--test-command")
    p_add.add_argument("--command-source", choices=["manifest", "fallback"], required=True)
    p_add.set_defaults(func=cmd_add_package)

    p_lang = sub.add_parser("add-language", help="Append one entry to languages[].")
    p_lang.add_argument("--name", required=True)
    p_lang.add_argument("--file-count", type=int, default=0)
    p_lang.add_argument("--runtime")
    p_lang.set_defaults(func=cmd_add_language)

    p_fw = sub.add_parser("add-framework", help="Append one entry to frameworks[].")
    p_fw.add_argument("--name", required=True)
    p_fw.add_argument("--role", choices=_FRAMEWORK_ROLES)
    p_fw.add_argument("--evidence")
    p_fw.set_defaults(func=cmd_add_framework)

    p_tool = sub.add_parser(
        "add-enforcement-tool", help="Append one string to enforcement_tooling[]."
    )
    p_tool.add_argument("--value", required=True)
    p_tool.set_defaults(func=cmd_add_enforcement_tool)

    p_reset = sub.add_parser("reset", help="Delete state file. Call at run start to clear stale state from a previous interrupted run.")
    p_reset.set_defaults(func=cmd_reset)

    p_status = sub.add_parser("status", help="Show which fields are set/unset.")
    p_status.set_defaults(func=cmd_status)

    p_compose = sub.add_parser(
        "compose",
        help="Validate and emit .devforge/detection_report.yaml; clears state on success.",
    )
    p_compose.set_defaults(func=cmd_compose)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
