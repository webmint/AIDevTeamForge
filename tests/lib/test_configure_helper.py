"""Tests for src/devforge/lib/configure_helper.py — Step 1 + Step 2 + Step 3 + Step 4.

Step 1 coverage: FIELD_SCHEMA, ENUM_FIELDS, default_state, emit_yaml/
parse_yaml round-trips (incl. multi-line scalars + missing-subfield
rejection + fence-aware section extractor), reset subcommand, read-init
(real-producer round-trip), read-docs (hand-authored Plan F fixtures),
read-manifests, read-configs.

Step 2 coverage: _load / _dump / _state_transaction (write-on-exit, abort-
on-exception, lock-file creation), five _validate_* helpers, all 28 setter
subcommands (3 identity + 1 primary-language + 8 stack arrays incl.
project_natures + 3 per-pkg arrays + add-package-stack + 3 verbatim +
6 enums + 3 ac-runtime), round-trip integration (all-28-fields set +
reload + compare; replace-not-append
for string_arrays; accumulate for add-package-stack), cross-process safety
(5 concurrent add-package-stack via Popen — no lost writes; mixed scalar+
append concurrency — no corruption).

Step 3 coverage: _write_json (atomic write, idempotency, no temp files left),
_build_project_config (36-key output, WRAPPER_MODE_SECTION variants,
COMMIT_ATTRIBUTION variants, field mapping, package_stacks pass-through),
_read_agent_list (absent dir, empty dir, sorted alphabetically, non-md excluded),
render-config subprocess (init.yaml missing, 36-key output, configure fields,
init fields, wrapper section, commit attribution, agent list, idempotency,
overwrite semantics, package_stacks), verify subprocess (all-populated pass,
null scalar fail, empty array fail, ac-runtime optional when not runtime-
assisted, ac-runtime required when runtime-assisted, json missing, json
malformed, round-trip drift), summary subprocess (unset shows label, populated
values, long string truncation, package_stacks rows, stability, empty array,
section headers).

Step 4 coverage: _build_substitution_map (all 36 project-config keys present,
10 singular aliases derive from plural arrays, PROJECT_PATHS from
packages_detected, PACKAGE_STACKS_SECTION empty → empty string, populated →
4-column markdown table, UPPERCASE identity, STATE_MANAGEMENT + STYLING NOT
in map — those rules live in constitution.md per /constitute pipeline),
_substitute_placeholders engine (single placeholder, multiple placeholders,
unknown key → missing list, STATE_MANAGEMENT + STYLING reported as unknown (no
deprecated empty-string fallback — those rules live in constitution.md), once-per
run, UPPERCASE round-trip, no bleed-over on lowercase/mixed patterns),
substitute-templates subprocess (defaults exit 0 no leftover placeholders,
populated project_name substituted, single language, multi-language comma-join,
PACKAGE_STACKS_SECTION table, unknown placeholder exit 2,
idempotent re-run, project-config.json missing exit 1, agent .md substituted,
unknown placeholder leaves original file unchanged, UPPERCASE round-trip).

Each subprocess test runs in its own `tempfile.TemporaryDirectory` via
_EnvIsolationMixin. Pure-function tests import the module directly.

Real-producer principle for read-init: init_helper writes init.yaml via
its subprocess; configure_helper read-init parses it. No hand-authored
yaml fixtures bypass the real producer.

Stdlib only.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "configure_helper.py"
_INIT_HELPER_PY = _LIB_DIR / "init_helper.py"

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import configure_helper  # noqa: E402
import init_helper  # noqa: E402


# ---------------------------------------------------------------------------
# Subprocess helpers.
# ---------------------------------------------------------------------------


def _run_configure(devforge_dir, *args):
    """Invoke configure_helper.py <args> as a subprocess."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY), "--devforge-dir", str(devforge_dir)] + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _run_configure_extra(devforge_dir, extra_args, *args):
    """Invoke configure_helper.py with extra flags inserted before subcommand."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY), "--devforge-dir", str(devforge_dir)]
        + list(extra_args) + list(args),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _run_init(devforge_dir, *args):
    """Invoke init_helper.py <args> as a subprocess."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_INIT_HELPER_PY)] + list(args),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


class _EnvIsolationMixin:
    """Save/restore DEVFORGE_DIR around each test + provide a tmpdir.

    Layout:
      self._tmp.name/          ← install_root (used for docs/, config files)
        .devforge/             ← devforge_dir (configure.yaml, index.json, etc.)
    """

    def setUp(self):
        self._saved_env = os.environ.pop("DEVFORGE_DIR", None)
        self._tmp = tempfile.TemporaryDirectory()
        self.install_root = Path(self._tmp.name)
        self.devforge_dir = self.install_root / ".devforge"
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.devforge_dir / configure_helper.OUTPUT_FILE_NAME

    def tearDown(self):
        self._tmp.cleanup()
        if self._saved_env is None:
            os.environ.pop("DEVFORGE_DIR", None)
        else:
            os.environ["DEVFORGE_DIR"] = self._saved_env


# ---------------------------------------------------------------------------
# 1. Schema tests (~5)
# ---------------------------------------------------------------------------


class SchemaTests(unittest.TestCase):

    def test_field_schema_has_28_fields(self):
        self.assertEqual(len(configure_helper.FIELD_SCHEMA), 28)

    def test_default_state_has_28_keys(self):
        state = configure_helper.default_state()
        self.assertEqual(len(state), 28)

    def test_default_state_scalars_are_none(self):
        state = configure_helper.default_state()
        for name, kind in configure_helper.FIELD_SCHEMA:
            if kind == "scalar":
                self.assertIsNone(
                    state[name],
                    "scalar {0} should default to None".format(name),
                )

    def test_default_state_arrays_are_empty_list(self):
        state = configure_helper.default_state()
        for name, kind in configure_helper.FIELD_SCHEMA:
            if kind in ("string_array", "package_stack_array"):
                self.assertEqual(
                    state[name],
                    [],
                    "{0} should default to []".format(name),
                )

    def test_field_schema_order_is_locked(self):
        """Regression guard: field order is part of the diff-stability contract."""
        names = [name for name, _ in configure_helper.FIELD_SCHEMA]
        expected = [
            "project_name",
            "project_description",
            "project_type",
            "primary_language",
            "languages",
            "frameworks",
            "architectures",
            "project_natures",
            "error_handlings",
            "api_layers",
            "testings",
            "build_tools",
            "build_commands",
            "type_check_commands",
            "lint_commands",
            "package_stacks",
            "project_structure",
            "dev_commands",
            "architecture_details",
            "workflow_enforcement",
            "ai_attribution",
            "claude_tier_think",
            "claude_tier_do",
            "claude_tier_verify",
            "ac_verification_mode",
            "ac_runtime_url",
            "ac_runtime_api_base",
            "ac_runtime_cli_command",
        ]
        self.assertEqual(names, expected)

    def test_enum_fields_has_3_entries(self):
        # claude_tier_* deliberately omitted to allow custom model aliases
        # via Q11 Other branch.
        self.assertEqual(len(configure_helper.ENUM_FIELDS), 3)

    def test_enum_fields_correct_keys(self):
        expected_keys = {
            "workflow_enforcement",
            "ai_attribution",
            "ac_verification_mode",
        }
        self.assertEqual(set(configure_helper.ENUM_FIELDS.keys()), expected_keys)

    def test_enum_fields_correct_values(self):
        self.assertEqual(
            configure_helper.ENUM_FIELDS["workflow_enforcement"],
            {"Strict", "Moderate", "Light"},
        )
        self.assertEqual(
            configure_helper.ENUM_FIELDS["ai_attribution"],
            {"Yes", "No"},
        )
        self.assertEqual(
            configure_helper.ENUM_FIELDS["ac_verification_mode"],
            {"code-only", "tests", "runtime-assisted", "off"},
        )


# ---------------------------------------------------------------------------
# 2. emit_yaml / parse_yaml round-trip tests (~12)
# ---------------------------------------------------------------------------


class EmitParseRoundTripTests(unittest.TestCase):

    def test_defaults_round_trip(self):
        state = configure_helper.default_state()
        text = configure_helper.emit_yaml(state)
        state2 = configure_helper.parse_yaml(text)
        self.assertEqual(state, state2)

    def test_emit_ends_with_newline(self):
        text = configure_helper.emit_yaml(configure_helper.default_state())
        self.assertTrue(text.endswith("\n"))

    def test_emit_field_order_matches_schema(self):
        """Fields appear in FIELD_SCHEMA order in emitted yaml."""
        text = configure_helper.emit_yaml(configure_helper.default_state())
        lines = [l for l in text.splitlines() if l and not l.startswith(" ") and ":" in l]
        emitted_keys = []
        for line in lines:
            key = line.split(":")[0].strip()
            if key:
                emitted_keys.append(key)
        schema_keys = [name for name, _ in configure_helper.FIELD_SCHEMA]
        self.assertEqual(emitted_keys, schema_keys)

    def test_scalar_none_emits_null(self):
        text = configure_helper.emit_yaml(configure_helper.default_state())
        self.assertIn("project_name: null", text)

    def test_string_array_empty_emits_bracket(self):
        text = configure_helper.emit_yaml(configure_helper.default_state())
        self.assertIn("languages: []", text)

    def test_package_stack_array_empty_emits_bracket(self):
        text = configure_helper.emit_yaml(configure_helper.default_state())
        self.assertIn("package_stacks: []", text)

    def test_all_scalars_set_round_trip(self):
        state = configure_helper.default_state()
        state["project_name"] = "my-project"
        state["project_description"] = "A test project"
        state["project_type"] = "Web Application"
        state["primary_language"] = "TypeScript"
        state["project_structure"] = "src/ lib/ tests/"
        state["dev_commands"] = "npm run dev"
        state["architecture_details"] = "Clean Architecture"
        state["workflow_enforcement"] = "Strict"
        state["ai_attribution"] = "Yes"
        state["claude_tier_think"] = "Opus"
        state["claude_tier_do"] = "Sonnet"
        state["claude_tier_verify"] = "Haiku"
        state["ac_verification_mode"] = "tests"
        state["ac_runtime_url"] = "http://localhost:3000"
        state["ac_runtime_api_base"] = "http://localhost:4000"
        state["ac_runtime_cli_command"] = "npm run start"
        text = configure_helper.emit_yaml(state)
        state2 = configure_helper.parse_yaml(text)
        self.assertEqual(state, state2)

    def test_string_array_populated_round_trip(self):
        state = configure_helper.default_state()
        state["languages"] = ["TypeScript", "Python", "Go"]
        state["frameworks"] = ["Vue", "FastAPI"]
        text = configure_helper.emit_yaml(state)
        # Block list format.
        self.assertIn("languages:\n  -", text)
        state2 = configure_helper.parse_yaml(text)
        self.assertEqual(state2["languages"], ["TypeScript", "Python", "Go"])
        self.assertEqual(state2["frameworks"], ["Vue", "FastAPI"])

    def test_string_array_items_quoted_when_needed(self):
        """String array items are quoted when _needs_quoting returns True."""
        state = configure_helper.default_state()
        # "null" is a YAML reserved word — must be quoted.
        state["languages"] = ["null"]
        text = configure_helper.emit_yaml(state)
        self.assertIn('  - "null"', text)
        state2 = configure_helper.parse_yaml(text)
        self.assertEqual(state2["languages"], ["null"])

    def test_string_array_items_unquoted_when_safe(self):
        """Plain identifiers with no special chars are emitted unquoted."""
        state = configure_helper.default_state()
        state["languages"] = ["TypeScript"]
        text = configure_helper.emit_yaml(state)
        self.assertIn("  - TypeScript", text)

    def test_package_stack_array_populated_round_trip(self):
        state = configure_helper.default_state()
        state["package_stacks"] = [
            {
                "path": "apps/app-web",
                "language": "TypeScript",
                "framework": "Vue",
                "build_tool": "Vite",
                "build_command": "npm run build",
                "type_check_command": "npm run typecheck",
                "lint_command": "npm run lint",
            }
        ]
        text = configure_helper.emit_yaml(state)
        state2 = configure_helper.parse_yaml(text)
        self.assertEqual(state2["package_stacks"], state["package_stacks"])

    def test_package_stack_nullable_fields_round_trip(self):
        state = configure_helper.default_state()
        state["package_stacks"] = [
            {
                "path": "services/api",
                "language": "Python",
                "framework": None,
                "build_tool": None,
                "build_command": None,
                "type_check_command": "mypy .",
                "lint_command": "flake8 .",
            }
        ]
        text = configure_helper.emit_yaml(state)
        state2 = configure_helper.parse_yaml(text)
        self.assertEqual(state2["package_stacks"][0]["framework"], None)
        self.assertEqual(state2["package_stacks"][0]["build_tool"], None)
        self.assertEqual(state2["package_stacks"][0]["build_command"], None)

    def test_special_chars_in_scalar_round_trip(self):
        state = configure_helper.default_state()
        state["project_name"] = 'has "quotes" and \\backslash'
        text = configure_helper.emit_yaml(state)
        state2 = configure_helper.parse_yaml(text)
        self.assertEqual(state2["project_name"], 'has "quotes" and \\backslash')

    def test_multiline_scalar_round_trip(self):
        """Newlines + carriage returns escape via \\n / \\r and round-trip.

        Regression: project_structure / dev_commands / architecture_details
        carry verbatim multi-line content from docs/. A non-escaped newline
        produces broken yaml that splits across physical lines.
        """
        tree_text = "apps/\n  app-web/\n    src/\n      main.ts\npackages/"
        state = configure_helper.default_state()
        state["project_structure"] = tree_text
        state["dev_commands"] = "npm run dev\nnpm test"
        text = configure_helper.emit_yaml(state)
        # Emitted text MUST be valid yaml — no unescaped newline inside the
        # quoted scalar (each scalar appears on a single physical line).
        for line in text.splitlines():
            if line.startswith('project_structure:') or line.startswith('dev_commands:'):
                # The line must contain the full quoted string ending with `"`.
                self.assertTrue(
                    line.rstrip().endswith('"'),
                    "scalar emitted across physical lines: {0!r}".format(line),
                )
        state2 = configure_helper.parse_yaml(text)
        self.assertEqual(state2["project_structure"], tree_text)
        self.assertEqual(state2["dev_commands"], "npm run dev\nnpm test")

    def test_carriage_return_in_scalar_round_trip(self):
        state = configure_helper.default_state()
        state["project_name"] = "windows\r\nline ending"
        text = configure_helper.emit_yaml(state)
        state2 = configure_helper.parse_yaml(text)
        self.assertEqual(state2["project_name"], "windows\r\nline ending")

    def test_package_stack_missing_subfield_rejected(self):
        """Closed-shape contract: record missing any of 7 subfields raises.

        Regression: parse_yaml previously accepted incomplete records.
        """
        # Hand-craft yaml with a 6-subfield record (missing lint_command).
        bad_yaml = (
            "project_name: null\n"
            "project_description: null\n"
            "project_type: null\n"
            "primary_language: null\n"
            "languages: []\n"
            "frameworks: []\n"
            "architectures: []\n"
            "error_handlings: []\n"
            "api_layers: []\n"
            "testings: []\n"
            "build_tools: []\n"
            "build_commands: []\n"
            "type_check_commands: []\n"
            "lint_commands: []\n"
            "package_stacks:\n"
            "  - path: \"apps/app-web\"\n"
            "    language: \"TypeScript\"\n"
            "    framework: \"Vue\"\n"
            "    build_tool: \"Vite\"\n"
            "    build_command: \"npm run build\"\n"
            "    type_check_command: \"npm run typecheck\"\n"
            "project_structure: null\n"
        )
        with self.assertRaises(configure_helper.YamlParseError) as ctx:
            configure_helper.parse_yaml(bad_yaml)
        self.assertIn("lint_command", str(ctx.exception))

    def test_all_fields_set_round_trip(self):
        """All 28 fields populated — comprehensive round-trip."""
        state = {
            "project_name": "db-cse-ui-strata",
            "project_description": "A complex monorepo project",
            "project_type": "Web Application",
            "primary_language": "TypeScript",
            "languages": ["TypeScript", "Python"],
            "frameworks": ["Vue", "FastAPI"],
            "architectures": ["Clean Architecture", "Turborepo monorepo"],
            "project_natures": ["web", "backend"],
            "error_handlings": ["Either monad"],
            "api_layers": ["REST", "tRPC"],
            "testings": ["Vitest", "Playwright"],
            "build_tools": ["Vite", "tsc"],
            "build_commands": ["npm run build"],
            "type_check_commands": ["npm run typecheck"],
            "lint_commands": ["npm run lint"],
            "package_stacks": [
                {
                    "path": "apps/app-web",
                    "language": "TypeScript",
                    "framework": "Vue",
                    "build_tool": "Vite",
                    "build_command": "npm run build",
                    "type_check_command": "npm run typecheck",
                    "lint_command": "npm run lint",
                }
            ],
            "project_structure": "apps/ packages/ services/",
            "dev_commands": "npm run dev",
            "architecture_details": "Clean Architecture with domain layers",
            "workflow_enforcement": "Strict",
            "ai_attribution": "Yes",
            "claude_tier_think": "Opus",
            "claude_tier_do": "Sonnet",
            "claude_tier_verify": "Haiku",
            "ac_verification_mode": "tests",
            "ac_runtime_url": "http://localhost:3000",
            "ac_runtime_api_base": "http://localhost:4000",
            "ac_runtime_cli_command": "npm run start",
        }
        text = configure_helper.emit_yaml(state)
        state2 = configure_helper.parse_yaml(text)
        self.assertEqual(state, state2)

    def test_emit_is_idempotent_byte_identical(self):
        """Re-running emit_yaml on same state produces byte-identical output."""
        state = configure_helper.default_state()
        state["project_name"] = "test"
        state["languages"] = ["TypeScript", "Python"]
        state["package_stacks"] = [
            {
                "path": "apps/web",
                "language": "TypeScript",
                "framework": "Vue",
                "build_tool": "Vite",
                "build_command": "npm run build",
                "type_check_command": None,
                "lint_command": None,
            }
        ]
        text1 = configure_helper.emit_yaml(state)
        text2 = configure_helper.emit_yaml(state)
        self.assertEqual(text1, text2)

    def test_multiple_package_stacks_round_trip(self):
        state = configure_helper.default_state()
        state["package_stacks"] = [
            {
                "path": "apps/web",
                "language": "TypeScript",
                "framework": "Vue",
                "build_tool": "Vite",
                "build_command": "npm run build",
                "type_check_command": "npm run typecheck",
                "lint_command": "npm run lint",
            },
            {
                "path": "services/api",
                "language": "Python",
                "framework": None,
                "build_tool": None,
                "build_command": None,
                "type_check_command": "mypy .",
                "lint_command": "flake8 .",
            },
        ]
        text = configure_helper.emit_yaml(state)
        state2 = configure_helper.parse_yaml(text)
        self.assertEqual(len(state2["package_stacks"]), 2)
        self.assertEqual(state2["package_stacks"][0]["path"], "apps/web")
        self.assertEqual(state2["package_stacks"][1]["path"], "services/api")
        self.assertEqual(state2["package_stacks"][1]["framework"], None)


