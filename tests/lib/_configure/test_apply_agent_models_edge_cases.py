"""Permission/frontmatter/CRLF edge-case tests for `configure_helper apply-models`; siblings `test_apply_agent_models.py` (core round-trip) and `test_apply_agent_models_validation.py` (validation/exit-2 + un-configure) hold the rest."""

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
_CLAUDE_EMITTER_PY = _REPO_ROOT / "scripts" / "emitters" / "claude.py"
_AGENTS_SRC = _REPO_ROOT / "src" / "agents"
_SRC_ROOT = _REPO_ROOT / "src"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import configure_helper  # noqa: E402, F401 -- imported for parity with the sibling file / any future direct use

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


# ---- 1. An unclosed frontmatter fence -- skipped, untouched. ----

class UnclosedFrontmatterTests(_EnvIsolationMixin, unittest.TestCase):
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

        skipped_by_name = {
            s["name"]: s["reason"] for s in report["skipped"] if s["kind"] == "agent"
        }
        self.assertEqual(skipped_by_name.get("unclosed-agent"), "unclosed-frontmatter")
        self.assertEqual(unclosed.read_text(encoding="utf-8"), unclosed_text)


# ---- 2. Existing file permissions survive a rewrite, for BOTH classes. ----

class PermissionPreservationTests(_EnvIsolationMixin, unittest.TestCase):
    @unittest.skipIf(os.name != "posix", "permission bits are not meaningful on this platform")
    def test_existing_agent_file_permissions_survive_a_rewrite(self):
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
        architect_entry = next(
            e for e in report["applied"] if e["kind"] == "agent" and e["name"] == "architect"
        )
        # The write path must actually have RUN -- otherwise this test
        # would pass vacuously without exercising _write_file_atomic.
        self.assertTrue(architect_entry["changed"])

        mode = stat.S_IMODE(target.stat().st_mode)
        self.assertEqual(mode, 0o644)

    @unittest.skipIf(os.name != "posix", "permission bits are not meaningful on this platform")
    def test_existing_command_file_permissions_survive_a_rewrite(self):
        """The same _write_file_atomic call backs the command write
        path -- this proves the preservation holds there too, not just
        for the agent branch above."""
        self._emit_real_commands()
        target = self.commands_dir / "plan.md"
        target.chmod(0o644)

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("set-claude-tier-think", "fable")
        self._configure("render-config")

        proc = self._apply()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())
        plan_entry = next(
            e for e in report["applied"] if e["kind"] == "command" and e["name"] == "plan"
        )
        self.assertTrue(plan_entry["changed"])

        mode = stat.S_IMODE(target.stat().st_mode)
        self.assertEqual(mode, 0o644)


# ---- 3. A duplicated key inside one file's frontmatter is malformed,
# for BOTH classes. ----

class DuplicateKeyValidationTests(_EnvIsolationMixin, unittest.TestCase):
    def test_duplicate_effort_line_in_an_agent_exits_2_and_writes_nothing(self):
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

    def test_duplicate_model_line_in_a_command_exits_2_and_writes_nothing(self):
        """The same rejection applies to a command file -- plan.md's
        real emitted output carries no model: line to begin with (only
        its BODY prose ever mentions the word "model"), so two lines
        are inserted BY LINE NUMBER, inside the frontmatter fence only,
        to simulate a malformed shape (e.g. a hand-edit, or a prior
        apply run left in a bad state)."""
        self._emit_real_commands()
        target = self.commands_dir / "plan.md"
        lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
        self.assertEqual(lines[0].rstrip("\n"), "---")
        description_idx = next(
            i for i, l in enumerate(lines) if l.startswith("description:")
        )
        lines[description_idx + 1:description_idx + 1] = [
            "model: opus\n", "model: sonnet\n"
        ]
        target.write_text("".join(lines), encoding="utf-8")

        self._write_full_init_yaml()
        self._configure("reset")
        self._configure("render-config")

        before = self._all_command_bytes()
        proc = self._apply()
        self.assertEqual(proc.returncode, 2, proc.stdout.decode())
        self.assertIn(b"plan.md", proc.stderr)
        self.assertIn(b"duplicate model", proc.stderr)
        after = self._all_command_bytes()
        self.assertEqual(before, after)


