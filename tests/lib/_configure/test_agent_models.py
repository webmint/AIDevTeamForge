"""Tests for `src/devforge/lib/_configure/_agent_models.py` -- the pure
frontmatter-rewrite logic behind `configure_helper apply-agent-models`
(92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md Phase 1, Deliverable 3) plus the
default-map-equality half of Deliverable 5.

Split out of `tests/lib/_configure/test_apply_agent_models.py` (which grew
past this repo's 600-line test-file threshold) to mirror that module's own
split: `test_apply_agent_models.py` covers the CLI/command layer
(`_cmds_agent_models.py`, exercised via subprocess through the real
`configure_helper` + `scripts/generate-agents.py` producers);
THIS file covers `_agent_models.py` directly -- no subprocess, no
filesystem round-trip, just the pure function.

`PureFunctionEdgeCaseTests` exercises `_agent_models.plan_rewrite` on
hand-crafted frontmatter for shapes the real emitter/producer chain
cannot currently produce: a `model_tier: scan` agent (the tier has zero
real members -- plan 92 OQ-3), a `model_tier:` line with no sibling
`model:` line (malformed by construction, since the emitter never writes
one without the other), and a file where `model:` is the LAST
frontmatter line (the real emitter always follows it with `model_tier:`
and/or `applies_to:`). These are internal-function unit tests, not
round-tripped producer output, and are labelled as such throughout.

Stdlib only.
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_INSTALL_DEFAULTS_PY = _REPO_ROOT / "scripts" / "lib" / "install_defaults.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _configure import _agent_models  # noqa: E402


# ---- Deliverable 5 (equality half) -- the default-map pin. ----

class DefaultMapEqualityTests(unittest.TestCase):
    def _load_install_defaults(self):
        spec = importlib.util.spec_from_file_location(
            "_plan92_install_defaults_under_test", _INSTALL_DEFAULTS_PY
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_maps_are_equal(self):
        install_defaults = self._load_install_defaults()
        self.assertEqual(
            install_defaults.CLAUDE_AGENT_DEFAULTS_BY_TIER,
            _agent_models.CLAUDE_AGENT_DEFAULTS_BY_TIER,
        )

    def test_pin_is_live_a_single_edited_value_breaks_equality(self):
        """Proves the equality test above actually pins something, not
        just two dicts that happen to match: a mutated COPY of one map
        (a single value flipped) must compare UNEQUAL to the other,
        real, unedited map. If this failed, the equality test could
        pass vacuously (e.g. via a bug that compares a dict to itself)."""
        install_defaults = self._load_install_defaults()
        mutated = dict(install_defaults.CLAUDE_AGENT_DEFAULTS_BY_TIER)
        mutated["think"] = "haiku"  # was "opus"
        self.assertNotEqual(mutated, install_defaults.CLAUDE_AGENT_DEFAULTS_BY_TIER)
        self.assertNotEqual(mutated, _agent_models.CLAUDE_AGENT_DEFAULTS_BY_TIER)


# ---- Pure-function edge cases plan_rewrite touches that the real producer
# chain cannot currently exercise (see module docstring). ----

class PureFunctionEdgeCaseTests(unittest.TestCase):
    def test_scan_tier_falls_back_to_static_default_with_no_effort_line(self):
        """model_tier: scan has zero real members (plan 92 OQ-3) and no
        CLAUDE_TIER_SCAN / CLAUDE_EFFORT_SCAN project-config key exists,
        so tier_models/tier_efforts (as extract_tier_config builds them)
        never carry a "scan" entry -- exercised here directly since no
        real src/agents/*.md source declares this tier."""
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
        new_text, decision = _agent_models.plan_rewrite(text, tier_models, tier_efforts)
        self.assertEqual(decision["status"], "applied")
        self.assertEqual(decision["tier"], "scan")
        self.assertEqual(decision["model"], "haiku")
        self.assertIsNone(decision["effort"])
        self.assertFalse(decision["changed"])
        self.assertEqual(new_text, text)

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
        position (python-reviewer run B finding 12)."""
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
        self.assertEqual(decision["effort"], "high")

        new_lines = new_text.splitlines()
        idx_model = new_lines.index("model: sonnet")
        idx_effort = new_lines.index("effort: high")
        self.assertEqual(idx_effort, idx_model + 1)
        # And the very next line after the inserted effort: is the
        # closing fence -- confirming the insertion correctly pushed it
        # down rather than overwriting or skipping it.
        self.assertEqual(new_lines[idx_effort + 1], "---")


if __name__ == "__main__":
    unittest.main()