class ParserErrorTests(unittest.TestCase):

    def test_unknown_field_rejected(self):
        with self.assertRaises(configure_helper.YamlParseError):
            configure_helper.parse_yaml("bogus_field: value\n")

    def test_anchor_rejected(self):
        with self.assertRaises(configure_helper.YamlParseError):
            configure_helper.parse_yaml("project_name: &anchor x\n")

    def test_flow_mapping_rejected(self):
        with self.assertRaises(configure_helper.YamlParseError):
            configure_helper.parse_yaml("project_name: {a: b}\n")

    def test_single_quotes_rejected(self):
        with self.assertRaises(configure_helper.YamlParseError):
            configure_helper.parse_yaml("project_name: 'myproject'\n")

    def test_bad_indentation_rejected(self):
        with self.assertRaises(configure_helper.YamlParseError):
            configure_helper.parse_yaml("      project_name: x\n")


# ---------------------------------------------------------------------------
# 3. reset tests (~3)
# ---------------------------------------------------------------------------


class ResetTests(_EnvIsolationMixin, unittest.TestCase):

    def test_reset_writes_valid_yaml(self):
        proc = _run_configure(self.devforge_dir, "reset")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertTrue(self.output_file.exists())
        text = self.output_file.read_text(encoding="utf-8")
        # Must parse cleanly.
        state = configure_helper.parse_yaml(text)
        self.assertEqual(state, configure_helper.default_state())

    def test_reset_is_idempotent_byte_identical(self):
        _run_configure(self.devforge_dir, "reset")
        first = self.output_file.read_bytes()
        _run_configure(self.devforge_dir, "reset")
        second = self.output_file.read_bytes()
        self.assertEqual(first, second)

    def test_reset_overwrites_populated_yaml(self):
        """reset restores defaults even when the yaml has been modified."""
        # Write a non-default yaml directly.
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        state = configure_helper.default_state()
        state["project_name"] = "existing-project"
        state["languages"] = ["TypeScript", "Go"]
        self.output_file.write_text(configure_helper.emit_yaml(state), encoding="utf-8")
        # reset should restore defaults.
        proc = _run_configure(self.devforge_dir, "reset")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        text = self.output_file.read_text(encoding="utf-8")
        state2 = configure_helper.parse_yaml(text)
        self.assertEqual(state2, configure_helper.default_state())

    def test_reset_creates_devforge_dir_when_absent(self):
        nested = self.install_root / "deeper" / ".devforge"
        # nested does not exist yet — reset must create it.
        self.assertFalse(nested.exists())
        proc = _run_configure(nested, "reset")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertTrue((nested / configure_helper.OUTPUT_FILE_NAME).exists())

    def test_no_subcommand_returns_2(self):
        proc = _run_configure(self.devforge_dir)
        self.assertEqual(proc.returncode, 2)


# ---------------------------------------------------------------------------
# 4. read-init tests (~3, via real producer)
# ---------------------------------------------------------------------------


class ReadInitTests(_EnvIsolationMixin, unittest.TestCase):
    """read-init parses init.yaml produced by the real init_helper producer."""

    def _populate_init_yaml(self):
        """Use init_helper subprocess to create a real init.yaml."""
        _run_init(self.devforge_dir, "reset")
        _run_init(self.devforge_dir, "set-workspace-mode", "wrapper")
        _run_init(self.devforge_dir, "set-project-root", "db-cse-ui-strata")
        _run_init(self.devforge_dir, "set-project-state", "brownfield")
        _run_init(self.devforge_dir, "set-default-branch", "dev")
        _run_init(
            self.devforge_dir, "add-package",
            "--path", ".", "--manifest", "package.json",
        )
        _run_init(
            self.devforge_dir, "add-package",
            "--path", "apps/app-web", "--manifest", "package.json",
        )

    def test_read_init_real_producer_round_trip(self):
        """init_helper writes init.yaml; read-init parses and emits matching JSON."""
        self._populate_init_yaml()
        proc = _run_configure(self.devforge_dir, "read-init")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(proc.stdout.decode())
        # Verify all 5 init.yaml fields are present.
        self.assertEqual(data["workspace_mode"], "wrapper")
        self.assertEqual(data["project_root"], "db-cse-ui-strata")
        self.assertEqual(data["project_state"], "brownfield")
        self.assertEqual(data["default_branch"], "dev")
        self.assertEqual(len(data["packages_detected"]), 2)
        self.assertEqual(data["packages_detected"][0]["path"], ".")
        self.assertEqual(data["packages_detected"][1]["path"], "apps/app-web")

    def test_read_init_missing_exits_1(self):
        """read-init with no init.yaml exits 1 with helpful stderr."""
        # Do not create init.yaml.
        proc = _run_configure(self.devforge_dir, "read-init")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"init.yaml not found", proc.stderr)

    def test_read_init_malformed_exits_1(self):
        """Malformed init.yaml causes exit 1 with stderr error."""
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        (self.devforge_dir / "init.yaml").write_text("bogus: [unclosed\n", encoding="utf-8")
        proc = _run_configure(self.devforge_dir, "read-init")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"cannot parse", proc.stderr)


# ---------------------------------------------------------------------------
# 5. read-docs tests (~8)
# ---------------------------------------------------------------------------


_OVERVIEW_MD_FIXTURE = """\
# Project Overview

## Purpose

A Vue 3 TypeScript monorepo for enterprise UI.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Vue 3 |
| Language | TypeScript |
| Build Tool | Vite |
| Testing | Vitest |
| API Layer | REST |

## Project Structure

```
apps/
  app-web/      # main SPA
packages/
  pkg-core/     # shared logic
```

## Entry Points

| Entry Point | Path | Purpose |
|---|---|---|
| main SPA | apps/app-web/src/main.ts | bootstraps Vue app |

## Key Commands

| Command | Description |
|---|---|
| npm run dev | Start dev server |
| npm run build | Build all packages |

## Module Map

### Infrastructure Packages

| Package | Purpose |
|---|---|
| pkg-infra | HTTP client + error handling |

### Core Package

| Package | Purpose |
|---|---|
| pkg-core | Domain logic + types |

### Domain Packages

| Package | Purpose |
|---|---|
| pkg-domain | Business entities |

## Cross-Module Dependencies

pkg-domain → pkg-core → pkg-infra

## Application Routes

| Route | Component | Description |
|---|---|---|
| / | HomeView | Landing page |
| /about | AboutView | About page |

## Navigation Guards

- requiresAuth: blocks unauthenticated users
- requiresRole: blocks insufficient permissions

## Test Files

1. apps/app-web/src/tests/
2. packages/pkg-core/tests/

## Packages

- apps/app-web
- packages/pkg-core
- packages/pkg-domain
"""

_ARCHITECTURE_MD_FIXTURE = """\
# Architecture

## Architecture Overview

The project follows Clean Architecture with domain isolation.

## Module/Package Structure

```
src/
  domain/       # pure domain logic
  application/  # use cases
  infra/        # adapters
```

## Patterns

### Either Monad

**Applies in**: error-prone operations in domain layer

All domain operations return `Either<Error, Result>` instead of throwing.

```typescript
type Either<L, R> = Left<L> | Right<R>
```

### Repository Pattern

**Applies in**: data access layer

Abstracts persistence behind interfaces.

```typescript
interface UserRepository {
  findById(id: string): Promise<User>
}
```

## Conventions

- Never import domain from infra
- Use dependency injection for all adapters

## Layers

- Domain
- Application
- Infrastructure
- Presentation

## Cross-Cuts

- Logging via structured logger
- Error handling via Either monad

## Dependency Direction Rules

- Domain has no external dependencies
- Application depends only on Domain
- Infrastructure implements Domain interfaces

## Dependency Overview

```mermaid
graph TD
  Presentation --> Application
  Application --> Domain
  Infrastructure --> Domain
```
"""


class ReadDocsSectionExtractorTests(unittest.TestCase):
    """Tests for the private _extract_section helper."""

    def test_section_found(self):
        body = configure_helper._extract_section(_OVERVIEW_MD_FIXTURE, "Purpose")
        self.assertIn("Vue 3 TypeScript monorepo", body)

    def test_section_stops_at_next_heading(self):
        body = configure_helper._extract_section(_OVERVIEW_MD_FIXTURE, "Purpose")
        self.assertNotIn("## Tech Stack", body)

    def test_section_not_found_returns_empty(self):
        body = configure_helper._extract_section(_OVERVIEW_MD_FIXTURE, "Nonexistent Section")
        self.assertEqual(body, "")

    def test_section_preserves_fenced_code_block(self):
        body = configure_helper._extract_section(_OVERVIEW_MD_FIXTURE, "Project Structure")
        self.assertIn("```", body)
        self.assertIn("apps/", body)

    def test_section_does_not_terminate_on_hash_inside_fence(self):
        """Regression: a '## ' line inside a fenced block must NOT close the section."""
        md = (
            "# Title\n\n"
            "## Target Section\n"
            "Body line one.\n"
            "```mermaid\n"
            "graph TD\n"
            "## Inner heading inside fence\n"
            "  A --> B\n"
            "```\n"
            "Body line two — after fence.\n\n"
            "## Next Section\n"
            "Should not appear in body.\n"
        )
        body = configure_helper._extract_section(md, "Target Section")
        self.assertIn("Body line one.", body)
        self.assertIn("## Inner heading inside fence", body)
        self.assertIn("Body line two", body)
        self.assertNotIn("Next Section", body)
        self.assertNotIn("Should not appear", body)


class ReadDocsMdTableTests(unittest.TestCase):

    def test_parse_tech_stack_table(self):
        body = configure_helper._extract_section(_OVERVIEW_MD_FIXTURE, "Tech Stack")
        rows = configure_helper._parse_md_table(body)
        self.assertEqual(len(rows), 5)
        # Headers are lowercased column names.
        self.assertEqual(rows[0]["layer"], "Framework")
        self.assertEqual(rows[0]["technology"], "Vue 3")

    def test_parse_returns_empty_list_when_no_table(self):
        rows = configure_helper._parse_md_table("No table here\n")
        self.assertEqual(rows, [])


class ReadDocsBulletTests(unittest.TestCase):

    def test_dashed_bullets_parsed(self):
        body = configure_helper._extract_section(_OVERVIEW_MD_FIXTURE, "Navigation Guards")
        items = configure_helper._parse_md_bullets(body)
        self.assertEqual(len(items), 2)
        self.assertIn("requiresAuth: blocks unauthenticated users", items)

    def test_numbered_list_parsed(self):
        body = configure_helper._extract_section(_OVERVIEW_MD_FIXTURE, "Test Files")
        items = configure_helper._parse_md_bullets(body)
        self.assertEqual(len(items), 2)
        self.assertIn("apps/app-web/src/tests/", items)


class ReadDocsModuleMapTests(unittest.TestCase):

    def test_module_map_three_buckets(self):
        body = configure_helper._extract_section(_OVERVIEW_MD_FIXTURE, "Module Map")
        mm = configure_helper._parse_module_map(body)
        self.assertIn("infrastructure", mm)
        self.assertIn("core", mm)
        self.assertIn("domain", mm)
        self.assertEqual(mm["infrastructure"][0]["package"], "pkg-infra")
        self.assertEqual(mm["core"][0]["package"], "pkg-core")
        self.assertEqual(mm["domain"][0]["package"], "pkg-domain")


