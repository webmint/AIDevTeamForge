"""Tests for src/devforge/lib/constitute_helper.py — Step 0 + Step 1.

Step 0 coverage (preserved):
  reset subcommand writes a JSON defaults file with the locked top-level
  shape. Idempotent: byte-identical re-runs.

Step 1 coverage:
  FIELD_SCHEMA — 11 keys, locked order, correct kinds.
  ENUM_FIELDS  — 4 closed enums accessible by name; known values present.
  default_state() — top-level keys + types, patterns_and_antipatterns 6-bucket
    struct, project_identity + scaffolding_guide default to None.
  reset — JSON round-trip (matches default_state); idempotent byte-identical.
  read-init — round-trip via init_helper subprocess (write real init.yaml,
    parse via read-init, assert fields); file missing → exit 1 stderr;
    malformed yaml → exit 2 stderr.
  read-configure — round-trip via configure_helper subprocess; file missing
    → exit 1; malformed yaml → exit 2.
  read-docs — overview-only fixture (Tech Stack table + Project Structure
    fenced block + Key Commands table); architecture-only fixture (Patterns
    sub-headings + Conventions); both files together (testForge20 sample
    copied to tmpdir); overview missing → exit 1; architecture missing →
    exit 1; malformed markdown → graceful exit 0.
  read-glossary — 3-term hand-authored fixture; file missing → exit 1; empty
    file → exit 0 with empty list [].

Each subprocess test runs in its own tempfile.TemporaryDirectory.
Pure-function tests import the module directly.

Real-producer principle for read-init and read-configure: the real helper
subprocess writes the yaml; constitute_helper reads it back — no hand-authored
yaml fixtures bypass the real producer.

Stdlib only.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_LIB_DIR = _REPO_ROOT / "src" / "devforge" / "lib"
_HELPER_PY = _LIB_DIR / "constitute_helper.py"
_INIT_HELPER_PY = _LIB_DIR / "init_helper.py"
_CONFIGURE_HELPER_PY = _LIB_DIR / "configure_helper.py"
_TESTFORGE20 = Path("/Users/mykolakudlyk/Projects/testForge20")

if str(_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(_LIB_DIR))

import constitute_helper  # noqa: E402
import init_helper  # noqa: E402
import configure_helper  # noqa: E402


# ---------------------------------------------------------------------------
# Subprocess helpers.
# ---------------------------------------------------------------------------


def _run(argv, cwd=None, env=None):
    """Run constitute_helper.py with given argv; capture output."""
    return subprocess.run(
        [sys.executable, str(_HELPER_PY)] + list(argv),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _run_init(devforge_dir, *extra_args):
    """Run init_helper.py via DEVFORGE_DIR env var."""
    env = os.environ.copy()
    env["DEVFORGE_DIR"] = str(devforge_dir)
    return subprocess.run(
        [sys.executable, str(_INIT_HELPER_PY)] + list(extra_args),
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _run_configure(devforge_dir, *extra_args):
    """Run configure_helper.py with --devforge-dir."""
    return subprocess.run(
        [sys.executable, str(_CONFIGURE_HELPER_PY),
         "--devforge-dir", str(devforge_dir)] + list(extra_args),
        capture_output=True,
        text=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# Step 0 scaffolding (preserved verbatim).
# ---------------------------------------------------------------------------


class TestStep0Scaffolding(unittest.TestCase):
    def test_default_state_top_level_shape(self):
        """default_state() returns the locked top-level keys with correct types."""
        state = constitute_helper.default_state()

        self.assertIsNone(state["project_name"])
        self.assertIsNone(state["generated_date"])
        self.assertIsNone(state["last_updated"])
        self.assertIsNone(state["mode"])
        self.assertIsNone(state["project_identity"])
        self.assertEqual(state["architecture_rules"], [])
        self.assertEqual(state["code_quality_standards"], [])
        self.assertEqual(state["domain_rules"], [])
        self.assertEqual(state["workflow_rules"], [])
        self.assertIsNone(state["scaffolding_guide"])

        patterns = state["patterns_and_antipatterns"]
        self.assertEqual(
            sorted(patterns.keys()),
            sorted([
                "always_universal",
                "always_project_specific",
                "never_universal",
                "never_project_specific",
                "prefer_universal",
                "prefer_project_specific",
            ]),
        )
        for bucket in patterns.values():
            self.assertEqual(bucket, [])

    def test_reset_writes_default_state_json(self):
        """reset writes constitute.json containing the default state."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"
            result = _run(["--devforge-dir", str(devforge), "reset"], cwd=tmp_path)

            self.assertEqual(result.returncode, 0, result.stderr)

            output_file = devforge / "constitute.json"
            self.assertTrue(output_file.exists())

            loaded = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(loaded, constitute_helper.default_state())

    def test_reset_idempotent_byte_identical(self):
        """Re-running reset produces byte-identical output."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"

            r1 = _run(["--devforge-dir", str(devforge), "reset"], cwd=tmp_path)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            first = (devforge / "constitute.json").read_bytes()

            r2 = _run(["--devforge-dir", str(devforge), "reset"], cwd=tmp_path)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            second = (devforge / "constitute.json").read_bytes()

            self.assertEqual(first, second)


# ---------------------------------------------------------------------------
# Step 1 — FIELD_SCHEMA + ENUM_FIELDS.
# ---------------------------------------------------------------------------


class TestStep1Schema(unittest.TestCase):
    def test_field_schema_has_11_keys(self):
        """FIELD_SCHEMA defines exactly 11 top-level fields."""
        self.assertEqual(len(constitute_helper.FIELD_SCHEMA), 11)

    def test_field_schema_key_order(self):
        """FIELD_SCHEMA preserves the locked key order."""
        names = [name for name, _kind in constitute_helper.FIELD_SCHEMA]
        expected = [
            "project_name",
            "generated_date",
            "last_updated",
            "mode",
            "project_identity",
            "architecture_rules",
            "code_quality_standards",
            "patterns_and_antipatterns",
            "domain_rules",
            "workflow_rules",
            "scaffolding_guide",
        ]
        self.assertEqual(names, expected)

    def test_enum_fields_has_4_enums(self):
        """ENUM_FIELDS defines exactly 4 closed enums."""
        self.assertEqual(len(constitute_helper.ENUM_FIELDS), 4)

    def test_enum_fields_mode(self):
        """ENUM_FIELDS['mode'] contains the two expected values."""
        self.assertEqual(
            constitute_helper.ENUM_FIELDS["mode"],
            {"existing-codebase", "greenfield"},
        )

    def test_enum_fields_rule_tag(self):
        """ENUM_FIELDS['rule_tag'] contains 4 values."""
        self.assertEqual(
            constitute_helper.ENUM_FIELDS["rule_tag"],
            {"extracted", "enforced", "universal", "project-specific"},
        )

    def test_enum_fields_section_tag(self):
        """ENUM_FIELDS['section_tag'] contains 3 values."""
        self.assertEqual(
            constitute_helper.ENUM_FIELDS["section_tag"],
            {"universal", "project-specific", "greenfield-only"},
        )

    def test_enum_fields_code_label(self):
        """ENUM_FIELDS['code_label'] contains 3 values."""
        self.assertEqual(
            constitute_helper.ENUM_FIELDS["code_label"],
            {"CORRECT", "WRONG", "EXAMPLE"},
        )

    def test_default_state_top_level_key_count(self):
        """default_state() returns a dict with exactly 11 top-level keys."""
        state = constitute_helper.default_state()
        self.assertEqual(len(state), 11)

    def test_default_state_section_arrays_empty(self):
        """Section array fields default to []."""
        state = constitute_helper.default_state()
        for field in (
            "architecture_rules",
            "code_quality_standards",
            "domain_rules",
            "workflow_rules",
        ):
            self.assertIsInstance(state[field], list)
            self.assertEqual(state[field], [])

    def test_default_state_patterns_and_antipatterns_structure(self):
        """patterns_and_antipatterns has 6 named buckets, each an empty list."""
        patterns = constitute_helper.default_state()["patterns_and_antipatterns"]
        expected_buckets = sorted([
            "always_universal",
            "always_project_specific",
            "never_universal",
            "never_project_specific",
            "prefer_universal",
            "prefer_project_specific",
        ])
        self.assertEqual(sorted(patterns.keys()), expected_buckets)
        for bucket_list in patterns.values():
            self.assertEqual(bucket_list, [])

    def test_default_state_nullable_fields(self):
        """project_identity and scaffolding_guide default to None."""
        state = constitute_helper.default_state()
        self.assertIsNone(state["project_identity"])
        self.assertIsNone(state["scaffolding_guide"])

    def test_default_state_scalar_fields_none(self):
        """Scalar fields default to None."""
        state = constitute_helper.default_state()
        for field in ("project_name", "generated_date", "last_updated", "mode"):
            self.assertIsNone(state[field])


# ---------------------------------------------------------------------------
# Step 1 — read-init.
# ---------------------------------------------------------------------------


class TestReadInit(unittest.TestCase):
    def test_read_init_round_trip(self):
        """read-init round-trips a real init.yaml written by init_helper."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"
            devforge.mkdir()

            # Use init_helper subprocess to write a real init.yaml.
            r = _run_init(devforge, "set-workspace-mode", "standalone")
            self.assertEqual(r.returncode, 0, r.stderr)
            r = _run_init(devforge, "set-project-root", ".")
            self.assertEqual(r.returncode, 0, r.stderr)
            r = _run_init(devforge, "set-project-state", "brownfield")
            self.assertEqual(r.returncode, 0, r.stderr)
            r = _run_init(devforge, "set-default-branch", "main")
            self.assertEqual(r.returncode, 0, r.stderr)

            # Now parse it back via read-init.
            result = _run(
                ["--devforge-dir", str(devforge), "read-init"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            self.assertEqual(parsed["workspace_mode"], "standalone")
            self.assertEqual(parsed["project_root"], ".")
            self.assertEqual(parsed["project_state"], "brownfield")
            self.assertEqual(parsed["default_branch"], "main")
            self.assertIn("packages_detected", parsed)

    def test_read_init_file_missing_exits_1(self):
        """read-init exits 1 with a stderr message when init.yaml is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"
            devforge.mkdir()  # devforge dir exists but no init.yaml

            result = _run(
                ["--devforge-dir", str(devforge), "read-init"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("init.yaml", result.stderr)

    def test_read_init_malformed_yaml_exits_2(self):
        """read-init exits 2 when init.yaml is malformed."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"
            devforge.mkdir()
            # Write a file that is syntactically invalid for init_helper's parser.
            init_yaml = devforge / "init.yaml"
            init_yaml.write_text("workspace_mode: {bad: yaml: here}\n", encoding="utf-8")

            result = _run(
                ["--devforge-dir", str(devforge), "read-init"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 2)
            self.assertTrue(result.stderr)


# ---------------------------------------------------------------------------
# Step 1 — read-configure.
# ---------------------------------------------------------------------------


class TestReadConfigure(unittest.TestCase):
    def test_read_configure_round_trip(self):
        """read-configure round-trips a real configure.yaml written by configure_helper."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"

            # Use configure_helper subprocess to reset + set a field.
            r = _run_configure(devforge, "reset")
            self.assertEqual(r.returncode, 0, r.stderr)
            r = _run_configure(devforge, "set-project-name", "my-test-project")
            self.assertEqual(r.returncode, 0, r.stderr)

            # Parse back via read-configure.
            result = _run(
                ["--devforge-dir", str(devforge), "read-configure"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            self.assertEqual(parsed["project_name"], "my-test-project")
            # All 28 configure fields present.
            self.assertIn("project_description", parsed)
            self.assertIn("primary_language", parsed)
            self.assertIn("frameworks", parsed)
            self.assertIn("workflow_enforcement", parsed)

    def test_read_configure_all_28_fields_present(self):
        """read-configure emits all 28 configure fields."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"

            r = _run_configure(devforge, "reset")
            self.assertEqual(r.returncode, 0, r.stderr)

            result = _run(
                ["--devforge-dir", str(devforge), "read-configure"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            # configure_helper.FIELD_SCHEMA has exactly 28 fields.
            expected_fields = {name for name, _ in configure_helper.FIELD_SCHEMA}
            self.assertEqual(set(parsed.keys()), expected_fields)

    def test_read_configure_file_missing_exits_1(self):
        """read-configure exits 1 when configure.yaml is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"
            devforge.mkdir()

            result = _run(
                ["--devforge-dir", str(devforge), "read-configure"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("configure.yaml", result.stderr)

    def test_read_configure_malformed_yaml_exits_2(self):
        """read-configure exits 2 when configure.yaml is malformed."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"
            devforge.mkdir()
            configure_yaml = devforge / "configure.yaml"
            configure_yaml.write_text(
                "project_name: {not: valid: for: closed: parser}\n",
                encoding="utf-8",
            )

            result = _run(
                ["--devforge-dir", str(devforge), "read-configure"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 2)
            self.assertTrue(result.stderr)


# ---------------------------------------------------------------------------
# Step 1 — read-docs.
# ---------------------------------------------------------------------------

# Hand-authored minimal fixture fragments for overview + architecture testing.
_OVERVIEW_FIXTURE = """\
# My Project

## Purpose

This is the project purpose text.

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Vue |
| Language | TypeScript |
| Build Tool | Vite |

## Project Structure

```text
project/
├── src/
│   └── main.ts
└── package.json
```

## Key Commands

| Command | Description |
|---|---|
| `npm run dev` | Start dev server |
| `npm run build` | Build for production |
"""

_ARCHITECTURE_FIXTURE = """\
# My Project architecture

## Architecture Overview

This is the architecture overview text spanning multiple
lines of prose.

## Module / Package Structure

```text
src/
├── components/
└── utils/
```

## Patterns

### Repository Pattern

**Applies in**: Data layer implementations.

All data access goes through repositories.

```typescript
class UserRepository {
  getUser(id: string) { ... }
}
```

### Factory Pattern

**Applies in**: Service creation.

Use factories to construct services.

## Conventions

**Naming**
- Classes are PascalCase
- Functions are camelCase

**Import Style**
- Use barrel exports
"""


class TestReadDocs(unittest.TestCase):
    def _write_docs(self, tmp_path, overview_text, arch_text):
        """Write docs/overview.md + docs/architecture.md to tmp_path."""
        docs = tmp_path / "docs"
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "overview.md").write_text(overview_text, encoding="utf-8")
        (docs / "architecture.md").write_text(arch_text, encoding="utf-8")
        return docs

    def test_read_docs_overview_tech_stack(self):
        """read-docs parses Tech Stack table from overview.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_docs(tmp_path, _OVERVIEW_FIXTURE, _ARCHITECTURE_FIXTURE)
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            ts = parsed["overview"]["tech_stack"]
            self.assertIsInstance(ts, list)
            self.assertGreater(len(ts), 0)
            # Check that the table was parsed — layer + technology keys.
            layers = [row["layer"] for row in ts]
            self.assertIn("Framework", layers)
            self.assertIn("Language", layers)

    def test_read_docs_overview_purpose(self):
        """read-docs extracts Purpose section text from overview.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_docs(tmp_path, _OVERVIEW_FIXTURE, _ARCHITECTURE_FIXTURE)
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            purpose = parsed["overview"]["purpose"]
            self.assertIn("purpose text", purpose)

    def test_read_docs_overview_key_commands(self):
        """read-docs parses Key Commands table from overview.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_docs(tmp_path, _OVERVIEW_FIXTURE, _ARCHITECTURE_FIXTURE)
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            cmds = parsed["overview"]["key_commands"]
            self.assertIsInstance(cmds, list)
            self.assertGreater(len(cmds), 0)

    def test_read_docs_architecture_patterns(self):
        """read-docs parses ### Patterns sub-headings from architecture.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_docs(tmp_path, _OVERVIEW_FIXTURE, _ARCHITECTURE_FIXTURE)
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            patterns = parsed["architecture"]["patterns"]
            self.assertIsInstance(patterns, list)
            self.assertGreaterEqual(len(patterns), 2)
            names = [p["name"] for p in patterns]
            self.assertIn("Repository Pattern", names)
            self.assertIn("Factory Pattern", names)

    def test_read_docs_architecture_module_structure(self):
        """read-docs extracts Module / Package Structure section text from architecture.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_docs(tmp_path, _OVERVIEW_FIXTURE, _ARCHITECTURE_FIXTURE)
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            module_structure = parsed["architecture"]["module_structure"]
            self.assertTrue(module_structure, "module_structure should not be empty")
            self.assertIn("src/", module_structure)

    def test_read_docs_architecture_overview_text(self):
        """read-docs extracts Architecture Overview text from architecture.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            self._write_docs(tmp_path, _OVERVIEW_FIXTURE, _ARCHITECTURE_FIXTURE)
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            overview = parsed["architecture"]["architecture_overview"]
            self.assertIn("architecture overview", overview)

    @unittest.skipUnless(_TESTFORGE20.exists(), "testForge20 not present on this machine")
    def test_read_docs_testforge20_real_sample(self):
        """read-docs with testForge20 sample emits tech_stack + patterns."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docs_src = _TESTFORGE20 / "docs"
            docs_dst = tmp_path / "docs"
            shutil.copytree(str(docs_src), str(docs_dst))
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            parsed = json.loads(result.stdout)
            self.assertIn("tech_stack", parsed["overview"])
            self.assertGreater(len(parsed["overview"]["tech_stack"]), 0)
            self.assertIn("patterns", parsed["architecture"])
            self.assertGreater(len(parsed["architecture"]["patterns"]), 0)

    def test_read_docs_overview_missing_exits_1(self):
        """read-docs exits 1 when docs/overview.md is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docs = tmp_path / "docs"
            docs.mkdir()
            # Only architecture.md exists.
            (docs / "architecture.md").write_text(
                _ARCHITECTURE_FIXTURE, encoding="utf-8"
            )
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("overview.md", result.stderr)

    def test_read_docs_architecture_missing_exits_1(self):
        """read-docs exits 1 when docs/architecture.md is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docs = tmp_path / "docs"
            docs.mkdir()
            (docs / "overview.md").write_text(
                _OVERVIEW_FIXTURE, encoding="utf-8"
            )
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("architecture.md", result.stderr)

    def test_read_docs_malformed_markdown_graceful_exit_0(self):
        """read-docs handles malformed markdown gracefully (exit 0, empty sections)."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docs = tmp_path / "docs"
            docs.mkdir()
            # Files exist but contain no recognizable section headings.
            (docs / "overview.md").write_text(
                "This is just random prose with no headings.\n", encoding="utf-8"
            )
            (docs / "architecture.md").write_text(
                "Also random prose.\n", encoding="utf-8"
            )
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path), "--devforge-dir", str(devforge), "read-docs"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0)
            parsed = json.loads(result.stdout)
            self.assertIn("overview", parsed)
            self.assertIn("architecture", parsed)


# ---------------------------------------------------------------------------
# Step 1 — read-glossary (pure-function tests).
# ---------------------------------------------------------------------------


# Minimal 3-term glossary fixture.
_GLOSSARY_3_TERMS = """\
---
generated_by: /generate-docs
total_terms: 3
---

# Project Glossary

## Alpha

The first Greek letter. Used for primary identifiers.

- **Used in**: `docs/overview.md`, `docs/architecture.md` (and 1 others)
- **Related**: Beta, Gamma

## Beta

The second Greek letter. Used for secondary identifiers and testing.

- **Used in**: `docs/overview.md`
- **Related**: Alpha

## Gamma

The third Greek letter. Used only in math contexts.

- **Used in**: `docs/architecture.md`
- **Related**: Alpha, Beta
"""


class TestReadGlossaryPure(unittest.TestCase):
    """Pure-function tests for _parse_glossary_md."""

    def test_parse_glossary_three_terms(self):
        """_parse_glossary_md parses 3 terms from the hand-authored fixture."""
        terms = constitute_helper._parse_glossary_md(_GLOSSARY_3_TERMS)
        self.assertEqual(len(terms), 3)

    def test_parse_glossary_first_term_name(self):
        terms = constitute_helper._parse_glossary_md(_GLOSSARY_3_TERMS)
        self.assertEqual(terms[0]["term"], "Alpha")

    def test_parse_glossary_first_term_definition(self):
        terms = constitute_helper._parse_glossary_md(_GLOSSARY_3_TERMS)
        self.assertIn("first Greek letter", terms[0]["definition"])

    def test_parse_glossary_first_term_used_in(self):
        terms = constitute_helper._parse_glossary_md(_GLOSSARY_3_TERMS)
        used_in = terms[0]["used_in"]
        self.assertIsInstance(used_in, list)
        self.assertGreater(len(used_in), 0)
        # Should include the two cited files (without trailing "(and 1 others)")
        self.assertTrue(
            any("overview.md" in u for u in used_in),
            "expected overview.md in used_in: {0}".format(used_in),
        )

    def test_parse_glossary_first_term_related(self):
        terms = constitute_helper._parse_glossary_md(_GLOSSARY_3_TERMS)
        related = terms[0]["related"]
        self.assertIsInstance(related, list)
        self.assertIn("Beta", related)
        self.assertIn("Gamma", related)

    def test_parse_glossary_empty_text(self):
        """_parse_glossary_md returns [] for empty input."""
        terms = constitute_helper._parse_glossary_md("")
        self.assertEqual(terms, [])

    def test_parse_glossary_no_terms_only_frontmatter(self):
        """_parse_glossary_md returns [] when only YAML frontmatter is present."""
        text = "---\ntotal_terms: 0\n---\n\n# Project Glossary\n"
        terms = constitute_helper._parse_glossary_md(text)
        self.assertEqual(terms, [])

    def test_parse_glossary_term_with_no_metadata(self):
        """Term with no Used in / Related lines still parses definition."""
        text = "## Foo\n\nFoo is a placeholder term.\n"
        terms = constitute_helper._parse_glossary_md(text)
        self.assertEqual(len(terms), 1)
        self.assertEqual(terms[0]["term"], "Foo")
        self.assertIn("placeholder", terms[0]["definition"])
        self.assertEqual(terms[0]["used_in"], [])
        self.assertEqual(terms[0]["related"], [])

    def test_parse_used_in_line_strips_and_others(self):
        """_parse_used_in_line strips '(and N others)' suffix."""
        line = "- **Used in**: `a.md`, `b.md` (and 3 others)"
        result = constitute_helper._parse_used_in_line(line)
        self.assertEqual(result, ["`a.md`", "`b.md`"])

    def test_parse_related_line_basic(self):
        """_parse_related_line parses comma-separated related terms."""
        line = "- **Related**: Alpha, Beta, Gamma"
        result = constitute_helper._parse_related_line(line)
        self.assertEqual(result, ["Alpha", "Beta", "Gamma"])


class TestReadGlossarySubprocess(unittest.TestCase):
    def test_read_glossary_round_trip(self):
        """read-glossary round-trips a 3-term hand-authored fixture."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docs = tmp_path / "docs"
            docs.mkdir()
            (docs / "glossary.md").write_text(_GLOSSARY_3_TERMS, encoding="utf-8")
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path),
                 "--devforge-dir", str(devforge), "read-glossary"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            terms = json.loads(result.stdout)
            self.assertEqual(len(terms), 3)
            names = [t["term"] for t in terms]
            self.assertEqual(names, ["Alpha", "Beta", "Gamma"])

    def test_read_glossary_file_missing_exits_1(self):
        """read-glossary exits 1 when glossary.md is missing."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path),
                 "--devforge-dir", str(devforge), "read-glossary"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("glossary.md", result.stderr)

    def test_read_glossary_empty_file_exits_0_empty_list(self):
        """read-glossary exits 0 and emits [] for an empty glossary.md."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docs = tmp_path / "docs"
            docs.mkdir()
            (docs / "glossary.md").write_text("", encoding="utf-8")
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path),
                 "--devforge-dir", str(devforge), "read-glossary"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            terms = json.loads(result.stdout)
            self.assertEqual(terms, [])

    @unittest.skipUnless(_TESTFORGE20.exists(), "testForge20 not present on this machine")
    def test_read_glossary_testforge20_real_sample(self):
        """read-glossary parses real testForge20 glossary without error."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            docs_src = _TESTFORGE20 / "docs"
            docs_dst = tmp_path / "docs"
            docs_dst.mkdir()
            # Copy only glossary.md to keep test lightweight.
            shutil.copy(
                str(docs_src / "glossary.md"),
                str(docs_dst / "glossary.md"),
            )
            devforge = tmp_path / ".devforge"

            result = _run(
                ["--install-root", str(tmp_path),
                 "--devforge-dir", str(devforge), "read-glossary"],
                cwd=tmp_path,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            terms = json.loads(result.stdout)
            self.assertIsInstance(terms, list)
            self.assertGreater(len(terms), 10, "Expected >10 terms in testForge20 glossary")
            # Each term has required keys.
            for t in terms:
                self.assertIn("term", t)
                self.assertIn("definition", t)
                self.assertIn("used_in", t)
                self.assertIn("related", t)


if __name__ == "__main__":
    unittest.main()
