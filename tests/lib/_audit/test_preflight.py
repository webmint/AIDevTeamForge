"""Tests for src/devforge/lib/_audit/_preflight.py.

Coverage:
  resolve_mode — all documented argument shapes
  check_agents — 0 / partial / all agent files present
  preflight_context — no files, sentinel constitution, real constitution,
                      CLAUDE.md source-root extraction, MEMORY.md present
"""

import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

from _audit._preflight import check_agents, preflight_context, resolve_mode  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ok(result: dict) -> dict:
    """Assert no error and return result for chaining."""
    assert result["error"] is None, "Unexpected error: {!r}".format(result["error"])
    return result


# ---------------------------------------------------------------------------
# resolve_mode tests
# ---------------------------------------------------------------------------

class TestResolveModeEmpty(unittest.TestCase):
    def test_empty_string_gives_broad(self):
        r = _ok(resolve_mode(""))
        self.assertEqual(r["mode"], "broad")

    def test_whitespace_only_gives_broad(self):
        r = _ok(resolve_mode("   "))
        self.assertEqual(r["mode"], "broad")

    def test_no_args_defaults(self):
        r = _ok(resolve_mode(""))
        self.assertFalse(r["uncommitted"])
        self.assertIsNone(r["top_n"])
        self.assertIsNone(r["weights"])
        self.assertEqual(r["scope_limit"], 200)
        self.assertIsNone(r["line_range"])
        self.assertIsNone(r["scope_arg"])


class TestResolveModeFull(unittest.TestCase):
    def test_full_flag_gives_broad(self):
        r = _ok(resolve_mode("--full"))
        self.assertEqual(r["mode"], "broad")

    def test_full_with_scope_limit(self):
        r = _ok(resolve_mode("--full --scope-limit 50"))
        self.assertEqual(r["mode"], "broad")
        self.assertEqual(r["scope_limit"], 50)


class TestResolveModeUncommitted(unittest.TestCase):
    def test_uncommitted_gives_narrow(self):
        r = _ok(resolve_mode("--uncommitted"))
        self.assertEqual(r["mode"], "narrow")
        self.assertTrue(r["uncommitted"])

    def test_uncommitted_with_scope_limit(self):
        r = _ok(resolve_mode("--uncommitted --scope-limit 100"))
        self.assertEqual(r["mode"], "narrow")
        self.assertTrue(r["uncommitted"])
        self.assertEqual(r["scope_limit"], 100)


class TestResolveModeHotspot(unittest.TestCase):
    def test_top_25_gives_hotspot(self):
        r = _ok(resolve_mode("--top 25"))
        self.assertEqual(r["mode"], "hotspot")
        self.assertEqual(r["top_n"], 25)
        self.assertIsNone(r["weights"])

    def test_top_10(self):
        r = _ok(resolve_mode("--top 10"))
        self.assertEqual(r["top_n"], 10)

    def test_top_with_weights(self):
        r = _ok(resolve_mode("--top 10 --weights c=0.5,k=0.4,s=0.1"))
        self.assertEqual(r["mode"], "hotspot")
        self.assertEqual(r["top_n"], 10)
        self.assertIsNotNone(r["weights"])
        self.assertAlmostEqual(r["weights"]["c"], 0.5)
        self.assertAlmostEqual(r["weights"]["k"], 0.4)
        self.assertAlmostEqual(r["weights"]["s"], 0.1)

    def test_bad_top_value_error(self):
        r = resolve_mode("--top abc")
        self.assertIsNotNone(r["error"])
        self.assertIsNone(r["mode"])

    def test_negative_top_error(self):
        r = resolve_mode("--top -5")
        self.assertIsNotNone(r["error"])
        self.assertIsNone(r["mode"])

    def test_zero_top_error(self):
        r = resolve_mode("--top 0")
        self.assertIsNotNone(r["error"])
        self.assertIsNone(r["mode"])

    def test_weight_out_of_range_error(self):
        r = resolve_mode("--top 10 --weights c=1.5,k=0.4,s=0.1")
        self.assertIsNotNone(r["error"])
        self.assertIsNone(r["mode"])


class TestResolveModeNarrowPath(unittest.TestCase):
    def test_plain_path_gives_narrow(self):
        r = _ok(resolve_mode("src/auth/login.ts"))
        self.assertEqual(r["mode"], "narrow")
        self.assertEqual(r["scope_arg"], "src/auth/login.ts")
        self.assertIsNone(r["line_range"])

    def test_path_with_line_range(self):
        r = _ok(resolve_mode("src/auth/login.ts:42-87"))
        self.assertEqual(r["mode"], "narrow")
        self.assertEqual(r["scope_arg"], "src/auth/login.ts")
        self.assertEqual(r["line_range"], "42-87")

    def test_path_without_range_line_range_is_none(self):
        r = _ok(resolve_mode("src/utils.py"))
        self.assertIsNone(r["line_range"])
        self.assertEqual(r["scope_arg"], "src/utils.py")

    def test_scope_limit_with_path(self):
        r = _ok(resolve_mode("src/auth/login.ts --scope-limit 50"))
        self.assertEqual(r["mode"], "narrow")
        self.assertEqual(r["scope_arg"], "src/auth/login.ts")
        self.assertEqual(r["scope_limit"], 50)


