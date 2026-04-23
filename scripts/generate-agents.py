#!/usr/bin/env python3
"""Agent generator for AIDevTeamForge.

Reads src/agents/*.md as a universal authoring source and produces per-runtime
agent files. Each source is treated as SEMANTIC DATA — outputs are constructed
from scratch for every runtime; none is privileged or passed through unchanged.

Source format: a fenced yaml meta block at the top of the file, then the
body as markdown prose. The fenced block is deliberately distinct from
Claude's '---'-delimited native agent frontmatter — the source is not a
Claude file, a Codex file, or any runtime's native format.

    ```yaml
    name: architect
    description: "..."
    model_tier: think
    ```

    <body>

Fields in the meta block:
  - name         : agent identifier (required)
  - description  : when-to-use hint (required)
  - model_tier   : think | do | verify (required; semantic, not a runtime placeholder)

Model tier is translated per runtime into wizard placeholders:
  - Claude : model: {{CLAUDE_TIER_THINK}}
  - Codex  : model = "{{CODEX_TIER_THINK}}"
             model_reasoning_effort = "{{CODEX_REASONING_THINK}}"

{{UPPERCASE}} placeholders in body pass through untouched — wizard substitutes
them post-install with project-specific answers.

Usage:
  python3 scripts/generate-agents.py --src src/agents --target /path/to/project

Adding a new runtime: add an entry to RUNTIMES below with its emit function.
No other changes required.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Shared helper for per-runtime {{cli.*}} marker substitution (sigil,
# attribution, primer, subagent). Agent sources use these markers the
# same way commands do; emitting them literally would leak unsubstituted
# {{cli.sigil}} into .claude/agents/ and .codex/agents/ outputs.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.variation_markers import substitute as substitute_markers  # noqa: E402

# We intentionally don't use lib.frontmatter here — agent sources use a
# ```yaml fenced meta block, not ---/--- frontmatter, to avoid mimicking
# Claude's native agent file format. See _parse_source() below.


VALID_TIERS = {"think", "do", "verify"}


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


def _toml_escape_basic(s: str) -> str:
    """Escape a string for a TOML single-line basic string."""
    out = []
    for ch in s:
        code = ord(ch)
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
        elif code < 0x20:
            out.append(f"\\u{code:04X}")
        else:
            out.append(ch)
    return "".join(out)


def _toml_multiline_literal(s: str) -> str:
    """Emit a string as a TOML multi-line literal string '''...'''.

    No escape processing inside literal strings — safe for arbitrary markdown
    content (backslashes, backticks, quotes). If the body itself contains the
    sequence ''' (vanishingly rare in agent prose), fall back to a basic
    multi-line string with minimal escaping.
    """
    if "'''" in s:
        # Fallback: basic multi-line. Escape backslashes, and escape any
        # occurrence of """ (TOML spec allows up to two consecutive unescaped
        # double-quotes inside """...""", so 3+ must be broken up).
        escaped = s.replace("\\", "\\\\").replace('"""', '""\\"')
        return f'"""\n{escaped}"""' if escaped.endswith("\n") else f'"""\n{escaped}\n"""'
    return f"'''\n{s}'''" if s.endswith("\n") else f"'''\n{s}\n'''"


# ── Runtime emitters ─────────────────────────────────────────────────────

def _tier_model(runtime: str, tier: str) -> str:
    return f"{{{{{runtime.upper()}_TIER_{tier.upper()}}}}}"


def _tier_reasoning(tier: str) -> str:
    return f"{{{{CODEX_REASONING_{tier.upper()}}}}}"


def emit_claude(name: str, description: str, model_tier: str, body: str) -> str:
    """Build a Claude-native agent file from scratch (YAML + markdown)."""
    body = body.lstrip("\n")
    return (
        "---\n"
        f"name: {name}\n"
        f'description: "{_yaml_escape_double(description)}"\n'
        f"model: {_tier_model('claude', model_tier)}\n"
        "---\n"
        "\n"
        + body
    )


def emit_codex(name: str, description: str, model_tier: str, body: str) -> str:
    """Build a Codex subagent TOML file from scratch."""
    return (
        f'name = "{_toml_escape_basic(name)}"\n'
        f'description = "{_toml_escape_basic(description)}"\n'
        f'model = "{_tier_model("codex", model_tier)}"\n'
        f'model_reasoning_effort = "{_tier_reasoning(model_tier)}"\n'
        f"developer_instructions = {_toml_multiline_literal(body)}\n"
    )


RUNTIMES: dict[str, dict] = {
    "claude": {
        "target_subdir": ".claude/agents",
        "ext": ".md",
        "emit": emit_claude,
    },
    "codex": {
        "target_subdir": ".codex/agents",
        "ext": ".toml",
        "emit": emit_codex,
    },
}


# ── Main ─────────────────────────────────────────────────────────────────

def _render_one(src_file: Path, runtime: str, cfg: dict, target: Path) -> str:
    text = src_file.read_text()
    try:
        meta, body = _parse_source(text)
    except ValueError as e:
        raise ValueError(f"{src_file}: {e}") from None

    name = meta.get("name") or src_file.stem
    description = meta.get("description", "").strip()
    model_tier = meta.get("model_tier", "").strip().lower()

    if not description:
        raise ValueError(f"{src_file}: missing required 'description'")
    if model_tier not in VALID_TIERS:
        raise ValueError(
            f"{src_file}: 'model_tier' must be one of {sorted(VALID_TIERS)}, "
            f"got {model_tier!r}"
        )
    if not body.strip():
        raise ValueError(f"{src_file}: empty body — agent has no instructions")

    # Substitute per-runtime {{cli.*}} markers (sigil, attribution, primer,
    # subagent) in both description and body before emit. Frontmatter tier
    # markers ({{CLAUDE_TIER_*}} / {{CODEX_TIER_*}}) stay untouched — the
    # wizard substitutes those at install time per agents.md §6.4.
    description = substitute_markers(description, runtime)
    body = substitute_markers(body, runtime)

    rendered = cfg["emit"](
        name=name,
        description=description,
        model_tier=model_tier,
        body=body,
    )

    out_dir = target / cfg["target_subdir"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{name}{cfg['ext']}"
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
        help="Target project dir (outputs go under .claude/agents and .codex/agents)",
    )
    parser.add_argument(
        "--runtimes", type=str, default="",
        help="Space-separated runtimes to emit. Empty = all registered runtimes.",
    )
    args = parser.parse_args()

    if not args.src.is_dir():
        print(f"error: --src '{args.src}' is not a directory", file=sys.stderr)
        return 1
    if not args.target.is_dir():
        print(f"error: --target '{args.target}' is not a directory", file=sys.stderr)
        return 1

    # Resolve runtime filter.
    selected = [r for r in args.runtimes.split() if r]
    if selected:
        unknown = [r for r in selected if r not in RUNTIMES]
        if unknown:
            print(
                f"error: unknown runtime(s): {', '.join(unknown)}. "
                f"Known: {', '.join(RUNTIMES)}",
                file=sys.stderr,
            )
            return 1
    else:
        selected = list(RUNTIMES.keys())

    sources = sorted(p for p in args.src.glob("*.md"))
    if not sources:
        print(f"warning: no agent sources in {args.src}", file=sys.stderr)
        return 0

    for runtime in selected:
        cfg = RUNTIMES[runtime]
        count = 0
        for src_file in sources:
            _render_one(src_file, runtime, cfg, args.target)
            count += 1
        print(f"  {runtime} → {count} agents in {args.target / cfg['target_subdir']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
