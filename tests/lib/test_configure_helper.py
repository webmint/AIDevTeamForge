"""Tests for src/devforge/lib/configure_helper.py — Step 1.

Covers: FIELD_SCHEMA, ENUM_FIELDS, default_state, emit_yaml/parse_yaml
round-trips, reset subcommand, read-init (real-producer round-trip),
read-docs (hand-authored Plan F fixtures), read-manifests, read-configs.

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

    def test_field_schema_has_27_fields(self):
        self.assertEqual(len(configure_helper.FIELD_SCHEMA), 27)

    def test_default_state_has_27_keys(self):
        state = configure_helper.default_state()
        self.assertEqual(len(state), 27)

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

    def test_enum_fields_has_6_entries(self):
        self.assertEqual(len(configure_helper.ENUM_FIELDS), 6)

    def test_enum_fields_correct_keys(self):
        expected_keys = {
            "workflow_enforcement",
            "ai_attribution",
            "claude_tier_think",
            "claude_tier_do",
            "claude_tier_verify",
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
            configure_helper.ENUM_FIELDS["claude_tier_think"],
            {"Opus", "Sonnet", "Haiku", "Other"},
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
        """All 27 fields populated — comprehensive round-trip."""
        state = {
            "project_name": "db-cse-ui-strata",
            "project_description": "A complex monorepo project",
            "project_type": "Web Application",
            "primary_language": "TypeScript",
            "languages": ["TypeScript", "Python"],
            "frameworks": ["Vue", "FastAPI"],
            "architectures": ["Clean Architecture", "Turborepo monorepo"],
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


if __name__ == "__main__":
    unittest.main()
