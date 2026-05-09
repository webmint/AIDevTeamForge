"""configure_helper — composes the configuration state file for /configure.

Owns the shape of `.devforge/configure.yaml`: 27 fields covering project
metadata, language/framework stacks, build/lint/type-check commands,
per-package stack records, workflow enforcement, AI attribution, Claude
tier settings, and AC verification parameters. `/configure` is the third
command in the 4-command pivot (init-forge → generate-docs → configure →
constitute).

When fully built (Steps 1-4 per CONFIGURE-PLAN.md), it reads
`.devforge/init.yaml`, `.devforge/index.json`, `docs/*.md`, and a focused
subset of repo config files, renders `.devforge/project-config.json` as a
derived artifact, and substitutes `{{KEY}}` placeholders in `CLAUDE.md` +
`.claude/agents/*.md`. Step 0 (current) scaffolds only: argparse + the
`reset` subcommand. FIELD_SCHEMA, ENUM_FIELDS, read-* subcommands, setters,
render-config, substitute-templates are all populated in later steps.

Architecture notes:

- The yaml IS the state. Each setter reads yaml from disk (or loads
  defaults if the file is absent), mutates an in-memory dict, and writes
  yaml back atomically via tempfile.mkstemp + os.replace in the same
  directory as the target.

- Field order in the emitted yaml is fixed (deterministic output for
  diff stability) and matches the source-of-truth schema below.

- `reset` writes a fresh defaults yaml; it does NOT delete the file.
  The artifact always exists post-reset. Idempotent: byte-identical on
  re-run.

- FIELD_SCHEMA and ENUM_FIELDS are empty placeholders in Step 0. Step 1
  populates them with the full 27-field schema (project_name,
  project_description, project_type, primary_language, languages,
  frameworks, architectures, error_handlings, api_layers, testings,
  build_tools, build_commands, type_check_commands, lint_commands,
  package_stacks, project_structure, dev_commands, architecture_details,
  workflow_enforcement, ai_attribution, claude_tier_think, claude_tier_do,
  claude_tier_verify, ac_verification_mode, ac_runtime_url,
  ac_runtime_api_base, ac_runtime_cli_command) and enum sets for
  workflow_enforcement, ai_attribution, claude_tier_*, ac_verification_mode.

- `default_state()` currently returns `{}` because FIELD_SCHEMA is empty.
  When Step 1 fills FIELD_SCHEMA, this will iterate it and return all keys
  with their default values (scalars → None, arrays → []).

- `emit_yaml(state)` currently returns a placeholder comment because there
  are no schema fields to render. Step 1 expands this to walk FIELD_SCHEMA
  in locked order, using the same quoting/escaping rules as init_helper.

- `parse_yaml(text)` currently returns `{}` when given the placeholder
  text. Step 1 expands this to the same closed-shape parser pattern as
  init_helper.

- Validation is set-time per-field shape only. No cross-field invariants
  at Step 0 (none implemented yet).

- `--devforge-dir` CLI argument (default: DEVFORGE_DIR env var, falling
  back to `.devforge`) is threaded through args to all subcommand handlers,
  making the devforge directory explicit at every call site. This differs
  from init_helper's env-only approach and is intentional for /configure:
  the command may be invoked from multiple locations during a session.

Stdlib only. No third-party dependencies. Targets Python 3.8+.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path
from typing import Union

# Published artifact name (NOT a hidden state file — downstream commands
# read it).
OUTPUT_FILE_NAME = "configure.yaml"


# ---------------------------------------------------------------------------
# Schema — single source of truth for field order, kind, and defaults.
# ---------------------------------------------------------------------------

# Step 0 scaffolding: both constants are empty placeholders.
# Step 1 populates per CONFIGURE-PLAN.md with the full 27-field schema.
#
# When populated, FIELD_SCHEMA will follow the same tuple-of-tuples
# convention as init_helper.FIELD_SCHEMA: (field_name, field_kind) pairs
# where field_kind is one of "scalar", "scalar_array", or "record_array".
FIELD_SCHEMA: tuple = ()

# Step 0 scaffolding: empty dict placeholder.
# Step 1 populates with enum sets for workflow_enforcement, ai_attribution,
# claude_tier_think, claude_tier_do, claude_tier_verify, ac_verification_mode.
ENUM_FIELDS: dict = {}

# Placeholder text emitted by emit_yaml when FIELD_SCHEMA is empty.
# Step 1 replaces emit_yaml with a schema-driven implementation that
# renders all 27 fields in FIELD_SCHEMA order.
_PLACEHOLDER_YAML = (
    "# configure.yaml — schema populated by Step 1 of CONFIGURE-PLAN.md\n"
)


# ---------------------------------------------------------------------------
# Path resolution.
# ---------------------------------------------------------------------------


def _output_file_path(devforge_dir: Union[str, "os.PathLike[str]"]) -> Path:
    """Return the output file path for the given devforge directory.

    Joins OUTPUT_FILE_NAME to devforge_dir. The devforge_dir is supplied
    explicitly by callers (threaded from CLI args or from the DEVFORGE_DIR
    env var via main()) — not resolved from the environment at call time.
    This makes the path explicit at every call site.
    """
    return Path(devforge_dir) / OUTPUT_FILE_NAME


# ---------------------------------------------------------------------------
# Defaults.
# ---------------------------------------------------------------------------


def default_state() -> dict:
    """Return a fresh defaults dict matching FIELD_SCHEMA shape.

    Currently returns `{}` because FIELD_SCHEMA is empty (Step 0
    scaffolding). When Step 1 populates FIELD_SCHEMA, this will iterate
    it and return all keys with their type-appropriate defaults:
    scalars → None, arrays → [].
    """
    return {}


# ---------------------------------------------------------------------------
# YAML emitter (stub — Step 0).
# ---------------------------------------------------------------------------


def emit_yaml(state: dict) -> str:
    """Serialize `state` to a YAML string.

    Step 0: returns the placeholder comment because FIELD_SCHEMA is empty
    and there are no fields to render. The `state` argument is accepted
    but ignored at this stage (it will always be `{}` from `default_state()`).

    Step 1 expands this to a schema-driven emitter that walks FIELD_SCHEMA
    in locked order, applying the same quoting/escaping rules as
    init_helper's emitter (double-quote scalars containing YAML special
    chars, reserved words, or numeric-looking strings; null for None).
    """
    return _PLACEHOLDER_YAML


# ---------------------------------------------------------------------------
# YAML parser (stub — Step 0).
# ---------------------------------------------------------------------------


def parse_yaml(text: str) -> dict:
    """Parse a YAML string previously emitted by `emit_yaml`.

    Step 0: returns `{}` for the placeholder text produced by emit_yaml.
    Does not attempt full YAML parsing (the schema is not yet defined).

    Step 1 expands this to a closed-shape parser (the inverse of the
    emit_yaml implementation) that reconstructs a state dict from the
    schema-driven output. Raises YamlParseError on input outside the
    closed shape.
    """
    return {}


# ---------------------------------------------------------------------------
# Atomic write helper.
# ---------------------------------------------------------------------------


def _write_state(state: dict, devforge_dir: Union[str, "os.PathLike[str]"]) -> None:
    """Atomically write `state` to the output yaml path.

    Uses tempfile.mkstemp in the same directory as the target so
    os.replace is atomic on a single filesystem. flush + fsync before
    os.replace adds a durability barrier — init_helper omits fsync;
    this is an intentional divergence (durability over the small
    syscall cost). On any failure, attempts to remove the temp file
    and re-raises.
    """
    target = _output_file_path(devforge_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix="configure-",
        suffix=".yaml.tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(emit_yaml(state))
            f.flush()
            # fsync before os.replace — durability improvement over
            # init_helper's pattern. Step 1+ writers should preserve.
            os.fsync(f.fileno())
        os.replace(tmp_path, str(target))
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Subcommand implementations.
# ---------------------------------------------------------------------------


def _die(message: str, code: int = 1) -> int:
    sys.stderr.write("configure_helper: {0}\n".format(message))
    return code


def cmd_reset(args: argparse.Namespace) -> int:
    """Write a fresh defaults yaml. Idempotent: byte-identical on re-run."""
    try:
        _write_state(default_state(), args.devforge_dir)
    except OSError as err:
        return _die(
            "reset: cannot write {0}: {1}".format(
                _output_file_path(args.devforge_dir), err
            )
        )
    return 0


# ---------------------------------------------------------------------------
# CLI wiring.
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    default_devforge_dir = os.environ.get("DEVFORGE_DIR", ".devforge")

    parser = argparse.ArgumentParser(
        prog="configure_helper",
        description="Compose the configuration state file for /configure.",
    )
    parser.add_argument(
        "--devforge-dir",
        default=default_devforge_dir,
        dest="devforge_dir",
        help=(
            "Directory for devforge state files. "
            "Default: DEVFORGE_DIR env var, or '.devforge'."
        ),
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    sp = subparsers.add_parser("reset", help="Write a fresh defaults yaml.")
    sp.set_defaults(func=cmd_reset)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "func", None) is None:
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
