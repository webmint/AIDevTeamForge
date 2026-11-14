#!/usr/bin/env python3
"""Verify the citations of a gate report or a spec against the files they cite.

Two modes. `report` checks the `path:N[-M]` citations of a gate report; `spec` checks every `path:N[-M]` citation of a
spec. The citation syntax, path resolution and quote-window rules are defined in spec_refs.py.

Usage:
  python3 scripts/forge/verify_citations.py report <gates/<gate>.md> [--root <dir>]
  python3 scripts/forge/verify_citations.py spec <spec.md> [--root <dir>]
      --root <dir>   project root that cited paths resolve against (default: the current directory)

Report mode: findings are the `### <id>` headings under `## Critical`, `## Warning` and `## Suggestion` (severity from
the section); dispositions are the `- <id>[, <id>...]: <text>` bullets under any `## Dispositions...` heading
(indented lines below one belong to it; ids may be backticked); `## Re-check` citations are attributed to the id of
their `### <id>` heading. Every citation in a finding, unquoted ones included, is checked for file and line range;
a quoted one also for its quote.
Reasons (citation-level, the failure line ends with the citation):
  file_missing, line_oob, range_too_wide (M-N > 300), quote_mismatch, quote_empty, quote_too_short (fewer than 8
  non-space characters in the quote or 3 in a fragment), quote_unclosed (an unclosed backtick run after the span).
Reasons (finding-level, the failure line ends with `-`):
  no_quoted_citation        a finding without any quoted citation
  floor_in_suggestion       a `[security-floor]` finding (tag case-insensitive) under `## Suggestion`
  floor_disposition_unverified  a `[security-floor]` finding whose last disposition word (the first token after
                            `<id>:`, `*` and backticks stripped; one of fixed, rejected, deferred, recorded,
                            accepted, unverified) is `recorded`,
                            `rejected` or `deferred` without a verified quoted citation on the disposition lines
                            that resolves to a file the finding itself cites
  floor_disposition_unparsed  a `[security-floor]` finding named on a disposition line that does not parse as a
                            disposition, or whose first token is not a disposition word
  duplicate_id              two `### <id>` headings with the same id (their floor flags are OR-ed)
  finding_not_heading       (a) a bullet, bold or heading line under a severity section that starts with a finding id
                            (`C-1`, `W-2`, `S-3`) but is not a `### ` heading; (b) a `#### <id>` heading anywhere;
                            (c) a `### <id>` heading in a section that is not a severity, re-check or disposition
                            section; (d) id `report`: any non-blank line before the first `###` heading of a severity
                            section other than `None` (once per section). `C0 W0 S0` excuses none of these.
  unclosed_fence            a fenced code block still open at the end of the report (id `report`)
  no_findings_parsed        no `## Critical|Warning|Suggestion` section and no `C0 W0 S0` line
Spec mode: every `path:N[-M]` code span, outside the `## Request (verbatim)` section: file exists and lines in
range; a quoted one also verifies its quote.
A path with several suffix matches is ambiguous: the check passes when any candidate passes (a `note` line says so).
Reviewed snapshots (report mode): a citation that resolves to the gate's own spec (`<gates dir>/../spec.md`) and to
no other file, and fails against it, is checked against each `<gates dir>/spec.reviewed-*.md` (written by
`spec_lint.py hash --record` after every review or re-check round; symlinks are skipped); it passes when one of them
verifies it, with a line `note <id> <citation> verified against the reviewed spec <file>`. A fix round moves or rewrites
spec lines the findings quoted; each snapshot is a version of the spec that a review round read, so a quote found in
any of them is a quote of a spec a reviewer saw.

Output: written to `<gates dir>/<gate>.citations.txt` (report) or `<spec dir>/gates/spec.citations.txt` (spec; `gates/`
is created) and printed: one line per failure (`<id> <reason> <citation>`; the id is the finding id, or `L<line>` in
spec mode), `note` lines for ambiguous matches, then `citations: <checked> checked, <failed> failed`.
Exit codes: 0 clean; 1 at least one failure; 2 bad arguments or an unreadable input or output file.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import sys
from typing import Dict, List, NamedTuple, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spec_refs  # noqa: E402  (sibling module; path set above)

SEVERITIES = ("critical", "warning", "suggestion")
FLOOR_TAG = "[security-floor]"
FLOOR_WORDS = ("recorded", "rejected", "deferred")
_DISPOSITION_RE = re.compile(r"^ {0,3}[-*]\s+(?P<ids>[^:]*?)\s*:\s*(?P<rest>.*)$")
_ID_TOKEN_RE = re.compile(r"^[A-Za-z][\w.\-]*$")
DISPOSITION_WORDS = ("fixed", "rejected", "deferred", "recorded", "accepted", "unverified")
_H3_RE = re.compile(r"^ {0,3}###\s")
_HEADING_ID_RE = re.compile(r"^ {0,3}###\s+[*`]*([^\s:*`]+)")
_FINDING_LINE_RE = re.compile(r"^\s*(?:(?:#{1,6}|[-*+])\s+[*`]*|\*\*|\d+[.)]\s+\*\*)(?P<id>[CWS]-\d+)\b")
_ID_HEADING_RE = re.compile(r"^ {0,3}###\s+[*`]*(?P<id>[CWS]-\d+)\b")
_NONE_LINES = ("none", "none.")
_DEEP_HEADING_RE = re.compile(r"^\s*#{4,}\s+[*`]*(?P<id>[CWS]-\d+)\b")


class Block(NamedTuple):
    ident: str
    heading: str
    lines: List[Tuple[int, str]]  # (line number, text), the heading included


def _blocks(section: spec_refs.Section) -> List[Block]:
    """The `### <id>` blocks of a section; text before the first one is a block with id ""."""
    blocks: List[Block] = []
    ident, heading, lines = "", "", []  # type: str, str, List[Tuple[int, str]]
    fence: Optional[str] = None
    for offset, text in enumerate(section.body):
        new = spec_refs.fence_update(fence, text)
        fenced = fence is not None or new is not None
        fence = new
        if not fenced and _H3_RE.match(text):
            if ident or lines:
                blocks.append(Block(ident, heading, lines))
            m = _HEADING_ID_RE.match(text)
            ident, heading, lines = (m.group(1) if m else text.strip()[3:].strip()), text, []
        lines.append((section.first + offset, text))
    if ident or any(t.strip() for _n, t in lines):
        blocks.append(Block(ident, heading, lines))
    return blocks


def _citations(lines: List[Tuple[int, str]]) -> List[spec_refs.Citation]:
    """Citations of numbered lines, with the line numbers of the original text."""
    found: List[spec_refs.Citation] = []
    for number, text in lines:
        for cit in spec_refs.iter_citations(text):
            found.append(cit._replace(line=number))
    return found


class Disposition(NamedTuple):
    ids: List[str]
    word: Optional[str]  # None: no disposition word found
    lines: List[Tuple[int, str]]


def _parse_ids(text: str) -> Optional[List[str]]:
    text = re.sub(r"\([^)]*\)", "", text)
    ids = []
    for token in re.split(r"[,&]|\band\b", text):
        token = token.strip().strip("*`").strip()
        if not _ID_TOKEN_RE.match(token):
            return None
        ids.append(token)
    return ids or None


def _dispositions(section: spec_refs.Section) -> List[Disposition]:
    """One Disposition per bullet `- <id>[, <id>]: <text>`; indented non-blank lines below it belong to it."""
    out: List[Disposition] = []
    current: Optional[Disposition] = None
    for offset, text in enumerate(section.body):
        number = section.first + offset
        m = _DISPOSITION_RE.match(text)
        ids = _parse_ids(m.group("ids")) if m else None
        if m and ids:
            tokens = m.group("rest").split()
            first = tokens[0].strip("*`").lower() if tokens else ""
            current = Disposition(ids, first if first in DISPOSITION_WORDS else None, [(number, text)])
            out.append(current)
        elif current is not None and text.strip() and text[0] in " \t":
            current.lines.append((number, text))
        else:
            current = None
    return out


def _cite_text(cit: spec_refs.Citation) -> str:
    return "%s:%d" % (cit.path, cit.start) + ("" if cit.end is None else "-%d" % cit.end)


class Result:
    def __init__(self, root: str, spec: Optional[str] = None, snapshots: Optional[List[str]] = None) -> None:
        self.root = root
        self.spec = os.path.realpath(spec) if spec else None
        self.snapshots = [s for s in (snapshots or []) if not os.path.islink(s)]
        self._snapshot_lines: Dict[str, Optional[List[str]]] = {}
        self.failures: List[str] = []
        self.notes: List[str] = []
        self.checked = 0
        self._memo: Dict[Tuple[str, int, Optional[int], Optional[str]], Tuple[Optional[str], List[str]]] = {}

    def verify_full(self, ident: str, cit: spec_refs.Citation) -> Tuple[bool, List[str]]:
        """Verify one citation, record a failure or an ambiguity note; (verified, candidate files)."""
        self.checked += 1
        if cit.unclosed:
            self.failures.append("%s quote_unclosed %s" % (ident, _cite_text(cit)))
            return False, []
        key = (cit.path, cit.start, cit.end, cit.quote)
        if key not in self._memo:
            self._memo[key] = spec_refs.verify_citation(cit, self.root)
        reason, candidates = self._memo[key]
        ambiguous = len(candidates) > 1
        if reason is None:
            if ambiguous:
                self.notes.append("note %s %s ambiguous: %d candidates, one passes" % (ident, _cite_text(cit), len(candidates)))
            return True, candidates
        snapshot = self._snapshot_match(cit, candidates)
        if snapshot is not None:
            self.notes.append("note %s %s verified against the reviewed spec %s"
                              % (ident, _cite_text(cit), os.path.basename(snapshot)))
            return True, candidates
        suffix = " (ambiguous: %d candidates, none passes)" % len(candidates) if ambiguous else ""
        self.failures.append("%s %s %s%s" % (ident, reason, _cite_text(cit), suffix))
        return False, candidates

    def _snapshot_match(self, cit: spec_refs.Citation, candidates: List[str]) -> Optional[str]:
        """The first reviewed snapshot that verifies a citation of the gate's own spec, else None."""
        if not self.spec or not self.snapshots or _real(candidates) != {self.spec}:
            return None
        for snap in self.snapshots:
            if snap not in self._snapshot_lines:
                self._snapshot_lines[snap] = spec_refs.read_lines(snap)
            lines = self._snapshot_lines[snap]
            if lines is None:
                continue
            reason = spec_refs.check_lines(len(lines), cit.start, cit.end)
            if reason is None and cit.quote is not None:
                reason = spec_refs.check_quote(lines, cit.start, cit.end, cit.quote)
            if reason is None:
                return snap
        return None

    def verify(self, ident: str, cit: spec_refs.Citation) -> bool:
        return self.verify_full(ident, cit)[0]

    def fail(self, ident: str, reason: str) -> None:
        self.failures.append("%s %s -" % (ident, reason))

    def text(self) -> str:
        lines = self.failures + self.notes
        lines.append("citations: %d checked, %d failed" % (self.checked, len(self.failures)))
        return "\n".join(lines) + "\n"


