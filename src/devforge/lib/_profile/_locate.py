"""_locate.py -- transcript filesystem location for profile_helper.

A project's Claude Code harness transcripts live at
`~/.claude/projects/<encoded-cwd>/<uuid>.jsonl`, where `<encoded-cwd>` is
the project's absolute root path with every "/" replaced by "-" (verified
2026-08-05/07, see 70-PIPELINE-WALLCLOCK-PROFILING-PLAN.md Empirical
Grounding).  This module resolves that directory and picks the
most-recently-modified transcript when the caller passes neither
`--transcript` nor `--dir`.

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import os
from typing import List, Optional


def encode_cwd(abs_cwd):
    # type: (str) -> str
    """Encode an absolute project path the way the harness names its
    transcript directory: every "/" becomes "-".
    """
    return abs_cwd.replace("/", "-")


def default_transcripts_dir(cwd=None):
    # type: (Optional[str]) -> str
    """Return the harness transcript directory for the given (or current)
    working directory: ~/.claude/projects/<encoded-abs-cwd>/
    """
    resolved_cwd = os.path.realpath(cwd) if cwd else os.path.realpath(os.getcwd())
    encoded = encode_cwd(resolved_cwd)
    home = os.path.expanduser("~")
    return os.path.join(home, ".claude", "projects", encoded)


def list_transcripts_by_mtime(dir_path):
    # type: (str) -> List[str]
    """Return the top-level *.jsonl files in dir_path, sorted by mtime
    ascending (oldest first).  Empty list when dir_path is missing/empty.
    """
    if not os.path.isdir(dir_path):
        return []
    candidates = []
    for name in os.listdir(dir_path):
        if not name.endswith(".jsonl"):
            continue
        full = os.path.join(dir_path, name)
        if os.path.isfile(full):
            candidates.append(full)
    candidates.sort(key=lambda p: os.path.getmtime(p))
    return candidates


def find_latest_transcript(dir_path):
    # type: (str) -> Optional[str]
    """Return the most-recently-modified *.jsonl in dir_path, or None."""
    candidates = list_transcripts_by_mtime(dir_path)
    return candidates[-1] if candidates else None
