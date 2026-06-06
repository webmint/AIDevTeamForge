"""_cmds_commit -- wip-commit verb for implement_helper.

Stage only the explicitly named paths, compose a commit message per
wrapper/standalone convention, and commit.  After a successful commit,
clear the wip.md marker.

Algorithm
---------
1. Parse --files (JSON array), --task-file, --index (required staging targets).
2. Resolve workspace via resolve_workspace(--root): gives install_root,
   source_root, is_wrapper.  Config is loaded from install_root.
3. Read .devforge/project-config.json for COMMIT_ATTRIBUTION.
4. Derive TICKET-ID:
   - WRAPPER mode: run `git -C <source_root> rev-parse --abbrev-ref HEAD`
     to get the SOURCE repo branch; extract [A-Z]+-[0-9]+ ticket token
     (e.g. `bugfix/MIG-123` → `MIG-123`); fall back to full branch name.
   - STANDALONE mode: ticket-id is unused (non-wrapper message format).
5. Compose message:
   - wrapper mode:   "[TICKET-ID] - <title> (Task NNN)"
   - standalone:     "[WIP] task: <title> (Task NNN)"
6. Append COMMIT_ATTRIBUTION exactly as stored (may be empty/absent → no append).
7. Stage paths individually (`git add -- <path>`). NEVER `git add -A`.
   - WRAPPER mode:   stage ONLY source touched_files in the SOURCE repo
                     (`git -C <source_root> add -- <file>`).
                     Do NOT stage --task-file or --index (per D1 — those are
                     wrapper artifacts, left uncommitted; mark-complete already
                     wrote them to disk).
   - STANDALONE mode: stage source touched_files + task_file + index in the
                     single repo (unchanged from before).
8. Commit in the TARGET repo:
   - WRAPPER mode:   `git -C <source_root> commit -m <msg>` in SOURCE repo.
   - STANDALONE mode: `git commit -m <msg>` (single repo).
9. Capture the new HEAD SHA from the TARGET repo.
10. Clear wip.md in the INSTALL root (wrapper artifacts, always install-root).
11. Emit JSON {committed: true, head_sha: "...", message: "..."} to stdout.

Arguments (argparse):
  --files     <json>   Required. JSON array of source-relative touched file paths.
  --task-file <path>   Required. Path to the task .md file (install-root-relative
                       in wrapper mode; not staged there per D1).
  --index     <path>   Required. Path to tasks/README.md index file (install-root-
                       relative in wrapper mode; not staged per D1).
  --number    <str>    Required. Task number string, e.g. "001".
  --title     <str>    Required. Task title.
  --root      <path>   Optional. Install root; defaults to cwd.

Emitted JSON (stdout, exit 0):
  {"committed": true, "head_sha": "<sha>", "message": "<msg>"}

Exit codes:
  0 — committed successfully.
  1 — I/O / config error (message on stderr).
  2 — git staging or commit failure (message on stderr).

Design notes:
- D1 (wrapper mode): only source touched_files are staged and committed per
  task; task_file and index (wrapper artifacts) are written by mark-complete
  but NOT committed by wip-commit in wrapper mode.  The wrapper tree accumulates
  those changes separately (not auto-committed per task, per D1 of the plan).
- D2 (ticket-id source): in wrapper mode the TICKET-ID derives from the SOURCE
  repo's branch name, not the wrapper branch.  The wrapper branch (spec/NNN-…)
  is irrelevant to the source repo commit message.
- TICKET-ID pattern [A-Z]+-[0-9]+: industry-standard Jira-style ticket pattern.
  Applied after stripping path prefixes:
    bugfix/MIG-123-desc → MIG-123
    PROJ-42-do-thing    → PROJ-42
    develop-no-ticket   → fallback = full branch name
- WORKSPACE_MODE key: project-config.json stores workspace mode as
  "WORKSPACE_MODE" (uppercase). Value "wrapper" means wrapper mode is active.
  resolve_workspace() is the canonical detector (via PROJECT_ROOT); WORKSPACE_MODE
  is consulted for compatibility when the config contains it.
- COMMIT_ATTRIBUTION: stored verbatim in project-config.json. May be an empty
  string (ai_attribution == "No") or "\\n\\nCo-Authored-By: Claude <...>". The
  value is appended directly to the message body (no extra newline added); if
  absent (key not in config), no attribution line is added.
- Staging safety: each path is staged individually so an unrelated dirty file
  in the working tree is NEVER committed.  git add -A is never used.
- subprocess timeout: 30 s per git call. Generous but bounded.
- git -C <path>: used for all source-repo operations in wrapper mode so the
  implementation never changes the process working directory.

Stdlib only. Python 3.8+.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from _implement._wip import clear_wip_marker  # type: ignore[import]
from _implement._workspace import resolve_workspace  # type: ignore[import]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_ERR = 1
EXIT_FINDINGS = 2

# Helper-owned ticket-token regex: matches Jira-style PROJ-123 tokens.
# Requires all-uppercase letter prefix, dash, one-or-more digits.
_TICKET_PATTERN = re.compile(r"\b([A-Z]+-[0-9]+)\b")

# Timeout (seconds) for git subprocess calls.
_GIT_TIMEOUT = 30

# The project-config.json key for commit attribution.
_COMMIT_ATTRIBUTION_KEY = "COMMIT_ATTRIBUTION"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_project_config(root):
    # type: (Path) -> dict
    """Load .devforge/project-config.json relative to root.

    Returns an empty dict if the file is absent (config is optional —
    caller falls back to defaults). Raises ValueError on malformed JSON.
    """
    config_path = root / ".devforge" / "project-config.json"
    if not config_path.exists():
        return {}
    try:
        with open(str(config_path), "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(
            "Malformed .devforge/project-config.json: {0}".format(exc)
        )


def _get_commit_attribution(config):
    # type: (dict) -> str
    """Return COMMIT_ATTRIBUTION from config, or '' if absent/empty."""
    val = config.get(_COMMIT_ATTRIBUTION_KEY, "")
    if not val:
        return ""
    return val


def _current_branch(repo_root):
    # type: (Path) -> Optional[str]
    """Return the current git branch name in repo_root, or None on failure.

    Uses 'git -C <repo_root>' so the caller can target either the install
    repo or the source repo without changing the process working directory.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
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


