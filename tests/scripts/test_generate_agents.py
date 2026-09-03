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
# ScanTierTests — scan → haiku tier mapping.
# ---------------------------------------------------------------------------


class ScanTierTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # scan tier emits `model: haiku` in frontmatter
    def test_scan_tier_emits_haiku_model(self):
        src = (
            "```yaml\n"
            "name: tree-annotator\n"
            'description: "Cheap per-tree-entry annotation calls for generate-docs Phase 3."\n'
            "model_tier: scan\n"
            "```\n"
            "\n"
            "Body content for scan-tier agent.\n"
        )
        _write_source(self.tmp_path, "tree-annotator", src)
        generate_agents._render_one(
            self.tmp_path / "src" / "agents" / "tree-annotator.md",
            self.tmp_path,
        )
        rendered = _read_emitted(self.tmp_path, "tree-annotator")
        fm = _frontmatter_block(rendered)
        self.assertIn("model: haiku", fm)


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
        # this test was written — pick it as the canary against accidental
        # `tools:` line injection. If a future change adds `tools:` to
        # tech-writer.md's source, update this test (the canary moves to
        # whichever existing agent still has no tools).
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
        # Expected keys: name + description + model + model_tier (plan 92 D1 —
        # every non-pinned agent now carries model_tier) + applies_to (added
        # 2026-05-10 for configure_helper prune-agents). The regression guard is
        # on the ABSENCE of `tools` (canary's whole point) — not on the exact key
        # set, which legitimately grows as new emit-time fields ship.
        self.assertNotIn(
            "tools", keys,
            f"tools: line spuriously injected into tech-writer frontmatter: {keys!r}",
        )
        # Required-keys subset check: name + description + model + model_tier
        # must always appear (tech-writer declares no model_pin); applies_to
        # may or may not (depends on whether source has it).
        for required in ("name", "description", "model", "model_tier"):
            self.assertIn(required, keys, f"required key {required!r} missing: {keys!r}")


# ---------------------------------------------------------------------------
# ModelTierFrontmatterTests — plan 92 Deliverable 4: `model_tier:` line
# emitted immediately after `model:`, for every tier.
# ---------------------------------------------------------------------------


class ModelTierFrontmatterTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_model_tier_line_immediately_follows_model_line_for_each_tier(self):
        for tier in sorted(generate_agents.VALID_TIERS):
            with self.subTest(tier=tier):
                name = f"agent-tier-{tier}"
                src = (
                    "```yaml\n"
                    f"name: {name}\n"
                    'description: "An agent for tier frontmatter testing."\n'
                    f"model_tier: {tier}\n"
                    "```\n"
                    "\n"
                    "Body content.\n"
                )
                _write_source(self.tmp_path, name, src)
                generate_agents._render_one(
                    self.tmp_path / "src" / "agents" / f"{name}.md",
                    self.tmp_path,
                )
                rendered = _read_emitted(self.tmp_path, name)
                fm = _frontmatter_block(rendered)
                lines = fm.splitlines()
                expected_default = generate_agents.CLAUDE_AGENT_DEFAULTS_BY_TIER[tier]
                self.assertIn(f"model: {expected_default}", lines)
                model_idx = lines.index(f"model: {expected_default}")
                self.assertEqual(
                    lines[model_idx + 1],
                    f"model_tier: {tier}",
                    f"model_tier line did not immediately follow model line: {lines!r}",
                )


# ---------------------------------------------------------------------------
# FrontmatterOrderTests — full key order pinned (plan 92 D1, Step 0 answer 2).
# ---------------------------------------------------------------------------


class FrontmatterOrderTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_full_frontmatter_order_with_tools_and_applies_to(self):
        src = (
            "```yaml\n"
            "name: agent-full-order\n"
            'description: "An agent exercising every optional frontmatter field."\n'
            "model_tier: verify\n"
            "tools: Read, Grep\n"
            'applies_to: ["web"]\n'
            "```\n"
            "\n"
            "Body content.\n"
        )
        _write_source(self.tmp_path, "agent-full-order", src)
        generate_agents._render_one(
            self.tmp_path / "src" / "agents" / "agent-full-order.md",
            self.tmp_path,
        )
        rendered = _read_emitted(self.tmp_path, "agent-full-order")
        fm = _frontmatter_block(rendered)
        keys = [line.split(":", 1)[0] for line in fm.splitlines()]
        self.assertEqual(
            keys,
            ["name", "description", "tools", "model", "model_tier", "applies_to"],
        )


# ---------------------------------------------------------------------------
# ModelPinTests — plan 92 D6: `model_pin` overrides `model:` and omits
# `model_tier:` (which is what makes `apply-agent-models` skip the file).
# ---------------------------------------------------------------------------


class ModelPinTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_model_pin_overrides_model_and_omits_model_tier(self):
        src = (
            "```yaml\n"
            "name: agent-pinned\n"
            'description: "An agent pinned to a specific model."\n'
            "model_tier: think\n"
            "model_pin: opus\n"
            "tools: Read\n"
            'applies_to: ["all"]\n'
            "```\n"
            "\n"
            "Body content.\n"
        )
        _write_source(self.tmp_path, "agent-pinned", src)
        generate_agents._render_one(
            self.tmp_path / "src" / "agents" / "agent-pinned.md",
            self.tmp_path,
        )
        rendered = _read_emitted(self.tmp_path, "agent-pinned")
        fm = _frontmatter_block(rendered)
        lines = fm.splitlines()
        # Order otherwise unchanged: tools before model, applies_to after —
        # only the model_tier slot is skipped.
        keys = [line.split(":", 1)[0] for line in lines]
        self.assertEqual(keys, ["name", "description", "tools", "model", "applies_to"])
        self.assertIn("model: opus", lines)
        for line in lines:
            self.assertFalse(
                line.startswith("model_tier:"),
                f"unexpected model_tier line with model_pin set: {line!r}",
            )

    def test_model_pin_still_requires_valid_model_tier(self):
        # model_pin present and valid, but model_tier absent entirely — the
        # authoring contract keeps model_tier required (plan 92 D6): a pinned
        # agent still belongs to a tier for documentation.
        src = (
            "```yaml\n"
            "name: agent-pin-no-tier\n"
            'description: "An agent with a valid pin but no tier."\n'
            "model_pin: opus\n"
            "```\n"
            "\n"
            "Body content.\n"
        )
        _write_source(self.tmp_path, "agent-pin-no-tier", src)
        with self.assertRaises(ValueError) as ctx:
            generate_agents._render_one(
                self.tmp_path / "src" / "agents" / "agent-pin-no-tier.md",
                self.tmp_path,
            )
        self.assertIn("model_tier", str(ctx.exception))

    def test_invalid_model_pin_values_raise_naming_the_file(self):
        invalid_values = {
            "uppercase": "Opus",
            "embedded-space": "claude opus",
            "empty": "",
            "leading-hyphen": "-x",
            # A pin is an ALIAS by contract (plan 92 D6) — no digits, ever.
            # These two are exactly the hyphen-joined and bare-digit
            # pseudo-version shapes python-reviewer flagged as slipping
            # both the tripwire patterns AND the pre-tightening regex.
            "hyphen-joined-pseudo-version": "sonnet-4-5",
            "trailing-digit": "opus5",
        }
        for label, pin_value in invalid_values.items():
            with self.subTest(label=label, pin_value=pin_value):
                name = f"agent-bad-pin-{label}"
                src = (
                    "```yaml\n"
                    f"name: {name}\n"
                    'description: "An agent with an invalid model_pin."\n'
                    "model_tier: do\n"
                    f"model_pin: {pin_value}\n"
                    "```\n"
                    "\n"
                    "Body content.\n"
                )
                _write_source(self.tmp_path, name, src)
                src_file = self.tmp_path / "src" / "agents" / f"{name}.md"
                with self.assertRaises(ValueError) as ctx:
                    generate_agents._render_one(src_file, self.tmp_path)
                message = str(ctx.exception)
                self.assertIn(str(src_file), message)
                self.assertIn("model_pin", message)


