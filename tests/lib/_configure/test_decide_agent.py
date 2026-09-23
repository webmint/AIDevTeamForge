"""Tests for the `decide-agent` verb (101-NON-WEB-STACK-READINESS-PLAN.md
Phase 2b, D9).

`decide-agent` is the ONE keep/drop decision `update.sh`'s NEW_AGENTS
computation calls per candidate `src/agents/*.md` file so the nature filter
has one Python-tested owner instead of a shell re-implementation. It calls
the SAME two functions `prune-agents` calls -- `_parse_agent_frontmatter`
(`_configure/_md_parsers.py`) and `_decide_agent` (`_configure/_render.py`)
-- against `configure.yaml`'s `project_natures`, loaded via `_load()` the
same way `cmd_prune_agents` does.

Drives the real CLI (subprocess) and builds `configure.yaml` through the
real `set-project-natures` setter -- following `tests/lib/_configure/
test_require_ticket.py`'s pattern, not hand-authored yaml fixtures.

Covers:
  - KEEP for applies_to: ["all"].
  - KEEP for an applies_to that overlaps project_natures.
  - KEEP for a missing applies_to field (prune-agents' conservative rule 1).
  - KEEP for an unparseable applies_to (same conservative rule).
  - DROP for no overlap.
  - KEEP when there is no configure.yaml at all (differs from prune-agents,
    which exits 2 -- documented in the verb's own docstring).
  - KEEP when project_natures is unset/empty (same no-natures rule).
  - Non-zero exit for a missing --file.
  - The installed `---`-delimited frontmatter form parses identically to
    the fenced ```yaml source form (same parser, both forms).
  - The verb run on the REAL `src/agents/game-engineer.md` (applies_to:
    ["game"]) against natures ["web"] -> drop, ["game"] -> keep.
  - The verb run on the REAL `src/agents/devils-advocate.md` (applies_to:
    ["all"]) against natures ["web"] -> keep.

Stdlib only.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "configure_helper.py"
_GAME_ENGINEER_MD = _REPO_ROOT / "src" / "agents" / "game-engineer.md"
_DEVILS_ADVOCATE_MD = _REPO_ROOT / "src" / "agents" / "devils-advocate.md"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import configure_helper  # noqa: E402


def _run_configure(devforge_dir, *args):
    """Invoke configure_helper.py <args> as a subprocess."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY), "--devforge-dir", str(devforge_dir)] + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class _EnvIsolationMixin:
    """Save/restore DEVFORGE_DIR around each test + provide a tmpdir.

    Mirrors tests/lib/_configure/test_require_ticket.py's mixin.
    """

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.install_root = Path(self._tmp.name)
        self.devforge_dir = self.install_root / ".devforge"
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.devforge_dir / configure_helper.OUTPUT_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    def _write_agent_source_form(self, name, applies_to_str):
        """Write a SOURCE-form agent file (fenced ```yaml) -- the only form
        update.sh's one call site hands the verb (D9)."""
        content = (
            "```yaml\n"
            "name: {0}\n"
            "description: \"Agent {0}\"\n"
            "model_tier: do\n"
            "applies_to: {1}\n"
            "```\n\n"
            "Agent body.\n"
        ).format(name, applies_to_str)
        path = self.install_root / "{0}.md".format(name)
        path.write_text(content, encoding="utf-8")
        return path

    def _write_agent_installed_form(self, name, applies_to_str):
        """Write an INSTALLED-form agent file (triple-dash) -- the form the
        parser also tolerates, exercised by test_installed_dash_form_parses."""
        content = (
            "---\n"
            "name: {0}\n"
            "applies_to: {1}\n"
            "---\n"
            "\nAgent body.\n"
        ).format(name, applies_to_str)
        path = self.install_root / "{0}.md".format(name)
        path.write_text(content, encoding="utf-8")
        return path

    def _decide(self, file_path):
        return _run_configure(self.devforge_dir, "decide-agent", "--file", str(file_path))


