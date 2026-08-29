"""_artifact._cli -- argparse registry + main() for artifact_helper.

Two verbs are wired here; each verb's own logic lives in a sibling module
(one file per concern, per this repository's module-split discipline) and
this file stays the thin Controller (GRASP) that dispatches to them:

  commit-artifacts        -- git primitives + handler defined IN THIS FILE
                              below (the original, unmoved verb).
  find-feature-artifacts  -- defined in _cmds_find_artifacts.py (91-
                              FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md
                              Phase 1b); registered here via import only.

commit-artifacts stages ONLY the explicitly named paths into the install
repo and creates a [WIP] <label> commit.  This is the shared, tested
git-discipline verb that each pipeline command calls after writing its
own artifacts (spec.md, plan.md, *-handoff.json, review.md, etc.) so work
is git-safe at every step.  The per-step [WIP] commits fold into
/finalize's existing `git reset --soft` squash, leaving the final PR
byte-identical to today.

Verb
----
commit-artifacts  --paths <json>  --label <str>  [--root <path>]

Algorithm
---------
1. Parse --paths (JSON array of file or directory paths).  Bad JSON or
   non-array → clean exit 1 (stderr message, no traceback).
2. Resolve workspace via resolve_workspace(--root) from
   _implement._workspace: gives Workspace{install_root, source_root,
   is_wrapper}.  Always targets workspace.install_root (never source_root
   — D2 of plan 37).
3. Stage each path individually:
     git -C <install_root> add -- <path>
   Absent paths produce a benign skip (git add of a nonexistent path
   exits 1 with a warning; we treat that as a no-op and continue).
   NEVER `git add -A` / `git add .` — explicit named paths only.
4. Commit with message `[WIP] <label>`.
5. FAIL-SOFT throughout: a staging or commit git failure warns on stderr
   and returns exit 1 cleanly.  "Nothing to commit" (no staged delta) is
   a benign no-op → exit 0, JSON {"committed": false, ...}.
6. Bound every git call with _GIT_TIMEOUT (30 s).
7. Emit JSON to stdout:
   Success:    {"committed": true, "head_sha": "<sha>", "message": "..."}
   Benign nop: {"committed": false, "skipped": "nothing to commit"}
   Exit 0 in both.

Exit codes
----------
0  -- committed successfully, OR benign no-op (nothing new to stage).
1  -- clean error: bad --paths JSON, or a git staging/commit failure
      (message on stderr, NO traceback, NO exception escaping main()).

Design notes
------------
- D2 (plan 37): targets workspace.install_root ALWAYS.  In wrapper mode
  specs/ (which, per plan 68, now also holds the intake artifacts research/
  and discover/ used to hold — those two top-level dirs are legacy, kept
  on disk only for grandfathered installs, D3 clean cut) lives in the
  install/wrapper root.  The source (product) repo gets code commits only
  (wip-commit's job) and must stay traceless (plan 25 D5).  Pointing this
  verb at source_root is a hard invariant violation — do NOT do it.
- Fail-soft (D1 plan 37): a commit failure warns on stderr and returns
  exit 1, but NEVER raises an exception that would crash the calling
  command.  The artifact is already written; the commit is a safety net.
- No attribution logic: the install-repo [WIP] commits are not the
  traceless product commits.  Attribution is the wip-commit verb's
  concern (source-repo code commits), not this verb's.
- No ticket-id: [WIP] <label> is the full message; no TICKET-ID
  extraction (those are for source-repo code commits).
- Path absent benign skip: git add of an absent path exits 1 with
  "pathspec '...' did not match"; we detect no staged delta after
  staging all paths and call it a benign no-op rather than an error.
  This lets the orchestrator pass optional paths (grill-seed.json,
  data-model.md) without crashing when the run did not write them.
- Advisory-only Cyrillic scan on staged files + label, stderr-only,
  never affects exit code or JSON (plan 87).

Stdlib only. Python 3.8+.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from _implement._workspace import resolve_workspace  # type: ignore[import]

from ._cmds_find_artifacts import (
    add_find_feature_artifacts_args,
    cmd_find_feature_artifacts,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_ERR = 1

# Timeout (seconds) for each git subprocess call — mirrors _cmds_commit.py.
_GIT_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Git helpers (mirror _cmds_commit.py conventions exactly)
# ---------------------------------------------------------------------------


def _git_stage_path(repo_root, path_str):
    # type: (Path, str) -> Optional[str]
    """Stage a single file or directory path via `git -C <repo_root> add -- <path>`.

    Returns None on success, error message string on failure.
    path_str may be relative (to repo_root) or absolute.
    NEVER uses git add -A — only the explicitly named path is staged.

    An absent path is NOT an error here: git will print a warning to
    stderr and return non-zero; the caller (_cmd_commit_artifacts) checks
    whether anything was actually staged after all paths are processed and
    treats zero delta as a benign no-op.
    """
    p = Path(path_str)
    if not p.is_absolute():
        p = repo_root / p

    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "add", "--", str(p)],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        if result.returncode != 0:
            return "git add {0!r} failed (rc={1}): {2}".format(
                path_str, result.returncode, (result.stderr or result.stdout).strip()
            )
        return None
    except subprocess.TimeoutExpired:
        return "git add {0!r} timed out".format(path_str)
    except OSError as exc:
        return "git add {0!r} OS error: {1}".format(path_str, exc)


def _git_has_staged_changes(repo_root):
    # type: (Path) -> bool
    """Return True if there are staged changes ready to commit in repo_root."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--cached", "--quiet"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        # exit 0 → no staged changes; exit 1 → staged changes present;
        # exit >1 → git error (not a repo, etc.) — treat as nothing staged.
        return result.returncode == 1
    except (subprocess.TimeoutExpired, OSError):
        return False


