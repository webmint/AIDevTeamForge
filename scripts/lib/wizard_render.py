#!/usr/bin/env python3
"""Wizard Render composer for setup-wizard Phase 3 + Phase 4.

The setup-wizard LLM calls this tool once per rendered value (`set`,
`set-render`, `add-*`), records per-agent substitutions (`apply-agents`),
checks progress (`status`), and writes all populated files atomically
(`compose`).

The helper owns file shape: paths, frontmatter, placeholder substitution,
sentinel preservation, validation. The LLM owns values: prose composition,
per-stack rendering, multi-line content. This mirrors the detect_report
pattern (set field --value X → compose).

Stdlib only. No third-party dependencies. Target Python: 3.8+.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


# ─── Paths ───────────────────────────────────────────────────────────────────

DEVFORGE_DIR = Path(".devforge")
STATE_FILE = DEVFORGE_DIR / ".wizard-render-state.json"
DETECTION_REPORT = DEVFORGE_DIR / "detection_report.yaml"
PROJECT_CONFIG = DEVFORGE_DIR / "project-config.json"
MEMORY_FILE = DEVFORGE_DIR / "memory.md"
BASELINE_DIR = DEVFORGE_DIR / "baseline"
AGENT_BASELINE_DIR = BASELINE_DIR / "agents"
AGENTS_DIR = Path(".claude/agents")
SETTINGS_FILE = Path(".claude/settings.json")
MCP_FILE = Path(".mcp.json")

# Templates / target docs (read + written in place)
CLAUDE_MD = Path("CLAUDE.md")
CONSTITUTION_MD = Path("constitution.md")
DOCS_OVERVIEW = Path("docs/overview.md")
DOCS_ARCHITECTURE = Path("docs/architecture.md")

# Drift-risk literal — kept in sync with populate.md "Drift-risk literals"
CHROME_DEVTOOLS_MCP_PACKAGE = "chrome-devtools-mcp"

# Sentinel for the memory.md insertion point
MEMORY_SENTINEL = "<!-- Populated during constitute"


# ─── Schema ──────────────────────────────────────────────────────────────────


@dataclass
class ClaudeTiers:
    think: str | None = None  # opus | sonnet | haiku
    do: str | None = None
    verify: str | None = None


@dataclass
class WizardRenderState:
    # Phase 2 direct-value answers
    project_name: str | None = None
    project_description: str | None = None
    project_type: str | None = None
    workflow_enforcement: str | None = None  # strict | moderate | light
    ai_attribution: str | None = None  # yes | no

    claude_tiers: ClaudeTiers = field(default_factory=ClaudeTiers)

    # Per-stack arrays (post-Q3 truth — may differ from detection_report).
    # All parallel-indexed by language. Helper derives FRAMEWORK / LANGUAGE /
    # ARCHITECTURE / ERROR_HANDLING / API_LAYER / TESTING / BUILD_TOOL /
    # BUILD_COMMAND / TYPE_CHECK_COMMAND / LINT_COMMAND for both CLAUDE.md
    # and agent files from these arrays — LLM never re-emits the rendered form.
    languages: list[str] = field(default_factory=list)
    frameworks: list[str | None] = field(default_factory=list)
    architectures: list[str] = field(default_factory=list)
    error_handlings: list[str] = field(default_factory=list)
    api_layers: list[str] = field(default_factory=list)
    testings: list[str] = field(default_factory=list)
    build_tools: list[str | None] = field(default_factory=list)
    build_commands: list[str | None] = field(default_factory=list)
    type_check_commands: list[str | None] = field(default_factory=list)
    lint_commands: list[str | None] = field(default_factory=list)

    # AC verification
    ac_modes: list[str] = field(default_factory=list)
    ac_runtime_url: str | None = None
    ac_runtime_api_base: str | None = None
    ac_runtime_cli_command: str | None = None

    # LLM-composed multi-line renders for CLAUDE.md placeholders that
    # genuinely need composition (tree saliency, monorepo collapse, etc.) —
    # not derivable mechanically from per-stack arrays.
    project_structure: str | None = None
    dev_commands: str | None = None
    architecture_details: str | None = None
    package_stacks_section: str | None = None  # may be empty string for ≤1 packages

    # Memory.md seed prose (LLM-composed; includes any "Other observations" bullet)
    memory_seed: str | None = None

    # Phase 4 agent decisions (set via apply-agents)
    agents_kept: dict[str, dict[str, Any]] = field(default_factory=dict)
    # shape: { agent_name: { "tier": "think|do|verify", "substitutions": {KEY: VALUE, ...} } }
    agents_removed: list[str] = field(default_factory=list)


# ─── Validation tables ───────────────────────────────────────────────────────

_TIERS = {"think", "do", "verify"}
_TIER_VALUES = {"opus", "sonnet", "haiku"}
_AC_MODES = {"code-only", "tests", "runtime-assisted", "off"}
_WORKFLOW = {"strict", "moderate", "light"}
_ATTRIBUTION = {"yes", "no"}

_SCALAR_FIELDS: dict[str, set[str] | None] = {
    "project_name": None,
    "project_description": None,
    "project_type": None,
    "workflow_enforcement": _WORKFLOW,
    "ai_attribution": _ATTRIBUTION,
    "ac_runtime_url": None,
    "ac_runtime_api_base": None,
    "ac_runtime_cli_command": None,
}

_RENDER_FIELDS: tuple[str, ...] = (
    "project_structure",
    "dev_commands",
    "architecture_details",
    "package_stacks_section",
    "memory_seed",
)

# Required-for-compose: scalars and renders that downstream files depend on.
# project-config.json + CLAUDE.md substitution will fail without these.
_REQUIRED_SCALARS: tuple[str, ...] = (
    "project_name",
    "project_description",
    "project_type",
    "workflow_enforcement",
    "ai_attribution",
)
_REQUIRED_RENDERS: tuple[str, ...] = (
    "project_structure",
    "dev_commands",
    "architecture_details",
    "memory_seed",
)


# ─── State RW ────────────────────────────────────────────────────────────────


def default_state() -> dict[str, Any]:
    return asdict(WizardRenderState())


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return default_state()
    with STATE_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state: dict[str, Any]) -> None:
    DEVFORGE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(STATE_FILE.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=False)
        f.write("\n")
    os.replace(tmp, STATE_FILE)


def clear_state() -> None:
    if STATE_FILE.exists():
        STATE_FILE.unlink()


# ─── Detection Report read ───────────────────────────────────────────────────
# Compose reads detection_report.yaml directly for SOURCE_ROOT / WORKSPACE_MODE
# (single source of truth — LLM doesn't re-emit detection facts).


def read_detection_report() -> dict[str, Any]:
    """Tiny YAML parser for detection_report.yaml's flat shape.

    The Report uses a small subset of YAML: scalars, nested dotted keys,
    and lists of dicts. We don't pull in pyyaml — stdlib only. Parser
    handles the shapes detect_report emits; reject anything unexpected.
    """
    if not DETECTION_REPORT.exists():
        die(
            f"detection report not found at {DETECTION_REPORT}. "
            f"Run Phase 1 (`scripts/lib/detect_report compose`) first."
        )
    text = DETECTION_REPORT.read_text(encoding="utf-8")
    return _parse_yaml_subset(text)


def _parse_yaml_subset(text: str) -> dict[str, Any]:
    """Parse the YAML shapes detect_report emits.

    Supports: top-level scalars, nested dicts via indentation, lists of
    dicts (`- key: value`). String quoting via double-quotes. Integers
    parsed as int. `null` / empty → None. Comments (`#`) and blank lines
    skipped.
    """
    result: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, result)]  # (indent, container)
    pending_list_item: dict[str, Any] | None = None

    for raw_line in text.splitlines():
        # Strip trailing comment + whitespace; preserve indent
        stripped_no_indent = raw_line.lstrip(" ")
        if not stripped_no_indent or stripped_no_indent.startswith("#"):
            continue
        indent = len(raw_line) - len(stripped_no_indent)
        line = stripped_no_indent.rstrip()
        if "#" in line:
            # remove inline comment that's NOT inside quotes (simplified)
            in_q = False
            for i, ch in enumerate(line):
                if ch == '"':
                    in_q = not in_q
                elif ch == "#" and not in_q:
                    line = line[:i].rstrip()
                    break

        # Pop stack until current indent fits
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent_indent, parent = stack[-1] if stack else (-1, result)

        if line.startswith("- "):
            # List item — start of a new dict in a list
            container = parent
            if not isinstance(container, list):
                # The previous key declared an empty list parent; skip
                continue
            # Parse the inline first key=value of the list item
            inline = line[2:]
            item: dict[str, Any] = {}
            container.append(item)
            pending_list_item = item
            if ":" in inline:
                k, _, v = inline.partition(":")
                item[k.strip()] = _coerce_yaml_scalar(v.strip())
            stack.append((indent, item))
            continue

        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        target = parent if isinstance(parent, dict) else pending_list_item
        if target is None:
            continue

        if value == "":
            # Nested container — peek next non-blank line to decide list vs dict
            # We use a heuristic: assume dict; switch to list when first child is `- `
            target[key] = {}
            stack.append((indent, target[key]))
        elif value == "[]":
            target[key] = []
        elif value == "{}":
            target[key] = {}
        else:
            target[key] = _coerce_yaml_scalar(value)

    # Repair: any container that received only list items should be a list
    return _post_process_lists(result)


def _coerce_yaml_scalar(value: str) -> Any:
    if value == "" or value == "null" or value == "~":
        return None
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value == "true":
        return True
    if value == "false":
        return False
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        pass
    return value


def _post_process_lists(node: Any) -> Any:
    """Walk the parsed tree; convert dicts that ended up holding list-items into lists."""
    if isinstance(node, dict):
        for k in list(node.keys()):
            child = node[k]
            if isinstance(child, dict) and child and all(isinstance(v, dict) for v in child.values()):
                # Heuristic check: if every value has the same keys AND was set via `- key:` dispatch,
                # this might be a list. Skip — our parser handles list-vs-dict at parse time when
                # `- ` prefix is present. Leave as-is.
                pass
            node[k] = _post_process_lists(child)
        return node
    if isinstance(node, list):
        return [_post_process_lists(item) for item in node]
    return node


# ─── Substitution engine ─────────────────────────────────────────────────────


PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")


def apply_substitutions(text: str, subs: dict[str, str]) -> tuple[str, list[str]]:
    """Replace every `{{KEY}}` in text with subs[KEY].

    Returns (substituted_text, unresolved_keys).
    Unresolved = `{{KEY}}` markers that had no entry in subs.
    """
    unresolved: list[str] = []

    def repl(m: re.Match[str]) -> str:
        key = m.group(1)
        if key in subs:
            return subs[key]
        unresolved.append(key)
        return m.group(0)

    out = PLACEHOLDER_RE.sub(repl, text)
    return out, unresolved


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)


# ─── Output helpers ──────────────────────────────────────────────────────────


def info(msg: str) -> None:
    print(msg, file=sys.stderr)


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(2)


# ─── Subcommand handlers ─────────────────────────────────────────────────────


def cmd_set(args: argparse.Namespace) -> int:
    field_name = args.field
    if field_name not in _SCALAR_FIELDS:
        die(f"unknown scalar field {field_name!r}. Valid: {sorted(_SCALAR_FIELDS)}")
    enum = _SCALAR_FIELDS[field_name]
    value = args.value
    if enum is not None and value not in enum:
        die(f"{field_name}={value!r} not in {sorted(enum)}")
    state = load_state()
    state[field_name] = value
    save_state(state)
    return 0


def cmd_set_tier(args: argparse.Namespace) -> int:
    if args.tier not in _TIERS:
        die(f"tier must be one of {sorted(_TIERS)}, got {args.tier!r}")
    if args.value not in _TIER_VALUES:
        die(f"tier value must be one of {sorted(_TIER_VALUES)}, got {args.value!r}")
    state = load_state()
    state["claude_tiers"][args.tier] = args.value
    save_state(state)
    return 0


def cmd_set_render(args: argparse.Namespace) -> int:
    field_name = args.field
    if field_name not in _RENDER_FIELDS:
        die(f"unknown render field {field_name!r}. Valid: {sorted(_RENDER_FIELDS)}")
    if args.stdin:
        value = sys.stdin.read()
    elif args.value is not None:
        value = args.value
    else:
        die("set-render requires either --value or --stdin")
    state = load_state()
    state[field_name] = value
    save_state(state)
    return 0


def cmd_add_language(args: argparse.Namespace) -> int:
    state = load_state()
    state["languages"].append(args.name)
    state["frameworks"].append(args.framework)  # may be None
    save_state(state)
    return 0


def cmd_add_ac_mode(args: argparse.Namespace) -> int:
    if args.value not in _AC_MODES:
        die(f"ac mode must be one of {sorted(_AC_MODES)}, got {args.value!r}")
    state = load_state()
    if args.value in state["ac_modes"]:
        return 0  # idempotent
    state["ac_modes"].append(args.value)
    save_state(state)
    return 0


def _make_per_stack_adder(field_name: str):
    def cmd(args: argparse.Namespace) -> int:
        state = load_state()
        state[field_name].append(args.value)
        save_state(state)
        return 0
    return cmd


cmd_add_architecture = _make_per_stack_adder("architectures")
cmd_add_error_handling = _make_per_stack_adder("error_handlings")
cmd_add_api_layer = _make_per_stack_adder("api_layers")
cmd_add_testing = _make_per_stack_adder("testings")
cmd_add_build_tool = _make_per_stack_adder("build_tools")
cmd_add_build_command = _make_per_stack_adder("build_commands")
cmd_add_type_check_command = _make_per_stack_adder("type_check_commands")
cmd_add_lint_command = _make_per_stack_adder("lint_commands")


def cmd_apply_agents(args: argparse.Namespace) -> int:
    """Record kept + removed agent decisions and per-agent substitutions.

    Reads a JSON file with shape:
      {
        "kept": {
          "<agent-name>": {
            "tier": "think|do|verify",
            "substitutions": { "PLACEHOLDER": "value", ... }
          },
          ...
        },
        "removed": ["agent-name", ...]
      }
    """
    path = Path(args.substitutions_file)
    if not path.exists():
        die(f"substitutions file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"failed to parse {path}: {e}")

    if not isinstance(data, dict) or "kept" not in data or "removed" not in data:
        die(f"substitutions file must have top-level 'kept' (dict) and 'removed' (list)")

    kept = data["kept"]
    removed = data["removed"]

    if not isinstance(kept, dict):
        die("'kept' must be a dict of agent-name → {tier, substitutions}")
    if not isinstance(removed, list):
        die("'removed' must be a list of agent names")

    # Validate kept entries
    for name, entry in kept.items():
        if not isinstance(entry, dict):
            die(f"kept[{name!r}] must be a dict with 'tier' (and optional 'substitutions')")
        tier = entry.get("tier")
        if tier not in _TIERS:
            die(f"kept[{name!r}].tier must be one of {sorted(_TIERS)}, got {tier!r}")
        # 'substitutions' is optional — helper derives all known placeholders
        # automatically. Only pass substitutions for placeholders the helper
        # doesn't know how to derive (rare; flag for review).
        subs = entry.get("substitutions")
        if subs is not None and not isinstance(subs, dict):
            die(f"kept[{name!r}].substitutions, when present, must be a dict")

    # Validate removed list
    for name in removed:
        if not isinstance(name, str):
            die(f"removed entries must be strings, got {name!r}")

    # Cross-check: no agent in both kept and removed
    overlap = set(kept) & set(removed)
    if overlap:
        die(f"agents in both kept and removed: {sorted(overlap)}")

    state = load_state()
    state["agents_kept"] = kept
    state["agents_removed"] = removed
    save_state(state)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    state = load_state()
    print("== Wizard Render state ==\n")

    print("Scalars:")
    for f in _SCALAR_FIELDS:
        v = state.get(f)
        marker = "✓" if v is not None else "·"
        print(f"  {marker} {f}: {v!r}")

    print("\nClaude tiers:")
    tiers = state.get("claude_tiers", {})
    for t in ("think", "do", "verify"):
        v = tiers.get(t)
        marker = "✓" if v is not None else "·"
        print(f"  {marker} claude_tiers.{t}: {v!r}")

    print("\nPer-stack arrays:")
    for f in (
        "languages", "frameworks", "architectures", "error_handlings",
        "api_layers", "testings", "build_tools", "build_commands",
        "type_check_commands", "lint_commands",
    ):
        v = state.get(f, [])
        print(f"  · {f}: {v}")

    print("\nAC verification:")
    print(f"  · ac_modes: {state.get('ac_modes', [])}")
    for f in ("ac_runtime_url", "ac_runtime_api_base", "ac_runtime_cli_command"):
        v = state.get(f)
        print(f"  · {f}: {v!r}")

    print("\nRenders:")
    for f in _RENDER_FIELDS:
        v = state.get(f)
        marker = "✓" if v is not None else "·"
        preview = ""
        if isinstance(v, str):
            preview = v.replace("\n", "↵")[:60]
            if len(v) > 60:
                preview += "..."
        print(f"  {marker} {f}: {preview!r}")

    print("\nAgents:")
    print(f"  kept: {sorted(state.get('agents_kept', {}).keys())}")
    print(f"  removed: {sorted(state.get('agents_removed', []))}")

    print("\nValidation (compose readiness):")
    issues = validate_for_compose(state)
    if not issues:
        print("  ✓ ready to compose")
    else:
        for i in issues:
            print(f"  ✗ {i}")
    return 0


def validate_for_compose(state: dict[str, Any]) -> list[str]:
    issues: list[str] = []

    for f in _REQUIRED_SCALARS:
        if state.get(f) is None:
            issues.append(f"required scalar unset: {f}")

    for f in _REQUIRED_RENDERS:
        v = state.get(f)
        if v is None:
            issues.append(f"required render unset: {f}")

    tiers = state.get("claude_tiers", {})
    for t in ("think", "do", "verify"):
        if tiers.get(t) is None:
            issues.append(f"required tier unset: claude_tiers.{t}")

    if not state.get("languages"):
        issues.append("languages array is empty")

    if len(state.get("languages", [])) != len(state.get("frameworks", [])):
        issues.append("languages and frameworks arrays must be parallel (same length)")

    if not state.get("ac_modes"):
        issues.append("ac_modes array is empty (must have ≥1 mode)")
    elif "off" in state.get("ac_modes", []) and len(state.get("ac_modes", [])) > 1:
        issues.append("ac_modes contains 'off' alongside other modes — 'off' is exclusive")

    if not state.get("agents_kept"):
        issues.append("agents_kept is empty — Phase 4 must apply at least the always-keep set")

    return issues


# ─── Compose ─────────────────────────────────────────────────────────────────


def cmd_compose(args: argparse.Namespace) -> int:
    state = load_state()

    issues = validate_for_compose(state)
    if issues:
        info("compose blocked — fix these and re-run:")
        for i in issues:
            info(f"  ✗ {i}")
        return 2

    report = read_detection_report()
    source_root = report.get("source_root") or "."
    workspace_mode = report.get("workspace_mode") or "standalone"
    packages = report.get("packages") or []

    written: list[str] = []
    skipped: list[str] = []

    # 5.1 — CLAUDE.md substitution
    if CLAUDE_MD.exists():
        subs = compose_claude_md_subs(state, source_root, workspace_mode, packages, report)
        text = CLAUDE_MD.read_text(encoding="utf-8")
        out, unresolved = apply_substitutions(text, subs)
        if unresolved:
            die(f"CLAUDE.md has unresolved placeholders: {sorted(set(unresolved))}")
        write_atomic(CLAUDE_MD, out)
        written.append(str(CLAUDE_MD))
    else:
        skipped.append(str(CLAUDE_MD))

    # 5.3 — baseline copies
    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    for src in (CLAUDE_MD, CONSTITUTION_MD):
        if src.exists():
            dst = BASELINE_DIR / src.name
            shutil.copy2(src, dst)
            written.append(str(dst))
    docs_baseline = BASELINE_DIR / "docs"
    docs_baseline.mkdir(parents=True, exist_ok=True)
    for src in (DOCS_OVERVIEW, DOCS_ARCHITECTURE):
        if src.exists():
            dst = docs_baseline / src.name
            shutil.copy2(src, dst)
            written.append(str(dst))

    # 5.4 — chrome-devtools MCP entries (conditional)
    if state.get("ac_runtime_url"):
        if MCP_FILE.exists():
            inject_chrome_devtools_mcp(MCP_FILE)
            written.append(str(MCP_FILE))
        if SETTINGS_FILE.exists():
            append_chrome_devtools_permissions(SETTINGS_FILE)
            written.append(str(SETTINGS_FILE))

    # 5.5 — project-config.json
    if PROJECT_CONFIG.exists():
        write_project_config(state, source_root, workspace_mode, packages)
        written.append(str(PROJECT_CONFIG))
    else:
        skipped.append(str(PROJECT_CONFIG))

    # 5.6 — memory.md seed insertion
    if MEMORY_FILE.exists() and state.get("memory_seed"):
        insert_memory_seed(MEMORY_FILE, state["memory_seed"])
        written.append(str(MEMORY_FILE))

    # 5.7 — constitution.md header
    if CONSTITUTION_MD.exists():
        text = CONSTITUTION_MD.read_text(encoding="utf-8")
        text = strip_authoring_blockquotes(text)
        subs = compose_constitution_subs(state, report)
        out, unresolved = apply_substitutions(text, subs)
        # Body-section sentinels (`_Run /constitute to populate_`) are not placeholders;
        # only header-level {{...}} markers should remain unresolved (none expected).
        if unresolved:
            die(f"constitution.md has unresolved header placeholders: {sorted(set(unresolved))}")
        write_atomic(CONSTITUTION_MD, out)
        written.append(str(CONSTITUTION_MD))

    # 5.8 — docs files
    for path in (DOCS_OVERVIEW, DOCS_ARCHITECTURE):
        if path.exists():
            text = path.read_text(encoding="utf-8")
            subs = {
                "PROJECT_NAME": state["project_name"],
                "PROJECT_DESCRIPTION": state.get("project_description") or "",
            }
            out, unresolved = apply_substitutions(text, subs)
            if unresolved:
                die(f"{path} has unresolved placeholders: {sorted(set(unresolved))}")
            write_atomic(path, out)
            written.append(str(path))

    # 6.3 — remove rejected agents
    for name in state.get("agents_removed", []):
        path = AGENTS_DIR / f"{name}.md"
        if path.exists():
            path.unlink()
            written.append(f"deleted: {path}")

    # 6.4 — apply per-agent substitutions (helper-derived) + model: regex.
    # Scan each kept agent's template for {{KEY}} markers; derive each via the
    # registry. LLM-supplied 'substitutions' (optional in apply-agents JSON)
    # override derived values for keys the LLM explicitly set.
    AGENT_BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    agent_descriptions: dict[str, str] = {}
    for name, entry in state.get("agents_kept", {}).items():
        path = AGENTS_DIR / f"{name}.md"
        if not path.exists():
            skipped.append(str(path))
            continue
        text = path.read_text(encoding="utf-8")
        # Discover every {{KEY}} marker in the template
        keys_in_template = sorted(set(PLACEHOLDER_RE.findall(text)))
        # Build subs: derive each known key, allow LLM-supplied overrides
        llm_subs = entry.get("substitutions") or {}
        subs: dict[str, str] = {}
        unknown: list[str] = []
        for key in keys_in_template:
            if key in llm_subs:
                subs[key] = llm_subs[key]
                continue
            v = derive_placeholder(key, state, report, agent_name=name)
            if v is not None:
                subs[key] = v
            else:
                unknown.append(key)
        if unknown:
            die(
                f"{path} contains placeholders the helper can't derive and that "
                f"apply-agents didn't supply: {unknown}. Either add a deriver in "
                f"wizard_render.py or pass them in apply-agents substitutions."
            )
        out, unresolved = apply_substitutions(text, subs)
        if unresolved:
            die(f"{path} has unresolved placeholders: {sorted(set(unresolved))}")
        # Replace model: line in YAML frontmatter
        out = replace_model_line(out, resolve_tier_value(state, entry["tier"]))
        write_atomic(path, out)
        written.append(str(path))
        # 6.5 — agent baseline
        shutil.copy2(path, AGENT_BASELINE_DIR / f"{name}.md")
        # Capture description for AGENT_LIST rendering
        desc = parse_agent_description(out)
        agent_descriptions[name] = desc

    # 6.6 — AGENT_LIST swap-back into CLAUDE.md
    if CLAUDE_MD.exists() and agent_descriptions:
        agent_list_md = render_agent_list(state, agent_descriptions)
        text = CLAUDE_MD.read_text(encoding="utf-8")
        if "(pending Phase 4 curation)" in text:
            text = text.replace("(pending Phase 4 curation)", agent_list_md)
            write_atomic(CLAUDE_MD, text)

    # Write setup-complete marker
    write_setup_complete(written)

    # Summary
    info("compose succeeded.")
    info(f"  files written: {len(written)}")
    if skipped:
        info(f"  files skipped (not present): {len(skipped)}")
        for s in skipped:
            info(f"    · {s}")

    clear_state()
    return 0


# ─── Compose helpers ─────────────────────────────────────────────────────────


# ─── Derivation registry ─────────────────────────────────────────────────────
# Helper auto-derives substitutions for known placeholders from per-stack arrays
# in state + detection_report. Architect-vs-others rendering rules are encoded
# here in one place — agent templates and CLAUDE.md alike pull from this.

# Map of placeholder name → state field carrying the per-stack array
_STACK_ARRAY_FIELD: dict[str, str] = {
    "ARCHITECTURE": "architectures",
    "ERROR_HANDLING": "error_handlings",
    "API_LAYER": "api_layers",
    "TESTING": "testings",
    "BUILD_TOOL": "build_tools",
    "BUILD_COMMAND": "build_commands",
    "TYPE_CHECK_COMMAND": "type_check_commands",
    "LINT_COMMAND": "lint_commands",
}


def _join_non_null(values: list[Any]) -> str:
    parts = [str(v) for v in values if v is not None]
    return ", ".join(parts) if parts else "N/A"


def _primary(values: list[Any]) -> str:
    if not values:
        return "N/A"
    v = values[0]
    return str(v) if v is not None else "N/A"


def _paired(
    values: list[Any],
    languages: list[str],
    frameworks: list[str | None],
    *,
    with_framework_label: bool,
    skip_values: tuple[str, ...] = ("N/A", "TBD"),
) -> str:
    """Multi-stack paired rendering. Skips None and skip_values entries."""
    pairs: list[str] = []
    for i, v in enumerate(values):
        if v is None or (isinstance(v, str) and v in skip_values):
            continue
        lang = languages[i] if i < len(languages) else "?"
        fw = frameworks[i] if i < len(frameworks) else None
        if with_framework_label and fw:
            label = f"{lang}/{fw}"
        else:
            label = lang
        pairs.append(f"{v} ({label})")
    return ", ".join(pairs) if pairs else "N/A"


def derive_placeholder(
    key: str,
    state: dict[str, Any],
    report: dict[str, Any],
    *,
    agent_name: str | None = None,
) -> str | None:
    """Derive a substitution value for the named placeholder.

    agent_name=None → CLAUDE.md context (joined-comma for FRAMEWORK/LANGUAGE,
    paired-with-(lang)-label for stack-aware multi-stack).
    agent_name='architect' + multi-stack → joined-comma + paired-with-(lang/fw).
    Other agents → primary-only.

    Returns None for unknown keys; caller decides whether to error or fall through.
    """
    languages = state.get("languages", [])
    frameworks = state.get("frameworks", [])
    is_multi = len(languages) > 1
    is_architect_paired = agent_name == "architect" and is_multi
    is_claude_md = agent_name is None

    # FRAMEWORK / LANGUAGE: joined-comma for CLAUDE.md and architect-multi; primary-only for other agents.
    if key == "FRAMEWORK":
        if is_claude_md or is_architect_paired:
            return _join_non_null(frameworks)
        return _primary(frameworks)
    if key == "LANGUAGE":
        if is_claude_md or is_architect_paired:
            return _join_non_null(languages)
        return _primary(languages)

    # 8 stack-aware placeholders (ARCHITECTURE / ERROR_HANDLING / API_LAYER / TESTING /
    # BUILD_TOOL / BUILD_COMMAND / TYPE_CHECK_COMMAND / LINT_COMMAND).
    if key in _STACK_ARRAY_FIELD:
        values = state.get(_STACK_ARRAY_FIELD[key], [])
        if is_multi:
            # CLAUDE.md → paired with (lang) label; architect → paired with (lang/fw) label.
            if is_claude_md:
                return _paired(values, languages, frameworks, with_framework_label=False)
            if is_architect_paired:
                return _paired(values, languages, frameworks, with_framework_label=True)
            return _primary(values)
        # Single-stack: same value for everyone.
        return _primary(values)

    # Detection-only placeholders (only used by certain agents)
    if key == "STYLING":
        v = report.get("styling")
        return str(v) if v is not None else "N/A"
    if key == "STATE_MANAGEMENT":
        v = report.get("state_management")
        return str(v) if v is not None else "N/A"
    if key == "PROJECT_PATHS":
        packages = report.get("packages") or []
        if not packages:
            source_root = report.get("source_root") or "."
            return f"- `{source_root}/`"
        return "\n".join(f"- `{p.get('path', '?')}/`" for p in packages)

    return None


# ─── Compose helpers ─────────────────────────────────────────────────────────


def compose_claude_md_subs(
    state: dict[str, Any],
    source_root: str,
    workspace_mode: str,
    packages: list[Any],
    report: dict[str, Any],
) -> dict[str, str]:
    wrapper_section = render_wrapper_mode_section(workspace_mode, source_root)
    commit_attribution = render_commit_attribution(state["ai_attribution"])
    package_stacks = state.get("package_stacks_section") or ""
    if not package_stacks and len(packages) >= 2:
        info(f"warn: {len(packages)} packages detected but no package_stacks_section render set")
    subs: dict[str, str] = {
        "PROJECT_DESCRIPTION": state["project_description"],
        "PROJECT_NAME": state["project_name"],
        "PROJECT_TYPE": state["project_type"],
        "SOURCE_ROOT": source_root,
        "WRAPPER_MODE_SECTION": wrapper_section,
        "PROJECT_STRUCTURE": state["project_structure"],
        "DEV_COMMANDS": state["dev_commands"],
        "ARCHITECTURE_DETAILS": state["architecture_details"],
        "PACKAGE_STACKS_SECTION": package_stacks,
        "AGENT_LIST": "(pending Phase 4 curation)",
        "COMMIT_ATTRIBUTION": commit_attribution,
    }
    # Derive the 6 stack-aware placeholders for CLAUDE.md context
    for key in ("FRAMEWORK", "LANGUAGE", "BUILD_TOOL", "BUILD_COMMAND",
                "TYPE_CHECK_COMMAND", "LINT_COMMAND"):
        v = derive_placeholder(key, state, report)
        if v is not None:
            subs[key] = v
    return subs


def compose_constitution_subs(state: dict[str, Any], report: dict[str, Any]) -> dict[str, str]:
    from datetime import date
    today = date.today().isoformat()
    return {
        "PROJECT_NAME": state["project_name"],
        "DATE": today,
        "PROJECT_TYPE": state["project_type"],
        "FRAMEWORK": derive_placeholder("FRAMEWORK", state, report) or "N/A",
        "LANGUAGE": derive_placeholder("LANGUAGE", state, report) or "N/A",
        "WORKSPACE_MODE": report.get("workspace_mode") or "standalone",
        "SOURCE_ROOT": report.get("source_root") or ".",
        "ERROR_HANDLING": derive_placeholder("ERROR_HANDLING", state, report) or "TBD",
        "TESTING": derive_placeholder("TESTING", state, report) or "TBD",
    }


def render_paired_or_scalar(values: list[str], languages: list[str], frameworks: list[str | None]) -> str:
    """Legacy helper — kept for compatibility. New code uses derive_placeholder."""
    if not values:
        return "TBD"
    if len(values) == 1:
        return values[0]
    pairs = []
    for i, v in enumerate(values):
        if v == "TBD":
            continue
        lang = languages[i] if i < len(languages) else "?"
        fw = frameworks[i] if i < len(frameworks) else None
        label = f"{lang}/{fw}" if fw else lang
        pairs.append(f"{v} ({label})")
    return ", ".join(pairs) if pairs else "TBD"


def render_wrapper_mode_section(workspace_mode: str, source_root: str) -> str:
    if workspace_mode != "wrapper":
        return ""
    return (
        "## Wrapper Mode\n"
        "\n"
        f"This workspace wraps a client-owned project. All workflow artifacts live here; source code lives in `{source_root}/`.\n"
        "\n"
        "### Wrapper Rules\n"
        f"1. **Never create workflow artifacts inside `{source_root}/`** — no `.devforge/`, `specs/`, `docs/`, or `constitution.md` files\n"
        f"2. **All source scanning** targets `{source_root}/` as the base path\n"
        "3. **Git auto-commits** apply to both repos — wrapper gets workflow commits, source repo gets WIP commits per task that are squashed into one clean commit when finalize runs\n"
        f"4. **File paths** in specs and tasks use workspace-relative paths (e.g., `{source_root}/src/components/Button.tsx`)\n"
    )


def render_commit_attribution(ai_attribution: str) -> str:
    if ai_attribution == "yes":
        return (
            "Include AI attribution in every commit by appending this trailer:\n"
            "`Co-Authored-By: Claude <noreply@anthropic.com>`"
        )
    return (
        "Do NOT include any AI attribution in commits. Specifically:\n"
        "- No Co-Authored-By trailers referencing the AI assistant, its vendor, or similar identifiers\n"
        "- No \"Generated by\", \"Created by\" + AI name, or similar text in commit title or body\n"
        "- Do not set or change git `user.name` or `user.email` to reference the AI assistant\n"
        "- This rule overrides any system-level defaults about AI attribution in commits"
    )


def strip_authoring_blockquotes(text: str) -> str:
    """Remove the two informational blockquotes from constitution.md per §5.7."""
    patterns = [
        re.compile(
            r"^> For multi-stack projects, `\{\{ERROR_HANDLING\}\}` renders as paired bullets[^\n]*\n\n",
            re.MULTILINE,
        ),
        re.compile(
            r"^> For multi-stack projects, `\{\{TESTING\}\}` renders as paired bullets[^\n]*\n\n",
            re.MULTILINE,
        ),
    ]
    for p in patterns:
        text = p.sub("", text)
    return text


def replace_model_line(text: str, tier_value: str) -> str:
    """Surgically replace `model: <x>` in the YAML frontmatter (between `---` delimiters)."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return text
    # Find closing ---
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        return text
    # Replace model: line within frontmatter
    for i in range(1, end_idx):
        if re.match(r"^\s*model\s*:", lines[i]):
            indent_match = re.match(r"^(\s*)model\s*:", lines[i])
            indent = indent_match.group(1) if indent_match else ""
            lines[i] = f"{indent}model: {tier_value}"
            break
    return "\n".join(lines)


