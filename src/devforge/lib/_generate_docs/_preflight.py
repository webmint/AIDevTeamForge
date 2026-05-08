"""F.0 — preflight subcommand.

Runs vue-extract + codebase-memory-mcp index_repository (both idempotent),
then computes per-concern source_stamps and diffs each against the existing
`docs/<package>/<concern>/index.md` frontmatter. Emits a JSON summary the
caller (F.4 /generate-docs orchestrator, F.9 consumer commands) gates on.

Reframes freshness from "invariant-to-maintain" to "operation-to-run":
cheap mechanical operations always run, expensive LLM dispatch gates on
the per-concern `status` field returned here.

Side effect: writes `<devforge_dir>/.preflight-stamp` with the wall-time
of the last successful run. Consumer commands MAY use this for a 60s
freshness shortcut (per-command policy, not enforced here).

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ._concern_input import _build_spans_and_stamp, _walk_concern_subfolder
from ._md_frontmatter import FrontmatterParseError, parse_frontmatter
from ._setters_concern import _path_contains_trivial_dir

_PREFLIGHT_STAMP_FILE = ".preflight-stamp"
_INDEX_FILE_NAME = "index.json"


def _enumerate_concerns(
    devforge_dir: Path, project_root: Path
) -> List[Tuple[str, str]]:
    """List (project_relative_package_path, concern) pairs.

    Source of packages: index.json's `packages` map (excluding the `.`
    project-root entry). Each package key in index.json is relative to
    index.json's own `project_root` field, which in wrapper-mode setups
    differs from `<devforge_dir>/..` (e.g., wrapper root vs monorepo root
    one level deeper). This function bridges by prefixing the wrapper-to-
    monorepo path component so the returned package path is always
    relative to the wrapper (i.e., to the F.0 caller's project_root).

    For each resolved package path, walks `<project_root>/<full_pkg>/src/`
    for direct subdirs; each non-trivial subdir is a concern. Packages
    without a `src/` dir at the resolved location are skipped silently.
    """
    index_path = devforge_dir / _INDEX_FILE_NAME
    if not index_path.exists():
        return []
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    packages = index.get("packages")
    if not isinstance(packages, dict):
        return []

    # Bridge index.json's package keys (relative to its project_root) to
    # paths relative to F.0's caller-supplied project_root.
    prefix = ""
    raw_index_root = index.get("project_root")
    if isinstance(raw_index_root, str) and raw_index_root:
        try:
            index_root = Path(raw_index_root).resolve()
            if index_root != project_root:
                rel = index_root.relative_to(project_root)
                prefix = str(rel) + "/"
        except (ValueError, OSError):
            prefix = ""

    pairs: List[Tuple[str, str]] = []
    for pkg in sorted(packages.keys()):
        if pkg == ".":
            continue
        full_pkg = prefix + pkg
        src_dir = project_root / full_pkg / "src"
        if not src_dir.is_dir():
            continue
        try:
            entries = sorted(src_dir.iterdir())
        except OSError:
            continue
        for entry in entries:
            if not entry.is_dir():
                continue
            if _path_contains_trivial_dir(entry.name):
                continue
            pairs.append((full_pkg, entry.name))
    return pairs


def _read_prior_stamp(doc_path: Path) -> Optional[str]:
    """Read the `source_stamp` field from a doc's frontmatter.

    Returns None when the doc doesn't exist, the file is unreadable,
    frontmatter is malformed, or the field is absent.
    """
    if not doc_path.is_file():
        return None
    try:
        text = doc_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        record, _body = parse_frontmatter(text)
    except FrontmatterParseError:
        return None
    value = record.get("source_stamp")
    if isinstance(value, str) and value:
        return value
    return None


def _diff_concern(
    pkg: str,
    concern: str,
    project_root: Path,
    docs_root: Path,
) -> Dict[str, Any]:
    """Compute source_stamp for one concern + diff against existing doc."""
    project_root = project_root.resolve()
    _subfolder_abs, concern_files = _walk_concern_subfolder(project_root, pkg, concern)
    if not concern_files:
        return {
            "package": pkg,
            "concern": concern,
            "source_stamp": "",
            "prior_stamp": None,
            "status": "empty",
        }
    _records, _hashes, source_stamp = _build_spans_and_stamp(concern_files, project_root)
    doc_path = docs_root / pkg / concern / "index.md"
    prior_stamp = _read_prior_stamp(doc_path)
    if prior_stamp is None:
        status = "new"
    elif prior_stamp == source_stamp:
        status = "unchanged"
    else:
        status = "changed"
    return {
        "package": pkg,
        "concern": concern,
        "source_stamp": source_stamp,
        "prior_stamp": prior_stamp,
        "status": status,
    }


def _run_vue_extract(
    devforge_dir: Path, project_root: Path
) -> Dict[str, Any]:
    """Invoke `vue-extract` launcher; return result block."""
    launcher = devforge_dir / "lib" / "vue-extract"
    if not launcher.is_file():
        return {
            "ran": False,
            "reason": f"launcher not found at {launcher}",
            "compiled": 0,
            "failed": 0,
            "duration_ms": 0,
        }
    start = time.monotonic()
    try:
        result = subprocess.run(
            ["bash", str(launcher)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return {
            "ran": False,
            "reason": f"launcher invocation failed: {exc}",
            "compiled": 0,
            "failed": 0,
            "duration_ms": int((time.monotonic() - start) * 1000),
        }
    duration_ms = int((time.monotonic() - start) * 1000)
    blob = (result.stdout or "") + (result.stderr or "")
    # vue-extract launcher prints e.g. `1 ok, 0 failed, 0.01s` on its last line.
    compiled = 0
    failed = 0
    match = re.search(r"(\d+)\s+ok,\s+(\d+)\s+failed", blob)
    if match:
        compiled = int(match.group(1))
        failed = int(match.group(2))
    summary = blob.strip().splitlines()[-1] if blob.strip() else ""
    return {
        "ran": True,
        "exit_code": result.returncode,
        "compiled": compiled,
        "failed": failed,
        "duration_ms": duration_ms,
        "summary_line": summary,
    }


def _run_index_repository(project_root: Path) -> Dict[str, Any]:
    """Invoke `codebase-memory-mcp cli index_repository`; return result block."""
    if shutil.which("codebase-memory-mcp") is None:
        return {
            "ran": False,
            "reason": "codebase-memory-mcp binary not found on PATH",
            "duration_ms": 0,
        }
    start = time.monotonic()
    payload = json.dumps({"repo_path": str(project_root.resolve())})
    try:
        result = subprocess.run(
            ["codebase-memory-mcp", "cli", "index_repository", payload],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return {
            "ran": False,
            "reason": f"cli invocation failed: {exc}",
            "duration_ms": int((time.monotonic() - start) * 1000),
        }
    duration_ms = int((time.monotonic() - start) * 1000)
    block: Dict[str, Any] = {
        "ran": True,
        "exit_code": result.returncode,
        "duration_ms": duration_ms,
    }
    # CBM CLI prints a level=info line + JSON; pull JSON.
    json_payload: Optional[Dict[str, Any]] = None
    for line in (result.stdout or "").splitlines():
        line_stripped = line.strip()
        if line_stripped.startswith("{") and line_stripped.endswith("}"):
            try:
                json_payload = json.loads(line_stripped)
                break
            except json.JSONDecodeError:
                continue
    if isinstance(json_payload, dict):
        for key in ("nodes", "edges", "size_bytes", "project"):
            if key in json_payload:
                block[key] = json_payload[key]
    if result.returncode != 0:
        block["stderr"] = (result.stderr or "").strip()[:500]
    return block


def cmd_preflight(args: argparse.Namespace) -> int:
    """Handler for `preflight` subcommand. Returns CLI exit code."""
    devforge_dir = Path(args.devforge_dir)
    project_root = devforge_dir.parent.resolve()
    docs_root = project_root / "docs"

    output: Dict[str, Any] = {}

    if args.skip_vue_extract:
        output["vue_extract"] = {"ran": False, "reason": "skipped via flag"}
    else:
        output["vue_extract"] = _run_vue_extract(devforge_dir, project_root)
        if output["vue_extract"].get("exit_code", 0) not in (0,) and output["vue_extract"].get("ran"):
            print(json.dumps(output, indent=2))
            print(
                f"vue-extract failed (exit {output['vue_extract']['exit_code']})",
                file=sys.stderr,
            )
            return 1

    if args.skip_index:
        output["index_repository"] = {"ran": False, "reason": "skipped via flag"}
    else:
        output["index_repository"] = _run_index_repository(project_root)
        if not output["index_repository"].get("ran"):
            print(json.dumps(output, indent=2))
            print(
                output["index_repository"].get("reason", "index_repository did not run"),
                file=sys.stderr,
            )
            return 2
        if output["index_repository"].get("exit_code", 0) != 0:
            print(json.dumps(output, indent=2))
            print(
                f"index_repository failed (exit {output['index_repository']['exit_code']})",
                file=sys.stderr,
            )
            return 1

    pairs = _enumerate_concerns(devforge_dir, project_root)
    concerns = [_diff_concern(pkg, c, project_root, docs_root) for pkg, c in pairs]
    output["concerns"] = concerns

    counts = {"unchanged": 0, "changed": 0, "new": 0, "empty": 0}
    for entry in concerns:
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    output["concern_counts"] = counts

    stamp_path = devforge_dir / _PREFLIGHT_STAMP_FILE
    try:
        stamp_path.write_text(str(int(time.time())) + "\n", encoding="utf-8")
        try:
            relative = stamp_path.resolve().relative_to(project_root)
            output["preflight_stamp_path"] = str(relative)
        except ValueError:
            # devforge_dir may be outside project_root (rare); fall back to absolute.
            output["preflight_stamp_path"] = str(stamp_path)
    except OSError:
        # Stamp file is advisory; don't fail the run if it can't be written.
        output["preflight_stamp_path"] = None

    print(json.dumps(output, indent=2))
    return 0


def _build_preflight(p: argparse.ArgumentParser) -> None:
    """argparse factory for the `preflight` subcommand."""
    p.add_argument("--devforge-dir", default=".devforge")
    p.add_argument(
        "--skip-vue-extract",
        action="store_true",
        help="Skip the vue-extract pre-pass (escape valve only)",
    )
    p.add_argument(
        "--skip-index",
        action="store_true",
        help="Skip the codebase-memory-mcp index_repository call (escape valve only)",
    )