def _git_commit(repo_root, message):
    # type: (Path, str) -> Optional[str]
    """Commit with the given message in repo_root.

    Returns None on success, error message string on failure.
    Uses git -C <repo_root> so the process cwd is never changed.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "commit", "-m", message],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        if result.returncode != 0:
            return "git commit failed (rc={0}): {1}".format(
                result.returncode, (result.stderr or result.stdout).strip()
            )
        return None
    except subprocess.TimeoutExpired:
        return "git commit timed out"
    except OSError as exc:
        return "git commit OS error: {0}".format(exc)


def _git_head_sha(repo_root):
    # type: (Path) -> Optional[str]
    """Return the current HEAD SHA of repo_root, or None on failure."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        if result.returncode != 0:
            return None
        return result.stdout.strip() or None
    except (subprocess.TimeoutExpired, OSError):
        return None


# ---------------------------------------------------------------------------
# Verb handler
# ---------------------------------------------------------------------------


def _cmd_commit_artifacts(args):
    # type: (argparse.Namespace) -> int
    """commit-artifacts verb: stage named paths, WIP commit to install root.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments: paths (str JSON), label (str), root (str).

    Returns
    -------
    int
        0 on success or benign no-op; 1 on clean error.
    """
    # --- Parse --paths JSON ---
    paths_json = getattr(args, "paths", "[]") or "[]"
    try:
        paths = json.loads(paths_json)
    except (json.JSONDecodeError, ValueError) as exc:
        sys.stderr.write(
            "commit-artifacts: --paths is not valid JSON: {0}\n".format(exc)
        )
        return EXIT_ERR

    if not isinstance(paths, list):
        sys.stderr.write(
            "commit-artifacts: --paths must be a JSON array, got {0}\n".format(
                type(paths).__name__
            )
        )
        return EXIT_ERR

    # --- Validate --label ---
    label = (getattr(args, "label", "") or "").strip()
    if not label:
        sys.stderr.write("commit-artifacts: --label is required and must be non-empty\n")
        return EXIT_ERR

    # --- Resolve workspace (D2: always targets install_root) ---
    root_str = getattr(args, "root", ".") or "."
    install_root = Path(root_str).resolve()
    try:
        workspace = resolve_workspace(install_root)
    except Exception as exc:  # resolve_workspace is fail-soft but guard anyway
        sys.stderr.write(
            "commit-artifacts: workspace resolution failed: {0}\n".format(exc)
        )
        return EXIT_ERR

    # D2 guard — commit repo is ALWAYS the install root, never source_root.
    commit_repo = workspace.install_root

    # --- Compose commit message ---
    message = "[WIP] {0}".format(label)

    # --- Stage each path individually (NEVER git add -A) ---
    # Absent paths are a benign skip: git add exits 1 with "did not match";
    # we warn once per path but continue. Zero staged delta → benign no-op.
    stage_errors = []  # type: List[str]
    for path_str in paths:
        if not path_str or not str(path_str).strip():
            # Empty / blank path — benign skip, no error.
            continue
        err = _git_stage_path(commit_repo, str(path_str))
        if err is not None:
            # Warn but do NOT abort: the path may not exist (optional artifact).
            stage_errors.append(err)

    # Check whether we actually staged anything.
    if not _git_has_staged_changes(commit_repo):
        # Nothing staged.  Two sub-cases:
        # a) staging errors occurred (git itself failed — bad repo, rc=128, etc.)
        #    → this is a real failure; report errors and exit 1.
        # b) no errors but nothing staged (paths absent/already-committed or empty
        #    list) → benign no-op, exit 0.
        if stage_errors:
            for err in stage_errors:
                sys.stderr.write("commit-artifacts: {0}\n".format(err))
            return EXIT_ERR
        result_obj = {
            "committed": False,
            "skipped": "nothing to commit",
        }
        sys.stdout.write(json.dumps(result_obj) + "\n")
        return EXIT_OK

    # Some paths staged successfully.  If there were also stage errors on other
    # paths (absent optional artifacts), warn but continue with the commit.
    if stage_errors:
        for err in stage_errors:
            sys.stderr.write("commit-artifacts: warning: {0}\n".format(err))

    # Advisory only (D1-D3, plan 87): bare statement, return value discarded,
    # never gates the commit — see _warn_non_english_artifacts below.
    _warn_non_english_artifacts(commit_repo, label)

    # --- Commit ---
    err = _git_commit(commit_repo, message)
    if err is not None:
        sys.stderr.write("commit-artifacts: {0}\n".format(err))
        return EXIT_ERR

    # --- Capture HEAD SHA ---
    head_sha = _git_head_sha(commit_repo)
    if head_sha is None:
        # The commit DID land; SHA is informational only. Warn and exit 0 so
        # callers gating on committed:true are not misled into thinking no
        # commit happened (which would make a retry no-op and silently skip).
        sys.stderr.write(
            "commit-artifacts: WARNING: commit succeeded but could not read HEAD SHA\n"
        )

    result_obj = {
        "committed": True,
        "head_sha": head_sha,
        "message": message,
    }
    sys.stdout.write(json.dumps(result_obj) + "\n")
    return EXIT_OK


