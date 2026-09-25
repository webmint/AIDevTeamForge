"""cmd_drop_rule + cmd_drop_section — D6(a) universal-override setters.

Moved out of ``_cmds_set.py`` in a behavior-preserving restructure (plan 104
Phase 3 Unit D follow-up): the module was pushed past the 600-line
automatic-HIGH-finding threshold. No logic, message text or exit code
changed in the move — see ``_cmds_seed.py`` for the sibling-module pattern
this mirrors.
"""

from __future__ import annotations

import argparse
import json

from ._schema import _PATTERN_SCOPE_TO_SUFFIX
from ._state import _find_section, _load, _state_transaction
from ._validators import _die


def cmd_drop_rule(args: argparse.Namespace) -> int:
    """Remove one rule by 1-based --index, from a section or a pattern bucket.

    Exactly one target form:
      - ``--section <number> --index <i>`` — remove rule *i* of that section
        (same lookup as ``add-rule``).
      - ``--bucket <always|never|prefer> --scope <universal|project-specific>
        --index <i>`` — remove rule *i* of that patterns_and_antipatterns
        bucket (same key construction as ``add-pattern-rule``).

    D6(a) (plan 104 Phase 3 Unit D): overrides stay available against
    universal sections seeded by ``seed-universal`` — a user who drops a
    seeded universal rule (optionally re-adding a project-specific
    replacement via ``add-rule``) is a deliberate divergence the drift
    detector then reports, by design.

    Any other combination (both forms given, neither given, --bucket
    without --scope or vice versa), a section/number that does not exist,
    or an out-of-range --index → exit 2, state NOT written.
    """
    section_given = args.section is not None
    pattern_given = args.bucket is not None or args.scope is not None

    if section_given and pattern_given:
        return _die(
            "drop-rule: specify exactly one of --section or --bucket/--scope, not both",
            code=2,
        )
    if not section_given and not pattern_given:
        return _die(
            "drop-rule: specify --section, or both --bucket and --scope",
            code=2,
        )
    if pattern_given and (args.bucket is None or args.scope is None):
        return _die(
            "drop-rule: --bucket and --scope must be given together",
            code=2,
        )
    if args.bucket is not None and args.bucket not in {"always", "never", "prefer"}:
        return _die(
            "drop-rule: unknown bucket {0!r}; allowed: {1}".format(
                args.bucket, sorted(["always", "never", "prefer"])
            ),
            code=2,
        )
    if args.scope is not None and args.scope not in _PATTERN_SCOPE_TO_SUFFIX:
        return _die(
            "drop-rule: unknown scope {0!r}; allowed: {1}".format(
                args.scope, sorted(_PATTERN_SCOPE_TO_SUFFIX.keys())
            ),
            code=2,
        )

    index = args.index
    if index < 1:
        return _die("drop-rule: --index must be >= 1 (1-based)", code=2)

    try:
        prev_state = _load(args.devforge_dir)
    except (OSError, ValueError) as err:
        return _die("drop-rule: {0}".format(err))

    pattern_key = None
    if section_given:
        _bucket_ro, section_ro = _find_section(prev_state, args.section)
        if section_ro is None:
            return _die(
                "drop-rule: section {0!r} not found".format(args.section), code=2
            )
        rule_count = len(section_ro.get("rules", []))
        if index > rule_count:
            return _die(
                "drop-rule: index {0} out of range for section {1!r} "
                "({2} rule(s))".format(index, args.section, rule_count),
                code=2,
            )
    else:
        pattern_key = "{0}_{1}".format(args.bucket, _PATTERN_SCOPE_TO_SUFFIX[args.scope])
        rule_count = len(prev_state["patterns_and_antipatterns"][pattern_key])
        if index > rule_count:
            return _die(
                "drop-rule: index {0} out of range for bucket {1!r} "
                "({2} rule(s))".format(index, pattern_key, rule_count),
                code=2,
            )

    try:
        with _state_transaction(args.devforge_dir) as state:
            if section_given:
                _bucket, section = _find_section(state, args.section)
                assert section is not None, (
                    "drop-rule: section {0!r} disappeared between check and "
                    "lock".format(args.section)
                )
                del section["rules"][index - 1]
            else:
                del state["patterns_and_antipatterns"][pattern_key][index - 1]
    except (OSError, json.JSONDecodeError) as err:
        return _die("drop-rule: {0}".format(err))
    return 0


def cmd_drop_section(args: argparse.Namespace) -> int:
    """Remove the section identified by --number (same lookup as add-rule).

    D6(a) (plan 104 Phase 3 Unit D): dropping an entire seeded universal
    section is a deliberate divergence the drift detector then reports, by
    design — the override grammar stays available against universal
    sections.

    Section not found → exit 2, state unchanged.
    """
    number = args.number

    try:
        prev_state = _load(args.devforge_dir)
    except (OSError, ValueError) as err:
        return _die("drop-section: {0}".format(err))
    _bucket_ro, section_ro = _find_section(prev_state, number)
    if section_ro is None:
        return _die("drop-section: section {0!r} not found".format(number), code=2)

    try:
        with _state_transaction(args.devforge_dir) as state:
            bucket, section = _find_section(state, number)
            assert section is not None, (
                "drop-section: section {0!r} disappeared between check and "
                "lock".format(number)
            )
            for i, candidate in enumerate(bucket):
                if candidate is section:
                    del bucket[i]
                    break
    except (OSError, json.JSONDecodeError) as err:
        return _die("drop-section: {0}".format(err))
    return 0
