"""argparse parser + dispatch + main entry for profile_helper.

build_parser composes the top-level + subparsers.
_register_subcommands attaches each cmd_* handler via set_defaults(func=...).
main parses argv + dispatches (prints help + returns 2 when no subcommand).

Two verbs:
  run        -- profile one transcript (--transcript), a mtime-stitched
                chain (--dir), or the auto-located latest transcript for
                --workspace-root's project; prints the report table and
                (unless --no-store) writes .devforge/profile/ storage.
  aggregate  -- read every stored .devforge/profile/*.json run and print
                the cross-run verdict table (OQ5).

The profiler is a diagnostic, not a gate (D7 -- no pass/fail semantics):
`run` and `aggregate` exit 0 whenever they produce a report, regardless of
what the numbers say.  Exit 2 is reserved for "could not produce a report
at all" (bad args, no transcript found, unreadable input).
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from ._bucket import compute_totals, profile_events
from ._locate import default_transcripts_dir, find_latest_transcript, list_transcripts_by_mtime
from ._parse import parse_transcript_chain
from ._report import render_aggregate_table, render_table
from ._storage import aggregate_runs, append_summary, build_run_record, write_run


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


def _resolve_input_paths(transcript, transcript_dir, workspace_root):
    # type: (Optional[str], Optional[str], str) -> tuple
    """Resolve the list of transcript file paths to profile.

    Returns (paths, error_message).  error_message is None on success;
    paths is [] when error_message is set.
    """
    if transcript and transcript_dir:
        return [], "--transcript and --dir are mutually exclusive"

    if transcript:
        if not os.path.isfile(transcript):
            return [], "transcript not found: {0!r}".format(transcript)
        return [transcript], None

    if transcript_dir:
        paths = list_transcripts_by_mtime(transcript_dir)
        if not paths:
            return [], "no *.jsonl files found in {0!r}".format(transcript_dir)
        return paths, None

    auto_dir = default_transcripts_dir(workspace_root)
    latest = find_latest_transcript(auto_dir)
    if not latest:
        return [], (
            "no transcript directory found at {0!r}. "
            "Pass --transcript <path> or --dir <dir> explicitly.".format(auto_dir)
        )
    return [latest], None


def _extract_harness_version(events):
    # type: (List) -> str
    for ev in reversed(events):
        if ev.get("version"):
            return ev["version"]
    return ""


def cmd_run(args):
    # type: (argparse.Namespace) -> int
    """Handle the `run` verb: profile a transcript and print + store the report.

    Exit codes:
      0 -- a report was produced (printed to stdout; stored unless --no-store)
      2 -- could not produce a report (bad args, no transcript, no events)
    """
    workspace_root = getattr(args, "workspace_root", ".") or "."
    transcript = getattr(args, "transcript", None) or None
    transcript_dir = getattr(args, "dir", None) or None
    no_store = bool(getattr(args, "no_store", False))

    paths, err = _resolve_input_paths(transcript, transcript_dir, workspace_root)
    if err:
        sys.stderr.write("profile_helper run: {0}\n".format(err))
        return 2

    events, n_skipped = parse_transcript_chain(paths)
    if not events:
        sys.stderr.write(
            "profile_helper run: no usable events parsed from {0}\n".format(paths)
        )
        return 2

    segments = profile_events(events)
    totals = compute_totals(segments)

    table = render_table(segments, totals, n_skipped)
    sys.stdout.write(table)

    if not no_store:
        session_id = events[-1]["session_id"]
        harness_version = _extract_harness_version(events)
        run_record = build_run_record(
            session_id=session_id,
            harness_version=harness_version,
            source_paths=paths,
            segments=segments,
            totals=totals,
            n_lines_skipped=n_skipped,
        )
        written_path = write_run(workspace_root, session_id, events[-1]["ts"], run_record)
        summary_path = append_summary(workspace_root, run_record)
        sys.stdout.write("\nWrote {0}\n".format(written_path))
        sys.stdout.write("Updated {0}\n".format(summary_path))

    return 0


# ---------------------------------------------------------------------------
# aggregate
# ---------------------------------------------------------------------------


def cmd_aggregate(args):
    # type: (argparse.Namespace) -> int
    """Handle the `aggregate` verb: roll up all stored runs into one table.

    Exit codes:
      0 -- at least one stored run was found and aggregated
      2 -- no stored runs found under <workspace-root>/.devforge/profile/
    """
    workspace_root = getattr(args, "workspace_root", ".") or "."
    agg = aggregate_runs(workspace_root)
    if agg["n_runs"] == 0:
        sys.stderr.write(
            "profile_helper aggregate: no stored runs found under "
            "{0}/.devforge/profile/\n".format(workspace_root)
        )
        return 2

    sys.stdout.write(render_aggregate_table(agg))
    return 0


# ---------------------------------------------------------------------------
# Registry + parser construction
# ---------------------------------------------------------------------------

_SUBCOMMAND_REGISTRY = [
    (
        "run",
        (
            "Profile one transcript (--transcript), a mtime-stitched --dir "
            "chain, or the auto-located latest transcript for the project. "
            "Prints the per-command bucket-split table and writes "
            ".devforge/profile/ storage unless --no-store."
        ),
        cmd_run,
    ),
    (
        "aggregate",
        (
            "Read every stored .devforge/profile/*.json run and print the "
            "cross-run verdict table: per-command median/max wall + median "
            "bucket split, plus a largest-bucket-per-run tally."
        ),
        cmd_aggregate,
    ),
]


def build_parser():
    # type: () -> argparse.ArgumentParser
    """Build and return the top-level ArgumentParser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="profile_helper",
        description=(
            "Diagnostic helper for pipeline wall-clock profiling (plan 70). "
            "Reads a Claude Code session transcript and reports, per "
            "pipeline command, the wall-clock split into LLM turn time, "
            "Bash/helper time, agent sub-session time, and human-answer "
            "time.  Measurement only -- no pass/fail semantics."
        ),
    )
    subparsers = parser.add_subparsers(dest="subcommand")
    _register_subcommands(subparsers)
    return parser


