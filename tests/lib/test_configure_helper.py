"""Tests for src/devforge/lib/configure_helper.py — Step 1 + Step 2.

Step 1 coverage: FIELD_SCHEMA, ENUM_FIELDS, default_state, emit_yaml/
parse_yaml round-trips (incl. multi-line scalars + missing-subfield
rejection + fence-aware section extractor), reset subcommand, read-init
(real-producer round-trip), read-docs (hand-authored Plan F fixtures),
read-manifests, read-configs.

Step 2 coverage: _load / _dump / _state_transaction (write-on-exit, abort-
on-exception, lock-file creation), five _validate_* helpers, all 27 setter
subcommands (3 identity + 1 primary-language + 7 stack arrays + 3 per-pkg
arrays + add-package-stack + 3 verbatim + 6 enums + 3 ac-runtime), round-
trip integration (all-27-fields set + reload + compare; replace-not-append
for string_arrays; accumulate for add-package-stack), cross-process safety
(5 concurrent add-package-stack via Popen — no lost writes; mixed scalar+
append concurrency — no corruption).

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

    def test_case_sensitive_rejection(self):
        # "strict" is not in the set {"Strict", "Moderate", "Light"}
        with self.assertRaises(ValueError):
            configure_helper._validate_enum("strict", "workflow_enforcement")


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
        proc = _run_configure(self.devforge_dir, "set-claude-tier-think", "Other")
        self.assertEqual(proc.returncode, 0)

    def test_invalid_rejected(self):
        proc = _run_configure(self.devforge_dir, "set-claude-tier-do", "GPT-4")
        self.assertEqual(proc.returncode, 2)
        self.assertIn(b"claude_tier_do", proc.stderr)


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

    def test_all_27_fields_set_reload_match(self):
        """Set all 27 fields via setters then reload and compare full state."""
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


if __name__ == "__main__":
    unittest.main()
