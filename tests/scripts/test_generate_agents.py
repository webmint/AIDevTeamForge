"""Tests for scripts/generate-agents.py.

Covers the `tools:` frontmatter field propagation from agent source meta to
emitted Claude `.claude/agents/<name>.md`. Per Claude Code subagent docs
(`docs.claude.com/en/docs/claude-code/sub-agents`, verified 2026-05-01), the
`tools:` field constrains which tools the subagent can invoke; omitted →
inherits all tools.

Also covers the model surface (94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md
Phase 1, Deliverables 3-4): every emitted agent carries an explicit
`model: inherit` line, `VALID_TIERS` is `think | do | verify | security`
(`scan` retired, `security` added), and the removed `model_pin` field is
tolerated on a source that still declares it (a transition-only stderr
warning, never a failure).

Tests 1-4 use inline source fixtures + `tmp_path` to keep them hermetic.
The real-roster tests read real `src/agents/*.md` files to catch
accidental drift on existing agents.

The emitter does NOT canonicalize the `tools` value — Claude Code's parser
handles both comma-separated (`Read, Bash`) and YAML-list (`[Read, Bash]`)
forms; coupling here would rot.

Stdlib only.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
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
    `importlib.util.spec_from_file_location`. `generate-agents.py` no
    longer imports anything from `scripts/lib/` at all (plan 94 D2
    deleted its one such import, the sibling default-map module), so no
    sys.path shadowing dance is needed here any more — a plain by-path
    load suffices.
    """
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
# TierValidationTests — `scan` retired, `security` added (plan 94 D2 part 4,
# D3). `VALID_TIERS` is now think | do | verify | security.
# ---------------------------------------------------------------------------


class TierValidationTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    # scan is retired (plan 94 D2 part 4) — a source still declaring it
    # must fail, naming all four surviving valid tiers.
    def test_scan_tier_is_rejected_naming_the_four_valid_tiers(self):
        src = (
            "```yaml\n"
            "name: agent-retired-tier\n"
            'description: "An agent still declaring the retired scan tier."\n'
            "model_tier: scan\n"
            "```\n"
            "\n"
            "Body content.\n"
        )
        _write_source(self.tmp_path, "agent-retired-tier", src)
        src_file = self.tmp_path / "src" / "agents" / "agent-retired-tier.md"
        with self.assertRaises(ValueError) as ctx:
            generate_agents._render_one(src_file, self.tmp_path)
        message = str(ctx.exception)
        for tier in ("think", "do", "verify", "security"):
            self.assertIn(
                tier, message,
                f"valid tier {tier!r} missing from error message: {message!r}",
            )

    # security is the new fourth tier (plan 94 D3) — accepted and rendered
    # like any other tier.
    def test_security_tier_is_accepted(self):
        src = (
            "```yaml\n"
            "name: agent-security-tier\n"
            'description: "An agent on the security tier."\n'
            "model_tier: security\n"
            "```\n"
            "\n"
            "Body content.\n"
        )
        _write_source(self.tmp_path, "agent-security-tier", src)
        generate_agents._render_one(
            self.tmp_path / "src" / "agents" / "agent-security-tier.md",
            self.tmp_path,
        )
        rendered = _read_emitted(self.tmp_path, "agent-security-tier")
        fm = _frontmatter_block(rendered)
        lines = fm.splitlines()
        self.assertIn("model: inherit", lines)
        self.assertIn("model_tier: security", lines)


# ---------------------------------------------------------------------------
# ExistingAgentRegressionTests — change 5 of the task spec.
#
# Real shipped agents must continue to render with EXACTLY name / description /
# model / model_tier in the frontmatter (no spurious `tools:` line), and
# `model:` must be the literal `inherit` (plan 94 D2). This catches
# accidental injection if the emitter starts adding `tools:` for agents
# that don't define it, or drifts off `inherit`.
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
        lines = fm.splitlines()
        keys = []
        for line in lines:
            if ":" in line and not line.startswith(" "):
                keys.append(line.split(":", 1)[0])
        # Expected keys: name + description + model + model_tier (every
        # agent carries both now — plan 94 D2) + applies_to (added
        # 2026-05-10 for configure_helper prune-agents). The regression guard is
        # on the ABSENCE of `tools` (canary's whole point) — not on the exact key
        # set, which legitimately grows as new emit-time fields ship.
        self.assertNotIn(
            "tools", keys,
            f"tools: line spuriously injected into tech-writer frontmatter: {keys!r}",
        )
        # Required-keys subset check: name + description + model + model_tier
        # must always appear.
        for required in ("name", "description", "model", "model_tier"):
            self.assertIn(required, keys, f"required key {required!r} missing: {keys!r}")
        # And `model:` must be the literal `inherit` — no framework default
        # (plan 94 D2, OQ-5).
        self.assertIn(
            "model: inherit", lines,
            f"expected 'model: inherit' in tech-writer frontmatter: {lines!r}",
        )


# ---------------------------------------------------------------------------
# ModelTierFrontmatterTests — plan 94 D2: `model: inherit` immediately
# followed by `model_tier:` for every valid tier.
# ---------------------------------------------------------------------------


class ModelTierFrontmatterTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_model_tier_line_immediately_follows_model_inherit_for_each_tier(self):
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
                self.assertIn("model: inherit", lines)
                model_idx = lines.index("model: inherit")
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
        lines = fm.splitlines()
        keys = [line.split(":", 1)[0] for line in lines]
        self.assertEqual(
            keys,
            ["name", "description", "tools", "model", "model_tier", "applies_to"],
        )
        self.assertIn("model: inherit", lines)


