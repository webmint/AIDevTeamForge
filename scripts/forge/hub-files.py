#!/usr/bin/env python3
"""Hub files: the files that most feature changes edit, the Open/Closed smell of a growing composition root.

A file that every new feature must edit (a route list, a composition root, a navigation table, a shared seed) makes
each feature change a hub edit, and the hub grows by hand. The per-spec structural check reads this list: `/plan`
(and its plan-gate) decides each hub edit, and `/review`'s Structural Check, run before `/finalize`, checks the
spec's edits against that decision. So a spec that adds another hub edit carries a registration seam (a
self-registering manifest, a compile-time link) or a recorded reason.

Binding: `.claude/quality-profile.json` → `hubFiles` (`commitPattern`, `window`, `threshold`, `paths`, optional
`ignore`) and `integrationRef` (the ref whose history is read; `HEAD` when unset), loaded through
scripts/forge/quality_profile.py. A hub is a file under `paths`, not matching `ignore`, that at least `threshold` of
the newest `window` commits on the ref whose subject matches `commitPattern` (the squashed feature commits, or the
merge commits of a merge workflow, read against their first parent; first-parent history) edited. Git runs in the source root (`SOURCE_ROOT`, see quality_profile.py): in a wrapper
project the ref is a ref of the nested source repository, and `paths`, `ignore` and `--files` are relative to it (a
`<SOURCE_ROOT>/` prefix is accepted).

Usage:
  python3 scripts/forge/hub-files.py list [--ref <ref>]
      every hub: `hub <count>/<window> <path>`, most edits first.
  python3 scripts/forge/hub-files.py check (--files <path>... | --base <rev> [--head <rev>]) [--ref <ref>] [--fail]
      the given files, or the files changed in <base>...<head> under `paths`, that are hubs (`hub`) or that this
      change makes one (`new-hub`: one edit below the threshold). --fail exits 1 when any is listed.
Each command ends with the summary line `hub-files: ...`. When `hubFiles` is unset (`{}` or absent), the command
prints one line saying so and exits 0 (the manual form: the hub list is made by hand from the integration ref's
history). Exit codes: 0 done, nothing listed with --fail, or `hubFiles` unset; 1 something listed with --fail;
2 the binding file is invalid, or git fails. A missing binding file counts as every key unset: one line (`no .claude/quality-profile.json; run python3
scripts/forge/quality_profile.py init`) and exit 0.

Standard library only. Tests: `tests/scripts/forge/test_hub_files.py`.
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality_profile  # noqa: E402  (sibling module; path set above)


class HubError(Exception):
    """A git call failed or the binding is unusable."""


def git(repo: str, *args: str) -> str:
    """Stdout of one git command in the repository; a failure raises HubError."""
    result = subprocess.run(["git", "-C", repo, "-c", "core.quotepath=off", *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise HubError(f"git {args[0]}: {result.stderr.strip()}")
    return result.stdout


def in_scope(path: str, section: dict) -> bool:
    """Under one of `paths` and matching none of `ignore`."""
    under = any(path == p.rstrip("/") or path.startswith(p.rstrip("/") + "/") for p in section["paths"])
    return under and not any(fnmatch.fnmatchcase(path, glob) for glob in section.get("ignore", []))


def edit_counts(repo: str, section: dict, ref: str) -> tuple[dict[str, int], int]:
    """Per file in scope, how many of the newest `window` feature commits on `ref` edited it; and the commits read."""
    pattern = re.compile(section["commitPattern"])
    commits = []
    for line in git(repo, "log", "--first-parent", "--format=%H%x09%s", ref).splitlines():
        sha, _, subject = line.partition("\t")
        if pattern.search(subject):
            commits.append(sha)
            if len(commits) == section["window"]:
                break
    counts: dict[str, int] = {}
    if commits:
        # A merge commit (a merge-commit workflow) lists its change against the first parent, as a squash would.
        out = git(repo, "show", "--no-renames", "--name-only", "-m", "--first-parent", "--format=@%H", *commits)
        for name in {(sha, path) for sha, path in _pairs(out)}:
            if in_scope(name[1], section):
                counts[name[1]] = counts.get(name[1], 0) + 1
    return counts, len(commits)


def _pairs(out: str):
    """(commit, path) pairs of a `git show --name-only --format=@%H` listing."""
    sha = ""
    for line in out.splitlines():
        if line.startswith("@"):
            sha = line[1:]
        elif line.strip():
            yield sha, line.strip()


def classify(paths: list[str], counts: dict[str, int], threshold: int) -> list[tuple[str, int, str]]:
    """(kind, count, path) for each given path that is a hub or becomes one with this change, most edits first."""
    rows = []
    for path in sorted(set(paths)):
        count = counts.get(path, 0)
        if count >= threshold:
            rows.append(("hub", count, path))
        elif count + 1 >= threshold:
            rows.append(("new-hub", count + 1, path))
    return sorted(rows, key=lambda row: (-row[1], row[2]))


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", default=quality_profile.DEFAULT_PROFILE)
    sub = parser.add_subparsers(dest="command", required=True)
    p_list = sub.add_parser("list")
    p_list.add_argument("--ref")
    p_check = sub.add_parser("check")
    p_check.add_argument("--ref")
    p_check.add_argument("--files", nargs="+")
    p_check.add_argument("--base")
    p_check.add_argument("--head", default="HEAD")
    p_check.add_argument("--fail", action="store_true")
    args = parser.parse_args(argv)
    repo = os.path.dirname(os.path.dirname(os.path.abspath(args.profile)))
    try:
        profile = quality_profile.load(args.profile)
        problems = quality_profile.validate(profile, repo=repo)
        section = quality_profile.configured(profile).get("hubFiles")
        if problems:
            raise HubError("quality profile: " + "; ".join(problems))
        if not section:
            print("hub-files: hubFiles is unset in the quality profile; list the hubs by hand")
            return 0
        # Product code lives in the source root (wrapper mode: a nested repository); `paths`, `ignore` and the given
        # files are relative to it, and the ref is resolved there.
        workspace, repo = repo, quality_profile.source_root(repo)
        section = dict(section, **{k: [quality_profile.source_path(p, workspace) for p in section[k]]
                                   for k in ("paths", "ignore") if k in section})
        ref = args.ref or profile.get("integrationRef") or "HEAD"
        counts, read = edit_counts(repo, section, ref)
        window, threshold = section["window"], section["threshold"]
        scope = f"{read} feature commit(s) on {ref}, threshold {threshold}"
        if args.command == "list":
            hubs = sorted(((c, p) for p, c in counts.items() if c >= threshold), key=lambda x: (-x[0], x[1]))
            for count, path in hubs:
                print(f"hub {count}/{read} {path}")
            print(f"hub-files: {len(hubs)} hub(s) ({scope})")
            return 0
        if bool(args.files) == bool(args.base):
            parser.error("check needs exactly one of --files and --base")
        if args.files:
            paths = [quality_profile.source_path(os.path.normpath(f), workspace) for f in args.files]
        else:
            changed = git(repo, "diff", "--name-only", "--no-renames", f"{args.base}...{args.head}", "--",
                          *section["paths"])
            paths = [p for p in changed.splitlines() if p.strip()]
        rows = classify([p for p in paths if in_scope(p, section)], counts, threshold)
        for kind, count, path in rows:
            print(f"{kind} {count}/{window} {path}")
        hubs = sum(1 for kind, _, _ in rows if kind == "hub")
        print(f"hub-files: {hubs} hub(s), {len(rows) - hubs} new hub(s) among {len(paths)} file(s) ({scope})")
        return 1 if args.fail and rows else 0
    except quality_profile.MissingProfile:
        print(f"hub-files: {quality_profile.MISSING}")
        return 0
    except (HubError, quality_profile.ProfileError) as exc:
        print(f"hub-files: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
