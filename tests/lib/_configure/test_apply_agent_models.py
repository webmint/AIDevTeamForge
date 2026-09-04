"""Core round-trip tests for `configure_helper apply-models` -- happy path, idempotence, null tiers and body-identity; sibling files `test_apply_agent_models_validation.py` (un-configure + the exit-2/IO-error classes) and `test_apply_agent_models_edge_cases.py` (permission/frontmatter/CRLF edge cases) split out the rest."""

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

# NOTE: the POSIX-permission-skip constants (_SKIP_PERMISSION_TESTS /
# _PERMISSION_SKIP_REASON) and the `stat` import live in
# tests/lib/_configure/test_apply_agent_models_edge_cases.py now -- this
# file's own PermissionPreservationTests and Pass1CombinedErrorsTests
# (the only two consumers) moved there in the same split.


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


# ---- 1. Happy path -- both classes, all four tiers, an unmapped command. ----
class HappyPathTests(_EnvIsolationMixin, unittest.TestCase):
    def test_happy_path_tiers_and_efforts_applied_to_both_classes(self):
        self._emit_real_agents()
        self._emit_real_commands()

        # Which real agents carry a model_tier: line at all (D1/D6's
        # keying mechanism) is computed HERE, from the real emitted
        # bytes, rather than assumed as a fixed roster -- the expected
        # applied/skipped split for agents is DERIVED, not hand-asserted,
        # and stays correct as the roster changes.
        real_agent_names = {p.stem for p in self.agents_dir.glob("*.md")}
        tiered_agent_names = {
            name for name in real_agent_names
            if "\nmodel_tier:" in self._agent_text(name)
        }
        untiered_agent_names = real_agent_names - tiered_agent_names

        # Same derivation on the command side, against the helper-owned
        # COMMAND_TIERS map (imported, not hand-copied).
        real_command_names = {p.stem for p in self.commands_dir.glob("*.md")}
        mapped_command_names = real_command_names & set(_agent_models.COMMAND_TIERS)
        unmapped_command_names = real_command_names - mapped_command_names
        # Sanity: the live roster genuinely exercises both branches --
        # if either set were empty this test would pass vacuously.
        self.assertTrue(mapped_command_names)
        self.assertTrue(unmapped_command_names)
        self.assertIn("research", unmapped_command_names)
        self.assertIn("configure", unmapped_command_names)

        unmapped_before = {
            name: (self.commands_dir / "{0}.md".format(name)).read_bytes()
            for name in unmapped_command_names
        }

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-tier-think", "fable")
        # "haiku", not "sonnet": a do-tier agent's real source declares
        # no model: line to begin with (the emitter always writes
        # "inherit"), so any real configured value produces changed:
        # true -- "haiku" is simply a distinct, unambiguous value.
        self._configure("set-claude-tier-do", "haiku")
        self._configure("set-claude-tier-verify", "sonnet")
        self._configure("set-claude-tier-security", "opus")
        self._configure("set-claude-effort-think", "xhigh")
        self._configure("set-claude-effort-do", "default")
        self._configure("set-claude-effort-verify", "medium")
        self._configure("set-claude-effort-security", "high")
        proc = self._configure("render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())

        # --- Agents ---
        # architect.md (think): model, then effort, then model_tier -- in
        # that exact line order (Phase 1 Step 0 answer 2's insertion point).
        lines = self._agent_lines("architect")
        self.assertIn("model: fable", lines)
        self.assertIn("effort: xhigh", lines)
        self.assertIn("model_tier: think", lines)
        idx_model = lines.index("model: fable")
        idx_effort = lines.index("effort: xhigh")
        idx_tier = lines.index("model_tier: think")
        self.assertEqual(idx_effort, idx_model + 1)
        self.assertEqual(idx_tier, idx_effort + 1)

        # A do-tier engineer: model set, NO effort: line (do = "default").
        do_lines = self._agent_lines("backend-engineer")
        self.assertIn("model: haiku", do_lines)
        self.assertFalse(any(l.startswith("effort:") for l in do_lines))

        # code-reviewer.md (verify): effort: medium present.
        self.assertIn("effort: medium", self._agent_lines("code-reviewer"))

        # security-reviewer.md (security, the real roster's sole
        # member): model: opus, effort: high.
        security_lines = self._agent_lines("security-reviewer")
        self.assertIn("model: opus", security_lines)
        self.assertIn("effort: high", security_lines)
        self.assertIn("model_tier: security", security_lines)

        # --- Commands ---
        # plan.md (think): model, then effort, landing immediately after
        # description: -- the insertion anchor D1 specifies.
        plan_lines = self._command_lines("plan")
        idx_description = next(
            i for i, l in enumerate(plan_lines) if l.startswith("description:")
        )
        idx_model_cmd = plan_lines.index("model: fable")
        idx_effort_cmd = plan_lines.index("effort: xhigh")
        self.assertEqual(idx_model_cmd, idx_description + 1)
        self.assertEqual(idx_effort_cmd, idx_model_cmd + 1)

        # implement.md (do): model set, NO effort: line.
        implement_lines = self._command_lines("implement")
        self.assertIn("model: haiku", implement_lines)
        self.assertFalse(any(l.startswith("effort:") for l in implement_lines))

        # Unmapped commands (research.md, configure.md incl.) are
        # byte-identical -- never even reported as "applied".
        for name in unmapped_command_names:
            after = (self.commands_dir / "{0}.md".format(name)).read_bytes()
            self.assertEqual(after, unmapped_before[name], name)

        # --- Report shape ---
        applied_agent_names = {a["name"] for a in report["applied"] if a["kind"] == "agent"}
        skipped_agent_names = {s["name"] for s in report["skipped"] if s["kind"] == "agent"}
        self.assertEqual(applied_agent_names, tiered_agent_names)
        self.assertEqual(skipped_agent_names, untiered_agent_names)

        applied_command_names = {a["name"] for a in report["applied"] if a["kind"] == "command"}
        skipped_command_names = {s["name"] for s in report["skipped"] if s["kind"] == "command"}
        self.assertEqual(applied_command_names, mapped_command_names)
        self.assertEqual(skipped_command_names, unmapped_command_names)

        for entry in report["skipped"]:
            expected_reason = (
                "no-model-tier" if entry["kind"] == "agent" else "not-in-command-tiers"
            )
            self.assertEqual(entry["reason"], expected_reason, entry)

        # Every applied entry (agent AND command) genuinely changed --
        # no tier landed on a value the source already carried.
        for entry in report["applied"]:
            self.assertTrue(entry["changed"], entry)

        # Sorted by (kind, name): every "agent" entry before every
        # "command" entry, alphabetical within each class.
        applied_pairs = [(e["kind"], e["name"]) for e in report["applied"]]
        self.assertEqual(applied_pairs, sorted(applied_pairs))
        skipped_pairs = [(e["kind"], e["name"]) for e in report["skipped"]]
        self.assertEqual(skipped_pairs, sorted(skipped_pairs))


# ---- 2. Idempotence, over BOTH directories. ----
class IdempotenceTests(_EnvIsolationMixin, unittest.TestCase):
    def test_second_run_is_byte_level_noop_over_both_directories(self):
        self._emit_real_agents()
        self._emit_real_commands()
        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-tier-think", "fable")
        self._configure("set-claude-effort-think", "high")
        self._configure("set-claude-tier-verify", "opus")
        self._configure("set-claude-tier-security", "sonnet")
        self._configure("render-config")

        proc1 = self._apply()
        self.assertEqual(proc1.returncode, 0, proc1.stderr.decode())
        agents_after_first = self._all_agent_bytes()
        commands_after_first = self._all_command_bytes()

        proc2 = self._apply()
        self.assertEqual(proc2.returncode, 0, proc2.stderr.decode())
        report2 = json.loads(proc2.stdout.decode())
        agents_after_second = self._all_agent_bytes()
        commands_after_second = self._all_command_bytes()

        self.assertEqual(agents_after_first, agents_after_second)
        self.assertEqual(commands_after_first, commands_after_second)
        for entry in report2["applied"]:
            self.assertFalse(entry["changed"], entry)


# ---- 3. Null tiers (never answered Q11) -- inherit for agents, no line for commands. ----
class NullTierDefaultTests(_EnvIsolationMixin, unittest.TestCase):
    def test_unset_tiers_leave_agents_on_inherit_and_commands_with_no_model_line(self):
        self._emit_real_agents()
        self._emit_real_commands()
        agents_before = self._all_agent_bytes()
        commands_before = self._all_command_bytes()
        self._write_full_init_yaml()
        self._configure("reset")
        # No set-claude-tier-* / set-claude-effort-* calls at all.
        self._configure("render-config")

        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())

        # Byte-identical to the fresh emitter output for BOTH classes --
        # the emitter already writes "model: inherit" into every agent
        # (plan 94 D2), and no command ever carries a model: line until
        # configured, so an unconfigured apply changes nothing.
        agents_after = self._all_agent_bytes()
        commands_after = self._all_command_bytes()
        self.assertEqual(agents_before, agents_after)
        self.assertEqual(commands_before, commands_after)

        for entry in report["applied"]:
            self.assertFalse(entry["changed"], entry)
            if entry["kind"] == "agent":
                self.assertEqual(entry["model"], "inherit")
            else:
                self.assertIsNone(entry["model"])
            self.assertIsNone(entry["effort"])


