"""cmd_seed_universal — seeds all 11 canonical universal sections into
constitute.json from the canonical constitution.md (D3(a), plan 104 Phase 3).

Single responsibility: this module owns the seed-universal verb only. State
I/O goes through ``_state_transaction`` (``_state.py``); canonical-text
parsing goes through ``_parse_universal_blocks`` (``_universal.py``); this
module's own job is mapping each parsed canonical section onto its target
bucket/section and replacing it wholesale.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ._schema import _PATTERNS_BUCKET_TO_SECTION, _UNIVERSAL_SECTIONS
from ._state import _state_transaction
from ._universal import _parse_universal_blocks
from ._validators import _die

# Inverse of _PATTERNS_BUCKET_TO_SECTION: §-number key -> patterns bucket name.
_SECTION_TO_PATTERNS_BUCKET = {
    v: k for k, v in _PATTERNS_BUCKET_TO_SECTION.items()
}


def _rules_from_canonical(section_data: dict) -> list:
    """Build the stored rule-record list for one canonical section.

    Every rule is tagged "universal" and carries its canonical ``name`` —
    the helper owns tag + name here; the model composes nothing.
    """
    return [
        {"tag": "universal", "name": r["name"], "text": r["body"]}
        for r in section_data.get("rules", [])
    ]


def _seed_section_array(bucket: list, number: str, heading: str, rules: list) -> None:
    """Replace-or-append one section record identified by ``number`` in
    ``bucket``, in place.

    Idempotent: a second seed with identical canonical content replaces
    the existing record AT THE SAME POSITION, so re-running seed-universal
    never duplicates a section and never reorders the bucket.

    Replacement is unconditional on the EXISTING record's tag or content:
    a pre-existing section already occupying a universal ``number`` — e.g.
    a project-specific §3.5 a user composed by hand, with its own rules —
    is wholesale-replaced by the canonical universal section, silently.
    This is intended (D3(a): the helper owns every universal number, and
    `/devforge:constitute` runs `reset` immediately before seeding), not a
    defensive gap to close here.
    """
    new_section = {
        "number": number,
        "title": heading,
        "tag": "universal",
        "description": None,
        "rules": rules,
        "tables": [],
        "code_examples": [],
    }
    for i, existing in enumerate(bucket):
        if existing.get("number") == number:
            bucket[i] = new_section
            return
    bucket.append(new_section)


def _apply_seed(state: dict, canonical_blocks: dict) -> None:
    """Write all 11 ``_UNIVERSAL_SECTIONS`` entries from ``canonical_blocks``
    into ``state``, in place.

    §3.5-§3.8 -> ``code_quality_standards``; §6.1-§6.4 -> ``workflow_rules``
    (replace-or-append by section ``number``, metadata + rules wholesale).
    §4.1-§4.3 -> the matching ``*_universal`` patterns-and-antipatterns
    bucket, REPLACED wholesale; the ``*_project_specific`` buckets are never
    touched. Assumes every key in ``_UNIVERSAL_SECTIONS`` is present in
    ``canonical_blocks`` — the caller validates that before opening the
    state transaction.
    """
    for sect_key in _UNIVERSAL_SECTIONS:
        data = canonical_blocks[sect_key]
        number = sect_key[1:]  # strip leading "§"
        heading = data["heading"]
        rules = _rules_from_canonical(data)

        if sect_key in _SECTION_TO_PATTERNS_BUCKET:
            bucket_name = _SECTION_TO_PATTERNS_BUCKET[sect_key]
            state["patterns_and_antipatterns"][bucket_name] = rules
        elif number.startswith("3."):
            _seed_section_array(state["code_quality_standards"], number, heading, rules)
        else:
            _seed_section_array(state["workflow_rules"], number, heading, rules)


def cmd_seed_universal(args: argparse.Namespace) -> int:
    """Seed all 11 ``_UNIVERSAL_SECTIONS`` from the canonical constitution.md.

    Default ``--canonical-path``: ``<devforge-dir>/templates/constitution.md``
    — the D2(d) ``templateOwned`` carrier target (``src/manifest.json`` maps
    ``src/constitution.md`` there; refreshed on every ``update.sh`` run).

    Reads the canonical file with ``_parse_universal_blocks``, then writes
    every universal section/bucket into ``.devforge/constitute.json``,
    replacing each wholesale (idempotent — a byte-identical canonical file
    re-seeded twice produces a byte-identical ``constitute.json``). The
    helper owns every number, heading, tag and rule name written; the model
    composes nothing here.

    Exit 1: canonical file missing / unreadable (``OSError`` from the
        parser's ``Path.read_text`` — e.g. ``FileNotFoundError``,
        ``PermissionError``, ``IsADirectoryError``). State NOT written.
    Exit 2: canonical file readable but missing one or more of the 11
        ``_UNIVERSAL_SECTIONS`` keys — named on stderr. State NOT written.
    Exit 0: success, silent (matches the other setters — no stdout output).
    """
    canonical_path = args.canonical_path
    if canonical_path is None:
        canonical_path = str(Path(args.devforge_dir) / "templates" / "constitution.md")

    try:
        canonical_blocks = _parse_universal_blocks(canonical_path)
    except OSError as err:
        return _die("seed-universal: cannot read canonical file: {0}".format(err))

    missing_keys = [k for k in _UNIVERSAL_SECTIONS if k not in canonical_blocks]
    if missing_keys:
        return _die(
            "seed-universal: canonical file is missing section(s): {0}".format(
                ", ".join(missing_keys)
            ),
            code=2,
        )

    try:
        with _state_transaction(args.devforge_dir) as state:
            _apply_seed(state, canonical_blocks)
    except (OSError, json.JSONDecodeError) as err:
        return _die("seed-universal: {0}".format(err))

    return 0