# ---- 4. CRLF line endings survive a real round-trip through the CLI,
# for BOTH classes. ----

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
        architect_entry = next(
            e for e in report["applied"] if e["kind"] == "agent" and e["name"] == "architect"
        )
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
        architect_entry2 = next(
            e for e in report2["applied"] if e["kind"] == "agent" and e["name"] == "architect"
        )
        self.assertFalse(architect_entry2["changed"])
        after_bytes2 = target.read_bytes()
        self.assertEqual(after_bytes, after_bytes2)

    def test_crlf_command_file_applied_and_stays_crlf(self):
        """The command-side twin of the test above (python-reviewer run
        B finding 2): a CRLF-normalized command file must resolve and
        get its INSERTED model:/effort: lines through
        _rewrite_command_field with the same CRLF ending, not silently
        no-op and not slip in a bare LF on the two lines that path
        inserts rather than rewrites in place."""
        self._emit_real_commands()
        target = self.commands_dir / "plan.md"
        original_bytes = target.read_bytes()
        crlf_bytes = original_bytes.replace(b"\n", b"\r\n")
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
        plan_entry = next(
            e for e in report["applied"] if e["kind"] == "command" and e["name"] == "plan"
        )
        self.assertEqual(plan_entry["model"], "fable")
        self.assertEqual(plan_entry["effort"], "xhigh")
        self.assertTrue(plan_entry["changed"])

        after_bytes = target.read_bytes()
        after_text = after_bytes.decode("utf-8")
        self.assertIn("model: fable\r\n", after_text)
        self.assertIn("effort: xhigh\r\n", after_text)
        # Every '\n' in the file is part of a '\r\n' pair -- proves the
        # two INSERTED lines (never present before this apply) came out
        # CRLF too, not just the lines an agent-style in-place rewrite
        # would have touched.
        self.assertEqual(after_bytes.count(b"\n"), after_bytes.count(b"\r\n"))

        # Second run: byte-level no-op, still CRLF throughout.
        proc2 = self._apply()
        self.assertEqual(proc2.returncode, 0, proc2.stderr.decode())
        report2 = json.loads(proc2.stdout.decode())
        plan_entry2 = next(
            e for e in report2["applied"] if e["kind"] == "command" and e["name"] == "plan"
        )
        self.assertFalse(plan_entry2["changed"])
        after_bytes2 = target.read_bytes()
        self.assertEqual(after_bytes, after_bytes2)


# ---- 5. A pass-1 read error must not swallow an earlier validation error. ----

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


# ---- 6. The apply-agent-models alias produces byte-identical output. ----

class VerbAliasTests(unittest.TestCase):
    """Standalone (not _EnvIsolationMixin-based): builds TWO independent
    installs from scratch with identical setup, applies through each
    verb NAME once, and compares -- proving the alias reaches the
    IDENTICAL handler rather than merely proving idempotence (which a
    single install re-run under a different name could not rule out,
    since a second run is always a no-op by construction)."""

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)

    def tearDown(self):
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    def _build_install(self, tmp_dir):
        install_root = Path(tmp_dir)
        devforge_dir = install_root / ".devforge"
        devforge_dir.mkdir(parents=True, exist_ok=True)

        proc = _run_generate_agents(install_root)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        proc = _run_claude_emitter(install_root)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

        _run_init(devforge_dir, "reset")
        _run_init(devforge_dir, "set-workspace-mode", "standalone")
        _run_init(devforge_dir, "set-project-root", ".")
        _run_init(devforge_dir, "set-project-state", "brownfield")
        _run_init(devforge_dir, "set-default-branch", "main")

        _run_configure(devforge_dir, install_root, "reset")
        _run_configure(devforge_dir, install_root, "set-claude-tier-think", "fable")
        _run_configure(devforge_dir, install_root, "set-claude-effort-think", "xhigh")
        proc = _run_configure(devforge_dir, install_root, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        return install_root, devforge_dir

    def test_apply_agent_models_alias_matches_apply_models(self):
        with tempfile.TemporaryDirectory() as tmp_a, tempfile.TemporaryDirectory() as tmp_b:
            install_a, devforge_a = self._build_install(tmp_a)
            install_b, devforge_b = self._build_install(tmp_b)

            proc_a = _run_configure(devforge_a, install_a, "apply-models")
            self.assertEqual(proc_a.returncode, 0, proc_a.stderr.decode())
            proc_b = _run_configure(devforge_b, install_b, "apply-agent-models")
            self.assertEqual(proc_b.returncode, 0, proc_b.stderr.decode())

            self.assertEqual(proc_a.stdout, proc_b.stdout)
            self.assertEqual(proc_a.returncode, proc_b.returncode)

            agents_a = {
                p.name: p.read_bytes()
                for p in sorted((install_a / ".claude" / "agents").glob("*.md"))
            }
            agents_b = {
                p.name: p.read_bytes()
                for p in sorted((install_b / ".claude" / "agents").glob("*.md"))
            }
            self.assertEqual(agents_a, agents_b)

            commands_a = {
                p.name: p.read_bytes()
                for p in sorted(
                    (install_a / ".claude" / "commands" / "devforge").glob("*.md")
                )
            }
            commands_b = {
                p.name: p.read_bytes()
                for p in sorted(
                    (install_b / ".claude" / "commands" / "devforge").glob("*.md")
                )
            }
            self.assertEqual(commands_a, commands_b)


if __name__ == "__main__":
    unittest.main()
