"""Tests for `configure_helper apply-agent-models` -- the CLI/command layer
in `src/devforge/lib/_configure/_cmds_agent_models.py`
(92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md Phase 1, Deliverable 3).

Round-trips through the REAL producers, per this repo's testing rule for
anything that parses another tool's output:
  - `python3 scripts/generate-agents.py --src src/agents --target <tmp>`
    for the `.claude/agents/*.md` tree (the parser under test consumes
    THESE bytes, not a hand-authored fixture).
  - `configure_helper reset` + `set-claude-tier-*` + `set-claude-effort-*`
    + `render-config` (with the same `init.yaml` setup
    `tests/lib/_configure/test_effort_fields.py` uses) for
    `project-config.json`.
  - `configure_helper apply-agent-models` via subprocess, exercising the
    real CLI wiring in `_cli.py`.

Sibling file `tests/lib/_configure/test_agent_models.py` covers the pure
rewrite logic in `_agent_models.py` directly (no subprocess) -- split out
once this file grew past this repo's 600-line test-file threshold, to
mirror that module's own split from the CLI/command layer tested here.

Sections 14-17 (added after a python-reviewer pass on this file's first
cut, "run B") cover four further fixes to `_agent_models.py` /
`_cmds_agent_models.py` / `_render.py`: `_write_file_atomic` preserving
an existing file's permission bits, a duplicated `model:`/`effort:`/
`model_tier:` key inside one file's frontmatter being rejected rather
than guessed at, CRLF line endings surviving a real round-trip through
the CLI, and a pass-1 read error no longer swallowing an earlier file's
already-collected validation error.

Stdlib only.
"""

from __future__ import annotations

import json
import os
import stat
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
_AGENTS_SRC = _REPO_ROOT / "src" / "agents"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import configure_helper  # noqa: E402
from _configure import _agent_models  # noqa: E402

# chmod(..., 0o000) only enforces anything under POSIX, and only for a
# non-root user (root bypasses permission checks, so a test relying on
# it would pass for the wrong reason). Mirrors
# tests/lib/_shared/test_feature_alloc.py's own gate.
_SKIP_PERMISSION_TESTS = os.name != "posix" or (
    hasattr(os, "geteuid") and os.geteuid() == 0
)
_PERMISSION_SKIP_REASON = "permission enforcement requires a non-root POSIX user"


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


class _EnvIsolationMixin:
    """Save/restore DEVFORGE_DIR around each test + provide a tmpdir.

    Layout:
      self.install_root/            <- --target for the emitter; --install-root
        .claude/agents/*.md         <- real emitted agent tree
        .devforge/                  <- devforge_dir
    """

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.install_root = Path(self._tmp.name)
        self.devforge_dir = self.install_root / ".devforge"
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        self.agents_dir = self.install_root / ".claude" / "agents"

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

    def _configure(self, *args):
        return _run_configure(self.devforge_dir, self.install_root, *args)

    def _apply(self):
        return self._configure("apply-agent-models")

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


# ---- 1. Happy path. ----