class TestResolveModeScopeLimit(unittest.TestCase):
    def test_scope_limit_override_with_full(self):
        r = _ok(resolve_mode("--scope-limit 50 --full"))
        self.assertEqual(r["mode"], "broad")
        self.assertEqual(r["scope_limit"], 50)

    def test_bad_scope_limit_error(self):
        r = resolve_mode("--scope-limit xyz")
        self.assertIsNotNone(r["error"])

    def test_zero_scope_limit_error(self):
        r = resolve_mode("--scope-limit 0")
        self.assertIsNotNone(r["error"])


class TestResolveModeErrors(unittest.TestCase):
    def test_two_paths_error(self):
        r = resolve_mode("src/a.py src/b.py")
        self.assertIsNotNone(r["error"])
        self.assertIsNone(r["mode"])

    def test_unknown_flag_error(self):
        r = resolve_mode("--frobnicate")
        self.assertIsNotNone(r["error"])
        self.assertIsNone(r["mode"])

    def test_path_combined_with_full_error(self):
        r = resolve_mode("--full src/auth.py")
        self.assertIsNotNone(r["error"])
        self.assertIsNone(r["mode"])

    def test_path_combined_with_uncommitted_error(self):
        r = resolve_mode("--uncommitted src/auth.py")
        self.assertIsNotNone(r["error"])
        self.assertIsNone(r["mode"])


class TestResolveModeResultKeys(unittest.TestCase):
    """All result dicts must have the full stable keyset."""

    _EXPECTED_KEYS = {
        "mode", "scope_arg", "uncommitted", "top_n", "weights",
        "scope_limit", "line_range", "error",
    }

    def _assert_keys(self, args_str: str):
        r = resolve_mode(args_str)
        self.assertEqual(set(r.keys()), self._EXPECTED_KEYS,
                         msg="Missing or extra keys for args {!r}".format(args_str))

    def test_keys_empty(self):
        self._assert_keys("")

    def test_keys_full(self):
        self._assert_keys("--full")

    def test_keys_uncommitted(self):
        self._assert_keys("--uncommitted")

    def test_keys_top(self):
        self._assert_keys("--top 10")

    def test_keys_path(self):
        self._assert_keys("src/main.py")

    def test_keys_error_case(self):
        self._assert_keys("--unknown-flag")


# ---------------------------------------------------------------------------
# check_agents tests
# ---------------------------------------------------------------------------

class TestCheckAgents(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.td = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.td)

    def test_all_missing_when_dir_absent(self):
        r = check_agents(os.path.join(self.td, "nonexistent"))
        self.assertTrue(r["all_missing"])
        self.assertEqual(r["present"], [])
        self.assertEqual(sorted(r["missing"]), [
            "architect", "code-reviewer", "qa-engineer", "security-reviewer"
        ])

    def test_all_missing_when_dir_empty(self):
        agents_dir = os.path.join(self.td, "agents")
        os.makedirs(agents_dir)
        r = check_agents(agents_dir)
        self.assertTrue(r["all_missing"])
        self.assertEqual(r["present"], [])

    def test_two_agents_present(self):
        agents_dir = os.path.join(self.td, "agents")
        os.makedirs(agents_dir)
        for name in ("architect", "code-reviewer"):
            open(os.path.join(agents_dir, name + ".md"), "w").close()
        r = check_agents(agents_dir)
        self.assertFalse(r["all_missing"])
        self.assertEqual(r["present"], ["architect", "code-reviewer"])
        self.assertEqual(r["missing"], ["qa-engineer", "security-reviewer"])

    def test_all_agents_present(self):
        agents_dir = os.path.join(self.td, "agents")
        os.makedirs(agents_dir)
        for name in ("architect", "code-reviewer", "qa-engineer", "security-reviewer"):
            open(os.path.join(agents_dir, name + ".md"), "w").close()
        r = check_agents(agents_dir)
        self.assertFalse(r["all_missing"])
        self.assertEqual(r["present"], [
            "architect", "code-reviewer", "qa-engineer", "security-reviewer"
        ])
        self.assertEqual(r["missing"], [])

    def test_non_md_files_ignored(self):
        agents_dir = os.path.join(self.td, "agents")
        os.makedirs(agents_dir)
        # Create .json file — should NOT count as present.
        open(os.path.join(agents_dir, "architect.json"), "w").close()
        r = check_agents(agents_dir)
        self.assertIn("architect", r["missing"])

    def test_result_sorted(self):
        agents_dir = os.path.join(self.td, "agents")
        os.makedirs(agents_dir)
        open(os.path.join(agents_dir, "security-reviewer.md"), "w").close()
        r = check_agents(agents_dir)
        self.assertEqual(r["present"], sorted(r["present"]))
        self.assertEqual(r["missing"], sorted(r["missing"]))


