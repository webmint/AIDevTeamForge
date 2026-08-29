"""Internal package for artifact_helper (commit-artifacts + find-feature-artifacts).

Exposes the shared WIP artifact-commit discipline and shared feature-dir
artifact discovery for pipeline commands (/research, /discover, /specify,
/spec-check, /plan, /grill, /breakdown, /review, /fix, /verify, /finalize,
/summarize).

Public entry point is `main` (re-exported below). Subcommand verbs are wired
in `_cli.py`; `main` dispatches to the selected handler. commit-artifacts's
own logic stays in `_cli.py`; find-feature-artifacts's logic lives in
`_cmds_find_artifacts.py` (one module per verb, per this repository's
module-split discipline).

Verbs shipped:
  commit-artifacts        -- stage explicit artifact paths + WIP commit to
                              install root
  find-feature-artifacts  -- locate a named artifact (or set of artifacts)
                              across every feature dir under specs/,
                              regardless of directory-nesting shape (91-
                              FEATURE-DIR-IDENTITY-AND-PROVENANCE-PLAN.md
                              Phase 1b)
"""

from ._cli import main

__all__ = ["main"]
