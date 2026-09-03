#!/usr/bin/env python3
"""Agent generator for AIDevTeamForge.

Reads src/agents/*.md as a universal authoring source and produces
.claude/agents/*.md files. Each source is treated as SEMANTIC DATA — the
output is constructed from scratch, not passed through unchanged.

Source format: a fenced yaml meta block at the top of the file, then the
body as markdown prose. The fenced block is deliberately distinct from
Claude's '---'-delimited native agent frontmatter — the source is not a
Claude file but authoring data.

    ```yaml
    name: architect
    description: "..."
    model_tier: think
    ```

    <body>

Fields in the meta block:
  - name         : agent identifier (required)
  - description  : when-to-use hint (required)
  - model_tier   : think | do | verify | scan (required; semantic, not a runtime placeholder;
                    also emitted verbatim as a `model_tier:` frontmatter line — see below)
  - model_pin    : optional; a lowercase alias (matching `^[a-z][a-z-]*$` — no
                    digits; a pin names an alias, never a version) pinned for this agent
                    regardless of its tier. When
                    present, the emitter writes `model: <pin>` and OMITS the `model_tier:`
                    line entirely. `model_tier` is still required in the source even when
                    `model_pin` is set (plan 92 D6) — a pinned agent still belongs to a tier
                    for documentation, it just isn't keyed on for the apply mechanism
                    below.

Model tier is translated into Claude boot-safe defaults (NOT placeholders)
so Claude Code can parse these files at launch without error:
  opus | sonnet | sonnet | haiku (per tier)

Defaults live in `scripts/lib/install_defaults.py`. The emitted `model_tier:`
frontmatter line is what the consumer-side `configure_helper
apply-agent-models` verb (plan 92 D1, built as Phase 1 Deliverable 3 of
that plan) keys on: at `/devforge:configure` Phase 5 and on `update.sh`,
that verb rewrites `model:` and `effort:` on every `.claude/agents/*.md`
from `.devforge/project-config.json`. A file with no `model_tier:` line —
an agent pinned via `model_pin`, or a consumer's own hand-written agent —
is left untouched by that verb.

{{UPPERCASE}} placeholders in body prose pass through untouched — wizard
substitutes them post-install with project-specific answers (FRAMEWORK,
LANGUAGE, ARCHITECTURE, etc.). Those are inside string fields, not structural,
so Claude parses them fine as literal text.

Usage:
  python3 scripts/generate-agents.py --src src/agents --target /path/to/project
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.install_defaults import CLAUDE_AGENT_DEFAULTS_BY_TIER  # noqa: E402

# We intentionally don't use lib.frontmatter here — agent sources use a
# ```yaml fenced meta block, not ---/--- frontmatter, to avoid mimicking
# Claude's native agent file format. See _parse_source() below.


VALID_TIERS = {"think", "do", "verify", "scan"}

TARGET_SUBDIR = ".claude/agents"

# `model_pin` (plan 92 D6): a lowercase ALIAS shape, no digits — a pin
# names an alias by contract (D6), never a version. Excluding digits here
# means a hyphen-joined pseudo-version like `sonnet-4-5` is rejected at
# emit time with a ValueError, rather than merely relying on the separate
# maintainer-side version-string tripwire (scripts/lib/model_version_
# tripwire.py) to catch it after the fact. The emitter does NOT enforce
# Claude Code's actual alias set here — that's version-freedom, not this
# emitter's job.
_MODEL_PIN_RE = re.compile(r"^[a-z][a-z-]*$")


# ── Source parser ────────────────────────────────────────────────────────

def _parse_source(text: str) -> tuple[dict[str, str], str]:
    """Split an agent source file into (metadata_dict, body).

    Source format:

        ```yaml
        name: foo
        description: "..."
        model_tier: think
        ```

        <body>

    The fenced block must start on line 1 with exactly '```yaml'. Inner
    lines use the same subset of YAML as scripts/lib/frontmatter.py:
    'key: value' with optional double- or single-quoted values.
    """
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\n") != "```yaml":
        raise ValueError("source must begin with '```yaml' fenced block")

    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].rstrip("\n") == "```":
            close_idx = i
            break
    if close_idx is None:
        raise ValueError("source's '```yaml' block is not closed with '```'")

    body = "".join(lines[close_idx + 1:]).lstrip("\n")

    meta: dict[str, str] = {}
    for line in lines[1:close_idx]:
        line = line.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == '"':
            value = _unescape_yaml_double(value[1:-1])
        elif len(value) >= 2 and value[0] == value[-1] == "'":
            value = value[1:-1]
        meta[key] = value
    return meta, body


def _unescape_yaml_double(s: str) -> str:
    """Interpret YAML double-quoted escapes we actually use: \\n \\t \\r \\\\ \\" \\'."""
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s):
            nxt = s[i + 1]
            if nxt == "n": out.append("\n")
            elif nxt == "t": out.append("\t")
            elif nxt == "r": out.append("\r")
            elif nxt == '"': out.append('"')
            elif nxt == "'": out.append("'")
            elif nxt == "\\": out.append("\\")
            else: out.append(s[i:i+2])
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