# ---- 4. Body byte-identity, for BOTH classes. ----
class BodyByteIdentityTests(_EnvIsolationMixin, unittest.TestCase):
    def _body_bytes(self, raw):
        """Body = everything after the closing '---' line, located via
        the module's OWN frontmatter locator (`_agent_models.
        _locate_frontmatter`) rather than a naive `text.split("---\\n",
        2)` -- the naive split can't tell a literal "---\\n" occurring
        inside prose apart from the real closing fence, and it measures
        decoded text, not the bytes this test's name promises
        (python-reviewer run B finding 10). Shared between agents and
        commands -- both classes fence their frontmatter identically."""
        text = raw.decode("utf-8")
        lines = text.splitlines(keepends=True)
        status, _open_idx, close_idx = _agent_models._locate_frontmatter(lines)
        self.assertEqual(status, "ok")
        return "".join(lines[close_idx + 1:]).encode("utf-8")

    def test_body_byte_identical_for_every_applied_agent(self):
        self._emit_real_agents()
        bodies_before = {
            p.name: self._body_bytes(p.read_bytes())
            for p in sorted(self.agents_dir.glob("*.md"))
        }

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-tier-think", "fable")
        self._configure("set-claude-effort-verify", "high")
        self._configure("render-config")
        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        for p in sorted(self.agents_dir.glob("*.md")):
            body_after = self._body_bytes(p.read_bytes())
            self.assertEqual(body_after, bodies_before[p.name], p.name)

    def test_body_byte_identical_for_every_applied_command(self):
        self._emit_real_commands()
        bodies_before = {
            p.name: self._body_bytes(p.read_bytes())
            for p in sorted(self.commands_dir.glob("*.md"))
        }

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-tier-think", "fable")
        self._configure("set-claude-tier-do", "haiku")
        self._configure("set-claude-effort-do", "high")
        self._configure("render-config")
        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        for p in sorted(self.commands_dir.glob("*.md")):
            body_after = self._body_bytes(p.read_bytes())
            self.assertEqual(body_after, bodies_before[p.name], p.name)


if __name__ == "__main__":
    unittest.main()
