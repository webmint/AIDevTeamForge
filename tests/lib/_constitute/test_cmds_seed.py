"""Tests for _cmds_seed.cmd_seed_universal (D3(a), plan 104 Phase 3 Unit A).

Moved out of tests/lib/test_constitute_helper.py in a behavior-preserving
restructure (Unit D follow-up, mirrors the _cmds_seed.py source-module
split): test bodies and the real-CLI subprocess approach are unchanged from
the original file — only the location and the path-computation prologue
moved, following the pattern this package's other test files use (see
test_verify_forcing_function_keys.py) adjusted for the subprocess-based
CLI invocation this class needs.

Real-producer principle: every fixture is built via `reset` +
`seed-universal --canonical-path <repo>/src/constitution.md` through the
real CLI subprocess — never a hand-authored constitute.json.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "constitute_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import constitute_helper  # noqa: E402


def _run(argv, cwd=None, env=None):
    """Run constitute_helper.py with given argv; capture output."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(argv),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


class TestSeedUniversal(unittest.TestCase):
    """Tests for the `seed-universal` subcommand (_cmds_seed.cmd_seed_universal).

    Real-producer principle: every fixture is built via `reset` +
    `seed-universal --canonical-path <repo>/src/constitution.md` through the
    real CLI subprocess — never a hand-authored constitute.json.
    """

    _CANONICAL = _REPO_ROOT / "src" / "constitution.md"

    def _seed(self, devforge, canonical_path=None):
        args = ["--devforge-dir", str(devforge), "seed-universal"]
        if canonical_path is not None:
            args += ["--canonical-path", str(canonical_path)]
        return _run(args)

    def test_happy_path_all_11_sections_populated(self):
        """Fresh reset + seed-universal -> all 11 _UNIVERSAL_SECTIONS keys
        present with non-empty rules, via _extract_universal_rules_from_state."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset"])
            result = self._seed(devforge, self._CANONICAL)
            self.assertEqual(result.returncode, 0, result.stderr)

            state_path = devforge / "constitute.json"
            extracted = constitute_helper._extract_universal_rules_from_state(state_path)
            expected_keys = {
                "§3.5", "§3.6", "§3.7", "§3.8",
                "§4.1", "§4.2", "§4.3",
                "§6.1", "§6.2", "§6.3", "§6.4",
            }
            self.assertEqual(set(extracted.keys()), expected_keys)
            for key, val in extracted.items():
                self.assertGreater(len(val["rules"]), 0, msg=key)

    def test_verify_universal_defaults_exits_0_zero_findings(self):
        """Headline Phase 3 check: forge-internal:verify-universal-defaults
        against a seed-universal'd state exits 0 with zero findings."""
        with tempfile.TemporaryDirectory() as tmp:
            consumer_root = Path(tmp)
            devforge = consumer_root / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset"])
            seed_result = self._seed(devforge, self._CANONICAL)
            self.assertEqual(seed_result.returncode, 0, seed_result.stderr)

            result = subprocess.run(
                [
                    sys.executable, str(_HELPER_PY),
                    "forge-internal:verify-universal-defaults",
                    "--consumer-path", str(consumer_root),
                    "--canonical-path", str(self._CANONICAL),
                ],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["findings"], [], msg=report["findings"])

    def test_idempotent_byte_identical(self):
        """Running seed-universal twice yields byte-identical constitute.json."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset"])
            r1 = self._seed(devforge, self._CANONICAL)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            first = (devforge / "constitute.json").read_bytes()

            r2 = self._seed(devforge, self._CANONICAL)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            second = (devforge / "constitute.json").read_bytes()

            self.assertEqual(first, second)

    def test_project_section_added_first_survives_seeding(self):
        """A project-specific section (3.1) added before seeding survives it."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset"])
            _run(["--devforge-dir", str(devforge), "add-section",
                  "--bucket", "code-quality", "--number", "3.1",
                  "--title", "Type Safety", "--tag", "project-specific"])
            _run(["--devforge-dir", str(devforge), "add-rule",
                  "--section", "3.1", "--tag", "project-specific",
                  "--text", "Use strict TypeScript settings."])

            result = self._seed(devforge, self._CANONICAL)
            self.assertEqual(result.returncode, 0, result.stderr)

            state = json.loads((devforge / "constitute.json").read_text(encoding="utf-8"))
            sections_31 = [s for s in state["code_quality_standards"] if s["number"] == "3.1"]
            self.assertEqual(len(sections_31), 1)
            self.assertEqual(sections_31[0]["title"], "Type Safety")
            self.assertEqual(sections_31[0]["tag"], "project-specific")
            self.assertEqual(len(sections_31[0]["rules"]), 1)
            self.assertEqual(
                sections_31[0]["rules"][0]["text"], "Use strict TypeScript settings."
            )
            # §3.5 was also seeded alongside it.
            numbers = {s["number"] for s in state["code_quality_standards"]}
            self.assertIn("3.5", numbers)

    def test_seeding_replaces_pre_existing_section_regardless_of_tag(self):
        """python-reviewer LOW finding: a pre-existing section already
        occupying a universal number is wholesale-replaced by seeding
        regardless of its own tag or rules — a hand-composed
        project-specific §3.5 becomes the canonical universal §3.5 only."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset"])
            _run(["--devforge-dir", str(devforge), "add-section",
                  "--bucket", "code-quality", "--number", "3.5",
                  "--title", "My Custom Quality Rules", "--tag", "project-specific"])
            _run(["--devforge-dir", str(devforge), "add-rule",
                  "--section", "3.5", "--tag", "project-specific",
                  "--text", "A user-authored rule that should not survive seeding."])

            result = self._seed(devforge, self._CANONICAL)
            self.assertEqual(result.returncode, 0, result.stderr)

            state = json.loads((devforge / "constitute.json").read_text(encoding="utf-8"))
            sections_35 = [s for s in state["code_quality_standards"] if s["number"] == "3.5"]
            self.assertEqual(len(sections_35), 1)
            section = sections_35[0]
            self.assertEqual(section["tag"], "universal")
            self.assertNotEqual(section["title"], "My Custom Quality Rules")
            rule_texts = [r["text"] for r in section["rules"]]
            self.assertNotIn(
                "A user-authored rule that should not survive seeding.", rule_texts
            )

    def test_missing_canonical_file_exits_1_state_unchanged(self):
        """A nonexistent --canonical-path exits 1 and leaves state unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset"])
            before = (devforge / "constitute.json").read_bytes()

            missing = Path(tmp) / "does-not-exist.md"
            result = self._seed(devforge, missing)
            self.assertEqual(result.returncode, 1, result.stderr)

            after = (devforge / "constitute.json").read_bytes()
            self.assertEqual(before, after)

    def test_canonical_missing_section_exits_2_state_unchanged(self):
        """A canonical file lacking §3.8 exits 2 naming it; state unchanged."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset"])
            before = (devforge / "constitute.json").read_bytes()

            # Mangle §3.8's heading number so the parser can never record it
            # (regex requires the number to be followed by whitespace).
            text = self._CANONICAL.read_text(encoding="utf-8")
            self.assertEqual(text.count("### 3.8 "), 1)
            mangled = text.replace("### 3.8 ", "### 3.8x ")
            mangled_path = Path(tmp) / "mangled-constitution.md"
            mangled_path.write_text(mangled, encoding="utf-8")

            result = self._seed(devforge, mangled_path)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("§3.8", result.stderr)

            after = (devforge / "constitute.json").read_bytes()
            self.assertEqual(before, after)

    def test_default_canonical_path_is_devforge_dir_templates(self):
        """Omitting --canonical-path reads <devforge-dir>/templates/constitution.md."""
        with tempfile.TemporaryDirectory() as tmp:
            devforge = Path(tmp) / ".devforge"
            _run(["--devforge-dir", str(devforge), "reset"])

            templates_dir = devforge / "templates"
            templates_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(self._CANONICAL, templates_dir / "constitution.md")

            result = self._seed(devforge)  # no --canonical-path
            self.assertEqual(result.returncode, 0, result.stderr)

            state_path = devforge / "constitute.json"
            extracted = constitute_helper._extract_universal_rules_from_state(state_path)
            self.assertIn("§3.5", extracted)


if __name__ == "__main__":
    unittest.main()
