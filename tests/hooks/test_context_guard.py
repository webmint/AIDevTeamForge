"""Tests for .claude/hooks/forge/context-guard.py (stdlib unittest; Python 3.9+).

Run: python3 -m unittest discover -s tests/hooks -v
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOOK = os.path.join(REPO, ".claude", "hooks", "forge", "context-guard.py")

spec = importlib.util.spec_from_file_location("context_guard", HOOK)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def assistant(tokens, sidechain=False):
    return {"type": "assistant", "isSidechain": sidechain,
            "message": {"usage": {"input_tokens": tokens, "cache_creation_input_tokens": 0,
                                  "cache_read_input_tokens": 0, "output_tokens": 0}}}


class Env:
    """Temporarily set or clear environment variables."""

    def __init__(self, **values):
        self.values = values
        self.saved = {}

    def __enter__(self):
        for key, value in self.values.items():
            self.saved[key] = os.environ.get(key)
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(value)

    def __exit__(self, *exc):
        for key, value in self.saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


CLEAN = dict(FORGE_CONTEXT_WINDOW=None, FORGE_CONTEXT_WARN=None, FORGE_CONTEXT_STOP=None)


class ContextGuardTest(unittest.TestCase):
    def transcript(self, entries):
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        with os.fdopen(fd, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
        self.addCleanup(os.remove, path)
        return path

    def run_hook(self, path, **env):
        full = dict(os.environ)
        for key in CLEAN:
            full.pop(key, None)
        full.update({k: str(v) for k, v in env.items()})
        proc = subprocess.run([sys.executable, HOOK], input=json.dumps({"transcript_path": path}),
                              capture_output=True, text=True, env=full)
        return proc.returncode, proc.stdout

    def test_counts_latest_main_session_turn_and_skips_sidechains(self):
        path = self.transcript([assistant(1000), assistant(5000), assistant(99999, sidechain=True),
                                {"type": "user", "message": {"content": "x"}}])
        self.assertEqual(guard.context_tokens(path), 5000)

    def test_default_window_thresholds(self):
        with Env(**CLEAN):
            self.assertEqual(guard.thresholds(10_000), (150_000, 170_000))

    def test_larger_context_than_window_assumes_large_window(self):
        with Env(**CLEAN):
            self.assertEqual(guard.thresholds(300_000), (750_000, 850_000))

    def test_absolute_overrides(self):
        with Env(FORGE_CONTEXT_WINDOW=None, FORGE_CONTEXT_WARN=100, FORGE_CONTEXT_STOP=200):
            self.assertEqual(guard.thresholds(50), (100, 200))

    def test_silent_below_warn(self):
        code, out = self.run_hook(self.transcript([assistant(10_000)]))
        self.assertEqual((code, out), (0, ""))

    def test_wind_down_message(self):
        code, out = self.run_hook(self.transcript([assistant(160_000)]))
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertNotIn("systemMessage", data)
        self.assertIn("Wind down", data["hookSpecificOutput"]["additionalContext"])

    def test_stop_message(self):
        code, out = self.run_hook(self.transcript([assistant(180_000)]))
        data = json.loads(out)
        self.assertIn("STOP at the nearest safe point", data["hookSpecificOutput"]["additionalContext"])
        self.assertIn("systemMessage", data)

    def test_window_env(self):
        code, out = self.run_hook(self.transcript([assistant(160_000)]), FORGE_CONTEXT_WINDOW=1_000_000)
        self.assertEqual(out, "")

    def test_never_fails_on_garbage(self):
        proc = subprocess.run([sys.executable, HOOK], input="not json", capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, "")

    def test_missing_transcript_is_silent(self):
        code, out = self.run_hook("/nonexistent/transcript.jsonl")
        self.assertEqual((code, out), (0, ""))


if __name__ == "__main__":
    unittest.main()