class HappyPathTests(_EnvIsolationMixin, unittest.TestCase):
    def test_happy_path_tiers_and_efforts_applied(self):
        self._emit_real_agents()
        # Which real agents carry a model_tier: line at all (D1/D6's
        # keying mechanism) is computed HERE, from the real emitted
        # bytes, rather than assumed as a fixed 19-of-19 roster: a
        # model_pin agent (e.g. security-reviewer, D6) omits
        # model_tier: by the emitter's own contract, and the pin set
        # lives in src/agents/*.md sources this deliverable does not
        # own -- so the expected applied/skipped split is DERIVED, not
        # hand-asserted, and stays correct as that set changes.
        real_names = {p.stem for p in self.agents_dir.glob("*.md")}
        tiered_names = {
            name for name in real_names
            if "\nmodel_tier:" in self._agent_text(name)
        }
        pinned_names = real_names - tiered_names

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-tier-think", "fable")
        # "haiku", not "sonnet": CLAUDE_AGENT_DEFAULTS_BY_TIER["do"] is
        # already "sonnet" (the emitter's static default), so configuring
        # "sonnet" here would leave every do-tier agent's model: line
        # byte-identical to its freshly emitted form -- changed: false
        # for all 9 of them -- and the "every applied agent changed"
        # assertion below would pass vacuously (python-reviewer follow-up).
        self._configure("set-claude-tier-do", "haiku")
        self._configure("set-claude-tier-verify", "sonnet")
        self._configure("set-claude-effort-think", "xhigh")
        self._configure("set-claude-effort-do", "default")
        self._configure("set-claude-effort-verify", "medium")
        proc = self._configure("render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())

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

        # Every real agent is accounted for exactly once, split between
        # "applied" (has model_tier:) and "skipped" (a pinned agent, or
        # any other file without one) matching what was derived above.
        applied_names = {a["agent"] for a in report["applied"]}
        skipped_names = {s["agent"] for s in report["skipped"]}
        self.assertEqual(applied_names, tiered_names)
        self.assertEqual(skipped_names, pinned_names)
        for entry in report["skipped"]:
            self.assertEqual(entry["reason"], "no-model-tier")
        self.assertEqual(len(applied_names) + len(skipped_names), len(real_names))

        # Every applied agent genuinely changed -- think/verify get a
        # non-default model + a real effort, and do now gets "haiku"
        # against a "sonnet" static default, so no tier can land on its
        # own emitted default and report changed: false vacuously.
        for entry in report["applied"]:
            self.assertTrue(entry["changed"], entry)


# ---- 2. Idempotence. ----

class IdempotenceTests(_EnvIsolationMixin, unittest.TestCase):
    def test_second_run_is_byte_level_noop(self):
        self._emit_real_agents()
        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-tier-think", "fable")
        self._configure("set-claude-effort-think", "high")
        self._configure("set-claude-tier-verify", "opus")
        self._configure("render-config")

        proc1 = self._apply()
        self.assertEqual(proc1.returncode, 0, proc1.stderr.decode())
        snapshot_after_first = self._all_agent_bytes()

        proc2 = self._apply()
        self.assertEqual(proc2.returncode, 0, proc2.stderr.decode())
        report2 = json.loads(proc2.stdout.decode())
        snapshot_after_second = self._all_agent_bytes()

        self.assertEqual(snapshot_after_first, snapshot_after_second)
        for entry in report2["applied"]:
            self.assertFalse(entry["changed"], entry)


# ---- 3. Null tiers (never answered Q11) -- static default applies, no-op. ----

class NullTierDefaultTests(_EnvIsolationMixin, unittest.TestCase):
    def test_unset_tiers_apply_static_default_with_no_byte_change(self):
        self._emit_real_agents()
        before = self._all_agent_bytes()
        self._write_full_init_yaml()
        self._configure("reset")
        # No set-claude-tier-* / set-claude-effort-* calls at all.
        self._configure("render-config")

        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())

        after = self._all_agent_bytes()
        self.assertEqual(before, after)
        for entry in report["applied"]:
            self.assertFalse(entry["changed"], entry)
            expected = _agent_models.CLAUDE_AGENT_DEFAULTS_BY_TIER[entry["tier"]]
            self.assertEqual(entry["model"], expected)
            self.assertIsNone(entry["effort"])


# ---- 4. Legacy capitalized tier value (pre-normalization install). ----

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


# ---- 5. Pin passthrough. ----

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


# ---- 6. `default` effort removes an existing effort: line. ----

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


# ---- 7. Files without model_tier: / without any frontmatter -- skipped, untouched. ----

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

        skipped_by_name = {s["agent"]: s["reason"] for s in report["skipped"]}
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

        skipped_by_name = {s["agent"]: s["reason"] for s in report["skipped"]}
        self.assertEqual(skipped_by_name.get("plain-notes"), "no-frontmatter")
        self.assertEqual(no_fm.read_text(encoding="utf-8"), no_fm_text)

    def test_unclosed_frontmatter_skipped(self):
        """Opens a '---' fence and never closes it (python-reviewer run
        B finding 11) -- distinct from "no-frontmatter": the opening
        marker IS present, there's just no matching close before EOF."""
        self._emit_real_agents()
        unclosed = self.agents_dir / "unclosed-agent.md"
        unclosed_text = (
            "---\n"
            "name: unclosed-agent\n"
            "description: \"Opens frontmatter, never closes it.\"\n"
            "model_tier: do\n"
        )
        unclosed.write_text(unclosed_text, encoding="utf-8")

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("render-config")

        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())

        skipped_by_name = {s["agent"]: s["reason"] for s in report["skipped"]}
        self.assertEqual(skipped_by_name.get("unclosed-agent"), "unclosed-frontmatter")
        self.assertEqual(unclosed.read_text(encoding="utf-8"), unclosed_text)