def _register_subcommands(subparsers):
    # type: (argparse._SubParsersAction) -> None
    for verb, help_text, handler in _SUBCOMMAND_REGISTRY:
        sp = subparsers.add_parser(verb, help=help_text)

        if verb == "run":
            sp.add_argument(
                "--transcript",
                default=None,
                dest="transcript",
                metavar="PATH",
                help="Path to a single transcript .jsonl file to profile.",
            )
            sp.add_argument(
                "--dir",
                default=None,
                dest="dir",
                metavar="DIR",
                help=(
                    "Stitch all top-level *.jsonl files in DIR by mtime "
                    "into one chain and profile it (a /clear-split "
                    "pipeline run). Mutually exclusive with --transcript."
                ),
            )
            sp.add_argument(
                "--workspace-root",
                default=".",
                dest="workspace_root",
                metavar="DIR",
                help=(
                    "Project root used to auto-locate the transcript "
                    "directory (when neither --transcript nor --dir is "
                    "given) and as the storage root for .devforge/profile/. "
                    "Default: CWD."
                ),
            )
            sp.add_argument(
                "--no-store",
                action="store_true",
                dest="no_store",
                help="Print the report but skip writing .devforge/profile/ storage.",
            )

        elif verb == "aggregate":
            sp.add_argument(
                "--workspace-root",
                default=".",
                dest="workspace_root",
                metavar="DIR",
                help="Project root whose .devforge/profile/ dir to aggregate. Default: CWD.",
            )

        sp.set_defaults(func=handler)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv=None):
    # type: (Optional[List[str]]) -> int
    """Parse argv and dispatch to the selected subcommand handler.

    Returns the handler's exit code (0 = success, non-zero = error).
    When no subcommand is given, prints help and returns 2.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help(sys.stderr)
        return 2

    return args.func(args)
