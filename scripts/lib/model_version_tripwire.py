"""model_version_tripwire.py — maintainer-side model-version-string tripwire.

Problem this module addresses
------------------------------
Plan 92 (D3) makes the framework's model choice VERSION-FREE: `src/` stores
only Claude Code aliases (`opus`, `sonnet`, `haiku`, `fable`) or a
consumer-owned pin, never a priced, dated, version-bound model identifier.
Version-freedom is only real if it is FALSIFIABLE — this module is the
mechanized check, in the shape of `scripts/lib/memory_lane.py`'s standing
maintainer gate (a live-`src/` test IS the gate; there is no CI wiring).

Two patterns, BOTH required
----------------------------
  - API-ID shape:        ``claude-[a-z]+-[0-9]``
    (e.g. ``claude-opus-5``, ``claude-sonnet-4-5``)
  - display-name shape:  ``\\b(opus|sonnet|haiku|fable)[\\s-]+[0-9]``
    (case-insensitive; separator is whitespace OR hyphen, one or more; e.g.
    ``Opus 5``, ``Haiku 4.5``, ``Fable 5.1``, ``sonnet-4-5``, ``Sonnet - 5``)

The API-ID pattern alone is NOT enough: it catches `claude-opus-5` and
misses `Opus 5` — the prose shape a well-meaning author writes into a
question, a rationale, or a `CHANGELOG` line. The display-name pattern's
separator is deliberately `[\\s-]+`, not `\\s+` alone: a bare `\\s+`
separator misses a hyphen-joined pseudo-version like `sonnet-4-5`, which
also slips the API-ID pattern (no `claude-` prefix) — so an unwidened
display-name pattern would have been the one gap neither pattern covered.
`tests/lib/test_model_version_tripwire.py` proves every shape is caught
with SEPARATE planted-string tests (whitespace-separated, hyphen-joined,
and spaced-hyphen) — a test that only proves the whitespace-separated form
passes the plan's Verify bullet by a fraction and leaves the others
unproven.

Public API
----------
Finding
    A `typing.NamedTuple` — `(path, line, text, pattern)`: `path` is
    POSIX-relative to the scanned root; `line` is 1-based; `text` is the
    matched substring; `pattern` is `"api-id"` or `"display-name"`.

find_version_strings(root) -> List[Finding]
    Scan every regular file under `root` (a path-like or str) and return a
    `Finding` for every match of either pattern. Directories named
    `__pycache__` are skipped entirely. Walks via `os.walk(root,
    followlinks=False)` rather than `Path.rglob` — `rglob` follows
    symlinked directories on Python < 3.13 and can loop forever on a
    symlink cycle; `os.walk` with `followlinks=False` lists a symlinked
    directory once in its parent's entries but never descends into it, so
    a cycle terminates instead of recursing. `dirnames` and `filenames` are
    both sorted for deterministic traversal order. A file that cannot be
    decoded as UTF-8 is read with `errors="ignore"` rather than skipped
    outright — stray undecodable bytes are dropped silently, which is
    enough to avoid a crash on a binary file without needing an extension
    allowlist.

main(argv=None) -> int
    CLI entry point, mirroring `memory_lane.py` + `verify-memory-lane.py`'s
    report shape (this module folds both into one file — no separate
    `scripts/verify-*.py` launcher ships with this change). Exit 0 on zero
    findings, exit 1 with every finding listed on stdout, exit 2 if the
    given root is not a directory.

Usage
-----
    python3 scripts/lib/model_version_tripwire.py [<root>]

If `<root>` is omitted, this repo's `src/` directory is scanned (this file
lives at `scripts/lib/`, two parents up from the repo root).

Stdlib only. Targets Python 3.8+.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import List, NamedTuple

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# The API-ID shape: a hyphenated `claude-<word>-<digit>` token, e.g.
# "claude-opus-5". Lowercase only — API model IDs are always lowercase.
API_ID_RE = re.compile(r"claude-[a-z]+-[0-9]")

# The display-name-with-version shape: one of the four tier aliases
# immediately followed by a separator and a digit, e.g. "Opus 5",
# "Haiku 4.5", "sonnet-4-5", "Sonnet - 5". The separator is `[\s-]+`
# (whitespace OR hyphen, one or more) rather than `\s+` alone: a bare
# whitespace-only separator misses a hyphen-joined pseudo-version like
# "sonnet-4-5", which also has no `claude-` prefix to be caught by
# API_ID_RE — the one shape neither pattern would otherwise cover.
# Case-insensitive — this is exactly the prose shape a human writes.
DISPLAY_NAME_RE = re.compile(
    r"\b(opus|sonnet|haiku|fable)[\s-]+[0-9]", re.IGNORECASE
)

_SKIP_DIR_NAMES = frozenset({"__pycache__"})


class Finding(NamedTuple):
    path: str
    line: int
    text: str
    pattern: str


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------

def find_version_strings(root):
    # type: (object) -> List[Finding]
    """Scan every regular file under `root` for either version-string shape.

    `root` may be a `Path` or a str; both are accepted since callers (CLI
    argv, test fixtures) commonly hand this a plain string.

    Walks via `os.walk(root, followlinks=False)`, NOT `Path.rglob` — see
    the module docstring's `find_version_strings` entry for why: `rglob`
    follows symlinked directories on Python < 3.13 and can recurse forever
    on a symlink cycle, while `os.walk(followlinks=False)` lists a
    symlinked directory once and never descends into it, so a cycle
    terminates. `dirnames` and `filenames` are both sorted in place for
    deterministic traversal order.
    """
    root = Path(root)
    findings = []  # type: List[Finding]

    for dirpath, dirnames, filenames in os.walk(str(root), followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIR_NAMES)
        for filename in sorted(filenames):
            path = Path(dirpath) / filename
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            rel = path.relative_to(root).as_posix()
            for lineno, line in enumerate(text.splitlines(), start=1):
                api_match = API_ID_RE.search(line)
                if api_match:
                    findings.append(
                        Finding(rel, lineno, api_match.group(0), "api-id")
                    )
                display_match = DISPLAY_NAME_RE.search(line)
                if display_match:
                    findings.append(
                        Finding(rel, lineno, display_match.group(0), "display-name")
                    )

    return findings


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    # type: (object) -> int
    if argv is None:
        argv = sys.argv[1:]

    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    if argv:
        root = Path(argv[0])
    else:
        # scripts/lib/model_version_tripwire.py -> scripts/lib -> scripts
        # -> repo root -> src
        root = Path(__file__).resolve().parent.parent.parent / "src"

    if not root.is_dir():
        sys.stderr.write("error: '{}' is not a directory\n".format(root))
        return 2

    findings = find_version_strings(root)

    print("Model-version-string tripwire")
    print("Root      : {}".format(root))
    print("Scope     : forbids two version-bound shapes anywhere under this root — the")
    print("            API-ID shape (claude-[a-z]+-[0-9]) and the display-name-with-")
    print("            version shape (opus|sonnet|haiku|fable followed by whitespace")
    print("            and/or a hyphen, then a digit, case-insensitive — catches both")
    print("            'Opus 5' and 'sonnet-4-5') — so a model choice stays alias-only")
    print("            and the framework never needs an update for a new version (plan")
    print("            92 D3).")
    print()

    if findings:
        print("FAIL — {} version-string finding(s):".format(len(findings)))
        for f in findings:
            print("  - {}:{}  [{}]  {!r}".format(f.path, f.line, f.pattern, f.text))
        print()
        print("Result: FAIL ({} finding(s))".format(len(findings)))
        return 1

    print("PASS — no version-bound model string found under {}.".format(root))
    print()
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
