"""cbm_sync_helper — keep CBM index aligned with parent repo HEAD.

Two subcommands:

  write — read parent HEAD via `git rev-parse HEAD`, write
          `.devforge/cbm-last-indexed-sha` atomically.
  check — compare stamp to current HEAD, print one of four state
          tokens on stdout: `current` / `missing` / `drift <a>..<b>`
          / `not-a-git-repo`.

State tokens (stdout, single line, newline-terminated):

  current             — stamp.git_sha == current HEAD
  missing             — no stamp file (or stamp JSON is corrupt /
                        missing the git_sha field)
  drift <a>..<b>      — stamp records <a>, current HEAD is <b>
  not-a-git-repo      — `git rev-parse HEAD` failed (no git repo,
                        no HEAD commit, or git binary missing)

Exit codes:

  0 — success (every state above except not-a-git-repo)
  1 — write: I/O failure persisting the stamp file
  2 — check / write: not-a-git-repo (no HEAD to compare or stamp)
      or argparse usage error (no subcommand)

Stamp shape — `.devforge/cbm-last-indexed-sha`:

  {"git_sha": "<40-char sha>", "indexed_at": "<iso8601 utc>"}

Schema version field deliberately omitted per CBM-SYNC-PLAN §Design
summary (resolved 2026-05-11 — defer until empirical need).

Path resolution honors `DEVFORGE_DIR` (test override), else derives
from this script's own location: `<target>/.devforge/lib/<this>.py`
sits one directory below `<target>/.devforge/`, where the stamp lives.

Stdlib only. No third-party dependencies. Targets Python 3.8+.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

STAMP_FILE_NAME = "cbm-last-indexed-sha"


# ---------------------------------------------------------------------------
# Path resolution.
# ---------------------------------------------------------------------------


def _stamp_path():
    """Resolve the stamp file path at call time (not import time).

    Honors `DEVFORGE_DIR` for tests + unusual layouts. Without it, the
    path derives from this file's own location.
    """
    env_dir = os.environ.get("DEVFORGE_DIR")
    if env_dir:
        return Path(env_dir) / STAMP_FILE_NAME
    return Path(__file__).resolve().parent.parent / STAMP_FILE_NAME


# ---------------------------------------------------------------------------
# Git probe.
# ---------------------------------------------------------------------------


def _git_head():
    """Return current parent-repo HEAD sha, or None if no HEAD is resolvable.

    None covers three failure modes treated identically by the protocol:
    (a) cwd is not inside any git repo, (b) cwd is in a fresh repo with
    no commits, (c) git binary not on PATH.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(Path.cwd()),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    sha = result.stdout.strip()
    if not sha:
        return None
    return sha


# ---------------------------------------------------------------------------
# Stamp I/O.
# ---------------------------------------------------------------------------


def _read_stamp():
    """Return stamp dict or None if file is missing / corrupt / wrong shape."""
    path = _stamp_path()
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _write_stamp(sha):
    """Atomically write stamp file. Raises OSError on failure.

    Uses tempfile.mkstemp in the stamp's parent dir so os.replace is
    atomic on a single filesystem. On any failure mid-write, removes
    the temp file and re-raises.
    """
    target = _stamp_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "git_sha": sha,
        "indexed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    fd, tmp_path = tempfile.mkstemp(
        prefix="cbm-stamp-",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, sort_keys=True)
            f.write("\n")
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Subcommand implementations.
# ---------------------------------------------------------------------------


def cmd_write(args):
    sha = _git_head()
    if sha is None:
        sys.stderr.write(
            "cbm_sync_helper: not a git repository (or no HEAD commit)\n"
        )
        return 2
    try:
        _write_stamp(sha)
    except OSError as err:
        sys.stderr.write("cbm_sync_helper: cannot write stamp: {0}\n".format(err))
        return 1
    return 0


def cmd_check(args):
    sha = _git_head()
    if sha is None:
        sys.stdout.write("not-a-git-repo\n")
        return 2
    stamp = _read_stamp()
    if stamp is None:
        sys.stdout.write("missing\n")
        return 0
    stamp_sha = stamp.get("git_sha")
    if not isinstance(stamp_sha, str) or not stamp_sha:
        sys.stdout.write("missing\n")
        return 0
    if stamp_sha == sha:
        sys.stdout.write("current\n")
        return 0
    sys.stdout.write("drift {0}..{1}\n".format(stamp_sha, sha))
    return 0


# ---------------------------------------------------------------------------
# CLI wiring.
# ---------------------------------------------------------------------------


def build_parser():
    parser = argparse.ArgumentParser(
        prog="cbm_sync_helper",
        description="Keep CBM index aligned with parent repo HEAD.",
    )
    sub = parser.add_subparsers(dest="subcommand")

    sp = sub.add_parser(
        "write",
        help="Stamp current HEAD into .devforge/cbm-last-indexed-sha.",
    )
    sp.set_defaults(func=cmd_write)

    sp = sub.add_parser(
        "check",
        help="Compare stamp to current HEAD; print state token on stdout.",
    )
    sp.set_defaults(func=cmd_check)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
