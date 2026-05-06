"""Per-source-file .md skeleton flow for the per-md validator-loop Part B architecture.

This module owns the `render-file-skeletons` subcommand (Step B.1 of
VALIDATOR-LOOP-B-PLAN.md). For each source file registered in
index.json under `src/<concern>/`, it writes an empty zero-byte .md
file to `docs/<package>/<concern>/<suffix>.md`. These skeletons become
the filesystem forcing function for Part B: Step B.2 will gate
`validate-concern` on the docs tree being non-empty per file.

v0 scope: skeleton creation only (zero-byte files). B.3 will add
`_write_md_with_frontmatter` for filled-skeleton emit. DO NOT add
frontmatter or content writing here — that's B.3's responsibility.

Stdlib only. Targets Python 3.8+.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from ._render import _project_root
from ._setters_concern import _load_index_files, _path_contains_trivial_dir
from ._state import (
    StateLoadError,
    _die,
    _load_state,
    _require_concern,
    _require_package,
    _state_file_path,
)
from ._validation import _validate_string


def cmd_render_file_skeletons(args: argparse.Namespace) -> int:
    """Walk index.json files for the concern subfolder; write empty .md skeletons.

    B.1 is filesystem-only — no state mutation occurs. The index.json is the
    authoritative file list; a missing index is a hard failure (DO NOT degrade
    gracefully) because without it the skeleton set is incomplete and the B.2
    forcing function breaks.
    """
    try:
        _validate_string(args.package, "--package")
        _validate_string(args.concern, "--concern")
    except ValueError as err:
        return _die(str(err), code=2)

    try:
        state = _load_state()
    except StateLoadError as err:
        return _die(str(err), code=1)

    if _require_package(state, args.package) is None:
        return _die(
            "package not registered at {0!r}; run add-package first".format(
                args.package
            ),
            code=2,
        )

    if _require_concern(state, args.package, args.concern) is None:
        return _die(
            "concern {0!r} not registered under {1}; run add-concern first".format(
                args.concern, args.package
            ),
            code=2,
        )

    devforge_dir = _state_file_path().parent
    project_root = _project_root()

    files = _load_index_files(devforge_dir, args.package)
    # DO NOT degrade gracefully on missing index — see B.1 §step 5. The index
    # is the structural backbone; silent skip would break the Part-B forcing
    # function entirely.
    if files is None:
        return _die(
            "index.json missing or package {0!r} not in index"
            " — run init-forge build-index first".format(args.package),
            code=2,
        )

    subfolder_prefix = "src/{0}/".format(args.concern)

    created = 0
    preexisting = 0
    any_matched = False

    for rel_path in files:
        if not rel_path.startswith(subfolder_prefix):
            continue
        if _path_contains_trivial_dir(rel_path):
            continue

        suffix = rel_path[len(subfolder_prefix):]
        # Skip directory-only entries (rel_path equals subfolder_prefix exactly).
        # Without this guard the target would become "<docs>/<P>/<C>/.md" — a
        # spurious hidden dotfile.
        if not suffix:
            continue
        any_matched = True
        target = (
            project_root
            / "docs"
            / args.package
            / args.concern
            / (suffix + ".md")
        )

        if target.exists():
            preexisting += 1
            continue

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"")
        except OSError as err:
            return _die(
                "failed to write {0}: {1}".format(target, err),
                code=1,
            )
        created += 1

    if not any_matched:
        sys.stderr.write(
            "render-file-skeletons: no source files under {0} for {1}/{2}"
            " — concern subfolder may not exist\n".format(
                subfolder_prefix, args.package, args.concern
            )
        )

    sys.stdout.write(
        "render-file-skeletons {0}/{1}: created={2} preexisting={3}\n".format(
            args.package, args.concern, created, preexisting
        )
    )
    return 0