# ---- 8. Body byte-identity. ----

class BodyByteIdentityTests(_EnvIsolationMixin, unittest.TestCase):
    def _body_bytes(self, raw):
        """Body = everything after the closing '---' line, located via
        the module's OWN frontmatter locator (`_agent_models.
        _locate_frontmatter`) rather than a naive `text.split("---\\n",
        2)` -- the naive split can't tell a literal "---\\n" occurring
        inside prose apart from the real closing fence, and it measures
        decoded text, not the bytes this test's name promises
        (python-reviewer run B finding 10)."""
        text = raw.decode("utf-8")
        lines = text.splitlines(keepends=True)
        status, _open_idx, close_idx = _agent_models._locate_frontmatter(lines)
        self.assertEqual(status, "ok")
        return "".join(lines[close_idx + 1:]).encode("utf-8")

    def test_body_byte_identical_for_every_applied_file(self):
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


# ---- 9. Unknown model_tier value -- exit 2, nothing written. ----

class UnknownTierValidationTests(_EnvIsolationMixin, unittest.TestCase):
    def test_unknown_model_tier_exits_2_and_writes_nothing(self):
        self._emit_real_agents()
        target = self.agents_dir / "architect.md"
        text = target.read_text(encoding="utf-8")
        self.assertIn("model_tier: think\n", text)
        text = text.replace("model_tier: think\n", "model_tier: nonsense\n")
        target.write_text(text, encoding="utf-8")

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("render-config")

        before = self._all_agent_bytes()
        proc = self._apply()
        self.assertEqual(proc.returncode, 2, proc.stdout.decode())
        self.assertIn(b"architect.md", proc.stderr)
        self.assertIn(b"nonsense", proc.stderr)
        after = self._all_agent_bytes()
        self.assertEqual(before, after)


# ---- 10. Effort value outside the enum in project-config.json -- exit 2. ----

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


# ---- 11. IO / config errors. ----

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

    def test_missing_agents_dir_exits_0_with_empty_report(self):
        # No _emit_real_agents() call -- .claude/agents/ never created.
        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("render-config")
        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())
        self.assertEqual(report, {"applied": [], "skipped": []})


# ---- 12. Colon-bearing description / tools lines survive byte-for-byte. ----

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


# ---- 13. Deliverable 5 (equality half) + pure-function edge cases --
# MOVED to tests/lib/_configure/test_agent_models.py (this file's split
# sibling, see module docstring). ----


# ---- 14. Existing file permissions survive a rewrite. ----

class PermissionPreservationTests(_EnvIsolationMixin, unittest.TestCase):
    @unittest.skipIf(os.name != "posix", "permission bits are not meaningful on this platform")
    def test_existing_file_permissions_survive_a_rewrite(self):
        """_write_file_atomic must not silently narrow an existing
        file's mode to mkstemp's 0o600 (python-reviewer run B finding
        1): mkstemp always creates 0o600 and os.replace does not copy
        permissions from the file it overwrites."""
        self._emit_real_agents()
        target = self.agents_dir / "architect.md"
        target.chmod(0o644)

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-tier-think", "fable")
        self._configure("render-config")

        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())
        architect_entry = next(a for a in report["applied"] if a["agent"] == "architect")
        # The write path must actually have RUN -- otherwise this test
        # would pass vacuously without exercising _write_file_atomic.
        self.assertTrue(architect_entry["changed"])

        mode = stat.S_IMODE(target.stat().st_mode)
        self.assertEqual(mode, 0o644)


# ---- 15. A duplicated key inside one file's frontmatter is malformed. ----

class DuplicateKeyValidationTests(_EnvIsolationMixin, unittest.TestCase):
    def test_duplicate_effort_line_exits_2_and_writes_nothing(self):
        """A frontmatter with the same key twice is rejected outright
        (python-reviewer run B finding 2), not "pick the first and
        leave the second as a stray line". architect.md's emitted
        output carries no effort: line to begin with -- two are
        inserted by hand here to simulate the malformed shape (real
        producer output, hand-edited for an edge case no real path
        produces)."""
        self._emit_real_agents()
        target = self.agents_dir / "architect.md"
        text = target.read_text(encoding="utf-8")
        self.assertNotIn("effort:", text)
        text = text.replace(
            "model_tier: think\n",
            "effort: high\neffort: medium\nmodel_tier: think\n",
        )
        target.write_text(text, encoding="utf-8")

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("render-config")

        before = self._all_agent_bytes()
        proc = self._apply()
        self.assertEqual(proc.returncode, 2, proc.stdout.decode())
        self.assertIn(b"architect.md", proc.stderr)
        self.assertIn(b"duplicate effort", proc.stderr)
        after = self._all_agent_bytes()
        self.assertEqual(before, after)


