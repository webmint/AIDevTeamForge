"""_squash.py — squash-base resolution + already-pushed guard for finalize_helper.

Phase 2 ships two read/compute verbs (NO git history mutation — that is Phase 3):

  resolve-squash-base
      Compute the commit SHA to squash back to:
      - Wrapper/install repo, feature branch case:
            use the _shared merge-base (git merge-base HEAD <DEFAULT_BRANCH>).
      - Wrapper/install repo, on-DEFAULT_BRANCH case (no feature branch):
            find the oldest [checkpoint] commit's parent as the squash base.
      - Source repo (wrapper mode):
            use the _shared merge-base scoped to source_root (replaces the
            draft finalize.md's grep-based source-repo base detection at :39).
      Returns a dict with keys:
        install_squash_base   str or None  — SHA to squash to in the install repo
        source_squash_base    str or None  — SHA to squash to in the source repo (None in standalone)
        strategy              str          — "merge-base" | "checkpoint-parent" | "none"
        is_feature_branch     bool         — True when HEAD is not on DEFAULT_BRANCH
        default_branch        str or None  — the detected/resolved DEFAULT_BRANCH name
        error                 str or None  — present and non-None only on fatal failure

  check-pushed
      Detect whether the current feature's commits have already been pushed to
      the remote (origin/<branch>..HEAD).  Pushed commits must NOT be squashed
      (rewriting shared history is forbidden).
      Returns a dict with keys:
        is_pushed             bool  — True when origin/<branch>..HEAD is empty —
                                      i.e. all HEAD commits are already on
                                      origin/<branch> (commit_count == 0).
                                      Safe-to-squash = NOT is_pushed.
        commit_count          int   — number of commits in origin/<branch>..HEAD
        branch                str or None  — current branch name
        no_upstream           bool  — True when the remote or upstream doesn't exist
        error                 str or None  — present and non-None only on fatal failure

Exit codes for CLI handlers:
  0 — success (JSON emitted to stdout)
  2 — error (message on stderr)

Design notes:
- All git operations use git -C <repo> (never a process cwd change).
- _extract_ticket_id is imported from _implement._cmds_commit — the one
  canonical authority for the [A-Z]+-[0-9]+ Jira-style ticket token.
  It is exercised here (Phase 2) so Phase 3's squash verb can consume a
  tested value without re-authoring the regex.
- The BSD-safe --fixed-strings form is used for all [checkpoint] / [WIP]
  greps (same discipline as _preflight.py, _summarize, etc.).
- NO git reset --soft, NO git commit in this module (Phase 3 adds those).

Stdlib only.  Python 3.8+.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

# Import the canonical ticket-ID extractor from implement — do NOT re-author.
from _implement._cmds_commit import _extract_ticket_id  # type: ignore  # noqa: F401


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GIT_TIMEOUT = 60

# Candidates for the default branch, tried in order when origin/HEAD is absent.
# Must match _shared/feature_scope._BASE_CANDIDATES — update both together.
_DEFAULT_BRANCH_CANDIDATES = ["main", "develop", "master"]


# ---------------------------------------------------------------------------
# Internal git helper
# ---------------------------------------------------------------------------


def _git(args, cwd, timeout=_GIT_TIMEOUT):
    # type: (List[str], str, int) -> Tuple[int, str, str]
    """Run git -C <cwd> <args>.

    Returns (returncode, stdout, stderr).
    Never raises — subprocess errors become (1, "", error_message).
    """
    cmd = ["git", "-C", cwd] + args
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except FileNotFoundError:
        return 1, "", "git not found on PATH"
    except subprocess.TimeoutExpired:
        return 1, "", "git command timed out after {0}s: {1}".format(
            timeout, " ".join(cmd)
        )


# ---------------------------------------------------------------------------
# Internal helpers shared by both verbs
# ---------------------------------------------------------------------------


def _ref_exists(ref, repo_root):
    # type: (str, str) -> bool
    """Return True if the git ref resolves in repo_root."""
    rc, _, _ = _git(["rev-parse", "--verify", ref], repo_root)
    return rc == 0


def _current_branch_str(repo_root):
    # type: (str) -> Optional[str]
    """Return the current git branch name (string), or None on detached/error."""
    rc, stdout, _ = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo_root)
    if rc != 0:
        return None
    branch = stdout.strip()
    if not branch or branch == "HEAD":
        return None
    return branch


def _resolve_default_branch(repo_root):
    # type: (str) -> Optional[str]
    """Auto-detect the trunk/default branch.

    Precedence (mirrors _shared/feature_scope.py _autodetect_base):
      1. origin/HEAD via git symbolic-ref refs/remotes/origin/HEAD
      2. origin/HEAD as a direct ref (bare-checkout fallback)
      3. local branch "main"
      4. local branch "develop"
      5. local branch "master"

    Returns the first that resolves, or None.
    """
    # Step 1: origin/HEAD via symbolic-ref.
    rc, stdout, _ = _git(
        ["symbolic-ref", "refs/remotes/origin/HEAD"],
        repo_root,
    )
    if rc == 0:
        ref = stdout.strip()
        if ref and _ref_exists(ref, repo_root):
            return ref

    # Step 2: origin/HEAD as a direct ref.
    if _ref_exists("origin/HEAD", repo_root):
        return "origin/HEAD"

    # Steps 3-5: local branch candidates.
    for candidate in _DEFAULT_BRANCH_CANDIDATES:
        if _ref_exists(candidate, repo_root):
            return candidate

    return None


def _is_on_default_branch(repo_root, default_branch):
    # type: (str, str) -> bool
    """Return True when HEAD and default_branch resolve to the same commit."""
    rc_h, head_sha, _ = _git(["rev-parse", "HEAD"], repo_root)
    if rc_h != 0:
        return False
    rc_d, default_sha, _ = _git(["rev-parse", default_branch], repo_root)
    if rc_d != 0:
        return False
    return head_sha.strip() == default_sha.strip()


def _compute_merge_base(repo_root, default_branch):
    # type: (str, str) -> Optional[str]
    """Return git merge-base HEAD <default_branch> SHA, or None on error."""
    rc, stdout, _ = _git(["merge-base", "HEAD", default_branch], repo_root)
    if rc != 0:
        return None
    return stdout.strip() or None


def _oldest_checkpoint_parent(repo_root):
    # type: (str,) -> Tuple[Optional[str], Optional[str]]
    """Find the oldest [checkpoint] commit reachable from HEAD and return its parent SHA.

    This is the on-DEFAULT_BRANCH squash-base fallback: when the user is not
    on a feature branch, the squash base is the commit just before the oldest
    [checkpoint] entry in the full history.

    NOTE: No range is used here — when the caller is already ON the default
    branch, the range `<default_branch>..HEAD` would be empty (HEAD IS the
    default branch tip).  We search the full history so all [checkpoint]
    commits are visible regardless of branch position.

    Uses the BSD-safe --fixed-strings form to prevent git from treating the
    square brackets in [checkpoint] as a BRE character class.

    Returns (parent_sha, error_or_none):
      - (sha_str, None)   — success: parent SHA of the oldest [checkpoint] commit
      - (None, None)      — no [checkpoint] commits exist in history (or git log failed)
      - (None, error_str) — [checkpoint] commits exist but the oldest IS the repository's
                            initial commit (no parent; git rev-parse <sha>^ fails with rc=128)
    """
    rc, stdout, _ = _git(
        [
            "log",
            "--fixed-strings",
            "--grep=[checkpoint]",
            "--format=%H",
        ],
        repo_root,
    )
    if rc != 0 or not stdout.strip():
        return None, None

    # tail -1 equivalent: git log lists newest-first; the last entry is the
    # chronologically oldest [checkpoint] commit.
    shas = [s.strip() for s in stdout.splitlines() if s.strip()]
    if not shas:
        return None, None

    oldest_sha = shas[-1]

    # Resolve the parent of the oldest checkpoint commit.
    rc2, parent_out, _ = _git(
        ["rev-parse", "{0}^".format(oldest_sha)],
        repo_root,
    )
    if rc2 != 0:
        # rc=128 is git's "bad revision" exit code, which is what rev-parse
        # returns when the commit has no parent (it is the repository's initial
        # commit).  Surface a clear error so resolve_squash_base can distinguish
        # this case from the "no checkpoints found" no-op.
        return None, (
            "cannot squash: the oldest [checkpoint] commit ({0}) is the "
            "repository's initial commit (no parent to squash back to)".format(
                oldest_sha[:12]
            )
        )
    parent_sha = parent_out.strip()
    return (parent_sha if parent_sha else None), None


# ---------------------------------------------------------------------------
# resolve_squash_base — public interface
# ---------------------------------------------------------------------------


def resolve_squash_base(
    install_root,       # type: str
    source_root,        # type: str
    default_branch=None,  # type: Optional[str]
):
    # type: (...) -> Dict
    """Compute the squash base SHAs for the install repo and (in wrapper mode) source repo.

    Parameters
    ----------
    install_root:
        Absolute path to the forge install/wrapper root.
    source_root:
        Absolute path to the source tree.  Equals install_root in standalone mode.
    default_branch:
        The trunk/default branch name (e.g. "main").  When None, auto-detected
        via the standard precedence (origin/HEAD -> main -> develop -> master).

    Returns a dict (always — never raises):
      install_squash_base   str or None  — SHA to squash to in install repo
      source_squash_base    str or None  — SHA to squash to in source repo (None in standalone)
      strategy              str          — "merge-base" | "checkpoint-parent" | "none"
      is_feature_branch     bool         — True when HEAD is not on DEFAULT_BRANCH
      default_branch        str or None  — resolved DEFAULT_BRANCH ref name
      error                 str or None  — fatal error message (None = success)
    """
    result = {
        "install_squash_base": None,
        "source_squash_base":  None,
        "strategy":            "none",
        "is_feature_branch":   False,
        "default_branch":      None,
        "error":               None,
    }  # type: Dict

    # --- Resolve default branch ---
    if default_branch:
        db = default_branch
        if not _ref_exists(db, install_root):
            result["error"] = (
                "default branch {0!r} does not exist in {1!r}".format(
                    db, install_root
                )
            )
            return result
    else:
        db = _resolve_default_branch(install_root)
        if db is None:
            result["error"] = (
                "cannot auto-detect default branch in {0!r}. "
                "None of origin/HEAD, main, develop, master resolve. "
                "Pass --default-branch <ref> explicitly.".format(install_root)
            )
            return result

    result["default_branch"] = db

    # --- Determine whether we are on the default branch or a feature branch ---
    on_default = _is_on_default_branch(install_root, db)
    result["is_feature_branch"] = not on_default

    # --- Install repo squash base ---
    if not on_default:
        # Feature-branch case: use merge-base.
        mb = _compute_merge_base(install_root, db)
        if mb is None:
            result["error"] = (
                "git merge-base HEAD {0!r} failed in {1!r}".format(db, install_root)
            )
            return result
        result["install_squash_base"] = mb
        result["strategy"] = "merge-base"
    else:
        # On DEFAULT_BRANCH: fall back to the oldest [checkpoint] commit's parent.
        # No range needed — we search full history because HEAD IS the default
        # branch tip, making the <default_branch>..HEAD range empty.
        parent, cp_err = _oldest_checkpoint_parent(install_root)
        if cp_err:
            # [checkpoint] commits exist but the oldest is the repo's initial
            # commit — distinguish this from the silent "no checkpoints" no-op.
            result["error"] = cp_err
            return result
        if parent:
            result["install_squash_base"] = parent
            result["strategy"] = "checkpoint-parent"
        else:
            # No checkpoint commits found — nothing to squash.
            result["strategy"] = "none"

    # --- Source repo squash base (wrapper mode only) ---
    abs_source = os.path.realpath(source_root)
    abs_install = os.path.realpath(install_root)
    if abs_source != abs_install:
        # In wrapper mode the source repo may be on a different branch from the
        # install repo.  Use the _shared merge-base scoped to source_root.
        src_db = _resolve_default_branch(source_root)
        if src_db is None:
            # Non-fatal: surface None but don't fail the whole call.
            result["source_squash_base"] = None
        else:
            src_mb = _compute_merge_base(source_root, src_db)
            result["source_squash_base"] = src_mb  # None if computation failed

    return result


# ---------------------------------------------------------------------------
# check_pushed — public interface
# ---------------------------------------------------------------------------


def check_pushed(repo_root):
    # type: (str) -> Dict
    """Check whether the current branch's commits are already on the remote.

    Runs:  git -C <repo_root> log --oneline origin/<branch>..HEAD

    Returns a dict (always — never raises):
      is_pushed     bool         — True when origin/<branch>..HEAD is empty —
                                   i.e. all HEAD commits are already on
                                   origin/<branch> (commit_count == 0).
                                   Safe-to-squash = NOT is_pushed.
      commit_count  int          — commits in origin/<branch>..HEAD (0 = pushed / no range)
      branch        str or None  — current branch name (None if detached)
      no_upstream   bool         — True when origin/<branch> doesn't exist OR no remote
      error         str or None  — fatal git error (None = success)

    Graceful degradation:
      - No remote configured or origin/<branch> not found:
            no_upstream=True, is_pushed=False, commit_count=0
            (treated as "not pushed → safe to squash" but the caller is warned
            via the no_upstream flag)
      - Detached HEAD: branch=None, no_upstream=True, is_pushed=False
    """
    result = {
        "is_pushed":    False,
        "commit_count": 0,
        "branch":       None,
        "no_upstream":  False,
        "error":        None,
    }  # type: Dict

    branch = _current_branch_str(repo_root)
    result["branch"] = branch

    if branch is None:
        # Detached HEAD — cannot determine origin reference.
        result["no_upstream"] = True
        return result

    origin_ref = "origin/{0}".format(branch)

    # Check whether the remote tracking ref exists.
    if not _ref_exists(origin_ref, repo_root):
        # Remote branch does not exist → treat as "not pushed → safe to squash".
        result["no_upstream"] = True
        return result

    # Run git log --oneline <origin/branch>..HEAD to count local-only commits.
    rc, stdout, stderr = _git(
        ["log", "--oneline", "{0}..HEAD".format(origin_ref)],
        repo_root,
    )
    if rc != 0:
        result["error"] = (
            "git log {0}..HEAD failed in {1!r}: {2}".format(
                origin_ref, repo_root, stderr.strip()
            )
        )
        return result

    commits = [ln for ln in stdout.splitlines() if ln.strip()]
    count = len(commits)
    result["commit_count"] = count
    # is_pushed=True means commits HAVE been pushed (count == 0 → all on remote).
    result["is_pushed"] = (count == 0)

    return result


# ---------------------------------------------------------------------------
# CLI handlers — registered via _cli.py _SUBCOMMAND_REGISTRY
# ---------------------------------------------------------------------------


def cmd_resolve_squash_base(args):
    # type: (object) -> int
    """Handle the resolve-squash-base verb.

    Emits JSON to stdout on success (exit 0).
    Emits an error message to stderr on failure (exit 2).
    """
    install_root = getattr(args, "install_root", ".") or "."
    source_root  = getattr(args, "source_root", None) or install_root
    default_branch = getattr(args, "default_branch", None) or None

    result = resolve_squash_base(
        install_root=os.path.realpath(install_root),
        source_root=os.path.realpath(source_root),
        default_branch=default_branch,
    )

    if result.get("error"):
        sys.stderr.write(
            "resolve-squash-base: {0}\n".format(result["error"])
        )
        sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
        return 2

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0


def cmd_check_pushed(args):
    # type: (object) -> int
    """Handle the check-pushed verb.

    Emits JSON to stdout (always, so the orchestrator can read no_upstream etc.).
    Exits 2 only on a fatal git error.
    """
    repo_root = getattr(args, "repo_root", ".") or "."

    result = check_pushed(os.path.realpath(repo_root))

    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")

    if result.get("error"):
        sys.stderr.write(
            "check-pushed: {0}\n".format(result["error"])
        )
        return 2

    return 0
