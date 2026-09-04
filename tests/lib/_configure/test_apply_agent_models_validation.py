"""Validation/exit-2 and un-configure tests for `configure_helper apply-models`, split out of `test_apply_agent_models.py` (core round-trip) to stay under this repo's 600-line test-file threshold; sibling `test_apply_agent_models_edge_cases.py` holds the permission/frontmatter/CRLF edge cases."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "configure_helper.py"
_INIT_HELPER_PY = _LIB_DIR / "init_helper.py"
_GENERATE_AGENTS_PY = _REPO_ROOT / "scripts" / "generate-agents.py"
_CLAUDE_EMITTER_PY = _REPO_ROOT / "scripts" / "emitters" / "claude.py"
_AGENTS_SRC = _REPO_ROOT / "src" / "agents"
_SRC_ROOT = _REPO_ROOT / "src"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import configure_helper  # noqa: E402, F401 -- imported for parity with the sibling file / any future direct use
from _configure import _agent_models  # noqa: E402

# ---- Subprocess helpers -- mirrors test_effort_fields.py / test_configure_helper.py. ----

def _run_configure(devforge_dir, install_root, *args):
    """Invoke configure_helper.py <args> as a subprocess."""
    return subprocess.run(
        [
            sys.executable, str(_HELPER_PY),
            "--devforge-dir", str(devforge_dir),
            "--install-root", str(install_root),
        ] + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _run_init(devforge_dir, *args):
    """Invoke init_helper.py <args> as a subprocess."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_INIT_HELPER_PY)] + list(args),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _run_generate_agents(target_dir):
    """Invoke the real emitter: python3 scripts/generate-agents.py --src
    src/agents --target <target_dir>. Writes <target_dir>/.claude/agents/*.md."""
    return subprocess.run(
        [
            sys.executable, str(_GENERATE_AGENTS_PY),
            "--src", str(_AGENTS_SRC),
            "--target", str(target_dir),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _run_claude_emitter(target_dir):
    """Invoke the real command emitter: python3 scripts/emitters/claude.py
    --src src --target <target_dir>. Writes <target_dir>/.claude/commands/
    devforge/*.md (--src is the repo's whole src/ root, not src/commands
    -- see tests/scripts/test_claude_emitter.py, which drives this same
    entry point the same way)."""
    return subprocess.run(
        [
            sys.executable, str(_CLAUDE_EMITTER_PY),
            "--src", str(_SRC_ROOT),
            "--target", str(target_dir),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class _EnvIsolationMixin:
    """Save/restore DEVFORGE_DIR around each test + provide a tmpdir.

    Layout:
      self.install_root/                        <- --target for both emitters; --install-root
        .claude/agents/*.md                      <- real emitted agent tree
        .claude/commands/devforge/*.md            <- real emitted command tree
        .devforge/                               <- devforge_dir
    """

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.install_root = Path(self._tmp.name)
        self.devforge_dir = self.install_root / ".devforge"
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        self.agents_dir = self.install_root / ".claude" / "agents"
        self.commands_dir = self.install_root / ".claude" / "commands" / "devforge"

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    def _write_full_init_yaml(self):
        """Minimal init.yaml sufficient for render-config to succeed."""
        _run_init(self.devforge_dir, "reset")
        _run_init(self.devforge_dir, "set-workspace-mode", "standalone")
        _run_init(self.devforge_dir, "set-project-root", ".")
        _run_init(self.devforge_dir, "set-project-state", "brownfield")
        _run_init(self.devforge_dir, "set-default-branch", "main")

    def _emit_real_agents(self):
        proc = _run_generate_agents(self.install_root)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertTrue(self.agents_dir.is_dir())

    def _emit_real_commands(self):
        proc = _run_claude_emitter(self.install_root)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertTrue(self.commands_dir.is_dir())

    def _configure(self, *args):
        return _run_configure(self.devforge_dir, self.install_root, *args)

    def _apply(self):
        return self._configure("apply-models")

    def _agent_text(self, name):
        return (self.agents_dir / "{0}.md".format(name)).read_text(encoding="utf-8")

    def _agent_lines(self, name):
        return self._agent_text(name).splitlines()

    def _all_agent_bytes(self):
        """Snapshot every agent file's raw bytes, keyed by filename."""
        return {
            p.name: p.read_bytes()
            for p in sorted(self.agents_dir.glob("*.md"))
        }

    def _command_text(self, name):
        return (self.commands_dir / "{0}.md".format(name)).read_text(encoding="utf-8")

    def _command_lines(self, name):
        return self._command_text(name).splitlines()

    def _all_command_bytes(self):
        """Snapshot every command file's raw bytes, keyed by filename."""
        return {
            p.name: p.read_bytes()
            for p in sorted(self.commands_dir.glob("*.md"))
        }


# ---- 1. Un-configuring: a tier set then unset reverts what apply wrote. ----
class ReconfigureToNullTests(_EnvIsolationMixin, unittest.TestCase):
    def test_unconfiguring_reverts_agent_to_inherit_and_removes_command_model_line(self):
        self._emit_real_agents()
        self._emit_real_commands()
        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-tier-think", "fable")
        self._configure("render-config")

        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn("model: fable", self._agent_lines("architect"))
        self.assertIn("model: fable", self._command_lines("plan"))

        # Simulate un-configuring by hand-editing the REAL rendered
        # project-config.json (round-tripped through render-config, then
        # mutated back to null) -- there is no "unset" setter verb, so
        # this is the same technique LegacyCapitalizedValueTests below
        # uses to simulate a pre-existing config shape.
        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        data["CLAUDE_TIER_THINK"] = None
        config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        proc2 = self._apply()
        self.assertEqual(proc2.returncode, 0, proc2.stderr.decode())
        report2 = json.loads(proc2.stdout.decode())

        self.assertIn("model: inherit", self._agent_lines("architect"))
        plan_lines_after = self._command_lines("plan")
        self.assertFalse(any(l.startswith("model:") for l in plan_lines_after))

        architect_entry = next(
            e for e in report2["applied"] if e["kind"] == "agent" and e["name"] == "architect"
        )
        self.assertEqual(architect_entry["model"], "inherit")
        self.assertTrue(architect_entry["changed"])

        plan_entry = next(
            e for e in report2["applied"] if e["kind"] == "command" and e["name"] == "plan"
        )
        self.assertIsNone(plan_entry["model"])
        self.assertTrue(plan_entry["changed"])


# ---- 2. Legacy capitalized tier value (pre-normalization install). ----
class LegacyCapitalizedValueTests(_EnvIsolationMixin, unittest.TestCase):
    def test_legacy_capitalized_tier_value_normalized_on_apply(self):
        self._emit_real_agents()
        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-tier-think", "opus")
        self._configure("render-config")

        # Simulate a pre-normalization install by hand-editing the REAL
        # rendered project-config.json (round-tripped through the real
        # render-config producer, then mutated to the shape a pre-D3
        # install would have written).
        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        data["CLAUDE_TIER_THINK"] = "Opus"
        config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn("model: opus", self._agent_lines("architect"))


# ---- 3. Pin passthrough. ----
class PinPassthroughTests(_EnvIsolationMixin, unittest.TestCase):
    def test_pin_value_written_verbatim(self):
        self._emit_real_agents()
        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-tier-do", "my-bedrock-route")
        self._configure("render-config")

        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn("model: my-bedrock-route", self._agent_lines("backend-engineer"))


# ---- 4. `default` effort removes an existing effort: line. ----
class EffortDefaultRemovesLineTests(_EnvIsolationMixin, unittest.TestCase):
    def test_reconfiguring_to_default_removes_effort_line(self):
        self._emit_real_agents()
        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-effort-think", "xhigh")
        self._configure("render-config")
        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn("effort: xhigh", self._agent_lines("architect"))
        before_other_lines = [
            l for l in self._agent_lines("architect") if not l.startswith("effort:")
        ]

        self._configure("set-claude-effort-think", "default")
        self._configure("render-config")
        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        after_lines = self._agent_lines("architect")
        self.assertFalse(any(l.startswith("effort:") for l in after_lines))
        self.assertEqual(after_lines, before_other_lines)


# ---- 5. Files/commands without a keying match -- skipped, untouched. ----
class SkippedFileTests(_EnvIsolationMixin, unittest.TestCase):
    def test_hand_written_agent_without_model_tier_skipped(self):
        self._emit_real_agents()
        hand_made = self.agents_dir / "my-custom-agent.md"
        hand_made_text = (
            "---\n"
            "name: my-custom-agent\n"
            "description: \"A consumer's own hand-written agent.\"\n"
            "---\n"
            "\n"
            "Body text.\n"
        )
        hand_made.write_text(hand_made_text, encoding="utf-8")

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-tier-think", "fable")
        self._configure("render-config")

        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())

        skipped_by_name = {
            s["name"]: s["reason"] for s in report["skipped"] if s["kind"] == "agent"
        }
        self.assertEqual(skipped_by_name.get("my-custom-agent"), "no-model-tier")
        self.assertEqual(hand_made.read_text(encoding="utf-8"), hand_made_text)

    def test_file_with_no_frontmatter_at_all_skipped(self):
        self._emit_real_agents()
        no_fm = self.agents_dir / "plain-notes.md"
        no_fm_text = "Just prose, no frontmatter at all.\n"
        no_fm.write_text(no_fm_text, encoding="utf-8")

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("render-config")

        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())

        skipped_by_name = {
            s["name"]: s["reason"] for s in report["skipped"] if s["kind"] == "agent"
        }
        self.assertEqual(skipped_by_name.get("plain-notes"), "no-frontmatter")
        self.assertEqual(no_fm.read_text(encoding="utf-8"), no_fm_text)


# ---- 6. Unknown model_tier value -- exit 2, names all four valid tiers,# writes nothing across BOTH classes. ----

class UnknownTierValidationTests(_EnvIsolationMixin, unittest.TestCase):
    def test_unknown_model_tier_exits_2_names_all_four_valid_tiers_and_writes_nothing(self):
        self._emit_real_agents()
        self._emit_real_commands()
        target = self.agents_dir / "architect.md"
        text = target.read_text(encoding="utf-8")
        self.assertIn("model_tier: think\n", text)
        text = text.replace("model_tier: think\n", "model_tier: nonsense\n")
        target.write_text(text, encoding="utf-8")

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("render-config")

        before_agents = self._all_agent_bytes()
        before_commands = self._all_command_bytes()
        proc = self._apply()
        self.assertEqual(proc.returncode, 2, proc.stdout.decode())
        self.assertIn(b"architect.md", proc.stderr)
        self.assertIn(b"nonsense", proc.stderr)

        stderr_text = proc.stderr.decode()
        for tier_name in _agent_models.VALID_TIERS:
            self.assertIn(tier_name, stderr_text)

        after_agents = self._all_agent_bytes()
        after_commands = self._all_command_bytes()
        # A validation failure in ONE agent file blocks writes to every
        # file in the batch -- agents AND commands alike (the two-pass
        # contract spans both classes together).
        self.assertEqual(before_agents, after_agents)
        self.assertEqual(before_commands, after_commands)


# ---- 7. Effort value outside the enum in project-config.json -- exit 2. ----
class EffortEnumValidationTests(_EnvIsolationMixin, unittest.TestCase):
    def test_effort_outside_enum_exits_2_and_writes_nothing(self):
        self._emit_real_agents()
        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("render-config")

        config_path = self.devforge_dir / "project-config.json"
        data = json.loads(config_path.read_text(encoding="utf-8"))
        data["CLAUDE_EFFORT_THINK"] = "turbo"
        config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

        before = self._all_agent_bytes()
        proc = self._apply()
        self.assertEqual(proc.returncode, 2, proc.stdout.decode())
        self.assertIn(b"turbo", proc.stderr)
        self.assertIn(b"CLAUDE_EFFORT_THINK", proc.stderr)
        after = self._all_agent_bytes()
        self.assertEqual(before, after)


# ---- 8. IO / config errors. ----
class ConfigAndIOErrorTests(_EnvIsolationMixin, unittest.TestCase):
    def test_missing_project_config_exits_1(self):
        self._emit_real_agents()
        # project-config.json deliberately never rendered.
        proc = self._apply()
        self.assertEqual(proc.returncode, 1, proc.stdout.decode())
        self.assertIn(b"project-config.json", proc.stderr)

    def test_malformed_project_config_exits_1(self):
        self._emit_real_agents()
        config_path = self.devforge_dir / "project-config.json"
        config_path.write_text("{ not valid json", encoding="utf-8")
        proc = self._apply()
        self.assertEqual(proc.returncode, 1, proc.stdout.decode())
        self.assertIn(b"malformed", proc.stderr)

    def test_missing_agents_and_commands_dirs_exits_0_with_empty_report(self):
        # Neither _emit_real_agents() nor _emit_real_commands() called --
        # .claude/agents/ and .claude/commands/devforge/ never created.
        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("render-config")
        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())
        self.assertEqual(report, {"applied": [], "skipped": []})

    def test_missing_commands_dir_only_still_reports_agents(self):
        """Agents present, commands absent -- each class is independent:
        a missing commands dir contributes zero command entries without
        affecting the agent report at all."""
        self._emit_real_agents()
        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-tier-think", "fable")
        self._configure("render-config")
        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())
        self.assertTrue(any(e["kind"] == "agent" for e in report["applied"]))
        self.assertFalse(any(e["kind"] == "command" for e in report["applied"]))
        self.assertFalse(any(e["kind"] == "command" for e in report["skipped"]))