def _extract_ticket_id(branch):
    # type: (str) -> str
    """Extract a Jira-style ticket token from branch name, or return branch.

    Pattern: [A-Z]+-[0-9]+
    Examples:
      spec/PROJ-123-slugify-feature  → PROJ-123
      PROJ-42-do-thing               → PROJ-42
      develop-2.0-init               → develop-2.0-init (no match)
      feature/ABC-99                 → ABC-99
    """
    m = _TICKET_PATTERN.search(branch)
    if m:
        return m.group(1)
    # No ticket token found: use full branch name as fallback.
    return branch


def _compose_message(is_wrapper, ticket_id, title, number, attribution):
    # type: (bool, str, str, str, str) -> str
    """Compose the commit message with optional attribution.

    wrapper mode:  "[TICKET-ID] - <title> (Task NNN)"
    non-wrapper:   "[WIP] task: <title> (Task NNN)"
    Attribution is appended verbatim when non-empty.
    """
    if is_wrapper:
        subject = "[{0}] - {1} (Task {2})".format(ticket_id, title, number)
    else:
        subject = "[WIP] task: {0} (Task {1})".format(title, number)

    if attribution:
        return subject + attribution
    return subject


def _git_stage_path(repo_root, path_str):
    # type: (Path, str) -> Optional[str]
    """Stage a single file path via `git -C <repo_root> add -- <path>`.

    Returns None on success, error message string on failure.
    path_str may be relative (to repo_root) or absolute.

    Uses 'git -C <repo_root>' so the caller can target either the install
    repo or the source repo without changing the process working directory.
    Precise staging: only the explicitly named path is staged (never add -A).
    """
    # Resolve relative paths against repo_root.
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


