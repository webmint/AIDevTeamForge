#!/usr/bin/env python3
"""Onboard Helper for the /onboard command.

The onboard LLM (and its dispatched tech-writer subagents) calls this tool
to register documentation artifacts: per-package docs, per-concern docs,
the workspace architecture doc, and memory findings. The helper is the
*only* sanctioned path to write under docs/. Bulk-script-write is
unrepresentable in the API surface — this is the forcing function for
per-unit dispatch + per-concern decomposition.

Verbs:
  set                   Set a top-level scalar (e.g. mode = overwrite|merge|fresh)
  add-package-doc       Register one package's index.md content
  add-concern-doc       Register one concern doc inside a package
  add-architecture-doc  Register the workspace architecture.md (single call)
  add-memory-finding    Register one memory observation (multiple calls)
  status                Print machine-readable progress
  compose-onboard       Validate + atomically write all registered docs

Step 1.5 adds: compose-onboard atomic write to docs/, baseline drops, and
memory append. No validation gates yet — those land in Phase 2.

Stdlib only. No third-party dependencies. Target Python: 3.8+.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional


# ─── Paths ───────────────────────────────────────────────────────────────────
# The onboard command invokes this tool from the target project root.
# `.devforge/` is created by install.sh; we mkdir defensively for ad-hoc / test
# use (in load_state / save_state).

DEVFORGE_DIR = Path(".devforge")
STATE_FILE = DEVFORGE_DIR / ".onboard-state.json"
DOCS_DIR = Path("docs")
BASELINE_DIR = DEVFORGE_DIR / "baseline" / "docs"


# ─── Schema ──────────────────────────────────────────────────────────────────
# State persisted between invocations. Each invocation reads → mutates →
# writes back. compose-onboard consumes the final state and clears it.


@dataclass
class DocEntry:
    """Common shape for package / concern / architecture doc registrations."""
    content: str = ""
    block_count: int = 0
    ref_count: int = 0


@dataclass
class PackageDoc(DocEntry):
    """A package-level index.md registration."""
    unit: str = ""
    path: str = ""  # Source path relative to SOURCE_ROOT.


@dataclass
class ConcernDoc(DocEntry):
    """A concern-level doc registration nested within a package."""
    unit: str = ""
    concern: str = ""


@dataclass
class MemoryFinding:
    """One observation for .devforge/memory.md."""
    category: str = ""  # module-boundaries | dependency-warnings | complexity | inconsistencies
    unit: str = ""  # or 'workspace' for cross-cutting
    observation: str = ""


@dataclass
class OnboardState:
    """All registered onboard artifacts. Persisted as .devforge/.onboard-state.json."""
    mode: Optional[str] = None  # overwrite | merge | fresh
    package_docs: dict[str, PackageDoc] = field(default_factory=dict)  # keyed by unit name
    concern_docs: list[ConcernDoc] = field(default_factory=list)
    architecture_doc: Optional[DocEntry] = None
    memory_findings: list[MemoryFinding] = field(default_factory=list)


# ─── State R/W (atomic) ──────────────────────────────────────────────────────


def load_state() -> OnboardState:
    """Read state from STATE_FILE; return empty OnboardState if missing."""
    if not STATE_FILE.exists():
        return OnboardState()
    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(
            f"onboard_helper: corrupt state file {STATE_FILE}: {exc}",
            file=sys.stderr,
        )
        sys.exit(2)
    return _state_from_dict(raw)


def save_state(state: OnboardState) -> None:
    """Atomically write state to STATE_FILE via temp file + os.replace."""
    DEVFORGE_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(asdict(state), indent=2, sort_keys=False)
    # Write to a sibling temp file in the same directory for atomic rename.
    fd, tmp_path = tempfile.mkstemp(
        prefix=".onboard-state-", suffix=".json", dir=str(DEVFORGE_DIR)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(payload)
        os.replace(tmp_path, STATE_FILE)
    except Exception:
        # Clean up the temp file if rename failed.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def clear_state() -> None:
    """Remove the state file. Called by compose-onboard on success."""
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def _state_from_dict(raw: dict[str, Any]) -> OnboardState:
    """Reconstruct OnboardState from the JSON-loaded dict.

    Hand-written rather than asdict-inverse because dataclass nesting needs
    explicit reconstruction for list[X] / dict[str, X] fields.
    """
    state = OnboardState(mode=raw.get("mode"))

    pkg_docs_raw = raw.get("package_docs") or {}
    for unit, doc_raw in pkg_docs_raw.items():
        state.package_docs[unit] = PackageDoc(**doc_raw)

    for c_raw in raw.get("concern_docs") or []:
        state.concern_docs.append(ConcernDoc(**c_raw))

    arch_raw = raw.get("architecture_doc")
    if arch_raw is not None:
        state.architecture_doc = DocEntry(**arch_raw)

    for m_raw in raw.get("memory_findings") or []:
        state.memory_findings.append(MemoryFinding(**m_raw))

    return state


# ─── Subcommand handlers ─────────────────────────────────────────────────────


def _not_implemented(name: str) -> int:
    print(f"onboard_helper: '{name}' not implemented yet (current step skeleton).", file=sys.stderr)
    return 2


def cmd_set(args: argparse.Namespace) -> int:
    """Update a top-level scalar on the state."""
    state = load_state()
    field_name = args.field
    if field_name == "mode":
        state.mode = args.value
    else:
        # No validation gate yet (lands in Phase 2). Accept any field name and
        # set it as a generic attribute. Currently only `mode` is recognized;
        # unknown fields print a warning but do not fail.
        print(
            f"onboard_helper: warning — unknown top-level field '{field_name}'. "
            f"Currently only 'mode' is recognized. Stored anyway for forward compat.",
            file=sys.stderr,
        )
        # Use setattr for forward-compat with future top-level fields.
        setattr(state, field_name, args.value)
    save_state(state)
    print(f"set {field_name} = {args.value}")
    return 0


def cmd_add_package_doc(args: argparse.Namespace) -> int:
    """Register one package-level index.md."""
    state = load_state()
    state.package_docs[args.unit] = PackageDoc(
        unit=args.unit,
        path=args.path,
        content=args.content,
        block_count=args.block_count,
        ref_count=args.ref_count,
    )
    save_state(state)
    print(f"add-package-doc {args.unit} (path={args.path}, blocks={args.block_count}, refs={args.ref_count})")
    return 0


def cmd_add_concern_doc(args: argparse.Namespace) -> int:
    """Register one concern doc within a package."""
    state = load_state()
    state.concern_docs.append(ConcernDoc(
        unit=args.unit,
        concern=args.concern,
        content=args.content,
        block_count=args.block_count,
        ref_count=args.ref_count,
    ))
    save_state(state)
    print(f"add-concern-doc {args.unit}/{args.concern} (blocks={args.block_count}, refs={args.ref_count})")
    return 0


def cmd_add_architecture_doc(args: argparse.Namespace) -> int:
    """Register the workspace architecture.md (overwrites if called twice)."""
    state = load_state()
    state.architecture_doc = DocEntry(
        content=args.content,
        block_count=args.block_count,
        ref_count=args.ref_count,
    )
    save_state(state)
    print(f"add-architecture-doc (blocks={args.block_count}, refs={args.ref_count})")
    return 0


def cmd_add_memory_finding(args: argparse.Namespace) -> int:
    """Register one memory observation."""
    state = load_state()
    state.memory_findings.append(MemoryFinding(
        category=args.category,
        unit=args.unit,
        observation=args.observation,
    ))
    save_state(state)
    print(f"add-memory-finding [{args.category}] {args.unit}: {args.observation[:60]}...")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Print machine-readable progress.

    Format: one field per line, `field: value`. Consumable by the LLM
    orchestrator to decide whether more registrations are needed before
    compose-onboard.
    """
    state = load_state()
    print(f"mode: {state.mode if state.mode else 'UNSET'}")
    print(f"package_docs: {len(state.package_docs)}")
    print(f"concern_docs: {len(state.concern_docs)}")
    print(f"architecture_doc: {'SET' if state.architecture_doc else 'UNSET'}")
    print(f"memory_findings: {len(state.memory_findings)}")
    # Per-package concern-doc counts (helps the orchestrator see which units
    # have decomposition coverage).
    if state.concern_docs:
        per_unit_concerns: dict[str, int] = {}
        for c in state.concern_docs:
            per_unit_concerns[c.unit] = per_unit_concerns.get(c.unit, 0) + 1
        print("concern_docs_by_unit:")
        for unit, count in sorted(per_unit_concerns.items()):
            print(f"  {unit}: {count}")
    return 0