class ReadDocsFullFixtureTests(_EnvIsolationMixin, unittest.TestCase):
    """read-docs against a full hand-authored fixture."""

    def _write_docs(self):
        docs_dir = self.install_root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "overview.md").write_text(_OVERVIEW_MD_FIXTURE, encoding="utf-8")
        (docs_dir / "architecture.md").write_text(_ARCHITECTURE_MD_FIXTURE, encoding="utf-8")

    def test_read_docs_full_fixture_exit_0(self):
        self._write_docs()
        proc = _run_configure(
            self.devforge_dir,
            "--install-root", str(self.install_root),
            "read-docs",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(proc.stdout.decode())
        self.assertIn("overview", data)
        self.assertIn("architecture", data)

    def test_read_docs_overview_sections_parsed(self):
        self._write_docs()
        proc = _run_configure(
            self.devforge_dir,
            "--install-root", str(self.install_root),
            "read-docs",
        )
        data = json.loads(proc.stdout.decode())
        ov = data["overview"]
        self.assertIn("Vue 3 TypeScript monorepo", ov["purpose"])
        self.assertEqual(len(ov["tech_stack"]), 5)
        self.assertIn("apps/", ov["project_structure"])
        self.assertEqual(len(ov["entry_points"]), 1)
        self.assertEqual(len(ov["key_commands"]), 2)
        self.assertIn("infrastructure", ov["module_map"])
        self.assertIn("pkg-domain → pkg-core", ov["cross_module_dependencies"])
        self.assertEqual(len(ov["application_routes"]), 2)
        self.assertEqual(len(ov["navigation_guards"]), 2)
        self.assertEqual(len(ov["test_files"]), 2)
        self.assertEqual(len(ov["packages"]), 3)

    def test_read_docs_architecture_sections_parsed(self):
        self._write_docs()
        proc = _run_configure(
            self.devforge_dir,
            "--install-root", str(self.install_root),
            "read-docs",
        )
        data = json.loads(proc.stdout.decode())
        arch = data["architecture"]
        self.assertIn("Clean Architecture", arch["architecture_overview"])
        self.assertIn("src/", arch["module_structure"])
        self.assertEqual(len(arch["patterns"]), 2)
        self.assertEqual(arch["patterns"][0]["name"], "Either Monad")
        self.assertIn("typescript", arch["patterns"][0]["snippet_lang"])
        self.assertIn("Never import domain", arch["conventions"])
        self.assertEqual(len(arch["layers"]), 4)
        self.assertEqual(len(arch["cross_cuts"]), 2)
        self.assertEqual(len(arch["dependency_direction_rules"]), 3)
        self.assertIn("mermaid", arch["dependency_overview"])

    def test_read_docs_missing_overview_exits_1(self):
        # Only create architecture.md.
        docs_dir = self.install_root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "architecture.md").write_text(_ARCHITECTURE_MD_FIXTURE, encoding="utf-8")
        proc = _run_configure(
            self.devforge_dir,
            "--install-root", str(self.install_root),
            "read-docs",
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"overview.md not found", proc.stderr)

    def test_read_docs_missing_architecture_exits_1(self):
        # Only create overview.md.
        docs_dir = self.install_root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "overview.md").write_text(_OVERVIEW_MD_FIXTURE, encoding="utf-8")
        proc = _run_configure(
            self.devforge_dir,
            "--install-root", str(self.install_root),
            "read-docs",
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"architecture.md not found", proc.stderr)

    def test_read_docs_missing_section_emits_empty(self):
        """Docs without a section emit empty string/list — no error."""
        docs_dir = self.install_root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        # Minimal docs without Navigation Guards or Application Routes.
        minimal_overview = "# Overview\n\n## Purpose\n\nMinimal project.\n"
        minimal_arch = "# Arch\n\n## Architecture Overview\n\nSimple.\n"
        (docs_dir / "overview.md").write_text(minimal_overview, encoding="utf-8")
        (docs_dir / "architecture.md").write_text(minimal_arch, encoding="utf-8")
        proc = _run_configure(
            self.devforge_dir,
            "--install-root", str(self.install_root),
            "read-docs",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(proc.stdout.decode())
        self.assertEqual(data["overview"]["navigation_guards"], [])
        self.assertEqual(data["overview"]["application_routes"], [])
        self.assertEqual(data["architecture"]["layers"], [])


# ---------------------------------------------------------------------------
# 6. read-manifests tests (~3)
# ---------------------------------------------------------------------------


class ReadManifestsTests(_EnvIsolationMixin, unittest.TestCase):

    def _write_index(self, packages):
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        index = {"version": 1, "packages": packages}
        (self.devforge_dir / "index.json").write_text(
            json.dumps(index), encoding="utf-8"
        )

    def test_two_packages_emits_two_records(self):
        self._write_index([
            {
                "path": "apps/app-web",
                "manifest": "package.json",
                "manifest_scripts": {"build": "vite build", "lint": "eslint ."},
                "manifest_dependencies": {"vue": "^3.0.0"},
                "manifest_dev_dependencies": {"vite": "^5.0.0"},
                "files": [],
            },
            {
                "path": "services/api",
                "manifest": "pyproject.toml",
                "manifest_scripts": {},
                "manifest_dependencies": {},
                "manifest_dev_dependencies": {},
                "files": [],
            },
        ])
        proc = _run_configure(self.devforge_dir, "read-manifests")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(proc.stdout.decode())
        self.assertEqual(len(data["packages"]), 2)
        self.assertEqual(data["packages"][0]["path"], "apps/app-web")
        self.assertEqual(data["packages"][0]["scripts"]["build"], "vite build")

    def test_build_tool_hint_vite(self):
        self._write_index([
            {
                "path": "apps/app-web",
                "manifest": "package.json",
                "manifest_scripts": {},
                "manifest_dependencies": {},
                "manifest_dev_dependencies": {"vite": "^5.0.0"},
                "files": [],
            },
        ])
        proc = _run_configure(self.devforge_dir, "read-manifests")
        data = json.loads(proc.stdout.decode())
        self.assertEqual(data["packages"][0]["build_tool_hint"], "vite")

    def test_build_tool_hint_webpack(self):
        self._write_index([
            {
                "path": "apps/app-web",
                "manifest": "package.json",
                "manifest_scripts": {},
                "manifest_dependencies": {},
                "manifest_dev_dependencies": {"webpack": "^5.0.0"},
                "files": [],
            },
        ])
        proc = _run_configure(self.devforge_dir, "read-manifests")
        data = json.loads(proc.stdout.decode())
        self.assertEqual(data["packages"][0]["build_tool_hint"], "webpack")

    def test_build_tool_hint_null_when_unknown(self):
        self._write_index([
            {
                "path": "services/api",
                "manifest": "pyproject.toml",
                "manifest_scripts": {},
                "manifest_dependencies": {"fastapi": "^0.100.0"},
                "manifest_dev_dependencies": {},
                "files": [],
            },
        ])
        proc = _run_configure(self.devforge_dir, "read-manifests")
        data = json.loads(proc.stdout.decode())
        self.assertIsNone(data["packages"][0]["build_tool_hint"])

    def test_missing_index_exits_1(self):
        # No index.json.
        proc = _run_configure(self.devforge_dir, "read-manifests")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"index.json not found", proc.stderr)

    def test_dict_shape_packages_normalized(self):
        """index.json with dict-of-path packages (current /init-forge format) parses.

        Regression: index_helper.py emits packages as a dict keyed by
        path; original read-manifests assumed list-of-records and
        returned empty.
        """
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        index = {
            "version": 1,
            "packages": {
                "apps/app-web": {
                    "manifest_file": "package.json",
                    "scripts": {"build": "vite build"},
                    "manifest_deps": [
                        {"name": "vue", "version": "^3.0.0"},
                        {"name": "vite", "version": "^5.0.0"},
                    ],
                    "files": [],
                },
            },
        }
        (self.devforge_dir / "index.json").write_text(
            json.dumps(index), encoding="utf-8"
        )
        proc = _run_configure(self.devforge_dir, "read-manifests")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(proc.stdout.decode())
        self.assertEqual(len(data["packages"]), 1)
        self.assertEqual(data["packages"][0]["path"], "apps/app-web")
        self.assertEqual(data["packages"][0]["scripts"]["build"], "vite build")

    def test_manifest_deps_list_normalized_to_dict(self):
        """index_helper.py emits manifest_deps: [{name, version}, ...].

        Regression: original read-manifests expected manifest_dependencies
        as a name→version dict and returned empty deps when the list-shape
        was the only signal. build_tool_hint also derives from the
        normalized dict.
        """
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        index = {
            "version": 1,
            "packages": {
                "apps/app-web": {
                    "manifest_file": "package.json",
                    "scripts": {},
                    "manifest_deps": [
                        {"name": "vite", "version": "^5.0.0"},
                        {"name": "vue", "version": "^3.0.0"},
                    ],
                    "files": [],
                },
            },
        }
        (self.devforge_dir / "index.json").write_text(
            json.dumps(index), encoding="utf-8"
        )
        proc = _run_configure(self.devforge_dir, "read-manifests")
        data = json.loads(proc.stdout.decode())
        # manifest_deps list normalized to dict
        self.assertEqual(data["packages"][0]["dependencies"]["vite"], "^5.0.0")
        self.assertEqual(data["packages"][0]["dependencies"]["vue"], "^3.0.0")
        # build_tool_hint derives correctly from the normalized list
        self.assertEqual(data["packages"][0]["build_tool_hint"], "vite")


# ---------------------------------------------------------------------------
# 7. read-configs tests (~4)
# ---------------------------------------------------------------------------


