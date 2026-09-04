"""apply-models command handler (92-AGENT-MODEL-AND-EFFORT-CONFIG-PLAN.md
D1, Phase 1 Deliverable 3; extended over commands and renamed by
94-MODEL-OVERRIDE-AND-NO-DEFAULTS-PLAN.md D1, Phase 1 Deliverable 2).
Walks the filesystem and project-config.json; all rewrite logic lives in
_agent_models.py.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from ._agent_models import (
    COMMAND_TIERS,
    REASON_NOT_IN_COMMAND_TIERS,
    AgentValidationError,
    extract_tier_config,
    plan_rewrite,
)
from ._render import _write_file_atomic


def cmd_apply_agent_models(args: argparse.Namespace) -> int:
    """Rewrite model:/effort: frontmatter on every .claude/agents/*.md AND
    every mapped .claude/commands/devforge/*.md from
    .devforge/project-config.json.

    Two classes, two keying mechanisms, one report: agents are keyed on
    each file's own model_tier: line (unchanged from plan 92); commands
    are keyed on COMMAND_TIERS by file stem, since a command carries no
    tier marker line at all (plan 94 D1). Either directory being absent
    is fine -- that class simply contributes zero entries, never an
    error; only project-config.json missing/malformed is a hard failure.

    Two-pass across BOTH classes together: every file's decision is
    computed first (plan_rewrite, pure); nothing is written until every
    file -- agent and command alike -- has validated cleanly. A file
    without a keying match (an agent with no model_tier:, or a command
    whose stem is not a COMMAND_TIERS member) is reported under
    "skipped" and never touched; an unmapped command is not even read,
    since nothing about its content could change the outcome.

    Files are read via read_bytes().decode("utf-8") rather than
    Path.read_text() -- the latter performs universal-newline
    translation on read, which would silently flatten a CRLF file's line
    endings to LF before plan_rewrite ever saw them; reading raw bytes
    preserves whatever ending the file actually has (python-reviewer run
    B finding 3, paired with plan_rewrite's own CRLF-aware rewrite).
    Writes are atomic per file (_write_file_atomic: mkstemp + fsync +
    os.replace, preserving the target's existing permission bits) and
    only happen for a file whose bytes actually change -- idempotent by
    construction, since a second run's plan_rewrite yields changed=False
    for every file and nothing is written. A write-phase IO error can
    therefore leave a PARTIALLY applied set -- each individual write is
    atomic, but the batch as a whole is not transactional -- distinct
    from a config or validation error (both pass 1), which always write
    nothing at all.

    Exit 0 = report emitted (files may or may not have changed).
    Exit 1 = project-config.json missing/malformed, or an IO error
             reading a file (pass 1) or writing one (pass 2). A pass-1
             read error is collected and reported alongside any
             validation errors from other files rather than aborting the
             run early (python-reviewer run B finding 8): every file
             still gets a chance to validate before anything is decided.
    Exit 2 = at least one file's resolved tier/effort or frontmatter
             shape is invalid (unknown model_tier, a claude_effort value
             outside the six-member enum, a duplicated
             model_tier:/model:/effort: key, or -- commands only -- no
             description: line to anchor an inserted model:/effort:
             line after); every such file is named on stderr and NOTHING
             is written. Exit 2 takes priority over exit 1 when a run
             has both a validation error and a pass-1 read error.

    stdout JSON shape -- a contract for its callers: /devforge:configure
    Phase 5.4 invokes this verb and prints its report, and update.sh does
    the same after the promoted-command re-emit:
        {
          "applied": [
            {"kind": "agent", "name": "architect", "tier": "think",
             "model": "fable", "effort": "xhigh", "changed": true},
            {"kind": "command", "name": "plan", "tier": "think",
             "model": "fable", "effort": "xhigh", "changed": true},
            ...
          ],
          "skipped": [
            {"kind": "agent", "name": "my-custom-agent",
             "reason": "no-model-tier"},
            {"kind": "command", "name": "research",
             "reason": "not-in-command-tiers"},
            ...
          ]
        }
    Both lists sorted by ("kind", "name") -- agents before commands,
    alphabetical within each. "model" is a string for every applied
    agent (an unconfigured tier still resolves to "inherit" -- see
    _agent_models._resolve_tier) but may be null for an applied command
    (an unconfigured tier writes no model: line at all, so there is no
    value to report). This report carries "name", not the plan-92 report
    shape's "agent" key -- update.sh's jq reads the field it renames in
    the same release this verb's rename lands in, so there is no
    transition window where both keys need to coexist.
    """
    devforge_dir = Path(args.devforge_dir)

    config_path = devforge_dir / "project-config.json"
    if not config_path.exists():
        sys.stderr.write(
            "configure_helper apply-models: project-config.json not found at "
            "{0}\n".format(config_path)
        )
        return 1
    try:
        config_text = config_path.read_text(encoding="utf-8")
    except OSError as err:
        sys.stderr.write(
            "configure_helper apply-models: cannot read {0}: {1}\n".format(
                config_path, err
            )
        )
        return 1
    try:
        project_config = json.loads(config_text)
    except (json.JSONDecodeError, ValueError) as err:
        sys.stderr.write(
            "configure_helper apply-models: malformed project-config.json: "
            "{0}\n".format(err)
        )
        return 1

    tier_models, tier_efforts = extract_tier_config(project_config)

    install_root = Path(args.install_root)
    agents_dir = install_root / ".claude" / "agents"
    commands_dir = install_root / ".claude" / "commands" / "devforge"

    agent_files = []  # type: List[Path]
    if agents_dir.is_dir():
        try:
            agent_files = sorted(
                p for p in agents_dir.iterdir() if p.is_file() and p.suffix == ".md"
            )
        except OSError as err:
            sys.stderr.write(
                "configure_helper apply-models: cannot list {0}: {1}\n".format(
                    agents_dir, err
                )
            )
            return 1

    command_files = []  # type: List[Path]
    if commands_dir.is_dir():
        try:
            command_files = sorted(
                p for p in commands_dir.iterdir() if p.is_file() and p.suffix == ".md"
            )
        except OSError as err:
            sys.stderr.write(
                "configure_helper apply-models: cannot list {0}: {1}\n".format(
                    commands_dir, err
                )
            )
            return 1

    # --- Pass 1: compute every file's decision, across BOTH classes.
    # Nothing is written here. Both read errors and validation errors
    # are COLLECTED across the whole loop rather than returning on the
    # first one, so a later file's problem never hides an earlier file's
    # (python-reviewer run B finding 8) -- every error any file raised
    # is on stderr together.
    plans = []  # type: List[tuple]
    errors = []  # type: List[str]
    had_validation_error = False

    for agent_path in agent_files:
        name = agent_path.stem
        try:
            original = agent_path.read_bytes().decode("utf-8")
        except OSError as err:
            errors.append("{0}: cannot read: {1}".format(agent_path.name, err))
            continue
        try:
            new_text, decision = plan_rewrite(original, tier_models, tier_efforts)
        except AgentValidationError as err:
            errors.append("{0}: {1}".format(agent_path.name, err))
            had_validation_error = True
            continue
        plans.append(("agent", agent_path, name, new_text, decision))

    for command_path in command_files:
        name = command_path.stem
        tier = COMMAND_TIERS.get(name)
        if tier is None:
            # Not read at all -- nothing about an unmapped command's
            # content could change this outcome, and D1 requires it be
            # left byte-identical.
            plans.append((
                "command", command_path, name, None,
                {"status": "skipped", "reason": REASON_NOT_IN_COMMAND_TIERS},
            ))
            continue
        try:
            original = command_path.read_bytes().decode("utf-8")
        except OSError as err:
            errors.append("{0}: cannot read: {1}".format(command_path.name, err))
            continue
        try:
            new_text, decision = plan_rewrite(
                original, tier_models, tier_efforts, kind="command", tier=tier
            )
        except AgentValidationError as err:
            errors.append("{0}: {1}".format(command_path.name, err))
            had_validation_error = True
            continue
        plans.append(("command", command_path, name, new_text, decision))

    if errors:
        for msg in errors:
            sys.stderr.write("configure_helper apply-models: {0}\n".format(msg))
        return 2 if had_validation_error else 1

    # --- Pass 2: write, then build the report. ---
    applied = []  # type: List[dict]
    skipped = []  # type: List[dict]

    for kind, path, name, new_text, decision in plans:
        if decision["status"] == "skipped":
            skipped.append({"kind": kind, "name": name, "reason": decision["reason"]})
            continue
        if decision["changed"]:
            try:
                _write_file_atomic(path, new_text)
            except OSError as err:
                sys.stderr.write(
                    "configure_helper apply-models: cannot write {0}: {1}\n".format(
                        path, err
                    )
                )
                return 1
        applied.append({
            "kind": kind,
            "name": name,
            "tier": decision["tier"],
            "model": decision["model"],
            "effort": decision["effort"],
            "changed": decision["changed"],
        })

    applied.sort(key=lambda d: (d["kind"], d["name"]))
    skipped.sort(key=lambda d: (d["kind"], d["name"]))
    report = {"applied": applied, "skipped": skipped}
    sys.stdout.write(json.dumps(report, indent=2))
    sys.stdout.write("\n")
    return 0