def cmd_compose_onboard(args: argparse.Namespace) -> int:
    """Atomically write all registered docs to docs/, drop baselines, append
    memory findings, and clear state on success. No validation gates yet
    (those layer in Phase 2)."""
    state = load_state()
    written: list[Path] = []

    # 1. Package docs.
    for unit, pkg in state.package_docs.items():
        target = DOCS_DIR / pkg.path / "index.md"
        _write_doc_atomically(target, pkg.content)
        written.append(target)

    # 2. Concern docs (resolved against parent package's path).
    skipped_concerns: list[str] = []
    for concern in state.concern_docs:
        parent = state.package_docs.get(concern.unit)
        if parent is None:
            skipped_concerns.append(f"{concern.unit}/{concern.concern}")
            continue
        target = DOCS_DIR / parent.path / f"{concern.concern}.md"
        _write_doc_atomically(target, concern.content)
        written.append(target)

    # 3. Architecture doc.
    if state.architecture_doc is not None:
        target = DOCS_DIR / "architecture.md"
        _write_doc_atomically(target, state.architecture_doc.content)
        written.append(target)

    # 4. Memory findings.
    memory_appended = _append_memory_findings(state.memory_findings)

    # 5. Drop baselines.
    for target in written:
        rel = target.relative_to(DOCS_DIR)
        baseline_path = BASELINE_DIR / rel
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, baseline_path)

    # 6. Clear state on success.
    clear_state()

    # 7. Report.
    print(
        f"compose-onboard: wrote {len(written)} doc files; "
        f"baselines dropped at {BASELINE_DIR}; "
        f"memory findings appended: {memory_appended}"
    )
    if skipped_concerns:
        print(
            f"  warning: {len(skipped_concerns)} concern doc(s) skipped (no parent package): "
            f"{', '.join(skipped_concerns)}",
            file=sys.stderr,
        )
    return 0