def _real(paths: List[str]) -> set:
    return {os.path.realpath(p) for p in paths}


def check_report(text: str, root: str, spec: Optional[str] = None, snapshots: Optional[List[str]] = None) -> Result:
    res = Result(root, spec, snapshots)
    sections = spec_refs.split_sections(text)
    floor: Dict[str, bool] = {}
    files: Dict[str, set] = {}  # id -> real paths of the files the finding cites
    duplicated: set = set()
    seen_severity = False
    for sec in sections:
        title = sec.title.lower()
        severity = next((s for s in SEVERITIES if title.startswith(s)), None)
        keeps_findings = severity or title.startswith(("re-check", "recheck", "disposition"))
        fence: Optional[str] = None
        in_preamble = bool(severity)
        for offset, line in enumerate(sec.body):
            new = spec_refs.fence_update(fence, line)
            fenced = fence is not None or new is not None
            fence = new
            if severity and in_preamble and not fenced and _H3_RE.match(line):
                in_preamble = False
            if severity and in_preamble and line.strip() and line.strip().strip("_*()").lower() not in _NONE_LINES:
                res.fail("report", "finding_not_heading")  # text before the first `### <id>`: once per section
                in_preamble = False
            if fenced:
                continue
            if not keeps_findings:
                m = _ID_HEADING_RE.match(line)
                if m:
                    res.fail(m.group("id"), "finding_not_heading")
                    continue
            m = _FINDING_LINE_RE.match(line) if (severity or not keeps_findings) else _DEEP_HEADING_RE.match(line)
            if m and not (severity and _H3_RE.match(line)):
                res.fail(m.group("id"), "finding_not_heading")
        if severity:
            seen_severity = True
            for block in _blocks(sec):
                if not block.ident:
                    continue
                if block.ident in floor:
                    if block.ident not in duplicated:
                        duplicated.add(block.ident)
                        res.fail(block.ident, "duplicate_id")
                is_floor = FLOOR_TAG in block.heading.lower()
                floor[block.ident] = floor.get(block.ident, False) or is_floor
                cited = files.setdefault(block.ident, set())
                quoted = 0
                for cit in _citations(block.lines):
                    if cit.quote is not None:
                        quoted += 1
                    _ok, cands = res.verify_full(block.ident, cit)
                    cited |= _real(cands)
                if not quoted:
                    res.fail(block.ident, "no_quoted_citation")
                if is_floor and severity == "suggestion":
                    res.fail(block.ident, "floor_in_suggestion")
        elif title.startswith("re-check") or title.startswith("recheck"):
            for block in _blocks(sec):
                for cit in _citations(block.lines):
                    if cit.quote is not None or cit.unclosed:
                        res.verify(block.ident or "re-check", cit)
    if not seen_severity and not any("C0 W0 S0" in line for line in text.split("\n")):
        res.fail("report", "no_findings_parsed")
    fence = None
    for line in text.split("\n"):
        fence = spec_refs.fence_update(fence, line)
    if fence is not None:
        res.fail("report", "unclosed_fence")
    last: Dict[str, Tuple[Optional[str], List[set]]] = {}  # id -> (word, real files of verified quoted citations)
    unparsed: set = set()
    for sec in sections:
        if not sec.title.lower().startswith("disposition"):
            continue
        covered = set()
        for disp in _dispositions(sec):
            covered.update(n for n, _t in disp.lines)
            verified: List[set] = []
            for cit in _citations(disp.lines):
                if cit.quote is not None or cit.unclosed:
                    ok, cands = res.verify_full(disp.ids[0], cit)
                    if ok:
                        verified.append(_real(cands))
            for ident in disp.ids:
                last[ident] = (disp.word, verified)
                if floor.get(ident) and disp.word is None:
                    unparsed.add(ident)
        for ident in floor:
            if not floor[ident]:
                continue
            pat = re.compile(r"(?<![\w-])%s(?![\w-])" % re.escape(ident))
            for offset, line in enumerate(sec.body):
                if sec.first + offset not in covered and pat.search(line):
                    unparsed.add(ident)
    for ident in floor:
        if not floor[ident]:
            continue
        if ident in unparsed:
            res.fail(ident, "floor_disposition_unparsed")
            continue
        if ident not in last:
            continue
        word, verified = last[ident]
        if word in FLOOR_WORDS and not any(v & files[ident] for v in verified):
            res.fail(ident, "floor_disposition_unverified")
    return res