class ReadConfigsTests(_EnvIsolationMixin, unittest.TestCase):

    def _write_index(self, packages):
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        index = {"version": 1, "packages": packages}
        (self.devforge_dir / "index.json").write_text(
            json.dumps(index), encoding="utf-8"
        )

    def _write_config_file(self, rel_path, contents):
        """Write a file at install_root / rel_path."""
        abs_path = self.install_root / rel_path
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(contents, bytes):
            abs_path.write_bytes(contents)
        else:
            abs_path.write_text(contents, encoding="utf-8")

    def test_vite_config_matched_and_read(self):
        self._write_index([
            {
                "path": "apps/app-web",
                "manifest": "package.json",
                "manifest_scripts": {},
                "manifest_dependencies": {},
                "manifest_dev_dependencies": {},
                "files": ["vite.config.ts", "src/main.ts"],
            },
        ])
        vite_contents = "export default defineConfig({ server: { port: 3000 } })"
        self._write_config_file("apps/app-web/vite.config.ts", vite_contents)

        proc = _run_configure(
            self.devforge_dir,
            "--install-root", str(self.install_root),
            "read-configs",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(proc.stdout.decode())
        self.assertEqual(len(data["matched_files"]), 1)
        self.assertEqual(data["matched_files"][0]["basename"], "vite.config.ts")
        self.assertIn("port: 3000", data["matched_files"][0]["contents"])
        self.assertFalse(data["matched_files"][0]["truncated"])

    def test_file_over_10kb_truncated(self):
        self._write_index([
            {
                "path": ".",
                "manifest": "package.json",
                "manifest_scripts": {},
                "manifest_dependencies": {},
                "manifest_dev_dependencies": {},
                "files": [".env"],
            },
        ])
        # Write > 10 KB file.
        large_contents = "KEY=VALUE\n" * 1200  # ~12 KB
        self._write_config_file(".env", large_contents)

        proc = _run_configure(
            self.devforge_dir,
            "--install-root", str(self.install_root),
            "read-configs",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(proc.stdout.decode())
        self.assertEqual(len(data["matched_files"]), 1)
        self.assertTrue(data["matched_files"][0]["truncated"])
        self.assertLessEqual(len(data["matched_files"][0]["contents"]), 10240 + 10)

    def test_no_matches_emits_empty_array(self):
        """No config files → emits {"matched_files": []}, exit 0."""
        self._write_index([
            {
                "path": "apps/app-web",
                "manifest": "package.json",
                "manifest_scripts": {},
                "manifest_dependencies": {},
                "manifest_dev_dependencies": {},
                "files": ["src/main.ts", "src/App.vue"],  # no config files
            },
        ])
        proc = _run_configure(
            self.devforge_dir,
            "--install-root", str(self.install_root),
            "read-configs",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(proc.stdout.decode())
        self.assertEqual(data["matched_files"], [])

    def test_dict_shape_packages_walked(self):
        """index.json with dict-of-path packages (current /init-forge format).

        Regression: original read-configs assumed list-of-records and
        returned empty when index_helper.py emitted dict-of-path.
        """
        self.devforge_dir.mkdir(parents=True, exist_ok=True)
        index = {
            "version": 1,
            "packages": {
                "apps/app-web": {
                    "manifest_file": "package.json",
                    "files": ["vite.config.ts", "src/main.ts"],
                },
            },
        }
        (self.devforge_dir / "index.json").write_text(
            json.dumps(index), encoding="utf-8"
        )
        self._write_config_file(
            "apps/app-web/vite.config.ts",
            "export default { server: { port: 3000 } }",
        )
        proc = _run_configure(
            self.devforge_dir,
            "--install-root", str(self.install_root),
            "read-configs",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(proc.stdout.decode())
        self.assertEqual(len(data["matched_files"]), 1)
        self.assertEqual(data["matched_files"][0]["basename"], "vite.config.ts")

    def test_wrapper_mode_prepends_project_root(self):
        """Wrapper-mode: source files at <install_root>/<project_root>/...

        Regression: read-configs constructed install_root/file_rel and
        skipped the project_root segment. On testForge20 (wrapper) all
        88 config files were silently OSError-skipped, returning empty.
        """
        # Write init.yaml signaling wrapper mode + project_root="src-tree".
        (self.devforge_dir / "init.yaml").write_text(
            'workspace_mode: "wrapper"\n'
            'project_root: "src-tree"\n'
            'project_state: "brownfield"\n'
            'default_branch: "main"\n'
            'packages_detected: []\n',
            encoding="utf-8",
        )
        # Write index.json with file paths relative to project_root.
        index = {
            "version": 1,
            "packages": {
                "apps/app-web": {
                    "manifest_file": "package.json",
                    "files": ["vite.config.ts"],
                },
            },
        }
        (self.devforge_dir / "index.json").write_text(
            json.dumps(index), encoding="utf-8"
        )
        # File lives at install_root/src-tree/apps/app-web/vite.config.ts.
        self._write_config_file(
            "src-tree/apps/app-web/vite.config.ts",
            "// wrapper-mode config",
        )
        proc = _run_configure(
            self.devforge_dir,
            "--install-root", str(self.install_root),
            "read-configs",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(proc.stdout.decode())
        # File should be matched + read despite wrapper-mode prefix.
        self.assertEqual(len(data["matched_files"]), 1)
        self.assertIn("wrapper-mode config", data["matched_files"][0]["contents"])

    def test_standalone_mode_no_prefix(self):
        """Standalone mode: source files at <install_root>/... (no prefix)."""
        (self.devforge_dir / "init.yaml").write_text(
            'workspace_mode: "standalone"\n'
            'project_root: "."\n'
            'project_state: "brownfield"\n'
            'default_branch: "main"\n'
            'packages_detected: []\n',
            encoding="utf-8",
        )
        index = {
            "version": 1,
            "packages": {
                ".": {
                    "manifest_file": "package.json",
                    "files": ["vite.config.ts"],
                },
            },
        }
        (self.devforge_dir / "index.json").write_text(
            json.dumps(index), encoding="utf-8"
        )
        self._write_config_file("vite.config.ts", "// standalone")
        proc = _run_configure(
            self.devforge_dir,
            "--install-root", str(self.install_root),
            "read-configs",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(proc.stdout.decode())
        self.assertEqual(len(data["matched_files"]), 1)

    def test_missing_index_exits_1(self):
        proc = _run_configure(
            self.devforge_dir,
            "--install-root", str(self.install_root),
            "read-configs",
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"index.json not found", proc.stderr)

    def test_non_config_files_not_matched(self):
        self._write_index([
            {
                "path": "apps/app-web",
                "manifest": "package.json",
                "manifest_scripts": {},
                "manifest_dependencies": {},
                "manifest_dev_dependencies": {},
                "files": [
                    "src/main.ts",
                    "vite.config.ts",
                    "src/components/Button.vue",
                ],
            },
        ])
        self._write_config_file("apps/app-web/vite.config.ts", "export default {}")
        proc = _run_configure(
            self.devforge_dir,
            "--install-root", str(self.install_root),
            "read-configs",
        )
        data = json.loads(proc.stdout.decode())
        # Only vite.config.ts matched.
        self.assertEqual(len(data["matched_files"]), 1)
        self.assertEqual(data["matched_files"][0]["basename"], "vite.config.ts")


# ---------------------------------------------------------------------------
# 8. Build tool hint derivation (pure function tests)
# ---------------------------------------------------------------------------


class BuildToolHintTests(unittest.TestCase):

    def test_vite_in_dev_deps(self):
        hint = configure_helper._derive_build_tool_hint({}, {"vite": "^5.0.0"})
        self.assertEqual(hint, "vite")

    def test_webpack_in_deps(self):
        hint = configure_helper._derive_build_tool_hint({"webpack": "^5.0.0"}, {})
        self.assertEqual(hint, "webpack")

    def test_rollup_detected(self):
        hint = configure_helper._derive_build_tool_hint({"rollup": "^3.0.0"}, {})
        self.assertEqual(hint, "rollup")

    def test_next_detected(self):
        hint = configure_helper._derive_build_tool_hint({"next": "13.0.0"}, {})
        self.assertEqual(hint, "next")

    def test_tsc_detected(self):
        hint = configure_helper._derive_build_tool_hint({"tsc": "^5.0.0"}, {})
        self.assertEqual(hint, "tsc")

    def test_no_build_tool_returns_none(self):
        hint = configure_helper._derive_build_tool_hint(
            {"fastapi": "^0.100.0"}, {"pytest": "^7.0.0"}
        )
        self.assertIsNone(hint)

    def test_vite_takes_priority_over_tsc(self):
        """vite appears before tsc in _BUILD_TOOL_HINTS — must win."""
        hint = configure_helper._derive_build_tool_hint(
            {"tsc": "^5.0.0"}, {"vite": "^5.0.0"}
        )
        self.assertEqual(hint, "vite")

    def test_empty_deps_returns_none(self):
        hint = configure_helper._derive_build_tool_hint({}, {})
        self.assertIsNone(hint)


# ===========================================================================
# STEP 2 TESTS — setters, _load/_dump/_state_transaction, validation helpers
# ===========================================================================


# ---------------------------------------------------------------------------
# 9. _load / _dump helper tests (~5)
# ---------------------------------------------------------------------------


class LoadDumpTests(_EnvIsolationMixin, unittest.TestCase):

    def test_load_missing_returns_defaults(self):
        """_load on a missing file returns default_state() (not an error)."""
        state = configure_helper._load(self.devforge_dir)
        self.assertEqual(state, configure_helper.default_state())

    def test_dump_then_load_round_trip(self):
        """_dump writes yaml; _load reads it back identically."""
        state = configure_helper.default_state()
        state["project_name"] = "round-trip-test"
        state["languages"] = ["TypeScript", "Python"]
        configure_helper._dump(state, self.devforge_dir)
        state2 = configure_helper._load(self.devforge_dir)
        self.assertEqual(state, state2)

    def test_dump_creates_directory_if_absent(self):
        nested = self.install_root / "nested" / ".devforge"
        self.assertFalse(nested.exists())
        state = configure_helper.default_state()
        configure_helper._dump(state, nested)
        self.assertTrue((nested / configure_helper.OUTPUT_FILE_NAME).exists())

    def test_load_malformed_raises_yaml_parse_error(self):
        self.output_file.write_text("bogus: [unclosed\n", encoding="utf-8")
        with self.assertRaises(configure_helper.YamlParseError):
            configure_helper._load(self.devforge_dir)

    def test_dump_overwrites_existing(self):
        state1 = configure_helper.default_state()
        state1["project_name"] = "first"
        configure_helper._dump(state1, self.devforge_dir)
        state2 = configure_helper.default_state()
        state2["project_name"] = "second"
        configure_helper._dump(state2, self.devforge_dir)
        loaded = configure_helper._load(self.devforge_dir)
        self.assertEqual(loaded["project_name"], "second")


# ---------------------------------------------------------------------------
# 10. _state_transaction tests (~3)
# ---------------------------------------------------------------------------


class StateTransactionTests(_EnvIsolationMixin, unittest.TestCase):

    def test_transaction_writes_on_clean_exit(self):
        with configure_helper._state_transaction(self.devforge_dir) as state:
            state["project_name"] = "written"
        loaded = configure_helper._load(self.devforge_dir)
        self.assertEqual(loaded["project_name"], "written")

    def test_transaction_does_not_write_on_exception(self):
        # Write a known initial state.
        initial = configure_helper.default_state()
        initial["project_name"] = "initial"
        configure_helper._dump(initial, self.devforge_dir)
        try:
            with configure_helper._state_transaction(self.devforge_dir) as state:
                state["project_name"] = "mutated"
                raise RuntimeError("abort")
        except RuntimeError:
            pass
        loaded = configure_helper._load(self.devforge_dir)
        # Must remain "initial" since the transaction was aborted.
        self.assertEqual(loaded["project_name"], "initial")

    def test_transaction_creates_lock_file(self):
        with configure_helper._state_transaction(self.devforge_dir) as state:
            state["project_name"] = "x"
        lock_path = configure_helper._lock_file_path(self.devforge_dir)
        self.assertTrue(lock_path.exists())


# ---------------------------------------------------------------------------
# 11. Validation helper unit tests (~20)
# ---------------------------------------------------------------------------


class ValidateScalarTests(unittest.TestCase):

    def test_valid_string_returned_stripped(self):
        result = configure_helper._validate_scalar("  hello  ", "field")
        self.assertEqual(result, "hello")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError) as ctx:
            configure_helper._validate_scalar("", "myfield")
        self.assertIn("myfield", str(ctx.exception))
        self.assertIn("cannot be empty", str(ctx.exception))

    def test_whitespace_only_raises(self):
        with self.assertRaises(ValueError):
            configure_helper._validate_scalar("   ", "myfield")

    def test_nonempty_string_no_strip_internal(self):
        result = configure_helper._validate_scalar("hello world", "field")
        self.assertEqual(result, "hello world")


class ValidateEnumTests(unittest.TestCase):

    def test_valid_enum_value_returned(self):
        result = configure_helper._validate_enum("Strict", "workflow_enforcement")
        self.assertEqual(result, "Strict")

    def test_invalid_enum_value_raises(self):
        with self.assertRaises(ValueError) as ctx:
            configure_helper._validate_enum("InvalidValue", "workflow_enforcement")
        self.assertIn("workflow_enforcement", str(ctx.exception))
        self.assertIn("invalid value", str(ctx.exception))
        self.assertIn("InvalidValue", str(ctx.exception))

    def test_empty_value_raises(self):
        with self.assertRaises(ValueError):
            configure_helper._validate_enum("", "ai_attribution")

    def test_case_insensitive_match_returns_canonical(self):
        """Lower/upper-cased input normalizes to the canonical exact-case member.

        LLM running /configure may lowercase AskUserQuestion option labels
        (saw 'Strict' → 'strict' in real run); validator now accepts and
        normalizes to the canonical 'Strict'.
        """
        for raw in ("strict", "STRICT", "Strict", "sTrIcT"):
            result = configure_helper._validate_enum(raw, "workflow_enforcement")
            self.assertEqual(
                result,
                "Strict",
                "input {0!r} must normalize to 'Strict'".format(raw),
            )

    def test_case_insensitive_no_match_still_raises(self):
        # 'Mostly' is not in workflow_enforcement enum at any case.
        with self.assertRaises(ValueError):
            configure_helper._validate_enum("Mostly", "workflow_enforcement")


class ValidateStringArrayTests(unittest.TestCase):

    def test_single_item(self):
        result = configure_helper._validate_string_array("TypeScript", "languages")
        self.assertEqual(result, ["TypeScript"])

    def test_multiple_items_comma_sep(self):
        result = configure_helper._validate_string_array("TypeScript,Python,Go", "languages")
        self.assertEqual(result, ["TypeScript", "Python", "Go"])

    def test_whitespace_trimmed_per_item(self):
        result = configure_helper._validate_string_array(" A , B , C ", "languages")
        self.assertEqual(result, ["A", "B", "C"])

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError) as ctx:
            configure_helper._validate_string_array("", "languages")
        self.assertIn("languages", str(ctx.exception))

    def test_empty_item_in_middle_raises(self):
        with self.assertRaises(ValueError) as ctx:
            configure_helper._validate_string_array("a,,b", "languages")
        self.assertIn("non-empty", str(ctx.exception))

    def test_whitespace_only_item_raises(self):
        with self.assertRaises(ValueError):
            configure_helper._validate_string_array("a, ,b", "languages")

    def test_json_array_form_accepted(self):
        """JSON-array input form: starts with `[`, ends with `]`."""
        result = configure_helper._validate_string_array(
            '["TypeScript", "Python", "Go"]', "languages"
        )
        self.assertEqual(result, ["TypeScript", "Python", "Go"])

    def test_json_array_preserves_internal_commas(self):
        """JSON-array form lets items contain literal commas.

        Regression: comma-sep split breaks on TypeScript generic syntax
        like `Either<DataError, T>`. JSON-array form bypasses the split.
        """
        result = configure_helper._validate_string_array(
            '["Either<DataError, T> via fp-ts", "BLoC notifications"]',
            "error_handlings",
        )
        self.assertEqual(
            result,
            ["Either<DataError, T> via fp-ts", "BLoC notifications"],
        )

    def test_json_array_single_item(self):
        result = configure_helper._validate_string_array('["one"]', "languages")
        self.assertEqual(result, ["one"])

    def test_malformed_json_array_raises(self):
        # Starts and ends with brackets (so JSON-detection fires) but the
        # body is not valid JSON: unquoted identifiers.
        with self.assertRaises(ValueError) as ctx:
            configure_helper._validate_string_array("[a, b]", "languages")
        self.assertIn("languages", str(ctx.exception))

    def test_json_array_with_non_string_items_raises(self):
        with self.assertRaises(ValueError) as ctx:
            configure_helper._validate_string_array('["a", 42]', "languages")
        self.assertIn("languages", str(ctx.exception))

    def test_json_array_empty_item_raises(self):
        with self.assertRaises(ValueError) as ctx:
            configure_helper._validate_string_array('["a", "", "b"]', "languages")
        self.assertIn("non-empty", str(ctx.exception))


class ValidatePathValueTests(unittest.TestCase):

    def test_valid_path_returned(self):
        result = configure_helper._validate_path_value("apps/web", "path")
        self.assertEqual(result, "apps/web")

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            configure_helper._validate_path_value("", "path")

    def test_newline_in_path_raises(self):
        with self.assertRaises(ValueError) as ctx:
            configure_helper._validate_path_value("apps\nweb", "path")
        self.assertIn("newline", str(ctx.exception))

    def test_carriage_return_in_path_raises(self):
        with self.assertRaises(ValueError):
            configure_helper._validate_path_value("apps\rweb", "path")


class ValidateVerbatimTests(unittest.TestCase):

    def test_single_line_accepted(self):
        result = configure_helper._validate_verbatim("single line", "project_structure")
        self.assertEqual(result, "single line")

    def test_multiline_content_preserved(self):
        text = "apps/\n  web/\npackages/"
        result = configure_helper._validate_verbatim(text, "project_structure")
        self.assertEqual(result, text)

    def test_leading_trailing_whitespace_preserved(self):
        # _validate_verbatim does NOT strip — it preserves exactly what's passed.
        text = "  indented content  "
        result = configure_helper._validate_verbatim(text, "project_structure")
        self.assertEqual(result, text)

    def test_whitespace_only_raises(self):
        with self.assertRaises(ValueError):
            configure_helper._validate_verbatim("   \n\t  ", "project_structure")

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            configure_helper._validate_verbatim("", "project_structure")


# ---------------------------------------------------------------------------
# 12. Scalar setter subprocess tests (~18: 3 identity + 1 stack + 3 AC)
# ---------------------------------------------------------------------------


class SetProjectNameTests(_EnvIsolationMixin, unittest.TestCase):

    def test_happy_path_exit_0_and_yaml_updated(self):
        proc = _run_configure(self.devforge_dir, "set-project-name", "my-app")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_name"], "my-app")

    def test_empty_value_exits_2(self):
        proc = _run_configure(self.devforge_dir, "set-project-name", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"project_name", proc.stderr)
        self.assertIn(b"cannot be empty", proc.stderr)

    def test_whitespace_only_exits_2(self):
        proc = _run_configure(self.devforge_dir, "set-project-name", "   ")
        self.assertEqual(proc.returncode, 2)

    def test_round_trip(self):
        _run_configure(self.devforge_dir, "set-project-name", "round-trip")
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_name"], "round-trip")

    def test_overwrite_prior_value(self):
        _run_configure(self.devforge_dir, "set-project-name", "first")
        _run_configure(self.devforge_dir, "set-project-name", "second")
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_name"], "second")

    def test_strips_leading_trailing_whitespace(self):
        _run_configure(self.devforge_dir, "set-project-name", "  my-app  ")
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_name"], "my-app")


class SetProjectDescriptionTests(_EnvIsolationMixin, unittest.TestCase):

    def test_happy_path(self):
        proc = _run_configure(self.devforge_dir, "set-project-description", "A test project")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_description"], "A test project")

    def test_empty_exits_2(self):
        proc = _run_configure(self.devforge_dir, "set-project-description", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"project_description", proc.stderr)

    def test_round_trip(self):
        _run_configure(self.devforge_dir, "set-project-description", "My Description")
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_description"], "My Description")


class SetProjectTypeTests(_EnvIsolationMixin, unittest.TestCase):

    def test_happy_path(self):
        proc = _run_configure(self.devforge_dir, "set-project-type", "Web Application")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_type"], "Web Application")

    def test_empty_exits_2(self):
        proc = _run_configure(self.devforge_dir, "set-project-type", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"project_type", proc.stderr)

    def test_round_trip(self):
        _run_configure(self.devforge_dir, "set-project-type", "CLI Tool")
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_type"], "CLI Tool")


class SetPrimaryLanguageTests(_EnvIsolationMixin, unittest.TestCase):

    def test_happy_path(self):
        proc = _run_configure(self.devforge_dir, "set-primary-language", "TypeScript")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["primary_language"], "TypeScript")

    def test_empty_exits_2(self):
        proc = _run_configure(self.devforge_dir, "set-primary-language", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"primary_language", proc.stderr)

    def test_round_trip(self):
        _run_configure(self.devforge_dir, "set-primary-language", "Python")
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["primary_language"], "Python")


class SetAcRuntimeScalarTests(_EnvIsolationMixin, unittest.TestCase):

    def test_set_ac_runtime_url_happy(self):
        proc = _run_configure(self.devforge_dir, "set-ac-runtime-url", "http://localhost:3000")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["ac_runtime_url"], "http://localhost:3000")

    def test_set_ac_runtime_url_empty_exits_2(self):
        proc = _run_configure(self.devforge_dir, "set-ac-runtime-url", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"ac_runtime_url", proc.stderr)

    def test_set_ac_runtime_api_base_happy(self):
        proc = _run_configure(self.devforge_dir, "set-ac-runtime-api-base", "http://localhost:4000")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["ac_runtime_api_base"], "http://localhost:4000")

    def test_set_ac_runtime_api_base_empty_exits_2(self):
        proc = _run_configure(self.devforge_dir, "set-ac-runtime-api-base", "")
        self.assertEqual(proc.returncode, 2)

    def test_set_ac_runtime_cli_command_happy(self):
        proc = _run_configure(self.devforge_dir, "set-ac-runtime-cli-command", "npm run start")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["ac_runtime_cli_command"], "npm run start")

    def test_set_ac_runtime_cli_command_empty_exits_2(self):
        proc = _run_configure(self.devforge_dir, "set-ac-runtime-cli-command", "")
        self.assertEqual(proc.returncode, 2)


# ---------------------------------------------------------------------------
# 13. String array setter tests (~18)
# ---------------------------------------------------------------------------


class SetLanguagesTests(_EnvIsolationMixin, unittest.TestCase):

    def test_single_item(self):
        proc = _run_configure(self.devforge_dir, "set-languages", "TypeScript")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["languages"], ["TypeScript"])

    def test_multiple_comma_sep(self):
        proc = _run_configure(self.devforge_dir, "set-languages", "TypeScript,Python,Go")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["languages"], ["TypeScript", "Python", "Go"])

    def test_whitespace_trimmed_per_item(self):
        proc = _run_configure(self.devforge_dir, "set-languages", " TypeScript , Python ")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["languages"], ["TypeScript", "Python"])

    def test_empty_item_rejected(self):
        proc = _run_configure(self.devforge_dir, "set-languages", "a,,b")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"non-empty", proc.stderr)

    def test_second_set_replaces_first(self):
        _run_configure(self.devforge_dir, "set-languages", "TypeScript")
        _run_configure(self.devforge_dir, "set-languages", "Python,Go")
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["languages"], ["Python", "Go"])

    def test_empty_string_exits_2(self):
        proc = _run_configure(self.devforge_dir, "set-languages", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"languages", proc.stderr)


class SetStringArrayVariousFieldsTests(_EnvIsolationMixin, unittest.TestCase):
    """Test a representative sample of the remaining 6 string_array setters."""

    def _set_and_reload(self, subcommand, value):
        proc = _run_configure(self.devforge_dir, subcommand, value)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        return configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))

    def test_frameworks(self):
        state = self._set_and_reload("set-frameworks", "Vue,React")
        self.assertEqual(state["frameworks"], ["Vue", "React"])

    def test_architectures(self):
        state = self._set_and_reload("set-architectures", "Clean Architecture")
        self.assertEqual(state["architectures"], ["Clean Architecture"])

    def test_error_handlings(self):
        state = self._set_and_reload("set-error-handlings", "Either monad,exceptions")
        self.assertEqual(state["error_handlings"], ["Either monad", "exceptions"])

    def test_api_layers(self):
        state = self._set_and_reload("set-api-layers", "REST,tRPC")
        self.assertEqual(state["api_layers"], ["REST", "tRPC"])

    def test_testings(self):
        state = self._set_and_reload("set-testings", "Vitest,Playwright")
        self.assertEqual(state["testings"], ["Vitest", "Playwright"])

    def test_build_tools(self):
        state = self._set_and_reload("set-build-tools", "Vite,tsc")
        self.assertEqual(state["build_tools"], ["Vite", "tsc"])

    def test_build_commands(self):
        state = self._set_and_reload("set-build-commands", "npm run build")
        self.assertEqual(state["build_commands"], ["npm run build"])

    def test_type_check_commands(self):
        state = self._set_and_reload("set-type-check-commands", "npm run typecheck")
        self.assertEqual(state["type_check_commands"], ["npm run typecheck"])

    def test_lint_commands(self):
        state = self._set_and_reload("set-lint-commands", "npm run lint,eslint .")
        self.assertEqual(state["lint_commands"], ["npm run lint", "eslint ."])

    def test_empty_value_exits_2_for_frameworks(self):
        proc = _run_configure(self.devforge_dir, "set-frameworks", "")
        self.assertEqual(proc.returncode, 2)


# ---------------------------------------------------------------------------
# 14. add-package-stack tests (~12)
# ---------------------------------------------------------------------------


