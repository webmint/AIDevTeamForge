"""CLI handler for grill_helper's merge-passes verb.

SRP split from _cli.py (review finding 2, post-initial-wiring pass):
_cli.py was already 1527 lines before merge-passes was added, well past the
project's >600-line automatic-HIGH module-split threshold, and adding a new
verb's full body pushed it further over. `cmd_resolve_scope` in _cli.py
already established the escape: a two-line delegator in _cli.py
(`from ._scope import cmd_resolve_scope as _impl; return _impl(args)`) with
the real implementation living in its own module. This file is that same
pattern applied to merge-passes. Registration (the _SUBCOMMAND_REGISTRY
entry) and the argparse block stay in _cli.py -- that is wiring, not
implementation, and belongs with the other verbs' wiring.

Deliberately NOT part of _merge.py: _merge.py is pure logic (no argparse,
no sys, no json, no file I/O) and is reviewed as such. Mixing CLI plumbing
into it would undo that separation. See _merge.py's own module docstring.

Public surface: cmd_merge_passes(args) -> int (registered in _cli.py).

Stdlib only. Python 3.8+. No from __future__ import annotations.
"""

import json
import sys


def cmd_merge_passes(args):
    # type: (object) -> int
    """CLI handler for the merge-passes verb.

    Union-merge exactly 2 pass pools of validated findings.

    Delegates to _merge.merge_two_passes -- a UNION, not a majority/quorum
    rule (see _merge.py's module docstring). A finding present in exactly
    ONE pass MUST survive; this is NOT plan 62's spec-formalizer reproduce-
    across-passes rule, which would wrongly suppress it. This CLI layer
    does not reinterpret that semantics -- it only parses the two pool
    files, validates their shape, and prints merge_two_passes's return
    value verbatim.

    Mirrors /devforge:audit's `merge-passes --pools` contract (same flag
    name, same accept-bare-array-or-{"passed": [...]}-object tolerance,
    same error-message shapes) closely enough that one pattern covers both
    readers. It diverges where grill's semantics diverge from audit's: no
    glob expansion, no N-pass generalization -- --pools takes EXACTLY 2
    paths (argparse nargs=2 enforces the count before this handler ever
    runs, registered in _cli.py), and ORDER is significant: the first path
    is pass_a, the second is pass_b. merge_two_passes emits all of pass_a's
    findings first (in order), then any pass_b finding whose
    (file, line, pattern) identity was not already seen in pass_a.

    Expected args attributes:
      pools  list[str]  exactly 2 pool file paths, in (pass_a, pass_b) order

    Input: --pools PATH_A PATH_B  (each file: a JSON array of ParsedFinding
                                    dicts, or a validate-findings output
                                    object with a 'passed' key; every
                                    top-level element of the resolved list
                                    must be a JSON object)
    Returns 0 on success, printing the merged BARE JSON array to stdout.
    Returns 2 on missing/unreadable/malformed pool file -- including a
    pool whose resolved findings list contains a non-dict element (review
    finding 1: this used to raise an unhandled AttributeError deep inside
    merge_two_passes's dict.get() calls; every other malformed-shape branch
    in this function already produces a clean stderr message + exit 2, so
    that inconsistency was a defect in the error contract, not a gap).
    """
    from ._merge import merge_two_passes

    pool_paths = args.pools

    pools = []
    for path in pool_paths:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except OSError as exc:
            sys.stderr.write(
                "grill_helper merge-passes: cannot read pool file {0!r}: "
                "{1}\n".format(path, exc)
            )
            return 2
        except json.JSONDecodeError as exc:
            sys.stderr.write(
                "grill_helper merge-passes: pool file {0!r} is not valid "
                "JSON: {1}\n".format(path, exc)
            )
            return 2

        if isinstance(raw, dict) and "passed" in raw:
            pool_findings = raw["passed"]
            if not isinstance(pool_findings, list):
                sys.stderr.write(
                    "grill_helper merge-passes: pool file {0!r} has "
                    "'passed' key but its value is not a JSON array\n".format(
                        path
                    )
                )
                return 2
        elif isinstance(raw, list):
            pool_findings = raw
        else:
            sys.stderr.write(
                "grill_helper merge-passes: pool file {0!r} must be a JSON "
                "array or an object with a 'passed' key\n".format(path)
            )
            return 2

        # Finding 1: every element of the resolved findings list must be a
        # JSON object. merge_two_passes reads finding.get("file", ...) etc.
        # on each element; a non-dict element (e.g. a bare string or int)
        # crashes that with an unhandled AttributeError instead of the
        # clean exit-2 every other malformed-shape branch above produces.
        # Checked here, once, after pool_findings is resolved from EITHER
        # branch, so both the bare-array and the "passed"-wrapper shapes
        # are covered by one check.
        if not all(isinstance(f, dict) for f in pool_findings):
            sys.stderr.write(
                "grill_helper merge-passes: pool file {0!r} must contain "
                "only JSON objects (ParsedFinding dicts)\n".format(path)
            )
            return 2

        pools.append(pool_findings)

    merged = merge_two_passes(pools[0], pools[1])
    sys.stdout.write(json.dumps(merged, indent=2, sort_keys=True) + "\n")
    return 0
