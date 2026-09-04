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
  - model_tier   : think | do | verify | security (required; semantic, not
                    a runtime placeholder; also emitted verbatim as a
                    `model_tier:` frontmatter line — see below)

The emitter ships NO model choice of its own (plan 94 D2 — "there must be
no defaults, the user chooses"). Every emitted agent carries an explicit
`model: inherit` line. Explicit, not omitted: `inherit` is step 2 of
Claude Code's documented subagent model-resolution order and beats the
`CLAUDE_CODE_SUBAGENT_MODEL` environment variable at step 3 — an absent
`model:` line would fall through to that variable first, handing the
choice to an environment the framework does not set and cannot see (plan
94 OQ-5).

The `model_tier:` line that follows `model:` is what the consumer-side
`configure_helper apply-models` verb (plan 94 D1, built as plan 94 Phase 1
Deliverable 2 — `apply-agent-models` kept as an argparse alias for one
release, OQ-1) keys on: at `/devforge:configure` Phase 5.4 and on
`update.sh`, that verb rewrites `model:` and `effort:` on every
`.claude/agents/*.md` from `.devforge/project-config.json`, using the
value the user configured for that tier. An unconfigured tier leaves
`model: inherit` untouched — inheriting the session model is what "no
defaults" means for an agent that nobody has configured yet. A file with
no `model_tier:` line — a consumer's own hand-written agent — is left
untouched by that verb.

`model_pin` support was REMOVED from this emitter by plan 94 D3 — a
framework-chosen model for one agent was itself a one-member default,
which D2 forbids (`src/agents/security-reviewer.md` moved onto
`model_tier: security` at plan 94 Phase 2, 2026-09-04 — the security tier
became its own Q11.4 question instead). GUARD: a source that still
declares the removed `model_pin` key (none in the shipped roster since
that date) is emitted normally — `model: inherit` plus `model_tier:` —
and this emitter prints one warning to stderr, naming the source file and
the key, saying the field is no longer honored.

{{UPPERCASE}} placeholders in body prose pass through untouched — wizard
substitutes them post-install with project-specific answers (FRAMEWORK,
LANGUAGE, ARCHITECTURE, etc.). Those are inside string fields, not structural,
so Claude parses them fine as literal text.

Usage:
  python3 scripts/generate-agents.py --src src/agents --target /path/to/project
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# We intentionally don't use lib.frontmatter here — agent sources use a
# ```yaml fenced meta block, not ---/--- frontmatter, to avoid mimicking
# Claude's native agent file format. See _parse_source() below.


VALID_TIERS = {"think", "do", "verify", "security"}

TARGET_SUBDIR = ".claude/agents"


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
# No model default is emitted (plan 94 D2). Every agent carries an
# explicit `model: inherit` — see the module docstring for why that line
# is explicit rather than omitted. The `model_tier:` line that follows it
# is what the consumer-side `configure_helper apply-models` verb (plan 94
# D1) keys on to rewrite `model:`/`effort:` post-install.


def emit_claude(
    name: str,
    description: str,
    model_tier: str,
    body: str,
    tools: str = "",
    applies_to: str = "",
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

    `model:` is always the literal `inherit` (plan 94 D2 — the framework
    ships no model of its own) and `model_tier: <model_tier>` always
    follows it; there is no per-agent override at this layer (plan 94 D3
    removed `model_pin`). Emitted frontmatter order: `name`, `description`,
    optional `tools`, `model`, `model_tier`, optional `applies_to`.
    """
    body = body.lstrip("\n")
    tools_line = f"tools: {tools.strip()}\n" if tools.strip() else ""
    applies_to_line = f"applies_to: {applies_to.strip()}\n" if applies_to.strip() else ""
    model_line = "model: inherit\n"
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

    if not description:
        raise ValueError(f"{src_file}: missing required 'description'")
    if model_tier not in VALID_TIERS:
        raise ValueError(
            f"{src_file}: 'model_tier' must be one of {sorted(VALID_TIERS)}, "
            f"got {model_tier!r}"
        )
    if not body.strip():
        raise ValueError(f"{src_file}: empty body — agent has no instructions")

    # GUARD (plan 94 D3): `model_pin` was removed from the authoring
    # contract (none in the shipped roster since Phase 2, 2026-09-04).
    # A source that still declares it isn't failed — warn once and ignore
    # it, so the source keeps rendering like any other agent.
    if "model_pin" in meta:
        print(
            f"warning: {src_file}: 'model_pin' has been removed from the "
            "authoring contract (plan 94 D3) and is no longer honored — "
            "ignoring it",
            file=sys.stderr,
        )

    rendered = emit_claude(
        name=name,
        description=description,
        model_tier=model_tier,
        body=body,
        tools=tools,
        applies_to=applies_to,
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