class AddPackageStackTests(_EnvIsolationMixin, unittest.TestCase):

    def test_required_path_and_language_happy(self):
        proc = _run_configure(
            self.devforge_dir,
            "add-package-stack",
            "--path", "apps/web",
            "--language", "TypeScript",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(len(state["package_stacks"]), 1)
        self.assertEqual(state["package_stacks"][0]["path"], "apps/web")
        self.assertEqual(state["package_stacks"][0]["language"], "TypeScript")

    def test_optional_fields_default_to_null(self):
        _run_configure(
            self.devforge_dir,
            "add-package-stack",
            "--path", "apps/web",
            "--language", "TypeScript",
        )
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        record = state["package_stacks"][0]
        self.assertIsNone(record["framework"])
        self.assertIsNone(record["build_tool"])
        self.assertIsNone(record["build_command"])
        self.assertIsNone(record["type_check_command"])
        self.assertIsNone(record["lint_command"])

    def test_all_optional_fields_provided(self):
        proc = _run_configure(
            self.devforge_dir,
            "add-package-stack",
            "--path", "apps/web",
            "--language", "TypeScript",
            "--framework", "Vue",
            "--build-tool", "Vite",
            "--build-command", "npm run build",
            "--type-check-command", "npm run typecheck",
            "--lint-command", "npm run lint",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        record = state["package_stacks"][0]
        self.assertEqual(record["framework"], "Vue")
        self.assertEqual(record["build_tool"], "Vite")
        self.assertEqual(record["build_command"], "npm run build")
        self.assertEqual(record["type_check_command"], "npm run typecheck")
        self.assertEqual(record["lint_command"], "npm run lint")

    def test_missing_path_exits_2(self):
        proc = _run_configure(
            self.devforge_dir,
            "add-package-stack",
            "--language", "TypeScript",
        )
        self.assertNotEqual(proc.returncode, 0)

    def test_missing_language_exits_2(self):
        proc = _run_configure(
            self.devforge_dir,
            "add-package-stack",
            "--path", "apps/web",
        )
        self.assertNotEqual(proc.returncode, 0)

    def test_three_calls_accumulate_three_records(self):
        for i in range(3):
            proc = _run_configure(
                self.devforge_dir,
                "add-package-stack",
                "--path", "pkg/pkg{0}".format(i),
                "--language", "Python",
            )
            self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(len(state["package_stacks"]), 3)
        paths = [r["path"] for r in state["package_stacks"]]
        self.assertEqual(paths, ["pkg/pkg0", "pkg/pkg1", "pkg/pkg2"])

    def test_path_with_newline_rejected(self):
        proc = _run_configure(
            self.devforge_dir,
            "add-package-stack",
            "--path", "apps\nweb",
            "--language", "TypeScript",
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"newline", proc.stderr)

    def test_empty_language_rejected(self):
        proc = _run_configure(
            self.devforge_dir,
            "add-package-stack",
            "--path", "apps/web",
            "--language", "",
        )
        self.assertEqual(proc.returncode, 2)

    def test_empty_path_rejected(self):
        proc = _run_configure(
            self.devforge_dir,
            "add-package-stack",
            "--path", "",
            "--language", "TypeScript",
        )
        self.assertEqual(proc.returncode, 2)

    def test_empty_optional_field_rejected(self):
        proc = _run_configure(
            self.devforge_dir,
            "add-package-stack",
            "--path", "apps/web",
            "--language", "TypeScript",
            "--framework", "",
        )
        self.assertEqual(proc.returncode, 2)


# ---------------------------------------------------------------------------
# 15. Verbatim setter tests (~9)
# ---------------------------------------------------------------------------


class SetProjectStructureTests(_EnvIsolationMixin, unittest.TestCase):

    def test_single_line_happy(self):
        proc = _run_configure(
            self.devforge_dir, "set-project-structure", "--text", "apps/ packages/"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_structure"], "apps/ packages/")

    def test_multiline_content_preserved_via_subprocess(self):
        """Multi-line content passed via --text round-trips through emit/parse."""
        text = "apps/\n  web/\npackages/"
        proc = _run_configure(
            self.devforge_dir, "set-project-structure", "--text", text
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_structure"], text)

    def test_empty_text_exits_2(self):
        proc = _run_configure(
            self.devforge_dir, "set-project-structure", "--text", ""
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"project_structure", proc.stderr)

    def test_whitespace_only_exits_2(self):
        proc = _run_configure(
            self.devforge_dir, "set-project-structure", "--text", "   "
        )
        self.assertEqual(proc.returncode, 2)


class SetDevCommandsTests(_EnvIsolationMixin, unittest.TestCase):

    def test_happy_path(self):
        proc = _run_configure(
            self.devforge_dir, "set-dev-commands", "--text", "npm run dev"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["dev_commands"], "npm run dev")

    def test_multiline_round_trip(self):
        text = "npm run dev\nnpm run test\nnpm run lint"
        _run_configure(self.devforge_dir, "set-dev-commands", "--text", text)
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["dev_commands"], text)

    def test_empty_exits_2(self):
        proc = _run_configure(self.devforge_dir, "set-dev-commands", "--text", "")
        self.assertEqual(proc.returncode, 2)


class SetArchitectureDetailsTests(_EnvIsolationMixin, unittest.TestCase):

    def test_happy_path(self):
        proc = _run_configure(
            self.devforge_dir, "set-architecture-details", "--text", "Clean Architecture"
        )
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["architecture_details"], "Clean Architecture")

    def test_multiline_round_trip(self):
        text = "Layer 1: Domain\nLayer 2: Application\nLayer 3: Infrastructure"
        _run_configure(self.devforge_dir, "set-architecture-details", "--text", text)
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["architecture_details"], text)

    def test_empty_exits_2(self):
        proc = _run_configure(self.devforge_dir, "set-architecture-details", "--text", "")
        self.assertEqual(proc.returncode, 2)


# ---------------------------------------------------------------------------
# 16. Enum setter tests (~12)
# ---------------------------------------------------------------------------


class SetWorkflowEnforcementTests(_EnvIsolationMixin, unittest.TestCase):

    def test_strict_accepted(self):
        proc = _run_configure(self.devforge_dir, "set-workflow-enforcement", "Strict")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["workflow_enforcement"], "Strict")

    def test_moderate_accepted(self):
        proc = _run_configure(self.devforge_dir, "set-workflow-enforcement", "Moderate")
        self.assertEqual(proc.returncode, 0)

    def test_light_accepted(self):
        proc = _run_configure(self.devforge_dir, "set-workflow-enforcement", "Light")
        self.assertEqual(proc.returncode, 0)

    def test_invalid_rejected(self):
        proc = _run_configure(self.devforge_dir, "set-workflow-enforcement", "None")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"workflow_enforcement", proc.stderr)
        self.assertIn(b"invalid value", proc.stderr)

    def test_empty_rejected(self):
        proc = _run_configure(self.devforge_dir, "set-workflow-enforcement", "")
        self.assertEqual(proc.returncode, 2)


class SetAiAttributionTests(_EnvIsolationMixin, unittest.TestCase):

    def test_yes_accepted(self):
        proc = _run_configure(self.devforge_dir, "set-ai-attribution", "Yes")
        self.assertEqual(proc.returncode, 0)
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["ai_attribution"], "Yes")

    def test_no_accepted(self):
        proc = _run_configure(self.devforge_dir, "set-ai-attribution", "No")
        self.assertEqual(proc.returncode, 0)

    def test_invalid_rejected(self):
        proc = _run_configure(self.devforge_dir, "set-ai-attribution", "Maybe")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"ai_attribution", proc.stderr)


class SetClaudeTierTests(_EnvIsolationMixin, unittest.TestCase):

    def test_opus_accepted_for_think(self):
        proc = _run_configure(self.devforge_dir, "set-claude-tier-think", "Opus")
        self.assertEqual(proc.returncode, 0)
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["claude_tier_think"], "Opus")

    def test_sonnet_accepted_for_do(self):
        proc = _run_configure(self.devforge_dir, "set-claude-tier-do", "Sonnet")
        self.assertEqual(proc.returncode, 0)

    def test_haiku_accepted_for_verify(self):
        proc = _run_configure(self.devforge_dir, "set-claude-tier-verify", "Haiku")
        self.assertEqual(proc.returncode, 0)

    def test_other_accepted(self):
        # claude_tier_* fields accept any non-empty scalar (no enum
        # restriction) so users can name custom Claude routes via Q11
        # `Other` branch.
        proc = _run_configure(self.devforge_dir, "set-claude-tier-think", "Other")
        self.assertEqual(proc.returncode, 0)

    def test_custom_model_name_accepted(self):
        # Free-text model alias accepted (e.g., Bedrock route, self-hosted).
        proc = _run_configure(
            self.devforge_dir, "set-claude-tier-do", "claude-opus-4-7-bedrock"
        )
        self.assertEqual(proc.returncode, 0)
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["claude_tier_do"], "claude-opus-4-7-bedrock")

    def test_empty_rejected(self):
        proc = _run_configure(self.devforge_dir, "set-claude-tier-verify", "")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"claude_tier_verify", proc.stderr)


class SetAcVerificationModeTests(_EnvIsolationMixin, unittest.TestCase):

    def test_code_only_accepted(self):
        proc = _run_configure(self.devforge_dir, "set-ac-verification-mode", "code-only")
        self.assertEqual(proc.returncode, 0)
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["ac_verification_mode"], "code-only")

    def test_tests_accepted(self):
        proc = _run_configure(self.devforge_dir, "set-ac-verification-mode", "tests")
        self.assertEqual(proc.returncode, 0)

    def test_runtime_assisted_accepted(self):
        proc = _run_configure(self.devforge_dir, "set-ac-verification-mode", "runtime-assisted")
        self.assertEqual(proc.returncode, 0)

    def test_off_accepted(self):
        proc = _run_configure(self.devforge_dir, "set-ac-verification-mode", "off")
        self.assertEqual(proc.returncode, 0)

    def test_invalid_rejected(self):
        proc = _run_configure(self.devforge_dir, "set-ac-verification-mode", "full")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"ac_verification_mode", proc.stderr)


# ---------------------------------------------------------------------------
# 17. Round-trip integration tests (~5)
# ---------------------------------------------------------------------------


class RoundTripIntegrationTests(_EnvIsolationMixin, unittest.TestCase):

    def test_all_28_fields_set_reload_match(self):
        """Set all 28 fields via setters then reload and compare full state."""
        # Identity scalars
        _run_configure(self.devforge_dir, "set-project-name", "full-roundtrip")
        _run_configure(self.devforge_dir, "set-project-description", "Full round-trip test")
        _run_configure(self.devforge_dir, "set-project-type", "Web Application")
        # Stack scalar
        _run_configure(self.devforge_dir, "set-primary-language", "TypeScript")
        # Stack string_arrays
        _run_configure(self.devforge_dir, "set-languages", "TypeScript,Python")
        _run_configure(self.devforge_dir, "set-frameworks", "Vue,FastAPI")
        _run_configure(self.devforge_dir, "set-architectures", "Clean Architecture")
        _run_configure(self.devforge_dir, "set-project-natures", "web,backend")
        _run_configure(self.devforge_dir, "set-error-handlings", "Either monad")
        _run_configure(self.devforge_dir, "set-api-layers", "REST,tRPC")
        _run_configure(self.devforge_dir, "set-testings", "Vitest,Playwright")
        _run_configure(self.devforge_dir, "set-build-tools", "Vite,tsc")
        # Per-package string_arrays
        _run_configure(self.devforge_dir, "set-build-commands", "npm run build")
        _run_configure(self.devforge_dir, "set-type-check-commands", "npm run typecheck")
        _run_configure(self.devforge_dir, "set-lint-commands", "npm run lint")
        # Package stack record
        _run_configure(
            self.devforge_dir, "add-package-stack",
            "--path", "apps/web", "--language", "TypeScript",
            "--framework", "Vue", "--build-tool", "Vite",
        )
        # Verbatim docs
        _run_configure(self.devforge_dir, "set-project-structure", "--text", "apps/\npackages/")
        _run_configure(self.devforge_dir, "set-dev-commands", "--text", "npm run dev")
        _run_configure(self.devforge_dir, "set-architecture-details", "--text", "Clean Architecture")
        # Enums
        _run_configure(self.devforge_dir, "set-workflow-enforcement", "Strict")
        _run_configure(self.devforge_dir, "set-ai-attribution", "Yes")
        _run_configure(self.devforge_dir, "set-claude-tier-think", "Opus")
        _run_configure(self.devforge_dir, "set-claude-tier-do", "Sonnet")
        _run_configure(self.devforge_dir, "set-claude-tier-verify", "Haiku")
        _run_configure(self.devforge_dir, "set-ac-verification-mode", "tests")
        # AC runtime
        _run_configure(self.devforge_dir, "set-ac-runtime-url", "http://localhost:3000")
        _run_configure(self.devforge_dir, "set-ac-runtime-api-base", "http://localhost:4000")
        _run_configure(self.devforge_dir, "set-ac-runtime-cli-command", "npm run start")

        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_name"], "full-roundtrip")
        self.assertEqual(state["languages"], ["TypeScript", "Python"])
        self.assertEqual(state["frameworks"], ["Vue", "FastAPI"])
        self.assertEqual(state["project_natures"], ["web", "backend"])
        self.assertEqual(state["package_stacks"][0]["path"], "apps/web")
        self.assertEqual(state["project_structure"], "apps/\npackages/")
        self.assertEqual(state["workflow_enforcement"], "Strict")
        self.assertEqual(state["ac_runtime_url"], "http://localhost:3000")

    def test_scalar_setter_overwrite_prior(self):
        _run_configure(self.devforge_dir, "set-project-name", "first")
        _run_configure(self.devforge_dir, "set-project-name", "second")
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_name"], "second")

    def test_string_array_setter_replaces_not_appends(self):
        _run_configure(self.devforge_dir, "set-languages", "TypeScript")
        _run_configure(self.devforge_dir, "set-languages", "Python,Go")
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["languages"], ["Python", "Go"])

    def test_add_package_stack_accumulates(self):
        for i in range(3):
            _run_configure(
                self.devforge_dir, "add-package-stack",
                "--path", "pkg/p{0}".format(i),
                "--language", "Python",
            )
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(len(state["package_stacks"]), 3)
        paths = [r["path"] for r in state["package_stacks"]]
        self.assertIn("pkg/p0", paths)
        self.assertIn("pkg/p1", paths)
        self.assertIn("pkg/p2", paths)

    def test_setters_do_not_reset_other_fields(self):
        """Setting one field does not clear other fields in the yaml."""
        _run_configure(self.devforge_dir, "set-project-name", "my-project")
        _run_configure(self.devforge_dir, "set-languages", "TypeScript,Python")
        # Now set a different field.
        _run_configure(self.devforge_dir, "set-project-type", "Web Application")
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        # Both earlier fields must still be intact.
        self.assertEqual(state["project_name"], "my-project")
        self.assertEqual(state["languages"], ["TypeScript", "Python"])
        self.assertEqual(state["project_type"], "Web Application")


# ---------------------------------------------------------------------------
# 18. Cross-process safety tests (~2)
# ---------------------------------------------------------------------------