def check_spec(text: str, root: str) -> Result:
    res = Result(root)
    for sec in spec_refs.split_sections(text):
        if sec.title.lower().startswith("request (verbatim)"):
            continue
        for cit in _citations([(sec.first + i, t) for i, t in enumerate(sec.body)]):
            res.verify("L%d" % cit.line, cit)
    return res


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Verify the citations of a gate report or a spec.")
    parser.add_argument("mode", choices=("report", "spec"))
    parser.add_argument("file", help="gates/<gate>.md (report) or spec.md (spec)")
    parser.add_argument("--root", default=os.getcwd(), help="project root (default: the current directory)")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    path = os.path.abspath(args.file)
    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        print("error: --root is not a directory: %s" % root, file=sys.stderr)
        return 2
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError as exc:
        print("error: cannot read %s: %s" % (path, exc), file=sys.stderr)
        return 2
    if args.mode == "report":
        out_dir = os.path.dirname(path)
        spec = os.path.join(os.path.dirname(out_dir), "spec.md")
        snapshots = sorted(glob.glob(os.path.join(out_dir, "spec.reviewed-*.md")))
        res = check_report(text, root, spec if os.path.isfile(spec) else None, snapshots)
        out_path = os.path.join(out_dir, os.path.splitext(os.path.basename(path))[0] + ".citations.txt")
    else:
        res = check_spec(text, root)
        out_dir = os.path.join(os.path.dirname(path), "gates")
        out_path = os.path.join(out_dir, "spec.citations.txt")
    output = res.text()
    try:
        spec_refs.atomic_write(out_path, output)
    except OSError as exc:
        print("error: cannot write %s: %s" % (out_path, exc), file=sys.stderr)
        return 2
    sys.stdout.write(output)
    return 1 if res.failures else 0


if __name__ == "__main__":
    sys.exit(main())
