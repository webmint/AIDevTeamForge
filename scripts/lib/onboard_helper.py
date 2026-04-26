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

Step 1.2 adds: schema dataclasses + state R/W with atomic write. Subcommand
handlers remain stubs; wiring lands in Step 1.3.

Stdlib only. No third-party dependencies. Target Python: 3.8+.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass, field
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


# ─── Subcommand handlers (stubs — wiring lands in Step 1.3) ──────────────────


def _not_implemented(name: str) -> int:
    print(f"onboard_helper: '{name}' not implemented yet (Step 1.2 skeleton).", file=sys.stderr)
    return 2


def cmd_set(args: argparse.Namespace) -> int:
    return _not_implemented("set")


def cmd_add_package_doc(args: argparse.Namespace) -> int:
    return _not_implemented("add-package-doc")


def cmd_add_concern_doc(args: argparse.Namespace) -> int:
    return _not_implemented("add-concern-doc")


def cmd_add_architecture_doc(args: argparse.Namespace) -> int:
    return _not_implemented("add-architecture-doc")


def cmd_add_memory_finding(args: argparse.Namespace) -> int:
    return _not_implemented("add-memory-finding")


def cmd_status(args: argparse.Namespace) -> int:
    return _not_implemented("status")


def cmd_compose_onboard(args: argparse.Namespace) -> int:
    return _not_implemented("compose-onboard")


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