class CrossProcessSafetyTests(_EnvIsolationMixin, unittest.TestCase):
    """Verify concurrent add-package-stack invocations do not lose writes."""

    def _wait_all(self, procs):
        """Wait for all Popen procs, close their pipes, return exit codes."""
        codes = []
        for p in procs:
            p.wait()
            codes.append(p.returncode)
            if p.stdout:
                p.stdout.close()
            if p.stderr:
                p.stderr.close()
        return codes

    def test_5_concurrent_add_package_stack_no_lost_writes(self):
        """5 concurrent add-package-stack subprocesses → all 5 records present."""
        procs = []
        for i in range(5):
            p = subprocess.Popen(
                [
                    sys.executable,
                    str(_HELPER_PY),
                    "--devforge-dir", str(self.devforge_dir),
                    "add-package-stack",
                    "--path", "concurrent/pkg{0}".format(i),
                    "--language", "Python",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            procs.append(p)
        exit_codes = self._wait_all(procs)
        self.assertEqual(exit_codes, [0, 0, 0, 0, 0], "not all processes exited 0")
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        paths = {r["path"] for r in state["package_stacks"]}
        expected = {"concurrent/pkg{0}".format(i) for i in range(5)}
        self.assertEqual(paths, expected, "some records were lost in concurrent writes")

    def test_concurrent_scalar_set_and_append_no_corruption(self):
        """Concurrent set-project-name + add-package-stack don't corrupt the yaml."""
        procs = []
        # 3 scalar setters.
        for i in range(3):
            p = subprocess.Popen(
                [
                    sys.executable,
                    str(_HELPER_PY),
                    "--devforge-dir", str(self.devforge_dir),
                    "set-project-name", "project-{0}".format(i),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            procs.append(p)
        # 3 appenders.
        for i in range(3):
            p = subprocess.Popen(
                [
                    sys.executable,
                    str(_HELPER_PY),
                    "--devforge-dir", str(self.devforge_dir),
                    "add-package-stack",
                    "--path", "mixed/pkg{0}".format(i),
                    "--language", "Go",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            procs.append(p)
        exit_codes = self._wait_all(procs)
        self.assertTrue(all(c == 0 for c in exit_codes), "some processes exited non-zero")
        # The yaml must be parseable and have 3 package_stacks.
        text = self.output_file.read_text(encoding="utf-8")
        state = configure_helper.parse_yaml(text)
        self.assertEqual(len(state["package_stacks"]), 3)
        # Scalar side: project_name must be exactly one of the 3 launched
        # values (race winner). Any other value indicates corruption.
        self.assertIn(
            state["project_name"],
            {"project-0", "project-1", "project-2"},
            "project_name corrupted by concurrent scalar set",
        )


# ---------------------------------------------------------------------------
# Step 3: _write_json tests (~3)
# ---------------------------------------------------------------------------


class WriteJsonTests(_EnvIsolationMixin, unittest.TestCase):

    def test_writes_valid_json(self):
        target = self.devforge_dir / "test.json"
        configure_helper._write_json({"foo": "bar", "n": 42}, target)
        data = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(data["foo"], "bar")
        self.assertEqual(data["n"], 42)

    def test_atomic_write_idempotent(self):
        """Two writes produce byte-identical output for the same data."""
        target = self.devforge_dir / "idempotent.json"
        payload = {"x": 1, "y": [1, 2, 3]}
        configure_helper._write_json(payload, target)
        first = target.read_bytes()
        configure_helper._write_json(payload, target)
        second = target.read_bytes()
        self.assertEqual(first, second)

    def test_no_temp_files_left_on_success(self):
        """No .json.tmp files linger after a successful write."""
        target = self.devforge_dir / "clean.json"
        configure_helper._write_json({"a": 1}, target)
        tmp_files = list(self.devforge_dir.glob("*.json.tmp"))
        self.assertEqual(tmp_files, [], "orphaned temp files: {0}".format(tmp_files))


# ---------------------------------------------------------------------------
# Step 3: _build_project_config tests (~4)
# ---------------------------------------------------------------------------


class BuildProjectConfigTests(unittest.TestCase):

    def _make_cfg(self, **kwargs):
        state = configure_helper.default_state()
        state.update(kwargs)
        return state

    def _make_init(self, **kwargs):
        init_state = init_helper.default_state()
        init_state.update(kwargs)
        return init_state

    def test_all_36_keys_present(self):
        cfg = self._make_cfg()
        init = self._make_init()
        result = configure_helper._build_project_config(cfg, init, "")
        self.assertEqual(len(result), 36)
        for k in configure_helper._PROJECT_CONFIG_KEY_ORDER:
            self.assertIn(k, result, "missing key {0}".format(k))

    def test_key_order_matches_testforge20_reference(self):
        """Regression: positions 7-9 are LANGUAGES, FRAMEWORKS, PRIMARY_LANGUAGE.

        testForge20's existing project-config.json is the reference shape;
        diff stability across renders requires the exact same ordering.
        """
        keys = list(configure_helper._PROJECT_CONFIG_KEY_ORDER)
        self.assertEqual(keys[7:10], ["LANGUAGES", "FRAMEWORKS", "PRIMARY_LANGUAGE"])

    def test_wrapper_mode_section_standalone(self):
        cfg = self._make_cfg()
        init = self._make_init(workspace_mode="standalone", project_root="myapp")
        result = configure_helper._build_project_config(cfg, init, "")
        self.assertEqual(result["WRAPPER_MODE_SECTION"], "")

    def test_wrapper_mode_section_wrapper_contains_project_root(self):
        cfg = self._make_cfg()
        init = self._make_init(workspace_mode="wrapper", project_root="db-cse-ui-strata")
        result = configure_helper._build_project_config(cfg, init, "")
        self.assertIn("db-cse-ui-strata", result["WRAPPER_MODE_SECTION"])
        self.assertIn("## Wrapper Mode", result["WRAPPER_MODE_SECTION"])

    def test_commit_attribution_no(self):
        cfg = self._make_cfg(ai_attribution="No")
        init = self._make_init()
        result = configure_helper._build_project_config(cfg, init, "")
        self.assertEqual(result["COMMIT_ATTRIBUTION"], "")

    def test_commit_attribution_yes(self):
        cfg = self._make_cfg(ai_attribution="Yes")
        init = self._make_init()
        result = configure_helper._build_project_config(cfg, init, "")
        self.assertIn("Co-Authored-By", result["COMMIT_ATTRIBUTION"])

    def test_configure_fields_uppercased(self):
        cfg = self._make_cfg(project_name="my-project", languages=["TypeScript", "Python"])
        init = self._make_init()
        result = configure_helper._build_project_config(cfg, init, "")
        self.assertEqual(result["PROJECT_NAME"], "my-project")
        self.assertEqual(result["LANGUAGES"], ["TypeScript", "Python"])

    def test_init_fields_mapped(self):
        cfg = self._make_cfg()
        init = self._make_init(
            workspace_mode="standalone",
            project_root=".",
            project_state="brownfield",
            default_branch="main",
        )
        result = configure_helper._build_project_config(cfg, init, "")
        self.assertEqual(result["WORKSPACE_MODE"], "standalone")
        self.assertEqual(result["PROJECT_ROOT"], ".")
        self.assertEqual(result["PROJECT_STATE"], "brownfield")
        self.assertEqual(result["DEFAULT_BRANCH"], "main")

    def test_agent_list_passed_through(self):
        cfg = self._make_cfg()
        init = self._make_init()
        agent_list = "- ac-verifier\n- architect"
        result = configure_helper._build_project_config(cfg, init, agent_list)
        self.assertEqual(result["AGENT_LIST"], agent_list)

    def test_package_stacks_lowercase_subkeys(self):
        """package_stack records pass through with lowercase subkeys."""
        stack = [{"path": "api", "language": "Python", "framework": "FastAPI",
                  "build_tool": None, "build_command": None,
                  "type_check_command": None, "lint_command": None}]
        cfg = self._make_cfg(package_stacks=stack)
        init = self._make_init()
        result = configure_helper._build_project_config(cfg, init, "")
        self.assertEqual(result["PACKAGE_STACKS"][0]["path"], "api")
        self.assertEqual(result["PACKAGE_STACKS"][0]["language"], "Python")


# ---------------------------------------------------------------------------
# Step 3: _read_agent_list tests (~3)
# ---------------------------------------------------------------------------


class ReadAgentListTests(_EnvIsolationMixin, unittest.TestCase):

    def _agents_dir(self):
        d = self.install_root / ".claude" / "agents"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_no_agents_dir_returns_empty(self):
        # .claude/agents/ does not exist.
        result = configure_helper._read_agent_list(self.install_root)
        self.assertEqual(result, "")

    def test_empty_agents_dir_returns_empty(self):
        self._agents_dir()  # create but add no .md files
        result = configure_helper._read_agent_list(self.install_root)
        self.assertEqual(result, "")

    def test_agents_sorted_alphabetically(self):
        agents_dir = self._agents_dir()
        for name in ("zebra-agent", "alpha-agent", "beta-agent"):
            (agents_dir / "{0}.md".format(name)).write_text("# {0}\n".format(name), encoding="utf-8")
        result = configure_helper._read_agent_list(self.install_root)
        lines = result.splitlines()
        self.assertEqual(lines, ["- alpha-agent", "- beta-agent", "- zebra-agent"])

    def test_non_md_files_excluded(self):
        agents_dir = self._agents_dir()
        (agents_dir / "my-agent.md").write_text("# Agent\n", encoding="utf-8")
        (agents_dir / "README.txt").write_text("readme\n", encoding="utf-8")
        result = configure_helper._read_agent_list(self.install_root)
        self.assertEqual(result, "- my-agent")


# ---------------------------------------------------------------------------
# Step 3: render-config subprocess tests (~12)
# ---------------------------------------------------------------------------


class RenderConfigTests(_EnvIsolationMixin, unittest.TestCase):

    def _write_init_yaml(self, **kwargs):
        """Write init.yaml via init_helper setters (real producer)."""
        defaults = {
            "workspace_mode": "standalone",
            "project_root": ".",
            "project_state": "brownfield",
            "default_branch": "main",
        }
        defaults.update(kwargs)
        _run_init(self.devforge_dir, "reset")
        if defaults.get("workspace_mode"):
            _run_init(self.devforge_dir, "set-workspace-mode", defaults["workspace_mode"])
        if defaults.get("project_root"):
            _run_init(self.devforge_dir, "set-project-root", defaults["project_root"])
        if defaults.get("project_state"):
            _run_init(self.devforge_dir, "set-project-state", defaults["project_state"])
        if defaults.get("default_branch"):
            _run_init(self.devforge_dir, "set-default-branch", defaults["default_branch"])

    def _config_path(self):
        return self.devforge_dir / "project-config.json"

    def test_init_yaml_missing_exits_1(self):
        # configure.yaml reset but init.yaml absent.
        _run_configure(self.devforge_dir, "reset")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"init.yaml", proc.stderr)

    def test_renders_36_keys_with_defaults(self):
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(self._config_path().read_text(encoding="utf-8"))
        self.assertEqual(len(data), 36)
        for k in configure_helper._PROJECT_CONFIG_KEY_ORDER:
            self.assertIn(k, data, "missing key {0}".format(k))

    def test_configure_yaml_values_appear_in_json(self):
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "acme-app")
        _run_configure(self.devforge_dir, "set-primary-language", "TypeScript")
        _run_configure(self.devforge_dir, "set-languages", "TypeScript,Python")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(self._config_path().read_text(encoding="utf-8"))
        self.assertEqual(data["PROJECT_NAME"], "acme-app")
        self.assertEqual(data["PRIMARY_LANGUAGE"], "TypeScript")
        self.assertEqual(data["LANGUAGES"], ["TypeScript", "Python"])

    def test_init_yaml_values_appear_in_json(self):
        self._write_init_yaml(workspace_mode="wrapper", project_root="my-src")
        _run_configure(self.devforge_dir, "reset")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(self._config_path().read_text(encoding="utf-8"))
        self.assertEqual(data["WORKSPACE_MODE"], "wrapper")
        self.assertEqual(data["PROJECT_ROOT"], "my-src")

    def test_wrapper_mode_section_standalone(self):
        self._write_init_yaml(workspace_mode="standalone", project_root=".")
        _run_configure(self.devforge_dir, "reset")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(self._config_path().read_text(encoding="utf-8"))
        self.assertEqual(data["WRAPPER_MODE_SECTION"], "")

    def test_wrapper_mode_section_wrapper_contains_project_root(self):
        self._write_init_yaml(workspace_mode="wrapper", project_root="db-cse-ui-strata")
        _run_configure(self.devforge_dir, "reset")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(self._config_path().read_text(encoding="utf-8"))
        self.assertIn("db-cse-ui-strata", data["WRAPPER_MODE_SECTION"])
        self.assertIn("## Wrapper Mode", data["WRAPPER_MODE_SECTION"])

    def test_commit_attribution_no_is_empty(self):
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-ai-attribution", "No")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(self._config_path().read_text(encoding="utf-8"))
        self.assertEqual(data["COMMIT_ATTRIBUTION"], "")

    def test_commit_attribution_yes_contains_co_authored_by(self):
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-ai-attribution", "Yes")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(self._config_path().read_text(encoding="utf-8"))
        self.assertIn("Co-Authored-By", data["COMMIT_ATTRIBUTION"])

    def test_agent_list_absent_dir_is_empty(self):
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(self._config_path().read_text(encoding="utf-8"))
        self.assertEqual(data["AGENT_LIST"], "")

    def test_agent_list_3_agents_sorted(self):
        agents_dir = self.install_root / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        for name in ("zebra", "alpha", "beta"):
            (agents_dir / "{0}.md".format(name)).write_text("# {0}\n".format(name), encoding="utf-8")
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(self._config_path().read_text(encoding="utf-8"))
        self.assertEqual(data["AGENT_LIST"], "- alpha\n- beta\n- zebra")

    def test_idempotent_byte_identical_output(self):
        """Re-running render-config produces byte-identical project-config.json."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "stable-app")
        _run_configure(self.devforge_dir, "render-config")
        first = self._config_path().read_bytes()
        _run_configure(self.devforge_dir, "render-config")
        second = self._config_path().read_bytes()
        self.assertEqual(first, second)

    def test_overwrite_prior_json(self):
        """Re-running render-config overwrites (not appends to) prior JSON."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "first-run")
        _run_configure(self.devforge_dir, "render-config")
        data1 = json.loads(self._config_path().read_text(encoding="utf-8"))
        # Now update the name and re-render.
        _run_configure(self.devforge_dir, "set-project-name", "second-run")
        _run_configure(self.devforge_dir, "render-config")
        data2 = json.loads(self._config_path().read_text(encoding="utf-8"))
        self.assertEqual(data1["PROJECT_NAME"], "first-run")
        self.assertEqual(data2["PROJECT_NAME"], "second-run")

    def test_package_stacks_render_with_lowercase_subkeys(self):
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(
            self.devforge_dir, "add-package-stack",
            "--path", "services/api",
            "--language", "Python",
            "--framework", "FastAPI",
        )
        proc = _run_configure(self.devforge_dir, "render-config")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        data = json.loads(self._config_path().read_text(encoding="utf-8"))
        stacks = data["PACKAGE_STACKS"]
        self.assertEqual(len(stacks), 1)
        self.assertEqual(stacks[0]["path"], "services/api")
        self.assertEqual(stacks[0]["language"], "Python")
        self.assertEqual(stacks[0]["framework"], "FastAPI")


# ---------------------------------------------------------------------------
# Step 3: verify subprocess tests (~8)
# ---------------------------------------------------------------------------


class VerifyTests(_EnvIsolationMixin, unittest.TestCase):

    def _write_init_yaml(self):
        _run_init(self.devforge_dir, "reset")
        _run_init(self.devforge_dir, "set-workspace-mode", "standalone")
        _run_init(self.devforge_dir, "set-project-root", ".")
        _run_init(self.devforge_dir, "set-project-state", "brownfield")
        _run_init(self.devforge_dir, "set-default-branch", "main")

    def _populate_all_configure_fields(self):
        """Set all 28 configure.yaml fields to valid values."""
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "test-project")
        _run_configure(self.devforge_dir, "set-project-description", "A test project")
        _run_configure(self.devforge_dir, "set-project-type", "Web App")
        _run_configure(self.devforge_dir, "set-primary-language", "TypeScript")
        _run_configure(self.devforge_dir, "set-languages", "TypeScript")
        _run_configure(self.devforge_dir, "set-frameworks", "React")
        _run_configure(self.devforge_dir, "set-architectures", "MVC")
        _run_configure(self.devforge_dir, "set-project-natures", "web")
        _run_configure(self.devforge_dir, "set-error-handlings", "try-catch")
        _run_configure(self.devforge_dir, "set-api-layers", "REST")
        _run_configure(self.devforge_dir, "set-testings", "Jest")
        _run_configure(self.devforge_dir, "set-build-tools", "vite")
        _run_configure(self.devforge_dir, "set-build-commands", "npm run build")
        _run_configure(self.devforge_dir, "set-type-check-commands", "npx tsc")
        _run_configure(self.devforge_dir, "set-lint-commands", "npm run lint")
        _run_configure(
            self.devforge_dir, "add-package-stack",
            "--path", "src", "--language", "TypeScript",
        )
        _run_configure(self.devforge_dir, "set-project-structure", "--text", "src/\n  index.ts")
        _run_configure(self.devforge_dir, "set-dev-commands", "--text", "npm start")
        _run_configure(self.devforge_dir, "set-architecture-details", "--text", "MVC pattern")
        _run_configure(self.devforge_dir, "set-workflow-enforcement", "Strict")
        _run_configure(self.devforge_dir, "set-ai-attribution", "No")
        _run_configure(self.devforge_dir, "set-claude-tier-think", "Opus")
        _run_configure(self.devforge_dir, "set-claude-tier-do", "Sonnet")
        _run_configure(self.devforge_dir, "set-claude-tier-verify", "Haiku")
        _run_configure(self.devforge_dir, "set-ac-verification-mode", "code-only")
        # ac_runtime_* left null — allowed when mode != runtime-assisted

    def test_all_fields_populated_exits_0(self):
        self._write_init_yaml()
        self._populate_all_configure_fields()
        _run_configure(self.devforge_dir, "render-config")
        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn(b"verify: ok", proc.stderr)

    def test_null_scalar_exits_2(self):
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        # project_name is null — all others also null.
        _run_configure(self.devforge_dir, "render-config")
        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"PROJECT_NAME", proc.stderr)

    def test_empty_string_array_exits_2(self):
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        # All scalars populated but arrays empty.
        _run_configure(self.devforge_dir, "set-project-name", "test")
        _run_configure(self.devforge_dir, "set-project-description", "desc")
        _run_configure(self.devforge_dir, "set-project-type", "Web App")
        _run_configure(self.devforge_dir, "set-primary-language", "TypeScript")
        _run_configure(self.devforge_dir, "set-workflow-enforcement", "Strict")
        _run_configure(self.devforge_dir, "set-ai-attribution", "No")
        _run_configure(self.devforge_dir, "set-claude-tier-think", "Opus")
        _run_configure(self.devforge_dir, "set-claude-tier-do", "Sonnet")
        _run_configure(self.devforge_dir, "set-claude-tier-verify", "Haiku")
        _run_configure(self.devforge_dir, "set-ac-verification-mode", "off")
        _run_configure(self.devforge_dir, "set-project-structure", "--text", "src/")
        _run_configure(self.devforge_dir, "set-dev-commands", "--text", "npm start")
        _run_configure(self.devforge_dir, "set-architecture-details", "--text", "MVC")
        _run_configure(self.devforge_dir, "render-config")
        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        # At minimum, languages array is empty.
        self.assertIn(b"LANGUAGES", proc.stderr)

    def test_ac_runtime_fields_optional_when_mode_is_code_only(self):
        """ac_runtime_url/api_base/cli_command may be null when mode != runtime-assisted."""
        self._write_init_yaml()
        self._populate_all_configure_fields()  # mode=code-only, ac_runtime_* null
        _run_configure(self.devforge_dir, "render-config")
        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())

    def test_ac_runtime_fields_required_when_runtime_assisted(self):
        self._write_init_yaml()
        self._populate_all_configure_fields()
        # Switch mode to runtime-assisted; leave ac_runtime_url null.
        _run_configure(self.devforge_dir, "set-ac-verification-mode", "runtime-assisted")
        _run_configure(self.devforge_dir, "render-config")
        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"AC_RUNTIME_URL", proc.stderr)

    def test_project_config_json_missing_exits_2(self):
        self._write_init_yaml()
        self._populate_all_configure_fields()
        # Do NOT run render-config — project-config.json is absent.
        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"project-config.json missing", proc.stderr)

    def test_project_config_json_malformed_exits_2(self):
        self._write_init_yaml()
        self._populate_all_configure_fields()
        _run_configure(self.devforge_dir, "render-config")
        # Corrupt the JSON file.
        config_path = self.devforge_dir / "project-config.json"
        config_path.write_text("{not valid json", encoding="utf-8")
        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"malformed", proc.stderr)

    def test_round_trip_drift_detected(self):
        """Editing configure.yaml after render causes round-trip mismatch."""
        self._write_init_yaml()
        self._populate_all_configure_fields()
        _run_configure(self.devforge_dir, "render-config")
        # Now change project_name without re-rendering.
        _run_configure(self.devforge_dir, "set-project-name", "changed-name")
        proc = _run_configure(self.devforge_dir, "verify")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"round-trip mismatch", proc.stderr)


