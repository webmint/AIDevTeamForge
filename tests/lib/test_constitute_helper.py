"""Tests for src/devforge/lib/constitute_helper.py — Step 0 scaffolding.

Step 0 coverage: reset subcommand writes a JSON defaults file with the
locked top-level shape (project_name / generated_date / last_updated /
mode / project_identity / 5 section-array buckets / patterns_and_
antipatterns 6-bucket struct / scaffolding_guide nullable). Idempotent:
byte-identical re-runs.

Subprocess test runs in a tempfile.TemporaryDirectory. Pure-function
tests import the module directly.

Stdlib only.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "constitute_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import constitute_helper  # noqa: E402


def _run(argv, cwd):
    return subprocess.run(
        [sys.executable, str(_HELPER_PY), *argv],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


class TestStep0Scaffolding(unittest.TestCase):
    def test_default_state_top_level_shape(self):
        """default_state() returns the locked top-level keys with correct types."""
        state = constitute_helper.default_state()

        self.assertIsNone(state["project_name"])
        self.assertIsNone(state["generated_date"])
        self.assertIsNone(state["last_updated"])
        self.assertIsNone(state["mode"])
        self.assertIsNone(state["project_identity"])
        self.assertEqual(state["architecture_rules"], [])
        self.assertEqual(state["code_quality_standards"], [])
        self.assertEqual(state["domain_rules"], [])
        self.assertEqual(state["workflow_rules"], [])
        self.assertIsNone(state["scaffolding_guide"])

        patterns = state["patterns_and_antipatterns"]
        self.assertEqual(
            sorted(patterns.keys()),
            sorted([
                "always_universal",
                "always_project_specific",
                "never_universal",
                "never_project_specific",
                "prefer_universal",
                "prefer_project_specific",
            ]),
        )
        for bucket in patterns.values():
            self.assertEqual(bucket, [])

    def test_reset_writes_default_state_json(self):
        """reset writes constitute.json containing the default state."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "reset"], cwd=tmp_path)

            self.assertEqual(result.returncode, 0, result.stderr)

            output_file = devforge / "constitute.json"
            self.assertTrue(output_file.exists())

            loaded = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(loaded, constitute_helper.default_state())

    def test_reset_idempotent_byte_identical(self):
        """Re-running reset produces byte-identical output."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"

            r1 = _run(["--devforge-dir", str(devforge), "reset"], cwd=tmp_path)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            first = (devforge / "constitute.json").read_bytes()

            r2 = _run(["--devforge-dir", str(devforge), "reset"], cwd=tmp_path)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            second = (devforge / "constitute.json").read_bytes()

            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
