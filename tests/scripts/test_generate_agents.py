"""Tests for scripts/generate-agents.py.

Covers the `tools:` frontmatter field propagation from agent source meta to
emitted Claude `.claude/agents/<name>.md`. Per Claude Code subagent docs
(`docs.claude.com/en/docs/claude-code/sub-agents`, verified 2026-05-01), the
`tools:` field constrains which tools the subagent can invoke; omitted →
inherits all tools.

Tests 1-4 use inline source fixtures + `tmp_path` to keep them hermetic.
Test 5 (regression) reads a real `src/agents/*.md` file to catch accidental
tools-field injection on existing agents that don't specify `tools`.

The emitter does NOT canonicalize the `tools` value — Claude Code's parser
handles both comma-separated (`Read, Bash`) and YAML-list (`[Read, Bash]`)
forms; coupling here would rot.

Stdlib only.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
_GENERATE_AGENTS_PY = _SCRIPTS_DIR / "generate-agents.py"
_AGENTS_SRC = _REPO_ROOT / "src" / "agents"


def _load_generate_agents():
    """Load `scripts/generate-agents.py` as a module despite the hyphen.

    The hyphen blocks `import generate-agents`, so we go through
    `importlib.util.spec_from_file_location`.

    Subtlety: `generate-agents.py` does `from lib.install_defaults import ...`
    at import time. Under `unittest discover -s tests`, `tests/lib/` (an
    empty namespace package used by the lib-helper tests) is on sys.path
    first and SHADOWS `scripts/lib/`, so the bare `lib.install_defaults`
    import fails. We pre-load the real `lib.install_defaults` by absolute
    path and inject it into `sys.modules` so the bare-name import in
    `generate-agents.py` hits the cache instead of resolving via sys.path.
    """
    install_defaults_path = _SCRIPTS_DIR / "lib" / "install_defaults.py"
    if "lib.install_defaults" not in sys.modules:
        # Make sure parent `lib` exists in sys.modules first — Python
        # requires the parent package to be present before a submodule
        # entry is honored.
        if "lib" not in sys.modules:
            lib_spec = importlib.util.spec_from_file_location(
                "lib", _SCRIPTS_DIR / "lib" / "__init__.py",
                submodule_search_locations=[str(_SCRIPTS_DIR / "lib")],
            ) if (_SCRIPTS_DIR / "lib" / "__init__.py").exists() else None
            if lib_spec is None:
                # No __init__.py — synthesize a minimal package object.
                import types
                lib_pkg = types.ModuleType("lib")
                lib_pkg.__path__ = [str(_SCRIPTS_DIR / "lib")]
                sys.modules["lib"] = lib_pkg
            else:
                lib_pkg = importlib.util.module_from_spec(lib_spec)
                sys.modules["lib"] = lib_pkg
                lib_spec.loader.exec_module(lib_pkg)

        id_spec = importlib.util.spec_from_file_location(
            "lib.install_defaults", install_defaults_path
        )
        id_mod = importlib.util.module_from_spec(id_spec)
        sys.modules["lib.install_defaults"] = id_mod
        id_spec.loader.exec_module(id_mod)

    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(
        "generate_agents", _GENERATE_AGENTS_PY
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


generate_agents = _load_generate_agents()


def _write_source(tmp_path: Path, name: str, body_lines: str) -> Path:
    """Write a source file under `<tmp_path>/src/agents/<name>.md` and return it.

    `body_lines` is the full meta block + body (caller controls the meta
    contents to exercise the field-propagation paths).
    """
    src_dir = tmp_path / "src" / "agents"
    src_dir.mkdir(parents=True, exist_ok=True)
    src = src_dir / f"{name}.md"
    src.write_text(body_lines, encoding="utf-8")
    return src


def _read_emitted(tmp_path: Path, name: str) -> str:
    return (tmp_path / ".claude" / "agents" / f"{name}.md").read_text(encoding="utf-8")


def _frontmatter_block(rendered: str) -> str:
    """Return the `---`-delimited frontmatter block (without the fences)."""
    lines = rendered.splitlines()
    assert lines[0] == "---", f"expected '---' at line 0, got {lines[0]!r}"
    end = None
    for i in range(1, len(lines)):
        if lines[i] == "---":
            end = i
            break
    assert end is not None, "frontmatter not closed with '---'"
    return "\n".join(lines[1:end])


# ---------------------------------------------------------------------------
# ToolsPropagationTests — changes 1 & 2 of the task spec.
# ---------------------------------------------------------------------------


class ToolsPropagationTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # 1 ─ tools field propagated when present
    def test_tools_field_propagated_when_present(self):
        src = (
            "```yaml\n"
            "name: agent-with-tools\n"
            'description: "An agent that should have a tools allowlist."\n'
            "model_tier: do\n"
            "tools: Read, Bash\n"
            "```\n"
            "\n"
            "Body content.\n"
        )
        _write_source(self.tmp_path, "agent-with-tools", src)
        # _render_one expects target dir to exist
        self.tmp_path.mkdir(parents=True, exist_ok=True)
        generate_agents._render_one(
            self.tmp_path / "src" / "agents" / "agent-with-tools.md",
            self.tmp_path,
        )
        rendered = _read_emitted(self.tmp_path, "agent-with-tools")
        fm = _frontmatter_block(rendered)
        self.assertIn("tools: Read, Bash", fm)

    # 2 ─ tools field omitted when absent (regression — byte-identical to today)
    def test_tools_field_omitted_when_absent(self):
        src = (
            "```yaml\n"
            "name: agent-no-tools\n"
            'description: "An agent that does not specify tools."\n'
            "model_tier: do\n"
            "```\n"
            "\n"
            "Body content.\n"
        )
        _write_source(self.tmp_path, "agent-no-tools", src)
        generate_agents._render_one(
            self.tmp_path / "src" / "agents" / "agent-no-tools.md",
            self.tmp_path,
        )
        rendered = _read_emitted(self.tmp_path, "agent-no-tools")
        fm = _frontmatter_block(rendered)
        # No `tools:` line of any kind — the entire field must be absent.
        for line in fm.splitlines():
            self.assertFalse(
                line.startswith("tools:"),
                f"unexpected tools line in frontmatter: {line!r}",
            )

    # 3 ─ tools field omitted when key present but value empty
    def test_tools_field_omitted_when_empty_string(self):
        src = (
            "```yaml\n"
            "name: agent-empty-tools\n"
            'description: "An agent with empty tools field."\n'
            "model_tier: do\n"
            "tools: \n"
            "```\n"
            "\n"
            "Body content.\n"
        )
        _write_source(self.tmp_path, "agent-empty-tools", src)
        generate_agents._render_one(
            self.tmp_path / "src" / "agents" / "agent-empty-tools.md",
            self.tmp_path,
        )
        rendered = _read_emitted(self.tmp_path, "agent-empty-tools")
        fm = _frontmatter_block(rendered)
        for line in fm.splitlines():
            self.assertFalse(
                line.startswith("tools:"),
                f"unexpected tools line in frontmatter: {line!r}",
            )

    # 4 ─ tools value preserved verbatim (no canonicalization)
    def test_tools_field_preserves_verbatim_value(self):
        src = (
            "```yaml\n"
            "name: agent-yaml-list\n"
            'description: "An agent using YAML list form for tools."\n'
            "model_tier: do\n"
            "tools: [Read, Bash, Grep]\n"
            "```\n"
            "\n"
            "Body content.\n"
        )
        _write_source(self.tmp_path, "agent-yaml-list", src)
        generate_agents._render_one(
            self.tmp_path / "src" / "agents" / "agent-yaml-list.md",
            self.tmp_path,
        )
        rendered = _read_emitted(self.tmp_path, "agent-yaml-list")
        fm = _frontmatter_block(rendered)
        self.assertIn("tools: [Read, Bash, Grep]", fm)


# ---------------------------------------------------------------------------
# ExistingAgentRegressionTests — change 5 of the task spec.
#
# Real shipped agents must continue to render with EXACTLY name / description /
# model in the frontmatter (no spurious `tools:` line). This catches accidental
# injection if the emitter starts adding `tools:` for agents that don't define it.
# ---------------------------------------------------------------------------


class ExistingAgentRegressionTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_existing_agents_render_unchanged(self):
        # tech-writer has no `tools` line in its source meta as of the time
        # this test was written — pick it as the canary. If a future change
        # adds `tools:` to tech-writer.md's source, update this test (the
        # canary moves to whichever existing agent still has no tools).
        src_file = _AGENTS_SRC / "tech-writer.md"
        self.assertTrue(src_file.exists(), f"missing canary source: {src_file}")
        # Sanity-check the canary: its source meta must NOT have a tools line.
        text = src_file.read_text(encoding="utf-8")
        meta, _ = generate_agents._parse_source(text)
        self.assertNotIn(
            "tools", meta,
            "canary tech-writer.md now has tools in its source meta — "
            "this regression test needs a different canary that still has none.",
        )

        generate_agents._render_one(src_file, self.tmp_path)
        rendered = _read_emitted(self.tmp_path, "tech-writer")
        fm = _frontmatter_block(rendered)
        keys = []
        for line in fm.splitlines():
            if ":" in line and not line.startswith(" "):
                keys.append(line.split(":", 1)[0])
        self.assertEqual(
            keys, ["name", "description", "model"],
            f"tech-writer frontmatter keys drifted: got {keys!r}",
        )


if __name__ == "__main__":
    unittest.main()
