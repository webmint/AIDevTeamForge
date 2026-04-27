"""Minimal frontmatter parser for AIDevTeamForge templates.

Handles the subset of YAML-ish frontmatter used in src/commands/*.md and
src/agents/*.md:

    ---
    name: architect
    description: "long quoted string, possibly with \\n escapes"
    model_tier: think
    ---
    <body>

Stdlib only — no PyYAML dependency. We never interpret escape sequences in
values; quoted strings are returned with outer quotes stripped but internal
content preserved verbatim. That's sufficient: pass-through to Claude outputs.
"""

from __future__ import annotations
from typing import Dict, Tuple


def parse(text: str) -> Tuple[Dict[str, str], str, str]:
    """Split a markdown file into (frontmatter_dict, body, raw_frontmatter_block).

    If there is no frontmatter, returns ({}, text, "").

    frontmatter_dict values are strings with surrounding quotes stripped but
    no escape interpretation. Order of keys is preserved (Python 3.7+ dicts
    are insertion-ordered).

    raw_frontmatter_block is the frontmatter section including the opening
    and closing '---' lines and the trailing newline, useful for pass-through
    emission where we don't need to reparse.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\n") != "---":
        return {}, text, ""

    # Find closing --- line
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\n") == "---":
            end_idx = i
            break
    if end_idx is None:
        # Opens but never closes — treat as no frontmatter
        return {}, text, ""

    raw = "".join(lines[: end_idx + 1])
    body = "".join(lines[end_idx + 1 :])
    # Strip leading newline from body if present (common after closing ---)
    if body.startswith("\n"):
        body = body[1:]

    fm: Dict[str, str] = {}
    for line in lines[1:end_idx]:
        line = line.rstrip("\n")
        if not line.strip():
            continue
        if line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Strip surrounding quotes and interpret escape sequences.
        # Double-quoted YAML strings support \n, \t, \r, \\, \".
        # Single-quoted strings treat backslashes literally.
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = _unescape_double_quoted(value[1:-1])
        elif len(value) >= 2 and value[0] == value[-1] == "'":
            value = value[1:-1]
        fm[key] = value
    return fm, body, raw


def _unescape_double_quoted(s: str) -> str:
    """Interpret the small subset of YAML double-quoted escape sequences we use.

    Supported: \\n \\t \\r \\\\ \\" \\'. Unknown escapes are preserved verbatim
    (e.g. \\x becomes literal backslash-x) so source is not corrupted.
    """
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt == "n":
                out.append("\n")
            elif nxt == "t":
                out.append("\t")
            elif nxt == "r":
                out.append("\r")
            elif nxt == '"':
                out.append('"')
            elif nxt == "'":
                out.append("'")
            elif nxt == "\\":
                out.append("\\")
            else:
                out.append(s[i : i + 2])
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def dump(fm: Dict[str, str], body: str) -> str:
    """Serialize frontmatter dict + body back into markdown text.

    Values containing special chars (colons, quotes, leading/trailing space,
    or multi-line) get double-quoted. We don't escape internal quotes — source
    frontmatter is expected to use already-escaped forms. Good enough for
    pass-through emission where the input was already well-formed.
    """
    out = ["---\n"]
    for key, value in fm.items():
        if _needs_quoting(value):
            out.append(f'{key}: "{value}"\n')
        else:
            out.append(f"{key}: {value}\n")
    out.append("---\n")
    if body and not body.startswith("\n"):
        out.append("\n")
    out.append(body)
    return "".join(out)


def _needs_quoting(value: str) -> bool:
    if not value:
        return True
    if value[0] in " \t" or value[-1] in " \t":
        return True
    if any(ch in value for ch in (":", "#", "\n")):
        return True
    return False


def strip_frontmatter(text: str) -> str:
    """Return the body only, with frontmatter (if any) removed."""
    _, body, _ = parse(text)
    return body