# ---------------------------------------------------------------------------
# Advisory language guard (Cyrillic detector)
#
# Tripwire, not a control (D1): warns on stderr and changes nothing else --
# not the exit code, not either stdout JSON shape, not whether the commit
# happens. Deliberately placed after the verb handler rather than beside the
# four _git_* primitives above so this section's own local `import re` (its
# only new import) cannot shift a single line number inside the verb
# handler above, including its staging-error handling.
# ---------------------------------------------------------------------------

import re  # noqa: E402 -- local on purpose, see module note above

# Cyrillic (Basic) + Cyrillic Supplement, U+0400-U+052F (D2). Covers every
# letter modern Ukrainian needs (i U+0456, yi U+0457, ye U+0454, g U+0491).
# Historic Cyrillic Extended blocks are deliberately out of range.
_CYRILLIC_RANGE_RE = re.compile(u"[\u0400-\u052F]")


def _contains_cyrillic(text):
    # type: (str) -> bool
    """Pure predicate: True if text contains a Cyrillic codepoint (U+0400-U+052F)."""
    return bool(_CYRILLIC_RANGE_RE.search(text))


def _warn_non_english_artifacts(commit_repo, label):
    # type: (Path, str) -> None
    """Advisory-only Cyrillic scan over what is about to be committed.

    Enumerates the staged set from git (never from --paths -- a staged
    directory expands to many files) via `git diff --cached --name-only -z`,
    reads each staged file's worktree bytes, decodes UTF-8 with
    errors="replace", and scans for Cyrillic text. Also scans label, which
    covers the whole commit message since "[WIP] " is ASCII. A staged
    deletion has no worktree file and is skipped.

    Warns on stderr per offending file/label and never raises: the entire
    body runs inside one try/except so a detector failure cannot fail the
    commit (fail-soft, D1). Callers must invoke this as a bare, discarded
    statement -- it returns nothing and must never gate control flow.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(commit_repo), "diff", "--cached", "--name-only", "-z"],
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "git diff --cached --name-only failed (rc={0}): {1}".format(
                    result.returncode, (result.stderr or result.stdout).strip()
                )
            )
        staged_paths = [p for p in result.stdout.split("\0") if p]

        for rel_path in staged_paths:
            file_path = commit_repo / rel_path
            if not file_path.is_file():
                # Staged deletion (or otherwise absent from the worktree) --
                # nothing to read.
                continue
            content = file_path.read_bytes().decode("utf-8", errors="replace")
            if _contains_cyrillic(content):
                sys.stderr.write(
                    "commit-artifacts: warning: non-English (Cyrillic) text in "
                    "{0} — artifacts must be English (advisory, commit "
                    "proceeds)\n".format(rel_path)
                )

        if _contains_cyrillic(label):
            sys.stderr.write(
                "commit-artifacts: warning: non-English (Cyrillic) text in "
                "commit label — artifacts must be English (advisory, "
                "commit proceeds)\n"
            )
    except Exception as exc:  # noqa: BLE001 -- fail-soft by design (D1)
        sys.stderr.write(
            "commit-artifacts: warning: language check skipped: {0}\n".format(exc)
        )


# ---------------------------------------------------------------------------
# argparse registry
# ---------------------------------------------------------------------------

_SUBCOMMAND_REGISTRY = [
    (
        "commit-artifacts",
        lambda p: (
            p.add_argument(
                "--paths",
                required=True,
                help=(
                    "JSON array of file or directory paths to stage. "
                    "Items may be relative to --root or absolute. "
                    "Passed unchanged to `git add -- <path>`. "
                    "Absent paths are benign skips."
                ),
            ),
            p.add_argument(
                "--label",
                required=True,
                help=(
                    "WIP message label. Commit message will be `[WIP] <label>`. "
                    "Example: 'spec: 003-foo'"
                ),
            ),
            p.add_argument(
                "--root",
                default=".",
                help=(
                    "Install root path. Defaults to cwd. "
                    "The verb always commits to the install root (never the source root)."
                ),
            ),
        ),
        _cmd_commit_artifacts,
    ),
    (
        "find-feature-artifacts",
        add_find_feature_artifacts_args,
        cmd_find_feature_artifacts,
    ),
]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main():
    # type: () -> int
    """Entry point for artifact_helper.

    Dispatches to the commit-artifacts verb handler.
    Returns an int exit code (0 = success or benign no-op; 1 = error).
    All exceptions are caught; no traceback escapes.
    """
    parser = argparse.ArgumentParser(
        prog="artifact_helper",
        description=(
            "Shared WIP artifact-commit discipline for pipeline commands. "
            "Stages explicit artifact paths and creates a [WIP] commit in the "
            "install repo."
        ),
    )
    subparsers = parser.add_subparsers(dest="subcommand", metavar="<verb>")

    for name, add_args_fn, handler in _SUBCOMMAND_REGISTRY:
        sub = subparsers.add_parser(name, help="{0} verb".format(name))
        add_args_fn(sub)
        sub.set_defaults(_handler=handler)

    args = parser.parse_args()

    if not getattr(args, "subcommand", None):
        parser.print_help(sys.stderr)
        return EXIT_ERR

    handler = getattr(args, "_handler", None)
    if handler is None:
        sys.stderr.write(
            "artifact_helper: unknown verb: {0}\n".format(args.subcommand)
        )
        return EXIT_ERR

    try:
        return handler(args)
    except Exception as exc:  # noqa: BLE001 — catch-all: must never crash caller
        # Prefixed with the actual subcommand (not a hardcoded "commit-
        # artifacts") now that this dispatcher serves more than one verb.
        sys.stderr.write(
            "{0}: unexpected error: {1}: {2}\n".format(
                args.subcommand, type(exc).__name__, exc
            )
        )
        return EXIT_ERR