# ─── compose-onboard internals ───────────────────────────────────────────────


def _write_doc_atomically(target: Path, content: str) -> None:
    """Write content to target via temp file in same dir + os.replace."""
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".onboard-doc-", suffix=".md", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, target)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# Memory category → (parent section heading, subsection-heading-format).
# Subsection heading is dated so re-runs append rather than collide.
_MEMORY_SECTION_MAP = {
    "module-boundaries": ("## Architecture Decisions", "### Module boundaries (from onboard {date})"),
    "dependency-warnings": ("## Known Pitfalls", "### Dependency warnings (from onboard {date})"),
    "complexity": ("## Known Pitfalls", "### Areas of complexity (from onboard {date})"),
    "inconsistencies": ("## Known Pitfalls", "### Inconsistencies (from onboard {date})"),
}


def _append_memory_findings(findings: list[MemoryFinding]) -> int:
    """Insert findings into .devforge/memory.md under scaffold sections.

    Returns count of findings appended. If memory.md doesn't exist, prints a
    warning and returns 0.
    """
    if not findings:
        return 0

    memory_file = DEVFORGE_DIR / "memory.md"
    if not memory_file.exists():
        print(
            f"warning: {memory_file} not found; memory findings not persisted",
            file=sys.stderr,
        )
        return 0

    today = date.today().isoformat()

    # Group findings by category.
    by_category: dict[str, list[MemoryFinding]] = {}
    for f in findings:
        by_category.setdefault(f.category, []).append(f)

    existing = memory_file.read_text(encoding="utf-8")
    updated = existing
    appended = 0

    for category, items in by_category.items():
        if category not in _MEMORY_SECTION_MAP:
            continue
        parent_heading, sub_heading_fmt = _MEMORY_SECTION_MAP[category]
        sub_heading = sub_heading_fmt.format(date=today)
        bullets = "\n".join(f"- `{f.unit}`: {f.observation}" for f in items)
        block = f"\n{sub_heading}\n{bullets}\n"

        # Insert immediately after the parent heading line if it exists;
        # otherwise append at end with parent heading prepended.
        if parent_heading in updated:
            idx = updated.index(parent_heading) + len(parent_heading)
            line_end = updated.index("\n", idx)
            updated = updated[: line_end + 1] + block + updated[line_end + 1 :]
        else:
            updated += f"\n{parent_heading}\n{block}"

        appended += len(items)

    memory_file.write_text(updated, encoding="utf-8")
    return appended


