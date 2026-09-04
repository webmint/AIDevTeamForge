"""tests/lib/_configure/test_command_tiers.py

Maintainer test (a live-tree gate, not a consumer-facing test -- the same
shape as tests/lib/test_model_version_tripwire.py's TestLiveSrc and
tests/lib/test_breakdown_helper.py's `_DONE_WHEN_FIXED_LINES` byte-
consistency pin) that pins `_agent_models.COMMAND_TIERS` against the
eight advisory lines' own tier words in `src/commands/<name>/main.md`
(94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md D1, Phase 1 Deliverable 1,
ratified 2026-09-04).

Every command source that carries the line `"This command's judgment
work belongs to the <tier> tier..."` is read from the LIVE repo tree (not
a hand-authored fixture) and its tier word compared against
COMMAND_TIERS[<command name>]. This is what makes a future edit that
changes one side alone -- widening COMMAND_TIERS without updating the
matching advisory line's prose, or vice versa -- fail loudly here instead
of drifting silently, mirroring plan 89's `storage-rules.md` <->
`_DONE_WHEN_FIXED_LINES` precedent this test's own author (94's Phase 1
Deliverable 1) cites.

Two of the four tests below prove the pin is genuinely LIVE, on both
sides, by mutating a COPY (never the real tree) and showing the
comparison then fails -- reasoning about it is not enough (plan 92 D2/D3
precedent for the equality-pin family this test belongs to).

Stdlib only.
"""

from __future__ import annotations

import re
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_COMMANDS_DIR = _REPO_ROOT / "src" / "commands"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _configure._agent_models import COMMAND_TIERS, VALID_TIERS  # noqa: E402

# Matches the advisory line's own construction, byte-identical across all
# eight command sources modulo the tier word (fact 10 of plan 94's
# `## Verified mechanics`): "...judgment work belongs to the think tier;
# configured think model: ...".
_ADVISORY_RE = re.compile(r"judgment work belongs to the (\w+) tier")


def _find_advisory_tier(main_md_path: Path):
    """Return the tier word from `main_md_path`'s FIRST advisory-line
    match, or None if the file carries no such line at all."""
    text = main_md_path.read_text(encoding="utf-8")
    match = _ADVISORY_RE.search(text)
    return match.group(1) if match else None


def _live_advisory_tiers():
    """{command_name: tier_word} for every src/commands/<name>/main.md
    under the LIVE repo tree that carries the advisory line."""
    result = {}
    for main_md in sorted(_COMMANDS_DIR.glob("*/main.md")):
        tier = _find_advisory_tier(main_md)
        if tier is not None:
            result[main_md.parent.name] = tier
    return result


class CommandTiersConsistencyTests(unittest.TestCase):
    def test_every_command_tiers_value_is_a_valid_tier(self):
        """COMMAND_TIERS' values must themselves be resolvable tiers --
        this is what would catch a COMMAND_TIERS entry pointing at a
        retired tier name (e.g. "scan") or a typo that VALID_TIERS
        itself would reject at apply time, but here BEFORE any file is
        ever touched (python-reviewer run B finding 5)."""
        for name, tier in COMMAND_TIERS.items():
            self.assertIn(
                tier, VALID_TIERS,
                "{0}: COMMAND_TIERS points at {1!r}, which is not in "
                "VALID_TIERS {2!r}".format(name, tier, VALID_TIERS),
            )

    def test_every_command_tiers_member_matches_its_advisory_line(self):
        """(a) No COMMAND_TIERS member is missing its advisory line, and
        no member's tier disagrees with what that line prints."""
        live = _live_advisory_tiers()
        for name, tier in COMMAND_TIERS.items():
            self.assertIn(
                name, live,
                "{0} is in COMMAND_TIERS but its main.md carries no "
                "advisory line".format(name),
            )
            self.assertEqual(
                tier, live[name],
                "{0}: COMMAND_TIERS says {1!r}, the advisory line says "
                "{2!r}".format(name, tier, live[name]),
            )

    def test_every_advisory_line_command_is_a_command_tiers_member(self):
        """(b) No command carries the advisory line without being a
        COMMAND_TIERS member -- the map has no line without a member,
        the mirror of the first test's "no member without a line"."""
        live = _live_advisory_tiers()
        for name in live:
            self.assertIn(
                name, COMMAND_TIERS,
                "{0}'s main.md carries the advisory line but {0} is not "
                "a COMMAND_TIERS member".format(name),
            )

    def test_exactly_eight_commands_pinned(self):
        """Both sides agree on the SET, not just pairwise on its
        members -- a stray ninth entry on either side would slip past
        the two tests above if it happened to equal a real pair."""
        live = _live_advisory_tiers()
        self.assertEqual(len(COMMAND_TIERS), 8)
        self.assertEqual(len(live), 8)
        self.assertEqual(set(COMMAND_TIERS), set(live))

    def test_mutated_map_value_fails_the_comparison(self):
        """(c), map side: a COPY of COMMAND_TIERS with one value changed
        no longer matches the live advisory lines -- proves the pin is
        live from the map's side, not merely reasoned about."""
        live = _live_advisory_tiers()
        mutated = dict(COMMAND_TIERS)
        name = next(iter(mutated))
        original = mutated[name]
        mutated[name] = "verify" if original != "verify" else "think"
        self.assertNotEqual(mutated[name], live[name])
        # COMMAND_TIERS itself is untouched by the mutation above.
        self.assertEqual(COMMAND_TIERS[name], original)

    def test_mutated_advisory_line_in_a_temp_copy_fails_the_comparison(self):
        """(c), advisory-line side: editing a TEMP COPY of one command's
        main.md (never the real tree) to name a different tier makes
        _find_advisory_tier disagree with COMMAND_TIERS -- proves the
        pin is live from the advisory-line's side too."""
        name = next(iter(COMMAND_TIERS))
        real_tier = COMMAND_TIERS[name]
        real_path = _COMMANDS_DIR / name / "main.md"
        text = real_path.read_text(encoding="utf-8")
        replacement_tier = "verify" if real_tier != "verify" else "think"
        mutated_text, n = _ADVISORY_RE.subn(
            "judgment work belongs to the {0} tier".format(replacement_tier),
            text,
            count=1,
        )
        self.assertEqual(n, 1, "{0}'s main.md has no advisory line to mutate".format(name))
        self.assertNotEqual(mutated_text, text)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / "main.md"
            tmp_path.write_text(mutated_text, encoding="utf-8")
            mutated_tier = _find_advisory_tier(tmp_path)

        self.assertEqual(mutated_tier, replacement_tier)
        # This IS the assertion the real consistency test makes -- it
        # now fails, because the temp copy disagrees with the (real,
        # unmutated) map.
        self.assertNotEqual(mutated_tier, COMMAND_TIERS[name])
        # And the REAL tree is untouched -- this test only ever wrote
        # into a TemporaryDirectory.
        self.assertEqual(real_path.read_text(encoding="utf-8"), text)


if __name__ == "__main__":
    unittest.main()
