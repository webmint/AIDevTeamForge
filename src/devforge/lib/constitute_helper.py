"""constitute_helper — composes the constitution.md state file for /constitute.

Owns the shape of `.devforge/constitute.json` (canonical state) and
`<install_root>/constitution.md` (render artifact). Schema-anchored:
helper owns markdown structure, LLM provides values via setters. Mirrors
the helper-owns-shape pattern established by init_helper / configure_helper /
generate_docs_helper.

`/constitute` is the fourth and last command in the 4-command pivot
(init-forge → generate-docs → configure → constitute).

Step 1 (this commit): FIELD_SCHEMA + ENUM_FIELDS populated; default_state()
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
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union


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
# Error helpers.
# ---------------------------------------------------------------------------


def _die(message: str, code: int = 1) -> int:
    """Write an error message to stderr and return the given exit code."""
    sys.stderr.write("constitute_helper: {0}\n".format(message))
    return code


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