# ---------------------------------------------------------------------------
# preflight_context tests
# ---------------------------------------------------------------------------

class TestPreflightContext(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.td = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.td)

    def _write(self, rel_path: str, content: str) -> str:
        full = os.path.join(self.td, rel_path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return full

    def test_no_files_returns_sane_defaults(self):
        r = preflight_context(self.td)
        self.assertFalse(r["constitution_present"])
        self.assertFalse(r["constitution_populated"])
        self.assertFalse(r["claude_md_present"])
        self.assertFalse(r["memory_present"])
        self.assertEqual(r["memory_excerpt"], "")
        self.assertEqual(r["source_root"], ".")
        self.assertEqual(r["project_type"], "")
        self.assertEqual(r["framework"], "")
        self.assertEqual(r["language"], "")

    def test_constitution_with_sentinel_unpopulated(self):
        self._write("constitution.md", "This file contains {{CONSTITUTION_BODY}} placeholder.")
        r = preflight_context(self.td)
        self.assertTrue(r["constitution_present"])
        self.assertFalse(r["constitution_populated"])

    def test_constitution_with_run_constitute_sentinel(self):
        self._write("constitution.md", "Run `/constitute` to populate this file.")
        r = preflight_context(self.td)
        self.assertTrue(r["constitution_present"])
        self.assertFalse(r["constitution_populated"])

    def test_constitution_with_real_content_populated(self):
        self._write("constitution.md", "# Architecture Rules\n\n1. Use dependency injection.\n2. No globals.")
        r = preflight_context(self.td)
        self.assertTrue(r["constitution_present"])
        self.assertTrue(r["constitution_populated"])

    def test_constitution_absent(self):
        r = preflight_context(self.td)
        self.assertFalse(r["constitution_present"])
        self.assertFalse(r["constitution_populated"])

    def test_claude_md_present(self):
        self._write("CLAUDE.md", "# Project\n\nSome content here.\n")
        r = preflight_context(self.td)
        self.assertTrue(r["claude_md_present"])

    def test_claude_md_source_root_extraction(self):
        content = (
            "# Project\n"
            "- **Project Root**: src/backend\n"
            "- **Type**: web\n"
            "- **Frameworks**: Django\n"
            "- **Languages**: Python\n"
        )
        self._write("CLAUDE.md", content)
        r = preflight_context(self.td)
        self.assertTrue(r["claude_md_present"])
        self.assertEqual(r["source_root"], "src/backend")

    def test_claude_md_project_type_extracted(self):
        content = "- **Type**: library\n"
        self._write("CLAUDE.md", content)
        r = preflight_context(self.td)
        self.assertEqual(r["project_type"], "library")

    def test_claude_md_framework_extracted(self):
        content = "- **Frameworks**: FastAPI\n"
        self._write("CLAUDE.md", content)
        r = preflight_context(self.td)
        self.assertEqual(r["framework"], "FastAPI")

    def test_claude_md_language_extracted(self):
        content = "- **Languages**: TypeScript\n"
        self._write("CLAUDE.md", content)
        r = preflight_context(self.td)
        self.assertEqual(r["language"], "TypeScript")

    def test_memory_present_and_excerpt(self):
        mem_content = "\n".join(
            ["Line {0}".format(i) for i in range(60)]
        ) + "\n"
        self._write(".claude/memory/MEMORY.md", mem_content)
        r = preflight_context(self.td)
        self.assertTrue(r["memory_present"])
        self.assertNotEqual(r["memory_excerpt"], "")
        # Excerpt should be at most 40 lines.
        lines = r["memory_excerpt"].splitlines()
        self.assertLessEqual(len(lines), 40)

    def test_memory_absent(self):
        r = preflight_context(self.td)
        self.assertFalse(r["memory_present"])
        self.assertEqual(r["memory_excerpt"], "")

    def test_result_has_all_expected_keys(self):
        r = preflight_context(self.td)
        expected_keys = {
            "constitution_present", "constitution_populated",
            "source_root", "project_type", "framework", "language",
            "claude_md_present", "memory_present", "memory_excerpt",
        }
        self.assertEqual(set(r.keys()), expected_keys)

    def test_nonexistent_workspace_no_raise(self):
        # Should not raise — all files absent → all defaults.
        r = preflight_context(os.path.join(self.td, "does_not_exist"))
        self.assertFalse(r["constitution_present"])
        self.assertFalse(r["memory_present"])


if __name__ == "__main__":
    unittest.main()