# ── Escape helpers ───────────────────────────────────────────────────────

def _yaml_escape_double(s: str) -> str:
    """Escape a string for a YAML double-quoted scalar."""
    out = []
    for ch in s:
        if ch == "\\":
            out.append("\\\\")
        elif ch == '"':
            out.append('\\"')
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\r":
            out.append("\\r")
        elif ch == "\t":
            out.append("\\t")
        else:
            out.append(ch)
    return "".join(out)


# ── Emitter ──────────────────────────────────────────────────────────────
#
# Emit boot-safe defaults (not placeholder tokens). Values come from
# `scripts/lib/install_defaults.py` — the single source of truth. The
# emitted `model_tier:` line is what the consumer-side `configure_helper
# apply-agent-models` verb (plan 92 D1, built as Phase 1 Deliverable 3 of
# that plan) keys on to rewrite `model:`/`effort:` post-install; see the
# module docstring above.


def _claude_tier_model(tier: str) -> str:
    return CLAUDE_AGENT_DEFAULTS_BY_TIER[tier]


def emit_claude(
    name: str,
    description: str,
    model_tier: str,
    body: str,
    tools: str = "",
    applies_to: str = "",
    model_pin: str = "",
) -> str:
    """Build a Claude-native agent file from scratch (YAML + markdown).

    `tools` is the optional Claude Code subagent tool allowlist. When non-empty
    after `.strip()`, it is emitted verbatim as a `tools: <value>` frontmatter
    line; when empty/absent, the line is omitted entirely so agents that don't
    specify `tools` render byte-identical to pre-allowlist behavior. The value
    is propagated as-is — Claude Code's own parser handles both comma-separated
    (`Read, Bash`) and YAML-list (`[Read, Bash]`) forms; this emitter does NOT
    canonicalize. Coupling to Claude's tool enumeration would rot.

    `applies_to` is the project-natures allowlist consumed by configure_helper
    prune-agents. When non-empty, emitted verbatim as an `applies_to: <value>`
    frontmatter line — Claude Code ignores unknown keys; configure_helper
    parses it. Empty/absent omits the line.

    `model_pin` (plan 92 D6) is an optional per-agent pin that overrides the
    tier default regardless of `model_tier`. When non-empty after `.strip()`,
    the emitted `model:` line carries the pin verbatim and the `model_tier:`
    line is OMITTED entirely — that omission is what makes the consumer-side
    `configure_helper apply-agent-models` verb (plan 92 D1, built as Phase 1
    Deliverable 3 of that plan) skip the file, since that verb keys on the
    presence of `model_tier:`. When empty/absent,
    `model:` comes from the tier's static default
    (`CLAUDE_AGENT_DEFAULTS_BY_TIER`) and a `model_tier: <tier>` line follows
    it. Emitted frontmatter order: `name`, `description`, optional `tools`,
    `model`, optional `model_tier`, optional `applies_to`.
    """
    body = body.lstrip("\n")
    tools_line = f"tools: {tools.strip()}\n" if tools.strip() else ""
    applies_to_line = f"applies_to: {applies_to.strip()}\n" if applies_to.strip() else ""
    pin = model_pin.strip()
    if pin:
        model_line = f"model: {pin}\n"
        model_tier_line = ""
    else:
        model_line = f"model: {_claude_tier_model(model_tier)}\n"
        model_tier_line = f"model_tier: {model_tier}\n"
    return (
        "---\n"
        f"name: {name}\n"
        f'description: "{_yaml_escape_double(description)}"\n'
        + tools_line
        + model_line
        + model_tier_line
        + applies_to_line
        + "---\n"
        "\n"
        + body
    )