def _git_commit(repo_root, message):
    # type: (Path, str) -> Optional[str]
    """Create a commit with the given message in repo_root.

    Returns None on success, error message string on failure.
    Uses 'git -C <repo_root>' so the caller can target either the install
    repo or the source repo without changing the process working directory.
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
    """Return the current HEAD SHA of repo_root, or None on failure.

    Uses 'git -C <repo_root>' so the caller can target either the install
    repo or the source repo without changing the process working directory.
    """
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
# argparse setup
# ---------------------------------------------------------------------------


def add_args_wip_commit(parser):
    # type: (object) -> None
    """Register wip-commit arguments on the given subparser."""
    parser.add_argument(
        "--files",
        required=True,
        help="JSON array of touched file paths to stage.",
    )
    parser.add_argument(
        "--task-file",
        required=True,
        dest="task_file",
        help="Path to the task .md file to stage.",
    )
    parser.add_argument(
        "--index",
        required=True,
        help="Path to tasks/README.md index file to stage.",
    )
    parser.add_argument(
        "--number",
        required=True,
        help="Task number string, e.g. '001'.",
    )
    parser.add_argument(
        "--title",
        required=True,
        help="Task title string.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repo root directory. Defaults to cwd.",
    )


# ---------------------------------------------------------------------------
# Command handler
# ---------------------------------------------------------------------------


def cmd_wip_commit(args):
    # type: (object) -> int
    """Stage named paths and create a per-task WIP commit.

    In WRAPPER mode (PROJECT_ROOT != "."):
      - Ticket-id derived from the SOURCE repo branch (D2).
      - Stage ONLY source touched_files in the SOURCE repo (precise staging, D1).
      - task_file and index are NOT staged (wrapper artifacts, left uncommitted per D1).
      - Commit lands in the SOURCE repo on its branch.
      - wip.md is cleared in the INSTALL root (where .devforge/ lives).
      - Emitted head_sha is the SOURCE repo's new HEAD.

    In STANDALONE mode (PROJECT_ROOT == "."):
      - Unchanged from before: stage source touched_files + task_file + index
        all in the single repo; commit there; clear wip.md there.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed arguments: files, task_file, index, number, title, root.

    Returns
    -------
    int
        0 on success; 1 on config/I/O error; 2 on git failure.
    """
    install_root = Path(getattr(args, "root", ".")).resolve()

    # --- Resolve workspace (single source of truth for repo targeting) ---
    workspace = resolve_workspace(install_root)

    # --- Parse --files JSON ---
    files_json = getattr(args, "files", "[]")
    try:
        touched = json.loads(files_json)
    except json.JSONDecodeError as exc:
        sys.stderr.write(
            "wip-commit: --files is not valid JSON: {0}\n".format(exc)
        )
        return EXIT_ERR
    if not isinstance(touched, list):
        sys.stderr.write(
            "wip-commit: --files must be a JSON array, got {0}\n".format(
                type(touched).__name__
            )
        )
        return EXIT_ERR

    task_file = getattr(args, "task_file", "")
    index = getattr(args, "index", "")
    number = getattr(args, "number", "")
    title = getattr(args, "title", "")

    if not task_file:
        sys.stderr.write("wip-commit: --task-file is required\n")
        return EXIT_ERR
    if not index:
        sys.stderr.write("wip-commit: --index is required\n")
        return EXIT_ERR
    if not number:
        sys.stderr.write("wip-commit: --number is required\n")
        return EXIT_ERR
    if not title:
        sys.stderr.write("wip-commit: --title is required\n")
        return EXIT_ERR

    # --- Load project config (from install_root where .devforge/ lives) ---
    try:
        config = _load_project_config(workspace.install_root)
    except ValueError as exc:
        sys.stderr.write("wip-commit: config error: {0}\n".format(exc))
        return EXIT_ERR

    is_wrapper = workspace.is_wrapper
    attribution = _get_commit_attribution(config)

    # --- Determine the commit target repo and ticket-id ---
    if is_wrapper:
        # D2: ticket-id from the SOURCE repo's branch (where code commits land).
        commit_repo = workspace.source_root
        branch = _current_branch(workspace.source_root)
        if branch:
            ticket_id = _extract_ticket_id(branch)
        else:
            ticket_id = "UNKNOWN"
    else:
        # Standalone: single repo; ticket-id unused (non-wrapper message format).
        commit_repo = workspace.install_root  # install_root == source_root
        ticket_id = ""

    # --- Compose commit message ---
    message = _compose_message(is_wrapper, ticket_id, title, number, attribution)

    # --- Stage paths individually (NEVER git add -A) ---
    if is_wrapper:
        # D1: stage ONLY the source touched_files in the SOURCE repo.
        # task_file and index are wrapper artifacts — they are NOT staged here.
        # mark-complete already wrote them to disk; they will be committed
        # separately (or not at all per D1 policy).
        seen = set()  # type: ignore
        to_stage = []  # type: List[str]
        for p in list(touched):
            if p and p not in seen:
                seen.add(p)
                to_stage.append(p)
    else:
        # Standalone: stage source touched_files + task_file + index together.
        seen = set()
        to_stage = []
        for p in list(touched) + [task_file, index]:
            if p and p not in seen:
                seen.add(p)
                to_stage.append(p)

    for path_str in to_stage:
        err = _git_stage_path(commit_repo, path_str)
        if err is not None:
            sys.stderr.write("wip-commit: staging failed: {0}\n".format(err))
            return EXIT_FINDINGS

    # --- Commit (in the target repo) ---
    err = _git_commit(commit_repo, message)
    if err is not None:
        sys.stderr.write("wip-commit: {0}\n".format(err))
        return EXIT_FINDINGS

    # --- Capture new HEAD SHA from the target repo ---
    head_sha = _git_head_sha(commit_repo)
    if head_sha is None:
        sys.stderr.write(
            "wip-commit: commit succeeded but could not read HEAD SHA\n"
        )
        return EXIT_ERR

    # --- Clear wip.md (always in the INSTALL root's .devforge/) ---
    devforge_dir = workspace.install_root / ".devforge"
    try:
        clear_wip_marker(str(devforge_dir))
    except OSError as exc:
        # Non-fatal: commit already succeeded; warn but don't fail.
        sys.stderr.write(
            "wip-commit: warning: could not clear wip.md: {0}\n".format(exc)
        )

    # --- Emit result JSON ---
    result = {
        "committed": True,
        "head_sha": head_sha,
        "message": message,
    }
    sys.stdout.write(json.dumps(result) + "\n")
    return EXIT_OK
