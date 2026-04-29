"""Tests for src/devforge/lib/wizard_render.py.

Covers the `reset`, `set-project-name`, `set-project-description`,
`set-project-type`, `set-architecture`, `set-error-handling`,
`set-runtime-url`, `set-api-layer`, and `set-testing` subcommands plus
`_state_file_path` resolution.

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


class SetProjectTypeSubcommandTests(_StringSetterTestBase):
    """End-to-end behavior of `wizard_render set-project-type`.

    PROJECT_TYPE is a single-line category label — same validation policy
    as PROJECT_NAME (no LF/CR, no other control chars). The happy-path
    value is one of the 13 Q3 taxonomy categories; free-text custom
    values are also valid (the helper enforces shape, not the enum).
    """

    HAPPY_VALUE = "Frontend / web application"

    def test_writes_key_to_new_state_file(self):
        self.assertFalse(self.state_file.exists())
        proc = _run_helper(
            self.devforge_dir, "set-project-type", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.state_file.exists())
        self.assertEqual(
            self._read_state(), {"PROJECT_TYPE": self.HAPPY_VALUE}
        )

    def test_merges_into_existing_state(self):
        self._write_state({"PROJECT_NAME": "foo"})
        proc = _run_helper(
            self.devforge_dir, "set-project-type", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(),
            {"PROJECT_NAME": "foo", "PROJECT_TYPE": self.HAPPY_VALUE},
        )

    def test_overwrites_prior_value(self):
        self._write_state({"PROJECT_TYPE": "old"})
        proc = _run_helper(self.devforge_dir, "set-project-type", "new")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state(), {"PROJECT_TYPE": "new"})

    def test_empty_value_rejected(self):
        proc = _run_helper(self.devforge_dir, "set-project-type", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"PROJECT_TYPE", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_whitespace_only_value_rejected(self):
        proc = _run_helper(self.devforge_dir, "set-project-type", "   ")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"PROJECT_TYPE", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_control_char_value_rejected(self):
        # 0x01 — see SetProjectNameSubcommandTests.test_control_char_value_rejected
        # for why this isn't NUL.
        proc = _run_helper(
            self.devforge_dir, "set-project-type", "bad\x01type"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"PROJECT_TYPE", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_del_control_char_rejected(self):
        # 0x7F (DEL) — verifies the high-end control char branch.
        proc = _run_helper(
            self.devforge_dir, "set-project-type", "bad\x7ftype"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"PROJECT_TYPE", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_newline_in_value_rejected(self):
        # PROJECT_TYPE is a single-line category label; embedded LF would
        # silently corrupt template substitution (e.g. `{{PROJECT_TYPE}}`
        # in a single-line list-item context).
        proc = _run_helper(
            self.devforge_dir, "set-project-type", "Frontend\nweb"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"PROJECT_TYPE", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_pretty_printed_with_sorted_keys(self):
        # Insert keys in non-sorted order; verify file has sorted output.
        self._write_state({"ZZZ_LAST": "z", "AAA_FIRST": "a"})
        proc = _run_helper(
            self.devforge_dir, "set-project-type", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        content = self.state_file.read_text(encoding="utf-8")
        self.assertIn('  "AAA_FIRST": "a"', content)
        self.assertIn(
            '  "PROJECT_TYPE": "Frontend / web application"', content
        )
        self.assertIn('  "ZZZ_LAST": "z"', content)
        # Sorted: AAA appears before PROJECT_TYPE, which appears before ZZZ.
        self.assertLess(
            content.index("AAA_FIRST"), content.index("PROJECT_TYPE")
        )
        self.assertLess(
            content.index("PROJECT_TYPE"), content.index("ZZZ_LAST")
        )

    def test_no_temp_files_leaked_after_success(self):
        # mkstemp leaves no leftover files on the happy path.
        proc = _run_helper(
            self.devforge_dir, "set-project-type", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        leftovers = [
            p.name
            for p in self.devforge_dir.iterdir()
            if p.name.startswith("wizard-render-state-")
        ]
        self.assertEqual(leftovers, [])


class SetArchitectureSubcommandTests(_StringSetterTestBase):
    """End-to-end behavior of `wizard_render set-architecture`.

    ARCHITECTURE is a single-line architectural-pattern label — a detected
    value confirmed by the user or a free-text override. Same validation
    policy as PROJECT_NAME (no LF/CR, no other control chars). The helper
    enforces shape, not an enum (Q4 permits free-text).
    """

    HAPPY_VALUE = "Clean Architecture"

    def test_writes_key_to_new_state_file(self):
        self.assertFalse(self.state_file.exists())
        proc = _run_helper(
            self.devforge_dir, "set-architecture", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.state_file.exists())
        self.assertEqual(
            self._read_state(), {"ARCHITECTURE": self.HAPPY_VALUE}
        )

    def test_merges_into_existing_state(self):
        self._write_state({"PROJECT_NAME": "foo"})
        proc = _run_helper(
            self.devforge_dir, "set-architecture", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(),
            {"ARCHITECTURE": self.HAPPY_VALUE, "PROJECT_NAME": "foo"},
        )

    def test_overwrites_prior_value(self):
        self._write_state({"ARCHITECTURE": "Old Pattern"})
        proc = _run_helper(self.devforge_dir, "set-architecture", "Hexagonal")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state(), {"ARCHITECTURE": "Hexagonal"})

    def test_empty_value_rejected(self):
        proc = _run_helper(self.devforge_dir, "set-architecture", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"ARCHITECTURE", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_whitespace_only_value_rejected(self):
        proc = _run_helper(self.devforge_dir, "set-architecture", "   ")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"ARCHITECTURE", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_control_char_value_rejected(self):
        # 0x01 — see SetProjectNameSubcommandTests.test_control_char_value_rejected
        # for why this isn't NUL.
        proc = _run_helper(
            self.devforge_dir, "set-architecture", "bad\x01arch"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"ARCHITECTURE", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_del_control_char_rejected(self):
        # 0x7F (DEL) — verifies the high-end control char branch.
        proc = _run_helper(
            self.devforge_dir, "set-architecture", "bad\x7farch"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"ARCHITECTURE", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_newline_in_value_rejected(self):
        # ARCHITECTURE is a single-line pattern label; embedded LF would
        # silently corrupt template substitution.
        proc = _run_helper(
            self.devforge_dir, "set-architecture", "Clean\nArchitecture"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"ARCHITECTURE", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_pretty_printed_with_sorted_keys(self):
        # Insert keys in non-sorted order; verify file has sorted output.
        self._write_state({"ZZZ_LAST": "z", "AAA_FIRST": "a"})
        proc = _run_helper(
            self.devforge_dir, "set-architecture", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        content = self.state_file.read_text(encoding="utf-8")
        self.assertIn('  "AAA_FIRST": "a"', content)
        self.assertIn('  "ARCHITECTURE": "Clean Architecture"', content)
        self.assertIn('  "ZZZ_LAST": "z"', content)
        # Sorted: AAA appears before ARCHITECTURE, which appears before ZZZ.
        self.assertLess(
            content.index("AAA_FIRST"), content.index("ARCHITECTURE")
        )
        self.assertLess(
            content.index("ARCHITECTURE"), content.index("ZZZ_LAST")
        )

    def test_no_temp_files_leaked_after_success(self):
        # mkstemp leaves no leftover files on the happy path.
        proc = _run_helper(
            self.devforge_dir, "set-architecture", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        leftovers = [
            p.name
            for p in self.devforge_dir.iterdir()
            if p.name.startswith("wizard-render-state-")
        ]
        self.assertEqual(leftovers, [])


class SetErrorHandlingSubcommandTests(_StringSetterTestBase):
    """End-to-end behavior of `wizard_render set-error-handling`.

    ERROR_HANDLING is a single-line description combining library +
    pattern (e.g. "purify-ts Either", "neverthrow with Result type",
    "try/catch"). Same validation policy as PROJECT_NAME (no LF/CR, no
    other control chars).
    """

    HAPPY_VALUE = "purify-ts Either"

    def test_writes_key_to_new_state_file(self):
        self.assertFalse(self.state_file.exists())
        proc = _run_helper(
            self.devforge_dir, "set-error-handling", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.state_file.exists())
        self.assertEqual(
            self._read_state(), {"ERROR_HANDLING": self.HAPPY_VALUE}
        )

    def test_merges_into_existing_state(self):
        self._write_state({"PROJECT_NAME": "foo"})
        proc = _run_helper(
            self.devforge_dir, "set-error-handling", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(),
            {"ERROR_HANDLING": self.HAPPY_VALUE, "PROJECT_NAME": "foo"},
        )

    def test_overwrites_prior_value(self):
        self._write_state({"ERROR_HANDLING": "old pattern"})
        proc = _run_helper(
            self.devforge_dir, "set-error-handling", "try/catch"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(), {"ERROR_HANDLING": "try/catch"}
        )

    def test_empty_value_rejected(self):
        proc = _run_helper(self.devforge_dir, "set-error-handling", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"ERROR_HANDLING", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_whitespace_only_value_rejected(self):
        proc = _run_helper(
            self.devforge_dir, "set-error-handling", "   \t  "
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"ERROR_HANDLING", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_control_char_value_rejected(self):
        # 0x01 — see SetProjectNameSubcommandTests.test_control_char_value_rejected
        # for why this isn't NUL.
        proc = _run_helper(
            self.devforge_dir, "set-error-handling", "bad\x01eh"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"ERROR_HANDLING", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_del_control_char_rejected(self):
        # 0x7F (DEL) — verifies the high-end control char branch.
        proc = _run_helper(
            self.devforge_dir, "set-error-handling", "bad\x7feh"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"ERROR_HANDLING", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_newline_in_value_rejected(self):
        # ERROR_HANDLING is a single-line description; embedded LF would
        # silently corrupt template substitution.
        proc = _run_helper(
            self.devforge_dir,
            "set-error-handling",
            "purify-ts\nEither",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"ERROR_HANDLING", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_pretty_printed_with_sorted_keys(self):
        # Insert keys in non-sorted order; verify file has sorted output.
        self._write_state({"ZZZ_LAST": "z", "AAA_FIRST": "a"})
        proc = _run_helper(
            self.devforge_dir, "set-error-handling", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        content = self.state_file.read_text(encoding="utf-8")
        self.assertIn('  "AAA_FIRST": "a"', content)
        self.assertIn('  "ERROR_HANDLING": "purify-ts Either"', content)
        self.assertIn('  "ZZZ_LAST": "z"', content)
        # Sorted: AAA appears before ERROR_HANDLING, which appears before ZZZ.
        self.assertLess(
            content.index("AAA_FIRST"), content.index("ERROR_HANDLING")
        )
        self.assertLess(
            content.index("ERROR_HANDLING"), content.index("ZZZ_LAST")
        )

    def test_no_temp_files_leaked_after_success(self):
        # mkstemp leaves no leftover files on the happy path.
        proc = _run_helper(
            self.devforge_dir, "set-error-handling", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        leftovers = [
            p.name
            for p in self.devforge_dir.iterdir()
            if p.name.startswith("wizard-render-state-")
        ]
        self.assertEqual(leftovers, [])


class SetRuntimeUrlSubcommandTests(_StringSetterTestBase):
    """End-to-end behavior of `wizard_render set-runtime-url`.

    RUNTIME_URL is a single-line URL OR the literal sentinel "N/A" when
    the project has no runtime URL. The sentinel passes the strict
    string validator naturally — no special-case branch is needed. Same
    validation policy as PROJECT_NAME (no LF/CR, no other control chars).
    """

    HAPPY_VALUE = "http://localhost:3000"

    def test_writes_key_to_new_state_file(self):
        self.assertFalse(self.state_file.exists())
        proc = _run_helper(
            self.devforge_dir, "set-runtime-url", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.state_file.exists())
        self.assertEqual(
            self._read_state(), {"RUNTIME_URL": self.HAPPY_VALUE}
        )

    def test_merges_into_existing_state(self):
        self._write_state({"PROJECT_NAME": "foo"})
        proc = _run_helper(
            self.devforge_dir, "set-runtime-url", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(),
            {"PROJECT_NAME": "foo", "RUNTIME_URL": self.HAPPY_VALUE},
        )

    def test_overwrites_prior_value(self):
        self._write_state({"RUNTIME_URL": "http://old.example.com"})
        proc = _run_helper(
            self.devforge_dir, "set-runtime-url", "http://new.example.com"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(),
            {"RUNTIME_URL": "http://new.example.com"},
        )

    def test_empty_value_rejected(self):
        proc = _run_helper(self.devforge_dir, "set-runtime-url", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"RUNTIME_URL", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_whitespace_only_value_rejected(self):
        proc = _run_helper(self.devforge_dir, "set-runtime-url", "   ")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"RUNTIME_URL", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_control_char_value_rejected(self):
        # 0x01 — see SetProjectNameSubcommandTests.test_control_char_value_rejected
        # for why this isn't NUL.
        proc = _run_helper(
            self.devforge_dir, "set-runtime-url", "http://bad\x01url"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"RUNTIME_URL", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_del_control_char_rejected(self):
        # 0x7F (DEL) — verifies the high-end control char branch.
        proc = _run_helper(
            self.devforge_dir, "set-runtime-url", "http://bad\x7furl"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"RUNTIME_URL", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_newline_in_value_rejected(self):
        # RUNTIME_URL is a single-line URL; embedded LF would silently
        # corrupt template substitution.
        proc = _run_helper(
            self.devforge_dir,
            "set-runtime-url",
            "http://localhost:3000\nextra",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"RUNTIME_URL", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_pretty_printed_with_sorted_keys(self):
        # Insert keys in non-sorted order; verify file has sorted output.
        self._write_state({"ZZZ_LAST": "z", "AAA_FIRST": "a"})
        proc = _run_helper(
            self.devforge_dir, "set-runtime-url", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        content = self.state_file.read_text(encoding="utf-8")
        self.assertIn('  "AAA_FIRST": "a"', content)
        self.assertIn(
            '  "RUNTIME_URL": "http://localhost:3000"', content
        )
        self.assertIn('  "ZZZ_LAST": "z"', content)
        # Sorted: AAA appears before RUNTIME_URL, which appears before ZZZ.
        self.assertLess(
            content.index("AAA_FIRST"), content.index("RUNTIME_URL")
        )
        self.assertLess(
            content.index("RUNTIME_URL"), content.index("ZZZ_LAST")
        )

    def test_no_temp_files_leaked_after_success(self):
        # mkstemp leaves no leftover files on the happy path.
        proc = _run_helper(
            self.devforge_dir, "set-runtime-url", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        leftovers = [
            p.name
            for p in self.devforge_dir.iterdir()
            if p.name.startswith("wizard-render-state-")
        ]
        self.assertEqual(leftovers, [])

    def test_na_sentinel_accepted(self):
        # Q6 spec (line 107): when the project has no runtime URL, the
        # user replies 'N/A' and the helper saves it verbatim. The
        # strict string validator already accepts non-empty
        # non-control-char strings, so the sentinel passes naturally —
        # this test pins that contract so future tightening of
        # _validate_string can't silently reject the documented value.
        proc = _run_helper(self.devforge_dir, "set-runtime-url", "N/A")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state(), {"RUNTIME_URL": "N/A"})


class SetApiLayerSubcommandTests(_StringSetterTestBase):
    """End-to-end behavior of `wizard_render set-api-layer`.

    API_LAYER is a single-line label naming the project's API style —
    one of the four Q7 options ("REST", "GraphQL", "tRPC", "N/A") or a
    free-text custom value. Same validation policy as PROJECT_NAME (no
    LF/CR, no other control chars). The "N/A" sentinel passes the strict
    string validator naturally; no special-case branch is needed.
    """

    HAPPY_VALUE = "REST"

    def test_writes_key_to_new_state_file(self):
        self.assertFalse(self.state_file.exists())
        proc = _run_helper(
            self.devforge_dir, "set-api-layer", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.state_file.exists())
        self.assertEqual(
            self._read_state(), {"API_LAYER": self.HAPPY_VALUE}
        )

    def test_merges_into_existing_state(self):
        self._write_state({"PROJECT_NAME": "foo"})
        proc = _run_helper(
            self.devforge_dir, "set-api-layer", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(),
            {"API_LAYER": self.HAPPY_VALUE, "PROJECT_NAME": "foo"},
        )

    def test_overwrites_prior_value(self):
        self._write_state({"API_LAYER": "REST"})
        proc = _run_helper(self.devforge_dir, "set-api-layer", "GraphQL")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state(), {"API_LAYER": "GraphQL"})

    def test_empty_value_rejected(self):
        proc = _run_helper(self.devforge_dir, "set-api-layer", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"API_LAYER", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_whitespace_only_value_rejected(self):
        proc = _run_helper(self.devforge_dir, "set-api-layer", "   ")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"API_LAYER", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_control_char_value_rejected(self):
        # 0x01 — see SetProjectNameSubcommandTests.test_control_char_value_rejected
        # for why this isn't NUL.
        proc = _run_helper(
            self.devforge_dir, "set-api-layer", "bad\x01layer"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"API_LAYER", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_del_control_char_rejected(self):
        # 0x7F (DEL) — verifies the high-end control char branch.
        proc = _run_helper(
            self.devforge_dir, "set-api-layer", "bad\x7flayer"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"API_LAYER", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_newline_in_value_rejected(self):
        # API_LAYER is a single-line label; embedded LF would silently
        # corrupt template substitution.
        proc = _run_helper(
            self.devforge_dir, "set-api-layer", "REST\nGraphQL"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"API_LAYER", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_pretty_printed_with_sorted_keys(self):
        # Insert keys in non-sorted order; verify file has sorted output.
        self._write_state({"ZZZ_LAST": "z", "AAA_FIRST": "a"})
        proc = _run_helper(
            self.devforge_dir, "set-api-layer", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        content = self.state_file.read_text(encoding="utf-8")
        self.assertIn('  "AAA_FIRST": "a"', content)
        self.assertIn('  "API_LAYER": "REST"', content)
        self.assertIn('  "ZZZ_LAST": "z"', content)
        # Sorted: AAA appears before API_LAYER, which appears before ZZZ.
        self.assertLess(
            content.index("AAA_FIRST"), content.index("API_LAYER")
        )
        self.assertLess(
            content.index("API_LAYER"), content.index("ZZZ_LAST")
        )

    def test_no_temp_files_leaked_after_success(self):
        # mkstemp leaves no leftover files on the happy path.
        proc = _run_helper(
            self.devforge_dir, "set-api-layer", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        leftovers = [
            p.name
            for p in self.devforge_dir.iterdir()
            if p.name.startswith("wizard-render-state-")
        ]
        self.assertEqual(leftovers, [])

    def test_na_sentinel_accepted(self):
        # Q7 spec (line 119): when the project has no API layer (library,
        # CLI, static site), the user picks the "N/A" option and the
        # helper saves it verbatim. The strict string validator already
        # accepts non-empty non-control-char strings, so the sentinel
        # passes naturally — this test pins that contract so future
        # tightening of _validate_string can't silently reject the
        # documented value.
        proc = _run_helper(self.devforge_dir, "set-api-layer", "N/A")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state(), {"API_LAYER": "N/A"})


class SetTestingSubcommandTests(_StringSetterTestBase):
    """End-to-end behavior of `wizard_render set-testing`.

    TESTING is a single-line label naming the project's testing framework
    — one of the four Q8 options ("pytest", "vitest", "jest", "N/A") or a
    free-text custom value (e.g. "go test", "cargo test"). Same validation
    policy as PROJECT_NAME (no LF/CR, no other control chars). The "N/A"
    sentinel passes the strict string validator naturally; no special-case
    branch is needed. Spaces are valid (e.g. "go test", "cargo test")
    because no whitespace-collapse transform is applied.
    """

    HAPPY_VALUE = "pytest"

    def test_writes_key_to_new_state_file(self):
        self.assertFalse(self.state_file.exists())
        proc = _run_helper(
            self.devforge_dir, "set-testing", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(self.state_file.exists())
        self.assertEqual(
            self._read_state(), {"TESTING": self.HAPPY_VALUE}
        )

    def test_merges_into_existing_state(self):
        self._write_state({"PROJECT_NAME": "foo"})
        proc = _run_helper(
            self.devforge_dir, "set-testing", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(),
            {"PROJECT_NAME": "foo", "TESTING": self.HAPPY_VALUE},
        )

    def test_overwrites_prior_value(self):
        self._write_state({"TESTING": "pytest"})
        proc = _run_helper(self.devforge_dir, "set-testing", "vitest")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state(), {"TESTING": "vitest"})

    def test_empty_value_rejected(self):
        proc = _run_helper(self.devforge_dir, "set-testing", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"TESTING", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_whitespace_only_value_rejected(self):
        proc = _run_helper(self.devforge_dir, "set-testing", "   ")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"TESTING", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_control_char_value_rejected(self):
        # 0x01 — see SetProjectNameSubcommandTests.test_control_char_value_rejected
        # for why this isn't NUL.
        proc = _run_helper(
            self.devforge_dir, "set-testing", "bad\x01test"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"TESTING", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_del_control_char_rejected(self):
        # 0x7F (DEL) — verifies the high-end control char branch.
        proc = _run_helper(
            self.devforge_dir, "set-testing", "bad\x7ftest"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"TESTING", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_newline_in_value_rejected(self):
        # TESTING is a single-line framework label; embedded LF would
        # silently corrupt template substitution.
        proc = _run_helper(
            self.devforge_dir, "set-testing", "pytest\nvitest"
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"TESTING", proc.stderr)
        self.assertFalse(self.state_file.exists())

    def test_pretty_printed_with_sorted_keys(self):
        # Insert keys in non-sorted order; verify file has sorted output.
        self._write_state({"ZZZ_LAST": "z", "AAA_FIRST": "a"})
        proc = _run_helper(
            self.devforge_dir, "set-testing", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        content = self.state_file.read_text(encoding="utf-8")
        self.assertIn('  "AAA_FIRST": "a"', content)
        self.assertIn('  "TESTING": "pytest"', content)
        self.assertIn('  "ZZZ_LAST": "z"', content)
        # Sorted: AAA appears before TESTING, which appears before ZZZ.
        self.assertLess(
            content.index("AAA_FIRST"), content.index("TESTING")
        )
        self.assertLess(
            content.index("TESTING"), content.index("ZZZ_LAST")
        )

    def test_no_temp_files_leaked_after_success(self):
        # mkstemp leaves no leftover files on the happy path.
        proc = _run_helper(
            self.devforge_dir, "set-testing", self.HAPPY_VALUE
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        leftovers = [
            p.name
            for p in self.devforge_dir.iterdir()
            if p.name.startswith("wizard-render-state-")
        ]
        self.assertEqual(leftovers, [])

    def test_na_sentinel_accepted(self):
        # Q8 spec (line 137): when the project has no testing framework,
        # the user picks the "N/A" option and the helper saves it
        # verbatim. The strict string validator already accepts non-empty
        # non-control-char strings, so the sentinel passes naturally —
        # this test pins that contract so future tightening of
        # _validate_string can't silently reject the documented value.
        proc = _run_helper(self.devforge_dir, "set-testing", "N/A")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state(), {"TESTING": "N/A"})

    def test_spaced_value_accepted(self):
        # Q8 auto-Other captures free-text custom values that legitimately
        # contain spaces ("go test", "cargo test", "JUnit 5"). The helper
        # preserves the value verbatim — no whitespace-collapse, no
        # tokenization. This test pins that contract so a future
        # well-meaning "normalize whitespace" change can't silently mangle
        # the value passed in by the agent.
        proc = _run_helper(self.devforge_dir, "set-testing", "go test")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._read_state(), {"TESTING": "go test"})


class SetterCompositionTests(_StringSetterTestBase):
    """Verify the setters compose correctly into a shared state file."""

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

    def test_all_three_setters_coexist_in_state(self):
        # Sequential setter calls accumulate into a single state dict.
        # Narrower test kept intentionally alongside the all-six version
        # below: it pins the original three-setter contract from the prior
        # round so any regression on those specific keys surfaces with a
        # focused failure rather than buried in the all-six assertion diff.
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
        proc = _run_helper(
            self.devforge_dir,
            "set-project-type",
            "Frontend / web application",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(),
            {
                "PROJECT_NAME": "my-project",
                "PROJECT_DESCRIPTION": "My project description.",
                "PROJECT_TYPE": "Frontend / web application",
            },
        )

    def test_all_eight_setters_coexist_in_state(self):
        # Sequential setter calls across all eight Phase 2 fields
        # accumulate into a single state dict — verifies no key collision
        # and that each setter merges (rather than overwrites) the dict.
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
        proc = _run_helper(
            self.devforge_dir,
            "set-project-type",
            "Frontend / web application",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = _run_helper(
            self.devforge_dir, "set-architecture", "Clean Architecture"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = _run_helper(
            self.devforge_dir,
            "set-error-handling",
            "purify-ts Either",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = _run_helper(
            self.devforge_dir,
            "set-runtime-url",
            "http://localhost:3000",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = _run_helper(
            self.devforge_dir, "set-api-layer", "REST"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc = _run_helper(
            self.devforge_dir, "set-testing", "pytest"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            self._read_state(),
            {
                "PROJECT_NAME": "my-project",
                "PROJECT_DESCRIPTION": "My project description.",
                "PROJECT_TYPE": "Frontend / web application",
                "ARCHITECTURE": "Clean Architecture",
                "ERROR_HANDLING": "purify-ts Either",
                "RUNTIME_URL": "http://localhost:3000",
                "API_LAYER": "REST",
                "TESTING": "pytest",
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