# ── Main ─────────────────────────────────────────────────────────────────

def _render_one(src_file: Path, target: Path) -> str:
    text = src_file.read_text()
    try:
        meta, body = _parse_source(text)
    except ValueError as e:
        raise ValueError(f"{src_file}: {e}") from None

    name = meta.get("name") or src_file.stem
    description = meta.get("description", "").strip()
    model_tier = meta.get("model_tier", "").strip().lower()
    tools = meta.get("tools", "")
    applies_to = meta.get("applies_to", "")
    # `model_pin` is distinguished from "absent" by dict membership, not by
    # truthiness — an explicitly empty `model_pin:` value is still a
    # declared (and invalid) pin, not the "no pin" default. `_parse_source`
    # always sets `meta[key]` once a `key:` line is seen, even with an empty
    # value, so `"model_pin" in meta` is the correct absence test.
    model_pin_raw = meta.get("model_pin")
    model_pin = model_pin_raw.strip() if model_pin_raw is not None else ""

    if not description:
        raise ValueError(f"{src_file}: missing required 'description'")
    if model_tier not in VALID_TIERS:
        raise ValueError(
            f"{src_file}: 'model_tier' must be one of {sorted(VALID_TIERS)}, "
            f"got {model_tier!r}"
        )
    if model_pin_raw is not None and not _MODEL_PIN_RE.match(model_pin):
        raise ValueError(
            f"{src_file}: 'model_pin' must match a lowercase alias/id shape "
            f"({_MODEL_PIN_RE.pattern!r}), got {model_pin!r}"
        )
    if not body.strip():
        raise ValueError(f"{src_file}: empty body — agent has no instructions")

    rendered = emit_claude(
        name=name,
        description=description,
        model_tier=model_tier,
        body=body,
        tools=tools,
        applies_to=applies_to,
        model_pin=model_pin,
    )

    out_dir = target / TARGET_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}.md"
    out_path.write_text(rendered)
    return str(out_path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Agent generator")
    parser.add_argument(
        "--src", type=Path, required=True,
        help="Directory containing *.md agent sources",
    )
    parser.add_argument(
        "--target", type=Path, required=True,
        help="Target project dir (outputs go under .claude/agents)",
    )
    args = parser.parse_args()

    if not args.src.is_dir():
        print(f"error: --src '{args.src}' is not a directory", file=sys.stderr)
        return 1
    if not args.target.is_dir():
        print(f"error: --target '{args.target}' is not a directory", file=sys.stderr)
        return 1

    sources = sorted(p for p in args.src.glob("*.md"))
    if not sources:
        print(f"warning: no agent sources in {args.src}", file=sys.stderr)
        return 0

    count = 0
    for src_file in sources:
        _render_one(src_file, args.target)
        count += 1
    print(f"  claude → {count} agents in {args.target / TARGET_SUBDIR}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
