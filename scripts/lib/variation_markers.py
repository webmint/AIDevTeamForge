"""Per-runtime variation marker substitution for AIDevTeamForge commands.

Commands in src/commands/ embed runtime-invariant source with a small set of
`{{cli.<key>}}` markers that each runtime emitter substitutes with its own
value at install time. The alternative — pre-generating runtime-specific
source files — would double authoring work and drift.

Markers handled here (simple scalar substitution; block-level markers like
`{{ask}}...{{/ask}}` need a separate parser):

    {{cli.sigil}}        — command invocation prefix
    {{cli.attribution}}  — commit-trailer string for AI attribution

The value map below is the single source of truth. Adding a runtime = one
new entry. Adding a marker = one new key in each runtime's dict.
"""

from __future__ import annotations

import re
from typing import Dict


# ── Per-runtime marker values ───────────────────────────────────────────────

_MARKERS: Dict[str, Dict[str, str]] = {
    "claude": {
        "cli.sigil": "/",
        "cli.attribution": "Co-Authored-By: Claude <noreply@anthropic.com>",
    },
    "codex": {
        # Codex skills are invoked with a "$" prefix in user text — per
        # Codex CLI turn/start docs: "$<skill-name> <optional additional text>".
        # See openai/codex codex-rs/app-server/README.md for the full spec.
        "cli.sigil": "$",
        "cli.attribution": "Co-Authored-By: Codex <noreply@openai.com>",
    },
}


# Matches {{cli.<key>}} where <key> is dot-qualified word characters.
# Anchored on the `cli.` prefix so we don't accidentally touch `{{output.*}}`
# (generator-only) or `{{UPPERCASE}}` wizard placeholders.
_MARKER_RE = re.compile(r"\{\{(cli\.[a-z_]+)\}\}")


def substitute(text: str, runtime: str) -> str:
    """Substitute all `{{cli.<key>}}` markers with the runtime's values.

    Unknown markers (key not in the runtime's map) are left as-is so missing
    entries are visible rather than silently blanked — downstream prose
    instructs the LLM to treat unsubstituted markers semantically, so this
    is safe and debuggable.
    """
    values = _MARKERS.get(runtime)
    if values is None:
        raise ValueError(
            f"unknown runtime {runtime!r}; known: {sorted(_MARKERS)}"
        )

    def _handler(m: re.Match) -> str:
        key = m.group(1)
        return values.get(key, m.group(0))

    return _MARKER_RE.sub(_handler, text)