# ---------------------------------------------------------------------------
# ModelPinTransitionTests — plan 94 D3: `model_pin` support removed from
# the emitter. A source that still declares the removed `model_pin` key
# (none in the shipped roster since plan 94 Phase 2, 2026-09-04) is
# emitted normally — `model: inherit` plus `model_tier:` — and the
# emitter prints ONE stderr warning naming the file and the key.
# ---------------------------------------------------------------------------


class ModelPinTransitionTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_model_pin_present_emits_one_stderr_warning_naming_file_and_key(self):
        src = (
            "```yaml\n"
            "name: agent-still-pinned\n"
            'description: "An agent still declaring the removed model_pin key."\n'
            "model_tier: do\n"
            "model_pin: opus\n"
            "```\n"
            "\n"
            "Body content.\n"
        )
        src_file = _write_source(self.tmp_path, "agent-still-pinned", src)
        captured = io.StringIO()
        with contextlib.redirect_stderr(captured):
            generate_agents._render_one(src_file, self.tmp_path)
        stderr_text = captured.getvalue()
        self.assertEqual(
            len(stderr_text.strip().splitlines()), 1,
            f"expected exactly one warning line on stderr, got: {stderr_text!r}",
        )
        self.assertIn(str(src_file), stderr_text)
        self.assertIn("model_pin", stderr_text)

    def test_model_pin_present_renders_identical_output_to_a_source_without_it(self):
        common = (
            "name: agent-pin-comparison\n"
            'description: "Comparison agent for the model_pin transition."\n'
            "model_tier: verify\n"
        )
        pinned_src = "```yaml\n" + common + "model_pin: opus\n```\n\nBody content.\n"
        unpinned_src = "```yaml\n" + common + "```\n\nBody content.\n"

        pinned_root = self.tmp_path / "pinned"
        unpinned_root = self.tmp_path / "unpinned"
        pinned_root.mkdir()
        unpinned_root.mkdir()
        pinned_file = _write_source(pinned_root, "agent-pin-comparison", pinned_src)
        unpinned_file = _write_source(unpinned_root, "agent-pin-comparison", unpinned_src)

        with contextlib.redirect_stderr(io.StringIO()):
            generate_agents._render_one(pinned_file, pinned_root)
            generate_agents._render_one(unpinned_file, unpinned_root)

        pinned_rendered = _read_emitted(pinned_root, "agent-pin-comparison")
        unpinned_rendered = _read_emitted(unpinned_root, "agent-pin-comparison")
        self.assertEqual(pinned_rendered, unpinned_rendered)


# ---------------------------------------------------------------------------
# RealAgentRosterModelTests — every shipped src/agents/*.md source renders
# `model: inherit` plus a `model_tier:` line, and nothing else on the
# `model:` line (plan 94 D2, D3). A source that still declares the removed
# `model_pin` key (none in the shipped roster since plan 94 Phase 2,
# 2026-09-04) is emitted normally with one stderr warning — the render
# below asserts NO warning fires, since none of today's sources declare it.
# ---------------------------------------------------------------------------


class RealAgentRosterModelTests(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_every_shipped_agent_emits_inherit_and_a_model_tier_line(self):
        sources = sorted(_AGENTS_SRC.glob("*.md"))
        self.assertTrue(sources, f"no agent sources found under {_AGENTS_SRC}")

        for src_file in sources:
            with self.subTest(agent=src_file.stem):
                captured = io.StringIO()
                with contextlib.redirect_stderr(captured):
                    out_path = generate_agents._render_one(src_file, self.tmp_path)
                self.assertEqual(
                    captured.getvalue(), "",
                    f"{src_file.name}: unexpected stderr output — no source "
                    f"in the shipped roster declares the removed model_pin "
                    f"key any more (plan 94 Phase 2, 2026-09-04), so no "
                    f"warning should fire: {captured.getvalue()!r}",
                )
                rendered = Path(out_path).read_text(encoding="utf-8")
                fm = _frontmatter_block(rendered)
                lines = fm.splitlines()

                model_lines = [line for line in lines if line.startswith("model:")]
                self.assertEqual(
                    model_lines, ["model: inherit"],
                    f"{src_file.name}: expected exactly one 'model: inherit' "
                    f"line, got {model_lines!r}",
                )
                self.assertTrue(
                    any(line.startswith("model_tier: ") for line in lines),
                    f"{src_file.name}: no model_tier: line in emitted "
                    f"frontmatter: {lines!r}",
                )

    def test_security_reviewer_frontmatter_order_is_the_standard_shape(self):
        # A source that still declares the removed `model_pin` key (none
        # in the shipped roster since plan 94 Phase 2, 2026-09-04, incl.
        # security-reviewer.md itself) is emitted normally with one
        # stderr warning and must not perturb the standard field order —
        # confirmed here with no warning firing at all, since this source
        # no longer declares the key.
        src_file = _AGENTS_SRC / "security-reviewer.md"
        self.assertTrue(src_file.exists(), f"missing source: {src_file}")
        captured = io.StringIO()
        with contextlib.redirect_stderr(captured):
            out_path = generate_agents._render_one(src_file, self.tmp_path)
        self.assertEqual(
            captured.getvalue(), "",
            f"security-reviewer.md no longer declares model_pin (plan 94 "
            f"Phase 2, 2026-09-04) so no warning should fire: "
            f"{captured.getvalue()!r}",
        )
        rendered = Path(out_path).read_text(encoding="utf-8")
        fm = _frontmatter_block(rendered)
        keys = [line.split(":", 1)[0] for line in fm.splitlines()]
        self.assertEqual(
            keys,
            ["name", "description", "tools", "model", "model_tier", "applies_to"],
        )


if __name__ == "__main__":
    unittest.main()