def parse_agent_description(text: str) -> str:
    """Extract `description:` from YAML frontmatter for AGENT_LIST rendering."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return ""
    for i in range(1, len(lines)):
        line = lines[i]
        if line.strip() == "---":
            break
        m = re.match(r"^\s*description\s*:\s*(.*)$", line)
        if m:
            desc = m.group(1).strip()
            # Strip surrounding quotes if present
            if (desc.startswith('"') and desc.endswith('"')) or (desc.startswith("'") and desc.endswith("'")):
                desc = desc[1:-1]
            # Use first sentence / first 80 chars
            if "." in desc:
                desc = desc.split(".")[0]
            return desc[:80]
    return ""


def render_agent_list(state: dict[str, Any], agent_descriptions: dict[str, str]) -> str:
    tier_by_agent = {name: entry["tier"].capitalize() for name, entry in state["agents_kept"].items()}
    lines: list[str] = []
    for name in sorted(agent_descriptions):
        desc = agent_descriptions.get(name, "")
        tier = tier_by_agent.get(name, "")
        suffix = f" ({tier} tier)" if tier else ""
        if desc:
            lines.append(f"- `{name}` — {desc}{suffix}")
        else:
            lines.append(f"- `{name}`{suffix}")
    return "\n".join(lines)


def resolve_tier_value(state: dict[str, Any], tier: str) -> str:
    return state["claude_tiers"].get(tier) or "sonnet"


def inject_chrome_devtools_mcp(path: Path) -> None:
    """Insert the chrome-devtools entry into .mcp.json's mcpServers object."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"failed to parse {path}: {e}")
    servers = data.setdefault("mcpServers", {})
    servers["chrome-devtools"] = {
        "command": "npx",
        "args": ["-y", CHROME_DEVTOOLS_MCP_PACKAGE],
    }
    write_atomic(path, json.dumps(data, indent=2) + "\n")