# ---- 9. Colon-bearing description / tools lines survive byte-for-byte. ----
class ColonValueSurvivalTests(_EnvIsolationMixin, unittest.TestCase):
    def test_description_with_colons_and_tools_line_survive(self):
        self._emit_real_agents()
        # ac-verifier.md's real source description contains multiple
        # colons ("... under ac_verification_mode: observe the running
        # app (browser/API) under runtime-assisted, ...") and its tools:
        # line is a long comma-separated MCP tool list -- both real,
        # emitted bytes, not hand-authored.
        before_text = self._agent_text("ac-verifier")
        before_lines = before_text.splitlines()
        description_line = next(l for l in before_lines if l.startswith("description:"))
        tools_line = next(l for l in before_lines if l.startswith("tools:"))
        self.assertIn(":", description_line[len("description: "):])

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-tier-verify", "fable")
        self._configure("set-claude-effort-verify", "high")
        self._configure("render-config")
        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        after_lines = self._agent_lines("ac-verifier")
        self.assertIn(description_line, after_lines)
        self.assertIn(tools_line, after_lines)
        # And the file DID change (model/effort rewritten) -- proving
        # survival isn't just "nothing happened".
        self.assertNotEqual(before_text, self._agent_text("ac-verifier"))


if __name__ == "__main__":
    unittest.main()
