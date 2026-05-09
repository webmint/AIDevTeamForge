"""Smoke tests for src/hooks/* — F.11 CBM-first enforcement hooks.

Each hook is a stand-alone shell script that consumes a Claude Code hook
JSON object on stdin. Tests subprocess each script with sample stdin,
assert exit code, stderr substring, and (where relevant) stdout
substring or side-effect file contents.

PPID-keyed gates: the scripts derive their gate-file paths from $PPID,
which (for a child process spawned by this test) equals os.getpid().
setUp / tearDown remove the gate files matching the test runner's PID
so the once-per-session semantics are testable deterministically.

Cases:
  cbm-code-discovery-gate:
    1. First invocation in a session blocks (exit 2 + BLOCKED stderr)
    2. Second invocation in the same session passes through (exit 0)
  cbm-session-reminder:
    3. SessionStart stdin → stdout heredoc + exit 0
  cbm-mcp-marker:
    4. Bash invocation → appends timestamped tool line to .devforge/cbm-usage.log
    5. mcp__codebase-memory-mcp__search_graph → log line written
    6. Empty stdin → exit 0 quietly (no log line)
  bash-ban-raw-tools:
    7. `grep foo src/x.py` first call blocks (exit 2)
    8. `grep foo src/x.py` second call same session passes (exit 0)
    9. `cat package.json` passes (no source extension)
   10. `git status` passes (no grep/find/cat token)
   11. `find . -name '*.py'` blocks (find + .py)
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / "src" / "hooks"

GATE_DIRS = ("cbm-code-discovery-gate", "bash-ban-raw-tools")


def _gate_path(name: str) -> Path:
    return Path(f"/tmp/{name}-{os.getpid()}")


def _run(script_name: str, stdin_json: str | None, env: dict | None = None) -> subprocess.CompletedProcess:
    """Invoke a hook script with stdin JSON and return CompletedProcess.

    Subprocess inherits this test runner's PID as PPID, making the gate
    file path deterministic via os.getpid().
    """
    cmd = [str(HOOKS_DIR / script_name)]
    proc_env = os.environ.copy()
    if env:
        proc_env.update(env)
    return subprocess.run(
        cmd,
        input=stdin_json if stdin_json is not None else "",
        capture_output=True,
        text=True,
        env=proc_env,
    )


class HookTestBase(unittest.TestCase):
    def setUp(self) -> None:
        for name in GATE_DIRS:
            p = _gate_path(name)
            if p.exists():
                p.unlink()

    def tearDown(self) -> None:
        for name in GATE_DIRS:
            p = _gate_path(name)
            if p.exists():
                p.unlink()


class CbmCodeDiscoveryGateTests(HookTestBase):
    def test_first_invocation_blocks(self):
        stdin = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "/x"}})
        result = _run("cbm-code-discovery-gate", stdin)
        self.assertEqual(result.returncode, 2)
        self.assertIn("BLOCKED", result.stderr)
        self.assertIn("search_graph", result.stderr)
        self.assertTrue(_gate_path("cbm-code-discovery-gate").exists())

    def test_second_invocation_same_session_passes(self):
        stdin = json.dumps({"tool_name": "Read", "tool_input": {"file_path": "/x"}})
        first = _run("cbm-code-discovery-gate", stdin)
        self.assertEqual(first.returncode, 2)
        second = _run("cbm-code-discovery-gate", stdin)
        self.assertEqual(second.returncode, 0)
        self.assertEqual(second.stderr, "")


class CbmSessionReminderTests(HookTestBase):
    def test_emits_protocol_to_stdout(self):
        stdin = json.dumps({"hook_event_name": "SessionStart", "source": "startup"})
        result = _run("cbm-session-reminder", stdin)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Code Discovery Protocol", result.stdout)
        self.assertIn("search_graph", result.stdout)
        self.assertIn("trace_path", result.stdout)


class CbmMcpMarkerTests(HookTestBase):
    def test_bash_invocation_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            stdin = json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}})
            result = _run("cbm-mcp-marker", stdin, env={"CLAUDE_PROJECT_DIR": tmp})
            self.assertEqual(result.returncode, 0)
            log = Path(tmp) / ".devforge" / "cbm-usage.log"
            self.assertTrue(log.exists())
            content = log.read_text()
            self.assertIn("Bash", content)

    def test_cbm_mcp_invocation_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tool = "mcp__codebase-memory-mcp__search_graph"
            stdin = json.dumps({"tool_name": tool, "tool_input": {}})
            result = _run("cbm-mcp-marker", stdin, env={"CLAUDE_PROJECT_DIR": tmp})
            self.assertEqual(result.returncode, 0)
            log = Path(tmp) / ".devforge" / "cbm-usage.log"
            self.assertIn(tool, log.read_text())

    def test_empty_stdin_quiet_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = _run("cbm-mcp-marker", "", env={"CLAUDE_PROJECT_DIR": tmp})
            self.assertEqual(result.returncode, 0)
            log = Path(tmp) / ".devforge" / "cbm-usage.log"
            self.assertFalse(log.exists())


class BashBanRawToolsTests(HookTestBase):
    def _stdin(self, command: str) -> str:
        return json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})

    def test_grep_over_python_blocks_first_call(self):
        result = _run("bash-ban-raw-tools", self._stdin("grep foo src/devforge/lib/init.py"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("BLOCKED", result.stderr)
        self.assertIn("search_graph", result.stderr)

    def test_grep_over_python_passes_second_call(self):
        first = _run("bash-ban-raw-tools", self._stdin("grep foo src/devforge/lib/init.py"))
        self.assertEqual(first.returncode, 2)
        second = _run("bash-ban-raw-tools", self._stdin("grep foo src/devforge/lib/init.py"))
        self.assertEqual(second.returncode, 0)
        self.assertEqual(second.stderr, "")

    def test_cat_package_json_passes(self):
        result = _run("bash-ban-raw-tools", self._stdin("cat package.json"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, "")

    def test_git_status_passes(self):
        result = _run("bash-ban-raw-tools", self._stdin("git status"))
        self.assertEqual(result.returncode, 0)

    def test_find_for_python_files_blocks(self):
        result = _run("bash-ban-raw-tools", self._stdin("find . -name '*.py'"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("BLOCKED", result.stderr)


if __name__ == "__main__":
    unittest.main()