def append_chrome_devtools_permissions(path: Path) -> None:
    """Append chrome-devtools tool-name permissions to .claude/settings.json."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"failed to parse {path}: {e}")
    permissions = data.setdefault("permissions", {})
    allow = permissions.setdefault("allow", [])
    tools = [
        "mcp__chrome-devtools__take_screenshot",
        "mcp__chrome-devtools__take_snapshot",
        "mcp__chrome-devtools__evaluate_script",
        "mcp__chrome-devtools__navigate_page",
        "mcp__chrome-devtools__list_pages",
        "mcp__chrome-devtools__select_page",
        "mcp__chrome-devtools__click",
        "mcp__chrome-devtools__fill",
        "mcp__chrome-devtools__fill_form",
        "mcp__chrome-devtools__wait_for",
        "mcp__chrome-devtools__press_key",
        "mcp__chrome-devtools__hover",
        "mcp__chrome-devtools__list_console_messages",
        "mcp__chrome-devtools__list_network_requests",
        "mcp__chrome-devtools__get_network_request",
    ]
    for t in tools:
        if t not in allow:
            allow.append(t)
    write_atomic(path, json.dumps(data, indent=2) + "\n")


def write_project_config(
    state: dict[str, Any],
    source_root: str,
    workspace_mode: str,
    packages: list[Any],
) -> None:
    """Write the canonical answers record to .devforge/project-config.json.

    Reads existing file (if it has structure) or starts fresh, populates with
    state values + Phase 1 detection facts.
    """
    try:
        data = json.loads(PROJECT_CONFIG.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (json.JSONDecodeError, FileNotFoundError):
        data = {}

    # Fill from state + report
    data.update(
        {
            "PROJECT_NAME": state["project_name"],
            "PROJECT_DESCRIPTION": state["project_description"],
            "PROJECT_TYPE": state["project_type"],
            "WORKSPACE_MODE": workspace_mode,
            "SOURCE_ROOT": source_root,
            "LANGUAGES": state["languages"],
            "FRAMEWORKS": state["frameworks"],
            "PRIMARY_LANGUAGE": state["languages"][0] if state["languages"] else None,
            "ARCHITECTURES": state["architectures"],
            "ERROR_HANDLINGS": state["error_handlings"],
            "API_LAYERS": state["api_layers"],
            "TESTINGS": state["testings"],
            "WORKFLOW_ENFORCEMENT": state["workflow_enforcement"],
            "AI_ATTRIBUTION": state["ai_attribution"],
            "CLAUDE_TIER_THINK": state["claude_tiers"]["think"],
            "CLAUDE_TIER_DO": state["claude_tiers"]["do"],
            "CLAUDE_TIER_VERIFY": state["claude_tiers"]["verify"],
            "AC_VERIFICATION_MODE": state["ac_modes"],
            "AC_RUNTIME_URL": state.get("ac_runtime_url"),
            "AC_RUNTIME_API_BASE": state.get("ac_runtime_api_base"),
            "AC_RUNTIME_CLI_COMMAND": state.get("ac_runtime_cli_command"),
            "PACKAGES_DETECTED": packages,
        }
    )

    write_atomic(PROJECT_CONFIG, json.dumps(data, indent=2) + "\n")


def insert_memory_seed(path: Path, seed: str) -> None:
    """Insert the seed prose above the `<!-- Populated during constitute` sentinel."""
    text = path.read_text(encoding="utf-8")
    if MEMORY_SENTINEL not in text:
        # Sentinel missing — append at end as a soft fallback
        text = text.rstrip() + "\n\n" + seed.rstrip() + "\n"
        write_atomic(path, text)
        return
    # Insert seed immediately before the sentinel line
    parts = text.split(MEMORY_SENTINEL, 1)
    new_text = parts[0].rstrip() + "\n\n" + seed.rstrip() + "\n\n" + MEMORY_SENTINEL + parts[1]
    write_atomic(path, new_text)


def write_setup_complete(written: list[str]) -> None:
    from datetime import datetime, timezone
    marker = DEVFORGE_DIR / "setup-complete"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content = f"Setup completed: {ts}\nPopulated files: {', '.join(written)}\n"
    write_atomic(marker, content)


# ─── argparse setup ──────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wizard_render",
        description="Compose Phase 3 + Phase 4 file population for setup-wizard.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_set = sub.add_parser("set", help="Set a scalar field (project_name, etc.).")
    p_set.add_argument("field")
    p_set.add_argument("--value", required=True)
    p_set.set_defaults(func=cmd_set)

    p_tier = sub.add_parser("set-tier", help="Set a Claude tier (think/do/verify) → model.")
    p_tier.add_argument("tier")
    p_tier.add_argument("--value", required=True)
    p_tier.set_defaults(func=cmd_set_tier)

    p_render = sub.add_parser("set-render", help="Set an LLM-composed multi-line render (project_structure, dev_commands, architecture_details, package_stacks_section, memory_seed).")
    p_render.add_argument("field")
    p_render.add_argument("--value", default=None)
    p_render.add_argument("--stdin", action="store_true", help="Read value from stdin (preferred for multi-line).")
    p_render.set_defaults(func=cmd_set_render)

    p_lang = sub.add_parser("add-language", help="Append to languages[] + frameworks[] (parallel arrays).")
    p_lang.add_argument("--name", required=True)
    p_lang.add_argument("--framework", default=None)
    p_lang.set_defaults(func=cmd_add_language)

    p_ac = sub.add_parser("add-ac-mode", help="Append to ac_modes[] (one of code-only|tests|runtime-assisted|off).")
    p_ac.add_argument("--value", required=True)
    p_ac.set_defaults(func=cmd_add_ac_mode)

    for name, fn in (
        ("add-architecture", cmd_add_architecture),
        ("add-error-handling", cmd_add_error_handling),
        ("add-api-layer", cmd_add_api_layer),
        ("add-testing", cmd_add_testing),
        ("add-build-tool", cmd_add_build_tool),
        ("add-build-command", cmd_add_build_command),
        ("add-type-check-command", cmd_add_type_check_command),
        ("add-lint-command", cmd_add_lint_command),
    ):
        p = sub.add_parser(name, help=f"Append one entry to per-stack array.")
        p.add_argument("--value", required=True)
        p.set_defaults(func=fn)

    p_agents = sub.add_parser("apply-agents", help="Record kept + removed agent decisions and substitutions.")
    p_agents.add_argument("--substitutions-file", required=True)
    p_agents.set_defaults(func=cmd_apply_agents)

    p_status = sub.add_parser("status", help="Show set/unset state and compose readiness.")
    p_status.set_defaults(func=cmd_status)

    p_compose = sub.add_parser("compose", help="Validate + write all files atomically.")
    p_compose.set_defaults(func=cmd_compose)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