class DecideAgentTests(_EnvIsolationMixin, unittest.TestCase):
    def test_applies_to_all_kept(self):
        self._run_configure_natures("web")
        path = self._write_agent_source_form("universal-agent", '["all"]')
        proc = self._decide(path)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(proc.stdout.decode().strip(), "keep")

    def test_overlapping_applies_to_kept(self):
        self._run_configure_natures("web")
        path = self._write_agent_source_form("web-or-backend", '["web", "backend"]')
        proc = self._decide(path)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(proc.stdout.decode().strip(), "keep")

    def test_missing_applies_to_kept(self):
        """No applies_to field at all -- prune-agents' conservative rule 1."""
        self._run_configure_natures("web")
        content = (
            "```yaml\n"
            "name: no-applies-to\n"
            "description: \"Agent\"\n"
            "```\n\n"
            "Body.\n"
        )
        path = self.install_root / "no-applies-to.md"
        path.write_text(content, encoding="utf-8")
        proc = self._decide(path)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(proc.stdout.decode().strip(), "keep")

    def test_unparseable_applies_to_kept(self):
        """applies_to present but not the bracketed-list form -- unparseable,
        same conservative KEEP as missing frontmatter."""
        self._run_configure_natures("web")
        path = self._write_agent_source_form("weird-agent", "some-bareword")
        proc = self._decide(path)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(proc.stdout.decode().strip(), "keep")

    def test_no_overlap_dropped(self):
        self._run_configure_natures("web")
        path = self._write_agent_source_form("mobile-only", '["mobile"]')
        proc = self._decide(path)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(proc.stdout.decode().strip(), "drop")

    def test_no_configure_yaml_kept(self):
        """No configure.yaml at all -- differs from prune-agents (exit 2);
        decide-agent decides 'keep' (D9)."""
        self.assertFalse(self.output_file.exists())
        path = self._write_agent_source_form("mobile-only", '["mobile"]')
        proc = self._decide(path)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(proc.stdout.decode().strip(), "keep")

    def test_project_natures_unset_kept(self):
        """configure.yaml exists (via reset) but project_natures was never
        set -- same no-natures KEEP rule as the absent-file case."""
        _run_configure(self.devforge_dir, "reset")
        path = self._write_agent_source_form("mobile-only", '["mobile"]')
        proc = self._decide(path)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(proc.stdout.decode().strip(), "keep")

    def test_missing_file_nonzero_exit(self):
        missing = self.install_root / "does-not-exist.md"
        proc = self._decide(missing)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.decode(), "")

    def test_installed_dash_form_parses(self):
        """The installed --- form parses identically to the source
        ```yaml form -- same parser, both forms tolerated."""
        self._run_configure_natures("web")
        path = self._write_agent_installed_form("mobile-only-dash", '["mobile"]')
        proc = self._decide(path)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(proc.stdout.decode().strip(), "drop")

    def test_malformed_configure_yaml_exits_1(self):
        """configure.yaml that _load()'s parser rejects (YamlParseError) --
        the except (OSError, YamlParseError) branch around _load() in
        cmd_decide_agent. Hand-written malformed content is fine here: this
        is an error-path fixture, not a producer round-trip (the CLI never
        writes yaml this shape; it exists to prove the error branch)."""
        self.output_file.write_text(
            "project_natures: not-a-list-scalar\n", encoding="utf-8"
        )
        path = self._write_agent_source_form("some-agent", '["web"]')
        proc = self._decide(path)
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout.decode(), "")
        self.assertIn(b"cannot load configure.yaml", proc.stderr)

    def _run_configure_natures(self, natures_csv):
        _run_configure(self.devforge_dir, "set-project-natures", natures_csv)


class RealAgentSourceTests(_EnvIsolationMixin, unittest.TestCase):
    """Runs decide-agent on the REAL src/agents/*.md sources."""

    def test_game_engineer_dropped_for_web(self):
        self._run_configure_natures("web")
        proc = self._decide(_GAME_ENGINEER_MD)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(proc.stdout.decode().strip(), "drop")

    def test_game_engineer_kept_for_game(self):
        self._run_configure_natures("game")
        proc = self._decide(_GAME_ENGINEER_MD)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(proc.stdout.decode().strip(), "keep")

    def test_devils_advocate_kept_for_web(self):
        """applies_to: ["all"] always lands, regardless of natures (D9's
        first-write-rule guarantee)."""
        self._run_configure_natures("web")
        proc = self._decide(_DEVILS_ADVOCATE_MD)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertEqual(proc.stdout.decode().strip(), "keep")

    def _run_configure_natures(self, natures_csv):
        _run_configure(self.devforge_dir, "set-project-natures", natures_csv)


if __name__ == "__main__":
    unittest.main()
