"""Run-by provenance stamp shared by the /devforge:specify and
/devforge:research renderers (91-FEATURE-DIR-IDENTITY-AND-PROVENANCE-
PLAN.md Phase 4, D7-D9, OQ-7, OQ-8).

Three independent pieces, each owned here so both renderers get the
identical predicate rather than two that can drift apart:

  1. extract_run_by -- pull an already-rendered "**Run by**: <value>"
     line back out of markdown text. This is the OQ-7 read-back: a
     caller that already has the on-disk artifact's text (or has read
     it back before re-rendering) uses this to recover the ORIGINAL
     value instead of recomputing one, so a re-render never overwrites
     a creator's name with whoever happens to re-run the command.

  2. read_ai_attribution_enabled -- the D9/OQ-8 config gate. OQ-8
     ratified option (i): no new config key. This reads the SAME
     AI_ATTRIBUTION answer _configure/_render.py's COMMIT_ATTRIBUTION
     derivation already gates on (`ai_attribution == "Yes"`), from the
     project-config.json render, not from the "yes"/"no" verbatim
     answer wording -- so an install that told /devforge:configure "no
     attribution in files" cannot get a human name stamped into a
     committed artifact by this, a completely different route.

     Deliberately independent of every other project-config.json
     reader in this codebase (see _shared/feature_alloc.py's
     read_require_ticket docstring for the precedent this follows --
     "two independent config readers for two independent keys, so a
     change to one gate's read path can never silently move the
     other's"). Fails CLOSED (False) on any read/parse problem -- the
     opposite default of read_require_ticket's fail-OPEN, because the
     two gates protect against opposite mistakes: a missing
     REQUIRE_TICKET must not impose friction nobody asked for, but a
     missing/unreadable project-config.json must not cause a human
     name to leak into a public, committed artifact by default.

  3. capture_git_user_name -- read `git config user.name` and nothing
     else. Never reads user.email or any other git-config key: D9's
     stated bound is "nothing but the configured name reaches the
     artifact", and this module is the only place that value is ever
     produced from the environment.

resolve_run_by_for_render composes all three into the one decision a
render call site needs: given the text of an already-existing artifact
(or None, when this is the first render), return the value that
belongs in this render's "Run by:" line -- preserving the original
when one exists (OQ-7), else capturing fresh (gated, never invented,
per D9).
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Optional, Union

# The rendered label both _specify/_render.py and _research/_render.py
# use for the provenance line. A shared constant so the two renderers
# and this module's own extractor can never spell it three different
# ways.
RUN_BY_LABEL = "Run by"

# D9's stated bound, rendered directly under the Run-by line by both
# renderers -- "without that sentence the field becomes exactly the
# 'used to be true, now silently false' failure mode" (D9). Only
# rendered alongside the Run-by line itself; when the line is absent
# there is no claim left to bound.
RUN_BY_BOUND_NOTE = (
    "_Records who ran the command that created this document; "
    "not updated on later edits._"
)

# Anchored at the start of a line: "**Run by**: <value>". MULTILINE so
# `^`/`$` match per physical line rather than only at the string's
# very start/end -- the label can appear anywhere in a multi-section
# document. Whitespace around <value> is trimmed by the capture
# group's own `\s*`/`\s*$` rather than by a separate .strip() call, so
# a rejected (fully-whitespace) match returns no group at all instead
# of an empty string.
_RUN_BY_LINE_RE = re.compile(
    r"^\*\*" + re.escape(RUN_BY_LABEL) + r"\*\*:\s*(\S.*?)\s*$",
    re.MULTILINE,
)

_PROJECT_CONFIG_FILENAME = "project-config.json"
_AI_ATTRIBUTION_KEY = "AI_ATTRIBUTION"

# Matches _implement/_cmds_commit.py's _GIT_TIMEOUT precedent for a
# local, single git-config read -- generous because a hang here must
# never look like a crash, not because this call is expected to be
# slow.
_GIT_TIMEOUT = 30


def extract_run_by(markdown_text: Optional[str]) -> Optional[str]:
    """Return the value of an existing "**Run by**: <value>" line, or None.

    None is returned for: markdown_text is None or empty, no such line
    is present, or the line's value is empty/all-whitespace. All three
    are the SAME outcome for a caller -- "this document records no
    creator" -- and OQ-7's "keep the original" means preserving that
    absence exactly as much as it means preserving a present value.

    Only the FIRST match is read (a rendered document carries at most
    one Run-by line by construction; a hand-edited document with more
    than one is not a case this function tries to adjudicate).
    """
    if not markdown_text:
        return None
    m = _RUN_BY_LINE_RE.search(markdown_text)
    if not m:
        return None
    return m.group(1)


def read_ai_attribution_enabled(
    devforge_dir: Union[str, Path],
) -> bool:
    """Read AI_ATTRIBUTION from devforge_dir/project-config.json (OQ-8(i)).

    Returns True iff the key's value is EXACTLY the string "Yes" --
    the same predicate _configure/_render.py's COMMIT_ATTRIBUTION
    derivation already applies (`ai_attribution == "Yes"`). Every
    other case returns False:
      - project-config.json is absent or unreadable (any OSError)
      - its content is not valid JSON, or the top-level value is not
        a JSON object
      - the AI_ATTRIBUTION key is absent
      - the key's value is anything other than the string "Yes"
        (including "yes", "YES", "No", a JSON boolean, or garbage)

    Fails CLOSED (False), the opposite default from
    _shared.feature_alloc.read_require_ticket's fail-OPEN -- see this
    module's docstring for why the two gates need opposite defaults.

    Never raises.
    """
    config_path = Path(devforge_dir) / _PROJECT_CONFIG_FILENAME
    try:
        raw = config_path.read_text(encoding="utf-8")
    except OSError:
        return False
    try:
        data = json.loads(raw)
    except ValueError:
        return False
    if not isinstance(data, dict):
        return False
    return data.get(_AI_ATTRIBUTION_KEY) == "Yes"


def capture_git_user_name(
    repo_root: Optional[Union[str, Path]] = None,
) -> Optional[str]:
    """Read `git config user.name`, and nothing else.

    Returns the stripped value, with any embedded newline collapsed to
    a single space (a value this hostile is unlikely from git config,
    but the render call site trusts this function's return to be
    safely embeddable in a single markdown line -- collapsing here,
    once, is cheaper than trusting every caller to do it). Returns
    None when: git is not installed, the command exits non-zero (no
    user.name configured anywhere in the local/global/system chain),
    the call times out, or the resulting value is empty after
    stripping.

    `repo_root`, when given, is passed via `git -C <repo_root>` so the
    caller can target the install repo without changing the process
    working directory (_implement/_cmds_commit.py's `_current_branch`
    is the precedent for this shape). When omitted, git resolves
    config from the process's own working directory.

    Deliberately reads ONLY user.name -- never user.email or any other
    key. D9's bound is "nothing but the configured name reaches the
    artifact"; this function is the sole producer of that value from
    the environment, so the bound is enforced by never asking git for
    anything else.

    Never raises.
    """
    argv = ["git"]
    if repo_root is not None:
        argv += ["-C", str(repo_root)]
    argv += ["config", "user.name"]
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            check=False,
            timeout=_GIT_TIMEOUT,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    name = result.stdout.replace("\r\n", " ").replace("\n", " ").strip()
    return name or None


def resolve_run_by_for_render(
    existing_text: Optional[str],
    devforge_dir: Union[str, Path],
    repo_root: Optional[Union[str, Path]] = None,
) -> Optional[str]:
    """Decide the "Run by:" value for one render call (D9 + OQ-7).

    `existing_text` is the FULL text of the artifact this render would
    overwrite, when the caller has one -- pass the on-disk file's
    content when it already exists (a re-render / grill re-entry
    revision), or None when it does not (a first-time render). This
    function never touches the filesystem itself for that path; the
    caller resolves it, because the composition differs per artifact
    (spec.md's directory is derived from /devforge:specify state,
    research-report.md's from an explicit --existing-path -- see each
    call site).

      - existing_text is not None (a prior render happened): return
        exactly what extract_run_by finds in it -- present or absent.
        This is OQ-7's "keep the original": the creator was decided
        whenever that file was FIRST written, and this function must
        not let a later re-render silently reassign it, even when the
        original recorded no name at all (an install with the gate off
        or no git user.name at first creation stays name-less forever,
        not retroactively backfilled once someone else's config is
        readable).
      - existing_text is None (first-time render): capture fresh,
        gated on read_ai_attribution_enabled. An install that answered
        "no attribution in files" gets None here regardless of what
        git config user.name would return -- D9's config-gate bound.
    """
    if existing_text is not None:
        return extract_run_by(existing_text)
    if not read_ai_attribution_enabled(devforge_dir):
        return None
    return capture_git_user_name(repo_root)
