"""Tests for src/devforge/lib/wizard_render.py.

Covers the `reset`, `set-project-name`, and `set-project-description`
subcommands plus `_state_file_path` resolution.

Each test runs in its own `tempfile.TemporaryDirectory` and points the
helper at it via the `DEVFORGE_DIR` environment variable, so the repo's
real `.devforge/` is never touched. The env override is restored in
tearDown so tests can't bleed into each other.

Pure-function tests (`_state_file_path`) import the module directly.
End-to-end CLI tests invoke the .py file as a subprocess, exercising
the real argparse + dispatch path.

Stdlib only.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Resolve the helper script + add lib dir to sys.path so we can `import
# wizard_render` for pure-function tests. The path computation is
# repo-relative, not env-dependent.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "wizard_render.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import wizard_render  # noqa: E402


def _run_reset(devforge_dir):
    """Invoke `wizard_render.py reset` as a subprocess with DEVFORGE_DIR set."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_HELPER_PY), "reset"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _run_helper(devforge_dir, *args):
    """Invoke wizard_render.py with arbitrary args and DEVFORGE_DIR set."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(args),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class StateFilePathTests(unittest.TestCase):
    """`_state_file_path` resolution rules."""

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)

    def tearDown(self):
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    def test_env_override_honored(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["DEVFORGE_DIR"] = tmp
            path = wizard_render._state_file_path()
            self.assertEqual(
                path, Path(tmp) / wizard_render.STATE_FILE_NAME
            )

    def test_no_env_falls_back_to_helper_location(self):
        path = wizard_render._state_file_path()
        expected_dir = Path(wizard_render.__file__).resolve().parent.parent
        self.assertEqual(path, expected_dir / wizard_render.STATE_FILE_NAME)

    def test_resolution_is_per_call_not_cached(self):
        with tempfile.TemporaryDirectory() as tmp_a:
            os.environ["DEVFORGE_DIR"] = tmp_a
            first = wizard_render._state_file_path()
        with tempfile.TemporaryDirectory() as tmp_b:
            os.environ["DEVFORGE_DIR"] = tmp_b
            second = wizard_render._state_file_path()
        self.assertNotEqual(first, second)


class ResetSubcommandTests(unittest.TestCase):
    """End-to-end behavior of `wizard_render reset`."""

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.devforge_dir = Path(self._tmp.name)
        self.state_file = self.devforge_dir / wizard_render.STATE_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    def test_missing_state_file_exits_zero_silently(self):
        self.assertFalse(self.state_file.exists())
        proc = _run_reset(self.devforge_dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, b"")
        self.assertEqual(proc.stderr, b"")
        self.assertFalse(self.state_file.exists())

    def test_existing_valid_json_state_is_deleted(self):
        self.state_file.write_text('{"languages": ["python"]}\n')
        self.assertTrue(self.state_file.exists())
        proc = _run_reset(self.devforge_dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_empty_state_file_is_deleted(self):
        self.state_file.write_text("")
        self.assertTrue(self.state_file.exists())
        proc = _run_reset(self.devforge_dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_invalid_json_state_file_is_deleted(self):
        self.state_file.write_text("not json at all }{")
        self.assertTrue(self.state_file.exists())
        proc = _run_reset(self.devforge_dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_state_path_is_directory_returns_error(self):
        self.state_file.mkdir()
        self.assertTrue(self.state_file.is_dir())
        proc = _run_reset(self.devforge_dir)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn(str(self.state_file).encode(), proc.stderr)
        self.assertTrue(self.state_file.is_dir())

    def test_devforge_dir_env_isolates_from_real_state(self):
        self.state_file.write_text('{"x": 1}')
        proc = _run_reset(self.devforge_dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(self.state_file.exists())
        self.assertTrue(
            str(self.state_file).startswith(str(self.devforge_dir))
        )


class _StringSetterTestBase(unittest.TestCase):
    """Shared setUp / tearDown for setter test classes.

    Each test gets a fresh temp `.devforge/` directory and a clean
    `DEVFORGE_DIR` env var. The real env value (if any) is saved and
    restored so tests don't bleed into each other.
    """

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.devforge_dir = Path(self._tmp.name)
        self.state_file = self.devforge_dir / wizard_render.STATE_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env

    def _read_state(self):
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def _write_state(self, payload):
        self.state_file.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


class SetProjectNameSubcommandTests(_StringSetterTestBase):
    """End-to-end behavior of `wizard_render set-project-name`."""

    def test_writes_key_to_new_state_file(self):
        self.assertFalse(self.state_file.exists())
        proc = _run_helper(self.devforge_dir, "set-project-name", "foo")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.state_file.exists())
        self.assertEqual(self._read_state(), {"PROJECT_NAME": "foo"})

    def test_merges_into_existing_state(self):
        self._write_state({"PROJECT_TYPE": "library"})
        proc = _run_helper(self.devforge_dir, "set-project-name", "foo")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(),
            {"PROJECT_NAME": "foo", "PROJECT_TYPE": "library"},
        )

    def test_overwrites_prior_value(self):
        self._write_state({"PROJECT_NAME": "old"})
        proc = _run_helper(self.devforge_dir, "set-project-name", "new")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state(), {"PROJECT_NAME": "new"})

    def test_empty_value_rejected(self):
        proc = _run_helper(self.devforge_dir, "set-project-name", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"PROJECT_NAME", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_whitespace_only_value_rejected(self):
        proc = _run_helper(self.devforge_dir, "set-project-name", "   ")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"PROJECT_NAME", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_control_char_value_rejected(self):
        # 0x01 (Start of Heading) — POSIX execve rejects argv containing
        # NUL (0x00), so we use a non-NUL control char to verify our
        # helper-level rejection. Validation rejects all 0x00–0x1F except
        # tab (and LF/CR for fields that opt in); 0x01 is the canonical
        # sample for that range.
        proc = _run_helper(
            self.devforge_dir, "set-project-name", "bad\x01name"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"PROJECT_NAME", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_del_control_char_rejected(self):
        # 0x7F (DEL) — verifies the high-end control char branch.
        proc = _run_helper(
            self.devforge_dir, "set-project-name", "bad\x7fname"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"PROJECT_NAME", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_newline_in_name_rejected(self):
        # PROJECT_NAME substitutes into single-line template contexts
        # (e.g. `{{PROJECT_NAME}}` in a markdown heading); embedded LF
        # would silently split the heading and corrupt downstream output.
        # Mirror the shape of test_control_char_value_rejected.
        proc = _run_helper(
            self.devforge_dir, "set-project-name", "hello\nworld"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"PROJECT_NAME", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_validate_string_rejects_nul_byte(self):
        # Pure-function check: the helper rejects NUL even though we can't
        # exercise it via subprocess (OS rejects argv with embedded NUL).
        with self.assertRaises(ValueError) as ctx:
            wizard_render._validate_string("bad\x00name", "PROJECT_NAME")
        self.assertIn("PROJECT_NAME", str(ctx.exception))

    def test_pretty_printed_with_sorted_keys(self):
        # Insert keys in non-sorted order; verify file has sorted output.
        self._write_state({"ZZZ_LAST": "z", "AAA_FIRST": "a"})
        proc = _run_helper(self.devforge_dir, "set-project-name", "middle")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        content = self.state_file.read_text(encoding="utf-8")
        # Pretty-printed: each key on its own line with two-space indent.
        self.assertIn('  "AAA_FIRST": "a"', content)
        self.assertIn('  "PROJECT_NAME": "middle"', content)
        self.assertIn('  "ZZZ_LAST": "z"', content)
        # Sorted: AAA appears before PROJECT_NAME, which appears before ZZZ.
        self.assertLess(
            content.index("AAA_FIRST"), content.index("PROJECT_NAME")
        )
        self.assertLess(
            content.index("PROJECT_NAME"), content.index("ZZZ_LAST")
        )

    def test_no_temp_files_leaked_after_success(self):
        # mkstemp leaves no leftover files on the happy path.
        proc = _run_helper(self.devforge_dir, "set-project-name", "foo")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        leftovers = [
            p.name
            for p in self.devforge_dir.iterdir()
            if p.name.startswith("wizard-render-state-")
        ]
        self.assertEqual(leftovers, [])

    def test_corrupt_state_file_surfaces_error(self):
        # A pre-existing malformed state file must not be silently overwritten.
        # This is an I/O-failure path (exit 1), not a validation rejection
        # (exit 2) — assertNotEqual is intentional here so the test stays
        # robust to either code, while validation tests above pin exit 2.
        self.state_file.write_text("not json {")
        proc = _run_helper(self.devforge_dir, "set-project-name", "foo")
        self.assertNotEqual(proc.returncode, 0)
        # Original corrupt content remains — no clobber.
        self.assertEqual(self.state_file.read_text(), "not json {")


class SetProjectDescriptionSubcommandTests(_StringSetterTestBase):
    """End-to-end behavior of `wizard_render set-project-description`."""

    HAPPY_VALUE = (
        "A description with multiple sentences. "
        "Including punctuation. And so on."
    )

    def test_writes_key_to_new_state_file(self):
        self.assertFalse(self.state_file.exists())
        proc = _run_helper(
            self.devforge_dir, "set-project-description", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(), {"PROJECT_DESCRIPTION": self.HAPPY_VALUE}
        )

    def test_merges_into_existing_state(self):
        self._write_state({"PROJECT_TYPE": "library"})
        proc = _run_helper(
            self.devforge_dir, "set-project-description", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(),
            {
                "PROJECT_DESCRIPTION": self.HAPPY_VALUE,
                "PROJECT_TYPE": "library",
            },
        )

    def test_overwrites_prior_value(self):
        self._write_state({"PROJECT_DESCRIPTION": "old desc."})
        proc = _run_helper(
            self.devforge_dir, "set-project-description", "New desc."
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(), {"PROJECT_DESCRIPTION": "New desc."}
        )

    def test_empty_value_rejected(self):
        proc = _run_helper(self.devforge_dir, "set-project-description", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"PROJECT_DESCRIPTION", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_whitespace_only_value_rejected(self):
        proc = _run_helper(
            self.devforge_dir, "set-project-description", "   \t  "
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"PROJECT_DESCRIPTION", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_control_char_value_rejected(self):
        # 0x01 — see SetProjectNameSubcommandTests.test_control_char_value_rejected
        # for why this isn't NUL.
        proc = _run_helper(
            self.devforge_dir,
            "set-project-description",
            "bad\x01desc",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"PROJECT_DESCRIPTION", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_validate_string_rejects_nul_byte(self):
        with self.assertRaises(ValueError) as ctx:
            wizard_render._validate_string(
                "bad\x00desc", "PROJECT_DESCRIPTION"
            )
        self.assertIn("PROJECT_DESCRIPTION", str(ctx.exception))

    def test_newline_in_value_permitted(self):
        # PROJECT_DESCRIPTION opts into the newline-allowed policy
        # (multi-sentence README quotes legitimately span lines). Compare
        # to SetProjectNameSubcommandTests.test_newline_in_name_rejected,
        # which verifies the opposite policy for the single-line field.
        value = "First sentence.\nSecond sentence."
        proc = _run_helper(
            self.devforge_dir, "set-project-description", value
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(), {"PROJECT_DESCRIPTION": value}
        )

    def test_pretty_printed_with_sorted_keys(self):
        proc = _run_helper(
            self.devforge_dir, "set-project-description", "Some desc."
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        content = self.state_file.read_text(encoding="utf-8")
        self.assertIn('  "PROJECT_DESCRIPTION": "Some desc."', content)
        # Trailing newline at end of file (we write `\n` after json.dump).
        self.assertTrue(content.endswith("\n"))


class SetterCompositionTests(_StringSetterTestBase):
    """Verify the two setters compose correctly into a shared state file."""

    def test_both_setters_coexist_in_state(self):
        proc = _run_helper(
            self.devforge_dir, "set-project-name", "my-project"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = _run_helper(
            self.devforge_dir,
            "set-project-description",
            "My project description.",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(),
            {
                "PROJECT_NAME": "my-project",
                "PROJECT_DESCRIPTION": "My project description.",
            },
        )

    def test_reset_then_set_starts_fresh(self):
        # Pre-existing state, then reset, then set — only the new key remains.
        self._write_state({"PROJECT_NAME": "old", "PROJECT_TYPE": "library"})
        proc = _run_reset(self.devforge_dir)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(self.state_file.exists())
        proc = _run_helper(self.devforge_dir, "set-project-name", "fresh")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state(), {"PROJECT_NAME": "fresh"})


if __name__ == "__main__":
    unittest.main()
