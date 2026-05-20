"""Tests for src/devforge/lib/_pr_review/_validators.py.

Coverage:
  _die — writes msg + newline to stderr, returns correct exit code.
  _validate_pr_number — happy path (int/str), rejects 0/negative/non-numeric/None.
"""

import io
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _pr_review._validators import _die, _validate_pr_number  # noqa: E402


class TestDie(unittest.TestCase):
    def _capture_stderr(self, fn):
        """Run fn with stderr replaced by a StringIO; return (result, captured)."""
        buf = io.StringIO()
        old_stderr = sys.stderr
        sys.stderr = buf
        try:
            result = fn()
        finally:
            sys.stderr = old_stderr
        return result, buf.getvalue()

    def test_default_code_is_1(self):
        code, _ = self._capture_stderr(lambda: _die("some error"))
        self.assertEqual(code, 1)

    def test_custom_code_returned(self):
        code, _ = self._capture_stderr(lambda: _die("some error", code=2))
        self.assertEqual(code, 2)

    def test_message_written_to_stderr(self):
        _, captured = self._capture_stderr(lambda: _die("hello error"))
        self.assertIn("pr_review_helper: hello error", captured)

    def test_message_has_trailing_newline(self):
        _, captured = self._capture_stderr(lambda: _die("msg"))
        self.assertTrue(captured.endswith("\n"), repr(captured))

    def test_empty_message(self):
        code, captured = self._capture_stderr(lambda: _die(""))
        self.assertEqual(code, 1)
        self.assertEqual(captured, "pr_review_helper: \n")

    def test_code_zero_is_valid(self):
        code, _ = self._capture_stderr(lambda: _die("ok", code=0))
        self.assertEqual(code, 0)


class TestValidatePrNumber(unittest.TestCase):
    def test_positive_int_returns_int(self):
        self.assertEqual(_validate_pr_number(42), 42)

    def test_positive_string_returns_int(self):
        self.assertEqual(_validate_pr_number("42"), 42)

    def test_string_one_returns_one(self):
        self.assertEqual(_validate_pr_number("1"), 1)

    def test_large_number(self):
        self.assertEqual(_validate_pr_number(99999), 99999)

    def test_zero_raises_value_error(self):
        with self.assertRaises(ValueError):
            _validate_pr_number(0)

    def test_string_zero_raises_value_error(self):
        with self.assertRaises(ValueError):
            _validate_pr_number("0")

    def test_negative_int_raises_value_error(self):
        with self.assertRaises(ValueError):
            _validate_pr_number(-1)

    def test_negative_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            _validate_pr_number("-5")

    def test_non_numeric_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            _validate_pr_number("not_a_number")

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            _validate_pr_number("")

    def test_float_string_raises_value_error(self):
        """'3.5' is not a valid PR number (not an integer string)."""
        with self.assertRaises(ValueError):
            _validate_pr_number("3.5")

    def test_none_raises_type_error(self):
        """None raises TypeError as documented in the function docstring."""
        with self.assertRaises(TypeError):
            _validate_pr_number(None)


if __name__ == "__main__":
    unittest.main()