# ---------------------------------------------------------------------------
# Step 3: summary subprocess tests (~5)
# ---------------------------------------------------------------------------


class SummaryTests(_EnvIsolationMixin, unittest.TestCase):

    def test_empty_configure_yaml_shows_unset(self):
        _run_configure(self.devforge_dir, "reset")
        proc = _run_configure(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        out = proc.stdout.decode()
        self.assertIn("(unset)", out)
        self.assertIn("## Configure Report", out)

    def test_populated_values_appear(self):
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "demo-project")
        _run_configure(self.devforge_dir, "set-primary-language", "Rust")
        proc = _run_configure(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        out = proc.stdout.decode()
        self.assertIn("demo-project", out)
        self.assertIn("Rust", out)

    def test_long_string_truncated_with_ellipsis(self):
        long_val = "A" * 100
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-description", long_val)
        proc = _run_configure(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        out = proc.stdout.decode()
        self.assertIn("...", out)
        # The rendered value should be ≤80 chars (name + padding excluded).
        # The raw 100-char string should NOT appear verbatim.
        self.assertNotIn(long_val, out)

    def test_package_stack_array_renders_one_row_per_record(self):
        _run_configure(self.devforge_dir, "reset")
        _run_configure(
            self.devforge_dir, "add-package-stack",
            "--path", "frontend", "--language", "TypeScript", "--framework", "React",
        )
        _run_configure(
            self.devforge_dir, "add-package-stack",
            "--path", "backend", "--language", "Python", "--framework", "Django",
        )
        proc = _run_configure(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        out = proc.stdout.decode()
        self.assertIn("frontend | TypeScript | React", out)
        self.assertIn("backend | Python | Django", out)

    def test_output_stable_across_reruns(self):
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "stable")
        proc1 = _run_configure(self.devforge_dir, "summary")
        proc2 = _run_configure(self.devforge_dir, "summary")
        self.assertEqual(proc1.stdout, proc2.stdout)

    def test_empty_array_shows_empty_label(self):
        _run_configure(self.devforge_dir, "reset")
        proc = _run_configure(self.devforge_dir, "summary")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        out = proc.stdout.decode()
        self.assertIn("(empty)", out)

    def test_section_headers_present(self):
        _run_configure(self.devforge_dir, "reset")
        proc = _run_configure(self.devforge_dir, "summary")
        out = proc.stdout.decode()
        for header in ("Identity", "Stack", "Per-package", "Verbatim docs",
                       "Preferences", "AC verification"):
            self.assertIn(header, out, "section header '{0}' missing".format(header))


# ---------------------------------------------------------------------------
# Step 4: _build_substitution_map tests (~6)
# ---------------------------------------------------------------------------


class SubstitutionMapTests(unittest.TestCase):
    """Unit tests for _build_substitution_map — no subprocess, pure function."""

    def _make_config(self, **overrides) -> dict:
        """Return a minimal project_config dict (all keys from _PROJECT_CONFIG_KEY_ORDER)."""
        base = {k: None for k in configure_helper._PROJECT_CONFIG_KEY_ORDER}
        # Set array keys to empty list.
        for k in (
            "LANGUAGES", "FRAMEWORKS", "ARCHITECTURES", "PROJECT_NATURES",
            "ERROR_HANDLINGS", "API_LAYERS", "TESTINGS", "BUILD_TOOLS",
            "BUILD_COMMANDS", "TYPE_CHECK_COMMANDS", "LINT_COMMANDS",
            "PACKAGE_STACKS", "PACKAGES_DETECTED",
        ):
            base[k] = []
        # Derived strings default to "".
        for k in ("WRAPPER_MODE_SECTION", "COMMIT_ATTRIBUTION", "AGENT_LIST"):
            base[k] = ""
        base.update(overrides)
        return base

    def test_all_36_project_config_keys_present_in_map(self):
        """All 36 keys from _PROJECT_CONFIG_KEY_ORDER appear as entries in the map."""
        config = self._make_config()
        sub_map = configure_helper._build_substitution_map(config, [])
        for key in configure_helper._PROJECT_CONFIG_KEY_ORDER:
            self.assertIn(
                key, sub_map,
                "key {0} missing from substitution map".format(key),
            )

    def test_10_singular_aliases_derive_from_plural_arrays(self):
        """10 singular aliases are present in the map and derive from their plural array."""
        config = self._make_config(
            FRAMEWORKS=["Vue", "React"],
            LANGUAGES=["TypeScript", "Python"],
            BUILD_TOOLS=["Vite"],
            BUILD_COMMANDS=["npm run build"],
            TYPE_CHECK_COMMANDS=["npx tsc"],
            LINT_COMMANDS=["npm run lint"],
            ERROR_HANDLINGS=["try-catch"],
            API_LAYERS=["REST"],
            TESTINGS=["Jest"],
            ARCHITECTURES=["MVC", "MVVM"],
        )
        sub_map = configure_helper._build_substitution_map(config, [])
        self.assertEqual(sub_map["FRAMEWORK"], "Vue, React")
        self.assertEqual(sub_map["LANGUAGE"], "TypeScript, Python")
        self.assertEqual(sub_map["BUILD_TOOL"], "Vite")
        self.assertEqual(sub_map["BUILD_COMMAND"], "npm run build")
        self.assertEqual(sub_map["TYPE_CHECK_COMMAND"], "npx tsc")
        self.assertEqual(sub_map["LINT_COMMAND"], "npm run lint")
        self.assertEqual(sub_map["ERROR_HANDLING"], "try-catch")
        self.assertEqual(sub_map["API_LAYER"], "REST")
        self.assertEqual(sub_map["TESTING"], "Jest")
        self.assertEqual(sub_map["ARCHITECTURE"], "MVC, MVVM")

    def test_project_paths_derives_from_packages_detected(self):
        """PROJECT_PATHS is comma-joined path field from packages_detected[]."""
        config = self._make_config()
        packages_detected = [
            {"path": "apps/web", "language": "TypeScript"},
            {"path": "packages/core", "language": "TypeScript"},
        ]
        sub_map = configure_helper._build_substitution_map(config, packages_detected)
        self.assertEqual(sub_map["PROJECT_PATHS"], "apps/web, packages/core")

    def test_package_stacks_section_empty_array_gives_empty_string(self):
        """PACKAGE_STACKS_SECTION is empty string when PACKAGE_STACKS is []."""
        config = self._make_config(PACKAGE_STACKS=[])
        sub_map = configure_helper._build_substitution_map(config, [])
        self.assertEqual(sub_map["PACKAGE_STACKS_SECTION"], "")

    def test_package_stacks_section_populated_gives_markdown_table(self):
        """PACKAGE_STACKS_SECTION renders a 4-column markdown table."""
        stacks = [
            {
                "path": "apps/app-web",
                "language": "TypeScript",
                "framework": "Vue",
                "build_tool": "Vite",
                "build_command": "npm run build",
                "type_check_command": "npx tsc",
                "lint_command": "npm run lint",
            },
            {
                "path": "packages/pkg-core",
                "language": "TypeScript",
                "framework": None,
                "build_tool": "Vite",
                "build_command": "npm run build",
                "type_check_command": "npx tsc",
                "lint_command": "npm run lint",
            },
        ]
        config = self._make_config(PACKAGE_STACKS=stacks)
        sub_map = configure_helper._build_substitution_map(config, [])
        table = sub_map["PACKAGE_STACKS_SECTION"]
        self.assertIn("| Package | Language | Framework | Build Tool |", table)
        self.assertIn("|---------|----------|-----------|------------|", table)
        self.assertIn("| apps/app-web | TypeScript | Vue | Vite |", table)
        # None framework → empty cell (not the word "None").
        self.assertIn("| packages/pkg-core | TypeScript |  | Vite |", table)
        self.assertNotIn("None", table)

    def test_uppercase_key_produces_identity_passthrough(self):
        """UPPERCASE key in sub_map renders as the literal {{UPPERCASE}} string."""
        config = self._make_config()
        sub_map = configure_helper._build_substitution_map(config, [])
        self.assertEqual(sub_map["UPPERCASE"], "{{UPPERCASE}}")

    def test_state_management_and_styling_not_in_substitution_map(self):
        """STATE_MANAGEMENT + STYLING are NOT in the map.

        These rules belong in constitution.md (project conventions), not in
        the CLAUDE.md / agent-file template substitution layer. Agent files
        reference constitution.md §Conventions for these rules; if a stray
        {{STATE_MANAGEMENT}} or {{STYLING}} appears in a template, it gets
        reported as an unknown placeholder (exit 2).
        """
        config = self._make_config()
        sub_map = configure_helper._build_substitution_map(config, [])
        self.assertNotIn("STATE_MANAGEMENT", sub_map)
        self.assertNotIn("STYLING", sub_map)


# ---------------------------------------------------------------------------
# Step 4: _substitute_placeholders engine tests (~6)
# ---------------------------------------------------------------------------


class SubstitutePlaceholdersTests(unittest.TestCase):
    """Unit tests for _substitute_placeholders — pure function."""

    def test_single_placeholder_substituted(self):
        text, missing = configure_helper._substitute_placeholders(
            "Project: {{PROJECT_NAME}}",
            {"PROJECT_NAME": "MyApp"},
        )
        self.assertEqual(text, "Project: MyApp")
        self.assertEqual(missing, [])

    def test_multiple_placeholders_substituted(self):
        text, missing = configure_helper._substitute_placeholders(
            "{{PROJECT_NAME}} — {{LANGUAGE}} — {{FRAMEWORK}}",
            {"PROJECT_NAME": "App", "LANGUAGE": "TypeScript", "FRAMEWORK": "Vue"},
        )
        self.assertEqual(text, "App — TypeScript — Vue")
        self.assertEqual(missing, [])

    def test_unknown_placeholder_collected_into_missing(self):
        text, missing = configure_helper._substitute_placeholders(
            "Hello {{FOO}} and {{BAR}}",
            {"PROJECT_NAME": "X"},
        )
        # Unknown keys are left as-is in the output.
        self.assertIn("{{FOO}}", text)
        self.assertIn("{{BAR}}", text)
        self.assertEqual(missing, ["BAR", "FOO"])  # sorted

    def test_state_management_treated_as_unknown_placeholder(self):
        """STATE_MANAGEMENT in a template is reported as missing (exit-2 path).

        State-management rules live in constitution.md, not in the
        substitution layer. A stray {{STATE_MANAGEMENT}} marker in a
        template is a template bug — engine flags it for the caller.
        """
        text, missing = configure_helper._substitute_placeholders(
            "Style: {{STATE_MANAGEMENT}} end",
            {"PROJECT_NAME": "X"},
        )
        self.assertIn("{{STATE_MANAGEMENT}}", text)
        self.assertEqual(missing, ["STATE_MANAGEMENT"])

    def test_styling_treated_as_unknown_placeholder(self):
        """STYLING placeholder is unknown — same rationale as STATE_MANAGEMENT."""
        text, missing = configure_helper._substitute_placeholders(
            "Use {{STYLING}}",
            {},
        )
        self.assertIn("{{STYLING}}", text)
        self.assertEqual(missing, ["STYLING"])

    def test_uppercase_round_trips_unchanged(self):
        """{{UPPERCASE}} substituted to {{UPPERCASE}} leaves prose explanation intact."""
        sub_map = {"UPPERCASE": "{{UPPERCASE}}"}
        original = "Use {{UPPERCASE}} placeholders for substitution."
        text, missing = configure_helper._substitute_placeholders(original, sub_map)
        self.assertEqual(text, original)
        self.assertEqual(missing, [])

    def test_no_regex_bleed_over_on_non_uppercase_content(self):
        """Patterns like {{lowercase}} or {{Mixed}} are NOT matched."""
        sub_map = {"PROJECT_NAME": "App"}
        text, missing = configure_helper._substitute_placeholders(
            "{{PROJECT_NAME}} and {{lowercase}} and {{Mixed}}",
            sub_map,
        )
        self.assertEqual(text, "App and {{lowercase}} and {{Mixed}}")
        self.assertEqual(missing, [])


# ---------------------------------------------------------------------------
# Step 4: substitute-templates subprocess tests (~10)
# ---------------------------------------------------------------------------


class SubstituteTemplatesTests(_EnvIsolationMixin, unittest.TestCase):
    """End-to-end subprocess tests for the substitute-templates subcommand."""

    def _write_init_yaml(self, workspace_mode: str = "standalone", project_root: str = ".") -> None:
        """Write a minimal init.yaml to devforge_dir via init_helper."""
        _run_init(self.devforge_dir, "reset")
        _run_init(self.devforge_dir, "set-project-name", "test-project")
        _run_init(self.devforge_dir, "set-workspace-mode", workspace_mode)

    def _write_project_config_json(self) -> None:
        """Run render-config to produce project-config.json."""
        _run_configure_extra(
            self.devforge_dir,
            ["--install-root", str(self.install_root)],
            "render-config",
        )

    def _run_substitute(self) -> "subprocess.CompletedProcess":
        return _run_configure_extra(
            self.devforge_dir,
            ["--install-root", str(self.install_root)],
            "substitute-templates",
        )

    def _write_claude_md(self, content: str) -> None:
        """Write content to <install_root>/CLAUDE.md."""
        (self.install_root / "CLAUDE.md").write_text(content, encoding="utf-8")

    def _write_agent_md(self, name: str, content: str) -> None:
        """Write an agent template to <install_root>/.claude/agents/<name>.md."""
        agents_dir = self.install_root / ".claude" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "{0}.md".format(name)).write_text(content, encoding="utf-8")

    def _read_claude_md(self) -> str:
        return (self.install_root / "CLAUDE.md").read_text(encoding="utf-8")

    def _read_agent_md(self, name: str) -> str:
        return (self.install_root / ".claude" / "agents" / "{0}.md".format(name)).read_text(encoding="utf-8")

    def test_defaults_template_exits_0_no_placeholders_remain(self):
        """Defaults configure.yaml + minimal template → exit 0, no {{...}} markers."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        self._write_project_config_json()
        self._write_claude_md("Name: {{PROJECT_NAME}}\nLang: {{LANGUAGE}}\n")
        proc = self._run_substitute()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        result = self._read_claude_md()
        import re
        leftover = re.findall(r"\{\{[A-Z_]+\}\}", result)
        self.assertEqual(leftover, [], "leftover placeholders: {0}".format(leftover))

    def test_populated_project_name_substituted(self):
        """configure.yaml.project_name → substituted into {{PROJECT_NAME}}."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "demo-forge")
        self._write_project_config_json()
        self._write_claude_md("Project: {{PROJECT_NAME}}")
        proc = self._run_substitute()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn("demo-forge", self._read_claude_md())

    def test_single_language_substituted(self):
        """languages=['TypeScript'] → {{LANGUAGE}} = 'TypeScript'."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-languages", "TypeScript")
        self._write_project_config_json()
        self._write_claude_md("Lang: {{LANGUAGE}}")
        proc = self._run_substitute()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn("TypeScript", self._read_claude_md())

    def test_multi_language_comma_joined(self):
        """languages=['TypeScript','Python'] → {{LANGUAGE}} = 'TypeScript, Python'."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-languages", "TypeScript,Python")
        self._write_project_config_json()
        self._write_claude_md("Lang: {{LANGUAGE}}")
        proc = self._run_substitute()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertIn("TypeScript, Python", self._read_claude_md())

    def test_package_stacks_section_markdown_table(self):
        """populate package_stacks → {{PACKAGE_STACKS_SECTION}} renders as table."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(
            self.devforge_dir, "add-package-stack",
            "--path", "apps/web",
            "--language", "TypeScript",
            "--framework", "Vue",
            "--build-tool", "Vite",
        )
        self._write_project_config_json()
        self._write_claude_md("## Packages\n\n{{PACKAGE_STACKS_SECTION}}\n")
        proc = self._run_substitute()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        result = self._read_claude_md()
        self.assertIn("| Package | Language | Framework | Build Tool |", result)
        self.assertIn("| apps/web | TypeScript | Vue | Vite |", result)

    def test_unknown_placeholder_exits_2_and_lists_key(self):
        """Template with {{FOO}} → exit 2 + stderr names FOO."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        self._write_project_config_json()
        self._write_claude_md("Hello {{FOO}} world")
        proc = self._run_substitute()
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"FOO", proc.stderr)

    def test_state_management_placeholder_in_template_exits_2(self):
        """{{STATE_MANAGEMENT}} in a template is an unknown placeholder.

        State-management rules live in constitution.md per /constitute
        pipeline; the substitution layer does NOT define a value. A stray
        {{STATE_MANAGEMENT}} marker in CLAUDE.md or an agent file is a
        template bug — exit 2 with the unknown placeholder enumerated.
        """
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        self._write_project_config_json()
        self._write_claude_md("State: {{STATE_MANAGEMENT}} end")
        proc = self._run_substitute()
        self.assertEqual(proc.returncode, 2, proc.stderr.decode())
        # Original file unchanged because the substitution failed.
        self.assertIn("{{STATE_MANAGEMENT}}", self._read_claude_md())
        self.assertIn(b"STATE_MANAGEMENT", proc.stderr)

    def test_idempotent_no_placeholders_in_already_substituted_file(self):
        """Re-running substitute-templates on an already-substituted file exits 0."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "idempotent-project")
        self._write_project_config_json()
        self._write_claude_md("Project: {{PROJECT_NAME}}")
        # First run — substitutes.
        proc1 = self._run_substitute()
        self.assertEqual(proc1.returncode, 0, proc1.stderr.decode())
        content_after_first = self._read_claude_md()
        self.assertIn("idempotent-project", content_after_first)
        # Second run — no {{...}} left; exits 0, file unchanged.
        proc2 = self._run_substitute()
        self.assertEqual(proc2.returncode, 0, proc2.stderr.decode())
        self.assertEqual(self._read_claude_md(), content_after_first)

    def test_project_config_missing_exits_1(self):
        """project-config.json absent → exit 1."""
        self._write_init_yaml()
        # Do NOT run render-config → project-config.json does not exist.
        self._write_claude_md("{{PROJECT_NAME}}")
        proc = self._run_substitute()
        self.assertEqual(proc.returncode, 1)
        self.assertIn(b"project-config.json not found", proc.stderr)

    def test_agent_template_substituted(self):
        """Agent .md files under .claude/agents/ are also substituted."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        _run_configure(self.devforge_dir, "set-project-name", "forge-test")
        self._write_project_config_json()
        self._write_claude_md("Project: {{PROJECT_NAME}}")
        self._write_agent_md("code-reviewer", "Agent for {{PROJECT_NAME}} review")
        proc = self._run_substitute()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        agent_content = self._read_agent_md("code-reviewer")
        self.assertIn("forge-test", agent_content)
        self.assertNotIn("{{PROJECT_NAME}}", agent_content)

    def test_unknown_placeholder_leaves_original_file_unchanged(self):
        """File with unknown placeholder is NOT modified (atomic write skipped)."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        self._write_project_config_json()
        original_content = "Has {{UNKNOWN_KEY}} in it"
        self._write_claude_md(original_content)
        proc = self._run_substitute()
        self.assertEqual(proc.returncode, 2)
        # Original file must be unchanged.
        self.assertEqual(self._read_claude_md(), original_content)

    def test_uppercase_identity_placeholder_round_trips(self):
        """{{UPPERCASE}} in a template round-trips as {{UPPERCASE}} after substitution."""
        self._write_init_yaml()
        _run_configure(self.devforge_dir, "reset")
        self._write_project_config_json()
        self._write_claude_md("See {{UPPERCASE}} convention for details.")
        proc = self._run_substitute()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        result = self._read_claude_md()
        self.assertEqual(result, "See {{UPPERCASE}} convention for details.")


# ---------------------------------------------------------------------------
# Step 5a: SchemaProjectNaturesTests (~3)
# ---------------------------------------------------------------------------


class SchemaProjectNaturesTests(unittest.TestCase):

    def test_project_natures_in_field_schema(self):
        """FIELD_SCHEMA contains project_natures as string_array."""
        found = None
        for name, kind in configure_helper.FIELD_SCHEMA:
            if name == "project_natures":
                found = kind
                break
        self.assertEqual(found, "string_array")

    def test_project_natures_position_after_architectures(self):
        """project_natures immediately follows architectures in FIELD_SCHEMA.

        These two 'shape of project' arrays cluster together; position is
        part of the diff-stability contract.
        """
        names = [name for name, _ in configure_helper.FIELD_SCHEMA]
        arch_idx = names.index("architectures")
        natures_idx = names.index("project_natures")
        self.assertEqual(natures_idx, arch_idx + 1)

    def test_default_state_project_natures_is_empty_list(self):
        """default_state() returns project_natures: [] (not None)."""
        state = configure_helper.default_state()
        self.assertIn("project_natures", state)
        self.assertEqual(state["project_natures"], [])

    def test_emit_parse_round_trip_with_project_natures(self):
        """emit_yaml / parse_yaml round-trip preserves project_natures values."""
        state = configure_helper.default_state()
        state["project_natures"] = ["web", "backend"]
        text = configure_helper.emit_yaml(state)
        state2 = configure_helper.parse_yaml(text)
        self.assertEqual(state2["project_natures"], ["web", "backend"])


# ---------------------------------------------------------------------------
# Step 5a: SetProjectNaturesTests (~3)
# ---------------------------------------------------------------------------


class SetProjectNaturesTests(_EnvIsolationMixin, unittest.TestCase):

    def test_happy_path_sets_values(self):
        """set-project-natures 'web,backend' writes ['web', 'backend'] to state."""
        proc = _run_configure(self.devforge_dir, "set-project-natures", "web,backend")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_natures"], ["web", "backend"])

    def test_empty_string_rejected_exit_2(self):
        """set-project-natures '' exits 2 (validation failure)."""
        proc = _run_configure(self.devforge_dir, "set-project-natures", "")
        self.assertEqual(proc.returncode, 2)

    def test_second_call_replaces_not_appends(self):
        """Calling set-project-natures twice: second value replaces first."""
        _run_configure(self.devforge_dir, "set-project-natures", "mobile")
        _run_configure(self.devforge_dir, "set-project-natures", "web,backend")
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_natures"], ["web", "backend"])

    def test_single_value_accepted(self):
        """Single nature (no comma) is accepted and stored as one-element list."""
        proc = _run_configure(self.devforge_dir, "set-project-natures", "cli")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_natures"], ["cli"])

    def test_custom_nature_accepted_no_enum_check(self):
        """Non-vocabulary nature string is accepted (no enum restriction)."""
        proc = _run_configure(self.devforge_dir, "set-project-natures", "custom-platform")
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        state = configure_helper.parse_yaml(self.output_file.read_text(encoding="utf-8"))
        self.assertEqual(state["project_natures"], ["custom-platform"])


# ---------------------------------------------------------------------------
# Step 5a: PruneAgentsTests (~6)
# ---------------------------------------------------------------------------


class PruneAgentsTests(_EnvIsolationMixin, unittest.TestCase):
    """Tests for the prune-agents subcommand.

    Agent files are hand-authored in self.agents_dir (not round-tripped
    from the real agent generator — the frontmatter parser is the unit
    under test, not the generator). The parser itself is verified by
    _parse_agent_frontmatter unit tests below.
    """

    def setUp(self):
        super().setUp()
        self.agents_dir = self.install_root / ".claude" / "agents"
        self.agents_dir.mkdir(parents=True, exist_ok=True)

    def _write_agent(self, name, applies_to_str):
        """Write a minimal agent .md file with given applies_to value."""
        content = (
            "```yaml\n"
            "name: {0}\n"
            "description: \"Agent {0}\"\n"
            "model_tier: do\n"
            "applies_to: {1}\n"
            "```\n\n"
            "Agent body.\n"
        ).format(name, applies_to_str)
        (self.agents_dir / "{0}.md".format(name)).write_text(content, encoding="utf-8")

    def _set_project_natures(self, natures_csv):
        _run_configure(self.devforge_dir, "set-project-natures", natures_csv)

    def _run_prune(self, apply=False):
        extra = ["--install-root", str(self.install_root)]
        args = ["prune-agents"]
        if apply:
            args.append("--apply")
        return _run_configure_extra(self.devforge_dir, extra, *args)

    def test_empty_project_natures_exits_2(self):
        """prune-agents exits 2 when project_natures is empty."""
        # Do NOT set project_natures (default is []).
        proc = self._run_prune()
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"project_natures unset", proc.stderr)

    def test_applies_to_all_always_kept(self):
        """Agent with applies_to: ['all'] is always kept regardless of natures."""
        self._set_project_natures("web")
        self._write_agent("universal-agent", '["all"]')
        proc = self._run_prune()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())
        self.assertIn("universal-agent", report["kept"])
        self.assertNotIn("universal-agent", report["dropped"])

    def test_non_matching_applies_to_dropped(self):
        """Agent with applies_to: ['mobile'] dropped when project_natures=['web']."""
        self._set_project_natures("web")
        self._write_agent("mobile-only", '["mobile"]')
        proc = self._run_prune()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())
        self.assertIn("mobile-only", report["dropped"])
        self.assertNotIn("mobile-only", report["kept"])

    def test_partial_overlap_kept(self):
        """Agent with applies_to: ['web', 'backend'] kept when project_natures includes 'web'."""
        self._set_project_natures("web")
        self._write_agent("web-or-backend", '["web", "backend"]')
        proc = self._run_prune()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())
        self.assertIn("web-or-backend", report["kept"])
        self.assertNotIn("web-or-backend", report["dropped"])

    def test_dry_run_does_not_delete_files(self):
        """Without --apply, dropped agents remain on disk."""
        self._set_project_natures("web")
        self._write_agent("mobile-only", '["mobile"]')
        proc = self._run_prune(apply=False)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())
        self.assertIn("mobile-only", report["dropped"])
        # File must still exist (dry-run).
        self.assertTrue((self.agents_dir / "mobile-only.md").exists())

    def test_apply_deletes_dropped_files(self):
        """With --apply, dropped agents are deleted from disk."""
        self._set_project_natures("web")
        self._write_agent("mobile-only", '["mobile"]')
        self._write_agent("universal-agent", '["all"]')
        proc = self._run_prune(apply=True)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        self.assertFalse((self.agents_dir / "mobile-only.md").exists())
        # Kept agent still present.
        self.assertTrue((self.agents_dir / "universal-agent.md").exists())

    def test_missing_applies_to_frontmatter_keeps_file(self):
        """Agent without applies_to frontmatter is kept with a stderr warning."""
        self._set_project_natures("web")
        # Write agent without applies_to field.
        content = (
            "```yaml\n"
            "name: no-applies-to\n"
            "description: \"Agent\"\n"
            "```\n\n"
            "Body.\n"
        )
        (self.agents_dir / "no-applies-to.md").write_text(content, encoding="utf-8")
        proc = self._run_prune()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())
        self.assertIn("no-applies-to", report["kept"])
        # Warning emitted to stderr.
        self.assertIn(b"warning", proc.stderr.lower())

    def test_report_contains_decisions_list(self):
        """JSON output includes decisions list with name, applies_to, status per agent."""
        self._set_project_natures("web")
        self._write_agent("web-agent", '["web"]')
        self._write_agent("mobile-agent", '["mobile"]')
        proc = self._run_prune()
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        report = json.loads(proc.stdout.decode())
        self.assertIn("decisions", report)
        names = [d["name"] for d in report["decisions"]]
        self.assertIn("web-agent", names)
        self.assertIn("mobile-agent", names)
        # Verify status fields.
        status_map = {d["name"]: d["status"] for d in report["decisions"]}
        self.assertEqual(status_map["web-agent"], "keep")
        self.assertEqual(status_map["mobile-agent"], "drop")


# ---------------------------------------------------------------------------
# Step 5a: ParseAgentFrontmatterTests (unit tests, ~4)
# ---------------------------------------------------------------------------


class ParseAgentFrontmatterTests(unittest.TestCase):
    """Unit tests for _parse_agent_frontmatter (internal helper)."""

    def _make_agent_text(self, frontmatter_fields):
        """Build agent file text with given fields inside the yaml fence."""
        inner = "\n".join("{0}: {1}".format(k, v) for k, v in frontmatter_fields)
        return "```yaml\n{0}\n```\n\nBody text.\n".format(inner)

    def test_standard_applies_to_list(self):
        text = self._make_agent_text([
            ("name", "my-agent"),
            ('applies_to', '["web", "backend"]'),
        ])
        result = configure_helper._parse_agent_frontmatter(text)
        self.assertEqual(result, ["web", "backend"])

    def test_applies_to_all(self):
        text = self._make_agent_text([
            ("name", "universal"),
            ('applies_to', '["all"]'),
        ])
        result = configure_helper._parse_agent_frontmatter(text)
        self.assertEqual(result, ["all"])

    def test_missing_applies_to_returns_none(self):
        """Frontmatter without applies_to field → None (caller keeps file)."""
        text = self._make_agent_text([
            ("name", "no-natures"),
            ("model_tier", "do"),
        ])
        result = configure_helper._parse_agent_frontmatter(text)
        self.assertIsNone(result)

    def test_no_frontmatter_returns_none(self):
        """Plain markdown without yaml fence → None."""
        text = "# My Agent\n\nJust plain markdown.\n"
        result = configure_helper._parse_agent_frontmatter(text)
        self.assertIsNone(result)

    def test_blank_lines_before_fence_allowed(self):
        """Blank lines before the opening fence are tolerated."""
        text = "\n\n```yaml\nname: agent\napplies_to: [\"web\"]\n```\nBody.\n"
        result = configure_helper._parse_agent_frontmatter(text)
        self.assertEqual(result, ["web"])


if __name__ == "__main__":
    unittest.main()
