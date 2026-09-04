"""Tests for `src/devforge/lib/_configure/_agent_models.py` -- the pure
frontmatter-rewrite logic behind `configure_helper apply-models`
(92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md Phase 1, Deliverable 3;
extended over commands + re-based off the deleted default-map by
94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md D1/D2/D3, Phase 1 Deliverable
5, ratified 2026-09-04).

The default-map-equality test that used to live here (pinning this
module's `CLAUDE_AGENT_DEFAULTS_BY_TIER` against the sibling default-map
module that used to live under `scripts/lib/`) was DELETED, and so was
the literal itself: plan 94 D2 removes the whole sibling module
(`scripts/lib/install_defaults.py`) outright, and this module's own copy
along with it -- a pin over a literal that no longer exists on either
side would be dead weight reading as a live constraint. The tier-
validity check and the null-tier fallback that used to read that literal
now read `VALID_TIERS` (a plain tuple, no default values) and a
class-dependent literal (`"inherit"` for an agent, `None` for a command)
respectively -- see `_resolve_tier`'s own docstring.

Split out of `tests/lib/_configure/test_apply_agent_models.py` (which grew
past this repo's 600-line test-file threshold) to mirror that module's own
split: `test_apply_agent_models.py` covers the CLI/command layer
(`_cmds_agent_models.py`, exercised via subprocess through the real
`configure_helper` + `scripts/generate-agents.py` + `scripts/emitters/
claude.py` producers); THIS file covers `_agent_models.py` directly -- no
subprocess, no filesystem round-trip, just the pure function.

`PureFunctionEdgeCaseTests` exercises `_agent_models.plan_rewrite` on
hand-crafted frontmatter for shapes the real emitter/producer chain
cannot currently produce: a `model_tier:` line with no sibling `model:`
line (malformed by construction, since the emitter never writes one
without the other), a file where `model:` is the LAST frontmatter line
(the real emitter always follows it with `model_tier:` and/or
`applies_to:`), and (added by plan 94 Deliverable 5) the `kind="command"`
path's edge cases -- an unmapped/never-configured tier, a command
carrying no `description:` line to anchor an inserted line after, and a
tier that configures an effort but no model. These are internal-function
unit tests, not round-tripped producer output, and are labelled as such
throughout.

Stdlib only.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _configure import _agent_models  # noqa: E402


# ---- VALID_TIERS <-> _TIER_CONFIG_KEYS key-set pin (python-reviewer run B
# finding 1). Two hand-kept literals -- nothing else in the module pins
# their key sets equal, and _resolve_tier's own defensive .get() default
# was removed in favor of a direct index precisely so a desync between
# them fails LOUDLY (a KeyError at that one call site) rather than
# silently resolving to "not configured". This test is the other half of
# that fix: it catches the desync BEFORE it ever reaches a real call. ----

class TierKeySetConsistencyTests(unittest.TestCase):
    def test_valid_tiers_and_tier_config_keys_have_the_same_key_set(self):
        self.assertEqual(set(_agent_models.VALID_TIERS), set(_agent_models._TIER_CONFIG_KEYS))


# ---- Pure-function edge cases plan_rewrite touches that the real producer
# chain cannot currently exercise (see module docstring). ----

class PureFunctionEdgeCaseTests(unittest.TestCase):
    def test_scan_tier_is_retired_and_now_raises_as_an_unknown_tier(self):
        """model_tier: scan had zero real members even before it was
        retired (plan 92 OQ-3 kept it only because the now-deleted
        default map gave it meaning); plan 94 D2 part 4 removes it from
        VALID_TIERS outright, reversing that OQ-3 answer. A file
        declaring it is therefore no longer a resolvable tier -- it is
        an UNKNOWN one, exercised here directly since no real
        src/agents/*.md source ever declared it."""
        text = (
            "---\n"
            "name: hypothetical-scanner\n"
            "description: \"A hypothetical scan-tier agent.\"\n"
            "model: haiku\n"
            "model_tier: scan\n"
            "---\n"
            "\n"
            "Body.\n"
        )
        tier_models, tier_efforts = _agent_models.extract_tier_config({})
        with self.assertRaises(_agent_models.AgentValidationError) as ctx:
            _agent_models.plan_rewrite(text, tier_models, tier_efforts)
        self.assertIn("scan", str(ctx.exception))
        for name in _agent_models.VALID_TIERS:
            self.assertIn(name, str(ctx.exception))

    def test_model_tier_without_model_line_raises_validation_error(self):
        """model_tier: present with no sibling model: line is malformed
        by construction -- the real emitter never writes one without the
        other -- so this hand-crafted shape exercises plan_rewrite's own
        defensive check directly."""
        text = (
            "---\n"
            "name: malformed\n"
            "description: \"Missing its model: line.\"\n"
            "model_tier: do\n"
            "---\n"
            "\n"
            "Body.\n"
        )
        tier_models, tier_efforts = _agent_models.extract_tier_config(
            {"CLAUDE_TIER_DO": "sonnet"}
        )
        with self.assertRaises(_agent_models.AgentValidationError):
            _agent_models.plan_rewrite(text, tier_models, tier_efforts)

    def test_effort_inserted_when_model_is_last_frontmatter_line(self):
        """The real emitter never places `model:` as the LAST
        frontmatter line before the closing '---' -- `model_tier:`
        and/or `applies_to:` always follow it -- so this hand-crafted
        shape is the only way to exercise the insert-at-model_idx+1
        path when that position coincides with the closing fence's own
        position (python-reviewer run B finding 12). The do tier's
        model is left unconfigured here (only CLAUDE_EFFORT_DO is set),
        so the existing `model: sonnet` line is REWRITTEN to the
        literal `model: inherit` (plan 94 D2 -- an unconfigured agent
        tier always resolves to "inherit", never a static default)."""
        text = (
            "---\n"
            "name: minimal\n"
            "description: \"model: is the last frontmatter line.\"\n"
            "model_tier: do\n"
            "model: sonnet\n"
            "---\n"
            "\n"
            "Body.\n"
        )
        tier_models, tier_efforts = _agent_models.extract_tier_config(
            {"CLAUDE_EFFORT_DO": "high"}
        )
        new_text, decision = _agent_models.plan_rewrite(text, tier_models, tier_efforts)
        self.assertEqual(decision["status"], "applied")
        self.assertEqual(decision["model"], "inherit")
        self.assertEqual(decision["effort"], "high")

        new_lines = new_text.splitlines()
        idx_model = new_lines.index("model: inherit")
        idx_effort = new_lines.index("effort: high")
        self.assertEqual(idx_effort, idx_model + 1)
        # And the very next line after the inserted effort: is the
        # closing fence -- confirming the insertion correctly pushed it
        # down rather than overwriting or skipping it.
        self.assertEqual(new_lines[idx_effort + 1], "---")


# ---- kind="command" pure-function edge cases (plan 94 Phase 1
# Deliverable 5). tests/lib/_configure/test_apply_agent_models.py's
# HappyPathTests / IdempotenceTests / etc. round-trip the SAME kind
# through the real emitter + configure_helper producers; these exercise
# shapes that chain cannot currently reach: an unmapped/never-configured
# tier resolved directly (no real command source is ever built with an
# unanswered tier by that round-trip's own test setup), a command
# missing the description: line D1's insertion rule anchors on, and a
# tier that configures an effort with no model (independent knobs -- see
# _rewrite_command_field's own docstring). ----

class CommandKindEdgeCaseTests(unittest.TestCase):
    def test_command_kind_null_tier_leaves_text_byte_identical(self):
        """A command whose tier was never configured resolves model=None,
        effort=None -- no model:/effort: line at all, and (since none
        existed to begin with) the text comes back byte-identical."""
        text = (
            "---\n"
            "name: implement\n"
            "description: \"Drain the feature's tasks.\"\n"
            "---\n"
            "\n"
            "Body.\n"
        )
        new_text, decision = _agent_models.plan_rewrite(
            text, {}, {}, kind="command", tier="do"
        )
        self.assertEqual(decision["status"], "applied")
        self.assertEqual(decision["tier"], "do")
        self.assertIsNone(decision["model"])
        self.assertIsNone(decision["effort"])
        self.assertFalse(decision["changed"])
        self.assertEqual(new_text, text)

    def test_command_kind_effort_configured_with_no_model_anchors_after_description(self):
        """The two fields are resolved independently (D5): an effort can
        be configured while the model stays unanswered. effort: must
        still land somewhere sensible -- immediately after description:,
        since there is no model: line to anchor after."""
        text = (
            "---\n"
            "name: fix\n"
            "description: \"Proposal-only remediation.\"\n"
            "argument-hint: \"[x]\"\n"
            "---\n"
            "\n"
            "Body.\n"
        )
        tier_models, tier_efforts = _agent_models.extract_tier_config(
            {"CLAUDE_EFFORT_DO": "high"}
        )
        new_text, decision = _agent_models.plan_rewrite(
            text, tier_models, tier_efforts, kind="command", tier="do"
        )
        self.assertEqual(decision["status"], "applied")
        self.assertIsNone(decision["model"])
        self.assertEqual(decision["effort"], "high")

        new_lines = new_text.splitlines()
        idx_description = next(
            i for i, l in enumerate(new_lines) if l.startswith("description:")
        )
        idx_effort = new_lines.index("effort: high")
        self.assertEqual(idx_effort, idx_description + 1)
        self.assertFalse(any(l.startswith("model:") for l in new_lines))

    def test_command_kind_missing_description_line_raises(self):
        """Every real emitted command carries description: -- a file
        without one is malformed by construction, so this is a
        hand-crafted shape (like the agent-side "no sibling model:"
        case above), not a shape the real producer chain can reach."""
        text = (
            "---\n"
            "name: mystery\n"
            "---\n"
            "\n"
            "Body.\n"
        )
        tier_models, tier_efforts = _agent_models.extract_tier_config(
            {"CLAUDE_TIER_THINK": "fable"}
        )
        with self.assertRaises(_agent_models.AgentValidationError) as ctx:
            _agent_models.plan_rewrite(
                text, tier_models, tier_efforts, kind="command", tier="think"
            )
        self.assertIn("description", str(ctx.exception))

    def test_command_kind_reconfiguring_removes_stray_model_line(self):
        """A previously-applied command's model: line, once its tier is
        un-configured (a null tier_models entry, matching what a hand-
        edited project-config.json produces), is REMOVED rather than
        left to linger -- the un-configuring behavior D1's report
        contract depends on."""
        already_applied = (
            "---\n"
            "name: plan\n"
            "description: \"Technical plan.\"\n"
            "model: fable\n"
            "effort: xhigh\n"
            "argument-hint: \"[spec-file]\"\n"
            "---\n"
            "\n"
            "Body.\n"
        )
        new_text, decision = _agent_models.plan_rewrite(
            already_applied, {}, {}, kind="command", tier="think"
        )
        self.assertEqual(decision["status"], "applied")
        self.assertIsNone(decision["model"])
        self.assertIsNone(decision["effort"])
        self.assertTrue(decision["changed"])
        self.assertNotIn("model:", new_text)
        self.assertNotIn("effort:", new_text)
        self.assertIn("argument-hint:", new_text)

    def test_command_kind_inserts_correctly_when_description_is_last_frontmatter_line(self):
        """The command-side mirror of
        test_effort_inserted_when_model_is_last_frontmatter_line above:
        the real emitter never places description: as the LAST
        frontmatter line before the closing '---' (every real command
        source also carries at least a trailing disable-model-invocation
        or argument-hint line, or nothing after description: at all in a
        way that matters), but this hand-crafted shape is the only way
        to exercise BOTH insertions (model: after description:, effort:
        after model:) when the anchor position coincides with the
        closing fence's own position (python-reviewer run B finding 4 --
        the command-side twin of the agent-side "model: is last" case)."""
        text = (
            "---\n"
            "name: minimal-command\n"
            "description: \"description: is the last frontmatter line.\"\n"
            "---\n"
            "\n"
            "Body.\n"
        )
        tier_models, tier_efforts = _agent_models.extract_tier_config(
            {"CLAUDE_TIER_THINK": "fable", "CLAUDE_EFFORT_THINK": "xhigh"}
        )
        new_text, decision = _agent_models.plan_rewrite(
            text, tier_models, tier_efforts, kind="command", tier="think"
        )
        self.assertEqual(decision["status"], "applied")
        self.assertEqual(decision["model"], "fable")
        self.assertEqual(decision["effort"], "xhigh")

        new_lines = new_text.splitlines()
        idx_description = next(
            i for i, l in enumerate(new_lines) if l.startswith("description:")
        )
        idx_model = new_lines.index("model: fable")
        idx_effort = new_lines.index("effort: xhigh")
        self.assertEqual(idx_model, idx_description + 1)
        self.assertEqual(idx_effort, idx_model + 1)
        # And the very next line after the inserted effort: is the
        # closing fence -- confirming both insertions correctly pushed
        # it down rather than overwriting or skipping it.
        self.assertEqual(new_lines[idx_effort + 1], "---")


if __name__ == "__main__":
    unittest.main()
