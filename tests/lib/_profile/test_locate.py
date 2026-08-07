"""Tests for src/devforge/lib/_profile/_locate.py.

Coverage:
  encode_cwd                  -- "/" -> "-" encoding.
  default_transcripts_dir     -- resolves relative to a given cwd, under
                                 ~/.claude/projects/.
  list_transcripts_by_mtime   -- sorted ascending, ignores non-.jsonl files
                                 and subdirectories, empty on missing dir.
  find_latest_transcript      -- picks the most-recently-modified file.

Never touches the real ~/.claude -- default_transcripts_dir is always
called with an explicit tmp_path-derived cwd in these tests.
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _profile._locate import (  # noqa: E402
    default_transcripts_dir,
    encode_cwd,
    find_latest_transcript,
    list_transcripts_by_mtime,
)


def test_encode_cwd_replaces_slashes():
    assert encode_cwd("/Users/me/Projects/foo") == "-Users-me-Projects-foo"


def test_default_transcripts_dir_shape(tmp_path):
    project_dir = tmp_path / "myproject"
    project_dir.mkdir()
    result = default_transcripts_dir(str(project_dir))
    encoded = encode_cwd(os.path.realpath(str(project_dir)))
    home = os.path.expanduser("~")
    expected = os.path.join(home, ".claude", "projects", encoded)
    assert result == expected


def test_list_transcripts_by_mtime_missing_dir():
    assert list_transcripts_by_mtime("/nonexistent/dir/at/all") == []


def test_list_transcripts_by_mtime_sorted_ascending(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    a.write_text("")
    time.sleep(0.02)
    b.write_text("")
    result = list_transcripts_by_mtime(str(tmp_path))
    assert result == [str(a), str(b)]


def test_list_transcripts_by_mtime_ignores_non_jsonl_and_dirs(tmp_path):
    jsonl = tmp_path / "real.jsonl"
    jsonl.write_text("")
    (tmp_path / "notes.txt").write_text("")
    subdir = tmp_path / "sess1"
    subdir.mkdir()
    result = list_transcripts_by_mtime(str(tmp_path))
    assert result == [str(jsonl)]


def test_find_latest_transcript_picks_most_recent(tmp_path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    a.write_text("")
    time.sleep(0.02)
    b.write_text("")
    assert find_latest_transcript(str(tmp_path)) == str(b)


def test_find_latest_transcript_empty_dir_returns_none(tmp_path):
    assert find_latest_transcript(str(tmp_path)) is None


def test_find_latest_transcript_missing_dir_returns_none():
    assert find_latest_transcript("/nonexistent/dir/at/all") is None