# ---------------------------------------------------------------------------
# RealAgentRosterModelTierTests — every shipped src/agents/*.md source
# renders with a model_tier: line, and none pins today (so the day one does,
# this test names it rather than silently passing).
# ---------------------------------------------------------------------------


class RealAgentRosterModelTierTests(unittest.TestCase):
    """Live-roster coverage of the model_tier: / model_pin: split (plan 92 D6).

    As of Phase 2, exactly ONE source in src/agents/ declares model_pin —
    security-reviewer, pinned to opus. This is the set this test's failure
    message names; the day a second agent gains model_pin, that message is
    what a reader needs to update it correctly.
    """

    # The live-roster pin set. Update this alongside the corresponding
    # source file(s) — this is the single place a second pin's expected
    # value belongs.
    _PINNED_AGENTS = {"security-reviewer": "opus"}

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_every_shipped_agent_emits_model_tier_except_the_declared_pins(self):
        sources = sorted(_AGENTS_SRC.glob("*.md"))
        self.assertTrue(sources, f"no agent sources found under {_AGENTS_SRC}")

        # Sanity-check the pin set itself first: every name in
        # _PINNED_AGENTS must actually declare model_pin in its source,
        # with the expected value — a stale entry here would silently
        # under-test the split below.
        declared_pins = {}
        for src_file in sources:
            text = src_file.read_text(encoding="utf-8")
            meta, _ = generate_agents._parse_source(text)
            if "model_pin" in meta:
                declared_pins[src_file.stem] = meta["model_pin"].strip()
        self.assertEqual(
            declared_pins, self._PINNED_AGENTS,
            "the live model_pin roster no longer matches _PINNED_AGENTS — "
            f"found {declared_pins!r}, expected {self._PINNED_AGENTS!r}. "
            "Update _PINNED_AGENTS (and this test's per-agent assertions "
            "below) to match the live source(s).",
        )

        for src_file in sources:
            with self.subTest(agent=src_file.stem):
                out_path = generate_agents._render_one(src_file, self.tmp_path)
                rendered = Path(out_path).read_text(encoding="utf-8")
                fm = _frontmatter_block(rendered)
                lines = fm.splitlines()

                if src_file.stem in self._PINNED_AGENTS:
                    expected_model = self._PINNED_AGENTS[src_file.stem]
                    self.assertIn(
                        f"model: {expected_model}", lines,
                        f"{src_file.name}: pinned agent missing its expected "
                        f"model: {expected_model!r} line: {lines!r}",
                    )
                    self.assertFalse(
                        any(line.startswith("model_tier:") for line in lines),
                        f"{src_file.name}: pinned agent (in "
                        f"{sorted(self._PINNED_AGENTS)!r}) still carries a "
                        f"model_tier: line, which apply-agent-models would "
                        f"key on and rewrite past the pin: {lines!r}",
                    )
                else:
                    self.assertTrue(
                        any(line.startswith("model_tier: ") for line in lines),
                        f"{src_file.name}: no model_tier: line in emitted "
                        f"frontmatter (not one of the declared pins "
                        f"{sorted(self._PINNED_AGENTS)!r}): {lines!r}",
                    )

    def test_security_reviewer_frontmatter_order_unchanged_around_the_pin(self):
        # The pin only removes the model_tier slot — tools before model,
        # applies_to after, exactly as an unpinned agent with the same
        # optional fields would render.
        src_file = _AGENTS_SRC / "security-reviewer.md"
        self.assertTrue(src_file.exists(), f"missing pinned source: {src_file}")
        out_path = generate_agents._render_one(src_file, self.tmp_path)
        rendered = Path(out_path).read_text(encoding="utf-8")
        fm = _frontmatter_block(rendered)
        keys = [line.split(":", 1)[0] for line in fm.splitlines()]
        self.assertEqual(keys, ["name", "description", "tools", "model", "applies_to"])


if __name__ == "__main__":
    unittest.main()
