"""Tests for src/devforge/lib/_profile/_cli.py -- end-to-end via main().

Coverage:
  run --transcript          -- prints a coherent table + writes storage.
  run --no-store             -- skips storage entirely.
  run --dir                  -- stitches two *.jsonl files by mtime into
                                 one chain.
  run --transcript + --dir   -- mutually exclusive, exit 2.
  run missing transcript     -- exit 2, no storage written.
  run empty --dir             -- exit 2.
  run auto-locate (neither given) -- exit 2 with a clear "not found"
                                 message when no transcript dir exists
                                 under the given --workspace-root's
                                 encoded project path (never touches the
                                 real ~/.claude/projects -- the tmp_path
                                 project root does not exist there).
  aggregate no runs           -- exit 2.
  aggregate with runs         -- exit 0, prints per-command table.
  main() with no subcommand   -- prints help, returns 2.

All storage is scoped to tmp_path via --workspace-root; nothing under the
real ~/.claude or the developer's own .devforge/ is read or written.
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_TESTS_DIR = Path(__file__).resolve().parent

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

from _profile._cli import main  # noqa: E402

from _fixtures import (  # noqa: E402
    assistant_text_line,
    assistant_tooluse_line,
    command_marker_text,
    user_text_line,
    user_toolresult_line,
    write_jsonl,
)


def _sample_lines(session_id="sess1"):
    return [
        user_text_line(0, command_marker_text("/plan"), session_id=session_id),
        assistant_tooluse_line(1, "toolu_1", "Bash", command="plan_helper preflight", session_id=session_id),
        user_toolresult_line(3, "toolu_1", session_id=session_id),
    ]


def _run_cli(argv):
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


# ---------------------------------------------------------------------------
# run --transcript
# ---------------------------------------------------------------------------


def test_run_transcript_prints_table_and_writes_storage(tmp_path):
    transcript = tmp_path / "sess1.jsonl"
    write_jsonl(str(transcript), _sample_lines())
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    code, out, err = _run_cli([
        "run", "--transcript", str(transcript), "--workspace-root", str(workspace),
    ])

    assert code == 0, err
    assert "plan" in out
    assert "TOTAL" in out
    assert "Wrote" in out

    profile_dir = workspace / ".devforge" / "profile"
    json_files = list(profile_dir.glob("*.json"))
    assert len(json_files) == 1
    assert (profile_dir / "summary.md").is_file()

    with open(json_files[0], "r", encoding="utf-8") as fh:
        record = json.load(fh)
    assert record["schema_version"] == 1
    assert record["segments"][0]["command"] == "plan"


def test_run_no_store_skips_storage(tmp_path):
    transcript = tmp_path / "sess1.jsonl"
    write_jsonl(str(transcript), _sample_lines())
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    code, out, err = _run_cli([
        "run", "--transcript", str(transcript), "--workspace-root", str(workspace), "--no-store",
    ])

    assert code == 0, err
    assert "Wrote" not in out
    profile_dir = workspace / ".devforge" / "profile"
    assert not profile_dir.exists()


# ---------------------------------------------------------------------------
# run --dir
# ---------------------------------------------------------------------------


def test_run_dir_stitches_two_files_by_mtime(tmp_path):
    transcripts_dir = tmp_path / "transcripts"
    transcripts_dir.mkdir()
    early = transcripts_dir / "early.jsonl"
    later = transcripts_dir / "later.jsonl"

    write_jsonl(str(early), [
        user_text_line(0, command_marker_text("/plan"), session_id="early"),
        assistant_text_line(1, "planning", session_id="early"),
    ])
    time.sleep(0.02)
    write_jsonl(str(later), [
        # /clear starts a new transcript file in real usage; here the second
        # file simply continues the chain with its own command.
        user_text_line(0, command_marker_text("/breakdown"), session_id="later"),
        assistant_text_line(1, "breaking down", session_id="later"),
    ])

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    code, out, err = _run_cli([
        "run", "--dir", str(transcripts_dir), "--workspace-root", str(workspace),
    ])

    assert code == 0, err
    assert "plan" in out
    assert "breakdown" in out


def test_run_transcript_and_dir_mutually_exclusive(tmp_path):
    transcript = tmp_path / "sess1.jsonl"
    write_jsonl(str(transcript), _sample_lines())
    code, out, err = _run_cli([
        "run", "--transcript", str(transcript), "--dir", str(tmp_path),
    ])
    assert code == 2
    assert "mutually exclusive" in err


def test_run_missing_transcript_file(tmp_path):
    code, out, err = _run_cli([
        "run", "--transcript", str(tmp_path / "does-not-exist.jsonl"),
    ])
    assert code == 2
    assert "not found" in err


def test_run_empty_dir(tmp_path):
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    code, out, err = _run_cli(["run", "--dir", str(empty_dir)])
    assert code == 2
    assert "no *.jsonl files found" in err


def test_run_auto_locate_no_transcript_dir(tmp_path):
    # tmp_path's own path is virtually guaranteed to have no corresponding
    # entry under the REAL ~/.claude/projects/ -- this only reads (never
    # writes) that location, and only to confirm absence.
    project_root = tmp_path / "some-project-that-does-not-exist-anywhere"
    project_root.mkdir()
    code, out, err = _run_cli(["run", "--workspace-root", str(project_root)])
    assert code == 2
    assert "no transcript directory found" in err


# ---------------------------------------------------------------------------
# aggregate
# ---------------------------------------------------------------------------


def test_aggregate_no_runs(tmp_path):
    code, out, err = _run_cli(["aggregate", "--workspace-root", str(tmp_path)])
    assert code == 2
    assert "no stored runs found" in err


def test_aggregate_with_stored_runs(tmp_path):
    transcript = tmp_path / "sess1.jsonl"
    write_jsonl(str(transcript), _sample_lines())
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    code, _, err = _run_cli([
        "run", "--transcript", str(transcript), "--workspace-root", str(workspace),
    ])
    assert code == 0, err

    code, out, err = _run_cli(["aggregate", "--workspace-root", str(workspace)])
    assert code == 0, err
    assert "Aggregated across 1 stored run(s)" in out
    assert "plan" in out


# ---------------------------------------------------------------------------
# main() with no subcommand
# ---------------------------------------------------------------------------


def test_main_no_subcommand_prints_help_and_returns_2():
    code, out, err = _run_cli([])
    assert code == 2
    assert "usage" in err.lower()
