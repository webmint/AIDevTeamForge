"""F.5 — validate-doc helper (concern tier; v0).

Walks a rendered concern doc at `docs/<package>/<concern>/index.md` and
checks every Plan F density invariant: frontmatter required keys present,
section anchors present, no banned phrases, hazard count within range,
hazard bullets carry a resolvable cite-back within the per-bullet length
cap, structure annotations within their cap.

Concern-tier only in this build. Package + project tiers ship under
forthcoming F.5 expansion. Vue cite-back through-sourcemap validation
likewise deferred — currently only existence + line-range is checked.

Exit codes:
- 0 — every check passed
- 2 — at least one violation; stderr lists every error; orchestrator
       passes stderr verbatim back to doc-composer as
       previous_attempt_feedback for retry

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from ._md_frontmatter import FrontmatterParseError, parse_frontmatter

_CONCERN_REQUIRED_KEYS = ("concern", "package", "files", "source_stamp", "last_indexed")
_CONCERN_REQUIRED_SECTIONS = ("## Purpose", "## Structure", "## Hazards")

_BANNED_PHRASES_RE = re.compile(
    r"\b(this document|in this section|we will|various|several|many|some|other)\b",
    re.IGNORECASE,
)
_BULLET_RE = re.compile(r"^- ", re.MULTILINE)
_CITE_RE = re.compile(
    r"(?P<path>[A-Za-z0-9_./-]+):(?P<start>\d+)"
    r"(?:-(?P<end>\d+))?"
    r"(?:,(?P<extra>\d+))?"
)
_HAZARD_BULLET_CAP = 200
_ANNOTATION_CAP = 60
_HAZARD_COUNT_MIN = 3
_HAZARD_COUNT_MAX = 15


def _split_sections(body: str) -> Dict[str, str]:
    """Split body into {section_name: section_body} pairs.

    Section header pattern: a line starting with `## `. Body of a section
    is everything between its header and the next `## ` header (or EOF).
    """
    sections: Dict[str, str] = {}
    current_name: str = ""
    current_lines: List[str] = []
    for line in body.split("\n"):
        if line.startswith("## "):
            if current_name:
                sections[current_name] = "\n".join(current_lines).strip("\n")
            current_name = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_name:
        sections[current_name] = "\n".join(current_lines).strip("\n")
    return sections


def _parse_bullets(section_text: str) -> List[str]:
    """Extract bullet entries from a `## ` section.

    A bullet entry begins with a line `- ` and continues until the next
    line that begins with `- ` or until end of section. Returns the joined
    text per bullet (whitespace-stripped).
    """
    if not section_text:
        return []
    lines = section_text.split("\n")
    bullets: List[str] = []
    current: List[str] = []
    for line in lines:
        if line.startswith("- "):
            if current:
                bullets.append(" ".join(s.strip() for s in current).strip())
            current = [line[2:]]
        elif current:
            stripped = line.strip()
            if stripped:
                current.append(stripped)
    if current:
        bullets.append(" ".join(s.strip() for s in current).strip())
    return bullets


def _resolve_cite_path(
    cite_path: str, target: str, project_root: Path
) -> Tuple[Path, str]:
    """Resolve a cite-back path string to an absolute file path.

    Plan F allows three cite-path forms (in priority order):

    1. Full project-relative path — `<pkg>/src/<concern>/.../<file>`.
       Tried first; resolves verbatim under project_root.
    2. In-concern basename — when the cited file lives in the doc's own
       concern subfolder, the agent may write only the basename. Source
       dir is `<pkg>/src/<concern>/` on disk; target convention is
       `<pkg>/<concern>` (no `src/`). This branch splits target into pkg
       + concern parts and probes `<project_root>/<pkg>/src/<concern>/<cite_path>`.
    3. Verbatim target append — fallback `<project_root>/<target>/<cite_path>`
       for callers passing a target that already includes `src/`.

    Returns (absolute_path, mode). Mode ∈ {"full", "basename", "verbatim",
    "miss"}. On miss the returned path is the full-form attempt (for
    diagnostic).
    """
    full_attempt = project_root / cite_path
    if full_attempt.is_file():
        return full_attempt, "full"

    target_parts = target.split("/")
    if len(target_parts) >= 2:
        pkg_part = "/".join(target_parts[:-1])
        concern_part = target_parts[-1]
        basename_attempt = project_root / pkg_part / "src" / concern_part / cite_path
        if basename_attempt.is_file():
            return basename_attempt, "basename"

    verbatim_attempt = project_root / target / cite_path
    if verbatim_attempt.is_file():
        return verbatim_attempt, "verbatim"

    return full_attempt, "miss"


def _validate_concern_doc(
    doc_path: Path, target: str, project_root: Path
) -> List[str]:
    """Apply concern-tier checks. Return list of error strings (empty = OK)."""
    errors: List[str] = []
    if not doc_path.is_file():
        return [f"doc not found: {doc_path}"]
    try:
        text = doc_path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"doc unreadable: {exc}"]

    record: Dict[str, object] = {}
    body = text
    try:
        record, body = parse_frontmatter(text)
    except FrontmatterParseError as exc:
        errors.append(f"frontmatter parse: {exc}")

    missing_keys = [k for k in _CONCERN_REQUIRED_KEYS if k not in record]
    if missing_keys:
        errors.append(f"frontmatter missing keys: {missing_keys}")

    for anchor in _CONCERN_REQUIRED_SECTIONS:
        if anchor not in body:
            errors.append(f"missing required section: {anchor!r}")

    for match in _BANNED_PHRASES_RE.finditer(body):
        line_idx = body[: match.start()].count("\n") + 1
        errors.append(f"banned phrase {match.group(0)!r} at body line {line_idx}")

    sections = _split_sections(body)
    hazards_text = sections.get("Hazards", "")
    hazards = _parse_bullets(hazards_text)

    if hazards or "## Hazards" in body:
        if not (_HAZARD_COUNT_MIN <= len(hazards) <= _HAZARD_COUNT_MAX):
            errors.append(
                f"hazard count {len(hazards)} outside range "
                f"[{_HAZARD_COUNT_MIN}, {_HAZARD_COUNT_MAX}]"
            )
        for i, hz in enumerate(hazards, start=1):
            if len(hz) > _HAZARD_BULLET_CAP:
                errors.append(
                    f"hazard {i} length {len(hz)} > {_HAZARD_BULLET_CAP} "
                    f"(first 80 chars: {hz[:80]!r})"
                )
            if not _CITE_RE.search(hz):
                errors.append(
                    f"hazard {i} missing cite-back: {hz[:80]!r}"
                )

    structure_text = sections.get("Structure", "")
    for line in structure_text.split("\n"):
        if " — " in line:
            annotation = line.split(" — ", 1)[1].strip()
            if len(annotation) > _ANNOTATION_CAP:
                errors.append(
                    f"structure annotation {annotation!r} length "
                    f"{len(annotation)} > {_ANNOTATION_CAP}"
                )

    for match in _CITE_RE.finditer(body):
        cite_path = match.group("path")
        # Skip a few common false positives (URL-ish patterns, dates).
        if cite_path.endswith("/") or cite_path.startswith("http"):
            continue
        resolved, mode = _resolve_cite_path(cite_path, target, project_root)
        if mode == "miss":
            errors.append(f"cite path not found: {cite_path!r}")
            continue
        try:
            line_count = len(resolved.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError as exc:
            errors.append(f"cite file unreadable {cite_path!r}: {exc}")
            continue
        for group_name in ("start", "end", "extra"):
            ln_str = match.group(group_name)
            if ln_str is None:
                continue
            try:
                ln = int(ln_str)
            except ValueError:
                continue
            if ln < 1 or ln > line_count:
                errors.append(
                    f"cite {cite_path}:{ln} out of range (file has {line_count} lines)"
                )

    return errors


def cmd_validate_doc(args: argparse.Namespace) -> int:
    """Handler for `validate-doc` subcommand. Returns CLI exit code."""
    tier = args.tier
    target = args.target
    devforge_dir = Path(args.devforge_dir)
    project_root = devforge_dir.parent.resolve()

    if tier != "concern":
        print(
            f"only tier=concern supported in this build (got tier={tier!r}); "
            f"package + project tiers ship under forthcoming F.5 expansion",
            file=sys.stderr,
        )
        return 2

    doc_path = project_root / "docs" / target / "index.md"
    errors = _validate_concern_doc(doc_path, target, project_root)
    if errors:
        for line in errors:
            print(line, file=sys.stderr)
        return 2
    return 0


def _build_validate_doc(p: argparse.ArgumentParser) -> None:
    """argparse factory for the `validate-doc` subcommand."""
    p.add_argument("--tier", required=True, choices=("concern",))
    p.add_argument(
        "--target",
        required=True,
        help="Tier target (concern: <package>/<concern>)",
    )
    p.add_argument("--devforge-dir", default=".devforge")