# ─── Argparse setup ──────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="onboard_helper",
        description=(
            "Register onboard documentation artifacts (per-package, per-concern, "
            "architecture, memory) and atomically compose them into docs/. "
            "Bulk-script-write is unsupported by design."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_set = sub.add_parser(
        "set",
        help="Set a top-level scalar (e.g. mode).",
    )
    p_set.add_argument("field", help="Field name (e.g. mode).")
    p_set.add_argument("--value", required=True, help="Value to set.")
    p_set.set_defaults(func=cmd_set)

    p_pkg = sub.add_parser(
        "add-package-doc",
        help="Register one package's index.md content.",
    )
    p_pkg.add_argument("--unit", required=True, help="Package/unit name.")
    p_pkg.add_argument("--path", required=True, help="Package's source path relative to SOURCE_ROOT (e.g. packages/pkg-foo).")
    p_pkg.add_argument("--content", required=True, help="Full markdown content for docs/<path>/index.md.")
    p_pkg.add_argument("--block-count", type=int, required=True, help="Self-reported count of fenced code blocks in content.")
    p_pkg.add_argument("--ref-count", type=int, required=True, help="Self-reported count of <!-- path:line --> references in content. Must equal block-count.")
    p_pkg.set_defaults(func=cmd_add_package_doc)

    p_concern = sub.add_parser(
        "add-concern-doc",
        help="Register one concern doc inside a package.",
    )
    p_concern.add_argument("--unit", required=True, help="Parent package/unit name (must be already registered via add-package-doc).")
    p_concern.add_argument("--concern", required=True, help="Concern name (subfolder name, e.g. components, services, routing).")
    p_concern.add_argument("--content", required=True, help="Full markdown content for docs/<unit-path>/<concern>.md.")
    p_concern.add_argument("--block-count", type=int, required=True, help="Self-reported count of fenced code blocks in content.")
    p_concern.add_argument("--ref-count", type=int, required=True, help="Self-reported count of <!-- path:line --> references in content. Must equal block-count.")
    p_concern.set_defaults(func=cmd_add_concern_doc)

    p_arch = sub.add_parser(
        "add-architecture-doc",
        help="Register the workspace architecture.md (single call). Distinct prompt template — NOT the per-package template.",
    )
    p_arch.add_argument("--content", required=True, help="Full markdown content for docs/architecture.md.")
    p_arch.add_argument("--block-count", type=int, required=True, help="Self-reported count of fenced code blocks in content.")
    p_arch.add_argument("--ref-count", type=int, required=True, help="Self-reported count of <!-- path:line --> references in content. Must equal block-count.")
    p_arch.set_defaults(func=cmd_add_architecture_doc)

    p_mem = sub.add_parser(
        "add-memory-finding",
        help="Register one memory observation. Multiple calls. Findings collected during a separate source-reading pass, NOT summarized from generated docs.",
    )
    p_mem.add_argument(
        "--category",
        required=True,
        choices=["module-boundaries", "dependency-warnings", "complexity", "inconsistencies"],
        help="Memory category (maps to scaffold subsection).",
    )
    p_mem.add_argument("--unit", required=True, help="Unit/package this finding applies to (or 'workspace' for cross-cutting).")
    p_mem.add_argument("--observation", required=True, help="The finding itself (one line).")
    p_mem.set_defaults(func=cmd_add_memory_finding)

    p_status = sub.add_parser(
        "status",
        help="Show machine-readable progress (registrations per category, missing required, validator state).",
    )
    p_status.set_defaults(func=cmd_status)

    p_compose = sub.add_parser(
        "compose-onboard",
        help="Validate state and atomically write all registered docs to docs/. Drop baselines on success. Clears state on success.",
    )
    p_compose.set_defaults(func=cmd_compose_onboard)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