# ---- 16. CRLF line endings survive a real round-trip through the CLI. ----

class CRLFRoundTripTests(_EnvIsolationMixin, unittest.TestCase):
    def test_crlf_agent_file_applied_and_stays_crlf(self):
        """A CRLF-normalized consumer tree (e.g. one whose git
        re-normalized line endings) must resolve and rewrite exactly
        like an LF tree, not silently no-op as "no-frontmatter"
        (python-reviewer run B finding 3). A file that MIXES '\\r\\n'
        and bare '\\n' endings is explicitly OUT OF SCOPE -- see
        `_agent_models._detect_line_ending`'s own docstring; this test
        only covers a UNIFORMLY CRLF file."""
        self._emit_real_agents()
        target = self.agents_dir / "architect.md"
        original_bytes = target.read_bytes()
        crlf_bytes = original_bytes.replace(b"\n", b"\r\n")
        # Sanity: the conversion actually produced CRLF, not a no-op.
        self.assertNotEqual(crlf_bytes, original_bytes)
        target.write_bytes(crlf_bytes)

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-tier-think", "fable")
        self._configure("set-claude-effort-think", "xhigh")
        self._configure("render-config")

        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())
        architect_entry = next(a for a in report["applied"] if a["agent"] == "architect")
        self.assertEqual(architect_entry["model"], "fable")
        self.assertEqual(architect_entry["effort"], "xhigh")
        self.assertTrue(architect_entry["changed"])

        after_bytes = target.read_bytes()
        after_text = after_bytes.decode("utf-8")
        self.assertIn("model: fable\r\n", after_text)
        self.assertIn("effort: xhigh\r\n", after_text)
        # Every '\n' in the file is part of a '\r\n' pair -- proves no
        # rewritten OR inserted line slipped in a bare LF.
        self.assertEqual(after_bytes.count(b"\n"), after_bytes.count(b"\r\n"))

        # Second run: byte-level no-op, still CRLF throughout.
        proc2 = self._apply()
        self.assertEqual(proc2.returncode, 0, proc2.stderr.decode())
        report2 = json.loads(proc2.stdout.decode())
        architect_entry2 = next(a for a in report2["applied"] if a["agent"] == "architect")
        self.assertFalse(architect_entry2["changed"])
        after_bytes2 = target.read_bytes()
        self.assertEqual(after_bytes, after_bytes2)


# ---- 17. A pass-1 read error must not swallow an earlier validation error. ----

class Pass1CombinedErrorsTests(_EnvIsolationMixin, unittest.TestCase):
    @unittest.skipIf(_SKIP_PERMISSION_TESTS, _PERMISSION_SKIP_REASON)
    def test_validation_error_and_unreadable_file_both_reported(self):
        """A pass-1 OSError reading a LATER file (backend-engineer.md,
        chmod 0o000) must not discard a validation error already
        collected from an EARLIER file (architect.md, an unknown
        model_tier) (python-reviewer run B finding 8): both are named
        on stderr, and nothing is written."""
        self._emit_real_agents()
        bad_tier = self.agents_dir / "architect.md"
        text = bad_tier.read_text(encoding="utf-8")
        text = text.replace("model_tier: think\n", "model_tier: nonsense\n")
        bad_tier.write_text(text, encoding="utf-8")

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("render-config")

        # Snapshot BEFORE chmod'ing the unreadable file -- _all_agent_
        # bytes() reads every file, which would itself raise on a
        # 0o000 target.
        before = self._all_agent_bytes()

        unreadable = self.agents_dir / "backend-engineer.md"
        unreadable.chmod(0o000)
        try:
            proc = self._apply()
            self.assertEqual(proc.returncode, 2, proc.stdout.decode())
            self.assertIn(b"architect.md", proc.stderr)
            self.assertIn(b"backend-engineer.md", proc.stderr)
        finally:
            unreadable.chmod(0o644)

        after = self._all_agent_bytes()
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
