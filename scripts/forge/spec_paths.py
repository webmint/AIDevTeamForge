#!/usr/bin/env python3
"""Reviewer inputs for the spec-gate: the repository files a spec cites, so the reviewer reads them first.

Collects every repository path the spec names (and the paths in the /specify run report's `## Sources read`), resolves
them against the project, and writes one file with the four sections the spec-gate reviewer is given.

Usage:
  python3 scripts/forge/spec_paths.py <feature-dir> [--run-report <path>] [--root <dir>]
      --root <dir>        project root; the feature dir and cited paths resolve against it (default: the current dir)
      --run-report <path> the /specify run report (default: `<feature-dir>/runs/specify.md` when it exists)

Paths: every token of the spec (all sections except `## Request (verbatim)`) with a `/` or a file extension containing a
letter, optionally followed by `:N[-M]` (and `, N-M` continuations); URLs are dropped; a token ending in `/` is a
directory and is dropped, and so is a single `/word` (a slash command). Resolution: `<feature-dir>/<token>` first,
then spec_refs.resolve (root, SOURCE_ROOT, then unique path suffix). Files are de-duplicated by resolved file and keep
every cited line range (`10-20` and `10–20`). A token with several suffix matches lists up to MAX_AMBIGUOUS files,
each marked `(one of N matches for <token>)`; more than that is one `ambiguous` line.

Output: `<feature-dir>/gates/reviewer-inputs.txt`, printed too, with the sections `## Files to verify`,
`## Cited but not found` (only tokens with a `/` that have a file extension or sit in a code span, and do not
resolve to a directory under the root or SOURCE_ROOT; an npm `@scope/name` is never listed),
`## Author's notes on validation and normalisation` (spec and run report lines that mention validat*,
normalis*/normaliz*, canonical*, trim, case, slash, encod*, unicode, default, sanitis*/sanitiz*, path or key; a line
longer than MAX_NOTE characters is cut) and `## Security focus` (fixed text).
Exit codes: 0 written; 2 bad arguments, an unreadable input (a run report that exists but cannot be read included)
or an unwritable output.
Stdlib only; Python 3.9+.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_refs  # noqa: E402  (sibling module; path set above)

MAX_AMBIGUOUS = 3
MAX_NOTE = 400

_URL_RE = re.compile(r"(?:https?|ftp)://\S+|www\.\S+", re.IGNORECASE)
_TOKEN_RE = re.compile(
    r"(?<![\w@~.\-/])([\w@~.\-/]+?)(?::(\d+(?:[-–]\d+)?(?:,\s*\d+(?:[-–]\d+)?(?![\w]))*))?(?![\w@~\-/])(?!\.\w)")
_EXT_RE = re.compile(r"\.[A-Za-z][A-Za-z0-9]*$")
_NOTES_RE = re.compile(
    r"validat|normali[sz]|canonical|\btrim|\bcase\b|slash|encod|unicode|default|sanitis|sanitiz|\bpath\b|\bkey\b",
    re.IGNORECASE)
_SCOPED_RE = re.compile(r"^@[\w-]+/[\w.-]+$")
_NOT_PATHS = frozenset({"e.g", "i.e", "etc", "vs"})

SECURITY_FOCUS = (
    "Authorisation and access scope. For every identifier that comes from a request or a token, trace both its "
    "access-check use and its data-addressing use through the whole validator, normaliser, path builder and DAO, "
    "callees included, and report any place where the two uses see a different value (trim, case, slashes, encoding, "
    "Unicode, defaults)."
)


class PathsError(Exception):
    """Bad input or an unreadable / unwritable file: exit code 2."""


def extract_tokens(text: str) -> List[Tuple[str, str, bool]]:
    """(token, line ranges text, inside a code span) of the repository paths in the text, in order of appearance."""
    found: List[Tuple[str, str, bool]] = []
    for raw in _URL_RE.sub(lambda u: " " * len(u.group()), text).split("\n"):
        spans = [(a, b) for a, b, _c in spec_refs.code_spans(raw)]
        for m in _TOKEN_RE.finditer(raw):
            token = m.group(1).rstrip(".,;")
            if not token or token.endswith("/") or token.lower() in _NOT_PATHS:
                continue
            if "/" not in token and not _EXT_RE.search(token):
                continue
            if token.startswith("/") and token.count("/") == 1 and not _EXT_RE.search(token):
                continue  # a slash command (`/plan`) or a collection name, not a file
            if "//" in token or not re.search(r"[A-Za-z]", token):
                continue
            found.append((token, m.group(2) or "", any(a <= m.start(1) < b for a, b in spans)))
    return found


def _ranges(text: str) -> List[Tuple[int, int]]:
    out = []
    for part in re.split(r",\s*", text):
        if not part:
            continue
        a, _, b = part.replace("–", "-").partition("-")
        out.append((int(a), int(b) if b else int(a)))
    return out


def _spec_text_without_request(text: str) -> str:
    keep = [s for s in spec_refs.split_sections(text) if not s.title.lower().startswith("request")]
    return "\n".join(line for s in keep for line in ([("## " + s.title)] if s.title else []) + s.body)


def _section_body(text: str, title_prefix: str) -> str:
    for section in spec_refs.split_sections(text):
        if section.title.lower().startswith(title_prefix):
            return "\n".join(section.body)
    return ""


def _read(path: str) -> str:
    lines = spec_refs.read_lines(path)
    if lines is None:
        raise PathsError("cannot read {}".format(path))
    return "\n".join(lines)


def _label(path: str, root: str) -> str:
    rel = os.path.relpath(path, root)
    return path if rel.startswith("..") else rel.replace(os.sep, "/")


def _notes(lines: List[str], label: str, skip_request: bool = False) -> List[str]:
    out: List[str] = []
    in_request = False
    for number, line in enumerate(lines, 1):
        if line.startswith("## "):
            in_request = skip_request and line[3:].strip().lower().startswith("request")
        if in_request or not _NOTES_RE.search(line):
            continue
        text = " ".join(line.split())
        if len(text) > MAX_NOTE:
            text = text[:MAX_NOTE] + "..."
        out.append("{}:{}: {}".format(label, number, text))
    return out


def build(feature: str, root: str, run_report: Optional[str]) -> str:
    spec_path = os.path.join(feature, "spec.md")
    spec_lines = spec_refs.read_lines(spec_path)
    if spec_lines is None:
        raise PathsError("cannot read {}".format(spec_path))
    tokens = extract_tokens(_spec_text_without_request("\n".join(spec_lines)))
    report_lines: List[str] = []
    if run_report:
        loaded = spec_refs.read_lines(run_report)
        if loaded is None:
            raise PathsError("cannot read {}".format(run_report))
        report_lines = loaded
        tokens += extract_tokens(_section_body("\n".join(report_lines), "sources read"))

    try:
        src_root: Optional[str] = spec_refs.quality_profile.source_root(root)
    except spec_refs.quality_profile.ProfileError:
        src_root = None
    files: Dict[str, List[Tuple[int, int]]] = {}
    marks: Dict[str, List[str]] = {}
    ambiguous: List[str] = []
    missing: List[str] = []
    for token, ranges, in_code in tokens:
        local = os.path.join(feature, token)
        if not os.path.isabs(token) and os.path.isfile(local) and os.path.realpath(local).startswith(
                os.path.realpath(root) + os.sep):
            candidates = [local]  # relative to the feature dir (`brief.md`, `research/x.md`) before the suffix search
        else:
            candidates = spec_refs.resolve(token, root)
        if not candidates:
            rel = token[2:] if token.startswith("./") else token
            is_dir = any(os.path.isdir(os.path.join(base, rel)) for base in (root, src_root) if base)
            if _SCOPED_RE.match(token):
                continue  # an npm package name, not a file
            if "/" in token and (in_code or _EXT_RE.search(token)) and not is_dir and token not in missing:
                missing.append(token)
            continue
        if len(candidates) > MAX_AMBIGUOUS:
            note = "{} ambiguous: {} files match".format(token, len(candidates))
            if note not in ambiguous:
                ambiguous.append(note)
            continue
        for cand in candidates:
            files.setdefault(cand, []).extend(_ranges(ranges))
            if len(candidates) > 1:
                mark = "(one of {} matches for {})".format(len(candidates), token)
                if mark not in marks.setdefault(cand, []):
                    marks[cand].append(mark)

    out = ["## Files to verify", ""]
    for cand in sorted(files, key=lambda c: _label(c, root)):
        merged = sorted(set(files[cand]))
        cited = ", ".join(str(a) if a == b else "{}-{}".format(a, b) for a, b in merged)
        out.append("- {}{}{}".format(_label(cand, root), " (lines {})".format(cited) if cited else "",
                                     "".join(" " + m for m in marks.get(cand, []))))
    out += ["- {}".format(a) for a in ambiguous]
    if not files and not ambiguous:
        out.append("(none)")
    out += ["", "## Cited but not found", ""] + (["- {}".format(m) for m in missing] or ["(none)"])
    notes = _notes(spec_lines, _label(spec_path, root), skip_request=True)
    if report_lines:
        notes += _notes(report_lines, _label(run_report or "", root))
    out += ["", "## Author's notes on validation and normalisation", ""] + (notes or ["(none)"])
    out += ["", "## Security focus", "", SECURITY_FOCUS]
    return "\n".join(out) + "\n"


def _write(path: str, text: str) -> None:
    try:
        spec_refs.atomic_write(path, text)
    except OSError as err:
        raise PathsError("cannot write {}: {}".format(path, err))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="spec_paths.py", description="Reviewer inputs for the spec-gate")
    parser.add_argument("feature_dir")
    parser.add_argument("--run-report", default=None, help="the /specify run report (default: runs/specify.md)")
    parser.add_argument("--root", default=".", help="project root (default: the current directory)")
    args = parser.parse_args(argv)
    root = os.path.abspath(args.root)
    feature = os.path.join(root, args.feature_dir)
    report = args.run_report
    if report is None:
        default = os.path.join(feature, "runs", "specify.md")
        report = default if os.path.isfile(default) else None
    elif not os.path.isabs(report):
        report = os.path.join(root, report)
    try:
        text = build(feature, root, report)
        _write(os.path.join(feature, "gates", "reviewer-inputs.txt"), text)
    except PathsError as err:
        sys.stderr.write("spec_paths: {}\n".format(err))
        return 2
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
